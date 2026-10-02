# Cross-module synthesis

**Scope:** The 15 module summaries each cover three runs. Several explicitly identify version `m7e194es0ist2`, while the behaviour table ends at `m7e194es0ist`. Module-summary totals and behaviour-table totals are therefore kept separate. Historical comparisons below use only the behaviour table.

## 1. How the executor reasons now

Across the supplied module summaries:

- **15/15 modules:** the executor agrees on the broad module function in **3/3 runs**.
- **15/15 modules:** it describes functional flows, groups values into concepts, assesses security questions, and assigns element roles using relationship-map evidence.
- **15/15 modules:** all structured flow `path` fields are null. Influence points, hypotheses, and exclusions are also empty in **3/3 runs**.
- Across **307 concepts**, objectives are **303 `Integrity`** and **4 `Availability`**. Eleven modules use only `Integrity`; `neorv32_bus`, `neorv32_spi`, `neorv32_trng`, and `neorv32_uart` each have one `Availability` concept.
- Map evidence includes `CLOCKED_BY` for storage, derivation and propagation relationships for values, gating and selection relationships for controls, and `CONNECTS` for interfaces. The module totals contain **706 verified citations out of 873**.

**Interpretation:** The executor’s current reasoning is primarily a functional narrative followed by value selection, security classification, and role/citation assignment—not a completed element-by-element traversal. Its descriptions frequently recognize dependencies that never become explicitly considered or reported elements.

### Changes recorded in the behaviour table

All four versions have three runs.

| Version | P | R | Emitted/run | Concepts with questions | Concepts whose reasoning cites a map fact |
|---|---:|---:|---:|---:|---:|
| `m7e194es0ism` | 0.3439 | 0.8468 | 273.33 | 0 | 0 |
| `m7e194es0ismr` | 0.3528 | 0.7778 | 244.67 | 0 | 0 |
| `m7e194es0ismq` | 0.3521 | 0.7538 | 237.67 | 331 | 0 |
| `m7e194es0ist` | 0.3589 | 0.6907 | 213.67 | 276 | 276 |

**Relationship-map use:**

- The first three versions record **0 references**, **0 verified citations**, and **0 concepts citing a map fact**.
- `m7e194es0ist` records map facts in **276/276 concepts**, **771 references**, **626 verified citations**, and **262 concepts with a verified citation**.
- It also records **364 influence points**, **65 hypotheses**, and **440 exclusions**. Earlier versions have zero influence points and hypotheses; exclusions are **0**, **0**, and **22**, respectively.

These are changes in *recorded evidence use*, not evidence about unrecorded internal reasoning.

**Four-security-question use:**

| Version | Answers | Negative answers | Yes: confidentiality | Yes: integrity | Yes: availability | Yes: undermined behavior |
|---|---:|---:|---:|---:|---:|---:|
| `m7e194es0ismq` | 1,324 | 722 | 0 | 327 | 199 | 76 |
| `m7e194es0ist` | 1,104 | 520 | 0 | 274 | 271 | 39 |

The first two versions record no question answers. Both question-bearing versions record four answers per concept, and every version records **0 concepts with all four answers yes**.

Selected objectives remain concentrated in `Integrity`: the `Integrity`/`Availability` counts are **341/8**, **371/6**, **327/4**, and **272/4** across the four versions.

The table’s final version has the highest P, lowest R, and fewest emissions per run. **Interpretation:** The table does not establish that introducing map citations or changing the questions caused those metric changes.

The behaviour table does not distinguish `yes-assumed` from `yes-rtl`; the distinctions below come from the module summaries only.

## 2. Recurring blind spots, most frequent first

Frequency here means **modules affected**. Categories overlap.

### 2.1 Narrative coverage without complete element accounting — 15/15 modules

Every module has null flow paths and empty influence-point, hypothesis, and exclusion collections. Every module also has reference omissions, flow-graph consideration gaps, or both.

The following audit gives the per-module counts used throughout this section:

- **Reference misses:** reference-entry/run instances, split between concept-text-only and nowhere.
- **Never considered:** flow-graph-element/run instances.
- **Citations:** citation instances; **V** = `verified`, **O** = `occurrence only`, **U** = `edge, role unfit`.

