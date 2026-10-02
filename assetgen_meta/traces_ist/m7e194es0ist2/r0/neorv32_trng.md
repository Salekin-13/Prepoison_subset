# neorv32_trng

**Purpose (model):** A bus-accessible true-random-number generator: it accepts bus writes to control sampling and FIFO clear, instantiates a neoTRNG that produces debiased random bytes, buffers those bytes into a rnd_pool_fifo, and responds to bus reads with status (FIFO available/size) or FIFO data.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | control registers written from the bus: sampling enable and FIFO-clear bits |  | 5 / 5 |
| start | sampling enable propagated into the neoTRNG (start/stop sampling) |  | 4 / 4 |
| operate | neoTRNG samples, combines and debiases ring-oscillator bits, assembles bytes and emits data/valid to the FIFO |  | 15 / 15 |
| report | bus response: ack, status fields (enable, fifo size, sim_mode, fifo.avail) returned on reads |  | 8 / 8 |
| read out | consumer reads a FIFO entry: bus read asserts fifo.re, FIFO produces rdata which is copied to bus_rsp_o.data |  | 7 / 7 |
| reset | top-level reset forces known values (bus_rsp_o <= rsp_terminate_c; fifo_clr, enable cleared) and resets are passed to subunits |  | 8 / 8 |

## Concept: Bus request decode (strobe / read-write / addr[2]) that decides register writes, reads and FIFO operations

