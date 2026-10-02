# neorv32_imem

**Purpose (model):** Instruction memory for the core: it accepts bus requests on bus_req_i, forms an index (addr / addr_ff), reads a 32-bit word into rdata from either a pre-initialized ROM (mem_rom_c) or from RAM byte arrays (mem_ram_b0..mem_ram_b3), optionally accepts bus writes into RAM (when IMEM_INIT = false) controlled by bus_req_i.stb/rw/ben and bus_req_i.data, and drives the bus response bus_rsp_o (ack, data, err).

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | memory-write eligibility (bus write strobes & rw decide whether a bus request will write IMEM bytes) |  | 21 / 21 |
| operate | write bytes from bus_req_i.data into RAM byte-arrays mem_ram_b0..mem_ram_b3 on a clock edge when the write guards hold |  | 36 / 36 |
| read out | fetching a 32-bit word: index computed from bus_req_i.addr, rdata assembled from ROM or RAM bytes, and bus_rsp_o.data driven from rdata when rden is asserted |  | 16 / 16 |
| report | bus response acknowledge event produced on bus_rsp_o.ack according to bus_req_i.stb and bus_req_i.rw (and the IMEM_INIT generic) |  | 11 / 11 |
| reset | response-related registers are cleared when rstn_i = '0' (rden and bus_rsp_o.ack forced '0') |  | 4 / 4 |

## Concept: Instruction memory contents (the 32-bit word fetched and delivered on the bus)

