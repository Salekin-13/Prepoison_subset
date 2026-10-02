# neorv32_cache

**Purpose (model):** neorv32_cache is a cache controller: it accepts host memory requests (host_req_i), decodes address fields into tag/index/offset, checks/controls an internal cache memory instance (neorv32_cache_memory) for hits or misses, issues bus requests for direct responses or for cache-line downloads/fills, and drives host responses (host_rsp_o) and memory control signals (clr/inv/new/addr/we/data).

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | a host memory request (host_req_i) is captured / buffered and begins cache handling (enter S_LOOKUP or S_CLEAR) |  | 11 / 11 |
| operate | lookup: decode request address into tag/index/offset and decide hit vs miss (cache_i.sta_hit) to route the request |  | 12 / 12 |
| operate | direct response / bus forwarding: when bypassed or on write-miss, issue bus_req_o or forward bus_rsp_i to host (S_DIRECT_RSP) |  | 11 / 11 |
| operate | download / fill: request cache line words from bus (bus_req_o with lock), write them into cache memory (cache_o.new/cache_o.we/cache_o.data) and advance offset until done |  | 17 / 17 |
| report | produce host response signals (ack, err, data) from cache state, direct bus responses or downloaded data |  | 6 / 6 |
| reset | controller state and buffers cleared on rstn_i asserted low (ctrl reset to defaults) |  | 13 / 13 |
| lock | bus lock asserted during multi-word cache-line download (bus_req_o.lock) |  | 2 / 2 |

## Concept: Direct-bypass decision (whether a host request bypasses the cache and is served directly)

- confidentiality: yes-assumed, line 187 `bus_req_o.stb  <= '1';` via bus_req_o.stb -- The direct-bypass decision drives bus_req_o.stb (line 187), an external output that reveals the decision to the bus/receiver.
- integrity: yes-assumed, line 173 `ctrl_nxt.buf_dir <= '1';` via host_req_i -- ctrl_nxt.buf_dir is set from host request fields (address nibble, amo, debug) in S_IDLE (line 173), so an external requester can change this decision.
- availability: no, line 126 `ctrl <= ctrl_nxt;` via ctrl -- The stored decision (ctrl.buf_dir) is latched from ctrl_nxt on every rising clock edge (ctrl <= ctrl_nxt at line 126) and there is no external stall gating that latch.
- undermined behavior: no, line 140 `ctrl_nxt.buf_dir  <= '0';` via ctrl_nxt.buf_dir -- The comb process provides the only drivers for the decision (default at line 140 and conditional set at line 173); no debug/test override or alternate driver exists.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| host_req_i.addr | neorv32_cache | sets | 3 -> 171 `if (unsigned(host_req_i.addr(31 downto 28)) >= unsigned(UC_BEGIN)) or` | GATES ctrl_nxt.buf_dir | verified |  | not listed |
| host_req_i.amo | neorv32_cache | sets | 2 -> 172 `(host_req_i.amo = '1') or (host_req_i.debug = '1') then` | GATES ctrl_nxt.buf_dir | verified |  | not listed |
| host_req_i.debug | neorv32_cache | sets | 2 -> 172 `(host_req_i.amo = '1') or (host_req_i.debug = '1') then` | GATES ctrl_nxt.buf_dir | verified |  | not listed |
| ctrl_nxt.buf_dir | neorv32_cache | computes | 3 -> 173 `ctrl_nxt.buf_dir <= '1';` | SELECTED_BY ctrl.state | verified |  | not listed |
| ctrl | neorv32_cache | stores | 10 -> 126 `ctrl <= ctrl_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl_nxt.buf_dir <- ctrl.buf_req, ctrl.buf_sync, ctrl.state, host_req_i.addr, host_req_i.amo, host_req_i.debug, host_req_i.fence, host_req_i.stb

## Concept: Decoded request address (tag, index, offset) used to select cache lines and to form bus request addresses

- confidentiality: yes-assumed, line 227 `bus_req_o.addr  <= ctrl.tag & ctrl.idx & ctrl.ofs & "00";` via bus_req_o.addr -- The decoded fields are assembled into bus_req_o.addr (line 227), an external bus output, so the decoded address is observable outside the module.
- integrity: no, line 126 `ctrl <= ctrl_nxt;` via ctrl -- The decoded tag/index/offset are captured into the ctrl register from ctrl_nxt on the clock (ctrl <= ctrl_nxt at line 126) and ctrl_nxt.tag/idx/ofs are produced in S_LOOKUP (lines 180-182), so updates occur only at the intended times.
- availability: yes-rtl, line 243 `if (bus_rsp_i.ack = '1') then` via bus_rsp_i.ack -- Progress through S_DOWNLOAD_RSP (guarded at line 243) and the ofs increment (line 244) is gated by bus_rsp_i.ack, so a missing or withheld ack from the external bus can block download/address progression.
- undermined behavior: no, line 180 `ctrl_nxt.tag     <= host_req_i.addr(31 downto 32-tag_size_c);` via ctrl_nxt.tag -- The decoded fields are driven only by the state-machine assignments in S_LOOKUP (e.g. tag at line 180) and the download increment (line 244); there is no debug/test override that substitutes a different source.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| host_req_i.addr | neorv32_cache | sets | 4 -> 180 `ctrl_nxt.tag     <= host_req_i.addr(31 downto 32-tag_size_c);` | SOURCES ctrl_nxt.tag | verified |  | not listed |
| ctrl_nxt.tag | neorv32_cache | computes | 3 -> 180 `ctrl_nxt.tag     <= host_req_i.addr(31 downto 32-tag_size_c);` | DERIVES_FROM host_req_i.addr | verified |  | not listed |
| ctrl | neorv32_cache | stores | 10 -> 126 `ctrl <= ctrl_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
| bus_req_o.addr | neorv32_cache | exit port | 2 -> 227 `bus_req_o.addr  <= ctrl.tag & ctrl.idx & ctrl.ofs & "00";` | DERIVES_FROM ctrl.tag | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl_nxt.tag <- ctrl.state; bus_req_o.addr <- ctrl.state

