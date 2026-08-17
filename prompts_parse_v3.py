"""V3 RTL-parser prompts -- Algorithm 1 line 4. Occurrence-driven, open-vocabulary.

WHAT THIS STAGE IS. `rtl_parse.parse_rtl_file` extracts the elements mechanically; the RTL
text is authoritative for what exists. These prompts add meaning to elements that already
exist. The model never decides membership -- it is handed the closed set and must annotate
every entry, add none, drop none.

FOUR ANNOTATION FIELDS, on top of the mechanical name/type/dir/kind:

    functionality   1-2 sentences: what it does, what it acts on, its part in the purpose
    role            1-3 short phrases: the parts it plays in what the entity is for
    relationship    typed structural edges to named counterparts
    evidence        the construct in the source that substantiates the other three

WHY `role` IS OPEN VOCABULARY. A closed enum was built and rejected. Every candidate list
that was specific enough to be useful turned out to be shaped like the asset stage's own
conceptual rubric -- labels such as KEY_MATERIAL, CREDENTIAL, OVERRIDE_OR_BYPASS restate
that rubric's clauses almost word for word, so the parser would answer the question the
asset stage exists to ask and the asset stage would grade its own input. Re-basing the
labels onto their structural definitions fixed the wording without fixing the shape: a
fixed menu of role types still partitions the design along whatever axis the menu was
drawn on.

Open prose has the opposite failure mode -- it can smuggle a verdict in a sentence where an
enum could only smuggle it in a name. Three things hold it in check, and all three are
structural rather than hortatory:

  1. Every field must be derived from an OCCURRENCE PROFILE (below), which is a list of
     syntactic sites. An annotation that must cite a site cannot be produced from a name.
  2. `evidence` must name a construct and a counterpart. A role with no construct behind
     it fails validation rather than reaching the asset stage.
  3. The banned-word list is enforced on the OUTPUT, by `parse_v3.check_annotation`, not
     merely requested in the prompt.

WHAT THE ASSET STAGE NEEDS, AND WHERE IT COMES FROM. The downstream stage decides whether
an element carries a Confidentiality, Integrity or Availability objective. It can only do
that if this stage reports mechanism precisely, so the ROLE spec below asks five questions
whose answers are exactly the hooks that decision needs -- holds or carries, governs
whether, chooses which, crosses the boundary, externally writable -- and none of which
names an objective. That is the whole design: supply the mechanism, withhold the verdict.

COMMENT-STRIPPED INPUT. These prompts are written for `rtl_parse.strip_comments` output and
never mention comments. This is a deliberate change from the v1/v2 annotate prompts, which
told the model to infer function from "name, in-source comments, and usage". A comment is
the one place a designer can assert a conclusion the RTL does not show, and a parser told to
read comments will repeat that assertion as a finding.

REVERTED IN GEN4, AND WHY. Two rules were added in gen3 and removed again after measurement:
a prose/edge consistency rule that listed eight governing verbs, and a one-hop prose rule
that named a hop pattern. Both named a target population, and both produced the effect this
project's log records for S-1 and S-3 -- the model treats the named population as a quota.
Governing prose rose 245 -> 288 while governing EDGES fell 215 -> 201, and prose hops fell
128 -> 105. The defects they targeted are real and still open; they are not fixable by
telling this model what to look for.

STANDING RULE, inherited from v1 sec.6: no identifier from any of the 41 annotated modules
may enter a prompt. `audit()` checks the known-banned list at import;
`audit_against_corpus()` checks the full reference and closed-set name lists and is called
by `parse_v3` before any API call.
"""
from __future__ import annotations

import hashlib

# =============================================================================
# The occurrence-site taxonomy. This is the mechanical vocabulary the whole stage rests
# on: it is about WHERE an identifier appears, never about what it means. Kept closed
# deliberately -- unlike `role`, a site is a syntactic fact with a finite set of answers,
# and leaving it open would make the profiles unusable as evidence.
# =============================================================================

