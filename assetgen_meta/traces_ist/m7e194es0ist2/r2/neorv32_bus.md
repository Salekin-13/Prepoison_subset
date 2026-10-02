# neorv32_bus

**Purpose (model):** A collection of bus fabrics: a switch that arbitrates between local masters (ports A/B) and forwards the chosen request to an external bus (x_req_o) and returns responses; a gateway that decodes request addresses to per-port requests and aggregates device responses; optional request/response register stage; and AMO/RVS units that implement atomic read-modify-write and reservation semantics with timeout monitoring.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | Issue of a selected master request on the external bus (assemble x_req_o fields and assert x_req_o.stb) |  | 31 / 31 |
| operate | Arbitration and hold/release sequencing (state machine keeps S_IDLE / S_BUSY_A / S_BUSY_B and latches/clears a_req/b_req) |  | 55 / 55 |
| report | Forward external responses back to the selected master (data copied; ack/err gated by the grant decision) |  | 8 / 8 |
| operate | Address decode and per-port request generation (gateway: compute port_sel from req_i.addr and produce port_req(i)) |  | 20 / 20 |
| report | Aggregate device responses into int_rsp and drive external rsp_o (data copy; ack/err ORed; keeper.err influences ack/err) |  | 13 / 13 |
| operate | Request-monitoring and timeout (keeper): detect start of request, count cycles, set err on timeout and clear on response or lock change |  | 25 / 25 |
| operate | AMO RMW sequence and compute: schedule read, capture rdata, compute alu_res, and drive write (sys_req_o.data) during write phase |  | 45 / 45 |
| operate | Reservation (RVS) flow: compute rvso, control request forwarding for RVS, set sc_fail on store-conditional failure, and encode sc result into core response |  | 24 / 24 |
| reset | Reset to known values (clear arbiter/switch/gateway registers and keeper state under rstn_i) |  | 24 / 24 |

## Concept: Arbitration/grant decision (which master is granted and when a request is driven)

- confidentiality: yes-assumed, line 158 `x_req_o.stb   <= stb;` via x_req_o.stb -- The selection and strobe (sel/stb) are presented on the external request bus (x_req_o.*, e.g. x_req_o.stb at line 158), so an external observer can learn which master is granted and when.
- integrity: yes-rtl, line 114 `sel       <= '0';` via a_req_i.stb / b_req_i.stb (inputs) -- sel and stb are assigned directly by the FSM from the masters' request inputs (e.g. the idle branch assigns sel/stb when (a_req_i.stb='1') or (b_req_i.stb='1') at line 114 and 118) with no protection preventing those inputs from changing the selection while a transfer is presented (x_req_o.stb at line 158).
- availability: yes-rtl, line 90 `if (a_req_i.lock = '0') then` via a_req_i.lock / b_req_i.lock (inputs) -- The FSM observes and uses the masters' lock bits (e.g. in S_BUSY_A S_BUSY_B branches it tests locked(0)/locked(1) and checks a_req_i.lock/b_req_i.lock to leave busy; if a master holds its lock (checked at line 90/102) the grant can be held and other masters blocked.
- undermined behavior: no, line 79 `sel        <= '0';` via arbiter_fsm -- sel and stb are driven only by the arbiter_fsm combinational logic (default and state-branch assignments beginning at line 79) and there is no alternate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| state | neorv32_bus_switch | stores | 3 -> 55 `state  <= state_nxt;` | CLOCKED_BY clk_i | verified |  | hit |
| sel | neorv32_bus_switch | computes | 4 -> 87 `sel <= '0';` | SELECTED_BY state | verified |  | hit |
| sel_q | neorv32_bus_switch | stores | 3 -> 56 `sel_q  <= sel;` | CLOCKED_BY clk_i | verified |  | not listed |
| stb | neorv32_bus_switch | computes | 5 -> 115 `stb       <= '1';` | SELECTED_BY state | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sel <- a_req, a_req_i.stb, b_req, b_req_i.stb, sel_q, state; stb <- a_req, a_req_i.stb, b_req, b_req_i.stb, locked, sel_q, state

