# Parser ablation log

The research record for the **parse stage** — the LLM pass that annotates RTL elements.
Companion to `VERIFIER_ABLATION_LOG.md`, which covers the audit stage.

Started 2026-09-01, at prompt `fe0e47d27646`. Everything before that entry is reconstructed
from the code, the prompt text and the run artifacts; entries from §4 onward are recorded as
the change is made.

---

## 1. What the stage is

`rtl_parse` extracts ports and signals by regex and expands record types into fields. That
set is **closed**: the model annotates it and may not add to it, drop from it or reorder it.
`verify_against_cache` raises if it ever does.

One call per entity per batch (128 combined ports and signals), each carrying that entity's
own scoped source. Six threads. The calls share no state, so concurrency changes wall clock
and nothing else; `_assemble` rebuilds each record in mechanical order, so the file does not
depend on which call returned first.

**The governing principle.** Membership errors *raise*; content errors are *counted, never
repaired*. A repaired record hides the rate that tells you whether the prompt is working —
the empty slot is the measurement.

## 2. Version history

| Version | Prompt sha | Edge types | Output dir | Note |
|---|---|---|---|---|
| v3 | — | 14 | `data/parsed_v3_tuning18` | the run all current metrics are computed on |
| v4 | `21c3d3e71ecd` | 15 | `parsed_v4_tuning18` | `RESETS` split from `SEQUENCES`; `guard` required |
| v5 | `e6c2de72186e` | 14 | `parsed_v5_tuning18` | ran 2026-09-05; results and insights in section 3B |
| v6 | `d2569ebb9165` | 14 | `parsed_v6_tuning18` | shapes on all 14; ran 2026-09-05, net regression — section 3C |
| **v7** | **`2e6f9eff2ed2`** | 14 | `parsed_v7_tuning18` | shapes kept on REFLECTS/CONSTRAINS/OVERRIDES only; PORT_MAP named |

**Never mix directories in one metric.** From v5, `CARRIES` points the opposite way from v3,
so a figure spanning both compares two different things while looking consistent.

## 3. What the v3 run measured

All figures re-derived in-session on `data/parsed_v3_tuning18` (1,689 elements, 18 modules).

| Quantity | Value | Denominator |
|---|---|---|
| Governing-edge coverage | 51% | elements appearing in a condition (regex lower bound) |
| Site-class recall, all roles | 63% | 2,709 element/role pairs |
| — tested in a condition | 49% | 351 |
| — used as a case selector | 43% | 23 |
| — used as an array index | 14% | 29 |
| — is an output port | 54% | 671 |
| Value couplings recorded at both ends | 77% | 562 assignment pairs |
| Control couplings recorded at both ends | **2%** | 118 mux-condition pairs |
| Edges with the arrow reversed | 67 | 1,692 direction-decidable claims |
| Pairs carrying one edge type both ways | 67 | — |

The 2% is the finding the v5 vocabulary work is built on: control flow had no receiving-end
edge, so a governed element had no way to record that it was governed.

## 3B. What the v5 run measured — the baseline v6 is judged against

Run 2026-09-05 into `parsed_v5_tuning18`, stamp `v5/e6c2de72186e/14`. Every figure below was
re-derived in session from those files on 2026-09-05, after the run, by `report()`,
`audit_dead_ends()`, `audit_cross_record()` and `diagnose_v5.py`. Nothing here is carried
from the run's own console output.

### 3B.1 The census

1 689 elements across 18 modules — the closed set held exactly, none added, none dropped.
2 876 edges, against 2 464 in v3.

| Edge | Count | Share |
|---|---|---|
| `DERIVES_FROM` | 632 | 22.0% |
| `SOURCES` | 630 | 21.9% |
| `EXPORTS` | 603 | 21.0% |
| `CAPTURES` | 239 | 8.3% |
| `GATES` | 225 | 7.8% |
| `GOVERNED_BY` | 171 | 5.9% |
| `ISOLATED` | 141 | 4.9% |
| `CARRIES` | 106 | 3.7% |
| `RESETS` | 53 | 1.8% |
| `SELECTS` | 37 | 1.3% |
| `SEQUENCES` | 34 | 1.2% |
| `CONSTRAINS` | **4** | 0.1% |
| `GATED_BY` | **1** | invented; not in `EDGE_TYPES` |
| `REFLECTS` | **0** | — |
| `OVERRIDES` | **0** | — |

### 3B.2 What passed

| Measure | v5 | Note |
|---|---|---|
| Verdict/hedging words | 13/1 689 = **0.8%** | the gate; 14 word hits |
| Guard coverage | 314/319 = **98%** | governing edges carrying their guard |
| EXPORTS coverage | 603/671 = **90%** | was 54% in v3 |
| Control reciprocity | 326/757 = **43%** | was 2% in v3 — the `GOVERNED_BY` result |
| Value reciprocity | 787/1 306 = 60% | |
| Overall reciprocity | 1 113/2 063 = 54% | |
| Same type written both ways | 60 pairs | v3 was 61 — flat, so `GOVERNED_BY` is not reflexive stamping |
| `UNRESOLVED` markers | **0** | the driver never had to drop a record's edges |

The control-reciprocity move from 2% to 43% while the both-ways count stayed flat is the
single clearest win in the run, and it passed its own falsification test: had `GOVERNED_BY`
been stamped reflexively, the both-ways count would have climbed with it.

### 3B.3 What failed

| Measure | v5 | Note |
|---|---|---|
| Governing coverage | 190/338 = **56%** | v3 was 51%; the sweep did not land |
| `REFLECTS` / `OVERRIDES` | **0 / 0** | the two shape-defined receiving/driving edges |
| `CONSTRAINS` | 4 | the third shape-defined edge |
| ISOLATED claims wrong | 20/141 = **14%** | 16 record bases + 4 plain signals |
| Elements with an EMPTY relationship list | **43** | distinct from claiming ISOLATED |
| `handling` violations in `_issues` | 161 | present-when-dotted rule |
| Invented edge type | `GATED_BY` × 1 | the English mirror of `GATES` |

The 184 elements `report()` calls isolated decompose as **141 ISOLATED claims + 43 empty
relationship lists**. These are not the same failure. An ISOLATED claim is an assertion the
source can contradict; an empty list is the model declining to answer, and only
`no_relationship` records it.

### 3B.4 The insights, in the order they were established

**1. The model finds the sites and mislabels them.** Of 300 elements appearing in a governing
condition: 62% got a governing edge, 23% got a VALUE edge instead, 8% something else, 5% were
claimed ISOLATED, and **2% got no edge at all**. Site recall is near total. The entire
governing gap is in the labelling step, not in the model's ability to see the construct. This
rules out "make the sweep more insistent" as a fix and rules in "make the distinctions
decidable".

**2. Prose states a positional fact well and a shape badly.** Every edge type above 100 is
defined by ONE positional fact — right-hand side, left-hand side, in a condition, at a clock
edge, declared an output. Every type at or near zero is defined by a MULTI-PART SHAPE. That
split is the whole explanation for `REFLECTS` 0, `OVERRIDES` 0 and `CONSTRAINS` 4, and it is
what §4.20's schematics are aimed at.

**3. `REFLECTS` lost to `DERIVES_FROM` specifically.** Of 44 sites in the corpus matching the
`REFLECTS` shape, 41 (**93%**) were given `DERIVES_FROM` or `CAPTURES`, 1 `GOVERNED_BY`, 2
something else, and 0 `REFLECTS`. The model was not confused about what `REFLECTS` means; it
did not recognise an instance. That is under-binding, the characteristic failure of a purely
structural prompt, and the reason the fix is a schematic rather than more prose.

**4. A rule stated in the prompt and never checked in code stays violated.** The `ISOLATED`
definition has said since v5 that an element coupled through its fields is not isolated. 16
record bases were claimed ISOLATED anyway. The fix that worked was a validator (§4.21), not
a rewording.

**5. Dead logic is absent; missed couplings are not.** `audit_dead_ends()` finds **0 confirmed
dead ends** in NEORV32 — validated by a positive control, a synthetic written-never-read
signal, which it catches. But **42** elements had no consuming edge in the parse and ARE read
in the source. The zero is a fact about the design; the 42 is a fact about the parse, and it
is a recall finding the vocabulary cannot express on its own.

**6. Two independent methods agreeing is worth more than either alone.** The 16 wrongly
ISOLATED record bases were found twice — once by opening the RTL, once by reading only the
parse — and the two sets are element-for-element identical. Where a finding can be reached
two ways, reach it two ways.

### 3B.5 What v5 does NOT establish

- Whether the schematics help. That is what the v6 run measures.
- Whether `OVERRIDES` is reachable at all. Its boundary against `GATES` rests on which arm
  counts as "ordinary", which has no syntactic marker (§4.19-H). A zero here may be a
  definition problem rather than a recognition problem, and the v6 run is the test.
- Anything about assets. This stage reports mechanism; nothing above is an asset judgement.

## 3C. What the v6 run measured — the schematics, and why they were narrowed

Run 2026-09-05 into `parsed_v6_tuning18`, stamp `v6/d2569ebb9165/14`. 18 files, 1 689
elements — the closed set held. All figures re-derived in session from those files.

