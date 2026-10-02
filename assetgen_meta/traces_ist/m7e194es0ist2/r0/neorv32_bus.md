# neorv32_bus

**Purpose (model):** The supplied RTL implements the Neorv32 bus infrastructure: it arbitrates and multiplexes requests from multiple masters (A, B, core, main, etc.) to shared device/system ports (x_req_o/sys_req_o/device_req_o), decodes addresses to target device ports, optionally registers requests/responses, implements AMO (read-modify-write) and RVS store-conditional semantics, and monitors outstanding transactions for timeouts; it reads master request ports, holds/arbitrates state, and drives request and response ports to devices and masters.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | transaction start (strobe): a master's stb is captured/accumulated and the arbiter asserts the internal start decision copied to the outgoing request strobe |  | 6 / 6 |
| operate | request multiplexing/forwarding: the selected master's request fields (addr, data, rw, src, priv, lock, amo, amoop, debug, ben, fence) are forwarded to the shared output x_req_o |  | 12 / 12 |
| lock | request lock capture and hold: per-request lock bits are captured into locked/locked_nxt and hold or release the busy state |  | 7 / 7 |
| report | response aggregation and forwarding: responses from devices are OR-aggregated (gateway) and gated back to the requesting master (a_rsp_o, b_rsp_o) with error/ack gating by selection and keeper.err |  | 11 / 11 |
| operate | AMO read-modify-write: core_req_i triggers a read, the arbiter captures rdata, the ALU computes alu_res, the core issues a write with alu_res to sys_req_o and finally the core receives the response |  | 8 / 8 |
| report | RVS store-conditional result: rvso detection and sc_result set sc_fail, which alters the core response (ack/data) |  | 6 / 6 |
| reset | registers and state are cleared by active-low rstn_i (bus switch, regs, gateway keeper, AMO arbiter and ALU, RVS sc_fail) |  | 7 / 7 |

## Concept: Multiplexed system request (the request record sent out on the shared bus: x_req_o)

- confidentiality: yes-assumed, line 30 `x_req_o : out bus_req_t;` via x_req_o (output port) -- The request record's fields are driven onto the module's external output port (assignments at lines 140-158) so an external observer can read the forwarded request; integrator may treat that data as secret.
- integrity: yes-assumed, line 140 `x_req_o.addr  <= a_req_i.addr  when (sel = '0') else b_req_i.addr;` via a_req_i / b_req_i (input ports) -- Each x_req_o field is selected directly from a_req_i or b_req_i under sel (example x_req_o.addr at line 140) so external masters driving those inputs can change the outgoing request and trust depends on integration.
- availability: yes-rtl, line 93 `elsif (x_rsp_i.ack = '1') then` via x_rsp_i.ack (input) -- The arbiter FSM waits for the external response acknowledge (x_rsp_i.ack) to return from a BUSY state (line 93), so if ack does not arrive externally new x_req_o transactions (via stb) can be blocked.
- undermined behavior: no, line 140 `x_req_o.addr  <= a_req_i.addr  when (sel = '0') else b_req_i.addr;` -- x_req_o fields have a single concurrent-driver pattern (each field assigned from a_req_i or b_req_i under sel, e.g. line 140) and no runtime debug/test override is present in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| x_req_o | neorv32_bus_switch | exit port | 2 -> 140 `x_req_o.addr  <= a_req_i.addr  when (sel = '0') else b_req_i.addr;` | DERIVES_FROM a_req_i.addr | occurrence only | no DERIVES_FROM record to 'a_req_i.addr' at occurrence 2 | not listed |
| a_req_i | neorv32_bus_switch | sets | 9 -> 140 `x_req_o.addr  <= a_req_i.addr  when (sel = '0') else b_req_i.addr;` | SOURCES x_req_o.addr | occurrence only | no SOURCES record to 'x_req_o.addr' at occurrence 9 | not listed |
| b_req_i | neorv32_bus_switch | sets | 9 -> 140 `x_req_o.addr  <= a_req_i.addr  when (sel = '0') else b_req_i.addr;` | SOURCES x_req_o.addr | occurrence only | no SOURCES record to 'x_req_o.addr' at occurrence 9 | not listed |
| sel | neorv32_bus_switch | computes | 4 -> 87 `sel <= '0';` | SELECTED_BY state | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sel <- a_req, a_req_i.stb, b_req, b_req_i.stb, sel_q, state

## Concept: Arbitration decision (which master is granted / current busy state)

