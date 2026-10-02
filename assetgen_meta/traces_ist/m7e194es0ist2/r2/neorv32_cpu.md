# neorv32_cpu

**Purpose (model):** Top-level NEORV32 CPU entity that wires together the frontend, control, regfile, ALU, LSU, PMP, counters and optional ICC. It forwards clock/reset and interrupt inputs to subunits, accepts fetched instructions from the frontend, receives sub-unit results (ALU, LSU, CSR, counters, PMP, ICC), and produces control signals (ctrl) that direct execution and route writeback data to the regfile.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| operate | instruction fetch delivered from frontend to control (fetched instruction + valid fields) |  | 5 / 5 |
| operate | control generation and distribution: control core computes the ctrl record and drives it to execution subunits |  | 13 / 13 |
| operate | ALU computation and delivery of ALU result into the writeback mux (alu_res -> rf_wdata) |  | 4 / 4 |
| operate | Load-store return: LSU produces load data (lsu_rdata) which feeds the writeback mux |  | 4 / 4 |
| operate | Register-file read/write: regfile provides rs1/rs2/rs3 to execution units and accepts rf_wdata as rd (writeback) |  | 8 / 8 |
| operate | CSR read aggregation: xcsr_res collects CSR sources (counters, ALU, PMP, ICC) and is delivered into control as xcsr_rdata_i |  | 4 / 4 |
| start | machine-interrupt combination: mti_i, mei_i and msi_i are combined into irq_machine and passed to control |  | 7 / 7 |
| reset | reset (rstn_i) is forwarded into instantiated sub-units (they are reset by rstn_i) |  | 18 / 18 |

## Concept: Control decisions produced by the control core (the 'ctrl' record) that direct ALU/LSU/regfile/CSR/PMP/ICC behaviour

- confidentiality: yes-assumed, line 196 `ibus_req_o => ibus_req_o,` via ibus_req_o -- The control instance drives ctrl (line 253) which is forwarded into the frontend (line 194) and the frontend drives the external ibus_req_o (line 196), so external observers can infer control decisions; confidentiality depends on integration.
- undermined behavior: no, line 253 `ctrl_o        => ctrl,` via neorv32_cpu_control_inst -- At top-level ctrl has a single driver (control instance ctrl_o at line 253); there is no alternate top-level debug/test override or second runtime driver shown.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| ctrl | neorv32_cpu | computes | 3 -> 253 `ctrl_o        => ctrl,` | CONNECTS neorv32_cpu_control_inst.ctrl_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |

## Concept: Fetched instruction stream (frontend outputs) delivered into the control pipeline

- confidentiality: no, line 255 `frontend_i    => frontend,` via neorv32_cpu_control_inst.frontend_i -- The frontend->control instruction record is consumed internally by the control instance (frontend_i mapping at line 255) and the top-level RTL provides no direct path or output that exposes the fetched-instruction words outside the IP.
- integrity: yes-assumed, line 197 `ibus_rsp_i => ibus_rsp_i,` via ibus_rsp_i -- The frontend's fetched-instruction values ultimately originate from the external instruction bus response (ibus_rsp_i mapped to the frontend at line 197) so external devices supplying bus responses can change the instructions delivered into the control pipeline; whether that writer is trusted depends on integration.
- availability: yes-rtl, line 197 `ibus_rsp_i => ibus_rsp_i,` via ibus_rsp_i -- Instruction delivery depends on external instruction-bus responses (ibus_rsp_i at line 197); an external agent that withholds or stalls those responses can prevent the frontend from producing instructions and thus stop progress.
- undermined behavior: no, line 199 `frontend_o => frontend` via neorv32_cpu_frontend_inst -- The frontend instance is the single top-level writer of the frontend record (frontend_o => frontend at line 199) and there is no alternate top-level override or debug assignment shown.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| frontend | neorv32_cpu | computes | 2 -> 199 `frontend_o => frontend` | CONNECTS neorv32_cpu_frontend_inst.frontend_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |

## Concept: Register write-back data (rf_wdata) selected from ALU / LSU / CSR / pc_ret and presented to the regfile for rd

