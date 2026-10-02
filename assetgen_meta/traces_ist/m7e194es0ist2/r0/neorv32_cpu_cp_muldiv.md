# neorv32_cpu_cp_muldiv

**Purpose (model):** Decodes multiply/divide ALU control inputs and, on a recognized multiply/divide instruction, runs a multiply or divide datapath (parallel DSP when FAST_MUL_EN or a serial algorithm otherwise; iterative divider when DIVISION_EN), sequences the multi-cycle operation with an internal state and counter, and presents the computed product/quotient/remainder on res_o with valid_o asserted when done.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | recognition of a multiply/divide coprocessor instruction and generation of per-datapath start signals |  | 5 / 5 |
| operate | multiply operation: load operands into multiplier, compute product (parallel DSP or serial shift-add), and update mul.prod |  | 15 / 15 |
| operate | divide operation: initialize quotient/remainder/rs2_abs and iterate subtract/shift steps to form quotient and remainder, then compute signed adjustment |  | 18 / 18 |
| report | signal completion (valid_o) when state machine reaches S_DONE |  | 5 / 5 |
| read out | deliver the selected result on res_o (lower/upper product words or divider result) when ctrl.out_en is asserted |  | 6 / 6 |
| reset | synchronous/asynchronous clears of control and datapath registers on rstn_i = '0' (controller state/counter, mul and div registers) |  | 14 / 14 |

## Concept: Operation start decision (instruction recognition -> mul.start / div.start)

- confidentiality: yes-assumed, line 325 `res_o <= mul.prod(31 downto 0);` via res_o -- The instruction-recognition combinational result (valid_cmd, lines 97-99) controls mul.start/div.start (lines 154-155) and the selected datapath result is driven onto res_o (lines 325/329), so an external observer can infer the start decision.
- integrity: yes-rtl, line 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` via ctrl_i.alu_cp_alu / ctrl_i.ir_opcode / ctrl_i.ir_funct12 / ctrl_i.ir_funct3 -- valid_cmd is computed combinationally from external ctrl_i fields (line 97) and is used directly by the control process (e.g. line 120) to start datapaths (lines 154-155), so those external inputs can change the start decision while it is in use.
- availability: yes-rtl, line 154 `mul.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '0') else '0';` via valid_cmd / ctrl_i.ir_funct3 -- mul.start/div.start are gated by valid_cmd and instruction bits (lines 154-155), so external control inputs (ctrl_i fields) can prevent start and block operation progress.
- undermined behavior: no, line 154 `mul.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '0') else '0';` -- There is no runtime debug/test override in the RTL; start signals are driven only by valid_cmd and ir_funct3 (lines 154-155).

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| valid_cmd | neorv32_cpu_cp_muldiv | computes | 2 -> 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` | GATED_BY ctrl_i.alu_cp_alu | verified |  | not listed |
| ctrl_i.alu_cp_alu | neorv32_cpu_cp_muldiv | sets | 2 -> 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` | GATES valid_cmd | verified |  | not listed |
| ctrl_i.ir_opcode | neorv32_cpu_cp_muldiv | sets | 2 -> 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` | GATES valid_cmd | verified |  | not listed |
| ctrl_i.ir_funct12 | neorv32_cpu_cp_muldiv | sets | 2 -> 98 `(ctrl_i.ir_funct12(11 downto 5) = "0000001") and` | GATES valid_cmd | verified |  | not listed |
| mul.start | neorv32_cpu_cp_muldiv | sets | 2 -> 154 `mul.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '0') else '0';` | GATED_BY valid_cmd | verified |  | hit |
| div.start | neorv32_cpu_cp_muldiv | sets | 2 -> 155 `div.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '1') else '0';` | GATED_BY valid_cmd | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): valid_cmd <- ctrl_i.alu_cp_alu, ctrl_i.ir_funct12, ctrl_i.ir_funct3, ctrl_i.ir_opcode; mul.start <- ctrl_i.ir_funct3, valid_cmd; div.start <- ctrl_i.ir_funct3, valid_cmd

## Concept: Operand values (rs1_i, rs2_i) supplied to multiplier and divider

