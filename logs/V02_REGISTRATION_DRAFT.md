# v02 — precision study, registration DRAFT — **SUPERSEDED**

> **Superseded 2026-08-08 by `ABLATION_LOG_V2.md`**, which is the canonical record. Kept only
> for the reasoning behind the arm designs.
>
> **One claim in here is wrong and is corrected in the new log.** §0(d) and §3 say F1 is "the
> wrong decision metric for this study" and "decides nothing", on the grounds that it stays
> flat across the whole truncation sweep. The flatness is real; the conclusion was backwards.
> F1 is flat when an arm merely *emits less* and rises when an arm removes false positives
> without losing true ones — baseline 0.381, blind cap-4 0.382, bus rule 0.402, oracle cap-4
> 0.481. That is exactly the discrimination this study needs. **F1 is a reported headline
> metric, second to precision.** See `ABLATION_LOG_V2.md` §8, R-V2-01(b).

**Status: nothing has been run. Nothing in `ABLATION_LOG.md`, `prompts.py` or the notebook has
been changed.** On approval this file's §1–§6 get pasted into `ABLATION_LOG.md` §3 and the
config/registry edits in §7 get made.

Drafted 2026-08-08 from `V02_HANDOFF.md`, the log, and the run artifacts on disk.

---

## 0. Read this first — four things the handoff got wrong or left open

Each is verified against the artifacts, with the check named so you can re-run it.

**(a) `v02` is already a registry key.** `PROMPT_VERSIONS["v02"]` = (`ASSET_PRIMARY_CORE`,
`icl_examples_02.ICL_ASSET_EXAMPLES_02`) — the AES-swap ICL variant. `BASELINE["v02"] = "v01"`.
It has **no runs on disk** but it is referenced in four places in the log, including the open
threat *"v01 vs v02 is confounded"*. Naming the study's baseline `v02` would collide with all
of that.

**It dissolves without a rename.** The v02 baseline needs **no new prompt code**: it is exactly
`v01c6p1p2d` — P-2's input regime with L-1 folded in — which is **already built, already
registered, asserts already passing, sha `cc3f0b397044`, and never run.** So: *v02 is the name
of the **study**, not of a version.* The baseline version key stays `v01c6p1p2d`. No rename, no
log edits, no collision.

**(b) Arm version keys must never be `<baseline>_<tag>`.** `EV.collect()` globs
`assets_tuning18_{v}_r*`. I tested it:

```
vBASE  -> ['..._vBASE_r0', '..._vBASE_r1', '..._vBASE_r8_r0']   <-- the arm folded in
vBASEq -> ['..._vBASEq_r0']
```

An arm keyed `v01c6p1p2d_r8` would have its repeat directories silently collected as **extra
repeats of the baseline**, corrupting both. Alphanumeric suffixes (`v01c6p1p2dq`) are safe
because `_r` is the separator. The existing keys are all accidentally safe; the next one typed
by hand would not be. **Registering this as a rule in §6 of the log.**

**(c) The proposed recall guard cannot be adjudicated the proposed way.** The handoff asks for
*"recall must not fall more than 0.03, judged on the paired CI."* The log's own §6 says the
paired recall CI runs **±0.14** at 15 modules, and that anything under ~0.10 reads as
inconclusive. A true drop of 0.03 and a true drop of 0.10 produce the same verdict — a CI
spanning zero. The guard as written would never fire. §3 proposes an enforceable replacement.

**(d) F1 is the wrong decision metric for this study, and I can show it rather than argue it.**
Truncating v01c6p1p2's own outputs to at most *k* elements per concept, sweeping *k* from 99
down to 1, moves precision 0.243 → 0.386 and recall 0.886 → 0.315 — and **F1 stays between
0.382 and 0.391 the entire way.** F1 is flat along exactly the axis this study moves. It gets
reported; it decides nothing.

---

## 1. What v02 is, and the objective switch

**Registered change of objective: from recall to precision, with recall as a guard.**

Up to `v01c6p1p2` the target was recall and the chain delivered it — 0.553 → 0.886, against the
paper's 0.910. Precision went the other way: **0.300 → 0.243, against the paper's 0.737.** We
are not matching LAsset; we are reaching comparable recall by naming three times as much (404
emissions against 137, on 1 572 elements — a 3.4× lift over random against their 10.5×).

