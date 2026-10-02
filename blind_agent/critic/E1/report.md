Writing `E:/jobs/ff/test/Prepoison_subset/blind_agent/critic/E1/report.md` was refused: the harness does not let subagents write report files. The report follows instead of DONE.

# Critic report: prompt E1, tuning run r0

## Scope and how to read this

- I read the task brief, `MAP_FORMAT.md`, `prompts/E1/prompt.md` and all 15 outputs in `runs/tuning/E1/r0`.
- I read the input files of three modules:
  - **neorv32_bus**: six entities and the most decisions.
  - **neorv32_trng**: the prompt's [Home] rule names random state directly, yet the output lists one element.
  - **neorv32_cpu**: a wrapper with no registers, where the prompt's rules fit worst.
- For the other 12 modules I did not read the RTL. Points about them use the executor's own text and the lines it cites. They are marked *(executor text)*.
- I saw no reference list and no scores. I cannot say whether a given inconsistency costs precision or recall.
- `Lnn` means a line of `prompt.md`. `RTL nnn` means the source line number printed in the input file.
- Points marked "argued" are my reasoning. Everything else is what the files say.

---

## 1. Instructions ignored, misread or applied inconsistently

**1.1 Step C (L41, "Map each conceptual asset to elements") is left unfinished without saying so.**
Several outputs name a conceptual asset in `analysis` and then map no element to it.
- **trng:** names "Unbiased entropy" (Integrity) and "Supply of random bytes" (Availability), with no listed element for either. Elements that hold them exist:
  - `debias_sreg` (RTL 334) and `sync` (RTL 470) hold raw random state.
  - `enable` (RTL 105) starts and stops generation.
- **cpu:** names the register file, the privilege mode and the program counter. It says each home is in a sub-unit, then rejects every relay of those values.
- **dtm** *(executor text)*: "CPU state ... lives outside this file".
- **bus:** at least says so outright ("no home in this module").

The prompt allows an empty result only when nothing passes Step B (L214). It says nothing about an asset that passes Step B but has no home in the file (see 4.6).

**1.2 The "already listed" condition of the [Hallway] sub-unit clause is skipped.**
L75 rejects "Ports of an instantiated sub-unit that receive or return a value **already listed** at its home or at an outer door".
- **cpu:** these were rejected as Hallway because "the home is in a sub-unit": `ctrl.cpu_priv` (FORWARDS), `ctrl.pc_cur`, `rs1`, `rs2`, `rs3`, `lsu_err` and `frontend.fault`. None of those homes is in the file or listed, so the condition fails.
- The prompt's own examples list the privilege-mode register (L167) and the program counter (L162) as homes.
- **pmp** *(executor text)*: `ctrl_i.cpu_priv` and `ctrl_i.lsu_priv` are rejected the same way.

**1.3 The [Door] rule is applied beyond its words (cpu).**
`msi_i`, `mei_i`, `mti_i` and `firq_i` (RTL 75-78) are listed as Doors, but neither door rule covers them.
- L65 names "an interrupt, timeout, halt or reset request **output**". These are inputs.
- L187 asks that an input door's records "lead into a home or into the result". In the map:
  - `msi_i`, `mei_i` and `mti_i` only SOURCE `irq_machine` (RTL 276), a wire into the control sub-unit.
  - `firq_i` only connects to that sub-unit (RTL 268).
  - The file holds no home and no result.

These four may still be right in the reference's view. The prompt does not support them.

**1.4 A map field is contradicted (bus, low impact).**
- `a_rsp_o.err` was rejected with the reason "nothing originates it here".
- The map marks it ORIGINATES, because it is gated by `sel` (RTL 165).
- The RTL agrees with the executor: it is a gated pass-through of `x_rsp_i.err`. See 4.10.

**1.5 The same role gets different labels (analysis only, not the list).**
- Enable bits: `ctrl.enable` is a Handle in uart, twi and wdt, but an Ordinary setting in spi. trng `enable` is also an Ordinary setting.
- Busy flags: Handle in uart (`tx_engine.busy`) and twi (`engine.busy`), but Shared interface in spi (`rtx_engine.busy`).

