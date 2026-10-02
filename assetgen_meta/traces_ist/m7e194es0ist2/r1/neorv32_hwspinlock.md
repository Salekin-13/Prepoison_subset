# neorv32_hwspinlock

**Purpose (model):** Implements a 32-entry hardware spinlock array: it samples bus_req_i, decodes an index, updates the corresponding lock bit lock_q(i) on a clock edge when the request and index select match, and returns lock state and handshake fields on bus_rsp_o. Registers are cleared on rstn_i.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | bus request strobe that begins an access and is reflected as the response ACK |  | 3 / 3 |
| operate | update of a selected lock bit: conditional clocked assignment of lock_q(i) <= not bus_req_i.rw when the request, address decode and sel(i) match |  | 4 / 4 |
| read out | return of lock state (masked by selection or full vector) on bus_rsp_o.data for read accesses |  | 5 / 5 |
| report | response fields ack and err driven each cycle (ack mirrors request strobe; err tied '0') and data defaulted to zero before conditional read assignment |  | 3 / 3 |
| reset | lock_q entries cleared to '0' on rstn_i='0' and bus_rsp_o set to rsp_terminate_c while reset holds |  | 5 / 5 |

## Concept: Per-index lock state (the 32-bit lock_q vector) held across cycles

- confidentiality: yes-assumed, line 70 `bus_rsp_o.data <= lock_q;` via bus_rsp_o.data -- The RTL drives the full lock_q vector to the output at line 70 (bus_rsp_o.data <= lock_q) on a read request, so an external observer can learn the lock state.
- integrity: yes-assumed, line 45 `lock_q(i) <= not bus_req_i.rw;` via bus_req_i -- Each lock bit is written from the external bus at line 45 (lock_q(i) <= not bus_req_i.rw) under the bus request guard, so an external writer can change stored lock state.
- availability: yes-rtl, line 44 `if (bus_req_i.stb = '1') and (bus_req_i.addr(7) = '0') and (sel(i) = '1') then` via bus_req_i.stb -- Writes to lock_q occur only when the write condition on line 44 holds ((bus_req_i.stb='1') and address decode and sel), so external bus signals can freeze or force lock updates and affect availability.
- undermined behavior: no, line 45 `lock_q(i) <= not bus_req_i.rw;` -- lock_q is driven only by the internal spinlock process assignment (line 45) with no alternate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| lock_q | neorv32_hwspinlock | stores | 3 -> 45 `lock_q(i) <= not bus_req_i.rw;` | CLOCKED_BY clk_i | verified |  | hit |
| bus_rsp_o | neorv32_hwspinlock | exit port | 6 -> 68 `bus_rsp_o.data <= lock_q and sel;` | DERIVES_FROM lock_q | occurrence only | no DERIVES_FROM record to 'lock_q' at occurrence 6 | not listed |
| bus_req_i | neorv32_hwspinlock | sets | 4 -> 45 `lock_q(i) <= not bus_req_i.rw;` | SOURCES lock_q | occurrence only | no SOURCES record to 'lock_q' at occurrence 4 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): lock_q <- bus_req_i.addr, bus_req_i.stb, sel

## Concept: Selected lock index (the one-hot sel vector computed from bus_req_i.addr(6 downto 2)) used to pick which lock bit an access targets

- confidentiality: yes-assumed, line 68 `bus_rsp_o.data <= lock_q and sel;` via bus_rsp_o.data -- The masked read at line 68 (bus_rsp_o.data <= lock_q and sel) exposes the one-hot sel pattern to an external observer, revealing which index was selected.
- integrity: yes-rtl, line 51 `sel(i) <= '1' when (bus_req_i.addr(6 downto 2) = std_ulogic_vector(to_unsigned(i, 5))) else '0';` via bus_req_i.addr -- sel is computed directly from the external address at line 51 and is sampled in the write guard at line 44, so changes to bus_req_i.addr can alter sel while a write occurs.
- availability: yes-rtl, line 51 `sel(i) <= '1' when (bus_req_i.addr(6 downto 2) = std_ulogic_vector(to_unsigned(i, 5))) else '0';` via bus_req_i.addr -- sel is derived from the external bus address (line 51), so control of bus_req_i.addr can hold or change selection and thereby affect whether particular accesses proceed.
- undermined behavior: no, line 51 `sel(i) <= '1' when (bus_req_i.addr(6 downto 2) = std_ulogic_vector(to_unsigned(i, 5))) else '0';` -- sel has a single combinational driver at line 51 and there is no alternate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| sel | neorv32_hwspinlock | computes | 3 -> 51 `sel(i) <= '1' when (bus_req_i.addr(6 downto 2) = std_ulogic_vector(to_unsigned(i, 5))) els` | GATED_BY bus_req_i.addr | verified |  | hit |
| bus_req_i | neorv32_hwspinlock | sets | 5 -> 51 `sel(i) <= '1' when (bus_req_i.addr(6 downto 2) = std_ulogic_vector(to_unsigned(i, 5))) els` | GATES sel | occurrence only | no GATES record to 'sel' at occurrence 5 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sel <- bus_req_i.addr

## Concept: Bus request handshake (request strobe and response ACK) — the start event of an access and the ACK the module delivers


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_hwspinlock | sets | 6 -> 63 `bus_rsp_o.ack  <= bus_req_i.stb;` | CARRIES bus_rsp_o.ack | occurrence only | no CARRIES record to 'bus_rsp_o.ack' at occurrence 6 | not listed |
| bus_rsp_o | neorv32_hwspinlock | exit port | 3 -> 63 `bus_rsp_o.ack  <= bus_req_i.stb;` | COPIES bus_req_i.stb | occurrence only | no COPIES record to 'bus_req_i.stb' at occurrence 3 | not listed |

## Concept: Bus operation type (the rw bit) — the request's read/write indicator that determines the stored lock value and read behavior


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_hwspinlock | sets | 4 -> 45 `lock_q(i) <= not bus_req_i.rw;` | SOURCES lock_q | occurrence only | no SOURCES record to 'lock_q' at occurrence 4 | not listed |
| bus_rsp_o | neorv32_hwspinlock | exit port | 6 -> 68 `bus_rsp_o.data <= lock_q and sel;` | GATED_BY bus_req_i.rw | occurrence only | no GATED_BY record to 'bus_req_i.rw' at occurrence 6 | not listed |
