# Relation annotator experiments (Step 1, 15 test modules)

One change per experiment, each in its own folder under `step1/lasset_step1/relation_exp/`. Numbers are written by `relation_experiments.log_entry()` from the saved answers; the analysis under each entry is added after the run. Metrics: records = relationship records (element, occurrence, type, target); unpartnered = records whose mirrored record is absent, split into omission (the other side wrote nothing for the pair, which the code reference links), type disagreement (the other side wrote a different type) and wrong side (a type from the other end of the pair); element pairs and typed records are agreement with the code reference, not accuracy.

## E0 baseline (2026-09-29 18:01)

Prompt v1 `a44eebd83bf7`, declaration-order batches (at most 20 elements, 85 occurrences), gpt-5-mini medium, v3d profiles. Folders: `relation_out/`, `relation_map/`.

   all 15 modules: records 3935, unpartnered 584 (14.8%: omission 280, type disagreement 255, wrong side 49); element pairs R 96.5% P 95.5%; typed R 79.1% P 90.8%; pairs in one call 26%; check failures 39; 117 calls, at most $4.58
   on the E1 modules (cache, spi, uart): records 1221, unpartnered 272 (22.3%: omission 122, type disagreement 121, wrong side 29); element pairs R 97.4% P 89.0%; typed R 78.6% P 88.9%; pairs in one call 17%; check failures 27; 23 calls, at most $1.06

**Analysis.** Baseline for E1-E4. 71% of the code reference's element pairs have their two sides in different
calls (declaration-order batches); records of such pairs lack a mirrored partner 17.6% of the time (484 / 2,744)
against 8.4% (100 / 1,191) when both sides are written in one call. 83% of the unpartnered records (484 / 584) are
cross-call, so a prompt change inside one call cannot reach most of them: E2 (batching) and E4 (repair) target that.

## E1 noise floor (2026-09-29 18:28)

E0 setup again (prompt v1, declaration-order batches) on cache, spi, uart. Folder: `relation_exp/E1_noise/`.

   E1, second run: records 1174, unpartnered 256 (21.8%: omission 142, type disagreement 106, wrong side 8); element pairs R 96.7% P 93.9%; typed R 77.7% P 91.4%; pairs in one call 17%; check failures 13; 23 calls, at most $1.07
   E0 on the same modules: records 1221, unpartnered 272 (22.3%: omission 122, type disagreement 121, wrong side 29); element pairs R 97.4% P 89.0%; typed R 78.6% P 88.9%; pairs in one call 17%; check failures 27; 23 calls, at most $1.06
   E0 vs E1, same prompt and batches: records 1220 / 1173, differing 381; element pairs 557 / 524, differing 77

## E2 linked batches (2026-09-29 19:31)

Prompt v1 `a44eebd83bf7`; batches from relation_stage.linked_batches (same caps). Folder: `relation_exp/E2_linked/`.

   E2, linked batches: records 3634, unpartnered 689 (19.0%: omission 403, type disagreement 171, wrong side 115); element pairs R 92.8% P 95.5%; typed R 72.2% P 89.7%; pairs in one call 55%; check failures 137; 113 calls, at most $4.47
   E0, declaration-order batches: records 3935, unpartnered 584 (14.8%: omission 280, type disagreement 255, wrong side 49); element pairs R 96.5% P 95.5%; typed R 79.1% P 90.8%; pairs in one call 26%; check failures 39; 117 calls, at most $4.58

## E1 and E2 analysis (2026-09-29 19:48)

Analysis of E1 and E2 (numbers above), with a new headline metric.

