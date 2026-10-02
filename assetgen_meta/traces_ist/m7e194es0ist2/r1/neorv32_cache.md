# neorv32_cache

**Purpose (model):** Arbitrate host memory requests (host_req_i), perform a cache tag/index lookup and either return data from the local cache or forward requests to the external bus (bus_req_o). It instantiates and drives neorv32_cache_memory (clr/inv/new, addr/we/wdata) and returns responses to the host via host_rsp_o while progressing a control FSM (ctrl).

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | Host request ingress and buffering: a host request (strobe/fence/addr/data) is sampled and buffered (buf_req / buf_sync / buf_dir) and the FSM advances from S_IDLE to S_LOOKUP. |  | 7 / 7 |
| operate | Lookup and decision: compute tag/ index/ offset from host_req_i.addr, check cache_i.sta_hit and READ_ONLY/ rw to choose direct response, write-through, or start a download/refill. |  | 11 / 11 |
| operate | Direct response path: when direct/bypass or on hit+read, assert bus_req_o/stb or forward bus_rsp_i to host_rsp_o and return ack; FSM transitions on bus_rsp_i.ack. |  | 8 / 8 |
| operate | Download/refill sequence: issue bus read(s) (bus_req_o.addr/rw/lock/stb), assert cache_o.cmd_new, accept bus_rsp_i.data into cache_o.data with cache_o.we, increment ctrl.ofs until line is complete, then on success either leave cache line valid or on error invalidate and report. |  | 22 / 22 |
| report | Produce responses to the host (host_rsp_o): ack/err/data are driven from cache_i.data or forwarded bus_rsp_i fields depending on state. |  | 7 / 7 |
| read out | Cache memory readback: neorv32_cache_memory returns rdata_o (rdata_o assembled from data_mem_b0..b3) on clock edge and that value is presented to the top-level via the cache_i.data connection and copied to host_rsp_o.data. |  | 10 / 10 |
| lock | Bus lock during multi-beat download: bus_req_o.lock is asserted while the controller issues the multi-beat read for a cache line. |  | 4 / 4 |
| reset | Synchronous reset clears the control record and the memory valid bits: ctrl and its fields are forced to known defaults and valid_mem is cleared. |  | 10 / 10 |

## Concept: Control FSM and buffered request state (the controller record that holds the current state, buffered request flags and address decomposition: state, buf_req, buf_sync, buf_err, buf_dir, tag, idx, ofs)

- confidentiality: yes-assumed, line 227 `bus_req_o.addr  <= ctrl.tag & ctrl.idx & ctrl.ofs & "00";` via bus_req_o.addr -- ctrl holds address decomposition derived from host_req_i.addr which is emitted on the external bus as bus_req_o.addr in S_DOWNLOAD_REQ (line 227), so an external observer could learn the controller's address fields.
- integrity: yes-rtl, line 137 `ctrl_nxt.buf_req  <= ctrl.buf_req or host_req_i.stb;` via host_req_i -- ctrl fields are driven from external inputs (e.g. ctrl_nxt.buf_req <= ctrl.buf_req or host_req_i.stb at line 137) and the register is captured unconditionally on the clock (ctrl <= ctrl_nxt at line 126) while the FSM uses these fields (e.g. decision at line 170), so external inputs can change controller state/flags while they are in use.
- availability: yes-rtl, line 243 `if (bus_rsp_i.ack = '1') then` via bus_rsp_i.ack -- progress of the download sequence and ctrl.ofs advancement is gated on bus_rsp_i.ack (the branch and increment at line 243-244), so an external bus not asserting ack can stall the controller and freeze its state progression.
- undermined behavior: no, line 126 `ctrl <= ctrl_nxt;` -- The ctrl record has a single synchronous driver 'ctrl <= ctrl_nxt' on the rising clock (line 126) and there is no separate debug/test override that replaces ctrl's assignment in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl | neorv32_cache | stores | 10 -> 126 `ctrl <= ctrl_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
| ctrl_nxt.state | neorv32_cache | computes | 10 -> 211 `ctrl_nxt.state <= S_IDLE;` | SELECTED_BY ctrl.state | verified |  | not listed |
| host_req_i | neorv32_cache | sets | 3 -> 137 `ctrl_nxt.buf_req  <= ctrl.buf_req or host_req_i.stb;` | GATES ctrl_nxt.buf_req | occurrence only | no GATES record to 'ctrl_nxt.buf_req' at occurrence 3 | not listed |
| bus_rsp_i | neorv32_cache | sets | 4 -> 210 `if (bus_rsp_i.ack = '1') then` | GATES ctrl_nxt.state | occurrence only | no GATES record to 'ctrl_nxt.state' at occurrence 4 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl_nxt.state <- bus_rsp_i.ack, cache_i.sta_hit, ctrl.buf_dir, ctrl.buf_err, ctrl.buf_req, ctrl.buf_sync, ctrl.ofs, ctrl.state ...

