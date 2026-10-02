# neorv32_twi

**Purpose (model):** TWI (I2C) peripheral: it accepts bus requests (bus_req_i) to write/read control and FIFO data, stores control settings, runs a clock generator and a phase generator, drives a bit-level TWI engine that samples/produces SDA/SCL, presents FIFO read/write interfaces to instantiated FIFO subunits, reports status and responses on bus_rsp_o, exposes a clock-enable output clkgen_en_o and an interrupt irq_o.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | control register settings (enable, prescaler index, clock divisor, clock-stretch enable) written by bus writes |  | 7 / 7 |
| start | enqueue a transmit command / data into the TX FIFO (wdata + write enable) from a bus write |  | 6 / 6 |
| operate | clock generation (tick) and phase sequencing, and the TWI engine's bit-level transmit/receive operations that drive/observe SDA and SCL |  | 23 / 23 |
| read out | readback of control and status fields and RX FIFO data returned on bus_rsp_o.data |  | 12 / 12 |
| report | interrupt event (irq_o) produced from ctrl.enable, fifo.tx_avail and engine.busy |  | 3 / 3 |
| reset | what the block clears on rstn_i: bus response, control fields, clock generator counters, phase state, engine registers and I/O flip-flops |  | 17 / 17 |

## Concept: Control settings (enable, prescaler index, clock-divisor, clock-stretch enable) that configure clock generation and enable/disable the engine

- confidentiality: yes-assumed, line 143 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` via bus_rsp_o.data -- The settings are written by external bus writes and are explicitly read back onto bus_rsp_o (ctrl.enable copied at line 143), so an integrator could treat them as secret configuration values.
- integrity: yes-rtl, line 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` via bus_req_i -- Bus writes at line 136 (guarded by bus_req_i.stb/bus_req_i.rw/bus_req_i.addr) update ctrl.enable while the engine uses it (engine.state(2) <= ctrl.enable at line 321), and the RTL places no guard preventing updates during operation.
- availability: yes-rtl, line 252 `if (ctrl.enable = '0') then` via bus_req_i -- Clearing ctrl.enable (which external bus writes can do) causes the clock generator to force clk_gen.tick='0' and reset cnt (if ctrl.enable='0' branch at line 252), preventing clock ticks and halting engine progress.
- undermined behavior: no, line 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` via bus_req_i -- There is a single update path (reset and bus writes at lines 124 and 136--139) and no debug/test override or alternate driver present to bypass these registers.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.enable | neorv32_twi | stores | 3 -> 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.prsc | neorv32_twi | stores | 3 -> 137 `ctrl.prsc   <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.cdiv | neorv32_twi | stores | 3 -> 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.clkstr | neorv32_twi | stores | 2 -> 139 `ctrl.clkstr <= bus_req_i.data(ctrl_clkstr_en_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i | neorv32_twi | sets | 6 -> 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` | SOURCES ctrl.enable | occurrence only | no SOURCES record to 'ctrl.enable' at occurrence 6 | not listed |
| bus_req_i | neorv32_twi | sets | 7 -> 137 `ctrl.prsc   <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | SOURCES ctrl.prsc | occurrence only | no SOURCES record to 'ctrl.prsc' at occurrence 7 | not listed |
| bus_req_i | neorv32_twi | sets | 8 -> 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` | SOURCES ctrl.cdiv | occurrence only | no SOURCES record to 'ctrl.cdiv' at occurrence 8 | not listed |
| bus_req_i | neorv32_twi | sets | 9 -> 139 `ctrl.clkstr <= bus_req_i.data(ctrl_clkstr_en_c);` | SOURCES ctrl.clkstr | occurrence only | no SOURCES record to 'ctrl.clkstr' at occurrence 9 | not listed |
| bus_rsp_o | neorv32_twi | exit port | 6 -> 143 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` | COPIES ctrl.enable | occurrence only | no COPIES record to 'ctrl.enable' at occurrence 6 | not listed |
| bus_rsp_o | neorv32_twi | exit port | 7 -> 144 `bus_rsp_o.data(ctrl_prsc2_c downto ctrl_prsc0_c) <= ctrl.prsc;` | COPIES ctrl.prsc | occurrence only | no COPIES record to 'ctrl.prsc' at occurrence 7 | not listed |
| bus_rsp_o | neorv32_twi | exit port | 8 -> 145 `bus_rsp_o.data(ctrl_cdiv3_c downto ctrl_cdiv0_c) <= ctrl.cdiv;` | COPIES ctrl.cdiv | occurrence only | no COPIES record to 'ctrl.cdiv' at occurrence 8 | not listed |
| bus_rsp_o | neorv32_twi | exit port | 9 -> 146 `bus_rsp_o.data(ctrl_clkstr_en_c)                 <= ctrl.clkstr;` | COPIES ctrl.clkstr | occurrence only | no COPIES record to 'ctrl.clkstr' at occurrence 9 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.prsc <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.cdiv <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.clkstr <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Clock-generation decision (clk_gen.tick and clk_gen.cnt) that sequences engine steps and FIFO transfers

- confidentiality: yes-assumed, line 282 `elsif (clk_gen.tick = '1') and (clk_gen.halt = '0') then` via twi_sda_o/twi_scl_o -- clk_gen.tick controls phase advancement (phase_generator at line 282) which determines the io_con outputs forwarded to the external pins (twi_sda_o/twi_scl_o), so tick/cnt are observable via waveform timing.
- integrity: yes-rtl, line 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` via bus_req_i -- Bus writes set ctrl.cdiv at line 138 and clock_generator uses ctrl.cdiv to decide when clk_gen.tick is asserted (compare at line 258/259), and these writes are not blocked while the generator runs so external writes can alter tick timing.
- availability: yes-rtl, line 257 `if (clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1') then` via clkgen_i -- Generation of ticks is gated by clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1' (line 257), so an external clkgen_i input bit can prevent tick production and block engine/FIFO sequencing.
- undermined behavior: no, line 259 `clk_gen.tick <= '1';` via clock_generator -- clk_gen.tick and clk_gen.cnt are driven only by the clock_generator logic (e.g. tick <= '1' at line 259) and there is no debug/test override path in the RTL that substitutes a different driver.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| clk_gen.tick | neorv32_twi | stores | 6 -> 259 `clk_gen.tick <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| clk_gen.cnt | neorv32_twi | stores | 3 -> 254 `clk_gen.cnt  <= (others => '0');` | CLOCKED_BY clk_i | verified |  | not listed |
| clkgen_i | neorv32_twi | sets | 2 -> 257 `if (clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1') then` | GATES clk_gen.tick | verified |  | not listed |
| ctrl.prsc | neorv32_twi | computes | 5 -> 257 `if (clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1') then` | SELECTS clk_gen.tick | edge, role unfit | SELECTS does not demonstrate 'computes' | hit |
| ctrl.cdiv | neorv32_twi | computes | 5 -> 258 `if (clk_gen.cnt = ctrl.cdiv) then` | CONSTRAINS clk_gen.cnt | edge, role unfit | CONSTRAINS does not demonstrate 'computes' | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): clk_gen.tick <- clk_gen.cnt, clkgen_i, ctrl.cdiv, ctrl.enable, ctrl.prsc; clk_gen.cnt <- clk_gen.cnt, clkgen_i, ctrl.cdiv, ctrl.enable, ctrl.prsc; ctrl.prsc <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.cdiv <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: TX FIFO transmit command/data (the command bytes written by the bus that the engine consumes to drive SDA/SCL)

