# neorv32_bus

**Purpose (model):** This RTL file implements the neorv32 bus infrastructure: arbitration and multiplexing between masters A/B and the external system port X (neorv32_bus_switch), optional request/response register staging (neorv32_bus_reg), address decoding and per-port request routing (neorv32_bus_gateway / neorv32_bus_io_switch), and AMO RMW / RVS sequencing and ALU result computation (neorv32_bus_amo_rmw, neorv32_bus_amo_rvs). Inputs are decoded and gated, selected request fields are driven to downstream ports, responses are aggregated and forwarded, and internal state registers sequence transactions.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | master request forwarded to the external system (x_req_o fields and strobe) |  | 28 / 28 |
| configure | lock bits captured from incoming requests and held (locked / locked_nxt) |  | 4 / 4 |
| operate | AMO read-modify-write sequence: accept core AMO request, wait for read, compute ALU result, issue write request, and produce core response |  | 20 / 20 |
| report | forward responses from the external bus or devices back to the requesting master (a_rsp_o/b_rsp_o/rsp_o) |  | 14 / 14 |
| read out | address decode and device routing: req_i.addr → port_sel → port_req(i) → device request outputs |  | 10 / 10 |
| lock | keeper reservation and timeout tracking (keeper.busy, keeper.lock, keeper.cnt, keeper.err, keeper.halt) |  | 12 / 12 |
| reset | synchronous registers cleared to known values on rstn_i asserted low (switch, reg, gateway, AMO units) |  | 7 / 7 |

## Concept: Arbitration choice between masters A and B (the selection that decides which master is connected to X)

- confidentiality: yes-assumed, line 140 `x_req_o.addr  <= a_req_i.addr  when (sel = '0') else b_req_i.addr;` via x_req_o.addr -- sel determines which master's address/control fields are driven to the external bus (x_req_o.addr at line 140) so an outside observer can infer the selection from those outputs.
- integrity: yes-assumed, line 114 `sel       <= '0';` via a_req_i.stb / b_req_i.stb -- sel is computed from external masters' request signals and sel_q/ROUND_ROBIN_EN in the comb arbiter_fsm (assignment at line 114), so those external writers can influence the selection and whether it changes.
- availability: yes-rtl, line 90 `if (a_req_i.lock = '0') then` via a_req_i.lock -- the FSM remains in the busy arm while a master's lock input is asserted (the transition to S_IDLE is gated on a_req_i.lock = '0' at line 90), so a_req_i.lock can prevent arbitration progress and freeze the selection.
- undermined behavior: no, line 79 `sel        <= '0';` via arbiter_fsm.sel -- there is no alternate debug/test override path in the RTL; sel is driven only by the arbiter_fsm assignments (default at line 79) and latched at line 56.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| sel_q | neorv32_bus_switch | stores | 3 -> 56 `sel_q  <= sel;` | CLOCKED_BY clk_i | verified |  | not listed |
| x_req_o.addr | neorv32_bus_switch | exit port | 2 -> 140 `x_req_o.addr  <= a_req_i.addr  when (sel = '0') else b_req_i.addr;` | DERIVES_FROM a_req_i.addr | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): x_req_o.addr <- sel

## Concept: Forwarded system request (address, data and control fields sent on x_req_o to the external bus)

