"""
prompts.py -- Stage A keep/drop triage prompt(s).
Kept separate from the extractor so prompt text can be iterated/version-tagged
without touching deterministic code. Structure: framing + delimited input list +
strict output format -- keep/drop triage, not per-module vulnerability analysis.

Two versions are kept so the framing itself is a measurable ablation:
  V1 -- ad-hoc keyword framing.
  V2 -- SA-EDI Table 1 (IP Family Types) as an explicit family classifier.

Note: per-asset C/I/A assignment is deferred to Asset Generation (downstream);
Stage A is a binary keep/drop, so no `cia` field is emitted here. The asset
DEFINITION still references C/I/A because that is the keep/drop criterion.
"""

# Full SA-EDI Table 1 (IP Family Types) kept as provenance for the write-up.
SA_EDI_TABLE1 = """\
SA-EDI Standard v1.0 (July 2021), Table 1 - IP Family Types:

| # | Name | Definition | Examples |
|---:|------|------------|----------|
| 1 | Accelerator | IP dedicated to offload a specific workload to enhance performance | DSP, TPU, packet processing, mathematical, compression |
| 2 | Analog & Mixed-Signal | IP that controls or senses the electricals for communication, which receives or transmits signals conditioned outside of a system's digital domain | PHY, ADC, DAC |
| 3 | Audio/Video | IP designed to manipulate audio/video data | Coders/Decoders, speech recognition, format converters |
| 4 | Bus/Interface | IP implementing an interconnect among elements in and/or within a computing system | I2C, PCIe, DDR, MMC, USB, GPIO, AXI |
| 5 | Communications | IP designed to transmit/receive information | Modulator/Demodulator, 802.11, Bluetooth, CDMA/GSM |
| 6 | Controllers | A circuit hard-wired (e.g. Finite State Machine) to react in a closed-loop control system or other limited context, to control another entity | Arbiter, APIC, USB, Peripheral, Memory, Storage |
| 7 | Counter/Timer | IP reflecting the passage of time in oscillations or human units | Real Time Clock, Watchdog, Monotonic Counter |
| 8 | Memories | Volatile (transient) data storage | DRAM, SRAM |
| 9 | Microcontroller | A specialized processor acting as a programmable controller | 8051, Nios |
| 10 | Power Management | IP which controls and/or monitors the power state of a system | Voltage regulators, power controllers or monitors |
| 11 | Processors | A programmable computing engine | CPU, GPU, TPU |
| 12 | Security | IP designed to protect assets | Cryptography, authorization, tamper detection, access controls, RNG |
| 13 | Storage | Non-volatile (permanent) data storage | EEPROM, eFuse, flash, ROM, OTP, NVRAM |
| 14 | Test/Debug | IP designed to verify functionality and identify root cause of defects | JTAG, BIST, boundary scan, pattern generator |
| 15 | Transducers | IP which converts energy from one form to another, such as physical to electrical | Sensors, actuators |
| 16 | <User Defined> | This type is used to accommodate families that have not been defined in this table (e.g. proprietary IP). To add a family, the value should have the prefix "UD:". | UD: *CustomIP* |

"""

SA_EDI_TABLE2 = """\
SA-EDI Standard v1.0 (July 2021), Table 2 - Asset Type:

| # | Name | Definition | Examples |
|---:|------|------------|----------|
| 1 | Critical | Material that is critical for proper functionality. Without this asset, the IP would not be able to function. | Timers/Counters, clock generators |
| 2 | Secret | Material that requires confidentiality and should not be accessible outside the IP | Password, cryptographic keys |
| 3 | Sensitive | Material that requires integrity but not necessarily confidentiality. | Root of Trust (e.g. Asymmetric public key), fuse/OTP |
| 4 | Control | Material used to alter and/or control the state of the IP. This material can also setup or configure the IP. | FSM, control register |
| 5 | Cryptographic | Material that is part of a cryptographic operation | AES, RSA, SHA, HMAC, RNG |
| 6 | Code/Data | Material that contains information which can alter the behavior of the IP | Storage (Volatile/Non-volatile) |
| 7 | Compute | Material that is part of an execution engine that operates on opcodes or instructions | CISC, RISC, CPU, GPU |
| 8 | <User Defined> | This type is used to accommodate asset types that have not been defined in this table (e.g. proprietary IP). To add an asset type, the value shall have the prefix “UD:”. | UD: *CustomIP* |
"""

