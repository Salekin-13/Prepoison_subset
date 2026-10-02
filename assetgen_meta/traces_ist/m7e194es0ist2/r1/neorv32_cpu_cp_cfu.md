# neorv32_cpu_cp_cfu

**Purpose (model):** Implements an XTEA co-processor: a 4-word key is written via CSR, the block accepts start/type/function selectors and operands (rs1_i, rs2_i), performs XTEA round computations updating internal registers (xtea.sum, xtea.res, xtea.done) and exports the computed result and validity (result_o, valid_o); CSR readback of key_mem is provided.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | write a 32-bit word into the key memory (key_mem) via CSR write |  | 4 / 4 |
| start | start request that captures operands and arms the XTEA core when rtype indicates the co-processor operation |  | 4 / 4 |
| operate | XTEA internal step: update sum and compute res from operands, tmp values and key_mem |  | 11 / 11 |
| report | select and drive result_o and valid_o from internal XTEA state (res / done) or produce init/zero responses |  | 9 / 9 |
| read out | read back a key_mem word onto csr_rdata_o |  | 1 / 1 |
| reset | reset clears key_mem and the XTEA registers (done, opa, opb, sum, res) |  | 8 / 8 |

## Concept: Key material stored in key_mem (4-word key)

- confidentiality: yes-assumed, line 185 `csr_rdata_o <= key_mem(to_integer(unsigned(csr_addr_i)));` via csr_rdata_o -- key_mem is read back to csr_rdata_o at line 185, so an external observer can read configured key material and the integrator must treat it as potentially secret.
- integrity: yes-rtl, line 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` via csr_wdata_i -- key_mem is written from csr_wdata_i at line 179 (guarded only by csr_we_i at line 178) and those writes can occur while XTEA reads key_mem (tmp_z at lines 236-237 used in result at line 249), so the RTL does not prevent modification during use.
- availability: no, line 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` -- key_mem only changes via CSR writes (line 179) and global reset (line 176) and there is no input-controlled stall/enable that freezes key_mem and blocks module progress.
- undermined behavior: no, line 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` -- key_mem has a single driver path (CSR writes at line 179 and reset at line 176) and there is no alternate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| key_mem | neorv32_cpu_cp_cfu | stores | 3 -> 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` | CLOCKED_BY clk_i | verified |  | hit |
| csr_wdata_i | neorv32_cpu_cp_cfu | sets | 2 -> 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` | CARRIES key_mem | verified |  | hit |
| csr_we_i | neorv32_cpu_cp_cfu | sets | 2 -> 178 `if (csr_we_i = '1') then` | GATES key_mem | verified |  | hit |
| csr_addr_i | neorv32_cpu_cp_cfu | sets | 2 -> 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` | SELECTS key_mem | verified |  | hit |
| csr_rdata_o | neorv32_cpu_cp_cfu | exit port | 2 -> 185 `csr_rdata_o <= key_mem(to_integer(unsigned(csr_addr_i)));` | DERIVES_FROM key_mem | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): key_mem <- csr_addr_i, csr_we_i; csr_rdata_o <- csr_addr_i

## Concept: XTEA operands (operand A and operand B) captured for a started operation

- confidentiality: no, line 205 `xtea.opa     <= rs1_i;` via rs1_i -- operands are provided as external inputs (rs1_i/rs2_i) and are captured into internal registers at lines 205/206, so the module does not hide their contents.
- integrity: yes-assumed, line 205 `xtea.opa     <= rs1_i;` via rs1_i -- operands are written into xtea.opa/opb from external inputs rs1_i/rs2_i at lines 205/206 gated by start/rtype, so whether those writers are trusted depends on the integration.
- availability: yes-rtl, line 204 `if (start_i = '1') and (rtype_i = r3type_c) then` via start_i -- operand capture only occurs when start_i='1' and rtype_i=r3type_c (line 204), so external control of start/rtype can prevent capture and stall operations.
- undermined behavior: no, line 205 `xtea.opa     <= rs1_i;` -- xtea.opa and xtea.opb have only the capture assignments from rs1_i/rs2_i (lines 205/206) and no alternate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rs1_i | neorv32_cpu_cp_cfu | sets | 2 -> 205 `xtea.opa     <= rs1_i;` | CARRIES xtea.opa | verified |  | hit |
| rs2_i | neorv32_cpu_cp_cfu | sets | 2 -> 206 `xtea.opb     <= rs2_i;` | CARRIES xtea.opb | verified |  | hit |
| xtea.opa | neorv32_cpu_cp_cfu | stores | 3 -> 205 `xtea.opa     <= rs1_i;` | CLOCKED_BY clk_i | verified |  | not listed |
| xtea.opb | neorv32_cpu_cp_cfu | stores | 3 -> 206 `xtea.opb     <= rs2_i;` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.opa <- rtype_i, start_i; xtea.opb <- rtype_i, start_i

