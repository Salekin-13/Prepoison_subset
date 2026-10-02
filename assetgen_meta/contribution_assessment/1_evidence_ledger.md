# Evidence ledger: how much the occurrence map and relationship map add to LAsset

All numbers below were re-run in this session. Python was run from `E:/jobs/ff/test/Prepoison_subset`, and every script is in `<session scratchpad>/contrib/` (t1 to t7). Nothing in the repo was written; `PYTHONDONTWRITEBYTECODE=1` was set and the report writers were pointed at the scratchpad. No paid API call was made.

**Scoring setup.** The scorer is `eval_assets.score(strict=True)`, compared against `load_refs()["gt"]` (the manual reference).
- Tuning set: 15 modules, 111 reference entries per list (exact).
- Held-out set: 26 modules, 189 entries (exact).
- Scorer self-test: the reference scored against itself gives P = R = 1.0 (111/111).
- "P" means precision and "R" means recall in every table. Values are exact counts, or means of runs where stated.

## 1. Map in the generator's input (tuning, gpt-5-mini)
Run folders: `assets_tuning18_<v>_r0..2`, all 15/15 modules present. Each row is the mean over runs. The paired deltas use a module bootstrap (`ea.paired`, 10,000 resamples). That bootstrap averages per-module P and R, so its deltas differ slightly from differences of the pooled means.

| arm | input | runs | P | R | emitted per run | runs' P | runs' R |
|---|---|---|---|---|---|---|---|
| ism | RTL only | 3 | 0.344 | 0.847 | 273.3 | .347/.332/.353 | .856/.820/.865 |
| ismr | + map section (LLM-written map) | 3 | 0.353 | 0.778 | 244.7 | .356/.355/.347 | .793/.784/.757 |
| ismc | + map section (code-written map) | 3 | 0.346 | 0.787 | 252.3 | – | .820/.829/.712 |
| ismq | RTL + four questions | 3 | 0.352 | 0.754 | 237.7 | .378/.351/.328 | .793/.775/.694 |
| ismrq | ismq + map section | 3 | 0.360 | 0.697 | 215.0 | .363/.368/.349 | .694/.676/.721 |
| ist | restructured prompt + numbered RTL + map with occurrence IDs, cited | 3 | 0.359 | 0.691 | 213.7 | .361/.363/.353 | .676/.694/.703 |
| ist2 | ist with fixes (traced_inputs_v2) | 3 | 0.343 | 0.733 | 237.3 | .363/.339/.326 | .775/.721/.703 |
| v2 | RTL only | 3 | 0.251 | 0.925 | 412.7 | | |
| v2p3c1 | LLM-parsed annotations (not the code map) | 3 | 0.240 | 0.847 | 393.3 | | |

Paired deltas (an asterisk means the 95% interval excludes 0):

| comparison | change in P [95% CI] | change in R [95% CI] |
|---|---|---|
| ismr − ism | +0.015 [−0.011, +0.043] | −0.028 [−0.104, +0.046] |
| ismc − ism | +0.013 [−0.009, +0.038] | −0.029 [−0.100, +0.046] |
| ismrq − ismq | +0.019 [−0.011, +0.053] | −0.032 [−0.095, +0.032] |
| ist − ism | −0.020 [−0.115, +0.061] | −0.138 [−0.243, −0.031]* |
| ist2 − ism | −0.019 [−0.078, +0.032] | −0.070 [−0.158, +0.016] |
| v2p3c1 − v2 | −0.038 [−0.071, −0.005]* | −0.057 [−0.104, −0.011]* |

F1 deltas: ismr +0.002, ismc −0.002, ist −0.057, ist2 −0.038, v2p3c1 −0.044*.

ist and ist2 change the whole prompt as well as the input, so they do not isolate the map.

## 2. Held-out pre-registered reading
Source: `assetgen_meta/heldout_readings.json`. I rebuilt it in memory with `post_levers.Levers` on `assets_heldout26_m7e194es0ism_r0..2`.
- Pinned files: 18 of 18 unchanged (`verify_prereg`).
- `post_levers.selftest`: PASS. All 17 tuning stacks and the LAsset row reproduce to 3 decimals.

