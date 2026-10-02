"""Seed-method worked examples: shared data, a small Verilog reader, and the checker for drafted demonstrations.

The two example designs (omsp_gpio, tiny_aes) and their VERIFIED annotations (concepts, objectives, element lists) come
from icl_examples_01b_noparse.ICL_ASSET_EXAMPLES_01B_NOPARSE, the RTL-only block the baseline v2x3r8 used. The verified
element lists are fixed: a draft must keep every verified element with its verified entity and the verified concept
wording. Anything else it reports must be a realization point the seed's rules require for the same concept, and each
such addition is listed as a departure with the seed lines that require it.

Nothing here calls an API. selftest() checks the Verilog reader against hand-read lines of the example RTL.
"""
from __future__ import annotations

import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from icl_examples_01b_noparse import ICL_ASSET_EXAMPLES_01B_NOPARSE as SRC  # noqa: E402

SEED_PATH = ROOT / "assetgen_meta/runs/meta_7e194e6254be_gpt-6-astra/sample_0/exec_prompt.txt"
HEADS = {"omsp_gpio": "### CASE STUDY 1", "tiny_aes": "### CASE STUDY 2"}
REALIZATIONS = ("stores", "sets", "computes", "exit port")


def _span(s: str, needle: str):
    k = s.index(needle); i = s.rindex("{", 0, k); d = 0
    for j in range(i, len(s)):
        d += (s[j] == "{") - (s[j] == "}")
        if d == 0:
            return i, j + 1
    raise ValueError(needle)


def load_case(ip: str) -> dict:
    """RTL exactly as the executor would receive it (up to the last endmodule), plus the verified annotation."""
    h = SRC.index(HEADS[ip]); r = SRC.index("=== RTL ===\n", h) + len("=== RTL ===\n"); e = SRC.index("CSA ANALYSIS", r)
    block = SRC[r:e]
    rtl = block[:block.rindex("endmodule") + len("endmodule")]
    a, b = _span(SRC, f'"IP": "{ip}"')
    gold = json.loads(SRC[a:b])
    return {"ip": ip, "rtl": rtl,
            "concepts": [{"id": c["id"], "concept": c["Concept"], "objective": c["Security Objective"], "why": c["Why"]}
                         for c in gold["ConceptualAssets"]],
            "elements": [{"entity": x["Entity"], "name": x["Asset RTL"], "concept": x["Concept"],
                          "objective": x["Security Objective"], "justification": x["Justification"]}
                         for x in gold["Assets"]]}


# ----------------------------------------------------------------------------------------------- Verilog reader ---
_KW = {"input", "output", "inout", "reg", "wire", "signed", "logic", "assign", "always", "posedge", "negedge", "or",
       "if", "else", "begin", "end", "case", "endcase", "default", "module", "endmodule", "parameter", "localparam"}


def modules(rtl: str) -> dict:
    """module name -> (first line number, body lines as [(line_no, text)])."""
    out, cur = {}, None
    for i, line in enumerate(rtl.splitlines(), 1):
        m = re.match(r"\s*module\s+(\w+)", line)
        if m:
            cur = m.group(1); out[cur] = (i, [])
        if cur:
            out[cur][1].append((i, line))
        if re.match(r"\s*endmodule\b", line):
            cur = None
    return out


def statements(lines, spans=False):
    """Join physical lines into ';'-terminated statements, keeping the first line number (and the last, if spans)."""
    stmts, buf, start = [], "", None
    for i, t in lines:
        if not buf.strip():
            start = i
        buf += " " + t
        while ";" in buf:
            s, buf = buf.split(";", 1)
            stmts.append((start, i, s.strip()) if spans else (start, s.strip())); start = i
    return stmts


