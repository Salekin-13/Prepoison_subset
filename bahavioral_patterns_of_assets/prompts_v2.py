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

THREE CORRECTIONS ARE APPLIED ON TOP, and each is a separate, reversible function:

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

  N  NEUTRALISE. The two real identifiers L-1 left behind (`clk_i`, `rstn_i`, quoted in the
     clock/reset rule) and the two P3164 ones (`ZBT_addr`, `ZBT_addr2`) are removed, the
     output contract's `'watchdog timeout configuration'` placeholder is replaced, and a new
     RULES bullet declares every surviving quoted identifier illustrative and forbids
     emitting any name not read in the RTL. See the block above _N_EDITS for the evidence.

ALL THREE ARE ON BY DEFAULT. To run the draft verbatim instead, set ASSET_V2_BASE = ASSET_V2_DRAFT
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
    # NOTE: clk_i/rstn_i are deliberately NOT asserted here. Correction N removes them at
    # the next stage, so asserting their presence would couple this function to an
    # ordering. What matters is that the RULE survives, which is what is checked.
    for kept in ("Record-typed PORTS are named WHOLE",
                 "Record-typed INTERNAL signals are the opposite",
                 "copy record-field names verbatim including the dot",
                 "pure boilerplate are NOT assets"):
        assert kept in out, f"{label}: {kept!r} was lost -- the rule has been damaged"
    return out


# =============================================================================
# Correction N -- neutralise every remaining real identifier, and say so in the prompt.
#
# WHY, BEYOND L. L-1 removed the four identifiers that were ANSWERS or near-answers. Two
# real NEORV32 names survived it, in a rule that states a NEGATIVE:
#
#   "Global clock/reset ports (e.g. clk_i, rstn_i) ... are NOT assets"
#
# Neither is ground truth in any of the 41 modules, which is why L-1 left them. That test
# was the wrong one. `clk_i` is declared 24 times and `rstn_i` 22 times across the 15
# SCORED modules, so the prompt was stating a correct negative fact about 46 real elements
# of the evaluation set. In a RECALL study that is nearly free. In a PRECISION study it is
# a leak pointing the right way: bound at +0.025 precision if the model would otherwise
# have named them all -- larger than arm E-1's entire expected gain. Measured: even with
# the rule in force the model still emits `rstn_i` twice across 45 module-repeats, so the
# rule is doing real suppression work.
#
# The rule survives without the examples. "Global clock and reset ports" is unambiguous.
#
# ZBT_addr / ZBT_addr2 ALSO GO, though they are NOT NEORV32 names -- they come from IEEE
# P3164 3.2.4's SRAM controller, and are verified absent from all 1355 parsed names and all
# 218 ground-truth names. They are removed for a different reason: a quoted identifier is a
# naming template the model copies. Keeping only invented names makes the standing rule
# checkable by a single substring sweep rather than by remembering which real names were
# judged harmless.
#
# WHAT STAYS, AND WHY. cfg_port_i / cfg_port_i.mode / blk_ctrl.step / xfer_unit.stage are
# INVENTED. The granularity rule cannot be stated without showing a record and one of its
# fields, so these earn their place. They are covered by the new disclaimer instead.
#
# THE DISCLAIMER IS THE POINT OF THIS CORRECTION, not a footnote. v1 evidence: `ctrl_i` was
# quoted as a naming example and became the single worst false positive in the study
# (cpu_pmp:ctrl_i, 7 occurrences over 3 repeats). The model copies quoted identifiers into
# its output. Telling it not to is cheap and directly targets that behaviour.
# =============================================================================

_N_EDITS = (
    # the clock/reset rule -- keep the rule, drop the two real names
    ('- Global clock/reset ports (e.g. clk_i, rstn_i) and pure boilerplate are NOT assets '
     'unless clock/reset control is the module\'s actual function.',
     '- Global clock and reset ports and pure boilerplate are NOT assets unless clock/reset '
     'control is the module\'s actual function.'),
    # P3164's SRAM controller -- keep the point (structural assets can be internal), drop
    # the two identifiers
    ('for the SRAM controller (3.2.4), whose structural assets are the internal signals '
     'ZBT_addr and ZBT_addr2.',
     'for the SRAM controller (3.2.4), whose structural assets are internal address signals '
     'rather than ports.'),
    # the output contract's placeholder CONCEPT. Not an identifier -- which is why it passed
    # every name sweep -- but `neorv32_wdt` is one of the 15 SCORED modules and `ctrl.timeout`
    # is a ground-truth asset in it, so the contract's throwaway example described a real
    # answer in the evaluation set. Inherited from V0 and present in every v1 version.
    # `sensor calibration constants` is verified: no module of the 41 has that function, and
    # neither "sensor" nor "calib" occurs in any parsed or ground-truth name.
    ("\"Concept\": \"<the data or system state, e.g. 'watchdog timeout configuration'>\"",
     "\"Concept\": \"<the data or system state, e.g. 'sensor calibration constants'>\""),
    # the disclaimer, inserted as its own RULES bullet immediately before the grounding rule
    ('- Ground "Functionality" (what the element does/carries)',
     '- Identifiers quoted in these instructions (e.g. "cfg_port_i", "blk_ctrl.step") are '
     'INVENTED illustrations of a naming pattern, and identifiers in the worked examples '
     'below belong to those example IPs. NONE of them exists in the module you are given. '
     'Never emit a name you have not read in the RTL above, and never let a quoted name '
     'steer which real element you choose.\n'
     '- Ground "Functionality" (what the element does/carries)'),
)

# Real identifiers that must never appear in a v2 prompt. The L-1 four, plus the two the
# clock/reset rule used to quote. All six are declared in RTL_data.
EVAL_SET_IDENTIFIERS = BANNED_IDENTIFIERS + ("clk_i", "rstn_i")
# Real, but from IEEE P3164 rather than NEORV32. Removed as naming templates, not as leaks.
EXTERNAL_IDENTIFIERS = ("ZBT_addr", "ZBT_addr2")


def _apply_neutralise(core: str, label: str = "N") -> str:
    """Remove every remaining real identifier and declare the surviving ones illustrative."""
    out = core
    for old, new in _N_EDITS:
        n = core.count(old)
        assert n == 1, f"{label}: anchor matches {n}x, expected 1 -- {old[:60]!r}"
        out = out.replace(old, new)
    back = out
    for old, new in reversed(_N_EDITS):
        back = back.replace(new, old)
    assert back == core, f"{label}: changed something outside the four edits"
    for gone in EVAL_SET_IDENTIFIERS + EXTERNAL_IDENTIFIERS:
        assert gone not in out, f"{label}: {gone!r} survived"
    # The rules must survive the removal -- this correction takes out names, not instruction.
    for kept in ("pure boilerplate are NOT assets",
                 "clock/reset control is the module's actual function",
                 "Record-typed PORTS are named WHOLE",
                 "structural assets are internal address signals",
                 "Never emit a name you have not read in the RTL above"):
        assert kept in out, f"{label}: {kept!r} missing -- a rule was damaged, not neutralised"
    return out