_SITES = """\
  DECL          its declaration or port-clause entry. Type, width, direction. Nothing more.
  COND          inside the condition of an if / elsif / when / ternary. X GOVERNS whatever
                that branch assigns. The strongest control evidence there is.
  CASE_SEL      the selector expression of a case statement. X CHOOSES among the branches.
  ENABLE_TERM   a term of an expression used as a write or output enable. X partly gates
                the enabled element.
  LHS_SEQ       left of an assignment inside a clocked process. X is STATE; the right-hand
                side sources it and the enclosing branch conditions gate it.
  LHS_COMB      left of a continuous or combinational assignment. X is a DERIVED VALUE of
                its operands.
  RESET_BRANCH  assigned in the reset branch of a clocked process. X has a defined
                recovery value and the reset element overrides it.
  RHS           anywhere in an assignment's right-hand expression. X FEEDS the assigned
                element.
  INDEX         used as an array index or bit-select. X ADDRESSES the indexed storage.
  INDEX_TARGET  X is the array being indexed. X is STORAGE.
  SLICE         X appears with a bit range on either side. Partial-width coupling.
  CONCAT        X is part of a concatenation or aggregate.
  SENS          a sensitivity list, or the argument of rising_edge / posedge / negedge.
                X supplies timing -- and ONLY timing if it has no COND, ENABLE_TERM or
                LHS site anywhere else.
  PORT_MAP      connected to an instance port. Cross-boundary coupling; record it as
                instance.port.
  GEN_COND      a generate condition or a width expression. X shapes structure at
                elaboration."""

# The edge names are written BARE here, with the counterpart described in prose rather than
# shown as a parenthesised argument. A previous revision wrote them as SOURCES(Y),
# CAPTURES(Y) and so on; the model copied the notation into the JSON verbatim and 200 of
# 3 048 edges came back with a type of "SOURCES(Y)". The name in this list is the exact
# string the `type` field must contain, and nothing else.
_EDGES = """\
  SOURCES        the element appears on the right-hand side of an assignment to the target.
  CAPTURES       the element is assigned the target inside a clocked process, so it now
                 holds the target's value.
  DERIVES_FROM   the element is assigned some function of the target.
  GATES          the element appears in the condition governing an assignment to the
                 target, or as a term of the target's enable.
  SELECTS        the element is a case selector or an index choosing among the targets.
  CONSTRAINS     the element is compared, and the comparison's result governs the target.
  OVERRIDES      the element selects an alternative value for the target in place of the
                 one normally computed.
  SEQUENCES      the element is the clock or reset edge of the process assigning the target.
  CARRIES        the element is assigned the target alone and unmodified, so their values
                 are equal.
  REFLECTS       the element is derived from the target by a reduction or comparison, so it
                 reveals something about the target without carrying its value.
  EXPORTS        the element reaches the entity boundary. Empty target list.
  AGGREGATES     the element is composed from the listed targets.
  SLICES         the element is a bit range of the target. Give the range in `bits`.
  ISOLATED       no coupling can be substantiated anywhere in this entity. Empty target
                 list. An element whose fields are named individually is coupled through
                 them and is not isolated, even where its own bare name never appears."""


