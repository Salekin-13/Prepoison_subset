"""The evidence layer applied to LAsset's OWN published asset lists: does the code-built relationship map carry
information about which of LAsset's items are in the reference, and can a map-based filter learnt on the tuning modules
raise LAsset's precision on unseen modules beyond random removal? No model call.
Pre-registration: assetgen_meta/lasset_layer/PREREG.md (design v2; v1 and its review are recorded there).

Lists (published by the LAsset authors, scored strictly against the manual reference, eval_assets):
  rtl_only    LAsset_initial_results/asset_list_neorv32_initial.json   RTL-only, initial (the primary list)
  spec_rtl    ground_truth/lasset_initial.json                         Spec+RTL, initial
  refined     ground_truth/lasset_refined.json                         Spec+RTL, after LAsset's refinement agents
Maps: assetgen_meta/traced_inputs_v2/<split>/<module>.txt, read with fp_diagnosis.load_module.

Resolution of an item to map elements. Every identifier in the item string is tried (index or slice suffixes removed;
identifiers inside parentheses too); "Entity.port" is read as (Entity, port) when Entity is an entity of the module.
Lookup order: R1 (item entity, name); R2 the name in any entity; R3 a record whose fields are in the map, or the record of
a field. A resolved record is dropped when the item also resolves one of its own fields (prose such as "fifo record
contents" must not pull in every field).
  single-element item   resolves to exactly one element: the population of H1 and the filter (H2)
  compound item         resolves to several elements (the strict scorer counts such an item as one name): reported
                        separately and always kept by the filter
  version-drift item    resolves to nothing: a name absent from this RTL version (e.g. a port renamed since LAsset
                        and the reference were written); reported separately, never dropped by the filter

Evidence per element: the relationship-class profile (fault_reporter.profile, class level), with a whole record taking
the tokens of its fields as well. Trace levels are descriptive only: T1 no record and no connection; T2 records but no
use confirmed; T3 use traced (stored on a clock edge, the element's own or its enclosing record's; computed; set from
an input; or leaving through an output). T3 is close to universal, so it is not used to decide anything.

H1 (audit): a logistic regression on the class tokens, trained on the tuning split's single-element items of the same
list (C=1), scores the held-out single-element items; the area under the ROC curve (AUC, 0.5 = chance) and its module
bootstrap 97.5% interval (Bonferroni over H1 and H2).
H2 (filter): the same model; the threshold is chosen on tuning only, from leave-one-module-out probabilities, as the one
maximizing the tuning list's F1 after dropping single-element items below it. Applied once to held-out: drop
single-element items below the threshold. Precision / recall change with a module bootstrap 97.5% interval, against
random removal of the same number per module from the single-element items (2000 draws, seed 0). If the filter drops
items in fewer than 4 modules the hypothesis is "not testable".
Back-fill (BF, descriptive only): whole, non-clock, non-reset, non-record input ports not named by any item, reaching
within 2 CARRIES / SOURCES steps an (entity, element) of the list whose own map roles include stored or computes.

    python assetgen_meta/lasset_layer.py --selftest
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eval_assets as ea          # noqa: E402
import fp_diagnosis as fd         # noqa: E402
import fault_reporter as fr       # noqa: E402

OUT = HERE / "lasset_layer"
PREREG = OUT / "PREREG.md"
LISTS = {"rtl_only": ROOT / "data/LAsset_initial_results" / "asset_list_neorv32_initial.json",
         "spec_rtl": ROOT / "data/ground_truth" / "lasset_initial.json",
         "refined": ROOT / "data/ground_truth" / "lasset_refined.json"}
PRIMARY_LIST = "rtl_only"
EXPECT = {"tuning": (15, 111), "heldout": (26, 189)}
CLKRST = re.compile(r"(^|_)(clk|rst|rstn|clkgen)(_|$)", re.I)
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
RECV_ROLE = {"DERIVES_FROM", "GATED_BY", "SELECTED_BY", "CONSTRAINED_BY"}
DRIVE = {"CARRIES", "SOURCES", "GATES", "SELECTS", "CONSTRAINS"}
RECEIVE = {"COPIES", "DERIVES_FROM", "GATED_BY", "SELECTED_BY", "CONSTRAINED_BY"}
LEVELS = ("T1", "T2", "T3")
DRAWS, BOOT, SEED = 2000, 10000, 0
ALPHA_Q = (0.0125, 0.9875)          # 97.5% intervals: Bonferroni over the two confirmatory readings
MIN_MODULES = 4


# -------------------------------------------------------------------------------------------------- lists ---
def load_list(which: str) -> dict:
    """{module: [item dicts with 'entity', 'name', 'objective']} in the published order."""
    d = json.loads(LISTS[which].read_text(encoding="utf-8"))
    out = defaultdict(list)
    if isinstance(d, list):
        for ip in d:
            for a in ip.get("Assets", []) or []:
                if a.get("Asset RTL"):
                    out[ip["IP"]].append({"entity": a.get("Entity", "") or "", "name": a["Asset RTL"], "objective": a.get("Security Objective", "")})
    else:
        for m, v in d["modules"].items():
            for a in v.get("assets", []) or []:
                if a.get("element"):
                    out[m].append({"entity": a.get("entity", "") or "", "name": a["element"], "objective": a.get("objective", "")})
    return dict(out)


def as_run(items: dict) -> dict:
    return {m: [(x["entity"], x["name"], x["objective"]) for x in v] for m, v in items.items()}


# ---------------------------------------------------------------------------------------------- resolution ---
def identifiers(s: str) -> list[str]:
    """Every identifier in the item string, index / slice suffixes removed, parenthesised ones included, in order."""
    out = []
    for t in IDENT.findall(s):
        if t not in out:
            out.append(t)
    return out


def _split_entity(t: str, mod: dict):
    ents = {e for (e, _n) in mod["els"]}
    if "." in t:
        head, rest = t.split(".", 1)
        if head in ents:
            return head, rest
    return None, t


def resolve(item: dict, mod: dict) -> tuple[list[dict], Counter]:
    by_name = defaultdict(list)
    for (ent, n), e in mod["els"].items():
        by_name[n].append(e)
    els, rules = [], Counter()
    for t in identifiers(item["name"]):
        ent, n = _split_entity(t, mod)
        e = mod["els"].get((ent or item["entity"], n))
        if e:
            els.append(e); rules["R1"] += 1
            continue
        if by_name.get(n):
            els += by_name[n]; rules["R2"] += 1
            continue
        fields = [e for k, es in by_name.items() if k.startswith(n + ".") for e in es]
        base = by_name.get(n.split(".")[0]) if "." in n else None
        if fields or base:
            els += fields + (base or []); rules["R3"] += 1
    uniq = {(e.get("entity"), e["name"]): e for e in els}
    # a record is dropped when the item also resolves one of its own fields
    keep = {k: e for k, e in uniq.items() if not any(k2[0] == k[0] and k2[1].startswith(k[1] + ".") for k2 in uniq)}
    return list(keep.values()), rules


def _with_fields(e: dict, mod: dict) -> list[dict]:
    return [e] + [x for (ent, n), x in mod["els"].items() if ent == e.get("entity") and n.startswith(e["name"] + ".")]


def _record_clocked(e: dict, mod: dict) -> bool:
    """A field of a record that is stored on a clock edge as a whole (rec <= rec_nxt): the nearest enclosing record."""
    parts = e["name"].split(".")
    for i in range(len(parts) - 1, 0, -1):
        rec = mod["els"].get((e.get("entity"), ".".join(parts[:i])))
        if rec and rec["_cls"] == "SIGNAL":
            types = {r.get("type") for r in rec.get("relationship", []) or []}
            return rec.get("storage") in ("edge", "mixed") and "CLOCKED_BY" in types
    return False


def roles(e: dict, mod: dict) -> set:
    rel = e.get("relationship", []) or []
    types = {r.get("type") for r in rel}
    conns = e.get("connections", []) or []
    mode = (e.get("boundary") or {}).get("mode")
    stor = e.get("storage_eff", e.get("storage"))
    out = set()
    if (stor in ("edge", "mixed") and "CLOCKED_BY" in types) or (e["_cls"] == "SIGNAL" and "." in e["name"] and _record_clocked(e, mod)):
        out.add("stored")
    if mode is None and (types & RECV_ROLE or ("." not in e["name"] and any(c.get("mode") in fd.OUT_MODES for c in conns))):
        out.add("computes")
    if mode in fd.IN_MODES and (types & DRIVE or any(c.get("mode") in fd.IN_MODES for c in conns)):
        out.add("sets")
    if mode in fd.OUT_MODES and (types & RECEIVE or any(c.get("mode") in fd.OUT_MODES for c in conns)):
        out.add("exit")
    return out


def describe_item(item: dict, mod: dict) -> dict:
    els, rules = resolve(item, mod)
    kind = "version-drift" if not els else ("single" if len(els) == 1 else "compound")
    if not els:
        return {"kind": kind, "level": None, "elements": [], "roles": [], "tokens": frozenset(), "rules": dict(rules)}
    allel = [x for e in els for x in _with_fields(e, mod)]
    evid = any((x.get("relationship") or x.get("connections")) for x in allel)
    rs = set().union(*[roles(x, mod) for x in allel])
    toks = frozenset().union(*[fr.profile(x, mod, "class") for x in allel])
    return {"kind": kind, "level": "T3" if rs else ("T2" if evid else "T1"),
            "elements": sorted(f"{e.get('entity')}:{e['name']}" for e in els), "roles": sorted(rs), "tokens": toks, "rules": dict(rules)}


# --------------------------------------------------------------------------------------------- labels, scoring ---
def labels(items: dict, gt: dict, mods) -> dict:
    return {m: fd._labels([x["name"] for x in items.get(m, [])], gt[m]) for m in mods}


def _counts(items: dict, gt: dict, mods) -> dict:
    s = ea.score(as_run({m: items.get(m, []) for m in mods}), gt, strict=True, only=set(mods))
    return {m: (s["per_module"][m]["tp"], len(s["per_module"][m]["fp"]), s["per_module"][m]["ref"]) for m in mods if m in s["per_module"]}


def _pr(pm: dict, mods) -> tuple[float, float]:
    tp = sum(pm[m][0] for m in mods if m in pm); fp = sum(pm[m][1] for m in mods if m in pm); g = sum(pm[m][2] for m in mods if m in pm)
    return tp / max(tp + fp, 1), tp / max(g, 1)


def score(items: dict, gt: dict, mods) -> dict:
    pm = _counts(items, gt, mods)
    P, R = _pr(pm, mods)
    tp = sum(v[0] for v in pm.values()); fp = sum(v[1] for v in pm.values())
    return {"P": P, "R": R, "F1": 2 * P * R / (P + R) if P + R else 0.0, "tp": tp, "fp": fp, "emitted": tp + fp,
            "ref": sum(v[2] for v in pm.values()), "per_module": pm}


def bootstrap(a: dict, b: dict, mods, n=BOOT, seed=SEED, q=ALPHA_Q) -> dict:
    mods = sorted(mods)
    pa, ra = _pr(a, mods); pb, rb = _pr(b, mods)
    rng, dp, dr = random.Random(seed), [], []
    for _ in range(n):
        s = [rng.choice(mods) for _ in mods]
        x, y = _pr(a, s), _pr(b, s)
        dp.append(x[0] - y[0]); dr.append(x[1] - y[1])
    dp.sort(); dr.sort()
    lo, hi = int(q[0] * n), int(q[1] * n)
    return {"dP": pa - pb, "dP_lo": dp[lo], "dP_hi": dp[hi], "dR": ra - rb, "dR_lo": dr[lo], "dR_hi": dr[hi]}


# ------------------------------------------------------------------------------------------- the map model ---
def _vectorize(rows, vocab):
    import numpy as np
    X = np.zeros((len(rows), len(vocab)), dtype=float)
    ix = {t: i for i, t in enumerate(vocab)}
    for i, r in enumerate(rows):
        for t in r["tokens"]:
            if t in ix:
                X[i, ix[t]] = 1.0
    return X


def _rows(items: dict, desc: dict, labs: dict, mods, kind="single") -> list[dict]:
    return [{"module": m, "index": j, "tokens": d["tokens"], "y": labs[m][j] == "TP"}
            for m in mods for j, d in enumerate(desc[m]) if d["kind"] == kind]


def fit(rows: list[dict]):
    from sklearn.linear_model import LogisticRegression
    vocab = sorted({t for r in rows for t in r["tokens"]})
    X, y = _vectorize(rows, vocab), [r["y"] for r in rows]
    return LogisticRegression(max_iter=2000, C=1.0).fit(X, y), vocab


def predict(model, vocab, rows) -> list[float]:
    return list(model.predict_proba(_vectorize(rows, vocab))[:, 1]) if rows else []


def lomo_probs(rows: list[dict]) -> list[float]:
    """Leave-one-module-out probabilities (the model never sees the module it scores)."""
    out = [0.0] * len(rows)
    for m in sorted({r["module"] for r in rows}):
        tr = [r for r in rows if r["module"] != m]
        te = [i for i, r in enumerate(rows) if r["module"] == m]
        if len({r["y"] for r in tr}) < 2:
            p = [sum(r["y"] for r in tr) / max(len(tr), 1)] * len(te)
        else:
            mdl, voc = fit(tr)
            p = predict(mdl, voc, [rows[i] for i in te])
        for i, pi in zip(te, p):
            out[i] = pi
    return out


def auc(y, p) -> float:
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, p)) if len(set(y)) == 2 else float("nan")


def auc_boot(rows, probs, n=BOOT, seed=SEED, q=ALPHA_Q) -> dict:
    mods = sorted({r["module"] for r in rows})
    idx = defaultdict(list)
    for i, r in enumerate(rows):
        idx[r["module"]].append(i)
    rng, vals = random.Random(seed), []
    for _ in range(n):
        ii = [i for m in (rng.choice(mods) for _ in mods) for i in idx[m]]
        y = [rows[i]["y"] for i in ii]
        if len(set(y)) == 2:
            vals.append(auc(y, [probs[i] for i in ii]))
    vals.sort()
    return {"auc": auc([r["y"] for r in rows], probs), "lo": vals[int(q[0] * len(vals))], "hi": vals[int(q[1] * len(vals))], "resamples": len(vals)}


def drop_below(items: dict, desc: dict, probs: dict, thr: float) -> dict:
    """Drop single-element items whose probability is below thr; compound and version-drift items are kept."""
    return {m: [x for j, (x, d) in enumerate(zip(v, desc[m])) if not (d["kind"] == "single" and probs[m][j] < thr)] for m, v in items.items()}


def choose_threshold(items, desc, labs, gt, mods) -> dict:
    """On tuning only: leave-one-module-out probabilities, then the threshold maximizing the list's F1 after dropping."""
    rows = _rows(items, desc, labs, mods)
    lp = lomo_probs(rows)
    probs = {m: [1.0] * len(items[m]) for m in mods}
    for r, p in zip(rows, lp):
        probs[r["module"]][r["index"]] = p
    best = (score(items, gt, mods)["F1"], 0.0)
    for thr in sorted(set(lp)):
        f1 = score(drop_below(items, desc, probs, thr), gt, mods)["F1"]
        if f1 > best[0] + 1e-12:
            best = (f1, thr)
    return {"threshold": best[1], "tuning_F1_lomo": best[0], "tuning_lomo_auc": auc([r["y"] for r in rows], lp)}