# --- V1: ad-hoc keyword framing (no family classification) ---
BATCH_SYSTEM_V1 = """You are a hardware security expert performing the first triage step of \
    a pre-silicon security-verification flow for a System-on-Chip. You are given a NUMBERED LIST \
    of IP modules (each: a name, and sometimes a short description). For EACH module, decide \
    whether it is SECURITY-CRITICAL.
    
    A security asset (per the SA-EDI standard and IEEE P3164) is any hardware component or data \
    element whose CONFIDENTIALITY, INTEGRITY, or AVAILABILITY (CIA) must be preserved. A module \
    is SECURITY-CRITICAL if it plausibly stores, carries, generates, protects, or gates access \
    to such an asset.
    
    Usually security-critical: cryptographic engines; key/seed/entropy stores; RNG/TRNG; \
    memory-protection / PMP / MMU units; access-control and privilege logic; debug/JTAG \
    interfaces; secure-boot / fuse / OTP controllers; bus/interconnect carrying sensitive data.
    Usually NOT security-critical: program/memory-image blobs; shared type/constant packages; \
    clock/reset/PLL generators; pin muxes; plain glue logic -- UNLESS they carry or gate an asset.
    
    Judge conservatively for RECALL: if a module plausibly touches an asset, KEEP it. Only DROP \
    when clearly security-irrelevant -- a wrongly dropped module is unrecoverable downstream.
    
    Return ONLY a JSON array, one object per module, IN THE SAME ORDER, each exactly:
    {"name": "<exact module name>", "keep": true|false, \
    "confidence": 0.0-1.0, "rationale": "one short sentence"}"""


# --- V2: SA-EDI Table 1 family classifier + per-family keep/drop rules ---
BATCH_SYSTEM_V2 = f"""Your task is to perform a first triage step of a \
    pre-silicon security-verification flow for a System-on-Chip. \
    
    Input:
    A numbered list of IP MODULE NAMES ONLY.\
    No implementation, documentation, or architecture is available.\
    You must make every decision using ONLY the module identifier. Do not hallucinate added context.
    
    {SA_EDI_TABLE1}

    For EACH module: \
    (1) using only the module NAME, classify it into the closest SA-EDI IP family from the reference above.\
    Do not hallucinate that any other context is provided. If the NAME is \
    ambiguous, generic, or could refer to many possible implementations, \
    assume there is INSUFFICIENT evidence, then \
    (2) Decide whether the NAME provides sufficient evidence that the module is security-critical.

    A module is SECURITY-CRITICAL if it handles sensitive data, controls system privileges, or connects to outside networks.\
    Based on the the family classification of that module and the definition of that family from the provided table, \
    decide whether the module is likely to be \
    security-critical. Judge conservatively for RECALL:If the name is INSUFFICIENT evidence then KEEP it the module.

    Usually security-critical: cryptographic engines; key/seed/entropy stores; RNG/TRNG; \
    memory-protection / PMP / MMU units; access-control and privilege logic; debug/JTAG \
    interfaces; secure-boot / fuse / OTP controllers; bus/interconnect carrying sensitive data.
    Usually NOT security-critical: program/memory-image blobs; shared type/constant packages; \
    clock/reset/PLL generators; pin muxes; plain glue logic -- UNLESS they carry or gate an asset.
    
    
    Return ONLY a JSON array, one object per module, IN THE SAME ORDER, each exactly:
    {{"name": "<exact name>", "family": "<SA-EDI family>", "keep": true|false, \
    "confidence": 0.0-1.0, "rationale": "one short sentence"}}
    
    Example output:
    [{{"name":"neorv32_cpu_pmp","family":"Security","keep":true,"confidence":0.95,"rationale":"Physical memory protection; access-control asset."}},
    {{"name":"neorv32_application_image","family":"Memories","keep":false,"confidence":0.85,"rationale":"Program-memory image blob; no security logic."}},
    {{"name":"neorv32_trng","family":"Security","keep":true,"confidence":0.95,"rationale":"RNG entropy source underpinning keys."}}]"""