**Verdict: a net regression. Three of the five falsifiers in §4.20 failed.**

| Falsifier (§4.20) | Result | |
|---|---|---|
| `REFLECTS` > 0, share above 0% | 0 -> 9 edges; 0% -> 9% of its 44 sites | pass, barely |
| `OVERRIDES` > 0, `CONSTRAINS` > 4 | 0 -> 3, 4 -> 6 | pass |
| `DERIVES_FROM` falls by ~the `REFLECTS` gain, no more | **rose +10** | **fail** |
| `unknown_edge` and `unresolved_target` flat | `unknown_edge` **1 -> 7** | **fail** |
| Total edges not falling | **2 876 -> 2 714, −162** | **fail** |

### 3C.1 Edge census, v5 -> v6

    SOURCES       630 ->  660   +30      RESETS         53 ->  50    -3
    DERIVES_FROM  632 ->  642   +10      CARRIES       106 ->  43   -63
    EXPORTS       603 ->  473  -130      SELECTS        37 ->  37     0
    CAPTURES      239 ->  218   -21      SEQUENCES      34 ->  32    -2
    GATES         225 ->  186   -39      CONSTRAINS      4 ->   6    +2
    GOVERNED_BY   171 ->  209   +38      REFLECTS        0 ->   9    +9
    ISOLATED      141 ->  139    -2      OVERRIDES       0 ->   3    +3
                                         PORT_MAP        0 ->   5   invented
                                         RESET_BRANCH    0 ->   2   invented
                                         GATED_BY        1 ->   0
    TOTAL        2876 -> 2714  −162

### 3C.2 What got better

| | v5 | v6 |
|---|---|---|
| Contradictory both-ways pairs | 60 | **13** |
| `no_relationship` (empty answers) | 43 | **22** |
| `unresolved_target` | 8 | 3 |
| Whole output ports missing EXPORTS | 3 | **0** |
| Verdict/hedging words | 0.8% | 0.7% |
| ISOLATED contradicted | 20/141 = 14% | 18/139 = 13% |
| Control reciprocity | 43% | 45% |

The both-ways collapse from 60 pairs to 13 is the largest single gain of the run and is not
undone by the narrowing in §4.24 — it came from the definitions, not from the shapes.

### 3C.3 The EXPORTS regression, traced to one line I wrote

    v5:  65/570 output-port FIELDS missing EXPORTS,   3/101 whole ports missing
    v6: 198/570 fields missing,                       0/101 whole ports missing

Whole ports got BETTER (3 -> 0). The entire −130 is on record fields. The shape was:

    SHAPE   port ( <elem> : out ... ) ;  and something inside drives <elem>.

A field such as `<rec>.<f>` never appears in a port clause — only the whole record does.
The first reading of this was that the shape could not match a field at all; that is wrong,
because 372 of 570 fields still got the edge. The shape made the model HESITATE on fields
rather than exclude them. Either way the line is the cause, and it is a schematic narrowing
a rule the prose states broadly.

### 3C.4 The invented types are the two-vocabulary confusion

    neorv32_bus/state    RESET_BRANCH -> ['state']
    neorv32_trng/clk_i   PORT_MAP     -> ['neoTRNG_cell_inst.clk_i']   (5 of these)

Both are SITE names from `_SITES` used as edge types — the confusion `_SITES` and STEP 2
explicitly warn against. Making shapes salient pushed the model toward the other
shape-shaped vocabulary. `RESET_BRANCH` is pure confusion: STEP 2b already maps it to
`RESETS`. `PORT_MAP` was different — it was **the one site in the STEP 2b sweep table with no
edge name attached**, so the model had a real coupling and nothing to call it.

It is NOT a recall gap. Instance-port couplings were recorded all along:

    v5: 296 edges point at an instance.port  {SOURCES 131, DERIVES_FROM 134, SEQUENCES 10, ...}
    v6: 246 edges                            {SOURCES 157, DERIVES_FROM 54, PORT_MAP 5, ...}

### 3C.5 Half the governing-coverage fall is bookkeeping, not loss

`GATES` fell 39 and `GOVERNED_BY` rose 38 — very nearly a swap. `governing_coverage` counts
only the DRIVING end, so a coupling moved to the receiving end reads as a loss. Measured
counting EITHER end, over the same 300 elements that appear in a condition:

                                          v5     v6
      governing edge on the element      62%    54%    −8
      OR named by someone's GOVERNED_BY  63%    59%    −4

So about half the headline regression is the same coupling recorded at the other end. The
real loss is 4 points, roughly 12 elements. This correction matters: reading only
`governing_coverage` would have overstated the damage twofold, and it is the reason §4.24
is described as a scope reduction rather than as a dilution fix.

### 3C.6 `REFLECTS` barely moved, and the likely reason is not the shape

Of the 44 sites matching the `REFLECTS` shape, **4** got `REFLECTS` and **40** still got
`DERIVES_FROM`/`CAPTURES`. Total `REFLECTS` edges is 9, so 5 landed at sites the shape check
does not identify — unverified in either direction.

The clearest failing case is a concurrent conditional assignment where every arm is a
literal and the condition compares a target. In that construct **the condition is textually
to the RIGHT of the assignment operator**. `DERIVES_FROM`'s exclusion says a condition-only
target "is not on the right-hand side" — which is false as written for this construct. The
model reads the condition as part of the right-hand expression and writes `DERIVES_FROM`,
which is exactly what it did 40 times.

If that reading is correct, no schematic can fix `REFLECTS`, because the competing definition
gives the model a true-sounding reason to prefer it. **Raised as a prose-accuracy question and
NOT changed**, because it alters a definition validated in §4.1 and §4.15.

## 4. Changes

### 4.1 Definitions rewritten and validated — 2026-09-01

Fourteen edge definitions rewritten. Full text in `defs_v5.txt`. Derivation and literature
support in `edge_definition_derivation.xlsx` and `edge_definition_literature.xlsx`.

Validated by four independent readers applying the definitions to 22 real RTL sites chosen to
stress every boundary. Three rounds:

| Round | Agreement | Trouble reported |
|---|---|---|
| 1 — as drafted | 77% | 5 overlaps, 1 gap |
| 2 — precedence ladders added | 100% | 1 overlap (self-reference) |
| 3 — self-reference clause added | 22/22 on type | none |

The two sites that differ in round 3 differ only in whether the target was written
`cmp_lt` or `cmp_lt(r)`. That exposed a real omission — the de-indexing rule lived in the
prompt body but not in the definitions block — now fixed in `defs_v5.txt`.

**Applied to `prompts_parse_v3.py` in §4.7.** The two open decisions — `REFLECTS` becoming
mechanical, `OVERRIDES` being kept — went in as the validated file has them; see §4.7.

### 4.2 `function` field removed — 2026-09-01

**What.** The `function` field is gone from the three output schemas, from `THE FIELDS`, from
`_MAX`, from the banned-word scan, from record assembly and from `parse_fingerprint`.

**Why.** It restates the identifier rather than the behaviour. From `neorv32_bus`:

```
a_req_i.addr   function: "A request address"
a_req_i.ben    function: "A byte-enable bus"
a_req_i.priv   function: "A privilege flag"
```

It is also the field where name-derived content appeared where the source held none:
`funct7_i` has zero occurrences in the CFU architecture, and came back as
`"unused function field"` — a characterisation only the name could supply.

And it was the only emitted field the verifier never audited. Its checks are
`functionality_check`, `role_checks`, `relationship_checks`, `evidence_check`; there is no
`function_check`. So it was unmeasured output on 1,689 elements.

**A correction recorded against myself.** An earlier reading of a word-overlap test —
5% of `function` values share every word with `functionality` — was reported as evidence the
two fields carry different content. That was the wrong test. The overlap is low because
`function` paraphrases the *name* while `functionality` describes the *behaviour*; low
overlap and zero added information are compatible. The user identified this from
`neorv32_bus.json` directly.

**What would falsify the change.** If `functionality` compliance drops after the next parse,
the short label was doing work as a warm-up for the longer field. Read `over_length` and
`no_relationship` against the v3 baseline.

### 4.3 `handling` field added — 2026-09-01

**What.** A new field, required on every element whose name contains a dot and omitted on
every other, holding exactly one of `ORIGINATES`, `CONSUMES`, `FORWARDS`. STEP 2c keeps its
explanation of how to decide; only the answer moved out of `functionality` prose into a
field.

**Why.** The prose instruction was not working:

```
record/struct fields (dotted names):            1245
  functionality naming one of the three words:   262   (21%)
  which word: FORWARDS 259, CONSUMES 5, ORIGINATES 2
```

79% ignored it, and of those that complied 97% said FORWARDS — in a design where record
fields are tested in conditions constantly. Five `CONSUMES` in the whole corpus is not a
classification, it is a default.

**Why a field rather than a checked keyword.** Requiring the word in prose would take
compliance to ~100% and `FORWARDS` to ~95%, because `FORWARDS` is the cheap answer. That
measures word presence, not classification. As a field it is an enum, it does not compete for
the 45-word `functionality` budget, its distribution is readable at a glance, and — the real
reason — **`FORWARDS` is falsifiable from the source.** If the field appears anywhere other
than a whole-record copy, `FORWARDS` is false. That check is mechanical and costs no API
calls. It is not yet written; see §6.