# ---------------------------------------------------------------- the baseline ---
# Flip to ASSET_V2_DRAFT to run the supplied text verbatim; see the module docstring for
# what that costs.
ASSET_V2_BASE = _apply_neutralise(_apply_deleak(_apply_parity(ASSET_V2_DRAFT)))


# =============================================================================
# ARMS. One proposition each, applied to ASSET_V2_BASE, nothing stacked.
# Each is registered in ABLATION_LOG_V2.md with an Expect and a decision rule BEFORE it
# runs. None is built yet -- E-1 is first in the queue.
# =============================================================================

# S-1  container vs content            BUILT BELOW, first arm of the revised plan
# S-2  require an SA-EDI asset type    not built
# S-3  attachment vs function          not built (was E-1; headroom corrected to +0.052)
# S-4  one object per element          not built (was E-7; gain corrected to +0.009)
# E-2  revert the A-08 closure sweep   not built; the only arm with zero overtuning risk
#      -- it REMOVES an instruction we added rather than adding a design-specific criterion
#
# CLOSED, do not re-propose:
#   E-6 record enumeration  -- four independent discriminator families tested, all null
#       (write/read 70.2%, width 52.1%, control-dependence 57.4%, output reach 64.9%,
#       best conjunction 74.5%, against a 68.1% always-say-no baseline). wdt::ctrl.lock
#       (asset) and ctrl.strict (non-asset) have identical feature vectors. The reference
#       itself has no consistent per-field rule: its justifications are written per REGISTER
#       and shared verbatim across fields, and uart's names "IRQ levels, clears" among the
#       configuration it protects while listing neither as an asset.
#   E-3 confidentiality     -- subsumed by S-2; SA-EDI's "Secret" type covers it generally,
#       and v2 already moved Confidentiality precision 0.144 -> 0.208 untouched.
#   E-4 per-concept budget  -- a count encodes an expected asset density. Ours varies from
#       2 (hwspinlock) to 14 (cpu) per module, so no single number generalises.


# ============ S-1 · Container vs content ============
# THE TARGET, measured on v2's own output. Splitting every false positive by whether the
# model found the right record:
#     dotted, record HAS a ground-truth asset  163 of 930 = 17.5%  (right register, extra
#                                                                   fields -- NOT fixable)
#     dotted, record has NO ground-truth asset 225 of 930 = 24.2%  (wrong register -- THIS)
#     not a record field at all                542 of 930 = 58.3%
# Removing the wrong-register group entirely gives emit 412.7 -> 337.7, precision
# 0.251 -> 0.304. Worst offenders are buffers and protocol sub-blocks: twi:fifo 34,
# uart:tx_fifo 21, uart:rx_fifo 20, spi:tx_fifo 19, twi:engine 16, spi:rtx_engine 15,
# cpu_cp_cfu:xtea 15, twi:io_con 14.
#
# WHY THIS IS A REAL DISTINCTION AND NOT A NAME LIST. The reference is consistent about it:
# trng's fifo fields ARE assets (the buffer holds entropy) while twi's, uart's and spi's are
# not (the same structure holding ordinary traffic). cpu_cp_cfu's key_mem IS an asset while
# the xtea cipher's internals are not. The model names the machinery; the reference names
# what the machinery protects.
#
# GROUNDING. SA-EDI Table 2 types the CONTENT, not the vessel -- "Secret: Material that
# requires confidentiality", "Critical: Material that is critical for proper functionality".
# P3164 3.1.2 asks for the RTL that produces, stores and transports a conceptual asset, so a
# transport structure is in scope only once a conceptual asset has been established to
# transport. This rule states the missing precondition.
#
# LEAKAGE AUDIT: 0 collisions against all 1 355 parsed names and 235 ground-truth names, and
# no word matching any of the 41 module stems. An earlier draft said "transfer engine" and
# was rejected -- `engine` is a real record base in neorv32_twi and one of the top false
# positive sources, so quoting it would have pointed at the answer.

_S1_ANCHOR = '- Ground "Functionality" (what the element does/carries)'

_S1_RULE = ("- A structure that STORES or CARRIES data is not an asset merely because data "
            "passes through it. A buffer, a staging or shift register, the working storage "
            "of a protocol block -- each is an asset only when what it holds is itself an "
            "asset: a secret, a credential, entropy, or privileged configuration. When the "
            "content is ordinary traffic the module exists to move, the structure and its "
            "fields are INFLUENCING elements that a later stage handles, and the asset is "
            "the content itself, named where the design produces or holds it. Test each "
            "candidate by asking what an attacker gains from reading or altering it; if the "
            "answer is only whatever happened to be in transit at that moment, it is not an "
            "asset.\n")


def _apply_s1(core: str, label: str = "S1") -> str:
    """Insert the container-vs-content rule as its own RULES bullet. Round-trips or fails."""
    n = core.count(_S1_ANCHOR)
    assert n == 1, f"{label}: anchor matches {n} times, expected 1"
    out = core.replace(_S1_ANCHOR, _S1_RULE + _S1_ANCHOR)
    assert out.replace(_S1_RULE, "") == core, f"{label}: changed something outside the insertion"
    assert out != core, f"{label}: no-op"
    # the rule must not smuggle in a real identifier
    for b in EVAL_SET_IDENTIFIERS + EXTERNAL_IDENTIFIERS:
        assert b not in _S1_RULE, f"{label}: {b!r} present in the inserted rule"
    # everything the baseline established must survive untouched
    for kept in ("Record-typed PORTS are named WHOLE", "CLOSE EACH CONCEPT",
                 "pure boilerplate are NOT assets", "Never emit a name you have not read"):
        assert kept in out, f"{label}: {kept!r} was lost"
    return out


ASSET_V2_S1 = _apply_s1(ASSET_V2_BASE)


