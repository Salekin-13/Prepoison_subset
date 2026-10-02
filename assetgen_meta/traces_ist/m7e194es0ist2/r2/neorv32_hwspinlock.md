# neorv32_hwspinlock

**Purpose (model):** A 32-bit hardware spinlock array accessed over a bus: each lock bit lock_q(i) is reset to 0, can be written on a bus request whose address selects an index (sel(i)), and the module replies on the bus with ack/err/data derived from the stored lock bits.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | bus request strobe begins a bus transaction that the module observes (start of read or write) |  | 2 / 2 |
| configure | write operation that sets or clears a lock bit: on a qualifying bus request the chosen lock_q(i) is updated from the request (not bus_req_i.rw) on the clock edge |  | 2 / 2 |
| operate | bus-response production: on each clock the module drives bus_rsp_o.ack, bus_rsp_o.err and bus_rsp_o.data and implements read logic when stb and rw indicate a read |  | 7 / 7 |
| read out | return of lock state: when a read to the locks is performed the reply data is either the masked single-bit vector (lock_q and sel) or the full lock_q vector |  | 4 / 4 |
| reset | synchronous/asynchronous clear of state and response on reset: lock_q bits are cleared and bus_rsp_o is set to rsp_terminate_c on rstn_i = '0' |  | 4 / 4 |

## Concept: Spinlock state (the 32-bit lock file) — the stored per-index lock bits that the module keeps and reports


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| lock_q | neorv32_hwspinlock | stores | 3 -> 45 `lock_q(i) <= not bus_req_i.rw;` | CLOCKED_BY clk_i | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): lock_q <- bus_req_i.addr, bus_req_i.stb, sel

## Concept: Address-to-index decode decision (sel) — which lock bit index a bus request targets


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| sel | neorv32_hwspinlock | computes | 3 -> 51 `sel(i) <= '1' when (bus_req_i.addr(6 downto 2) = std_ulogic_vector(to_unsigned(i, 5))) els` | GATED_BY bus_req_i.addr | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): sel <- bus_req_i.addr
