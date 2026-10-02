# neorv32_debug_dtm

**Purpose (model):** Synchronises JTAG pins and implements a JTAG TAP + Debug Transport Module (DTM): it runs the TAP state machine, holds IR and DR registers (IDCODE, DTMCS, DMI, bypass), translates DR UPDATE events into DMI requests (dmi_req_o) consumed by an external DMI responder (dmi_rsp_i), and serialises register readback on jtag_tdo_o.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| operate | synchronise asynchronous JTAG inputs into internal tap_sync signals and detect TCK edges |  | 13 / 13 |
| operate | advance TAP control-state machine from TMS/TCK events |  | 25 / 25 |
| start | DR-UPDATE sequence produces dr_trigger.sreg and dr_trigger.valid which authorises subsequent DMI request issuance |  | 20 / 20 |
| configure | write DTMCS fields (assembled in dtmcs_nxt) into the DTMCS register and have them update DMI-reset control bits |  | 19 / 19 |
| operate | assemble and issue a DMI request from tap_reg.dmi into dmi_ctrl (addr, wdata, op) and drive dmi_req_o; receive dmi_rsp_i and record rdata / clear busy on ack |  | 18 / 18 |
| read out | serial readback on TDO of the selected DR (IDCODE, DTMCS, DMI or bypass) and IR content during IR_SHIFT |  | 24 / 24 |
| reset | module reset clears synchronisers, TAP state, DR/IR registers and DMI controller state under rstn_i |  | 20 / 20 |

## Concept: Instruction register value that selects which Data Register (IDCODE, DTMCS, DMI, bypass) is accessed

- confidentiality: no, line 204 `jtag_tdo_o <= tap_reg.ireg(0);` via jtag_tdo_o -- The IR is shifted out on TDO during IR_SHIFT (jtag_tdo_o <= tap_reg.ireg(0) at line 204), so the JTAG host that wrote it can read it back and it does not reveal new secrets to other parties.
- integrity: yes-assumed, line 181 `tap_reg.ireg <= tap_sync.tdi & tap_reg.ireg(tap_reg.ireg'left downto 1);` via jtag_tdi_i -- The IR is written bit-serial from TDI when the TAP is in IR_SHIFT (assignment at line 181), so an external JTAG writer can change which DR is selected; whether that writer is trusted depends on integration.
- availability: yes-rtl, line 181 `tap_reg.ireg <= tap_sync.tdi & tap_reg.ireg(tap_reg.ireg'left downto 1);` via tap_ctrl_state -- IR only updates when the TAP is in IR_SHIFT on a TCK rising edge (guard at line 181), so external TAP control (tap_ctrl_state driven via jtag_tms/jtag_tck) can prevent or force IR changes and thereby freeze selection.
- undermined behavior: no, line 181 `tap_reg.ireg <= tap_sync.tdi & tap_reg.ireg(tap_reg.ireg'left downto 1);` -- The IR is driven only by reset/IR_CAPTURE forcing and by the serial IR_SHIFT write (drivers at lines 169, 179 and 181) and there is no separate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tap_reg.ireg | neorv32_debug_dtm | stores | 3 -> 179 `tap_reg.ireg <= addr_idcode_c;` | CLOCKED_BY clk_i | verified |  | not listed |
| jtag_tdi_i | neorv32_debug_dtm | sets | 2 -> 100 `tap_sync.tdi_ff <= tap_sync.tdi_ff(1 downto 0) & jtag_tdi_i;` | SOURCES tap_sync.tdi_ff | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tap_reg.ireg <- tap_ctrl_state, tap_sync.tck_rising

## Concept: Assembled DMI request (address, operation, write-data) that the module issues to the DMI consumer

