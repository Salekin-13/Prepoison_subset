# neorv32_debug_dtm

**Purpose (model):** Bridge between JTAG TAP and the RISC-V Debug Module Interface (DMI): synchronize JTAG inputs, run the TAP state machine and IR/DR access logic (IDCODE, DTMCS, DMI, bypass), and implement a DMI controller that turns DR updates into outward dmi_req_o requests and consumes dmi_rsp_i responses.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | write DTMCS fields (including dmireset and dmihardreset) into the DTMCS register |  | 11 / 11 |
| start | start a DMI request: latch op/addr/wdata from the DMI DR into the controller and assert busy |  | 10 / 10 |
| operate | drive the external DMI request outputs (op, addr, data) and handle the DMI response (rdata/ack) |  | 7 / 7 |
| report | shift/read out selected register bits to JTAG TDO (IDCODE / DTMCS / DMI / bypass / IR) |  | 11 / 11 |
| read out | return DMI read data from dmi_rsp_i into the DMI DR (rdata -> dmi_ctrl.rdata -> tap_reg.dmi_nxt -> tap_reg.dmi captured for JTAG) |  | 5 / 5 |
| lock | the busy flag that blocks acceptance of new DMI requests while a request is outstanding |  | 5 / 5 |
| reset | clear TAP registers and DMI controller state on external reset (rstn_i) |  | 16 / 16 |

## Concept: DMI transaction (operation, address, write-data) as shifted in via the DMI DR and transmitted to the external DMI interface

