# D2 rationale (angle: MINIMAL)

## Read this first: the critic report was missing

The task listed `blind_agent/critic/D1/report.md`. That file did not exist when I tried to read it. The blindness rules
forbid searching, so I did not look for it elsewhere. Instead I reviewed the fifteen D1 outputs myself against D1's own
definition and the RTL, and read the relevant input files. Every change below comes from that review. Each one names
the output and the RTL or map lines behind it.

## The bet (unchanged from D1)

One definition, one test, and every exclusion stated by **role** (what the element does), not by name. No worked
examples. Names are a weak signal: LAsset faults earlier work for relying on "RTL signal and register naming
conventions" (LAsset p.1), and Nath & Tan trace their false positives to atypical names (Nath & Tan p.6).

D2 keeps that bet. It does not add examples. It fixes places where two D1 rules pointed opposite ways, or where one
D1 word could be read two ways, so that the executor decided the same role differently in different modules.

## Page conventions

- LAsset (2601.02624v2), Nath & Tan (2502.04648), SAIF: PDF page numbers.
- IEEE P3164 white paper: printed page = PDF page.
- Accellera SA-EDI v1.0: printed document page, PDF page in brackets (PDF = document + 8).
- "Checked" means I read that page in this session. "Carried" means the citation comes from D1 and I did not re-read
  the page this time.

## Decision rules and their sources

Rules marked **changed** or **new** are explained in the change log below.

