"""Code-built occurrence profiles: the part of the LLM annotator that measurement showed it cannot do.

WHERE THE LLM FAILED (run 6 audit, bahavioral_patterns_of_assets/annotation_pack_elements/occurrence_profiles_v2/
_audit_2026-09-16_run6/run6_outputs.txt line 104, 661 entries over trng and cache):
    structures equal to the code finder's: 476 of 661
    per kind, in the source / wrong end / missing or wrong start / extra:
        branch    408 / 106 / 158 / 8        <- the failure
        if        408 /   0 / 112 / 2        <- the failure
        alternative 161 /  1 /  26 / 2
        architecture body 519 / 0 / 0 / 0    process 415 / 0 / 0 / 0    case 163 / 0 / 6 / 0
        port clause 75 / 0 / 0 / 0           association list 48 / 0 / 0 / 0   generate 22 / 0 / 0 / 0
The model names the CONTAINER correctly (process, architecture, case, port clause, association list, generate: zero
errors) and gets the BRANCH level wrong: wrong end line, wrong or missing start, or the branch omitted entirely. Run 5
hand review of the same corpus called this out by name: context_span_wrong 104, context_structure_wrong 59 of 662
(_audit_2026-09-15_run5/analysis_b.txt line 38).

SO THIS FILE SUPPLIES, BY CODE: for every element of the closed set, every line it occurs on, what it does on that line
(declaration, target, condition, read, port map, clock or reset position) and the exact structure chain with spans,
from structure_finder. No model, no API call. Line numbers refer to RTL_data/<module>.vhd, the revision the executor
reads (the annotation pack used a different, longer copy, so its line numbers do not transfer).

Usage: python step1/occurrence_profile.py    -> writes step1/occurrence_profiles/<module>.json and prints a summary.
"""
from __future__ import annotations

import json, re, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
import structure_finder as SF   # noqa: E402

OUT = HERE / "occurrence_profiles"
COMMENT = re.compile(r"--.*$")
ASSIGN = re.compile(r"(<=|:=)")
COND_OPEN = re.compile(r"\b(if|elsif)\b(?P<expr>.*?)\bthen\b", re.I)
WHEN_ELSE = re.compile(r"\bwhen\b(?P<expr>.*?)(?=\belse\b|$)", re.I)
CASE_OPEN = re.compile(r"\bcase\b(?P<expr>.*?)\bis\b", re.I)
# "[^=]" keeps this off a conditional assignment: in `when (b = '1') else c` the "=" blocks the match
CASE_ALT = re.compile(r"\bwhen\b(?P<expr>[^=]*?)=>", re.I)
EDGE = re.compile(r"\b(rising_edge|falling_edge)\s*\((?P<expr>[^)]*)\)", re.I)
SENS = re.compile(r"\bprocess\s*\((?P<expr>[^)]*)\)", re.I)


def masked_lines(path: Path) -> dict:
    """{line number: text with comments blanked}, so names inside comments never count as occurrences."""
    out = {}
    for i, t in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        out[i] = COMMENT.sub(lambda m: " " * len(m.group(0)), t)
    return out


def roles(text: str, name: str) -> list[str]:
    """What the element does on this line. A line can carry more than one role."""
    w = re.compile(rf"(?<![\w.]){re.escape(name)}(?![\w])")
    hit = lambda s: bool(s and w.search(s))
    out = []
    # `when "010" => alu_res <= a xor b;` is a CASE ALTERNATIVE: only the choice ("010") is a condition, the rest is an
    # ordinary assignment. Without this split, `when ... ` swallowed the body and 84 reads were called conditions,
    # which would have produced false GATES relations.
    alt = CASE_ALT.search(text)
    body = text.split("=>", 1)[1] if alt else text
    if alt and hit(alt.group("expr")):
        out.append("condition")
    for rx, seg in ((COND_OPEN, text), (WHEN_ELSE, body), (CASE_OPEN, text)):
        for m in rx.finditer(seg):
            if hit(m.group("expr")):
                out.append("condition"); break
    for rx in (EDGE, SENS):
        for m in rx.finditer(text):
            if hit(m.group("expr")):
                out.append("clock or reset position"); break
    a = ASSIGN.search(body)
    if a:
        if hit(body[:a.start()]):
            out.append("target")
        if hit(body[a.end():]) and "condition" not in out:
            out.append("read")
    elif not out and hit(text):
        out.append("read")
    return sorted(set(out)) or ["mention"]


