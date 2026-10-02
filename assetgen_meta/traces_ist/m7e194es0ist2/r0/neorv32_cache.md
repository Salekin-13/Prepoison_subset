# neorv32_cache

**Purpose (model):** Front-end cache between a host interface and a system bus: it accepts and buffers host requests, decodes addresses into tag/index/offset, consults the on-chip cache memory to serve hits or issues bus requests to fetch cache blocks (download), writes fetched data into the cache memory, and forwards responses to the host.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | accept or latch a host request (strobe / fence) into the controller buffer |  | 8 / 8 |
| operate | lookup: derive tag/index/offset from the host address and decide hit vs miss or direct bypass |  | 12 / 12 |
| operate | direct response / forward: forward a host request to the system bus and return bus response to host |  | 8 / 8 |
| operate | download (miss handling): issue block-read requests to the bus, receive bus responses, write fetched words into cache memory and finish |  | 29 / 29 |
| read out | return cached read data to the host (rdata path) |  | 5 / 5 |
| reset | clear controller and memory valid/tag state on reset |  | 14 / 14 |

## Concept: Controller finite-state (FSM) value that determines which outputs and actions the cache engine takes

- confidentiality: yes-assumed, line 191 `host_rsp_o.ack <= '1';` via host_rsp_o.ack -- The FSM state is reflected on externally driven signals (for example host_rsp_o.ack asserted under S_LOOKUP at line 191), so an external observer can infer the controller state and the integrator may treat that state as secret.
- integrity: yes-rtl, line 126 `ctrl <= ctrl_nxt;` via ctrl_nxt (driven by host_req_i and bus_rsp_i) -- The register ctrl is updated unconditionally at the clock edge (ctrl <= ctrl_nxt at line 126) and ctrl_nxt is computed from untrusted external inputs (e.g. host_req_i inputs at lines 171-175 and bus_rsp_i inputs at lines 242-243), so outside inputs can change the FSM state while it controls behavior.
- availability: yes-rtl, line 210 `if (bus_rsp_i.ack = '1') then` via bus_rsp_i.ack -- Several states wait for bus responses (e.g. S_DIRECT_RSP checks bus_rsp_i.ack at line 210), so an external bus that withholds acknowledgements can stall the FSM and prevent progress.
- undermined behavior: no, line 126 `ctrl <= ctrl_nxt;` via ctrl (ctrl <= ctrl_nxt) -- The FSM value is driven only by the clocked update ctrl <= ctrl_nxt (line 126) with next-state logic; there is no separate debug/test override that directly substitutes the FSM state.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl | neorv32_cache | stores | 10 -> 126 `ctrl <= ctrl_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl_nxt.state | neorv32_cache | computes | 10 -> 211 `ctrl_nxt.state <= S_IDLE;` | SELECTED_BY ctrl.state | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl_nxt.state <- bus_rsp_i.ack, cache_i.sta_hit, ctrl.buf_dir, ctrl.buf_err, ctrl.buf_req, ctrl.buf_sync, ctrl.ofs, ctrl.state ...

## Concept: Host request inputs (address and request/privilege flags) that set which cache line / bus transaction is requested

- confidentiality: yes-assumed, line 159 `bus_req_o       <= host_req_i;` via bus_req_o -- Host request fields are forwarded to the external bus (bus_req_o <= host_req_i at line 159), so external parties can observe requested addresses/flags and the integrator may treat those inputs as secret.
- integrity: yes-assumed, line 159 `bus_req_o       <= host_req_i;` via host_req_i (external writer) -- The request values originate from an external writer and are carried/forwarded by the RTL (bus_req_o <= host_req_i at line 159 and tag/idx derived at lines 180-181), so whether that writer is trusted depends on integration.
- availability: no, line 137 `ctrl_nxt.buf_req  <= ctrl.buf_req or host_req_i.stb;` via host_req_i.stb -- The controller combinationally ORs host_req_i.stb into the request buffer (ctrl_nxt.buf_req <= ctrl.buf_req or host_req_i.stb at line 137), so the RTL does not block acceptance of host requests.
- undermined behavior: no, line 37 `host_req_i : in  bus_req_t;` via host_req_i (external port) -- host_req_i is driven by the external host (port at line 37) and the design contains no internal debug/test mechanism that replaces that input value.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| host_req_i | neorv32_cache | sets | 13 -> 180 `ctrl_nxt.tag     <= host_req_i.addr(31 downto 32-tag_size_c);` | SOURCES ctrl_nxt.tag | occurrence only | no SOURCES record to 'ctrl_nxt.tag' at occurrence 13 | not listed |

## Concept: Bus request sent to the system bus (address, control bits, strobe) that the cache issues on misses or bypasses

- confidentiality: yes-assumed, line 159 `bus_req_o       <= host_req_i;` via bus_req_o -- Bus requests are emitted on the module's external bus port (bus_req_o <= host_req_i at line 159), so addresses and control bits are observable outside the IP and may be sensitive.
- integrity: yes-rtl, line 159 `bus_req_o       <= host_req_i;` via host_req_i and ctrl.state -- bus_req_o is driven both by a direct copy of host_req_i (line 159) and by controller-computed fields in different states (e.g. addr/stb/rw/lock in lines 227-231,238-240), so external inputs and state can change the outgoing bus request while it matters.
- availability: yes-rtl, line 210 `if (bus_rsp_i.ack = '1') then` via bus_rsp_i.ack -- Request-response progression depends on external bus acknowledgements (bus_rsp_i.ack is checked at line 210 and 243), so the external bus can withhold ack and stall the request/response flow.
- undermined behavior: yes-rtl, line 227 `bus_req_o.addr  <= ctrl.tag & ctrl.idx & ctrl.ofs & "00";` via ctrl.state -- The controller's state selects alternate drivers for bus_req_o (default copy from host at line 159 versus controller-computed address/control in S_DOWNLOAD_REQ at line 227), so a state-selected mode substitutes a different source for the bus request.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_o | neorv32_cache | exit port | 2 -> 159 `bus_req_o       <= host_req_i;` | COPIES host_req_i | verified |  | not listed |

## Concept: Cache-memory control commands and write-data that create/clear/invalidate cache lines and write fetched words into memory

- confidentiality: yes-assumed, line 283 `clr_i   => cache_o.cmd_clr,` via neorv32_cache_memory_inst.clr_i -- Cache control commands and write data are forwarded into the memory instance (clr_i/new_i/inv_i/addr_i/we_i/wdata_i mapped at lines 283-290), and the memory's contents and responses are observable to external masters (e.g. host_rsp_o at line 156), so these commands can be inferred externally.
- integrity: yes-rtl, line 236 `cache_o.data   <= bus_rsp_i.data;` via bus_rsp_i.data -- cache_o.data is driven directly from bus_rsp_i.data in S_DOWNLOAD_RSP (line 236) and cache_o.we is asserted (line 237), so an external bus supplying responses can control what is written into the cache memory.
- availability: yes-rtl, line 243 `if (bus_rsp_i.ack = '1') then` via bus_rsp_i.ack -- The download sequence advances ofs and state only when bus_rsp_i.ack = '1' (checked at line 243), so an external bus that withholds acknowledgements can block memory updates and stall downloads.
- undermined behavior: no, line 226 `cache_o.cmd_new <= '1';` via ctrl.state -- The cache control commands are generated only by the controller state and bus responses (e.g. cache_o.cmd_new at line 226 and cache_o.data/we at lines 236-237); there is no separate debug/test override that directly substitutes these command sources.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cache_o.cmd_new | neorv32_cache | computes | 3 -> 226 `cache_o.cmd_new <= '1';` | SELECTED_BY ctrl.state | verified |  | not listed |
| cache_o.cmd_clr | neorv32_cache | computes | 3 -> 219 `cache_o.cmd_clr   <= '1';` | SELECTED_BY ctrl.state | verified |  | not listed |
| cache_o.cmd_inv | neorv32_cache | computes | 3 -> 255 `cache_o.cmd_inv <= '1';` | SELECTED_BY ctrl.state | verified |  | not listed |
| cache_o.addr | neorv32_cache | computes | 3 -> 225 `cache_o.addr    <= ctrl.tag & ctrl.idx & ctrl.ofs & "00";` | SELECTED_BY ctrl.state | verified |  | not listed |
| cache_o.data | neorv32_cache | computes | 3 -> 236 `cache_o.data   <= bus_rsp_i.data;` | SELECTED_BY ctrl.state | verified |  | not listed |
| cache_o.we | neorv32_cache | computes | 4 -> 237 `cache_o.we     <= (others => '1');` | SELECTED_BY ctrl.state | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): cache_o.cmd_new <- ctrl.state; cache_o.cmd_clr <- ctrl.state; cache_o.cmd_inv <- ctrl.buf_err, ctrl.state; cache_o.addr <- ctrl.state; cache_o.data <- ctrl.state; cache_o.we <- cache_i.sta_hit, ctrl.buf_dir, ctrl.state, host_req_i.rw

## Concept: Cache hit indicator delivered by the on-chip cache memory (hit signal) that the controller reads to choose hit vs miss behavior

- confidentiality: yes-assumed, line 191 `host_rsp_o.ack <= '1';` via host_rsp_o.ack -- The hit result from the memory influences externally visible responses (host_rsp_o.ack asserted for hits at line 191), so an external observer can learn whether a given access hit the cache and the integrator may treat that as sensitive information.
- integrity: yes-rtl, line 405 `hit_o <= '1' when (valid_mem_rd = '1') and (tag_mem_rd = acc_tag) else '0';` via neorv32_cache_memory_inst.hit_o -- hit_o is computed inside the memory from valid_mem_rd and tag_mem_rd at line 405, and valid/tag bits are updated by clr_i/inv_i/new_i driven by the controller and bus responses (lines 380-386,397), so external inputs that influence those signals can change hit behavior while the controller depends on it.
- availability: yes-rtl, line 380 `if (clr_i = '1') then` via neorv32_cache_memory_inst.clr_i (cache_o.cmd_clr) -- valid_mem is cleared when clr_i = '1' (status_memory at line 380), and the controller can assert cache_o.cmd_clr (line 219) in response to fence requests, so external actions can force invalidation and prevent hits, affecting availability.
- undermined behavior: no, line 405 `hit_o <= '1' when (valid_mem_rd = '1') and (tag_mem_rd = acc_tag) else '0';` via neorv32_cache_memory hit logic -- The hit indicator is computed by the memory's compare logic at line 405 and there is no separate debug/test input that force-writes or bypasses the hit signal directly.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cache_i.sta_hit | neorv32_cache | computes | 3 -> 286 `hit_o   => cache_i.sta_hit,` | CONNECTS neorv32_cache_memory_inst.hit_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | hit |

## Concept: Read data returned from cache memory (rdata) that the module forwards to the host

- confidentiality: yes-assumed, line 156 `host_rsp_o.data <= cache_i.data;` via host_rsp_o.data -- Read data produced by the memory is forwarded to the external host (host_rsp_o.data <= cache_i.data at line 156), so externally observable outputs expose cached or fetched data and it may be sensitive.
- integrity: yes-rtl, line 413 `if (we_i(0) = '1') then` via we_i / wdata_i (memory write path) -- The memory bytes are written under we_i control (e.g. data_mem_b0 <= wdata_i(7 downto 0) when we_i(0) = '1' at line 413) and wdata_i can be supplied from bus responses (cache_o.data <= bus_rsp_i.data at line 236), so external writers can change what is later read out.
- availability: yes-rtl, line 243 `if (bus_rsp_i.ack = '1') then` via bus_rsp_i.ack -- Block downloads and writes that populate the read data proceed only when bus_rsp_i.ack is asserted (line 243), so an external bus that withholds ack can stall availability of read data.
- undermined behavior: yes-rtl, line 209 `host_rsp_o <= bus_rsp_i;` via ctrl.state -- In S_DIRECT_RSP the controller forwards bus responses directly to the host (host_rsp_o <= bus_rsp_i at line 209), providing an alternate bypass path that replaces or bypasses cached rdata.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cache_i.data | neorv32_cache | computes | 3 -> 291 `rdata_o => cache_i.data` | CONNECTS neorv32_cache_memory_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| host_rsp_o | neorv32_cache | exit port | 4 -> 156 `host_rsp_o.data <= cache_i.data;` | COPIES cache_i.data | occurrence only | no COPIES record to 'cache_i.data' at occurrence 4 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): host_rsp_o <- ctrl.state

## Concept: Download error flag (buf_err) that causes invalidation and error reporting when a block download fails

- confidentiality: yes-assumed, line 257 `host_rsp_o.err  <= '1';` via host_rsp_o.err -- When a download has errors the flag causes host_rsp_o.err to be asserted (line 257), so external parties learn the error condition and the flag may be considered sensitive.
- integrity: yes-rtl, line 242 `ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err;` via bus_rsp_i.err -- The next-state buffer accumulates bus response errors (ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err at line 242) and that stored flag controls invalidation and error replies, so external bus error signals can set this flag.
- availability: no, line 183 `ctrl_nxt.buf_err <= '0';` via ctrl_nxt.buf_err -- The flag is explicitly cleared in normal lookup flow (ctrl_nxt.buf_err <= '0' at line 183) and its presence leads to a terminal handling path (S_DOWNLOAD_DONE), so the flag itself does not create an unbounded hang in the RTL.
- undermined behavior: no, line 242 `ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err;` via ctrl.buf_err -- buf_err is computed from bus response error bits and carried in the controller state (line 242); there is no separate debug/test override that substitutes a different source for this flag.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl | neorv32_cache | stores | 10 -> 126 `ctrl <= ctrl_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl_nxt.buf_err | neorv32_cache | computes | 4 -> 242 `ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err;` | SELECTED_BY ctrl.state | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl_nxt.buf_err <- bus_rsp_i.err, ctrl.buf_err, ctrl.state
