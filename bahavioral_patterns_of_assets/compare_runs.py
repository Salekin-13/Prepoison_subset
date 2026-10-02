# -*- coding: utf-8 -*-
"""Compare two verifier runs.

    python compare_runs.py                  # the two most recent runs
    python compare_runs.py run_006 run_007  # a specific pair

Prints everything VERIFIER_ABLATION_LOG.md section 4 requires, and nothing it forbids.
In particular it prints NO pass/fail verdict and NO agreement threshold -- section 4
says thresholds are not to be invented, so this tool describes and you decide.

The question this is built to answer is section 5 rule R3:

    Not "is the agreement number high enough?"
    But  "did the specific finding I was about to act on stay on the SAME ELEMENTS?"

That is what the ERROR-TYPE STABILITY table at the end is for. Read that table first;
the agreement percentages above it are context, not the decision.

Anti-drift note: reading two finished runs to compare them is analysis, not evidence.
Nothing here is ever fed back into a model payload, so this does not touch the
section 5 R6 rule ("no prior verification result may enter a payload").
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent / "verification_results"


# --------------------------------------------------------------------------- keys
def norm_key(s):
    """Same normalisation as the notebook's _norm_key.

    The model reformats its own target strings between runs ("ISOLATED -> " one run,
    "ISOLATED -> (none)" the next). Joining on the raw string reports that as a
    disagreement. This folds pure formatting together -- and deliberately does NOT
    fold a merged target list or a dropped claim, because those are real coverage
    loss and must stay visible.
    """
    s = re.sub(r"\s+", " ", str(s or "")).strip().lower()
    if "->" in s:
        lhs, rhs = s.split("->", 1)
        # The parser NEVER puts parentheses in a target (verified: 0 of 68 targets in
        # neorv32_imem -- bit ranges live in a separate "bits" field). So any "(...)"
        # on the target side is the VERIFIER's own annotation: a bit range like
        # "(bits 7 downto 0)", or a placeholder like "(no targets)". It is not part of
        # the claim. Two runs differing only by whether the model volunteered a bit
        # range are making the same claim, and must join.
        rhs = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", rhs)
        rhs = re.sub(r"\b(none|n/a|null|no targets?|empty)\b", " ", rhs)
        tgts = sorted(t.strip() for t in re.split(r"[,;]", rhs) if t.strip())
        s = re.sub(r"\s+", " ", lhs).strip() + " -> " + "|".join(tgts)
    else:
        s = re.sub(r"\b(none|n/a|null)\b", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
    return s


# --------------------------------------------------------------------------- load
def load_run(name):
    d = ROOT / name
    if not d.exists():
        sys.exit(f"no such run: {d}")
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    flat = pd.read_csv(d / "claim_status.csv")
    flat["claim_key"] = flat["claim_key"].fillna("")
    flat["k"] = flat["claim_key"].map(norm_key)
    rows = []
    for p in sorted((d / "per_file").glob("*_verification.json")):
        rows += json.loads(p.read_text(encoding="utf-8"))
    return {"name": name, "manifest": man, "flat": flat, "rows": rows}


def latest_two():
    runs = sorted(p.name for p in ROOT.glob("run_*") if p.is_dir())
    if len(runs) < 2:
        sys.exit("need at least two runs to compare")
    return runs[-2], runs[-1]


# --------------------------------------------------------------------------- parts
def header(a, b):
    print("=" * 78)
    print(f"COMPARING  {a['name']}  ->  {b['name']}")
    print("=" * 78)
    fields = [
        ("run_tag", lambda m: m.get("run_tag", "<absent>")),
        ("verifier", lambda m: m.get("verifier_prompt_version")),
        ("prompt sha", lambda m: (m.get("verifier_prompt_sha256") or "")[:16]),
        ("parser", lambda m: m.get("parser_prompt_version")),
        ("model", lambda m: m["llm"]["model"]),
        ("effort", lambda m: m["llm"].get("reasoning_effort")),
        ("max_out", lambda m: m["llm"].get("max_output_tokens")),
        ("elements", lambda m: m["counts"]["elements_verified"]),
        ("parse ok", lambda m: m["counts"]["parse_ok"]),
        ("escalations", lambda m: m["counts"].get("budget_escalations")),
        ("calls", lambda m: m["usage_and_cost"]["calls"]),
        ("usd", lambda m: m["usage_and_cost"]["usd"]),
    ]
    print(f"{'':16s} {a['name']:>22s}   {b['name']:>22s}")
    for label, fn in fields:
        va, vb = fn(a["manifest"]), fn(b["manifest"])
        mark = "" if va == vb else "   <-- differs"
        print(f"  {label:14s} {str(va):>22s}   {str(vb):>22s}{mark}")

    for r in (a, b):
        if r["manifest"]["usage_and_cost"]["calls"] == 0:
            print(f"\n  !! {r['name']} made ZERO API calls -- it is a cache replay, not an")
            print(f"     independent observation. Comparing against it measures the cache.")
    print()


def agreement(a, b):
    ka = a["flat"].copy()
    kb = b["flat"].copy()
    # pandas merges duplicate keys as a CROSS PRODUCT. An element that legitimately
    # carries the same (field, normalised key) twice would pair every copy in A against
    # every copy in B, inventing status transitions that neither run produced. An
    # occurrence index pairs first-with-first and leaves genuine extras unmatched.
    for _d in (ka, kb):
        _d["occ"] = _d.groupby(["element_id", "field", "k"]).cumcount()
    m = ka.merge(kb, on=["element_id", "field", "k", "occ"], suffixes=("_a", "_b"),
                 how="outer", indicator=True)
    both = m[m._merge == "both"]
    agree = int((both.status_a == both.status_b).sum())

    print("-" * 78)
    print("CLAIM-LEVEL AGREEMENT   (joined on the normalised key)")
    print("-" * 78)
    print(f"  claims joined      : {len(both)}")
    print(f"  same status        : {agree}")
    print(f"  changed status     : {len(both) - agree}")
    print(f"  agreement          : {agree/max(1,len(both)):.1%}")
    print(f"  did NOT join       : {len(m) - len(both)}   (coverage difference, see below)")

    ov = both.groupby("element_id")[["overall_a", "overall_b"]].first()
    same_el = int((ov.overall_a == ov.overall_b).sum())
    print()
    print("ELEMENT-LEVEL AGREEMENT (the verifier's overall verdict per element)")
    print(f"  elements compared  : {len(ov)}")
    print(f"  same overall       : {same_el}  ({same_el/max(1,len(ov)):.1%})")
    print("  NOTE: this and the claim number answer different questions and can")
    print("        diverge sharply. Report both, never one alone.")

    print()
    print("PER-FIELD AGREEMENT")
    for fld, grp in both.groupby("field"):
        n = len(grp)
        ag = int((grp.status_a == grp.status_b).sum())
        print(f"  {fld:16s} {ag:4d}/{n:<4d} = {ag/max(1,n):6.1%}")

    ch = both[both.status_a != both.status_b]
    print()
    print("TRANSITION MATRIX  (changed claims only)")
    if len(ch):
        for (sa, sb), n in ch.groupby(["status_a", "status_b"]).size().items():
            print(f"  {sa:22s} -> {sb:22s} {n:4d}")
    else:
        print("  (no status changed)")

    print()
    print("CLAIMS THAT DID NOT JOIN  (present in one run, absent in the other)")
    nj = m[m._merge != "both"]
    if len(nj):
        print("  These are coverage differences, not formatting -- the normaliser already")
        print("  folded formatting together. A claim here was DROPPED or MERGED by one run.")
        for _, r in nj.iterrows():
            el = r.element_a if isinstance(r.element_a, str) else r.element_b
            mod = r.module_a if isinstance(r.module_a, str) else r.module_b
            side = a["name"] if r._merge == "left_only" else b["name"]
            st = r.status_a if r._merge == "left_only" else r.status_b
            print(f"    only in {side:9s}  {str(mod)[:18]:18s} {str(el):20s} "
                  f"{str(r.k)[:40]:40s} {st}")
    else:
        print("  (none -- both runs returned the same set of claims)")
    print()
    return both, ch


def _parsed_claims():
    """Load the parser's own claims, so coverage can be recomputed for runs that
    predate the claim_coverage instrumentation. Returns {(entity, name): record}."""
    d = Path(__file__).resolve().parent / "data" / "parsed_v3_tuning18"
    out = {}
    for p in sorted(d.glob("*.json")):
        j = json.loads(p.read_text(encoding="utf-8"))
        for bucket in ("ports", "signals"):
            for e in j.get(bucket) or []:
                if isinstance(e, dict) and "entity" in e and "name" in e:
                    out[(e["entity"], e["name"])] = e
    return out


def _recompute_coverage(rows, claims):
    """Same arithmetic as the notebook's claim_coverage(). Returns
    (incomplete_elements, pairs_lost) or (None, None) if the claims are unavailable."""
    if not claims:
        return None, None
    inc = lost = 0
    for r in rows:
        e = claims.get((r.get("entity"), r.get("element")))
        if not e:
            continue
        v = r.get("verification") or {}
        exp_roles = len(e.get("role") or [])
        got_roles = len(v.get("role_checks") or [])
        exp_rels = sum(max(1, len(x.get("targets") or []))
                       for x in (e.get("relationship") or []))
        got_rels = len(v.get("relationship_checks") or [])
        if exp_roles != got_roles or exp_rels != got_rels:
            inc += 1
        lost += max(0, exp_rels - got_rels)
    return inc, lost


def coverage(a, b):
    print("-" * 78)
    print("CLAIM COVERAGE   (did the verifier return one check per parser claim?)")
    print("-" * 78)
    print("  Section 5 R5: if claims went missing, EVERY count in that run is over a")
    print("  subset, and that must be stated before any pattern number is quoted.")
    claims = _parsed_claims()
    for r in (a, b):
        c = r["manifest"]["counts"]
        inc, lost = c.get("claim_coverage_incomplete"), c.get("rel_pairs_lost_to_merging")
        if inc is not None:
            print(f"  {r['name']:10s} incomplete elements: {inc:3d}   "
                  f"(type,target) pairs lost: {lost:3d}   [from manifest]")
            continue
        # Run predates the instrumentation. Recompute from the parser's claims --
        # do NOT fall back to the absent field, which would silently report 0 and
        # turn "not measured" into "measured, and clean".
        inc, lost = _recompute_coverage(r["rows"], claims)
        if inc is None:
            print(f"  {r['name']:10s} incomplete elements: UNKNOWN -- not recorded in the "
                  f"manifest and the parsed claims could not be loaded to recompute it.")
        else:
            print(f"  {r['name']:10s} incomplete elements: {inc:3d}   "
                  f"(type,target) pairs lost: {lost:3d}   [recomputed -- run predates "
                  f"the instrumentation]")
    print()


def error_stability(a, b):
    """The section 5 R3 test, and the reason this script exists.

    For each error category: is it landing on the SAME ELEMENTS in both runs, or
    just on the same NUMBER of elements? A stable count with an unstable element
    set is the dangerous case -- the aggregate looks reproducible while the
    attribution is not, and a parser-prompt edit written from it is written on noise.
    """
    # Key on element_id, NEVER on the bare name. 507 of 1689 elements (30.0%) share
    # a name with an element in another entity -- clk_i occurs in 26 entities, rstn_i
    # in 24 -- so a name-keyed set silently merges unrelated elements and the shared /
    # only-A / only-B counts are computed over a 1355-key universe instead of 1689.
    def by_type(rows):
        d = defaultdict(set)
        for r in rows:
            for e in ((r.get("verification") or {}).get("errors") or []):
                if e.get("error_type"):
                    d[e["error_type"]].add(r["element_id"])
        return d

    def labels(*rowsets):
        """element_id -> module/entity/element, so printed lists are unambiguous."""
        out = {}
        for rows in rowsets:
            for r in rows:
                out[r["element_id"]] = f"{r['module']}/{r['entity']}/{r['element']}"
        return out

    LBL = labels(a["rows"], b["rows"])
    lbl = lambda i: LBL.get(i, i)

    da, db = by_type(a["rows"]), by_type(b["rows"])
    types = sorted(set(da) | set(db))

    print("=" * 78)
    print("ERROR-TYPE STABILITY   <-- READ THIS FIRST. This is the decision.")
    print("=" * 78)
    print("  For each category: how many ELEMENTS carry it in each run, and are they")
    print("  the same elements? Same count + different elements = do NOT act on it.")
    print()
    print(f"  {'error type':32s} {a['name']:>9s} {b['name']:>9s} {'shared':>7s} "
          f"{'only A':>7s} {'only B':>7s}")
    print("  " + "-" * 74)
    for t in types:
        sa, sb = da.get(t, set()), db.get(t, set())
        print(f"  {t:32s} {len(sa):>9d} {len(sb):>9d} {len(sa & sb):>7d} "
              f"{len(sa - sb):>7d} {len(sb - sa):>7d}")

    print()
    print("  Elements that moved, per category:")
    any_move = False
    for t in types:
        sa, sb = da.get(t, set()), db.get(t, set())
        gone, new = sorted(lbl(x) for x in sa - sb), sorted(lbl(x) for x in sb - sa)
        if not gone and not new:
            continue
        any_move = True
        print(f"    {t}")
        if gone:
            print(f"       dropped in {b['name']}: {', '.join(gone)}")
        if new:
            print(f"       appeared in {b['name']}: {', '.join(new)}")
    if not any_move:
        print("    (every category landed on exactly the same elements in both runs)")

    print()
    print("  Elements whose ERROR SET changed at all:")
    ea = {r["element_id"]: {e.get("error_type")
                            for e in ((r.get("verification") or {}).get("errors") or [])}
          for r in a["rows"]}
    eb = {r["element_id"]: {e.get("error_type")
                            for e in ((r.get("verification") or {}).get("errors") or [])}
          for r in b["rows"]}
    moved = sorted(k for k in set(ea) | set(eb) if ea.get(k, set()) != eb.get(k, set()))
    print(f"    {len(moved)} of {len(set(ea) | set(eb))} elements")
    for k in moved:
        print(f"      {lbl(k)}")
        print(f"          {sorted(ea.get(k, set())) or '[]'}")
        print(f"       -> {sorted(eb.get(k, set())) or '[]'}")
    print()


def closing():
    print("=" * 78)
    print("HOW TO DECIDE  (VERIFIER_ABLATION_LOG.md section 5, R3)")
    print("=" * 78)
    print("""
  Do NOT read the agreement percentage and ask "is that high enough?" There is no
  threshold and section 4 forbids inventing one after the fact.

  Instead:

    1. Name the finding you were about to act on.
       Right now that is CONDITIONAL_BEHAVIOR_ERROR -- it carried 12 of 27 elements
       in run_006 and is the only pattern big enough to justify a parser-prompt edit.

    2. In the ERROR-TYPE STABILITY table, find that category and look at 'shared'
       against 'only A' / 'only B'.

    3. Decide:
         mostly the same elements ......... the finding is solid; write the edit
         same count, different elements ... STOP. The aggregate is reproducible but
                                            the attribution is not. You cannot write
                                            a prompt fix from this. Repeat the module,
                                            or move that category to majority-of-3.
         count swings a lot ............... the pattern is not established; do not act

    4. Record the ELEMENT NAMES in the log, not just the percentage.

  And if coverage was incomplete in either run, say so before quoting any number
  from it -- those counts are over a subset (R5).
""")


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("-")]
    if len(args) == 2:
        na, nb = args
    elif not args:
        na, nb = latest_two()
        print(f"(no runs given; using the two most recent: {na}, {nb})\n")
    else:
        sys.exit(__doc__)

    a, b = load_run(na), load_run(nb)
    header(a, b)
    agreement(a, b)
    coverage(a, b)
    error_stability(a, b)
    closing()


if __name__ == "__main__":
    main()
