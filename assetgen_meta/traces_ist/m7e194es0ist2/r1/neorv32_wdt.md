# neorv32_wdt

**Purpose (model):** The watchdog block accepts bus configuration and reload requests, runs a prescaled counter when enabled, compares the counter against a programmable timeout and, on timeout or forced-access conditions, asserts a hardware reset output; it also reports control fields and the reset cause on the bus and exports a clock-enable signal.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | Control register fields (enable, lock, strict, timeout) written into internal ctrl record by bus writes to the control address |  | 6 / 6 |
| start | Watchdog reload / clear request (reset_wdt) set by a bus write of the correct password |  | 4 / 4 |
| operate | Prescaler tick (from clkgen_i) drives cnt_started and increments cnt; when cnt equals ctrl.timeout (cnt_timeout) hw_rst_timeout is produced |  | 9 / 9 |
| read out | Readback of control fields and reset cause returned on bus reads into bus_rsp_o.data |  | 6 / 6 |
| lock | The lock bit freezes control writes (attempts to write while locked cause reset_force) |  | 4 / 4 |
| reset | System reset output rstn_o asserted when hw_rst_timeout or hw_rst_access are set; reset_cause captured accordingly |  | 7 / 7 |

## Concept: Watchdog enable configuration (whether the WDT is enabled and the exported clock-enable)

- confidentiality: yes-assumed, line 140 `clkgen_en_o <= ctrl.enable;` via clkgen_en_o -- ctrl.enable is copied to the external clkgen_en_o output (line 140) and is also returned on bus reads (line 109), so an outside observer can learn its value.
- integrity: yes-rtl, line 94 `ctrl.enable  <= bus_req_i.data(ctrl_enable_c);` via bus_req_i.data -- ctrl.enable is written directly from bus_req_i.data at line 94 under the bus write path (guarded only by ctrl.lock), so an external bus master can change it while the WDT is operating and affect counting (see cnt_started/cnt updates lines 129-135).
- availability: yes-rtl, line 131 `if (ctrl.enable = '0') or (reset_wdt = '1') then` via bus_req_i -- Clearing ctrl.enable (via a bus write to the enable bit) causes the counter to be reset in wdt_counter (line 131), so an external master can stop counting and prevent timeouts.
- undermined behavior: no, line 94 `ctrl.enable  <= bus_req_i.data(ctrl_enable_c);` via bus_req_i.data -- ctrl.enable is driven only by the bus write (line 94) and reset (line 75); there is no debug/test override path that substitutes a different assignment.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.enable | neorv32_wdt | stores | 3 -> 94 `ctrl.enable  <= bus_req_i.data(ctrl_enable_c);` | CLOCKED_BY clk_i | verified |  | hit |
| clkgen_en_o | neorv32_wdt | exit port | 2 -> 140 `clkgen_en_o <= ctrl.enable;` | COPIES ctrl.enable | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Configuration lock (whether control fields are frozen against writes)

- confidentiality: yes-assumed, line 110 `bus_rsp_o.data(ctrl_lock_c)                                  <= ctrl.lock;` via bus_rsp_o.data -- ctrl.lock is returned on bus reads (line 110), so external observers can learn whether controls are locked.
- integrity: yes-rtl, line 95 `ctrl.lock    <= bus_req_i.data(ctrl_lock_c) and ctrl.enable;` via bus_req_i.data -- ctrl.lock is written from bus_req_i.data at line 95 and it itself gates whether subsequent control writes are accepted (line 93), so an external writer can set the protection and thereby change integrity of control fields.
- availability: yes-rtl, line 93 `if (ctrl.lock = '0') then` via bus_req_i -- If ctrl.lock is set to '1' the bus-access path rejects configuration writes and sets reset_force instead (lines 93/99), so an external actor that sets lock can prevent further reconfiguration until reset.
- undermined behavior: no, line 95 `ctrl.lock    <= bus_req_i.data(ctrl_lock_c) and ctrl.enable;` via bus_req_i.data -- ctrl.lock has a single intended driver (the bus write at line 95 and reset at line 76); there is no alternate debug/test override that changes it.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.lock | neorv32_wdt | stores | 4 -> 95 `ctrl.lock    <= bus_req_i.data(ctrl_lock_c) and ctrl.enable;` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.lock <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb, ctrl.enable, ctrl.lock