- confidentiality: yes-assumed, line 325 `res_o <= mul.prod(31 downto 0);` via res_o -- rs1_i/rs2_i are external inputs that are used to compute results forwarded to res_o (lines 325/327/329), so operand-derived information can be observed outside the module.
- integrity: yes-assumed, line 171 `mul.dsp_x <= signed((rs1_i(rs1_i'left) and ctrl.rs1_is_signed) & rs1_i);` via rs1_i / rs2_i (input ports) -- Operand values are provided by external input ports and copied into internal registers (e.g. mul.dsp_x/mul.dsp_y at lines 171-172), so their integrity depends on the trustworthiness of those external writers.
- availability: yes-rtl, line 171 `mul.dsp_x <= signed((rs1_i(rs1_i'left) and ctrl.rs1_is_signed) & rs1_i);` via mul.start (driven by valid_cmd / ctrl_i) -- Operands are captured into internal registers only when mul.start/div.start are asserted (lines 170-173 and 261-273), and those start signals depend on external ctrl_i fields, so outsiders can prevent capture and stall progress.
- undermined behavior: no, line 171 `mul.dsp_x <= signed((rs1_i(rs1_i'left) and ctrl.rs1_is_signed) & rs1_i);` -- There is no runtime debug/test bypass of the operand paths; operands are written into the datapath only via the input ports under the indicated guards (e.g. lines 171-172, 212, 263-273).

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rs1_i | neorv32_cpu_cp_muldiv | sets | 2 -> 171 `mul.dsp_x <= signed((rs1_i(rs1_i'left) and ctrl.rs1_is_signed) & rs1_i);` | SOURCES mul.dsp_x | verified |  | hit |
| rs2_i | neorv32_cpu_cp_muldiv | sets | 2 -> 172 `mul.dsp_y <= signed((rs2_i(rs2_i'left) and ctrl.rs2_is_signed) & rs2_i);` | SOURCES mul.dsp_y | verified |  | hit |

## Concept: Multiplication product value produced by the multiplier (mul.prod) and delivered externally

- confidentiality: yes-assumed, line 325 `res_o <= mul.prod(31 downto 0);` via res_o -- mul.prod is selected and placed on res_o for multiply instructions (lines 325,327), so the product is externally observable.
- integrity: yes-rtl, line 184 `mul.prod <= std_ulogic_vector(mul.dsp_z(63 downto 0));` via mul.dsp_z (driven by mul.dsp_x/mul.dsp_y from rs1_i/rs2_i) -- mul.prod is updated by the multiplier (e.g. line 184 for the parallel DSP, or lines 211-216 for the serial path) while operation_result reads mul.prod when ctrl.out_en is asserted (lines 321-329), and nothing in the RTL prevents concurrent updates by new inputs, so external inputs can change the product while it is being used.
- availability: yes-rtl, line 154 `mul.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '0') else '0';` via mul.start / valid_cmd -- Generation/capture of the multiplication product depends on mul.start (line 154) and the control state, so external control inputs can prevent product generation and block progress.
- undermined behavior: no, line 184 `mul.prod <= std_ulogic_vector(mul.dsp_z(63 downto 0));` -- There is no runtime debug/test override that substitutes mul.prod; its drivers are the multiplier paths (lines 184 and 211-216), selected by the compile-time FAST_MUL_EN generic.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| mul.prod | neorv32_cpu_cp_muldiv | stores | 2 -> 184 `mul.prod <= std_ulogic_vector(mul.dsp_z(63 downto 0));` | CLOCKED_BY clk_i | verified |  | hit |
| res_o | neorv32_cpu_cp_muldiv | exit port | 3 -> 325 `res_o <= mul.prod(31 downto 0);` | DERIVES_FROM mul.prod | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): mul.prod <- ctrl.state, mul.start; res_o <- ctrl.out_en, ctrl_i.ir_funct3

## Concept: Division result (quotient or remainder) computed by the divider and forwarded

- confidentiality: yes-assumed, line 329 `res_o <= div.res;` via res_o -- div.res is selected and copied to res_o (line 329) when the result is presented, so the divider result is observable outside the module.
- integrity: yes-rtl, line 300 `div.res   <= std_ulogic_vector(0 - unsigned(div.res_u)) when (div.sign_mod = '1') else div.res_u;` via ctrl_i.ir_funct3 -- div.res is computed from div.res_u (lines 299-300) where res_u and sign_mod depend on ctrl_i.ir_funct3 and the operand registers (lines 275-279, 299), and those inputs can be changed while the operation runs, so external inputs can alter the final divider result.
- availability: yes-rtl, line 155 `div.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '1') else '0';` via div.start / valid_cmd / ctrl_i.ir_funct3 -- Division starts only when div.start is asserted (line 155, driven by valid_cmd and instruction bits), and DIVISION_EN / ctrl_i fields can prevent start, blocking divider progress.
- undermined behavior: no, line 300 `div.res   <= std_ulogic_vector(0 - unsigned(div.res_u)) when (div.sign_mod = '1') else div.res_u;` -- No runtime debug/test bypass substitutes the divider result; the divider output path is uniquely implemented in RTL (lines 299-300) apart from the compile-time DIVISION_EN configuration.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| div.res | neorv32_cpu_cp_muldiv | computes | 2 -> 300 `div.res   <= std_ulogic_vector(0 - unsigned(div.res_u)) when (div.sign_mod = '1') else div` | DERIVES_FROM div.res_u | verified |  | hit |
| res_o | neorv32_cpu_cp_muldiv | exit port | 5 -> 329 `res_o <= div.res;` | COPIES div.res | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): div.res <- div.sign_mod; res_o <- ctrl.out_en, ctrl_i.ir_funct3

## Concept: Control state machine (ctrl.state) and sequencing registers that govern operation progression and completion

