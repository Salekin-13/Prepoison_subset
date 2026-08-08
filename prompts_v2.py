"""V2 asset-generation prompts — the PRECISION study.

Separate module from `prompts.py` on purpose. The v1 chain (v0 -> v01c6p1p2) was a RECALL
study and its eleven core variants are built by stacked substitution; adding precision arms
on top of that stack would make every new sha depend on eight earlier edits. V2 starts from
one flat baseline string and applies one documented edit per arm, exactly as v1 did, but
with a clean root.

`prompts.py` IS NOT MODIFIED. Every v1 sha still resolves to the code that produced it.

WHAT THE V2 BASELINE IS. The user-supplied draft (ASSET_V2_DRAFT) is the v01c6p1p2 core
transcribed by hand: P-2's input regime (RTL only -- no spec summary, no parsed
ports/signals), T-1's visible ConceptualAssets, A-02's role-not-location, A-03's port
granularity, A-08's closure sweep. It is preserved BYTE-FOR-BYTE so the two corrections
below are visible as edits rather than folded into a retype.

TWO CORRECTIONS ARE APPLIED ON TOP, and each is a separate, reversible function:

  D  CLOSED-SET PARITY. The draft's RULES still say "from the provided ports/signals" and
     "that element's 'entity' field". Under this input regime there ARE no provided
     ports/signals and no entity field -- the model reads declarations off the RTL. Leaving
     the text as-is tells the model to use something absent, which the log calls a confound
     rather than an ablation (it is what nearly wrecked P-1). This restores the wording
     `_apply_drop_parsed` already uses in v1, so the baseline is honest about its own inputs.

  L  DE-LEAK (v1 arm L-1). The draft quotes four real NEORV32 identifiers as naming
     examples. One of them, `ctrl_i`, is a ground-truth ANSWER in 10 of the 41 annotated
     modules -- A-03's rule literally says a record port carrying an asset is named whole,
     "ctrl_i". Nine of those ten are in the 26 held-out modules, so the leak is worth <=0.009
     recall today and is disqualifying for the generalisation test that is the point of the
     held-out set.

BOTH ARE ON BY DEFAULT. To run the draft verbatim instead, set ASSET_V2_BASE = ASSET_V2_DRAFT
at the bottom -- but then the leak and the dangling references are in the baseline of every
arm in the study, and no arm's absolute precision figure can be quoted against the paper.

STANDING RULE inherited from v1 §6: no literal identifier from any of the 41 annotated
modules may enter a prompt. `audit()` at the bottom checks this and is called at import.
"""
from __future__ import annotations

import hashlib

# =============================================================================
# The draft, as supplied. Three MECHANICAL fixes only -- no wording changed:
#   1. `{{"IP":` -> `{"IP":`   the doubled brace is an f-string escape artefact. The ICL
#      splice is a CONCATENATION, never an f-string (the examples are full of literal JSON
#      braces), so `{{` would reach the model as two literal braces and corrupt the contract.
#   2. `explicitly (internally).\` + newline -> a space before "Report every conceptual".
#      A backslash-newline in a Python string joins with NO space: "(internally).Report".
#   3. `closed-set element still\` + newline -> a space before "belongs here". Same defect:
#      it would have read "stillbelongs here".
# Nothing else differs from the text supplied.
# =============================================================================

