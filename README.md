# Security assets from VHDL, with an audit trail

Research work from July to October 2026 by Sumaiya Salekin. It replicates part of LAsset (arXiv:2601.02624,
DATE 2026), which uses an LLM to name the security assets of RTL modules, on the NEORV32 RISC-V processor. It then
adds an evidence layer that is built by code: every listed asset can be traced back to the line it cites and, when
it cites one, to the relationship record; code checks whether each citation is true.

**Start here: [`FINAL_NOTEBOOK.ipynb`](FINAL_NOTEBOOK.ipynb).** It runs the final pipeline on the 41 NEORV32 modules
that have a manual reference. The steps are occurrence profiles, the relationship map, correctness checks,
generation with the final prompt, and an audit trail of every listed asset. It then compares the final prompt with
LAsset on all 41 modules and shows how the prompt converged. It ends with what the audit trail says about why the
false positives do not go down, and with what the two structures show about each module. It runs without an API key.

## What the work shows

All figures below are printed by `FINAL_NOTEBOOK.ipynb`. They use strict scoring against LAsset's manual reference.
The tuning set has 15 modules and 111 reference entries; the held-out set has 26 modules and 189 entries; the RTL of
all 41 is listed in `data/LASSET_41_MODULES.csv`.
**Precision** is the share of listed assets that are in the reference. **Recall** is the share of reference entries
that were listed.

- **The evidence layer is exact where code can be exact.**
  - Rebuilding from the raw VHDL gives byte-identical maps (43 of 43) and generator inputs (41 of 41).
  - Every occurrence sits on a line that names its element: 5,760 of 5,760 (tuning) and 11,997 of 11,997 (held-out).
  - Typed relationship records agree with a gold sample: precision 0.988, 95% interval 0.969 to 1.0. That is 120
    occurrences and 212 records. The gold was written by an LLM and adjudicated, so it is a consistency check, not
    human ground truth.
- **On the 41 modules, precision is far below LAsset's; recall is higher than LAsset's RTL-only list.** The final
  prompt on gpt-5.4, 3 runs on every module:
  - All 41 modules (300 entries): precision 0.394, recall 0.856.
  - LAsset's RTL-only list (the like-for-like row; my pipeline reads only RTL): precision 0.711, recall 0.753.
    Difference, with a 95% module-bootstrap interval: precision -0.316 [-0.392, -0.232], recall +0.102 [+0.037, +0.167].
  - Against LAsset's spec+RTL list (0.735 / 0.880): precision -0.341 [-0.395, -0.274]; recall -0.024 [-0.080, +0.030],
    not distinguishable.
  - Held-out modules alone: precision 0.388, recall 0.877 (LAsset RTL-only 0.730 / 0.757). Tuning modules
    (in-sample): 0.406 / 0.820 (pooled over runs; the per-run mean precision is 0.407). *Reading:* held-out precision
    is close to tuning precision, so the gap to LAsset is not an artefact of tuning.
  - The same prompt run by a Claude agent, as a check: 0.343 / 0.932 on all 41 modules.
- **The audit trail explains why the false positives do not go down.** Over the 41 modules (1,183 false-positive
  listings from three runs per module; 500 distinct module/entity/element triples):
  - Most of them (97.1%) cite a real occurrence with a true record (99.5% for hits): they are not misreadings of the RTL
    as the map records it. 59.6% cite only a clock edge, which says no more than "this element is stored".
  - All 13 relationship classes occur on both hits and false positives; 23.8% of false-positive listings have exactly
    the relationship profile of some hit.
  - The profile separates hits from false positives on unseen modules unevenly: on the tuning modules the AUC falls
    from 0.776 in-sample to 0.678 even when the model learns from all 40 other modules; the held-out modules separate
    better and lose less when unseen (0.911 in-sample, 0.875 unseen).
  - Rules found on the tuning modules, applied unchanged to the held-out modules, raise precision from 0.388 to 0.545,
    better than any of 2,000 random removals of the same size. But recall falls from 0.877 to 0.598, and both stay below
    LAsset's RTL-only list.
  - The model lists internal state registers at 0.159 of its list over all 41 modules. The reference lists them at
    0.082 on the tuning modules and 0.011 on the held-out modules. Leaving that role out (an in-sample check: the role
    was picked after seeing these shares) gives 0.459 / 0.866 on the held-out modules but 0.432 / 0.742 on the tuning
    modules, still far below LAsset's precision.
  - 44.4% of the false-positive listings sit in concepts where the reference lists nothing.
  - *Reading:* on the held-out modules, part of the gap is a role preference the structure shows (the reference there
    almost never lists internal state); the rest is a choice among elements that the relationship profiles separate
    only partly. The earlier reading, that the separating differences weaken on unseen modules, holds for the tuning
    modules.