## Concept: Timeout setting (the programmable timeout value the counter is compared against)

- confidentiality: yes-assumed, line 113 `bus_rsp_o.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c) <= ctrl.timeout;` via bus_rsp_o.data -- ctrl.timeout is returned on bus reads (line 113), so an outside observer can learn the configured timeout value.
- integrity: yes-rtl, line 97 `ctrl.timeout <= bus_req_i.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c);` via bus_req_i.data -- ctrl.timeout is written directly from bus_req_i.data at line 97 and that write can occur while the counter runs (the comparator is at line 144), so external writes can change when a timeout will occur.
- availability: yes-rtl, line 97 `ctrl.timeout <= bus_req_i.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c);` via bus_req_i.data -- An external master can write ctrl.timeout (line 97) to values that either prevent timeouts or cause an immediate cnt = ctrl.timeout and hw_rst_timeout (lines 144/155), enabling external interference with reset availability.
- undermined behavior: no, line 97 `ctrl.timeout <= bus_req_i.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c);` via bus_req_i.data -- ctrl.timeout is driven only by the bus write (line 97) and reset (line 78); there is no alternate debug/test override for the timeout field.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.timeout | neorv32_wdt | stores | 3 -> 97 `ctrl.timeout <= bus_req_i.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c);` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.timeout <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Strict mode configuration (whether forced-access generates a hardware reset)

- confidentiality: yes-assumed, line 112 `bus_rsp_o.data(ctrl_strict_c)                                <= ctrl.strict;` via bus_rsp_o.data -- ctrl.strict is readable on bus reads (line 112), so external observers can learn whether strict mode is enabled.
- integrity: yes-rtl, line 96 `ctrl.strict  <= bus_req_i.data(ctrl_strict_c);` via bus_req_i.data -- ctrl.strict is written from bus_req_i.data at line 96 and is used to compute hw_rst_access (line 156), so external writes can change whether forced-access escalates to a reset.
- availability: yes-rtl, line 156 `hw_rst_access  <= ctrl.enable and ctrl.strict and reset_force;` via bus_req_i -- Changing ctrl.strict (via bus writes at line 96) controls whether reset_force escalates to hw_rst_access (line 156) and thus whether rstn_o will be asserted, enabling an external actor to affect system availability.
- undermined behavior: no, line 96 `ctrl.strict  <= bus_req_i.data(ctrl_strict_c);` via bus_req_i.data -- ctrl.strict is only driven by the bus write (line 96) and reset (line 77); there is no debug/test bypass that substitutes a different assignment.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.strict | neorv32_wdt | stores | 3 -> 96 `ctrl.strict  <= bus_req_i.data(ctrl_strict_c);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.strict <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Watchdog reload request (the reload/clear signal that resets the WDT counter)

- confidentiality: yes-assumed, line 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` via rstn_o -- reset_wdt clears the internal counter (line 131) which alters cnt_timeout and hw_rst_timeout (line 155) and thus the external rstn_o output (line 161), so an outside observer can infer reload events and whether a password-matching write occurred.
- integrity: yes-rtl, line 103 `reset_wdt <= '1';` via bus_req_i.data -- reset_wdt is asserted by a bus write when the bus data equals the hard-coded reset_pwd_c (line 103), so an external master that supplies that data can change the reload state while the WDT runs.
- availability: yes-rtl, line 103 `reset_wdt <= '1';` via bus_req_i.data -- An external master that can provide the matching password (line 103) can repeatedly assert reset_wdt and continuously clear the counter (line 131), preventing timeouts and affecting availability of reset behavior.
- undermined behavior: no, line 103 `reset_wdt <= '1';` via bus_req_i.data -- reset_wdt has a single intended driver (the passworded bus write at line 103 and reset/clear at lines 79/87) and there is no debug/test bypass.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| reset_wdt | neorv32_wdt | stores | 4 -> 103 `reset_wdt <= '1';` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): reset_wdt <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb

## Concept: Forced-reset indicator (reset_force) set on disallowed or incorrect bus accesses

- confidentiality: yes-assumed, line 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` via rstn_o -- reset_force can cause hw_rst_access (line 156) and a system reset (rstn_o at line 161) and later reset_cause='11' (line 176) readable on the bus (line 111), so external observers can learn when forced-reset conditions occurred.
- integrity: yes-rtl, line 99 `reset_force <= '1';` via bus_req_i -- reset_force is set directly by the bus-access logic on disallowed or incorrect writes (lines 99/105), so an external master can cause the forced-reset indicator to change.
- availability: yes-rtl, line 99 `reset_force <= '1';` via bus_req_i -- An external master can trigger reset_force (lines 99/105) which can be escalated (line 156) to assert rstn_o (line 161) and thereby cause system resets, enabling denial-of-service.
- undermined behavior: no, line 99 `reset_force <= '1';` via bus_req_i -- reset_force is driven only by the bus-access branches (lines 99/105) and reset; there is no alternate debug/test override path that substitutes a different assignment.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| reset_force | neorv32_wdt | stores | 5 -> 105 `reset_force <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): reset_force <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Watchdog counter state (current counter value used to detect timeout)

- confidentiality: yes-assumed, line 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` via rstn_o -- cnt equality to ctrl.timeout produces cnt_timeout (line 144) and hw_rst_timeout (line 155) which change the external rstn_o (line 161), so outside observers can infer the counter's progress/timing.
- integrity: yes-rtl, line 134 `cnt <= std_ulogic_vector(unsigned(cnt) + 1);` via prsc_tick (clkgen_i) and reset_wdt (bus_req_i) -- cnt is incremented at line 134 under cnt_inc and cleared by reset_wdt (line 131); external-influenced signals (prsc_tick from clkgen_i and reset_wdt from bus writes) can therefore change cnt while it is in use.
- availability: yes-rtl, line 129 `cnt_inc     <= prsc_tick and cnt_started;` via clkgen_i (prsc_tick) -- cnt_inc depends on prsc_tick (line 129) which is derived from clkgen_i (line 141), so if the external clock source stops or is manipulated the counter will not advance and timeouts are prevented.
- undermined behavior: no, line 134 `cnt <= std_ulogic_vector(unsigned(cnt) + 1);` via cnt_inc -- cnt's drivers are the intended increment (line 134) and clears (line 131); there is no debug/test mode that substitutes a different driver for cnt.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cnt | neorv32_wdt | stores | 4 -> 134 `cnt <= std_ulogic_vector(unsigned(cnt) + 1);` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): cnt <- cnt_inc, ctrl.enable, reset_wdt

## Concept: Counter-started flag (whether the watchdog counter is active)

- confidentiality: yes-assumed, line 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` via rstn_o -- cnt_started gates counting (line 129) and thereby affects cnt_timeout and hw_rst_timeout (line 155) and the external rstn_o (line 161), so external observers can infer whether the counter is active.
- integrity: yes-rtl, line 130 `cnt_started <= ctrl.enable and (cnt_started or prsc_tick);` via ctrl.enable (bus_req_i) and prsc_tick (clkgen_i) -- cnt_started is driven from ctrl.enable and prsc_tick at line 130; both are influenced by external inputs, so outsiders can change whether the counter is active while it is used.
- availability: yes-rtl, line 130 `cnt_started <= ctrl.enable and (cnt_started or prsc_tick);` via clkgen_i / bus_req_i -- External inputs can prevent cnt_started from becoming '1' by clearing ctrl.enable (bus write) or by stopping prsc_tick (clkgen_i), halting counter activity (line 130) and affecting availability.
- undermined behavior: no, line 130 `cnt_started <= ctrl.enable and (cnt_started or prsc_tick);` via cnt_started update -- cnt_started is driven only by its update expression (line 130) and reset; there is no debug/test bypass that selects an alternate assignment.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cnt_started | neorv32_wdt | stores | 4 -> 130 `cnt_started <= ctrl.enable and (cnt_started or prsc_tick);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): cnt_started <- ctrl.enable

## Concept: Reset cause register (the recorded source of the last reset)

- confidentiality: yes-assumed, line 111 `bus_rsp_o.data(ctrl_rcause_hi_c downto ctrl_rcause_lo_c)     <= reset_cause;` via bus_rsp_o.data -- reset_cause is returned on the bus (line 111), so external observers can learn the recorded reason for the last reset.
- integrity: yes-rtl, line 171 `if (rstn_dbg_i = '0') then` via rstn_dbg_i -- reset_cause is written from external rstn_dbg_i (lines 171-172) and from internal hw_rst_timeout/hw_rst_access (lines 173-176), so external inputs can change the recorded cause.
- availability: no, line 169 `reset_cause <= "00";` via rstn_ext_i -- reset_cause is a reporting register updated by reset and internal flags (lines 169,172,174,176) and nothing in the RTL depends on this register for forward progress, so its value does not block module progress.
- undermined behavior: yes-rtl, line 171 `if (rstn_dbg_i = '0') then` via rstn_dbg_i -- The debug input rstn_dbg_i = '0' forces reset_cause to the debug code (line 172), selecting a different assignment path that overrides other conditions.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| reset_cause | neorv32_wdt | stores | 4 -> 172 `reset_cause <= "01";` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): reset_cause <- hw_rst_access, hw_rst_timeout, rstn_dbg_i

## Concept: System reset output (the rstn_o value derived from internal reset flags)

- confidentiality: yes-assumed, line 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` via rstn_o -- rstn_o is an externally visible output (line 161) so outside components can observe the reset assertion and its timing.
- integrity: yes-rtl, line 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` via hw_rst_timeout/hw_rst_access -- rstn_o is computed directly from hw_rst_timeout and hw_rst_access (line 161) which are driven by signals that external inputs can influence (lines 155/156), so outside actors can cause or prevent system resets.
- availability: yes-rtl, line 156 `hw_rst_access  <= ctrl.enable and ctrl.strict and reset_force;` via bus_req_i / clkgen_i -- External inputs (e.g. bus writes that set reset_force or reset_wdt, and the clkgen_i prescaler that affects cnt_timeout) can assert hw_rst_access or hw_rst_timeout (lines 155/156) and thereby assert rstn_o (line 161), enabling forced resets and denial-of-service.
- undermined behavior: no, line 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` -- rstn_o is driven by the single combinational expression not (hw_rst_timeout or hw_rst_access) (line 161); there is no special debug/test mode that substitutes a different source.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rstn_o | neorv32_wdt | exit port | 2 -> 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` | DERIVES_FROM hw_rst_access | verified |  | not listed |
| hw_rst_timeout | neorv32_wdt | stores | 3 -> 155 `hw_rst_timeout <= ctrl.enable and cnt_timeout and prsc_tick;` | CLOCKED_BY clk_i | verified |  | not listed |
| hw_rst_access | neorv32_wdt | stores | 3 -> 156 `hw_rst_access  <= ctrl.enable and ctrl.strict and reset_force;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): hw_rst_timeout <- cnt_timeout, ctrl.enable, prsc_tick; hw_rst_access <- ctrl.enable, ctrl.strict, reset_force
