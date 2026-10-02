# neorv32_fifo

**Purpose (model):** A parameterizable FIFO buffer: it accepts write data and write-enable inputs, stores entries in an internal register or memory depending on FIFO_DEPTH, updates write/read pointers on clk_i, and presents read data and occupancy/status outputs (free_o, avail_o, half_o, level_o). Behavior is configurable by generics FIFO_RSYNC (synchronous read), FIFO_SAFE (gate enables) and FULL_RESET (memory reset).

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | Write: a write request (we_i) causes wdata_i to be written into FIFO storage and advances the write pointer |  | 6 / 6 |
| start | Read: a read request (re_i) causes the read pointer to advance and the selected stored entry to be presented on rdata_o |  | 8 / 8 |
| operate | Pointer and occupancy update: w_pnt/r_pnt are clocked, w_nxt/r_nxt are computed (including clear_i), and level/match/full/empty/half are derived from the pointers |  | 9 / 9 |
| read out | Stored entry returned on rdata_o: read logic selects fifo_mem or fifo_reg at the current read index and drives rdata_o (sync or async depending on FIFO_RSYNC) |  | 4 / 4 |
| report | Status reporting: free/avail/half are produced and copied to free_o/avail_o/half_o, and level is extended to level_o (synchronously or combinationally depending on FIFO_RSYNC) |  | 14 / 14 |
| reset | Reset clears pointer registers (and, when FULL_RESET is true, clears the memory/register contents and resets status outputs) |  | 11 / 11 |

## Concept: FIFO stored entries (the data values held in the FIFO memory or single-entry register that must be delivered unchanged on read)

- confidentiality: yes-assumed, line 213 `rdata_o <= fifo_mem(to_integer(unsigned(r_pnt_ff(r_pnt_ff'left-1 downto 0))));` via rdata_o -- Stored entries written from external wdata_i are later driven to the external rdata_o port (e.g. rdata_o <= fifo_mem at line 213), so an external observer can learn entry contents.
- integrity: yes-assumed, line 184 `fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;` via wdata_i -- Storage is written from the external input wdata_i under the write gate 'we' (e.g. fifo_mem <= wdata_i at line 184), so an external writer can change stored entries and their integrity depends on integration.
- availability: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i forces w_nxt/r_nxt to zeros (line 82/83) which pointer_reg then loads, making previously stored locations inaccessible and allowing an external input to block access to stored entries.
- undermined behavior: no, line 184 `fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;` -- Storage locations are driven only by the gated write processes from wdata_i (e.g. fifo_mem <= wdata_i at line 184) and there is no debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| fifo_mem | neorv32_fifo | stores | 3 -> 150 `fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;` | CLOCKED_BY clk_i | verified |  |
| fifo_reg | neorv32_fifo | stores | 3 -> 135 `fifo_reg <= wdata_i;` | CLOCKED_BY clk_i | verified |  |
| wdata_i | neorv32_fifo | sets | 3 -> 150 `fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;` | CARRIES fifo_mem | verified |  |
| rdata_o | neorv32_fifo | exit port | 3 -> 213 `rdata_o <= fifo_mem(to_integer(unsigned(r_pnt_ff(r_pnt_ff'left-1 downto 0))));` | DERIVES_FROM fifo_mem | verified |  |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fifo_mem <- w_pnt, we; fifo_reg <- we; rdata_o <- r_pnt, r_pnt_ff

## Concept: Effective write-enable decision (the internal write-permit that actually gates storing an entry)

- confidentiality: no, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` -- we is a combinational internal signal derived directly from the external we_i assignment (line 65) and is not exported, so the RTL does not reveal it beyond its writer.
- integrity: yes-rtl, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` via we_i -- we is driven directly from external we_i (and free under FIFO_SAFE) at line 65 and is used without additional protection to gate writes (e.g. 'if (we = ''1'')' in the write processes), so an external input can change the write permit while writes occur.
- availability: no, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` -- we updates combinationally from we_i/free (assignment at line 65) and is not subject to an internal runtime blocker other than the normal clock/reset, so nothing reachable from outside additionally blocks its update.
- undermined behavior: no, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` -- we has a single combinational driver (assignment at line 65) with no debug/test override or alternate runtime assignment in the RTL.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| we | neorv32_fifo | computes | 2 -> 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` | DERIVES_FROM we_i | verified |  |
| we_i | neorv32_fifo | sets | 2 -> 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` | SOURCES we | verified |  |

