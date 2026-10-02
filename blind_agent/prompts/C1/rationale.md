# C1 rationale: the map procedure

Designer: C1. Angle: a systematic procedure that uses the relation map to find candidates and to decide,
with the RTL as the authority.

## The idea in one paragraph

An expert does three things: names what is worth protecting (the conceptual assets), finds where each of
those values lives in the RTL (the structural assets), and keeps only the elements that hold or carry the
value itself (primary), dropping the ones that only act on it (secondary). The map makes the second and
third steps mechanical enough to be consistent: every element gets a role from its map facts (storage,
boundary, handling, and the kinds of relationship records it has), the role is confirmed at the cited RTL
lines, and ordered rules turn roles into decisions. The executor must triage every element, which protects
recall, and every role has a fixed decision, which protects precision and consistency.

## How the prompt is built, and why

| part of the prompt | what it is for | failure it targets |
|---|---|---|
| Words used here | One meaning for primary, secondary, conceptual, structural. | Executor invents its own notion of "asset" and lists everything security-flavoured. |
| How to read the map | The executor never sees the map format document, so the prompt carries it. It also says unknown relationship types may appear (the design input for the queue module has comparison-type records that the format document does not describe) and that the map can miss statements. | Misreading the map; trusting a missing record. |
| Step A, purpose | Executor states what the module does before judging anything. | Judging elements by name without knowing the module. |
| Step B, conceptual assets | The four P3164 questions, with category hints from SAIF, SA-EDI and Nath & Tan. | Listing too little (stopping at "the key"). |
| Step C, roles | A closed list of roles, each with its map signature. Every map line must get one. A tie-break says roles are chosen by what the value means. | Skipped elements; the same kind of element decided differently. |
| Step D, ordered rules | First match wins; each role has a fixed decision. | Listing too much (every port, every register, every wire). |
| Step E, checks | Direct-target test (LAsset attack classes), coverage per conceptual asset, same-role-same-decision, granularity and name checks. | Inconsistency between siblings; wrong names; record and field both listed. |
| Worked example | Invented module with invented names; shows each role once. | Abstract rules applied loosely. |
| Output | The contract from the brief, with analysis keys before `assets`. | Contract drift. The analysis keys make each decision auditable after the run. |

## Decision rules and their sources

Page conventions. LAsset (2601.02624v2), Nath & Tan (2502.04648) and SAIF: page of the PDF file. IEEE
P3164: printed page (same as PDF page). Accellera SA-EDI: printed page, with the PDF page in brackets
(PDF page = printed page + 8).

