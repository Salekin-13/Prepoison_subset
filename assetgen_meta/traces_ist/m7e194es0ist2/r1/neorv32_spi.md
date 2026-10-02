# neorv32_spi

**Purpose (model):** neorv32_spi is an SPI controller accessible over a bus: it accepts bus writes to configure control registers and enqueue TX data into a TX FIFO, drives SPI signals (spi_clk_o, spi_dat_o, spi_csn_o) to perform transfers, captures incoming SPI bits into an RX FIFO, and produces bus responses and an interrupt output (irq_o).

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | write control registers (enable, cpha, cpol, prsc, cdiv, highspeed, irq enables) from bus_req_i.data |  | 11 / 11 |
| start | enqueue a TX FIFO entry from a bus write which the transceiver consumes to begin or continue an SPI transfer |  | 8 / 8 |
| operate | SPI byte transfer: clock generation, chip-select control, bit shifts out (spi_dat_o) and sampling in (spi_dat_i) driven by the transceiver FSM |  | 17 / 17 |
| report | generate an interrupt (irq_o) when enabled conditions (RX available, TX empty/half, idle) occur |  | 7 / 7 |
| read out | return control/status fields and RX FIFO data on bus reads via bus_rsp_o.data |  | 16 / 16 |
| reset | hardware reset clears control registers, transceiver state and counters, resets SPI outputs and FIFOs when rstn_i = '0' |  | 17 / 17 |

## Concept: Control register settings (enable, cpha, cpol, prsc, cdiv, highspeed, IRQ enables) that determine SPI timing, phase/polarity, enabling and IRQ masks

- confidentiality: yes-assumed, line 153 `bus_rsp_o.data(ctrl_en_c)                        <= ctrl.enable;` via bus_rsp_o.data -- Control fields are written from bus_req_i.data (lines 140-149) and are explicitly read back to the bus via bus_rsp_o.data (e.g. line 153 shows ctrl.enable readback), so an external bus master can observe their values.
- integrity: yes-rtl, line 140 `ctrl.enable       <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- Bus writes at line 140 (and 141-149) assign control fields whenever bus_req_i indicates a write (guarded only by bus_req_i.stb/rw/addr) and those fields are used by the transceiver/clock generator (e.g. rtx_engine.state(2) <= ctrl.enable at line 281), so a write can change configuration while the block is operating.
- availability: yes-rtl, line 369 `if (ctrl.enable = '0') then` via bus_req_i (ctrl.enable) -- Clearing ctrl.enable (writable via bus_req_i at line 140) disables clock generation and related progress (clock_generator checks ctrl.enable at line 369), allowing an external bus master to stop SPI progress.
- undermined behavior: no, line 140 `ctrl.enable       <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- Control fields are driven only by reset (120-129) and bus writes (140-149); there is no alternate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.enable | neorv32_spi | stores | 3 -> 140 `ctrl.enable       <= bus_req_i.data(ctrl_en_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i.data | neorv32_spi | sets | 2 -> 140 `ctrl.enable       <= bus_req_i.data(ctrl_en_c);` | SOURCES ctrl.enable | verified |  | not listed |
| ctrl.cpha | neorv32_spi | stores | 3 -> 141 `ctrl.cpha         <= bus_req_i.data(ctrl_cpha_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_spi | sets | 3 -> 141 `ctrl.cpha         <= bus_req_i.data(ctrl_cpha_c);` | SOURCES ctrl.cpha | verified |  | not listed |
| ctrl.cpol | neorv32_spi | stores | 3 -> 142 `ctrl.cpol         <= bus_req_i.data(ctrl_cpol_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_spi | sets | 4 -> 142 `ctrl.cpol         <= bus_req_i.data(ctrl_cpol_c);` | SOURCES ctrl.cpol | verified |  | not listed |
| ctrl.prsc | neorv32_spi | stores | 3 -> 143 `ctrl.prsc         <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i.data | neorv32_spi | sets | 5 -> 143 `ctrl.prsc         <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c);` | SOURCES ctrl.prsc | verified |  | not listed |
| ctrl.cdiv | neorv32_spi | stores | 3 -> 144 `ctrl.cdiv         <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i.data | neorv32_spi | sets | 6 -> 144 `ctrl.cdiv         <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` | SOURCES ctrl.cdiv | verified |  | not listed |
| ctrl.highspeed | neorv32_spi | stores | 3 -> 145 `ctrl.highspeed    <= bus_req_i.data(ctrl_highspeed_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_spi | sets | 7 -> 145 `ctrl.highspeed    <= bus_req_i.data(ctrl_highspeed_c);` | SOURCES ctrl.highspeed | verified |  | not listed |
| ctrl.irq_rx_avail | neorv32_spi | stores | 3 -> 146 `ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i.data | neorv32_spi | sets | 8 -> 146 `ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c);` | SOURCES ctrl.irq_rx_avail | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.enable <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.cpha <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.cpol <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.prsc <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.cdiv <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.highspeed <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb; ctrl.irq_rx_avail <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: TX FIFO contents (bus-written transmit bytes and CS-control words) that determine what the transceiver sends

- confidentiality: yes-assumed, line 343 `spi_dat_o <= rtx_engine.sreg(7);` via spi_dat_o -- TX FIFO entries are written from bus_req_i.data (line 213) and are output onto the SPI pins (e.g. spi_dat_o at line 343 and spi_csn_o at line 354), so external observers on the SPI lines can learn FIFO contents.
- integrity: yes-assumed, line 212 `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i.data -- FIFO data and write enable come from bus writes (tx_fifo.wdata at 213 and tx_fifo.we at 212); the RTL exposes an external writer so whether that writer is trusted depends on integration and thus FIFO contents' integrity is an assumption about the bus master.
- availability: yes-rtl, line 211 `tx_fifo.clear <= not ctrl.enable;` via ctrl.enable (written via bus_req_i at 140) -- tx_fifo.clear is driven by not ctrl.enable at line 211, so clearing ctrl.enable via a bus write (line 140) asserts clear and can remove or prevent FIFO contents, blocking transmission availability.
- undermined behavior: no, line 213 `tx_fifo.wdata <= bus_req_i.data(31) & bus_req_i.data(7 downto 0);` via bus_req_i.data -- FIFO content is supplied via the bus write path (lines 212-213) and the FIFO instance; there is no alternate debug/test override of tx_fifo.wdata or we in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| tx_fifo.wdata | neorv32_spi | sets | 3 -> 213 `tx_fifo.wdata <= bus_req_i.data(31) & bus_req_i.data(7 downto 0);` | DERIVES_FROM bus_req_i.data | verified |  | not listed |
| tx_fifo.we | neorv32_spi | sets | 3 -> 212 `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.ad` | GATED_BY bus_req_i.stb | verified |  | not listed |
| tx_fifo.rdata | neorv32_spi | computes | 2 -> 207 `rdata_o => tx_fifo.rdata,` | CONNECTS tx_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): tx_fifo.we <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: RX FIFO contents (received bytes stored for bus readback)

