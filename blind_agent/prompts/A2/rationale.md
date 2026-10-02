# Rationale for prompt A2 (definition-first, revision of A1)

## What changed, in brief

A2 keeps A1's definition: **a primary asset is the element where a conceptual asset is held; everything that carries,
copies, selects, enables, sequences or derives it is secondary** (LAsset p.2, IEEE P3164 p.8 to p.10). The revision
does not change the angle. It removes the places where A1 let the executor reach two different answers for the same
structure. It does this in three ways:

- The holder rules are now an ordered list of named tests. The executor must write which test it used.
- An empty holder is allowed only for three named reasons.
- Every value is classed as either a content value (what the module stores or computes with) or a steering value
  (what decides whether, when, where or how). This class settles inputs, latched request fields and wrapper wiring.

**The critic's report was not available.** The listed file `blind_agent/critic/A1/report.md` did not exist when I
tried to read it: the Read tool returned "File does not exist". I did not search for it or list its folder, because
the blindness rules forbid that. So no change below cites a critic point. Every change cites evidence I read myself:
the executor's output files, and the module input lines that show what the RTL does.

Page numbers are PDF pages, except for SA-EDI, where both are given (printed page = PDF page − 8). I re-read every
page cited below in this session.

## Change log

Each row: the change, the evidence behind it, and the rule it touches. "Output" means a file under
`blind_agent/runs/tuning/A1/r0/`. "Input" means a file under `blind_agent/inputs/tuning/`. Element names appear here
only as evidence. The prompt contains none of them.

