"""Code-only SITE tagging for any VHDL file: the last field the model was still supplying.

The occurrence profile already comes from code (step1/occurrence_profile.py): every occurrence, its line, what the
element does there, and the chain of enclosing structures with spans. Of the five fields the classify prompt asks for
("Occurrence ID", "Occurrence Lines", "Structure", "Role", "SITE Tagged"), only the SITE tags were model-only.

Most SITEs in the rulebook are defined by structure and position, which the profile already records, so they can be
read off the source. Each rule below quotes the rulebook's own trigger
(bahavioral_patterns_of_assets/annotation_pack_elements/occurrence_prompts_v2/rulebook.json).

WHAT THIS IS FOR
  - supplement: fill the occurrences the model never answered (76 of 1065 in the first run, mostly clock and reset
    positions and declarations);
  - check: compare code tags with the model's on the occurrences it did answer, per SITE (validate());
  - any file: tag_file() takes any .vhd path and needs no cached closed set.

WHAT IT DOES NOT DO: the Role sentence (prose), and the SITEs that need judgement rather than position. An occurrence
the rules do not cover gets an empty list and is counted as "not covered", never guessed.

Usage:
    python step1/site_tagger.py RTL_data/neorv32_wdt.vhd     # tag one file, print a summary
    python step1/site_tagger.py --validate                   # code tags vs the model's answers, per SITE
"""
from __future__ import annotations

import json, re, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
import occurrence_profile as OP   # noqa: E402
import rtl_parse                  # noqa: E402

IF_COND_RE = re.compile(r"\b(?:if|elsif)\b(?P<e>.*?)\bthen\b", re.I)
CASE_EXPR_RE = re.compile(r"\bcase\b(?P<e>.*?)\bis\b", re.I)
CASE_ALT_RE = re.compile(r"\bwhen\b(?P<e>[^=]*?)=>", re.I)
WHEN_ELSE_RE = re.compile(r"\bwhen\b(?P<e>.*?)\belse\b", re.I)
EDGE_RE = re.compile(r"\b(?:rising_edge|falling_edge)\s*\((?P<e>[^)]*)\)", re.I)
SENS_RE = re.compile(r"\bprocess\s*\((?P<e>[^)]*)\)", re.I)
VAR_ASSIGN = re.compile(r":=")
SIG_ASSIGN = re.compile(r"<=")


def _in(expr: str | None, name: str) -> bool:
    return bool(expr) and re.search(rf"(?<![\w.]){re.escape(name)}(?![\w])", expr) is not None


def sites_for(name: str, kind: str, occ: dict, text: str) -> list[str]:
    """The SITEs of one occurrence, from its position in the line and its enclosing structures.

    Precedence follows the rulebook's own triggers, which an earlier version of this function got wrong on reads:
      DIRR_ASS   the element IS the whole right-hand side: no operator, no index, no range, no other name.
      RHS_OPERAND the element is joined to something else by an operator, on a NON-conditional assignment.
      WHEN_EXPR  the element is in the value expression of a conditional assignment (not in its condition).
      INDEXED_NAME / PART_SELECT / INDEX / ATTR_PREFIX are ADD-ONS, and where no primary applies they stand alone.
      FIELD_USE  a record base reaching one of its fields takes FIELD_USE and nothing else from that occurrence.
    """
    roles, chain = occ["roles"], occ["structure"]
    in_process = "process" in chain
    after = text.split(name, 1)[1] if name in text else ""
    before = text.split(name, 1)[0] if name in text else ""
    add = []
    if re.match(r"\s*\(", after):
        inner = after.strip()[1:]
        add.append("PART_SELECT" if re.match(r"[^)]*\b(downto|to)\b", inner, re.I) else "INDEXED_NAME")
    if re.match(r"\s*'", after):
        add.append("ATTR_PREFIX")
    if re.search(r"[A-Za-z_]\w*\s*\([^()]*$", before):           # inside another name's parentheses: a position
        add.append("INDEX")
    if re.match(r"\s*\.", after) and "." not in name:
        return ["FIELD_USE"]

    if "declaration" in roles:
        return (["DECL_FIELD"] if "." in name else ["DECL_PORT" if kind == "port" else "DECL_SIGNAL"]) + add
    for m in EDGE_RE.finditer(text):
        if _in(m.group("e"), name):
            return ["EDGE_CHECK"] + add
    for m in SENS_RE.finditer(text):
        if _in(m.group("e"), name):
            return ["PROCESS_TRIG"] + add
    for rx, site in ((IF_COND_RE, "IF_COND"), (CASE_EXPR_RE, "CASE_EXPR"),
                     (CASE_ALT_RE, "CASE_COND"), (WHEN_ELSE_RE, "WHEN_COND")):
        for m in rx.finditer(text):
            if _in(m.group("e"), name):
                return [site] + add
    if "port map" in roles:
        return ["ASSOC_ACTUAL"] + add
    if "target" in roles:
        return (["LHS_PROC"] if in_process else ["LHS_CONC"]) + add
    if "read" in roles:
        op, sig = VAR_ASSIGN.search(text), SIG_ASSIGN.search(text)
        if op and (not sig or op.start() < sig.start()):
            return ["VAR_RHS_OPERAND"] + add
        if not sig:
            return add
        rhs = text[sig.end():].rstrip(" ;")
        if re.search(r"\bwhen\b.*?\belse\b", rhs, re.I) or re.search(r"\bwhen\b", rhs, re.I):
            return ["WHEN_EXPR"] + add                            # a conditional assignment's value expression
        if rhs.strip() == name:                                   # the whole right-hand side, nothing else
            return ["DIRR_ASS"] + add
        if re.search(r"[+\-*/&=<>]|\b(and|or|xor|nand|nor|not|sll|srl|rol|ror|mod|rem)\b", rhs, re.I):
            return ["RHS_OPERAND"] + add
        return add or ["RHS_OPERAND"]                             # e.g. dev_req(27): the add-on stands alone
    return add


