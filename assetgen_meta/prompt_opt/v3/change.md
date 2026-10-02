# v3 change note (from v1)

**v3 has no prompt change.** No edit met all three conditions: a basis in a "Prompt" row of ASSET_DEFINITION.md
section 3 (or a paper), no conflict with an unchanged prompt definition, and an expected F1 gain larger than the
run-to-run noise (about 0.027). So `v3/instructions.md` is a byte copy of `v1/instructions.md`.

- Checked in this session: `cmp v1/instructions.md v3/instructions.md` finds no difference (28,992 bytes, ASCII, LF).
  Because the bytes are equal, the instructions sha12 is the one in `v1/build_info.json`: `3737b8f908a7`.
- Do not build or run v3 as a new version. A run would be a v1 replicate under a v3 label.
- Iteration 3 therefore has F1 gain 0. Iteration 2 also had gain 0 (v2 = v1). That is two iterations in a row below
  0.02, so **the stopping rule is met**.

## What was re-run in this session (counts exact, against the 111-entry reference of the 15 tuning modules)

Scripts: `scratchpad/v3ana/` (session scratchpad). All self-tests ran first.
- `selftest.py`: PASS (uart `ctrl.irq_rx_nempty` parsed as hand-read).
- `subent.py`: runs; prints the sub-entity port entries it classifies.
- `families.py` on v1 r0: 171 false positives (FP), 104 true positives (TP). The family counts below add up to both.
- `concepts.py` on v1 r0: of 140 concepts, 54 have no TP at all (45 mixed, 36 all TP, 5 empty). The 54 hold 112 FP
  references, counted with duplicates across concepts.

| Family (v1 r0) | FP | TP of the same shape | Class |
|---|---|---|---|
| Internal state registers (counters, sequencing state, shift and sync registers, flags) | 53 | 19 | reference inconsistency |
| Combinational signals | 24 | 12 | reference inconsistency |
| Settings written from an input | 22 | 16 | reference inconsistency; the prompt's own row says settings are primary |
| Record fields wired to a sub-unit | 21 | 3 | reference inconsistency |
| Plain wires between sub-units | 11 | 8 | reference inconsistency |
| Input ports | 9 | 24 | reference inconsistency |
| Output ports | 9 | 21 | reference inconsistency |
| Reset generation | 13 | 0 | evaluation-layer row (no basis) |
| Memory arrays at rest | 4 | 1 | evaluation-layer row (no basis) |
| Renamed port | 1 | 0 | reference defect |
| Register whose only use is to drive whole output ports (E1) | 4 | 0 | only prompt candidate |

"Reference inconsistency" means the reference lists this record shape in some modules and not in others, and the
listed and unlisted elements have the same shape. A prompt rule written by shape would remove TP and FP together.
That covers 149 of the 171 FP. The rows with no basis (17 FP) may only be applied as code filters after generation
(ASSET_DEFINITION.md section 3, row "Reset generation and memory arrays at rest are not listed").

## Edits made: none

The task allowed one to three edits. The best candidate is below, with the wording it would have had, so that a
later iteration can pick it up or reject it on the record.

### Candidate E1 (not made): a register whose only use is to drive whole output ports

- **Old text (v1 section 6, unchanged):** "A storing element remains a realization point even when it captures
  unchanged data, provided this entity uses the value it holds and the element's own records show that use: a GATES,
  SELECTS or CONSTRAINS record that targets another element, a CARRIES or SOURCES record into an output port or output
  field of its entity, or a connection of mode in into a sub-unit. [...]"
- **New text it would have added:** "A stored register that is neither a setting written by a configure flow nor
  self-updating, and whose only driving records are CARRIES or SOURCES into whole output ports of its entity that are
  eligible exits, holds the value only on its way out: it is secondary, and the exit port realizes the value. Where
  the value leaves only through a transport record, the register keeps its role."
- **Error pattern and counts** (`stage.py`, rule "E1 strict", 0 TP removed in every run):

  | Run | FP removed | TP removed | F1 before | F1 after (upper bound) |
  |---|---|---|---|---|
  | v1 r0 | 4 | 0 | 0.539 | 0.545 |
  | v1 r1 | 3 | 0 | 0.528 | 0.532 |
  | v0 r0 | 5 | 0 | 0.473 | 0.479 |
  | v0 r1 | 4 | 0 | 0.500 | 0.505 |

  Anchor (hand-read): `RTL_data/neorv32_cpu_cp_cfu.vhd` line 222 assigns `xtea.res <= ... unsigned(tmp_b) +
  unsigned(tmp_r)` on the clock edge; line 249 copies it to `result_o`. In the map, `xtea.res`'s only driving record
  is CARRIES into that output port.
