Note: the write to `E:/jobs/ff/test/Prepoison_subset/blind_agent/critic/B1/report.md` was refused by the harness ("Subagents should return findings as text"). The report is below and has not been saved to disk.

# Critic report: prompt B1, tuning run r0

## Scope and method

- I read the brief, the map format, prompt B1 and all 15 outputs.
- I read the RTL and map for three modules only. These were `neorv32_cpu`, `neorv32_debug_dtm` and `neorv32_trng`.
  - **cpu:** the output lists 16 elements, yet the output itself says the file holds no register.
  - **dtm:** the output lists one debug channel in seven places.
  - **trng:** it is a security peripheral, and its output names a counter as the decision.
- Tags used below:
  - **[RTL]** means I checked the finding against the input file.
  - **[output]** means the finding rests only on the output and the prompt. I did not read that module's RTL, so the finding is not verified.
- Line citations:
  - `P:nn` is a line of `prompts/B1/prompt.md`.
  - `src nn` is an RTL source line number, as printed in the input file.
  - `<module>.json:nn` is a line of that output file.
- I saw no reference list and no score. Nothing below says whether any element is in the reference.
- I counted every number by hand from the files named. I could run no code. Each count is exact for those files.

## Summary

In the peripheral modules the executor follows the prompt closely. Most of its departures trace back to three places where the prompt contradicts itself:

- **(a) Wrapper files.** The processor-core example (P:180) says the program counter, the general-purpose registers and the privilege mode are assets. In a file that only wires sub-units together, the FORWARD rule, the CARRIER rule and the "a register" wording say these are not assets.
- **(b) Copies and intermediate values.** STORE includes payload "the module computes" (P:96). The AES example (P:178) and the copy rule (P:153) say otherwise.
- **(c) Address and instruction registers.** CORE includes them (P:103, P:107). Step E says an element that only selects is a lever (P:129, P:131).

The three changes in section 6 target (a), (b) and (c), in that order.

## 1. Instructions ignored, misread or applied inconsistently

**1.1 cpu [RTL]: the FORWARD rule is ignored for internal record fields.**
- P:141 says record fields with map handling `FORWARDS` get the tag FORWARD.
- `neorv32_cpu` has 39 `ctrl.*` fields and 5 `frontend.*` fields (hand count from the map, exact).
  - All 44 have handling `FORWARDS`. `ctrl.pc_ret` also has `CONSUMES`.
  - All 44 have storage `not assigned`.
- None of these 44 is tagged FORWARD. They are spread over LEVER, CARRIER, BOOKKEEPING and the asset list (cpu.json:18-20, 26-36).
- Port fields with the same map facts are tagged FORWARD (cpu.json:21).

**1.2 cpu [RTL]: "a register" is ignored for CORE and STORE (P:96, P:101).**
- `rs1`, `rs2` and `rs3` are tagged STORE.
  - They are declared as plain signals (src 111-113).
  - They are driven only by the register-file sub-unit's read ports (src 324-326).
  - Their map storage is `not assigned`.
- `ctrl.pc_cur`, `ctrl.cpu_priv`, `ctrl.lsu_priv`, `ctrl.cpu_debug` and `frontend.instr` are tagged CORE. They are fields of signals driven by sub-unit outputs (src 253, src 199).
- None of these eight is a register in this file. The executor says so itself: "It holds no register of its own" (cpu.json:3).
- It then stretches the STORE fallback in P:96 ("the first register in this file that holds the value") to cover wires.

**1.3 cpu [RTL]: the BOUNDARY map test is ignored (P:114).**
- P:114 requires a COPIES, CARRIES, SOURCES or DERIVES_FROM record between the port and its holder.
- `ibus_rsp_i.data`, `dbus_rsp_i.data`, `dbus_req_o.data`, `icc_tx_o.dat` and `icc_rx_i.dat` have no relationship record at all.
- Their whole records are wired straight to sub-units (src 196-197, 394-395, 447-448). There is no holder in this file.