| stack | tuning P / R (111) | held-out P / R (189) | held-out emitted | held-out F1 |
|---|---|---|---|---|
| base (mean of 3 runs) | 0.344 / 0.847 | 0.352 / 0.852 | 458.0 | 0.498 |
| MV (majority vote) | 0.357 / 0.874 | 0.350 / 0.857 | 463 | 0.497 |
| **MV+NONE+BF** (adopted) | 0.394 / 0.901 | **0.399 / 0.884** (167 of 189 found) | 419 | 0.549 |
| GUARD | 0.451 / 0.793 | 0.446 / 0.801 | 340.0 | |
| MV+NONE+BF+GUARD (secondary, overfitted) | 0.500 / 0.847 | 0.497 / 0.836 | 318 | 0.623 |

Intervals (module bootstrap, 10,000 resamples, seed 0, all re-derived):

| comparison | change in P [95% CI] | change in R [95% CI] |
|---|---|---|
| R1 held-out: MV+NONE+BF − MV | +0.049 [+0.025, +0.080] | +0.026 [−0.021, +0.075] |
| R1 tuning: MV+NONE+BF − MV | +0.037 [+0.016, +0.058] | +0.027 [+0.000, +0.063] |
| held-out NONE+BF − base | +0.042 [+0.024, +0.063] | +0.023 [−0.005, +0.056] |
| held-out MV − base | −0.002 [−0.018, +0.013] | +0.005 [−0.021, +0.031] |

- R1 passes as pre-registered: the precision interval is above 0 and recall is at least 0.83.
- **What each lever does on its own (held-out, per run).** NONE removes 46.3 elements, 95% of them false positives. BF adds 9.0, 74% of them correct. GUARD removes 118.0, 91.8% of them false positives. None was falsified.
- **GUARD against random removal (re-derived).** Removing the same number of elements at random gives P 0.393 [0.383, 0.404], against GUARD's 0.446 (0 of 1,000 random draws reached it). For MV+NONE+BF+GUARD, random gives 0.460 [0.441, 0.480] against 0.497.
- **LAsset row on the same held-out modules** (`lasset_initial.json`): P 0.734, R 0.862, 222 emitted, 163 found.
- **R5 leak check (read from the JSON only, not re-derived).** Using only the relationship-type exclusion in BF gives +0.048. The convention-neutral score gives +0.049. Zero emissions matched a convention, and the largest move was 0.001.

**What NONE and BF read from the map** (`post_levers.py`, `asset_trace.py`):
- **NONE** drops an element only when its trace path is "none". That happens when the element is not in the map under its entity, or when both of these hold:
  - the reasoning quotes none of the element's lines (matched through the map's occurrence lines), and
  - the map does not confirm the realization label. "stores" needs storage = edge; "exit port" needs mode = out; "sets" needs mode = in plus a driving record; "computes" needs a receiving record.
- **BF** adds whole input ports that the run did not list. A port qualifies when its value reaches an element the run labelled stores or computes within 2 CARRIES/SOURCES hops in the map. These are excluded: ports with SEQUENCES/RESETS records, clock/reset/enable names, and record-typed ports. The labels come from the generator itself; the map does not confirm them.
- **GUARD** reads the code SITE condition tags. MV does not use the map at all.

**How NONE's removals break down (new run, in memory, t2c/t2d).**

| | per run: "in map, unquoted, unconfirmed" | per run: "not in map" | P: base → names-only check → full NONE (mean of runs) |
|---|---|---|---|
| held-out | 28.3 (26.0 wrong) | 18.0 (all wrong; mostly indexed names such as `sysinfo(0)`) | 0.352 → 0.366 → 0.386 |
| tuning | 21.3 (21.0 wrong) | 2.7 (all wrong) | 0.344 → 0.347 → 0.376 |

So on held-out, about 40% of NONE's precision gain could come from a plain name check against the parsed element list, which any parser provides. The rest needs the map's quote and confirmation layer.

## 3. LAsset lists under the same strict scorer
Scored with t3 and t3b.