**What was done correctly:**
- In bus, every register in every entity got an explicit decision (L41). This covers `state`, `sel_q`, `locked`, `a_req`, `b_req`, `keeper.*`, `arbiter.*`, `alu_res`, `sc_fail` and the registered ports of `neorv32_bus_reg`.
- cpu correctly says the entity has no registers: every SIGNAL line in its map is `"kind":"signal"`.

---

## 2. Inconsistent decisions (same role, different decision)

**2.1 The register that raises or holds a reset or timeout event.**
- **wdt** *(executor text)*: `hw_rst_timeout` and `hw_rst_access` are listed as [Home].
- **bus gateway:** `keeper.err` (RTL 424) is listed as [Home].
- **sys** *(executor text)*: `sreg_sys` and `sreg_ext` are rejected as [Handle], because each "only delays the release". Yet `rstn_sys_o` is driven from `sreg_sys` (line 59).
- L96 gives this role the decision "register that raises the timeout: List [Home]".

**2.2 Request events, by direction.**
- **cpu:** the interrupt request inputs are listed. The debug halt request `dbi_i` (RTL 79) is rejected as [Handle]. In the map it has the same shape as `firq_i`: one connection to the control sub-unit (RTL 266 vs 268).
- **sys** *(executor text)*: the reset request inputs `rstn_wdt_i` and `rstn_dbg_i` are rejected as [Handle]. Their clocked copies `xrstn_wdt_o` and `xrstn_ocd_o` (lines 72-73) are listed as [Door]. L194 asks for one decision for "the input door and the output door of the same protected payload".
- **wdt:** `rstn_dbg_i` is rejected.

**2.3 Home and door of a computed result: three patterns.**

| Module | Result home | Result way out |
|---|---|---|
| muldiv | `mul.prod`, `div.quotient`, `div.remainder` listed [Home] | `res_o` listed [Door] |
| cfu *(executor text)* | `xtea.res` rejected [Hallway] ("output register that result_o forwards") | `result_o` listed |
| bus amo_rmw | `alu_res` (RTL 833-845) listed [Home] | `sys_req_o.data` (RTL 813) rejected, Shared interface |
| bus amo_rvs | `sc_fail` (RTL 957) listed [Status] | `core_rsp_o.ack` (RTL 963) and `core_rsp_o.data` bit 0 (RTL 964) rejected |
| bus gateway | `keeper.err` listed | `rsp_o.err` (RTL 401) listed; `rsp_o.ack` (RTL 400) also carries `keeper.err` but is rejected |

The single bus output uses three of these patterns.

**2.4 Bus or CSR data fields that carry the module's own protected content.**
- **Listed as doors:**
  - imem: `bus_req_i.data`, `bus_rsp_o.data`
  - cache: `host_req_i.data`, `host_rsp_o.data`, `bus_rsp_i.data`
  - cfu: `csr_wdata_i`, `csr_rdata_o`
- **Rejected as Shared interface:**
  - trng: `bus_rsp_o.data`. RTL 117 carries the random byte, and this is its only way out.
  - hwspinlock: `bus_rsp_o.data`, which carries the lock state.
  - pmp: `csr_o` and `ctrl_i.csr_wdata`, which carry the policy registers.
  - uart, spi, twi: `bus_rsp_o.data`, which carries the received bytes.
  - cpu: `dbus_req_o.data`.
- **Closest pair, cfu vs pmp:** each has a small CSR port to an array of registers whose whole content is the protected value (`key_mem` vs `pmpcfg`/`pmpaddr`). One is listed, the other rejected.
- **cache** *(executor text)*: `bus_req_o.data` is rejected as [Hallway] while `bus_rsp_i.data` is listed. These are the out and in directions of the same payload on the same side (L194).

**2.5 Error response fields.**
- gateway: `rsp_o.err` is listed.
- cache *(executor text)*: `host_rsp_o.err` is rejected, although the cache raises it from its own `ctrl.buf_err`.
- cpu: `ibus_rsp_i.err` and `dbus_rsp_i.err` are rejected.