## Concept: Cached contents (the data bytes and the address/tags that determine where a line is stored and read)

- confidentiality: yes-assumed, line 156 `host_rsp_o.data <= cache_i.data;` via host_rsp_o.data -- cached read data flows out of the memory to host_rsp_o.data (memory rdata_o -> cache_i.data -> host_rsp_o.data at line 156), so external observers can read cached contents and thus confidentiality depends on integration.
- integrity: yes-rtl, line 414 `data_mem_b0(to_integer(unsigned(acc_adr))) <= wdata_i(7 downto 0);` via cache_o.we / we_i -- data memory bytes are written in the data_memory process when we_i bits are asserted (write at line 414, guarded by we_i(0) at line 413) and we_i is driven by cache_o.we coming from host_req_i writes (line 194) or by the refill path (cache_o.we = (others => '1') at line 237), so external host or bus inputs can change cached contents without an internal protective guard.
- availability: yes-rtl, line 243 `if (bus_rsp_i.ack = '1') then` via bus_rsp_i.ack -- the refill/download sequence advances and writes cache lines conditioned on bus_rsp_i.ack (line 243-244), so an external bus not asserting ack can prevent cache fills and thereby block cache availability.
- undermined behavior: yes-rtl, line 209 `host_rsp_o <= bus_rsp_i;` via ctrl.buf_dir (via host_req_i.addr/amo/debug) -- when ctrl.buf_dir is set (by host_req_i.addr/amo/debug at lines 171-173) the controller takes the direct-forward path and forwards bus responses directly to the host (host_rsp_o <= bus_rsp_i at line 209), which bypasses the normal cache refill/write behavior and thus provides an alternate mode that changes whether cached contents are updated or used.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cache_o.data | neorv32_cache | sets | 4 -> 290 `wdata_i => cache_o.data,` | CONNECTS neorv32_cache_memory_inst.wdata_i | edge, role unfit | CONNECTS does not demonstrate 'sets' (mode None, storage none) | not listed |
| cache_o.we | neorv32_cache | sets | 5 -> 289 `we_i    => cache_o.we,` | CONNECTS neorv32_cache_memory_inst.we_i | edge, role unfit | CONNECTS does not demonstrate 'sets' (mode None, storage none) | not listed |
| cache_o.addr | neorv32_cache | sets | 5 -> 288 `addr_i  => cache_o.addr,` | CONNECTS neorv32_cache_memory_inst.addr_i | edge, role unfit | CONNECTS does not demonstrate 'sets' (mode None, storage none) | not listed |
| cache_i.data | neorv32_cache | computes | 3 -> 291 `rdata_o => cache_i.data` | CONNECTS neorv32_cache_memory_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| host_rsp_o | neorv32_cache | exit port | 4 -> 156 `host_rsp_o.data <= cache_i.data;` | COPIES cache_i.data | occurrence only | no COPIES record to 'cache_i.data' at occurrence 4 | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): cache_o.data <- ctrl.state; cache_o.we <- cache_i.sta_hit, ctrl.buf_dir, ctrl.state, host_req_i.rw; cache_o.addr <- ctrl.state; host_rsp_o <- ctrl.state

