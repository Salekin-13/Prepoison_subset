The report was not written to `E:/jobs/ff/test/Prepoison_subset/blind_agent/critic/A1/report.md`: the Write call was refused because subagents may not write report files. The full report follows instead of DONE.

# Critic report: prompt A1, tuning run r0 (15 modules)

## Summary

- The executor followed the format and the core definition well on the small peripherals. It listed control registers as whole records, interrupt outputs, memory arrays and stored error flags, and it kept bus fields, handshakes and counters out. Most faults sit at three boundaries where the prompt gives two opposite rules for the same element.
- **Boundary 1: values driven by a sub-unit.** The "produced by a sub-unit" case and the "only forwarded" case both match the same elements, and the map's `mode` is often null. As a result, the CPU wrapper lists 7 sub-unit outputs and drops their direct siblings, and FIFO read ports are primary in two peripherals but carriers in two others.
- **Boundary 2: capture registers versus delayed copies.** The prompt calls "a register that copies another element" secondary, but that wording also fits every register that captures an input and holds it, which the prompt calls primary. The bus file treats four such registers three different ways.
- **Boundary 3: state machines, counters and one-cycle flags.** Step D calls them bookkeeping. Step B and the unit list call some of them assets ("counters ... that trigger a reaction", "current grant", "timeout and error decisions", "reservations"). The executor's decisions follow the meaning of the names, not a test.
- **Output faults are minor.** `element_roles` lists elements by bare name. In files with several entities, that list cannot hold two elements that share a name, so the bus and TRNG outputs repeat names or put one name in two lists.

## Scope and notation

- **Read in full:** the brief, the map format, the prompt and all 15 outputs.
- **Inputs read:** neorv32_cpu (wrapper, 7 primaries, all of them sub-unit record fields), neorv32_bus (6 entities, several judgement calls, and fields where the RTL overrides the map) and neorv32_trng (security peripheral, chain and sub-unit questions).
- **The other 12 modules:** findings on them come from their outputs alone and are marked *(output only)*. Their RTL was not checked.
- **Line references:**
  - "RTL n" is the source line number printed in the input file.
  - "map L" is a line of the input file.
  - "prompt L" is a line of `prompts/A1/prompt.md`.
  - "out L" is a line of that module's output JSON.
- **Counts:** the 15 outputs list 70 elements in total. I counted them by hand from the files. Nothing was run.

## 1. Instructions ignored, misread or applied inconsistently

**1.1 neorv32_cpu: "only forwarded" fields listed as primary.** Six listed elements are record fields that the map marks `handling: FORWARDS` and `storage: not assigned`:

| element | map line |
|---|---|
| ctrl.pc_cur | L432 |
| ctrl.pc_nxt | L433 |
| ctrl.pc_ret (CONSUMES+FORWARDS) | L434 |
| ctrl.cpu_priv | L469 |
| ctrl.cpu_debug | L472 |
| frontend.instr | L476 |

- Prompt L129-130 says a forwarded value "belongs to another unit; nothing here is its holder".
- The executor used the sub-unit case instead (prompt L124-125). That case asks for "`connections` with mode `out`". In this file the connection sits only on the whole record: `ctrl` has formal ctrl_o (map L428) and `frontend` has formal frontend_o (map L474). Every `mode` in this file is null.
- So neither case applies literally. The executor chose element by element, from what the names mean. See 4.1.

**1.2 neorv32_cpu: rs1, rs2, rs3 called "indexed reads".** They were put in copy_or_part as indexed reads of the register file (out L33-36, L65).
- Prompt L152-153 defines an indexed read as a `SELECTED_BY` read from an array.
- Map L483-488 shows only connections to the regfile sub-unit's rs1_o, rs2_o and rs3_o (RTL 324-326). This module has no array and no SELECTED_BY record.
- Under the reading the executor used for ctrl.pc_cur, these three signals are this module's holders of "register file contents", which the prompt names as a core asset (prompt L205). The same rule was applied in one place and not in the other.

**1.3 neorv32_bus (neorv32_bus_amo_rmw): delayed copies listed as primary.** arbiter.cmd, arbiter.rdata and arbiter.wdata are listed. Each is a clocked copy of a next-value helper (`arbiter <= arbiter_nxt`, RTL 763; map L2043-2046), and each helper COPIES an input port:

| helper | copies | RTL | map |
|---|---|---|---|
| arbiter_nxt.cmd | core_req_i.amoop | 778 | L2094 |
| arbiter_nxt.wdata | core_req_i.data | 779 | L2101 |
| arbiter_nxt.rdata | sys_rsp_i.data | 785 | L2097 |

- Prompt L154-155 calls "a register that copies another element or another register's next value" a delayed copy. Prompt L135 says staging and delayed copies are secondary.
- The executor's own reason for arbiter.rdata (out L92) calls it a register "buffering the memory word read".
- One part was right: the executor overrode the map's `storage: none` for these fields (map L2047-2077) because of RTL 763.

**1.4 Coverage check not met.** Prompt L182-183 says each conceptual asset needs a holder in the list, or "a note in the analysis saying why no element of this module holds it". Three outputs leave `held_by` empty with no reason:

- **neorv32_cpu_cp_muldiv** *(output only)*: the conceptual asset "operand values" (out L17-20).
  - The executor's own purpose text says the unit "takes the two register operands rs1_i and rs2_i".
  - Prompt L127-128 covers this: a value received and used without storing has its input port as the holder. If the value is stored, the storing register is the holder. Either way, some element should be named.
- **neorv32_cache** *(output only)*: "the decision to bypass the cache" (out L17-20).
  - Its chain names ctrl.buf_dir.
  - Prompt L107-108 says the holder of a bypass is "the stored setting or mode that turns them on".
- **neorv32_imem** *(output only)*: "Bus acknowledge" (out L13-16).

**1.5 neorv32_cpu: role-list rule for empty ports not applied.** holds_nothing is empty (out L53).
- ibus_req_o and dbus_req_o are whole record ports marked undriven (map L368, L387). icc_tx_o has drive `tied` (map L356).
- Prompt L145-147 puts all three under "holds nothing". The executor put them in interface_carrier (out L54-60).
- This does not change the asset list.

## 2. Inconsistent decisions

### Within neorv32_bus (RTL read)

**2.1 locked (primary) versus keeper.lock (control).** locked is in neorv32_bus_switch; keeper.lock is in neorv32_bus_gateway. They have the same role: a register that captures the requester's lock flag when a transfer starts and keeps the unit busy until the lock is released.
- **locked:** set at RTL 111 (`locked_nxt <= b_req_i.lock & a_req_i.lock`) and RTL 57, and used at RTL 88-92 and 100-104.
- **keeper.lock:** set at RTL 420 (`keeper.lock <= req_i.lock` when idle), used at RTL 426. The map shows it COPIES req_i.lock (map L1921).
- The sibling check (prompt L175-177) asks for one decision for both.

**2.2 Registered captures of a bus value: four registers, three outcomes.**
- arbiter.cmd, arbiter.rdata, arbiter.wdata: primary (see 1.3).
- device_req_o in neorv32_bus_reg: copy_or_part (RTL 222 `device_req_o <= host_req_i` under the strobe; map L838-844).
- keeper.lock: control. locked: primary.

**2.3 State registers.**
- state in neorv32_bus_switch (RTL 55): primary, as "current grant".
- state in neorv32_bus_amo_rvs (RTL 906-930): primary, as "reservation".
- arbiter.state in neorv32_bus_amo_rmw (RTL 773-808): bookkeeping, as "sequencing". Yet this register also decides whether the computed value or the core's data is written to memory (RTL 813), and when the core gets its acknowledge (RTL 827-828).
- The split can be defended, but only by letting the unit list (prompt L210-212) override Step D (prompt L161-163). See 4.3.

### Within neorv32_cpu (RTL read)

**2.4 Fault reports from sub-units treated differently.** All three below are fault reports that a sub-unit sends to the control unit. Prompt L105 names fault requests as availability assets.
- **pmp_fault: primary.** It comes from the PMP sub-unit (RTL 420) and is used by the control unit (RTL 257) and the load/store unit (RTL 392).
- **lsu_err: interface_carrier.** It comes from the load/store sub-unit (RTL 391) and is used by the control unit (RTL 272).
- **frontend.fault: interface_carrier.** It is the fetch-fault field of the frontend record (RTL 199).

