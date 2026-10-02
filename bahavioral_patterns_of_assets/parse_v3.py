"""Algorithm 1 line 4, v3 -- mechanical extraction + occurrence-driven LLM annotation.

    RTL file
      -> rtl_parse.parse_rtl_file        deterministic: what elements exist
      -> rtl_parse.strip_comments        the text handed to the annotator
      -> PARSE_PORTS_V3_SYSTEM           one call per entity per batch
         PARSE_SIGNALS_V3_SYSTEM
      -> parsed_v3_tuning18/<module>.json

WHO DECIDES WHAT. The regex decides membership; the model never adds or drops an element.
The model decides meaning; the regex never guesses at it. Keeping that split is what makes
a coverage failure a hard error rather than a judgement call -- `verify_against_cache`
raises if the annotated set differs from the mechanical one by a single entry.

WRITES A SEPARATE DIRECTORY. `parsed_tuning18/` is read by the scorer, by
`validate_primary`, and by every run recorded in ABLATION_LOG_V2.md. This module reads it
as the reference closed set and writes `parsed_v3_tuning18/`, so nothing already measured
moves underneath.

COMMENTS ARE STRIPPED. The v1/v2 annotate prompts told the model to use in-source comments;
`rtl_parse.strip_comments` carries a docstring forbidding its use on that stage for exactly
that reason. The v3 prompts never reference comments, so stripping is correct here and is
the point: a comment is where a designer states a conclusion the RTL does not show, and an
annotator that reads one will report it as observed fact.

THE OUTPUT GATE. `role` is open prose, so nothing about its shape constrains what the model
can say. The constraint is applied afterwards instead: `check_annotation` rejects verdict
and hedging vocabulary, unresolvable relationship targets, unknown edge types and
over-length fields. `report()` aggregates the violations. Read it before spending anything
downstream -- an annotation set with a non-trivial violation rate is a parse that has
started doing the asset stage's job, and no downstream number taken on it means what it
appears to mean.
"""
from __future__ import annotations

import hashlib
import collections
import json
import re
from collections import Counter
from pathlib import Path

import rtl_parse
from prompts_parse_v3 import (BANNED_IN_OUTPUT, EDGE_TYPES, PARSE_ELEMENTS_V3_SYSTEM,
                              PARSE_PORTS_V3_SYSTEM, PARSE_SIGNALS_V3_SYSTEM,
                              audit_against_corpus, sha)

# Resolved once. The working copy keeps its sources under data/, the repo root does not,
# and a wrong default made governing_coverage return without printing -- a missing primary
# metric that looked like a clean run.
RTL_DIR = next((p for p in (Path("data/RTL_data"), Path("RTL_data")) if p.exists()),
               Path("RTL_data"))

CACHE_DIR = Path("parsed_tuning18")      # the v1 closed set, used as the coverage reference
OUT_DIR = Path("parsed_v7_tuning18")     # each prompt version writes to its own dir

# Stamped into every output file. CARRIES reverses direction between v3 and v5, so a
# figure computed across both compares two different things while looking consistent.
# report() and compare_parses() refuse to read a directory that mixes stamps.
PARSE_VERSION = {"prompt_sha": sha(PARSE_ELEMENTS_V3_SYSTEM),
                 "edge_set": "v7", "edge_types": len(EDGE_TYPES)}

_EDGE_SET = set(EDGE_TYPES)
_HANDLING = ("ORIGINATES", "CONSUMES", "FORWARDS")

# Types the DRIVER may write. They are not edges and never come from the model: UNRESOLVED
# means normalisation dropped every edge this element had. It exists because the previous
# fallback wrote ISOLATED, which is a positive claim -- "no coupling can be substantiated
# anywhere in this entity" -- and that claim then fed audit_isolated, the check built to
# catch it. A parse failure and a finding are different things and must not share a name.
DRIVER_MARKERS = ("UNRESOLVED",)
_MAX = {"functionality": 45, "evidence": 40, "guard": 25, "bits": 25}


def _loads(txt):
    """Same salvage path as the v1 parse cell: a truncated tail costs one batch, not one
    module."""
    try:
        return json.loads(txt)
    except Exception:
        pass
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def entity_source(path, ename, vhdl=True):
    """The source of ONE entity -- its declaration plus its own architecture -- comments
    removed. Falls back to the whole file when the architecture cannot be located.

    WHY NOT THE WHOLE FILE. Two reasons, and the second matters more than the first.

    Cost: an occurrence profile is a whole-file scan, so the source goes with every batch.
    Sending all six entities of a multi-entity file to annotate one of them multiplied the
    input by the number of entities -- measured at 1.13 M characters across the corpus,
    750 K of it from one file.

    Correctness: 54 names in that same file are declared in MORE THAN ONE entity (59 across
    the 18 modules), `clk_i` in all six. An annotator handed the whole file and asked about
    one entity's `core_req_i.addr` sees two declarations of that name and two disjoint sets
    of occurrences, with nothing marking which belongs to the element in front of it. The
    profile it builds is then a merge of two elements. Scoping removes that failure
    outright -- the elements are extracted per entity, so the source should be too.

    What is NOT lost: a port map to a sub-instance lives in the PARENT's architecture, so
    cross-boundary couplings stay visible. The child's internals were never needed -- the
    prompt records those as `instance.port` and forbids claims about elements outside the
    closed set.
    """
    from stage_a import _mask_comments
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    masked = _mask_comments(raw, vhdl=vhdl)
    ent = next((m.group(0) for m in rtl_parse._ENTITY.finditer(masked)
                if m.group(1).lower() == ename.lower()), "")
    arch = rtl_parse.arch_region(masked, ename)
    if arch is None:
        return rtl_parse.strip_comments(raw, vhdl=vhdl)
    return rtl_parse.strip_comments(ent + "\n" + arch, vhdl=vhdl)


def _annot_user(stem, entity, rtl, elems, key):
    """The user message.

    FIELD ORDER IS DELIBERATE: the invariant part first, the part that varies per batch
    last. Every batch of one entity sends the same header and the same source and differs
    only in the element list, so putting the list first would make the long shared span a
    suffix and defeat prefix caching entirely. With the source first, everything up to the
    element list is byte-identical across an entity's batches.

    NO IDENTIFIER FROM THE CORPUS APPEARS HERE. The v1 builder quoted 'ctrl.buf_req' and
    'host_req_i.stb' as dotted-name examples; both are declared in the evaluation set and
    this stage feeds the asset stage, so the standing rule applies. The dot convention is
    stated rather than demonstrated.
    """
    return (f"ENTITY: {entity}   (in file {stem})\n\n"
            f"SOURCE of this entity (comments removed):\n{rtl}\n\n"
            f"AUTHORITATIVE {key.upper()} of this entity, extracted from the source above. "
            f"Annotate every one, add none, drop none. A name containing a dot is a field "
            f"of a record-typed element and is reproduced with the dot exactly as given:\n"
            f"{json.dumps(elems, indent=2)}\n\n"
            f"Return the annotated {key} as one JSON object in the required schema.")


def _by_locality(combined, rtl):
    """Order one entity's elements by where each first appears in that entity's source.

    WHY. An edge and its mirror are written on two different elements, so the mirror only
    gets written if the other end is in the same call. Measured on the one entity in this
    corpus that splits -- 582 elements over 5 batches -- the batch boundary is not a
    degradation but a wall:

        both ends in the SAME batch  : 14/73  = 19% mirrored
        ends in DIFFERENT batches    :  0/141 =  0% mirrored

    Elements used in the same statement sit near each other in the text, so ordering by
    first appearance puts both ends in one call more often. On the pairs the v6 parse
    actually wrote: 31% -> 50% same-batch.

    ONLY APPLIED WHEN THE ENTITY SPLITS. A single-call entity is byte-identical to before,
    so any change measured outside the split entity is attributable to the prompt and not
    to this.

    Alternatives measured on the same pairs and rejected: grouping by record field name
    (25%), by median statement index (41%), and a greedy statement walk (34%). Plain first
    use won, and the field-name idea -- that a bus switch couples same-named fields across
    records -- was simply wrong.

    Ordering affects only which call an element is annotated in. `_assemble` rebuilds every
    record in mechanical order afterwards, and `_annot_user` puts the element list LAST so
    the cacheable prefix is unchanged.
    """
    # `entity_source` returns the entity DECLARATION followed by the architecture body, and
    # `arch_region` has already eaten the 'architecture X of Y is' header, so there is no
    # keyword to split on. Skip past the entity declaration with the same regex that built
    # it. Without this, every port's first occurrence is its own port-clause entry, in
    # declaration order -- reproducing the ordering this function exists to replace. Caught
    # by measuring after the change: the rate stayed at 31% twice.
    em = rtl_parse._ENTITY.search(rtl)
    off = em.end() if em else 0
    body = rtl[off:]

    def key(item):
        i, (_kind, e) = item
        n = e["name"]
        for cand in (n, n.split(".")[0]):
            m = re.search(r"(?<![\w.])" + re.escape(cand) + r"(?![\w])", body, re.I)
            if m:
                return (off + m.start(), n, i)
        return (len(rtl), n, i)          # never mentioned: park it at the end, stably

    out = [ke for _, ke in sorted(enumerate(combined), key=key)]
    assert len(out) == len(combined), "locality ordering changed the element count"
    assert {e["name"] for _, e in out} == {e["name"] for _, e in combined}, \
        "locality ordering changed the element set"
    return out


