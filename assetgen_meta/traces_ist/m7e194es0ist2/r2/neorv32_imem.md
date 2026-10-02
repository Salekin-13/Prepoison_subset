# neorv32_imem

**Purpose (model):** Processor-internal instruction memory: accepts bus requests (bus_req_i), maps the bus address to an internal index, returns a 32-bit word on bus_rsp_o.data and an acknowledge on bus_rsp_o.ack, and (when configured as RAM) accepts per-byte writes into mem_ram_b0..b3. Sequencing uses clk_i and rstn_i.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | Per-byte writes into instruction RAM: bus_req_i.data -> mem_ram_b0..mem_ram_b3 at addr when (bus_req_i.stb = '1') and (bus_req_i.rw = '1'), gated by bus_req_i.ben bits (RAM builds only). |  | 25 / 25 |
| read out | Instruction fetch: select a 32-bit word from ROM or RAM into rdata and present it on bus_rsp_o.data when rden = '1'. |  | 13 / 13 |
| report | Acknowledge the bus request: bus_rsp_o.ack is driven from bus_req_i.stb (and, for IMEM_INIT=true, from (not bus_req_i.rw)). |  | 8 / 8 |
| reset | Reset clears response state: rstn_i = '0' forces rden <= '0' and bus_rsp_o.ack <= '0'. |  | 4 / 4 |

## Concept: Instruction memory contents — the 32-bit instruction words the block holds and delivers to requesters


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rdata | neorv32_imem | stores | 2 -> 81 `rdata <= mem_rom_c(to_integer(addr));` | CLOCKED_BY clk_i | verified |  | hit |
| bus_rsp_o | neorv32_imem | exit port | 5 -> 185 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` | DERIVES_FROM rdata | occurrence only | no DERIVES_FROM record to 'rdata' at occurrence 5 | not listed |
| mem_ram_b0 | neorv32_imem | stores | 2 -> 116 `mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b1 | neorv32_imem | stores | 2 -> 119 `mem_ram_b1(to_integer(addr)) <= bus_req_i.data(15 downto 8);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b2 | neorv32_imem | stores | 2 -> 122 `mem_ram_b2(to_integer(addr)) <= bus_req_i.data(23 downto 16);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b3 | neorv32_imem | stores | 2 -> 125 `mem_ram_b3(to_integer(addr)) <= bus_req_i.data(31 downto 24);` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rdata <- addr, addr_ff; mem_ram_b0 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b1 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b2 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b3 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb

## Concept: Writable instruction memory — the ability for bus writes to modify IMEM bytes (RAM builds)


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| mem_ram_b0 | neorv32_imem | stores | 2 -> 116 `mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b1 | neorv32_imem | stores | 2 -> 119 `mem_ram_b1(to_integer(addr)) <= bus_req_i.data(15 downto 8);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b2 | neorv32_imem | stores | 2 -> 122 `mem_ram_b2(to_integer(addr)) <= bus_req_i.data(23 downto 16);` | CLOCKED_BY clk_i | verified |  | not listed |
| mem_ram_b3 | neorv32_imem | stores | 2 -> 125 `mem_ram_b3(to_integer(addr)) <= bus_req_i.data(31 downto 24);` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_i | neorv32_imem | sets | 3 -> 114 `if (bus_req_i.stb = '1') and (bus_req_i.rw = '1') then` | GATES mem_ram_b0 | occurrence only | no GATES record to 'mem_ram_b0' at occurrence 3 | not listed |
| bus_req_i | neorv32_imem | sets | 6 -> 116 `mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0);` | SOURCES mem_ram_b0 | occurrence only | no SOURCES record to 'mem_ram_b0' at occurrence 6 | not listed |
| bus_req_i | neorv32_imem | sets | 5 -> 115 `if (bus_req_i.ben(0) = '1') then` | GATES mem_ram_b0 | occurrence only | no GATES record to 'mem_ram_b0' at occurrence 5 | not listed |
| addr | neorv32_imem | computes | 4 -> 101 `addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));` | DERIVES_FROM bus_req_i.addr | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): mem_ram_b0 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b1 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b2 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb; mem_ram_b3 <- addr, bus_req_i.ben, bus_req_i.rw, bus_req_i.stb

## Concept: Effective memory index — the internal address used to select which memory word is read or written


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_imem | sets | 2 -> 101 `addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));` | SOURCES addr | occurrence only | no SOURCES record to 'addr' at occurrence 2 | not listed |
| addr | neorv32_imem | computes | 4 -> 101 `addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));` | DERIVES_FROM bus_req_i.addr | verified |  | hit |
| addr_ff | neorv32_imem | stores | 3 -> 92 `addr_ff <= addr;` | CLOCKED_BY clk_i | verified |  | not listed |

## Concept: Read-response control — the stored read-enable (rden) and the outgoing acknowledge (bus_rsp_o.ack) that govern delivery of fetch results


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rden | neorv32_imem | stores | 3 -> 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i | neorv32_imem | sets | 23 -> 176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | GATES rden | occurrence only | no GATES record to 'rden' at occurrence 23 | not listed |
| bus_rsp_o | neorv32_imem | exit port | 3 -> 178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);` | GATED_BY bus_req_i.stb | occurrence only | no GATED_BY record to 'bus_req_i.stb' at occurrence 3 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rden <- bus_req_i.rw, bus_req_i.stb
