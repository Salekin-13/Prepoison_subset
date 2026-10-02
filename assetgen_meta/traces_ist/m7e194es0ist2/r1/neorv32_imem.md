# neorv32_imem

**Purpose (model):** Instruction memory (IMEM) for the Neorv32 core: accepts bus requests on bus_req_i, indexes the internal ROM (when IMEM_INIT=true) or RAM (when IMEM_INIT=false), produces synchronous read data in rdata and drives the bus response bus_rsp_o (data, ack, err); synchronous to clk_i and reset by rstn_i.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | A bus transaction is started by the bus strobe; bus_req_i.stb gates writes and initiates the read/ack path |  | 5 / 5 |
| operate | Write to IMEM RAM bytes: when (bus_req_i.stb='1') and (bus_req_i.rw='1'), bus_req_i.data and bus_req_i.ben selectively update mem_ram_b0..mem_ram_b3 on the rising clock |  | 20 / 20 |
| operate | Read from IMEM: memory (ROM mem_rom_c or RAM mem_ram_b*) is selected by addr/addr_ff into rdata (synchronously), and rdata is presented to the bus when rden is asserted |  | 12 / 12 |
| report | Acknowledge (bus_rsp_o.ack) is produced by the bus_feedback process (different behavior for ROM vs RAM builds) to report request completion |  | 8 / 8 |
| read out | bus_rsp_o.data is driven from rdata when rden = '1', otherwise driven zero |  | 2 / 2 |
| reset | bus response state is cleared on reset: rstn_i = '0' forces rden <= '0' and bus_rsp_o.ack <= '0' |  | 5 / 5 |

## Concept: Instruction fetch result that this block delivers to the bus (the 32-bit instruction word driven out)

- confidentiality: yes-assumed, line 185 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` via bus_rsp_o.data -- rdata is presented on the external port bus_rsp_o.data when rden='1' (line 185), so an external observer can read fetched instructions and the integrator may treat those instruction words as confidential.
- integrity: yes-assumed, line 114 `if (bus_req_i.stb = '1') and (bus_req_i.rw = '1') then` via bus_req_i -- RAM bytes that feed rdata are written from bus_req_i.data under the write guard (if (bus_req_i.stb='1') and (bus_req_i.rw='1') at line 114 with per-byte assigns at lines 116/119/122/125 and 145/148/151/154), so an external bus master can modify the instruction contents that rdata later delivers (line 185); whether that writer is trusted depends on integration.
- availability: yes-rtl, line 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i -- the read-enable rden is set from bus_req_i.stb and (not bus_req_i.rw) (rden <= bus_req_i.stb and (not bus_req_i.rw) at line 176) and bus_rsp_o.data is driven only when rden='1' (line 185), so external bus_req_i inputs can block instruction delivery.
- undermined behavior: no, line 185 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` via rdata -- bus_rsp_o.data is driven only from rdata (line 185) and there is no alternative debug/test override or separate runtime source in the RTL that substitutes the delivered instruction.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_rsp_o | neorv32_imem | exit port | 5 -> 185 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` | DERIVES_FROM rdata | occurrence only | no DERIVES_FROM record to 'rdata' at occurrence 5 | not listed |
| rdata | neorv32_imem | stores | 2 -> 81 `rdata <= mem_rom_c(to_integer(addr));` | CLOCKED_BY clk_i | verified |  | hit |
| addr | neorv32_imem | computes | 4 -> 101 `addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));` | DERIVES_FROM bus_req_i | occurrence only | no DERIVES_FROM record to 'bus_req_i' at occurrence 4 | hit |
| addr_ff | neorv32_imem | stores | 3 -> 92 `addr_ff <= addr;` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b0 | neorv32_imem | stores | 2 -> 116 `mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b1 | neorv32_imem | stores | 2 -> 119 `mem_ram_b1(to_integer(addr)) <= bus_req_i.data(15 downto 8);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b2 | neorv32_imem | stores | 2 -> 122 `mem_ram_b2(to_integer(addr)) <= bus_req_i.data(23 downto 16);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b3 | neorv32_imem | stores | 2 -> 125 `mem_ram_b3(to_integer(addr)) <= bus_req_i.data(31 downto 24);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i | neorv32_imem | sets | 2 -> 101 `addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));` | SOURCES addr | occurrence only | no SOURCES record to 'addr' at occurrence 2 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rdata <- addr, addr_ff; mem_ram_b0 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b1 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b2 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b3 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb

## Concept: Instruction memory contents (the stored program words held by IMEM: writable RAM bytes mem_ram_b0..b3 or compiled ROM contents)

- confidentiality: yes-assumed, line 185 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` via bus_rsp_o.data -- mem_ram_b0..b3 (written from bus_req_i.data under the write guard at line 114 and per-byte assigns at lines 116/119/122/125 or 145/148/151/154) are read into rdata (lines 128-131 or 159-162) and forwarded to the external bus via bus_rsp_o.data (line 185), so memory contents are observable and may be treated as confidential by the integrator.
- integrity: yes-assumed, line 114 `if (bus_req_i.stb = '1') and (bus_req_i.rw = '1') then` via bus_req_i.data -- mem_ram_b* are updated from bus_req_i.data when (bus_req_i.stb='1') and (bus_req_i.rw='1') (guard at line 114 with per-byte writes at lines 116/119/122/125 and 145/148/151/154), so an external bus writer can modify stored program words; whether that writer is authorized depends on integration.
- availability: yes-rtl, line 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i -- reading memory contents out is gated by rden which is set from bus_req_i.stb and (not bus_req_i.rw) (line 176) and bus_rsp_o.data is only driven when rden='1' (line 185), so external bus_req_i signals can prevent reads and deny progress.
- undermined behavior: no, line 116 `mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0);` via mem_ram_b0..mem_ram_b3 -- mem_ram_b* are written only by the normal write path from bus_req_i.data (per-byte assigns at lines 116/119/122/125 and 145/148/151/154) and ROM contents are compile-time constant (line 44); the RTL contains no runtime debug/test override to substitute or bypass the stored contents.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| mem_ram_b0 | neorv32_imem | stores | 2 -> 116 `mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b1 | neorv32_imem | stores | 2 -> 119 `mem_ram_b1(to_integer(addr)) <= bus_req_i.data(15 downto 8);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b2 | neorv32_imem | stores | 2 -> 122 `mem_ram_b2(to_integer(addr)) <= bus_req_i.data(23 downto 16);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b3 | neorv32_imem | stores | 2 -> 125 `mem_ram_b3(to_integer(addr)) <= bus_req_i.data(31 downto 24);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i | neorv32_imem | sets | 6 -> 116 `mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0);` | SOURCES mem_ram_b0 | occurrence only | no SOURCES record to 'mem_ram_b0' at occurrence 6 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): mem_ram_b0 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b1 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b2 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b3 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb

## Concept: Bus acknowledge produced by IMEM (bus_rsp_o.ack) that reports request completion

- confidentiality: no, line 180 `bus_rsp_o.ack <= bus_req_i.stb;` via bus_rsp_o.ack -- bus_rsp_o.ack is a protocol/status signal intended for the requester and in the IMEM_INIT=false branch is a direct copy of bus_req_i.stb (line 180), so it conveys no secret internal data.
- integrity: yes-rtl, line 180 `bus_rsp_o.ack <= bus_req_i.stb;` via bus_req_i -- bus_rsp_o.ack is assigned from external request signals (ack <= bus_req_i.stb in the IMEM_INIT=false branch at line 180, or ack <= bus_req_i.stb and (not bus_req_i.rw) at line 178), so an external requester can change the ack output by driving bus_req_i without internal protection.
- availability: yes-rtl, line 178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i -- the ack output is driven from bus_req_i.stb (and optionally bus_req_i.rw) per the assignment in the bus_feedback process (line 178/180), so external request signals can force or suppress ack and thereby affect availability of the bus handshake.
- undermined behavior: no, line 178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);` via bus_feedback process -- bus_rsp_o.ack has a single clocked driver in the bus_feedback process (assignments at lines 174, 178, 180) and there is no runtime debug/test override that replaces or bypasses ack generation.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_rsp_o | neorv32_imem | exit port | 3 -> 178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);` | GATED_BY bus_req_i | occurrence only | no GATED_BY record to 'bus_req_i' at occurrence 3 | not listed |
| bus_req_i | neorv32_imem | sets | 25 -> 178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);` | GATES bus_rsp_o | occurrence only | no GATES record to 'bus_rsp_o' at occurrence 25 | not listed |
| bus_req_i | neorv32_imem | sets | 26 -> 178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);` | GATES bus_rsp_o | occurrence only | no GATES record to 'bus_rsp_o' at occurrence 26 | not listed |

## Concept: Read-enable decision (rden) that gates when rdata is forwarded to bus_rsp_o.data

- confidentiality: no, line 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i -- rden is computed directly from bus_req_i.stb and bus_req_i.rw (rden <= bus_req_i.stb and (not bus_req_i.rw) at line 176) and its effect is visible on bus_rsp_o.data (line 185), so it reveals only request state, not secret data.
- integrity: yes-rtl, line 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i -- rden is assigned from external request signals without additional protection (line 176) and it gates forwarding of rdata to the bus (line 185), so an external agent that controls bus_req_i can change rden while the forward is in use and influence what is delivered.
- availability: yes-rtl, line 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i -- rden controls whether bus_rsp_o.data is driven (line 185) and rden itself is derived from bus_req_i.stb and bus_req_i.rw (line 176), so external bus_req_i signals can prevent reads and thus block progress.
- undermined behavior: no, line 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_feedback process -- rden has a single clocked driver in the bus_feedback process (line 176, reset at line 173) and there is no separate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rden | neorv32_imem | stores | 3 -> 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i | neorv32_imem | sets | 23 -> 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | GATES rden | occurrence only | no GATES record to 'rden' at occurrence 23 | not listed |
| bus_req_i | neorv32_imem | sets | 24 -> 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | GATES rden | occurrence only | no GATES record to 'rden' at occurrence 24 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rden <- bus_req_i.rw, bus_req_i.stb