def _procedure(unit: str, extra: str = "") -> str:
    """The shared body. Written once so the two parsers cannot drift apart -- a drift
    would surface downstream as a port/signal asymmetry and be misread as a finding about
    the asset stage."""
    return f"""
HOW TO WORK

Do these in order. The order is the method, not a suggestion.

STEP 1 -- STATE WHAT THE ENTITY IS FOR. Before annotating anything, work out one sentence:
"This entity <verb> <what> for <consumer>." Derive it from the source, in this order of
authority: its output ports and what feeds them; the state it holds across clock edges;
the structure of its port bundles; what it instantiates. The entity name is corroboration,
never the source.

Every role you assign afterwards answers: what part of that sentence does this element
implement?

STEP 2 -- BUILD AN OCCURRENCE PROFILE. For each {unit} you are given, scan the WHOLE source
and list every place the identifier appears, tagging each with its site and its
counterparts.

>>> These SITE names are for your own working notes in this step. They are NOT values for
>>> any output field. The `relationship` field has its own separate vocabulary, given later
>>> under THE FIELDS, and only names from that list may appear in a `type`.

{_SITES}

STEP 2b -- SWEEP FOR GOVERNING SITES BEFORE MOVING ON. Having built the profile, go back
over it once and ask of every COND, CASE_SEL and ENABLE_TERM entry: which element's
assignment does this condition govern? Each answer is a coupling that must appear in
`relationship`.

Do this as a separate pass, deliberately. A condition governs an element without ever
appearing in that element's value, so nothing in the assignment you are reading points back
at it -- it is found by looking at the branch you are inside, not at the expression in front
of you. It is the coupling most often left out, and leaving it out is the single largest
loss this task can suffer, because it is the only record that one element determines whether
another one acts at all.

STEP 2c -- FOR ANY RECORD, STRUCT OR INTERFACE-TYPED ELEMENT, AND EACH OF ITS FIELDS,
settle one structural question before annotating it: what does THIS entity do with the
value?

  ORIGINATES  the entity constructs the value here. It is assigned from this entity's own
              logic, or converted into a different representation from something else.
  CONSUMES    the entity reads the value and acts on it -- decodes it, tests it in a
              condition, uses it to index or compare, maintains state from it.
  FORWARDS    the entity receives the value and passes it on unchanged, in the same form,
              usually by a whole-record assignment. Nothing here reads the field's value.

Say which, in `functionality`, in those words. The answer is a fact about the source and is
usually settled by one line: a whole-record assignment that copies the aggregate and never
mentions the field again is FORWARDS; a field named in a condition or an index is CONSUMES.
An element may forward most fields of a record and consume one or two -- answer per field,
not per record.

This is a description, not a judgement. Do not say whether forwarding matters, and do not
treat a forwarded field as uninteresting: report what the entity does with it and stop.

STEP 3 -- ANNOTATE FROM THE PROFILE. Only now write the four fields.

**Never annotate from the declaration alone.** A declaration gives type, width and
direction, and no function whatsoever. If the profile holds nothing but DECL, the element
is unused in this source, and saying so plainly is the correct annotation.

HOW TO READ AN ASSIGNMENT

- X on the right, Y on the left: X feeds Y. Clocked, X is captured into Y.
- X in the condition of the branch, Y assigned inside it: X governs Y. This is a real
  coupling and it does not appear in the values at all -- it is the most commonly missed
  relationship in this task.
- X the case selector, Y1..Yn assigned per branch: X chooses among them.
- X the index, A the array: X addresses A.

THE FIELDS

`function` -- the shortest true statement of what the element does, at most 12 words, no
final stop. It is a label, not a sentence: a reader scanning a list of two hundred elements
reads this and nothing else. Derive it from the profile like everything else.

`functionality` -- one or two sentences, at most 45 words, present tense, active voice.
Cover, in this order, as much as the profile supports:
  1. what it does mechanically -- the action visible in the source;
  2. what it acts on or comes from -- name the counterparts;
  3. its part in the entity's purpose -- one clause, and only when that is not already
     obvious from 1 and 2.
Name at least one counterpart unless the element is unused. Describe behaviour, not syntax:
write what the element causes to happen, never "appears in an if condition" -- where it
appears belongs in `evidence`.

`role` -- one to three short phrases naming the parts this element plays in what the entity
is for. This is the field the next stage reasons over, so it must be about the design, not
about the syntax and not about the element's type.

Where the profile supports an answer, make sure the role phrases between them convey:
  - whether it HOLDS a value across cycles, or CARRIES one through combinationally;
  - whether it GOVERNS whether some other element updates;
  - whether it CHOOSES among alternatives;
  - whether it CROSSES the entity boundary, and in which direction;
  - whether anything OUTSIDE this entity can change it, and by what path.

Each phrase must be supported by at least one occurrence site. Do not invent a role to
fill the field. Most elements in a typical design play ordinary parts -- an operand, a
pipeline stage, a handshake, an unremarkable counter -- and writing that plainly is a
correct and expected answer, not a failure to find something.

`relationship` -- one entry per coupling you can substantiate, each traceable to a specific
occurrence site.

The `type` must be EXACTLY one of the following names, copied character for character. Do
not add parentheses, arguments or any other decoration to the name, and do not use a site
name from STEP 2 here -- those are two different vocabularies and only this one is valid in
a `type`:

{_EDGES}

`targets` must name DECLARED elements, spelled exactly as they were given to you in the
lists above. If a coupling is to one element of an array, name the array itself -- write the
declared name, never an indexed or sliced expression, and put the range in `bits` instead.
If the counterpart is a port of an instance, write it as `instance.port`. If the counterpart
is not a declared element at all -- a constant, a generic, a literal -- leave it out of
`targets` and describe it in `evidence` instead.

Give `bits` whenever the coupling is through a bit range, a partial assignment or a
concatenation; omit it when the whole width is involved. Record DIRECT couplings only --
one construct away. If A feeds B and B feeds C, emit A->B and B->C, never A->C.
Emit every edge you can substantiate; there is no cap. Every governing site found in
STEP 2b must appear here as a GATES, SELECTS, CONSTRAINS or OVERRIDES edge.

`evidence` -- at most 40 words. Name the construct that substantiates the annotation and at
least one counterpart: an assignment, a branch or case condition, a port map, a generate
statement. Cite line numbers when you can. `functionality` says what the element does;
`evidence` says where in the source that can be seen.

WHAT YOU MUST NOT DO

- **Do not decide significance.** Do not state or imply that an element is important,
  sensitive, secret, protected, critical, trusted, exposed, vulnerable or at risk. Do not
  name a security objective. Do not use the words asset, threat, attacker or weakness. A
  later stage makes those judgements and needs your description to be neutral evidence.
  Two elements with the same behaviour get the same description regardless of what they
  are called.
- **Do not infer from the name.** Derive every annotation with the identifier treated as a
  meaningless token, then check whether the name agrees. If it agrees, the name has added
  nothing and does not belong in the evidence. If it disagrees, the source wins and the
  disagreement is worth stating -- an element named like a status output that is only ever
  used as a write condition is a control element with a misleading name.
- **Do not hedge.** No may, could, might, possibly, potentially, likely. Where you are
  unsure, describe less and describe it exactly. State a limit as a fact: "No driver for
  this element appears in this source."
- **Do not claim anything about elements outside the closed set.** If an element is driven
  by an instance whose source is not here, say that.
{extra}
Reproduce every name exactly as given, including record fields written with a dot.
Annotate every element you are given, add none, drop none. Return ONE JSON object and
nothing else -- no markdown, no code fences, no prose."""


