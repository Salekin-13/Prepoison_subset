# Ablation log — LAsset replication on NEORV32

Started 2026-08-02, once the evaluation framework was in place. Nothing generated before
that date is part of this study.

How to use this file:

- §2 is the configuration every arm runs on. It changes rarely; if it changes mid-study,
  say so in §5 and note which results predate the change.
- §3 is the arms. Write the arm and its `Expect:` **before** running it. That ordering is
  the only thing separating a finding from a story told after the fact.
- §4 is results. Paste `ablate()` output; never hand-edit a number.
- Commit an entry in the same commit as the change it describes, so `git log` and this file
  cannot disagree.

IDs: `C-nn` configuration · `A-nn` arm · `M-n` metric version.

---

## 1. The paper's stages

What each stage is for, and what Algorithm 1 says. Scope of this replication: **lines 3–5**.

| line | stage | purpose | in scope |
|---|---|---|---|
| 1 | `MOD_LISTING` | prune the RTL file list on module *names* | reference only |
| 3 | `SpecRAG` | retrieve datasheet passages for module *m* → technical summary | yes |
| 4 | `LLMparse` | extract ports/signals — the closed set assets must bind to | yes |
| 5 | `LLMasset(·, ICLasset)` | emit primary assets, guided by in-context examples | yes — the target |
| 6 | `SecAsset` | accumulate across modules | trivial here |
| 7–9 | refinement | attack-surface / CWE / self-critique passes that prune | not replicated |

Two facts that shape every arm:

- Refinement only **removes** — on the paper's own figures, precision +0.083 and recall
  −0.026. Recall out of line 5 is therefore a hard ceiling on the final result, which is why
  the objective here is recall rather than F1.
- The paper does not specify how RTL reaches line 5, how the closed set is built, or how the
  ICL examples are constructed. Those are ours. Each one is either §2 or an arm.

**References.** `gt` = `Asset_Dataset_Statistics_NEORV32.xlsx`, sheet `Assets (Manual)` —
the paper's manual True Assets; ground truth. `paper` = `asset_list_neorv32_initial.json` —
the output of the paper's own line 5; a target to match, not ground truth, and carrying its
own false positives.

---

## 2. Configuration under test

Settled before the study. Not arms — no arm varies these unless one is promoted to §3.

### C-01 · Kept `fifo`, `package`, `boot_rom` that the paper pruned
Paper prunes 51 RTL files to 41 IPs on module names; these are among the ten dropped. Kept
as the only negative controls available — a prompt that cannot say "no assets here" will
invent them, and nothing else in the set tests that. Scored as `skipped`, not as false
positives, so they do not distort totals.

### C-02 · SpecRAG at the paper's parameters
chunk 1000 / overlap 200 / top-k 20, `text-embedding-ada-002`. Unchanged so that any
difference is attributable downstream. Summaries are generated once and reused by every arm.

### C-03 · Closed set extracted deterministically, not by the LLM
The paper does not say how line 4 extracts elements. Ours is regex extraction over the VHDL
(`rtl_parse.py`); the LLM only annotates what each element *means* and is told the list is
authoritative — add none, drop none.

An asset that does not name a real element is unverifiable, so the closed set has to be
ground truth rather than a model output. This is what makes the binding check in
`validate_primary` possible at all.

Cost: the reference set was annotated against a different NEORV32 revision than `RTL_data`
(v1.11.4.3), so some referenced identifiers do not exist in the RTL we parse. Audited
2026-08-07 against both the closed set and the raw VHDL — **two of the 111 scored
references, both in `neorv32_cache`:**

| element | class | why |
|---|---|---|
| `inval_i` | **ABSENT** | the identifier is `inv_i` in this revision; base name not in the closed set at all |
| `cache_o.cmd_dir` | **FIELD-GONE** | `cache_o_t` has `cmd_clr`, `cmd_inv`, `cmd_new` — there is no `cmd_dir` field anywhere in `neorv32_cache.vhd` |

**Max achievable recall is 0.982, not 0.991** — the earlier figure counted only `inval_i`.
**`neorv32_cache`'s own ceiling is 4/6 = 0.667**, and every per-module recall figure for
`cache` in §4 must be read against that, not against 1.0. At v01c6's 0.467 it is running at
70% of achievable, not 47%.

`cache_o.cmd_dir` *can* be matched by the scorer — `_hit_idx` lets a dotted reference match
a bare prediction, so emitting `cache_o` would score it. **That would be a spurious credit,
not a recovery**, because `cmd_dir` does not exist in this RTL at all: the model would be
scoring a hit on a field it never named and could not have found. No version has done so in
26 runs, and **A-03's rule is why** — *"Record-typed INTERNAL signals … there the field is
the asset."* An earlier draft of this entry framed that as A-03 "closing the only remaining
path" to the reference, i.e. as a cost. It is the opposite: **the rule prevents a false
positive from being scored as a true one.** Worth remembering before any future rule touches
record granularity, but as a benefit to preserve rather than a loss to undo.

Neither element has ever been produced by any version in 26 runs, which is consistent with
both being unreachable rather than hard.

**Scope of the audit.** Of the full 302-element ground truth, only 111 belong to modules
whose RTL we hold; the other 189 could not be checked. Among the checkable 111 the skew rate
is **1.8%**. If it holds, expanding to all 41 modules would surface roughly three or four
more unreachable references — **re-run this audit before reporting on the full set**, or
those will be counted as model failures.

### C-04 · RTL comments stripped for line 5 only
Stripped from the RTL handed to the asset stage; kept for the line-4 annotation stage, whose
prompt is explicitly told to infer function from in-source comments. Line 5 takes its
semantics from the summary and the `function` fields, so it loses nothing —
`parse_rtl_file` returns an identical closed set either way.

Promote to an arm if the "free" claim ever needs evidence rather than argument.

### C-05 · No post-filter between line 5 and scoring
Considered and rejected. No dotted field of a *port* record is a labelled asset in either
reference — 0 of 110 in `gt`, 0 of 137 in `paper` — while dotted fields of *signal* records
are 28% and 35%. So the rule is port-vs-signal, not dotted-vs-undotted, and filtering on it
removes 31% of false positives.

Rejected anyway because it also destroys a true positive: `gt` wants `ctrl_i` in
`neorv32_cpu_pmp`; the model emitted `ctrl_i.csr_wdata`. A filter deletes that and converts
a TP into a FN. The same rule as an instruction redirects the model to `ctrl_i` and scores.
Delete versus redirect — with recall as the objective, redirect wins. Carried to **A-03**.

### C-06 · Three repeats per arm
Generation is nondeterministic. `REPEATS = 3`, each into its own directory with
`_run_meta.json` recording the system-prompt SHA256. The sd column is the noise floor: a gap
between arms smaller than it is not measurable.

---

## 3. Arms

One entry per arm. Fill `Expect:` before running.

### A-00 · Noise floor
**Run first.** One version, `REPEATS` runs, nothing varied. Establishes the minimum
detectable effect; every later arm is read against it. Not a separate run — the first arm
at `REPEATS = 3` produces it for free. Run as v0, 2026-08-03, prompt sha `e0d31754ca62`.

Expect: — (not recorded before the run; the first arm, before the habit was in place)

Got: **sd 0.019 recall, 0.010 F1** (M-2; per-repeat recall 0.536 / 0.555 / 0.564).

Three things follow.

1. The instrument is precise. Aggregate recall is good to about ±0.03, so most planned arms
   are measurable.
2. **Repeats are not the binding constraint — modules are.** Repeat sd is 0.019, but the
   paired CI is driven by variance *across the 15 modules* and runs about ±0.14 wide.
   More repeats will not narrow it. Effects below roughly 0.10 paired recall will come back
   inconclusive whatever we spend. Design arms expected to move things a lot.
3. The failure is not "too many" or "too few" assets but the **wrong class of element** —
   see §4. That was not visible in the aggregate and is now printed for every arm.

### A-01 · ICL construction
Line 5 takes an `ICLasset` argument whose contents the paper never specifies. Four
constructions, holding `ASSET_PRIMARY_CORE` fixed:

| version | examples | system prompt |
|---|---|---|
| v0 | P3164 §3.2 only, deliberately **not** format-matched | ~3.2k tok |
| v1 | adapted to our parsed shape and output contract | ~7.1k tok |
| v01 | worked input→reasoning→output triples: `omsp_gpio` + `tiny_aes` | ~25.3k tok |
| v02 | same GPIO, AES swapped to `aes_highthroughput_lowarea` | ~31.0k tok |

v0 vs v1 asks whether the model needs examples in the shape it must produce, or only the
concepts. v01 vs v02 is **not** a clean arm: it moves the IP *and* the label provenance
(`tiny_aes` is the only AES in the set LAsset labelled, so v02's objectives are derived from
P3164 rather than sourced). Read it as architectural fidelity, not as a single variable.

No NEORV32 module appears in any example, so the eventual 41-module run stays uncontaminated.

**v1 is not being run.** Its examples were fabricated rather than sourced — `dir_sel_i`,
`pad_io`, `lfsr_state`, `Tausworthe` and others appear nowhere in P3164. They have no place
in a replication. v01 is the first arm: real Verilog from published IPs, published manual
labels, P3164 reasoning.

Expect (registered before the run, in discussion rather than in this file — write it here
next time): port recall rises, because v01's examples bind 18 of 18 assets to top-level
ports while v0's bind to nothing. Registered discriminator: if the gain lands **only** in
modules whose summaries already name their port assets, stage 3 is the constraint and no
stage-5 prompt finishes the job; if it lands in both groups, stage 5 is. Also predicted:
emissions rise and precision falls, because the GPIO example runs at 20.9% asset density
against a real 6.8%.

Got (v01, 2026-08-03, prompt sha `e99a0b798fd2`, 3 repeats, M-2):

| | port | signal | signal-field | aggregate recall | F1 |
|---|---|---|---|---|---|
| v0 | 0.326 | 0.771 | 0.688 | 0.553 | 0.389 |
| **v01** | **0.589** | **0.573** | 0.688 | 0.607 | 0.390 |
| *paper* | *0.894* | *0.906* | *0.935* | *0.910* | *0.815* |

Paired, modules as the pairing unit:

| metric | Δ | 95% CI | modules |
|---|---|---|---|
| **port recall** | **+0.181** | **[+0.048, +0.302]** | 9 better / 1 worse (n=12) |
| **signal recall** | **−0.157** | **[−0.229, −0.086]** | 0 better / 6 worse (n=8) |
| signal-field recall | +0.008 | [−0.074, +0.123] | null |
| aggregate recall | +0.049 | [−0.061, +0.166] | 7 better / 7 worse — null |
| F1 | −0.020 | [−0.094, +0.059] | null |

**Three findings.**

1. **The port-blindness diagnosis was right and the fix works at stage 5.** Port recall
   nearly doubled, and the effect clears zero.
2. **It is a trade, not a gain.** Signal recall fell almost as much, and *unanimously* —
   not one module improved. The examples bind 100% to ports; the model swapped one bias for
   another. Predicted before the run, and the size was underestimated.