## Concept: Cache hit indicator (the hit/miss decision produced by the tag/valid tests)

- confidentiality: yes-assumed, line 191 `host_rsp_o.ack <= '1';` via host_rsp_o.ack -- cache hit is used to drive host_rsp_o.ack on a cache-hit path (line 191), exposing hit/miss information to the host and thus potentially revealing internal cache state.
- integrity: yes-rtl, line 383 `valid_mem(to_integer(unsigned(acc_idx))) <= '0';` via inv_i / cache_o.cmd_inv -- the valid bits and tags that determine the hit are modified by clr/inv/new inputs in status_memory/tag_memory (e.g. invalidate of a single index on inv_i at line 383, tag write at line 398) and those inputs are driven by cache commands generated by the controller (cache_o.cmd_inv/cmd_new), so external events (e.g. bus or host requests that set those commands) can change the hit result while it is used.
- availability: yes-rtl, line 242 `ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err;` via bus_rsp_i.err -- bus_rsp_i.err is captured into ctrl.buf_err (line 242) which can lead the controller to issue a cache-invalidate command (cache_o.cmd_inv at line 255) that drives inv_i and clears valid bits in the memory (line 383), so an external agent can force invalidation and prevent hits.
- undermined behavior: no, line 405 `hit_o <= '1' when (valid_mem_rd = '1') and (tag_mem_rd = acc_tag) else '0';` -- the hit signal is computed only by the tag/valid compare in the memory (single assignment at line 405) and there is no alternate debug/test assignment that replaces this computation in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| cache_i.sta_hit | neorv32_cache | computes | 3 -> 286 `hit_o   => cache_i.sta_hit,` | CONNECTS neorv32_cache_memory_inst.hit_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | hit |

## Concept: Bus-side requests placed by the cache controller (the bus_req_o transaction driven to the external bus: address, rw, stb, lock)

- confidentiality: yes-assumed, line 159 `bus_req_o       <= host_req_i;` via bus_req_o -- the controller forwards or composes bus transactions onto the external bus (bus_req_o <= host_req_i at line 159 and composed addr/rw at lines 227/238), so addresses and control fields are exposed externally and confidentiality depends on integration.
- integrity: yes-assumed, line 159 `bus_req_o       <= host_req_i;` via host_req_i -- bus_req_o is initially a direct copy of host_req_i (line 159) and is also composed from controller state (lines 227/238) which itself is influenced by external inputs, so external parties can influence or change bus_req_o contents and integrity depends on trust in those inputs.
- availability: yes-rtl, line 243 `if (bus_rsp_i.ack = '1') then` via bus_rsp_i.ack -- the download/forward sequence that issues successive bus_req_o transactions advances only when bus_rsp_i.ack is asserted (the ack-controlled state/offset update at line 243-244), so an external bus that withholds ack can block further bus-side requests and stall progress.
- undermined behavior: yes-rtl, line 173 `ctrl_nxt.buf_dir <= '1';` via ctrl.buf_dir (via host_req_i.addr/amo/debug) -- setting ctrl.buf_dir (by host_req_i.addr/amo/debug at lines 171-173) selects a direct-forward path in S_LOOKUP that drives bus_req_o differently (direct passthrough and S_DIRECT_RSP handling), providing an alternate mode that bypasses the normal cached request behavior.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_req_o | neorv32_cache | exit port | 9 -> 227 `bus_req_o.addr  <= ctrl.tag & ctrl.idx & ctrl.ofs & "00";` | SELECTED_BY ctrl.state | occurrence only | no SELECTED_BY record to 'ctrl.state' at occurrence 9 | not listed |
