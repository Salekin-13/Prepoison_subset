# Verifier ablation log — parser-audit fidelity study

Companion to `ABLATION_LOG.md` (v1 recall) and `ABLATION_LOG_V2.md` (v2 precision), which stay
exactly as they are. Nothing here changes a number, a sha, or a conclusion in either.

Those two logs study **asset triage**. This one studies the **verifier that sits upstream of
it** — the auditor that checks whether the parser's behavioral claims are actually supported by
the RTL.

Opened 2026-08-21. Arm **V-1 is complete** (run_008); its result is in section 7.

---

## 1. What this study is

**Goal: make the verifier a trustworthy instrument, so its error patterns can be used to revise
the parser prompt.**

The verifier is not the result. It is the measuring device in this loop:

```
                    ORIGINAL RTL
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
      deterministic facts      parser JSON
              │                     │
              └──────────┬──────────┘
                         ▼
                  LLM VERIFIER
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
        verification             error evidence
          results                     │
             │                        │
             └──────────┬─────────────┘
                        ▼
               parser error patterns
                        │
                        ▼
                 parser prompt revision
```

A pattern count from this instrument becomes an edit to the parser prompt. If the instrument is
noisy or incomplete, that edit is made on noise. So two properties have to be measured before
any pattern count is acted on:

1. **Reproducibility** — does the same input, same prompt, same configuration give the same
   verdicts twice?
2. **Coverage** — does the verifier return one check per parser claim, or does it silently drop
   and merge claims so the counts are computed over a subset?

Neither was measured before 2026-08-21. Coverage was not even instrumented.

**Scope discipline, carried over from the notebook.** The verifier never identifies assets,
never assigns C/I/A/U, never reads `back_test.md`. Every status is of the form *"the parser
claims X; the RTL supports / partially supports / contradicts / does not establish X."* This is
asserted in code (cell 16 scope guard) and is not an arm of this study.

---

## 2. Runs already on disk — retrospective, NOT arms of this study

These four predate the log. They are recorded for provenance and are not counted as arms.

| run | verifier | prompt sha | effort | calls | cost | what it actually is |
|---|---|---|---:|---:|---:|---|
| `run_003` | VP2 | `c2d2368be778` | medium | 26 | $0.1964 | VP2 baseline. 1 parse error (26/27 ok). |
| `run_004` | VP3 | `26a2583261da` | medium | 27 | $0.1988 | VP3 at medium effort. Full claim coverage. |
| `run_005` | VP3 | `26a2583261da` | medium | **0** | **$0.0000** | **INVALID as a distinct observation — see below.** |
| `run_006` | VP3 | `26a2583261da` | **high** | 31 | $0.5684 | VP3 at high effort. 4 budget escalations. |

All four are `neorv32_imem`, 27 elements, parser `v3_tuning18`, model `gpt-5-mini`.

### run_005 is a cache replay and must never be quoted as a run

Its manifest says VP3 and its own `usage_and_cost` says `{"calls": 0, "usd": 0.0}`. Its prompt
sha is byte-identical to run_004's. The version label was bumped VP2 → VP3 **without changing a
character of prompt text**, `verifier_prompt_version` was not part of the cache key, so all 27
responses replayed from run_004 and the replay was written to disk as a distinct "VP3" run.

Its `error_summary.json` is identical to run_004's, digit for digit. That identity is an
artifact of the cache, not a finding about stability.

**Fixed 2026-08-21:** `verifier_prompt_version` is now part of `_cache_key()`, so a version bump
forces real calls. `run_005/` is left on disk unaltered; this entry is the correction.

### run_004 vs run_006 is an unintended effort ablation

The only configuration difference is `reasoning_effort` medium -> high. Same prompt sha, same
model, same budget, same payloads. Measured on `claim_status.csv`, joined on `claim_key_norm`:

```
claim-level agreement        151/175 = 86.3%
element overall agreement     27/27  = 100%
per-field:  functionality .926   evidence .889   relationship .841   role .840

transition matrix (004 -> 006), disagreements only:
    PARTIALLY_SUPPORTED -> SUPPORTED             17
    SUPPORTED           -> PARTIALLY_SUPPORTED    6
    NOT_ESTABLISHED     -> CONTRADICTED           1

claims that did not join at all: 8 -- ALL genuine coverage loss, no formatting
    addr             SELECTS -> mem_ram_b0..b3    4 claims in 004, merged into 1 in 006
    bus_req_i.amo    ISOLATED                     present in 004, absent in 006
    bus_req_i.priv   ISOLATED -> bus_req_i.priv   present in 004, absent in 006
    bus_rsp_o.err    ISOLATED                     present in 004, absent in 006
```

**Higher effort makes the verifier less likely to flag partial support, and costs 2.9x more.**
The dominant movement is 17 claims relaxing from PARTIALLY_SUPPORTED to SUPPORTED.

> **WITHDRAWN 2026-08-21 by arm V-1.** The same lenient drift (22 claims, same direction)
> appears between two runs at the SAME effort, and a pure replicate agrees at 85.1% against
> this pair's 86.3%. The effort change produced no signal above run-to-run noise. Read this
> paragraph as a description of noise, not of effort. See the V-1 result in section 7.

**This is an effort ablation confounded with run-to-run noise, not a variance measurement.**
Nothing here separates "high effort judges differently" from "the model is just variable".
Separating them is exactly what arm V-1 is for.

**On the join key.** On the raw model-authored key the same comparison reads 149/173 = 86.1%
with 12 non-joining rows. Four of those rows -- two claims, counted once in each run -- were
pure reformatting by the model (`ISOLATED -> ` vs `ISOLATED -> (none)`;
`bus_req_i.addr(hi downto 2)` vs `bus_req_i.addr (hi downto 2)`) and are not verdict changes.
`_norm_key` folds them together, which is why the joined count rises from 173 to 175 and the
remaining 8 non-joining rows are all real.

The normaliser deliberately does **not** merge the collapsed `SELECTS` case or the dropped
`ISOLATED` claims. Those are coverage loss, and a join key that hid them would make the defect
in section 3 line 3 invisible. Formatting is normalised; missing claims stay missing.

---

## 3. Instrument changes made 2026-08-21, before V-1

Ten defects found and fixed in `notebooks/parser_verifier.ipynb`. Recorded here because every
one of them changes what a number in a future run means.

| # | defect | effect if unfixed |
|---|---|---|
| 1 | `USAGE` undefined — deleted when `_cache_key` was rewritten | **every API call `NameError`s after being billed**, is swallowed into `api_error`, nothing caches, then `cost()` raises uncaught and the run's results are lost |
| 2 | `inspect()` body swallowed its own call site (indent bug) | infinite recursion the moment `SMOKE_ENABLED = True` |
| 3 | claim coverage never measured | run_006 lost 6 of 78 (type,target) pairs; every count was over the survivors |
| 4 | `PATTERNS` had a duplicate key (11 entries, 10 unique) | second definition silently overwrote the first; advertised a detector that did not exist |
| 5 | `flatten()` keyed claims on model-authored text | run-to-run joins report formatting as disagreement |
| 6 | parse errors emitted as `status=None` | dropped by `pivot_table`; a failed run looked cleaner than it was |
| 7 | `run_tag` in the cache key but not the manifest | a saved run had no record of which replicate it was |
| 8 | `verifier_prompt_version` not in the cache key | produced run_005 |
| 9 | `project_cost` divided USD by **calls**, not elements | budget escalations inflate the call count; full-run projection understated by 13% ($30.97 → $35.6) |
| 10 | dead `deep_traces` reference | cosmetic |

### What was deliberately NOT changed

