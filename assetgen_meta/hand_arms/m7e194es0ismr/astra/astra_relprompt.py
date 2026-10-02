"""Asset prompt + relationship map, on gpt-6-astra.
  gen       astra writes ONE new section for the frozen winner m7e194es0ism (seed + worked examples stay byte-identical)
  critique  astra critiques that section and returns an improved one
  fix <src> only if the code checks fail on <src>
Every stage assembles seed + section + examples and runs the project's prompt checks."""
import json, os, sys
from pathlib import Path

ROOT = Path("E:/jobs/ff/test/Prepoison_subset"); os.chdir(ROOT)
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "assetgen_meta")); sys.stdout.reconfigure(encoding="utf-8")
for _line in (ROOT / "API.env").read_text(encoding="utf-8").splitlines():
    if "=" in _line and not _line.strip().startswith("#"):
        _k, _v = _line.split("=", 1); os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
import meta_tools as mt

HERE = Path(__file__).parent
SEED = (ROOT / "assetgen_meta/runs/meta_7e194e6254be_gpt-6-astra/sample_0/exec_prompt.txt").read_text(encoding="utf-8")
ISM = (ROOT / "assetgen_meta/hand_arms/m7e194es0ism/exec_prompt.txt").read_text(encoding="utf-8")
EXAMPLES = ISM[len(SEED) + 2:]
assert ISM == SEED + "\n\n" + EXAMPLES and mt.sha12(SEED) == "e8df164fddb3", "the winner is not seed + examples"
_RELP = (ROOT / "bahavioral_patterns_of_assets/annotation_pack_elements/relation_prompts_v1/"
         "relation_system_prompt.md").read_text(encoding="utf-8").splitlines()
REL_DEFS = "\n".join(_RELP[57:70]) + "\n\n" + "\n".join(_RELP[75:128])      # program fields; section 3 table + rules
_P = (HERE.parent / "p3164_pages.txt").read_text(encoding="utf-8").split("\n<<<PAGE ")
_KEEP = set(range(6, 14)) | set(range(15, 20)) | set(range(21, 25))
P3164 = "\n".join("PAGE " + b for b in _P if b.split(">>>")[0].strip().isdigit() and int(b.split(">>>")[0]) in _KEEP)
EXAMPLE_MAP = (HERE / "example_map_compact.json").read_text(encoding="utf-8")[:7000]
BLOCK = "=== RELATIONSHIP MAP ==="
NONE_TEXT = "(none for this module)"

EVIDENCE = """RECORDED RESULTS (project log; precision = share of reported elements that are in the reference list, recall =
share of reference elements reported; 15 modules, reference list of 111 elements):
- Baseline prompt: precision 0.296, recall 0.853. SEED (frozen part 1, a concept-first procedure): confirmation over 3
  runs precision 0.379, recall 0.787. SEED + WORKED EXAMPLES (frozen part 2; the current best, the prompt you extend):
  precision 0.344, recall 0.847. The examples restored recall (mostly input ports read by the entity).
- An earlier arm already gave the generator a relation annotation next to the RTL (parsed element list + an occurrence
  annotation + a reading procedure): precision unchanged (0.240 vs 0.251), recall fell 0.078. Measured cause: the
  element list "became a menu" -- the model named candidates from the list, about seventy extra emissions. The new
  section must make that impossible: the map is never a source of candidates.
- The seed's false positives (145, majority vote over 3 runs), grouped by family: copy relays 44 (an element that only
  carries another element's value), decision chains 33 (elements upstream of a decision), record-field fan-out 26,
  other 20, reset/clock 17, port plumbing 4. A theory review judged 63 of them plausible assets the reference omits (do
  NOT tune against those), 48 carriers of a concept realised elsewhere, 33 mechanisms.
- The seed's recall losses (21): the concept was realised at another element 10, excluded by the seed's own rules 5,
  reference limits 5, other 1.
- The relationship map itself: written by an annotator model checked by a program. A blind adjudication estimated its
  precision near 0.95 and recall near 0.84 (relationships missed by both were not counted). So a relationship that is
  present is usually right; a relationship that is ABSENT is not evidence of absence. The RTL is the authority."""

