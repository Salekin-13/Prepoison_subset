# neorv32_cpu_cp_cfu

**Purpose (model):** Implements a small custom-function unit (CFU) that holds a 4-word key in key_mem written via CSRs, latches operands on a start request, runs an XTEA-like core (registers xtea.opa/opb/sum/res/done and combinational tmp_* that index key_mem), and produces a 32-bit result and a valid flag on result_o/valid_o.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | write a 32-bit key word into key_mem via a CSR write |  | 5 / 5 |
| start | start request latches operands into xtea.opa/xtea.opb and sets the core start bit (xtea.done(0)) |  | 5 / 5 |
| operate | core sequencing and arithmetic: update xtea.sum, select key_mem via xtea.sum, compute tmp_r and xtea.res from operands and selected key words |  | 11 / 11 |
| report | export the computed result and a valid indication on result_o and valid_o, under rtype_i/funct3_i selection |  | 9 / 9 |
| read out | read back a key_mem word through the CSR read data port csr_rdata_o (indexed by csr_addr_i) |  | 1 / 1 |
| reset | reset clears key_mem and the xtea registers (done/opa/opb/sum/res) |  | 8 / 8 |

## Concept: Stored CFU key words (the 4×32-bit words held in key_mem)

- confidentiality: yes-assumed, line 185 `csr_rdata_o <= key_mem(to_integer(unsigned(csr_addr_i)));` via csr_rdata_o -- key_mem contents are read back on csr_rdata_o (line 185) and also influence result_o (line 249), so an external observer can learn the stored key words.
- integrity: yes-rtl, line 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` via csr_wdata_i -- csr_wdata_i writes key_mem at line 179 under csr_we_i without any guard preventing writes while the cipher uses key_mem (lines 236-237), so an external CSR write can change keys during operation.
- availability: no, line 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` -- key_mem is read combinationally by the core (lines 236-237) and is only driven by CSR writes at line 179 and reset at 176; there is no external enable/mode that can block core access to key_mem.
- undermined behavior: no, line 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` -- key_mem is driven only by CSR writes (line 179) and reset (line 176); there is no alternate test/debug override or separate driver in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| key_mem | neorv32_cpu_cp_cfu | stores | 3 -> 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` | CLOCKED_BY clk_i | verified |  | hit |
| csr_wdata_i | neorv32_cpu_cp_cfu | sets | 2 -> 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` | CARRIES key_mem | verified |  | hit |
| csr_addr_i | neorv32_cpu_cp_cfu | sets | 2 -> 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` | SELECTS key_mem | verified |  | hit |
| csr_rdata_o | neorv32_cpu_cp_cfu | exit port | 2 -> 185 `csr_rdata_o <= key_mem(to_integer(unsigned(csr_addr_i)));` | DERIVES_FROM key_mem | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): key_mem <- csr_addr_i, csr_we_i; csr_rdata_o <- csr_addr_i

## Concept: Operation operands — the input words latched into xtea.opa and xtea.opb used by the core

- confidentiality: yes-assumed, line 249 `result_o <= xtea.res;` via result_o -- operands latched from rs1_i/rs2_i (lines 205-206) influence the computed result that is exported on result_o (line 249), so their values can be observed outside the module.
- integrity: yes-rtl, line 205 `xtea.opa     <= rs1_i;` via rs1_i, rs2_i -- xtea.opa/opb are clocked from rs1_i/rs2_i at lines 205-206 under the start/rtype gate and there is no RTL guard preventing a new start/write while the algorithm is using the latched operands, so external inputs can change them at times that affect the computation.
- availability: yes-rtl, line 204 `if (start_i = '1') and (rtype_i = r3type_c) then` via start_i -- the capture of rs1_i/rs2_i into xtea.opa/opb is gated by (start_i = '1') and rtype_i = r3type_c (line 204), so external control of start_i/rtype_i can prevent operand capture and block operation.
- undermined behavior: no, line 205 `xtea.opa     <= rs1_i;` -- xtea.opa and xtea.opb are driven only by the start-gated copies from rs1_i/rs2_i (lines 205-206); no alternate debug/test override exists in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xtea.opa | neorv32_cpu_cp_cfu | stores | 3 -> 205 `xtea.opa     <= rs1_i;` | CLOCKED_BY clk_i | verified |  | not listed |
| rs1_i | neorv32_cpu_cp_cfu | sets | 2 -> 205 `xtea.opa     <= rs1_i;` | CARRIES xtea.opa | verified |  | hit |
| xtea.opb | neorv32_cpu_cp_cfu | stores | 3 -> 206 `xtea.opb     <= rs2_i;` | CLOCKED_BY clk_i | verified |  | not listed |
| rs2_i | neorv32_cpu_cp_cfu | sets | 2 -> 206 `xtea.opb     <= rs2_i;` | CARRIES xtea.opb | verified |  | hit |
| start_i | neorv32_cpu_cp_cfu | sets | 2 -> 204 `if (start_i = '1') and (rtype_i = r3type_c) then` | GATES xtea.opa | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.opa <- rtype_i, start_i; xtea.opb <- rtype_i, start_i

