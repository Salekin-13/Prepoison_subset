# neorv32_uart

**Purpose (model):** UART peripheral that decodes bus accesses to configure control registers and FIFOs, generates uart_clk from clkgen_i(ctrl.prsc), accepts/transmits serial data via uart_rxd_i/uart_txd_o through RX/TX FIFOs and engines, and reports events on irq_rx_o/irq_tx_o.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | bus request handshake and decode (acknowledge a bus transaction and decide its target) |  | 5 / 5 |
| configure | writes to control registers (enable, sim_mode, hwfc_en, prsc, baud, irq enables, clr flags) |  | 15 / 15 |
| operate | transmit path: bus writes a byte into TX FIFO, FIFO read into tx_engine.sreg and serialized onto uart_txd_o |  | 13 / 13 |
| operate | receive path: uart_rxd_i sampled into rx_engine.sync/sreg, rx_engine.done set and RX FIFO written |  | 10 / 10 |
| report | interrupt generation for RX/TX conditions (irq_rx_o, irq_tx_o) derived from ctrl.irq_* bits and FIFO status |  | 11 / 11 |
| read out | bus reads return control/status fields and RX FIFO data on bus_rsp_o.data |  | 22 / 22 |
| reset | reset clears control registers, engine state and FIFOs under rstn_i |  | 35 / 35 |

## Concept: Bus access decode and eligibility (strobe, read/write, address bit) that selects control registers vs data FIFOs