def _selftest_locality():
    """The ordering must group co-located elements and must never lose one."""
    src = "begin  aa <= bb and cc;  dd <= ee;  end"
    comb = [("signal", {"name": n}) for n in ("ee", "dd", "cc", "bb", "aa")]
    got = [e["name"] for _, e in _by_locality(comb, src)]
    assert got == ["aa", "bb", "cc", "dd", "ee"], got
    # an element the source never mentions is kept, at the end
    comb2 = comb + [("signal", {"name": "zz"})]
    got2 = [e["name"] for _, e in _by_locality(comb2, src)]
    assert got2[-1] == "zz" and len(got2) == 6, got2
    return True


def _annotate_merged(complete, stem, entity, rtl, ports, signals, issues,
                     batch=128, max_tokens=32768):
    """ONE call per batch covering ports AND internal elements together.

    CONFIGURATION D. Algorithm 1 line 4 specifies two parsers, one for I/O ports and one for
    internal signals/registers, and `_annotate` below still implements that faithfully. This
    merges them, which is a registered deviation (ABLATION_LOG_V2.md, arm P3) taken for cost:
    61 calls and ~100 k input tokens become 30 and ~48 k, because the entity's source is
    resent per call and merging halves the number of calls that carry it.

    It is also defensible on quality, which is why it was worth doing at all. An element's
    occurrence profile routinely spans both lists -- a port is captured into a register, a
    register drives a port -- so a single call sees both sides of every edge it is asked to
    record, and the reciprocal edges (§7.5 of the KB) can be made consistent within one
    answer rather than across two.

    Batching walks the COMBINED sequence, so a chunk may hold only ports, only signals, or
    both; the schema returns both arrays and an empty one is legal.
    """
    pann, sann = {}, {}
    combined = [("port", e) for e in ports] + [("signal", e) for e in signals]
    if len(combined) > batch and _selftest_locality():
        combined = _by_locality(combined, rtl)
    for i in range(0, len(combined), batch):
        chunk = combined[i:i + batch]
        cp = [e for k, e in chunk if k == "port"]
        cs = [e for k, e in chunk if k == "signal"]
        txt = complete(PARSE_ELEMENTS_V3_SYSTEM,
                       _annot_user_merged(stem, entity, rtl, cp, cs), max_tokens=max_tokens)
        got = _loads(txt)
        gp = got.get("ports") or []
        gs = got.get("signals") or []
        for a in gp:
            if isinstance(a, dict) and "name" in a:
                pann[a["name"]] = a
        for a in gs:
            if isinstance(a, dict) and "name" in a:
                sann[a["name"]] = a
        if not gp and not gs:
            issues["dead_batch"][f"{stem}/{entity}/batch{i // batch}"] += 1
            print(f"    [warn] {stem}/{entity} batch {i // batch}: "
                  f"{len(chunk)} element(s) came back unannotated")
    return pann, sann


def _annot_user_merged(stem, entity, rtl, ports, signals):
    """Same field order as `_annot_user`: invariant source first, varying lists last, so the
    long prefix stays cacheable across an entity's batches."""
    return (f"ENTITY: {entity}   (in file {stem})\n\n"
            f"SOURCE of this entity (comments removed):\n{rtl}\n\n"
            f"AUTHORITATIVE PORTS of this entity, extracted from the source above. Annotate "
            f"every one, add none, drop none. A name containing a dot is a field of a "
            f"record-typed element and is reproduced with the dot exactly as given:\n"
            f"{json.dumps(ports, indent=2)}\n\n"
            f"AUTHORITATIVE INTERNAL SIGNALS AND REGISTERS of this entity, same rules:\n"
            f"{json.dumps(signals, indent=2)}\n\n"
            f"Return both annotated lists as one JSON object in the required schema.")


def _annotate(complete, system, stem, entity, rtl, elems, key, issues,
              batch=64, max_tokens=32768):
    """Annotate in batches so a large record-expanded list cannot overflow the output and
    truncate the JSON. The entity's whole source goes with every batch: an occurrence
    profile is a whole-scope scan, and an annotator shown a fragment cannot build one.

    BATCH 64, NOT 40. The source is resent per batch, so batch size trades input volume
    against truncation risk. This schema returns five fields per element -- roughly 90
    output tokens each -- so 64 elements is about 5.8 k tokens of JSON, well inside the
    32 k ceiling even with a large reasoning budget. A truncated batch costs every element
    in it, which is why the ceiling is raised alongside the batch rather than instead."""
    ann = {}
    for i in range(0, len(elems), batch):
        chunk = elems[i:i + batch]
        got = _loads(complete(system, _annot_user(stem, entity, rtl, chunk, key),
                              max_tokens=max_tokens)).get(key, [])
        for a in got:
            if isinstance(a, dict) and "name" in a:
                ann[a["name"]] = a
        if not got:
            issues["dead_batch"][f"{stem}/{entity}/{key}"] += 1
            print(f"    [warn] {stem}/{entity} {key} batch {i // batch}: "
                  f"{len(chunk)} element(s) came back unannotated")
    return ann


# ------------------------------------------------------------------ the gate ---

def check_annotation(rec, closed_names, issues, where):
    """Enforce on the OUTPUT what the prompt asks for. Returns the record, annotated with
    nothing -- violations are counted, never silently repaired, because a repaired record
    hides the rate that tells you whether the prompt is working."""
    text = " ".join([str(rec.get("functionality", "")),
                     str(rec.get("evidence", ""))] + list(rec.get("role") or []))
    low = " " + text.lower() + " "
    for w in BANNED_IN_OUTPUT:
        if w in low:
            issues["banned_word"][w.strip()] += 1
            issues["_offenders"][where] += 1

    for f, limit in _MAX.items():
        v = str(rec.get(f, ""))
        if v and len(v.split()) > limit:
            issues["over_length"][f] += 1

    # `handling` is present exactly where the name is dotted. Both directions are counted:
    # a missing one loses the record/field structural fact, a stray one means the model is
    # answering a question that was not asked of that element.
    h = str(rec.get("handling", "")).strip().upper()
    dotted = "." in str(rec.get("name", ""))
    if dotted and h not in _HANDLING:
        issues["handling_missing_or_bad"][f"{where}:{h or '<missing>'}"] += 1
    if not dotted and h:
        issues["handling_on_non_field"][where] += 1

    roles = rec.get("role") or []
    if not isinstance(roles, list) or not roles:
        issues["no_role"][where] += 1
    elif len(roles) > 3:
        issues["over_three_roles"][where] += 1

    rels = rec.get("relationship") or []
    if not isinstance(rels, list) or not rels:
        issues["no_relationship"][where] += 1
    for r in rels if isinstance(rels, list) else []:
        if not isinstance(r, dict):
            continue
        ty = str(r.get("type", "")).upper()
        if ty in DRIVER_MARKERS:
            # written by normalize_record, not by the model. Counted apart so that
            # `unknown_edge` keeps measuring the annotator and nothing else.
            issues["driver_unresolved"][where] += 1
            continue
        if ty not in _EDGE_SET:
            issues["unknown_edge"][ty or "<missing>"] += 1
        # v4: a governing edge without its guard records THAT one element governs another
        # and never UNDER WHAT CONDITION -- the difference between an ordinary enable and
        # a lock. Counted, never repaired: the empty slot IS the measurement.
        g = str(r.get("guard", "")).strip()
        if ty in GUARD_REQUIRED and not g:
            issues["governing_edge_without_guard"][f"{where}:{ty}"] += 1
        if ty not in GUARD_REQUIRED and g:
            issues["guard_on_non_governing_edge"][f"{where}:{ty}"] += 1
        if len(g.split()) > _MAX["guard"]:
            issues["over_length"]["guard"] += 1
        if len(str(r.get("bits", "")).split()) > _MAX["bits"]:
            issues["over_length"]["bits"] += 1
        for tgt in r.get("targets") or []:
            # an instance.port target is outside the closed set by construction
            if tgt not in closed_names and "." not in str(tgt):
                issues["unresolved_target"][str(tgt)] += 1
    if not str(rec.get("evidence", "")).strip():
        issues["no_evidence"][where] += 1
    return rec


