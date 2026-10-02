# neorv32_twi

**Purpose (model):** neorv32_twi is a TWI/I2C controller: it accepts bus requests (bus_req_i), implements control and status registers, a TX/RX FIFO pair, a clock/phase generator, and a bit-level TWI engine that drives/reads the SDA and SCL pins and raises irq_o. It exposes register readback and an interrupt to the bus via bus_rsp_o and irq_o.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | control registers (enable, prescaler index, divider, clock-stretch enable) written from bus_req_i.data into ctrl |  | 9 / 9 |
| start | enqueue a transmit command / data into the TX FIFO (fifo.tx_wdata, fifo.tx_we) from a bus write |  | 6 / 6 |
| operate | clock generation (clk_gen.cnt, clk_gen.tick, phase generator) and the twi_engine state machine that sequences SDA/SCL phases and shifts bits (engine.sreg, engine.bitcnt, engine.state) |  | 29 / 29 |
| read out | bus reads return control/status fields and RX FIFO word (bus_rsp_o.data carrying ctrl fields or fifo.rx_rdata) |  | 12 / 12 |
| report | interrupt reporting: irq_o is driven from ctrl.enable, fifo.tx_avail and engine.busy |  | 5 / 5 |
| reset | reset clears control and engine registers and IO sample registers under rstn_i |  | 15 / 15 |

## Concept: Controller enable bit (ctrl.enable) that turns the TWI logic and clock-generator on or off

- confidentiality: no, line 143 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` via bus_rsp_o -- ctrl.enable is a configuration bit written by bus_req_i and explicitly returned on bus reads (bus_rsp_o.data at line 143), so the RTL treats it as readable rather than secret.
- integrity: yes-rtl, line 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` via bus_req_i -- bus_access writes ctrl.enable from bus_req_i.data at line 136 with no guard preventing writes while the engine/clock-generator are active, allowing external bus writes to change the enable during operation.
- availability: yes-rtl, line 252 `if (ctrl.enable = '0') then` via ctrl.enable -- clock_generator checks ctrl.enable at line 252 and clears clk_gen.tick and clk_gen.cnt when ctrl.enable = '0', so clearing this externally-writable bit prevents clocking and halts progress.
- undermined behavior: no, line 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` via bus_req_i -- ctrl.enable has a single write source in the bus_access process (line 136) and the RTL contains no debug/test override that substitutes a different assignment.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.enable | neorv32_twi | stores | 3 -> 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i.data | neorv32_twi | sets | 2 -> 136 `ctrl.enable <= bus_req_i.data(ctrl_en_c);` | SOURCES ctrl.enable | verified |  | not listed |
| bus_rsp_o | neorv32_twi | exit port | 6 -> 143 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` | COPIES ctrl.enable | occurrence only | no COPIES record to 'ctrl.enable' at occurrence 6 | not listed |
| clkgen_en_o | neorv32_twi | exit port | 2 -> 270 `clkgen_en_o <= ctrl.enable;` | COPIES ctrl.enable | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Clock prescaler selection (ctrl.prsc) used to index clkgen_i for tick sampling

