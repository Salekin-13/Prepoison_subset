"""eval_assets.py -- score generated asset lists. Built for version ablations.

Three functions is the whole API:

    refs   = load_refs()                      # both reference sets
    r      = score(assets_dir, refs["gt"])    # one run vs one reference
    table(r)                                  # per-module breakdown
    compare({"v0": r0, "v1": r1})             # one line per version

Metrics are TP / FP / FN + precision / recall / F1, the same columns the LAsset
paper's own statistics sheet uses. No TN and no FPR: the negative class ("every
parsed element that is not an asset") outnumbers the positives ~14:1, so FPR
reads ~0.1 while precision is ~0.3. Objective accuracy is one separate number.

Matching is by element name; a record field matches its base name in either
direction (bus_req_i.addr <-> bus_req_i), because the references name a whole
record in some places and a single field in others.
"""
from __future__ import annotations

import json
from pathlib import Path

GT_DIR = Path("ground_truth")


# --------------------------------------------------------------------- load ---

def load_refs(gt_dir=GT_DIR) -> dict:
    """-> {"gt": ..., "paper": ..., "paper_refined": ...}; each {module: {element: objective}}"""
    def read(name):
        p = Path(gt_dir) / name
        if not p.exists():
            return {}
        d = json.loads(p.read_text(encoding="utf-8"))
        return {m: {a["element"]: a.get("objective", "")
                    for a in v["assets"] if a.get("element")}
                for m, v in d["modules"].items()}

    return {"gt": read("manual_gt_neorv32.json"),
            "paper": read("lasset_initial.json"),
            "paper_refined": read("lasset_refined.json")}


def load_run(assets_dir) -> dict:
    """-> {module: {element: objective}} from a directory of <module>.json files.

    Files whose name starts with '_' are bookkeeping (e.g. _run_meta.json) and are
    skipped, so they cannot be picked up as a module with zero assets.
    """
    out = {}
    for f in sorted(Path(assets_dir).glob("*.json")):
        if f.name.startswith("_"):
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        out[f.stem] = {a["Asset RTL"]: a.get("Security Objective", "")
                       for a in data.get("Assets", []) if a.get("Asset RTL")}
    return out


# -------------------------------------------------------------------- score ---

def _hit(pred_names, ref_name, strict=True):
    """The predicted name matching ref_name, or None.

    Exact match first. Then the ONE legitimate near-match: the references name a whole
    record in some places and a single field in others, so `ctrl` <-> `ctrl.enable` must
    match in either direction.

    What strict mode refuses is FIELD-TO-FIELD matching. The old rule also accepted any
    two dotted names sharing a base, so a prediction of `fifo.avail` was credited against
    a ground-truth `fifo.re` -- two different fields, both separately in the reference.
    That silently rewards spraying record fields, and it inflated recall unevenly across
    prompt versions (v0 by 4 TP, v1 by 2), which biases exactly the comparison an ablation
    is trying to make. strict=False restores the old behaviour for back-comparison only.

    Candidates are sorted before scanning: iterating a set would make the choice depend on
    hash order, and two runs of the same data could then report different scores.
    """
    if ref_name in pred_names:
        return ref_name
    rb = ref_name.split(".")[0]
    dotted = "." in ref_name
    for p in sorted(pred_names):
        if (not dotted and p.split(".")[0] == ref_name) or (dotted and p == rb):
            return p
    if not strict:
        for p in sorted(pred_names):
            if p.split(".")[0] == rb:
                return p
    return None


def _obj(s):
    s = (s or "").lower()
    return ("Confidentiality" if "conf" in s else
            "Integrity" if "integ" in s else
            "Availability" if "avail" in s else "")


def score(run, reference: dict, strict: bool = True, only=None) -> dict:
    """`run` is a directory path or a {module: {element: objective}} dict.

    Modules absent from the reference are skipped, not counted as false positives:
    the paper pruned boot_rom / fifo / package before generating any assets.

    `only` restricts scoring to a set of module names. Pass it whenever comparing runs:
    if one version failed a module its totals cover a different denominator and the
    versions are not comparable. ablate() computes the intersection and passes it here.
    """
    pred = run if isinstance(run, dict) else load_run(run)
    per, skipped = {}, []
    for mod, elems in sorted(pred.items()):
        if mod not in reference or (only is not None and mod not in only):
            skipped.append(mod)
            continue
        ref = reference[mod]
        matched, obj_ok, obj_n = {}, 0, 0
        for r in ref:
            h = _hit(set(elems) - set(matched.values()), r, strict)
            if h:
                matched[r] = h
                po, ro = _obj(elems[h]), _obj(ref[r])
                if po and ro:
                    obj_n += 1
                    obj_ok += (po == ro)
        tp = len(matched)
        per[mod] = {
            "ref": len(ref), "emit": len(elems), "tp": tp,
            "fp": sorted(set(elems) - set(matched.values())),
            "fn": sorted(set(ref) - set(matched)),
            "obj_ok": obj_ok, "obj_n": obj_n,
        }

    tp = sum(m["tp"] for m in per.values())
    fp = sum(len(m["fp"]) for m in per.values())
    fn = sum(len(m["fn"]) for m in per.values())
    obj_ok = sum(m["obj_ok"] for m in per.values())
    obj_n = sum(m["obj_n"] for m in per.values())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {
        "per_module": per, "skipped": skipped,
        "tp": tp, "fp": fp, "fn": fn,
        "precision": p, "recall": r,
        "f1": 2 * p * r / (p + r) if p + r else 0.0,
        "objective": obj_ok / obj_n if obj_n else 0.0,
        "emit": sum(m["emit"] for m in per.values()),
        "ref": sum(m["ref"] for m in per.values()),
    }


# ------------------------------------------------------------------- report ---

_HDR = f"{'':22s} {'ref':>4s} {'emit':>5s} {'TP':>4s} {'FP':>4s} {'FN':>4s} {'P':>6s} {'R':>6s} {'F1':>6s} {'obj':>6s}"


def _row(label, ref, emit, tp, fp, fn, p, r, f1, obj):
    return (f"{label:22s} {ref:4d} {emit:5d} {tp:4d} {fp:4d} {fn:4d} "
            f"{p:6.3f} {r:6.3f} {f1:6.3f} {obj:6.3f}")


def table(res: dict, title: str = "", show_names: bool = False) -> None:
    """Per-module breakdown for one run."""
    print(title or "asset evaluation")
    print(_HDR)
    print("-" * 76)
    for mod, m in res["per_module"].items():
        tp, fp, fn = m["tp"], len(m["fp"]), len(m["fn"])
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        obj = m["obj_ok"] / m["obj_n"] if m["obj_n"] else 0.0
        print(_row(mod.replace("neorv32_", ""), m["ref"], m["emit"], tp, fp, fn, p, r, f1, obj))
    print("-" * 76)
    print(_row("TOTAL", res["ref"], res["emit"], res["tp"], res["fp"], res["fn"],
               res["precision"], res["recall"], res["f1"], res["objective"]))
    if res["skipped"]:
        print(f"skipped (no reference): {', '.join(res['skipped'])}")
    if show_names:
        for mod, m in res["per_module"].items():
            if m["fn"] or m["fp"]:
                print(f"\n{mod}")
                if m["fn"]:
                    print(f"   MISSED: {', '.join(m['fn'])}")
                if m["fp"]:
                    print(f"   EXTRA : {', '.join(m['fp'])}")


def compare(results: dict, title: str = "") -> None:
    """One line per version. `results` = {label: score(...)}"""
    print(title or "version comparison")
    print(_HDR)
    print("-" * 76)
    for label, res in results.items():
        print(_row(label, res["ref"], res["emit"], res["tp"], res["fp"], res["fn"],
                   res["precision"], res["recall"], res["f1"], res["objective"]))


# ----------------------------------------------------------------- ablation ---
# Three calls are the whole ablation API:
#
#     RUNS = collect(["v0", "v01", "v02"])   # {version: [run per repeat]}
#     ablate(RUNS, refs["gt"])               # one row per version, mean +/- sd
#     paired(RUNS, "v0", "v02", refs["gt"])  # delta + 95% CI, modules as the pairing unit
#
# Why paired: every version runs the SAME modules, so each module is its own control.
# Between-module variance here is enormous (cpu ground-truth density ~38%, peripherals
# ~7%), and an unpaired comparison of aggregate F1 drowns a real effect in it.

def collect(versions, root=".", stem="assets_tuning18") -> dict:
    """{version: [run, ...]} -- one run dict per repeat directory.

    Explicit repeats `<stem>_<v>_r<i>` win. The legacy bare directory `<stem>_<v>` is
    used only when no repeat directories exist -- mixing the two would fold a run made
    under an older prompt state in as though it were another repeat of the current one.
    """
    out = {}
    for v in versions:
        runs = [r for d in sorted(Path(root).glob(f"{stem}_{v}_r*"))
                for r in [load_run(d)] if r]
        if not runs:                      # empty repeat dirs must not shadow a real run
            runs = [r for d in Path(root).glob(f"{stem}_{v}") for r in [load_run(d)] if r]
        if runs:
            out[v] = runs
        else:
            print(f"  [warn] no run directory for version {v!r}")
    return out