**1.4 dtm [RTL]: the copy rule in Step G (P:153) is ignored.**
- One debug word is credited at three registers:
  - `tap_reg.dmi` (src 189, 196);
  - `dmi_ctrl.wdata`, loaded from a slice of `tap_reg.dmi` (src 267);
  - `dmi_ctrl.rdata` (src 274), which is copied back into `tap_reg.dmi` through `tap_reg.dmi_nxt` (src 229, then 189).
- It is also credited at four ports: `jtag_tdi_i`, `jtag_tdo_o`, `dmi_req_o.data` and `dmi_rsp_i.data`.
- P:153 allows one holder plus its BOUNDARY port. It says "other copies may not".

**1.5 dtm [RTL]: the Step E selector test (P:129, P:131) is not applied to `tap_reg.ireg` and `dmi_ctrl.addr`. Both are tagged CORE.**
- **`tap_reg.ireg`:**
  - It SELECTS `jtag_tdo_o` (src 206) and the four data registers (src 186, 193).
  - It GATES the `dmi_ctrl` fields (src 247, 258, 265).
  - Its only other record shifts its own bits out on TDO (src 204).
  - The executor's reason names a selection harm: "reach the DMI access path the debugger did not select" (dtm.json:78).
- **`dmi_ctrl.addr`:** its reason, "redirect a debug read or write to a different debug-module register" (dtm.json:70), is exactly the P:129 case "it selects which word is read".
- The root cause is the conflict in 4.3.

**1.6 trng [RTL]: the objective rule (P:160) is misapplied.**
- `sample_cnt` is given Availability.
- Half of its reason is an Integrity harm: "fire it early so half-filled low-entropy bytes enter the pool" (trng.json:42).
- This is minor, because the objective is not scored.

**1.7 sys [output]: CLOCK-RESET (P:137) is not applied to `clk_en_o`.**
- P:137 puts clock-enable ticks under CLOCK-RESET. Its only exception covers a generated reset or timeout.
- `clk_en_o` is listed as BOUNDARY (sys.json:55-58).

**1.8 Wrong tags with no effect on the asset list.**
- [output] `spi_clk_o`, `twi_scl_o`, `twi_scl_i` and `io_con.scl_*` are tagged CLOCK-RESET (spi.json:14, twi.json:13). P:137 covers clock and reset inputs, their internal copies and clock-enable ticks.
- [RTL] dtm `tap_reg.dtmcs` is tagged CARRIER (dtm.json:29). It is not a copy: it is a shift register fed from TDI (src 195) that drives the DMI reset requests (src 248-249).
- [output] wdt `bus_req_i.data` and `bus_rsp_o.data` are tagged CARRIER (wdt.json:15). P:115 calls such fields attack points.

## 2. Inconsistent decisions

**2.1 [RTL] dtm: one request register gets three decisions.**
- `dmi_ctrl.addr`, `dmi_ctrl.wdata` and `dmi_ctrl.op` are loaded together under one guard (src 265-269).
- They are tagged CORE, STORE and LEVER.
- Their ports split the same way (src 283-285): `dmi_req_o.addr` is CARRIER, `dmi_req_o.data` is BOUNDARY and `dmi_req_o.op` is LEVER.

**2.2 [mixed] Address registers are decided differently across modules.**
- dtm `dmi_ctrl.addr` is CORE [RTL].
- cache `ctrl.tag`, `ctrl.idx` and `ctrl.ofs` are CORE (cache.json:31-33) [output].
- imem `addr_ff` is CARRIER (imem.json:17) [output, unverified].
- The SRAM example (P:177) calls "the address register" an asset. If `addr_ff` is a register, imem contradicts both P:107 and P:177.

**2.3 [RTL] cpu: one record, same map facts, different tags.**
- `icc_tx_o.rdy` and `icc_tx_o.ack` are FORWARD, but `icc_tx_o.dat` is BOUNDARY.
- All three have handling `FORWARDS`, storage `not assigned`, and no records.
- Separating data from handshake is defensible. Even so, `.dat` fails the BOUNDARY map test (1.3).