| rule in the prompt | source and page | what the source says (paraphrase) |
|---|---|---|
| Primary = holds or carries the protected value; it is what the attacker targets directly | LAsset p2 (Sec. II-A) | Primary assets are the direct target of an attack; the key itself is the primary asset. |
| Secondary = acts on a primary asset (enables, selects, carries a copy) and is not listed | LAsset p2 (Sec. II-A); LAsset p4 (Sec. III-B); SAIF p2 (Terminologies) | Secondary assets interact with or facilitate exposure of primary assets, including internal signals and registers that carry its data; for each primary asset, the signals that influence its objectives are the secondary assets; SAIF: secondary assets are infrastructure that closely interacts with primary assets. |
| Conceptual assets first, then structural | P3164 p8-10 (Sec. 3.1, 3.1.1, 3.1.2); LAsset p3-4 (Sec. III, III-B) | CSA: identify conceptual assets from objectives, then the RTL that physically supports them; LAsset maps conceptual assets to structural RTL references, which are the primary assets at module level. |
| The four questions of Step B | P3164 p9 | Confidentiality, integrity, availability and undermined-expected-behaviour questions. |
| Category hints in Step B | SAIF p2; SA-EDI p10 [18] Table 2; P3164 p8; Nath & Tan p3 | Keys, random numbers and seeds, IDs, private data, configuration bits for operational and privilege modes; asset types Critical (timers, counters), Secret, Sensitive, Control (FSM, control register), Code/Data; data and system state; control, configuration, status and data patterns. |
| Structural asset = register, buffer, array, wire, port that holds or carries the value | P3164 p7, p8, p10; LAsset p2 | Assets may be a register, buffer, array or any RTL material; structural assets store and transport the value (reg and wire). |
| Purpose summary (Step A) | LAsset p3 (Sec. III-A); P3164 p9 | LAsset builds a technical summary before asset generation; P3164 relies on an architectural view. The executor has no specification, so it writes its own summary from the RTL. |
| Do not decide by names | LAsset p1 (Sec. I); Nath & Tan p6 (Sec. IV-B) | LAsset criticises name matching; Nath & Tan report false positives from atypical names. |
| Clock and reset are never assets | Nath & Tan p6 (Sec. IV-A); SA-EDI p25 [33] | Nath & Tan did not consider clock and reset; in the watchdog example the clock and reset ports are listed only as attack-point ports of the Element objects, never as Asset Definitions. |
| Tied and unused elements are not assets | P3164 p9-10; SA-EDI p2 [10] | If the answer is "No" to all questions, the element is not an asset; an asset is something used, produced or protected within the IP. A constant output produces nothing that can be read, changed or blocked; an unused input is not used. |
| Whole record: judge the fields; never list both | SA-EDI p13 [21] (7.2.1 b, d); P3164 p18 | An Asset Definition references a single asset, and separate ranges get separate objects; the SRAM example keeps related assets as separate objects "so it is explicit". |
| Array listed by name, no index | SA-EDI p13 [21] (7.2.1 c) | If the asset is an array, the entire array is the asset unless a range is given. |
| Names copied exactly | SA-EDI p12 [20]; SA-EDI p15 [23] (7.4.1 d) | The asset Name shall match its text in the source, including case. |
| Data store and secret registers are primary | P3164 p8, p13, p17; SAIF p2 (Example 2); LAsset p2 | A buffer that stores the data and registers holding details of it are structural assets; the SRAM Memory Array, Data-In and Output registers are assets; the key register contents are the primary asset; LAsset names the Key Reg as the structural asset. |
| Generated values (seed, random) are primary even without a path to a port | P3164 p13; SA-EDI p15 [23] | The seed (XOR, LFSR) is a confidentiality asset; an RNG entropy source with no port path can still be an asset. |
| Settings (configuration, mode, permission, lock) are primary | SAIF p2; SA-EDI p10 [18] Table 2; P3164 p15; Nath & Tan p3 | Configuration bits for operational and privilege modes are primary assets; Control type covers control registers; the AES Config Regs need integrity; configuration signals carry availability and integrity. |
| Operating state (state machine, pointer, address register, program counter, counter whose count is the job) is primary | P3164 p8, p17-18; SA-EDI p10 [18], p24 [32]; SAIF p5 (Case Study I) | System state is a conceptual asset; the address register is an asset and both address signals are listed; FSMs and timers/counters are asset types; the watchdog's timer register is an asset; the program counter value is a primary asset. |
| Sticky status registers are primary | P3164 p15; LAsset p2 (Fig. 2) | The AES Status Regs may leak information and are a conceptual asset. LAsset Fig. 2 colours Status Regs as primary; this colour reading is mine and is the weakest anchor in this table. |
| Data inputs and created outputs (the value itself crossing the boundary) are primary | LAsset p5 (Table II); Nath & Tan p1 (Sec. II), p5 (Sec. III-C-5, Case 1) | LAsset's AES-128 primary structural assets are the module's key, state and out ports; Nath & Tan define primary assets as elements that store important values and communicate with other IPs and peripherals, and treat top-level I/O candidates as potential primary assets. |
| Read-back of registers is a created output and is primary | LAsset p5 (Fig. 5) | LAsset's own processor output names "CSR read data" as a primary asset (Integrity), while the write enable that controls it is secondary. |
| Event outputs (interrupt, error, fault, timeout, reset request, alarm) are primary | Nath & Tan p3; SA-EDI p25 [33], p29 [37]; P3164 p9 | A status signal connected to another module's control carries availability; the watchdog's timeout assertion is an asset because the reset must propagate, and the integrator adds an Availability objective for the reset output; the availability question asks what could gate an output. |
| Mode attribute inputs (privilege, security, debug, test) are primary | SAIF p2; P3164 p9 (question 4) | Configuration bits for privilege modes are primary; privileged modes, overrides, bypass and test injection are named as concerns. |
| Sub-unit links that deliver an asset value are primary | LAsset p4 (Sec. III-B), p5 (Fig. 5); P3164 p19-22 (Sec. 4) | Primary assets are mapped at module level from the parsed design elements; the CPU-level read-data element is primary although the value is produced in sub-units; PIO looks at the points where a unit's assets are observed. |
| Control inputs, address inputs, write enables are secondary | LAsset p5 (Fig. 5); LAsset p4 (Sec. III-B); P3164 p12; SA-EDI p14-15 [22-23] | The CSR write enable is a secondary asset; influencers are secondary; the GPIO Direction Select port is an attack point, the mux data path is the asset; Element objects list the ports that affect or observe an asset, which are attack points, not assets. |
| Handshake and flow status are secondary | SA-EDI p23-25 [31-33] with source on p32-34 [40-42]; LAsset p5 (Fig. 5) | In the watchdog, the read and write enables, the "timer done" flag and the "count set" flags are not Asset Definitions; only the timer and the timeout assertion are. |
| Timing copies and pipeline stages are secondary | SAIF p6 (Table II); LAsset p2 | On MSP430 a delayed enable and the decoded-instruction stage registers are secondary assets, while the program counter is primary (p5); registers that carry the primary's data are secondary. |
| Pacing counters are secondary; counters whose count is the job are primary | SA-EDI p10 [18]; LAsset p2 | Timers and counters are Critical when the IP cannot function without them; a counter that only paces a transfer facilitates rather than holds the asset. The split is my reasoning on top of these two definitions. |
| Pass-through (FORWARDS) is secondary | LAsset p2; SAIF p2 (Example 1) | System buses that carry the primary's data are secondary; in the shared-bus example the bus and decoder are secondary, the master's data is primary. |
| Internal combinational signals are secondary | LAsset p2; LAsset p4 | Internal signals that carry the primary's data fully or partially, or influence it, are secondary. |
| A value that lives in a constant is represented by the first element that receives it | P3164 p13-14 (Fig. 3); LAsset p6 (Sec. IV-C-2) | The Coeff ROM asset is defined on the register that holds the ROM output; LAsset counts round constants as assets that the earlier list missed. |
| Same role, same decision; build-option variants too | P3164 p18; SA-EDI p15 [23] (Table 5) | Both address signals of the SRAM are listed as the same asset; Element objects carry the configuration parameters associated with an asset. |
| Direct-target test with seven attack classes | LAsset p4 (Sec. III-C-1) | Candidates are checked against side-channel, fault injection, secure-to-nonsecure leakage, unauthorized access, privilege escalation, hardware Trojan and denial of service; candidates with no scenario are removed. |
| Objective choice | SA-EDI p3 [11], p10 [18], p16 [24] (7.5.1 b); Nath & Tan p3 | CIA as objectives; Secret, Sensitive and Critical types; an APSO object has exactly one objective; patterns map to objectives. |
| The map is an index, the RTL decides | MAP_FORMAT.md, "What the map is not" | The map is mechanical and can be incomplete; the RTL is the authority. |

