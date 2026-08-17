"""V2 RTL-parser prompts -- Algorithm 1 line 4, with functional roles.

WHAT THIS IS. `prompts.PARSE_PORTS_ANNOTATE_SYSTEM` / `PARSE_SIGNALS_ANNOTATE_SYSTEM` ask
for one free-text `function` per element (<= 12 words). This module asks for the same
`function` PLUS a structured annotation drawn from a controlled vocabulary:

    roles         1-3 labels from ROLE_VOCAB (positive) or NEGATIVE_ROLES
    relationship  {verb, object} from RELATIONSHIPS, or null
    evidence      <= 15 words of RTL justification for the role

`prompts.py` IS NOT MODIFIED and the existing parse cache is not touched -- see
`parse_roles.py`, which writes a SEPARATE directory. Every historical run's closed set,
scorer input and `validate_primary` baseline stay byte-identical.

THE DIVISION THIS PROMPT MUST NOT CROSS. The parser says what an element DOES. LLMasset
decides what needs protecting and which element represents it. So this prompt:

  - never uses the words asset, primary, secondary, or any CIA objective in its
    INSTRUCTIONS (the vocabulary block is exempt -- two of the taxonomy's own section
    headings are named after objectives). `audit()` sweeps for all of them;
  - never ranks or scores an element;
  - forbids inferring a role from a name alone (rule 6 of the taxonomy's evidence rules);
  - REQUIRES a role on every element, so the negative vocabulary is live rather than
    decorative. See "WHY A ROLE IS MANDATORY" below.

The first bullet is why `roles[0]` is called the LEAD role and not the primary one: it
keeps "primary" a word that only ever means primary ASSET in this codebase, so the audit
can stay a plain substring sweep instead of a context-sensitive one.

WHY A ROLE IS MANDATORY, AND WHY ONLY ONE LEADS. The vocabulary is 152 positive
labels against 16 negative ones (90.5% positive; counted from the taxonomy file, and
asserted at import below). "Assign one or more roles" against a menu shaped like that
biases hard toward positives: nobody stacks two negative labels, but stacking three
positives is free. Two counter-measures, both structural rather than hortatory:

  1. Every element gets a role. An element with no supported positive role is not left
     blank -- it takes a negative label, which is a claim the annotator has to make.
  2. `roles[0]` is the LEAD role and the schema caps the list at 3. A cap turns
     "assign one or more" into a ranking problem instead of an accumulation problem.

This is the same failure mode the v1 log records twice: a free-standing checklist becomes
a generator (ABLATION_LOG.md line 275 -- `cpu` emitted `ctrl.*` eleven times), and a
numeric hint becomes a hard quota however it is hedged. Note where the risk lands here: the
VOCABULARY is shown to the PARSER only. LLMasset never sees the menu, only the assigned
labels, so the generator risk is confined to a stage that does not emit assets. What it can
still do is inflate LLMasset's input -- if the parser marks most of the closed set with a
positive role, the asset stage sees a design where everything looks security-relevant.
`parse_roles.role_report()` measures exactly that, and it is meant to be read BEFORE any
generation run is paid for.

TWO COLLISIONS IN THE SOURCE TAXONOMY, resolved here by first-occurrence:
  AUTHENTICATION_TAG  defined in E (integrity-bearing) and M (crypto data) -> kept in E
  LIFECYCLE_STATE     defined in D (FSM state) and G (reset/lifecycle)     -> kept in D
Both are single labels either way; keeping the duplicate would let the same element take
two spellings of one role and add run-to-run variance to an input every downstream number
depends on.

STANDING RULE, inherited from v1 sec.6 and enforced by `prompts_v2.audit`: no identifier
from any of the 41 annotated modules may enter a prompt. This stage feeds the asset stage,
so a leak here is a leak there. `prompts.PARSE_*_ANNOTATE_SYSTEM`'s user-message builder
quotes two real names (`ctrl.buf_req`, `host_req_i.stb`); the builder in `parse_roles.py`
does not, and `audit()` at the bottom of this module proves it for the system prompts.
"""
from __future__ import annotations

