# Asset definition

Adopted 2026-10-01 at the user's request. It governs every prompt arm and every reported number from now on. A change
is a new dated section at the end of this file, logged in `step1/lasset_step1/RELATION_EXPERIMENTS_LOG.md`.
Measurements behind it: that log, entries "What 'asset' means", "Reanalysis of next steps" and "Counter-example
checks"; all on the 15 tuning modules unless marked.

## 1. The reference we are scored against

- **What it is.** The LAsset repository's manual "True Assets" list for NEORV32 (LAsset, arXiv 2601.02624, DATE 2026):
  41 modules. We tune on 15 (`RTL_data/`, 111 entries) and hold out 26 (`RTL_heldout/`, 189 entries).
- **How it was made.** By hand, from the annotators' hardware-security knowledge, then cross-checked with LLMs (LAsset
  p5). The paper gives no annotation guideline and no rule for what to include.
- **It is a primary list.** The sheet has no primary/secondary column. LAsset scored its own *primary* output against
  it. Its refined primaries score P 0.800 / R 0.901 on the tuning set; with its 1,725 secondary names added, P 0.312 /
  R 0.946. 101 of the 111 tuning entries appear among LAsset's primaries.
- **Every row carries a reason and a CWE list** (112 of 113 tuning rows). LAsset's refinement drops elements with no
  mappable CWE (p4).
- **Known defects.**
  - It was written for an older NEORV32 version in `neorv32_cache`: `inval_i` is today's `inv_i`, and `cache_o.cmd_dir`
    has no counterpart. `assetgen_meta/gt_overlay.py` gives a corrected copy (110 entries); the file is not edited.
  - It is inconsistent across modules. The same kind of concept is listed in some modules and not in others: internal
    FSM state is listed for the bus arbiter and the multiplier, never for the cache, the JTAG TAP, SPI or TWI. 216 of
    the winner's 336 false-positive references in unlisted concepts fall in kinds the reference lists elsewhere. No
    definition can reproduce this part, and nothing is tuned to it.
  - Two annotation conventions (clock/reset inputs and bus-transaction ports are never listed) were checked against
    all 41 modules early on, so the held-out set is not blind to them.

## 2. Definition

An **asset** is a **primary asset** in LAsset's sense (p2, p4): a declared RTL element of the module (a port, a
signal, or a field of an internal record signal) whose own value is data, a configuration, a state or a decision that
the module's behaviour depends on, and that an attacker would target directly to break its integrity, its
availability or its confidentiality.

- A **conceptual asset** is the value or decision itself; its **structural references** are the elements that realise
  it: where it is **stored**, where it **enters** the module from another IP or off-chip (an input the module itself
  reads: "sets"), where it is **computed** or decided, and the output port through which it **leaves** ("exit port").
  One concept usually has several references, each listed as its own entry.
- A **state, setting or decision element realises its own concept.** It is primary in its own right, not a mere
  influence on another value.
- A **secondary asset** is an element that only carries a value, gates it on its way, or holds it only while moving it
  between where it enters and where it leaves. Secondary assets are not reported.
- The **objective** follows what the consumer loses: a wrong value is Integrity (the default), no value or a forced
  value is Availability, disclosure of a designated secret is Confidentiality (rare).

## 3. Conventions, their basis, and where each lives

"Prompt" means the rule may appear in a prompt (it has a basis outside the reference). "Evaluation layer" means it may
only be applied in code after generation and reported as its own labelled row. Page numbers: SA-EDI = Accellera SA-EDI
Standard v1.0 (printed page); P3164 = IEEE P3164 white paper; N&T = Nath & Tan, ISQED 2025 (arXiv 2502.04648).

| Convention | Measured (tuning set) | Basis | Lives in |
|---|---|---|---|
| State, setting and decision elements are primary in their own right | internal deciders 42/150 in the reference (28%) vs data-only 20/283 (7%) | SA-EDI Table 2 type "Control" (p10) and its watchdog example (Annex B, p24-25); P3164 3.1.1 questions 2-4 (p9); N&T control, configuration and status patterns (p3); SAIF lists mode and privilege configuration bits as primary (p2) | Prompt. The seed's lines 15 and 97 (after LAsset p4) treat influencers as secondary: arm `m7e194es0ismd` resolves it |
| Several points of one flow are listed | 57 of 109 entries sit one hop from another entry | P3164 p10, p18; SA-EDI 7.2.1(b) (p13) | Prompt (seed line 13), unchanged |
| An input the module reads, carrying a value in from another IP or off-chip, is where that value is set | single-bit ports 29/55 listed; interrupt and serial pins 6/6 | N&T p1 | Prompt (seed line 13, "sets"), unchanged |
| A register that holds a value only while moving it between its entry and exit is secondary | data-type concepts hold 190 of 558 false-positive references (34%), element precision 0.24; FIFO contents never listed (15 concepts) | LAsset p2 (the AES output buffer is a secondary asset); SAIF p2, example 1 | Prompt: arm `m7e194es0ismd` |
| Pure carriers are secondary | 0 of 12 carrier wires listed | LAsset p2; SAIF p2 | Prompt (seed lines 13, 15, 17), unchanged |
| Bus-transaction ports are secondary | 0 of 118 transaction ports, 0 of their 875 fields | LAsset p2; SAIF p2 | Prompt (seed lines 13, 16), unchanged |
| Clock and reset inputs are not assets | 0 of 45 | none by definition; N&T p6 excludes them from evaluation only | Evaluation layer. Also in the seed (lines 13, 219), kept there for comparability with every arm since the seed |
| Reset generation and memory arrays at rest are not listed | reset generation 0 of 18 concepts; arrays only through their read port | none; P3164 p17-18 and SA-EDI type "Code/Data" count arrays | Evaluation layer, reported as reference-convention rows |
| "Decision inputs" form their own class | single-bit inputs that decide locally 2/10 listed | none | Rejected |
| One element per concept | refuted (see row 2) | none | Rejected |
| A stored register whose only driving records go into whole output ports, none CARRIES, is not an asset (R1a, prompt-optimization iteration 2) | tuning, Claude executor: 21 FP / 0 TP removed on v1 r0, 21 / 0 on r1, 20 / 0 on r2; held-out v1: 23 FP / 8 TP, precision 0.333 vs random thinning 0.329 (24.8% of draws reach it) | none (derived from reference counts); as a prompt rule it contradicted row 1 | Rejected after the pre-registered held-out check (`prompt_opt/HELDOUT_CHECK_PREREG.md`, `eval_layer.py`) |
| Record fields that never sit in a condition are not assets (GUARD) | tuning 23/30 vs 59/241; held-out 11/21 vs 183/524 (gap shrinks from +0.52 to +0.175, interval includes 0) | none (derived from reference counts) | Evaluation layer, in-sample row only, next to an equal-strength random-thinning baseline |

