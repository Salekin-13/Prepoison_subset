# `neorv32_bus` — trust summary
Version: `m7e194es0ist2`

## 1. What the executor concluded the module does

The runs agree on the module’s broad function in **3 of 3 runs**: arbitration and request multiplexing, address decoding and downstream routing, response forwarding or aggregation, optional request/response register staging, and AMO/RVS sequencing. Timeout monitoring also appears in the analysis in **3 of 3 runs**.

The differences concern which values become reported elements, rather than conflicting descriptions of the module’s purpose.

## 2. How it reasoned

### Flows and questioned values

The executor built flows around transaction start, arbitration, request forwarding, lock retention/release, response delivery, address decoding, timeout tracking, AMO computation/writeback, RVS results, and reset. Classification varied: lock capture was a `lock` flow in r0 but `configure` in r1; address routing was `read out` in r1 but `operate` in r2. The flows remained descriptions: `path` was null in **23 of 23** flows.

The assessed values included grant decisions, request and response contents, stored sequencing state, lock state, address-decode results, timeout state, `alu_res`, and store-conditional results. The selected objective was `Integrity` in **23 of 24** concepts; the exception was r0’s `keeper.err` concept, which selected `Availability`.

### Answers to the CIAU questions

Here, `a` means `yes-assumed`, `R` means `yes-rtl`, and `n` means `no`; positions are confidentiality, integrity, availability, and undermined behavior.

| Pattern | Frequency |
|---|---:|
| `aaRn` | 15 of 24 |
| `aRRn` | 3 of 24 |
| `aann` | 3 of 24 |
| `nRRn` | 1 of 24 |
| `aaRR` | 1 of 24 |
| `aRRR` | 1 of 24 |

- **Confidentiality:** `yes-assumed` in **23 of 24** assessments, with no `yes-rtl` answers. The exception was address decoding in r2, answered `no`.
- **Integrity:** `yes-assumed` in **19 of 24** and `yes-rtl` in **5 of 24**; no negative answers.
- **Availability:** `yes-rtl` in **21 of 24**. Negative answers concerned address decoding in r0 and r1, and the store-conditional result in r0.
- **Undermined behavior:** `no` in **22 of 24**. The positive answers were both in r2: response aggregation through `int_rsp`, and request-tracking/timeout state involving `keeper.halt` and `keeper.err`.

**Interpretation:** The confidentiality answers should be treated as assumptions, not demonstrated confidentiality requirements; this applies to control decisions and state as well as transferred data.

### Roles and map evidence

The executor assigned `stores` to clocked state and results, `computes` to selections and derived controls, `sets` to request inputs, and `exit port` to outgoing requests and responses. Its map evidence connected:

- stored values to `clk_i` through `CLOCKED_BY`;
- `sel` and `stb` to `state` through `SELECTED_BY`;
- request selection, lock capture, response aggregation, and AMO writeback through `DERIVES_FROM`;
- forwarding through `COPIES`, and controls through `GATED_BY` or `GATES`.

Citation statuses were **55 of 65 `verified`** and **10 of 65 `occurrence only`**. The latter all came from r0.

## 3. Blind spots

The expert reference list is used here only to locate omissions. Absence from that list is not treated as evidence that a reported element is wrong.

### a. Missed reference entries and their disposition

| Reference elements | Reported coverage | Where they ended up when missed |
|---|---:|---|
| `a_req`, `b_req` | Each in 1 of 3 runs | Concept text only in r1 and r2 |
| `keeper.halt`, `keeper.cnt` | Each in 1 of 3 runs | Concept text only in r0 and r1 |
| `sel`, `port_sel`, `stb` | Each in 2 of 3 runs | Concept text only in r1 |

`keeper.err`, `state`, and `alu_res` were reported in **3 of 3 runs** each. The expert reference list contains repeated `state` entries, while the coverage aggregate uses the single name `state`.

In **3 of 3 runs**, influence-point, hypothesis, and exclusion lists were empty. Thus the missed entries were not explicitly excluded with reasons, assigned as influence points, or retained as hypotheses; the digest classifies their disposition as concept text only, not only in a flow path or nowhere.

### b. Flow-graph elements never considered

The digest records the following coverage gaps:

| Never considered in | Elements |
|---|---|
| **3 of 3 runs** | `a_req_i.fence`, `b_req_i.fence`, `arbiter.state`, `b_req_o`, `c_req_o`, `core_req_i.amo`, `core_req_i.amoop`, `core_req_i.rw`, `core_rsp_o.data`, `core_rsp_o.err`, `device_req_o.fence`, `device_req_o.lock`, `device_req_o.stb`, `sys_req_o.stb`, `sys_rsp_i.ack`, `x_req_o.amo`, `x_req_o.amoop`, `x_req_o.ben`, `x_req_o.debug`, `x_req_o.priv`, `x_req_o.src` |
| **2 of 3 runs** | `a_req`, `b_req`, `keeper.cnt`, `req_i.addr`, `sys_req_o.data`, `x_req_o`, `x_req_o.addr`, `x_req_o.data`, `x_req_o.lock`, `x_req_o.rw`, `x_req_o.stb` |
| **1 of 3 runs** | `a_req_o`, `keeper.busy`, `keeper.lock` |

These are element-level coverage results: for example, `arbiter` was reported in **2 of 3 runs**, while `arbiter.state` was never considered in **3 of 3 runs**. Similarly, r1 cited `a_req_i.fence` as a relationship partner for `x_req_o.fence`, yet the digest records `a_req_i.fence` as never considered in **3 of 3 runs**.

### c. Reported elements absent from the expert reference list

| Assigned role | Elements with `verified` citations | Elements with `occurrence only` citations |
|---|---|---|
| `stores` | `sel_q`, `locked`, `sc_fail`, `keeper.busy`, `keeper.lock`, `arbiter` | — |
| `computes` | `state_nxt`, `locked_nxt`, `int_rsp`, `rvso` | — |
| `sets` | `req_i.addr` | `a_req_i`, `b_req_i`, `req_i` |
| `exit port` | `a_req_o`, `x_req_o.addr`, `x_req_o.data`, `x_req_o.rw`, `x_req_o.lock`, `x_req_o.fence`, `x_req_o.stb`, `a_rsp_o.data`, `a_rsp_o.ack`, `a_rsp_o.err`, `b_rsp_o.data`, `b_rsp_o.ack`, `b_rsp_o.err`, `sys_req_o.data` | `x_req_o`, `rsp_o`, `sys_req_o`, `core_rsp_o` |

The additional elements therefore include both verified map relationships and record-level citations that establish only occurrence.

### d. Citations that do not verify

All **10 of 65** `occurrence only` citations occur in r0:

- **Record names cited against field assignments:** `x_req_o` at lines 140 and 158; `a_req_i` at lines 140 and 111; `b_req_i` at line 140; `req_i` at line 356; `rsp_o` at line 400; and `core_rsp_o` at line 964.
- **Relationship direction for `port_sel`:** r0 cited `port_sel GATES req_i.addr` at line 356 with status `occurrence only`. In contrast, r2’s `port_sel GATED_BY req_i.addr` citation verified.
- **AMO delivery mismatch:** r0 claimed `sys_req_o DERIVES_FROM alu_res` but cited line 812, which assigns `sys_req_o.addr <= core_req_i.addr`. r1 instead cited `sys_req_o.data DERIVES_FROM alu_res` at line 813, which verified.

The per-run citation results were **13 of 23 verified** in r0, **25 of 25** in r1, and **17 of 17** in r2.

### e. Run-to-run instability

- **Reported in 3 of 3 runs:** `alu_res`, `keeper.err`, `locked`, `locked_nxt`, `sel_q`, `state`.
- **Reported in 2 of 3 runs:** `a_req_o`, `arbiter`, `keeper.busy`, `keeper.lock`, `port_sel`, `sc_fail`, `sel`, `stb`.
- Every other reported element appeared in **1 of 3 runs**.

The emphasis changed alongside coverage: r1 reported detailed request/response output fields, while r2 uniquely reported `int_rsp`, `rvso`, `keeper.cnt`, and `keeper.halt`. Security answers also changed: address-decode availability moved from `no` in r0/r1 to `yes-rtl` in r2, while confidentiality moved from `yes-assumed` to `no`; store-conditional availability changed from `no` in r0 to `yes-rtl` in r2. Timeout-related concepts selected `Availability` in r0 but `Integrity` in r1/r2.

**Interpretation:** Agreement about module purpose does not translate into a reproducible element inventory or consistent security classification.

## 4. Verdict

**Interpretation:** The reasoning gets the broad functional account and many state/dataflow relationships right, supported by agreement in **3 of 3 runs** and **55 of 65** verified citations.  
**Interpretation:** The main blind spot is inconsistent element-level coverage: `a_req`, `b_req`, `keeper.halt`, and `keeper.cnt` each appear in only **1 of 3 runs**, despite appearing in concept text elsewhere.  
**Interpretation:** Trust would improve through element-by-element reconciliation against the relationship map, explicit dispositions for omissions, exact field-and-edge citation validation, and separate treatment of assumed versus RTL-supported security claims.