import hashlib

# =============================================================================
# The controlled vocabulary, generated from LAsset_RTL_Role_Taxonomy sec.2/3/4 rather than
# retyped. Section keys are the taxonomy's own, and are printed in the prompt so the
# annotator sees the same grouping the taxonomy defines.
# =============================================================================

ROLE_VOCAB = {
    "A. Protected data/state": [
        "SECRET_DATA_STORAGE", "SECURITY_SENSITIVE_CONFIGURATION_STORAGE",
        "IDENTITY_CREDENTIAL_STORAGE", "CRYPTOGRAPHIC_STATE_STORAGE",
        "SECURITY_PRIVILEGE_STATE", "TRUSTED_BOOT_STATE",
        "VERSION_ROLLBACK_STATE", "INTEGRITY_METADATA",
        "AUTHENTICATION_ATTESTATION_STATE", "SECURITY_SENSITIVE_RANDOMNESS",
    ],
    "B. Sensitive-data and security-state propagation": [
        "SENSITIVE_DATA_CARRIER", "SECRET_DERIVED_INTERMEDIATE", "SENSITIVE_DATA_INGRESS",
        "SENSITIVE_DATA_EGRESS", "SECURITY_STATE_PROPAGATION", "SECURITY_METADATA_PROPAGATION",
        "CROSS_MODULE_SENSITIVE_DATA_PATH", "SENSITIVE_DATA_SELECTION_GATING",
    ],
    "C. Security policy and access enforcement": [
        "ACCESS_CONTROL", "PRIVILEGE_ENFORCEMENT", "SECURITY_DOMAIN_ENFORCEMENT",
        "ISOLATION_CONTROL", "PERMISSION_CHECK", "SECURITY_POLICY_CONFIGURATION",
        "SECURITY_POLICY_SELECTOR", "RESOURCE_AUTHORIZATION", "TRANSACTION_ATTRIBUTION",
        "SECURITY_DECISION_OUTPUT",
    ],
    "D. Security-sensitive FSM/control state": [
        "SECURITY_PROTOCOL_STATE", "AUTHENTICATION_STATE", "AUTHORIZATION_STATE",
        "BOOT_SECURITY_STATE", "LIFECYCLE_STATE", "SECURE_TRANSITION_STATE",
        "LOCK_UNLOCK_STATE", "PROVISIONING_STATE", "RECOVERY_SECURITY_STATE",
        "SECURITY_ERROR_STATE", "PRIVILEGE_TRANSITION_STATE", "CRYPTOGRAPHIC_OPERATION_STATE",
        "SECURITY_SENSITIVE_FSM_CONTROL",
    ],
    "E. Integrity protection": [
        "HASH_VALUE", "MAC_VALUE", "AUTHENTICATION_TAG",
        "DIGITAL_SIGNATURE", "ECC_PARITY_METADATA", "CHECKSUM",
        "REDUNDANCY_METADATA", "EXPECTED_INTEGRITY_VALUE", "HASH_VERIFICATION",
        "MAC_VERIFICATION", "SIGNATURE_VERIFICATION", "ECC_PARITY_CHECK",
        "CONSISTENCY_CHECK", "REDUNDANT_STATE_COMPARISON", "TAMPER_DETECTION",
        "VERIFIED_STATUS", "AUTHENTICATION_SUCCESS_STATUS", "BOOT_VERIFICATION_STATUS",
        "TRUST_STATUS", "POST_VERIFICATION_LOCK_STATE", "ROLLBACK_PROTECTION_STATE",
    ],
    "F. Availability/security-resilience": [
        "SERVICE_AVAILABILITY_CONTROL", "RESOURCE_ALLOCATION_CONTROL", "RESOURCE_OWNERSHIP",
        "RESET_CONTROL", "CLOCK_AVAILABILITY_CONTROL", "RECOVERY_CONTROL",
        "WATCHDOG_CONTROL", "LIVENESS_PROGRESS_CONTROL", "DOS_SENSITIVE_RESOURCE_CONTROL",
        "FAULT_ISOLATION_CONTROL",
    ],
    "G. Reset and lifecycle": [
        "RESET_RELEASE_CONTROL", "RESET_SEQUENCING_CONTROL", "SECURE_RESET_CONTROL",
        "MANUFACTURING_PRODUCTION_MODE", "PROVISIONING_MODE", "SECURE_BOOT_ENABLE",
        "SECURITY_LOCK_STATE", "OTP_FUSE_SECURITY_STATE", "LIFECYCLE_TRANSITION_AUTHORIZATION",
    ],
    "H. Debug/test/maintenance": [
        "DEBUG_ACCESS_CONTROL", "JTAG_ACCESS_CONTROL", "SCAN_TEST_ENABLE",
        "TEST_MODE_CONTROL", "DEBUG_AUTHENTICATION", "DEBUG_UNLOCK",
        "TRACE_CONTROL", "PRIVILEGED_DEBUG_COMMAND", "MANUFACTURING_ACCESS",
        "TEST_BYPASS_OVERRIDE",
    ],
    "I. Memory/address protection": [
        "ADDRESS_RANGE_CHECK", "MEMORY_REGION_SELECTION", "MEMORY_PRIVILEGE_CHECK",
        "MEMORY_PERMISSION_CHECK", "SECURITY_DOMAIN_ATTRIBUTION", "MPU_PMP_CONFIGURATION",
        "SECURITY_PAGE_TABLE_ATTRIBUTE", "PROTECTION_REGION_CONFIGURATION",
        "SECURE_MEMORY_SELECTION", "ADDRESS_TRANSLATION_SECURITY_STATE", "ACCESS_FAULT_STATUS",
    ],
    "J. Interconnect/transaction security": [
        "TRANSACTION_SECURITY_ATTRIBUTE", "TRANSACTION_PRIVILEGE_ATTRIBUTE", "MASTER_IDENTITY",
        "REQUESTER_IDENTITY", "ADDRESS_PROTECTION_ATTRIBUTE", "REQUEST_AUTHORIZATION",
        "RESPONSE_AUTHORIZATION", "SECURE_DATA_ROUTING", "TRUST_BOUNDARY_CROSSING",
        "SECURITY_DOMAIN_CLASSIFICATION", "BUS_FIREWALL_CONTROL", "SECURITY_CRITICAL_ARBITRATION",
    ],
    "K. Security interrupts/events": [
        "SECURITY_INTERRUPT", "FAULT_INTERRUPT", "AUTHENTICATION_FAILURE_EVENT",
        "ACCESS_VIOLATION_EVENT", "TAMPER_EVENT", "WATCHDOG_SECURITY_EVENT",
        "SECURE_MONITOR_EVENT", "SECURITY_EXCEPTION", "SECURITY_INTERRUPT_MASKING",
        "SECURITY_INTERRUPT_ROUTING",
    ],
    "L. Fault/tamper detection and response": [
        "SECURITY_FAULT_DETECTION", "INTEGRITY_ERROR_DETECTION",
        "AUTHENTICATION_FAILURE_DETECTION", "ILLEGAL_ACCESS_DETECTION",
        "SECURITY_ANOMALY_DETECTION", "FAULT_ESCALATION", "SECURE_SHUTDOWN_TRIGGER",
        "QUARANTINE_TRIGGER", "SECURITY_RECOVERY_TRIGGER",
    ],
    "M. Cryptographic processing": [
        "CRYPTOGRAPHIC_KEY", "PLAINTEXT_DATA", "CIPHERTEXT_DATA",
        "IV_NONCE", "CRYPTOGRAPHIC_INTERMEDIATE", "ENCRYPT_DECRYPT_CONTROL",
        "KEY_LOAD_CONTROL", "KEY_CLEAR_CONTROL", "CRYPTOGRAPHIC_MODE_CONTROL",
        "ALGORITHM_SELECTION", "CRYPTO_OPERATION_START", "CRYPTO_OPERATION_COMPLETION",
        "ROUND_STATE", "KEY_SCHEDULE_STATE", "NONCE_COUNTER_STATE",
        "CIPHERTEXT_OUTPUT", "AUTHENTICATION_RESULT", "DERIVED_KEY_OUTPUT",
        "DIGEST_OUTPUT",
    ],
}