## Concept: Effective read-enable decision (the internal read-permit that actually advances the read side and enables delivery)

- confidentiality: no, line 64 `re <= re_i when (FIFO_SAFE = false) else (re_i and avail);` -- re is derived directly from external re_i (assignment at line 64) and is not exported by the RTL, so the signal itself is not disclosed.
- integrity: yes-rtl, line 64 `re <= re_i when (FIFO_SAFE = false) else (re_i and avail);` via re_i -- re is assigned from external re_i (and avail when FIFO_SAFE) at line 64 and is used to advance the read pointer (r_nxt update and pointer_reg at lines 83 and 76-77), so external inputs can change the read-permit while reads occur.
- availability: yes-rtl, line 83 `r_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(r_pnt) + 1) when (re = '1') else r_pnt;` via re_i -- r_nxt increments only when re = '1' (r_nxt <= ... when (re = '1') at line 83), so withholding or clearing the external re_i input prevents pointer advancement and blocks read progress.
- undermined behavior: no, line 64 `re <= re_i when (FIFO_SAFE = false) else (re_i and avail);` -- re has a single combinational driver from re_i (assignment at line 64) and there is no separate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| re | neorv32_fifo | computes | 2 -> 64 `re <= re_i when (FIFO_SAFE = false) else (re_i and avail);` | DERIVES_FROM re_i | verified |  |
| re_i | neorv32_fifo | sets | 2 -> 64 `re <= re_i when (FIFO_SAFE = false) else (re_i and avail);` | SOURCES re | verified |  |

## Concept: FIFO pointer state (the write and read pointers that determine which locations are written and read)

- confidentiality: yes-assumed, line 117 `level_o(level'left downto 0) <= level(level'left downto 0);` via level_o -- pointer contents determine the occupancy count (level) which is extended and driven out on level_o by the process at lines 114-117, so external observers can infer pointer state via level_o.
- integrity: yes-rtl, line 76 `w_pnt <= w_nxt;` via w_nxt/r_nxt (driven by we_i,re_i,clear_i) -- w_pnt/r_pnt are clocked from w_nxt/r_nxt on rising_edge(clk_i) (w_pnt <= w_nxt at line 76) and those next-pointer values are computed from external-controlled signals (we/re/clear), so external inputs can change pointer state while it is in use.
- availability: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i forces w_nxt/r_nxt to zeros (line 82/83) and pointer_reg will load them (lines 76-77), so an external clear can empty pointers and prevent progress.
- undermined behavior: no, line 76 `w_pnt <= w_nxt;` -- pointer registers have a single clocked driver assigning w_pnt<=w_nxt and r_pnt<=r_nxt at lines 76-77 and there is no runtime debug/test bypass in the RTL.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| w_pnt | neorv32_fifo | stores | 3 -> 76 `w_pnt <= w_nxt;` | CLOCKED_BY clk_i | verified |  |
| r_pnt | neorv32_fifo | stores | 3 -> 77 `r_pnt <= r_nxt;` | CLOCKED_BY clk_i | verified |  |
| r_pnt_ff | neorv32_fifo | stores | 2 -> 210 `r_pnt_ff <= r_nxt;` | CLOCKED_BY clk_i | verified |  |

## Concept: Occupancy/status indicators (free, avail, half) and their exported ports that gate operations and report FIFO state