| list | tuning P / R (emitted) | held-out P / R (emitted) |
|---|---|---|
| `ground_truth/lasset_initial.json` (spec+RTL, initial) | 0.737 / 0.910 (137) | 0.734 / 0.862 (222) |
| `ground_truth/lasset_refined.json` | 0.800 / 0.901 (125) | 0.791 / 0.862 (206) |
| `LAsset_initial_results/asset_list_neorv32_initial.json` (RTL-only, initial) | **0.680 / 0.748 (122)** | **0.730 / 0.757 (196)** |
| `...initial (1).json` | 0.737 / 0.910 (137) | 0.734 / 0.862 (222) |
| SA-EDI per-IP RTL-only initial (my reading of the files) | 0.656 / 0.721 (122) | 0.699 / 0.725 (196) |
| SA-EDI RTL-only refined (same as final) | 0.705 / 0.712 (112) | 0.753 / 0.725 (182) |
| SA-EDI Spec+RTL initial / final | 0.708 / 0.874 (137); 0.768 / 0.865 (125) | 0.707 / 0.831; 0.762 / 0.831 |

- **What the two LAsset_initial_results files are.** The plain file is byte-identical (md5) to `LAsset-Security-Assets/SoC/RTL/asset_list_neorv32_initial.json`. The ' (1)' file is identical to `SoC/Spec.+RTL/asset_list_neorv32_initial.json`, which is the source of `lasset_initial.json`.
- **Where the two old RTL-only figures come from.**
  - 0.680 / 0.748 with 122 listed: the combined JSON. Names are bare, as in `Asset RTL: addr_i`.
  - 0.653 / 0.712 with 121 listed: memory note `lasset-replication-pipeline.md` line 71 (2026-09-19). It was scored from the per-IP files in github.com/Ajoad/SA-EDI-Asset-Objects. I rebuilt those files from the git pack kept in the scratchpad. Their names are entity-qualified, use sub-instance paths and join several names with commas, for example `neorv32_cache_memory_inst.addr_i`.
  - Both sources hold the same number of items per module, so the gap is about how names are written. The same note's Spec+RTL numbers reproduce exactly from SA-EDI (0.708 / 0.874 / 137 and 0.768 / 0.865 / 125), which supports this explanation.
  - The exact 0.653 / 0.712 / 121 does **not** reproduce: my reading gives 0.656 / 0.721 / 122, and the old script no longer exists.
  - The combined-JSON row is the one more favourable to LAsset.
- `read_ist2._lasset_rtl_only` gives 0.680 / 0.748 / 122 (tuning) and 0.730 / 0.757 / 196 (held-out).
- Some LAsset items name several elements in one entry. In the RTL-only list this affects 11 of 122 items on tuning and 6 of 196 on held-out. Strict scoring counts each such entry as one item.

## 4. Citation checks
**`trace_check` re-run** (self-test PASS on 13 cases; written with `write=False`). Unit: one cited reference row, pooled over 3 runs.

| arm | verified (now) | on disk `_summary.json` |
|---|---|---|
| ist | 687 / 846 = 0.812 | 799 / 846 = 0.944 |
| ist2 | 778 / 951 = 0.818 | 775 / 951 = 0.815 |

- ist2 therefore fails its own pre-registered bar of at least 90% verified.
- On ist2, rows whose element is a reference entry are verified 256/272 times; rows whose element is a false positive, 453/601. Here TP/FP is assigned by element name, so these two counts are approximate.

**`fp_diagnosis` D1 re-run** (self-test PASS on 20 checks). Unit: one listed element, using its citation status.

| run set | correct elements verified | false positives verified |
|---|---|---|
| gpt-5-mini ist2 | 236 / 244 = 0.967 | 390 / 468 = 0.833 |
| Claude final (`assets_opt_v1`) | 308 / 311 = 0.990 | 496 / 527 = 0.941 |
| held-out Claude v1 | 176 / 176 = 1.0 | 334 / 359 = 0.930 |

A verified citation shows the cited evidence is real. It does not show the element is an asset.

**84.8% verbatim figure.** Source: `RELATION_EXPERIMENTS_LOG.md` line 242. **Re-derived** by re-running `scratchpad/agents/check_g.py` (self-test PASS): 1,681 of 1,983 `<=` assignments written in 1,112 reasonings (arms c, ism and ismr, 9 runs) reproduce an RTL statement verbatim.
- It measures free-text reasoning; for c and ism, no map was in the input.
- It does not separate correct elements from false positives: a quote of 20 or more characters appears for 739/797 = 92.7% of correct elements and 1,333/1,442 = 92.4% of false positives. A quote on the element's own line: 76.0% against 70.7%.