- **The two structures also describe each module.** For all 41 modules: which registers are written from an input
  (192) and which of those from a write-data port (116), which internal signals guard such writes (for example
  `ctrl.lock` in the watchdog), which registers have a reset, and which internal values reach an output.
- **On LAsset's own list, the layer is an audit trail, not a filter.** A pre-registered test on the held-out set did
  not separate LAsset's hits from its false positives: AUC 0.639, 97.5% interval 0.495 to 0.768.

## Timeline

[`docs/TIMELINE.md`](docs/TIMELINE.md) has the full sequence, with the source of every number and the decisions
marked. In short:

| when | what | where |
|---|---|---|
| July | LAsset replication: specification retrieval, closed set by code, a first run and a root-cause pass over its 163 false positives; the RTL parser fixed | `notebooks/finetuning_assetgen.ipynb`, `docs/TUNING_GUIDE.md`, `src/gt_extract.py`, `src/rtl_parse.py` |
| 2-8 Aug | v1 recall study: one change per arm, each pre-registered with a decision rule | `logs/ABLATION_LOG.md` |
| 8-18 Aug | v2 precision study with a recall guard; leak checks enforced in code | `logs/ABLATION_LOG_V2.md`, `logs/V02_REGISTRATION_DRAFT.md`, `notebooks/finetuning_assetgen_v2.ipynb` |
| 17 Aug - 6 Sep | parser and verifier work; edge definitions for relationships | `bahavioral_patterns_of_assets/PARSER_ABLATION_LOG.md`, `bahavioral_patterns_of_assets/VERIFIER_ABLATION_LOG.md` |
| 9-29 Sep | occurrence profiles: LLM versions measured, then the structure moved into code | `bahavioral_patterns_of_assets/notebooks/` (`occurrence_profiles_v2.ipynb`, `_v3.ipynb`, `_v3b.ipynb`), `step1/` |
| 19-30 Sep | meta prompts and hand arms; the relationship map | `notebooks/assetgen_meta.ipynb`, `step1/lasset_step1/RELATION_EXPERIMENTS_LOG.md`, `notebooks/lasset_step1.ipynb` |
| 1-2 Oct | held-out pre-registrations, traced arms with cited occurrence IDs, the prompt-optimization loop, gpt-5.4, the false-positive diagnosis, and the evidence layer on LAsset's lists | `assetgen_meta/HELDOUT_PREREG.md`, `assetgen_meta/prompt_opt/OPTIMIZATION_LOG.md`, `notebooks/lasset_evidence_layer.ipynb`, `FINAL_NOTEBOOK.ipynb` |

Decisions I would point to first:

- Pre-registration from the first study on. Wrong predictions were kept, and corrections were written beside the
  registered block, never inside it.
- No answers in prompts. A leaked element name was found and removed, and the check was then enforced in code.
- Code where there is one right answer. Structure and relationships moved from the LLM to code after measurement.
- Rules fitted to the reference were rejected when they failed on held-out modules.
- Claims I had made earlier were corrected in the logs, including in a skeptical review of my own contribution
  (`assetgen_meta/contribution_assessment/`).

## Repository map

