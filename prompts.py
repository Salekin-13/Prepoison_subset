# ===================== Summary generation  =====================

SUMMARY_SYSTEM = """Your task: given the name of one IP module of the NEORV32 RISC-V SoC \
and excerpts retrieved from the official NEORV32 datasheet, produce a TECHNICAL SUMMARY \
of that module. The summary is the sole specification input consumed by a downstream \
Asset Generation agent that decides which security-critical assets, if any, exist in \
that module. The agent separately receives the module's RTL, so do not enumerate ports \
or signal-level details — with one exception: capture the security SEMANTICS of any \
signal that carries privilege, protection, isolation, reset/halt, or debug-access meaning \
(describe the meaning, not the pin). Prioritize what only the specification provides: \
system context, cross-module interaction, privilege and configuration semantics. Some \
modules may contain no security assets; your summary must make that determinable rather \
than implying relevance. A module can also be security-critical BY FUNCTION — it handles \
keys, entropy, passwords, boot/firmware images, or executable memory — even if it enforces \
no access control of its own.
Output EXACTLY this structure, replacing angle-bracket placeholders:
MODULE: <module name>
1. FUNCTION AND ROLE
<What the module does and its role in the SoC. Prose, 2-5 sentences.>
2. REGISTERS, CSRS, AND FLAGS
<One line per item the excerpts describe for this module:>
- <EXACT_NAME> — <access: r/w, r/-, privilege level if stated> — <reset value if stated> — <function>
3. CONFIGURATION
<One line per generic/parameter/enable the excerpts describe:>
- <EXACT_NAME> — <build-time or run-time> — <functional effect>
4. CROSS-MODULE INTERACTION
<How this module connects to and interacts with other NEORV32 modules and the processor \
core: bus access, interrupts, privilege transitions, shared state — at both the modular \
and the processor level. Include the extent of access or control the module grants to any \
external agent or downstream module (what an interface, test/debug port, or bus master can \
reach, read, write, halt, or reset through it) and any gating or authentication on that \
access, including whether the spec calls that gating optional, default, or weak. Prose.>
5. SECURITY-RELEVANT BEHAVIOR
<Report in prose whichever of the following the excerpts describe for this module: access \
control and which privilege levels may read/write/execute what; privilege propagation, \
override, or transitions (effective-privilege changes, privilege/security signaling to the \
bus fabric); protection, isolation, or lock mechanisms AND their documented bypasses, \
exemptions, or conditions; handling of secret or security-critical material (keys, \
entropy/random sources, passwords, boot/firmware images) and anything affecting its quality, \
determinism, or exposure; mutability of state normally expected to be fixed (writable \
instruction/code memory, lockable configuration); timing or side-channel guarantees such as \
data-independent execution time; fault and exception behavior on illegal or unauthorized \
access; and any protection the spec explicitly notes to be absent, optional, weak, default, \
or example-only. Report only what the excerpts state; describe behavior, not exploitability.>
Rules:
- Use ONLY the provided excerpts. Do not add register names, bit fields, or behavior \
from outside knowledge, even if you believe you know the NEORV32 design.
- The excerpts may describe multiple modules. The named module is your subject, but do NOT \
discard content about other modules when it changes the subject's security posture — \
specifically when: (a) another module can bypass, override, or is exempt from a protection \
this module enforces; (b) another module can access, reset, halt, or control this module or \
its state; or (c) this module can bypass or override a protection enforced elsewhere. Report \
such relationships in section 4 or 5, naming the other module. Otherwise ignore content about \
other modules.
- Reproduce all names (registers, CSRs, flags, generics) VERBATIM with exact casing \
as they appear in the excerpts. Never paraphrase a name.
- In section 2, always include register fields that control privilege mode, lock/lockout, \
secret or credential values, or the enable/disable of a protection, even when embedded within \
a larger register.
- When you state that this module enforces a protection, isolation, or permission check, also \
state its documented scope limits, exemptions, bypass paths, and which privilege levels or \
agents are exempt. Never write that a check applies to "all" accesses unless the excerpts \
state it holds without exception.
- If the excerpts do not cover a section, write exactly: Not documented for this \
module. Do not guess.
- Do NOT inflate security relevance; report only what the excerpts state and never speculate \
about exploits. Use the exact sentence "No access-control, protection, or privileged \
mechanisms are documented for this module." in section 5 ONLY when none of the section-5 \
categories apply. A module that is security-critical by function (keys, entropy, passwords, \
boot images, executable memory) must be described rather than negated. A faithful negative, \
when genuinely warranted, is a correct and useful output.
- For an unknown field within a list line (e.g. an unstated reset value), write \
"not stated" for that field only. Never use a section-level sentence inside a line.
- The summary must read as a standalone specification digest. Never mention excerpts, \
excerpt numbers, retrieval, context, or these instructions in the output.
- Be dense and factual. No preamble, no conclusions, no recommendations. Target \
under ~450 words unless the module's register set or documented security behavior \
genuinely requires more.
- In section 3, list only named parameters/generics that appear in the source text. \
If configuration is described in prose without a named parameter, summarize it in \
prose after the list. Never invent a label.
- Sections 1, 4, and 5 are prose only — no bullet points.
"""

