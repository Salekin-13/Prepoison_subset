# neorv32_spi

**Purpose (model):** SPI controller that accepts bus requests (bus_req_i), holds configuration in internal control registers, buffers transmit/receive bytes in FIFOs, runs an rtx_engine that shifts SPI data and controls chip-selects, generates the SPI clock and data outputs, and reports status/RX data and interrupts via bus_rsp_o and irq_o.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | control register fields (enable, cpha, cpol, prsc, cdiv, highspeed, irq enables) written from the bus |  | 14 / 14 |
| start | enqueue a transmit entry into the TX FIFO (wdata and we) which can start a transmission |  | 8 / 8 |
| operate | bitwise transmit/receive sequencing by the transceiver FSM (rtx_engine) gated by spi_clk_en and using ctrl settings (CPOL/CPHA), shifting sreg and sampling sdi |  | 27 / 27 |
| report | status and readback returned on the bus (bus_rsp_o.data) including FIFO status and ctrl fields |  | 20 / 20 |
| read out | RX FIFO readback to the bus (rx_fifo.re driven by bus reads) and RX data delivered to rx_fifo by rtx_engine.done |  | 5 / 5 |
| report | interrupt generation (irq_o) asserted from ctrl irq-enable bits gated with FIFO and engine status |  | 11 / 11 |
| reset | configuration and engine/FIFO control state cleared when rstn_i = '0' |  | 26 / 26 |

