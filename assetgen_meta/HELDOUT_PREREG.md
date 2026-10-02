# Held-out pre-registration: the winner prompt plus the post-generation levers

Written 2026-10-01, **before any held-out executor run**. At the time of writing no held-out asset list exists, and no
precision or recall of our pipeline has been computed on held-out ground truth (GT). Commit this file and every pinned
file below before starting the run. After the run, `assetgen_meta/heldout_readings.py` prints the readings once; it
refuses to run if any pinned file has changed.

Terms used here:
- **Precision (P)**: of the elements a pipeline lists, the share that are in the GT.
- **Recall (R)**: of the GT entries, the share the pipeline lists.
- **Run**: one executor call per module, over all modules. Three runs are made.
- **Lever**: a code filter applied to the executor's asset lists after generation. No model call.

## 1. What is run, once

| Item | Value |
|---|---|
| Executor | gpt-5-mini, reasoning effort high, 65,536 output-token cap, JSON mode, comment-stripped RTL only, user message `meta_tools.build_user`, no validation retry (the same settings as the tuning runs) |
| Prompt | `assetgen_meta/hand_arms/m7e194es0ism/exec_prompt.txt`, sha12 `0d0def4c6fe3` (of its text, as `run_version` records it) |
| Modules | the 26 files in `RTL_heldout/` (all 26 have GT); 189 GT entries after `eval_assets`' repeat cap (exact, counted this session) |
| Run folders | `assets_heldout26_m7e194es0ism_r0`, `_r1`, `_r2` |
| Call | `mt.run_version(client, "m7e194es0ism", rep, system, mt.rtl_modules("RTL_heldout"), stem="assets_heldout26", parsed_dir="parsed_heldout26")` for rep 0, 1, 2 |
| Closed set | `parsed_heldout26/` (written by `step1/build_heldout_code_map.py`; equal file for file to the held-out copies in `parsed_tuning18/`) |
| Relation maps | `step1/lasset_step1/relation_map_code_heldout/b0e767000ec2_codetags/` (code only: code SITE tags + `code_pairs_v2`) |
| Calls | 78 (3 runs x 26 modules), plus retries |
| Cost estimate | about $2.80 to $3.49 if the system prompt is cached after the first call of a run; $3.36 to $4.06 with no caching. Output tokens are most of it. Estimate only, no API call made (method in section 8). |

Retries. Re-running a run's cell retries only the modules with no parseable answer (`run_version` skips modules already
on disk). Each missing module may be retried up to 3 more times. A module still missing in any run after that is
excluded from **every** row, the LAsset row included, and is listed in the output. Known risk: the two largest held-out
modules (`cpu_cp_fpu`, `cpu_control`) are larger than any tuning input and may hit the output cap.

Nothing in sections 3 to 5 may be changed after the first held-out call is made. The result is reported whatever it is.

## 2. Pinned files

`heldout_readings.read()` recomputes each sha12 and refuses to score if any differs. Kind `bytes` = sha256 of the file
bytes; `text` = sha256 of the text as Python reads it; `dir` = sha256 over every file in the folder, sorted by relative
path (path and bytes).

| File | Kind | sha12 | Role |
|---|---|---|---|
| `assetgen_meta/hand_arms/m7e194es0ism/exec_prompt.txt` | text | `0d0def4c6fe3` | the winner prompt |
| `step1/code_pairs_v2.py` | bytes | `b0e767000ec2` | relationships by code (frozen) |
| `step1/code_site_tags.py` | bytes | `68357a3d3a56` | SITE tags by code |
| `step1/build_heldout_code_map.py` | bytes | `1617930d17d8` | closed set + map builder |
| `assetgen_meta/post_levers.py` | bytes | `30b563e562a3` | the frozen levers and scoring |
| `assetgen_meta/heldout_readings.py` | bytes | `4236de1d347b` | the readings below |
| `assetgen_meta/asset_trace.py` | bytes | `1d8d66f7191b` | trace paths (NONE, BF) |
| `step1/relation_stage.py` | bytes | `53f792235ade` | map merge |
| `assetgen_meta/meta_tools.py` | bytes | `a714b5228cd5` | executor call, majority vote, convention filter |
| `eval_assets.py` | bytes | `9749538c778e` | the scorer |
| `assetgen_meta/gt_overlay.py` | bytes | `f77e1c9967ba` | corrected GT (touches a tuning module only) |
| `step1/structure_stage.py` | bytes | `c28fcead3095` | Context / Path of each occurrence |
| `bahavioral_patterns_of_assets/annotation_pack_elements/occurrence_prompts_v2/rulebook_edits/build_occurrence_notebook_v3b.py` | bytes | `87b8ad02470e` | the profiler's code extract |
| `ground_truth/manual_gt_neorv32.json` | bytes | `e5437438157d` | the GT |
| `ground_truth/lasset_initial.json` | bytes | `647d08cfa971` | LAsset initial lists (no CWE refinement) |
| `parsed_heldout26` | dir | `4f0562c5421d` | held-out closed sets |
| `step1/lasset_step1/relation_map_code_heldout/b0e767000ec2_codetags` | dir | `61a99a10e131` | held-out maps and SITE tags |
| `RTL_heldout` | dir | `7ae9ca1323a0` | held-out RTL |

