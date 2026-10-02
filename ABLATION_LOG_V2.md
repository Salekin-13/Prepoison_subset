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

### Version `v2`, core sha `89efcccf1b55` (7 412 chars) · composed core+ICL sha `ea0608b316dc` (70 262 chars)

The composed sha is the one the run loop stamps into `_run_meta.json`.

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

### Three corrections folded into the baseline

All three are in `prompts_v2.py` as separate reversible functions, so they are visible as edits.

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
generalisation test the held-out set exists for.

**N — neutralise the remaining real identifiers, and declare the survivors illustrative.**
L-1's test was *"is this identifier an answer?"*, and by that test `clk_i` and `rstn_i` passed
and were kept. **That was the wrong test.** The rule read *"Global clock/reset ports (e.g.
`clk_i`, `rstn_i`) … are NOT assets"*. Neither is ground truth anywhere — but **`clk_i` is
declared 24 times and `rstn_i` 22 times across the 15 scored modules**, so the prompt stated a
correct *negative* fact about 46 real elements of the evaluation set. In a recall study that is
nearly free. In a precision study it is a leak pointing the right way: bounded at **+0.025
precision** if the model would otherwise have named them all — more than arm E-1's entire
expected gain. Measured: even with the rule in force the model still emits `rstn_i` twice across
45 module-repeats, so the rule is doing real suppression work. The rule survives without the
examples; *"Global clock and reset ports"* is unambiguous.

`ZBT_addr` / `ZBT_addr2` go too, for a different reason. They are **not** NEORV32 names — they
come from IEEE P3164 §3.2.4's SRAM controller, verified absent from all 1 355 parsed and 218
ground-truth names. They are removed because **a quoted identifier is a naming template the
model copies**, and keeping only invented names makes the standing rule checkable by one
substring sweep instead of by remembering which real names were once judged harmless.

`cfg_port_i` / `cfg_port_i.mode` / `blk_ctrl.step` / `xfer_unit.stage` stay: they are invented,
and the granularity rule cannot be stated without showing a record and one of its fields.

**The new RULES bullet is the point of this correction, not a footnote.** v1 evidence: `ctrl_i`
was quoted as a naming example and became the single worst false positive in the whole study
(`cpu_pmp:ctrl_i`, 7 occurrences over 3 repeats). **The model copies quoted identifiers into its
output.** The bullet states that quoted identifiers are illustrations, that none exists in the
target module, and that no name may be emitted unless it was read in the RTL.

**Verified after the edit:** every token in the core swept against all 1 355 parsed names and
235 ground-truth names returns **six hits, all ordinary English used as English** —
`condition`, `enable`, `engine`, `level`, `state`, `timeout`. No identifier survives.

**The contract's placeholder concept went too.** It read *"e.g. 'watchdog timeout
configuration'"* — not an identifier, which is why it passed every name sweep, but
`neorv32_wdt` is one of the 15 scored modules and `ctrl.timeout` is a ground-truth asset in it,
so the contract's throwaway example described a real answer. Now `'sensor calibration
constants'`: verified that neither *sensor* nor *calib* occurs in any of the 1 355 parsed
names, any of the 235 ground-truth names, or any of the 41 module names. After this, **no
function word belonging to any scored module survives in the core.**

### Residuals recorded, deliberately not removed

Found by the same sweeps; each is kept for a stated reason. Recorded so they are not
rediscovered as surprises, and so a reviewer sees they were considered.

**The Confidentiality rubric — cannot be removed, because removing it IS arm E-3.** The rubric
reads *"Genuine secrets are keys, seeds, entropy/random state, or private plaintext."* Two of
our three Confidentiality ground-truth assets are pointed at by that list: `key_mem`
(cpu_cp_cfu) by *keys*, `data_o` (trng) by *entropy/random state*. That is a real prior. But it
is also standard CIA taxonomy that any asset-identification prompt states, it is inherited from
V0, and **replacing the enumeration with a criterion is precisely arm E-3's proposition.**
Folding it into the baseline would consume the arm and leave nothing to measure. It stays until
E-3 measures it.

**P3164's AES and SRAM citations** (`AES engine`, `Memory Array`, `SRAM controller`). Real, but
from the standard being followed, not from NEORV32. `neorv32_cpu_cp_crypto` is in the 41 but
**not** in our 18, so nothing scored is affected. Removing them would break the method's
citation to the standard it claims to implement.

**The ICL case studies are `omsp_gpio` and `tiny_aes`.** `neorv32_gpio` and
`neorv32_cpu_cp_crypto` are both in the 41 — **neither is in our 18**, so no scored module is
touched. On a held-out run those two modules get an advantage `neorv32_xbus` does not, and that
should be footnoted rather than fixed: the paper's own case studies are AES, GPIO and a
Gaussian Noise Generator, so this exposure is faithful replication, and identifier overlap is
**zero** (verified: the 18 elements the examples name as assets collide with nothing in the
ground truth).

**Tuning-set fitting is the deepest leak and no sweep can find it.** A-02's role list, A-03's
granularity rule and A-08's closure sweep were each designed after inspecting misses on these
same 15 modules. A-02's roles — *"an operation enable or start, a direction or mode select, a
computed result, a busy/ready/error condition"* — read as generic role language, but they are a
paraphrase of the specific elements that were being missed. This cannot be edited out; the only
cure is the held-out set. See §9.

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

## 5. v2 baseline — RESULT, 2026-08-08

Run: 3 repeats × 18 modules, scored on the 15 common modules / 111 references, metric M-2.
`_run_meta.json` sha `ea0608b316dc…` — matches the registered prompt.

**All figures below are the MEAN over the 3 repeats** unless a row says *union*. Never a
single run: one run cannot separate a prompt effect from sampling noise.

| | emit | TP | FP | **P** | recall | F1 |
|---|---|---|---|---|---|---|
| `v01c6p1p2` (n=3) | 404.0 | 98.3 | 305.7 | 0.243 | 0.886 | 0.382 |
| **`v2` (n=3)** | **412.7** | **102.7** | **310.0** | **0.251** | **0.925** | **0.394** |
| LAsset line 5 | 137 | 101 | 36 | 0.737 | 0.910 | 0.815 |

Paired vs `v01c6p1p2`: precision **+0.024** [+0.007, +0.042] · recall **+0.033** [+0.002,
+0.073] · F1 **+0.027** [+0.008, +0.045]. All three CIs exclude zero.

**Guard: passes trivially — recall rose.**

**Union over the 3 repeats: 0.937 → 0.955 (104 → 106 of 111).** Only A-08 had ever moved the
ceiling before. Newly reachable: `cpu:lsu_wait`, `debug_dtm:jtag_tms_i`. Nothing lost.

### Got vs Expect — the prediction was wrong

Registered Expect was *"approximately `v01c6p1p2`: P 0.243, recall 0.886, emit 404, F1 0.381.
The de-leak may cost up to 0.009 recall,"* with a decision rule keyed on recall **falling**.
**Recall rose 0.033 and precision rose 0.024.** A predicted null came back as a significant
three-way improvement. Recorded because the log's standard is to record predictions that were
wrong, and because the error was directional, not just in magnitude: the whole Expect was
framed around a cost that did not exist.

### Mechanism — what each correction actually did

`v2` bundles D, L, N and a hand transcription, so **the aggregate delta is not attributable**.
These are name-level observations, which are.

**D (closed-set parity) — the largest effect, and it is about binding.**

| | emissions | ungrounded names |
|---|---|---|
| `v01c6p1p2` | 1 479 | **187 (12.6%)** |
| `v2` | 1 425 | **106 (7.4%)** |

The old text said *"MUST be the exact name of one element from the provided ports/signals"*
while no ports/signals were provided. Making the instruction coherent cut ungrounded names by
**43%**. Best available explanation for both deltas.

**L (de-leak) — the third branch of the L-1 hypothesis is now measured.** `ctrl_i` emissions
fell 13 → 8 over three repeats, all of it in `cpu_pmp` (10 → 5). `ctrl_i` *is* ground truth
there, once, so the old 10 were ~3 true and ~7 duplicates. **`cpu_pmp` recall stayed 1.000
while its emissions fell 21.0 → 18.3.** L-1 predicted this exact outcome as its third branch:
*"the names were pulling emissions toward `ctrl*` where that was wrong."*

**N (dropping `clk_i`/`rstn_i` from the clock/reset rule) — cost ~1.7 FP per repeat.**
`clk_i` went 0 → 5 across three repeats; `rstn_i` stayed at 2. Against the **46** upper bound
computed before the run. The generic wording holds; precision cost ≈ 0.001. **Removing that
leak was nearly free, which the pre-run analysis could not establish.**

**The "identifiers are illustrations" bullet — 0 copies, but weak evidence.** None of the four
invented names was emitted. They exist in no RTL, so the model could not have bound them
anyway. The real test is `ctrl_i`: real, no longer quoted, still emitted 8 times — those are
RTL-driven, not copied. **The bullet may be working; this run cannot show it.**

### Where the recall came from

| class | recall | FP |
|---|---|---|
| port | 0.894 → **0.936** | 83.3 → **110.0** |
| signal | 0.875 → **0.948** | 76.0 → **68.3** |
| signal-field | 0.914 → 0.914 | 144.3 → 129.3 |

**Signal recall +0.073 at lower FP is a free gain. Port recall +0.042 was bought with +27 FP.**

**But the aggregate hides that two modules did it:**

| module | recall | emit |
|---|---|---|
| `neorv32_bus` | 0.727 → **0.939** | 41.7 → **70.0** (P 0.148) |
| `neorv32_debug_dtm` | 0.667 → **0.867** | 21.0 → 22.0 |
| `neorv32_cache` | 0.667 → **0.611** | 39.7 → 38.7 |
| the other 12 | flat or ±0.056 | — |

~3.3 of the 4.4 TP gain is those two. `bus` bought its share with a 68% emission rise;
`debug_dtm` gained at flat emissions and is the only clean one. `cache` is the sole regression.

### What did not change

**The precision problem.** P 0.251 against 0.737; 310 FP against 36. **Emissions went up**,
404 → 413. We gained precision by adding true positives, not by removing false ones. The
marginal 8.7 emissions split about half TP / half FP — better than the 0.25 average, and
irrelevant to the 310 that were already there.

---

## 5b. Where the error is now — measured on v2

**Two distinct failure modes, and the smaller one is the intuitive one.**

| pattern | share of all FP |
|---|---|
| **many DISTINCT fields of one record, each emitted once** | **33.4%** |
| the SAME name emitted twice or more in one module-repeat | 10.2% |

