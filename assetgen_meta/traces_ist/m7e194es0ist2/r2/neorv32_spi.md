# neorv32_spi

**Purpose (model):** SPI controller: it maps bus transactions to internal control registers and TX/RX FIFOs, runs a transmit/receive engine that generates SPI clock, MOSI and chip-select outputs and samples MISO, and provides bus responses and an interrupt output.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | control registers (enable, cpha, cpol, prsc, cdiv, highspeed and IRQ mask bits) written from bus_req_i.data |  | 13 / 13 |
| start | enqueue transmit word into TX FIFO (tx_fifo.wdata) and assert write (tx_fifo.we) to begin a transfer; transceiver reads FIFO when in start state |  | 8 / 8 |
| operate | rtx_engine state-machine sequences SPI bit transfers: toggling sck, shifting sreg, sampling spi_dat_i and driving spi_dat_o/spi_clk_o/spi_csn_o |  | 14 / 14 |
| report | interrupt output irq_o driven from ctrl.* IRQ enables and FIFO / engine status |  | 7 / 7 |
| read out | bus reads return control register fields, FIFO status or RX FIFO data via bus_rsp_o.data and ack via bus_rsp_o.ack |  | 13 / 13 |
| reset | control registers, FIFOs and transceiver state cleared when rstn_i = '0' |  | 28 / 28 |

## Concept: SPI enable configuration (ctrl.enable) that gates FIFO clears, clock generation and overall SPI activity

