# neorv32_wdt

**Purpose (model):** Watchdog timer with a bus-accessible control register set (enable/lock/strict/timeout), a prescaler input, a 24-bit counter that increments on prescaler ticks, and reset generation (timeout or forced-access). It exports an enable bit and a system reset output and reports registers / reset cause over the bus.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | Write the control registers (enable, lock, strict, timeout) from bus requests into the module's ctrl record |  | 8 / 8 |
| start | Password-protected software reset of the watchdog (write reset password to trigger reset_wdt) |  | 5 / 5 |
| operate | Prescaler-driven watchdog counting: prsc_tick enables cnt_inc/cnt_started; cnt increments and when cnt == ctrl.timeout cnt_timeout is asserted (leading to hw_rst_timeout) |  | 9 / 9 |
| report | Readback of control bits and reset cause on bus_rsp_o.data in response to bus reads |  | 6 / 6 |
| lock | Locking the control register: ctrl.lock freezes further control writes and causes a forced-reset flag on write attempts when locked |  | 6 / 6 |
| reset | Resets: (a) external system reset rstn_sys_i clears registers and counters; (b) hardware resets are produced from timeout or forced-access and driven out on rstn_o; reset_cause is recorded |  | 22 / 22 |

## Concept: Watchdog enable (ctrl.enable): the configuration bit that enables counting and participates in reset generation and export

