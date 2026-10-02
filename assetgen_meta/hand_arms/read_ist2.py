"""Pre-registered readings for arm m7e194es0ist2 (generation call + CIA labelling call). Fixed 2026-10-02, before the arm
ran. Tuning set: 15 reference modules, 111 entries, 3 runs, gpt-5-mini, strict scorer; noise about 0.03. Built from
the evidence workflow's evaluation (hand_arms/m7e194es0ist2/evidence_v1v2_theory_evaluation.json, section 4).

GENERATION
 R0  P / R / emitted per run: m7e194es0ism, m7e194es0ist, m7e194es0ist2; LAsset initial spec+RTL (0.737 / 0.910) and
     RTL-only (0.680 / 0.748; LAsset_initial_results/asset_list_neorv32_initial.json, the like-for-like row).
 R1  format and traceability: no removed field in any output; >= 90% of references verified (ist: 94%).
 R2  headline: R >= 0.817 and P >= 0.344. Adoption: Step 1b bar P >= 0.374 at R >= 0.83.
 R3  breadth: concepts per run >= 105 (ism 116.3, ist 92.0).
 R4  the reference entries ist parked in influence points: hit run-slots back >= 12 of the 19; emitted <= 285 per run.
 R5  transport: FP run-slots on transport records <= 5 (ist about 40); port-field FP run-slots <= 2; cpu_pmp ctrl_i 3/3.
 R6  sub-unit values: cpu alu_res, csr_rdata, lsu_mar, lsu_err found in >= 2 runs each for >= 3 of the 4.
 R7  map cost: if R ends within 0.03 of 0.778 and cpu recall < 0.6, the map in the input is the remaining cost.
 R8  lost entries against ism (found in >= 2 runs by ism, <= 1 by ist2) <= 8 (ist: 20).
 R9  evaluation-layer rows (ist_levers): T, BF, T+BF, MV, MV+T+BF; each reported, none adopted from this reading.
CIA LABELLING (never changes the list, so never P or R)
 C1  discrimination: for each question, no single answer on more than 90% of concepts (ist: 98-100%).
 C2  evidence: >= 90% of yes AND no answers cite an RTL line of the input (ist: 1 of 520 "no" had evidence).
 C3  objective mix (labelled) printed next to the reference's (I 75 / A 33 / C 3 on these modules), not tuned to it;
     confidentiality yes (RTL or assumed) by value kind.
 C4  evaluation-layer row: drop the references of concepts labelled "none" -> P / R, against random thinning of the
     same number of references (1,000 draws, seed 0).
"""
import json, random, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "assetgen_meta", "assetgen_meta/hand_arms", "blind_agent"):
    sys.path.insert(0, str(ROOT / p))
import eval_assets as ea          # noqa: E402
import trace_check as TC          # noqa: E402
import trace_digest as TD         # noqa: E402
import ist_levers as IL           # noqa: E402
import read_def_arm as rda        # noqa: E402
import diagnose as DG             # noqa: E402

ISM, IST = "m7e194es0ism", "m7e194es0ist"
REPS = (0, 1, 2)
CPU_SUB = ["alu_res", "csr_rdata", "lsu_mar", "lsu_err"]


def _mods(gt):
    return sorted(m for m in gt if (ROOT / "RTL_data" / f"{m}.vhd").exists())


def _lasset_rtl_only(gt, mods):
    f = ROOT / "LAsset_initial_results" / "asset_list_neorv32_initial.json"
    run = {ip["IP"]: [(a.get("Entity", ""), a.get("Asset RTL", ""), "") for a in ip.get("Assets", []) if a.get("Asset RTL")]
           for ip in json.loads(f.read_text(encoding="utf-8"))}
    return ea.score({m: run.get(m, []) for m in mods}, gt, strict=True, only=set(mods))