## Concept: Master lock state (per-master lock bits that hold a granted transfer until the master releases the lock)

- confidentiality: yes-assumed, line 158 `x_req_o.stb   <= stb;` via x_req_o.stb -- The locked bits affect which master continues to drive stb and thus the external request timing (x_req_o.stb at line 158), so external observers can infer locked state and the integrator may need to treat it as confidential.
- integrity: yes-assumed, line 111 `locked_nxt <= b_req_i.lock & a_req_i.lock;` via a_req_i.lock / b_req_i.lock (inputs) -- locked is computed directly from the masters' lock inputs (locked_nxt <= b_req_i.lock & a_req_i.lock at line 111) and then clocked into locked (line 57), so external writers determine its value and its integrity depends on the trustworthiness of those inputs.
- availability: yes-rtl, line 90 `if (a_req_i.lock = '0') then` via a_req_i.lock / b_req_i.lock (inputs) -- The FSM checks the masters' lock inputs to keep a transfer active or to release it (e.g. S_BUSY_A checks a_req_i.lock and uses it to decide when to return to S_IDLE at line 90), so an external master holding its lock can prevent progress.
- undermined behavior: no, line 111 `locked_nxt <= b_req_i.lock & a_req_i.lock;` via arbiter_fsm -- The locked register is derived only from the masters' lock inputs inside arbiter_fsm (locked_nxt <= b_req_i.lock & a_req_i.lock at line 111) and latched in arbiter_sync, with no alternate override or debug bypass in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| locked | neorv32_bus_switch | stores | 3 -> 57 `locked <= locked_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
| locked_nxt | neorv32_bus_switch | computes | 4 -> 111 `locked_nxt <= b_req_i.lock & a_req_i.lock;` | DERIVES_FROM a_req_i.lock | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): locked_nxt <- state

## Concept: Address decode result (which gateway port a request is routed to)