| Module | Reference misses: text / nowhere | Never considered | Citations: V / O / U |
|---|---:|---:|---:|
| `neorv32_bus` | 11 / 0 | 88 | 55 / 10 / 0 |
| `neorv32_cache` | 6 / 10 | 65 | 37 / 6 / 7 |
| `neorv32_cpu` | 5 / 16 | 0 | 20 / 0 / 21 |
| `neorv32_cpu_cp_cfu` | 1 / 6 | 3 | 51 / 0 / 0 |
| `neorv32_cpu_cp_muldiv` | 5 / 0 | 27 | 48 / 0 / 0 |
| `neorv32_cpu_pmp` | 2 / 0 | 22 | 57 / 1 / 0 |
| `neorv32_debug_dtm` | 2 / 4 | 23 | 57 / 1 / 4 |
| `neorv32_hwspinlock` | 0 / 0 | 9 | 6 / 11 / 0 |
| `neorv32_imem` | 0 / 0 | 12 | 32 / 21 / 0 |
| `neorv32_spi` | 3 / 1 | 32 | 77 / 2 / 12 |
| `neorv32_sys` | 0 / 0 | 1 | 45 / 0 / 0 |
| `neorv32_trng` | 2 / 4 | 32 | 32 / 5 / 5 |
| `neorv32_twi` | 3 / 0 | 32 | 61 / 28 / 7 |
| `neorv32_uart` | 6 / 2 | 41 | 81 / 9 / 5 |
| `neorv32_wdt` | 2 / 0 | 16 | 47 / 10 / 2 |
| **Total** | **48 / 43** | **403** | **706 / 104 / 63** |

The two coverage audits are distinct and must not be added together:

- **12/15 modules** have missed reference entries: **91 instances**, comprising **48 text-only** and **43 nowhere**.
- **14/15 modules** have flow-graph consideration gaps: **403 instances**. `neorv32_cpu` has none in that audit but still has **21 reference-miss instances**.
- `neorv32_hwspinlock`, `neorv32_imem`, and `neorv32_sys` have no reference misses, but still have **9**, **12**, and **1** flow-graph consideration gaps.

Examples show both textual awareness without reporting and complete absence:

- `neorv32_twi`: `twi_sda_i` remains concept-text-only in **3/3 runs**.
- `neorv32_cpu_cp_muldiv`: `rs1_i`, `rs2_i`, `mul.start`, `div.start`, and `valid_o` are text-only in r2.
- `neorv32_cpu_cp_cfu`: `rs3_i` and `active_i` are nowhere in **3/3 runs each**.
- `neorv32_cache`: `ctrl.buf_sync`, `cache_o.cmd_dir`, and `inval_i` are nowhere in **3/3 runs each**.
- `neorv32_cpu`: `lsu_err`, `firq_i`, `dbi_i`, and `lsu_mar` are nowhere in **3/3 runs each**.

**Interpretation:** Mentioning an element in prose or citing it as another element’s relationship partner is not functioning as a reliable trigger for explicit consideration.

### 2.2 Assumed confidentiality and inconsistent security decisions — 15/15 modules

Every module has positive confidentiality answers, but **all 215 positive confidentiality answers are `yes-assumed`**; none is `yes-rtl`.

| Module | Concepts | Confidentiality `yes-assumed` | Completely unanswered question sets |
|---|---:|---:|---:|
| `neorv32_bus` | 24 | 23 | 0 |
| `neorv32_cache` | 16 | 15 | 0 |
| `neorv32_cpu` | 21 | 6 | 3 |
| `neorv32_cpu_cp_cfu` | 19 | 14 | 0 |
| `neorv32_cpu_cp_muldiv` | 16 | 13 | 0 |
| `neorv32_cpu_pmp` | 21 | 16 | 5 |
| `neorv32_debug_dtm` | 23 | 17 | 0 |
| `neorv32_hwspinlock` | 8 | 2 | 6 |
| `neorv32_imem` | 12 | 4 | 4 |
| `neorv32_spi` | 24 | 22 | 2 |
| `neorv32_sys` | 16 | 11 | 5 |
| `neorv32_trng` | 18 | 14 | 0 |
| `neorv32_twi` | 27 | 18 | 1 |
| `neorv32_uart` | 27 | 23 | 0 |
| `neorv32_wdt` | 35 | 17 | 14 |
| **Total** | **307** | **215** | **40** |