PARSE_PORTS_V3_SYSTEM = """You annotate the I/O ports of one hardware entity.

You are given the entity's source with comments removed, and the AUTHORITATIVE list of its
ports (name, direction, type) already extracted from that source. The list is ground truth.
""" + _procedure(
    "port",
    """- **Do not treat a port's direction as its function.** An input that only ever appears
  in branch conditions is a control element; an output assigned from a register is
  reporting held state. Direction tells you which way the coupling points, not what the
  element is for.
""") + """

OUTPUT SCHEMA, exactly one entry per port given:
{"ports": [
  {"name": "<exactly as given>",
   "function": "<=12 words>",
   "functionality": "<1-2 sentences, <=45 words>",
   "role": ["<short phrase>", "..."],
   "relationship": [{"type": "<EDGE>", "targets": ["<name>", "..."], "bits": "<optional>"}],
   "evidence": "<the construct, <=40 words>"}
]}"""


PARSE_SIGNALS_V3_SYSTEM = """You annotate the internal signals and registers of one hardware
entity.

You are given the entity's source with comments removed, and the AUTHORITATIVE list of its
internal elements (name, type) already extracted from that source. The list is ground truth.
""" + _procedure(
    "signal or register",
    """- **Decide `kind` from where it is assigned, not from its declared type.** It is a
  register when it is assigned inside a clocked process and holds its value between edges;
  otherwise it is a signal. A declaration alone never settles this.
""") + """

OUTPUT SCHEMA, exactly one entry per element given:
{"signals": [
  {"name": "<exactly as given>",
   "kind": "register" | "signal",
   "function": "<=12 words>",
   "functionality": "<1-2 sentences, <=45 words>",
   "role": ["<short phrase>", "..."],
   "relationship": [{"type": "<EDGE>", "targets": ["<name>", "..."], "bits": "<optional>"}],
   "evidence": "<the construct, <=40 words>"}
]}"""