They overlap slightly. One example carries both — `neorv32_uart` r0, base `ctrl`, 13 objects
for 3 real assets:

```
TP  ctrl.enable          C3        GT for neorv32_uart:
FP  ctrl.sim_mode        C3          clkgen_en_o, ctrl.baud, ctrl.enable,
FP  ctrl.hwfc_en         C3          ctrl.prsc, irq_rx_o, irq_tx_o,
TP  ctrl.prsc            C3          uart_ctsn_i, uart_rtsn_o,
TP  ctrl.baud            C3          uart_rxd_i, uart_txd_o
FP  ctrl.irq_rx_nempty   C3
FP  ctrl.irq_rx_half     C3        -> 12 distinct fields emitted, 3 are assets
FP  ctrl.irq_rx_full     C3        -> ctrl.prsc emitted TWICE, under C3 and C7;
FP  ctrl.irq_tx_empty    C3           the second is an FP because the reference
FP  ctrl.irq_tx_nhalf    C3           holds ctrl.prsc once
FP  ctrl.clr_rx          C3
FP  ctrl.clr_tx          C3
FP  ctrl.prsc            C7   <- duplicate
```

Worst groups in `v2`: `twi` r1 `fifo` 13 fields/13 FP · `uart` r0 `ctrl` 13/10 · `uart` r0
`tx_fifo` 10/10 · `spi` r0 `tx_fifo` 8/8.

Across all modules, record groups of ≥5 fields hold **369 emissions: 56 TP, 313 FP** —
precision **0.15** inside them.

**A-03 does not cover this.** Its rule is that record *PORTS* are named whole; for internal
records it says explicitly that the field is the asset. Every group above is an internal record.

**New pathology, absent from v1:** max elements bound to one concept went 15 → **53**.
`neorv32_bus` r2 declared *"Master request record (address, data and control fields: addr,
data, stb, lock, amo, amoop, rw, priv, debug, src, fence, ben)"* and bound 53 elements to it.

**`neorv32_bus` alone is 59.7 FP per repeat = 19.2% of every false positive in the study**, at
70 emissions per repeat and precision 0.148. Its FPs are mostly bare names, not record fields
(dotted share 8.4%) — that module has 811 parsed ports.

---

## 5c. Where we started, and where the error was

Kept for the record; superseded by §5b for anything v2-related.

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

### S-1 · Container vs content — FIRST ARM OF THE REVISED PLAN
**Version `v2s1`. Core sha `9e6b061bf20b` (8 117 chars) · composed `4fcdac76cce3` (70 967).
Baseline `v2`. Built 2026-08-09, not yet run.**

**Proposition.** A structure that stores or carries data is an asset only when what it holds
is itself an asset. Otherwise the structure and its fields are influencing elements and the
asset is the content, named where the design produces or holds it.

**Target, measured on v2's own output.** Every false positive split by whether the model found
the right record:

| | count / 930 | share |
|---|---|---|
| dotted, record **has** a GT asset — right register, extra fields | 163 | 17.5% |
| dotted, record has **no** GT asset — wrong register entirely | **225** | **24.2%** |
| not a record field | 542 | 58.3% |

This arm targets the middle row. Worst offenders: `twi:fifo` 34, `uart:tx_fifo` 21,
`uart:rx_fifo` 20, `spi:tx_fifo` 19, `twi:engine` 16, `spi:rtx_engine` 15,
`cpu_cp_cfu:xtea` 15, `twi:io_con` 14. **Ceiling: emit 412.7 → 337.7, precision
0.251 → 0.304, recall unchanged.**

**Why this is a real distinction and not a name list.** The reference applies it consistently:
`trng`'s `fifo` fields ARE assets (the buffer holds entropy) while `twi`'s, `uart`'s and
`spi`'s are not (the same structure holding ordinary traffic); `cpu_cp_cfu:key_mem` is an
asset while the `xtea` cipher's internals are not. **The model names the machinery; the
reference names what the machinery protects.**

**Grounding.** SA-EDI Table 2 types the *content* — *"Secret: Material that requires
confidentiality"*, *"Critical: Material that is critical for proper functionality"* — never
the vessel. P3164 §3.1.2 asks for the RTL that produces, stores and transports *a conceptual
asset*, so a transport structure is in scope only once a conceptual asset exists to transport.
This rule states the precondition the prompt was missing.

**Leakage audit:** 0 collisions against all 1 355 parsed and 235 ground-truth names; no word
matching any of the 41 module stems. An earlier draft said *"transfer engine"* and was
rejected — `engine` is a real record base in `neorv32_twi` and one of the top FP sources.

**Baseline is byte-identical.** `ASSET_V2_BASE` still hashes to `89efcccf1b55`, composed
`ea0608b316dc`. The arm round-trips: removing the rule reproduces the baseline exactly.

**Expect:** precision **+0.02 to +0.05** · recall **−0.01 to −0.02** · emissions −40 to −75.
**Decision rule:** precision up and guard passes → promote at n=5. Precision null → the model
is not applying the content test; **record and move on, do not re-word.**
**Hard checks, independent of the aggregate** — these must survive, or the arm is rejected
whatever precision did: `neorv32_trng:fifo.avail`, `fifo.free`, `fifo.re` (a buffer that IS an
asset) and `neorv32_cpu_cp_cfu:key_mem` (content inside a crypto block).

**Got: NULL on precision. Arm rejected; baseline stays `v2`.** Run sha `4fcdac76cce3`, n=3.

| | emit | TP | FP | P | recall | F1 |
|---|---|---|---|---|---|---|
| `v2` | 412.7 | 102.7 | 310.0 | 0.251 | 0.925 | 0.394 |
| `v2s1` | 425.0 | 104.0 | 321.0 | **0.246** | **0.937** | 0.389 |

Paired: precision **−0.009** [−0.023, +0.006] · recall **+0.010** [−0.010, +0.034] · F1
−0.006. **All three CIs include zero.** Recall 0.937 is the highest in the study.

**All four hard checks passed** — `trng:fifo.avail`, `fifo.free`, `fifo.re` and
`cpu_cp_cfu:key_mem` survived. The rule did not become a blanket ban.

**The target group did not move.** Splitting every FP the same way the arm was designed:

| FP group, per repeat | `v2` | `v2s1` | delta |
|---|---|---|---|
| dotted, record **has** a GT asset | 54.3 | 54.3 | **+0.0** |
| dotted, record has **no** GT asset ← the target | 75.0 | 76.0 | **+1.0** |
| not a record field | 180.7 | 190.7 | **+10.0** |

The eight named offender records moved **+3 across three repeats** (`twi:fifo` +2,
`uart:tx_fifo` −2, `spi:tx_fifo` −2, `twi:io_con` −3, `xtea` +1). Noise. All growth is in
non-record emissions.

**Mechanism, and it is in the rule itself.** The rule made a container an asset *"only when
what it holds is itself an asset: a secret, a credential, **entropy**, or privileged
configuration."* **In the TRNG everything holds entropy**, so the exception fired universally
there:

| `neorv32_trng` | `v2` | `v2s1` |
|---|---|---|
| emissions/repeat | 14.0 | **20.0** (+43%) |
| distinct non-GT names | 12 | **20** |
| non-GT emissions/repeat | 8.7 | **13.7** |

New false positives were `cell_rnd`, `sample_sreg`, `fifo.wdata`, `fifo.we`, `fifo.rdata`,
`fifo.clear` — exactly the buffer fields the reference excludes. **A restrictive rule whose
carve-out is security-relevant becomes a licence in security-relevant modules**, which are the
modules that matter. Recorded as the reason not to re-word and re-run: any revival of this
idea must drop the carve-out entirely.

**One positive signal, verified.** Bus-interface FPs fell without being targeted —
`wdt:bus_rsp_o` −5, `uart:bus_req_i` −3, `uart:bus_rsp_o` −3, `wdt:bus_req_i` −2,
`sys:clk_i` −5. The phrase *"ordinary traffic the module exists to move"* did land for the
fabric case. Evidence that S-3 is viable, and a reason to run it after R-8.

**What this says about the prompt.** Fan-out **rose** in the run where a restrictive rule was
added: elements/concept 4.49 → 4.69, while concepts/module stayed flat (6.16 → 6.11). The
model did not conceive more; it bound more to each concept. **Hypothesis, not verified:** the
A-08 closure sweep is cancelling restrictive additions. R-8 is the direct test.

---

### R-8 · Revert the A-08 per-concept closure sweep
**Version `v2r8`. Core sha `8c4024a9b168` (6 862 chars, −550) · composed `e02218e4c95d`
(69 712). Baseline `v2`. Built 2026-08-10, not yet run.**

**The only arm that removes rather than adds**, and that is the point: nothing design-specific
can leak through a deletion, so it carries **zero overtuning risk by construction**. Verified
as a clean excision — the unified diff against `ASSET_V2_BASE` is exactly the two sweep
paragraphs and nothing else; `ASSET_V2_BASE` still hashes to `89efcccf1b55` / `ea0608b316dc`.

**What is removed:** *"CLOSE EACH CONCEPT… make one more pass over the closed set for that
asset alone… **Add every one that does**… A conceptual asset is finished when the closed set
has been read against it — **not when its elements stop coming readily**."*

**Measured effect when it was ADDED** (v1, `v01c5` → `v01c6`, one edit): emissions
**331.2 → 428.0** (+96.8/repeat, the largest single-edit jump in the study), precision
**0.285 → 0.229**, recall **0.849 → 0.881**, union ceiling **0.928 → 0.955**. Good trade under
a recall objective; it inverts under a precision one.

**Deliberately still present** (one proposition per arm): *"may fan out to SEVERAL elements"*
and A-02's *"ask BOTH"*. If R-8 lands, those become the next candidates.

**Expect:** precision **+0.04 to +0.06** · recall **−0.02 to −0.04** · emissions −20%.

**Guard arithmetic, written before the run.** Baseline recall 0.925, floor 0.895. A symmetric
revert of A-08's +0.032 lands near **0.893 — inside the indeterminate band**, so promotion
requires n=5 whatever the point estimate says. Recall being at an all-time high is what makes
this affordable now.

**Decision rule:** precision up and recall drop ≤ 0.03 → promote at n=5. Drop > 0.06 → reject,
the sweep stays. Drop 0.03–0.06 → re-run at n=5 and decide there.

**Registered cost:** A-08 is the only arm that ever moved the union ceiling. Reverting it
probably gives that back. Accepted.

