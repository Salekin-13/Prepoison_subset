"""Why precision does not improve and why false positives cannot be controlled, read from the evidence the model itself
sees and cites: the occurrence IDs and the relationship map of its input (assetgen_meta/traced_inputs_v2). No model call.

For every element a run lists, the module records:
  label       true positive (TP) or false positive (FP), assigned exactly as eval_assets.score assigns it (strict)
  citation    the role, the cited occurrence ID and the RTL line behind it, the cited edge, and the trace_check status
  signature   what the map says about the element, at three levels (coarse to fine):
              L1 kind      port direction or signal, record field or not, stored / combinational / undriven
              L2 behaviour L1 + updates itself (through any record), controls another element, carries data into an output,
                           is written from an input, feeds or is fed by a sub-unit, clocks or resets others, any local use
              L3 records   L2 + carries data to internal elements, is gated, is reset, the exact set of record types
Readings:
  D1 evidence  Are FPs misreadings of the RTL? Citation status of FPs against TPs.
  D2 shape     Share of FPs whose signature also holds TPs in the same run: those FPs cannot be told apart from hits by
               anything the map records.
  D3 selectors Model-independent. Over every element of every map, the reference's listing rate per signature, and the
               precision a signature-rate selector reaches at a given recall: in-sample (rates fitted to the reference)
               and leave-one-module-out (rates learnt on the other modules: what a rule would carry to a new module). The
               best point is read off the scored set's curve, so both are optimistic; other kinds of method are not bounded.
  D4 pairs     Minimal pairs: a TP and an FP with the same signature in different modules, with the cited occurrence's
               RTL line and the map records side by side.
  D5 concepts  FPs inside concepts with no TP (concepts the reference does not have) against extra elements in concepts
               the reference does have.
  D6 edits     Compliance with the optimization loop's edits A (a stored register needs a use record) and B (a one-clock
               copy of a listed element is not listed): the entries each edit, applied as a code filter, would still
               remove. Near zero means the model followed the edit.
  D7 families  FP and TP per family across run sets: which families an edit moved and which it did not.

    python assetgen_meta/fp_diagnosis.py --selftest
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eval_assets as ea          # noqa: E402
import trace_check as TC          # noqa: E402

INPUTS = HERE / "traced_inputs_v2"
OUT = HERE / "fp_diagnosis"
CTL = {"GATES", "SELECTS", "CONSTRAINS"}
DATA = {"CARRIES", "SOURCES"}
RECV_DATA = {"COPIES", "DERIVES_FROM"}
RECV_CTL = {"GATED_BY", "SELECTED_BY", "CONSTRAINED_BY"}
IN_MODES, OUT_MODES = ("in", "inout"), ("out", "inout", "buffer")


# ------------------------------------------------------------------------------------------------ the map ---
def load_module(split: str, m: str) -> dict:
    """What the model read for module m: the map elements (as trace_check parses them) and the numbered RTL lines."""
    text = (INPUTS / split / f"{m}.txt").read_text(encoding="utf-8")
    mapd = TC.parse_map_text(text)
    els = {}
    ports = defaultdict(dict)                     # entity -> {port or port-field name: mode}
    for cls in ("ports", "signals"):
        for e in mapd[cls]:
            e["_cls"] = "PORT" if cls == "ports" else "SIGNAL"
            els[(e.get("entity"), e["name"])] = e
            if cls == "ports":
                ports[e.get("entity")][e["name"]] = (e.get("boundary") or {}).get("mode")
    # A record field the map marks "not assigned" may be assigned through its whole record (ctrl <= ctrl_nxt): it then
    # takes the storage of the nearest enclosing record signal that has one.
    for (ent, n), e in els.items():
        if e["_cls"] == "SIGNAL" and e.get("storage") == "not assigned" and "." in n:
            parts = n.split(".")
            for i in range(len(parts) - 1, 0, -1):
                rec = els.get((ent, ".".join(parts[:i])))
                if rec and rec["_cls"] == "SIGNAL" and rec.get("storage") in ("edge", "mixed", "none"):
                    e["storage_eff"], e["storage_from_record"] = rec["storage"], rec["name"]
                    break
    return {"module": m, "split": split, "els": els, "ports": ports, "lines": TC.numbered_lines(text), "mapd": mapd}


def features(e: dict, mod: dict) -> dict:
    name, ent = e["name"], e.get("entity")
    ports = mod["ports"].get(ent, {})

    def tclass(t):
        if t == name:
            return "self"
        if t in ports:
            return "port-" + str(ports[t])
        return "int"
    rel = e.get("relationship", []) or []
    drv = [(r["type"], tclass(t)) for r in rel if r.get("type") in CTL | DATA for t in r.get("targets", [])]
    rcv = [(r["type"], tclass(t)) for r in rel if r.get("type") in RECV_DATA | RECV_CTL for t in r.get("targets", [])]
    conns = e.get("connections", []) or []
    mode = (e.get("boundary") or {}).get("mode")
    clk = any(r.get("type") in ("SEQUENCES", "RESETS") for r in rel)
    return {
        "kind": f"port-{mode}" if e["_cls"] == "PORT" else "signal",
        "field": "." in name,
        # "not assigned here": no assignment in this file, of the element or of an enclosing record (an input port, a
        # signal driven by a sub-unit's output, or a field never assigned); a field assigned through its record takes
        # the record's storage (load_module)
        "storage": {"edge": "stored", "mixed": "stored", "none": "comb"}.get(e.get("storage_eff", e.get("storage")), "not assigned here"),
        # a self-update through a data record (cnt <= cnt + 1) or a control record (a_req <= a_req or x: GATES itself)
        "self_update": any(c == "self" for _ty, c in drv + rcv),
        "ctl_out": any(ty in CTL and c != "self" for ty, c in drv),
        "data_out_int": any(ty in DATA and c == "int" for ty, c in drv),
        "data_out_port": any(ty in DATA and c in tuple("port-" + x for x in OUT_MODES) for ty, c in drv),
        "from_input": any(ty in RECV_DATA and c in tuple("port-" + x for x in IN_MODES) for ty, c in rcv),
        "gated": any(ty in RECV_CTL for ty, _c in rcv),
        "sub_in": any(c.get("mode") in IN_MODES for c in conns),
        "sub_out": any(c.get("mode") in OUT_MODES for c in conns),
        "reset": any(r.get("type") == "RESET_BY" for r in rel),
        "clocks_resets": clk,
        "local_use": bool(drv) or clk or any(c.get("mode") in IN_MODES for c in conns),
        "types": tuple(sorted({r.get("type") for r in rel if r.get("type")})),
    }


L2_KEYS = ("self_update", "ctl_out", "data_out_port", "from_input", "sub_in", "sub_out", "clocks_resets", "local_use")
L3_KEYS = L2_KEYS + ("data_out_int", "gated", "reset")
WORDS = {"self_update": "updates itself", "ctl_out": "controls another element", "data_out_port": "carries data into an output",
         "from_input": "written from an input", "sub_in": "feeds a sub-unit", "sub_out": "fed by a sub-unit",
         "local_use": "used here", "data_out_int": "carries data inward", "gated": "is gated", "reset": "is reset",
         "clocks_resets": "clocks or resets other elements"}


def signature(f: dict, level: int) -> tuple:
    base = (f["kind"], "field" if f["field"] else "whole", f["storage"])
    if level == 1:
        return base
    keys = L2_KEYS if level == 2 else L3_KEYS
    s = base + (f"L{level}",) + tuple(k for k in keys if f[k])          # the marker keeps L1 and a flagless L2 apart
    return s + (("records",) + f["types"] if level == 3 else ())


def describe(sig: tuple) -> str:
    """A signature in words."""
    if not sig or len(sig) < 3:
        return " ".join(map(str, sig)) or "?"                           # e.g. ("not in map",)
    kind, field, storage = sig[:3]
    head = f"{kind}{' field' if field == 'field' else ''}, {storage}"
    if len(sig) == 3:                                                   # an L1 signature: no behaviour flags
        return head
    rest = [WORDS.get(x, x) for x in sig[4:] if x != "records"]
    return head + ("; " + ", ".join(rest) if rest else "; no local use")


def family(f: dict) -> str:
    """A readable family (D7). Fixed order of tests."""
    if f["kind"].startswith("port-"):
        return ("input port" if f["kind"] in ("port-in", "port-inout") else "output port") + (" field" if f["field"] else "")
    if f["storage"] == "stored":
        if f["from_input"]:
            return "setting written from an input"
        if f["self_update"] or f["ctl_out"]:
            return "internal state register"
        return "data register"
    if f["sub_in"] or f["sub_out"]:
        return "sub-unit interface signal"
    if f["storage"] == "comb":
        return "combinational decision" if f["ctl_out"] else "combinational data"
    return "signal not assigned here"


# ----------------------------------------------------------------------------------------------- the runs ---
def run_dir(run: str | Path) -> Path:
    p = Path(run)
    return p if p.is_absolute() else ROOT / p


def _nested(d: Path, m: str):
    f = d / "_nested" / f"{m}.json"
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    except Exception:
        return None


def modules_for(split: str) -> list[str]:
    gt = ea.load_refs()["gt"]
    src = ROOT / ("data/RTL_data" if split == "tuning" else "data/RTL_heldout")
    return sorted(m for m in gt if (src / f"{m}.vhd").exists())


def _labels(preds: list[str], ref: list) -> list[str]:
    """TP / FP per prediction index, by the scorer's own matching (eval_assets._hit_idx, strict, as eval_assets.score)."""
    used = set()
    for rname, _o in ref:
        pi = ea._hit_idx({i: preds[i] for i in range(len(preds)) if i not in used}, rname, True)
        if pi is not None:
            used.add(pi)
    return ["TP" if i in used else "FP" for i in range(len(preds))]


