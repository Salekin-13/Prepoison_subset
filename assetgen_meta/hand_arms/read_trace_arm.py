"""Pre-registered readings for arm m7e194es0ist (traced) against the winner m7e194es0ism. Fixed 2026-10-01, before the
arm ran. Tuning set, 15 reference modules (111 entries), 3 runs per version, gpt-5-mini, strict scorer.

 R0  P / R / emitted per run, both versions, with the LAsset initial row (0.737 / 0.910, 137 emitted).
 R1  traceability (the arm's purpose): share of reported references whose citation is 'verified' by trace_check
     (own occurrence, existing edge at it, edge fits the role). PASS if >= 0.80; and 'invalid' + 'no citation' <= 0.05.
 R2  every "yes" answer cites an RTL line that exists: PASS if >= 0.95 of them; flow lines likewise (reported).
 R3  recall guards. Three parts of this design were measured to cost recall before: the map in the input (arm ismr,
     recall 0.778), the four questions (ismq, -0.09), a separate list for non-reported elements (v2sec, 0.925 -> 0.628).
     (a) recall >= 0.80: PASS / FAIL;  (b) displacement: reference run-slots whose element the run puts in influence
     points or exclusions but not among its references (reported; the mechanism behind a recall loss);  (c) port-field
     false-positive slots (the menu effect; expected 0);  (d) emitted per run against the winner (reported).
 R4  evaluation-layer row CITE: each run keeps only references whose citation is verified -> P / R (a code lever,
     reported separately, like NONE).
 R5  parse: modules without a parsed output per run (output-size risk of the larger contract).
 Adoption: the Step 1b bar (P >= 0.374 at R >= 0.83) AND R1 PASS.
"""
import json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "assetgen_meta", "assetgen_meta/hand_arms", "blind_agent"):
    sys.path.insert(0, str(ROOT / p))
import eval_assets as ea          # noqa: E402
import trace_check as TC          # noqa: E402
import read_def_arm as rda        # noqa: E402
import diagnose as DG             # noqa: E402


def read(arm="m7e194es0ist", base="m7e194es0ism", log=print, reps=(0, 1, 2)):
    R = ea.load_refs(); gt = R["gt"]
    mods = sorted(m for m in gt if (ROOT / "assetgen_meta/traced_inputs/tuning" / f"{m}.txt").exists()
                  and (ROOT / "parsed_tuning18" / f"{m}.json").exists())
    ini = ea.score({m: R["paper"][m] for m in mods}, gt, strict=True, only=set(mods))
    log(f"{arm} readings: {len(mods)} modules, {sum(len(gt[m]) for m in mods)} reference entries, runs {list(reps)}")
    log(f"   R0  LAsset initial (no CWE refinement)   P {ini['precision']:.3f} R {ini['recall']:.3f} emitted {ini['emit']}")
    res = {}
    for v in (base, arm):
        h, f, em = rda.slots(v, gt, mods)
        res[v] = (h, f, em)
        log(f"   R0  {v:36s} P {sum(e[0] for e in em) / 3:.3f} R {sum(e[1] for e in em) / 3:.3f} emitted/run {sum(e[2] for e in em) / 3:.1f}"
            f"   (runs P {[round(e[0], 3) for e in em]} R {[round(e[1], 3) for e in em]})")
    tr = TC.run(arm, reps, gt=gt)
    st = Counter(); stI = Counter(); yes = yes_ok = fl = fl_ok = 0
    for k in reps:
        s = tr[k]["summary"]
        st.update(s["ref_status"]); stI.update(s["influence_status"])
        yes += s["yes_answers"]; yes_ok += s["yes_with_rtl_line"]; fl += s["flow_lines_cited"]; fl_ok += s["flow_lines_in_rtl"]
    n = sum(st.values())
    ver = st["verified"] / n if n else 0.0
    bad = (st["invalid"] + st["no citation"]) / n if n else 1.0
    log(f"   R1  references verified {st['verified']}/{n} = {ver:.2f}; invalid + no citation {bad:.2f} -> "
        f"{'PASS' if ver >= 0.80 and bad <= 0.05 else 'FAIL'}   statuses {dict(st)}")
    log(f"       influence points: {dict(stI)}")
    log(f"   R2  yes answers with an existing RTL line {yes_ok}/{yes} -> {'PASS' if yes and yes_ok / yes >= 0.95 else 'FAIL'}; "
        f"flow lines in RTL {fl_ok}/{fl}")
    (ha, fa, ea_) = res[arm]
    rec = sum(e[1] for e in ea_) / 3
    disp = 0
    for k in reps:
        for m, ch in tr[k]["checks"].items():
            if m not in gt:
                continue
            reported = {r["element"] for r in ch["refs"]}
            parked = {r["element"] for r in ch["influence"]} | {x.get("element") for x in ch["exclusions"] if isinstance(x, dict)}
            disp += sum(1 for nme, _o in gt[m] if nme in parked and nme not in reported)
    pf = sum(c for (m, nme), c in fa.items() if DG.kinds("tuning", m).get(nme, "").startswith("port-field"))
    mb, ma = sum(e[2] for e in res[base][2]) / 3, sum(e[2] for e in ea_) / 3
    log(f"   R3  (a) recall {rec:.3f} -> {'PASS' if rec >= 0.80 else 'FAIL'}; (b) reference slots parked in influence points or "
        f"exclusions and not reported: {disp}; (c) port-field FP slots {pf}; (d) emitted/run {mb:.1f} -> {ma:.1f} ({(ma - mb) / mb:+.0%})")
    cl = TC.cite_filter(arm, reps)
    sc = [ea.score(r, gt, strict=True, only=set(mods)) for r in cl]
    log(f"   R4  CITE row (verified references only): P {sum(s['precision'] for s in sc) / len(sc):.3f} "
        f"R {sum(s['recall'] for s in sc) / len(sc):.3f} emitted/run {sum(s['emit'] for s in sc) / len(sc):.1f}")
    miss = [sorted(set(mods) - {f.stem for f in (ROOT / f"assets_tuning18_{arm}_r{k}" / "_nested").glob("*.json")}) for k in reps]
    log(f"   R5  modules without a parsed output per run: {[len(x) for x in miss]} {miss if any(miss) else ''}")
    pa = sum(e[0] for e in ea_) / 3
    log(f"   Adoption (Step 1b bar P >= 0.374 at R >= 0.83, and R1 PASS): P {pa:.3f} R {rec:.3f} -> "
        f"{'counts' if pa >= 0.374 and rec >= 0.83 and ver >= 0.80 and bad <= 0.05 else 'does not count'}")
    log(f"   trace reports: assetgen_meta/traces_ist/{arm}/r<k>/<module>.md")


if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    sys.stdout.reconfigure(encoding="utf-8")
    read(*(sys.argv[1:3] or ()))