**Guard.** `check_annotation` counts `handling_missing_or_bad` when a dotted name lacks the
field or carries a value outside the enum, and `handling_on_non_field` when a non-dotted
element carries one. Tested against a deliberately bad stub: missing, out-of-enum and stray
all fire, correct element named in each.

**Budget.** Measured on the v3 output, the two field changes together are net negative on
output tokens, so headroom rises rather than falls:

```
`function` text removed         :  42,983 chars
its JSON key removed            :  25,335 chars
`handling` added (1245 dotted)  :  31,125 chars
NET                             :  37,193 chars saved  (~9,298 output tokens)
```

**What would falsify it.** If `handling` comes back above ~90% `FORWARDS`, the field has
inherited the prose version's problem and the decision is not being made. Read the
distribution before reading anything else.

### 4.4 Name-agreement clause removed — 2026-09-01

**What.** In `WHAT YOU MUST NOT DO`, the instruction now reads: derive with the identifier
treated as a meaningless token; the name is not evidence and belongs in no field; where the
source shows nothing beyond the declaration, write that the element is unused and stop.

Removed: *"then check whether the name agrees. If it agrees, the name has added nothing…
If it disagrees, the source wins and the disagreement is worth stating."*

**Why.** The clause fired **zero times in 1,689 elements** — no annotation anywhere flags a
name/behaviour disagreement. Tested against three CFU ports with zero architecture
occurrences: the derivation was correct (all three called unused) but no disagreement was
noted, and the name leaked into the description anyway.

It is also unverifiable by construction. The output cannot show whether the name was
consulted before or after the conclusion was formed, so the ordering the clause depends on
cannot be audited. And it explicitly re-admits the identifier after banning it, which is
where the leak occurs.

Misleading-name detection is worth having, but downstream, where the parse's description can
be compared against the name mechanically.

**What would falsify it.** If elements whose profile is `DECL`-only start carrying
name-derived detail at a higher rate, the added sentence did not land. Grep the next parse's
unused elements for words that appear only in their own identifiers.

### 4.5 `bits` capped — 2026-09-01

`_MAX["bits"] = 25`. `bits` now carries verbatim source expressions, so it needed the cap
`guard` already had. The spec also changed: quote the indexed or joined expression exactly as
the source writes it, **including the name it belongs to**, because a bare range does not say
which end it qualifies. Never compute a bit position the source does not write — a
concatenation offset is arithmetic the model gets wrong and is a numeric emission besides.

### 4.6 The driver stops asserting ISOLATED — 2026-09-01

**What.** `normalize_record`'s fallback was `out or [{"type": "ISOLATED", "targets": []}]`.
It now emits `UNRESOLVED`, counts `all_edges_dropped`, and `check_annotation` puts it in
`driver_unresolved` rather than `unknown_edge`. `audit_isolated` skips elements carrying a
driver marker.

**Why `UNRESOLVED` is the right name, checked rather than assumed.** It collides with no
edge type and no site name. Empty relationship lists already occur in the v3 output — 30 of
1,689 — so downstream already tolerates an element with no usable edge; the marker is
strictly more informative than the empty list it could have been, because it distinguishes
"the model returned nothing" from "the model returned edges and normalisation dropped them
all". Those have different fixes. And it is kept out of `unknown_edge` deliberately: that
counter measures the annotator, and mixing driver output into it would make the prompt look
worse than it is.

**Why it mattered.** `ISOLATED` is a positive claim — *no coupling can be substantiated
anywhere in this entity*. The fallback turned a parse failure into that claim, produced by
the driver, indistinguishable in the file from one the model made, and fed it to
`audit_isolated`, the check built to catch exactly that claim. It was the only place in the
file where a repair path asserted a finding.

**Unrecoverable for v3.** 110 of 1,689 elements carry a bare `ISOLATED` and there is no
`_raw/` directory for that output, so the split between model and fallback cannot be
recovered. Every `ISOLATED` figure quoted from v3 is an upper bound.

### 4.7 EDGE_TYPES and GOVERNING_EDGES moved to v5 — 2026-09-01

**What.** `EDGE_TYPES` is now the validated fourteen. `SLICES` and `AGGREGATES` retired,
`GOVERNED_BY` added. `_EDGES` replaced with the v5 definitions and both precedence ladders —
the constant and the prose cannot move apart, because `audit()` asserts every `EDGE_TYPES`
member appears in the text.

`GOVERNING_EDGES` gained `RESETS` and is now the DRIVING-end control set used by
`governing_coverage`. A second tuple, `GUARD_REQUIRED`, adds `GOVERNED_BY` and is what the
guard check uses. **They are deliberately different.** Counting `GOVERNED_BY` toward
governing coverage would let a governed element look like a governing one, which is the
opposite of what that metric exists to measure.

**Why the retirements.** `SLICES` was redundant with `SOURCES` plus `bits` and had the worst
direction record in the set — 12 of 39 reversed, because "X slices Y" means the opposite of
"X is a slice of Y". 235 of 244 `AGGREGATES` claims merely restated that a record contains
its own fields, which the element naming already says.

**Two decisions taken as validated rather than re-opened.** `REFLECTS` becomes mechanical and
grows from 2 uses to roughly 44 — address decodes and comparison results. `OVERRIDES` is kept
despite ending up with one or two genuine instances corpus-wide once `RESETS` takes the
reset cases. Both were flagged as the user's call and neither was answered; the file that
passed validation keeps them, so that is what was implemented. Either can be reversed.

### 4.8 Version stamp, and refusing to mix — 2026-09-01

Every output file now carries `_version` = prompt sha, edge-set name, edge count.
`assert_one_version()` **raises** on a directory holding more than one stamp, and an
unstamped file counts as its own version rather than silently matching. `report()` calls it
before printing anything; `compare_parses()` prints both versions and warns loudly when they
differ.

This is the `verify_against_cache` posture applied to comparability: `CARRIES` reverses
direction between v3 and v5, so a figure spanning both compares two different things while
looking consistent — and nothing downstream would announce it.

### 4.9 STEP 2b generalised to every site — 2026-09-01

**What.** STEP 2b swept `COND`, `CASE_SEL` and `ENABLE_TERM` only. It now walks the whole
profile site by site, and each site names the edge it should produce — including
`RESET_BRANCH` → `RESETS`, `SENS` → `SEQUENCES`, `LHS_SEQ` → `CAPTURES`, `LHS_COMB` →
`DERIVES_FROM` or `REFLECTS`, `RHS` → `SOURCES` or `CARRIES`, `PORT_MAP` → `instance.port`,
and a `DECL`-only profile → `ISOLATED`. `audit()` asserts eight of the site names appear
inside the STEP 2b block, so a future edit cannot quietly narrow it again.

**Why.** Conditions land at 49% recall and the other nine sites had no sweep at all — array
index 14%, case selector 43%. Largest expected recall gain of any change here, and the most
likely to regress something, which is why it is the only change in this batch that should be
read on its own.

**What would falsify it.** If site-class recall rises but `CONSTRAINS` and `OVERRIDES`
inflate against their v3 counts, the sweep is producing edges to satisfy the checklist rather
than because the site is there.

### 4.10 Are the occurrence sites complete? — verified, 2026-09-01

**Question asked:** do the fifteen `_SITES` cover every place an element can appear in RTL?

**Answer: yes, for the closed set.** Constructs present in the 18 files were enumerated with
comments masked, then each was checked against the site list. Everything resolves:
aggregates → `CONCAT`; attributes such as `'left` and `'range` → `RHS`; function and type
conversions → `RHS`; `for ... generate` and width expressions → `GEN_COND`; `=> open` and
generic maps carry no element coupling; case CHOICES are always literals or enumeration
literals, never signals, so a choice can never carry an edge.

**One error corrected in the course of checking.** An initial count reported 412 variable
assignments (`:=`) as a coverage gap. That regex matched `:=` in declarations. The real count
inside process bodies is **13**. And it does not matter at all, because
`rtl_parse.parse_signals` scans the architecture declarative region and process-local
variables never enter the closed set — `tmp_v`, `mode_v` and `char_v` are absent from all
1,689 elements. No annotated element is ever a variable, so no site is needed for one.

### 4.11 Reciprocity and EXPORTS checks — 2026-09-01

**What.** Two functions, both mechanical and both wired into `report()`.

`reciprocity_coverage()` asks whether the other end of each coupling records it. A `MIRROR`
table taken from the v5 definitions says which edges can stand as the counterpart of which;
`SEQUENCES` is deliberately absent, because the definitions say a register does not record its
own clock this way, and `EXPORTS`/`ISOLATED` carry no target to mirror. It also counts the
contradiction the v3 parse carried: the SAME edge type written in BOTH directions for one
pair. Pairs sharing a base name are excluded — a record and its own field cannot be told apart
by name matching.

`export_coverage()` counts output ports carrying `EXPORTS`. Decidable from the port list
alone, so a miss is a recall failure with no interpretation in it.

**Baseline, run against the v3 parse:**

