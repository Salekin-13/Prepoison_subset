# neorv32_cpu

**Purpose (model):** Top-level NEORV32 CPU: instantiates and wires the CPU sub-units (frontend, control, regfile, ALU, LSU, PMP, counters, ICC), routes external interrupts and bus interfaces, combines sub-unit results into register-file write data, and forwards the control bus and CSR/status signals between sub-units.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| operate | control decisions produced by the control unit and distributed to sub-units (the 'ctrl' bus) |  | 6 / 6 |
| operate | register-file write value computed from ALU result, LSU read data, CSR read data or control pc_ret and presented to the register file (rf_wdata) |  | 2 / 2 |
| operate | effective memory address produced by the ALU (alu_add) delivered to the LSU and PMP for memory accesses and protection checks |  | 3 / 3 |
| start | machine-level interrupt event formed from external interrupt inputs (msi_i, mei_i, mti_i) and presented to the control unit |  | 5 / 5 |
| operate | combined XCSR read result (xcsr_res) assembled from sub-unit CSR sources and delivered to control |  | 2 / 2 |
| report | PMP fault indication produced by the PMP and reported to control and the LSU (pmp_fault); when PMP is disabled this signal is tied to '0' |  | 4 / 4 |

## Concept: Control-bus decisions (the 'ctrl' bus) that direct regfile/ALU/LSU/PMP behavior

- integrity: yes-assumed, line 253 `ctrl_o        => ctrl,` via neorv32_cpu_control_inst.ctrl_o -- The ctrl bus is driven by the control instance (port map at line 253); its integrity depends on trusting that writer and the inputs that drive it.
- undermined behavior: no, line 253 `ctrl_o        => ctrl,` via neorv32_cpu_control_inst.ctrl_o -- There is a single top-level driver for ctrl (the control instance at line 253) and no alternate/top-level override is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl | neorv32_cpu | computes | 3 -> 253 `ctrl_o        => ctrl,` | CONNECTS neorv32_cpu_control_inst.ctrl_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |

## Concept: Register-file write data (rf_wdata) — the  value written into the register file when an instruction writes a register


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rf_wdata | neorv32_cpu | computes | 3 -> 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` | DERIVES_FROM alu_res | verified |  | hit |
| alu_res | neorv32_cpu | sets | 2 -> 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` | SOURCES rf_wdata | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage not assigned) | hit |
| lsu_rdata | neorv32_cpu | sets | 2 -> 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` | SOURCES rf_wdata | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage not assigned) | not listed |
| csr_rdata | neorv32_cpu | sets | 3 -> 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` | SOURCES rf_wdata | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage not assigned) | hit |
| ctrl.pc_ret | neorv32_cpu | sets | 2 -> 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` | SOURCES rf_wdata | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage not assigned) | not listed |

## Concept: ALU-produced address (alu_add) used for LSU memory accesses and PMP checks

- confidentiality: yes-assumed, line 394 `dbus_req_o  => dbus_req_o,` via neorv32_cpu_lsu_inst.dbus_req_o -- alu_add is forwarded into the LSU (line 386) and the LSU drives DBUS request outputs (dbus_req_o at line 394), so computed addresses can be observed externally; confidentiality depends on system use.
- undermined behavior: no, line 370 `add_o  => alu_add,` via neorv32_cpu_alu_inst.add_o -- alu_add has a single top-level driver (ALU instance at line 370) and no alternate top-level override is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| alu_add | neorv32_cpu | computes | 3 -> 370 `add_o  => alu_add,` | CONNECTS neorv32_cpu_alu_inst.add_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | hit |

## Concept: Combined XCSR read result (xcsr_res) assembled from sub-unit CSR/status sources and presented to control

- confidentiality: yes-assumed, line 264 `xcsr_rdata_i  => xcsr_res,` via neorv32_cpu_control_inst.xcsr_rdata_i -- xcsr_res aggregates CSR/status outputs and is delivered to the control unit (line 264), which produces CSR readback outputs (line 263) that may be observed externally, so confidentiality depends on system use.
- integrity: yes-assumed, line 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` via xcsr_res assignment (line 279) from xcsr_cnt / xcsr_alu / xcsr_pmp / xcsr_icc -- xcsr_res is assembled from multiple sub-unit CSR/status sources (lines 299/371/416/445) and those contributors can be written by sub-units or external-driven inputs, so integrity depends on trusting those writers.
- availability: no, line 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` via top-level assignment at line 279 -- xcsr_res is computed unconditionally as the OR of its contributors at line 279 and has no top-level runtime enable shown that can freeze its update.
- undermined behavior: no, line 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` via top-level assignment at line 279 -- xcsr_res has a single top-level combinational driver at line 279; although some contributors are tied to zero depending on generics, no runtime override of the assignment is present at top level.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xcsr_res | neorv32_cpu | computes | 3 -> 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` | DERIVES_FROM xcsr_alu | verified |  | not listed |
| xcsr_alu | neorv32_cpu | sets | 2 -> 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` | SOURCES xcsr_res | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage not assigned) | not listed |
| xcsr_cnt | neorv32_cpu | sets | 2 -> 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` | SOURCES xcsr_res | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage none) | not listed |
| xcsr_icc | neorv32_cpu | sets | 2 -> 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` | SOURCES xcsr_res | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage none) | not listed |
| xcsr_pmp | neorv32_cpu | sets | 2 -> 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` | SOURCES xcsr_res | edge, role unfit | SOURCES does not demonstrate 'sets' (mode None, storage none) | not listed |

## Concept: Machine interrupt event (irq_machine) computed from external interrupt inputs

- confidentiality: no, line 276 `irq_machine <= mti_i & mei_i & msi_i;` via mti_i / mei_i / msi_i -- irq_machine is computed directly from external input pins (line 276) so the originator of those pins already knows and controls the values.
- integrity: yes-assumed, line 276 `irq_machine <= mti_i & mei_i & msi_i;` via mti_i / mei_i / msi_i -- irq_machine is driven by external pins (line 276) and can be altered by the external signal sources, so its integrity depends on trusting those inputs.
- availability: yes-rtl, line 276 `irq_machine <= mti_i & mei_i & msi_i;` via mti_i / mei_i / msi_i -- External interrupt inputs directly control irq_machine (line 276), and holding or clearing those inputs can prevent the control unit from seeing interrupts.
- undermined behavior: no, line 276 `irq_machine <= mti_i & mei_i & msi_i;` via assignment at line 276 -- irq_machine is computed only from the three external interrupt inputs in a single assignment at line 276 and has no alternate top-level driver.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| irq_machine | neorv32_cpu | computes | 3 -> 276 `irq_machine <= mti_i & mei_i & msi_i;` | DERIVES_FROM mei_i | verified |  | hit |
| msi_i | neorv32_cpu | sets | 2 -> 276 `irq_machine <= mti_i & mei_i & msi_i;` | SOURCES irq_machine | verified |  | hit |
| mei_i | neorv32_cpu | sets | 2 -> 276 `irq_machine <= mti_i & mei_i & msi_i;` | SOURCES irq_machine | verified |  | hit |
| mti_i | neorv32_cpu | sets | 2 -> 276 `irq_machine <= mti_i & mei_i & msi_i;` | SOURCES irq_machine | verified |  | hit |

## Concept: PMP fault indicator (pmp_fault) produced by the PMP and consumed by control/LSU to detect access violations

- confidentiality: no, line 257 `pmp_fault_i   => pmp_fault,` via neorv32_cpu_control_inst.pmp_fault_i -- pmp_fault is an internal fault indicator consumed only within the CPU (control and LSU at lines 257 and 392) and is not driven to any top-level port.
- integrity: yes-assumed, line 420 `fault_o   => pmp_fault` via neorv32_cpu_pmp_inst.fault_o -- pmp_fault is produced by the PMP sub-unit (line 420) and its correctness depends on trusting that sub-unit and the inputs it evaluates.
- availability: no, line 420 `fault_o   => pmp_fault` via neorv32_cpu_pmp_inst.fault_o -- pmp_fault is provided either by the PMP instance or tied to '0' when PMP is disabled (lines 420/427) and there is no top-level runtime enable shown that can freeze its update.
- undermined behavior: yes-rtl, line 427 `pmp_fault <= '0';` via generic RISCV_ISA_Smpmp -- A generate/configuration condition forces pmp_fault to '0' when PMP is not included (line 427), replacing the PMP-driven value in that configuration.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| pmp_fault | neorv32_cpu | computes | 4 -> 420 `fault_o   => pmp_fault` | CONNECTS neorv32_cpu_pmp_inst.fault_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | hit |
