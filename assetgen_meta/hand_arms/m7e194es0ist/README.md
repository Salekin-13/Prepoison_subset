# Arm m7e194es0ist: the winner restructured, every decision traceable

Built 2026-10-01 at the user's request. Prompt `exec_prompt.txt` (sha `fa07ad720438`, 193,492 characters:
instructions 26,749, worked examples 166,743). Not run yet; notebook `assetgen_meta.ipynb` cells 42-45.

## The user's eight points, and where each lives

| point | prompt section | code |
|---|---|---|
| 1 the two inputs, accurately described | 1 What you are given | `traced_inputs.py` builds them (self-tested: every map occurrence on its numbered RTL line, 5,972/5,972 tuning, 11,997/11,997 held-out) |
| 2 a clear asset definition | 2 What an asset is (ASSET_DEFINITION.md section 2) | - |
| 3 purpose and use-case flows | 3 Purpose and use-case flows; output "module purpose", "use-case flows" | report: flows table with line check |
| 4 the flow graph | 4 The flow graph (use it, do not recompute) | `traced_inputs.flow_graph`: edge symmetry, paths from every input and constant-valued element to stores / exits / sub-unit connections with influence points, control-only sources, no local use |
| 5 four questions per value, each with a line | 5 Four questions; output "questions", "hypotheses" | report: each yes with its line text |
| 6 roles along the path | 6 Roles; output "related structural assets" (primary) and "influence points" | `trace_check.fits` |
| 7 exclusions with a reason | 7 Exclusions; output "exclusions" | report: exclusions by reason |
| 8 checks: occurrence ID + edge, nothing on its name | 8 Checks; output "occurrence", "edge" per element | `trace_check.check_citation`: verified / role unfit / occurrence only / map gap claimed / invalid / no citation |

## Kept from the winner (ASSET_DEFINITION.md section 3, rows with a measured contribution)

Verbatim: the consumed-input "sets" rule and several references per flow (winner line 13), carriers secondary (13, 15,
17), transport excluded whole and by field (16, 221-222), sub-block connection fields (17, 223-224), clock /
clock-enable / reset inputs (13, 219), port named whole (16, 19, 220), the four realization labels (205-208), the
restrictions (212-226), precedence (228), naming (230), objective serialization (275), the C / I / A criteria (section
6), the dependency rule (97). The worked examples keep their decisions exactly (`check_examples.py` check 4).

Changed on purpose: the definition takes ASSET_DEFINITION.md section 2, including row 1 ("a state, setting or decision
element realizes its own concept"; arm ismd tested this with the transit rule and was not adopted). The evidence levels
become "a C / I / A yes with a mechanism line and no outside premise"; a yes without a line is a hypothesis.

## Traceability

The model cites, per reported element, an occurrence ID and an edge from the map; per yes answer an RTL line; per flow
its lines. `trace_check.py` verifies each citation and writes one readable report per module and run:
`assetgen_meta/traces_ist/m7e194es0ist/r<k>/<module>.md` (purpose, flows, the four answers with line text, each
reference with its cited line, edge and status, influence points, hypotheses, exclusions; a reference column for
analysis). "Verified" is a necessary condition (the citation is real and fits the role), not proof that the element
is an asset. `cite_filter` gives an evaluation-layer row with verified references only.

## Checks run before any executor call

- `traced_inputs.py` self-test; `trace_check.py --selftest` (12 cases, including a whole record port cited through
  its field, an influence point cited from the wrong side, an internal element claimed as an exit port).
- `check_examples.py`: both examples pass all six checks (occurrences equal a code table; record lines match IDs;
  every cited edge has its mirror; decisions unchanged; every citation verified; leak check).
- `meta_tools.check_exec_prompt` and the leak check on held-out + tuning names: PASS.
- An independent rule audit (Claude agent) against the winner and ASSET_DEFINITION.md: its findings applied (input
  ports never influence points; a concept needs a C / I / A yes with a line and no outside premise; one fit table in
  prompt and code; restored dropped winner rules; a word list that named real signals replaced).
- Two pilots, blind Claude executors on wdt, hwspinlock, muldiv (format test only; the notebook executor is
  gpt-5-mini): pilot 2 after the audit fixes, 44/44 references verified, 6/6 influence points, 38/38 yes answers with a
  real line, 157/157 flow lines; 21 of 22 reference entries found, 37 listed on those three modules. Reports in
  `assetgen_meta/traces_ist/_pilot/`.

## Known risks (measured before on gpt-5-mini; pre-registered in `read_trace_arm.py` R3)

- The map in the input cost recall (arm ismr: 0.778 vs 0.847).
- The four questions cost recall (arm ismq: -0.09).
- A separate output list for non-reported elements cost recall (arm v2sec: 0.925 -> 0.628).
- The prompt is 1.9 times the winner's length, mostly the examples' map excerpts.
- The comparison with the winner mixes three changes: the structure, the input, and ASSET_DEFINITION's row-1 definition.
