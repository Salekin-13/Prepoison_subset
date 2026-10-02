## 1. What the executor concluded the module does

In **3 of 3 runs**, the executor described `neorv32_cpu` as a top-level CPU integration module: it connects the frontend, control, register-file, ALU, LSU, PMP, counters and ICC, distributes control signals, routes interrupts, and combines results for writeback and CSR readback.

The runs agree on that integration purpose. Their emphasis differs: r0 includes `alu_add` address delivery, r1 includes reset distribution, and r2 separately examines fetched instructions, register operands and load data.

## 2. How it reasoned

### Flows and values

The executor built flows around `ctrl`, `rf_wdata`, `xcsr_res` and `irq_machine` in **3 of 3 runs**. `pmp_fault` reporting and reset distribution each appeared as flows in **2 of 3 runs**; r2 expanded the datapath into separate instruction-fetch, ALU-result, LSU-return and register-file flows. All flow `path` fields were null: **20 of 20**.

Its concepts questioned control decisions, writeback values, interrupt decisions, addresses, protection faults, CSR values, fetched instructions and operands. **21 of 21 concepts** had the objective `Integrity`, including concepts whose integrity answer was `unknown` or absent.

### Answers to the four questions

The following counts cover concept question sets, not runs:

| Question | `yes-assumed` | `yes-rtl` | `no` | `unknown` | Absent |
|---|---:|---:|---:|---:|---:|
| confidentiality | 6 of 21 | 0 of 21 | 11 of 21 | 1 of 21 | 3 of 21 |
| integrity | 11 of 21 | 1 of 21 | 0 of 21 | 6 of 21 | 3 of 21 |
| availability | 0 of 21 | 4 of 21 | 5 of 21 | 9 of 21 | 3 of 21 |
| undermined behavior | 0 of 21 | 1 of 21 | 15 of 21 | 2 of 21 | 3 of 21 |

In CIAU order, using `a` for `yes-assumed`, `R` for `yes-rtl`, `n` for `no`, `?` for `unknown` and `-` for absent, the most frequent pattern was `a??n` (**4 of 21**). `nann` and `----` each occurred in **3 of 21**.

Negative answers often cited the same assignment or connection used elsewhere in the concept. For example, the `xcsr_res` assignment supported `no` answers for availability and undermined behavior in r0 and r1. The `irq_machine` assignment supported availability `yes-rtl` in r0 but `no` in r1.

All positive confidentiality answers were `yes-assumed`. Their citations included `dbus_req_o` for `alu_add`, `ibus_req_o` for `ctrl`, the control connection for `xcsr_res`, and the `rf_wdata` assignment for `xcsr_res`, `lsu_rdata` and `csr_rdata`.

**Interpretation:** The answers distinguish assumptions from RTL-backed claims, but the cited routing and assignments do not, by themselves, explain the confidentiality decisions or resolve the changing negative answers.

### Roles and map evidence

The reported roles were `computes` and `sets`. The executor cited:

- `DERIVES_FROM` for the assignments producing `rf_wdata`, `irq_machine` and `xcsr_res`; these citations verified in **3 of 3 runs**.
- `SOURCES` for contributors to those values.
- `CONNECTS` for sub-unit outputs and consumer inputs.
- The conditional constant driver `pmp_fault <= '0';` when discussing disabled PMP behavior.

Overall, **20 of 41 citations** were `verified`; **21 of 41** were `edge, role unfit`. Thus, the latter citations had map edges but did not verify the assigned roles.

## 3. Blind spots

The expert reference list is used here only to locate blind spots. Reference membership and citation verification are reported separately.

### a. Missed reference entries and where they ended up

The executor reported **9 of 14 reference entries** in at least one run. The missed entries fall into these groups:

| Reference entries | Reported frequency, per entry | Where they ended up when missed |
|---|---:|---|
| `lsu_err`, `firq_i`, `dbi_i`, `lsu_mar` | 0 of 3 runs | Nowhere in the output in r0, r1 and r2 |
| `lsu_wait` | 0 of 3 runs | Concept text only in r1; nowhere in r0 and r2 |
| `alu_add` | 1 of 3 runs | Nowhere in r1 and r2 |
| `alu_res`, `csr_rdata` | 2 of 3 runs | Concept text only in r1 |
| `mei_i`, `mti_i` | 2 of 3 runs | Concept text only in r2 |

