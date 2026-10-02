# neorv32_boot_rom

**Purpose (model):** Synchronous boot ROM: on clk_i it indexes an embedded ROM (mem_rom_c) with bus_req_i.addr and captures the selected 32-bit word into rdata; when a read strobe (bus_req_i.stb and not bus_req_i.rw) is latched as rden the module drives bus_rsp_o.data with that word and asserts bus_rsp_o.ack (bus_rsp_o.err is tied low).

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | detection and latching of a bus read request (strobe AND read) into rden |  | 3 / 3 |
| operate | read a 32-bit ROM word selected by the request address into the register rdata on clk_i |  | 3 / 3 |
| read out | deliver the stored rdata word onto the bus (bus_rsp_o.data) when rden = '1' |  | 2 / 2 |
| report | report read completion and error status via bus_rsp_o.ack and bus_rsp_o.err |  | 2 / 2 |
| reset | clear the read-enable latch (rden) when rstn_i = '0' |  | 2 / 2 |

## Concept: Boot ROM read data — the 32-bit word taken from the embedded boot ROM and returned on the bus


| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| rdata | neorv32_boot_rom | stores | 2 -> 48 `rdata <= mem_rom_c(to_integer(unsigned(bus_req_i.addr(boot_rom_size_index_c+1 downto 2))))` | CLOCKED_BY clk_i | verified |  |
| bus_rsp_o | neorv32_boot_rom | exit port | 2 -> 64 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` | DERIVES_FROM rdata | occurrence only | no DERIVES_FROM record to 'rdata' at occurrence 2 |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rdata <- bus_req_i.addr

## Concept: Read-response decision — the latched signal that enables returning data and drives the ack (rden)


| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| bus_req_i | neorv32_boot_rom | sets | 3 -> 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | GATES rden | occurrence only | no GATES record to 'rden' at occurrence 3 |
| rden | neorv32_boot_rom | stores | 3 -> 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | CLOCKED_BY clk_i | verified |  |
| bus_rsp_o | neorv32_boot_rom | exit port | 3 -> 65 `bus_rsp_o.ack  <= rden;` | COPIES rden | occurrence only | no COPIES record to 'rden' at occurrence 3 |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rden <- bus_req_i.rw, bus_req_i.stb

## Concept: Requested address (the bus-provided address bits that select which ROM word is read)

- confidentiality: yes-assumed, line 64 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` via bus_rsp_o.data -- bus_req_i.addr is used to index ROM at line 48 and the selected ROM word is presented on bus_rsp_o.data (line 64), so observing the returned word can reveal which address was requested and the integrator may treat the address as sensitive.
- integrity: yes-assumed, line 48 `rdata <= mem_rom_c(to_integer(unsigned(bus_req_i.addr(boot_rom_size_index_c+1 downto 2))));` via bus_req_i.addr -- The ROM index is taken directly from bus_req_i.addr in the mem_access write to rdata (line 48) and that address is supplied by an external writer, so the integrity of the address depends on whether the external writer is trusted.
- availability: yes-rtl, line 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i.stb -- Returning a read requires the request handshake (rden set from bus_req_i.stb and not bus_req_i.rw at line 60); if stb is not asserted the module will not present data for any address, so external signals can block progress.
- undermined behavior: no, line 48 `rdata <= mem_rom_c(to_integer(unsigned(bus_req_i.addr(boot_rom_size_index_c+1 downto 2))));` -- bus_req_i.addr is the single input used to select the ROM index at the mem_access assignment (line 48) and there is no alternate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| bus_req_i | neorv32_boot_rom | sets | 2 -> 48 `rdata <= mem_rom_c(to_integer(unsigned(bus_req_i.addr(boot_rom_size_index_c+1 downto 2))))` | SELECTS rdata | occurrence only | no SELECTS record to 'rdata' at occurrence 2 |