- confidentiality: yes-assumed, line 283 `dmi_req_o.op   <= dmi_ctrl.op;` via dmi_req_o -- The assembled request fields are copied to the external dmi_req_o port (dmi_req_o.op/data/addr <= dmi_ctrl.* at lines 283-285), exposing address/operation/data outside the module; whether these are treated as secret depends on integration.
- integrity: yes-assumed, line 266 `dmi_ctrl.addr  <= tap_reg.dmi(40 downto 34);` via tap_reg.dmi -- dmi_ctrl.addr/op/wdata are loaded from the DMI DR captured in tap_reg.dmi when not busy and on DR-UPDATE (assignments at lines 266-271), so external JTAG-provided DMI DR content can change issued requests and must be trusted by the integrator.
- availability: yes-rtl, line 276 `dmi_ctrl.busy <= '0';` via dmi_rsp_i.ack -- dmi_ctrl.busy is cleared only when the external dmi_rsp_i.ack = '1' (line 276), so an external DMI peer can withhold ack and keep busy set, blocking subsequent requests and stalling progress.
- undermined behavior: no, line 283 `dmi_req_o.op   <= dmi_ctrl.op;` -- The external request outputs are direct copies from dmi_ctrl registers (lines 283-285) and the RTL provides no alternate debug/test override that substitutes a different driver for the request fields.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dmi_req_o | neorv32_debug_dtm | exit port | 2 -> 283 `dmi_req_o.op   <= dmi_ctrl.op;` | COPIES dmi_ctrl.op | verified | (via field dmi_req_o.op) | not listed |
| dmi_ctrl.addr | neorv32_debug_dtm | stores | 4 -> 266 `dmi_ctrl.addr  <= tap_reg.dmi(40 downto 34);` | CLOCKED_BY clk_i | verified |  | not listed |
| dmi_ctrl.wdata | neorv32_debug_dtm | stores | 3 -> 267 `dmi_ctrl.wdata <= tap_reg.dmi(33 downto 02);` | CLOCKED_BY clk_i | verified |  | not listed |
| dmi_ctrl.op | neorv32_debug_dtm | stores | 4 -> 269 `dmi_ctrl.op   <= tap_reg.dmi(1 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| tap_reg.dmi | neorv32_debug_dtm | stores | 3 -> 189 `when addr_dmi_c    => tap_reg.dmi    <= tap_reg.dmi_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dmi_ctrl.addr <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dr_trigger.valid, tap_reg.ireg; dmi_ctrl.wdata <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dr_trigger.valid, tap_reg.ireg; dmi_ctrl.op <- dmi_ctrl.busy, dmi_ctrl.dmihardreset, dr_trigger.valid, tap_reg.dmi, tap_reg.ireg; tap_reg.dmi <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising

## Concept: DMI read-response data held for readback and returned over JTAG

- confidentiality: yes-assumed, line 209 `when addr_dmi_c    => jtag_tdo_o <= tap_reg.dmi(0);` via jtag_tdo_o -- Response data from dmi_rsp_i is captured into dmi_ctrl.rdata (line 274), composed into the DMI DR (tap_reg.dmi_nxt at line 229) and shifted out on TDO when the DMI DR is selected (jtag_tdo_o <= tap_reg.dmi(0) at line 209), so response contents are externally observable.
- integrity: yes-assumed, line 274 `dmi_ctrl.rdata <= dmi_rsp_i.data;` via dmi_rsp_i.data -- dmi_ctrl.rdata is loaded directly from the external dmi_rsp_i.data (line 274), so the DMI peer controls the returned read data; the module does not further authenticate it.
- availability: yes-rtl, line 276 `dmi_ctrl.busy <= '0';` via dmi_rsp_i.ack -- Progress and clearing of dmi_ctrl.busy (which enables subsequent responses and readback capture) depends on external dmi_rsp_i.ack = '1' (line 276), so an external peer can withhold ack and block readback availability.
- undermined behavior: no, line 229 `tap_reg.dmi_nxt <= dmi_ctrl.addr & dmi_ctrl.rdata & replicate_f(dmi_ctrl.err, 2);` -- The read-response path is direct: external dmi_rsp_i.data -> dmi_ctrl.rdata -> tap_reg.dmi_nxt (lines 274,229) and then to TAP/JTAG; there is no alternate test override or bypass in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dmi_ctrl.rdata | neorv32_debug_dtm | stores | 4 -> 274 `dmi_ctrl.rdata <= dmi_rsp_i.data;` | CLOCKED_BY clk_i | verified |  | not listed |
| tap_reg.dmi | neorv32_debug_dtm | stores | 4 -> 196 `when addr_dmi_c    => tap_reg.dmi    <= tap_sync.tdi & tap_reg.dmi(tap_reg.dmi'left downto` | CLOCKED_BY clk_i | verified |  | not listed |
| jtag_tdo_o | neorv32_debug_dtm | exit port | 6 -> 209 `when addr_dmi_c    => jtag_tdo_o <= tap_reg.dmi(0);` | DERIVES_FROM tap_reg.dmi | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dmi_ctrl.rdata <- dmi_ctrl.busy; tap_reg.dmi <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising; jtag_tdo_o <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_falling

