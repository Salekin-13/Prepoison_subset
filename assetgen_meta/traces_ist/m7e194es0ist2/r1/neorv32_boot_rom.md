# neorv32_boot_rom

**Purpose (model):** A small read-only boot ROM: on each clock it samples the initialized ROM image at an address taken from the bus request and, when a bus read is requested, drives the response bundle (data and ack); err is tied low.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | read-request decision (a bus read is detected) |  | 4 / 4 |
| operate | memory read: select a ROM word by bus_req_i.addr and capture it into rdata on clk_i |  | 3 / 3 |
| read out | deliver the sampled ROM word on the response data port when rden is asserted |  | 2 / 2 |
| report | report read completion via ack (bus_rsp_o.ack driven from rden) |  | 2 / 2 |
| reset | clear the response-enable state (rden) when rstn_i = '0' |  | 3 / 3 |

## Concept: Boot ROM contents (the 32-bit words initialized into mem_rom_c) that the module returns on bus reads

- confidentiality: yes-assumed, line 64 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` via bus_rsp_o.data -- The sampled ROM word (rdata) is presented on the external output bus_rsp_o.data when rden = '1' (concurrent assignment at line 64), so the ROM contents are exposed outside the module.
- integrity: no, line 35 `constant mem_rom_c : mem32_t(0 to boot_rom_size_c-1) := mem32_init_f(bootloader_init_image_c, boot_rom_size_c);` via mem_rom_c -- The ROM image is a constant initialized at line 35 (mem_rom_c := mem32_init_f(...)) and there is no RTL writer that modifies mem_rom_c at runtime.
- availability: yes-rtl, line 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i.stb and bus_req_i.rw -- bus_rsp_o.data is gated by rden (line 64) and rden is driven from bus_req_i.stb and (not bus_req_i.rw) on the clock at line 60, so external request signals can keep rden low and prevent the ROM contents from being output.
- undermined behavior: no, line 64 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` -- The output bus_rsp_o.data has a single concurrent driver (line 64) that selects rdata when rden='1' and the RTL contains no alternate/test/debug override for this path.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| rdata | neorv32_boot_rom | stores | 2 -> 48 `rdata <= mem_rom_c(to_integer(unsigned(bus_req_i.addr(boot_rom_size_index_c+1 downto 2))))` | CLOCKED_BY clk_i | verified |  |
| bus_rsp_o | neorv32_boot_rom | exit port | 2 -> 64 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');` | DERIVES_FROM rdata | occurrence only | no DERIVES_FROM record to 'rdata' at occurrence 2 |
| bus_req_i | neorv32_boot_rom | sets | 2 -> 48 `rdata <= mem_rom_c(to_integer(unsigned(bus_req_i.addr(boot_rom_size_index_c+1 downto 2))))` | SELECTS rdata | occurrence only | no SELECTS record to 'rdata' at occurrence 2 |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rdata <- bus_req_i.addr

## Concept: Read-response decision (rden) that determines when the ROM responds (drives ack and enables data)

- confidentiality: yes-assumed, line 65 `bus_rsp_o.ack  <= rden;` via bus_rsp_o.ack -- rden is directly copied to the external port bus_rsp_o.ack at line 65, exposing the module's response state to observers.
- integrity: yes-rtl, line 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i.stb and bus_req_i.rw -- rden is updated on the clock from external inputs bus_req_i.stb and bus_req_i.rw at line 60 and there is no RTL guard preventing these inputs from changing rden while it is used to gate outputs (lines 64–65).
- availability: yes-rtl, line 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` via bus_req_i.stb and bus_req_i.rw -- External signals bus_req_i.stb and bus_req_i.rw determine rden at line 60, so an external agent can hold rden low and prevent the ROM from responding.
- undermined behavior: no, line 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` -- rden has only the reset assignment (line 58) and the clocked assignment (line 60) in the bus_feedback process and there is no alternate/debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| rden | neorv32_boot_rom | stores | 3 -> 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | CLOCKED_BY clk_i | verified |  |
| bus_req_i | neorv32_boot_rom | sets | 3 -> 60 `rden <= bus_req_i.stb and (not bus_req_i.rw);` | GATES rden | occurrence only | no GATES record to 'rden' at occurrence 3 |
| bus_rsp_o | neorv32_boot_rom | exit port | 3 -> 65 `bus_rsp_o.ack  <= rden;` | COPIES rden | occurrence only | no COPIES record to 'rden' at occurrence 3 |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): rden <- bus_req_i.rw, bus_req_i.stb
