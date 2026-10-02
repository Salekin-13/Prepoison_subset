# neorv32_twi

**Purpose (model):** neorv32_twi decodes bus requests to configure TWI control registers and to enqueue/dequeue FIFO words, produces status and interrupt outputs, runs a programmable clock generator and a bit-level TWI engine that drives/reads the SDA and SCL pins.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | write TWI control registers (ctrl.enable, ctrl.prsc, ctrl.cdiv, ctrl.clkstr) |  | 9 / 9 |
| start | enqueue a transmit command into the TX FIFO from a bus write (tx_wdata/tx_we), making it available to the engine |  | 9 / 9 |
| operate | timed TWI bit-transfer operation driven by the clock generator and the engine (phase sequencing, sda/scl outputs, shift/bitcount, done) |  | 25 / 25 |
| report | status and register readback returned on bus_rsp_o.data (control bits, FIFO size, sense bits, busy/avail flags) |  | 12 / 12 |
| read out | read out received bytes from RX FIFO onto the bus (fifo.rx_rdata -> bus_rsp_o.data) |  | 4 / 4 |
| report | interrupt event asserted to CPU (irq_o) when enabled and a TX slot is empty and engine idle |  | 3 / 3 |
| reset | what is cleared or forced on rstn_i active: bus_rsp_o, control registers, clock-generator counters and phases, engine state and io_con registers |  | 22 / 22 |

## Concept: Module enable configuration (ctrl.enable): the stored enable bit that turns TWI operation on/off

- confidentiality: no, line 143 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` via bus_rsp_o -- ctrl.enable is copied to the bus read data at line 143 (and exposed on clkgen_en_o at line 270), so the setting is externally observable and is a read-back of the writer's own setting.
- integrity: yes-rtl, line 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- A bus write at line 136 (guarded by stb/rw/addr) can change ctrl.enable while the engine uses it (engine.state reads ctrl.enable at line 321), so the bit can be altered during operation without additional protection.
- availability: yes-rtl, line 252 `if (ctrl.enable = '0') then` via bus_req_i -- The clock generator stops advancing (clk_gen.tick and clk_gen.cnt forced at line 252-253) when ctrl.enable = '0', so external writes that clear ctrl.enable can prevent module progress.
- undermined behavior: no, line 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- ctrl.enable has only the reset assignment (line 124) and the bus write (line 136); there is no alternate/test/debug override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.enable | neorv32_twi | stores | 3 -> 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i | neorv32_twi | sets | 6 -> 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` | SOURCES ctrl.enable | occurrence only | no SOURCES record to 'ctrl.enable' at occurrence 6 | not listed |
| bus_rsp_o | neorv32_twi | exit port | 6 -> 143 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` | COPIES ctrl.enable | occurrence only | no COPIES record to 'ctrl.enable' at occurrence 6 | not listed |
| clkgen_en_o | neorv32_twi | exit port | 2 -> 270 `clkgen_en_o <= ctrl.enable;` | COPIES ctrl.enable | verified |  | not listed |
| engine.state | neorv32_twi | stores | 3 -> 321 `engine.state(2) <= ctrl.enable;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; engine.state <- clk_gen.phase, clk_gen.tick, engine.bitcnt, engine.state, fifo.tx_avail

## Concept: Clock prescaler selection (ctrl.prsc) that chooses which clkgen_i bit gates the clock counter