# ============ R-8 · Revert the A-08 per-concept closure sweep ============
# THE ONLY ARM SO FAR THAT REMOVES RATHER THAN ADDS, and that property is the point: nothing
# about NEORV32 can leak through a deletion, so this arm carries zero overtuning risk by
# construction. Every other candidate adds a criterion that has to be judged for
# generalisability; this one cannot.
#
# WHAT IS BEING REMOVED. v1 arm A-08 inserted a verification pass telling the model to
# re-read the closed set against each conceptual asset and "Add every one that does", closing
# with "not when its elements stop coming readily" -- an explicit instruction that stopping
# early is wrong.
#
# MEASURED EFFECT WHEN IT WAS ADDED (v1, v01c5 -> v01c6, one edit):
#     emissions 331.2 -> 428.0   (+96.8 per repeat, the largest single-edit jump in the study)
#     precision     0.285 -> 0.229  (-0.056)
#     recall        0.849 -> 0.881  (+0.032)
#     union ceiling 0.928 -> 0.955  (the only arm ever to move it)
# Under a recall objective that was a good trade. Under a precision objective it inverts.
#
# WHY NOW RATHER THAN LATER. S-1 was a restrictive rule and came back null on precision
# (-0.009 [-0.023, +0.006]) while emissions ROSE 412.7 -> 425.0 and elements-per-concept rose
# 4.49 -> 4.69. Concepts per module stayed flat, so the model did not conceive more -- it
# bound more to each concept, in the run where it had just been told to bind less. HYPOTHESIS,
# not yet verified: the closure sweep is cancelling restrictive additions. This arm is the
# direct test, and it is the cheapest one available.
#
# AFFORDABLE NOW AND NOT BEFORE. Baseline v2 recall is 0.925, the highest in the study, so the
# guard floor is 0.895. A symmetric revert of A-08's +0.032 lands near 0.893 -- inside the
# indeterminate band, requiring n=5 before promotion. Registered in advance so the outcome is
# not adjudicated by eye.
#
# REGISTERED COST: A-08 is the only arm that ever moved the union ceiling. Reverting it
# probably gives that back. Accepted under a precision objective.

_R8_BLOCK = (
    "\n\nSTEP 2 (continued) -- CLOSE EACH CONCEPT. Before leaving a conceptual asset, make "
    "one more pass over the closed set for that asset alone, and ask of each element: does "
    "this element also produce, store, transport or gate this same conceptual asset? Add "
    "every one that does.\n\nDo this per conceptual asset, after its elements are listed. It "
    "is a check on a list you have already written, not a repeat of the search that wrote "
    "it. A conceptual asset is finished when the closed set has been read against it -- not "
    "when its elements stop coming readily.")


def _apply_revert_a08(core: str, label: str = "R8") -> str:
    """Delete the closure sweep and nothing else. Round-trips, or fails loudly."""
    n = core.count(_R8_BLOCK)
    assert n == 1, f"{label}: sweep block matches {n} times, expected 1"
    out = core.replace(_R8_BLOCK, "")
    # round trip: putting it back must reproduce the input byte for byte
    assert out[:core.index(_R8_BLOCK)] + _R8_BLOCK + out[core.index(_R8_BLOCK):] == core, \
        f"{label}: removal is not a clean excision"
    assert len(core) - len(out) == len(_R8_BLOCK), f"{label}: removed more than the block"
    # the sweep must be gone
    for gone in ("CLOSE EACH CONCEPT", "Add every one that does",
                 "not when its elements stop coming readily"):
        assert gone not in out, f"{label}: {gone!r} survived"
    # NOTHING ELSE may move. These are the other arms' texts and the baseline's corrections.
    for kept in ("Record-typed PORTS are named WHOLE", "ROLE, NOT LOCATION",
                 "may fan out to SEVERAL elements", "pure boilerplate are NOT assets",
                 "Never emit a name you have not read in the RTL above",
                 "structural assets are internal address signals",
                 "ConceptualAssets", "exact declared name"):
        assert kept in out, f"{label}: {kept!r} was lost -- this arm removes ONE block only"
    return out


ASSET_V2_R8 = _apply_revert_a08(ASSET_V2_BASE)


# ============ S-3 · Routed traffic belongs to the fabric, not the stop ============
# THE STRONGEST ARM IN THE QUEUE ON MEASURED EVIDENCE, and the first whose mechanism is
# SELECTIVE rather than volumetric. Every precision gain in v2 so far came from turning one
# class-blind dial (elements per concept), which removes true and false positives together.
# This one is defined by what an element IS, not by how many of them to emit.
#
# HEADROOM, measured on v2's own output, 15 modules x 3 repeats, using the structural
# definition rather than a name list (the v1 lesson: a hand-written six-name regex undercounted
# this same arm 25.0 -> 76.0 FP/repeat):
#
#   elements whose DECLARED TYPE is the design's shared interconnect record
#       FP removed     76.0 / repeat   (25% of all false positives)
#       TP removed      0.0 / repeat
#       precision   0.249 -> 0.305     (+0.056)
#       recall      0.925 -> 0.925     (unchanged, by construction)
#
# WHY ZERO TP LOSS EVEN IN THE INTERCONNECT MODULE. The switch/gateway module declares 91
# elements of the shared request/response record types. Not one of them is a reference asset.
# The reference names that module's arbitration and qualification signals instead -- plain
# scalar internal signals, the DECISIONS it makes about traffic. The annotation already draws
# exactly the line this rule states, in the module where the rule bites hardest (45.3 of the
# 76.0 FP/repeat are there).
#
# THE SAFETY CONTRAST, ALSO MEASURED. Applying the identical structural test to the CONTROL
# record type instead of the interconnect type:
#       FP removed 24.3/rep, TP removed 16.7/rep, precision -0.017, recall 0.925 -> 0.775
# So the rule is only sound when scoped to traffic the module FORWARDS. The record a module
# ACTS ON is an asset. That contrast is why this is a criterion and not a blocklist.
#
# WHY THE CARVE-OUT IS SAFE HERE AND WAS NOT IN S-1. S-1 failed because its exception was keyed
# on SECURITY RELEVANCE ("a secret, a credential, entropy, or privileged configuration"), so in
# the module that is entirely about entropy the exception fired universally and the restrictive
# rule became a licence. This arm's exceptions are keyed on STRUCTURAL facts checkable in the
# RTL -- does the traffic change representation here, does it leave the design here -- and both
# are FALSE in the modules that carry the headroom.
#
# THE CARVE-OUT ALSO PROTECTS EXACTLY WHAT X-3R-8 DESTROYED. That arm's damage was concentrated
# in the port class (recall -0.120, CI [-0.202,-0.043]) and the newly missed elements were
# device-facing and off-chip lines. Those are precisely what the second exception preserves.
#
# GENERALISATION, CHECKED AGAINST THE OTHER 26 ANNOTATED MODULES. A protocol bridge lists its
# foreign-side signals as assets (9 reference assets, 8 of them the external bus), and a
# streaming link lists its external stream ports (13 assets). Neither uses the internal shared
# record type, so a TYPE-scoped rule never reaches them -- but a rule phrased in prose as "bus
# interface signals are not assets" WOULD reach them and would gut both. Hence the wording
# below turns on origination, transformation and design boundary, never on what an interface
# is called.
#
# BUILT ON ASSET_V2_BASE, NOT ASSET_V2_R8. Stacking this on the R-8 core would confound a
# selective criterion with a fan-out reduction -- the exact confound that made X-3R-8
# uninterpretable as a precision result.

