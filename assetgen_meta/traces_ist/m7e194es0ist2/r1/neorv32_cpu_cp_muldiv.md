# neorv32_cpu_cp_muldiv

**Purpose (model):** Decodes CPU control inputs to detect multiply/divide instructions, sequences and executes a multiply or divide operation (fast parallel or serial multiplier and optional serial divider), holds intermediate values (product, quotient, remainder) and delivers the selected result on res_o with valid_o indicating completion.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| start | recognition of a multiply/divide command (valid_cmd) and generation of start strobes for multiplier or divider (mul.start / div.start) |  | 4 / 4 |
| configure | operand signedness decisions derived from the instruction (ctrl.rs1_is_signed, ctrl.rs2_is_signed) |  | 4 / 4 |
| operate | multiplication: compute product from rs1_i and rs2_i (fast parallel path or serial path), store full product in mul.prod |  | 5 / 5 |
| operate | division: compute quotient and remainder from rs1_i and rs2_i and form final signed/unsigned result (div.res) |  | 10 / 10 |
| report | completion indicator valid_o asserted when the operation state reaches S_DONE |  | 3 / 3 |
| read out | final result returned on res_o (selected from mul.prod or div.res when ctrl.out_en enables output) |  | 4 / 4 |
| reset | reset to known values for control, multiplier and divider registers under rstn_i |  | 8 / 8 |

## Concept: Decoded multiply/divide command and operation selection (which instruction the unit should execute and whether to start mul or div)

- confidentiality: no, line 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` via ctrl_i -- valid_cmd is a combinational decode of ctrl_i instruction fields (line 97) and therefore conveys no information beyond inputs the instruction writer already holds.
- integrity: yes-assumed, line 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` via ctrl_i -- valid_cmd is produced directly from external control inputs (line 97), so an external writer of ctrl_i can change the decision and thereby choose whether/which unit starts.
- availability: yes-rtl, line 154 `mul.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '0') else '0';` via valid_cmd (ctrl_i) -- the start strobes (mul.start/div.start) are gated from valid_cmd (lines 154-155), so external control inputs can prevent or force operation start and block progress.
- undermined behavior: no, line 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` via ctrl_i -- valid_cmd has a single combinational driver from the ctrl_i instruction fields (line 97) and there is no alternate debug/test override in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl_i | neorv32_cpu_cp_muldiv | sets | 2 -> 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` | GATES valid_cmd | verified | (via field ctrl_i.alu_cp_alu) | not listed |
| valid_cmd | neorv32_cpu_cp_muldiv | computes | 2 -> 97 `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` | GATED_BY ctrl_i.ir_funct3 | verified |  | not listed |
| mul.start | neorv32_cpu_cp_muldiv | computes | 2 -> 154 `mul.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '0') else '0';` | GATED_BY valid_cmd | verified |  | hit |
| div.start | neorv32_cpu_cp_muldiv | computes | 2 -> 155 `div.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '1') else '0';` | GATED_BY valid_cmd | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): valid_cmd <- ctrl_i.alu_cp_alu, ctrl_i.ir_funct12, ctrl_i.ir_funct3, ctrl_i.ir_opcode; mul.start <- ctrl_i.ir_funct3, valid_cmd; div.start <- ctrl_i.ir_funct3, valid_cmd

## Concept: Operand values supplied to the unit (rs1_i and rs2_i) that are consumed to compute product or quotient/remainder

