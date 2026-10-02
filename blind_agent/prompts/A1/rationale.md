# Rationale for prompt A1 (definition-first)

## The design in brief

The prompt makes the executor apply one definition to every element: **a primary asset is the element where a
conceptual asset is held; everything that carries, copies, selects, enables, sequences or derives it is secondary.**
This is the LAsset split (LAsset p.2) combined with the conceptual-then-structural method of IEEE P3164 (CSA, p.8 to
p.10).

The procedure follows that order:

- **Step A**: understand the module.
- **Step B**: name the conceptual assets with the P3164 questions.
- **Step C**: map each conceptual asset to its holder with ordered holder cases.
- **Step D**: put every other element into a named secondary class, with the map facts that identify it.
- **Step E**: run the checks (attack, chain, sibling, record, coverage).
- **Step F**: copy names exactly.

Page numbers are PDF pages, except SA-EDI, where both the printed page and the PDF page are given (printed = PDF − 8).

## Decision rules, their sources and pages

"Reasoning" marks a rule, or part of one, that I derived from the cited text rather than read in it.

| # | Rule in the prompt (section) | Source and page | Why / note |
|---|---|---|---|
| R1 | Security asset = component or value whose protection preserves C, I or A (Definitions) | LAsset p.2 (§II.A first sentence); SA-EDI printed p.2 / PDF p.10 ("Asset" definition); Nath & Tan p.1 | Common base definition across the sources. |
| R2 | Conceptual asset (what) vs structural asset (where) (Definitions) | LAsset p.2 (§II.A, conceptual and structural bullets); P3164 p.8 (§3.1 both definitions) | The definition-first angle: the executor first names what is valued, then finds where it lives. |
| R3 | Primary = the structural element that is the conceptual asset, where it is held; the key register example (Definitions, Step C) | LAsset p.2 ("Primary Assets... direct target of an attack"; "Key Register is a structural asset because it directly stores the encryption key value"); SAIF p.2 ("definitive target for protection"; Example 2: the key value in an internal register is the primary asset) | The holder is the element an attacker must reach to get the harm directly. |
| R4 | Secondary = interacts with or facilitates exposure: buses, interface fields, ports and wires carrying a copy or part, enables, selects, addresses, machinery; engine and output buffer are secondary (Definitions) | LAsset p.2 (Secondary bullet: "system buses, peripheral ports, and internal signals/registers that carry the data of the primary asset, either fully or partially"; Enc/Dec engine and Output Buffer); LAsset p.4 (§III.B: internal signals/registers that influence the objectives are secondary); SAIF p.2 (secondary = infrastructure that closely interacts; tangible or intangible; Example 1: bus and decoder are secondary) | This rule controls precision. Being linked to an asset defines secondary, not primary. |
| R5 | Assume a system that needs C, I and A, with no context (The task) | P3164 p.9 (§3.1.1: each question starts "Assume that the IP is to be integrated into an IC where ... protections are required"; the approach assumes zero contextual knowledge) | The executor has no specification, so it must not guess a use case that removes assets. |
| R6 | The questions on confidentiality, integrity, availability and undermined behavior; "no" to all means not an asset (Step B) | P3164 p.9 (the questions) and p.10 (first line: "No" to all → not an asset); P3164 p.19 (the same questions reused in PIO) | The questions are reworded for RTL. The typical answers are filled in from R8 to R10. |
| R7 | Normal functional use is not an attack (Step B, last paragraph) | P3164 p.22 (DCache integrity: replacement on a store "is expected behavior and should not result in a 'yes'") | Stops "anything can be faulted" reasoning from making every element an asset. |
| R8 | Typical conceptual assets: keys, seeds, random numbers, identifiers, private payload, memory contents; configuration, permissions, privilege mode; control-flow state; register contents (Step B, kinds of unit) | SAIF p.2 (primary examples: cryptographic keys, random numbers and seeds, manufacturer keys and IDs, DRM keys, end-user private data, configuration bits for operational and privilege modes; program counter integrity); SAIF p.5 (case studies: program counter value and encryption key as primary); P3164 p.13 (LFSR/XOR seed: confidentiality; address into the coefficient ROM: integrity); P3164 p.15 (key, IV, input and output buffers, status and config registers); P3164 p.17 (memory array, data-in register, output register, address register); P3164 p.22 to p.23 (Table 3: registers, source and data registers, cache contents and internal state, branch-prediction history and target addresses); SA-EDI printed p.10 / PDF p.18 (Table 2 asset types: Critical, Secret, Sensitive, Control, Cryptographic, Code/Data, Compute) | Recall aid. Every candidate must still pass Steps C to E. |
| R9 | Reaction requests (reset, timeout, alarm, fault, halt, interrupt) the module generates are primary, objective Availability, at their holder (Step B, Step C) | SA-EDI printed p.25 / PDF p.33 (the timeout-assertion register is an asset: an adversary could block the reset or assert it constantly, a DoS); printed p.29 / PDF p.37 (Step 9: "The timeout assertion should never be gated", an Availability objective, attached to the register, not to the output port); P3164 p.9 (availability question: elements that could gate an output port) | Interrupt requests are added to this class by reasoning: they are the module's way to change the system's control flow, the same role as the timeout. |
| R10 | Counters and timers whose value is the module's function or triggers a reaction are primary (Step B, kinds of unit) | SA-EDI printed p.24 / PDF p.32 (the countdown register is an asset because an adversary would want to change it); SA-EDI printed p.10 / PDF p.18 (Critical type: timers and counters) | Bounded by R25: helper counters that only step an operation are secondary. |
| R11 | Stored here: the register, array or memory whose value is the asset is the holder (Step C, first case) | LAsset p.2 (the key register "directly stores" the key); P3164 p.10 (§3.1.2: structural assets are the RTL that produces the data and stores and transports its value); SA-EDI printed p.24 to p.25 / PDF p.32 to p.33 (the two assets are registers; the debug multiplexer wires and the ports are not assets); P3164 p.13 to p.14 (the ROM's output register is named as the structural asset) | Storage is where an asset rests; it is the most direct target. |
| R12 | A memory or register array is a single element: list the array (Step C) | SA-EDI printed p.13 / PDF p.21 (§7.2.1 c: "If the asset is an array, it is assumed the entire array is the asset unless a specified range is included") | Prevents index-level names, which cannot be compared as declared names. |
| R13 | Value read from a constant: the receiving register is the holder (Step C, second case) | P3164 p.13 to p.14 (for the coefficient ROM, the asset definition names the register that holds the ROM output, "Output from Coeff ROM"); MAP_FORMAT (constants are not elements) | Direct analogue of the source's own ROM example. |
| R14 | Value produced by a sub-unit outside the file: the element connected to that sub-unit's output is the holder in this module (Step C, third case) | LAsset p.4 (§III.B: conceptual assets are mapped "to their corresponding structural RTL references, derived from the parsed design elements; these are the primary assets at the module level"); LAsset p.5 (Fig. 5: the primary asset is a read-data signal named at the processor-top entity, while its write enable in a sub-unit is secondary); Nath & Tan p.5 (Case 2: trace a candidate to the connected port of the module) | Reasoning: inside a module that only instantiates, the connecting element is the module-level representative of the value. |
| R15 | Value not stored: the producing element, or the input port through which a consumed value enters, is the holder (Step C, fourth case) | LAsset p.5 (Table II: the AES primary assets are the module's key and state inputs, objective Confidentiality, and its out output, objective Availability); Nath & Tan p.5 (Case 1: an I/O port candidate is a potential primary asset); P3164 p.10 (structural = what produces and transports, e.g. reg and wire) | Ports become primary only when nothing inside holds the value (see D1). |
| R16 | Only forwarded: nothing here is the holder (Step C, fifth case) | LAsset p.2 (system buses carry the primary's data → secondary); SAIF p.2 (Example 1: the bus and decoder are secondary) | In a pure interconnect, the prompt points instead to the decisions it holds (grant, select, timeout, error, reservation). That pointer is reasoning, supported by P3164 p.9 (availability: elements that gate an output port or the use of an input port). |
| R17 | One holder per chain; staging, pipeline and delayed copies are secondary; the holder is the register software sees or the one that keeps the value until the next deliberate update (Step C) | LAsset p.4 (§III.C.4: "Along each path, the most tamper-prone asset is designated as the primary asset, while the remaining assets are treated as secondary"); LAsset p.2 ("either fully or partially") | Reasoning: "most tamper-prone" is made concrete as "the definitive, persistent copy". |
| R18 | An element that holds an asset is primary even if it also gates or selects (Step C) | P3164 p.15 (config registers are conceptual assets although their role is to control the engine); SAIF p.2 (configuration bits are primary) | Without this, the transient-control class (R24) would wrongly remove configuration registers. |
| R19 | Clock and reset are secondary (Step D) | Nath & Tan p.6 ("we did not consider 'Clock' and 'Reset' signals"); SA-EDI printed p.25 / PDF p.33 (clock and reset appear as Element ports, i.e. attack points, of the watchdog assets, not as assets) | |
| R20 | Holds nothing: unassigned signals, unused inputs, tied outputs, an undriven whole record port (Step D) | P3164 p.10 ("No" to all the questions → not an asset) | Reasoning: a constant tie-off or an unused name holds no information and no state, so every question answers "no". The whole record port is judged through its fields because the map says only its fields are assigned (MAP_FORMAT, `undriven`). |
| R21 | Interface carriers (request and response fields, read-back payload, copied acknowledge or error) are attack points, not assets (Step D) | LAsset p.2 (peripheral ports, system buses → secondary); SA-EDI printed p.2 / PDF p.10 ("Attack Point: an access location or means through which a threat can be realized against an asset"); SA-EDI printed p.14 / PDF p.22 (§7.4: Elements are the "top module influencers", i.e. ports, "that can affect and/or observe the behavior of the asset"); P3164 p.7 (ports are "the attack surface"); P3164 p.12 (the direction-select port is an attack point; the gates are the asset) | |
| R22 | Copies and parts: copies, slices, indexed reads, gated or multiplexed versions, delayed copies (Step D) | LAsset p.2 ("carry the data of the primary asset, either fully or partially"); SAIF p.3 (§III.A: components in the fan-out of a primary asset are where secondary assets are found) | Map cues (`COPIES`, `SELECTED_BY`, `GATED_BY` + `DERIVES_FROM`) make the rule checkable. |
| R23 | Next-value helpers are secondary (Step D) | LAsset p.2 (signals carrying the primary's data are secondary) | Reasoning: a next-state signal is the value on its way into the holder. |
| R24 | Transient controls (enables, strobes, selects, pulses, handshakes, decoded conditions) are secondary (Step D) | LAsset p.5 (Fig. 5: the write enable that "gates write access" to the primary asset is listed as its secondary asset); LAsset p.4 (§III.B: signals that influence the objectives are secondary); P3164 p.22 (expected behavior is not a "yes") | |
| R25 | Bookkeeping state (pointers, indexes, bit counters, prescaler ticks, sequencing FSMs) is secondary unless it encodes a privilege, protection or security mode (Step D) | SAIF p.2 (secondary assets can be intangible, "the controllability of an IP/states of an FSM"; Example 2: the boot-versus-normal execution state that restricts access to the key is secondary); SAIF p.6 (Table II: state and decoded-instruction registers come out as secondary assets of the program counter); P3164 p.19 (CSA can end up marking all internal blocks as structural assets, giving false positives); LAsset p.2 (the processing engine is secondary) | See D2 and D5 for the conflicts. |
| R26 | Mode and privilege state is primary (Step B, Step D exception, kinds of unit) | SAIF p.2 ("configuration bits for operational and privilege modes" listed with primary assets); P3164 p.9 (undermined-behavior question: privileged modes, overrides, bypass, test injection) | |
| R27 | Derived combinational status is secondary; stored status records that software acts on are primary (Step D, Step B) | P3164 p.15 (status registers "may leak confidential information" → conceptual asset); Nath & Tan p.3 (status-signal pattern: integrity, or availability when wired to another module's control) | Reasoning for the split: a combinational flag holds nothing beyond the state it is computed from. |
| R28 | Attack check: name the attack on the element's own value (Step E) | LAsset p.4 (§III.C.1: each candidate primary asset is checked against side-channel, fault injection, secure-to-nonsecure leakage, unauthorized access, privilege escalation, hardware Trojan and denial-of-service; "assets without such scenarios are excluded") | The added clause "aimed at another element that this one only carries" applies R4. |
| R29 | Chain check (Step E) | LAsset p.4 (§III.C.4, as R17) | |
| R30 | Sibling check: same role, same decision (Step E) | P3164 p.18 (both SRAM address signals get their own asset object "so it is explicit") | Reasoning: the main aim is consistency between runs and between like elements; the source shows like elements treated alike. |
| R31 | Record check: never a record together with its fields; the whole record when it is a single software-visible register loaded by the same write, otherwise the primary fields (Step E) | SA-EDI printed p.13 / PDF p.21 (§7.2.1 b: an Asset Definition "shall reference a single asset"; c: an array is whole by default); P3164 p.18 (combining or separating is a choice made explicit) | Reasoning: "loaded by the same write" is my test for "one asset". See risk F2. |
| R32 | Coverage check: every conceptual asset gets a holder, every entity is examined (Step E) | P3164 p.8 (a missed asset, a false negative, leaves a threat unidentified); LAsset p.3 (§III.A.3: RTL parsing exists "to ensure that LLMs do not overlook any of the parsed design elements") | Recall guard, balancing R21 to R25. |
| R33 | Names copied exactly from the map; no slices, constants, labels or instance names (Step F) | SA-EDI printed p.12 / PDF p.20 (§7.2: the Name "shall match its corresponding text in the source"); SA-EDI printed p.13 / PDF p.21 (Table 3: Name is case-sensitive); TASK_BRIEF (names compared as declared) | |
| R34 | A single objective per element (Step F) | SA-EDI printed p.16 / PDF p.24 (§7.5.1 b: an APSO object has exactly one security objective) | By analogy; the brief's contract also takes a single value. |
| R35 | Names are hints, confirmed by behavior (Step A) | Nath & Tan p.2 (partial keywords from "sensible" names); Nath & Tan p.3 (§III.B: "simple name matching is insufficient", so behavior is examined too) | |
| R36 | Elements that exist only under some build settings stay candidates (map legend) | SA-EDI printed p.15 / PDF p.23 (Table 5: configuration parameters are recorded with an asset, not used to drop it) | Reasoning: the reference describes the design, not a single build. |
| R37 | No list-size target; both error kinds weigh the same (The task) | TASK_BRIEF ("Precision ... and recall ... both count, equally"); LAsset p.4 (§III.C: LLMs "lean toward listing a broad set", which introduces false positives) | Says that over-listing is the known failure without giving a number. |

## Where the sources disagree, and what the prompt chose

- **D1. Ports.** LAsset p.2 lists peripheral ports and buses among the secondary assets. LAsset p.5 (Table II) and Nath
  & Tan p.5 (Cases 1 and 2) treat module I/O ports as primary. The prompt makes a port primary only when the port itself
  holds or produces the value, or when nothing in the module holds it (R15). Otherwise the internal holder wins (R11,
  R21). This is the largest recall risk (F1 below).
- **D2. State machines.** SA-EDI printed p.10 lists "FSM" under the Control asset type. SAIF p.2 calls FSM states
  secondary. The prompt treats sequencing FSMs as secondary and mode or privilege state as primary (R25, R26).
- **D3. Configuration registers.** The SA-EDI watchdog walk-through (printed p.24 to p.25) names only the countdown
  register and the timeout register; the control register with its locking bit is not named. P3164 p.15 (config
  registers need integrity) and SAIF p.2 (configuration bits are primary) include configuration. The prompt includes
  configuration registers (R18). This is the main precision risk in peripherals (F4).
- **D4. Copies.** P3164 p.18 gives both SRAM address signals their own asset objects. LAsset p.2 makes signals that
  carry the primary's data secondary. The reference comes from LAsset, so the prompt keeps the holder only (R17, R22).
- **D5. Addresses and pointers.** P3164 p.13 (the ROM address block) and p.17 (the address register) treat addresses
  as conceptual assets. Under LAsset's split, an address that picks which part of a primary is read "facilitates
  exposure", so it is secondary. The prompt classes pointers and indexes as bookkeeping (R25) (F3).
- **D6. Status.** A derived combinational status is secondary; a stored status record is primary (R27). This is a
  reasoned split, not a source's own rule.

## Why the prompt is built this way

- **One test, applied to every element.** Executors fail by listing everything on a value's path, or by deciding
  similar elements differently. "Holder versus carrier" is a single test that the map can mostly settle (`storage`,
  `COPIES`, `SELECTED_BY`, `GATED_BY`, `FORWARDS`, `connections`).
- **The map legend is inside the prompt.** The executor never sees MAP_FORMAT.md (brief rule 5). The example input
  also contains `CONSTRAINS` / `CONSTRAINED_BY` records that MAP_FORMAT.md does not describe, so the prompt tells the
  executor to read the cited lines for any type it does not know.
- **The analysis key has two parts.**
  - `conceptual_assets`, with `held_by` and `chain_not_listed`, makes the executor write each chain down and name the
    holder.
  - `element_roles` makes it place every element in a single role, which protects recall and consistency. `primary`
    must equal `assets`, which gives a check the executor can run on itself.
- **The worked example is invented** (neutral names, a made-up signing peripheral). It shows each hard case once: a
  record listed whole, a port that is itself a holder, a delayed copy, a next-value helper, a bookkeeping counter, a
  handshake flag, and interface carriers.
- **The kinds-of-unit reminders** cover the unit families named in the brief. They are written as generic hardware
  vocabulary, and each one sends the executor back to Steps C to E so that it does not copy the list.
- **What the rules give on the two example inputs.** This is reasoning; I scored nothing and saw no reference.
  - Read-only-memory module: only the register that receives the word read from the constant image. The response
    payload is a gated version of it, the acknowledge copies a read pulse, the error is tied, and the request fields
    are carriers or unused.
  - Queue module: the storage array and the single-entry storage register (alternative stores under different build
    settings). Pointers, the delayed pointer copy, flags, the fill count, the read and write ports and the enables are
    all secondary.

  These lists are short. If the reference also lists boundary ports or pointers for such modules, recall will suffer
  there (F1, F3).

## Risks, and what would falsify the choices

After the run, read precision and recall separately, per module and pooled. Also split both by element class: input
port, output port, clocked signal, combinational signal, whole record, record field.

- **F1 (port rule, D1).** If recall is low and the missed reference entries are mostly ports, while precision stays
  high, then R15/R21 are too strict for this reference.
- **F2 (record rule, R31).** If false positives are whole records while the misses are their fields (or the
  reverse), the record test points the wrong way.
- **F3 (bookkeeping, R25, D5).** If the missed entries are mostly pointers, counters or FSM state registers, the
  bookkeeping class is too wide.
- **F4 (configuration, D3).** If precision is low and the false positives are mostly fields of control and status
  registers in processor modules, the configuration inclusion is too wide for this reference.
- **F5 (decisiveness).** If repeated runs on the same module give different lists, the rules are not decisive enough.
  Check the sibling and record checks first.

Comparability: this prompt's outputs must go to their own output directory and must not be pooled with another
prompt's runs in one metric.

## Compliance with the brief

- **Rule 1 (no identifiers).** The prompt contains no name from the processor or its files. The example uses invented
  names. Plain words that are element names in the two example inputs are replaced by synonyms. Processor-specific
  unit names and acronyms are replaced by generic descriptions. The map vocabulary (field and type names) comes from
  the analyser's format, not from the processor. This rationale also avoids processor element names.
- **Rule 2 (no quotas).** The prompt has no list-size target and no proportion. The only number words in it are inside
  the brief's own contract placeholder, which is reproduced verbatim.
- **Rule 3 (no comments).** The prompt only states that comments were removed. It never asks the executor to use them.
- **Rule 4 (sources).** Every rule that decides asset or not-asset is in the table above, with source and page. Parts
  that are my own derivation are labelled reasoning.
- **Rule 5 (self-contained).** The map legend, the definitions and the example are all inside the prompt. The prompt
  does not refer to any outside document.
- **Output contract.** Reproduced verbatim. An `analysis` key is added between `module` and `assets`, which the brief
  allows.
- **Blindness.** I read only the listed files. I did not use the LAsset reference-list sizes (LAsset p.5, Table I) to
  set any expectation about list length.

## Files read

- E:/jobs/ff/test/Prepoison_subset/blind_agent/TASK_BRIEF.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/MAP_FORMAT.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/inputs/design/neorv32_boot_rom.txt
- E:/jobs/ff/test/Prepoison_subset/blind_agent/inputs/design/neorv32_fifo.txt
- E:/jobs/ff/2601.02624v2.pdf (all pages)
- E:/jobs/ff/IEEE_P3164_Asset_Identification.pdf (all pages)
- E:/jobs/ff/Accellera_SA-EDI_Standard_v10.pdf (all pages)
- E:/jobs/ff/2502.04648.pdf (all pages)
- E:/jobs/ff/SAIF_Automated_Asset_Identification_for_Security_Verification_at_the_Register_Transfer_Level.pdf (all pages)