def inventory(rtl: str) -> dict:
    """(module, name) -> {"kind": input|output|inout|reg|wire, "output_reg": bool, "line": n}."""
    inv = {}
    for mod, (_l0, lines) in modules(rtl).items():
        for ln, s in statements(lines):
            m = re.match(r"(input|output|inout|reg|wire)\b(.*)", s)
            if not m:
                continue
            kind, rest = m.group(1), m.group(2)
            out_reg = kind == "output" and re.match(r"\s*reg\b", rest) is not None
            rest = re.sub(r"\[[^\]]*\]", " ", rest.split("=")[0])
            for n in re.findall(r"\b[A-Za-z_]\w*\b", rest):
                if n in _KW:
                    continue
                if (mod, n) in inv and inv[(mod, n)]["kind"] in ("input", "output", "inout"):
                    if kind == "reg":
                        inv[(mod, n)]["output_reg"] = True
                    continue
                inv[(mod, n)] = {"kind": kind, "output_reg": out_reg, "line": ln}
    return inv


_INST = re.compile(r"(?!(?:if|else|begin|end|case|always|assign|module)\b)\w+\s+\w+\s*\(")


def uses(rtl: str, mod: str, name: str) -> dict:
    """Where `name` is written and read inside `mod`.
    written: (line, 'clocked' | 'assign' | 'comb') ; read: (line, 'expr' | 'cond' | 'clockedge') ; inst: (line, instance)."""
    lines = modules(rtl)[mod][1]
    phys = dict(lines)
    w = re.compile(rf"(?<![\w.]){re.escape(name)}(?![\w])")
    res = {"written": [], "read": [], "inst": []}
    clocked_block = False
    for start, end, s in statements(lines, spans=True):
        # report the physical line where the name occurs, not the line the statement starts on
        ln = next((i for i in range(start, end + 1) if w.search(phys.get(i, ""))), start)
        if re.match(r"(input|output|inout|reg|wire|parameter|localparam)\b", s) and "=" not in s:
            continue
        if re.match(r"(input|output|inout|parameter|localparam)\b", s):
            continue
        if re.match(r"wire\b", s) and "=" in s:
            lhs, rhs = s.split("=", 1)
            if w.search(lhs):
                res["written"].append((ln, "assign"))
            if w.search(rhs):
                res["read"].append((ln, "expr"))
            continue
        if s.startswith("assign"):
            lhs, rhs = s[len("assign"):].split("=", 1)
            if w.search(lhs):
                res["written"].append((ln, "assign"))
            if w.search(rhs):
                res["read"].append((ln, "expr"))
            continue
        sens = re.search(r"always\s*@\s*\(([^)]*)\)", s)
        if sens:
            clocked_block = bool(re.search(r"\b(posedge|negedge)\b", sens.group(1)))
            if w.search(sens.group(1)):
                res["read"].append((ln, "clockedge" if clocked_block else "expr"))
            s = s[sens.end():]
        if re.search(r"<=|(?<![<>!=])=(?!=)", s) and not _INST.match(s):
            for cond in re.findall(r"\bif\s*\((.*?)\)\s*(?=[\w{(])", s) + re.findall(r"\bcase\s*\((.*?)\)", s):
                if w.search(cond):
                    res["read"].append((ln, "cond"))
            body = re.sub(r"\bcase\s*\(.*?\)", " ", s)
            body = re.sub(r"^\s*[\w']+\s*:", " ", body)                 # a case item label such as 8'h00:
            body = re.sub(r"\bif\s*\(.*?\)\s*(?=[\w{(])", " ", body)
            body = re.sub(r"\b(else|begin|end)\b", " ", body)
            parts = re.split(r"<=|(?<![<>!=])=(?!=)", body, maxsplit=1)
            if len(parts) == 2:
                if w.search(parts[0]):
                    res["written"].append((ln, "clocked" if clocked_block and "<=" in body else "comb"))
                if w.search(parts[1]):
                    res["read"].append((ln, "expr"))
            continue
        if _INST.match(s):
            if w.search(s):
                res["inst"].append((ln, s[:60]))
    return res