**Got: mechanism CONFIRMED, precision NULL. Arm not promoted; baseline stays `v2`.** Run sha
`e02218e4c95d`. Scored on the 15 modules common to `v2`/`v2r8`/`v2x3`/`v2x3r8`.

| | n | emit | TP | FP | P | recall | F1 |
|---|---|---|---|---|---|---|---|
| `v2` | 3 | 412.7 | 102.7 | 310.0 | 0.251 | 0.925 | 0.394 |
| `v2r8` | 3 | 367.7 | 99.7 | 268.0 | **0.271** | **0.898** | 0.416 |
| `v2r8` | 5 | 375.0 | 99.0 | 275.0 | **0.265** | **0.895** | 0.409 |

Paired, matched n=3: precision **+0.005** [−0.011, +0.019] · recall **−0.019** [−0.044,
+0.009] · F1 +0.007 [−0.011, +0.022]. **All three include zero.**
Paired at n=5 vs `v2` at n=3 (unmatched, the comparison as first run): precision **−0.000**
[−0.014, +0.012] · recall **−0.024** [−0.043, −0.007] **\*** · F1 −0.000. Extending to 5 moved
precision *down* and made the recall loss distinguishable. **Read the matched row.**

**The mechanism is confirmed — this is the value of the arm.** The sweep was doing exactly what
it was described as doing:

| | `v2` | `v2r8` |
|---|---|---|
| elements/concept | 4.47 | **3.76** |
| max elements on one concept | 53 | **12** |
| concepts/module | 6.16 | **6.53** (+0.37) |

Removing the closure sweep cut fan-out by 16% and cut the worst single-concept blow-up by 77%.
**Concept count rose while element count fell** — the model did not conceive less, it bound
less to each concept. That confirms the S-1 hypothesis: the sweep was cancelling restrictive
additions.

**The registered cost did not materialise.** Union ceiling over repeats is **0.946 for both**
`v2` and `v2r8` — unchanged. Reverting A-08 did not give back what adding it bought. Recorded
as a prediction that was wrong.

**Guard: passes at n=3 (0.925 → 0.898, drop 0.027), lands on the floor at n=5 (0.895).** The
pre-registered arithmetic said this would land near 0.893 inside the indeterminate band, and
it did. That part of the prediction held.

**Why it is not promoted.** Precision is the primary metric and it is a null at both n. The
arm buys a confirmed mechanism and no measurable precision. **It is not rejected either** —
it is the only edit in the study with a demonstrated, quantified handle on fan-out, and X-3R-8
below shows what it does when combined.

**One class moved on its own:** signal recall −0.025 [−0.050, −0.005] at n=3 and −0.023
[−0.046, −0.005] at n=5 — distinguishable at both. Ports and signal-fields did not move.

---

### X-3 · A third ICL case study — composition-matched negative examples
**Version `v2x3`. Core sha `89efcccf1b55` — BYTE-IDENTICAL to `v2`. ICL
`icl_examples_01b_ot.ICL_ASSET_EXAMPLES_01B_OT` (103 676 chars) · composed `bdd9bb375f12`
(111 090 chars). Baseline `v2`. n=3.**

**⚠ RUN WITHOUT PRE-REGISTRATION.** No `Expect` and no decision rule were written before this
ran, in violation of §4. It is therefore adjudicated **against the standing §2 guard only**,
and no target is retrofitted. Recorded this way deliberately.

**Proposition.** Only the ICL moves. A third worked case study — OpenTitan `gpio`, selected by
surveying all 21 golden asset lists in `Asset_Asset_Dataset_Statistics_IPs.xlsx` as the one IP
where internal-signal assets dominate (3 of 5) — adds explicit **NON-asset** reasoning to the
example block. The five asset labels are the repository's own, verified identical to the xlsx;
only the reasoning and the rejections are ours.

**Got: NULL on precision, guard passes. Arm not promoted.**

| | emit | TP | FP | FN | P | recall | F1 |
|---|---|---|---|---|---|---|---|
| `v2` | 412.7 | 102.7 | 310.0 | 8.3 | 0.251 | 0.925 | 0.394 |
| `v2x3` | 391.3 | 100.0 | 291.3 | 11.0 | **0.259** | **0.901** | 0.402 |

Paired: precision **−0.005** [−0.024, +0.012] · recall **−0.016** [−0.049, +0.016] · F1
−0.003 [−0.023, +0.017]. **All three include zero.** Guard: aggregate drop 0.024 → **passes**.

**Pooled and paired precision disagree in sign.** Pooled rose (0.251 → 0.259); paired fell
(−0.005) with 10 of 15 modules better and 5 worse. The losers lost more than the winners
gained; the pooled figure is carried by the highest-emission modules. **Report the paired
number.**

**Where the recall went: 75% of it is one module.** Total FN 8.3 → 11.0 (+2.67/repeat);
`neorv32_bus` alone went 0.67 → 2.67. Attributing the six extra bus FNs over three repeats:

| GT element | class | missed `v2` | missed `v2x3` |
|---|---|---|---|
| `keeper.cnt` | signal-field | 0/3 | **2/3** |
| `keeper.halt` | signal-field | 0/3 | **2/3** |
| `state` | signal | 2/3 | 3/3 |
| `stb` | signal | 0/3 | 1/3 |

`keeper.cnt` + `keeper.halt` are **4 of the 8 extra FNs across the whole run** — half the
recall loss is two fields of one record in one module.

**Two failure modes ruled out.** *Not coverage:* all six repeats emitted from
`neorv32_bus_gateway`, the entity declaring `keeper`, and all six formed a timeout concept.
*Not container-for-content:* no repeat emitted bare `keeper`; `v2x3` r0/r1 emitted
`keeper.err` and `keeper.lock` explicitly. The record was expanded, just not as far.

**`state` and `stb` are not attributable to the arm.** The bus reference lists `state`
**twice** (two entities in the file) and M-2 does not collapse same-name elements, so matching
both requires emitting `state` twice — `v2` r2 happened to, no `v2x3` repeat did. `stb` was
missed only in the 40-emission repeat.

**`neorv32_bus` is the wrong module to conclude anything from.** Emission sd is **41.6** (`v2`)
and **48.3** (`v2x3`) on means of 70.0 and 61.7, five times the next noisiest module
(`twi`, 9.0), and visibly bimodal — roughly 28–48 or ~118.

**A causal claim made here and then withdrawn.** The first analysis attributed the keeper loss
to this example's line *"the asset is the decision, not the inputs that produce it."*
**Withdrawn — `v2r8` r0, which uses the baseline `v2` ICL and never sees this prose, produced
the identical `{keeper.err, keeper.lock}` pattern.** The pruning is reachable from the core
edit alone; rewriting that sentence would not have prevented it. See X-3R-8.

**What the arm did measurably do:** elements/concept 4.47 → 4.15, signal-field FP 129.3 →
118.7 with signal-field recall 0.914 → 0.882. It prunes record fields, removing true and false
ones together. **Same axis as R-8, roughly 40% of the distance.** It is not an independent
proposition, which is the finding that matters.

---

### X-3R-8 · R-8 core + X-3 ICL — the combination
**Version `v2x3r8`. Core `8c4024a9b168` (`ASSET_V2_R8`) + ICL `ICL_ASSET_EXAMPLES_01B_OT`
= 110 540 chars, run sha `3c543758f459`. Baseline `v2`. n=3.**

**⚠ RUN WITHOUT PRE-REGISTRATION**, same as X-3. Adjudicated against the standing guard only.
The one prediction the design does imply is **additivity of two separately-measured arms**, and
that is what is tested below.

**Got: GUARD FAILS. Arm rejected. First distinguishable precision gain in the study.**

| | emit | TP | FP | FN | P | recall | F1 |
|---|---|---|---|---|---|---|---|
| `v2` | 412.7 | 102.7 | 310.0 | 8.3 | 0.251 | 0.925 | 0.394 |
| `v2x3r8` | 319.7 | 94.7 | 225.0 | 16.3 | **0.296** | **0.853** | **0.439** |

| paired vs `v2` | d | 95% CI | |
|---|---|---|---|
| precision | **+0.025** | [+0.013, +0.038] | **\*** 12 better / 1 worse |
| F1 | **+0.023** | [+0.008, +0.038] | **\*** 12 better / 1 worse |
| recall | **−0.054** | [−0.096, −0.016] | **\*** 2 better / 9 worse |

**Guard: aggregate recall 0.925 → 0.853, drop 0.072 > 0.06 → FAILS, arm rejected.**
The paired estimate (−0.054) lands in the *indeterminate* band, so the two readings disagree.
**The aggregate governs**, per the precedent set by R-8's own guard arithmetic, which is
written in ablate-table numbers. Noted: `v2x3r8`'s recall sd is **0.055**, the largest of any
arm — this is the least stable point estimate in the study.

**v2, S-1, R-8 and X-3 were all precision nulls. This is the first arm to clear the bar** — and
it does so by breaking the guard, which is precisely the trade the guard exists to refuse.

**The additivity prediction failed — super-additive in suppression.**

| metric | `v2` | `v2r8` | `v2x3` | additive | observed | excess |
|---|---|---|---|---|---|---|
| precision | 0.251 | 0.271 | 0.259 | 0.279 | **0.296** | **+0.017** |
| recall | 0.925 | 0.898 | 0.901 | 0.874 | **0.853** | **−0.021** |
| emissions | 412.7 | 367.7 | 391.3 | 346.3 | **319.7** | **−26.7** |
| port recall | 0.936 | 0.915 | 0.915 | 0.894 | **0.837** | **−0.057** |

**Because they are not two propositions.** Elements/concept: 4.47 → 3.76 (R-8) → 4.15 (X-3) →
**3.54** (combined); max elements bound to one concept 53 → 12 (R-8) → 47 (X-3) → **20**
(combined). Both edits turn the same dial, so stacking them overshoots.

**The cost is the port class, and it is the only distinguishable class:**

| class | paired recall d | CI | |
|---|---|---|---|
| port | **−0.120** | [−0.202, −0.043] | **\*** 8 of 12 modules worse |
| signal | −0.035 | [−0.083, +0.000] | null |
| signal-field | −0.037 | [−0.148, +0.037] | null |

Port FN events rose 9 → 23 over three repeats (inputs 7 → 16, outputs 2 → 7). Newly missed:
`twi:twi_sda_i` (3/3), `uart:uart_rxd_i`, `cpu:mei_i`, `cpu:mti_i`, `cpu_cp_cfu:start_i`,
`cpu_pmp:addr_ls_i`, `spi:spi_dat_o`, `wdt:clkgen_en_o` — interface data and control lines.