## Concept: XTEA internal round state (sum) used to index key_mem and steer the algorithm

- confidentiality: yes-assumed, line 249 `result_o <= xtea.res;` via result_o -- xtea.sum indexes key_mem (lines 236-237) and thereby affects xtea.res that is output at result_o (line 249), so external observers can infer internal sum and it should be treated as potentially confidential.
- integrity: yes-rtl, line 214 `xtea.sum <= xtea.opa;` via funct3_i -- xtea.sum is updated under input-controlled conditions (e.g. xtea.sum <= xtea.opa at line 214 selected by funct3_i at line 213) and the RTL provides no protection against changes to those inputs while sum is used, so external inputs can alter sum.
- availability: yes-rtl, line 207 `xtea.done(0) <= '1';` via start_i -- xtea.sum only advances when xtea.done(0)='1', and xtea.done(0) is asserted by start_i (line 207), so external control of start can prevent sum progression and block the algorithm.
- undermined behavior: no, line 214 `xtea.sum <= xtea.opa;` -- xtea.sum has a single set of update assignments in the xtea_core process (lines 214/216/218) and there is no separate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xtea.sum | neorv32_cpu_cp_cfu | stores | 3 -> 214 `xtea.sum <= xtea.opa;` | CLOCKED_BY clk_i | verified |  | not listed |
| funct3_i | neorv32_cpu_cp_cfu | sets | 2 -> 213 `if (funct3_i(2) = '1') then` | GATES xtea.sum | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.sum <- funct3_i, xtea.done

## Concept: XTEA computed result (res) that the module exports as the operation result

- confidentiality: yes-assumed, line 249 `result_o <= xtea.res;` via result_o -- xtea.res is driven to the external result_o at line 249, so the computed result is externally observable and may be considered confidential depending on use.
- integrity: yes-rtl, line 222 `xtea.res <= std_ulogic_vector(unsigned(tmp_b) + unsigned(tmp_r));` via funct3_i, csr_wdata_i -- xtea.res is computed at lines 222/224 from operands and tmp_r that depends on key_mem (read at lines 236-237) and on inputs (funct3_i, rs1_i/rs2_i), so CSR writes (line 179) or changes to inputs can alter the computed result while an operation runs.
- availability: yes-rtl, line 245 `if (rtype_i = r3type_c) then` via rtype_i -- result_o is only driven with xtea.res in the rtype_i = r3type_c branch (result_select gating lines 243-249 and the else branches), so external control of rtype/funct3 can prevent the result from being presented.
- undermined behavior: yes-rtl, line 252 `result_o <= (others => '0');` via funct3_i -- result_select forces result_o to all zeros and valid_o='1' for the xtea_init function at lines 251-253, thereby replacing the exported computed result in that mode.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xtea.res | neorv32_cpu_cp_cfu | stores | 3 -> 222 `xtea.res <= std_ulogic_vector(unsigned(tmp_b) + unsigned(tmp_r));` | CLOCKED_BY clk_i | verified |  | not listed |
| result_o | neorv32_cpu_cp_cfu | exit port | 2 -> 249 `result_o <= xtea.res;` | COPIES xtea.res | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.res <- funct3_i, xtea.done; result_o <- funct3_i, rtype_i

## Concept: XTEA completion event (done) that produces valid_o