- confidentiality: yes-assumed, line 150 `x_req_o.data  <= b_req_i.data  when PORT_A_READ_ONLY else` via x_req_o.data -- x_req_o carries the selected master's address/data/control to the external bus (e.g. x_req_o.data assignment at line 150) so those values are observable outside the IP and may be treated as confidential by integrators.
- integrity: yes-assumed, line 150 `x_req_o.data  <= b_req_i.data  when PORT_A_READ_ONLY else` via a_req_i.data / b_req_i.data -- x_req_o.data is driven directly from a_req_i.data or b_req_i.data under sel (line 150), so the external masters that supply those inputs can change the forwarded request fields.
- availability: yes-rtl, line 93 `elsif (x_rsp_i.ack = '1') then` via x_rsp_i.ack -- the arbiter waits for the external bus response (x_rsp_i.ack checked at line 93) and FSM transitions that drive stb/x_req_o.stb depend on that ack, so the external response signal can block or freeze forwarding of new x_req_o requests.
- undermined behavior: no, line 150 `x_req_o.data  <= b_req_i.data  when PORT_A_READ_ONLY else` via x_req_o.data -- there is no runtime debug/test override in the RTL that substitutes or bypasses the x_req_o drivers; x_req_o.* is driven only by the selection and the source fields (e.g. x_req_o.data at line 150).

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| x_req_o.addr | neorv32_bus_switch | exit port | 2 -> 140 `x_req_o.addr  <= a_req_i.addr  when (sel = '0') else b_req_i.addr;` | DERIVES_FROM a_req_i.addr | verified |  | not listed |
| x_req_o.data | neorv32_bus_switch | exit port | 2 -> 150 `x_req_o.data  <= b_req_i.data  when PORT_A_READ_ONLY else` | DERIVES_FROM a_req_i.data | verified |  | not listed |
| x_req_o.rw | neorv32_bus_switch | exit port | 2 -> 147 `x_req_o.rw    <= a_req_i.rw    when (sel = '0') else b_req_i.rw;` | DERIVES_FROM a_req_i.rw | verified |  | not listed |
| x_req_o.lock | neorv32_bus_switch | exit port | 2 -> 143 `x_req_o.lock  <= a_req_i.lock  when (sel = '0') else b_req_i.lock;` | DERIVES_FROM a_req_i.lock | verified |  | not listed |
| x_req_o.fence | neorv32_bus_switch | exit port | 2 -> 148 `x_req_o.fence <= a_req_i.fence or b_req_i.fence;` | GATED_BY a_req_i.fence | verified |  | not listed |
| x_req_o.stb | neorv32_bus_switch | exit port | 2 -> 158 `x_req_o.stb   <= stb;` | COPIES stb | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): x_req_o.addr <- sel; x_req_o.data <- sel; x_req_o.rw <- sel; x_req_o.lock <- sel; x_req_o.fence <- a_req_i.fence, b_req_i.fence

## Concept: Response delivery to masters (the switch's a_rsp_o / b_rsp_o outputs that return data/ack/err to A and B)

- confidentiality: yes-assumed, line 163 `a_rsp_o.data <= x_rsp_i.data;` via a_rsp_o.data -- response fields from the external bus are forwarded to the masters (a_rsp_o.data copies x_rsp_i.data at line 163), so external observers (the masters) learn these values and they may be considered confidential.
- integrity: yes-assumed, line 163 `a_rsp_o.data <= x_rsp_i.data;` via x_rsp_i.data / x_rsp_i.ack -- a_rsp_o and b_rsp_o are driven from the external bus inputs x_rsp_i.* (copy at line 163 and gated ack/err at lines 164/165), so an external responder can alter the response seen by the masters.
- availability: yes-rtl, line 164 `a_rsp_o.ack  <= x_rsp_i.ack when (sel = '0') else '0';` via x_rsp_i.ack -- ack to a master is gated by x_rsp_i.ack and sel (a_rsp_o.ack <= x_rsp_i.ack when sel='0' at line 164), so the external bus's ack input can prevent ack delivery and therefore block master progress.
- undermined behavior: no, line 163 `a_rsp_o.data <= x_rsp_i.data;` via a_rsp_o.data -- there is no alternate debug/test path that overrides the response forwarding; responses are only copied/gated from x_rsp_i into a_rsp_o/b_rsp_o (data copy at line 163).

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| a_rsp_o.data | neorv32_bus_switch | exit port | 2 -> 163 `a_rsp_o.data <= x_rsp_i.data;` | COPIES x_rsp_i.data | verified |  | not listed |
| a_rsp_o.ack | neorv32_bus_switch | exit port | 2 -> 164 `a_rsp_o.ack  <= x_rsp_i.ack when (sel = '0') else '0';` | DERIVES_FROM x_rsp_i.ack | verified |  | not listed |
| a_rsp_o.err | neorv32_bus_switch | exit port | 2 -> 165 `a_rsp_o.err  <= x_rsp_i.err when (sel = '0') else '0';` | DERIVES_FROM x_rsp_i.err | verified |  | not listed |
| b_rsp_o.data | neorv32_bus_switch | exit port | 2 -> 167 `b_rsp_o.data <= x_rsp_i.data;` | COPIES x_rsp_i.data | verified |  | not listed |
| b_rsp_o.ack | neorv32_bus_switch | exit port | 2 -> 168 `b_rsp_o.ack  <= x_rsp_i.ack when (sel = '1') else '0';` | DERIVES_FROM x_rsp_i.ack | verified |  | not listed |
| b_rsp_o.err | neorv32_bus_switch | exit port | 2 -> 169 `b_rsp_o.err  <= x_rsp_i.err when (sel = '1') else '0';` | DERIVES_FROM x_rsp_i.err | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): a_rsp_o.ack <- sel; a_rsp_o.err <- sel; b_rsp_o.ack <- sel; b_rsp_o.err <- sel

