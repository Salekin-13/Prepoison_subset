# neorv32_sys

**Purpose (model):** System reset sequencing/synchronization and clock-enable generation. The reset unit (neorv32_sys_reset) sequences and synchronizes external, watchdog and debug reset inputs into stretched/synchronized reset outputs (rstn_ext_o, rstn_sys_o, xrstn_wdt_o, xrstn_ocd_o). The clock unit (neorv32_sys_clock) derives an enable from enable_i, counts while enabled, and emits divided clock-enable pulses on clk_en_o.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| reset | clear reset sequencing registers and force reset outputs while external system reset is asserted |  | 12 / 12 |
| operate | external-reset release sequencing: shift sreg_ext and derive rstn_ext_o when sreg_ext is filled |  | 2 / 2 |
| operate | system-reset sequencing: update sreg_sys on each clock edge unless watchdog or debug reset hold it asserted, and drive rstn_sys_o from sreg_sys |  | 6 / 6 |
| operate | synchronize watchdog and debug reset inputs onto clk_i and present them as xrstn_wdt_o and xrstn_ocd_o |  | 6 / 6 |
| configure | clock-enable configuration: reduce enable_i into en (the run/stop setting for the ticker) |  | 2 / 2 |
| operate | clock-enable generation: when en='1' increment cnt, copy cnt into cnt2, and produce clk_en_o pulses from cnt and cnt2 (clk_div2..clk_div4096) |  | 11 / 11 |

## Concept: System reset release decision (value delivered on rstn_sys_o) that determines whether the system domain is held in reset or released