- confidentiality: yes-assumed, line 164 `a_rsp_o.ack  <= x_rsp_i.ack when (sel = '0') else '0';` via a_rsp_o.ack (output) -- The arbitration state controls sel which gates a_rsp_o.ack (line 164) so an external observer can infer which master is currently granted and the integrator may treat that status as sensitive.
- integrity: yes-rtl, line 55 `state  <= state_nxt;` via state_nxt (arbiter_fsm) -- The state register (which determines grants) is updated unconditionally from the combinational state_nxt on each clock (state <= state_nxt at line 55) and that state decides resource grants, so external inputs feeding the FSM can change the arbitration decision.
- availability: yes-rtl, line 93 `elsif (x_rsp_i.ack = '1') then` via x_rsp_i.ack (input) -- The FSM remains in busy states until the external x_rsp_i.ack is seen (checked at line 93), so lack of external acknowledgement can freeze the arbitration state and prevent progress.
- undermined behavior: no, line 55 `state  <= state_nxt;` -- The arbitration state has a single register update path (state <= state_nxt at line 55) driven by the FSM and there is no alternate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| state | neorv32_bus_switch | stores | 3 -> 55 `state  <= state_nxt;` | CLOCKED_BY clk_i | verified |  | hit |
| sel_q | neorv32_bus_switch | stores | 3 -> 56 `sel_q  <= sel;` | CLOCKED_BY clk_i | verified |  | not listed |
| state_nxt | neorv32_bus_switch | computes | 8 -> 116 `state_nxt <= S_BUSY_A;` | SELECTED_BY state | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): state_nxt <- a_req, a_req_i.lock, a_req_i.stb, b_req, b_req_i.lock, b_req_i.stb, locked, sel_q ...

## Concept: Transaction start (internal strobe decision that begins a transfer)

- confidentiality: yes-assumed, line 158 `x_req_o.stb   <= stb;` via x_req_o.stb (output port) -- The internal start strobe is copied to the external port x_req_o.stb at line 158, so an external agent can observe transaction start events and the integrator may treat those events as sensitive.
- integrity: yes-assumed, line 89 `stb <= a_req_i.stb;` via a_req_i.stb / b_req_i.stb (input ports) -- stb is driven from masters' strobe inputs in the busy cases (e.g. line 89) and from the FSM in start conditions (lines 115/119/etc.), so external masters can influence the start decision and trust depends on integration.
- availability: yes-rtl, line 93 `elsif (x_rsp_i.ack = '1') then` via x_rsp_i.ack (input) -- The FSM waits for external x_rsp_i.ack to leave BUSY and allow new starts (checked at line 93), so withholding ack externally prevents new stb assertions and stalls transactions.
- undermined behavior: no, line 115 `stb       <= '1';` -- stb assignments occur only in the arbiter_fsm arms (example line 115) and there is no separate debug/test override that replaces or bypasses stb in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| stb | neorv32_bus_switch | computes | 5 -> 115 `stb       <= '1';` | SELECTED_BY state | verified |  | hit |
| a_req | neorv32_bus_switch | stores | 3 -> 59 `a_req <= '0';` | CLOCKED_BY clk_i | verified |  | hit |
| b_req | neorv32_bus_switch | stores | 3 -> 64 `b_req <= '0';` | CLOCKED_BY clk_i | verified |  | hit |
| x_req_o | neorv32_bus_switch | exit port | 13 -> 158 `x_req_o.stb   <= stb;` | COPIES stb | occurrence only | no COPIES record to 'stb' at occurrence 13 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): stb <- a_req, a_req_i.stb, b_req, b_req_i.stb, locked, sel_q, state; a_req <- a_req, a_req_i.stb, state; b_req <- b_req, b_req_i.stb, state

## Concept: Request lock state (per-master lock bits that hold a busy grant)