def selftest():
    g = load_case("omsp_gpio"); a = load_case("tiny_aes")
    ig, ia = inventory(g["rtl"]), inventory(a["rtl"])
    L = g["rtl"].splitlines(); A = a["rtl"].splitlines()
    # hand-read lines (1-based) of the example RTL
    assert re.match(r"input\s+per_en;", L[71].strip()) and ig[("omsp_gpio", "per_en")]["kind"] == "input"
    assert re.match(r"input\s+\[1:0\] per_we;", L[72].strip()) and ig[("omsp_gpio", "per_we")]["kind"] == "input"
    assert L[198].strip() == "reg  [7:0] p1dir;" and ig[("omsp_gpio", "p1dir")]["kind"] == "reg"
    assert L[204].strip() == "assign p1_dout_en = p1dir;" and ig[("omsp_gpio", "p1_dout_en")]["kind"] == "output"
    u = uses(g["rtl"], "omsp_gpio", "p1dir")
    assert (204, "clocked") in u["written"] and (203, "clocked") in u["written"] and (205, "expr") in u["read"], u
    u = uses(g["rtl"], "omsp_gpio", "per_en")
    assert any(ln == 145 for ln, _k in u["read"]), u                       # reg_sel = per_en & (...)
    u = uses(g["rtl"], "omsp_gpio", "mclk")
    assert u["read"] and all(k == "clockedge" for _l, k in u["read"]) or u["inst"], u
    assert A[11].strip() == "k0 <= key;" and ia[("aes_128", "k0")]["kind"] == "reg"
    u = uses(a["rtl"], "aes_128", "key")
    assert (11, "expr") in u["read"] and (12, "expr") in u["read"], u
    assert ia[("final_round", "key_in")]["kind"] == "input"
    assert (102, "expr") in uses(a["rtl"], "final_round", "key_in")["read"]
    assert ia[("final_round", "state_out")] == {"kind": "output", "output_reg": True, "line": 94}
    assert (114, "clocked") in uses(a["rtl"], "final_round", "state_out")["written"]
    assert ia[("expand_key_128", "out_1")]["output_reg"] and (62, "clocked") in uses(a["rtl"], "expand_key_128", "out_1")["written"]
    assert ia[("aes_128", "s0")]["kind"] == "reg" and ia[("aes_128", "state")]["kind"] == "input"
    # verified annotation shape
    assert len(g["elements"]) == 14 and len(a["elements"]) == 4 and len(g["concepts"]) == 3 and len(a["concepts"]) == 3
    return True


# ------------------------------------------------------------------------------------------------------ checker ---
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def quote_lines(rtl: str, q: str):
    """Line numbers of RTL lines that contain quote q (whitespace-normalised); [] if none."""
    nq = norm(q)
    return [i for i, line in enumerate(rtl.splitlines(), 1) if nq and nq in norm(line)]


