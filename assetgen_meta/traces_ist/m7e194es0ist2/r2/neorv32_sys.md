# neorv32_sys

**Purpose (model):** This file implements two system services: a reset/sequencer (neorv32_sys_reset) that synchronises an external reset, generates a timed deassertion (shift-registers) and forwards synchronized watchdog/debug resets; and a clock-control unit (neorv32_sys_clock) that latches an enable vector, runs a counter while enabled, and produces timed clk-enable pulses (clk_en_o) at several divide ratios.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| reset | external-reset assertion clears sequencer state and forces reset outputs low |  | 8 / 8 |
| operate | external-reset deassertion sequence: sreg_ext shifts ones and rstn_ext_o is derived from sreg_ext; sreg_sys shifts ones unless watchdog or debug reset forces it clear, and rstn_sys_o is derived from sreg_sys |  | 6 / 6 |
| operate | synchronise watchdog and debug reset inputs into synchronous outputs (captured on clk rising edge) |  | 5 / 5 |
| reset | clock generator reset: rstn_i clears en, cnt and cnt2 |  | 4 / 4 |
| configure | enable vector written into en (or_reduce_f(enable_i)) to start/stop counting |  | 2 / 2 |
| operate | when enabled, cnt increments on each clk edge and cnt2 follows cnt; these registers implement the timing state |  | 3 / 3 |
| report | clk_en_o outputs pulses derived from cnt and cnt2 bits (one-cycle pulse when a selected bit rises) |  | 8 / 8 |

## Concept: External-reset output and its deassertion sequence (the rstn_ext_o value produced after the external reset release)

- confidentiality: yes-assumed, line 52 `rstn_ext_o <= and_reduce_f(sreg_ext);` via rstn_ext_o -- rstn_ext_o is driven out of the module (rstn_ext_o <= and_reduce_f(sreg_ext) at line 52) so an external consumer can observe the deassertion sequence and the integrator may treat that signal as secret.
- integrity: yes-assumed, line 45 `sreg_ext   <= (others => '0');` via rstn_ext_i -- the external reset input rstn_ext_i forces sreg_ext to zero (sreg_ext <= (others => '0') at line 45) and thus can change rstn_ext_o, so whether that writer is trusted depends on integration.
- availability: yes-rtl, line 44 `if (rstn_ext_i = '0') then` via rstn_ext_i -- the process checks if rstn_ext_i = '0' (if (rstn_ext_i = '0') at line 44) and while asserted forces sreg_ext and rstn_ext_o low, allowing an external input to block or freeze the deassertion sequence.
- undermined behavior: no, line 52 `rstn_ext_o <= and_reduce_f(sreg_ext);` via sreg_ext -- rstn_ext_o has a single normal driver (rstn_ext_o <= and_reduce_f(sreg_ext) at line 52) and there is no debug/test override or alternate assignment in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rstn_ext_o | neorv32_sys_reset | exit port | 3 -> 52 `rstn_ext_o <= and_reduce_f(sreg_ext);` | DERIVES_FROM sreg_ext | verified |  | not listed |
| sreg_ext | neorv32_sys_reset | stores | 3 -> 51 `sreg_ext   <= sreg_ext(sreg_ext'left-1 downto 0) & '1';` | CLOCKED_BY clk_i | verified |  | not listed |

## Concept: System-reset value/state that this block produces for the core/peripherals (rstn_sys_o) and the shift-register that implements it