- confidentiality: yes-assumed, line 174 `bus_rsp_o.data(7 downto 0) <= rx_fifo.rdata(7 downto 0);` via bus_rsp_o.data -- Received bytes are written into the RX FIFO from the transceiver (line 244/245) and are explicitly read back to the bus via bus_rsp_o.data at line 174, so a bus master can observe RX contents.
- integrity: yes-rtl, line 243 `rx_fifo.clear <= not ctrl.enable;` via ctrl.enable (written via bus_req_i at 140) -- rx_fifo.clear is driven by not ctrl.enable at line 243 and can be asserted by clearing ctrl.enable via bus writes (line 140), allowing an external bus master to clear or change RX FIFO contents while they may be expected to remain for readback (bus read at line 174).
- availability: yes-rtl, line 243 `rx_fifo.clear <= not ctrl.enable;` via ctrl.enable (written via bus_req_i at 140) -- Asserting not ctrl.enable drives rx_fifo.clear at line 243, which clears the RX FIFO and prevents delivery of received bytes to the bus, so availability is controllable from outside via ctrl.enable.
- undermined behavior: no, line 245 `rx_fifo.we    <= rtx_engine.done;` via rtx_engine.done -- RX FIFO writes (lines 244-245) are driven only by the transceiver (rtx_engine.sreg and rtx_engine.done) and the FIFO instance; no separate debug/test override is provided in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rx_fifo.wdata | neorv32_spi | sets | 3 -> 244 `rx_fifo.wdata <= '0' & rtx_engine.sreg;` | DERIVES_FROM rtx_engine.sreg | verified |  | not listed |
| rx_fifo.we | neorv32_spi | sets | 3 -> 245 `rx_fifo.we    <= rtx_engine.done;` | COPIES rtx_engine.done | verified |  | not listed |
| rx_fifo.rdata | neorv32_spi | computes | 3 -> 239 `rdata_o => rx_fifo.rdata,` | CONNECTS rx_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |

## Concept: Transceiver FSM and shift-register state (rtx_engine.state, rtx_engine.sreg, bit counter, sampled bit) that implement an ongoing SPI transfer

