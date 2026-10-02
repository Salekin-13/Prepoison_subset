"""Error-analysis table: one row per (version, run, module, element) over the 15 scoring modules.

status  TP / FP / FN / TN   (TN = closed-set element neither predicted nor in the ground truth)
features come from RTL_data/<module>.vhd (the files the executor reads) and parsed_tuning18/.
Run from the repo root. Self-test against hand-read RTL statements runs first; nothing is written
if it fails.
"""
import json, re, sys, csv
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "."); sys.path.insert(0, "assetgen_meta")
import eval_assets as ea
import meta_tools as mt

OUT = Path(__file__).parent
VERSIONS = {"v2x3r8": [0, 1, 2], "m4bc606s0": [0], "m4bc606s1": [0], "m4bc606s2": [0]}

# ------------------------------------------------------------------ RTL features ---
LIT = re.compile(r"""^\s*(\(\s*others\s*=>\s*'[01-]'\s*\)|'[01xzXZ-]'|"[01xzXZ-]*"|x"[0-9a-fA-F_]*"|\d+|true|false|[A-Za-z_]\w*_c)\s*$""")
IDENT = re.compile(r"^\s*([A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)*)(\s*\([^()]*\))?\s*$")


def statements(path):
    """-> [(start line, statement text, in_clocked_process)] from the comment-stripped file."""
    raw = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    code = [l.split("--")[0] for l in raw]
    # clocked-process spans
    clocked = [False] * (len(code) + 1)
    i = 0
    while i < len(code):
        if re.search(r"^\s*(\w+\s*:\s*)?process\b", code[i], re.I) and not re.search(r"\bend\s+process\b", code[i], re.I):
            j = i
            while j < len(code) and not re.search(r"\bend\s+process\b", code[j], re.I):
                j += 1
            ck = any(re.search(r"\b(rising_edge|falling_edge)\b", code[k], re.I) for k in range(i, min(j + 1, len(code))))
            for k in range(i, min(j + 1, len(code))):
                clocked[k + 1] = ck
            i = j + 1
        else:
            i += 1
    out, buf, start = [], "", None
    for n, l in enumerate(code, 1):
        for part in re.split(r"(;)", l):
            if part == ";":
                if buf.strip():
                    out.append((start, " ".join(buf.split()), clocked[start]))
                buf, start = "", None
            else:
                if part.strip() and start is None:
                    start = n
                buf += " " + part
    return out


ASSIGN = re.compile(r"(?:^|\bthen\b|\belse\b|\bbegin\b|\bgenerate\b|\bloop\b|=>)\s*(?:\w+\s*:\s*)?"
                    r"([A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)*)\s*(\([^;]*?\))?\s*<=\s*(.*)$", re.I)