RULES = f"""HARD CONSTRAINTS on the text you write (a program checks the first four):
1. No identifier from any real design: use placeholders such as <elem>, <reg>, <port>, <cond>. Quote no names from the
   example map or the P3164 text.
2. No numeric emission hints: never "at most N", "at least N", "N assets/elements/signals/ports/concepts", "%",
   "half", "a third".
3. Never tell the model to read or rely on comments (a prohibition is fine).
4. Add no output field, change no schema key, no realization value ("stores", "sets", "computes", "exit port"), no stage
   name; the frozen output contract governs. The prompt must still say to return only the final JSON object (the seed
   already does; do not contradict it).
5. Contradict no rule of the frozen parts. Where the map would suggest something a frozen rule forbids, the frozen rule
   wins; say so.
6. Every rule you add must rest on P3164 (cite its section or example in your analysis, not in the prompt text) or on
   the frozen seed. No rule may rest on counts from a reference list. Paraphrase P3164; do not quote it.
7. The map is evidence about elements the procedure has ALREADY reached from the RTL through a concept. It never
   proposes a candidate, and no element is reported because it appears in the map.
8. The user message carries the map after the RTL, under the line: {BLOCK}. For a module without a map that block
   holds only: {NONE_TEXT}. The section must name both and say what to do then (the frozen procedure alone).
9. Keep the section as short as its content allows; it joins a prompt of about one hundred thousand characters."""

MAP_FORMAT = f"""THE MAP (compact view of the relation stage's final JSON; one file per module):
{{"ports": [...], "signals": [...]}}; each element: name, entity, kind (register | signal, internal signals only), dir /
boundary (ports), functionality (the annotator's one- or two-sentence description of what the logic does), handling
(record fields: ORIGINATES / CONSUMES / FORWARDS), storage ("edge" = assigned on a clock edge), constant_drivers (literal
or constant values and their lines), configuration (generic/constant conditions under which it is declared or driven,
with lines), connections (wiring to sub-block ports), relationship: [{{type, targets, guard (for GATES / SELECTS /
CONSTRAINS and their partners: the condition or selector text), bits, lines (RTL line numbers of this element's
occurrences that carry the relationship)}}]. The full file's occurrence list is dropped from this view; lines point
into the RTL.

RELATIONSHIP DEFINITIONS the annotator followed (driving record at Y, receiving record at X, for X = F(Y)):
{REL_DEFS}"""


def assemble(section: str) -> str:
    return SEED + "\n\n" + section.strip() + "\n\n" + EXAMPLES


def checks(prompt: str, label: str) -> dict:
    r = mt.check_exec_prompt(prompt, mt.corpus_names(), label)
    for w in (BLOCK, NONE_TEXT):
        if w not in prompt:
            r["problems"].append(f"missing: {w}")
    r["frozen_prefix"] = prompt.startswith(SEED + "\n\n")
    r["frozen_suffix"] = prompt.endswith("\n\n" + EXAMPLES)
    r["ok"] = not r["problems"] and r["frozen_prefix"] and r["frozen_suffix"]
    return r


def ask(system, user, tag, max_out=40000):
    from openai import OpenAI
    client = OpenAI().with_options(timeout=1800, max_retries=0)
    txt, u, status = mt.call_text(client, "gpt-6-astra", system, user, "high", max_out, retries=3, json_mode=True)
    A = mt.loads(txt)
    (HERE / f"{tag}.json").write_text(json.dumps({"usage": u, "answer": A}, indent=1), encoding="utf-8")
    print(f"{tag}: tokens in {u['in']:,} out {u['out']:,}, ~${u['in'] * 10 / 1e6 + u['out'] * 50 / 1e6:.2f}")
    return A


