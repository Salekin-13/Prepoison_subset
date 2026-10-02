Writing `E:/jobs/ff/test/Prepoison_subset/blind_agent/critic/D1/report.md` was refused, so the file does not exist. The report is below, ready to save at that path.

# Critic report: prompt D1, tuning run r0

## Scope

- **Read:** `TASK_BRIEF.md`, `MAP_FORMAT.md`, `prompts/D1/prompt.md`, and all 15 outputs in `runs/tuning/D1/r0/`.
- **Inputs read:** 3 of 15: **neorv32_bus**, **neorv32_cpu** and **neorv32_trng**. Each is a multi-entity or structural (wiring-only) file. In such files the port rule, the transport rule and the fallback rule collide.
- **Other 12 modules:** points about them come from their outputs only. They are marked **(output only)**, and their RTL facts are unverified.
- **No scores:** there is no reference and there are no scores. This report contains no precision or recall figure. All counts are hand counts from the files I read.
- **Line references:** "line N" is the RTL line number printed in the input file. "map line N" is the line number inside the input .txt.

**Short answer.** The executor mostly followed the prompt's words. Most faults come from three rules that pull in opposite directions:
- (a) "list each port through which the value enters or leaves";
- (b) the transport and secondary rules, where transport is decided by a map label (`FORWARDS`);
- (c) the fallback "the signal that carries the complete value".

Where these collide, the executor decided case by case. Elements with the same role were then decided differently across entities and modules.

---

## 1. Instructions ignored, misread or applied inconsistently

**1.1 Fallback bullet used selectively (cpu).** The prompt says: "only if the value has no such register or port in the file: the signal that carries the complete value."
- The executor used it for `pmp_fault` (lines 257, 392, 420) and `lsu_err` (lines 272, 391).
- Its own conceptual asset 5 covers register file, CSR contents, program counter, privilege and debug mode. It says these are held in sub-units and only moved here.
- Those values also have no register or port in this file, and signals carry them whole:
  - `rf_wdata` (line 330)
  - `rs1`, `rs2` (lines 324-325)
  - `csr_rdata` (line 263)
  - `lsu_rdata` (line 388)
  - `alu_res` (line 369)
- They were left out with a reason the prompt does not contain ("moved one word at a time").
- Under the prompt's text, the bullet applies to all of these or to none.

**1.2 Transport rule applied by data type, not by role (cpu).** The leave-out list says: "fields the module passes on unchanged without storing or using them (map handling `FORWARDS` only)".
- **Dropped:** every record field marked `FORWARDS`. That includes:
  - `ibus_rsp_i.err` and `dbus_rsp_i.err` (map lines 385, 404)
  - `dbus_req_o.priv` and `dbus_req_o.debug` (map lines 395-396)
  - `ibus_rsp_i.data`, `dbus_rsp_i.data` and `dbus_req_o.data`
- **Kept:** `firq_i` and `dbi_i`. They are also wired unchanged to a sub-unit (lines 268, 266). They carry no handling label only because they are scalar ports (map lines 352-355).
- The prompt says "Decide by role, not by name." By role, a bus error entering (`dbus_rsp_i.err`) and a debug request entering (`dbi_i`) are the same kind of element: events the CPU top passes on unchanged.

**1.3 "Keep only direct targets" not applied to in-ports.** The prompt says: "If the attack really targets another element, list that other element instead." Several reasons say the port matters only because of the register it feeds. The executor listed both the port and the register:
- **bus `a_req_i.lock`, `b_req_i.lock`:** "Port through which host A's lock request enters the locked register". `locked` is also listed.
- **bus `req_i.lock`:** "Port through which the lock value enters keeper.lock". `keeper.lock` is also listed.
- **trng `bus_req_i.data`:** "Input field through which the enable setting enters". `enable` is also listed.

The prompt does not say which rule wins (see 4.4).

**1.4 In-port/out-port pairing not applied.** The prompt asks for the same decision for "the in-port and out-port of the same data".
- **bus `neorv32_bus_switch`:** `a_req_i.lock` and `b_req_i.lock` are listed. `x_req_o.lock` carries the same value out (line 143) and is not listed.
- **trng `neoTRNG_cell`:** `en_i` is listed and `en_o` is not. `en_o` is the same enable after the cell's shift register (lines 416, 421). If `en_o` is excluded as a delayed copy, so is `en_i` of cells 1..n, because line 312 drives it from the previous cell's `en_o`.

