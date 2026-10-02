# Rationale for prompt B1 (threat-first)

## The idea in three lines

- An element is a primary asset when an attacker would go after it **directly**: read it, change it, or block it, and the harm is stated in terms of that element's own value.
- Everything that only helps the attacker get there (wires that move the value, enables, selects, addresses, handshakes, clocks, resets, forwarded bus fields) is secondary or an attack point, and is not listed.
- The executor finds candidates by asking the P3164 questions about the module, maps each conceptual asset to its "home" element with five inclusion tags, then runs a one-sentence threat test on every candidate. Every element of the map must end up either listed or in a named exclusion group.

## Page conventions

- LAsset = `2601.02624v2.pdf`, PDF page numbers (pp. 1-7).
- P3164 = `IEEE_P3164_Asset_Identification.pdf`; printed page numbers equal PDF page numbers.
- SA-EDI = `Accellera_SA-EDI_Standard_v10.pdf`; I give the printed page and, in brackets, the PDF page (PDF page = printed page + 8).
- Nath & Tan = `2502.04648.pdf`, PDF pages (pp. 1-7).
- SAIF = `SAIF_..._Register_Transfer_Level.pdf`, PDF pages (pp. 1-7).

## Decision rules and their sources

### Core definitions (prompt section "Words used here")

