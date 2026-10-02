# Blind-agent prompt study: report

2026-10-01. Protocol and every deviation: `PREREG.md`. All numbers below are from runs made in this study, scored
with `eval_assets.score(strict=True)`; precision (P) and recall (R) are always named. Tuning = 15 modules, 111
reference entries; held-out = 26 modules, 189 entries. "Run" = one agent per module over the whole set.

## 1. How to prompt a blind agent without leaking the reference

The leak can enter in four places. Each is closed by construction and then checked.

| leak path | how it was closed | how it was checked |
|---|---|---|
| the prompt text | designers never saw the reference, a score, or any earlier prompt; rules had to cite a source page | `leak_check.py`: no identifier from either module set or the reference, no numeric quota, no comment use (10/10 blind prompts PASS) |
| the designers' reading | designers read only the brief, the map format, the two modules that have no reference entries (boot_rom, fifo) and the five theory papers | `audit.py` reads every tool call of every agent; any other file, command, search or web use voids the agent |
| the executor's reading | each executor reads one prompt file and one input file (numbered RTL + code-built relation map) | same audit: 349/349 executor agents pass (53 of them stopped early by the usage limit and were redone); 15/15 designer and critic agents pass |
| feedback during design | round 2 gave designers only their own outputs; no score, no reference fact | the only reference information that reached the study is the selection between finished prompts |

Validation is by aggregate score only, with the winner chosen by a rule fixed in advance, then read once on the
held-out modules.

## 2. Results

| prompt | set | runs | P | R | F1 | listed per run |
|---|---|---|---|---|---|---|
| A1 definition-first | tuning | 1 | 0.357 | 0.225 | 0.276 | 70 |
| B1 threat-first | tuning | 1 | 0.315 | 0.459 | 0.374 | 162 |
| C1 map procedure | tuning | 1 | 0.308 | 0.541 | 0.392 | 195 |
| **D1 minimal** | tuning | 1 | 0.358 | 0.577 | 0.441 | 179 |
| E1 worked examples | tuning | 1 | 0.507 | 0.315 | 0.389 | 69 |
| A2 / B2 / C2 / D2 / E2 (self-revised) | tuning | 1 | 0.326 / 0.353 / 0.311 / 0.325 / 0.449 | 0.261 / 0.486 / 0.505 / 0.568 / 0.279 | 0.290 / 0.409 / 0.385 / 0.413 / 0.344 | 89 / 153 / 180 / 194 / 69 |
| **D1 (validation, winner)** | tuning | 2 | **0.359** | **0.577** | **0.442** | 178.5 |
| D2 (validation) | tuning | 2 | 0.327 | 0.572 | 0.416 | 194.0 |
| **D1** | **held-out** | 2 | **0.362** | **0.619** | **0.457** | 323.5 |
| LAsset initial (no CWE refinement) | held-out | - | 0.734 | 0.862 | 0.793 | 222 |
| our gpt-5-mini pipeline, winner prompt | held-out | 3 | 0.352 | 0.852 | 0.498 | 458 |
| same + MV+NONE+BF (adopted) | held-out | MV | 0.399 | 0.884 | 0.550 | 419 |

Winner: **D1** (`prompts/D1/prompt.md`, 6,593 characters). On held-out it scores as on tuning (P 0.362 vs 0.359, R
0.619 vs 0.577): it carries nothing tuned to these modules. It does not reach high recall: R 0.62 against 0.86 for
LAsset initial and 0.85 for our pipeline.

## 3. What makes a prompt good (from these ten prompts)

Measured, on one executor (Claude, session model) and one input form; ten prompts, one screen run each, so a single
F1 difference under about 0.03 is not a finding.

1. **Say what to list, by kind, including where values enter and leave.** D1 lists the kinds of conceptual asset
   (data, settings, progress state, decisions and events) and maps each to its holder AND to the ports it enters or
   leaves by. It has the highest recall of the ten. A1 makes the port a fallback "only when nothing stores the value"
   and finds 0 of 26 reference input ports (R 0.225).
2. **Exclusion lists cost recall and buy little precision.** All ten prompts carry long "leave out" lists; precision
   stayed at 0.31-0.36 for every prompt except E1/E2 (0.507/0.449), which list about 70 elements per run and pay with
   recall 0.32/0.28. A1/A2 list 70-89 and still sit at 0.357/0.326: listing less did not by itself raise precision.
3. **Short beats long when the content is the same.** D1 (6.6k characters) beats every longer blind prompt (19.8k-34.2k);
   D2, its 37% longer revision, scores lower (F1 0.416 vs 0.442 over 2 runs).
4. **A short definitional prompt is reproducible.** D1's two runs: 0.358/0.577 and 0.360/0.577. BASE's: 0.381/0.793
   and 0.380/0.712.
5. **Self-review without the reference does not move the score.** Round 2 changed F1 by -0.045 to +0.035 (inside one-run
   noise) while the prompts grew by 34-62%. Making a prompt more internally consistent does not make it agree more
   with an external labelling.
6. **Naming granularity is a large precision lever.** Every blind prompt named fields of record ports (D1: 31.5 per run,
   all false positives; the reference lists no port field). Dropping them from D1's own outputs by code: P 0.359 ->
   0.432, R 0.577 -> 0.568.
7. **A prompt's quality depends on the executor.** BASE: P 0.296 R 0.853 on gpt-5-mini (3 runs, RTL only), P 0.380 R
   0.752 on Claude (2 runs, RTL + map). CUR: 0.344/0.847 and 0.334/0.820. (Executor and input both differ between those
   pairs.)

