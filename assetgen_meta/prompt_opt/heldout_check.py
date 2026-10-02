"""The one held-out check of the prompt-optimization loop. Pre-registration: HELDOUT_CHECK_PREREG.md (same folder),
written before any held-out run of a loop version. This script refuses to read if a pinned file has changed.

    python assetgen_meta/prompt_opt/heldout_check.py            readings H1-H4 (after the runs)
    python assetgen_meta/prompt_opt/heldout_check.py --pins     print the current sha12 of every pinned file
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in ("", "assetgen_meta", "assetgen_meta/prompt_opt"):
    sys.path.insert(0, str(ROOT / _p))
import eval_assets as ea                     # noqa: E402
from heldout_readings import sha12_of        # noqa: E402

PREREG = HERE / "HELDOUT_CHECK_PREREG.md"
PINNED = [("assetgen_meta/prompt_opt/v1/exec_prompt.txt", "bytes"), ("assetgen_meta/prompt_opt/v0/exec_prompt.txt", "bytes"),
          ("assetgen_meta/prompt_opt/opt_exec.js", "bytes"), ("assetgen_meta/prompt_opt/opt_tools.py", "bytes"),
          ("assetgen_meta/prompt_opt/eval_layer.py", "bytes"), ("eval_assets.py", "bytes"),
          ("ground_truth/manual_gt_neorv32.json", "bytes"), ("assetgen_meta/traced_inputs_v2/heldout", "dir"),
          ("RTL_heldout", "dir")]
NOISE = 0.03                    # ASSET_DEFINITION.md section 5: a change smaller than this is not a result
RUNS = {"v1": "assets_opt_heldout_v1_r0", "v0": "assets_opt_heldout_v0_r0"}
ISM = [f"assets_heldout26_m7e194es0ism_r{k}" for k in range(3)]


def pins_now():
    return [(rel, kind, sha12_of(rel, kind)) for rel, kind in PINNED]


def verify():
    table = re.findall(r"^\|\s*`([^`]+)`\s*\|\s*(bytes|text|dir)\s*\|\s*`([0-9a-f]{12})`\s*\|",
                       PREREG.read_text(encoding="utf-8"), re.M)
    bad = [(rel, sha, sha12_of(rel, kind)) for rel, kind, sha in table if sha12_of(rel, kind) != sha]
    if len(table) != len(PINNED + [("heldout_check", "")]) or bad:
        raise SystemExit(f"pinned files changed or table incomplete ({len(table)} rows): {bad}")


def prf(s):
    P, R = s["precision"], s["recall"]
    return round(P, 3), round(R, 3), round(2 * P * R / (P + R) if P + R else 0.0, 3)


def readings(log=print):
    import opt_tools as OT
    import eval_layer as EL
    verify()
    gt = ea.load_refs()["gt"]
    mods = OT.modules("heldout")
    for v in RUNS:
        OT.flatten_run(v, 0, "heldout")
    have = {v: {f.stem for f in (ROOT / d / "_nested").glob("*.json")} for v, d in RUNS.items()}
    excluded = sorted(set(mods) - (have["v1"] & have["v0"]))
    use = set(mods) - set(excluded)
    nref = sum(len(gt[m]) for m in use)
    log(f"modules {len(use)} of {len(mods)} (excluded, no output in a run: {excluded}); reference entries {nref}")
    sc = {v: ea.score(ROOT / d, gt, strict=True, only=use) for v, d in RUNS.items()}
    out = {"excluded": excluded, "modules": len(use), "reference_entries": nref}
    # H1
    out["H1_v1"] = dict(zip(("P", "R", "F1"), prf(sc["v1"])), emitted=sc["v1"]["emit"])
    log(f"H1 v1 held-out (Claude executor, 1 run): P {out['H1_v1']['P']} R {out['H1_v1']['R']} F1 {out['H1_v1']['F1']}, "
        f"{out['H1_v1']['emitted']} listed")
    # H2
    p1, p0 = prf(sc["v1"]), prf(sc["v0"])
    d = {"dP": round(p1[0] - p0[0], 3), "dR": round(p1[1] - p0[1], 3), "dF1": round(p1[2] - p0[2], 3)}
    verdict_p = "supported" if d["dP"] >= NOISE else ("direction only, within noise" if d["dP"] > 0 else "not supported")
    verdict_r = "holds" if d["dR"] >= -NOISE else "fails"
    out["H2"] = dict(v0=dict(zip(("P", "R", "F1"), p0)), **d, precision_prediction=verdict_p, recall_prediction=verdict_r)
    log(f"H2 v0 held-out: P {p0[0]} R {p0[1]} F1 {p0[2]} | v1 - v0: dP {d['dP']:+} dR {d['dR']:+} dF1 {d['dF1']:+} "
        f"| P prediction: {verdict_p}; R prediction: {verdict_r}")
    # H3
    r1a = EL.apply(ROOT / RUNS["v1"], "heldout", only=use)
    gen = r1a["removed_tp"] == 0 and r1a["thinning_share_ge"] < 0.05
    out["H3_R1a"] = dict(r1a, verdict="generalizes" if gen else "tuning fit")
    log(f"H3 R1a on v1 held-out: removes FP {r1a['removed_fp']} TP {r1a['removed_tp']} -> {r1a['after']}; random thinning "
        f"mean P {r1a['thinning_mean_P']}, share >= R1a {r1a['thinning_share_ge']} -> {out['H3_R1a']['verdict']}")
    # H4 (descriptive) and context rows
    for v in RUNS:
        OT.evaluate(v, 0, None, log=lambda *a: None, split="heldout")
    ism = [prf(ea.score(ROOT / r, gt, strict=True, only=use)) for r in ISM if (ROOT / r).exists()]
    if ism:
        out["context_ism_gpt5mini_plain_mean"] = tuple(round(sum(x[i] for x in ism) / len(ism), 3) for i in range(3))
        log(f"context, other executor (gpt-5-mini, prompt m7e194es0ism, {len(ism)} runs, no levers): mean P/R/F1 "
            f"{out['context_ism_gpt5mini_plain_mean']}")
    (HERE / "heldout_check_result.json").write_text(json.dumps(out, indent=1, default=list), encoding="utf-8")
    return out


if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    sys.stdout.reconfigure(encoding="utf-8")
    if "--pins" in sys.argv:
        for rel, kind, sha in pins_now() + [("assetgen_meta/prompt_opt/heldout_check.py", "bytes",
                                             sha12_of("assetgen_meta/prompt_opt/heldout_check.py", "bytes"))]:
            print(f"| `{rel}` | {kind} | `{sha}` |")
    else:
        readings()