- confidentiality: no, line 323 `rd_i   => rf_wdata,` via neorv32_cpu_regfile_inst.rd_i -- rf_wdata is an internal writeback signal presented only to the regfile (rd_i mapping at line 323) and the top-level RTL includes no direct path that exposes rf_wdata to the module boundary.
- integrity: yes-assumed, line 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` via rf_wdata assignment (from alu_res/lsu_rdata/csr_rdata/ctrl.pc_ret) -- rf_wdata is derived from sources including lsu_rdata which itself is driven from the external data bus (dbus_rsp_i), so external components can influence the value written back to registers and whether those writes are authorized depends on the integration.
- availability: no, line 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` via rf_wdata assignment -- rf_wdata is assigned combinationally at the top-level (line 330) without any top-level enable or stall input, so nothing reachable from outside the IP directly prevents the assignment from updating.
- undermined behavior: no, line 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` via rf_wdata assignment -- A single top-level combinational assignment at line 330 defines rf_wdata and no alternative runtime driver or debug override for rf_wdata is present at the top-level.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rf_wdata | neorv32_cpu | computes | 3 -> 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` | DERIVES_FROM alu_res | verified |  | hit |

## Concept: ALU result produced by the ALU and consumed by writeback and other logic (alu_res)

- confidentiality: no, line 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` via rf_wdata -- alu_res is used internally (combined into rf_wdata at line 330) and the top-level RTL provides no direct outward-facing readback or port that discloses alu_res.
- undermined behavior: no, line 369 `res_o  => alu_res,` via neorv32_cpu_alu_inst -- alu_res has a single runtime driver (ALU instance res_o at line 369) and no alternate top-level override is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| alu_res | neorv32_cpu | computes | 3 -> 369 `res_o  => alu_res,` | CONNECTS neorv32_cpu_alu_inst.res_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | hit |

## Concept: Register-file read operands (rs1, rs2) provided by the regfile to execution units

- confidentiality: no, line 324 `rs1_o  => rs1,` via neorv32_cpu_regfile_inst.rs1_o -- rs1/rs2 are register-file outputs consumed internally by execution units (e.g. ALU at line 364) and the top-level RTL does not expose rs1/rs2 directly at any module boundary.
- integrity: yes-assumed, line 323 `rd_i   => rf_wdata,` via neorv32_cpu_regfile_inst.rd_i (rf_wdata) -- The regfile contents that produce rs1/rs2 are updated via rd_i (rf_wdata mapped at line 323), and rf_wdata is influenced by external-sourced data (e.g. lsu_rdata), so whether regfile updates are authorized depends on integration.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| rs1 | neorv32_cpu | computes | 3 -> 324 `rs1_o  => rs1,` | CONNECTS neorv32_cpu_regfile_inst.rs1_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |
| rs2 | neorv32_cpu | computes | 2 -> 325 `rs2_o  => rs2,` | CONNECTS neorv32_cpu_regfile_inst.rs2_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |

## Concept: Combined machine-interrupt signal (irq_machine) computed from external interrupt inputs and delivered to control

- confidentiality: no, line 267 `irq_machine_i => irq_machine,` via neorv32_cpu_control_inst.irq_machine_i -- irq_machine is formed from external interrupt inputs and delivered to the control core (mapping at line 267) and is not a confidential internal secret.
- integrity: yes-rtl, line 276 `irq_machine <= mti_i & mei_i & msi_i;` via mti_i/mei_i/msi_i -- irq_machine is computed directly from top-level interrupt ports (assignment at line 276) with no guarding at the top-level, so external actors that drive those ports can change the interrupt vector seen by control.
- undermined behavior: no, line 276 `irq_machine <= mti_i & mei_i & msi_i;` via irq_machine assignment -- irq_machine has a single combinational assignment at line 276 and no alternate top-level override or debug bypass is present.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| irq_machine | neorv32_cpu | computes | 3 -> 276 `irq_machine <= mti_i & mei_i & msi_i;` | DERIVES_FROM mei_i | verified |  | hit |
| msi_i | neorv32_cpu | sets | 2 -> 276 `irq_machine <= mti_i & mei_i & msi_i;` | SOURCES irq_machine | verified |  | hit |

## Concept: Aggregated CSR read value (xcsr_res) formed from counters/ALU/PMP/ICC and presented to control as xcsr_rdata_i

- confidentiality: yes-assumed, line 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` via rf_wdata -- xcsr_res aggregates CSR read results and is delivered into control (line 264); control's csr_rdata can be included in rf_wdata (line 330) and written back, so CSR contents aggregated here can be observed outside the IP depending on integration.
- undermined behavior: no, line 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` via xcsr_res assignment -- The top-level simply ORs the CSR sources into xcsr_res (line 279) and there is no alternate runtime driver or debug/test override shown at this level.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| xcsr_res | neorv32_cpu | computes | 3 -> 279 `xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc;` | DERIVES_FROM xcsr_cnt | verified |  | not listed |
| xcsr_cnt | neorv32_cpu | sets | 3 -> 299 `rdata_o => xcsr_cnt` | CONNECTS neorv32_cpu_counters_inst.rdata_o | verified | (via connection, mode None) | not listed |

## Concept: PMP fault indicator (pmp_fault) produced by PMP and consumed by control/LSU

- confidentiality: no, line 257 `pmp_fault_i   => pmp_fault,` via neorv32_cpu_control_inst.pmp_fault_i -- pmp_fault is an internal fault indicator consumed by control/LSU (line 257) and is not directly presented at a module boundary as confidential data.
- undermined behavior: no, line 420 `fault_o   => pmp_fault` via neorv32_cpu_pmp_inst -- At runtime pmp_fault is driven by the PMP instance (line 420); the only other driver is a compile-time constant when PMP is disabled (line 427), not a runtime bypass.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| pmp_fault | neorv32_cpu | computes | 4 -> 420 `fault_o   => pmp_fault` | CONNECTS neorv32_cpu_pmp_inst.fault_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | hit |

## Concept: Load data returned by the LSU (lsu_rdata) that feeds writeback

- confidentiality: yes-assumed, line 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` via rf_wdata -- lsu_rdata carries load data supplied by external DBUS responses (dbus_rsp_i at line 395) and is used as a writeback source (rf_wdata at line 330), so this data can be observed outside the IP depending on integration and is therefore assumed confidential in many uses.
- integrity: yes-assumed, line 395 `dbus_rsp_i  => dbus_rsp_i` via dbus_rsp_i -- lsu_rdata originates from the external data-bus responses (dbus_rsp_i mapped to the LSU at line 395), so external devices can change the load data delivered to the CPU and affect correctness.
- availability: yes-rtl, line 395 `dbus_rsp_i  => dbus_rsp_i` via dbus_rsp_i -- The LSU's returned data depends on the external data-bus response (dbus_rsp_i at line 395); an external agent that withholds or stalls responses can prevent load data from being delivered and thus block progress.
- undermined behavior: no, line 388 `rdata_o     => lsu_rdata,` via neorv32_cpu_lsu_inst.rdata_o -- lsu_rdata is driven by the LSU instance rdata_o at line 388 and there is no alternate top-level driver or runtime override shown.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| lsu_rdata | neorv32_cpu | computes | 3 -> 388 `rdata_o     => lsu_rdata,` | CONNECTS neorv32_cpu_lsu_inst.rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | not listed |

## Concept: CSR read data produced by the control core (csr_rdata) that can be written back to registers

- confidentiality: yes-assumed, line 330 `rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret;` via rf_wdata -- csr_rdata from the control core (line 263) is included as a writeback source and can be written into registers (rf_wdata at line 330) and subsequently observed depending on integration, so CSR read results are assumed confidential in general.
- undermined behavior: no, line 263 `csr_rdata_o   => csr_rdata,` via neorv32_cpu_control_inst -- csr_rdata has a single top-level driver (control instance csr_rdata_o at line 263) and no alternate runtime override is present at the top-level.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| csr_rdata | neorv32_cpu | computes | 2 -> 263 `csr_rdata_o   => csr_rdata,` | CONNECTS neorv32_cpu_control_inst.csr_rdata_o | edge, role unfit | CONNECTS does not demonstrate 'computes' | hit |
