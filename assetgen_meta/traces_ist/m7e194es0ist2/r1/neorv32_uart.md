# neorv32_uart

**Purpose (model):** UART peripheral: decodes bus reads/writes into control and data registers, holds TX/RX FIFO data, runs TX and RX engines that drive uart_txd_o and sample uart_rxd_i, manages RTS/CTS hardware flow-control, and emits bus responses and IRQs.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | Control registers written (enable, sim_mode, hwfc_en, prsc, baud, IRQ-selection bits, clr_rx, clr_tx) |  | 15 / 15 |
| start | Enqueue a transmit byte: bus_req_i.data -> tx_fifo.wdata and tx_fifo.we, then tx_engine may fetch (tx_fifo.re) to begin transmission |  | 4 / 4 |
| operate | Transmit operation: tx_engine sequences, shifts bits from tx_engine.sreg and toggles tx_engine.txd -> uart_txd_o |  | 7 / 7 |
| operate | Receive operation: sample uart_rxd_i into rx_engine.sync, assemble bits into rx_engine.sreg and assert rx_fifo.we when a byte is complete |  | 8 / 8 |
| report | IRQ generation (irq_tx_o, irq_rx_o) from control bits and FIFO status |  | 4 / 4 |
| read out | Bus read returns control fields and FIFO values (bus_rsp_o.data), including rx FIFO read data (rx_fifo.rdata) |  | 8 / 8 |
| reset | Synchronous registers and outputs cleared or forced on rstn_i = '0' (control registers, tx/rx engine state, FIFOs cleared by clear signals) |  | 8 / 8 |

## Concept: Module enable flag (ctrl.enable) that gates operation, FIFO clears, IRQs and clkgen enable

- confidentiality: no, line 195 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` via bus_rsp_o.data -- The module returns ctrl.enable on the bus at bus_rsp_o.data(ctrl_en_c) <= ctrl.enable (line 195), so the writer/master can read it back and it is not hidden by the RTL.
- integrity: yes-rtl, line 179 `ctrl.enable        <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- A bus write at line 179 (ctrl.enable <= bus_req_i.data(...)) can change ctrl.enable while the TX/RX engines use it (e.g. tx_engine.state(2) <= ctrl.enable at line 344 and rx_engine.state(1) <= ctrl.enable at line 417) and there is no RTL guard preventing such runtime writes.
- availability: yes-rtl, line 179 `ctrl.enable        <= bus_req_i.data(ctrl_en_c);` via bus_req_i -- An external bus master can clear or set ctrl.enable via the write at line 179, and ctrl.enable gates operation and IRQ generation (e.g. clkgen_en_o at line 228 and irq processes at lines 270 and 315), so an external write can stop module progress.
- undermined behavior: no, line 179 `ctrl.enable        <= bus_req_i.data(ctrl_en_c);` via bus_req_i -- ctrl.enable has a single software driver in the RTL (bus write at line 179 and reset at line 156); there is no debug/test override or secondary assignment in the supplied RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_uart | sets | 6 -> 179 `ctrl.enable        <= bus_req_i.data(ctrl_en_c);` | SOURCES ctrl.enable | occurrence only | no SOURCES record to 'ctrl.enable' at occurrence 6 | not listed |
| ctrl.enable | neorv32_uart | stores | 3 -> 179 `ctrl.enable        <= bus_req_i.data(ctrl_en_c);` | CLOCKED_BY clk_i | verified |  | hit |
| clkgen_en_o | neorv32_uart | exit port | 2 -> 228 `clkgen_en_o <= ctrl.enable;` | COPIES ctrl.enable | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Baud-rate configuration (ctrl.baud) that sets TX and RX timing counters