## Concept: Arbiter FSM state in the switch (state register that sequences idle/busy_A/busy_B)

- confidentiality: yes-assumed, line 164 `a_rsp_o.ack  <= x_rsp_i.ack when (sel = '0') else '0';` via a_rsp_o.ack -- the FSM state determines which master is served and hence which response ack/err are forwarded (a_rsp_o.ack gating at line 164), so external observers can infer the internal state from outputs.
- integrity: yes-assumed, line 55 `state  <= state_nxt;` via state_nxt (computed by arbiter_fsm from a_req_i.stb, b_req_i.stb, x_rsp_i.ack, locked) -- the stored FSM state is updated from state_nxt on the clock (state <= state_nxt at line 55) and state_nxt is driven by external request and response signals, so external inputs can change the FSM state and its sequencing.
- availability: yes-rtl, line 93 `elsif (x_rsp_i.ack = '1') then` via x_rsp_i.ack -- the FSM returns to S_IDLE on x_rsp_i.ack (e.g. 'elsif (x_rsp_i.ack = '1') then state_nxt <= S_IDLE' at line 93), so absence of an external ack or asserted lock can freeze the FSM and block progress.
- undermined behavior: no, line 55 `state  <= state_nxt;` via state <= state_nxt -- the FSM state register has a single synchronous update path (state <= state_nxt at line 55) and the RTL contains no alternate debug/test override for the state.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| state | neorv32_bus_switch | stores | 3 -> 55 `state  <= state_nxt;` | CLOCKED_BY clk_i | verified |  | hit |

## Concept: Per-master lock bits captured in the switch (locked register) that hold request lock state