- confidentiality: no, line 98 `bus_rsp_o.ack  <= bus_req_i.stb;` via bus_rsp_o.ack -- The decoded bus request fields are inputs from an external master and are reflected to outputs (e.g. ack copied at line 98), so they reveal nothing new beyond the writer's own view.
- integrity: yes-assumed, line 103 `if (bus_req_i.stb = '1') then` via bus_req_i -- The bus request bits are external inputs used by the bus_access process (gated at line 103 and used to drive writes at lines 104-106 and reads at 108-117), so whether they are trusted depends on the integrator's choice of bus master.
- availability: yes-rtl, line 171 `fifo.re    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '0') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i -- FIFO reads are gated by bus request signals (fifo.re is driven only when bus_req_i.stb='1' and rw='0' and addr(2)='1' at line 171), so an external actor can withhold or assert those inputs to block or force reads.
- undermined behavior: no, line 103 `if (bus_req_i.stb = '1') then` via bus_req_i -- There is no alternate debug/test/override source in the RTL; the decode is driven only from the external bus_req_i fields used at lines 103-117 and 171.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_trng | sets | 3 -> 103 `if (bus_req_i.stb = '1') then` | GATES bus_rsp_o.data | occurrence only | no GATES record to 'bus_rsp_o.data' at occurrence 3 | not listed |
| fifo.re | neorv32_trng | sets | 3 -> 171 `fifo.re    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '0') and (bus_req_i.addr(` | GATED_BY bus_req_i.stb | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fifo.re <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Sampling enable setting stored by the module (controls whether the TRNG samples)

- confidentiality: no, line 109 `bus_rsp_o.data(ctrl_en_c)                                  <= enable;` via bus_rsp_o.data -- The enable bit is written by the bus master and explicitly read back to the bus at line 109, so it is not treated as a secret by the RTL.
- integrity: yes-rtl, line 105 `enable   <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- Enable is written directly from bus_req_i.data at line 105 without RTL protection while sampling may be active (sample_en <= enable_i at line 354), so an external writer can change it during operation.
- availability: yes-rtl, line 354 `sample_en <= enable_i;` via enable -- sample_en inside neoTRNG is driven from enable_i (line 354), so an external write that clears enable (via bus_req_i) will stop sampling and block progress.
- undermined behavior: no, line 105 `enable   <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- Enable has a single RTL driver (bus write at line 105 plus reset) and there is no alternate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_trng | sets | 5 -> 105 `enable   <= bus_req_i.data(ctrl_en_c);` | SOURCES enable | occurrence only | no SOURCES record to 'enable' at occurrence 5 | not listed |
| enable | neorv32_trng | stores | 3 -> 105 `enable   <= bus_req_i.data(ctrl_en_c);` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): enable <- bus_req_i.rw, bus_req_i.stb

## Concept: FIFO-clear control (the fifo_clr bit and the computed fifo.clear) that clears the random-data buffer

- confidentiality: yes-assumed, line 115 `bus_rsp_o.data(ctrl_data_msb_c downto ctrl_data_lsb_c) <= (others => '0');` via bus_rsp_o.data -- fifo_clr (written by a bus write at line 106) causes fifo.clear (line 170) which empties the FIFO and makes subsequent reads return zeros (line 115), so external observers can detect the clear and confidentiality depends on integrator policy.
- integrity: yes-rtl, line 106 `fifo_clr <= bus_req_i.data(ctrl_fifo_clr_c);` via bus_req_i.data -- An external bus write sets fifo_clr at line 106 and there is no RTL guard preventing this while FIFO contents exist; fifo.clear uses fifo_clr (line 170) to clear stored entropy, so external actors can change FIFO contents.
- availability: yes-rtl, line 170 `fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1') else '0';` via fifo_clr -- fifo.clear is asserted when (enable='0') or (fifo_clr='1') at line 170, so external inputs (via fifo_clr or enable) can force the FIFO cleared and prevent data delivery.
- undermined behavior: no, line 170 `fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1') else '0';` via fifo.clear -- fifo.clear is computed in a single RTL assignment (line 170) and there is no separate debug/test override path in the RTL to substitute a different driver.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_trng | sets | 6 -> 106 `fifo_clr <= bus_req_i.data(ctrl_fifo_clr_c);` | SOURCES fifo_clr | occurrence only | no SOURCES record to 'fifo_clr' at occurrence 6 | not listed |
| fifo_clr | neorv32_trng | stores | 4 -> 106 `fifo_clr <= bus_req_i.data(ctrl_fifo_clr_c);` | CLOCKED_BY clk_i | verified |  | hit |
| fifo.clear | neorv32_trng | computes | 3 -> 170 `fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1') else '0';` | GATED_BY fifo_clr | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fifo_clr <- bus_req_i.rw, bus_req_i.stb; fifo.clear <- enable, fifo_clr

## Concept: Random bytes as delivered to a consumer (data written by neoTRNG into the FIFO and returned on bus reads)

- confidentiality: yes-assumed, line 117 `bus_rsp_o.data(ctrl_data_msb_c downto ctrl_data_lsb_c) <= fifo.rdata;` via bus_rsp_o.data -- The TRNG bytes flow from neoTRNG into the FIFO (lines 138-139, 161-162) and are presented to external readers on bus reads (bus_rsp_o.data <= fifo.rdata at line 117), so confidentiality depends on how the integrator treats those outputs.
- integrity: yes-rtl, line 106 `fifo_clr <= bus_req_i.data(ctrl_fifo_clr_c);` via bus_req_i -- Although the bytes are produced internally (neoTRNG -> fifo.wdata, lines 138-139), an external bus write can assert fifo_clr (line 106) and via fifo.clear (line 170) remove or replace FIFO contents (reads return zeros at line 115), so external inputs can change what is delivered.
- availability: yes-rtl, line 170 `fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1') else '0';` via fifo_clr -- fifo.clear is driven by enable and fifo_clr at line 170, so an external actor can force the FIFO cleared and thus prevent consumers from receiving bytes.
- undermined behavior: no, line 138 `valid_o  => fifo.we,` via neoTRNG_inst -- The delivered bytes have a single RTL driver path (neoTRNG.data_o -> fifo.wdata -> FIFO -> bus_rsp_o.data) and there is no runtime debug/test override in the RTL that substitutes alternate data.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| data_o | neoTRNG | exit port | 2 -> 366 `data_o  <= sample_sreg;` | COPIES sample_sreg | verified |  | hit |
| fifo.re | neorv32_trng | sets | 3 -> 171 `fifo.re    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '0') and (bus_req_i.addr(` | GATED_BY bus_req_i.stb | verified |  | hit |
| bus_rsp_o | neorv32_trng | exit port | 11 -> 117 `bus_rsp_o.data(ctrl_data_msb_c downto ctrl_data_lsb_c) <= fifo.rdata;` | COPIES fifo.rdata | occurrence only | no COPIES record to 'fifo.rdata' at occurrence 11 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fifo.re <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb

## Concept: Assembled TRNG output byte (sample_sreg) inside neoTRNG before it leaves the subunit

- confidentiality: yes-assumed, line 117 `bus_rsp_o.data(ctrl_data_msb_c downto ctrl_data_lsb_c) <= fifo.rdata;` via bus_rsp_o.data -- sample_sreg is copied to data_o (line 366) and propagated through the FIFO to bus reads (bus_rsp_o.data <= fifo.rdata at line 117), so external observers can read the assembled byte and confidentiality depends on integrator policy.
- integrity: yes-rtl, line 357 `sample_sreg <= (others => '0');` via enable -- sample_sreg is cleared when sampling is disabled (the reset/clear path at lines 355-357) and sample_en is driven from enable_i (line 354), which an external bus write can change (enable <= bus_req_i.data at line 105), so external inputs can alter sample_sreg content.
- availability: yes-rtl, line 354 `sample_en <= enable_i;` via enable -- sample_en inside neoTRNG is driven from enable_i (line 354); clearing enable via bus writes prevents further sample_sreg updates and thus stops byte production.
- undermined behavior: no, line 360 `sample_sreg <= sample_sreg(6 downto 0) & (sample_sreg(7) xor debias_data);` via sample_sreg -- The assembled byte register sample_sreg has explicit RTL assignments (update at line 360, clears at lines 352/357) and no runtime override path is present to substitute a different driver.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| sample_sreg | neoTRNG | stores | 3 -> 357 `sample_sreg <= (others => '0');` | CLOCKED_BY clk_i | verified |  | not listed |
| data_o | neoTRNG | exit port | 2 -> 366 `data_o  <= sample_sreg;` | COPIES sample_sreg | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sample_sreg <- debias_valid, sample_cnt, sample_en

## Concept: FIFO availability flag (fifo.avail) used to report whether data exists and to select returned data vs zeros

- confidentiality: yes-assumed, line 112 `bus_rsp_o.data(ctrl_avail_c)                               <= fifo.avail;` via bus_rsp_o.data -- fifo.avail is produced by the FIFO (line 167) and explicitly reported on the bus (bus_rsp_o.data(ctrl_avail_c) <= fifo.avail at line 112), so its value is observable and confidentiality depends on integration.
- integrity: yes-rtl, line 170 `fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1') else '0';` via fifo.clear -- fifo.avail is directly affected by fifo.clear (computed at line 170 and fed to the FIFO at line 157), and fifo.clear itself can be asserted by external-controlled signals (fifo_clr or enable), so external inputs can force changes in fifo.avail.
- availability: yes-rtl, line 170 `fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1') else '0';` via fifo.clear -- Since fifo.clear is asserted when enable='0' or fifo_clr='1' (line 170), external control can force the FIFO empty state and thus the availability flag and data delivery.
- undermined behavior: no, line 167 `avail_o => fifo.avail` via rnd_pool_fifo_inst -- fifo.avail is supplied only by the FIFO submodule (avail_o mapped at line 167) and there is no runtime debug/test override in the RTL to replace its source.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| fifo.avail | neorv32_trng | sets | 4 -> 167 `avail_o => fifo.avail` | CONNECTS rnd_pool_fifo_inst.avail_o | verified | (via connection, mode None) | hit |
| bus_rsp_o | neorv32_trng | exit port | 9 -> 112 `bus_rsp_o.data(ctrl_avail_c)                               <= fifo.avail;` | COPIES fifo.avail | occurrence only | no COPIES record to 'fifo.avail' at occurrence 9 | not listed |