## Concept: DTM control register content (DTMCS) that sets dmireset/dmihardreset and advertises fixed fields

- confidentiality: yes-assumed, line 208 `when addr_dtmcs_c  => jtag_tdo_o <= tap_reg.dtmcs(0);` via jtag_tdo_o -- DTMCS contains control/status bits (including bits reflecting dmireset/dmihardreset) and those bits are driven out on TDO when the DTMCS DR is read (jtag_tdo_o <= tap_reg.dtmcs(0) at line 208), exposing internal control state outside the module.
- integrity: yes-assumed, line 195 `when addr_dtmcs_c  => tap_reg.dtmcs  <= tap_sync.tdi & tap_reg.dtmcs(tap_reg.dtmcs'left downto 1);` via jtag_tdi_i -- tap_reg.dtmcs can be written bit-serial via TDI during DR_SHIFT (tap_reg.dtmcs <= tap_sync.tdi & tap_reg.dtmcs(...) at line 195) and those captured bits are used to set dmi_ctrl.dmireset/dmihardreset (line 248), so external JTAG can change DTMCS fields; trust in the writer is integration-dependent.
- availability: yes-rtl, line 265 `if (dmi_ctrl.dmihardreset = '0') and (dr_trigger.valid = '1') and (tap_reg.ireg = addr_dmi_c) then` via dmi_ctrl.dmihardreset -- The DMI controller will not start requests while dmi_ctrl.dmihardreset = '1' (guard includes dmi_ctrl.dmihardreset = '0' at line 265), and dmihardreset is derived from DTMCS, so external writes to DTMCS can force/reset that bit and block DMI operation.
- undermined behavior: no, line 195 `when addr_dtmcs_c  => tap_reg.dtmcs  <= tap_sync.tdi & tap_reg.dtmcs(tap_reg.dtmcs'left downto 1);` -- DTMCS is produced only by the DR write/capture semantics (DR_SHIFT/DR_CAPTURE drivers at lines 195 and 188 and the combinational dtmcs_nxt assembly at lines 219-226); there is no separate debug/test override path in the RTL that substitutes a different driver.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tap_reg.dtmcs | neorv32_debug_dtm | stores | 3 -> 188 `when addr_dtmcs_c  => tap_reg.dtmcs  <= tap_reg.dtmcs_nxt;` | CLOCKED_BY clk_i | verified |  | hit |
| dmi_ctrl.dmireset | neorv32_debug_dtm | stores | 4 -> 248 `dmi_ctrl.dmireset     <= tap_reg.dtmcs(16);` | CLOCKED_BY clk_i | verified |  | not listed |
| dmi_ctrl.dmihardreset | neorv32_debug_dtm | stores | 4 -> 249 `dmi_ctrl.dmihardreset <= tap_reg.dtmcs(17);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tap_reg.dtmcs <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising; dmi_ctrl.dmireset <- dmi_ctrl.busy, dr_trigger.valid, tap_reg.ireg; dmi_ctrl.dmihardreset <- dmi_ctrl.busy, dr_trigger.valid, tap_reg.ireg

## Concept: DR-UPDATE event (dr_trigger.valid) that authorises capture/update actions and DMI request issuance

- confidentiality: no, line 161 `dr_trigger.valid <= '1' when (dr_trigger.sreg = "01") else '0';` via dr_trigger.sreg -- dr_trigger.valid is derived from TAP-driven state transitions (dr_trigger.sreg -> line 161) caused by the JTAG host, so the host already knows when it occurs and it does not expose additional secret information.
- integrity: yes-assumed, line 151 `if (tap_ctrl_state = DR_UPDATE) then` via tap_ctrl_state -- dr_trigger.sreg is set when tap_ctrl_state = DR_UPDATE (assignment at line 151) and TAP state is driven by external JTAG signals, so an untrusted JTAG can assert or suppress the DR-UPDATE event and thereby affect authorised captures and DMI issuance.
- availability: yes-rtl, line 151 `if (tap_ctrl_state = DR_UPDATE) then` via tap_ctrl_state -- The two-stage update trigger only asserts when the TAP reaches DR_UPDATE (guard at line 151), so external TAP control via jtag_tms/jtag_tck can prevent or force DR-UPDATE and block or enable authorised actions.
- undermined behavior: no, line 151 `if (tap_ctrl_state = DR_UPDATE) then` -- dr_trigger.valid is solely derived from the two-stage sreg updated in update_trigger (lines 151-156) with no alternate override or test-mode path presented in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| dr_trigger.sreg | neorv32_debug_dtm | stores | 3 -> 152 `dr_trigger.sreg(0) <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| dr_trigger.valid | neorv32_debug_dtm | computes | 2 -> 161 `dr_trigger.valid <= '1' when (dr_trigger.sreg = "01") else '0';` | GATES dr_trigger.sreg | occurrence only | no GATES record to 'dr_trigger.sreg' at occurrence 2 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): dr_trigger.sreg <- tap_ctrl_state; dr_trigger.valid <- dr_trigger.sreg

