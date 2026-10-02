"""Why m7e194es0ist lost recall and gained little precision against m7e194es0ism (tuning, 15 reference modules, 3 runs
each, strict scorer). Code only; reference-side analysis.

1. Per reference entry: hit runs in each version. LOST = found in >= 2 runs by ism and <= 1 by ist; GAINED = reverse.
   For each lost entry: its kind, the realization label(s) ism gave it, where ist put it in the runs that missed it
   (trace_digest._where), and whether the map has ANY record of that element that fits ism's label under the traced
   prompt's fit table (trace_check.fits) -> "citable" or "not citable" (the citation rule then forces an edge-null
   'map gap' claim, or an omission).
2. False positives per run by kind for both versions, and the new kinds' elements (module/element: runs).
3. Concepts and references per module per run, both versions.
4. Output size: characters of the raw answer per module (ist vs ism), the size pressure of the larger contract.
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "assetgen_meta", "blind_agent"):
    sys.path.insert(0, str(ROOT / p))
import eval_assets as ea          # noqa: E402
import trace_check as TC          # noqa: E402
import trace_digest as TD         # noqa: E402
import traced_inputs as TI        # noqa: E402
import diagnose as DG             # noqa: E402

A, B = "m7e194es0ism", "m7e194es0ist"
GT = ea.load_refs()["gt"]
MODS = sorted(m for m in GT if (ROOT / f"assets_tuning18_{B}_r0" / f"{m}.json").exists())
REPS = (0, 1, 2)


def hits_fps(v):
    h, f = Counter(), Counter()
    for k in REPS:
        s = ea.score(ROOT / f"assets_tuning18_{v}_r{k}", GT, strict=True, only=set(MODS))
        for m in MODS:
            miss = Counter(s["per_module"][m]["fn"])
            for n, _o in GT[m]:
                if miss[n] > 0:
                    miss[n] -= 1
                else:
                    h[(m, n)] += 1
            for n in set(s["per_module"][m]["fp"]):
                f[(m, n)] += 1
    return h, f


def labels(v, m, n):
    out = Counter()
    for k in REPS:
        o = TD._nested(v, k, m)
        for c in (o or {}).get("conceptual assets", []) or []:
            for s in c.get("related structural assets", []) or []:
                if isinstance(s, dict) and s.get("asset rtl") == n:
                    out[s.get("realization")] += 1
    return out


def citable(m, n, label):
    mapd = TI.load_map("tuning", m)
    if not mapd:
        return "no map"
    ix = TC.MapIndex(mapd)
    e = ix.get(n)
    if e is None:
        return "not in map"
    cands = [(r["type"], None) for r in e.get("relationship", []) or []] + [("CONNECTS", c.get("mode")) for c in e.get("connections", []) or []]
    for f in ix.fields(n, e.get("entity")):
        cands += [(r["type"], None) for r in f.get("relationship", []) or []]
    return "citable" if any(TC.fits(TC.FIT, label, t, e, cm) for t, cm in cands) else "not citable"


def main(log=print):
    ha, fa = hits_fps(A)
    hb, fb = hits_fps(B)
    keys = [(m, n) for m in MODS for n, _o in GT[m]]
    lost = [k for k in keys if ha[k] >= 2 and hb[k] <= 1]
    gained = [k for k in keys if hb[k] >= 2 and ha[k] <= 1]
    log(f"reference entries {len(keys)}; hit run-slots {A} {sum(ha.values())}, {B} {sum(hb.values())}; "
        f"LOST {len(lost)}, GAINED {len(gained)}")
    where, kinds, lab, cit = Counter(), Counter(), Counter(), Counter()
    rows = []
    for m, n in lost:
        kind = DG.kinds("tuning", m).get(n, "absent")
        la = labels(A, m, n)
        top = la.most_common(1)[0][0] if la else "?"
        c = citable(m, n, top)
        ws = []
        for k in REPS:
            o = TD._nested(B, k, m)
            if o is None:
                continue
            chk = TC.check_output(o, TI.load_map("tuning", m) or {"ports": [], "signals": []}, TC.numbered_lines(TC.module_input("tuning", m) or ""))
            if n not in {r["element"] for r in chk["refs"]}:
                w = TD._where(n, o, chk)
                ws.append(w.split(" (")[0]); where[w.split(" (")[0]] += 1
        kinds[kind] += 1; lab[top] += 1; cit[c] += 1
        rows.append(f"   {m[8:]:14s} {n:24s} {kind:12s} ism {ha[(m, n)]}/3 as {dict(la)}  ist {hb[(m, n)]}/3  ist put it: {Counter(ws)}  map {c}")
    log(f"LOST by kind {dict(kinds)}; by ism label {dict(lab)}; where ist put them (run-slots) {dict(where)}; "
        f"citable under the traced fit table: {dict(cit)}")
    for r in rows:
        log(r)
    log("GAINED: " + ", ".join(f"{m[8:]}/{n} ({ha[(m, n)]}->{hb[(m, n)]})" for m, n in gained))
    # 2 false positives by kind
    for v, f in ((A, fa), (B, fb)):
        by = Counter()
        for (m, n), c in f.items():
            by[DG.kinds("tuning", m).get(n, "absent")] += c
        log(f"FP run-slots by kind {v}: {dict(sorted(by.items(), key=lambda x: -x[1]))}  total {sum(f.values())}")
    newk = defaultdict(list)
    for (m, n), c in fb.items():
        k = DG.kinds("tuning", m).get(n, "absent")
        if k.startswith("port-field") or (k.startswith("port-") and fa[(m, n)] == 0 and c >= 2):
            newk[k].append(f"{m[8:]}/{n}:{c}")
    for k, xs in newk.items():
        log(f"   {B} {k} FPs not in {A}: {', '.join(sorted(xs))}")
    # 3 concepts and references per module
    log("concepts / references per run, per module (ism -> ist):")
    for m in MODS:
        ca = [len((TD._nested(A, k, m) or {}).get("conceptual assets", [])) for k in REPS]
        cb = [len((TD._nested(B, k, m) or {}).get("conceptual assets", [])) for k in REPS]
        ra = [sum(len(c.get("related structural assets", []) or []) for c in (TD._nested(A, k, m) or {}).get("conceptual assets", []) if isinstance(c, dict)) for k in REPS]
        rb = [sum(len(c.get("related structural assets", []) or []) for c in (TD._nested(B, k, m) or {}).get("conceptual assets", []) if isinstance(c, dict)) for k in REPS]
        sa = [len((ROOT / f"assets_tuning18_{A}_r{k}" / "_raw" / f"{m}.json").read_text(encoding="utf-8")) for k in REPS]
        sb = [len((ROOT / f"assets_tuning18_{B}_r{k}" / "_raw" / f"{m}.json").read_text(encoding="utf-8")) for k in REPS]
        log(f"   {m[8:]:16s} concepts {sum(ca) / 3:5.1f} -> {sum(cb) / 3:5.1f}   refs {sum(ra) / 3:5.1f} -> {sum(rb) / 3:5.1f}   "
            f"answer chars {sum(sa) / 3:8.0f} -> {sum(sb) / 3:8.0f}")


if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    sys.stdout.reconfigure(encoding="utf-8")
    main()