- confidentiality: yes-assumed, line 343 `spi_dat_o <= rtx_engine.sreg(7);` via spi_dat_o -- The FSM, sreg and sampled bits determine the SPI outputs (spi_dat_o at line 343 and spi_clk_o at line 344) and a busy flag visible on the bus (line 172), so external observers can infer internal transfer state.
- integrity: yes-rtl, line 281 `rtx_engine.state(2) <= ctrl.enable;` via bus_req_i.data (ctrl.enable) -- The transceiver's state bit rtx_engine.state(2) is directly driven by ctrl.enable at line 281, and ctrl.enable can be written by bus requests (line 140) at any time, allowing external writes to change FSM state during transfers.
- availability: yes-rtl, line 299 `if (spi_clk_en = '1') then` via spi_clk_en (driven by clkgen_i and ctrl.prsc/ctrl.highspeed) -- Many state transitions and bit shifts are gated by spi_clk_en (e.g. the if (spi_clk_en = '1') at line 299), and spi_clk_en depends on clkgen_i and ctrl fields reachable from outside, so external inputs can freeze state progression.
- undermined behavior: no, line 281 `rtx_engine.state(2) <= ctrl.enable;` via transceiver process -- The FSM and shift register are updated only by the transceiver process (lines 266-336) and by FIFO-loaded words; there is no alternate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rtx_engine.state | neorv32_spi | stores | 4 -> 281 `rtx_engine.state(2) <= ctrl.enable;` | CLOCKED_BY clk_i | verified |  | not listed |
| rtx_engine.sreg | neorv32_spi | stores | 4 -> 292 `rtx_engine.sreg              <= tx_fifo.rdata(7 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| rtx_engine.bitcnt | neorv32_spi | stores | 4 -> 311 `rtx_engine.bitcnt            <= std_ulogic_vector(unsigned(rtx_engine.bitcnt) + 1);` | CLOCKED_BY clk_i | verified |  | not listed |
| spi_dat_i | neorv32_spi | sets | 2 -> 310 `rtx_engine.sdi_sync          <= spi_dat_i;` | CARRIES rtx_engine.sdi_sync | verified |  | hit |
| spi_dat_o | neorv32_spi | exit port | 2 -> 343 `spi_dat_o <= rtx_engine.sreg(7);` | DERIVES_FROM rtx_engine.sreg | verified |  | hit |
| spi_clk_o | neorv32_spi | exit port | 2 -> 344 `spi_clk_o <= rtx_engine.sck;` | COPIES rtx_engine.sck | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rtx_engine.state <- rtx_engine.bitcnt, rtx_engine.state, spi_clk_en, tx_fifo.avail, tx_fifo.rdata; rtx_engine.sreg <- rtx_engine.state, spi_clk_en, tx_fifo.avail, tx_fifo.rdata; rtx_engine.bitcnt <- rtx_engine.state, spi_clk_en

## Concept: Chip-select outputs (spi_csn_o) driven by rtx_engine.cs_ctrl selecting which slave is activated

- confidentiality: yes-assumed, line 354 `spi_csn_o(to_integer(unsigned(rtx_engine.cs_ctrl(2 downto 0)))) <= '0';` via spi_csn_o -- spi_csn_o is driven onto external pins (the conditional write at line 354 pulls a selected CS low), so external observers can directly learn which slave is selected; cs_ctrl originates from FIFO words (line 290).
- integrity: yes-assumed, line 290 `rtx_engine.cs_ctrl <= tx_fifo.rdata(3 downto 0);` via tx_fifo.rdata (written from bus_req_i.data) -- rtx_engine.cs_ctrl is loaded from tx_fifo.rdata at line 290 (when tx_fifo.rdata(8) = '1'), and tx_fifo content is supplied by bus writes (line 213), so an external bus writer can change which chip-select will be asserted.
- availability: yes-rtl, line 354 `spi_csn_o(to_integer(unsigned(rtx_engine.cs_ctrl(2 downto 0)))) <= '0';` via rtx_engine.cs_ctrl (driven by tx_fifo entries) -- chip_select defaults spi_csn_o to all-ones each clock (line 352) and only drives a CS low when rtx_engine.cs_ctrl(3)='1' at line 354, and cs_ctrl is controlled by FIFO entries provided from outside, so external inputs can prevent or force CS behavior.
- undermined behavior: no, line 354 `spi_csn_o(to_integer(unsigned(rtx_engine.cs_ctrl(2 downto 0)))) <= '0';` via chip_select process -- spi_csn_o is driven only by the chip_select process (lines 347-356) together with rtx_engine.cs_ctrl; the RTL contains no alternate/debug override for spi_csn_o.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| spi_csn_o | neorv32_spi | exit port | 4 -> 354 `spi_csn_o(to_integer(unsigned(rtx_engine.cs_ctrl(2 downto 0)))) <= '0';` | SELECTED_BY rtx_engine.cs_ctrl | verified |  | hit |
| rtx_engine.cs_ctrl | neorv32_spi | stores | 4 -> 290 `rtx_engine.cs_ctrl <= tx_fifo.rdata(3 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| tx_fifo.rdata | neorv32_spi | sets | 4 -> 290 `rtx_engine.cs_ctrl <= tx_fifo.rdata(3 downto 0);` | SOURCES rtx_engine.cs_ctrl | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage not assigned) | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): spi_csn_o <- rtx_engine.cs_ctrl; rtx_engine.cs_ctrl <- rtx_engine.state, tx_fifo.avail, tx_fifo.rdata

