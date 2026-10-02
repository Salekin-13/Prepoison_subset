# D1 rationale (angle: MINIMAL)

## The bet

A short prompt that gives the executor one definition and one test, and states every exclusion by **role** (what the
element does), not by name. No worked examples. Reasons:

- Examples anchor an executor on surface names. Name-based asset finding is what LAsset criticises in earlier work
  (LAsset p.1, right column: the method of [18] "relies heavily on RTL signal and register naming conventions") and
  what Nath & Tan report as their main source of false positives (Nath & Tan p.6, Results: "atypical signal names,
  incorrect spelling ... atypical abbreviated signals").
- The executor's typical errors are listing too much (every signal near the data path), listing whole records or
  constants, and deciding similar elements differently. Each of those gets one explicit line in the prompt.
- Every rule uses facts the map already gives (storage, drive, handling, relationship type), so the executor can apply
  it the same way on a short file and on a file with thousands of lines.

## Page conventions

- LAsset (2601.02624v2), Nath & Tan (2502.04648) and SAIF: PDF page numbers (the papers print none).
- IEEE P3164 white paper: printed page = PDF page.
- Accellera SA-EDI v1.0: printed document page, with the PDF page in brackets (PDF = document + 8).

## Decision rules and their sources

| # | Rule in the prompt | Source and page | Why it is in the prompt |
|---|---|---|---|
| R1 | An asset is a value whose confidentiality, integrity or availability must be protected. | LAsset p.2 (II-A: "any hardware component or data element whose protection is essential to preserve ... (CIA)"); SA-EDI doc p.12 [PDF p.20] (7.2: asset is "critical to proper behavior which require security objective protections ... a port, module, register, or another object in the design"). | Sets the scope to CIA; tells the executor a port or a register can be an asset. |
| R2 | Conceptual asset = the value as an idea; structural asset = the RTL that holds or carries it. | P3164 p.8 (3.1: conceptual asset "associated with the use-case flows ... such as data and system state"; structural asset "RTL material that physically supports a conceptual asset"); LAsset p.2 (conceptual vs structural, AES key register). | The executor first names what is protected, then finds where it lives. This is the CSA order. |
| R3 | Primary = the element that is the direct target; secondary = elements that move, time, select, enable or compute part of it. List only primary. | LAsset p.2 (primary "serve as the direct target of an attack"; secondary "interact with or facilitate the exposure of primary assets ... system buses, peripheral ports, and internal signals/registers that carry the data of the primary asset, either fully or partially"); LAsset p.4 (III-B: conceptual assets mapped to structural RTL references from the parsed elements are the primary assets; signals that influence them are secondary); SAIF p.2 (II-C: primary = "definitive target for protection"; secondary = "infrastructures that closely interact with the primary assets"). | This is the definition the reference uses. It is the main precision lever. |
| R4 | The four questions (confidentiality, integrity, availability, undermined behaviour). | P3164 p.9 (3.1.1, questions 1-4); P3164 p.19 (PIO form of the same questions). | They are the standard's own test for a conceptual asset. "No to all" means not an asset (P3164 p.10, first line). |
| R5 | Intended updates in normal operation are not an integrity threat. | P3164 p.22 (4.1.2, DCache integrity: replacing data on a store "is expected behavior and should not result in a 'yes'"). | Stops the executor from calling every register an integrity asset just because it changes. |
| R6 | Undermined behaviour: the elements a privileged/debug/test/override/bypass path can corrupt are the conceptual assets (not the switch itself). | P3164 p.9 (question 4, "focus should be on elements that may be compromised"); P3164 p.13 (the address-override input makes the coefficient ROM the asset); P3164 p.12 (GPIO: the direction-select port is the attack point; the mux gates are the assets). | Points the executor at the target, not at the control input. |
| R7a | Kind: stored, received or returned data, including keys, seeds, random values. | SAIF p.2 (left column: "cryptographic keys, random numbers and seeds, manufacturer keys and IDs ... end-user's private data"); LAsset p.5 (Table II: AES primary assets are the key, the state input and the output); P3164 p.17 (SRAM: memory array, data-in register, output register); Nath & Tan p.3 (III-B-4, data signals: "Seed" and "Key", data stored in memory registers, Confidentiality). | Data is the most common conceptual asset in peripherals and memories. |
| R7b | Kind: settings held in registers (configuration, mode, privilege, lock, enable). | SAIF p.2 (left column: "configuration bits for operational and privilege modes" listed among primary assets); P3164 p.9 (question 2: "state or configuration settings that need to be immutable"); P3164 p.15 (AES: Config Regs need integrity); SA-EDI doc p.10 [PDF p.18] (Table 2, asset type Control: "FSM, control register"). | Settings are the integrity assets of control logic. |
| R7c | Kind: state that says where the module is in its work (state machine, program counter, timer count, pointers into stored data). | SA-EDI doc p.24 [PDF p.32] (B.2 step 2: the watchdog's timer count register is the asset); SA-EDI doc p.10 [PDF p.18] (Table 2: Critical, "Timers/Counters"; Control, "FSM"); SAIF p.1 (program counter value as an integrity concern) and p.5 (IV-A-1: program counter value chosen as the primary asset); P3164 p.22 (Table 3: branch history and target addresses, internal state). | Covers CPU, timer and buffer modules where the asset is state rather than data. |
| R7d | Kind: security decisions and events emitted (access allowed/denied, fault/error report, interrupt request, timer expiry, reset request). | SA-EDI doc p.25 [PDF p.33] (B.2: the timeout assertion register is an asset because "it is critical that the indication ... gets propagated out ... without any modification"); Nath & Tan p.3 (III-B-3: status signals such as "alert, and error", Availability or Integrity). | Covers outputs whose integrity or availability other logic depends on. |
| R8 | Map each conceptual asset to: the register/memory/array that holds it; the ports or record-port fields where it enters or leaves; a carrying signal only if neither exists. | P3164 p.10 (3.1.2: structural assets are the RTL that "produces 'Data' and stores and transports its value"); P3164 p.8 (a buffer that stores data "as it is entered into the IP"); LAsset p.5 (Table II: module ports listed as primary assets); Nath & Tan p.5 (III-C-5, Case 1: an element that is an input or output port of the top module goes to the primary list); P3164 p.19 (PIO: start from the information that goes in and is produced). | Storage plus boundary are the places a value can be read or changed whole. Internal carriers are left to R10. |
| R9 | Leave out clock and reset. | Nath & Tan p.6 (IV-A: "we did not consider 'Clock' and 'Reset' signals"); SA-EDI doc p.25 [PDF p.33] (the clock and reset ports appear in the Element objects as attack points, not as Asset Definitions). | Clock and reset touch every register. Listing them costs precision in every module. |
| R10 | Leave out strobes, handshakes and selectors (request/command strobes, valid/ready, read/write direction, write and byte enables, acknowledge, fill-state flags and counts, per-transfer addresses and indexes). Held settings and state are not strobes. | LAsset p.5 (Fig. 5 and IV-A: a write-enable input is listed as a *secondary* asset of a read-data primary asset); LAsset p.2 (secondary assets "interact with or facilitate"); SA-EDI doc p.25-26 [PDF p.33-34] (read enable, write enable, address and data inputs are attack points in Element/APSO objects, not assets); P3164 p.12 (a control port is the attack point, not the asset). | The example inside LAsset itself puts an enable on the secondary side. The exception for held settings keeps R7b. |
| R11 | Leave out intermediates: next-value signals, partial or derived versions, delayed or duplicated copies. | LAsset p.2 (signals/registers that carry the data "either fully or partially" are secondary); LAsset p.5 (Table II: one-round key, intermediate state and table-lookup signals are secondary); P3164 p.19 (CSA "may end up identifying all the internal blocks ... which could result in false positives"). | Without this, every wire on the data path gets listed. |
| R12 | Leave out fields that are only forwarded unchanged. | LAsset p.2 (system buses that carry the primary asset are secondary); SAIF p.2 (Example 1: "the bus and the decoder are the secondary supports helping to transfer the primary asset"). | Bus pass-through fields are transport, not the module's asset. |
| R13 | Leave out unused ports/fields and constant-tied outputs. | P3164 p.8 (a structural asset "physically supports a conceptual asset": an unused field or a constant supports none); P3164 p.10 ("No" to all questions means not an asset). | Unused record fields are many in bus slaves; they are a precision trap. |
| R14 | Name fields, not the whole record, when the fields carry the values; an array is one element. | SA-EDI doc p.13 [PDF p.21] (Table 3: Name is the path "as defined in the RTL source"; 7.2.1 b: one asset per Asset Definition; 7.2.1 c: "the entire array is the asset unless a specified range is included"). | Matches names as declared, which is how the output is compared. |
| R15 | Constants are not elements; if a constant (a ROM table) holds an asset, list the elements that hold or deliver its value. | P3164 p.13-14 (the coefficient ROM's asset is recorded as its output register, the Asset Definition names that register); brief and MAP_FORMAT (constants are not elements). | Prevents invented names and keeps recall for ROM-like modules. |
| R16 | Keep only direct targets: the executor must name a concrete attack whose target is the element itself. | LAsset p.4 (III-C-1: candidates are checked against seven attack classes, side-channel, fault injection, secure-to-nonsecure leakage, unauthorized access, privilege escalation, hardware Trojan, denial of service; "assets without such scenarios are excluded"); LAsset p.4 (III-C-4: on a path, "the most tamper-prone asset is designated as the primary asset, while the remaining assets are treated as secondary"). | This is LAsset's own refinement step, turned into a per-element check that also separates target from path. |
| R17 | Be consistent: same role, same decision. | LAsset p.4 (III-C-3: refinement includes "self-consistency checks"); P3164 p.18 (two signals holding the same SRAM address are both structural assets, kept as separate objects). | Inconsistent decisions between twin elements cost precision and recall at the same time. |
| R18 | Objective: the one most at risk. | SA-EDI doc p.16 [PDF p.24] (7.5.1 b: "An APSO object shall have exactly one Security Objective defined"). | The objective is not scored. One word keeps the output short. |

## Where the sources disagree, and the choice I made

- **Ports.** SA-EDI treats ports as attack points kept apart from assets (doc p.14-15 [PDF p.22-23]; watchdog example
  doc p.24-25 [PDF p.32-33], where only two internal registers are assets). LAsset's AES table lists the module's key,
  state and output ports as primary assets (LAsset p.5, Table II), and Nath & Tan put top-module ports on the primary
  list (p.5). The reference comes from LAsset, so the prompt lists ports that carry a conceptual asset (R8) and
  leaves out ports that only control a transfer (R10). This is a judgement, not a measurement.
- **Mode state.** SAIF lists configuration bits for operational and privilege modes as primary (p.2), but its Example 2
  calls a boot/normal execution state secondary to a key (p.2). The prompt follows the first: a held mode or privilege
  setting is primary. In a module that also holds a secret, this choice may add false positives.
- **Status and control signals.** Nath & Tan treat single-bit control, configuration and status signals as asset
  patterns (p.3), and P3164 question 3 names elements that "could gate an output port" (p.9). LAsset's own example puts
  an enable on the secondary side (p.5, Fig. 5). The prompt follows LAsset: transfer strobes, handshakes and fill-state
  flags are left out; security decisions and events (R7d) stay in.

## How the rules play out on the two design inputs (reasoning, not a score)

I traced the prompt by hand on the two files I was given. I have no reference, so this shows only that the rules
give a definite, consistent answer. It says nothing about precision or recall.

- Boot ROM file (21 elements: 19 PORT lines and 2 SIGNAL lines, counted by hand from the map, exact). Kept 2: the
  read-data register and the read-data field of the response port (R7a, R8, R15: the ROM table is a constant). Left
  out 19: clock and reset (R9); address, strobe and read/write fields (R10); the registered read pulse and the
  acknowledge field (R10); the constant-tied error field (R13); nine unused request fields (R13); the two whole
  records (R14).
- FIFO file (27 elements: 11 PORT lines and 16 SIGNAL lines, counted by hand, exact). Kept 6: write-data input,
  read-data output, both storage elements (each exists under a different build condition), write and read pointers
  (R7a, R7c, R8). Left out 21: clock and reset (R9); write, read and flush strobes at the ports and inside (R10);
  fill-state flags and the fill count, inside and at the ports (R10); the pointer-compare signal, the next-value
  signals and the registered duplicate of the read pointer (R11).

The FIFO map also contains a relationship type, `CONSTRAINS`/`CONSTRAINED_BY`, that the map format document does not
describe. The prompt therefore tells the executor to read the cited RTL lines for any type it does not know.

## Rule compliance

- No identifier from the design files or the processor. Generic English words that also happen to be field names
  (such as "data", "debug", "lock") appear only as ordinary words. Record and field placeholders are written as
  `<record>.<field>`.
- No digits, quotas or proportions anywhere in the prompt.
- No instruction to use HDL comments.
- The output contract has the brief's shape. One extra key, `conceptual_assets`, comes before `assets` to hold the
  executor's analysis, as the brief allows.

## What could prove this design wrong, and what to read after the run

- If recall misses are mostly **status flags, handshakes or control inputs**, R10 is too strict. Read: the recall
  loss split by element role (strobe, flag, handshake, control input) against the reference.
- If false positives are mostly **ports**, R8 is too generous. In that case the reference follows SA-EDI's separation
  of ports from assets. Read: precision on port entries against precision on internal register entries.
- If false positives are mostly **mode or privilege registers in modules that also hold secrets**, the SAIF Example 2
  reading was the right one. Read: the false-positive list filtered to settings registers.
- If misses are **whole records** where the executor listed fields (or the other way round), R14 picked the wrong
  naming level. Read: the misses whose name is a prefix of a listed name.
- If two runs on the same file disagree on twin elements, R17 is not strong enough. Read: run-to-run agreement on
  sibling elements (pointer pairs, fields of one register).
