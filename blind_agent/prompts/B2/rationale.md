# Rationale for prompt B2 (threat-first, revision of B1)

## The idea, unchanged from B1

- An element is a primary asset when an attacker would go after it **directly**: read it, change it, or block it. The harm must be about that element's own value.
- Everything that only helps the attacker get there is secondary or an attack point, and is not listed. That covers wires that move the value, operand and staging copies, strobes, selects, addresses, handshakes, clocks, resets and forwarded bus fields.
- The executor asks the P3164 questions to get conceptual assets. It finds each one's home with a home rule and inclusion labels. Then it runs a one-sentence threat test. Every map element ends up either listed or in a named exclusion group.

## What this revision is based on

- **The critic report was not available.** `blind_agent/critic/B1/report.md` did not exist when I read it. I did not search for it (blindness rule). The change log below therefore rests on my own review. I compared the 15 executor outputs in `runs/tuning/B1/r0/` with B1's own definition. I checked the RTL behind each doubtful call in these input files: random generator, bus, debug transport, CPU top, system clock/reset, serial peripheral interface (SPI), and the buffer design file.
- **Sources re-read in this session** (every page cited below was read in this session): LAsset pp.1-7; SAIF pp.1-7; Nath & Tan pp.1-7; P3164 pp.7-23; SA-EDI PDF pp.10-11, 18-24, 30-37.
- **Not used:**
  - LAsset Table I (p.5): per-module golden counts for this processor.
  - LAsset Fig. 5 (p.5): an output snippet on this processor.

  Both are about this processor. The brief allows LAsset only for definitions and for examples on other designs, and the prompt may hold no quotas. B1 cited Fig. 5 for two points (a control/status register value is primary; its write strobe is secondary). B2 drops that citation and grounds both points on other sources (rows S5 and F2 below). The processor worked example no longer credits LAsset.

## Page conventions

- LAsset = `2601.02624v2.pdf`, PDF pages (pp.1-7).
- P3164 = `IEEE_P3164_Asset_Identification.pdf`; printed page = PDF page.
- SA-EDI = `Accellera_SA-EDI_Standard_v10.pdf`; printed page, with the PDF page in brackets (PDF = printed + 8).
- Nath & Tan = `2502.04648.pdf`, PDF pages (pp.1-7).
- SAIF = `SAIF_..._Register_Transfer_Level.pdf`, PDF pages (pp.1-7).

## Decision rules and their sources

Rows marked **new** or **changed** are B2 edits. The change log gives the evidence for each one.

### Definitions and adversary model

