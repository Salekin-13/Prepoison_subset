# neorv32_uart

**Purpose (model):** UART peripheral that services a bus: it decodes bus read/write accesses to control and data registers, provides TX and RX FIFOs, runs transmit and receive engines driven by a selected uart clock, presents status and interrupts (irq_tx_o, irq_rx_o), and supports hardware flow-control (CTS/RTS).

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | control register values written from the bus (enable, sim_mode, hwfc_en, prsc, baud, IRQ masks, clr_rx, clr_tx) |  | 15 / 15 |
| start | host write of a transmit byte into the TX FIFO (bus -> tx_fifo.wdata and tx_fifo.we) |  | 3 / 3 |
| operate | transmit operation: tx_engine loads a FIFO byte into sreg, clocks bits out with uart_clk and drives uart_txd_o |  | 12 / 12 |
| operate | receive operation: uart_rxd sampled into rx_engine.sreg, assembled into a byte and pushed into RX FIFO |  | 12 / 12 |
| report | interrupt outputs and bus-status reporting (irq_tx_o, irq_rx_o and bus_rsp_o.data status fields) |  | 18 / 18 |
| read out | bus read returns: control/status fields or RX FIFO readback (rx_fifo.rdata -> bus_rsp_o.data) and rx_fifo.re |  | 15 / 15 |
| reset | reset forces control registers, engine state and FIFOs to known values (rstn_i = '0' arms in processes) |  | 36 / 36 |

## Concept: Bus access predicates that decide which internal register or FIFO field a bus transaction addresses (strobe, read/write, addr[2])

- confidentiality: no, line 170 `bus_rsp_o.ack  <= bus_req_i.stb;` via bus_rsp_o.ack -- bus_req_i.stb is copied directly to the bus response ack (bus_rsp_o.ack <= bus_req_i.stb at line 170) and the predicates are only observed by the bus interface that supplied them.
- integrity: yes-assumed, line 176 `if (bus_req_i.stb = '1') then` via bus_req_i -- The predicates are inputs driven by the external bus and the RTL uses them (e.g. 'if (bus_req_i.stb = ''1'')' at line 176) without internal protection, so whether the writer is trusted depends on integration.
- availability: yes-rtl, line 176 `if (bus_req_i.stb = '1') then` via bus_req_i.stb -- The bus_access process executes read/write routing only when bus_req_i.stb = '1' (line 176), so absence or control of stb by an external actor can prevent bus operations and block progress.
- undermined behavior: no, line 34 `bus_req_i   : in  bus_req_t;` via bus_req_i -- The predicate signals are only driven by the bus_req_i port (port declaration at line 34) and the RTL contains no alternate debug/test override that replaces these inputs.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i.addr | neorv32_uart | sets | 2 -> 178 `if (bus_req_i.addr(2) = '0') then` | GATES ctrl.enable | verified |  | not listed |
| bus_req_i.rw | neorv32_uart | sets | 2 -> 177 `if (bus_req_i.rw = '1') then` | GATES ctrl.baud | verified |  | not listed |
| bus_req_i.stb | neorv32_uart | sets | 2 -> 170 `bus_rsp_o.ack  <= bus_req_i.stb;` | CARRIES bus_rsp_o.ack | verified |  | not listed |

## Concept: Control-register configuration (enable, sim_mode, hwfc_en, prsc, baud, IRQ mask bits, clr_rx, clr_tx) that defines UART operating mode, clock selection, flow-control and IRQ policy

