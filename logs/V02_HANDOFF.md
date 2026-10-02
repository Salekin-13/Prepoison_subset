# LAsset replication — handoff for the v02 precision study

Paste this whole file as the opening prompt of the new chat.

---

## What this project is

I am replicating **LAsset** (arXiv 2601.02624v2, DATE 2026), specifically **Algorithm 1 line 5**
— `Asset_m ← LLMASSET(S_m, Prm_m, R(m), ICL_ASSET)` — on an 18-module subset of the NEORV32
RISC-V SoC, as a pre-registered ablation study. Working directory
`E:\jobs\ff\test\Prepoison_subset`, git branch `feat/rtl-parse-fix-and-eval-framework`.

**Up to now the objective has been recall.** The next study (v02) switches to **precision, with
recall as a guard.** That switch has not yet been registered.

---

## The paper, as verified against the PDF and the authors' published outputs

- **Line 4** `MOD_RTLPARSE{Prm_m, Sec_m} ← LLMPARSE(R(m))` depends on **RTL only**. Two LLM
  parsers — one for I/O ports, one for internal signals/registers — with types and functions.
- **Line 5** takes the spec summary `S_m`, the parsed elements `Prm_m`, the RTL `R(m)`, and the
  ICL examples. LAsset's "Only RTL" configuration drops **`S_m` and nothing else**.
- **Asset Generation is lines 5 AND 6.** Line 5 binds each conceptual asset to its structural
  RTL reference — the **primary** assets. Line 6 `SECASSET` then finds, per primary asset, the
  internal signals that influence it — the **secondary** assets. Their published
  `asset_list_neorv32_initial.json` holds both in one record (`Asset RTL` + `Secondary Assets`).
- **Refinement is lines 7–9** (attack scenario → CWE mapping → self-critique). §III-C states
  plainly that LLMs over-produce at generation and that refinement exists to filter. Measured
  effect of refinement: precision **+0.083**, recall **−0.026** — it only removes. **So recall
  out of line 5 is a hard ceiling for the whole pipeline.**
- Model GPT-5. SpecRAG: 1 000-char chunks, 200 overlap, top-20, `text-embedding-ada-002`, FAISS.
- Reported recall: SoC **90.67%** (Spec+RTL) vs **78.33%** (RTL only); IP **93.21%** vs
  **90.12%**; Nath et al. 83.33%. Table III SoC: RTL+Spec TP 272 / FN 30 / FP 59; RTL TP 235 /
  FN 67 / FP 59.

**Their line-5 output scored on our 15 modules: 137 primaries, TP 101, FP 36, P 0.737, R 0.910.**
Also 726 secondary mentions (283 distinct names) which we do **not** count — our ground truth is
a primary-asset list, so primary-only is the correct comparator.

---

## Setup and metric

- **18 modules parsed, 15 scored** (`boot_rom`, `fifo`, `package` are pruned, as in the paper).
  **111 references** across the 15.
- **Ground truth is the paper's own manual list** — `ground_truth/manual_gt_neorv32.json`,
  source `Asset_Dataset_Statistics_NEORV32.xlsx`, sheet "Assets (Manual)". Verified to match the
  paper's Table I golden counts exactly: CPU 14, PMP 6, Debug Transport 5, TRNG 7, UART 10. We
  inherit any omission in theirs and do not independently validate it.
- **Metric M-2**: index-based matching, same-name elements not collapsed across entities,
  reference multiplicity capped by `_name_caps`. Near-match (record↔field) is tracked separately
  and is currently **0** — all recall is exact.
- **Paired bootstrap with modules as the pairing unit** for every arm-vs-baseline delta.
- Generation model `gpt-5-mini`, `effort="high"`.
- **1 572 elements across the 15 modules; 111 are assets → 7.1% density.**

---

## Results