def complete(run, split: str = "tuning") -> bool:
    """A run counts only when every module of the split with a reference has its output."""
    d = run_dir(run)
    return all(_nested(d, m) is not None for m in modules_for(split))


def rows_for_run(run, split: str = "tuning", mods: dict | None = None) -> tuple[list[dict], dict]:
    """One row per listed element, in the order of the flat list the scorer reads (first concept wins, as
    meta_tools.flatten); each row labelled by the scorer's own matching on that list."""
    import traced_inputs as TI
    d = run_dir(run)
    gt = ea.load_refs()["gt"]
    names = modules_for(split)
    have = [m for m in names if _nested(d, m) is not None]
    sc = ea.score(d, gt, strict=True, only=set(have))
    flat = ea.load_run(d)
    mods = mods if mods is not None else {}
    rows = []
    for m in have:
        mod = mods.setdefault(m, load_module(split, m))
        obj = _nested(d, m)
        chk = TC.check_output(obj, TI.load_map(split, m) or {"ports": [], "signals": []}, mod["lines"], m)
        status = {}
        for r in chk["refs"]:
            status.setdefault((r.get("entity"), r.get("element")), r.get("status"))
            status.setdefault((None, r.get("element")), r.get("status"))
        concepts = defaultdict(list)
        seen = []
        for c in obj.get("conceptual assets", []) or []:
            if not isinstance(c, dict):
                continue
            for s in c.get("related structural assets", []) or []:
                if not isinstance(s, dict) or not s.get("asset rtl"):
                    continue
                key = (s.get("entity", ""), s.get("asset rtl", ""))
                concepts[key].append(c.get("concept"))
                if key not in [k for k, _ in seen]:
                    seen.append((key, s))
        preds = [x[1] for x in flat.get(m, [])]
        assert [k for k, _ in seen] == [(x[0], x[1]) for x in flat.get(m, [])], f"{d.name}/{m}: flat file differs from flatten(_nested)"
        labs = _labels(preds, gt[m])
        assert sorted(n for n, l in zip(preds, labs) if l == "FP") == sorted(sc["per_module"][m]["fp"]), f"{m}: FP names differ from the scorer"
        for ((ent, n), s), lab in zip(seen, labs):
            e = mod["els"].get((ent, n)) or next((v for k, v in mod["els"].items() if k[1] == n), None)
            f = features(e, mod) if e else None
            occ = TC._int(s.get("occurrence"))
            line = next((o.get("line") for o in (e or {}).get("occurrences", []) if o.get("id") == occ), None)
            edge = s.get("edge") if isinstance(s.get("edge"), dict) else {}
            rows.append({"module": m, "entity": ent, "element": n, "label": lab, "role": s.get("realization"),
                         "concept": concepts[(ent, n)][0], "n_concepts": len(concepts[(ent, n)]),
                         "occurrence": occ, "line": line, "rtl": mod["lines"].get(line, "") if line else "",
                         "edge": f"{edge.get('type')} {edge.get('partner')}" if edge else "",
                         "status": status.get((ent, n)) or status.get((None, n)) or "?",
                         "in_map": e is not None, "features": f,
                         "sig": {lvl: (signature(f, lvl) if f else ("not in map",)) for lvl in (1, 2, 3)},
                         "family": family(f) if f else "not in map"})
    tot = {"tp": sum(1 for r in rows if r["label"] == "TP"), "fp": sum(1 for r in rows if r["label"] == "FP")}
    assert (tot["tp"], tot["fp"]) == (sc["tp"], sc["fp"]), f"labels disagree with the scorer: {tot} vs {sc['tp']}/{sc['fp']}"
    return rows, {"tp": sc["tp"], "fp": sc["fp"], "fn": sc["fn"], "P": sc["precision"], "R": sc["recall"], "modules": have}


# ------------------------------------------------------------------------------------------------ readings ---
def d1_evidence(rows) -> dict:
    out = {}
    for lab in ("TP", "FP"):
        c = Counter(r["status"] for r in rows if r["label"] == lab)
        n = sum(c.values()) or 1
        out[lab] = {"n": sum(c.values()), "statuses": dict(c), "verified_share": round(c.get("verified", 0) / n, 3)}
    return out


def d2_shape(rows, level: int = 2) -> dict:
    by = defaultdict(lambda: {"TP": 0, "FP": 0, "TPmods": set(), "FPmods": set()})
    for r in rows:
        b = by[r["sig"][level]]
        b[r["label"]] += 1
        b[r["label"] + "mods"].add(r["module"])
    fp = sum(b["FP"] for b in by.values()) or 1
    mixed = {s: b for s, b in by.items() if b["TP"] and b["FP"]}
    cross = {s: b for s, b in mixed.items() if b["TPmods"] - b["FPmods"] or b["FPmods"] - b["TPmods"]}
    table = sorted(({"signature": describe(s), "sig": s, "FP": b["FP"], "TP": b["TP"],
                     "TP_modules": sorted(x[8:] for x in b["TPmods"]), "FP_modules": sorted(x[8:] for x in b["FPmods"])}
                    for s, b in by.items()), key=lambda x: (-x["FP"], -x["TP"]))
    return {"level": level, "signatures": len(by), "fp_in_mixed": sum(b["FP"] for b in mixed.values()),
            "fp_in_mixed_share": round(sum(b["FP"] for b in mixed.values()) / fp, 3),
            "fp_in_cross_module_mixed": sum(b["FP"] for b in cross.values()),
            "fp_only_shapes": sum(b["FP"] for b in by.values() if not b["TP"]), "table": table}


