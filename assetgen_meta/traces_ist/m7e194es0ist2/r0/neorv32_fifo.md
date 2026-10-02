# neorv32_fifo

**Purpose (model):** Parameterized FIFO buffer: accepts write requests and data (we_i, wdata_i), stores data into an internal memory/register indexed by write pointer, advances read pointer on read requests, presents stored words on rdata_o, and reports occupancy/status via level_o, free_o, avail_o and half_o; behavior is configurable for depth, synchronous vs asynchronous read, safe gating, and reset semantics.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | write request (we/we_i) that begins a write sequence and advances the write pointer on the next clock |  | 7 / 7 |
| start | read request (re/re_i) that begins a read sequence and advances the read pointer on the next clock (async path captures r_nxt into r_pnt_ff) |  | 6 / 6 |
| operate | store write-data (wdata_i) into the FIFO memory or single-word register at the write-pointer index when write enable is asserted |  | 6 / 6 |
| read out | deliver the stored word on rdata_o selected from fifo_mem or fifo_reg at the read-pointer index (r_pnt or r_pnt_ff depending on configuration) |  | 4 / 4 |
| report | compute occupancy (level) and status flags (full, empty, half) and present them on level_o, free_o, avail_o and half_o (combinationally or registered depending on FIFO_RSYNC) |  | 15 / 15 |
| reset | synchronous pointer reset on rstn_i = '0' (w_pnt and r_pnt cleared), and optional memory/register clear when FULL_RESET is set; outputs cleared in sync_status reset arm |  | 7 / 7 |
| reset | synchronous clear request (clear_i) that forces w_nxt and r_nxt to zero so pointers are cleared on the next clock |  | 4 / 4 |

## Concept: Stored FIFO payload (the data words held in the FIFO memory or single-word register and delivered on read)

- confidentiality: yes-assumed, line 213 `rdata_o <= fifo_mem(to_integer(unsigned(r_pnt_ff(r_pnt_ff'left-1 downto 0))));` via rdata_o -- Words written from wdata_i into fifo_reg/fifo_mem (writes at lines 135/150/171/184) are later driven out on rdata_o (reads at lines 201/213/232/241), so an external observer can read the stored payload.
- integrity: no, line 184 `fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;` via fifo_mem/fifo_reg -- Stored payload is updated only by the FIFO's intended clocked write processes (writes guarded by we = '1' at lines 135/150/171/184), i.e. normal operation replaces stored words as designed.
- availability: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i forces w_nxt and r_nxt to zeros (line 82/83) so on the next clock the pointer registers are reset and previously stored words become inaccessible or will be overwritten, allowing an external input to prevent progress or access to stored payload.
- undermined behavior: no, line 184 `fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;` via fifo_mem -- There is a single class of drivers for stored payload (clocked write processes at lines 135/150/171/184); no runtime debug/test override or alternate driver is present in the RTL.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| fifo_mem | neorv32_fifo | stores | 3 -> 150 `fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;` | CLOCKED_BY clk_i | verified |  |
| fifo_reg | neorv32_fifo | stores | 3 -> 135 `fifo_reg <= wdata_i;` | CLOCKED_BY clk_i | verified |  |
| rdata_o | neorv32_fifo | exit port | 3 -> 213 `rdata_o <= fifo_mem(to_integer(unsigned(r_pnt_ff(r_pnt_ff'left-1 downto 0))));` | SELECTED_BY r_pnt_ff | verified |  |
| wdata_i | neorv32_fifo | sets | 3 -> 150 `fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;` | CARRIES fifo_mem | verified |  |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fifo_mem <- w_pnt, we; fifo_reg <- we; rdata_o <- r_pnt, r_pnt_ff

## Concept: Pointer state (write and read pointers w_pnt, r_pnt, and the captured read-pointer r_pnt_ff) that index the storage and determine full/empty conditions

- confidentiality: yes-assumed, line 117 `level_o(level'left downto 0) <= level(level'left downto 0);` via level_o -- The difference of pointers is presented externally (level computed at line 95 and assigned to level_o at line 117) and full/empty/half are copied to output ports (lines 217-219/254-256), so external observers can infer pointer-derived state.
- integrity: yes-rtl, line 76 `w_pnt <= w_nxt;` via clear_i -- Pointer registers are updated from w_nxt/r_nxt at line 76/77 and w_nxt/r_nxt can be forced to zeros or advanced by external-controllable inputs (clear_i at line 82 and we_i/re_i via we/re at lines 65/64), so external inputs can change pointer state while it is in use.
- availability: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i drives w_nxt/r_nxt to zeros (line 82/83) so an external clear_i asserted continuously will reset pointers at each clock (pointer_reg lines 76/77) and can halt or prevent forward progress that depends on pointer movement.
- undermined behavior: yes-rtl, line 213 `rdata_o <= fifo_mem(to_integer(unsigned(r_pnt_ff(r_pnt_ff'left-1 downto 0))));` via FIFO_RSYNC -- The read-address source is selected by mode: in async mode rdata_o uses r_pnt_ff (line 213) while in sync mode it uses r_pnt (line 241); the FIFO_RSYNC configuration therefore changes which captured pointer is used for reads.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| w_pnt | neorv32_fifo | stores | 3 -> 76 `w_pnt <= w_nxt;` | CLOCKED_BY clk_i | verified |  |
| r_pnt | neorv32_fifo | stores | 3 -> 77 `r_pnt <= r_nxt;` | CLOCKED_BY clk_i | verified |  |
| r_pnt_ff | neorv32_fifo | stores | 2 -> 210 `r_pnt_ff <= r_nxt;` | CLOCKED_BY clk_i | verified |  |