_S3_RULE = (
    '- ROUTED TRAFFIC BELONGS TO THE FABRIC, NOT TO EVERY STOP ALONG IT. Decide, for each '
    'interface this module has, whether the module ORIGINATES the traffic on it, CONSUMES it, '
    'or merely CARRIES it. A record, struct or interface-typed element that this module '
    'neither originates nor consumes -- one it receives and passes on in the same form, and '
    'whose type comes from a shared package rather than being declared in this module -- is '
    'NOT an asset here, and neither are its fields. It is an asset of whichever block\'s '
    'function is to be that fabric. What THIS module contributes is the DECISION it makes '
    'about that traffic: which target is selected, whether a transfer is qualified, granted '
    'or refused, when it completes, stalls or is aborted. Name those decision elements '
    'instead; they are usually ordinary internal signals, not the record. TWO EXCEPTIONS, '
    'both structural and both mandatory. (1) If the traffic CHANGES REPRESENTATION here -- '
    'this module is the bridge or adapter, and the outgoing form is its own construction -- '
    'the signals carrying the converted traffic are this module\'s own interface and ARE '
    'assets. (2) If the traffic LEAVES THE DESIGN here, on a device-facing, off-chip or '
    'externally visible port, that port IS an asset. Apply this test only to traffic the '
    'module forwards; a record the module READS AND ACTS ON -- configuration it decodes, '
    'state it maintains -- is unaffected by this rule and its fields remain assets.\n')


def _apply_s3(core: str, label: str = "S3") -> str:
    """Insert the routed-traffic rule as its own RULES bullet. Round-trips or fails."""
    n = core.count(_S1_ANCHOR)
    assert n == 1, f"{label}: anchor matches {n} times, expected 1"
    out = core.replace(_S1_ANCHOR, _S3_RULE + _S1_ANCHOR)
    assert out.replace(_S3_RULE, "") == core, f"{label}: changed something outside the insertion"
    assert out != core, f"{label}: no-op"
    # No identifier may enter, real or illustrative. This rule is deliberately written with
    # ZERO example names -- there is nothing for the model to copy into an answer.
    for b in EVAL_SET_IDENTIFIERS + EXTERNAL_IDENTIFIERS:
        assert b not in _S3_RULE, f"{label}: {b!r} present in the inserted rule"
    assert '"' not in _S3_RULE, f"{label}: quoted identifier introduced into the rule"
    # It must be a CRITERION, not a procedure. A procedure edit moves emission volume hard
    # (v1: +62.7/+77.8/+96.8); that is the fan-out dial this arm exists to avoid.
    for banned in ("STEP ", "make one more pass", "Add every one", "for each element in the"):
        assert banned not in _S3_RULE, f"{label}: {banned!r} makes this a procedure edit"
    # everything the baseline established must survive untouched
    for kept in ("Record-typed PORTS are named WHOLE", "CLOSE EACH CONCEPT",
                 "pure boilerplate are NOT assets", "Never emit a name you have not read",
                 "ConceptualAssets", "exact declared name"):
        assert kept in out, f"{label}: {kept!r} was lost"
    return out


ASSET_V2_S3 = _apply_s3(ASSET_V2_BASE)


# ============ SEC · Line-6 expansion: demote influencers to a secondary list ============
# FIRST ARM TO TOUCH ALGORITHM 1 LINE 6. Every previous arm tried to make line 5 emit less.
# This one gives the model somewhere else to PUT an element, which is a different mechanism.
#
# HEADROOM, measured against LAsset's own published primary/secondary lists on our 15
# modules. The discriminator is NOT "does this element appear as a secondary" -- that fires
# on 49.8% of our false positives and 56.2% of our true positives, because 77 of 137 LAsset
# primary elements are ALSO secondary somewhere. Secondary is a ROLE, not a class. The
# discriminator that works is "only ever an influencer, never independently a primary":
#
#   category            our FP/rep   our TP/rep   FP:TP
#   secondary-ONLY          133.3        4.0      33 : 1     <- this arm's target
#   both roles               21.0       53.7       0.39
#   primary-only              9.0       42.3       0.21
#   in neither list         146.7        2.7      55 : 1     <- NOT addressed by this arm
#
#   oracle demotion of the secondary-ONLY population:
#       emit 412.7 -> 275.3   precision 0.249 -> 0.358 (+0.110)   recall 0.925 -> 0.889
#
# +0.110 is the largest single lever measured in the study, double S-3's. Three caveats are
# registered with it: the oracle uses LAsset's OWN secondary lists, so it assumes the model's
# notion matches theirs and is an upper bound; recall -0.036 lands INSIDE the indeterminate
# band, so this arm sits on the guard by design; and it addresses 43% of false positives, not
# the 47% that LAsset never named in any role.
#
# THE PREDICTED FAILURE MODE, from our own four-for-four record. Every time this model is
# handed a population to name, it names from it: S-1's carve-out became a licence, S-3's
# redirect became a licence, the parsed block became a menu, and both restrictive criteria
# RAISED emissions. The hypothesis here requires elements to MOVE from primary to secondary.
# The likelier failure is that the primary list stays put and a secondary list is simply
# ADDED. That is the arm's primary mechanism check, not a footnote.
#
# WHAT IS TAKEN FROM SAIF AND WHAT IS NOT. Taken: the definition of primary vs secondary
# assets, and the two worked examples (shared bus + decoder secondary to a master's data; a
# boot-vs-normal FSM state secondary to a crypto key). Both are IP-agnostic and name nothing
# from NEORV32. NOT taken: SAIF's three algorithms. Algorithm 1 needs fan-out/fan-in traversal
# with sequential-depth extraction; Algorithm 2 needs stuck-at fault insertion, stimulus
# application and an Observation-Hardness threshold, i.e. fault simulation; Step 3 needs
# formal information-flow verification and side-channel metrics. None is executable by a model
# reading RTL text, and prose that gestured at them would be an instruction the model performs
# superficially and over-applies -- which is exactly how S-3's redirect failed.
#
# SCORING IS UNCHANGED. The scorer reads the "Assets" array only; there is no secondary
# ground truth, so secondary emissions are recorded and never scored. The hypothesis predicts
# the PRIMARY list shrinks.

_SEC_ANCHOR = "\n\nRULES:"