def population(split: str, mods: dict) -> tuple[list[dict], dict]:
    """Every element of every map, with whether the reference lists it (a name listed N times marks at most N
    elements). Reference entries whose name is in no map element are counted as unreachable."""
    gt = ea.load_refs()["gt"]
    pop, unreachable, total = [], [], 0
    for m in modules_for(split):
        mod = mods.setdefault(m, load_module(split, m))
        left = Counter(n for n, _o in gt[m])
        total += sum(left.values())
        names = {k[1] for k in mod["els"]}
        unreachable += [(m, n) for n in left if n not in names]
        for (ent, n), e in sorted(mod["els"].items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
            inref = left[n] > 0
            if inref:
                left[n] -= 1
            f = features(e, mod)
            pop.append({"module": m, "element": n, "inref": inref, "sig": {lvl: signature(f, lvl) for lvl in (1, 2, 3)},
                        "family": family(f)})
    return pop, {"elements": len(pop), "reference_entries": total, "unreachable": unreachable}


def _frontier(scored: list[tuple[float, bool]], total: int) -> list[tuple[float, float, int]]:
    """scored: (score, in reference). Sweep a threshold from the top: [(precision, recall, listed)] at each distinct score."""
    pts, k, n = [], 0, 0
    order = sorted(scored, key=lambda x: -x[0])
    for i, (s, inref) in enumerate(order):
        n += 1
        k += inref
        if i + 1 == len(order) or order[i + 1][0] != s:
            pts.append((k / n, k / total, n))
    return pts


def _best_p(pts, r_min: float):
    ok = [p for p in pts if p[1] >= r_min]
    return max(ok, key=lambda x: x[0]) if ok else None


def d3_ceiling(pop: list[dict], meta: dict, targets=(0.5, 0.7, 0.85)) -> dict:
    total = meta["reference_entries"]
    out = {"elements": meta["elements"], "reference_entries": total, "unreachable": len(meta["unreachable"]),
           "recall_max": round((total - len(meta["unreachable"])) / total, 3), "levels": {}}
    for lvl in (1, 2, 3):
        rate = defaultdict(lambda: [0, 0])
        for p in pop:
            rate[p["sig"][lvl]][0] += 1
            rate[p["sig"][lvl]][1] += p["inref"]
        ins = _frontier([(rate[p["sig"][lvl]][1] / rate[p["sig"][lvl]][0] + 1e-9 * rate[p["sig"][lvl]][1], p["inref"]) for p in pop], total)
        # leave one module out: the rate of the element's signature on the other modules, backing off to a coarser
        # level when the signature never occurs there
        lomo = []
        tot_by = {l2: defaultdict(lambda: [0, 0]) for l2 in (1, 2, 3)}
        mod_by = {l2: defaultdict(lambda: defaultdict(lambda: [0, 0])) for l2 in (1, 2, 3)}
        for p in pop:
            for l2 in (1, 2, 3):
                tot_by[l2][p["sig"][l2]][0] += 1
                tot_by[l2][p["sig"][l2]][1] += p["inref"]
                mod_by[l2][p["module"]][p["sig"][l2]][0] += 1
                mod_by[l2][p["module"]][p["sig"][l2]][1] += p["inref"]
        for p in pop:
            est = 0.0
            for l2 in range(lvl, 0, -1):
                n = tot_by[l2][p["sig"][l2]][0] - mod_by[l2][p["module"]][p["sig"][l2]][0]
                k = tot_by[l2][p["sig"][l2]][1] - mod_by[l2][p["module"]][p["sig"][l2]][1]
                if n > 0:
                    est = k / n
                    break
            lomo.append((est, p["inref"]))
        lo = _frontier(lomo, total)
        out["levels"][lvl] = {
            "signatures": len(rate),
            "in_sample": {f"P@R>={t}": _round(_best_p(ins, t)) for t in targets},
            "leave_one_module_out": {f"P@R>={t}": _round(_best_p(lo, t)) for t in targets},
            "curve_in_sample": [(round(a, 3), round(b, 3), c) for a, b, c in ins],
            "curve_lomo": [(round(a, 3), round(b, 3), c) for a, b, c in lo],
            "rates": sorted(({"signature": describe(s), "elements": v[0], "in_reference": v[1], "rate": round(v[1] / v[0], 3)}
                             for s, v in rate.items()), key=lambda x: (-x["in_reference"], -x["elements"])),
        }
    return out


def d3b_filter(rows: list[dict], total_ref: int, targets=(0.7, 0.85)) -> dict:
    """Can a code filter on the model's own list remove FPs? Each listed row gets the hit rate of its signature among
    the listed rows; in-sample (rates from all rows: optimistic) and leave-one-module-out (rates from the other
    modules' rows, backing off to a coarser level for a signature never listed there). total_ref: reference entries
    summed over the pooled runs."""
    out = {"listed": len(rows), "tp": sum(r["label"] == "TP" for r in rows), "reference_entries": total_ref, "levels": {}}
    tot = {l: defaultdict(lambda: [0, 0]) for l in (1, 2, 3)}
    per = {l: defaultdict(lambda: defaultdict(lambda: [0, 0])) for l in (1, 2, 3)}
    for r in rows:
        for l in (1, 2, 3):
            tot[l][r["sig"][l]][0] += 1
            tot[l][r["sig"][l]][1] += r["label"] == "TP"
            per[l][r["module"]][r["sig"][l]][0] += 1
            per[l][r["module"]][r["sig"][l]][1] += r["label"] == "TP"
    for lvl in (1, 2, 3):
        ins = _frontier([(tot[lvl][r["sig"][lvl]][1] / tot[lvl][r["sig"][lvl]][0], r["label"] == "TP") for r in rows], total_ref)
        lo = []
        for r in rows:
            est = 0.0
            for l in range(lvl, 0, -1):
                n = tot[l][r["sig"][l]][0] - per[l][r["module"]][r["sig"][l]][0]
                k = tot[l][r["sig"][l]][1] - per[l][r["module"]][r["sig"][l]][1]
                if n > 0:
                    est = k / n
                    break
            lo.append((est, r["label"] == "TP"))
        lof = _frontier(lo, total_ref)
        out["levels"][lvl] = {"in_sample": {f"P@R>={x}": _round(_best_p(ins, x)) for x in targets},
                              "leave_one_module_out": {f"P@R>={x}": _round(_best_p(lof, x)) for x in targets},
                              "curve_lomo": [(round(a, 3), round(b, 3), c) for a, b, c in lof]}
    return out


def transfer(train: list[tuple[dict, bool]], test: list[tuple[dict, bool, str]], total_ref: int, targets=(0.7, 0.85),
             train_total: int | None = None) -> dict:
    """Rates learnt on one set of items, applied to another (for example tuning -> held-out). Items: (signatures by
    level, label[, module]). A test signature never seen in training backs off to a coarser level; never seen at L1
    either -> rate 0."""
    out = {}
    tr = {l: defaultdict(lambda: [0, 0]) for l in (1, 2, 3)}
    for sig, lab in train:
        for l in (1, 2, 3):
            tr[l][sig[l]][0] += 1
            tr[l][sig[l]][1] += lab
    for lvl in (1, 2, 3):
        sc = []
        for sig, lab, *_ in test:
            est = 0.0
            for l in range(lvl, 0, -1):
                if tr[l][sig[l]][0] > 0:
                    est = tr[l][sig[l]][1] / tr[l][sig[l]][0]
                    break
            sc.append((est, lab))
        pts = _frontier(sc, total_ref)
        out[lvl] = {f"P@R>={x}": _round(_best_p(pts, x)) for x in targets}
        if train_total:
            # the threshold is chosen on the training items only (max training F1, rates in-sample on training), then
            # applied once: no test label touches the choice
            trs = [(tr[lvl][sig[lvl]][1] / tr[lvl][sig[lvl]][0], lab) for sig, lab in train]
            order = sorted(trs, key=lambda x: -x[0])
            k = n = 0
            bestf, thr = -1.0, 1.0
            for i, (s, lab) in enumerate(order):
                n += 1
                k += lab
                if i + 1 == len(order) or order[i + 1][0] != s:
                    P, R = k / n, k / train_total
                    f1 = 2 * P * R / (P + R) if P + R else 0.0
                    if f1 > bestf:
                        bestf, thr = f1, s
            keep = [lab for (s, lab) in sc if s >= thr]
            k = sum(keep)
            P = k / len(keep) if keep else 0.0
            R = k / total_ref
            out[lvl]["fixed"] = {"threshold": round(thr, 3), "train_F1": round(bestf, 3), "P": round(P, 3), "R": round(R, 3),
                                 "F1": round(2 * P * R / (P + R), 3) if P + R else 0.0, "listed": len(keep)}
    return out


def _fmt_best(x) -> str:
    return "unreachable" if not x else f"{x['P']} (R {x['R']})"


def _round(p):
    return None if p is None else {"P": round(p[0], 3), "R": round(p[1], 3), "listed": p[2]}


def d4_pairs(rows, k: int = 6) -> list[dict]:
    """For the signatures (L3, else L2) holding the most FPs that also hold TPs: one TP and one FP from different
    modules, same role when possible."""
    out = []
    for lvl in (3, 2):
        by = defaultdict(lambda: {"TP": [], "FP": []})
        for r in rows:
            if r["in_map"]:
                by[r["sig"][lvl]][r["label"]].append(r)
        cands = sorted(((s, b) for s, b in by.items() if b["TP"] and b["FP"]), key=lambda x: -len(x[1]["FP"]))
        for s, b in cands:
            if len(out) >= k or any(o["sig"] == s or o["sig"][:len(s)] == s for o in out):
                continue
            best = None
            for fp in sorted(b["FP"], key=lambda r: (r["module"], r["element"])):
                for tp in sorted(b["TP"], key=lambda r: (r["module"], r["element"])):
                    if tp["module"] == fp["module"]:
                        continue
                    score = (tp["role"] == fp["role"], tp["status"] == "verified" and fp["status"] == "verified")
                    if best is None or score > best[0]:
                        best = (score, tp, fp)
            if best:
                out.append({"level": lvl, "sig": s, "signature": describe(s), "FP_count": len(b["FP"]), "TP_count": len(b["TP"]),
                            "TP": _pair_side(best[1]), "FP": _pair_side(best[2])})
        if len(out) >= k:
            break
    return out


def _pair_side(r):
    f = r["features"] or {}
    return {"module": r["module"][8:], "element": r["element"], "role": r["role"], "occurrence": r["occurrence"],
            "line": r["line"], "rtl": r["rtl"], "edge": r["edge"], "status": r["status"], "record types": list(f.get("types", ()))}


def d5_concepts(rows) -> dict:
    by = defaultdict(lambda: {"TP": 0, "FP": 0})
    for r in rows:
        by[(r.get("run"), r["module"], r["concept"])][r["label"]] += 1
    zero = [c for c, b in by.items() if b["TP"] == 0]
    fp = sum(b["FP"] for b in by.values()) or 1
    return {"concepts": len(by), "concepts_without_TP": len(zero), "fp_in_concepts_without_TP": sum(by[c]["FP"] for c in zero),
            "share": round(sum(by[c]["FP"] for c in zero) / fp, 3)}


def d6_edits(run, split: str = "tuning", mods: dict | None = None, roles: str = "all", config_exempt: bool = True) -> dict:
    """Edits A and B of prompt-optimization v1 as shipped (prompt_opt/v1/change.md), applied per concept as code
    filters; an element is removed only if every concept listing it removes it. Counts the FP and TP each would still
    remove.
      A  a stored internal signal (any role; roles="stores" checks only entries labelled "stores", as the loop's first
         measurement did) with no use record: no control record to another element, no data record into an output
         port or output field, no connection of mode in. config_exempt: a setting written from an input that a
         computation here reads (a data record to an internal element) is kept, as the edit allows.
      B  a stored internal signal whose COPIES / DERIVES_FROM records name exactly one element, not itself, and that
         element is listed (internal) in the same concept; kept when that element is combinational and either COPIES
         it or drives nothing but it. Also a combinational signal with a COPIES record naming a listed internal element."""
    d = run_dir(run)
    gt = ea.load_refs()["gt"]
    mods = mods if mods is not None else {}
    have = [m for m in modules_for(split) if _nested(d, m) is not None]
    out = {}
    for name in ("A", "B", "AB"):
        T = F = 0
        base = ea.score(d, gt, strict=True, only=set(have))
        for m in have:
            mod = mods.setdefault(m, load_module(split, m))
            obj = _nested(d, m)
            preds = []
            for c in obj.get("conceptual assets", []) or []:
                if not isinstance(c, dict):
                    continue
                lst = [(s.get("entity", ""), s.get("asset rtl", ""), s.get("realization")) for s in c.get("related structural assets", []) or []
                       if isinstance(s, dict) and s.get("asset rtl")]
                sig = lambda x: (x[0], x[1]) in mod["els"] and mod["els"][(x[0], x[1])]["_cls"] == "SIGNAL"
                keep = list(lst)
                if name in ("A", "AB"):
                    # roles "all": every stored internal signal, whatever its role; roles "stores": entries labelled
                    # "stores", as the loop's first measurement (scratch sim3) did, with no storage check
                    keep = [x for x in keep if not (sig(x) and (x[2] == "stores" if roles == "stores" else
                                                                _stor(mod["els"][(x[0], x[1])]) in ("edge", "mixed"))
                                                     and not _used(mod, x[0], x[1], config_exempt))]
                if name in ("B", "AB"):
                    names = {x[1] for x in keep if sig(x)}
                    k2 = []
                    for x in keep:
                        if sig(x):
                            e = mod["els"][(x[0], x[1])]
                            pt = _recv_partners(e, include_self=True)
                            if _stor(e) in ("edge", "mixed") and len(pt) == 1 and pt <= names - {x[1]}:
                                y = mod["els"].get((x[0], next(iter(pt))))
                                if not (y and _stor(y) == "none" and (x[1] in _copies(y) or _drives_only(y, x[1]))):
                                    continue
                            if _stor(e) == "none" and (_copies(e) & (names - {x[1]})):
                                continue
                        k2.append(x)
                    keep = k2
                preds += [(x[0], x[1]) for x in keep]
            seen, flat = set(), []
            for q in preds:
                if q not in seen:
                    seen.add(q)
                    flat.append((q[0], q[1], ""))
            r = ea.score({m: flat}, {m: gt[m]}, strict=True)
            T += r["tp"]
            F += r["fp"]
        out[name] = {"removes_FP": base["fp"] - F, "removes_TP": base["tp"] - T}
    return out


def _used(mod, ent, name, config_exempt: bool = False) -> bool:
    e = mod["els"][(ent, name)]
    outs = {n for n, md in mod["ports"].get(ent, {}).items() if md == "out"}
    rel = e.get("relationship", []) or []
    if any(t != name for r in rel if r.get("type") in CTL for t in r.get("targets", [])):
        return True
    if {t for r in rel if r.get("type") in DATA for t in r.get("targets", []) if t != name} & outs:
        return True
    if any(c.get("mode") == "in" for c in e.get("connections", []) or []):
        return True
    if config_exempt:
        f = features(e, mod)
        return f["from_input"] and f["data_out_int"]
    return False


def _stor(e) -> str:
    """The storage, a record field taking its record's (load_module)."""
    return e.get("storage_eff", e.get("storage"))


def _recv_partners(e, include_self: bool = False) -> set:
    return {t for r in e.get("relationship", []) or [] if r.get("type") in RECV_DATA for t in r.get("targets", [])
            if include_self or t != e["name"]}


def _drives_only(y, x: str) -> bool:
    """y's driving records target x and nothing else, and y feeds no sub-unit."""
    tg = {t for r in y.get("relationship", []) or [] if r.get("type") in CTL | DATA for t in r.get("targets", [])}
    return tg == {x} and not any(c.get("mode") in IN_MODES for c in y.get("connections", []) or [])


def _copies(e) -> set:
    return {t for r in e.get("relationship", []) or [] if r.get("type") == "COPIES" for t in r.get("targets", [])}


def d7_families(run_sets: dict, split: str = "tuning", mods: dict | None = None) -> dict:
    """{label: [run dirs]} -> per family, mean FP and TP per run of each set."""
    mods = mods if mods is not None else {}
    out = {}
    for label, runs in run_sets.items():
        runs = [r for r in runs if complete(r, split)]
        if not runs:
            continue
        acc = defaultdict(lambda: Counter())
        for r in runs:
            rows, _ = rows_for_run(r, split, mods)
            for x in rows:
                acc[x["family"]][x["label"]] += 1
        out[label] = {"runs": len(runs), "families": {fam: {"FP": round(c["FP"] / len(runs), 1), "TP": round(c["TP"] / len(runs), 1)}
                                                      for fam, c in acc.items()}}
    return out


# ------------------------------------------------------------------------------------------------- report ---
def diagnose(primary: list[str], label: str, split: str = "tuning", run_sets: dict | None = None, log=print,
             train_runs: list[str] | None = None, train_split: str = "tuning") -> dict:
    """All readings for the primary run set (D1, D2, D4, D5, D6 per run, pooled over runs), D3 for the split, and D7
    across run_sets. Writes fp_diagnosis/<label>.md and .json."""
    mods: dict = {}
    skipped = [Path(r).name for r in primary if (run_dir(r) / "_nested").exists() and not complete(r, split)]
    if skipped:
        log(f"   skipped incomplete runs (a module without output): {skipped}")
    primary = [r for r in primary if complete(r, split)]
    assert primary, "no complete run of the primary set exists"
    allrows, per_run = [], []
    for r in primary:
        rows, s = rows_for_run(r, split, mods)
        for x in rows:
            x["run"] = Path(r).name
        allrows += rows
        per_run.append({"run": Path(r).name, "P": round(s["P"], 3), "R": round(s["R"], 3), "TP": s["tp"], "FP": s["fp"], "FN": s["fn"],
                        "edits": d6_edits(r, split, mods)})
    pop, meta = population(split, mods)
    res = {"label": label, "split": split, "runs": per_run, "D1": d1_evidence(allrows),
           "D2": {lvl: d2_shape(allrows, lvl) for lvl in (1, 2, 3)}, "D3": d3_ceiling(pop, meta),
           "D3b": d3b_filter(allrows, sum(r["TP"] + r["FN"] for r in per_run)),
           "D4": d4_pairs(allrows), "D5": d5_concepts(allrows),
           "D7": d7_families(run_sets or {}, split, mods)}
    if train_runs:
        tmods: dict = {}
        trows, ttot = [], 0
        for r in train_runs:
            if complete(r, train_split):
                rr, ss = rows_for_run(r, train_split, tmods)
                trows += rr
                ttot += ss["tp"] + ss["fn"]
        used = [Path(r).name for r in train_runs if complete(r, train_split)]
        if not used:
            log("   D3c skipped: no complete training run")
            train_runs = None
    if train_runs:
        tpop, tmeta = population(train_split, tmods)
        res["D3c"] = {"train": used, "train_split": train_split,
                      "own_list": transfer([(r["sig"], r["label"] == "TP") for r in trows],
                                           [(r["sig"], r["label"] == "TP", r["module"]) for r in allrows],
                                           res["D3b"]["reference_entries"], train_total=ttot),
                      "population": transfer([(x["sig"], x["inref"]) for x in tpop], [(x["sig"], x["inref"], x["module"]) for x in pop],
                                             meta["reference_entries"], train_total=tmeta["reference_entries"])}
    OUT.mkdir(exist_ok=True)
    (OUT / f"{label}.json").write_text(json.dumps(res, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o)),
                                       encoding="utf-8")
    md = report_md(res)
    (OUT / f"{label}.md").write_text(md, encoding="utf-8")
    log(f"report: {OUT / f'{label}.md'}")
    return res