- **Basis claimed:** section 3 row 4, "A register that holds a value only while moving it between its entry and exit
  is secondary" (LAsset p2: the AES output buffer is a secondary asset; SAIF p2, example 1). The exact record test is
  pattern only.
- **Why it was not made (reasoning):**
  1. It conflicts with an unchanged definition. All four registers it removes on v1 r0 are where their value is
     computed or decided, not where an already-made value waits. The cfu register computes a sum at line 222. The
     other three are set under conditions on their engine's state. Prompt section 2 makes "where its value is ...
     computed" a structural reference, and section 3 row 1 makes decision elements primary in their own right. The
     LAsset output buffer holds a value computed elsewhere, which is a different situation.
  2. A narrower version that keeps the basis ("an unchanged copy only": the register's only receiving data record is
     COPIES) removes 0 of the 4. So the part with a basis gains nothing, and the part that gains has no basis.
  3. The best case, +0.006 F1 on v1 r0 and +0.004 on v1 r1, is below the 0.027 noise. The risk is larger: if the
     model reads transport output fields as exits, it would drop 4 TP of the same record shape (in imem, bus, wdt and
     hwspinlock), and F1 on v1 r0 would fall to about 0.529 (analyst's figure; not re-run here).
- **Worked example check:** the fixed example lists a direction register beside the output port it drives
  (`assign p1_dout_en = p1dir;`, example line 205). That register is a setting, so E1's setting exclusion would keep
  it. No contradiction with the example.
- **Predicted effect if it had been made:** FP -3 to -5, FN +0 to +4. Net F1 between -0.010 and +0.006.
- **What would show it fails (if a later iteration makes it):** re-apply E1 as a code filter to the new output (it
  should match 0 entries), and check that the four same-shape TP (one register each in imem, bus, wdt and hwspinlock)
  and every setting are still listed.

### Other candidates (not made; counts re-run with `operand.py` and `decode.py`)

- **Combinational decision used only as an operand of other listed elements.** v1 r0: removes 12 FP and 4 TP (F1
  0.541), or 10 FP and 3 TP in the control-only variant (F1 0.542). v0 r0: F1 falls to 0.463 / 0.464; v0 r1: falls
  to 0.497 / 0.499. The TP it loses have the same shape as the FP it removes, so this is reference inconsistency.
  It would also contradict section 3 row 1 (decisions are primary). This differs from the analyst's note, which gave
  F1 0.545 for an "internal targets only" variant; that variant is not in `operand.py`, so the 0.545 is not
  re-derived here. Either way the gain is below the noise.
- **Signal decoded only from transaction fields.** v1 r0: removes 27 FP and 18 TP; F1 falls to 0.504. Most lost TP
  are settings, which row 1 makes primary. The worked example also lists a write-eligibility decision. Rejected.
- **Recall.** 7 false negatives on v1 r0, none fixable by a rule with a basis: 2 reference defects, 3 elements never
  read in their entity (listing them would contradict section 4, "no local use"), 2 one-offs that appear only in a
  concept's text.
- **Not proposed again:** edit D (withdrawn in v2; now the evaluation-layer filter R1a).

## Correction to v2/change.md

That note said 6 of the 8 "Other" R1a matches on v1 r0 are registered read-outs of memory arrays, and pointed the
next edit at row 4. That was wrong. Four of them are the arrays themselves: `RTL_data/neorv32_cache.vhd` lines
414-423 write them from `wdata_i`, and lines 425-428 read them into `rdata_o`. They belong to the evaluation-layer
row for arrays at rest, not to row 4. Only two are registered read-outs, and those feed a hit comparison through a
control record, which is the shape of the withdrawn edit D.

## What to do next (recommendation)

1. Stop the edit loop (stopping rule met). Final prompt: v1 (sha12 `3737b8f908a7`).
2. Run a third v1 replicate so the headline is a mean of 3 runs, as ASSET_DEFINITION.md section 4 requires.
3. Run the one pre-registered held-out check of v1.
4. Report the evaluation-layer rows (R1a, reset generation, arrays at rest) as separate labelled rows, never in the
   headline.

What would show "no edit" was the wrong call: a later analysis finds an error pattern with a basis whose removals in
both v1 replicates exceed 0.03 in F1 without losing a TP.