```
RECIPROCITY  does the other end record the coupling?
   value     755/1564    48%   mirrored
   control     0/463      0%   mirrored
   all       755/2027    37%
   same type written BOTH ways: 61 pair(s)

EXPORTS COVERAGE  364/671 = 54% of output ports carry it
```

**Read the denominator carefully.** This is *per edge the parse wrote*, not per coupling the
RTL has. The earlier statement-level figures — value 77%, control 2% — counted assignment
pairs found in the source (562 value, 118 mux-condition). Both are legitimate and they answer
different questions. This one is the right shape for a gate because it needs no RTL and runs
on any parse directory.

Control reads 0%, not 2%, and that is correct: `GOVERNED_BY` did not exist in v3, so no
control edge could have had a mirror. The earlier 2% came from control couplings that
happened to be recorded on the other end using a value-flow word — the mislabelling measured
separately in §3.

`export_coverage` reproduces the 54% found independently by the site-recall script, on the
same denominator of 671. Two implementations agreeing is the only reason to trust either.

**What would falsify the change.** If control reciprocity rises but the same-type-both-ways
count rises with it, the model is emitting `GOVERNED_BY` as a reflex rather than as a mirror.
Watch the two together; neither means anything alone.

### 4.12 Pre-flight before the v5 run — 2026-09-01

A dry run with the model stubbed, exercising every path that runs before and after the call
on real modules. It found four defects, three of which would have surfaced only after the
calls were paid for.

1. **Crash at assembly.** `handling_missing_or_bad` and `handling_on_non_field` were added to
   `check_annotation` but never to the issue-key tuples. The first dotted element would have
   raised `KeyError` in `_assemble` — after the whole module's calls had completed.
2. **`handling` was dropped on the floor.** `_assemble` rebuilt each record without copying
   the field through, so the model's answer would have been discarded and then reported
   missing on all 1,245 dotted elements. Now carried through, and only where the model sent
   one, so a non-dotted element does not acquire an empty field the guard would flag.
3. **`OUT_DIR` still said `parsed_v4_tuning18`.** A v5 parse writing into a directory named
   v4, one week after adding a version stamp whose whole purpose is to stop that confusion.
   Now `parsed_v5_tuning18`.
4. **`rtl_dir` defaulted to a directory that does not exist here.** The working copy keeps
   its sources under `data/RTL_data`; the default said `RTL_data`. `governing_coverage`
   returned silently, so **the primary metric would simply not have printed**, and
   `audit_isolated` skipped every file while reporting "0 total, 0 contradicted (0%)" — which
   reads like a clean result and is a scan that never happened. `RTL_DIR` is now resolved once
   at import, and both functions say so out loud when the source is absent. `audit_isolated`
   also counts and reports files it could not read.

The fourth is the one worth remembering. A metric that fails loudly costs you a re-run; a
metric that fails silently costs you a wrong conclusion.

### 4.13 The v5 run — 2026-09-05

18 modules, **1,689 elements, identical to v3**, one version stamp, `verify_against_cache`
did not raise. Edges 2,464 → 2,876.

| Metric | v3 | v5 | Verdict |
|---|---|---|---|
| `handling` FORWARDS share | 97% (prose) | **48%** | passed; threshold was 90% |
| control couplings mirrored | 0% | **43%** | `GOVERNED_BY` works |
| same type written both ways | 61 | 60 | flat — so NOT reflexive stamping |
| `EXPORTS` coverage | 54% | **90%** | passed |
| governing-edge coverage | 51% | **56%** | mostly failed |
| `ISOLATED` claims / contradicted | 110 / 6 | **141 / 20** | regressed |
| guard coverage | — | 98% | passed |
| banned words | — | 13 elements, 0.8% | acceptable |

Edge moves: `EXPORTS` +173, `DERIVES_FROM` +415, `GOVERNED_BY` +171, `RESETS` +53,
`GATES` +76; `CARRIES` −354 (now source-side and strict), `SEQUENCES` −42 (reset split out),
`SLICES`/`AGGREGATES` retired to 0. One invented type, `GATED_BY`, caught as `unknown_edge`.

**Predictions, scored honestly.** `handling` and `GOVERNED_BY`: correct, including the
falsification test that both-ways would rise if the mirror were reflexive — it did not.
**`REFLECTS` predicted to grow 2 → ~44. It came back 0. That prediction was wrong.**
`CONSTRAINS` 30 → 4 and `OVERRIDES` 11 → 0: closer to what was said, but "nearly empty"
became "empty".

### 4.14 Diagnosis: one root cause behind three symptoms — 2026-09-05

| Question | Answer from the files |
|---|---|
| Why is `REFLECTS` zero? | The 44 sites exist and were annotated. **41 of them (93%) got `DERIVES_FROM`/`CAPTURES` instead.** |
| Why did `ISOLATED` regress? | 121 of 141 claims (86%) are correct. The 20 bad ones are **record bases whose fields are used** — `ctrl` at 64 occurrences with 12 fields, `clk_gen` at 52 with 6. |
| Did the sweep find the sites? | **Yes.** Of 300 elements in a condition: 62% got a governing edge, **23% got a VALUE edge instead**, 5% claimed `ISOLATED`, and only **2% got nothing at all**. |

The three are one defect: **value-flow words used where control-flow words belong.** The same
thing measured in v3, where 81% of controlled elements naming their controller used a
value-flow label. `GOVERNED_BY` fixed the receiving side; the driving side was never
addressed.

The decisive detail: `DERIVES_FROM`'s own definition says the target must appear on the
right-hand side. In `port_sel(0) <= '1' when (req_i.addr = A_BASE) else '0'` the right-hand
side is a literal and `req_i.addr` is in the condition. The model wrote
`port_sel DERIVES_FROM req_i.addr` regardless. `SOURCES` carries an explicit exclusion for
exactly this; `DERIVES_FROM` and `CAPTURES` did not.

**A cause I introduced.** Generalising STEP 2b added the line *"DECL and nothing else → the
element is unused here → ISOLATED"*. That is a new explicit path to `ISOLATED`, and claims
rose 28%. Not yet changed; see §6.

### 4.15 The condition exclusion, verified then added — 2026-09-05

`DERIVES_FROM` and `CAPTURES` now carry the exclusion `SOURCES` already had: *a target that
appears ONLY in the condition governing the assignment is not on the right-hand side; that is
GOVERNED_BY, or REFLECTS where every value the element takes is a literal.*

**Verified before adding, not after.** The risk is an element appearing BOTH in the condition
and in a value arm, where the exclusion must not fire — the word "only" is what protects it.
Measured across every concurrent `when … else` in the corpus:

```
only in the CONDITION    241   74%   exclusion applies
only in a value ARM       82   25%   exclusion does not
in BOTH                    2    1%   'only' protects these
```

Both "BOTH" cases are generate-loop indices (`r`, `i`), which never enter the closed set —
the same reason process variables need no site. So the exclusion is safe on this corpus, and
"only" costs nothing while covering the general case.

No leak: no `BANNED_IN_OUTPUT` word, no numeric hint, and `audit_against_corpus()` passes.
(A crude hand-scan flagged "condition" as a corpus identifier; that was a false positive —
the real audit passes and the existing prompt uses the word throughout.)

Prompt sha `e6c2de72186e` → **`79ac68e7abb3`**, 21,509 chars.

### 4.16 The prompt split into editable blocks — 2026-09-05

`_procedure()` was one f-string. It is now a concatenation of named constants, ordered by
`_BLOCK_ORDER`:

```
_KNOWLEDGE_HEADER  _KNOWLEDGE_STEP1  _KNOWLEDGE_STEP2  _KNOWLEDGE_STEP2B
_KNOWLEDGE_STEP2C  _ANSWER_STEP3  _ANSWER_READING  _ANSWER_FIELDS  _GUARDRAILS
```

Named for the two structures requested. **Generated Knowledge Prompting** (Liu et al.,
arXiv:2110.08387) is two-stage — generate the knowledge, then answer using it. The
`KNOWLEDGE_*` blocks are stage one, producing the entity purpose and the occurrence profile;
the `ANSWER_*` blocks are stage two and consume them. **Meta Prompting** (Zhang, Yuan & Yao,
arXiv:2311.11482) puts formal task structure ahead of content-specific examples; `_SITES` and
`_EDGES` already are that, and are kept outside the step blocks so a vocabulary change and a
procedure change stay separate edits.

**The refactor changed nothing.** It was done by cutting the existing body at its own section
headers, and the sha was `e6c2de72186e` before and after — byte-identical. The exclusions in
§4.15 were added only after that was proven.

### 4.17 The condition exclusion generalised, and three findings — 2026-09-05

**Wording fix.** All three exclusions now read *"ONLY in the **branch or selection** condition
governing the assignment"*. The earlier phrasing could be misread to cover any boolean
subexpression: in `y <= f(a > b, c)` there is a comparison but nothing governs anything, and
`a` genuinely IS on the right-hand side. Sha `79ac68e7abb3` → **`7a182a7e4397`**.