- confidentiality: no, line 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c)) else '0';` via req_i.addr -- port_sel is computed directly from the incoming request address (e.g. port_sel(0) <= '1' when req_i.addr matches A_BASE at line 356), and the requester already provides that address, so the selector reveals no additional secret by itself.
- integrity: yes-rtl, line 378 `port_req(i).stb <= port_sel(i) and req_i.stb;` via req_i.addr (input) -- port_sel is derived from req_i.addr and is used immediately to gate port_req(i).stb (port_req(i).stb <= port_sel(i) and req_i.stb at line 378) with no protection preventing the address from changing during an asserted strobe, so the decode can be altered by external inputs while a request is presented.
- availability: yes-rtl, line 378 `port_req(i).stb <= port_sel(i) and req_i.stb;` via req_i.addr (input) -- If the decoded address does not select any enabled port (port_sel has no '1'), port_req(i).stb will remain deasserted because of the port_sel mask (line 378), preventing the request from being forwarded and blocking progress.
- undermined behavior: no, line 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c)) else '0';` via address-comparison concurrent assignments -- port_sel bits are driven only by the explicit address-comparison assignments (lines 356-361) and there is no debug/test override in the RTL that substitutes a different decode.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| port_sel | neorv32_bus_gateway | computes | 2 -> 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c))` | GATED_BY req_i.addr | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): port_sel <- port_sel, req_i.addr

## Concept: Aggregated device response (int_rsp) that the gateway presents to the system output

- confidentiality: yes-assumed, line 399 `rsp_o.data <= int_rsp.data;` via rsp_o.data -- int_rsp (the OR-combined device responses) is copied to the external response outputs (rsp_o.data at line 399 and ack/err at 400-401), so external observers can learn its contents and an integrator may need to treat it as secret.
- integrity: yes-assumed, line 390 `tmp_v.data := tmp_v.data or port_rsp(i).data;` via port_rsp(i) (device response inputs) -- int_rsp is derived by OR'ing the per-port responses (tmp_v updated from port_rsp(i) at lines 390-392) which are driven by the devices (inputs); the RTL provides no internal validation, so the integrity of int_rsp depends on the trustworthiness of those device inputs.
- availability: yes-rtl, line 400 `rsp_o.ack  <= int_rsp.ack or keeper.err;` via port_rsp(i) / device responses -- The external output ack/err is gated by int_rsp.ack/err (and keeper.err) (rsp_o.ack <= int_rsp.ack or keeper.err at line 400), so devices can withhold ack or assert erroneous signals and thereby block or alter progress.
- undermined behavior: yes-rtl, line 400 `rsp_o.ack  <= int_rsp.ack or keeper.err;` via keeper.err -- The keeper error signal is ORed into the final outputs (rsp_o.ack/rsp_o.err at lines 400-401), giving a second, internal path (keeper.err) that can force the externally observed ack/err independently of int_rsp.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| int_rsp | neorv32_bus_gateway | computes | 2 -> 395 `int_rsp <= tmp_v;` | DERIVES_FROM port_rsp | verified |  | not listed |

## Concept: Gateway request-tracking and timeout state (keeper.busy, keeper.cnt, keeper.err, keeper.halt, keeper.lock)

- confidentiality: yes-assumed, line 400 `rsp_o.ack  <= int_rsp.ack or keeper.err;` via rsp_o.ack / rsp_o.err -- keeper state (notably keeper.err) is ORed into the external response outputs (rsp_o.ack/rsp_o.err at lines 400-401), so observers can learn timeout/error state and the integrator may need to treat these internal fields as confidential.
- integrity: yes-rtl, line 419 `keeper.busy <= req_i.stb;` via req_i.stb / req_i.lock (inputs) -- keeper.busy/lock/cnt are driven directly from the incoming request and lock inputs (keeper.busy <= req_i.stb at line 419; keeper.lock <= req_i.lock at line 420) and updated without additional protection while used by the timeout logic, so external inputs can alter keeper state during operation.
- availability: yes-rtl, line 422 `keeper.cnt <= std_ulogic_vector(unsigned(keeper.cnt) + 1);` via int_rsp.ack / req_i.lock -- The monitor increments keeper.cnt and only clears busy on int_rsp.ack or when a master clears its lock (the increment and timeout at line 422 and release/clear tests at lines 426-427), so external devices or masters can prevent or delay completion and thus affect availability.
- undermined behavior: yes-rtl, line 416 `keeper.halt <= port_sel(port_sel'left);` via port_sel (derived from req_i.addr) -- keeper.halt is driven from port_sel(port_sel'left) at line 416 and when halt='1' the timeout test is suppressed (the timeout assignment at line 423 checks keeper.halt), providing an alternate mode that bypasses timeout behavior.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| keeper.busy | neorv32_bus_gateway | stores | 4 -> 419 `keeper.busy <= req_i.stb;` | CLOCKED_BY clk_i | verified |  | not listed |
| keeper.cnt | neorv32_bus_gateway | stores | 4 -> 422 `keeper.cnt <= std_ulogic_vector(unsigned(keeper.cnt) + 1);` | CLOCKED_BY clk_i | verified |  | hit |
| keeper.err | neorv32_bus_gateway | stores | 6 -> 424 `keeper.err  <= '1';` | CLOCKED_BY clk_i | verified |  | hit |
| keeper.halt | neorv32_bus_gateway | stores | 3 -> 416 `keeper.halt <= port_sel(port_sel'left);` | CLOCKED_BY clk_i | verified |  | hit |
| keeper.lock | neorv32_bus_gateway | stores | 3 -> 420 `keeper.lock <= req_i.lock;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): keeper.busy <- int_rsp.ack, keeper.busy, keeper.cnt, keeper.halt, keeper.lock, req_i.lock; keeper.cnt <- keeper.busy; keeper.err <- keeper.busy, keeper.cnt, keeper.halt; keeper.lock <- keeper.busy

## Concept: AMO RMW execution context and result (arbiter state / wdata/rdata/cmd and alu_res) that produce write-back data and core responses

- confidentiality: yes-assumed, line 813 `sys_req_o.data  <= alu_res when (arbiter.state = S_WRITE) or (arbiter.state = S_WRITE_WAIT) else core_req_i.data;` via sys_req_o.data -- Computed AMO results (alu_res) are forwarded on the outgoing system request bus when issuing the write (sys_req_o.data <= alu_res in line 813), so external observers can learn the computed result.
- integrity: yes-rtl, line 779 `arbiter_nxt.wdata <= core_req_i.data;` via core_req_i.data (input) and sys_rsp_i.data (input) -- arbiter.wdata and arbiter.rdata are captured directly from core_req_i.data and sys_rsp_i.data (arbiter_nxt.wdata <= core_req_i.data at line 779; arbiter_nxt.rdata <= sys_rsp_i.data at line 785) and those external inputs can change the execution context that alu_res uses, with no RTL protection preventing changes during the sequence.
- availability: yes-rtl, line 786 `if (sys_rsp_i.ack = '1') then` via sys_rsp_i.ack (input) -- The arbiter waits for sys_rsp_i.ack to advance from read/wait states (if sys_rsp_i.ack = '1' then arbiter_nxt.state <= S_EXECUTE at line 786), so an external responder that withholds ack can stall AMO progress.
- undermined behavior: no, line 763 `arbiter <= arbiter_nxt;` via arbiter_sync / arbiter_fsm -- The AMO execution context (arbiter and alu_res) is driven only by the arbiter FSM and the AMO ALU processes (arbiter <= arbiter_nxt at line 763; alu_res updated in amo_alu), with no alternate debug/test override path present in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| arbiter | neorv32_bus_amo_rmw | stores | 6 -> 763 `arbiter <= arbiter_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
| alu_res | neorv32_bus_amo_rmw | stores | 4 -> 839 `when "000"  => alu_res <= arbiter.wdata;` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): alu_res <- arbiter.cmd