- confidentiality: yes-assumed, line 140 `clkgen_en_o <= ctrl.enable;` via clkgen_en_o -- ctrl.enable is written by bus writes (line 94) and is exported on an output pin (clkgen_en_o at line 140) and read back on the bus (line 109), so external parties can observe its value.
- integrity: yes-rtl, line 94 `ctrl.enable  <= bus_req_i.data(ctrl_enable_c);` via bus_req_i -- A bus write directly updates ctrl.enable (line 94, gated by ctrl.lock at line 93) and that same bit gates counting (wdt_counter line 130) and reset generation (reset_generator line 155), so it can be changed by external writes while in use.
- availability: yes-rtl, line 131 `if (ctrl.enable = '0') or (reset_wdt = '1') then` via bus_req_i -- Clearing ctrl.enable stops or resets the counter (wdt_counter if branch at line 131) and bus writes can clear it (line 94), so an external actor can halt watchdog progress.
- undermined behavior: no, line 94 `ctrl.enable  <= bus_req_i.data(ctrl_enable_c);` -- ctrl.enable has a single intended driver (bus write at line 94 and reset at line 75) and no debug/test override or alternate driver is present in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.enable | neorv32_wdt | stores | 3 -> 94 `ctrl.enable  <= bus_req_i.data(ctrl_enable_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i | neorv32_wdt | sets | 6 -> 94 `ctrl.enable  <= bus_req_i.data(ctrl_enable_c);` | SOURCES ctrl.enable | occurrence only | no SOURCES record to 'ctrl.enable' at occurrence 6 | not listed |
| clkgen_en_o | neorv32_wdt | exit port | 2 -> 140 `clkgen_en_o <= ctrl.enable;` | COPIES ctrl.enable | verified |  | hit |
| bus_rsp_o | neorv32_wdt | exit port | 6 -> 109 `bus_rsp_o.data(ctrl_enable_c)                                <= ctrl.enable;` | COPIES ctrl.enable | occurrence only | no COPIES record to 'ctrl.enable' at occurrence 6 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Control lock (ctrl.lock): the configuration bit that freezes control writes and causes a forced-reset on write attempts when set

- confidentiality: no, line 110 `bus_rsp_o.data(ctrl_lock_c)                                  <= ctrl.lock;` via bus_rsp_o.data -- ctrl.lock is a configuration bit written by the bus and read back via the bus read path (bus_rsp_o.data at line 110) so it is not hidden from its writer.
- integrity: yes-rtl, line 95 `ctrl.lock    <= bus_req_i.data(ctrl_lock_c) and ctrl.enable;` via bus_req_i -- ctrl.lock is settable by bus writes (line 95) and is used to protect control writes (checked at line 93), so changing it via the bus directly affects protection without additional hardware enforcement.
- availability: yes-rtl, line 93 `if (ctrl.lock = '0') then` via bus_req_i -- When ctrl.lock = '1' the control write path is blocked (guard at line 93) and attempted writes assert reset_force (line 99), therefore setting the lock externally can deny further configuration updates.
- undermined behavior: no, line 95 `ctrl.lock    <= bus_req_i.data(ctrl_lock_c) and ctrl.enable;` -- ctrl.lock is driven only by the bus write at line 95 and reset at line 76; the RTL provides no alternate override or debug bypass for ctrl.lock.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.lock | neorv32_wdt | stores | 4 -> 95 `ctrl.lock    <= bus_req_i.data(ctrl_lock_c) and ctrl.enable;` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i | neorv32_wdt | sets | 7 -> 95 `ctrl.lock    <= bus_req_i.data(ctrl_lock_c) and ctrl.enable;` | GATES ctrl.lock | occurrence only | no GATES record to 'ctrl.lock' at occurrence 7 | not listed |
| bus_rsp_o | neorv32_wdt | exit port | 7 -> 110 `bus_rsp_o.data(ctrl_lock_c)                                  <= ctrl.lock;` | COPIES ctrl.lock | occurrence only | no COPIES record to 'ctrl.lock' at occurrence 7 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.lock <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb, ctrl.enable, ctrl.lock

## Concept: Strict mode (ctrl.strict): the configuration bit that enables forced-reset-on-invalid-access behavior

- confidentiality: no, line 112 `bus_rsp_o.data(ctrl_strict_c)                                <= ctrl.strict;` via bus_rsp_o.data -- ctrl.strict is written by bus accesses and read back on the bus (line 112) and is not masked or withheld by the RTL.
- integrity: yes-rtl, line 96 `ctrl.strict  <= bus_req_i.data(ctrl_strict_c);` via bus_req_i -- ctrl.strict is settable by bus writes (line 96) and directly participates in hw_rst_access computation (line 156), so external writes can change a signal that decides hardware resets.
- availability: yes-rtl, line 156 `hw_rst_access  <= ctrl.enable and ctrl.strict and reset_force;` via bus_req_i -- When ctrl.strict is '1' it contributes to hw_rst_access (line 156) and thus to rstn_o (line 161), enabling an external writer to cause or amplify reset behavior that can stop progress.
- undermined behavior: no, line 96 `ctrl.strict  <= bus_req_i.data(ctrl_strict_c);` -- ctrl.strict is driven only by intended bus writes (line 96) and reset (line 77) and there is no alternate override or debug substitution in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.strict | neorv32_wdt | stores | 3 -> 96 `ctrl.strict  <= bus_req_i.data(ctrl_strict_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i | neorv32_wdt | sets | 8 -> 96 `ctrl.strict  <= bus_req_i.data(ctrl_strict_c);` | SOURCES ctrl.strict | occurrence only | no SOURCES record to 'ctrl.strict' at occurrence 8 | not listed |
| bus_rsp_o | neorv32_wdt | exit port | 9 -> 112 `bus_rsp_o.data(ctrl_strict_c)                                <= ctrl.strict;` | COPIES ctrl.strict | occurrence only | no COPIES record to 'ctrl.strict' at occurrence 9 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.strict <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Timeout setting (ctrl.timeout): the configured counter value that determines when the watchdog times out

- confidentiality: no, line 113 `bus_rsp_o.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c) <= ctrl.timeout;` via bus_rsp_o.data -- ctrl.timeout is configured via bus writes and is read back on the bus (line 113), so the writer can observe it and it is not withheld by the RTL.
- integrity: yes-rtl, line 97 `ctrl.timeout <= bus_req_i.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c);` via bus_req_i -- ctrl.timeout is written by bus accesses (line 97) and is used in the timeout equality test (line 144) that gates hw_rst_timeout, so it can be altered by external writes while in use.
- availability: no, line 97 `ctrl.timeout <= bus_req_i.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c);` -- ctrl.timeout is only updated by intended bus writes (line 97); nothing in the RTL shows an external-controlled enable or stall that would freeze the module's ability to operate because of this field.
- undermined behavior: no, line 97 `ctrl.timeout <= bus_req_i.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c);` -- ctrl.timeout has the single intended driver (bus write at line 97 and reset at line 78) and there is no separate test/debug override present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.timeout | neorv32_wdt | stores | 3 -> 97 `ctrl.timeout <= bus_req_i.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i | neorv32_wdt | sets | 9 -> 97 `ctrl.timeout <= bus_req_i.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c);` | SOURCES ctrl.timeout | occurrence only | no SOURCES record to 'ctrl.timeout' at occurrence 9 | not listed |
| bus_rsp_o | neorv32_wdt | exit port | 10 -> 113 `bus_rsp_o.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c) <= ctrl.timeout;` | COPIES ctrl.timeout | occurrence only | no COPIES record to 'ctrl.timeout' at occurrence 10 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.timeout <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Watchdog counter value (cnt) and increment decision (cnt_inc): the runtime counter that is compared to ctrl.timeout

- confidentiality: yes-assumed, line 144 `cnt_timeout <= '1' when (cnt_started = '1') and (cnt = ctrl.timeout) else '0';` via rstn_o -- The counter value is compared to ctrl.timeout to produce cnt_timeout (line 144) which leads to hw_rst_timeout (line 155) and the external reset output rstn_o (line 161), so external observers can infer counter progress from reset timing.
- integrity: yes-rtl, line 132 `cnt <= (others => '0');` via bus_req_i -- cnt is cleared by the condition (ctrl.enable = '0') or reset_wdt = '1' (line 132) and both ctrl.enable and reset_wdt can be driven by bus writes (lines 94 and 103), so external inputs can alter cnt while it is in use.
- availability: yes-rtl, line 129 `cnt_inc     <= prsc_tick and cnt_started;` via clkgen_i / bus_req_i -- cnt only increments when prsc_tick and cnt_started are true (line 129), and an external clkgen_i input or clearing ctrl.enable via bus writes can stop cnt progression, preventing timeout.
- undermined behavior: no, line 134 `cnt <= std_ulogic_vector(unsigned(cnt) + 1);` -- cnt is updated only by the internal increment (line 134) and the reset branches (line 132); there is no separate override or alternate assignment path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cnt | neorv32_wdt | stores | 3 -> 132 `cnt <= (others => '0');` | CLOCKED_BY clk_i | verified |  | hit |
| cnt_inc | neorv32_wdt | computes | 3 -> 129 `cnt_inc     <= prsc_tick and cnt_started;` | GATED_BY prsc_tick | verified |  | not listed |
| reset_wdt | neorv32_wdt | sets | 4 -> 103 `reset_wdt <= '1';` | GATED_BY bus_req_i.data | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): cnt <- cnt_inc, ctrl.enable, reset_wdt; cnt_inc <- cnt_started, prsc_tick; reset_wdt <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb

## Concept: Counter started flag (cnt_started): whether the counter is running (enables counting progression)

- confidentiality: yes-assumed, line 130 `cnt_started <= ctrl.enable and (cnt_started or prsc_tick);` via rstn_o -- cnt_started enables counting progression (line 130) and so affects the timing of cnt_timeout and hw_rst_timeout (lines 144/155) which is visible externally via rstn_o (line 161), allowing inference of its value.
- integrity: yes-rtl, line 130 `cnt_started <= ctrl.enable and (cnt_started or prsc_tick);` via bus_req_i -- cnt_started is driven from ctrl.enable and prsc_tick (line 130) and ctrl.enable is writable by bus accesses (line 94), so external inputs can change whether the counter is started while the module is running.
- availability: yes-rtl, line 130 `cnt_started <= ctrl.enable and (cnt_started or prsc_tick);` via clkgen_i / bus_req_i -- cnt_started requires prsc_tick or ctrl.enable to become '1' (line 130), so stopping clkgen_i/prsc_tick or clearing ctrl.enable externally prevents the counter from starting and halts progress.
- undermined behavior: no, line 130 `cnt_started <= ctrl.enable and (cnt_started or prsc_tick);` -- cnt_started has a single register update (line 130) driven by ctrl.enable and prsc_tick; no alternate override or debug bypass exists in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cnt_started | neorv32_wdt | stores | 4 -> 130 `cnt_started <= ctrl.enable and (cnt_started or prsc_tick);` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl.enable | neorv32_wdt | sets | 6 -> 130 `cnt_started <= ctrl.enable and (cnt_started or prsc_tick);` | GATES cnt_started | edge, role unfit | GATES does not demonstrate 'sets' (mode None, storage edge) | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): cnt_started <- ctrl.enable; ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Prescaler tick input (clkgen_i -> prsc_tick): the external prescaler bit that produces prsc_tick used to drive counting

- confidentiality: no, line 141 `prsc_tick   <= clkgen_i(clk_div4096_c);` via clkgen_i -- prsc_tick is directly sourced from an external input (clkgen_i at line 141) and the RTL does not treat it as secret.
- integrity: yes-assumed, line 141 `prsc_tick   <= clkgen_i(clk_div4096_c);` via clkgen_i -- prsc_tick is driven by the external input clkgen_i (line 141) so its integrity depends on that external source and the RTL provides no internal protection.
- availability: yes-rtl, line 129 `cnt_inc     <= prsc_tick and cnt_started;` via clkgen_i -- Counting only advances when prsc_tick is true (cnt_inc uses prsc_tick at line 129), so disabling or stopping clkgen_i/prsc_tick externally prevents the watchdog from progressing.
- undermined behavior: no, line 141 `prsc_tick   <= clkgen_i(clk_div4096_c);` -- prsc_tick is derived only from the clkgen_i input at line 141 and there is no alternate test/debug override in the RTL to replace it.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| clkgen_i | neorv32_wdt | sets | 2 -> 141 `prsc_tick   <= clkgen_i(clk_div4096_c);` | SOURCES prsc_tick | verified |  | not listed |
| prsc_tick | neorv32_wdt | computes | 4 -> 141 `prsc_tick   <= clkgen_i(clk_div4096_c);` | DERIVES_FROM clkgen_i | verified |  | not listed |

## Concept: Password-protected WDT reset request (reset_wdt): the write-of-password decision that clears/affects counting

- confidentiality: yes-assumed, line 103 `reset_wdt <= '1';` via bus_req_i.data -- The RTL compares the written 32-bit word to reset_pwd_c (line 102) and asserts reset_wdt on equality (line 103); that assertion affects counter/reset behavior (line 131) which an external observer can detect, so the password decision reveals information to an external party.
- integrity: yes-rtl, line 103 `reset_wdt <= '1';` via bus_req_i.data -- A bus write that matches the password sets reset_wdt (line 103) and the RTL immediately uses reset_wdt to clear the counter (line 131), allowing external writes to change this decision while the watchdog is running.
- availability: yes-rtl, line 103 `reset_wdt <= '1';` via bus_req_i.data -- Repeatedly asserting reset_wdt via correct password writes (line 103) or clearing the counter prevents timeout (line 131) and can be used by an external agent to deny timeout-driven behavior.
- undermined behavior: no, line 103 `reset_wdt <= '1';` -- reset_wdt is driven only by the password-equality write path (lines 102-103) and reset logic (lines 79/87); there is no alternate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_wdt | sets | 10 -> 102 `if (bus_req_i.data(31 downto 0) = reset_pwd_c) then` | GATES reset_wdt | occurrence only | no GATES record to 'reset_wdt' at occurrence 10 | not listed |
| reset_wdt | neorv32_wdt | stores | 4 -> 103 `reset_wdt <= '1';` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): reset_wdt <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb

## Concept: Forced-reset flag from invalid/forbidden access (reset_force): the internal flag set on bad writes that can lead to hw_rst_access

- confidentiality: yes-assumed, line 99 `reset_force <= '1';` via bus_req_i -- reset_force is asserted on invalid writes (line 99 for writes to locked controls, line 105 for wrong password) and that feeds hw_rst_access (line 156) and rstn_o (line 161), allowing external observers to learn about invalid-access events.
- integrity: yes-rtl, line 99 `reset_force <= '1';` via bus_req_i -- Invalid or forbidden bus writes directly set reset_force (lines 99/105) and the RTL uses that flag to generate hw_rst_access (line 156), so external inputs can change a value that decides hardware resets.
- availability: yes-rtl, line 156 `hw_rst_access  <= ctrl.enable and ctrl.strict and reset_force;` via bus_req_i -- Setting reset_force results in hw_rst_access (line 156) which drives rstn_o low (line 161), enabling an external writer to force repeated resets and deny system progress.
- undermined behavior: no, line 99 `reset_force <= '1';` -- reset_force is driven only by the invalid-write paths (lines 99 and 105) and reset (lines 80/88); the RTL provides no separate test/debug override to bypass or substitute this behavior.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| reset_force | neorv32_wdt | stores | 4 -> 99 `reset_force <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| reset_force | neorv32_wdt | computes | 4 -> 99 `reset_force <= '1';` | GATED_BY ctrl.lock | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): reset_force <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: System reset decision and output (hw_rst_timeout / hw_rst_access -> rstn_o): the hardware reset signals and the exported rstn_o line

