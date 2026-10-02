**Verdict: the contribution is incremental.** It holds up as an evidence and error-analysis contribution, which suits a workshop like CAD4Sec. It does not hold up as an accuracy contribution. One problem sits above all the others: none of the evidence measures adding the map to LAsset. Every arm adds the map to our own gpt-5-mini generator. So "adding occurrence profiling and a relationship map to LAsset" is not yet a claim the data can carry.

Every figure below comes from the three reports. Some figures are combinations of report figures (sums, ratios, differences), which I computed in this session; these are marked "(derived)". "P" means precision and "R" means recall throughout.

## Claim grades

**C1: "We add a code-built relationship map with occurrence IDs to LLM asset identification for VHDL RTL." SUPPORTED, if you narrow the scope.**
- Evidence:
  - The map is built by code (`step1/code_pairs_v2.py`).
  - Every occurrence sits on its source line: 5,972 of 5,972 on tuning and 11,997 of 11,997 on held-out.
  - Typed relationship records score P 0.988 and R 0.988 on 120 sampled tuning occurrences (212 gold records).
- Gaps:
  - The gold set was written by an LLM, not a human.
  - The held-out map has no accuracy measurement.
  - There is one design (NEORV32) and one parser subset.
- Strongest supported wording: "A code-built relationship map of VHDL RTL in which every signal occurrence has an ID tied to its source line. On a 120-occurrence tuning sample, typed relationship precision and recall are both 0.988 against an LLM-written gold set."
- Do not say "first relation map": LAsset already derives inter-module relationships and a Degree of Influence.

**C2: "Every reported asset is linked to an RTL occurrence and a relationship record that code verifies." WRONG as worded.**
- The checker verified 778 of 951 cited rows (0.818) for gpt-5-mini ist2. That misses the arm's own pre-registered bar of at least 90%.
- Per listed element (derived): 0.879 for ist2, 0.959 for the Claude tuning runs, 0.953 for Claude held-out.
- False positives pass the check too: 0.833, 0.941 and 0.930 in the same three run sets. A verified citation shows the evidence exists, not that the element is an asset.
- The arm that cites occurrence IDs (ist/ist2) is not the adopted stack, and ist lost recall: −0.138 [−0.243, −0.031].
- The adopted stack runs on ism, whose reasoning is free text. There, code matches quotes to occurrences after the fact.
- The ist checker result moved from 0.944 on disk to 0.812 after a rule change.
- Strongest supported wording: "In a traced variant, each decision cites occurrence IDs and relationship records, and a program checks them. 82% of cited rows pass for gpt-5-mini and 95–96% of listed elements pass for Claude. Passing does not separate hits from false positives."
- A second option, which is my reasoning from the NONE definition and not a measurement: "In the adopted stack, every output element carries a code-derived trace path; elements without one are removed." This is true by construction, so present it as a design property.

**C3: "Map-derived post-generation filters raise precision on 26 held-out modules (pre-registered) without losing recall." SUPPORTED, with one wording fix.**
- Majority vote (MV) alone: P 0.350, R 0.857. The adopted stack (majority vote plus the NONE and BF filters): P 0.399, R 0.884.
- Paired change in P: +0.049 [+0.025, +0.080]. The precision gain is pre-registered and the 18 pinned files are unchanged.
- Change in R: +0.026 [−0.021, +0.075]. Say "no measurable recall loss", not "without losing recall".
- NONE removes 46.3 elements per run, 95% of them false positives. BF adds 9.0 per run, 74% of them correct.
- Caveat: about 41% of NONE's held-out precision gain comes from a plain name check that needs no map (derived: 0.352 → 0.366 → 0.386). On tuning that share is 9%.
- Strongest supported wording: "Two map-derived post-generation filters raised held-out precision from 0.350 to 0.399 (+0.049, 95% CI [0.025, 0.080]; pre-registered; 26 modules, 189 reference entries), with no measurable change in recall."

**C4: "Giving the map to the generator does not improve precision and costs recall." Half supported: the precision part holds, the recall part is overstated.**
- Change in P across the three clean comparisons: +0.013 to +0.019. All intervals include 0.
- Change in R: −0.028 to −0.032. All intervals also include 0.
- The model listed 8–10% fewer items with the map (derived). Pooled recall fell by 0.057 to 0.069 (derived), but the paired module bootstrap does not support a loss.
- The only significant recall loss is ist (−0.138), and ist also restructures the whole prompt.
- With 15 modules and 3 runs, this test cannot rule out a recall loss of about 0.10.
- Strongest supported wording: "Adding the map to the generator's input had no measurable effect on precision or recall (15 tuning modules × 3 runs; paired intervals include 0). With the map, the model listed 8–10% fewer items."

