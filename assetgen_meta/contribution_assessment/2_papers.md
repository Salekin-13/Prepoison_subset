**Bottom line.** These documents do not contain an automated asset-identification method where each decision cites a source occurrence and a relationship record, and a program checks that citation. They also do not contain a code-built relation map of VHDL. Both are new here. Using RTL structure, giving reasons for each asset, quoting RTL and filtering LLM output are already in prior work, so claiming those as novel would be wrong. The project's measured precision is far below LAsset's own on the same reference. The contribution is the evidence layer and the error analysis, not accuracy.

## LAsset (2601.02624v2, DATE 2026), read in full

**1. Metrics**
- The abstract (p.1) claims up to 90% recall on the SoC and 93% on IPs.
- Table I (p.5) has 14 rows: 3 OpenTitan, 6 OpenCores and 5 NEORV32. For each it gives the reference size, design elements, Init (after generation) and Ref (after refinement), then TP, FN and FP for Spec+RTL and for RTL only.
- TP and FP are given only after refinement. So no per-stage precision or recall can be computed. Only the list shrink is visible: 177 to 157 (Spec+RTL) and 163 to 150 (RTL only).
- Table III (p.6) gives confusion matrices. NEORV32 is reported as accuracy (93.75% and 91.16%). The 21 IPs are reported as recall (93.21% and 90.12%).
- Fig. 6 (p.6) shows recall bars. Fig. 7 and the cost-weighted model-selection score (eq. 2, p.6) cover recall, cost and time for 5 models.
- **Precision and F1 are never reported.** The paper says F1 against Nath & Tan is not meaningful because their reference misses assets such as the SHA-3 round constants rc1 and rc2 (p.6).
- Precision derived from LAsset's own tables (computed this session; transcription self-test reproduced the printed Total row):

| Source | Config | Precision | Recall |
|---|---|---|---|
| Table III, SoC | Spec+RTL | 0.822 (272/331) | 0.901 (272/302) |
| Table III, SoC | RTL | 0.799 | 0.778 |
| Table III, IP | Spec+RTL | 0.747 (148/198) | 0.908 (148/163) |
| Table III, IP | RTL | 0.741 | 0.877 |
| Table I, all 14 rows | Spec+RTL | 0.776 | 0.910 |

- **The paper's own numbers do not agree with each other:**
  - The Table III IP cells give recall 90.80% and 87.73%. The printed 93.21% and 90.12% equal 151/162 and 146/162.
  - SoC accuracy recomputes to 93.60% and 90.69%, not the printed values.
  - For the same design, SoC negatives differ between the two configurations (1088 vs 1051).
  - Fig. 6 SoC recall is 272/300, but Table III has 302 actual positives.
  - In Table I, tiny_aes has Ref ≠ TP+FP.
  - The text says 21 IPs, but Table I has 9 non-NEORV32 rows.
  - Table III has 302 NEORV32 positives, but Table I's NEORV32 rows total 42.

**2. How each asset is justified** (p.3–5)
- Generation uses few-shot examples (AES, GPIO, Gaussian noise generator) with written reasons.
- Refinement has three stages:
  - Attack-scenario analysis over 7 attack classes. Assets with no scenario are dropped.
  - CWE mapping. Assets with no CWE are dropped.
  - LLM self-critique.
- The output (Fig. 5, p.5) has these fields: structural name, security objective, secondary asset, linkage path, Degree of Influence, VHDL entity, functionality, attack scenario, CWEs and CWE reasoning. The scenario text can quote an RTL fragment and name the process it sits in.
- There are no line numbers and no occurrence IDs. Nothing checks by code that a quote exists or supports the claim.

**3. Use of structure**
- The RTL "parsers" are two LLM prompts, one for ports and one for internal signals (p.3).
- Secondary assets come from a function called SecAsset; its method is not described (Alg. 1, p.4).
- Degree of Influence (DoI) is computed along the hierarchy (p.4). Its formula is bits of the secondary asset connected to the primary, divided by the primary's total bits, multiplied along each path.
- The paper calls DoI deterministic and does not validate it (p.5). How it is implemented is not described (unverified).
- Structure scores secondary assets **after** selection. It is never used to accept or reject a primary asset.

**4. How the reference was made** (p.5)
- The authors wrote the NEORV32 reference by hand, "based on our knowledge".
- They cross-checked it with GPT, Gemini and Grok chatbots.
- No annotator count, guideline or agreement figure is given.
- For IPs they used Nath & Tan's public list (p.5), which they also call incomplete (p.6).

**5. Limitations and future work**
- The paper has no limitations or future-work section (conclusion, p.6). "Limitations" appears only about token limits (p.3).
- The only implicit limits are that the spec alone is not enough (p.6) and that Nath's reference is incomplete (p.6).

**6. Claims about explanation**
- The paper says its justifications are explainable and verifiable, and that its rationales are human-readable (p.3).
- It lists trustworthiness, through CWE cross-checks and self-consistency, as a contribution (p.2).
- It says attack scenarios justify each asset to experts (p.4).
- It criticises Nath & Tan for giving no reasoning (p.1).
- The words "traceability" and "auditability" do not appear (searched this session). No explanation quality is measured.

## Other papers

**Nath & Tan (ISQED'25, arXiv 2502.04648)**
- Not an LLM method. It is a Python tool for Verilog/SystemVerilog only (p.5).
- It uses keyword groups per IP family and signal width.
- It sorts signals into four behaviour patterns (control, configuration, status, data) by where they appear: inside if/case/ternary conditions, or on the left or right side of an assignment (p.3–4).
- It traces candidates to the top-level ports through instantiations (p.5).
- Output is a list of assets. Line numbers appear only in the paper's worked example.
- It reports confusion matrices, accuracy, F1 and a true-positive rate of 82.18% (p.6). Derived precision: crypto 0.876, GPIO 0.913, peripheral 0.650 (self-test: 9875 signals reproduced).
- False-positive causes get one short paragraph with no counts: unusual names, misspellings, packages, multi-level instantiation (p.6).
- The reference came from designer docs plus an expert panel (p.5–6). Clock and reset were excluded (p.6).
- Future work lists structural analysis of the source code, CIA labels and CWE mapping (p.6–7).

**SAIF**
- The two SAIF PDFs (SAIF_….pdf and farzana2021.pdf) are the same paper: VTS 2021, same DOI. They differ only in download-watermark lines.
- SAIF finds secondary assets only. The user supplies primary assets and trusted/untrusted output points (p.2–3).
- Structure is used heavily:
  - Fan-out of the asset intersected with fan-in of trusted outputs, after Design Compiler elaboration (Alg. 1, p.3).
  - Fault-simulation observation hardness (p.3–4).
  - Pruning by formal information-flow checks, a side-channel score and a fault-injection score (p.4).
- No source citations. No precision or recall; only counts (10 and 44 assets, Table I, p.5).
- Validation uses correlation on a hand-picked subset (p.5–6). There is no false-positive analysis.
- The HDL is not stated (unverified).

**IEEE P3164 white paper (2024)**
- A manual method, not a standard (p.3). It has two parts: conceptual-and-structural analysis with four C/I/A questions (p.9–10), and points of influence and observation (p.19).
- It cites a file and line by hand for two structural assets: gng_coef.v (p.13) and zbt_top.vhd, a VHDL file (p.18). Its asset JSON has no line field (p.14, p.18).
- It names false-positive and false-negative risk (p.5), and says its first method can flag almost every block (p.16, p.19). Nothing is measured.
- Its framing (p.7) fits this project: "how can one objectively identify, with justification, what an IP asset is?"

**Assertain (2604.01583, MDTS 2026)**
- Generates security assertions; it is not asset identification. It cites LAsset as the asset-identification work (p.1).
- CWEs come from fixed lookup tables (p.2–3).
- An LLM step (GPT-4o) is instructed to remove assertions whose signal names are not in the RTL (p.4–5). This checks names only, and the text describes it as an LLM step, not code.
- No source citations. SystemVerilog only.

**LASP (MLCAD'24, 3670474.3685967)** is the closest prior art, and LAsset does not cite it (checked p.7).
- An LLM identifies assets with a written reason (Table 1, p.5).
- Pyverilog then builds a syntax tree and a control/data-flow graph. This happens **after** asset selection and feeds property generation (p.3–4).
- No source citations. No asset precision or recall (Fig. 2, p.6 gives counts). Verilog only.

**The rest are not asset identification:**
- BugWhisperer (2505.22878): vulnerability detection with a fine-tuned LLM.
- VerilogDB (2507.13369): a Verilog dataset.
- ThreatLens (2505.06821): threat modelling on NEORV32. It says it does no asset extraction (p.4).
- 2310.06046v1: the arXiv version of LLM_for_SoC_Security_A_Paradigm_Shift.pdf (IEEE Access 2024). It is a survey; assets are mentioned only in passing.
- Meta Prompting (2311.11482): general LLM prompting, not hardware.

## What is genuinely not in this prior work
1. **Citations checked by code.** Each asset cites an occurrence ID and a relationship record, and a program verifies both. LAsset has prose plus LLM self-critique. P3164 has hand-written file:line for two examples. Assertain checks names only.
2. **Structure as evidence for the primary decision, and map-derived filters on LLM output.** LAsset and LASP use structure only after selection. SAIF assumes the primaries are given. Nath & Tan use rules, not an LLM.
3. **A code-built relation map for VHDL.** Nath & Tan, LASP and Assertain are Verilog only. LAsset parses with an LLM.
4. **False-positive root causes counted against LAsset's own reference, and precision reported for LAsset at all.**

## What is already there (a novelty claim would be wrong)
- Using RTL structure for asset identification: SAIF, Nath & Tan, LASP, LAsset's DoI.
- Combining an LLM with static analysis: LASP.
- A reason for each asset: LAsset, LASP.
- Quoting RTL inside a justification: LAsset Fig. 5.
- File and line for a structural asset: P3164, by hand.
- Filtering after generation: LAsset drops assets with no scenario or no CWE.
- Claiming explainability: LAsset.
- VHDL support: LAsset claims it.

**This changes an earlier position.** The earlier memory note said no asset-identification work cites the exact source occurrence. P3164 and LAsset Fig. 5 partly do. The gap must be worded as "automated and checked by code", not as "cites source".

## Measured effect, and how to word it
**Measured** (read from the stored assetgen_meta/heldout_readings.json, written 2026-10-01 and not re-run here; I recomputed the LAsset row from its TP, emitted and reference counts). Held-out set: 26 modules, 189 reference assets.

| Row | Precision | Recall |
|---|---|---|
| LAsset initial list (Spec+RTL) | 0.734 (163/222) | 0.862 (163/189) |
| This project, adopted stack (majority vote + drop "none"-path entries + back-fill captured pins) | 0.399 | 0.884 |

Against majority vote alone, the stack gains about 5 points of precision (+0.049, interval [+0.025, +0.080]). Recall changes by +0.026 with an interval of [−0.021, +0.075], so no measurable recall loss.

**Reasoning, not measured.** The two rows are not fully comparable. LAsset used GPT-5 with the spec. The memory notes say this pipeline is RTL only on gpt-5-mini; I did not re-check that. Still, no wording can claim better precision than LAsset. My judgment is that this is an incremental, workshop-level contribution. It becomes stronger if the evidence is shown to separate true from false positives. The memory notes have figures on that, which were not re-derived here.

**Safe wording:**
- "We add a code-built evidence layer to LLM asset identification on VHDL RTL. Each reported asset cites an RTL occurrence and a relationship record that a program checks."
- "Among the asset-identification works we reviewed (SAIF, Nath & Tan, LASP, LAsset, IEEE P3164), none checks each decision's citation by program."
- "We report precision alongside recall against LAsset's manual NEORV32 reference, and assign each false positive to a cause."

**Avoid:**
- "first explainable"
- "first to use RTL structure"
- "outperforms LAsset"
- "first VHDL asset identification"
- "verified assets": a passed check shows only that the citation exists and fits, which is necessary but not sufficient.

## Not verified
- LASHED and the TCAD 2024 SAIF follow-up (Ayalasomayajula et al.) are not in the folder. The TCAD paper must be read before any novelty claim.
- LAsset's GitHub outputs were not checked.
- How LAsset implements DoI is not described in the paper.
- The HDL used by SAIF is not stated in the paper.
- No literature beyond these files was searched.

The script that recomputes LAsset's metrics is <session scratchpad>/contrib/lasset_math.py.