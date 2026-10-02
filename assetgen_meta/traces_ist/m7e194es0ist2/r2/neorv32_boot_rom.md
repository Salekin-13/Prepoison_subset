# neorv32_boot_rom

**Purpose (model):** Synchronous boot ROM: on each clk_i the module indexes an internal constant ROM (mem_rom_c) with the requested bus address and registers the selected 32-bit word into rdata; when a bus read is requested (bus_req_i.stb and bus_req_i.rw='0') the module asserts rden and drives bus_rsp_o.data with rdata and bus_rsp_o.ack with rden (bus_rsp_o.err is tied '0').

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | read request: the read strobe (bus_req_i.stb with bus_req_i.rw='0') that begins producing a read-enable |  | 2 / 2 |
| operate | ROM read: sample the requested address and register the selected 32-bit ROM word into rdata on the clock edge |  | 3 / 3 |
| read out | deliver the registered ROM word to the bus (bus_rsp_o.data) when the read-enable is asserted |  | 1 / 1 |
| report | report transaction status: drive bus_rsp_o.ack from rden and drive bus_rsp_o.err low |  | 3 / 3 |
| reset | clear the read-enable state (rden) when rstn_i = '0' |  | 3 / 3 |

## Concept: Boot ROM read value — the 32-bit ROM word selected from mem_rom_c and returned to the bus


| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| rdata | neorv32_boot_rom | stores | 2 -> 48 `rdata <= mem_rom_c(to_integer(unsigned(bus_req_i.addr(boot_rom_size_index_c+1 downto 2))))` | CLOCKED_BY clk_i | verified |  |
| bus_rsp_o.data | neorv32_boot_rom | exit port | 2 -> 64 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` | DERIVES_FROM rdata | verified |  |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rdata <- bus_req_i.addr; bus_rsp_o.data <- rden

## Concept: Read-enable decision (rden) — the registered decision that gates data output and produces the acknowledge


| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| rden | neorv32_boot_rom | stores | 3 -> 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | CLOCKED_BY clk_i | verified |  |
| bus_req_i.stb | neorv32_boot_rom | sets | 2 -> 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | GATES rden | verified |  |
| bus_req_i.rw | neorv32_boot_rom | sets | 2 -> 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | GATES rden | verified |  |
| bus_rsp_o.ack | neorv32_boot_rom | exit port | 2 -> 65 `bus_rsp_o.ack  <= rden;` | COPIES rden | verified |  |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rden <- bus_req_i.rw, bus_req_i.stb

## Concept: Requested ROM address — the address presented on bus_req_i.addr that selects which ROM word is read


| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| bus_req_i.addr | neorv32_boot_rom | sets | 2 -> 48 `rdata <= mem_rom_c(to_integer(unsigned(bus_req_i.addr(boot_rom_size_index_c+1 downto 2))))` | SELECTS rdata | verified |  |
