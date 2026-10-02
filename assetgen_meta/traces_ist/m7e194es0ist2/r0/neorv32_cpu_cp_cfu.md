# neorv32_cpu_cp_cfu

**Purpose (model):** CFU (custom function unit) that holds a 4-word key (key_mem) via CSR writes/reads, accepts a start request with operand inputs (rs1_i, rs2_i) and rtype/funct3 controls to run an XTEA-like operation, computes an internal sum/result and delivers a result and validity flag on result_o / valid_o.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | a 32-bit key word written into the key_mem array via CSR write |  | 4 / 4 |
| read out | a stored key_mem word returned on the CSR read output csr_rdata_o |  | 1 / 1 |
| start | start request that captures operands into the XTEA registers and asserts the operation-start flag |  | 4 / 4 |
| operate | XTEA internal computation: update of xtea.sum (accumulator), selection of key word (tmp_z) and computation of tmp_r and xtea.res |  | 12 / 12 |
| report | selection and export of the computed result and its validity (result_o, valid_o) |  | 7 / 7 |
| reset | what is cleared by the reset path: key_mem and the xtea record fields (done, opa, opb, sum, res) |  | 7 / 7 |

## Concept: Key memory contents (key_mem): the four 32-bit words that realize the CFU key material stored inside the block

- confidentiality: yes-assumed, line 185 `csr_rdata_o <= key_mem(to_integer(unsigned(csr_addr_i)));` via csr_rdata_o -- key_mem holds CSR-written key words and is read back directly on csr_rdata_o (line 185), so an external integrator can observe its contents.
- integrity: yes-rtl, line 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` via csr_wdata_i -- CSR writes assign key_mem at line 179 (guarded by csr_we_i at line 178) and there is no protection preventing writes while the XTEA core reads key_mem (lines 236-237), so external writes can change the stored key words.
- availability: no, line 236 `tmp_z <= key_mem(to_integer(unsigned(xtea.sum(1 downto 0)))) when (funct3_i(0) = '0') else` -- key_mem is read combinationally for the operation (tmp_z reads key_mem at line 236) and there is no input-controlled stall that freezes reads, so nothing outside the module blocks its use.
- undermined behavior: no, line 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` via csr_wdata_i -- key_mem is written only by the CSR write path at line 179 (enabled by csr_we_i) and there is no alternate debug/test override that selects a different driver.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| key_mem | neorv32_cpu_cp_cfu | stores | 3 -> 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` | CLOCKED_BY clk_i | verified |  | hit |
| csr_wdata_i | neorv32_cpu_cp_cfu | sets | 2 -> 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` | CARRIES key_mem | verified |  | hit |
| csr_rdata_o | neorv32_cpu_cp_cfu | exit port | 2 -> 185 `csr_rdata_o <= key_mem(to_integer(unsigned(csr_addr_i)));` | DERIVES_FROM key_mem | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): key_mem <- csr_addr_i, csr_we_i; csr_rdata_o <- csr_addr_i

## Concept: CSR write decision (whether a CSR write updates key_mem): the enable/address decoding that gates a write into key_mem

- confidentiality: no, line 178 `if (csr_we_i = '1') then` via csr_we_i -- the write-enable/address inputs (csr_we_i at line 178 and csr_addr_i at line 179) that decide the CSR write are provided by the external writer and thus reveal nothing new beyond the writer's own control.
- integrity: yes-rtl, line 178 `if (csr_we_i = '1') then` via csr_we_i -- csr_we_i at line 178 gates CSR writes and csr_addr_i at line 179 selects which key_mem word is updated; these inputs can be changed externally while the CFU uses key_mem (lines 236-237), so the write-decision's integrity is not enforced by the RTL.
- availability: yes-rtl, line 178 `if (csr_we_i = '1') then` via csr_we_i -- CSR writes only occur when csr_we_i = '1' (line 178), so an external agent can keep csr_we_i deasserted to prevent key_mem updates and thus prevent intended updates.
- undermined behavior: no, line 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` via csr_wdata_i -- the write-decision is implemented by the single CSR write path (assignment at line 179); there is no alternate override or special-mode driver in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| csr_we_i | neorv32_cpu_cp_cfu | sets | 2 -> 178 `if (csr_we_i = '1') then` | GATES key_mem | verified |  | hit |
| csr_addr_i | neorv32_cpu_cp_cfu | sets | 2 -> 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` | SELECTS key_mem | verified |  | hit |