- confidentiality: yes-assumed, line 145 `valid_o <= '1' when (ctrl.state = S_DONE) else '0';` via valid_o -- ctrl.state is directly exposed by valid_o (valid_o <= '1' when ctrl.state = S_DONE at line 145) and therefore reveals the block's progression to external observers.
- integrity: yes-rtl, line 132 `ctrl.state <= S_DONE;` via ctrl_i.cpu_trap -- ctrl.state can be forced to S_DONE from the S_BUSY branch when (or_reduce_f(ctrl.cnt) = '0') or (ctrl_i.cpu_trap = '1') (assignment at line 132), so an external input (ctrl_i.cpu_trap) can change the state while an operation is in progress.
- availability: yes-rtl, line 132 `ctrl.state <= S_DONE;` via ctrl_i.cpu_trap -- State transitions are gated by external-controlled conditions (e.g. ctrl_i.cpu_trap used at line 132 and valid_cmd in earlier lines), so external inputs can stop, freeze or force the state machine and block progress.
- undermined behavior: no, line 122 `ctrl.state <= S_DONE;` -- There is no runtime debug/test override of the state machine; ctrl.state is updated only by the control process case statements (lines 122,124,132,138).

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.state | neorv32_cpu_cp_muldiv | stores | 4 -> 122 `ctrl.state <= S_DONE;` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.cnt | neorv32_cpu_cp_muldiv | stores | 3 -> 113 `ctrl.cnt    <= std_ulogic_vector(to_unsigned(XLEN-2, ctrl.cnt'length));` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.out_en | neorv32_cpu_cp_muldiv | stores | 4 -> 137 `ctrl.out_en <= '1';` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.state <- ctrl.cnt, ctrl.state, ctrl_i.cpu_trap, ctrl_i.ir_funct3, valid_cmd; ctrl.cnt <- ctrl.state; ctrl.out_en <- ctrl.state

## Concept: Result-ready indicator (valid_o) that reports operation completion to the outside

- confidentiality: yes-assumed, line 145 `valid_o <= '1' when (ctrl.state = S_DONE) else '0';` via valid_o -- valid_o is an external output directly driven from ctrl.state (line 145) and therefore reveals operation completion/state to observers outside the module.
- integrity: yes-rtl, line 145 `valid_o <= '1' when (ctrl.state = S_DONE) else '0';` via ctrl.state (affected by ctrl_i.cpu_trap) -- valid_o is driven from ctrl.state (line 145) and ctrl.state can be altered by external inputs (e.g. ctrl_i.cpu_trap at line 132), so external inputs can change the ready indication at times that affect consumers.
- availability: yes-rtl, line 145 `valid_o <= '1' when (ctrl.state = S_DONE) else '0';` via ctrl_i.cpu_trap -- valid_o depends on ctrl.state and can be forced or cleared by external-controlled conditions (ctrl_i.cpu_trap, reset), so outsiders can prevent or force the ready indication.
- undermined behavior: no, line 145 `valid_o <= '1' when (ctrl.state = S_DONE) else '0';` -- There is no alternate debug/test path that substitutes or bypasses valid_o; it is derived solely from ctrl.state (line 145).

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| valid_o | neorv32_cpu_cp_muldiv | exit port | 2 -> 145 `valid_o <= '1' when (ctrl.state = S_DONE) else '0';` | GATED_BY ctrl.state | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): valid_o <- ctrl.state

## Concept: Signedness controls (ctrl.rs1_is_signed, ctrl.rs2_is_signed) selecting signed vs unsigned arithmetic

- confidentiality: yes-assumed, line 325 `res_o <= mul.prod(31 downto 0);` via res_o -- Signedness flags change arithmetic semantics and therefore the values driven onto res_o (lines 325/327/329), so an external observer can infer the signedness from outputs.
- integrity: yes-rtl, line 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mulhsu_c) or` via ctrl_i.ir_funct3 -- The flags are driven combinationally from ctrl_i.ir_funct3 (line 148-151) and can be changed by external instruction fields while arithmetic uses them (e.g. divider initialization line 263, mul.add at line 224), so their integrity is not protected by the RTL.
- availability: no, line 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mulhsu_c) or` via ctrl_i.ir_funct3 -- The signedness flags update combinationally from ctrl_i.ir_funct3 (line 148) and do not themselves gate progress (they alter computation semantics but do not block the datapath), so nothing externally reachable in the RTL solely freezes progress by holding these flags.
- undermined behavior: no, line 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mulhsu_c) or` -- There is no runtime debug/test override of the signedness signals; they are driven only from ir_funct3 fields (lines 148-151).

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.rs1_is_signed | neorv32_cpu_cp_muldiv | computes | 2 -> 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mu` | GATED_BY ctrl_i.ir_funct3 | verified |  | hit |
| ctrl.rs2_is_signed | neorv32_cpu_cp_muldiv | computes | 2 -> 150 `ctrl.rs2_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or` | GATED_BY ctrl_i.ir_funct3 | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.rs1_is_signed <- ctrl_i.ir_funct3; ctrl.rs2_is_signed <- ctrl_i.ir_funct3