- confidentiality: yes-assumed, line 199 `bus_rsp_o.data(ctrl_baud9_c downto ctrl_baud0_c) <= ctrl.baud;` via bus_rsp_o.data -- ctrl.baud is returned on the bus at line 199 and also determines UART timing (copied into TX/RX baud counters at lines 349 and 432), so the value and its effects are observable and may be treated as sensitive by an integrator.
- integrity: yes-rtl, line 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` via bus_req_i.data -- A bus write at line 183 updates ctrl.baud and there is no RTL protection against changing it while it is being copied into tx_engine.baudcnt and rx_engine.baudcnt (lines 349, 368, 432), so the timing configuration can be altered during operation.
- availability: no, line 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` via bus_req_i.data -- ctrl.baud is updated only by the bus write at line 183 and reset at line 160; there is no external gate that freezes or prevents its update (clock/reset aside).
- undermined behavior: no, line 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` via bus_req_i.data -- ctrl.baud has a single RTL driver path (bus write at line 183 and reset at line 160); no debug/test override assignment is present in the supplied RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_uart | sets | 10 -> 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` | SOURCES ctrl.baud | occurrence only | no SOURCES record to 'ctrl.baud' at occurrence 10 | not listed |
| ctrl.baud | neorv32_uart | stores | 3 -> 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| tx_engine.baudcnt | neorv32_uart | stores | 3 -> 349 `tx_engine.baudcnt <= ctrl.baud;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.baud <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; tx_engine.baudcnt <- tx_engine.baudcnt, tx_engine.state, uart_clk

## Concept: UART prescaler selection (ctrl.prsc) that chooses which clkgen_i bit forms uart_clk

- confidentiality: yes-assumed, line 198 `bus_rsp_o.data(ctrl_prsc2_c downto ctrl_prsc0_c) <= ctrl.prsc;` via bus_rsp_o.data -- ctrl.prsc is returned on the bus at line 198 and it selects clkgen_i bits for uart_clk at line 229, so its setting and effects are observable and may be treated as confidential.
- integrity: yes-rtl, line 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i.data -- A bus write at line 182 updates ctrl.prsc and there is no RTL guard preventing changes while uart_clk is selected/used (selection occurs at line 229), so the prescaler can be altered during operation.
- availability: no, line 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i.data -- ctrl.prsc updates only via the bus write at line 182 and reset at line 159; there is no external gate that freezes its updates apart from reset.
- undermined behavior: no, line 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i.data -- ctrl.prsc has only the bus write and reset drivers in the RTL; no alternate/test mode assignment is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_uart | sets | 9 -> 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | SOURCES ctrl.prsc | occurrence only | no SOURCES record to 'ctrl.prsc' at occurrence 9 | not listed |
| ctrl.prsc | neorv32_uart | stores | 3 -> 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| uart_clk | neorv32_uart | computes | 2 -> 229 `uart_clk    <= clkgen_i(to_integer(unsigned(ctrl.prsc)));` | SELECTED_BY ctrl.prsc | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.prsc <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; uart_clk <- ctrl.prsc

## Concept: Hardware flow-control enable (ctrl.hwfc_en) that affects CTS/RTS gating and transmitter behavior

- confidentiality: yes-assumed, line 197 `bus_rsp_o.data(ctrl_hwfc_en_c)                   <= ctrl.hwfc_en;` via bus_rsp_o.data -- ctrl.hwfc_en is returned on the bus at line 197 and it drives external handshake signals (uart_rtsn_o) and transmitter gating, so its value and effects are externally observable and may be treated as confidential.
- integrity: yes-rtl, line 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` via bus_req_i.data -- A bus write at line 181 updates ctrl.hwfc_en and the transmitter and rtr_control use it (e.g. transmitter gating at line 359 and uart_rtsn_o control at lines 472-477) with no RTL protection preventing runtime changes.
- availability: yes-rtl, line 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` via bus_req_i.data -- An external bus write at line 181 can enable or disable hardware flow control and thereby cause rtr_control to assert/deassert RTS (lines 472-476) or cause the transmitter to be gated (line 359), which can stop or resume data flow.
- undermined behavior: no, line 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` via bus_req_i.data -- ctrl.hwfc_en is driven only by the bus write at line 181 and reset at line 158; no alternate debug/test override exists in the supplied RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_uart | sets | 8 -> 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` | SOURCES ctrl.hwfc_en | occurrence only | no SOURCES record to 'ctrl.hwfc_en' at occurrence 8 | not listed |
| ctrl.hwfc_en | neorv32_uart | stores | 3 -> 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| uart_rtsn_o | neorv32_uart | exit port | 3 -> 475 `uart_rtsn_o <= '1';` | GATED_BY ctrl.hwfc_en | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.hwfc_en <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; uart_rtsn_o <- ctrl.enable, ctrl.hwfc_en, rx_fifo.half

## Concept: Serial transmit bit-stream (uart_txd_o) produced by the TX engine

- confidentiality: yes-assumed, line 392 `uart_txd_o <= tx_engine.txd;` via uart_txd_o -- The serial bit-stream is driven out on the uart_txd_o port at line 392 (tx_engine.txd -> uart_txd_o), so transmitted data are observable outside the module and may be considered confidential depending on integration.
- integrity: yes-rtl, line 261 `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i.data -- Bus writes assert tx_fifo.we and supply tx_fifo.wdata at lines 260-261 and those writes are not blocked while the TX engine reads tx_fifo.rdata (used at line 351), allowing external bus activity to change the queued transmit data during operation.
- availability: yes-rtl, line 259 `tx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_tx = '1') else '0';` via ctrl.sim_mode -- tx_fifo.clear is asserted when (ctrl.enable='0') or (ctrl.sim_mode='1') or (ctrl.clr_tx='1') (line 259), and this clears queued TX data and prevents transmission; additionally CTS (uart_ctsn_i -> tx_engine.cts at line 337 and gating at 359) can pause transmission.
- undermined behavior: yes-rtl, line 499 `if (ctrl.enable = '1') and (ctrl.sim_mode = '1') and (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') then` via ctrl.sim_mode -- When simulation mode is enabled the RTL includes a simulation_transmitter process that logs bus writes (condition checked at line 499) and tx_fifo.clear is asserted in sim mode (line 259), redirecting transmitted data to a file and bypassing the physical UART output.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tx_engine.txd | neorv32_uart | stores | 3 -> 341 `tx_engine.txd  <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |
| uart_txd_o | neorv32_uart | exit port | 2 -> 392 `uart_txd_o <= tx_engine.txd;` | COPIES tx_engine.txd | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tx_engine.txd <- tx_engine.state

## Concept: Received bytes and RX-FIFO occupancy (data stored by RX FIFO and its avail/half/free indicators)

- confidentiality: yes-assumed, line 217 `bus_rsp_o.data(data_rtx_msb_c        downto data_rtx_lsb_c)        <= rx_fifo.rdata;` via bus_rsp_o.data -- RX FIFO data (rx_fifo.rdata) are returned on the bus at line 217 and occupancy/status also appear on bus reads and IRQ outputs (lines 201-203 and 315), so received contents and status are observable outside the module.
- integrity: yes-rtl, line 304 `rx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_rx = '1') else '0';` via ctrl.clr_rx -- rx_fifo.clear is asserted when ctrl.clr_rx='1' (written by the bus at line 190) or ctrl.sim_mode etc (line 304), and this clear can occur while the receiver writes into the FIFO (rx_fifo.we <= rx_engine.done at line 306), enabling an external bus write to lose or modify stored received data.
- availability: yes-rtl, line 307 `rx_fifo.re    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '0') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i.stb -- rx_fifo.re is asserted only when the bus issues a read ((bus_req_i.stb='1') and (bus_req_i.rw='0') and (bus_req_i.addr(2)='1')) at line 307, so an external master that does not read can cause the FIFO to fill and eventually block reception (overrun).
- undermined behavior: yes-rtl, line 304 `rx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_rx = '1') else '0';` via ctrl.sim_mode -- rx_fifo.clear is controlled not only by clr_rx but also by ctrl.sim_mode (rx_fifo.clear <= '1' when ctrl.sim_mode='1' at line 304), so simulation/test mode or the clear control can bypass normal FIFO contents and behavior.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rx_engine.sreg | neorv32_uart | stores | 4 -> 434 `rx_engine.sreg    <= rx_engine.sync(2) & rx_engine.sreg(rx_engine.sreg'left downto 1);` | CLOCKED_BY clk_i | verified |  | not listed |
| rx_fifo.wdata | neorv32_uart | sets | 3 -> 305 `rx_fifo.wdata <= rx_engine.sreg(7 downto 0);` | DERIVES_FROM rx_engine.sreg | verified |  | not listed |
| rx_fifo.avail | neorv32_uart | sets | 3 -> 301 `avail_o => rx_fifo.avail` | CONNECTS rx_engine_fifo_inst.avail_o | verified | (via connection, mode None) | not listed |
| bus_rsp_o | neorv32_uart | exit port | 24 -> 217 `bus_rsp_o.data(data_rtx_msb_c        downto data_rtx_lsb_c)        <= rx_fifo.rdata;` | COPIES rx_fifo.rdata | occurrence only | no COPIES record to 'rx_fifo.rdata' at occurrence 24 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rx_engine.sreg <- rx_engine.baudcnt, rx_engine.state, uart_clk

