"""Score the blind analysts' results against the ground truth (original and corrected references), per module, primary
only and primary+secondary; validate their citations against the relation map; compare with the winner's per-module
means. Writes engineer_scores.json."""
import json, sys, os
from collections import Counter
from pathlib import Path
ROOT = Path("E:/jobs/ff/test/Prepoison_subset"); os.chdir(ROOT)
for p in ("", "assetgen_meta", "step1"): sys.path.insert(0, str(ROOT / p))
sys.stdout.reconfigure(encoding="utf-8")
import eval_assets as ea, rel_view as rv, gt_overlay
HERE = Path(__file__).parent; RES = HERE / "results"
MODS = ["hwspinlock", "wdt", "cpu_cp_muldiv", "cache", "sys", "debug_dtm", "spi"]
gt0 = ea.load_refs()["gt"]; gt1 = gt_overlay.corrected(gt0)
W = "m7e194es0ism"
wsc = [ea.score(Path(f"assets_tuning18_{W}_r{k}"), gt0, strict=True)["per_module"] for k in range(3)]


def score(names, ref):
    """Consumed matching by exact name, like eval_assets.score (strict)."""
    used, hit = set(), []
    preds = list(names)
    for rn, _o in ref:
        for i, p in enumerate(preds):
            if i not in used and p == rn:
                used.add(i); hit.append(rn); break
    fp = [p for i, p in enumerate(preds) if i not in used]
    fn = [rn for rn, _o in ref if rn not in hit or hit.count(rn) < sum(1 for x, _ in ref if x == rn)]
    return hit, fp, sorted(set(fn))


out = {}; tot = Counter()
for m in MODS:
    f = RES / f"{m}.json"
    if not f.exists():
        print(f"{m}: NO RESULT"); continue
    r = json.loads(f.read_text(encoding="utf-8"))
    mod = "neorv32_" + m
    d = json.loads(rv.map_path(mod, rv.CODE_MAP_DIR).read_text(encoding="utf-8"))
    occ = {(e["entity"], e["name"]): {o["id"] for o in e["occurrences"]} for a in ("ports", "signals") for e in d[a]}
    names_all = {n for _e, n in occ}
    prim = r.get("primary", []); sec = r.get("secondary", [])
    pn = [x["element"] for x in prim]; sn = [x["element"] for x in sec]
    valid = sum(1 for x in prim if any(set(x.get("occ") or []) <= occ.get((e, x["element"]), set()) and x.get("occ") for e in {en for en, n in occ if n == x["element"]}))
    inmap = sum(1 for n in pn if n in names_all)
    row = {}
    for tag, ref in (("original", gt0[mod]), ("corrected", gt1[mod])):
        hit, fp, fn = score(pn, ref)
        hit2, fp2, fn2 = score(pn + sn, ref)
        row[tag] = {"primary": {"tp": len(hit), "fp": len(fp), "fn": len(fn), "P": round(len(hit) / max(len(pn), 1), 3), "R": round(len(hit) / max(len(ref), 1), 3), "fp_names": fp, "fn_names": fn},
                    "primary+secondary": {"tp": len(hit2), "fp": len(fp2), "R": round(len(hit2) / max(len(ref), 1), 3), "P": round(len(hit2) / max(len(pn) + len(sn), 1), 3)}}
    wtp = sum(s[mod]["tp"] for s in wsc) / 3; wfp = sum(len(s[mod]["fp"]) for s in wsc) / 3
    row["winner"] = {"P": round(wtp / (wtp + wfp), 3) if wtp + wfp else 0, "R": round(wtp / len(gt0[mod]), 3), "tp": round(wtp, 1), "fp": round(wfp, 1)}
    row["citations"] = {"primary": len(prim), "in_map": inmap, "occ_ids_valid": valid, "secondary": len(sec),
                        "conceptual_assets": len(r.get("conceptual_assets", [])), "hypotheses": len(r.get("hypotheses", []))}
    row["roles"] = dict(Counter(x.get("role") for x in prim))
    row["gt_roles"] = {n: [x.get("role") for x in prim if x["element"] == n] for n, _o in gt0[mod]}
    row["sec_gt"] = [x["element"] for x in sec if x["element"] in {n for n, _o in gt0[mod]}]
    out[m] = row
    o = row["original"]["primary"]
    tot["tp"] += o["tp"]; tot["fp"] += o["fp"]; tot["gt"] += len(gt0[mod]); tot["wtp"] += wtp; tot["wfp"] += wfp
    print(f"{m:14s} GT {len(gt0[mod]):2d} | engineer primary P {o['P']:.2f} R {o['R']:.2f} (tp {o['tp']}, fp {o['fp']}) "
          f"| +secondary R {row['original']['primary+secondary']['R']:.2f} | winner P {row['winner']['P']:.2f} R {row['winner']['R']:.2f} "
          f"| corrected-ref R {row['corrected']['primary']['R']:.2f} | citations valid {valid}/{len(prim)}")
    print(f"   missed: {o['fn_names']}   GT via secondary only: {row['sec_gt']}")
    print(f"   false positives: {o['fp_names'][:14]}")
if tot["gt"]:
    print(f"\nALL 7: engineer primary P {tot['tp'] / max(tot['tp'] + tot['fp'], 1):.3f} R {tot['tp'] / tot['gt']:.3f} (tp {tot['tp']}, fp {tot['fp']}, GT {tot['gt']}) | "
          f"winner P {tot['wtp'] / (tot['wtp'] + tot['wfp']):.3f} R {tot['wtp'] / tot['gt']:.3f}")
(HERE / "engineer_scores.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