def profile_module(stem: str) -> dict:
    return profile_file(ROOT / f"RTL_data/{stem}.vhd",
                        json.loads((ROOT / f"parsed_tuning18/{stem}.json").read_text(encoding="utf-8")))


def statements(L: dict) -> list[dict]:
    """';'-terminated statements over the masked lines: {id, first, last, text}.

    Relations need this: a line can hold two statements, and a statement can span lines, so a target cannot be paired
    with its own operands by line number alone.
    """
    out, buf, first, depth = [], "", None, 0
    for n, t in sorted(L.items()):
        for ch in t:
            if first is None and not ch.isspace():
                first = n
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            if ch == ";" and depth == 0:
                out.append({"id": len(out), "first": first or n, "last": n, "text": re.sub(r"\s+", " ", buf).strip()})
                buf, first = "", None
                continue
            buf += ch
        buf += " "
    if buf.strip():
        out.append({"id": len(out), "first": first or max(L), "last": max(L), "text": re.sub(r"\s+", " ", buf).strip()})
    # a control header carries no ';', so it sits in front of the statement it opens: drop those prefixes, since the
    # enclosing structure chain already records them and pairing a target with its operands needs the bare statement
    head = re.compile(r"^\s*(?:(?:els)?if\b.*?\bthen\b|else\b|begin\b|case\b.*?\bis\b|when\b[^;]*?=>|"
                      r"\w+\s*:\s*process\b[^)]*\)?|process\b[^)]*\)?)\s*", re.I)
    for s in out:
        s["raw"] = s["text"]
        prev = None
        while prev != s["text"]:
            prev = s["text"]
            s["text"] = head.sub("", s["text"])
    return out


def profile_file(src, closed: dict) -> dict:
    """The occurrence profile of ANY VHDL file, given its closed set. Line numbers refer to that file."""
    src = Path(src); stem = src.stem
    L = masked_lines(src)
    S = SF.structures(L)
    STMTS = statements(L)
    rows = {}
    for e in closed["ports"] + closed["signals"]:
        n = e["name"]
        w = re.compile(rf"(?<![\w.]){re.escape(n)}(?![\w])")
        occ = []
        for ln, t in L.items():
            hits = len(w.findall(t))
            if not hits:
                continue
            ch = SF.chain(S, ln)
            kinds = [s["kind"] for s in ch]
            rs = roles(t, n)
            if kinds and kinds[-1] in ("port clause", "declarative part"):
                rs = ["declaration"]                       # a declaration, not a use
            elif "association list" in kinds:
                rs = sorted(set(rs) | {"port map"})        # connected to an instantiated sub-block
            # one entry per OCCURRENCE, not per line: a name can appear several times on one line
            here = [s for s in STMTS if s["first"] <= ln <= s["last"] and w.search(s["raw"])]
            for k in range(1, hits + 1):
                st = here[min(k - 1, len(here) - 1)] if here else None
                occ.append({"line": ln, "on_line": k, "roles": rs, "structure": SF.render(ch),
                            "innermost": kinds[-1] if kinds else None,
                            "in_branch": "branch" in kinds, "text": t.strip()[:120],
                            "statement_id": st["id"] if st else None,
                            "statement_lines": [st["first"], st["last"]] if st else None,
                            "statement": (st["text"] or st["raw"])[:400] if st else None,
                            # a condition sits in the control header, not in the statement body
                            "in_guard": bool(st and not w.search(st["text"]) and w.search(st["raw"])) if st else None,
                            "guard": st["raw"][:200] if st and not w.search(st["text"]) else None})
        rows[f"{e.get('entity', stem)}.{n}"] = {"entity": e.get("entity", stem), "name": n,
                                                "kind": "port" if "dir" in e else "signal",
                                                "occurrences": occ}
    return {"schema": "occurrence-profile-v1", "module": stem, "source": str(src),
            "built_by": "code (structure_finder + role regexes); no model", "elements": rows}


