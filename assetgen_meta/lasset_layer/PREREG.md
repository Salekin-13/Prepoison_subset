# The evidence layer on LAsset's own lists: pre-registration (design v2)

Written 2026-10-02. **No held-out trace, filter, model or coverage result has been computed** by anyone (the design
reviewers were barred from held-out, and so was every script run so far). The readings are produced by
`assetgen_meta/lasset_layer.py` (`read_tuning`, `read_heldout`); `read_heldout` on the primary list refuses to run if a
pinned file below has changed, and so does the notebook `lasset_evidence_layer.ipynb`. Nothing in sections 2-4 changes
after the held-out reading; the result is reported whatever it is. Not committed to git (the user commits only when
asked); the sha pins stand in for the commit.

Terms. Precision (P): share of listed items in the reference. Recall (R): share of reference entries listed. Hit: a
listed item in the reference; false positive (FP): a listed item not in it. Labels by the scorer's own matching
(`eval_assets`, strict). AUC: area under the ROC curve, 0.5 = chance, 1 = perfect ranking.

## 1. Why, and what changed from design v1

The contribution assessment found that nothing measured "the evidence layer adds to LAsset": every earlier test added
the map to this project's own generator. This test applies the map to the lists LAsset itself published, with no
model call, so the only change is the evidence layer.

Design v1 (trace levels T0-T3, label-free drop filters, label-free back-fill) was reviewed on the tuning split only
(workflow wf_cb781c77-6bd). The review showed v1 could not answer the question:
- T0 ("not in map") items are names absent from this RTL version (inval_i, dirty_i, clean_o, mem_sync_i): version
  drift, not map evidence, yet they carried much of v1's H1 gap.
- T3 ("role confirmed") held for about 94% of hits and 83-85% of FPs: it means "the element is used".
- v1's primary filter (drop T0 and T1) was a name check plus a lint-level unused-signal check; on tuning its only
  T1 drop was a hit.
- With a module bootstrap, a filter or back-fill touching 3 modules or fewer has a lower bound of exactly 0, so v1's
  H2 / H3 could fail mechanically.
- Code defects (fields of a whole-clocked record never "stored", prose words pulling in whole records, back-fill
  re-adding named ports, relative paths, missing pins).
Design v2 (this file) fixes the defects and replaces the decision rules. It was written after the v1 tuning
distributions were seen; the held-out split remains unread.

## 2. What is run