def random_drop(items: dict, desc: dict, k: dict, gt, mods, draws=DRAWS, seed=SEED) -> list[float]:
    """Precision after dropping k[m] single-element items per module at random."""
    rng, ps = random.Random(seed), []
    for _ in range(draws):
        out = {}
        for m, v in items.items():
            cand = [j for j, d in enumerate(desc[m]) if d["kind"] == "single"]
            drop = set(rng.sample(cand, min(k.get(m, 0), len(cand))))
            out[m] = [x for j, x in enumerate(v) if j not in drop]
        ps.append(score(out, gt, mods)["P"])
    return ps


# ------------------------------------------------------------------------------------------ back-fill (descr.) ---
def backfill(items: dict, desc: dict, mods: dict, hops: int = 2) -> dict:
    add, pool = {}, {}
    for m, v in items.items():
        mod = mods[m]
        listed = set()
        for x in v:
            for t in identifiers(x["name"]):
                ent, n = _split_entity(t, mod)
                listed.add((ent, n) if ent else (None, n))
        held = set()
        for d in desc[m]:
            for e in d["elements"]:
                ent, n = e.split(":", 1)
                el = mod["els"].get((ent, n))
                if el:
                    for x in _with_fields(el, mod):
                        if roles(x, mod) & {"stored", "computes"}:
                            held.add((x.get("entity"), x["name"]))
        a, p = [], []
        for (ent, name), e in sorted(mod["els"].items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
            if e["_cls"] != "PORT" or "." in name or (e.get("boundary") or {}).get("mode") != "in":
                continue
            if (None, name) in listed or (ent, name) in listed:
                continue
            if any(n.startswith(name + ".") for (en, n) in mod["els"] if en == ent):
                continue
            ts = {r.get("type") for r in e.get("relationship", []) or []}
            if ts & {"SEQUENCES", "RESETS"} or CLKRST.search(name):
                continue
            p.append((ent, name))
            frontier, seen = {name}, set()
            for _ in range(hops):
                nxt = set()
                for n in frontier:
                    for r in (mod["els"].get((ent, n)) or {}).get("relationship", []) or []:
                        if r.get("type") in ("CARRIES", "SOURCES"):
                            nxt |= set(r.get("targets", []))
                seen |= nxt
                frontier = nxt
            if {(ent, n) for n in seen} & held:
                a.append((ent, name))
        add[m], pool[m] = a, p
    return {"add": add, "pool": pool}


def with_additions(items: dict, add: dict) -> dict:
    return {m: v + [{"entity": e, "name": n, "objective": "Integrity"} for e, n in add.get(m, [])] for m, v in items.items()}


# ------------------------------------------------------------------------------------------------- readings ---
def _setup(which: str, split: str):
    os.chdir(ROOT)
    gt = ea.load_refs()["gt"]
    mods = fd.modules_for(split)
    n_ref = sum(len(gt[m]) for m in mods)
    assert (len(mods), n_ref) == EXPECT[split], f"{split}: {len(mods)} modules, {n_ref} entries; expected {EXPECT[split]}"
    items_all = load_list(which)
    items = {m: items_all.get(m, []) for m in mods}
    maps = {m: fd.load_module(split, m) for m in mods}
    desc = {m: [describe_item(x, maps[m]) for x in items[m]] for m in mods}
    return gt, mods, items, maps, desc, labels(items, gt, mods)


def _composition(items, desc, labs, mods) -> dict:
    out = {}
    for kind in ("single", "compound", "version-drift"):
        c = Counter(labs[m][j] for m in mods for j, d in enumerate(desc[m]) if d["kind"] == kind)
        out[kind] = {"hits": c["TP"], "fps": c["FP"]}
    lev = {}
    for lab in ("TP", "FP"):
        c = Counter(d["level"] for m in mods for j, d in enumerate(desc[m]) if d["kind"] != "version-drift" and labs[m][j] == lab)
        n = sum(c.values())
        lev[lab] = {"n": n, **{L: (c[L] / n if n else None) for L in LEVELS}}
    out["trace_levels"] = lev
    return out


def read_tuning(which: str, log=print) -> dict:
    """Development reading: everything the held-out reading will use is fixed here (model, threshold)."""
    gt, mods, items, maps, desc, labs = _setup(which, "tuning")
    rows = _rows(items, desc, labs, mods)
    th = choose_threshold(items, desc, labs, gt, mods)
    base = score(items, gt, mods)
    res = {"list": which, "split": "tuning", "base": _strip(base), "composition": _composition(items, desc, labs, mods),
           "single_items": len(rows), "lomo_auc": th["tuning_lomo_auc"], "threshold": th["threshold"],
           "tuning_F1_after_lomo_filter": th["tuning_F1_lomo"],
           "resolution_rules": dict(sum((Counter(d["rules"]) for m in mods for d in desc[m]), Counter()))}
    _write(res, items, desc, labs, mods, "tuning", which, log)
    return res


def read_heldout(which: str, log=print) -> dict:
    """Confirmatory reading (primary list): model trained on the tuning single-element items, threshold from tuning."""
    if which == PRIMARY_LIST:
        bad = verify_pins()
        assert not bad, f"pinned files changed since the pre-registration: {bad}"
    tg, tm, ti, _tmaps, tdesc, tlabs = _setup(which, "tuning")
    trows = _rows(ti, tdesc, tlabs, tm)
    model, vocab = fit(trows)
    thr = choose_threshold(ti, tdesc, tlabs, tg, tm)["threshold"]
    gt, mods, items, maps, desc, labs = _setup(which, "heldout")
    rows = _rows(items, desc, labs, mods)
    p = predict(model, vocab, rows)
    probs = {m: [1.0] * len(items[m]) for m in mods}
    for r, pi in zip(rows, p):
        probs[r["module"]][r["index"]] = pi
    base = score(items, gt, mods)
    filt = drop_below(items, desc, probs, thr)
    s = score(filt, gt, mods)
    k = {m: len(items[m]) - len(filt[m]) for m in mods}
    touched = sum(1 for v in k.values() if v)
    ps = random_drop(items, desc, k, gt, mods)
    dropped = [(m, labs[m][j]) for m in mods for j, d in enumerate(desc[m]) if d["kind"] == "single" and probs[m][j] < thr]
    h1 = auc_boot(rows, p)
    lomo_h = lomo_probs(rows)
    bf = backfill(items, desc, maps)
    sb = score(with_additions(items, bf["add"]), gt, mods)
    res = {"list": which, "split": "heldout", "base": _strip(base), "composition": _composition(items, desc, labs, mods),
           "single_items": len(rows), "threshold_from_tuning": thr,
           "H1": {**h1, "within_heldout_lomo_auc": auc([r["y"] for r in rows], lomo_h)},
           "H2": {**_strip(s), "dropped": len(dropped), "dropped_hits": sum(x[1] == "TP" for x in dropped),
                  "dropped_fps": sum(x[1] == "FP" for x in dropped), "modules_touched": touched,
                  "vs_base": bootstrap(s["per_module"], base["per_module"], mods),
                  "random": {"P_mean": sum(ps) / len(ps), "P_lo": sorted(ps)[int(0.0125 * len(ps))], "P_hi": sorted(ps)[int(0.9875 * len(ps))],
                             "share_ge": sum(x >= s["P"] - 1e-9 for x in ps) / len(ps)}},
           "BF": {**_strip(sb), "added": sum(len(v) for v in bf["add"].values()), "added_hits": sb["tp"] - base["tp"],
                  "pool": sum(len(v) for v in bf["pool"].values()), "modules": sum(1 for v in bf["add"].values() if v)},
           "resolution_rules": dict(sum((Counter(d["rules"]) for m in mods for d in desc[m]), Counter()))}
    res["verdicts"] = verdicts(res) if which == PRIMARY_LIST else {"note": "secondary list: no decision rule"}
    _write(res, items, desc, labs, mods, "heldout", which, log, probs)
    return res


def _strip(s: dict) -> dict:
    return {k: v for k, v in s.items() if k != "per_module"}


def verdicts(r: dict) -> dict:
    """PREREG.md section 3 (design v2), on unrounded values."""
    h1 = r["H1"]["lo"] > 0.5
    h = r["H2"]
    if h["modules_touched"] < MIN_MODULES:
        h2 = "not testable"
    else:
        h2 = "holds" if (h["vs_base"]["dP_lo"] > 0 and h["random"]["share_ge"] < 0.025) else "does not hold"
    claims = []
    if h1:
        claims.append("map evidence carries information about which LAsset items are in the reference")
    if h2 == "holds":
        claims.append("a map-based filter learnt on tuning raises LAsset's held-out precision beyond random removal")
    return {"H1_audit": "holds" if h1 else "does not hold", "H2_filter": h2,
            "claim": "; ".join(claims) if claims else "audit trail only: the map traces LAsset's items but does not tell its hits from its false positives"}


def _write(res, items, desc, labs, mods, split, which, log, probs=None):
    import csv
    OUT.mkdir(exist_ok=True)
    (OUT / f"{split}_{which}.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    with (OUT / f"{split}_{which}_items.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["module", "entity", "item", "label", "kind", "trace_level", "map_elements", "roles", "tokens", "resolution"]
                   + (["model_probability"] if probs else []))
        for m in mods:
            for j, (x, d, lab) in enumerate(zip(items[m], desc[m], labs[m])):
                w.writerow([m, x["entity"], x["name"], lab, d["kind"], d["level"] or "", " ".join(d["elements"]), " ".join(d["roles"]),
                            " | ".join(sorted(d["tokens"])), " ".join(f"{k}:{v}" for k, v in d["rules"].items())]
                           + ([f"{probs[m][j]:.3f}"] if probs else []))
    (OUT / f"{split}_{which}.md").write_text(report_md(res), encoding="utf-8")
    log(f"{split} {which}: written {OUT / f'{split}_{which}.md'}")


def report_md(r: dict) -> str:
    b, c = r["base"], r["composition"]
    f = lambda x: f"{x:.3f}"
    L = [f"# Evidence layer on LAsset's list `{r['list']}` ({r['split']})", "",
         f"As published: P {f(b['P'])}, R {f(b['R'])}, F1 {f(b['F1'])} ({b['emitted']} items, {b['ref']} reference entries). P = "
         "precision (share of listed items in the reference); R = recall (share of reference entries listed). Labels by the "
         "scorer's own matching.", "",
         "| items | hits | false positives |", "|---|---|---|"]
    for k, name in (("single", "single-element (the tested population)"), ("compound", "compound (always kept)"),
                    ("version-drift", "name not in this RTL version (never dropped)")):
        L.append(f"| {name} | {c[k]['hits']} | {c[k]['fps']} |")
    tl = c["trace_levels"]
    L += ["", "Trace levels of resolved items (descriptive; T3 = use traced, close to universal):", "",
          "| | items | T1 no record | T2 records, no use | T3 use traced |", "|---|---|---|---|---|"]
    for lab, name in (("TP", "hits"), ("FP", "false positives")):
        x = tl[lab]
        L.append(f"| {name} | {x['n']} | " + " | ".join(f"{x[l]:.0%}" if x[l] is not None else "-" for l in LEVELS) + " |")
    L += ["", f"Resolution rules used: {r['resolution_rules']}.", ""]
    if r["split"] == "tuning":
        L += ["## Development reading (fixes what held-out will use)", "",
              f"- Single-element items: {r['single_items']}. Leave-one-module-out AUC of the map model (hits vs false positives, "
              f"0.5 = chance): {f(r['lomo_auc'])}.",
              f"- Threshold chosen on tuning (leave-one-module-out probabilities, maximizing F1): {f(r['threshold'])}; tuning F1 "
              f"after that filter {f(r['tuning_F1_after_lomo_filter'])} against {f(b['F1'])} as published.", ""]
        return "\n".join(L) + "\n"
    h1, h2, bf = r["H1"], r["H2"], r["BF"]
    q = h2["vs_base"]
    L += ["## H1, audit: does map evidence rank LAsset's held-out hits above its false positives?", "",
          f"Model trained on the tuning single-element items of this list, applied to the {r['single_items']} held-out single-element "
          f"items: AUC {f(h1['auc'])} (97.5% module-bootstrap interval {f(h1['lo'])} to {f(h1['hi'])}). Within held-out, leave one module "
          f"out: {f(h1['within_heldout_lomo_auc'])} (descriptive).", "",
          "## H2, filter: does the map-based filter raise LAsset's held-out precision beyond random removal?", "",
          f"Threshold fixed on tuning: {f(r['threshold_from_tuning'])}. Dropped {h2['dropped']} single-element items "
          f"({h2['dropped_hits']} hits, {h2['dropped_fps']} false positives) in {h2['modules_touched']} modules.", "",
          "| | P | R | F1 |", "|---|---|---|---|",
          f"| as published | {f(b['P'])} | {f(b['R'])} | {f(b['F1'])} |",
          f"| after the filter | {f(h2['P'])} | {f(h2['R'])} | {f(h2['F1'])} |", "",
          f"Change in P {q['dP']:+.3f} (97.5% interval {q['dP_lo']:+.3f} to {q['dP_hi']:+.3f}); change in R {q['dR']:+.3f} "
          f"({q['dR_lo']:+.3f} to {q['dR_hi']:+.3f}). Random removal of the same number per module: mean P {f(h2['random']['P_mean'])} "
          f"(97.5% range {f(h2['random']['P_lo'])} to {f(h2['random']['P_hi'])}); share of random draws reaching the filter's P: "
          f"{h2['random']['share_ge']:.1%}.", "",
          "## Back-fill (descriptive only)", "",
          f"Added {bf['added']} input ports in {bf['modules']} modules (pool {bf['pool']}), {bf['added_hits']} of them hits; list after: "
          f"P {f(bf['P'])}, R {f(bf['R'])}.", ""]
    v = r["verdicts"]
    if "H1_audit" in v:
        L += ["## Pre-registered verdicts (PREREG.md section 3)", "",
              f"- H1, audit (interval lower bound above 0.5): **{v['H1_audit']}**.",
              f"- H2, filter (precision interval above 0 and under 2.5% of random removals reaching it; not testable if fewer "
              f"than {MIN_MODULES} modules touched): **{v['H2_filter']}**.",
              f"- What the data supports: **{v['claim']}**.", ""]
    else:
        L += [f"Secondary list: {v['note']}.", ""]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------------------------------ pins, test ---
def sha12(p: Path) -> str:
    if p.is_dir():
        h = hashlib.sha256()
        for f in sorted((x for x in p.rglob("*") if x.is_file() and "__pycache__" not in x.parts), key=lambda x: x.relative_to(p).as_posix()):
            h.update(f.relative_to(p).as_posix().encode() + b"\0" + f.read_bytes() + b"\0")
        return h.hexdigest()[:12]
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


PINNED = ["assetgen_meta/lasset_layer.py", "assetgen_meta/fp_diagnosis.py", "assetgen_meta/fault_reporter.py",
          "assetgen_meta/trace_check.py", "src/eval_assets.py", "data/ground_truth/manual_gt_neorv32.json",
          "data/LAsset_initial_results/asset_list_neorv32_initial.json", "data/ground_truth/lasset_initial.json", "data/ground_truth/lasset_refined.json",
          "data/parsed_tuning18", "assetgen_meta/traced_inputs_v2/tuning", "assetgen_meta/traced_inputs_v2/heldout"]


def pins_now() -> list[tuple[str, str]]:
    return [(p, sha12(ROOT / p)) for p in PINNED]


def verify_pins() -> list[str]:
    table = dict(re.findall(r"^\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{12})`\s*\|", PREREG.read_text(encoding="utf-8"), re.M))
    return sorted({p for p, s in pins_now() if table.get(p) != s})


def selftest(log=print) -> bool:
    """Hand-read map lines (traced_inputs_v2/tuning, read 2026-10-02), the scorer reproduction of LAsset's lists, and
    planted cases. Tuning only. No API call."""
    ok = True

    def chk(c, msg):
        nonlocal ok
        ok &= bool(c)
        log(f"{'ok  ' if c else 'FAIL'} {msg}")
    os.chdir(ROOT)
    cpu, wdt = fd.load_module("tuning", "neorv32_cpu"), fd.load_module("tuning", "neorv32_wdt")
    cache, trng = fd.load_module("tuning", "neorv32_cache"), fd.load_module("tuning", "neorv32_trng")
    # cpu.txt 348-350: msi_i, input port, SOURCES irq_machine -> single, T3, sets
    d = describe_item({"entity": "neorv32_cpu", "name": "msi_i"}, cpu)
    chk(d["kind"] == "single" and d["level"] == "T3" and d["roles"] == ["sets"], f"cpu msi_i -> single, T3, sets ({d['kind']}, {d['level']}, {d['roles']})")
    # wdt.txt 168-169: bus_req_i.ben has no record and no connection -> T1
    chk(describe_item({"entity": "neorv32_wdt", "name": "bus_req_i.ben"}, wdt)["level"] == "T1", "wdt bus_req_i.ben -> T1")
    # cache map: ctrl <= ctrl_nxt (whole record clocked); ctrl.buf_req has storage none and no CLOCKED_BY of its own
    d = describe_item({"entity": "neorv32_cache", "name": "ctrl.buf_req"}, cache)
    chk("stored" in d["roles"], f"cache ctrl.buf_req is stored through its clocked record ({d['roles']})")
    # trng: 'fifo.wdata / fifo.rdata (fifo record contents)': the prose word 'fifo' must not pull in every field
    d = describe_item({"entity": "neorv32_trng", "name": "fifo.wdata / fifo.rdata (fifo record contents)"}, trng)
    chk(all(e.split(":", 1)[1] in ("fifo.wdata", "fifo.rdata") for e in d["elements"]) and d["kind"] == "compound",
        f"trng fifo item resolves to its two named fields only ({d['elements']})")
    # trng: 'enable (... neoTRNG.enable_i ...)' names neoTRNG:enable_i, which back-fill must not add again
    it = {"neorv32_trng": [{"entity": "neorv32_trng", "name": "enable (ctrl_en_c / neoTRNG.enable_i / sample_en)", "objective": ""}]}
    ds = {"neorv32_trng": [describe_item(it["neorv32_trng"][0], trng)]}
    chk(("neoTRNG", "enable_i") not in backfill(it, ds, {"neorv32_trng": trng})["add"]["neorv32_trng"],
        "back-fill does not re-add a port the item names as Entity.port")
    chk(describe_item({"entity": "neorv32_wdt", "name": "no_such_element_xyz"}, wdt)["kind"] == "version-drift", "an invented name -> version-drift")
    # wdt.txt 145-147: rstn_dbg_i is a reset name: never a back-fill addition
    it = {"neorv32_wdt": [{"entity": "neorv32_wdt", "name": "reset_cause", "objective": ""}]}
    ds = {"neorv32_wdt": [describe_item(it["neorv32_wdt"][0], wdt)]}
    chk(("neorv32_wdt", "rstn_dbg_i") not in backfill(it, ds, {"neorv32_wdt": wdt})["add"]["neorv32_wdt"], "back-fill never adds a reset input")
    gt = ea.load_refs()["gt"]
    tun = fd.modules_for("tuning")
    for which, want in (("rtl_only", (0.680, 0.748, 122)), ("spec_rtl", (0.737, 0.910, 137)), ("refined", (0.800, 0.901, 125))):
        s = score({m: load_list(which).get(m, []) for m in tun}, gt, tun)
        chk((round(s["P"], 3), round(s["R"], 3), s["emitted"]) == want, f"{which} on tuning scores {s['P']:.3f} / {s['R']:.3f} ({s['emitted']}) (want {want})")
    # labels equal the scorer's per-module FP names
    it = {m: load_list("rtl_only").get(m, []) for m in tun}
    labs = labels(it, gt, tun)
    sc = ea.score(as_run(it), gt, strict=True, only=set(tun))
    chk(all(sorted(x["name"] for x, l in zip(it[m], labs[m]) if l == "FP") == sorted(sc["per_module"][m]["fp"]) for m in tun),
        "item labels equal the scorer's FP names in every module")
    # random removal of 0 items leaves P unchanged; bootstrap of a list against itself is 0
    s0 = score(it, gt, tun)
    desc = {m: [describe_item(x, fd.load_module("tuning", m)) for x in it[m]] for m in tun}
    chk(all(abs(p - s0["P"]) < 1e-12 for p in random_drop(it, desc, {m: 0 for m in tun}, gt, tun, draws=5)), "random removal of 0 items leaves P unchanged")
    bz = bootstrap(s0["per_module"], s0["per_module"], tun, n=200)
    chk(bz["dP"] == 0 and bz["dP_lo"] == 0 and bz["dP_hi"] == 0, "bootstrap of a list against itself is exactly 0")
    # the "not testable" rule
    fake = {"H1": {"lo": 0.6}, "H2": {"modules_touched": 3, "vs_base": {"dP_lo": 0.1}, "random": {"share_ge": 0.0}}}
    chk(verdicts(fake)["H2_filter"] == "not testable" and verdicts(fake)["H1_audit"] == "holds", "fewer than 4 modules touched -> not testable")
    log("self-test " + ("PASS" if ok else "FAIL"))
    return ok


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    if "--pins" in sys.argv:
        for p, s in pins_now():
            print(f"| `{p}` | `{s}` |")