NEGATIVE_ROLES = (
    "ORDINARY_DATAPATH", "ORDINARY_COUNTER", "ORDINARY_PIPELINE_STATE",
    "ORDINARY_ARITHMETIC_INTERMEDIATE", "ORDINARY_PROTOCOL_HANDSHAKE",
    "PERFORMANCE_ONLY_CONTROL", "POWER_MANAGEMENT_ONLY", "GENERIC_BUFFER",
    "ORDINARY_STATUS", "NON_SECURITY_CONFIGURATION", "IMPLEMENTATION_TEMPORARY",
    "ORDINARY_ARBITRATION", "GENERIC_INTERRUPT", "GENERIC_RESET",
    "GENERIC_MEMORY_STATE", "ORDINARY_FSM_STATE",
)

RELATIONSHIPS = (
    "STORES", "CARRIES", "PRODUCES", "CONSUMES", "TRANSFORMS",
    "CONTROLS_ACCESS_TO", "AUTHORIZES", "SELECTS", "VALIDATES", "PROTECTS",
    "RELEASES", "OBSCURES", "CLEARS", "LOCKS", "UNLOCKS",
    "GATES", "ROUTES", "REPORTS_STATUS_OF", "DESTROYS", "RECOVERS",
)

POSITIVE_ROLES = tuple(r for labs in ROLE_VOCAB.values() for r in labs)
ALL_ROLES = POSITIVE_ROLES + NEGATIVE_ROLES