3. **Stage 3 is not the constraint.** Group B — the 8 modules whose summaries name *none*
   of their port assets — went 0.355 → 0.645. If the summary naming a port were necessary
   for the model to find it, group B could not have moved at all. This closes the SpecRAG
   hypothesis and saves regenerating every summary and re-baselining every arm.
   (Group A went 0.271 → 0.479. The A-vs-B gap is **not** tested and would not survive a
   test at 16 and 31 elements; only group B's movement carries the argument.)

Also: emissions 205 → 235 (+15%) as predicted, and **port-field false positives 19 → 51**,
now 30% of all FPs. Not predicted. The examples are Verilog, which has no record types, so
they can never demonstrate the port-versus-port-field distinction — which is exactly what
A-03 addresses.

Decision: **keep v01 as the baseline for subsequent arms.** The port mechanism is real and
its aggregate recall is higher; the signal loss is a separate defect to be fixed on top,
not a reason to revert. *(Superseded 2026-08-05: A-02's decision rule fired and promoted
`v01c2`. v01 remains the baseline **for A-02 only**, which is the arm that tested against
it.)*

### A-01x · Why no example can fix the signal loss
Checked before planning the next arm: every manual asset list in the Calgary IP set is
75–100% top-level ports — `axi_adapter` 75%, `hmac` 83%, `aes` 95%, and every remaining IP
100%. NEORV32's ground truth is 42% port / 29% signal / 28% signal-field.

That is the IP-regime versus SoC-regime split showing up in the labels: in a standalone IP
the interface *is* the function, so its ports are the assets; in an SoC the bus is inherited
plumbing and the assets are internal state.

**So a composition-matched example cannot be built from this source — the labels do not
exist.** The signal-recall loss has to be addressed by instruction (A-02), not by example.
This also means v02 will face the same constraint: its 24 example assets are likewise 100%
ports.

### A-02 · Core prompt — role, not location
**Next arm.** Version `v01c2`, prompt sha `8df77c38fab9`. Baseline **v01**, not v0.
`ASSET_PRIMARY_CORE_V2` = `ASSET_PRIMARY_CORE` plus one insertion in STEP 2 and nothing
else — built by substitution with an assert, so "identical apart from the insertion" is
guaranteed by construction rather than by care. ICL block held at v01. Diff: 0 lines
removed, 11 added.

**Why instruction and not a better example.** A-01x: every Calgary manual asset list is
75–100% ports, so a composition-matched example does not exist in the labelled corpus.
Instruction is the only channel left.

**Why the existing wording was not enough.** `ASSET_PRIMARY_CORE` already says *"Ports AND
internal signals/registers are equally eligible"* and *"may fan out to SEVERAL elements"*.
Both correct, both ignored — 18 port-bound demonstrations beat two correct sentences. So the
insertion is **procedural** (a question to answer per conceptual asset) rather than a third
restatement of eligibility, and it names the examples as the source of the skew so the
instruction can reach past them.

**The failure is location, not concept.** v01's misses line up role-for-role against its own
example assets:

| v01 misses (internal) | role | example asset, a **port** |
|---|---|---|
| `div.start`, `mul.start`, `fifo.re` | operation enable / start | `per_en`, `p1_dout_en` |
| `ctrl.rs1_is_signed`, `ctrl.rs2_is_signed` | operand / mode select | `p1_sel`, `per_we` |
| `cache_o.cmd_dir` | direction control | `p1_dout_en` — also direction control |
| `alu_add`, `alu_res` | computed result | `state_out` |
| `a_req`, `b_req`, `keeper.halt` | request gate | `per_en` |

The GPIO example's thesis is that direction control is an asset, and v01 then missed an
internal direction signal in all three repeats.

The role list in the insertion is tied to roles the examples already demonstrate, not a free
checklist of signal types — a free-standing checklist became a generator once before (`cpu`
emitted `ctrl.*` eleven times). No count, proportion or threshold appears.

Expect:

1. **Signal recall recovers toward v0's 0.771**, from v01's 0.573. Specifically the four
   regressions — `a_req`, `b_req`, `fifo.re`, `cnt_timeout` — should return, since v0 found
   every one of them in every repeat.
2. **Port recall holds near v01's 0.589.** This is a guard, not a prediction of gain.
3. Emissions rise modestly from 235; precision flat to slightly down from 0.288.

Decision rule, fixed in advance:

- signal up **and** port holds → the instruction works; `v01c2` becomes the new baseline.
- signal up **and** port falls by a comparable amount → oscillation. The instruction is
  displacing rather than adding, more instruction will not help, and the example channel
  (v03, the P3164 §3.2.4 SRAM controller) becomes the only remaining lever.
- signal flat → a demonstration cannot be overridden by instruction at all. That is itself a
  finding about ICL in this pipeline, and it makes v03 the priority.

Read `paired_classes()` output, not aggregate recall — A-01 is the proof that the aggregate
hides exactly this kind of two-sided movement.

**Correction, 2026-08-05, post-hoc.** The clause "since v0 found every one of them in every
repeat" in Expect 1 is wrong, and was wrong when written. It is a misreading of
`signal_misses.py`, where `always01 - always0` means "v01 misses it in all three repeats and
v0 does *not*" — i.e. v0 found it **at least once**, not every time. Actual v0 hit rates:
`a_req` 1/3, `b_req` 1/3, `fifo.re` 1/3, `cnt_timeout` 2/3. The prediction itself stands as
written; only its stated basis was weaker than claimed. Left in place rather than edited — a
pre-registered block quietly corrected after the result is known is no longer pre-registered.

Got: **rule fires; `v01c2` becomes the new baseline.**

Provenance verified before scoring. Each version records one prompt sha across all three
repeats — `v01` `e99a0b798fd2` (101 415 chars), `v01c2` `8df77c38fab9` (102 781) — matching
the sha recomputed from `prompts.py` today, so no repeat ran a different prompt. The composed
system prompts differ by **one diff hunk, 0 lines removed, 11 added, +1366 chars**, and the
ICL block is byte-identical at 97 049 chars. One variable, confirmed at the byte level.

| | Δ (v01c2 − v01) | 95% CI | modules |
|---|---|---|---|
| **port recall** | **+0.262** | **[+0.110, +0.414]** | 9 better / 1 worse (n=12) |
| **signal recall** | **+0.106** | **[+0.047, +0.165]** | 6 better / **0 worse** (n=8) |
| signal-field recall | +0.094 | [−0.017, +0.205] | null |
| **aggregate recall** | **+0.162** | **[+0.083, +0.232]** | 13 better / 1 worse |
| precision | −0.001 | [−0.035, +0.030] | null |
| F1 | +0.029 | [−0.017, +0.071] | null |

Against the three predictions:

1. **Partial.** Signal reached 0.677, not v0's 0.771, and against v0 it is still down
   −0.052 [−0.124, −0.005]. Instruction undid most of the ICL port bias, not all of it. Of
   the four named elements, `fifo.re` went 0/3 → 2/3 and `cnt_timeout` 0/3 → 1/3; `a_req`
   and `b_req` did not return at all (0/3 in both versions).
2. **Missed, in the good direction.** Port was written as a guard at 0.589 and reached
   0.851. The insertion asks *both* questions, so a port gain was foreseeable and was not
   called — the prediction was anchored on the signal regression and ignored the other half
   of its own instruction.
3. Precision exact (0.288 → 0.286). Emissions were not modest: 235 → 304, **+29%**.

**Robustness.** "The rule fired" on pooled means can still be one repeat or one module:

- *Per repeat.* Port separates completely — the worst v01c2 repeat (0.809) beats the best
  v01 repeat (0.660). Signal does **not**: v01 spans 0.500–0.625, v01c2 spans 0.625–0.719,
  touching at 0.625.
- *All nine cross-pairs.* The rule fires strictly in eight. The ninth, v01 r0 → v01c2 r2, is
  d(signal) = **+0.000** exactly with d(port) = +0.319 — a tie, never a reversal. Worst case
  across all nine is signal flat with port +0.149, so branch 2 of the decision rule
  (oscillation) is excluded even in the unluckiest pairing.
- *Per module.* Signal 6 better / **0 worse** / 2 unchanged, and both flats (`cpu_cp_cfu`,
  `trng`) were already at 1.000 — no module could have improved and failed to. Port's single
  loser is `twi`, thin at denominator 3: `[2/3 3/3 2/3] → [1/3 2/3 2/3]`.
- *Leave-one-module-out.* Dropping any one module leaves the effect clear of zero in 12/12
  (port), 8/8 (signal), 15/15 (aggregate). Dropping `cpu`, the largest port contributor at
  +0.733, still gives +0.219 [+0.078, +0.363]. Dropping `twi` *raises* port to +0.306, so the
  one opposing module is depressing the estimate, not propping it up.

So the port half is unconditional; the signal half is directionally robust but not separated
at repeat level. At three repeats a +0.106 signal effect against a v01 spread of 0.125 sits
at the edge of what this design resolves. Separating it costs repeats, not prompt work.

**Unpredicted side effect.** `v01c2` r2 emitted four entity-qualified names
(`neorv32_cache_memory.clr_i`, `.inv_i`, `.new_i`, `.rdata_o`) — the model merged the
`Asset RTL` and `Entity` fields. The validator rejected them as ungrounded and one
regeneration did not fix it. Frequency 4/729 emissions against **0/670 in v0 and 0/766 in
v01**, so the insertion caused it; *which clause* cannot be resolved from a single
occurrence. Two candidates: the phrase "inside the module" meeting a multi-entity file, or
the foreign identifiers the citation introduces with no entity context. Costs v01c2 four
FPs, so every figure above is conservative for this arm.

**The port lever is now nearly exhausted.** Six modules sit at 1.000 port recall — `cpu`,
`cpu_cp_muldiv`, `cpu_pmp`, `debug_dtm`, `trng`, `wdt`. What remains is `cache` at **0.000**
(`addr_i` and `we_i` missed by every repeat of every version — a specific diagnosable
failure, not a dosage problem), `twi` 0.556, `spi` 0.733. Further general port instruction
will not move much; recall work should go to signal, and the next arm to precision.

### A-03 · Port-record granularity rule
**Next arm.** Baseline **`v01c2`**, not v01 — re-baselined per A-02's own decision rule.

**Why the baseline moved.** The rule fixed in advance said *"signal up and port holds →
`v01c2` becomes the new baseline"*, and it fired. Running A-03 against v01 instead would
measure a configuration that will never ship, and would override a pre-registered promotion
after seeing the result — the exact failure pre-registration exists to prevent. The earlier
note *"run separately from A-02"* was about running the two changes **simultaneously** in one
arm, where they could cancel the way port and signal did in A-01. Sequentially, with A-02's
effect already measured and bounded, attribution stays clean.

The residual risk is interaction: V2's *"ask BOTH — which port carries it? which internal
signal holds it?"* sits in the same STEP 2 region as the granularity rule. If A-03 reads null
on `v01c2`, that is ambiguous between "the rule does nothing" and "V2 masks it" — resolve it
*then* with one confirmation arm on v01, conditional on the null. Running both baselines
up front doubles the cost for information probably never needed.

**The target grew.** Port-field false positives: v0 19 → v01 51 → **v01c2 73**, now 34% of
all FPs and the largest single block. Excess over the paper by class, on `v01c2`:
port-field 73, signal-field 64, signal 34, port 13.

#### Clause 2 is dropped — the defect does not occur
The rule as drafted had two halves. The second — *"a record-typed internal signal is the
opposite: name the field, not the record"* — was checked against the runs before being
carried forward: across 3 repeats × 15 modules of **both** v01 and v01c2, the model emitted a
bare whole internal record **zero times**. It already names the field. The clause would fix
nothing and could only push more emissions into signal-field, which already carries 83 FPs
against the paper's 19. Dropping it also keeps the arm to one variable.

#### Ceiling, measured not guessed
Clause 1 applied *perfectly* to the real `v01c2` outputs (rewrite each port-field emission to
its record, then dedup), as an oracle:

| | emit | TP | FP | P | recall | F1 |
|---|---|---|---|---|---|---|
| v01c2 as run | 304 | 87.0 | 217.0 | 0.286 | 0.784 | 0.419 |
| **oracle: clause 1 perfect** | **258** | **87.0** | **170.7** | **0.338** | **0.784** | **0.472** |
| *LAsset paper* | *137* | *101* | *36* | *0.737* | *0.910* | *0.815* |

**Recall is untouched — TP is identical.** So the arm is precision-only by construction, and
its Expect must be written in precision terms with a recall guard, not the other way round.

*(Post-run: the oracle held. Actual `v01c3` precision 0.315 against 0.338 predicted, F1 0.451
against 0.472, recall 0.793 slightly BETTER than the 0.784 predicted. About 0.023 optimistic
on precision, because the arm also raised signal-field FPs, which the oracle held fixed.)*

The important qualifier: the 73 port-field emissions collapse to **34 distinct records, and
only one of them (`cpu_pmp.ctrl_i`) is in `gt`.** The other 33 are bus plumbing —
`bus_req_i`, `bus_rsp_o`, `host_req_i`, `dmi_req_o` and kin. So the rule is a **rename**, and
the renamed thing is still wrong 33 times out of 34; the entire gain is dedup (many fields →
one record), not correction. The underlying defect — emitting inherited bus interface at all
— survives it untouched. Worth knowing before spending 54 calls on a +0.052 precision ceiling.

Expect:

1. **Precision rises from 0.286 toward the 0.338 oracle**, realistically capturing a fraction
   of it. Anything above ~0.31 is the rule working.
2. **Port-field FPs fall from 73.** This is the mechanism check — if precision moves without
   this falling, something else caused it.
3. **Recall guard: port recall holds at ≥0.80** (currently 0.851) and aggregate recall does
   not fall. The rule pushes toward whole ports, which is the direction `gt` wants, so it
   should be neutral-to-helpful for port recall; a drop means it is suppressing ports
   outright rather than re-naming their fields.
4. Signal and signal-field recall unchanged — the rule does not mention them.

Decision rule, fixed in advance:

- precision up **and** recall guard holds → keep; `v01c2` + rule becomes the baseline.
- precision up **and** port recall falls → the rule suppresses whole ports too. Revert, and
  treat port-field suppression as a scoring-side question, not a prompt one.
- precision flat → a granularity rule cannot be carried by prompt text in this pipeline. That
  is a finding. The same transform as a deterministic post-filter would bank the full 0.338
  ceiling, but it adds a stage Algorithm 1 does not have and would have to be declared as a
  deviation, not folded in silently (see C-05).

Got: **keep; `v01c3` becomes the new baseline.** Two arms, and the control is what decides it.

Provenance: `v01c3` sha `b6d98530d74b` (103 121 chars) and `v01r` sha `037070a1959d`
(101 755), one sha per version across every repeat, both matching the value recomputed from
`prompts.py`. `v01c2 → v01c3` and `v0 → v01r` are each 2 hunks, −1 / +2 lines, +340 chars —
provably the same edits; `v01c3 → v01r` is 1 hunk, −1366 chars, exactly V2's insertion.

**The rule is followed, on both cores.** Port-field emissions per repeat: `v01` 51.3 (21.9%
of all emissions) → `v01r` **1.0** (0.5%); `v01c2` 73.7 (24.2%) → `v01c3` **1.7** (0.6%).
About 98% compliance either way. This is the most reliably-obeyed instruction in the study,
in sharp contrast with A-02, where the same channel bought only partial signal recovery.

| | **V0 core** `v01 → v01r` (n=2) | **V2 core** `v01c2 → v01c3` (n=3) |
|---|---|---|
| **precision** | **+0.060 [+0.024, +0.099]** | **+0.042 [+0.005, +0.077]** |
| **F1** | **+0.053 [+0.016, +0.090]** | **+0.046 [+0.002, +0.087]** |
| **port recall (GUARD)** | **+0.048** [−0.068, +0.150] | −0.037 [−0.194, +0.116] |
| aggregate recall | +0.012 [−0.061, +0.077] | +0.008 [−0.074, +0.089] |
| signal recall | −0.014 null | +0.042 null |
| signal-field recall | +0.024 null | +0.023 null |

Against the four predictions:

1. **Precision hit 0.315** against the 0.338 oracle — above the ~0.31 threshold registered as
   "the rule working". The oracle was sound and about 0.023 optimistic; worth remembering
   next time one is used to size an arm before spending calls.
2. **Port-field FPs fell 72.7 → 1.7.** Mechanism confirmed.
3. **Recall guard.** Aggregate recall held on both cores. Port recall is the awkward part and
   is resolved below.
4. **Signal and signal-field were not left alone.** Signal-field FPs rose 83.0 → 92.3 and
   signal-field recall +0.023. Both null, both small, but the fence sentence was described in
   this log as changing "nothing the model already does" and that was wrong — telling the
   model internal records are "the opposite" mildly *encouraged* field emission.

**The guard, and why the control settles it.** Port recall came in at **0.801** against a
pre-registered floor of 0.80 — a pass by 0.001, and one that hides a split: the per-repeat
values are 0.745 / 0.766 / **0.894**, so two of three repeats fail and only r2 lifts the
mean. Read as a mean it passes; read as three runs it fails twice.

That is exactly what `v01r` was run to disambiguate, and it does: **on the V0 core the same
edits moved port recall +0.048, the opposite sign.** For "A-03 suppresses whole ports" to be
true the effect must be negative, and the independent replication is positive. Both deltas
are null, so nothing is established either way — but there is no support for the concern, and
`v01c3`'s port-recall spread (0.149, more than double `v01c2`'s 0.063) is consistent with
repeat noise rather than a rule effect. A V2-specific interaction cannot be excluded; there
is simply no evidence for one.

