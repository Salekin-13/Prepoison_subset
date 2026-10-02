"""Traceability of the traced arm (m7e194es0ist): every decision of the asset-generation LLM is checked against the
relationship map, and a readable trace report is written, so the model's choices are not a black box. No model call.

What the LLM cites (its output contract, section 9 of the prompt): per reported element an "occurrence" (one of the
element's occurrence IDs in the map) and an "edge" ({type, partner}: a relationship record of that element whose "at"
holds the occurrence, or CONNECTS to "<instance>.<formal>" for a sub-unit wiring); per question answered "yes" an RTL
line; per flow its lines; influence points cite like elements.

Per reported element, the check gives one status:
  verified          the element is in the map, the occurrence is its own, the edge exists at that occurrence, and the
                    edge fits the role (fit table below, the same as asset_trace.RULES "default" plus CONNECTS)
  edge, role unfit  the citation is real but the record type does not demonstrate the claimed role
  occurrence only   the occurrence is the element's own; the edge is absent, unknown, or not at that occurrence
  map gap claimed   edge null (the model says the map missed the statement); the occurrence is checked
  invalid           the element is not in the map, or the occurrence is not one of its own
  no citation       no occurrence given
Fit (fits(), = the prompt's section 8): stores <- CLOCKED_BY on a storage edge/mixed element; sets <- an input port's
driving record (CARRIES/SOURCES/GATES/SELECTS/CONSTRAINS) or CONNECTS into a sub-unit, or an internal element's
receiving record (COPIES/DERIVES_FROM/GATED_BY/SELECTED_BY/CONSTRAINED_BY) or CONNECTS from a sub-unit output; computes
<- DERIVES_FROM/GATED_BY/SELECTED_BY/CONSTRAINED_BY; exit port <- an output port's receiving record or CONNECTS from a
sub-unit output (never an internal element). Influence points: driving side only (gates <- GATES, selects <- SELECTS,
constrains <- CONSTRAINS or GATES, forwards <- CARRIES/SOURCES/CONNECTS). A whole record port may cite a field's
record on the same RTL line ("via field"). 'verified' is a necessary condition: the citation is real and fits the role;
it does not prove the element is an asset.

Outputs, per run: assetgen_meta/traces_ist/<version>/r<k>/<module>.md (the report) and _summary.json.
CLI:  python assetgen_meta/trace_check.py <version> [reps...]      (default reps 0 1 2)
      python assetgen_meta/trace_check.py --selftest
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

INPUTS = HERE / "traced_inputs"
OUT = HERE / "traces_ist"
DRIVING = {"CARRIES", "SOURCES", "GATES", "SELECTS", "CONSTRAINS"}
RECEIVING = {"COPIES", "DERIVES_FROM", "GATED_BY", "SELECTED_BY", "CONSTRAINED_BY"}
IN_MODES, OUT_MODES = ("in", "inout"), ("out", "inout", "buffer")
FIT, INFL = "reference", "influence"          # the two fit tables, as the prompt's section 8 states them


def fits(kind: str, role: str, t: str, e: dict, conn_mode) -> bool:
    """Section 8 of the prompt. conn_mode: the connection's port direction for a CONNECTS edge (None if unknown).
    reference: stores <- CLOCKED_BY on a storage edge/mixed element; sets <- an input port's driving record or a CONNECTS
    into a sub-unit, or an internal element's receiving record or a CONNECTS from a sub-unit output; computes <- a
    receiving DERIVES_FROM/GATED_BY/SELECTED_BY/CONSTRAINED_BY; exit port <- an output port's receiving record or a
    CONNECTS from a sub-unit output (never an internal element). influence: driving side only."""
    mode = (e.get("boundary") or {}).get("mode")
    into = conn_mode in IN_MODES or conn_mode is None          # the element's value goes into the sub-unit
    outof = conn_mode in OUT_MODES or conn_mode is None        # the sub-unit drives the element
    if kind == FIT:
        if role == "stores":
            return t == "CLOCKED_BY" and e.get("storage") in ("edge", "mixed")
        if role == "sets":
            if mode in IN_MODES:
                return t in DRIVING or (t == "CONNECTS" and into)
            if mode is None:
                return t in RECEIVING or (t == "CONNECTS" and outof)
            return False
        if role == "computes":
            # a plain internal signal driven by a sub-unit's output carries the value that sub-unit computes
            return t in {"DERIVES_FROM", "GATED_BY", "SELECTED_BY", "CONSTRAINED_BY"} or \
                (t == "CONNECTS" and mode is None and "." not in str(e.get("name", "")) and conn_mode in OUT_MODES)
        if role == "exit port":
            return mode in OUT_MODES and (t in RECEIVING or (t == "CONNECTS" and outof))
        return False
    return {"gates": t == "GATES", "selects": t == "SELECTS", "constrains": t in ("CONSTRAINS", "GATES"),
            "forwards": t in ("CARRIES", "SOURCES", "CONNECTS")}.get(role, False)
STATUSES = ("verified", "edge, role unfit", "occurrence only", "map gap claimed", "invalid", "no citation")


# ----------------------------------------------------------------------------------------------- loading ---
def parse_map_text(text: str) -> dict:
    """The ELEMENTS AND RECORDS section of a traced input (or an example's excerpt) -> {"ports", "signals"} with
    occurrences [{id, line}], relationship [...], connections [...]. Lines outside that section are ignored."""
    sec = text.split("=== RELATIONSHIP MAP: ELEMENTS AND RECORDS", 1)
    if len(sec) < 2:
        return {"ports": [], "signals": []}
    body = sec[1].split("\n", 1)[1].split("=== RELATIONSHIP MAP: FLOW GRAPH", 1)[0]
    out, cur = {"ports": [], "signals": []}, None
    for l in body.split("\n"):
        if l.startswith("PORT ") or l.startswith("SIGNAL "):
            tag, js = l.split(" ", 1)
            cur = json.loads(js)
            cur.setdefault("occurrences", []); cur.setdefault("relationship", [])
            out["ports" if tag == "PORT" else "signals"].append(cur)
        elif l.startswith("    ") and cur is not None and l.strip().startswith("{"):
            o = json.loads(l)
            if "occurrences" in o:
                cur["occurrences"] += o["occurrences"]
            elif "type" in o:
                cur["relationship"].append(o)
            else:
                for k in ("constant_drivers", "configuration", "connections"):
                    if k in o:
                        cur.setdefault(k, []).extend(o[k])
    return out


def numbered_lines(text: str) -> dict[int, str]:
    rtl = text.split("=== RELATIONSHIP MAP", 1)[0]
    out = {}
    for l in rtl.split("\n"):
        if "|" in l and l.split("|", 1)[0].strip().isdigit():
            n, s = l.split("|", 1)
            out[int(n)] = s.strip()
    return out


def module_input(split: str, m: str) -> str | None:
    p = INPUTS / split / f"{m}.txt"
    return p.read_text(encoding="utf-8") if p.exists() else None


class MapIndex:
    def __init__(self, mapd: dict, module: str | None = None):
        self.module = module
        self.by = {}
        for a in ("ports", "signals"):
            for e in mapd.get(a, []):
                self.by.setdefault(e["name"], []).append(e)

    def fields(self, name, entity=None):
        return [e for n, es in self.by.items() if n.startswith(str(name) + ".") for e in es
                if entity is None or e.get("entity") == entity]

    def get(self, name, entity=None):
        c = self.by.get(name, [])
        if entity:
            exact = [e for e in c if e.get("entity") == entity]
            if exact:
                return exact[0]
        return c[0] if c else None


# ------------------------------------------------------------------------------------------------ checking ---
def _transport(e: dict, module: str | None) -> bool:
    """A transport record (bus transaction record type) or clock / reset input, by meta_tools.convention_filter, which
    reads the element's declared type from parsed_tuning18/<module>.json. False when the module is unknown."""
    if not module or not (ROOT / "data/parsed_tuning18" / f"{module}.json").exists():
        return False
    import os
    import meta_tools as mt
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        return not mt.convention_filter({module: [(e.get("entity", ""), e.get("name", ""), "")]})[module]
    finally:
        os.chdir(cwd)


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def check_citation(ix: MapIndex, name, entity, role, occ, edge, fit_table) -> dict:
    e = ix.get(name, entity)
    res = {"element": name, "entity": entity, "role": role, "occurrence": occ, "edge": edge}
    if e is None:
        return {**res, "status": "invalid", "why": "element not in the map"}
    occ_i = _int(occ)
    lines = {o["id"]: o["line"] for o in e.get("occurrences", [])}
    if occ_i is None:
        return {**res, "status": "no citation", "why": "no occurrence ID"}
    if occ_i not in lines:
        return {**res, "status": "invalid", "why": f"occurrence {occ} is not one of the element's ({len(lines)} occurrences)"}
    res["line"] = lines[occ_i]
    if edge is None:
        return {**res, "status": "map gap claimed", "why": "edge null"}
    if not isinstance(edge, dict):
        return {**res, "status": "occurrence only", "why": "edge not an object"}
    t, p = str(edge.get("type", "")).upper(), edge.get("partner")
    found, conn_mode = False, None
    if t == "CONNECTS":
        for c in e.get("connections", []) or []:
            if f"{c.get('instance')}.{c.get('formal')}" == p and occ_i in (c.get("at") if isinstance(c.get("at"), list) else [c.get("at")]):
                found, conn_mode = True, c.get("mode")
                break
    else:
        found = any(r.get("type") == t and p in r.get("targets", []) and occ_i in (r.get("at") or [])
                    for r in e.get("relationship", []) or [])
    via = ""
    if not found and t != "CONNECTS" and not _transport(e, ix.module):
        # a whole record (a port named whole): its records sit on its fields; accept a field's record of that type and
        # partner whose occurrence is on the same RTL line as the cited occurrence of the record. Never for a transport
        # record (bus transactions): that route reported whole bus ports in m7e194es0ist (98 of 112 such references).
        for f in ix.fields(name, e.get("entity")):
            fl = {o["id"]: o["line"] for o in f.get("occurrences", [])}
            if any(r.get("type") == t and p in r.get("targets", []) and any(fl.get(i) == lines[occ_i] for i in (r.get("at") or []))
                   for r in f.get("relationship", []) or []):
                found, via = True, f" (via field {f['name']})"
                break
    if not found:
        return {**res, "status": "occurrence only", "why": f"no {t} record to {p!r} at occurrence {occ}"}
    mode = (e.get("boundary") or {}).get("mode")
    ok = fits(fit_table, role, t, e, conn_mode)
    if t == "CONNECTS" and ok:
        via = f" (via connection, mode {conn_mode})"
    return {**res, "status": "verified" if ok else "edge, role unfit",
            "why": via.strip() if ok else f"{t} does not demonstrate '{role}'{via}" + (f" (mode {mode}, storage {e.get('storage')})" if role in ("stores", "sets", "exit port") else "")}


def check_output(obj: dict, mapd: dict, lines: dict[int, str], module: str | None = None) -> dict:
    ix = MapIndex(mapd, module or obj.get("module name"))
    refs, infl, qs, flows = [], [], [], []
    for f in obj.get("use-case flows", []) or []:
        if isinstance(f, dict):
            ls = [_int(x) for x in f.get("lines", []) or []]
            flows.append({**f, "lines_ok": sum(1 for x in ls if x in lines), "lines_n": len(ls)})
    for c in obj.get("conceptual assets", []) or []:
        if not isinstance(c, dict):
            continue
        for q, a in (c.get("questions") or {}).items():
            ans = str(a.get("answer", "")).lower() if isinstance(a, dict) else ""
            if ans.startswith("yes") or ans == "no":          # every yes and every no must cite a real RTL line
                ln = _int(a.get("line"))
                qs.append({"concept": c.get("concept"), "question": q, "answer": ans, "line": ln, "ok": ln in lines,
                           "text": lines.get(ln, ""), "via": a.get("via"), "reason": a.get("reason")})
        for s in c.get("related structural assets", []) or []:
            if isinstance(s, dict):
                refs.append({"concept": c.get("concept"), **check_citation(ix, s.get("asset rtl"), s.get("entity"), s.get("realization"),
                                                                           s.get("occurrence"), s.get("edge"), FIT)})
        for s in c.get("influence points", []) or []:
            if isinstance(s, dict):
                infl.append({"concept": c.get("concept"), **check_citation(ix, s.get("element"), s.get("entity"), s.get("role"),
                                                                           s.get("occurrence"), s.get("edge"), INFL)})
    for r in refs + infl:
        if r.get("line"):
            r["text"] = lines.get(r["line"], "")
    for r in refs:                       # influence points by code: what gates, selects or constrains the element's value
        e = ix.get(r["element"], r.get("entity"))
        r["influenced_by"] = sorted({t for x in ((e or {}).get("relationship") or [])
                                     if x.get("type") in ("GATED_BY", "SELECTED_BY", "CONSTRAINED_BY") for t in x.get("targets", [])})
    return {"refs": refs, "influence": infl, "questions": qs, "flows": flows,
            "hypotheses": obj.get("hypotheses", []) or [], "exclusions": obj.get("exclusions", []) or [],
            "purpose": obj.get("module purpose", "")}


# ------------------------------------------------------------------------------------------------ report ---
def _esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def module_report(m: str, chk: dict, gt_hits: set | None = None) -> str:
    L = [f"# {m}", "", f"**Purpose (model):** {_esc(chk['purpose'])}", "", "## Use-case flows", "",
         "| flow | value | path | lines (cited / in RTL) |", "|---|---|---|---|"]
    for f in chk["flows"]:
        L.append(f"| {_esc(f.get('flow'))} | {_esc(f.get('value'))} | {_esc(', '.join(map(str, f.get('path', []) or [])))} | "
                 f"{f['lines_n']} / {f['lines_ok']} |")
    concepts = []
    for r in chk["refs"]:
        if r["concept"] not in concepts:
            concepts.append(r["concept"])
    for c in concepts:
        L += ["", f"## Concept: {_esc(c)}", ""]
        for q in [q for q in chk["questions"] if q["concept"] == c]:
            L.append(f"- {q['question']}: {q.get('answer', 'yes')}, line {q['line']} "
                     f"{'`' + _esc(q['text']) + '`' if q['ok'] else '(LINE NOT IN RTL)'}"
                     + (f" via {_esc(q['via'])}" if q.get("via") else "") + (f" -- {_esc(q['reason'])}" if q.get("reason") else ""))
        L += ["", "| element | entity | role | occurrence -> line | edge | status | why |" + (" reference |" if gt_hits is not None else ""),
              "|---|---|---|---|---|---|---|" + ("---|" if gt_hits is not None else "")]
        for r in [r for r in chk["refs"] if r["concept"] == c]:
            e = r.get("edge")
            es = f"{e.get('type')} {e.get('partner')}" if isinstance(e, dict) else "null"
            L.append(f"| {_esc(r['element'])} | {_esc(r['entity'])} | {r['role']} | {r['occurrence']} -> {r.get('line', '?')} "
                     f"`{_esc(r.get('text', ''))[:90]}` | {_esc(es)} | {r['status']} | {_esc(r.get('why', ''))} |"
                     + (f" {'hit' if r['element'] in gt_hits else 'not listed'} |" if gt_hits is not None else ""))
        inf = [r for r in chk["influence"] if r["concept"] == c]
        if inf:
            L += ["", "Influence points (model): " + "; ".join(f"{_esc(r['element'])} ({r['role']}, {r['status']})" for r in inf)]
        byc = {r["element"]: r.get("influenced_by", []) for r in chk["refs"] if r["concept"] == c and r.get("influenced_by")}
        if byc:
            L += ["", "Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): "
                  + "; ".join(f"{_esc(k)} <- {', '.join(map(_esc, v[:8]))}{' ...' if len(v) > 8 else ''}" for k, v in byc.items())]
    if chk["hypotheses"]:
        L += ["", "## Hypotheses (not reported)", ""] + [f"- {_esc(h.get('value'))}: {h.get('question')}; missing premise: {_esc(h.get('missing premise'))}"
                                                         for h in chk["hypotheses"] if isinstance(h, dict)]
    if chk["exclusions"]:
        by = {}
        for x in chk["exclusions"]:
            if isinstance(x, dict):
                by.setdefault(x.get("reason"), []).append(x.get("element"))
        L += ["", "## Exclusions", ""] + [f"- {k}: {', '.join(map(str, v))}" for k, v in by.items()]
    return "\n".join(L) + "\n"


def summarize(chk_by_mod: dict) -> dict:
    c = Counter(r["status"] for ch in chk_by_mod.values() for r in ch["refs"])
    ci = Counter(r["status"] for ch in chk_by_mod.values() for r in ch["influence"])
    q = [x for ch in chk_by_mod.values() for x in ch["questions"]]
    fl = [x for ch in chk_by_mod.values() for x in ch["flows"]]
    n = sum(c.values())
    qy = [x for x in q if x.get("answer", "yes").startswith("yes")]
    qn = [x for x in q if x.get("answer") == "no"]
    return {"refs": n, "ref_status": {s: c[s] for s in STATUSES}, "verified_share": c["verified"] / n if n else 0.0,
            "influence": sum(ci.values()), "influence_status": {s: ci[s] for s in STATUSES},
            "yes_answers": len(qy), "yes_with_rtl_line": sum(x["ok"] for x in qy),
            "no_answers": len(qn), "no_with_rtl_line": sum(x["ok"] for x in qn),
            "flows": len(fl), "flow_lines_cited": sum(x["lines_n"] for x in fl), "flow_lines_in_rtl": sum(x["lines_ok"] for x in fl),
            "hypotheses": sum(len(ch["hypotheses"]) for ch in chk_by_mod.values()),
            "exclusions": sum(len(ch["exclusions"]) for ch in chk_by_mod.values())}


def run(version: str, reps=(0, 1, 2), split: str = "tuning", stem: str = "assets_tuning18", gt: dict | None = None, write=True) -> dict:
    import traced_inputs as TI
    res = {}
    for k in reps:
        d = ROOT / f"runs/{stem}_{version}_r{k}" / "_nested"
        chk_by_mod = {}
        for f in sorted(d.glob("*.json")):
            m = f.stem
            text = module_input(split, m)
            mapd = TI.load_map(split, m) or {"ports": [], "signals": []}
            obj = json.loads(f.read_text(encoding="utf-8"))
            if (d.parent / "_cia" / f"{m}.json").exists():        # m7e194es0ist2: the labelling call's answers
                import cia_label as CL
                obj = CL.merged(version, k, m, stem)
            chk_by_mod[m] = check_output(obj, mapd, numbered_lines(text or ""), m)
            if write:
                o = OUT / version / f"r{k}"
                o.mkdir(parents=True, exist_ok=True)
                hits = {n for n, _o in gt[m]} if gt and m in gt else None
                (o / f"{m}.md").write_text(module_report(m, chk_by_mod[m], hits), encoding="utf-8")
        s = summarize(chk_by_mod)
        if write:
            (OUT / version / f"r{k}" / "_summary.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
        res[k] = {"summary": s, "checks": chk_by_mod}
    return res


def cite_filter(version: str, reps=(0, 1, 2), keep=("verified",), split="tuning", stem="assets_tuning18") -> list[dict]:
    """Evaluation-layer row: each run's flat list keeping only references whose citation status is in `keep`."""
    out = []
    r = run(version, reps, split, stem, write=False)
    for k in reps:
        lst = {}
        for m, ch in r[k]["checks"].items():
            seen = set()
            lst[m] = []
            for x in ch["refs"]:
                key = (x["entity"] or "", x["element"])
                if x["status"] in keep and key not in seen:
                    seen.add(key)
                    lst[m].append((key[0], key[1], ""))
        out.append(lst)
    return out


# ------------------------------------------------------------------------------------------------ self-test ---
def selftest(log=print) -> bool:
    """(1) parse_map_text on a real traced input returns every element and record of the JSON map (occurrence IDs and
    record types/targets/at equal); (2) hand-made citations on neorv32_wdt (hand-read from the map lines printed by
    traced_inputs): ctrl.lock occurrence with its CLOCKED_BY clk_i -> stores verified; the same with role sets -> unfit;
    a wrong occurrence -> invalid; a made-up partner -> occurrence only; an unknown element -> invalid."""
    import traced_inputs as TI
    ok = True
    for m in ("neorv32_wdt", "neorv32_bus"):
        txt = module_input("tuning", m)
        a, b = parse_map_text(txt), TI.load_map("tuning", m)
        def sig(d):
            return sorted((e["entity"], e["name"], tuple(sorted(o["id"] for o in e["occurrences"])),
                           tuple(sorted((r["type"], tuple(r.get("targets", [])), tuple(r.get("at", []))) for r in e.get("relationship", []))))
                          for x in ("ports", "signals") for e in d[x])
        def sig_merged(d):   # targets of a record split over several lines are re-joined
            rows = []
            for x in ("ports", "signals"):
                for e in d[x]:
                    rs = {}
                    for r in e.get("relationship", []):
                        rs.setdefault((r["type"], tuple(r.get("at", []))), []).extend(r.get("targets", []))
                    rows.append((e["entity"], e["name"], tuple(sorted(o["id"] for o in e["occurrences"])),
                                 tuple(sorted((t, tuple(sorted(tg)), at) for (t, at), tg in rs.items()))))
            return sorted(rows)
        good = sig_merged(a) == sig_merged(b)
        ok &= good
        log(f"   parse_map_text {m}: {sum(len(a[x]) for x in a)} elements, same occurrences and records as the JSON map: {'ok' if good else 'MISMATCH'}")
    mapd = TI.load_map("tuning", "neorv32_wdt")
    lock = next(e for e in mapd["signals"] if e["name"] == "ctrl.lock")
    clk = next(r for r in lock["relationship"] if r["type"] == "CLOCKED_BY")
    occ = clk["at"][0]
    ix = MapIndex(mapd)
    cases = [("stores verified", ("ctrl.lock", "neorv32_wdt", "stores", occ, {"type": "CLOCKED_BY", "partner": "clk_i"}), "verified"),
             ("sets unfit", ("ctrl.lock", "neorv32_wdt", "sets", occ, {"type": "CLOCKED_BY", "partner": "clk_i"}), "edge, role unfit"),
             ("wrong occurrence", ("ctrl.lock", "neorv32_wdt", "stores", 999, {"type": "CLOCKED_BY", "partner": "clk_i"}), "invalid"),
             ("made-up partner", ("ctrl.lock", "neorv32_wdt", "stores", occ, {"type": "CLOCKED_BY", "partner": "no_such"}), "occurrence only"),
             ("unknown element", ("no_such_reg", "neorv32_wdt", "stores", 1, None), "invalid"),
             ("map gap", ("ctrl.lock", "neorv32_wdt", "stores", occ, None), "map gap claimed")]
    for lab, args, want in cases:
        got = check_citation(ix, *args, FIT)["status"]
        ok &= got == want
        log(f"   citation {lab}: {got} ({'ok' if got == want else 'WRONG, want ' + want})")
    # whole record port named whole: hwspinlock line 44 `if (bus_req_i.stb = '1') and ... then` (hand-read) holds the
    # record's occurrence and its field bus_req_i.stb's GATES record to lock_q
    # a TRANSPORT record port cannot cite through its field any more: hwspinlock bus_req_i (type bus_req_t) at line 44
    hm = TI.load_map("tuning", "neorv32_hwspinlock")
    hix = MapIndex(hm, "neorv32_hwspinlock")
    rec = hix.get("bus_req_i", "neorv32_hwspinlock")
    occ44 = next(o["id"] for o in rec["occurrences"] if o["line"] == 44)
    got = check_citation(hix, "bus_req_i", "neorv32_hwspinlock", "sets", occ44, {"type": "GATES", "partner": "lock_q"}, FIT)
    ok &= got["status"] == "occurrence only"
    log(f"   citation transport record via field: {got['status']} ({'ok' if got['status'] == 'occurrence only' else 'WRONG, want occurrence only'})")
    # a NON-transport record port still can: muldiv ctrl_i (a control record), on a line where one of its fields has a record
    mm = TI.load_map("tuning", "neorv32_cpu_cp_muldiv")
    mix = MapIndex(mm, "neorv32_cpu_cp_muldiv")
    rec = mix.get("ctrl_i")
    pick = None
    for f in mix.fields("ctrl_i", rec["entity"]):
        fl = {o["id"]: o["line"] for o in f["occurrences"]}
        for r in f.get("relationship", []):
            if r["type"] in ("SOURCES", "GATES", "CARRIES", "SELECTS") and r.get("at"):
                ln = fl.get(r["at"][0])
                ro = [o["id"] for o in rec["occurrences"] if o["line"] == ln]
                if ro:
                    pick = (ro[0], {"type": r["type"], "partner": r["targets"][0]}, f["name"], ln)
                    break
        if pick:
            break
    got = check_citation(mix, "ctrl_i", rec["entity"], "sets", pick[0], pick[1], FIT)
    ok &= got["status"] == "verified"
    log(f"   citation control record via field ({pick[2]} at line {pick[3]}): {got['status']} {got.get('why', '')} "
        f"({'ok' if got['status'] == 'verified' else 'WRONG, want verified'})")
    # computes via a sub-unit output: the cpu signal wired to neorv32_cpu_alu_inst.res_o (direction from the alu's declaration)
    cm = TI.load_map("tuning", "neorv32_cpu")
    cix = MapIndex(cm, "neorv32_cpu")
    sig = next((e, c) for e in cm["signals"] for c in e.get("connections", []) or []
               if c.get("instance") == "neorv32_cpu_alu_inst" and c.get("formal") == "res_o")
    got = check_citation(cix, sig[0]["name"], sig[0]["entity"], "computes", sig[1]["at"],
                         {"type": "CONNECTS", "partner": "neorv32_cpu_alu_inst.res_o"}, FIT)
    ok &= got["status"] == "verified"
    log(f"   citation computes via sub-unit output ({sig[0]['name']} <- res_o): {got['status']} "
        f"({'ok' if got['status'] == 'verified' else 'WRONG, want verified'})")
    # influence points cite the driving side: an element's own GATED_BY record does not show that it gates
    cnt = next(e for e in mapd["signals"] if e["name"] == "cnt")
    gb = next((r for r in cnt["relationship"] if r["type"] == "GATED_BY"), None)
    if gb:
        got = check_citation(ix, "cnt", "neorv32_wdt", "gates", gb["at"][0], {"type": "GATED_BY", "partner": gb["targets"][0]}, INFL)
        ok &= got["status"] == "edge, role unfit"
        log(f"   citation influence from the receiving side: {got['status']} ({'ok' if got['status'] == 'edge, role unfit' else 'WRONG'})")
    # an internal element is never an exit port, even with a receiving record
    got = check_citation(ix, "ctrl.lock", "neorv32_wdt", "exit port", occ, {"type": "CLOCKED_BY", "partner": "clk_i"}, FIT)
    ok &= got["status"] == "edge, role unfit"
    log(f"   citation internal element as exit port: {got['status']} ({'ok' if got['status'] == 'edge, role unfit' else 'WRONG'})")
    return ok


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if selftest() else 1)
    import eval_assets as ea
    v = sys.argv[1]
    reps = tuple(int(x) for x in sys.argv[2:]) or (0, 1, 2)
    gt = ea.load_refs()["gt"]
    for k, r in run(v, reps, gt=gt).items():
        print(f"{v} r{k}: {json.dumps(r['summary'])}")