- confidentiality: yes-assumed, line 111 `locked_nxt <= b_req_i.lock & a_req_i.lock;` via locked_nxt -- locked stores bits derived from masters' lock inputs (assignment at line 111) and those bits affect externally observable transaction behavior, so their values can be inferred and may be considered confidential by integrators.
- integrity: yes-assumed, line 111 `locked_nxt <= b_req_i.lock & a_req_i.lock;` via a_req_i.lock / b_req_i.lock -- locked is computed from the masters' lock inputs (line 111) and then latched (line 57), so external masters write the lock bits and can change them; whether those writers are trusted depends on integration.
- availability: yes-rtl, line 90 `if (a_req_i.lock = '0') then` via a_req_i.lock -- the FSM stays in the busy arm while the master's lock is asserted (the transition to S_IDLE is gated on a_req_i.lock = '0' at line 90), therefore a master's lock input can block progress and freeze related state.
- undermined behavior: no, line 57 `locked <= locked_nxt;` via locked <= locked_nxt -- locked is updated only via the computed locked_nxt and clocked assignment (locked <= locked_nxt at line 57); there is no alternate override or debug path in the RTL that bypasses this update.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| locked | neorv32_bus_switch | stores | 3 -> 57 `locked <= locked_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
| locked_nxt | neorv32_bus_switch | computes | 4 -> 111 `locked_nxt <= b_req_i.lock & a_req_i.lock;` | DERIVES_FROM a_req_i.lock | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): locked_nxt <- state

## Concept: Address decode / port selection in gateway (which downstream port receives a given request address)

- confidentiality: yes-assumed, line 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c)) else '0';` via port_sel(0) <= ... (req_i.addr check) -- the decode uses the incoming request address (assignment at line 356) and the selected port is observable by which port_req/port outputs are asserted (e.g. a_req_o at line 366), so the selection reveals address routing decisions to outside observers.
- integrity: yes-assumed, line 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c)) else '0';` via req_i.addr -- port_sel is driven directly from req_i.addr comparisons (line 356), so external request addresses determine routing and can change the selected downstream port.
- availability: no, line 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c)) else '0';` via port_sel assignment -- port_sel is computed combinationally from req_i.addr and compile-time enables (lines 356-361) and does not require an additional runtime enable that an external actor could toggle to freeze the decode itself.
- undermined behavior: no, line 361 `port_sel(3) <= '1' when X_EN and (port_sel(2 downto 0) = "000") else '0';` via port_sel(3) fallback -- there is no runtime debug/test override in the RTL; port_sel bits are produced only by the address comparisons and the X_EN fallback (line 361) with no separate bypass path.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| req_i.addr | neorv32_bus_gateway | sets | 2 -> 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c))` | GATES port_sel | verified |  | not listed |
| a_req_o | neorv32_bus_gateway | exit port | 2 -> 366 `a_req_o <= port_req(0); port_rsp(0) <= a_rsp_i;` | DERIVES_FROM port_req | verified |  | not listed |

## Concept: Gateway keeper state (busy, lock, error) that enforces reservation, timeouts and response composition

- confidentiality: yes-assumed, line 400 `rsp_o.ack  <= int_rsp.ack or keeper.err;` via rsp_o.ack -- keeper.err is combined into externally visible response signals (rsp_o.ack at line 400 and rsp_o.err at line 401), so the keeper state affects outputs that an external observer can see.
- integrity: yes-assumed, line 419 `keeper.busy <= req_i.stb;` via req_i.stb / req_i.lock -- keeper.busy and keeper.lock are set from the incoming request signals (keeper.busy <= req_i.stb and keeper.lock <= req_i.lock at lines 419-420), so external request inputs drive and can change keeper state.
- availability: yes-rtl, line 426 `elsif (int_rsp.ack = '1') or ((keeper.lock = '1') and (req_i.lock = '0')) then` via int_rsp.ack / req_i.lock -- keeper.busy is only cleared when an external response ack arrives or a held lock is released (condition at line 426), so the external responder or requester can block or freeze keeper-driven progress.
- undermined behavior: no, line 416 `keeper.halt <= port_sel(port_sel'left);` via keeper.halt <= port_sel(...) -- the keeper signals are only driven by the bus_monitor logic and port_sel (line 416) and there is no separate debug/test override path to replace or bypass the keeper state in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| keeper.busy | neorv32_bus_gateway | stores | 4 -> 419 `keeper.busy <= req_i.stb;` | CLOCKED_BY clk_i | verified |  | not listed |
| keeper.err | neorv32_bus_gateway | stores | 6 -> 424 `keeper.err  <= '1';` | CLOCKED_BY clk_i | verified |  | hit |
| keeper.lock | neorv32_bus_gateway | stores | 3 -> 420 `keeper.lock <= req_i.lock;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): keeper.busy <- int_rsp.ack, keeper.busy, keeper.cnt, keeper.halt, keeper.lock, req_i.lock; keeper.err <- keeper.busy, keeper.cnt, keeper.halt; keeper.lock <- keeper.busy

## Concept: AMO ALU result (the computed value used for AMO writeback)

- confidentiality: yes-assumed, line 813 `sys_req_o.data  <= alu_res when (arbiter.state = S_WRITE) or (arbiter.state = S_WRITE_WAIT) else core_req_i.data;` via sys_req_o.data -- alu_res is driven onto the system request data bus when performing the AMO write (sys_req_o.data uses alu_res at line 813), so the value is observable outside the IP and may be considered confidential.
- integrity: yes-assumed, line 839 `when "000"  => alu_res <= arbiter.wdata;` via arbiter.wdata / arbiter.rdata (derived from core_req_i.data / sys_rsp_i.data) -- alu_res is computed from arbiter operands (arbiter.wdata and arbiter.rdata assigned from core_req_i.data and sys_rsp_i.data at lines like 779/785) so external inputs determine the ALU result and can influence it.
- availability: yes-rtl, line 813 `sys_req_o.data  <= alu_res when (arbiter.state = S_WRITE) or (arbiter.state = S_WRITE_WAIT) else core_req_i.data;` via arbiter.state -- sys_req_o.data is driven from alu_res only when the arbiter is in the write states (the guard at line 813), so if the arbiter never reaches those states (e.g. due to missing sys responses) the ALU result will not be presented to the system.
- undermined behavior: no, line 836 `alu_res <= (others => '0');` via amo_alu (alu_res) -- alu_res is produced only by the amo_alu process (reset at line 836 and case assignments at lines 839-844); there is no alternate override or debug substitution in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| alu_res | neorv32_bus_amo_rmw | stores | 4 -> 839 `when "000"  => alu_res <= arbiter.wdata;` | CLOCKED_BY clk_i | verified |  | hit |
| sys_req_o.data | neorv32_bus_amo_rmw | exit port | 2 -> 813 `sys_req_o.data  <= alu_res when (arbiter.state = S_WRITE) or (arbiter.state = S_WRITE_WAIT` | DERIVES_FROM alu_res | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): alu_res <- arbiter.cmd; sys_req_o.data <- arbiter.state

## Concept: AMO arbiter sequencing state (the arbiter record that sequences RMW phases)

- confidentiality: yes-assumed, line 826 `core_rsp_o.data <= sys_rsp_i.data when (arbiter.state = S_IDLE) else arbiter.rdata;` via core_rsp_o.data -- arbiter sequencing determines which data is returned to the core and when (core_rsp_o.data depends on arbiter.state at line 826), so external behavior reveals the arbiter's internal sequencing state.
- integrity: yes-assumed, line 780 `arbiter_nxt.state <= S_READ_WAIT;` via core_req_i.stb / core_req_i.amo -- arbiter_nxt.state is set from incoming core requests (e.g. transition to S_READ_WAIT at line 780 when core_req_i.stb and core_req_i.amo), so external request signals influence and can change the arbiter sequencing state.
- availability: yes-rtl, line 787 `arbiter_nxt.state <= S_EXECUTE;` via sys_rsp_i.ack -- the arbiter advances from read-wait to execute only when sys_rsp_i.ack is asserted (the guard at line 787), so missing or delayed system responses can block the arbiter and prevent sequencing progress.
- undermined behavior: no, line 763 `arbiter <= arbiter_nxt;` via arbiter <= arbiter_nxt -- the arbiter state updates synchronously from arbiter_nxt (arbiter <= arbiter_nxt at line 763) and there is no separate debug/test override path in the RTL to bypass this sequencing.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| arbiter | neorv32_bus_amo_rmw | stores | 6 -> 763 `arbiter <= arbiter_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