## 3. The levers (frozen in `post_levers.py`)

- **MV** (majority vote): keep an element listed in at least 2 of the 3 runs.
- **NONE**: drop an element whose trace path is "none": the reasoning quotes none of its RTL lines, and the relation
  map does not confirm its realization label (`asset_trace.py`).
- **BF** (back-fill): add a whole input port the run did not list, when its value reaches, within 2 CARRIES/SOURCES
  steps of the map, an element the same run labelled stores or computes. Never added: clock, reset and clock-enable
  inputs (by relationship type SEQUENCES/RESETS, or by the name pattern `(^|_)(clk|rst|rstn|clkgen)(_|$)`), and
  record-typed ports.
- **GUARD**: drop an internal record field that never appears in an if / when / case condition. GUARD was derived
  from the tuning GT, so it is **overfitted**. It is only ever a secondary row and is never adopted.

A stack name lists the filters in the order they run on each run; `MV+` means the vote is taken last.
Condition source on held-out: the code SITE tags (no LLM profiler).

Stacks scored (all 17): base, NONE, GUARD, BF, NONE+BF, GUARD+BF, NONE+GUARD, NONE+GUARD+BF, MV, MV+NONE, MV+GUARD,
MV+BF, MV+NONE+BF, MV+GUARD+BF, MV+NONE+GUARD, MV+NONE+GUARD+BF, MV+NONE+BF+GUARD.
A stack without MV reports the mean of the 3 runs; an MV stack reports the one voted list.

## 4. Readings

All on the held-out modules present in all 3 runs; strict scorer; original GT (the corrected GT is printed too; on
held-out it is identical, since the overlay only touches `neorv32_cache`). The 95% intervals come from a module
bootstrap: resample the modules with replacement, 10,000 resamples, a fresh `random.Random(0)` per comparison.

Tuning reference values below were measured this session by `python assetgen_meta/heldout_readings.py --tuning`
(15 modules, 111 GT entries per list, exact).

**The external row, printed next to every stack: LAsset's initial JSON lists (`ground_truth/lasset_initial.json`, before
LAsset's CWE refinement), scored on the same modules with the same scorer.** Tuning: P 0.737, R 0.910, 137 emitted
(re-derived this session). Held-out: P 0.734, R 0.862, 222 emitted, as recorded earlier in this project; not re-derived
this session, because no P/R is computed on held-out GT before the run. `read()` recomputes it on the scored modules.

**R1, primary: adopt MV+NONE+BF.** Pass needs both:
1. its precision gain over MV has a 95% interval whose low end is above 0;
2. its recall is at least 0.83.

Reported, not decisive: P minus base, and recall minus MV.
Tuning reference: P 0.394, R 0.901 (TP 100/111). Gain over MV +0.037 [+0.016, +0.058]; recall change +0.027
[+0.000, +0.063]. Falsified if the interval includes 0 or recall is below 0.83.

**R2, secondary: GUARD, against random thinning of equal strength.** "Random thinning" drops, in each run and module,
as many elements as GUARD would drop there, chosen at random from that module's listed elements (1,000 draws, seed 0).
Rows: GUARD, MV+NONE+GUARD+BF, MV+NONE+BF+GUARD. GUARD cannot change the decision. Tuning reference:
- GUARD: P 0.451 vs random 0.362 [0.343, 0.379];
- MV+NONE+GUARD+BF: P 0.495 vs random 0.428 [0.399, 0.456]; gain over MV +0.138 [+0.094, +0.180]; recall 0.829 (92/111);
- MV+NONE+BF+GUARD: P 0.500 vs random 0.424 [0.395, 0.455]; recall 0.847 (94/111).