| Prompt text | Source and page |
|---|---|
| Asset = something of value used, produced or protected | SA-EDI p.2 [PDF 10], definition of Asset; SA-EDI p.12 [PDF 20]: an asset can be a port, module, register or other object |
| C / I / A objectives | SA-EDI p.3 [PDF 11], Security Objective; LAsset p.2, security asset definition (CIA) |
| Conceptual vs structural asset | P3164 p.8 (conceptual: high-level asset tied to use-case flows; structural: RTL material that physically supports it); LAsset p.2 |
| Primary = direct target of an attack | LAsset p.2 ("components that serve as the direct target of an attack"); SAIF p.2 ("definitive target for protection") |
| Secondary = helps reach a primary; carriers, buses, ports are examples | LAsset p.2 ("system buses, peripheral ports, and internal signals/registers that carry the data of the primary asset, either fully or partially"); LAsset p.4 (secondary = internal signals/registers that influence or violate the primary's objective); SAIF p.2 (tangible or intangible infrastructure that closely interacts with primary assets); Nath & Tan p.1 (secondary help propagate and handle primary assets) |
| Attack point = way in, not a target | SA-EDI p.2 [PDF 10] (Attack Point, Attack Surface); SA-EDI p.14 [PDF 22] (Element objects: top-module ports that an adversary can use to affect the asset); SA-EDI pp.24-25 [PDF 32-33] (watchdog: the ports are listed as Element ports, the registers are the assets) |

### Adversary model (prompt section "Who attacks")

| Prompt text | Source and page |
|---|---|
| Software via bus, external pins, debugging/test, fault injection, side channel, Trojan | LAsset p.4 (seven attack classes: side-channel, fault injection, secure-to-nonsecure leakage, unauthorized access, privilege escalation, hardware Trojan, denial of service); SAIF p.3 (bus snooping, test/debug structures, unprotected communication, third-party IPs, glitching); SA-EDI p.16 [PDF 24] (side-channel and injection attack points) |
| "A glitch or Trojan can hit any wire; that alone never makes an element primary" | Reasoning, built on LAsset p.2 (primary = direct target; secondary = elements whose compromise only indirectly exposes the primary). Without this caution every element passes an attack-scenario check, so the LAsset p.4 refinement step would filter nothing. |
| "Normal operation is not an attack" | P3164 p.22: the data cache replacing a line on a store "is expected behavior and should not result in a 'yes'" to the integrity question |

### Step C: conceptual assets

| Prompt text | Source and page |
|---|---|
| The four questions (Confidentiality, Integrity, Availability, Undermined behaviour) and their examples | P3164 p.9 (the four questions, with keys/secret info, immutable state or configuration, elements that gate an output port, privileged modes/overrides/bypass/test injection) |
| "Override inputs are attack points; the elements they corrupt are assets" | P3164 p.13 (the override port forces a wrong coefficient, so the coefficient ROM is the asset); P3164 p.12 (the GPIO direction-select port is the attack point; the mux gates are the asset); SA-EDI pp.25-26 [PDF 33-34] (debug inputs are attack points of the timer assets) |
| "No to all questions means no asset" | P3164 pp.9-10 ("If the answer is 'No' to all the questions above, then it is probably safe to assume that the element is not an asset") |

### Step D: inclusion tags

| Tag | What it keeps | Source and page |
|---|---|---|
| STORE | registers/memories that hold keys, seeds, random values, buffered or in-transit payload, code, memory contents | SAIF p.2 (primary examples: cryptographic keys, random numbers and seeds, IDs, user private data); P3164 p.8 (a buffer that stores the data, registers that contain details of it); P3164 p.17 (SRAM: memory array, data-in register, output register); P3164 pp.22-23 Table 3 (cache contents, general-purpose registers); SA-EDI p.10 [PDF 18] Table 2 (Secret, Code/Data types); SA-EDI p.15 [PDF 23] (an RNG entropy source with no port can still be an asset); LAsset p.2 (the key register is the structural asset) |
| STORE: "if the real store is not an element, the first register that holds the value" | Reasoning. MAP_FORMAT.md says constants are not elements, and SA-EDI p.12 [PDF 20] says an asset must be named as it appears in the RTL. So a constant table can only be represented by the first declared element that holds its value. |
| SETTING | software-written configuration: enables, modes, permissions, write-protect bits, bounds, compare/reload values, each field separately | SAIF p.2 ("configuration bits for operational and privilege modes" are primary assets); P3164 p.9 question 2 (configuration settings that must stay immutable); P3164 p.15 (AES configuration registers need integrity); SA-EDI p.10 [PDF 18] Table 2 (Control type: control register); SA-EDI p.16 [PDF 24] (a write-protect bit guards a register's integrity); LAsset p.5 Fig. 5 (control/status register value is a primary asset, objective Integrity) |
| SETTING exclusion of registered strobes | P3164 pp.16-18: in the SRAM controller the control register that registers the chip/write/output enables is not named as an asset; only the array, data registers and address register are |
| CORE: program counter, executing instruction | SAIF p.2 (program counter integrity in a micro-controller) and p.5 (program counter is the primary asset in case study I); P3164 p.21 and p.22 Table 3 (instructions are a conceptual asset) |
| CORE: privilege/operating mode the module keeps and enforces, debugger-halted or unlock status | SAIF p.2 (privilege-mode configuration bits); P3164 p.9 question 4 (privileged modes and bypass) |
| CORE: main count of a timer or watchdog | SA-EDI p.24 [PDF 32] (the timer count register is an asset because an adversary would modify it to prevent the timeout); SA-EDI p.10 [PDF 18] Table 2 (Critical type: timers/counters) |
| CORE: main state machine register | SA-EDI p.10 [PDF 18] Table 2 (Control type: "FSM, control register"); P3164 p.9 question 2 (state that must be immutable) |
| CORE: stored pointers / address registers locating protected contents | P3164 p.17 (SRAM address register is a conceptual asset); P3164 p.13 (the address into the coefficient ROM is an integrity asset); P3164 p.18 (both address signals listed as structural assets) |
| CORE exclusions: pacing counters, delayed copies, synchronizers | LAsset p.2 (internal registers that carry the primary's data are secondary); SAIF p.2 (FSM states that only gate access are secondary, Example 2). The split "main state machine in, pacing counters out" is my reasoning; see Tension 2 below. |
| DECISION | interrupt, error/fault/violation, grant/deny, timeout/reset request, fresh-random-ready | SA-EDI p.25 [PDF 33] (the timeout-assertion register is an asset: control over it blocks the reset or creates denial of service); SA-EDI p.29 [PDF 37] (the timeout output must never be gated, objective Availability); Nath & Tan p.3 (status signals: Availability when they drive another module's control, otherwise Integrity); P3164 p.9 question 3 (elements that could gate an output); LAsset p.4 (denial-of-service attack class) |
| DECISION exclusion of flow-control flags | Reasoning; see Tension 3 below |
| BOUNDARY | outer-entity port that carries a STORE value itself, or the main product | LAsset p.5 Table II (for AES-128 the primary assets are the outer key input, the input block and the final output, the last with objective Availability); Nath & Tan p.5 (Case 1: an input or output port of the TOP module is a potential primary asset); P3164 p.19 (PIO: the information that goes into the IP and what it produces are the conceptual assets; points where they are observed or influenced become structural assets); P3164 p.7 (a port that can observe an asset violates confidentiality) |
| BOUNDARY exclusions: inner-entity ports, settings-only bus fields | LAsset p.5 Table II (per-round copies inside sub-units are secondary); SA-EDI p.25 [PDF 33] (the watchdog's write payload input is an attack point) and p.27 [PDF 35] (the read payload output carried no security objective) |
| ATTRIBUTE | requester privilege/security/debugging status consumed by an access check | SAIF p.2 (privilege-mode bits are primary); P3164 p.9 question 4; LAsset p.4 (privilege escalation and unauthorized access classes) |

### Step E: threat test

| Prompt text | Source and page |
|---|---|
| One threat sentence per candidate; drop candidates without a scenario | LAsset p.4 (Attack Scenario Analysis: "assets without such scenarios are excluded") |
| Harm must concern the element's own value; otherwise credit the other element | LAsset p.2 (primary = direct target; secondary = indirectly exposes the primary); LAsset p.5 Fig. 5 (the write enable of the control/status registers is secondary to their value) |
| Unauthorized action only | P3164 p.22 (expected behavior is not a "yes") |
| Tie-break: holds the value across cycles or crosses the outer boundary = keep | Reasoning that combines LAsset p.2 (carriers are secondary) with the BOUNDARY sources above |

### Step F: exclusion tags

| Tag | Source and page |
|---|---|
| CLOCK-RESET | Nath & Tan p.6 ("we did not consider 'Clock' and 'Reset' signals"); SA-EDI p.25 [PDF 33] (clock and reset are Element attack points, not assets). The exception for a generated reset/timeout comes from SA-EDI pp.25 and 29 [PDF 33, 37]. |
| LEVER | SA-EDI p.14 [PDF 22] (ports that affect the asset are access points); SA-EDI p.25 [PDF 33] (read/write enables, address, write payload, debug inputs are attack points); P3164 pp.17-18 (mode, chip enable, write enable, output enable, sleep inputs are not named assets); LAsset p.5 Fig. 5 (write enable is secondary); SAIF p.2 (address decoder is secondary) |
| CARRIER | LAsset p.2 (internal signals/registers carrying the primary's data are secondary); LAsset p.5 Table II (round-internal copies are secondary); LAsset p.4 ("along each path, the most tamper-prone asset is designated as the primary asset, while the remaining assets are treated as secondary"); Nath & Tan p.1 |
| BOOKKEEPING | LAsset p.2 (elements that interact with or facilitate the primary are secondary); P3164 p.19 (CSA tends to mark every internal block, which yields false positives); LAsset p.4 (LLMs "lean toward listing a broad set of possible security and non-security assets") |
| FORWARD | SAIF p.2 Example 1 (the information a master sends is primary; the bus that carries it is secondary); LAsset p.2 (system buses are secondary) |
| UNUSED | P3164 pp.9-10 (no to all questions means not an asset); P3164 p.11 (gates that "do not leak any information" give a "No") |
| RECORD-WHOLE | SA-EDI p.13 [PDF 21] 7.2.1 c-d (a whole array is the asset unless a range is named; each range gets its own definition); P3164 p.18 (two address signals kept as separate objects "so it is explicit"); SA-EDI p.12 [PDF 20] (Name must match the RTL text) |
| Never output constants, generics, variables, labels, instances, slices | MAP_FORMAT.md (these are not elements); SA-EDI p.12 [PDF 20] (Name must match the RTL text) |

### Step G and H: consistency, names, objective

| Prompt text | Source and page |
|---|---|
| Same role, same decision (channels, fields, key parts, build variants) | SA-EDI p.13 [PDF 21] 7.2.1 d (every range of an array is defined); P3164 p.18 (both address signals listed); LAsset p.2 (self-consistency checks in the refinement stage) |
| Accounting of every map element | LAsset p.3 (the RTL parsers extract every port and internal signal "to ensure that LLMs do not overlook any of the parsed design elements") |
| Copy names exactly | SA-EDI p.12 [PDF 20] (Name "shall match its corresponding text in the source"); SA-EDI p.15 [PDF 23] Table 5 (case-sensitive names); TASK_BRIEF.md (names compared as declared) |
| Objective choice | SA-EDI p.3 [PDF 11]; LAsset p.5 Table II (key C, final output A, input block C); Nath & Tan p.3 (data signals C, configuration signals A and I, status signals A or I); SAIF p.2 (program counter I) |

### Worked examples in the prompt

All come from the sources' own designs; none uses a name from this processor.

- Watchdog: SA-EDI pp.24-26 [PDF 32-34]. The sentence that its control register bits and reload value "would also be listed, as SETTING" is labelled in the prompt as our rule, not the standard's; its basis is the SETTING row above.
- SRAM controller: P3164 pp.16-18.
- AES core: LAsset p.5 Table II.
- Shared bus: SAIF p.2 Example 1.
- Processor core: P3164 pp.21-23 (Table 3, cache "No" on integrity); SAIF p.5 (debugger observing the program counter); LAsset p.5 Fig. 5 (control/status register value primary, its write enable secondary).

## Where the sources disagree, and what I chose

These are judgement calls. Each is labelled as reasoning.

**Tension 1: are ports assets or attack points?**
SA-EDI (p.14 [PDF 22], pp.24-25 [PDF 32-33]) treats ports as attack points and puts the asset inside. LAsset p.2 lists "peripheral ports" among secondary assets. But LAsset's own AES example (p.5 Table II) makes the outer key, input and output ports primary, Nath & Tan (p.5) roots primary assets at the top module's ports, and P3164 PIO (p.19) starts from the information that crosses the interface.
Choice: a port is listed only when it is a port of the outer entity and carries the protected payload itself, or the main product (BOUNDARY), or delivers a DECISION. Address, enable, strobe and handshake ports stay attack points. Ports of inner entities are carriers. This is the narrowest reading that still reproduces the AES example.

**Tension 2: are state machines primary?**
SA-EDI p.10 [PDF 18] Table 2 lists "FSM, control register" as the Control asset type. SAIF p.2 says FSM states can be secondary (the boot-versus-normal state that only gates access to a key, Example 2).
Choice: the main state machine of the module is CORE; a mode that the module keeps and enforces is CORE; a state that only gates access to something else, and pacing counters, are secondary.

**Tension 3: are status flags primary?**
Nath & Tan p.3 treats single-bit status outputs as potential assets (Availability or Integrity). The SRAM and watchdog examples (P3164 pp.16-18, SA-EDI pp.24-25 [PDF 32-33]) name no flow-control flag as an asset, and LAsset p.4 warns that LLMs over-list.
Choice: generic flow-control flags (ready, busy, acknowledge, occupancy) are BOOKKEEPING. Alerts that the system acts on (interrupt, error, violation, timeout, fresh-random-ready) are DECISION.

**Tension 4: pointers.**
P3164 names the SRAM address register (p.17) and the coefficient-ROM address (p.13) as assets. A pointer can also be seen as a lever on the store.
Choice: a stored pointer or address register that decides where protected contents go is CORE; an address input is a LEVER. The map's `storage` field separates the two.

## Why this design

Reasoning, not measured.

1. **Over-listing is the expected failure.** LAsset p.4 says LLMs list broadly. A threat-first prompt can make it worse, because fault injection gives every wire an attack story. So the prompt pins the test on "harm about the element's own value" and adds the caution about glitches and Trojans.
2. **Under-listing is the second failure.** A strict "targets only" reading drops settings registers, the main counter and the interrupt output, because they "look ordinary". The inclusion tags name those families explicitly, and the "Common mistakes" list repeats them.
3. **Consistency comes from tags, not from case-by-case taste.** Every element receives a tag. Siblings get the same tag. The `not_listed` groups make each exclusion visible.
4. **Naming errors are cheap to prevent.** The inventory step fixes the namespace; the prompt says which things are not elements; record fields are decided one by one.
5. **The map is used for role, not for judgement.** `storage`, `kind`, `handling`, CARRIES/COPIES, GATES/SELECTS and SEQUENCES/RESETS give the executor mechanical evidence for LEVER, CARRIER, FORWARD and CLOCK-RESET. The prompt warns that the map can miss statements and that relationship types beyond the documented ones exist (the sample map shows one).

## Dry run on the two design inputs (reasoning only; no executor was run)

This is how I expect a careful executor to apply the rules. It is not a score, and I have no reference to compare it with.

- Read-only memory module (boot image). The image is a constant, so it is not an element. STORE: the read register `rdata` (first register holding the image word). BOUNDARY: `bus_rsp_o.data` (the image word leaves through it). LEVER: `bus_req_i.addr`, `bus_req_i.stb`, `bus_req_i.rw`, `rden` (registered strobe), `bus_rsp_o.ack`. CLOCK-RESET: `clk_i`, `rstn_i`. UNUSED: `bus_rsp_o.err` (tied) and the unread request fields. RECORD-WHOLE: `bus_req_i`, `bus_rsp_o`. Expected list: `rdata`, `bus_rsp_o.data`.
- Buffer module. STORE: `fifo_mem`, `fifo_reg` (siblings under different build options). BOUNDARY: `wdata_i`, `rdata_o`. CORE: `w_pnt`, `r_pnt` (stored pointers locating protected contents). CARRIER: `w_nxt`, `r_nxt`, `r_pnt_ff` (delayed copy). LEVER: `we_i`, `re_i`, `clear_i`, `we`, `re`. BOOKKEEPING: `match`, `empty`, `full`, `half`, `free`, `avail`, `level`, `level_o`, `half_o`, `free_o`, `avail_o`. CLOCK-RESET: `clk_i`, `rstn_i`. Expected list: six elements.

The risky calls in this dry run are the pointers (Tension 4) and the status outputs (Tension 3).

## Project constraints, checked before writing

- **No processor identifiers in the prompt.** The prompt names no module, entity, port, signal, field or constant from the inputs. I also avoided English words that equal identifiers seen in the two sample files or their record types (the bus record field names, the buffer's flag names, the word for the pronoun that equals a write-enable signal name, and hyphenated words that would split into a read-enable signal name). The prompt says "payload" instead of the bus field word for it, and "debugger"/"debugging" and "write-protect" instead of two other field names. The words "state" (in "state machine"), "ready", "busy", "enable" and "mode" remain as plain English; if the code check rejects any of them, they can be replaced without changing a rule.
- **No numeric quotas or proportions.** The prompt contains no digits, no percent sign and no quantity phrase about the number of assets. Steps and rules are labelled with letters and words.
- **No instruction to use HDL comments.** The prompt states that the input has none and tells the executor to judge by RTL behaviour, the map and names.
- **Output contract.** `module` and `assets` are present; the asset item shape is copied from the brief. One extra top-level key, `analysis`, sits before `assets`, as the brief allows.
- **Self-contained.** The prompt explains the map format itself and refers to no other file.
- **Examples.** All worked examples come from the sources' own designs on other IP (watchdog, SRAM controller, AES, shared bus, generic processor core).

## What this design risks, what would falsify it, what to read after a run

Each item names a measurement that can be read from executor outputs plus the reference, without changing the prompt. The `reason` field ends with a rule tag, and `not_listed` groups carry a tag, so every listed and every excluded element is attributable to a rule.

| Rule | Risk | Falsified if | Measurement |
|---|---|---|---|
| BOUNDARY | extra bus payload fields (precision) | listed BOUNDARY elements are mostly absent from the reference | precision of listed elements with tag BOUNDARY, per module family |
| CORE (pointers, main state machine) | extra elements in buffer and engine modules | CORE elements other than counters and program-counter-like registers are mostly absent from the reference | precision per tag CORE, split by sub-kind in the reason text |
| BOOKKEEPING exclusion of flags | missed status outputs (recall) | reference entries land in the BOOKKEEPING group often | count of reference entries found under each `not_listed` tag |
| LEVER exclusion of addresses and enables | missed address inputs (recall) | reference entries land in the LEVER group often | same count, tag LEVER |
| CLOCK-RESET exclusion | missed clock/reset (recall) | reference entries land in CLOCK-RESET | same count, tag CLOCK-RESET |
| RECORD-WHOLE | name-form mismatch (both) | reference uses whole-record names where the executor listed fields | for each false negative that is a whole record, check whether its fields were listed |
| Accounting | longer output on large files | executor truncates or omits `not_listed` on large modules | share of outputs whose `not_listed` plus `assets` covers the inventory |

**What it breaks.** Nothing earlier: this is a new prompt in its own output directory. The extra `analysis` key does not change the scored fields, so scores stay comparable with prompts that output only `module` and `assets`.