- confidentiality: yes-assumed, line 153 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` via bus_rsp_o -- ctrl.enable is copied into the bus response at line 153 (and also exported on clkgen_en_o and affects irq/spi outputs), so external observers can learn its value.
- integrity: yes-rtl, line 140 `ctrl.enable       <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- ctrl.enable is written directly from the bus at line 140 under the bus request guard and that write is not blocked while FIFOs are cleared (line 211/243) or the clock generator and transceiver use it (line 369/281), so external writes can change it during operation.
- availability: yes-rtl, line 369 `if (ctrl.enable = '0') then` via bus_req_i -- the clock generator checks ctrl.enable at line 369 and will not advance the divider or assert spi_clk_en when ctrl.enable='0', and ctrl.enable is controllable by bus writes (line 140), so an external write can prevent SPI progress.
- undermined behavior: no, line 140 `ctrl.enable       <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- ctrl.enable only has the documented bus write (line 140) and reset driver (line 120) in the RTL and there is no alternate debug/test override provided.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.enable | neorv32_spi | stores | 3 -> 140 `ctrl.enable       <= bus_req_i.data(ctrl_en_c);` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: SPI phase and polarity configuration (ctrl.cpha, ctrl.cpol) that determine SCK transitions and sampling points

- confidentiality: yes-assumed, line 154 `bus_rsp_o.data(ctrl_cpha_c)                      <= ctrl.cpha;` via bus_rsp_o -- ctrl.cpha and ctrl.cpol are copied to the bus response at lines 154/155 and they also affect externally observable SCK timing, so their values can be learned outside the module.
- integrity: yes-rtl, line 141 `ctrl.cpha         <= bus_req_i.data(ctrl_cpha_c);` via bus_req_i.data -- these bits are written directly from the bus at lines 141/142 under the bus request guard and those writes are not prevented during active transfers while the transceiver uses them to select SCK transitions (e.g., line 301/309), so external writes can alter timing correctness.
- availability: no, line 141 `ctrl.cpha         <= bus_req_i.data(ctrl_cpha_c);` via bus_req_i.data -- there is no RTL condition that an external input uses to freeze or block the block by manipulating cpha/cpol; they are simply configuration registers updated by bus writes (lines 141/142).
- undermined behavior: no, line 141 `ctrl.cpha         <= bus_req_i.data(ctrl_cpha_c);` via bus_req_i.data -- ctrl.cpha and ctrl.cpol have a single documented driver (bus writes at lines 141/142 and reset at 121/122) and no alternate debug/test override is present in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.cpha | neorv32_spi | stores | 3 -> 141 `ctrl.cpha         <= bus_req_i.data(ctrl_cpha_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl.cpol | neorv32_spi | stores | 3 -> 142 `ctrl.cpol         <= bus_req_i.data(ctrl_cpol_c);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.cpha <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.cpol <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: SPI clock configuration (ctrl.prsc, ctrl.cdiv, ctrl.highspeed) that determine spi_clk_en and the generated SPI bit rate

- confidentiality: yes-assumed, line 156 `bus_rsp_o.data(ctrl_prsc2_c downto ctrl_prsc0_c) <= ctrl.prsc;` via bus_rsp_o -- prescaler/divider/highspeed registers are copied to bus_rsp_o.data at lines 156-158 and they determine externally visible SPI bit timing, so their values are observable outside the module.
- integrity: yes-rtl, line 144 `ctrl.cdiv         <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` via bus_req_i.data -- ctrl.cdiv (and ctrl.prsc/ctrl.highspeed) are written directly from the bus at lines 144/143/145 and the clock_generator compares cdiv_cnt to ctrl.cdiv and uses ctrl.prsc/ctrl.highspeed at lines 371-377, so bus writes can change spi_clk_en/bit timing at runtime without write-protection.
- availability: yes-rtl, line 371 `elsif (clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1') or (ctrl.highspeed = '1') then` via clkgen_i -- the clock generator requires clkgen_i(to_integer(unsigned(ctrl.prsc)))='1' or ctrl.highspeed='1' to advance the divider and assert spi_clk_en (line 371), so an external clkgen_i input (or control of ctrl.highspeed via the bus) can block or force SPI clock generation and thus affect progress.
- undermined behavior: no, line 144 `ctrl.cdiv         <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` via bus_req_i.data -- the prescaler/divider/highspeed fields are only driven by documented bus writes (lines 143-145) and reset, and no alternate debug/test override is present in RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.prsc | neorv32_spi | stores | 3 -> 143 `ctrl.prsc         <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.cdiv | neorv32_spi | stores | 3 -> 144 `ctrl.cdiv         <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.highspeed | neorv32_spi | stores | 3 -> 145 `ctrl.highspeed    <= bus_req_i.data(ctrl_highspeed_c);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.prsc <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.cdiv <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.highspeed <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Transmitted frame entries enqueued to the TX FIFO (MSB = control/CS flag and lower 8-bit payload) that determine outgoing MOSI bytes and CS selection

- confidentiality: yes-assumed, line 343 `spi_dat_o <= rtx_engine.sreg(7);` via spi_dat_o -- TX FIFO entries are constructed from bus_req_i.data at line 213 and subsequently drive the external MOSI output spi_dat_o at line 343, so transmitted payload is observable externally.
- integrity: yes-assumed, line 213 `tx_fifo.wdata <= bus_req_i.data(31) & bus_req_i.data(7 downto 0);` via bus_req_i.data -- TX FIFO contents are written from the bus at line 213 when tx_fifo.we is asserted (line 212) so the RTL shows an external writer for the transmitted words and trust in that writer depends on integration.
- availability: yes-rtl, line 212 `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i -- tx_fifo.we is driven by the bus request condition at line 212 and tx_fifo.clear is driven by ctrl.enable at line 211, so external actors can fill, withhold or clear the TX FIFO (or repeatedly write) and thereby block or starve transmissions.
- undermined behavior: no, line 212 `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i -- the TX FIFO data path is driven by the bus write (lines 212-213) and the FIFO sub-unit; there is no separate debug/test override in the RTL that substitutes or bypasses these drivers.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tx_fifo.wdata | neorv32_spi | sets | 3 -> 213 `tx_fifo.wdata <= bus_req_i.data(31) & bus_req_i.data(7 downto 0);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| tx_fifo.we | neorv32_spi | sets | 3 -> 212 `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.ad` | GATED_BY bus_req_i.stb | verified |  | not listed |
| tx_fifo.rdata | neorv32_spi | computes | 2 -> 207 `rdata_o => tx_fifo.rdata,` | CONNECTS tx_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| rtx_engine.sreg | neorv32_spi | stores | 5 -> 318 `rtx_engine.sreg <= rtx_engine.sreg(6 downto 0) & rtx_engine.sdi_sync;` | CLOCKED_BY clk_i | verified |  | not listed |
| spi_dat_o | neorv32_spi | exit port | 2 -> 343 `spi_dat_o <= rtx_engine.sreg(7);` | DERIVES_FROM rtx_engine.sreg | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tx_fifo.we <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; rtx_engine.sreg <- rtx_engine.state, spi_clk_en, tx_fifo.avail, tx_fifo.rdata

## Concept: Chip-select selection (rtx_engine.cs_ctrl) and the driven chip-select outputs (spi_csn_o)

- confidentiality: yes-assumed, line 354 `spi_csn_o(to_integer(unsigned(rtx_engine.cs_ctrl(2 downto 0)))) <= '0';` via spi_csn_o -- rtx_engine.cs_ctrl is used to drive the external chip-select outputs at lines 352-354 (and its top bit is read back at line 171), so external observers can learn the selection values.
- integrity: yes-rtl, line 290 `rtx_engine.cs_ctrl <= tx_fifo.rdata(3 downto 0);` via tx_fifo.rdata -- cs_ctrl is loaded from tx_fifo.rdata at line 290 when the transceiver starts a frame (state="100" and tx_fifo.avail), and the FIFO contents originate from bus writes (line 213), so external writes can cause mis-selection of chip-selects during operation.
- availability: yes-rtl, line 281 `rtx_engine.state(2) <= ctrl.enable;` via ctrl.enable -- rtx_engine.state(2) is driven from ctrl.enable at line 281 and clearing ctrl.enable (writable by the bus at line 140) forces the engine into idle/other paths (lines 331-333) and the chip_select logic drives spi_csn_o inactive (line 352), so an external write can deassert CS and prevent peripheral access.
- undermined behavior: no, line 290 `rtx_engine.cs_ctrl <= tx_fifo.rdata(3 downto 0);` via tx_fifo.rdata -- the only drivers for cs_ctrl in the RTL are the transceiver assignments (line 290) and the reset/idle defaults (lines 275,332); no alternate debug/test bypass is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rtx_engine.cs_ctrl | neorv32_spi | stores | 4 -> 290 `rtx_engine.cs_ctrl <= tx_fifo.rdata(3 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| spi_csn_o | neorv32_spi | exit port | 4 -> 354 `spi_csn_o(to_integer(unsigned(rtx_engine.cs_ctrl(2 downto 0)))) <= '0';` | SELECTED_BY rtx_engine.cs_ctrl | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rtx_engine.cs_ctrl <- rtx_engine.state, tx_fifo.avail, tx_fifo.rdata; spi_csn_o <- rtx_engine.cs_ctrl

## Concept: Received data queued in RX FIFO (rx_fifo.wdata / rx_fifo.we / rx_fifo.rdata) and its readback to the bus

- confidentiality: yes-assumed, line 174 `bus_rsp_o.data(7 downto 0) <= rx_fifo.rdata(7 downto 0);` via bus_rsp_o -- rx_fifo.rdata is connected to the bus response at line 174 when the RX read address is selected, so received payload stored in the RX FIFO is exposed to the requester and can be learned externally.
- integrity: yes-assumed, line 244 `rx_fifo.wdata <= '0' & rtx_engine.sreg;` via rtx_engine.sreg / spi_dat_i -- RX FIFO writes are driven by the transceiver at lines 244-245 (rx_fifo.wdata from rtx_engine.sreg and rx_fifo.we from rtx_engine.done) and the source of rtx_engine.sreg is the external MISO input (spi_dat_i), so the RTL shows an external-influenced writer and trust in that writer depends on integration.
- availability: yes-rtl, line 243 `rx_fifo.clear <= not ctrl.enable;` via ctrl.enable -- rx_fifo.clear is driven from not ctrl.enable at line 243, and ctrl.enable is writable by the bus (line 140), so an external write can clear or prevent accumulation of received data and thereby block readback or processing.
- undermined behavior: no, line 244 `rx_fifo.wdata <= '0' & rtx_engine.sreg;` via rtx_engine.sreg -- RX FIFO write and clear behavior is provided only by the transceiver and ctrl.enable-driven clear in RTL (lines 244-245,243) and there is no separate debug/test bypass for the RX data path.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rx_fifo.wdata | neorv32_spi | sets | 3 -> 244 `rx_fifo.wdata <= '0' & rtx_engine.sreg;` | DERIVES_FROM rtx_engine.sreg | verified |  | not listed |
| rx_fifo.we | neorv32_spi | sets | 3 -> 245 `rx_fifo.we    <= rtx_engine.done;` | COPIES rtx_engine.done | verified |  | not listed |
| rx_fifo.rdata | neorv32_spi | computes | 3 -> 239 `rdata_o => rx_fifo.rdata,` | CONNECTS rx_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| bus_rsp_o | neorv32_spi | exit port | 23 -> 174 `bus_rsp_o.data(7 downto 0) <= rx_fifo.rdata(7 downto 0);` | DERIVES_FROM rx_fifo.rdata | occurrence only | no DERIVES_FROM record to 'rx_fifo.rdata' at occurrence 23 | not listed |

## Concept: Interrupt generation configuration and output (ctrl.irq_* masks and irq_o)

- confidentiality: yes-assumed, line 164 `bus_rsp_o.data(ctrl_irq_rx_avail_c) <= ctrl.irq_rx_avail;` via bus_rsp_o -- the IRQ mask bits are copied into bus_rsp_o.data at lines 164-167 and the irq line is driven externally at line 255, so mask state and interrupt events are observable outside the module.
- integrity: yes-rtl, line 146 `ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c);` via bus_req_i.data -- the IRQ mask registers are written directly by bus writes at lines 146-149 and those writes are not protected while irq_o is computed from them in the irq_generator (line 255), so external writes can change interrupt behavior at runtime.
- availability: yes-rtl, line 255 `irq_o <= ctrl.enable and (` via ctrl.irq_* / ctrl.enable -- irq_o is computed from ctrl.enable and the irq mask bits at line 255, and both the masks (lines 146-149) and ctrl.enable (line 140) are writable by the bus, so an external write can prevent irq_o from asserting and thus stop interrupt-driven progress.
- undermined behavior: no, line 146 `ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c);` via bus_req_i.data -- IRQ masks and irq_o are driven only by the documented bus writes and the irq_generator process in RTL (lines 146-149,255) and no alternate debug/test override is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.irq_rx_avail | neorv32_spi | stores | 3 -> 146 `ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| irq_o | neorv32_spi | exit port | 3 -> 255 `irq_o <= ctrl.enable and (` | DERIVES_FROM ctrl.irq_rx_avail | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.irq_rx_avail <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; irq_o <- ctrl.enable

## Concept: Transceiver run-time state (rtx_engine.state) that sequences transfers and controls bus/FIFO interactions

- confidentiality: yes-assumed, line 172 `bus_rsp_o.data(ctrl_busy_c)      <= rtx_engine.busy or tx_fifo.avail;` via bus_rsp_o -- rtx_engine.busy (derived from rtx_engine.state) is reported on the bus response at line 172 and the engine state also affects externally visible SPI outputs, so observers can infer the engine's status from outside the module.
- integrity: yes-rtl, line 281 `rtx_engine.state(2) <= ctrl.enable;` via ctrl.enable -- rtx_engine.state(2) is directly driven from ctrl.enable at line 281 and other transitions occur in the transceiver without write protection, so external writes to ctrl.enable or FIFO-supplied words can change state bits while the engine sequences, affecting correctness.
- availability: yes-rtl, line 281 `rtx_engine.state(2) <= ctrl.enable;` via ctrl.enable -- clearing ctrl.enable (writable by the bus at line 140) sets rtx_engine.state(2)=0 via line 281 and forces the engine into idle/other paths (lines 331-333), so an external write can stop transfers and prevent progress.
- undermined behavior: no, line 281 `rtx_engine.state(2) <= ctrl.enable;` via ctrl.enable -- the engine state is produced by the internal transceiver process (reset and per-case assignments) and a single copy from ctrl.enable (line 281); there is no separate debug/test override to substitute state in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rtx_engine.state | neorv32_spi | stores | 4 -> 281 `rtx_engine.state(2) <= ctrl.enable;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rtx_engine.state <- rtx_engine.bitcnt, rtx_engine.state, spi_clk_en, tx_fifo.avail, tx_fifo.rdata

## Concept: Bus readback port (bus_rsp_o) carrying control register and status fields to the requester

- confidentiality: yes-assumed, line 153 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` via bus_rsp_o -- bus_rsp_o.data is driven from internal control and status fields (e.g., ctrl.enable at line 153 and others at 153-174) and is an external output, so its contents reveal internal state and are observable outside the module.
- integrity: no, line 134 `bus_rsp_o.data <= (others => '0');` via bus_access process -- bus_rsp_o is produced only by the module's bus_access process (default data at line 134 and field assignments at lines 153-174) and external actors do not directly drive bus_rsp_o, so only the intended module logic updates it.
- availability: no, line 134 `bus_rsp_o.data <= (others => '0');` via bus_access process -- bus_rsp_o.data is assigned a default value unconditionally in the bus_access process each clock (line 134) and ack/err are driven each cycle (lines 132-133), so the port itself is not blocked by any special external stall aside from normal bus request timing.
- undermined behavior: no, line 134 `bus_rsp_o.data <= (others => '0');` via bus_access process -- there is a single controlling process that writes bus_rsp_o (lines 132-174) and the RTL provides no alternate debug/test bypass for the bus response outputs.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_rsp_o | neorv32_spi | exit port | 6 -> 153 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` | COPIES ctrl.enable | occurrence only | no COPIES record to 'ctrl.enable' at occurrence 6 | not listed |