**2.5 ctrl.cpu_priv (primary) versus ctrl.lsu_priv (interface_carrier).**
- Both are FORWARDS fields driven by the control sub-unit (map L469, L455).
- The executor puts lsu_priv in the "chain" of cpu_priv (out L20). No COPIES, CARRIES or SOURCES record links the two in this file.
- Prompt L100 names "the current privilege mode" as an asset. Nothing in this module shows that the data-access privilege is a copy of it.

**2.6 frontend.instr (primary) versus other sub-unit values (secondary).**
- frontend.instr is produced by the frontend sub-unit (RTL 199) and is listed.
- These are not listed: alu_res (ALU result, RTL 369), lsu_rdata (RTL 388), csr_rdata (RTL 263) and rs1, rs2, rs3 (RTL 324-326).
- All of them are values produced by sub-units whose RTL is not in the file.
- Prompt L102-103 names "the module's computed result" as an integrity asset. In other modules the executor lists computed-result registers (muldiv mul.prod, cfu xtea.res, bus alu_res). Only the wrapper drops the ALU result.

### Across modules

**2.7 FIFO sub-unit read ports.**

| module | elements | decision | source |
|---|---|---|---|
| neorv32_twi | fifo.tx_rdata, fifo.rx_rdata | primary | out L45-52 *(output only)* |
| neorv32_trng | fifo.rdata | primary | out L41-44; map L405-407; RTL 166; connection mode null |
| neorv32_uart | rx_fifo.rdata, tx_fifo.rdata | interface_carrier | out L34 *(output only)* |
| neorv32_spi | tx_fifo.rdata, rx_fifo.rdata | interface_carrier | out L26 *(output only)* |

- All four have the same role: the read-data port of a buffer sub-unit that holds the module's payload.
- In TWI and TRNG the same payload also has a listed holder inside the file (engine.sreg; sample_sreg). Those two lists therefore name two points of one chain. Prompt L132-133 forbids that, unless the buffer counts as a separate asset.

**2.8 Latched operands.**
- neorv32_cpu_cp_cfu lists xtea.opa and xtea.opb (Confidentiality) *(output only)*.
- neorv32_bus lists arbiter.rdata and arbiter.wdata.
- neorv32_cpu_cp_muldiv names "operand values" but lists nothing (see 1.4).

**2.9 Objective for the same fault value.**
- neorv32_cpu_pmp gives fault_o "Availability" (out L41-44).
- neorv32_cpu gives pmp_fault "Integrity" (out L103-106).
- The objective is not scored, but prompt L104-105 and L192-194 point to Availability.

## 3. Reasons that contradict the definition, and omissions

### Listed with a reason that contradicts the prompt

**3.1 neorv32_cpu ctrl.pc_cur, ctrl.pc_nxt, ctrl.cpu_priv, ctrl.cpu_debug, frontend.instr.**
- The reasons say the sub-unit "drives it, so this field is where the current PC is held in this module" (out L82).
- The definition of primary (prompt L28-30) is "the place where it is held". The map says this module holds nothing in these fields (`not assigned`, FORWARDS).
- The reason argues "carried here". The prompt calls that secondary: "the ports and wires that carry a copy" (L32-33), and "being connected to an asset ... never makes it primary" (L36-37).
- Whether the decision is wrong depends on the conflict in 4.1. The reason as written contradicts the definition.

**3.2 neorv32_bus arbiter.rdata.** The reason "Register buffering the memory word read" (out L92) describes staging, which prompt L135 calls secondary.

**3.3 neorv32_bus keeper.cnt.** The reason is "bus-timeout counter whose top bit ends a hung transfer" (out L89).
- This counter resets at each new transfer (RTL 418) and counts the cycles of one transfer (RTL 422). Step D (L161-163) puts counters that step an operation under bookkeeping.
- Step B (L101-102) allows "counters ... whose value ... triggers a reaction". The prompt supports both readings.
- The reaction itself (keeper.err) is also listed. neorv32_wdt lists the same pair (cnt and hw_rst_timeout), so the two modules are at least consistent with each other.

**3.4 neorv32_bus keeper.err.** It is a one-cycle pulse: cleared every clock (RTL 415), set at RTL 424, and it gates rsp_o.ack and rsp_o.err (RTL 400-401).
- Step D (L158-160) calls "comparison results that only gate other assignments" transient controls.
- Step B (L104-105) calls timeout requests assets.
- This is the same conflict as 3.3.

### Left out although the prompt's own definitions call for them

From modules whose RTL I read:

- **3.5 neorv32_cpu alu_res** (RTL 369). Prompt L102-103 calls the computed result an asset, and the sub-unit case (L124-125) gives this signal as its holder in the module.
- **3.6 neorv32_cpu lsu_err (RTL 391) and frontend.fault (RTL 199)**, if pmp_fault stays (prompt L105; sibling check L175-177).
- **3.7 neorv32_cpu rs1, rs2, rs3** (RTL 324-326; prompt L205 "register file contents"). The alternative is that the prompt means wrapper modules to list nothing that sub-units produce. In that case the 7 listed fields should go instead.
- **3.8 neorv32_bus keeper.lock** (RTL 420), if locked stays. Otherwise locked should go (see 2.1).
- **3.9 neorv32_trng: no clear omission.** Prompt L223-225 names "the internal state of the noise source". The executor named latch (storage none, map L488; RTL 435). It called the clocked noise-path registers sync (RTL 470) and debias_sreg (RTL 334) copies, which matches Step D's delayed-copy rule.

From outputs only:

- **3.10 neorv32_uart and neorv32_spi FIFO read ports**, if the TWI and TRNG decisions are right (see 2.7).
- **3.11 neorv32_cpu_cp_muldiv rs1_i and rs2_i**, or the register that stores them (see 1.4).

## 4. Prompt wording that explains points 1-3

**4.1 The sub-unit case and the "only forwarded" case overlap (prompt L124-130).**
- "Use the first case that applies" (L116) does not settle it. The sub-unit case depends on "`connections` with mode `out`", and two things in the inputs block it:
  - `mode` is often null: every connection in neorv32_cpu (map L343-515) and the FIFO instance in neorv32_trng (map L396-415).
  - The connection sits on the whole record, while the fields carry `handling: FORWARDS` (cpu `ctrl` and `frontend`).
- L58-59 explains mode `out` but not null.
- Explains 1.1, 1.2, 2.4-2.7, 3.1 and 3.5-3.7.

**4.2 "Delayed copy" is too broad.**
- L154-155 defines it as "a register that copies another element or another register's next value". That also matches every capture register, including:
  - the "Stored here" holders of L118-121;
  - "the register that keeps the value until the next deliberate update" of L134.
- The worked example shows only an unconditional one-cycle copy (sig_dly_q, L233-234). It does not show where the line falls.
- Explains 1.3, 2.1, 2.2 and 3.2.

**4.3 Three places give opposite defaults for the same kinds of element.**
- Step D says secondary for "sequencing state machines" and "bit and beat counters" (L161-163), and for "comparison results that only gate" (L158-160).
- Step B says asset for "counters and timers whose value ... triggers a reaction" (L101-102) and for "timeout ... requests" (L105).
- The unit list says asset for "current grant, selected target, timeout and error decisions, reservations" (L211-212).
- The unit list adds "Every entry still has to pass Steps C to E" (L201-202). But Step D would then reject "current grant" and "reservations", which are state machines.
- Explains 2.3, 3.3 and 3.4.

**4.4 The coverage check is too loose.**
- It lets a named conceptual asset stay without a holder if a note says why (L182-183), but it does not require the note to name the Step C case that applies.
- Step C also has no case for a value that is both used in the computation and stored on the way, so operands get dropped.
- Explains 1.4 and 2.8.

**4.5 Buffers are left open.**
- The communication list (L220-222) calls "buffers" assets and "buffer handshakes" secondary.
- The chain rule (L132-133) allows one holder per chain.
- Nothing says whether a buffer sub-unit's read port belongs to the same chain as the shift register that fills or drains it.
- Explains 2.7.

**4.6 The output format cannot hold same-named elements.**
- `element_roles` (L278-291) is keyed by bare name, and L196 says "Each element appears in assets only once".
- In files with several entities, one name is declared several times:
  - neorv32_bus: clk_i, rstn_i, x_req_o, x_rsp_i, core_req_i, core_rsp_o, sys_req_o, sys_rsp_i, state.
  - neorv32_trng: clk_i, rstn_i.
- Explains 5.1-5.3.

**4.7 "Stored here" reads as a test on map values (L119-120: "`storage` `edge` or `mixed`").**
- For a clocked assignment of a whole record, the map leaves the fields at `storage: none`: bus map L2047-2077 against RTL 763.
- L15-16 says the RTL is the authority, but L119-120 reads as a map test.
- The executor overrode the map correctly this time. A less careful run would drop or misclassify these fields.

