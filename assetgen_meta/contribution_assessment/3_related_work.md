**Verdict: defensible only with "to our knowledge", and only if you narrow it.** None of the 26 works I checked contradicts the claim. That count is a lower bound: it is what my search found, not a full survey. The broad wording "first asset-identification method with per-decision source-level grounding" has three weak spots:

- **Rule-based methods.** Nath & Tan, SAIF and Liu et al. are not LLM-based, so their decisions can be traced by how they are built. Say "LLM-based asset identification".
- **Location reporting is not new.** Two LLM security tools already report source locations, but for bug findings, not asset decisions. LASHED gives a line number and statement for each static-analysis violation. MARVEL gives a file and line for each finding.
- **Deterministic, traceable decisions exist.** RTL-Obliger makes every decision traceable, with no LLM in the decision step. But it works on a graph built from the specification, to guide code generation. It does not identify assets in existing RTL.

**How I checked.** Marks: Y = yes, N = no, P = partial, U = unclear. The columns are (a) per-decision grounding to source locations, (b) reports precision, (c) analyses causes of false positives, (d) handles VHDL. I read the full PDF only for Nath & Tan. Every other mark comes from a summary of the abstract or arXiv HTML made by a fetch tool, so a detail could be missed. IEEE Xplore pages were blocked.

## A. Asset identification (closest to your work)

1. **LAsset.** Hasan, Saha, Hasan, Alam, Uddin, Saha, Tehranipoor, Farahmandi. DATE 2026. https://arxiv.org/abs/2601.02624. Verified (abstract and HTML v2).
   - **What it does:** an LLM finds primary and secondary assets from the spec plus the RTL, or from the RTL alone. Ports and signals are read by "LLM-based parsers". It also derives inter-module relationships and a "Degree of Influence" from bit-level RTL connectivity; the paper does not say which tool does this. Refinement uses attack scenarios, CWE mapping and self-critique.
   - **Output per asset:** conceptual asset, structural asset, security objective, secondary asset, CWE and a justification. No line numbers and no code snippets.
   - **Marks:** (a) N. (b) P: headline is recall (90% on the SoC, 93% on IPs), but Table I lists FP counts per design, so precision can be derived. (c) N: it says LLMs over-list assets but gives no root-cause analysis. (d) P: it claims support for Verilog, SystemVerilog and VHDL. Its NEORV32 case study is natively VHDL (checked on the NEORV32 GitHub), but the paper does not say whether the VHDL or a Verilog conversion was analysed.

2. **Toward Automated Potential Primary Asset Identification in Verilog Designs.** S. K. D. Nath, B. Tan. ISQED 2025. https://arxiv.org/abs/2502.04648. Verified (full PDF read).
   - **What it does:** a rule-based Python tool, no LLM. It uses keyword groups, behavioural patterns of signals, signal width, and tracing up to the top module.
   - **Marks:** (a) N: it outputs a list of assets. (b) Y: confusion matrices per IP family. (c) P: a short list of FP causes (unusual names, spelling, abbreviations, external packages, multi-level instantiation). (d) N: Verilog/SystemVerilog only.

3. **Identifying System-on-Chip Security Assets with Structure-Based Analysis.** W.-K. Liu, B. Tan, K. Chakrabarty. DAC 2025. IEEE document 11133104. Partly verified: title, authors and session confirmed on the DAC program page; the method summary comes only from a search snippet.
   - **What it does:** turns RTL into graphs and classifies assets with a deep neural network. The snippet reports up to 99% accuracy. Not LLM-based.
   - **Marks:** (a) N. (b) U. (c) U. (d) U.

4. **SAIF journal version (Automatic Asset Identification for Assertion-Based SoC Security Verification).** Ayalasomayajula, Farzana, Tehranipoor, Farahmandi. IEEE TCAD 2024. Not verified (IEEE page blocked; search snippet only).
   - **What it does:** non-LLM, vulnerability metrics.
   - **Marks:** (a) U. (b) U. (c) U. (d) U.

5. **SV-LLM.** Saha, Tarek et al. (Farahmandi group). https://arxiv.org/abs/2506.20415, 2025. Verified.
   - **What it does:** its asset agent works from the specification only, with RAG and self-critique. Output fields: name, function, objective, justification.
   - **Marks:** (a) N. (b) N: qualitative case study only. (c) N. (d) N.

6. **CHARGE.** X. Tan, C. Sturton. ICCAD 2026. https://arxiv.org/abs/2607.27776. Verified.
   - **What it does:** walks the CWE hierarchy to ask an LLM for assets, then generates SVAs (SystemVerilog assertions). Assets are output as signal names in JSON.
   - **Marks:** (a) N. (b) N: uses a run-consistency score, not precision. (c) N: analyses false negatives only. (d) N.