def report_md(res: dict) -> str:
    runs, D1, D2, D3, D5 = res["runs"], res["D1"], res["D2"], res["D3"], res["D5"]
    n = len(runs)
    mp = sum(r["P"] for r in runs) / n
    mr = sum(r["R"] for r in runs) / n
    fp = sum(r["FP"] for r in runs)
    L = [f"# Why precision does not improve: {res['label']} ({res['split']}, {n} run{'s' if n > 1 else ''})", "",
         "Evidence comes from what the model reads and cites: the occurrence IDs and the relationship map of its input. "
         "Every count below is computed from the runs and the maps by `assetgen_meta/fp_diagnosis.py`; nothing is "
         "estimated. Precision (P) = share of listed elements that are in the reference; recall (R) = share of "
         "reference entries that were listed. TP = listed and in the reference; FP = listed and not in it.", "",
         f"Runs: " + "; ".join(f"{r['run']} P {r['P']} R {r['R']} (TP {r['TP']}, FP {r['FP']})" for r in runs)
         + f". Mean P {mp:.3f}, R {mr:.3f}.", "",
         "## Answer", ""]
    lv = D3["levels"]
    best = lambda d, kind, key: max((d["levels"][l][kind][key] for l in (1, 2, 3) if d["levels"][l][kind][key]),
                                    key=lambda x: x["P"], default=None)
    lo85, lo70 = best(D3, "leave_one_module_out", "P@R>=0.85"), best(D3, "leave_one_module_out", "P@R>=0.7")
    in85 = best(D3, "in_sample", "P@R>=0.85")
    f85, f70 = best(res["D3b"], "leave_one_module_out", "P@R>=0.85"), best(res["D3b"], "leave_one_module_out", "P@R>=0.7")
    eA = (sum(r["edits"]["A"]["removes_FP"] for r in runs), sum(r["edits"]["A"]["removes_TP"] for r in runs))
    eB = (sum(r["edits"]["B"]["removes_FP"] for r in runs), sum(r["edits"]["B"]["removes_TP"] for r in runs))
    vfp, vtp = D1["FP"]["verified_share"], D1["TP"]["verified_share"]
    mf1 = 2 * mp * mr / (mp + mr) if mp + mr else 0.0
    c3 = res.get("D3c")
    if c3:   # the level is chosen by its F1 on the training set, never by this set's labels
        lvl_c = max((1, 2, 3), key=lambda l: c3["own_list"][l]["fixed"]["train_F1"])
        fx = c3["own_list"][lvl_c]["fixed"]
    L += [f"- **Citations.** {vfp:.0%} of FP citations are verified (the cited occurrence is the element's own and the cited "
          f"edge exists there and fits the role), against {vtp:.0%} for TPs. Verified is a necessary condition: it shows "
          "the model read the RTL as the map records it, not that the element is an asset.",
          f"- **Shared signatures.** {D2[2]['fp_in_mixed_share']:.0%} of FPs have a behaviour signature (L2) that at least one "
          f"TP in these runs also has; with the exact set of record types (L3), {D2[3]['fp_in_mixed_share']:.0%}. A rule "
          "stated on the signature cannot drop those FPs without dropping the TPs that share it.",
          f"- **Signature-rate selectors over the whole map** (all {D3['elements']:,} elements; list a signature when its "
          f"reference rate on the other modules is high enough; best of L1-L3, threshold read off this set's curve, so "
          f"optimistic): precision {_fmt_best(lo85)} at recall >= 0.85 and {_fmt_best(lo70)} at recall >= 0.70. With the "
          f"rates fitted to this set itself (in-sample): {_fmt_best(in85)} at recall >= 0.85. The runs: P {mp:.3f} at "
          f"R {mr:.3f}. {D3['unreachable']} of {D3['reference_entries']} reference entries have no element of that exact name "
          "in the map.",
          f"- **A filter on the model's own list** (keep an element when its signature's hit rate among the other modules' "
          f"listed elements is high enough; best of L1-L3, threshold read off this set's curve): precision {_fmt_best(f85)} "
          f"at recall >= 0.85 and {_fmt_best(f70)} at recall >= 0.70.",
          *([f"- **Learnt on {c3['train_split']}, applied here once** (level and threshold chosen on {c3['train_split']} "
             f"only, by training F1: L{lvl_c}; in-sample training F1 favours the finest level): P {fx['P']}, R {fx['R']}, "
             f"F1 {fx['F1']}, against the runs' P {mp:.3f}, R {mr:.3f}, F1 {mf1:.3f}. All levels are in D3c."] if c3 else []),
          f"- **Whole concepts.** {D5['fp_in_concepts_without_TP']} FPs ({D5['share']:.0%}) sit in {D5['concepts_without_TP']} "
          f"of {D5['concepts']} concepts (per run) that contain no reference element.",
          f"- **The precision edits** (D6), re-applied as code filters over {n} run(s): edit A would still drop {eA[0]} FPs and "
          f"{eA[1]} TPs, edit B {eB[0]} FPs and {eB[1]} TPs, both (A then B) {sum(r['edits']['AB']['removes_FP'] for r in runs)} FPs "
          f"and {sum(r['edits']['AB']['removes_TP'] for r in runs)} TPs.", ""]
    eAB = (sum(r["edits"]["AB"]["removes_FP"] for r in runs), sum(r["edits"]["AB"]["removes_TP"] for r in runs))
    best_any = max([x["P"] for x in (lo85, f85) if x] + ([fx["P"]] if c3 and fx["R"] >= 0.85 else []) or [0.0])
    gain = max([x["P"] - mp for x in (f85,) if x] + ([fx["P"] - mp] if c3 and fx["R"] >= 0.85 else []) or [0.0])
    read = ["Reading (each line follows from the numbers above):"]
    read.append(f"- Precision 0.85 at recall >= 0.85 is {'not reached' if best_any < 0.85 else 'reached'} by any selector "
                f"or filter of these forms with rates learnt on other modules (best leave-one-module-out {best_any:.3f}; the "
                "in-sample values in D3 and D3b are fitted to the labels they score).")
    if f85 is None and mr < 0.85:
        read.append(f"- Recall 0.85 is out of reach for any filter on this list: the runs' recall is {mr:.3f}.")
    elif gain > 0.03:
        read.append(f"- A filter of these forms raises precision at recall >= 0.85 by up to +{gain:.3f}: part of the FPs "
                    "can be removed by structure, at a recall cost.")
    else:
        read.append("- No filter of these forms raises precision at recall >= 0.85 by more than the 0.03 noise bar.")
    if c3:
        read.append(f"- The filter carried from {c3['train_split']} " + (
            f"raises F1 by {fx['F1'] - mf1:+.3f}: a structural filter learnt elsewhere removes part of the FPs here. This is an "
            "exploratory reading of outputs already used once, not a result; it needs a fresh check before use."
            if fx["F1"] - mf1 > 0.03 else f"changes F1 by {fx['F1'] - mf1:+.3f}, within the 0.03 noise bar."))
    if eAB[0] > 0 and eAB[1] == 0:
        read.append(f"- {eAB[0]} FPs are still removable by the edits' own rules (A then B) without losing a TP: the model did "
                    "not follow the edits fully on those (D6).")
    if best_any < 0.85:
        read.append(f"- Hypothesis, not measured here: the FPs that share a signature with TPs "
                    f"({D2[2]['fp_in_mixed_share']:.0%} at L2) are decided by conventions of the reference that the RTL "
                    "structure does not record. D4 shows pairs; the fault reporter tests this per relationship type.")
    L += read + [""]
    L += ["## D1. Are false positives misreadings? (citation status)", "",
          "| label | listed | verified | statuses |", "|---|---|---|---|"]
    L += [f"| {k} | {v['n']} | {v['verified_share']:.0%} | {v['statuses']} |" for k, v in D1.items()]
    L += ["", "## D2. Do false positives look like hits? (signature shared with a TP)", "",
          "| level | signatures | FP in a signature that also holds a TP | share | FP in signatures with no TP |", "|---|---|---|---|---|"]
    L += [f"| L{l} | {D2[l]['signatures']} | {D2[l]['fp_in_mixed']} of {fp} | {D2[l]['fp_in_mixed_share']:.0%} | {D2[l]['fp_only_shapes']} |" for l in (1, 2, 3)]
    L += ["", "Largest behaviour signatures (L2), pooled over runs:", "", "| signature | FP | TP | TP in modules | FP in modules |", "|---|---|---|---|---|"]
    L += [f"| {t['signature']} | {t['FP']} | {t['TP']} | {', '.join(t['TP_modules'][:6])} | {', '.join(t['FP_modules'][:6])} |" for t in D2[2]["table"][:12]]
    L += ["", "## D3. Signature-rate selectors over the whole map (model-independent)", "",
          f"All {D3['elements']:,} elements of the {res['split']} maps; {D3['reference_entries']} reference entries, "
          f"{D3['unreachable']} with no element of that exact name (recall by exact name can reach at most {D3['recall_max']}; "
          "the scorer also credits a record against one of its fields). A selector lists every element whose signature's "
          "reference rate is above a threshold. In-sample rates are fitted to the reference itself; leave-one-module-out "
          "rates come from the other modules only. In both, the best point at each recall is read off the curve of this "
          "set, so the values are optimistic. These are selectors of one form (signature rates); they do not bound a "
          "method that uses other information.", "",
          "| level | signatures | in-sample P@R>=0.5 | P@R>=0.7 | P@R>=0.85 | leave-one-out P@R>=0.5 | P@R>=0.7 | P@R>=0.85 |",
          "|---|---|---|---|---|---|---|---|"]
    fmt = lambda x: "-" if not x else f"{x['P']} (R {x['R']}, {x['listed']} listed)"
    for l in (1, 2, 3):
        a, b = lv[l]["in_sample"], lv[l]["leave_one_module_out"]
        L.append(f"| L{l} | {lv[l]['signatures']} | {fmt(a['P@R>=0.5'])} | {fmt(a['P@R>=0.7'])} | {fmt(a['P@R>=0.85'])} | "
                 f"{fmt(b['P@R>=0.5'])} | {fmt(b['P@R>=0.7'])} | {fmt(b['P@R>=0.85'])} |")
    L += ["", f"For comparison, the runs above: P {mp:.3f} at R {mr:.3f}.", "",
          "### D3b. A code filter on the model's own list", "",
          "Each listed element gets its signature's hit rate among the listed elements; the filter keeps elements above a "
          "threshold. Leave-one-module-out rates come from the other modules' rows only. Recall counts the reference "
          f"entries of all pooled runs ({res['D3b']['reference_entries']}).", "",
          "| level | in-sample P@R>=0.7 | P@R>=0.85 | leave-one-out P@R>=0.7 | P@R>=0.85 |", "|---|---|---|---|---|"]
    for l in (1, 2, 3):
        a, b = res["D3b"]["levels"][l]["in_sample"], res["D3b"]["levels"][l]["leave_one_module_out"]
        L.append(f"| L{l} | {fmt(a['P@R>=0.7'])} | {fmt(a['P@R>=0.85'])} | {fmt(b['P@R>=0.7'])} | {fmt(b['P@R>=0.85'])} |")
    if res.get("D3c"):
        c = res["D3c"]
        L += ["", f"### D3c. Learnt on {c['train_split']} ({', '.join(c['train'])}), applied here", "",
              "The 'fixed' columns use the threshold that maximizes F1 on the training set, applied once. The other "
              "columns pick the best point on this set's curve, which uses this set's labels for the threshold (optimistic).", "",
              "| level | own list, fixed threshold P / R / F1 (listed) | own list best P@R>=0.7 | own list best P@R>=0.85 | "
              "all map elements, fixed P / R / F1 | all map elements best P@R>=0.85 |",
              "|---|---|---|---|---|---|"]
        for l in (1, 2, 3):
            a, b = c["own_list"][l], c["population"][l]
            fa, fb = a.get("fixed", {}), b.get("fixed", {})
            L.append(f"| L{l} | {fa.get('P')} / {fa.get('R')} / {fa.get('F1')} ({fa.get('listed')}) | {fmt(a['P@R>=0.7'])} | "
                     f"{fmt(a['P@R>=0.85'])} | {fb.get('P')} / {fb.get('R')} / {fb.get('F1')} | {fmt(b['P@R>=0.85'])} |")
    L += ["",
          "Reference listing rate of the largest L2 signatures (all map elements):", "",
          "| signature | elements | in the reference | rate |", "|---|---|---|---|"]
    L += [f"| {x['signature']} | {x['elements']} | {x['in_reference']} | {x['rate']} |" for x in lv[2]["rates"][:14]]
    L += ["", "## D4. Minimal pairs: same map evidence, opposite reference decision", ""]
    for p in res["D4"]:
        L += [f"**{p['signature']}** (L{p['level']}; {p['FP_count']} FP, {p['TP_count']} TP in these runs)", "",
              "| | module | element | role | occurrence -> line | cited edge | RTL line | status |", "|---|---|---|---|---|---|---|---|"]
        for side in ("TP", "FP"):
            s = p[side]
            L.append(f"| {side} | {s['module']} | `{s['element']}` | {s['role']} | {s['occurrence']} -> {s['line']} | {s['edge']} | "
                     f"`{str(s['rtl'])[:90]}` | {s['status']} |")
        L += [f"", f"Record types: TP {', '.join(p['TP']['record types'])}; FP {', '.join(p['FP']['record types'])}.", ""]
    L += ["## D5. Whole concepts the reference does not have", "",
          f"{D5['concepts_without_TP']} of {D5['concepts']} concepts (pooled over runs) contain no TP. They hold "
          f"{D5['fp_in_concepts_without_TP']} FPs, {D5['share']:.0%} of all. The rest are extra elements inside concepts "
          "the reference does have.", "",
          "## D6. Did the model follow the precision edits? (entries each edit would still remove)", "",
          "| run | P | R | edit A removes FP / TP | edit B removes FP / TP |", "|---|---|---|---|---|"]
    L += [f"| {r['run']} | {r['P']} | {r['R']} | {r['edits']['A']['removes_FP']} / {r['edits']['A']['removes_TP']} | "
          f"{r['edits']['B']['removes_FP']} / {r['edits']['B']['removes_TP']} |" for r in runs]
    L += ["", "Edit A: a stored internal signal, whatever role it was given, is listed only when its records show a "
          "use (it controls another element, carries data into an output, or feeds a sub-unit), or it is a setting written "
          "from an input that a computation here reads. Edit B, as shipped: a register whose value-taking records name one "
          "other listed element and nothing else, not even itself, is a one-clock copy, unless that element is "
          "combinational and copies it or drives only it. For a run of a prompt without these edits the numbers show what "
          "they would remove; for a run with them, the FPs are entries the model kept against the edit.", ""]
    if res["D7"]:
        sets = list(res["D7"])
        fams = sorted({f for s in sets for f in res["D7"][s]["families"]},
                      key=lambda f: (-max(res["D7"][s]["families"].get(f, {}).get("FP", 0) for s in sets), f))
        L += ["## D7. Which families moved between versions (mean per run, FP / TP)", "",
              "| family | " + " | ".join(f"{s} ({res['D7'][s]['runs']} runs)" for s in sets) + " |", "|---|" + "---|" * len(sets)]
        for f in fams:
            L.append(f"| {f} | " + " | ".join(f"{res['D7'][s]['families'].get(f, {}).get('FP', 0)} / "
                                               f"{res['D7'][s]['families'].get(f, {}).get('TP', 0)}" for s in sets) + " |")
        L += ["", "Read across a row: a family whose FPs fall while its TPs stay is one an edit moved.", ""]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------------------------------ self-test ---