def tag_file(path: str | Path, closed: dict | None = None) -> dict:
    """Occurrence profile with SITE tags for ANY VHDL file. No cached closed set needed, no model."""
    path = Path(path)
    if closed is None:
        cached = ROOT / f"parsed_tuning18/{path.stem}.json"
        if cached.exists():
            closed = json.loads(cached.read_text(encoding="utf-8"))
        else:                                                    # parse it here, expanding record types
            records = rtl_parse.build_record_registry(sorted(path.parent.glob("*.vhd")))
            p = rtl_parse.parse_rtl_file(str(path), records)
            ports = [{"entity": e["entity"], **x} for e in p["entities"] for x in e.get("ports", [])]
            signals = [{"entity": e["entity"], **x} for e in p["entities"] for x in e.get("signals", [])]
            closed = {"module": path.stem, "entities": [e["entity"] for e in p["entities"]],
                      "ports": ports, "signals": signals}
    prof = OP.profile_file(path, closed)
    L = OP.masked_lines(path)
    for v in prof["elements"].values():
        for o in v["occurrences"]:
            o["sites"] = sites_for(v["name"], v["kind"], o, L[o["line"]])
            # a continuation line of a multi-line assignment or condition carries no '<=' and no 'if..then', so the
            # line alone decides nothing; the statement this occurrence belongs to does. 190 of 17,357 occurrences.
            if not o["sites"] and (o["guard"] or o["statement"]):
                o["sites"] = sites_for(v["name"], v["kind"], o, o["guard"] or o["statement"])
    prof["built_by"] = "code (structure_finder + role and SITE rules); no model"
    return prof


def validate(model_dir=ROOT / "step1/occ_llm_out") -> dict:
    """Code tags against the model's, on the occurrences the model answered. Per SITE: agree / differ."""
    agree, differ, by_site, missed_by_model = Counter(), Counter(), Counter(), Counter()
    cache: dict[str, dict] = {}
    for f in sorted(p for p in Path(model_dir).glob("*.json") if not p.name.endswith(".raw.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        prof = cache.setdefault(d["module"], tag_file(ROOT / f"RTL_data/{d['module']}.vhd"))
        idx = {(v["name"], i): o for v in prof["elements"].values()
               for i, o in enumerate(v["occurrences"], 1)}
        for e in d["entries"]:
            o = idx.get((e["Element"], e["Occurrence ID"]))
            if o is None:
                continue
            code = [s for s in o["sites"]]
            if e["Role"] is None:                     # the model never answered this one
                missed_by_model["covered by code" if code else "not covered"] += 1
                continue
            model = [str(x).strip().upper() for x in (e["SITE Tagged"] or [])]
            primary_c = code[0] if code else None
            by_site[primary_c or "(none)"] += 1
            if primary_c and primary_c in model:
                agree[primary_c] += 1
            else:
                differ[(primary_c or "(none)", ",".join(model) or "(none)")] += 1
    return {"agree": agree, "differ": differ, "by_site": by_site, "missed_by_model": missed_by_model}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--validate" in sys.argv:
        r = validate()
        tot = sum(r["by_site"].values()); ok = sum(r["agree"].values())
        print(f"occurrences the model answered and code also tagged: {tot}; primary SITE agrees on {ok} ({ok/max(tot,1):.0%})")
        print(f"{'SITE (code)':18s} {'n':>5s} {'agree':>6s} {'rate':>6s}")
        for s, n in r["by_site"].most_common():
            print(f"{s:18s} {n:5d} {r['agree'][s]:6d} {r['agree'][s]/n:6.0%}")
        print("\nmost common disagreements (code -> model):")
        for (c, m), n in r["differ"].most_common(8):
            print(f"   {n:4d}  {c:16s} -> {m}")
        print(f"\noccurrences the model never answered: {dict(r['missed_by_model'])}")
    else:
        for p in [a for a in sys.argv[1:] if a.endswith(".vhd")] or ["RTL_data/neorv32_wdt.vhd"]:
            prof = tag_file(p)
            c = Counter(s for v in prof["elements"].values() for o in v["occurrences"] for s in (o["sites"] or ["(none)"]))
            n = sum(len(v["occurrences"]) for v in prof["elements"].values())
            out = HERE / "occurrence_profiles_tagged" / f"{Path(p).stem}.json"
            out.parent.mkdir(exist_ok=True)
            out.write_text(json.dumps(prof, indent=1), encoding="utf-8")
            print(f"{p}: {len(prof['elements'])} elements, {n} occurrences -> {out}")
            print("   ", dict(c.most_common()))