**Headline metric changed (from here on):** mirrored typed pairs. An expected occurrence pair of the code reference counts
only when BOTH records exist, with the reference's type and its mirror; precision = the share of mirrored driving
records that match an expected pair. Reason (astra's review, and E1): the unpartnered rate is conditional on what was
written, so a call that writes little looks clean (E2's uart call with load 338 wrote 35 records, 9 unpartnered).
Self-test: sys (97/97 typed, all partnered) scores 100% / 100%. The reference's CONSTRAINS / operand-GATES typing is
approximate, so this is agreement with the reference, not accuracy.

| run | mirrored recall | mirrored precision | typed R / P |
|---|---|---|---|
| E0, 15 modules | 68.4% | 94.7% | 79.1% / 90.8% |
| E2, 15 modules | 60.3% | 95.3% | 72.2% / 89.7% |
| E0, cache/spi/uart | 62.2% | 96.1% | 78.6% / 88.9% |
| E1, cache/spi/uart (identical re-run) | 60.2% | 97.5% | 77.7% / 91.4% |
| E2, cache/spi/uart | 36.2% | 91.7% | 55.8% / 80.0% |

**E1 (noise).** Identical setup, two runs: mirrored recall moves 2.0 points, precision 1.4 points; 381 of 1,387 records in either run
(1,220 and 1,173 per run, 1,006 in both), and 77 of 579 element pairs in either run differ. Component counts move a lot (omission 122 vs 142,
wrong side 29 vs 8, check failures 27 vs 13), so single-run comparisons of components are unreliable; the headline
moves little.

**E2 (linked batches) loses, beyond noise:** mirrored recall -8.1 points on 15 modules and -26 points on the E1
modules (noise: 2.0). It helped bus, cache, cpu_pmp, imem, debug_dtm (unpartnered down) and hurt uart (108 -> 232,
check failures 2 -> 73), twi, muldiv. Mechanism (astra, gpt-6-astra, ~$0.67, verified against the numbers): load
concentration -- calls with more than 120 expected records went from 7 to 15 and from 20% to 58% of all expected
records; heavy calls under-produce (uart 35 of 338, spi 142 of 351, twi 145 of 279; written/expected 0.57 vs 0.85 at
loads 21-60). Load is not the only cause: debug_dtm's call at load 353 did well, and uart's wrong-side records rose
24 -> 105. Linking pairs into one call does cut type disagreements (255 -> 171), as intended, but the load cost
outweighs it.

**Decision:** E3 uses declaration-order batches (BATCHING_E3 = "declaration"), so it changes only the prompt and is
compared with E0 (and E1's 2-point noise). Astra's alternative -- linked batches capped at 120 expected records per
call, with prompt v1 as a control and three repeats per prompt (about $27) -- is parked as a possible E2b.

## Adjudication: code vs LLM relationships (2026-09-29 20:07)

Blind adjudication of E0 disagreements from the RTL.

Question: should the relationship records be written by code instead of the LLM? Method: every E0 (element,
occurrence, target) key where code_pairs and the LLM differ (1,044 of 4,594 keys: code only 673, type differs 270, LLM
only 101) plus agreed keys; stratified sample of 114 (36 / 36 / 30 / 12, seed 20260929). Judges saw the numbered source,
the profile rows and sections 3, 4 and 8 of prompt v1, never the code's or the LLM's answer. Judges: gpt-6-astra on
every item (~$3.73), a second astra call (items reversed) on chunk 0, Claude verdicts on chunks 1-3 (finished before
the switch to astra). Judge agreement: astra vs astra 29/29, astra vs Claude 85/85, Claude vs Claude 27/28; no split
to resolve. Scripts and verdicts: scratchpad adjud/, astra_adjud/, adjud_scored.json.

| stratum (population) | sample | code right | LLM right | both wrong |
|---|---|---|---|---|
| code only (673) | 36 | 27 | 7 | 2 |
| type differs (270) | 36 | 19 | 17 | 0 |
| LLM only (101) | 30 | 14 | 11 | 5 |
| agreed (3,550) | 12 | 12 | 12 | 0 |

Weighted to the 1,044 disagreement keys: code right ~66.5%, LLM right ~28.3%. Weighted to all keys (exact type per key;
true keys missed by both are invisible, so recall is within the union of the two): code precision ~93.4% recall ~95.0%;
LLM precision ~94.7% recall ~84.1%. The agreed stratum carries most keys and rests on 12/12, so the absolute levels are
soft; the code-vs-LLM difference comes from the disagreement strata.

All 42 code errors fall into six mechanical causes (my reading of the judges' notes, checked on Q040 and Q101):
13 statement on several lines (L4 pairs same-line only), 7 several statements on one line, 13 condition typed from the
whole line (cond_type sees the assigned element and "<=", so literal compares become CONSTRAINS), 4 operand-GATES test
stricter than section 3 (_flat_logic demands one flat operator), 2 run-time index inside a condition (rule 7), 3
process variables not followed. LLM errors (67): 29 omitted a true record, 24 wrong type, 14 a record where none holds.
Spec ambiguous: 2 (Q079 variable in a condition, Q087 run-time index in a condition).

Reading (argument, not measurement): the relationship rules are a lookup over SITE, Context and the statement; every
code error found is a fixable parse gap, while the LLM's main error is omission, which E1/E2 showed to be load-bound
and noisy. Recommendation: code writes relationship; the LLM keeps functionality. E3/E4 are paused pending the user.

## E3 pair-first prompt (2026-09-29 21:04)

Prompt v2 `8406f390b729`; declaration batches. Folder: `relation_exp/E3_pairfirst_declaration/`.

   E3, prompt v2, declaration batches: MIRRORED TYPED PAIRS recall 72.7% precision 95.3%; records 3928, unpartnered 390 (9.9%: omission 244, type disagreement 133, wrong side 13); element pairs R 97.0% P 97.3%; typed R 81.3% P 93.5%; pairs in one call 26%; check failures 39; 117 calls, at most $4.83
   same batching with prompt v1: MIRRORED TYPED PAIRS recall 68.4% precision 94.7%; records 3935, unpartnered 584 (14.8%: omission 280, type disagreement 255, wrong side 49); element pairs R 96.5% P 95.5%; typed R 79.1% P 90.8%; pairs in one call 26%; check failures 39; 117 calls, at most $4.58

## E4 repair pass (2026-09-29 21:20)

Repair of E0: each batch holding an unpartnered record re-called with the items appended. Folder: `relation_exp/E4_repair_on_E0/`.

   E4, repaired E0: MIRRORED TYPED PAIRS recall 54.6% precision 95.0%; records 3510, unpartnered 807 (23.0%: omission 463, type disagreement 298, wrong side 46); element pairs R 90.8% P 96.8%; typed R 70.1% P 90.2%; pairs in one call 26%; check failures 23; 117 calls, at most $4.62
   E0 before repair: MIRRORED TYPED PAIRS recall 68.4% precision 94.7%; records 3935, unpartnered 584 (14.8%: omission 280, type disagreement 255, wrong side 49); element pairs R 96.5% P 95.5%; typed R 79.1% P 90.8%; pairs in one call 26%; check failures 39; 117 calls, at most $4.58
   repair calls: {'calls': 78, 'in': 5943972, 'out': 929364, 'minutes': 10.1, 'usd_upper': 3.3447}

## E3 and E4 analysis (2026-09-29 21:48)

Analysis of E3 (prompt v2, declaration batches) and E4 (repair on E0).

Re-derived from the saved answers (mirrored typed pairs, agreement with the code reference, expected 2,696 pairs):
E0 1,843 (68.4% recall, 94.7% precision); E3 1,961 (72.7%, 95.3%); E4 1,472 (54.6%, 95.0%).

**E3 (pair-first prompt v2): small gain, mixed by module.** +4.3 points recall on 15 modules; on cache/spi/uart E3
64.1% vs E0 62.2% vs E1 60.2% (within the E1 noise of 2 points). Better on 9 of 15 modules, worse on 3 (cpu_cp_muldiv
78->68, uart 71->59, wdt 92->70), equal on 3. The gain comes from type disagreements (255 -> 133) and wrong side
(49 -> 13); omission, the main failure, barely moved (280 -> 244), and uart wrote fewer records (538 -> 449).

**E4 (repair pass on E0): rejected.** Recall -13.8 points. The 78 re-called batches wrote 3,145 relationship records
(occurrence x target) against 3,571 before: asked to return the whole batch again with about 14 repair items each,
the model dropped records it had. imem fell 82% -> 14%, debug_dtm 62% -> 37%, twi 75% -> 48%.

**Reading.** Neither a prompt change nor a repair pass fixes omission, the LLM's dominant error; the best LLM variant
agrees with the code reference on 72.7% of pairs. This supports the adjudication's recommendation (code writes
relationship, LLM keeps functionality). Caveat: all figures are agreement with the code reference, which has the six
known gaps; E3's accuracy against a hand label was not measured.

## E3 and E4: astra analysis (2026-09-29 21:56)

Independent analysis by gpt-6-astra.

gpt-6-astra (~$0.42), evidence computed from the saved answers (scratchpad e3e4_evidence.json). Verdicts: E3 adopt, E4 reject; confidence medium.

**Q1.** E3 adds 118 matches (+4.4 recall points): 9 modules improve, 3 regress, 3 tie; changes span −21.2 to +23.0 points. E1's matched-subset rerun shifts recall −2.0 points, with module swings −7.4 to +6.8. E3 gains only +1.9 points on that subset, not clearly beyond noise. Overall precision's +0.6 points is also unestablished. Stronger consistency evidence: subset type disagreements fall 121→38 versus 121→106 on rerun. Inference: E3 likely improves consistency; aggregate recall improvement is suggestive, not statistically established by one three-module repeat. Adopt provisionally as the LLM prompt, not as proven higher RTL accuracy.

**Q2.** Inference: E3 reduces independent type/side decisions, not batch separation: co-location stays 25.9%. Globally, type disagreements fall 255→133 and wrong-side records 49→13. Bus/cfu/pmp combine improved consistency with fewer one-sided omissions; spi gains despite omissions rising 28→71, consistent with type repair dominating. Twi's type disagreements also decline. Coverage competes with consistency: muldiv/uart/wdt emit 22/89/21 fewer records; muldiv omissions and wdt disagreements increase. UART's orphan counts improve while matches fall 241→202: losing both sides can hide missing relationships. Extra bookkeeping displacing exhaustive enumeration is a hypothesis, not a measured cause. The bundled procedure/examples prevent attributing effects to individual prompt components.

**Q3.** E4 failed as a replacement strategy: recalled batches shrank from 3571 to 3145 records (−11.9%); overall omissions rose 280→463 and recall fell 68.4%→54.6%. Inference: complete-batch regeneration redirected attention toward repair items while dropping or changing previously usable output. Fewer check failures did not prevent semantic regressions. Repair remains worth testing as bounded, transactional pair patches against immutable originals, with explicit conflict handling and no silent deletions. Generate mirrors deterministically only after validating the underlying pair; blindly copying a wrong type merely improves symmetry. Orphan-triggered repair cannot recover pairs missing both sides. Reject E4, not every repair design.

**Q4.** Yes, provisionally: fix the six parse gaps, have code resolve canonical typed pairs and render both sides, and retain LLM functionality sentences. E0 adjudication favors code on sampled disagreements (~66.5% versus ~28.3%); those are not overall accuracy rates, and E3 was not adjudicated. Reconsider if replicated E3 or a hybrid materially beats patched code on source-grounded correctness at acceptable cost. Settle this with a blinded, held-out comparison against independently enumerated RTL relationships, including relationships missed by both systems. Measure true mirrored typed-pair precision/recall, per-module uncertainty, and total cost—not agreement with either implementation.

**Q5.** Agreement is trustworthy as compatibility, not as standalone accuracy evidence. Type harmonization and contrastive examples could align both sides with an erroneous reference label: agreement rises while that relationship remains wrong. Switching to another wrong label could lower agreement with correctness unchanged. Completing mirrors can improve the headline without improving semantic inference. Conversely, adding valid dependencies missed by variable/index parsing can lower reference precision while improving accuracy. E0's disagreement proportions cannot calibrate E3's gain because E3 may change the disagreement mix. Blindly adjudicate E3's gained and lost matches against RTL, stratified by the six reference-gap families.

**Q6.** Run one source-grounded bake-off: compare six-gap-patched code, E0, and E3 on independently RTL-annotated, representative held-out entities; report six-gap stress cases separately. Use at least three paired E0/E3 reruns with identical declaration-order batches. Blind scoring should report true mirrored typed-pair precision/recall, module/run uncertainty, and end-to-end cost, including repair calls where applicable. Keep original-reference agreement only as a secondary diagnostic. Predefine the minimum recall advantage at acceptable precision and cost that would justify retaining an LLM relationship writer.


## Bake-off on an astra gold set (2026-09-29 22:58)

Current code vs E0 x3 vs E3 x3, true accuracy on held-out occurrences.

Gold: 120 held-out occurrences (stratified by SITE group, none from the 114-key adjudication), every record listed by gpt-6-astra from the RTL and the definitions, blind; two passes agreed 117/120, 3 resolved; 212 gold records; 5 flagged spec-ambiguous. Typed records (type, target) per occurrence, weighted by stratum, 95% bootstrap CI. Replicates: relation_exp/E0_rep2, E0_rep3, E3_rep2, E3_rep3. Scripts: scratchpad bakeoff/.

| system | typed precision | typed recall | target-only P / R |
|---|---|---|---|
| code (current) | 0.914 [0.872, 0.956] | 0.933 [0.89, 0.97] | 0.974 / 0.994 |
| E0 r1 | 0.954 [0.917, 0.985] | 0.824 [0.733, 0.901] | 0.983 / 0.855 |
| E0 r2 | 0.912 [0.841, 0.97] | 0.846 [0.773, 0.92] | 1.0 / 0.927 |
| E0 r3 | 0.936 [0.877, 0.986] | 0.834 [0.754, 0.916] | 0.991 / 0.889 |
| E3 r1 | 0.993 [0.977, 1.0] | 0.87 [0.787, 0.941] | 1.0 / 0.875 |
| E3 r2 | 0.978 [0.947, 1.0] | 0.915 [0.859, 0.959] | 1.0 / 0.935 |
| E3 r3 | 0.959 [0.918, 0.993] | 0.929 [0.881, 0.969] | 0.993 / 0.961 |

E3 minus E0 (mean of 3 runs each): precision 0.043 [0.013, 0.08], recall 0.07 [0.025, 0.118] -- both intervals exclude zero.

Astra (~$0.22): E3 vs E0 adopt; writer undecided; confidence medium.
**Q3.** Code: EDGE/CASE perfect; errors in LHS/RHS/IF/WHEN. Target-only P/R is 97.4%/99.4% versus typed 91.4%/93.3%. E0: LHS omissions, unstable CASE recall, RHS errors, occasional EDGE/WHEN/IF errors, and typing losses; target recall is 85.5–92.7%. E3: IF/WHEN mostly strong, but LHS/CASE/RHS omissions persist, with one EDGE recall dip; target precision is 99.3–100% and recall 87.5–96.1%. Inference: code’s dominant problem is typing, while LLM pair omissions remain despite E3’s improvements. Aggregate strata cannot attribute errors to individual parse gaps or predict gains from all six fixes.
**Q4.** Undecided: fixed code has not been tested. For point-estimate dominance over every E3 run, fixed code would need typed precision above 99.3% and recall above 92.9%; retaining current 93.3% recall satisfies the latter. That alone would not settle statistical superiority: require paired intervals against E3, or prespecified noninferiority plus operational advantages. Prioritize LHS, then RHS/IF and WHEN; EDGE/CASE are already perfect on this sample. Inference: code is a promising candidate because target recall is 99.4%, but improvement after the six fixes is unmeasured.
**Q5.** Strengths: blinded, held-out, definition-based enumeration; 117/120 exact agreement (97.5%); three adjudicated splits; zero site_wrong flags. Limits: repeated calls to one model are not independent expert validation, and five ambiguities warrant sensitivity analysis. There are only 120 occurrences across 15 modules, with 8–34 samples per stratum. OTHER has ten sampled occurrences, no positive gold records, and 3,411 population occurrences: absence of errors there is weak evidence. Weighting addresses allocation, not annotation bias or unseen failures. Inference: useful comparative evidence, not definitive truth; bootstrap treatment of module and run dependence remains unspecified.
**Q6.** Run one preregistered follow-up: freeze a six-fix code candidate without inspecting gold labels, then compare it with all three E3 runs using paired, weighted typed precision/recall and target-only diagnostics. Prespecify superiority or noninferiority criteria, account for strata and module/run dependence, and report LHS/RHS/IF/WHEN error contributions. Include independent expert review of the five ambiguous items and sensitivity results. If gold labels guide implementation, make the final decision on a fresh held-out sample instead.

Position change: the adjudication (E0 disagreements only) favoured code; on true accuracy E3 beats the CURRENT code on precision and the code's recall lead is not significant, so the writer question is open until a six-fix code is frozen and scored on this gold set.

## Fixed code vs E3 on the gold set (2026-09-30 01:15)

Six-fix code writer, frozen, scored on the held-out astra gold set.

step1/code_pairs_v2.py, written by gpt-6-astra (~$1.75 incl. analysis; an earlier attempt timed out 3x, billing unknown) from the current code, the definitions and the DEVELOPMENT set only (the 114 earlier adjudication keys). Dev self-test 114/114 (current code 72/114), 0 regressions, no repair round. FROZEN sha b0e767000ec2 before scoring on the held-out gold set.

| writer | typed precision | typed recall | target-only P / R |
|---|---|---|---|
| code (current) | 0.914 [0.872, 0.956] | 0.933 [0.89, 0.97] | 0.974 / 0.994 |
| code (fixed) | 0.988 [0.969, 1.0] | 0.988 [0.969, 1.0] | 1.0 / 1.0 |
| E3 r1 | 0.993 [0.977, 1.0] | 0.87 [0.787, 0.941] | 1.0 / 0.875 |
| E3 r2 | 0.978 [0.947, 1.0] | 0.915 [0.859, 0.959] | 1.0 / 0.935 |
| E3 r3 | 0.959 [0.918, 0.993] | 0.929 [0.881, 0.969] | 0.993 / 0.961 |

Fixed code minus E3 (mean of 3 runs): precision 0.011 [-0.003, 0.028], recall 0.083 [0.053, 0.113].

Astra: writer = code (confidence high). Inference: Use fixed code to produce the records. It provides clearly higher recall with no demonstrated precision disadvantage, deterministic output, and a frozen implementation identifiable by SHA b0e767000ec2. Its rules and version history support auditing and reproducibility. Lower marginal cost than repeated LLM calls is plausible, but costs were not measured. LLMs can assist development or error review without becoming the production writer.
Remaining errors: Observed: Residual errors are confined to RHS among evaluated strata: typed precision and recall are both 0.933 there; other populated strata score 1.0. Overall target-only precision and recall are 1.0. Inference: The remaining defects concern relationship typing rather than target identification, although exact failure mechanisms require record inspection. Focused RHS fixes are worthwhile if inexpensive or consequential downstream; prioritize targeted tests and fresh validation rather than broad rewrites chasing perfection.
Threats: Inference: No strong sign of dev-only overfitting: dev coverage improved from 72/114 to 114/114, while frozen code reached 0.988 precision/recall on separate gold. These are different metrics, so the gap is not a direct overfit estimate. Threats include only 120 occurrences, LLM-generated gold with three initial disagreements, unsupported OTHER cases, and only three E3 runs. E0/E3 evaluation on the same gold raises possible prompt-selection reuse concerns. Independent adjudication and fresh designs would strengthen generalization claims.

**Decision: code writes relationship; the LLM keeps functionality.** Settles the open writer question.

## Counter-example checks of the prompt suggestions (2026-09-30 18:41)

Which of the five suggestions survive the data.

Code-only checks (scratchpad relprompt/counterexamples.py) of the five prompt suggestions from the cluster analysis; 15 GT
modules, 111 GT assets, 9 runs (m7e194es0c, ism, ismr), code-written map as the feature source.

A. Map accuracy is not the lever. On the 9 modules all arms finished (70 GT): ism P 0.382 R 0.838; ismr (E3 map) P 0.396
   R 0.738; ismc (code map) P 0.393 R 0.743. Identical within noise: the section costs ~0.10 recall for ~+0.01 precision
   with either map. Do not spend on finishing ismc.
B. Consumed-input lookup (decides / feeds a computation / copied into a clocked register), whole input ports only: passes
   21 of 26 GT inputs (fails dbi_i, firq_i, active_i, rs3_i, ctrl_i), 17 non-GT (8 clock/reset-like names). On record
   fields it passes 88 non-GT and 0 GT: the rule works ONLY with the existing field/transport exclusion. Survives.
C. Wired-only elements: 8 GT of 35 (23%; cpu 7/26). Relating them through sub-block ports would expose 27 non-GT for 8
   GT, below the arm's precision. The seed already finds them from RTL (difficult cluster); the section suppresses them.
   Suggestion dropped.
D. Decision elements toward a GT asset or an output port: 29 GT of 115 (25%); only 2 of the 31 difficult/chance assets
   are decision elements. A keep-decision-elements rule buys ~nothing and costs precision. Dropped.
E. Graph walk from the 79 reliable assets: one hop reaches 218 elements, 4 GT (2%); second hop 183 more, 5 GT. Relation
   neighbourhoods carry no asset signal: the walk is not a discovery procedure. Dropped. (Explains the precision null.)
F. Realization labels, GT share: stores 27% (1324 emitted), computes 34%, sets 46%, exit port 64%. The 'stores' rule is
   the recall engine AND the FP engine; the measured remedy is the post-generation guard filter (memory: 0.344 -> 0.495,
   earlier session, not re-derived here).
G. Reasoning quotes (lower bounds; nested VHDL quotes break the parser): 845 of 2,793 quoted assignments found verbatim
   (30%); TP elements: 43% quote some RTL line, 31% quote one of the element's own occurrences; FP: 42% / 23%. Quotes are
   mostly unverifiable and do not separate TP from FP -> free-text citation is not traceability; closed-set occurrence-ID
   citations verified by code are needed. Corrects the earlier '0 citations' note (0 line numbers, many quotes).

## Agent review of the counter-example checks (2026-09-30 22:44)

Refutation, per-asset diagnosis and design attack.

Four Claude agents (Opus; scripts in scratchpad agents/): two read the generator's reasoning for the 31 hard assets, one
tried to refute checks A-G, one attacked the proposed 'traceable winner' arm. Reversals against the previous entry:

- G REFUTED (my parser was wrong): 1,681 of 1,983 quoted assignments (84.8%) reproduce a full RTL statement verbatim.
  A verbatim span on one of the element's own occurrence lines: TP 76.0%, FP 70.7%. Quotes are real.
- A WEAKENED: numbers reproduce, but in cpu, where the recall is lost (R ism 0.810, ismr 0.429, ismc 0.500), the two maps
  are identical (22 records, 0 differences), so map accuracy is untested there. The section's recall cost is real when
  pooled (+0.098, permutation p 0.048) and nearly absent on the 6 peripherals (ismr 0.846 vs ism 0.862).
- E WEAKENED in wording: a walk adds GT at the base rate (1.8% vs 1.9%), so it is not a discovery step; but assets do
  cluster (neighbours of a GT element are 21.5% GT against 6.6% overall).
- B, C, D, F STAND (entity-level counts: C 8 of 37, D 30 of 116 with 2 of 26 difficult/chance). B status quo: the winner
  finds 18, 16, 16 of 26 GT whole inputs with 10, 9, 8 non-GT; the lookup adds 4-8 GT and 8-10 non-GT per run.
- ARM DESIGN FLAW: ismr/ismc gave map line numbers from the ORIGINAL file next to unnumbered comment-stripped RTL (0 of
  5,760 lines keep their number); line references pointed at nothing the model could see.
- 'Traceable winner' arm REJECTED: the occurrence index is the same 1,572-name list that added +71.6 emissions per run
  (P-2) and port-field FP 0 -> 51.7 (v2p3c1); a field for dropped elements matches v2sec (R 0.925 -> 0.628); the seed
  forbids excluded cases (L269); ID validity with an index is 99.7-100%, so its success test could not fail.

Hard-asset causes (31): realised elsewhere 12, concept not formed 6, rule ambiguity 5, GT convention 5, exclusion fires 2,
map-section suppression 1. 61 of 135 module outputs list no whole input port; 30 of 46 misses of 9 input ports fall in
those. GT names cache_o.cmd_dir and inval_i do not exist in the RTL (inv_i is found 6/9 and scored FP). Per-asset report:
assetgen_meta/hand_arms/hard_assets_diagnosis.md.

Next step adopted as recommendation: build the trace AFTER generation, in code, on stored outputs (quote -> occurrence ID
-> relationship records -> label confirmation). Measured on ism: full path for 186 of 282 TP (66.0%) and 193 of 538 FP
(35.9%); map caps it at 87.2% of TP (36 TP are sub-block-driven signals with no record). P/R unchanged.

## Trace module, blind audit, input-port sentence review, GT overlay (2026-09-30 23:49)

Agent-built trace + its falsification test.

Four Claude agents (Opus). Scripts: scratchpad agents2/.

**Trace module built:** assetgen_meta/asset_trace.py (new file) + traces/<version>/{r0,r1,r2}/<module>.json,
trace_report.md, summary.json. Self-test: 12 hand-read lines in 4 modules (one hand count was wrong and corrected),
5,760/5,760 occurrences found on their stripped line, invented statements rejected. Reproduces the prototype exactly on
m7e194es0ism (full path TP 186/282, FP 193/538; label confirmed 246/282, 338/538); its stricter matcher removes 7
spurious "full" paths on the other arms (whole-identifier match, fragment length). Other arms: m7e194es0c full 159/262
TP, 175/429 FP; m7e194es0ismr 175/259, 196/475. As filters (not adopted): full-only P 0.491 R 0.559; confirmed-only
P 0.421 R 0.739. Known limits: partial quotes cannot separate a shortened real quote from an invented one (TP 11, FP
17 full paths rest on them); identical text on two lines is ambiguous (TP 8, FP 13); the map has no column positions;
exit port is confirmed by direction alone (never separates TP/FP); storage "mixed" never confirms stores.

**Blind audit (the pre-registered falsification test, fail if > 2 of 20 TP wrong):** two independent auditors, blind to
TP/FP, 30 items (20 TP + 10 FP with full paths): 30/30 ok from both, identical verdicts. PASSED. Note: the 10 false
positives also check out, i.e. their cited line and record really show the labelled behaviour: a full path shows
evidence exists, not that the reference agrees.

**Input-port sentence: NOT WORTH RUNNING (reversal of the earlier '4-8 more correct inputs per run').** The reviewer
measured: 154 whole input ports in the 15 modules, 26 GT; 83 are tested in a condition or drive a decision record; 67
of those are excluded by role (22 clocks, 25 resets, 2 clock-enables, 18 transport records); 16 remain: 7 GT and 9
non-GT. The winner already hits the 7 GT in 18 of 21 run-slots and misses none in 2+ runs; upper bound +1 correct per
run. Of the 9 non-GT, 6 are already reported (FP) and 3 could be added. The unstable GT inputs are the 19 UNTESTED ones
(interrupt and serial-data inputs; the winner misses 25 of 57 slots), which the sentence cannot reach. Reviewer verdict
'revise', with a wording that keeps the Established gate and the clock/reset exclusion; conflicts: seed L13-15 make
gating secondary for every element, L97/L214 forbid promoting influence, the draft's trigger described a clock-enable.

**GT overlay (assetgen_meta/gt_overlay.py):** the reference was written against another NEORV32 version for cache
(neorv32/rtl/core = hw 01.11.00.06 has inval_i; RTL_data = 01.11.04.03 has inv_i, same port). cache_o.cmd_dir exists in
neither. Corrected reference = 110 entries; recall +0.010 to +0.017, ranking unchanged (winner 0.344/0.847 ->
0.348/0.864).

## Captured-input rule: review and arm m7e194es0ismcap (2026-10-01 00:25)

One-bullet recall repair for sampled inputs, built and pre-registered.

Two Claude agents (attacker + independent recount; scratchpad agents3/). Rule idea: an input captured into a register of
this entity is a setting point (the generator credits the sampling register, never the pin).
Counts (both agents, all reproduced): 154 whole input ports, 26 GT; captured into a clocked register (map, strict) 16 =
10 GT + 6 non-GT; RTL one-hop reading 36 = 14 GT + 22 non-GT (adds 14 transport records and 2 clock-like). The winner
misses 8 GT inputs in 2+ of 3 runs; the rule covers 4 (jtag_tms_i, spi_dat_i, sys enable_i, uart_rxd_i), 5 under the
one-hop reading (twi_sda_i). Not reachable: firq_i (only a port map), active_i and rs3_i (never read).
Attacker: draft REVISED. Dropped "report the register as well" (+6.7 FP/run, 0 GT: the 15 capturing registers are
reported 11/15 already and only 2 are GT). Restated the clock/reset/transport exclusions in the bullet (else 3
clock/reset pins and 19 record-typed ports qualify; the map types rstn_wdt_i/rstn_dbg_i as CARRIES+GATES, so no map
filter catches them). Quota risk handled by phrasing it as a narrowing of L218, naming nothing to report. Basis: seed
L13, L57, L216; P3164 3.1.2 and p8. Prompt checks PASS on the assembled prompt.
Mechanical bound (re-scoring the winner's runs): +3.3 to +4 GT, +1.7 non-GT per run -> P 0.355/0.337/0.362, R
0.892/0.847/0.910; failure cases +4.3 (clock/reset slips), +21.3 (transport slips), +8.3 (registers listed).
ARM BUILT: hand_arms/m7e194es0ismcap (sha e1c7d09ba571; one inserted line after seed L218; RTL-only input); notebook
cells 26-29; pre-registered readings hand_arms/read_cap_arm.py (baselines on the winner: target inputs 2/12, captured 11
GT 21/33, clock/reset 1/9, first-stage registers 0/15, new-FP 4/9, pmp ctrl_i 2/3, transport 0/168, emitted 273.3/run).
Falsified if the 4 target inputs reach <= 4 of 12. Needs OpenAI credit (about 54 calls).

## Arm m7e194es0ismcap: result and trace-based analysis (2026-10-01 02:41)

Captured-input bullet: falsified at the pre-registered line; trace locates the weaknesses.

Run complete (18 modules x 3, sha e1c7d09ba571). Score: P 0.355 R 0.829 vs winner 0.344 / 0.847; Step 1b verdict: does not
count (R < 0.83). Corrected GT (110): not recomputed here. Pre-registered main test: the 4 target inputs 4/12 vs 2/12,
falsified at <= 4 -> FAILED (sys enable_i 1->3, spi_dat_i 0->1, jtag_tms_i 1->0, uart_rxd_i 0->0). All 11 captured GT
inputs 21/33 vs 21/33 (muldiv rs1_i, rs2_i lost 1 each). Guards held (clock/reset pins 0/9, first-stage registers 1/15,
transport 0/168, pmp ctrl_i 3/3) but the list missed clkgen_i: spi/wdt/uart 1/1/0 -> 3/3/2 slots, labelled 'sets',
plus its riders prsc_tick, cdiv_cnt (clock-generator package 10 -> 20 FP slots). Emitted fell 273.3 -> 259.3 per run.
Three Claude agents (scratchpad agents4/; every number re-derived, self-tests passed):
- Noise: 20-way permutation over the 6 runs; GT slots -6 (p 0.40, ~1.1 SD), recall -0.018 (p 0.40), precision +0.011
  (p 0.20); only FP slots -36 and emitted -14 reach the floor p 0.10. Movers (>= 2 slots): 3 observed, 1-7 under
  reshuffling, expected 4.7 -> the GT movement is noise. Losses: bus state (one run without the FSM concept), jtag_tdo_o
  (the IDCODE concept not formed in 2 runs), dbi_i (never named; forwarded to a sub-block) - noise / unclear.
- Where the bullet worked: sys enable_i (register en reported 3/3 in both; the winner named the pin but listed it 1/3;
  the arm lists it 3/3 in the same concept, path full, L129) and spi_dat_i arm r1 (a new 'sampled input' concept
  quoting the capture line L310). Where it could not: uart_rxd_i and spi (other runs): the RX concept is anchored
  DOWNSTREAM (FIFO write L305/L244, readback L217/L174, FIFO port map); the capturing register rx_engine.sync is
  reported 0/6 and sreg 2/6; the value is realised at the FIFO boundary, a sub-block, so there is no storing element
  of this entity to attach the pin to. jtag_tms_i: its stored effect is a decision (TAP state, L123-138), not a
  captured value; seed L215 pulls against it. Over 17 captured non-clock inputs: the pin is listed in the same
  concept as its register 21/30 (winner) vs 28/36 (arm) slots when the register is reported; never otherwise.
- The bullet's words appear ~0 times in the reasoning ('setting point' 0/364 concepts), so text cannot show it fired.
- FP accounting: of the -36 FP slots, ~28 are explained by writing less (42 fewer emissions at the winner's TP mix);
  ~8 are a real mix change. Vanished FPs are mostly sub-block connection fields quoted only via port-map lines (cpu
  ctrl.csr_* 3->0 x4, trng fifo.we/wdata, twi fifo.tx_free): trace path 'none' (precision 0.01-0.07 in all four traced
  versions). twi io_con.*_ff 1->3 is a name-form change ('io_con.sda_in_ff(1)' -> bare name), net 0.
- Trace-located weaknesses: (1) 44% of the arm's FPs have a FULL evidence path (registers the RTL really stores that
  the GT omits: ctrl.cpha/cpol, ctrl.irq_*, data_mem_b*, mem_ram_b*) - not removable by evidence; (2) path 'none' FPs
  (71 slots in the winner, precision 0.01) - removable by code; (3) misses concentrate where the path is weak: GT
  entries whose best path is 'quoted, not confirmed' miss 38% (16/42) vs 7% for 'full'; that group (cpu alu_add,
  lsu_mar, lsu_err, lsu_wait ... connected only through port maps) carries the whole net recall change.
VERDICT (critic): INEFFECTIVE. Keep m7e194es0ism as the base. Next steps ranked, all counter-example-checked in code:
#1 code filter: drop path 'none' elements (W 0.344/0.847 -> 0.376/0.844; costs 1 TP slot); #2 code back-fill of input
pins whose value reaches (<= 2 hops) a reported stores/computes element (W -> 0.349/0.874; adds 9 GT / 4 non-GT slots;
combined with #1: the winner passes P >= 0.374 at R >= 0.83); #3 map: add port-map association records so the 21
port-map-only elements (5 GT) can be confirmed instead of all landing in 'quoted, not confirmed' (not a filter: dropping
them costs 11 TP for 21 FP).

## Engineer prompt v1: blind analysis from RTL + relation map (2026-10-01 03:23)

Seven blind analysts, engineered prompt, scored against GT; audit of the model's reasoning.

`engineer_prompt_v1.md` is a prompt written from the task alone (IEEE P3164's four questions applied to flows drawn
from the relation map's typed edges; roles stores / sets / computes / exit port; influence points reported separately),
not from any tested asset prompt. It passes the project's prompt checks (no corpus identifier, no numeric hint, no use
of comments).

Seven blind Claude analysts (Opus), one per module, saw only the module's comment-stripped RTL with original line numbers
and its code-written relation map (`step1/lasset_step1/relation_map_code/b0e767000ec2_func-8406f390b729/`), plus the prompt.
Scored afterwards against the ground truth (strict names), primary elements only, and with the secondary list added:

| module | GT | engineer primary P / R | with secondary R | winner m7e194es0ism P / R (mean of 3 runs) |
|---|---|---|---|---|
| hwspinlock | 2 | 1.00 / 1.00 | 1.00 | 1.00 / 1.00 |
| wdt | 8 | 0.57 / 1.00 | 1.00 | 0.55 / 0.96 |
| cpu_cp_muldiv | 12 | 0.44 / 0.67 | 1.00 | 0.56 / 0.86 |
| cache | 6 | 0.05 / 0.33 | 0.67 | 0.11 / 0.50 |
| sys | 2 | 0.00 / 0.00 | 0.00 | 0.13 / 0.67 |
| debug_dtm | 5 | 0.22 / 0.80 | 1.00 | 0.20 / 0.80 |
| spi | 8 | 0.32 / 1.00 | 1.00 | 0.25 / 0.83 |

All 7: primary P 0.262 R 0.744 (tp 32, fp 90, GT 43); primary + secondary P 0.204 R 0.907; winner P 0.294 R 0.814.
Every primary citation (122 of 122) resolves to a real occurrence id of the element in the map.

What the reference counts that the P3164 primary framing demotes to "influence": start strobes (mul.start, div.start),
sign flags (ctrl.rs*_is_signed), the TMS pin, a write enable (we_i), a hit flag (cache_i.sta_hit). What the analysts
report that the reference omits: every stored or exported point along a flow (data arrays, FIFO fields, config bits
such as ctrl.cpha/cpol/strict, reset outputs, DMI request fields). sys: the analyst answered all four questions "no"
for the clock-enable path (the reference's two assets) and reported the reset generator instead.

Files: results/<module>.json (flows, four-question answers, primary/secondary/excluded with occurrence ids, map
assessment, process notes); scores.json; model_reasoning_audit.json (audit of the winner's and the map arm's reasoning
on the same modules); build_packs.py, score_results.py. Log: step1/lasset_step1/RELATION_EXPERIMENTS_LOG.md.

## Four-question arms ismq / ismrq: result (2026-10-01 05:00)

Asking C/I/A/U per value with a required negative, on both prompts.

Arms m7e194es0ismq (winner + four questions, sha 4629c6a2e3a2) and m7e194es0ismrq (map arm + the same, sha 24a1ac5f1f71),
3 runs each, 15 GT modules. Run note: 2 of 108 module-runs (ismrq) emitted the literal string 'excluded values": [] }'
inside the concept list; meta_tools now treats a malformed concept list as unparseable (re-called) and validate/flatten
skip malformed entries.
Scores (mean of 3): ismq P 0.352 R 0.754 emitted 237.7/run (winner 0.344 / 0.847 / 273.3); ismrq P 0.360 R 0.697
emitted 215.0 (ismr 0.353 / 0.778 / 244.7). Recall -0.093 and -0.081: far beyond the 0.03 noise; precision +0.008 /
+0.007: within noise. Majority vote: ismq 0.351/0.775, ismrq 0.393/0.712.
Compliance: four answers on 100% / 98% of concepts; 99% of yes-statements verbatim in the RTL (594/602, 729/739).
But the answers do not discriminate: integrity yes 327/331 and 351/353; confidentiality yes 0/331 and 0/353;
availability yes 60% / 72%; undermined yes 23% / 38%. Objective mix unchanged (Integrity 327, Availability 4). A value
is excluded only when all four are no, which needs integrity = no: 4 and 2 cases. Excluded values 22 / 18 in total
(0.5 per module-run); of those, 3 / 5 name a GT asset (1.0 / 1.7 per run; pre-registered fail line 1: ismrq fails,
ismq on the line): jtag_tdo_o, trng data_o, pmp ctrl_i, cfu active_i, rs3_i, trng fifo_clr, enable.
Where recall went (GT run-slots 282 -> 251; 259 -> 232): diffuse. Concepts/run 116 -> 110, structural refs/run 288 ->
275 (ismq); losses include RELIABLE assets (bus state 6->3, keeper.halt 3->1, keeper.cnt 3->1, jtag_tdo_o 3->1) as well
as difficult ones (trng fifo.re 3->0, cpu alu_add / lsu_mar / dbi_i 2->0); ismrq lost muldiv rs1_i / rs2_i 2->0,
valid_o 3->1, pmp addr_ls_i 3->1. Gains: sys enable_i 1->3 (ismq), trng fifo.re 0->3 and spi_dat_o 1->3 (ismrq).
Reading: the schema change made the model write less (the T-1 effect in reverse), while the one default argument
survived inside the new form: it answers 'integrity yes' with a real quote for any used value, and 'confidentiality
no' for everything, so the required negative is trivial and no exclusion of substance happens. VERDICT: harmful as
built (recall), no precision gain; do not adopt. The blind engineers answered integrity yes on 33/33 too; their
selectivity came from considering fewer values and writing 139 reasoned exclusions, a step this arm did not create.

## Reanalysis of next steps: levers, GUARD overfit, residual errors, held-out plan (2026-10-01 05:36)

All code levers on one footing; GUARD fails out of sample.

Scope: every post-generation lever on the 6 prompt versions of the seed family (18 runs, 15 tuning modules, strict).
Script scratchpad levers/levers.py (self-test reproduced base 0.344/0.847, MV 0.357/0.874, NONE 0.376/0.844 and the
guard separator 23/30). Three Claude agents (scratchpad agents5/, self-tests passed): guard adversary, residual errors,
held-out planner.
Lever table on the winner (mean of 3 runs unless MV): base 0.344/0.847; NONE 0.376/0.844; BF 0.350/0.874; GUARD
0.451/0.793; NONE+BF 0.382/0.871; MV 0.357/0.874; MV+NONE+BF 0.394/0.901 (passes the Step 1b bar); MV+NONE+GUARD+BF
0.495/0.829 (misses the bar by one entry; with order NONE, BF, GUARD: 0.500/0.847). Every lever moves all 6 prompt
versions the same way (GUARD +0.09..+0.11 P; BF +0.02..+0.07 R). The 6 prompts span base P 0.344-0.379 only. Pooled
voting over 18 runs peaks ~0.37/0.86 (no better than one prompt + levers). Union recall over 18 runs 0.955; the 5 GT
never reported are GT-side.
GUARD is OVERFITTED (reverses the memory note 'the win is a post-generation guard filter'). Its premise on held-out GT
with a code condition detector (calibrated 271/271 against the profile definition): GT fields in a condition 11/21 =
0.524 vs non-GT 183/524 = 0.349, gap +0.175, 95% [-0.09, +0.44], Fisher p 0.08; tuning 23/30 vs 59/241, gap +0.52.
The recorded non-GT rate 19% (45/241) does not reproduce: 59/241 = 24.5%. About 70% of GUARD's in-sample precision gain
is plain thinning of record fields (a random rule of equal strength gives 0.419/0.703). It removes 6 GT data/config
assets (keeper.err, div.res, tap_reg.dtmcs, fifo.re, ctrl.baud, ctrl.prsc). Coding style: the module enable bit is
in a condition in all 4 tuning peripherals but gates through logic in 3 of 5 held-out ones. Report GUARD only as an
in-sample, GT-derived row.
Residual errors after MV+NONE+GUARD+BF (TP 92, FP 94, FN 19): blind adjudication of 40 of the 94 FPs: 21 plausible GT
omissions (16 strong), 19 model errors (8 carriers, 4 intermediates, 7 no C/I/A consequence); about half the model
errors are constructs the GT counts elsewhere. Adjusted (non-GT) precision if omissions count: 0.76 [0.70, 0.82].
GT precision ceiling if all model errors vanished: ~0.65; if only the ~21 separable ones (decode / edge / sync
intermediates, protocol mechanics): ~0.56. No code-feature family removes FPs without losing TPs (0 of 94; every family
costs >= 3 TP). FN: 5 GT-side, 6 removed by GUARD, 2 by lever order, 6 model misses.
Held-out plan: every lever can run on CODE alone. A code SITE tagger reproduces the LLM profiler on 5,734/5,760 tag
sets and 1,641/1,641 condition memberships; maps (4,418/4,418 records), traces (820/820) and all lever results are
identical to 3 decimals. Only the executor needs the API: 78 calls, estimated $2.8-4.1 (the profiler would add 350
calls, ~$7-9, and is not needed). Leak: clock/reset/transport conventions are known on held-out; only filter DELTAS
are a clean test. Pre-registered: R1 adopt MV+NONE+BF if its precision gain over MV has a 95% interval above 0 and
recall >= 0.83; R2 GUARD only if it also passes recall; R3 per-filter falsifiers (NONE removes >= 90% FP; GUARD better
than random thinning; BF additions).

## What 'asset' means: the reference's measured definition and its basis (2026-10-01 06:06)

Conventions measured, union scoring rejected, basis per convention.

Question: what should 'asset' mean before further tuning? Tuning set only (15 modules, 111 GT); held-out untouched.
Scripts: scratchpad definition/conventions.py, role_filter.py; two Claude agents (scratchpad agents6/: theory basis from
the local PDFs of LAsset, Nath & Tan, SAIF, P3164, SA-EDI; concept vocabulary of the winner's 349 concepts).
THE REFERENCE: the LAsset repo's manual list has no annotation guideline (LAsset p5: built by hand from 'knowledge of
hardware security assurance', cross-checked with LLMs), no primary/secondary column, and a reason + CWE list on 112/113
tuning rows. LAsset scored its own PRIMARY list against it: refined primaries P 0.800 R 0.901 (125 listed) on the tuning
set; with its 1,725 secondary names added, P 0.312 R 0.946. 101/111 GT entries appear as a LAsset primary.
UNION SCORING REJECTED (reverses my 2026-10-01 'or score primary+secondary' option): v2sec primary 0.287/0.628,
primary+secondary 0.220/0.898 (454 emitted/run, below old baseline v2 0.251/0.925); engineers 0.262/0.744 -> 0.204/0.907.
'ONE ELEMENT PER CONCEPT' REFUTED (my earlier characterisation): 57 of 109 GT entries have another GT entry one hop away.
The winner's FP references: 60% (336/558) in concepts with no GT entry, 40% in concepts that have one.
ROLES (GT rate, code map): input used in a decision 6/17; register that decides 29/87; output port 21/95; wire that
decides 13/63; input data-only 15/108; register data-only 6/59; wire data-only 8/110; wired-only 6/102; carrier 0/12.
Internal deciders 42/150 (28%) vs internal data-only 20/283 (7%). Single-bit ports 29/55, multi-bit 18/149. 'Decision
input' does NOT hold for single-bit inputs (2/10 decide-locally GT, 6/6 data-only GT: interrupt and serial pins).
An in-sample drop of data-only wires gives 0.397/0.775: a thinning trade, not proposed.
CONCEPT VOCABULARY (349 concepts, 14 types, 124 hand-corrected): listed = software knobs (enable 15/16, rate/deadline
9/9, protection settings 12/12, key 3/3), boundary hand-offs (IRQ 11/11, valid 6/6, results 19/24, operands 8/10, pins),
decision points (counters/timeout 9/9, selects/grants 14/18, requests/starts 15/20, signedness 3/3). Never listed (post
hoc kinds, 0/56 concepts): reset generation (18), FIFO contents (15), engine busy/done (8), secondary mode bits such as
CPHA/CPOL, strict, flow control (7), bus lock-hold, datapath intermediates, entropy internals: 120/558 FP refs (21.5%).
Rarely listed kinds add 171 (30.6%). 216 of the 336 wrong-concept FP refs fall in kinds the reference lists in OTHER
modules (e.g. FSM state listed for bus and muldiv, never for cache, TAP, spi, twi): annotator inconsistency.
DATA type: 190 of 558 FP refs (34%), element precision 0.24; CLKRST 48 refs, element precision 0.11.
BASIS per convention (agent, page-cited): deciders primary in their own right = basis (SA-EDI Table 2 'Control', P3164
Q2-Q4, Nath & Tan control/configuration/status) but CONTRADICTS the seed's L15/L97 (influencers are secondary, after
LAsset p4); several points per flow = basis, already in the seed (L13); data held only in transit (FIFO data, shift
registers, buffers) is secondary = basis (LAsset p2, its AES output-buffer example), new; carriers and transaction
ports secondary = basis, already in the seed; clock/reset inputs, reset generation, memory arrays at rest = no
definitional basis -> evaluation-layer convention rows only (Nath & Tan p6 precedent).
LAsset's admission test (agent reading p4): refinement drops assets with no mappable CWE; every reference row carries a
CWE. The generation stage alone has never been compared with a CWE-gated refinement in this project.

## ASSET_DEFINITION, held-out pipeline, definition arm (2026-10-01 07:01)

Built and pre-registered; nothing run yet.

User decisions: write ASSET_DEFINITION.md; implement step 2 (held-out validation of the code levers) and step 3 (one
prompt arm with the definition's basis-backed rules); the external comparison is LAsset INITIAL (lasset_initial.json,
no CWE refinement), not a CWE-gated refinement of our own.
LAsset initial, strict scorer: tuning 15 P 0.737 R 0.910 (137 emitted, TP 101/111); held-out 26 P 0.734 R 0.862 (222
emitted, 163/189). LAsset refined: 0.800/0.901 and 0.791/0.862. Caveats: GPT-5 + spec retrieval + parsed RTL, an older
NEORV32 version (it names inval_i), and the same group made the reference.
1. assetgen_meta/ASSET_DEFINITION.md: the reference, the definition (LAsset primary asset; state/setting/decision
   elements primary in their own right; transit registers secondary), the basis table, the scoring policy.
2. Held-out pipeline (Claude builder + reviewer, 7/7 review checks pass): step1/code_site_tags.py (code SITE tagger;
   5,734/5,760 tuning rows equal the LLM profiler, 1,641/1,641 condition memberships; 75/75 hand-read occurrences),
   step1/build_heldout_code_map.py (15 tuning maps rebuilt from code tags equal the stored ones on 1,641/1,641 elements;
   26 held-out maps: 1,713 elements, 5,934 relationship records, no model), assetgen_meta/post_levers.py (frozen MV,
   NONE, BF, GUARD; reproduces all 17 tuning stacks and the LAsset initial row to 3 decimals), heldout_readings.py,
   HELDOUT_PREREG.md (18 pinned sha12s; read() refuses on any change, any mismatching run folder, or a second reading).
   Minimal edits: meta_tools.run_dir/run_version gain stem and parsed_dir; asset_trace gains stem and rtl_dir; defaults
   reproduce the winner's 54/54 trace files byte for byte. parsed_heldout26/ closed sets. No held-out P/R computed.
   R1 (decides): MV+NONE+BF adopted if its precision gain over MV has a module-bootstrap 95% interval above 0 and
   recall >= 0.83. GUARD secondary only, vs equal-strength random thinning. Cost: 78 calls, $2.80-4.06 (estimate).
3. Arm m7e194es0ismd (sha 6f74d32530ab): winner + 4 amended seed lines (primary, secondary, the dependency sentence,
   the storing restriction); examples unchanged; checks PASS. Readings (read_def_arm.py, frozen): R1 FP on 17 transit
   registers / FIFO data fields (33 winner slots) falls >= 50%; R2 hits on deciding elements not lower (winner 120/126);
   R3 imem rdata, muldiv mul.prod, cfu key_mem, hwspinlock lock_q, uart ctrl.baud stay >= 2/3 (a structural 'entry and
   exit' proxy caught exactly these configuration registers, so the transit rule's risk is to drop them); R4 FP price on
   deciders (winner 184 slots); R5 emissions within 10% of 273.3.
Notebook: definition arm cells 34-37, held-out cells 38-41.

## Definition arm ismd and held-out validation: results (2026-10-01 16:xx)

Definition arm m7e194es0ismd (tuning 15, 111 entries, 3 runs, strict): P 0.340 R 0.877, 286.3 emitted/run, against the
winner 0.344 / 0.847 / 273.3. Readings (read_def_arm.py): R1 transit-list FP slots 33 -> 43, FAIL; R1b internal
data-only FP slots 260 -> 273; R2 decider hit slots 120 -> 121 of 126, PASS; R3 5/5 protected at 3/3, PASS; R4 decider
FP slots 184 -> 206; R5 +5%, PASS; Step 1b bar (P >= 0.374): does not count (score_hand_arm's "COUNTS" line uses the
old 0.326 bar). 0 of 378 concepts use the new rule's wording; transit registers still labelled "stores". Net +10 hit
slots of 333, mostly inputs and start flags (muldiv div.start / mul.start 1 -> 3, uart uart_rxd_i 0 -> 2). In-sample
levers: winner MV+NONE+BF 0.394 / 0.901; ismd MV+NONE+BF 0.385 / 0.937. Not adopted. Fourth prompt arm whose
exclusion sentence changed nothing.

Held-out (pre-registered, read once by the user; assetgen_meta/heldout_readings.json; 26 modules, 189 entries, none
excluded): winner base P 0.352 R 0.852 (458 emitted/run; runs 0.341/0.852, 0.350/0.868, 0.365/0.836); MV 0.350 /
0.857; MV+NONE+BF 0.399 / 0.884 (419). R1 PASS: dP vs MV +0.049 [0.025, 0.080], recall 0.884 -> MV+NONE+BF ADOPTED.
GUARD (secondary): 0.446 / 0.801 vs equal-strength random thinning 0.393 / 0.707 (0 of 1,000 draws >= GUARD); bootstrap
vs base dP +0.094 [0.046, 0.147], dR -0.051 [-0.101, -0.013]. Correction: GUARD is weaker out of sample but NOT noise;
it stays evaluation-layer for lack of a basis. MV+NONE+BF+GUARD 0.497 / 0.836. LAsset initial 0.734 / 0.862 (222).

## Blind-agent prompt study (2026-10-01; blind_agent/REPORT.md, PREREG.md)

User asked: prompt a blind agent (RTL + relation map only) to find assets without leaking the reference; test,
validate, select, analyse prompt qualities; compare with m7e194es0ism and v2x3r8 only after selecting. Executor =
Claude agents (session model), one per (prompt, run, module); inputs = numbered RTL + code-built map
(blind_agent/build_inputs.py, self-tested 5,760/5,760 and 11,997/11,997 occurrences on their line). 5 blind designers
(theory PDFs + 2 reference-free modules only), round-2 self-revision (critic reports not delivered: harness refused
subagent report files), leak check 10/10 PASS, transcript audit 349/349 executors + 15/15 designers/critics PASS.
Screen (tuning, 1 run): D1 0.358/0.577 best F1 0.441; E1 0.507/0.315; A1 0.357/0.225 (0/26 input ports). Round 2
changed F1 by -0.045..+0.035. Validation (2 runs, user cut 3 -> 2 after the usage limit): D1 0.359/0.577 F1 0.442 vs
D2 0.327/0.572 0.416 -> winner D1 (6,593 chars). Held-out (2 runs, 189 entries): D1 P 0.362 R 0.619 (323.5/run).
Same executor + inputs, tuning, 2 runs: CUR m7e194es0ism 0.334/0.820 (272.5); BASE v2x3r8 0.380/0.752 (219.5).
Gap: D1 lists 31.5 port record fields/run (all FP; reference has 0; CUR/BASE 0 by their whole-port rule); dropping them
from D1's outputs by code: 0.432/0.568. 33 reference entries CUR finds in both runs and D1 in neither, 23 of them
strobes/enables/selects/handshakes (my reading of names), 4 decisions: D1's theory-cited "leave out strobes" rule.
Reading: a theory-only blind prompt reaches ~P 0.36 / R 0.6; the rest is reference convention (strobes primary, port
fields never, arrays via read port) that its sources do not state.

## Traced arm m7e194es0ist built (2026-10-01; not run)

User request: restructure the winner into eight parts (inputs, definition, purpose and flows, flow graph, four questions
per value with a mechanism line, roles along the path with influence points, exclusions with reasons, checks with an
occurrence ID and an edge per element) and make every decision traceable. Files: assetgen_meta/traced_inputs.py
(inputs: numbered RTL + map with occurrence IDs + code flow graph; self-tested 5,972/5,972 and 11,997/11,997
occurrences on their line), assetgen_meta/trace_check.py (citation check + per-module reports; self-test 12 cases),
hand_arms/m7e194es0ist/ (instructions.md, examples adapted with code-checked map excerpts, build_ist.py,
check_examples.py, README.md), hand_arms/read_trace_arm.py (readings R0-R5). Prompt sha fa07ad720438, 193,492 chars.
Rule audit by a Claude agent: input ports could fall into influence points (fixed: never), "undermined behavior" yes
alone could qualify (fixed), prompt and code fit tables differed (unified), dropped winner rules restored, a word list
naming real signals replaced. Pilot 2 (Claude executors, wdt / hwspinlock / muldiv, format test): 44/44 references
verified, 38/38 yes lines real, 157/157 flow lines real; 21/22 reference entries, 37 listed.
LAsset_initial_results/ (user-supplied): "(1)" file = ground_truth/lasset_initial.json (41/41 modules identical); the
other file scores tuning 0.680/0.748 (122), held-out 0.730/0.757 (196): by size probably LAsset's RTL-only run (logged
2026-09-19 as 121 reported), to confirm with the user. If so, LAsset's precision does not come from the spec.
Notebook cells 42-45. Risks pre-registered (R3): map in input (ismr), four questions (ismq), separate list (v2sec).

Correction / confirmation (2026-10-01, user): LAsset_initial_results/asset_list_neorv32_initial (1).json is the
Spec+RTL initial run (= ground_truth/lasset_initial.json); asset_list_neorv32_initial.json is the RTL-only initial run.
RTL-only: tuning P 0.680 R 0.748 (122), held-out P 0.730 R 0.757 (196). Spec+RTL: 0.737/0.910 (137), 0.734/0.862 (222).
The spec adds recall (+0.162 tuning, +0.105 held-out), little precision (+0.057, +0.004). Like-for-like external row for
our RTL(+map)-only pipeline = LAsset RTL-only.

Trace summaries for the traced arm (2026-10-01; not run): assetgen_meta/trace_digest.py. (1) behaviour_table: per
version over the 15 reference modules: objectives, four-question answers and negatives, C / A / U raised, map facts in
the reasoning (relationship type in upper case, occurrence ID or line number; plain "gates" no longer counts),
verified occurrence + edge citations, hypotheses, exclusions. Current numbers (3 runs each): ism 341/349 Integrity, no
questions, 0/349 map facts; ismr 371/377, 0/377; ismq 327/331, 1,324 answers with 722 "no", C yes 0, 0/331 map facts.
(2) digests by code per module (where each missed reference entry ended up; flow-graph elements never considered; FPs
by role and citation status; stability). (3) summarize(): one META_MODEL call per module on its digest + one
synthesis, background mode with polling; code lists names a summary uses that are not in its digest. Self-test
(pilot 2) and a mock end-to-end run (fake client: 4 calls, the invented name flagged in each summary) pass.
Notebook cells 46-49 (after the traced arm's cells 42-45).

## Traced arm m7e194es0ist: results and diagnosis (2026-10-01; user ran cells 43-49)

Tuning, 15 modules, 111 entries, 3 runs: P 0.359 R 0.691 (213.7 emitted/run) vs ism 0.344 / 0.847 (273.3). MV 0.384 /
0.703. R1 PASS (799/846 references verified, 0 invalid / no citation); R2 PASS (631/631 yes lines real); R3a FAIL
(recall); R3b 33 reference slots parked in influence points / exclusions; R3c 13 port-field FP slots; R4 CITE 0.372 /
0.679; R5 no parse failures. Behaviour: 276/276 concepts cite map facts (ism 0/349, ismr 0/377); four questions
answered on all concepts but uniform (I yes 274/276, A yes 271, C no 276/276, U yes 39; 519/520 "no" unsupported).
Diagnosis (hand_arms/diagnose_ist.py, counterfactuals_ist.py): 20 reference entries lost (ism >= 2 runs, ist <= 1),
3 gained (muldiv mul.start, div.start, sys enable_i). Lost run-slots: influence point 19, nowhere 17, only in a flow
path / concept text 18. 16/20 lost had a fitting map edge (citation rule not the main cause); the 4 without are cpu
signals realized in a sub-unit (alu_res, csr_rdata, lsu_mar, lsu_err). Concepts per run fell in 11/15 modules (cpu 8 ->
4, bus 13 -> 7.3) while answers doubled in size. FP run-slots 538 -> 411 but hit run-slots 282 -> 230. New FP class:
transport ports whole (~40 slots, 9 modules) + port fields 13; 98 of 112 transport references cited "via field": the
post-pilot rule letting a port named whole cite its field's record broke the transport exclusion (my error).
Counterfactuals on ist's outputs (exploratory): drop transport + port fields 0.396 / 0.688; promote GATES/SELECTS
influence points 0.344 / 0.745; input back-fill 0.369 / 0.733; all three 0.390 / 0.784; + MV 0.403 / 0.802.
Tooling fixed: digests / summaries ran on 41 modules (26 empty; removed, module list fixed); the summary name check
over-flagged (now allows relation types, digest keys, RTL identifiers, sub-unit ports): 15/15 module summaries clean.

## ist2 design in progress (2026-10-02; nothing run)

Evidence workflow (4 Claude agents; saved: assetgen_meta/hand_arms/m7e194es0ist2/evidence_v1v2_theory_evaluation.json):
- Key finding: ismrq (map + four questions, no influence list) scored P 0.360 R 0.697, matching ist 0.359/0.691. Recall
  costs isolate as map in input (ism -> ismr -0.07) + questions in the same call (ism -> ismq -0.09) ~ ist's -0.156.
  The influence list mostly shows where losses landed (v2sec: a destination moves 95% of borderline elements).
- CIA bias cause: the inherited C criterion ("require an RTL restriction on disclosure") is not P3164's question.
  P3164 Q1/Q2 (p.9) tell the IP developer to ASSUME confidentiality/integrity protection is required; its worked
  examples answer C yes for stored / generated / readable data in 4 of 5 designs (GNG p.13, AES p.15, SRAM p.17, CPU
  pp.21-22) and no only for pure pass-through (GPIO p.11). Integrity: value must stay fixed during an operation and
  something can change it outside expected behaviour (p.9, p.22 "no" for expected replacement). Availability: an
  integration-level means can gate/block it (p.9, GNG "no" p.13). SA-EDI Table 2 p.10 (Secret -> C, Sensitive -> I).
- Evaluation of fixes: A transport fix APPLY (scope the field route to non-transport records); B remove influence list
  APPLY, but NOT the decider/redirect sentence (S-3, ismd failures); C prompt input-disposition DO NOT (ismcap
  falsified), code BF APPLY; D compact output by deleting fields APPLY; E sub-unit fix as map/citation fix APPLY;
  F questions: move to a SEPARATE labelling call after the list is fixed (in-call questions cost recall in ismq/ismrq).
Plan (ist2): generation call = ist minus questions / influence / hypotheses / exclusion lists / flow paths, with ism's
established-value criteria restored, transport scoping, computes-via-sub-unit citations; second call = SoC-engineer CIA
questionnaire (yes-RTL / yes-assumed / no / unknown, every answer with a line and a "via"; P3164 worked answers as
teaching); code rows T, BF, MV; readings from the evaluation's table (R0-R8 + CIA discrimination readings).
Code done this session: traced_inputs.resolve_modes (sub-unit connection direction from the instantiated entity's
declaration; cpu 72/72 resolved; self-test ok) and inputs rebuilt into assetgen_meta/traced_inputs_v2/ (ist's
traced_inputs/ kept); trace_check: transport records cannot cite via a field, a plain internal signal driven by a
sub-unit output may cite CONNECTS as "computes", MapIndex carries the module; influence points computed by code in
the reports; self-test 13/13; ist_levers.py (T, BF, MV; reproduces the counterfactuals); trace_digest module list
fixed (15 modules), name check widened (15/15 summaries clean), 52 empty held-out files removed.
NOT done: ist2 instructions, CIA labeller prompt + teaching examples, examples rebuilt to the ist2 format,
cia_label.py, read_ist2.py readings, notebook cells, consolidated entry in ABLATION_LOG_V2.md (the m7e194e* arms are
logged only here).

## Arm m7e194es0ist2 built (2026-10-02; notebook cells 50-56; not run on gpt-5-mini)

Two calls. Generation prompt hand_arms/m7e194es0ist2/exec_prompt.txt (sha 5d1e82e53d58, 177,581 chars; instructions
25,904): ist minus the four questions, influence points, hypotheses, exclusions and flow paths; ism's established-value
criteria (sections 5-8) restored without the "require an RTL restriction" confidentiality sentence; transport records
never cited through a field; a plain signal a sub-unit drives may cite that connection as "computes"; a map-reading
correction for entities that instantiate sub-units (their connecting signals are this entity's elements; "not
assigned" means no assignment in this file). Inputs: assetgen_meta/traced_inputs_v2 (connection directions from the
sub-units' declarations). Examples: ist's decisions kept exactly, final objects reduced, analyses rewritten by two
agents; examples_ist2.py 7 checks PASS.
CIA labelling prompt cia_instructions.md (sha be31fc3e1e9a, 11,151 chars) + assetgen_meta/cia_label.py: one gpt-5-mini
call per run and module on the fixed list; IEEE P3164 3.1.1 questions answered as an SoC security engineer does for an
IP of unknown use (writers, observers, blockers; yes-RTL / yes-assumed / no / unknown; a line for every yes and no),
taught with P3164's worked judgements (paraphrased). trace_digest / trace_check read the merged answers.
Readings fixed before the run: hand_arms/read_ist2.py (R0-R9 generation; C1-C4 labelling).
Pilots (Claude executors, format and reasoning test, not scores): generation on wdt and cpu: all citations verified
(16/16, 3/3); wdt 8/8 reference entries; cpu only 3 listed, 2/14 reference entries -> the map-reading correction above
(cpu re-pilot pending). Labelling on both: 0 validation problems; every yes (26/26) and every no (21/21) cites a real
RTL line; answers vary by value (wdt settings C no / I yes / A yes / U no; reset-cause record C yes-assumed, U yes-RTL
via the debugger reset input).
Incident: a concurrent run of an early examples_ist2.py check overwrote ist's two example files; recovered exactly from
ist's built prompt (recover_examples.py: re-assembly equals exec_prompt.txt byte for byte); the check no longer writes.
ABLATION_LOG_V2.md: section 10 added (index of the m7e194e* arms, held-out, blind study, lessons).

ist2 final changes before any gpt-5-mini run (2026-10-02): (1) IEEE P3164 Q2 integrity assumption (p.9) scoped to
values that cross the entity's boundary to a consumer that is not supplied (instructions section 5; ASSET_DEFINITION
section 6). Claude pilots, one run each: cpu 1 -> 25 listed, recall 0.07 -> 1.00 (14/14), precision 0.56 (FPs are
sub-unit results the reference omits: rs1-rs3, xcsr_*, alu_cmp, lsu_rdata); the first, unscoped wording gave cpu 23
listed / R 0.93 and uart 38 listed / P 0.26; the scoped wording uart 41 listed / R 1.00 / P 0.24 -> the uart breadth
comes from the restored established-value criteria (ism listed 29 on uart on gpt-5-mini), not from the assumption.
All 66 pilot citations verified. (2) Notebook markdown cell of the ist2 section updated. Final generation prompt sha
e5fe4918c22b (178,439 chars); CIA prompt sha be31fc3e1e9a. Cells 50-56 ready; nothing run on gpt-5-mini.