ASSET_V2_DRAFT = """Your task: identify the PRIMARY SECURITY ASSETS in ONE hardware IP \
module for pre-silicon security verification, following the IEEE P3164 Conceptual-and-Structural \
Analysis (CSA).

INPUTS (in the user message):
(4) RTL -- the module source, and ground truth for what each element does. \
Its entity/port declarations and its architecture signal declarations \
TOGETHER are the CLOSED SET of design elements; read them off the source \
yourself. Every asset MUST bind to exactly one element declared there, by \
its exact declared name. Ports AND internal signals/registers are equally \
eligible. Never invent, rename, split, or merge a name; copy record-field \
names verbatim including the dot (e.g. "ctrl.buf_req", "rtx_engine.sreg").

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
STEP 1 -- CONCEPTUAL ASSETS (output these; see the contract). Apply the rubric to \
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
An element is an asset iff at least one of C/I/A/U is "yes" with a reason grounded in the RTL. \
An element answering "no" to all four is NOT an asset; make such non-asset decisions explicitly \
(internally). Report every conceptual asset you identify in "ConceptualAssets", each with a \
short id. This is a record of STEP 1, NOT a substitute for STEP 2 -- a conceptual asset with no \
closed-set element still belongs here, and every structural asset must still appear in "Assets".

STEP 2 -- STRUCTURAL (PRIMARY) ASSETS. Map each conceptual asset to the concrete closed-set \
element(s) that store, carry, generate, or gate it. A conceptual asset may fan out to SEVERAL \
elements -- emit one object per element. If NO closed-set element supports a conceptual asset, \
OMIT it -- never fabricate an element.
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
internal signals ZBT_addr and ZBT_addr2.

STEP 2 (continued) -- CLOSE EACH CONCEPT. Before leaving a conceptual asset, make one more \
pass over the closed set for that asset alone, and ask of each element: does this element \
also produce, store, transport or gate this same conceptual asset? Add every one that does.

Do this per conceptual asset, after its elements are listed. It is a check on a list you \
have already written, not a repeat of the search that wrote it. A conceptual asset is \
finished when the closed set has been read against it -- not when its elements stop coming \
readily.

RULES:
- "Asset RTL" MUST be the exact "name" of one element from the provided ports/signals. If an \
idea cannot bind to a real element, drop it.
- Record-typed PORTS are named WHOLE. A record port is the module's external interface; \
when it carries an asset, the asset is the port itself ("ctrl_i"), never one of its fields \
("ctrl_i.csr_wdata"). Record-typed INTERNAL signals are the opposite and are unchanged by \
this rule -- there the field is the asset ("ctrl.buf_req"), as above.
- "Entity" MUST be copied verbatim from that element's "entity" field.
- "Security Objective" is MANDATORY: exactly ONE of "Confidentiality", "Integrity", \
"Availability" -- the dominant objective. Fold (U) findings into Integrity or Availability. Note \
any non-dominant objective inside the Justification.
- Global clock/reset ports (e.g. clk_i, rstn_i) and pure boilerplate are NOT assets unless \
clock/reset control is the module's actual function.
- Ground "Functionality" (what the element does/carries) and "Justification" (why its compromise \
violates the chosen objective) in the RTL only; do not add outside knowledge or \
assess exploitability. Every asset carries explicit reasoning.

OUTPUT CONTRACT (strict): return ONE JSON object and nothing else -- no markdown, no code fences, \
no prose:
{"IP": "<module name>",
 "ConceptualAssets": [
   {"id": "<short id, e.g. C1>",
    "Concept": "<the data or system state, e.g. 'watchdog timeout configuration'>",
    "Security Objective": "Confidentiality" | "Integrity" | "Availability",
    "Why": "<which of C/I/A/U triggered, grounded in the RTL>"}
 ],
 "Assets": [
   {"Asset Name": "<short descriptive title>",
    "Concept": "<id of the ConceptualAssets entry this element realises>",
    "Asset RTL": "<element name from the closed set>",
    "Entity": "<the element's entity, verbatim>",
    "Functionality": "<what it does/carries>",
    "Security Objective": "Confidentiality" | "Integrity" | "Availability",
    "Justification": "<why its compromise violates the objective>"}
 ]}
If the module has no assets, return {"IP": "<module name>", "Assets": []}."""


# =============================================================================
# Correction D -- closed-set parity with the actual inputs.
#
# The draft's RULES were written when the user message carried two JSON blocks. It does not
# any more. These two lines are the only survivors that still point at them, and they are
# the exact two lines v1's `_apply_drop_parsed` rewrites for the same reason. Wording is
# copied from there verbatim so v2's baseline and v1's v01c6p1p2 say the same thing.
# =============================================================================

_D_EDITS = (
    ('- "Asset RTL" MUST be the exact "name" of one element from the provided '
     'ports/signals.',
     '- "Asset RTL" MUST be the exact declared name of one element from the module\'s '
     'ports/signals.'),
    ('- "Entity" MUST be copied verbatim from that element\'s "entity" field.',
     '- "Entity" MUST be the RTL entity/module that declares the element, copied verbatim.'),
)


def _apply_parity(core: str, label: str = "D") -> str:
    """Re-point the two dangling references at the RTL. Round-trips, or fails loudly."""
    out = core
    for old, new in _D_EDITS:
        n = core.count(old)
        assert n == 1, f"{label}: anchor matches {n}x, expected 1 -- {old[:60]!r}"
        out = out.replace(old, new)
    back = out
    for old, new in reversed(_D_EDITS):
        back = back.replace(new, old)
    assert back == core, f"{label}: changed something outside the two edits"
    for gone in ("the provided ports/signals", '"entity" field'):
        assert gone not in out, f"{label}: {gone!r} survived"
    # The closed-set ABSTRACTION must survive; only its source moves.
    for kept in ("CLOSED SET", "closed-set element", "closed set",
                 "Record-typed PORTS are named WHOLE", "CLOSE EACH CONCEPT"):
        assert kept in out, f"{label}: {kept!r} was lost -- an instruction has been damaged"
    return out


# =============================================================================
# Correction L -- de-leak (v1 arm L-1, unrun there, folded in here).
#
#   ctrl_i             GROUND TRUTH in 10 of the 41 annotated modules (cpu_alu, cpu_counters,
#                      cpu_cp_bitmanip, cpu_cp_cond, cpu_cp_crypto, cpu_cp_fpu,
#                      cpu_cp_shifter, cpu_lsu, cpu_pmp, cpu_regfile). This one states an
#                      ANSWER, in the form of a naming rule.
#   ctrl_i.csr_wdata   declared in cpu_cp_muldiv, cpu_pmp. Not an answer.
#   ctrl.buf_req       declared in cache. Not an answer.
#   rtx_engine.sreg    declared in spi. Not an answer.
#
# Replacements were checked in v1 against all 1 355 parsed element names and all 218
# ground-truth names across the 41 annotated modules, base identifier and dotted form.
# INHERITED from the v1 log, not re-verified here -- re-run scratchpad/identifier_audit.py
# before trusting it for a publication figure.
#
# clk_i and rstn_i ARE DELIBERATELY KEPT. Neither is ground truth in ANY of the 41 modules,
# so neither states an answer; both are universal VHDL convention rather than anything
# specific to this design; and they serve a rule that is correct.
# =============================================================================