On generality: the exclusion rests on HDL syntax, not on this corpus — a name inside a branch
condition is not on the right-hand side in either VHDL or Verilog. The corpus supplies no
counterexample but is too small to be the evidence; the earlier log wording overstated that.
The word "only" protects the case where a name is both tested and stored, which is common in
general RTL and which this corpus happens not to exercise.

**`handling` compliance splits by record kind.**

```
port field   (974):  FORWARDS 55%  CONSUMES 27%  ORIGINATES 16%  none  2%
signal field (271):  none     50%  ORIGINATES 22%  FORWARDS 22%  CONSUMES 6%
```

98% on port record fields, 50% on internal signal record fields. That accounts for all 153
`handling_missing_or_bad`. The prompt says "every element whose name contains a dot" and does
not distinguish; the model does. A wording fix, not a design failure. Not yet changed.

**No port record field is a ground-truth asset.**

```
GT asset elements       302
dotted                   52
  internal signal fields 30
  outside the 18 modules 22
  PORT record fields      0
```

Every dotted ground-truth asset is a field of an internal record — `ctrl` (25), `shifter`,
`fifo`, `keeper`, `mul`, `div`. `cache_i` and `cache_o` look port-shaped but are declared
signals, which the mechanical parse gets right and a name-based filter would not.

**Read this as annotation granularity, not as a fact about hardware.** When a whole bus port
matters an annotator names the port rather than enumerating twelve fields; when an internal
config record matters its fields have individually distinct meanings. The pattern is real for
reproducing this ground truth and belongs in the ASSET stage or an evaluation filter — never
in the parser, where "cannot be an asset" would be a verdict the parser is built not to make.

**On sourcing the port-boundary claim.** That a field of an input port record arrives from
outside the entity is language semantics, defined in IEEE 1076 (VHDL) and IEEE 1800
(SystemVerilog). It is not a research finding and no paper states it, because papers do not
restate the LRM. No clause number is recorded here because none was verified in session.

### 4.18 `audit_dead_ends()` — 2026-09-05

The one fact the vocabulary cannot express. `ISOLATED` means no coupling at all; an element
with a driver has a coupling, so it is correctly not `ISOLATED` and correctly nothing else
either. Maps onto CWE-1164, Irrelevant Code.

**Complement, not verifier.** `audit_isolated` checks a claim the model made and asks whether
the source contradicts it. This finds a fact the model was never able to state.

**Two independent signals, disagreement reported not hidden.** The parse says nothing consumes
it; the source says the name appears on no right-hand side and in no condition. Confirmed dead
ends are where both agree. Where the parse says dead and the source shows a reader, the parse
missed a coupling — counted apart as a recall finding.

**Writes nothing.** The parsed files keep exactly what the model produced.

**Two bugs found by running it, both mine.** The first version reported 8 dead ends and every
one was a reset signal. `RESETS` had been put on the driven side of the ledger, but it is
written ON the reset and names what it resets — the element is acting, so it belongs with
`GATES`. And the read-detection searched only the text after `<=`, so a name in the branch
condition preceding an assignment in the same statement was invisible. Both fixed, and a
self-test now refuses to report a result in which every hit is a reset.

**Result on the v5 parse:**

```
DEAD ENDS  0 confirmed by the source, of 42 the parse flagged
           42 had no consuming edge in the parse but ARE read in the source
```

Zero dead logic in NEORV32, which is plausible for a taped-out design. Validated with a
positive control: a synthetic signal written and never read is found. **The useful number here
is the 42** — couplings the parse missed, such as `arbiter_nxt.state` and `ctrl_nxt.state`,
each read once in the source and given no consumer edge.

### 4.19 Audit of the prompt as it stands, before the schematics — 2026-09-05

Recorded before any edit, so the schematics change can be measured against it. Every count
below was re-derived in session from `parsed_v5_tuning18`, not carried over from an earlier
turn.

**A. Three edge types are effectively unreachable.** Full type census of the v5 parse,
1 689 elements and 2 876 edges:

    DERIVES_FROM 632   GATES        225   RESETS      53
    SOURCES      630   GOVERNED_BY  171   SELECTS     37
    EXPORTS      603   ISOLATED     141   SEQUENCES   34
    CAPTURES     239   CARRIES      106   CONSTRAINS   4
                                          GATED_BY     1   (invented, not in EDGE_TYPES)

    REFLECTS 0.  OVERRIDES 0.

The split is not random. Every type above 100 is defined by ONE positional fact — on the
right-hand side, on the left, in a condition, at a clock edge, declared as an output. Every
type at or near zero is defined by a MULTI-PART SHAPE: "every arm is a literal AND the test
compares the target"; "two elements compared AGAINST EACH OTHER"; "two paths, an ordinary one
AND a substitute". Prose states a positional fact well and a shape badly.

**B. The model finds the sites and mislabels them.** Of 300 elements appearing in a governing
condition: 62% got a governing edge, 23% got a VALUE edge instead, 8% something else, 5% were
claimed ISOLATED, and only 2% got no edge at all. Recall of the SITE is near total; the loss
is entirely in turning the site into the right edge. This rules out "the model cannot see the
construct" as a cause for the governing gap, and it rules in the labelling step.

**C. ISOLATED is wrong in a shape the prose already forbids.** Of 141 claims: 86% genuinely
absent and correct; 11% (16) are record bases whose own bare name never appears but whose
FIELDS are used; 3% (4) are plain signals used in the source. The prose in `_EDGES` already
says a element coupled through its fields is not isolated. Saying it again will not help — it
is a check the driver can make and does not.

**D. `check_annotation` cannot express the rule that would catch C.** Its signature is
`check_annotation(rec, closed_names, issues, where)` — one record at a time. Every dependency
rule in the schema today (`guard` by edge type, `handling` by dotted name) is intra-record.
"A record base is not ISOLATED when one of its fields carries an edge" is INTER-record, and
there is no pass over the assembled file that could hold it.

**E. The occurrence profile is never emitted, so two different failures look identical.**
STEP 2 builds the profile and STEP 3 consumes it inside one call. Nothing leaves the model
between them. Where a governing edge is missing, the output cannot distinguish:

    the profile never recorded the COND site        -- a stage-one recall failure
    the profile recorded it, stage two wrote SOURCES -- a stage-two labelling failure

B says the second dominates, but B was measured against the RTL from outside. The parse
itself carries no evidence either way. This is the largest structural divergence from the
generated-knowledge method the prompt is modelled on (Liu et al., arXiv:2110.08387 §2.1-2.2),
where knowledge generation is a SEPARATE call producing an inspectable artifact.

**F. The shapes in `defs_v5.txt` were dropped for a mechanical reason, now identified.** The
working definitions file carries an example shape under most edges — `Y <= X;`,
`if rising_edge(clk_i) then X <= Y and Z;`, and the three `bits` examples. None reached
`prompts_parse_v3.py`. Running rule 1 of `audit_against_corpus()` over `defs_v5.txt` finds
**12 corpus identifiers**:

    bus_rsp_o, bus_rsp_o.data, clk_i, cmp_lt, rx_engine, rx_engine.sreg,
    rx_fifo, rx_fifo.wdata, tx_engine, tx_engine.sreg, tx_fifo, tx_fifo.rdata

Any of those in a prompt raises at import. The shapes were not judged unhelpful; they were
unusable as written. This also confirms the standing rule is doing its job, and it says what
a usable shape must look like: metavariables only, no identifier that could belong to any
real design.

**G. STEP 2b names edge types before `_EDGES` defines them.** Block order is PREAMBLE,
KNOWLEDGE_HEADER, STEP1, STEP2 (`_SITES`), STEP2B, STEP2C, ANSWER_STEP3, ANSWER_READING,
ANSWER_FIELDS (`_EDGES`), GUARDRAILS. STEP 2b asks for REFLECTS, GATES, CAPTURES and the rest
by name; their definitions arrive two blocks later. The model reads the whole prompt, so this
is not broken. It is recorded because the sweep is where A fails, and the sweep is asking for
a decision the vocabulary has not yet been given for. Moving `_EDGES` earlier would duplicate
a ~100-line block; not done.

**H. `OVERRIDES` is under-specified against `GATES`, and this is a definitional problem, not
a wording one.** `GATES` covers an element in a condition that decides "WHICH of the
alternative values" the target takes. A two-armed select where one arm is a substitute fits
BOTH types, and the driving-end ladder puts OVERRIDES first, so OVERRIDES should win. But
which arm counts as "the ordinary one the design already computes" has no syntactic marker at
all — it is a judgement about intent. The definition's own falsification test (delete the
element; does the target still get a value?) is sound and mechanical; the surrounding prose is
not. NOT CHANGED in this pass. Recorded as an open definitional item.

**I. STEP 2b's ISOLATED line hands over a conclusion rather than a procedure.** It reads
`DECL and nothing else -> the element is unused here -> ISOLATED`. Liu et al. §2.1 give the
authoring guideline for exactly this: a knowledge statement should turn the problem "into an
explicit reasoning procedure, without directly answering the question", and they name a
conclusion-shaped statement as a POOR demonstration. This line is conclusion-shaped, and
ISOLATED claims rose 28% in the run that introduced it. NOT CHANGED in this pass.

**J. STEP 3 still says "the four fields".** Five are emitted: `functionality`, `handling`,
`role`, `relationship`, `evidence`. Carried from §6; still open.