**`VERIFIER_SYSTEM` is untouched.** sha stays `26a2583261dae183f87efa6acae272809ac9ba9cfe3724b938758f494569658b`, 14 948 chars. Changing one character moves the sha, invalidates the cache, and destroys comparability with run_006.

**Payload identity verified, not assumed.** Every one of the 27 `neorv32_imem` payloads was
rebuilt from the patched notebook and hashed under the *old* cache-key formula. All 27 hit an
existing run_006 cache entry:

```
old-key cache hits: 27/27   misses: 0
=> payload is byte-identical to run_006
```

So V-1 differs from run_006 in the cache key and nothing else. That is what makes it a clean
replicate rather than a confounded one.

**Claim coverage is measured, not repaired.** `claim_coverage()` records the loss and
`run_verification` prints a warning. The verifier is not patched to re-ask for missing checks,
and merged targets are not split apart. Repairing model output in the harness would make the
defect invisible while leaving it in the prompt — the same reasoning that keeps
`validate_verification` free of silent JSON repair. The fix, if one is warranted, belongs in
VP4.

**The builder is now guarded.** `build_verifier_notebook.py` was 7 of 8 features behind the
notebook and would have silently reverted all of the above. It now refuses to overwrite when
the on-disk code cells differ from what it generates (content-based, so touching the file does
not defeat it). `--force` overrides. This folder is not under git.

---

## 4. Reported quantities — defined before any number is seen

For every replicate pair, report all of these. Not a subset chosen after the fact.

**Agreement — two different measures, both required.** They answer different questions and can
diverge sharply (run_004/006: 86.3% vs 100%).

| measure | unit | question it answers |
|---|---|---|
| claim-level agreement | claims | did the same claim get the same status? |
| element overall agreement | elements | did the verifier reach the same conclusion for the element? |

**Also reported, every time:**

- exact number of changed **elements**, named
- exact number of changed **claims**, named
- per-field agreement — functionality / role / relationship / evidence, separately
- full transition matrix (`SUPPORTED → PARTIALLY_SUPPORTED`, etc.)
- which **error types** changed, by count and severity
- claim coverage: elements incomplete, (type,target) pairs lost
- parse errors, budget escalations, still-incomplete responses
- calls, cost, **usd per element** (not per call)

**Join key is `claim_key_norm`, never `claim_key`.** Normalises case, whitespace, empty-target
spellings, and target order. Raw-key results may be reported alongside as a lower bound, and
must be labelled as such.

**Denominators travel with every percentage.** `pattern_report` carries `unit: elements` and
`pct_of_elements` for this reason; `error_summary` counts error instances. They are different
numbers and are not to be quoted interchangeably.

### No agreement thresholds

**No pass/fail agreement threshold is defined, and none is to be invented after the numbers
arrive.** A "96–100% = good, <85% = bad" style rubric was considered and rejected:

- n = 27 elements / ~176 claims. A handful of changed claims moves the percentage several
  points.
- Claims are **not independent**. One element contributes up to six correlated relationship
  claims, so the effective sample is well below the claim count and no ordinary interval
  applies.
- There is no prior run at this configuration to calibrate against — run_006 is the only one,
  and V-1 is its first replicate.

Report the magnitudes and the named changes. Interpret them against the specific claims that
moved, not against a number picked in advance.

---

## 5. Decision rules, written before the run

**R1 — V-1 is a variance diagnostic, not a stability certification.** One replicate of one
27-element module estimates same-input variability *for that module at that configuration*. It
does not establish that the verifier is stable in general, and no sentence anywhere may say
that it does.

**R2 — the progression is staged, and each stage is decided on the previous one's numbers.**

```
27-element repeat (V-1)
      ↓  inspect what changed, claim by claim
possibly repeat a second, structurally different module
      ↓
estimate whether repeated judgments (n>1 per element) are necessary at all
```

Do not queue V-2 before V-1's changed claims have been read individually.

**R3 — repeated judgments are a cost decision, and the trigger is stated in advance.** If the
claims that move between V-1 and run_006 are concentrated in a field or a claim type that
drives a parser-prompt edit, then that edit is being made on noise and majority-of-3 is
required for that field before acting. If the movement is in claims that no prompt edit depends
on, single judgments stand. **The trigger is "does a prompt edit depend on a claim that moved",
not an agreement percentage.**

**R4 — `run_tag` discipline.** A stable tag within a run; a new tag for every intentional
replicate. Never change it mid-run. A normal run keeps its tag so the cache enables resumption;
a variance replicate takes a fresh tag to bypass the cache deliberately.

**R5 — coverage loss is reported before any pattern count.** If a run drops or merges claims,
every count in it is over a subset. The `rel_pairs_lost_to_merging` figure is quoted alongside
any pattern table from that run, not filed separately.

**R6 — no prior verification result may enter a payload.** Already asserted per payload in code
(`assert_no_prior_results_used`). Every run compares parser output against RTL independently,
so an early verifier mistake cannot become pseudo-ground-truth later. This is a hard rule, not
an arm.

**R7 — patterns describe; they do not edit.** `pattern_report` never rewrites the parser
prompt. The last hop of the loop is manual and stays manual.

---

## 6. What V-1 can and cannot establish

**Can:** whether two runs at identical input and configuration produce the same verdicts on
`neorv32_imem`; which specific claims are unstable; whether the claim-dropping seen in run_006
is reproducible or was a one-off.

**Cannot:** anything about the other 16 modules. `neorv32_imem` is 27 of 1 689 elements (1.6%),
it is small, it is memory-shaped, and it is the only module in the corpus carrying a
`false`-valued generate guard (`alt_style_c`). Its claim mix is not the corpus's claim mix.

**Cannot:** separate "the model is variable" from "this module is hard". That needs a second
module, which is R2's next stage.

**Cannot:** justify a full-corpus run on cost grounds. The $35.6 projection is extrapolated
from one 27-element module at a rate that includes 4 budget escalations. It is an order of
magnitude, not a quote.

---

## 7. Arms

### V-1 · Same-input replicate of run_006 — **RUN 2026-08-21, see result below**

**Question.** Run the identical payload, prompt, model, effort and budget as run_006 a second
time. How much of run_006's output is reproducible?

**This is the first arm because nothing downstream is interpretable without it.** run_006 is
currently the only run at the current configuration, and `CONDITIONAL_BEHAVIOR_ERROR` at 44.4%
of elements is the only pattern with enough mass to drive a parser-prompt edit. Whether that
44.4% is a property of the parser or a property of one sampling of the verifier is unknown, and
V-1 is what decides it.

**Configuration — identical to run_006 except `run_tag`.**

| | value |
|---|---|
| module / elements | `neorv32_imem` · 27 |
| STAGE | 1 |
| parser | `v3_tuning18` → `parsed_v3_tuning18` |
| RTL | `RTL_data`, 18 files, 26 entities |
| verifier prompt | **VP3**, sha `26a2583261dae183`, 14 948 chars — unchanged from run_006 |
| model | `gpt-5-mini`, Responses API, reasoning |
| reasoning effort | `high` |
| max_output_tokens | 12 000, ceiling 24 000, escalate on incomplete |
| temperature / seed | **none** — the Responses API accepts neither for a reasoning model |
| context extraction | ±6 lines, ≤40 hits/symbol, ≤22 000 chars |
| workers | 4 |
| **run_tag** | **`vp3_variance_01`** ← the only difference |
| writes to | `verification_results/run_007/` |

**No decoding-level determinism exists here.** There is no temperature and no seed to fix. Any
run-to-run difference is the model's own sampling variability at `effort=high`, which is
precisely the quantity being measured.

**Cost.** All 88 cached responses are unreachable under the new key, so this is 27 fresh calls.
At the run_006 rate: **≈ $0.57**, 27–31 calls depending on escalations. This is not free and
the cache will not rescue it.

