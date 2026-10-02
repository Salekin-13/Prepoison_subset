# C2 rationale: the map procedure, revised

Designer: C. Angle unchanged: a systematic procedure over the relation map facts, with the RTL as the
authority. C2 revises C1.

## What this revision is based on

- **The critic report was not available.** `blind_agent/critic/C1/report.md` did not exist when I read it.
  The blindness rule forbids searching for it, so I did not. No change below comes from the critic. Every
  change comes from my own reading of the fifteen C1 r0 outputs against C1's own definitions and the RTL of
  the inputs.
- **Evidence was checked in the RTL this session.** For each inconsistency cited below, I read the cited RTL
  lines in the input file before using it. The line numbers quoted are those RTL source numbers.
- **What I read in the sources.** LAsset p1-7; P3164 p7-18; SAIF p2-6; SA-EDI printed p10, 12-15, 23-29
  (PDF p18, 20-23, 31-37); Nath & Tan p1-6. Rows marked "carried from C1" cite pages I did not re-read in
  this session.
- **Information seen but not used.** LAsset Table I (p5) prints the size of the expert reference list for
  some IPs. I saw it while reading the definitions. No rule, wording or check in C2 was set from those
  sizes, and C2 contains no size or proportion.

## The idea, and what stays from C1

C1's structure stays the same:

1. Name the conceptual assets.
2. Give every map element a role from a closed list.
3. Turn roles into decisions.
4. Check the list.

The C1 outputs show the structure works: every output triaged every element, followed the granularity
and name rules, and kept to the contract.

The problems were inside the role list. Some role signatures overlapped (a "data store" signature also
matched operand registers that C1's own definition calls short-lived copies). Some cases had no role at
all (a register that raises a timeout, an incoming interrupt, a reset-stretch chain). One definition was
wrong as written: "tied" as "only ever gets constants" also matches every state machine. So the executor
invented compound roles and decided the same kind of element differently in different modules. C2 makes
the roles disjoint, adds the missing ones with a source, fixes the wrong one, and states one rule behind
all of them:

> Inside the module, list the element where a protected value is created or kept; at the boundary, list the
> ports that a protected value crosses; do not list what only re-holds, passes on, times, enables, selects
> or addresses it.

This rule is a summary of C1's own primary/secondary definitions (C1 already put "keeps a short-lived copy"
under secondary). It is not a new definition.

## Decision rules and their sources

Page conventions. LAsset (2601.02624v2), Nath & Tan (2502.04648) and SAIF: page of the PDF file. IEEE
P3164: printed page (same as PDF page). Accellera SA-EDI: printed page, with the PDF page in brackets
(PDF page = printed page + 8; checked this session on printed p10, 12-15, 23-29).