- confidentiality: no, line 144 `bus_rsp_o.data(ctrl_prsc2_c downto ctrl_prsc0_c) <= ctrl.prsc;` via bus_rsp_o -- ctrl.prsc is returned on bus reads at line 144, so its value is externally observable as a readable configuration.
- integrity: yes-rtl, line 137 `ctrl.prsc   <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i.data -- Bus writes at line 137 set ctrl.prsc and the clock generator uses it immediately to index clkgen_i at line 257, so writes can change which external clkgen_i bit is sampled while the generator runs.
- availability: yes-rtl, line 257 `if (clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1') then` via clkgen_i -- The clock generator only advances cnt and may assert tick when clkgen_i(selected) = '1' (line 257), so the external clkgen_i input can prevent ticks and stall operation depending on the selected index.
- undermined behavior: no, line 137 `ctrl.prsc   <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i.data -- ctrl.prsc is only written by the reset (line 125) and the bus write (line 137); no alternate override or debug assignment appears in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.prsc | neorv32_twi | stores | 3 -> 137 `ctrl.prsc   <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i | neorv32_twi | sets | 7 -> 137 `ctrl.prsc   <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | SOURCES ctrl.prsc | occurrence only | no SOURCES record to 'ctrl.prsc' at occurrence 7 | not listed |
| bus_rsp_o | neorv32_twi | exit port | 7 -> 144 `bus_rsp_o.data(ctrl_prsc2_c downto ctrl_prsc0_c) <= ctrl.prsc;` | COPIES ctrl.prsc | occurrence only | no COPIES record to 'ctrl.prsc' at occurrence 7 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.prsc <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Clock divider setting (ctrl.cdiv) used to compare the counter and generate the clock tick

- confidentiality: no, line 145 `bus_rsp_o.data(ctrl_cdiv3_c downto ctrl_cdiv0_c) <= ctrl.cdiv;` via bus_rsp_o -- ctrl.cdiv is returned on bus reads at line 145, so it is externally observable and not treated as secret in the RTL.
- integrity: yes-rtl, line 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` via bus_req_i.data -- Bus writes at line 138 set ctrl.cdiv and the clock generator compares clk_gen.cnt to ctrl.cdiv at lines 258-260, so writes can change tick timing during operation without blocking.
- availability: no, line 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` via bus_req_i -- ctrl.cdiv is only updated by explicit bus writes (line 138) and reset (line 126); there is no RTL condition reachable from outside that freezes ctrl.cdiv itself.
- undermined behavior: no, line 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` via bus_req_i.data -- ctrl.cdiv has a single driver from bus write (line 138) and reset (line 126); no override/test mode is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.cdiv | neorv32_twi | stores | 3 -> 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i | neorv32_twi | sets | 8 -> 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` | SOURCES ctrl.cdiv | occurrence only | no SOURCES record to 'ctrl.cdiv' at occurrence 8 | not listed |
| bus_rsp_o | neorv32_twi | exit port | 8 -> 145 `bus_rsp_o.data(ctrl_cdiv3_c downto ctrl_cdiv0_c) <= ctrl.cdiv;` | COPIES ctrl.cdiv | occurrence only | no COPIES record to 'ctrl.cdiv' at occurrence 8 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.cdiv <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Clock-stretch enable (ctrl.clkstr) that allows the engine to halt the phase generator on a stretched SCL

- confidentiality: no, line 146 `bus_rsp_o.data(ctrl_clkstr_en_c)                 <= ctrl.clkstr;` via bus_rsp_o -- ctrl.clkstr is returned on bus reads at line 146, so it is externally readable and not masked by the RTL.
- integrity: yes-rtl, line 139 `ctrl.clkstr <= bus_req_i.data(ctrl_clkstr_en_c);` via bus_req_i.data -- Bus writes at line 139 set ctrl.clkstr and clk_gen.halt uses it at line 296 to allow external SCL stretching to stop phase progression, so the configuration can be changed while running.
- availability: yes-rtl, line 296 `clk_gen.halt <= '1' when (io_con.scl_out = '1') and (io_con.scl_in_ff(1) = '0') and (ctrl.clkstr = '1') else '0';` via twi_scl_i -- When ctrl.clkstr = '1', an external SCL being pulled low (io_con.scl_in_ff(1) = '0') with scl_out='1' asserts clk_gen.halt (line 296) and stops phase progression, so external SCL input can block operation.
- undermined behavior: no, line 139 `ctrl.clkstr <= bus_req_i.data(ctrl_clkstr_en_c);` via bus_req_i.data -- ctrl.clkstr is driven only by the bus write at line 139 (and readback at 146); there is no separate override or test assignment in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.clkstr | neorv32_twi | stores | 2 -> 139 `ctrl.clkstr <= bus_req_i.data(ctrl_clkstr_en_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i | neorv32_twi | sets | 9 -> 139 `ctrl.clkstr <= bus_req_i.data(ctrl_clkstr_en_c);` | SOURCES ctrl.clkstr | occurrence only | no SOURCES record to 'ctrl.clkstr' at occurrence 9 | not listed |
| bus_rsp_o | neorv32_twi | exit port | 9 -> 146 `bus_rsp_o.data(ctrl_clkstr_en_c)                 <= ctrl.clkstr;` | COPIES ctrl.clkstr | occurrence only | no COPIES record to 'ctrl.clkstr' at occurrence 9 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.clkstr <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: TX command buffer contents (items enqueued into the TX FIFO by bus writes and later consumed by the engine)

- confidentiality: yes-assumed, line 327 `engine.sreg   <= fifo.tx_rdata(dcmd_msb_c downto dcmd_lsb_c) & (not fifo.tx_rdata(dcmd_ack_c));` via twi_sda_o / twi_scl_o -- FIFO entries written by the bus (lines 197-198) are loaded into engine.sreg at line 327 and then drive the external SDA/SCL outputs (lines 406-407), so FIFO contents can leave the module and are observable outside; whether they are secret depends on integration.
- integrity: yes-assumed, line 198 `fifo.tx_wdata <= bus_req_i.data(dcmd_cmd_hi_c downto dcmd_lsb_c);` via bus_req_i.data -- TX FIFO contents are written directly from bus_req_i.data at line 198 under the bus write guard (line 197), so the integrity of FIFO contents depends on whether the bus writer is trusted in the integration context.
- availability: yes-rtl, line 199 `fifo.tx_re    <= '1' when (engine.busy = '0') and (fifo.tx_avail = '1') and (clk_gen.tick = '1') else '0';` via clkgen_i -- FIFO consumption (fifo.tx_re) is gated by clk_gen.tick at line 199, and clk_gen.tick depends on external clkgen_i selection (line 257), so external clkgen_i can prevent FIFO items from being consumed and stall progress.
- undermined behavior: no, line 197 `fifo.tx_we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i -- TX FIFO write-data and write-enable are driven only by the bus assignments at lines 197-198 (and cleared by fifo.clear at line 168); there is no separate override/test source in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_twi | sets | 14 -> 198 `fifo.tx_wdata <= bus_req_i.data(dcmd_cmd_hi_c downto dcmd_lsb_c);` | SOURCES fifo.tx_wdata | occurrence only | no SOURCES record to 'fifo.tx_wdata' at occurrence 14 | not listed |
| fifo.tx_wdata | neorv32_twi | sets | 3 -> 198 `fifo.tx_wdata <= bus_req_i.data(dcmd_cmd_hi_c downto dcmd_lsb_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| fifo.tx_wdata | neorv32_twi | sets | 2 -> 188 `wdata_i => fifo.tx_wdata,` | CONNECTS tx_fifo_inst.wdata_i | verified | (via connection, mode None) | not listed |
| fifo.tx_rdata | neorv32_twi | computes | 2 -> 193 `rdata_o => fifo.tx_rdata,` | CONNECTS tx_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| engine.sreg | neorv32_twi | computes | 5 -> 327 `engine.sreg   <= fifo.tx_rdata(dcmd_msb_c downto dcmd_lsb_c) & (not fifo.tx_rdata(dcmd_ack` | DERIVES_FROM fifo.tx_rdata | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): engine.sreg <- clk_gen.phase, engine.state

## Concept: RX received-byte buffer (bytes produced by the engine and stored in RX FIFO for bus readout)

- confidentiality: yes-assumed, line 156 `bus_rsp_o.data(8 downto 0) <= fifo.rx_rdata;` via bus_rsp_o -- Bytes produced by the engine are written to the RX FIFO (lines 228-229) and the FIFO rdata is returned on bus reads at line 156, so received data can be observed externally and confidentiality depends on the use case.
- integrity: yes-assumed, line 228 `fifo.rx_wdata <= engine.sreg(0) & engine.sreg(8 downto 1);` via twi_sda_i / engine.sreg -- RX FIFO writes originate from engine.sreg (line 228), which is assembled from sampled external SDA (engine shifts in io_con.sda_in_ff at line 378 / twi_sda_i at line 408), so the content integrity depends on external I2C inputs and integration trust.
- availability: yes-rtl, line 229 `fifo.rx_we    <= engine.done;` via clkgen_i -- fifo.rx_we is asserted only when engine.done is asserted (line 229), and engine.done depends on clock/phase progression which can be blocked by external clock source selection (clkgen_i at line 257) or control, so external inputs can prevent RX FIFO writes and stall reception.
- undermined behavior: no, line 228 `fifo.rx_wdata <= engine.sreg(0) & engine.sreg(8 downto 1);` via twi_engine -- RX FIFO write-data and write-enable are produced only by the engine at lines 228-229; there is no alternate/test override of RX FIFO writes in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| engine.sreg | neorv32_twi | stores | 5 -> 327 `engine.sreg   <= fifo.tx_rdata(dcmd_msb_c downto dcmd_lsb_c) & (not fifo.tx_rdata(dcmd_ack` | CLOCKED_BY clk_i | verified |  | not listed |
| fifo.rx_wdata | neorv32_twi | sets | 3 -> 228 `fifo.rx_wdata <= engine.sreg(0) & engine.sreg(8 downto 1);` | DERIVES_FROM engine.sreg | verified |  | not listed |
| fifo.rx_wdata | neorv32_twi | sets | 2 -> 219 `wdata_i => fifo.rx_wdata,` | CONNECTS rx_fifo_inst.wdata_i | verified | (via connection, mode None) | not listed |
| fifo.rx_we | neorv32_twi | sets | 3 -> 229 `fifo.rx_we    <= engine.done;` | COPIES engine.done | verified |  | not listed |
| fifo.rx_rdata | neorv32_twi | exit port | 3 -> 224 `rdata_o => fifo.rx_rdata,` | CONNECTS rx_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'exit port' (mode None, storage not assigned) | not listed |
| bus_rsp_o | neorv32_twi | exit port | 16 -> 156 `bus_rsp_o.data(8 downto 0) <= fifo.rx_rdata;` | COPIES fifo.rx_rdata | occurrence only | no COPIES record to 'fifo.rx_rdata' at occurrence 16 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): engine.sreg <- clk_gen.phase, engine.state

## Concept: TWI serial-line driving values (the SDA and SCL outputs that leave the module)

- confidentiality: yes-assumed, line 406 `twi_sda_o     <= io_con.sda_out;` via twi_sda_o / twi_scl_o -- io_con.sda_out/scl_out are driven by the engine (various assignments 334..374) and forwarded to external pins at lines 406-407, so serial line activity is observable outside and confidentiality depends on the integration context.
- integrity: no, line 335 `io_con.sda_out <= '1';` via twi_engine -- The SDA/SCL outputs are driven only by the internal twi_engine state-machine assignments (for example line 335) and reset (line 306); there is no direct external writer to these signals in the RTL.
- availability: yes-rtl, line 281 `clk_gen.phase_gen <= "0001";` via ctrl.enable -- Phase generation is forced to the idle phase when ctrl.enable = '0' or engine.busy = '0' (line 281), and the engine's 'when others' sets outputs idle (lines 392-394), so external clearing of ctrl.enable prevents line toggling and halts activity.
- undermined behavior: no, line 335 `io_con.sda_out <= '1';` via twi_engine -- SDA/SCL outputs have a single driver in the twi_engine process (examples at lines 335, 341, 350, 356, 372, 374, 392); no debug/test override is present in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| twi_sda_o | neorv32_twi | exit port | 2 -> 406 `twi_sda_o     <= io_con.sda_out;` | COPIES io_con.sda_out | verified |  | hit |
| io_con.sda_out | neorv32_twi | stores | 3 -> 335 `io_con.sda_out <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| twi_scl_o | neorv32_twi | exit port | 2 -> 407 `twi_scl_o     <= io_con.scl_out;` | COPIES io_con.scl_out | verified |  | not listed |
| io_con.scl_out | neorv32_twi | stores | 4 -> 341 `io_con.scl_out <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): io_con.sda_out <- clk_gen.phase, engine.bitcnt, engine.state; io_con.scl_out <- clk_gen.phase, engine.state