**Predictions, recorded before the run so they can be scored:**

| prediction | reasoning |
|---|---|
| claim-level agreement (on `claim_key_norm`) lands **above 86.3%** | a pure replicate should differ less than an effort change did |
| the dominant transition is again **PARTIALLY_SUPPORTED ↔ SUPPORTED**, roughly symmetric | that boundary carried 23 of 24 movements in the effort ablation; with no effort change the asymmetry should collapse |
| element overall agreement stays at or near **27/27** | it was 100% even across an effort change |
| **claim coverage is incomplete again**, 2–6 pairs lost | the drop/merge behaviour looks like a prompt property at high effort, not a one-off |
| budget escalations recur, **2–6** | run_006 had 4 at this exact budget |
| **`relationship` is the least stable field** | it was lowest in the effort ablation (.841) and carries the most claims per element |

**Reading the result:**

- Agreement near run_006 **and** the same claims flagged → the instrument is usable as-is on
  this module; proceed to R2's second module.
- Agreement high **but different claims flagged** → the aggregate is stable while the
  attribution is not, which is worse for this pipeline than a lower agreement number, because
  the parser-prompt edit depends on *which* claim moved.
- Coverage loss recurring at similar magnitude → VP4 is warranted, targeted at the
  one-check-per-pair instruction and at `ISOLATED` claims specifically.
- Coverage loss absent → run_006's loss was sampling, and VP4 waits.

**Status: complete. Result recorded below as run_008.**

---

### V-1 · RESULT, 2026-08-21 — `run_008`

Completed after one interruption. 11 elements replayed from cache, 16 called fresh.
17 calls, **$0.3112**, 27/27 parsed, 0 API errors, 0 harness errors, 3 escalations
(1 fresh + 2 carried on replayed rows), 0 still-incomplete.

`run_007` is an **empty directory** — cell 4 mints a run dir on every kernel start, and the
interrupted session never reached `save_run`. It holds nothing and is not a run.

#### Headline

```
claim-level agreement       149/175 = 85.1%     (joined on claim_key_norm)
element overall agreement    26/27  = 96.3%
per-field:  functionality .926  evidence .926  relationship .831  role .800

transition matrix (006 -> 008), changed claims only:
    PARTIALLY_SUPPORTED -> SUPPORTED             22
    SUPPORTED           -> PARTIALLY_SUPPORTED    2
    CONTRADICTED        -> PARTIALLY_SUPPORTED    2

claims that did not join: 8 -- ALL of them run_006 coverage loss that run_008 did not repeat
```

#### Predictions vs outcome — 2 of 6 correct

Recorded in §7 before the run, scored here without adjustment.

| prediction | outcome | |
|---|---|---|
| claim agreement **above 86.3%** | **85.1%** — slightly *below* | ✗ |
| dominant transition PARTIALLY ↔ SUPPORTED, **roughly symmetric** | dominant yes; **22:2, strongly asymmetric** | ✗ |
| element overall agreement at/near 27/27 | 26/27 | ✓ |
| coverage incomplete again, **2–6 pairs lost** | **0 lost, 0 incomplete elements** | ✗ |
| escalations 2–6 | 3 | ✓ |
| `relationship` the least stable field | **`role` was worst** (.800 vs .831) | ✗ |

#### Finding 1 — the effort ablation in §2 was noise

A **pure replicate** (identical prompt, model, effort, budget, payload) agrees at **85.1%**.
Two runs at **different reasoning effort** agreed at **86.3%**.

The replicate agrees no better than the effort change did. **The medium→high effort
difference produced no signal detectable above run-to-run variation on this module.** §2's
reading — "higher effort makes the verifier less likely to flag partial support" — is
withdrawn: the same 22-claim lenient drift appears between two runs at the *same* effort.
What §2 measured was noise wearing an effort label.

#### Finding 2 — SUPPORTED is stable; PARTIALLY_SUPPORTED is not

Where each run_006 status landed in run_008:

| run_006 status | n | stayed | went |
|---|---:|---:|---|
| `SUPPORTED` | 104 | **98.1%** | 2 → PARTIALLY |
| `PARTIALLY_SUPPORTED` | 67 | **67.2%** | **22 → SUPPORTED** |
| `CONTRADICTED` | 4 | 50.0% | 2 → PARTIALLY |

**A third of PARTIALLY_SUPPORTED verdicts do not survive a repeat**, and they move almost
entirely one way. The overall mix shifts with them: SUPPORTED 59% → 70%.

This is the most consequential result so far. `PARTIALLY_SUPPORTED` is not behaving as a
distinct verdict — it reads as a low-confidence `SUPPORTED`. **Any headline number built on
PARTIALLY_SUPPORTED counts is unreliable**, including the partial-support columns of
`status_by_field.csv`. CONTRADICTED at n=4 is too small to characterise.

#### Finding 3 — the verifier's own confidence predicts instability

| run_006 confidence | claims | flipped in run_008 |
|---|---:|---:|
| `< 0.80` | 5 | 40.0% |
| `0.80 – 0.89` | 31 | 32.3% |
| `0.90 – 0.94` | 55 | 16.4% |
| `>= 0.95` | 84 | **6.0%** |

Monotonic, and usable. Restricting to `confidence >= 0.95` keeps 48% of claims and raises
stability to 94%. This is the cheapest available reliability lever — no extra API calls, no
repeated judgments — and it should be tried before anything more expensive.

(All 5 `TRACED_RTL` claims held while 25 of 26 flips were `DIRECT_RTL`. n=5 is far too small
to mean anything; recorded only so it can be checked at scale.)

#### Finding 4 — the run_006 coverage loss was sampling, not a prompt property

run_006 dropped 3 `ISOLATED` claims and merged 4 `SELECTS` targets into one check: 6 lost
pairs. **run_008 lost nothing** — `claim_coverage_incomplete: 0`, `rel_pairs_lost_to_merging:
0`, and it returned `addr SELECTS` as four separate checks exactly as the prompt requires.

All 8 non-joining claims are run_006's loss, not run_008's. §7's prediction that this was a
stable prompt-level defect is withdrawn. **VP4 is not warranted on coverage grounds** — but
coverage must stay instrumented, because one clean run does not establish it cannot recur.

#### The R3 decision — what may be acted on

| category | run_006 | run_008 | shared | verdict |
|---|---:|---:|---:|---|
| `CONDITIONAL_BEHAVIOR_ERROR` | 12 | 9 | **9** | **stable core — actionable** |
| `RELATIONSHIP_ERROR` | 7 | 6 | **5** | stable core — actionable with care |
| `COMBINATIONAL_REGISTER_ERROR` | 1 | 1 | **0** | **noise** |
| `EVIDENCE_ERROR` | 0 | 1 | 0 | noise |
| `MISSING_BEHAVIOR` | 0 | 1 | 0 | noise |
| `ROLE_ERROR` | 1 | 0 | 0 | noise |

The stable 9 for `CONDITIONAL_BEHAVIOR_ERROR`:

```
bus_req_i.ben  bus_req_i.data  bus_req_i.stb  clk_i
mem_ram_b0  mem_ram_b1  mem_ram_b2  mem_ram_b3  rdata
```

Marginal, one run only: `addr`, `addr_ff`, `bus_req_i.rw`.

**R3 verdict: the conditional-branch finding is solid on those 9 and a parser-prompt edit may
be written from them.** Nine elements appear in both runs and run_008 introduced no new ones,
so the core is a subset relationship rather than a reshuffle. Do not cite the count "12 of 27"
— it is 9 stable plus 3 that come and go. Do not cite per-element findings for the marginal
three.