**C5: "Hits and false positives share their relationship profiles; structure predicts the reference only weakly on new modules." OVERSTATED as worded; holds once narrowed.**
- All 21 relationship classes appear on both hits and false positives (21 of 21).
- Only 19–26% of false positives have exactly a hit's profile, so "share their profiles" is too strong.
- Leave-one-module-out AUC is 0.615–0.629 from classes and 0.641–0.661 from record types. In-sample it is 0.75–0.81. AUC is a score where 0.5 is chance.
- The population is only elements the generator already listed, on the 15 tuning modules, for two models. "Structure alone" really means this map's relationship features.
- Strongest supported wording: "Among the elements the generator listed, every relationship class occurs on both hits and false positives. Relationship features rank hits above false positives with an AUC of only 0.62–0.66 on modules they were not fitted on."

**C6: "Rules on relationship types transfer partially to new modules (precision up, recall down)." SUPPORTED, with qualifiers.**
- Held-out results for Claude v1: P 0.329 → 0.478 and R 0.931 → 0.640. F1, the balance of precision and recall, goes 0.486 → 0.548.
- The rules dropped 63% of false positives (227 of 359) and 31% of hits (55 of 176) (derived).
- About 78% of the in-sample precision gain carried over (derived).
- Qualifiers: one run, one model (Claude), no confidence interval, and no random-removal control (random removal would keep P at 0.329).
- The recall cost is so large that this is not a usable operating point: 0.640 is below LAsset's RTL-only 0.757.
- Wording: keep the claim, and add "one run, one model, no interval".

**C7: "Precision against the LAsset reference is bounded by labelling conventions that RTL structure does not record." UNSUPPORTED, and partly contradicted.**
- Nothing in the evidence measures a bound.
- LAsset reaches P 0.730 on the same reference from RTL alone. So if any ceiling exists, it is far above 0.40.
- The R5 leak check found zero emissions matching a convention.
- What is supported: 56–69% of false positives fall in design concepts with no reference element at all (D5: 264/468, 364/527, 239/359).
- That fact is consistent with a selection convention, but it is equally consistent with real over-listing. Present the convention reading as an argument, not a finding.

**C8: "An error analysis ties every false positive to the evidence the generator cited, with LLM explanations checked by code." WRONG.**
- The LLM part of the fault reporter was never run. The facts files say "none (code only)".
- Supported wording: "A code-only diagnosis classifies every false positive of the traced runs by:
  - citation status,
  - relationship profile, and
  - whether its design concept has any reference element."
- One more useful negative result: quoting does not separate hits from false positives. A quote of 20 or more characters appears for 92.7% of hits and 92.4% of false positives.

**C9: "This is the first asset-identification method with per-decision source-level grounding." OVERSTATED, close to wrong.**
- Rule-based methods (Nath & Tan, SAIF) are grounded in the source by construction.
- IEEE P3164 cites file and line by hand.
- LAsset's Fig. 5 quotes RTL.
- Strongest supported wording: "To our knowledge, among the asset-identification works we reviewed, this is the first LLM-based security-asset identification method in which asset decisions cite RTL occurrence IDs and relationship records, and code checks each citation against a relation map built from the RTL." Report the 82% pass rate in the same paragraph.
- This conflicts with the related-work report's recommended claim, which says "every asset decision". The ledger shows that "every" fails.

**C10: "Our pipeline reaches higher recall than LAsset's RTL-only generation stage, at lower precision." SUPPORTED on held-out.**
- Change in R: +0.127 [+0.064, +0.186]. Change in P: −0.331 [−0.405, −0.242].
- This is not a map contribution:
  - The base prompt alone gives +0.095 of the +0.127, about 75% (derived).
  - We list 2.1 times as many items (419 against 196).
- F1 is 0.549 for us against 0.743 for LAsset.
- Against LAsset spec+RTL, the recall difference is not significant: +0.021 [−0.044, +0.085].
- Model mismatch: LAsset used GPT-5; we used gpt-5-mini.
- Use the LAsset RTL-only row that is more favourable to them (0.730 / 0.757) and say that you did.