## Concept: Reservation/SC result and control (rvso and sc_fail) used to implement RVS semantics and to encode SC failure into core responses

- confidentiality: yes-assumed, line 963 `core_rsp_o.ack  <= sys_rsp_i.ack or sc_fail;` via core_rsp_o.ack / core_rsp_o.data -- sc_fail (and rvso-influenced SC outcome) is reflected in the core response outputs (core_rsp_o.ack and core_rsp_o.data at lines 963-964), so external observers can learn the reservation/SC result.
- integrity: yes-assumed, line 957 `sc_fail <= rvso and core_req_i.stb and core_req_i.rw and (not state(1));` via core_req_i.amo / core_req_i.amoop / core_req_i.stb (inputs) -- rvso is derived from the core request AMO fields (line 935) and sc_fail is set based on rvso together with core_req_i signals (sc_fail assignment at line 957), so external requester inputs determine these values and their integrity depends on the trust in those inputs.
- availability: yes-rtl, line 963 `core_rsp_o.ack  <= sys_rsp_i.ack or sc_fail;` via sys_rsp_i.ack (input) -- core response ack is gated by sys_rsp_i.ack or sc_fail (core_rsp_o.ack <= sys_rsp_i.ack or sc_fail at line 963), so an external responder that withholds ack can affect RVS/SC completion and observable availability.
- undermined behavior: no, line 935 `rvso <= '1' when (core_req_i.amo = '1') and (core_req_i.amoop(3 downto 2) = "10") else '0';` via rvso combinational assignment -- rvso and sc_fail are driven only by the combinational AMO fields (rvso at line 935) and the sc_result clocked update (line 957) with no alternate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rvso | neorv32_bus_amo_rvs | computes | 4 -> 935 `rvso <= '1' when (core_req_i.amo = '1') and (core_req_i.amoop(3 downto 2) = "10") else '0'` | GATED_BY core_req_i.amo | verified |  | not listed |
| sc_fail | neorv32_bus_amo_rvs | stores | 3 -> 957 `sc_fail <= rvso and core_req_i.stb and core_req_i.rw and (not state(1));` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rvso <- core_req_i.amo, core_req_i.amoop; sc_fail <- core_req_i.rw, core_req_i.stb, rvso, state