## Concept: Device IDCODE value reported via the IDCODE DR

- confidentiality: yes-assumed, line 207 `when addr_idcode_c => jtag_tdo_o <= tap_reg.idcode(0);` via jtag_tdo_o -- The IDCODE is loaded from generics on DR_CAPTURE (line 187) and driven out on TDO when the IDCODE DR is selected (jtag_tdo_o <= tap_reg.idcode(0) at line 207), so its contents are externally observable and may be sensitive depending on integration.
- integrity: yes-assumed, line 194 `when addr_idcode_c => tap_reg.idcode <= tap_sync.tdi & tap_reg.idcode(tap_reg.idcode'left downto 1);` via jtag_tdi_i -- Although the IDCODE is loaded from constants on DR_CAPTURE (line 187), the register is also shift-updateable from TDI in DR_SHIFT (line 194), so an external JTAG writer can alter the visible IDCODE between captures and integrity depends on trusting that writer.
- availability: yes-rtl, line 187 `when addr_idcode_c => tap_reg.idcode <= IDCODE_VERSION & IDCODE_PARTID & IDCODE_MANID & '1';` via tap_ctrl_state -- The IDCODE is captured from constants only in DR_CAPTURE (line 187) and readout depends on TAP state transitions, so external JTAG-controlled TAP state/TCK can block or freeze IDCODE availability.
- undermined behavior: no, line 187 `when addr_idcode_c => tap_reg.idcode <= IDCODE_VERSION & IDCODE_PARTID & IDCODE_MANID & '1';` -- IDCODE is driven only by reset and DR_CAPTURE/DR_SHIFT semantics (lines 170, 187, 194); there is no separate debug/test override path in the RTL that substitutes a different driver.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tap_reg.idcode | neorv32_debug_dtm | stores | 3 -> 187 `when addr_idcode_c => tap_reg.idcode <= IDCODE_VERSION & IDCODE_PARTID & IDCODE_MANID & '1` | CLOCKED_BY clk_i | verified |  | not listed |
| jtag_tdo_o | neorv32_debug_dtm | exit port | 4 -> 207 `when addr_idcode_c => jtag_tdo_o <= tap_reg.idcode(0);` | DERIVES_FROM tap_reg.idcode | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tap_reg.idcode <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_rising; jtag_tdo_o <- tap_ctrl_state, tap_reg.ireg, tap_sync.tck_falling