## Concept: XTEA operation-in-flight / done flags (xtea.done): the pipeline bits that indicate an operation has been started and when a result is ready

- confidentiality: yes-assumed, line 250 `valid_o  <= xtea.done(1);` via valid_o -- xtea.done(1) is forwarded to the external valid_o (line 250), so external observers can learn the operation state.
- integrity: yes-rtl, line 207 `xtea.done(0) <= '1';` via start_i -- xtea.done(0) is set by the start condition at line 207 (guarded by start_i and rtype_i at line 204) and there is no RTL protection preventing external control of start_i/rtype_i while the core is running, so the done bits can be altered by external inputs.
- availability: yes-rtl, line 204 `if (start_i = '1') and (rtype_i = r3type_c) then` via start_i -- xtea.done is asserted only when start_i = '1' and rtype_i = r3type_c (line 204), so external control of start_i or rtype_i can prevent the operation from starting and thus block progress.
- undermined behavior: no, line 207 `xtea.done(0) <= '1';` via start_i -- the done bits are driven only by the xtea_core process assignments (lines 200-207); there is no separate debug/test override that bypasses these drivers.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xtea.done | neorv32_cpu_cp_cfu | stores | 3 -> 200 `xtea.done(0) <= '0';` | CLOCKED_BY clk_i | verified |  | not listed |
| start_i | neorv32_cpu_cp_cfu | sets | 2 -> 204 `if (start_i = '1') and (rtype_i = r3type_c) then` | GATES xtea.done | verified |  | hit |
| valid_o | neorv32_cpu_cp_cfu | exit port | 2 -> 250 `valid_o  <= xtea.done(1);` | DERIVES_FROM xtea.done | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.done <- rtype_i, start_i; valid_o <- funct3_i, rtype_i

## Concept: Operation operands captured for the XTEA operation (xtea.opa, xtea.opb loaded from rs1_i, rs2_i)

- confidentiality: yes-assumed, line 249 `result_o <= xtea.res;` via result_o -- the captured operands (from rs1_i/rs2_i) are used to compute the CFU result which is exported on result_o (line 249), so their values can be inferred from externally-observable results.
- integrity: yes-rtl, line 205 `xtea.opa     <= rs1_i;` via rs1_i -- xtea.opa/opb are captured from rs1_i/rs2_i at lines 205-206 under the start/rtype guard (line 204); external control of rs1_i/rs2_i or start/rtype while an operation runs can change the stored operands.
- availability: yes-rtl, line 204 `if (start_i = '1') and (rtype_i = r3type_c) then` via start_i -- operands are only captured when start_i = '1' and rtype_i = r3type_c (line 204), so external control can prevent operand capture and block the operation.
- undermined behavior: no, line 205 `xtea.opa     <= rs1_i;` via rs1_i -- the operands are driven only by the start-time copies from rs1_i/rs2_i at lines 205-206 (and reset at lines 194-195); there is no alternate debug/test override present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xtea.opa | neorv32_cpu_cp_cfu | stores | 3 -> 205 `xtea.opa     <= rs1_i;` | CLOCKED_BY clk_i | verified |  | not listed |
| rs1_i | neorv32_cpu_cp_cfu | sets | 2 -> 205 `xtea.opa     <= rs1_i;` | CARRIES xtea.opa | verified |  | hit |
| xtea.opb | neorv32_cpu_cp_cfu | stores | 3 -> 206 `xtea.opb     <= rs2_i;` | CLOCKED_BY clk_i | verified |  | not listed |
| rs2_i | neorv32_cpu_cp_cfu | sets | 2 -> 206 `xtea.opb     <= rs2_i;` | CARRIES xtea.opb | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.opa <- rtype_i, start_i; xtea.opb <- rtype_i, start_i