- confidentiality: no, line 144 `bus_rsp_o.data(ctrl_prsc2_c downto ctrl_prsc0_c) <= ctrl.prsc;` via bus_rsp_o -- ctrl.prsc is a configuration register written by the bus and explicitly read back via bus_rsp_o.data at line 144, so the RTL does not keep it secret.
- integrity: yes-rtl, line 137 `ctrl.prsc   <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i -- bus_access writes ctrl.prsc from bus_req_i.data at line 137 with no guard preventing writes while the clock/tick selection is in use, allowing external writes to change prescaler while running.
- availability: no, line 137 `ctrl.prsc   <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i -- ctrl.prsc is updated only by the bus write at line 137 (on the clock edge) and there is no external stall input in the RTL that can freeze its update, so availability is not blocked by the design.
- undermined behavior: no, line 137 `ctrl.prsc   <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i -- ctrl.prsc has a single intended driver (the bus_access write at line 137) and the RTL shows no alternate/test override for this field.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.prsc | neorv32_twi | stores | 3 -> 137 `ctrl.prsc   <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i.data | neorv32_twi | sets | 3 -> 137 `ctrl.prsc   <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | SOURCES ctrl.prsc | verified |  | not listed |
| bus_rsp_o | neorv32_twi | exit port | 7 -> 144 `bus_rsp_o.data(ctrl_prsc2_c downto ctrl_prsc0_c) <= ctrl.prsc;` | COPIES ctrl.prsc | occurrence only | no COPIES record to 'ctrl.prsc' at occurrence 7 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.prsc <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Clock divider value (ctrl.cdiv) that defines when clk_gen.tick is asserted (cnt == cdiv)

- confidentiality: no, line 145 `bus_rsp_o.data(ctrl_cdiv3_c downto ctrl_cdiv0_c) <= ctrl.cdiv;` via bus_rsp_o -- ctrl.cdiv is a configuration register written by the bus and explicitly returned on bus reads (bus_rsp_o.data at line 145), so the RTL does not hide it.
- integrity: yes-rtl, line 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` via bus_req_i -- bus_access writes ctrl.cdiv from bus_req_i.data at line 138 with no guarding against writes while clk_gen.cnt is used to produce clk_gen.tick, allowing external writes to change the divider during operation.
- availability: no, line 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` via bus_req_i -- ctrl.cdiv is updated by the bus write at line 138 on the clock edge and there is no RTL stall that prevents updates, so availability is not blocked by the design.
- undermined behavior: no, line 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` via bus_req_i -- ctrl.cdiv has a single write source in the bus_access process (line 138) and no alternate/test assignment overrides it in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.cdiv | neorv32_twi | stores | 3 -> 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i.data | neorv32_twi | sets | 4 -> 138 `ctrl.cdiv   <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` | SOURCES ctrl.cdiv | verified |  | not listed |
| bus_rsp_o | neorv32_twi | exit port | 8 -> 145 `bus_rsp_o.data(ctrl_cdiv3_c downto ctrl_cdiv0_c) <= ctrl.cdiv;` | COPIES ctrl.cdiv | occurrence only | no COPIES record to 'ctrl.cdiv' at occurrence 8 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.cdiv <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Clock-stretch enable (ctrl.clkstr) that allows SCL-based halting of the internal phase generator

- confidentiality: no, line 146 `bus_rsp_o.data(ctrl_clkstr_en_c)                 <= ctrl.clkstr;` via bus_rsp_o -- ctrl.clkstr is written by bus_req_i and explicitly readable via bus_rsp_o.data at line 146, so the RTL does not treat it as secret.
- integrity: yes-rtl, line 139 `ctrl.clkstr <= bus_req_i.data(ctrl_clkstr_en_c);` via bus_req_i -- bus_access writes ctrl.clkstr from bus_req_i.data at line 139 without guarding against writes while the phase generator/engine are active, permitting external writes to change clock-stretch behavior during operation.
- availability: yes-rtl, line 296 `clk_gen.halt <= '1' when (io_con.scl_out = '1') and (io_con.scl_in_ff(1) = '0') and (ctrl.clkstr = '1') else '0';` via io_con.scl_in_ff -- clk_gen.halt is asserted when (io_con.scl_out = '1') and (io_con.scl_in_ff(1) = '0') and (ctrl.clkstr = '1') at line 296, so with clkstr enabled an external SCL condition (sampled via io_con.scl_in_ff) can halt the phase generator and block progress.
- undermined behavior: no, line 139 `ctrl.clkstr <= bus_req_i.data(ctrl_clkstr_en_c);` via bus_req_i -- ctrl.clkstr is driven only by the bus_access write at line 139 and the RTL contains no alternate debug/test override that substitutes a different source.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.clkstr | neorv32_twi | stores | 2 -> 139 `ctrl.clkstr <= bus_req_i.data(ctrl_clkstr_en_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_twi | sets | 5 -> 139 `ctrl.clkstr <= bus_req_i.data(ctrl_clkstr_en_c);` | SOURCES ctrl.clkstr | verified |  | not listed |
| bus_rsp_o | neorv32_twi | exit port | 9 -> 146 `bus_rsp_o.data(ctrl_clkstr_en_c)                 <= ctrl.clkstr;` | COPIES ctrl.clkstr | occurrence only | no COPIES record to 'ctrl.clkstr' at occurrence 9 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.clkstr <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Transmit FIFO contents — TWI transmit commands/data queued by bus writes and consumed by the engine


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| fifo.tx_wdata | neorv32_twi | sets | 3 -> 198 `fifo.tx_wdata <= bus_req_i.data(dcmd_cmd_hi_c downto dcmd_lsb_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| fifo.tx_rdata | neorv32_twi | computes | 2 -> 193 `rdata_o => fifo.tx_rdata,` | CONNECTS tx_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| engine.sreg | neorv32_twi | stores | 5 -> 327 `engine.sreg   <= fifo.tx_rdata(dcmd_msb_c downto dcmd_lsb_c) & (not fifo.tx_rdata(dcmd_ack` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): engine.sreg <- clk_gen.phase, engine.state