SUMMARY_SYSTEM_v2 = """Your task: given the name of one IP module of the NEORV32 RISC-V SoC \
and excerpts retrieved from the official NEORV32 datasheet, produce a TECHNICAL SUMMARY \
of that module. The summary is the sole specification input consumed by a downstream \
Asset Generation agent that decides which security-critical assets, if any, exist in \
that module. The agent separately receives the module's RTL, so do not enumerate ports \
or signal-level details; prioritize what only the specification provides: system context, \
cross-module interaction, privilege and configuration semantics. Some modules may contain no \
security assets; your summary must make that determinable rather than implying relevance.

Output EXACTLY this structure, replacing angle-bracket placeholders:

MODULE: <module name>

1. FUNCTION AND ROLE
<What the module does and its role in the SoC. Prose, 2-5 sentences.>

2. REGISTERS, CSRS, AND FLAGS
<One line per item the excerpts describe for this module:>
- <EXACT_NAME> — <access: r/w, r/-, privilege level if stated> — <reset value if stated> — <function>

3. CONFIGURATION
<One line per generic/parameter/enable the excerpts describe:>
- <EXACT_NAME> — <build-time or run-time> — <functional effect>

4. CROSS-MODULE INTERACTION
<How this module connects to and interacts with other NEORV32 modules and the processor \
core: bus access, interrupts, privilege transitions, shared state — at both the modular \
and the processor level. Prose.>

5. SECURITY-RELEVANT BEHAVIOR
<Access control, privilege enforcement, protection mechanisms, and error/exception \
behavior the excerpts describe for this module. Prose.>

Rules:
- Use ONLY the provided excerpts. Do not add register names, bit fields, or behavior \
from outside knowledge, even if you believe you know the NEORV32 design.
- The excerpts may describe multiple modules; extract only what concerns the target \
module named in the request. Ignore the rest.
- Reproduce all names (registers, CSRs, flags, generics) VERBATIM with exact casing \
as they appear in the excerpts. Never paraphrase a name.
- If the excerpts do not cover a section, write exactly: Not documented for this \
module. Do not guess.
- Do NOT inflate security relevance. If no access control, protection, or privileged \
state is described for this module, write in section 5 exactly: No access-control, \
protection, or privileged mechanisms are documented for this module. A faithful \
negative statement is a correct and useful output.
- For an unknown field within a list line (e.g. an unstated reset value), write \
"not stated" for that field only. Never use the section-level sentence inside a line.
- The summary must read as a standalone specification digest. Never mention excerpts, \
excerpt numbers, retrieval, context, or these instructions in the output.
- Be dense and factual. No preamble, no conclusions, no recommendations. Target \
under ~450 words unless the module's register set genuinely requires more.
- In section 3, list only named parameters/generics that appear in the source text. \
If configuration is described in prose without a named parameter, summarize it in \
prose after the list. Never invent a label.
- Sections 1, 4, and 5 are prose only — no bullet points.
"""

# ===================== RTL annotation  =====================

PARSE_PORTS_ANNOTATE_SYSTEM = """Your task is to annotate the FUNCTION of hardware I/O ports. You are \
given a module's VHDL source and the AUTHORITATIVE list of its entity ports (name, direction, \
type), already extracted from the RTL. That list is ground truth: annotate every port, add \
none, drop none, reproduce names verbatim.
For each port infer a concise function (<= 12 words) from its name, in-source comments, and \
usage. If a port's purpose is not determinable, use "unclear from RTL".
Output a JSON object of exactly this shape, one entry per provided port:
{"ports": [{"name": "<verbatim>", "function": "<concise>"}]}
JSON only. No prose."""

PARSE_SIGNALS_ANNOTATE_SYSTEM = """Your task is to annotate internal design elements. You are given a \
module's VHDL source and the AUTHORITATIVE list of its internal signals (name, type), already \
extracted from the RTL. That list is ground truth: annotate every element, add none, drop \
none, reproduce names verbatim.
For each element infer, from the source: kind ("register" if it holds state across clock \
edges / is assigned in a clocked process, otherwise "signal") and a concise function \
(<= 12 words). If not determinable, use kind "signal" and function "unclear from RTL".
Output a JSON object of exactly this shape, one entry per provided element:
{"signals": [{"name": "<verbatim>", "kind": "register|signal", "function": "<concise>"}]}
JSON only. No prose."""


# ===================== Asset generation  =====================