**2.6 One access-violation value, two decisions.**
- pmp: `fault_o` is listed as [Status].
- cpu: `pmp_fault` is the same value, wired from the PMP sub-unit's `fault_o` (RTL 420). It is rejected as [Handle] ("guards memory accesses").

**2.7 Communication payload.**
- uart, spi and twi list their serial data pins as payload doors.
- cpu rejects `icc_rx_i.dat` and `icc_tx_o.dat` (inter-core message data, RTL 81-82 and 447-448) as Shared interface.
- That link is a point-to-point message channel, not "a general bus or register interface that carry every access to a set of registers" (L77).

**2.8 Debugger paths.**
- Rejected as override handles (L37, L73): cpu `dbi_i`, pmp `ctrl_i.cpu_debug`, cache `host_req_i.debug`.
- dtm lists registers of the debugger path itself: `tap_reg.dmi`, `dmi_ctrl.rdata`, `dmi_ctrl.err`.
- Inside dtm *(executor text)*:
  - Request side: `tap_reg.dmi` is listed and its copy `dmi_ctrl.wdata` is rejected as staging.
  - Response side: `dmi_ctrl.rdata` is listed, although the executor says `tap_reg.dmi` "also captures the response that is shifted out". By the executor's own staging rule, one of the two should go.

**2.9 Guard and state registers in bus.**
- amo_rvs `state` is listed.
- These are rejected as handles: bus_switch `locked` (guard bits, RTL 57, 88, 100), `keeper.busy`, `keeper.halt` and `arbiter.state`.

**2.10 Operand inputs.**
- muldiv and cfu list `rs1_i` and `rs2_i` as private payload doors.
- These are not listed: the AMO operand `core_req_i.data` (amo_rmw, RTL 779) and the cpu relays `rs1` and `rs2`.
- The structural difference is defensible. But the reason given ("may be secret program data") fits all of them equally.

---

## 3. Reasons that contradict the definition, and omissions the definition calls for

**Listed, but the reason contradicts the prompt's definition:**
- **3.1 bus `state` (neorv32_bus_amo_rvs).**
  - The reason, "decides whether a store-conditional may write", is the Handle definition (L24 "decides when, where or whether a value moves"; L73 guarding bits).
  - The RTL uses it only as a `case` selector (RTL 906) and a gating bit (RTL 944, 957).
  - L184 makes such a register a handle unless it is a policy or security counter. The executor argued neither.
- **3.2 cpu `msi_i`, `mei_i`, `mti_i`, `firq_i`.** See 1.3.
- **3.3 imem `rdata`** *(executor text)*.
  - It is listed because it captures the ROM word in one build option (L58).
  - In the RAM build it is the output register between the banks and `bus_rsp_o.data`, which L133 (SRAM output register: Hallway) excludes.
  - L189 forces one decision across builds, so two rules collide.
- **3.4 dtm `tap_reg.dmi`, `dmi_ctrl.rdata`.** L37 says "the path itself is a handle", and this module is that path.
- **3.5 sys `xrstn_wdt_o`, `xrstn_ocd_o`** *(executor text)*. Each reason calls it a clocked copy of an input that the same output rejects.

**Left out, though the prompt's definition includes them:**
- **3.6 trng `debias_sreg` (neoTRNG) and `sync` (neoTRNG_cell).**
  - `debias_sreg <= debias_sreg(0) & cell_sum` (RTL 334) and `sync <= sync(0) & latch(latch'left)` (RTL 470) both hold raw random state.
  - L52 lists "a key, seed or random-state register" as a home. The example at L147 says "Shift-register state registers: List [Home]".
  - The executor's Hallway reason fails L75: neither register is a copy of the value in `sample_sreg`. `sample_sreg` keeps only debiased bits, folded in by XOR when `debias_valid` is set (RTL 358-360).
  - They were removed through Step E (L45).
