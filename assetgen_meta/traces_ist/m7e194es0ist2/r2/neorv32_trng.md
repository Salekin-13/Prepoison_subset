# neorv32_trng

**Purpose (model):** Top-level TRNG IP that exposes a neoTRNG entropy generator and a FIFO to a bus: it decodes bus reads/writes to control the generator (enable, FIFO clear), forwards neoTRNG output bytes into an internal FIFO, and returns status (FIFO available, FIFO size, sim mode) and random bytes on bus_rsp_o.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | Write control bits (enable, fifo_clr) into the TRNG control registers |  | 4 / 4 |
| start | Enable bit flows into neoTRNG as sample_en and starts/stops sampling |  | 2 / 2 |
| operate | neoTRNG produces bytes (data_o, valid_o) that are presented to the FIFO inputs and written into the FIFO |  | 6 / 6 |
| read out | Bus read returns either zero or the FIFO read-data word (fifo.rdata) depending on fifo.avail and read address |  | 4 / 4 |
| report | Bus read of control/status returns enable, FIFO size, sim-mode and fifo.avail fields |  | 4 / 4 |
| reset | Reset forces control registers and internal sampling state to known defaults (bus_rsp_o, enable, fifo_clr at top-level; debias and sample counters inside neoTRNG) |  | 8 / 8 |

## Concept: Peripheral write decision that sets TRNG control bits (the bus write that stores enable and fifo_clr)

- confidentiality: no, line 109 `bus_rsp_o.data(ctrl_en_c)                                  <= enable;` via bus_rsp_o.data -- The control bits are written by the bus master and at least enable is explicitly read back via bus_rsp_o.data at line 109, so the RTL does not hide this setting.
- integrity: yes-rtl, line 105 `enable   <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- enable and fifo_clr are assigned directly from bus_req_i.data at lines 105-106 under the bus write guard (bus_req_i.stb/rw) and there is no RTL guard that prevents these writes while sampling/FIFO are in use.
- availability: yes-rtl, line 170 `fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1') else '0';` via bus_req_i.data -- An external bus write to enable or fifo_clr (lines 105-106) can cause fifo.clear to assert (line 170) or disable sampling, thereby stopping or forcing unavailability of entropy.
- undermined behavior: no, line 105 `enable   <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- These control bits have a single register driver from the bus write/reset (lines 105-106 and 94-95) and there is no runtime debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i.data | neorv32_trng | sets | 2 -> 105 `enable   <= bus_req_i.data(ctrl_en_c);` | SOURCES enable | verified |  | not listed |
| bus_req_i.stb | neorv32_trng | sets | 3 -> 103 `if (bus_req_i.stb = '1') then` | GATES enable | verified |  | not listed |
| bus_req_i.rw | neorv32_trng | sets | 2 -> 104 `if (bus_req_i.rw = '1') then` | GATES enable | verified |  | not listed |

## Concept: TRNG enable state (the stored enable bit that starts/stops sampling)

- confidentiality: no, line 109 `bus_rsp_o.data(ctrl_en_c)                                  <= enable;` via bus_rsp_o.data -- The enable register is written by the bus master and explicitly readable via bus_rsp_o.data at line 109, so the RTL does not keep it confidential.
- integrity: yes-rtl, line 105 `enable   <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- enable is updated directly from bus_req_i.data at line 105 under bus write control and can be changed while the TRNG is running (it is consumed by neoTRNG via the port mapping at line 137 and used at line 354).
- availability: yes-rtl, line 354 `sample_en <= enable_i;` via enable -- sample_en <= enable_i at line 354 shows sampling depends on enable, so an external write that clears enable (line 105) can stop sampling and prevent progress.
- undermined behavior: no, line 105 `enable   <= bus_req_i.data(ctrl_en_c);` via bus_req_i.data -- enable has a single driver (bus write and reset) with no alternate runtime override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| enable | neorv32_trng | stores | 3 -> 105 `enable   <= bus_req_i.data(ctrl_en_c);` | CLOCKED_BY clk_i | verified |  | hit |
| enable_i | neoTRNG | sets | 2 -> 354 `sample_en <= enable_i;` | CARRIES sample_en | verified |  | not listed |
| bus_rsp_o.data | neorv32_trng | exit port | 3 -> 109 `bus_rsp_o.data(ctrl_en_c)                                  <= enable;` | COPIES enable | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): enable <- bus_req_i.rw, bus_req_i.stb; bus_rsp_o.data <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, fifo.avail

## Concept: FIFO-clear control (the stored fifo_clr bit that forces the FIFO clear signal)

