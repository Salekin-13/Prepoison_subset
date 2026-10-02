# Blind-agent prompt study: pre-registration

Fixed 2026-10-01, before any prompt is written. Requested by the user: design a prompt with which a blind agent finds
the assets of a module from its RTL and relation map alone, scoring high precision and recall against the LAsset
manual reference, without leaking anything about the reference; test, validate, select a winner; analyse what makes a
prompt good; only then compare the winner with our current prompt (`m7e194es0ism`) and the baseline (`v2x3r8`).

## Who sees what

| role | reads | never reads |
|---|---|---|
| designer (5, independent) | `TASK_BRIEF.md`, `MAP_FORMAT.md`, the 2 design inputs (boot_rom, fifo: no reference entries exist for them), the 5 theory PDFs; in round 2 also its own prompt, its executor's outputs and a critic report | the reference, any score, any earlier prompt of this project, any other file of the repository, other designers' prompts |
| executor (Claude agent, session model) | one prompt file + one input file | anything else |
| blind critic (round 2) | one prompt, the executor outputs of that prompt, the inputs of the modules it checks, `MAP_FORMAT.md` | the reference, any score |
| main loop (me) | everything; scores by code | gives designers and critics no score and no reference-derived fact |

Blindness is enforced after the fact: every agent's tool calls are read from its transcript; an agent that touched
any file outside its list, ran a command, searched, or used the web is void and its work is redone.
Leaks into prompts are checked by code (`leak_check.py`: corpus identifiers, numeric hints, comment use).

## Inputs

`build_inputs.py` (self-tested: every map occurrence matches its numbered RTL line, 5,760/5,760 tuning and
11,997/11,997 held-out; the line format parses back to the compact map in 43/43 modules; no line over 1,500 chars;
guards over 400 chars cut: 1 of 2,961 tuning records, 162 of 8,895 held-out).

## Rounds

1. **Design, round 1**: designers A-E, one angle each (A definition-first, B threat-first, C map procedure,
   D minimal, E worked examples from the sources' own case studies). Version ids `A1` ... `E1`.
2. **Screen**: each version, 1 run x 15 tuning modules (111 reference entries).
3. **Design, round 2** (no score shown): each designer gets its executor's 15 outputs and a blind critic's report on
   them (instructions misread or ignored, inconsistent decisions, ambiguous wording, output-format faults) and writes
   `A2` ... `E2`.
4. **Screen**: each round-2 version, 1 run x 15 modules.
5. **Validate**: the two versions with the highest screen F1 (of the ten) get 2 more runs each (3 in all).
6. **Select** (rule fixed here): the highest mean F1 over its 3 runs, strict scorer, 15 tuning modules; if the top two
   are within 0.02 F1, the one with higher mean recall. Precision and recall are reported every time, never F1 alone.
7. **Held-out, once**: the selected prompt, 3 runs x 26 held-out modules (189 entries). Reported next to LAsset
   initial on the same modules (P 0.734 / R 0.862, 222 emitted) and, once the lever study's held-out reading is taken,
   our pipeline's held-out row. Taken after that reading, never before.
8. **Only then**: the analysis of prompt qualities, and the comparison with `m7e194es0ism` and `v2x3r8` run under the
   same blind protocol (same executor, same inputs, 3 runs x 15 modules each, their own output contracts flattened by
   code).

## Deviations (recorded as they happened)

- **Round 2, critic reports not delivered (2026-10-01).** The harness refused each critic's Write of `report.md`
  ("Subagents should return findings as text"); the critics returned the reports as text, and the revisers, finding no
  file, reviewed their executor's 15 outputs against the RTL themselves (still reference-blind). The five reports are
  saved afterwards, verbatim, in `critic/<version>/report.md` (`save_critic_reports.py`); no reviser saw them. A2-E2 are
  therefore self-reviewed revisions, not critic-guided ones.
- **Audit rule clarified:** a Grep inside one handed file counts as a read of that file (two revisers used it on their
  own inputs and prompts); a Grep or Glob over a folder stays a violation. Self-test extended.

- **Runs 3 -> 2 (2026-10-01, user's instruction after the Claude usage limit was hit mid-validation).** Validation,
  selection, held-out and the step-8 comparison all use 2 runs per version (r0, r1). Selection: the highest mean F1
  over r0 and r1; within 0.02, the higher mean recall. The interrupted validation run left 7 output files whose agents
  never confirmed completion: deleted and redone. Its partial third run (D1 r2, D2 r2: 6 files each) is set aside in
  `runs_unused/` and never scored. With 2 runs, majority vote is not defined (2 of 2 = intersection); no MV row is
  reported for the blind study.

## Selection (2026-10-01, by the rule above, 2 runs)

Tuning, 15 modules, 111 entries, strict scorer, mean of r0 and r1: **D1 P 0.359 R 0.577 F1 0.442** (178.5 emitted per
run; runs 0.358/0.577 and 0.360/0.577); D2 P 0.327 R 0.572 F1 0.416 (194.0). Gap 0.026 > 0.02: **winner D1**. All
agents of the validation pass the blindness audit (60/60 interrupted run, 27/27 completion run). Step 8 prompt files
were written only after this: `prompts/CUR` (m7e194es0ism, sha256 0d0def4c6fe3) and `prompts/BASE` (v2x3r8, sha256
3c543758f459), both byte-identical to the recorded fingerprints (`build_compare_prompts.py`).

## Caveats fixed in advance

- Selection among ten versions on 15 modules with one screen run each favours a lucky version; the 3-run validation and
  the held-out reading are the guard.
- The executor (a Claude agent) differs from the notebook's gpt-5-mini; the step-8 comparison runs all prompts on the
  same executor so the prompt is the only difference.
- LAsset's paper is a design source and shows a few examples; the reference was written by the same group.
- Selecting by reference score is the only reference information that reaches the study, and it reaches only the
  choice, never a designer.