def _vocab_block() -> str:
    """The vocabulary as it appears in the prompt. Negative section is rendered with the
    same weight as the positive ones -- it is a section of the vocabulary, not a footnote."""
    out = ["POSITIVE ROLES (the element has a demonstrable security function):"]
    for section, labels in ROLE_VOCAB.items():
        out.append(f"  {section}")
        out.append("    " + ", ".join(labels))
    out.append("")
    out.append("NEGATIVE ROLES (you examined the element and its function is ordinary):")
    out.append("    " + ", ".join(NEGATIVE_ROLES))
    return "\n".join(out)


# =============================================================================
# The shared body. Ports and signals differ only in what they are called, which fields
# come back, and the one extra question a port asks (which side of the boundary). Writing
# the shared reasoning ONCE means the two parsers cannot drift apart -- a drift that would
# show up as a port/signal asymmetry in the asset stage and be misread as a finding about
# LLMasset.
# =============================================================================

_COMMON = """
HOW TO ASSIGN A ROLE

1. Read what the element actually does in the RTL: its assignments and updates, its
fan-in and fan-out, the conditions that guard it, the state machine it belongs to, the
comparisons and checks it feeds, what it selects, gates or routes.
2. Choose the LEAD role: the single label that best describes that function. Put it
first in "roles".
3. Add at most two further labels, and only when the element genuinely performs that
second function too. Do not list near-synonyms of the lead role.
4. If no positive label is supported by the RTL, choose the NEGATIVE label that fits.
Every element gets a role -- "I examined this and its function is ordinary" is a real
answer and the expected one for most of a typical module.

EVIDENCE RULES (these decide the role, not the name)

- A name is supporting evidence only. Never assign a positive role because an identifier
contains key, secret, auth, secure, priv, lock, debug, or similar. If the RTL behaviour
does not support the role, the name does not either.
- Being a register, a memory, an FSM, a bus, a mux, an enable, a reset, a counter, or
sitting inside a cryptographic block, does NOT by itself justify a positive role.
- Ordinary enable/ready/busy/valid handshakes, FIFO occupancy, resets, counters and
arbiters take a negative role unless the RTL shows a specific security consequence.
- "evidence" must quote or paraphrase what the RTL DOES -- an assignment, a guard, a
comparison, a state transition, a port connection. "named like a key" is not evidence.
Keep it under 15 words. If nothing in the RTL supports a positive role, say what the
element does instead and take the negative label.

RELATIONSHIP

When the element relates to a specific piece of data, state or control, record it as
{"verb": <one of the list>, "object": "<short plain-English name of what it relates to>"}.
The object is described in words, not as a role label, and it must be something that
exists in this module. Use null when the element takes a negative role, or when no
specific object can be named from the RTL.

VERBS: """ + ", ".join(RELATIONSHIPS) + """

WHAT YOU ARE NOT DOING

You are describing function, not making a verdict. Do not decide, state, rank or imply
that an element deserves attention, needs protecting, or matters more than another, and
do not name or hint at the objective a later stage will assign to it. That stage makes
those decisions and needs your description to be neutral evidence, not a recommendation.
Two elements with the same role are equally described, never ordered.
"""