PARSE_ELEMENTS_V3_SYSTEM = """You annotate the design elements of one hardware entity — its
I/O ports and its internal signals and registers together.

You are given the entity's source with comments removed, and the AUTHORITATIVE lists of its
ports (name, direction, type) and its internal elements (name, type), already extracted from
that source. Both lists are ground truth.

Annotate BOTH lists in one answer. An element's occurrence profile routinely spans the two —
a port is captured into a register, a register drives a port — so having both in front of you
is an advantage, not a complication. Use it: when you annotate a port, you already know which
internal element consumes it, and the relationship edges on both sides should agree.
""" + _procedure(
    "port, signal or register",
    """- **Do not treat a port's direction as its function.** An input that only ever appears
  in branch conditions is a control element; an output assigned from a register is
  reporting held state. Direction tells you which way the coupling points, not what the
  element is for.
- **For internal elements, decide `kind` from where it is assigned, not from its declared
  type.** It is a register when it is assigned inside a clocked process and holds its value
  between edges; otherwise it is a signal. A declaration alone never settles this. Ports do
  not carry `kind`.
""") + """

OUTPUT SCHEMA — one entry per element given, in BOTH arrays. Return an empty array for a
list that was given empty:
{"ports": [
  {"name": "<exactly as given>",
   "function": "<=12 words>",
   "functionality": "<1-2 sentences, <=45 words>",
   "role": ["<short phrase>", "..."],
   "relationship": [{"type": "<EDGE>", "targets": ["<name>", "..."], "bits": "<optional>"}],
   "evidence": "<the construct, <=40 words>"}
 ],
 "signals": [
  {"name": "<exactly as given>",
   "kind": "register" | "signal",
   "function": "<=12 words>",
   "functionality": "<1-2 sentences, <=45 words>",
   "role": ["<short phrase>", "..."],
   "relationship": [{"type": "<EDGE>", "targets": ["<name>", "..."], "bits": "<optional>"}],
   "evidence": "<the construct, <=40 words>"}
 ]}"""


# The closed structural edge vocabulary, exported so the driver can validate against it
# rather than keeping a second copy that could drift.
EDGE_TYPES = ("SOURCES", "CAPTURES", "DERIVES_FROM", "GATES", "SELECTS", "CONSTRAINS",
              "OVERRIDES", "SEQUENCES", "CARRIES", "REFLECTS", "EXPORTS", "AGGREGATES",
              "SLICES", "ISOLATED")

OCCURRENCE_SITES = ("DECL", "COND", "CASE_SEL", "ENABLE_TERM", "LHS_SEQ", "LHS_COMB",
                    "RESET_BRANCH", "RHS", "INDEX", "INDEX_TARGET", "SLICE", "CONCAT",
                    "SENS", "PORT_MAP", "GEN_COND")

# Words that must not appear in an annotation. Enforced on OUTPUT by
# parse_v3.check_annotation -- the prompt asks, this list checks.
BANNED_IN_OUTPUT = (
    # verdict and significance
    "asset", "secret", "confidential", "integrity", "availability", "sensitive",
    "critical", "important", "protect", "trusted", "untrusted", "privileged",
    "vulnerable", "vulnerability", "exploit", "threat", "attacker", "adversary",
    "malicious", "secure", "insecure", "security", "cwe", "risk", "leak",
    # hedging
    "may ", "could ", "might ", "possibly", "potentially", "likely",
)


# ------------------------------------------------------------------- audit ---