## Where the sources disagree, and the choice made

These are judgement calls. Each is labelled as reasoning, with what would show it wrong.

1. **Are data ports primary?** LAsset p2 lists "peripheral ports" among secondary examples, and SA-EDI and
   P3164 treat ports as attack points. But LAsset's own AES table (p5) makes the key, state and out ports the
   primary assets, and Nath & Tan (p1, p5) treat I/O as primary. Choice: a port is primary only when the
   protected value itself crosses it (data in, created data out, read-back, events). Ports that only
   control, address or time are secondary. Reasoning: this matches LAsset's practice at module level, and it
   keeps the control ports out, which is where both camps agree.
2. **Are status and handshake signals primary?** Nath & Tan (p3) count done/ready style status. SA-EDI's
   watchdog does not list its done and set flags. LAsset (p5) makes a write enable secondary. Choice: event
   outputs that make the system act are primary; per-transfer handshake and flow status are secondary.
3. **Is a mode or privilege indication primary?** SAIF p2 lists privilege-mode configuration bits as primary,
   but its Example 2 (same page) calls the boot/normal execution state secondary relative to a key. Choice:
   when the module itself uses the mode to allow, deny or change behaviour, it is primary. Reasoning: in
   SAIF's example the protected thing is a key in another IP; at the module level the mode is what the
   module manages.
4. **Are counters primary?** SA-EDI calls timers and counters Critical. Choice: only when counting is the
   module's job (timer, watchdog, pointer, program counter); pacing counters are secondary.
5. **Record or fields?** No source speaks about VHDL records. Choice: fields, by analogy with SA-EDI's
   separate-objects rule; the record only when its fields have no records.

## Hand trace on the two design inputs

This is my reasoning about what the prompt should produce on the two example inputs. It is not a run and
not a score; I have no reference list and no executor output.

Boot-ROM input (RTL lines 19-69, map lines 40-79):

