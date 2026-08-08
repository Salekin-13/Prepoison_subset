# Ablation log v2 — the precision study

Companion to `ABLATION_LOG.md` (the v1 recall study), which stays exactly as it is. Nothing
here changes a v1 number, a v1 sha, or a v1 conclusion.

Opened 2026-08-08. **Nothing has been run yet.**

---

## 1. What this study is

**Goal: raise precision to a defensible number without letting recall fall.**

v1 chased recall and got it — 0.553 → 0.886 against the paper's 0.910. Precision went the
other way: **0.300 → 0.243, against the paper's 0.737.** We reach comparable recall by naming
three times as much (404 emissions against 137).

**The target is the paper's pre-refinement precision, and that is the right target.** LAsset's
`asset_list_neorv32_initial.json` is the output of Algorithm 1 line 5 — asset generation,
before the refinement stage (lines 7–9) touches it. Scored on our 15 modules it is **137
emissions, TP 101, P 0.737, R 0.910**. That is the same pipeline stage we run, so it is the
correct comparator, and 0.737 is the number to move toward.

**The honest position on reaching it is in §6.** Short version: this queue can plausibly
double precision. It cannot reach 0.737, and §6 shows why with a measurement rather than an
opinion.

---

## 2. The recall guard is a DECISION RULE, not a code path

Recorded explicitly because it was asked and because getting it wrong would be a serious
methodological error.

**The guard does not touch generation. Nothing regenerates because recall fell.** It is a rule
applied at the ablation table, after scoring, exactly like every v1 decision rule:

> If an arm raises precision but drops recall past the threshold, **it does not become the new
> baseline.** The arm is recorded with its numbers and the chain continues from the previous
> baseline.

**It could not be a generation-time check even if we wanted one.** Recall is measured against
the ground truth. Feeding that back into generation — regenerate until recall improves — is
selecting on the answers, which is the same leak the v1 log already guards against with
`RETRY_ON_VALIDATION` under P-2, where choosing the sample that agreed better with the parsed
list would have been selection on withheld information. A recall-triggered retry would be a
much worse version of that. **Not to be built.**

### The threshold

> An arm passes if its mean recall over repeats is **not more than 0.03 below its own
> baseline's**, on the same repeats and the same modules.

**Judged on the point estimate, not the confidence interval.** The paired recall CI runs about
±0.14 at 15 modules (v1 §6). Gated on that interval, a true drop of 0.03 and a true drop of
0.10 give the same verdict — "spans zero" — and the guard would never fire. The CI is printed
and interpreted; it does not gate.

**0.03 is at the edge of what this setup can resolve.** At n=3 the recall sd is about 0.026, so
0.03 is roughly two standard errors. This is a declared risk tolerance, not a detection claim.
Hence the third verdict:

| recall vs baseline | verdict |
|---|---|
| drop ≤ 0.03 | **guard passes** |
| drop 0.03 – 0.06 | **indeterminate — re-run at n=5 and decide there** |
| drop > 0.06 | **guard fails, arm rejected** |

Written before any number is seen, so no arm gets adjudicated by eye afterwards.

### Repeats

**n=3 to screen an arm, n=5 before promoting it.** v1 established n=3 is enough for precision
(3-of-5 subsampling, 100% sign agreement) and that n=5 is needed for per-class recall (port
sign agrees only 58% at n=3). The guard is on recall, so promotion needs 5.

### Reported quantities

**Precision** (primary) · **recall** (guard) · **emissions** · **per-class recall** · **F1**.

**F1 is a genuine discriminator here and is reported as such** — see §7, R-V2-01, where an
earlier claim that it "decides nothing" was tested and turned out to be backwards.

---

## 3. Configuration and baseline

### Version `v2`, core sha `f082f3dbd073`