## 4. The winner against our current prompt and the baseline (run only after the selection)

Same executor, same inputs (RTL + map), 2 runs each, tuning:

| prompt | characters | P | R | F1 | listed per run |
|---|---|---|---|---|---|
| D1 (blind winner) | 6,593 | 0.359 | 0.577 | 0.442 | 178.5 |
| CUR `m7e194es0ism` (current) | 103,678 | 0.334 | 0.820 | 0.475 | 272.5 |
| BASE `v2x3r8` (baseline) | 110,540 | 0.380 | 0.752 | 0.505 | 219.5 |

By element kind, per run (reference count in brackets; hits / false positives):

| kind | D1 | CUR | BASE |
|---|---|---|---|
| input ports (26) | 16 / 3.5 | 19 / 12.5 | 17 / 15 |
| output ports (21) | 17 / 9.5 | 21 / 14 | 15.5 / 23.5 |
| internal signals (32) | 12 / 19.5 | 22.5 / 42 | 24.5 / 34.5 |
| internal record fields (30) | 19 / 50.5 | 28.5 / 113 | 26.5 / 63 |
| port record fields (0) | 0 / 31.5 | 0 / 0 | 0 / 0 |

How they differ, and what each difference does:

| difference | text | impact (measured) |
|---|---|---|
| **Port granularity.** CUR and BASE name a port whole; D1 says "each port, or field of a record port" | CUR lines 16 and 220 ("A port is a whole candidate. Never report a port field"); BASE line 33 ("Record-typed PORTS are named WHOLE") | D1 lists 31.5 port fields per run, all false positives; CUR and BASE 0. Removing them from D1's outputs: P +0.073, R -0.009 |
| **Strobes, enables, selects, handshakes.** D1 leaves them out ("request and command strobes ... valid and ready ... write enables ... addresses"), citing LAsset p2 and SAIF p2 (enables and selects are secondary). CUR treats an input the entity reads to store, compute or decide as where a value is "set" | CUR line 13 (consumed-input rule) and line 12 ("including a decision or event the module computes") | 33 reference entries are found by CUR in both runs and by D1 in neither. By my reading of their names and roles, 23 of them are strobes, enables, selects, handshakes or addresses (we_i, start_i, valid_o x3, stb, sel, rden, div.start, mul.start, fifo.re, ...), 4 are decisions (pmp fail, wdt cnt_timeout, reset_wdt, keeper.halt), 6 other |
| **Coverage of internal signals and fields.** CUR's realization labels (stores / sets / computes / exit port) and its worked examples push it to list more internal elements | CUR lines 205-208 (the four labels) and its worked examples (the second part of the prompt) | internal signals 22.5 vs 12 hits per run, at 42 vs 19.5 false positives; record fields 28.5 vs 19 hits at 113 vs 50.5 |
| **Interrupt inputs.** D1 names "an interrupt request" as a kind of event and lists the ports values enter by | D1 lines 34-35 and 40 | 7 entries D1 finds and CUR never does: the CPU's interrupt inputs (firq_i, mei_i, msi_i, mti_i, dbi_i), lsu_err, pmp_fault |
| **Length and form.** D1 is a definition + decision procedure with no examples; CUR and BASE are 15-17x longer, mostly worked examples | - | on this executor, BASE has the best F1 (0.505) and the best precision (0.380); CUR the best recall (0.820) |

Where the two big rules came from: the whole-port rule and the consumed-input rule were measured against the reference
earlier in this project (memory: "a dotted field of a PORT record is never a primary asset: reference 0 of 31"; the
input-port and captured-input arms). They are what a blind designer cannot know: the designers cite LAsset p2 and SAIF
p2 for treating enables and selects as secondary (their rationale files; I have not re-read those pages this session),
and none of them found a source on port granularity.

## 5. Reading

- A blind, theory-only prompt reaches P 0.36 / R 0.58-0.62 here, stable across runs and modules. That is roughly our
  current prompt's precision at much lower recall.
- Most of the gap to the reference is **labelling conventions of the reference** that its own paper does not state:
  control strobes, enables, selects and handshakes count as primary (the designers read the papers as calling them
  secondary); port fields never
  count; memory arrays count only through their read port. A blind prompt that follows the papers is penalised for
  following them.
- So "high precision and recall against this reference, with no reference information" is not reachable by prompt
  wording alone on this data. The convention gap has to be either learned from the reference (what CUR and BASE did,
  which is a leak by construction) or argued from a source that states it.
- REASONING, not measured: a whole-port rule could be argued from LAsset's own method (its parser lists ports, and its
  outputs never name a port field), which would make it admissible in a blind prompt; the strobe convention has no
  such source here.

## 6. Limits

- One executor (Claude, session model); the notebook executor is gpt-5-mini. Prompt rankings differ between them (row 7
  above).
- 2 runs per validated version (user's instruction after the usage limit; `PREREG.md`); 1 screen run for the other
  eight versions.
- Round 2 ran without the critic reports (harness refused subagent report files; `PREREG.md`).
- The classification of the 33 entries in section 4 is my reading of names and roles, not a code check.

## Files

`build_inputs.py` (inputs, self-tested), `TASK_BRIEF.md`, `MAP_FORMAT.md`, `PREREG.md`, `leak_check.py`, `audit.py`
(self-tested), `score_blind.py` (self-tested against a stored run), `diagnose.py`, `misses.py`, `compare.py`,
`build_compare_prompts.py`, `prompts/<version>/{prompt,rationale}.md`, `critic/<version>/report.md`,
`runs/<split>/<version>/r<k>/`.
