# 1. What the executor concluded

In **3 of 3 runs**, the executor described `neorv32_cache` as handling host memory requests through address decoding and cache lookup, returning cached data on hits or using the system bus for forwarding and cache-line downloads/fills. The runs agree on that functional account; their differences concern which values and elements they report.

This summary concerns version `m7e194es0ist2`.

# 2. How it reasoned

## Flows and values examined

The shared flows in **3 of 3 runs** were request ingress/buffering, lookup, direct forwarding, download/fill, and reset. Explicit `read out` flows appeared in **2 of 3 runs** (`r0`, `r1`); `report` and `lock` flows appeared in **2 of 3 runs** (`r1`, `r2`). Every recorded flow `path` was null.

The concepts changed between runs:
- `r0` separated controller state, host requests, bus requests, cache-memory commands, hit indication, returned data, and download errors.
- `r1` grouped more of this into controller/buffered state and cached contents, alongside hit indication and bus requests.
- `r2` focused on direct bypass, decoded addresses, stored cache contents, download-error reporting, and clear/fence handling.

All concepts had objective `Integrity`—**16 of 16**—including the decoded-address concept whose integrity answer was `no`.

## Question answers

In CIAU order—confidentiality, integrity, availability, undermined behavior—`a` denotes `yes-assumed`, `R` denotes `yes-rtl`, and `n` denotes `no`.

| Pattern | Frequency |
|---|---:|
| `aRRn` | 5 of 16 |
| `aRRR` | 3 of 16 |
| `aann`, `aaRn` | 2 of 16 each |
| `aRnn`, `aaRR`, `anRn`, `nanR` | 1 of 16 each |

The answer distribution and negative-answer contexts were:

- **Confidentiality:** `yes-assumed` in **15 of 16**, `yes-rtl` in **0 of 16**, and `no` in **1 of 16**—the clear/fence concept in `r2`.
- **Integrity:** `yes-rtl` in **9 of 16**, `yes-assumed` in **6 of 16**, and `no` in **1 of 16**—decoded request addresses in `r2`.
- **Availability:** `yes-rtl` in **12 of 16** and `no` in **4 of 16**. The negative answers concerned host request inputs and download errors in `r0`, and bypass and clear/fence handling in `r2`.
- **Undermined behavior:** `yes-rtl` in **5 of 16** and `no` in **11 of 16**. Positive answers concerned bus requests in `r0` and `r1`, returned data/cached contents in `r0` and `r1`, and clear/fence handling in `r2`.

**Interpretation:** The confidentiality answers should not be treated as RTL-established properties: almost all were explicitly assumptions. The negative answers also need review alongside their cited statements, particularly where another run answered the corresponding concern differently.

## Roles and map evidence

The executor assigned `stores`, `computes`, `sets`, and `exit port` roles. Its verified evidence included:
- `CLOCKED_BY` for `ctrl` and memory storage;
- `SELECTED_BY` for state-dependent computations and outputs;
- `SOURCES` and `DERIVES_FROM` for address derivation;
- `GATES` and `GATED_BY` for request/error controls;
- `COPIES` for request and response routing.

Across citation instances, **37 of 50** were `verified`, **6 of 50** were `occurrence only`, and **7 of 50** were `edge, role unfit`. The role-unfit citations used `CONNECTS` edges.

# 3. Blind spots

The expert reference list is used here only to locate blind spots; absence from that list does not classify a reported element as incorrect.

## a. Missed reference entries and where they ended up

Only `cache_i.sta_hit` was reported from the reference list, in **2 of 3 runs**. Using the digest’s missed-entry classifications:

| Reference entry | Reporting and disposition |
|---|---|
| `ctrl.buf_sync` | Reported in **0 of 3 runs**; classified as nowhere in the output in **3 of 3 runs**. |
| `cache_o.cmd_dir` | Reported in **0 of 3 runs**; nowhere in **3 of 3 runs**. |
| `inval_i` | Reported in **0 of 3 runs**; nowhere in **3 of 3 runs**. |
| `we_i` | Reported in **0 of 3 runs**; concept text only in **3 of 3 runs**. |
| `addr_i` | Reported in **0 of 3 runs**; concept text only in **2 of 3 runs** (`r0`, `r1`), nowhere in **1 of 3 runs** (`r2`). |
| `cache_i.sta_hit` | Reported in **2 of 3 runs** (`r0`, `r1`), both with `edge, role unfit` citations; concept text only in **1 of 3 runs** (`r2`). |

Influence points, hypotheses, and exclusions were empty in **3 of 3 runs**. Thus, no exclusion reasons were supplied, and none of these misses was classified as flow-path-only.

## b. Flow-graph elements never considered

The digest’s flow-graph consideration audit marks the following as unconsidered; this classification is distinct from whether an element appears in narrative text.