**THE FINDING: the pruning is aimed at the wrong class.**

| class | `v2` precision | `v2` FP/rep | emissions cut by `v2x3r8` |
|---|---|---|---|
| port | 0.286 | 110.0 | **−31.4%** |
| signal | 0.307 | 68.3 | −18.2% |
| signal-field | **0.180** | **129.3** | **−16.9%** |

**It cut hardest into the class with the best precision and least into the class carrying the
worst precision and the most false positives.** `signal-field` is where the FP problem lives
and it is the class the pruning barely touched.

**It is not merely truncating, and this is worth keeping.** At its emission volume, random
pruning at `v2`'s TP rate (0.2488) predicts 79.5 TP; it delivered 94.7 — **15.1 TPs retained
above chance**, the best selectivity of the four arms (`v2r8` +8.2, `v2x3` +2.6). FP rate
75.1% → 70.4%. The pruning is genuinely preferential, just class-blind.

**First arm to cost the union ceiling.** Union recall over repeats: `v2` 0.946, `v2r8` 0.946,
`v2x3` 0.946, **`v2x3r8` 0.928**. Two GT elements became unreachable in every repeat.

**What this buys the study.** Precision is movable by a measurable amount (+0.025, CI excludes
zero) and the price is now priced exactly. Every precision gain in v2 so far comes from one
class-blind dial that trades TP and FP together. **The next arm must be class-aware:** target
`signal-field` (P 0.180, 129.3 FP/repeat) while leaving port emission volume alone. That is a
different proposition from anything in §7 and it can be stated without reference to which
modules are in the test set.

---

### S-3 · Routed traffic belongs to the fabric, not to every stop along it
**Version `v2s3`. Core sha `32f14a69f9b1` (8 851 chars, +1 439) · composed core+ICL
`6bd762261967` (71 701). Baseline `v2`. ICL is the BASELINE block. Built 2026-08-11, not yet
run.** Supersedes E-1.

**One change from `v2`: a single RULES bullet.** Round-trip verified — deleting the bullet
reproduces `ASSET_V2_BASE` byte-for-byte, which still hashes `89efcccf1b55` / `ea0608b316dc`.

**The first arm in the study whose mechanism is SELECTIVE rather than volumetric.** Every
precision gain so far came from one class-blind dial (elements/concept) that removes TP and FP
together. This arm is defined by what an element *is*.

**Headroom, measured on `v2`'s own output — structural definition, not a name list:**

| definition | FP/rep removed | TP removed | precision | recall |
|---|---|---|---|---|
| root name is a port in ≥6 of 18 modules | 25.0 | 0.0 | +0.016 | unchanged |
| **declared type is the shared interconnect record** | **76.0** | **0.0** | **0.249 → 0.305 (+0.056)** | **unchanged** |
| same test applied to the CONTROL record (contrast) | 24.3 | **16.7** | **−0.017** | **0.925 → 0.775** |

76.0 FP/repeat is **25% of all false positives**. The 25.0 row is why E-1's original figure was
wrong: a name-based instrument misses the internal pass-through records.

**Zero TP loss even inside the interconnect module.** `neorv32_bus` declares **91** elements of
the shared request/response record types; **not one is a reference asset**. The reference names
`a_req`, `b_req`, `sel`, `port_sel`, `stb`, `keeper.*`, `state` — plain scalar internals, the
*decisions*. The annotation already draws this exact line in the module carrying 45.3 of the
76.0 FP/repeat.

**The control-record row is the arm's own safety proof.** The record a module **acts on** is an
asset; the record it **forwards** is not. Applying the identical structural test to the wrong
record type costs 0.150 recall and *lowers* precision. This is why the rule is a criterion and
not a blocklist.

**Why the carve-out is safe here and was not in S-1.** S-1's exception was keyed on *security
relevance* — "a secret, a credential, entropy, or privileged configuration" — so in the module
that is entirely about entropy it fired universally and the restrictive rule became a licence.
S-3's exceptions are keyed on **structural facts checkable in the RTL**: does the traffic change
representation here, does it leave the design here. **Both are false in the modules that carry
the headroom**, and both are true exactly where the reference says they should be.

**Generalisation, checked against the other 26 annotated modules.** A protocol bridge lists 8 of
its 9 assets on the foreign-protocol side; a streaming link lists 13 external stream ports.
Neither uses the internal shared record type, so a **type**-scoped rule never reaches them — but
a rule phrased as *"bus interface signals are not assets"* would reach them and gut both. The
bullet therefore turns on **origination, transformation and design boundary**, never on what an
interface is named. **The rule contains zero identifiers** — asserted at import.

**Exception (2) protects precisely what X-3R-8 destroyed:** that arm's damage was port recall
−0.120 [−0.202, −0.043], and the newly missed elements were device-facing and off-chip lines.

**Built on `ASSET_V2_BASE`, not `ASSET_V2_R8`** — stacking it on R-8 would confound a selective
criterion with a fan-out reduction, the confound that made X-3R-8 uninterpretable.

**Expect:** precision **+0.035 to +0.056** · recall **0.000 to −0.010** · emissions **−60 to
−80**/repeat · elements/concept **unchanged near 4.47**.

The precision range is the measured headroom discounted for the model applying a criterion by
judgement rather than by type lookup. **The recall Expect is 0.000 by construction** — no arm
before this could say that, and it makes S-3 a clean test of the guard machinery as well.

**Decision rule:** precision up **and** recall drop ≤ 0.03 **and** all hard checks pass →
promote at n=5. Any hard check fails → **reject regardless of precision**. Precision null →
record and move on, **do not re-word** (the S-1 precedent).

**Hard checks, independent of the aggregate** — these test *both* halves of the rule and are in
the `s3decide` notebook cell:
- *Exception (2), traffic leaving the design:* `uart:uart_rxd_i`, `uart:uart_txd_o`,
  `spi:spi_dat_i`, `twi:twi_sda_i` must survive.
- *The redirect, decisions inside the interconnect module:* `bus:sel`, `bus:stb`,
  `bus:port_sel`, `bus:state` must survive.
- *The boundary, the record the module ACTS ON:* **17 reference assets are fields of the
  control record** — `wdt:ctrl.enable/lock/timeout`, `uart:ctrl.enable/baud/prsc`,
  `spi:ctrl.enable/cdiv/prsc`, `twi:ctrl.enable/cdiv/prsc`,
  `cpu_cp_muldiv:ctrl.cnt/state/rs1_is_signed/rs2_is_signed`, `cache:ctrl.buf_sync`. These
  are the exact population the control-record contrast shows would be destroyed if the model
  generalises the rule to every record it sees. **This is the single most informative hard
  check in the arm** — added 2026-08-11 after it was noticed the first check set tested the
  rule's two halves but not its boundary. Eight of the seventeen are checked directly.

**Zero reference assets are declared with a fabric record type.** That is the whole
justification for the recall Expect of 0.000: the population S-3 targets and the population
the reference draws from do not intersect at all.

**Mechanism check, registered because X-3 failed it.** X-3 intended a criterion and delivered a
volume cut (elements/concept 4.47 → 4.15, precision null). **If `v2s3` moves elements/concept
more than it moves precision, it is turning the fan-out dial and the claimed mechanism is
false**, whatever the aggregate says. Also reported: fabric-typed FP/repeat, which must fall
from 76.0 toward zero. A precision gain without that fall came from somewhere else.

**Registered cost:** none identified. If the model over-applies exception (1) it will start
naming converted traffic in ordinary peripherals; that shows up as *rising* port FPs, not
falling recall.

**Got: REJECTED — precision moved the WRONG WAY, distinguishably, and one hard check failed.
Run sha `6bd762261967`, n=3.** But the arm split cleanly into a half that worked and a half
that broke it, and that split is the finding.

| | emit | TP | FP | FN | P | recall | F1 |
|---|---|---|---|---|---|---|---|
| `v2` | 412.7 | 102.7 | 310.0 | 8.3 | 0.251 | 0.925 | 0.394 |
| `v2s3` | 420.0 | 105.0 | 315.7 | 6.0 | **0.249** | **0.943** | 0.394 |

Paired: precision **−0.016** [−0.036, −0.001] **\*** (7 better / 7 worse — the mean is carried
by magnitude, not by count) · recall **+0.017** [+0.000, +0.039] null · F1 −0.015 [−0.033,
+0.002] null.

**Expect vs Got — three of four predictions wrong:**

| | Expect | Got |
|---|---|---|
| precision | +0.035 to +0.056 | **−0.016** |
| recall | 0.000 to −0.010 | **+0.017** |
| emissions | −60 to −80/rep | **+7.7** |
| elements/concept | unchanged ~4.47 | **4.41** ✓ |

**`v2s3` has the highest recall in the entire v2 study (0.943).** It is a recall arm that was
registered as a precision arm.

**Note the n=2 artefact.** r2 first produced malformed JSON for `neorv32_cpu_cp_cfu` (object
ended `,"Assets"]}` with the array never opened) and `collect()` correctly excluded the repeat.
At n=2 F1 read −0.019 **\***; at the registered n=3 it is null. **The arm was adjudicated only
after r2 was regenerated** — the decision rule specified n=3 and reading it at n=2 would have
overstated the damage.

### What worked — the prohibition, and the boundary

**The `ctrl_t` boundary held perfectly.** Across all 17 control-record reference assets: `v2`
had 1 FN event in 51 chances, **`v2s3` had 0 in 51.** The clause exempting the record a module
*acts on* did exactly its job — the −0.150 recall collapse the contrast predicted never
appeared. Group A (traffic leaving the design) also passed 3/3 on every element.

**The mechanism check passed.** elements/concept 4.47 → **4.41**, concepts/module 6.16 → 6.36,
max elements on one concept **53 → 19**. S-3 is confirmed to be a different *kind* of edit from
R-8 and X-3: it did not touch the fan-out dial. It broke up the giant concepts without reducing
total binding.

**The prohibition fired correctly, and only where its premise holds.** Fabric-typed FP
**76.0 → 55.7**/repeat. Of that −20.3, **−19.0 is `neorv32_bus` alone** (45.3 → 26.3), where
emissions fell 70.0 → 50.3 and **FN did not move at all** (0.67 → 0.67). In the target module
the arm removed 19.7 emissions/repeat at zero recall cost.

**One hard check failed:** `bus:stb` 3/3 → 2/3.

### Why precision fell anyway — the REDIRECT became a licence

