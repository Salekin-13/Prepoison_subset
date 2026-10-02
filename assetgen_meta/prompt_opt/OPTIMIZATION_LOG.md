# Prompt optimization log

Started 2026-10-02 at the user's request: iterate the current prompt with Claude agents on the 15 tuning modules toward
precision and recall both about 0.85, or until iterations stop improving. Rules of the loop:

- The evaluation set (15 modules, 111 reference entries, `ground_truth/manual_gt_neorv32.json`) and the scorer
  (`eval_assets.score`, strict) are never modified.
- Each version is kept in `assetgen_meta/prompt_opt/v<i>/` (instructions, built prompt, build record, change note,
  evaluation). Runs: `assets_opt_v<i>_r<k>/`.
- A change is made only from observed error patterns, worded generally: no reference answer, module name, element
  name or test-set-specific fact enters a prompt (leak check on tuning and held-out names; `meta_tools.check_exec_prompt`).
  Each entry records the change, the evidence and the reasoning, and whether the change also has a theory basis.
  This relaxes the earlier rule that every prompt rule needs a theory basis (user, 2026-10-02); pattern-only changes
  are marked as such.
- Executors are Claude agents (the notebook's executor is gpt-5-mini; results may not carry over); every executor's
  file access is audited (`blind_agent/audit.py`).
- One run per version (Claude run-to-run noise not yet measured); a change is kept only if F1 improves, and the run
  noise is measured once by repeating a version.
- The 26 held-out modules are not used during the loop; the final version gets one held-out check.

Stopping rule: precision >= 0.85 and recall >= 0.85, or two consecutive iterations with F1 gain below 0.02.

| version | sha12 | P | R | F1 | emitted | change (one line) | kept |
|---|---|---|---|---|---|---|---|
| v0 | e5fe4918c22b | 0.326 | 0.856 | 0.473 | 291 | the ist2 generation prompt (notebook cells 50-56) | baseline |
| v1 | 802ee9a90d41 | 0.378 | 0.937 | 0.539 | 275 | stored registers need a use record; no one-clock copies; inputs into unsupplied sub-units set | yes |
| v2 | = v1 | - | - | - | - | edit D (register that is one operand of output ports is secondary) withdrawn after review; moved to evaluation layer as R1a | no change, not run |
| v3 | = v1 | - | - | - | - | no edit: no candidate with a Prompt-row basis beats run noise (best +0.006 F1) | no change, not run |

### v0 (2026-10-02)
Run assets_opt_v0_r0 (15/15 executors pass the blindness audit). P 0.326 R 0.856 F1 0.473, 291 listed, 95 of 111 hits.
Citations: 312 verified, 12 "map gap claimed". False negatives: 7 nowhere in the output, 9 only in a concept's text.
False positives by module: cache 31, uart 28, twi 23, spi 22, trng 14, debug_dtm 14, sys 11, bus 10, cpu 9, muldiv 9,
cfu 8, wdt 7, pmp 6, imem 4, hwspinlock 0. cpu 5 of 14 hits here against 14 of 14 in the pilot: large run variance
on that module. Details: v0/eval_r0.md, v0/eval_r0.json.
Noise: a second run (assets_opt_v0_r1, 15/15 audited) gave P 0.343 R 0.919 F1 0.500 (297 listed; cpu 13 of 14). v0 mean
P 0.335 R 0.887 F1 0.486. Run-to-run difference 0.027 in F1, 0.063 in recall (mostly cpu). Keep rule from here: a
version is kept when its F1 beats the v0 mean by more than 0.03 (one run) or its P gain exceeds 0.03 at R >= 0.85.

### v1 (2026-10-02)
Written by the revise workflow (analyse, edit, adversarial review). The first review failed on four points: edit A
contradicted itself, edit C conflicted with the definition of "sets", a redundant sentence in section 5, and a false
claim in the change note (that only cpu wires inputs into sub-units that are not supplied; spi, twi, uart and trng also
do). All four were fixed by hand; a sentence-level diff against v0 shows only the three edits. Full note: v1/change.md.

Changes, evidence and basis (counts exact, from the v0 outputs; "upper bound" = the edit applied as a code filter):
- A. A stored register is a realization point only when its own records show this entity uses its value (a GATES,
  SELECTS or CONSTRAINS record, a path into an output, a connection into a sub-unit, or a configure-flow setting read by
  a computation here). Evidence: 159 internal "stores" entries in v0 r0, 37 TP and 122 FP; all 37 TP pass the test,
  24 FP fail it (r1: also 24 FP, 0 TP). Basis: partial (LAsset p2 secondary assets; Nath and Tan p1; P3164 p19 PIO);
  the record list itself is pattern only.
- B. List a value once: an internal register that only copies another listed internal element one clock later is not
  a second realization. Evidence: 15 FP, 0 TP in r0 (12 FP, 0 TP in r1). Basis: partial (LAsset p2); record test
  pattern only.
- C. An input port wired into a sub-unit whose code is not supplied "sets" the value it brings. Evidence: v0 r0 left
  the cpu interrupt and debug concept empty, quoting the forwarding rule (5 FN); v0 r1 listed the same 5 ports. A
  sentence readable both ways. Basis: partial (P3164 p19 PIO); the "not supplied" limit is pattern only, from section 5.
- Predicted, upper bound: A+B+C on v0 r0, F1 0.473 -> 0.538.

Result: run assets_opt_v1_r0, 15/15 executors pass the blindness audit. P 0.378 R 0.937 F1 0.539, 275 listed, 104 of
111 hits. Against v0 r0: +9 hits, 0 lost; FP +5 new, -30 removed (196 -> 171). Citations: 295 verified, 11 "map gap
claimed". False negatives: 3 nowhere in the output, 4 only in a concept's text.
- Compliance (scratchpad v1edit/sim_v1out.py, which reproduces the scorer's counts on v0 r0 and v1 r0): re-applying A
  as a code filter to v1's output removes 0 entries; B removes 1. The model followed both edits.
- Failure signs from the change note: none seen. All 5 cpu interrupt and debug ports are listed; the bus request port
  is not listed in spi, twi or uart; `icc_rx_i` is not listed; no input wired only into a supplied sub-unit was added.
- What the gain is made of (measured): 8 of the 9 new hits are in cpu, and v0's second run already had all 8. With one
  run per version, the recall gain over v0 r1 is 2 hits (cpu equal, muldiv `div.res` new), within noise. The precision
  gain is the robust part: FP 196 and 195 in the two v0 runs, 171 here.
- Against the v0 mean: P +0.043, R +0.050, F1 +0.053 (keep bar +0.03). Kept.

Distance to target (reasoning, from the numbers above): at 104 hits, P 0.85 needs at most 18 FP; v1 has 171. Earlier
sessions classed about two thirds of the FPs as kinds of element the reference lists in some modules and not in others
(asset-definition-reference memory; not re-derived here). The next analyses are asked to separate those.

### v2 (2026-10-02): withdrawn, no prompt change
Analysis of v1 r0 (revise run wf_85b16813-373; the analyst's parser passed a self-test against hand-read uart map
lines). 166 of v1's 171 FPs also appear in both v0 runs, and all 171 in at least one (re-counted in this session):
the errors are systematic, not noise, and v1 added no new kind of FP. Ranked patterns (analyst's counts; pattern 1
re-run below):
1. A stored register whose only records to other elements go into output ports of its entity (SOURCES, GATES, SELECTS,
   CONSTRAINS; read-back into a transport field aside), so it is one operand of the port's value: 21 FP, 0 TP.
2. A register copied unchanged (CARRIES) into an output port: 5 FP, 0 TP. Not edited: a worked example lists such a
   register beside its port.
3. A combinational decision used only as an operand of another listed decision: 5 FP; a looser reading loses 2 to 6 TP.
   Upper bound +0.007 F1.
Recall: no pattern worth an edit (two one-offs). The analyst classed the rest as reference inconsistency: internal
sequencing state, counters and shift registers 68 FP (listed in some modules, not in others; six flow-graph features
tested, none separates them); FIFO and sub-unit interface fields 21 FP; ports of sub-entities, opcode inputs and
read-back exits 16 FP; cpu wiring between sub-units 8 FP (identical map records for listed and unlisted ones).

Edit D (pattern 1) was written, then failed review. The reasons that decide it:
- It contradicts four unchanged prompt lines: settings and state are primary (lines 53, 82, 119) and "secondary" means
  "without holding a state, setting or decision of its own" (line 54). The model would be told both.
- Its boundary (the record test, the read-back exception) has no basis outside the reference. ASSET_DEFINITION.md
  section 5: "A rule whose only support is a count from the reference goes to the evaluation layer".
- The reviewer's smaller fix (keep settings and self-updating registers) leaves 8 of the 21 removals: F1 0.539 ->
  0.550 at most, below the 0.027 run noise. So the editor reverted; v2/instructions.md is byte-identical to v1.
Re-run in this session (scratch_archive/v1err/rules.py, v2fix/fix1_residual.py; parser self-test v2edit/selftest.py
PASS): R1a removes 21 FP / 0 TP on v1 r0 (F1 0.539 -> 0.570), 22 / 0 on v0 r0 (0.473 -> 0.500) and v0 r1
(0.500 -> 0.528). Of the 21 on v1 r0: 9 bus-written settings, 4 self-updating, 8 other.

R1a moves to the evaluation layer: a labelled in-sample row next to the headline, basis "none (derived from reference
counts)", like GUARD. What would show it is only a fit to the tuning reference: on held-out it removes a TP, or its
precision gain is no larger than random thinning of the same number of entries.

Iteration 2 counts as an iteration with F1 gain 0 (below 0.02). One more such iteration meets the stopping rule.

Rule change for the loop (this reverses the relaxation stated at the top of this log): from v3 on, every prompt edit
must cite a "Prompt" row of ASSET_DEFINITION.md section 3 or a paper; the exact record test may be pattern only. A rule
whose only support is reference counts, or that contradicts a "Prompt" row, goes to the evaluation layer. Reason: the
v2 review showed that a count-only boundary forced a contradiction with the prompt's own definitions. revise.js now
states this rule up front, and the reviewer's caution: word rules by record shape only, never by kind of structure of
an evaluated module (no arrays, memories, caches, FIFOs).

### v1 replicate (2026-10-02)
Run assets_opt_v1_r1 (15/15 pass the blindness audit): P 0.366 R 0.946 F1 0.528, 287 listed, 105 of 111 hits; cpu 14 of
14. v1 mean of 2 runs: P 0.372, R 0.941, F1 0.533 (v0 mean 0.335 / 0.887 / 0.486: +0.047 F1 on means, above the 0.03
bar). Run-to-run difference on v1: 0.011 F1. Compliance on r1: re-applying edit A removes 4 entries, B 3, A+B 7 (r0:
0, 1, 1); no TP lost. R1a (evaluation layer, in-sample) on r1: 21 FP / 0 TP removed, F1 0.528 -> 0.557.

### v3 (2026-10-02): no prompt change; loop stopped
Revise run wf_af802ed0-5ea (analyse, edit, review PASS). v3/instructions.md is byte-identical to v1. Re-run in this
session (scratch_archive/v3ana; parser and sub-entity self-tests PASS): the false-positive family table reproduces.
Every large family has true positives of the same record shape in the same run:

| family | FP | same-shape TP |
|---|---|---|
| internal state registers | 53 | 19 |
| combinational signals | 24 | 12 |
| settings written from an input | 22 | 16 |
| sub-unit interface fields | 21 | 3 |
| plain wires between sub-units | 11 | 8 |
| input ports | 9 | 24 |
| output ports | 9 | 21 |
| staging register into an exit (E1) | 4 | 0 |

So a structural rule that removes one also removes the other: these are kinds of element the reference lists in some
modules and not in others. The one clean candidate, E1 (4 FP, 0 TP; F1 0.539 -> 0.545), is below noise and its four
registers compute or decide their value in their own assignment, which the prompt's definitions make primary.
The analyst also corrected the v2 note: cache data_mem_b0..b3 are the memory arrays themselves (arrays-at-rest row),
not registered read-outs.

Stopping rule met: iterations 2 and 3 both F1 gain 0. Final version: v1 (tuning mean of 2 runs P 0.372 R 0.941 F1 0.533).
Neither stopping target was reached by P (0.372 vs 0.85); R passed it.

Evaluation layer: R1a moved from scratch into assetgen_meta/prompt_opt/eval_layer.py (split-aware; self-test PASS on
v0 r0, v0 r1, v1 r0, v1 r1). Random thinning of the same number of entries leaves P at the base value (0.378 / 0.366)
and reaches R1a's precision in 0.05% of 2000 draws (tuning, in-sample).

Next (pre-registered in HELDOUT_CHECK_PREREG.md before any held-out run of a loop version): one held-out run each of
v1 and v0 (paired, same Claude executor), readings by heldout_check.py; plus a third tuning run of v1 for the 3-run
mean that ASSET_DEFINITION.md section 4 asks for. opt_tools.py gained a split option (tuning numbers reproduce:
v1 r0 0.378 / 0.937 / 0.539) and opt_exec.js replaces the session-local executor script.

### v1 third tuning run (2026-10-02)
Run assets_opt_v1_r2 (15/15 pass the blindness audit): P 0.370 R 0.919 F1 0.527, 276 listed, 102 of 111 hits.
v1 headline, mean of 3 runs (ASSET_DEFINITION.md section 4): P 0.371, R 0.934, F1 0.531 (ranges across runs: P 0.012,
R 0.027, F1 0.012). Compliance on r2: re-applying edit A removes 1 entry, B 2, A+B 3; no TP lost. R1a (evaluation
layer, in-sample) on r2: 20 FP / 0 TP removed, F1 0.527 -> 0.556; random thinning mean P 0.369, 0 of 2000 draws reach it.

### Held-out check (2026-10-02), pre-registered in HELDOUT_CHECK_PREREG.md
Runs assets_opt_heldout_v1_r0 and assets_opt_heldout_v0_r0, Claude executors, 26 modules, 189 reference entries.
Blindness audit 26/26 for both runs and 1/1 for the retry. Five agents were cut off by a session limit after writing
their file. v1 cpu_control's first output was unparseable JSON (an unescaped quote in a text field); it was moved to
assets_opt_heldout_v1_r0/_invalid/ and retried once (valid, audited). No module excluded. Readings printed once by
heldout_check.py (pins verified; result in heldout_check_result.json):

- H1, v1: P 0.329, R 0.931, F1 0.486 (535 listed; TP 176, FP 359, FN 13).
- H2, v0: P 0.310, R 0.899, F1 0.461 (548 listed; TP 170, FP 378, FN 19). v1 - v0: dP +0.019, dR +0.032, dF1 +0.025.
  Precision prediction: "direction only, within noise" (pre-registered bar +0.03). Recall prediction: holds.
- H3, R1a on v1: removes 23 FP and 8 TP (cpu_counters hi_q, cpu_cp_shifter shifter.done_ff, shifter.sreg, bs_result,
  cpu_lsu misaligned, cpu_regfile reg_file, gpio irq_pend, pwm cfg_duty); P 0.333 R 0.889 F1 0.485. Random thinning of
  31 entries: mean P 0.329, 24.8% of draws reach R1a's precision. Verdict: tuning fit. R1a is not adopted, not even
  as an in-sample row beside the headline.
- H4: FP by role v1 / v0: stores 200 / 226, computes 97 / 93, sets 43 / 40, exit port 19 / 19. Edit A's target role
  ("stores") fell by 26 on held-out. Recall gain is mostly slink (13 vs 8 hits), the kind of single-module swing seen
  on cpu during tuning. Two modules carry 136 of v1's 359 FPs: cpu_control 84, cpu_cp_fpu 52.
- Context, other executor (not like-for-like): gpt-5-mini with prompt m7e194es0ism, 3 runs, no levers, on the same 26
  modules: mean P 0.352, R 0.852, F1 0.498.

Reading (reasoning, not a measurement): on tuning, v1 beat v0 by +0.036 P (means of 3 vs 2 runs). On held-out the
gain is +0.019, the same direction but below the noise bar, and one run each. The edits did what they target ("stores"
FPs fell on both sets), but the effect is small next to the reference-inconsistency families. The loop raised recall
on both sets and did not reach the precision target. The rule fitted most closely to the tuning reference (R1a) failed
out of sample, as GUARD did before.

## After the loop (2026-10-02): the final version in the notebook, and the false-positive diagnosis
User request: implement the final version in assetgen_meta.ipynb on a stronger OpenAI generator than gpt-5-mini
(default gpt-5.4), and add diagnostic cells that use the occurrence IDs and the relationship map to explain why
precision does not improve; the reporter may use an LLM (gpt-5.4) and must cluster the relationship types of hits
and false positives. Cells 57-69 of assetgen_meta.ipynb (marker [opt-final]); cell 54 now reloads trace_digest.
- Final version cells: EXEC_MODEL = gpt-5.4; FINAL_VERSION m7e194es0opt1_g54 (prompt 802ee9a90d41); paired baseline
  BASE_VERSION m7e194es0ist2_g54 (the ist2 prompt on the same model). Readings fixed before the run in
  prompt_opt/read_final.py (F0-F5); without the paired baseline they are labelled confounded. Not run (API cost).
- CIA labels: cell 54's "labelled 0/307" came from a stale trace_digest in the kernel (fresh process: 267/307). The
  label merge also missed 47 of 333 concepts whose names the labeller re-punctuated; cia_label.merged now matches them
  when unique (331/333) and no longer crashes on a non-object answer.
- assetgen_meta/fp_diagnosis.py (D1-D7; self-test 20 checks against hand-read map lines and the scorer) and
  assetgen_meta/fault_reporter.py (relationship-type profiles, clusters, AUC, rules, LLM per cluster with code checks;
  self-test 18 checks; prompts fault_reporter_prompt.md, fault_reporter_synthesis_prompt.md). Two read-only review
  rounds (workflows wf_c2e1103d-b8d, wf_e9398678-972) found and confirmed fixes for: edit compliance tested against
  the wrong wording, labels on repeated names, report sentences that contradicted their tables, flags (self-updates
  through control, sub-unit-driven and record-assigned signals, clock and reset drivers), a rule search that missed
  'unless' rules, LLM answers that could crash or pass the checks, and incomplete runs.
Measured, code only (no LLM call), Claude v1 tuning (3 runs, 838 listings) unless stated:
- 94% of FP citations verified (TP 99%): the FPs are not misreadings of the RTL as the map records it.
- 21 of 21 relationship-class tokens occur on both hits and FPs; 26% of FPs have exactly the profile of a hit; 74%
  share their L2 behaviour signature with a hit.
- Hit vs FP from the relationship classes: AUC 0.762 in-sample, 0.629 leave one module out (one row per element 0.62).
- Rules found per cluster (cluster tokens + up to two, minus one 'unless'; clean inside the cluster), all together:
  in-sample P 0.371 -> 0.563, R 0.934 -> 0.592, F1 0.531 -> 0.577; carried unchanged to held-out (Claude v1 r0):
  P 0.329 -> 0.478, R 0.931 -> 0.640, F1 0.486 -> 0.548. So rules on relationship types do remove part of the FPs on
  new modules, at a recall cost; no selector or filter of these forms reaches P 0.85 at R 0.85 (best leave-one-module-
  out 0.371 on tuning, 0.537 held-out). Held-out readings re-use outputs already read once: exploratory, not results.
- 69% of FPs sit in concepts with no reference element.
This changes the earlier one-line reading "FPs cannot be controlled" (my words in the loop's final message): measured,
part of them can, by structural rules, at a recall cost; the rest share their map evidence with hits.

### Final version on gpt-5.4, run by the user in assetgen_meta.ipynb (read 2026-10-02, cells 58-60)
Generation: m7e194es0opt1_g54 3 runs complete (18/18). Paired baseline m7e194es0ist2_g54: r0, r1 complete, r2 missing
neorv32_wdt (OpenAI credits exhausted); CIA labelling (cell 61) failed on credits; cells 62-69 not run. Computed from
the stored runs (scratchpad g54/readings.py, g54/diag.py; no API call):
- Pre-registered readings (read_final; the paired baseline has 2 complete runs, so the rule falls back to ist2 on
  gpt-5-mini and labels F1-F3 CONFOUNDED): final P 0.407 R 0.820 F1 0.544 vs 0.343 / 0.733.
- Supplementary, same executor (not pre-registered): final 0.407 / 0.820 (3 runs) vs ist2 prompt on gpt-5.4 0.407 /
  0.815 (2 runs); on the 14 modules of baseline r2, 0.398 / 0.816 vs 0.408 / 0.835. The gain over gpt-5-mini is the
  model's; the loop's edits add nothing measurable on gpt-5.4.
- F3: edits A and B still removable 14 / 19 / 19 FP per run (final) vs 15 / 18 (baseline gpt-5.4): not followed.
  F4 (edit C): cpu interrupt and debug ports 5/5/5 (final) vs 3/3/5 (baseline gpt-5.4). F5 citations verified
  1.00 / 0.97 / 0.96 per run.
- Code-only diagnosis (fp_diagnosis / fault_reporter, label tuning_gpt54_final): 21/21 relationship classes on both hits
  and FPs; 16% of FPs share an exact profile with a hit; leave-one-module-out AUC 0.644; 59% of FPs in concepts with no
  reference element.