## Concept: Control configuration (ctrl.enable, ctrl.cpha, ctrl.cpol, ctrl.prsc, ctrl.cdiv, ctrl.highspeed, ctrl.irq_*) — the SPI-mode, clock selection and IRQ-enable settings the block stores


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.enable | neorv32_spi | stores | 3 -> 140 `ctrl.enable       <= bus_req_i.data(ctrl_en_c);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.cpha | neorv32_spi | stores | 3 -> 141 `ctrl.cpha         <= bus_req_i.data(ctrl_cpha_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl.cpol | neorv32_spi | stores | 3 -> 142 `ctrl.cpol         <= bus_req_i.data(ctrl_cpol_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl.prsc | neorv32_spi | stores | 3 -> 143 `ctrl.prsc         <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.cdiv | neorv32_spi | stores | 3 -> 144 `ctrl.cdiv         <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.highspeed | neorv32_spi | stores | 3 -> 145 `ctrl.highspeed    <= bus_req_i.data(ctrl_highspeed_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl.irq_rx_avail | neorv32_spi | stores | 3 -> 146 `ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl.irq_tx_empty | neorv32_spi | stores | 3 -> 147 `ctrl.irq_tx_empty <= bus_req_i.data(ctrl_irq_tx_empty_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl.irq_tx_nhalf | neorv32_spi | stores | 3 -> 148 `ctrl.irq_tx_nhalf <= bus_req_i.data(ctrl_irq_tx_nhalf_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl.irq_idle | neorv32_spi | stores | 3 -> 149 `ctrl.irq_idle     <= bus_req_i.data(ctrl_irq_idle_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| clkgen_en_o | neorv32_spi | exit port | 2 -> 383 `clkgen_en_o <= ctrl.enable;` | COPIES ctrl.enable | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.cpha <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.cpol <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.prsc <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.cdiv <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.highspeed <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_rx_avail <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_tx_empty <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_tx_nhalf <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_idle <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Transmit FIFO contents (words enqueued by the bus) that determine what is sent on SPI and whether an entry is a CS-control header

- confidentiality: yes-assumed, line 343 `spi_dat_o <= rtx_engine.sreg(7);` via spi_dat_o -- Words written into the TX FIFO from the bus (tx_fifo.wdata assigned at line 213) are eventually loaded into rtx_engine.sreg and driven out on spi_dat_o (line 343), so external observers on the SPI pins can learn FIFO contents.
- integrity: yes-assumed, line 213 `tx_fifo.wdata <= bus_req_i.data(31) & bus_req_i.data(7 downto 0);` via bus_req_i.data -- TX FIFO payload is written from bus_req_i.data at line 213; the FIFO contents therefore depend on an external bus writer and whether that writer is trusted depends on integration.
- availability: yes-rtl, line 212 `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i.stb / bus_req_i.rw / bus_req_i.addr -- Writes into the TX FIFO occur only when the bus write condition is asserted (tx_fifo.we at line 212), so an external master can withhold writes and prevent the FIFO from being populated, blocking transmissions.
- undermined behavior: yes-rtl, line 211 `tx_fifo.clear <= not ctrl.enable;` via ctrl.enable -- The FIFO clear input is driven by ctrl.enable (tx_fifo.clear <= not ctrl.enable at line 211), so disabling the core will clear/replace TX FIFO contents as a mode that bypasses normal FIFO contents.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tx_fifo.wdata | neorv32_spi | computes | 3 -> 213 `tx_fifo.wdata <= bus_req_i.data(31) & bus_req_i.data(7 downto 0);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| tx_fifo.we | neorv32_spi | sets | 3 -> 212 `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.ad` | GATED_BY bus_req_i.stb | verified |  | not listed |
| tx_fifo.rdata | neorv32_spi | computes | 2 -> 207 `rdata_o => tx_fifo.rdata,` | CONNECTS tx_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| rtx_engine.cs_ctrl | neorv32_spi | stores | 4 -> 290 `rtx_engine.cs_ctrl <= tx_fifo.rdata(3 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tx_fifo.we <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; rtx_engine.cs_ctrl <- rtx_engine.state, tx_fifo.avail, tx_fifo.rdata

## Concept: Chip-select control (rtx_engine.cs_ctrl) — the stored select bits that determine which SPI chip-select line is driven low


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rtx_engine.cs_ctrl | neorv32_spi | stores | 4 -> 290 `rtx_engine.cs_ctrl <= tx_fifo.rdata(3 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| tx_fifo.rdata | neorv32_spi | sets | 4 -> 290 `rtx_engine.cs_ctrl <= tx_fifo.rdata(3 downto 0);` | SOURCES rtx_engine.cs_ctrl | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage not assigned) | not listed |
| spi_csn_o | neorv32_spi | exit port | 4 -> 354 `spi_csn_o(to_integer(unsigned(rtx_engine.cs_ctrl(2 downto 0)))) <= '0';` | SELECTED_BY rtx_engine.cs_ctrl | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rtx_engine.cs_ctrl <- rtx_engine.state, tx_fifo.avail, tx_fifo.rdata; spi_csn_o <- rtx_engine.cs_ctrl

## Concept: Receive FIFO contents and delivered RX byte (rx_fifo) used for readback and IRQ decisions

- confidentiality: yes-assumed, line 174 `bus_rsp_o.data(7 downto 0) <= rx_fifo.rdata(7 downto 0);` via bus_rsp_o.data -- RX FIFO data is presented on the bus read path (bus_rsp_o.data <= rx_fifo.rdata at line 174), so received bytes are observable by a bus master and may be sensitive.
- integrity: yes-assumed, line 244 `rx_fifo.wdata <= '0' & rtx_engine.sreg;` via rtx_engine.sreg (driven from spi_dat_i) -- rx_fifo.wdata is derived from rtx_engine.sreg at line 244, and rtx_engine.sreg is populated from spi_dat_i (external SPI input), so external SPI peers can influence RX contents and trust depends on integration.
- availability: yes-rtl, line 245 `rx_fifo.we    <= rtx_engine.done;` via rtx_engine.done -- rx_fifo.we is asserted only when rtx_engine.done is asserted (line 245), and done requires the transceiver and clocking (spi_clk_en/bitcnt), so external conditions can prevent RX words from being written.
- undermined behavior: yes-rtl, line 243 `rx_fifo.clear <= not ctrl.enable;` via ctrl.enable -- rx_fifo.clear <= not ctrl.enable at line 243 clears the RX FIFO when ctrl.enable is cleared, providing a mode that erases received data under control of the enable bit.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rtx_engine.sreg | neorv32_spi | stores | 4 -> 292 `rtx_engine.sreg              <= tx_fifo.rdata(7 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| rx_fifo.wdata | neorv32_spi | computes | 3 -> 244 `rx_fifo.wdata <= '0' & rtx_engine.sreg;` | DERIVES_FROM rtx_engine.sreg | verified |  | not listed |
| rx_fifo.we | neorv32_spi | sets | 3 -> 245 `rx_fifo.we    <= rtx_engine.done;` | COPIES rtx_engine.done | verified |  | not listed |
| rx_fifo.rdata | neorv32_spi | computes | 3 -> 239 `rdata_o => rx_fifo.rdata,` | CONNECTS rx_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rtx_engine.sreg <- rtx_engine.state, spi_clk_en, tx_fifo.avail, tx_fifo.rdata

## Concept: Interrupt signal (irq_o) produced by the block from ctrl IRQ enables and FIFO/engine status

- confidentiality: yes-assumed, line 255 `irq_o <= ctrl.enable and (` via irq_o -- irq_o is driven out of the module at line 255 from internal status and ctrl.irq_* enables and thus reveals internal FIFO/engine conditions to external observers and may be treated as sensitive.
- integrity: yes-rtl, line 146 `ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c);` via bus_req_i.data -- IRQ generation uses ctrl.irq_rx_avail and other ctrl.irq_* bits which are written from the bus (e.g. ctrl.irq_rx_avail <= bus_req_i.data at line 146) and those writes are not blocked while irq_generator uses them (line 255), so bus writes can change IRQ behavior at runtime.
- availability: yes-rtl, line 255 `irq_o <= ctrl.enable and (` via ctrl.enable -- irq_o is gated by ctrl.enable at line 255; clearing ctrl.enable (writable by the bus at line 140) prevents irq_o from asserting and thus blocks interrupt delivery.
- undermined behavior: no, line 255 `irq_o <= ctrl.enable and (` via irq_o -- irq_o is produced only by the irq_generator assignment (line 255) and reset (line 253); no alternate debug/test driver or bypass is present to override irq_o.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| irq_o | neorv32_spi | exit port | 3 -> 255 `irq_o <= ctrl.enable and (` | DERIVES_FROM ctrl.irq_rx_avail | verified |  | hit |
| ctrl.irq_rx_avail | neorv32_spi | stores | 3 -> 146 `ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| rx_fifo.avail | neorv32_spi | computes | 3 -> 240 `avail_o => rx_fifo.avail` | CONNECTS rx_fifo_inst.avail_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): irq_o <- ctrl.enable; ctrl.irq_rx_avail <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: SPI external signals (spi_dat_o, spi_clk_o, spi_csn_o) that the core drives into the physical SPI lines

- confidentiality: yes-assumed, line 343 `spi_dat_o <= rtx_engine.sreg(7);` via spi_dat_o -- The module drives data onto the external SPI pins (spi_dat_o <= rtx_engine.sreg(7) at line 343) so transmitted data is externally observable and may be sensitive depending on integration.
- integrity: yes-rtl, line 213 `tx_fifo.wdata <= bus_req_i.data(31) & bus_req_i.data(7 downto 0);` via bus_req_i.data -- The data shifted out via spi_dat_o originates from TX FIFO payload which is written from bus_req_i.data at line 213, and those bus writes can change the transmitted bits at runtime.
- availability: yes-rtl, line 211 `tx_fifo.clear <= not ctrl.enable;` via ctrl.enable -- The transmit FIFO is cleared when ctrl.enable = '0' (tx_fifo.clear <= not ctrl.enable at line 211) and clock generation/transfers are gated by ctrl.enable, so external control of enable can stop SPI outputs.
- undermined behavior: no, line 343 `spi_dat_o <= rtx_engine.sreg(7);` via rtx_engine.sreg -- The SPI outputs are driven by the transceiver signals (lines 343-344 and chip_select 352-355) and reset; no separate debug/test override is present to replace these drivers.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| spi_dat_o | neorv32_spi | exit port | 2 -> 343 `spi_dat_o <= rtx_engine.sreg(7);` | DERIVES_FROM rtx_engine.sreg | verified |  | hit |
| spi_clk_o | neorv32_spi | exit port | 2 -> 344 `spi_clk_o <= rtx_engine.sck;` | COPIES rtx_engine.sck | verified |  | not listed |
| spi_csn_o | neorv32_spi | exit port | 4 -> 354 `spi_csn_o(to_integer(unsigned(rtx_engine.cs_ctrl(2 downto 0)))) <= '0';` | SELECTED_BY rtx_engine.cs_ctrl | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): spi_csn_o <- rtx_engine.cs_ctrl

## Concept: SPI bit-clock gating and generation state (cdiv_cnt, spi_clk_en) that enables rtx_engine progress

- confidentiality: yes-assumed, line 344 `spi_clk_o <= rtx_engine.sck;` via spi_clk_o -- cdiv_cnt/spi_clk_en determine the SPI bit clock which is visible externally on spi_clk_o (line 344), so timing and derived state can be observed outside the module.
- integrity: yes-rtl, line 144 `ctrl.cdiv         <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` via bus_req_i.data -- ctrl.cdiv is written from bus_req_i.data at line 144 and is used as the compare target in the clock generator (line 372), so bus writes can change clock timing while the counter is operating.
- availability: yes-rtl, line 371 `elsif (clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1') or (ctrl.highspeed = '1') then` via clkgen_i / ctrl.highspeed -- spi_clk_en is produced only when (clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1') or ctrl.highspeed = '1' (line 371), so external clkgen_i or the bus-writable ctrl.highspeed can block or force clock pulses and thus availability.
- undermined behavior: yes-rtl, line 371 `elsif (clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1') or (ctrl.highspeed = '1') then` via ctrl.highspeed -- The clock generator includes an override mode (ctrl.highspeed) at line 371 that can produce spi_clk_en independently of clkgen_i, allowing a mode to bypass the normal prescaler path.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cdiv_cnt | neorv32_spi | stores | 3 -> 370 `cdiv_cnt <= (others => '0');` | CLOCKED_BY clk_i | verified |  | not listed |
| spi_clk_en | neorv32_spi | stores | 6 -> 368 `spi_clk_en <= '0';` | CLOCKED_BY clk_i | verified |  | not listed |
| clkgen_i | neorv32_spi | sets | 2 -> 371 `elsif (clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1') or (ctrl.highspeed = '1') then` | GATES cdiv_cnt | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): cdiv_cnt <- cdiv_cnt, clkgen_i, ctrl.cdiv, ctrl.enable, ctrl.highspeed, ctrl.prsc; spi_clk_en <- cdiv_cnt, clkgen_i, ctrl.cdiv, ctrl.enable, ctrl.highspeed, ctrl.prsc

## Concept: Transceiver internal state (rtx_engine.state, rtx_engine.bitcnt, rtx_engine.sreg) that sequences SPI transfers

- confidentiality: yes-assumed, line 172 `bus_rsp_o.data(ctrl_busy_c)      <= rtx_engine.busy or tx_fifo.avail;` via bus_rsp_o.data -- The transceiver state is observable indirectly (rtx_engine.busy is exposed in bus_rsp_o.data at line 172) and by external SPI pins and IRQs, so FSM progress/state can be inferred by observers and may be sensitive.
- integrity: yes-rtl, line 140 `ctrl.enable       <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- rtx_engine.state(2) is driven from ctrl.enable at line 281 and ctrl.enable is writable from the bus at line 140, so bus writes can change FSM state bits while the FSM operates.
- availability: yes-rtl, line 299 `if (spi_clk_en = '1') then` via spi_clk_en -- Many state transitions wait for spi_clk_en = '1' (e.g. the 'when "101"' branch checks spi_clk_en at line 299), and spi_clk_en depends on external inputs (clkgen_i) and ctrl settings, so external conditions can block FSM progress.
- undermined behavior: no, line 281 `rtx_engine.state(2) <= ctrl.enable;` via rtx_engine.state -- The transceiver FSM state is driven solely by its internal process (lines 281, 286-326) and the ctrl.enable input; there is no separate debug/test override to substitute a different driver.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rtx_engine.state | neorv32_spi | stores | 4 -> 281 `rtx_engine.state(2) <= ctrl.enable;` | CLOCKED_BY clk_i | verified |  | not listed |
| rtx_engine.bitcnt | neorv32_spi | stores | 4 -> 311 `rtx_engine.bitcnt            <= std_ulogic_vector(unsigned(rtx_engine.bitcnt) + 1);` | CLOCKED_BY clk_i | verified |  | not listed |
| rtx_engine.sreg | neorv32_spi | stores | 4 -> 292 `rtx_engine.sreg              <= tx_fifo.rdata(7 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rtx_engine.state <- rtx_engine.bitcnt, rtx_engine.state, spi_clk_en, tx_fifo.avail, tx_fifo.rdata; rtx_engine.bitcnt <- rtx_engine.state, spi_clk_en; rtx_engine.sreg <- rtx_engine.state, spi_clk_en, tx_fifo.avail, tx_fifo.rdata
