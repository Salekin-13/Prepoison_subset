# Security assets from VHDL, with an audit trail

Research work from July to October 2026 by Sumaiya Salekin. It replicates part of LAsset (arXiv:2601.02624,
DATE 2026), which uses an LLM to name the security assets of RTL modules, on the NEORV32 RISC-V processor. It then
adds an evidence layer that is built by code: every listed asset can be traced back to the exact line and
relationship in the VHDL that the model cited.

**Start here: [`FINAL_NOTEBOOK.ipynb`](FINAL_NOTEBOOK.ipynb).** It runs the final pipeline on the 41 NEORV32 modules
that have a manual reference. The steps are occurrence profiles, the relationship map, correctness checks,
generation with the final prompt, and an audit trail of every listed asset. It ends with what that trail says about
why precision stopped rising, and a plot of how the prompt converged. It runs without an API key.

## What the work shows

All figures below are printed by `FINAL_NOTEBOOK.ipynb`. They use strict scoring against LAsset's manual reference.
The tuning set has 15 modules and 111 reference entries; the held-out set has 26 modules and 189 entries.
**Precision** is the share of listed assets that are in the reference. **Recall** is the share of reference entries
that were listed.

- **The evidence layer is exact where code can be exact.**
  - Rebuilding from the raw VHDL gives byte-identical maps (43 of 43) and generator inputs (41 of 41).
  - Every occurrence sits on a line that names its element: 5,760 of 5,760 (tuning) and 11,997 of 11,997 (held-out).
  - Typed relationship records agree with a gold sample: precision 0.988, 95% interval 0.969 to 1.0. That is 120
    occurrences and 212 records. The gold was written by an LLM and adjudicated, so it is a consistency check, not
    human ground truth.
- **Accuracy is below LAsset's.**
  - The final prompt on gpt-5.4 (mean of 3 runs, tuning): precision 0.407, recall 0.820.
  - LAsset's published RTL-only list, scored the same way: 0.680 / 0.748.
  - Held-out generation is pending: my API credits ran out.
- **The audit trail explains the errors better than it fixes them.**
  - Of the 399 false positives in the 3 tuning runs, 96.5% cite a true occurrence and a true record. For hits the
    share is 99.3%. The false positives are not hallucinations.
  - All 21 relationship classes occur on both hits and false positives.
  - A model that predicts hit vs false positive from the relationship profile reaches an AUC of 0.776 on the modules
    it was fitted on. On a module left out it reaches 0.644.
  - *Reading:* what separates a listed element from an unlisted one is mostly not in the code structure. That may
    explain why two months of prompt changes moved precision so little. The notebook names the measurement that
    would show this reading is wrong.
- **On LAsset's own list, the layer is an audit trail, not a filter.** A pre-registered test on the held-out set did
  not separate LAsset's hits from its false positives: AUC 0.639, 97.5% interval 0.495 to 0.768.

## Timeline

[`docs/TIMELINE.md`](docs/TIMELINE.md) has the full sequence, with the source of every number and the decisions
marked. In short:

| when | what | where |
|---|---|---|
| July | LAsset replication: specification retrieval, closed set by code, a first run and a root-cause pass over its 163 false positives; the RTL parser fixed | `finetuning_assetgen.ipynb`, `docs/TUNING_GUIDE.md`, `gt_extract.py`, `rtl_parse.py` |
| 2-8 Aug | v1 recall study: one change per arm, each pre-registered with a decision rule | `ABLATION_LOG.md` |
| 8-18 Aug | v2 precision study with a recall guard; leak checks enforced in code | `ABLATION_LOG_V2.md`, `V02_REGISTRATION_DRAFT.md`, `finetuning_assetgen_v2.ipynb` |
| 17 Aug - 6 Sep | parser and verifier work; edge definitions for relationships | `bahavioral_patterns_of_assets/PARSER_ABLATION_LOG.md`, `VERIFIER_ABLATION_LOG.md` |
| 9-29 Sep | occurrence profiles: LLM versions measured, then the structure moved into code | `bahavioral_patterns_of_assets/notebooks/occurrence_profiles_v2/v3/v3b.ipynb`, `step1/` |
| 19-30 Sep | meta prompts and hand arms; the relationship map | `assetgen_meta.ipynb`, `step1/lasset_step1/RELATION_EXPERIMENTS_LOG.md`, `lasset_step1.ipynb` |
| 1-2 Oct | held-out pre-registrations, traced arms with cited occurrence IDs, the prompt-optimization loop, gpt-5.4, the false-positive diagnosis, and the evidence layer on LAsset's lists | `assetgen_meta/HELDOUT_PREREG.md`, `assetgen_meta/prompt_opt/OPTIMIZATION_LOG.md`, `lasset_evidence_layer.ipynb`, `FINAL_NOTEBOOK.ipynb` |

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
| `final/` | `final_pipeline.py` (the notebook's helper), `convergence.csv` and `heldout.csv` (every scored prompt version, rebuilt by `build_convergence.py`), the occurrence profiles of the 41 modules (plus the 2 controls boot_rom and fifo), the FP diagnosis and the fault report |
| `docs/` | `TIMELINE.md` (July to October), `TUNING_GUIDE.md`, `experiment_tracker.csv` (the July plan) |
| `ABLATION_LOG.md`, `ABLATION_LOG_V2.md`, `V02_*.md` | logs and registration of the v1 and v2 prompt studies |
| `finetuning_assetgen.ipynb`, `finetuning_assetgen_v2.ipynb` | the v1 and v2 ablation notebooks |
| `assetgen_meta.ipynb`, `assetgen_meta/` | meta prompts, hand arms, traced inputs, `trace_check.py` (the citation checker), the optimization loop (`prompt_opt/`), `fp_diagnosis.py`, `fault_reporter.py`, `lasset_layer.py`, pre-registrations |
| `lasset_step1.ipynb`, `step1/` | occurrence profiles and relationship maps: `structure_stage.py` (tree-sitter Context and Path), `code_site_tags.py`, `code_pairs_v2.py`, `build_heldout_code_map.py`, the stored maps, the relation log, and the gold set (`bakeoff/`) |
| `lasset_evidence_layer.ipynb` | the pre-registered test of the evidence layer on LAsset's lists |
| `bahavioral_patterns_of_assets/` | parser and verifier logs, the occurrence-profile notebooks and their prompts (`annotation_pack_elements/`) |
| `blind_agent/` | a side study: prompts written from theory only, without seeing the reference |
| root `*.py` | parser, prompts, ICL examples, the scorer (`eval_assets.py`) |
| `RTL_data/`, `RTL_heldout/` | NEORV32 VHDL: 18 tuning files (15 with reference entries, plus 3 controls) and 26 held-out files |
| `ground_truth/`, `LAsset_initial_results/` | LAsset's manual reference and published lists (see the notices) |
| `parsed_*` | closed sets: the ports and signals of each module, extracted by regex |
| `assets_*` | the run folders needed to re-score the final prompt, its baselines and the held-out checks |
| `step2/` | the Step 2 rules and the script that built the held-out closed sets |

## Running it

```bash
pip install -r requirements.txt
```

Open `FINAL_NOTEBOOK.ipynb` and run all cells. It needs no API key and takes a few minutes. If the tree-sitter
VHDL grammar is missing, the first cell stops and prints the one-line command that fetches it.

To run the held-out generation, put `OPENAI_API_KEY=...` in a file named `API.env` in the repo root and set
`RUN_API = True`. That file is ignored by git.

To check that the files pinned by the pre-registrations are unchanged (an empty list means all match):

```bash
python -c "import sys; sys.path.insert(0, 'assetgen_meta'); import lasset_layer; print(lasset_layer.verify_pins())"
```

**Which notebooks re-run on a fresh clone.**
- `FINAL_NOTEBOOK.ipynb` and `lasset_evidence_layer.ipynb` re-run in full.
- In `assetgen_meta.ipynb`, the final-version and diagnosis cells (57-69) read only published files. The generation
  cells among them need an API key.
- The other notebooks are records: their saved outputs show the results, but the run folders and caches they read
  are not published. Their numbers are in the logs.

`.gitattributes` keeps every file byte for byte (`* -text`), because the pre-registrations pin files by a hash of
their exact bytes.

## Limits

- Held-out generation with the final prompt has not run yet.
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
