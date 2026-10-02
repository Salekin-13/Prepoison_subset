"""What the asset-generation LLM did, and what it missed: exact digests built by code from its traces, then an LLM summary
of each digest, checked by code. For the traced arm (m7e194es0ist) and, for the behaviour table, the earlier arms.

1. behaviour_table(versions)  (code, no model)  per version, over its runs on the 15 reference modules:
     objectives chosen; four questions answered per concept, negative answers, confidentiality / availability raised;
     structured map citations (traced arm: references whose occurrence + edge verify) and a text proxy comparable to
     the earlier audit ("a concept cites a map fact": a relationship type name, 'occurrence', or 'line <n>' in its
     reasoning); hypotheses; exclusions with a reason; P / R / emitted.
2. module_digest(version, module)  (code, no model)  exact facts per module over the runs: purpose and flows; each
     concept with its four answers (and the line text), references (role, cited line, edge, citation status, listed by
     the reference or not), influence points, hypotheses, exclusions; and the blind spots by code:
       - reference entries missed, per run, and where each ended up (influence point, exclusion with its reason, only in
         a flow path, mentioned in a hypothesis, nowhere);
       - flow-graph elements never considered (on a PATH as a store or exit, a control-only source, or self-updating, but
         in no reference, influence point, exclusion or flow path of that run);
       - reported elements the reference does not list, by role and citation status;
       - citation statuses that are not 'verified'; run-to-run stability of the reported elements.
3. summarize(client, model, version)  (LLM)  one call per module on its digest, then one synthesis call; every summary
     is checked by code: element names it mentions that are not in that module's digest are listed (_validation.json).

Outputs: assetgen_meta/traces_ist/<version>/_digest/<module>.json, _summaries/<module>.md, _summaries/_overall.md,
_summaries/_validation.json. The reference ("listed by the reference") is used for analysis only, never in a prompt.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT / "src"), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eval_assets as ea          # noqa: E402
import trace_check as TC          # noqa: E402

OUT = HERE / "traces_ist"
FLOW = HERE / "traced_inputs" / "tuning" / "_flow"
QS = ("confidentiality", "integrity", "availability", "undermined behavior")
# a map fact in a concept's reasoning: a relationship type written as the map writes it (upper case), an occurrence ID, or
# a cited line number. Case-sensitive on the types, so the plain words "gates" or "copies" do not count.
MAPFACT = re.compile(r"\b(CARRIES|COPIES|SOURCES|DERIVES_FROM|SEQUENCES|CLOCKED_BY|RESETS|RESET_BY|SELECTS|SELECTED_BY|GATES|"
                     r"GATED_BY|CONSTRAINS|CONSTRAINED_BY|CONNECTS)\b|\b[Oo]ccurrence (ID )?\d+|\b[Ll]ines? \d+")


def _gt():
    return ea.load_refs()["gt"]


def _mods(gt):
    """The tuning modules with a reference list (RTL_data and the reference; parsed_tuning18 also holds held-out copies)."""
    return sorted(m for m in gt if (ROOT / "data/RTL_data" / f"{m}.vhd").exists())


def _nested(version, k, m, stem="assets_tuning18"):
    """The run's output for the module; when a CIA labelling call answered it (m7e194es0ist2), merged with its answers."""
    d = ROOT / f"runs/{stem}_{version}_r{k}"
    if (d / "_cia" / f"{m}.json").exists():
        import cia_label as CL
        return CL.merged(version, k, m, stem)
    f = d / "_nested" / f"{m}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def _questions(c: dict) -> dict:
    """{question: (answer, evidence)}, answer lower-cased as written: yes / no (ist), yes-rtl / yes-assumed / no /
    unknown (ist2 labelling call); traced arms: "questions" {answer, line}; four-question arms: "security questions"
    {answer, statement}."""
    q = c.get("questions") or c.get("security questions") or {}
    out = {}
    for k in QS:
        a = q.get(k)
        if isinstance(a, dict):
            ans = str(a.get("answer", "")).strip().lower() or None
            out[k] = (ans, a.get("line", a.get("statement")))
    return out


def _yes(a) -> bool:
    return bool(a) and str(a).startswith("yes")