| # | Change in A2 | Evidence | Rule |
|---|---|---|---|
| C1 | `held_by` may be empty only under `forwarded`, `held in another unit` or `constant only`. Otherwise the executor names a holder, or removes the item as not a conceptual asset. A new `holder_case` field records the test used. | Output `neorv32_cpu.json`: "Register file contents" and "Control and status registers" have `held_by: []`. Yet input `neorv32_cpu.txt` RTL lines 263, 299, 324 to 326, 371, 416 and 445 wire `csr_rdata`, `xcsr_cnt`, `rs1`/`rs2`/`rs3`, `xcsr_alu`, `xcsr_pmp` and `xcsr_icc` to sub-unit outputs. A1's third holder case makes those the holders. Output `neorv32_cpu_cp_muldiv.json`: "operand values" has `held_by: []`. Outputs `neorv32_cache.json` (bypass decision), `neorv32_imem.json` (bus acknowledge) and `neorv32_sys.json` (clock-enable ticks) name items as conceptual assets and give them no holder. Each of those items is a transient control or bookkeeping under A1's own Step D. A1's coverage check allowed "a note saying why no element holds it", and the executor used that note to skip holders. | R40 (new), R14, R32 |
| C2 | A conceptual asset is the information, not its location. The same message in a queue, a shift register and a port is a single conceptual asset. A store in this file comes before a sub-unit connection (`stored here` is tested before `sub-unit`). | Output `neorv32_twi.json` lists both `engine.sreg` and the queue read-outs `fifo.tx_rdata`, `fifo.rx_rdata` as separate conceptual assets. Input `neorv32_twi.txt` RTL line 327 loads `engine.sreg` from `fifo.tx_rdata`, and line 228 writes `fifo.rx_wdata` from `engine.sreg`, so they hold the same bytes. Output `neorv32_trng.json` lists both `sample_sreg` and `fifo.rdata`, which also hold the same bytes. Outputs `neorv32_uart.json` and `neorv32_spi.json` list only the shift registers and class the queue connections as carriers. One structure, two decisions. | R2, R42 (new), R14 |
| C3 | A *store* (loads under a condition and keeps the value, or builds it step by step) is now separated from a *delayed copy* (copies another element of this file on every clock) and from a *synchroniser* (copies an input every clock). A register that captures a content value from a port under a load condition is a store. | A1 defined a delayed copy as "a register that copies another element", and a port counts as an element. Output `neorv32_cpu_cp_muldiv.json` classes `mul.dsp_x` and `mul.dsp_y` as `copy_or_part`. Input `neorv32_cpu_cp_muldiv.txt` RTL lines 170 to 172 load them from the operand ports only when an operation starts, and `div.rs2_abs` is loaded at line 270 the same way. Output `neorv32_cpu_cp_cfu.json` lists `xtea.opa` and `xtea.opb`, which are loaded from the operand ports on start in the same way, as primary. Same structure, opposite decisions. | R41 (new), R11, R22 |
| C4 | Content value versus steering value. A steering value that arrives from another unit and is only used here is a carrier (`held in another unit`). The input-port holder case is limited to content values (`content input`). | A1 contradicted itself. Step C case 4 said that a value received and used without being stored is held at its input port. Step D said that requester attributes such as privilege are interface carriers. Output `neorv32_cpu_pmp.json` names the privilege mode as a conceptual asset with `held_by: []`, and classes `ctrl_i.cpu_priv` as an interface carrier. Output `neorv32_sys.json` does the same for the incoming reset requests. Both follow Step D and break case 4. A2 settles the conflict in favour of Step D, which has the stronger source basis (R38). | R38 (new), R15, R21 |
| C5 | A steering value kept only for the length of one transfer or operation (an operation code, a request attribute) is a transient control. | Output `neorv32_bus.json` lists `arbiter.cmd`, the atomic operation code latched for one read-modify-write, as primary. A1's Step D already classes requester attributes and transient controls as secondary, but its "stored here" case was tested first and caught the latch. | R24, R38 |
| C6 | The `FORWARDS` cue is narrowed. `forwarded` applies only to a value that arrives through a port and leaves through another port. An internal record field marked `FORWARDS` that runs between sub-units goes to the `sub-unit` test. | Input `neorv32_cpu.txt` map lines 429 to 479 mark internal fields such as `ctrl.pc_cur` and `frontend.instr` with `"handling":["FORWARDS"]` and `"storage":"not assigned"`. A1's "Only forwarded" case cited `handling FORWARDS` as its cue. Read literally, it removes the program-counter field that the A1 executor listed. The executor got it right in this run, but the rule did not force that answer. | R16 |
| C7 | Sub-unit connections: the map's `mode` can be empty. A2 says how to read the direction from the RTL, and says that the fields of a record wired as a whole are wired through it. | A1 told the executor to look for `connections` "with mode `out`". In input `neorv32_cpu.txt` every connection has `"mode":null` (map lines 343 to 515), so the cue A1 named never appears in that file. The record `ctrl` carries the connections (map line 428), while its fields show none (lines 429 to 472). | R14, R20, R45 (new) |
| C8 | The `sub-unit` test now covers a sub-unit output that delivers only the selected entry of a larger store (a register-file read port, a status read-out). The indexed-read rule in Step D applies only to an array stored in this file. A merge of several holders (an `or`) is secondary. Bus request and response fields stay carriers even when a sub-unit drives them. | Output `neorv32_cpu.json` classes `rs1`, `rs2` and `rs3` as indexed reads (`copy_or_part`) and the read-back words as carriers. The array they read from is not in the file, so A1's indexed-read rule had no array to point to. `xcsr_res` is the `or` of the sub-unit read-outs (input `neorv32_cpu.txt` RTL line 279). | R14, R22 |
| C9 | The chain tie-break is now an order. First, the store that another party writes or reads directly. Otherwise, the store where the complete value comes to rest. | A1 joined these two criteria with "or". Output `neorv32_debug_dtm.json` (its `notes` field) says that `dmi_ctrl.addr`, `dmi_ctrl.wdata` and `dmi_ctrl.op` are slices of `tap_reg.dmi`, taken at update and kept until the next one, while the debugger shifts `tap_reg.dmi` directly. The two criteria therefore point at different registers. The executor chose the debugger-facing register; A1 allowed either choice. I did not read this module's input, so this rests on the executor's description. | R17 |
| C10 | The sibling check now also covers every operand store of the same operation, every read-out of the same store, and every fault, error or alarm request the module or its sub-units generate. | Output `neorv32_cpu.json` lists `pmp_fault`, a fault decision delivered by a sub-unit. It classes `lsu_err` and `frontend.fault`, which are fault and error signals delivered by other sub-units (input RTL lines 391 and 199), as carriers. | R30 |
| C11 | State registers: a single test separates bookkeeping from an asset. Bookkeeping says which step is running. An asset says who owns or may use something, or which mode is in force. | A1 stated this split in two places (Step D bookkeeping, and the bus reminder about "current grant"). Output `neorv32_bus.json` applied it as intended (switch grant state primary, read-modify-write step state secondary), so this is a wording merge, not a behaviour fix. | R25 |
| C12 | New reminders for execution units and co-processors, and for units that only connect sub-units. Third and second worked examples added: a queue sub-unit with a shift register and a steering input; a module that only connects sub-units. | These are the structures behind C1 to C8. Each example is invented and shows the decision the new rules give. | R43, R44 (new) |
| C13 | Analysis format: a `field_of_listed_record` role; a name declared in several entities is written once per entity; the `holder_case` field. | Outputs `neorv32_uart.json`, `neorv32_spi.json`, `neorv32_twi.json` and `neorv32_wdt.json` put the fields of the listed `ctrl` record in `copy_or_part`, which is the wrong class. Output `neorv32_trng.json` lists `clk_i` and `rstn_i` three times each without saying which entity declares each one. These keys are not scored. | none (format) |
| C14 | Vocabulary: no new word that is a bare element name in this processor's files. A2 says "content value", not "data value", and avoids "lock", "start" and "done" as bare words. No digits in rule text or in invented names. | A1 avoided these words. I kept the same discipline for the new text. | Brief rules 1, 2 |

