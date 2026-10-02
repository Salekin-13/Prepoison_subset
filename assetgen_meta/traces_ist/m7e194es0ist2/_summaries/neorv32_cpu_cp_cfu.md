## 1. What the executor concluded the module does

In **3 of 3 runs**, the executor described `neorv32_cpu_cp_cfu` as a custom-function unit performing XTEA or XTEA-like computation: CSR access configures and reads `key_mem`; a start request captures `rs1_i` and `rs2_i`; internal state computes the result; and `result_o` and `valid_o` report it.

The runs agree on this functional outline. Their differences concern which controls receive separate analysis and how some security questions are answered.

## 2. How it reasoned

### Flows and values questioned

In **3 of 3 runs**, it built the same flow categories: `configure`, `start`, `operate`, `report`, `read out`, and `reset`. These describe key configuration and readback, operand capture, accumulator updates and key selection, result reporting, and clearing stored state. All flow paths were `null` in **3 of 3 runs**.

The recurring concepts were `key_mem`, captured operands in `xtea.opa` and `xtea.opb`, `xtea.sum`, `xtea.res`, and `xtea.done`. Separate treatment of CSR write controls and operation selectors varied. The stated objective was `Integrity` for **19 of 19 concepts**.

### Answers to the four questions

In confidentiality–integrity–availability–undermined behavior order, with `a` = `yes-assumed`, `R` = `yes-rtl`, and `n` = `no`:

| Pattern | Frequency |
|---|---:|
| `aRnn` | 3 of 19 |
| `nRRn` | 3 of 19 |
| `aRRn` | 7 of 19 |
| `aRRR` | 4 of 19 |
| `naRn` | 2 of 19 |

- **Confidentiality:** `yes-assumed` in **14 of 19**, `no` in **5 of 19**, and `yes-rtl` in **0 of 19**. Assumptions cite CSR key readback, `result_o`, or `valid_o`. Operand confidentiality changes between runs.
- **Integrity:** `yes-rtl` in **17 of 19** and `yes-assumed` in **2 of 19**. The assumptions concern operands and `start_i` in r1; there are no negative integrity answers.
- **Availability:** `yes-rtl` in **16 of 19**. The negative answers concern `key_mem` in **3 of 3 runs**, citing a key write or key selection.
- **Undermined behavior:** `no` in **15 of 19**. The positive answers concern the computed result in **3 of 3 runs**, citing `result_o` being set to zero, and completion in **1 of 3 runs**, citing `valid_o` being set to `'1'`. Negative answers generally cite normal assignments or control statements.

### Roles and map evidence

The executor assigned `stores` to `key_mem` and internal registers, `sets` to data inputs and controls, and `exit port` to outputs. Its cited relationships include:

- `CLOCKED_BY` linking stored state to `clk_i`;
- `CARRIES` linking `csr_wdata_i`, `rs1_i`, and `rs2_i` to their destination registers;
- `GATES` and `SELECTS` linking enables and selectors to updates or outputs;
- `DERIVES_FROM` linking `csr_rdata_o` to `key_mem` and `valid_o` to `xtea.done`;
- `COPIES` linking `result_o` to `xtea.res`.

The digest marks **51 of 51 citations** as `verified`.

## 3. Blind spots

The expert reference list is used here only to locate blind spots, not to treat unlisted elements as incorrect.

### a. Missed reference entries and their disposition

| Element | Reported coverage | Where the omission ended up |
|---|---:|---|
| `rs3_i` | 0 of 3 runs | Nowhere in the output in 3 of 3 runs |
| `active_i` | 0 of 3 runs | Nowhere in the output in 3 of 3 runs |
| `csr_we_i` | 2 of 3 runs | In r2, mentioned only in a concept’s text; not reported as an element |

Influence points, exclusions, and hypotheses were populated in **0 of 3 runs**, and explicit flow paths were populated in **0 of 3 runs**. Thus, the missing reference entries received no disposition through those structures and no exclusion reason.

### b. Flow-graph elements never considered

The digest records `csr_we_i` as never considered in **1 of 3 runs** and `rtype_i` in **2 of 3 runs**. This coverage finding coexists with textual mentions: `csr_we_i` remains in concept text in r2, while `rtype_i` appears in conditions and descriptions beyond the run that reports it.

### c. Reported elements not listed by the reference

| Assigned role | Elements | Reporting and citation status |
|---|---|---|
| `stores` | `xtea.done`, `xtea.opa`, `xtea.opb`, `xtea.sum`, `xtea.res` | Each in 3 of 3 runs; all citations `verified` |
| `sets` | `funct3_i` | 3 of 3 runs; all citations `verified` |
| `sets` | `rtype_i` | 1 of 3 runs; citation `verified` |
| `exit port` | `csr_rdata_o` | 3 of 3 runs; all citations `verified` |

### d. Citations that do not verify

Unverified citations: **0 of 51**.

**Interpretation:** Citation verification supports the reported relationships, but does not by itself establish the security conclusions. In particular, citing an output assignment does not resolve an assumed confidentiality requirement, and citing an ordinary assignment or selector does not fully explain a negative security answer.

### e. Run-to-run instability

- **Element reporting:** **15 of 17** reported elements appear in **3 of 3 runs**; `csr_we_i` appears in **2 of 3 runs**, and `rtype_i` in **1 of 3 runs**.
- **Concept boundaries:** r0 separately analyzes the CSR write decision. r1 separately analyzes `start_i`, `rtype_i`, and `funct3_i`; r2 does not create those separate concepts.
- **Operand answers:** Confidentiality is `yes-assumed` in **2 of 3 runs** and `no` in **1 of 3 runs**. Integrity is `yes-rtl` in **2 of 3 runs** and `yes-assumed` in **1 of 3 runs**.
- **Completion answers:** Undermined behavior for `xtea.done` is `no` in **2 of 3 runs** and `yes-rtl` in **1 of 3 runs**.
- **Persistent omissions:** `rs3_i` and `active_i` remain absent in **3 of 3 runs**.

## 4. Verdict

The executor consistently traces key storage, operand capture, internal computation, and result reporting, with **51 of 51 citations** verified.  
**Interpretation:** The main blind spot is incomplete element disposition: `rs3_i` and `active_i` disappear in **3 of 3 runs**, while control coverage and some security answers vary.  
**Interpretation:** Before trusting the output as complete, require explicit dispositions for reference and flow-graph elements, populated flow paths, and separate justification for security assumptions and negative answers.