def read(arm="m7e194es0ist2", log=print):
    R = ea.load_refs(); gt = R["gt"]; mods = _mods(gt)
    ini = ea.score({m: R["paper"][m] for m in mods}, gt, strict=True, only=set(mods))
    ro = _lasset_rtl_only(gt, mods)
    log(f"{arm} readings: {len(mods)} modules, {sum(len(gt[m]) for m in mods)} reference entries, runs {list(REPS)}")
    log(f"   R0  LAsset initial spec+RTL            P {ini['precision']:.3f} R {ini['recall']:.3f} emitted {ini['emit']}")
    log(f"   R0  LAsset initial RTL-only (like-for-like) P {ro['precision']:.3f} R {ro['recall']:.3f} emitted {ro['emit']}")
    res = {}
    for v in (ISM, IST, arm):
        h, f, em = rda.slots(v, gt, mods)
        res[v] = (h, f, em)
        log(f"   R0  {v:16s} P {sum(e[0] for e in em) / 3:.3f} R {sum(e[1] for e in em) / 3:.3f} emitted/run {sum(e[2] for e in em) / 3:6.1f}"
            f"   runs P {[round(e[0], 3) for e in em]} R {[round(e[1], 3) for e in em]}")
    ha, fa, ea_ = res[arm]
    P = sum(e[0] for e in ea_) / 3; Rr = sum(e[1] for e in ea_) / 3; emit = sum(e[2] for e in ea_) / 3
    # R1
    removed = 0
    for k in REPS:
        for m in mods:
            f = ROOT / f"assets_tuning18_{arm}_r{k}" / "_nested" / f"{m}.json"
            if f.exists():
                o = json.loads(f.read_text(encoding="utf-8"))
                removed += sum(1 for x in ("hypotheses", "exclusions") if x in o) + sum(
                    1 for c in o.get("conceptual assets", []) or [] if isinstance(c, dict) for x in ("questions", "influence points") if x in c)
    tr = TC.run(arm, REPS, gt=gt)
    st = Counter()
    for k in REPS:
        st.update(tr[k]["summary"]["ref_status"])
    n = sum(st.values())
    ver = st["verified"] / n if n else 0.0
    log(f"   R1  removed fields present {removed}; references verified {st['verified']}/{n} = {ver:.2f} -> "
        f"{'PASS' if removed == 0 and ver >= 0.90 else 'FAIL'}   {dict(st)}")
    log(f"   R2  P {P:.3f} R {Rr:.3f} -> {'PASS' if Rr >= 0.817 and P >= 0.344 else 'FAIL'}; Step 1b bar -> "
        f"{'counts' if P >= 0.374 and Rr >= 0.83 else 'does not count'}")
    # R3
    cpr = {}
    for v in (ISM, IST, arm):
        tot = 0
        for k in REPS:
            for m in mods:
                o = TD._nested(v, k, m)
                tot += len([c for c in (o or {}).get("conceptual assets", []) or [] if isinstance(c, dict)])
        cpr[v] = tot / 3
    log(f"   R3  concepts per run: ism {cpr[ISM]:.1f}, ist {cpr[IST]:.1f}, {arm} {cpr[arm]:.1f} -> {'PASS' if cpr[arm] >= 105 else 'FAIL'}")
    # R4 entries ist parked in influence points
    parked = set()
    for k in REPS:
        for m in mods:
            o = TD._nested(IST, k, m)
            if not o:
                continue
            refs = {s.get("asset rtl") for c in o.get("conceptual assets", []) or [] for s in c.get("related structural assets", []) or [] if isinstance(s, dict)}
            infl = {ip.get("element") for c in o.get("conceptual assets", []) or [] for ip in c.get("influence points", []) or [] if isinstance(ip, dict)}
            for nm, _o in gt[m]:
                if nm in infl and nm not in refs:
                    parked.add((m, nm, k))
    hb_ist = res[IST][0]
    keys = sorted({(m, nm) for m, nm, _k in parked})
    slots_ist = len(parked)
    back = sum(min(ha[(m, nm)], sum(1 for x in parked if x[:2] == (m, nm))) for m, nm in keys)
    log(f"   R4  ist parked {slots_ist} reference run-slots in influence points ({len(keys)} entries); {arm} hits on them "
        f"{back}/{slots_ist}; emitted/run {emit:.1f} -> {'PASS' if back >= 12 and emit <= 285 else 'FAIL'}")
    # R5
    tslots = pfs = 0
    for (m, nm), c in fa.items():
        if not IL.T({m: [("", nm, "")]})[m]:
            if nm in IL._port_fields(m):
                pfs += c
            else:
                tslots += c
    ctrl = ha[("neorv32_cpu_pmp", "ctrl_i")]
    log(f"   R5  transport / clock-reset FP run-slots {tslots}; port-field FP run-slots {pfs}; cpu_pmp ctrl_i {ctrl}/3 -> "
        f"{'PASS' if tslots <= 5 and pfs <= 2 and ctrl == 3 else 'FAIL'}")
    # R6
    sub = {nm: ha[("neorv32_cpu", nm)] for nm in CPU_SUB}
    log(f"   R6  cpu sub-unit values {sub} -> {'PASS' if sum(v >= 2 for v in sub.values()) >= 3 else 'FAIL'}")
    # R7
    cpu_rec = sum(min(3, ha[("neorv32_cpu", nm)]) for nm, _o in gt["neorv32_cpu"]) / (3 * len(gt["neorv32_cpu"]))
    log(f"   R7  cpu recall {cpu_rec:.3f}; R {Rr:.3f} -> " + ("the map in the input is the remaining cost (drop it next)"
                                                         if abs(Rr - 0.778) <= 0.03 and cpu_rec < 0.6 else "not the map pattern"))
    # R8
    hs = res[ISM][0]
    lost = [(m, nm) for m in mods for nm, _o in gt[m] if hs[(m, nm)] >= 2 and ha[(m, nm)] <= 1]
    gained = [(m, nm) for m in mods for nm, _o in gt[m] if ha[(m, nm)] >= 2 and hs[(m, nm)] <= 1]
    log(f"   R8  lost against ism {len(lost)} (pass if <= 8), gained {len(gained)} -> {'PASS' if len(lost) <= 8 else 'FAIL'}")
    log("       lost: " + ", ".join(f"{m[8:]}/{nm}" for m, nm in lost))
    # R9
    for name in ("T", "BF", "T+BF", "MV", "MV+T+BF"):
        s = IL.score(arm, name, gt, mods)
        log(f"   R9  {name:8s} P {s['precision']:.3f} R {s['recall']:.3f} emitted {s['emit']:.1f}")
    cia(arm, gt, mods, log)