Influence points, hypotheses and exclusions were empty in **3 of 3 runs**, so none of these omissions had an exclusion reason. No missed entry was classified as appearing only in a flow path.

### b. Flow-graph elements never considered

The digest lists no flow-graph elements as never considered.

**Interpretation:** That empty result should not be treated as evidence of complete coverage, because the reference-entry omissions above remain present.

### c. Reported elements not listed by the reference

These elements are grouped by the assigned role; frequencies refer to that role and citation status.

| Role | Citation status | Elements and frequency |
|---|---|---|
| `computes` | `verified` | `xcsr_res`: 3 of 3 runs |
| `computes` | `edge, role unfit` | `ctrl`: 3 of 3 runs; `lsu_rdata`, `frontend`, `rs1`, `rs2`: each 1 of 3 runs, in r2 |
| `sets` | `verified` | `xcsr_res`: 1 of 3 runs, in r1; `xcsr_cnt`: 1 of 3 runs, in r2 |
| `sets` | `edge, role unfit` | `lsu_rdata`, `ctrl.pc_ret`, `xcsr_alu`, `xcsr_cnt`, `xcsr_icc`, `xcsr_pmp`: each 1 of 3 runs, in r0 |

In particular, `xcsr_res` was consistently reported with a verified `computes` citation despite not being listed by the reference. `xcsr_cnt` retained the role `sets` between r0 and r2, but its citation changed from `edge, role unfit` to `verified`.

### d. Citations that do not verify

The non-verifying citations divide into distinct patterns:

- **13 of 41 citations** assigned `computes` using `CONNECTS` and were `edge, role unfit`. These covered `ctrl` and `pmp_fault` in **3 of 3 runs**, `alu_add` in r0, and `alu_res`, `csr_rdata`, `lsu_rdata`, `frontend`, `rs1` and `rs2` in r2.
- **8 of 41 citations** assigned `sets` using `SOURCES` and were `edge, role unfit`. All occurred in r0, covering `alu_res`, `lsu_rdata`, `csr_rdata`, `ctrl.pc_ret`, `xcsr_alu`, `xcsr_cnt`, `xcsr_icc` and `xcsr_pmp`.

The failure therefore affects both reference-listed and reference-unlisted elements. It also coexists with verified consumer connections: r1’s `sets` citations for `rf_wdata`, `xcsr_res` and `pmp_fault` verified.

**Interpretation:** The recurring problem is not simply missing map evidence; it is assigning a role that the cited relationship does not support.

### e. Run-to-run instability

The consistently reported elements were `ctrl`, `irq_machine`, `msi_i`, `pmp_fault`, `rf_wdata` and `xcsr_res`, each in **3 of 3 runs**. Reference coverage nevertheless changed from **9 of 14** in r0 to **6 of 14** in both r1 and r2.

Instability also affected roles and answers:

- `alu_res`, `csr_rdata` and `lsu_rdata` changed from `sets` in r0 to `computes` in r2; those citations remained `edge, role unfit`.
- `ctrl` confidentiality changed from `unknown` to `no` to `yes-assumed` across r0, r1 and r2.
- `xcsr_res` confidentiality changed from `yes-assumed` to `no` to `yes-assumed`.
- `irq_machine` availability changed from `yes-rtl` to `no` to `unknown`; its integrity answer changed from `yes-assumed` in r0 and r1 to `yes-rtl` in r2.
- `pmp_fault` undermined behavior was `yes-rtl` in r0, citing its disabled-PMP constant driver; unanswered in r1; and `no` in r2, citing the PMP output connection.

## 4. Verdict

Interpretation: The integration-level account is supported by verified derivations for `rf_wdata`, `irq_machine` and `xcsr_res` in **3 of 3 runs**.  
Interpretation: The main blind spot is incomplete treatment of interrupt and LSU-related reference entries, compounded by **21 of 41** citations whose assigned roles do not verify.  
Interpretation: Trust would improve with explicit per-element coverage accounting, role-aware citation checks, and reconciliation of the four question answers against consistent evidence across runs.