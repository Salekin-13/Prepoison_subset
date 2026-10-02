# neorv32_cpu_cp_muldiv

**Purpose (model):** Decode multiply/divide coprocessor instructions from the control bus, start and sequence multi-cycle multiply or divide operations (fast parallel or serial variants depending on FAST_MUL_EN / DIVISION_EN), compute multiplication product or division quotient/remainder (signed/unsigned variants), and drive the 32-bit result (res_o) and a completion valid signal (valid_o).

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | coprocessor command validity and start indicators (valid_cmd; mul.start or div.start) that begin an operation |  | 4 / 4 |
| operate | multiplication: capture operands (mul.dsp_x / mul.dsp_y), form dsp_z (product) and register mul.prod (parallel DSP path) or shift-accumulate serial path (mul.prod, mul.add, mul_update) |  | 15 / 15 |
| operate | division: initialize dividend/abs-divisor then iterate shift/subtract to produce div.quotient / div.remainder and derive final div.res |  | 13 / 13 |
| report | completion flag valid_o asserted when FSM reaches S_DONE |  | 5 / 5 |
| read out | selected 32-bit result driven on res_o (low 32 bits of product, high 32 bits for MULH variants, or div.res for divide/remainder variants) when ctrl.out_en is set |  | 6 / 6 |
| reset | what is cleared to a known value by rstn_i: FSM (ctrl.state, ctrl.cnt, ctrl.out_en), multiplier input/accumulators (mul.dsp_x, mul.dsp_y, mul.prod) and divider registers (div.quotient, div.remainder, div.rs2_abs, div.sign_mod) |  | 16 / 16 |

## Concept: Coprocessor command decode and operation-start decision (whether an incoming control packet starts a multiply or divide)