## 5. How accurate the map is
- **Relationship records** (`step1/code_pairs_v2.py`, sha `b0e767000ec2`), re-scored with t5 (scorer self-test PASS). The gold set is 120 sampled occurrences with 212 gold records, from the tuning modules.
  - Typed precision 0.988 [0.969, 1.0] and typed recall 0.988 [0.969, 1.0], weighted by stratum. Unweighted: 210 correct, 2 wrong, 2 missed. Target-only: 1.0 / 1.0.
  - The earlier code scored 0.914 / 0.933.
  - Caveat: gpt-6-astra wrote the gold (two passes agreed on 117/120), not a human. These modules were tuning modules, though not the development keys. The held-out map has **no** accuracy measurement.
- **Occurrence-to-line integrity (self-tests run).** `asset_trace`: 12 hand-read lines, and 5,760 of 5,760 occurrences sit on their stripped line. `traced_inputs`: 5,972/5,972 tuning and 11,997/11,997 held-out occurrences sit on their numbered line. These test consistency with the source lines, not whether the relationships are right.
- **Known gap.** Some internal record fields have their own storage marked as not "edge", even though the whole record is assigned on a clock edge. I counted 12 of 271 such fields on tuning and 45 of 541 on held-out, using the extension rule in `asset_trace`. NONE's confirmation does not apply that rule.
- The LLM occurrence-profile reports (`profile_check_report*.txt`) are rule-consistency checks, not accuracy, and I did not re-run them.
- No "relations right of 20" round exists in `step1/`, `bahavioral_patterns_of_assets/` or the `assetgen_meta/` .md files.

## 6. Fault reporter and FP diagnosis
Re-run code-only into the scratchpad; both self-tests PASS. Every number below equals the on-disk `facts.json` exactly.

| quantity | gpt-5-mini ist2 (712 listed, 244 correct) | Claude final (838 listed, 311 correct) |
|---|---|---|
| relationship-class tokens seen on both correct and wrong elements | 21 / 21 | 21 / 21 |
| false positives with exactly a correct element's profile | 0.194 | 0.264 |
| AUC from classes: in-sample / leave one module out | 0.750 / 0.615 | 0.762 / 0.629 |
| AUC from record types: in-sample / leave one module out | 0.813 / 0.641 | 0.808 / 0.661 |
| all clean rules together, in-sample | 41 rules: P 0.343 → 0.654, R 0.733 → 0.408 | 31 rules: P 0.371 → 0.563, R 0.934 → 0.592 |
| same rules on held-out (535 listed, 176 correct) | – | P 0.329 → 0.478, R 0.931 → 0.640, F1 0.486 → 0.548 (227 of 359 false positives and 55 of 176 correct elements dropped) |
| false positives in concepts with no reference element (D5) | 264 / 468 = 0.564 | 364 / 527 = 0.691 |

Held-out Claude v1 D5: 239 / 359 = 0.666. AUC 0.5 means chance.

## 7. Our numbers against LAsset, like for like
"Like for like" means the RTL-only, initial list: no spec input and no refinement stage.

| set | row | P | R | F1 | emitted |
|---|---|---|---|---|---|
| tuning | LAsset RTL-only initial | 0.680 | 0.748 | 0.712 | 122 |
| tuning | LAsset spec+RTL initial / refined | 0.737 / 0.800 | 0.910 / 0.901 | 0.815 / 0.847 | 137 / 125 |
| tuning | ours, base (gpt-5-mini ism) | 0.344 | 0.847 | 0.489 | 273.3 |
| tuning | ours, MV+NONE+BF (fitted on this set) | 0.394 | 0.901 | 0.548 | 254 |
| tuning | ours, Claude executor `opt_v1` (3 runs, different model) | 0.371 | 0.934 | 0.531 | 279.3 |
| held-out | LAsset RTL-only initial | 0.730 | 0.757 | 0.743 | 196 |
| held-out | LAsset RTL-only final (SA-EDI) | 0.753 | 0.725 | 0.739 | 182 |
| held-out | LAsset spec+RTL initial / refined | 0.734 / 0.791 | 0.862 / 0.862 | 0.793 / 0.825 | 222 / 206 |
| held-out | ours, base | 0.352 | 0.852 | 0.498 | 458 |
| held-out | **ours, MV+NONE+BF (pre-registered)** | **0.399** | **0.884** | 0.549 | 419 |
| held-out | ours, MV+NONE+BF+GUARD (secondary) | 0.497 | 0.836 | 0.623 | 318 |
| held-out | ours, Claude `opt_heldout_v1` (1 run) | 0.329 | 0.931 | 0.486 | 535 |