## Concept: Received bytes captured from the TWI bus and placed into the RX FIFO for bus reads

- confidentiality: yes-assumed, line 156 `bus_rsp_o.data(8 downto 0) <= fifo.rx_rdata;` via bus_rsp_o -- received bytes are captured from the external TWI pins (line 378->228) and explicitly returned to the bus master via bus_rsp_o.data at line 156, so they are observable externally and may be treated as sensitive by the integrator.
- integrity: yes-assumed, line 228 `fifo.rx_wdata <= engine.sreg(0) & engine.sreg(8 downto 1);` via engine.sreg -- fifo.rx_wdata is derived from engine.sreg (line 228), which itself is shifted from sampled SDA (line 378); the RTL provides no authentication on the source of the sampled bits (twi_sda_i), so whether the writer is trusted depends on integration.
- availability: yes-rtl, line 296 `clk_gen.halt <= '1' when (io_con.scl_out = '1') and (io_con.scl_in_ff(1) = '0') and (ctrl.clkstr = '1') else '0';` via io_con.scl_in_ff -- clk_gen.halt can be asserted (line 296) when ctrl.clkstr = '1' and an external SCL condition is observed via io_con.scl_in_ff, and halting phase progression prevents engine shifts/done and thus blocks RX FIFO writes.
- undermined behavior: no, line 228 `fifo.rx_wdata <= engine.sreg(0) & engine.sreg(8 downto 1);` via fifo.rx_wdata -- RX FIFO write data and write-enable come from the engine (lines 228-229) and there is no alternate/test mode in the RTL that substitutes a different source for received bytes.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| fifo.rx_wdata | neorv32_twi | sets | 3 -> 228 `fifo.rx_wdata <= engine.sreg(0) & engine.sreg(8 downto 1);` | DERIVES_FROM engine.sreg | verified |  | not listed |
| engine.sreg | neorv32_twi | stores | 5 -> 327 `engine.sreg   <= fifo.tx_rdata(dcmd_msb_c downto dcmd_lsb_c) & (not fifo.tx_rdata(dcmd_ack` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_rsp_o | neorv32_twi | exit port | 16 -> 156 `bus_rsp_o.data(8 downto 0) <= fifo.rx_rdata;` | COPIES fifo.rx_rdata | occurrence only | no COPIES record to 'fifo.rx_rdata' at occurrence 16 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): engine.sreg <- clk_gen.phase, engine.state

## Concept: Engine finite state (engine.state) that sequences TWI transactions and phases