- confidentiality: yes-assumed, line 185 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` via bus_rsp_o.data -- The 32-bit word rdata is presented on the external port bus_rsp_o.data when rden='1' (line 185), so an external requester or observer can read the instruction word even if the integrator considers it secret.
- integrity: yes-assumed, line 116 `mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0);` via bus_req_i.data -- In RAM mode the stored bytes (mem_ram_b0..mem_ram_b3) are written from bus_req_i.data under the write guard ((bus_req_i.stb = '1') and (bus_req_i.rw = '1')) (e.g. mem_ram_b0 <= bus_req_i.data(7 downto 0) at line 116), so an external bus writer can change the instruction contents.
- availability: yes-rtl, line 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i.stb / bus_req_i.rw -- Presentation of rdata is gated by rden and rden is assigned from bus_req_i.stb and bus_req_i.rw (rden <= bus_req_i.stb and (not bus_req_i.rw); line 176) and bus_rsp_o.data is gated by rden (line 185), so external request signals can prevent the word from being output.
- undermined behavior: no, line 185 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` -- bus_rsp_o.data has a single driver that conditionally forwards rdata (line 185) and there is no debug/test override or alternate runtime bypass in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_rsp_o | neorv32_imem | exit port | 5 -> 185 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` | DERIVES_FROM rdata | occurrence only | no DERIVES_FROM record to 'rdata' at occurrence 5 | not listed |
| rdata | neorv32_imem | stores | 2 -> 81 `rdata <= mem_rom_c(to_integer(addr));` | CLOCKED_BY clk_i | verified |  | hit |
| mem_ram_b0 | neorv32_imem | stores | 2 -> 116 `mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b1 | neorv32_imem | stores | 2 -> 119 `mem_ram_b1(to_integer(addr)) <= bus_req_i.data(15 downto 8);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b2 | neorv32_imem | stores | 2 -> 122 `mem_ram_b2(to_integer(addr)) <= bus_req_i.data(23 downto 16);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b3 | neorv32_imem | stores | 2 -> 125 `mem_ram_b3(to_integer(addr)) <= bus_req_i.data(31 downto 24);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i | neorv32_imem | sets | 6 -> 116 `mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0);` | SOURCES mem_ram_b0 | occurrence only | no SOURCES record to 'mem_ram_b0' at occurrence 6 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rdata <- addr, addr_ff; mem_ram_b0 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b1 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b2 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b3 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb

## Concept: Requested address (the bus-provided address used to select which IMEM word is read or written)

- confidentiality: no, line 101 `addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));` via bus_req_i.addr -- addr is directly derived from the external bus_req_i.addr input (line 101) and the requester that supplied the address already knows it, and the RTL does not export the address itself to other ports.
- integrity: yes-assumed, line 101 `addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));` via bus_req_i.addr -- The selected index addr is taken directly from bus_req_i.addr (line 101), an external input, so an external agent controlling the bus can change which IMEM word is selected and thus affect integrity of instruction fetches.
- availability: no, line 101 `addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));` -- addr is assigned concurrently from bus_req_i.addr without internal gating (line 101) and there is no internal enable/stall that the RTL shows which can freeze addr updates (aside from clock/reset).
- undermined behavior: no, line 101 `addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));` -- addr has a single source (the concurrent assignment from bus_req_i.addr at line 101) and there is no alternate runtime override or debug mode in the RTL that replaces it.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_imem | sets | 2 -> 101 `addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));` | SOURCES addr | occurrence only | no SOURCES record to 'addr' at occurrence 2 | not listed |
| addr | neorv32_imem | computes | 4 -> 101 `addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));` | DERIVES_FROM bus_req_i.addr | verified |  | hit |
| addr_ff | neorv32_imem | stores | 3 -> 92 `addr_ff <= addr;` | CLOCKED_BY clk_i | verified |  | not listed |

## Concept: Bus response acknowledge (the ack event driven to the requester)

- confidentiality: no, line 178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);` via bus_rsp_o.ack -- The ack is an explicit handshake output driven to the requester (bus_rsp_o.ack assigned from bus_req_i.stb/(not bus_req_i.rw) in the bus_feedback process; line 178) and is intended to be observed, so it is not treated as secret.
- integrity: no, line 178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);` via bus_feedback process -- bus_rsp_o.ack is produced only by the internal bus_feedback process (lines 170-181) from the request signals and reset, so there is no unintended external writer inside the RTL that modifies ack outside its designed handshake logic.
- availability: yes-rtl, line 178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i.stb -- The ack output is generated from the incoming request signals (e.g. bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw) in the IMEM_INIT branch; line 178), so an external requester controlling bus_req_i.stb can prevent ack and thereby stall progress.
- undermined behavior: no, line 178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);` -- ack has a single internal driver in the bus_feedback process (lines 170-181) and there is no debug/test override or alternate assignment in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_rsp_o | neorv32_imem | exit port | 3 -> 178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);` | GATED_BY bus_req_i.stb | occurrence only | no GATED_BY record to 'bus_req_i.stb' at occurrence 3 | not listed |

## Concept: Read-enable decision rden (the internal read-request latch that gates returned data)

- confidentiality: yes-assumed, line 185 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` via bus_rsp_o.data -- rden gates the external data output (line 185) so observing bus_rsp_o.data (and its absence) reveals the read-enable state to external observers and thus the RTL exposes this internal decision.
- integrity: yes-rtl, line 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i.stb / bus_req_i.rw -- rden is assigned from external request signals (rden <= bus_req_i.stb and (not bus_req_i.rw); line 176) and there is no protection preventing those inputs from changing rden while it is gating output, so an external actor can change rden at times that affect operation.
- availability: yes-rtl, line 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i.stb -- Because rden is driven from bus_req_i.stb/(not bus_req_i.rw) (line 176) an external requester can prevent or force rden and thereby stop or allow the module from presenting read data, affecting availability.
- undermined behavior: no, line 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` -- rden is written by a single internal process (line 176) with no alternate debug/test override or secondary driver shown in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rden | neorv32_imem | stores | 3 -> 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i | neorv32_imem | sets | 23 -> 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | GATES rden | occurrence only | no GATES record to 'rden' at occurrence 23 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rden <- bus_req_i.rw, bus_req_i.stb