_SEC_STEP = (
    "\n\nSTEP 3 -- SECONDARY ASSETS, AND THE DEMOTION TEST. Every element you listed in "
    "STEP 2 is either a primary asset in its own right or a secondary asset of one. Decide "
    "which, for each.\n\n"
    "A PRIMARY asset is an object the design must protect as a definitive target in itself: "
    "the data, the configuration or the state whose compromise IS the security violation.\n\n"
    "A SECONDARY asset is infrastructure that closely interacts with a primary asset and "
    "therefore needs protection to keep that primary asset secure while it rests or moves. "
    "It may be tangible -- a signal, a register, a block -- or intangible, such as the "
    "controllability of a block or the state of a control FSM. An attacker exploits it to "
    "reach the primary asset; it is not the target itself.\n\n"
    "Two worked cases from the security literature, neither drawn from the module you are "
    "given:\n"
    " - Masters and slaves share a bus, and a decoder selects which slave is addressed. The "
    "sensitive data a master transmits is the PRIMARY asset. The bus and the decoder are "
    "SECONDARY: they carry and steer that data, and protecting them is how it stays "
    "confined to the intended target.\n"
    " - A cryptographic block holds a key that no other block may read during boot. The key "
    "is the PRIMARY asset. The execution state that distinguishes boot from normal operation "
    "is SECONDARY: it is what restricts access, so subverting it exposes the key.\n\n"
    "THE DEMOTION TEST. For each element from STEP 2 ask: does this element have protection "
    "value of its own, or does it matter ONLY because it carries, gates, steers, times or "
    "exposes something else? If the security story you would have to write for it needs a "
    "SECOND element named to make any sense, it is that element's secondary asset.\n\n"
    "This step REMOVES elements from the primary list. It is a reassignment, not an "
    "addition: an element you place in a secondary array must NOT also remain a primary "
    "entry. One element may be secondary to several primary assets -- list it under each.\n\n"
    "Keep an element PRIMARY when its own compromise is itself the violation, that is, when "
    "the security story needs no second element to make sense. Configuration a module "
    "decodes and acts upon, and data crossing the boundary of the design, are targets in "
    "their own right even though they also travel.")

_SEC_CONTRACT_OLD = (
    '    "Justification": "<why its compromise violates the objective>"}\n'
    ' ]}')
_SEC_CONTRACT_NEW = (
    '    "Justification": "<why its compromise violates the objective>",\n'
    '    "secondary": ["<exact declared names of the elements that are THIS asset\'s '
    'secondary assets; [] if none>"]}\n'
    ' ]}')


def _apply_sec(core: str, label: str = "SEC") -> str:
    """Add STEP 3 and the per-asset secondary array. Round-trips, or fails loudly."""
    n = core.count(_SEC_ANCHOR)
    assert n == 1, f"{label}: RULES anchor matches {n} times, expected 1"
    out = core.replace(_SEC_ANCHOR, _SEC_STEP + _SEC_ANCHOR)
    m = out.count(_SEC_CONTRACT_OLD)
    assert m == 1, f"{label}: contract anchor matches {m} times, expected 1"
    out = out.replace(_SEC_CONTRACT_OLD, _SEC_CONTRACT_NEW)
    # round trip: undoing both edits must reproduce the input byte for byte
    back = out.replace(_SEC_CONTRACT_NEW, _SEC_CONTRACT_OLD).replace(_SEC_STEP, "")
    assert back == core, f"{label}: changed something outside the two insertions"
    # no identifier may enter, real or illustrative
    for b in EVAL_SET_IDENTIFIERS + EXTERNAL_IDENTIFIERS:
        assert b not in _SEC_STEP, f"{label}: {b!r} present in the inserted step"
    # SAIF's algorithms are deliberately NOT ported -- they need structural traversal,
    # fault simulation and formal IFA. Assert we did not smuggle in prose that pretends to.
    for cargo in ("fan-out", "fan-in", "sequential depth", "stuck-at", "observation hardness",
                  "taint", "side-channel", "simulate"):
        assert cargo not in _SEC_STEP.lower(), \
            f"{label}: {cargo!r} implies an analysis the model cannot actually perform"
    # the demotion must be stated as a MOVE, or the arm tests nothing
    for req in ("REMOVES elements", "not an addition", "must NOT also remain"):
        assert req in _SEC_STEP, f"{label}: the reassignment requirement {req!r} is missing"
    # everything the baseline established must survive untouched
    for kept in ("Record-typed PORTS are named WHOLE", "CLOSE EACH CONCEPT",
                 "pure boilerplate are NOT assets", "Never emit a name you have not read",
                 "ConceptualAssets", "exact declared name", "STEP 2 -- STRUCTURAL"):
        assert kept in out, f"{label}: {kept!r} was lost"
    return out


ASSET_V2_SEC = _apply_sec(ASSET_V2_BASE)


# ============ RP · Restore the parsed closed set, now carrying functional roles ============
# THE FIRST ARM TO CHANGE THE INPUT REGIME RATHER THAN THE PROMPT. It undoes correction D
# and hands line 5 the parsed ports/signals again -- but annotated by the line-4 parser in
# `prompts_parse_v2`, so each element arrives with `roles`, `relationship` and `evidence`
# alongside the `function` string v1 had.
#
# WHAT IT IS FOR. Recall in this pipeline is currently bought with prompt text that raises
# emission: A-08's per-concept closure sweep took v1 emissions 331.2 -> 428.0 while
# precision fell 0.285 -> 0.229. If the parsed list supplies the coverage instead, that
# text becomes removable and the precision it costs is recoverable. So the reading of this
# arm is deliberately NOT "did precision go up":
#
#   recall and emission ~flat  -> the roles carry the coverage the prompt text was buying.
#                                 R-8 and the other emission-raising blocks become
#                                 candidates for removal, one at a time, on top of this.
#   recall UP, emission UP     -> the roles are a second generator, not a substitute. The
#                                 arm has added a dial, not replaced one.
#   recall DOWN               -> the parsed list is displacing RTL reading rather than
#                                 supporting it; the closed set is not the bottleneck.
#
# PRIOR, REGISTERED BEFORE RUNNING. v1's P-2 removed the parsed blocks and was NULL on every
# paired delta (P 0.210 -> 0.243, recall 0.897 -> 0.886, ABLATION_LOG.md §P-2). That was a
# name+function list. This arm's claim is that the ANNOTATION, not the name list, is what
# would have mattered -- so a null here is a real and informative result, not a failed arm:
# it would say the closed set is not where line 5's recall comes from, in either direction.
#
# TWO KNOWN ASYMMETRIES, both accepted deliberately, both recorded so they are not later
# mistaken for findings:
#
#  1. THE ICL EXAMPLES DO NOT DEMONSTRATE THE BLOCKS. v2's ICL is the P-2 block, which has
#     both `=== PARSED ... (JSON) ===` spans removed. So the worked examples reason from
#     RTL alone while the live message carries a parsed list. The notebook's _BLOCK_MARKERS
#     drift assertion does NOT fire on this: it only checks the direction where a block is
#     dropped from the message while the prompt still declares it. This is the reverse, and
#     it is the arm's chief risk -- the model may under-use a block no example ever uses.
#     Holding the ICL fixed is what keeps this one proposition; pairing it with a
#     parsed-carrying ICL would be two changes at once, which is what made X-3R-8
#     uninterpretable.
#  2. 58.1% OF THE CLOSED SET IS A DOTTED PORT FIELD, and A-03's rule ("Record-typed PORTS
#     are named WHOLE") forbids emitting any of them. Measured over the 15 scored modules:
#     914 of 1572 elements, holding 0 of the 30 dotted ground-truth assets -- all 30 are
#     fields of internal SIGNAL records. So most of the restored list is a menu of names the
#     rule already rejects. This is not new: v1's v01c6p1 ran exactly this combination and
#     sat at 0 ungrounded names across 90 module-repeats. It is stated here because a
#     precision fall in this arm has that as its first candidate explanation.
#
# THE LOAD-BEARING EDIT IS THE THIRD ONE. Restoring the blocks without it would hand the
# model a column of labels like SECRET_DATA_STORAGE and ACCESS_CONTROL with no statement of
# what they are, and the natural reading of a positive-sounding role is "emit this" -- which
# would move STEP 1's C/I/A decision into the parser and make the arm measure label transfer
# rather than anything about the closed set. The bullet says the annotations are evidence,
# never the decision, in both directions: a positive role does not qualify an element and a
# negative one does not disqualify it.
# =============================================================================