| rule in the prompt | source and page | what the source says (paraphrase) | status in C2 |
|---|---|---|---|
| Primary = holds or carries the protected value; the attacker's direct target | LAsset p2 (Sec. II-A) | Primary assets are the direct target of an attack; the key itself is the primary asset. | kept |
| Secondary = acts on a primary, or keeps a copy of a value another element holds; not listed | LAsset p2 (Sec. II-A); LAsset p4 (Sec. III-B); SAIF p2 (Terminologies) | Secondary assets interact with or facilitate exposure of primaries, including internal signals/registers that carry the primary's data fully or partially; for each primary, the influencing signals are secondary; SAIF: infrastructure closely interacting with primaries. | kept; wording "keeps a copy that another element already holds" made explicit |
| Rule behind the steps: created-or-kept inside, crossings at the boundary | LAsset p2; LAsset p5 (Table II); Nath & Tan p4 (Fig. 2, Algorithm 1); Nath & Tan p5 (Sec. III-C-5) | The Key Register is a structural asset because it directly stores the key; registers carrying the primary's data are secondary. AES-128's primary structural assets are its key, state and out ports. Nath & Tan's data signals are input ports read on the right-hand side and output ports written on the left; their example's internal capture register is not one. Refinement roots candidates at top-level I/O ports. | new summary of C1's existing choices |
| Conceptual assets first, then structural | P3164 p8-10 (Sec. 3.1, 3.1.1, 3.1.2); LAsset p3-4 | CSA: conceptual assets from objectives, then the RTL that supports them; LAsset maps conceptual to structural, which are the module's primary assets. | kept |
| The four questions of Step B | P3164 p9 | Confidentiality, integrity, availability, undermined expected behaviour. | kept |
| Category hints of Step B | SAIF p2; SA-EDI p10 [18] Table 2; P3164 p8; Nath & Tan p3 | Keys, seeds, IDs, private data, configuration bits for operational and privilege modes; Critical, Secret, Sensitive, Control, Code/Data types; data and system state; control, configuration, status and data patterns. | kept; "addresses" removed from the Integrity hint (change 15) |
| Purpose summary (Step A) | LAsset p3 (Sec. III-A) | LAsset builds a technical summary before asset generation. | kept |
| Do not decide by names | LAsset p1 (Sec. I); Nath & Tan p6 (Sec. IV-B) | Name matching fails on other conventions; false positives come from atypical names. | kept |
| Clock and reset are never assets | Nath & Tan p6 (Sec. IV-A); SA-EDI p25-28 [33-36] | Clock and reset were not considered; in the watchdog example clock and reset appear only as Element (attack-point) ports. | kept |
| Tied = always the same constant in every build option; constant drivers alone do not make an element tied; judge a build-option-dependent element by its driven option | P3164 p9-10; SA-EDI p12 [20] | If the answer is "No" to all questions the element is not an asset; an asset is something of value or importance, critical to proper behaviour. A value that never changes at run time has nothing to read, change or block; a state register that takes constant state names does. | changed (change 3) |
| Unused elements are not assets | P3164 p9-10 | As above. | kept |
| Whole record: judge the fields; record judged whole only when no field has records; its fields then get "covered by the record"; never list both | SA-EDI p13 [21] (7.2.1 b, d); P3164 p18 | An Asset Definition references a single asset; related assets are kept as separate objects "so it is explicit". | kept; role made explicit (change 17) |
| Array listed by name | SA-EDI p13 [21] (7.2.1 c) | If the asset is an array, the entire array is the asset. | kept |
| Names copied exactly | SA-EDI p12 [20]; SA-EDI p15 [23] (7.4.1 d) | Name shall match its text in the source, including case. | kept |
| Data store: arrays; registers loaded by a write and kept; registers the module builds (word shift register, accumulator, working register, result register) | P3164 p8; P3164 p17; SA-EDI p10 [18] Table 2; Nath & Tan p4 | A buffer that stores the data and registers holding details of it are structural assets; the SRAM Memory Array, Data-In and Output registers are conceptual assets; Code/Data = storage; the bank registers that store and carry data are Data signals. | narrowed (change 7) |
| Secret or table value (key, seed, random value, word from a constant table) | P3164 p13; P3164 p13-14 (Fig. 3); SA-EDI p15 [23]; LAsset p6 (Sec. IV-C-2) | The XOR/LFSR seed is a confidentiality asset; the Coeff ROM asset is the register holding the ROM output; an RNG entropy source with no port path can be an asset; round constants should be assets. | renamed from "secret or generated value" |
| Setting (a choice that steers the module, loaded by a write or a command, kept until replaced) | SAIF p2; SA-EDI p10 [18] Table 2; P3164 p15; Nath & Tan p3 | Configuration bits for operational and privilege modes are primary; Control type covers control registers; AES Config Regs need integrity; configuration signals carry availability and integrity. | kept; "or by a command" added |
| Operating state: state machine, advancing pointer or program counter, timer (expiry raises an event, value read by software, or ticks are the module's product) | P3164 p8; SA-EDI p10 [18] Table 2; SA-EDI p24 [32]; SAIF p5 (Case Study I) | System state is a conceptual asset; FSM is Control, timers/counters and clock generators are Critical; the watchdog's timer register is an asset; the program counter is a primary asset. | changed: timer defined, pacing excluded (change 9) |
| Sticky status | P3164 p15; LAsset p2 (Fig. 2) | AES Status Regs may leak information. LAsset Fig. 2 colours Status Regs as primary; this colour reading is mine and is the weakest anchor here. | kept |
| Event register (a register set from a detected condition that drives an event output or a sticky status) | SA-EDI p25 [33]; SA-EDI p29 [37] | The watchdog asset is the register `wd_assert_timeout` that asserts the timeout ("critical for proper operation"). The integrator adds an Availability objective on that asset, with the reset output as its attack point. | new (change 8) |
| Event output (raised by this module) | Nath & Tan p3; SA-EDI p29 [37]; P3164 p9 (question 3) | A status signal connected to another module's control carries availability; the timeout assertion should never be gated; availability asks what could gate an output. | kept; "raised by this module, not only routed" added (change 4) |
| Data input / created output (the protected value crosses the boundary); inputs into a sub-unit and outputs from a sub-unit judged by the kind of value | LAsset p5 (Table II); Nath & Tan p1 (Sec. II); Nath & Tan p5 (Sec. III-C-5, Cases 1-2) | Key, state and out ports are AES-128's primary structural assets; elements that store important values and communicate with other IPs are primary; candidates are rooted at top-level ports. | kept; sub-unit cases added (change 13) |
| Read-back of registers is a created output | LAsset p5 (Fig. 5) | LAsset's own output names CPU-level "CSR read data" as primary; the write enable that controls it is secondary. | kept |
| Mode attribute input = the privilege or mode of the current access, used to allow, deny or change; a pulse requesting a mode is control | SAIF p2; P3164 p9 (question 4) | Privilege-mode configuration bits are primary; privileged modes, overrides and bypasses are the concern. | narrowed (change 18) |
| Sub-unit link delivering a primary kind of value | LAsset p4 (Sec. III-B); LAsset p5 (Fig. 5); P3164 p19-22 (Sec. 4, carried from C1, not re-read) | Primary assets are mapped at module level from parsed design elements; the CPU-level read-data signal, produced in a sub-unit, is primary. | kept; null-mode reading rule added (change 5) |
| Control input, including incoming request / interrupt / error / reset-request signals and a one-bit request attribute whose value is stored | LAsset p5 (Fig. 5); P3164 p12; SA-EDI p14-15 [22-23]; SA-EDI p25-28 [33-36] | A write enable is secondary; the Direction Select port is the attack point while the mux gates are the asset; Element objects list the ports that affect or observe an asset; the watchdog's enables, address and data ports are Element ports, not Asset Definitions. | extended (changes 10, 11) |
| Address or index input is secondary | LAsset p5 (Fig. 5) by analogy; C1 secondary definition ("addresses it") | See disagreement 2 for P3164 p17. | kept |
| Handshake or flow status is secondary | SA-EDI p23 [31]; SA-EDI p27 [35] | The watchdog's start, service, pause and timeout handshake signals on its internal bus are described, but the IP bundle has only two Asset Definitions: the timer and the timeout-assertion register. | kept |
| Pacing counter is secondary | SA-EDI p10 [18]; LAsset p2 | Timers/counters are Critical when the IP cannot function without them; elements that facilitate are secondary. The split is my reasoning on these two definitions. | clarified (change 9) |
| Copy register (plain capture held for one operation; synchronizer, delay, edge-detect or stretch chain; re-registered register; registered decoded value) is secondary | LAsset p2; LAsset p5 (Table II); SAIF p6 (Table II); Nath & Tan p4 | Registers that carry the primary's data, fully or partially, are secondary. AES-128's primary list is its ports, not the internal registers that carry them. On MSP430 a delayed enable and the decoded-instruction registers are secondary. Nath & Tan's internal capture register of a data input is not a Data signal. | new (change 6); merges C1 "timing copy" and "pipeline stage" |
| Pass-through = value comes unchanged from inputs and leaves on an output | LAsset p2; SAIF p2 (Example 1) | System buses carrying the primary's data are secondary; in the shared-bus example the bus and decoder are secondary. | redefined by origin (change 4) |
| Internal combinational signals are secondary unless sub-unit links | LAsset p2; LAsset p4 | Internal signals carrying or influencing the primary are secondary. | kept |
| A value in a constant is represented by its first receiving register | P3164 p13-14 (Fig. 3); LAsset p6 (Sec. IV-C-2) | Coeff ROM asset on the register holding the ROM output; round constants count as assets. | kept |
| Same role, same decision (parallel structures, build-option alternatives) | P3164 p18; SA-EDI p15 [23] (Table 5) | Both SRAM address signals are listed as the same asset; Element objects carry associated configuration parameters. | kept; "same role" defined (change 14) |
| Direct-target test with seven attack classes | LAsset p4 (Sec. III-C-1) | Candidates are checked against seven attack classes; those with no scenario are removed. | kept |
| Objective choice | SA-EDI p10 [18]; SA-EDI p15 [23] (7.5); Nath & Tan p3 | Secret, Sensitive, Critical types; APSO objectives are CIA; patterns map to objectives. | kept; event registers added under Availability |
| Map reading rules: whole-record clocked assignment, `ORIGINATES`, null connection mode, constant drivers, build options | `blind_agent/MAP_FORMAT.md` ("Elements" table; "What the map is not") | The map is mechanical and can be incomplete; the RTL is the authority. | new (changes 2, 3, 4, 5); reading rules, not asset rules |

## Change log

Each entry gives the change, the evidence from the C1 r0 outputs (file and element), and the RTL lines I
read to confirm it. The paths are under `blind_agent/runs/tuning/C1/r0/` and `blind_agent/inputs/tuning/`.

1. **One role per element, spelled from the list; a fixed order for registers.**
   - **Evidence.** The executor invented or joined roles:
     - `neorv32_bus.json`: "status" (`keeper.err`), "status / result" (`sc_fail`), "setting / operating state" (`arbiter.cmd`).
     - `neorv32_sys.json`: "reset request inputs".
     - `neorv32_imem.json`: "secret or generated value / data store" (`rdata`).
     - `neorv32_hwspinlock.json`: "operating state / data store" (`lock_q`).
     - `neorv32_debug_dtm.json`: "data store / address register" (`dmi_ctrl.addr`).
     - `neorv32_cpu_cp_muldiv.json`: "register that only decides whether the result is negated" (`div.sign_mod`).
   - **Why.** Joined roles hide which rule decided, and they made sibling cases come out differently.
   - **Change.** Exactly one role from the list, with an optional bracket note. For registers, the first
     role that fits in a stated order. This is a process rule, so it has no source.

2. **A record assigned as a whole on a clock edge makes its fields registers.**
   - **Evidence.**
     - `neorv32_bus.json`, `arbiter.state`: "map says storage none, but RTL lines 758/763 show a clocked register". In the bus input, RTL line 763 is `arbiter <= arbiter_nxt;` inside the clock-edge branch.
     - `neorv32_cache.json`, `ctrl`: "map lists fields as storage none but line 126 clocks the whole record".
   - **Why.** The executor got these right only by reading the RTL. C1's rule D-e (combinational signals are not listed) would have dropped them if read literally.
   - **Basis.** MAP_FORMAT, "What the map is not".

3. **"Tied" redefined; constant drivers and build options handled.**
   - **Evidence.**
     - C1 said tied is "an element that only ever gets constants". The muldiv state register `ctrl.state` has only constant drivers: S_IDLE, S_DONE, S_BUSY (map line 329; RTL lines 107, 122, 124, 132, 138). Under C1's wording it would be tied.
     - `neorv32_cpu_cp_muldiv.json` labels `ctrl.out_en` "register given only constants".
     - `neorv32_cpu.json` had to override `icc_tx_o` being `drive tied`. The map gives a constant only under `not ICC_EN` (map lines 356-359). Under the other build option a sub-unit drives it (RTL line 447).
   - **Basis.** P3164 p9-10; SA-EDI p12 [20].

4. **`ORIGINATES` does not mean "made here"; pass-through and event output are defined by where the value comes from.**
   - **Evidence.** In the bus input, the map marks these fields ORIGINATES, but the RTL only gates or selects an input:
     - `a_rsp_o.err` derives from `x_rsp_i.err` gated by `sel` (map lines 715-717).
     - `core_rsp_o.ack` and `core_rsp_o.err` of the read-modify-write entity derive from the system response (map lines 1647-1652; RTL lines 827-828).
   - **Why.** C1's created-output role said "drive driven, or a field with handling ORIGINATES". That invites listing such fields. The executor resisted only by adding its own "created here" test, and C2 now states that test.
   - **Basis.** LAsset p2; SAIF p2 (Example 1).

5. **Reading a connection whose `mode` is null.**
   - **Evidence.** Every `connections` entry in the CPU input has `"mode":null` (map lines 343-516), because the sub-units are in other files. C1 defined a sub-unit link as a connection "to an output port". The executor inferred direction from formal names (`rdata_o`, `res_o`).
   - **Change.** Decide the direction from the RTL: the signal is assigned nowhere in this file, and is read elsewhere. Names are only a hint.
   - **Basis.** MAP_FORMAT.

6. **New secondary role "copy register".** It merges C1's "timing copy" and "pipeline stage". It adds plain captures taken at an operation step and registered decoded values.
   - **Evidence.** Elements of the same kind were decided differently:
     - Muldiv. `mul.dsp_x` and `mul.dsp_y` were judged secondary ("pipeline stage"). `div.rs2_abs` was judged primary ("data store"). Yet all three are loaded from an operand input under a start strobe and then held unchanged (RTL lines 170-172 and 261-272).
     - Custom-instruction unit. `xtea.opa` and `xtea.opb` were judged primary. They are loaded from `rs1_i` / `rs2_i` under `start_i` and held unchanged (RTL lines 204-206).
     - Debug transport. `dmi_ctrl.addr`, `dmi_ctrl.wdata` and `dmi_ctrl.rdata` were judged primary. They are plain captures of slices of `tap_reg.dmi` and of `dmi_rsp_i.data` (RTL lines 266-267, 274).
     - Cache. `ctrl.tag` and `ctrl.idx`, captures of the request address, were judged secondary.
     - Bus. `arbiter.wdata` and `arbiter.rdata` were judged primary. They are captures of `core_req_i.data` and `sys_rsp_i.data` (RTL lines 779, 785).
   - **Why secondary.** C1's own definition already called "a short-lived copy" secondary. The "data store" signature ("loaded from a data input, often gated by a write enable") overlapped it. C2 resolves the overlap toward the stated definition.
   - **Basis.** LAsset p2; LAsset p5 (Table II); SAIF p6 (Table II); Nath & Tan p4.
   - **Disagreement.** P3164 p8 and p17 pull the other way (disagreement 2).

7. **"Data store" narrowed.** It now covers arrays, registers loaded by a write and kept, and registers the module builds: word shift registers, accumulators, working registers and result registers.
   - **Why.** This keeps the cases C1 got right on the stated definition, so they do not fall into the copy role:
     - TX and RX shift registers in the serial units.
     - `mul.prod`, `div.quotient`, `div.remainder` (RTL lines 212-215, 264-289).
     - The result registers `xtea.res` and `alu_res` (bus RTL lines 836-845).
     - The design FIFO's single-entry `fifo_reg` (RTL lines 135, 171).
   - **Basis.** P3164 p8, p17; SA-EDI p10 [18]; Nath & Tan p4.

8. **New primary role "event register".**
   - **Evidence.** The watchdog's `hw_rst_timeout` and `hw_rst_access` were judged secondary ("pipeline stage"). They are set from the timeout comparison and the strict-mode access condition (RTL lines 155-156), and they drive `rstn_o` (line 161). The gateway's `keeper.err` was judged primary under an invented role "status". It is set when the timeout count expires (RTL lines 415, 423-424) and drives `rsp_o.err` (line 401).
   - **Why.** These are the same kind of element with opposite decisions.
   - **Basis.** SA-EDI p25 [33] makes exactly this kind of register (`wd_assert_timeout`) the asset, and SA-EDI p29 [37] gives it Availability. Done/ready pulses are kept out (they remain handshakes).

9. **Timer versus pacing counter made precise.**
   - **Evidence.** C1 listed "tick divider" under pacing, but also "counters whose count is the module's job" under operating state. The clock-divider entity's `cnt` is both (`neorv32_sys.json` chose operating state; RTL lines 129-135, 140-143).
   - **Change.** A timer is a counter whose expiry raises an event, whose value software reads, or whose ticks the module delivers. Counters of bits, words, ticks or iterations of one transfer are pacing.
   - **Basis.** SA-EDI p10 [18], p24 [32]; LAsset p2.

10. **Incoming events are control inputs; width does not decide.**
    - **Evidence.** In `neorv32_cpu.json`, `msi_i`, `mei_i`, `mti_i`, `firq_i` and `dbi_i` were judged primary "data input" (map lines 346-355). Elsewhere, incoming request and error signals were judged secondary:
      - `rstn_wdt_i` and `rstn_dbg_i` in `neorv32_sys.json`.
      - `bus_rsp_i.err` in `neorv32_cache.json`.
      - `rstn_dbg_i` in `neorv32_wdt.json`.
    - **Why.** C1's "usually several bits wide" heuristic pushed the vector of fast interrupt lines into "data input".
    - **Basis.** P3164 p12; SA-EDI p14-15 [22-23]; LAsset p5 (Fig. 5).
    - **Disagreement.** Nath & Tan p3 (disagreement 4).

11. **A one-bit request attribute stays a control input even when its value is stored.**
    - **Evidence.** `neorv32_hwspinlock.json` listed `bus_req_i.rw` as a primary "data input", because of RTL line 45, `lock_q(i) <= not bus_req_i.rw;`. That line is a set/clear command under the strobe and address condition (line 44). The protected value is `lock_q`.
    - **Basis.** LAsset p5 (Fig. 5); SA-EDI p25-28 [33-36] (the read and write enables are Element ports, not assets).

12. **Shift chains split by what they hold.**
    - **Evidence.** `neorv32_sys.json` listed `sreg_sys` and `sreg_ext` as primary "operating state" (they use their own old value). They shift a constant into a stretch chain (RTL lines 51, 57), the same kind of element as the cell enable chain `sreg` in `neorv32_trng.json`, which was judged a secondary "timing copy".
    - **Change.** A shift register holding a word is a data store. A chain of earlier values of one signal, or a shifted constant, is a copy register. Shift registers are never operating state.
    - **Basis.** SAIF p6 (Table II); P3164 p8.

13. **Inputs that only go into a sub-unit, and outputs driven straight from a sub-unit, are judged by the kind of value.**
    - **Evidence.** At the CPU top level, every port and link meets a sub-unit (map lines 342-516). C1 had no wording for this, and the executor improvised.
    - **Basis.** Nath & Tan p5 (Cases 1-2); LAsset p5 (Fig. 5).

14. **"Same role, same decision" now compares the same role only.**
    - **Evidence.** C1's check named "the write side and the read side" as a pair that must get the same decision. The executor then listed each sub-unit buffer's read-out link but not the wire into the buffer: `tx_fifo.rdata` / `tx_fifo.wdata` in `neorv32_uart.json` and `neorv32_spi.json`, and `fifo.tx_rdata` / `fifo.tx_wdata` in `neorv32_twi.json`. That broke C1's own check, although the roles really differ: an intermediate rename of the write data versus the only element of this module that delivers the buffer's content.
    - **Change.** C2 keeps the asymmetric decisions and fixes the wording of the check.
    - **Basis.** P3164 p18 (unchanged).

15. **Step B no longer suggests "addresses" as integrity assets.**
    - **Evidence.** `neorv32_debug_dtm.json` listed `dmi_ctrl.addr` as "address register", primary.
    - **Why.** C1 both listed "address registers" under operating state and called "addresses it" secondary.
    - **Change.** C2 keeps advancing pointers and program counters as operating state. A captured address is a copy register.

16. **Worked example replaced.** The new invented example shows, once each:
    - a field of a record assigned as a whole on the clock edge;
    - a state register whose drivers are constants;
    - an operand register as a copy register;
    - a synchronizer;
    - an incoming tamper event as a control input;
    - an event register with its event output and sticky flag.

    The old example's only event output came from a done flag. Under the new roles that would have been ambiguous.

17. **"Covered by the record" is now an explicit role.**
    - **Evidence.** In `neorv32_cpu.json` the fields of records judged whole (for example `dbus_req_o.*`) got free-text roles.
    - **Change.** The rule itself is unchanged from C1 (choice 5 below).

18. **"Mode attribute input" limited to the privilege or mode of the current access.** A pulse requesting a mode is a control input.
    - **Evidence.** `dbi_i` in `neorv32_cpu.json` was judged "data input / debug-mode request".
    - **Basis.** SAIF p2; P3164 p9 (question 4); change 10.

19. **No digits in the prompt.** The one place C2's draft had digit literals (a flag given a low or a high constant) was reworded. The brief's quota rule is checked by code, and none of the rules needs a digit.

20. **Setting versus per-operation capture.**
    - **Evidence.** `neorv32_bus.json` judged `arbiter.cmd` "setting / operating state", primary. In the RTL it is the operation code copied from `core_req_i.amoop` when an atomic request starts (line 778) and used for that one operation (lines 838-845). By contrast, a setting such as the serial units' control fields is loaded by a host write and kept across many operations.
    - **Change.** A setting keeps its value across operations. A register captured at the start of each operation for that operation only is a copy register, even when it selects what the operation does.
    - **Basis.** As change 6 (LAsset p2; SAIF p6, Table II).
    - **Falsifier.** As change 6.

## Where the sources disagree, and the choice made

These are judgement calls. Each says what would show it wrong.

1. **Are data ports primary?** (kept from C1)
   - **Against.** LAsset p2 lists "peripheral ports" among secondary examples. SA-EDI treats ports as attack points (p14-15 [22-23], p25-28 [33-36]).
   - **For.** LAsset p5 (Table II) makes the AES-128 ports primary, and Nath & Tan p5 roots candidates at top-level ports.
   - **Choice.** A port is primary only when a protected value crosses it.

2. **Capture registers (new choice).**
   - **For primary.** P3164 p8 names "a buffer that temporarily stores the data as it is entered into the IP". P3164 p17 names the Data-In, Output and Address registers as conceptual assets (the address register "pending on the use case").
   - **For secondary.** LAsset p2 calls registers that carry the primary's data secondary. SAIF p6 classes delayed and decoded registers as secondary.
   - **Choice.** A plain capture taken at an operation step is a copy register (secondary). A register loaded by a write and kept is a data store (primary).
   - **Reasoning.** P3164 has no primary/secondary split. LAsset, the study the reference comes from, does.
   - **Falsifier.** Many reference entries among elements the executor tags "copy register".

3. **Event register and event output (new).**
   - **The tension.** SA-EDI p25 [33] and p29 [37] make the register the asset and the output port an attack point.
   - **Choice.** List both: the register as where the event is created, the port as where it crosses. This follows the rule behind the procedure.
   - **Falsifier.** Low precision on "event register" entries, or on event outputs whose register is listed.

4. **Incoming events (new choice).**
   - **For primary.** Nath & Tan p3 treat single-bit control inputs as potential primary assets with availability.
   - **For secondary.** LAsset p5 (Fig. 5) makes an enable secondary, and P3164 p12 calls the controlling port the attack point.
   - **Choice.** Control input.
   - **Falsifier.** Reference entries among the CPU-level interrupt inputs.

5. **State machines** (kept from C1).
   - **For secondary.** SAIF p2 gives "states of an FSM" as an example of a secondary asset, and SAIF p6 classes `e_state` and `i_state` as secondary relative to the program counter.
   - **For primary.** P3164 p8 (system state) and SA-EDI p10 [18] (FSM as Control type) support primary.
   - **Choice.** Primary.
   - **Reasoning.** SAIF's classes are relative to one chosen primary asset. At module level the state machine is what the module manages.

6. **Status and handshake** (kept from C1, choice 2). Events that make the system act are primary. Per-transfer handshakes are secondary.

7. **Record or fields** (kept from C1, choice 5). Fields, unless no field has a record.

## Hand trace on the two design inputs (re-derived this session)

Boot ROM input (RTL lines 19-69, map lines 40-79, both read this session):

| element | facts (RTL line) | C2 role | decision |
|---|---|---|---|
| clk_i | SEQUENCES only (47, 59) | clock | not an asset |
| rstn_i | RESETS only (57) | reset | not an asset |
| bus_req_i.addr | SELECTS rdata (48) | address or index input | secondary |
| bus_req_i.stb, bus_req_i.rw | GATES rden (60) | control input | secondary |
| other bus_req_i fields | no records, not in any statement | unused | not an asset |
| bus_req_i, bus_rsp_o | fields have records | whole record | judge fields |
| bus_rsp_o.data | ORIGINATES; DERIVES_FROM rdata, GATED_BY rden (64) | created output | primary |
| bus_rsp_o.ack | COPIES rden (65) | handshake or flow status | secondary |
| bus_rsp_o.err | tied, constant only (66) | tied | not an asset |
| rden | register; GATED_BY stb, rw (60) | handshake or flow status | secondary |
| rdata | register; word from the constant table, SELECTED_BY addr (48) | secret or table value | primary |

Expected list: rdata, bus_rsp_o.data. This is the same as C1.

Queue input (RTL lines 18-263 read this session; its map was not re-read):

| element | facts (RTL line) | C2 role | decision |
|---|---|---|---|
| wdata_i | stored into fifo_mem / fifo_reg (135, 150, 171, 184) | data input | primary |
| rdata_o | read from fifo_mem / fifo_reg (201, 213, 232, 241) | created output | primary |
| fifo_mem | array written at w_pnt under write enable (150, 184) | data store | primary |
| fifo_reg | loaded by write enable and kept (135, 171); alternative of fifo_mem under another build option | data store | primary |
| w_pnt, r_pnt | take w_nxt / r_nxt, which derive from them (76-77, 82-83) | operating state | primary |
| w_nxt, r_nxt | combinational, carry into the pointers (82-83) | next-value | secondary |
| r_pnt_ff | takes r_nxt, the same next value as r_pnt (210) | copy register | secondary |
| we_i, re_i, clear_i | only gate the pointers (64-65, 82-83) | control input | secondary |
| half_o, level_o, free_o, avail_o | fill status (116-117, 217-219, 254-256) | handshake or flow status | secondary |
| we, re, match, empty, full, half, free, avail, level | combinational (64-111) | intermediate | secondary |

Expected list: wdata_i, rdata_o, fifo_mem, fifo_reg, w_pnt, r_pnt. This is the same as C1.

## Predicted effect on the tuning outputs

This is reasoning, not a run. I apply C2's roles to the C1 r0 triage lines and the RTL I read. Only one
C1 run (r0) exists, so run-to-run variation is unknown. A real C2 run may also differ for that reason.

| module | entries C2 should drop | entries C2 should add | why (change) |
|---|---|---|---|
| bus | arbiter.rdata, arbiter.wdata, arbiter.cmd | none | captures (6); arbiter.cmd is the operation code captured per operation (RTL line 778), so it is a copy register, not a setting (change 20) |
| debug transport | dmi_ctrl.addr, dmi_ctrl.wdata, dmi_ctrl.rdata | none | captures (6, 15) |
| multiply/divide | div.rs2_abs | none | capture (6) |
| custom-instruction unit | xtea.opa, xtea.opb | none | captures (6) |
| CPU top | msi_i, mei_i, mti_i, firq_i, dbi_i | none | incoming events (10, 18) |
| reset/clock entities | sreg_sys, sreg_ext | none | stretch chains (12) |
| spinlock | bus_req_i.rw | none | one-bit request attribute (11) |
| watchdog | none | hw_rst_timeout, hw_rst_access | event registers (8) |
| uart, spi, twi, cache, pmp, trng, imem | none | none | roles already consistent with C2 |

## What this breaks, and what to read after the next run

- **Comparability.**
  - The output contract is unchanged. The `assets` lists of C1 and C2 can be compared directly.
  - Role names changed. Per-role joins across versions need this mapping:

    | C1 role | C2 role |
    |---|---|
    | timing copy | copy register |
    | pipeline stage | copy register |
    | secret or generated value | secret or table value |
    | (none) | event register (new) |
    | (none) | covered by the record (new) |

  - C1 role-level metrics are not directly comparable with C2 for those roles.
- **Measurements to read after the next parse** (triage joined with the reference; each split into precision and recall):
  1. Recall lost on reference entries that the executor tagged "copy register". If this is a large share of the misses, change 6 is wrong: move write-free captures back to data store.
  2. Precision of "event register" entries. If it is low, the reference does not follow SA-EDI's watchdog reading: drop the role and keep only event outputs.
  3. Recall lost on reference entries tagged "control input" that are incoming events. If the CPU-level interrupt inputs are reference entries, change 10 is wrong.
  4. A process check, not a score: the number of triage lines whose role is not one of the listed names. C2 expects none. If some remain, the executor is still inventing roles, and that is a prompt-clarity failure.
  5. C1's measurements still apply: precision of "data input" and "created output"; recall lost on handshake and pacing roles; record versus field mismatches.

## Compliance with the brief

- **No identifier from the processor in the prompt.** The worked example uses invented `qx_` names. The note on whole-record assignment uses `qx_r` / `qx_r_nxt`. Processor names appear only in this rationale, as evidence.
- **No numeric quotas or proportions.** The prompt has no digits and no "at most / at least" phrasing.
- **No instruction to use HDL comments.**
- **Output contract.** It is the brief's. The analysis keys (`purpose`, `conceptual_assets`, `triage`) sit between `module` and `assets`, as the brief allows.
- **Sources.** Every rule that decides asset or not-asset has a source and page in the table above.
- **Self-contained.** The prompt carries its own description of the map, including the reading rules added in C2.