- confidentiality: yes-assumed, line 283 `dmi_req_o.op   <= dmi_ctrl.op;` via dmi_req_o -- The DMI fields are copied to external dmi_req_o outputs (lines 283-285) and are also available on the serial JTAG TDO readout (line 209), so an off-chip observer can learn the transaction contents.
- integrity: yes-assumed, line 266 `dmi_ctrl.addr  <= tap_reg.dmi(40 downto 34);` via tap_reg.dmi -- dmi_ctrl.addr/wdata/op are written from tap_reg.dmi (line 266-269), and tap_reg.dmi itself is loaded from the JTAG-shifted DMI DR (lines 196,189), so an external JTAG writer can change the transaction fields.
- availability: yes-rtl, line 265 `if (dmi_ctrl.dmihardreset = '0') and (dr_trigger.valid = '1') and (tap_reg.ireg = addr_dmi_c) then` via dr_trigger.valid -- Acceptance of a new DMI transaction is gated by busy, dmihardreset and the DR-update event (the condition at line 265), so external-controlled update/reset conditions can block new requests.
- undermined behavior: no, line 266 `dmi_ctrl.addr  <= tap_reg.dmi(40 downto 34);` -- The dmi_ctrl.addr/wdata/op registers are driven only by the dmi_controller process from tap_reg.dmi (lines 266-269) and there is no alternate override or debug bypass assignment in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dmi_req_o.op | neorv32_debug_dtm | exit port | 2 -> 283 `dmi_req_o.op   <= dmi_ctrl.op;` | COPIES dmi_ctrl.op | verified |  | not listed |
| dmi_req_o.data | neorv32_debug_dtm | exit port | 2 -> 284 `dmi_req_o.data <= dmi_ctrl.wdata;` | COPIES dmi_ctrl.wdata | verified |  | not listed |
| dmi_req_o.addr | neorv32_debug_dtm | exit port | 2 -> 285 `dmi_req_o.addr <= dmi_ctrl.addr;` | COPIES dmi_ctrl.addr | verified |  | not listed |
| dmi_ctrl.op | neorv32_debug_dtm | stores | 3 -> 263 `dmi_ctrl.op <= dmi_req_nop_c;` | CLOCKED_BY clk_i | verified |  | not listed |
| dmi_ctrl.addr | neorv32_debug_dtm | stores | 4 -> 266 `dmi_ctrl.addr  <= tap_reg.dmi(40 downto 34);` | CLOCKED_BY clk_i | verified |  | not listed |
| dmi_ctrl.wdata | neorv32_debug_dtm | stores | 3 -> 267 `dmi_ctrl.wdata <= tap_reg.dmi(33 downto 02);` | CLOCKED_BY clk_i | verified |  | not listed |
| tap_reg.dmi | neorv32_debug_dtm | stores | 3 -> 189 `when addr_dmi_c    => tap_reg.dmi    <= tap_reg.dmi_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
| tap_reg.dmi_nxt | neorv32_debug_dtm | computes | 4 -> 229 `tap_reg.dmi_nxt <= dmi_ctrl.addr & dmi_ctrl.rdata & replicate_f(dmi_ctrl.err, 2);` | DERIVES_FROM dmi_ctrl.addr | verified |  | not listed |
| tap_sync.tdi | neorv32_debug_dtm | sets | 6 -> 196 `when addr_dmi_c    => tap_reg.dmi    <= tap_sync.tdi & tap_reg.dmi(tap_reg.dmi'left downto` | SOURCES tap_reg.dmi | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage none) | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dmi_ctrl.op <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dr_trigger.valid, tap_reg.dmi, tap_reg.ireg; dmi_ctrl.addr <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dr_trigger.valid, tap_reg.ireg; dmi_ctrl.wdata <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dr_trigger.valid, tap_reg.ireg; tap_reg.dmi <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising

## Concept: DTMCS configuration bits (including dmireset and dmihardreset) that control DMI resets and status

- confidentiality: yes-assumed, line 208 `when addr_dtmcs_c  => jtag_tdo_o <= tap_reg.dtmcs(0);` via jtag_tdo_o -- The DTMCS register bits are driven out on JTAG TDO (line 208) so an off-chip observer can read the configuration and controller-reset status.
- integrity: yes-assumed, line 248 `dmi_ctrl.dmireset     <= tap_reg.dtmcs(16);` via tap_reg.dtmcs -- dmireset and dmihardreset are written into the controller from the DTMCS DR on DR_UPDATE (lines 247-249), so the JTAG-written DTMCS fields can change these reset bits.
- availability: yes-rtl, line 265 `if (dmi_ctrl.dmihardreset = '0') and (dr_trigger.valid = '1') and (tap_reg.ireg = addr_dmi_c) then` via dmi_ctrl.dmihardreset -- The controller refuses to start new DMI operations when dmihardreset/dmireset block acceptance (the check at line 265), and dmihardreset is writable via DTMCS, so an external write can disable acceptance and block progress.
- undermined behavior: no, line 248 `dmi_ctrl.dmireset     <= tap_reg.dtmcs(16);` -- DTMCS bits and the controller reset bits are updated only by the DTMCS DR capture/update logic (lines 219-226 and 248-249) and normal controller reset handling; the RTL contains no alternate debug/test bypass that overrides them.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tap_reg.dtmcs | neorv32_debug_dtm | stores | 3 -> 188 `when addr_dtmcs_c  => tap_reg.dtmcs  <= tap_reg.dtmcs_nxt;` | CLOCKED_BY clk_i | verified |  | hit |
| tap_reg.dtmcs_nxt | neorv32_debug_dtm | computes | 4 -> 220 `tap_reg.dtmcs_nxt(17)           <= dmi_ctrl.dmihardreset;` | COPIES dmi_ctrl.dmihardreset | edge, role unfit | COPIES does not demonstrate 'computes' | not listed |
| dmi_ctrl.dmihardreset | neorv32_debug_dtm | stores | 4 -> 249 `dmi_ctrl.dmihardreset <= tap_reg.dtmcs(17);` | CLOCKED_BY clk_i | verified |  | not listed |
| dmi_ctrl.dmireset | neorv32_debug_dtm | stores | 4 -> 248 `dmi_ctrl.dmireset     <= tap_reg.dtmcs(16);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tap_reg.dtmcs <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising; dmi_ctrl.dmihardreset <- dmi_ctrl.busy, dr_trigger.valid, tap_reg.ireg; dmi_ctrl.dmireset <- dmi_ctrl.busy, dr_trigger.valid, tap_reg.ireg

## Concept: Instruction register value (IREG) that selects which IR/DR is active and thus which register is read/written

- confidentiality: no, line 204 `jtag_tdo_o <= tap_reg.ireg(0);` via jtag_tdo_o -- IREG is written by the JTAG IR shift/capture path and its bit(s) are driven back on TDO (line 204), so the writer already knows the value and it reveals nothing new to that writer.
- integrity: yes-assumed, line 181 `tap_reg.ireg <= tap_sync.tdi & tap_reg.ireg(tap_reg.ireg'left downto 1);` via tap_sync.tdi -- IREG is loaded from the JTAG TDI stream during IR_SHIFT (line 181) so an external JTAG sender can change which register is selected and thereby affect accesses.
- availability: yes-rtl, line 181 `tap_reg.ireg <= tap_sync.tdi & tap_reg.ireg(tap_reg.ireg'left downto 1);` via tap_ctrl_state -- IREG only updates when the TAP enters IR_SHIFT and on tap_sync.tck_rising (line 181), so external JTAG signals (TMS/TCK) can hold the TAP state and prevent IREG updates, blocking changes.
- undermined behavior: no, line 181 `tap_reg.ireg <= tap_sync.tdi & tap_reg.ireg(tap_reg.ireg'left downto 1);` -- IREG is driven only by the IR capture/shift logic at line 181 (and the reset/default at 179) with no alternate override or bypass present in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tap_reg.ireg | neorv32_debug_dtm | stores | 3 -> 179 `tap_reg.ireg <= addr_idcode_c;` | CLOCKED_BY clk_i | verified |  | not listed |
| tap_sync.tdi | neorv32_debug_dtm | sets | 3 -> 181 `tap_reg.ireg <= tap_sync.tdi & tap_reg.ireg(tap_reg.ireg'left downto 1);` | SOURCES tap_reg.ireg | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage none) | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tap_reg.ireg <- tap_ctrl_state, tap_sync.tck_rising

## Concept: JTAG TDO output (serial readout) that reports the selected register contents off-chip

- confidentiality: yes-assumed, line 204 `jtag_tdo_o <= tap_reg.ireg(0);` via jtag_tdo_o -- The RTL drives internal register bits out on the jtag_tdo_o port (lines 204 and 207-210), so off-chip observers can read internal state via TDO.
- integrity: yes-assumed, line 204 `jtag_tdo_o <= tap_reg.ireg(0);` via tap_reg.ireg / tap_reg.idcode / tap_reg.dtmcs / tap_reg.dmi / tap_reg.bypass -- TDO is driven directly from internal registers (lines 204,207-210) which are in turn written from JTAG or controller logic, so external inputs can influence what is output on TDO.
- availability: yes-rtl, line 202 `if (tap_sync.tck_falling = '1') then` via tap_sync.tck_falling -- TDO updates are produced only on tap_sync.tck_falling and under TAP-state conditions (line 202 and case lines 203-211), so external JTAG clock/state control can stall or force TDO behavior and prevent expected output.
- undermined behavior: no, line 204 `jtag_tdo_o <= tap_reg.ireg(0);` -- jtag_tdo_o has a single driver in the reg_access process (lines 202-211) with no separate debug/test bypass assignment shown in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| jtag_tdo_o | neorv32_debug_dtm | exit port | 3 -> 204 `jtag_tdo_o <= tap_reg.ireg(0);` | DERIVES_FROM tap_reg.ireg | verified |  | hit |
| tap_reg.idcode | neorv32_debug_dtm | stores | 3 -> 187 `when addr_idcode_c => tap_reg.idcode <= IDCODE_VERSION & IDCODE_PARTID & IDCODE_MANID & '1` | CLOCKED_BY clk_i | verified |  | not listed |
| tap_reg.dtmcs | neorv32_debug_dtm | stores | 3 -> 188 `when addr_dtmcs_c  => tap_reg.dtmcs  <= tap_reg.dtmcs_nxt;` | CLOCKED_BY clk_i | verified |  | hit |
| tap_reg.dmi | neorv32_debug_dtm | stores | 3 -> 189 `when addr_dmi_c    => tap_reg.dmi    <= tap_reg.dmi_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): jtag_tdo_o <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_falling; tap_reg.idcode <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising; tap_reg.dtmcs <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising; tap_reg.dmi <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising

## Concept: DR-update trigger (dr_trigger.valid) that enables use of captured DR contents (the update event)

- confidentiality: no, line 161 `dr_trigger.valid <= '1' when (dr_trigger.sreg = "01") else '0';` via dr_trigger.sreg -- dr_trigger.valid is derived internally from the two-bit sreg (line 161) and is an event produced by TAP transitions that the JTAG master itself generates, so it is not a secret beyond what the JTAG master already knows.
- integrity: yes-rtl, line 152 `dr_trigger.sreg(0) <= '1';` via tap_ctrl_state -- dr_trigger.sreg(0) is asserted on TAP DR_UPDATE (line 152) so external JTAG-driven TAP transitions can create or manipulate the update event that the DMI controller and other logic consume (lines 247-265) without additional internal locking.
- availability: yes-rtl, line 151 `if (tap_ctrl_state = DR_UPDATE) then` via tap_ctrl_state -- The update event only occurs when the TAP reaches DR_UPDATE (check at line 151/152), so external JTAG control of the TAP state can prevent or force the event and thereby block or enable DR updates.
- undermined behavior: no, line 161 `dr_trigger.valid <= '1' when (dr_trigger.sreg = "01") else '0';` -- dr_trigger.valid is computed only from the two-bit shift register (line 161) and there is no alternate override or bypass for the DR-update event present in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dr_trigger.sreg | neorv32_debug_dtm | stores | 3 -> 152 `dr_trigger.sreg(0) <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| dr_trigger.valid | neorv32_debug_dtm | computes | 2 -> 161 `dr_trigger.valid <= '1' when (dr_trigger.sreg = "01") else '0';` | GATED_BY dr_trigger.sreg | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dr_trigger.sreg <- tap_ctrl_state; dr_trigger.valid <- dr_trigger.sreg

## Concept: DMI controller busy flag that blocks new request acceptance until the outstanding DMI completes

- confidentiality: yes-assumed, line 283 `dmi_req_o.op   <= dmi_ctrl.op;` via dmi_req_o -- busy controls whether new requests are exported on dmi_req_o (gating at line 264 leading to outputs at lines 283-285), so off-chip observers can infer controller activity and busy state.
- integrity: yes-assumed, line 276 `dmi_ctrl.busy <= '0';` via dmi_rsp_i.ack -- dmi_ctrl.busy is cleared when dmi_rsp_i.ack='1' (lines 275-276), so an external responder that drives ack can change the busy state observed by the controller.
- availability: yes-rtl, line 264 `if (dmi_ctrl.busy = '0') then` via dmi_ctrl.busy -- New request setup is explicitly gated on dmi_ctrl.busy = '0' (line 264), so if busy remains asserted external conditions can prevent new requests and stall progress.
- undermined behavior: no, line 270 `dmi_ctrl.busy <= '1';` -- busy is driven only by the dmi_controller process (set at line 270 and cleared at line 276, reset at 237) with no alternate override or bypass present in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dmi_ctrl.busy | neorv32_debug_dtm | stores | 6 -> 270 `dmi_ctrl.busy <= '1';` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dmi_ctrl.busy <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dmi_rsp_i.ack, dr_trigger.valid, tap_reg.dmi, tap_reg.ireg

## Concept: DMI controller error indicator (dmi_ctrl.err) and its inclusion in readback

- confidentiality: yes-assumed, line 229 `tap_reg.dmi_nxt <= dmi_ctrl.addr & dmi_ctrl.rdata & replicate_f(dmi_ctrl.err, 2);` via tap_reg.dmi_nxt -- err is included in the DMI readback vector (tap_reg.dmi_nxt at line 229) and that DR is output via JTAG TDO (line 209), so an off-chip observer can learn the controller error status.
- integrity: yes-assumed, line 259 `dmi_ctrl.err <= '1';` via dr_trigger.valid -- dmi_ctrl.err is set by the controller when a DR_UPDATE occurs while busy and the DMI IR is selected (line 259) and can be cleared by DTMCS resets (lines 256-257), so external JTAG/DMI events can change the error bit.
- availability: no, line 229 `tap_reg.dmi_nxt <= dmi_ctrl.addr & dmi_ctrl.rdata & replicate_f(dmi_ctrl.err, 2);` via tap_reg.dmi_nxt -- err is a status bit included in readback (line 229) and the RTL does not use err to gate forward progress of request handling, so its value alone does not prevent the module from making progress.
- undermined behavior: yes-rtl, line 256 `if (dmi_ctrl.dmireset = '1') or (dmi_ctrl.dmihardreset = '1') then` via dmi_ctrl.dmireset / dmi_ctrl.dmihardreset -- dmi_ctrl.err can be cleared by asserting DMI reset or hard-reset (the assignment at line 256-257), and those reset bits are writable via DTMCS, providing an alternate mode to change err.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dmi_ctrl.err | neorv32_debug_dtm | stores | 4 -> 257 `dmi_ctrl.err <= '0';` | CLOCKED_BY clk_i | verified |  | not listed |
| tap_reg.dmi_nxt | neorv32_debug_dtm | computes | 4 -> 229 `tap_reg.dmi_nxt <= dmi_ctrl.addr & dmi_ctrl.rdata & replicate_f(dmi_ctrl.err, 2);` | DERIVES_FROM dmi_ctrl.addr | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dmi_ctrl.err <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dmi_ctrl.dmireset, dr_trigger.valid, tap_reg.ireg