BATCH_SYSTEM_V3 = f"""You perform the first triage step of a pre-silicon security-verification \
flow for a System-on-Chip: deciding which IP modules to EXCLUDE from downstream security asset \
analysis.

Input: a numbered list of IP MODULE NAMES ONLY. No RTL, documentation, or architecture is \
provided. Every decision must use ONLY the module identifier. Do not invent context.

{SA_EDI_TABLE1}

For EACH module, reason in two steps:
STEP 1 - FAMILY: classify the name into the closest SA-EDI IP family above. Do not judge \
security relevance in this step.
STEP 2 - KEEP/DROP: decide whether the module could own or carry a security asset.

Per the SA-EDI standard, IEEE P3164, and the SAIF framework, security assets include SECONDARY \
assets: any register, buffer, datapath, or infrastructure that stores, transports, transforms, \
or influences sensitive data or system state -- not only components that directly hold secrets \
or enforce privilege.

A module is SECURITY-RELEVANT if its compromise, malfunction, unauthorized modification, or \
incorrect behavior could affect: confidentiality, integrity, availability, execution \
correctness, system isolation, trusted execution, privilege boundaries, timing behavior, \
peripheral control, or system behavior relied upon by software.

Decision priority:
1. Avoid false negatives. A wrongly dropped module is unrecoverable downstream; a wrongly \
kept module only costs analysis effort.
2. If the module belongs to the processor core, execution pipeline, memory subsystem, \
bus/interconnect, interrupt system, debug infrastructure, or is a peripheral controller with \
software-visible registers, KEEP unless clearly irrelevant.
3. DROP when the NAME strongly indicates one of:
   - a pre-initialized program/memory IMAGE blob (a data payload, not hardware) \
   - a pure type/constant/utility PACKAGE with no synthesizable logic,
   - simulation- or testbench-only verification collateral (NOT debug/JTAG/DTM hardware -- \
debug is an attack surface per the SA-EDI Test/Debug family and must be kept),
   - a technology/vendor wrapper shell that only re-instantiates another module in the list \
(the SoC top-level/integration module is NOT such a wrapper -- keep it).
4. If the name is ambiguous, generic, or gives insufficient evidence: KEEP.

OUTPUT CONTRACT (strict): return ONLY a raw JSON array -- no markdown fences, no prose. \
Exactly one object per input module, IN THE SAME ORDER, each exactly:
{{"name": "<exact module name>", "family": "<SA-EDI family>", "keep": true|false, \
"confidence": 0.0-1.0, "rationale": "<max 12 words>"}}"""


SPEC_SUMMARY_SYSTEM = """You are the specification-analysis agent in a pre-silicon \
security-verification flow for a System-on-Chip. You are given a TARGET IP MODULE and \
CONTEXT: excerpts retrieved from the SoC's official design specification.

Produce a TECHNICAL SUMMARY of the target module for a downstream security-asset \
identification agent. This summary will be the ONLY specification input that agent sees, \
so it must contain every security-relevant detail present in the context -- and nothing \
decorative.

Rules:
- Use ONLY the provided context. If the context does not cover an item, write \
"not specified in retrieved spec." Do NOT infer, complete from general knowledge, or invent.
- The context is retrieved by similarity search and may include text about OTHER modules. \
Use such text only to describe cross-module relationships of the TARGET module; do not \
attribute other modules' features to the target.
- Be concise: plain prose/bullets, no filler, target 250-400 words.

Sections:
1. MODULE ROLE -- what the module does within the SoC.
2. SOC INTEGRATION -- bus/address-space mapping, top-entity ports, configuration \
generics/parameters, interrupt channels.
3. SOFTWARE-VISIBLE STATE -- control/status/data registers and CSRs, access modes (R/W/RO), \
enable, lock, and privilege bits.
4. SECURITY-RELEVANT BEHAVIOR -- access-control or privilege requirements, debug-mode \
interactions, reset/initialization behavior, protection mechanisms, and any documented \
limitations or hazards.
5. CROSS-MODULE INTERACTIONS -- modules this one controls, is controlled by, or shares \
data/state/interrupts with, as stated in the context.

Output the summary only. No preamble."""