**R3, each filter alone** (on the unfiltered runs, mean per run):
- NONE: tuning removes 24.0 per run, FP share 0.986. Falsified if the FP share is below 0.90.
- GUARD: tuning removes 78.0 per run, FP share 0.923, recall change -0.054. Falsified as a general rule if its FP share
  is at most (1 - base precision) + 0.05, i.e. no better than removing at random, or if its recall change is below -0.08.
- BF: tuning adds 3.7 per run, TP share 0.818. Falsified if the TP share is below 0.50.

**R4, descriptive, computed after scoring:** internal record fields in a condition, GT vs non-GT.
Tuning: GT fields 23/30; other fields 59/241.

**R5, overlap (leak) checks on R1's gain:** BF with the relationship-type exclusion only (no name pattern); a
convention-neutral score (`meta_tools.convention_filter` on both stacks); convention-matching emissions per run. If
either version moves the gain by more than 0.01, the claim uses the lowest of the three gains. Tuning: +0.036 and
+0.037 vs +0.037; emissions per run [0, 1, 1].

**R6, reported alongside:** base P and R per run; NONE+BF minus base without voting (tuning +0.038 [+0.022, +0.052]);
excluded modules, if any.

**Decision.** R1 passes: MV+NONE+BF is the reported pipeline. R1 fails: the filters do not generalise; report base and
MV, and write the filters up as a tuning-set finding. GUARD rows are reported either way and never adopted.

## 5. Leak note (what is not blind)

Two annotation conventions are known on held-out before the run: clock / reset / clock-enable inputs are never assets,
and transaction-record ports are never assets. The winner prompt states both, and BF's exclusions use both. So the
**absolute** held-out precision of every row, the unfiltered winner included, is not a blind measurement. The clean
test is the **difference** between a stack and its reference on the same runs (R1, R3), where the prompt's conventions
cancel out. R5 measures how much BF's own convention rules move that difference. GUARD's precision and recall on
model output have never been computed on held-out. Its premise has: before this pre-registration, the scratchpad script
`agents5/q2b_heldout.py` measured on the held-out GT, with an RTL detector and no model output, how often GT and non-GT
internal record fields sit in a condition (results in `agents5/guard_result.json`, which judged GUARD overfitted). So
R4 on held-out repeats a known measurement, and the GUARD rows (R2, R3) are blind only as filter results on model output.

## 6. What this breaks, and what would falsify it

- Breaks nothing earlier: every held-out output goes to new folders (`assets_heldout26_*`,
  `assetgen_meta/traces/assets_heldout26/`, `assetgen_meta/heldout_readings.json`). Tuning runs, maps and traces are
  untouched. The edits to `meta_tools.py` and `asset_trace.py` keep their default behaviour (self-tests re-run; the
  winner's 54 stored trace files reproduce byte for byte).
- Falsifiers are in R1 and R3. The measurement to read after the run: R1's interval and recall, then R3's three shares.

## 7. Differences from the earlier plan (`plan_result.json` readings)

- R1 has two pass conditions instead of four; "P at least base + 0.03" and "recall change vs MV at least -0.01" are
  printed but do not decide. Reason: the brief for this step defines R1 by the interval and the recall bar only.
- The plan allowed adopting MV+NONE+GUARD+BF if it reached recall 0.83. Here GUARD is never adopted, because it was
  derived from the tuning GT. It is reported against random thinning instead.
- MV+NONE+BF+GUARD (GUARD after BF) is added as a secondary row.
- The bootstrap uses a fresh `random.Random(0)` per comparison, so the tuning interval for R1 reads [+0.016, +0.058]
  here, against [+0.016, +0.057] in the plan.

## 8. How the cost was estimated (reasoning, not a measurement)

From the earlier pricing script (`agents5/t2_price.json`, no API call): per run about 982,452 input tokens (message
characters of the 26 held-out modules times 0.3232 tokens per character, the ratio of the recorded `ismcap` run: 670,685
tokens over 2,075,005 characters) and 437,329 to 553,726 output tokens (the recorded 18-module output scaled by 26/18,
or by the held-out / tuning RTL size ratio). gpt-5-mini prices: $0.25 per million input tokens, $0.025 cached, $2.00
output. Recomputed this session: $3.36 to $4.06 for 3 runs with no caching; $2.80 to $3.49 with the system prompt
cached after the first call of a run.