def selftest(log=print) -> bool:
    """Against hand-read map and RTL lines (assetgen_meta/traced_inputs_v2/tuning, read 2026-10-02) and against
    counts measured earlier in this session with the scratch scripts."""
    ok = True

    def chk(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        log(f"{'ok  ' if cond else 'FAIL'} {msg}")
    wdt, uart = load_module("tuning", "neorv32_wdt"), load_module("tuning", "neorv32_uart")
    # wdt.txt lines 286-296: cnt, storage edge; CONSTRAINS cnt_timeout (144); SOURCES/DERIVES_FROM cnt (134); RESET_BY
    f = features(wdt["els"][("neorv32_wdt", "cnt")], wdt)
    chk(f["storage"] == "stored" and f["self_update"] and f["ctl_out"] and f["reset"] and not f["data_out_port"]
        and not f["from_input"], f"wdt cnt features {dict((k, f[k]) for k in ('storage', 'self_update', 'ctl_out', 'reset', 'data_out_port', 'from_input'))}")
    occ = {o["id"]: o["line"] for o in wdt["els"][("neorv32_wdt", "cnt")]["occurrences"]}
    chk(occ[6] == 144 and "cnt_timeout <= '1' when (cnt_started = '1') and (cnt = ctrl.timeout)" in wdt["lines"][144],
        "wdt cnt occurrence 6 -> line 144, the timeout comparison")
    # uart.txt lines 730-738: tx_engine.bitcnt, edge; GATES tx_engine.done/state (375); SOURCES itself (369)
    f = features(uart["els"][("neorv32_uart", "tx_engine.bitcnt")], uart)
    chk(f["storage"] == "stored" and f["self_update"] and f["ctl_out"] and f["reset"] and f["field"] and not f["data_out_port"],
        "uart tx_engine.bitcnt: stored field, updates itself, controls another element, reset")
    occ = {o["id"]: o["line"] for o in uart["els"][("neorv32_uart", "tx_engine.bitcnt")]["occurrences"]}
    chk(occ[6] == 375 and 'if (tx_engine.bitcnt = "0000") then' in uart["lines"][375], "uart tx_engine.bitcnt occurrence 6 -> line 375")
    chk(signature(features(wdt["els"][("neorv32_wdt", "cnt")], wdt), 2)[2:] ==
        signature(features(uart["els"][("neorv32_uart", "tx_engine.bitcnt")], uart), 2)[2:]
        and describe(signature(features(wdt["els"][("neorv32_wdt", "cnt")], wdt), 1)) == "signal, stored",
        "wdt cnt and uart tx_engine.bitcnt share the L2 behaviour (apart from the field flag)")
    # wdt.txt 226-242: ctrl.enable DERIVES_FROM bus_req_i.data (242), CARRIES bus_rsp_o.data (234) and clkgen_en_o (235)
    f = features(wdt["els"][("neorv32_wdt", "ctrl.enable")], wdt)
    chk(f["from_input"] and f["data_out_port"] and f["ctl_out"] and not f["self_update"], "wdt ctrl.enable: written from an input, into outputs, controls")
    chk(family(f) == "setting written from an input", "wdt ctrl.enable family")
    occ = {o["id"]: o["line"] for o in wdt["els"][("neorv32_wdt", "ctrl.enable")]["occurrences"]}
    chk(occ[3] == 94 and "ctrl.enable  <= bus_req_i.data(ctrl_enable_c);" in wdt["lines"][94], "wdt ctrl.enable occurrence 3 -> line 94")
    # wdt.txt 145-147: rstn_dbg_i GATES reset_cause; uart.txt 399: clk_i connected (mode in) to the FIFO instances
    f = features(wdt["els"][("neorv32_wdt", "rstn_dbg_i")], wdt)
    chk(f["kind"] == "port-in" and f["ctl_out"] and family(f) == "input port", "wdt rstn_dbg_i: input port that controls")
    chk(features(uart["els"][("neorv32_uart", "clk_i")], uart)["sub_in"], "uart clk_i feeds a sub-unit")
    # labels agree with the scorer, and the edit filters reproduce this session's counts (v1 change note, log)
    rows, s = rows_for_run("runs/assets_opt_v1_r0")
    chk(sum(r["label"] == "TP" for r in rows) == 104 and sum(r["label"] == "FP" for r in rows) == 171,
        "v1 r0 row labels: 104 TP, 171 FP (the scorer's totals)")
    # held-out v1 r0 lists names twice; rows_for_run asserts per module that its FP names equal the scorer's
    hrows, hs = rows_for_run("runs/assets_opt_heldout_v1_r0", "heldout")
    consumed, orig = defaultdict(set), ea._hit_idx           # record the indices eval_assets.score itself consumes
    cur = {"m": None}

    def spy(cand, rname, strict=True):
        i = orig(cand, rname, strict)
        if i is not None:
            consumed[cur["m"]].add(i)
        return i
    ea._hit_idx = spy
    try:
        gt = ea.load_refs()["gt"]
        flat = ea.load_run(run_dir("runs/assets_opt_heldout_v1_r0"))
        for m in sorted({r["module"] for r in hrows}):
            cur["m"] = m
            ea.score({m: flat[m]}, {m: gt[m]}, strict=True)
    finally:
        ea._hit_idx = orig
    by_mod = defaultdict(list)
    for r in hrows:
        by_mod[r["module"]].append(r["label"])
    mism = sum(1 for m, labs in by_mod.items() for i, l in enumerate(labs) if (l == "TP") != (i in consumed[m]))
    chk(mism == 0, f"held-out v1 r0 (repeated names): every row's label equals the scorer's by index ({mism} differ)")
    # heldout cpu_control.txt 1894 / 1925, RTL line 275 `ctrl <= ctrl_nxt;`: ctrl.alu_op takes the record's storage
    cc = load_module("heldout", "neorv32_cpu_control")
    chk(features(cc["els"][("neorv32_cpu_control", "ctrl.alu_op")], cc)["storage"] == "stored",
        "cpu_control ctrl.alu_op (not assigned itself) takes the storage of its record ctrl (edge)")
    # bus.txt 2600-2609: a_req GATES itself (line 61) -> updates itself; cache.txt 537-541: cache_i.sta_hit is not
    # assigned here and driven by neorv32_cache_memory_inst.hit_o (mode out) -> a sub-unit interface signal
    bus, cache = load_module("tuning", "neorv32_bus"), load_module("tuning", "neorv32_cache")
    chk(features(bus["els"][("neorv32_bus_switch", "a_req")], bus)["self_update"], "bus a_req updates itself through GATES")
    f = features(cache["els"][("neorv32_cache", "cache_i.sta_hit")], cache)
    chk(f["storage"] == "not assigned here" and f["sub_out"] and family(f) == "sub-unit interface signal",
        "cache cache_i.sta_hit: not assigned here, fed by a sub-unit")
    chk(features(wdt["els"][("neorv32_wdt", "clk_i")], wdt)["local_use"], "wdt clk_i is used here (it clocks other elements)")
    chk(describe(("not in map",)) == "not in map", "describe() handles an element that is not in the map")
    # edits, against the counts in prompt_opt/v1/change.md: A as first measured (role "stores", no exemption) 24 FP;
    # B as shipped 15 FP on v0 r0 and 12 on v0 r1 (17 and 14 were the first draft's)
    a0 = d6_edits("runs/assets_opt_v0_r0", roles="stores", config_exempt=False)["A"]
    chk((a0["removes_FP"], a0["removes_TP"]) == (24, 0), f"edit A (stores only, no exemption) on v0 r0 removes {a0} (want 24 FP, 0 TP)")
    b0, b1 = d6_edits("runs/assets_opt_v0_r0")["B"], d6_edits("runs/assets_opt_v0_r1")["B"]
    chk((b0["removes_FP"], b0["removes_TP"], b1["removes_FP"], b1["removes_TP"]) == (15, 0, 12, 0),
        f"edit B as shipped removes {b0} on v0 r0 and {b1} on v0 r1 (want 15/0 and 12/0)")
    log("self-test " + ("PASS" if ok else "FAIL"))
    return ok


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    import os
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