**1.5 Executor trusted the RTL over a wrong map entry.** This was correct; it is noted only as a risk.
- The map shows `arbiter.state`, `arbiter.cmd`, `arbiter.rdata` and `arbiter.wdata` as kind "signal" with storage "none" (map lines 2047, 2059, 2066, 2072).
- Line 763 assigns the whole record on a clock edge, and the record `arbiter` itself is register/edge (map line 2043).
- The executor treated the fields as registers ("the RTL is the authority"). An executor that relies on `storage` would drop them (see 4.7).

---

## 2. Inconsistent decisions (same role, different outcome)

**2.1 Data ports of routing entities in one file (bus).**
- **Not listed:**
  - switch `a_req_i.data`, `b_req_i.data` (map: CONSUMES) and `x_req_o.data` (ORIGINATES), lines 150-152;
  - gateway `rsp_o.data` (ORIGINATES, line 399, map line 901).
- **Listed:** all four data ports of `neorv32_bus_amo_rmw`.
- None of the switch or gateway ports is `FORWARDS`, so the leave-out list does not exclude them.
- The executor seems to use an unwritten test: list a data port only when the entity also stores or computes the data. That test is reasonable but is not in the prompt.

**2.2 Privilege and debug qualifiers.**
- `neorv32_cpu_pmp` lists `ctrl_i.cpu_priv`, `ctrl_i.lsu_priv` and `ctrl_i.cpu_debug`.
- Bus switch `a_req_i.priv`, `b_req_i.priv`, `.debug` and `x_req_o.priv` (lines 144-145, CONSUMES) are not listed.
- The roles do differ: PMP decides on these values, the switch only selects them. But the prompt names "privilege" as a setting and gives no test for "held" versus "passing through".

**2.3 Fields of one record loaded under one condition (bus gateway).**
- `keeper.busy` (line 419) and `keeper.lock` (line 420) are both loaded at transfer start, under `keeper.busy = '0'` (line 417).
- `keeper.lock` is listed. `keeper.busy` is not, although it also gates the timeout counter (lines 417-422).

**2.4 Transfer-busy flags across modules.**
- **dtm lists `dmi_ctrl.busy`** (output only): "State of the DMI transfer; forcing it stuck high blocks every further debug request".
- **The bus gateway leaves out `keeper.busy`**, which has the same role:
  - it is set from the request (line 419);
  - it is held until acknowledge or timeout (lines 425-427);
  - stuck high, it blocks the monitor.

See 4.5.

**2.5 Two progress registers in one entity (trng `neoTRNG`).**
- `sample_cnt` (line 359) is listed.
- `debias_state` (line 336) is not. It is the phase bit that decides which sample pairs count (line 341).
- Both fit "state that says where the module is in its work".

**2.6 Serial clock lines (output only).**
- twi lists `twi_scl_i` and `twi_scl_o`. spi lists no SPI clock output.
- If the SPI has one (RTL not read), the same role was decided two ways.
- `twi_scl_i` is also a clock input, which the prompt says to leave out (see 4.6).

**2.7 Bit counters (output only).** uart lists `tx_engine.bitcnt` and `rx_engine.bitcnt`, and twi lists `engine.bitcnt`. spi lists none, and its conceptual assets do not mention bit position. Check whether the SPI engine has a bit counter.

**2.8 Bus write-data in-port (output only).** Six peripherals list both `bus_req_i.data` and `bus_rsp_o.data`: uart, spi, twi, wdt, imem and trng. hwspinlock lists only `bus_rsp_o.data`. Whether hwspinlock uses write data (for example, to release a lock) is unverified.

**2.9 Cache outbound data and tag ports (output only).**
- `host_req_i.data` and `bus_rsp_i.data` are listed going in, and `host_rsp_o.data` going out. No bus-side request data going out is listed.
- If host writes reach the bus, that out-port was skipped.
- `neorv32_cache_memory` lists `wdata_i` and `rdata_o` but no tag ports. Check whether tag ports exist.

---

## 3. Reasons that contradict the definition, and omissions the definition requires

### Listed elements whose reason contradicts the prompt