## Concept: XTEA accumulator state (xtea.sum): the internal sum/round accumulator that indexes key words and controls round steps

- confidentiality: yes-assumed, line 249 `result_o <= xtea.res;` via result_o -- xtea.sum controls key selection (lines 236-237) and thus affects the externally-visible result_o (line 249), so observers of result_o can infer information about the internal accumulator.
- integrity: yes-rtl, line 216 `xtea.sum <= std_ulogic_vector(unsigned(xtea.sum) + unsigned(xtea_delta_c));` via funct3_i -- xtea.sum is updated by funct3-dependent branches (lines 214, 216, 218) while gated by xtea.done(0) (line 211); because funct3_i and the gating are external inputs, an external agent can alter sum updates during operation.
- availability: yes-rtl, line 211 `if (xtea.done(0) = '1') then` via xtea.done -- xtea.sum updates occur only when xtea.done(0) = '1' (line 211), and xtea.done is controlled by start_i/rtype_i, so external control can prevent sum progression and stall the operation.
- undermined behavior: no, line 216 `xtea.sum <= std_ulogic_vector(unsigned(xtea.sum) + unsigned(xtea_delta_c));` via funct3_i -- xtea.sum is produced only by the internal branches at lines 214/216/218; there is no separate debug/test override that substitutes a different driver.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xtea.sum | neorv32_cpu_cp_cfu | stores | 3 -> 214 `xtea.sum <= xtea.opa;` | CLOCKED_BY clk_i | verified |  | not listed |
| funct3_i | neorv32_cpu_cp_cfu | sets | 2 -> 213 `if (funct3_i(2) = '1') then` | GATES xtea.sum | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.sum <- funct3_i, xtea.done

## Concept: Computed CFU result (xtea.res) and its export (result_o) with validity (valid_o)

- confidentiality: yes-assumed, line 249 `result_o <= xtea.res;` via result_o -- xtea.res is forwarded to the external result_o (line 249), so the computed CFU result is exposed outside the module.
- integrity: yes-rtl, line 179 `key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i;` via csr_wdata_i -- the computed result depends on intermediate data that includes key_mem (read at lines 236-237); CSR writes at line 179 can change key_mem while an operation is in flight and thereby alter xtea.res (assigned at lines 222/224) at unintended times, so the result's integrity can be modified via external writes.
- availability: yes-rtl, line 245 `if (rtype_i = r3type_c) then` via rtype_i -- the result_select process only forwards xtea.res when rtype_i = r3type_c (checked at line 245); changing rtype_i or funct3_i from outside causes result_o/valid_o to be driven to other values (e.g. line 261), so external inputs can block or alter the externally-observed result.
- undermined behavior: yes-rtl, line 252 `result_o <= (others => '0');` via funct3_i -- funct3_i selects alternate output behavior (xtea_init_c case at line 252) that replaces the normal xtea.res output with a constant zero and drives valid_o accordingly, providing a selectable mode that substitutes the computed result.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xtea.res | neorv32_cpu_cp_cfu | stores | 3 -> 222 `xtea.res <= std_ulogic_vector(unsigned(tmp_b) + unsigned(tmp_r));` | CLOCKED_BY clk_i | verified |  | not listed |
| result_o | neorv32_cpu_cp_cfu | exit port | 2 -> 249 `result_o <= xtea.res;` | COPIES xtea.res | verified |  | hit |
| valid_o | neorv32_cpu_cp_cfu | exit port | 2 -> 250 `valid_o  <= xtea.done(1);` | DERIVES_FROM xtea.done | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): xtea.res <- funct3_i, xtea.done; result_o <- funct3_i, rtype_i; valid_o <- funct3_i, rtype_i