The cited support for confidentiality includes readback, output assignments, internal dependencies, and control/status exposure.

**Interpretation:** These citations establish visibility or functional dependencies, but not independently a confidentiality requirement. The explicit assumption label should be preserved rather than promoted to an RTL-established security conclusion.

Other recorded inconsistencies include:

- **Eight concepts in six modules** retain an `Integrity` objective despite answering integrity `no`: `neorv32_cache` **1**, `neorv32_cpu_cp_muldiv` **1**, `neorv32_imem` **1**, `neorv32_spi` **1**, `neorv32_trng` **2**, and `neorv32_twi` **2**.
- `neorv32_cpu`: `irq_machine` availability changes from `yes-rtl` to `no` to `unknown`.
- `neorv32_imem`: acknowledgement integrity changes from `no` to `yes-rtl`.
- `neorv32_sys`: `xrstn_wdt_o` and `xrstn_ocd_o` availability changes from `no` in run 0 to `yes-rtl` in run 2.
- `neorv32_uart`: negative availability answers for configuration values cite configuration writes.

**Interpretation:** Functional citation verification and security-answer justification require separate checks; neither a normal assignment nor an exposure path settles the security question by itself.

### 2.3 Unstable reported inventories — 14/15 modules

**Affected modules:** every module in the audit table except `neorv32_imem`.

The summaries show variation in reported membership even when module-purpose descriptions agree:

- `neorv32_cache`: only **1/33** reported elements, `ctrl`, appears in all three runs; **21/33** appear in only one.
- `neorv32_debug_dtm`: **11/25** appear in all three runs, **8/25** in two, and **6/25** in one.
- `neorv32_twi`: **13/30** appear in all three runs, **6/30** in two, and **11/30** in one.
- `neorv32_cpu_cp_cfu`: **15/17** appear in all three runs; `csr_we_i` appears in two and `rtype_i` in one.
- `neorv32_wdt`: **13/20** appear in all three runs.
- The exception, `neorv32_imem`, reports the same **10/10 elements** in all three runs, although its question answers and citation support still vary.

Parent/field granularity also changes—for example, `dmi_req_o` versus its fields in `neorv32_debug_dtm`, and `bus_req_i`/`bus_rsp_o` versus individual fields in `neorv32_uart`.

**Interpretation:** Agreement on module purpose is substantially more reproducible than the resulting element inventory.

### 2.4 Citations that do not support the exact element, relationship, or role — 12/15 modules

The affected modules are the audit-table rows with nonzero **O** or **U**:

`neorv32_bus`, `neorv32_cache`, `neorv32_cpu`, `neorv32_cpu_pmp`, `neorv32_debug_dtm`, `neorv32_hwspinlock`, `neorv32_imem`, `neorv32_spi`, `neorv32_trng`, `neorv32_twi`, `neorv32_uart`, and `neorv32_wdt`.

There are **167 non-verifying citation instances**:

- **104 `occurrence only` instances in 11 modules**, with per-module counts in column O.
- **63 `edge, role unfit` instances in 8 modules**, with per-module counts in column U.

Recurring mechanisms are:

- **Aggregate names cited against field assignments.** Examples include `bus_req_i` and `bus_rsp_o` in `neorv32_imem`, accounting for **20/21** non-verifying citations there; corresponding bus-record citations account for **27/28** occurrence-only citations in `neorv32_twi`.
- **Real edges assigned unsupported roles.** `neorv32_cpu` has **13** `computes` citations using `CONNECTS` and **8** `sets` citations using `SOURCES`, all role-unfit.
- **Wrong direction or partner.** In `neorv32_bus`, `port_sel GATES req_i.addr` is occurrence-only, whereas `port_sel GATED_BY req_i.addr` verifies. The claimed `sys_req_o DERIVES_FROM alu_res` citation points to an address assignment; `sys_req_o.data DERIVES_FROM alu_res` verifies in another run.