- confidentiality: yes-assumed, line 195 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` via bus_rsp_o.data -- Control registers are read back onto bus_rsp_o.data (e.g. ctrl.enable returned at line 195) so their values are observable externally and should be treated as potentially confidential depending on integration.
- integrity: yes-rtl, line 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` via bus_req_i.data -- Control fields (for example ctrl.baud <= bus_req_i.data at line 183) are written by bus accesses with no protection against writes while the TX/RX engines use them (e.g. ctrl.baud is loaded into tx_engine.baudcnt at line 349), so they can be changed during operation.
- availability: yes-rtl, line 344 `tx_engine.state(2) <= ctrl.enable;` via ctrl.enable -- ctrl.enable drives engine activity (tx_engine.state(2) <= ctrl.enable at line 344) and clearing it or writing it externally disables engine progress and triggers FIFO clears (see line 259), so external writes can stop operations.
- undermined behavior: no, line 179 `ctrl.enable        <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- Each control field has a single driver from the bus_access write path (e.g. ctrl.enable <= bus_req_i.data at line 179) and there is no alternate debug/test assignment that replaces these control writes.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.enable | neorv32_uart | sets | 3 -> 179 `ctrl.enable        <= bus_req_i.data(ctrl_en_c);` | DERIVES_FROM bus_req_i.data | verified |  | hit |
| ctrl.sim_mode | neorv32_uart | sets | 3 -> 180 `ctrl.sim_mode      <= bus_req_i.data(ctrl_sim_en_c) and bool_to_ulogic_f(sim_mode_en_c);` | DERIVES_FROM bus_req_i.data | occurrence only | no DERIVES_FROM record to 'bus_req_i.data' at occurrence 3 | not listed |
| ctrl.hwfc_en | neorv32_uart | sets | 3 -> 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| ctrl.prsc | neorv32_uart | sets | 3 -> 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | DERIVES_FROM bus_req_i.data | verified |  | hit |
| ctrl.baud | neorv32_uart | sets | 3 -> 183 `ctrl.baud          <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c);` | DERIVES_FROM bus_req_i.data | verified |  | hit |
| ctrl.clr_rx | neorv32_uart | sets | 4 -> 190 `ctrl.clr_rx        <= bus_req_i.data(ctrl_rx_clr_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| ctrl.clr_tx | neorv32_uart | sets | 4 -> 191 `ctrl.clr_tx        <= bus_req_i.data(ctrl_tx_clr_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| ctrl.irq_rx_nempty | neorv32_uart | sets | 3 -> 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| ctrl.irq_tx_empty | neorv32_uart | sets | 3 -> 188 `ctrl.irq_tx_empty  <= bus_req_i.data(ctrl_irq_tx_empty_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.sim_mode <- bus_req_i.addr, bus_req_i.data, bus_req_i.rw, bus_req_i.stb; ctrl.hwfc_en <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.prsc <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.baud <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.clr_rx <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.clr_tx <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_rx_nempty <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_tx_empty <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Transmit data bytes (host-supplied bytes written into the TX FIFO and consumed by the transmitter to produce uart_txd_o)

- confidentiality: yes-assumed, line 392 `uart_txd_o <= tx_engine.txd;` via uart_txd_o -- Host-supplied bytes written to the TX FIFO are shifted out and appear on the uart_txd_o port (assignment at line 392) and (in sim mode) are logged to a file (lines 501-512), so their contents are observable outside the IP.
- integrity: yes-assumed, line 260 `tx_fifo.wdata <= bus_req_i.data(data_rtx_msb_c downto data_rtx_lsb_c);` via bus_req_i.data -- The TX data bytes are written by external bus transactions (tx_fifo.wdata <= bus_req_i.data at line 260) and the RTL does not prevent writes or clears (line 259) by the bus master, so whether the writer is trusted depends on integration.
- availability: yes-rtl, line 359 `((tx_engine.cts(1) = '0') or (ctrl.hwfc_en = '0')) then` via uart_ctsn_i -- Transmission progression is gated by CTS and hwfc (the transmitter only advances when '(tx_engine.cts(1) = ''0'') or (ctrl.hwfc_en = ''0'')' at line 359), so the external CTS line (uart_ctsn_i) or hwfc configuration can stall output and prevent progress.
- undermined behavior: yes-rtl, line 259 `tx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_tx = '1') else '0';` via ctrl.sim_mode -- Simulation or control modes can change the TX data path: tx_fifo.clear is asserted when ctrl.sim_mode = '1' (line 259), which clears pending TX data and alters behavior.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i.data | neorv32_uart | sets | 14 -> 260 `tx_fifo.wdata <= bus_req_i.data(data_rtx_msb_c downto data_rtx_lsb_c);` | SOURCES tx_fifo.wdata | verified |  | not listed |
| tx_fifo.wdata | neorv32_uart | sets | 3 -> 260 `tx_fifo.wdata <= bus_req_i.data(data_rtx_msb_c downto data_rtx_lsb_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| tx_fifo.we | neorv32_uart | sets | 3 -> 261 `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.ad` | GATED_BY bus_req_i.stb | verified |  | not listed |
| tx_engine.sreg | neorv32_uart | stores | 3 -> 351 `tx_engine.sreg    <= tx_fifo.rdata & '0';` | CLOCKED_BY clk_i | verified |  | not listed |
| uart_txd_o | neorv32_uart | exit port | 2 -> 392 `uart_txd_o <= tx_engine.txd;` | COPIES tx_engine.txd | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tx_fifo.we <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; tx_engine.sreg <- tx_engine.baudcnt, tx_engine.state, uart_clk

## Concept: Received data bytes (serial input sampled and assembled by rx_engine then stored into RX FIFO for bus readout)

- confidentiality: yes-assumed, line 217 `bus_rsp_o.data(data_rtx_msb_c        downto data_rtx_lsb_c)        <= rx_fifo.rdata;` via bus_rsp_o.data -- Completed received bytes are stored in the RX FIFO and are returned to the bus master via bus_rsp_o.data (rx_fifo.rdata copied at line 217), so their contents are externally observable and should be treated as potentially confidential.
- integrity: yes-assumed, line 305 `rx_fifo.wdata <= rx_engine.sreg(7 downto 0);` via rx_engine.sreg -- The RX FIFO data is produced from the receiver (rx_fifo.wdata <= rx_engine.sreg at line 305) which ultimately derives from the serial input (uart_rxd_i), so the FIFO contents depend on an external writer (the serial source) and trust depends on integration.
- availability: yes-rtl, line 304 `rx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_rx = '1') else '0';` via ctrl.enable -- rx_fifo.clear is asserted when ctrl.enable = '0' or ctrl.sim_mode = '1' or ctrl.clr_rx = '1' (line 304), so external writes to control fields can clear the RX FIFO and prevent readout or reception progress.
- undermined behavior: yes-rtl, line 304 `rx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_rx = '1') else '0';` via ctrl.sim_mode -- A special mode (sim_mode) and control clears affect the RX path (rx_fifo.clear includes ctrl.sim_mode and ctrl.clr_rx at line 304), providing alternate assignments that change stored RX data behavior.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| uart_rxd_i | neorv32_uart | sets | 2 -> 408 `rx_engine.sync(2) <= uart_rxd_i;` | CARRIES rx_engine.sync | verified |  | hit |
| rx_engine.sreg | neorv32_uart | stores | 4 -> 434 `rx_engine.sreg    <= rx_engine.sync(2) & rx_engine.sreg(rx_engine.sreg'left downto 1);` | CLOCKED_BY clk_i | verified |  | not listed |
| rx_fifo.wdata | neorv32_uart | sets | 3 -> 305 `rx_fifo.wdata <= rx_engine.sreg(7 downto 0);` | DERIVES_FROM rx_engine.sreg | verified |  | not listed |
| rx_engine.done | neorv32_uart | computes | 2 -> 306 `rx_fifo.we    <= rx_engine.done;` | CARRIES rx_fifo.we | edge, role unfit | CARRIES does not demonstrate 'computes' | not listed |
| bus_rsp_o.data | neorv32_uart | exit port | 21 -> 217 `bus_rsp_o.data(data_rtx_msb_c        downto data_rtx_lsb_c)        <= rx_fifo.rdata;` | COPIES rx_fifo.rdata | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rx_engine.sreg <- rx_engine.baudcnt, rx_engine.state, uart_clk; rx_engine.done <- rx_engine.bitcnt, rx_engine.state; bus_rsp_o.data <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, ctrl.sim_mode, tx_engine.busy, tx_fifo.avail

## Concept: Interrupt-decision (IRQ mask bits and the irq_tx_o / irq_rx_o outputs) that reports TX/RX conditions to the system

- confidentiality: yes-assumed, line 208 `bus_rsp_o.data(ctrl_irq_rx_nempty_c)             <= ctrl.irq_rx_nempty;` via bus_rsp_o.data -- IRQ mask bits are returned on bus reads (e.g. bus_rsp_o.data at line 208 returns ctrl.irq_rx_nempty) and the IRQ outputs are externally observable, so mask state can be learned and should be treated as potentially confidential.
- integrity: yes-rtl, line 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` via bus_req_i.data -- IRQ mask bits are written directly by bus transactions (e.g. ctrl.irq_rx_nempty <= bus_req_i.data at line 185) and the IRQ outputs use these fields immediately (irq logic at line 315), so masks can be changed while interrupts are active.
- availability: yes-rtl, line 270 `irq_tx_o <= ctrl.enable and (` via ctrl.enable -- Both irq_tx_o and irq_rx_o are gated by ctrl.enable in their generators (irq_tx_o assigned at line 270 and irq_rx_o at line 315), so clearing ctrl.enable externally suppresses interrupts and affects availability of IRQ notifications.
- undermined behavior: no, line 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` via bus_req_i.data -- IRQ mask bits have a single driver path from bus writes (e.g. line 185) and there is no alternate debug/test override assignment in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.irq_tx_empty | neorv32_uart | sets | 3 -> 188 `ctrl.irq_tx_empty  <= bus_req_i.data(ctrl_irq_tx_empty_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| ctrl.irq_tx_nhalf | neorv32_uart | sets | 3 -> 189 `ctrl.irq_tx_nhalf  <= bus_req_i.data(ctrl_irq_tx_nhalf_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| irq_tx_o | neorv32_uart | exit port | 3 -> 270 `irq_tx_o <= ctrl.enable and (` | DERIVES_FROM ctrl.irq_tx_empty | verified |  | hit |
| ctrl.irq_rx_nempty | neorv32_uart | sets | 3 -> 185 `ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| irq_rx_o | neorv32_uart | exit port | 3 -> 315 `irq_rx_o <= ctrl.enable and (` | DERIVES_FROM ctrl.irq_rx_nempty | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.irq_tx_empty <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_tx_nhalf <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; irq_tx_o <- ctrl.enable; ctrl.irq_rx_nempty <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; irq_rx_o <- ctrl.enable

## Concept: Hardware flow-control policy and handshake (CTS input and RTS output) that permits or blocks transmission

- confidentiality: no, line 197 `bus_rsp_o.data(ctrl_hwfc_en_c)                   <= ctrl.hwfc_en;` via bus_rsp_o.data -- hwfc configuration (ctrl.hwfc_en) is returned on bus reads (line 197) and the handshake lines (CTS/RTS) are external I/O, so the policy/state is not kept secret by the IP.
- integrity: yes-rtl, line 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` via bus_req_i.data -- hwfc enable (ctrl.hwfc_en <= bus_req_i.data at line 181) can be written by the bus while transmission is ongoing and is used immediately in transmitter gating (see line 359), so the setting can be changed during use.
- availability: yes-rtl, line 359 `((tx_engine.cts(1) = '0') or (ctrl.hwfc_en = '0')) then` via uart_ctsn_i -- Transmission progression is gated by the CTS line (the transmitter checks '(tx_engine.cts(1) = ''0'') or (ctrl.hwfc_en = ''0'')' at line 359), so the external CTS input (uart_ctsn_i) can block transmission and prevent progress.
- undermined behavior: no, line 337 `tx_engine.cts <= tx_engine.cts(0) & uart_ctsn_i;` via uart_ctsn_i -- CTS is sampled only from the external uart_ctsn_i input into tx_engine.cts (line 337) and hwfc control is written only via the bus (line 181); there is no alternate override/debug path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.hwfc_en | neorv32_uart | sets | 3 -> 181 `ctrl.hwfc_en       <= bus_req_i.data(ctrl_hwfc_en_c);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| uart_ctsn_i | neorv32_uart | sets | 2 -> 337 `tx_engine.cts <= tx_engine.cts(0) & uart_ctsn_i;` | SOURCES tx_engine.cts | verified |  | hit |
| tx_engine.cts | neorv32_uart | stores | 3 -> 337 `tx_engine.cts <= tx_engine.cts(0) & uart_ctsn_i;` | DERIVES_FROM uart_ctsn_i | edge, role unfit | DERIVES_FROM does not demonstrate 'stores' (mode None, storage edge) | not listed |
| uart_rtsn_o | neorv32_uart | exit port | 3 -> 475 `uart_rtsn_o <= '1';` | GATED_BY rx_fifo.half | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.hwfc_en <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; uart_rtsn_o <- ctrl.enable, ctrl.hwfc_en, rx_fifo.half

## Concept: RX FIFO overrun flag (rx_engine.over) that records an overflow event and is reported to the bus

- confidentiality: yes-assumed, line 214 `bus_rsp_o.data(ctrl_rx_over_c)                   <= rx_engine.over;` via bus_rsp_o.data -- The overrun flag is explicitly exposed to the bus (bus_rsp_o.data <= rx_engine.over at line 214) so its value is externally observable and should be treated as potentially sensitive status.
- integrity: yes-rtl, line 459 `rx_engine.over <= '0';` via ctrl.enable -- fifo_overrun clears rx_engine.over when ctrl.enable = '0' (line 459), so an external write to ctrl.enable can clear the overrun indicator while it is intended to record an event.
- availability: yes-rtl, line 459 `rx_engine.over <= '0';` via ctrl.enable -- Because fifo_overrun either clears or sets rx_engine.over based on ctrl.enable and FIFO signals (lines 459-461), external control of ctrl.enable (or the FIFO interface) can force or suppress the overrun indicator and affect availability of that status.
- undermined behavior: no, line 461 `rx_engine.over <= '1';` via fifo_overrun process -- rx_engine.over is driven only by the local fifo_overrun process (the assignments at lines 459 and 461) and there is no alternate debug/test assignment that replaces that behavior.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rx_engine.over | neorv32_uart | stores | 2 -> 214 `bus_rsp_o.data(ctrl_rx_over_c)                   <= rx_engine.over;` | CARRIES bus_rsp_o.data | edge, role unfit | CARRIES does not demonstrate 'stores' (mode None, storage edge) | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rx_engine.over <- ctrl.enable, rx_fifo.free, rx_fifo.we

## Concept: Selected UART sampling/bit clock (uart_clk) derived from clkgen_i and ctrl.prsc that times bit sampling and shifting

- confidentiality: yes-assumed, line 392 `uart_txd_o <= tx_engine.txd;` via uart_txd_o -- The selected uart_clk controls the timing of bit shifts/sampling and that timing appears on the serial output (uart_txd_o at line 392), so the chosen clock can be inferred externally and should be considered potentially sensitive.
- integrity: yes-rtl, line 182 `ctrl.prsc          <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` via bus_req_i.data -- The clock selection index ctrl.prsc is written from the bus (ctrl.prsc <= bus_req_i.data at line 182) and can be changed while the engines use uart_clk (selected at line 229), so the clock selection can be altered during operation.
- availability: yes-rtl, line 229 `uart_clk    <= clkgen_i(to_integer(unsigned(ctrl.prsc)));` via ctrl.prsc / clkgen_i -- uart_clk is selected as clkgen_i(to_integer(unsigned(ctrl.prsc))) at line 229, so an external change to clkgen_i or to ctrl.prsc can cause uart_clk to stop toggling or change rate and thereby prevent the bit engines from progressing.
- undermined behavior: no, line 229 `uart_clk    <= clkgen_i(to_integer(unsigned(ctrl.prsc)));` via clkgen_i/ctrl.prsc -- uart_clk has a single assignment that selects one bit of clkgen_i by index ctrl.prsc (line 229); there is no alternate debug/test path in the RTL that substitutes a different source.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| uart_clk | neorv32_uart | computes | 2 -> 229 `uart_clk    <= clkgen_i(to_integer(unsigned(ctrl.prsc)));` | SELECTED_BY ctrl.prsc | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): uart_clk <- ctrl.prsc