GEN = f"""You are extending an LLM prompt that identifies the security assets (ports and signals) of a VHDL module. The
executor model reads this prompt as its system prompt; its user message carries the comment-stripped RTL of one module
and, new in this version, that module's RELATIONSHIP MAP. Your job: write ONE new section that teaches the executor
how to reason with the map alongside the RTL, so it decides more accurately whether an element it has reached is a
security asset. Everything else is FROZEN.

FROZEN PART 1 -- the seed execution prompt, in full (proved to raise precision; keep every rule):
<<<SEED
{SEED}
SEED>>>

FROZEN PART 2 -- worked examples appended after your section (proved to restore recall; they predate the map and show
no map). Their opening, for their structure only:
<<<EXAMPLES (excerpt)
{EXAMPLES[:5000]}
EXAMPLES>>>

The assembled prompt will be: FROZEN PART 1, your section, FROZEN PART 2. Nothing in the frozen parts can change.

{MAP_FORMAT}

AN EXAMPLE MAP (compact view, one real module, truncated; for the format only -- copy no name from it):
{EXAMPLE_MAP}

IEEE P3164 white paper, "Asset Identification for Electronic Design IP" (extracted text, selected pages). Its section
3.1.1 asks four questions (confidentiality, integrity, availability, undermined behaviour); 3.1.2 says structural assets
are the RTL that produces, stores and transports a conceptual asset's value; section 4 narrows to points where the asset
can be observed or influenced:
<<<P3164
{P3164}
P3164>>>

{EVIDENCE}

{RULES}

FIRST answer these questions (your analysis; it is not prompt text):
Q1. For each P3164 question (C, I, A, undermined behaviour), which map facts are evidence for or against an element
    holding a conceptual asset, and how should the executor read them for an element it has already reached? Be
    concrete about relationship types, guard, storage, boundary, constant_drivers, configuration, handling.
Q2. How can the map separate an asset from a copy relay, a decision-chain input, a record-field fan-out element and a
    reset/clock element, without losing input ports the entity reads or concepts realised at one element? Name the
    pattern of relationships for each case and the P3164 basis.
Q3. At which of the seed's stages does the map enter, and what does it change in each? (No new stage names.)
Q4. What can go wrong (menu effect, annotator errors, missing map, very large maps), and what in your section
    prevents it?

THEN write the section. Return one json object:
{{"analysis": {{"q1": "...", "q2": "...", "q3": "...", "q4": "...", "p3164_basis": ["<rule> <- <P3164 section/page>"]}},
  "section": "<the full text of the new section, with its own heading>"}}"""

CRIT = f"""You are reviewing a new section written for an LLM prompt that identifies the security assets (ports and
signals) of a VHDL module. The section teaches the executor how to use a RELATIONSHIP MAP (given in the user message
after the RTL) together with the RTL. The rest of the prompt is FROZEN and cannot change. Find the gaps and errors in
the section, then write an improved version.

FROZEN PART 1 -- the seed execution prompt, in full:
<<<SEED
{SEED}
SEED>>>
(FROZEN PART 2, worked examples without any map, follows the section.)

{MAP_FORMAT}

IEEE P3164 white paper (extracted text, selected pages):
<<<P3164
{P3164}
P3164>>>

{EVIDENCE}

{RULES}

THE SECTION UNDER REVIEW, and its author's analysis:
<<<SECTION
@@SECTION@@
SECTION>>>
<<<ANALYSIS
@@ANALYSIS@@
ANALYSIS>>>

Check in particular:
a. Any contradiction with a frozen rule, stage, schema key, realization value or the final-JSON instruction.
b. Any way the map can still act as a candidate list (the measured menu effect), including "check every element of
   the map" style steps.
c. Misreadings of the relationship definitions (e.g. treating a GATES record as proof of an asset, CARRIES/COPIES
   direction, RESETS/SEQUENCES semantics, what guard and storage mean, absent relationships taken as evidence).
d. Whether each P3164 question is mapped to map facts correctly, and whether any rule lacks a P3164 or seed basis or
   rests on reference-list statistics.
e. Recall risks: input ports the entity reads, concepts realised at one element, elements the map omits.
f. Precision gains the section misses: copy relays, decision chains, record-field fan-out, reset/clock.
g. The hard constraints 1-9, the missing-map case, length, and clarity for a mid-size model.

Return one json object:
{{"issues": [{{"severity": "high|medium|low", "where": "<a few words of the section>", "problem": "...", "fix": "..."}}],
  "improved_section": "<the full improved section, with its heading>",
  "changes": ["<one line per change and the issue it fixes>"]}}"""

FIX = ("The section below fails the program checks listed after it. Return one json object {\"section\": \"<the "
       "corrected full section>\"} that fixes exactly those problems and changes nothing else.\n<<<SECTION\n@@SECTION@@\n"
       "SECTION>>>\nPROBLEMS: @@PROBLEMS@@\n\n" + RULES)