## Concept: Interrupt output decision (irq_o) computed from control IRQ enables and FIFO/transceiver status

- confidentiality: yes-assumed, line 255 `irq_o <= ctrl.enable and (` via irq_o -- irq_o is driven to an external pin (assignment at line 255) and encodes internal status and enabled-event conditions (ctrl.irq_*, fifo/engine status), so observing the IRQ reveals internal activity and configuration.
- integrity: yes-rtl, line 146 `ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c);` via bus_req_i.data -- IRQ-enable bits (e.g. ctrl.irq_rx_avail at line 146) are writable via bus_req_i.data and directly affect irq_o's computation at line 255, so bus writes can change IRQ behavior while the module runs.
- availability: yes-rtl, line 255 `irq_o <= ctrl.enable and (` via ctrl.enable (written via bus_req_i at 140) -- irq_o is ANDed with ctrl.enable in the assignment at line 255, so clearing ctrl.enable via a bus write (line 140) forces irq_o low and externally prevents IRQ signaling.
- undermined behavior: no, line 255 `irq_o <= ctrl.enable and (` via irq_generator process -- irq_o has a single computed driver in the irq_generator process (line 255) and there is no alternate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| irq_o | neorv32_spi | exit port | 3 -> 255 `irq_o <= ctrl.enable and (` | DERIVES_FROM ctrl.irq_rx_avail | verified |  | hit |
| ctrl.irq_rx_avail | neorv32_spi | stores | 3 -> 146 `ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c);` | CLOCKED_BY clk_i | verified |  | not listed |
| rx_fifo.avail | neorv32_spi | sets | 4 -> 256 `(ctrl.irq_rx_avail and      rx_fifo.avail)  or` | SOURCES irq_o | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage not assigned) | not listed |
| tx_fifo.avail | neorv32_spi | sets | 5 -> 257 `(ctrl.irq_tx_empty and (not tx_fifo.avail)) or` | SOURCES irq_o | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage not assigned) | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): irq_o <- ctrl.enable; ctrl.irq_rx_avail <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: SPI clock-enable (spi_clk_en) that gates transceiver bit shifts and timing

- confidentiality: yes-assumed, line 344 `spi_clk_o <= rtx_engine.sck;` via spi_clk_o -- spi_clk_en is generated internally (clock_generator lines 362-377) but determines the external SPI clock (spi_clk_o at line 344), so an external observer can infer clock-enable and timing from the SPI clock.
- integrity: yes-rtl, line 144 `ctrl.cdiv         <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c);` via bus_req_i.data -- spi_clk_en's timing depends on control fields (ctrl.cdiv/ctrl.prsc/ctrl.highspeed; ctrl.cdiv is written at line 144) which can be rewritten by bus writes at any time, altering the generated clock while the transceiver depends on it.
- availability: yes-rtl, line 369 `if (ctrl.enable = '0') then` via ctrl.enable (written via bus_req_i at 140) -- If ctrl.enable = '0' the clock_generator resets cdiv_cnt and will not assert spi_clk_en (the check and reset are at line 369), so clearing ctrl.enable via bus writes can stop SPI clock generation and block progress.
- undermined behavior: no, line 373 `spi_clk_en <= '1';` via clock_generator process -- spi_clk_en is produced only by the clock_generator logic (assignment at line 373) under ctrl/prsc/highspeed and clkgen_i control; the RTL contains no separate debug/test override that bypasses it.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| spi_clk_en | neorv32_spi | stores | 6 -> 368 `spi_clk_en <= '0';` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl.prsc | neorv32_spi | computes | 5 -> 371 `elsif (clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1') or (ctrl.highspeed = '1') then` | SELECTS spi_clk_en | edge, role unfit | SELECTS does not demonstrate 'computes' | hit |
| clkgen_i | neorv32_spi | sets | 2 -> 371 `elsif (clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1') or (ctrl.highspeed = '1') then` | GATES spi_clk_en | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): spi_clk_en <- cdiv_cnt, clkgen_i, ctrl.cdiv, ctrl.enable, ctrl.highspeed, ctrl.prsc; ctrl.prsc <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb
