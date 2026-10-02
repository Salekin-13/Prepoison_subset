"""Stage C substage -- T-1: split every miss into conception failure vs binding failure.

    (a) STEP 1 failure -- the conceptual asset was never conceived
    (b) STEP 2 failure -- conceived, but never bound to its element

There is NO conceptual-asset reference to score against. `manual_gt`'s `raw_cell` groups
elements that the annotator wrote in one spreadsheet cell under one shared `why`, which is
the right shape, but it is 75 singletons out of 90 concepts -- too thin to be the reference.
`lasset_initial`'s `asset_name` labels the structural element, not a concept.

So classification is a judgement. Once v01c4 is running the PRIMARY reading comes from the
model's own emitted concept list -- see split_misses() -- because that is the only source
that says what the model actually conceived. The sibling and secondary rules
(corroborating_evidence) are what you use when you cannot see that list, and afterwards they
serve as a cross-check: a miss the judge calls "not conceived" while a same-cell sibling was
emitted is the case to read by hand.

  PRIMARY      split_misses()          reads the model's ConceptualAssets
    strong (a)   objective absent from the concept list -- deterministic, non-circular
    weak   (a)   judge finds no covering concept
           (b)   judge finds one
  CROSS-CHECK  corroborating_evidence()
    sibling      a same-raw_cell element was emitted -> (b), STRONG but not proof:
                 raw_cell is the annotator's spreadsheet grouping, not a validated concept
                 boundary, so a found sibling shows the model reached something the
                 ANNOTATOR bundled with the miss
    secondary    an element in the `secondary` graph was emitted -> (b), suggestive only,
                 and worthless without the hub cutoff

TWO STANDING CAVEATS.
  * ASYMMETRY. (b) is sound -- a covering concept is present, so the model reached it and
    failed to bind. (a) is always weaker: absence from the emitted list is not proof of
    absence from the model's reasoning. Never present them as symmetric.
  * THE JUDGE DECIDES THE ANSWER. With a stub that always picks a concept the split reads
    100% (b); with one that always answers NONE it reads 100% (a). calibrate_judge() on
    FOUND references is therefore mandatory, and no (a)/(b) number is reportable without
    its agreement rate beside it.

This module is a DIAGNOSTIC. Its output classifies misses; it is not a metric to optimise,
and no arm should be accepted or rejected on it.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import eval_assets as EA

# Resolved against this file, not the working directory. A cwd-relative default silently
# raises FileNotFoundError from any caller that is not sitting in the repo root, which for a
# diagnostic that gets driven from scratch scripts is a guaranteed trip hazard.
_HERE = Path(__file__).resolve().parent
GT_DIR = _HERE / "ground_truth"
PARSED_DIR = _HERE / "parsed_tuning18"


# --------------------------------------------------------------------------- loading
def load_concept_runs(assets_dir) -> dict:
    """-> {module: {"concepts": {id: {...}}, "assets": [(entity, name, objective, concept_id)]}}

    Tolerates a directory produced by a version that does NOT emit concepts: `concepts` is
    then empty and every asset carries concept_id None. That keeps the loader usable for
    back-comparison against v01c3 without a second code path.
    """
    out = {}
    for f in sorted(Path(assets_dir).glob("*.json")):
        if f.name.startswith("_"):
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        concepts = {}
        for c in d.get("ConceptualAssets", []) or []:
            cid = str(c.get("id") or "").strip()
            if cid:
                concepts[cid] = {
                    "concept": c.get("Concept", ""),
                    "objective": EA._obj(c.get("Security Objective", "")),
                    "why": c.get("Why", ""),
                }
        assets = [(a.get("Entity", ""), a["Asset RTL"], a.get("Security Objective", ""),
                   str(a.get("Concept") or "").strip() or None)
                  for a in d.get("Assets", []) if a.get("Asset RTL")]
        out[f.stem] = {"concepts": concepts, "assets": assets}
    return out


def validate_concepts(result: dict, expect_concepts: bool = False) -> list:
    """Structural checks for the T-1 contract.

    A dangling `Concept` id is the failure that would quietly destroy this arm: the (a)/(b)
    split is read off the concept->element mapping, so an id resolving to nothing turns a
    binding failure into an unclassifiable one.

    expect_concepts=False keeps this a no-op for versions that do not ask for concepts, so
    the run loop needs no version branching. But that tolerance is exactly what let v01c4
    print [ok] for 90 module-repeats while emitting ZERO ConceptualAssets -- a default that
    silently accepted the thing it was built to catch. Pass True whenever the prompt asks
    for the array and the missing-array case becomes a loud failure.
    """
    cs = result.get("ConceptualAssets")
    if cs is None:
        return ["ConceptualAssets missing entirely -- the prompt asked for it"] \
            if expect_concepts else []
    issues, ids = [], set()
    OBJ = {"Confidentiality", "Integrity", "Availability"}
    for i, c in enumerate(cs):
        cid = str(c.get("id") or "").strip()
        if not cid:
            issues.append(f"ConceptualAssets[{i}] has no id")
            continue
        if cid in ids:
            issues.append(f"duplicate concept id '{cid}'")
        ids.add(cid)
        if not (c.get("Concept") or "").strip():
            issues.append(f"concept '{cid}' has empty Concept text")
        if c.get("Security Objective") not in OBJ:
            issues.append(f"concept '{cid}': bad objective {c.get('Security Objective')!r}")
    for a in result.get("Assets", []):
        ref = str(a.get("Concept") or "").strip()
        if not ref:
            issues.append(f"asset '{a.get('Asset RTL')}' has no Concept id")
        elif ref not in ids:
            issues.append(f"asset '{a.get('Asset RTL')}' -> unknown concept '{ref}'")
    if not cs:
        issues.append("ConceptualAssets is empty")
    return issues


# ----------------------------------------------------------------- concept partitions
def raw_cell_groups(mods) -> tuple:
    """(concept_of, members) from manual_gt's raw_cell -- the annotator's own grouping."""
    raw = json.loads((GT_DIR / "manual_gt_neorv32.json").read_text(encoding="utf-8"))
    concept_of, members = {}, defaultdict(list)
    for m, v in raw["modules"].items():
        if m not in mods:
            continue
        for a in v["assets"]:
            cid = (m, (a.get("raw_cell") or a["element"]).strip())
            concept_of[(m, a["element"])] = cid
            members[cid].append(a["element"])
    return concept_of, dict(members)


def secondary_graph(mods, hub_cutoff: int = 4) -> dict:
    """{(module, element): {related elements}} from lasset_initial's `secondary` lists.

    Undirected: if B is listed under A, A is treated as related to B as well. The paper
    populates this on 358 of 359 assets, so it reaches further than raw_cell does.

    HUB CUTOFF IS NOT OPTIONAL COSMETICS. Without it this tier is near-vacuous. In-degree
    runs to 29 (`uart.ctrl.enable`), 20 (`cpu_cp_muldiv.ctrl.rs1_is_signed`), 15
    (`cpu.ctrl`) -- elements that half the module names as an influencer and that the model
    emits almost every run. Matching on those would score "concept reached" for practically
    any miss. Measured: with hubs counted, this tier claims 61.7% of misses and 81% of those
    verdicts rest on a hub; with in-degree >= 4 dropped it claims 22.5%. The larger number
    is an artefact. Pass hub_cutoff=None to reproduce it, never to report it.
    """
    d = json.loads((GT_DIR / "lasset_initial.json").read_text(encoding="utf-8"))
    g = defaultdict(set)
    for m, v in d.get("modules", {}).items():
        if m not in mods:
            continue
        for a in v.get("assets", []):
            e = a.get("element")
            for s in a.get("secondary") or []:
                g[(m, e)].add(s)
                g[(m, s)].add(e)
    if hub_cutoff is None:
        return dict(g)
    indeg = Counter()
    for (m, _e), rel in g.items():
        for r in rel:
            indeg[(m, r)] += 1
    return {k: {r for r in rel if indeg[(k[0], r)] < hub_cutoff} for k, rel in g.items()}


# -------------------------------------------------------------------- classification
# Ordered by confidence. Tier 1 is strong but NOT proof (see the module docstring); tier 2
# is suggestive even after the hub cutoff. Tiers 3 and 4 are the judge's pool and together
# they are the MAJORITY of misses (~54%), which is the reason the judge is the primary
# instrument here rather than the mop-up.
#
# CORROBORATION ONLY -- these are NOT verdicts once v01c4 is running. They infer "was the
# concept reached" from what happened to be emitted nearby, which is what you do when you
# cannot see the model's concepts. v01c4 makes them visible, so the primary reading comes
# from the emitted concept list and these become a cross-check on the judge. Tier 1 was
# previously labelled "certain" here and that was wrong: raw_cell is the annotator's
# spreadsheet grouping, not a validated concept boundary. The wdt cell
# "ctrl.enable, ctrl.lock, ctrl.timeout" carries one `why` that reads as being about
# ctrl.enable alone -- typing convenience with a rationale skewed to one member. A found
# sibling shows the model reached something the ANNOTATOR bundled with the miss, not that
# it conceived the miss's concept. Strong evidence, not proof.
TIERS = ("sibling: concept reached (b)", "secondary: concept reached (b)",
         "unresolved -> judge", "solo, nothing emitted nearby")

# Primary verdicts, read off the model's own concept list.
#
# ASYMMETRIC BY CONSTRUCTION. A (b) verdict is sound: a concept covering the element is
# present, so the model reached it and failed to bind. An (a) verdict is always weaker --
# absence from the emitted list is not proof the model never conceived it, because STEP 1
# was internal until this arm and the model may conceive without reporting. Never present
# (a) and (b) as symmetric findings.
V_A_STRONG = "(a) not conceived -- objective absent from the concept list"
V_A_WEAK = "(a) not conceived -- judge finds no covering concept"
V_B = "(b) conceived but unbound -- a concept covers it"
V_UNRESOLVED = "unresolved -- no judge supplied"
V_NO_LIST = "UNCLASSIFIABLE -- module emitted no concept list"
VERDICTS = (V_B, V_A_STRONG, V_A_WEAK, V_UNRESOLVED, V_NO_LIST)


def corroborating_evidence(run, reference, mods=None, concept_of=None, members=None,
                           graph=None):
    """Sibling / secondary cross-check. Returns (rows, Counter).

    Usable on a pre-v01c4 run, where it is all there is. On a v01c4 run it exists to
    disagree with the judge -- a miss the judge calls (a) while a same-cell sibling was
    emitted is the case worth reading by hand.
    """
    res = EA.score(run, reference, only=mods)
    pred = EA.load_run(run) if not isinstance(run, dict) else EA._as_run(run)
    if concept_of is None:
        concept_of, members = raw_cell_groups(set(res["per_module"]))
    if graph is None:
        graph = secondary_graph(set(res["per_module"]))

    rows, tally = [], Counter()
    for m, d in res["per_module"].items():
        emitted = {n for _e, n, *_ in pred.get(m, [])}
        for e in d["fn"]:
            cid = concept_of.get((m, e))
            sibs = [x for x in members.get(cid, []) if x != e]
            rel = graph.get((m, e), set())
            if any(x in emitted for x in sibs):
                t = TIERS[0]
            elif any(x in emitted for x in rel):
                t = TIERS[1]
            elif sibs or rel:
                t = TIERS[2]
            else:
                t = TIERS[3]
            tally[t] += 1
            rows.append({"module": m, "element": e, "tier": t,
                         "siblings": sibs, "related": sorted(rel)[:6]})
    return rows, tally


# Kept so pre-v01c4 callers do not break; the name now says what it actually does.
classify_misses = corroborating_evidence


# ------------------------------------------------------------------------ the judge
JUDGE_SYSTEM = (
    "You decide whether a hardware design element is an instance of one of a given list of "
    "conceptual security assets. Answer with the single best matching concept id, or the "
    "word NONE if no concept in the list describes the data or system state that this "
    "element carries, stores or gates. Answer with the id or NONE and nothing else."
)


def judge_user(module, element, function, concepts):
    lines = [f"MODULE: {module}", f"ELEMENT: {element}",
             f"WHAT IT DOES: {function or '(no description available)'}", "", "CONCEPTS:"]
    for cid, c in concepts.items():
        lines.append(f"  {cid}: {c['concept']}  [{c['objective']}]")
    lines.append("")
    lines.append("Which concept id does this element realise? Answer with the id, or NONE.")
    return "\n".join(lines)


def make_judge(call):
    """call(system, user) -> str.  Returns judge(module, element, function, concepts) -> id|None.

    Deliberately BLIND: the judge is never told whether the element was found or missed, nor
    which concept the model itself linked it to. The same call is used for calibration and
    for classification, so the two are directly comparable.
    """
    def judge(module, element, function, concepts):
        if not concepts:
            return None
        raw = (call(JUDGE_SYSTEM, judge_user(module, element, function, concepts)) or "").strip()
        tok = raw.split()[0].strip(".,:;\"'") if raw.split() else "NONE"
        return tok if tok in concepts else None
    return judge


def calibrate_judge(concept_run, reference, parsed_dir=None, mods=None,
                    judge=None, limit=40, seed=0):
    """MANDATORY before any (a)/(b) number is reported.

    Every FOUND reference carries a Concept id the model itself asserted. Run the judge blind
    on those and see how often it agrees. Two rates, because they answer different things:

      exact  -- judge picks the same concept id the model did
      any    -- judge picks SOME concept rather than NONE

    `any` is the one that bounds the (a)/(b) split, because the split only asks whether a
    covering concept exists. If the judge answers NONE on links the model explicitly made,
    it will answer NONE on misses too, and every (a) verdict inherits that false-negative
    rate. Report it alongside the split or the split is not reportable.
    """
    import random
    if judge is None:
        raise ValueError("calibrate_judge needs a judge; build one with make_judge(call)")
    func = _function_index(parsed_dir)
    pool = []
    for m, blob in concept_run.items():
        if m not in reference or (mods is not None and m not in mods):
            continue
        preds = [(e, n, o) for e, n, o, _c in blob["assets"]]
        cids = [c for _e, _n, _o, c in blob["assets"]]
        used = set()
        for rname, _robj in reference[m]:
            cand = {i: preds[i][1] for i in range(len(preds)) if i not in used}
            pi = EA._hit_idx(cand, rname, True)
            if pi is not None:
                used.add(pi)
                if cids[pi] in blob["concepts"]:
                    pool.append((m, preds[pi][1], cids[pi], blob["concepts"]))
    random.Random(seed).shuffle(pool)
    pool = pool[:limit]
    exact = any_hit = 0
    rows = []
    for m, name, model_cid, concepts in pool:
        got = judge(m, name, func.get((m, name.split(".")[0]), ""), concepts)
        exact += got == model_cid
        any_hit += got is not None
        rows.append({"module": m, "element": name, "model": model_cid, "judge": got})
    n = len(pool) or 1
    return {"n": len(pool), "exact": exact / n, "any": any_hit / n, "rows": rows}


def _function_index(parsed_dir=None):
    parsed_dir = Path(parsed_dir) if parsed_dir else PARSED_DIR
    out = {}
    for f in sorted(Path(parsed_dir).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for e in d.get("ports", []) + d.get("signals", []):
            out[(f.stem, e["name"])] = e.get("function", "") or ""
    return out


def split_misses(concept_run, reference, parsed_dir=None, mods=None, judge=None):
    """The primary (a)/(b) instrument. Reports over DISTINCT references, not instances.

    Counting per repeat inflates n -- 24 misses x 5 repeats is 120 instances but only ~44
    distinct references, and repeats of the same miss are not independent.
    """
    func = _function_index(parsed_dir)
    rows = []
    n_no_list = 0
    for m, blob in concept_run.items():
        if m not in reference or (mods is not None and m not in mods):
            continue
        concepts = blob["concepts"]
        if not concepts:
            n_no_list += 1
            continue          # see V_NO_LIST below -- never silently score these as (a)
        have_obj = {c["objective"] for c in concepts.values() if c["objective"]}
        preds = [(e, n, o) for e, n, o, _c in blob["assets"]]
        used = set()
        for rname, robj in reference[m]:
            cand = {i: preds[i][1] for i in range(len(preds)) if i not in used}
            pi = EA._hit_idx(cand, rname, True)
            if pi is not None:
                used.add(pi)
                continue
            obj = EA._obj(robj)
            if obj and obj not in have_obj:
                v, cid = V_A_STRONG, None
            elif judge is None:
                v, cid = V_UNRESOLVED, None
            else:
                cid = judge(m, rname, func.get((m, rname.split(".")[0]), ""), concepts)
                v = V_B if cid else V_A_WEAK
            rows.append({"module": m, "element": rname, "objective": obj,
                         "verdict": v, "concept": cid})
    tally = Counter(r["verdict"] for r in rows)
    if n_no_list:
        # Surfaced as its own verdict rather than dropped, so a run where the model never
        # emitted the array cannot be mistaken for a run where it conceived nothing.
        for m, blob in concept_run.items():
            if m in reference and (mods is None or m in mods) and not blob["concepts"]:
                tally[V_NO_LIST] += len(reference[m])
    return rows, tally


def concept_precision(concept_run, reference, mods=None):
    """Q5, first half: is each FP's parent concept also the parent of a TP?

    Distinguishes 'the model invented a bad concept' from 'the model had a legitimate
    concept and over-bound it'.

    TWO TRAPS, both hit on the first attempt and both silent:

    1. A load_concept_runs() dict is {module: {"concepts":..., "assets":...}}, which is NOT
       run shape. Passing it to EA.score() sends it through _as_run(), which iterates the
       inner dict's KEYS and yields elements literally named "concepts" and "assets" -- no
       exception, just an empty result. So build the run shape explicitly here.
    2. Identifying which emitted asset is the FP by counting names re-introduces exactly the
       same-name collapse that M-2 exists to fix (neorv32_bus has two `state` assets). The
       scorer consumes predictions BY INDEX, so this replays that loop and reads the
       leftover indices, which keeps FP identity consistent with every reported number.
    """
    if not isinstance(concept_run, dict) or "assets" not in next(iter(concept_run.values()), {}):
        raise ValueError("pass a load_concept_runs() dict -- this needs the Concept ids")

    out, per_concept = Counter(), defaultdict(lambda: {"tp": 0, "fp": 0})
    for m, blob in concept_run.items():
        if m not in reference or (mods is not None and m not in mods):
            continue
        preds = [(e, n, o) for e, n, o, _c in blob["assets"]]
        cids = [c for _e, _n, _o, c in blob["assets"]]
        used = set()
        for rname, _robj in reference[m]:
            cand = {i: preds[i][1] for i in range(len(preds)) if i not in used}
            pi = EA._hit_idx(cand, rname, True)
            if pi is not None:
                used.add(pi)
                per_concept[(m, cids[pi])]["tp"] += 1
        for i in range(len(preds)):
            if i not in used:
                per_concept[(m, cids[i])]["fp"] += 1

    for _key, v in per_concept.items():
        if v["fp"] and v["tp"]:
            out["FP under a concept that also produced a TP (over-binding)"] += v["fp"]
        elif v["fp"]:
            out["FP under a concept that produced no TP (bad concept)"] += v["fp"]
    return out, per_concept


def concept_binding(concept_run, mods=None):
    """Concepts by how many emitted assets they bind. Returns (Counter, unbound rows).

    UNBOUND IS A THIRD OUTCOME, not a variant of (a) or (b). The model conceived an idea and
    attached no element to it. The prompt explicitly invites that -- "a conceptual asset with
    no closed-set element still belongs here" -- so it is not a contract violation. It is the
    model reporting that the closed set cannot express something it considered, which is a
    statement about STAGE 4 (what the parser extracted), not about STAGE 5's reasoning.

    The known instance: cache.inval_i is class `absent`, genuinely not in the parsed closed
    set because of the C-03 revision skew, and unreachable by any prompt. If unbound concepts
    line up with references like that one, they are measuring the parser, not the model.

    Also flags DANGLING ids -- an asset pointing at a concept that was never defined. That is
    a real violation, and it is what v01c4's data looked like once the top-level array had
    been discarded by generate_assets().
    """
    tally, rows = Counter(), []
    for m, blob in concept_run.items():
        if mods is not None and m not in mods:
            continue
        concepts, assets = blob["concepts"], blob["assets"]
        if not concepts:
            tally["module emitted no concept list"] += 1
            continue
        used = Counter(c for _e, _n, _o, c in assets if c)
        for cid, meta in concepts.items():
            n = used.get(cid, 0)
            tally["concept bound to >=1 asset" if n else "concept UNBOUND (no element)"] += 1
            if not n:
                rows.append({"module": m, "id": cid, "concept": meta["concept"],
                             "objective": meta["objective"], "why": meta["why"]})
        for cid, n in used.items():
            if cid not in concepts:
                tally["asset points at an UNDEFINED concept id"] += n
    return tally, rows


def objective_coverage(concept_run, reference, mods=None):
    """A deterministic tier the sibling/secondary rules cannot give: for each MISS, did the
    model conceive ANY concept carrying that element's reference objective, in that module?

    Coarse -- three objectives -- but it is free, non-circular, and unlike tiers 1 and 2 it
    reads the model's OWN concept list rather than inferring conception from what happened
    to be emitted nearby. A miss whose objective is entirely absent from the concept list is
    the strongest available evidence for (a).
    """
    tally = Counter()
    for m, blob in concept_run.items():
        if m not in reference or (mods is not None and m not in mods):
            continue
        if not blob["concepts"]:
            # NO CONCEPT LIST AT ALL. Without this guard every miss scores "objective
            # absent -> (a) not conceived", which is the most confident possible wrong
            # answer: the objective is absent because the LIST is absent, not because the
            # model failed to conceive anything. v01c4 emitted zero ConceptualAssets in
            # 90/90 files and would have reported 100% conception failure.
            tally["NO CONCEPT LIST -- unclassifiable, not evidence of (a)"] += sum(
                1 for _r in reference[m])
            continue
        have = {c["objective"] for c in blob["concepts"].values() if c["objective"]}
        preds = [(e, n, o) for e, n, o, _c in blob["assets"]]
        used = set()
        missed = []
        for rname, robj in reference[m]:
            cand = {i: preds[i][1] for i in range(len(preds)) if i not in used}
            pi = EA._hit_idx(cand, rname, True)
            if pi is None:
                missed.append(EA._obj(robj))
            else:
                used.add(pi)
        for o in missed:
            tally["objective present in concept list" if o in have
                  else "objective ABSENT from concept list -> (a)"] += 1
    return tally


def report(assets_dir, reference, mods=None):
    """Print the whole substage for one repeat directory."""
    run = EA.load_run(assets_dir)
    rows, tally = classify_misses(run, reference, mods)
    n = sum(tally.values())
    print(f"  {assets_dir}: {n} misses")
    for t in TIERS:
        if tally[t]:
            print(f"    {tally[t]:4d}  ({100 * tally[t] / n:4.1f}%)  {t}")
    return rows, tally