def module_features(path, names, ports_dir):
    """{name: feature dict} for the given element names."""
    st = statements(path)
    assigns = defaultdict(list)     # name -> [(line, rhs, clocked)]
    cond_text, rhs_all = [], []      # condition segments; (target, rhs)
    portmap_actuals = Counter()
    for line, s, ck in st:
        for m in re.finditer(r"\b(?:if|elsif)\b(.*?)\bthen\b", s, re.I):
            cond_text.append(m.group(1))
        for m in re.finditer(r"\bcase\b(.*?)\bis\b", s, re.I):
            cond_text.append(m.group(1))
        for m in re.finditer(r"\bwhen\b(.*?)(?=\belse\b|=>|$)", s, re.I):
            cond_text.append(m.group(1))
        for m in re.finditer(r"=>\s*([A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)*)\s*(?=[,)])", s):
            portmap_actuals[m.group(1)] += 1
        # split on control keywords so each assignment is found once
        for seg in re.split(r"(?=\b(?:then|else|elsif|begin)\b)", s, flags=re.I):
            m = ASSIGN.search(seg.strip())
            if m and not re.match(r"\s*(if|elsif|when|while|return)\b", seg.strip(), re.I) or (m and re.match(r"\s*(then|else|begin)\b", seg.strip(), re.I)):
                tgt, rhs = m.group(1), m.group(3).strip()
                assigns[tgt].append((line, rhs, ck))
                rhs_all.append((tgt, rhs))
    feats = {}
    for n in names:
        pat = re.compile(rf"(?<![\w.]){re.escape(n)}(?![\w])")
        base = n.split(".")[0]
        own = assigns.get(n, []) + ([] if "." in n else [])
        kinds, sources, regd, comb = Counter(), set(), False, False
        for _l, rhs, ck in own:
            r = re.sub(r"\s+when\s+others.*$", "", rhs)
            if LIT.match(r):
                kinds["const"] += 1
            elif IDENT.match(r) and not re.search(r"\bwhen\b|\bnot\b|\band\b|\bor\b|\bxor\b|[+\-*/&=<>]", r):
                kinds["relay"] += 1; sources.add(IDENT.match(r).group(1))
            else:
                kinds["computed"] += 1
            regd |= ck; comb |= not ck
        nonconst = kinds["relay"] + kinds["computed"]
        readers = sorted({t for t, rhs in rhs_all if t != n and pat.search(rhs)})
        fwd_ports = sorted({t for t, rhs in rhs_all if t != n and IDENT.match(rhs) and IDENT.match(rhs).group(1) == n
                            and ports_dir.get(t) == "out"})
        src_in_ports = sorted(s_ for s_ in sources if ports_dir.get(s_.split(".")[0]) == "in")
        feats[n] = {
            "n_assign": len(own), "n_const": kinds["const"], "n_relay": kinds["relay"], "n_computed": kinds["computed"],
            "only_relay": nonconst > 0 and kinds["computed"] == 0,
            "relay_sources": ";".join(sorted(sources)), "relay_from_input_port": bool(src_in_ports),
            "registered": regd, "combinational": comb,
            "field_of_assigned_record": ("." in n and base in assigns),
            "read_in_condition": any(pat.search(c) for c in cond_text),
            "n_readers": len(readers), "readers": ";".join(readers[:8]),
            "forwarded_to_out_port": ";".join(fwd_ports),
            "portmap_actual": portmap_actuals.get(n, 0) > 0,
        }
    return feats, assigns


def selftest():
    wdt, trng = "RTL_data/neorv32_wdt.vhd", "RTL_data/neorv32_trng.vhd"
    f, a = module_features(wdt, ["clkgen_en_o", "rstn_o", "reset_cause", "cnt_timeout", "ctrl.enable"], {"clkgen_en_o": "out", "rstn_o": "out"})
    assert f["clkgen_en_o"]["only_relay"] and f["clkgen_en_o"]["relay_sources"] == "ctrl.enable", f["clkgen_en_o"]
    assert f["rstn_o"]["n_computed"] >= 1 and not f["rstn_o"]["only_relay"], f["rstn_o"]
    assert f["reset_cause"]["registered"], f["reset_cause"]
    assert f["cnt_timeout"]["n_computed"] >= 1, f["cnt_timeout"]
    assert f["ctrl.enable"]["read_in_condition"], f["ctrl.enable"]
    assert "clkgen_en_o" in f["ctrl.enable"]["forwarded_to_out_port"], f["ctrl.enable"]
    g, _ = module_features(trng, ["data_o"], {"data_o": "out"})
    assert g["data_o"]["only_relay"] and "sample_sreg" in g["data_o"]["relay_sources"], g["data_o"]
    # hand-read statements these assertions rest on (printed so the reader can check them)
    for n in ("clkgen_en_o", "rstn_o", "cnt_timeout"):
        print("  hand-check", n, "->", a[n][:2])
    print("  hand-check data_o ->", _[ "data_o"][:2])
    print("SELFTEST PASS")


