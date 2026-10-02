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
import json
import re
from collections import Counter
from pathlib import Path

import rtl_parse
from prompts_parse_v3 import (BANNED_IN_OUTPUT, EDGE_TYPES, PARSE_ELEMENTS_V3_SYSTEM,
                              PARSE_PORTS_V3_SYSTEM, PARSE_SIGNALS_V3_SYSTEM,
                              audit_against_corpus)

CACHE_DIR = Path("parsed_tuning18")      # the v1 closed set, used as the coverage reference
OUT_DIR = Path("parsed_v3_tuning18")

_EDGE_SET = set(EDGE_TYPES)
_MAX = {"function": 12, "functionality": 45, "evidence": 40}


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
    text = " ".join([str(rec.get("function", "")), str(rec.get("functionality", "")),
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
        if ty not in _EDGE_SET:
            issues["unknown_edge"][ty or "<missing>"] += 1
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
               "dead_batch", "missing")}
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
                   "function": a.get("function", "unclear from RTL"),
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
                   "dead_batch", "missing")}
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
        parsed = _assemble(stem, mech, pann, sann, issues)
        cache = CACHE_DIR / f"{stem}.json"
        if cache.exists():
            verify_against_cache(parsed, json.loads(cache.read_text(encoding="utf-8")), stem)
        (OUT_DIR / f"{stem}.json").write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        bad = len(issues["_offenders"])
        print(f"[ok  ] {stem:24s} {len(parsed['ports'])}p / {len(parsed['signals'])}s"
              + (f"   {bad} element(s) used verdict/hedging words" if bad else ""))
        out[stem] = parsed
    return {**load_all(modules), **out}


def _assemble(stem, mech, pann, sann, issues):
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
                 "function": a.get("function", "unclear from RTL"),
                 "functionality": a.get("functionality", ""),
                 "role": a.get("role") or [],
                 "relationship": a.get("relationship") or [],
                 "evidence": a.get("evidence", "")}, closed, issues, where))
        for e in ent["signals"]:
            a = sann.get((en, e["name"]), {})
            where = f"{stem}/{en}/{e['name']}"
            if not a:
                issues["missing"][where] += 1
            signals_out.append(check_annotation(
                {"entity": en, **e, "kind": a.get("kind", "signal"),
                 "function": a.get("function", "unclear from RTL"),
                 "functionality": a.get("functionality", ""),
                 "role": a.get("role") or [],
                 "relationship": a.get("relationship") or [],
                 "evidence": a.get("evidence", "")}, closed, issues, where))
    return {"module": stem, "entities": [e["entity"] for e in mech["entities"]],
            "ports": ports_out, "signals": signals_out,
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
                                 ("entity", "name", "function", "functionality",
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
        e["relationship"] = out or [{"type": "ISOLATED", "targets": []}]
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

GOVERNING_EDGES = ("GATES", "SELECTS", "CONSTRAINS", "OVERRIDES")


def governing_coverage(out_dir=None, rtl_dir="RTL_data"):
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
    rtl = Path(rtl_dir)
    if not rtl.exists():
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


def compare_parses(old_dir, new_dir=None, rtl_dir="RTL_data"):
    """Side-by-side on the numbers a re-parse is meant to move.

    The point of a re-parse is not "the output changed" -- it will, the stage is
    non-deterministic. It is whether the three defects the prompt fix targeted actually
    closed, and whether the coupling the asset stage cannot reconstruct got denser. Anything
    else that moved is noise between two samples of the same prompt, and the element counts
    are asserted identical so a difference cannot be a closed-set difference.
    """
    a, b = Path(old_dir), Path(new_dir or OUT_DIR)

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
    if tot:
        print("\nother issues (parse defects, not findings):")
        for k, v in sorted(tot.items()):
            print(f"   {k:20} {v}")