def common_modules(runs_by_version: dict, reference: dict) -> set:
    """Modules present in EVERY run of EVERY version, and in the reference.

    A version that failed one module otherwise reports totals over a different
    denominator, which makes the versions silently incomparable.
    """
    sets = [set(r) for runs in runs_by_version.values() for r in runs]
    return set.intersection(*sets) & set(reference) if sets else set()


def per_module(res: dict, key: str = "f1") -> dict:
    """{module: metric} for one scored run. The pairing unit for paired()."""
    out = {}
    for mod, m in res["per_module"].items():
        tp, fp, fn = m["tp"], len(m["fp"]), len(m["fn"])
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        out[mod] = {"precision": p, "recall": r,
                    "f1": 2 * p * r / (p + r) if p + r else 0.0}[key]
    return out


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def _sd(xs):
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def ablate(runs_by_version: dict, reference: dict, extra: dict = None,
           strict: bool = True, title: str = "") -> dict:
    """One row per version: mean over repeats, +/- sample sd. Returns {version: [score,...]}.

    `extra` adds unrepeated reference rows (e.g. {"LAsset paper": paper_run}).
    The sd column is the number to read first: any difference between versions smaller
    than it is not measurable with this many repeats.
    """
    mods = common_modules(runs_by_version, reference)
    print(title or "ablation vs manual ground truth")
    print(f"scored on {len(mods)} modules common to every run"
          + ("" if strict else "   [LENIENT matching -- inflates recall]"))
    hdr = (f"{'version':12s} {'n':>2s} {'emit':>5s} {'TP':>4s} {'FP':>4s} {'FN':>4s} "
           f"{'P':>6s} {'recall':>7s} {'sd':>6s} {'F1':>7s} {'sd':>6s}")
    print(hdr)
    print("-" * len(hdr))
    out = {}
    for v, runs in runs_by_version.items():
        rs = [score(r, reference, strict, only=mods) for r in runs]
        out[v] = rs
        col = lambda k: [x[k] for x in rs]                            # noqa: E731
        print(f"{v:12s} {len(rs):2d} {_mean(col('emit')):5.0f} {_mean(col('tp')):4.0f} "
              f"{_mean(col('fp')):4.0f} {_mean(col('fn')):4.0f} {_mean(col('precision')):6.3f} "
              f"{_mean(col('recall')):7.3f} {_sd(col('recall')):6.3f} "
              f"{_mean(col('f1')):7.3f} {_sd(col('f1')):6.3f}")
    for label, run in (extra or {}).items():
        r = score(run, reference, strict, only=mods)
        print(f"{label:12s} {1:2d} {r['emit']:5d} {r['tp']:4d} {r['fp']:4d} {r['fn']:4d} "
              f"{r['precision']:6.3f} {r['recall']:7.3f} {'':6s} {r['f1']:7.3f}")
    return out


def paired(runs_by_version: dict, a: str, b: str, reference: dict, key: str = "f1",
           B: int = 10000, seed: int = 0, strict: bool = True) -> dict:
    """Paired bootstrap of (b - a) on per-module `key`. Prints and returns the result.

    A CI straddling zero is an honest null: with ~15 modules many real-looking
    differences will not clear it. Report the interval, not just the point estimate.
    """
    import random
    mods = sorted(common_modules(runs_by_version, reference))

    def avg(v):
        pms = [per_module(score(r, reference, strict, only=set(mods)), key)
               for r in runs_by_version[v]]
        return {m: _mean(p[m] for p in pms) for m in mods}

    A, Bv = avg(a), avg(b)
    d = [Bv[m] - A[m] for m in mods]
    rng = random.Random(seed)
    boot = sorted(_mean(rng.choices(d, k=len(d))) for _ in range(B))
    res = {"key": key, "n": len(mods), "delta": _mean(d),
           "lo": boot[int(0.025 * B)], "hi": boot[int(0.975 * B)],
           "wins": sum(1 for x in d if x > 1e-9),
           "losses": sum(1 for x in d if x < -1e-9),
           "per_module": dict(zip(mods, d))}
    sig = "" if res["lo"] <= 0 <= res["hi"] else "  *"
    print(f"{b} - {a}   d{key} = {res['delta']:+.3f}  "
          f"95% CI [{res['lo']:+.3f}, {res['hi']:+.3f}]{sig}   "
          f"n={res['n']} modules, {res['wins']} better / {res['losses']} worse")
    if res["lo"] <= 0 <= res["hi"]:
        print("    CI includes 0 -- not distinguishable from no effect at this sample size")
    return res