**3.1 bus `alu_res` (`neorv32_bus_amo_rmw`).**
- The leave-out list includes "partial or derived versions of a listed value".
- `alu_res` is computed from `arbiter.rdata` and `arbiter.wdata` (lines 839-844), and both are listed.
- Its reason ("computed atomic result") fits "data the module ... returns", so the prompt contradicts itself (see 4.3).
- The same pattern appears in muldiv `res_o` and cfu `xtea.res` (output only).

**3.2 trng `enable_i`, `en_i` and `data_o`.** The leave-out list includes "registers that only delay or duplicate a listed value".
- `enable_i` is the listed `enable`, wired in at line 137.
- `en_i` is that enable after the `sample_en` register (line 354) and the cell shift chain (lines 311-312, 416).
- `data_o` is an exact copy of the listed `sample_sreg` (line 366; map: COPIES).
- These are ports, so the rule's words miss them, but its intent covers them. Hand count: 3 of the 9 trng elements are such copies.

**3.3 bus `a_req_i.lock`, `b_req_i.lock` and `req_i.lock`.** The reasons call them a "lock request", and the leave-out list excludes "request and command strobes". They are request qualifiers held for a whole sequence (lines 90, 102, 426), not one-cycle strobes. Listing them is defensible, but the reason's wording points the other way.

**3.4 cpu `firq_i` and `dbi_i`.** The CPU top only forwards them (see 1.2). Read by role, the transport rule drops them; read by its words, they stay.

**3.5 trng `data_o` reason.** It says "each finished random byte leaves". In fact line 366 drives `data_o` from `sample_sreg` every cycle, including partial bytes. `valid_o` (line 367) marks completion. This is a small factual slip.

### Elements the prompt's own text calls for that were left out

- **3.6 bus `x_req_o.lock`** (line 143): the out-port of a value whose in-ports are listed (see 1.4).
- **3.7 bus switch `a_req_i.data`, `b_req_i.data`, `x_req_o.data`** (lines 150-152) **and gateway `rsp_o.data`** (line 399): they carry data the module receives and returns, and they are not `FORWARDS`.
- **3.8 bus `keeper.busy`** (lines 417-427): progress state of the monitored transfer, unless the strobe-holder sentence covers it.
- **3.9 cpu `rf_wdata`, `csr_rdata`, `lsu_rdata`, `rs1`, `rs2`:** the fallback bullet requires them (see 1.1), given the executor's own conceptual asset 5.
- **3.10 trng `debias_state`** (line 336): see 2.5.

---

## 4. Prompt wording that is ambiguous, conflicting or easy to misapply

**4.1 "Module" is undefined when a file holds several entities.**
- The prompt asks for "each port ... through which the value enters or leaves the module". It also asks for the same decision for "the same kind of element in each entity of the file". Together, these make every internal entity boundary a module boundary.
- In trng, one enable setting appears three times (`enable`, `enable_i`, `en_i`), plus its bus in-port. One random byte appears three times (`sample_sreg`, `data_o`, `bus_rsp_o.data`).
- The cache output shows the same pattern (output only).
- Explains 3.2 and part of 1.4.

**4.2 The duplicate rule covers registers only.** It says nothing about ports or plain signals that copy a listed value. Explains 3.2.

**4.3 "Partial or derived versions of a listed value" conflicts with "data the module ... returns".**
- Every result register is derived from listed operands.
- The executor ignored the clause for `alu_res`, `res_o` and `xtea.res`; another run may apply it.
- This is reasoning, not measured: it is a source of run-to-run variance. Explains 3.1.

**4.4 The port bullet conflicts with the direct-target test.** An in-port that feeds a register always "leads to" that register. The prompt does not say which rule wins. Explains 1.3 and 3.3.

**4.5 Strobe-holder versus progress state.** "A register that holds such a pulse for one transfer is still a strobe" and "state that says where the module is in its work" both fit a busy flag set by a request and cleared by an acknowledge or timeout. Explains 2.3, 2.4 and 3.8.

**4.6 "Clock and reset inputs" is unclear for serial-protocol clock lines.** Lines that are sampled as data, such as `twi_scl_i`, may or may not count. Explains 2.6.

**4.7 The transport rule trusts a map label that does not follow role.**
- The map sets `FORWARDS` when a whole record is copied, even if a field is later combined:
  - bus gateway `a_rsp_i.err` is `FORWARDS` (map line 920), but line 392 ORs it into the error;
  - in cpu, every field is `FORWARDS` because whole records are wired to sub-units.
