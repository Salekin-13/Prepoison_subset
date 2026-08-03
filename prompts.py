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