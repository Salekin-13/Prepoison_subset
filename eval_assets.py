"""eval_assets.py -- score a generated asset list against a reference.

References are produced by gt_extract.py:
  ground_truth/manual_gt_neorv32.json   manual ground truth (the paper's "True Assets")
  ground_truth/lasset_initial.json      the paper's generation-stage output (our stage)
  ground_truth/lasset_refined.json      the paper's post-refinement output

Metrics follow the paper's own Statistics sheet: TP / FP / FN per module plus
precision, recall, F1. There is deliberately NO true-negative or FPR column -- the
negative class here is "every parsed element that is not an asset", which outnumbers
the positives ~14:1, so a confusion matrix and FPR look excellent while precision is
poor. Objective correctness is reported SEPARATELY from asset-set correctness,
because the two move independently.

Matching (`lenient=True`, the default) treats a record field and its base name as
equal, so `bus_req_i.addr` matches a reference entry of `bus_req_i` and vice versa.
This is needed because the reference sometimes names a whole record and sometimes a
field. Pass lenient=False for exact-name scoring.

Typical notebook use:
    import eval_assets as EV
    gt = EV.load_reference("ground_truth/manual_gt_neorv32.json")
    res = EV.evaluate("assets_tuning18", gt, parsed_dir="parsed_tuning18")
    EV.report(res, "ours vs manual GT")
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

OBJECTIVES = ("Confidentiality", "Integrity", "Availability")
_OBJ_KEYS = (("Confidentiality", "conf"), ("Integrity", "integ"), ("Availability", "avail"))


# ----------------------------------------------------------------- loading ---

def load_reference(path) -> dict:
    """-> {stem: {element: [objectives...]}}"""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for stem, mod in d["modules"].items():
        elems = {}
        for a in mod["assets"]:
            el = a.get("element", "")
            if not el:
                continue
            objs = a.get("objectives") or ([a["objective"]] if a.get("objective") else [])
            elems.setdefault(el, [o for o in objs if o])
        out[stem] = elems
    return out


def load_predictions(assets_dir, modules=None) -> dict:
    """-> {stem: {element: objective}} from a directory of <stem>.json asset files."""
    out = {}
    for f in sorted(Path(assets_dir).glob("*.json")):
        if modules and f.stem not in modules:
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        elems = {}
        for a in data.get("Assets", []):
            el = a.get("Asset RTL", "")
            if el:
                elems.setdefault(el, a.get("Security Objective", ""))
        out[f.stem] = elems
    return out


def closed_set_sizes(parsed_dir) -> dict:
    out = {}
    for f in sorted(Path(parsed_dir).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out[f.stem] = len(d.get("ports", [])) + len(d.get("signals", []))
    return out


# ----------------------------------------------------------------- matching ---

def _base(n: str) -> str:
    return n.split(".")[0]


def match(pred: dict, ref: dict, lenient: bool = True):
    """-> (pairs, fp, fn). pairs = [(pred_name, ref_name)] one-to-one, greedy on exact."""
    pred_names, ref_names = list(pred), list(ref)
    pairs, used_p = [], set()
    for r in ref_names:                       # exact matches first
        if r in pred and r not in used_p:
            pairs.append((r, r))
            used_p.add(r)
    if lenient:
        for r in ref_names:
            if any(rr == r for _, rr in pairs):
                continue
            for p in pred_names:
                if p in used_p:
                    continue
                if _base(p) == r or p == _base(r) or _base(p) == _base(r):
                    pairs.append((p, r))
                    used_p.add(p)
                    break
    matched_ref = {rr for _, rr in pairs}
    return pairs, [p for p in pred_names if p not in used_p], \
        [r for r in ref_names if r not in matched_ref]


def norm_obj(s: str) -> str:
    low = (s or "").lower()
    for name, key in _OBJ_KEYS:
        if key in low:
            return name
    return ""


# --------------------------------------------------------------- evaluation ---

def prf(tp: int, fp: int, fn: int):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def evaluate(predictions, reference: dict, parsed_dir=None, modules=None,
             lenient: bool = True) -> dict:
    """`predictions` is a directory path or an already-loaded {stem: {el: obj}} dict.

    Only modules present in BOTH the predictions and the reference are scored; the
    reference has no entry for modules the paper pruned at its module-listing step
    (neorv32_boot_rom, neorv32_fifo, neorv32_package), so those are reported
    separately as `unscored` rather than counted as all-false-positive.
    """
    pred = (predictions if isinstance(predictions, dict)
            else load_predictions(predictions, modules))
    sizes = closed_set_sizes(parsed_dir) if parsed_dir else {}

    scored = [m for m in pred if m in reference and (not modules or m in modules)]
    unscored = [m for m in pred if m not in reference and (not modules or m in modules)]

    per, conf = {}, Counter()
    tot = dict(tp=0, fp=0, fn=0, emit=0, closed=0, obj_n=0, obj_ok=0)
    for m in sorted(scored):
        pairs, fp, fn = match(pred[m], reference[m], lenient)
        obj_n = obj_ok = 0
        for pn, rn in pairs:
            po, ro = norm_obj(pred[m][pn]), [norm_obj(o) for o in reference[m][rn] if norm_obj(o)]
            if po and ro:
                obj_n += 1
                conf[(po, "".join(o[0] for o in ro))] += 1
                if po in ro:
                    obj_ok += 1
        p, r, f1 = prf(len(pairs), len(fp), len(fn))
        per[m] = dict(gt=len(reference[m]), emit=len(pred[m]), tp=len(pairs),
                      fp=sorted(fp), fn=sorted(fn), precision=p, recall=r, f1=f1,
                      obj_n=obj_n, obj_ok=obj_ok, closed=sizes.get(m, 0))
        tot["tp"] += len(pairs); tot["fp"] += len(fp); tot["fn"] += len(fn)
        tot["emit"] += len(pred[m]); tot["closed"] += sizes.get(m, 0)
        tot["obj_n"] += obj_n; tot["obj_ok"] += obj_ok

    p, r, f1 = prf(tot["tp"], tot["fp"], tot["fn"])
    return dict(per_module=per, micro=dict(**tot, precision=p, recall=r, f1=f1,
                objective_agreement=(tot["obj_ok"] / tot["obj_n"]) if tot["obj_n"] else 0.0,
                emission_rate=(tot["emit"] / tot["closed"]) if tot["closed"] else 0.0,
                gt=sum(len(reference[m]) for m in scored), n_modules=len(scored)),
                objective_confusion=conf, unscored=sorted(unscored), lenient=lenient)


# ------------------------------------------------------------------ reporting ---

def report(res: dict, title: str = "", show_names: bool = False) -> None:
    mi = res["micro"]
    print("=" * 96)
    print(f"{title or 'asset evaluation'}   "
          f"({mi['n_modules']} modules, {mi['gt']} reference elements, "
          f"{'lenient' if res['lenient'] else 'exact'} matching)")
    print("=" * 96)
    print(f"{'module':26s} {'ref':>4s} {'emit':>5s} {'TP':>4s} {'FP':>4s} {'FN':>4s} "
          f"{'P':>6s} {'R':>6s} {'F1':>6s} {'obj':>6s}")
    print("-" * 96)
    for m, d in res["per_module"].items():
        obj = d["obj_ok"] / d["obj_n"] if d["obj_n"] else 0.0
        print(f"{m:26s} {d['gt']:4d} {d['emit']:5d} {d['tp']:4d} {len(d['fp']):4d} "
              f"{len(d['fn']):4d} {d['precision']:6.3f} {d['recall']:6.3f} {d['f1']:6.3f} "
              f"{obj:6.3f}")
    print("-" * 96)
    print(f"{'MICRO TOTAL':26s} {mi['gt']:4d} {mi['emit']:5d} {mi['tp']:4d} {mi['fp']:4d} "
          f"{mi['fn']:4d} {mi['precision']:6.3f} {mi['recall']:6.3f} {mi['f1']:6.3f} "
          f"{mi['objective_agreement']:6.3f}")
    if mi["closed"]:
        print(f"emission rate: {mi['emit']}/{mi['closed']} = {mi['emission_rate']:.1%} "
              f"of the parsed closed set")
    if res["unscored"]:
        print(f"unscored (absent from this reference): {', '.join(res['unscored'])}")
    if show_names:
        print("\nper-module false positives / false negatives:")
        for m, d in res["per_module"].items():
            if d["fp"] or d["fn"]:
                print(f"  {m}")
                if d["fn"]:
                    print(f"     MISSED   : {', '.join(d['fn'])}")
                if d["fp"]:
                    print(f"     EXTRA    : {', '.join(d['fp'])}")


def objective_table(res: dict) -> None:
    """Ours-vs-reference objective confusion (rows = ours, cols = reference)."""
    conf = res["objective_confusion"]
    if not conf:
        print("no matched elements to compare objectives on")
        return
    cols = sorted({c for _, c in conf})
    print(f"{'ours\\ref':>10s} " + " ".join(f"{c:>6s}" for c in cols) + f" {'total':>7s} {'agree':>6s}")
    for o in ("C", "I", "A"):
        full = dict(C="Confidentiality", I="Integrity", A="Availability")[o]
        row = [conf.get((full, c), 0) for c in cols]
        agree = sum(n for c, n in zip(cols, row) if o in c)
        print(f"{full:>10s} " + " ".join(f"{n:>6d}" for n in row)
              + f" {sum(row):>7d} {agree:>6d}")
    tot = sum(conf.values())
    ok = sum(n for (po, rc), n in conf.items() if po[0] in rc)
    print(f"\noverall objective agreement: {ok}/{tot} = {ok/tot if tot else 0:.3f}")


def compare(rows: list) -> None:
    """rows = [(label, result_dict), ...] -- one summary line per configuration."""
    print(f"{'configuration':30s} {'emit':>5s} {'rate':>6s} {'TP':>4s} {'FP':>4s} {'FN':>4s} "
          f"{'P':>6s} {'R':>6s} {'F1':>6s} {'obj':>6s}")
    print("-" * 92)
    for label, res in rows:
        mi = res["micro"]
        rate = f"{mi['emission_rate']:.1%}" if mi["closed"] else "  -  "
        print(f"{label:30s} {mi['emit']:5d} {rate:>6s} {mi['tp']:4d} {mi['fp']:4d} "
              f"{mi['fn']:4d} {mi['precision']:6.3f} {mi['recall']:6.3f} {mi['f1']:6.3f} "
              f"{mi['objective_agreement']:6.3f}")


def to_dataframe(res: dict):
    """Per-module rows as a pandas DataFrame (returns None if pandas is absent)."""
    try:
        import pandas as pd
    except ImportError:
        return None
    return pd.DataFrame([
        dict(module=m, ref=d["gt"], emit=d["emit"], TP=d["tp"], FP=len(d["fp"]),
             FN=len(d["fn"]), precision=round(d["precision"], 3),
             recall=round(d["recall"], 3), f1=round(d["f1"], 3),
             objective=round(d["obj_ok"] / d["obj_n"], 3) if d["obj_n"] else None)
        for m, d in res["per_module"].items()])