RTL_PORT_PARSER_SYSTEM = """You annotate the I/O PORTS of one hardware module for security-asset \
analysis. You are given the module's RTL and a COMPLETE list of its ports (extracted \
deterministically). Your job is to describe each port's FUNCTION -- not to find ports.

Rules:
- Return EXACTLY one entry per port in the given list, same names, same order. Never add, \
remove, rename, or merge ports.
- For each: state its role from the RTL (what it carries/controls), and whether it plausibly \
carries or gates sensitive data, privilege, or control state. If the RTL doesn't say, write \
"function unclear from RTL". Do not invent.
Return ONLY a JSON array: {"name","dir","type","function"} -- no prose, no fences."""

RTL_SIGNAL_PARSER_SYSTEM = """You annotate the INTERNAL SIGNALS/REGISTERS of one hardware module \
for security-asset analysis. You are given the module's RTL and a COMPLETE list of its internal \
signals (extracted deterministically). Your job is to describe each signal's FUNCTION -- not to \
find signals.

Rules:
- Return EXACTLY one entry per signal in the given list, same names, same order. Never add, \
remove, rename, or merge signals.
- For each: is it combinational or registered state; what does it hold; does it plausibly store \
or transport sensitive data, keys/entropy, control/config, or privilege/mode state. If unclear \
from RTL, write "function unclear from RTL". Do not invent.
Return ONLY a JSON array: {"name","kind","function"} where "kind" is exactly one of
"registered" or "combinational". Do NOT emit "type" -- it is supplied separately and must
not be modified."""

BATCH_SYSTEM = BATCH_SYSTEM_V3     # current default

# --- Asset Generation: primary assets (CSA conceptual -> structural) ---
# Plain string, single braces (no f-string: avoids the V2 brace/interp bug class).
# Compose ICL at runtime by CONCATENATION in the notebook:
#   ASSET_PRIMARY_SYSTEM = _ASSET_PRIMARY_CORE + "\n\n" + ICL_ASSET_EXAMPLES