- confidentiality: yes-assumed, line 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` via rstn_o -- The external reset output rstn_o is driven from hw_rst_timeout and hw_rst_access (line 161) so observers outside the module directly learn when those internal reset decisions occur.
- integrity: yes-rtl, line 156 `hw_rst_access  <= ctrl.enable and ctrl.strict and reset_force;` via bus_req_i / clkgen_i -- hw_rst_timeout (line 155) and hw_rst_access (line 156) are computed from signals that external inputs can influence (ctrl.enable/timeout/prsc_tick and reset_force/ctrl.strict), and rstn_o is driven directly from them (line 161), so external inputs can change the reset output.
- availability: yes-rtl, line 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` via bus_req_i / clkgen_i -- External actions can assert hw_rst_access or hw_rst_timeout (lines 156/155) and thereby drive rstn_o low (line 161), enabling forced resets that prevent system progress.
- undermined behavior: no, line 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` -- rstn_o is computed only from hw_rst_timeout and hw_rst_access (line 161) and the RTL provides no alternate debug/test mode that substitutes a different source for the external reset output.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| hw_rst_timeout | neorv32_wdt | stores | 3 -> 155 `hw_rst_timeout <= ctrl.enable and cnt_timeout and prsc_tick;` | CLOCKED_BY clk_i | verified |  | not listed |
| hw_rst_access | neorv32_wdt | stores | 3 -> 156 `hw_rst_access  <= ctrl.enable and ctrl.strict and reset_force;` | CLOCKED_BY clk_i | verified |  | not listed |
| rstn_o | neorv32_wdt | exit port | 2 -> 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` | DERIVES_FROM hw_rst_access | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): hw_rst_timeout <- cnt_timeout, ctrl.enable, prsc_tick; hw_rst_access <- ctrl.enable, ctrl.strict, reset_force