# --------------------------------------------------------------------------------------------- 1. behaviour ---
def behaviour(version: str, reps=(0, 1, 2), stem="assets_tuning18") -> dict:
    gt = _gt(); mods = _mods(gt)
    obj, q_asked, q_answered, neg, yes = Counter(), 0, 0, 0, Counter()
    concepts = mapfact = all_yes = hyp = excl = infl = 0
    verified = refs = cv = 0
    traced = None
    sc = []
    for k in reps:
        d = ROOT / f"runs/{stem}_{version}_r{k}"
        if not d.exists():
            continue
        sc.append(ea.score(d, gt, strict=True, only=set(mods)))
        for m in mods:
            o = _nested(version, k, m, stem)
            if not o:
                continue
            hyp += len(o.get("hypotheses", []) or [])
            excl += len(o.get("exclusions", []) or o.get("excluded values", []) or [])
            if traced is None:
                traced = "questions" in json.dumps(o.get("conceptual assets", [])[:1]) or "use-case flows" in o
            chk = None
            if "use-case flows" in o:
                import traced_inputs as TI
                chk = TC.check_output(o, TI.load_map("tuning", m) or {"ports": [], "signals": []},
                                      TC.numbered_lines(TC.module_input("tuning", m) or ""))
                refs += len(chk["refs"]); verified += sum(r["status"] == "verified" for r in chk["refs"])
                infl += len(chk["influence"])
                cv += len({r["concept"] for r in chk["refs"] if r["status"] == "verified"})
            for c in o.get("conceptual assets", []) or []:
                if not isinstance(c, dict):
                    continue
                concepts += 1
                obj[c.get("security objective")] += 1
                mapfact += bool(MAPFACT.search(str(c.get("reasoning", ""))))
                qs = _questions(c)
                if qs:
                    q_asked += 1
                    q_answered += sum(1 for a, _e in qs.values() if _yes(a) or a in ("no", "unknown"))
                    neg += sum(1 for a, _e in qs.values() if a == "no")
                    for qk, (a, _e) in qs.items():
                        yes[qk] += _yes(a)
                        if a == "yes-assumed":
                            yes[qk + " (assumed)"] += 1
                    all_yes += all(_yes(a) for a, _e in qs.values()) and len(qs) == 4
    n = len(sc) or 1
    return {"version": version, "runs": len(sc), "P": sum(s["precision"] for s in sc) / n, "R": sum(s["recall"] for s in sc) / n,
            "emitted_per_run": sum(s["emit"] for s in sc) / n, "concepts": concepts, "objectives": dict(obj),
            "concepts_with_questions": q_asked, "answers": q_answered, "negative_answers": neg, "yes_by_question": dict(yes),
            "concepts_all_four_yes": all_yes, "concepts_reasoning_cites_map_fact": mapfact,
            "references": refs, "references_citation_verified": verified, "concepts_with_a_verified_citation": cv,
            "influence_points": infl, "hypotheses": hyp, "exclusions": excl}


def behaviour_table(versions=("m7e194es0ism", "m7e194es0ismr", "m7e194es0ismq", "m7e194es0ist"), log=print) -> list[dict]:
    rows = [behaviour(v) for v in versions]
    log("behaviour over the 15 reference modules, all runs of each version (counts are totals over the runs)")
    log(f"   {'version':16s} runs    P     R  emit/run concepts  Integrity  C-yes  A-yes  U-yes  answers  'no'  4x yes  "
        f"map-fact text  verified cites  hypotheses  exclusions")
    for r in rows:
        o = r["objectives"]; y = r["yes_by_question"]
        log(f"   {r['version']:16s} {r['runs']:4d} {r['P']:.3f} {r['R']:.3f} {r['emitted_per_run']:8.1f} {r['concepts']:8d}  "
            f"{o.get('Integrity', 0):5d}/{r['concepts']:<4d} {y.get('confidentiality', 0):5d}  {y.get('availability', 0):5d}  "
            f"{y.get('undermined behavior', 0):5d}  {r['answers']:7d} {r['negative_answers']:5d}  {r['concepts_all_four_yes']:6d}  "
            f"{r['concepts_reasoning_cites_map_fact']:6d}/{r['concepts']:<6d} "
            f"{(str(r['references_citation_verified']) + '/' + str(r['references'])) if r['references'] else '-':>14s}  "
            f"{r['hypotheses']:10d}  {r['exclusions']:10d}")
    return rows