The rule has two halves. The prohibition worked. The redirect — *"Name those decision elements
instead; they are usually ordinary internal signals, not the record"* — fired **everywhere**,
including where nothing was being forwarded.

| class | `v2` emissions | `v2s3` | FP delta |
|---|---|---|---|
| port | 154.0 | **133.0** | −22 |
| signal | 98.7 | **110.3** | **+11** |
| signal-field | 157.7 | **174.3** | **+16** |

It removed 22 fabric port FPs and added 27 signal / signal-field FPs — **the two worst-precision
classes** (0.307 and 0.180 against port's 0.286). Per module: `bus` **−19.7**, and then
`trng` **+10.7**, `debug_dtm` +6.0, `spi` +4.3, `cpu_pmp` +2.3; net **+7.7**.

**`neorv32_trng` is the decisive evidence.** Its fabric-typed FP did not move (2.0 → 2.3) —
a TRNG forwards no bus traffic, so the prohibition had nothing to bite on — yet its emissions
rose **+76%**, the largest jump of any module. The model applied *"name the decision elements
instead"* **without the precondition that any traffic was being forwarded.**

**This is the S-1 failure in a new location.** S-1 died because its *carve-out* became a licence
in the module that mattered. S-3's carve-out is verified sound; **its redirect became the
licence instead — and it fired hardest in the same module that broke S-1.**

The extra emissions were partly productive, which is why recall rose: FN 8.3 → 6.0, with
`trng` −1.00, `cpu` −0.67, `debug_dtm` −0.33. Untargeted volume buys recall and costs precision.

### The rule that this establishes for every future arm

**Two for two: every restrictive criterion added to this prompt has INCREASED emissions.**
S-1 +12.3/repeat, S-3 +7.7/repeat, both landing outside the class they targeted. The only edits
that ever reduced volume were a **deletion** (R-8, −45.0) and an **ICL change** (X-3, −21.4).

**Prohibit without redirecting.** Do not tell this model what to name instead — it treats the
substitute as a new quota. If a replacement population needs naming, that belongs in a stage
where the model cannot inflate it.

---

### SEC · Line-6 expansion — demote influencers to a per-primary secondary array
**Version `v2sec`. Core sha `e262b83a1cb7` (9 783 chars, +2 371) · composed core+ICL
`1b0826ca22cf` (72 633). Baseline `v2`. ICL is the BASELINE block. n=3. Built 2026-08-11,
not yet run.**

**The first arm to touch Algorithm 1 line 6.** Every previous arm tried to make line 5 emit
*less*. This one gives the model somewhere else to *put* an element. Different mechanism,
and the first one that is not a variation on the fan-out dial.

**One change from `v2`:** STEP 3 (SAIF's primary/secondary definition, its two worked
examples, and a demotion test) plus one output-contract field. Round-trip verified — undoing
both edits reproduces `ASSET_V2_BASE` byte-for-byte at `89efcccf1b55` / `ea0608b316dc`.

**The discriminator had to be corrected before the headroom meant anything.** Asking *"does
this element appear as a secondary?"* does not discriminate: it fires on **49.8% of our false
positives and 56.2% of our true positives**, because **77 of 137** LAsset primary elements are
*also* secondary somewhere. Secondary is a **role**, not a class. The cut that works is
*"only ever an influencer, never independently a primary"*:

| category | our FP/rep | %FP | our TP/rep | %TP | FP:TP |
|---|---|---|---|---|---|
| **secondary-ONLY** | **133.3** | 43.0% | **4.0** | 3.9% | **33 : 1** |
| both roles | 21.0 | 6.8% | 53.7 | 52.3% | 0.39 |
| primary-only | 9.0 | 2.9% | 42.3 | 41.2% | 0.21 |
| in neither list | 146.7 | 47.3% | 2.7 | 2.6% | 55 : 1 |

**Oracle demotion of the secondary-ONLY population: emit 412.7 → 275.3, precision
0.249 → 0.358 (+0.110), recall 0.925 → 0.889 (−0.036).** The largest single lever measured in
the study, double S-3's.

**Three caveats registered with that number.** It uses **LAsset's own** secondary lists as the
discriminator, so it assumes the model's notion matches theirs — an upper bound, not a
forecast. Recall −0.036 sits **inside the indeterminate band**, so this arm is on the guard by
design. And it addresses 43% of false positives; the 47% that LAsset never named in any role
are untouched by it.

**Scoring is unchanged and this was verified, not assumed.** The scorer reads the `Assets`
array only. Secondary arrays are recorded and never scored — there is no secondary ground
truth. Verified empirically by injecting `secondary` arrays into all 479 asset objects of a
real `v2` repeat and re-scoring: emit/TP/FP/FN and every per-module FP list identical.

**What is taken from SAIF, and what is deliberately not.** Taken: the primary/secondary
definition, and both worked examples (a shared bus and its decoder as secondary to a master's
data; a boot-versus-normal execution state as secondary to a crypto key). Both are IP-agnostic
and name nothing from NEORV32 — **the inserted step contains zero identifiers**, asserted at
import. **Not taken: SAIF's three algorithms.** Algorithm 1 needs fan-out/fan-in traversal with
sequential-depth extraction; Algorithm 2 needs stuck-at fault insertion, stimulus application
and an Observation-Hardness threshold — fault simulation; Step 3 needs formal information-flow
verification and side-channel metrics. **None is executable by a model reading RTL text**, and
prose gesturing at them would be an instruction performed superficially and over-applied —
which is precisely how S-3's redirect failed. `_apply_sec` asserts none of that vocabulary
entered the prompt.

**No confidence score, and no threshold.** Considered and rejected: it would make this arm test
two propositions; the threshold is a free parameter with no principled value and tuning it
afterwards would be fitting to the test set; and E-4 already exists to test whether the model
can rank its own emissions, against a pre-computed blind line. That question belongs there.

**REGISTERED CONFLICT — SAIF's definition contradicts this ground truth on FSM state.** SAIF
names *"states of an FSM"* as an intangible **secondary** asset. Our reference lists **7 such
elements as PRIMARY**: `bus:state` ×2, `bus:sel`, `bus:stb`, `cpu_cp_muldiv:ctrl.state`,
`hwspinlock:sel`, `wdt:cnt`. These are the elements a literal reading of STEP 3 demotes first.
Recorded before the run as a known cost, and covered by hard-check group C. **This disagreement
between the literature definition and the annotation is a finding in its own right**, not a
defect to paper over.

**Expect:** precision **+0.05 to +0.11** · recall **−0.010 to −0.036** · primary emissions
**−80 to −133**/repeat · elements/concept **unchanged near 4.47**.

**Decision rule — the mechanism check decides first, whatever precision did:**
- **Primary list did not shrink, or fewer than 50% of departures reappear in a secondary
  array → REJECT.** The model added a channel instead of reassigning. This is the predicted
  failure and it is the point of the arm.
- Precision up **and** recall drop ≤ 0.03 **and** all hard checks pass → promote at n=5.
- Recall drop 0.03–0.06 → indeterminate, re-run at n=5. **Expected** — the oracle cost is
  −0.036 and the arm sits on the guard by design.
- Any hard check fails → reject regardless of precision.

**Hard checks** (in the `secdecide` cell), all three testing what a loose reading of
"infrastructure" would demote:
- *Control record, all 17:* `wdt/uart/spi/twi:ctrl.*`, `cpu_cp_muldiv:ctrl.*`,
  `cache:ctrl.buf_sync`.
- *Crosses the design boundary:* `uart:uart_rxd_i`, `uart:uart_txd_o`, `spi:spi_dat_i`,
  `twi:twi_sda_i`.
- *FSM / arbitration state:* the 7 elements of the registered conflict above.

**Why this is the four-for-four test.** S-1's carve-out became a licence, S-3's redirect became
a licence, the parsed block became a menu, and both restrictive criteria *raised* emissions.
Every time this model is handed a population to name, it names from it. **This arm hands it a
population deliberately** — and the whole question is whether a *reassignment* framing
("it leaves `Assets`") can do what a prohibition framing could not.

**Registered cost:** token cost rises; secondary arrays are generated and never scored. Accepted
— the alternative is not testing line 6 at all.

**Got: REJECTED on the guard — recall 0.925 → 0.628, a drop of 0.297 against a 0.06 threshold,
and all three hard-check groups failed. But the registered mechanism check PASSED
emphatically, and that is the finding.** Run sha `1b0826ca22cf`, n=3, 15 modules.

| | emit | TP | FP | FN | P | recall | F1 |
|---|---|---|---|---|---|---|---|
| `v2` | 412.7 | 102.7 | 310.0 | 8.3 | 0.251 | 0.925 | 0.394 |
| `v2sec` | 246.0 | 70.0 | 176.7 | 41.0 | **0.287** | **0.628** | 0.392 |

| paired vs `v2` | d | 95% CI | |
|---|---|---|---|
| precision | **+0.069** | [+0.006, +0.131] | **\*** 9 better / 6 worse |
| recall | **−0.300** | [−0.379, −0.220] | **\*** **0 better / 14 worse** |
| F1 | −0.012 | [−0.073, +0.046] | null |

**+0.069 is the largest precision gain in the study** — nearly triple X-3R-8's +0.025. F1 is flat,
so every point of it was bought with recall.

**Expect vs Got:**

| | Expect | Got |
|---|---|---|
| precision | +0.05 to +0.11 | **+0.069** ✓ |
| recall | −0.010 to −0.036 | **−0.300** — wrong by an order of magnitude |
| primary emissions | −80 to −133 | **−166.7** |
| elements/concept | unchanged ~4.47 | **2.69** |

### The mechanism check passed — the four-for-four pattern is broken

**123 elements left the primary list and 117 (95%) reappear as secondary.** Primary emissions
393.0 → 242.7 distinct. **This is the first arm in the study where handing the model a
population did not cause addition.** S-1's carve-out became a licence, S-3's redirect became a
licence, the parsed block became a menu — all three ADDED. A *reassignment* framing moves
elements instead. That property is worth carrying forward independently of this arm's failure.

Concepts/module was **unchanged at 6.16** while elements/concept fell 4.47 → **2.69**: the model
did not conceive differently, it unbound elements from concepts and re-attached them elsewhere.

### Why recall collapsed — the demotion test has no floor

The test as written: *"does this element matter ONLY because it carries, gates, steers, times
or exposes something else? If the security story needs a SECOND element named to make sense, it
is that element's secondary asset."*

**In RTL essentially every element satisfies that.** A design is a connected graph; almost no
signal has a security story naming only itself. `wdt:cnt` serves the timeout,
`cpu_cp_muldiv:ctrl.rs1_is_signed` serves the multiply result, `bus:stb` qualifies a
transaction — all three were demoted. **The criterion selected on nothing.**

Demoted share, computed per repeat: **69.4% / 55.6% / 62.9%** of all emitted entries.

Selectivity, against the 33:1 oracle:

| class | TP removed | FP removed | ratio |
|---|---|---|---|
| port | 11.7 | 25.0 | **2.1 : 1** |
| signal | 12.3 | 41.3 | 3.4 : 1 |
| signal-field | 9.0 | 66.6 | 7.4 : 1 |
| **overall** | **32.7** | **133.3** | **4 : 1** (oracle: 33 : 1) |

Directionally correct and **about eight times less selective than the oracle**. It captured the
target population — FPs in the secondary-ONLY oracle set fell 133.3 → 61.0/repeat — but took
33 true positives with them where the oracle costs 4.

### Hard checks — all three groups failed

| group | missing in `v2` | missing in `v2sec` |
|---|---|---|
| control record (17) | 1/51 | **9/51** |
| crosses design boundary (4) | 0/12 | **3/12** |
| FSM / arbitration state (7) | 0/21 | **10/21** |

**The registered conflict materialised exactly as predicted.** SAIF's *"states of an FSM"*
clause cost 5 of the 7 FSM elements — `bus:state`, `bus:sel`, `bus:stb`, `hwspinlock:sel`,
`wdt:cnt`, all demoted rather than dropped. Registering that casualty before the run is what
makes this an evidenced conflict between the literature definition and this annotation rather
than an unexplained loss. `twi:twi_sda_i` vanished entirely rather than being demoted.

**The output contract was not fully obeyed:** 33 / 17 / 24 elements per repeat were **both** a
primary entry and a secondary of some other primary, despite the prompt stating that an element
placed in a secondary array must not remain a primary entry.

### What this establishes

**Five for five, with a new qualification.** Every population handed to this model gets used —
but the *shape* of the instruction decides how. A prohibition or a criterion makes it emit MORE
(S-1 +12.3, S-3 +7.7, parsed block +70). A **destination** makes it MOVE (95% compliance).
Movement is controllable in a way that prohibition is not.

**The failure is calibration, not mechanism.** The demotion machinery works; the criterion
deciding what to demote must be structural rather than a judgement about whether an element
"serves" another, because in RTL that is almost always true. The obvious successor pairs SEC's
destination with S-3's type-scoped fabric population — 76 FP/repeat at a measured zero TP cost —
instead of a free-text test. Not registered here; recorded as the indicated direction.

---

### E-6 · Record enumeration guard — CLOSED, no mechanism exists
**Version `v2e6`. Baseline `v2`. Largest measured lever in the study.**

Registered 2026-08-08 from §5b, which was not visible before the baseline ran. **It displaces
E-1 as the first arm** — same safety profile, roughly five times the headroom.

**The proposition.** When a record's fields are considered for one conceptual asset, the assets
are the fields that carry the security property — the configuration the module acts on, the
state it protects — **not every field the record declares.** Status, interrupt-condition and
clear/strobe fields of a control record are consequences of the asset, not the asset.

**Headroom, measured on v2's own output.** Record groups of ≥5 fields hold 369 emissions: 56
TP, **313 FP**, precision 0.15 inside them. Removing the FP while keeping every TP gives emit
412.7 → 308.4, precision **0.251 → 0.333**. That is the upper bound and it will not be reached;
expect a fraction.

**Expect:** precision **+0.03 to +0.06** · recall **−0.01 to −0.03** · emissions −15 to −25%.
**Decision rule:** precision up and guard passes → promote. **Recall drop > 0.03 → reject
outright**, because the 56 TP inside those groups are real assets and the arm must separate
them, not delete the category. Drop 0.03–0.06 → re-run at n=5.
**Registered risk, and it is the whole difficulty:** the ground truth *does* contain record
fields — 31 of the 111 references are signal-field, and `uart`'s own `ctrl.enable`, `ctrl.prsc`
and `ctrl.baud` are three of them. A rule that suppresses record fields as a class fails the
guard by construction. **The arm must be a selection criterion, never a cap or a ban.**

**Got:** —

---

### E-1 · Replicated interconnect is not an asset of the module it passes through
**SUPERSEDED 2026-08-11 by S-3 below, which is this proposition rewritten as a criterion with
structural exceptions and built as `v2s3`. Kept for the headroom-correction record.**
**Version `v2e1`. Baseline `v2`. Status: superseded, never built, never run.**

The worst FP names are the SoC bus interface repeated in every peripheral — `bus_req_i`,
`bus_rsp_o`, `core_req_i` and kin.

**CORRECTED 2026-08-09.** The 25.3 FP/repeat below came from a hand-written six-name regex on
the *old* baseline — a blocklist, and the wrong instrument. Defined structurally (ports whose
type is a bus transaction record, present in 11 of 18 modules) and measured on v2:
**73.7 FP per repeat at exactly ZERO true positives → precision 0.251 → 0.303.** Nearly 3×.
Also regime-scoped: the fabric a module is *attached to* is not its asset, but an interface a
module *exists to implement* is — `neorv32_xbus` has 8 bus signals as GT assets, `slink` 11 of
13. Both are held out. The superseded text follows.

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

> **UPDATED after the v2 run — this arm's headroom shrank by itself.** On `v2`: claims
> **58.0 → 41.7** per repeat (−28%), TP 8.3 → 8.7, FP 49.7 → **33.0**, precision
> **0.144 → 0.208**. The Confidentiality rubric was **not touched** by D, L or N, so the
> improvement is a side effect — most plausibly D, which made the binding contract coherent.
> Perfect execution now gives emit 412.7 → 379.7, precision → **0.270**, i.e. a ceiling of
> **+0.019** rather than the +0.034 registered below. **Still worth running, no longer near
> the top of the queue.** The paragraphs below are the original registration and stand as
> written; only the size of the prize has moved.

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

### RP · Restore the parsed closed set, now carrying functional roles
**Version `v2rp`, core-sha `82f478cded9f` (core 8 066 chars = base 7 412 + 654).** Baseline
**`v2`**. Registered 2026-08-16, before running.

**The first arm that changes the INPUT regime rather than the prompt text.** It undoes
correction D and hands line 5 the parsed ports/signals again — but annotated by a new line-4
parser (`prompts_parse_v2`) that assigns each element a functional role from the LAsset RTL
role taxonomy, a relationship, and a line of RTL evidence, alongside the `function` string
v1 had.

**Why, and why the reading is not "did precision go up".** Recall in this pipeline is
currently bought with prompt text that raises emission — A-08's per-concept closure sweep
took v1 emissions 331.2 → 428.0 while precision fell 0.285 → 0.229. If the parsed list
supplies that coverage instead, the text becomes removable and the precision it costs is
recoverable. So the arm is a **substitution test**, and its three outcomes are all
informative:

| outcome | reading |
|---|---|
| recall and emission ~flat | the roles carry the coverage the prompt text was buying — start removing that text on top of this baseline, one block at a time, R-8 first |
| recall UP, emission UP | the roles are a second generator, not a substitute — a dial was added, nothing became removable |
| recall DOWN | the parsed list displaces RTL reading rather than supporting it; the closed set is not where recall comes from |

**Prior, registered before running.** v1's P-2 removed the parsed blocks and was **null on
every paired delta** (P 0.210 → 0.243, recall 0.897 → 0.886, ABLATION_LOG.md §P-2). That was
a name+`function` list. This arm's claim is that the **annotation**, not the name list, is
what would have mattered. A null here is therefore a real result rather than a failed arm: it
says the closed set is not where line 5's recall comes from, in either direction.

**Four edits to the core, one insertion.** The first three are the exact reversal of
correction D, restoring `prompts._P2_INPUTS_OLD` / `_P2_EDITS` wording verbatim except that
the field list gains `roles, relationship, evidence`. The fourth is new and load-bearing: a
RULES bullet declaring the annotations **evidence, never verdicts, in both directions** — a
positive-sounding role does not make an element an asset and an `ORDINARY_`/`GENERIC_` role
does not stop one being an asset; where an annotation and the RTL disagree, the RTL wins.
Without it the natural reading of `SECRET_DATA_STORAGE` is "emit this", which would move
STEP 1's C/I/A decision into the parser and make the arm measure label transfer.

**Two asymmetries, both accepted deliberately, both recorded so they are not later mistaken
for findings:**

1. **The ICL examples do not demonstrate the blocks.** v2's ICL is the P-2 block with both
   `=== PARSED … (JSON) ===` spans removed, so the worked examples reason from RTL alone
   while the live message carries a parsed list. `_BLOCK_MARKERS` does **not** catch this —
   it only fires when a block is dropped from the message while the prompt still declares it,
   and this is the reverse. This is the arm's chief risk and the first suspect if recall
   falls. Holding the ICL fixed is what keeps this one proposition; pairing it with a
   parsed-carrying ICL would be two changes, which is what made X-3R-8 uninterpretable.
2. **58.1% of the restored list is a dotted PORT field, and A-03 forbids emitting any of
   them.** Recomputed over the 15 scored modules: 914 of 1 572 elements, holding **0 of the
   30** dotted ground-truth assets — all 30 are fields of internal SIGNAL records. Not new:
   v1's `v01c6p1` ran exactly this combination at 0 ungrounded names across 90
   module-repeats. Recorded because it is the first candidate explanation for a precision
   fall here.

**Baseline is byte-identical.** `_apply_rp` round-trips — undoing all four edits reproduces
`ASSET_V2_BASE`, which still hashes to `89efcccf1b55` / `ea0608b316dc`. The change to
`prompts_v2.py` is an append plus one `audit()` line; no earlier version's sha moves.

**The closed set is copied, not re-derived.** `parse_roles.annotate_module` reads the element
list verbatim from `parsed_tuning18/` and writes `parsed_roles_tuning18/`;
`verify_against_cache` asserts the `(entity, name)` sequences and the `type`/`dir` fields are
identical and raises on any drift. So the scorer, `validate_primary` and every recorded run
are untouched, and an emission delta cannot be a closed-set delta. `RETRY_ON_VALIDATION`
flips back to True on its own, correctly: the corrective retry selects on the parsed closed
set, which this version puts *in* the prompt rather than withholding.

**Gate before spending the run.** `parse_roles.role_report()` prints the share of the closed
set carrying a positive lead role. The reference's own asset rate over the 15 scored modules
is **7.2%** (113/1 572, recomputed from `manual_gt_neorv32.json`). The vocabulary is 152
positive labels against 16 negative ones, and §4's standing finding is that a free-standing
checklist becomes a generator. Here the checklist is shown to the **parser**, not to
LLMasset, so it cannot inflate emission directly — but if it marks most of the closed set
positive, the asset stage is handed a design in which everything looks security-relevant and
the arm's emission delta is about the parser. **A positive rate far above the low tens of
percent is a defect in the parse, not a finding about the design; fix it before generating.**

**Expect** — emission within ±10% of v2 and recall within ±0.03. Stated as a null because
P-2 was null in the other direction and nothing measured yet says the annotation changes
that; the arm is worth running because all three outcomes redirect the queue differently.
**Decision rule:** flat recall and emission → the emission-raising blocks become removable
and E-2 (revert A-08) runs next **on `v2rp`** rather than on `v2`. Emission up → the arm
added a dial, record and close. Recall down → check the ICL asymmetry before concluding
anything about the closed set.

**Diagnostic to run whichever way it lands**, because it separates "the model used the
annotations" from "the model ignored them": compare the positive-lead-role rate of the
**emitted** elements against the closed-set base rate. No lift over base means the
annotations were decorative and the result is about the name list after all. The script is
the `RP DIAGNOSTIC` cell in `finetuning_assetgen_v2.ipynb`, directly after the scoring cell.

**Got:** —

---

### P3 · The v3 parse — occurrence-driven, open-vocabulary annotation
**Version `v2p3`, core-sha `f3a56b13cba7` (8 372 chars) · composed `ed45ec668d37`.** Baseline **`v2`**;
paired against **`v2rp`** for the vocabulary question. Registered 2026-08-17, before running.

**Same input regime as RP, different annotation.** RP hands line 5 a closed set whose `roles`
come from a 152-label taxonomy. P3 hands it `function`, `functionality`, `role`,
`relationship` and `evidence` produced by `prompts_parse_v3`, where `role` is open prose and
the annotator is given **no vocabulary at all**.

**Why the vocabulary was dropped.** Measured, not argued: eight of RP's role names restate the
v2 asset core's own STEP 1 rubric almost verbatim — the rubric names *keys, seeds,
entropy/random state* as genuine secrets, and the taxonomy answers with `A1_KEY_MATERIAL` and
`A2_ENTROPY_SOURCE`; it asks about *privileged modes, overrides, bypass* and the taxonomy
answers `F3_OVERRIDE_OR_BYPASS`. Under RP the parser fills in STEP 1's answer sheet and the
asset stage grades its own input. Re-basing the labels onto their structural definitions fixed
the wording without fixing the shape, so the enum went entirely.

**What replaces it.** Three structural guards, none of them hortatory:
1. Every field must derive from an **occurrence profile** — the list of syntactic sites where
   the identifier appears. An annotation that must cite a site cannot be produced from a name.
2. `evidence` must name a construct and a counterpart, or the record fails validation.
3. The banned vocabulary is enforced on the **output** by `parse_v3.check_annotation` — 31
   verdict and hedging terms, unknown edge types, unresolvable targets, over-length fields.

**Comment-stripped input**, unlike every earlier annotate stage. A comment is where a designer
states a conclusion the RTL does not show; an annotator told to read one reports it as observed
behaviour. `rtl_parse.strip_comments`'s docstring is updated to record the exception.

**The parse is built from scratch.** `rtl_parse.parse_rtl_file` re-derives the closed set with
the same regex and `verify_against_cache` asserts it matches `parsed_tuning18/` element for
element, so the scorer and `validate_primary` are unaffected and an emission delta cannot be a
closed-set delta.

**A SEPARATE ARM, NOT AN EDIT TO RP.** `assets_tuning18_v2rp_r0..r2` exist and record
ASSET_V2_RP's composed sha `c18f0d40c62c`. Rewriting that string would leave three paid runs
attributed to code that no longer exists. Verified after this arm was added: RP's sha is
unchanged.

**The gate.** No positive-role rate exists any more — there is no label to count. `parse_v3.report()`
gives the share of elements whose annotation used verdict or hedging vocabulary; target ~0, and a
non-trivial rate means the parser has begun doing the asset stage's job. Also reported:
isolation rate, and **GATES:SOURCES** — GATES is the edge a value-flow reading misses, and if it
is scarce the most consequential instruction in the prompt is not landing.

**One asymmetry inherited from RP and still registered:** the ICL block has both PARSED spans
removed, so the worked examples reason from RTL alone while the live message carries a parsed
list. Held fixed deliberately to keep this one proposition.

**REGISTERED DEVIATION FROM ALGORITHM 1 LINE 4 — the two parsers are merged into one call.**
The paper is explicit: *two* LLM-based parsers, one for I/O ports and one for internal
signals/registers. `parse_v3` runs one call per entity covering both lists
(`PARSE_ELEMENTS_V3_SYSTEM`, sha `2faa550c3b16`). Measured
like-for-like over the 18 modules, both annotating all 1 689 elements:

| configuration | calls | input tokens |
|---|---|---|
| two parsers, batch 64 (faithful) | 61 | 284 337 |
| **merged, batch 128 (in use)** | **30** | **165 980** |

The entity's source is resent on every call, so merging halves the number of calls that
carry it. Roughly half of the remaining input is the system prompt repeated across calls,
byte-identical and therefore cacheable, as is the entity source across an entity's batches.

**Not purely a cost trade.** An element's occurrence profile routinely spans both lists — a
port captured into a register, a register driving a port — so one call sees both ends of
every edge it is asked to record, and the reciprocal edges can be made consistent inside one
answer instead of across two. The faithful configuration is preserved and reachable:
`parse_v3.annotate_all(..., merged=False)` restores the two parsers with no other change, so
this is an ablatable switch rather than a fork.

**Also registered: the annotator sees ONE ENTITY's source, not the file's.** 54 names in
`neorv32_bus` are declared in more than one of its six entities (59 across the 18 modules),
`clk_i` in all six. Sending the whole file meant an annotation for one entity's element was
derived from a profile merging two same-named elements. Verified after the change: every
entity scope contains exactly one entity block and one architecture, and no element is
missing from its own scope.

**A correction to the RP entry above, found while diagnosing why RP under-performed.** The
RP parse was not the cause. Measured over `parsed_roles_tuning18/`: only 10.6% of elements
took a positive lead role against a 7.2% ground-truth asset rate, and 89.3% took an
`ORDINARY_*`/`GENERIC_*` label — the gate would have passed it. The likelier cause is RP's
own status rule, which told the asset stage that an `ORDINARY_` label *"does not stop one
being an asset"*, discarding the suppressive signal present on 89.3% of the input. P3's
equivalent rule generalises that instruction to all neutral phrasing, so under P3 the
suppression must come entirely from the accuracy of the descriptions and not from any label.
Whether that is enough is what this arm measures.

**Expect** — emission within ±10% of v2 and recall within ±0.03, same null prior as RP.
**Decision rule:** flat recall and emission → the annotation carries the coverage the
emission-raising prompt text was buying, and E-2 runs next on `v2p3`. Emission up → a dial was
added, not a substitute. Recall down → check the ICL asymmetry first.
**Against RP:** if P3 and RP land together, the vocabulary never mattered and the closed set is
what the arm is measuring. If they separate, the direction says which representation transfers.

**Got:** —

---

### C1 · Teach the asset stage how to READ the annotations
**Version `v2p3c1`, core-sha `6724f501d107` (11 885 chars) · composed `ef4151232e86`.**
Baseline **`v2p3`**. Registered 2026-08-17, before running.

**ONE ADDITION, AND NOTHING ELSE MOVES.** P3 states what the four annotation fields are and
what they are not; it never says how to use them, so the model improvises a reading of a
structured input it has not seen before. C1 inserts a `READING THE ANNOTATIONS` block ahead
of STEP 1: read `evidence` first because it names the construct the other three rest on;
what `functionality` and `role` report; how to read the edge types in groups; which of the
four fields bears on each of the C/I/A/U questions; and what may not be inferred.

**No asset criteria are added.** The baseline's definition of a primary asset — an element
that stores, carries, generates or gates a conceptual asset — is untouched. A delta against
`v2p3` is therefore attributable to the reading procedure alone.

**Why this is not leakage.** The obvious way to write the block is to state which annotation
patterns mark assets. Two do, measured against this project's own ground truth: over the 271
dotted signal fields, 80% of the true assets appear in a condition against 28% of the
non-assets, and 57% are written from an input port against 24%. **Neither is in the prompt,
and neither may be** — that is the answer key. What the block carries instead is the
*mechanism* each field reports and which question it bears on. Naming the confidential
concept, and deciding whether this element is where it lives, remain the model's work.

**The lever against over-emission is "A COUPLING IS NOT A REASON".** Every element in a
working design is coupled to something; the v3 parse averages 1.8 edges per element across
3 017 of them. Handed that, a model can read connectedness as significance and name most of
the file. The block states that an edge supplies the mechanism and never the reason, and
that the Justification must still argue from the module's purpose — paired with the
converse, already in P3, that neutral phrasing is not evidence of unimportance.

**Input fixes that land with this arm** (both are parser-side, and both were prompt defects
found on the first real v3 parse):

| defect | cause | fix |
|---|---|---|
| 233 unknown edge types | the edge list showed the counterpart as `SOURCES(Y)`; the model copied the notation | edge names written bare; 200 recovered by normalisation, 33 site-name uses dropped |
| 589 unresolved targets | indexed array references such as an array name followed by `(0)` | targets constrained to declared names; 496 recovered by de-indexing, 93 genuinely outside |
| GATES at 54% | 338 elements appear in a condition, 184 GATES edges emitted | new STEP 2b governing-site sweep, linked to a required edge |

`parse_v3.load_all` normalises on load and never rewrites the files, so provenance is intact
and the repair is visible in its printed counts. **The parse feeding this arm is the one
already on disk**, unchanged; the prompt fixes apply to the next parse and the GATES
improvement is not in this arm's input.

**Expect** — emission below `v2p3`, recall within ±0.03. C1 is the first arm in this study
whose stated mechanism is suppression rather than coverage.
**Decision rule:** emission down with recall flat → the reading procedure is what the parsed
input was missing, and the annotation route is worth continuing. Emission flat → the model
was already reading the fields as well as the instructions can make it, and the remaining
over-emission is not an input-comprehension problem. Emission up → connectedness is being
read as significance despite the rule, and the parsed list is a generator whatever is said
about it.

**Got: RECORDED, n=3 on the 15 scored modules, parse gen2 (`450d8de774ca`).**

| arm | input | emit | P | recall | port-field FP |
|---|---|---|---|---|---|
| `v2` | RTL only | 412.7 | **0.250** | **0.930** | **0.0** |
| `v2rp` | parsed + 152-label taxonomy | 449.0 | 0.210 | 0.855 | 11.0 |
| `v2p3c1` | parsed v3 + reading procedure | **375.7** | 0.249 | 0.848 | **36.7** |

**Against `v2rp` the arm is a clear win** — emission −73.3, precision +0.039, recall +0.007. The
v3 parse plus the reading procedure beats the closed-taxonomy parse on every axis.

**Against `v2` it is not.** Emission −37.0, precision **+0.000** — identical to three decimal
places — and recall −0.082 with non-overlapping per-repeat ranges (v2 0.909–0.945, C1
0.836–0.873). The parsed input still buys no precision and still costs recall.

**THE RECALL LOSS IS INSTABILITY, NOT BLINDNESS. This is the arm's real finding.**

| arm | union recall | core recall | gap |
|---|---|---|---|
| `v2` | 0.955 | **0.882** | 0.073 |
| `v2rp` | 0.945 | 0.755 | 0.190 |
| `v2p3c1` | 0.945 | **0.727** | **0.218** |

Union = found in ≥1 repeat; core = found in all three. **All three arms reach the same
elements** — union recall 0.945–0.955 — and exactly ONE reference element is found by `v2`
and never by `v2p3c1` (`debug_dtm:jtag_tms_i`). The parsed input does not make the model
blind. It makes its selection unrepeatable: `v2` names 97 of 105 reachable elements in every
repeat, `v2p3c1` only 80 of 104. Handed 1 689 annotated elements the model has more
plausible things to name and its choice shifts run to run.

**Port-field FPs are a cost the parsed arms alone pay.** Zero under all seven RTL-only arms;
11.0 under `v2rp`; **36.7 under `v2p3c1`**. A-03's "record-typed PORTS are named WHOLE" holds
perfectly until the parsed block enumerates 929 dotted field names, at which point the model
names them. Pure loss: **no reference contains a single port-field asset** — 0 in the manual
list, 0 in LAsset initial, 0 in LAsset refined.

**A correction to the granularity story this log has carried.** A-03 was read as meaning a
record port is named as an aggregate. Measured: of 49 bare-port assets in the manual
reference exactly **one** is a record port (`cpu_pmp:ctrl_i`); LAsset initial and refined
have **zero**. No reference ever names a port field without its parent. So record-typed
interconnect ports are not assets at ANY granularity — which is S-3's thesis arriving from a
second direction, and it means the port-field fix is to stop SENDING the fields, not to
re-word A-03.

### The parser stage — three generations, measured

`prompts_parse_v3` was revised twice while this arm's input was being built. All three
parses are on disk and fingerprinted, so the attribution is recoverable.

| | edges | elements w/ governing edge | malformed types | unresolved targets |
|---|---|---|---|---|
| gen1 `5274280e` | 3 017 | 218 | 233 → 0 by repair | 589 → 0 by repair |
| gen2 `450d8de7` | 2 392 | 215 | **0 natively** | **8 natively** |
| gen3 `540765753f` | 2 464 | **201** | 0 | 8 |

**What worked.** Writing the edge names BARE fixed 233 malformed types at source — the list
had shown them as `SOURCES(Y)` and the model copied the notation verbatim. Constraining
targets to declared names fixed 589 → 8. Both were prompt defects, both closed completely.

**What did not.** A STEP 2b sweep instructing a separate pass over every governing site moved
governing elements 218 → 215. Two materially different prompts, the same count. **Read as a
model capability limit, not a prompt limit** — do not spend a third revision on it.

**What backfired, and it is the same failure this log has now recorded three times.** gen3
added a prose/edge consistency rule listing eight governing verbs, and a one-hop prose rule
naming a hop pattern. Result: prose CLAIMING governance rose 245 → 288 while governing EDGES
fell 215 → 201, and prose hops fell 128 → 105. **Naming a target population makes this model
treat it as a quota** — S-1 (+12.3 emissions), S-3 (+7.7), and now a parser-stage instance
where the quota was filled in the field the downstream stage does not read. Both rules were
reverted; gen2's wording stands.

### `parse_audit.py` — a parse-quality instrument that never reads the reference

Five checks comparing annotation against RTL. Deliberately blind to the ground truth: a
parse metric that consulted the answer key would select parses that agree with the answers
rather than parses that describe the design, and the difference would be undetectable later.

Baseline on gen3: 134 elements in a condition with no governing edge; 112 whose prose claims
governance with no matching edge; 278 whose target is tested with no prose mentioning it; 58
forwarded fields unclassified; 87 evidence strings citing no construct. Hallucination is
**not** a problem — 96% of records cite an identifier and only **7 of 1 689 (0.4%)** cite one
absent from that entity, all of them family shorthands (`dev_x_req_o` for `dev_00..31`)
rather than inventions. Relationship targets: 2 unresolved of 3 056.

**One real accuracy defect:** 6 of 140 `ISOLATED` claims are wrong, every one a record
aggregate whose fields are used individually (`imem:bus_req_i` marked uncoupled while
occurring 27 times). Fixed by clarifying the `ISOLATED` definition rather than by adding a
rule.

### What the parse does and does not transfer

| feature | reference assets | non-assets | gap |
|---|---|---|---|
| has a governing edge | 38% | 10% | **+28pt** |
| mentions external writability | 24% | 26% | **−2pt** |
| mean edges per element | 2.04 | 1.41 | +0.62 |

Measured directly from the RTL, both features discriminate: over the 271 dotted signal
fields, 80% of true assets appear in a condition against 28% of non-assets, and 57% are
written from an input port against 24%. **The parse transfers the first and loses the
second entirely.** `role` already asks whether anything outside the entity can change the
element; it is not being answered. Left open deliberately — a third attempt at instructing
it would repeat the mistake above.

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


---

## 10. The assetgen_meta hand arms (`m7e194e*`), 2026-09-30 to 2026-10-02 — consolidated

Logged in full, with every reading, in `step1/lasset_step1/RELATION_EXPERIMENTS_LOG.md`; this section is the index the
v2 log was missing (0 hits for "m7e194" before it). Tuning set = the 15 reference modules, 111 entries, strict scorer,
mean of 3 runs, gpt-5-mini executor, unless marked. "(log)" = re-derived in the session that wrote that log entry;
"(here)" = re-derived 2026-10-01/02.

**Lineage.** A meta-prompt (`gpt-6-astra`) wrote the seed executor prompt `e8df164fddb3`; the winner `m7e194es0ism`
(`0d0def4c6fe3`) = that seed + two worked examples (omsp_gpio, tiny_aes). Every arm below is a hand arm on the winner.

| arm | change | P | R | emitted/run | verdict / mechanism |
|---|---|---|---|---|---|
| `v2x3r8` | the v2 baseline used as reference row | 0.296 | 0.853 | 319.7 | (here) |
| `m7e194es0ism` | seed + worked examples | 0.344 | 0.847 | 273.3 | winner (here) |
| `ismr` | + relationship map (LLM-written E3 maps) in the input | 0.353 | 0.778 | 244.7 | recall cost, mostly `cpu` sub-block-wired signals (here; trace in log) |
| `ismc` | + code-written map | about `ismr` | | | (log) |
| `ismcap` | + one captured-input bullet | 0.355 | 0.829 | | ineffective: target inputs 4/12 (log) |
| `ismq` | + four CIA questions per value | 0.352 | 0.754 | 237.7 | harmful: questions answered but uniform; recall cost (here) |
| `ismrq` | map + four questions | 0.360 | 0.697 | 215.0 | harmful (log) |
| `ismd` | ASSET_DEFINITION rules: deciders primary, transit registers secondary | 0.340 | 0.877 | 286.3 | not adopted: transit rule ignored (0/378 concepts use it) (here) |
| `ist` | eight-part restructure, map with occurrence IDs + code flow graph, occurrence + edge citation per element, questions + influence / hypotheses / exclusions lists | 0.359 | 0.691 | 213.7 | traceable (94% of citations verify; 276/276 concepts cite map facts) but recall FAIL; same as `ismrq` (here) |
| `ist2` | `ist` without questions and side lists, established-value criteria restored, transport and sub-unit citation fixes; separate SoC-engineer CIA labelling call (P3164 3.1.1) | | | | built 2026-10-02, not run; readings `assetgen_meta/hand_arms/read_ist2.py` |

**Held-out (26 modules, 189 entries; pre-registered, read once, `assetgen_meta/HELDOUT_PREREG.md`):** winner base
0.352 / 0.852 (458 emitted/run); MV + NONE + BF 0.399 / 0.884, adopted (precision gain over MV +0.049, 95% interval
[0.025, 0.080]); GUARD 0.446 / 0.801, beats equal-strength random thinning (0.393 / 0.707) but stays a secondary row
for lack of a basis. LAsset initial on the same modules: spec + RTL 0.734 / 0.862; RTL-only 0.730 / 0.757 (the
like-for-like row; `LAsset_initial_results/`). The open threat "No held-out set exists" in section 9 no longer holds.

**Blind-agent study (Claude executor, RTL + map, prompts written blind; `blind_agent/REPORT.md`):** winner D1 0.359 /
0.577 tuning, 0.362 / 0.619 held-out; the gap to the reference is its conventions (port fields never, strobes and
decisions listed), not reasoning.

**Lessons this adds to sections 4-8.**
- A sentence that tells the model to leave something out changed nothing in five arms (`ismd`, `ismcap`, `ismq`,
  `ismrq`, blind prompts); only code levers moved precision (`ist_levers.py`, `post_levers.py`).
- Per-value questions inside the generation call cost recall (`ismq` about -0.09, `ismrq`, `ist`), whatever their
  form; answers stayed uniform (integrity yes 274/276, confidentiality no 276/276 in `ist`). The confidentiality
  criterion inherited from the seed ("require an RTL restriction on disclosure") is not P3164's question: P3164 Q1
  assumes the integrator may need protection and answers "yes" for stored, generated or readable data in 4 of its 5
  worked designs (p.9-23).
- A second output list in the same call is a destination (as SEC): `ist` parked 19 reference run-slots in its
  influence list.
- A rule that opens a citation route for record ports reopened the transport class (`ist`: about 40 FP run-slots).