V0 = """Your task: identify the PRIMARY SECURITY ASSETS in ONE hardware IP \
module for pre-silicon security verification, following the IEEE P3164 Conceptual-and-Structural \
Analysis (CSA).

INPUTS (in the user message):
(1) TECHNICAL SUMMARY -- SoC-context spec summary (may say "not specified in retrieved spec"; \
never fill such gaps from general knowledge).
(2) PARSED I/O PORTS and (3) PARSED INTERNAL SIGNALS -- each is a JSON object with fields \
including entity, name, direction(dir), type, function (signals also have kind). TOGETHER they are the CLOSED \
SET of design elements. Every asset MUST bind to exactly one element from this set by its exact \
"name". Ports AND internal signals/registers are equally eligible. Never invent, rename, split, \
or merge a name; copy record-field names verbatim including the dot (e.g. "ctrl.buf_req", \
"host_req_i.stb").
(4) RTL -- ground truth for what each element does.

DEFINITIONS:
- A security asset is a design element (or the data it holds/derives) whose Confidentiality, \
Integrity, or Availability (CIA) must be protected because its compromise weakens the security \
of the module or the wider SoC.
- Conceptual asset: high-level data or system state tied to a use-case flow that carries a CIA \
objective.
- PRIMARY (structural) asset: a concrete closed-set element that STORES, CARRIES, GENERATES, or \
GATES a conceptual asset. (Secondary/influencing signals are produced by a later stage -- do NOT \
emit them here.)

METHOD:
STEP 1 -- CONCEPTUAL ASSETS (reason internally; do NOT output this step). Apply the rubric to \
the module's use cases:
 (C) Confidentiality: is there information -- input or internally generated -- an integrator may \
deem secret, or that could leak/expose confidential material? Genuine secrets are keys, seeds, \
entropy/random state, or private plaintext. A plain data/address/control bus with no secret is \
NOT confidential -- evaluate it under (I)/(A) instead.
 (I) Integrity: are there state or configuration settings that must stay immutable during \
certain operations/modes, whose modification would harm the integrator?
 (A) Availability: is there any element that, if made unavailable or manipulated, would prohibit \
correct operation of the IP or IC (denial of service at integration)?
 (U) Undermine: are there privileged modes, overrides, bypass, or injection paths that could \
make the IP produce incorrect output under normal-looking operation?
An element is an asset iff at least one of C/I/A/U is "yes" with a reason grounded in the summary \
or RTL. An element answering "no" to all four is NOT an asset; make such non-asset decisions \
explicitly (internally).

STEP 2 -- STRUCTURAL (PRIMARY) ASSETS. Map each conceptual asset to the concrete closed-set \
element(s) that store, carry, generate, or gate it. A conceptual asset may fan out to SEVERAL \
elements -- emit one object per element. If NO closed-set element supports a conceptual asset, \
OMIT it -- never fabricate an element.

RULES:
- "Asset RTL" MUST be the exact "name" of one element from the provided ports/signals. If an \
idea cannot bind to a real element, drop it.
- "Entity" MUST be copied verbatim from that element's "entity" field.
- "Security Objective" is MANDATORY: exactly ONE of "Confidentiality", "Integrity", \
"Availability" -- the dominant objective. Fold (U) findings into Integrity or Availability. Note \
any non-dominant objective inside the Justification.
- Global clock/reset ports (e.g. clk_i, rstn_i) and pure boilerplate are NOT assets unless \
clock/reset control is the module's actual function.
- Ground "Functionality" (what the element does/carries) and "Justification" (why its compromise \
violates the chosen objective) in the summary or RTL only; do not add outside knowledge or \
assess exploitability. Every asset carries explicit reasoning.

OUTPUT CONTRACT (strict): return ONE JSON object and nothing else -- no markdown, no code fences, \
no prose:
{"IP": "<module name>",
 "Assets": [
   {"Asset Name": "<short descriptive title>",
    "Asset RTL": "<element name from the closed set>",
    "Entity": "<the element's entity, verbatim>",
    "Functionality": "<what it does/carries>",
    "Security Objective": "Confidentiality" | "Integrity" | "Availability",
    "Justification": "<why its compromise violates the objective>"}
 ]}
If the module has no assets, return {"IP": "<module name>", "Assets": []}."""

ASSET_PRIMARY_CORE = V0


# ===================== Asset generation -- core variant V2 (arm A-02) =====================
# V2 is V0 plus ONE insertion, and nothing else. It is built by substitution rather than by
# copy-paste so that "identical except for the insertion" is guaranteed by construction; the
# assert below fails loudly if the anchor ever stops matching.
#
# WHY. A-01 (v01) raised port recall +0.181 [+0.048, +0.302] and dropped signal recall
# -0.157 [-0.229, -0.086], the latter unanimously -- not one module improved. Its examples
# bind 18 of 18 assets to entity ports, and that demonstration overrode the core prompt,
# which ALREADY said "Ports AND internal signals/registers are equally eligible" and "may
# fan out to SEVERAL elements". Both statements are correct and both were ignored, so a
# third restatement of eligibility would not help. The insertion is therefore PROCEDURAL --
# a question the model must answer per conceptual asset -- and it names the examples as the
# source of the skew so the instruction can reach past them.
#
# The failure is location, not concept: v01 missed div.start / mul.start / fifo.re (operation
# enables) while its examples label per_en and p1_dout_en (also enables, but ports); it missed
# ctrl.rs1_is_signed (a select) while labelling p1_sel; and it missed cache_o.cmd_dir -- an
# internal DIRECTION signal -- although the GPIO example's whole thesis is that direction
# control is an asset. Same roles, different location.
#
# The role list is tied to roles the examples already demonstrate rather than being a free
# checklist of "signal types to look for": an earlier free-standing checklist became a
# generator (cpu emitted ctrl.* eleven times). No count, proportion or threshold appears --
# a numeric hint becomes a hard quota however it is hedged.

_STEP2_ANCHOR = ("If NO closed-set element supports a conceptual asset, "
                 "OMIT it -- never fabricate an element.")

_ROLE_NOT_LOCATION = """

STEP 2 (continued) -- ROLE, NOT LOCATION. P3164 3.1.2 asks for the RTL that PRODUCES a \
conceptual asset, that STORES it, and that TRANSPORTS it. Those are usually different \
elements, so one conceptual asset normally maps to several: emit one object per element.

The worked examples below bind most of their assets to entity ports, because in a small \
standalone IP the interface is where these roles live. In a larger module the SAME roles are \
internal. An operation enable or start, a direction or mode select, a computed result, a \
busy/ready/error condition -- each is a port in one design and a signal or register in \
another. Judge the role, not where the element is declared.

For each conceptual asset ask BOTH:
 - which port carries it across the boundary?
 - which internal signal or register produces, holds, or gates it inside the module?
Emit an object for each that exists. When a module computes a condition internally and never \
brings it to a port, that internal element is the only structural asset for it -- omit it and \
the asset is lost.

P3164's own conceptual assets are mostly registers rather than ports: Config Regs, Status \
Regs and Key Reg for the AES engine (3.2.3); Memory Array, Data-In Register, Output Register \
and Address Register for the SRAM controller (3.2.4), whose structural assets are the \
internal signals ZBT_addr and ZBT_addr2."""