`v01r` was pre-registered as **directional only** at n=2 and that stands — the intervals
above are shown for completeness and the argument does not lean on its asterisks. What
carries it is that **every metric has the same sign on both cores except signal recall**, and
the two that clear zero clear it on both. Replication across an independent core is stronger
evidence here than either arm's interval.

Decision: **`v01c3` is the baseline from A-04 onward.** `v01r` has the higher precision of the
two A-03 arms (0.331 vs 0.315) but that is the V0 core's lower emission rate, not the rule —
its recall is 0.626 against `v01c3`'s 0.793, and since refinement only removes, recall out of
line 5 is the ceiling. `v01c3` is the unambiguous carry-forward.

#### The base prompt demonstrates the defect
Found while drafting the rule, and it changes what A-03 is. `ASSET_PRIMARY_CORE` — present
unchanged in **v0, v01 and v01c2** — says in INPUTS:

> Never invent, rename, split, or merge a name; copy record-field names verbatim including
> the dot (e.g. `"ctrl.buf_req"`, `"host_req_i.stb"`).

`ctrl` is an internal signal record (7 of the 15 modules). But **`host_req_i` is a *port*
record** — `neorv32_bus` and `neorv32_cache` — so the prompt's own worked example of correct
naming is a port-record field: the class that is 0/31 in manual `gt`, 0/47 in the paper's
list, and 73 FPs in v01c2.

Sized honestly, it is **not** the driver: `host_req_i` is 12 of the 218 port-field FPs across
three repeats (5.5%). The real mass is elsewhere — `bus_req_i` 82 (37%), `ctrl_i` 37 (17%),
`bus_rsp_o` 21. It matters for *interpretability*, not magnitude: A-01 established that a
demonstration beats a correct sentence here (18 port-bound examples overrode two accurate
lines of eligibility text), so a rule arguing against a live counter-demonstration thirty
lines above it would make a null unreadable — "the rule does nothing" and "the rule lost to
the example" look identical.

So A-03 is **two edits stating one proposition**, applied together. Confounded by
construction: a win cannot be split between the rule and the example removal. That trade was
taken deliberately — an interpretable null is worth more here than an attributable win.

#### A-03 prompt text, as implemented
Built by `prompts._apply_a03()`, which round-trip asserts that undoing both edits reproduces
the input byte for byte, so "identical outside the two edits" is guaranteed by construction.

Edit 1, INPUTS — drop the port-field illustration, keep the sentence's actual job:

```diff
- copy record-field names verbatim including the dot (e.g. "ctrl.buf_req", "host_req_i.stb").
+ copy record-field names verbatim including the dot (e.g. "ctrl.buf_req", "rtx_engine.sreg").
```

Edit 2, RULES — new bullet immediately after the `"Asset RTL"` bullet:

> Record-typed PORTS are named WHOLE. A record port is the module's external interface; when
> it carries an asset, the asset is the port itself (`"ctrl_i"`), never one of its fields
> (`"ctrl_i.csr_wdata"`). Record-typed INTERNAL signals are the opposite and are unchanged by
> this rule — there the field is the asset (`"ctrl.buf_req"`), as above.

Every identifier verified against the parsed closed sets: `rtx_engine.sreg` is a signal-field
in `neorv32_spi`; `ctrl_i` is a port in `cpu_cp_muldiv` and `cpu_pmp` **and is in `gt`**;
`ctrl_i.csr_wdata` is a port-field in the same two modules and is in no reference. The
example is the one case out of 34 where the collapse actually yields a true positive.

**The second sentence is a fence, not the dropped clause 2.** Clause 2 was a *fix* for a
defect that occurs zero times. This is a *guard*: without it the port rule can bleed across
to internal records, and signal-field is 31 references at 0.817 recall — the collateral loss
would swamp the gain.

#### The two arms

| version | core | baseline | repeats | system sha |
|---|---|---|---|---|
| `v01c3` | `_V3` = V2 + A-03 | `v01c2` | 3 — **the arm** | `b6d98530d74b` |
| `v01r` | `_V0R` = V0 + A-03 | `v01` | 2 — **control** | `037070a1959d` |

Diffs, verified: `v01c2 → v01c3` and `v0 → v01r` are each 2 hunks, −1 / +2 lines, +340 chars
— the same edits. `v01c3 → v01r` is 1 hunk, −11 lines, −1366 chars, i.e. exactly V2's
insertion and nothing else. ICL block byte-identical in all four at 97 049 chars.

`v01r` runs at 2 repeats and is **directional only** — A-00 put the recall noise floor at
sd 0.019, and n=2 supports no sd and no CI. It answers one question, "does the rule do
anything at all on the V0 core?", and must never be quoted with an interval. It is run now
rather than conditionally on a null so that both arms face the same model snapshot; deferring
it would confound the answer with any change to `gpt-5-mini` in the interval.

Grounding beyond the counts in C-05: `gt` does treat CPU privilege/interrupt/debug state as
assets — `firq_i`, `mei_i`, `msi_i`, `mti_i`, `dbi_i` in `neorv32_cpu`, `ctrl_i` in
`neorv32_cpu_pmp` — and names every one as a whole, undotted port.

Phrased as granularity with no count or threshold, deliberately. A numeric cap becomes a
hard quota however it is hedged: an earlier "stop at ~20% of the closed set" suggestion cost
7 of 17 recall losses on `cpu_cp_cfu`, whose ground-truth density is 38%.

---

### T-1 · Diagnostic — is a miss a conception failure or a binding failure?
**Not an arm.** It changes the output contract, so its recall delta is confounded by
construction and is never quoted as a result. The deliverable is the classification.

Question: when a reference is missed, did the model (a) never conceive the idea, or (b)
conceive it and fail to bind it to the element? These need opposite fixes — (a) means the
C/I/A/U rubric is wrong, (b) means STEP 2's mapping is. There was no data either way, so
every recall-focused edit was a guess about which half to aim at.

Method: expose STEP 1 as a `ConceptualAssets` array, with a `Concept` id on each asset so
the concept→element mapping is stated rather than inferred. Then for each miss, ask whether
the model's own list contains a concept covering it.

#### The v01c4 result was an artefact of our own code
`v01c4` reported `ConceptualAssets` in **0 of 90 files**, and that was written up here as a
prompt failure with an explanation about the ICL examples overriding the contract. Both were
wrong. `generate_assets()` contained:

```python
result = {"IP": stem, "Assets": obj["Assets"]}
```

It rebuilt the response from two keys and wrote that to disk. Everything else the model
returned was deleted before it reached a file. A single-module probe printing the *raw*
response settled it: `top-level keys: ['IP', 'ConceptualAssets', 'Assets']`.

The clue that misled the diagnosis came from the same line. `obj["Assets"]` passes through
wholesale, so fields nested *inside* each asset survived while top-level keys vanished. That
asymmetry — "it adopted the nested `Concept` field but skipped the top-level array" — read
as evidence about the model and was evidence about five words of Python.

Cost: v01c4's entire concept layer, 90 calls, unrecoverable because only the reshaped result
was ever written. Fixed two ways — `generate_assets` now preserves every top-level key, and
the verbatim response is saved to `<run>/_raw/<stem>.json` before parsing, in a subdirectory
`load_run()` cannot see (it globs `*.json` non-recursively; verified 18 modules before and
after adding raw files).