def verify_against_cache(parsed, cached, stem):
    """The invariant the stage rests on: the annotated set is the mechanical set, in order,
    with the mechanical fields untouched. Raises rather than warns -- a drift here turns an
    annotation change into a closed-set change, and no downstream care recovers the
    attribution once a run is paid for."""
    for key in ("ports", "signals"):
        a = [(e["entity"], e["name"]) for e in cached[key]]
        b = [(e["entity"], e["name"]) for e in parsed[key]]
        assert a == b, (f"{stem}: {key} differs from {CACHE_DIR}/{stem}.json -- "
                        f"{len(a)} vs {len(b)}; missing {sorted(set(a) - set(b))[:5]}, "
                        f"extra {sorted(set(b) - set(a))[:5]}")
        for c, p in zip(cached[key], parsed[key]):
            for f in ("type", "dir"):
                if f in c:
                    assert c[f] == p.get(f), \
                        f"{stem}: {c['name']} field {f!r} changed: {c[f]!r} -> {p.get(f)!r}"


# ---------------------------------------------------------------- the driver ---

def annotate_module(complete, stem, rtl_path, records=None, overwrite=False, merged=True):
    """-> the v3 record for one file. Cached per module; re-running is free.

    merged=True (configuration D) annotates a whole entity in one call. merged=False
    keeps Algorithm 1 line 4's two separate parsers. Both write the same schema, so the
    choice is invisible downstream and can be ablated."""
    OUT_DIR.mkdir(exist_ok=True)
    outp = OUT_DIR / f"{stem}.json"
    if outp.exists() and not overwrite:
        return json.loads(outp.read_text(encoding="utf-8"))

    vhdl = Path(rtl_path).suffix.lower() in (".vhd", ".vhdl")
    mech = rtl_parse.parse_rtl_file(rtl_path, records=records)

    issues = {k: Counter() for k in
              ("banned_word", "_offenders", "over_length", "no_role", "over_three_roles",
               "no_relationship", "unknown_edge", "unresolved_target", "no_evidence",
               "dead_batch", "missing", "driver_unresolved",
               "handling_missing_or_bad", "handling_on_non_field",
               "governing_edge_without_guard",
               "guard_on_non_governing_edge", "isolated_but_used",
               "isolated_with_coupled_field")}
    closed_names = {e["name"] for ent in mech["entities"]
                    for e in ent["ports"] + ent["signals"]}

    ports_out, signals_out = [], []
    for ent in mech["entities"]:
        en = ent["entity"]
        # ONE entity's source, not the file's. See entity_source() -- this is a correctness
        # fix as much as a cost one, because names repeat across entities of a file.
        scope = entity_source(rtl_path, en, vhdl=vhdl)
        # the annotator is shown name/type/dir only -- no v1 `function`, which would
        # anchor this annotation to one produced under a different input regime
        pin = [{k: v for k, v in e.items() if k in ("name", "dir", "type")} for e in ent["ports"]]
        sin = [{k: v for k, v in e.items() if k in ("name", "type")} for e in ent["signals"]]
        if merged:
            pa, sa = _annotate_merged(complete, stem, en, scope, pin, sin, issues)
        else:
            # the two-parser configuration, faithful to Algorithm 1 line 4
            pa = _annotate(complete, PARSE_PORTS_V3_SYSTEM, stem, en, scope, pin,
                           "ports", issues) if pin else {}
            sa = _annotate(complete, PARSE_SIGNALS_V3_SYSTEM, stem, en, scope, sin,
                           "signals", issues) if sin else {}

        def merge(e, a, extra):
            where = f"{stem}/{en}/{e['name']}"
            if not a:
                issues["missing"][where] += 1
            rec = {"entity": en, **e, **extra,
                                      "functionality": a.get("functionality", ""),
                   "role": a.get("role") or [],
                   "relationship": a.get("relationship") or [],
                   "evidence": a.get("evidence", "")}
            return check_annotation(rec, closed_names, issues, where)

        for e in ent["ports"]:
            ports_out.append(merge(e, pa.get(e["name"], {}), {}))
        for e in ent["signals"]:
            a = sa.get(e["name"], {})
            signals_out.append(merge(e, a, {"kind": a.get("kind", "signal")}))

    check_cross_record(ports_out + signals_out, issues, stem)
    check_isolated_used(ports_out + signals_out, rtl_path, vhdl, issues, stem)
    parsed = {"module": stem, "entities": [e["entity"] for e in mech["entities"]],
              "ports": ports_out, "signals": signals_out,
              "_issues": {k: dict(v) for k, v in issues.items() if v}}

    cache = CACHE_DIR / f"{stem}.json"
    if cache.exists():
        verify_against_cache(parsed, json.loads(cache.read_text(encoding="utf-8")), stem)
    outp.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
    return parsed