| path | what it holds |
|---|---|
| `FINAL_NOTEBOOK.ipynb` | the final pipeline, its checks and its analysis (start here) |
| `final/` | `final_pipeline.py` (the notebook's helper); `results41.py` (scores on the 41 modules vs LAsset), `fp_trace41.py` (why the false positives stay, with outputs in `fp_trace41/`) and `module_insights.py` (module portraits, outputs in `module_insights/`), each with a self-test; `convergence.csv` and `heldout.csv` (every scored prompt version), the occurrence profiles of the 41 modules (plus the 2 control modules boot_rom and fifo), the FP diagnosis and the fault report |
| `notebooks/` | the ablation notebooks: `finetuning_assetgen.ipynb` (v1), `finetuning_assetgen_v2.ipynb` (v2), `assetgen_meta.ipynb` (meta prompts, hand arms, traced arms, diagnosis), `lasset_step1.ipynb` (occurrence profiles and relation map on the 15 tuning modules), `lasset_evidence_layer.ipynb` (the pre-registered test of the evidence layer on LAsset's lists) |
| `logs/` | logs and registration of the v1 and v2 prompt studies: `ABLATION_LOG.md`, `ABLATION_LOG_V2.md`, `V02_*.md` |
| `docs/` | `TIMELINE.md` (July to October), `LAYOUT.md` (the folder layout and the 2026-10-02 move), `TUNING_GUIDE.md`, `experiment_tracker.csv` (the July plan) |
| `src/` | the study code from July and August: parser, prompts, ICL examples, the scorer (`eval_assets.py`), and `verify_layout_move.py` |
| `data/` | `RTL_data/` and `RTL_heldout/` (NEORV32 VHDL: 18 tuning files: 15 with reference entries, 2 control modules (boot_rom, fifo) and the shared package; and 26 held-out files), `ground_truth/` and `LAsset_initial_results/` (LAsset's manual reference and published lists; see the notices), `parsed_*/` (closed sets: the ports and signals of each module, extracted by regex) |
| `runs/` | the run folders needed to re-score the final prompt, its baselines and the held-out checks |
| `assetgen_meta/` | meta prompts, hand arms, traced inputs, `trace_check.py` (the citation checker), the optimization loop (`prompt_opt/`), `fp_diagnosis.py`, `fault_reporter.py`, `lasset_layer.py`, pre-registrations |
| `step1/` | occurrence profiles and relationship maps: `structure_stage.py` (tree-sitter Context and Path), `code_site_tags.py`, `code_pairs_v2.py`, `build_heldout_code_map.py`, the stored maps, the relation log, and the gold set (`bakeoff/`) |
| `step2/` | the Step 2 rules and the script that built the held-out closed sets |
| `bahavioral_patterns_of_assets/` | parser and verifier logs, the occurrence-profile notebooks and their prompts (`annotation_pack_elements/`) |
| `blind_agent/` | a side study: prompts written from theory only, without seeing the reference |
| `third_party/` | the NEORV32 license |

Logs and outputs written before 2026-10-02 use the old root paths (for example `RTL_data/` for `data/RTL_data/`).
[`docs/LAYOUT.md`](docs/LAYOUT.md) maps them.

## Running it

```bash
pip install -r requirements.txt
```

On Windows, clone into a short folder: the longest path in the repo is 146 characters, and Windows limits a full
path to 260 unless `git config --global core.longpaths true` is set.

Open `FINAL_NOTEBOOK.ipynb` and run all cells. It needs no API key and takes a few minutes. If the tree-sitter
VHDL grammar is missing, the first cell stops and prints the one-line command that fetches it.

The gpt-5.4 runs are already in `runs/`. To generate runs that are missing, put `OPENAI_API_KEY=...` in a file
named `API.env` in the repo root and set `RUN_API = True`; modules already on disk are skipped. That file is ignored
by git.

To check the files pinned by the three pre-registrations (it prints one line per pin and ends with the failure
count):

```bash
python src/verify_layout_move.py
```

The pins were registered before the 2026-10-02 layout move. The checker compares every pin with the tag
`prereg-layout-before`, the last commit in the old layout. It allows a file to differ only by the move's path
prefixes. [`docs/LAYOUT.md`](docs/LAYOUT.md) explains this.

**Which notebooks re-run on a fresh clone.**
- `FINAL_NOTEBOOK.ipynb` and `notebooks/lasset_evidence_layer.ipynb` re-run in full.
- In `notebooks/assetgen_meta.ipynb`, the final-version and diagnosis cells (57-69) read only published files. The
  generation cells among them need an API key.
- The other notebooks are records: their saved outputs show the results, but the run folders and caches they read
  are not published. Their numbers are in the logs. To re-run record code, use a worktree of the tag
  (`git worktree add ../prepoison-old prereg-layout-before`), where the old layout is intact.

`.gitattributes` keeps every file byte for byte (`* -text`), because the pre-registrations pin files by a hash of
their exact bytes.

## Limits

- Three gpt-5.4 runs per module; the Claude check has one run on the held-out modules.
- Every precision figure measures agreement with one manual list. An element the reference does not list is
  counted as a false positive, which is not proof that it is not an asset.
- The LAsset rows are LAsset's published lists, scored with my scorer. They are not reruns of LAsset.
- The relationship gold set was written by an LLM and covers the tuning modules only.
- Executors and the scorer changed over the months. Numbers within one study are comparable; across months they
  are approximate (see the timeline).

## Third-party material

The NEORV32 RTL (BSD 3-Clause), LAsset's reference lists (no upstream license; included for scoring, with
attribution) and two open IPs used as worked examples in prompts are described in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