## Concept: Interrupt request event (irq_o) asserted to the CPU when enabled, TX empty and engine idle

- confidentiality: yes-assumed, line 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` via irq_o -- irq_o is driven from internal status (ctrl.enable, fifo.tx_avail, engine.busy) and presented as an external interrupt output at line 239, so it reveals module activity to external observers and its confidentiality depends on system integration.
- integrity: yes-rtl, line 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` via bus_req_i -- irq_o reflects ctrl.enable which can be changed by bus writes at line 136 and other inputs that affect fifo.tx_avail/engine.busy, so external actors able to write control/status bits can affect irq_o without additional RTL protection.
- availability: yes-rtl, line 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` via ctrl.enable -- irq_o is gated by ctrl.enable and status signals at line 239, so clearing ctrl.enable (or manipulating fifo.tx_avail/engine.busy via external actions) can prevent irq assertion and affect availability of the interrupt.
- undermined behavior: no, line 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` via irq_generator -- irq_o has a single RTL driver in the irq_generator process (line 239) and no alternate/test override is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| irq_o | neorv32_twi | exit port | 3 -> 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` | GATED_BY ctrl.enable | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): irq_o <- ctrl.enable, engine.busy, fifo.tx_avail

## Concept: Engine run-time state (engine.state) that sequences bit-transfer phases and determines busy/done transitions

- confidentiality: yes-assumed, line 154 `bus_rsp_o.data(ctrl_busy_c)      <= engine.busy or fifo.tx_avail;` via bus_rsp_o -- engine.state drives engine.busy (line 401) and the busy/status bit is returned on bus reads at line 154, and engine.state also affects external SDA/SCL activity, so the internal sequencing state can be observed externally and confidentiality depends on integration.
- integrity: yes-rtl, line 321 `engine.state(2) <= ctrl.enable;` via bus_req_i / fifo.tx_rdata -- engine.state(2) is driven from ctrl.enable at line 321 (which bus writes can change at line 136) and the low bits are loaded from fifo.tx_rdata (line 329) populated by bus writes, so external bus actions can change engine.state while it is used for sequencing.
- availability: yes-rtl, line 328 `if (fifo.tx_avail = '1') and (clk_gen.tick = '1') then` via clkgen_i -- Loading of engine.state low bits depends on fifo.tx_avail and clk_gen.tick (line 328), and clk_gen.tick depends on external clkgen_i selection (line 257), so external clock input selection can prevent state transitions and freeze the engine sequence.
- undermined behavior: no, line 321 `engine.state(2) <= ctrl.enable;` via twi_engine -- engine.state is updated only inside the twi_engine process (assignments at line 321 and the case arms around 327..394); there is no separate override or debug path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| engine.state | neorv32_twi | stores | 3 -> 321 `engine.state(2) <= ctrl.enable;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): engine.state <- clk_gen.phase, clk_gen.tick, engine.bitcnt, engine.state, fifo.tx_avail