ASSET_PRIMARY_CORE_V2 = V0.replace(_STEP2_ANCHOR, _STEP2_ANCHOR + _ROLE_NOT_LOCATION)
assert ASSET_PRIMARY_CORE_V2 != V0, "STEP 2 anchor no longer matches -- V2 would equal V0"
assert V0.replace(_STEP2_ANCHOR, "") == ASSET_PRIMARY_CORE_V2.replace(
    _STEP2_ANCHOR + _ROLE_NOT_LOCATION, ""), "V2 differs from V0 outside the insertion"


# ============ Asset generation -- port-record granularity (arm A-03) ============
# ONE proposition -- "a record-typed PORT is named whole" -- applied wherever the prompt
# speaks about naming. Applied as a function so the two arms below get provably identical
# text: A-03 on top of V2 (the arm) and on top of V0 (the confirmation).
#
# WHY TWO EDITS AND NOT ONE. The rule alone would argue against a demonstration sitting
# thirty lines above it. The INPUTS section illustrates "copy record-field names verbatim"
# with "host_req_i.stb", and host_req_i is a PORT record (neorv32_bus, neorv32_cache) -- so
# the prompt's own worked example of correct naming is the exact class that is 0/31 in the
# manual ground truth, 0/47 in the paper's list, and 73 false positives in v01c2. A-01
# established that a demonstration beats a correct sentence in this pipeline (18 port-bound
# examples overrode two accurate lines of eligibility text), so leaving it in place would
# make a null result uninterpretable: "the rule does nothing" and "the rule lost to the
# example" would look identical. Removing it costs nothing -- the sentence's actual job is
# to stop the model mangling dotted names, and rtx_engine.sreg (neorv32_spi) does that job
# without demonstrating the defect.
#
# WHAT THIS BUYS, MEASURED NOT GUESSED. Applying the rule perfectly to the real v01c2
# outputs -- rewrite each port-field emission to its record, then dedup -- gives
# emit 304->258, TP 87.0 UNCHANGED, FP 217->170.7, P 0.286->0.338, F1 0.419->0.472. The arm
# is precision-only by construction, so its guard is on recall. And the gain is DEDUP, not
# correction: the 73 port-field emissions collapse to 34 distinct records, of which exactly
# one (cpu_pmp.ctrl_i) is in gt. The other 33 are inherited bus plumbing -- bus_req_i alone
# is 82 of the 218 FPs across three repeats. This rule renames a wrong answer into a shorter
# wrong answer; it does not stop the model reaching for the SoC bus.
#
# THE SECOND SENTENCE IS A FENCE, NOT A FIX. An earlier draft had a symmetric clause telling
# the model to name the FIELD of an internal record. That was dropped: across 3 repeats x 15
# modules of both v01 and v01c2 the model emitted a bare whole internal record ZERO times, so
# the clause would fix nothing while pushing more emissions into signal-field, already 83 FPs
# against the paper's 19. What survives is only the guard -- without it the port rule can
# bleed across to internal records, and signal-field is 31 references at 0.817 recall.

_A03_EXAMPLE_OLD = '(e.g. "ctrl.buf_req", "host_req_i.stb").'
_A03_EXAMPLE_NEW = '(e.g. "ctrl.buf_req", "rtx_engine.sreg").'

_A03_RULE_ANCHOR = ('- "Asset RTL" MUST be the exact "name" of one element from the provided '
                    'ports/signals. If an idea cannot bind to a real element, drop it.')

_A03_RULE = """
- Record-typed PORTS are named WHOLE. A record port is the module's external interface; \
when it carries an asset, the asset is the port itself ("ctrl_i"), never one of its fields \
("ctrl_i.csr_wdata"). Record-typed INTERNAL signals are the opposite and are unchanged by \
this rule -- there the field is the asset ("ctrl.buf_req"), as above."""


def _apply_a03(core: str, label: str) -> str:
    """Both A-03 edits, or a loud failure. Never a silent no-op."""
    for anchor in (_A03_EXAMPLE_OLD, _A03_RULE_ANCHOR):
        n = core.count(anchor)
        assert n == 1, f"A-03/{label}: anchor matches {n} times, expected exactly 1: {anchor[:60]!r}"
    out = core.replace(_A03_EXAMPLE_OLD, _A03_EXAMPLE_NEW)
    out = out.replace(_A03_RULE_ANCHOR, _A03_RULE_ANCHOR + _A03_RULE)
    # Round-trip: undoing both edits must reproduce the input byte for byte. This is what
    # makes "identical outside the two edits" a guarantee rather than an intention.
    back = out.replace(_A03_RULE_ANCHOR + _A03_RULE, _A03_RULE_ANCHOR)
    back = back.replace(_A03_EXAMPLE_NEW, _A03_EXAMPLE_OLD)
    assert back == core, f"A-03/{label}: changed something outside the two edits"
    assert out != core, f"A-03/{label}: no-op"
    return out


# The arm: A-03 on top of V2. Baseline v01c2. 3 repeats.
ASSET_PRIMARY_CORE_V3 = _apply_a03(ASSET_PRIMARY_CORE_V2, "V3")

