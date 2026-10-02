# Repository layout and the 2026-10-02 move

On 2026-10-02 the loose files and folders in the repo root were grouped into five folders. Logs, pre-registrations,
notebook outputs and the convergence tables written before that date still use the old names. This page maps them.

## What moved where

| old path (root) | new path |
|---|---|
| `RTL_data/`, `RTL_heldout/` | `data/RTL_data/`, `data/RTL_heldout/` |
| `ground_truth/`, `LAsset_initial_results/` | `data/ground_truth/`, `data/LAsset_initial_results/` |
| `parsed_tuning18/`, `parsed_heldout26/`, `parsed_heldout_raw/` | `data/parsed_tuning18/`, `data/parsed_heldout26/`, `data/parsed_heldout_raw/` |
| `assets_*` run folders (22) | `runs/assets_*` (same names) |
| the 23 root `*.py` files (`eval_assets.py`, `rtl_parse.py`, `prompts*.py`, `icl_examples*.py`, ...) | `src/` (same names) |
| `finetuning_assetgen.ipynb`, `finetuning_assetgen_v2.ipynb`, `assetgen_meta.ipynb`, `lasset_step1.ipynb`, `lasset_evidence_layer.ipynb` | `notebooks/` (same names) |
| `ABLATION_LOG.md`, `ABLATION_LOG_V2.md`, `V02_HANDOFF.md`, `V02_REGISTRATION_DRAFT.md` | `logs/` (same names) |

Nothing else moved. `FINAL_NOTEBOOK.ipynb`, `README.md`, `final/`, `docs/`, `third_party/`, `assetgen_meta/`, `step1/`,
`step2/`, `bahavioral_patterns_of_assets/` and `blind_agent/` stay where they were. The subsystem folders have their
own `data/`-like subfolders (for example `bahavioral_patterns_of_assets/data/RTL_data/`); those did not move.

## How the move was made

1. **Renames only.** Every moved file kept its bytes. Git records the move as 1,449 renames at 100% similarity.
2. **Path strings.** In code that still runs (`FINAL_NOTEBOOK.ipynb`, `notebooks/lasset_evidence_layer.ipynb`, the
   final-version and diagnosis cells of `notebooks/assetgen_meta.ipynb`, and the modules they import), string
   literals that name a moved item gained a `data/`, `runs/` or `src/` prefix. Six unpinned modules that put the repo
   root on `sys.path` now put `src/` there instead (`final/final_pipeline.py`, `assetgen_meta/traced_inputs.py`,
   `cia_label.py`, `trace_digest.py`, `prompt_opt/read_final.py`, `hand_arms/score_hand_arm.py`). The two re-runnable notebooks move to the repo root when started
   in `notebooks/`.
3. **Records stay as they were.** Older notebooks and scripts whose inputs are not published were not edited. Their
   saved outputs, and the logs, keep the old names.

## The pre-registration pins

The three pre-registrations pin files by a hash of their bytes. A moved file keeps its hash. Seven pinned code files
were edited in path strings only: `src/eval_assets.py`, `assetgen_meta/meta_tools.py`, `assetgen_meta/lasset_layer.py`,
`assetgen_meta/fp_diagnosis.py`, `assetgen_meta/fault_reporter.py`, `assetgen_meta/trace_check.py` and
`step1/build_heldout_code_map.py`. Their hashes changed.

- **The tag `prereg-layout-before`** marks the last commit in the old layout. There, all 40 pin rows of the three
  pre-registrations verify with the repo's own checks: `lasset_layer.verify_pins()`, `heldout_readings.verify_prereg()`
  and `prompt_opt/heldout_check.verify()`.
- **`python src/verify_layout_move.py`** (run from the repo root) checks every one of the 40 rows against that tag.
  A row passes if the item is unchanged, or moved with the same bytes, or is a Python file that differs from the
  tagged bytes only in string literals, each rewritten by exactly one of the move's prefixes. Code, comments,
  spacing and line endings must match byte for byte. It tests itself on planted failures before it reports.
- **`assetgen_meta/lasset_layer/PREREG.md` has an appended section 6** with the twelve items at their new paths, so
  `verify_pins()` and `notebooks/lasset_evidence_layer.ipynb` still check pins at the latest commit. Section 5 is
  unchanged. `HELDOUT_PREREG.md` and `prompt_opt/HELDOUT_CHECK_PREREG.md` are not edited. Their own verifiers name
  the old paths, so run them at the tag (below), or use `src/verify_layout_move.py`.

## Running record code

Record notebooks and scripts expect the old layout. Run them from a worktree of the tag, next to this clone:

```bash
git worktree add ../prepoison-old prereg-layout-before
```

Command-line runs of the pinned modules in the new layout need `src/` on the import path, because their own
`sys.path` lines (not edited, to keep the edits to path strings) add the repo root, not `src/`:

```bash
PYTHONPATH=src python assetgen_meta/lasset_layer.py --pins
```
