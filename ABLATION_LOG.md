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

Cost: `neorv32_cache.inval_i` is `inv_i` in `RTL_data` (v1.11.4.3) — the reference was
annotated against a different NEORV32 revision. **Max achievable recall is 0.991.**

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
not a reason to revert.

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

Got: —

### A-03 · Port-record granularity rule
See below for the rule. Motivation strengthened by A-01: port-field false positives went
19 → 51, now 30% of all FPs, because the examples are Verilog and can never demonstrate the
port-versus-port-field distinction.

**Run separately from A-02.** They touch the same prompt and could cancel the way port and
signal did in A-01, leaving you unable to attribute either.

Expect: —

Got: —

#### A-03 rule text
From C-05:

> A record-typed **port** carries the module's external interface; if it matters, name the
> port, not its field (`ctrl_i`, not `ctrl_i.csr_wdata`). A record-typed **internal signal**
> is the opposite: name the field that holds the state (`ctrl.enable`, not `ctrl`).

Grounding beyond the counts in C-05: `gt` does treat CPU privilege/interrupt/debug state as
assets — `firq_i`, `mei_i`, `msi_i`, `mti_i`, `dbi_i` in `neorv32_cpu`, `ctrl_i` in
`neorv32_cpu_pmp` — and names every one as a whole, undotted port.

Phrased as granularity with no count or threshold, deliberately. A numeric cap becomes a
hard quota however it is hedged: an earlier "stop at ~20% of the closed set" suggestion cost
7 of 17 recall losses on `cpu_cp_cfu`, whose ground-truth density is 38%.

Expect: —

Got: —

---

## 4. Results

All **M-2** unless stated. Scored against `gt` on the 15 modules common to every run
(ref = 111 elements). `n` = repeats. Paste from `ablate()`; never retype a number.

| arm | version | n | emit | TP | FP | FN | P | recall | sd | F1 | sd |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A-00 | v0 | 3 | 205 | 61 | 143 | 50 | 0.300 | 0.553 | 0.019 | 0.389 | 0.010 |
| A-01 | v01 | 3 | 235 | 67 | 167 | 44 | 0.288 | 0.607 | 0.005 | 0.390 | 0.015 |
| — | *LAsset paper* | 1 | 137 | 101 | 36 | 10 | 0.737 | 0.910 | | 0.815 | |

**Recall by element class is the PRIMARY metric here, not aggregate recall.** A-01 is the
proof: aggregate recall read +0.049 [−0.061, +0.166], an honest null, while port recall rose
+0.181 [+0.048, +0.302] and signal recall fell −0.157 [−0.229, −0.086] — *both clearing
zero* and cancelling. The aggregate was not wrong, it was uninformative. With 15 modules the
aggregate CI runs ±0.14 and will keep failing to resolve real effects, so report the classes.

| | port | signal | signal-field |
|---|---|---|---|
| reference size | 47 | 32 | 31 |
| v0 | 0.326 | 0.771 | 0.688 |
| **v01** | **0.589** | **0.573** | 0.688 |
| *LAsset paper* | *0.894* | *0.906* | *0.935* |

False positives by class:

| | port | signal | signal-field | port-field |
|---|---|---|---|---|
| v0 | 7 | 43 | 74 | 19 |
| v01 | 14 | 39 | 64 | **51** |
| *paper* | *6* | *7* | *19* | *0* |

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