**What this section commits to.** Only A and F are addressed by the schematics change logged
in §4.20. C, D, E, H, I and J are recorded here so that the next run's numbers can be read
against a written baseline rather than against memory, and so that a later fix for any of them
is not mistaken for an effect of the schematics.

### 4.20 Schematic shapes added to all 14 edge definitions — 2026-09-05

**Change.** Every entry in `_EDGES` now carries a `SHAPE` line, and eleven of them a `NOT`
line giving the nearest type that would otherwise capture the site. A header was added at the
top of `_EDGES` with a metavariable glossary, a statement that the shapes are HDL-agnostic,
and the no-copy guard. `_EDGES` 6 410 -> 10 573 chars; the ELEMENTS prompt 21 569 -> 25 732,
a 19.3% rise. Prompt sha `7a182a7e4397` -> `d2569ebb9165`.

**Prose unchanged, and this is proved rather than asserted.** The patch script inserts each
block after a named anchor, then deletes every inserted block from the result and asserts the
remainder is byte-identical to the original file. It refuses to write otherwise. This matters
because the definitions were validated in §4.1 and §4.15 and a silent reflow would invalidate
both.

**Reason.** §4.19-A: the three types defined by a multi-part shape rather than a single
positional fact came back at 0, 0 and 4 of 2 876 edges. §4.19-F: shapes already existed in
`defs_v5.txt` but carried 12 corpus identifiers and would have raised at import.

**Notation, and why it differs from the `defs_v5.txt` draft.** The draft used `X`, `Y`, `Z`
and trailing lines of the form `X SOURCES Y`. Two changes:

  - `<elem>` and `<target>` replace `X` and `Y`. They are the exact words the prose uses, so
    the shape reinforces the direction rather than introducing a third vocabulary. The
    measured direction defect (§4.1: 67 reversed claims, `SLICES` 31% reversed) was a
    which-end-is-which failure, and neutral letters do not help with it.
  - The `X SOURCES Y` summary lines are NOT carried over. That is the notation which put
    `"SOURCES(Y)"` into 200 `type` fields in an earlier revision; a bare-name-plus-argument
    line next to a definition is exactly what got copied.

Angle brackets were chosen because `<` and `>` cannot occur in a VHDL or Verilog identifier,
so any leak is unambiguous rather than plausible.

**Self-critique performed before writing, and what it changed.**

  - *`OVERRIDES` given a test, not only a picture.* Its shape genuinely varies — priority
    branch, default-then-override, mask, bypass mux. The `when ... else` realisation is
    ALSO a valid `GATES` shape, separated only by which arm counts as "ordinary", which has
    no syntactic marker (§4.19-H). Showing it would have taught an ambiguity. Only the two
    unambiguous mask forms are shown, and the definition's own deletion test is written out
    as the rule. This follows the draft's own `Y <= (not X) and fail;` example.
  - *`REFLECTS` given three shapes, not one.* It outranks `CAPTURES` on the receiving-end
    ladder, so a concurrent-only shape would have under-covered the in-process form. The
    draft's reduction shape was kept but generalised: `and_reduce_f` is a NEORV32 function
    name, so it is written `<reduce>(<target>)`, which also covers Verilog's `&`/`|`.
  - *`SELECTS` shown on both sides of the index.* The definition says an index chooses which
    part of an array is "read OR written"; a read-only shape would have lost the write case.
  - *`SOURCES` given two shapes.* One alone would not separate it from `CARRIES`, whose
    boundary is two independent conditions (joined with something else, OR clocked).
  - *`ISOLATED` written as an absence, not a shape.* There is no construct to draw. The line
    states the two things that must both be absent, including the field carve-out that
    §4.19-C shows failing 16 times.
  - *`CARRIES` NOT line.* Partial width falls through the driving-end ladder to `SOURCES`.
    Recorded here because the definition says "whole width" without saying what a partial
    width becomes.

**Generality.** The shapes are written in VHDL because the prose already is. The header says
the same arrangement in any other HDL counts identically, and every language-specific token
is a metavariable: `<edge>` covers `rising_edge`/`falling_edge`/`posedge`/`negedge`,
`<reduce>` covers a reduction function or a unary reduction operator, `<array>(<elem>)`
covers `array[elem]`. No shape names a construct that exists only in VHDL. No shape was
derived from a NEORV32 line; the failure they target was, but the shapes are read off the
definitions.

**Checks run.** `audit()` passes at import. `audit_against_corpus()` passes against the
ground truth and both closed-set name lists — 0 identifiers. `EDGE_TYPES` still 14.

**What would falsify this.** After the next parse, on the same corpus and the same closed set:

  - `REFLECTS` > 0, and the 44-site check in `diagnose_v5.py` §1 showing its share above 0%.
    If it stays at 0, shapes do not fix recognition and the cause is elsewhere.
  - `OVERRIDES` > 0 and `CONSTRAINS` above 4.
  - `DERIVES_FROM` falling by roughly the `REFLECTS` gain and NO MORE. A larger fall means
    `REFLECTS` is over-firing and the `NOT` line is too weak.
  - `unknown_edge` and `unresolved_target` FLAT. Any rise means the schematics are being
    copied into output fields, which is the §4.19-F failure returning in a new form. The
    existing counters detect it; no new checker was added.
  - Total edges not falling. A 19.3% longer prompt for fewer edges is a net loss.

**Not addressed by this change.** §4.19 C, D, E, G, H, I and J stand. In particular the
`ISOLATED` cross-record check (C, D) is a driver change needing no re-parse and should be done
before the next run so that the true `ISOLATED` error rate is known beforehand.

### 4.21 The first cross-record schema rule — 2026-09-05

**Change.** `check_cross_record(elements, issues, stem)` added to `parse_v3.py`, called from
`_assemble` once every record for a module exists, with `_selftest_cross_record()` and
`audit_cross_record()` alongside it. New issue key `isolated_with_coupled_field`.
`audit_cross_record()` is wired into `report()`. No prompt change; no re-parse needed.

**The rule.** Within one entity, an element claiming ISOLATED whose own fields carry at least
one real edge is counted as a violation. `ISOLATED` and the driver's `UNRESOLVED` marker are
not evidence of a coupling and do not count.

**Why it could not live in `check_annotation`.** §4.19-D. That function's signature is
`check_annotation(rec, closed_names, issues, where)` — one record, no sight of its siblings.
Every dependency rule the schema had was therefore intra-record: `guard` keyed on the edge
type in the same record, `handling` keyed on the name in the same record. "A record base is
not ISOLATED when one of its fields carries an edge" relates TWO records and had nowhere to
go. The prompt has said this since v5 and it is still violated 16 times; a sentence asking
for compliance is not the same object as a rule the output can be checked against.

**Why it is a `check_` and not an `audit_`.** It opens no RTL. That is the line already drawn
in this file and it is the line Meta Prompting draws too (Zhang, Yuan & Yao, §3 and Appendix
A.1): a schema constraint is enforceable exactly when a validator can decide it from the
output. `check_*` decides from the parse and is enforced; `audit_*` needs the source and can
only be measured. A base claimed ISOLATED whose BARE name appears in the RTL is a different
finding and stays with `audit_isolated`.

**Self-test, five cases, all synthetic.** The rule refuses to report until it fires on a case
built to fire and stays silent on four built not to: field carries no edge; the coupled field
is in a different entity; a name that merely starts with the base (`aardvark` vs `aa`) is not
a field of it; and the base was never claimed ISOLATED. No corpus element appears in the test.

**Result on the v5 parse, no re-parse:**

    CROSS-RECORD  16 of 141 ISOLATED claims are record bases whose own fields carry edges (11%)
       neorv32_bus/neorv32_bus_amo_rmw/core_req_i   12 coupled field(s)
       neorv32_twi/neorv32_twi/fifo                 12
       neorv32_uart/neorv32_uart/ctrl               12
       neorv32_trng/neorv32_trng/fifo                8
       neorv32_uart/neorv32_uart/tx_engine           8
       ... and 11 more

**Validated against an independent method.** The RTL-based check in `diagnose_v5.py` §2
reaches 16 by a completely different route — it opens the source, counts occurrences of the
bare name, and asks whether the element has declared fields. The parse-based rule opens no
source at all. The two sets were compared element by element and are **identical**, with
nothing in the symmetric difference. Two methods with no shared code path agreeing on the
same 16 names is the strongest evidence available here that the rule is neither over- nor
under-firing.

**The true ISOLATED error rate, established BEFORE the schematics run.** Of 141 claims:

    121  86%  genuinely absent -- correct
     16  11%  record base, fields coupled      <- caught by this rule, output only
      4   3%  plain signal, used in the source <- needs the RTL, audit_isolated
    ----
     20  14%  wrong

This is the number the next run is measured against. Without it, a change in ISOLATED after
the schematics could not be attributed to either change.

**A dead counter found while doing this.** `isolated_but_used` is declared in BOTH issue
dictionaries (`parse_v3.py:341` and `:468` before this edit) and **written nowhere**. It has
reported zero for every run since it was added, which reads as a clean result rather than an
absent check. Left in place rather than removed, because removing a key changes the shape of
`_issues` in every parsed file and would break comparability with the v5 run. Recorded as an
open item: it should either be wired to `audit_isolated`'s finding or deleted at the next
version bump, not silently.

**What would falsify this.** The rule is a tautology on its own terms, so the falsifier is
about scope, not correctness: if after the next parse `isolated_with_coupled_field` rises
while total ISOLATED claims fall, the model is moving the same error into a shape the rule
does not see -- most likely claiming ISOLATED on a FIELD whose base is coupled, which this
rule deliberately does not flag because the prose makes no claim in that direction.

### 4.22 `isolated_but_used` wired, and a false positive removed on the way — 2026-09-05

**Change.** `_isolated_hits()`, `_selftest_isolated_hits()` and `check_isolated_used()` added
to `parse_v3.py`. The counter declared in §4.19 and never written is now written during the
parse. `audit_isolated()` was refactored onto the same helper. Both assembly paths now run
both cross-element checks.

**A false positive was found before the counter could inherit it.** `rtl_parse.arch_region`
deliberately does not cut at the first `begin` (its docstring records why: an architecture
with a function body in its declarative part lost every signal declared after it). So the
region handed to the ISOLATED check contains the DECLARATIONS as well as the statements, and
the old inline pattern matched a signal's own `signal x : ...;` line. Positive control, run
before the fix:

    signal unused_sig : std_ulogic;     -- declared, never used
    signal live_sig   : std_ulogic;
    begin  live_sig <= '1';

    unused_sig   hits=1   -> reported as USED
    live_sig     hits=2

A signal that is genuinely unused is exactly the case ISOLATED is FOR. The check would have
reported the one correct annotation as contradicted. `_isolated_hits` now blanks every signal
declaration before counting; after the fix the same control gives `unused_sig` 0 and
`live_sig` 1. Ports are declared in the entity, outside this region, and are unaffected.

**Not currently firing, and that was verified rather than assumed.** Every plain signal
claimed ISOLATED in the v5 parse turned out to be a record base whose fields are used, so
none was being mis-scored. `audit_isolated` reports **20 of 141 (14%)** both before and after
the fix — the §4.21 baseline is unchanged. The bug was latent, not active.

**One implementation, so the two cannot drift.** `audit_isolated` (whole directory, after the
fact) and `check_isolated_used` (during assembly, into `_issues`) now both call
`_isolated_hits`. Run across the corpus they agree exactly: 20 and 20.

**Self-test is hand-read, four cases**, and the rule reports nothing until all pass:

    unused_sig   0   declared and never used -- the declaration must not count
    live_sig     2   assigned once, read once
    rec_sig      1   bare base, matched only inside `rec_sig.ff`
    rec_sig.ff   2   the base match plus the `.ff` tail match

The third and fourth encode a deliberate behaviour rather than an accident: the bare-base
pattern ends at `(?![\w])` and `.` is not a word character, so `rec` matches inside
`rec.field`. That is correct — a record base IS coupled through its fields, which is the same
fact §4.21's rule enforces from the output side.

**Taxonomy note.** This one needs the source, so by the division drawn in §4.21 it is an
audit, not a schema rule. It is named `check_` and called during assembly for one reason: the
counter belongs in the same `_issues` block as the rest, and the source is already open at
that point. The naming is a placement decision, not a claim that it is enforceable from the
output.

**A gap in §4.21 closed.** `check_cross_record` was added to `_assemble` only. The
single-file path builds its `parsed` dict inline and never calls `_assemble`, so it ran
neither check. Both calls are now in both paths, in the same order.

**Still open, found here and NOT changed.** The single-file path's `parsed` dict omits
`_version`, which the batched path sets. `parse_version_of` and `assert_one_version` would
therefore fail on any file produced by that path. Out of scope for this edit; recorded.

**What would falsify this.** `isolated_but_used` in a fresh parse should equal what
`audit_isolated` reports for the same directory. If they diverge, the during-parse and
after-the-fact views have come apart again and the shared helper has been bypassed.

### 4.23 Cut over to v6 — 2026-09-05

**Change.** The prompt edits of §4.20 make this a new prompt version, so the run is labelled
v6 throughout rather than overwriting v5.

    parse_v3.OUT_DIR              parsed_v5_tuning18 -> parsed_v6_tuning18
    parse_v3.PARSE_VERSION        edge_set "v5" -> "v6"   (prompt_sha d2569ebb9165)
    notebooks/parser_v4.ipynb     V5_DIR -> V6_DIR, compare_v3_v5 -> compare_v3_v6,
                                  12 cells rewritten; no v5 output reference survives

`parsed_v5_tuning18/` is untouched and remains the baseline for §3B.

**Why a new directory and not `overwrite=True`.** The pre-flight caught that this was about
to be a silent no-op rather than an overwrite. `annotate_all_parallel` skips a module whose
file already exists unless `overwrite` is set, the notebook does not set it, and all 18 files
were present. The run would have made **zero API calls**, finished in seconds, and printed
the v5 numbers — the schematics would have looked like they changed nothing. A new directory
avoids both that and the loss of the baseline.

**The version label is a labelling decision, not a vocabulary change.** `EDGE_TYPES` is
byte-identical to v5: the same 14 names, same order. Only the prompt text changed. `edge_set`
is set to "v6" because the run needs to be distinguishable, not because the vocabulary moved.
Anyone reading a v6 file's stamp should take `v6` to mean "the v5 vocabulary, sixth prompt".

**`compare_parses` corrected as a consequence.** It keyed its warning on the whole stamp, so
any prompt edit produced *"Edge counts below are not comparable"*. For v5 -> v6 that is
false, and it would have told the reader to ignore the one number the run exists to produce
(`REFLECTS` 0 -> ?). It now reports what actually differs, and where the stamps declare the
same number of edge types it says per-type counts are comparable if the vocabulary is
unchanged, pointing at this log rather than guessing. Verified against a synthetic v6 file:

    old: v5/e6c2de72186e/14
    new: v6/d2569ebb9165/14
    <- DIFFERENT PARSE VERSIONS.
       Both declare 14 edge types. If the vocabulary is unchanged and only
       the prompt was edited, per-type counts ARE comparable -- ...

**Pre-flight, `preflight_v6.py`, ALL CHECKS PASS.** No API calls; the model is stubbed and
every path before and after it runs on real modules. What it covers beyond the v5 pre-flight:

  - a `SyntaxWarning` at import is treated as a failure, not noise;
  - 14 SHAPE lines, 7 NOT lines, metavariables present, none inside the output-schema block;
  - the ALL-CAPS tokens in `_EDGES` are diffed against the pre-schematics module, and the
    three the schematics add (`LEFT`, `SHAPE`, `TEST`) are PINNED, so a later edit that adds
    a fourth fails rather than being absorbed;
  - every `issues[...]` key written anywhere in `parse_v3.py` is checked against the keys
    declared in both issue dictionaries — 18 declared, 18 written, 0 undeclared. An
    undeclared key is a `KeyError` in the middle of a paid run;
  - both assembly paths are checked by AST for both cross-element calls;
  - the stub deliberately claims ISOLATED on record bases so the two new checks actually
    execute rather than being skipped for want of input;
  - `OUT_DIR` must be empty, which is the check that caught the no-op.

**A defect the notebook check caught in my own rename.** The cutover used a blanket
`e5 -> e6` substitution to rename the comparison variables. `e5` also occurs inside a hex
sha, so cell 8's printed note `8e7e3fb0e517685d` became `8e7e3fb0e617685d` -- a wrong sha
recorded in the notebook, silent, and invisible to any syntax or import check. Restored. The
lesson is the one this log keeps recording: a substitution narrow enough to look safe is not
the same as one verified against a diff. `check_notebook.py` now prints every changed line
between the notebook and its backup, which is how this was found.

**What to read after the v6 run.** §4.20's falsifiers, plus the §3B tables as the before
column. In particular: `REFLECTS` and `OVERRIDES` off zero; `CONSTRAINS` above 4;
`DERIVES_FROM` falling by roughly the `REFLECTS` gain and no more; `unknown_edge` and
`unresolved_target` flat; total edges not falling; and `isolated_but_used` agreeing with
`audit_isolated` on the same directory.

### 4.24 v7 — schematics narrowed to the three edges that needed them — 2026-09-05

**Change.** The v6 schematics are removed from eleven edge definitions and kept on three:
`REFLECTS`, `CONSTRAINS`, `OVERRIDES`. The STEP 2b sweep line for `PORT_MAP` is given an edge
name. Prompt sha `d2569ebb9165` -> `2e6f9eff2ed2`; 25 732 -> 23 841 chars, so the rise over v5
falls from +19.3% to +10.5%. `OUT_DIR` -> `parsed_v7_tuning18`, `edge_set` -> "v7".
`parsed_v6_tuning18/` is untouched.

**Three proposals were tested before being implemented; two survived, and they merged.**

*Proposal 1, fix the EXPORTS shape.* Correct that the line caused the −130, but the stated
mechanism was wrong: 372 of 570 fields still carried the edge, so the shape did not exclude
fields, it made the model hesitate on them (§3C.3). Superseded — removing the shape outright
restores the v5 prose, which is the better fix and is subsumed by proposal 3.

*Proposal 2, name the `PORT_MAP` edge.* Correct but minor. It was sold as closing a recall
gap; it is not one. 296 instance-port couplings were recorded in v5 and 246 in v6 as ordinary
`SOURCES`/`DERIVES_FROM` (§3C.4). It is 5 mislabelled edges. Kept because the STEP 2b table
genuinely had one site with no edge name and the cost is three lines.

*Proposal 3, strip the eleven.* The premise — that the sweep regression is dilution from a
longer prompt — is HALF supported. Counting both ends, governing coverage fell 63% -> 59%,
not 62% -> 54% (§3C.5). Half the apparent damage is a driving-to-receiving swap. Further,
stripping removes bad shapes AND length together, so it does not isolate dilution. Kept, but
relabelled: this is a SCOPE REDUCTION — shapes only where the definition turns on an
arrangement rather than a position — not a dilution experiment.

**Built by reversion, not by deletion.** The patch starts from the pre-schematics prompt and
re-applies three blocks, then asserts that removing those three blocks and the header
reproduces that file byte for byte. The eleven untouched definitions are therefore identical
to v5 by construction rather than by inspection. Nothing is written if the assertion fails.

**What v7 tests.** Whether the three targeted shapes deliver the `REFLECTS`/`OVERRIDES`/
`CONSTRAINS` gain without the collateral. Read against §3C:

  - EXPORTS back to ~90% (v5 65 fields missing, v6 198). If it stays near 198 the shape was
    not the cause and §3C.3 is wrong.
  - Total edges back toward 2 876. Still below it means the loss was not the eleven shapes.
  - `unknown_edge` back to ~1, with no `PORT_MAP` or `RESET_BRANCH` among the types.
  - `REFLECTS` at least holding 9, `OVERRIDES` at least 3, `CONSTRAINS` at least 6. If these
    fall back to zero, the three shapes were never what moved them and the whole schematic
    idea is dead.
  - Both-ways pairs staying near 13, not returning to 60. That gain came from the
    definitions, so it should survive; if it does not, something in the narrowing undid it.
  - Governing coverage read at BOTH ends, against 63% (v5) and 59% (v6). Reading the
    driving-end number alone overstates any change twofold.

**Not done, and awaiting a decision.** §3C.6: the `DERIVES_FROM` exclusion asserts a
condition-only target "is not on the right-hand side", which is textually false for a
concurrent conditional assignment, where the condition sits to the right of the assignment
operator. That reading would explain 40 of the 44 `REFLECTS` misses better than any shape
does. It is a prose accuracy question on a definition validated in §4.1 and §4.15, so it is
recorded rather than changed.

**Checks.** `audit()` and `audit_against_corpus()` pass. Pre-flight ALL CHECKS PASS with the
stubbed model, including the empty-`OUT_DIR` check that caught the v6 no-op. Notebook check:
NO NOTEBOOK-BLOCKING ERRORS — all cells parse, no undefined name top to bottom, no v4/v5/v6
leftovers, `STAGE = 2`, full module list passed. The v6 cutover's blanket-substitution defect
is not repeated: every rename here is word-boundary anchored and the v3 sha string is
asserted intact after the edit.

### 4.25 Batch ordering by locality — the batch boundary was a wall — 2026-09-05

**Finding first.** Reciprocity was measured inside the one entity that splits across calls
and compared with everywhere else, on both parses:

    v5   SPLIT (5 batches)   value 16/75  = 21%      all others  value 771/1231 = 63%
    v6   SPLIT (5 batches)   value 14/211 =  7%      all others  value 870/1225 = 71%

Then against the batch boundary itself, `neorv32_bus_io_switch`, 582 elements, 5 calls:

    v6   both ends in the SAME batch  : 14/73  = 19% mirrored
         ends in DIFFERENT batches    :  0/141 =  0% mirrored

**Zero of 141.** The boundary is not a degradation, it is a wall, and the mechanism is
plain: an edge and its mirror are written on two different elements, and the call that could
write the mirror never has that element in its list. This entity is 582 of 1 689 elements,
34% of the corpus, so it was suppressing the corpus-wide reciprocity figure throughout.

Same-batch reciprocity in that entity is also only 19% against 71% elsewhere, so 128
elements plus a large source is additionally too much to hold consistent inside one answer.
Not addressed here.

**Change.** `_by_locality(combined, rtl)` orders a splitting entity's elements by where each
first appears in that entity's architecture body. Applied ONLY when
`len(combined) > batch`, so all seventeen single-call entities are byte-identical to before
and any difference measured outside the split entity is attributable to the prompt, not to
this. `_selftest_locality()` gates it.

**Predicted before implementing, then confirmed after.** On the 205 mirrorable pairs the v6
parse actually wrote in that entity:

    current (ports, then signals)    same batch  64/205 = 31%
    first use in source              same batch 103/205 = 50%   <- adopted
    median statement index           same batch  84/205 = 41%
    field name, then base            same batch  52/205 = 25%
    statement walk (greedy)          same batch  69/205 = 34%

The field-name idea came from my own guess that a bus switch mostly couples same-named
fields across records. It is the WORST of the five. Recorded because the guess was confident
and wrong, and only measurement separated it from the one that worked.

**Two bugs, both caught by measuring after the change rather than before.** The first
implementation left the rate at 31%, twice:

  1. `entity_source` returns the entity DECLARATION followed by the architecture body, so
     every port's first occurrence is its own port-clause entry, in declaration order --
     exactly the ordering being replaced.
  2. The obvious fix, splitting on the word `architecture`, cannot work: `arch_region`
     has already consumed the `architecture X of Y is` header, so the word is not in the
     text at all. The boundary is found with `rtl_parse._ENTITY` instead, the same regex
     that built the declaration.

After the fix the measured rate is 50%, matching the prediction exactly.

**Why ordering is safe.** `_annot_user` puts the element list LAST, after the source and
header, precisely so the long shared span stays a cacheable prefix -- reordering the list
does not touch that prefix. `_assemble` rebuilds every record in mechanical order from a
`(entity, name)` key, so the output file is unaffected by which call annotated an element.
The self-test asserts the element count and the element set are preserved.

**What this does not fix.** 102 pairs are still cross-batch, and cross-batch mirroring is
0%. Locality ordering roughly halves the exposure; it does not remove it. The remaining
options, in order of cost: raise `batch` (200 gives 3 calls, still split), or a second pass
that writes only mirrors. 582 elements in one call is not available -- the output would run
to roughly 100 k tokens against a 32 k ceiling.

**What to read after the next run.** Reciprocity inside `neorv32_bus_io_switch` against
v6's 7% value / 0% control, and the corpus-wide value figure against 71% for all other
entities. If the split entity does not move well above 7%, the wall is not where the loss
is and this change should come out. Everything outside that entity must be unchanged by
this edit alone; any movement there belongs to the v7 prompt.

**Checks.** Pre-flight ALL CHECKS PASS. Notebook check NO BLOCKING ERRORS.

## 5. Standing invariants

Enforced in code, not by review. Each exists because it was violated once.

- No corpus identifier in any prompt — `audit_against_corpus()`, fails at import.
- No banned word in a prompt outside the section that names them in order to forbid them.
- No numeric emission hint — a number in a prompt becomes a hard quota however it is hedged.
- No edge type shown with a parenthesised argument. An earlier revision wrote `SOURCES(Y)`
  and the model copied the notation into 200 of 3,048 `type` fields. `audit()` now asserts
  `f"{e}(" not in text` for every edge name.
- The closed set is fixed by regex — `verify_against_cache` raises on drift.
- Never write to a notebook file while its kernel is running.

## 6. Open, not yet done

Ranked by what they cost if skipped. Items 4.5 through 4.11 closed what were items 1, 2, 3, 4 and 6 here.

1. **`FORWARDS` falsification check** — the reason `handling` was made a field rather than a
   checked keyword. If a record field appears anywhere other than a whole-record copy,
   `FORWARDS` is false. Mechanical, no API cost. Not written.
2. **`"four fields"` in STEP 3.** With `function` gone and `handling` added the emitted count
   is five. The phrase was left alone because it was not in scope.
3. **`normalize_record` runs on load and on disk.** Worth confirming double application is
   idempotent, or picking one.
4. **`neorv32_bus_io_switch` splits across five batches** (582 elements at batch=128). Some
   of the value-flow misses there are batch-boundary loss rather than reading failure.
   Measure the two apart before blaming the prompt.
5. **Add `function` to the verifier** — no longer applicable; the field is gone.

## 7. What to read after the next parse

In this order. The first two decide whether the run is usable at all.

1. `verify_against_cache` did not raise — the closed set held.
2. `handling_missing_or_bad` and `handling_on_non_field` near zero, and the `handling`
   distribution NOT dominated by `FORWARDS`.
3. `governing_coverage` against the 51% baseline.
4. `guard_coverage` — the direct read-out of the v4 change, never yet measured on a real run.
5. Site-class recall against the 63% baseline, per role.
6. `audit_isolated` — but only after item 1 of §6 is fixed, since until then it is partly
   measuring the driver rather than the model.