def cia(arm, gt, mods, log=print):
    import cia_label as CL
    dist, lines_ok, lines_n, kinds_c, objs, none_refs = defaultdict(Counter), 0, 0, Counter(), Counter(), []
    labelled = concepts = 0
    for k in REPS:
        for m in mods:
            o = TD._nested(arm, k, m)
            if not o:
                continue
            numbered = TC.numbered_lines(TC.module_input("tuning", m) or "")
            for c in o.get("conceptual assets", []) or []:
                if not isinstance(c, dict):
                    continue
                concepts += 1
                q = c.get("questions")
                if not q:
                    continue
                labelled += 1
                for qq in CL.QS:
                    a = (q.get(qq) or {})
                    ans = a.get("answer")
                    dist[qq][ans] += 1
                    if ans and ans != "unknown":
                        lines_n += 1
                        lines_ok += TC._int(a.get("line")) in numbered
                obj = c.get("labelled objective")
                objs[obj] += 1
                if str((q.get("confidentiality") or {}).get("answer", "")).startswith("yes"):
                    kinds_c[c.get("kind")] += 1
                if obj == "none":
                    none_refs.append((k, m, [s.get("asset rtl") for s in c.get("related structural assets", []) or [] if isinstance(s, dict)]))
    log(f"   CIA labelled concepts {labelled}/{concepts}")
    worst = 0.0
    for qq in CL.QS:
        tot = sum(dist[qq].values()) or 1
        top = dist[qq].most_common(1)[0][1] / tot if dist[qq] else 0
        worst = max(worst, top)
        log(f"   C1  {qq:20s} {dict(dist[qq])}  (largest share {top:.2f})")
    log(f"   C1  -> {'PASS' if worst <= 0.90 else 'FAIL'} (largest single-answer share {worst:.2f})")
    log(f"   C2  yes / no answers with an RTL line of the input {lines_ok}/{lines_n} -> "
        f"{'PASS' if lines_n and lines_ok / lines_n >= 0.90 else 'FAIL'}")
    ref_obj = Counter(o for m in mods for _n, o in gt[m])
    log(f"   C3  labelled objectives {dict(objs)}; reference objectives on these modules {dict(ref_obj)}; "
        f"confidentiality yes by kind {dict(kinds_c)}")
    # C4: drop the references of concepts labelled none, against random thinning of the same size
    lists = [ea.load_run(ROOT / f"assets_tuning18_{arm}_r{k}") for k in REPS]
    lists = [{m: r[m] for m in mods if m in r} for r in lists]
    drop = defaultdict(set)
    for k, m, els in none_refs:
        drop[(k, m)] |= set(els)
    # an element is dropped only if every concept that lists it in that run is labelled none
    keep_any = defaultdict(set)
    for k in REPS:
        for m in mods:
            o = TD._nested(arm, k, m) or {}
            for c in o.get("conceptual assets", []) or []:
                if isinstance(c, dict) and c.get("labelled objective") not in (None, "none"):
                    keep_any[(k, m)] |= {s.get("asset rtl") for s in c.get("related structural assets", []) or [] if isinstance(s, dict)}
    filt, ndrop = [], Counter()
    for k, r in zip(REPS, lists):
        out = {}
        for m, lst in r.items():
            d = drop[(k, m)] - keep_any[(k, m)]
            out[m] = [x for x in lst if x[1] not in d]
            ndrop[(k, m)] = len(lst) - len(out[m])
        filt.append(out)
    sc = [ea.score(x, gt, strict=True, only=set(mods)) for x in filt]
    Pn, Rn = sum(s["precision"] for s in sc) / 3, sum(s["recall"] for s in sc) / 3
    rng = random.Random(0)
    rp = []
    for _ in range(1000):
        th = []
        for k, r in zip(REPS, lists):
            out = {}
            for m, lst in r.items():
                cut = set(rng.sample(range(len(lst)), min(ndrop[(k, m)], len(lst))))
                out[m] = [x for i, x in enumerate(lst) if i not in cut]
            th.append(out)
        rp.append(sum(ea.score(x, gt, strict=True, only=set(mods))["precision"] for x in th) / 3)
    rp.sort()
    log(f"   C4  drop references of concepts labelled 'none' ({sum(ndrop.values())} run-items): P {Pn:.3f} R {Rn:.3f}; random "
        f"thinning of the same size: P mean {sum(rp) / len(rp):.3f}, 95% range [{rp[25]:.3f}, {rp[974]:.3f}]")


if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    sys.stdout.reconfigure(encoding="utf-8")
    read(*(sys.argv[1:2] or ()))