- confidentiality: yes-assumed, line 154 `bus_rsp_o.data(ctrl_busy_c)      <= engine.busy or fifo.tx_avail;` via bus_rsp_o -- engine.state determines engine.busy which is reported on bus_rsp_o.data(ctrl_busy_c) at line 154 and affects externally visible behavior, so parts of the internal state are observable and may reveal activity to an external observer.
- integrity: yes-rtl, line 321 `engine.state(2) <= ctrl.enable;` via ctrl.enable -- engine.state(2) is copied from ctrl.enable at line 321, and ctrl.enable is writable by bus_req_i (line 136) with no guard preventing updates while the engine is running, enabling external writes to alter engine.state.
- availability: yes-rtl, line 321 `engine.state(2) <= ctrl.enable;` via ctrl.enable -- engine.state(2) follows ctrl.enable (line 321) and clearing ctrl.enable (writable from bus_req_i) causes the engine to be disabled and prevents state progression, so external writes can stop the state machine.
- undermined behavior: no, line 321 `engine.state(2) <= ctrl.enable;` via twi_engine -- engine.state is driven only by the twi_engine process (assignments such as line 321 and the case arms) and the RTL contains no separate debug/test override that bypasses the state updates.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| engine.state | neorv32_twi | stores | 3 -> 321 `engine.state(2) <= ctrl.enable;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): engine.state <- clk_gen.phase, clk_gen.tick, engine.bitcnt, engine.state, fifo.tx_avail

## Concept: Engine busy indicator (engine.busy) used to gate reads, FIFO pops and IRQ logic

- confidentiality: yes-assumed, line 154 `bus_rsp_o.data(ctrl_busy_c)      <= engine.busy or fifo.tx_avail;` via bus_rsp_o -- engine.busy is reported via bus_rsp_o.data(ctrl_busy_c) at line 154 and via irq behavior, so its value (which reveals controller activity) is observable outside the module.
- integrity: yes-rtl, line 321 `engine.state(2) <= ctrl.enable;` via ctrl.enable -- engine.busy follows engine.state (computed at line 401) and engine.state(2) is driven from ctrl.enable at line 321 (which is writable by the bus), so external writes to ctrl.enable can change engine.busy while it is being used.
- availability: yes-rtl, line 321 `engine.state(2) <= ctrl.enable;` via ctrl.enable -- clearing ctrl.enable (copied into engine.state(2) at line 321) forces engine.busy low and prevents the engine from being 'busy', so an external writer can stop the busy condition and thereby affect progress/handshakes.
- undermined behavior: no, line 401 `engine.busy <= '1' when (engine.state(2) = '1') and (engine.state(1 downto 0) /= "00") else '0';` via engine.state -- engine.busy is derived only from engine.state by the concurrent assignment at line 401 and the RTL offers no alternate/test override for busy.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| engine.busy | neorv32_twi | computes | 6 -> 401 `engine.busy <= '1' when (engine.state(2) = '1') and (engine.state(1 downto 0) /= "00") els` | GATED_BY engine.state | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): engine.busy <- engine.state

## Concept: IRQ output (irq_o) that reports controller ready/idle condition to the host

- confidentiality: yes-assumed, line 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` via irq_o -- irq_o is an external interrupt output driven from internal status signals at line 239 and thus reveals controller readiness/activity to external observers, so the integrator may treat it as sensitive.
- integrity: yes-rtl, line 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` via ctrl.enable -- irq_o is computed from ctrl.enable, fifo.tx_avail and engine.busy at line 239 and those inputs (e.g. ctrl.enable) are writable/controllable from outside via bus_req_i, so external actions can change irq_o without internal protection.
- availability: yes-rtl, line 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` via ctrl.enable -- the IRQ assignment at line 239 is gated by ctrl.enable and fifo.tx_avail/engine.busy, so clearing ctrl.enable (or manipulating FIFO availability) prevents the IRQ from asserting and thus denies that external event to the host.
- undermined behavior: no, line 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` via irq_generator -- irq_o is produced only by the irq_generator process (reset at 237 and assignment at 239) and there is no alternate/test-mode assignment present in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| irq_o | neorv32_twi | exit port | 3 -> 239 `irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy);` | GATED_BY ctrl.enable | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): irq_o <- ctrl.enable, engine.busy, fifo.tx_avail

## Concept: TWI bus output levels (SDA and SCL) that the core drives onto the external pins

- confidentiality: yes-assumed, line 406 `twi_sda_o     <= io_con.sda_out;` via twi_sda_o -- the module drives SDA/SCL on the external pins (twi_sda_o at line 406 / twi_scl_o at line 407) and those signals convey the transmitted data/timing, so their contents are observable outside and may be considered sensitive by the integrator.
- integrity: no, line 335 `io_con.sda_out <= '1';` via twi_engine -- io_con.sda_out/io_con.scl_out are driven only by the internal twi_engine process (e.g. assignments at line 335 and related case arms) and the RTL contains no alternate external driver that directly overwrites those signals.
- availability: yes-rtl, line 296 `clk_gen.halt <= '1' when (io_con.scl_out = '1') and (io_con.scl_in_ff(1) = '0') and (ctrl.clkstr = '1') else '0';` via io_con.scl_in_ff -- clk_gen.halt is asserted when a sampled SCL condition and ctrl.clkstr are present (line 296), which stops phase progression and therefore can freeze or alter the externally visible SDA/SCL toggling.
- undermined behavior: no, line 335 `io_con.sda_out <= '1';` via twi_engine -- the TWI outputs are driven by the twi_engine case logic (e.g. line 335) and the RTL provides no debug/test override that substitutes a different driver for the outputs.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| twi_sda_o | neorv32_twi | exit port | 2 -> 406 `twi_sda_o     <= io_con.sda_out;` | COPIES io_con.sda_out | verified |  | hit |
| twi_scl_o | neorv32_twi | exit port | 2 -> 407 `twi_scl_o     <= io_con.scl_out;` | COPIES io_con.scl_out | verified |  | not listed |

## Concept: Sampled TWI input registers (io_con.sda_in_ff, io_con.scl_in_ff) used for status reads and for halt/clock-stretch detection

- confidentiality: yes-assumed, line 150 `bus_rsp_o.data(ctrl_sense_scl_c) <= io_con.scl_in_ff(1);` via bus_rsp_o -- the sampled SDA/SCL registers are reported back to the bus master via bus_rsp_o.data at line 150/151 and reflect external bus conditions, so they are observable externally and may be treated as sensitive.
- integrity: yes-assumed, line 314 `io_con.sda_in_ff <= io_con.sda_in_ff(0) & io_con.sda_in;` via twi_sda_i -- io_con.sda_in_ff/io_con.scl_in_ff are populated from the external pins (io_con.sda_in/io_con.scl driven from twi_sda_i/twi_scl_i at lines 408-409 and clocked into the flip-flops at line 314-315), and the RTL provides no mechanism to authenticate those external sources, so integrity depends on integration.
- availability: yes-rtl, line 296 `clk_gen.halt <= '1' when (io_con.scl_out = '1') and (io_con.scl_in_ff(1) = '0') and (ctrl.clkstr = '1') else '0';` via io_con.scl_in_ff -- clk_gen.halt uses sampled SCL (io_con.scl_in_ff) and ctrl.clkstr at line 296, so external SCL conditions can cause the phase generator to halt and thereby block engine progress.
- undermined behavior: no, line 314 `io_con.sda_in_ff <= io_con.sda_in_ff(0) & io_con.sda_in;` via twi_engine -- the sampled input flip-flops are driven only by the sampling assignments in the twi_engine process (line 314-315) and the RTL provides no alternate/test override for those registers.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| io_con.sda_in_ff | neorv32_twi | stores | 4 -> 314 `io_con.sda_in_ff <= io_con.sda_in_ff(0) & io_con.sda_in;` | CLOCKED_BY clk_i | verified |  | not listed |
| io_con.scl_in_ff | neorv32_twi | stores | 5 -> 315 `io_con.scl_in_ff <= io_con.scl_in_ff(0) & io_con.scl_in;` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_rsp_o | neorv32_twi | exit port | 11 -> 150 `bus_rsp_o.data(ctrl_sense_scl_c) <= io_con.scl_in_ff(1);` | DERIVES_FROM io_con.scl_in_ff | occurrence only | no DERIVES_FROM record to 'io_con.scl_in_ff' at occurrence 11 | not listed |
| bus_rsp_o | neorv32_twi | exit port | 12 -> 151 `bus_rsp_o.data(ctrl_sense_sda_c) <= io_con.sda_in_ff(1);` | DERIVES_FROM io_con.sda_in_ff | occurrence only | no DERIVES_FROM record to 'io_con.sda_in_ff' at occurrence 12 | not listed |
