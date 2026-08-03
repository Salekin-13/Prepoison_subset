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
detectable effect; every later arm is read against it.

Expect: —

Got: —

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

Expect: —

Got: —

### A-02 · Core prompt
Variants of `ASSET_PRIMARY_CORE`, holding the ICL block fixed. Versions not yet chosen.

Expect: —

Got: —

### A-03 · Port-record granularity rule
From C-05. Rule to add to a core variant:

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

All M-1 unless stated. Scored against `gt` on the modules common to every run. `n` =
repeats. Paste from `ablate()`.

| arm | version | n | emit | TP | FP | FN | P | recall | sd | F1 | sd |
|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | |

*LAsset paper*, its own line 5 on the same 15 modules — the target:

| | n | emit | TP | FP | FN | P | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| LAsset paper | 1 | 137 | 101 | 36 | 9 | 0.737 | 0.918 | 0.818 |

Paired deltas, modules as the pairing unit, 95% bootstrap CI:

| comparison | Δrecall | ΔF1 |
|---|---|---|
| | | |

---

## 5. Metric

A result is comparable only to another under the same `M-n`. If this list grows, restamp or
re-run; old numbers do not become wrong, they become unlabelled, which is worse.

### M-1 — current, from 2026-08-02
Match is exact, or the one legitimate near-match where the reference names a whole record
and the prediction names one of its fields, or the reverse. Field-to-field matching is
refused — crediting a predicted `fifo.avail` against a ground-truth `fifo.re` rewards
spraying record fields. Module sets are intersected across all runs before scoring, so an
arm that failed a module cannot report totals over a different denominator.

TP / FP / FN with precision, recall, F1. No TN or FPR: the negative class outnumbers the
positives ~14:1, so FPR reads ~0.1 while precision is ~0.3.

---

## 6. Open threats

Delete a line when it stops being true.

- **Tuning set sits inside the reporting set.** The 18 modules are a subset of the paper's
  41. Selecting prompts on 15 of them and later reporting on 41 contaminates 15. Plan: report
  the final number split into tuned-on and unseen.
- **Three NEORV32 revisions in play.** `RTL_data` v1.11.4.3, `neorv32/rtl/core` v1.11.0.6,
  datasheet v1.11.2. Measured impact so far is one element (C-03).
- **v01 vs v02 is confounded** — IP and label provenance move together (A-01).
- **Pre-study run directories still on disk.** `assets_tuning18`, `_v0`, `_v1` are n=1
  exploratory runs from before the framework. `collect()` prefers `_r*` directories, so they
  are superseded automatically once an arm runs — but until then they will populate the
  scoreboard. Do not report them.
