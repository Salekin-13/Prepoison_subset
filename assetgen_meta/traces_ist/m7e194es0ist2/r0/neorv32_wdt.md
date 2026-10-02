# neorv32_wdt

**Purpose (model):** A watchdog timer: it exposes control registers (enable, lock, strict, timeout) to a bus, samples a prescaled tick input, increments an internal counter while enabled, detects a timeout or access-fault condition and produces a hardware reset output (rstn_o), and records the reset cause; it also exports clkgen_en_o (copies enable).

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | writes that set the watchdog control registers (enable, lock, strict, timeout) |  | 5 / 5 |
| start | watchdog enable captured and used to start counting (sets cnt_started) |  | 4 / 4 |
| operate | prescaler tick drives cnt_inc and the counter increments while started |  | 5 / 5 |
| report | the reset-cause value is selected and stored (ext/dbg/timeout/access) |  | 4 / 4 |
| read out | bus read returns control fields and the stored reset cause on bus_rsp_o.data |  | 5 / 5 |
| lock | lock bit prevents software writes to the control registers and causes reset_force on write attempts when locked |  | 5 / 5 |
| reset | timeout reset: when cnt_started and cnt == ctrl.timeout a hw timeout is produced and rstn_o is driven (system reset) |  | 3 / 3 |
| reset | access-forced reset: illegal/unauthorised writes set reset_force, which (when strict and enabled) produces hw_rst_access and drives rstn_o |  | 4 / 4 |
| reset | watchdog internal reset of the counter: a correct-password bus write sets reset_wdt which clears cnt |  | 4 / 4 |

## Concept: Watchdog enable setting (ctrl.enable) — the register bit that enables or disables the watchdog and that the block exports to the clock-generator enable output


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.enable | neorv32_wdt | stores | 3 -> 94 `ctrl.enable  <= bus_req_i.data(ctrl_enable_c);` | CLOCKED_BY clk_i | verified |  | hit |
| clkgen_en_o | neorv32_wdt | exit port | 2 -> 140 `clkgen_en_o <= ctrl.enable;` | COPIES ctrl.enable | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Configuration lock (ctrl.lock) — the register bit that freezes the control registers and causes an access to become a force-reset if writes are attempted while locked


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.lock | neorv32_wdt | stores | 4 -> 95 `ctrl.lock    <= bus_req_i.data(ctrl_lock_c) and ctrl.enable;` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.lock <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb, ctrl.enable, ctrl.lock

## Concept: Strict-mode flag (ctrl.strict) — when set it causes invalid accesses (reset_force) to produce an immediate hardware reset


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.strict | neorv32_wdt | stores | 3 -> 96 `ctrl.strict  <= bus_req_i.data(ctrl_strict_c);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.strict <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Timeout configuration (ctrl.timeout) — the stored n-bit value that the counter is compared against to detect expiry


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.timeout | neorv32_wdt | stores | 3 -> 97 `ctrl.timeout <= bus_req_i.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c);` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.timeout <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Watchdog count (cnt) — the internal counter value that is incremented on prescaler ticks while started


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cnt | neorv32_wdt | stores | 3 -> 132 `cnt <= (others => '0');` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): cnt <- cnt_inc, ctrl.enable, reset_wdt

## Concept: Counting-active flag (cnt_started) — the stored boolean that enables counting once enabled and a prescaler tick arrives


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cnt_started | neorv32_wdt | stores | 4 -> 130 `cnt_started <= ctrl.enable and (cnt_started or prsc_tick);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): cnt_started <- ctrl.enable

## Concept: Timeout condition (cnt_timeout) — the combinational decision that cnt equals ctrl.timeout while started


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cnt_timeout | neorv32_wdt | computes | 2 -> 144 `cnt_timeout <= '1' when (cnt_started = '1') and (cnt = ctrl.timeout) else '0';` | CONSTRAINED_BY cnt | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): cnt_timeout <- cnt, cnt_started, ctrl.timeout

## Concept: Prescaler/timebase input (clkgen_i) — the external vector supplying the selected prescaler bit used as prsc_tick


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| clkgen_i | neorv32_wdt | sets | 2 -> 141 `prsc_tick   <= clkgen_i(clk_div4096_c);` | SOURCES prsc_tick | verified |  | not listed |

## Concept: Watchdog counter-clear trigger (reset_wdt) — the register set by a password-write that clears the internal counter


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| reset_wdt | neorv32_wdt | stores | 4 -> 103 `reset_wdt <= '1';` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): reset_wdt <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb

## Concept: Access-force flag (reset_force) — the register that records an illegal/unauthorised write and contributes to access-triggered reset


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| reset_force | neorv32_wdt | stores | 4 -> 99 `reset_force <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): reset_force <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb, ctrl.lock

## Concept: Hardware-timeout reset decision (hw_rst_timeout) — the stored decision that a timeout expiry should generate a hardware reset


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| hw_rst_timeout | neorv32_wdt | stores | 3 -> 155 `hw_rst_timeout <= ctrl.enable and cnt_timeout and prsc_tick;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): hw_rst_timeout <- cnt_timeout, ctrl.enable, prsc_tick

## Concept: Hardware-access reset decision (hw_rst_access) — the stored decision that a strict-mode access fault should generate a hardware reset


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| hw_rst_access | neorv32_wdt | stores | 3 -> 156 `hw_rst_access  <= ctrl.enable and ctrl.strict and reset_force;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): hw_rst_access <- ctrl.enable, ctrl.strict, reset_force

## Concept: System reset output (rstn_o) — the external reset driven low by the watchdog's hardware-reset decisions


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rstn_o | neorv32_wdt | exit port | 2 -> 161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);` | DERIVES_FROM hw_rst_access | verified |  | not listed |

## Concept: Stored reset cause (reset_cause) — the 2-bit register recording why the last reset occurred (external, debug, timeout, access)


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| reset_cause | neorv32_wdt | stores | 4 -> 172 `reset_cause <= "01";` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): reset_cause <- hw_rst_access, hw_rst_timeout, rstn_dbg_i