- **3.7 trng `bus_rsp_o.data`.**
  - It is the only outer port that carries the random byte (ports RTL 25-28; data RTL 117).
  - L63 names "the module's result output", and the buffer exception (L64, L77) covers the random pool.
- **3.8 cpu `dbus_req_o.data`.**
  - L168: "The sensitive payload a bus master sends: List, at its home or door in the master".
  - This entity is the master. Its home is outside the file, so the door is the only place left to list it.
- **3.9 sys `sreg_sys`, `sreg_ext`.** Per L96 (see 2.1).
- **3.10 bus `sys_req_o.data` (RTL 813) and `core_rsp_o.data` (RTL 964).** These are the ways out of listed homes. They belong on the list if gateway `rsp_o.err` is a door.

---

## 4. Prompt wording that is ambiguous, conflicting or easy to misapply

- **4.1 L63/L64 conflict with L77.**
  - [Door] lists "the module's result output" and the payload of "a module whose whole content is the protected payload (a memory or a buffer)".
  - [Shared interface] excludes "read value ... write value", except for "the memory/buffer case".
  - In most peripherals here, the bus read value is the only result output.
  - "Whole content" and "buffer" are undefined. Does a random pool count? A lock bank? A key array behind a CSR port? A policy array?
  - Explains 2.3, 2.4, 2.5, 2.7, 3.7, 3.8, 3.10.
- **4.2 L65 + L73 + L187.**
  - [Door] names request *outputs*. [Handle] names "reset inputs" and "debugger inputs". Input doors must lead to a home.
  - No rule covers request *inputs*.
  - No rule separates the module's own reset input from the reset requests it passes on.
  - Explains 2.2, 3.2, 3.5.
- **4.3 L73 vs L96.** L73 rejects "a register that only ... delays a strobe". L96 lists the "register that raises the timeout". A reset-stretching shift register does both. Explains 2.1, 3.9.
- **4.4 L54 vs L120.** L54 lists "a register ... whose content is the payload the module exists to ... send". L120 rejects "Input buffer, output buffer" as Hallway. A result register fits both. Explains 2.3, 3.3.
- **4.5 L45 (Step E).** "If the only honest description is 'the attacker uses this element to reach another element', remove it" fits any upstream register in a chain. It overrides L52 and L147. Explains 3.6.
- **4.6 L41 and L75 (wrapper case).** No rule covers an asset that passes Step B but whose home is in a sub-unit outside the file. Explains 1.1, 1.2, 3.8.
- **4.7 L37.** "The path itself is a handle" gives no guidance when the whole module is the debug path. Explains 2.8, 3.4.
- **4.8 L24/L73 vs L56 ("debugger authorization state").** No test separates a policy register from a guarding bit. Explains 2.9, 3.1.
- **4.9 L184-185 cite CONSTRAINS / CONSTRAINED_BY.** MAP_FORMAT.md defines only SEQUENCES, RESETS, SELECTS, GATES, CARRIES and SOURCES (plus their receiving forms). None of the three maps I read contains CONSTRAINS. The executor may hunt for records that do not exist.
- **4.10 L187 says ORIGINATES fields "are created by this module".** The analyser also marks gated pass-throughs as ORIGINATES (bus `a_rsp_o.err`, RTL 165). Explains 1.4.
- **4.11 L62 "a private payload input" is undefined.** Any operand can be called private. Explains 2.10.
- **4.12 L69 limits [Status] to "a register or output".** The same fault value is Status at its source but a Handle or Hallway when it is a wire in a wrapper. Explains 2.6.
- **4.13 L233: `rejected` has no `entity` key.** bus rejects `state` (bus_switch) and lists `state` (amo_rvs). The two cannot be told apart without reading the `why` text.
- **4.14 Minor gaps.**
  - The watchdog example decides the reload *wire* (L101) but not the stored reload register (L91). wdt lists `ctrl.timeout`, and nothing settles that either way.
  - No rule covers metadata arrays (address tags, valid bits) that decide which stored data is served. cache rejects `tag_mem` and `valid_mem` as handles *(executor text)*.

---