- confidentiality: yes-assumed, line 250 `valid_o  <= xtea.done(1);` via valid_o -- xtea.done(1) is copied to valid_o at line 250, making completion status externally observable and potentially revealing internal state timing.
- integrity: yes-rtl, line 207 `xtea.done(0) <= '1';` via start_i -- xtea.done(0) is asserted by start_i at line 207 and shifted/cleared by internal logic (lines 200-201) with no RTL protection against external toggling while operations run, so its integrity can be affected by inputs.
- availability: yes-rtl, line 207 `xtea.done(0) <= '1';` via start_i -- the module relies on xtea.done to indicate completion and start_i controls setting of xtea.done(0) (line 207), therefore an external actor can prevent completion by withholding start.
- undermined behavior: yes-rtl, line 253 `valid_o  <= '1';` via funct3_i -- result_select forces valid_o='1' for the xtea_init function at line 253 regardless of the xtea.done register, bypassing the done signal as the sole completion indicator.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xtea.done | neorv32_cpu_cp_cfu | stores | 4 -> 201 `xtea.done(1) <= xtea.done(0);` | CLOCKED_BY clk_i | verified |  | not listed |
| valid_o | neorv32_cpu_cp_cfu | exit port | 2 -> 250 `valid_o  <= xtea.done(1);` | DERIVES_FROM xtea.done | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.done <- rtype_i, start_i; valid_o <- funct3_i, rtype_i

## Concept: Start request that arms operand capture and begins an XTEA operation

- confidentiality: no, line 204 `if (start_i = '1') and (rtype_i = r3type_c) then` via start_i -- start_i is an external input used directly in the if condition at line 204 to trigger operand capture and is not masked or hidden by the RTL.
- integrity: yes-assumed, line 204 `if (start_i = '1') and (rtype_i = r3type_c) then` via start_i -- start_i is an unprotected external input that directly controls capture and operation start (lines 204-207), so whether unauthorized assertions are possible depends on integration.
- availability: yes-rtl, line 204 `if (start_i = '1') and (rtype_i = r3type_c) then` via start_i -- the co-processor only captures operands and begins the operation when start_i='1' and rtype_i=r3type_c (line 204), therefore external control of start_i can block operation progress.
- undermined behavior: no, line 204 `if (start_i = '1') and (rtype_i = r3type_c) then` -- start_i is the single input-driven mechanism to arm capture in the RTL (lines 204-207) and there is no alternate debug/test override present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| start_i | neorv32_cpu_cp_cfu | sets | 2 -> 204 `if (start_i = '1') and (rtype_i = r3type_c) then` | GATES xtea.done | verified |  | hit |

## Concept: Operation-type selector (rtype_i) that chooses whether the co-processor path is taken and which outputs are driven

- confidentiality: no, line 243 `result_select: process(rtype_i, funct3_i, xtea)` via rtype_i -- rtype_i is an external input selecting the co-processor path in the result_select process at line 243 and is not treated as secret by the RTL.
- integrity: yes-rtl, line 204 `if (start_i = '1') and (rtype_i = r3type_c) then` via rtype_i -- rtype_i gates operand capture (line 204) and result selection (lines 243-245) and can be changed by external inputs while operations are in flight, so the RTL does not protect its integrity.
- availability: yes-rtl, line 261 `result_o <= (others => '0');` via rtype_i -- when rtype_i is not equal to r3type_c the result_select else branch drives result_o and valid_o to zeros at lines 261-262, so external control of rtype_i can prevent co-processor outputs and stall expected behavior.
- undermined behavior: no, line 245 `if (rtype_i = r3type_c) then` -- rtype_i has a single selection role (gating at lines 204 and 243-245) and there is no separate override or debug bypass in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rtype_i | neorv32_cpu_cp_cfu | sets | 4 -> 245 `if (rtype_i = r3type_c) then` | GATES result_o | verified |  | not listed |

## Concept: Function selector (funct3_i) that selects XTEA enc/dec variants and local arithmetic behaviors

- confidentiality: no, line 247 `case funct3_i is` via funct3_i -- funct3_i is an external selector used directly in the result_select case at line 247 and the RTL does not mask it, so it is not treated as secret.
- integrity: yes-rtl, line 213 `if (funct3_i(2) = '1') then` via funct3_i -- funct3_i gates updates to xtea.sum and arithmetic direction (e.g. the conditions at lines 213 and 221) and can be changed externally while an operation runs, so the RTL does not prevent tampering with the selected function.
- availability: yes-rtl, line 256 `valid_o  <= '0';` via funct3_i -- certain funct3 encodings lead to the 'others' branch that drives result_o to zeros and valid_o='0' at lines 255-256, so external control of funct3_i can prevent useful outputs.
- undermined behavior: no, line 247 `case funct3_i is` -- funct3_i is the single selector for XTEA variants in the RTL and there is no alternate debug/test override to bypass its selection.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| funct3_i | neorv32_cpu_cp_cfu | sets | 12 -> 247 `case funct3_i is` | SELECTS result_o | verified |  | not listed |