_L_EDITS = (
    ('(e.g. "ctrl.buf_req", "rtx_engine.sreg").',
     '(e.g. "blk_ctrl.step", "xfer_unit.stage").'),
    ('the asset is the port itself ("ctrl_i"), never one of its fields '
     '("ctrl_i.csr_wdata").',
     'the asset is the port itself ("cfg_port_i"), never one of its fields '
     '("cfg_port_i.mode").'),
    ('there the field is the asset ("ctrl.buf_req"), as above.',
     'there the field is the asset ("blk_ctrl.step"), as above.'),
)

# Plain substrings, not word-boundary regexes: stricter, and this module imports nothing
# beyond hashlib.
BANNED_IDENTIFIERS = ("ctrl_i", "ctrl_i.csr_wdata", "ctrl.buf_req", "rtx_engine.sreg")


def _apply_deleak(core: str, label: str = "L") -> str:
    """Replace every evaluation-set identifier with a neutral one. Round-trips, or fails."""
    out = core
    for old, new in _L_EDITS:
        n = core.count(old)
        assert n == 1, f"{label}: anchor matches {n}x, expected 1 -- {old[:60]!r}"
        out = out.replace(old, new)
    back = out
    for old, new in reversed(_L_EDITS):
        back = back.replace(new, old)
    assert back == core, f"{label}: changed something outside the three edits"
    for b in BANNED_IDENTIFIERS:
        assert b not in out, f"{label}: {b!r} survived"
    # This arm removes NAMES, not instruction. The rules themselves must be intact.
    for kept in ("Record-typed PORTS are named WHOLE",
                 "Record-typed INTERNAL signals are the opposite",
                 "copy record-field names verbatim including the dot", "clk_i", "rstn_i"):
        assert kept in out, f"{label}: {kept!r} was lost -- the rule has been damaged"
    return out


# ---------------------------------------------------------------- the baseline ---
# Flip to ASSET_V2_DRAFT to run the supplied text verbatim; see the module docstring for
# what that costs.
ASSET_V2_BASE = _apply_deleak(_apply_parity(ASSET_V2_DRAFT))


# =============================================================================
# ARMS. One proposition each, applied to ASSET_V2_BASE, nothing stacked.
# Each is registered in ABLATION_LOG_V2.md with an Expect and a decision rule BEFORE it
# runs. None is built yet -- E-1 is first in the queue.
# =============================================================================

# E-1  replicated interconnect is not an asset of the module it passes through
# E-2  revert the A-08 per-concept closure sweep
# E-3  tighten what qualifies as a secret (rubric (C))
# E-4  per-concept element budget WITH an explicit ranking criterion
# E-5  restore port-record granularity -- measure first, may not become an arm


# ------------------------------------------------------------------- audit ---

def sha(core: str, icl: str = "") -> str:
    """First 12 hex of the sha256 of the composed system prompt, matching the run loop."""
    text = core + ("\n\n" + icl if icl else "")
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def audit(core: str, label: str = "core") -> None:
    """The standing rule: no identifier from the 41 annotated modules may enter a prompt.

    Substring check against the four known leaks only. It is NOT a general audit -- a new
    example added by hand still needs scratchpad/identifier_audit.py run against the full
    parsed and ground-truth name lists.
    """
    hits = [b for b in BANNED_IDENTIFIERS if b in core]
    assert not hits, f"{label}: evaluation-set identifier(s) present: {hits}"


audit(ASSET_V2_BASE, "ASSET_V2_BASE")

# The draft is expected to FAIL the audit -- that is why the correction exists. Asserting
# it here means the day someone "cleans up" the draft, this line fails and tells them the
# de-leak has become a no-op rather than letting it pass silently.
assert any(b in ASSET_V2_DRAFT for b in BANNED_IDENTIFIERS), \
    "ASSET_V2_DRAFT no longer contains the leak -- _apply_deleak is now a no-op"
assert ASSET_V2_BASE != ASSET_V2_DRAFT, "corrections are a no-op"

if __name__ == "__main__":
    print(f"ASSET_V2_DRAFT  {len(ASSET_V2_DRAFT):6d} chars  core-sha {sha(ASSET_V2_DRAFT)}")
    print(f"ASSET_V2_BASE   {len(ASSET_V2_BASE):6d} chars  core-sha {sha(ASSET_V2_BASE)}")
    print(f"delta           {len(ASSET_V2_BASE) - len(ASSET_V2_DRAFT):+6d} chars")