Bootstrap of the difference, ours (MV+NONE+BF) minus LAsset (t7b; 10,000 module resamples, seed 0):

| set | against | change in P [95% CI] | change in R [95% CI] | found only by ours / only by LAsset |
|---|---|---|---|---|
| held-out | RTL-only initial | −0.331 [−0.405, −0.242] | +0.127 [+0.064, +0.186] | 36 / 12 |
| held-out | spec+RTL initial | −0.336 [−0.393, −0.263] | +0.021 [−0.044, +0.085] | 22 / 18 |
| tuning | RTL-only initial | −0.287 [−0.388, −0.179] | +0.153 [+0.057, +0.268] | 25 / 8 |

## Reading of the evidence (my reasoning, not a measurement)
- **As generator input, the map adds nothing measurable** to precision or recall. It is a null at best and costs recall in the restructured prompts.
- **Map-based filtering after generation is real but small.** It adds about +0.05 precision on held-out. That gain is pre-registered and its interval excludes zero. The recall gain of about +0.03 is not significant. About 40% of the NONE part of the gain could come from a plain name check.
- **The recall lead over LAsset RTL-only (+0.127) mostly comes from the base prompt.** The base alone is +0.095 (0.852 against 0.757), and it lists 2.3 times as many items. Precision stays about 0.33 below LAsset.
- **The map's clearest unique value is auditability and diagnosis**, not accuracy: checked citations, the trace from quoted line to occurrence to record, and the false-positive diagnosis. Its main diagnostic finding is negative: correct and wrong elements share their relationship profiles, and AUC is only about 0.62–0.66 on a module the rules were not fitted on.

## Discrepancies
1. ist citation verification: the on-disk 0.944 (also the "ist: 94%" in the `read_ist2` docstring) against 0.812 with today's `trace_check`. The likely cause is the later rule that refuses citations of transport record ports made through their fields; the code comment names 98 of 112 such references in ist. For ist2, run r1 now gives 250 against 255 on disk and r2 gives 278 against 270; I did not find the cause.
2. ist2 misses its pre-registered R1 bar of at least 90% verified (0.818).
3. Old LAsset RTL-only figures: explained in section 3. The exact 0.653 / 0.712 / 121 does not reproduce.
4. The memory note's spec+RTL initial (0.708 / 0.874) and today's `lasset_initial.json` (0.737 / 0.910) come from different source formats of the same lists.
5. ABLATION_LOG_V2's v2p3c1 row (emitted 375.7, P 0.249, R 0.848) and v2 row (P 0.250, R 0.930) against today's 393.3 / 0.240 / 0.847 and 0.251 / 0.925. The log predates later changes to the reference and the scorer.
6. The relation log compared ismc on 9 modules and 70 entries; ismc is now complete on 15 modules.
7. Claude final D5 counts 394 concepts now against 395 on disk; the false-positive count (364) is the same.
8. `LAsset-Security-Assets` `RTL/refined.json` will not parse (a trailing comma), and the `final` files use another format. For those rows I used SA-EDI.

## Not re-derived
- The exact 0.653 / 0.712 / 121 LAsset row.
- The R5 leak-check numbers (read from the JSON only).
- The blind trace audit (30/30), the LLM-writer runs (E0/E3) of the bake-off, and the gold set itself.
- The relation-log claim that ismr's input carried line numbers no model could see.
- The occurrence-profile consistency reports.
- The fault-reporter LLM part (never run; the facts files say "none (code only)").
- No "relations right of 20" round was found.