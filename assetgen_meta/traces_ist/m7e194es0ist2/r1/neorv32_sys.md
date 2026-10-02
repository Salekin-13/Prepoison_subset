# neorv32_sys

**Purpose (model):** This file implements system reset sequencing and synchronization (neorv32_sys_reset) and a clock-enable generator (neorv32_sys_clock). The reset unit sequences/deasserts rstn_ext_o and rstn_sys_o from shift registers and synchronizes watchdog/debug reset inputs to xrstn_wdt_o and xrstn_ocd_o; the clock unit samples enable_i, increments internal counters when enabled, and produces divided clock-enable pulses on clk_en_o.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| reset | external reset asserted (rstn_ext_i='0') clears sequencer registers and forces reset outputs low |  | 10 / 10 |
| operate | delayed release of external reset: sreg_ext shifts ones and rstn_ext_o becomes the AND of sreg_ext |  | 2 / 2 |
| operate | delayed release of system reset: sreg_sys shifts ones unless gated-clear by watchdog or debug resets, and rstn_sys_o is the AND of sreg_sys |  | 5 / 5 |
| report | synchronized reporting of watchdog and debug reset inputs on xrstn_wdt_o and xrstn_ocd_o (sampled to clk_i) |  | 4 / 4 |
| reset | clock generator reset: rstn_i='0' clears en, cnt and cnt2 |  | 4 / 4 |
| configure | enable vector (enable_i) is collapsed to en (or_reduce_f) to enable/disable counting |  | 1 / 1 |
| operate | when enabled, cnt increments and cnt2 copies cnt; transitions produce one-cycle pulses on clk_en_o fields (cnt(bit) and not cnt2(bit)) |  | 13 / 13 |

## Concept: External reset release decision — the delayed deassertion of rstn_ext_o produced by a shift register


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| sreg_ext | neorv32_sys_reset | stores | 3 -> 51 `sreg_ext   <= sreg_ext(sreg_ext'left-1 downto 0) & '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| rstn_ext_o | neorv32_sys_reset | exit port | 3 -> 52 `rstn_ext_o <= and_reduce_f(sreg_ext);` | DERIVES_FROM sreg_ext | verified |  | not listed |

## Concept: System reset release decision — the deassertion of rstn_sys_o determined by sreg_sys and gated-clear by watchdog and debug reset inputs


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| sreg_sys | neorv32_sys_reset | stores | 4 -> 57 `sreg_sys <= sreg_sys(sreg_sys'left-1 downto 0) & '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| rstn_sys_o | neorv32_sys_reset | exit port | 3 -> 59 `rstn_sys_o <= and_reduce_f(sreg_sys);` | DERIVES_FROM sreg_sys | verified |  | not listed |
| rstn_wdt_i | neorv32_sys_reset | sets | 2 -> 54 `if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then` | GATES sreg_sys | verified |  | not listed |
| rstn_dbg_i | neorv32_sys_reset | sets | 2 -> 54 `if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then` | GATES sreg_sys | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sreg_sys <- rstn_dbg_i, rstn_wdt_i

## Concept: Synchronized watchdog reset output — the sampled (clocked) copy of rstn_wdt_i delivered on xrstn_wdt_o


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xrstn_wdt_o | neorv32_sys_reset | exit port | 3 -> 72 `xrstn_wdt_o <= rstn_wdt_i;` | COPIES rstn_wdt_i | verified |  | not listed |
| rstn_wdt_i | neorv32_sys_reset | sets | 3 -> 72 `xrstn_wdt_o <= rstn_wdt_i;` | CARRIES xrstn_wdt_o | verified |  | not listed |

## Concept: Synchronized debug/OCD reset output — the sampled (clocked) copy of rstn_dbg_i delivered on xrstn_ocd_o


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xrstn_ocd_o | neorv32_sys_reset | exit port | 3 -> 73 `xrstn_ocd_o <= rstn_dbg_i;` | COPIES rstn_dbg_i | verified |  | not listed |
| rstn_dbg_i | neorv32_sys_reset | sets | 3 -> 73 `xrstn_ocd_o <= rstn_dbg_i;` | CARRIES xrstn_ocd_o | verified |  | not listed |

## Concept: Clock-enable pulse generation — the divided clock-enable pulses driven on clk_en_o fields (per-bit pulses produced when cnt(bit) transitions)


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| clk_en_o | neorv32_sys_clock | exit port | 2 -> 140 `clk_en_o(clk_div2_c)    <= cnt(0)  and (not cnt2(0));` | GATED_BY cnt | verified |  | hit |
| cnt | neorv32_sys_clock | stores | 3 -> 131 `cnt <= std_ulogic_vector(unsigned(cnt) + 1);` | CLOCKED_BY clk_i | verified |  | not listed |
| cnt2 | neorv32_sys_clock | stores | 3 -> 135 `cnt2 <= cnt;` | CLOCKED_BY clk_i | verified |  | not listed |
| enable_i | neorv32_sys_clock | sets | 2 -> 129 `en <= or_reduce_f(enable_i);` | SOURCES en | verified |  | hit |
| en | neorv32_sys_clock | stores | 3 -> 129 `en <= or_reduce_f(enable_i);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): clk_en_o <- cnt, cnt2; cnt <- en
