# neorv32_fifo

**Purpose (model):** Parameterized FIFO: accepts write data wdata_i under write enable we_i, stores entries in an internal single-word register or an array (fifo_reg / fifo_mem) addressed by write pointer w_pnt, provides read data on rdata_o selected by read pointer r_pnt (or r_pnt_ff for async read), and reports occupancy/status via level_o, free_o, avail_o and half_o. Supports optional synchronous read path, optional full-memory reset, and a clear input that zeros the pointers.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| operate | enqueue: accept wdata_i and store it into the FIFO memory/register and advance the write pointer |  | 9 / 9 |
| operate | dequeue: select an entry from storage into rdata_o and advance the read pointer |  | 9 / 9 |
| report | report FIFO occupancy and status: compute level, half, full/empty-derived free/avail, and present them on level_o, half_o, free_o, avail_o (either directly or synchronized) |  | 14 / 14 |
| read out | deliver stored entry value to an external consumer via rdata_o (async or sync path depending on FIFO_RSYNC and FIFO_DEPTH) |  | 4 / 4 |
| reset | clear pointers and (when FULL_RESET) clear memory contents while rstn_i = '0' |  | 12 / 12 |

## Concept: Stored FIFO payloads (the data words placed into FIFO entries and later returned on read)

- confidentiality: yes-assumed, line 213 `rdata_o <= fifo_mem(to_integer(unsigned(r_pnt_ff(r_pnt_ff'left-1 downto 0))));` via rdata_o -- wdata_i is stored into fifo_reg/fifo_mem (lines 135,150,171,184) and later selected onto rdata_o (lines 201,213,232,241), so an external consumer can read the stored payload.
- integrity: yes-rtl, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` via we_i / wdata_i -- internal write enable we can be assigned directly from we_i when FIFO_SAFE = false (line 65), allowing an external writer (we_i with wdata_i) to overwrite stored entries while they may still be in use (writes at lines 135,150,171,184).
- availability: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i = '1' forces w_nxt/r_nxt to zero (lines 82-83) which pointer_reg captures on the next clock (lines 76-77), clearing/forcing pointer state and preventing or forcing payload progress.
- undermined behavior: no, line 150 `fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;` via wdata_i -- payload storage assignments are driven only from wdata_i into fifo_mem/fifo_reg (lines 150/184 and 135/171) with no runtime debug/test override path that substitutes a different driver.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| fifo_mem | neorv32_fifo | stores | 3 -> 150 `fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;` | CLOCKED_BY clk_i | verified |  |
| fifo_reg | neorv32_fifo | stores | 3 -> 135 `fifo_reg <= wdata_i;` | CLOCKED_BY clk_i | verified |  |
| wdata_i | neorv32_fifo | sets | 3 -> 150 `fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;` | CARRIES fifo_mem | verified |  |
| wdata_i | neorv32_fifo | sets | 2 -> 135 `fifo_reg <= wdata_i;` | CARRIES fifo_reg | verified |  |
| rdata_o | neorv32_fifo | exit port | 3 -> 213 `rdata_o <= fifo_mem(to_integer(unsigned(r_pnt_ff(r_pnt_ff'left-1 downto 0))));` | DERIVES_FROM fifo_mem | verified |  |
| we | neorv32_fifo | computes | 2 -> 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` | DERIVES_FROM we_i | verified |  |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fifo_mem <- w_pnt, we; fifo_reg <- we; rdata_o <- r_pnt, r_pnt_ff

## Concept: Pointer state (write pointer w_pnt, read pointer r_pnt and the async-read shadow r_pnt_ff) that determine which storage location is written or read

- confidentiality: yes-assumed, line 117 `level_o(level'left downto 0) <= level(level'left downto 0);` via level_o -- the pointer difference is computed into level (line 95) which is driven to level_o (lines 116-117), and read selection (lines 213/241) also reveals which index is used, so external observers can infer pointer state.
- integrity: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i / we_i / re_i -- clear_i forces w_nxt/r_nxt to zero (lines 82-83) and we/re (driven from we_i/re_i) control pointer increments, while pointers are clock-updated at lines 76-77 and r_pnt_ff at 210, allowing external inputs to alter pointer state during operation.
- availability: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i can repeatedly force next-pointer values to zero (lines 82-83) which pointer_reg captures (lines 76-77), freezing pointer progression and preventing FIFO progress.
- undermined behavior: no, line 76 `w_pnt <= w_nxt;` via pointer_reg -- pointers have a single clocked driver (w_pnt <= w_nxt, r_pnt <= r_nxt at lines 76-77) and there is no runtime override or debug path to replace that driver.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| w_pnt | neorv32_fifo | stores | 3 -> 76 `w_pnt <= w_nxt;` | CLOCKED_BY clk_i | verified |  |
| r_pnt | neorv32_fifo | stores | 3 -> 77 `r_pnt <= r_nxt;` | CLOCKED_BY clk_i | verified |  |
| r_pnt_ff | neorv32_fifo | stores | 2 -> 210 `r_pnt_ff <= r_nxt;` | CLOCKED_BY clk_i | verified |  |

## Concept: Read / write commit decisions (the internal we and re signals computed from the external we_i / re_i and availability flags) that gate whether a write or read actually occurs

- confidentiality: yes-assumed, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` via we_i / re_i -- the internal commit signals derive from external inputs we_i/re_i (lines 64-65) and their effects (reads/writes and status changes) are observable on rdata_o and status outputs, so external parties can infer commit decisions.
- integrity: yes-rtl, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` via we_i / re_i -- when FIFO_SAFE = false the internal enables follow we_i/re_i directly (lines 64-65) without masking, allowing external inputs to change commit decisions while operations are in progress.
- availability: yes-rtl, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` via we_i / re_i -- external inputs we_i/re_i directly control internal enables (line 65), so an external actor can stall or force reads/writes and thus block FIFO progress.
- undermined behavior: no, line 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` via we_i / re_i -- there is a single runtime assignment for we/re from we_i/re_i (lines 64-65) with no debug or alternate runtime override path present.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| we_i | neorv32_fifo | sets | 2 -> 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` | SOURCES we | verified |  |
| we | neorv32_fifo | computes | 2 -> 65 `we <= we_i when (FIFO_SAFE = false) else (we_i and free);` | DERIVES_FROM we_i | verified |  |
| re_i | neorv32_fifo | sets | 2 -> 64 `re <= re_i when (FIFO_SAFE = false) else (re_i and avail);` | SOURCES re | verified |  |
| re | neorv32_fifo | computes | 2 -> 64 `re <= re_i when (FIFO_SAFE = false) else (re_i and avail);` | DERIVES_FROM re_i | verified |  |

## Concept: Occupancy count (level) — the computed fill level exposed to consumers via level_o


| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| level | neorv32_fifo | computes | 2 -> 95 `level <= std_ulogic_vector(unsigned(w_pnt) - unsigned(r_pnt));` | DERIVES_FROM w_pnt | verified |  |
| level_o | neorv32_fifo | exit port | 3 -> 117 `level_o(level'left downto 0) <= level(level'left downto 0);` | DERIVES_FROM level | verified |  |

## Concept: Availability / fullness flags (free, avail, half) and their exported ports (free_o, avail_o, half_o)

- confidentiality: yes-assumed, line 217 `free_o  <= free;` via free_o / avail_o / half_o -- the fullness/availability signals are copied to output ports (lines 217-219 and 254-256), so external entities can read these status flags.
- integrity: yes-rtl, line 110 `free  <= not full;` via w_pnt / r_pnt / clear_i / we_i / re_i -- free/avail/half derive from full/empty/level (lines 93-96,110-111) which in turn depend on pointer state and external inputs (clear_i, we_i, re_i), allowing outside-controlled changes to these flags.
- availability: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i can force pointer/level/full-empty conditions (lines 82-83 and 93-96) that in turn fix or toggle free/avail/half and thereby stall or force status signals and block progress.
- undermined behavior: no, line 217 `free_o  <= free;` via free_o -- the flags are driven by the computed signals and routed to outputs (lines 217-219 and 254-256) with no runtime debug/test override path that replaces their assignments.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| free | neorv32_fifo | computes | 3 -> 110 `free  <= not full;` | DERIVES_FROM full | verified |  |
| free_o | neorv32_fifo | exit port | 2 -> 217 `free_o  <= free;` | COPIES free | verified |  |
| avail | neorv32_fifo | computes | 3 -> 111 `avail <= not empty;` | DERIVES_FROM empty | verified |  |
| avail_o | neorv32_fifo | exit port | 2 -> 218 `avail_o <= avail;` | COPIES avail | verified |  |
| half | neorv32_fifo | computes | 2 -> 96 `half  <= level(level'left-1) or full;` | GATED_BY level | verified |  |
| half_o | neorv32_fifo | exit port | 2 -> 219 `half_o  <= half;` | COPIES half | verified |  |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): half <- full, level

## Concept: Clear command (clear_i) that forces next-pointer values to zero and thereby clears FIFO pointer state

- confidentiality: yes-assumed, line 117 `level_o(level'left downto 0) <= level(level'left downto 0);` via level_o -- asserting clear_i forces w_nxt/r_nxt = 0 (lines 82-83) which changes pointers and thus level, and level is exported on level_o (lines 116-117), revealing the clear event externally.
- integrity: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i directly selects zero for w_nxt and r_nxt (lines 82-83) and pointer_reg captures those next-pointer values (lines 76-77) without additional guarding, so an external actor can assert clear_i and change pointer state at any time.
- availability: yes-rtl, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i = '1' forces next-pointer values to zero (lines 82-83) and pointer_reg captures them (lines 76-77), allowing an external input to clear or freeze FIFO progress and block users.
- undermined behavior: no, line 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) when (we = '1') else w_pnt;` via clear_i -- clear_i is a single input used in the w_nxt/r_nxt conditional assignments (lines 82-83) with no runtime alternate override or debug path present.

| element | entity | role | occurrence -> line | edge | status | why |
|---|---|---|---|---|---|---|
| clear_i | neorv32_fifo | sets | 2 -> 82 `w_nxt <= (others => '0') when (clear_i = '1') else std_ulogic_vector(unsigned(w_pnt) + 1) ` | GATES w_nxt | verified |  |
