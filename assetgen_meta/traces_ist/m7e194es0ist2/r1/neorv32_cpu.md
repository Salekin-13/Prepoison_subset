# neorv32_cpu

**Purpose (model):** Top-level RISC-V CPU entity that instantiates the frontend, control, register-file, ALU, LSU, PMP, counters and optional ICC and wires their clocks, resets, interrupts, CSR readback and bus/ICC interfaces. It aggregates CSR sources, computes interrupt and fault signals, generates the control bus and the register-file writeback value, and forwards bus/ICC transactions to the subunits.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| operate | Control-bus generation by the control unit and distribution to frontend, counters, regfile, ALU, LSU and PMP |  | 7 / 7 |
| operate | Register-file writeback: selection of writeback source (ALU, LSU, CSR, or return PC) and delivery into the regfile |  | 2 / 2 |
| operate | CSR aggregation: assemble readback value from subunits and present it to the control unit |  | 2 / 2 |
| start | Machine-level interrupt decision computed from msi/mei/mti and delivered to the control unit |  | 2 / 2 |
| report | PMP fault reporting: PMP produces a fault flag that is consumed by control and by the LSU (zeroed when PMP is disabled by configuration) |  | 4 / 4 |
| reset | Global reset input routed into every sub-unit (propagates reset to their rstn_i ports) |  | 8 / 8 |

## Concept: Control decisions (the control bus) that determine per-cycle operations of the frontend, register-file, ALU, LSU and PMP

- confidentiality: no, line 194 `ctrl_i     => ctrl,` -- The 'ctrl' bus is only routed to internal sub-units (e.g. frontend ctrl_i at line 194) and is not directly exported on any top-level output port in this RTL.
- integrity: yes-assumed, line 253 `ctrl_o        => ctrl,` via neorv32_cpu_control_inst.ctrl_o -- The control sub-unit drives 'ctrl' (port mapping at line 253); external inputs to that sub-unit can change these control decisions and whether those writers are trusted depends on system integration.
- availability: yes-rtl, line 270 `lsu_wait_i    => lsu_wait,` via lsu_wait (neorv32_cpu_lsu_inst.wait_o => lsu_wait, line 390; depends on dbus_rsp_i at line 395) -- The control unit receives lsu_wait (line 270) driven by the LSU wait_o (line 390) which depends on external DBUS responses (line 395), so external bus behavior can stall/alter control progress.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl | neorv32_cpu | computes | 3 -> 253 `ctrl_o        => ctrl,` | CONNECTS neorv32_cpu_control_inst.ctrl_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |

## Concept: Register-file writeback value — the data selected and presented to the regfile for writing (ALU result, LSU read data, CSR readback or return-PC)


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rf_wdata | neorv32_cpu | computes | 3 -> 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` | DERIVES_FROM alu_res | verified |  | hit |
| rf_wdata | neorv32_cpu | sets | 2 -> 323 `rd_i   => rf_wdata,` | CONNECTS neorv32_cpu_regfile_inst.rd_i | verified | (via connection, mode None) | hit |

## Concept: Aggregated CSR read value (xcsr_res) assembled from CSR sources and supplied to the control unit

- confidentiality: no, line 264 `xcsr_rdata_i  => xcsr_res,` -- xcsr_res is routed only into the control unit at line 264 and the RTL does not expose it directly on any top-level output port.
- integrity: yes-assumed, line 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` via xcsr_cnt / xcsr_alu / xcsr_pmp / xcsr_icc (the source CSR buses) -- xcsr_res is formed by OR-ing multiple CSR source buses at line 279 which are driven by different sub-units and configurations, so its integrity depends on the correctness/trustworthiness of those writers.
- availability: no, line 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` -- The top-level provides an unconditional combinational assignment for xcsr_res (line 279); no runtime-ready/enable signal in this RTL blocks its assembly.
- undermined behavior: no, line 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` -- xcsr_res has a single top-level combinational driver (line 279); the presence or absence of individual source buses is determined by compile-time generates, not by a visible runtime override in this RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xcsr_res | neorv32_cpu | computes | 3 -> 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` | DERIVES_FROM xcsr_alu | verified |  | not listed |
| xcsr_res | neorv32_cpu | sets | 2 -> 264 `xcsr_rdata_i  => xcsr_res,` | CONNECTS neorv32_cpu_control_inst.xcsr_rdata_i | verified | (via connection, mode None) | not listed |

## Concept: Machine interrupt decision (irq_machine) computed from the interrupt input pins and supplied to control

- confidentiality: no, line 276 `irq_machine <= mti_i & mei_i & msi_i;` -- irq_machine is formed directly from external input pins (lines 75-77); these inputs are set by external agents and the RTL exposes no additional readback beyond those inputs.
- integrity: yes-assumed, line 276 `irq_machine <= mti_i & mei_i & msi_i;` via mti_i / mei_i / msi_i (external interrupt input pins) -- irq_machine is driven from external pins (assignment at line 276), so external agents that drive those pins can change this decision and trust depends on system integration.
- availability: no, line 276 `irq_machine <= mti_i & mei_i & msi_i;` -- irq_machine is a combinational function of input pins (line 276); there is no RTL-visible enable or stall that an external actor can toggle to freeze the existence of this vector.
- undermined behavior: no, line 276 `irq_machine <= mti_i & mei_i & msi_i;` -- irq_machine has a single combinational driver at line 276 and no alternate/runtime override is present in this RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| irq_machine | neorv32_cpu | computes | 3 -> 276 `irq_machine <= mti_i & mei_i & msi_i;` | DERIVES_FROM mei_i | verified |  | hit |
| msi_i | neorv32_cpu | sets | 2 -> 276 `irq_machine <= mti_i & mei_i & msi_i;` | SOURCES irq_machine | verified |  | hit |
| mei_i | neorv32_cpu | sets | 2 -> 276 `irq_machine <= mti_i & mei_i & msi_i;` | SOURCES irq_machine | verified |  | hit |
| mti_i | neorv32_cpu | sets | 2 -> 276 `irq_machine <= mti_i & mei_i & msi_i;` | SOURCES irq_machine | verified |  | hit |

## Concept: PMP fault indication — the flag that reports a memory access permission fault and gates control/LSU behavior (zero when PMP is disabled)


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| pmp_fault | neorv32_cpu | computes | 4 -> 420 `fault_o   => pmp_fault` | CONNECTS neorv32_cpu_pmp_inst.fault_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | hit |
| pmp_fault | neorv32_cpu | sets | 2 -> 257 `pmp_fault_i   => pmp_fault,` | CONNECTS neorv32_cpu_control_inst.pmp_fault_i | verified | (via connection, mode None) | hit |