`COMBINATIONAL_REGISTER_ERROR` is the textbook trap §5 was written for: **1 element in each
run, zero overlap** (`rdata` in run_006, `clk_i` in run_008). A count-based reading calls that
perfectly stable. The element-set reading shows it is pure noise. This is the concrete
justification for R3 and for refusing a percentage threshold.

Six of 27 elements changed their error set outright; `addr_ff` went from three errors to none.

#### Instrument note

The join key needed a third revision during this analysis. run_008 introduced two spellings
the previous normaliser missed — `ISOLATED -> (no targets)`, and bit-range annotations such as
`mem_ram_b0(bits 7 downto 0)` where run_006 wrote `mem_ram_b0`. Verified before changing it:
the parser never puts parentheses in a target (0 of 68 in this module; bit ranges live in a
separate `bits` field), so parenthesised text on the target side is always the verifier's own
annotation and never part of the claim. Folding it recovered 7 claims: joined 168 → 175,
agreement 84.5% → 85.1%, non-joins 22 → 8.

#### What V-1 does not establish

One module, 27 elements, 1.6% of the corpus, and a single repeat. It gives an estimate of
same-input variability for `neorv32_imem` at this configuration and nothing more. Per §6 it
cannot separate "the model is variable" from "this module is hard", and it says nothing about
the other 16 modules.

---

### O-1 · Parser coverage of the RTL — **RESULT, 2026-08-22**, deterministic, $0.00

Every other check audits claims the parser **made**. None could see a signal the parser never
mentioned: the verifier is only ever shown elements that exist in the parsed JSON, so an
omission was invisible by construction. This closes the gap in the other direction.

Ports from each `entity X is` clause and signals from its architecture body, compared against
parsed elements in both directions. Generics, constants, types, components, variables and
aliases excluded — the parser is not asked to describe them. Record fields folded to their base
port. Matched against the comment-stripped mirror.

```
entities checked          26
RTL symbols declared     444
OMITTED  (in RTL, never parsed)    0
FABRICATED (parsed, not in RTL)    0
```

**The parser missed nothing and invented nothing, across all 26 entities and 1 689 elements.**
On the coverage question — one of the two ways a parser can hallucinate — the answer is clean.

This measures **coverage, not correctness**. An element can be present and still be described
wrongly; that is what the LLM verifier is for.

#### Two extraction bugs found before this number was trusted

Both produced confident, wrong answers first, and both are recorded because the fix is not
obvious from reading VHDL casually:

1. **Declarations are not one per line.** `neorv32_bus.vhd` writes
   `dev_00_req_o : out bus_req_t; dev_00_rsp_i : in bus_rsp_t;` on a single line. A
   line-anchored regex caught only the first and reported **32 phantom fabrications** in
   `neorv32_bus_io_switch`.
2. **The first port has no preceding `;`.** It sits directly after `port (`, so a `(?:^|;)`
   delimiter dropped one port from *every* entity and reported `clk_i` as fabricated **26
   times**.

Requiring a mode keyword (`in`/`out`/`inout`/`buffer`) is what separates ports from generics,
so the generic clause needs no special case. Cross-checked against an independent extraction;
where the two disagreed (`neorv32_bus_io_switch`, 82 vs 72) the **cross-check** was wrong — it
searched to end-of-file and swept in signals belonging to later entities in the same file.

---

### VP4 · Full-architecture context — **QUEUED, not yet run**

**The defect being fixed.** VP3's RTL excerpt was assembled by searching the file for the very
symbols the parser claimed:

```python
syms = [rec["name"], _base(rec["name"])]
for r in rec["relationship"]:
    for t in (r.get("targets") or []):
        syms += [t, _base(t)]
```

The verifier was shown evidence **selected by the hypothesis it was meant to test**. If the
parser invented a dependency on a signal that exists elsewhere in the file, the excerpt would
dutifully contain lines mentioning both. Absence was never observable, because the excerpt was
built from the claim.

The consequence is visible in run_008: of 182 checks, **`NOT_ESTABLISHED` was returned 0
times** and `UNVERIFIABLE` 0 times. The verdict that means *"plausible, but the RTL does not
show it"* — the natural hallucination signal — was never once reached.

**The change.** Send the whole entity declaration and architecture body, contiguous and
unabridged, whenever it fits. Measured: at `ctx_max_chars` 32 000, **all 26 entities fit and
100% of the 1 689 elements get `FULL_ARCHITECTURE`** (at the old 22 000 it was 25 of 26; only
`neorv32_cpu` at 23 740 chars needed the raise). The claim-driven excerpt remains as a fallback
and is now explicitly labelled as biased when used.

The payload states its `CONTEXT MODE`, and the prompt tells the verifier what each mode means:
under `FULL_ARCHITECTURE` absence **is** evidence and `NOT_ESTABLISHED` is the right answer for
a claim that does not appear; under `CLAIM_DRIVEN_EXCERPT` absence proves nothing.

**Second prompt change — the INTERPRETATION label.** run_008 marked **180 of 182 checks
`DIRECT_RTL` and 0 `INTERPRETATION`**, while a third of its `PARTIALLY_SUPPORTED` verdicts did
not reproduce on an identical repeat. A verdict that changes when nothing changed was not read
off the RTL. VP4 adds an operational test: `DIRECT_RTL` means a careful reader given the same
lines reaches the same verdict every time; a call that turns on degree — whether an omission is
important enough to be `PARTIALLY_SUPPORTED` rather than `SUPPORTED` — is `INTERPRETATION`.

**Third change — payload order.** The RTL now comes **first**, ahead of the claims. It is
identical for every element of an entity, so it becomes a shared prompt prefix that
provider-side caching can cover. Measured: **9 893 chars (~2 473 tokens) of shared prefix**
across `neorv32_imem` elements; `neorv32_bus_io_switch` alone has 582 elements sharing one
architecture.

**Configuration.**

| | VP3 | VP4 |
|---|---|---|
| prompt sha | `26a2583261dae183` | `8e7e3fb0e517685d` |
| prompt chars | 14 948 | 16 981 |
| `ctx_max_chars` | 22 000 | 32 000 |
| context mode | claim-driven excerpt | **full architecture, 1689/1689** |
| payload order | claims → RTL | **RTL → claims** |
| `run_tag` | `vp3_variance_01` | `vp4_full_context_01` |
| median context | ~3 600 chars | **16 883 chars** (max 28 878) |

**Cost.** The whole cache is invalidated — prompt and payload both changed. Input tokens roughly
triple, but input is only **1.2%** of spend (run_008: $0.0035 input against $0.2950 output), so
that is nearly free, and prefix caching claws back most of it. **The real and unmeasured risk is
that a larger context provokes more reasoning**, and reasoning is billed as output at
$2.00/1M — where all the money is. Run one module before committing to a full pass.

**Predictions, recorded before the run:**

| prediction | reasoning |
|---|---|
| `NOT_ESTABLISHED` appears at all — **more than 0 of ~182** | it was structurally unreachable before; this is the whole point of the arm |
| `INTERPRETATION` appears at all — **more than 0** | the operational test names the exact case that was being mislabelled |
| output tokens per element **rise**, escalations rise with them | a 4.7× larger context to reason over |
| `SUPPORTED` share **falls** from 69.8% | some support was an artifact of a claim-shaped excerpt |
| the `CONDITIONAL_BEHAVIOR_ERROR` core of 9 **largely survives** | it reproduced across two VP3 runs; if full context dissolves it, it was an excerpt artifact |

**Status: complete — `run_009`, 2026-08-22.**

### VP4 · RESULT — `run_009`

27/27 parsed, 0 API errors, 4 escalations, **$0.5334**, all 27 called fresh.