| element | facts (RTL line) | role | decision |
|---|---|---|---|
| clk_i | SEQUENCES only (47, 59) | clock | not an asset |
| rstn_i | RESETS only (57) | reset | not an asset |
| bus_req_i | no records | whole record | judge fields |
| bus_req_i.addr | SELECTS rdata (48) | address input | secondary |
| bus_req_i.stb, bus_req_i.rw | GATES rden (60) | control input | secondary |
| bus_req_i.data, .ben, .src, .priv, .debug, .amo, .amoop, .lock, .fence | no records, not in any statement | unused | not an asset |
| bus_rsp_o | undriven, no records | whole record | judge fields |
| bus_rsp_o.data | ORIGINATES; DERIVES_FROM rdata, GATED_BY rden (64) | created output (read data) | primary |
| bus_rsp_o.ack | COPIES rden (65) | handshake | secondary |
| bus_rsp_o.err | tied (66) | tied | not an asset |
| rden | register; GATED_BY stb, rw; CARRIES ack (58-65) | handshake flag | secondary |
| rdata | register; loaded from a constant table, SELECTED_BY addr (48) | value from a constant (D-f) | primary |

Expected list: rdata, bus_rsp_o.data.

Queue input (RTL lines 18-263, map lines 177-333):

| element | facts (RTL line) | role | decision |
|---|---|---|---|
| clk_i, rstn_i | SEQUENCES / RESETS only | clock, reset | not an asset |
| clear_i | GATES w_nxt, r_nxt (82, 83) | control input | secondary |
| we_i, re_i | SOURCES we / re, which only GATE (64-65, 82-83, 134-184) | control input | secondary |
| wdata_i | CARRIES fifo_mem, fifo_reg (135-184) | data input | primary |
| rdata_o | DERIVES_FROM fifo_mem, COPIES fifo_reg (201-241) | created output | primary |
| half_o, level_o, free_o, avail_o | copies of fill status (116-117, 217-256) | flow status | secondary |
| fifo_mem | register array; COPIES wdata_i, GATED_BY we, SELECTED_BY w_pnt (147-184) | data store | primary |
| fifo_reg | register; COPIES wdata_i, GATED_BY we (132-171), other build option | data store (variant) | primary |
| w_pnt, r_pnt | register; COPIES next-value that DERIVES_FROM itself (73-83); SELECTS the array | operating state (pointers) | primary |
| w_nxt, r_nxt | combinational; CARRIES into the pointer (76-77, 82-83) | next-value | secondary |
| r_pnt_ff | register; COPIES r_nxt (210), same next value as r_pnt (77) | timing copy | secondary |
| we, re, match, empty, full, half, free, avail, level | combinational (64-111) | intermediate | secondary |

Expected list: wdata_i, rdata_o, fifo_mem, fifo_reg, w_pnt, r_pnt.

The queue map holds relationship types (CONSTRAINS, CONSTRAINED_BY; map lines 258-259, 263, 272, 291-294,
308-311) that the format document does not describe. The prompt tells the executor to read the cited lines
for any unknown type, so these do not stall it.

## What this design breaks, what would falsify it, and what to read after the run

- **Comparability.** The analysis keys (`purpose`, `conceptual_assets`, `triage`) are extra. Only `assets` is
  scored, so scores stay comparable with other designers. The triage lets each false positive and false
  negative be traced to the role and rule that caused it.
- **Measurement to read after the run** (per role, from the triage joined with the reference):
  1. precision of entries listed under "data input" and "created output". If it is low, choice 1 is wrong:
     drop boundary ports and keep only stored homes (the SA-EDI reading).
  2. recall lost on reference entries the executor tagged "control input", "handshake or flow status" or
     "pacing counter". If many reference entries fall there, the reference follows Nath & Tan's broader
     patterns and choices 2 and 4 should flip.
  3. reference entries that are whole records where the executor listed fields, or the reverse. If this is
     common, choice 5 should flip.
  4. reference entries never seen in the triage. That would mean the executor skipped map lines, a process
     failure, not a rule failure.
- **Falsifier for the whole approach.** If entries the executor tagged "intermediate" or "next-value" make up a
  large part of the reference, the expert list includes internal wires, and the home-only principle is
  wrong for this reference.

## Compliance with the brief

- No identifier from the processor appears in the prompt. The example uses invented names with a `qx_`
  prefix. Element names from the design inputs appear only in this rationale's hand trace, not in the prompt.
- No numeric quotas or proportions. The prompt contains no digits and no "at most / at least" phrasing.
- No instruction to use HDL comments.
- The output contract is the one in the brief; extra keys sit between `module` and `assets`, as the brief
  allows.
- Every rule that decides asset or not-asset has a source and page in the table above.
- Self-contained: the prompt explains the map format itself, because the executor sees only the prompt and
  the input file.
