"""Did the parse actually report what the RTL contains?

`parse_v3.report()` answers "is the output well-formed and did it stay on its side of the
line". This module answers a different and harder question: **is it right**. Every check
below compares the annotation against the RTL, so each one can fail even on a parse that
passes every format gate.

Five checks, each targeting a defect observed in a real run:

  1. GOVERNING COVERAGE      elements that appear in a condition but carry no governing edge.
                             Measured at ~50% on the first two parses.
  2. PROSE/EDGE CONSISTENCY  prose that says the element is tested, chooses or gates, with
                             no GATES/SELECTS/CONSTRAINS/OVERRIDES edge to match. The next
                             stage reads the edge, so the prose is what gets lost.
                             Observed on neorv32_cache:cache_i.sta_hit.
  3. CHAIN VISIBILITY        elements whose own target is compared or tested, where the
                             prose never mentions it. Edges are direct by design, so if the
                             prose does not carry the hop nothing does.
                             Observed on neorv32_cache:addr_i.
  4. FORWARDING CLASSIFIED   record fields assigned only by a whole-record copy, where the
                             annotation does not say ORIGINATES / CONSUMES / FORWARDS.
  5. EVIDENCE GROUNDED       evidence that cites no construct, so nothing supports the rest.

WHAT THIS IS NOT. It does not check whether an element is an asset, and it never reads the
reference. Every judgement here is annotation-against-source, so it can be run on a parse of
any design, including one with no ground truth. Keeping it that way is deliberate: a parse
quality metric that consulted the answer key would select parses that agree with the answers
rather than parses that describe the RTL.
"""
from __future__ import annotations

import glob
import json
import os
import re
from collections import Counter
from pathlib import Path

GOVERNING = ("GATES", "SELECTS", "CONSTRAINS", "OVERRIDES")

# Prose that asserts the element governs something. Deliberately narrow: these are verbs of
# decision, not of value flow. "drives" and "provides" are excluded because they describe
# sourcing, which is not a governing claim.
GOVERN_WORDS = ("tested", "tests", "checked", "checks", "compared", "compares",
                "chooses", "choose", "selects", "decides", "qualifies", "gates",
                "gating", "enables the", "governs", "determines whether", "when asserted")

# Prose that carries a hop onward: the element's target is itself used for something.
HOP_WORDS = ("that the", "which is then", "used to", "feeds the", "consumed by",
             "compared against", "tested by", "drives the comparison")


def _mask(path):
    from stage_a import _mask_comments
    return _mask_comments(Path(path).read_text(encoding="utf-8", errors="ignore"), vhdl=True)


def _conditions(src):
    """Text that is a CONDITION, nothing else. A VHDL condition contains no ';', so each
    pattern is bounded by [^;] -- otherwise `when` in a case alternative swallows the file."""
    out = []
    out += [m.group(1) for m in re.finditer(r"\b(?:els)?if\b([^;]*?)\bthen\b", src, re.I | re.S)]
    out += [m.group(1) for m in re.finditer(r"\bcase\b([^;]*?)\bis\b", src, re.I | re.S)]
    out += [m.group(1) for m in re.finditer(r"\bwhen\b([^;]*?)\belse\b", src, re.I | re.S)]
    return "\n".join(out)


def _whole_record_copies(src):
    """Base names assigned as a whole record: `x <= y;` where neither side is a field.
    A field of such a record, never named individually, is being forwarded."""
    out = set()
    for m in re.finditer(r"^\s*(\w+)\s*<=\s*(\w+)\s*;", src, re.M):
        out.add(m.group(1)); out.add(m.group(2))
    return out


def audit_module(stem, parse_dir="parsed_v3_tuning18", rtl_dir="RTL_data"):
    f = Path(parse_dir) / f"{stem}.json"
    src_f = Path(rtl_dir) / f"{stem}.vhd"
    if not (f.exists() and src_f.exists()):
        return None
    rec = json.loads(f.read_text(encoding="utf-8"))
    src = _mask(src_f)
    conds = _conditions(src)
    copies = _whole_record_copies(src)
    els = rec["ports"] + rec["signals"]
    out = {k: [] for k in ("gov_missing", "prose_edge", "chain_hidden",
                           "forward_unclassified", "evidence_thin")}
    n_cond = n_fieldcopy = 0
    for e in els:
        name = e["name"]
        prose = " ".join([e.get("functionality", ""), " ".join(e.get("role") or [])]).lower()
        ev = (e.get("evidence") or "").lower()
        edges = e.get("relationship") or []
        has_gov = any(r.get("type") in GOVERNING for r in edges)

        # 1. appears in a condition but no governing edge
        if re.search(rf"(?<![\w.]){re.escape(name)}(?![\w])", conds):
            n_cond += 1
            if not has_gov:
                out["gov_missing"].append(name)

        # 2. prose claims governance, edges do not
        if any(w in prose or w in ev for w in GOVERN_WORDS) and not has_gov:
            out["prose_edge"].append(name)

        # 3. the element's own target is compared/tested, and the prose does not say so
        for r in edges:
            if r.get("type") not in ("SOURCES", "DERIVES_FROM", "CAPTURES", "SLICES"):
                continue
            for tgt in r.get("targets") or []:
                if re.search(rf"(?<![\w.]){re.escape(str(tgt))}(?![\w])", conds):
                    if not any(w in prose for w in HOP_WORDS):
                        out["chain_hidden"].append(f"{name}->{tgt}")
                    break

        # 4. a field of a wholesale-copied record, with no originates/consumes/forwards call
        if "." in name and name.split(".")[0] in copies:
            n_fieldcopy += 1
            if not any(w in prose for w in ("forward", "consume", "originat")):
                out["forward_unclassified"].append(name)

        # 5. evidence naming no construct
        if not any(w in ev for w in ("<=", ":=", "process", "if ", "case", "when",
                                     "port map", "generate", "assign", "declar")):
            out["evidence_thin"].append(name)
    return {"module": stem, "n": len(els), "n_cond": n_cond,
            "n_fieldcopy": n_fieldcopy, **out}


def audit(parse_dir="parsed_v3_tuning18", rtl_dir="RTL_data", verbose=False):
    rows = [r for r in (audit_module(os.path.basename(f)[:-5], parse_dir, rtl_dir)
                        for f in sorted(glob.glob(f"{parse_dir}/*.json"))) if r]
    if not rows:
        print(f"no parse found in {parse_dir}/")
        return
    tot = Counter()
    N = sum(r["n"] for r in rows)
    NC = sum(r["n_cond"] for r in rows)
    NF = sum(r["n_fieldcopy"] for r in rows)
    for r in rows:
        for k in ("gov_missing", "prose_edge", "chain_hidden",
                  "forward_unclassified", "evidence_thin"):
            tot[k] += len(r[k])

    print(f"PARSE AUDIT — {parse_dir}   {len(rows)} modules, {N} elements\n")
    print(f"{'check':32} {'count':>7} {'of':>7}  what it means")
    print("-" * 96)
    print(f"{'1 in a condition, no gov edge':32} {tot['gov_missing']:7} {NC:7}  "
          f"the coupling the asset stage cannot rebuild")
    print(f"{'2 prose governs, edges do not':32} {tot['prose_edge']:7} {N:7}  "
          f"the governing claim is in the half that is not read")
    print(f"{'3 hop hidden from the prose':32} {tot['chain_hidden']:7} {N:7}  "
          f"target is tested; no record says so")
    print(f"{'4 forwarded field unclassified':32} {tot['forward_unclassified']:7} {NF:7}  "
          f"no originates/consumes/forwards call")
    print(f"{'5 evidence cites no construct':32} {tot['evidence_thin']:7} {N:7}  "
          f"nothing supports the other three")
    if NC:
        print(f"\ngoverning coverage {NC - tot['gov_missing']}/{NC} = "
              f"{100 * (NC - tot['gov_missing']) / NC:.0f}%")
    if verbose:
        for r in rows:
            hits = {k: r[k] for k in ("gov_missing", "prose_edge", "chain_hidden",
                                      "forward_unclassified") if r[k]}
            if hits:
                print(f"\n{r['module']}")
                for k, v in hits.items():
                    print(f"   {k:24} {v[:8]}{' ...' if len(v) > 8 else ''}")
    return tot


def compare(old_dir, new_dir="parsed_v3_tuning18", rtl_dir="RTL_data"):
    """Same five checks on two parses. Element counts are printed so a delta cannot be
    mistaken for a closed-set difference."""
    import io
    import contextlib
    res = {}
    for lbl, d in (("before", old_dir), ("after", new_dir)):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res[lbl] = audit(d, rtl_dir)
    if not all(res.values()):
        print("one of the parses is missing")
        return
    print(f"{'check':32} {'before':>8} {'after':>8} {'delta':>8}")
    for k in ("gov_missing", "prose_edge", "chain_hidden",
              "forward_unclassified", "evidence_thin"):
        a, b = res["before"][k], res["after"][k]
        print(f"{k:32} {a:8} {b:8} {b - a:+8}")