## Concept: Reset cause register (reset_cause): recorded reason for the last reset (external debug reset, timeout, or access)

- confidentiality: yes-assumed, line 111 `bus_rsp_o.data(ctrl_rcause_hi_c downto ctrl_rcause_lo_c)     <= reset_cause;` via bus_rsp_o.data -- reset_cause is explicitly reported to the bus (line 111) and thus external agents can read the recorded reason for the last reset.
- integrity: yes-rtl, line 172 `reset_cause <= "01";` via rstn_dbg_i / bus_req_i -- reset_cause is written by external debug reset input (rstn_dbg_i at lines 171-172) and by hw-generated resets (lines 173-176) which external inputs can influence, so its value can be changed by outside-controlled events.
- availability: no, line 169 `reset_cause <= "00";` -- reset_cause is only a recorded status updated on resets (line 169 and lines 172/174/176) and nothing in the RTL requires other modules to wait on it for forward progress.
- undermined behavior: no, line 172 `reset_cause <= "01";` -- reset_cause is assigned only by its normal sources (external debug reset at line 172, hw_rst_timeout/hw_rst_access at lines 174/176 and reset at line 169) and there is no special test/debug override that substitutes a different assignment.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| reset_cause | neorv32_wdt | stores | 4 -> 172 `reset_cause <= "01";` | CLOCKED_BY clk_i | verified |  | hit |
| rstn_dbg_i | neorv32_wdt | sets | 2 -> 171 `if (rstn_dbg_i = '0') then` | GATES reset_cause | verified |  | not listed |
| hw_rst_timeout | neorv32_wdt | sets | 5 -> 173 `elsif (hw_rst_timeout = '1') then` | GATES reset_cause | edge, role unfit | GATES does not demonstrate 'sets' (mode None, storage edge) | not listed |
| bus_rsp_o | neorv32_wdt | exit port | 8 -> 111 `bus_rsp_o.data(ctrl_rcause_hi_c downto ctrl_rcause_lo_c)     <= reset_cause;` | COPIES reset_cause | occurrence only | no COPIES record to 'reset_cause' at occurrence 8 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): reset_cause <- hw_rst_access, hw_rst_timeout, rstn_dbg_i; hw_rst_timeout <- cnt_timeout, ctrl.enable, prsc_tick