**2.4 [mixed] Bus payload that carries only settings gets four different tags.**
- wdt tags it CARRIER (wdt.json:15).
- trng tags it FAILED-THREAT-TEST (trng.json:19). [RTL] confirms it feeds only `enable` and `fifo_clr` (src 105-106).
- hwspinlock tags it UNUSED (hwspinlock.json:17).
- pmp tags `ctrl_i.csr_wdata` CARRIER (cpu_pmp.json:15).
- The decision (not listed) is the same every time. Only the tag differs. The cause is 4.6.

**2.5 [mixed] Counters that end a multi-cycle job are tagged differently.**
- trng `sample_cnt` is DECISION. Its top bit is `valid_o` (src 367).
- muldiv `ctrl.cnt` is BOOKKEEPING (muldiv.json:17). The uart, spi and twi bit counters are BOOKKEEPING too.
- The trng choice follows the wording of P:111, which names the random-value-ready indication as a DECISION.
- But the element chosen is a counter, and P:140 puts helper counters in BOOKKEEPING.

**2.6 [output] Bus error outputs get different objectives.**
- The gateway's `rsp_o.err` gets Availability (bus.json:140).
- The cache's `host_rsp_o.err` gets Integrity (cache.json:35).
- The role is the same. The objective is not scored.

**2.7 [output, unverified] neorv32_bus: registers that buffer payload are treated two ways.**
- `amo_rmw` lists `arbiter.rdata`, `arbiter.wdata`, `alu_res` and four data ports as STORE or BOUNDARY (bus.json:147-174).
- Every port of `neorv32_bus_reg` is CARRIER (bus.json:22), although the executor itself calls that unit "an optional pipeline register stage" (bus.json:3).
- If the outputs of `bus_reg` are registers, P:96 treats both units alike.
- Not a fault: `core_req_i.data` is BOUNDARY in `amo_rmw` but FORWARD in `amo_rvs`. The roles differ, so that split is consistent.

## 3. Listed elements whose reason contradicts the definition, and omissions

**3.1 cpu [RTL]: all 16 assets (cpu.json:26-41) conflict with the prompt's own definitions.**
- The four `ctrl.*` CORE items, `frontend.instr` and `frontend.fault` should be FORWARD (P:141).
- `rs1`, `rs2` and `rs3` are wires from a sub-unit port, so they are CARRIER (P:139).
- `pmp_fault` and `lsu_err` are wires carrying a decision formed in a sub-unit (src 122-123, 391, 420), so they are also CARRIER. `pmp_fault` is even tied to '0' when the protection unit is not built (src 427).
- The five data ports fail the BOUNDARY map test (1.3).
- Reasoning, not measured: read literally, the prompt lists nothing for this module. The one possible exception is an input port under the last sentence of P:114, which requires that the module "uses it directly". A wrapper does not.

**3.2 dtm [RTL]:**
- `tap_reg.ireg` as CORE contradicts Step E (1.5).
- `dmi_ctrl.wdata` and `dmi_ctrl.rdata` contradict P:153 (1.4).

**3.3 cfu [output]: `xtea.sum` is tagged STORE with an Integrity reason (cfu.json:50-53).**
- STORE (P:96) covers keys, seeds, random values, payload, code and memory contents. A running round sum is none of these.
- P:178 calls values inside each round secondary.

**3.4 muldiv [output]: copies and intermediates are listed.**
- `mul.dsp_x` and `mul.dsp_y` are registered operand copies. Their reasons say "the first operand held" and "the second operand held" (muldiv.json:34-41). They are listed next to `rs1_i` and `rs2_i`.
- `div.rs2_abs` is a derived copy.
- `mul.prod`, `div.quotient` and `div.remainder` are intermediate values.
- The rules disagree here. P:153 forbids extra copies and P:178 calls intermediates secondary, but P:96 ("payload ... computes") includes them. The executor followed P:96.