## 4. Scoring policy

- **Headline:** `eval_assets.score(..., strict=True)` against the original reference, primary elements only, mean of 3
  runs, precision and recall named every time. Tuning (15 modules) and held-out (26 modules, run once, see
  `assetgen_meta/HELDOUT_PREREG.md`) are reported separately and never pooled.
- **External comparison row: LAsset initial**, `ground_truth/lasset_initial.json` (`eval_assets.load_refs()["paper"]`),
  the generation stage before LAsset's CWE refinement, scored the same way:

  | Set | Precision | Recall | Emitted |
  |---|---|---|---|
  | tuning 15 (111 entries) | 0.737 | 0.910 | 137 |
  | held-out 26 (189 entries) | 0.734 | 0.862 | 222 |

  Caveats printed with it: LAsset used GPT-5 with specification retrieval and the parsed RTL, on an older NEORV32
  version, and the same group made the reference. LAsset refined (0.800 / 0.901 tuning; 0.791 / 0.862 held-out) is
  shown for context only.
- **Separately reported rows, each labelled:** the corrected reference (`gt_overlay.py`); post-generation code levers
  (majority vote, NONE, back-fill; GUARD in-sample only); evaluation-layer convention filters; precision adjudicated on
  a blind sample (a non-reference figure).
- **Diagnostic only:** primary + secondary (union) scoring. It rewards listing more (v2sec 0.287/0.628 -> 0.220/0.898;
  LAsset refined 0.800 -> 0.312).
- **Adoption bar (Step 1b):** precision >= 0.374 at recall >= 0.83 on the tuning set; held-out per the pre-registration.

## 5. Change control

- A prompt rule must cite a "Prompt" row of section 3. A rule whose only support is a count from the reference goes to
  the evaluation layer and is reported separately.
- No reference identifier and no numeric emission hint may enter a prompt (`meta_tools.check_exec_prompt`).
- Every prompt version writes to its own output folder and has pre-registered readings before it runs.
- Run-to-run noise on the tuning set is about 0.03 in recall and precision; a change smaller than that is not a result.

## 6. Changes 2026-10-02 (arm m7e194es0ist2; logged in RELATION_EXPERIMENTS_LOG.md)

| change | basis | lives in |
|---|---|---|
| Confidentiality is judged by a separate labelling call that answers IEEE P3164's question as the IP developer does: assume the integrator may need the IP's information kept confidential; "yes-assumed" when the value holds or carries data that entered, was generated or computed, and can be observed outside; "no" (with its line) when it holds nothing or is a setting only its own writer reads back. The seed's criterion "require evidence for a restriction on disclosure" is removed from generation: it made confidentiality "no" on 276/276 concepts in m7e194es0ist | P3164 3.1.1 Q1 (p.9) and its worked judgements (pp.11-23); SA-EDI Table 2 "Secret" (p.10) for "yes-RTL" | Prompt (labelling call `cia_instructions.md`); the label does not change the reported list |
| Integrity of values that cross the entity's boundary is assumed when their consumer is not supplied: a value delivered by the entity to a sub-unit or through an output port, or received from a sub-unit, whose user lies in a sub-unit or another IP that is not supplied, is Established for integrity from the lines that deliver or receive it. A value whose users all lie in the entity is judged by its use there. Covers elements that compute, store, set or deliver such a value, never those that only forward or gate it. (A first, unscoped wording also covered every value held inside the entity; a Claude pilot listed 38 elements on uart, precision 0.26, and it was narrowed before any run.) | P3164 3.1.1 Q2 (p.9): the developer assumes integration into an IC that requires integrity protection; P3164 p.10: structural assets are the RTL that produces, stores and transports the value | Prompt (generation, section 5) |
| External comparison rows: LAsset initial is shown in both its runs, spec + RTL (`ground_truth/lasset_initial.json`; tuning 0.737 / 0.910, held-out 0.734 / 0.862) and RTL-only (`LAsset_initial_results/asset_list_neorv32_initial.json`; tuning 0.680 / 0.748, held-out 0.730 / 0.757). RTL-only is the like-for-like row for our RTL-only pipeline (user confirmed which file is which, 2026-10-02) | - | Scoring policy (section 4) |
| Sub-unit connection directions are read from the instantiated entity's port declaration (`traced_inputs.resolve_modes`) | the RTL of the sub-units | Input (map) |