- confidentiality: yes-assumed, line 406 `twi_sda_o     <= io_con.sda_out;` via twi_sda_o -- FIFO entries are loaded into engine.sreg (line 327) and used to drive io_con outputs which are forwarded to the external pins (twi_sda_o at line 406), so FIFO contents are observable externally via the TWI waveform.
- integrity: yes-rtl, line 197 `fifo.tx_we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i -- External bus writes assert fifo.tx_we and provide fifo.tx_wdata at lines 197--198 under the bus_req_i guard, and those writes can alter FIFO contents while the engine later consumes fifo.tx_rdata (engine load at line 327) with no RTL guard preventing mid-operation changes.
- availability: yes-rtl, line 168 `fifo.clear <= not ctrl.enable;` via ctrl.enable -- fifo.clear is driven by not ctrl.enable (line 168) and connected into the FIFO clear input (tx_fifo_inst.clear_i at line 184), so clearing ctrl.enable (via bus writes) will flush/clear the TX FIFO and prevent transmission.
- undermined behavior: no, line 197 `fifo.tx_we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i -- TX FIFO entries are written only via the bus write path (fifo.tx_we/fifo.tx_wdata at lines 197--198) and FIFO clear/reset; there is no alternate debug/test override that directly substitutes TX payloads.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_twi | sets | 14 -> 198 `fifo.tx_wdata <= bus_req_i.data(dcmd_cmd_hi_c downto dcmd_lsb_c);` | SOURCES fifo.tx_wdata | occurrence only | no SOURCES record to 'fifo.tx_wdata' at occurrence 14 | not listed |
| fifo.tx_wdata | neorv32_twi | sets | 2 -> 188 `wdata_i => fifo.tx_wdata,` | CONNECTS tx_fifo_inst.wdata_i | verified | (via connection, mode None) | not listed |
| fifo.tx_we | neorv32_twi | sets | 2 -> 189 `we_i    => fifo.tx_we,` | CONNECTS tx_fifo_inst.we_i | verified | (via connection, mode None) | not listed |
| fifo.tx_rdata | neorv32_twi | computes | 2 -> 193 `rdata_o => fifo.tx_rdata,` | CONNECTS tx_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| engine.sreg | neorv32_twi | stores | 5 -> 327 `engine.sreg   <= fifo.tx_rdata(dcmd_msb_c downto dcmd_lsb_c) & (not fifo.tx_rdata(dcmd_ack` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fifo.tx_we <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; engine.sreg <- clk_gen.phase, engine.state