| Item | Value |
|---|---|
| Lists | `rtl_only` (LAsset RTL-only initial; **primary**, as in v1), `spec_rtl` (Spec+RTL initial), `refined` (after LAsset's refinement agents) |
| Splits | tuning, 15 modules / 111 entries (development: fixes the model and the threshold); held-out, 26 modules / 189 entries (**confirmatory**, read once) |
| Map | `assetgen_meta/traced_inputs_v2/<split>/` (code-built; typed-relation P and R 0.988 on 120 tuning occurrences against an LLM-written gold; held-out map accuracy unmeasured) |
| Item kinds | single-element (tested population); compound (several elements; always kept); version-drift (no element; never dropped) |
| Evidence | relationship-class tokens per element (`fault_reporter.profile`, class level; a whole record adds its fields' tokens) |
| Model | logistic regression (C=1) on the tokens, trained on the tuning single-element items of the same list |
| Threshold | chosen on tuning only: leave-one-module-out probabilities, the value maximizing the tuning list's F1 after dropping single-element items below it (0 = drop nothing) |
| Intervals | module bootstrap (10000 resamples, seed 0), **97.5%** (Bonferroni over H1 and H2) |
| Control (H2) | random removal of the same number of single-element items per module (2000 draws, seed 0) |
| Model calls | none |

## 3. Readings and decision rules (confirmatory: held-out, primary list)

- **H1, audit.** The tuning-trained model ranks LAsset's held-out single-element hits above its false positives: AUC
  97.5% interval lower bound above 0.5. Claim if it holds: "map evidence carries information about which LAsset items
  are in the reference".
- **H2, filter.** Dropping held-out single-element items below the tuning threshold raises precision: change in P with
  a 97.5% interval above 0, and under 2.5% of random removals of the same size reach the filter's precision. If the
  filter drops items in fewer than 4 modules (including dropping none), H2 is **not testable**. Claim if it holds: "a
  map-based filter learnt on tuning raises LAsset's held-out precision beyond random removal".
- **Neither holds:** "audit trail only: the map traces LAsset's items but does not tell its hits from its false
  positives".
- Secondary rows, no decision rule: `spec_rtl`, `refined`, the within-held-out leave-one-module-out AUC, trace levels,
  item kinds, back-fill (descriptive: its eligible pool is about 10 ports per split).

## 4. Expectation from the development reading (recorded before the held-out reading)

Tuning, single-element items, leave-one-module-out AUC: rtl_only 0.448, spec_rtl 0.676, refined 0.600. Threshold:
rtl_only 0 (no threshold raises the tuning F1, so the filter drops nothing), spec_rtl 0.322 (tuning F1 0.815 -> 0.824),
refined 0. T3 ("use traced") holds for 96% of hits and 94-100% of FPs. Therefore, before reading held-out:
**H2 on the primary list will be "not testable"** (a threshold of 0 drops nothing), and **H1 is expected to fail**
(the tuning model is below chance on its own split). A held-out H1 pass would be a surprise and is read as such. The
primary list is not switched to `spec_rtl` because of these numbers: that would choose the test by its result.

## 5. Pinned files

| File | sha12 |
|---|---|
| `assetgen_meta/lasset_layer.py` | `de75f15d052e` |
| `assetgen_meta/fp_diagnosis.py` | `fe5c7e49abcb` |
| `assetgen_meta/fault_reporter.py` | `b3e73f268594` |
| `assetgen_meta/trace_check.py` | `ed5725aeebb1` |
| `eval_assets.py` | `9749538c778e` |
| `ground_truth/manual_gt_neorv32.json` | `e5437438157d` |
| `LAsset_initial_results/asset_list_neorv32_initial.json` | `44959b53e72b` |
| `ground_truth/lasset_initial.json` | `647d08cfa971` |
| `ground_truth/lasset_refined.json` | `27d1be4a47df` |
| `parsed_tuning18` | `150ec3ff1be6` |
| `assetgen_meta/traced_inputs_v2/tuning` | `a1ccfbfdbc33` |
| `assetgen_meta/traced_inputs_v2/heldout` | `1dd19f332725` |

<!-- layout-move -->
## 6. Pins after the layout move (amendment, 2026-10-02, after the readings above)

On 2026-10-02 the repo root was regrouped into data/, runs/, src/, notebooks/ and logs/, by the author's decision
to amend the pins for a cleaner layout. Section 5 stays exactly as registered, and the readings were taken under it.
The rows below are the same twelve items at their new paths. Items whose sha12 equals section 5 were moved byte for
byte. Five were edited, in path string literals only (a data/, runs/ or src/ prefix). The git tag
`prereg-layout-before` (commit 5ebdfa0693761861f7fa39b7980ef1eeae03ac33) marks the last commit in the old layout, where
all section 5 rows verify.
`python src/verify_layout_move.py` checks every row of all three pre-registrations against that tag and allows no
change except those prefixes. `verify_pins()` keeps the last row per path, so it reads these rows.

| File | sha12 |
|---|---|
| `assetgen_meta/lasset_layer.py` | `2f9b2d9d4c29` |
| `assetgen_meta/fp_diagnosis.py` | `57ae13a6b0ca` |
| `assetgen_meta/fault_reporter.py` | `2bb7b75af0e3` |
| `assetgen_meta/trace_check.py` | `273cda6828e7` |
| `src/eval_assets.py` | `3f8688163ebb` |
| `data/ground_truth/manual_gt_neorv32.json` | `e5437438157d` |
| `data/LAsset_initial_results/asset_list_neorv32_initial.json` | `44959b53e72b` |
| `data/ground_truth/lasset_initial.json` | `647d08cfa971` |
| `data/ground_truth/lasset_refined.json` | `27d1be4a47df` |
| `data/parsed_tuning18` | `150ec3ff1be6` |
| `assetgen_meta/traced_inputs_v2/tuning` | `a1ccfbfdbc33` |
| `assetgen_meta/traced_inputs_v2/heldout` | `1dd19f332725` |