def check_draft(case: dict, draft: dict) -> dict:
    """-> {"hard": [...], "flags": [...], "quotes": {quote: [lines]}}. Hard problems block the build."""
    rtl, inv = case["rtl"], inventory(case["rtl"])
    hard, flags, qmap = [], [], {}
    out = draft.get("output") or {}
    if set(out) != {"module name", "conceptual assets"}:
        hard.append(f"output keys {sorted(out)}")
    cas = out.get("conceptual assets") or []
    ver_concepts = [c["concept"] for c in case["concepts"]]
    got_concepts = [c.get("concept") for c in cas]
    if got_concepts != ver_concepts:
        hard.append(f"concepts must be the verified ones, verbatim and in order: got {got_concepts}")
    reported = set()
    for c in cas:
        if set(c) != {"concept", "security objective", "reasoning", "related structural assets"}:
            hard.append(f"concept keys {sorted(c)}")
        if c.get("security objective") not in ("Confidentiality", "Integrity", "Availability"):
            hard.append(f"objective {c.get('security objective')!r}")
        seen = set()
        for r in c.get("related structural assets") or []:
            if set(r) != {"asset rtl", "entity", "realization"}:
                hard.append(f"reference keys {sorted(r)}")
            ent, name, lab = r.get("entity"), r.get("asset rtl"), r.get("realization")
            key = (ent, name)
            if key in seen:
                hard.append(f"duplicate reference {key} in one concept")
            seen.add(key); reported.add(key)
            if lab not in REALIZATIONS:
                hard.append(f"{key}: realization {lab!r}")
            if "." in (name or "") or key not in inv:
                hard.append(f"{key}: not a declared element of that entity")
                continue
            kind = inv[key]["kind"]; u = uses(rtl, ent, name)
            if lab == "exit port" and kind != "output":
                hard.append(f"{key}: 'exit port' but declared {kind}")
            if lab == "sets":
                if kind == "input":
                    if any(k == "clockedge" for _l, k in u["read"]):
                        hard.append(f"{key}: clock/reset input labelled 'sets'")
                    if not any(k in ("expr", "cond") for _l, k in u["read"]):
                        hard.append(f"{key}: input labelled 'sets' but never read in an expression or condition of {ent} "
                                    f"(only forwarded: {u['inst'][:2]})")
                else:
                    flags.append(f"{key}: internal element labelled 'sets' ({kind}); check it is a demonstrated setting point")
            if lab == "stores" and not any(k == "clocked" for _l, k in u["written"]):
                hard.append(f"{key}: 'stores' but not written on a clock edge in {ent}")
            if lab == "computes" and not u["written"]:
                hard.append(f"{key}: 'computes' but never assigned in {ent}")
            if kind == "output" and lab != "exit port":
                flags.append(f"{key}: output labelled {lab!r}; the seed prefers 'exit port' when the concept leaves through it")
        text = c.get("reasoning") or ""
        qs = re.findall(r"`([^`]+)`", text)
        if not qs:
            hard.append(f"reasoning of {c.get('concept', '')[:40]!r} quotes no RTL")
        for q in qs:
            qmap[q] = quote_lines(rtl, q)
    for e in case["elements"]:
        if (e["entity"], e["name"]) not in reported:
            hard.append(f"verified element dropped: {e['entity']}.{e['name']}")
    verified = {(e["entity"], e["name"]) for e in case["elements"]}
    listed = {(d.get("entity"), d.get("element")) for d in draft.get("departures") or []}
    for key in sorted(reported - verified):
        if key not in listed:
            hard.append(f"addition {key} is not listed in departures")
    for d in draft.get("departures") or []:
        lines = d.get("seed_lines") or []
        if not lines or not all(isinstance(x, int) and 1 <= x <= 293 for x in lines):
            hard.append(f"departure {d.get('element')}: seed_lines {lines}")
    for part in (draft.get("analysis") or {}).values():
        for q in re.findall(r"`([^`]+)`", part if isinstance(part, str) else json.dumps(part)):
            qmap[q] = quote_lines(rtl, q)
    identifiers = {n for (_m, n) in inv} | set(modules(rtl))
    for q, ls in qmap.items():
        if not ls and not (re.fullmatch(r"[A-Za-z_]\w*(\.\w+)?", q.strip()) and q.strip().split(".")[0] in identifiers):
            hard.append(f"quote not found in the RTL: `{q[:80]}`")
    return {"hard": hard, "flags": flags, "quotes": qmap, "reported": sorted(reported),
            "additions": sorted(reported - verified)}


if __name__ == "__main__":
    selftest()
    print("selftest PASS")
    for ip in HEADS:
        c = load_case(ip)
        inv = inventory(c["rtl"])
        print(ip, "lines", len(c["rtl"].splitlines()), "| declared", len(inv), "| modules", list(modules(c["rtl"])),
              "| verified", [(e["entity"], e["name"], e["concept"]) for e in c["elements"]])