## Concept: RX FIFO received data (bytes captured from SDA and written to the RX FIFO for bus readback)

- confidentiality: yes-assumed, line 156 `bus_rsp_o.data(8 downto 0) <= fifo.rx_rdata;` via bus_rsp_o.data -- RX FIFO contents are provided to bus masters on readback (bus_rsp_o.data assigned from fifo.rx_rdata at line 156), so captured bytes are observable outside the module and may be treated as sensitive.
- integrity: yes-assumed, line 228 `fifo.rx_wdata <= engine.sreg(0) & engine.sreg(8 downto 1);` via engine.sreg (derived from twi_sda_i) -- RX FIFO is written from engine.sreg at line 228, and engine.sreg is derived from sampled external SDA (io_con.sda_in_ff from twi_sda_i at line 408), so external TWI activity controls what is stored and whether that data is trusted depends on integration.
- availability: yes-rtl, line 296 `clk_gen.halt <= '1' when (io_con.scl_out = '1') and (io_con.scl_in_ff(1) = '0') and (ctrl.clkstr = '1') else '0';` via twi_scl_i -- clk_gen.halt is asserted when (io_con.scl_out='1') and (io_con.scl_in_ff(1)='0') and ctrl.clkstr='1' (line 296); halt blocks phase advancement (phase_generator condition at line 282) and can prevent the engine from sampling/writing received data, so external SCL behavior can freeze RX progress.
- undermined behavior: no, line 228 `fifo.rx_wdata <= engine.sreg(0) & engine.sreg(8 downto 1);` via engine.sreg -- RX FIFO entries are produced only by the engine (fifo.rx_wdata <= engine.sreg at line 228) with no alternate debug/test path that bypasses the capture into the RX FIFO.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| engine.sreg | neorv32_twi | stores | 5 -> 327 `engine.sreg   <= fifo.tx_rdata(dcmd_msb_c downto dcmd_lsb_c) & (not fifo.tx_rdata(dcmd_ack` | CLOCKED_BY clk_i | verified |  | not listed |
| engine.done | neorv32_twi | computes | 5 -> 386 `engine.done              <= '1';` | SELECTED_BY engine.state | verified |  | not listed |
| fifo.rx_wdata | neorv32_twi | sets | 2 -> 219 `wdata_i => fifo.rx_wdata,` | CONNECTS rx_fifo_inst.wdata_i | verified | (via connection, mode None) | not listed |
| fifo.rx_we | neorv32_twi | sets | 2 -> 220 `we_i    => fifo.rx_we,` | CONNECTS rx_fifo_inst.we_i | verified | (via connection, mode None) | not listed |
| bus_rsp_o | neorv32_twi | exit port | 16 -> 156 `bus_rsp_o.data(8 downto 0) <= fifo.rx_rdata;` | COPIES fifo.rx_rdata | occurrence only | no COPIES record to 'fifo.rx_rdata' at occurrence 16 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): engine.sreg <- clk_gen.phase, engine.state; engine.done <- clk_gen.phase, engine.bitcnt, engine.state

## Concept: Engine sequencing state and bit counter (engine.state, engine.bitcnt) that control TWI protocol steps