**C11: "LAsset reports recall only / lacks precision or error analysis." WRONG as worded.**
- LAsset reports accuracy, confusion matrices, and false-positive counts per design (Table I).
- Supported wording: "LAsset's headline metrics are recall and accuracy. It does not report precision as a metric or analyse the causes of false positives. Its tables allow precision to be derived (0.74–0.82)."

**C12: "The evidence layer improves LLM asset identification." OVERSTATED.**
- Precision improves only when the map is used as a filter: +0.049.
- As generator input, the map has no measurable effect.
- The citing prompt lost recall.
- Supported wording: say which use, which metric, and the size.

## 1. Degree of contribution
- **Accuracy (precision and recall): incremental, close to negligible against the state of the art.** The +0.049 precision gain is real and pre-registered, but precision stays about 0.33 below LAsset, and the recall lead comes from the base prompt.
- **Traceability and auditability: moderate novelty, unproven value.** Code-checked citations for LLM asset decisions are absent from the reviewed literature. But the checker passes false positives at 83–94%, misses its own 90% bar on gpt-5-mini, and no study shows that it helps a human catch errors.
- **Error-analysis method: moderate.** This is the most defensible line. It is the first counted false-positive analysis against this reference, and it has a clear negative result: the relationship features separate hits from false positives with an AUC of only 0.62–0.66 on modules they were not fitted on.
- **Evaluation method: incremental as a stated contribution.** This covers pre-registration, a module bootstrap, a random-removal control and precision reported for LAsset. Reviewers will read it as rigour that makes the other claims believable, not as a contribution of its own.

## 2. Three threats a reviewer will raise
1. **One design and one reference.** Everything is NEORV32, with 300 reference entries across 41 modules. The reference was written by the LAsset authors with no agreement figure. The map's accuracy gold is LLM-written and covers tuning only.
2. **The traceability claim and the precision claim come from different pipelines.**
   - The citing arm (ist/ist2) costs recall and fails its own bar.
   - The adopted stack (ism plus filters) has no occurrence-ID citations.
   - The checker's definition changed: the ist result moved from 0.944 to 0.812.
3. **The baselines are weak or mismatched.**
   - P is 0.399 against LAsset's 0.730.
   - The recall lead is bought with 2.1 times more items.
   - The models differ: gpt-5-mini against GPT-5.
   - 41% of NONE's gain needs no map.
   - There is no "name check only" baseline, and no recall comparison at an equal list size.
   - 17 tuning stacks were tried on 15 modules.
   - A side question: GUARD is labelled "overfitted", yet its tuning and held-out numbers nearly match (0.451 / 0.793 against 0.446 / 0.801). Explain why it is secondary from the pre-registration, not from the numbers.

## 3. Wording traps with the LAsset group
- **Do not call their reference incomplete or "bounded by conventions"** (C7). Say instead: "56–69% of our false positives fall in concepts the reference does not list. Structure cannot tell us whether these are omissions or out of scope, and we would value your view." Their own paper calls Nath & Tan's reference incomplete, so this point will be sensitive.
- **Do not present the internal mismatches in their Tables I and III** as findings (93.21% against 90.80%, 302 positives against 42). Raise them privately as questions.
- **Do not say** "recall only", "no precision", "outperforms LAsset" or "first VHDL".
- **Frame the work as a layer on top of LAsset, not as a competitor.** Then the experiment in section 4 becomes necessary, because that framing is not measured yet.
- **Use the LAsset rows that are more favourable to them**, and say so.

## 4. The one experiment that would most raise the contribution
Apply the map to LAsset's own published lists.
- **Lists:** the held-out RTL-only list (196 items) and the spec+RTL list (222 items).
- **Step 1, trace:**
  - Attach code traces to every LAsset item.
  - Report trace coverage separately for hits and for false positives.
- **Step 2, filters:**
  - Run the parts of NONE and BF that do not need labels. The "not in map" check works as is. For BF, use the map's own storage and computation records in place of generator labels.
  - Score with the strict scorer and the module bootstrap.
  - Compare against random removal of the same number of items.
- **Before running:** pre-register the thresholds.
- **Cost:** no paid API calls. It uses held-out data already on disk.
- **Why this one:** it is the only test of the actual claim, "adding the map to LAsset". It turns the story from "a lower-precision side pipeline" into "an audit and filter layer on LAsset". The LAsset group lead would also want to see this result.
- **What falsifies it:** hits and false positives get traces at similar rates, and filtered precision does not beat random removal. Then the honest claim shrinks to "audit only".

The runner-up is a small auditor study: do experts spot false positives faster with checked citations? It costs more, and it does not test the "added to LAsset" claim.