# The confirmation: the SAME two edits on top of V0. Baseline v01. 2 repeats, directional
# only -- at n=2 there is no usable sd (A-00 put the recall noise floor at sd 0.019), so this
# arm answers "does the rule do anything at all on the V0 core?" and must never be quoted
# with an interval. It exists to disambiguate a null on V3 between "the rule does nothing"
# and "V2's ask-BOTH wording masks it", and is run now rather than conditionally so both
# arms face the same model snapshot.
ASSET_PRIMARY_CORE_V0R = _apply_a03(V0, "V0R")

# The A-03 text is the same constant in both arms by construction; what needs checking is
# that each arm carries it exactly once and that stripping it leaves only the example swap.
for _label, _new, _base in (("V3", ASSET_PRIMARY_CORE_V3, ASSET_PRIMARY_CORE_V2),
                            ("V0R", ASSET_PRIMARY_CORE_V0R, V0)):
    assert _new.count(_A03_RULE) == 1, f"A-03/{_label}: rule text not present exactly once"
    assert _new.replace(_A03_RULE, "") == _base.replace(
        _A03_EXAMPLE_OLD, _A03_EXAMPLE_NEW), f"A-03/{_label}: differs beyond rule + example swap"
    assert _A03_EXAMPLE_OLD not in _new, f"A-03/{_label}: port-field example still present"
del _label, _new, _base


# ============ Asset generation -- expose STEP 1 (diagnostic arm T-1) ============
# NOT A RECALL ARM. This exists to split every miss into
#   (a) the conceptual asset was never conceived   -> STEP 1 / rubric failure
#   (b) conceived but never bound to its element   -> STEP 2 / binding failure
# and there is currently zero data on that split, which is what every later prompt edit
# would be aiming at blind.
#
# WHY IT CANNOT ALSO BE A CLEAN RECALL READING. It changes the OUTPUT CONTRACT, and asking
# for reasoning that was previously internal is itself known to change behaviour. So a
# recall delta here is confounded by construction and must be reported as diagnostic
# context, never as an ablation result. A clean recall arm on the same idea would need a
# separate design.
#
# Everything outside STEP 1's visibility and the contract slot it needs is byte-identical
# to V3, enforced by the round-trip assert below.
#
# WHY THE `Concept` ID. Without an explicit id per asset the concept->element mapping has
# to be inferred from prose, which makes the (a)/(b) classification a second judgement call
# on top of the first. The id makes the model state the mapping itself.

_T1_STEP1_OLD = "STEP 1 -- CONCEPTUAL ASSETS (reason internally; do NOT output this step)."
_T1_STEP1_NEW = "STEP 1 -- CONCEPTUAL ASSETS (output these; see the contract)."

_T1_CLOSE_OLD = "make such non-asset decisions explicitly (internally)."
_T1_CLOSE_NEW = ("make such non-asset decisions explicitly (internally). "
                 "Report every conceptual asset you identify in \"ConceptualAssets\", each "
                 "with a short id. This is a record of STEP 1, NOT a substitute for STEP 2 "
                 "-- a conceptual asset with no closed-set element still belongs here, and "
                 "every structural asset must still appear in \"Assets\".")

_T1_CONTRACT_OLD = '{"IP": "<module name>",\n "Assets": ['
_T1_CONTRACT_NEW = '''{"IP": "<module name>",
 "ConceptualAssets": [
   {"id": "<short id, e.g. C1>",
    "Concept": "<the data or system state, e.g. 'watchdog timeout configuration'>",
    "Security Objective": "Confidentiality" | "Integrity" | "Availability",
    "Why": "<which of C/I/A/U triggered, grounded in the summary or RTL>"}
 ],
 "Assets": ['''

_T1_ASSET_OLD = '   {"Asset Name": "<short descriptive title>",'
_T1_ASSET_NEW = ('   {"Asset Name": "<short descriptive title>",\n'
                 '    "Concept": "<id of the ConceptualAssets entry this element realises>",')

_T1_EDITS = ((_T1_STEP1_OLD, _T1_STEP1_NEW), (_T1_CLOSE_OLD, _T1_CLOSE_NEW),
             (_T1_CONTRACT_OLD, _T1_CONTRACT_NEW), (_T1_ASSET_OLD, _T1_ASSET_NEW))


def _apply_t1(core: str, label: str = "V4") -> str:
    """Expose STEP 1 and give it a contract slot. Round-trips, or fails loudly."""
    out = core
    for old, new in _T1_EDITS:
        assert core.count(old) == 1, f"T-1/{label}: anchor matches {core.count(old)}x: {old[:50]!r}"
        out = out.replace(old, new)
    back = out
    for old, new in reversed(_T1_EDITS):
        back = back.replace(new, old)
    assert back == core, f"T-1/{label}: changed something outside the four edits"
    return out


ASSET_PRIMARY_CORE_V4 = _apply_t1(ASSET_PRIMARY_CORE_V3)
assert ASSET_PRIMARY_CORE_V4 != ASSET_PRIMARY_CORE_V3, "T-1: no-op"