- confidentiality: yes-assumed, line 59 `rstn_sys_o <= and_reduce_f(sreg_sys);` via rstn_sys_o (output port) -- rstn_sys_o is driven to an external output (declared line 27 and assigned line 59) so external observers can read the system-reset state and thus learn this value.
- integrity: yes-rtl, line 55 `sreg_sys <= (others => '0');` via rstn_wdt_i / rstn_dbg_i (inputs gating sreg_sys) -- sreg_sys is forced to all zeros when (rstn_wdt_i='0') or (rstn_dbg_i='0') (guard at line 54, assignment at line 55) and that state is propagated to rstn_sys_o at line 59, so external inputs can change the system-reset decision while it is in use.
- availability: yes-rtl, line 54 `if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then` via rstn_wdt_i / rstn_dbg_i (inputs) -- the condition if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') at line 54 forces sreg_sys to zeros (line 55) and therefore keeps rstn_sys_o low, allowing external inputs to block or hold system release.
- undermined behavior: yes-rtl, line 54 `if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then` via rstn_dbg_i (debug/OCD reset) -- the debug/OCD reset input rstn_dbg_i asserted ('0') is a dedicated override (guard at line 54) that forces sreg_sys to zeros (line 55) and thus bypasses normal shift-to-release behavior.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rstn_sys_o | neorv32_sys_reset | exit port | 3 -> 59 `rstn_sys_o <= and_reduce_f(sreg_sys);` | DERIVES_FROM sreg_sys | verified |  | not listed |
| sreg_sys | neorv32_sys_reset | stores | 4 -> 57 `sreg_sys <= sreg_sys(sreg_sys'left-1 downto 0) & '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| rstn_wdt_i | neorv32_sys_reset | sets | 2 -> 54 `if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then` | GATES sreg_sys | verified |  | not listed |
| rstn_dbg_i | neorv32_sys_reset | sets | 2 -> 54 `if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then` | GATES sreg_sys | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sreg_sys <- rstn_dbg_i, rstn_wdt_i

## Concept: External reset release decision (value delivered on rstn_ext_o) that controls external-domain reset release

- confidentiality: yes-assumed, line 52 `rstn_ext_o <= and_reduce_f(sreg_ext);` via rstn_ext_o (output port) -- rstn_ext_o is driven to an external output (declared line 26 and assigned line 52) so external observers can read the external-reset release state.
- integrity: yes-assumed, line 46 `rstn_ext_o <= '0';` via rstn_ext_i (external reset input) -- rstn_ext_i='0' (guard at line 44) forces sreg_ext and rstn_ext_o to '0' (lines 45-46), so an external input controls and can change the external-reset release value and its integrity depends on integration trust.
- availability: yes-rtl, line 44 `if (rstn_ext_i = '0') then` via rstn_ext_i (external reset input) -- the asynchronous reset condition if (rstn_ext_i = '0') at line 44 holds sreg_ext at zeros (line 45) and rstn_ext_o low (line 46), allowing an external input to block external-domain release.
- undermined behavior: no, line 52 `rstn_ext_o <= and_reduce_f(sreg_ext);` via sreg_ext -- rstn_ext_o is driven only by the sreg_ext clocked assignment (line 52) and reset (line 46); there is no separate debug/test override or bypass in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rstn_ext_o | neorv32_sys_reset | exit port | 3 -> 52 `rstn_ext_o <= and_reduce_f(sreg_ext);` | DERIVES_FROM sreg_ext | verified |  | not listed |
| sreg_ext | neorv32_sys_reset | stores | 3 -> 51 `sreg_ext   <= sreg_ext(sreg_ext'left-1 downto 0) & '1';` | CLOCKED_BY clk_i | verified |  | not listed |

## Concept: Synchronized watchdog reset output (xrstn_wdt_o) delivered to consumers clocked by clk_i

- confidentiality: yes-assumed, line 72 `xrstn_wdt_o <= rstn_wdt_i;` via xrstn_wdt_o (output port) -- xrstn_wdt_o is driven to an external output (declared line 29 and assigned line 72) so external consumers can observe the sampled watchdog-reset value.
- integrity: yes-assumed, line 72 `xrstn_wdt_o <= rstn_wdt_i;` via rstn_wdt_i (input) -- xrstn_wdt_o is a registered copy of rstn_wdt_i (assignment at line 72), so the external rstn_wdt_i input determines the output and its trust depends on integration.
- availability: no, line 72 `xrstn_wdt_o <= rstn_wdt_i;` via rstn_wdt_i -- xrstn_wdt_o is updated each rising_edge(clk_i) by sampling rstn_wdt_i (line 72) except during the asynchronous reset branch (line 68), and there is no other external-controlled enable/stall that blocks updates (global reset excluded).
- undermined behavior: no, line 72 `xrstn_wdt_o <= rstn_wdt_i;` via rstn_wdt_i -- xrstn_wdt_o is driven only by the clocked copy from rstn_wdt_i (line 72) and reset (line 69); no alternate/test override is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xrstn_wdt_o | neorv32_sys_reset | exit port | 3 -> 72 `xrstn_wdt_o <= rstn_wdt_i;` | COPIES rstn_wdt_i | verified |  | not listed |
| rstn_wdt_i | neorv32_sys_reset | sets | 3 -> 72 `xrstn_wdt_o <= rstn_wdt_i;` | CARRIES xrstn_wdt_o | verified |  | not listed |

## Concept: Synchronized debug/OCD reset output (xrstn_ocd_o) delivered to consumers clocked by clk_i

- confidentiality: yes-assumed, line 73 `xrstn_ocd_o <= rstn_dbg_i;` via xrstn_ocd_o (output port) -- xrstn_ocd_o is driven to an external output (declared line 30 and assigned line 73) so external consumers can observe the debug/OCD reset state.
- integrity: yes-assumed, line 73 `xrstn_ocd_o <= rstn_dbg_i;` via rstn_dbg_i (input) -- xrstn_ocd_o is a registered copy of rstn_dbg_i (assignment at line 73), so the external rstn_dbg_i input determines the output and its trust depends on integration.
- availability: no, line 73 `xrstn_ocd_o <= rstn_dbg_i;` via rstn_dbg_i -- xrstn_ocd_o is updated each rising_edge(clk_i) by sampling rstn_dbg_i (line 73) except during the asynchronous reset branch (line 68), and there is no other external-controlled enable/stall that blocks updates (global reset excluded).
- undermined behavior: no, line 73 `xrstn_ocd_o <= rstn_dbg_i;` via rstn_dbg_i -- xrstn_ocd_o is driven only by the clocked copy from rstn_dbg_i (line 73) and reset (line 70); no alternate/test override is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xrstn_ocd_o | neorv32_sys_reset | exit port | 3 -> 73 `xrstn_ocd_o <= rstn_dbg_i;` | COPIES rstn_dbg_i | verified |  | not listed |
| rstn_dbg_i | neorv32_sys_reset | sets | 3 -> 73 `xrstn_ocd_o <= rstn_dbg_i;` | CARRIES xrstn_ocd_o | verified |  | not listed |

## Concept: Clock-enable configuration bit (en) that enables or disables the ticker/counter operation

- confidentiality: yes-assumed, line 140 `clk_en_o(clk_div2_c)    <= cnt(0)  and (not cnt2(0));` via clk_en_o (output port) -- en controls whether the ticker increments and thus whether clk_en_o pulses are produced (cnt gating at line 130 and pulses at line 140), so observers of clk_en_o can infer en's value.
- integrity: yes-rtl, line 129 `en <= or_reduce_f(enable_i);` via enable_i (input) -- en is updated every clock from enable_i (line 129) and immediately gates cnt updates (if en = '1' at line 130), so an external input can change en while the ticker is operating.
- availability: yes-rtl, line 130 `if (en = '1') then` via enable_i (via en) -- the condition if (en = '1') at line 130 controls whether cnt increments (line 131) or is held/reset (line 133), so clearing enable_i/en stops counting and prevents downstream clk_en_o pulses.
- undermined behavior: no, line 129 `en <= or_reduce_f(enable_i);` via enable_i -- en has a single clocked driver (en <= or_reduce_f(enable_i) at line 129 and reset at line 125) and there is no alternate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| en | neorv32_sys_clock | stores | 3 -> 129 `en <= or_reduce_f(enable_i);` | CLOCKED_BY clk_i | verified |  | not listed |
| enable_i | neorv32_sys_clock | sets | 2 -> 129 `en <= or_reduce_f(enable_i);` | SOURCES en | verified |  | hit |

## Concept: Clock-enable pulses (clk_en_o) produced from the internal counters (cnt, cnt2) that gate downstream clocks

- confidentiality: yes-assumed, line 140 `clk_en_o(clk_div2_c)    <= cnt(0)  and (not cnt2(0));` via clk_en_o (output port) -- clk_en_o bits are produced and driven to external outputs (lines 140-147) so external consumers can observe the pulse timing and learn information derived from the internal counters.
- integrity: yes-rtl, line 140 `clk_en_o(clk_div2_c)    <= cnt(0)  and (not cnt2(0));` via enable_i / en (via cnt and cnt2) -- clk_en_o bits are computed from cnt and cnt2 at line 140 and those counters are gated by en (if en = '1' at line 130, with en coming from enable_i at line 129), so an external input can alter the pulses while consumers rely on them.
- availability: yes-rtl, line 130 `if (en = '1') then` via enable_i (via en) -- the if (en = '1') condition at line 130 controls whether cnt increments (line 131) or is reset (line 133), and en is driven from enable_i, so clearing enable_i/en prevents cnt progression and therefore stops clk_en_o pulses.
- undermined behavior: no, line 140 `clk_en_o(clk_div2_c)    <= cnt(0)  and (not cnt2(0));` via cnt / cnt2 -- each clk_en_o bit is computed only from the internal counters cnt and cnt2 (lines 140-147) and there is no debug/test bypass or alternate assignment in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| clk_en_o | neorv32_sys_clock | exit port | 2 -> 140 `clk_en_o(clk_div2_c)    <= cnt(0)  and (not cnt2(0));` | GATED_BY cnt | verified |  | hit |
| cnt | neorv32_sys_clock | stores | 3 -> 131 `cnt <= std_ulogic_vector(unsigned(cnt) + 1);` | CLOCKED_BY clk_i | verified |  | not listed |
| cnt2 | neorv32_sys_clock | stores | 3 -> 135 `cnt2 <= cnt;` | CLOCKED_BY clk_i | verified |  | not listed |
| en | neorv32_sys_clock | stores | 3 -> 129 `en <= or_reduce_f(enable_i);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): clk_en_o <- cnt, cnt2; cnt <- en