#### Predictions vs outcome — 3 of 5 correct

| prediction | outcome | |
|---|---|---|
| `NOT_ESTABLISHED` appears — more than 0 | **still 0 of 179** | ✗ |
| `INTERPRETATION` appears — more than 0 | **4 of 179**, and `TRACED_RTL` 2 → 10 | ✓ |
| output tokens per element rise, escalations with them | output/call **8 677 → 8 307**; cost/element **$0.0194 → $0.0198** | ✗ |
| `SUPPORTED` share falls from 69.8% | **69.8% → 53.1%** | ✓ |
| the 9-element `CONDITIONAL_BEHAVIOR_ERROR` core largely survives | **9 vs 9, 7 shared** | ✓ |

#### Finding 1 — the mechanism was right, the predicted signature was wrong

The dominant movement is **`SUPPORTED` → `PARTIALLY_SUPPORTED`, 32 claims**. Reading the
downgrades, they are substantively justified and they share one cause: with the whole
architecture visible the verifier can see that an assignment sits inside
`if not IMEM_INIT generate`, so the dependency is **conditional on a generic** rather than
unconditional. The claim-shaped excerpt showed the assignment but not enough of the enclosing
structure, and VP3 endorsed it outright.

```
rdata DERIVES_FROM mem_ram_b3
  VP3  SUPPORTED  0.95  "rdata(31 downto 24) <= mem_ram_b3(to_integer(addr)) (L131)"
  VP4  PARTIALLY  0.80  "...inside the imem_ram generate region (if not IMEM_INIT generate)
                         (L106-L165), so the dependency is conditional on IMEM_INIT = false"
```

So the retrieval bias was real and VP4 removed it — but it expressed itself as
**over-endorsement**, not as false confidence about existence. §7's prediction looked for the
wrong tell.

#### Finding 2 — zero NOT_ESTABLISHED is a finding about the parser, not a broken instrument

The VP4 hypothesis was that a claim-shaped excerpt made `NOT_ESTABLISHED` unreachable. Full
context did not change it: still **0**. That hypothesis is **withdrawn**.

The better explanation is that there is nothing for it to fire on. `NOT_ESTABLISHED` means
*"plausible, but the RTL does not show it"* — and O-1 established that the parser invents
nothing: 0 fabricated elements, 0 omitted elements, and **0 of 2 929 relationship targets
unresolved** corpus-wide. This parser does not refer to things that are not there. Its failure
mode is **over-generalisation** — describing conditional behaviour as unconditional — and the
correct verdict for that is `PARTIALLY_SUPPORTED`, which is exactly what VP4 returns 79 times.

#### Finding 3 — VP4 catches the section-12 reset trap that VP3 missed

`CONTRADICTED` rose 2 → 5, and the new ones are the case this study was built around:

```
rstn_i SEQUENCES rden            "asynchronous reset branch if (rstn_i = '0') then rden <= '0'"
rstn_i SEQUENCES bus_rsp_o.ack   "if (rstn_i = '0') then ... bus_rsp_o.ack <= '0'"
clk_i  SEQUENCES addr_ff         "addr_ff is assigned a concurrent constant in the active branch"
```

A reset that **overrides** a register is not **sequencing** it. VP3 never flagged these. These
are genuine parser errors and they are actionable.

The other two `CONTRADICTED` (`bus_req_i` / `bus_rsp_o` `ISOLATED`) remain the vocabulary
disagreement recorded under V-1, not hallucinations.

#### Finding 4 — full context is free; the RTL-first ordering paid for it

| | run_008 (VP3) | run_009 (VP4) |
|---|---:|---:|
| median context | ~3 600 chars | 16 883 chars |
| total input tokens | 110 454 | 241 865 |
| **cached input share** | 45.9% | **77.4%** |
| output tokens / call | 8 677 | 8 307 |
| **cost / element** | **$0.0194** | **$0.0198** |

A 4.7× larger context cost **2% more per element**. Moving the RTL to the front of the payload
made it a shared prompt prefix, and the cached share rose from 45.9% to 77.4%. A full
1 689-element pass remains ≈ **$33**, not the $59 upper bound §7 allowed for.

#### Finding 5 — the coverage defect is intermittent and NOT fixed

| run | ISOLATED claims dropped |
|---|---|
| run_006 | 3 — `bus_req_i.amo`, `bus_req_i.priv`, `bus_rsp_o.err` (+ a merged `SELECTS`, 6 pairs) |
| run_008 | **0** |
| run_009 | 3 — `bus_req_i.priv`, `bus_req_i.debug`, `bus_rsp_o.err` |

V-1's conclusion that this was "sampling, not a prompt property" is **withdrawn**. With three
observations it is a recurring weakness in how `ISOLATED`-with-no-targets is handled: two runs
in three silently returned no `relationship_check` at all for such a claim. Per R5, run_009's
counts are over a subset of 179 rather than 182.

#### Instrument defect found and fixed

**VP4's defining change was invisible in its own output.** Neither the rows nor the manifest
recorded which retrieval mode produced a verdict — the one variable the arm changed. Fixed:
every row now carries `context_mode` and `context_chars`, and the manifest carries a
`retrieval` block with the settings and the mode distribution. Neither touches the cache key;
run_009's 27 cached responses verified still reachable (27/27).

#### R3 decision after VP4

| category | run_008 | run_009 | shared |
|---|---:|---:|---:|
| `CONDITIONAL_BEHAVIOR_ERROR` | 9 | 9 | **7** |
| `RELATIONSHIP_ERROR` | 6 | 6 | 4 |
| `MISSING_BEHAVIOR` | 1 | 1 | 1 |
| `COMBINATIONAL_REGISTER_ERROR` | 1 | 0 | 0 |
| `EVIDENCE_ERROR` | 1 | 0 | 0 |

The conditional-branch core held across a **prompt and retrieval change**, which is a stronger
test than the same-input repeat it survived in V-1. It did not evaporate under full context —
so it is a parser property, not an excerpt artifact. Note this comparison crosses two arms, so
it measures robustness, not variance.

---



---

### VP5 · Enumerated audit checklist + budget — **QUEUED, not yet run**

**Defect 1 — the instruction was literally wrong for a quarter of all relationships.**

```
"errors" is [] when nothing is wrong. Emit one relationship_check per (type, target) pair.
```

A relationship with `targets: []` has **zero (type, target) pairs**, so the verifier correctly
returned nothing and the claim was never audited. The model was obeying the instruction; the
instruction was wrong. `ISOLATED`, "no targets" and empty-target relationships were **never
mentioned anywhere** in the VP4 prompt.

Corpus-wide scale, measured:

```
relationships with NO targets: 678 of 2464 = 27.5%
by module: neorv32_bus 491, neorv32_cpu_cp_muldiv 37, neorv32_cpu 30,
           neorv32_spi 18, neorv32_wdt 18, neorv32_hwspinlock 14, ...
observed drop rate: 2 runs in 3 (run_006 dropped 3, run_008 dropped 0, run_009 dropped 3)
=> roughly 454 claims would go silently unaudited in a full pass
```

This supersedes V-1's "sampling, not a prompt property" reading and VP4's Finding 5: the cause
is now identified, and it is the prompt.

**Defect 2 — the same clause permitted merging.** run_006 collapsed four `SELECTS` targets into
one check (`mem_ram_b0, mem_ram_b1, mem_ram_b2, mem_ram_b3`), losing 3 further claims.

**Fix — enumerate, do not infer.** The payload now carries a numbered `AUDIT CHECKLIST` naming
every check the verifier must return, and the prompt requires exactly one check per line, in
order, no merging and no skipping. An empty-target relationship gets its own line:

```
functionality  -> exactly 1 functionality_check
roles          -> exactly 2 role_check(s)
    R1. address index
    R2. carries combinational index
relationships  -> exactly 6 relationship_check(s)
    L1. DERIVES_FROM -> bus_req_i.addr
    L2. SOURCES -> addr_ff
    L3. SELECTS -> mem_ram_b0
    L4. SELECTS -> mem_ram_b1
    L5. SELECTS -> mem_ram_b2
    L6. SELECTS -> mem_ram_b3
evidence       -> exactly 1 evidence_check
```

and for the elements that were being dropped:

```
    L1. ISOLATED -> (parser named NO target; return this check with "target": ""
                     and audit whether the ISOLATED claim itself holds)
```

Verified corpus-wide before running: **expected relationship checks 3 734, checklist lines
3 734, exact match** across all 1 689 elements.

**Fix 3 — token budget.** `max_output_tokens` 12 000 → **24 000**, ceiling 24 000 → **32 000**.
Measured across 142 cached calls: p50 5 851, p95 11 498, p99 12 361, max 13 706 — a 16 000
start would already have truncated none of them. The cap is not billed when unused, so this is
free for the ~99% of calls that fit, and it removes the waste run_009 measured at **$0.0989 of
$0.5334 (18.5%)** re-asking truncated answers — about **$6 of a $33 full pass**.

**Configuration.**

| | VP4 | VP5 |
|---|---|---|
| prompt sha | `8e7e3fb0e517685d` | `8246f9f9f46b3a8d` |
| relationship-check count | inferred from "(type,target) pairs" | **enumerated per element** |
| empty-target relationships | silently dropped, 2 runs in 3 | **explicit checklist line** |
| `max_output_tokens` | 12 000 | **24 000** |
| ceiling | 24 000 | **32 000** |
| `run_tag` | `vp4_full_context_01` | `vp5_full_pass_01` |

**Predictions, recorded before the run:**

| prediction | reasoning |
|---|---|
| `claim_coverage_incomplete` = **0** on neorv32_imem | the three dropped `ISOLATED` claims now have explicit checklist lines |
| `rel_pairs_lost_to_merging` = **0** | four `SELECTS` targets are four numbered lines |
| escalations fall to **0–1** | p99 is 12 361 against a 24 000 start |
| claim count rises 179 → **182** | the three recovered `ISOLATED` checks |
| verdict mix moves little otherwise | the checklist changes what is *returned*, not how the RTL is read |

#### Analysis-side defects fixed at the same time (none forces a re-run)

A preflight audit was run before committing to the full pass. **8 of its 9 agents died on a
session limit**, so its `confirmed: []` is an artifact, not a clean result; the one surviving
probe's findings were confirmed by hand against the corpus before anything was changed.

**A. `compare_runs.py` keyed the stability table on the bare element NAME — CRITICAL.**

```
507 of 1689 elements (30.0%) share a name with an element in another entity
clk_i occurs in 26 entities, rstn_i in 24, bus_req_i.addr in 8
```

The "READ THIS FIRST" table would have merged `neorv32_imem/clk_i` with `neorv32_uart/clk_i`
and 24 others, computing `shared` / `only A` / `only B` over a 1 355-key universe instead of
1 689. Two runs disagreeing completely about one module's `clk_i` while agreeing about
another's would have scored as agreeing. Harmless at one module; wrong at eighteen. Now keyed
on `element_id`, and every printed list carries `module/entity/element`.

**B. Corpus percentages are dominated by one entity.** `neorv32_bus` is **51.5%** of elements
and `neorv32_bus_io_switch` alone is **34.5%** — and its 582 elements are a few structural
shapes replicated 32 times, so one parser habit on `dev_NN_*` ports could move any corpus
number by ~30 points and read as a corpus-wide defect. Added `status_by_module.csv`,
`status_by_entity.csv` and `error_summary_by_module.json`; `error_summary()` now reports
`n_elements`, `errors_per_100_elements`, and names the largest module and its share.

**C. `flatten()` used two denominators once anything failed.** A failed element contributed
`functionality` and `evidence` rows but no `role`/`relationship` rows, because those were read
off an empty verification dict — silently removing ~4.5 of ~6.5 rows for that element from two
of the four fields. Now a failure emits one `PARSE_ERROR` row per **parser** claim, so all four
fields share the same element population.

**D. `pattern_report`'s `examples` column was not reproducible.** Results arrive in
thread-completion order across 4 workers, so the 5 examples were whichever elements finished
first — different on every run of the same data, and biased toward one module. Results are now
sorted by `(module, entity, element)` before sampling.

**E. `confidence` and `evidence_type` were missing from `claim_status.csv`.** V-1 established
confidence as the best predictor of whether a claim survives a repeat (**6% flip at ≥0.95
against 32% below 0.90**), yet the main analysis table could not filter on it without
re-parsing `per_file/*.json`. Both columns added.

**F. Duplicate claim keys would cross-product on a run-to-run join.** 11 elements legitimately
repeat a `(type, target)` pair; pandas pairs every copy in A against every copy in B and
invents transitions neither run produced. An occurrence index is now stamped in `flatten()` and
used in `compare_runs.py`.

**G. `save_run()` scanned `PARSED` linearly per result** — 1 689 × 1 689 ≈ 2.9M comparisons.
Replaced with a dict.

All seven are read-side. Every per-module table is recomputable from `claim_status.csv` and
`per_file/*.json` after the fact, so **none of them could have forced a re-run** — they were
fixed now so the pass's own output is usable without post-processing.

**Not audited, because those probes died with the session:** other claim shapes that might be
dropped beyond empty targets, 429/rate-limit behaviour across 1 689 calls at 4 workers, and the
memory footprint of retaining `raw_response` plus full RTL context for 1 689 rows. The first was
partly covered by hand (30 elements have no relationships — the checklist handles them; 11 have
duplicate pairs — covered by F). The other two remain open.

### VP5 · RESULT — `run_010`, 2026-08-22

27/27 parsed, **$0.5011**, 27 calls for 27 elements.

#### All five predictions correct

| prediction | outcome | |
|---|---|---|
| `claim_coverage_incomplete` = 0 | **0** (was 3) | ✓ |
| `rel_pairs_lost_to_merging` = 0 | **0** | ✓ |
| escalations fall to 0–1 | **0** (was 4) | ✓ |
| claim count 179 → 182 | **182** | ✓ |
| verdict mix moves little otherwise | SUPPORTED 53%→50%, PARTIALLY 44%→46%, CONTRADICTED 3%→4% | ✓ |

#### The counter was not taken on trust

`claim_coverage_incomplete` is computed by code written for this study, so a zero from it
proves nothing on its own. Three independent checks against the model's own saved output:

```
bus_req_i.priv    run_009: 0 checks -> run_010: 1   ISOLATED target='' SUPPORTED
bus_req_i.debug   run_009: 0 checks -> run_010: 1   ISOLATED target='' SUPPORTED
bus_rsp_o.err     run_009: 0 checks -> run_010: 1   ISOLATED target='' SUPPORTED

total claims       179 -> 182            (exactly the three recovered)
addr SELECTS       4 separate checks     (mem_ram_b0..b3, not merged)
```

The recovered checks carry `target: ""` exactly as the checklist instructed.

#### Escalation waste eliminated

| | run_009 (VP4) | run_010 (VP5) |
|---|---:|---:|
| `max_output_tokens` | 12 000 | 24 000 |
| calls for 27 elements | 31 | **27** |
| escalations | 4 | **0** |
| discarded answers | 4 | **0** |
| wasted USD | $0.0989 (18.5%) | **$0.0000** |
| total | $0.5334 | **$0.5011** |