## 5. Output faults

- **Names checked against the RTL (bus, trng, cpu):** every listed name is declared in the stated entity. No faults found.
  - bus: `keeper.cnt` and `keeper.err` (record at RTL 343-350, gateway); `rsp_o.err` (RTL 308); `alu_res` (RTL 743, amo_rmw); `state` and `sc_fail` (RTL 894-895, amo_rvs).
  - cpu: RTL 75-78.
  - trng: `sample_sreg`, RTL 274, neoTRNG.
- **Names not checked:** the other 12 modules, whose inputs I did not read. For example, cache `data_mem_b0..b3` under `neorv32_cache_memory`.
- **Duplicates:** I read each of the 15 asset lists and found none.
- **Contract:**
  - All 15 outputs have `module`, `analysis` and `assets`, in that order.
  - `analysis` has `purpose`, `conceptual_assets` and `rejected`.
  - Objectives are spelled exactly.
  - Every `role` value is from the allowed set.
- **Soft faults:**
  - Some `rejected` entries bundle several elements: bus ("same for b_req_i.priv, x_req_o.priv and the debug tags"), wdt ("likewise src, priv, ..."), uart ("Same decision for ctrl.irq_rx_half, ..."). This means the per-element decisions that L41 asks for cannot be audited.
  - Same-name elements in different entities are ambiguous in `rejected` (4.13).

---

## 6. The three prompt changes I would make first

**1. One test for when a bus or register-interface data field is a door, applied the same way in both directions.**
- Proposed rule (argued):
  - A field is a door when it is the only path by which the module's protected value enters or leaves. That value can be a stored array, a pool, a key or policy array, a computed result or a raised event.
  - Its partner field in the other direction gets the same decision.
  - Any other such field is shared interface.
- Ties to 2.3, 2.4, 2.5, 2.7, 3.7, 3.8, 3.10 and 4.1.
- It comes first because it touches the most outputs: trng, hwspinlock, pmp, uart, spi, twi, cpu, imem, cache, cfu and bus.
- **What it breaks:** comparability with r0 on every module that has a bus data port.
- **What to read after the next run:**
  - Do cfu and pmp get the same decision for their CSR data ports?
  - Do trng, hwspinlock and imem agree on `bus_rsp_o.data`?
  - Do amo_rmw, amo_rvs and the gateway follow one home-plus-door pattern?

**2. Make request events independent of direction, and fix the "delays a strobe" clause.**
- Say whether interrupt, halt and reset requests that arrive from another unit are doors or handles.
- Separate the module's own clock and reset inputs from the requests it passes on.
- Say that the register that raises or holds an event is a home, even when it also stretches or delays it.
- Ties to 2.1, 2.2, 3.2, 3.5, 3.9, 4.2 and 4.3.
- **What to read after the next run:**
  - In cpu, do `dbi_i` and `firq_i` get the same decision, or a stated reason to differ?
  - In sys, do each request input and its clocked output copy agree?
  - Do `sreg_sys`, `hw_rst_timeout` and `keeper.err` agree?

**3. Define a home by the value it holds, and limit Step E to handles and hallways.**
- Proposed rule (argued):
  - A register that holds a distinct form of the protected value is a home. Examples are raw random state and an accumulated result.
  - Only a register that holds the *same* value as an element already listed is a staging copy.
  - Step E removes handles and hallways, never upstream homes.
  - One sentence should settle whether a result register is a home or an output buffer.
- Ties to 2.3, 3.3, 3.6, 4.4 and 4.5.
- **What to read after the next run:**
  - Does trng decide `debias_sreg` and `sync` by citing [Home] rather than Step E?
  - Do muldiv, cfu and amo_rmw use one pattern for result registers?

**Constraints on all three:**
- Each new rule needs a source and page in the rationale (brief rule 4).
- Examples must stay generic (brief rule 1).
- No quota wording (brief rule 2).

The wrapper case (4.6) and the debug-path case (4.7) are next in line. They affect only cpu, pmp, dtm and bus, but each leaves conceptual assets with no element.