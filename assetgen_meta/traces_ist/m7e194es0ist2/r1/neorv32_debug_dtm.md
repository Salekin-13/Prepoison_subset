# neorv32_debug_dtm

**Purpose (model):** Implements a JTAG TAP + Debug Transport Module: it synchronizes JTAG inputs, runs the TAP state machine and IR/DR access (IDCODE, DTMCS, DMI), controls a DMI controller that latches requests and drives dmi_req_o, and consumes DMI responses on dmi_rsp_i.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | Start a DMI transaction: capture op/addr/wdata from the JTAG DMI register into dmi_ctrl and set busy to begin the transaction |  | 8 / 8 |
| operate | Issue the DMI request to the external DMI consumer by driving dmi_req_o.op / dmi_req_o.data / dmi_req_o.addr from the dmi_ctrl registers |  | 3 / 3 |
| operate | Handle DMI response: capture dmi_rsp_i.data into dmi_ctrl.rdata and clear busy when ack is observed |  | 4 / 4 |
| configure | Write/read TAP DR registers (IDCODE, DTMCS, DMI): DR_CAPTURE loads readback values into tap_reg.*, DR_SHIFT shifts TDI into the selected DR field(s) |  | 11 / 11 |
| report | Shift out selected register bits to JTAG TDO (idcode, dtmcs, dmi, or bypass) on tck_falling, selected by tap_reg.ireg and the TAP state |  | 10 / 10 |
| reset | DTMCS-derived resets (dmireset, dmihardreset) are transferred into the DMI controller and clear error state when asserted |  | 8 / 8 |
| lock | dmi_ctrl.busy acts as a lock that prevents new DMI requests from being started while a transaction is in flight |  | 4 / 4 |

## Concept: DMI request message (op, addr, wdata) sent to the external DMI consumer

- confidentiality: yes-assumed, line 283 `dmi_req_o.op   <= dmi_ctrl.op;` via dmi_req_o -- The computed request fields are driven onto the external port dmi_req_o (op/data/addr) at lines 283-285 so an external DMI consumer can learn the values.
- integrity: yes-assumed, line 266 `dmi_ctrl.addr  <= tap_reg.dmi(40 downto 34);` via tap_reg.dmi (via dmi_controller) -- The controller latches addr/wdata/op from tap_reg.dmi into dmi_ctrl when dmi_ctrl.busy='0' and a DR_UPDATE occurs (lines 266-271), so an external JTAG writer that controls tap_reg.dmi can change the request contents.
- availability: yes-rtl, line 264 `if (dmi_ctrl.busy = '0') then` via dmi_ctrl.busy (cleared by dmi_rsp_i.ack) -- New requests are only formed when dmi_ctrl.busy = '0' (guard at line 264) and busy is cleared by the external dmi_rsp_i.ack signal (line 276), so an external participant can withhold ack or keep busy asserted and block new requests.
- undermined behavior: no, line 283 `dmi_req_o.op   <= dmi_ctrl.op;` via dmi_req_o -- The outgoing request fields are driven only from the dmi_ctrl registers (copied to dmi_req_o at lines 283-285) and there is no separate debug/test override or alternate privileged driver in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dmi_req_o.op | neorv32_debug_dtm | exit port | 2 -> 283 `dmi_req_o.op   <= dmi_ctrl.op;` | COPIES dmi_ctrl.op | verified |  | not listed |
| dmi_req_o.data | neorv32_debug_dtm | exit port | 2 -> 284 `dmi_req_o.data <= dmi_ctrl.wdata;` | COPIES dmi_ctrl.wdata | verified |  | not listed |
| dmi_req_o.addr | neorv32_debug_dtm | exit port | 2 -> 285 `dmi_req_o.addr <= dmi_ctrl.addr;` | COPIES dmi_ctrl.addr | verified |  | not listed |
| dmi_ctrl.op | neorv32_debug_dtm | stores | 3 -> 263 `dmi_ctrl.op <= dmi_req_nop_c;` | CLOCKED_BY clk_i | verified |  | not listed |
| dmi_ctrl.wdata | neorv32_debug_dtm | stores | 3 -> 267 `dmi_ctrl.wdata <= tap_reg.dmi(33 downto 02);` | CLOCKED_BY clk_i | verified |  | not listed |
| dmi_ctrl.addr | neorv32_debug_dtm | stores | 4 -> 266 `dmi_ctrl.addr  <= tap_reg.dmi(40 downto 34);` | CLOCKED_BY clk_i | verified |  | not listed |
| tap_reg.dmi | neorv32_debug_dtm | sets | 3 -> 189 `when addr_dmi_c    => tap_reg.dmi    <= tap_reg.dmi_nxt;` | COPIES tap_reg.dmi_nxt | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dmi_ctrl.op <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dr_trigger.valid, tap_reg.dmi, tap_reg.ireg; dmi_ctrl.wdata <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dr_trigger.valid, tap_reg.ireg; dmi_ctrl.addr <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dr_trigger.valid, tap_reg.ireg; tap_reg.dmi <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising

## Concept: DMI controller busy flag that serializes transactions (exclusive lock)

- confidentiality: yes-assumed, line 283 `dmi_req_o.op   <= dmi_ctrl.op;` via dmi_req_o -- External observers can infer the busy state from whether requests are issued on dmi_req_o (lines 283-285) and from response handshake behavior, so the busy state can be learned outside the module.
- integrity: yes-assumed, line 270 `dmi_ctrl.busy <= '1';` via dmi_controller / dmi_rsp_i.ack -- busy is set/cleared by the dmi_controller (set at line 270) and cleared by the external ack input (line 276), so external inputs can change the busy state and its integrity depends on integration.
- availability: yes-rtl, line 276 `dmi_ctrl.busy <= '0';` via dmi_rsp_i.ack -- busy is cleared only when dmi_rsp_i.ack = '1' (line 276), so an external DMI responder can withhold ack and keep busy asserted, preventing new transactions and blocking progress.
- undermined behavior: no, line 270 `dmi_ctrl.busy <= '1';` via dmi_controller -- busy is driven only by the dmi_controller (reset plus the request/ack handlers at lines 237/270/276) and there is no alternate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dmi_ctrl.busy | neorv32_debug_dtm | stores | 6 -> 270 `dmi_ctrl.busy <= '1';` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dmi_ctrl.busy <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dmi_rsp_i.ack, dr_trigger.valid, tap_reg.dmi, tap_reg.ireg

## Concept: DMI reset controls that force DMI reset state and clear errors (dmireset, dmihardreset sourced from DTMCS)

- confidentiality: yes-assumed, line 208 `when addr_dtmcs_c  => jtag_tdo_o <= tap_reg.dtmcs(0);` via jtag_tdo_o / tap_reg.dtmcs -- dmireset and dmihardreset are reflected into tap_reg.dtmcs_nxt (lines 220-221), captured and presented on TDO (line 208), so an external JTAG reader can learn their values.
- integrity: yes-rtl, line 248 `dmi_ctrl.dmireset     <= tap_reg.dtmcs(16);` via tap_reg.dtmcs -- The controller writes dmireset/dmihardreset directly from tap_reg.dtmcs on DR_UPDATE (lines 247-249), so an external JTAG update can change these control bits while they affect internal behavior.
- availability: yes-rtl, line 265 `if (dmi_ctrl.dmihardreset = '0') and (dr_trigger.valid = '1') and (tap_reg.ireg = addr_dmi_c) then` via dmi_ctrl.dmihardreset / dmi_ctrl.dmireset -- dmihardreset/dmireset are tested when accepting new DMI requests (line 265 requires dmihardreset='0'), so setting these bits via DTMCS can prevent transaction starts and block progress.
- undermined behavior: yes-rtl, line 251 `dmi_ctrl.dmihardreset <= '0';` via dmi_ctrl.busy -- There are multiple assignment paths (set from tap_reg.dtmcs on DR_UPDATE at lines 247-249 and cleared when dmi_ctrl.busy = '0' at lines 250-252), so the effective reset bits can be replaced by the busy-controlled clearing path.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dmi_ctrl.dmihardreset | neorv32_debug_dtm | stores | 4 -> 249 `dmi_ctrl.dmihardreset <= tap_reg.dtmcs(17);` | CLOCKED_BY clk_i | verified |  | not listed |
| dmi_ctrl.dmireset | neorv32_debug_dtm | stores | 4 -> 248 `dmi_ctrl.dmireset     <= tap_reg.dtmcs(16);` | CLOCKED_BY clk_i | verified |  | not listed |
| tap_reg.dtmcs | neorv32_debug_dtm | stores | 3 -> 188 `when addr_dtmcs_c  => tap_reg.dtmcs  <= tap_reg.dtmcs_nxt;` | CLOCKED_BY clk_i | verified |  | hit |
| tap_reg.dtmcs_nxt | neorv32_debug_dtm | computes | 4 -> 220 `tap_reg.dtmcs_nxt(17)           <= dmi_ctrl.dmihardreset;` | COPIES dmi_ctrl.dmihardreset | edge, role unfit | COPIES does not demonstrate 'computes' | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dmi_ctrl.dmihardreset <- dmi_ctrl.busy, dr_trigger.valid, tap_reg.ireg; dmi_ctrl.dmireset <- dmi_ctrl.busy, dr_trigger.valid, tap_reg.ireg; tap_reg.dtmcs <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising

## Concept: DMI register contents (tap_reg.dmi) provided by JTAG and consumed to form DMI transactions

- confidentiality: yes-assumed, line 209 `when addr_dmi_c    => jtag_tdo_o <= tap_reg.dmi(0);` via jtag_tdo_o -- tap_reg.dmi is presented on TDO (line 209) during DR_SHIFT/DR_CAPTURE, so an external JTAG observer can read its contents.
- integrity: yes-assumed, line 196 `when addr_dmi_c    => tap_reg.dmi    <= tap_sync.tdi & tap_reg.dmi(tap_reg.dmi'left downto 1);` via jtag_tdi / tap_reg.dmi (DR_SHIFT/DR_CAPTURE) -- tap_reg.dmi can be written directly by external JTAG via DR_SHIFT (line 196) or loaded from internal controller state via DR_CAPTURE (line 189), so an external party controlling JTAG can change its contents.
- availability: yes-rtl, line 192 `elsif (tap_ctrl_state = DR_SHIFT) and (tap_sync.tck_rising = '1') then` via tap_ctrl_state and tap_sync.tck_rising (driven by jtag_tck_i/jtag_tms_i) -- Updates to tap_reg.dmi occur only during TAP DR_CAPTURE/DR_SHIFT states gated by tap_ctrl_state and synchronized TCK (see lines 185/192/196), so external JTAG inputs can block or freeze its updates.
- undermined behavior: yes-rtl, line 185 `if (tap_ctrl_state = DR_CAPTURE) then` via tap_ctrl_state -- tap_reg.dmi can be assigned either from internal dmi_ctrl via DR_CAPTURE (line 189) or from external TDI via DR_SHIFT (line 196); the TAP state (line 185) selects the source, creating alternate write paths.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tap_reg.dmi | neorv32_debug_dtm | stores | 3 -> 189 `when addr_dmi_c    => tap_reg.dmi    <= tap_reg.dmi_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
| tap_reg.dmi_nxt | neorv32_debug_dtm | computes | 4 -> 229 `tap_reg.dmi_nxt <= dmi_ctrl.addr & dmi_ctrl.rdata & replicate_f(dmi_ctrl.err, 2);` | DERIVES_FROM dmi_ctrl.addr | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tap_reg.dmi <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising

## Concept: DR-update trigger (dr_trigger.valid) that enables register updates and DMI starts

- confidentiality: no, line 161 `dr_trigger.valid <= '1' when (dr_trigger.sreg = "01") else '0';` -- dr_trigger.valid is an internal one-cycle event derived from dr_trigger.sreg (line 161) and is not presented directly on any external output.
- integrity: yes-assumed, line 152 `dr_trigger.sreg(0) <= '1';` via tap_ctrl_state -- dr_trigger.sreg(0) is set when tap_ctrl_state = DR_UPDATE (line 152), so external JTAG control of the TAP FSM determines when the DR_UPDATE trigger occurs and can change the event.
- availability: yes-rtl, line 151 `if (tap_ctrl_state = DR_UPDATE) then` via tap_ctrl_state / jtag_tck_i and jtag_tms_i -- dr_trigger.sreg is driven only when the TAP enters DR_UPDATE (the update_trigger logic tests tap_ctrl_state at line 151), so external JTAG inputs can prevent the DR_UPDATE event and thereby block register updates and DMI starts.
- undermined behavior: no, line 161 `dr_trigger.valid <= '1' when (dr_trigger.sreg = "01") else '0';` -- dr_trigger.valid is computed from dr_trigger.sreg (line 161) which is only driven by the update_trigger logic (lines 152-156); there is no alternate override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dr_trigger.valid | neorv32_debug_dtm | computes | 2 -> 161 `dr_trigger.valid <= '1' when (dr_trigger.sreg = "01") else '0';` | GATED_BY dr_trigger.sreg | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dr_trigger.valid <- dr_trigger.sreg

## Concept: TAP controller state (tap_ctrl_state) that selects IR/DR behaviour and gates register operations

- confidentiality: no, line 119 `tap_ctrl_state <= LOGIC_RESET;` -- tap_ctrl_state is an internal TAP FSM state (reset at line 119) and is not directly exported as data to external observers.
- integrity: yes-assumed, line 121 `if (tap_sync.tck_rising = '1') then` via tap_sync.tck_rising and tap_sync.tms (derived from jtag_tck_i and jtag_tms_i) -- tap_ctrl_state transitions only when tap_sync.tck_rising = '1' and depend on tap_sync.tms (line 121), so external JTAG inputs control and can change the TAP state machine.
- availability: yes-rtl, line 121 `if (tap_sync.tck_rising = '1') then` via tap_sync.tck_rising / tap_sync.tms (jtag_tck_i/jtag_tms_i) -- The TAP FSM advances only on synchronized TCK rising edges and by TMS decisions (check at line 121), so external JTAG inputs can hold or force TAP states and prevent register operations from progressing.
- undermined behavior: no, line 119 `tap_ctrl_state <= LOGIC_RESET;` -- tap_ctrl_state is driven exclusively by the tap_control process (reset and TCK/TMS-driven case transitions at lines 119 and 121-140) with no separate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tap_ctrl_state | neorv32_debug_dtm | stores | 4 -> 123 `when LOGIC_RESET => if (tap_sync.tms = '0') then tap_ctrl_state <= RUN_IDLE;   else tap_ct` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tap_ctrl_state <- tap_ctrl_state, tap_sync.tck_rising, tap_sync.tms

## Concept: IR register (tap_reg.ireg) selecting which DR is accessed and which data is shifted out

- confidentiality: yes-assumed, line 204 `jtag_tdo_o <= tap_reg.ireg(0);` via jtag_tdo_o -- tap_reg.ireg is shifted out on TDO (line 204) during IR_SHIFT, so external JTAG can read the IR contents.
- integrity: yes-assumed, line 181 `tap_reg.ireg <= tap_sync.tdi & tap_reg.ireg(tap_reg.ireg'left downto 1);` via jtag_tdi / tap_ctrl_state -- tap_reg.ireg can be shifted in from TDI during IR_SHIFT (line 181) under TAP control, so an external JTAG writer can change the IR and thereby affect which DR is accessed.
- availability: yes-rtl, line 181 `tap_reg.ireg <= tap_sync.tdi & tap_reg.ireg(tap_reg.ireg'left downto 1);` via tap_sync.tck_rising and tap_ctrl_state -- writes to ireg occur only in IR_CAPTURE/IR_SHIFT gated by the TAP state and synchronized TCK (lines 179-181), so external JTAG inputs can prevent or force IR updates and freeze IR selection.
- undermined behavior: yes-rtl, line 179 `tap_reg.ireg <= addr_idcode_c;` via tap_ctrl_state -- ireg can be loaded from a constant during LOGIC_RESET/IR_CAPTURE (line 179) or be shifted in via IR_SHIFT (line 181); the TAP state (tap_ctrl_state) selects which source drives ireg, so the source can be switched by TAP mode.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tap_reg.ireg | neorv32_debug_dtm | stores | 3 -> 179 `tap_reg.ireg <= addr_idcode_c;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tap_reg.ireg <- tap_ctrl_state, tap_sync.tck_rising

## Concept: JTAG TDO output stream (jtag_tdo_o) that reports register bits externally

- confidentiality: yes-assumed, line 204 `jtag_tdo_o <= tap_reg.ireg(0);` via jtag_tdo_o -- jtag_tdo_o is driven at TCK falling edges from internal registers (lines 204 and 207-211) and is exposed on the external TDO pin, so internal register bits are observable outside the module.
- integrity: yes-assumed, line 204 `jtag_tdo_o <= tap_reg.ireg(0);` via tap_reg.ireg / tap_reg.dmi / tap_reg.dtmcs -- TDO content is selected from internal registers which external JTAG operations (IR/DR sequences and TDI) can modify (see assignments at lines 204 and 206-211), so external actors can influence the stream.
- availability: yes-rtl, line 202 `if (tap_sync.tck_falling = '1') then` via tap_sync.tck_falling (derived from jtag_tck_i) -- TDO is updated only when tap_sync.tck_falling = '1' (line 202), which depends on the external JTAG TCK, so the JTAG host controls when the stream advances and can freeze it.
- undermined behavior: no, line 204 `jtag_tdo_o <= tap_reg.ireg(0);` -- jtag_tdo_o is driven only by the TAP-selected register outputs (lines 204 and 206-211) and there is no separate override or privileged bypass in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| jtag_tdo_o | neorv32_debug_dtm | exit port | 3 -> 204 `jtag_tdo_o <= tap_reg.ireg(0);` | DERIVES_FROM tap_reg.ireg | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): jtag_tdo_o <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_falling

## Concept: IDCODE register value used for device identification readback

- confidentiality: yes-assumed, line 207 `when addr_idcode_c => jtag_tdo_o <= tap_reg.idcode(0);` via jtag_tdo_o -- IDCODE is captured from generics into tap_reg.idcode (line 187) and presented on TDO (line 207), so it is externally readable.
- integrity: yes-assumed, line 194 `when addr_idcode_c => tap_reg.idcode <= tap_sync.tdi & tap_reg.idcode(tap_reg.idcode'left downto 1);` via jtag_tdi / DR_SHIFT -- tap_reg.idcode can be shifted by external TDI during DR_SHIFT (line 194), so an external writer can modify the shifted contents even though DR_CAPTURE reloads the constant IDCODE (line 187).
- availability: yes-rtl, line 187 `when addr_idcode_c => tap_reg.idcode <= IDCODE_VERSION & IDCODE_PARTID & IDCODE_MANID & '1';` via tap_ctrl_state / tap_sync.tck_rising -- IDCODE is presented via DR_CAPTURE/DR_SHIFT gated by TAP state and synchronized TCK (lines 185-194), so external JTAG can prevent capture or shifting and thereby block readback.
- undermined behavior: yes-rtl, line 187 `when addr_idcode_c => tap_reg.idcode <= IDCODE_VERSION & IDCODE_PARTID & IDCODE_MANID & '1';` via tap_ctrl_state -- IDCODE can be loaded from the constant generics on DR_CAPTURE (line 187) or be modified via DR_SHIFT (line 194); the TAP state selects which source drives the register.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tap_reg.idcode | neorv32_debug_dtm | stores | 3 -> 187 `when addr_idcode_c => tap_reg.idcode <= IDCODE_VERSION & IDCODE_PARTID & IDCODE_MANID & '1` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tap_reg.idcode <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising

## Concept: DMI response data as received from the external DMI (dmi_rsp_i.data) and stored for JTAG readback (dmi_ctrl.rdata)

- confidentiality: yes-assumed, line 229 `tap_reg.dmi_nxt <= dmi_ctrl.addr & dmi_ctrl.rdata & replicate_f(dmi_ctrl.err, 2);` via tap_reg.dmi_nxt / jtag_tdo_o -- dmi_ctrl.rdata is placed into tap_reg.dmi_nxt (line 229) and then captured and shifted out via JTAG (lines 189 and 209), so the response data is observable externally.
- integrity: yes-assumed, line 274 `dmi_ctrl.rdata <= dmi_rsp_i.data;` via dmi_rsp_i.data -- dmi_ctrl.rdata is directly loaded from the external dmi_rsp_i.data input (line 274), so an external DMI responder controls its value.
- availability: yes-rtl, line 274 `dmi_ctrl.rdata <= dmi_rsp_i.data;` via dmi_ctrl.busy and dmi_rsp_i.ack -- dmi_ctrl.rdata is updated in the response-handling path only when busy is set and depends on external response/ack behavior (line 274 and ack handling at 275-276), so an external responder can withhold data or ack and prevent updates.
- undermined behavior: no, line 274 `dmi_ctrl.rdata <= dmi_rsp_i.data;` -- dmi_ctrl.rdata is driven only from the external dmi_rsp_i.data in the response branch (line 274) and there is no alternate override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dmi_rsp_i.data | neorv32_debug_dtm | sets | 2 -> 274 `dmi_ctrl.rdata <= dmi_rsp_i.data;` | CARRIES dmi_ctrl.rdata | verified |  | not listed |
| dmi_ctrl.rdata | neorv32_debug_dtm | stores | 4 -> 274 `dmi_ctrl.rdata <= dmi_rsp_i.data;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dmi_ctrl.rdata <- dmi_ctrl.busy
