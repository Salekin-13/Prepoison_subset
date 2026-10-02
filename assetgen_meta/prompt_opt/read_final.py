"""Readings for the final version of the prompt-optimization loop (prompt_opt/v1) run on the notebook's executor
(an OpenAI model, effort high, 3 runs on the 18 RTL_data modules; scored on the 15 with a reference). No model call.
The paired baseline is the ist2 prompt on the same executor; without 3 complete runs of it, ist2 on gpt-5-mini, and
the comparison is labelled confounded (prompt and executor both differ).

Written 2026-10-02, before the run. The predictions come from the Claude-executor loop: v1 against v0 (the ist2
generation prompt) on tuning, means of 3 vs 2 runs: P +0.036, R +0.047.

  F0  P / R / F1 per run and mean on the 15 modules; Claude v1 shown as context only
  F1  precision: dP = final - baseline (means). "supported" if >= +0.03; "direction only, within noise" if 0 < dP <
      0.03; "not supported" if <= 0
  F2  recall: dR >= -0.03 "holds", else "fails"
  F3  edits A and B followed: FPs that A and B (as shipped), re-applied as code filters, would still remove, mean per
      run. "followed" if the final version's mean is at most half of the baseline's (the baseline has no such edits)
  F4  edit C: of the 5 cpu interrupt and debug input ports in the reference, how many each run lists, final and baseline
  F5  listed elements whose (first) citation is verified, share per run, final and baseline. The trace reports in the
      notebook count every citation on all 18 modules, so their share differs.
A run counts only when it is complete (every module with a reference has an output).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in ("", "assetgen_meta"):
    if str(ROOT / _p) not in sys.path:
        sys.path.insert(0, str(ROOT / _p))
import eval_assets as ea          # noqa: E402
import fp_diagnosis as fd         # noqa: E402

BASE = "m7e194es0ist2"
CLAUDE = ["assets_opt_v1_r0", "assets_opt_v1_r1", "assets_opt_v1_r2"]
CPU_PORTS = ("msi_i", "mei_i", "mti_i", "firq_i", "dbi_i")
NOISE = 0.03


def _runs(version, reps=(0, 1, 2)):
    """The complete runs of a version."""
    return [f"assets_tuning18_{version}_r{k}" for k in reps if fd.complete(f"assets_tuning18_{version}_r{k}", "tuning")]


def _incomplete(version, reps=(0, 1, 2)):
    return [f"assets_tuning18_{version}_r{k}" for k in reps
            if (ROOT / f"assets_tuning18_{version}_r{k}" / "_nested").exists() and not fd.complete(f"assets_tuning18_{version}_r{k}", "tuning")]


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def summary(runs, mods) -> list[dict]:
    gt = ea.load_refs()["gt"]
    out = []
    for r in runs:
        s = ea.score(ROOT / r, gt, strict=True, only=mods)
        P, R = s["precision"], s["recall"]
        out.append({"run": r, "P": P, "R": R, "F1": 2 * P * R / (P + R) if P + R else 0.0, "emit": s["emit"],
                    "ref": s["tp"] + s["fn"]})
    return out


def read(final: str, base: str | None = None, log=print) -> dict:
    fin = _runs(final)
    for v in (final, base):
        if v and _incomplete(v):
            log(f"   incomplete runs left out: {_incomplete(v)} (re-run the generation cell to fill them)")
    assert fin, f"no complete run of {final} yet: run the generation cell first"
    paired = bool(base) and len(_runs(base)) == 3
    bname = base if paired else BASE
    base_runs = _runs(bname)
    mods = set(fd.modules_for("tuning"))
    res = {"final": final, "base": bname, "paired": paired, "runs": len(fin), "base_runs": len(base_runs)}
    S = {"final": summary(fin, mods), "baseline": summary(base_runs, mods), "claude v1": summary(CLAUDE, mods)}
    refs = {k: sorted({x["ref"] for x in v}) for k, v in S.items()}
    log(f"{final} readings: {len(mods)} modules; reference entries per run {refs['final']} (final), {refs['baseline']} (baseline "
        f"{bname}); complete runs {len(fin)} (final), {len(base_runs)} (baseline)"
        + ("" if paired else "\n   ** baseline on another executor: F1-F3 are CONFOUNDED (prompt and executor both differ) **"))
    for k, rows in S.items():
        log(f"   F0  {k:10s} P {_mean(r['P'] for r in rows):.3f} R {_mean(r['R'] for r in rows):.3f} F1 {_mean(r['F1'] for r in rows):.3f} "
            f"emitted/run {_mean(r['emit'] for r in rows):.1f} | per run P {[round(r['P'], 3) for r in rows]} R {[round(r['R'], 3) for r in rows]}"
            + ("   (other executor: context only)" if k == "claude v1" else ""))
    dP = _mean(r["P"] for r in S["final"]) - _mean(r["P"] for r in S["baseline"])
    dR = _mean(r["R"] for r in S["final"]) - _mean(r["R"] for r in S["baseline"])
    if math.isnan(dP):
        v1 = v2 = "no baseline run: not read"
    else:
        v1 = "supported" if dP >= NOISE else ("direction only, within noise" if dP > 0 else "not supported")
        v2 = "holds" if dR >= -NOISE else "fails"
    log(f"   F1  precision: final - baseline = {dP:+.3f} -> {v1}")
    log(f"   F2  recall:    final - baseline = {dR:+.3f} -> {v2}")
    mcache: dict = {}
    ed = {k: [fd.d6_edits(r, "tuning", mcache) for r in runs] for k, runs in (("final", fin), ("baseline", base_runs))}
    per = {k: _mean(e["A"]["removes_FP"] + e["B"]["removes_FP"] for e in v) for k, v in ed.items()}
    v3 = ("no baseline run: not read" if math.isnan(per["baseline"]) else
          "followed" if per["final"] <= per["baseline"] / 2 else "not followed")
    log(f"   F3  FPs that edits A + B (as shipped) would still remove, mean per run: final {per['final']:.1f} "
        f"({[(e['A']['removes_FP'], e['B']['removes_FP']) for e in ed['final']]} A,B per run), baseline {per['baseline']:.1f} -> {v3}")
    cpu = {}
    for k, runs in (("final", fin), ("baseline", base_runs)):
        cpu[k] = [sum(p in {x[1] for x in ea.load_run(ROOT / r).get("neorv32_cpu", [])} for p in CPU_PORTS) for r in runs]
    log(f"   F4  cpu interrupt and debug ports listed per run (of 5): final {cpu['final']}, baseline {cpu['baseline']}")
    ver = {}
    for k, runs in (("final", fin), ("baseline", base_runs)):
        ver[k] = []
        for r in runs:
            rows, _ = fd.rows_for_run(r, "tuning", mcache)
            ver[k].append(sum(x["status"] == "verified" for x in rows) / max(len(rows), 1))
    log(f"   F5  listed elements with a verified citation, share per run: final {[round(v, 3) for v in ver['final']]}, "
        f"baseline {[round(v, 3) for v in ver['baseline']]}")
    res.update(F0={k: {"P": _mean(r["P"] for r in v), "R": _mean(r["R"] for r in v), "F1": _mean(r["F1"] for r in v)} for k, v in S.items()},
               F1={"dP": dP, "verdict": v1}, F2={"dR": dR, "verdict": v2}, F3={"mean_per_run": per, "verdict": v3}, F4=cpu, F5=ver)
    return res