def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def audit() -> None:
    """Checked at import. Everything this module claims about its own prompts."""
    from prompts_v2 import EVAL_SET_IDENTIFIERS, EXTERNAL_IDENTIFIERS
    for label, text in (("PORTS", PARSE_PORTS_V3_SYSTEM),
                        ("SIGNALS", PARSE_SIGNALS_V3_SYSTEM),
                        ("ELEMENTS", PARSE_ELEMENTS_V3_SYSTEM)):
        hits = [b for b in EVAL_SET_IDENTIFIERS + EXTERNAL_IDENTIFIERS if b in text]
        assert not hits, f"{label}: evaluation-set identifier(s) present: {hits}"

        # The stage must never be told to READ comments, because the input has none.
        # "comments removed" is a statement about the input and must stay; what must not
        # appear is any phrase that makes a comment a source of inference. Checked as
        # phrases rather than as the bare word, which the input declaration needs.
        low = text.lower()
        assert "comments removed" in low, f"{label}: the stripped input is not declared"
        for gone in ("in-source comment", "comments, and usage", "and comments",
                     "comment text", "read the comment", "header comment",
                     "comments corroborate"):
            assert gone not in low, f"{label}: {gone!r} makes a comment a source"

        # the three structural guards, each of which the design depends on
        assert "OCCURRENCE PROFILE" in text, f"{label}: the profile step is missing"
        assert "Never annotate from the declaration alone" in text, f"{label}: no DECL guard"
        assert "meaningless token" in text, f"{label}: the name-opacity rule is missing"

        # the prohibition must be present -- this is the one place the banned words are
        # allowed to appear, because forbidding them requires naming them
        for req in ("Do not decide significance", "Do not infer from the name",
                    "Do not hedge", "name a security objective"):
            assert req in text, f"{label}: prohibition {req!r} is missing"

        # every emitted field must be specified in the body, or the model invents a format
        for f in ("`function`", "`functionality`", "`role`", "`relationship`", "`evidence`"):
            assert f + " --" in text, f"{label}: field {f} has no spec"

        # the five mechanism hooks the asset stage reasons over
        for hook in ("HOLDS", "GOVERNS", "CHOOSES", "CROSSES", "OUTSIDE"):
            assert hook in text, f"{label}: role coverage hook {hook!r} is missing"

        # ordinary must be an available and respectable answer, or the field inflates
        assert "correct and expected answer" in text, f"{label}: no ordinary-role permission"

        # no numeric emission hint may reach the annotator -- v1 measured that a number in
        # a prompt becomes a hard quota however it is hedged
        for banned in ("%", "at most 20", "no more than 20", "at least half"):
            assert banned not in text, f"{label}: numeric emission hint {banned!r} present"

        # every edge type and site named in the schema must be defined in the body
        for e in EDGE_TYPES:
            assert e in text, f"{label}: edge type {e!r} not defined in the prompt"
        for s in OCCURRENCE_SITES:
            assert s in text, f"{label}: occurrence site {s!r} not defined in the prompt"

        # THE TWO VOCABULARIES MUST NOT BE CONFUSABLE. Measured on the first real run: 200
        # of 3 048 edges carried a type of "SOURCES(Y)" because the edge list showed the
        # counterpart as a parenthesised argument, and 33 more carried a SITE name. Both are
        # prompt defects, so both are asserted against here.
        for e in EDGE_TYPES:
            assert f"{e}(" not in text,                 f"{label}: edge {e!r} shown with a parenthesised argument -- the model copies it"
        # Fragments chosen to sit within one wrapped line -- a phrase that straddles a line
        # break is not a contiguous substring of the composed prompt and would assert
        # against text that is actually present.
        for req in ("They are NOT values for", "copied character for character",
                    "two different vocabularies"):
            assert req in text, f"{label}: vocabulary separation missing {req!r}"

        # the governing-site sweep, added after GATES came back at 54% of the elements that
        # actually appear in a condition
        assert "STEP 2b" in text, f"{label}: the governing-site sweep is missing"
        assert "must appear here as a GATES" in text, f"{label}: STEP 2b has no output link"

        # target normalisation -- 496 of 589 unresolved targets were indexed array refs
        assert "never an indexed or sliced expression" in text,             f"{label}: targets are not constrained to declared names"

        # STEP 2c -- the structural observation that separates a forwarded record field
        # from one the entity acts on. Reported as a FACT; the prompt must not say what
        # forwarding is worth, or the parser has made the asset stage's decision.
        assert "STEP 2c" in text, f"{label}: the originates/consumes/forwards question is missing"
        for w in ("ORIGINATES", "CONSUMES", "FORWARDS"):
            assert w in text, f"{label}: STEP 2c lacks {w!r}"
        assert "This is a description, not a judgement" in text,             f"{label}: STEP 2c does not disclaim judgement"
        for leak in ("not an asset", "is an asset", "uninteresting to", "can be ignored",
                     "safe to skip", "less important"):
            assert leak not in text, f"{label}: STEP 2c leaks a verdict: {leak!r}"


    # all three prompts must share the procedure verbatim -- they are built from the same
    # _procedure() call, and a drift between them would surface downstream as a port/signal
    # asymmetry and be misread as a finding about the asset stage
    shared = _procedure("port")
    assert shared.split("HOW TO READ")[0] in PARSE_PORTS_V3_SYSTEM
    for t2 in (PARSE_SIGNALS_V3_SYSTEM, PARSE_ELEMENTS_V3_SYSTEM):
        assert "STEP 1 -- STATE WHAT THE ENTITY IS FOR" in t2

    # The merged prompt answers for BOTH lists in one call. If either array were missing
    # from its schema, half the closed set would come back unannotated and the coverage
    # counter would report it as a model failure rather than as a prompt defect.
    for req in ('"ports": [', '"signals": [', "Annotate BOTH lists in one answer",
                '"kind": "register" | "signal"'):
        assert req in PARSE_ELEMENTS_V3_SYSTEM, f"merged prompt lacks {req!r}"
    assert "Ports do\n  not carry `kind`" in PARSE_ELEMENTS_V3_SYSTEM, \
        "merged prompt must say kind is signals-only, or ports come back with a kind field"