# ============ Asset generation -- per-concept closure sweep (arm A-08) ============
# WHAT T-1 FOUND. 82.1% of misses are BINDING failures: a concept covering the missed
# element was already in the model's own list, and the element was in the closed set. The
# model conceived the idea and did not write the element down. Only 14.3% + 3.6% are
# conception failures.
#
# AND THE SHAPE OF THAT FAILURE IS SPECIFIC. It is not fan-out. Where a covering concept
# existed it had typically already bound 5-6 elements (22% had 5, 19% had 6, up to 12); only
# 2.8% had bound just one. The model fans out -- 3.63 elements per concept -- and then stops
# one element short. So this is a COMPLETENESS problem: not "find more concepts", not "map
# to several elements", but "finish the concept you are already working on".
#
# WHY THIS IS NOT A FOURTH RESTATEMENT. The prompt already says "may fan out to SEVERAL
# elements -- emit one object per element", says it again in the V2 insertion, and adds the
# two-question procedure. The model COMPLIES with all of it. A-01 and A-02 both established
# that repeating an instruction the model already follows buys nothing. So the insertion is
# a VERIFICATION PASS over a list the model has already produced -- a different action from
# the search that produced it, with an explicit stopping criterion, which is the thing the
# current text never states.
#
# NO COUNT, NO PROPORTION, NO THRESHOLD -- the standing constraint from A-03's rule text. An
# earlier "~20% of the closed set" hint became a hard quota and cost 7 of 17 recall losses on
# cpu_cp_cfu, whose ground-truth density is 38%.
#
# REGISTERED RISK: "add any that does" can read as "add more", and this arm's whole mechanism
# is more emissions. Precision is already 0.285. See the Expect block in ABLATION_LOG.

_A08_ANCHOR = "\n\nRULES:\n"

_A08_SWEEP = """

STEP 2 (continued) -- CLOSE EACH CONCEPT. Before leaving a conceptual asset, make one more \
pass over the closed set for that asset alone, and ask of each element: does this element \
also produce, store, transport or gate this same conceptual asset? Add every one that does.

Do this per conceptual asset, after its elements are listed. It is a check on a list you \
have already written, not a repeat of the search that wrote it. A conceptual asset is \
finished when the closed set has been read against it -- not when its elements stop coming \
readily."""


def _apply_a08(core: str, label: str = "V5") -> str:
    """Insert the closure sweep immediately before RULES. Round-trips or fails loudly."""
    n = core.count(_A08_ANCHOR)
    assert n == 1, f"A-08/{label}: RULES anchor matches {n} times, expected 1"
    out = core.replace(_A08_ANCHOR, _A08_SWEEP + _A08_ANCHOR)
    assert out.replace(_A08_SWEEP, "") == core, \
        f"A-08/{label}: changed something outside the insertion"
    assert out != core, f"A-08/{label}: no-op"
    return out


ASSET_PRIMARY_CORE_V5 = _apply_a08(ASSET_PRIMARY_CORE_V4)


# ============ Input ablation family (arms P-1 / P-2' / P-3) ============
# WHY. Line 5 receives ~34.5k tokens per call: system prompt 106k chars plus a user message
# of summary 11% / parsed ports 42% / parsed signals 16% / RTL 31%. It emits 428 assets for
# 111 references. LASP (MLCAD'24) feeds a compact RTL ABSTRACTION instead, because it cannot
# fit the RTL at all -- so "is over-emission driven by input volume?" is a real question that
# nothing in this study has tested. This family answers it one block at a time.
#
# THE ABLATION IS NOT JUST DROPPING A BLOCK. The core prompt DECLARES its inputs and then
# refers back to them, so removing a block from the user message while the prompt still says
# to ground in it leaves dangling instructions -- the model would be told to use something
# absent, which is a confound, not a clean removal. Each variant below therefore also removes
# the prompt's references to that block. One coherent proposition, several edits, exactly as
# in A-03.
#
# P-2 AS ORIGINALLY SKETCHED WAS DROPPED. Removing the parsed ports/signals would also have
# required deleting the closed-set contract, A-03's port-vs-signal granularity rule, and the
# whole of A-08's closure sweep -- two arms' worth of instruction alongside the input, so no
# result could be attributed. Its hypothesis ("is the closed set load-bearing?") needs no
# experiment either: without it nothing can bind, validate_primary rejects everything, and
# the measurement would be of a contract breaking rather than of information. P-2' strips the
# `function` FIELD instead, keeping the binding contract intact and isolating what stage 4's
# LLM annotation contributes separately from the names it extracted.

_P1_EDITS = (
    # the INPUTS declaration
    ('(1) TECHNICAL SUMMARY -- SoC-context spec summary (may say "not specified in retrieved '
     'spec"; never fill such gaps from general knowledge).\n', ""),
    # every instruction that tells the model to ground in it
    ("with a reason grounded in the summary or RTL.",
     "with a reason grounded in the RTL."),
    ("violates the chosen objective) in the summary or RTL only;",
     "violates the chosen objective) in the RTL only;"),
    ('"Why": "<which of C/I/A/U triggered, grounded in the summary or RTL>"',
     '"Why": "<which of C/I/A/U triggered, grounded in the RTL>"'),
)


def _apply_drop_summary(core: str, label: str = "P1") -> str:
    """Remove the technical summary and every reference to it. Round-trips or fails loudly.

    Deliberately does NOT renumber the remaining (2)(3)(4) input labels: renumbering would
    touch three more lines for no semantic gain, and a gap in the numbering costs nothing.
    """
    out = core
    for old, new in _P1_EDITS:
        n = core.count(old)
        assert n == 1, f"{label}: anchor matches {n} times, expected 1 -- {old[:52]!r}"
        out = out.replace(old, new)
    back = out
    for old, new in reversed(_P1_EDITS):
        back = back.replace(new, old) if new else back
    assert "summary" not in out.lower() or out.lower().count("summary") == 0, \
        f"{label}: a reference to the summary survived"
    assert out != core, f"{label}: no-op"
    return out


ASSET_PRIMARY_CORE_P1 = _apply_drop_summary(ASSET_PRIMARY_CORE_V5)