## 5. Output faults

- **5.1 neorv32_bus: names in two role lists.** x_req_o, x_rsp_i, core_req_i and sys_req_o each appear both in holds_nothing (out L20) and in interface_carrier (out L26, L27, L76, L78).
  - Each pair is two different elements of different entities that share a name: x_req_o at map L759 and L960, core_req_i at L1616 and L1699, sys_req_o at L1656 and L1731.
  - The name-only list still breaks the "single list" rule (prompt L290).
  - clk_i and rstn_i are declared by six entities but appear once.
- **5.2 neorv32_trng:** clock_or_reset repeats clk_i and rstn_i three times each (out L28).
- **5.3 neorv32_bus: `state` listed twice.** The assets name `state` twice, with different entities (out L87, L95). This is correct per the map, but names are compared as declared, so the two entries collide. Prompt L196 does not say what to do in this case.
- **5.4 neorv32_cpu:** undriven and tied record ports were placed in interface_carrier (see 1.5).
- **5.5 Extra keys inside `analysis`:** neorv32_bus has coverage_notes (out L16) and neorv32_debug_dtm has notes (out L31). They are harmless and do not touch the required shape.
- **5.6 Names in the three read modules are clean.** Every listed element is declared in the map with the stated entity. There are no slices, constants, instance names, or duplicates within one entity. Names in the other 12 modules were not checked against their maps.
- **5.7 conceptual_assets used as a notes field:** neorv32_trng (out L21-24) and neorv32_imem (out L13-16). This is not a contract fault, but it makes real coverage gaps (1.4) harder to spot among filler entries.

## 6. The three changes I would make first, most important first

These describe what to change, not the new wording.

**1. Make the sub-unit rule decidable, and state its precedence.**
- Say how to recognise an element driven by a sub-unit when the map's `mode` is null, or when the connection sits on the parent record. For example: read the formal port's direction from the instantiation or component declaration in the RTL.
- Say whether that case wins over `handling: FORWARDS`.
- Say whether a buffer sub-unit's read port is a separate holder from the in-file register that fills or drains it.
- **Fixes:** 1.1, 1.2, 2.4-2.7, 3.1, 3.5-3.7, 4.1 and 4.5.
- **Breaks:** comparability with r0 on neorv32_cpu, neorv32_uart, neorv32_spi, neorv32_twi and neorv32_trng.
- **Check after the next run:**
  - The four FIFO peripherals make the same decision on their buffer read ports.
  - In neorv32_cpu, all sub-unit values of one kind get the same decision: the faults (pmp_fault, lsu_err, frontend.fault), the results (alu_res and frontend.instr), and the privilege fields.

**2. Separate "delayed copy" from "capture register" with a test that reads the RTL.**
- One possible test: a register loaded every clock from a single source is a copy; a register loaded only under a condition and held across cycles is a capture.
- Put one example of each in the worked example.
- **Fixes:** 1.3, 2.1, 2.2, 3.2 and 4.2.
- **Breaks:** comparability on neorv32_bus, and possibly neorv32_cpu_cp_cfu (xtea.opa, xtea.opb) and neorv32_debug_dtm.
- **Check:** in neorv32_bus, the decisions on locked, keeper.lock, device_req_o and arbiter.cmd/rdata/wdata all follow the stated test.

**3. Give one ordered test for state registers, counters and one-cycle flags.**
- The test must reconcile Step D with Step B and the unit list on three questions:
  - When is a state register "the current grant" or "a reservation", and when is it "sequencing state"?
  - When is a counter "a timer that triggers a reaction", and when is it a beat counter?
  - When is a one-cycle flag "a timeout or fault request", and when is it "a comparison result that only gates"?
- **Fixes:** 2.3, 3.3, 3.4 and 4.3.
- **Check:** each of these pairs follows the stated test: bus-switch state against amo_rmw arbiter.state, keeper.cnt against wdt cnt, and keeper.err against sc_fail and the TRNG fifo_clr.

**Not in the top three, but cheap:**
- Add the entity to every `element_roles` entry, and say how to list two same-named elements of different entities (5.1-5.3).
- Require every empty `held_by` to name the Step C case that leaves it empty (1.4, 4.4).