# ------------------------------------------------------------------ build table ---
def main():
    selftest()
    gt = ea.load_refs()["gt"]
    closed = ea.load_closed()
    runs = ea.collect(list(VERSIONS))
    common = ea.common_modules(runs, gt)
    parsed = {m: json.loads(Path(f"parsed_tuning18/{m}.json").read_text(encoding="utf-8")) for m in common}
    rows = []
    for v, reps in VERSIONS.items():
        for rep in reps:
            d = Path(f"assets_tuning18_{v}_r{rep}")
            run = ea.load_run(d)
            sc = ea.score(run, gt, strict=True, only=common)
            for m in sorted(common):
                P = parsed[m]
                ports_dir = {e["name"]: e.get("dir", "") for e in P["ports"]}
                types = {e["name"]: e.get("type", "") for e in P["ports"] + P["signals"]}
                kind_of = {**{e["name"]: "port" for e in P["ports"]}, **{e["name"]: "signal" for e in P["signals"]}}
                pm = sc["per_module"][m]
                fp_left = Counter(pm["fp"])
                gtnames = [e for e, _o in gt[m]]
                # model rationale per element
                flat = json.loads((d / f"{m}.json").read_text(encoding="utf-8"))
                rat = {}
                if (d / "_nested" / f"{m}.json").exists():
                    for c in json.loads((d / "_nested" / f"{m}.json").read_text(encoding="utf-8")).get("conceptual assets", []):
                        for s in c.get("related structural assets", []) or []:
                            rat.setdefault(s.get("asset rtl"), {"concept": c.get("concept", ""), "objective": c.get("security objective", ""),
                                                                 "reasoning": c.get("reasoning", ""), "realization": s.get("realization", "")})
                else:
                    for a in flat.get("Assets", []):
                        rat.setdefault(a.get("Asset RTL"), {"concept": a.get("Concept", "") or a.get("Asset Name", ""),
                                                            "objective": a.get("Security Objective", ""),
                                                            "reasoning": (a.get("Functionality", "") + " || " + a.get("Justification", "")).strip(" |"),
                                                            "realization": ""})
                pred = [a[1] for a in run.get(m, [])]
                names = set(pred) | set(gtnames) | set(kind_of)
                feats, _ = module_features(f"RTL_data/{m}.vhd", sorted(names), ports_dir)
                status = {}
                for n in pred:
                    status.setdefault(n, [])
                    if fp_left[n] > 0:
                        fp_left[n] -= 1; status[n].append("FP")
                    else:
                        status[n].append("TP")
                for n in pm["fn"]:
                    status.setdefault(n, []).append("FN")
                for n in kind_of:
                    if n not in status and n not in gtnames:
                        status[n] = ["TN"]
                for n, sts in status.items():
                    for s_ in sts:
                        base = n.split(".")[0]
                        cls = ea.elem_class(m, n, closed)
                        typ = types.get(n, types.get(base, ""))
                        r = rat.get(n, {})
                        rows.append({"version": v, "run": rep, "module": m, "element": n, "status": s_,
                                     "in_gt": n in gtnames, "predicted": s_ in ("TP", "FP"),
                                     "class": cls, "dir": ports_dir.get(base, ""), "type": typ,
                                     "bus_typed": bool(re.search(r"bus_(req|rsp)_t", typ)),
                                     "clk_rst_named": bool(re.match(r"(clk|rst|rstn)(_|$)", base)),
                                     **feats.get(n, {}),
                                     "gt_objective": next((o for e, o in gt[m] if e == n), ""),
                                     "pred_objective": r.get("objective", ""), "realization": r.get("realization", ""),
                                     "concept": r.get("concept", ""), "reasoning": (r.get("reasoning", "") or "")[:400]})
    keys = list(rows[0])
    with open(OUT / "error_table.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    c = Counter((r["version"], r["status"]) for r in rows)
    print("common modules:", len(common), "| rows:", len(rows))
    for v in VERSIONS:
        print(v, {s: c[(v, s)] for s in ("TP", "FP", "FN", "TN")})


if __name__ == "__main__":
    main()