# ============ Input ablation -- drop the parsed closed set (arm P-2) ============
# THE ORIGINAL OBJECTION TO P-2 WAS WRONG, and the log now says so. It read: removing the
# parsed ports/signals "would also have required deleting the closed-set contract, A-03's
# port-vs-signal granularity rule, and the whole of A-08's closure sweep". That assumed the
# CLOSED SET is the two JSON blocks. It is not -- it is an abstraction the prompt defines,
# and the RTL already contains every declaration it is built from. VHDL states its ports in
# the entity clause and its signals in the architecture declarative part; Verilog states
# both in the module header and body. So the closed set is RE-SOURCED, not deleted:
#
#     before   "the two JSON blocks you are given ARE the closed set"
#     after    "the RTL's own declarations ARE the closed set -- read them off yourself"
#
# Every downstream instruction that says "closed set" stays literally true and byte-
# identical: DEFINITIONS, STEP 2 (both sentences), T-1's "a conceptual asset with no
# closed-set element still belongs here", A-08's whole sweep, and the output contract slot.
# A-03 survives too -- its example sentence is carried into (4) verbatim, and its RULES
# bullet keeps the granularity text appended to it. THREE edits, all of them re-pointing
# the same idea at a different source.
#
# WHAT THIS ARM ACTUALLY ASKS, and it is not a LAsset replication. Algorithm 1 line 5 always
# receives Prm_m; the paper has no configuration without it, so unlike P-1 there is no
# published counterpart to check ourselves against. The question is ours: the parsed blocks
# are 58% of every user message, and stage 4 spends an LLM call per module to build them.
# If the model reads the declarations out of the RTL just as well, that stage is overhead.
#
# CONFOUND, REGISTERED IN ADVANCE. Dropping the blocks removes the NAMES and the `function`
# annotations together, so a recall fall cannot be attributed between them. P-2' (strip only
# `function`, keep the names) is the follow-up that separates them, and it should be run on
# v01c6p1 whichever way this lands.

_P2_INPUTS_OLD = ('(2) PARSED I/O PORTS and (3) PARSED INTERNAL SIGNALS -- each is a JSON '
                  'object with fields including entity, name, direction(dir), type, function '
                  '(signals also have kind). TOGETHER they are the CLOSED SET of design '
                  'elements. Every asset MUST bind to exactly one element from this set by '
                  'its exact "name". Ports AND internal signals/registers are equally '
                  'eligible. Never invent, rename, split, or merge a name; copy record-field '
                  'names verbatim including the dot (e.g. "ctrl.buf_req", '
                  '"rtx_engine.sreg").\n(4) RTL -- ground truth for what each element does.')

# The input numbering is deliberately NOT compacted, exactly as in P-1: "(4) RTL" is the
# marker _BLOCK_MARKERS uses to police a future P-3, and renumbering would break it silently
# for no semantic gain. A gap in the numbering costs nothing.
_P2_INPUTS_NEW = ('(4) RTL -- the module source, and ground truth for what each element '
                  'does. Its entity/port declarations and its architecture signal '
                  'declarations TOGETHER are the CLOSED SET of design elements; read them '
                  'off the source yourself. Every asset MUST bind to exactly one element '
                  'declared there, by its exact declared name. Ports AND internal '
                  'signals/registers are equally eligible. Never invent, rename, split, or '
                  'merge a name; copy record-field names verbatim including the dot '
                  '(e.g. "ctrl.buf_req", "rtx_engine.sreg").')

_P2_EDITS = (
    (_P2_INPUTS_OLD, _P2_INPUTS_NEW),
    # A-03's RULES anchor. Only the anchor sentence moves; A-03's granularity text is
    # appended after it and is not touched.
    ('- "Asset RTL" MUST be the exact "name" of one element from the provided ports/signals.',
     '- "Asset RTL" MUST be the exact declared name of one element from the module\'s '
     'ports/signals.'),
    # there is no "entity" FIELD any more -- the entity is read from the RTL
    ('- "Entity" MUST be copied verbatim from that element\'s "entity" field.',
     '- "Entity" MUST be the RTL entity/module that declares the element, copied verbatim.'),
)


def _apply_drop_parsed(core: str, label: str = "P2") -> str:
    """Re-source the closed set from the RTL. Round-trips, or fails loudly."""
    out = core
    for old, new in _P2_EDITS:
        n = core.count(old)
        assert n == 1, f"{label}: anchor matches {n} times, expected 1 -- {old[:60]!r}"
        out = out.replace(old, new)
    back = out
    for old, new in reversed(_P2_EDITS):
        back = back.replace(new, old)
    assert back == core, f"{label}: changed something outside the three edits"
    assert out != core, f"{label}: no-op"
    # The declaration of the parsed blocks must be gone; the ABSTRACTION must survive.
    for gone in ("PARSED I/O PORTS", "PARSED INTERNAL SIGNALS", '"entity" field',
                 "type, function"):
        assert gone not in out, f"{label}: {gone!r} survived the drop"
    for kept in ("CLOSED SET", "closed-set element", "closed set", "rtx_engine.sreg",
                 "Record-typed PORTS are named WHOLE", "CLOSE EACH CONCEPT"):
        assert kept in out, f"{label}: {kept!r} was lost -- an earlier arm has been damaged"
    return out


ASSET_PRIMARY_CORE_P1P2 = _apply_drop_parsed(ASSET_PRIMARY_CORE_P1)


