# Relationship definitions, v2 (2026-09-29)

Supersedes v1 of this file and the `_EDGES` block of `prompts_parse_v3.py`, for the relation annotator that reads the
v3b occurrence profile. Written for VHDL; the same arrangement written in any other HDL counts the same.

## The principle: every relationship is a PAIR

For a statement that gives X a value, X = F(Y) under some conditions, there are two elements and two records:

- the **driving record**, written on **Y**: what Y does for X;
- the **receiving record**, written on **X**: what X is to Y.

Every relationship type below has exactly one partner. A driving record always has its receiving record and the
reverse; one never stands in for the other.

**Who writes which side (revised).** The LLM writes BOTH sides, independently, occurrence by occurrence: the driving
record when it reaches Y's occurrence, the receiving record when it reaches X's assignment. Each record names its
partner element and partner Occurrence ID. Code writes no relationship; it checks that every record has its partner.
A record without one is flagged for the validate step. Agreement between the two sides is then evidence, and
disagreement locates an invented or missed relationship. (An earlier draft had code write the receiving side as a
mirror: that would have copied every LLM error to both sides and hidden it.) The exception is FEEDS / FED_BY: the
direction needs the formal's mode from another entity's file, which the LLM does not see, so code writes both sides.
The 43% both-ends figure of the old parser (logged) came from a parser without Context, Path or SITE tags.

**Terms.**
- *X's assignment*: an occurrence of X tagged LHS_PROC or LHS_CONC, or X as the target of a `when ... else` or
  `with ... select` assignment. *Its Path*: that occurrence's Path.
- *On a clock edge*: an edge function (`rising_edge(<clk>)`, `falling_edge(<clk>)`, or `<clk>'event and <clk> = <lit>`)
  appears in that Path with no `not (...)` around it. The `'event` form is absent from this corpus (0 of 44 files).
- *Element*: a name in the closed set (ports, internal signals, `<base>.<field>`). Literals, named constants,
  generics, loop parameters and process variables are not elements.
- *edge* qualifier: every pair carries `edge: true | false`, whether X's assignment is on a clock edge. This replaces
  the old CAPTURES type, which was DERIVES_FROM on a clock edge.

## Linking an element to the assignments it governs — measured, exact

A condition element sits inside the branch it opens: its occurrence's innermost Context frame is that then or elsif
branch (38 of 38 IF_COND, 10 of 10 EDGE_CHECK occurrences on trng + cache). A case selector's innermost frame is its
case (1 of 1). So:
- the assignments a condition governs are the assignments of other elements whose Context contains **the same branch
  frame** (same kind, same span) — plus, through its negation, those in the **later arms** of the same `if` frame;
- the assignments a selector governs are those whose Context contains **the same case frame**;
- the assignment a right-hand-side element feeds is the assignment on **the same statement**.

---

## A. The pairs