# ------------------------------------------------------------------------------------------------ 2. digest ---
def _where(name: str, obj: dict, chk: dict) -> str:
    if any(r["element"] == name for r in chk["influence"]):
        return "influence point"
    ex = [x for x in chk["exclusions"] if isinstance(x, dict) and x.get("element") == name]
    if ex:
        return f"excluded ({ex[0].get('reason')})"
    if any(name in (f.get("path") or []) for f in chk["flows"]):
        return "only in a flow path"
    if any(name in json.dumps(h) for h in chk["hypotheses"]):
        return "mentioned in a hypothesis"
    if name in json.dumps(obj.get("conceptual assets", [])):
        return "mentioned in a concept's text only"
    return "nowhere in the output"


def module_digest(version: str, m: str, reps=(0, 1, 2), stem="assets_tuning18", gt=None) -> dict:
    import traced_inputs as TI
    gt = gt if gt is not None else _gt()
    mapd = TI.load_map("tuning", m) or {"ports": [], "signals": []}
    lines = TC.numbered_lines(TC.module_input("tuning", m) or "")
    fg = json.loads((FLOW / f"{m}.json").read_text(encoding="utf-8")) if (FLOW / f"{m}.json").exists() else {"paths": {}}
    endpoints = set(fg.get("self_updating", [])) | set(fg.get("control_only_inputs", {}))
    for p in fg["paths"].values():
        endpoints |= set(p["stores"]) | set(p["exits"])
    ref_names = [n for n, _o in gt.get(m, [])]
    runs, reported_runs, missed, fps, unconsidered, statuses = [], Counter(), defaultdict(list), defaultdict(list), Counter(), Counter()
    q_pattern = Counter()
    for k in reps:
        o = _nested(version, k, m, stem)
        if o is None:
            runs.append({"run": k, "missing": True}); continue
        chk = TC.check_output(o, mapd, lines)
        rep = {r["element"] for r in chk["refs"]}
        for r in rep:
            reported_runs[r] += 1
        for r in chk["refs"]:
            statuses[r["status"]] += 1
        for n in ref_names:
            if n not in rep:
                missed[n].append(f"r{k}: {_where(n, o, chk)}")
        for r in chk["refs"]:
            if r["element"] not in ref_names:
                fps[r["element"]].append(f"r{k}: {r['role']}, {r['status']}")
        mentioned = rep | {r["element"] for r in chk["influence"]} | {x.get("element") for x in chk["exclusions"] if isinstance(x, dict)} \
            | {e for f in chk["flows"] for e in (f.get("path") or [])}
        for e in endpoints - mentioned:
            unconsidered[e] += 1
        concepts = []
        for c in o.get("conceptual assets", []) or []:
            if not isinstance(c, dict):
                continue
            qs = _questions(c)
            q_pattern["".join({"yes": "Y", "yes-rtl": "R", "yes-assumed": "a", "no": "n", "unknown": "?"}.get(qs.get(q, (None,))[0], "-")
                              for q in QS)] += 1
            concepts.append({
                "concept": c.get("concept"), "objective": c.get("security objective"),
                "questions": {q: {"answer": a, "line": e, "text": lines.get(TC._int(e), "")[:120]} for q, (a, e) in qs.items()},
                "reasoning": str(c.get("reasoning", ""))[:500],
                "references": [{"element": r["element"], "role": r["role"], "line": r.get("line"), "text": r.get("text", "")[:100],
                                "edge": r.get("edge"), "citation": r["status"], "listed_by_reference": r["element"] in ref_names}
                               for r in chk["refs"] if r["concept"] == c.get("concept")],
                "influence_points": [{"element": r["element"], "role": r["role"], "citation": r["status"]}
                                     for r in chk["influence"] if r["concept"] == c.get("concept")]})
        runs.append({"run": k, "purpose": o.get("module purpose", ""),
                     "flows": [{"flow": f.get("flow"), "value": f.get("value"), "path": f.get("path")} for f in chk["flows"]],
                     "concepts": concepts, "hypotheses": chk["hypotheses"], "exclusions": chk["exclusions"]})
    n = sum(1 for r in runs if not r.get("missing"))
    names = sorted({e["name"] for a in ("ports", "signals") for e in mapd[a]} | set(ref_names))
    return {"module": m, "version": version, "runs_present": n,
            "reference_entries": ref_names,
            "reference_found_in_runs": {nm: n - len(missed.get(nm, [])) for nm in ref_names},
            "reference_missed": dict(missed),
            "reported_not_listed_by_reference": dict(fps),
            "flow_graph_elements_never_considered": {e: c for e, c in sorted(unconsidered.items())},
            "reported_stability": {e: c for e, c in sorted(reported_runs.items(), key=lambda x: (-x[1], x[0]))},
            "citation_statuses": dict(statuses), "question_answer_patterns_CIAU": dict(q_pattern),
            "runs": runs, "_names": names}