- confidentiality: yes-assumed, line 325 `res_o <= mul.prod(31 downto 0);` via res_o -- rs1_i/rs2_i are external input data and processed results derived from them are output on res_o (e.g. mul low bits at line 325 or div result at line 329), so the inputs' information can be observed externally via the result.
- integrity: yes-assumed, line 171 `mul.dsp_x <= signed((rs1_i(rs1_i'left) and ctrl.rs1_is_signed) & rs1_i);` via rs1_i, rs2_i -- the RTL shows internal copies of the operand ports (mul.dsp_x/mul.dsp_y at lines 170-173 and divider captures at 263-273), so external writers of rs1_i/rs2_i can change the operands and thus alter the computation.
- availability: yes-rtl, line 154 `mul.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '0') else '0';` via mul.start / div.start (valid_cmd, ctrl_i) -- operand capture into the unit is gated by the start strobes (mul.start/div.start at lines 154-155 driven from valid_cmd), so external control of valid_cmd/ctrl_i can prevent operand capture and stall progress.
- undermined behavior: no, line 171 `mul.dsp_x <= signed((rs1_i(rs1_i'left) and ctrl.rs1_is_signed) & rs1_i);` via mul.start -- operands are captured only by the regular start-paths (e.g. mul.dsp_x/mul.dsp_y at line 171) and there is no alternate debug/test override that replaces these operand sources in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rs1_i | neorv32_cpu_cp_muldiv | sets | 2 -> 171 `mul.dsp_x <= signed((rs1_i(rs1_i'left) and ctrl.rs1_is_signed) & rs1_i);` | SOURCES mul.dsp_x | verified |  | hit |
| mul.dsp_x | neorv32_cpu_cp_muldiv | stores | 3 -> 171 `mul.dsp_x <= signed((rs1_i(rs1_i'left) and ctrl.rs1_is_signed) & rs1_i);` | CLOCKED_BY clk_i | verified |  | not listed |
| rs2_i | neorv32_cpu_cp_muldiv | sets | 2 -> 172 `mul.dsp_y <= signed((rs2_i(rs2_i'left) and ctrl.rs2_is_signed) & rs2_i);` | SOURCES mul.dsp_y | verified |  | hit |
| mul.dsp_y | neorv32_cpu_cp_muldiv | stores | 3 -> 172 `mul.dsp_y <= signed((rs2_i(rs2_i'left) and ctrl.rs2_is_signed) & rs2_i);` | CLOCKED_BY clk_i | verified |  | not listed |
| div.quotient | neorv32_cpu_cp_muldiv | stores | 3 -> 264 `div.quotient <= std_ulogic_vector(0 - unsigned(rs1_i));` | CLOCKED_BY clk_i | verified |  | not listed |
| div.rs2_abs | neorv32_cpu_cp_muldiv | stores | 3 -> 270 `div.rs2_abs <= std_ulogic_vector(0 - unsigned(rs2_i));` | CLOCKED_BY clk_i | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): mul.dsp_x <- mul.start; mul.dsp_y <- mul.start; div.quotient <- ctrl.rs1_is_signed, ctrl.state, div.start, rs1_i; div.rs2_abs <- ctrl.rs2_is_signed, div.start, rs2_i

## Concept: Operand signedness decisions (ctrl.rs1_is_signed, ctrl.rs2_is_signed) that determine signed vs unsigned interpretation of inputs

- confidentiality: no, line 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mulhsu_c) or` via ctrl_i.ir_funct3 -- the signedness flags are purely a direct decode of ctrl_i.ir_funct3 (line 148) and do not appear on any module output themselves, so the RTL does not reveal additional secret data beyond the instruction fields.
- integrity: yes-assumed, line 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mulhsu_c) or` via ctrl_i.ir_funct3 -- ctrl.rs1_is_signed / ctrl.rs2_is_signed are driven from external instruction bits (lines 148-151), so an external writer of ctrl_i can change these interpretation flags and thus alter how operands are treated.
- availability: no, line 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mulhsu_c) or` via ctrl_i.ir_funct3 -- these signals are combinationally derived from ctrl_i.ir_funct3 (line 148) and update whenever the inputs change; there is no input-controllable stall/halt in the RTL that freezes them.
- undermined behavior: no, line 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mulhsu_c) or` via ctrl_i.ir_funct3 -- there is a single combinational driver from ctrl_i.ir_funct3 (lines 148-151) and no debug/test override or alternate assignment path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.rs1_is_signed | neorv32_cpu_cp_muldiv | computes | 2 -> 148 `ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or (ctrl_i.ir_funct3 = op_mu` | GATED_BY ctrl_i.ir_funct3 | verified |  | hit |
| ctrl.rs2_is_signed | neorv32_cpu_cp_muldiv | computes | 2 -> 150 `ctrl.rs2_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or` | GATED_BY ctrl_i.ir_funct3 | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.rs1_is_signed <- ctrl_i.ir_funct3; ctrl.rs2_is_signed <- ctrl_i.ir_funct3

## Concept: Operation sequencing state and countdown (ctrl.state and ctrl.cnt) that determine when an operation is in progress and when it completes