- confidentiality: no, line 217 `bus_rsp_o.data(data_rtx_msb_c        downto data_rtx_lsb_c)        <= rx_fifo.rdata;` via bus_rsp_o.data -- The bus response copies either control fields or FIFO data to bus_rsp_o.data (e.g. line 217), so the decode decision is observable and not secret.
- integrity: yes-rtl, line 261 `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i -- Routing into FIFOs and control fields is driven directly by bus_req_i fields (tx_fifo.we uses bus_req_i.stb/rw/addr at line 261) with no protection, so an external bus can change the decode.
- availability: yes-rtl, line 176 `if (bus_req_i.stb = '1') then` via bus_req_i.stb -- The bus_access process only performs an access when bus_req_i.stb = '1' (line 176), so an external master can block or enable access routing and thereby stop decode-driven activity.
- undermined behavior: no, line 176 `if (bus_req_i.stb = '1') then` via bus_req_i -- The selection is performed only by the sampled bus_req_i fields in the bus_access process (lines 170-179) and there is no alternate debug/test bypass present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i.stb | neorv32_uart | sets | 3 -> 176 `if (bus_req_i.stb = '1') then` | GATES ctrl.enable | verified |  | not listed |
| bus_req_i.rw | neorv32_uart | sets | 2 -> 177 `if (bus_req_i.rw = '1') then` | GATES ctrl.enable | verified |  | not listed |
| bus_req_i.addr | neorv32_uart | sets | 2 -> 178 `if (bus_req_i.addr(2) = '0') then` | GATES ctrl.enable | verified |  | not listed |

## Concept: Module enable bit (ctrl.enable) that gates most UART behavior

- confidentiality: yes-assumed, line 228 `clkgen_en_o <= ctrl.enable;` via clkgen_en_o -- ctrl.enable is copied to the external output clkgen_en_o (line 228) and also read back via the bus (line 195), so its value is externally observable.
- integrity: yes-rtl, line 179 `ctrl.enable        <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- ctrl.enable is written directly from bus_req_i.data at line 179 and can be changed while the UART operates, affecting downstream gating.
- availability: yes-rtl, line 344 `tx_engine.state(2) <= ctrl.enable;` via ctrl.enable -- tx_engine.state(2) <= ctrl.enable (line 344) so clearing ctrl.enable externally disables the transmitter and can halt progress.
- undermined behavior: no, line 179 `ctrl.enable        <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- At runtime ctrl.enable is driven only by the bus write at line 179 (and reset at 156); there is no alternate override mode.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.enable | neorv32_uart | stores | 3 -> 179 `ctrl.enable        <= bus_req_i.data(ctrl_en_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i.data | neorv32_uart | sets | 2 -> 179 `ctrl.enable        <= bus_req_i.data(ctrl_en_c);` | SOURCES ctrl.enable | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Baud-rate configuration (ctrl.baud) used to load TX/RX baud counters

- confidentiality: yes-assumed, line 199 `bus_rsp_o.data(ctrl_baud9_c downto ctrl_baud0_c) <= ctrl.baud;` via bus_rsp_o.data -- ctrl.baud is returned on bus reads at line 199, so its configured value is observable externally.
- integrity: yes-rtl, line 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` via bus_req_i.data -- ctrl.baud is written directly from bus_req_i.data at line 183 and may be changed while the TX/RX engines use it, altering UART timing.
- availability: no, line 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` via bus_req_i.data -- ctrl.baud updates are ordinary clocked control writes (line 183) and there is no external condition that freezes its update.
- undermined behavior: no, line 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` via bus_req_i.data -- ctrl.baud has a single runtime driver (bus write at line 183) and no debug/test bypass is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.baud | neorv32_uart | stores | 3 -> 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i.data | neorv32_uart | sets | 6 -> 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` | SOURCES ctrl.baud | verified |  | not listed |
| tx_engine.baudcnt | neorv32_uart | stores | 3 -> 349 `tx_engine.baudcnt <= ctrl.baud;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.baud <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; tx_engine.baudcnt <- tx_engine.baudcnt, tx_engine.state, uart_clk

## Concept: Prescaler index (ctrl.prsc) that selects which clkgen_i bit yields uart_clk

- confidentiality: yes-assumed, line 198 `bus_rsp_o.data(ctrl_prsc2_c downto ctrl_prsc0_c) <= ctrl.prsc;` via bus_rsp_o.data -- ctrl.prsc is returned on bus reads at line 198, so its value can be learned externally.
- integrity: yes-rtl, line 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i.data -- ctrl.prsc is written directly from bus_req_i.data at line 182 and can be changed while uart_clk is relied upon, altering selected clocking.
- availability: no, line 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i.data -- ctrl.prsc updates are standard clocked writes (line 182) and nothing in the RTL blocks its update.
- undermined behavior: no, line 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i.data -- ctrl.prsc has a single runtime driver (line 182) and there is no alternate override path.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.prsc | neorv32_uart | stores | 3 -> 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i.data | neorv32_uart | sets | 5 -> 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | SOURCES ctrl.prsc | verified |  | not listed |
| uart_clk | neorv32_uart | computes | 2 -> 229 `uart_clk    <= clkgen_i(to_integer(unsigned(ctrl.prsc)));` | SELECTED_BY ctrl.prsc | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.prsc <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; uart_clk <- ctrl.prsc

## Concept: Hardware flow-control enable (ctrl.hwfc_en) that changes CTS/RTS gating

- confidentiality: yes-assumed, line 197 `bus_rsp_o.data(ctrl_hwfc_en_c)                   <= ctrl.hwfc_en;` via bus_rsp_o.data -- ctrl.hwfc_en is returned on bus reads at line 197 and thus externally observable.
- integrity: yes-rtl, line 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` via bus_req_i.data -- ctrl.hwfc_en is written directly from bus_req_i.data at line 181 and can be changed during operation, altering flow-control decisions.
- availability: no, line 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` via bus_req_i.data -- ctrl.hwfc_en is updated by ordinary clocked writes (line 181) and there is no external condition that freezes the bit.
- undermined behavior: no, line 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` via bus_req_i.data -- At runtime the bit is driven only by the bus write (line 181); no debug/test bypass is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.hwfc_en | neorv32_uart | stores | 3 -> 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_uart | sets | 4 -> 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` | SOURCES ctrl.hwfc_en | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.hwfc_en <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Simulation-mode flag (ctrl.sim_mode) that forces FIFO clears and enables the simulation transmitter

- confidentiality: yes-assumed, line 259 `tx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_tx = '1') else '0';` via tx_fifo.clear -- ctrl.sim_mode forces tx_fifo.clear (line 259) and rx_fifo.clear (line 304), so its setting is observable through FIFO behavior and thus externally visible.
- integrity: yes-rtl, line 180 `ctrl.sim_mode      <= bus_req_i.data(ctrl_sim_en_c) and bool_to_ulogic_f(sim_mode_en_c);` via bus_req_i.data -- ctrl.sim_mode is written from bus_req_i.data at line 180 (gated by sim_mode_en_c) and can be set while FIFOs are in use, changing FIFO behavior.
- availability: yes-rtl, line 259 `tx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_tx = '1') else '0';` via ctrl.sim_mode -- When ctrl.sim_mode = '1' the RTL asserts tx_fifo.clear (line 259), which can remove queued data and prevent progress.
- undermined behavior: no, line 180 `ctrl.sim_mode      <= bus_req_i.data(ctrl_sim_en_c) and bool_to_ulogic_f(sim_mode_en_c);` via bus_req_i.data -- At runtime ctrl.sim_mode is driven only by the bus write (line 180) (with a compile-time sim_mode_en_c gate); there is no alternate runtime override.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.sim_mode | neorv32_uart | stores | 3 -> 180 `ctrl.sim_mode      <= bus_req_i.data(ctrl_sim_en_c) and bool_to_ulogic_f(sim_mode_en_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_uart | sets | 3 -> 180 `ctrl.sim_mode      <= bus_req_i.data(ctrl_sim_en_c) and bool_to_ulogic_f(sim_mode_en_c);` | GATES ctrl.sim_mode | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.sim_mode <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb

## Concept: Interrupt-enable bits (ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf) that qualify irq_rx_o/irq_tx_o

- confidentiality: yes-assumed, line 208 `bus_rsp_o.data(ctrl_irq_rx_nempty_c)             <= ctrl.irq_rx_nempty;` via bus_rsp_o.data -- The irq enable bits are returned on bus reads (e.g. line 208) and also gate external irq outputs (lines 270, 315), making their state externally observable.
- integrity: yes-rtl, line 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` via bus_req_i.data -- These bits are written directly from bus_req_i.data (example at line 185) and can be changed while interrupts are active, altering interrupt behavior.
- availability: no, line 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` via bus_req_i.data -- The enable bits are ordinary clocked configuration writes (line 185) and there is no external blocker that freezes updates.
- undermined behavior: no, line 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` via bus_req_i.data -- Each interrupt-enable bit has a single runtime driver (control write at lines 185..189) and there is no alternate runtime bypass.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.irq_rx_nempty | neorv32_uart | stores | 3 -> 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_uart | sets | 7 -> 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` | SOURCES ctrl.irq_rx_nempty | verified |  | not listed |
| ctrl.irq_rx_half | neorv32_uart | stores | 3 -> 186 `ctrl.irq_rx_half   <= bus_req_i.data(ctrl_irq_rx_half_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_uart | sets | 8 -> 186 `ctrl.irq_rx_half   <= bus_req_i.data(ctrl_irq_rx_half_c);` | SOURCES ctrl.irq_rx_half | verified |  | not listed |
| ctrl.irq_rx_full | neorv32_uart | stores | 3 -> 187 `ctrl.irq_rx_full   <= bus_req_i.data(ctrl_irq_rx_full_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_uart | sets | 9 -> 187 `ctrl.irq_rx_full   <= bus_req_i.data(ctrl_irq_rx_full_c);` | SOURCES ctrl.irq_rx_full | verified |  | not listed |
| ctrl.irq_tx_empty | neorv32_uart | stores | 3 -> 188 `ctrl.irq_tx_empty  <= bus_req_i.data(ctrl_irq_tx_empty_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_uart | sets | 10 -> 188 `ctrl.irq_tx_empty  <= bus_req_i.data(ctrl_irq_tx_empty_c);` | SOURCES ctrl.irq_tx_empty | verified |  | not listed |
| ctrl.irq_tx_nhalf | neorv32_uart | stores | 3 -> 189 `ctrl.irq_tx_nhalf  <= bus_req_i.data(ctrl_irq_tx_nhalf_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_uart | sets | 11 -> 189 `ctrl.irq_tx_nhalf  <= bus_req_i.data(ctrl_irq_tx_nhalf_c);` | SOURCES ctrl.irq_tx_nhalf | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.irq_rx_nempty <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_rx_half <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_rx_full <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_tx_empty <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_tx_nhalf <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Received byte exported to the bus (RX FIFO readout, rx_fifo.rdata -> bus_rsp_o.data)

- confidentiality: yes-assumed, line 217 `bus_rsp_o.data(data_rtx_msb_c        downto data_rtx_lsb_c)        <= rx_fifo.rdata;` via bus_rsp_o.data -- Received bytes are copied from the RX FIFO into bus_rsp_o.data on bus reads (line 217), so externally-visible masters can learn the data.
- integrity: yes-assumed, line 306 `rx_fifo.we    <= rx_engine.done;` via rx_engine.done / uart_rxd_i -- rx_fifo entries are written by the rx_engine when rx_engine.done = '1' (line 306) based on uart_rxd_i samples, so whether the source of those samples is trusted depends on integration.
- availability: yes-rtl, line 304 `rx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_rx = '1') else '0';` via ctrl.clr_rx -- The RTL asserts rx_fifo.clear when ctrl.clr_rx = '1' (line 304), so an external control write can clear received data and prevent its delivery.
- undermined behavior: no, line 300 `rdata_o => rx_fifo.rdata,` via rx_engine_fifo_inst.rdata_o -- rx_fifo.rdata originates from the FIFO submodule (rdata_o, line 300) and there is no alternate runtime writer that replaces FIFO output.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rx_fifo.rdata | neorv32_uart | computes | 3 -> 300 `rdata_o => rx_fifo.rdata,` | CONNECTS rx_engine_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| bus_rsp_o.data | neorv32_uart | exit port | 21 -> 217 `bus_rsp_o.data(data_rtx_msb_c        downto data_rtx_lsb_c)        <= rx_fifo.rdata;` | COPIES rx_fifo.rdata | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): bus_rsp_o.data <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.sim_mode, tx_engine.busy, tx_fifo.avail

## Concept: Transmit byte staged in TX FIFO (tx_fifo.wdata and its flow into tx_engine.sreg) that will be sent serially

- confidentiality: yes-assumed, line 392 `uart_txd_o <= tx_engine.txd;` via uart_txd_o -- Data written into the TX FIFO is serialized and driven out on uart_txd_o (line 392), so the transmitted content is externally observable.
- integrity: yes-assumed, line 260 `tx_fifo.wdata <= bus_req_i.data(data_rtx_msb_c downto data_rtx_lsb_c);` via bus_req_i.data -- TX FIFO write-data is supplied by bus_req_i.data at line 260, so an external bus writer can control or change the bytes staged for transmission.
- availability: yes-rtl, line 259 `tx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_tx = '1') else '0';` via ctrl.clr_tx -- tx_fifo.clear is asserted when ctrl.enable = '0' or ctrl.sim_mode = '1' or ctrl.clr_tx = '1' (line 259), allowing external control writes to clear queued transmit data and prevent delivery.
- undermined behavior: no, line 260 `tx_fifo.wdata <= bus_req_i.data(data_rtx_msb_c downto data_rtx_lsb_c);` via tx_fifo.wdata -- At runtime the FIFO write-data is driven only from the bus write (line 260) and there is no alternate runtime override that substitutes a different write-data path.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i.data | neorv32_uart | sets | 14 -> 260 `tx_fifo.wdata <= bus_req_i.data(data_rtx_msb_c downto data_rtx_lsb_c);` | SOURCES tx_fifo.wdata | verified |  | not listed |
| tx_fifo.wdata | neorv32_uart | sets | 2 -> 250 `wdata_i => tx_fifo.wdata,` | CONNECTS tx_engine_fifo_inst.wdata_i | verified | (via connection, mode None) | not listed |
| tx_fifo.rdata | neorv32_uart | computes | 3 -> 351 `tx_engine.sreg    <= tx_fifo.rdata & '0';` | SOURCES tx_engine.sreg | edge, role unfit | SOURCES does not demonstrate 'computes' | not listed |
| tx_engine.sreg | neorv32_uart | stores | 3 -> 351 `tx_engine.sreg    <= tx_fifo.rdata & '0';` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tx_engine.sreg <- tx_engine.baudcnt, tx_engine.state, uart_clk

## Concept: Serialized TX output stream (uart_txd_o) driven by tx_engine.txd

- confidentiality: yes-assumed, line 392 `uart_txd_o <= tx_engine.txd;` via uart_txd_o -- The serial bit stream is driven onto the external port uart_txd_o (line 392), so the transmitted bits are externally visible.
- integrity: yes-assumed, line 365 `tx_engine.txd <= tx_engine.sreg(0);` via tx_engine.sreg -- tx_engine.txd is produced from tx_engine.sreg (tx_engine.txd <= tx_engine.sreg(0) at line 365) and the sreg content originates from the TX FIFO which is written by the bus, so external writers can indirectly change the transmitted stream.
- availability: yes-rtl, line 359 `((tx_engine.cts(1) = '0') or (ctrl.hwfc_en = '0')) then` via uart_ctsn_i / ctrl.hwfc_en -- The transmitter advances only when uart_clk = '1' and either CTS indicates clear or hwfc is disabled (guard at line 359), so an external CTS input (uart_ctsn_i) or hwfc setting can stall transmission.
- undermined behavior: no, line 392 `uart_txd_o <= tx_engine.txd;` via tx_engine.txd -- uart_txd_o is driven only from tx_engine.txd copied at line 392; there is no separate runtime bypass that substitutes a different driver for the serial pin.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tx_engine.txd | neorv32_uart | stores | 3 -> 341 `tx_engine.txd  <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| uart_txd_o | neorv32_uart | exit port | 2 -> 392 `uart_txd_o <= tx_engine.txd;` | COPIES tx_engine.txd | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tx_engine.txd <- tx_engine.state

## Concept: Serial RX input samples (uart_rxd_i) that feed the RX engine shift register

- confidentiality: yes-assumed, line 217 `bus_rsp_o.data(data_rtx_msb_c        downto data_rtx_lsb_c)        <= rx_fifo.rdata;` via bus_rsp_o.data -- Samples on uart_rxd_i are assembled into bytes and provided on bus_rsp_o.data during reads (line 217), so received data is externally observable.
- integrity: yes-assumed, line 408 `rx_engine.sync(2) <= uart_rxd_i;` via uart_rxd_i -- uart_rxd_i is an external input sampled into rx_engine.sync at line 408 and the module does not authenticate the source, so the integrity of received samples depends on the external line's trustworthiness.
- availability: yes-rtl, line 424 `if (rx_engine.sync(1 downto 0) = "01") then` via rx_engine.sync -- Receiver start detection relies on rx_engine.sync(1 downto 0) = "01" (line 424), so holding the serial line static prevents detection of a start bit and stops reception.
- undermined behavior: no, line 408 `rx_engine.sync(2) <= uart_rxd_i;` via uart_rxd_i -- Sampling is performed only from the uart_rxd_i port into rx_engine.sync at line 408; there is no alternate runtime source that overwrites those samples.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| uart_rxd_i | neorv32_uart | sets | 2 -> 408 `rx_engine.sync(2) <= uart_rxd_i;` | CARRIES rx_engine.sync | verified |  | hit |
| rx_engine.sync | neorv32_uart | stores | 3 -> 408 `rx_engine.sync(2) <= uart_rxd_i;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rx_engine.sync <- uart_clk