**Three guards added, each for a failure that had already happened once:**
- `validate_concepts(expect_concepts=True)` — the old no-op-on-missing-array let 90
  module-repeats print `[ok]` while emitting nothing usable. `EXPECT_CONCEPTS` is *derived*
  from the composed prompt, never hand-maintained.
- `split_misses` / `objective_coverage` refuse a run with no concept list. Without that they
  scored every miss as "objective absent → (a)" and reported **100% conception failure** —
  confidently wrong rather than broken.
- The diagnostic cell raises if its `DIAG_VERSION` points at a concept-less run. It had
  `v01c4` hardcoded and produced exactly that false 100% while v01c5 sat on disk populated.

#### Got — v01c5, n=5, sha `9f66b93202ce`
Pre-registered checks all pass: `ConceptualAssets` in **89/90** files (the exception is
`neorv32_package`, 0 assets, legitimately nothing to conceive); **3.63** assets per concept
against a registered band of 1.5–6; **6.2** concepts per module against ≥4. v01c4's dangling
ids had predicted 3.63 and 6.2 as 3.37 and 7.0 — an independent confirmation that the
salvage read the structure correctly.

Judge calibration on 40 found references: **exact id agreement 0.97, any-concept 1.00.**

| verdict | per repeat | share |
|---|---|---|
| **(b) conceived but unbound** | 13.8 | **82.1%** |
| (a) objective absent from the concept list — *deterministic* | 2.4 | 14.3% |
| (a) judge finds no covering concept | 0.6 | 3.6% |

**Misses are predominantly binding failures. The C/I/A/U rubric is not the main problem.**

Corroborated independently of the judge: sibling 32.1% + secondary 26.2% = 58% suggestive
(b), and the 14.3% (a) is deterministic — no judge involved.

**Three findings that decide what to do next.**