- confidentiality: yes-assumed, line 145 `valid_o <= '1' when (ctrl.state = S_DONE) else '0';` via valid_o -- ctrl.state is a status register whose S_DONE value is exposed on valid_o (line 145) and its transitions reveal the unit's activity, so its value (and what it reveals) can be observed externally.
- integrity: yes-rtl, line 131 `if (or_reduce_f(ctrl.cnt) = '0') or (ctrl_i.cpu_trap = '1') then` via ctrl_i.cpu_trap -- the control process allows external inputs to alter sequencing (ctrl.state is forced to S_DONE when ctrl_i.cpu_trap = '1' per line 131), so an external input can change the state while an operation is in progress.
- availability: yes-rtl, line 131 `if (or_reduce_f(ctrl.cnt) = '0') or (ctrl_i.cpu_trap = '1') then` via ctrl_i.cpu_trap -- an external input (ctrl_i.cpu_trap) appears in the completion condition (line 131) and can force or abort progress, so outside signals can stop or force the state machine.
- undermined behavior: yes-rtl, line 122 `ctrl.state <= S_DONE;` via FAST_MUL_EN (generic) / ctrl_i.ir_funct3 -- a special-path selection (FAST_MUL_EN with the funct3 check) bypasses the busy sequencing and sets ctrl.state to S_DONE immediately (line 121-122), providing an alternate completion path.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl.state | neorv32_cpu_cp_muldiv | stores | 4 -> 122 `ctrl.state <= S_DONE;` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl.cnt | neorv32_cpu_cp_muldiv | stores | 3 -> 113 `ctrl.cnt    <= std_ulogic_vector(to_unsigned(XLEN-2, ctrl.cnt'length));` | CLOCKED_BY clk_i | verified |  | hit |
| valid_o | neorv32_cpu_cp_muldiv | exit port | 2 -> 145 `valid_o <= '1' when (ctrl.state = S_DONE) else '0';` | GATED_BY ctrl.state | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): ctrl.state <- ctrl.cnt, ctrl.state, ctrl_i.cpu_trap, ctrl_i.ir_funct3, valid_cmd; ctrl.cnt <- ctrl.state; valid_o <- ctrl.state

## Concept: Final operation result (the value delivered to the requester on res_o, taken from the multiplier product or divider result)

- confidentiality: yes-assumed, line 325 `res_o <= mul.prod(31 downto 0);` via res_o -- the final result is presented on the external output res_o (e.g. mul low bits at line 325 or div.res at line 329), so data derived from internal operands is observable outside the IP.
- integrity: no, line 325 `res_o <= mul.prod(31 downto 0);` via res_o -- res_o is driven internally from the computed sources (mul.prod or div.res selected in the operation_result process at lines 325/327/329) and there is no external writer that can directly overwrite the output in the RTL.
- availability: yes-rtl, line 322 `if (ctrl.out_en = '1') then` via ctrl.out_en -- res_o is gated by ctrl.out_en (operation_result checks ctrl.out_en at line 322), and ctrl.out_en/state can be controlled by inputs (ctrl_i) so external signals can prevent or force the output from being presented.
- undermined behavior: no, line 325 `res_o <= mul.prod(31 downto 0);` via res_o -- the RTL has a single selection mechanism (case on ctrl_i.ir_funct3 guarded by ctrl.out_en at lines 323-329) and no separate debug/test override that substitutes a different result source.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| mul.prod | neorv32_cpu_cp_muldiv | stores | 2 -> 184 `mul.prod <= std_ulogic_vector(mul.dsp_z(63 downto 0));` | CLOCKED_BY clk_i | verified |  | hit |
| div.quotient | neorv32_cpu_cp_muldiv | stores | 3 -> 264 `div.quotient <= std_ulogic_vector(0 - unsigned(rs1_i));` | CLOCKED_BY clk_i | verified |  | not listed |
| div.remainder | neorv32_cpu_cp_muldiv | stores | 3 -> 283 `div.remainder <= (others => '0');` | CLOCKED_BY clk_i | verified |  | not listed |
| div.res | neorv32_cpu_cp_muldiv | computes | 2 -> 300 `div.res   <= std_ulogic_vector(0 - unsigned(div.res_u)) when (div.sign_mod = '1') else div` | DERIVES_FROM div.res_u | verified |  | hit |
| res_o | neorv32_cpu_cp_muldiv | exit port | 3 -> 325 `res_o <= mul.prod(31 downto 0);` | DERIVES_FROM mul.prod | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): mul.prod <- ctrl.state, mul.start; div.quotient <- ctrl.rs1_is_signed, ctrl.state, div.start, rs1_i; div.remainder <- ctrl.state, div.start, div.sub; div.res <- div.sign_mod; res_o <- ctrl.out_en, ctrl_i.ir_funct3
