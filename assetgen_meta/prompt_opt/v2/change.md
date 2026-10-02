# v2 change note (from v1)

**v2 has no prompt change.** Edit D was withdrawn after review (verdict FAIL). `v2/instructions.md` is now a byte copy
of `v1/instructions.md`. The rule D tested moves to the evaluation layer as a labelled code filter (see below).

This reverses the earlier version of this note, which proposed D as a prompt rule. The reason: D's boundary has no
basis outside the reference, so ASSET_DEFINITION.md section 5 does not allow it in a prompt.

- Checked in this session: `cmp v1/instructions.md v2/instructions.md` finds no difference. The instructions sha12,
  computed the way `opt_tools.build` computes it, is `3737b8f908a7` (28,993 characters) for both. That matches
  `v1/build_info.json`.
- Do not build or run v2. A run would be a v1 replicate under a v2 label. Steps 4 to 9 of RESUME.md do not apply.
  Default for the next iteration: run revise from `cur` v1 into v3. That keeps this folder as the record of the
  withdrawn edit.

## What was withdrawn

Two changes, now both reverted to the v1 text:
- A new bullet in section 6, after "A storing element remains a realization point...". It said a register that is
  only one operand of output ports is secondary when those ports are listed. It applied "also when it holds a setting
  written by a configure flow or updates itself".
- One extra clause on the section 8 "stores" check: "a register that section 6 makes one operand of the output ports
  it feeds passes neither way;".

## Why: the review, and one measurement

The reviewer found five problems. Problem 2 alone rules out a prompt edit:
- The rule's boundary was fitted to the reference, not taken from a theory. That covers the exact record test, the
  read-back exception, the "under any concept" scope, and the override of edit A. The earlier note already said
  "Theory basis: partial".
- ASSET_DEFINITION.md section 5 says: "A rule whose only support is a count from the reference goes to the evaluation
  layer and is reported separately."
- It also contradicts a "Prompt" row of section 3: "State, setting and decision elements are primary in their own
  right". The register's status would also depend on how its read-back is wired, not on what it holds.

The reviewer offered a smaller fix first for problem 1: delete ", also when it holds a setting written by a configure
flow or updates itself". The fallback was to revert if that fix "loses most of the predicted gain". It does. Script:
`scratchpad/v2fix/fix1_residual.py`, run in this session. It reuses `v1err/rules.py` (`R1a`). The parser self-test
`v2edit/selftest.py` passed first.

The script sorts the matches the model listed into three kinds:
- a setting written by a bus write (a COPIES or DERIVES_FROM record from a field of an input record);
- a register that updates itself (a self record);
- anything else.

Without the clause, prompt lines 53 and 82 keep the first two kinds primary. So at most the third kind can still go.
F1 is the balance of precision and recall.

| Run | Bus-written setting | Updates itself | Other | F1 base | F1, full D | F1, D after fix 1 (upper bound) |
|---|---|---|---|---|---|---|
| v1 r0 | 9 | 4 | 8 | 0.539 | 0.570 | 0.550 |
| v0 r0 | 9 | 4 | 9 | 0.473 | 0.500 | 0.483 |
| v0 r1 | 9 | 4 | 9 | 0.500 | 0.528 | 0.511 |

- All counts are exact, against the 111-entry reference of the 15 tuning modules. Every match is a false positive.
  None is a true positive.
- After fix 1, at most 8 of the 21 v1 r0 removals stay. The F1 gain is +0.011, below the run-to-run noise of about
  0.03. Problem 2 would still apply to what is left. So the fallback (revert) is the one to use.
- Problems 1, 3, 4 and 5 were all about the text that is now reverted, so none of them applies any more.

## Moved to the evaluation layer: `R1a`, a labelled code-filter row

R1a is a code filter for registers that are only one operand of output ports. It runs after generation. It is
reported as its own labelled row next to the headline and is never folded into the headline. Its basis is "none
(derived from reference counts)", the same as the GUARD row.

What it removes: a register that meets all of these.
- It is a stored signal: storage edge or mixed.
- It has no connection of mode in into a sub-unit.
- Leave out its records that target itself and its read-backs into output port fields. Every driving record left
  targets an output port of its own entity.
- None of those records is CARRIES.

Code: `R1a` in `scratchpad/v1err/rules.py`.

Measured in this session (`python v1err/rules.py`). Precision (P) is the share of listed elements that are in the
reference. Recall (R) is the share of reference entries that were listed.

| Run | Base P / R / F1 | FP removed | TP removed | With R1a P / R / F1 |
|---|---|---|---|---|
| v1 r0 | 0.378 / 0.937 / 0.539 | 21 | 0 | 0.409 / 0.937 / 0.570 |
| v0 r0 | 0.326 / 0.856 / 0.473 | 22 | 0 | 0.353 / 0.856 / 0.500 |
| v0 r1 | 0.343 / 0.919 / 0.500 | 22 | 0 | 0.371 / 0.919 / 0.528 |

- The rule was found on these 15 modules, so these are in-sample figures. Treat it like GUARD: in-sample row only,
  shown next to an equal-strength random-thinning baseline, until a held-out run shows its effect.
- What would show it is only a fit to the tuning reference: on the held-out set, it removes any true positive, or its
  precision gain is no larger than random thinning of the same number of entries.
- Not done here, because this task allowed edits to these two files only:
  - adding the row to ASSET_DEFINITION.md section 3;
  - moving `R1a` out of the session scratchpad into the evaluation code. Copy `v1err/rules.py`, `v1err/multi.py` and
    `v1err/mapparse.py` to `assetgen_meta/prompt_opt/scratch_archive/` before the scratchpad is cleared.

## Note for the next iteration (reasoning, not a measurement)

- 6 of the 8 "Other" v1 r0 matches are registered read-outs of memory arrays in one cache module. They pass the value
  read on to an output port.
- Section 3 has a "Prompt" row with a basis for this kind of register: "A register that holds a value only while
  moving it between its entry and exit is secondary" (LAsset p2).
- v1's edit A keeps them as realization points: line 126 counts "a CARRIES or SOURCES record into an output port" as
  a use.
- Any next edit here must cite that row. It must not touch settings or self-updating state.