def write_digests(version="m7e194es0ist", reps=(0, 1, 2), stem="assets_tuning18", log=print, out_dir: Path | None = None,
                  modules=None) -> dict:
    gt = _gt(); out = {}
    d = Path(out_dir or OUT / version) / "_digest"
    d.mkdir(parents=True, exist_ok=True)
    for m in (modules or _mods(gt)):
        dg = module_digest(version, m, reps, stem, gt)
        (d / f"{m}.json").write_text(json.dumps({k: v for k, v in dg.items() if k != "_names"}, indent=1), encoding="utf-8")
        out[m] = dg
    tot_missed = Counter(w.split(": ", 1)[1].split(" (")[0] for dg in out.values() for ws in dg["reference_missed"].values() for w in ws)
    log(f"digests: {len(out)} modules -> {d}")
    log(f"   where missed reference entries ended up (run-slots): {dict(tot_missed)}")
    log(f"   flow-graph elements never considered (element-runs): {sum(sum(dg['flow_graph_elements_never_considered'].values()) for dg in out.values())}")
    log(f"   citation statuses: {dict(sum((Counter(dg['citation_statuses']) for dg in out.values()), Counter()))}")
    return out


# ------------------------------------------------------------------------------------------------ 3. LLM ---
SYSTEM_MODULE = """You analyse the trace of an asset-identification LLM (the "executor") on one hardware module. You receive a DIGEST that a program computed exactly from the executor's runs and from the module's relationship map. Everything in it is a fact; nothing outside it is.

Write a summary for an engineer who must judge whether the executor's decisions can be trusted.
Rules:
- Use only facts in the digest. Name elements exactly as the digest writes them. Give counts as "n of N runs" or "n of N".
- Mark every judgement that goes beyond the digest with "Interpretation:".
- "listed_by_reference" and the reference fields come from an expert reference list, used here only to locate blind spots.
- Summarize; do not restate the digest.

Sections, in Markdown:
1. What the executor concluded the module does (and whether the runs agree).
2. How it reasoned: the flows it built, the values it questioned, how it answered the four questions (patterns, negative answers, confidentiality), the roles it assigned, and the map evidence it cited (citation statuses).
3. Blind spots:
   a. reference entries it missed, and where each ended up (influence point, exclusion and its reason, only in a flow path, in a hypothesis, nowhere);
   b. flow-graph elements it never considered;
   c. elements it reported that the reference does not list, grouped by role, and whether their citations verify;
   d. citations that do not verify;
   e. run-to-run instability.
4. Verdict, three sentences: what the reasoning gets right, the main blind spot, and (Interpretation:) what would fix it."""

SYSTEM_OVERALL = """You receive per-module summaries of an asset-identification LLM's traces, a behaviour table comparing it with earlier prompt versions, and totals computed by code. Write a cross-module synthesis for an engineer, in Markdown:
1. How the executor reasons now (with module counts), and how its use of the relationship map and of the four security questions changed against the earlier versions (numbers from the behaviour table only).
2. The recurring blind spots, most frequent first, each with the modules where it occurs and its counts.
3. Reasoning that is reliable, with evidence.
4. Three changes that would remove the main blind spots, each marked Interpretation: and tied to a blind spot.
Use only the material given. Name elements and modules exactly. Mark every judgement beyond the material with "Interpretation:"."""


def ask(client, model, system, user, effort="high", max_tokens=32000, poll=10, timeout=3600):
    """One Responses API call in background mode, polled (long analysis calls time out otherwise)."""
    r = client.responses.create(model=model, instructions=system, input=user, reasoning={"effort": effort},
                                max_output_tokens=max_tokens, background=True)
    t0 = time.time()
    while getattr(r, "status", None) in ("queued", "in_progress"):
        if time.time() - t0 > timeout:
            raise TimeoutError(f"response {r.id} still {r.status} after {timeout}s")
        time.sleep(poll)
        r = client.responses.retrieve(r.id)
    return r.output_text, getattr(r, "usage", None), r.status