- confidentiality: yes-assumed, line 217 `free_o  <= free;` via free_o, avail_o, half_o -- internal occupancy/status signals are copied to external ports (e.g. free_o <= free at line 217), so external observers can read FIFO state.
- integrity: yes-rtl, line 110 `free  <= not full;` via full (and therefore pointers) -- free/avail/half are computed from full/empty/level (free <= not full at line 110), and those upstream signals depend on pointer and write/read activity controlled by external inputs, so external actors can change status signals and thus affect gating decisions.
- availability: yes-rtl, line 249 `if (rstn_i = '0') then` via rstn_i -- the sync_status process forces the outputs to '0' on reset (if rstn_i='0' at lines 249-253), so an external reset can freeze or force status outputs and affect availability.
- undermined behavior: no, line 217 `free_o  <= free;` -- status signals are driven only by copies from internal computations (async case at lines 217-219 or by a single sync process at lines 247-256) and there is no separate debug/test override path.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| free | neorv32_fifo | computes | 3 -> 110 `free  <= not full;` | DERIVES_FROM full | verified |  |
| free_o | neorv32_fifo | exit port | 2 -> 217 `free_o  <= free;` | COPIES free | verified |  |
| avail | neorv32_fifo | computes | 3 -> 111 `avail <= not empty;` | DERIVES_FROM empty | verified |  |
| avail_o | neorv32_fifo | exit port | 2 -> 218 `avail_o <= avail;` | COPIES avail | verified |  |
| half | neorv32_fifo | computes | 2 -> 96 `half  <= level(level'left-1) or full;` | GATED_BY full | verified |  |
| half_o | neorv32_fifo | exit port | 2 -> 219 `half_o  <= half;` | COPIES half | verified |  |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): half <- full, level

## Concept: Level count (number of entries currently stored) and its exported readback

- confidentiality: yes-assumed, line 117 `level_o(level'left downto 0) <= level(level'left downto 0);` via level_o -- level is extended and driven to the external level_o port by the level_extend process (lines 114-117), exposing the occupancy count outside the module.
- integrity: yes-rtl, line 95 `level <= std_ulogic_vector(unsigned(w_pnt) - unsigned(r_pnt));` via w_pnt/r_pnt -- level is computed directly from the internal pointers at line 95 (unsigned(w_pnt)-unsigned(r_pnt)), and those pointers are driven by external-influenced signals (we_i/re_i/clear_i), so external inputs can change the reported level while it is used.
- availability: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i forces the next pointers to zero (line 82-83) which will make level zero on the next pointer update, so an external clear can force or freeze the occupancy count and affect availability.
- undermined behavior: no, line 95 `level <= std_ulogic_vector(unsigned(w_pnt) - unsigned(r_pnt));` -- level has a single combinational driver (assignment at line 95 or 105) producing the occupancy value and there is no alternate runtime bypass assignment exposed by the RTL.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| level | neorv32_fifo | computes | 2 -> 95 `level <= std_ulogic_vector(unsigned(w_pnt) - unsigned(r_pnt));` | DERIVES_FROM w_pnt | verified |  |
| level_o | neorv32_fifo | exit port | 3 -> 117 `level_o(level'left downto 0) <= level(level'left downto 0);` | DERIVES_FROM level | verified |  |

## Concept: Clear request (the external clear_i input that forces pointers to zero and empties the FIFO)

- confidentiality: no, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` -- clear_i is an external control input and there is no RTL readback of the raw input value, so the signal itself is not a secret held by the module.
- integrity: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- asserting clear_i immediately selects zero for w_nxt/r_nxt (line 82/83) so an external actor can change pointer state and thus FIFO contents/behavior at any time.
- availability: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i forces the next pointers to zero (line 82/83) and pointer_reg will load them on the next clock, so an external clear can deliberately empty the FIFO and prevent forward progress.
- undermined behavior: no, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` -- the only mechanism in RTL that forces pointers to zero at runtime is the clear_i-driven assignment (lines 82-83); there is no alternate runtime bypass or debug override implemented.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| clear_i | neorv32_fifo | sets | 2 -> 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) ` | GATES w_nxt | verified |  |
| w_nxt | neorv32_fifo | computes | 2 -> 76 `w_pnt <= w_nxt;` | CARRIES w_pnt | edge, role unfit | CARRIES does not demonstrate 'computes' |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): w_nxt <- clear_i, we