One call per element, nothing thrown away. Raising a cap that is not billed when unused cost
6% less overall, not more.

#### Agreement rose sharply — as it should have

```
claim-level agreement   168/178 = 94.4%   (VP4 vs VP3 was 78.7%)
role field              50/50   = 100.0%
relationship            70/74   =  94.6%
```

VP5 changed how many checks come back, not how the RTL is read, so a large verdict shift would
have meant something unintended had changed. 94.4% against the 85.1% same-input replicate
baseline from V-1 is the expected shape: this pair differs only in claim *coverage*, while V-1's
pair differed by nothing at all and still moved 15%.

#### Error categories remain unstable at singleton size

| category | run_009 | run_010 | shared |
|---|---:|---:|---:|
| `CONDITIONAL_BEHAVIOR_ERROR` | 9 | 9 | **7** |
| `RELATIONSHIP_ERROR` | 6 | 8 | **6** |
| `EVIDENCE_ERROR` | 0 | 2 | 0 |
| `FUNCTIONALITY_ERROR` | 0 | 2 | 0 |
| `ROLE_ERROR` | 0 | 2 | 0 |
| `RESET_BEHAVIOR_ERROR` | 0 | 1 | 0 |
| `MISSING_BEHAVIOR` | 1 | 0 | 0 |

The two load-bearing categories held across a third prompt version:
`CONDITIONAL_BEHAVIOR_ERROR` 9/9 with 7 shared, `RELATIONSHIP_ERROR` 6 shared of 6 and 8.
Everything at 0–2 elements continues to appear and vanish between runs and remains unusable
per R3, regardless of prompt version.

**The instrument is ready for the full pass.** Every defect found since VP3 is fixed and
verified: coverage complete, no escalation waste, retrieval unbiased, provenance recorded,
analysis correct at multi-module scale.

---

**Superseded — VP5 ran as run_010. Validate on `neorv32_imem` before the full pass — VP5 changes both the
prompt and the payload, and an unvalidated prompt is not what a one-shot $33 run should use.

---

## 7c. FULL PASS — `run_011`, 2026-08-22. The answer.

VP5, all 1 689 elements, 17 modules, 26 entities. **$30.23**, ~4 h at 8 workers.

```
elements 1689 | parse_ok 1687 | api_errors 0 | harness_errors 0
escalations 0 | discarded answers 0 | wasted $0.00
coverage incomplete 2 (0.1%) | context_modes {FULL_ARCHITECTURE: 1689}
```

A mains outage mid-run forced a WiFi-to-mobile switch; the transient-retry path absorbed it
completely — **0 API errors**. Every instrument fix from VP3 onward held at 62× the scale it
was validated at.

### Parser correctness — 10 947 claims

| verdict | claims | share |
|---|---:|---:|
| `SUPPORTED` | 8 575 | **78.3%** |
| `PARTIALLY_SUPPORTED` | 2 022 | 18.5% |
| `CONTRADICTED` | 195 | **1.8%** |
| `NOT_ESTABLISHED` | 136 | 1.2% |
| `PARSE_ERROR` | 19 | 0.2% |

**`NOT_ESTABLISHED` fires at scale.** It was 0-of-182 on `neorv32_imem` and VP4's Finding 2
concluded there was nothing for it to fire on. Corpus-wide it is **136**. That conclusion was a
single-module artifact and is **withdrawn**. `INTERPRETATION` likewise: 0 on imem, **116**
corpus-wide, and `TRACED_RTL` 1 421 (13.0%).

By claim type:

| field | n | SUPPORTED | PARTIAL | CONTRADICTED |
|---|---:|---:|---:|---:|
| evidence | 1 689 | **95.1%** | 4.7% | 0.1% |
| role | 3 835 | 83.9% | 14.4% | 0.2% |
| relationship | 3 734 | 70.4% | 22.8% | **5.0%** |
| functionality | 1 689 | 66.4% | 32.0% | 0.1% |

Relationships are where the parser is wrong; evidence is where it is strongest.

### The result is not an artifact of one big module

`neorv32_bus` is 51.5% of elements, so the concentration risk was real. It is not realised:

```
neorv32_bus only   SUPPORTED 79.2%   PARTIAL 19.2%   CONTRA 1.0%
everything else    SUPPORTED 77.6%   PARTIAL 17.9%   CONTRA 2.5%
whole corpus       SUPPORTED 78.3%   PARTIAL 18.5%   CONTRA 1.8%
```

Per-module `SUPPORTED` ranges 50.0% (`neorv32_imem`) to 92.7% (`neorv32_boot_rom`). The pilot
module was the **worst** in the corpus — every estimate taken from it understated the parser.
`neorv32_cpu` is the one outlier on `NOT_ESTABLISHED` at 13.2% against ≤1% everywhere else.

### The dominant parser error, named

Of 195 contradicted claims, **187 are relationships**, and of those **111 are `SEQUENCES`**:

```
source element of the contradicted SEQUENCES claim:
    reset signal (rstn/rst)   106
    clock (clk)                 3
    other                       2

verifier evidence mentions a reset branch:  107 of 111

31.8% of EVERY SEQUENCES claim the parser made is contradicted
```

```
neorv32_bus/rstn_i SEQUENCES -> state
  "if (rstn_i = '0') then state <= S_IDLE; elsif rising_edge(clk_i) then state <= state_nxt
   -- reset drives state asynchronously, not via clock sequencing by rstn_i"
```

**The parser labels an asynchronous reset override as `SEQUENCES`.** This is precisely the
section-12 case the deterministic hint layer was built to surface, now measured across the
whole corpus. It is one rule, mechanically checkable, and worth a parser-prompt edit on its own.

Second cluster: `EXPORTS` 27, `CAPTURES` 17, `SOURCES` 16 — smaller and not yet characterised.

### Error categories at corpus scale

| category | instances | per 100 elements |
|---|---:|---:|
| `CONDITIONAL_BEHAVIOR_ERROR` | 551 | 32.6 |
| `RELATIONSHIP_ERROR` | 492 | 29.1 |
| `ROLE_ERROR` | 200 | 11.8 |
| `FUNCTIONALITY_ERROR` | 88 | 5.2 |
| `RELATIONSHIP_TARGET_ERROR` | 78 | 4.6 |

The two categories that survived every stability test since V-1 —
`CONDITIONAL_BEHAVIOR_ERROR` and `RELATIONSHIP_ERROR` — are also the two largest at scale.
Everything that looked like singleton noise on one module stayed small.

### How much of this can be trusted

Per V-1: `SUPPORTED` reproduces 98% of the time, `PARTIALLY_SUPPORTED` only 67%. Filtering on
`confidence >= 0.95` keeps **6 834 of 10 947 claims (62.4%)**, which reproduce ~94% of the time:

```
within the high-confidence subset:
  SUPPORTED 96.7% | CONTRADICTED 2.1% | PARTIALLY_SUPPORTED 1.0% | NOT_ESTABLISHED 0.2%
```

The `PARTIALLY_SUPPORTED` mass sits almost entirely **below** 0.95 confidence — consistent with
V-1's finding that it behaves as a low-confidence `SUPPORTED` rather than a distinct verdict.
Treat the 18.5% as "worth a look", not as established error. The 1.8% contradicted, and the
`SEQUENCES` cluster inside it, is the part that is solid.

---

### Queued behind V-1, not yet specified

- **V-2 · second module replicate.** Only after V-1's changed claims are read individually
  (R2). Module chosen for a different claim mix — not another memory.
- **V-3 · effort=medium replicate.** Would turn the run_004/006 comparison into a clean
  2×2 and separate the effort effect from noise. Cheaper per call, so it is the affordable way
  to get a second variance estimate.