**3.5 spi [output]: `rtx_engine.cs_ctrl` is tagged CORE.**
- The executor itself calls it "the stored chip-select setting that decides which external device receives the payload" (spi.json:10).
- P:138 lists chip enables and selects as LEVER.
- P:131 drops elements that only select.

**3.6 sys [output]:**
- `clk_en_o`: see 1.7.
- `cnt` is CORE as a "prescaler count" (sys.json:51-54). P:109 excludes rate ticks, but P:105 includes "the main count of a timer". Both readings are arguable.

**3.7 Elements left out that the definition includes:**
- imem `addr_ff`, if it is a register (2.2). Basis: P:107 and P:177. [output, unverified]
- trng: none [RTL]. P:111 asks for the register where the ready indication forms, which is `sample_cnt` (src 355-359, 367), and it is listed. No output of the outer entity delivers that indication; `fifo.we` (src 138) is internal.
- dtm: none [RTL].
- cpu: none under the literal prompt [RTL].

## 4. Wording that is ambiguous or conflicting

**4.1 P:180 conflicts with P:96, P:101, P:139 and P:141.**
- The processor-core example calls the program counter, the general-purpose registers, the control and status registers (CSRs) and the privilege mode assets.
- It does not say where to credit them when the file only wires sub-units.
- The STORE fallback (P:96) assumes some register in this file holds the value. P:21 calls a wire that moves a value secondary.
- This explains 1.1-1.3, 2.3 and 3.1.

**4.2 P:96, P:131, P:153 and P:178 conflict.**
- STORE includes payload the module "computes".
- The tie-break keeps "an element that holds a protected value across clock cycles". Every intermediate register in a datapath passes that test.
- The AES example calls intermediate values secondary, and Step G forbids copies.
- P:179 (bus units that carry data are secondary) also collides with P:96.
- This explains 1.4, 2.7, 3.3, 3.4 and the 8 entries for `amo_rmw`.

**4.3 P:103 and P:107 conflict with P:129, P:131 and P:138.**
- CORE includes "the instruction being executed" and "stored pointers or address registers".
- Step E and LEVER drop anything that "selects which word is read", and list "address and index inputs".
- A TAP instruction register or a request address register fits both sides.
- This explains 1.5, 2.1, 2.2 and 3.5.

**4.4 P:111 conflicts with P:140 and P:138.**
- DECISION asks for "its register", but BOOKKEEPING excludes helper counters. Both apply when the decision is the top bit of a counter (2.5).
- P:111 says "reset request", but P:138 lists "clear ... requests". The dtm `dmi_ctrl.dmireset` and `dmi_ctrl.dmihardreset` (src 248-252) fit both. The executor chose LEVER.

**4.5 P:137 has gaps.**
- It names "clock-enable ticks" but gives an exception only for reset and timeout generators. A clock-enable generator's product has no rule (1.7).
- "Clock and reset inputs" does not cover serial clock outputs (1.8).

**4.6 P:115 calls settings-only bus payload "attack points", but P:135-143 has no tag for them.** The executor improvised three different tags (2.4).

**4.7 P:210 ("names only") makes the accounting check in P:154 impossible in multi-entity files.**
- In trng, `clk_i` is declared in three entities but appears once (trng.json:13).
- In cache, `clk_i` and `rstn_i` each appear twice in one group (cache.json:15).

**4.8 P:160 allows both Availability and Integrity for a decision output.** Identical roles were split (2.6). This is low priority, because the objective is not scored.

## 5. Output faults

- **Undeclared names:** none in cpu, dtm or trng. Every asset was checked against the map's PORT and SIGNAL lines. The other 12 modules were not checked against RTL.
- **Wrong entity:** none in the three modules read. The trng elements `sample_sreg`, `debias_sreg` and `sample_cnt` are correctly assigned to `neoTRNG`.
- **Duplicates:**
  - No asset is duplicated by name and entity.
  - In the not-listed groups, cache.json:15 lists `clk_i` and `rstn_i` twice in one group. They come from two entities, but the names are unqualified.