| | |
|---|---|
| core | `prompts_v2.ASSET_V2_BASE` |
| ICL | `icl_examples_01b_noparse.ICL_ASSET_EXAMPLES_01B_NOPARSE` |
| user message | **comment-stripped RTL only** — `INPUT_BLOCKS = {"summary": False, "parsed": False}` |
| validation | report-only, no corrective regeneration (`RETRY_ON_VALIDATION` False) |
| model | `gpt-5-mini`, `effort="high"` |
| scored on | the same 15 modules, 111 references, metric **M-2** |

**Prompt code lives in `prompts_v2.py`, not `prompts.py`.** v1's eleven core variants are built
by stacked substitution; adding precision arms on top would make every new sha depend on eight
earlier edits. v2 starts from one flat baseline and applies one documented edit per arm.
`prompts.py` is untouched, so every v1 sha still resolves to the code that produced it.

### Why RTL-only is the input regime

Two v1 input ablations justify it, and both were measured:

- **P-1**, drop the spec summary: null on recall, precision and F1.
- **P-2**, drop the parsed ports/signals and let the model read declarations off the RTL: null
  on recall (−0.020 [−0.086, +0.039]), precision +0.017, emissions −15%, and **58% of every
  user message removed**.

Precision variance is **2.5× lower** in that regime, which is what a precision study needs.
Recorded costs: the union-over-repeats ceiling falls 0.950 → 0.937 and recall variance roughly
doubles. Acceptable when recall is a guard rather than a target.

### Two corrections folded into the baseline

Both are in `prompts_v2.py` as separate reversible functions, so they are visible as edits.

**D — closed-set parity.** The supplied draft's RULES still said *"from the provided
ports/signals"* and *"that element's `entity` field"*. There are no provided ports/signals in
this regime. Leaving them tells the model to use something absent, which is a confound rather
than a clean baseline — it is what nearly wrecked P-1. Rewritten to the wording v1's
`_apply_drop_parsed` already uses, so v2's baseline and v1's `v01c6p1p2` say the same thing.

**L — de-leak (v1 arm L-1, registered there and never run).** The draft quotes four real
NEORV32 identifiers as naming examples. One, **`ctrl_i`, is a ground-truth answer in 10 of the
41 annotated modules** — the port-granularity rule literally says a record port carrying an
asset is named whole, `"ctrl_i"`. On our 15 modules that is worth at most 0.009 recall, but
**9 of the 10 are in the 26 held-out modules**, so leaving it in would poison the
generalisation test the held-out set exists for. `clk_i` and `rstn_i` are deliberately kept:
neither is ground truth anywhere, both are universal VHDL convention, and they serve a correct
rule.

**Consequence, stated plainly:** because L-1 was never run standalone, **we will never know
whether the leak was doing work.** That is the price of a clean base and it is accepted
deliberately. If it matters later, running `v2` against a leaked variant answers it in one arm.

### Three mechanical fixes to the supplied draft

No wording changed. `{{"IP":` → `{"IP":` (a doubled brace would reach the model literally,
since the ICL splice is a concatenation and never an f-string); and two missing spaces where a
backslash-newline joined words — `(internally).Report` and `stillbelongs`.

### Naming rule — new, and load-bearing

**An arm's version key must never be the baseline key plus `_<tag>`.** `EV.collect()` globs
`assets_tuning18_{v}_r*`, so an arm keyed `v2_e1` would produce `assets_tuning18_v2_e1_r0`,
which that glob matches — the arm's directories would be silently collected as **extra repeats
of the baseline**, corrupting both. Tested:

```
vBASE  -> ['..._vBASE_r0', '..._vBASE_r1', '..._vBASE_r8_r0']   <-- swallowed
vBASEq -> ['..._vBASEq_r0']                                      <-- clean
```

**Arm keys are alphanumeric suffixes only:** `v2e1`, `v2e2`, … `_r` is the separator and
nothing else may look like it.

---

## 4. Working rules, carried over from v1

These are load-bearing and unchanged.