## Concept: Cached contents (valid bits, tag memory, per-byte data banks) that determine hit/miss and the data returned to the host

- confidentiality: yes-assumed, line 156 `host_rsp_o.data <= cache_i.data;` via host_rsp_o.data -- Stored cache data (rdata_o) is forwarded to host_rsp_o.data (line 156), an output port visible outside the module, so cached contents are externally observable.
- integrity: yes-assumed, line 236 `cache_o.data   <= bus_rsp_i.data;` via bus_rsp_i.data -- In S_DOWNLOAD_RSP the controller assigns cache_o.data <= bus_rsp_i.data and asserts cache_o.we (lines 236-237), which is forwarded into the memory (manifested as data_mem_b0..b3 writes at lines 414..423), so external bus responses can change cached contents.
- availability: yes-rtl, line 243 `if (bus_rsp_i.ack = '1') then` via bus_rsp_i.ack -- The download/write sequence advances only when bus_rsp_i.ack is asserted (guard at line 243 leads to ofs increment at 244), so lack of external ack can stall filling cache contents and prevent progress.
- undermined behavior: no, line 414 `data_mem_b0(to_integer(unsigned(acc_adr))) <= wdata_i(7 downto 0);` via data_mem_b0 (and peers) -- Data stores are effected only by the standard we_i/wdata_i writes into the byte banks (lines 414..423); there is no separate debug/test override that replaces or bypasses these writes.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| valid_mem | neorv32_cache_memory | stores | 3 -> 381 `valid_mem <= (others => '0');` | CLOCKED_BY clk_i | verified |  | not listed |
| tag_mem | neorv32_cache_memory | stores | 2 -> 398 `tag_mem(to_integer(unsigned(acc_idx))) <= acc_tag;` | CLOCKED_BY clk_i | verified |  | not listed |
| data_mem_b0 | neorv32_cache_memory | stores | 2 -> 414 `data_mem_b0(to_integer(unsigned(acc_adr))) <= wdata_i(7 downto 0);` | CLOCKED_BY clk_i | verified |  | not listed |
| data_mem_b1 | neorv32_cache_memory | stores | 2 -> 417 `data_mem_b1(to_integer(unsigned(acc_adr))) <= wdata_i(15 downto 8);` | CLOCKED_BY clk_i | verified |  | not listed |
| data_mem_b2 | neorv32_cache_memory | stores | 2 -> 420 `data_mem_b2(to_integer(unsigned(acc_adr))) <= wdata_i(23 downto 16);` | CLOCKED_BY clk_i | verified |  | not listed |
| data_mem_b3 | neorv32_cache_memory | stores | 2 -> 423 `data_mem_b3(to_integer(unsigned(acc_adr))) <= wdata_i(31 downto 24);` | CLOCKED_BY clk_i | verified |  | not listed |
| host_rsp_o.data | neorv32_cache | exit port | 2 -> 156 `host_rsp_o.data <= cache_i.data;` | COPIES cache_i.data | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): valid_mem <- acc_idx, clr_i, inv_i, new_i; tag_mem <- acc_idx, new_i; data_mem_b0 <- acc_adr, we_i; data_mem_b1 <- acc_adr, we_i; data_mem_b2 <- acc_adr, we_i; data_mem_b3 <- acc_adr, we_i

## Concept: Download error indicator and host error/ack reporting (whether a downloaded cache line completed without bus errors)

- confidentiality: yes-assumed, line 257 `host_rsp_o.err  <= '1';` via host_rsp_o.err -- The accumulated download error flag is reported to the host via host_rsp_o.err (line 257), an external output, so the error indicator is observable outside the module.
- integrity: yes-assumed, line 242 `ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err;` via bus_rsp_i.err -- ctrl_nxt.buf_err is explicitly accumulated from bus_rsp_i.err in S_DOWNLOAD_RSP (line 242), allowing an external bus responder to influence the stored download error state.
- availability: yes-rtl, line 243 `if (bus_rsp_i.ack = '1') then` via bus_rsp_i.ack -- Completion of the download (ofs increments and transition to DONE) is gated by bus_rsp_i.ack (line 243), so a missing or withheld ack can prevent completion and subsequent error/ack reporting.
- undermined behavior: no, line 242 `ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err;` via ctrl_nxt.buf_err -- The error indicator is strictly the accumulation of bus_rsp_i.err into ctrl_nxt.buf_err (line 242) and reset; there is no alternate debug/test source that substitutes or bypasses this flag.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| bus_rsp_i.err | neorv32_cache | sets | 2 -> 242 `ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err;` | GATES ctrl_nxt.buf_err | verified |  | not listed |
| ctrl_nxt.buf_err | neorv32_cache | computes | 4 -> 242 `ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err;` | GATED_BY bus_rsp_i.err | verified |  | not listed |
| ctrl | neorv32_cache | stores | 10 -> 126 `ctrl <= ctrl_nxt;` | CLOCKED_BY clk_i | verified |  | not listed |
| host_rsp_o.err | neorv32_cache | exit port | 3 -> 257 `host_rsp_o.err  <= '1';` | SELECTED_BY ctrl.state | verified |  | not listed |
| host_rsp_o.ack | neorv32_cache | exit port | 3 -> 191 `host_rsp_o.ack <= '1';` | SELECTED_BY ctrl.state | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl_nxt.buf_err <- bus_rsp_i.err, ctrl.buf_err, ctrl.state; host_rsp_o.err <- ctrl.buf_err, ctrl.state; host_rsp_o.ack <- cache_i.sta_hit, ctrl.buf_dir, ctrl.buf_err, ctrl.state, host_req_i.rw

## Concept: Cache clear / fence command that invalidates cache state and (optionally) issues a bus fence

- confidentiality: no, line 217 `bus_req_o.fence <= '1';` via bus_req_o.fence -- The fence/clear is generated in response to the host's fence request and forwarded as bus_req_o.fence (line 217); this is a request the writer already initiated and therefore reveals nothing new to that writer.
- integrity: yes-assumed, line 138 `ctrl_nxt.buf_sync <= ctrl.buf_sync or host_req_i.fence;` via host_req_i.fence -- The clear/fence path is driven from the host fence input (ctrl_nxt.buf_sync <= ... host_req_i.fence at line 138), so an external requester can cause the clear and (when configured) the bus fence.
- availability: no, line 219 `cache_o.cmd_clr   <= '1';` via cache_o.cmd_clr -- When the controller enters S_CLEAR it asserts cache_o.cmd_clr (line 219) and then returns to S_IDLE (line 221); there is no external stall/gate that prevents issuance of the clear command apart from global reset/clock.
- undermined behavior: yes-rtl, line 217 `bus_req_o.fence <= '1';` via READ_ONLY generic -- The bus fence assertion is conditional on the static READ_ONLY generic (line 217), so a configuration mode disables the bus fence behavior.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| host_req_i.fence | neorv32_cache | sets | 2 -> 138 `ctrl_nxt.buf_sync <= ctrl.buf_sync or host_req_i.fence;` | GATES ctrl_nxt.buf_sync | verified |  | not listed |
| cache_o.cmd_clr | neorv32_cache | sets | 3 -> 219 `cache_o.cmd_clr   <= '1';` | SELECTED_BY ctrl.state | verified |  | not listed |
| bus_req_o.fence | neorv32_cache | exit port | 3 -> 217 `bus_req_o.fence <= '1';` | SELECTED_BY ctrl.state | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): cache_o.cmd_clr <- ctrl.state; bus_req_o.fence <- ctrl.state