## Concept: TX FIFO queued bytes (data written by bus writes and later consumed by the TX engine)

- confidentiality: yes-assumed, line 392 `uart_txd_o <= tx_engine.txd;` via uart_txd_o -- Bytes written to the TX FIFO will be emitted on the uart_txd_o pin (assignment at line 392), and the bus writer also supplies them (line 260), so their contents are externally observable and may be sensitive.
- integrity: yes-rtl, line 261 `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i.data -- Bus writes set tx_fifo.we and tx_fifo.wdata at line 261/260 and such writes are not prevented while the TX engine reads tx_fifo.rdata (used at line 351), allowing concurrent writes to alter queued transmit data.
- availability: yes-rtl, line 259 `tx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_tx = '1') else '0';` via ctrl.sim_mode -- tx_fifo.clear is asserted when ctrl.enable='0' or ctrl.sim_mode='1' or ctrl.clr_tx='1' (line 259), any of which (controllable via bus or sim mode) will clear the FIFO and prevent transmission progress.
- undermined behavior: yes-rtl, line 259 `tx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_tx = '1') else '0';` via ctrl.sim_mode -- Simulation mode (ctrl.sim_mode) and tx_fifo.clear at line 259 (plus the sim_tx logging at line 499) provide an alternate path that redirects or suppresses normal TX behavior, effectively bypassing the physical TX FIFO -> UART output path.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_uart | sets | 19 -> 260 `tx_fifo.wdata <= bus_req_i.data(data_rtx_msb_c downto data_rtx_lsb_c);` | SOURCES tx_fifo.wdata | occurrence only | no SOURCES record to 'tx_fifo.wdata' at occurrence 19 | not listed |
| tx_fifo.wdata | neorv32_uart | sets | 3 -> 260 `tx_fifo.wdata <= bus_req_i.data(data_rtx_msb_c downto data_rtx_lsb_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| tx_engine.sreg | neorv32_uart | stores | 3 -> 351 `tx_engine.sreg    <= tx_fifo.rdata & '0';` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tx_engine.sreg <- tx_engine.baudcnt, tx_engine.state, uart_clk

## Concept: IRQ-generation policy and outputs (irq_rx_o / irq_tx_o and their selecting control bits)

- confidentiality: yes-assumed, line 208 `bus_rsp_o.data(ctrl_irq_rx_nempty_c)             <= ctrl.irq_rx_nempty;` via bus_rsp_o.data -- The IRQ control bits are returned on the bus (lines 208-212) and the IRQ outputs themselves (lines 270/315) reveal module status, so their values and implications are externally observable and may be sensitive.
- integrity: yes-rtl, line 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` via bus_req_i.data -- Bus writes at lines 185-189 update the irq-select control bits and those bits are used directly by the IRQ generation logic at lines 270 and 315 with no RTL protection to prevent changes during operation, allowing the IRQ policy to be altered at runtime.
- availability: yes-rtl, line 270 `irq_tx_o <= ctrl.enable and (` via ctrl.enable -- Both IRQ outputs are gated by ctrl.enable in their generator processes (e.g. irq_tx_o assigned under ctrl.enable at line 270 and irq_rx_o at line 315), so clearing ctrl.enable from the bus will suppress IRQs and stop interrupt notifications.
- undermined behavior: no, line 270 `irq_tx_o <= ctrl.enable and (` via irq_tx_o -- The IRQ outputs are driven only by the IRQ generator processes (lines 270 and 315) and the supplied RTL contains no alternate debug/test override path that selects a different driver for these outputs.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.irq_tx_empty | neorv32_uart | stores | 3 -> 188 `ctrl.irq_tx_empty  <= bus_req_i.data(ctrl_irq_tx_empty_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i | neorv32_uart | sets | 14 -> 188 `ctrl.irq_tx_empty  <= bus_req_i.data(ctrl_irq_tx_empty_c);` | SOURCES ctrl.irq_tx_empty | occurrence only | no SOURCES record to 'ctrl.irq_tx_empty' at occurrence 14 | not listed |
| irq_tx_o | neorv32_uart | exit port | 3 -> 270 `irq_tx_o <= ctrl.enable and (` | DERIVES_FROM ctrl.irq_tx_empty | verified |  | hit |
| ctrl.irq_rx_nempty | neorv32_uart | stores | 3 -> 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i | neorv32_uart | sets | 11 -> 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` | SOURCES ctrl.irq_rx_nempty | occurrence only | no SOURCES record to 'ctrl.irq_rx_nempty' at occurrence 11 | not listed |
| irq_rx_o | neorv32_uart | exit port | 3 -> 315 `irq_rx_o <= ctrl.enable and (` | DERIVES_FROM ctrl.irq_rx_nempty | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.irq_tx_empty <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; irq_tx_o <- ctrl.enable; ctrl.irq_rx_nempty <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; irq_rx_o <- ctrl.enable