- confidentiality: yes-assumed, line 170 `fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1') else '0';` via fifo.clear -- fifo_clr controls fifo.clear at line 170, and that clear is connected to the FIFO input (line 157) producing externally observable changes in FIFO availability/data (lines 112, 115-117), so the bit's effect is visible outside the module.
- integrity: yes-rtl, line 106 `fifo_clr <= bus_req_i.data(ctrl_fifo_clr_c);` via bus_req_i.data -- fifo_clr is directly assigned from bus_req_i.data at line 106 under the bus write guard and can be asserted while FIFO holds entropy, affecting FIFO contents.
- availability: yes-rtl, line 170 `fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1') else '0';` via fifo_clr -- fifo.clear is asserted when fifo_clr='1' (line 170) and that clear is connected to the FIFO (line 157), so an external write to fifo_clr can force the FIFO to be cleared and make entropy unavailable.
- undermined behavior: no, line 106 `fifo_clr <= bus_req_i.data(ctrl_fifo_clr_c);` via bus_req_i.data -- fifo_clr has a single register driver from the bus write/reset (lines 106 and 94) and there is no runtime override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| fifo_clr | neorv32_trng | stores | 4 -> 106 `fifo_clr <= bus_req_i.data(ctrl_fifo_clr_c);` | CLOCKED_BY clk_i | verified |  | hit |
| fifo.clear | neorv32_trng | computes | 2 -> 157 `clear_i => fifo.clear,` | CONNECTS rnd_pool_fifo_inst.clear_i | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| bus_req_i.data | neorv32_trng | sets | 3 -> 106 `fifo_clr <= bus_req_i.data(ctrl_fifo_clr_c);` | SOURCES fifo_clr | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fifo_clr <- bus_req_i.rw, bus_req_i.stb; fifo.clear <- enable, fifo_clr

## Concept: Random output bytes (entropy) produced by neoTRNG and delivered to consumers via the FIFO and bus

- confidentiality: yes-assumed, line 117 `bus_rsp_o.data(ctrl_data_msb_c downto ctrl_data_lsb_c) <= fifo.rdata;` via bus_rsp_o.data -- Entropy bytes are written into the FIFO and returned on bus reads (bus_rsp_o.data <= fifo.rdata at line 117), so the RTL exposes the generated bytes to external observation.
- integrity: no, line 161 `wdata_i => fifo.wdata,` via fifo.wdata -- Only the internal neoTRNG writes entropy bytes into the FIFO (neoTRNG.data_o -> fifo.wdata mapping at lines 139/161); there is no bus write path for injecting arbitrary FIFO data, so data replacement is the intended FIFO behavior, not an integrity violation in RTL.
- availability: yes-rtl, line 171 `fifo.re    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '0') and (bus_req_i.addr(2) = '1') else '0';` via bus_req_i -- External bus reads assert fifo.re (line 171) and external writes can assert fifo_clr that drives fifo.clear (line 170 -> FIFO clear_i line 157), both of which can remove or prevent availability of stored entropy.
- undermined behavior: yes-rtl, line 445 `if SIM_MODE generate` via SIM_MODE -- neoTRNG_cell uses a SIM_MODE generic to select a synchronous simulation inverter implementation instead of the physical (asynchronous) inverter (generate blocks lines 439-451), providing an alternate (non-physical / lower-entropy) implementation.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| sample_sreg | neoTRNG | stores | 3 -> 357 `sample_sreg <= (others => '0');` | CLOCKED_BY clk_i | verified |  | not listed |
| data_o | neoTRNG | exit port | 2 -> 366 `data_o  <= sample_sreg;` | COPIES sample_sreg | verified |  | hit |
| valid_o | neoTRNG | exit port | 2 -> 367 `valid_o <= sample_cnt(sample_cnt'left);` | DERIVES_FROM sample_cnt | verified |  | hit |
| fifo.rdata | neorv32_trng | computes | 3 -> 166 `rdata_o => fifo.rdata,` | CONNECTS rnd_pool_fifo_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| bus_rsp_o.data | neorv32_trng | exit port | 8 -> 117 `bus_rsp_o.data(ctrl_data_msb_c downto ctrl_data_lsb_c) <= fifo.rdata;` | COPIES fifo.rdata | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sample_sreg <- debias_valid, sample_cnt, sample_en; bus_rsp_o.data <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, fifo.avail

## Concept: FIFO available flag (fifo.avail) used to select returning data versus zeros