| # | driving (on Y) | receiving (on X) | definition | cited SITE of Y (code check) | anchor |
|---|---|---|---|---|---|
| **value** | | | | | |
| 1 | **CARRIES** | **COPIES** | X's right-hand side is exactly Y: no operator, slice, index or conversion. On a clock edge or not (`edge`). | DIRR_ASS | `neorv32_boot_rom:65` `bus_rsp_o.ack <= rden` |
| 2 | **SOURCES** | **DERIVES_FROM** | Y's value is read on X's right-hand side in any other way: an operand, a function argument, an array element read, the value arm of a `when ... else` or `with ... select`, or through a process variable (rule below). | RHS_OPERAND, WHEN_EXPR, VAR_RHS_OPERAND, DIRR_ASS on a clock edge | `neorv32_boot_rom:64` rdata SOURCES bus_rsp_o.data |
| 3 | **FEEDS** | **FED_BY** | a value crosses an instance port. The driving side is the one the value leaves: an element that is the actual of a formal of mode `in` FEEDS `<instance>.<formal>`; a formal of mode `out` or `buffer` FEEDS the element that is its actual. `inout`: both. One endpoint is the formal, written `<instance>.<formal>`. **Written by code on both sides.** | ASSOC_ACTUAL | `neorv32_bus:611` `device_rsp_i => main_rsp` -> main_rsp FEEDS `<inst>.device_rsp_i`; `neorv32_bus:610` `device_req_o => main_req` -> `<inst>.device_req_o` FEEDS main_req |
| **control** | | | | | |
| 4 | **SEQUENCES** | **CLOCKED_BY** | Y is the argument of the edge function that puts X's assignment on a clock edge. *(v1 had no mirror for this.)* | EDGE_CHECK | `neorv32_boot_rom:59` clk_i SEQUENCES rden |
| 5 | **RESETS** | **RESET_BY** | Y is tested in an arm of the same `if` as that edge function, the arm comes before the edge arm, and in that arm X is assigned a literal or a named constant. *v2 also counted "the outermost `if` inside the edge arm"; on trng + cache that matched 5 conditions and none was a reset — `neoTRNG:355` restarts a sampling iteration, `neorv32_cache_memory:380-384` are clear / invalidate / new commands — so it is removed: such a condition is GATES.* | IF_COND | `neorv32_boot_rom:57-58` rstn_i RESETS rden |
| 6 | **SELECTS** | **SELECTED_BY** | Y is the selector of the `case` or `with ... select` whose alternative holds X's assignment; or an index computed while the design runs that picks which part of an array is read into X, or written when X is the array. | CASE_EXPR, INDEX | `neorv32_boot_rom:48` bus_req_i.addr SELECTS rdata |
| 7 | **CONSTRAINS** | **CONSTRAINED_BY** | Y is compared (`=`, `/=`, `<`, `<=`, `>`, `>=`) with an expression that contains another element, and that comparison is a condition in X's Path. Every element on either side carries it. | IF_COND, WHEN_COND | `neorv32_wdt:144` cnt and ctrl.timeout CONSTRAIN cnt_timeout |
| 8 | **GATES** | **GATED_BY** | Y decides whether X takes a value, or forces it to a fixed level. Two forms, told apart by the SITE of the occurrence in `at` (no `form` field): **condition** — Y appears in an `if`, `elsif` or `when ... else` condition in X's Path, or in an earlier arm's condition that the Path negates, used bare or compared with a literal or a named constant; **operand** — Y is a single-bit operand, bare or as `not Y`, of a top-level `and`, `or`, `nand` or `nor` on the right-hand side of a single-bit X. *(Merges v1's OVERRIDES.)* | IF_COND, WHEN_COND (condition); RHS_OPERAND (operand) | condition: `neorv32_boot_rom:64` rden GATES bus_rsp_o.data. operand: `neorv32_cpu_control:585` trap_ctrl.exc_fire GATES ctrl_o.rf_wb_en |

**Why OVERRIDES merged into GATES.** The same control can be written either way, and v1 gave the two spellings
different types. `x <= a when (en = '1') else '0'` (condition form) and `x <= a and en` (operand form) both mean "en
decides whether x can be '1'". The syntax cannot tell a "substitute" operand from an "ordinary" one: `neorv32_boot_rom:60`
`rden <= bus_req_i.stb and (not bus_req_i.rw)` and `neorv32_cpu_control:585` have the same shape. The v3 parser
emitted OVERRIDES 0 times in 2,876 edges (logged), so nothing comparable is lost.

## A2. SITE -> relationship, checked in code (2026-09-29)

The table in `META_PROMPT.md` section 4 was implemented in code over trng (v3) and cache (v3b): 662 occurrences, 144
assignments. Pairs found from the driving side (Y's occurrences) and from the receiving side (X's assignments) agree
exactly: 314 and 314, none found from one side only. This checks the table's internal consistency, not its accuracy
against a hand-read key. The check found and fixed:
- **24 reads with no record**: a whole right-hand side that is indexed (13, e.g. `neorv32_trng:105`
  `enable <= bus_req_i.data(ctrl_en_c)`) or sliced (11, e.g. `neoTRNG_cell:458`) carries INDEXED_NAME or PART_SELECT
  alone — the rulebook gives it no DIRR_ASS — and the table gave add-ons no record. Now: SOURCES, with bits.
- **The with ... select selector** has no SITE in the rulebook; the table now names it by position (3 lines corpus-wide).
- **A variable's whole right-hand side** has an empty SITE list by the rulebook; the table now routes it through the
  variable rule (0 such occurrences in trng + cache).
- **The synchronous RESETS clause**: removed (row 5).

## B. Rules that remove the remaining overlaps

1. **One type per occurrence.** For one Y occurrence and one X, keep the first that applies:
   SEQUENCES, RESETS, SELECTS, CONSTRAINS, GATES, CARRIES, SOURCES. The mirror takes the matching partner, so there is
   no separate receiving-end order.
2. **The clock is only SEQUENCES.** An edge function in X's Path is never GATES.
3. **The reset is only RESETS.** A reset arm negated in a later arm's Path is not GATES. *Measured: 26 of 144
   assignment occurrences on trng + cache are clocked and carry `not (<reset test>)`; v1 made the reset gate each.*
   A register with no RESET_BY is recorded as a fact (not reset), below.
4. **A case or with-select entry in the Path is only SELECTS**, never GATES, though it reads `<selector> = <choice>`.
5. **Element against element is only CONSTRAINS**; against a literal or a named constant it is GATES.
6. **A condition over generics or constants alone is not a relationship**: it is the configuration fact.
7. **An index**: computed at run time (contains an element) -> SELECTS; built only from literals, constants, generics
   or loop parameters -> `bits`. The array read itself -> SOURCES.
8. **An attribute prefix** (`Y'length`, `Y'left`) reads the shape, not the value: no relationship.
9. **Self**: X = F(X) (a counter, a state register) gives both records on X, both naming X.
10. **Citations**: the driving record cites Y's occurrence; the receiving record cites X's assignment occurrence.
    A pair is the two together.

**Process variables.** X = F(v) where v was computed from elements earlier in the same process: write the pairs as if
those elements were read directly. An element read in the variable's assignment takes the type it would have if read in X's statement (SOURCES,
GATES operand form, or SELECTS as a run-time index);
an element in a condition or selector governing that assignment takes the type rules 1-10 give it, as though the
condition were in X's Path; inside a loop, this holds for every assignment to the variable in the loop body. Cite the
occurrences in the variable's assignment, or in the condition. (v2.1: was "GATES X" and "every element read in the loop
body", which conflicted with rule 5 and with G3/G6.) Anchor: `neorv32_bus:384-395`
(`tmp_v.data := tmp_v.data or port_rsp(i).data; ... int_rsp <= tmp_v;` -> port_rsp SOURCES int_rsp). Count: 17 signal
assignments read a variable.

## C. Facts on one element — no partner, because X = F(no element)

Written by code.

| fact | definition | anchor / count |
|---|---|---|
| **configuration** | the `[generic]` / `[static]` conditions under which the element is declared or driven, with the occurrences; every pair at those occurrences inherits them | `neorv32_bus:670-671`; `neorv32_cache:216`. 503 assignments |
| **tied** | every assignment gives a literal or a named constant, unconditionally or under configuration only; values recorded | `neorv32_boot_rom:66` `bus_rsp_o.err <= '0'`. 219 of 1,250 driven elements |
| **constant_valued** | every assignment gives a literal or a named constant, and which one depends on conditions over elements (those elements GATE or CONSTRAIN it). *Replaces v1's REFLECTS, which was a property of X's assignments, not of one pair.* | `neorv32_wdt:144` cnt_timeout takes '1' or '0' |
| **initial** | the value in the declaration | — |
| **storage** | *edge* / *none* / *mixed*: whether X's assignments are on a clock edge | — |
| **not_reset** | X has an assignment on a clock edge but no RESET_BY | — |
| **boundary** | port mode; for an outward port, *driven*, *tied* or *undriven* (replaces EXPORTS) | — |
| **handling** | for a record field, any of ORIGINATES, CONSUMES, FORWARDS | 606 of 2,431 fields have more than one |
| **isolated** | no pair and no fact recorded | — |

## Changes from v1, and what they break

| v1 | v2 | why |
|---|---|---|
| GOVERNED_BY, one mirror for five types | GATED_BY, SELECTED_BY, CONSTRAINED_BY, RESET_BY, CLOCKED_BY | "what X is to Y" keeps its specific meaning |
| CAPTURES and DERIVES_FROM split by clocking | DERIVES_FROM and COPIES, with `edge` | one partner per driving type; clocking is a property of the assignment |
| OVERRIDES | GATES, operand form | the same control written two ways had two types |
| REFLECTS | fact `constant_valued` | a property of X's assignments, not a pair |
| SEQUENCES with no mirror | CLOCKED_BY | every relationship has two sides |
| reset negation counted as GATES | excluded (rule 3) | 26 of 144 duplicate edges |

Breaks comparability with the v3 parser's edge counts, and with v1 of this file. Nothing here is compared yet.

**Falsifiers, read after the first run.** Per driving type, the share of LLM records whose cited occurrence fails the
SITE check in table A, or whose X has no assignment in the linked frame or statement. The mirror count must equal the
driving count exactly; any difference is a code bug. For FEEDS / FED_BY, all 413 port-map actuals must be accounted for.

---

## Why each pair matters for asset identification (rationale — NOT prompt text)

Kept verdict-free in the parser; used by the later asset stage. Grounded in IEEE P3164 (produce / store / transport;
ports are attack surface; PIO = where a value can be observed or influenced) and LAsset (stores / sets / computes /
exit port).

- **COPIES / DERIVES_FROM / FED_BY** tell where X's value comes from: the backward trace from a sensitive value to
  whatever can influence it. **CARRIES / SOURCES / FEEDS** give the forward trace to where it can be observed.
- **CLOCKED_BY + storage** mark *stored* values (keys, configuration, lock bits). **RESET_BY + not_reset + tied +
  initial** say what a control holds after reset, or that it cannot change.
- **SELECTED_BY**: an address or index decides which stored value is read or written.
- **CONSTRAINED_BY**: element-vs-element checks — address bounds, tag compares, timeouts — typical enforcement points.
- **GATED_BY**: enables, inhibits and state checks that decide whether a value is written or released
  (`neorv32_cpu_control:585`: an exception inhibits a register write-back).
- **configuration**: the same RTL implements different features per build; an asset claim holds only for the
  configuration it names.