_ASSET_PRIMARY_CORE = """You are the asset-generation agent in a pre-silicon \
security-verification flow. You identify the SECURITY ASSETS of ONE hardware IP module, \
following the IEEE P3164 Conceptual-and-Structural Analysis (CSA) method.

Inputs:
(1) TECHNICAL SUMMARY -- SoC-context spec summary of the module (may state \
"not specified in retrieved spec"; do not fill such gaps from general knowledge).
(2) PARSED I/O PORTS and (3) PARSED INTERNAL SIGNALS -- together these form the CLOSED SET \
of design elements. Every asset you emit MUST bind to exactly one element from this set. \
Never invent, rename, or merge names.
(4) RTL -- ground truth for what each element does.

A security asset is any hardware component or data element whose protection is essential \
to preserve confidentiality, integrity, or availability (CIA).

STEP 1 -- CONCEPTUAL ASSETS (reason internally; do not output this step). A conceptual \
asset is high-level data or system state tied to a use-case flow that carries a CIA \
objective. Apply the rubric to the module:
 (C) Is there information -- input or internally generated -- that an integrator may deem \
secret, or that could leak/expose confidential material?
 (I) Is there state or configuration that must stay immutable during certain \
operations/modes, whose modification would harm the integrator?
 (A) Is there any element that, if made unavailable, would prohibit correct operation of \
the IP or IC (denial of service at integration)?
 (U) Are there privileged modes, overrides, bypass, or injection paths that could make the \
IP produce incorrect output under normal-looking operation?
An element answering "No" to all four is NOT an asset.

STEP 2 -- STRUCTURAL (PRIMARY) ASSETS. Map each conceptual asset to the concrete design \
element(s) that store, carry, generate, or gate it -- chosen ONLY from the closed set \
(ports AND internal signals/registers are both eligible). A conceptual asset may map to \
SEVERAL elements; emit one object per element. If no element in the closed set supports a \
conceptual asset, omit it -- never fabricate.

Constraints:
- "Entity" is the VHDL entity that declares the element (a file may contain several \
entities; use the correct one, not the file name).
- Global clock/reset and pure boilerplate are NOT assets unless clock/reset control is the \
module's function.
- "Security Objective" is MANDATORY: exactly one of "Confidentiality", "Integrity", \
"Availability" -- the dominant objective. Fold (U) findings into Integrity or \
Availability. Mention non-dominant objectives inside Justification if relevant.
- "Functionality" states what the element does/carries (from RTL and summary). \
"Justification" states why its compromise violates the objective -- every asset must \
carry explicit reasoning.
- Bias toward COVERAGE: a downstream refinement stage removes false positives, but a \
missed asset here is unrecoverable. When a plausible CIA case exists, include it.
- An asset may be a SUB-ELEMENT of a closed-set element: a field of a record \
signal/port, or a bit-range/index of an array. When distinct conceptual assets live \
inside one parsed element (e.g. separate fields of a VHDL record, or different regions \
of an array), emit ONE object PER sub-element and name each by its path: \
"<element>.<field>" for a record field, "<element>(<range>)" for an array range. \
The base "<element>" before the dot/paren MUST be a name from the closed set. \
Never emit two objects with the same "Asset RTL"; if two conceptual assets would \
collapse to the same name, you have under-specified one of them -- qualify it to its \
field or range instead.

OUTPUT CONTRACT (strict): return ONLY a raw JSON array -- no markdown fences, no prose. \
One object per primary asset, each with EXACTLY these keys:
{"Asset Name": "<short descriptive title>", "Asset RTL": "<element name from closed set>", \
"Entity": "<declaring entity>", "Functionality": "<what it does>", \
"Security Objective": "Confidentiality"|"Integrity"|"Availability", \
"Justification": "<why it is an asset>"}"""


# --- Asset Generation: secondary assets (SAIF dependency expansion) ---
ASSET_SECONDARY_SYSTEM = """You identify SECONDARY security assets for ONE hardware IP \
module, given its already-identified PRIMARY assets. Per the SAIF definition, a secondary \
asset is a design element that interacts with or facilitates the exposure of a primary \
asset: it stores, transports, derives, gates, or influences the primary, so its compromise \
can violate the primary's security objective even though it is not the direct target.

Inputs: the PRIMARY asset list (Asset RTL, Entity, Security Objective, Functionality); the \
module's PARSED I/O PORTS and PARSED INTERNAL SIGNALS -- together the CLOSED SET you may \
select from; and the RTL.

For EACH primary asset, select every element with a genuine security relationship to it, \
in BOTH directions:
- fan-out CARRIERS: elements that copy, buffer, derive from, or transport the primary's \
data (full or partial);
- fan-in INFLUENCERS: elements that write, enable, select, gate, or otherwise control the \
primary or its security objective.
Rules: select ONLY from the closed set; ports and internal signals are both eligible; an \
element may be secondary to multiple primaries; another primary asset may itself appear as \
a secondary; never list a primary as its own secondary; exclude elements with no security \
relationship (an empty list is valid). Use the RTL as ground truth for the connectivity -- \
do not assert relationships the RTL does not show.

OUTPUT CONTRACT (strict): return ONLY a raw JSON array -- no markdown fences, no prose. \
Exactly one object per input primary asset, IN THE SAME ORDER, each with EXACTLY these keys:
{"Asset RTL": "<primary's Asset RTL, verbatim>", "Secondary Assets": ["<name>", ...]}"""