# Reversal of correction D. The wording restored here is `prompts._P2_INPUTS_OLD` and
# `prompts._P2_EDITS` verbatim EXCEPT for the field list, which gains the three new keys --
# so v1's parsed-input versions and this arm say the same thing about everything that has
# not changed.
_RP_INPUTS_OLD = (
    'INPUTS (in the user message):\n(4) RTL -- the module source, and ground truth for '
    'what each element does. Its entity/port declarations and its architecture signal '
    'declarations TOGETHER are the CLOSED SET of design elements; read them off the '
    'source yourself. Every asset MUST bind to exactly one element declared there, by '
    'its exact declared name. Ports AND internal signals/registers are equally eligible. '
    'Never invent, rename, split, or merge a name; copy record-field names verbatim '
    'including the dot (e.g. "blk_ctrl.step", "xfer_unit.stage").')
_RP_INPUTS_NEW = (
    'INPUTS (in the user message):\n(2) PARSED I/O PORTS and (3) PARSED INTERNAL SIGNALS '
    '-- each is a JSON object with fields including entity, name, direction(dir), type, '
    'function, roles, relationship, evidence (signals also have kind). TOGETHER they are '
    'the CLOSED SET of design elements. Every asset MUST bind to exactly one element from '
    'this set by its exact "name". Ports AND internal signals/registers are equally '
    'eligible. Never invent, rename, split, or merge a name; copy record-field names '
    'verbatim including the dot (e.g. "blk_ctrl.step", "xfer_unit.stage").\n'
    '(4) RTL -- ground truth for what each element does.')

# The annotation-status bullet. Placed immediately before the grounding rule, which is the
# one that tells the model where "Functionality" and "Justification" may come from -- so
# the two rules about what the inputs are worth sit together.
_RP_STATUS_ANCHOR = '- Ground "Functionality" (what the element does/carries)'
_RP_STATUS_RULE = (
    '- The "roles", "relationship" and "evidence" fields are FUNCTIONAL annotations '
    'produced by an earlier stage: they record what an element DOES, not what it is worth. '
    'They are not verdicts and they are not ranked. A role that sounds security-related '
    'does not make an element an asset, and a role beginning ORDINARY_ or GENERIC_ does '
    'not stop one being an asset -- the earlier stage assigns those from local behaviour '
    'and cannot see the module\'s use cases. Read them as evidence alongside the RTL, and '
    'let STEP 1 and STEP 2 reach their own conclusion. Where an annotation and the RTL '
    'disagree, the RTL wins.\n')

_RP_EDITS = (
    (_RP_INPUTS_OLD, _RP_INPUTS_NEW),
    ('- "Asset RTL" MUST be the exact declared name of one element from the module\'s '
     'ports/signals.',
     '- "Asset RTL" MUST be the exact "name" of one element from the provided '
     'ports/signals.'),
    ('- "Entity" MUST be the RTL entity/module that declares the element, copied verbatim.',
     '- "Entity" MUST be copied verbatim from that element\'s "entity" field.'),
    (_RP_STATUS_ANCHOR, _RP_STATUS_RULE + _RP_STATUS_ANCHOR),
)


def _apply_rp(core: str, label: str = "RP") -> str:
    """Re-source the closed set from the parsed blocks and declare what the annotations
    are worth. Round-trips, or fails loudly."""
    out = core
    for old, new in _RP_EDITS:
        n = core.count(old)
        assert n == 1, f"{label}: anchor matches {n} times, expected 1 -- {old[:60]!r}"
        out = out.replace(old, new)
    back = out
    for old, new in reversed(_RP_EDITS):
        back = back.replace(new, old)
    assert back == core, f"{label}: changed something outside the four edits"
    assert out != core, f"{label}: no-op"

    # The notebook's _BLOCK_MARKERS reads these two literals to police input/prompt drift.
    # If either stops matching, a future version that drops a block would pass the drift
    # assertion while still declaring the block -- the confound that nearly wrecked P-1.
    for marker in ("PARSED I/O PORTS", "type, function"):
        assert marker in out, f"{label}: _BLOCK_MARKERS literal {marker!r} absent"

    # The annotations must be declared non-authoritative, in BOTH directions. A bullet that
    # only warned about positive roles would leave the negative ones as a silent veto, and
    # this arm would measure the parser's suppression rather than the asset stage's judgement.
    for req in ("are not verdicts", "does not make an element an asset",
                "does not stop one being an asset", "the RTL wins"):
        assert req in out, f"{label}: the annotation-status rule is missing {req!r}"

    # No identifier may enter, real or illustrative beyond what the baseline already quotes.
    for b in EVAL_SET_IDENTIFIERS + EXTERNAL_IDENTIFIERS:
        assert b not in _RP_INPUTS_NEW and b not in _RP_STATUS_RULE, \
            f"{label}: {b!r} present in the inserted text"

    # Everything the baseline established must survive untouched. A-03's granularity rule
    # matters most here: the restored list contains the dotted port fields it forbids.
    for kept in ("Record-typed PORTS are named WHOLE", "CLOSE EACH CONCEPT",
                 "pure boilerplate are NOT assets", "Never emit a name you have not read",
                 "ConceptualAssets", "STEP 2 -- STRUCTURAL", "ROLE, NOT LOCATION"):
        assert kept in out, f"{label}: {kept!r} was lost"
    return out


ASSET_V2_RP = _apply_rp(ASSET_V2_BASE)


# ============ P3 · The v3 parse — occurrence-driven, open-vocabulary annotation ============
# SAME INPUT REGIME AS RP, DIFFERENT ANNOTATION. RP receives `roles` drawn from a 152-label
# closed taxonomy. P3 receives `functionality`, `role`, `relationship` and `evidence`
# produced by `prompts_parse_v3`, where `role` is open prose derived from an occurrence
# profile and no vocabulary is supplied to the annotator at all.
#
# WHY THIS IS A SEPARATE ARM AND NOT AN EDIT TO RP. `assets_tuning18_v2rp_r0..r2` exist and
# their `_run_meta.json` records the composed sha of ASSET_V2_RP. Editing that string would
# leave three paid runs attributed to code that no longer exists — the failure §6 of the v1
# log exists to prevent. Keeping both also buys the comparison for nothing: RP and P3 differ
# in exactly one thing, the vocabulary the parser was given, so the pair answers whether a
# closed enum or open prose transfers more of the parse to the asset stage.
#
# THE STATUS RULE IS DIFFERENT FROM RP'S, AND THE DIFFERENCE MATTERS. RP's rule had to say
# that an `ORDINARY_`/`GENERIC_` role does not disqualify an element, because that arm's
# parser emitted an explicit negative label. The v3 parser emits no security vocabulary in
# either direction — every annotation is neutral by construction, because the stage is
# forbidden to write otherwise. So the risk inverts: a model reading fifteen hundred bland
# functional descriptions can read the blandness itself as a verdict and under-emit. The
# rule below states plainly that the absence of security language carries no information,
# because the stage that wrote it was not permitted to use any.
# =============================================================================