- **Contract:**
  - All outputs have `module`, `analysis` and `assets` in order, and every objective is from the allowed set.
  - twi.json:17 and twi.json:20 are empty groups, which is harmless.
  - The cpu BOUNDARY entries break the prompt's own map test (1.3).
- **Reason that does not match its objective:**
  - trng `sample_cnt` (1.6).
  - bus `arbiter.rdata` and `arbiter.wdata`: the reasons say "observe", but the objective is Integrity (bus.json:147-154).

## 6. The three changes to make first

**6.1 Say where a value is credited when the file only wires sub-units.**
- **Ties to:** 1.1, 1.2, 1.3, 2.3, 3.1 and 4.1.
- **Default:** an element with map storage `not assigned` and handling `FORWARDS`, or with only `connections`, is FORWARD or CARRIER. It is never STORE, CORE, DECISION or BOUNDARY.
- P:180 should say its assets are credited in the sub-units that hold them.
- **The alternative is the designer's call:** if a wrapper should still list something, name its home outright instead of leaving the executor to stretch P:96.
- **Anchor:** the cpu map entries for `ctrl.pc_cur`, `rs1` and `ibus_rsp_i.data`; P:21 and P:141.
- **What it breaks:** the cpu list shrinks to almost nothing, and cpu is no longer comparable with r0. Other wrapper modules change too.
- **What would falsify it:** cpu recall falls and precision does not rise.
- **Measurement:**
  - precision and recall for `neorv32_cpu` alone;
  - precision of all listed elements with map storage `not assigned`.

**6.2 Credit each value in one place, and decide what happens to intermediates.**
- **Ties to:** 1.4, 2.7, 3.2, 3.3, 3.4 and 4.2.
- **Default:**
  - List the first register in this file that holds the value, plus its outer BOUNDARY ports.
  - Later registers holding the same value or a slice of it are CARRIER.
  - Intermediate results of a multi-cycle computation are CARRIER, matching P:178 and P:153.
  - Limit "computes" in P:96 to the final product.
- **Anchor:** dtm src 267, 274, 229 and 189; P:178.
- **What it breaks:** muldiv, cfu, dtm and bus `amo_rmw` shrink and stop being comparable with r0.
- **What would falsify it:** recall falls on those modules and precision does not rise.
- **Measurement:** precision and recall of STORE-tagged elements, per module, r0 against the next run.

**6.3 Settle selectors against CORE, in the same words in CORE and Step E.**
- **Ties to:** 1.5, 2.1, 2.2, 3.5 and 4.3.
- **Default:**
  - Keep a stored address register only when it points into a store in this same module. This covers the SRAM case in P:177 and the cache's `ctrl.tag`, `ctrl.idx` and `ctrl.ofs`.
  - An instruction or address register that only picks a register or device elsewhere is LEVER.
  - Write this rule into P:103, P:107 and P:129.
- **Anchor:** the dtm `tap_reg.ireg` records are only SELECTS and GATES, apart from its own shift-out (src 186, 193, 204, 206, 247, 258, 265); P:177.
- **What it breaks:**
  - dtm drops `tap_reg.ireg` and `dmi_ctrl.addr`.
  - spi drops `rtx_engine.cs_ctrl`.
  - imem may gain `addr_ff`.
- **What would falsify it:** recall falls on dtm and spi and precision does not rise.
- **Measurement:** precision and recall of CORE-tagged elements, per module.

**Lower priority:**
- an attack-point tag (4.6);
- entity names in not-listed groups (4.7);
- a rule for clock-enable generators (4.5);
- a rule for decisions that are one counter bit (4.4).

**Constraint check:**
- None of the three changes needs a processor identifier, a numeric quota or an HDL comment. Each can be worded with generic examples.
- Each rests on a source example the prompt already cites: P:21 (secondary assets), P:178 (AES) and P:177 (SRAM).
- Page numbers belong in the designer's rationale file, which I did not read.

DONE