## Concept: Write and read enable decisions (we and re) that gate whether writes and reads occur

- confidentiality: no, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` via we_i / re_i -- we and re are derived directly from the external strobes we_i and re_i (lines 65/64) and do not hide information beyond what the writer already knows.
- integrity: yes-rtl, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` via we_i -- we is assigned from we_i (line 65) and, when FIFO_SAFE = false, is unguarded, and this we signal directly gates writes (lines 135/150/171/184), so an external writer can change the write-enable while operations run.
- availability: yes-rtl, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` via we_i/re_i -- Progress (writes/reads and pointer advancement) depends on we/re being asserted (we/re drive writes at lines 135/150/171/184 and pointer increments at lines 82/83), so external control of we_i/re_i can stall or force progress.
- undermined behavior: no, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` via we_i -- There is a single assignment form for the enables in the RTL (we/re assigned at lines 65/64, with the only variant being the compile-time FIFO_SAFE gating); no runtime debug/test override is present.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| we | neorv32_fifo | computes | 2 -> 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` | DERIVES_FROM we_i | verified |  |
| re | neorv32_fifo | computes | 2 -> 64 `re <= re_i when (FIFO_SAFE = false) else (re_i and avail);` | DERIVES_FROM re_i | verified |  |

## Concept: Occupancy and status (level, full/empty/half and the exported status ports free_o, avail_o, half_o, level_o) that report FIFO fullness and availability

- confidentiality: yes-assumed, line 217 `free_o  <= free;` via free_o -- Occupancy/status signals (level, full/empty/half) are driven to external ports (level_o at lines 116-117 and free_o/avail_o/half_o at lines 217-219 or 254-256), so an external observer can learn FIFO occupancy and activity.
- integrity: yes-rtl, line 95 `level <= std_ulogic_vector(unsigned(w_pnt) - unsigned(r_pnt));` via clear_i -- Status (level at line 95 and full/empty at lines 92-94) is computed from pointer registers which can be forced or altered by external-controllable inputs (e.g. clear_i at lines 82/83 and we_i/re_i via we/re at lines 65/64), so external inputs can change status while it is in use.
- availability: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- An external clear_i asserted to force w_nxt/r_nxt to zeros (line 82/83) will reset pointers and thus status outputs at the next clock, enabling an external input to freeze or force status and block progress.
- undermined behavior: no, line 217 `free_o  <= free;` via free_o -- Status outputs have a single RTL-driven source (combinational copies at lines 217-219 or the sync update at 254-256 depending on FIFO_RSYNC), and there is no runtime debug/test bypass present.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| level | neorv32_fifo | computes | 2 -> 95 `level <= std_ulogic_vector(unsigned(w_pnt) - unsigned(r_pnt));` | DERIVES_FROM w_pnt | verified |  |
| full | neorv32_fifo | computes | 2 -> 93 `full  <= '1' when (r_pnt(r_pnt'left) /= w_pnt(w_pnt'left)) and (match = '1') else '0';` | GATED_BY match | verified |  |
| free_o | neorv32_fifo | exit port | 2 -> 217 `free_o  <= free;` | COPIES free | verified |  |
| avail_o | neorv32_fifo | exit port | 2 -> 218 `avail_o <= avail;` | COPIES avail | verified |  |
| half_o | neorv32_fifo | exit port | 2 -> 219 `half_o  <= half;` | COPIES half | verified |  |
| level_o | neorv32_fifo | exit port | 3 -> 117 `level_o(level'left downto 0) <= level(level'left downto 0);` | DERIVES_FROM level | verified |  |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): full <- match, r_pnt, w_pnt

## Concept: Synchronous clear request (clear_i) that forces pointer next-values to zero and thus clears FIFO pointers at the next clock


| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| clear_i | neorv32_fifo | sets | 2 -> 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) ` | GATES w_nxt | verified |  |