def audit_against_corpus(gt_path="ground_truth/manual_gt_neorv32.json",
                         parsed_dir="parsed_tuning18") -> None:
    """The full standing-rule check: no identifier from the reference set or the closed set
    may appear in either prompt. Separate from `audit()` because it reads data files;
    `parse_v3` calls it before spending anything."""
    import glob
    import json
    import os
    import re

    names = set()
    if os.path.exists(gt_path):
        for d in json.load(open(gt_path, encoding="utf-8"))["modules"].values():
            for a in d["assets"]:
                names.add(a["element"].strip())
                names.update(a["element"].strip().split("."))
    for f in glob.glob(os.path.join(parsed_dir, "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        for e in d.get("ports", []) + d.get("signals", []):
            names.add(e["name"])
            names.update(e["name"].split("."))

    # A leak is a corpus name used AS AN IDENTIFIER, which is not the same as a corpus
    # name that happens to be an English word. Blacklisting the overlap ("empty", "over",
    # "state", "done") would be an ever-growing hand-kept list -- exactly the kind of
    # proxy that misses the real thing. Two precise rules instead:
    #
    #   1. Any corpus name containing '_' is unambiguously an identifier wherever it
    #      appears. Flag it in the whole prompt.
    #   2. Any other corpus name is flagged only inside a code span, because that is the
    #      only place these prompts put an identifier. They quote none, so a hit there is
    #      a genuine leak rather than a word collision.
    for label, text in (("PORTS", PARSE_PORTS_V3_SYSTEM),
                        ("SIGNALS", PARSE_SIGNALS_V3_SYSTEM),
                        ("ELEMENTS", PARSE_ELEMENTS_V3_SYSTEM)):
        code = " ".join(re.findall(r"`[^`\n]+`", text))
        hits = sorted(
            n for n in names if len(n) > 3 and (
                ("_" in n and re.search(rf"(?<![\w.]){re.escape(n)}(?![\w])", text))
                or ("_" not in n and re.search(rf"(?<![\w.]){re.escape(n)}(?![\w])", code))))
        assert not hits, f"{label}: corpus identifier(s) present: {hits}"


audit()


if __name__ == "__main__":
    for n, t in (("PARSE_PORTS_V3_SYSTEM", PARSE_PORTS_V3_SYSTEM),
                 ("PARSE_SIGNALS_V3_SYSTEM", PARSE_SIGNALS_V3_SYSTEM)):
        print(f"{n:26} {len(t):6d} chars  sha {sha(t)}")
    audit_against_corpus()
    print("corpus identifier audit: CLEAN")
