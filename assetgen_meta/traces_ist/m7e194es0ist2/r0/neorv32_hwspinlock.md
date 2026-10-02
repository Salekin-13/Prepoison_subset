# neorv32_hwspinlock

**Purpose (model):** Implements a 32-entry hardware spinlock array: it captures bus requests (bus_req_i), updates per-index lock bits (lock_q(i)) on clock edges when the request and address select an index, and drives a bus response (bus_rsp_o) that ACKs requests and returns lock state (masked by the index select).

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | bus request strobe (bus_req_i.stb) that begins a read or write access |  | 3 / 3 |
| configure | write to a lock bit: update lock_q(i) from the request (lock_q(i) <= not bus_req_i.rw) under index selection |  | 4 / 4 |
| read out | readback of lock state delivered on bus_rsp_o.data (either masked by sel when addr(7)='0' or the full lock_q vector) |  | 5 / 5 |
| report | bus response fields produced for each request: ack (bus_rsp_o.ack) and err (bus_rsp_o.err) |  | 2 / 2 |
| reset | reset forces lock bits and the response port to known values |  | 4 / 4 |

## Concept: Bus write eligibility (per-index) — the module's decision whether a given bus request should update a particular lock_q(i)


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_i | neorv32_hwspinlock | sets | 2 -> 44 `if (bus_req_i.stb = '1') and (bus_req_i.addr(7) = '0') and (sel(i) = '1') then` | GATES lock_q | occurrence only | no GATES record to 'lock_q' at occurrence 2 | not listed |
| bus_req_i | neorv32_hwspinlock | sets | 5 -> 51 `sel(i) <= '1' when (bus_req_i.addr(6 downto 2) = std_ulogic_vector(to_unsigned(i, 5))) els` | GATES sel | occurrence only | no GATES record to 'sel' at occurrence 5 | not listed |
| sel | neorv32_hwspinlock | computes | 3 -> 51 `sel(i) <= '1' when (bus_req_i.addr(6 downto 2) = std_ulogic_vector(to_unsigned(i, 5))) els` | GATED_BY bus_req_i.addr | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sel <- bus_req_i.addr

## Concept: Spinlock state — the 32-bit register vector (lock_q) that holds each lock bit


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| lock_q | neorv32_hwspinlock | stores | 3 -> 45 `lock_q(i) <= not bus_req_i.rw;` | CLOCKED_BY clk_i | verified |  | hit |
| bus_req_i | neorv32_hwspinlock | sets | 4 -> 45 `lock_q(i) <= not bus_req_i.rw;` | SOURCES lock_q | occurrence only | no SOURCES record to 'lock_q' at occurrence 4 | not listed |
| bus_rsp_o | neorv32_hwspinlock | exit port | 6 -> 68 `bus_rsp_o.data <= lock_q and sel;` | DERIVES_FROM lock_q | occurrence only | no DERIVES_FROM record to 'lock_q' at occurrence 6 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): lock_q <- bus_req_i.addr, bus_req_i.stb, sel
