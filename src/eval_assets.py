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
from collections import Counter
from pathlib import Path

GT_DIR = Path("ground_truth")


# --------------------------------------------------------------------- load ---

def load_refs(gt_dir=GT_DIR, parsed_dir="parsed_tuning18") -> dict:
    """-> {"gt": ..., "paper": ..., "paper_refined": ...}; each {module: [(element, objective)]}

    A LIST, not a dict keyed by element name. Two entities of one file can hold assets with
    the same name -- neorv32_bus has `state` in both neorv32_bus_switch (arbiter FSM) and
    neorv32_bus_amo_rvs (reservation FSM) -- and a name-keyed dict silently kept one.

    Repeats are capped by how many entities actually declare the name; see _name_caps.
    """
    caps = _name_caps(parsed_dir)

    def read(name):
        p = Path(gt_dir) / name
        if not p.exists():
            return {}
        d = json.loads(p.read_text(encoding="utf-8"))
        out = {}
        for m, v in d["modules"].items():
            seen, keep = {}, []
            for a in v["assets"]:
                e = a.get("element")
                if not e:
                    continue
                cap = caps.get(m, {}).get(e, 1) if caps.get(m) else None
                seen[e] = seen.get(e, 0) + 1
                if cap is None or seen[e] <= cap:
                    keep.append((e, a.get("objective", "")))
            out[m] = keep
        return out

    return {"gt": read("manual_gt_neorv32.json"),
            "paper": read("lasset_initial.json"),
            "paper_refined": read("lasset_refined.json")}