_TAIL = """
Reproduce every name VERBATIM, including record fields written with a dot. Annotate every
element you are given, add none, drop none. Emit ONE JSON object and nothing else -- no
markdown, no code fences, no prose."""


PARSE_PORTS_ROLES_SYSTEM = """You annotate the FUNCTION of hardware I/O ports.

You are given a module's VHDL source and the AUTHORITATIVE list of its entity ports (name,
direction, type), already extracted from the RTL. That list is ground truth: annotate every
port, add none, drop none, reproduce names verbatim.

For each port produce:
  function  what it does, <= 12 words, inferred from its name, in-source comments and usage
  roles     1 to 3 labels from the vocabulary below, most specific first
  relationship  {"verb": ..., "object": ...} or null
  evidence  <= 15 words of RTL justification for the lead role

A port additionally carries a direction, so ask which way the function crosses the
boundary: does the module receive this, drive it, or both? Say so in "function" when the
direction is what makes the port what it is.

If a port's purpose is not determinable from the RTL, use function "unclear from RTL",
roles ["IMPLEMENTATION_TEMPORARY"], relationship null, and say so in evidence.

VOCABULARY
""" + _vocab_block() + "\n" + _COMMON + """
OUTPUT SCHEMA, one entry per provided port:
{"ports": [{"name": "<verbatim>", "function": "<concise>", "roles": ["<LABEL>", ...],
 "relationship": {"verb": "<VERB>", "object": "<short phrase>"} | null,
 "evidence": "<concise RTL evidence>"}]}""" + _TAIL


PARSE_SIGNALS_ROLES_SYSTEM = """You annotate the FUNCTION of internal design elements.

You are given a module's VHDL source and the AUTHORITATIVE list of its internal signals
(name, type), already extracted from the RTL. That list is ground truth: annotate every
element, add none, drop none, reproduce names verbatim.

For each element produce:
  kind      "register" if it holds state across clock edges or is assigned in a clocked
            process, otherwise "signal"
  function  what it does, <= 12 words, inferred from its name, in-source comments and usage
  roles     1 to 3 labels from the vocabulary below, most specific first
  relationship  {"verb": ..., "object": ...} or null
  evidence  <= 15 words of RTL justification for the lead role

If an element's purpose is not determinable from the RTL, use kind "signal", function
"unclear from RTL", roles ["IMPLEMENTATION_TEMPORARY"], relationship null, and say so in
evidence.

VOCABULARY
""" + _vocab_block() + "\n" + _COMMON + """
OUTPUT SCHEMA, one entry per provided element:
{"signals": [{"name": "<verbatim>", "kind": "register|signal", "function": "<concise>",
 "roles": ["<LABEL>", ...],
 "relationship": {"verb": "<VERB>", "object": "<short phrase>"} | null,
 "evidence": "<concise RTL evidence>"}]}""" + _TAIL


# ------------------------------------------------------------------- audit ---

