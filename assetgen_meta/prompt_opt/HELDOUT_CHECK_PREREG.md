# Held-out check of the prompt-optimization loop: pre-registration

Written 2026-10-02, **before any held-out run of a loop version**. No held-out asset list from v0 or v1 exists at the
time of writing (`assets_opt_heldout*` folders: none). The readings are printed once, by
`assetgen_meta/prompt_opt/heldout_check.py`, which refuses to run if a pinned file below has changed. Nothing in
sections 2 to 4 may be changed after the first held-out executor call. The result is reported whatever it is.

Not committed to git: the user's rule is to commit only when asked. The sha pins below stand in for the commit.

Terms:
- Precision (P): of the elements a version lists, the share that are in the reference.
- Recall (R): of the reference entries, the share the version lists.
- F1: their harmonic mean (the balance of the two).
- Noise: on the tuning set, two runs of the same version differ by 0.011 (v1) to 0.027 (v0) in F1.
  ASSET_DEFINITION.md section 5: a change smaller than 0.03 is not a result.

## 1. Why this check, and what it is not

The loop stopped by its rule: iterations 2 and 3 both made no prompt change (F1 gain 0). v1 is the final version. On
the tuning set (2 runs each), v1 against v0: P 0.372 vs 0.335, R 0.941 vs 0.887, F1 0.533 vs 0.486. The precision
gain is the robust part (false positives about 195 -> 171 and 182); 8 of v1 r0's 9 new hits were in cpu, where v0 r1
already had them. This check asks whether the precision gain carries to modules the loop never saw.

- Executor: Claude agents, not gpt-5-mini. The held-out readings of the notebook pipeline
  (`assetgen_meta/HELDOUT_PREREG.md`, gpt-5-mini, prompt m7e194es0ism) are a different executor and a different prompt.
  They are shown as context, never as a like-for-like comparison.
- v0 is run on held-out too, with the same executor, so that H2 is a paired difference. This is the only clean way to
  attribute a held-out difference to the loop's edits.

## 2. What is run, once

| Item | Value |
|---|---|
| Versions | v1 (final; prompt sha12 `802ee9a90d41` as `opt_tools.build` records it) and v0 (baseline; `e5fe4918c22b`) |
| Executor | one Claude agent per module, `assetgen_meta/prompt_opt/opt_exec.js` with `split: "heldout"`; same task text as every tuning run; blindness audit `blind_agent/audit.py ... executor` |
| Modules | the 26 files in `RTL_heldout/`; 189 reference entries (counted in this session) |
| Inputs | `assetgen_meta/traced_inputs_v2/heldout/<module>.txt` (numbered RTL + map + flow graph) |
| Runs | one per version: `assets_opt_heldout_v1_r0`, `assets_opt_heldout_v0_r0` |

Missing outputs. A module whose executor writes no output is retried up to 2 times. A module still missing in either
version is excluded from **both** versions' rows and listed. Known risk: `cpu_control` (384 KB) and `cpu_cp_fpu`
(416 KB) are larger than any tuning input (largest: bus, 289 KB).

An executor that fails the blindness audit is re-run once; if it fails again, that module is excluded from both rows.

## 3. Readings (printed by `heldout_check.py`)

- **H1.** v1 held-out P, R, F1 (strict scorer, one run, Claude executor). Descriptive.
- **H2.** v1 minus v0 on held-out, paired. Predictions, from the tuning result:
  - P2a: dP > 0. Verdict "supported" if dP >= +0.03, "direction only, within noise" if 0 < dP < 0.03,
    "not supported" if dP <= 0.
  - P2b: dR >= -0.03 ("holds" / "fails").
  - What would falsify the loop's precision gain: dP <= 0.
- **H3.** Evaluation-layer row R1a (`eval_layer.py`, self-test PASS on four tuning runs) applied to v1's held-out
  output: false positives and true positives removed, P/R/F1 after, against random thinning of the same number of
  entries (2000 draws, seed 0). Verdict "generalizes" if it removes no true positive and fewer than 5% of random draws
  reach its precision; otherwise "tuning fit" (R1a stays an in-sample row only).
- **H4.** Descriptive: per-module table, false-negative placement and citation statuses for both versions
  (`v<i>/heldout_eval_r0.md`).
- **Context rows** (other executor or other inputs, never like-for-like):
  - gpt-5-mini with prompt m7e194es0ism, 3 runs, no levers, re-scored by `heldout_check.py` on the same modules
    (in this session, on all 26: P 0.341 / 0.350 / 0.365, R 0.852 / 0.868 / 0.836).
  - LAsset initial, RTL-only 0.730 / 0.757 and spec + RTL 0.734 / 0.862 (from ASSET_DEFINITION.md sections 4 and 6;
    not re-derived here).

## 4. Pinned files

| File | Kind | sha12 |
|---|---|---|
| `assetgen_meta/prompt_opt/v1/exec_prompt.txt` | bytes | `36ad1d44c61d` |
| `assetgen_meta/prompt_opt/v0/exec_prompt.txt` | bytes | `926c3f0cbccc` |
| `assetgen_meta/prompt_opt/opt_exec.js` | bytes | `89e379469dca` |
| `assetgen_meta/prompt_opt/opt_tools.py` | bytes | `2f1bb7278d82` |
| `assetgen_meta/prompt_opt/eval_layer.py` | bytes | `93d8900a0939` |
| `eval_assets.py` | bytes | `9749538c778e` |
| `ground_truth/manual_gt_neorv32.json` | bytes | `e5437438157d` |
| `assetgen_meta/traced_inputs_v2/heldout` | dir | `1dd19f332725` |
| `RTL_heldout` | dir | `7ae9ca1323a0` |
| `assetgen_meta/prompt_opt/heldout_check.py` | bytes | `f9fbf30f412c` |

(The exec-prompt rows hash the file bytes; `802ee9a90d41` / `e5fe4918c22b` are the same prompts hashed as
`opt_tools.build` records them. `eval_assets.py`, the reference and `RTL_heldout` match the pins of
`assetgen_meta/HELDOUT_PREREG.md`.)