_P3_INPUTS_NEW = (
    'INPUTS (in the user message):\n(2) PARSED I/O PORTS and (3) PARSED INTERNAL SIGNALS '
    '-- each is a JSON object with fields including entity, name, direction(dir), type, '
    'function, functionality, role, relationship, evidence (signals also have kind). '
    'TOGETHER they are the CLOSED SET of design elements. Every asset MUST bind to exactly '
    'one element from this set by its exact "name". Ports AND internal signals/registers '
    'are equally eligible. Never invent, rename, split, or merge a name; copy record-field '
    'names verbatim including the dot (e.g. "blk_ctrl.step", "xfer_unit.stage").\n'
    '(4) RTL -- ground truth for what each element does.')

_P3_STATUS_RULE = (
    '- The "functionality", "role", "relationship" and "evidence" fields are FUNCTIONAL '
    'annotations produced by an earlier stage that reads the RTL element by element. They '
    'record what each element DOES: what it holds or carries, what it governs, what it '
    'chooses between, whether it crosses the module boundary, and what can change it from '
    'outside. Use them as evidence.\n'
    '- That earlier stage was FORBIDDEN to write about security. It may not name an '
    'objective, may not call anything sensitive or protected, and may not say whether an '
    'element matters. So the neutral tone of every annotation carries NO information: an '
    'element described in plain functional terms is not thereby ordinary, and nothing in '
    'this input marks an element as unimportant. Judge each element by what the annotation '
    'says it does, exactly as you would judge it from the RTL. Where an annotation and the '
    'RTL disagree, the RTL wins.\n')

_P3_EDITS = (
    (_RP_INPUTS_OLD, _P3_INPUTS_NEW),
    ('- "Asset RTL" MUST be the exact declared name of one element from the module\'s '
     'ports/signals.',
     '- "Asset RTL" MUST be the exact "name" of one element from the provided '
     'ports/signals.'),
    ('- "Entity" MUST be the RTL entity/module that declares the element, copied verbatim.',
     '- "Entity" MUST be copied verbatim from that element\'s "entity" field.'),
    (_RP_STATUS_ANCHOR, _P3_STATUS_RULE + _RP_STATUS_ANCHOR),
)


def _apply_p3(core: str, label: str = "P3") -> str:
    """Restore the parsed blocks and declare what a v3 annotation is worth. Round-trips."""
    out = core
    for old, new in _P3_EDITS:
        n = core.count(old)
        assert n == 1, f"{label}: anchor matches {n} times, expected 1 -- {old[:60]!r}"
        out = out.replace(old, new)
    back = out
    for old, new in reversed(_P3_EDITS):
        back = back.replace(new, old)
    assert back == core, f"{label}: changed something outside the four edits"
    assert out != core, f"{label}: no-op"

    # the notebook's _BLOCK_MARKERS literals must survive, or a future block-drop arm
    # passes its drift assertion while still declaring the block
    for marker in ("PARSED I/O PORTS", "type, function"):
        assert marker in out, f"{label}: _BLOCK_MARKERS literal {marker!r} absent"

    # the two halves of the status rule, both load-bearing
    for req in ("record what each element DOES", "FORBIDDEN to write about security",
                "carries NO information", "the RTL wins"):
        assert req in out, f"{label}: the status rule is missing {req!r}"

    # this arm must NOT inherit RP's enum-specific wording -- there is no enum here
    for gone in ("ORDINARY_", "GENERIC_", '"roles"'):
        assert gone not in _P3_STATUS_RULE, f"{label}: {gone!r} is enum wording, not v3"

    for b in EVAL_SET_IDENTIFIERS + EXTERNAL_IDENTIFIERS:
        assert b not in _P3_INPUTS_NEW and b not in _P3_STATUS_RULE, \
            f"{label}: {b!r} present in the inserted text"

    for kept in ("Record-typed PORTS are named WHOLE", "CLOSE EACH CONCEPT",
                 "pure boilerplate are NOT assets", "Never emit a name you have not read",
                 "ConceptualAssets", "STEP 2 -- STRUCTURAL", "ROLE, NOT LOCATION"):
        assert kept in out, f"{label}: {kept!r} was lost"
    return out


ASSET_V2_P3 = _apply_p3(ASSET_V2_BASE)

# RP and P3 must remain distinct strings, or the comparison the pair exists for is vacuous.
assert ASSET_V2_P3 != ASSET_V2_RP, "P3 and RP composed to the same core"


# ============ C1 · Teach the asset stage how to READ the annotations ============
# ONE ADDITION TO P3, AND NOTHING ELSE MOVES. P3 tells the model what the four annotation
# fields ARE and what they are not. It does not say how to use them, so the model is left to
# improvise a reading of a structured input it has never seen before. C1 supplies the
# reading procedure.
#
# WHY THIS IS NOT LEAKAGE, AND HOW THAT WAS KEPT TRUE. The obvious way to write this block
# is to state which annotation patterns tend to mark assets. Measured against this project's
# own ground truth, two do -- but putting either in the prompt would be transcribing the
# answer key, and §4's standing rule already forbids numeric hints for the same reason. What
# goes in instead is the MECHANISM each field reports and which of STEP 1's four questions
# that mechanism bears on. The model still has to decide, from the module's use cases, both
# what needs protecting and whether this element is where it lives.
#
# THE ANTI-OVER-EMISSION LEVER IS "A COUPLING IS NOT A REASON". Every element in a working
# design is coupled to something; most carry several edges. Handed a list of 1 689 elements
# each with three or four relationships, a model can read connectedness as significance and
# name most of the file -- which is exactly the failure this study is trying to remove. The
# block therefore says plainly that an edge reports mechanism and never supplies the reason,
# and that the Justification must still argue from the module's purpose.
#
# IT ADDS NO ASSET CRITERIA. The baseline's definition of a primary asset -- an element that
# stores, carries, generates or gates a conceptual asset -- is untouched. C1 changes how the
# input is read, not what qualifies, so a delta against P3 is attributable to the reading
# procedure alone.
# =============================================================================

_C1_ANCHOR = "METHOD:\nSTEP 1 -- CONCEPTUAL ASSETS"