def _name_caps(parsed_dir) -> dict:
    """{module: {name: how many entities declare it}}.

    Reference multiplicity is capped by this. A name may legitimately appear twice when two
    entities of one file each declare it -- neorv32_bus has `state` in both
    neorv32_bus_switch (arbiter FSM) and neorv32_bus_amo_rvs (reservation FSM), written
    `state/state` in one cell. But neorv32_twi lists `twi_sda_i` in two separate rows while
    only one entity declares it; that is annotation redundancy, and counting it twice would
    make a ground-truth element permanently unreachable and depress recall for good.

    Returns {} when the parsed sets are unavailable, in which case no capping is applied.
    """
    caps = {}
    try:
        for f in sorted(Path(parsed_dir).glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            per = {}
            for e in d.get("ports", []) + d.get("signals", []):
                per.setdefault(e["name"], set()).add(e["entity"])
            caps[f.stem] = {k: len(v) for k, v in per.items()}
    except Exception:
        return {}
    return caps


def load_run(assets_dir) -> dict:
    """-> {module: [(entity, name, objective)]} from a directory of <module>.json files.

    Also a list, and carrying the entity, for the same reason as load_refs: a run that
    correctly emitted both `state` assets of neorv32_bus had one of them overwritten by a
    name-keyed dict, so the model was scored below what it actually produced.

    Files whose name starts with '_' are bookkeeping (e.g. _run_meta.json) and are skipped,
    so they cannot be picked up as a module with zero assets.
    """
    out = {}
    for f in sorted(Path(assets_dir).glob("*.json")):
        if f.name.startswith("_"):
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        out[f.stem] = [(a.get("Entity", ""), a["Asset RTL"], a.get("Security Objective", ""))
                       for a in data.get("Assets", []) if a.get("Asset RTL")]
    return out


# -------------------------------------------------------------------- score ---

def _hit_idx(cand, ref_name, strict=True):
    """cand = {prediction index: name}. Returns the index that matches ref_name, or None.

    Index-based rather than name-based so that two predictions sharing a name stay distinct
    and each can be consumed by a different reference entry.

    Exact match first. Then the ONE legitimate near-match: the references name a whole
    record in some places and a single field in others, so `ctrl` <-> `ctrl.enable` must
    match in either direction.

    What strict mode refuses is FIELD-TO-FIELD matching. The old rule also accepted any two
    dotted names sharing a base, so a prediction of `fifo.avail` was credited against a
    ground-truth `fifo.re` -- two different fields, both separately in the reference. That
    silently rewards spraying record fields, and it inflated recall unevenly across prompt
    versions (v0 by 4 TP, v1 by 2), biasing exactly the comparison an ablation is trying to
    make. strict=False restores the old behaviour for back-comparison only.

    Candidates are scanned in (name, index) order: iterating a set would make the choice
    depend on hash order, and two runs of the same data could then report different scores.
    """
    order = sorted(cand, key=lambda i: (cand[i], i))
    for i in order:
        if cand[i] == ref_name:
            return i
    rb = ref_name.split(".")[0]
    dotted = "." in ref_name
    for i in order:
        p = cand[i]
        if (not dotted and p.split(".")[0] == ref_name) or (dotted and p == rb):
            return i
    if not strict:
        for i in order:
            if cand[i].split(".")[0] == rb:
                return i
    return None


def _as_run(d: dict) -> dict:
    """Normalise to run shape [(entity, name, objective)].

    Accepts reference shape [(name, objective)] too, so a reference set can be scored as if
    it were a run -- which is exactly what the 'LAsset paper' baseline row does.
    """
    return {m: [x if len(x) == 3 else ("", x[0], x[1]) for x in v] for m, v in d.items()}


def _obj(s):
    s = (s or "").lower()
    return ("Confidentiality" if "conf" in s else
            "Integrity" if "integ" in s else
            "Availability" if "avail" in s else "")


def score(run, reference: dict, strict: bool = True, only=None) -> dict:
    """`run` is a directory path or a {module: [(entity, name, objective)]} dict.

    Modules absent from the reference are skipped, not counted as false positives:
    the paper pruned boot_rom / fifo / package before generating any assets.

    `only` restricts scoring to a set of module names. Pass it whenever comparing runs:
    if one version failed a module its totals cover a different denominator and the
    versions are not comparable. ablate() computes the intersection and passes it here.

    Matching consumes each prediction at most once, by index, so N reference entries
    sharing a name require N distinct predictions to all be credited.
    """
    pred = _as_run(run) if isinstance(run, dict) else load_run(run)
    per, skipped = {}, []
    for mod, preds in sorted(pred.items()):
        if mod not in reference or (only is not None and mod not in only):
            skipped.append(mod)
            continue
        ref = reference[mod]
        used, hit_ref, obj_ok, obj_n = set(), set(), 0, 0
        for ri, (rname, robj) in enumerate(ref):
            cand = {i: preds[i][1] for i in range(len(preds)) if i not in used}
            pi = _hit_idx(cand, rname, strict)
            if pi is None:
                continue
            used.add(pi)
            hit_ref.add(ri)
            po, ro = _obj(preds[pi][2]), _obj(robj)
            if po and ro:
                obj_n += 1
                obj_ok += (po == ro)
        per[mod] = {
            "ref": len(ref), "emit": len(preds), "tp": len(hit_ref),
            "fp": sorted(preds[i][1] for i in range(len(preds)) if i not in used),
            "fn": sorted(ref[ri][0] for ri in range(len(ref)) if ri not in hit_ref),
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
        dirs = sorted(Path(root).glob(f"{stem}_{v}_r*"))
        pairs = [(d, load_run(d)) for d in dirs]
        pairs = [(d, r) for d, r in pairs if r]
        # A repeat still being generated holds only the modules written so far. Folding it
        # in as a complete repeat drives common_modules() -- the intersection across every
        # run of every version -- down to whatever that partial directory contains, which
        # silently rescopes EVERY version's totals. Observed live: an in-progress r3 with
        # one module (neorv32_boot_rom, alphabetically first) took the common set from 15
        # modules to 0 with no error raised anywhere.
        if pairs:
            full = max(len(r) for _d, r in pairs)
            keep = []
            for d, r in pairs:
                if len(r) < full:
                    print(f"  [warn] {d.name} has {len(r)}/{full} modules -- INCOMPLETE, "
                          f"excluded. Re-run collect() once generation finishes.")
                else:
                    keep.append(r)
            pairs = keep
        runs = pairs
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


# --- element classes -----------------------------------------------------------
# The A-00 error analysis found the failure is not "too many" or "too few" assets but the
# wrong CLASS of element: 64% of misses were plain top-level ports while 82% of false
# positives were internal signals. Aggregate recall hides that completely, so it prints for
# every arm from here on.

CLASSES = ("port", "signal", "signal-field", "port-field", "absent")


def load_closed(parsed_dir="parsed_tuning18") -> dict:
    """{module: {"port": {names}, "signal": {names}}} from the parsed closed sets."""
    out = {}
    for f in sorted(Path(parsed_dir).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out[f.stem] = {"port": {e["name"] for e in d.get("ports", [])},
                       "signal": {e["name"] for e in d.get("signals", [])}}
    return out


def elem_class(mod, name, closed) -> str:
    c = closed.get(mod)
    if not c:
        return "absent"
    dot = "." in name
    base = name.split(".")[0]
    if name in c["port"] or (dot and base in c["port"]):
        return "port-field" if dot else "port"
    if name in c["signal"] or (dot and base in c["signal"]):
        return "signal-field" if dot else "signal"
    return "absent"


def per_module_class(res: dict, reference: dict, closed: dict, cls: str) -> dict:
    """{module: recall within `cls`}, for modules holding at least one element of it.

    The pairing unit for paired(..., cls=...). Modules with no element of the class are
    dropped rather than scored 0 -- they carry no information about that class and would
    otherwise dilute the comparison toward zero.
    """
    out = {}
    for mod, m in res["per_module"].items():
        ref = sum(1 for e, _o in reference[mod] if elem_class(mod, e, closed) == cls)
        if not ref:
            continue
        fn = sum(1 for e in m["fn"] if elem_class(mod, e, closed) == cls)
        out[mod] = (ref - fn) / ref
    return out


def by_class(res: dict, reference: dict, closed: dict) -> dict:
    """{class: {"ref": n, "tp": n, "fn": n, "fp": n}} for one scored run."""
    acc = {k: {"ref": 0, "tp": 0, "fn": 0, "fp": 0} for k in CLASSES}
    for mod, m in res["per_module"].items():
        for name, _o in reference[mod]:
            acc[elem_class(mod, name, closed)]["ref"] += 1
        for name in m["fn"]:
            acc[elem_class(mod, name, closed)]["fn"] += 1
        for name in m["fp"]:
            acc[elem_class(mod, name, closed)]["fp"] += 1
    for k in acc:
        acc[k]["tp"] = acc[k]["ref"] - acc[k]["fn"]
    return acc


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def _sd(xs):
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def near_matches(run, reference: dict, mods=None) -> dict:
    """How many true positives were scored by a NEAR-match rather than exact equality.

    _hit_idx allows two, and both let a prediction score at a different granularity than the
    reference asked for:
        A  record -> field   reference `ctrl`,        prediction `ctrl.enable`
        B  field  -> record  reference `ctrl.enable`, prediction `ctrl`
    B is the weaker: naming the whole record is a coarser claim than naming the field the
    reference singled out. Both exist because the reference set is itself inconsistent about
    granularity (32 whole-signal references against 31 signal-field ones), so M-1 hedged.

    Measured 2026-08-07 and printed by ablate() ever since, because the only way to see it
    before was to write a bespoke script. It is small and shrinking -- 2.7% of TPs at v0,
    0.4% at v01c6 -- and every version-to-version GAIN survives exact-only matching (A-08's
    is identical to three decimals). But an arm that ever rests on it must be visible.

    NOT a way to double-count: predictions are consumed by index, so one bare `ctrl` can
    satisfy exactly one dotted reference, never three.
    """
    pred = _as_run(run) if isinstance(run, dict) else load_run(run)
    out = Counter()
    for mod in sorted(pred):
        if mod not in reference or (mods is not None and mod not in mods):
            continue
        preds, used = pred[mod], set()
        for rname, _o in reference[mod]:
            cand = {i: preds[i][1] for i in range(len(preds)) if i not in used}
            pi = _hit_idx(cand, rname, True)
            if pi is None:
                continue
            used.add(pi)
            p = preds[pi][1]
            if p == rname:
                out["exact"] += 1
            elif "." not in rname and p.split(".")[0] == rname:
                out["A"] += 1
            elif "." in rname and p == rname.split(".")[0]:
                out["B"] += 1
    return dict(out)


def ablate(runs_by_version: dict, reference: dict, extra: dict = None,
           strict: bool = True, title: str = "", closed: dict = None) -> dict:
    """One row per version: mean over repeats, +/- sample sd. Returns {version: [score,...]}.

    `extra` adds unrepeated reference rows (e.g. {"LAsset paper": paper_run}).
    The sd column is the number to read first: any difference between versions smaller
    than it is not measurable with this many repeats.

    The `near` column is TPs scored by a near-match rather than exact equality -- see
    near_matches(). Read it whenever an arm's gain is small: a gain that lives there is a
    gain in vagueness, not in identification.
    """
    mods = common_modules(runs_by_version, reference)
    print(title or "ablation vs manual ground truth")
    print(f"scored on {len(mods)} modules common to every run"
          + ("" if strict else "   [LENIENT matching -- inflates recall]"))
    hdr = (f"{'version':12s} {'n':>2s} {'emit':>5s} {'TP':>4s} {'FP':>4s} {'FN':>4s} "
           f"{'P':>6s} {'recall':>7s} {'sd':>6s} {'F1':>7s} {'sd':>6s} {'near':>5s}")
    print(hdr)
    print("-" * len(hdr))
    out = {}
    for v, runs in runs_by_version.items():
        rs = [score(r, reference, strict, only=mods) for r in runs]
        out[v] = rs
        col = lambda k: [x[k] for x in rs]                            # noqa: E731
        nm = [near_matches(r, reference, mods) for r in runs]
        near = _mean([n.get("A", 0) + n.get("B", 0) for n in nm])
        print(f"{v:12s} {len(rs):2d} {_mean(col('emit')):5.0f} {_mean(col('tp')):4.0f} "
              f"{_mean(col('fp')):4.0f} {_mean(col('fn')):4.0f} {_mean(col('precision')):6.3f} "
              f"{_mean(col('recall')):7.3f} {_sd(col('recall')):6.3f} "
              f"{_mean(col('f1')):7.3f} {_sd(col('f1')):6.3f} {near:5.1f}")
    for label, run in (extra or {}).items():
        r = score(run, reference, strict, only=mods)
        n = near_matches(run, reference, mods)
        print(f"{label:12s} {1:2d} {r['emit']:5d} {r['tp']:4d} {r['fp']:4d} {r['fn']:4d} "
              f"{r['precision']:6.3f} {r['recall']:7.3f} {'':6s} {r['f1']:7.3f} {'':6s}"
              f"{n.get('A', 0) + n.get('B', 0):5.1f}")

    if closed is None:
        try:
            closed = load_closed()
        except Exception:
            closed = None
    if closed:
        _class_block(out, reference, closed, extra, strict, mods)
    return out


def _class_block(out, reference, closed, extra, strict, mods):
    """Per-class recall and FP composition. Aggregate recall hides which class is failing."""
    show = ("port", "signal", "signal-field")
    print(f"\n  recall by element class          "
          + "".join(f"{c:>13s}" for c in show))
    for v, rs in out.items():
        cs = [by_class(r, reference, closed) for r in rs]
        cells = []
        for c in show:
            rec = [x[c]["tp"] / x[c]["ref"] if x[c]["ref"] else 0.0 for x in cs]
            cells.append(f"{_mean(rec):8.3f}{'':5s}")
        n = cs[0]
        print(f"  {v:12s} (ref {'/'.join(str(n[c]['ref']) for c in show)})".ljust(35)
              + "".join(cells))
    for label, run in (extra or {}).items():
        c1 = by_class(score(run, reference, strict, only=mods), reference, closed)
        cells = "".join(f"{(c1[c]['tp']/c1[c]['ref'] if c1[c]['ref'] else 0):8.3f}{'':5s}"
                        for c in show)
        print(f"  {label:12s}".ljust(35) + cells)

    print(f"\n  false positives by class         "
          + "".join(f"{c:>13s}" for c in CLASSES[:4]))
    for v, rs in out.items():
        cs = [by_class(r, reference, closed) for r in rs]
        cells = "".join(f"{_mean(x[c]['fp'] for x in cs):8.0f}{'':5s}" for c in CLASSES[:4])
        print(f"  {v:12s}".ljust(35) + cells)
    for label, run in (extra or {}).items():
        c1 = by_class(score(run, reference, strict, only=mods), reference, closed)
        cells = "".join(f"{c1[c]['fp']:8d}{'':5s}" for c in CLASSES[:4])
        print(f"  {label:12s}".ljust(35) + cells)


def paired(runs_by_version: dict, a: str, b: str, reference: dict, key: str = "f1",
           B: int = 10000, seed: int = 0, strict: bool = True,
           cls: str = None, closed: dict = None) -> dict:
    """Paired bootstrap of (b - a) on per-module `key`. Prints and returns the result.

    With `cls` set ("port" / "signal" / "signal-field") the pairing unit becomes that
    class's per-module recall. Use it: A-01 showed the aggregate can read "inconclusive"
    while the classes move +0.263 and -0.198 in opposite directions and cancel. Aggregate
    recall is the metric most likely to hide a real effect at this sample size.

    A CI straddling zero is an honest null: with ~15 modules many real-looking differences
    will not clear it. Report the interval, not just the point estimate.
    """
    import random
    mods = sorted(common_modules(runs_by_version, reference))
    if cls and closed is None:
        closed = load_closed()

    def avg(v):
        scored = [score(r, reference, strict, only=set(mods)) for r in runs_by_version[v]]
        pms = ([per_module_class(s, reference, closed, cls) for s in scored] if cls
               else [per_module(s, key) for s in scored])
        return {m: _mean(p[m] for p in pms if m in p) for m in mods
                if any(m in p for p in pms)}

    A, Bv = avg(a), avg(b)
    mods = sorted(set(A) & set(Bv))          # cls drops modules lacking that element type
    d = [Bv[m] - A[m] for m in mods]
    rng = random.Random(seed)
    boot = sorted(_mean(rng.choices(d, k=len(d))) for _ in range(B))
    res = {"key": key, "n": len(mods), "delta": _mean(d),
           "lo": boot[int(0.025 * B)], "hi": boot[int(0.975 * B)],
           "wins": sum(1 for x in d if x > 1e-9),
           "losses": sum(1 for x in d if x < -1e-9),
           "per_module": dict(zip(mods, d))}
    res["class"] = cls
    label = f"{cls} recall" if cls else key
    sig = "" if res["lo"] <= 0 <= res["hi"] else "  *"
    print(f"  {b} - {a}   d({label}) = {res['delta']:+.3f}  "
          f"95% CI [{res['lo']:+.3f}, {res['hi']:+.3f}]{sig}   "
          f"n={res['n']} modules, {res['wins']} better / {res['losses']} worse")
    if res["lo"] <= 0 <= res["hi"]:
        print("      CI includes 0 -- not distinguishable from no effect at this sample size")
    return res


def paired_classes(runs_by_version: dict, a: str, b: str, reference: dict,
                   closed: dict = None, **kw) -> dict:
    """paired() for each element class plus the aggregate -- the primary report.

    Print this rather than the aggregate alone. A-01 is the worked example of why:
    aggregate recall +0.049 [-0.061, +0.166] read as "no effect", while port recall rose
    0.263 and signal recall fell 0.198. The aggregate was not wrong, it was uninformative.
    """
    if closed is None:
        closed = load_closed()
    out = {}
    print(f"\npaired deltas, {b} vs {a} (modules as the pairing unit):")
    for c in ("port", "signal", "signal-field"):
        out[c] = paired(runs_by_version, a, b, reference, cls=c, closed=closed, **kw)
    for k in ("recall", "f1"):
        out[k] = paired(runs_by_version, a, b, reference, key=k, **kw)
    return out


# ------------------------------------------------------------- validation ---
# The run loop writes <run_dir>/_validation.json per repeat. Through v01c6p1 that file is
# uninteresting -- every version receiving the parsed closed set sits at zero ungrounded
# names. P-2 withholds that list, so from v01c6p1p2 onward the ungrounded rate is a headline
# number of the arm, not bookkeeping.

def load_validation(versions, root=".", stem="assets_tuning18") -> dict:
    """{version: [report per repeat]} from each run directory's _validation.json.

    Missing files are skipped silently: every run before 2026-08-08 predates the report,
    and their absence is not an error.

    INCOMPLETE REPEATS ARE EXCLUDED, exactly as collect() excludes them. The run loop writes
    this file after the thread pool drains, so a repeat that was interrupted -- or never
    started, because the loop creates all REPEATS directories up front -- still leaves a
    valid report behind describing 0 or 10 modules. Averaging those in with a complete
    repeat silently divides every count by the number of aborted repeats. First observed on
    P-2, where r0's 40 ungrounded names over 493 assets read as 8.2 over 144 because r1-r4
    were empty or partial.
    """
    out = {}
    for v in versions:
        reps = []
        for d in sorted(Path(root).glob(f"{stem}_{v}_r*")):
            p = d / "_validation.json"
            if p.exists():
                reps.append((d, json.loads(p.read_text(encoding="utf-8"))))
        if not reps:
            continue
        full = max(len(r.get("modules", {})) for _d, r in reps)
        keep = []
        for d, r in reps:
            n = len(r.get("modules", {}))
            if n < full:
                print(f"  [warn] {d.name}/_validation.json covers {n}/{full} modules -- "
                      f"INCOMPLETE, excluded")
            else:
                keep.append(r)
        if keep:
            out[v] = keep
    return out


def validation_table(versions, root=".", stem="assets_tuning18") -> dict:
    """One row per version: mean counts by issue kind, and where the ungrounded names came
    from. Returns the aggregated dict as well as printing it.

    The three ungrounded columns are the point. An ungrounded name whose base identifier IS
    present in the RTL is evidence about rtl_parse -- the model found something our regex
    did not -- while one that is absent from the RTL is a plain invention. Reporting them as
    a single count would hide a parser gap inside a model error rate.
    """
    reports = load_validation(versions, root=root, stem=stem)
    print(f"  {'version':12s}{'n':>3s}{'assets':>8s}{'ungnd':>7s}{'rate':>7s} |"
          f"{'in RTL':>8s}{'near<=2':>9s}{'invented':>10s} |{'ent.mism':>10s}{'bad obj':>9s}"
          f"{'concept':>9s}")
    out = {}
    for v in versions:
        reps = reports.get(v)
        if not reps:
            print(f"  {v:12s}  -   (no _validation.json -- run predates the report)")
            continue
        acc = []
        for rep in reps:
            t = rep.get("totals", {})
            issues = [i for m in rep.get("modules", {}).values() for i in m.get("issues", [])]
            ung = [i for i in issues if i.get("kind") == "ungrounded"]
            acc.append({
                "assets": t.get("assets", 0), "ungrounded": len(ung),
                "in_rtl": sum(1 for i in ung if i.get("in_rtl_base")),
                "near": sum(1 for i in ung if (i.get("distance") is not None
                                               and i["distance"] <= 2)),
                "invented": sum(1 for i in ung if i.get("in_rtl_base") is False),
                "entity_mismatch": t.get("entity_mismatch", 0),
                "bad_objective": t.get("bad_objective", 0),
                "concept_contract": t.get("concept_contract", 0)})
        m = {k: sum(a[k] for a in acc) / len(acc) for k in acc[0]}
        out[v] = m
        print(f"  {v:12s}{len(acc):3d}{m['assets']:8.0f}{m['ungrounded']:7.1f}"
              f"{m['ungrounded'] / max(1, m['assets']):7.1%} |"
              f"{m['in_rtl']:8.1f}{m['near']:9.1f}{m['invented']:10.1f} |"
              f"{m['entity_mismatch']:10.1f}{m['bad_objective']:9.1f}"
              f"{m['concept_contract']:9.1f}")
    return out