# ============ Remove evaluation-set identifiers from the prompt (arm L-1) ============
# WHAT WAS FOUND, 2026-08-08. The core quotes four literal design identifiers as naming
# examples, and all four are real elements of the modules we evaluate on. One of them is an
# ANSWER:
#
#   ctrl_i             ground truth in 10 of the 41 annotated modules -- cpu_alu, cpu_counters,
#                      cpu_cp_bitmanip, cpu_cp_cond, cpu_cp_crypto, cpu_cp_fpu, cpu_cp_shifter,
#                      cpu_lsu, cpu_pmp, cpu_regfile. A-03's rule says "when it carries an
#                      asset, the asset is the port itself (ctrl_i)", which states the answer.
#   ctrl_i.csr_wdata   declared in cpu_cp_muldiv, cpu_pmp. Not an answer.
#   ctrl.buf_req       declared in cache. Not an answer.
#   rtx_engine.sreg    declared in spi. Not an answer.
#
# SIZE OF THE PROBLEM, STATED HONESTLY. Within the 15 modules we currently score, ctrl_i is an
# answer in cpu_pmp alone -- 1 reference in 111, at most 0.009 of recall. The other nine are in
# the 26 modules we have no RTL for, which is exactly the held-out set proposed for the first
# generalisation test. So the cost of leaving this in is small today and disqualifying for the
# measurement that matters most.
#
# IT IS NOT A CONFOUND FOR P-1 OR P-2. The identifiers entered at A-03 (v01c3) and are
# inherited by every later version, so they sit in the baseline and the arm alike and cancel in
# every paired delta computed so far. What they threaten is the ABSOLUTE recall figure quoted
# against the paper, and any future run on unseen modules. P-2's result stands.
#
# WHY A NEW VERSION RATHER THAN AN EDIT IN PLACE. Rewriting _A03_RULE would change the sha of
# v01c3, v01r, v01c4, v01c5, v01c6, v01c6p1 and v01c6p1p2 -- eight runs whose recorded
# provenance would stop matching the code that claims to have produced them. The chain records
# what was run. This is a forward fix, and it is measurable: if recall is unchanged, the leak
# was doing no work; if it falls by more than ~0.009, it was doing more than its token count.
#
# clk_i AND rstn_i ARE DELIBERATELY LEFT. They appear as "Global clock/reset ports (e.g. clk_i,
# rstn_i) ... are NOT assets". Neither is ground truth in ANY of the 41 modules, so neither
# states an answer; both are universal VHDL naming convention rather than anything specific to
# this design; and they serve a rule that is correct. Removing them would make a legitimate
# instruction vaguer and buy nothing.
#
# REPLACEMENTS are checked absent from all 1 355 parsed element names AND all 218 ground-truth
# names across the 41 annotated modules, base identifier as well as dotted form.

_L1_EDITS = (
    # the INPUTS naming example -- two internal record fields
    ('(e.g. "ctrl.buf_req", "rtx_engine.sreg").',
     '(e.g. "blk_ctrl.step", "xfer_unit.stage").'),
    # A-03's rule: the record PORT named whole, and the field it must not be named by
    ('the asset is the port itself ("ctrl_i"), never one of its fields '
     '("ctrl_i.csr_wdata").',
     'the asset is the port itself ("cfg_port_i"), never one of its fields '
     '("cfg_port_i.mode").'),
    # A-03's fence: the internal record field, which points back at the INPUTS example
    ('there the field is the asset ("ctrl.buf_req"), as above.',
     'there the field is the asset ("blk_ctrl.step"), as above.'),
)

_L1_BANNED = ("ctrl_i", "ctrl_i.csr_wdata", "ctrl.buf_req", "rtx_engine.sreg")


def _apply_deleak(core: str, label: str = "L1") -> str:
    """Replace every evaluation-set identifier with a neutral one. Round-trips or fails."""
    out = core
    for old, new in _L1_EDITS:
        n = core.count(old)
        assert n == 1, f"{label}: anchor matches {n} times, expected 1 -- {old[:60]!r}"
        out = out.replace(old, new)
    back = out
    for old, new in reversed(_L1_EDITS):
        back = back.replace(new, old)
    assert back == core, f"{label}: changed something outside the three edits"
    # plain substring, not a word-boundary regex: stricter, and prompts.py imports nothing
    for b in _L1_BANNED:
        assert b not in out, f"{label}: {b!r} survived"
    # the RULE ITSELF must be intact -- this arm removes names, not instruction
    for kept in ("Record-typed PORTS are named WHOLE", "Record-typed INTERNAL signals are the "
                 "opposite", "copy record-field names verbatim including the dot",
                 "clk_i", "rstn_i"):
        assert kept in out, f"{label}: {kept!r} was lost -- the rule has been damaged"
    return out


ASSET_PRIMARY_CORE_P1P2D = _apply_deleak(ASSET_PRIMARY_CORE_P1P2)


# The ICL splice (LAsset Alg.1 line 5: LLMASSET(..., ICLASSET)) is deliberately NOT done
# here. It belongs to the version registry in the notebook's Stage B cell, which picks the
# (core, examples) pair from VERSION:
#     ASSET_PRIMARY_SYSTEM = ASSET_PRIMARY_CORE + "\n\n" + <the ICL block VERSION selects>
#
# A module-level ASSET_PRIMARY_SYSTEM used to live here, pinned to icl_asset_examples (=v1).
# Nothing imported it, but anything that did would have silently received v1 regardless of
# VERSION -- in an ablation that is a result-invalidating trap, not an inconvenience. Its
# removal also lets prompts.py be imported without icl_asset_examples.py present.
#
# Splice by CONCATENATION, never an f-string: the case studies are full of literal JSON
# braces. verify_icl.py machine-checks the examples against the output contract above.