- confidentiality: yes-assumed, line 59 `rstn_sys_o <= and_reduce_f(sreg_sys);` via rstn_sys_o -- rstn_sys_o is driven out of the module from the shift-register (rstn_sys_o <= and_reduce_f(sreg_sys) at line 59) so external observers can see the system-reset state and the integrator may treat it as secret.
- integrity: yes-rtl, line 55 `sreg_sys <= (others => '0');` via rstn_wdt_i, rstn_dbg_i -- the inputs rstn_wdt_i or rstn_dbg_i directly clear the shift-register (sreg_sys <= (others => '0') at line 55) without any locking, so those external inputs can change the system-reset value while it is in use.
- availability: yes-rtl, line 54 `if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then` via rstn_wdt_i, rstn_dbg_i -- the condition if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') (line 54) selects clearing of sreg_sys and thus external watchdog or debug inputs can prevent the reset-deassertion progression and block availability.
- undermined behavior: yes-rtl, line 54 `if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then` via rstn_wdt_i, rstn_dbg_i -- the guard (rstn_wdt_i = '0') or (rstn_dbg_i = '0') at line 54 selects an alternate assignment (clear sreg_sys at line 55), i.e. watchdog or debug inputs bypass the normal shift-based deassertion.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rstn_sys_o | neorv32_sys_reset | exit port | 3 -> 59 `rstn_sys_o <= and_reduce_f(sreg_sys);` | DERIVES_FROM sreg_sys | verified |  | not listed |
| sreg_sys | neorv32_sys_reset | stores | 4 -> 57 `sreg_sys <= sreg_sys(sreg_sys'left-1 downto 0) & '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| rstn_wdt_i | neorv32_sys_reset | sets | 2 -> 54 `if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then` | GATES sreg_sys | verified |  | not listed |
| rstn_dbg_i | neorv32_sys_reset | sets | 2 -> 54 `if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then` | GATES sreg_sys | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sreg_sys <- rstn_dbg_i, rstn_wdt_i

## Concept: Synchronized watchdog-reset output (xrstn_wdt_o) delivered to consumers

- confidentiality: yes-assumed, line 72 `xrstn_wdt_o <= rstn_wdt_i;` via xrstn_wdt_o -- xrstn_wdt_o is driven out of the module by a clocked copy from the input (xrstn_wdt_o <= rstn_wdt_i at line 72), so an external consumer can observe this value and the integrator may treat it as secret.
- integrity: yes-assumed, line 72 `xrstn_wdt_o <= rstn_wdt_i;` via rstn_wdt_i -- the output is directly driven from the input rstn_wdt_i on the clock (xrstn_wdt_o <= rstn_wdt_i at line 72), so an external writer can change the value and whether that writer is trusted depends on integration.
- availability: yes-rtl, line 69 `xrstn_wdt_o <= '0';` via rstn_ext_i -- the synchronizer forces xrstn_wdt_o low during external reset (xrstn_wdt_o <= '0' when rstn_ext_i = '0' at line 69), so an external reset input can block or force this output and affect availability.
- undermined behavior: no, line 72 `xrstn_wdt_o <= rstn_wdt_i;` via rstn_wdt_i -- the output is a simple clocked copy of rstn_wdt_i (line 72) with no alternate debug/test override path present in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xrstn_wdt_o | neorv32_sys_reset | exit port | 3 -> 72 `xrstn_wdt_o <= rstn_wdt_i;` | COPIES rstn_wdt_i | verified |  | not listed |
| rstn_wdt_i | neorv32_sys_reset | sets | 3 -> 72 `xrstn_wdt_o <= rstn_wdt_i;` | CARRIES xrstn_wdt_o | verified |  | not listed |

## Concept: Synchronized on-chip-debug/OCD-reset output (xrstn_ocd_o) delivered to consumers

- confidentiality: yes-assumed, line 73 `xrstn_ocd_o <= rstn_dbg_i;` via xrstn_ocd_o -- xrstn_ocd_o is driven out of the module by a clocked copy from the debug input (xrstn_ocd_o <= rstn_dbg_i at line 73), so external consumers can observe the debug-reset signal and the integrator may treat it as secret.
- integrity: yes-assumed, line 73 `xrstn_ocd_o <= rstn_dbg_i;` via rstn_dbg_i -- the output is directly driven from the input rstn_dbg_i on the clock (xrstn_ocd_o <= rstn_dbg_i at line 73), so an external writer can change the value and whether that writer is trusted depends on integration.
- availability: yes-rtl, line 70 `xrstn_ocd_o <= '0';` via rstn_ext_i -- the synchronizer forces xrstn_ocd_o low during external reset (xrstn_ocd_o <= '0' when rstn_ext_i = '0' at line 70), so external reset can block or force this output and affect availability.
- undermined behavior: no, line 73 `xrstn_ocd_o <= rstn_dbg_i;` via rstn_dbg_i -- the output is implemented as a straight clocked copy of rstn_dbg_i (line 73) with no alternate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xrstn_ocd_o | neorv32_sys_reset | exit port | 3 -> 73 `xrstn_ocd_o <= rstn_dbg_i;` | COPIES rstn_dbg_i | verified |  | not listed |
| rstn_dbg_i | neorv32_sys_reset | sets | 3 -> 73 `xrstn_ocd_o <= rstn_dbg_i;` | CARRIES xrstn_ocd_o | verified |  | not listed |

## Concept: Clock-enable pulses produced on clk_en_o (the vector of divide-ratio pulses used to gate clocks)

- confidentiality: yes-assumed, line 140 `clk_en_o(clk_div2_c)    <= cnt(0)  and (not cnt2(0));` via clk_en_o -- clk_en_o signals are produced internally from en/cnt/cnt2 and driven out of the module (e.g. line 140), so external observers can see clock-enable pulses and the integrator may treat them as revealing internal timing/state.
- integrity: yes-rtl, line 129 `en <= or_reduce_f(enable_i);` via enable_i -- en is derived from the external enable_i (en <= or_reduce_f(enable_i) at line 129) and that signal gates counting (cnt updates at line 131), so an external writer can change enable_i at any time and thereby alter clk_en_o while pulses are being used.
- availability: yes-rtl, line 131 `cnt <= std_ulogic_vector(unsigned(cnt) + 1);` via enable_i -- cnt only increments when en = '1' (guard at line 131), and en is driven from enable_i, so an external enable input can stop pulse generation and prevent progress of downstream consumers.
- undermined behavior: no, line 140 `clk_en_o(clk_div2_c)    <= cnt(0)  and (not cnt2(0));` via cnt -- clk_en_o entries are driven solely from the counted state (cnt/cnt2) via the assignments at lines 140-147 and there is no separate debug/test override bypass in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| clk_en_o | neorv32_sys_clock | exit port | 2 -> 140 `clk_en_o(clk_div2_c)    <= cnt(0)  and (not cnt2(0));` | GATED_BY cnt | verified |  | hit |
| cnt | neorv32_sys_clock | stores | 3 -> 131 `cnt <= std_ulogic_vector(unsigned(cnt) + 1);` | CLOCKED_BY clk_i | verified |  | not listed |
| cnt2 | neorv32_sys_clock | stores | 3 -> 135 `cnt2 <= cnt;` | CLOCKED_BY clk_i | verified |  | not listed |
| enable_i | neorv32_sys_clock | sets | 2 -> 129 `en <= or_reduce_f(enable_i);` | SOURCES en | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): clk_en_o <- cnt, cnt2; cnt <- en