| # | Rule in the prompt | Source and page | Checked |
|---|---|---|---|
| R1 | An asset is a value whose confidentiality, integrity or availability must be protected. | LAsset p.2 (II-A, CIA definition); SA-EDI doc p.12 [PDF p.20] (7.2: an asset "can be identified as a port, module, register, or another object"). | Checked |
| R2 | Conceptual asset = the value as an idea; structural asset = the RTL that holds or carries it. | P3164 p.8 (3.1: conceptual asset "associated with the use-case flows"; structural asset "RTL material that physically supports a conceptual asset"); LAsset p.2. | Checked |
| R3 | Primary = the direct target; secondary = elements that move, **route**, time, select, enable or compute part of it. List only primary. | LAsset p.2 (primary "direct target of an attack"; secondary "system buses, peripheral ports, and internal signals/registers that carry the data ... either fully or partially"); LAsset p.4 (III-B, III-C-4); SAIF p.2 (II-C; Example 1: "the bus and the decoder are the secondary supports helping to transfer the primary asset"). "Route" is new wording for the same idea. | Checked |
| R4 | The four questions. | P3164 p.9 (3.1.1, questions 1-4); P3164 p.10 ("No" to all means not an asset); P3164 p.19 (PIO form). | Checked |
| R5 | Intended updates are not an integrity threat. | P3164 p.22 (DCache: replacing data on a store "is expected behavior"). | Checked |
| R6 | Undermined behaviour: the elements a privileged/debug/test/override/bypass path can corrupt are conceptual assets. | P3164 p.9 (question 4); P3164 p.13 (the address-override input makes the coefficient ROM the asset); P3164 p.11-12 (GPIO: Direction Select is the attack point, the mux gates are the assets). | Checked |
| R7a | Data, **now naming program code**. | SAIF p.2 (keys, random numbers and seeds, private data); LAsset p.5 (Table II: AES key, state, output); P3164 p.17 (SRAM memory array, data-in and output registers); **P3164 p.20 (a CPU core's conceptual assets are Instructions and Data)**; **SA-EDI doc p.10 [PDF p.18] (Table 2, asset type Code/Data)**; Nath & Tan p.3-4 (data signals; "Seed" and "Key"). | Checked |
| R7b | Settings held in registers (configuration, mode, privilege, lock, enable). | SAIF p.2 ("configuration bits for operational and privilege modes"); P3164 p.9 (question 2); P3164 p.15 (AES Config Regs need integrity); SA-EDI doc p.10 [PDF p.18] (Table 2, Control: "FSM, control register"). | Checked |
| R7c | **Changed.** State: state-machine state, program counter, read/write pointers of a buffer or memory, and a count only when counting is the module's own job (timer, watchdog, time limit on transfers, clock generator). | SA-EDI doc p.10 [PDF p.18] (Table 2: Control "FSM"; Critical "Timers/Counters, clock generators"); SA-EDI doc p.24 [PDF p.32] (B.2 step 2: the watchdog's count register is the asset); SAIF p.2 (program counter value as an integrity concern); P3164 p.17-18 (the SRAM address register and the two address signals are structural assets); P3164 p.22 (Table 3: internal state). | Checked |
| R7d | **Changed.** Decisions and events (access decision, fault/error report, interrupt request, timer expiry, reset request, debug-stop request) count where the module produces them **and where it receives and acts on them**. | SA-EDI doc p.25 [PDF p.33] (the timeout indication must "get propagated out ... without any modification"); Nath & Tan p.3 (control signals that are "connected with a status signal from a different module" carry the Availability objective; status signals such as alert and error carry Availability or Integrity); P3164 p.9 (question 3: elements that could gate "the use of an input port"). | Checked |
| R8 | **Changed.** Map each conceptual asset to: the holder in this file (including the register that holds the word just read from a memory or constant table); the boundary ports through which it enters or leaves; a carrier only when there is neither. A sub-unit whose code is in another file is not a holder here. | P3164 p.10 (3.1.2: structural assets are the RTL that "stores and transports its value"); P3164 p.13-14 (the coefficient ROM's asset is its output register `d`); P3164 p.17 (Data-In Register and Output Register are conceptual assets); LAsset p.5 (Table II: module ports are primary); Nath & Tan p.5 (Case 1: a port of the top module goes to the primary list); LAsset p.4 (III-B: primary assets at module level are "derived from the parsed design elements" of that module); LAsset p.5 (Fig. 5: at a CPU top level, a read-data signal wired from a sub-unit is the primary structural asset); P3164 p.22 (Table 3: "Source and data registers" of the functional units). | Checked |
| R8b | **New.** The boundary is the ports of entities that no other entity of the file instantiates. Sub-unit ports are internal wires; sub-unit storage still counts. | LAsset p.5 (Table II: elements named in sub-modules, such as the key of the round module, the state input of the round module and the state of the table-lookup module, are **secondary**; the top module's key, state and out are primary); Nath & Tan p.5 (Case 2: for a candidate in an instantiated sub-module, the connected **top-module port** is appended to the primary list); LAsset p.4 (III-C-4: along a path, one most tamper-prone asset is primary, the rest secondary). Storage inside sub-units stays: SA-EDI doc p.24-25 [PDF p.32-33] (asset `wd_top.count_block.wd_count.wd_timer`, a register two levels down); P3164 p.14 (asset `gng.gng_interp.gng_coef.d`). | Checked |
| R8c | **New.** If an element's role differs between build options, decide under each and list it if it is primary under any. | P3164 p.8 (a structural asset is what "physically supports" the conceptual asset; in that build it does); P3164 p.13-14 (a constant ROM's output register is the asset). | Checked |
| R9 | **Changed.** Leave out the module's own clock and reset, defined by map role: only `SEQUENCES` or only `RESETS` records. A reset or debug request the module acts on otherwise is an event (R7d). | Nath & Tan p.6 (IV-A: "we did not consider 'Clock' and 'Reset' signals"); MAP_FORMAT (`SEQUENCES` is the clock relation, `RESETS` the reset relation); SA-EDI doc p.25 [PDF p.33] (clock and reset ports appear among Element ports, i.e. attack points). | Checked |
| R10 | **Changed.** Transfer control: strobes, valid/ready, direction, write and byte enables, acknowledge, **outstanding-transfer flags**, fill-state flags and counts, per-transfer addresses. **A register holding a command written to the module until it is carried out is a strobe, even a reset command.** Held settings and state are not strobes. | LAsset p.5 (Fig. 5: a write-enable input is a secondary asset of a read-data primary asset); SA-EDI doc p.24-25 [PDF p.32-33] (B.1: the watchdog's service bit is a write-only command "cleared on the next clock cycle"; B.2 names the timer and the timeout-assertion register as the assets, not the service bit); SA-EDI doc p.25-26 [PDF p.33-34] (read enable, write enable, address and data inputs are attack points); P3164 p.12 (a control port is the attack point). | Checked |
| R10b | **New.** Pacing counts (bit position, bit-rate divider, iteration count inside a transfer or compute engine) are left out. | LAsset p.2 (secondary assets "interact with or facilitate"); SAIF p.2 (secondary assets are "infrastructures that closely interact with the primary assets"); D1 R3 (secondary elements "time" a primary asset). Contrast R7c: SA-EDI keeps a count when the count is the module's function. | Checked |
| R11 | Leave out intermediates: next-value, partial or derived versions, **merges of listed values**, delayed or duplicated copies. | LAsset p.2 ("either fully or partially"); LAsset p.5 (Table II: round keys, intermediate state and table-lookup signals are secondary); P3164 p.19 (CSA "may end up identifying all the internal blocks ... false positives"). | Checked |
| R12 | **Changed.** Transport is defined by role: a value the module only routes from one of its ports to another without holding it or deciding on it. The `FORWARDS` label alone neither makes nor unmakes transport. | LAsset p.2 (system buses that carry the primary asset are secondary); SAIF p.2 (Example 1: bus and decoder are secondary supports). | Checked |
| R13 | Leave out unused ports/fields and constant-tied outputs. | P3164 p.8 (a structural asset physically supports a conceptual asset); P3164 p.10. | Checked |
| R14 | Name fields, not the whole record; an array is one element. | SA-EDI doc p.13 [PDF p.21] (Table 3: Name is the path "as defined in the RTL source"; 7.2.1 b and c). | Checked |
| R15 | Constants are not elements; list what holds or delivers a constant asset. | P3164 p.13-14; brief and MAP_FORMAT. | Checked |
| R16 | Keep only direct targets. | LAsset p.4 (III-C-1: seven attack classes; "assets without such scenarios are excluded"; III-C-4). | Checked |
| R17 | Same role, same decision (**now also every count and every flag of the same kind**). | LAsset p.4 (III-C-3: "self-consistency checks"); P3164 p.18 (two signals holding the same SRAM address are both structural assets). | Checked |
| R18 | Objective: the one most at risk. | SA-EDI doc p.16 [PDF p.24] (7.5.1 b: exactly one Security Objective per APSO object). | Carried |

## Change log

Each entry gives the change, the evidence in the D1 outputs, the source basis, and what it changes in earlier
decisions. Line numbers are the source line numbers printed at the start of each RTL line, unless marked "input file
line" (the line of the `.txt` input itself).

### C1. Define the module's boundary in files with several entities (new R8b)

- **Evidence.** D1 said "each port through which the value enters or leaves the module" but never said what "the
  module" is when the file holds several entities. The TRNG output lists the enable setting at every entity edge:
  `bus_req_i.data`, then `enable_i` of `neoTRNG`, then `en_i` of `neoTRNG_cell`; it also lists `data_o` of `neoTRNG`
  and `rnd_o` of `neoTRNG_cell`. Both entities are instantiated inside the same file (lines 128 and 296). The cache
  output lists `wdata_i` and `rdata_o` of `neorv32_cache_memory`, which `neorv32_cache` instantiates (line 273), next
  to the parent's own data ports. One value, one path, several listed hops.
- **Basis.** LAsset Table II puts the elements of its sub-modules that carry the key and the state on the secondary
  side, and only the top module's elements on the primary side (LAsset p.5). Nath & Tan Case 2 lists the
  connected top-module port instead of the sub-module element (Nath & Tan p.5). LAsset III-C-4 keeps one primary per
  path (LAsset p.4). Storage inside a sub-unit stays a holder, as in SA-EDI's watchdog and P3164's ROM example.
- **What changes.** TRNG and cache lose their sub-unit ports. Bus, sys and others are unaffected: their entities are
  siblings that no entity of the file instantiates (I checked the bus file: only `neorv32_bus_io_switch` instantiates
  another entity of the file, `neorv32_bus_reg`).

### C2. Holder must be in this file; carrier rule and transport by role (changed R8, R12)

- **Evidence, conflict between two D1 rules.** D1 R8 said: if a value has no register or port in the file, list the
  signal that carries it. D1 R12 said: fields marked `FORWARDS` are transport. In the CPU file both apply to the same
  signals. The CPU output lists `pmp_fault` and `lsu_err` as carriers of values held in sub-units ("no register or port
  holds it here"). But its own conceptual-asset note drops register, CSR, program-counter and privilege values as
  "only forwarded as record fields or moved one word at a time between sub-units". `csr_rdata` (line 120) has the same
  role as `pmp_fault`: a signal wired from a sub-unit's output that carries a complete value with no holder in the
  file. Same role, opposite decisions.
- **Evidence, the label is a poor proxy for transport.** The bus switch only routes request data between its ports,
  yet the map marks `a_req_i.data` as `CONSUMES`, not `FORWARDS` (input file line 684), because it passes through a
  multiplexer. The CPU's `ibus_rsp_i.data` is marked `FORWARDS` (input file line 386), yet it is where instructions
  enter the CPU. So the label misses real transport and catches real entry points.
- **Basis.** LAsset builds module-level primary assets from that module's own parsed elements (LAsset p.4, III-B), and
  its own output for a CPU top level names a read-data signal wired from a sub-unit as the primary structural asset
  (LAsset p.5, Fig. 5). P3164 counts RTL that "transports" the value (p.10) and, for a CPU, names instructions, data
  and the source and data registers (p.20-22). Routing between ports stays secondary (LAsset p.2; SAIF p.2 Example 1).
- **What changes (flagged reversal).** In the CPU file, D2 will list the ports where instructions, load and store
  data, and bus error reports enter or leave, and carriers for values that have no holder and no port in the file
  (for example CSR read data, register operands, program counter, privilege and debug mode). D1's executor left all of
  these out under R12. This reverses D1's outcome for the CPU because D1's rule was internally inconsistent there, not
  because of any score. Peripherals are unaffected: their bus data fields are read and stored, not routed.

### C3. The read register of a memory or constant table is a holder; build options (changed R8, new R8c)

- **Evidence.** The IMEM output omits `rdata`. In the build where the memory is a constant image, `rdata` is the only
  register that holds the program word (line 81: `rdata <= mem_rom_c(...)`). D1's own hand trace of the boot ROM keeps
  exactly this kind of register. In the writable build the executor treated `rdata` as a delayed copy of the memory
  (lines 128-131), and dropped it in every build.
- **Basis.** P3164 records the coefficient ROM's asset as its output register (p.13-14) and names the SRAM's Output
  Register as a conceptual asset (p.17). A structural asset is what physically supports the value (P3164 p.8).
- **What changes.** IMEM gains `rdata`. The boot ROM and FIFO traces are unchanged (see below).

### C4. Clock and reset defined by map role; reset and debug requests are events where they are acted on (changed R9, R7d)

- **Evidence.** D1 said "leave out clock and reset inputs" and, separately, listed reset requests as events. The sys
  output drops `rstn_wdt_i` and `rstn_dbg_i`, which are reset requests from the watchdog and the debugger: they gate
  the system reset sequencer (line 54; map `GATES sreg_sys`), they are not the module's own reset. The WDT output
  drops `rstn_dbg_i`, which is recorded in `reset_cause` (line 171; map `GATES reset_cause`), while listing
  `reset_cause` itself. The CPU output, in contrast, lists its debug-stop request and interrupt inputs. Same role
  (an event that enters and is acted on), opposite decisions.
- **Basis.** Nath & Tan leave out clock and reset (p.6); the map defines which element is the clock and which the
  reset (`SEQUENCES`, `RESETS`). Events entering and acting on logic carry Availability or Integrity (Nath & Tan p.3;
  P3164 p.9 question 3). The watchdog's reset indication must propagate unmodified (SA-EDI doc p.25 [PDF p.33]).
- **What changes (flagged).** Sys gains the two reset-request inputs; WDT gains the debug reset input. Their
  registered copies sent straight out again (the sys synchronizer outputs) are routing and stay out.

### C5. Outstanding-transfer flags are handshakes (changed R10)

- **Evidence.** The debug-transport output lists `dmi_ctrl.busy` as state. That flag is raised by a request (line 270)
  and lowered by the acknowledge (line 276). The bus output leaves out the gateway's `keeper.busy`, raised by a request
  (line 419) and lowered by the acknowledge or a timeout (lines 425-427), and the switch's pending-request flags.
  Same role, opposite decisions.
- **Basis.** As R10: handshake and enable signals are secondary or attack points (LAsset p.5 Fig. 5; SA-EDI doc
  p.25-26 [PDF p.33-34]).
- **What changes.** The debug transport loses its busy flag.

### C6. A held command is a strobe, even a reset command (changed R10, R7d)

- **Evidence.** The debug-transport output lists `dmi_ctrl.dmireset` and `dmi_ctrl.dmihardreset` as "reset requests".
  Both copy a host-written bit and drop once the unit is idle (lines 247-252): they are commands written to this
  module. The UART output leaves out the analogous `ctrl.clr_rx` and `ctrl.clr_tx` (written at lines 190-191, dropped
  every cycle at lines 173-174), and the WDT output leaves out `reset_wdt` and `reset_force` (lines 87-105). D1's word
  "reset request" in the events list collided with "request and command strobes" in the exclusions.
- **Basis.** SA-EDI's watchdog example: the service bit is a command cleared on the next cycle, and the listed assets
  are the timer and the timeout-assertion register, not the service bit (SA-EDI doc p.24-25 [PDF p.32-33]).
- **What changes (flagged).** The debug transport loses its two reset-command flags. Registers holding a reset the
  module *produces* for others (the WDT's timeout and access-violation reset registers) stay, under R7d.

### C7. Counts: keep a count only when counting is the module's job (changed R7c, new R10b)

- **Evidence.** D1 listed "the count of a timer" as state and "signals that only time ... a transfer" as an
  exclusion. The executor split one engine's counters across both: the UART output lists `tx_engine.bitcnt` and
  `rx_engine.bitcnt` but not `tx_engine.baudcnt` and `rx_engine.baudcnt`, which sit in the same records (lines 114-115
  and 127-128). The sys output lists the clock generator's count. Same kind of element, different decisions.
- **Basis.** SA-EDI lists timers, counters and clock generators as an asset type (doc p.10 [PDF p.18], Table 2), and
  its watchdog example makes the count the asset because the count *is* the watchdog (doc p.24 [PDF p.32]). A count
  that paces one transfer or computation only facilitates the data it paces, which is the secondary definition
  (LAsset p.2; SAIF p.2).
- **What changes (flagged narrowing of D1).** UART loses its two bit counts, TWI its bit count, the multiply/divide
  unit its iteration count, and the TRNG its sampling count. The watchdog count, the bus gateway's time-limit count
  and the clock generator's count stay.
- **The alternative I rejected.** Keeping every counter would also be consistent. I chose the narrower reading
  because the reference lists primary assets only, and these counts fit LAsset's secondary description. This is
  reasoning, not a measurement.

### C8. Program code named under Data (changed R7a)

- **Evidence.** D1's data kind did not name code. The IMEM and CPU files carry instructions as their main data.
- **Basis.** P3164 p.20 (instructions are a CPU core's conceptual asset); SA-EDI Table 2 (Code/Data).
- **What changes.** Wording only; it supports C2 and C3.

### C9. Smaller wording fixes

- `storage: not assigned` now also means "driven only by a sub-unit". The CPU carriers all show this value; without
  it an executor could read them as unused.
- "Merges of listed values" added to intermediates, so a signal that ORs several listed values together is not listed
  again (for example a write-back value merged from several results in the CPU file, line 330).
- The self-check list now covers the new rules.
- Step headings use words, not digits, to keep the prompt free of numbers.

### What I kept, and why

- The definition, the four questions, the direct-target test and the output contract.
- Listing data ports of peripherals (`in` and `out` data fields) and every field of a settings register: the executor
  applied these consistently across the peripherals I checked.
- Excluding per-transfer addresses. P3164 treats an SRAM address register as an asset "pending on the use case"
  (p.17-18); the D1 choice stands, and buffer pointers are named explicitly as state instead.

## Where the sources disagree, and the choice I made

- **Ports.** SA-EDI keeps ports as attack points, apart from assets (doc p.24-26 [PDF p.32-34]). LAsset Table II and
  Nath & Tan Case 1 put the top module's ports on the primary list (LAsset p.5; Nath & Tan p.5). Unchanged from D1:
  boundary ports that carry a conceptual asset are listed. New in D2: ports of sub-units are not, which LAsset and
  Nath & Tan both support.
- **Storage inside sub-units.** Nath & Tan would replace it with the connected top-module port (p.5). SA-EDI and
  P3164 name such storage directly (SA-EDI doc p.24 [PDF p.32]; P3164 p.14). D2 keeps the storage, because a register
  is the place the value is held.
- **State-machine state.** SA-EDI lists FSMs as an asset type (Table 2). SAIF says "states of an FSM" can be a
  secondary asset (p.2). D2 keeps state-machine state as primary, as D1 did.
- **Counters.** See C7.
- **Mode settings next to secrets.** As in D1: SAIF lists mode bits as primary (p.2) but its Example 2 calls a
  boot/normal state secondary to a key. D2 keeps held mode settings as primary.

## How the rules play out on the two design inputs (reasoning, not a score)

I re-counted both maps in this session from their `PORT` and `SIGNAL` lines. The counts are exact.

- **Boot ROM** (21 elements: 19 `PORT` lines, 2 `SIGNAL` lines). D2 keeps 2, the same as D1: the read-data register
  (holder of the word read from the constant table, R8) and the read-data field of the response port (R8). Left out:
  the clock (only `SEQUENCES`) and reset (only `RESETS`) (R9); address, strobe and direction fields, the registered
  read pulse and the acknowledge field (R10); the tied error field and the unused request fields (R13); the two whole
  records (R14).
- **FIFO** (27 elements: 11 `PORT` lines, 16 `SIGNAL` lines). D2 keeps 6, the same as D1: write-data input, read-data
  output, both storage elements (each primary under a different build option, R8c), write and read pointers (R7c).
  Left out: clock and reset (R9); the write, read and flush strobes at the ports and inside (R10); fill-state flags and
  the fill count (R10); the pointer-compare signal, next-value signals and the registered duplicate of the read pointer
  (R11).

## Expected effect on the tuning outputs (reasoning, not measured)

These are the decisions I expect D2 to flip, from the RTL I read. Nothing here is a score.

| Module file | Expected change from D1's output | Change |
|---|---|---|
| imem | add the read-data register | C3 |
| trng | drop the ports of the two sub-unit entities; drop the sampling count | C1, C7 |
| cache | drop the ports of the memory sub-unit; possibly add the bus error input, which the cache holds as an error flag | C1, C4 |
| cpu | add ports where instructions, data and bus errors enter or leave, and carriers for values held only in sub-units | C2 |
| debug_dtm | drop the busy flag and the two reset-command flags | C5, C6 |
| uart | drop the two bit counts | C7 |
| twi | drop the bit count | C7 |
| cpu_cp_muldiv | drop the iteration count | C7 |
| sys | add the two reset-request inputs | C4 |
| wdt | add the debug reset input | C4 |
| bus, spi, cpu_pmp, cpu_cp_cfu, hwspinlock | none from the rules I traced | - |

## What this breaks

- D2 outputs are not comparable element by element with D1 outputs on the ten files in the table above. D2 runs must
  go to their own output directory, and no metric may mix D1 and D2 runs.
- The CPU list will grow (C2). If CPU precision falls, that is the price of resolving D1's internal conflict, and it
  should be read separately from the other files.

## What would prove each change wrong, and what to read after the next run

Someone with the reference has to read these; I cannot.

- **C1 boundary.** If the sub-unit ports dropped from the TRNG and cache files are reference entries, C1 is wrong.
  Read: recall on elements whose entity another entity of the same file instantiates.
- **C2 carriers and transport.** If the new CPU carriers and ports are mostly false positives, the reference treats a
  wiring-only top level as secondary. Read: precision in the CPU file, split into carriers (`storage: not assigned`
  with `connections`) and ports.
- **C3 read register.** Read: whether the IMEM read-data register is a reference entry.
- **C4 events entering.** Read: whether the sys and WDT reset-request inputs are reference entries.
- **C5 and C6 handshake flags and held commands.** Read: recall misses among outstanding-transfer flags and held
  command registers (debug transport).
- **C7 counts.** If the bit, iteration and sampling counts are reference entries, the narrowing was wrong and D1's
  broader rule should come back. Read: recall misses among counters, by kind (pacing count vs timer count).
- **Consistency.** Read: run-to-run agreement across the three runs per file on sibling elements (pointer pairs,
  counters in one engine, fields of one settings register).

## Rule compliance

- No identifier from the design files or the processor appears in the prompt. Generic words that are also field
  names elsewhere (data, debug, lock, enable, state, valid) appear only as ordinary words, as in D1. I replaced
  "baud", which is a field name in this processor, with "bit-rate".
- No digits, quotas or proportions in the prompt. Step headings are words.
- No instruction to use HDL comments.
- Output contract as the brief gives it, with the one extra key `conceptual_assets` before `assets`, as the brief
  allows.
- LAsset Table I (p.5) prints list sizes for a few modules of this processor. I did not use them in any rule. Using
  them would mean inferring the reference, and turning them into targets would be a numeric quota.