1. **Every strong-(a) case is Availability. 100% of them.** Availability is 30% of the
   reference set, so concentration this complete is not chance (p ≈ 7e-4 on the 6 distinct
   elements). In some modules the model conceives *no* Availability concept at all and every
   Availability reference there is lost. This is the fourth independent appearance of
   Availability under-invocation — Test 1 found it the most precise branch (0.397) and the
   least invoked (48.7 claims vs Integrity's 196), and it is over-represented in the blind
   spot.
2. **The (b) misses are a completeness problem, not a fan-out problem.** Where a covering
   concept existed, it had typically already bound 5–6 elements (22% had 5, 19% had 6,
   running to 12); only 2.8% had bound just one. The model works a concept and stops one
   short. "Enumerate more thoroughly per concept" is the right shape of fix; "conceive more
   concepts" is not.
3. **There is no separate hard core.** The 8 never-found references decompose into the same
   two causes — 1 unreachable (`cache.inval_i`, class `absent`, C-03 revision skew), 2
   Availability conception failures, 5 binding failures with the concept present.

Scope note: 84 miss *instances* over 5 repeats are only **32 distinct references**, of which
24 are found in at least one repeat. Report distinct references.

**Open threat — the judge's permissiveness is not bounded.** `calibrate_judge` runs on found
references, where a covering concept genuinely exists, so `any=1.00` measures the
true-positive direction only. It says nothing about whether the judge would find a concept
for anything put in front of it, and an over-permissive judge inflates (b). Evidence against
the extreme case: it did answer "no covering concept" 3.6% of the time. The missing control
is to judge elements against *another module's* concept list, where no hit should occur —
about 40 low-effort calls. **Until then 82.1% is an upper bound on (b).** The direction is
safe because the deterministic signals agree; the exact figure is not.

### P-1 / P-2′ / P-3 · Input ablation family
**Registered together, before any is run**, so the results are read as a set. This study has
already once run an arm, seen a null, and invented a reason to stop; three pre-registered
arms make that harder.

**Why.** Line 5 receives ~34.5k tokens per call and emits **428 assets for 111 references**
— 3.9×, against the paper's 1.2×. Nothing in this study has ever tested whether that is
driven by input volume. The user message splits:

| block | chars | share | arm |
|---|---|---|---|
| technical summary (SpecRAG) | 3 549 | 11% | **P-1** |
| parsed ports + signals JSON | 18 122 | 58% | P-2′ (partial) |
| RTL, comments stripped | 9 718 | 31% | **P-3** |

**LASP (MLCAD '24) is the prompt for the question, not evidence for an answer.** It feeds a
compact RTL *abstraction* — module hierarchy, interfaces, register/memory declarations,
configuration registers, clock and reset domains — because it cannot fit the RTL at all. We
feed the parsed closed set *and* the full RTL *and* a datasheet summary. LASP reports **no
precision or recall against any ground truth** (the word "precision" appears once, in its
conclusion, describing static analysis qualitatively), so it supplies a design contrast and
nothing more. Its CDFG step is *feature extraction after* assets are chosen — the analogue is
LAsset line 6, out of scope. Its threat-model conditioning was considered and set aside:
LASP unions assets across four threat models, which pushes emissions **up**, and those models
do not partition C/I/A, so adopting them would need a mapping layer inside the arm.

**Dropping a block is only half of each arm.** The core prompt declares its inputs and then
refers back to them, so removing a block while the prompt still says to ground in it leaves
the model told to use something absent — a confound, not a removal. Each variant also strips
the prompt's references to that block. One proposition, several edits, as in A-03.

#### P-2 was dropped, and that decision was wrong — reinstated 2026-08-08
The original note read: removing the parsed ports/signals "would also have required deleting
the closed-set contract, **A-03's port-vs-signal granularity rule**, and **all of A-08's
closure sweep**… no result could be attributed", and "without the closed set nothing can bind,
`validate_primary` rejects everything".

**That rested on one false premise: that the closed set *is* the two JSON blocks.** It is not.
The closed set is an abstraction the prompt defines, and the RTL already contains every
declaration it is built from — VHDL states its ports in the entity clause and its signals in
the architecture declarative part, which is precisely where `rtl_parse` extracts them from in
the first place. So the closed set can be **re-sourced rather than deleted**:

| | before | after |
|---|---|---|
| where the closed set comes from | the two JSON blocks in the user message | the RTL's own declarations, read off by the model |

Under that framing the objection dissolves. Three edits re-point the definition, and every
downstream instruction that says "closed set" stays **literally true and byte-identical**:
DEFINITIONS, both STEP 2 sentences, T-1's contract line, all of A-08's sweep, and the output
contract slot. A-03 survives in full — its example sentence is carried into input (4) verbatim
and its RULES bullet keeps the granularity text appended to it. Nothing is deleted that
belongs to an earlier arm.

The second claim was also wrong: `validate_primary` does not reject anything. It reports, and
the run loop reacts by regenerating once — which is a separate problem, handled below.

**P-2′ still stands and is still worth running**, but as a *follow-up* rather than a
replacement: P-2 removes the names and the `function` annotations together, so a recall fall
cannot be attributed between them. P-2′ (keep the names, strip only `function`) is what
separates them, and it should be run on `v01c6p1` whichever way P-2 lands.

**Lesson recorded.** The rejection was written confidently, with three specific reasons, and
survived unchallenged because the reasons sounded like careful engineering. Every one of them
followed from a single unexamined identification of an abstraction with its current
representation. *When an arm is rejected as impossible, the thing to re-check is the premise
that makes it impossible, not the reasoning built on it.*

---

#### P-1 · Drop the technical summary
Version `v01c6p1`, sha **`2214e7f97f39`** (101 177 chars). Baseline **`v01c6`**.

**Removed in all three places the summary appears** — one proposition, as in A-03:

| where | change |
|---|---|
| core prompt | 4 hunks, −4 / +3 lines, −173 chars — the INPUTS declaration and the three "grounded in the summary or RTL" instructions |
| user message | the `=== TECHNICAL SUMMARY ===` block, via `INPUT_BLOCKS` |
| **ICL examples** | both summary blocks (−5 059 chars) **and the two reasoning lines that cited them** |

**The ICL half was nearly missed and would have wrecked the arm.** The worked examples
contain the same input blocks the task does, and their reasoning cites the summary by
section — *"NO. Summary 5: no keys, entropy…"* and *"…will be a conceptual asset." Summary
section 5 says the same of this core…"*. Removing the summary from the task while leaving
those would have shown the model a procedure — consult the summary — it could not carry out,
and v01c4 already established how strongly the examples drive behaviour. That is a confound,
not an ablation. `icl_examples_01b_nosum` is derived from `_01b` by transformation with
round-trip asserts, so `_01B` stays byte-identical and v01c5 / v01c6 are untouched.

**The de-citations are deletions, not rewrites.** *"NO. Summary 5: no keys, entropy…"* →
*"NO. No keys, entropy…"*. The claim and its P3164 grounding survive verbatim; no reasoning
was authored. The v1 examples were rejected for being invented, and that line is not being
crossed here.

Pre-flight, all passing, no API calls spent:

- **0** occurrences of "summary" anywhere in the composed prompt (baseline has 9)
- user message loses exactly the summary block, confirmed by string equality
  (15 112 → 11 043 chars on `wdt`); parsed, signals, RTL and `function` all intact
- **input parity**: example blocks == task blocks == `{PARSED I/O PORTS, PARSED INTERNAL
  SIGNALS, RTL}`
- all **8** earlier versions re-hash byte-identical to their recorded run metadata
- P-1 still carries T-1's contract, A-02, A-03 (rule *and* example swap) and A-08's sweep
- evaluation path unchanged: `score`, `by_class`, `near_matches`, `diagnose_step1` all run

Expect:

1. **Precision moves little — I predict −0.02 to +0.03, and lean null.** The reason is
   evidence, not caution: unproductive and productive concepts are grounded in the summary at
   **0.513 vs 0.524** of their content words, permutation p = **0.33**. The summary does not
   differentiate the concepts that generate false positives from the ones that generate true
   ones, so removing it should hit both alike.
2. **GUARD — aggregate recall must not fall more than 0.03** from 0.881. A-01's group split
   showed summaries do not gate port recall: group B, whose summaries name *none* of their
   port assets, still went 0.355 → 0.645.
3. Emissions fall slightly or stay flat from 428.

Decision rule, fixed in advance:

- precision up **> 0.03** and the guard holds → a genuine surprise, and it would redirect the
  project: the SoC framing drives over-emission and stage 3 becomes the lever. Note before
  celebrating that regenerating summaries invalidates every prior arm (C-02).
- **null** → input volume at 11% does not matter. Proceed to **P-3** (31%), which is the
  bigger block and the more informative test. A null here is the expected outcome and is
  worth 90 calls precisely because it redirects effort rather than ending it.
- recall falls > 0.03 → the summary is load-bearing for recall after all, it stays, and the
  precision route is elsewhere entirely.

Got: —

#### P-2 · Drop the parsed closed set; let the model build it from the RTL
Version `v01c6p1p2`, sha **`70569027214e`** (69 908 chars = core 7 058 + ICL 62 848).
Baseline **`v01c6p1`**. Registered 2026-08-08, before running.

**Not a LAsset replication, and the log should not pretend otherwise.** Algorithm 1 line 5 is
`LLMASSET(S_m, Prm_m, R(m), ICL_ASSET)` and there is no published configuration without
`Prm_m` — the paper's Only-RTL variant drops `S_m` alone (that was P-1). So unlike P-1 there
is no reference number to check ourselves against. The question is ours: the parsed blocks are
**58.0% of every user message** (484 475 → 203 617 chars across the 18 modules) and stage 4
spends an LLM annotation call per module to build them. If the RTL alone serves, that stage is
overhead at line 5.

**Removed in all three places, one proposition:**

| where | change |
|---|---|
| core prompt | 3 hunks, −18 chars — the INPUTS (2)/(3) declaration folds into (4), and the two RULES bullets that named the JSON `"name"` / `"entity"` fields now name RTL declarations |
| user message | both `=== PARSED … (JSON) ===` blocks, via `INPUT_BLOCKS` |
| ICL examples | both blocks in both case studies (−31 251 chars, −1 479 lines) and the one phrase that assumed the set arrives ready-made ("the closed set **you are given**") |

**The reasoning in the examples is untouched, and that is the point.** Every "closed set"
sentence stays true because the core redefines the term rather than removing it. Contrast
P-1, where the reasoning cited the summary *by section* and could not survive its removal.
If the examples had needed re-reasoning here, the arm would be measuring authored text.

**One confound found and closed before running.** `validate_primary` checks every emitted name
against the parsed closed set, and the run loop regenerates once and keeps whichever attempt
has fewer issues. On every version that receives the parsed blocks that retry is inert —
`v01c6` and `v01c6p1` both sit at **0 ungrounded names across all 90 module-repeats**. Under
P-2 it would fire constantly, and it would be **selection on the closed set**: choosing the
sample that agrees better with exactly the information the prompt withholds. The measurement
would be of a two-sample filter, not of the model. So `RETRY_ON_VALIDATION` is derived from
`INPUT_BLOCKS` and this version **validates and reports but does not regenerate**.

**And the report is now persisted and structured**, because it stops being bookkeeping here.
`validate_primary` returns records rather than strings, and the run loop writes
`<run_dir>/_validation.json` per repeat (underscore-prefixed, so `load_run` skips it). An
ungrounded name has three quite different causes, and the old string form could not tell them
apart:

| evidence | cause | what it is evidence *about* |
|---|---|---|
| `in_rtl_base` **True** | the RTL declares it; `rtl_parse` did not list it | **our parser**, not the model |
| `in_rtl_base` False, `distance` ≤ 2 | variant spelling of a real element | model, recoverable |
| `in_rtl_base` False, `distance` large | invented | model, a true false positive |

Each record carries `name`, `entity_claimed`, `concept`, `objective`, `nearest`, `distance`
and the `in_rtl_full` / `in_rtl_base` flags. `eval_assets.validation_table()` aggregates across
repeats. The first column matters most: an element our regex missed would otherwise be scored
as a model error, and it feeds straight into the C-03 unreachable-reference thread.

Verified against the real notebook code, not a copy — the config and registry cells are
executed and their own `build_asset_user` / `validate_primary` called. The three causes were
separated on a live probe against `neorv32_wdt`: `ctrl_enable_c` (a VHDL constant the
architecture genuinely declares) → `in_rtl_base` True; `cnt_starte` → distance 1 from
`cnt_started`; `zzz_not_a_signal_anywhere` → distance 7.

Pre-flight, all passing, no API calls spent:

- **0** references to the parsed blocks anywhere in the composed prompt (baseline: 3 headers,
  209 `"function":`, 141 `"kind":`, 68 `"dir":`)
- user message loses exactly the two blocks, confirmed by string equality (11 043 → 4 943
  chars on `wdt`); RTL intact
- **input parity**: example blocks == task blocks == `{RTL}`
- the closed-set abstraction survives in all 7 places it is referenced
- all **9** earlier versions re-hash byte-identical to their recorded run metadata
- P-2 still carries A-02, A-03 (rule *and* example swap), T-1's contract, A-08's sweep, P-1
- evaluation path unchanged

Expect:

1. **Recall falls, and by how much is the finding.** I predict **−0.03 to −0.12** from 0.897.
   The paper's own stated reason for stage 4 is coverage — *"to ensure that LLMs do not
   overlook any of the parsed design elements… reducing the chance of false negatives"* — and
   A-08's sweep, worth +0.032, is an instruction to walk that list.
2. **Emissions fall, more than recall does.** 476 → I predict **260–360**. This is the first
   arm in the study with a mechanism for *fewer* emissions.
3. **Precision flat to slightly up, 0.00 to +0.05**, as the two effects partly cancel.
4. **A new column: the absent rate goes above zero for the first time** — 0.0% at every prior
   version. I predict **3–10%** of emissions naming something not in the parsed set. These are
   pure false positives and are the honest cost of removing the list.

Decision rule, fixed in advance:

- recall within **0.03** and emissions down → **the largest result in the family.** Stage 4's
  parsing is overhead at line 5, every future arm gets 58% cheaper, and the pipeline loses a
  whole LLM stage. Stage 4 is still needed for scoring and validation, which are ours, not the
  model's.
- recall falls **> 0.03** → the closed set is load-bearing. Then **P-2′ on `v01c6p1`** is the
  required follow-up: it separates "lost the names" from "lost the `function` annotations",
  and that answer decides whether enriching the annotations is worth any effort at all.
- precision up **> 0.05** while recall falls → a coverage/emission trade, worth plotting
  against the other arms but not a promotion.
- **Do not promote on F1.** The registered objective is recall (§1); F1 has pulled this study
  toward the wrong conclusion once already.

Got: **n=3, 2026-08-08.** Baseline `v01c6p1` at n=5.

| | emit | TP | FP | P | recall | sd | F1 | absent |
|---|---|---|---|---|---|---|---|---|
| v01c6p1 (n=5) | 476 | 99.6 | 376.0 | 0.210 | 0.897 | 0.013 | 0.340 | 0.0% |
| **v01c6p1p2 (n=3)** | **404** | 98.3 | 305.7 | **0.243** | 0.886 | 0.026 | 0.382 | 0.5% |

Per repeat: r0 recall 0.919 / emit 425, r1 0.856 / 394, r2 0.883 / 393.

Paired, modules as the pairing unit — **everything null**:

```
d(recall)       -0.020  [-0.086, +0.039]   5 better / 5 worse
d(precision)    +0.017  [-0.013, +0.050]   9 better / 6 worse
d(F1)           +0.021  [-0.011, +0.056]
d(signal-field) -0.049  [-0.128, +0.011]   the largest per-class move, still null
```

**Three of the four registered predictions were wrong.**

| # | predicted | got | |
|---|---|---|---|
| 1 | recall falls 0.03–0.12 | **−0.020** | wrong — it did not fall |
| 2 | emissions 260–360 | **404** | wrong — fell 15%, not 25–45% |
| 3 | precision 0.00 to +0.05 | **+0.017** | right |
| 4 | absent rate 3–10% | **0.5%** | wrong by 6–20× |

**The single most informative number in this arm is prediction 4 being wrong.** Across three
repeats the model produced **187 ungrounded names and invented none of them** — every one is a
real identifier declared in the RTL that `rtl_parse`'s regex did not list. Zero hallucinated
signals, zero near-miss spellings. Reading VHDL declarations was never the difficulty. Almost
all of them sit in `neorv32_package` (a package file with no entity, so its parsed closed set is
empty); on the 15 scored modules the absent rate is 0.5%.

**Two real costs, both established with matched-n comparisons rather than by eye.**

*The ceiling is genuinely lower.* Union over 3 repeats, compared against all ten 3-subsets of
the baseline: baseline **0.950** [0.946, 0.955], P-2 **0.937** — outside the range. The earlier
n=5-vs-n=3 union comparison was not admissible; more repeats always means a bigger union.

*Recall is about twice as variable.* Baseline sd(recall) over 3-repeat subsets: mean 0.0116,
range [0.0042, 0.0170]. P-2: **0.0258**, outside that range. The closed set was stabilising
which elements got named.

*But precision is more stable, not less* — sd(precision) **0.0042** vs the baseline's 0.0108.

**Verdict against the decision rule.** The promotion branch reads *"recall within 0.03 and
emissions down → stage 4's parsing is overhead at line 5"*. The point estimate meets it
(−0.020, emissions −15%). The interval does not exclude a −0.086 drop, and the ceiling fall is
real. So: **promote, with the ceiling recorded as the cost, not the mean.**

What this buys: **58.0% of every user message** removed (484 475 → 203 617 chars over 18
modules) and one LLM annotation call per module no longer needed at generation time. Stage 4
is still required for scoring, validation and per-class breakdown — those are ours, not the
model's.

**Consequence for the precision study.** `v01c6p1p2` is the better platform for it on two
counts beyond cost: precision is 2.5× more stable there, so smaller precision effects are
detectable at the same repeat count; and the lower recall ceiling is acceptable in a study
whose recall objective is a guard rather than a target. Recorded so the choice is not
re-litigated later on the ceiling number alone.

### L-1 · Remove evaluation-set identifiers from the prompt
Version `v01c6p1p2d`, sha **`cc3f0b397044`** (69 913 chars). Baseline **`v01c6p1p2`**.
Registered 2026-08-08 after a leak audit prompted by the user asking whether P-2's recall
could be explained by information leaking in somewhere.

**What was found.** The core quotes four literal design identifiers as naming examples, and
all four are real elements of the modules we evaluate on. One of them is an **answer**:

| identifier | ground truth in | declared in | entered at |
|---|---|---|---|
| **`ctrl_i`** | **10 of the 41 annotated modules** — cpu_alu, cpu_counters, cpu_cp_bitmanip, cpu_cp_cond, cpu_cp_crypto, cpu_cp_fpu, cpu_cp_shifter, cpu_lsu, cpu_pmp, cpu_regfile | cpu_cp_muldiv, cpu_pmp | A-03 |
| `ctrl_i.csr_wdata` | none | cpu_cp_muldiv, cpu_pmp | A-03 |
| `ctrl.buf_req` | none | cache | V0 |
| `rtx_engine.sreg` | none | spi | A-03 |

A-03's rule reads *"when it carries an asset, the asset is the port itself (`ctrl_i`)"* — it
states an answer, in the form of a naming rule.

**Size of it, stated honestly.** Within the 15 modules currently scored, `ctrl_i` is an answer
in `cpu_pmp` alone: **1 reference in 111, at most 0.009 of recall.** The other nine are in the
26 modules we have no RTL for — which is exactly the held-out set proposed as the first
generalisation test. **Small today, disqualifying for the measurement that matters most.**

**It is not a confound for P-1 or P-2.** The identifiers entered at A-03 (`v01c3`) and are
inherited by every later version, so they sit in the baseline and the arm alike and cancel in
every paired delta computed so far. What they threaten is the *absolute* recall figure quoted
against the paper, and any run on unseen modules. **P-2's result stands.**

**Why a new version rather than an edit in place.** Rewriting `_A03_RULE` would change the sha
of `v01c3`, `v01r`, `v01c4`, `v01c5`, `v01c6`, `v01c6p1` and `v01c6p1p2` — eight runs whose
recorded provenance would stop matching the code claiming to have produced them. The chain
records what was run. Verified: **10 versions with runs on disk, 0 shas changed.**

**Three edits, names only — the rule is untouched:**

| old | new |
|---|---|
| `(e.g. "ctrl.buf_req", "rtx_engine.sreg")` | `(e.g. "blk_ctrl.step", "xfer_unit.stage")` |
| `the port itself ("ctrl_i"), never one of its fields ("ctrl_i.csr_wdata")` | `… ("cfg_port_i") … ("cfg_port_i.mode")` |
| `there the field is the asset ("ctrl.buf_req"), as above` | `… ("blk_ctrl.step"), as above` |

+5 chars. Replacements checked absent from all **1 355** parsed element names and all **218**
ground-truth names across the 41 annotated modules, base identifier as well as dotted form.

**`clk_i` and `rstn_i` are deliberately kept.** They appear as *"Global clock/reset ports (e.g.
clk_i, rstn_i) … are NOT assets"*. Neither is ground truth in **any** of the 41 modules, so
neither states an answer; both are universal VHDL naming convention rather than anything
specific to this design; and they serve a rule that is correct. Removing them would make a
legitimate instruction vaguer and buy nothing. Recorded as a decision so it is not re-litigated.

**The ICL block is clean** — 0 of its quoted identifiers are NEORV32 elements or answers. Its
case studies are `omsp_gpio` and `tiny_aes`, neither of which is in the evaluation set.

Expect:

1. **Everything null.** Recall falls by at most **0.009** (the single `cpu_pmp` reference).
   Precision, emissions and per-class recall unchanged.
2. If recall falls **more than 0.02**, the identifiers were doing more work than their token
   count suggests — the model was pattern-matching on them beyond the one answer, and that
   would retroactively weaken every absolute figure in §4.
3. If recall *rises*, the names were noise, and the honest reading is that the four examples
   were pulling emissions toward `ctrl*` in modules where that was wrong.

Decision rule: null → **`v01c6p1p2d` becomes the baseline for every subsequent arm**, and the
held-out test runs on it. Not null → the leak is a finding in its own right and §4's absolute
numbers get a footnote.

**Standing rule added to §6:** no literal identifier from any of the 41 annotated modules may
enter a prompt again. The check is `identifier_audit.py`; run it before registering any arm
that adds an example.

Got: —

#### P-2′ · Strip the `function` field from the closed set
Not yet built. Keeps every name, drops stage 4's LLM annotation. One core edit needed (the
INPUTS line enumerates `function` among the JSON fields).