def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def audit() -> None:
    """Everything this module promises about itself, checked at import.

    Counts are asserted against the taxonomy file's own totals so that editing ROLE_VOCAB
    without updating the docstring fails loudly rather than silently changing an input
    every downstream number depends on.
    """
    # 1. the vocabulary is the size the taxonomy says it is, with no collisions left
    assert len(POSITIVE_ROLES) == 152, f"positive roles = {len(POSITIVE_ROLES)}, expected 152"
    assert len(NEGATIVE_ROLES) == 16, f"negative roles = {len(NEGATIVE_ROLES)}, expected 16"
    assert len(RELATIONSHIPS) == 20, f"relationships = {len(RELATIONSHIPS)}, expected 20"
    assert len(set(ALL_ROLES)) == len(ALL_ROLES), \
        f"duplicate label(s): {sorted({r for r in ALL_ROLES if ALL_ROLES.count(r) > 1})}"

    # 2. the standing rule -- no evaluation-set identifier may enter a prompt. Imported
    #    from prompts_v2 rather than re-listed, so the two modules cannot disagree about
    #    what the banned set is.
    from prompts_v2 import EVAL_SET_IDENTIFIERS, EXTERNAL_IDENTIFIERS
    for label, text in (("PORTS", PARSE_PORTS_ROLES_SYSTEM),
                        ("SIGNALS", PARSE_SIGNALS_ROLES_SYSTEM)):
        hits = [b for b in EVAL_SET_IDENTIFIERS + EXTERNAL_IDENTIFIERS if b in text]
        assert not hits, f"{label}: evaluation-set identifier(s) present: {hits}"

    # 3. the parser must not cross into asset classification. These words are the ones
    #    that would move the decision upstream; their absence is the whole design.
    #
    #    Swept over the INSTRUCTIONS ONLY -- the vocabulary block is excluded, because the
    #    taxonomy's own section headings legitimately contain "Availability" and "Integrity"
    #    as label-group names. Sweeping the whole string would either fail on the vocabulary
    #    or force the ban list down to words too rare to catch a real regression.
    for label, text in (("PORTS", PARSE_PORTS_ROLES_SYSTEM),
                        ("SIGNALS", PARSE_SIGNALS_ROLES_SYSTEM)):
        instr = text.replace(_vocab_block(), "")
        assert len(instr) < len(text), f"{label}: vocabulary block not found to exclude"
        low = instr.lower()
        for banned in ("asset", "primary", "secondary", "confidential", "integrity",
                       "availability", "must be protected", "security objective",
                       "important", "critical"):
            assert banned not in low, \
                f"{label}: {banned!r} in the instructions moves classification into the parser"

    # 4. the negative vocabulary must actually be reachable: both prompts must render it
    #    and must require a role on every element.
    for label, text in (("PORTS", PARSE_PORTS_ROLES_SYSTEM),
                        ("SIGNALS", PARSE_SIGNALS_ROLES_SYSTEM)):
        assert "NEGATIVE ROLES" in text, f"{label}: negative vocabulary not rendered"
        assert "Every element gets a role" in text, f"{label}: role is not mandatory"
        assert "1 to 3 labels" in text, f"{label}: the 3-label cap is missing"
        for r in NEGATIVE_ROLES:
            assert r in text, f"{label}: negative role {r!r} not rendered"

    # 5. no numeric emission hint may reach the annotator. v1 measured that a numeric
    #    hint becomes a hard quota however it is hedged; "most of a typical module" is
    #    deliberately qualitative for that reason.
    for label, text in (("PORTS", PARSE_PORTS_ROLES_SYSTEM),
                        ("SIGNALS", PARSE_SIGNALS_ROLES_SYSTEM)):
        for banned in ("%", "at most 20", "no more than 20", "proportion of"):
            assert banned not in text, f"{label}: numeric emission hint {banned!r} present"


audit()


if __name__ == "__main__":
    print(f"positive roles {len(POSITIVE_ROLES)}  negative {len(NEGATIVE_ROLES)}  "
          f"relationships {len(RELATIONSHIPS)}")
    print(f"PARSE_PORTS_ROLES_SYSTEM   {len(PARSE_PORTS_ROLES_SYSTEM):6d} chars  "
          f"sha {sha(PARSE_PORTS_ROLES_SYSTEM)}")
    print(f"PARSE_SIGNALS_ROLES_SYSTEM {len(PARSE_SIGNALS_ROLES_SYSTEM):6d} chars  "
          f"sha {sha(PARSE_SIGNALS_ROLES_SYSTEM)}")