Every remaining recall arm makes this worse, and §III-C of the paper says refinement (lines
7–9) only *removes* — measured at precision +0.083, recall −0.026. So line-5 recall is a hard
ceiling for the whole pipeline and we are already at 0.886 of it. **Precision is the binding
problem and it is now the target.**

**What this changes in practice.** An arm is now accepted on precision and rejected on the
recall guard, which is the exact inverse of A-02 through A-08. Two arms in the existing chain
(A-08 especially) would be rejected under the new objective; that is expected and is not a
retraction — they were run against the objective in force at the time, and their measurements
stand.

**What it does not change.** Metric **M-2**, unaltered. Ground truth, unaltered. Paired
bootstrap with modules as the pairing unit, unaltered. One proposition per arm, unaltered.

---

## 2. The baseline

**Version `v01c6p1p2d`, sha `cc3f0b397044`.** Already built and registered; this study runs it
for the first time.

| | |
|---|---|
| core | `prompts.ASSET_PRIMARY_CORE_P1P2D` |
| ICL | `icl_examples_01b_noparse.ICL_ASSET_EXAMPLES_01B_NOPARSE` |
| user message | comment-stripped RTL only — `INPUT_BLOCKS = {"summary": False, "parsed": False}` |
| validation | `RETRY_ON_VALIDATION` resolves to **False** — report only, no corrective regeneration |
| model | `gpt-5-mini`, `effort="high"` |

**Why this input regime.** P-1 (drop the summary) was null on recall, precision and F1. P-2
(drop the parsed closed set) was null on recall (−0.020 [−0.086, +0.039]), +0.017 precision,
−15% emissions, and removed **58% of every user message**. Precision variance is **2.5× lower**
there, which is what a precision study needs. Costs, recorded: the union ceiling falls
0.950 → 0.937 and recall variance roughly doubles — acceptable when recall is a guard.

**Why L-1 is folded in rather than run standalone.** L-1 removes four real NEORV32 identifiers
from the prompt, one of which (`ctrl_i`) is a ground-truth answer in 10 of the 41 annotated
modules. On our 15 it is worth at most 0.009 recall; **9 of the 10 are in the 26 held-out
modules**, so leaving it in would poison the generalisation test that is the point of the
held-out set. Folding it in costs one arm's worth of measurement and buys a clean base. If you
want L-1 measured as its own arm, that is a separate decision — say so and I will re-plan; it
costs one extra run and it is the only way to know whether the leak was doing work.

**This is a re-baseline, not a bundle.** No new idea enters v02. Every accumulated conclusion
goes into the arm queue.

**Registered caveat.** v02 vs `v01c6` may be reported as *"where we were vs where we are"* and
**never** as an attributable delta — it bundles the summary drop, the parsed drop and L-1.

---

## 3. The recall guard — enforceable version

**The guard is on the point estimate; the CI is reported for context and does not gate.**

> An arm passes the guard if its mean recall over repeats is **not more than 0.03 below its own
> baseline's** mean recall over the same repeats and the same modules. The paired CI is printed
> alongside and interpreted, but the gate is the point estimate.