IDENT = re.compile(r"`([^`]+)`|\b([A-Za-z]\w*(?:[._]\w+)+)\b")
RELTYPES = {"CARRIES", "COPIES", "SOURCES", "DERIVES_FROM", "SEQUENCES", "CLOCKED_BY", "RESETS", "RESET_BY", "SELECTS",
            "SELECTED_BY", "GATES", "GATED_BY", "CONSTRAINS", "CONSTRAINED_BY", "CONNECTS"}
DIGEST_KEYS = {"reference_entries", "reference_found_in_runs", "reference_missed", "reported_not_listed_by_reference",
               "flow_graph_elements_never_considered", "reported_stability", "citation_statuses",
               "question_answer_patterns_CIAU", "listed_by_reference", "runs_present", "influence_points"}


def allowed_names(m: str, dg: dict) -> set:
    """What a summary of module m may name: map elements, reference entries, elements in the outputs, every identifier
    in the module's RTL (constants, generics, instances), sub-unit ports <instance>.<formal>, relationship types and the
    digest's own field names."""
    import traced_inputs as TI
    names = set(dg.get("_names", [])) | {m, dg.get("version", "")} | RELTYPES | DIGEST_KEYS
    for r in dg.get("runs", []):
        for c in r.get("concepts", []):
            names |= {x["element"] for x in c["references"]} | {x["element"] for x in c["influence_points"]}
    txt = TC.module_input("tuning", m) or ""
    names |= set(re.findall(r"[A-Za-z_]\w*", txt.split("=== RELATIONSHIP MAP")[0]))
    mapd = TI.load_map("tuning", m) or {}
    for a in ("ports", "signals"):
        for e in mapd.get(a, []):
            names |= {f"{c.get('instance')}.{c.get('formal')}" for c in e.get("connections", []) or []}
            names |= {c.get("instance", "") for c in e.get("connections", []) or []}
    return names


def check_summary(text: str, names: set) -> list[str]:
    """Identifier-like tokens (with '_' or '.', or in backticks) the summary uses that are not allowed names. A token
    with an index or a wildcard (x(0), x_*) is checked on its base name."""
    out = set()
    for a, b in IDENT.findall(text):
        t = (a or b).strip()
        if not t or " " in t:
            continue
        base = re.sub(r"(\(.*\)|\*|\[.*\])$", "", t)
        if ("_" in t or "." in t) and t not in names and base not in names and not re.fullmatch(r"[\d.]+", t) \
                and not any(n.startswith(base) for n in names if base.endswith("_") or t.endswith("*")):
            out.add(t)
    return sorted(out)


def revalidate(version="m7e194es0ist", log=print) -> dict:
    """Re-check the written summaries against their digests (no model call)."""
    gt = _gt()
    sd = OUT / version / "_summaries"
    val, alln = {}, set()
    for m in _mods(gt):
        f = sd / f"{m}.md"
        if not f.exists():
            continue
        dg = module_digest(version, m, gt=gt)
        a = allowed_names(m, dg)
        alln |= a
        val[m] = check_summary(f.read_text(encoding="utf-8"), a)
    if (sd / "_overall.md").exists():
        val["_overall"] = check_summary((sd / "_overall.md").read_text(encoding="utf-8"), alln | set(_mods(gt)))
    (sd / "_validation.json").write_text(json.dumps(val, indent=1), encoding="utf-8")
    bad = {m: v for m, v in val.items() if v}
    log(f"   validation: {len(val) - len(bad)}/{len(val)} summaries use only names from their digest or RTL"
        + ("" if not bad else f"; other names: {json.dumps(bad)}"))
    return val