- **Unconsidered in 3 of 3 runs:** `bus_rsp_i.ack`, `clr_i`, `ctrl.buf_dir`, `ctrl.buf_err`, `ctrl.buf_req`, `ctrl.buf_sync`, `ctrl.state`, `host_req_i.rw`, `host_req_i.stb`, `inv_i`, `new_i`, `rdata_o`, `tag_mem_rd`, `valid_mem_rd`, `we_i`.
- **Unconsidered in 2 of 3 runs:** `bus_req_o.addr`, `bus_rsp_i.err`, `data_mem_b0`, `data_mem_b1`, `data_mem_b2`, `data_mem_b3`, `host_req_i.amo`, `host_req_i.debug`, `host_req_i.fence`, `tag_mem`.

**Interpretation:** Broad descriptions of buffering, hit detection, and refill do not provide complete element-level coverage of those flows.

## c. Reported elements not listed by the reference

The following groups preserve the executor’s assigned roles. Elements can appear under different roles across runs.

| Role | Citations that verify | Citations that do not verify |
|---|---|---|
| `stores` | `ctrl`, `valid_mem`, `tag_mem`, `data_mem_b0`, `data_mem_b1`, `data_mem_b2`, `data_mem_b3` | None recorded for this role. |
| `computes` | `ctrl_nxt.state`, `cache_o.cmd_new`, `cache_o.cmd_clr`, `cache_o.cmd_inv`, `cache_o.addr`, `cache_o.data`, `cache_o.we`, `ctrl_nxt.buf_err`, `ctrl_nxt.buf_dir`, `ctrl_nxt.tag` | `cache_i.data`: `edge, role unfit`. |
| `sets` | `host_req_i.addr`, `host_req_i.amo`, `host_req_i.debug`, `bus_rsp_i.err`, `host_req_i.fence`, `cache_o.cmd_clr` | `host_req_i`, `bus_rsp_i`: `occurrence only`; `cache_o.addr`, `cache_o.data`, `cache_o.we`: `edge, role unfit`. |
| `exit port` | `bus_req_o` in `r0`; `bus_req_o.addr`, `bus_req_o.fence`, `host_rsp_o.data`, `host_rsp_o.err`, `host_rsp_o.ack` in `r2` | `host_rsp_o`: `occurrence only`; `bus_req_o` in `r1`: `occurrence only`. |

## d. Citations that do not verify

The **6 of 50** `occurrence only` citations concern:
- `host_req_i` and `host_rsp_o` in **2 of 3 runs** (`r0`, `r1`);
- `bus_rsp_i` and `bus_req_o` in **1 of 3 runs** (`r1`).

Those citations name aggregate records while their cited statements use fields: `host_req_i.addr`, `host_req_i.stb`, `host_rsp_o.data`, `bus_rsp_i.ack`, or `bus_req_o.addr`.

The **7 of 50** `edge, role unfit` citations concern:
- `cache_i.sta_hit` and `cache_i.data`, assigned `computes` in **2 of 3 runs** (`r0`, `r1`);
- `cache_o.addr`, `cache_o.data`, and `cache_o.we`, assigned `sets` in **1 of 3 runs** (`r1`).

Their cited relationships are `CONNECTS` edges to ports of `neorv32_cache_memory_inst`.

**Interpretation:** These failures distinguish two checks the executor did not consistently satisfy: citing the exact element involved in the relationship, and selecting a role supported by the relationship type.

## e. Run-to-run instability

Only `ctrl` was reported in **3 of 3 runs**. Of the reported elements, **11 of 33** appeared in **2 of 3 runs**, and **21 of 33** appeared in **1 of 3 runs**.

The changes affected more than coverage:
- `cache_o.cmd_clr` changed from `computes` in `r0` to `sets` in `r2`, with both citations verified.
- `cache_o.addr`, `cache_o.data`, and `cache_o.we` changed from verified `computes` citations in `r0` to role-unfit `sets` citations in `r1`.
- `bus_req_o` changed from `verified` in `r0` to `occurrence only` in `r1`.
- Cached contents received `yes-rtl` for undermined behavior in `r1`, but `no` in `r2`.
- Download-error availability changed from `no` in `r0` to `yes-rtl` in `r2`.

Citation verification also varied: **11 of 15** in `r0`, **2 of 11** in `r1`, and **24 of 24** in `r2`. Despite that complete citation verification in `r2`, it reported **0 of 6** reference entries.

**Interpretation:** Better citation verification in a run does not, by itself, demonstrate more complete identification.

# 4. Verdict

The executor gives a consistent host/cache/bus account in **3 of 3 runs**, supported by **37 of 50** verified role citations.  
**Interpretation:** Its main blind spot is incomplete element-level coverage of control and memory interfaces, compounded by changing roles and question answers.  
**Interpretation:** Require an element-level flow traversal, exact-element and role-compatible map citations, and explicit justification of assumed and negative answers before trusting the identification as complete.