- **NEVER edit the notebook, `prompts*.py`, `eval_assets.py`, `diagnose_step1.py` or any
  `icl_examples_*` module while a run is in progress.** Writing the `.ipynb` reloads the
  editor and kills the kernel. This already destroyed one paid run.
- **One proposition per arm.** A new version is the standing baseline plus exactly one change,
  and pairs against it. Dropping an input block is only half an arm — the prompt's references
  to it must go too.
- **Pre-register `Expect` and a decision rule before running.** Then record `Got:` verbatim,
  including predictions that were wrong.
- **Never quote a delta computed across two changes.** Route every version through the
  `BASELINE` map.
- **Union-over-repeats is an internal ceiling diagnostic only** — never comparable to the
  paper's single-run figures, and only comparable across versions at matched repeat counts.
- **No count, proportion or threshold in a prompt** unless the arm's whole point is to test
  one. A numeric hint becomes a hard quota however it is hedged (A-08's earlier "~20% of the
  closed set" cost 7 of 17 recall losses on `cpu_cp_cfu`). **E-4 deliberately breaks this**,
  which is why it runs last.
- **No literal identifier from any of the 41 annotated modules may enter a prompt.**
  `prompts_v2.audit()` checks the four known ones at import; a newly added example still needs
  `scratchpad/identifier_audit.py`.

---

## 5. Where we start, and where the error is

Everything in this section was re-derived from the run artifacts on 2026-08-08, not copied
forward. `v01c6p1p2` (n=3) is the stand-in for `v2`'s baseline until `v2` actually runs — same
input regime, same ICL, differing only by the D and L corrections.

| | emit | TP | FP | P | recall | F1 |
|---|---|---|---|---|---|---|
| `v01c6p1p2` (n=3) | 404.0 | 98.3 | 305.7 | **0.243** | 0.886 | 0.381 |
| LAsset line 5 | 137 | 101 | 36 | **0.737** | 0.910 | 0.815 |

**With TP held near 100, precision is arithmetic on emissions:**

| target P | emissions allowed | cut needed from 404 |
|---|---|---|
| 0.30 | 328 | 19% |
| 0.40 | 246 | 39% |
| 0.50 | 197 | 51% |
| **0.737** | **133** | **67%** |

### Where the false positives actually are

- **A long tail, not a few offenders.** 285 distinct FP names (323 module-qualified); the top
  20 are 20% of FP mass by name, **11% module-qualified**. A suppression blocklist cannot
  work — the lever has to be a general criterion.
- **By class:** signal-field 47.2%, port 27.3%, signal 24.9%.
- **By objective, the ground truth is** Integrity 75 · Availability 33 · **Confidentiality 3**
  (111 total). Integrity is 68% of the ground truth and 67% of the FPs — proportional, not
  over-claimed. **Confidentiality is the one real outlier**: 3 real assets, 58 claimed per
  repeat, precision 0.144.
- **~50% of FPs are elements LAsset itself calls *secondary* assets.** Our single call does
  Algorithm 1 lines 5 and 6 at once while the reference credits only line 5. Flat near half
  since v0, so no arm caused it — it is structural. *(Inherited from v1 §5, not re-verified.)*
  **Secondary assets stay out of scope** until primary precision is addressed.

---

## 6. What this queue can and cannot reach — measured

This is the most important section for setting expectations, and it is measurement, not
judgement.

**Take `v01c6p1p2`'s own outputs and cheat with the answers.** Delete every *concept* that
produced no true positive at all — the most generous thing a concept-level prompt lever could
ever do:

| | emit | TP | P | recall |
|---|---|---|---|---|
| as generated | 404.0 | 98.3 | 0.243 | 0.886 |
| **every useless concept deleted (oracle)** | **271.7** | **98.3** | **0.362** | **0.886** |
| every false positive deleted (perfect filter) | 98.3 | 98.3 | 1.000 | 0.886 |

**Precision tops out at 0.362.** So **about two-thirds of the remaining false positives live
inside concepts that also produced a true positive.** The model is not mostly chasing wrong
ideas — it is over-binding correct ones.

**That is the structural reason line-5 prompting cannot reach 0.737.** Getting past ~0.36
requires filtering *element by element within a good concept*, and no instruction in a
generation prompt does that — it is a judgement made per candidate asset, after the candidate
exists. **It is exactly what LAsset's refinement stage does**: lines 7–9 take each asset,
build an attack scenario, map it to a CWE, and self-critique. §III-C says plainly that LLMs
over-produce at generation and that refinement exists to filter, measured at precision +0.083,
recall −0.026. *(Paper claims inherited from the v1 log; not re-read from the PDF this
session.)*

**Realistic outcome of this queue: precision 0.30–0.40 at recall ≥ 0.85.** That is a doubling
and still roughly half the paper's line-5 figure. **If matching 0.737 is required, the answer
is implementing lines 7–9, not more line-5 prompting** — a separate study, and the one the
paper's own ablation credits with this job.

**Say this in the write-up rather than letting a reviewer find it.**

---

## 7. Arms

Ordered cheapest-and-safest first, so each arm that lands raises the base for the next. Each is
the standing baseline plus exactly one proposition, with an explicit `BASELINE` entry.

Every headroom figure below was computed on `v01c6p1p2`'s real outputs.

---

### E-1 · Replicated interconnect is not an asset of the module it passes through
**Version `v2e1`. Baseline `v2`. Status: registered, not built, not run.**

The worst FP names are the SoC bus interface repeated in every peripheral — `bus_req_i`,
`bus_rsp_o`, `core_req_i` and kin.

**Measured: 25.3 FPs per repeat, 8.3% of all FP mass, at exactly ZERO true positives.** That
family hits nothing in the ground truth, in any module, in any repeat. Removing it gives
precision 0.243 → **0.260**, recall **unchanged to three decimals**, F1 0.381 → **0.402**.

The proposition is a general criterion, not a name list: *a generic interconnect port
replicated unchanged across many modules carries no asset specific to this module; judge it in
the module whose function is the interconnect.* The carve-out is not needed empirically —
`neorv32_bus`'s own `core_req_i` is also an FP — but it is the correct principle and the
held-out set is the point.

**Expect:** precision **+0.015 to +0.020** · recall **0.000** · emissions −25/repeat · F1 +0.02.
**Decision rule:** precision up and guard passes → promote. Precision null → the model is not
reading the criterion as general; **record it and move on, do not re-word and re-run.**
**Registered risk:** "generic" is a word the model must interpret; over-application would strip
real interface assets. **Port recall is the class to watch.**

**Got:** —

---

### E-2 · Revert the per-concept closure sweep (v1's A-08)
**Version `v2e2`. Baseline: whichever of `v2e1` / `v2` is standing.**

A-08 told the model to re-read the closed set against each concept before moving on. In v1 it
bought recall +0.032 for precision −0.056 and +97 emissions per repeat. **Under a precision
objective that trade inverts**, and it is the largest precision item available from a change we
already understand.

**Expect:** precision **+0.04 to +0.06** · recall **−0.02 to −0.04** · emissions −20%.
**Decision rule.** This arm sits *on the guard by design*, so the rule is fixed now: precision
up **and** recall drop ≤ 0.03 → promote. Drop > 0.06 → reject, the sweep stays. Drop 0.03–0.06
→ **re-run at n=5 and decide there.**
**Registered cost:** A-08 is the only v1 arm that ever moved the union ceiling (0.928 → 0.955).
Reverting it probably gives that back. Acceptable under this objective; recorded so it is not
rediscovered as a surprise.

**Got:** —

---

### E-3 · Tighten what qualifies as a secret
**Version `v2e3`.**

Confidentiality is the one clean outlier in the FP data: **3 real assets, 58 claimed per
repeat, precision 0.144.**

**But the obvious version of this arm would fail the guard, and the data says so.** Of the 58
Confidentiality-labelled emissions per repeat, **8.3 are true positives by element name** — and
only **2.7** are elements the ground truth also calls Confidentiality. The other **5.7 are
correct assets wearing the wrong label**: `uart_rxd_i`, `rs1_i`, `rs2_i`, `mul.prod`,
`csr_wdata_i`, `uart_txd_o`, `valid_o`. **Suppressing Confidentiality claims would cost ~8.3 TP
≈ 0.075 recall — more than twice the guard.**

**And the arm must change shape, because M-2 scores element names only, not objectives.** A
pure re-labelling arm is invisible to the metric. So the proposition is: **tighten the (C)
rubric so that an element qualifying on confidentiality grounds *alone* is not emitted, while
an element that is a genuine asset under (I) or (A) is re-labelled and kept.**

**Ceiling, arithmetic on the measured counts:** perfectly executed — 49.7 FPs dropped, all 8.3
TPs retained by re-labelling — gives emissions 404 → 354.3, precision → **0.277**, recall
unchanged. That is the upper bound; expect less.

**Expect:** precision **+0.015 to +0.034** · recall **0.000 to −0.01**.
**Decision rule:** recall drop > 0.03 means the re-labelling half failed and the arm is
deleting real assets → **reject outright, do not re-word.**
**Hard check, independent of the aggregate:** these three must survive —
`neorv32_cpu_cp_cfu:key_mem`, `neorv32_debug_dtm:jtag_tdo_o`, `neorv32_trng:data_o`. **If any
is lost the arm is rejected regardless of what precision did.**

**Got:** —

---

### E-4 · Per-concept element budget **with a ranking criterion**
**Version `v2e4`. Largest headroom, largest risk. Runs last.**

The model groups its emissions under concepts and emits **4.46 elements per concept** (median
4, p90 8, max 15). The obvious lever is a cap. **A cap alone is worthless, and that is
measured, not argued** — see R-V2-01 below.

**The headroom is entirely in the ranking.** Same cap, same emission count, two orderings:

| cap 4 | emit | TP | P | recall |
|---|---|---|---|---|
| keep the **first** 4 the model wrote | 286.3 | 76.0 | 0.265 | **0.685** |
| keep the **best** 4 (oracle) | 286.3 | 95.7 | **0.334** | **0.862** |

Recall 0.685 vs 0.862 at identical emission counts. **So the proposition is not "emit at most
N per concept" — it is "emit at most N, and here is how to choose which N."**

**Expect** — deliberately stated as a position between two measured lines, which is what makes
this arm worth running. At a cap of 4: precision between **0.265** and **0.334**, recall
between **0.685** and **0.862**.
**Decision rule:** lands near the blind line → **the model cannot rank its own emissions, the
whole budget family is closed, record and stop.** Lands near the oracle line → this is the
largest lever in the study and the cap becomes a tunable parameter.
**Registered rule-break:** this arm puts a number in a prompt, which §4 forbids. That is
deliberate and is the reason it runs last, after the arms that cannot backfire.

**Got:** —

---

### E-5 · Restore port-record granularity — measure before building
**Version `v2e5`, conditional.**

v1's handoff reports port-field FPs going 2.2 → 20.8 across later arms and calls it "A-03's
decay". **That number has not been verified**, and it is the only queue item resting on an
unchecked claim. Port FPs are 27.3% of FP mass, so something is there, but the specific story
needs confirming.

**Registered as: run the scoring-side check on existing artifacts first — no API cost — and
only then decide whether this becomes an arm.**

**Got:** —

---

## 8. Rejected before running

A wrong idea that costs a run is worth recording.

### R-V2-01 · A blind per-concept cap does nothing, and F1 is not the useless metric I called it
2026-08-08. Two claims tested against `v01c6p1p2`'s outputs; both came back against the
proposal that prompted them.

**(a) Emission order carries no confidence signal.** Truncating each concept to its first *k*
emissions, in the order the model wrote them:

| cap | emit | TP | P | recall | F1 |
|---|---|---|---|---|---|
| none | 404.0 | 98.3 | 0.243 | 0.886 | 0.381 |
| 6 | 350.7 | 89.3 | 0.255 | 0.805 | 0.387 |
| 4 | 286.3 | 76.0 | 0.265 | 0.685 | 0.382 |
| 3 | 237.0 | 67.3 | 0.284 | 0.607 | 0.387 |
| 1 | 90.7 | 35.0 | 0.386 | 0.315 | 0.347 |

Good and bad emissions fall in the same proportion. A cap of 4 buys +0.022 precision for
−0.201 recall. **A cap without a ranking criterion is rejected on measurement.** E-4 carries
the surviving half of the idea.

**Stated honestly:** this is post-hoc truncation of existing output, not a prompted cap. A
prompt-level cap could change *which* elements the model picks rather than just cutting the
tail. What is proven is that the model's own ordering is uninformative, so a cap that relies
on it gains nothing — which is why E-4 must supply the ranking rule explicitly.

**(b) F1 was called "the wrong decision metric for this study" and that was backwards.** The
reasoning was that F1 sits between 0.347 and 0.391 across the whole truncation sweep above, so
it is insensitive to the axis this study moves. The flatness is real — but it is a **feature**,
not a defect. Checked against arms that are genuinely good rather than merely smaller:

| | P | recall | F1 |
|---|---|---|---|
| baseline | 0.243 | 0.886 | 0.381 |
| blind cap 4 (pure truncation) | 0.265 | 0.685 | **0.382** |
| E-1 bus rule (real FP removal) | 0.260 | 0.886 | **0.402** |
| oracle cap 4 (real ranking) | 0.334 | 0.862 | **0.481** |

**F1 stays flat when an arm just emits less, and rises when an arm removes false positives
without losing true ones.** That is exactly the discrimination this study needs. F1 is a
reported headline metric, second to precision.

---

## 9. Open threats

Delete a line when it stops being true.

- **Only large effects are detectable.** The paired CI runs about ±0.14 at 15 modules. More
  repeats will not help; more modules would. *(Inherited from v1 §6.)*
- **The tuning set is the reporting set.** All 15 scored modules were used to design v1's arms
  by inspecting misses on them. v2 adds up to five more arms on the same 15. **This is fitting
  to the test set and is the most likely explanation for matching the paper's recall at a third
  of its precision.**
- **No held-out set exists.** The other 26 annotated modules have no RTL in `RTL_data/`. P-2
  makes a held-out run affordable — generation now needs only RTL — and the de-leak makes it
  honest. **This is the highest-value item in the project and it is not an arm**; it needs RTL
  pulled from the NEORV32 repo at the matching revision.
- **L-1 was never measured standalone.** Folded into `v2` by decision (§3), so whether the
  `ctrl_i` leak was doing work is now unknowable without a dedicated arm.
- **`v2` vs any v1 version is not an attributable delta.** It bundles the D correction, the L
  de-leak and a hand transcription. It may be reported as "where we were vs where we are" and
  never as an arm.
- **Three NEORV32 revisions in play.** `RTL_data` v1.11.4.3, `neorv32/rtl/core` v1.11.0.6,
  datasheet v1.11.2. Two of the 111 references cannot exist in our RTL revision, both in
  `neorv32_cache`, so **aggregate recall tops out at 0.982**.
- **Paper claims in §1 and §6 are inherited from the v1 log, not re-read from the PDF** in this
  session — specifically the refinement effect (+0.083 precision, −0.026 recall) and the §III-C
  over-production statement. Verify before they go in a write-up.
- **Cost per arm not yet estimated.** Rates are input $0.25/1M, cached $0.025/1M, output
  $2.00/1M, but token counts for the `v2` prompt are unmeasured. First run settles it.