- confidentiality: yes-assumed, line 145 `valid_o <= '1' when (ctrl.state = S_DONE) else '0';` via valid_o -- The decode valid_cmd (driven from ctrl_i fields, lines 97-99) determines starting and state transitions and its effect is visible externally through valid_o when the operation completes (line 145), so an external observer can learn the decision.
- integrity: yes-rtl, line 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` via ctrl_i -- valid_cmd is driven combinationally from ctrl_i (lines 97-99) and mul.start/div.start are derived from it (lines 154-155) with no sequencing or lock that prevents changes while the unit is running, so an external writer to ctrl_i can alter the start decision and affect the FSM and starts.
- availability: yes-rtl, line 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` via ctrl_i.alu_cp_alu -- The command-valid gate requires ctrl_i.alu_cp_alu (part of the combinational assignment at line 97), so clearing that external input prevents valid_cmd from asserting and blocks the unit from starting operations.
- undermined behavior: no, line 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` via valid_cmd -- There is a single combinational driver for the command-valid decision (valid_cmd assigned from ctrl_i at lines 97-99) and no alternate debug/test override in the RTL to replace or bypass it.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| valid_cmd | neorv32_cpu_cp_muldiv | computes | 2 -> 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` | GATED_BY ctrl_i.alu_cp_alu | verified |  | not listed |
| ctrl_i | neorv32_cpu_cp_muldiv | sets | 2 -> 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` | GATES valid_cmd | verified | (via field ctrl_i.alu_cp_alu) | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): valid_cmd <- ctrl_i.alu_cp_alu, ctrl_i.ir_funct12, ctrl_i.ir_funct3, ctrl_i.ir_opcode

## Concept: Operation sequencing and completion state (FSM state and cycle counter that determine operation duration and when results become valid)

- confidentiality: yes-assumed, line 145 `valid_o <= '1' when (ctrl.state = S_DONE) else '0';` via valid_o -- ctrl.state is directly reflected on the valid_o output (valid_o <= '1' when ctrl.state = S_DONE, line 145), so the FSM state (which reveals what the unit is doing) is observable outside the module.
- integrity: yes-rtl, line 132 `ctrl.state <= S_DONE;` via ctrl_i.cpu_trap -- While in S_BUSY the FSM will transition to S_DONE when (or_reduce_f(ctrl.cnt) = '0') or when ctrl_i.cpu_trap = '1' (lines 131-132), so an external input (cpu_trap) can change the state while an operation is in progress.
- availability: yes-rtl, line 131 `if (or_reduce_f(ctrl.cnt) = '0') or (ctrl_i.cpu_trap = '1') then` via ctrl_i.cpu_trap -- The control process checks ctrl_i.cpu_trap in S_BUSY (line 131) to move to S_DONE, thus an external signal can force or truncate the FSM and thereby stop or alter the expected sequencing and progress.
- undermined behavior: no, line 116 `case ctrl.state is` via control process / ctrl -- The FSM state is produced only by the clocked control process (case ctrl.state is ... starting at line 116 with assignments at 122/124/132/137/138) and there is no alternate debug/test mode in the RTL that substitutes or bypasses these assignments.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.state | neorv32_cpu_cp_muldiv | stores | 4 -> 122 `ctrl.state <= S_DONE;` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.cnt | neorv32_cpu_cp_muldiv | stores | 3 -> 113 `ctrl.cnt    <= std_ulogic_vector(to_unsigned(XLEN-2, ctrl.cnt'length));` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl_i | neorv32_cpu_cp_muldiv | sets | 8 -> 131 `if (or_reduce_f(ctrl.cnt) = '0') or (ctrl_i.cpu_trap = '1') then` | GATES ctrl.state | verified | (via field ctrl_i.cpu_trap) | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.state <- ctrl.cnt, ctrl.state, ctrl_i.cpu_trap, ctrl_i.ir_funct3, valid_cmd; ctrl.cnt <- ctrl.state

## Concept: Computed arithmetic result (the 32-bit value the unit delivers: product low/high or division result) that the core exports on res_o

- confidentiality: yes-assumed, line 325 `res_o <= mul.prod(31 downto 0);` via res_o -- The computed result is presented on the module output res_o (assignment from mul.prod or div.res at lines 325/327/329) so an external observer can read the computed data.
- integrity: yes-rtl, line 323 `case ctrl_i.ir_funct3 is` via ctrl_i.ir_funct3 -- The result selection and output are driven from ctrl_i.ir_funct3 at output time (case on ctrl_i.ir_funct3 in lines 323-329) without latching the opcode at operation start, and external changes to ctrl_i.ir_funct3 or other control inputs can therefore alter which value is driven to res_o or cause premature/incomplete results to be presented.
- availability: yes-rtl, line 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` via ctrl_i.alu_cp_alu -- Start of operation depends on valid_cmd which requires ctrl_i.alu_cp_alu (line 97); clearing that external input prevents operations from starting and thus stops res_o from being produced.
- undermined behavior: no, line 321 `res_o <= (others => '0');` via res_o -- res_o has a single functional driver in the operation_result process (initial assignment at line 321 and selection at lines 323-329) and there is no debug/test override in the RTL to substitute a different result source at runtime.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| res_o | neorv32_cpu_cp_muldiv | exit port | 3 -> 325 `res_o <= mul.prod(31 downto 0);` | DERIVES_FROM mul.prod | verified |  | hit |
| mul.prod | neorv32_cpu_cp_muldiv | stores | 2 -> 184 `mul.prod <= std_ulogic_vector(mul.dsp_z(63 downto 0));` | CLOCKED_BY clk_i | verified |  | hit |
| div.res | neorv32_cpu_cp_muldiv | computes | 2 -> 300 `div.res   <= std_ulogic_vector(0 - unsigned(div.res_u)) when (div.sign_mod = '1') else div` | DERIVES_FROM div.res_u | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): res_o <- ctrl.out_en, ctrl_i.ir_funct3; mul.prod <- ctrl.state, mul.start; div.res <- div.sign_mod

## Concept: Operand signedness interpretation (the per-operation flags that decide signed vs unsigned semantics for rs1 and rs2)

- confidentiality: no, line 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mulhsu_c) or` via ctrl_i.ir_funct3 -- These signedness flags are directly computed from the instruction field ctrl_i.ir_funct3 (lines 148-151) which is the same external writer that supplied them, so the setting does not reveal new secret information beyond what its writer already provided.
- integrity: yes-rtl, line 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mulhsu_c) or` via ctrl_i.ir_funct3 -- ctrl.rs1_is_signed/ctrl.rs2_is_signed are driven combinationally from ctrl_i.ir_funct3 (lines 148-151) and are read by multiplier/divider logic during operation (e.g., mul.dsp_x/mul.dsp_y at 171-173 and mul_update at 221-228 and divider init at 263-273) with no latch to freeze them for the duration, so external changes can alter signedness while an operation is in progress.
- availability: no, line 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mulhsu_c) or` via ctrl_i.ir_funct3 -- The signedness flags update combinationally from ctrl_i.ir_funct3 (lines 148-151) and there is no enable/hold/stall in the RTL that an external party can use to freeze these signals and block progress; they do not gate progress themselves.
- undermined behavior: no, line 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mulhsu_c) or` via ctrl_i.ir_funct3 -- There is a single combinational assignment for each signedness flag (lines 148-151) and no debug/test override path in the RTL that would replace or bypass these assignments at runtime.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.rs1_is_signed | neorv32_cpu_cp_muldiv | computes | 2 -> 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mu` | GATED_BY ctrl_i.ir_funct3 | verified |  | hit |
| ctrl.rs2_is_signed | neorv32_cpu_cp_muldiv | computes | 2 -> 150 `ctrl.rs2_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or` | GATED_BY ctrl_i.ir_funct3 | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.rs1_is_signed <- ctrl_i.ir_funct3; ctrl.rs2_is_signed <- ctrl_i.ir_funct3