What A2 keeps unchanged, because the outputs applied A1's rule consistently and the rule has a source basis:

- the whole-record rule (a single software-visible register loaded by one write is listed as the record);
- reaction requests at the register or port where they are produced;
- memories as whole arrays, and parallel byte-lane arrays each listed;
- the read-only-memory output register;
- grant, locking and reservation state;
- timeout and watchdog counters;
- stored status flags;
- the noise-source state.

### Position changes against A1

None of these reverses an A1 recommendation. Each one narrows or orders an A1 rule. I flag them because outputs
under A2 will differ from A1 on the same modules.

- A1's input-port holder case (any value received and used without being stored) is narrowed to content values. This
  is the C4 conflict, settled in favour of A1's own Step D.
- A1's "delayed copy" no longer covers a register that captures a value from a port under a load condition (C3).
- A1's `FORWARDS` cue no longer decides the `forwarded` test on its own (C6).
- A1's two-part chain tie-break is now an ordered rule (C9).

## Decision rules, their sources and pages

"Reasoning" marks a rule, or part of one, that I derived from the cited text rather than read in it. "(A2)" marks a
rule that is new or changed.

| # | Rule in the prompt (section) | Source and page | Why / note |
|---|---|---|---|
| R1 | Security asset = component or value whose protection keeps C, I or A (Definitions) | LAsset p.2 (§II.A, first sentence); SA-EDI printed p.2 / PDF p.10 ("Asset" definition); Nath & Tan p.1 (§II, first sentence) | Common base definition. |
| R2 (A2) | Conceptual asset (what) versus structural asset (where). A conceptual asset is the information wherever it sits; the other direction is a separate asset (Definitions) | LAsset p.2 (§II.A: the key "is a conceptual asset because its confidentiality must be preserved regardless of where it resides in the design"); P3164 p.8 (§3.1: conceptual asset = data and system state of the use-case flows; structural asset = RTL material that supports it) | The added sentence stops one message being split into several assets by location (C2). Treating the two directions separately is reasoning, consistent with the sibling rule R30. |
| R3 | Primary = the structural element that is the conceptual asset, where it is held; the key-register example (Definitions) | LAsset p.2 ("Primary Assets ... serve as the direct target of an attack"; "the Key Register is a structural asset because it directly stores the encryption key value"); SAIF p.2 ("definitive target for protection"; Example 2, key value in an internal register) | |
| R4 | Secondary = interacts with or helps expose a primary: buses, interface fields, ports and wires carrying a copy or part, enables, selects, addresses, machinery (Definitions) | LAsset p.2 (Secondary bullet: "system buses, peripheral ports, and internal signals/registers that carry the data of the primary asset, either fully or partially"; engine and output buffer); LAsset p.4 (§III.B: signals and registers that influence or violate the objectives are secondary); SAIF p.2 (secondary = infrastructure that closely interacts; tangible or intangible; Example 1, bus and decoder) | Being linked to an asset makes an element secondary, not primary. |
| R5 | Assume a system that needs C, I and A (The task) | P3164 p.9 (§3.1.1: each question begins "Assume that the IP is to be integrated into an IC where ... protections are required"; zero contextual knowledge) | |
| R6 | The C, I, A and undermined-behaviour questions; "no" to all = not an asset (Step B) | P3164 p.9 (the questions); P3164 p.10 (first line: "No" to all → not an asset) | |
| R7 | Normal functional use is not an attack (Step B) | P3164 p.22 (DCache integrity: replacement on a store "is expected behavior and should not result in a 'yes'") | |
| R8 (A2) | Typical conceptual assets, now including the operands and results of a computation (Step B, kinds of unit) | SAIF p.2 (keys, random numbers and seeds, IDs, private data, configuration bits for operational and privilege modes; program counter); P3164 p.13 (seed, coefficient address); P3164 p.15 (key, IV, input and output buffers, status and configuration registers); P3164 p.17 (memory array, data-in, output and address registers); P3164 p.22 to p.23 (Table 3: GPR/FPR registers, Confidentiality; functional units: "Source and data registers", Confidentiality; cache contents and internal state); SA-EDI printed p.10 / PDF p.18 (Table 2 asset types) | Recall aid. Every candidate must still pass Steps C to E. |
| R9 | Reaction requests (reset, timeout, alarm, fault, halt, interrupt) that this module or a sub-unit generates are primary at their holder (Step B, Step C) | SA-EDI printed p.25 / PDF p.33 (the timeout-assertion register is an asset: blocking or constantly asserting the reset is a DoS); SA-EDI printed p.29 / PDF p.37 (Step 9: "The timeout assertion should never be gated", Availability attached to the register, with the output port as the attack point); P3164 p.9 (availability question) | Adding interrupts to this class is reasoning. "Or a sub-unit" follows from R39. |
| R10 | Counters and timers whose value is the function or triggers a reaction are primary (Step B) | SA-EDI printed p.24 / PDF p.32 (the timer register is an asset because an adversary would want to modify the counter); SA-EDI printed p.10 / PDF p.18 (Critical type: timers and counters) | Bounded by R25. |
| R11 (A2) | `stored here`: a register, array or memory that keeps the value is the holder, including a register that captures a value from a port or a sub-unit under a load condition, and one that builds a value step by step (Step C) | LAsset p.2 and Fig. 2 (the Key input feeds the Key Reg, and the register, not the port, is the structural asset that "directly stores" the key); P3164 p.10 (§3.1.2: structural assets are the RTL that produces, stores and transports the value); P3164 p.17 (the Data-In Register, which captures the data port, is a conceptual asset); SA-EDI printed p.24 to p.25 / PDF p.32 to p.33 (the assets are registers; the ports appear as Element objects) | The capture-from-port clause fixes C3. |
| R12 | A memory or register array is a single element; alternative build-time stores and parallel stores of different parts are each a holder (Step C) | SA-EDI printed p.13 / PDF p.21 (§7.2.1 b: an Asset Definition references a single asset; c: an array is whole unless a range is named) | Parallel parts (for example byte-lane arrays) being separate holders is reasoning: each is its own declared element, and none is a copy of another. |
| R13 | `read from a constant`: the receiving register is the holder (Step C) | P3164 p.13 to p.14 (for the coefficient ROM, the asset definition names the register holding the ROM output, "Output from Coeff ROM"); MAP_FORMAT (constants are not elements) | |
| R14 (A2) | `sub-unit`: the element connected to the sub-unit output that delivers the value, even a selected entry; for a record wired as a whole, the field. If nothing delivers it, the element that carries it in. A store in this file comes first. Bus request and response fields stay carriers (Step C) | LAsset p.4 (§III.B: conceptual assets are mapped "to their corresponding structural RTL references, derived from the parsed design elements- these are the primary assets at the module level"); LAsset p.5 (Fig. 5: the primary asset at the processor-top entity is a control/status read-data signal, objective Integrity, while a write enable inside a sub-unit is its secondary asset); LAsset p.5 (Table II: for the AES-128 design, the primary assets are the top module's key and state inputs and its out output, while the signals inside the sub-modules are secondary); Nath & Tan p.5 (Case 2: a candidate inside an instantiated module is traced to the connected ports of the top module); LAsset p.2 and SAIF p.2 Example 1 (buses are secondary) | Reasoning: the delivering element is the module-level stand-in for a value whose store is not in the file. The bus-field exception keeps R21 intact. |
| R15 (A2) | `produced here`: the element the computation assigns. `content input`: a content value that is computed with and stored nowhere in any build is held at its input port (Step C) | LAsset p.5 (Table II: AES key and state inputs are primary, objective Confidentiality); Nath & Tan p.3 (data signals: inputs and outputs that carry information for processing, with key and seed as examples) and p.5 (Case 1: I/O port candidates); P3164 p.10 (structural = what produces and transports) | Limiting the port case to content values fixes C4. |
| R16 (A2) | `forwarded`: a value that arrives through a port and leaves through another port in the same form, and that the module neither keeps nor computes with, has no holder here. `FORWARDS` on its own does not decide this (Step C) | LAsset p.2 (system buses that carry the primary's data are secondary); SAIF p.2 (Example 1: bus and decoder secondary); MAP_FORMAT (`FORWARDS` is a mechanical fact, "it passes the value on unchanged", with no judgement on where the value rests) | The narrowing fixes C6. |
| R17 (A2) | A chain has a single holder. Among stores of this file in a row: first the store another party reads or writes directly, otherwise the store where the complete value comes to rest. Staging, pipeline, delayed and shift-out copies are secondary (Step C) | LAsset p.4 (§III.C.4: "Along each path, the most tamper-prone asset is designated as the primary asset, while the remaining assets are treated as secondary"); LAsset p.2 ("either fully or partially"); SAIF p.2 ("definitive target") | Reasoning: the store that an outside party reaches directly is the most tamper-prone point of the path. The fallback picks the definitive copy. |
| R18 | An element that holds an asset is primary even if it also gates or selects (Step C) | P3164 p.15 (configuration registers are conceptual assets, though their role is to control the engine); SAIF p.2 (configuration bits are primary) | |
| R19 | Clock and reset are secondary (Step D) | Nath & Tan p.6 ("we did not consider 'Clock' and 'Reset' signals"); SA-EDI printed p.25 / PDF p.33 (clock and reset are listed among the Element ports of the watchdog assets, that is, attack points) | |
| R20 (A2) | Holds nothing: unassigned signals not driven by a sub-unit, either directly or through their whole record; inputs with no relationship records and no connections; tied outputs; whole records unassigned as a whole (Step D) | P3164 p.10 ("No" to all → not an asset); MAP_FORMAT (`undriven`, `not assigned`, `connections`) | Reasoning: a tie-off or an unused name holds no information. The record-wiring clause comes from map evidence C7. |
| R21 (A2) | Interface carriers: bus request and response fields and ports that move a value held elsewhere, including steering inputs raised by another unit; bus record fields stay carriers even when a sub-unit drives them (Step D) | LAsset p.2 (peripheral ports and system buses → secondary); SA-EDI printed p.2 / PDF p.10 ("Attack Point: an access location or means through which a threat can be realized against an asset"); SA-EDI printed p.14 / PDF p.22 (§7.4: Elements are the top-module influencers, the ports, "that can affect and/or observe the behavior of the asset"); P3164 p.7 (ports are "the attack surface"); P3164 p.12 (the Direction Select port is the attack point and the mux gates are the asset); SAIF p.2 (Example 2: the execution state that restricts access is secondary) | |
| R22 (A2) | Copies and parts: copies, slices, indexed reads of an array stored in this file, gated or multiplexed versions, merges of several holders, delayed copies, synchronisers, and serial-line ports or sub-unit connections carrying a value stored in this file (Step D) | LAsset p.2 ("carry the data of the primary asset, either fully or partially"); SAIF p.3 (§III.A: components in the fan-out of a primary asset are where secondary assets are found) | Limiting indexed reads to arrays in the file fixes C8. That a merge is a partial carrier is reasoning from "partially". |
| R23 | Next-value helpers are secondary (Step D) | LAsset p.2 (signals carrying the primary's data are secondary) | Reasoning: a next-state signal is the value on its way into the holder. |
| R24 (A2) | Transient controls, now including operation codes and request attributes kept for one transfer or operation (Step D, Step B) | LAsset p.5 (Fig. 5: the write enable that "gates write access" is a secondary asset); LAsset p.4 (§III.B: influencing signals are secondary); P3164 p.22 (expected behaviour is not a "yes"); SAIF p.2 (Example 2) | Fixes C5. |
| R25 (A2) | Bookkeeping: pointers, bit counters, prescaler ticks, and state machines that only step through phases. A state register holds an asset when it says who owns or may use something, or which mode is in force (Step D) | SAIF p.2 (FSM states can be secondary; Example 2); SAIF p.6 (Table II: state and decoded-instruction registers come out as secondary assets of the program counter); P3164 p.19 (CSA can mark every internal block, giving false positives); SA-EDI printed p.10 / PDF p.18 (Table 2: "FSM, control register" under the Control type); P3164 p.9 (integrity question: state "that need[s] to be immutable during certain operations or modes") | The split between step state and ownership or mode state is reasoning that reconciles SAIF with SA-EDI (D2). |
| R26 | Mode and privilege state is primary where this module keeps it (Step B) | SAIF p.2 ("configuration bits for operational and privilege modes" listed with primary assets); P3164 p.9 (undermined-behaviour question) | "Where this module keeps it" comes from R38. |
| R27 | Derived combinational status is secondary; stored status records that software acts on are primary (Step D, Step B) | P3164 p.15 (status registers "may leak confidential information" → conceptual asset); Nath & Tan p.3 (status-signal pattern: integrity, or availability when wired to another module's control); LAsset p.2 (Fig. 2: as I read its colouring, the status-register block is marked as a primary asset) | The split is reasoning. The Fig. 2 reading depends on the figure's colours. |
| R28 | Attack check (Step E) | LAsset p.4 (§III.C.1: side channel, fault injection, secure-to-nonsecure leakage, unauthorized access, privilege escalation, hardware Trojan, denial of service; "assets without such scenarios are excluded") | |
| R29 (A2) | Chain check, now including a store against a sub-unit connection carrying the same value (Step E) | LAsset p.4 (§III.C.4, as R17) | |
| R30 (A2) | Sibling check, now including operand stores, read-outs of the same store, and every fault or error request of the module or its sub-units (Step E) | P3164 p.18 (both SRAM address signals get their own asset object "so it is explicit") | Reasoning: like elements are treated alike. The fault-request clause fixes C10. |
| R31 | Record check (Step E) | SA-EDI printed p.13 / PDF p.21 (§7.2.1 b and c); P3164 p.18 (combining or separating objects is a choice made explicit) | Unchanged. "Loaded by the same write" is my test for a single asset (risk F2 below). |
| R32 (A2) | Holder and coverage checks (Step E) | P3164 p.8 (a missed asset, a false negative, leaves a threat unidentified); LAsset p.3 (§III.A.3: RTL parsing exists "to ensure that LLMs do not overlook any of the parsed design elements") | |
| R33 | Names copied exactly (Step F) | SA-EDI printed p.12 / PDF p.20 (§7.2: Name "shall match its corresponding text in the source"); SA-EDI printed p.13 / PDF p.21 (Table 3: Name is case-sensitive) | |
| R34 | A single objective per element (Step F) | SA-EDI printed p.16 / PDF p.24 (§7.5.1 b: an APSO object has exactly one security objective) | By analogy. |
| R35 | Names are hints, confirmed by behaviour (Step A) | Nath & Tan p.2 ("sensible" names give partial keywords); Nath & Tan p.3 (§III.B: "simple name matching is insufficient") | |
| R36 | Elements that exist only under some build settings stay candidates (map legend) | SA-EDI printed p.15 / PDF p.23 (Table 5: configuration parameters are recorded with an asset, not used to drop it) | Reasoning: the reference describes the design, not a single build. |
| R37 | No list-size target; both error kinds weigh the same (The task) | TASK_BRIEF (precision and recall count equally); LAsset p.4 (§III.C: LLMs "lean toward listing a broad set") | |
| R38 (new) | Content value versus steering value. A steering value is this module's conceptual asset only when this module or a sub-unit keeps it as its own state, or when it is a reaction request generated here. One that arrives from another unit and is only used here is held in that unit, and its port is a carrier (Definitions, Step B, `held in another unit`) | SAIF p.2 (Example 2: the boot-versus-normal execution state that restricts access to the key register is a secondary asset; "configuration bits for operational and privilege modes" are primary); P3164 p.12 (the Direction Select input is the attack point; the gates it steers are the asset); LAsset p.5 (Fig. 5: a write enable is secondary); P3164 p.9 (integrity question: settings that must stay immutable belong to the IP that holds them) | Reasoning for the "kept as own state" boundary: a setting held here can be attacked here; a value only passing through to steer can be attacked here only as a carrier. This fixes C4 and C5. |
| R39 (new) | A sub-unit instantiated in the module is part of the module; "another unit" is outside it (Definitions) | LAsset p.4 (§III.B: primary assets "at the module level"); LAsset p.5 (Table II: for the AES-128 design, the primary assets are named at the top module and the sub-module signals are its secondary assets); Nath & Tan p.5 (Case 2: instantiated modules are traced to the top) | Needed so that `held in another unit` is not used for a value that rests in an instantiated sub-unit. |
| R40 (new) | `held_by` may be empty only for `forwarded`, `held in another unit` or `constant only`; otherwise name a holder or remove the item (Step C, Step E) | P3164 p.10 (§3.1.2: once conceptual assets are identified, "the next step is to identify structurally where these assets are in the design"); LAsset p.4 (§III.B: each conceptual asset is mapped to its structural RTL reference); P3164 p.10 ("No" to all → not an asset, for removal) | Fixes C1. |
| R41 (new) | Store versus delayed copy versus synchroniser (Step C) | LAsset p.2 and Fig. 2 (the register that captures the key from its port is the primary asset; elements that carry the data are secondary) | Reasoning from R11 and R22: a register that keeps a value under its own load condition is where the value rests; a register that copies another register on every clock only carries it. |
| R42 (new) | A store in this file comes before a sub-unit connection carrying the same value (Step C) | LAsset p.2 (the structural asset is the element that "directly stores" the value; internal signals that carry it are secondary); SA-EDI printed p.24 to p.25 / PDF p.32 to p.33 (the storing registers are the assets; the wires around them are not) | Reasoning: inside this file, the store is visible and direct, while the sub-unit connection is a wire carrying the stored value. Fixes C2. |
| R43 (new) | Reminder: execution units and co-processors (operand stores, or ports when nothing stores them; result; cipher key, block and state) (kinds of unit) | P3164 p.22 (Table 3, functional units: "Source and data registers", Confidentiality; GPR/FPR: registers); P3164 p.15 (AES input buffer and key are conceptual assets); LAsset p.5 (Table II: key, state and out of AES) | Recall aid; subject to Steps C to E. |
| R44 (new) | Reminder: units that only connect sub-units (kinds of unit) | LAsset p.5 (Fig. 5 and Table II, as R14); P3164 p.20 (instructions and data are a CPU's main conceptual assets) | Recall aid; subject to Steps C to E. |
| R45 (new) | Reading empty connection modes and record-level wiring (map legend) | MAP_FORMAT (`connections`: instance, formal, mode); input evidence C7 | A reading aid, not an asset rule. |

## Where the sources disagree, and what the prompt chooses

- **D1. Ports.** LAsset p.2 lists peripheral ports and buses as secondary. LAsset p.5 (Table II) and Nath & Tan p.5 treat
  module I/O ports as primary. A2 makes a port primary in four cases: it holds or produces the value; it is a content
  input that nothing stores (R15); in a module built from sub-units, it delivers a value from a sub-unit (R14); or it
  carries a content value into a sub-unit that never delivers it back (R14). Otherwise the internal holder wins. This
  is A1's choice, now stated per test.
- **D2. State machines.** SA-EDI printed p.10 lists "FSM" under the Control asset type. SAIF p.2 calls FSM states
  secondary. A2 keeps A1's split and states it as a single test (R25).
- **D3. Configuration registers.** The SA-EDI watchdog walk-through (printed p.24 to p.25) names only the timer and
  timeout registers. P3164 p.15 and SAIF p.2 include configuration. A2 includes configuration that the module keeps
  (R18, R38). Unchanged.
- **D4. Copies.** P3164 p.18 gives both SRAM address signals their own objects. LAsset p.2 makes carrying signals
  secondary. A2 keeps a single holder per chain (R17). Unchanged.
- **D5. Addresses and pointers.** P3164 p.13 and p.17 treat addresses as conceptual assets. Under LAsset's split, an
  address that picks which part of a primary is read helps expose it. A2 keeps addresses as steering values: carriers,
  or bookkeeping when stored (R25, R38). Unchanged.
- **D6. Status.** Derived status is secondary and stored status is primary (R27). Unchanged.
- **D7. Control inputs (new).** Nath & Tan p.3 treat single-bit control inputs as potential primary assets with an
  Availability objective. LAsset p.5 (Fig. 5) and SAIF p.2 (Example 2) treat such controls as secondary. A2 follows
  LAsset, the study the reference comes from (R38).
- **D8. Operands (new).** P3164 p.22 (Table 3) names source and data registers of functional units. LAsset p.5
  (Table II) names the AES module's input ports. A2 lists the operand stores when they exist, and the ports only when
  nothing stores the operand (R15, R43).

## What the rules should change on the tuning outputs (reasoning, not measured)

I scored nothing and saw no reference. This is what A2's rules imply for the A1 outputs I read. Use it as the
prediction to check after the next run.

- **Multiply/divide unit**: adds the operand stores (`mul.dsp_x`, `mul.dsp_y`, `div.rs2_abs`) to the three result
  registers.
- **Processor top**: adds the sub-unit read-outs (the control/status read data, the other sub-units' status read-outs,
  the register-file read ports), plus the fault and error signals of the other sub-units as siblings of the protection
  fault. The merged read-back word and the bus record fields stay secondary.
- **Two-wire controller and random number generator**: drop the queue read-out connections and keep the shift
  registers.
- **Bus file**: drops the latched atomic operation code.
- **Other modules**: lists unchanged. Some `conceptual_assets` items with empty holders disappear, with no effect on
  `assets`.

## What this breaks, what would falsify it, and what to read after the next run

**Comparability.** A2 runs must go to their own output directory and must not be pooled with A1 runs in any metric.
The `assets` shape is unchanged. The `analysis` shape changed: a new `holder_case` field, and a new
`field_of_listed_record` role. Any script that reads A1's `analysis` keys needs updating before it reads A2's.

**Measurements to read.** Read precision and recall separately, per module and pooled. For precision, the denominator
is the listed elements; for recall, the reference entries. Both are exact counts. Then split false positives and
misses three ways:

- by element class: input port, output port, clocked signal, combinational signal, whole record, record field;
- by `holder_case`, so that each Step C test can be judged on its own;
- by module, for the four modules named in the prediction above.

**What would falsify each change:**

- **F1 (content inputs and operand stores, R15, R43).** If the operand stores added in execution units are false
  positives (precision there drops, recall there does not rise), the reading of P3164 Table 3 does not match this
  reference.
- **F2 (record rule, R31, unchanged).** If false positives are whole records while the misses are their fields (or
  the reverse), the record test points the wrong way.
- **F3 (in-file store before sub-unit connection, R42).** If recall drops in communication or security peripherals
  and the new misses are queue read-outs, the precedence is backwards for this reference.
- **F4 (module-level read-outs, R14, R44).** If the read-outs added in the processor top are false positives, the
  module-level reading of LAsset Fig. 5 and Table II is too wide.
- **F5 (steering inputs, R38).** If misses concentrate on steering inputs (privilege tags, incoming interrupt or reset
  requests), the steering-is-carrier rule is too strict.
- **F6 (decisiveness).** Run each module several times and compare the element lists between runs. If A2 does not
  vary less than A1 on the modules named above, the ordered tests are not decisive enough. Check `holder_case`
  disagreements first.

## Compliance with the brief

- **Rule 1 (no identifiers).** The prompt contains no name from the processor or its files. Its examples use invented
  names (`demo_signer`, `demo_link`, `demo_top` and their elements). Words that are bare element names in this
  processor's files are avoided in the new text ("content value", "locking", "launch", "completion"). Processor
  element names appear only in this rationale's change log, as evidence.
- **Rule 2 (no quotas).** The prompt has no list-size target, no proportion and no digit. The number word "one"
  appears only in plain descriptions, none of which sets a size or proportion. A1 used it in "one hardware module",
  "one write" and "one cycle later", and A2 adds "one transfer or operation". The contract placeholder "one or two
  sentences" is the brief's own text, reproduced verbatim.
- **Rule 3 (no comments).** The prompt only states that comments were removed.
- **Rule 4 (sources).** Every rule that decides asset or not-asset is in the table above with source and page.
  Derivations are labelled reasoning.
- **Rule 5 (self-contained).** The map legend, definitions, tests and examples are all inside the prompt.
- **Output contract.** Reproduced verbatim. The `analysis` key sits between `module` and `assets`, as the brief
  allows.
- **Blindness.** I read only files listed in the task message. I ran no command and did not search, list or glob. The
  critic report path did not exist, and I did not look for it elsewhere. I reread LAsset Table I (p.5), which reports
  reference-list sizes for some of this processor's units. I did not use those sizes for any rule or expectation, and
  the prompt has no list-size target.

## Files read in this session

- E:/jobs/ff/test/Prepoison_subset/blind_agent/TASK_BRIEF.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/MAP_FORMAT.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/prompts/A1/prompt.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/prompts/A1/rationale.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/critic/A1/report.md (attempted; the file does not exist)
- The fifteen A1 outputs under E:/jobs/ff/test/Prepoison_subset/blind_agent/runs/tuning/A1/r0/
- E:/jobs/ff/test/Prepoison_subset/blind_agent/inputs/tuning/neorv32_cpu_cp_muldiv.txt (RTL part)
- E:/jobs/ff/test/Prepoison_subset/blind_agent/inputs/tuning/neorv32_cpu.txt (RTL and map, up to map line 516)
- E:/jobs/ff/test/Prepoison_subset/blind_agent/inputs/tuning/neorv32_sys.txt (RTL part)
- E:/jobs/ff/test/Prepoison_subset/blind_agent/inputs/tuning/neorv32_twi.txt (RTL around the engine and the queues)
- E:/jobs/ff/2601.02624v2.pdf (pp. 1 to 6)
- E:/jobs/ff/IEEE_P3164_Asset_Identification.pdf (pp. 7 to 24)
- E:/jobs/ff/SAIF_Automated_Asset_Identification_for_Security_Verification_at_the_Register_Transfer_Level.pdf (pp. 1 to 6)
- E:/jobs/ff/2502.04648.pdf (pp. 1 to 7)
- E:/jobs/ff/Accellera_SA-EDI_Standard_v10.pdf (PDF pp. 10, 18 to 24, 31 to 38)