| ID | Prompt text | Source and page |
|---|---|---|
| D1 | Asset = something of value used, produced or protected | SA-EDI p.2 [PDF 10] (Asset); SA-EDI p.12 [PDF 20] (an asset can be a port, module, register or other object) |
| D2 | C / I / A objectives | SA-EDI p.3 [PDF 11] (Security Objective); LAsset p.2 (CIA) |
| D3 | Conceptual vs structural asset | P3164 p.8; LAsset p.2 |
| D4 | Primary = direct target | LAsset p.2 ("components that serve as the direct target of an attack"); SAIF p.2 ("definitive target for protection") |
| D5 | Secondary = helps reach a primary. **Changed:** the examples now include staging copies and operand/partial/round values. | LAsset p.2 (internal signals/registers that carry the primary's data "fully or partially"; the AES Enc/Dec engine and output buffer are secondary); LAsset p.5 Table II (per-round copies secondary); SAIF p.2 (infrastructure that closely interacts with primary assets); Nath & Tan p.1 (secondary assets propagate and handle primary assets) |
| D6 | Attack point = way in, not a target | SA-EDI p.2 [PDF 10] (Attack Point, Attack Surface); SA-EDI p.14 [PDF 22] (Element objects: top-module ports an adversary uses to affect the asset); P3164 p.7 (ports are the attack surface) |
| D7 | **New:** pacing pulse (definition only) | Reading aid; used by S9 and F1 |
| A1 | Adversaries: software, external pins, debugging/test misuse, glitch and side channel, Trojan | LAsset p.4 (seven attack classes); SAIF p.3 (bus snooping, test/debug structures, unprotected communication, third-party IPs, glitching) |
| A2 | "A glitch or Trojan can hit any wire; that alone never makes an element primary" | Reasoning on LAsset p.2 (direct target). Without it every element passes the LAsset p.4 attack-scenario check. |
| A3 | "Normal operation is not an attack" | P3164 p.22 (a cache replacing a line on a store "is expected behavior and should not result in a 'yes'") |

### Step B and Step C

| ID | Prompt text | Source and page |
|---|---|---|
| K1 | **New:** module kinds (keeper, mover, calculator, guard, wiring file) | Reading aid, not a decision rule. It names the trigger of S3 (calculator rule) and the sub-unit output case of H3. The kinds come from the sources' own examples: SRAM keeper (P3164 p.16), AES calculator (LAsset p.5, P3164 p.14), watchdog guard (SA-EDI p.22 [PDF 30]), shared bus mover (SAIF p.2). |
| Q1 | The four questions | P3164 p.9 |
| Q2 | Override inputs are attack points; the elements they corrupt are assets | P3164 p.13 (Addr_OvR forces a wrong coefficient, so the Coeff ROM is the asset); P3164 p.12 (Direction Select is the attack point); SA-EDI p.23 [PDF 31] (debug signals override the counter) |
| Q3 | No to all questions = no asset | P3164 pp.9-10 |

### Step D: home rule (new in B2)

| ID | Case | Source and page |
|---|---|---|
| H1 | Own register: a register or array of this file keeps the value | LAsset p.2 (the Key Register is a structural asset because it "directly stores" the key); SA-EDI p.24 [PDF 32] (the timer register is the asset) |
| H2 | First holder: the store is a constant or sits in a sub-unit defined elsewhere | Carried from B1. MAP_FORMAT.md (constants are not elements); SA-EDI p.12 [PDF 20] (the Name must match the RTL). Choosing the first register is reasoning. |
| H3 | **New.** Sub-unit output: in a wiring file, the signal that carries a value out of the sub-unit that keeps it. Limited to values a sub-unit keeps as its record of the machine. Payload passing through is judged at the boundary. | P3164 p.10 (structural assets are the RTL that "stores and transports its value (e.g., reg and wire)"); LAsset p.3 and p.4 Algorithm 1 line 5 (primary assets are found per module, from that module's parsed elements); SA-EDI p.12 [PDF 20] (an asset can be "another object in the design"). The limit to kept values follows LAsset p.2 (internal signals that carry primary data are secondary). The list of kept values comes from P3164 pp.21-22 and Table 3 (instructions, PC, register contents) and SAIF p.2 (configuration bits for operational and privilege modes). |
| H4 | **New.** Single holder: along one path, credit the register where the value is complete and kept longest. Staging copies are STAGING. | LAsset p.4 ("Along each path, the most tamper-prone asset is designated as the primary asset, while the remaining assets are treated as secondary"). "Complete and kept longest" is my reading of "most tamper-prone": the longest window for a glitch or a probe. That part is reasoning. |

### Step D: inclusion labels

| ID | Label and what it keeps | Source and page |
|---|---|---|
| S1 | STORE: keys, seeds, random values, raw entropy, buffered/sent/received payload, code, memory contents. **Changed:** "computes" removed; raw entropy and the finished random value are separate homes. | SAIF p.2 (keys, random numbers and seeds, IDs, private user data are primary); P3164 p.8 (a buffer that stores the data); P3164 p.17 (SRAM array, data-in and output registers); P3164 p.13 (GNG seed path needs confidentiality); SA-EDI p.15 [PDF 23] (an RNG entropy source with no port can be an asset); SA-EDI p.10 [PDF 18] Table 2 (Secret, Code/Data) |
| S2 | STORE includes a serial shift register when no other register of this file holds that word | Single-holder case (H4) applied to movers. P3164 p.8 ("a buffer that temporarily stores the data as it is entered into the IP") |
| S3 | **New.** Calculator rule: credit the kept secret and the outer operand and result ports. Operand copies, partial results, round values, running totals and the result on its way to the port are INTERMEDIATE. Secrets the module creates are exempt. | LAsset p.5 Table II (AES-128: key, input block and final output primary; key and state copies in each round, round outputs and table lookups secondary); LAsset p.2 (Enc/Dec engine and output buffer secondary; Key Reg primary). Exemption for created secrets: P3164 p.13 (the GNG seed blocks are assets); SA-EDI p.15 [PDF 23] (entropy source). |
| S4 | SETTING: software-written configuration, each field | SAIF p.2 ("configuration bits for operational and privilege modes"); P3164 p.9 Q2 (configuration settings that must stay immutable); P3164 p.15 (AES configuration registers need integrity); SA-EDI p.10 [PDF 18] Table 2 (Control: "FSM, control register"); SA-EDI p.16 [PDF 24] (a lock bit protects a register's integrity) |
| S5 | SETTING excludes registered strobes | P3164 pp.16-18 (the SRAM control register that registers CE/WE/OE is not named an asset) |
| S6 | CORE: PC and the executing instruction | SAIF p.2 (PC integrity in a micro-controller) and p.5 (PC is the primary asset in Case Study I); P3164 pp.21-22 (instructions are a conceptual asset) |
| S7 | CORE: kept and enforced privilege/mode, debugger-stopped status, authentication status | SAIF p.2 (privilege-mode configuration bits); P3164 p.9 Q4 (privileged modes and bypass) |
| S8 | CORE: main count of a timer, watchdog or bus-expiry monitor | SA-EDI p.24 [PDF 32] (the timer register is an asset because an adversary would modify it to prevent the timeout); SA-EDI p.10 [PDF 18] Table 2 (Critical: timers/counters) |
| S9 | **New.** CORE: main counter or sequence register of a generator of the system's reset or pacing pulses | SA-EDI p.10 [PDF 18] Table 2 (Critical asset type: "Material that is critical for proper functionality. Without this asset, the IP would not be able to function"; examples "Timers/Counters, clock generators"); SA-EDI p.25 [PDF 33] (the register that asserts the timeout is an asset) |
| S10 | CORE: main FSM register | SA-EDI p.10 [PDF 18] Table 2 (Control: FSM); P3164 p.9 Q2 (state that must stay immutable) |
| S11 | **Changed.** CORE pointer: only an address or index register that picks a word of a store inside this module. Request-address registers are LEVER. | P3164 pp.17-18 (the SRAM address register addresses the controller's own array); P3164 p.13 (the address into the GNG's own coefficient ROM). Both source examples address the IP's own store. |
| S12 | CORE exclusions: pacing counters, delayed copies, synchronizers | LAsset p.2 (registers that carry the primary's data are secondary); SAIF p.2 Example 2 (FSM state that only gates access is secondary). The split is reasoning (B1 Tension 2, kept). |
| S13 | DECISION: interrupt, error/exception/violation, grant/deny, expiry/reset request. **Changed:** the generated outputs of a reset or pacing generator are added; the "fresh random value ready" item is removed; a counter bit is not a DECISION. | SA-EDI p.25 [PDF 33] (timeout-assertion register: blocking it or asserting it constantly is denial of service); SA-EDI p.16 [PDF 24] and p.29 [PDF 37] (a reset output must not be gated; Availability); Nath & Tan p.3 (status signals: Availability when they drive another module's control); P3164 p.9 Q3; LAsset p.4 (denial of service). Generator outputs: SA-EDI p.10 [PDF 18] Table 2 (clock generators are Critical). Removal: B1 gave no source for the "fresh value ready" item, and it fails B1's own threat test (row E2). |
| S14 | BOUNDARY: outer-entity port carrying a STORE value, a calculator's operands, or the main product. **Changed:** a port wired into a sub-unit counts even when the map says FORWARDS; the serial payload pins of a debugging port are named. | LAsset p.5 Table II (the outer key, input and output ports of AES are primary; that top does its work in sub-modules); Nath & Tan p.1 (elements that "communicate with the external peripherals" are primary); Nath & Tan p.5 Case 1 and Case 2 (candidates are rooted at TOP-module I/O); P3164 p.19 (PIO: the information that goes in and comes out; the points where it is observed or influenced become structural assets); P3164 p.7 (a port that can observe an asset violates confidentiality) |
| S15 | BOUNDARY exclusions: inner-entity ports, port-to-port fields, settings-only bus payload | LAsset p.5 Table II (sub-module copies secondary); SAIF p.2 Example 1 (a bus that carries and routes is secondary); SA-EDI p.25 [PDF 33] (the watchdog write-payload input is an attack point); SA-EDI p.27 [PDF 35] (the watchdog output port carried no security objective) |
| S16 | ATTRIBUTE: requester privilege/security/debugging status consumed by an access check | SAIF p.2 (privilege-mode bits); P3164 p.9 Q4; LAsset p.4 (privilege escalation, unauthorized access) |

### Step E: threat test

| ID | Prompt text | Source and page |
|---|---|---|
| E1 | One threat sentence; no scenario = drop | LAsset p.4 (Attack Scenario Analysis: "assets without such scenarios are excluded") |
| E2 | Harm must concern the element's own value; otherwise credit the other element. **Changed:** "it announces that a new value is ready" added as a lever example. | LAsset p.2 (primary = direct target; secondary = exposes the primary indirectly) |
| E3 | Unauthorized action only | P3164 p.22 |
| E4 | **Changed** tie-break: homes and boundary crossings are kept; moving, staging, selecting, gating or intermediate elements are dropped | Combines D5, H4, S3 and S14 |

### Step F: exclusion labels

| ID | Label | Source and page |
|---|---|---|
| F1 | CLOCK-RESET. **Changed:** pacing pulses received from elsewhere and reset requests that only feed a reset are included. The generator exception now covers pacing pulses. A serial-protocol clock line is a LEVER. | Nath & Tan p.6 ("we did not consider 'Clock' and 'Reset' signals"); SA-EDI p.25 [PDF 33] (clock and reset are Element ports, not assets); MAP_FORMAT.md (SEQUENCES = the clock whose edge the assignment waits for). Generator exception: S9, S13. |
| F2 | LEVER. **Changed:** mode flags and override inputs are named; registered command codes and request-address registers are added; a debugging port's payload pins go to BOUNDARY, its mode-select and clock pins are levers. | SA-EDI p.14 [PDF 22] (ports that affect the asset are access points); SA-EDI p.25 [PDF 33] (read/write enables, address, write payload and debug inputs are Element attack points); SA-EDI p.23 [PDF 31] (debug signals override the counter); P3164 pp.17-18 (mode, CE, WE, OE, ZZ inputs are not assets); P3164 p.12-13 (the override input is the attack point); SAIF p.2 (the address decoder is secondary). The write strobe of the control/status registers being secondary now rests on SA-EDI p.25 [PDF 33] (i_wen is an attack point) instead of LAsset Fig. 5. |
| F3 | CARRIER | LAsset p.2; LAsset p.5 Table II; LAsset p.4 (one primary per path); Nath & Tan p.1 |
| F4 | **New.** STAGING | H4 |
| F5 | **New.** INTERMEDIATE | S3 |
| F6 | BOOKKEEPING. **Changed:** new-value strobes added. | LAsset p.2; P3164 p.19 (CSA tends to mark every internal block, giving false positives); LAsset p.4 (LLMs "lean toward listing a broad set of possible security and non-security assets") |
| F7 | FORWARD. **Changed:** port to port only. | SAIF p.2 Example 1 (the bus that carries and routes is secondary); LAsset p.2 (system buses are secondary). The narrowing is needed so F7 does not contradict S14 (LAsset p.5 Table II). |
| F8 | UNUSED | P3164 pp.9-10; P3164 p.11 (gates that "do not leak any information" give a No) |
| F9 | RECORD-WHOLE | SA-EDI p.13 [PDF 21] 7.2.1 c-d (whole array unless a range is named; each range its own object); P3164 p.18 (two address signals kept as separate objects "so it is explicit"); SA-EDI p.12 [PDF 20] |
| F10 | Never output constants, generics, variables, labels, instances, slices | MAP_FORMAT.md; SA-EDI p.12 [PDF 20] |

### Steps G and H

| ID | Prompt text | Source and page |
|---|---|---|
| G1 | Same role, same decision. **Changed:** siblings in a wiring file added. | SA-EDI p.13 [PDF 21] 7.2.1 d; P3164 p.18; LAsset p.4 (self-consistency checks in refinement) |
| G2 | No double credit through copies, except holder + boundary port and decision + delivering output | LAsset p.4 (one primary per path); the exception follows B1 Tension 1 (kept) |
| G3 | Accounting of every map element | LAsset p.3 (parsers extract every element so "LLMs do not overlook any of the parsed design elements") |
| G4 | Copy names exactly | SA-EDI p.12 [PDF 20]; SA-EDI p.15 [PDF 23] Table 5 (case-sensitive); TASK_BRIEF.md |
| G5 | Objective choice. **Changed:** generated pulses added under Availability. | SA-EDI p.3 [PDF 11]; LAsset p.5 Table II (key C, final output A, input block C); Nath & Tan p.3 (data C; configuration A and I; status A or I); SAIF p.2 (PC integrity); SA-EDI p.29 [PDF 37] (reset output: Availability) |

### Worked examples (all from the sources' own designs)

- Watchdog: SA-EDI pp.22-29 [PDF 30-37]. The SETTING sentence is labelled in the prompt as our rule, not the standard's: the standard lists only the timer and the timeout-assertion register (p.27 [PDF 35]). Its basis is S4. The words changed from B1 (row C12).
- SRAM controller: P3164 pp.16-18.
- **New.** Gaussian noise generator: P3164 pp.12-13. It supports S1 (generator secrets), S11 (address into the module's own ROM) and F2 (the override input is the attack point).
- **Changed.** AES core: LAsset p.2 and p.5 Table II. It now states that the key register is primary and that the Enc/Dec block and the output buffer are secondary. This is the basis of S3.
- Shared bus: SAIF p.2 Example 1.
- **Changed.** Processor core: P3164 pp.21-23 (Table 3; the cache "No" on integrity); SAIF p.2 and p.5. The LAsset attribution was removed (it rested on Fig. 5).

## Change log

Each entry gives the change, the output evidence, and the RTL check. The evidence is from my own review, because the critic report was missing. "Expected effect" is reasoning, not a measurement.

**C1. Calculator rule and INTERMEDIATE label (S3, F5, D5, E4).**
- Evidence. In `neorv32_cpu_cp_muldiv` the executor listed six internal registers as STORE: `mul.dsp_x`, `mul.dsp_y`, `mul.prod`, `div.rs2_abs`, `div.quotient`, `div.remainder`. It also listed `rs1_i`, `rs2_i`, `res_o`. `neorv32_cpu_cp_cfu` lists `xtea.opa`, `xtea.opb`, `xtea.sum`, `xtea.res` next to `rs1_i`, `rs2_i`, `result_o`. `neorv32_bus` (`neorv32_bus_amo_rmw`) lists `arbiter.rdata`, `arbiter.wdata`, `alu_res` next to four payload ports.
- Diagnosis: this is B1's fault, not the executor's. B1's STORE text said "payload words the module ... computes", while B1's own AES example said per-round copies are secondary. RTL check: `alu_res` is a clocked register (bus input, RTL lines 833-847), so the executor applied B1's register test correctly.
- Expected effect: those 13 elements move to INTERMEDIATE. The ports stay.

**C2. Single-holder case and STAGING label (H4, F4).**
- Evidence. `neorv32_debug_dtm` lists `tap_reg.dmi` and `dmi_ctrl.wdata` as STORE. RTL lines 266-267 copy slices of `tap_reg.dmi` into `dmi_ctrl.addr` and `dmi_ctrl.wdata`. `dmi_ctrl.rdata` (line 274) goes back into `tap_reg.dmi` through `dmi_nxt` (line 229).
- Diagnosis: B1 Step G already forbade double credit through copies. The executor did not see a slice copy as a copy, and B1 gave no way to choose which copy to keep.
- Expected effect: `tap_reg.dmi` moves to STAGING; `dmi_ctrl.wdata` and `dmi_ctrl.rdata` stay. The serial transmitter/receiver shift registers in `neorv32_uart`, `neorv32_spi` and `neorv32_twi` are unchanged: their buffer queues are sub-units outside the file, so no other register of the file holds the word.

**C3. FORWARD is now port to port; BOUNDARY accepts ports wired into a sub-unit (F7, S14).**
- Evidence. In `neorv32_cpu` the map marks every outer port field `handling: FORWARDS`. Each port is wired straight to a sub-unit instance (RTL lines 196-197, 394-395, 447-448). Under B1's FORWARD text all of them were excluded. Under B1's BOUNDARY text, and the AES example, the payload ones qualified. The executor chose BOUNDARY for `ibus_rsp_i.data`, `dbus_rsp_i.data`, `dbus_req_o.data`, `icc_tx_o.dat`, `icc_rx_i.dat`.
- Diagnosis: two B1 rules contradicted each other in a wiring file.
- Expected effect: no change in that output; the call is now rule-backed and repeatable. In bus switches the port-to-port fields stay FORWARD.

**C4. Sub-unit output case for wiring files (H3, G1).**
- Evidence. In `neorv32_cpu` the executor listed wires as homes: `rs1`, `rs2`, `rs3` (STORE) and `ctrl.pc_cur`, `ctrl.cpu_priv`, `ctrl.lsu_priv`, `ctrl.cpu_debug`, `frontend.instr` (CORE). The file declares only signals and has no process (RTL lines 105-124). B1's STORE and CORE texts required a register, and B1's first-holder rule had nothing to point at.
- Diagnosis: the executor improvised, inconsistently. It put `csr_rdata` (the control/status read value, RTL line 263) in CARRIER, though B1's own processor example names control/status register values as assets.
- Expected effect: the listed wires stay. `csr_rdata` is likely added, and possibly its siblings that carry status values out of other sub-units. Which siblings get added is uncertain; G1 says to decide them alike.

**C5. "Fresh random value ready" removed from DECISION; new-value strobes are levers (S13, E2, F6).**
- Evidence. `neorv32_trng` lists `sample_cnt` as DECISION. RTL line 367 drives `valid_o` from the top bit of `sample_cnt`, and line 138 wires it to the pool's write strobe.
- Diagnosis: B1's DECISION item allowed this. But the harm ("half-filled bytes enter the pool") reaches the random byte through another element, which fails B1's own Step E. B1's rationale gave no source for that DECISION item.
- Expected effect: `sample_cnt` moves to BOOKKEEPING.

**C6. Reset or pacing-pulse generators (S9, S13, F1, G5). This changes B1's position.**
- Evidence. In `neorv32_sys` (`neorv32_sys_clock`) the executor listed `clk_en_o` (BOUNDARY) and `cnt` (CORE). B1's text excluded clock-enable pulses (CLOCK-RESET) and rate counters (not CORE). The executor went against B1's wording.
- Decision: B2 sides with the executor's reading because SA-EDI Table 2 (p.10 [PDF 18]) puts clock generators under the Critical asset type. B1 had excluded clock-enable pulses everywhere. B2 still excludes them as inputs but keeps them as a generator's product.
- Expected effect: no change in that output; it is now consistent with the text.

**C7. CORE pointer limited to the module's own store (S11, F2).**
- Evidence 1. `neorv32_debug_dtm` lists `dmi_ctrl.addr` as CORE. It is the address of a request sent to another unit (RTL line 285 drives `dmi_req_o.addr`).
- Evidence 2. `neorv32_spi` lists `rtx_engine.cs_ctrl` as CORE. It is loaded from a command word in the transmit queue (RTL line 290) and only picks which chip-select pin goes low (line 354).
- Diagnosis: B1's wording ("stored pointers or address registers that decide where protected contents are written or read") was too loose. Both source examples address the IP's own store.
- Expected effect: both move to LEVER. The cache refill address fields (`ctrl.tag`, `ctrl.idx`, `ctrl.ofs`) stay CORE because they pick blocks of the cache memory inside the same file.

**C8. CLOCK-RESET follows the map; serial-protocol clocks are levers (F1).**
- Evidence: `neorv32_twi` puts `twi_scl_i`, `twi_scl_o` and the `io_con.scl_*` fields in CLOCK-RESET, and `neorv32_spi` puts `spi_clk_o` there.
- Expected effect: they move to LEVER. The scored list is unchanged; the exclusion is now attributable.

**C9. LEVER and BOUNDARY wording for debugging ports (F2, S14).**
- Evidence: `neorv32_debug_dtm` lists `jtag_tdi_i` and `jtag_tdo_o` as BOUNDARY, while B1's LEVER named "debugging and test override inputs". Two B1 rules could claim the same pins.
- Decision: kept the executor's reading. It follows B1 Tension 1. LEVER now covers mode flags and override inputs; payload pins go to BOUNDARY.
- Expected effect: no change.

**C10. Module kinds in Step B (row K1).** These give the calculator rule and the sub-unit output case a defined trigger. They are not a decision rule.

**C11. Attribution aids.**
- The `reason` bracket may carry "first holder" or "sub-unit output".
- `not_listed` gains STAGING and INTERMEDIATE.
- No scored field changes.

**C12. Words that equal identifiers removed.**
- These words were replaced: "fault", "timeout", "enable", "state", "engine", "start", "clear", "halted", "busy", "tag" (now "label"), "bypass".
- Each equals a signal or record-field name in the tuning inputs. Examples: a `fault` field and an `engine` record in the CPU top and the two-wire module; `timeout`, `enable` and `state` names in the watchdog, random generator and bus files.
- B1 used them. I do not know whether the code check ignores common English words, so I removed the exposure. No rule changed.
- Words kept: "mode" (also the map's own field name, needed to explain the map), "key", "register", "signal", "core", "cache".

**C13. Worked examples.**
- Added: the GNG example.
- AES: now states the key register is primary and the engine and output buffer are secondary.
- Processor: the LAsset attribution was removed.

### Positions that changed from B1 (flagged)

1. Calculator intermediates: B1 listed them; B2 drops them (C1).
2. A generator's pacing-pulse outputs and counter: B1 excluded them by its text; B2 lists them (C6).
3. "Fresh random value ready": B1 called it a DECISION; B2 calls it a lever (C5).
4. Request-address and command registers: B1's wording made them CORE; B2 makes them LEVER (C7).
5. FORWARD: B1 used any FORWARDS field; B2 uses port to port only (C3).

### Kept from B1, and why (reasoning, not measured)

- **Holder plus boundary port for payload that is moved or kept.** The sources disagree:
  - P3164 pp.16-17 lists the SRAM data-in and output registers.
  - LAsset p.2 calls the AES output buffer secondary, and LAsset Table II makes the outer ports primary.
  - SAIF p.5 treats a serial transmitter port as an untrusted observation point.

  Suppose the reference keeps only one of the pair. Listing both then costs precision on that pair but keeps recall. Guessing one and missing costs both precision and recall. So B2 keeps the pair for movers and keepers. For calculators it follows LAsset, because the AES example there is a close analogue (C1).
- SETTING fields, interrupt outputs, main FSMs, ATTRIBUTE inputs, the first-holder case, and the accounting are unchanged.

## Tensions, updated

- **T1 ports vs attack points:** kept as in B1. B2 adds that a port wired into a sub-unit counts (C3).
- **T2 FSMs:** kept.
- **T3 status flags:** kept, plus new-value strobes (C5).
- **T4 pointers:** narrowed (C7).
- **T5 (new) holder vs port for payload:** see "Kept from B1".
- **T6 (new) wiring files.**
  - What the sources say: P3164 p.19 says PIO starts from the interface, and P3164 Table 3 names internal structures. LAsset p.2 calls internal carrier signals secondary. Nath & Tan p.5 roots candidates at top-module ports.
  - Choice: in a wiring file, credit the outer payload ports (BOUNDARY) and, once per kept value, the signal that leaves the sub-unit that keeps it (H3). Payload passing through gets ports only.
  - This is reasoning. Row "H3" in the measurement table below can falsify it.

## Facts about the B1 outputs used above (hand count, not a script)

These are the listed elements in the 15 B1 r0 outputs, counted by hand from the JSON files read in this session. The counts are exact for those files. No command could be run (blindness rule), so no script checked them.

| Module | Listed |
|---|---|
| bus | 15 |
| uart | 21 |
| spi | 18 |
| twi | 11 |
| cache | 15 |
| debug_dtm | 11 |
| cpu_cp_muldiv | 10 |
| cpu_pmp | 6 |
| trng | 5 |
| cpu | 16 |
| wdt | 9 |
| cpu_cp_cfu | 10 |
| imem | 7 |
| sys | 6 |
| hwspinlock | 2 |
| **Total** | **162** |

The elements that C1, C2, C5 and C7 are expected to move out of `assets` number 17 (13 + 1 + 1 + 2), all named in the change log. C4 may add one or more. This is a prediction about the executor, not a measurement. Precision and recall cannot be stated, because I have no reference.

## Dry run on the two design inputs (reasoning only)

- **Buffer module** (re-read in this session, RTL lines 18-232). Kind: keeper.
  - STORE: `fifo_mem`, `fifo_reg` (siblings under build options).
  - BOUNDARY: `wdata_i`, `rdata_o`.
  - CORE: `w_pnt`, `r_pnt`. `w_pnt` indexes the module's own array (RTL lines 150, 184). `r_pnt` feeds the read index through `r_nxt` and `r_pnt_ff` (lines 83, 210, 213), and it is `w_pnt`'s sibling. Both survive the narrowed pointer rule.
  - CARRIER: `r_pnt_ff` (a registered copy of `r_nxt`, line 210).
  - Same six elements as B1's dry run.
- **Boot ROM module:** not re-read in this session. B1's dry run (first holder plus the outgoing payload field) is not affected by any B2 change.

## What this revision breaks

- **Comparability.** B2 must write to its own run directory. Never mix B1 and B2 runs in one metric. The scored fields (`module`, `assets`) keep their shape. In `not_listed`, B2 splits B1's CARRIER into CARRIER, STAGING and INTERMEDIATE. To compare per-label losses with B1, sum the three.
- **Reason parsing.** Any parser that reads the label from the `reason` bracket must split on the comma.

## What would falsify each change, and what to read after the next run

Each measurement needs the reference and the B2 outputs. Precision and recall are named in each row.

| Change | Falsified if | Measurement |
|---|---|---|
| C1 calculator rule | reference entries often land in INTERMEDIATE | **recall loss**: number of reference entries found in INTERMEDIATE, per calculator module; **precision** of BOUNDARY elements in calculators |
| C2 single holder | reference entries land in STAGING | **recall loss**: reference entries in STAGING |
| C3 FORWARD narrowing | outer ports of wiring files are mostly absent from the reference | **precision** of BOUNDARY elements in modules with the wiring-file kind |
| C4 sub-unit output | listed sub-unit-output elements are mostly absent from the reference | **precision** of assets whose reason bracket says "sub-unit output" |
| C5 strobe as lever | reference contains new-value strobes or counter bits | **recall loss**: reference entries in BOOKKEEPING or LEVER that are new-value strobes |
| C6 generators | generator outputs and counters are absent from the reference | **precision** of DECISION and CORE elements in generator modules |
| C7 pointer narrowing | reference contains request-address or command registers | **recall loss**: reference entries in LEVER that are registers |
| All | run-to-run drift | Jaccard overlap of the asset sets of r0, r1 and r2 per module (stability, which is neither precision nor recall) |

## Brief rules, checked before writing

- **No identifiers from this processor in the prompt.** The prompt names no module, entity, port, signal, field or constant from the inputs, and not the processor. Words equal to identifiers seen in the inputs were replaced (C12). Element names appear only in this rationale.
- **No numeric quotas or proportions.** The prompt contains no digits and no quantity phrase about the number of assets. Home-rule cases are named, not numbered.
- **No instruction to use HDL comments.** The prompt says the input has none.
- **Output contract.** `module`, `analysis`, `assets` in that order; the asset item is copied from the brief. Only the allowed `analysis` key sits before `assets`.
- **Self-contained.** The prompt explains the map itself and refers to no other file.
- **Sources for every decision rule.** See the tables above. Reasoning is labelled as reasoning.