Expect: **recall falls** — `function` is how the model learns what an element does without
inferring it from RTL — but by how much is the point. Precision direction genuinely unknown.
If recall barely moves, the annotation stage is decorative and the effort to enrich it would
be wasted; if it falls hard, enriching it is the highest-value stage-4 work available.

Got: —

#### P-3 · Drop the RTL body
Not yet built. **Trap to avoid:** a naive `"RTL"` replacement corrupts the output-contract
field name `"Asset RTL"` and P3164's *"the RTL that PRODUCES a conceptual asset"*. Only the
four input-references may be touched — the same four spots as P-1, mirrored.

Expect: **recall falls most of the three**, since the prompt calls RTL "ground truth for what
each element does". But the model also receives `function` fields and the summary, so some
redundancy is likely. **If this is near-null it is the largest finding of the family:** 31% of
every call's input, bought for nothing, and every future arm gets a third cheaper.

Got: —

### A-04 · Stop expanding port records at stage 4 — superseded
**Not run, and now largely pointless.** Recorded here because it existed only as a Notion
row until 2026-08-07, when that row was overwritten by mistake while registering A-08. The
substance below is reconstructed; the row is gone.

Alternative fix for the *same* defect as A-03, at stage 4 instead of stage 5: drop
port-record *fields* from the closed set during parsing rather than instructing the model not
to name them. **959 of 1572 candidates are port-record fields and not one is ever a labelled
asset.** Never run in the same arm as A-03 — they attack the same thing from opposite ends.

The trade-off, as originally framed: dropping them at stage 4 removes 61% of the distractors
outright but hard-codes a rule the model cannot override; A-03 keeps them reachable but works
only as well as the model follows instructions. *Which stage you fix at is itself the
experiment.*

**Superseded by A-03's result.** Instruction alone achieved ~98% compliance — port-field
emissions fell 73.7 → 1.7 per repeat on the V2 core and 51.3 → 1.0 on the V0 core. Port-field
FPs are down to 2/repeat, so there is almost nothing left for a stage-4 filter to remove. The
question this arm was designed to settle has been answered in favour of stage 5, cheaply.

A-03 also showed the fix is a **rename, not a deletion**: port-field FPs went 73 → 2 while
whole-port FPs went 19 → 55. Removing the fields at stage 4 would not have avoided that — the
model reaches for the bus bundle either way, and deleting its fields just forces the same
emission at the record level.

If ever run: re-baseline to the standing baseline and expect near-zero movement. The
higher-value stage-4 target is the *bundle*, not its fields — of 116 record-typed ports
across the 15 modules exactly **one** (`cpu_pmp.ctrl_i`) is in `gt`. That would attack ~31
FPs/repeat, but note it is only 16% of the FP mass; the dominant block is signal-field
over-emission at 92/repeat against the paper's 19.

### A-08 · Per-concept closure sweep
**Next arm.** Version `v01c6`, prompt sha `9d9cf29aae23` (106 487 chars). Baseline
**`v01c5`**. `ASSET_PRIMARY_CORE_V5` = `_V4` plus one insertion immediately before `RULES:`
and nothing else — built by substitution with a round-trip assert. ICL held at `_01B`.
Diff: **1 hunk, 0 lines removed, 4 added, +550 chars.**

**Why this and not something else.** T-1 measured the split: **82.1% of misses are binding
failures** — a concept covering the missed element was already in the model's own list and
the element was in the closed set. Conception failures are 17.9%, and *all* of the strong
ones are Availability (that is A-09, run separately).

**Why a verification pass and not more fan-out instruction.** The shape of the binding
failure is specific: where a covering concept existed it had typically already bound 5–6
elements (22% had 5, 19% had 6, running to 12); only 2.8% had bound just one. **The model
fans out — 3.63 elements per concept — and stops one short.** So it is a *completeness*
problem, not a fan-out problem.