| version | n | emit | TP | FP | P | recall | sd | F1 | portR | sigR | sfR |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v0 | 3 | 205 | 61.3 | 143.3 | 0.300 | 0.553 | 0.019 | 0.389 | 0.326 | 0.771 | 0.688 |
| v01 | 3 | 235 | 67.3 | 167.3 | 0.288 | 0.607 | 0.005 | 0.390 | 0.589 | 0.573 | 0.688 |
| v01c2 | 5 | 297 | 82.6 | 214.8 | 0.277 | 0.744 | 0.062 | 0.404 | 0.804 | 0.669 | 0.755 |
| v01c3 | 5 | 274 | 87.0 | 186.8 | 0.318 | 0.784 | 0.053 | 0.452 | 0.796 | 0.738 | 0.839 |
| v01c4 | 5 | 352 | 93.8 | 257.8 | 0.267 | 0.845 | 0.022 | 0.406 | 0.906 | 0.781 | 0.845 |
| v01c5 | 5 | 331 | 94.2 | 237.0 | 0.285 | 0.849 | 0.015 | 0.426 | 0.906 | 0.769 | 0.871 |
| v01c6 | 5 | 428 | 97.8 | 330.2 | 0.229 | 0.881 | 0.018 | 0.364 | 0.919 | 0.812 | 0.923 |
| v01c6p1 | 5 | 476 | 99.6 | 376.0 | 0.210 | 0.897 | 0.013 | 0.340 | 0.885 | 0.894 | 0.948 |
| **v01c6p1p2** | **3** | **404** | **98.3** | **305.7** | **0.243** | **0.886** | **0.026** | **0.382** | **0.894** | **0.875** | **0.914** |
| *LAsset line 5* | 1 | 137 | 101 | 36 | **0.737** | 0.910 | | 0.815 | 0.894 | 0.906 | 0.935 |

**The chain — one proposition per hop, never compare across two:**

```
v0 -> v01        ICL examples                      A-01
v01 -> v01c2     core: role, not location          A-02
v01c2 -> v01c3   core: port-record granularity     A-03   (precision +0.050)
v01c3 -> v01c4   core: STEP 1 exposed              T-1    (confounded, diagnostic only)
v01c4 -> v01c5   ICL shows concepts                       (measured NULL on everything)
v01c5 -> v01c6   core: per-concept closure sweep   A-08   (recall +0.032, precision -0.056)
v01c6 -> v01c6p1     drop technical summary        P-1    (NULL on all three)
v01c6p1 -> v01c6p1p2 drop parsed closed set        P-2    (NULL recall, +0.017 precision)
```

**Prompt shas:** v0 `e0d31754ca62` · v01 `e99a0b798fd2` · v01c2 `8df77c38fab9` · v01c3
`b6d98530d74b` · v01r `037070a1959d` · v01c4 `ccdce70c1510` · v01c5 `9f66b93202ce` · v01c6
`9d9cf29aae23` · v01c6p1 `2214e7f97f39` · v01c6p1p2 `70569027214e` · v01c6p1p2d `cc3f0b397044`.

---

## What we established

1. **The summary is inert.** P-1 null on recall, precision and F1. LAsset loses 12 recall points
   at SoC level to the same ablation; we lose nothing. Most likely because we over-emit enough
   to sweep up the spec-dependent assets by accident.
2. **The parsed element list is inert too.** P-2 null on recall (−0.020 [−0.086, +0.039]),
   precision +0.017, emissions −15%, and **58% of every user message removed**. Costs: the union
   ceiling falls 0.950 → 0.937 (matched 3-repeat comparison) and recall variance roughly
   doubles. **But precision variance drops 2.5×**, which is why this is the right base for a
   precision study.
3. **The model never invents identifiers.** Across P-2's three repeats: **187 ungrounded names,
   100% of them real identifiers declared in the RTL** that our regex parser missed. Zero
   hallucinations, zero misspellings.
4. **Misses are binding failures, not conception failures.** T-1: 82–85% of missed references
   had a covering concept already in the model's own list, and the element was available.
5. **A-08 is the only arm that ever raised the ceiling** (union 0.928 → 0.955).
6. **~50% of our false positives are elements LAsset itself names as *secondary* assets.** Our
   single call does lines 5 and 6 at once while the reference credits only line 5. The share has
   been flat near half since v0 — no arm caused it, it is structural. **Deferred by decision:
   secondary assets are out of scope until primary precision is fixed.**

---

## The precision problem, quantified

We are **not** outperforming the paper. We reach comparable recall by naming three times as much:

| | emit | share of the 1 572 elements | recall | precision | lift over random |
|---|---|---|---|---|---|
| LAsset | 137 | 8.7% | 0.910 | 0.737 | **10.5×** |
| us (v01c6p1p2) | 404 | 25.7% | 0.886 | 0.243 | **3.4×** |

With TP held near 100, precision is arithmetic on emissions:

| target P | emissions allowed | cut from 476 |
|---|---|---|
| 0.30 | 333 | 30% |
| 0.40 | 250 | 47% |
| 0.50 | 200 | 58% |
| **0.737** | **136** | **71%** |

**Where the false positives are** (v01c6p1p2):

- **A long tail, not a few offenders.** 286 distinct FP names; the top 20 account for only 20%.
  `bus_req_i` + `bus_rsp_o`, the worst two, are 6.5% between them. **A suppression blocklist
  will not work — the lever has to be a general criterion.**
- By class: signal-field 47%, port 27%, signal 25%.
- By objective: **Integrity is 68% of the ground truth and 67% of the FPs — proportional, not
  over-claimed.** The one real outlier is **Confidentiality: 3 real assets, 58 claimed per
  repeat, precision 0.144.**
- **Oracle ceiling for concept-level filtering:** killing every concept that produced no true
  positive (cheating with the answers) reaches only **P = 0.347**, recall unchanged. **Line-5
  prompting alone almost certainly cannot reach 0.737** — the paper gets there with lines 7–9.

---

## Known leak, fix built but NOT RUN

The core quotes four real NEORV32 identifiers as naming examples. One is an **answer**:

| identifier | ground truth in | entered at |
|---|---|---|
| **`ctrl_i`** | **10 of the 41 annotated modules** (cpu_alu, cpu_counters, cpu_cp_bitmanip, cpu_cp_cond, cpu_cp_crypto, cpu_cp_fpu, cpu_cp_shifter, cpu_lsu, cpu_pmp, cpu_regfile) | A-03 |
| `ctrl_i.csr_wdata`, `ctrl.buf_req`, `rtx_engine.sreg` | none | A-03 / V0 |

Worth ≤ 0.009 recall on the 15 scored modules (only `cpu_pmp` overlaps), but **9 of the 10 are
in the 26 held-out modules**, so it would poison any generalisation test.

**It is not a confound for P-1 or P-2** — it entered at A-03 and sits in baseline and arm alike,
cancelling in every paired delta. It threatens the absolute recall quoted against the paper.

**Arm L-1 (`v01c6p1p2d`, sha `cc3f0b397044`) is built and registered but has not been run.** It
replaces the four names with `cfg_port_i` / `cfg_port_i.mode` / `blk_ctrl.step` /
`xfer_unit.stage`, all verified absent from the 1 355 parsed names and 218 ground-truth names.
`clk_i` and `rstn_i` are deliberately kept — not ground truth anywhere, universal VHDL
convention, and they serve a correct rule.

**Standing rule:** no literal identifier from any of the 41 annotated modules may enter a prompt.
Check with `scratchpad/identifier_audit.py` before registering any arm that adds an example.

---

## Files

| file | what |
|---|---|
| `prompts.py` | every core variant, built by substitution with round-trip asserts |
| `icl_examples_01b.py` | ICL block with `ConceptualAssets` (v01c5, v01c6) |
| `icl_examples_01b_nosum.py` | …minus the summary (P-1) |
| `icl_examples_01b_noparse.py` | …minus the parsed blocks (P-2) |
| `eval_assets.py` | scorer, `paired`, `ablate`, `by_class`, `near_matches`, `load_validation`, `validation_table` |
| `diagnose_step1.py` | concept-layer diagnostics (T-1, concept precision) |
| `ABLATION_LOG.md` | the canonical record — every arm, Expect, decision rule and Got |
| `finetuning_assetgen.ipynb` | cells: `93ecd6e3` config · `475f640b` parsing (`parsed_all`) · `2031c14a` registry + `build_asset_user` + `validate_primary` · `35e62f3a` run loop |

Run directories `assets_tuning18_<version>_r<n>/` hold one JSON per module plus `_run_meta.json`
(prompt sha), `_validation.json` (structured validation report) and `_raw/` (verbatim responses).
Files starting with `_` are skipped by `load_run`.

---

## Working rules — these are load-bearing