- confidentiality: yes-assumed, line 88 `if (locked(0) = '1') then` via x_req_o.stb / a_rsp_o (outputs) -- The locked bits are captured from masters and are used to alter FSM behavior (locked(0) gates stb in line 88), which changes externally visible transaction timing, so an external observer can infer lock state and integrator may consider it sensitive.
- integrity: yes-assumed, line 111 `locked_nxt <= b_req_i.lock & a_req_i.lock;` via a_req_i.lock and b_req_i.lock (input ports) -- locked is derived from master lock inputs at line 111 (locked_nxt <= b_req_i.lock & a_req_i.lock) and then latched at line 57, so external masters write the lock bits and whether those writers are trusted depends on integration.
- availability: yes-rtl, line 90 `if (a_req_i.lock = '0') then` via a_req_i.lock (input) -- While busy the FSM checks a_req_i.lock = '0' to return to idle (line 90), so an external master holding its lock bit prevents the arbiter from returning to idle and can block further progress.
- undermined behavior: no, line 57 `locked <= locked_nxt;` -- The locked register is only updated via locked <= locked_nxt on the clock (line 57) with locked_nxt computed by the FSM and there is no alternate debug/test bypass in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| locked | neorv32_bus_switch | stores | 3 -> 57 `locked <= locked_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
| locked_nxt | neorv32_bus_switch | computes | 4 -> 111 `locked_nxt <= b_req_i.lock & a_req_i.lock;` | DERIVES_FROM a_req_i.lock | verified |  | not listed |
| a_req_i | neorv32_bus_switch | sets | 6 -> 111 `locked_nxt <= b_req_i.lock & a_req_i.lock;` | SOURCES locked_nxt | occurrence only | no SOURCES record to 'locked_nxt' at occurrence 6 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): locked_nxt <- state

## Concept: Address decode result (destination port selection: port_sel)

- confidentiality: yes-assumed, line 366 `a_req_o <= port_req(0); port_rsp(0) <= a_rsp_i;` via a_req_o / b_req_o / c_req_o / x_req_o (output ports) -- port_sel is computed from req_i.addr and EN flags (line 356) and determines which per-port request is driven out (lines 366-369), so external recipients and timing reveal the decoded destination and integrator may treat that as sensitive.
- integrity: yes-assumed, line 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c)) else '0';` via req_i.addr (input) -- port_sel is computed directly from the incoming request address and EN generics at line 356, so an external requester controlling req_i.addr can change the destination selected and trust depends on integration.
- availability: no, line 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c)) else '0';` -- port_sel is a combinational decode computed from req_i.addr and compile-time EN/Base configuration (line 356) and is not gated by a runtime enable that an external actor can use to freeze updates.
- undermined behavior: no, line 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c)) else '0';` -- port_sel has a single combinational definition (lines 356-361) and the RTL contains no runtime debug/test override to substitute a different selection.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| port_sel | neorv32_bus_gateway | computes | 2 -> 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c))` | GATES req_i.addr | occurrence only | no GATES record to 'req_i.addr' at occurrence 2 | hit |
| req_i | neorv32_bus_gateway | sets | 2 -> 356 `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c))` | GATED_BY port_sel | occurrence only | no GATED_BY record to 'port_sel' at occurrence 2 | not listed |
| a_req_o | neorv32_bus_gateway | exit port | 2 -> 366 `a_req_o <= port_req(0); port_rsp(0) <= a_rsp_i;` | DERIVES_FROM port_req | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): port_sel <- port_sel, req_i.addr

## Concept: Timeout/error indicator (keeper.err) that signals request failure/unavailability

- confidentiality: yes-assumed, line 400 `rsp_o.ack  <= int_rsp.ack or keeper.err;` via rsp_o.ack / rsp_o.err (output ports) -- keeper.err is ORed into the external response signals rsp_o.ack and rsp_o.err (line 400-401) so an external observer can detect a timeout/error condition and integrator may treat that information as sensitive.
- integrity: yes-assumed, line 424 `keeper.err  <= '1';` via keeper.cnt / keeper.halt (internal counters influenced by req_i.stb and port_sel) -- keeper.err is driven by internal timeout logic at line 424 when the counter and halt conditions are met, and those internal conditions are influenced by external inputs (e.g. req_i.stb or lack of int_rsp.ack), so external actors can cause the error indicator to change and trust depends on integration.
- availability: yes-rtl, line 424 `keeper.err  <= '1';` via keeper.cnt / keeper.halt (driven by req_i.stb and port_sel) -- The RTL sets keeper.err when the timeout counter overflows while halt is clear (assignment at line 424), and an external lack of response (or repeated requests) can force this condition and thus disrupt normal response availability.
- undermined behavior: no, line 424 `keeper.err  <= '1';` -- keeper.err is updated only by the bus_monitor process (assignment at line 424) according to the timeout condition and there is no alternate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| keeper.err | neorv32_bus_gateway | stores | 6 -> 424 `keeper.err  <= '1';` | CLOCKED_BY clk_i | verified |  | hit |
| rsp_o | neorv32_bus_gateway | exit port | 3 -> 400 `rsp_o.ack  <= int_rsp.ack or keeper.err;` | GATED_BY keeper.err | occurrence only | no GATED_BY record to 'keeper.err' at occurrence 3 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): keeper.err <- keeper.busy, keeper.cnt, keeper.halt

## Concept: AMO computed write data (alu_res) and its delivery to the system request (sys_req_o.data)

- confidentiality: yes-assumed, line 813 `sys_req_o.data  <= alu_res when (arbiter.state = S_WRITE) or (arbiter.state = S_WRITE_WAIT) else core_req_i.data;` via sys_req_o.data (output port) -- The ALU result alu_res is selected and driven onto the external sys_req_o.data when the arbiter is in the write phase (line 813), so the computed write payload is visible outside and may be considered secret by an integrator.
- integrity: yes-assumed, line 839 `when "000"  => alu_res <= arbiter.wdata;` via amo_alu (arbiter.wdata/arbiter.rdata derived from core_req_i and sys_rsp_i) -- alu_res is computed in the amo_alu process (assignments at lines 839-844) from arbiter.rdata/arbiter.wdata which derive from external core and system inputs, so external inputs can influence the computed write and trust depends on integration.
- availability: yes-rtl, line 813 `sys_req_o.data  <= alu_res when (arbiter.state = S_WRITE) or (arbiter.state = S_WRITE_WAIT) else core_req_i.data;` via arbiter.state and sys_rsp_i.ack (inputs affecting arbiter progression) -- sys_req_o.data forwards alu_res only when the arbiter is in S_WRITE or S_WRITE_WAIT (guard at line 813), and arbiter state progression depends on external acknowledgements (sys_rsp_i.ack), so external actors can block delivery of the ALU result.
- undermined behavior: no, line 839 `when "000"  => alu_res <= arbiter.wdata;` -- alu_res is produced only by the amo_alu process (writers at lines 839-844) and there is no debug/test override in the RTL that substitutes a different payload at runtime.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| alu_res | neorv32_bus_amo_rmw | stores | 4 -> 839 `when "000"  => alu_res <= arbiter.wdata;` | CLOCKED_BY clk_i | verified |  | hit |
| sys_req_o | neorv32_bus_amo_rmw | exit port | 2 -> 812 `sys_req_o.addr  <= core_req_i.addr;` | DERIVES_FROM alu_res | occurrence only | no DERIVES_FROM record to 'alu_res' at occurrence 2 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): alu_res <- arbiter.cmd

## Concept: RVS store-conditional failure flag (sc_fail) used to modify the core's response

- confidentiality: yes-assumed, line 963 `core_rsp_o.ack  <= sys_rsp_i.ack or sc_fail;` via core_rsp_o.ack / core_rsp_o.data (output ports) -- sc_fail is latched in the sc_result process and is ORed into the core response outputs (lines 963-964) so the core observing its response can learn the flag and integrator may treat that as sensitive.
- integrity: yes-assumed, line 957 `sc_fail <= rvso and core_req_i.stb and core_req_i.rw and (not state(1));` via sc_result process (uses rvso and core_req_i signals) -- sc_fail is driven by the sc_result clocked logic at line 957 based on rvso and core_req_i signals (which come from the core), so external requesters (the core) can cause sc_fail to change and whether that writer is trusted depends on integration.
- availability: no, line 957 `sc_fail <= rvso and core_req_i.stb and core_req_i.rw and (not state(1));` -- sc_fail is updated only by the clocked sc_result process (assignment at line 957) and there is no external enable that can freeze its update beyond normal request sequencing, so it does not present an external-blocking availability condition in the RTL.
- undermined behavior: no, line 957 `sc_fail <= rvso and core_req_i.stb and core_req_i.rw and (not state(1));` -- sc_fail has a single clocked update path (sc_result at line 957) and the RTL contains no debug/test override to replace or bypass this flag.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| sc_fail | neorv32_bus_amo_rvs | stores | 3 -> 957 `sc_fail <= rvso and core_req_i.stb and core_req_i.rw and (not state(1));` | CLOCKED_BY clk_i | verified |  | not listed |
| core_rsp_o | neorv32_bus_amo_rvs | exit port | 4 -> 964 `core_rsp_o.data <= sys_rsp_i.data(31 downto 1) & (sys_rsp_i.data(0) or sc_fail);` | DERIVES_FROM sc_fail | occurrence only | no DERIVES_FROM record to 'sc_fail' at occurrence 4 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sc_fail <- core_req_i.rw, core_req_i.stb, rvso, state