- Scalar ports never get the label.
- Separately, the map shows storage "none" for record fields copied as a whole on a clock edge (see 1.5).
- Explains 1.2, 2.1 and 3.4.

**4.8 The lists of named bits attract decisions by name.** The settings list names "lock and enable bits"; the leave-out list names "write and byte enables". This pulls in bus-lock request bits and the trng `enable_i`/`en_i` ports, even though the prompt says "decide by role, not by name". Explains 3.3 and part of 3.2.

**4.9 "Do not repeat an element" does not define the key.** The bus output lists `state` twice (switch, amo_rvs) and `core_rsp_o.data` twice (amo_rmw, amo_rvs). That is legal if the key is name plus entity. The brief compares names "as declared", so the prompt should say which key applies.

**4.10 The fallback bullet has no test.** In a structural top file that only wires sub-units, almost every value has "no such register or port". The executor's choice of `pmp_fault` and `lsu_err` and nothing else is unconstrained. Explains 1.1 and 3.9.

---

## 5. Output faults

- **Names (3 inputs read):** every listed name appears on a PORT or SIGNAL line with the stated entity: bus 22/22, cpu 7/7, trng 9/9 (hand check).
- **Module names (3 inputs read):** each `module` matches the `MODULE:` line.
- **Extra keys (3 inputs read):** the only extra top-level key is `conceptual_assets`, placed before `assets`, which the prompt allows.
- **Objectives (all 15 outputs):** every `security_objective` is Confidentiality, Integrity or Availability.
- **Near-faults:**
  - bus has the same name under different entities (`state`, `core_rsp_o.data`). This is not a violation if the entity is part of the key (see 4.9).
  - The trng `data_o` reason has a factual slip (see 3.5).
- **Not checked:** the other 12 outputs, against their maps (inputs not read). In the three read, there are no undeclared names, wrong entities or exact duplicates.

---

## 6. The three prompt changes to make first (most important first)

These are described, not written as prompt text. Each can be phrased without processor identifiers and without numeric quotas. Each new decision rule still needs a page-cited source in `rationale.md` (TASK_BRIEF rule 4); I could not check the sources under the blindness rule.

**1. Use one role-based test for boundary elements.**
- **Replace:** both the `FORWARDS`-label rule and the bare "each port" bullet.
- **New test:**
  - List a port, record field or connection signal only if this entity stores, computes or decides on the value it carries.
  - A value that only passes through is transport, whether scalar or a record field, and whatever the map label says. "Passes through" means wired to a sub-unit, chosen by a selector, or copied across an internal entity boundary.
- **Also:** state once, in one place, whether the in-port that feeds a listed register is itself listed.
- **Fixes:** 1.2, 1.3, 1.4, 2.1, 3.2, 3.4, 4.1, 4.2, 4.4, 4.7.
- **What it breaks:**
  - It drops some currently listed ports: cpu `firq_i`/`dbi_i`, trng `enable_i`/`en_i`/`data_o`, possibly the bus `*.lock` in-ports.
  - The number of ports per module changes, so compare runs by element class.
  - If the reference lists boundary ports of routing units, port recall will fall.
- **What would falsify it:** after the next run, read precision and recall separately for ports and for internal registers. If port recall falls more than port precision rises, the test is too strict.

**2. Give the fallback bullet a concrete trigger, or delete it.**
- **Trigger, for example:** use it only when the file has no register at all that stores the value, and then apply it to every conceptual asset in that situation.
- **Fixes:** 1.1, 3.9, 4.10.
- **What it breaks:** the cpu output changes most. It may gain several connection signals or lose `pmp_fault` and `lsu_err`.
- **What would falsify it:** on structural top-level files like cpu, compare the listed set across repeated runs. If the sets still differ, the trigger is still too loose.

**3. Settle the strobe-holder versus progress-state boundary, and add a pairing self-check.**
- **Boundary:** say how to decide a flag that a request sets and an acknowledge or timeout clears.
- **Self-check:** in the final check, for each listed element, the executor names its in/out counterpart and the sibling fields loaded under the same condition, with the decision for each.
- **Fixes:** 1.4, 2.3, 2.4, 2.5, 3.6, 3.8, 4.5.
- **What it breaks:** it adds some elements (for example `x_req_o.lock`, `keeper.busy`) or removes their partners. Run lengths change.
- **What would falsify it:** count same-role pairs decided differently in the next run, by a critic or a script over the map relations. If that count does not fall, the check did not work.

DONE