- **NEVER edit the notebook, `prompts.py`, `eval_assets.py`, `diagnose_step1.py` or any
  `icl_examples_*` module while a run is in progress.** Writing the `.ipynb` reloads the editor
  and kills the kernel. This already destroyed one paid run.
- **One proposition per arm.** A new version is `CURRENT_BASELINE` plus exactly one change and
  pairs against it. Dropping an input block is only half an arm — the prompt's references to it
  must go too, or the model is told to use something absent.
- **Pre-register `Expect` and a decision rule in `ABLATION_LOG.md` before running anything.**
  Then record `Got:` verbatim, including predictions that were wrong.
- **Never quote a delta computed across two changes.** Route new versions through the `BASELINE`
  map so nothing falls through to a multi-variable contrast.
- **n=3 is enough for precision and F1** (3-of-5 subsampling: 100% sign agreement). **n=5 is
  needed for per-class recall** (port sign agrees only 58% at n=3).
- **Union-over-repeats is an internal ceiling diagnostic only** — never comparable to the
  paper's single-run figures, and only comparable across versions at matched repeat counts.
- Prompt caching: input $0.25/1M, cached $0.025/1M, output $2.00/1M.

**How I want you to work with me:** plain language, no jargon dumps. Act as a supervisor who is
also a research partner — teach and collaborate, explain the reasoning before proposing. Verify
claims against the actual sources and artifacts rather than recalling them; say plainly which
sources you have read and which you only know second-hand. Keep LASP, LASHED, Nath & Tan and
SAIF out of the implementation — they inform how we read LAsset, nothing more.

---

## What v02 is

A **fresh precision-targeted study**, starting from a clean re-baseline.

**Agreed so far:**

- `v02` is built on the **`v01c6p1p2` input regime** — comment-stripped RTL, ICL examples and
  prompt instructions only. No spec summary, no parsed ports/signals. Justified by: both
  ablations null, 58% less input per call, and precision 2.5× more stable there.
- `v02` **must fold in the L-1 de-leak.**
- `v02` should be a **minimal clean re-baseline, not a bundle of new ideas** — a bundle that
  regresses cannot be bisected, and this project has already lost a whole layer to one bundled
  change. The accumulated conclusions become the **arm queue**, not the baseline.
- The **objective switch must be registered** — precision as the target, recall as a guard with
  the threshold fixed in advance (proposed: recall must not fall more than 0.03 from v02's
  baseline, judged on the paired CI).
- A `v02` vs `v01c6` line may be reported as "where we were vs where we are", but **never as an
  attributable delta** — it bundles the summary drop, the parsed drop and the prompt change.

**Proposed arm queue, in priority order:**

1. **Revert A-08.** It bought recall +0.032 for precision −0.056. In a precision study that
   trade inverts. Cheapest possible test.
2. **A per-concept element budget.** The model binds ~3.6 elements per concept and A-08 pushed
   it higher. A general cap, not a blocklist.
3. **Tighten the Confidentiality test.** 58 claims against 3 real assets is the only clean
   outlier in the FP data.
4. **Restore A-03's decay.** Port-field FPs went 2.2 → 20.8 across later arms; something
   downstream is eroding the granularity rule.

**Open items not yet done:**

- **L-1 has not been run.** Fold it into v02 rather than running it standalone.
- **P-2′** (keep the names, strip only the `function` field) was pre-registered and never run.
  It can only run on `v01c6p1`, since `v01c6p1p2` has no parsed block left to strip. It answers
  whether stage 4's LLM annotation is worth enriching.
- **No held-out set exists.** All 15 modules with RTL are the tuning set; the other 26 annotated
  modules have no RTL in `RTL_data/`. Getting some from the NEORV32 repo would give the study
  its first honest generalisation number — and P-2 makes it affordable, since generation now
  needs only RTL.
- **Five arms of prompt tuning were done on these same 15 modules** (A-02's role list, A-03's
  rule, A-08's sweep were each designed after inspecting misses on them). This is fitting to the
  test set and is the most likely explanation for matching the paper's recall while sitting at a
  third of its precision.

**First task for the new chat:** draft the v02 registration for review — the objective switch,
the recall guard, exactly what goes into the baseline prompt, and the arm queue. Nothing runs
until I approve it.