- **VP4 · prompt revision.** Only if V-1 confirms coverage loss. Scope would be the
  one-relationship_check-per-(type,target)-pair instruction and `ISOLATED` handling — nothing
  else, so the sha change stays attributable.

---

## 7b. Budget escalation — measured 2026-08-21, during V-1

V-1 was started and interrupted partway (11 of 27 elements completed, all parsed ok,
2 escalations). During it the run printed:

```
[llm warn] incomplete (max_output_tokens) -> retrying at max_output_tokens=24000   (x2)
```

**That warning is the escalation mechanism working, not a fault.** It fires when the answer
did not fit in `max_output_tokens`, and re-asks at double the budget. run_006 did the same
thing 4 times and finished with `still_incomplete: 0`.

### What it costs, measured exactly on run_006

Total output billed 270 001 tokens; output inside the 27 kept results 222 001. The difference
is answers that were generated, billed, and thrown away:

| | |
|---|---:|
| discarded answers | 4 |
| discarded output tokens | 48 000 |
| tokens per discarded answer | 12 000 (exactly the cap) |
| **share of output spend wasted** | **17.8%** |
| wasted USD | $0.0960 of $0.5684 |

Extrapolated to the full 1 689-element pass at the same 14.8% escalation rate: **~250
escalations, ~3.0M wasted output tokens, ~$6.01** against a ~$35.6 projected run.

### `max_output_tokens` is a CAP, not a charge

Measured across 99 cached calls: at budget 12 000 the median output was 4 384 tokens and the
maximum 11 798; **nothing was ever billed at the cap.** Output distribution at effort=high:

```
p50 4384   p90 10009   p95 11482   p99 13300   max 13706
reasoning is 61% of output tokens on median, up to 90%; max reasoning seen 11 328
```

So 12 000 truncates roughly the top 5–15% of elements, and **raising the start budget costs
nothing for elements that fit.** 16 000–24 000 would remove nearly all escalation for free.

### Why it was NOT raised now

`max_output_tokens` is part of the cache key. Raising it would orphan every cached response —
including the 11 elements V-1 has already paid for — and, more importantly, **V-1 would stop
being a like-for-like repeat of run_006**, which ran at 12 000. That is precisely the mistake
that turned run_004 vs run_006 into an effort ablation instead of a replicate.

**Decision: V-1 finishes at 12 000. The budget is raised when the full pass is opened, and that
change is recorded as its own arm.** The measured distribution is now written into the CONFIG
cell next to the knob so the next choice is not a guess.

### One real defect found and fixed

`call_with_retry`'s docstring says a budget exhaustion "is a budget problem, not a model
failure, and must not be recorded as a parse error". The code did the opposite in the one case
the docstring is about. When a response is still incomplete at the ceiling, `budget < ceiling`
is false, so it returns with `error=None`; `validate_verification` then marks the truncated
JSON `parse_error`, and `if res["error"] is None:` **wrote it to the cache**. The element would
never be re-called on any later run — not even after raising the ceiling — and the parse-error
rate would carry a configuration fault as if it were a model observation.

run_006 recorded `still_incomplete: 0`, so this never fired in a saved run. It was live and
would have fired on the first element that needed more than 24 000.

Fixed: an incomplete-at-ceiling response is now treated like an API failure — not cached, and
reported with the reason. Also fixed: `retries` no longer counts escalations as retries (they
are different events — a retry means the API failed, an escalation means the answer did not
fit), and `run_verification` now prints the escalation waste in tokens and USD.

None of these fixes touch the cache key or the payload. Verified after patching: **11/27
elements still hit the cache**, so V-1 resumes free and only the remaining 16 are called.

---

### Two further defects, found by a follow-up audit

**A. The manifest billed the whole kernel session, not the run.** `USAGE` is module-global and
never reset -- correct, it is the session total -- but `save_run` wrote `cost(cfg)`, which reads
*all* of `USAGE`, into the manifest as that run's cost. Run the STAGE cell twice in one kernel
and the second manifest reports the sum of both runs, attributed entirely to the second. Every
number derived from it inherits the error: `usd_per_element`, the full-run projection, the
escalation-waste figure.

This has not corrupted a saved run yet -- run_006's 31 calls for 27 elements is exactly
27 + 4 escalations, so no contamination -- but V-1 is being **resumed after an interruption**,
which is precisely the second-run-in-one-kernel case.

Fixed: `run_verification` marks `len(USAGE)` on entry and publishes its own slice as
`LAST_RUN_USAGE`; `save_run` bills against that and additionally records
`usage_and_cost_session_cumulative` so the session total is still visible.

**B. One bad element could abort the whole pass.** `run_verification` called `f.result()`
unguarded inside the `as_completed` loop. Any exception raised inside a worker -- not an API
error, those are caught, but a genuine bug -- would propagate out and discard every result
collected so far, leaving `RESULTS` unassigned. No money is lost (responses are cached before
`verify_element` returns) but the pass dies. Fixed: the element is recorded as
`parse_status: "harness_error"` and the pass continues.

**C. The manifest could not tell three failure kinds apart.** `elements_verified - parse_ok`
lumped malformed JSON, API failures and crashed workers together. Now recorded separately as
`parse_errors`, `api_errors`, `harness_errors`.

**D. `escalation_waste` undercounted.** It priced only the discarded answer's output tokens;
the discarded call also billed its input. Now counted. For run_006 the correction is small --
input was 98.5% cached (101 760 of 103 321 tokens) -- so the waste stays $0.0960, not the
$0.1007 an unverified audit probe reported by pricing discarded input at the uncached rate.

### Status of that audit

The follow-up audit ran as a 29-agent fan-out and **23 of its agents died on a session limit**,
including every adversarial-verification agent. Its `confirmed: []` result is therefore an
artifact of the failures, **not** a finding that nothing is wrong. The four defects above were
taken from surviving probes as *leads* and each was then confirmed by hand against the code
before being fixed. Unverified probe claims not independently confirmed are not recorded here.

One surviving probe contributed a sharper justification for the caching fix than the original:
a cache entry should be a pure function of the inputs in `_cache_key`. An incomplete-at-ceiling
row is a function of `max_output_tokens_ceiling`, which is in **none** of the hashed inputs --
change that knob and the same key yields a different outcome. The cached value is not
attributable to any recorded input, and it is not the model's answer at all: the model never
reached a verdict, it was cut off. Caching it records "the verifier said nothing parseable"
when the truth is "we hung up on the verifier."

None of these fixes touch the cache key or the payload. Re-verified after patching:
**11/27 elements still hit the cache.**

---

## 8. How a comparison is run

```bash
python compare_runs.py run_006 run_007
```

`compare_runs.py` prints everything section 4 requires and no verdict. Read the
**ERROR-TYPE STABILITY** table first -- it answers R3 ("did the finding I was about to act on
stay on the same elements?"). The agreement percentages above it are context, not the decision.

Reading two finished runs to compare them is analysis, not evidence. Nothing it reads is fed
back into a payload, so it does not touch R6.

Runs that predate the claim-coverage instrumentation have their coverage **recomputed** from
the parser's claims and labelled as such. It never reports 0 for a run where coverage was
simply not measured.

---

## 9. Housekeeping recorded at open

- Backup of the pre-patch notebook: `notebooks/parser_verifier.BACKUP-20260821-205454.ipynb`.
- `_cache/` at the folder root (61 files) is an orphan from an earlier `results_root`; the live
  cache is `verification_results/_cache/` (88). Nothing reads the orphan.
- `results/` (7 empty directories) belongs to the **asset-triage ablation** notebook, which has
  never been run. Not part of this study.
- `README.md` documents only the triage pipeline and does not mention the verifier at all.