def selftest():
    """Assertions read by hand from RTL_data/neorv32_wdt.vhd (lines 90-144)."""
    d = profile_module("neorv32_wdt")
    get = lambda name: next(v for k, v in d["elements"].items() if v["name"] == name)
    ce = {o["line"]: o for o in get("ctrl.enable")["occurrences"]}
    assert "target" in ce[94]["roles"], ce[94]                       # 94: ctrl.enable <= bus_req_i.data(...)
    assert "read" in ce[109]["roles"], ce[109]                       # 109: bus_rsp_o.data(...) <= ctrl.enable
    assert "condition" in ce[131]["roles"], ce[131]                  # 131: if (ctrl.enable = '0') or ...
    assert "read" in ce[140]["roles"], ce[140]                       # 140: clkgen_en_o <= ctrl.enable
    for ln in (90, 91, 92, 93):                                      # the four ifs that enclose line 94
        assert f"if {ln}-" in ce[94]["structure"], (ln, ce[94]["structure"])
    assert "process" in ce[94]["structure"] and ce[94]["in_branch"]
    assert "process" not in ce[140]["structure"], ce[140]["structure"]   # 140 is concurrent, outside any process
    assert all(o["on_line"] >= 1 for o in get("ctrl.enable")["occurrences"])
    # line 95 writes ctrl.lock and reads ctrl.enable; line 130 reads cnt_started twice
    cs130 = [o for o in get("cnt_started")["occurrences"] if o["line"] == 130]
    assert len(cs130) == 2, cs130                        # cnt_started <= ctrl.enable and (cnt_started or prsc_tick)
    decl = [o for o in get("cnt")["occurrences"] if o["roles"] == ["declaration"]]
    assert decl, "the declaration of cnt should be tagged declaration"
    cnt = {o["line"]: o for o in get("cnt")["occurrences"]}
    # 133 is an elsif, so it opens a BRANCH of the if that started at 131, not a new if
    assert "target" in cnt[134]["roles"], cnt[134]
    assert "if 131-135" in cnt[134]["structure"] and "branch 133-134" in cnt[134]["structure"], cnt[134]
    cs = {o["line"]: o for o in get("cnt_started")["occurrences"]}
    assert "condition" in cs[144]["roles"], cs[144]                  # 144: when (cnt_started = '1') and ...
    print("selftest PASS: 10 assertions read by hand from RTL_data/neorv32_wdt.vhd")


def main():
    selftest()
    OUT.mkdir(exist_ok=True)
    tot_el = tot_occ = in_branch = 0
    roles_c, inner = Counter(), Counter()
    stems = sorted(p.stem for p in (ROOT / "step1/relation_map").glob("*.json"))
    for stem in stems:
        d = profile_module(stem)
        (OUT / f"{stem}.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
        for v in d["elements"].values():
            tot_el += 1
            for o in v["occurrences"]:
                tot_occ += 1; in_branch += o["in_branch"]
                roles_c.update(o["roles"]); inner[o["innermost"]] += 1
    print(f"wrote {len(stems)} files to {OUT}")
    print(f"elements {tot_el} | occurrences {tot_occ} | inside a branch {in_branch} "
          f"({in_branch/tot_occ if tot_occ else 0:.0%}) "
          f"<- the level the LLM got wrong on 264 of 408 branch entries")
    print(f"roles: {dict(roles_c.most_common())}")
    print(f"innermost structure: {dict(inner.most_common(8))}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