def annotate_all_parallel(complete, modules, records=None, overwrite=False, workers=6,
                          batch=128, max_tokens=32768):
    """Same result as `annotate_all`, with the calls issued concurrently.

    WHY THIS EXISTS. Stage B's run loop has always used a ThreadPoolExecutor; this stage was
    two nested sequential for-loops. Measured on the real corpus: 30 calls, and the heavy
    ones emit ~11.5 k output tokens apiece, so wall clock is dominated by generation and runs
    to roughly 100 minutes serially. `neorv32_bus` alone is 10 of those calls -- five of them
    `io_switch` batches -- and accounts for about a third of the total on its own.

    THE CALLS ARE INDEPENDENT BY CONSTRUCTION. Every work item is one entity's batch of a
    disjoint element set, annotated from that entity's own scoped source. Nothing an item
    returns feeds another. So concurrency changes throughput and nothing else -- the assembled
    record is identical, and `verify_against_cache` still gates every write.

    Ordering is restored at assembly: results are keyed by (stem, entity, batch index) and the
    record is rebuilt in the mechanical element order, so the output is byte-comparable with
    the sequential path.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    audit_against_corpus()
    print("standing-rule audit: no corpus identifier in either prompt")
    OUT_DIR.mkdir(exist_ok=True)

    plans, work = {}, []
    for stem, path in modules:
        if (OUT_DIR / f"{stem}.json").exists() and not overwrite:
            continue
        vhdl = Path(path).suffix.lower() in (".vhd", ".vhdl")
        mech = rtl_parse.parse_rtl_file(path, records=records)
        plans[stem] = (path, vhdl, mech, {})
        for ent in mech["entities"]:
            en = ent["entity"]
            scope = entity_source(path, en, vhdl=vhdl)
            pin = [{k: v for k, v in e.items() if k in ("name", "dir", "type")}
                   for e in ent["ports"]]
            sin = [{k: v for k, v in e.items() if k in ("name", "type")} for e in ent["signals"]]
            combined = [("port", e) for e in pin] + [("signal", e) for e in sin]
            for bi in range(0, max(len(combined), 1), batch):
                chunk = combined[bi:bi + batch]
                work.append((stem, en, scope,
                             [e for k, e in chunk if k == "port"],
                             [e for k, e in chunk if k == "signal"], bi // batch))

    if not work:
        print("every module already annotated -- nothing to do")
        return load_all(modules)
    print(f"{len(plans)} module(s) to annotate, {len(work)} call(s), {workers} workers\n")

    def one(item):
        stem, en, scope, cp, cs, bi = item
        txt = complete(PARSE_ELEMENTS_V3_SYSTEM,
                       _annot_user_merged(stem, en, scope, cp, cs), max_tokens=max_tokens)
        return item, _loads(txt)

    got = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(one, w): w for w in work}
        for k, f in enumerate(as_completed(futs), 1):
            item, res = f.result()
            stem, en, _, cp, cs, bi = item
            got[(stem, en, bi)] = res
            n = len(res.get("ports") or []) + len(res.get("signals") or [])
            flag = "" if n else "   <- EMPTY"
            print(f"  [{k:2}/{len(work)}] {stem}/{en} batch {bi}: "
                  f"{n} of {len(cp) + len(cs)} annotated{flag}")

    out = {}
    for stem, (path, vhdl, mech, _) in plans.items():
        issues = {k: Counter() for k in
                  ("banned_word", "_offenders", "over_length", "no_role", "over_three_roles",
                   "no_relationship", "unknown_edge", "unresolved_target", "no_evidence",
                   "dead_batch", "missing", "driver_unresolved",
                   "handling_missing_or_bad", "handling_on_non_field",
                   "governing_edge_without_guard",
                   "guard_on_non_governing_edge", "isolated_but_used",
                   "isolated_with_coupled_field")}
        pann, sann = {}, {}
        for (s, en, bi), res in got.items():
            if s != stem:
                continue
            if not (res.get("ports") or res.get("signals")):
                issues["dead_batch"][f"{stem}/{en}/batch{bi}"] += 1
            for a in res.get("ports") or []:
                if isinstance(a, dict) and "name" in a:
                    pann[(en, a["name"])] = a
            for a in res.get("signals") or []:
                if isinstance(a, dict) and "name" in a:
                    sann[(en, a["name"])] = a
        parsed = _assemble(stem, mech, pann, sann, issues, path, vhdl)
        cache = CACHE_DIR / f"{stem}.json"
        if cache.exists():
            verify_against_cache(parsed, json.loads(cache.read_text(encoding="utf-8")), stem)
        (OUT_DIR / f"{stem}.json").write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        bad = len(issues["_offenders"])
        print(f"[ok  ] {stem:24s} {len(parsed['ports'])}p / {len(parsed['signals'])}s"
              + (f"   {bad} element(s) used verdict/hedging words" if bad else ""))
        out[stem] = parsed
    return {**load_all(modules), **out}


def _isolated_hits(nm, arch):
    r"""How many times `nm` is USED in one architecture. Its own declaration does not count.

    THE DECLARATION IS NOT A USE. `rtl_parse.arch_region` deliberately does not cut at the
    first `begin`, so the architecture's declarative part comes back with the statements. A
    signal declared and never used therefore matched its own `signal x : ...;` line and was
    scored as used -- which would report a CORRECT ISOLATED annotation as contradicted. Every
    signal declaration is blanked before counting. Ports are declared in the entity, outside
    this region, so they are unaffected.

    A dotted name is counted twice over: the source writes `rec.field`, so the whole dotted
    name may never appear, and the field tail is searched as well. The bare-base pattern ends
    at `(?![\w])`, and `.` is not a word character, so `rec` also matches inside `rec.field`
    -- that is intended. A record base IS coupled through its fields.
    """
    import rtl_parse
    body = rtl_parse._SIGNAL.sub(lambda m: " " * len(m.group(0)), arch)
    hits = len(re.findall(r"(?<![\w.])" + re.escape(nm) + r"(?![\w])", body, re.I))
    if "." in nm:
        hits += len(re.findall(r"\." + re.escape(nm.split(".")[-1]) + r"(?![\w])", body, re.I))
    return hits


def _selftest_isolated_hits():
    """Hand-read cases. The rule reports nothing until all of them pass."""
    arch = ("\n  type rec_t is record\n    ff : std_ulogic;\n  end record;\n"
            "  signal unused_sig : std_ulogic;\n"
            "  signal live_sig   : std_ulogic;\n"
            "  signal rec_sig    : rec_t;\n"
            "begin\n"
            "  live_sig <= '1';\n"
            "  rec_sig.ff <= live_sig;\n"
            "end architecture;\n")
    cases = [("unused_sig", 0),   # declared, never used -- the declaration must not count
             ("live_sig",   2),   # assigned once, read once
             ("rec_sig",    1),   # bare name only inside `rec_sig.ff`
             ("rec_sig.ff", 2)]   # the base match plus the `.ff` tail match
    for nm, want in cases:
        got = _isolated_hits(nm, arch)
        assert got == want, f"_isolated_hits({nm!r}) = {got}, hand-read says {want}"
    return True


def check_isolated_used(elements, rtl_path, vhdl, issues, stem):
    """Fill `isolated_but_used`: elements claimed ISOLATED that the source actually uses.

    NEEDS THE SOURCE, so by this file's own division it is an audit rather than a schema
    rule -- `check_annotation` and `check_cross_record` decide from the output alone and can
    be enforced anywhere, this one cannot. It is named `check_` and called during assembly
    only because the counter belongs in the same `_issues` block as the rest, and the source
    is already open at that point. `audit_isolated` reports the same finding across a whole
    directory after the fact; both now go through `_isolated_hits`, so they cannot drift.

    Counted, never repaired.
    """
    if not _selftest_isolated_hits():
        return elements
    import rtl_parse
    from stage_a import _mask_comments
    p = Path(rtl_path) if rtl_path else None
    if not (p and p.exists()):
        return elements
    masked = _mask_comments(p.read_text(encoding="utf-8", errors="ignore"), vhdl=vhdl)
    arch_cache = {}
    for e in elements:
        rels = e.get("relationship") or []
        if any(str(r.get("type", "")).upper() in DRIVER_MARKERS for r in rels):
            continue              # the driver dropped this element's edges; not a claim
        if not any(str(r.get("type", "")).upper() == "ISOLATED" for r in rels):
            continue
        en = e["entity"]
        if en not in arch_cache:
            arch_cache[en] = rtl_parse.arch_region(masked, en) or ""
        n = _isolated_hits(e["name"], arch_cache[en])
        if n:
            issues["isolated_but_used"][f"{stem}/{en}/{e['name']}:{n}"] += 1
    return elements


def check_cross_record(elements, issues, stem):
    """Schema rules that need the whole file rather than one record.

    WHY THIS IS SEPARATE. `check_annotation` takes one record and cannot see its siblings,
    so every dependency rule in it is intra-record: `guard` by edge type, `handling` by
    dotted name. This one is INTER-record. A record base is coupled through its fields, so a
    base whose fields carry edges cannot be ISOLATED. The prompt already says exactly that
    and it is still violated; a rule the output can be checked against is not the same thing
    as a sentence asking for compliance.

    WHY IT IS A SCHEMA RULE AND NOT AN AUDIT. It reads nothing but the parse. No RTL is
    opened. That is the dividing line the rest of this file already draws -- `check_*` decides
    from the output alone and can be enforced, `audit_*` needs the source and can only be
    measured. A base claimed ISOLATED whose bare name appears in the RTL is a different
    finding and belongs to `audit_isolated`.

    Counted, never repaired.
    """
    by_ent = {}
    for e in elements:
        by_ent.setdefault(e["entity"], []).append(e)

    for en, els in by_ent.items():
        coupled = set()
        for e in els:
            for r in e.get("relationship") or []:
                ty = str(r.get("type", "")).upper()
                # ISOLATED is the absence of a coupling, and UNRESOLVED is the driver saying
                # it could not read the model's answer. Neither is evidence of a coupling.
                if ty and ty != "ISOLATED" and ty not in DRIVER_MARKERS:
                    coupled.add(e["name"])
                    break
        for e in els:
            if not any(str(r.get("type", "")).upper() == "ISOLATED"
                       for r in e.get("relationship") or []):
                continue
            pref = e["name"] + "."
            n = sum(1 for c in coupled if c.startswith(pref))
            if n:
                issues["isolated_with_coupled_field"][f"{stem}/{en}/{e['name']}:{n}"] += 1
    return elements


def _selftest_cross_record():
    """Refuses to let the rule report anything until it fires on a case built to fire and
    stays silent on one built not to. Both cases are synthetic; no corpus element is used."""
    from collections import Counter

    def run(els):
        iss = {"isolated_with_coupled_field": Counter()}
        check_cross_record(els, iss, "T")
        return sum(iss["isolated_with_coupled_field"].values())

    iso = [{"type": "ISOLATED", "targets": []}]
    edge = [{"type": "SOURCES", "targets": ["zz"]}]
    base = {"entity": "E", "name": "aa", "relationship": iso}

    # 1. base claimed ISOLATED, one field carries an edge -> must fire
    assert run([base, {"entity": "E", "name": "aa.bb", "relationship": edge}]) == 1
    # 2. same, but the field carries nothing -> must stay silent
    assert run([base, {"entity": "E", "name": "aa.bb", "relationship": iso}]) == 0
    # 3. the coupled field is in a DIFFERENT entity -> must stay silent
    assert run([base, {"entity": "F", "name": "aa.bb", "relationship": edge}]) == 0
    # 4. a name that merely starts with the base is not a field of it
    assert run([base, {"entity": "E", "name": "aardvark", "relationship": edge}]) == 0
    # 5. base not claimed ISOLATED -> nothing to say
    assert run([{"entity": "E", "name": "aa", "relationship": edge},
                {"entity": "E", "name": "aa.bb", "relationship": edge}]) == 0
    return True


def audit_cross_record(out_dir=None):
    """Run the cross-record rule over an existing parse, without re-parsing."""
    from collections import Counter
    if not _selftest_cross_record():
        print("   CROSS-RECORD  self-test failed -- reporting nothing")
        return {}
    d = Path(out_dir or OUT_DIR)
    iss = {"isolated_with_coupled_field": Counter()}
    iso_total = 0
    for f in sorted(d.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        els = rec["ports"] + rec["signals"]
        iso_total += sum(1 for e in els
                         if any(str(r.get("type", "")).upper() == "ISOLATED"
                                for r in e.get("relationship") or []))
        check_cross_record(els, iss, rec["module"])
    hits = iss["isolated_with_coupled_field"]
    n = sum(hits.values())
    print(f"\n   CROSS-RECORD  {n} of {iso_total} ISOLATED claims are record bases whose own "
          f"fields carry edges ({100 * n / max(1, iso_total):.0f}%)")
    for k, _ in sorted(hits.items(), key=lambda x: -int(x[0].rsplit(":", 1)[1]))[:8]:
        where, cnt = k.rsplit(":", 1)
        print(f"      {where}   {cnt} coupled field(s)")
    if n > 8:
        print(f"      ... and {n - 8} more")
    return dict(hits)


def _assemble(stem, mech, pann, sann, issues, rtl_path=None, vhdl=True):
    """Rebuild one module's record in mechanical element order from per-entity annotations.

    Keyed by (entity, name) rather than name alone: 59 names in this corpus are declared in
    more than one entity of the same file, so a bare-name key would let one entity's
    annotation overwrite another's -- the very contamination the entity scoping removed.
    """
    closed = {e["name"] for ent in mech["entities"]
              for e in ent["ports"] + ent["signals"]}
    ports_out, signals_out = [], []
    for ent in mech["entities"]:
        en = ent["entity"]
        for e in ent["ports"]:
            a = pann.get((en, e["name"]), {})
            where = f"{stem}/{en}/{e['name']}"
            if not a:
                issues["missing"][where] += 1
            ports_out.append(check_annotation(
                {"entity": en, **e,
                 "functionality": a.get("functionality", ""),
                 "role": a.get("role") or [],
                 **({"handling": a["handling"]} if a.get("handling") else {}),
                 "relationship": a.get("relationship") or [],
                 "evidence": a.get("evidence", "")}, closed, issues, where))
        for e in ent["signals"]:
            a = sann.get((en, e["name"]), {})
            where = f"{stem}/{en}/{e['name']}"
            if not a:
                issues["missing"][where] += 1
            signals_out.append(check_annotation(
                {"entity": en, **e, "kind": a.get("kind", "signal"),
                 "functionality": a.get("functionality", ""),
                 "role": a.get("role") or [],
                 **({"handling": a["handling"]} if a.get("handling") else {}),
                 "relationship": a.get("relationship") or [],
                 "evidence": a.get("evidence", "")}, closed, issues, where))
    check_cross_record(ports_out + signals_out, issues, stem)
    check_isolated_used(ports_out + signals_out, rtl_path, vhdl, issues, stem)
    return {"module": stem, "entities": [e["entity"] for e in mech["entities"]],
            "_version": PARSE_VERSION, "ports": ports_out, "signals": signals_out,
            "_issues": {k: dict(v) for k, v in issues.items() if v}}


def annotate_all(complete, modules, records=None, overwrite=False, merged=True):
    """-> {stem: record}. `modules` is the notebook's [(stem, path), ...].

    The standing-rule check runs FIRST and raises before any call is made: a leaked
    identifier discovered after the run is a run that has to be thrown away.
    """
    audit_against_corpus()
    print("standing-rule audit: no corpus identifier in either prompt\n")
    out = {}
    for stem, path in modules:
        try:
            p = annotate_module(complete, stem, path, records=records,
                                overwrite=overwrite, merged=merged)
            out[stem] = p
            bad = len((p.get("_issues") or {}).get("_offenders", {}))
            print(f"[ok  ] {stem:24s} {len(p['ports'])}p / {len(p['signals'])}s"
                  + (f"   {bad} element(s) used verdict/hedging words" if bad else ""))
        except Exception as e:
            print(f"[err ] {stem:24s} {type(e).__name__}: {e}")
    return out


def parse_fingerprint(out_dir=None):
    """A sha over the annotation content of the whole parse.

    THE PROVENANCE GAP THIS CLOSES. `_run_meta.json` records the asset prompt's sha, which
    was sufficient while the prompt was the only thing that varied. For the parsed-input
    arms it is not: the parse is half of what the model reads, and two runs of the same arm
    on two different parses are otherwise indistinguishable after the fact. Worse, because
    the asset sha is unchanged, the run loop accepts the old directories and
    `generate_assets` serves every module from cache -- so re-running after a re-parse is a
    silent no-op that looks like a completed run.

    Covers name, entity and the four annotation fields, in file order. Excludes `_issues`,
    which is bookkeeping about the parse rather than input to anything.
    """
    d = Path(out_dir or OUT_DIR)
    h = hashlib.sha256()
    for f in sorted(d.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        for e in rec["ports"] + rec["signals"]:
            h.update(json.dumps({k: e.get(k) for k in
                                 ("entity", "name", "functionality",
                                  "role", "relationship", "evidence")},
                                sort_keys=True).encode())
    return h.hexdigest()


def normalize_record(rec, closed, counts):
    """Repair the two conformance defects the first real run exposed. Applied ON LOAD, not
    on disk: the files keep exactly what the model produced, so provenance is intact and the
    repair is visible and reversible.

    Both are prompt defects, now fixed in `prompts_parse_v3` for future runs. Neither repair
    invents anything -- each recovers a value the model already stated:

      TYPE   200 of 3 048 edges carried a type like "SOURCES(Y)", because the edge list in
             the prompt showed the counterpart as a parenthesised argument and the model
             copied the notation. Stripping the parenthesis recovers the intended type.
             SITE names used as a type (PORT_MAP, RESET_BRANCH, COND...) are NOT remapped --
             turning a site into an edge would be inference, not repair, so they are counted
             and dropped.

      TARGET 496 of 589 unresolved targets were indexed array references such as an array
             name followed by "(0)", where the array itself IS a declared element. The
             asset stage can only bind to declared names, so the index is stripped and the
             range preserved. What remains unresolved is genuinely outside the closed set --
             constants and generics, which `rtl_parse` does not extract.
    """
    for e in rec["ports"] + rec["signals"]:
        out = []
        for r in e.get("relationship") or []:
            t = str(r.get("type", "")).upper().strip()
            if t not in _EDGE_SET:
                bare = t.split("(")[0].strip()
                if bare in _EDGE_SET:
                    counts["type_destructured"] += 1
                    t = bare
                else:
                    counts["type_dropped_site"] += 1
                    continue
            tg_out = []
            for tg in r.get("targets") or []:
                s = str(tg)
                if s in closed or "." in s:
                    tg_out.append(s); continue
                base = re.sub(r"\s*\(.*$", "", s).strip()
                if base in closed:
                    counts["target_deindexed"] += 1
                    if base not in tg_out:
                        tg_out.append(base)
                else:
                    counts["target_dropped"] += 1
            out.append({**r, "type": t, "targets": tg_out})
        if not out:
            # every edge was dropped. Say so; do not convert it into a claim about the RTL.
            counts["all_edges_dropped"] += 1
            out = [{"type": "UNRESOLVED", "targets": []}]
        e["relationship"] = out
    return rec


def normalize_on_disk(out_dir=None):
    """Apply `normalize_record` to the files themselves, keeping the originals under _raw/.

    ON-LOAD REPAIR ALONE WAS HALF A FIX. `load_all` normalised what the asset stage receives,
    but the files kept the malformed strings, so anything reading them directly saw the
    broken version -- `report()` and the diagnostic cells both do, which is why the gate went
    on showing 233 unknown types after the repair existed. An artifact that differs from what
    is consumed is a trap, and the fact that it caught me spot-checking the wrong module is
    the argument for not keeping it.

    The raw responses move to _raw/ rather than being overwritten, matching what
    `generate_assets` does for the asset stage: the model's actual output stays recoverable,
    and `_issues.normalized` records what changed in each file.
    """
    d = Path(out_dir or OUT_DIR)
    raw = d / "_raw"
    raw.mkdir(exist_ok=True)
    total = Counter()
    for f in sorted(d.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if (rec.get("_issues") or {}).get("normalized"):
            continue                                   # already done; idempotent
        (raw / f.name).write_text(json.dumps(rec, indent=2), encoding="utf-8")
        closed = {e["name"] for e in rec["ports"] + rec["signals"]}
        counts = Counter()
        rec = normalize_record(rec, closed, counts)
        if counts:
            rec.setdefault("_issues", {})["normalized"] = dict(counts)
            total.update(counts)
        f.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print(f"normalised {len(list(d.glob('*.json')))} file(s); originals in {raw}/")
    for k, v in sorted(total.items()):
        print(f"   {k:22} {v}")
    return total


def load_all(modules, out_dir=None, normalize=True):
    """-> {stem: record} from disk, no API calls.

    normalize=True applies `normalize_record` to what is loaded. The files on disk are never
    modified; the repair exists so the asset stage is not handed edges it cannot use. Set
    False to see the raw model output.
    """
    d = Path(out_dir or OUT_DIR)
    out = {}
    counts = Counter()
    for stem, _ in modules:
        f = d / f"{stem}.json"
        if not f.exists():
            print(f"[miss] {stem}: no {f}")
            continue
        rec = json.loads(f.read_text(encoding="utf-8"))
        if normalize:
            closed = {e["name"] for e in rec["ports"] + rec["signals"]}
            rec = normalize_record(rec, closed, counts)
        out[stem] = rec
    if counts:
        print("   normalised on load (files unchanged): "
              + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return out


# ------------------------------------------------------------------- report ---

# The DRIVING-end control edges. `governing_coverage` counts an element as covered when it
# carries one of these, so GOVERNED_BY is deliberately absent -- that is the receiving end,
# and counting it would let a governed element look like a governing one.
GOVERNING_EDGES = ("GATES", "SELECTS", "CONSTRAINS", "OVERRIDES", "RESETS")
# Every edge that must carry a guard. The receiving-end mirror needs one too: without the
# test quoted, GOVERNED_BY records only THAT an element is controlled, never under what.
GUARD_REQUIRED = GOVERNING_EDGES + ("GOVERNED_BY",)
# RESETS is deliberately NOT governing. It records that an element forces a recovery value,
# which is a real coupling but not "one element decides whether another acts".


def audit_isolated(out_dir=None, rtl_dir=None):
    """Every ISOLATED claim on an element the RTL actually uses.

    ISOLATED is the one edge checkable without a model. The prompt defines it as "no
    coupling can be substantiated ANYWHERE in this entity", so if the identifier occurs in
    the entity's architecture at all, the claim is false. The prompt already says this and
    the parser still got it wrong, which is the signature of a rule that belongs in code
    rather than in prose -- the same reasoning as the banned-word list.

    Reports, never repairs: a silently corrected record hides the rate that tells you
    whether the prompt is working.
    """
    import rtl_parse
    from stage_a import _mask_comments
    d = Path(out_dir or OUT_DIR)
    rtl = Path(rtl_dir or RTL_DIR)
    if not rtl.exists():
        print(f"\n   ISOLATED CLAIMS  cannot check -- no RTL at {rtl}/")
        return [], 0
    if not _selftest_isolated_hits():
        print("\n   ISOLATED CLAIMS  self-test failed -- reporting nothing")
        return [], 0
    bad, total, skipped = [], 0, 0
    for f in sorted(d.glob("*.json")):
        src_f = rtl / f"{f.stem}.vhd"
        if not src_f.exists():
            skipped += 1
            continue
        masked = _mask_comments(src_f.read_text(encoding="utf-8", errors="ignore"), vhdl=True)
        rec = json.loads(f.read_text(encoding="utf-8"))
        for e in rec["ports"] + rec["signals"]:
            rels = e.get("relationship") or []
            if any(str(r.get("type", "")).upper() in DRIVER_MARKERS for r in rels):
                continue          # the driver dropped this element's edges; not a claim
            if not any(str(r.get("type", "")).upper() == "ISOLATED" for r in rels):
                continue
            total += 1
            arch = rtl_parse.arch_region(masked, e["entity"]) or ""
            hits = _isolated_hits(e["name"], arch)
            if hits > 0:
                bad.append((rec["module"], e["name"], hits))
    print(f"\n   ISOLATED CLAIMS  {total} total, {len(bad)} contradicted by the source "
          f"({100 * len(bad) / max(1, total):.0f}%)"
          + (f"   <- {skipped} file(s) had no matching source and were NOT checked"
             if skipped else ""))
    for m, nm, h in bad[:12]:
        print(f"      {m}/{nm}  occurs {h}x in the architecture")
    if len(bad) > 12:
        print(f"      ... and {len(bad) - 12} more")
    return bad, total


def guard_coverage(out_dir=None):
    """How many governing edges carry the guard the v4 prompt requires.

    The direct read-out of the v4 change. STEP 2b asks for a sweep; before v4 that sweep
    left no trace in the output at all, so it could not be checked. An empty guard is
    countable; an unfollowed instruction is not.
    """
    d = Path(out_dir or OUT_DIR)
    have = miss = 0
    examples = []
    for f in sorted(d.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        for e in rec["ports"] + rec["signals"]:
            for r in e.get("relationship") or []:
                if str(r.get("type", "")).upper() not in GOVERNING_EDGES:
                    continue
                if str(r.get("guard", "")).strip():
                    have += 1
                    if len(examples) < 4:
                        tg = (r.get("targets") or ["-"])[0]
                        examples.append(f"{e['name']} {r['type']} -> {tg}  when "
                                        f"{str(r['guard'])[:52]}")
                else:
                    miss += 1
    tot = have + miss
    if not tot:
        print("\n   GUARD COVERAGE  no governing edges found")
        return have, tot
    print(f"\n   GUARD COVERAGE  {have}/{tot} = {100 * have / tot:.0f}% of governing edges "
          f"carry their guard")
    for x in examples:
        print(f"      {x}")
    return have, tot


def governing_coverage(out_dir=None, rtl_dir=None):
    """How many elements that ACTUALLY appear in a condition were given a governing edge.

    THE ONE NUMBER WORTH RE-PARSING FOR. A governing edge records that one element decides
    whether another acts; that influence never appears in the element's own value, so it is
    the coupling a value-flow reading cannot find and the one the asset stage cannot
    reconstruct for itself.

    A ratio like GATES:SOURCES cannot tell you whether the edge is scarce because the design
    has little control logic or because the annotator missed it. This can: the denominator
    comes from the RTL, by finding every element that appears inside an if/elsif/when/case
    condition. It is a lower bound -- a regex sees `if (x = '1')` but not an enable term
    buried in an expression -- so the true population is larger and the real coverage
    slightly worse than reported.

    Measured on the first v3 parse: 51% overall, and the separation this signal carries
    between true and false dotted-signal assets fell from +52 points in the RTL to +31 in
    the parse. Read this after any re-parse to see whether the STEP 2b sweep landed.
    """
    d = Path(out_dir or OUT_DIR)
    rtl = Path(rtl_dir or RTL_DIR)
    if not rtl.exists():
        print(f"\n   GOVERNING-EDGE COVERAGE  cannot compute -- no RTL at {rtl}/")
        return
    from stage_a import _mask_comments
    tot = cond = caught = 0
    for f in sorted(d.glob("*.json")):
        src_f = rtl / f"{f.stem}.vhd"
        if not src_f.exists():
            continue
        src = _mask_comments(src_f.read_text(encoding="utf-8", errors="ignore"), vhdl=True)
        rec = json.loads(f.read_text(encoding="utf-8"))
        for e in rec["ports"] + rec["signals"]:
            tot += 1
            if not re.search(rf"\b(if|elsif|when|case)\b[^;\n]*(?<![\w.])"
                             rf"{re.escape(e['name'])}(?![\w])", src, re.I):
                continue
            cond += 1
            caught += any(r.get("type") in GOVERNING_EDGES for r in e.get("relationship") or [])
    if not cond:
        return
    pct = 100 * caught / cond
    print(f"\n   GOVERNING-EDGE COVERAGE  {caught}/{cond} = {pct:.0f}% of the elements that "
          f"appear in a condition\n"
          f"   carry a governing edge (of {tot} elements; the denominator is a regex lower "
          f"bound)")
    if pct < 75:
        print("   <- the branch-condition sweep is not landing. This is the coupling the "
              "asset stage\n      cannot reconstruct on its own, so what is missed here is "
              "missed for good.")
    return caught, cond


# Which edges can stand as the mirror of which. Taken from the v5 definitions: an edge
# written from the driving end and its counterpart written from the receiving end are two
# records of one coupling, and both are required. SEQUENCES is deliberately absent -- the
# definitions say a register does not record its own clock this way. EXPORTS and ISOLATED
# carry no target, so there is nothing to mirror.
MIRROR = {
    "GATES":        ("GOVERNED_BY", "REFLECTS"),
    "SELECTS":      ("GOVERNED_BY", "REFLECTS"),
    "CONSTRAINS":   ("GOVERNED_BY", "REFLECTS"),
    "OVERRIDES":    ("GOVERNED_BY", "REFLECTS"),
    "RESETS":       ("GOVERNED_BY",),
    "SOURCES":      ("DERIVES_FROM", "CAPTURES", "REFLECTS"),
    "CARRIES":      ("DERIVES_FROM", "CAPTURES", "REFLECTS"),
    "GOVERNED_BY":  ("GATES", "SELECTS", "CONSTRAINS", "OVERRIDES", "RESETS"),
    "DERIVES_FROM": ("SOURCES", "CARRIES"),
    "CAPTURES":     ("SOURCES", "CARRIES"),
    "REFLECTS":     ("GATES", "SELECTS", "CONSTRAINS", "OVERRIDES", "SOURCES", "CARRIES"),
}
_CONTROL_SIDE = {"GATES", "SELECTS", "CONSTRAINS", "OVERRIDES", "RESETS", "GOVERNED_BY"}


def _ekey(n):
    return str(n).strip().split("(")[0].lower()


def _ebase(n):
    return re.split(r"[.(]", str(n).strip())[0].strip().lower()


def reciprocity_coverage(out_dir=None):
    """Does the other end of each coupling know the coupling exists?

    THE READ-OUT FOR GOVERNED_BY. Measured on the v3 parse, value couplings were recorded at
    both ends 77% of the time and control couplings 2%, because the vocabulary had no
    receiving-end control edge -- a governed element had no word for being governed. That is
    the gap GOVERNED_BY was added to close, and this is the number that says whether it did.

    Also counts the contradiction the v3 parse carried 67 times: the SAME edge type written
    in BOTH directions for one pair. That is not a coupling recorded twice, it is the arrow
    drawn both ways, and it needs no RTL to detect. Pairs sharing a base name are excluded --
    a record and its own field cannot be told apart by name matching.

    Reports, never repairs.
    """
    d = Path(out_dir or OUT_DIR)
    have = {"value": [0, 0], "control": [0, 0]}
    both_ways, one_sided = [], []
    for f in sorted(d.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        els = rec["ports"] + rec["signals"]
        present = {(e["entity"], _ekey(e["name"])) for e in els}
        edges = collections.defaultdict(set)
        for e in els:
            for r in e.get("relationship") or []:
                ty = str(r.get("type", "")).upper()
                for t in (r.get("targets") or []):
                    edges[(e["entity"], _ekey(e["name"]), _ekey(t))].add(ty)
        for (ent, a, b), tys in edges.items():
            if (ent, b) not in present or _ebase(a) == _ebase(b):
                continue           # instance ports, and a record naming its own field
            back = edges.get((ent, b, a), set())
            for ty in tys:
                if ty in back:
                    both_ways.append((rec["module"], a, ty, b))
                if ty not in MIRROR:
                    continue
                side = "control" if ty in _CONTROL_SIDE else "value"
                have[side][0] += 1
                if back & set(MIRROR[ty]):
                    have[side][1] += 1
                else:
                    one_sided.append((rec["module"], a, ty, b))

    print("\n   RECIPROCITY  does the other end record the coupling?")
    for side in ("value", "control"):
        n, k = have[side]
        if n:
            print(f"      {side:<8}{k:>5}/{n:<6}{100 * k / n:>4.0f}%   mirrored")
    n = sum(v[0] for v in have.values())
    k = sum(v[1] for v in have.values())
    if n:
        print(f"      {'all':<8}{k:>5}/{n:<6}{100 * k / n:>4.0f}%")
    print(f"      same type written BOTH ways: {len(both_ways) // 2} pair(s)"
          + ("   <- the arrow is drawn both ways" if both_ways else ""))
    for m, a, ty, b in both_ways[:6]:
        print(f"         {m}: {a} {ty} {b}  and  {b} {ty} {a}")
    return have, both_ways, one_sided


def export_coverage(out_dir=None):
    """Every element declared `out` carries EXPORTS. Decidable from the port list alone, so
    a miss is a recall failure with no interpretation in it. Read 54% on the v3 parse."""
    d = Path(out_dir or OUT_DIR)
    tot = k = 0
    miss = []
    for f in sorted(d.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        for e in rec["ports"]:
            if not str(e.get("dir") or "").lower().startswith(("out", "buffer")):
                continue
            tot += 1
            if any(str(r.get("type", "")).upper() == "EXPORTS"
                   for r in e.get("relationship") or []):
                k += 1
            else:
                miss.append((rec["module"], e["name"]))
    if not tot:
        print("\n   EXPORTS COVERAGE  no output ports found")
        return k, tot
    print(f"\n   EXPORTS COVERAGE  {k}/{tot} = {100 * k / tot:.0f}% of output ports carry it")
    for m, n in miss[:6]:
        print(f"      missing: {m}/{n}")
    if len(miss) > 6:
        print(f"      ... and {len(miss) - 6} more")
    return k, tot


# An element is DRIVEN when something puts a value into it, and CONSUMED when something
# takes that value out again. Both are read off the edge set, from either end.
_DRIVEN_SELF = {"DERIVES_FROM", "CAPTURES"}                    # written on the element
_DRIVEN_BY   = {"SOURCES", "CARRIES", "RESETS"}                # written on whatever drives it
_CONSUMED_SELF = {"SOURCES", "CARRIES", "GATES", "SELECTS", "CONSTRAINS", "OVERRIDES",
                  "SEQUENCES", "EXPORTS", "REFLECTS", "RESETS"}  # the element acts on something
_CONSUMED_BY   = {"DERIVES_FROM", "CAPTURES", "GOVERNED_BY", "REFLECTS"}


def audit_dead_ends(out_dir=None, rtl_dir=None):
    """Elements that are written and never read -- driven, but nothing takes the value.

    THE GAP THIS FILLS. ISOLATED means no coupling at all. An element with a driver HAS a
    coupling, so it is correctly not ISOLATED -- and correctly nothing else either. There is
    no edge in the vocabulary for "has a driver, has no consumer", so the parse cannot say
    it. This can. It maps onto CWE-1164 (Irrelevant Code): dead code, initialisation that is
    not used.

    NOT A VERIFIER FOR ISOLATED. `audit_isolated` checks a claim the model made and asks
    whether the source contradicts it. This finds a fact the model was never able to state.
    The two overlap only where an element is both dead-ended and wrongly called ISOLATED.

    TWO INDEPENDENT SIGNALS, and the disagreement is reported rather than hidden:
      the PARSE says nothing consumes it -- no consuming edge at either end;
      the SOURCE says nothing consumes it -- the name appears on no right-hand side and in
        no condition anywhere in the entity.
    Confirmed dead ends are where both agree. Where the parse says dead but the source shows
    a reader, the parse missed a coupling -- that is a recall finding and is counted apart.

    Writes nothing. The parsed files keep exactly what the model produced.
    """
    from stage_a import _mask_comments
    d = Path(out_dir or OUT_DIR)
    rtl = Path(rtl_dir or RTL_DIR)
    confirmed, parse_only, checked = [], [], 0

    for f in sorted(d.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        els = rec["ports"] + rec["signals"]
        driven, consumed = set(), set()
        for e in els:
            key = (e["entity"], _ekey(e["name"]))
            for r in e.get("relationship") or []:
                ty = str(r.get("type", "")).upper()
                if ty in _DRIVEN_SELF:
                    driven.add(key)
                if ty in _CONSUMED_SELF:
                    consumed.add(key)
                for t in (r.get("targets") or []):
                    tk = (e["entity"], _ekey(t))
                    if ty in _DRIVEN_BY:
                        driven.add(tk)
                    if ty in _CONSUMED_BY:
                        consumed.add(tk)

        src_f = rtl / f"{rec['module']}.vhd"
        masked = (_mask_comments(src_f.read_text(encoding="utf-8", errors="ignore"), vhdl=True)
                  if src_f.exists() else "")
        arch_cache = {}
        for e in els:
            key = (e["entity"], _ekey(e["name"]))
            if key not in driven or key in consumed:
                continue
            if str(e.get("dir") or "").lower().startswith(("out", "buffer")):
                continue                       # an output port leaves; that IS the consumer
            checked += 1
            if not masked:
                parse_only.append((rec["module"], e["name"], -1))
                continue
            if e["entity"] not in arch_cache:
                arch_cache[e["entity"]] = rtl_parse.arch_region(masked, e["entity"]) or ""
            arch = arch_cache[e["entity"]]
            nm = e["name"]
            # every place the name is READ: right of an assignment, or inside a condition
            reads = 0
            pat = re.compile(r"(?<![\w.])" + re.escape(nm.split(".")[-1]) + r"(?![\w])", re.I)
            for st in arch.split(";"):
                k = st.find("<=")
                lhs, rhs = (st[:k], st[k + 2:]) if k > 0 else ("", st)
                # right of the assignment is a read; so is anything left of it that is not
                # the assignment target -- a branch condition sits there
                if pat.search(rhs):
                    reads += 1
                elif lhs:
                    tail = re.search(r"([A-Za-z_][\w.]*(?:\s*\([^()]*\))*)\s*$", lhs)
                    before = lhs[:tail.start()] if tail else lhs
                    if pat.search(before):
                        reads += 1
            if reads == 0:
                confirmed.append((rec["module"], e["name"]))
            else:
                parse_only.append((rec["module"], e["name"], reads))

    # self-test: a reset is read in its own branch condition and must never be reported
    # dead. This exact case was reported dead by the first version of this function.
    if confirmed and all(re.search(r"rst", n, re.I) for _, n in confirmed):
        print("\n   DEAD ENDS  self-test FAILED -- every hit is a reset, which is read in "
              "its own\n   branch condition. Not reporting.")
        return [], parse_only

    print(f"\n   DEAD ENDS  driven but never consumed: {len(confirmed)} confirmed "
          f"by the source, of {checked} the parse flagged")
    for m, n in confirmed[:8]:
        print(f"      {m}/{n}")
    if len(confirmed) > 8:
        print(f"      ... and {len(confirmed) - 8} more")
    if parse_only:
        print(f"      {len(parse_only)} more had no consuming edge in the parse but ARE read "
              f"in the source\n      -- those are missed couplings, not dead logic:")
        for m, n, r in parse_only[:4]:
            print(f"         {m}/{n}  read {r}x")
    return confirmed, parse_only


def compare_parses(old_dir, new_dir=None, rtl_dir=None):
    """Side-by-side on the numbers a re-parse is meant to move.

    The point of a re-parse is not "the output changed" -- it will, the stage is
    non-deterministic. It is whether the three defects the prompt fix targeted actually
    closed, and whether the coupling the asset stage cannot reconstruct got denser. Anything
    else that moved is noise between two samples of the same prompt, and the element counts
    are asserted identical so a difference cannot be a closed-set difference.
    """
    a, b = Path(old_dir), Path(new_dir or OUT_DIR)
    va, vb = assert_one_version(a, "old_dir"), assert_one_version(b, "new_dir")
    print(f"   old: {va}\n   new: {vb}")
    if va != vb:
        # A changed prompt sha and a changed VOCABULARY are not the same thing. v6 edits the
        # prompt and leaves EDGE_TYPES byte-identical to v5, so per-type counts across those
        # two ARE the measurement. Saying "not comparable" would hide the very numbers the
        # run exists to produce. The stamp cannot prove which case this is, so say what
        # differs and point at the log rather than guessing.
        print("   <- DIFFERENT PARSE VERSIONS.")
        if va.rsplit("/", 1)[-1] == vb.rsplit("/", 1)[-1]:
            print(f"      Both declare {va.rsplit('/', 1)[-1]} edge types. If the vocabulary "
                  f"is unchanged and only\n      the prompt was edited, per-type counts ARE "
                  f"comparable -- check the log\n      entry for this version before "
                  f"assuming either way.")
        else:
            print("      Different edge-type counts. Read only the closed-set and coverage "
                  "lines,\n      and read those with care.")

    def stats(d):
        n = mal = unres = gov = 0
        edges = Counter()
        for f in sorted(d.glob("*.json")):
            rec = json.loads(f.read_text(encoding="utf-8"))
            closed = {e["name"] for e in rec["ports"] + rec["signals"]}
            for e in rec["ports"] + rec["signals"]:
                n += 1
                for r in e.get("relationship") or []:
                    t = str(r.get("type", ""))
                    edges[t] += 1
                    if t not in _EDGE_SET:
                        mal += 1
                    for tg in r.get("targets") or []:
                        if tg not in closed and "." not in str(tg):
                            unres += 1
                gov += any(r.get("type") in GOVERNING_EDGES for r in e.get("relationship") or [])
        return n, mal, unres, gov, sum(edges.values())

    na, mala, unra, gova, ea = stats(a)
    nb_, malb, unrb, govb, eb = stats(b)
    if not nb_:
        print(f"{b}/ is empty -- run the parse cell first")
        return
    print(f"{'':30} {'before':>10} {'after':>10} {'delta':>10}")
    for lbl, x, y in (("elements", na, nb_), ("edges", ea, eb),
                      ("malformed edge types", mala, malb),
                      ("unresolved targets", unra, unrb),
                      ("elements w/ governing edge", gova, govb)):
        print(f"{lbl:30} {x:10} {y:10} {y - x:+10}")
    if na and nb_ and na != nb_:
        print(f"\n   WARNING: element counts differ ({na} vs {nb_}). A metric delta could be "
              f"a closed-set delta.")
    print()
    for lbl, d in (("before", a), ("after", b)):
        print(f"   {lbl}:", end="")
        governing_coverage(d, rtl_dir=rtl_dir)


def parse_version_of(out_dir):
    """The stamps present in a directory, as a set. Files written before stamping report
    "unstamped", which is deliberate: an unknown version is not the same as a matching one
    and must not silently pass."""
    seen = set()
    for f in sorted(Path(out_dir).glob("*.json")):
        v = json.loads(f.read_text(encoding="utf-8")).get("_version")
        seen.add("unstamped" if not v else
                 f"{v.get('edge_set')}/{v.get('prompt_sha')}/{v.get('edge_types')}")
    return seen


def assert_one_version(out_dir, label=""):
    """Raise rather than warn. A mixed directory produces numbers that look ordinary and
    are computed over two different vocabularies -- the failure mode nothing downstream
    announces."""
    seen = parse_version_of(out_dir)
    if len(seen) > 1:
        raise AssertionError(
            f"{label or out_dir}: files from more than one parse version -- "
            f"{sorted(seen)}. Re-parse the directory or split it; a metric across two "
            f"edge sets is not a comparison.")
    return next(iter(seen)) if seen else None


def report(out_dir=None):
    """THE GATE. Read this before the annotation is used for anything.

    There is no positive-role rate to look at any more -- `role` is prose, so there is no
    label to count. What replaces it is the violation rate: the share of elements whose
    annotation used verdict or hedging vocabulary. That is the direct measure of whether
    the parser stayed on its side of the line.

      violations        should be ~0. A non-trivial rate means the annotator is describing
                        significance, and the asset stage is then reading its own rubric
                        back from its input.
      coverage          annotated / declared. Must be 1.0; anything else is a C-1 failure.
      no relationship   an element with a functional role and no coupling means the
                        occurrence scan under-ran. High rates make the DoI stage worthless.
      edge mix          GATES is the edge a value-flow reading misses. If it is rare
                        relative to SOURCES, the branch-condition instruction is not
                        landing, and that is the single most consequential miss.
    """
    d = Path(out_dir or OUT_DIR)
    files = sorted(d.glob("*.json"))
    if not files:
        print(f"no annotations in {d}/ -- run annotate_all() first")
        return
    ver = assert_one_version(d)
    print(f"   parse version: {ver}")

    tot = Counter()
    edges = Counter()
    roles_len = Counter()
    rows = []
    for f in files:
        p = json.loads(f.read_text(encoding="utf-8"))
        elems = p["ports"] + p["signals"]
        n = len(elems)
        iss = p.get("_issues") or {}
        # _offenders is keyed by element, valued by how many banned words that element
        # used. The rate that means anything is over ELEMENTS, so count keys -- summing
        # the values counts word hits and can exceed the element count.
        bad = len(iss.get("_offenders", {}))
        iso = sum(1 for e in elems
                  if not e["relationship"]
                  or all(str(r.get("type", "")).upper() == "ISOLATED" for r in e["relationship"]))
        for e in elems:
            roles_len[len(e.get("role") or [])] += 1
            for r in e.get("relationship") or []:
                edges[str(r.get("type", "")).upper()] += 1
        for k, v in iss.items():
            if k != "_offenders":
                tot[k] += sum(v.values())
        rows.append((f.stem, n, bad, iso))

    N = sum(r[1] for r in rows)
    B = sum(r[2] for r in rows)
    I = sum(r[3] for r in rows)
    print(f"{'module':26} {'elems':>6} {'bad':>6} {'bad%':>7} {'isolated':>9}")
    for stem, n, bad, iso in rows:
        print(f"{stem:26} {n:6} {bad:6} {100 * bad / n if n else 0:6.1f}% {iso:9}")
    print(f"{'TOTAL':26} {N:6} {B:6} {100 * B / N if N else 0:6.1f}% {I:9}")

    print(f"\nelements using verdict/hedging words : {B}/{N} = "
          f"{100 * B / N if N else 0:.1f}%   (target ~0; this is the gate)")
    if tot.get("banned_word"):
        print(f"   word hits across those elements    : {tot['banned_word']}")
    print(f"isolated elements          : {I}/{N} = {100 * I / N if N else 0:.1f}%")
    print(f"roles per element          : "
          + ", ".join(f"{k}->{v}" for k, v in sorted(roles_len.items())))
    print(f"\nedge mix ({sum(edges.values())} edges):")
    for e, c in edges.most_common():
        print(f"   {e:16} {c:6}  {100 * c / sum(edges.values()):5.1f}%")
    g, s = edges.get("GATES", 0), edges.get("SOURCES", 0)
    print(f"\n   GATES:SOURCES = {g}:{s}")
    governing_coverage(d)
    guard_coverage(d)
    reciprocity_coverage(d)
    export_coverage(d)
    audit_isolated(d)
    audit_cross_record(d)
    audit_dead_ends(d)
    if tot:
        print("\nother issues (parse defects, not findings):")
        for k, v in sorted(tot.items()):
            print(f"   {k:20} {v}")