REVISE = f"""A section for an LLM prompt that identifies the security assets (ports and signals) of a VHDL module went
through one draft and one critique. The reviewed version guards well against misuse of the RELATIONSHIP MAP, but it is
almost entirely negative: it tells the executor what the map does NOT prove, and never how to READ the map to decide
whether an element it has already reached from the RTL is a security asset. That was the section's purpose. Your own
earlier analysis answered it (below). Write the final section.

Requirements:
R1. Keep every guard of the reviewed version: the map is never a candidate source (the measured menu effect), frozen
    rules win, absent relationships are no evidence, labels are not asset classes, functionality is a hypothesis,
    RTL verification, the missing-map case, the final-JSON instruction.
R2. Add a short positive procedure for an element already reached through a concept: read its map entry through the
    four P3164 questions (confidentiality, integrity, availability, undermined behaviour) -- for each, which
    relationship types, guard, storage, boundary, constant_drivers, configuration, handling and connections facts
    support that the element produces, stores or transports the concept's value (P3164 3.1.2), and what the executor
    then verifies in the RTL. Paraphrase P3164; do not quote it.
R3. Add, per case, the relationship pattern that marks a copy relay, a decision-chain input, a record-field fan-out
    element and a reset/clock element, and the pattern that marks the element that realises the concept, so the
    executor keeps the realising element and drops the carrier -- without dropping input ports the entity reads or a
    concept realised at one element. Each rule must rest on P3164 or the frozen seed.
R4. Plain, short sentences a mid-size model follows reliably. Name the seed's stages exactly as the seed does. No
    grammar shortcuts such as "Keep build the closed set ... RTL-only".
R5. The hard constraints below.

FROZEN PART 1 -- the seed execution prompt, in full:
<<<SEED
{SEED}
SEED>>>

{MAP_FORMAT}

{EVIDENCE}

{RULES}

YOUR EARLIER ANALYSIS (q1-q4, P3164 basis):
<<<ANALYSIS
@@ANALYSIS@@
ANALYSIS>>>

THE REVIEWED SECTION:
<<<SECTION
@@SECTION@@
SECTION>>>

THE REVIEW'S ISSUES (already addressed in the reviewed section; do not reintroduce them):
@@ISSUES@@

Return one json object: {{"section": "<the final full section, with its heading>",
  "changes": ["<one line per change against the reviewed section>"],
  "p3164_basis": ["<rule> <- <P3164 section/page or seed rule>"]}}"""

if __name__ == "__main__":
    stage = sys.argv[1]
    if stage == "revise":
        g = json.loads((HERE / "gen.json").read_text(encoding="utf-8"))["answer"]
        c = json.loads((HERE / "critique.json").read_text(encoding="utf-8"))["answer"]
        A = ask("You design prompts for hardware-security LLM pipelines. You return only the json object asked for.",
                REVISE.replace("@@ANALYSIS@@", json.dumps(g["analysis"], indent=1))
                      .replace("@@SECTION@@", c["improved_section"])
                      .replace("@@ISSUES@@", json.dumps(c["issues"], indent=1)), "revise")
        sec = A["section"]
        (HERE / f"section_{stage}.txt").write_text(sec, encoding="utf-8")
        full = assemble(sec); r = checks(full, stage)
        print(f"section {len(sec):,} chars; assembled {len(full):,} chars, sha {mt.sha12(full)}; checks:",
              "PASS" if r["ok"] else r["problems"], "| frozen prefix", r["frozen_prefix"], "suffix", r["frozen_suffix"])
        sys.exit()
    if stage == "gen":
        A = ask("You design prompts for hardware-security LLM pipelines. You return only the json object asked for.",
                GEN, "gen")
        sec = A["section"]
    elif stage == "critique":
        g = json.loads((HERE / "gen.json").read_text(encoding="utf-8"))["answer"]
        A = ask("You are a strict reviewer of hardware-security prompts. You return only the json object asked for.",
                CRIT.replace("@@SECTION@@", g["section"]).replace("@@ANALYSIS@@", json.dumps(g["analysis"], indent=1)),
                "critique")
        sec = A["improved_section"]
        for i in A["issues"]:
            print(f"   [{i['severity']}] {i['where'][:60]!r}: {i['problem'][:160]}")
    elif stage == "fix":
        d = json.loads((HERE / f"{sys.argv[2]}.json").read_text(encoding="utf-8"))["answer"]
        sec0 = d.get("improved_section") or d.get("section")
        r0 = checks(assemble(sec0), "fix-input")
        A = ask("You correct prompt text exactly. You return only the json object asked for.",
                FIX.replace("@@SECTION@@", sec0).replace("@@PROBLEMS@@", json.dumps(r0["problems"])), "fix")
        sec = A["section"]
    else:
        sys.exit("stage: gen | critique | fix <src>")
    (HERE / f"section_{stage}.txt").write_text(sec, encoding="utf-8")
    full = assemble(sec)
    r = checks(full, stage)
    print(f"section {len(sec):,} chars; assembled {len(full):,} chars, sha {mt.sha12(full)}; checks:",
          "PASS" if r["ok"] else r["problems"], "| frozen prefix", r["frozen_prefix"], "suffix", r["frozen_suffix"])