**Why.** At 15 modules the paired recall CI is ±0.14. Gating on it means never rejecting
anything. The point estimate at n=3 has sd ≈ 0.026 (v01c6p1p2's measured value), so a 0.03 shift
is roughly 2 standard errors — noisy, but it is a *guard*, and a guard that fires occasionally
on noise is the correct failure direction. Gating on the CI fires never.

**Stated honestly: 0.03 is at the edge of what this setup can see.** It is a declared risk
tolerance, not a detection claim. If an arm lands between −0.03 and −0.06 the honest verdict is
*"guard indeterminate, re-run at n=5 before promoting"*, and that is written into the decision
rules below rather than resolved case by case afterwards.

**Repeats.** n=3 to screen an arm; **n=5 before any arm is promoted into the chain.** The log
establishes n=3 is sufficient for precision (3-of-5 subsampling, 100% sign agreement) and that
n=5 is needed for per-class recall (port sign agrees only 58% at n=3). Since the guard is on
recall, promotion needs n=5. Screening at 3 and promoting at 5 is the cheap ordering.

**Primary reported quantities, in this order:** precision · recall (guard) · emissions ·
per-class recall · F1 (context only, see §0d).

---

## 4. Verification pass — what I re-derived, and what I did not

Re-derived from the artifacts this session, all matching the handoff exactly unless noted:

| claim | verified |
|---|---|
| all 10 rows of the results table (emit/TP/FP/P/R) | **exact**, every version |
| 15 common modules, 111 references | ✓ |
| GT by objective | Integrity **75** (67.6%), Availability **33**, Confidentiality **3** |
| Confidentiality claimed 58.0/repeat at P 0.144 | ✓ exact |
| FP by class: signal-field 47 / port 27 / signal 25 | ✓ 47.2 / 27.3 / 24.9 |
| 286 distinct FP names, top-20 = 20% | ✓ 285 and 20.0% (bare names) |

Newly measured, not in the handoff:

- **Module-qualified**, distinct FP names are **323** and the top 20 are only **11.2%** of FP
  mass. The long-tail conclusion is *stronger* than recorded — a blocklist is even less viable.
- **Per-concept fan-out at `v01c6p1p2` is 4.46** (median 4, p90 8, max 15). The handoff's 3.63
  is the T-1/`v01c4` figure; A-08 raised it and it was never restated.
- The Confidentiality and per-concept-budget findings in §5, which change two arms.

**Inherited and NOT independently verified** — flagged so no one later mistakes them for
checked: the concept-level oracle ceiling of P = 0.347; the ~50% of FPs that LAsset itself calls
secondary; T-1's 82–85% binding-failure split; the union-over-repeats ceilings; L-1's
identifier audit over 1 355 parsed and 218 ground-truth names; all sd and CI values; the claim
that port-field FPs went 2.2 → 20.8.

---

## 5. Arm queue

Reordered from the handoff. Two arms are redesigned because the data contradicts their premise,
and one is added. Cheapest-and-safest first, so each landed arm raises the base for the next.

Every arm is `CURRENT_BASELINE` + exactly one proposition, paired against it, with an explicit
`BASELINE` entry.

---

### E-1 · Replicated interconnect is not an asset of the module it passes through
**Proposed key `v01c6p1p2de1`. Baseline `v01c6p1p2d`. Precision arm. Cheapest and safest.**

The worst FP names are the SoC bus interface repeated in every peripheral — `bus_req_i`,
`bus_rsp_o`, `core_req_i` and kin. **Measured on the actual `v01c6p1p2` outputs: 25.3 FPs per
repeat, 8.3% of all FP mass, at exactly ZERO true positives — the bus-interface family hits
nothing in the ground truth, in any module, in any repeat.** Removing them gives precision
0.243 → **0.260** with recall **unchanged to three decimals**.

This is a general criterion, not a blocklist: *a generic interconnect port replicated
unchanged across many modules carries no asset specific to this module; judge it in the module
whose function is the interconnect.* Note the carve-out is not even needed empirically —
`neorv32_bus`'s own `core_req_i` is also an FP — but it is kept because it is the correct
principle and because the held-out set is the point.

**Expect:** precision **+0.015 to +0.020**, recall **0.000**, emissions −25/repeat.
**Decision rule:** precision up and recall within guard → promote. Precision null → the model
is not reading the rule as general; do not re-word, record and move on.
**Risk, registered:** "generic" is a word the model must interpret, and over-application would
strip real interface assets. Port recall is the class to watch.

---

### E-2 · Revert A-08's per-concept closure sweep
**Proposed key `v01c6p1p2de2`. Baseline: whichever of E-1 / `v01c6p1p2d` is standing.**

A-08 bought recall +0.032 for precision −0.056 and +97 emissions per repeat. **Under the new
objective that trade inverts**, and it is the single largest precision item available from a
change we already understand.

**Expect:** precision **+0.04 to +0.06**, recall **−0.02 to −0.04**, emissions −20%.
**Decision rule.** This arm sits *exactly on the guard by design*, so the rule is written
before the number is seen: precision up **and** recall drop ≤ 0.03 → promote. Recall drop
> 0.06 → reject, A-08 stays. Recall drop between 0.03 and 0.06 → **re-run at n=5 and decide on
that**; do not adjudicate by eye.
**Registered cost:** A-08 is the only arm that ever moved the union ceiling (0.928 → 0.955).
Reverting it likely gives that back. That is acceptable under the new objective and is recorded
so it is not rediscovered as a surprise.

---

### E-3 · Tighten what qualifies as a secret — REDESIGNED, and the handoff's version would fail
**Proposed key `v01c6p1p2de3`.**

The handoff calls Confidentiality *"the only clean outlier: 3 real assets, 58 claimed per
repeat, precision 0.144"* — all confirmed. **But suppression would be far more expensive than
that framing implies.** Of the 58 Confidentiality-labelled emissions per repeat, **8.3 are true
positives by element name**, and only **2.7** of those are elements the ground truth also calls
Confidentiality. The other **5.7 are correct assets wearing the wrong label** — `uart_rxd_i`,
`rs1_i`, `rs2_i`, `mul.prod`, `csr_wdata_i`, `uart_txd_o`, `valid_o`.

Suppressing Confidentiality claims would therefore cost **8.3 TP ≈ 0.075 recall** — more than
twice the guard.

**And the arm must change shape, because the metric scores element names only, not objectives.**
A pure re-labelling arm is *invisible to the metric*. The proposition has to be: **tighten the
(C) rubric so that an element qualifying on confidentiality grounds alone is not emitted, while
an element that is a genuine asset under (I) or (A) is re-labelled and kept.**

**Ceiling, arithmetic on the measured counts:** perfectly executed — 49.7 FPs dropped, all 8.3
TPs retained by re-labelling — gives emissions 404 → 354.3, precision 0.243 → **0.277**, recall
unchanged. That is the *upper bound*; expect less.

**Expect:** precision **+0.015 to +0.034**, recall **0.000 to −0.01**.
**Decision rule:** recall drop > 0.03 means the re-labelling half failed and the arm is
suppressing real assets → reject outright, do not re-word.
**The 3 real ones must survive:** `neorv32_cpu_cp_cfu:key_mem`, `neorv32_debug_dtm:jtag_tdo_o`,
`neorv32_trng:data_o`. If any is lost the arm is rejected regardless of aggregate numbers.

---

### E-4 · Per-concept element budget — REDESIGNED; the handoff's version is dead, and I can prove it
**Proposed key `v01c6p1p2de4`. Highest headroom, highest risk. Run last.**

The handoff proposes *"a general cap, not a blocklist"* on elements per concept. **A blind cap
is worthless, measured on the real outputs.** Truncating each concept to its first *k*
emissions in output order:

| cap | emit | TP | P | recall |
|---|---|---|---|---|
| none | 404.0 | 98.3 | 0.243 | 0.886 |
| 6 | 350.7 | 89.3 | 0.255 | 0.805 |
| 4 | 286.3 | 76.0 | 0.265 | 0.685 |
| 3 | 237.0 | 67.3 | 0.284 | 0.607 |

Emissions and true positives fall **in proportion**. A cap of 4 buys +0.022 precision for
−0.201 recall. **Emission order carries essentially no confidence signal.**

**But the headroom is real, and it is entirely in the ranking.** Cheating — keeping each
concept's TP-bearing elements first, up to *k*:

| cap | emit | TP | P | recall | vs baseline |
|---|---|---|---|---|---|
| 6 | 350.7 | 98.3 | **0.280** | 0.886 | +0.037 precision, **zero** recall cost |
| 4 | 286.3 | 95.7 | **0.334** | 0.862 | +0.091 precision, −0.024 recall — **inside the guard** |
| 3 | 237.0 | 91.7 | 0.387 | 0.826 | +0.144 precision, −0.060 — outside the guard |

Same cap, same emission count, recall 0.685 vs 0.862 — the entire difference is *which* element
the concept keeps. **So the arm is not "cap the count". It is "cap the count AND rank within
the concept".** A cap without a ranking criterion is the top table; a cap with one is the
bottom table.

**Expect** — stated as a position between two measured lines, which is what makes this arm
worth running: at a cap of 4, precision between **0.265** (model cannot rank itself) and
**0.334** (model ranks perfectly), recall between **0.685** and **0.862**.
**Decision rule:** land near the blind line → the model cannot rank its own emissions and the
whole budget family is closed; record it and stop. Land near the oracle line → this is the
largest precision lever in the study and the cap becomes a tunable parameter.
**Registered risk:** the log's standing constraint is that no count, proportion or threshold
may appear in a prompt — A-08's earlier "~20% of the closed set" became a hard quota and cost
7 of 17 recall losses on `cpu_cp_cfu`. **This arm deliberately breaks that constraint**, which
is exactly why it runs last and why the guard is written before the number is seen.

---

### E-5 · Restore A-03's port-record granularity — lowest confidence, verify before building
**Proposed key `v01c6p1p2de5`.**

The handoff reports port-field FPs going 2.2 → 20.8 across later arms and calls it "A-03's
decay". **I did not verify that number** and it is the only queue item resting on an unchecked
claim. Port FPs are 27.3% of FP mass at `v01c6p1p2`, so there is something here, but the
specific decay story needs confirming first.

**Registered as: measure before building.** A scoring-side check on existing artifacts — no API
cost — decides whether this becomes an arm at all.

---

### Dropped from the queue

**Nothing else.** Both handoff items survive in redesigned form. Recording explicitly that
"blind per-concept cap" is **rejected on measurement, not on judgement** — see E-4's first
table — so it is not re-proposed later.

---

## 6. What this queue can and cannot reach

Honest arithmetic, so the study is not read as a route to 0.737.

| | precision | notes |
|---|---|---|
| v02 baseline (expected ≈ v01c6p1p2) | 0.243 | |
| + E-1 | ≈ 0.260 | measured, zero recall cost |
| + E-3 | ≈ 0.277 | ceiling, perfect execution |
| + E-2 | ≈ 0.33 | if A-08's −0.056 comes back |
| + E-4 at cap 4 | ≈ 0.33–0.40 | only if the model can rank |
| **LAsset line 5** | **0.737** | |

**These do not compose.** Each figure is that arm measured or bounded against the *baseline
alone*; the rows are stacked only to show the order of magnitude available. Overlapping
removals (E-1's bus ports are also emissions some concept produced, so E-4 would cut some of
them again) mean the true total is **below** the naive sum.

The inherited concept-level oracle — killing every concept that produced no true positive,
using the answers — reaches only **P = 0.347**. **Line-5 prompting alone almost certainly
cannot reach 0.737**; the paper gets there with lines 7–9, which we have not implemented. The
plausible honest outcome of v02 is **precision roughly 0.30–0.40 at recall ≥ 0.85**, which
would be a doubling and still half the paper's figure.

**This should be said in the write-up, not discovered by a reviewer.** If matching 0.737 at
line 5 is the goal, the queue above is not sufficient and the real answer is implementing lines
7–9 — a separate study, and the one the paper's own ablation says does this job.

---

## 7. Mechanical changes needed on approval

None of these are made yet. All are notebook/registry edits, no prompt text changes.

1. `93ecd6e3` (config): `CURRENT_BASELINE = "v01c6p1p2d"`, `VERSION = "v01c6p1p2d"`,
   `REPEATS = 3`. Add the objective-switch note to the chain comment.
2. `87ec7834` (ablation): add `"v01c6p1p2d"` to `VERSIONS`; add
   `BASELINE["v01c6p1p2d"] = "v01c6p1p2"` so the first run is scored as the L-1 arm it also is.
3. `2031c14a` (registry): no change — `v01c6p1p2d` and its `INPUT_BLOCKS` entry are already
   there. Verified.
4. `ABLATION_LOG.md`: paste §1–§6 into §3; add the promotion row for `v01c6p1p2` → `v01c6p1p2d`;
   add the §0b glob rule and the objective switch to §6.
5. **Not done and needs your call:** promoting `v01c6p1p2` to `CURRENT_BASELINE` was never
   propagated after P-2 — config still reads `v01c6p1p2`/`v01c6p1`. The log warns about exactly
   this failure mode ("a decision recorded in prose is not a decision applied").

---

## 8. Open items carried forward, not resolved here

- **P-2′** (strip only the `function` field) — pre-registered, never run, and can only run on
  `v01c6p1`. Orthogonal to this study; it answers whether stage 4's annotation is worth
  enriching. Not in the v02 queue.
- **No held-out set exists.** All 15 scored modules are the tuning set; the other 26 annotated
  modules have no RTL in `RTL_data/`. P-2 makes a held-out run affordable (RTL only) and L-1
  makes it honest. **This is the highest-value item in the whole project and it is not an arm** —
  it needs RTL pulled from the NEORV32 repo at the matching revision.
- **Five arms of prompt tuning were designed by inspecting misses on these same 15 modules.**
  This is fitting to the test set and is the most likely explanation for matching the paper's
  recall at a third of its precision. v02 adds up to five more. **The held-out set is the only
  thing that can answer it.**
- **Secondary assets remain out of scope** by standing decision — ~50% of our FPs are elements
  LAsset itself names as secondary. Deferred until primary precision is addressed.
- **Cost per arm not estimated.** I have the per-token rates but no measured token counts for
  the `v01c6p1p2d` prompt; I would rather measure one run than quote a guess.