_C1_BLOCK = """READING THE ANNOTATIONS

Each parsed element carries four fields written by an earlier stage that read the RTL \
element by element and was forbidden to write about security at all. Use them like this.

Read "evidence" FIRST. It names the construct the other three rest on -- an assignment, a \
branch condition, a port map. An annotation whose evidence names no construct is \
unsupported: disregard it and read the RTL yourself.

"functionality" says what the element does mechanically and what it acts on.

"role" names the parts the element plays in what its entity is for. The phrases were \
written to convey, where the RTL supported it: whether the element HOLDS a value across \
cycles or CARRIES one through; whether it GOVERNS whether another element updates; whether \
it CHOOSES among alternatives; whether it CROSSES the entity boundary, and in which \
direction; and whether anything OUTSIDE the entity can change it, and by what path.

"relationship" gives the couplings. Read the types in groups, because they answer different \
questions:
 - GATES, SELECTS, CONSTRAINS, OVERRIDES -- this element determines whether or how another \
element acts. That influence never appears in the element's own value, so following data \
alone will not find it. These edges tell you what changes if this element is wrong.
 - SOURCES, CAPTURES, CARRIES, DERIVES_FROM, AGGREGATES, SLICES -- value flow. Follow them \
to ask what the value IS. The edge says where a value goes, never whether it matters.
 - REFLECTS -- partial information about another value, without carrying it.
 - EXPORTS reaches the entity boundary; SEQUENCES supplies timing; ISOLATED means no \
coupling was substantiated in that entity.

WHAT EACH STEP 1 QUESTION CAN TAKE FROM THEM

(C) The annotations never say what is secret, and could not: the stage that wrote them \
could not see the module's use cases. Name the confidential concept yourself. Once named, \
the value-flow edges show which elements hold or carry it, and EXPORTS shows where it \
becomes observable outside the module.
(I) A governing edge, together with a role phrase saying something outside the entity can \
change the element, identifies an element whose modification changes behaviour it does not \
itself carry. That is the mechanism (I) asks about. Whether that behaviour is worth \
protecting is still yours to argue.
(A) SEQUENCES and the governing edges show what stops if this element stops or is held. An \
element that gates the module's product is a different case from one that gates an internal \
intermediate; the edges distinguish them, the objective does not.
(U) An edge into an element's state that does not pass through the module's normal path is \
a second route in, which is what (U) asks about.

WHAT YOU MUST NOT INFER FROM THEM

- A COUPLING IS NOT A REASON. Every element in a working design is coupled to something, \
and most carry several edges. A GATES edge no more makes an element an asset than a SOURCES \
edge does. The edge gives you the mechanism; the Justification must still say why \
compromising THIS element harms what the module is for.
- A rich annotation is not evidence of importance. Many edges means well connected. Well \
connected is not worth protecting.
- ISOLATED is a statement about one entity's source, not about the element.
- The annotation stage never saw the specification or the use cases, and you have both. \
Where an annotation and the RTL disagree, the RTL wins. Where an annotation is silent on \
something the use case makes plain, the use case wins.

"""


def _apply_c1(core: str, label: str = "C1") -> str:
    """Insert the reading procedure ahead of STEP 1. Round-trips, or fails loudly."""
    n = core.count(_C1_ANCHOR)
    assert n == 1, f"{label}: anchor matches {n} times, expected 1"
    out = core.replace(_C1_ANCHOR, _C1_BLOCK + _C1_ANCHOR)
    assert out.replace(_C1_BLOCK, "") == core, f"{label}: changed something outside the insertion"
    assert out != core, f"{label}: no-op"

    # It must teach READING, not qualifying. If any of these appear the arm has started
    # adding asset criteria and stops being one proposition.
    for banned in ("is an asset when", "treat as an asset", "always emit", "never emit an element",
                   "more likely", "usually an asset", "%"):
        assert banned not in _C1_BLOCK, f"{label}: {banned!r} turns this into an asset criterion"

    # the anti-over-emission lever and the two-way anti-inference must both survive
    for req in ("A COUPLING IS NOT A REASON", "never whether it matters",
                "not evidence of importance", "the use case wins"):
        assert req in out, f"{label}: {req!r} is missing"

    # every edge type the block names must be one the parser can actually emit, or the
    # instruction refers to something that never arrives
    for e in ("GATES", "SELECTS", "CONSTRAINS", "OVERRIDES", "SOURCES", "CAPTURES",
              "CARRIES", "DERIVES_FROM", "AGGREGATES", "SLICES", "REFLECTS", "EXPORTS",
              "SEQUENCES", "ISOLATED"):
        assert e in _C1_BLOCK, f"{label}: edge {e!r} not covered by the reading procedure"

    for b in EVAL_SET_IDENTIFIERS + EXTERNAL_IDENTIFIERS:
        assert b not in _C1_BLOCK, f"{label}: {b!r} present in the inserted block"

    # P3's own statement of what the fields are must survive -- C1 extends it, never replaces
    for kept in ("FORBIDDEN to write about security", "carries NO information",
                 "Record-typed PORTS are named WHOLE", "CLOSE EACH CONCEPT",
                 "ConceptualAssets", "STEP 2 -- STRUCTURAL", "PARSED I/O PORTS"):
        assert kept in out, f"{label}: {kept!r} was lost"
    return out


ASSET_V2_P3C1 = _apply_c1(ASSET_V2_P3)
assert ASSET_V2_P3C1 != ASSET_V2_P3, "C1 composed to P3"


# ------------------------------------------------------------------- audit ---

def sha(core: str, icl: str = "") -> str:
    """First 12 hex of the sha256 of the composed system prompt, matching the run loop."""
    text = core + ("\n\n" + icl if icl else "")
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def audit(core: str, label: str = "core") -> None:
    """The standing rule: no identifier from the 41 annotated modules may enter a prompt.

    Substring check against the known real names only. It is NOT a general audit -- a new
    example added by hand still needs scratchpad/identifier_audit.py run against the full
    parsed and ground-truth name lists.
    """
    hits = [b for b in EVAL_SET_IDENTIFIERS if b in core]
    assert not hits, f"{label}: evaluation-set identifier(s) present: {hits}"
    ext = [b for b in EXTERNAL_IDENTIFIERS if b in core]
    assert not ext, f"{label}: external real identifier(s) present: {ext}"


audit(ASSET_V2_BASE, "ASSET_V2_BASE")
audit(ASSET_V2_S1, "ASSET_V2_S1")
audit(ASSET_V2_R8, "ASSET_V2_R8")
audit(ASSET_V2_S3, "ASSET_V2_S3")
audit(ASSET_V2_SEC, "ASSET_V2_SEC")
audit(ASSET_V2_RP, "ASSET_V2_RP")
audit(ASSET_V2_P3, "ASSET_V2_P3")
audit(ASSET_V2_P3C1, "ASSET_V2_P3C1")

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