## Concept: Round accumulator and key-selector (xtea.sum) that controls which key word is used and round sequencing

- confidentiality: yes-assumed, line 249 `result_o <= xtea.res;` via result_o -- xtea.sum selects key_mem words (lines 236-237) and thereby affects the exported result (result_o at line 249), so an external observer could infer the accumulator state and it should be considered secret depending on use.
- integrity: yes-rtl, line 216 `xtea.sum <= std_ulogic_vector(unsigned(xtea.sum) + unsigned(xtea_delta_c));` via funct3_i -- xtea.sum is updated by internal assignments (e.g. addition at line 216) under control of funct3_i while xtea.done(0) = '1', so external control of funct3_i can alter the accumulator during operation and change which key word is selected.
- availability: yes-rtl, line 213 `if (funct3_i(2) = '1') then` via funct3_i -- funct3_i selects which update path for xtea.sum (starting at line 213) and can choose values that do not perform the expected update, allowing an external input to stall round progression and prevent forward progress.
- undermined behavior: no, line 214 `xtea.sum <= xtea.opa;` -- xtea.sum is driven only by the internal xtea_core assignments (lines 214/216/218) and reset; there is no alternate debug/test path that overrides the accumulator in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xtea.sum | neorv32_cpu_cp_cfu | stores | 3 -> 214 `xtea.sum <= xtea.opa;` | CLOCKED_BY clk_i | verified |  | not listed |
| funct3_i | neorv32_cpu_cp_cfu | sets | 2 -> 213 `if (funct3_i(2) = '1') then` | GATES xtea.sum | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.sum <- funct3_i, xtea.done

## Concept: Computed CFU result (xtea.res) that the block exports on result_o

- confidentiality: yes-assumed, line 249 `result_o <= xtea.res;` via result_o -- xtea.res is driven out on result_o (line 249) when the cipher case is selected, so the computed result is observable outside the module and should be treated as possibly sensitive.
- integrity: yes-rtl, line 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` via csr_wdata_i -- external CSR writes (csr_wdata_i at line 179) can change key_mem that is read combinationally (lines 236-237) and thus modify tmp_z/tmp_r used by the xtea.res assignments (lines 222/224), so an external writer can alter the computed result while the operation runs.
- availability: yes-rtl, line 249 `result_o <= xtea.res;` via rtype_i, funct3_i -- result_o is only assigned xtea.res for rtype_i = r3type_c and when funct3_i matches the cipher cases (result_select around lines 243-249); external control of rtype_i/funct3_i can prevent the computed result from being exported.
- undermined behavior: yes-rtl, line 252 `result_o <= (others => '0');` via funct3_i -- funct3_i = xtea_init_c selects a special case in result_select (line 252-253) that returns zeros (and valid='1'), thereby bypassing or replacing the actual computed xtea.res output.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xtea.res | neorv32_cpu_cp_cfu | stores | 3 -> 222 `xtea.res <= std_ulogic_vector(unsigned(tmp_b) + unsigned(tmp_r));` | CLOCKED_BY clk_i | verified |  | not listed |
| result_o | neorv32_cpu_cp_cfu | exit port | 2 -> 249 `result_o <= xtea.res;` | COPIES xtea.res | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.res <- funct3_i, xtea.done; result_o <- funct3_i, rtype_i

## Concept: Operation completion state (xtea.done) that gates when a result is valid and exported

- confidentiality: yes-assumed, line 250 `valid_o  <= xtea.done(1);` via valid_o -- xtea.done(1) is driven onto valid_o (line 250) and therefore the block's completion status is visible outside and can reveal what the module is doing.
- integrity: yes-rtl, line 207 `xtea.done(0) <= '1';` via start_i -- xtea.done(0) is set directly by start_i and rtype_i at line 207 without additional protection, so external control can set or replay completion state while operations are in progress.
- availability: yes-rtl, line 207 `xtea.done(0) <= '1';` via start_i -- the completion bit is only seeded by asserting start_i with the correct rtype (line 207), so if start_i/rtype_i are not asserted the block cannot progress to a completion state and cannot present valid results.
- undermined behavior: no, line 201 `xtea.done(1) <= xtea.done(0);` -- xtea.done is produced by the internal sequencing logic (lines 200-207) and reset (line 193); the RTL contains no alternate debug/test override that directly forces or bypasses the done register.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xtea.done | neorv32_cpu_cp_cfu | stores | 4 -> 201 `xtea.done(1) <= xtea.done(0);` | CLOCKED_BY clk_i | verified |  | not listed |
| start_i | neorv32_cpu_cp_cfu | sets | 2 -> 204 `if (start_i = '1') and (rtype_i = r3type_c) then` | GATES xtea.done | verified |  | hit |
| valid_o | neorv32_cpu_cp_cfu | exit port | 2 -> 250 `valid_o  <= xtea.done(1);` | DERIVES_FROM xtea.done | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.done <- rtype_i, start_i; valid_o <- funct3_i, rtype_i