def summarize(client, model, version="m7e194es0ist", reps=(0, 1, 2), workers=4, effort="high", log=print,
              stem="assets_tuning18", out_dir: Path | None = None, modules=None) -> dict:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    digests = write_digests(version, reps, stem, log=log, out_dir=out_dir, modules=modules)
    sd = Path(out_dir or OUT / version) / "_summaries"
    sd.mkdir(parents=True, exist_ok=True)
    allowed = {m: allowed_names(m, dg) for m, dg in digests.items()}

    def one(m):
        f = sd / f"{m}.md"
        if f.exists():
            return m, "cached", None
        dg = {k: v for k, v in digests[m].items() if k != "_names"}
        txt, usage, status = ask(client, model, SYSTEM_MODULE, "DIGEST\n" + json.dumps(dg, indent=1), effort=effort)
        f.write_text(txt, encoding="utf-8")
        return m, status, usage

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(one, m) for m in digests]):
            m, st, u = fut.result()
            log(f"   summary {m}: {st}" + (f" (tokens in {u.input_tokens}, out {u.output_tokens})" if u is not None else ""))
    val = {m: check_summary((sd / f"{m}.md").read_text(encoding="utf-8"), allowed[m]) for m in digests}
    rows = behaviour_table(log=lambda *a: None)
    fo = sd / "_overall.md"
    if not fo.exists():
        material = {"behaviour_table": rows,
                    "totals": {"reference_missed_where": dict(Counter(w.split(": ", 1)[1].split(" (")[0] for dg in digests.values()
                                                                     for ws in dg["reference_missed"].values() for w in ws)),
                               "never_considered_element_runs": {m: sum(dg["flow_graph_elements_never_considered"].values()) for m, dg in digests.items()},
                               "citation_statuses": {m: dg["citation_statuses"] for m, dg in digests.items()}},
                    "module_summaries": {m: (sd / f"{m}.md").read_text(encoding="utf-8") for m in digests}}
        txt, usage, status = ask(client, model, SYSTEM_OVERALL, json.dumps(material, indent=1), effort=effort)
        fo.write_text(txt, encoding="utf-8")
        log(f"   overall synthesis: {status}")
    all_names = set().union(*allowed.values())
    val["_overall"] = check_summary(fo.read_text(encoding="utf-8"), all_names | set(digests))
    (sd / "_validation.json").write_text(json.dumps(val, indent=1), encoding="utf-8")
    bad = {m: v for m, v in val.items() if v}
    log(f"   validation: {len(val) - len(bad)}/{len(val)} summaries use only names from their digest"
        + ("" if not bad else f"; names not in the digest: {json.dumps(bad)[:800]}"))
    return val


# ------------------------------------------------------------------------------------------------ self-test ---
def selftest(log=print) -> bool:
    """On the second pilot (stem pilot_tuning18, run 1; three modules), hand-checked against the pilot outputs:
    wdt reports ctrl.enable as stores with a verified citation; hwspinlock misses the reference entry 'sel' and the digest
    says where it went; check_summary flags an invented name and passes a real one."""
    ok = True
    gt = _gt()
    dg = module_digest("m7e194es0ist", "neorv32_wdt", (1,), stem="pilot_tuning18", gt=gt)
    refs = [x for c in dg["runs"][0]["concepts"] for x in c["references"]]
    good = any(x["element"] == "ctrl.enable" and x["role"] == "stores" and x["citation"] == "verified" for x in refs)
    ok &= good
    log(f"   wdt pilot: ctrl.enable stores verified -> {'ok' if good else 'FAIL'}")
    dh = module_digest("m7e194es0ist", "neorv32_hwspinlock", (1,), stem="pilot_tuning18", gt=gt)
    where = dh["reference_missed"].get("sel")
    o = _nested("m7e194es0ist", 1, "neorv32_hwspinlock", stem="pilot_tuning18")
    in_infl = any(ip.get("element") == "sel" for c in o["conceptual assets"] for ip in c.get("influence points", []) or [])
    in_excl = any(x.get("element") == "sel" for x in o.get("exclusions", []) or [])
    want = "influence point" if in_infl else ("excluded" if in_excl else None)
    good = bool(where) and (want is None or want in where[0])
    ok &= good
    log(f"   hwspinlock pilot: 'sel' missed -> {where} (raw output: influence {in_infl}, exclusion {in_excl}) -> {'ok' if good else 'FAIL'}")
    bad = check_summary("The executor stored `ctrl.enable` and invented `ctrl.made_up` and foo_bar.", set(dg["_names"]))
    good = bad == ["ctrl.made_up", "foo_bar"]
    ok &= good
    log(f"   check_summary flags {bad} -> {'ok' if good else 'FAIL'}")
    return ok


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    import os
    os.chdir(ROOT)
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if selftest() else 1)
    behaviour_table()