- confidentiality: yes-assumed, line 154 `bus_rsp_o.data(ctrl_busy_c)      <= engine.busy or fifo.tx_avail;` via bus_rsp_o.data -- Engine state and bit counter determine engine.busy and pin-driving behavior, and engine.busy is exposed via bus_rsp_o (ctrl_busy bit at line 154) and the TWI waveform on external pins, so the internal sequencing is externally observable.
- integrity: yes-rtl, line 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` via bus_req_i -- ctrl.enable is written by bus writes at line 136 and is copied into engine.state(2) at line 321, so external writes can change the engine's state bit while the state machine is running (no guard prevents mid-operation writes).
- availability: yes-rtl, line 321 `engine.state(2) <= ctrl.enable;` via bus_req_i -- engine.state(2) is driven from ctrl.enable (line 321), so clearing ctrl.enable via bus writes will clear the engine active bit and prevent the state machine from running.
- undermined behavior: no, line 321 `engine.state(2) <= ctrl.enable;` via ctrl.enable -- Engine sequencing (engine.state/engine.bitcnt) is controlled only by the state machine and ctrl.enable (e.g. engine.state(2) <= ctrl.enable at line 321); there is no alternate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| engine.state | neorv32_twi | stores | 3 -> 321 `engine.state(2) <= ctrl.enable;` | CLOCKED_BY clk_i | verified |  | not listed |
| engine.bitcnt | neorv32_twi | stores | 3 -> 326 `engine.bitcnt <= (others => '0');` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl.enable | neorv32_twi | sets | 10 -> 321 `engine.state(2) <= ctrl.enable;` | CARRIES engine.state | edge, role unfit | CARRIES does not demonstrate 'sets' (mode None, storage edge) | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): engine.state <- clk_gen.phase, clk_gen.tick, engine.bitcnt, engine.state, fifo.tx_avail; engine.bitcnt <- clk_gen.phase, engine.state; ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Physical TWI outputs (SDA and SCL) that leave the block (twi_sda_o, twi_scl_o) and the I/O-forwarding registers that drive them

- confidentiality: yes-assumed, line 406 `twi_sda_o     <= io_con.sda_out;` via twi_sda_o -- io_con.sda_out is forwarded to the external pin twi_sda_o at line 406, so the pin waveform is externally observable and may reveal internal data/state.
- integrity: yes-rtl, line 197 `fifo.tx_we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i -- External bus writes that populate the TX FIFO (fifo.tx_we/fifo.tx_wdata at lines 197--198) influence the engine's sreg and thus io_con outputs (engine loads fifo.tx_rdata at line 327 and sda_out is assigned in engine branches such as line 335), and the RTL provides no guard preventing changes while transmission is in progress.
- availability: yes-rtl, line 296 `clk_gen.halt <= '1' when (io_con.scl_out = '1') and (io_con.scl_in_ff(1) = '0') and (ctrl.clkstr = '1') else '0';` via twi_scl_i / ctrl.clkstr -- clk_gen.halt is asserted by the clock-stretch condition at line 296 (depends on io_con.scl_out, sampled scl input and ctrl.clkstr), which prevents phase advancement (phase_generator gating at line 282) and can freeze the external pin waveform.
- undermined behavior: no, line 335 `io_con.sda_out <= '1';` via io_con.sda_out -- The external pins are driven only by io_con.sda_out/io_con.scl_out assignments from the engine (example assignment at line 335) and reset; there is no separate debug/test override that substitutes a different driver for the outputs.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| twi_sda_o | neorv32_twi | exit port | 2 -> 406 `twi_sda_o     <= io_con.sda_out;` | COPIES io_con.sda_out | verified |  | hit |
| io_con.sda_out | neorv32_twi | stores | 3 -> 335 `io_con.sda_out <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| twi_scl_o | neorv32_twi | exit port | 2 -> 407 `twi_scl_o     <= io_con.scl_out;` | COPIES io_con.scl_out | verified |  | not listed |
| io_con.scl_out | neorv32_twi | stores | 4 -> 341 `io_con.scl_out <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): io_con.sda_out <- clk_gen.phase, engine.bitcnt, engine.state; io_con.scl_out <- clk_gen.phase, engine.state

## Concept: Interrupt event reported on irq_o that signals 'ready-to-send' (ctrl.enable & not fifo.tx_avail & not engine.busy)

- confidentiality: yes-assumed, line 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` via irq_o -- irq_o is an exported signal computed from internal state and FIFO status and is observable externally at line 239, so it reveals module readiness and may be treated as sensitive.
- integrity: yes-rtl, line 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` via bus_req_i -- irq_o is recomputed every clock at line 239 from ctrl.enable/fifo.tx_avail/engine.busy, and ctrl.enable can be changed by bus writes (line 136) while irq is in use, so external writes can alter the interrupt assertion.
- availability: yes-rtl, line 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` via bus_req_i -- irq_o depends on ctrl.enable and fifo/engine state (assignment at line 239), and external actions (e.g., clearing ctrl.enable via bus writes or changing FIFO occupancy with bus writes) can prevent or force the interrupt.
- undermined behavior: no, line 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` via irq_o -- irq_o is driven only by the irq_generator expression (line 239) and reset; there is no alternate debug/test mode that forces or bypasses the interrupt in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| irq_o | neorv32_twi | exit port | 3 -> 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` | GATED_BY ctrl.enable | verified |  | hit |
| fifo.tx_avail | neorv32_twi | computes | 5 -> 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` | GATED_BY engine.busy | occurrence only | no GATED_BY record to 'engine.busy' at occurrence 5 | not listed |
| engine.busy | neorv32_twi | computes | 6 -> 401 `engine.busy <= '1' when (engine.state(2) = '1') and (engine.state(1 downto 0) /= "00") els` | GATED_BY engine.state | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): irq_o <- ctrl.enable, engine.busy, fifo.tx_avail; engine.busy <- engine.state