The prompt already says *"may fan out to SEVERAL elements — emit one object per element"*,
says it again in the V2 insertion, and adds the two-question procedure — and the model
complies with all of it. A-01 and A-02 both established that repeating an instruction the
model already follows buys nothing. So the insertion is a **check on a list already
written**, with an explicit stopping criterion, which is the one thing the current text
never states. No count, proportion or threshold appears (A-03's standing constraint).

Expect:

1. **PRIMARY — the union must move.** `union-5` recall has been **0.928** for v01c3, v01c4
   and v01c5 alike while the mean climbed 0.784 → 0.845 → 0.849. If this arm only tightens
   variance the union stays at 0.928 and it has not done what it was designed to do.
   Registering: **union-5 > 0.928**, i.e. at least one reference recovered that no v01c5
   repeat ever found.
2. **Aggregate recall rises +0.02 to +0.06** from 0.849. The (b) block is 13.8/repeat
   (0.124 of the reference); a third of it recovered is +0.04. Full recovery is not
   expected — A-02 showed a search-style directive recovers partially, and only A-03's
   *constraint* achieved near-total compliance.
3. **Precision falls, 0.02 to 0.04**, from 0.285. This arm's entire mechanism is more
   emissions.
4. **GUARD — the (a) fraction is unchanged.** The insertion is in STEP 2 and does not touch
   STEP 1's rubric. If the conception split moves, something unintended happened and the
   arm is not measuring what it claims.

Decision rule, fixed in advance:

- union-5 rises **and** recall rises → keep; `v01c6` becomes the baseline. First movement in
  a ceiling stuck across three versions.
- recall rises **but union-5 stays 0.928** → the arm bought variance reduction, not
  capability. **Do not promote on the mean.** Record it as a null for its stated purpose;
  the headroom is nearly exhausted (0.079) so this route stops paying shortly anyway.
- recall flat → a verification pass cannot be induced by prompt text here. That is itself a
  finding, and it makes the pipeline version (a second additive pass over the model's own
  output) the only remaining route — which leaves the lines 3–5 scope and must be declared
  as a deviation, not folded in.
- precision falls more than 0.05 → note it prominently. Precision is the next phase's
  target, and a drop that large changes what that phase has to recover.

**Registered risk.** *"Add every one that does"* can read as *"add more"*, and this arm's
mechanism is more emissions. Watch FP-by-class as well as the total: an increase concentrated
in signal-field (already 92/repeat against the paper's 19) means the sweep is spraying rather
than closing.

Got: **the ceiling moved — the first time in this study.** `v01c6`, n=5, sha `9d9cf29aae23`.

| | v01c5 | v01c6 | registered |
|---|---|---|---|
| **union-5 recall** | **0.928** | **0.955** | **>0.928 — PASS** |
| union-5 TP | 103 | **106** | |
| mean recall | 0.849 | 0.881 | +0.02…+0.06 — PASS (+0.027) |
| precision | 0.285 | 0.229 | −0.02…−0.04 — see below |
| F1 | 0.426 | 0.364 | not registered |
| assets per concept | 3.63 | **4.62** | mechanism check |

Paired vs `v01c5`, one variable:

| | Δ | 95% CI | |
|---|---|---|---|
| **recall** | **+0.027** | **[+0.009, +0.046]** | 8 better / 1 worse |
| **precision** | **−0.038** | **[−0.057, −0.021]** | 2 better / 13 worse |
| **F1** | **−0.041** | **[−0.060, −0.023]** | 2 better / 13 worse |
| port recall | +0.023 | [−0.015, +0.067] | null |
| signal recall | +0.020 | [+0.000, +0.049] | null |
| signal-field recall | +0.044 | [+0.000, +0.089] | null |

**Expect 1, the primary, passes.** `union-5` had been **0.928 for v01c3, v01c4 and v01c5
alike** — 103 true positives, three prompts, no movement. It is now **0.955 / 106**. Three
references were recovered that *no repeat of any earlier version ever found*:
`bus.stb`, `cpu.alu_add`, `cpu.alu_res`. The never-found set drops 8 → 5.

This is the distinction the arm was registered on. Everything since A-03 had bought
consistency — the mean rising toward a fixed ceiling. This raised the ceiling.

**Expects 2 and 3 pass**, recall at the low end of the band (+0.027 against +0.02…+0.06) and
precision at the high end (−0.038 against −0.02…−0.04). The mechanism check confirms what
moved: **assets per concept 3.63 → 4.62** while concepts per module barely changed
(6.2 → 6.4). The sweep made concepts more complete rather than making more of them, which is
exactly what it was built to do.

**Expect 4, the guard, is mildly violated.** The deterministic (a) fraction moved
14.3% → 12.1%, absolute count 2.4 → 1.6 per repeat. The insertion is in STEP 2 and should not
have touched conception. It is a small movement on small counts and I have no interval for
it, so I cannot separate it from noise — but the honest reading is that the sweep is *not*
purely a STEP 2 intervention. Sweeping the closed set per concept plausibly surfaces elements
that suggest a further concept. Recorded as a deviation, not a failure.

**The registered risk did not materialise as predicted, and something else did.** The FP rise
is *not* concentrated in signal-field — it is broad:

| | port | signal | signal-field | port-field |
|---|---|---|---|---|
| v01c5 | 69.2 | 52.4 | 113.2 | 2.2 |
| **v01c6** | **101.2** | **68.2** | **151.6** | **9.2** |
| *paper* | *6.0* | *7.0* | *19.0* | *0.0* |

Proportionally port rose most (+46%) and signal-field least of the three main classes (+34%).
But **port-field went 2.2 → 9.2**, partially undoing A-03's result, which had driven it from
73 to 2. That was not predicted and should be watched if A-08 is carried forward.

**An ambiguity in my own registration.** The stop clause said "precision falls more than
0.05". The *paired* delta is −0.038 (under); the raw mean drop is 0.285 → 0.229 = 0.056
(over). The paired figure is this study's standard and is the one I am reading, but the
threshold should have named which. F1 is now 0.364, the lowest since v01.

**Decision: the rule fires — `v01c6` becomes the baseline.** Registered: *"union-5 rises and
recall rises → keep"*. Both did, and the union movement is the thing three previous arms
could not produce. The precision cost is real and is now the next phase's problem: 0.229
against the paper's 0.737, with 330 FPs against 36.

### T-1 addendum — the judge has run-to-run variance
A second run of the diagnostic on the *same* v01c5 data returned **(b) 84.5%** against the
first run's 82.1%; the judge-based (a) moved 3.6% → 1.2%. The **deterministic** component was
identical at 14.3% both times. So the split carries roughly ±2.5 points of judge
nondeterminism and should be quoted as **(b) ≈ 82–85%**, not as 82.1%. This is on top of, not
instead of, the unbounded-permissiveness threat above.

### Baseline promotions

The standing baseline a new arm is measured against. Promoting one **never invalidates an
earlier arm** — each was a paired comparison against its own baseline at the time, and that
comparison does not change later.

| date | baseline | what moved to get here | one variable? |
|---|---|---|---|
| 2026-08-03 | `v0` | — (root) | — |
| 2026-08-03 | `v01` | ICL block (A-01) | yes |
| 2026-08-04 | `v01c2` | core, role-not-location (A-02) | yes |
| 2026-08-06 | `v01c3` | core, port granularity (A-03) | yes |
| 2026-08-07 | `v01c5` | via `v01c4`: core exposes STEP 1 (T-1), then ICL shows concepts | yes, each hop |
| **2026-08-07** | **`v01c6`** | core, per-concept closure sweep (A-08) | yes |

`v01c6` was promoted by A-08's own pre-registered rule — *union-5 rises **and** recall
rises* — and it is the only arm so far to move the ceiling (0.928 → 0.955). The promotion
was recorded in A-08's `Got:` block on the day but **not propagated** to
`CURRENT_BASELINE`, to `VERSIONS`, or to this table until 2026-08-07. The live consequence:
`v01c6p1` had no explicit `BASELINE` entry, so the fallback would have paired it against
`v01c5` — turning a one-proposition arm into a two-proposition contrast (A-08's sweep plus
the summary removal). Caught before P-1 was run. **A decision recorded in prose is not a
decision applied; propagate a promotion in the same edit that records it.**

**The chain is intact.** An earlier draft of this file claimed `v01c3 → v01c5` was
"permanently unattributable" because it moves two things. It does — which is why you never
run that comparison. `v01c3 → v01c4` moves only the core and `v01c4 → v01c5` moves only the
ICL, so the chain is two clean single-variable hops and nothing is lost.

`v01c4 → v01c5` is **null on every metric** — recall +0.004 [−0.024, +0.033], precision
+0.009 [−0.006, +0.024], F1 +0.011 [−0.006, +0.029]. `icl_examples_01b` was built to fix the
ICL hypothesis from T-1, that hypothesis turned out to be wrong (the blocker was
`generate_assets`), and the edit bought nothing. Kept because it is harmless and because
v01c5 is the version the diagnostic was validated on; dropping back to v01c4 would mean
re-validating for no gain.

Why `v01c5` rather than `v01c3`: recall 0.849 vs 0.784, and sd 0.015 — the lowest of any arm.

**Footnote on `v01c3 → v01c4`.** It changed the output *contract*, not just wording. Asking
a model to write out reasoning it previously kept internal can alter the reasoning itself, so
that hop generalises less far than a pure wording change. This log earlier registered "its
recall delta will not be reported as a result", which was stricter than this study's own
standard — A-02's insertion bundled four paragraphs and A-03 bundled two edits, and both were
accepted as single arms. The measurement is clean; the interpretation carries this footnote.

Mechanically: `CURRENT_BASELINE` in the config cell, plus an entry in `BASELINE` in the
ablation cell. Anything in `VERSIONS` without an explicit entry now defaults to
`CURRENT_BASELINE`, so a new arm can never fall through to a multi-variable contrast against
`VERSIONS[0]`. Explicit entries always win, so promotion cannot silently re-point an old arm.

## 4. Results

All **M-2** unless stated. Scored against `gt` on the 15 modules common to every run
(ref = 111 elements). `n` = repeats. Paste from `ablate()`; never retype a number.

**Two of the 111 references cannot exist in our RTL revision (C-03), both in
`neorv32_cache`.** Aggregate recall therefore tops out at **0.982**, and `cache`'s own
per-module ceiling is **0.667**. Read that module's row against 0.667.

| arm | version | n | emit | TP | FP | FN | P | recall | sd | F1 | sd |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A-00 | v0 | 3 | 205 | 61 | 143 | 50 | 0.300 | 0.553 | 0.019 | 0.389 | 0.010 |
| A-01 | v01 | 3 | 235 | 67 | 167 | 44 | 0.288 | 0.607 | 0.005 | 0.390 | 0.015 |
| **A-02** | **v01c2** | 3 | 304 | 87 | 217 | 24 | 0.286 | **0.784** | 0.039 | 0.419 | 0.020 |
| **A-03** | **v01c3** | 3 | 279 | 88 | 191 | 23 | **0.315** | **0.793** | 0.053 | **0.451** | 0.021 |
| A-03 ctl | v01r | 2 | 210 | 70 | 141 | 42 | 0.331 | 0.626 | — | 0.433 | — |
| *T-1 diag* | *v01c4* | 5 | 352 | 94 | 258 | 17 | 0.267 | 0.845 | 0.022 | 0.406 | — |
| *T-1 diag* | *v01c5* | 5 | 331 | 94 | 237 | 17 | 0.285 | 0.849 | 0.015 | 0.426 | — |
| **A-08** | **v01c6** | 5 | 428 | 98 | 330 | 13 | 0.229 | **0.881** | 0.018 | 0.364 | — |
| — | *LAsset paper* | 1 | 137 | 101 | 36 | 10 | 0.737 | 0.910 | | 0.815 | |

`v01r` is the A-03 control on the V0 core, **directional only** — n=2 supports no sd.

**Recall by element class is the PRIMARY metric here, not aggregate recall.** A-01 is the
proof: aggregate recall read +0.049 [−0.061, +0.166], an honest null, while port recall rose
+0.181 [+0.048, +0.302] and signal recall fell −0.157 [−0.229, −0.086] — *both clearing
zero* and cancelling. The aggregate was not wrong, it was uninformative. With 15 modules the
aggregate CI runs ±0.14 and will keep failing to resolve real effects, so report the classes.

| | port | signal | signal-field |
|---|---|---|---|
| reference size | 47 | 32 | 31 |
| v0 | 0.326 | 0.771 | 0.688 |
| v01 | 0.589 | 0.573 | 0.688 |
| v01c2 | 0.851 | 0.677 | 0.817 |
| **v01c3** | **0.801** | **0.750** | **0.849** |
| v01r *(ctl)* | 0.617 | 0.562 | 0.726 |
| *v01c4 (diag)* | *0.906* | *0.781* | *0.845* |
| *v01c5 (diag)* | *0.906* | *0.769* | *0.871* |
| **v01c6** | **0.919** | **0.812** | **0.923** |
| *LAsset paper* | *0.894* | *0.906* | *0.935* |

False positives by class:

| | port | signal | signal-field | port-field |
|---|---|---|---|---|
| v0 | 7 | 43 | 74 | 19 |
| v01 | 14 | 39 | 64 | 51 |
| v01c2 | 19 | 41 | 83 | 73 |
| **v01c3** | **55** | 42 | **92** | **2** |
| *paper* | *6* | *7* | *19* | *0* |

A-03 did not delete 71 false positives, it **moved about half of them**: port-field 73 → 2,
whole-port 19 → 55. Excess over the paper on `v01c3` is now **signal-field +73**, port +49,
signal +35, port-field +2.

After A-02 the bottleneck has flipped. Port recall is 0.851 against the paper's 0.894 and
six modules are saturated at 1.000; the remaining gap to the paper is now almost entirely
**precision** — 0.286 against 0.737, 217 FPs against 36. Excess FPs over the paper by class:
port-field 73, signal-field 64, signal 34, port 13. Of the 24 remaining FNs, twelve are
missed by all three repeats, and one of those — `cache.inval_i` — is class `absent`: it is
not in the parsed closed set at all (C-03 revision skew) and is unreachable by any prompt.

v0 missed two thirds of the ports it should find while 82% of what it invented was internal
signal state — cataloguing implementation, ignoring the interface. Confirmed per-module: a
module's ground-truth port share predicted its recall (Spearman −0.611, CI [−0.864, −0.136]).
v01 fixed that and broke the other half.

Note the class means above are pooled across all elements (micro), while the paired deltas
are means of per-module recall (macro). Both are correct; they differ because modules carry
unequal numbers of each class. The paired figures are the ones with intervals.

Paired deltas, modules as the pairing unit, 95% bootstrap CI:

| comparison | metric | Δ | 95% CI |
|---|---|---|---|
| v01 − v0 | **port recall** | **+0.181** | **[+0.048, +0.302]** |
| v01 − v0 | **signal recall** | **−0.157** | **[−0.229, −0.086]** |
| v01 − v0 | signal-field recall | +0.008 | [−0.074, +0.123] |
| v01 − v0 | aggregate recall | +0.049 | [−0.061, +0.166] |
| v01 − v0 | F1 | −0.020 | [−0.094, +0.059] |
| **v01c2 − v01** | **port recall** | **+0.262** | **[+0.110, +0.414]** |
| **v01c2 − v01** | **signal recall** | **+0.106** | **[+0.047, +0.165]** |
| v01c2 − v01 | signal-field recall | +0.094 | [−0.017, +0.205] |
| **v01c2 − v01** | **aggregate recall** | **+0.162** | **[+0.083, +0.232]** |
| v01c2 − v01 | precision | −0.001 | [−0.035, +0.030] |
| v01c2 − v01 | F1 | +0.029 | [−0.017, +0.071] |
| **v01c3 − v01c2** | **precision** | **+0.042** | **[+0.005, +0.077]** |
| **v01c3 − v01c2** | **F1** | **+0.046** | **[+0.002, +0.087]** |
| v01c3 − v01c2 | port recall | −0.037 | [−0.194, +0.116] |
| v01c3 − v01c2 | aggregate recall | +0.008 | [−0.074, +0.089] |
| *v01r − v01 (ctl, n=2)* | *precision* | *+0.060* | *[+0.024, +0.099]* |
| *v01r − v01 (ctl, n=2)* | *port recall* | *+0.048* | *[−0.068, +0.150]* |

### Where the remaining error actually is — after A-03

**Recall side.** Only **9** of 111 references are missed by every `v01c3` repeat, down from 12
under `v01c2`. Six have never been produced by any version in any repeat:

| module | element | class |
|---|---|---|
| `cache` | `cache_o.cmd_dir` | signal-field |
| `cache` | `inval_i` | **absent** — not in the closed set (C-03 skew), unreachable |
| `cpu` | `alu_res` | signal |
| `cpu` | `lsu_err` | signal |
| `cpu` | `lsu_wait` | signal |
| `trng` | `fifo.free` | signal-field |

So the true blind spot is **5 reachable elements**, four of them internal state inside the two
largest multi-entity files.

The other 23 misses are not blind spots. **28 references are found in some repeats and not
others** — 73 found 3/3, 14 found 2/3, 14 found 1/3, 10 found 0/3. Scoring a merged run (all
three repeats concatenated, deduped by `(entity, name)`, same scorer so `_name_caps` and index
matching still apply):

| | mean recall | union of 3 repeats | gain | union precision |
|---|---|---|---|---|
| v0 | 0.553 | 0.685 | +0.132 | 0.270 |
| v01 | 0.607 | 0.748 | +0.141 | 0.265 |
| v01c2 | 0.784 | 0.892 | +0.108 | 0.253 |
| **v01c3** | **0.793** | **0.919** | **+0.126** | 0.293 |
| *paper* | *0.910* | | | *0.737* |

**`v01c3`'s union recall exceeds the paper's single-run recall.** The remaining recall gap is
mostly *consistency*, not capability — the model already finds 92% of the references, just
not the same 92% each time. That gap (+0.126) is larger than the whole A-03 effect and
comparable to A-02's, and no prompt edit addresses it; self-consistency over k samples does,
at k× the cost and some precision loss. It is the largest single recall lever left.

**Precision side — a correction.** This log previously framed the residual as "inherited SoC
bus interface treated as an asset at all… ~33 of the 34 records". The direction is right and
the scale was wrong, and the error came from carrying the A-03 *oracle's* framing past its
scope: 34 was the count of records the port-field FPs collapsed into, which sized A-03
correctly but does not describe the remaining FP population.

Measured on `v01c3`: record-typed port bundles are **31 of 191 FPs per repeat — 16%**. The
other 84% is signal-field 92.3, signal 42.3, non-bundle port 25.3.

What *is* true, and is worth keeping: of the **116 record-typed ports** in the closed set
across the 15 modules, exactly **one** (`cpu_pmp.ctrl_i`) appears in `gt` — 1%. The model
still emits about 14 distinct bundles per repeat, led by `bus_req_i` 7.0 and `bus_rsp_o` 5.7.
So bus plumbing is a clean, cheaply-characterised error class; it is simply not the biggest
one. **The dominant remaining FP block is signal-field over-emission: 92.3 per repeat against
the paper's 19.**

`v01c2 − v01` is the A-02 arm: one variable, verified byte-level. **Do not read the
`v01c2 − v0` rows that `ablate()` prints** — the notebook cell pairs every version against
the first in `VERSIONS`, and against v0 that comparison moves the core prompt *and* the ICL
block at once. It is a two-variable contrast and is not an arm.

---

## 5. Metric

A result is comparable only to another under the same `M-n`. If this list grows, restamp or
re-run; old numbers do not become wrong, they become unlabelled, which is worse.

### M-1 — 2026-08-02, superseded
Match is exact, or the one legitimate near-match where the reference names a whole record
and the prediction names one of its fields, or the reverse. Field-to-field matching is
refused — crediting a predicted `fifo.avail` against a ground-truth `fifo.re` rewards
spraying record fields. Module sets are intersected across all runs before scoring, so an
arm that failed a module cannot report totals over a different denominator.

TP / FP / FN with precision, recall, F1. No TN or FPR: the negative class outnumbers the
positives ~14:1, so FPR reads ~0.1 while precision is ~0.3.

### Near-match audit — 2026-08-07, no metric change

`_hit_idx` allows two near-matches beyond exact equality, and both let a prediction score at
a different granularity than the reference asked for:

| | reference | prediction |
|---|---|---|
| A record → field | `ctrl` | `ctrl.enable` |
| B field → record | `ctrl.enable` | `ctrl` |

B is the weaker — naming the whole record is a coarser claim than naming the field the
reference singled out, and `cache_o` is genuinely not the same element as `cache_o.cmd_dir`.
Both exist because the reference set is itself inconsistent about granularity (32
whole-signal references against 31 signal-field ones), so M-1 hedged.

**Audited rather than argued.** Near-matches are 2.7% of TPs at v0 and **0.4% at v01c6**, and
they shrink as the prompt improves. Absolute recall is inflated by 0.015 at v0 and **0.004 at
v01c6**. Every version-to-version *gain* survives exact-only matching:

| step | reported | exact-only |
|---|---|---|
| v0 → v01 | +0.054 | +0.057 |
| v01 → v01c2 | +0.138 | +0.139 |
| v01c2 → v01c3 | +0.040 | +0.049 |
| v01c3 → v01c5 | +0.065 | +0.063 |
| **v01c5 → v01c6 (A-08)** | **+0.032** | **+0.032** |

No conclusion in this file depends on the leniency. **The metric is unchanged** — dropping B
would move recall by 0.004, leave every comparison intact, and cost a full M-3 restamp.

**Made visible instead.** `ablate()` now prints a `near` column (`eval_assets.near_matches`),
so no future arm can rest on it invisibly; before this the only way to see it was a bespoke
script.

The failure mode that *would* matter is ruled out: predictions are consumed **by index**, so
one bare `ctrl` can satisfy exactly one dotted reference, never `ctrl.enable` and `ctrl.lock`
and `ctrl.timeout` together.

### M-2 — current, from 2026-08-03
Everything in M-1, plus: **same-name elements are no longer collapsed on either side.**

M-1 held both the reference and each run in a dict keyed by element name, so two assets
sharing a name in different entities of one file overwrote each other. Two consequences,
both silent:

- `neorv32_bus` ground truth reads `state/state` — the arbiter FSM in `neorv32_bus_switch`
  and the reservation FSM in `neorv32_bus_amo_rvs`. It was extracted as one element. **This
  single collapse was the entire reason the extraction totalled 301 against the paper's
  stated 302.** That discrepancy is now closed.
- Runs r1 and r2 correctly emitted *both* `state` assets and were credited for one. The
  model was scored below what it actually produced.

Reference multiplicity is capped by how many entities actually declare the name
(`_name_caps`). Without the cap, `neorv32_twi`'s `twi_sda_i` — listed in two separate
annotation rows but declared by only one entity — would become permanently unreachable and
depress recall for good. So 302 annotated rows score as 300 distinct elements across the
41 modules; 111 on our 15.

Effect on A-00: recall 0.552 → 0.553, F1 0.386 → 0.389, sd 0.014 → 0.019. Small, but the
generated assets were re-scored, not re-run, so the correction was free.

Also added in M-2: per-class recall (port / signal / signal-field) prints for every arm,
because the aggregate hid the actual failure mode completely.

### M-2 addendum — what the `paper` comparator row actually contains, 2026-08-08
Prompted by a re-read of the paper's §III-B against its published artifacts. Nothing here
changes a number; it changes what the numbers may be *said to mean*.

**LAsset's Asset Generation is two steps, not one.** Algorithm 1 comments lines 5–6 together
as "Assets generation", and §III-B spells them out: line 5 binds each conceptual asset to its
structural RTL reference — *"these are the primary assets"* — and then *"for each primary
asset, we find the internal signals/registers that influence/violate its security
objective(s) — these are termed as the secondary assets"* (line 6, `SECASSET`). Figure 4 shows
both as separate outputs of the same agent.

So `asset_list_neorv32_initial.json` holds **both**, in one record:

```
Asset Name        "Machine Software Interrupt Input"    <- conceptual
Asset RTL         "msi_i"                               <- structural, PRIMARY   (line 5)
Secondary Assets  ["irq_machine", "ctrl"]               <- line 6
```

On our 15 modules that is **137 primaries** and **726 secondary mentions** (283 distinct
names). `load_refs` reads only `element`, so the `paper` row has always been **primaries
only** — 137 emissions, P 0.737, R 0.910.

**That is the correct comparator, and it is now verified rather than assumed.** Our manual
ground truth matches the paper's Table I golden counts exactly on every NEORV32 module they
report — CPU 14, PMP 6, Debug Transport 5, TRNG 7, UART 10 — so both are primary-asset lists
and both score line 5's job. Recorded because it was checked, not because it changed.

**What does change: roughly half our false positives are things LAsset itself names.** Scoring
our emissions against LAsset's secondary vocabulary for the same module:

| version | emit | FP | FP that LAsset calls *secondary* | genuinely unaccounted | junk rate |
|---|---|---|---|---|---|
| v0 | 205 | 145 | 91 (62.9%) | 54 | 26.2% |
| v01c3 | 274 | 187 | 105 (55.9%) | 82 | 30.1% |
| v01c6 | 428 | 331 | 175 (52.9%) | 156 | 36.4% |
| v01c6p1 | 476 | 376 | 194 (51.6%) | 182 | 38.2% |

Two readings, both worth holding:

- The *share* has been flat near half since v0, so **no arm caused this** — it is structural.
  Our single call does lines 5 and 6 at once while the reference credits only line 5.
- The *absolute* unaccounted count went 54 → 182, and as a fraction of emissions 26% → 38%.
  That growth is the real cost of the recall arms, and it is the honest size of the precision
  problem: closer to 156 bad guesses at `v01c6` than to 331.

**Not acted on yet, by decision:** secondary assets are out of scope until primary precision
and emission are addressed. No metric, reference or table is changed by this note.

---

## 6. Open threats

Delete a line when it stops being true.

- **Only large effects are detectable.** The paired CI runs about ±0.14 because there are 15
  modules. Anything under ~0.10 paired recall will read as inconclusive. More repeats will
  not help; more modules would.
- **Tuning set sits inside the reporting set.** The 18 modules are a subset of the paper's
  41. Selecting prompts on 15 of them and later reporting on 41 contaminates 15. Plan: report
  the final number split into tuned-on and unseen.
- **Three NEORV32 revisions in play.** `RTL_data` v1.11.4.3, `neorv32/rtl/core` v1.11.0.6,
  datasheet v1.11.2. Measured impact so far is one element (C-03).
- **v01 vs v02 is confounded** — IP and label provenance move together (A-01).
- **`v01c2` can merge the `Asset RTL` and `Entity` fields.** Four emissions in one repeat
  came back as `neorv32_cache_memory.clr_i` and kin; the validator caught them and one
  regeneration did not. 4/729 in v01c2, 0/670 in v0, 0/766 in v01. It costs FPs, so it
  biases *against* whichever arm carries it — but if `v01c2` is carried forward, a V3 should
  address it as its own change rather than folding it into another arm.
- ~~**THE CEILING HAS NOT MOVED IN THREE PROMPT VERSIONS.**~~ **CLOSED by A-08,
  2026-08-07.** union-5 sat at **0.928** for v01c3, v01c4 and v01c5 — three prompts, 103 TP,
  no movement — while the mean climbed 0.784 -> 0.845 -> 0.849 on shrinking headroom. A-08
  moved it to **0.955 / 106 TP**, recovering `bus.stb`, `cpu.alu_add` and `cpu.alu_res`,
  which no repeat of any earlier version had ever produced. The standing rule survives and
  is now demonstrated rather than asserted: **an arm claiming a recall gain must show the
  UNION moving**, or it is buying variance reduction against a fixed ceiling. Headroom is
  now 0.074 and still shrinking.
- **PRECISION IS NOW THE BINDING PROBLEM.** 0.229 against the paper's 0.737; 330 FPs against
  36. A-08 bought its recall with 97 extra emissions per repeat, and port-field FPs went
  2.2 -> 9.2, partially undoing A-03. Every further recall arm makes this worse.
- **The T-1 judge's permissiveness is unbounded** — see the T-1 open threat. 82.1% (b) is an
  upper bound until the mismatched-module negative control is run (~40 calls).
- **`ablate()` pairs every version against the first in `VERSIONS`.** For any version whose
  designated baseline is not v0, the printed paired block is not that version's arm. Read
  `paired_classes(RUNS, <its baseline>, <version>, ...)` explicitly instead.

---

## 7. Rejected hypotheses and misreadings

Kept so they are not re-derived. A wrong idea that cost a day is worth three lines.

### R-01 · Emit variance does not predict recall — 2026-08-03
Six modules looked high-variance across the three A-00 repeats (`bus`, `cache`, `spi`,
`trng`, `uart`, `wdt`) and four had recall below 0.5 (`bus`, `cache`, `cpu`, `cpu_cp_cfu`),
suggesting unstable modules were the weak ones.

Tested: Spearman **−0.261, CI [−0.614, +0.296]**. No relationship. Two counterexamples from
the lists themselves: `cpu` has the third *lowest* CV (0.086 — it emits 16/19/18, steadily
wrong) and `wdt` has the second *highest* recall (0.917). The two lists were built by
different eyeball criteria and their overlap is chance.

Method notes for next time: compare coefficient of variation, not raw ranges — a module
emitting 25 swings more in absolute terms than one emitting 3, so a "high variance" list
built on ranges is partly just a "high emit count" list. And picking 6 modules by eye, then
4 by eye, and reading the overlap as signal will produce a pattern at n=15 more often than
not. Also tested and null: emit CV vs closed-set size (+0.421), emit CV vs mean emit
(+0.318), closed-set size vs recall (−0.343), GT size vs recall (−0.386) — every CI spans
zero.

What *is* real: GT port share vs recall, **−0.611, CI [−0.864, −0.136]**. But note this is
a consistency check on the class-level finding rather than independent evidence — if ports
are found at 33% and everything else at ~73%, that correlation follows arithmetically. Its
value is showing the effect is uniform across modules rather than driven by one or two.

### R-02 · `rvso` is not a missed asset — 2026-08-03
`asset_list_neorv32_initial.json` lists `rvso` as a primary asset of `neorv32_bus_amo_rvs`,
and it never appears in our FN lists — which looked like an evaluation bug.

It is not. That file is LAsset's **line-5 output**, not the reference: it carries its own
false positives, and `rvso` is one of them — it is absent from the manual ground truth and
absent from `lasset_refined.json`, meaning LAsset's own refinement stage deleted it. We
score against the manual ground truth, so its absence from the FN list is correct.

Same for `sc_fail`, which we emit and which the paper classes as a *secondary* asset: our
stage 5 emits primary assets only, so counting it as a false positive is right.

The instinct that something was wrong was nonetheless correct — chasing it found the
name-collapse bug now fixed in M-2. Wrong premise, real bug.

### R-03 · Numbers in this file are pasted, not retyped — 2026-08-03
`neorv32_bus` emit counts were transcribed as 10 / 19 / 26; the runs are 10 / 18 / 25.
Harmless here, but it is the reason §4 says to paste from `ablate()`.