- confidentiality: yes-assumed, line 112 `bus_rsp_o.data(ctrl_avail_c)                               <= fifo.avail;` via bus_rsp_o.data -- fifo.avail is reported on the bus response (line 112) and also affects whether data or zeros are returned (lines 115-117), so the occupancy/state is externally observable.
- availability: yes-rtl, line 170 `fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1') else '0';` via fifo_clr -- fifo.clear (connected to the FIFO clear input at line 157) is asserted when (enable='0') or (fifo_clr='1') at line 170, and bus reads assert fifo.re at line 171, so external inputs can force or starve availability of fifo.avail.
- undermined behavior: no, line 167 `avail_o => fifo.avail` via rnd_pool_fifo_inst.avail_o -- fifo.avail has a single driver from the FIFO sub-unit (line 167) in this RTL and there is no runtime override present here.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| fifo.avail | neorv32_trng | computes | 4 -> 167 `avail_o => fifo.avail` | CONNECTS rnd_pool_fifo_inst.avail_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | hit |
| bus_rsp_o.data | neorv32_trng | exit port | 6 -> 112 `bus_rsp_o.data(ctrl_avail_c)                               <= fifo.avail;` | COPIES fifo.avail | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): bus_rsp_o.data <- bus_req_i.addr, bus_req_i.rw, bus_req_i.stb, fifo.avail

## Concept: Debiasing state (debias_state) that controls acceptance of debiased bits into the sampling path

- confidentiality: yes-assumed, line 341 `debias_valid <= debias_state and (debias_sreg(1) xor debias_sreg(0));` via debias_valid/valid_o -- debias_state directly controls debias_valid at line 341 which gates sampling and therefore influences externally visible valid/data timing (lines 358-367), making the internal state externally inferable.
- integrity: yes-rtl, line 336 `debias_state <= (not debias_state) and cell_en_out(cell_en_out'left);` via cell_en_out -- debias_state is updated by the debiasing process at line 336 using cell_en_out(cell_en_out'left); cell_en_out is driven by the sampling enable chain that external writes (enable) can change, so the state can be influenced while in use.
- availability: yes-rtl, line 336 `debias_state <= (not debias_state) and cell_en_out(cell_en_out'left);` via enable -- debias_state's update depends on cell_en_out (line 336) which is derived from the sample enable chain (sample_en <= enable_i at line 354, top-level enable written at line 105), so external writes can prevent debias_state from progressing or force its value, affecting availability of debiased bits.
- undermined behavior: no, line 336 `debias_state <= (not debias_state) and cell_en_out(cell_en_out'left);` via debias_state -- debias_state has a single controlled update in the debiasing process (line 336) and there is no runtime debug/test bypass in this RTL that directly replaces it.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| debias_state | neoTRNG | stores | 3 -> 336 `debias_state <= (not debias_state) and cell_en_out(cell_en_out'left);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): debias_state <- cell_en_out, debias_state

## Concept: Sample-byte counter (sample_cnt) that determines when a full sampled byte is valid

- confidentiality: yes-assumed, line 367 `valid_o <= sample_cnt(sample_cnt'left);` via valid_o -- sample_cnt directly determines valid_o at line 367 and thus the timing of bytes on data_o, making the sequencing state observable externally through valid/data behavior.
- integrity: no, line 359 `sample_cnt  <= std_ulogic_vector(unsigned(sample_cnt) + 1);` via sampling_control process -- sample_cnt is updated only by the internal sampling_control process (increment at line 359 and clear at lines 355-356) as intended operation; there is no external write that directly mutates the counter.
- availability: yes-rtl, line 355 `if (sample_en = '0') or (sample_cnt(sample_cnt'left) = '1') then` via sample_en/enable -- sampling_control clears sample_cnt when sample_en='0' (line 355) and sample_en is driven from enable (sample_en <= enable_i at line 354, top-level enable written at line 105), so external writes can stop or reset the counter and prevent bytes from becoming valid.
- undermined behavior: no, line 359 `sample_cnt  <= std_ulogic_vector(unsigned(sample_cnt) + 1);` via sample_cnt -- sample_cnt has a single update mechanism in the sampling_control process (lines 358-360) and there is no runtime override in this RTL that substitutes a different driver.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| sample_cnt | neoTRNG | stores | 6 -> 359 `sample_cnt  <= std_ulogic_vector(unsigned(sample_cnt) + 1);` | CLOCKED_BY clk_i | verified |  | not listed |
| valid_o | neoTRNG | computes | 2 -> 367 `valid_o <= sample_cnt(sample_cnt'left);` | DERIVES_FROM sample_cnt | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sample_cnt <- debias_valid, sample_cnt, sample_en