7. **LLM-Assisted Detection and Repair of Hardware Security Vulnerabilities in Verilog Designs.** Santana, Gyaase, Zheng. https://arxiv.org/abs/2608.04907, Aug 2026. Verified.
   - **What it does:** a staged LLM pipeline with an asset step. The program dependency graph is built by the LLM, not by code.
   - **Marks:** (a) N. (b) N: no metric for the asset step. (c) N. (d) N.

## B. LLM plus static analysis or code-built graphs

8. **LASHED.** Ahmad, Pearce, Karri, Tan. https://arxiv.org/abs/2504.21770, 2025. A secondary listing says COLM 2025; not verified.
   - **What it does:** the LLM picks assets for each CWE as bare signal names. Static analysis then flags violations, and the LLM filters them.
   - **Marks:** (a) P: each violation carries a line number and statement produced by code, but asset decisions carry no citation. (b) Y: 35 of 40 flagged instances plausible, 87.5%. (c) Y: it names over-liberal LLM asset picks as the main FP source, plus lock-bit confusion and wrong assertion conditions. (d) N.

9. **VerilogLAVD.** Long, Xia, Chen, Kuang. https://arxiv.org/abs/2508.13092, 2025. Verified.
   - **What it does:** builds a property graph by code (Pyverilog AST plus control flow plus data dependency). The LLM writes graph-traversal rules from CWE text. It detects vulnerabilities, not assets.
   - **Marks:** (a) U. (b) Y: precision, recall and F1. (c) P: rule-validity rates only. (d) N.

10. **AssertionForge.** Bai, Bany Hamad, Suhaib, Ren (NVIDIA). LAD 2025. https://arxiv.org/abs/2503.19174. Verified.
    - **What it does:** a knowledge graph built from the spec (by LLM) and the RTL (by Pyverilog), used for functional SVAs. Not security. No link from each assertion back to graph nodes.
    - **Marks:** (a) N. (b) N. (c) N. (d) N.

11. **Assertain.** Tarek, Saha, Hasan, Saha, Tehranipoor, Farahmandi. IEEE MDTS 2026. https://arxiv.org/abs/2604.01583. Verified.
    - **What it does:** the LLM classifies the design and maps CWEs. Code removes any assertion that names an identifier missing from the RTL.
    - **Marks:** (a) N: it checks that names exist, not where they occur. (b) N. (c) N. (d) N.

12. **RTLExplain.** Chi, Mackin, Shi, Vijayaraghavan, Tsai, Degan (IBM). DAC 2025. Verified on the IBM Research page.
    - **What it does:** bottom-up, data-dependency-aware RTL summarisation plus RAG. Not security.
    - **Marks:** (a) U. (b) N. (c) N. (d) U.

13. **LLM-IFT.** Mashnoor, Akyash, Kamali, Azar. VTS 2025. https://arxiv.org/abs/2504.07015. Abstract only.
    - **Marks:** (a) U. (b) N. (c) N. (d) U.

## C. Line-level localisation of bugs (not assets)

14. **MARVEL.** Collini, Ahmad, Ah-kiow, Karri. https://arxiv.org/abs/2505.11963. Venue TODAES per the paper; not verified.
    - **What it does:** multi-agent vulnerability detection. Each finding gives a file and line, reported by the LLM; the paper does not describe a code check of them.
    - **Marks:** (a) Y, for findings. (b) Y: 19 valid, 14 warnings, 18 hallucinated, out of 51. (c) P: agents not backed by EDA tools produced most false findings. (d) N.

15. **TrojanLoC.** Xiao et al. (Karri group). https://arxiv.org/abs/2512.00591, 2025. Verified.
    - **What it does:** line-level Trojan localisation from RTL embeddings.
    - **Marks:** (a) Y, as classification, not citation. (b) F1 only. (c) N. (d) U.

16. **VeriCWEty.** Basu Roy et al. https://arxiv.org/abs/2604.15375, 2026. Verified.
    - **What it does:** line-level CWE detection using embeddings.
    - **Marks:** (a) Y. (b) Y, about 89%. (c) N. (d) N.

17. **CWEEP.** Kwan, Tan. https://arxiv.org/abs/2607.29604, 2026. Verified.
    - **What it does:** lexical static analysis, non-LLM, reports the exact location.
    - **Marks:** (a) Y. (b) P: correct-warning rate 60.8%. (c) U. (d) U.

18. **SoCureLLM** (HOST 2025, eprint 2024/983), **ThreatLens** (VTS 2025, eprint 2025/561) and **SecureRAG-RTL** (https://arxiv.org/abs/2603.05689). All verified.
    - **Marks:** (a) N for all. (b) N for all: detection or accuracy rates only. (c) N for all. (d) U for all.

## D. Traceable or neuro-symbolic decisions

19. **RTL-Obliger / SECRTL-GEN.** Yang, Hu, Chen, Xia. https://arxiv.org/abs/2608.26588, Aug 2026. Verified.
    - **What it does:** the LLM builds a graph from the specification. Deterministic matching against a CWE ontology then infers obligations on signals, and every decision is traceable to matched elements. It also has a secret/internal/public sensitivity label.
    - **Marks:** (a) P: traces to spec-graph elements, not RTL lines. (b) N: pass rates only. (c) U. (d) Y: the benchmark includes VHDL.
    - **Why it matters:** this is the closest work to "traceable decisions". It is why the claim must say "existing RTL source" and "asset identification".

20. **Explainability Methods for Hardware Trojan Detection.** Whitten, Wolff, Papachristou. https://arxiv.org/abs/2601.18696, 2026. Gate level, no LLM.
    - **Why it matters:** it argues that explanations must use circuit terms, which supports why your citations matter.

## E. Surveys, and grounding as an open problem

21. **AI-Assisted Hardware Security Verification: A Survey and AI Accelerator Case Study.** K. T. Hasan, ..., Farahmandi. VTS 2026. https://arxiv.org/abs/2604.01572. Verified.
    - It says "trust, grounding, and hallucination remain central concerns". One research question asks how structured knowledge can ground LLM outputs.
    - It does not single out missing evidence in asset identification as a gap.
    - Its NVDLA case study gives RTL line numbers, but the authors added them by hand. No precision reported. No VHDL.
    - It describes Assertain (#11) as arXiv 2604.01583. I checked that ID: it is Assertain, not a survey.

22. **LLMs for Secure Hardware Design and Related Problems** (Knechtel, Sinanoglu, Karri, ISVLSI 2026, arXiv 2605.10807). **LLMs and Attention-Based AI for Hardware Design and Security** (Ghimire et al., arXiv 2504.08854).
    - Neither abstract names grounding, and neither discusses asset identification.

23. **LLM-based Vulnerability Detection at Project Scale.** Li, Jiang, Chen, Xiong. https://arxiv.org/abs/2601.19239, 2026. Software, not hardware.
    - **Why it matters:** it builds a full FP root-cause taxonomy. Software has this; hardware asset identification does not.

## F. VHDL

24. I found **no 2023–2026 work on VHDL-specific security asset identification**. Only LAsset (claims support), RTL-Obliger (code generation) and VHDLSuite (arXiv 2606.13735, generation only, not opened) touch VHDL. An older precedent is information flow analysis for VHDL (Tolstrup, Nielson and Nielson, 2005); it is outside the date window and I did not open it.

Also noted, not part of the comparison: DeepRTL (ICLR 2025, https://arxiv.org/pdf/2502.15832) is about Verilog understanding, not security. I checked it via search results only.

## How to word it

**Recommended claim:** "To our knowledge, this is the first LLM-based security-asset identification method in which every asset decision cites specific RTL source occurrences, and code checks each citation against a relation map built from the RTL."

**Second claim:** "We report precision alongside recall. An error analysis shows that true and false positives share the same structural profiles."

- I found no work with that second finding. LASHED (#8) and Nath & Tan (#2) only list FP causes.
- *This is reasoning, not a measurement:* the finding questions the premise of structure-based asset identification, as in Liu et al. (#3) and Nath & Tan (#2). That makes it a diagnostic contribution, not just a negative result. It holds for your corpus and model only.

**Do not say:**
- "first explainable or traceable LLM hardware-security tool" (MARVEL, LASHED and RTL-Obliger contradict this).
- "first to combine a relation graph or map with LLMs for hardware security" (VerilogLAVD and AssertionForge; LAsset already derives inter-module relationships and Degree of Influence).
- "first to verify LLM outputs against RTL by code" (Assertain filters made-up identifiers; LASHED uses static analysis). Say exactly what code checks: that the cited occurrence exists and supports the stated relation.
- "first VHDL asset identification" (LAsset claims VHDL support).
- "LAsset reports no false positives" (its Table I has an FP column).

**Gaps in this check:**
- The method summaries for Liu et al. (#3) and SAIF (#4) are unverified.
- The venues for LASHED and MARVEL come from secondary sources.
- Most marks rest on fetch-tool summaries, not my own full read.
- An IEEE-only or late-2026 paper could exist that I did not find. That is why "to our knowledge" is needed.