These failures are distinct from an element being absent from the RTL or map.

### 2.5 Missing four-question assessments — 8/15 modules

The unanswered sets are:

- `neorv32_cpu`: **3/21 concepts**
- `neorv32_cpu_pmp`: **5/21**
- `neorv32_hwspinlock`: **6/8**
- `neorv32_imem`: **4/12**
- `neorv32_spi`: **2/24**
- `neorv32_sys`: **5/16**
- `neorv32_twi`: **1/27**
- `neorv32_wdt`: **14/35**

That is **40/307 concepts** with all four answers absent. Entire runs omit the answers in `neorv32_imem`, `neorv32_sys`, and `neorv32_wdt`; `neorv32_hwspinlock` records answers in only one run.

Absent answers are not negative answers. The summaries also distinguish `unknown` from `no`.

## 3. Reasoning that is reliable, with evidence

**Interpretation:** The strongest supported reasoning is the reconstruction of broad functional behaviour and specific role-compatible relationships—not completeness of the inventory or correctness of every security answer.

| Supported reasoning | Evidence |
|---|---|
| Broad functional reconstruction | All **15 modules** agree on their functional account in **3/3 runs**. |
| Key storage, operand capture, computation, and result delivery in `neorv32_cpu_cp_cfu` | **51/51 citations verified**; `xtea.done`, `xtea.opa`, `xtea.opb`, `xtea.sum`, and `xtea.res` are reported in **3/3 runs**. |
| Arithmetic command, sequencing, and output relationships in `neorv32_cpu_cp_muldiv` | **48/48 citations verified**; the stable core includes `ctrl.state`, `ctrl.cnt`, `mul.prod`, `div.res`, and `res_o` in **3/3 runs**. |
| Reset and clock-enable relationships in `neorv32_sys` | **45/45 citations verified**; `enable_i` and `clk_en_o` are reported with verified roles in **3/3 runs**. |
| Specific integration-level derivations in `neorv32_cpu` | `DERIVES_FROM` citations for `rf_wdata`, `irq_machine`, and `xcsr_res` verify in **3/3 runs**, despite the module’s other role-fit failures. |
| Storage and address selection in `neorv32_hwspinlock` | `lock_q` as `stores` and `sel` as `computes` are stable in **3/3 runs**, supported by **6 verified citations**. |

The distinction between correctness of reported relationships and completeness is directly visible in `neorv32_cache`: r2 has **24/24 verified citations** but reports **0/6 reference entries**.

Reference membership and citation verification also remain separate: many elements outside the expert reference have verified citations. The reference is used here to locate omissions, not as a whitelist.

## 4. Three changes to remove the main blind spots

1. **Interpretation: Require a canonical, map-driven coverage ledger and populated flow paths — addresses blind spots 2.1 and 2.3.**  
   Enumerate exact elements, including fields and relationship partners, before concept grouping. Give each an explicit disposition: reported element, influence point, hypothesis, or exclusion with a reason. Reconcile prose mentions and cited partners against that ledger, and preserve parent/field distinctions. Use stable element identities and ordering so regrouping concepts does not silently change membership. Use the expert reference as an omission check, not as the candidate whitelist.

2. **Interpretation: Validate the complete citation-and-role tuple before accepting evidence — addresses blind spot 2.4.**  
   Check the exact element, relationship type, direction, partner, cited statement, and assigned role together. Reject aggregate substitutions where only field-level evidence exists, and distinguish occurrence-only failures from real edges with unsuitable roles. Retain unresolved elements in the coverage ledger rather than silently dropping them when citation validation fails.

3. **Interpretation: Gate final output on complete, evidence-typed security assessments — addresses blind spots 2.2 and 2.5.**  
   Require all four answers for every concept, preserving `yes-assumed`, `yes-rtl`, `no`, and `unknown` as distinct states. Require the security premise behind assumptions and an explicit rationale for negative answers; functional exposure alone should not establish confidentiality. Select or reconcile the objective after answering the questions, flagging cases such as `Integrity` paired with integrity `no`. Reconcile conflicting answers against the same configuration and evidence before accepting the final assessment.