# Asset / non-asset element dossier

Every element of the scored modules, with the four fields the RTL parser wrote for it. Section A is the elements the manual ground truth calls assets. Section B is everything else in the same modules.

- parse: `parsed_v3_tuning18/` (the generation that fed `v2p3c1`)
- reference: `ground_truth/manual_gt_neorv32.json`
- LAsset's own two lists are shown per element as `[paper]` / `[paper-refined]` when they also name it, so disagreement between the three references is visible.
- Matching is the scorer's rule: exact name, else a record field against its base in either direction. Every non-exact match says so.

| module | elements parsed | reference rows | elements matched | non-assets |
|---|---:|---:|---:|---:|
| bus | 870 | 10 | 11 | 859 |
| cache | 86 | 6 | 5 | 81 |
| cpu | 115 | 14 | 14 | 101 |
| cpu_cp_cfu | 29 | 11 | 11 | 18 |
| cpu_cp_muldiv | 70 | 12 | 12 | 58 |
| cpu_pmp | 62 | 6 | 6 | 56 |
| debug_dtm | 42 | 5 | 5 | 37 |
| hwspinlock | 21 | 2 | 2 | 19 |
| imem | 27 | 3 | 3 | 24 |
| spi | 66 | 8 | 8 | 58 |
| sys | 17 | 2 | 2 | 15 |
| trng | 56 | 7 | 7 | 49 |
| twi | 65 | 6 | 6 | 59 |
| uart | 76 | 10 | 10 | 66 |
| wdt | 39 | 8 | 8 | 31 |
| **total** | **1641** | **110** | **110** | **1531** |

So 110 of 1641 parsed elements (6.7%) are assets. That ratio is the base rate any generation prompt is working against.

**One reference row can never be matched.** `neorv32_cache:inval_i` is listed as an asset by all three references, but no port of that name exists in this version of the RTL — the equivalent ports here are `clr_i` and `inv_i`. Recall is therefore capped at 109/110 = 0.991, and the miss is an artefact of a reference built against a different NEORV32 revision, not a parser failure.

## What separates Section A from Section B

Every feature below is something the parser itself wrote. The first column is how often it appears on an asset, the second how often on a non-asset. **Lift** is the ratio. A lift of 1 means the parser writes it just as readily for things that are not assets, so reading it cannot help the next stage.

The last column is the honest one: if the asset stage emitted *every* element carrying that feature and nothing else, this is the precision it would get. The base rate is 6.7%, so even a lift of 4 only reaches about 23%.

| what the parser wrote | on assets | on non-assets | lift | precision if used alone | assets covered |
|---|---:|---:|---:|---:|---:|
| text says something outside can write it | 7.3% | 1.8% | **4.12** | 22.9% | 8 / 110 |
| three or more relationship edges | 20.9% | 5.4% | **3.90** | 21.9% | 23 / 110 |
| a governing edge (GATES/SELECTS/CONSTRAINS/OVERRIDES) | 37.3% | 9.7% | **3.83** | 21.6% | 41 / 110 |
| CAPTURES — holds a value across cycles | 35.5% | 10.5% | **3.37** | 19.5% | 39 / 110 |
| role words: select / choose / arbitrate | 13.6% | 5.4% | **2.52** | 15.3% | 15 / 110 |
| it is an internal signal | 57.3% | 24.2% | **2.37** | 14.5% | 63 / 110 |
| role words: configuration / control | 21.8% | 11.4% | **1.91** | 12.1% | 24 / 110 |
| role words: status / flag | 16.4% | 15.7% | **1.04** | 7.0% | 18 / 110 |
| role words: data / payload | 10.0% | 11.2% | **0.89** | 6.0% | 11 / 110 |
| role words: clock / reset / handshake | 11.8% | 13.8% | **0.86** | 5.8% | 13 / 110 |
| it is a port | 42.7% | 75.8% | **0.56** | 3.9% | 47 / 110 |
| its name is dotted (a record field) | 27.3% | 78.4% | **0.35** | 2.4% | 30 / 110 |
| no edges at all, or ISOLATED | 1.8% | 8.4% | **0.22** | 1.5% | 2 / 110 |

**Reading of the table.** The strongest honest signal in the whole parse is a governing edge: lift 3.8, and it covers 41 of the 110 assets. Used alone it would give about 22% precision. Nothing else beats it while also covering a useful share of the assets. Three features actively point the *wrong* way — being a port, having a dotted name, and having no edges — which is consistent with the reference naming ports whole and treating pass-through fields as not-assets.

**The `role` field carries almost no reusable vocabulary.** Across the 110 assets the parser wrote 253 role phrases, of which 223 are distinct — 88% appear exactly once. Across the non-assets it wrote 3477 phrases with 1608 distinct. So `role` is close to free prose. It is readable by a human and it is faithful to the RTL, but there is no repeated wording for the asset stage to key on. That is a direct consequence of asking for open description instead of a closed vocabulary, and it is the trade that decision was making.

**Relationship edges do carry signal, and it is concentrated.** Share of all edges written, assets against non-assets: SELECTS 3.6% / 1.2% (lift 2.99), GATES 13.5% / 5.3% (2.55), CONSTRAINS 2.7% / 1.1% (2.43), CAPTURES 17.9% / 7.8% (2.30), DERIVES_FROM 15.7% / 7.7% (2.03). Pointing away: EXPORTS 4.5% / 19.2% (0.23), CARRIES 8.5% / 20.1% (0.42), SEQUENCES 0.4% / 3.3% (0.13). **AGGREGATES never once appears on an asset** — a bare record name is not what the references call an asset.

**Why the asset stage still over-emits.** The features that separate best are the ones it already over-weights. Connectedness (three or more edges) has lift 3.9 but produced a 5.25× emission lift in the measured runs, while governance — the better security signal — has lift 3.8 and produced only 3.0×. The stage is reading the parse; it is ranking connectedness above governance.

---

# Section A — elements the ground truth calls assets

## neorv32_bus

### `a_req` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** carry CPU addresses/data/control into the fabric; altering them writes or reads the wrong location — that’s why integrity is critical

> **CWE:** 1220, 1242, 1311

  (signal, `std_ulogic`, entity `neorv32_bus_switch`)
  - **functionality** — Latches whether A has an outstanding request across cycles (captured from a_req_i.stb or retained); the FSM tests a_req to decide grants when external stb is absent.
  - **roles** — latched request flag; holds A request across cycles; gates FSM selection
  - **relationships** — **CAPTURES** → a_req_i.stb; **GATES** → state_nxt, sel, stb
  - **evidence** — a_req <= a_req or a_req_i.stb in arbiter_sync; a_req tested in arbiter_fsm conditions to choose state_nxt and sel.

### `alu_res` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The 'AMO ALU Result' is critical for ensuring the integrity of atomic operations in the 'neorv32' design. Attacks on this result could lead to incorrect data being written back to memory, affecting the correctness of atomic operations.

> **CWE:** 1319

  (signal, `std_ulogic_vector(31 downto 0)`, entity `neorv32_bus_amo_rmw`)
  - **functionality** — Computes and stores the AMO ALU result on the clock edge from functions of arbiter.rdata, arbiter.wdata and cmp_res according to arbiter.cmd; drives sys_req_o.data during write phases.
  - **roles** — ALU result holder; provides write-back data
  - **relationships** — **DERIVES_FROM** → arbiter.rdata, arbiter.wdata, cmp_res
  - **evidence** — amo_alu process (rising_edge) assigns alu_res using case on arbiter.cmd and expressions with arbiter.rdata/wdata or cmp_res

### `b_req` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** carry CPU addresses/data/control into the fabric; altering them writes or reads the wrong location — that’s why integrity is critical

> **CWE:** 1220, 1242, 1311

  (signal, `std_ulogic`, entity `neorv32_bus_switch`)
  - **functionality** — Latches whether B has an outstanding request across cycles (captured from b_req_i.stb or retained); the FSM tests b_req to decide grants when external stb is absent.
  - **roles** — latched request flag; holds B request across cycles; gates FSM selection
  - **relationships** — **CAPTURES** → b_req_i.stb; **GATES** → state_nxt, sel, stb
  - **evidence** — b_req <= b_req or b_req_i.stb in arbiter_sync; b_req tested in arbiter_fsm conditions to choose state_nxt and sel.

### `keeper.cnt` — Availability  _(manual GT only)_

> **why the reference lists it:** The attack on these registers significantly impacts the 'neorv32_bus_gateway' entity by compromising its ability to manage bus access timeouts. This can lead to system-wide availability issues in the 'neorv32' design, as the bus infrastructure is critical for communication between different components. Disrupting this functionality can halt security-critical functions and create opportunities for further exploitation.

> **CWE:** 1320, 1347

  (signal, `std_ulogic_vector(index_size_f(TIMEOUT) downto 0)`, entity `neorv32_bus_gateway`)
  - **functionality** — Counts cycles while busy by incrementing itself each clock; its top bit is tested for timeout and used to set keeper.err.
  - **roles** — holds timeout counter; counts while busy; gates timeout error
  - **relationships** — **CAPTURES** → keeper.cnt; **CONSTRAINS** → keeper.err
  - **evidence** — keeper.cnt <= std_ulogic_vector(unsigned(keeper.cnt) + 1) in bus_monitor; keeper.cnt(...) tested to set keeper.err

### `keeper.err` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** The attack on these registers significantly impacts the 'neorv32_bus_gateway' entity by compromising its ability to manage bus access timeouts. This can lead to system-wide availability issues in the 'neorv32' design, as the bus infrastructure is critical for communication between different components. Disrupting this functionality can halt security-critical functions and create opportunities for further exploitation.

> **CWE:** 1320, 1347

  (signal, `std_ulogic`, entity `neorv32_bus_gateway`)
  - **functionality** — Captured error flag set on timeout and cleared each cycle; is ORed into rsp_o.ack and rsp_o.err to report error externally.
  - **roles** — holds timeout/error state; reports error to outputs
  - **relationships** — **SOURCES** → rsp_o
  - **evidence** — keeper.err set in bus_monitor on timeout; rsp_o.ack/err include keeper.err in OR

### `keeper.halt` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** The attack on these registers significantly impacts the 'neorv32_bus_gateway' entity by compromising its ability to manage bus access timeouts. This can lead to system-wide availability issues in the 'neorv32' design, as the bus infrastructure is critical for communication between different components. Disrupting this functionality can halt security-critical functions and create opportunities for further exploitation.

> **CWE:** 1320, 1347

  (signal, `std_ulogic`, entity `neorv32_bus_gateway`)
  - **functionality** — Captures the MSB of port_sel each clock to indicate the selected port halt condition and is tested before declaring timeout.
  - **roles** — holds halt state; affects timeout decision
  - **relationships** — **CAPTURES** → port_sel; **CONSTRAINS** → keeper.err
  - **evidence** — keeper.halt <= port_sel(port_sel'left) in bus_monitor; (keeper.halt = '0') used with keeper.cnt top bit before setting keeper.err

### `port_sel` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** handshake/response lines must toggle to finish every transaction; if they hang, masters stall — that’s why availability is critical

> **CWE:** 1245, 1261, 1292

  (signal, `std_ulogic_vector(3 downto 0)`, entity `neorv32_bus_gateway`)
  - **functionality** — Holds the per-port decode bits computed from address comparisons and enable flags; used to mask per-port stb and to derive keeper.halt.
  - **roles** — carries port decode; drives per-port enables; feeds keeper halt
  - **relationships** — **DERIVES_FROM** → req_i.addr; **GATES** → port_req; **SOURCES** → keeper.halt
  - **evidence** — concurrent assignments port_sel(0..3) <= '1' when ...; used in request process and bus_monitor

### `sel` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** handshake/response lines must toggle to finish every transaction; if they hang, masters stall — that’s why availability is critical

> **CWE:** 1245, 1261, 1292

  (signal, `std_ulogic`, entity `neorv32_bus_switch`)
  - **functionality** — Combinationally selects which port (A when '0', B when '1') drives the x_req_o outputs for the current arbitration decision; its value is captured into sel_q on the clock edge.
  - **roles** — selection signal; chooses which port drives x_req_o; feeds response routing
  - **relationships** — **SOURCES** → sel_q; **SELECTS** → x_req_o.addr, x_req_o.amo, x_req_o.amoop, x_req_o.lock, x_req_o.priv, x_req_o.debug, x_req_o.src, x_req_o.rw, x_req_o.data, x_req_o.ben, a_rsp_o.ack, a_rsp_o.err, b_rsp_o.ack, b_rsp_o.err
  - **evidence** — sel assigned in arbiter_fsm; concurrent assignments use sel to choose between a_req_i.* and b_req_i.* and to gate a/b rsp ack/err.

### `state` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The 'Arbiter FSM State' is critical for managing access to the bus in the 'neorv32_bus' entity. An attack on this asset could lead to a denial-of-service condition, impacting the availability of the bus and potentially halting the entire 'neorv32' SoC design.

> **CWE:** 1245, 1247, 1319

  **neorv32_bus_switch · state** (signal, `state_t`)
  - **functionality** — Holds the current FSM state (S_IDLE, S_BUSY_A, S_BUSY_B); used as the case selector in the combinational FSM and is updated on clock from state_nxt to drive arbiter behaviour.
  - **roles** — holds FSM state; selects FSM branch; governs request latches
  - **relationships** — **CAPTURES** → state_nxt; **SELECTS** → state_nxt, sel, stb, locked_nxt; **GATES** → a_req, b_req
  - **evidence** — state assigned in arbiter_sync (state <= state_nxt) and used as case state in arbiter_fsm; state = S_BUSY_* conditions gate a_req/b_req updates.

  **neorv32_bus_amo_rvs · state** (signal, `std_ulogic_vector(1 downto 0)`)
  - **functionality** — Holds the two-bit FSM state across clock edges; the case selection governs which state transitions occur based on core_req_i and rvso, and state(1) is tested elsewhere to gate strobe and sc_fail.
  - **roles** — FSM state register; holds state across cycles; chooses control branches; drives gating of sys_req_o.stb and sc_fail
  - **relationships** — **CAPTURES** → _(none)_; **SELECTS** → state; **SOURCES** → sys_req_o.stb, sc_fail; **GATES** → _(none)_
  - **evidence** — state is assigned inside rvs_control clocked process (case state ... state <= "11"/"00"/"10"); state(1) used in bus_request and sc_result.

### `stb` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** handshake/response lines must toggle to finish every transaction; if they hang, masters stall — that’s why availability is critical

> **CWE:** 1245, 1261, 1292

  (signal, `std_ulogic`, entity `neorv32_bus_switch`)
  - **functionality** — Combinationally carries the strobe to forward to x_req_o.stb; it is driven from FSM decisions and directly from selected port's stb when locked, so it reflects the active forwarded request cycle.
  - **roles** — internal strobe; drives x_req_o.stb; reflects selected port strobe
  - **relationships** — **DERIVES_FROM** → a_req_i.stb, b_req_i.stb; **SOURCES** → x_req_o.stb
  - **evidence** — stb assigned in arbiter_fsm (stb <= '0' default; stb <= a_req_i.stb or b_req_i.stb or '1' in branches); x_req_o.stb <= stb.


## neorv32_cache

### `addr_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** addr_i selects the cache index/tag and therefore the target block/word for every read/write. If it is corrupted or improperly controlled, the cache may return or store data from/to the wrong location, causing silent data corruption or writes into unintended regions.

> **CWE:** 1257, 1260, 1262, 1290, 1292, 1311, 1312, 1316

  (port, `std_ulogic_vector(31 downto 0)`, entity `neorv32_cache_memory`)
  - **functionality** — Supplies the external 32-bit address which is sliced to produce acc_tag, acc_idx and acc_off; those fields drive tag/index/offset logic inside the entity.
  - **roles** — source of tag/index/offset fields; input to address decoding
  - **relationships** — **SOURCES** → acc_tag, acc_idx, acc_off
  - **evidence** — concurrent assignments: acc_tag <= addr_i(...); acc_idx <= addr_i(...); acc_off <= addr_i(...).

### `cache_i.sta_hit` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** The cache_o signal is critical for controlling cache operations. Any unauthorized changes to the control commands or data could disrupt cache functionality, leading to data corruption or incorrect cache behavior. The cache_i signal provides status and data from the cache memory. Ensuring its integrity is vital to prevent incorrect status reporting or data corruption, which could affect subsequent cache operations and system behavior.

> **CWE:** 1242, 1280, 1290, 1189

  (signal, `std_ulogic`, entity `neorv32_cache`)
  - **functionality** — Reflects the cache memory hit output and is tested by the controller to choose hit paths (read return) or miss/download paths.
  - **roles** — hit indication; governs cache hit path
  - **relationships** — **CARRIES** → neorv32_cache_memory_inst.hit_o; **GATES** → ctrl_nxt.state, host_rsp_o.ack
  - **evidence** — cache_i.sta_hit is used in S_LOOKUP condition to choose hit vs miss; port map hit_o => cache_i.sta_hit.

### `cache_o.cmd_dir` — Availability  _(manual GT only)_

> **why the reference lists it:** The cache_o signal is critical for controlling cache operations. Any unauthorized changes to the control commands or data could disrupt cache functionality, leading to data corruption or incorrect cache behavior. The cache_i signal provides status and data from the cache memory. Ensuring its integrity is vital to prevent incorrect status reporting or data corruption, which could affect subsequent cache operations and system behavior.

> **CWE:** 1242, 1280, 1290, 1189

  _matched via record `cache_o` (reference names the field)_

  **neorv32_cache · cache_o** (signal, `cache_o_t`)
  - **functionality** — Aggregates cache commands, address, data and write-enable mask driven by the controller and forwards them to the cache memory instance ports.
  - **roles** — cache command carrier; drives cache memory inputs
  - **relationships** — **SOURCES** → neorv32_cache_memory_inst.clr_i, neorv32_cache_memory_inst.inv_i, neorv32_cache_memory_inst.new_i, neorv32_cache_memory_inst.addr_i, neorv32_cache_memory_inst.we_i, neorv32_cache_memory_inst.wdata_i
  - **evidence** — cache_o.* assigned in ctrl_engine_comb and connected in instance port map.

### `ctrl.buf_sync` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Governs the cache FSM for lookup, miss, fill and eviction; a flip here steers operations to the wrong address or data – that’s why its correctness is vital.

> **CWE:** 1242, 1280, 1290, 1268

  (signal, `std_ulogic`, entity `neorv32_cache`)
  - **functionality** — Latched fence/sync request; when set causes the FSM to go to S_CLEAR to issue a fence/clear operation.
  - **roles** — latched fence flag; triggers cache clear
  - **relationships** — **CAPTURES** → ctrl_nxt.buf_sync; **GATES** → ctrl_nxt.state
  - **evidence** — ctrl_nxt.buf_sync <= ctrl.buf_sync or host_req_i.fence; S_IDLE checks ctrl.buf_sync to go to S_CLEAR.

### `inval_i` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** inval_i invalidates the addressed cache block; if an attacker can assert or glitch it, the cache can be forced to thrash (constant misses/refills) or to drop hot lines, stalling the pipeline and degrading the system into a denial-of-service.

> **CWE:** 1245, 1247, 1276, 1319, 1384

  - **PARSER DID NOT DESCRIBE THIS ELEMENT** — no element of this name or its base exists in the parse. The asset stage never saw it.

### `we_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** we_i is the per-byte write-enable for the cache data array; when asserted, the addressed bytes of the selected line are overwritten. Any unauthorized assertion, masking, or corruption of we_i causes silent data corruption (partial or full-word), breaks coherence/invariants, and can overwrite protected words.

> **CWE:** 1220, 1221, 1224, 1242, 1280, 1290, 1311, 1312, 1319

  (port, `std_ulogic_vector(3 downto 0)`, entity `neorv32_cache_memory`)
  - **functionality** — Per-bit write-enable signals gate writes to each data_mem_bX byte at acc_adr on the rising clock; each bit enables its corresponding byte write.
  - **roles** — byte write enables; gates data memory writes
  - **relationships** — **GATES** → data_mem_b0, data_mem_b1, data_mem_b2, data_mem_b3
  - **evidence** — data_memory process: if (we_i(0)='1') then data_mem_b0(...) <= ...; similarly for we_i(1..3).


## neorv32_cpu

### `alu_add` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Corruption redirects memory accesses.

> **CWE:** 203, 1255, 1303, 1290, 1311, 1312

  (signal, `std_ulogic_vector(XLEN-1 downto 0)`, entity `neorv32_cpu`)
  - **functionality** — Carries the ALU adder output from the ALU instance and supplies that computed address/value to the LSU and to the control instance (alu_add_i).
  - **roles** — adder result / address; forwarded from ALU to LSU and control
  - **relationships** — **CARRIES** → neorv32_cpu_alu_inst.add_o; **SOURCES** → neorv32_cpu_lsu_inst.addr_i, neorv32_cpu_control_inst.alu_add_i
  - **evidence** — alu port map: add_o => alu_add; lsu port map: addr_i => alu_add; control port map: alu_add_i => alu_add.

### `alu_res` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Corruption changes program semantics.

> **CWE:** 1258, 1255, 1300, 203, 1319, 1247, 1384

  (signal, `std_ulogic_vector(XLEN-1 downto 0)`, entity `neorv32_cpu`)
  - **functionality** — Receives the ALU result from the ALU instance and is one of the sources selected into the register-file writeback data (rf_wdata).
  - **roles** — ALU result; writeback source
  - **relationships** — **CARRIES** → neorv32_cpu_alu_inst.res_o; **SOURCES** → rf_wdata
  - **evidence** — alu port map: res_o => alu_res; rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret.

### `csr_rdata` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Must reflect true CSR contents (status/privilege/PMP config). Spoofing misleads software.

> **CWE:** 1262, 1243, 1258, 1221, 1224, 1220

  (signal, `std_ulogic_vector(XLEN-1 downto 0)`, entity `neorv32_cpu`)
  - **functionality** — Holds CSR read data produced by the control instance and supplies it as a possible register-file writeback source (rf_wdata).
  - **roles** — CSR readback; writeback source
  - **relationships** — **CARRIES** → neorv32_cpu_control_inst.csr_rdata_o; **SOURCES** → rf_wdata
  - **evidence** — control port map: csr_rdata_o => csr_rdata; rf_wdata <= ... or csr_rdata ...

### `dbi_i` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** Entering debug may expose internal state/memory, allow arbitrary modification, or halt the core.

> **CWE:** 1191, 1243, 1258, 1273, 1272, 203, 1255, 1300, 1244, 1220, 1247, 1242

  (port, `std_ulogic`, entity `neorv32_cpu`)
  - **functionality** — Forwards the debug interrupt input to the control instance; it is connected to the control's irq_dbg_i port.
  - **roles** — debug interrupt input; forwarded to control
  - **relationships** — **SOURCES** → neorv32_cpu_control_inst.irq_dbg_i
  - **evidence** — port map in neorv32_cpu_control_inst: irq_dbg_i => dbi_i.

### `firq_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** “Fast” custom IRQs can gate control flow or keep the core in ISR paths (DoS).

> **CWE:** 1189, 1220, 1276, 1247, 1245, 1384

  (port, `std_ulogic_vector(15 downto 0)`, entity `neorv32_cpu`)
  - **functionality** — Forwards the fast interrupt vector to the control submodule; it is passed unchanged to the control instance's irq_fast_i port.
  - **roles** — interrupt vector input; forwarded to control instance
  - **relationships** — **SOURCES** → neorv32_cpu_control_inst.irq_fast_i
  - **evidence** — port map in neorv32_cpu_control_inst: irq_fast_i => firq_i.

### `irq_machine` — Integrity `[paper]`

> **why the reference lists it:** Aggregated M-mode interrupt pending bits; forging can steer control flow or cause livelock.

> **CWE:** 1189, 1220, 1276, 1247, 1245

  (signal, `std_ulogic_vector(2 downto 0)`, entity `neorv32_cpu`)
  - **functionality** — Combines the three machine interrupt inputs (mti_i, mei_i, msi_i) into a 3-bit vector and supplies it to the control instance as the machine interrupt input.
  - **roles** — machine IRQ vector; forwarded to control
  - **relationships** — **DERIVES_FROM** → mti_i, mei_i, msi_i; **SOURCES** → neorv32_cpu_control_inst.irq_machine_i
  - **evidence** — irq_machine <= mti_i & mei_i & msi_i; control port map: irq_machine_i => irq_machine.

### `lsu_err` — Integrity  _(manual GT only)_

> **why the reference lists it:** Signals alignment/access faults; suppressing/forging errors enables illegal accesses or causes spurious traps.

> **CWE:** 1245, 1247, 1384, 203

  (signal, `std_ulogic_vector(3 downto 0)`, entity `neorv32_cpu`)
  - **functionality** — Carries LSU error status bits from the LSU instance and supplies them to the control unit for exception reporting via lsu_err_i.
  - **roles** — LSU error status; forwarded to control
  - **relationships** — **CARRIES** → neorv32_cpu_lsu_inst.err_o; **SOURCES** → neorv32_cpu_control_inst.lsu_err_i
  - **evidence** — lsu port map: err_o => lsu_err; control port map: lsu_err_i => lsu_err.

### `lsu_mar` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Memory address register; is critical to correct addressing.

> **CWE:** 1257, 1260, 1303, 1316, 1290, 1311, 1312

  (signal, `std_ulogic_vector(XLEN-1 downto 0)`, entity `neorv32_cpu`)
  - **functionality** — Receives the memory address register output from the LSU instance and forwards it to the control unit (lsu_mar_i) for debug/exception handling.
  - **roles** — LSU MAR; forwarded to control
  - **relationships** — **CARRIES** → neorv32_cpu_lsu_inst.mar_o; **SOURCES** → neorv32_cpu_control_inst.lsu_mar_i
  - **evidence** — lsu port map: mar_o => lsu_mar; control port map: lsu_mar_i => lsu_mar.

### `lsu_wait` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** Back-pressure indicator; misuse leads to DoS, observable timing differences.

> **CWE:** 1245, 1247, 1384, 203, 1255

  (signal, `std_ulogic`, entity `neorv32_cpu`)
  - **functionality** — Carries the LSU wait indicator from the LSU instance and supplies it to the control unit via lsu_wait_i for stall handling.
  - **roles** — LSU wait/stall indicator; forwarded to control
  - **relationships** — **CARRIES** → neorv32_cpu_lsu_inst.wait_o; **SOURCES** → neorv32_cpu_control_inst.lsu_wait_i
  - **evidence** — lsu port map: wait_o => lsu_wait; control port map: lsu_wait_i => lsu_wait.

### `mei_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** External interrupts can be abused to force trap/ISR paths or cause persistent preemption.

> **CWE:** 1189, 1220, 1276, 1247, 1245, 1384

  (port, `std_ulogic`, entity `neorv32_cpu`)
  - **functionality** — Supplies the machine-external interrupt bit to this entity; it is combined with msi_i and mti_i to form irq_machine used by control.
  - **roles** — interrupt source; input combined into irq vector
  - **relationships** — **SOURCES** → irq_machine
  - **evidence** — irq_machine <= mti_i & mei_i & msi_i (concurrent assignment).

### `msi_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Spurious machine software interrupts can redirect control flow or livelock the CPU

> **CWE:** 1189, 1220, 1276, 1247, 1245, 1384

  (port, `std_ulogic`, entity `neorv32_cpu`)
  - **functionality** — Supplies the machine-software interrupt bit to this entity; it is combined with mei_i and mti_i to form irq_machine used by control.
  - **roles** — interrupt source; input combined into irq vector
  - **relationships** — **SOURCES** → irq_machine
  - **evidence** — irq_machine <= mti_i & mei_i & msi_i (concurrent assignment).

### `mti_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Timer interrupts drive scheduling/CSRs; injection can corrupt execution order or starve tasks.

> **CWE:** 1189, 1220, 1276, 1247, 1245, 1384

  (port, `std_ulogic`, entity `neorv32_cpu`)
  - **functionality** — Supplies the machine-timer interrupt bit to this entity; it is combined with mei_i and msi_i to form irq_machine used by control.
  - **roles** — interrupt source; input combined into irq vector
  - **relationships** — **SOURCES** → irq_machine
  - **evidence** — irq_machine <= mti_i & mei_i & msi_i (concurrent assignment).

### `pmp_fault` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Signals permission violations; must assert correctly to enforce isolation and may reveal layout.

  (signal, `std_ulogic`, entity `neorv32_cpu`)
  - **functionality** — Receives the PMP fault output when PMP is enabled (from PMP instance) or is held '0' when PMP is disabled; the signal is forwarded to the control unit to indicate access faults.
  - **roles** — PMP fault flag; forwarded to control; sourced from PMP instance or tied low
  - **relationships** — **CARRIES** → neorv32_cpu_pmp_inst.fault_o; **SOURCES** → neorv32_cpu_control_inst.pmp_fault_i
  - **evidence** — pmp port map: fault_o => pmp_fault; pmp_disabled sets pmp_fault <= '0'; control port map: pmp_fault_i => pmp_fault.

### `rf_wdata` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Data written into the GPR file may be key material/intermediate crypto values; corruption directly breaks correctness.

> **CWE:** 1258, 1255, 1300, 203, 1319, 1247, 1384

  (signal, `std_ulogic_vector(XLEN-1 downto 0)`, entity `neorv32_cpu`)
  - **functionality** — Selects writeback data for the register file by OR'ing several sources (ALU result, LSU read data, CSR read data, or control.pc_ret) and supplies the result to the regfile rd_i port.
  - **roles** — writeback data; forwarded to regfile
  - **relationships** — **DERIVES_FROM** → alu_res, lsu_rdata, csr_rdata, ctrl.pc_ret; **SOURCES** → neorv32_cpu_regfile_inst.rd_i
  - **evidence** — rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret; regfile port map: rd_i => rf_wdata.


## neorv32_cpu_cp_cfu

### `active_i` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does handshake busy status with CPU, so blocking it stalls pipeline — that’s why availability must be preserved

> **CWE:** 1245, 1247, 1261

  (port, `std_ulogic`, entity `neorv32_cpu_cp_cfu`)
  - **functionality** — Declared input that is not read or used anywhere in this source; it has no effect inside this entity.
  - **roles** — unused port
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences of active_i in the source

### `csr_addr_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does select which CSR/key word is written — that’s why integrity must be preserved

> **CWE:** 1220, 1262, 1244

  (port, `std_ulogic_vector(1 downto 0)`, entity `neorv32_cpu_cp_cfu`)
  - **functionality** — Selects which key_mem element is read or written; it is used as the index for key_mem in both the CSR write process and the csr_rdata_o read assignment.
  - **roles** — address selector; selects key_mem element
  - **relationships** — **SELECTS** → key_mem
  - **evidence** — key_mem(to_integer(unsigned(csr_addr_i))) in csr_write_access and csr_rdata_o <= key_mem(to_integer(unsigned(csr_addr_i)))

### `csr_wdata_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does supply the data written into key_mem — that’s why integrity must be preserved

> **CWE:** 1220, 1262, 1244

  (port, `std_ulogic_vector(31 downto 0)`, entity `neorv32_cpu_cp_cfu`)
  - **functionality** — Supplies the 32-bit data written into the key_mem entry when csr_we_i is asserted; it is captured into key_mem on the clock edge.
  - **roles** — write data source; feeds key_mem
  - **relationships** — **SOURCES** → key_mem
  - **evidence** — key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i in csr_write_access

### `csr_we_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does gate writes into key_mem and status CSRs — that’s why integrity must be preserved

> **CWE:** 1220, 1262, 1244

  (port, `std_ulogic`, entity `neorv32_cpu_cp_cfu`)
  - **functionality** — Gates writes into the key_mem array when asserted; used only in the CSR write process to qualify storing csr_wdata_i at csr_addr_i.
  - **roles** — write enable; gates CSR write
  - **relationships** — **GATES** → key_mem
  - **evidence** — if (csr_we_i = '1') then key_mem(to_integer(unsigned(csr_addr_i))) <= csr_wdata_i in csr_write_access

### `key_mem` — Confidentiality `[paper]` `[paper-refined]`

> **why the reference lists it:** does store long-term XTEA key words — that’s why confidentiality must be preserved

> **CWE:** 203, 226, 319, 1191, 1239, 1258, 1300, 1342

  (signal, `key_mem_t`, entity `neorv32_cpu_cp_cfu`)
  - **functionality** — Stores four 32-bit key words written from csr_wdata_i at positions selected by csr_addr_i on csr_we_i; supplies selected key words to csr_rdata_o and tmp_z.
  - **roles** — key storage (holds across cycles); written by CSR writes; supplies key words to tmp_z and csr_rdata_o
  - **relationships** — **CAPTURES** → csr_wdata_i; **SOURCES** → csr_rdata_o, tmp_z
  - **evidence** — key_mem <= ... in csr_write_access; csr_rdata_o <= key_mem(...); tmp_z <= key_mem(...) concurrent

### `result_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does return computation result; if stuck CPU cannot proceed — that’s why availability must be preserved

> **CWE:** 1245, 1247, 1261

  (port, `std_ulogic_vector(31 downto 0)`, entity `neorv32_cpu_cp_cfu`)
  - **functionality** — Drives the external result port by carrying the xtea.res register value (or constants for init/others); it presents the computed result to the entity boundary.
  - **roles** — result export; carries computed result
  - **relationships** — **CARRIES** → xtea.res; **EXPORTS** → _(none)_
  - **evidence** — result_o <= xtea.res and other branches in result_select process

### `rs1_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does carry operand that directly affects result — that’s why integrity must be preserved

> **CWE:** 1189, 1251

  (port, `std_ulogic_vector(31 downto 0)`, entity `neorv32_cpu_cp_cfu`)
  - **functionality** — Supplies the 32-bit operand captured into xtea.opa on start; it is a source for the XTEA operand register.
  - **roles** — input operand; feeds xtea.opa
  - **relationships** — **SOURCES** → xtea.opa
  - **evidence** — xtea.opa <= rs1_i inside xtea_core when start condition

### `rs2_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does carry operand that directly affects result — that’s why integrity must be preserved

> **CWE:** 1189, 1251

  (port, `std_ulogic_vector(31 downto 0)`, entity `neorv32_cpu_cp_cfu`)
  - **functionality** — Supplies the 32-bit operand captured into xtea.opb on start; it is a source for the XTEA operand register.
  - **roles** — input operand; feeds xtea.opb
  - **relationships** — **SOURCES** → xtea.opb
  - **evidence** — xtea.opb <= rs2_i inside xtea_core when start condition

### `rs3_i` — Integrity  _(manual GT only)_

> **why the reference lists it:** does carry operand that directly affects result — that’s why integrity must be preserved

> **CWE:** 1189, 1251

  (port, `std_ulogic_vector(31 downto 0)`, entity `neorv32_cpu_cp_cfu`)
  - **functionality** — Declared operand input that is not read or used in this source; it has no effect inside this entity.
  - **roles** — unused port
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences of rs3_i in the source

### `start_i` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does initiate every CFU job, so blocking it halts progress — that’s why availability must be preserved

> **CWE:** 1245, 1247, 1261

  (port, `std_ulogic`, entity `neorv32_cpu_cp_cfu`)
  - **functionality** — Acts as a start request that, when asserted with the right rtype, gates capture of rs1/rs2 into xtea.opa/opb and sets xtea.done(0) to begin an operation.
  - **roles** — operation starter; gates register capture
  - **relationships** — **GATES** → xtea.opa, xtea.opb, xtea.done
  - **evidence** — if (start_i = '1') and (rtype_i = r3type_c) then xtea.opa<=rs1_i; xtea.opb<=rs2_i; xtea.done(0)<= '1' in xtea_core

### `valid_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does signal the completion of an operation. If compromised, it could prevent the CPU from recognizing when results are ready, impacting the module's availability.

> **CWE:** 1245, 1247, 1261, 1384

  (port, `std_ulogic`, entity `neorv32_cpu_cp_cfu`)
  - **functionality** — Exports the result valid flag driven from xtea.done(1) or constants; it reports when result_o holds a valid operation result.
  - **roles** — valid flag export; carries done bit
  - **relationships** — **CARRIES** → xtea.done; **EXPORTS** → _(none)_
  - **evidence** — valid_o <= xtea.done(1) in result_select for certain funct3 cases


## neorv32_cpu_cp_muldiv

### `ctrl.cnt` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Encodes opcode/funct fields that decide when the unit acts; corrupting them changes architectural state, that’s why it is integrity-critical.

> **CWE:** 1244, 1280, 1319

  (signal, `std_ulogic_vector(index_size_f(XLEN)-1 downto 0)`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Carries the countdown counter for multi-cycle serial operations; it is set in the clocked process and decremented when busy, and its all-zero detection helps end busy state.
  - **roles** — holds countdown across cycles; governs busy termination
  - **relationships** — **CAPTURES** → ctrl; **GATES** → ctrl.state
  - **evidence** — ctrl.cnt assigned in control process and used in 'if (or_reduce_f(ctrl.cnt) = '0') ...' condition

### `ctrl.rs1_is_signed` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Encodes opcode/funct fields that decide when the unit acts; corrupting them changes architectural state, that’s why it is integrity-critical.

> **CWE:** 1244, 1280, 1319

  (signal, `std_ulogic`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Records whether rs1 should be treated signed, derived from ctrl_i.ir_funct3 and used when forming DSP operands and in division sign handling.
  - **roles** — holds operand signedness; influences operand formation; gates division initialisation
  - **relationships** — **DERIVES_FROM** → ctrl_i.ir_funct3; **SOURCES** → mul.dsp_x, div.quotient; **GATES** → div.quotient
  - **evidence** — ctrl.rs1_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or ...; used in dsp_x formation and divider_core sign tests

### `ctrl.rs2_is_signed` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Encodes opcode/funct fields that decide when the unit acts; corrupting them changes architectural state, that’s why it is integrity-critical.

> **CWE:** 1244, 1280, 1319

  (signal, `std_ulogic`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Records whether rs2 should be treated signed, derived from ctrl_i.ir_funct3 and used to form DSP operand and divisor absolute value.
  - **roles** — holds operand signedness; influences operand formation
  - **relationships** — **DERIVES_FROM** → ctrl_i.ir_funct3; **SOURCES** → mul.dsp_y, div.rs2_abs
  - **evidence** — ctrl.rs2_is_signed <= '1' when (ctrl_i.ir_funct3 = op_mulh_c) or ...; used in dsp_y formation and div.rs2_abs assignment

### `ctrl.state` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Encodes opcode/funct fields that decide when the unit acts; corrupting them changes architectural state, that’s why it is integrity-critical.

> **CWE:** 1244, 1280, 1319

  (signal, `state_t`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Holds the current control state (S_IDLE/S_BUSY/S_DONE); it is updated in the clocked control process and is tested elsewhere to drive starts, division iterations and the valid output.
  - **roles** — holds state across cycles; governs updates; gates result valid
  - **relationships** — **CAPTURES** → ctrl; **SOURCES** → valid_o; **GATES** → mul.add, div.quotient, div.remainder
  - **evidence** — ctrl.state assigned in control process; tested in operation_result, mul_update and divider_core (if ctrl.state = S_BUSY / S_DONE / S_DONE)

### `div.res` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** An attack on the these Registers can significantly impact the integrity of arithmetic operations in the 'neorv32_cpu_cp_muldiv' entity, leading to incorrect results being propagated to other parts of the system.

> **CWE:** 1247, 1319

  (signal, `std_ulogic_vector(XLEN-1 downto 0)`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Final division result after applying sign correction; it is optionally negated from div.res_u based on div.sign_mod and is exported to res_o when selected.
  - **roles** — final result carrier; feeds output
  - **relationships** — **DERIVES_FROM** → div.res_u; **SOURCES** → res_o
  - **evidence** — div.res <= std_ulogic_vector(0 - unsigned(div.res_u)) when (div.sign_mod = '1') else div.res_u; operation_result uses div.res

### `div.start` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** The attack on ' Start Trigger' can significantly impact the availability of the 'neorv32_cpu_cp_muldiv' entity, as it controls the initiation of division/multiplication operations. Since division is a fundamental operation in many computational tasks, its unavailability can degrade the overall performance and functionality of the 'neorv32' design, affecting its reliability and usability in critical applications.

> **CWE:** 1247, 1319

  (signal, `std_ulogic`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Combinational start flag asserted when a divide command is detected; it gates initialisation in the clocked divider process and begins iterative division updates.
  - **roles** — start qualifier; gates divider initialisation
  - **relationships** — **DERIVES_FROM** → valid_cmd, ctrl_i.ir_funct3; **GATES** → div.quotient, div.rs2_abs, div.sign_mod, div.remainder
  - **evidence** — div.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '1') else '0'; used in divider_core process if (div.start = '1') then ...

### `mul.prod` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** An attack on the these Registers can significantly impact the integrity of arithmetic operations in the 'neorv32_cpu_cp_muldiv' entity, leading to incorrect results being propagated to other parts of the system.

> **CWE:** 1247, 1319

  (signal, `std_ulogic_vector((2*XLEN)-1 downto 0)`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Holds the current product bits (full width); it is produced either from DSP multiplication (parallel path) or shifted/updated in serial multiply, and its upper/lower slices form the output result.
  - **roles** — holds product across cycles; feeds result selection and serial logic
  - **relationships** — **CAPTURES** → mul.dsp_z; **SOURCES** → res_o, mul.add, mul.p_sext
  - **evidence** — multiplier_core_out_reg captures mul.prod <= std_ulogic_vector(mul.dsp_z(63 downto 0)); operation_result reads mul.prod(31 downto 0) and (63 downto 32)

### `mul.start` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** The attack on ' Start Trigger' can significantly impact the availability of the 'neorv32_cpu_cp_muldiv' entity, as it controls the initiation of division/multiplication operations. Since division is a fundamental operation in many computational tasks, its unavailability can degrade the overall performance and functionality of the 'neorv32' design, affecting its reliability and usability in critical applications.

> **CWE:** 1247, 1319

  (signal, `std_ulogic`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Combinational flag asserted when a multiply command is detected; it gates DSP operand capture and serial multiplier initialisation.
  - **roles** — start qualifier; gates multiplier initialisation
  - **relationships** — **DERIVES_FROM** → valid_cmd, ctrl_i.ir_funct3; **GATES** → mul.dsp_x, mul.dsp_y, mul.prod
  - **evidence** — mul.start <= '1' when (valid_cmd = '1') and (ctrl_i.ir_funct3(2) = '0') else '0'; used in multiplier processes

### `res_o` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The result output is crucial for the module's functionality. If unavailable, it would prevent the module from delivering its primary function, which is to provide arithmetic results.

> **CWE:** 1245, 1281, 1319

  (port, `std_ulogic_vector(XLEN-1 downto 0)`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Exports the computed multiply or divide result to the outside; its value is derived from mul.prod slices for multiplies or div.res for divides and is enabled by ctrl.out_en.
  - **roles** — result output; exports computed result
  - **relationships** — **DERIVES_FROM** → mul.prod, div.res; **EXPORTS** → _(none)_
  - **evidence** — operation_result process assigns res_o <= mul.prod(...) or div.res when (ctrl.out_en = '1')

### `rs1_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does carry the first arithmetic operand into the datapath, that’s why altering it forges the value that the CPU finally commits to its architectural state

> **CWE:** 1280, 1319

  (port, `std_ulogic_vector(XLEN-1 downto 0)`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Supplies the first multiplicand/dividend; it is consumed to form signed extended operands for the DSP multiply and to initialise the division quotient and sign calculations.
  - **roles** — operand input (consumed); source for multiply/divide calculations
  - **relationships** — **SOURCES** → mul.dsp_x, div.quotient
  - **evidence** — mul.dsp_x <= signed((rs1_i(rs1_i'left) and ctrl.rs1_is_signed) & rs1_i); div.quotient <= std_ulogic_vector(0 - unsigned(rs1_i)) or rs1_i

### `rs2_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does carry the second arithmetic operand into the datapath, that’s why tampering corrupts every product/quotient computed

> **CWE:** 1280, 1319

  (port, `std_ulogic_vector(XLEN-1 downto 0)`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Supplies the second multiplicand/divisor; it is read to form signed extended DSP operand, to compute serial multiplier adds, and to produce absolute divisor for division.
  - **roles** — operand input (consumed); source for multiply/divide calculations
  - **relationships** — **SOURCES** → mul.dsp_y, mul.add, div.rs2_abs
  - **evidence** — mul.dsp_y <= signed((rs2_i(rs2_i'left) and ctrl.rs2_is_signed) & rs2_i); mul_update uses rs2_i; div.rs2_abs <= ... rs2_i

### `valid_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does signal the CPU that the result is ready, that’s why forcing it low or high stalls the in-order pipeline

> **CWE:** 1245, 1281, 1319

  (port, `std_ulogic`, entity `neorv32_cpu_cp_muldiv`)
  - **functionality** — Reports when the unit has completed an operation; it is driven from the ctrl.state equality to S_DONE and exported outside the entity.
  - **roles** — status output; exports completion indication
  - **relationships** — **DERIVES_FROM** → ctrl.state; **EXPORTS** → _(none)_
  - **evidence** — valid_o <= '1' when (ctrl.state = S_DONE) else '0';


## neorv32_cpu_pmp

### `addr_ls_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The load/store address input is essential for determining which memory regions are accessed. If this input is corrupted, it could lead to unauthorized memory accesses, violating the integrity of the protected regions.

> **CWE:** 1276, 1280, 1318, 1319

  (port, `std_ulogic_vector(XLEN-1 downto 0)`, entity `neorv32_cpu_pmp`)
  - **functionality** — Supplies the load/store address used as acc_addr when lsu_mo_we = '1'; that chosen address is used for matching and permission checks.
  - **roles** — address operand; combinational input
  - **relationships** — **SOURCES** → acc_addr
  - **evidence** — acc_addr <= ctrl_i.pc_nxt when (ctrl_i.lsu_mo_we = '0') else addr_ls_i

### `ctrl_i` — Integrity  _(manual GT only)_

> **why the reference lists it:** does carry CSR address/data that program all PMP regions, that’s why its integrity must be preserved

> **CWE:** 1191, 1220

  (port, `ctrl_bus_t`, entity `neorv32_cpu_pmp`)
  - **functionality** — Provides CSR addresses, enables, write data and access/control fields; its constituent fields drive CSR write enables, address selection, privilege selection and permission computation, and thereby influence internal PMP state and fault reporting.
  - **roles** — input bundle; supplies CSR control; selects access address and privileges; gates CSR write enables
  - **relationships** — **SOURCES** → pmpcfg_we; **SOURCES** → pmpaddr_we; **SOURCES** → acc_addr; **SOURCES** → acc_priv; **SOURCES** → allow; **DERIVES_FROM** → cfg_rd32; **DERIVES_FROM** → addr_rd; **SOURCES** → fault_o
  - **evidence** — process headers and many RHS uses: csr_we_cfg, csr_we_addr, acc_addr/acc_priv assignments, perm_gen and fault_check processes (uses fields like csr_addr, csr_we, csr_wdata, lsu_mo_we, lsu_priv, lsu_rw, cpu_priv, cpu_debug)

### `fail` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** The 'Prioritized Fail Chain' is critical for ensuring access control in the neorv32 design. Attacks on this asset can lead to denial-of-service, significantly impacting the availability of the system.

> **CWE:** 1247, 1261

  (signal, `std_ulogic_vector(NUM_REGIONS   downto 0)`, entity `neorv32_cpu_pmp`)
  - **functionality** — Reduction-style vector that produces a chained fault indication: fail(NUM_REGIONS) is set when acc_priv != machine, and for each region fail(r) becomes not allow(r) if that region matches, otherwise propagates the next fail. fail(0) drives fault output.
  - **roles** — fault chain; feeds fault output
  - **relationships** — **DERIVES_FROM** → acc_priv; **DERIVES_FROM** → allow; **DERIVES_FROM** → match; **SOURCES** → fault_o
  - **evidence** — fail(NUM_REGIONS) <= '1' when (acc_priv /= priv_mode_m_c) else '0'; fail(r) <= not allow(r) when (match(r) = '1') else fail(r+1); fault_check uses fail(0)

### `fault_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does raise CPU access-fault exceptions that gate every memory access, that’s why its availability must be assured

> **CWE:** 1245, 1320

  (port, `std_ulogic`, entity `neorv32_cpu_pmp`)
  - **functionality** — Reports the sampled fault condition synchronous to clk: on clock edges it captures the combination of not cpu_debug AND fail(0), producing an external fault signal.
  - **roles** — status output; reports sampled fault
  - **relationships** — **CAPTURES** → fail
  - **evidence** — fault_check process: on rising_edge(clk_i) fault_o <= (not ctrl_i.cpu_debug) and fail(0)

### `pmpaddr` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does hold region boundary addresses that set protected windows, that’s why its integrity must be preserved

> **CWE:** 1220, 1221, 1224, 1260, 1299

  (signal, `pmpaddr_t`, entity `neorv32_cpu_pmp`)
  - **functionality** — Holds per-region PMP address values captured from CSR write data (with top bits padded); these addresses feed readback logic and form the basis for region comparisons.
  - **roles** — registered PMP address; provides match/address readback
  - **relationships** — **CAPTURES** → ctrl_i.csr_wdata; **SOURCES** → addr_rd; **SOURCES** → addr_mask_napot; **SOURCES** → cmp_ge; **SOURCES** → cmp_lt
  - **evidence** — csr_pmpaddr process captures "00" & ctrl_i.csr_wdata(XLEN-3 downto 0) on rising_edge(clk_i); pmpaddr used in address_read_back, addr_mask_napot_gen and comparison expressions

### `pmpcfg` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does store R/W/X and lock bits that define the protection policy, that’s why its integrity must be preserved

> **CWE:** 1220, 1221, 1224, 1260, 1299

  (signal, `pmpcfg_t`, entity `neorv32_cpu_pmp`)
  - **functionality** — Holds per-region 8-bit PMP configuration captured from CSR write data when write-enable is set; supplies these cfg bytes for readback, matching and permission logic.
  - **roles** — registered PMP config; holds region permissions; gates address writes
  - **relationships** — **CAPTURES** → ctrl_i.csr_wdata; **SOURCES** → cfg_rd; **SOURCES** → addr_rd; **SOURCES** → match; **SOURCES** → allow; **GATES** → pmpaddr; **GATES** → pmpcfg
  - **evidence** — csr_pmpcfg process captures bits from ctrl_i.csr_wdata on rising_edge(clk_i); used by cfg_rd assignment, match_gen and perm_gen and gating pmpaddr writes


## neorv32_debug_dtm

### `dmi_ctrl.busy` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** If dmi_ctrl.busy is spuriously asserted or stuck, all DMI activity is stalled, blocking debug operations and potentially halting maintenance flows.

> **CWE:** 1247

  (signal, `std_ulogic`, entity `neorv32_debug_dtm`)
  - **functionality** — Indicates an in-flight DMI transaction; it is set when a new request is started from tap_reg.dmi and cleared on dmi_rsp_i.ack, and it gates the dmi_controller behavior between request and response phases.
  - **roles** — holds busy state; gates controller flow; registered transaction flag
  - **relationships** — **CAPTURES** → tap_reg.dmi; **CAPTURES** → dmi_rsp_i.ack; **GATES** → dmi_ctrl.dmihardreset, dmi_ctrl.dmireset, dmi_ctrl.err, dmi_ctrl.rdata, dmi_ctrl.addr, dmi_ctrl.wdata, dmi_ctrl.op
  - **evidence** — dmi_controller sets busy <= '1' when condition on tap_reg.dmi holds and clears busy when dmi_rsp_i.ack = '1'; busy tested to choose branches.

### `jtag_tdi_i` — Integrity  _(manual GT only)_

> **why the reference lists it:** Supplies every bit shifted into TAP; corrupting or blocking it flips instructions/data.

> **CWE:** 1191, 1242, 1244, 1247, 1313

  (port, `std_ulogic`, entity `neorv32_debug_dtm`)
  - **functionality** — Provides the raw JTAG TDI level sampled into the synchronizer tap_sync.tdi_ff; the synchronized bit (tap_sync.tdi) feeds instruction/data shift operations.
  - **roles** — sampled input; feeds shift operations after sync; crosses entity boundary
  - **relationships** — **SOURCES** → tap_sync.tdi_ff
  - **evidence** — tap_synchronizer process shifts jtag_tdi_i into tap_sync.tdi_ff (tap_synchronizer rising_edge branch).

### `jtag_tdo_o` — Confidentiality `[paper]` `[paper-refined]`

> **why the reference lists it:** The JTAG TDO output could potentially leak sensitive information from the TAP registers if the module is used in a security-sensitive context. Protecting this output is crucial to prevent unauthorized access to internal states.

> **CWE:** 203, 1191

  (port, `std_ulogic`, entity `neorv32_debug_dtm`)
  - **functionality** — Drives the JTAG TDO pin from the current selected register bit (ireg(0), idcode(0), dtmcs(0), dmi(0) or bypass) on tck falling edges, and is initialized in reset.
  - **roles** — exports TAP serial output; reports low-order bits of selected register; registered output (updated on falling edge)
  - **relationships** — **CAPTURES** → tap_reg.ireg, tap_reg.idcode, tap_reg.dtmcs, tap_reg.dmi, tap_reg.bypass; **EXPORTS** → _(none)_
  - **evidence** — jtag_tdo_o assigned in reg_access process (reset and under "if (tap_sync.tck_falling = '1') then" with case on tap_reg.ireg).

### `jtag_tms_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Drives TAP state machine; falsifying  or blocking it forces illegal state

> **CWE:** 1191, 1242, 1244, 1247, 1313

  (port, `std_ulogic`, entity `neorv32_debug_dtm`)
  - **functionality** — Provides the raw JTAG TMS level sampled into tap_sync.tms_ff; the synchronized value tap_sync.tms is used to decide TAP state transitions.
  - **roles** — sampled input; governs TAP state transitions after sync; crosses entity boundary
  - **relationships** — **SOURCES** → tap_sync.tms_ff
  - **evidence** — tap_synchronizer process shifts jtag_tms_i into tap_sync.tms_ff (tap_synchronizer rising_edge branch).

### `tap_reg.dtmcs` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Corrupting Control and Status registers tampers system functiinality

> **CWE:** 1191, 1244, 1247, 1319

  (signal, `std_ulogic_vector(31 downto 0)`, entity `neorv32_debug_dtm`)
  - **functionality** — Holds the 32-bit DTM control/status register (captured from dtmcs_nxt or shifted); selected bits (16,17) are read by dmi_controller to control resets and dtmcs(0) is shifted out on TDO when selected.
  - **roles** — holds DTM control/status; supplies reset control bits to dmi_controller; feeds jtag_tdo_o when selected
  - **relationships** — **CAPTURES** → tap_reg.dtmcs_nxt, tap_sync.tdi; **SOURCES** → dmi_ctrl.dmireset, dmi_ctrl.dmihardreset, jtag_tdo_o
  - **evidence** — reg_access assigns tap_reg.dtmcs <= tap_reg.dtmcs_nxt in DR_CAPTURE and shifts from tap_sync.tdi in DR_SHIFT; dmi_controller reads tap_reg.dtmcs(16/17).


## neorv32_hwspinlock

### `lock_q` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does store the claimed/free state of each spin-lock, that’s why its integrity is critical

> **CWE:** 1221, 1256

  (signal, `std_ulogic_vector(31 downto 0)`, entity `neorv32_hwspinlock`)
  - **functionality** — Holds per-bit lock state; each bit is reset to '0' and on a selected transaction (stb and addr(7)=0 and sel(i)=1) captures not bus_req_i.rw, and supplies bits to the response data.
  - **roles** — held lock state; captures writes from bus; supplies read data
  - **relationships** — **CAPTURES** → bus_req_i.rw; **SOURCES** → bus_rsp_o.data
  - **evidence** — In spinlock process lock_q(i) <= not bus_req_i.rw when stb and addr(7)='0' and sel(i)='1'; bus_response reads lock_q into bus_rsp_o.data.

### `sel` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does decode which lock index is being accessed, that’s why its integrity is critical

> **CWE:** 1221

  (signal, `std_ulogic_vector(31 downto 0)`, entity `neorv32_hwspinlock`)
  - **functionality** — Combinationally derives which lock index is selected from bus_req_i.addr(6 downto 2) and supplies per-bit selection that gates lock updates and masks the response data when requested.
  - **roles** — address decode; combinational carrier; gates lock update
  - **relationships** — **DERIVES_FROM** → bus_req_i.addr; **GATES** → lock_q; **SOURCES** → bus_rsp_o.data
  - **evidence** — sel(i) <= '1' when (bus_req_i.addr(6 downto 2) = to_unsigned(i,5)) else '0'; sel(i) used in spinlock condition and in bus_rsp_o.data <= lock_q and sel.


## neorv32_imem

### `addr` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The signal addr is formed from bus_req_i.addr(addr_hi_c downto 2) and does directly select the IMEM word that will be read (or written in RAM builds); if a fault or attack alters addr, the CPU fetches or stores instructions at an unintended row – that’s why the signal’s integrity is critical.

> **CWE:** 1189, 1260, 1290, 1312, 1316, 1318

  (signal, `unsigned(index_size_f(IMEM_SIZE/4)-1 downto 0)`, entity `neorv32_imem`)
  - **functionality** — Converts the incoming bus_req_i.addr slice into an unsigned index and supplies indexing for memory accesses and may be captured into addr_ff for timing alignment.
  - **roles** — address index; carries combinational index
  - **relationships** — **DERIVES_FROM** → bus_req_i.addr; **SOURCES** → addr_ff; **SELECTS** → mem_ram_b0, mem_ram_b1, mem_ram_b2, mem_ram_b3
  - **evidence** — addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2)); addr is used as index in mem_ram_bN(to_integer(addr)) and is captured into addr_ff in processes.

### `rdata` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Internal read data does feed the CPU’s instruction bus – that’s why if it is injected or corrupted execution flow changes (integrity) or fetch hangs (availability).

> **CWE:** 1189, 1260, 1290

  (signal, `std_ulogic_vector(31 downto 0)`, entity `neorv32_imem`)
  - **functionality** — Holds the 32-bit word read from ROM or RAM. It is assigned from mem_rom_c(...) or from mem_ram_b0..3 indexed by addr/addr_ff and supplies bus_rsp_o.data when rden is asserted.
  - **roles** — read data register; supplies response data
  - **relationships** — **DERIVES_FROM** → mem_ram_b0, mem_ram_b1, mem_ram_b2, mem_ram_b3; **SOURCES** → bus_rsp_o.data
  - **evidence** — Assignments: rdata <= mem_rom_c(to_integer(addr)) or rdata <= mem_rom_c(to_integer(addr_ff)); and rdata(7 downto 0) <= mem_ram_b0(to_integer(addr)); rdata supplies bus_rsp_o.data.

### `rden` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Read-enable does gate every memory access – that’s why forcing it high/low feeds stale zeros (integrity) or blocks reads entirely (availability).

> **CWE:** 1245, 1267

  (signal, `std_ulogic`, entity `neorv32_imem`)
  - **functionality** — Captures stb and rw on the clock to produce a registered read enable (stb and not rw). It gates output data validity and is used by the bus response assignment.
  - **roles** — registered qualifier; gates output data
  - **relationships** — **CAPTURES** → bus_req_i.stb, bus_req_i.rw; **GATES** → bus_rsp_o.data; **SEQUENCES** → clk_i, rstn_i
  - **evidence** — In bus_feedback: rden <= bus_req_i.stb and (not bus_req_i.rw) on rising_edge(clk_i); rden used in "bus_rsp_o.data <= rdata when (rden = '1') else ..."


## neorv32_spi

### `clkgen_en_o` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Drives the dedicated SPI clock-generator enable line; if its value is corrupted, the serial clock can be started, stopped, or glitched at the wrong time — does directly determine the timing integrity of every SPI frame, that’s why it is integrity-critical.

> **CWE:** 1191, 1262, 1268

  (port, `std_ulogic`, entity `neorv32_spi`)
  - **functionality** — Drives an external clock-enable output directly from ctrl.enable and exports that internal enable to the outside.
  - **roles** — exports enable; reflects ctrl.enable
  - **relationships** — **CARRIES** → ctrl.enable; **EXPORTS** → _(none)_
  - **evidence** — clkgen_en_o <= ctrl.enable (concurrent assignment at end of architecture)

### `ctrl.cdiv` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Configuration bits that arms/disarms the interface; a bad write changes operating mode — does govern correct operation, that’s why it is integrity-critical.

> **CWE:** 1191, 1262, 1268

  (signal, `std_ulogic_vector(3 downto 0)`, entity `neorv32_spi`)
  - **functionality** — Captured from bus writes and compared with the internal cdiv_cnt; that comparison decides when spi_clk_en pulses and when cdiv_cnt resets.
  - **roles** — holds divider value; compares against counter to produce spi clock enable
  - **relationships** — **CAPTURES** → bus_req_i.data; **CONSTRAINS** → spi_clk_en, cdiv_cnt
  - **evidence** — ctrl.cdiv <= bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c) in bus_access; used in (cdiv_cnt = ctrl.cdiv) comparison in clock_generator

### `ctrl.enable` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Configuration bits that arms/disarms the interface; a bad write changes operating mode — does govern correct operation, that’s why it is integrity-critical.

> **CWE:** 1191, 1262, 1268

  (signal, `std_ulogic`, entity `neorv32_spi`)
  - **functionality** — Captured from bus_req_i.data when written; gates the clock generator and is used in IRQ generation and as clkgen_en_o output.
  - **roles** — holds enable across cycles; gates clock generator; exported via clkgen_en_o
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → cdiv_cnt; **SOURCES** → irq_o; **CARRIES** → clkgen_en_o
  - **evidence** — ctrl.enable <= bus_req_i.data(ctrl_en_c) in bus_access; used in clock_generator and irq_generator; clkgen_en_o <= ctrl.enable

### `ctrl.prsc` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** Configuration bits that arms/disarms the interface; a bad write changes operating mode — does govern correct operation, that’s why it is integrity-critical.

> **CWE:** 1191, 1262, 1268

  (signal, `std_ulogic_vector(2 downto 0)`, entity `neorv32_spi`)
  - **functionality** — Captured from bus writes and consumed as an index into clkgen_i to select the clock gating bit used by the clock generator.
  - **roles** — holds prescaler index; selects clkgen_i bit
  - **relationships** — **CAPTURES** → bus_req_i.data; **SELECTS** → clkgen_i
  - **evidence** — ctrl.prsc <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c) in bus_access; clkgen_i(to_integer(unsigned(ctrl.prsc))) used in clock_generator

### `irq_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** Driver relies on this interrupt; masked or stuck line blocks service — does notify events, that’s why it is availability-critical.

> **CWE:** 1320

  (port, `std_ulogic`, entity `neorv32_spi`)
  - **functionality** — Captured each rising edge from a boolean combination of ctrl.enable, ctrl.irq_* fields, fifo status and rtx_engine.busy; reports internal event conditions to the outside.
  - **roles** — exports interrupt status; derived from control and FIFO status
  - **relationships** — **DERIVES_FROM** → ctrl.enable, ctrl.irq_rx_avail, rx_fifo.avail, ctrl.irq_tx_empty, tx_fifo.avail, ctrl.irq_tx_nhalf, tx_fifo.half, ctrl.irq_idle, rtx_engine.busy; **EXPORTS** → _(none)_
  - **evidence** — irq_o <= ctrl.enable and ( ... ) inside rising_edge(clk_i) in irq_generator

### `spi_csn_o` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The spi_csn_o port determines which SPI device is active. If this signal is compromised, it could result in data being sent to or received from the wrong device, leading to data integrity issues.

> **CWE:** 1276

  (port, `std_ulogic_vector(7 downto 0)`, entity `neorv32_spi`)
  - **functionality** — Captured each clock in chip_select: defaults to all '1' and conditionally drives the indexed bit low according to rtx_engine.cs_ctrl; exports CS lines to external SPI slaves.
  - **roles** — exports chip selects; holds CS vector; captures selection control
  - **relationships** — **CAPTURES** → rtx_engine.cs_ctrl; **EXPORTS** → _(none)_
  - **evidence** — spi_csn_o <= (others => '1') and indexed assignment using rtx_engine.cs_ctrl inside chip_select process

### `spi_dat_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The spi_dat_i port receives data from peripherals. If this input is compromised, it could lead to incorrect data being processed by the SPI controller, affecting the integrity of the received data.

> **CWE:** 1296

  (port, `std_ulogic`, entity `neorv32_spi`)
  - **functionality** — Supplies incoming serial data which is sampled into rtx_engine.sdi_sync in the transceiver state machine and then shifted into sreg.
  - **roles** — serial data source; consumed by transceiver
  - **relationships** — **SOURCES** → rtx_engine.sdi_sync
  - **evidence** — rtx_engine.sdi_sync <= spi_dat_i inside transceiver when state "110"

### `spi_dat_o` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The spi_dat_o port is used to send data to peripherals. If this output is tampered with, it could result in incorrect data being sent, affecting the integrity of the communication with peripheral devices.

> **CWE:** 1276

  (port, `std_ulogic`, entity `neorv32_spi`)
  - **functionality** — Driven combinationally from the MSB of rtx_engine.sreg (bit 7) and exported as the MOSI/MISO output depending on configuration.
  - **roles** — exports serial data; driven by shift register
  - **relationships** — **CARRIES** → rtx_engine.sreg; **EXPORTS** → _(none)_
  - **evidence** — spi_dat_o <= rtx_engine.sreg(7) (concurrent assignment)


## neorv32_sys

### `clk_en_o` — Availability  _(manual GT only)_

> **why the reference lists it:** The clock-enable ticks output is essential for providing clock-enable pulses that are used for timing control within the system. If this output is unavailable, it could prevent the proper operation of the system, leading to a denial of service.

> **CWE:** 1245, 1261, 1276, 1281, 1248, 1338

  (port, `std_ulogic_vector(7 downto 0)`, entity `neorv32_sys_clock`)
  - **functionality** — Exports eight single-bit clock-enable pulses derived from counter bits; each clk_en_o(bit) is assigned cnt(i) and (not cnt2(i)) to produce a one-cycle pulse at various divide ratios.
  - **roles** — output vector; carries divided clock pulses to consumers
  - **relationships** — **DERIVES_FROM** → cnt, cnt2; **DERIVES_FROM** → cnt, cnt2; **DERIVES_FROM** → cnt, cnt2; **DERIVES_FROM** → cnt, cnt2; **DERIVES_FROM** → cnt, cnt2; **DERIVES_FROM** → cnt, cnt2; **DERIVES_FROM** → cnt, cnt2; **DERIVES_FROM** → cnt, cnt2
  - **evidence** — concurrent assignments like clk_en_o(clk_div2_c) <= cnt(0) and (not cnt2(0)); similar lines for other divisors

### `enable_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The enable channels input is crucial for controlling the generation of clock-enable pulses. If this input is tampered with, it could disrupt the timing and synchronization of the system, leading to potential data corruption or malfunction.

> **CWE:** 1220, 1221, 1224, 1256, 1260, 1257

  (port, `std_ulogic_vector(NUM_EN-1 downto 0)`, entity `neorv32_sys_clock`)
  - **functionality** — Provides a vector whose OR-reduction is sampled into en; the port's bits are reduced by or_reduce_f and that result is captured into en to enable counting.
  - **roles** — control input; supplies enable reduction
  - **relationships** — **SOURCES** → en
  - **evidence** — en <= or_reduce_f(enable_i) inside the rising_edge branch of ticker process


## neorv32_trng

### `data_o` — Confidentiality `[paper]` `[paper-refined]`

> **why the reference lists it:** neoTRNG.data_o is the first point where the fully debiased byte exits the core; disclosure reveals key material — that’s why it is confidentiality-critical.

> **CWE:** 319, 276, 1220, 1191, 1244, 1258, 1300

  (port, `std_ulogic_vector(7 downto 0)`, entity `neoTRNG`)
  - **functionality** — Exports the 8-bit sampling shift register value sample_sreg unchanged to the consumer as the data output.
  - **roles** — byte output; exports sample_sreg
  - **relationships** — **CARRIES** → sample_sreg
  - **evidence** — data_o <= sample_sreg concurrent assignment.

### `enable` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** enable gates whether entropy generation is active; flipping it biases or freezes output — that’s why it is integrity-critical.

> **CWE:** 276, 1221, 1224, 1189, 1191, 1209, 1244, 1259, 1313

  (signal, `std_ulogic`, entity `neorv32_trng`)
  - **functionality** — Captured from bus_req_i.data(ctrl_en_c) in a write transaction and reset to '0'; it drives neoTRNG_inst.enable_i, is reported in bus_rsp_o.data, and participates in fifo.clear logic.
  - **roles** — holds TRNG enable across cycles; controls neoTRNG and FIFO-clear logic; reported in bus response
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → neoTRNG_inst.enable_i, bus_rsp_o.data; **GATES** → fifo.clear
  - **evidence** — enable <= bus_req_i.data(ctrl_en_c) in write branch; port mapped to neoTRNG_inst.enable_i; used in fifo.clear concurrent assignment.

### `fifo.avail` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** If avail or free is forced low- the readiness of the data— that’s why availability-critical.

> **CWE:** 1245, 1261, 1279, 1313, 1320

  (signal, `std_ulogic`, entity `neorv32_trng`)
  - **functionality** — Captured from rnd_pool_fifo_inst.avail_o; reported into bus_rsp_o.data at bit ctrl_avail_c and used to select zero vs fifo.rdata when the CPU reads the data register.
  - **roles** — reports FIFO availability; gates data-read response
  - **relationships** — **CAPTURES** → rnd_pool_fifo_inst.avail_o; **SLICES** → bus_rsp_o.data; **GATES** → bus_rsp_o.data
  - **evidence** — rnd_pool_fifo_inst port map avail_o => fifo.avail; bus_access tests fifo.avail to select bus_rsp_o.data <= (others=>'0') or fifo.rdata.

### `fifo.free` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** If avail or free is forced low- the readiness of the data— that’s why availability-critical.

> **CWE:** 1245, 1261, 1279, 1313, 1320

  (signal, `std_ulogic`, entity `neorv32_trng`)
  - **functionality** — Captured from rnd_pool_fifo_inst.free_o and available internally; not read or acted on elsewhere in this source.
  - **roles** — status output from FIFO; captured and unused
  - **relationships** — **CAPTURES** → rnd_pool_fifo_inst.free_o
  - **evidence** — rnd_pool_fifo_inst port map free_o => fifo.free; no other references in the source.

### `fifo.re` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The fifo.re signal controls when data can be read from the FIFO. If this signal is altered, it could lead to incorrect data being read, affecting the integrity of the TRNG's output.

> **CWE:** 1189, 1191, 1221, 1224, 1244

  (signal, `std_ulogic`, entity `neorv32_trng`)
  - **functionality** — Derived combinationally from bus_req_i.stb, bus_req_i.rw and bus_req_i.addr(2) and forwarded to rnd_pool_fifo_inst.re_i to pop data on bus reads.
  - **roles** — combinational read enable; drives FIFO pop on bus read
  - **relationships** — **DERIVES_FROM** → bus_req_i.stb, bus_req_i.rw, bus_req_i.addr; **SOURCES** → rnd_pool_fifo_inst.re_i
  - **evidence** — concurrent assignment fifo.re <= '1' when (bus_req_i.stb='1') and (bus_req_i.rw='0') and (bus_req_i.addr(2)='1') else '0'; port mapped to rnd_pool_fifo_inst.re_i.

### `fifo_clr` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** fifo_clr does something essential — it flushes all queued entropy; a malicious or accidental pulse replaces good data with zeros or stale bytes, so the byte stream’s correctness relies on this signal’s integrity, that’s why it is integrity-critical.

> **CWE:** 1189, 1191, 1221, 1224, 1244

  (signal, `std_ulogic`, entity `neorv32_trng`)
  - **functionality** — Captured from bus_req_i.data(ctrl_fifo_clr_c) on writes and reset to '0'; it contributes to fifo.clear (combined with enable) to clear the FIFO when asserted.
  - **roles** — holds FIFO-clear control; gates FIFO clear logic
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → fifo.clear
  - **evidence** — fifo_clr <= bus_req_i.data(ctrl_fifo_clr_c) in write branch; used in fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1').

### `valid_o` — Availability  _(manual GT only)_

> **why the reference lists it:** valid_o does something fundamental — it flags that a fresh random byte is present; if it never asserts, no bytes enter the FIFO, denying entropy to all consumers, that’s why it is availability-critical.

> **CWE:** 1245, 1261, 1279, 1313, 1320

  (port, `std_ulogic`, entity `neoTRNG`)
  - **functionality** — Exports the MSB bit of the internal sample_cnt as a ready/valid indicator to the consumer by presenting sample_cnt(sample_cnt'left) at the port.
  - **roles** — output flag; exports sample_cnt MSB
  - **relationships** — **SLICES** → sample_cnt
  - **evidence** — valid_o <= sample_cnt(sample_cnt'left) concurrent assignment.


## neorv32_twi

### `ctrl.cdiv` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does configure and enable the whole TWI engine, that’s why writes by an unauthorized agent can change clock rate, disable clock-stretch handling, or turn the block on/off, corrupting every subsequent transfer.

> **CWE:** 1262, 1299

  (signal, `std_ulogic_vector(3 downto 0)`, entity `neorv32_twi`)
  - **functionality** — Loaded from bus writes and compared against clk_gen.cnt to produce clk_gen.tick when equal; configures tick frequency.
  - **roles** — divider value; registered configuration; compared to clk counter to generate tick
  - **relationships** — **CAPTURES** → bus_req_i.data; **CONSTRAINS** → clk_gen.cnt, clk_gen.tick
  - **evidence** — Assigned in bus_access from bus_req_i.data(ctrl_cdiv3_c downto ctrl_cdiv0_c); compared in clock_generator: if (clk_gen.cnt = ctrl.cdiv) then ...

### `ctrl.enable` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does configure and enable the whole TWI engine, that’s why writes by an unauthorized agent can change clock rate, disable clock-stretch handling, or turn the block on/off, corrupting every subsequent transfer.

> **CWE:** 1262, 1299

  (signal, `std_ulogic`, entity `neorv32_twi`)
  - **functionality** — Captured from bus_req_i.data on writes and read back; it enables the clock generator, gates FIFO clear, and is sampled into engine.state(2) to enable the engine.
  - **roles** — enable flag; registered configuration; gates clocking and engine operation
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → fifo.clear, clkgen_en_o, io_con.sda_out, io_con.scl_out, engine.state, clk_gen.phase_gen; **GATES** → clk_gen.tick, clk_gen.cnt, clk_gen.phase_gen
  - **evidence** — Assigned in bus_access: ctrl.enable <= bus_req_i.data(ctrl_en_c); used in fifo.clear, clkgen_en_o, engine.state(2) and clock/phase generator conditions.

### `ctrl.prsc` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does configure and enable the whole TWI engine, that’s why writes by an unauthorized agent can change clock rate, disable clock-stretch handling, or turn the block on/off, corrupting every subsequent transfer.

> **CWE:** 1262, 1299

  (signal, `std_ulogic_vector(2 downto 0)`, entity `neorv32_twi`)
  - **functionality** — Captured from bus writes and used as an index into clkgen_i to select which bit gates the clock-counter; configures clock generation rate selection.
  - **roles** — prescaler index; registered configuration; selects clkgen_i bit
  - **relationships** — **CAPTURES** → bus_req_i.data; **SELECTS** → clkgen_i
  - **evidence** — Assigned in bus_access from bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c); used as index in clkgen_i(to_integer(unsigned(ctrl.prsc))).

### `irq_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does interrupt CPU when transfer ends, that’s why suppressing it forces time-outs and disables the peripheral.

> **CWE:** 1320, 1334

  (port, `std_ulogic`, entity `neorv32_twi`)
  - **functionality** — Registered interrupt output asserted when ctrl.enable is set, TX FIFO not available and engine not busy; computed each clock and exposed externally.
  - **roles** — interrupt output; reports ready-to-service condition; register driven by internal status
  - **relationships** — **DERIVES_FROM** → ctrl.enable, fifo.tx_avail, engine.busy
  - **evidence** — Assigned in irq_generator process at rising_edge(clk_i): irq_o <= ctrl.enable and (not fifo.tx_avail) and (not engine.busy).

### `twi_sda_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The twi_sda_i input is crucial for receiving data from the I\u00b2C bus. Any alteration in this input could lead to incorrect data being processed, thus affecting the integrity of the data communication.

> **CWE:** 1276, 1334

  (port, `std_ulogic`, entity `neorv32_twi`)
  - **functionality** — Converted and presented as io_con.sda_in, which is then sampled into io_con.sda_in_ff for engine use.
  - **roles** — serial input; feeds io_con sampling chain
  - **relationships** — **SOURCES** → io_con.sda_in
  - **evidence** — Assigned: io_con.sda_in <= to_stdulogic(to_bit(twi_sda_i)).

### `twi_sda_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** SDA is the data/ACK line of the two-wire bus. If it’s forced low/high, tri-stated, or heavily glitched, START/STOP and ACK handshakes fail; the controller can’t complete bytes, and the bus remains “busy” or stalls—i.e., a denial-of-service.

> **CWE:** 1245, 1247, 1261, 1276, 1384

  (port, `std_ulogic`, entity `neorv32_twi`)
  - **functionality** — Drives the external SDA pin from the internal io_con.sda_out signal (direct combinational forwarding).
  - **roles** — serial output; carries io_con.sda_out to external pin
  - **relationships** — **CARRIES** → io_con.sda_out
  - **evidence** — Concurrent assignment: twi_sda_o <= io_con.sda_out.


## neorv32_uart

### `clkgen_en_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does gate the UART’s bit clock, that’s why forcing it low halts both transmit and receive engines

> **CWE:** 1247, 1384

  (port, `std_ulogic`, entity `neorv32_uart`)
  - **functionality** — Forwards the ctrl.enable bit to the external clock generator. It is driven continuously from the internal ctrl.enable so external clock generation follows the control enable.
  - **roles** — exported enable; combinational forwarder
  - **relationships** — **CARRIES** → ctrl.enable
  - **evidence** — concurrent assignment clkgen_en_o <= ctrl.enable

### `ctrl.baud` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does hold configuration fields (enable, baud, IRQ levels, clears), that’s why unauthorized writes change timing or silently discard/overwrite data

> **CWE:** 1262, 1244, 1191

  (signal, `std_ulogic_vector(9 downto 0)`, entity `neorv32_uart`)
  - **functionality** — Stores the baud reload value written via the bus; transmitter and receiver load this value into their baud counters to generate bit timing.
  - **roles** — baud configuration; supplies baud reload to engines
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → tx_engine.baudcnt, rx_engine.baudcnt
  - **evidence** — ctrl.baud <= bus_req_i.data(ctrl_baud9_c downto ctrl_baud0_c); used to set tx_engine.baudcnt and rx_engine.baudcnt in engines

### `ctrl.enable` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does hold configuration fields (enable, baud, IRQ levels, clears), that’s why unauthorized writes change timing or silently discard/overwrite data

> **CWE:** 1262, 1244, 1191

  (signal, `std_ulogic`, entity `neorv32_uart`)
  - **functionality** — Captures the enable bit written from the bus and gates many behaviours (clock output, engine state bits, IRQ generation and FIFO clears). It is updated from bus_req_i.data and sampled throughout processes to enable or disable UART operation.
  - **roles** — held enable flag; gates engine activity; exported via clkgen_en_o
  - **relationships** — **CAPTURES** → bus_req_i.data; **CARRIES** → clkgen_en_o; **GATES** → tx_engine.state, rx_engine.state, uart_rtsn_o, irq_tx_o, irq_rx_o, tx_fifo.clear, rx_fifo.clear
  - **evidence** — ctrl.enable <= bus_req_i.data(ctrl_en_c) in bus_access; used to set tx_engine.state(2), rx_engine.state(1) and to compute clkgen_en_o and FIFO clears

### `ctrl.prsc` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does hold configuration fields (enable, baud, IRQ levels, clears), that’s why unauthorized writes change timing or silently discard/overwrite data

> **CWE:** 1262, 1244, 1191

  (signal, `std_ulogic_vector(2 downto 0)`, entity `neorv32_uart`)
  - **functionality** — Holds a small index selecting which bit of clkgen_i drives uart_clk. It is written from bus data and used as the index in the concurrent assignment that derives uart_clk.
  - **roles** — held prescaler index; selects uart_clk bit
  - **relationships** — **CAPTURES** → bus_req_i.data; **SELECTS** → clkgen_i
  - **evidence** — ctrl.prsc <= bus_req_i.data(ctrl_prsc2_c downto ctrl_prsc0_c); uart_clk <= clkgen_i(to_integer(unsigned(ctrl.prsc)))

### `irq_rx_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does signal the CPU to service the RX FIFO, that’s why masking or spoofing it allows overflow and stalls reception

> **CWE:** 1320, 1384

  (port, `std_ulogic`, entity `neorv32_uart`)
  - **functionality** — Signals RX-related interrupts based on enabled irq controls and FIFO status. The rx_irq_generator process computes irq_rx_o each clock from ctrl.enable and ctrl.irq_rx_* bits together with rx_fifo.avail/half/free.
  - **roles** — interrupt output; reports RX FIFO conditions
  - **relationships** — **CAPTURES** → ctrl.enable, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, rx_fifo.avail, rx_fifo.half, rx_fifo.free
  - **evidence** — rx_irq_generator process sets irq_rx_o <= ctrl.enable and (...) in rising_edge(clk_i)

### `irq_tx_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does signal the CPU to service the TX FIFO, that’s why masking or spoofing it allows underflow and stalls transmission

> **CWE:** 1320, 1384

  (port, `std_ulogic`, entity `neorv32_uart`)
  - **functionality** — Signals TX-related interrupts according to enabled irq controls and TX FIFO status. The tx_irq_generator process updates irq_tx_o each clock from ctrl.enable, ctrl.irq_tx_* and tx_fifo.avail/half.
  - **roles** — interrupt output; reports TX FIFO conditions
  - **relationships** — **CAPTURES** → ctrl.enable, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, tx_fifo.avail, tx_fifo.half
  - **evidence** — tx_irq_generator process sets irq_tx_o <= ctrl.enable and (...) in rising_edge(clk_i)

### `uart_ctsn_i` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does assert the peer’s “clear-to-send” status, that’s why holding it de-asserted blocks all transmission

> **CWE:** 1384

  (port, `std_ulogic`, entity `neorv32_uart`)
  - **functionality** — Feeds remote CTS into the transmit engine. The transmitter process shifts uart_ctsn_i into tx_engine.cts so the engine observes the peer's CTS for hardware flow-control decisions.
  - **roles** — hardware flow-control input; feeds tx_engine CTS
  - **relationships** — **SOURCES** → tx_engine.cts
  - **evidence** — tx_engine.cts <= tx_engine.cts(0) & uart_ctsn_i in transmitter process (rising_edge(clk_i))

### `uart_rtsn_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does advertise our “ready-to-receive” status, that’s why holding it asserted stops the peer from sending

> **CWE:** 1276, 1384

  (port, `std_ulogic`, entity `neorv32_uart`)
  - **functionality** — Provides the hardware flow-control RTS signal to the peer. The rtr_control process sets uart_rtsn_o each clock depending on ctrl.hwfc_en, ctrl.enable and rx_fifo.half, thereby asserting RTS when receiving should be paused.
  - **roles** — hardware flow-control output; synchronised control output
  - **relationships** — **CAPTURES** → ctrl.hwfc_en, ctrl.enable, rx_fifo.half
  - **evidence** — rtr_control process assigns uart_rtsn_o in rising_edge(clk_i) based on ctrl.hwfc_en, ctrl.enable, rx_fifo.half

### `uart_rxd_i` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does carry every incoming serial bit into the RX state-machine, that’s why any injection or corruption on this pin directly alters the value of the received data byte

> **CWE:** 1319, 1384

  (port, `std_ulogic`, entity `neorv32_uart`)
  - **functionality** — Feeds serial RX samples into the receiver synchroniser. The receiver process samples uart_rxd_i into rx_engine.sync(2) and thereby supplies bits for the RX shift register and framing logic.
  - **roles** — serial RX input; synchroniser source
  - **relationships** — **SOURCES** → rx_engine.sync
  - **evidence** — rx_engine.sync(2) <= uart_rxd_i in receiver process (rising_edge(clk_i))

### `uart_txd_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does drive outgoing serial data bits, that’s why a stuck fault prevents the peer from receiving any bytes

> **CWE:** 1384

  (port, `std_ulogic`, entity `neorv32_uart`)
  - **functionality** — Reports the transmit-output value produced by the transmit engine. It is driven continuously from tx_engine.txd so the external TX pin follows the engine's output.
  - **roles** — serial TX output; export of engine state
  - **relationships** — **CARRIES** → tx_engine.txd
  - **evidence** — concurrent assignment uart_txd_o <= tx_engine.txd


## neorv32_wdt

### `clkgen_en_o` — Availability `[paper]` `[paper-refined]`

> **why the reference lists it:** does enable the prescaler – if forced low, the counter never ticks, that’s why availability is critical.

> **CWE:** 1242, 1245, 1261

  (port, `std_ulogic`, entity `neorv32_wdt`)
  - **functionality** — Mirrors the internal ctrl.enable bit to an external clkgen enable output; directly driven by the control register value.
  - **roles** — forwarded output; exports enable state
  - **relationships** — **CARRIES** → ctrl.enable; **EXPORTS** → _(none)_
  - **evidence** — clkgen_en_o <= ctrl.enable (concurrent assignment)

### `cnt` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** The cnt signal is essential for tracking the timeout period. If its value is altered, it could prevent the WDT from triggering a reset when required, compromising system safety.

> **CWE:** 1220, 1221, 1251

  (signal, `std_ulogic_vector(23 downto 0)`, entity `neorv32_wdt`)
  - **functionality** — Holds the running counter value; increments when cnt_inc is true, is cleared on disable or reset_wdt, and is compared against ctrl.timeout to detect timeout.
  - **roles** — held counter; compared for timeout; incremented each tick
  - **relationships** — **DERIVES_FROM** → cnt; **CONSTRAINS** → cnt_timeout
  - **evidence** — cnt <= std_ulogic_vector(unsigned(cnt) + 1) in wdt_counter; comparison (cnt = ctrl.timeout) used in cnt_timeout

### `cnt_timeout` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does assert when cnt = timeout – corrupting this flag can mask a true time-out or raise false ones, that’s why integrity is critical.

> **CWE:** 1221, 1242, 1247

  (signal, `std_ulogic`, entity `neorv32_wdt`)
  - **functionality** — Combinationally asserted when counting has started and the counter equals the configured timeout; this signal is then used to request a hardware timeout reset.
  - **roles** — derived timeout flag; enables hardware timeout request
  - **relationships** — **DERIVES_FROM** → cnt_started, cnt, ctrl.timeout; **SOURCES** → hw_rst_timeout
  - **evidence** — cnt_timeout <= '1' when (cnt_started = '1') and (cnt = ctrl.timeout) else '0'

### `ctrl.enable` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does control whether the watchdog is active – if an attacker rewrites it, all timeout resets can be suppressed, that’s why integrity is critical.

> **CWE:** 1220, 1221, 1247, 1299

  (signal, `std_ulogic`, entity `neorv32_wdt`)
  - **functionality** — Captured from bus write (specific data bit) or cleared on reset; read by the counter and reset logic and forwarded outside as clkgen_en_o and in bus reads.
  - **roles** — held enable bit; controls counter start; forwarded to clkgen_en_o
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → clkgen_en_o, cnt_started, hw_rst_timeout, bus_rsp_o.data; **GATES** → cnt
  - **evidence** — ctrl.enable <= bus_req_i.data(ctrl_enable_c) in bus_access; used in wdt_counter and clkgen_en_o <= ctrl.enable

### `ctrl.lock` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does control whether the watchdog is active – if an attacker rewrites it, all timeout resets can be suppressed, that’s why integrity is critical.

> **CWE:** 1220, 1221, 1247, 1299

  (signal, `std_ulogic`, entity `neorv32_wdt`)
  - **functionality** — Captured from bus write (combined with current enable) and read back; it gates whether subsequent writes to control fields are allowed and thus prevents modifications when set.
  - **roles** — held lock bit; gates register writes
  - **relationships** — **DERIVES_FROM** → bus_req_i.data, ctrl.enable; **GATES** → reset_force; **SOURCES** → bus_rsp_o.data
  - **evidence** — ctrl.lock <= bus_req_i.data(ctrl_lock_c) and ctrl.enable in bus_access; used to decide write acceptance

### `ctrl.timeout` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** does control whether the watchdog is active – if an attacker rewrites it, all timeout resets can be suppressed, that’s why integrity is critical.

> **CWE:** 1220, 1221, 1247, 1299

  (signal, `std_ulogic_vector(23 downto 0)`, entity `neorv32_wdt`)
  - **functionality** — Captured from a slice of the bus write data and held; compared to the running counter to detect timeout and exported in bus reads.
  - **roles** — held timeout register; compared with counter; exported on bus read
  - **relationships** — **CAPTURES** → bus_req_i.data; **CONSTRAINS** → cnt_timeout; **SOURCES** → bus_rsp_o.data
  - **evidence** — ctrl.timeout <= bus_req_i.data(ctrl_timeout_msb_c downto ctrl_timeout_lsb_c) and used in (cnt = ctrl.timeout)

### `reset_cause` — Integrity `[paper]` `[paper-refined]`

> **why the reference lists it:** This status/flag register tells firmware why the watchdog (or system) reset occurred and often steers the recovery path (safe-mode, logging, lockout). If an attacker can alter or spoof it, they can hide a malicious reset, trigger the wrong recovery flow, or bypass post-reset safety checks—hence the integrity of this record is critical.

> **CWE:** 1220, 1221, 1224, 1262, 1280, 1290, 1313

  (signal, `std_ulogic_vector(1 downto 0)`, entity `neorv32_wdt`)
  - **functionality** — Holds a two-bit code indicating why the last reset occurred; updated by debug, timeout or access reset conditions and read-out on bus reads.
  - **roles** — held reset code; exported on bus read; updated by reset conditions
  - **relationships** — **CAPTURES** → _(none)_; **GATES** → reset_cause; **SOURCES** → bus_rsp_o.data
  - **evidence** — reset_cause set in reset_identifier process on rstn_dbg_i, hw_rst_timeout, hw_rst_access; read into bus_rsp_o.data(ctrl_rcause_hi_c downto ctrl_rcause_lo_c)

### `reset_wdt` — Availability  _(manual GT only)_

> **why the reference lists it:** if blocked, the WDT expires and can reset the system repeatedly (reset storm); if forced or stuck asserted, timeouts are masked and a hung system can persist—either way, service is denied, so availability is critical.

> **CWE:** 1245, 1261, 1247, 1313, 1242

  (signal, `std_ulogic`, entity `neorv32_wdt`)
  - **functionality** — Captured when a write with the correct reset password occurs; when asserted it clears the counter on the next cycle (used to reset the watchdog timer).
  - **roles** — reset request flag; clears counter
  - **relationships** — **DERIVES_FROM** → bus_req_i.data; **GATES** → cnt
  - **evidence** — reset_wdt <= '1' when bus_req_i.data(31 downto 0) = reset_pwd_c in bus_access; wdt_counter checks (reset_wdt = '1') to clear cnt


---

# Section B — every other element in the same modules

These are the non-assets. The asset stage must reject all of them. They are listed with the same four fields, so what the parser wrote here can be compared directly against Section A.

## neorv32_bus  (859 non-assets)

### ports

**`clk_i`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Provides the rising-edge timing used by sequential processes; it sequences updates of arbiter and alu_res registers on rising edges.
  - **roles** — clock source; sequences register updates
  - **relationships** — **SEQUENCES** → arbiter; **SEQUENCES** → alu_res
  - **evidence** — rising_edge(clk_i) in arbiter_sync and amo_alu processes

**`core_req_i`** — neorv32_bus_amo_rmw · `bus_req_t`
  - **functionality** — Supplies the request fields consumed to start AMO sequences and forwarded to sys_req_o; individual fields are read for control, data capture, and forwarding to the system interface.
  - **roles** — input bundle; provides operands and control for AMO; forwards request fields to sys_req_o
  - **relationships** — **SOURCES** → sys_req_o.addr, sys_req_o.ben, sys_req_o.src, sys_req_o.priv, sys_req_o.debug, sys_req_o.amo, sys_req_o.amoop, sys_req_o.lock, sys_req_o.fence; **SOURCES** → sys_req_o.data, sys_req_o.rw, sys_req_o.stb; **SOURCES** → arbiter_nxt.wdata, arbiter_nxt.cmd
  - **evidence** — concurrent sys_req_o.* assignments and arbiter_comb process read core_req_i fields (e.g. sys_req_o.addr <= core_req_i.addr; arbiter_nxt.wdata <= core_req_i.data)

**`core_req_i.addr`** — neorv32_bus_amo_rmw · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the core request address unchanged to the system request address to address the system transaction.
  - **roles** — forwarded address; crosses entity boundary to system
  - **relationships** — **CARRIES** → sys_req_o.addr
  - **evidence** — sys_req_o.addr  <= core_req_i.addr

**`core_req_i.amo`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Indicates that the core request is an AMO; it gates the arbiter's transition into the AMO read state and is forwarded to sys_req_o.amo.
  - **roles** — AMO start qualifier; forwarded AMO flag
  - **relationships** — **GATES** → arbiter_nxt.state; **CARRIES** → sys_req_o.amo
  - **evidence** — if ... (core_req_i.amo = '1') ... in S_IDLE; sys_req_o.amo <= core_req_i.amo

**`core_req_i.amoop`** — neorv32_bus_amo_rmw · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Provides the AMO opcode that is captured into arbiter_nxt.cmd when AMO starts and forwarded to sys_req_o.amoop; its high bits are tested to qualify AMO operations.
  - **roles** — AMO opcode operand; captured as command; forwarded to system
  - **relationships** — **GATES** → arbiter_nxt.state; **CARRIES** → arbiter_nxt.cmd, sys_req_o.amoop
  - **evidence** — condition uses core_req_i.amoop(3 downto 2) in S_IDLE; arbiter_nxt.cmd <= core_req_i.amoop; sys_req_o.amoop <= core_req_i.amoop

**`core_req_i.ben`** — neorv32_bus_amo_rmw · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the byte-enable mask from the core request directly to the system request's ben field.
  - **roles** — byte-enable forwarder; carries control to system
  - **relationships** — **CARRIES** → sys_req_o.ben
  - **evidence** — sys_req_o.ben  <= core_req_i.ben

**`core_req_i.data`** — neorv32_bus_amo_rmw · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies write data that is captured into arbiter_nxt.wdata when an AMO starts and is forwarded to sys_req_o.data when no AMO write result is used.
  - **roles** — write operand; forwarded data; captured for AMO
  - **relationships** — **SOURCES** → arbiter_nxt.wdata; **CARRIES** → sys_req_o.data
  - **evidence** — arbiter_nxt.wdata <= core_req_i.data; sys_req_o.data uses core_req_i.data in its else branch

**`core_req_i.debug`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the core debug flag unchanged to the system request debug output.
  - **roles** — forwarded debug flag
  - **relationships** — **CARRIES** → sys_req_o.debug
  - **evidence** — sys_req_o.debug <= core_req_i.debug

**`core_req_i.fence`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the core fence flag unchanged to the system request fence field.
  - **roles** — forwarded fence flag
  - **relationships** — **CARRIES** → sys_req_o.fence
  - **evidence** — sys_req_o.fence <= core_req_i.fence

**`core_req_i.lock`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the core lock flag unchanged to the system request lock field.
  - **roles** — forwarded lock flag
  - **relationships** — **CARRIES** → sys_req_o.lock
  - **evidence** — sys_req_o.lock  <= core_req_i.lock

**`core_req_i.priv`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the core privilege field unchanged to the system request privilege output.
  - **roles** — forwarded privilege
  - **relationships** — **CARRIES** → sys_req_o.priv
  - **evidence** — sys_req_o.priv  <= core_req_i.priv

**`core_req_i.rw`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the core request read/write bit to the system request except during arbiter-driven write phases where sys_req_o.rw is forced to '1'.
  - **roles** — read/write operand; forwarded control
  - **relationships** — **SOURCES** → sys_req_o.rw
  - **evidence** — sys_req_o.rw <= '1' when (arbiter.state = S_WRITE) or (arbiter.state = S_WRITE_WAIT) else core_req_i.rw

**`core_req_i.src`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the request source field unchanged to sys_req_o.src for the outgoing system transaction.
  - **roles** — forwarded source field
  - **relationships** — **CARRIES** → sys_req_o.src
  - **evidence** — sys_req_o.src  <= core_req_i.src

**`core_req_i.stb`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Supplies the core strobe used both to gate AMO start in the arbiter FSM and as the fallback strobe value forwarded to the system request when not driving a write strobed by the arbiter.
  - **roles** — start condition; forwarded strobe
  - **relationships** — **GATES** → arbiter_nxt.state; **CARRIES** → sys_req_o.stb
  - **evidence** — if (core_req_i.stb = '1') in S_IDLE branch; sys_req_o.stb <= '1' when ... else core_req_i.stb

**`core_rsp_o`** — neorv32_bus_amo_rmw · `bus_rsp_t`
  - **functionality** — Exports response fields to the core; individual fields either forward sys_rsp_i values or report arbiter-captured data as defined per-field below.
  - **roles** — response output bundle; exports system/arbiter response
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — core_rsp_o.* concurrent assignments map system/arbiter values to the core

**`core_rsp_o.ack`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Drives core ack from sys_rsp_i.ack when arbiter is idle or in write-wait; otherwise drives '0' to suppress ack during AMO execution.
  - **roles** — forwarded ack; gated response
  - **relationships** — **DERIVES_FROM** → sys_rsp_i.ack
  - **evidence** — core_rsp_o.ack <= sys_rsp_i.ack when (arbiter.state = S_IDLE) or (arbiter.state = S_WRITE_WAIT) else '0'

**`core_rsp_o.data`** — neorv32_bus_amo_rmw · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the core with sys_rsp_i.data when arbiter is idle; otherwise supplies the arbiter-captured read data (arbiter.rdata), reporting the AMO read/result.
  - **roles** — response data mux; exports read or AMO result
  - **relationships** — **DERIVES_FROM** → sys_rsp_i.data, arbiter.rdata
  - **evidence** — core_rsp_o.data <= sys_rsp_i.data when (arbiter.state = S_IDLE) else arbiter.rdata

**`core_rsp_o.err`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards system error status to the core when arbiter is idle or in write-wait; otherwise drives '0'.
  - **roles** — forwarded error; gated response
  - **relationships** — **DERIVES_FROM** → sys_rsp_i.err
  - **evidence** — core_rsp_o.err <= sys_rsp_i.err when (arbiter.state = S_IDLE) or (arbiter.state = S_WRITE_WAIT) else '0'

**`rstn_i`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Asynchronous reset input that forces initial values in sequential processes and thus overrides normal arbiter and alu_res updates during reset.
  - **roles** — reset source; overrides register values at reset
  - **relationships** — **SEQUENCES** → arbiter; **SEQUENCES** → alu_res; **OVERRIDES** → arbiter; **OVERRIDES** → alu_res
  - **evidence** — if (rstn_i = '0') branches in arbiter_sync and amo_alu processes

**`sys_req_o`** — neorv32_bus_amo_rmw · `bus_req_t`
  - **functionality** — Exports a system-facing request assembled from core_req_i and AMO ALU result (alu_res) during write phases; individual fields are derived or forwarded as shown below.
  - **roles** — system request exporter; carries forwarded and computed fields
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — concurrent assignments to sys_req_o.* build and export the system request

**`sys_req_o.addr`** — neorv32_bus_amo_rmw · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the forwarded core request address out on the system request address field.
  - **roles** — exported address; forwarded from core
  - **relationships** — **CARRIES** → core_req_i.addr
  - **evidence** — sys_req_o.addr  <= core_req_i.addr

**`sys_req_o.amo`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the core AMO flag to the system request's amo field unchanged.
  - **roles** — forwarded AMO flag
  - **relationships** — **CARRIES** → core_req_i.amo
  - **evidence** — sys_req_o.amo   <= core_req_i.amo

**`sys_req_o.amoop`** — neorv32_bus_amo_rmw · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the core AMO opcode to the system request's amoop field unchanged.
  - **roles** — forwarded AMO opcode
  - **relationships** — **CARRIES** → core_req_i.amoop
  - **evidence** — sys_req_o.amoop <= core_req_i.amoop

**`sys_req_o.ben`** — neorv32_bus_amo_rmw · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the core's byte-enable mask to the system request ben field.
  - **roles** — exported byte-enable
  - **relationships** — **CARRIES** → core_req_i.ben
  - **evidence** — sys_req_o.ben  <= core_req_i.ben

**`sys_req_o.data`** — neorv32_bus_amo_rmw · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Sends ALU result (alu_res) during arbiter write phases, otherwise forwards core_req_i.data; the arbiter state determines which source is used.
  - **roles** — exported data; muxes ALU result and core data
  - **relationships** — **DERIVES_FROM** → alu_res, core_req_i.data
  - **evidence** — sys_req_o.data <= alu_res when (arbiter.state = S_WRITE) or (arbiter.state = S_WRITE_WAIT) else core_req_i.data

**`sys_req_o.debug`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the core debug flag to the system request.
  - **roles** — forwarded debug
  - **relationships** — **CARRIES** → core_req_i.debug
  - **evidence** — sys_req_o.debug <= core_req_i.debug

**`sys_req_o.fence`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the core fence flag unchanged to the system request fence field.
  - **roles** — forwarded fence flag
  - **relationships** — **CARRIES** → core_req_i.fence
  - **evidence** — sys_req_o.fence <= core_req_i.fence

**`sys_req_o.lock`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the core lock flag unchanged to the system request lock field.
  - **roles** — forwarded lock flag
  - **relationships** — **CARRIES** → core_req_i.lock
  - **evidence** — sys_req_o.lock  <= core_req_i.lock

**`sys_req_o.priv`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the core privilege bit to the system request.
  - **roles** — forwarded privilege
  - **relationships** — **CARRIES** → core_req_i.priv
  - **evidence** — sys_req_o.priv  <= core_req_i.priv

**`sys_req_o.rw`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forces write ('1') during arbiter write phases, otherwise forwards the core request's rw bit to the system.
  - **roles** — exported rw; overridden for AMO writes
  - **relationships** — **DERIVES_FROM** → core_req_i.rw
  - **evidence** — sys_req_o.rw <= '1' when (arbiter.state = S_WRITE) or (arbiter.state = S_WRITE_WAIT) else core_req_i.rw

**`sys_req_o.src`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Forwards the core request source field unchanged to the system request.
  - **roles** — forwarded source
  - **relationships** — **CARRIES** → core_req_i.src
  - **evidence** — sys_req_o.src   <= core_req_i.src

**`sys_req_o.stb`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Drives system strobe '1' during arbiter write state; otherwise forwards the core strobe value.
  - **roles** — exported strobe; write-phase assertor
  - **relationships** — **DERIVES_FROM** → core_req_i.stb
  - **evidence** — sys_req_o.stb <= '1' when (arbiter.state = S_WRITE) else core_req_i.stb

**`sys_rsp_i`** — neorv32_bus_amo_rmw · `bus_rsp_t`
  - **functionality** — Provides system response fields (ack, err, data) that are consumed to update arbiter next-state and forwarded to the core response outputs as appropriate.
  - **roles** — system response input; supplies ack/err/data to arbiter and core response logic
  - **relationships** — **SOURCES** → arbiter_nxt.rdata, core_rsp_o.data, core_rsp_o.err, core_rsp_o.ack; **GATES** → arbiter_nxt.state
  - **evidence** — arbiter_nxt.rdata <= sys_rsp_i.data and if (sys_rsp_i.ack = '1') branches in arbiter_comb; core_rsp_o.* use sys_rsp_i.* when arbiter.state = S_IDLE

**`sys_rsp_i.ack`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Signals completion from the system; it gates arbiter state transitions (S_READ_WAIT->S_EXECUTE and S_WRITE_WAIT->S_IDLE) and is forwarded to core_rsp_o.ack when appropriate.
  - **roles** — completion indicator; gates arbiter state progression; forwarded ack
  - **relationships** — **GATES** → arbiter_nxt.state; **SOURCES** → core_rsp_o.ack
  - **evidence** — if (sys_rsp_i.ack = '1') then arbiter_nxt.state <= S_EXECUTE (S_READ_WAIT) or <= S_IDLE (S_WRITE_WAIT); core_rsp_o.ack <= sys_rsp_i.ack when (arbiter.state = S_IDLE) or (arbiter.state = S_WRITE_WAIT)

**`sys_rsp_i.data`** — neorv32_bus_amo_rmw · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides read data from the system which is captured into arbiter_nxt.rdata in READ_WAIT and forwarded to the core when arbiter is idle.
  - **roles** — system read data; fed into arbiter next-data and core response
  - **relationships** — **SOURCES** → arbiter_nxt.rdata, core_rsp_o.data
  - **evidence** — arbiter_nxt.rdata <= sys_rsp_i.data in S_READ_WAIT; core_rsp_o.data uses sys_rsp_i.data when arbiter.state = S_IDLE

**`sys_rsp_i.err`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Provides the system error flag which is forwarded to the core response err output when arbiter is idle or in write-wait.
  - **roles** — forwarded error flag
  - **relationships** — **SOURCES** → core_rsp_o.err
  - **evidence** — core_rsp_o.err <= sys_rsp_i.err when (arbiter.state = S_IDLE) or (arbiter.state = S_WRITE_WAIT) else '0'

**`clk_i`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Supplies the rising edge that sequences the FSM (state) and the sc_fail register; used as the clock in both rvs_control and sc_result processes.
  - **roles** — clocking source; sequences state register; sequences sc_fail register
  - **relationships** — **SEQUENCES** → state, sc_fail
  - **evidence** — rvs_control and sc_result processes use rising_edge(clk_i) to update state and sc_fail (process headers and elsif rising_edge(clk_i)).

**`core_req_i`** — neorv32_bus_amo_rvs · `bus_req_t`
  - **functionality** — Provides the incoming bus request record; its fields are consumed by control logic and the whole record is forwarded to sys_req_o (then sys_req_o.stb may be modified).
  - **roles** — input request aggregate; supplies fields for control decisions; forwarded to sys_req_o
  - **relationships** — **SOURCES** → sys_req_o; **SOURCES** → sc_fail; **SOURCES** → rvso
  - **evidence** — sys_req_o <= core_req_i in bus_request; core_req_i fields appear in rvs_control and sc_result (conditions and RHS).

**`core_req_i.addr`** — neorv32_bus_amo_rvs · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the request address from the core request into the system request record; forwarded unchanged to sys_req_o.addr.
  - **roles** — forwarded field; carries address to sys_req_o
  - **relationships** — **SOURCES** → sys_req_o.addr
  - **evidence** — sys_req_o <= core_req_i (whole-record assignment) in bus_request process.

**`core_req_i.amo`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Supplies the AMO bit used to detect RVS-type atomic operations (drives rvso) and is forwarded into the system request record.
  - **roles** — AMO flag source; drives rvso generation; forwarded to sys_req_o
  - **relationships** — **SOURCES** → rvso; **SOURCES** → sys_req_o.amo
  - **evidence** — rvso <= '1' when (core_req_i.amo = '1') and ...; sys_req_o <= core_req_i copies the field.

**`core_req_i.amoop`** — neorv32_bus_amo_rvs · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Supplies AMO opcode bits used (bits 3 downto 2) to detect the RVS operation (drives rvso) and is forwarded into sys_req_o.amoop.
  - **roles** — AMO opcode source; slice consumed for rvso detection; forwarded to sys_req_o
  - **relationships** — **SLICES** → rvso; **SOURCES** → sys_req_o.amoop
  - **evidence** — rvso <= '1' when ... core_req_i.amoop(3 downto 2) = "10"; sys_req_o <= core_req_i forwards amoop.

**`core_req_i.ben`** — neorv32_bus_amo_rvs · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the core request byte-enable field into the system request record unchanged.
  - **roles** — forwarded field; carries byte-enable to sys_req_o
  - **relationships** — **SOURCES** → sys_req_o.ben
  - **evidence** — sys_req_o <= core_req_i (whole-record assignment) in bus_request process.

**`core_req_i.data`** — neorv32_bus_amo_rvs · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries core request data into the system request record; forwarded unchanged to sys_req_o.data.
  - **roles** — forwarded field; carries data to sys_req_o
  - **relationships** — **SOURCES** → sys_req_o.data
  - **evidence** — sys_req_o <= core_req_i (whole-record assignment) in bus_request process.

**`core_req_i.debug`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Forwards the debug indicator into sys_req_o unchanged.
  - **roles** — forwarded field; carries debug to sys_req_o
  - **relationships** — **SOURCES** → sys_req_o.debug
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`core_req_i.fence`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Forwards the fence field into sys_req_o unchanged.
  - **roles** — forwarded field; carries fence to sys_req_o
  - **relationships** — **SOURCES** → sys_req_o.fence
  - **evidence** — sys_req_o <= core_req_i (whole-record assignment) in bus_request process.

**`core_req_i.lock`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Forwards the lock field from the core request into the system request record unchanged.
  - **roles** — forwarded field; carries lock to sys_req_o
  - **relationships** — **SOURCES** → sys_req_o.lock
  - **evidence** — sys_req_o <= core_req_i (whole-record assignment) in bus_request process.

**`core_req_i.priv`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Forwards the privilege field into the system request record unchanged.
  - **roles** — forwarded field; carries privilege to sys_req_o
  - **relationships** — **SOURCES** → sys_req_o.priv
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`core_req_i.rw`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Indicates read or write and is used to decide RVS transitions; it gates FSM transitions, gates sys_req_o.stb modification, and participates in sc_fail computation.
  - **roles** — operation type control; governs state updates; influences sys_req_o.stb; feeds sc_fail logic
  - **relationships** — **GATES** → state; **SOURCES** → sys_req_o.stb; **SOURCES** → sc_fail
  - **evidence** — core_req_i.rw appears in rvs_control conditions, in bus_request guard and sc_result RHS (sc_fail <= ... core_req_i.rw ...).

**`core_req_i.src`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Forwards the request source field from core_req_i into sys_req_o.src unchanged.
  - **roles** — forwarded field; carries source to sys_req_o
  - **relationships** — **SOURCES** → sys_req_o.src
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`core_req_i.stb`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Supplies the transaction strobe; it is forwarded to sys_req_o.stb (possibly gated) and used to gate FSM transitions and sc_fail computation.
  - **roles** — control strobe; governs state updates; feeds sys_req_o.stb; feeds sc_fail logic
  - **relationships** — **SOURCES** → sys_req_o.stb; **GATES** → state; **SOURCES** → sc_fail
  - **evidence** — Used in rvs_control conditions, in sc_result RHS, and in bus_request to form sys_req_o.stb (sys_req_o <= core_req_i and sys_req_o.stb <= core_req_i.stb ...).

**`core_rsp_o`** — neorv32_bus_amo_rvs · `bus_rsp_t`
  - **functionality** — Exports the response record to the core; its fields are driven from sys_rsp_i and sc_fail (ack and data combine sc_fail).
  - **roles** — output response aggregate; reports system response and SC status
  - **relationships** — **EXPORTS** → _(none)_; **DERIVES_FROM** → sys_rsp_i.ack, sc_fail; **CARRIES** → sys_rsp_i.err
  - **evidence** — core_rsp_o.err/ack/data assignments at end of architecture assign from sys_rsp_i fields and sc_fail.

**`core_rsp_o.ack`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Drives the core ack output as the system ack OR the sc_fail register, so it reports ack or a store-conditional failure.
  - **roles** — response ack; conveys system ack or sc_fail
  - **relationships** — **DERIVES_FROM** → sys_rsp_i.ack, sc_fail
  - **evidence** — core_rsp_o.ack <= sys_rsp_i.ack or sc_fail; (concurrent assignment).

**`core_rsp_o.data`** — neorv32_bus_amo_rvs · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Constructs core response data from sys_rsp_i.data bits 31:1 and an LSB that is sys_rsp_i.data(0) OR sc_fail, reporting modified data when SC failed.
  - **roles** — response data output; aggregates system data and sc_fail LSB
  - **relationships** — **SLICES** → sys_rsp_i.data; **DERIVES_FROM** → sc_fail; **SLICES** → sys_rsp_i.data
  - **evidence** — core_rsp_o.data <= sys_rsp_i.data(31 downto 1) & (sys_rsp_i.data(0) or sc_fail); concurrent assignment.

**`core_rsp_o.err`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Propagates the system error flag directly to the core response err field unchanged.
  - **roles** — response error output; carries sys_rsp_i.err to core
  - **relationships** — **CARRIES** → sys_rsp_i.err
  - **evidence** — core_rsp_o.err <= sys_rsp_i.err; concurrent assignment.

**`rstn_i`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Supplies the synchronous/asynchronous reset that initializes the FSM (state) and sc_fail; used in the reset branches of rvs_control and sc_result.
  - **roles** — reset source; overrides registers on reset
  - **relationships** — **SEQUENCES** → state, sc_fail
  - **evidence** — if (rstn_i = '0') branches in rvs_control and sc_result assign state and sc_fail to reset values.

**`sys_req_o`** — neorv32_bus_amo_rvs · `bus_req_t`
  - **functionality** — Exports a system request built from the core request; the record is copied from core_req_i but sys_req_o.stb may be gated for RVS stores using state and rvso.
  - **roles** — output request aggregate; forwards core_req_i to system bus; strobe may be gated for RVS
  - **relationships** — **CARRIES** → core_req_i
  - **evidence** — sys_req_o <= core_req_i in bus_request, with sys_req_o.stb adjusted conditionally in the same process.

**`sys_req_o.addr`** — neorv32_bus_amo_rvs · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the copied address field from core_req_i into the system request output unchanged.
  - **roles** — forwarded field; carries address out
  - **relationships** — **CARRIES** → core_req_i.addr
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`sys_req_o.amo`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Carries the AMO bit from the core request to the system request unchanged.
  - **roles** — forwarded field; carries AMO to system
  - **relationships** — **CARRIES** → core_req_i.amo
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`sys_req_o.amoop`** — neorv32_bus_amo_rvs · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the AMO opcode field from core_req_i into sys_req_o unchanged.
  - **roles** — forwarded field; carries AMO opcode to system
  - **relationships** — **CARRIES** → core_req_i.amoop
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`sys_req_o.ben`** — neorv32_bus_amo_rvs · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Carries core_req_i.ben into the system request unchanged.
  - **roles** — forwarded field; carries byte-enable out
  - **relationships** — **CARRIES** → core_req_i.ben
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`sys_req_o.data`** — neorv32_bus_amo_rvs · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the data field from core_req_i into sys_req_o unchanged (subject to whole-record copy).
  - **roles** — forwarded field; carries data out
  - **relationships** — **CARRIES** → core_req_i.data
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`sys_req_o.debug`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Forwards core_req_i.debug into sys_req_o.debug unchanged.
  - **roles** — forwarded field; carries debug to system
  - **relationships** — **CARRIES** → core_req_i.debug
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`sys_req_o.fence`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Carries core_req_i.fence into the system request unchanged.
  - **roles** — forwarded field; carries fence to system
  - **relationships** — **CARRIES** → core_req_i.fence
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`sys_req_o.lock`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Carries core_req_i.lock into the system request unchanged.
  - **roles** — forwarded field; carries lock to system
  - **relationships** — **CARRIES** → core_req_i.lock
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`sys_req_o.priv`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Carries core_req_i.priv into the system request unchanged.
  - **roles** — forwarded field; carries priv to system
  - **relationships** — **CARRIES** → core_req_i.priv
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`sys_req_o.rw`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Carries the read/write flag from core_req_i into the system request unchanged.
  - **roles** — forwarded field; carries rw to system
  - **relationships** — **CARRIES** → core_req_i.rw
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`sys_req_o.src`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Forwards core_req_i.src into sys_req_o.src unchanged.
  - **roles** — forwarded field; carries src to system
  - **relationships** — **CARRIES** → core_req_i.src
  - **evidence** — sys_req_o <= core_req_i whole-record assignment in bus_request process.

**`sys_req_o.stb`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Drives the system strobe from core_req_i.stb, but when rvso and core_req_i.rw are '1' it gates the strobe with state(1) so only asserted in certain FSM states.
  - **roles** — output strobe; gated for RVS operations; reflects core_req_i.stb
  - **relationships** — **DERIVES_FROM** → core_req_i.stb, state, rvso, core_req_i.rw
  - **evidence** — bus_request process: if (rvso = '1') and (core_req_i.rw = '1') then sys_req_o.stb <= core_req_i.stb and state(1) else sys_req_o.stb <= core_req_i.stb.

**`sys_rsp_i`** — neorv32_bus_amo_rvs · `bus_rsp_t`
  - **functionality** — Provides the system response record; its fields feed the core response outputs, with data partially combined with sc_fail for the LSB.
  - **roles** — input response aggregate; supplies error/ack/data to core outputs
  - **relationships** — **SOURCES** → core_rsp_o.err; **SOURCES** → core_rsp_o.ack; **SLICES** → core_rsp_o.data; **SLICES** → core_rsp_o.data
  - **evidence** — core_rsp_o.err/ack/data assigned from sys_rsp_i fields at end of architecture.

**`sys_rsp_i.ack`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Supplies the system ack which is ORed with sc_fail to form core_rsp_o.ack.
  - **roles** — system ack source; contributes to core ack
  - **relationships** — **SOURCES** → core_rsp_o.ack
  - **evidence** — core_rsp_o.ack <= sys_rsp_i.ack or sc_fail; concurrent assignment.

**`sys_rsp_i.data`** — neorv32_bus_amo_rvs · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the system data; bits 31:1 are forwarded to core_rsp_o.data, and bit0 is combined with sc_fail for the core LSB.
  - **roles** — system data source; provides MSBs and LSB for core response
  - **relationships** — **SLICES** → core_rsp_o.data; **SLICES** → core_rsp_o.data
  - **evidence** — core_rsp_o.data <= sys_rsp_i.data(31 downto 1) & (sys_rsp_i.data(0) or sc_fail); concurrent assignment.

**`sys_rsp_i.err`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Supplies the system error flag which is passed directly to the core error output.
  - **roles** — system error source; propagated to core_rsp_o.err
  - **relationships** — **SOURCES** → core_rsp_o.err
  - **evidence** — core_rsp_o.err <= sys_rsp_i.err; concurrent assignment.

**`a_req_o`** — neorv32_bus_gateway · `bus_req_t`
  - **functionality** — Drives the A port request record from internal port_req(0); exports the selected request fields to external A interface.
  - **roles** — port A export; carries selected request
  - **relationships** — **CARRIES** → port_req; **EXPORTS** → _(none)_
  - **evidence** — concurrent mapping a_req_o <= port_req(0)

**`a_req_o.addr`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries address field from internal port_req(0) out to the A port.
  - **roles** — A address output; forwards selected address
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) concurrent whole-record assignment

**`a_req_o.amo`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards AMO bit from port_req(0) to the A external interface.
  - **roles** — A AMO output; forwards AMO flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) mapping

**`a_req_o.amoop`** — neorv32_bus_gateway · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards AMO opcode bits from port_req(0) to the A port.
  - **roles** — A AMO-opcode output; forwards opcode
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) concurrent assignment

**`a_req_o.ben`** — neorv32_bus_gateway · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards ben bits from port_req(0) to the external A port.
  - **roles** — A byte-enable output; forwards ben
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) concurrent assignment

**`a_req_o.data`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries data field from internal port_req(0) out to the A port.
  - **roles** — A data output; forwards selected data
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) concurrent mapping

**`a_req_o.debug`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards debug flag from port_req(0) to the A port.
  - **roles** — A debug output; forwards debug flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) concurrent assignment

**`a_req_o.fence`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards fence bit from port_req(0) to the A external interface.
  - **roles** — A fence output; forwards fence bit
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) concurrent assignment

**`a_req_o.lock`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Carries lock bit from port_req(0) to the external A port.
  - **roles** — A lock output; forwards lock flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) mapping

**`a_req_o.priv`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards priv bit from port_req(0) to the external A port.
  - **roles** — A privilege output; forwards priv flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) mapping

**`a_req_o.rw`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards rw flag from port_req(0) to the A external interface.
  - **roles** — A R/W output; forwards operation type
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) mapping

**`a_req_o.src`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards source id field from port_req(0) to the external A port.
  - **roles** — A source id output; forwards origin info
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) concurrent assignment

**`a_req_o.stb`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Carries the per-port stb (masked by port_sel) from port_req(0) to the external A port.
  - **roles** — A strobe output; valid signal to A port
  - **relationships** — **CARRIES** → port_req
  - **evidence** — a_req_o <= port_req(0) and port_req built in request process

**`a_rsp_i`** — neorv32_bus_gateway · `bus_rsp_t`
  - **functionality** — Receives the A port response record and supplies it to internal port_rsp(0) for aggregation into int_rsp.
  - **roles** — A response input; feeds port_rsp(0)
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — concurrent mapping port_rsp(0) <= a_rsp_i

**`a_rsp_i.ack`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Supplies ack from external A response into port_rsp(0) so the response aggregator can OR it into int_rsp.ack.
  - **roles** — A ack input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(0) <= a_rsp_i and response process ORs port_rsp(i).ack into tmp_v.ack

**`a_rsp_i.data`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies data from external A response into port_rsp(0) for OR aggregation into int_rsp.data.
  - **roles** — A data input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(0) <= a_rsp_i and response process ORs port_rsp(i).data

**`a_rsp_i.err`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Supplies err from external A response into port_rsp(0) for OR-aggregation into int_rsp.err.
  - **roles** — A error input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(0) <= a_rsp_i and response process ORs port_rsp(i).err

**`b_req_o`** — neorv32_bus_gateway · `bus_req_t`
  - **functionality** — Drives the B port request record from internal port_req(1); exports the selected request fields to external B interface.
  - **roles** — port B export; carries selected request
  - **relationships** — **CARRIES** → port_req
  - **evidence** — concurrent mapping b_req_o <= port_req(1)

**`b_req_o.addr`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries address field from internal port_req(1) out to the B port.
  - **roles** — B address output; forwards selected address
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) concurrent whole-record assignment

**`b_req_o.amo`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards AMO bit from port_req(1) to the external B interface.
  - **roles** — B AMO output; forwards AMO flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) mapping

**`b_req_o.amoop`** — neorv32_bus_gateway · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards AMO opcode bits from port_req(1) to the B port.
  - **roles** — B AMO-opcode output; forwards opcode
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) concurrent assignment

**`b_req_o.ben`** — neorv32_bus_gateway · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards ben bits from port_req(1) to the external B port.
  - **roles** — B byte-enable output; forwards ben
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) concurrent assignment

**`b_req_o.data`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries data field from internal port_req(1) out to the B port.
  - **roles** — B data output; forwards selected data
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) mapping

**`b_req_o.debug`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards debug flag from port_req(1) to the B port.
  - **roles** — B debug output; forwards debug flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) concurrent assignment

**`b_req_o.fence`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards fence bit from port_req(1) to the B external interface.
  - **roles** — B fence output; forwards fence bit
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) concurrent assignment

**`b_req_o.lock`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Carries lock bit from port_req(1) to the external B port.
  - **roles** — B lock output; forwards lock flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) mapping

**`b_req_o.priv`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards priv bit from port_req(1) to the external B port.
  - **roles** — B privilege output; forwards priv flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) mapping

**`b_req_o.rw`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards rw flag from port_req(1) to the B external interface.
  - **roles** — B R/W output; forwards operation type
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) mapping

**`b_req_o.src`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards source id field from port_req(1) to the external B port.
  - **roles** — B source id output; forwards origin info
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) concurrent assignment

**`b_req_o.stb`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Carries the per-port stb (masked by port_sel) from port_req(1) to the external B port.
  - **roles** — B strobe output; valid signal to B port
  - **relationships** — **CARRIES** → port_req
  - **evidence** — b_req_o <= port_req(1) and port_req built in request process

**`b_rsp_i`** — neorv32_bus_gateway · `bus_rsp_t`
  - **functionality** — Receives the B port response record and supplies it to internal port_rsp(1) for aggregation into int_rsp.
  - **roles** — B response input; feeds port_rsp(1)
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — concurrent mapping port_rsp(1) <= b_rsp_i

**`b_rsp_i.ack`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Supplies ack from external B response into port_rsp(1) for OR aggregation into int_rsp.ack.
  - **roles** — B ack input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(1) <= b_rsp_i and response process ORs ack

**`b_rsp_i.data`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies data from external B response into port_rsp(1) for OR aggregation into int_rsp.data.
  - **roles** — B data input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(1) <= b_rsp_i and response process ORs data

**`b_rsp_i.err`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Supplies err from external B response into port_rsp(1) for aggregation into int_rsp.err.
  - **roles** — B error input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(1) <= b_rsp_i and response process ORs err

**`c_req_o`** — neorv32_bus_gateway · `bus_req_t`
  - **functionality** — Drives the C port request record from internal port_req(2); exports the selected request fields to external C interface.
  - **roles** — port C export; carries selected request
  - **relationships** — **CARRIES** → port_req
  - **evidence** — concurrent mapping c_req_o <= port_req(2)

**`c_req_o.addr`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries address field from internal port_req(2) out to the C port.
  - **roles** — C address output; forwards selected address
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) concurrent whole-record assignment

**`c_req_o.amo`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards AMO bit from port_req(2) to the external C interface.
  - **roles** — C AMO output; forwards AMO flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) mapping

**`c_req_o.amoop`** — neorv32_bus_gateway · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards AMO opcode bits from port_req(2) to the C port.
  - **roles** — C AMO-opcode output; forwards opcode
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) concurrent assignment

**`c_req_o.ben`** — neorv32_bus_gateway · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards ben bits from port_req(2) to the external C port.
  - **roles** — C byte-enable output; forwards ben
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) concurrent assignment

**`c_req_o.data`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries data field from internal port_req(2) out to the C port.
  - **roles** — C data output; forwards selected data
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) mapping

**`c_req_o.debug`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards debug flag from port_req(2) to the C port.
  - **roles** — C debug output; forwards debug flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) concurrent assignment

**`c_req_o.fence`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards fence bit from port_req(2) to the C external interface.
  - **roles** — C fence output; forwards fence bit
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) concurrent assignment

**`c_req_o.lock`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Carries lock bit from port_req(2) to the external C port.
  - **roles** — C lock output; forwards lock flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) mapping

**`c_req_o.priv`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards priv bit from port_req(2) to the external C port.
  - **roles** — C privilege output; forwards priv flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) mapping

**`c_req_o.rw`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards rw flag from port_req(2) to the C external interface.
  - **roles** — C R/W output; forwards operation type
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) mapping

**`c_req_o.src`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards source id field from port_req(2) to the external C port.
  - **roles** — C source id output; forwards origin info
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) concurrent assignment

**`c_req_o.stb`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Carries the per-port stb (masked by port_sel) from port_req(2) to the external C port.
  - **roles** — C strobe output; valid signal to C port
  - **relationships** — **CARRIES** → port_req
  - **evidence** — c_req_o <= port_req(2) and port_req constructed in request process

**`c_rsp_i`** — neorv32_bus_gateway · `bus_rsp_t`
  - **functionality** — Receives the C port response record and supplies it to internal port_rsp(2) for aggregation into int_rsp.
  - **roles** — C response input; feeds port_rsp(2)
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — concurrent mapping port_rsp(2) <= c_rsp_i

**`c_rsp_i.ack`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Supplies ack from external C response into port_rsp(2) for OR aggregation into int_rsp.ack.
  - **roles** — C ack input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(2) <= c_rsp_i and response process ORs ack

**`c_rsp_i.data`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies data from external C response into port_rsp(2) for OR aggregation into int_rsp.data.
  - **roles** — C data input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(2) <= c_rsp_i and response process ORs data

**`c_rsp_i.err`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Supplies err from external C response into port_rsp(2) for aggregation into int_rsp.err.
  - **roles** — C error input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(2) <= c_rsp_i and response process ORs err

**`clk_i`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Provides the clock edge that sequences updates of the keeper registers in the bus_monitor process; drives rising_edge(clk_i) that captures keeper fields.
  - **roles** — clock source; sequences keeper registers; timing supply
  - **relationships** — **SEQUENCES** → keeper.busy; **SEQUENCES** → keeper.lock; **SEQUENCES** → keeper.cnt; **SEQUENCES** → keeper.err; **SEQUENCES** → keeper.halt
  - **evidence** — bus_monitor process sensitivity and rising_edge(clk_i) that assigns keeper fields

**`req_i`** — neorv32_bus_gateway · `bus_req_t`
  - **functionality** — Supplies the incoming request record used to build per-port port_req entries, to form address-decode conditions (port_sel), and to update keeper status on capture.
  - **roles** — request source; feeds port_req; controls keeper behaviour
  - **relationships** — **SOURCES** → port_req; **SOURCES** → keeper.busy; **SOURCES** → keeper.lock; **GATES** → port_sel
  - **evidence** — request process assigns port_req <= req_i and bus_monitor captures keeper fields from req_i; port_sel uses req_i.addr in comparisons

**`req_i.addr`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the 32-bit address used in equality comparisons with A_BASE/B_BASE/C_BASE to set port_sel bits for destination selection.
  - **roles** — address operand; drives address decode; selects target port
  - **relationships** — **CONSTRAINS** → port_sel
  - **evidence** — concurrent assignments port_sel(0..2) use req_i.addr(31 downto a_lo_c/b_lo_c/c_lo_c) = A_BASE/B_BASE/C_BASE

**`req_i.amo`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards the atomic (AMO) flag from req_i into port_req so downstream logic sees AMO requests.
  - **roles** — carries AMO flag; forwarded to ports
  - **relationships** — **SOURCES** → port_req
  - **evidence** — request process whole-record assignment port_req(i) <= req_i

**`req_i.amoop`** — neorv32_bus_gateway · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the AMO opcode bits from req_i into port_req so the selected port receives AMO operation code.
  - **roles** — carries AMO opcode; forwarded to ports
  - **relationships** — **SOURCES** → port_req
  - **evidence** — request process assigns port_req(i) <= req_i

**`req_i.ben`** — neorv32_bus_gateway · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards byte-enable bits from the incoming request into port_req so downstream ports receive the same ben value.
  - **roles** — carries byte-enable; forwarded to ports
  - **relationships** — **SOURCES** → port_req
  - **evidence** — request process whole-record assignment port_req(i) <= req_i

**`req_i.data`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the request data into the internal port_req entries when a request is propagated, so data reaches the selected external port output.
  - **roles** — carries request data; forwarded to ports
  - **relationships** — **SOURCES** → port_req
  - **evidence** — request process assigns port_req(i) <= req_i when port enabled

**`req_i.debug`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards the debug bit from the incoming request into port_req for delivery to the selected port.
  - **roles** — carries debug flag; forwarded to ports
  - **relationships** — **SOURCES** → port_req
  - **evidence** — request process assigns port_req(i) <= req_i

**`req_i.fence`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards fence bit from incoming request into port_req so downstream ports receive fence semantics.
  - **roles** — carries fence flag; forwarded to ports
  - **relationships** — **SOURCES** → port_req
  - **evidence** — request process whole-record assignment port_req(i) <= req_i

**`req_i.lock`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Supplies the lock bit that is captured into keeper.lock when a request starts and is compared with keeper.lock to decide release of busy.
  - **roles** — carries lock flag; feeds keeper.lock; compares for release
  - **relationships** — **SOURCES** → keeper.lock; **CONSTRAINS** → keeper.busy
  - **evidence** — keeper.lock <= req_i.lock in bus_monitor; req_i.lock compared in condition ((keeper.lock='1') and (req_i.lock='0'))

**`req_i.priv`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards the priv bit from the incoming request into port_req so downstream ports receive privilege info.
  - **roles** — carries privilege flag; forwarded to ports
  - **relationships** — **SOURCES** → port_req
  - **evidence** — request process whole-record assignment port_req(i) <= req_i

**`req_i.rw`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards the rw bit from the incoming request into port_req so downstream ports see the operation type.
  - **roles** — carries R/W flag; forwarded to ports
  - **relationships** — **SOURCES** → port_req
  - **evidence** — request process whole-record assignment port_req(i) <= req_i

**`req_i.src`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards the source field from req_i into port_req so the selected port receives the request origin information.
  - **roles** — carries source id; forwarded to ports
  - **relationships** — **SOURCES** → port_req
  - **evidence** — request process assigns port_req(i) <= req_i

**`req_i.stb`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Used both to gate per-port stb (combined with port_sel) when forming port_req.stb and to start keeper.busy when a new request arrives.
  - **roles** — gates per-port valid; triggers keeper capture
  - **relationships** — **GATES** → port_req; **SOURCES** → keeper.busy
  - **evidence** — port_req(i).stb <= port_sel(i) and req_i.stb; keeper.busy <= req_i.stb in bus_monitor process

**`rsp_o`** — neorv32_bus_gateway · `bus_rsp_t`
  - **functionality** — Exports the combined internal response (int_rsp) and keeper error status to the entity output; provides the aggregated response record to the outside.
  - **roles** — response export; reports internal response and error
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — concurrent assignments rsp_o.* <= int_rsp.* and OR with keeper.err drive outputs

**`rsp_o.ack`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Outputs acknowledgement formed as logical OR of int_rsp.ack and keeper.err so external responder sees ack or error.
  - **roles** — response ack output; reports ACK or error
  - **relationships** — **DERIVES_FROM** → int_rsp.ack, keeper.err
  - **evidence** — rsp_o.ack <= int_rsp.ack or keeper.err concurrent assignment

**`rsp_o.data`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the aggregated response data from internal int_rsp.data directly to the external response port.
  - **roles** — response data output; carries combined response data
  - **relationships** — **CARRIES** → int_rsp.data
  - **evidence** — rsp_o.data <= int_rsp.data concurrent assignment

**`rsp_o.err`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Outputs error as logical OR of int_rsp.err and keeper.err so external view reflects either internal error or keeper timeout.
  - **roles** — response error output; reports error status
  - **relationships** — **DERIVES_FROM** → int_rsp.err, keeper.err
  - **evidence** — rsp_o.err <= int_rsp.err or keeper.err concurrent assignment

**`rstn_i`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Provides active-low asynchronous reset that initializes all keeper fields in bus_monitor reset branch; forces keeper.* to defined values on rstn_i='0'.
  - **roles** — async reset; initialises keeper registers; timing control
  - **relationships** — **SEQUENCES** → keeper.busy; **SEQUENCES** → keeper.lock; **SEQUENCES** → keeper.cnt; **SEQUENCES** → keeper.err; **SEQUENCES** → keeper.halt
  - **evidence** — if (rstn_i = '0') branch at start of bus_monitor process

**`x_req_o`** — neorv32_bus_gateway · `bus_req_t`
  - **functionality** — Drives the fallback X port request record from internal port_req(3) when no other port matches; exports selected request fields to external X interface.
  - **roles** — fallback port export; carries request when others disabled
  - **relationships** — **CARRIES** → port_req
  - **evidence** — concurrent mapping x_req_o <= port_req(3)

**`x_req_o.addr`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries address field from internal port_req(3) out to the X port.
  - **roles** — X address output; forwards selected address
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) concurrent whole-record assignment

**`x_req_o.amo`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards AMO bit from port_req(3) to the external X interface.
  - **roles** — X AMO output; forwards AMO flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) mapping

**`x_req_o.amoop`** — neorv32_bus_gateway · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards AMO opcode bits from port_req(3) to the X port.
  - **roles** — X AMO-opcode output; forwards opcode
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) concurrent assignment

**`x_req_o.ben`** — neorv32_bus_gateway · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards ben bits from port_req(3) to the external X port.
  - **roles** — X byte-enable output; forwards ben
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) concurrent assignment

**`x_req_o.data`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries data field from internal port_req(3) out to the X port.
  - **roles** — X data output; forwards selected data
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) mapping

**`x_req_o.debug`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards debug flag from port_req(3) to the X port.
  - **roles** — X debug output; forwards debug flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) concurrent assignment

**`x_req_o.fence`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards fence bit from port_req(3) to the X external interface.
  - **roles** — X fence output; forwards fence bit
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) concurrent assignment

**`x_req_o.lock`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Carries lock bit from port_req(3) to the external X port.
  - **roles** — X lock output; forwards lock flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) mapping

**`x_req_o.priv`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards priv bit from port_req(3) to the external X port.
  - **roles** — X privilege output; forwards priv flag
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) mapping

**`x_req_o.rw`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards rw flag from port_req(3) to the X external interface.
  - **roles** — X R/W output; forwards operation type
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) mapping

**`x_req_o.src`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Forwards source id field from port_req(3) to the external X port.
  - **roles** — X source id output; forwards origin info
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) concurrent assignment

**`x_req_o.stb`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Carries the per-port stb (masked by port_sel) from port_req(3) to the external X port.
  - **roles** — X strobe output; valid signal to X port
  - **relationships** — **CARRIES** → port_req
  - **evidence** — x_req_o <= port_req(3) and port_req built in request process

**`x_rsp_i`** — neorv32_bus_gateway · `bus_rsp_t`
  - **functionality** — Receives the X port response record and supplies it to internal port_rsp(3) for aggregation into int_rsp.
  - **roles** — X response input; feeds port_rsp(3)
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — concurrent mapping port_rsp(3) <= x_rsp_i

**`x_rsp_i.ack`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Supplies ack from external X response into port_rsp(3) for OR aggregation into int_rsp.ack.
  - **roles** — X ack input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(3) <= x_rsp_i and response process ORs ack

**`x_rsp_i.data`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies data from external X response into port_rsp(3) for OR aggregation into int_rsp.data.
  - **roles** — X data input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(3) <= x_rsp_i and response process ORs data

**`x_rsp_i.err`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Supplies err from external X response into port_rsp(3) for aggregation into int_rsp.err.
  - **roles** — X error input; feeds aggregator
  - **relationships** — **SOURCES** → port_rsp
  - **evidence** — port_rsp(3) <= x_rsp_i and response process ORs err

**`clk_i`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the clock input to the instantiated neorv32_bus_reg instance via port map so that the register block can sequence its internal behavior.
  - **roles** — clock input; connects to instantiated register
  - **relationships** — **SOURCES** → neorv32_bus_reg_inst.clk_i
  - **evidence** — component port map: clk_i => clk_i in neorv32_bus_reg_inst port map

**`dev_00_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Exports the internal dev_req(0) record to device 0 by assigning dev_00_req_o <= dev_req(0) in concurrent statements, carrying the request fields outwards.
  - **roles** — device 0 request exporter; carries internal dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is the address field of dev_00_req_o and is driven by the corresponding field of dev_req(0) via the whole-record concurrent assignment.
  - **roles** — address output field; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is the AMO indicator forwarded to device 0 as part of the whole dev_00_req_o <= dev_req(0) assignment.
  - **roles** — AMO flag output; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the AMO operation code from dev_req(0) to device 0 as part of the whole-record concurrent assignment.
  - **roles** — AMO opcode output; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Is the byte-enable field exported to device 0 as part of the whole dev_00_req_o <= dev_req(0) assignment.
  - **roles** — byte-enable output field; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is the data field of dev_00_req_o and is forwarded from dev_req(0) by the concurrent whole-record assignment.
  - **roles** — data output field; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is the debug bit forwarded to device 0 by the whole-record assignment from dev_req(0) to dev_00_req_o.
  - **roles** — debug flag output; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is included in the whole dev_00_req_o <= dev_req(0) assignment and thus forwarded to device 0.
  - **roles** — fence flag output; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from dev_req(0) to the external dev_00_req_o.lock field by the whole-record assignment.
  - **roles** — lock flag output; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from dev_req(0) to device 0 as part of the whole-record export dev_00_req_o <= dev_req(0).
  - **roles** — privilege flag output; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the read/write bit from internal dev_req(0) out to device 0 via the concurrent assignment.
  - **roles** — rw output field; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the source field from dev_req(0) to the external device 0 port via the whole-record dev_00_req_o <= dev_req(0) assignment.
  - **roles** — source output field; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is the strobe field exported to device 0 by carrying the strobe value from dev_req(0) through the whole-record concurrent assignment.
  - **roles** — strobe output field; carried from dev_req(0)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_00_req_o <= dev_req(0)

**`dev_00_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies device 0's response record into the internal dev_rsp(0) entry by the concurrent assignment dev_rsp(0) <= dev_00_rsp_i.
  - **roles** — device response input; feeds internal dev_rsp(0)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(0) <= dev_00_rsp_i

**`dev_00_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is the ack bit of device 0's response and is copied into dev_rsp(0) via the concurrent assignment dev_rsp(0) <= dev_00_rsp_i.
  - **roles** — ack input field; supplies dev_rsp(0)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(0) <= dev_00_rsp_i

**`dev_00_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is the data field of device 0's response and is forwarded into dev_rsp(0) by the concurrent assignment dev_rsp(0) <= dev_00_rsp_i.
  - **roles** — response data input; supplies dev_rsp(0)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(0) <= dev_00_rsp_i

**`dev_00_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is the error bit of device 0's response and is copied into the internal dev_rsp(0) by the concurrent assignment.
  - **roles** — error input field; supplies dev_rsp(0)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(0) <= dev_00_rsp_i

**`dev_01_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Exports the internal dev_req(1) record to device 1 via the concurrent assignment dev_01_req_o <= dev_req(1).
  - **roles** — device 1 request exporter; carries internal dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the address field from dev_req(1) to the external dev_01_req_o port via the whole-record assignment.
  - **roles** — address output field; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the AMO flag from dev_req(1) to the external dev_01_req_o port as part of the whole-record assignment.
  - **roles** — AMO flag output; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the AMO opcode field from dev_req(1) to device 1 via the whole-record concurrent assignment.
  - **roles** — AMO opcode output; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Is forwarded from dev_req(1) to dev_01_req_o as part of the whole-record concurrent assignment.
  - **roles** — byte-enable output field; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the data field from internal dev_req(1) out to device 1 by the concurrent whole-record assignment.
  - **roles** — data output field; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from internal dev_req(1) to the external dev_01_req_o debug field via the whole-record assignment.
  - **roles** — debug flag output; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is included in the whole dev_01_req_o <= dev_req(1) assignment and thus forwarded to device 1.
  - **roles** — fence flag output; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from internal dev_req(1) to the external dev_01_req_o.lock field by the whole-record assignment.
  - **roles** — lock flag output; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from dev_req(1) to dev_01_req_o as part of the concurrent whole-record assignment.
  - **roles** — privilege flag output; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the read/write bit from dev_req(1) to the external dev_01_req_o port as part of the whole-record assignment.
  - **roles** — rw output field; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source field from internal dev_req(1) to the external device 1 port via the whole-record assignment.
  - **roles** — source output field; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the strobe field from dev_req(1) out to device 1 via the whole-record assignment dev_01_req_o <= dev_req(1).
  - **roles** — strobe output field; carried from dev_req(1)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_01_req_o <= dev_req(1)

**`dev_01_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies the device 1 response record into the internal dev_rsp(1) entry via the concurrent assignment dev_rsp(1) <= dev_01_rsp_i.
  - **roles** — device response input; feeds internal dev_rsp(1)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(1) <= dev_01_rsp_i

**`dev_01_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is the ack bit of device 1's response and is copied into dev_rsp(1) by the concurrent assignment.
  - **roles** — ack input field; supplies dev_rsp(1)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(1) <= dev_01_rsp_i

**`dev_01_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is the data field of device 1's response and is copied into dev_rsp(1) by the concurrent assignment dev_rsp(1) <= dev_01_rsp_i.
  - **roles** — response data input; supplies dev_rsp(1)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(1) <= dev_01_rsp_i

**`dev_01_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is the error bit of device 1's response and is forwarded into dev_rsp(1) via the concurrent assignment.
  - **roles** — error input field; supplies dev_rsp(1)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(1) <= dev_01_rsp_i

**`dev_02_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Exports the internal dev_req(2) record to device 2 via the concurrent assignment dev_02_req_o <= dev_req(2).
  - **roles** — device 2 request exporter; carries internal dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is forwarded from dev_req(2) to dev_02_req_o as part of the whole-record concurrent assignment.
  - **roles** — address output field; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded as part of dev_02_req_o <= dev_req(2), carrying the AMO indicator to device 2.
  - **roles** — AMO flag output; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Carries the AMO operation code from dev_req(2) to the external port via the whole-record assignment.
  - **roles** — AMO opcode output; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Is forwarded from dev_req(2) to the external dev_02_req_o port as part of the whole-record assignment.
  - **roles** — byte-enable output field; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the data field from internal dev_req(2) to the external port via the whole-record assignment.
  - **roles** — data output field; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from dev_req(2) to dev_02_req_o.debug via the whole-record concurrent assignment.
  - **roles** — debug flag output; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is included in the whole dev_02_req_o <= dev_req(2) assignment and is forwarded to device 2.
  - **roles** — fence flag output; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock bit from dev_req(2) to the external dev_02_req_o.lock field by whole-record assignment.
  - **roles** — lock flag output; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded to device 2 as part of the whole dev_02_req_o <= dev_req(2) assignment, carrying the privilege flag.
  - **roles** — privilege flag output; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the read/write bit from dev_req(2) to device 2 via the whole-record assignment dev_02_req_o <= dev_req(2).
  - **roles** — rw output field; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from internal dev_req(2) to the external dev_02_req_o port by the whole-record assignment.
  - **roles** — source output field; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is carried from dev_req(2) to the external device 2 port via the whole-record concurrent assignment.
  - **roles** — strobe output field; carried from dev_req(2)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_02_req_o <= dev_req(2)

**`dev_02_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies the device 2 response record into internal dev_rsp(2) by the concurrent assignment dev_rsp(2) <= dev_02_rsp_i.
  - **roles** — device response input; feeds internal dev_rsp(2)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(2) <= dev_02_rsp_i

**`dev_02_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is copied into dev_rsp(2) as the ack bit by the concurrent assignment from dev_02_rsp_i.
  - **roles** — ack input field; supplies dev_rsp(2)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(2) <= dev_02_rsp_i

**`dev_02_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is the response data field from device 2 and is forwarded into dev_rsp(2) by the concurrent assignment.
  - **roles** — response data input; supplies dev_rsp(2)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(2) <= dev_02_rsp_i

**`dev_02_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded into the internal dev_rsp(2).err field via the concurrent assignment dev_rsp(2) <= dev_02_rsp_i.
  - **roles** — error input field; supplies dev_rsp(2)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(2) <= dev_02_rsp_i

**`dev_03_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Exports the internal dev_req(3) record to device 3 by the concurrent assignment dev_03_req_o <= dev_req(3).
  - **roles** — device 3 request exporter; carries internal dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is forwarded from dev_req(3) to dev_03_req_o.addr via the whole-record concurrent assignment.
  - **roles** — address output field; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from dev_req(3) to dev_03_req_o as part of the whole-record assignment, carrying the AMO indicator.
  - **roles** — AMO flag output; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Carries the AMO opcode from internal dev_req(3) to the external dev_03_req_o port via the whole-record assignment.
  - **roles** — AMO opcode output; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Is forwarded to device 3 as part of the whole dev_03_req_o <= dev_req(3) assignment, carrying the byte-enable field.
  - **roles** — byte-enable output field; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the data field from internal dev_req(3) to the external port via the whole-record assignment dev_03_req_o <= dev_req(3).
  - **roles** — data output field; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded to device 3 from dev_req(3) by the whole-record concurrent assignment.
  - **roles** — debug flag output; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded to device 3 as part of dev_03_req_o <= dev_req(3) whole-record assignment.
  - **roles** — fence flag output; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock bit from dev_req(3) to the external dev_03_req_o.lock field as part of the whole-record assignment.
  - **roles** — lock flag output; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from dev_req(3) to device 3 as part of dev_03_req_o <= dev_req(3).
  - **roles** — privilege flag output; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the rw bit from dev_req(3) to the external dev_03_req_o port via the whole-record assignment.
  - **roles** — rw output field; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source field from internal dev_req(3) to the external port via the whole-record assignment.
  - **roles** — source output field; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is carried from internal dev_req(3) to the external dev_03_req_o.stb field by the whole-record assignment.
  - **roles** — strobe output field; carried from dev_req(3)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_03_req_o <= dev_req(3)

**`dev_03_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies device 3's response into the internal dev_rsp(3) entry via the concurrent assignment dev_rsp(3) <= dev_03_rsp_i.
  - **roles** — device response input; feeds internal dev_rsp(3)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(3) <= dev_03_rsp_i

**`dev_03_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is copied into dev_rsp(3).ack via the concurrent assignment from dev_03_rsp_i.
  - **roles** — ack input field; supplies dev_rsp(3)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(3) <= dev_03_rsp_i

**`dev_03_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is the response data from device 3 and is forwarded into dev_rsp(3) by the concurrent assignment.
  - **roles** — response data input; supplies dev_rsp(3)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(3) <= dev_03_rsp_i

**`dev_03_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded into dev_rsp(3).err by the concurrent assignment dev_rsp(3) <= dev_03_rsp_i.
  - **roles** — error input field; supplies dev_rsp(3)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(3) <= dev_03_rsp_i

**`dev_04_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Exports dev_req(4) to device 4 via the concurrent assignment dev_04_req_o <= dev_req(4).
  - **roles** — device 4 request exporter; carries internal dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the address field from dev_req(4) to dev_04_req_o via the whole-record assignment.
  - **roles** — address output field; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded to device 4 as part of dev_04_req_o <= dev_req(4), carrying the AMO indicator.
  - **roles** — AMO flag output; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Carries the AMO opcode from dev_req(4) to the external port as part of the whole-record assignment.
  - **roles** — AMO opcode output; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Is forwarded to device 4 as part of dev_04_req_o <= dev_req(4), carrying the byte-enable field.
  - **roles** — byte-enable output field; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is forwarded from dev_req(4) to dev_04_req_o.data as part of the whole dev_04_req_o <= dev_req(4) assignment.
  - **roles** — data output field; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from internal dev_req(4) to dev_04_req_o.debug via the whole-record assignment dev_04_req_o <= dev_req(4).
  - **roles** — debug flag output; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is included in the whole dev_04_req_o <= dev_req(4) assignment and thus forwarded to device 4.
  - **roles** — fence flag output; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from internal dev_req(4) to the external dev_04_req_o.lock field by the whole-record assignment.
  - **roles** — lock flag output; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is passed through from dev_req(4) to dev_04_req_o in the whole-record concurrent assignment.
  - **roles** — privilege flag output; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the rw bit from dev_req(4) out to device 4 via the whole-record assignment.
  - **roles** — rw output field; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source field from internal dev_req(4) to the external dev_04_req_o port as part of the whole-record assignment.
  - **roles** — source output field; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the strobe bit from internal dev_req(4) to the external dev_04_req_o port via the whole-record assignment.
  - **roles** — strobe output field; carried from dev_req(4)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_04_req_o <= dev_req(4)

**`dev_04_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies device 4's response record into the internal dev_rsp(4) entry by the concurrent assignment dev_rsp(4) <= dev_04_rsp_i.
  - **roles** — device response input; feeds internal dev_rsp(4)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(4) <= dev_04_rsp_i

**`dev_04_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is copied into dev_rsp(4).ack via the concurrent assignment from dev_04_rsp_i.
  - **roles** — ack input field; supplies dev_rsp(4)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(4) <= dev_04_rsp_i

**`dev_04_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is the response data from device 4 and is forwarded into dev_rsp(4) by the concurrent assignment.
  - **roles** — response data input; supplies dev_rsp(4)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(4) <= dev_04_rsp_i

**`dev_04_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded into dev_rsp(4).err by the concurrent assignment dev_rsp(4) <= dev_04_rsp_i.
  - **roles** — error input field; supplies dev_rsp(4)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(4) <= dev_04_rsp_i

**`dev_05_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Exports internal dev_req(5) to device 5 via the concurrent assignment dev_05_req_o <= dev_req(5).
  - **roles** — device 5 request exporter; carries internal dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is forwarded from dev_req(5) to dev_05_req_o.addr as part of the whole-record concurrent assignment.
  - **roles** — address output field; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the AMO indicator from dev_req(5) to the external port as part of the whole-record assignment.
  - **roles** — AMO flag output; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the AMO opcode from internal dev_req(5) to the external dev_05_req_o port via whole-record assignment.
  - **roles** — AMO opcode output; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Is forwarded to device 5 as part of dev_05_req_o <= dev_req(5), carrying the byte-enable field.
  - **roles** — byte-enable output field; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is carried from internal dev_req(5) to the external dev_05_req_o.data field via the whole-record assignment.
  - **roles** — data output field; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded to device 5 as part of the whole dev_05_req_o <= dev_req(5) assignment.
  - **roles** — debug flag output; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is included in the whole dev_05_req_o <= dev_req(5) assignment and forwarded to device 5.
  - **roles** — fence flag output; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from dev_req(5) to device 5 by the whole dev_05_req_o <= dev_req(5) assignment.
  - **roles** — lock flag output; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded from dev_req(5) to dev_05_req_o.priv by the whole-record assignment dev_05_req_o <= dev_req(5).
  - **roles** — privilege flag output; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the read/write flag from internal dev_req(5) to device 5 via the whole-record concurrent assignment.
  - **roles** — rw output field; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source field from dev_req(5) to the external device 5 port as part of the whole-record assignment.
  - **roles** — source output field; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the strobe bit from dev_req(5) to the external dev_05_req_o port by the whole-record assignment.
  - **roles** — strobe output field; carried from dev_req(5)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_05_req_o <= dev_req(5)

**`dev_05_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies device 5's response into internal dev_rsp(5) by the concurrent assignment dev_rsp(5) <= dev_05_rsp_i.
  - **roles** — device response input; feeds internal dev_rsp(5)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(5) <= dev_05_rsp_i

**`dev_05_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is copied into dev_rsp(5).ack via the concurrent assignment from dev_05_rsp_i.
  - **roles** — ack input field; supplies dev_rsp(5)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(5) <= dev_05_rsp_i

**`dev_05_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is the response data field from device 5 and is forwarded into dev_rsp(5) by the concurrent assignment.
  - **roles** — response data input; supplies dev_rsp(5)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(5) <= dev_05_rsp_i

**`dev_05_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded into dev_rsp(5).err by the concurrent assignment dev_rsp(5) <= dev_05_rsp_i.
  - **roles** — error input field; supplies dev_rsp(5)
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — concurrent assignment: dev_rsp(5) <= dev_05_rsp_i

**`dev_06_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Exports internal dev_req(6) to device 6 via the concurrent assignment dev_06_req_o <= dev_req(6).
  - **roles** — device 6 request exporter; carries internal dev_req(6)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_06_req_o <= dev_req(6)

**`dev_06_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is forwarded from dev_req(6) to the external dev_06_req_o.addr field as part of the whole-record concurrent assignment.
  - **roles** — address output field; carried from dev_req(6)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_06_req_o <= dev_req(6)

**`dev_06_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the amo bit of device-6 request, carrying dev_req(6).amo out to the device; dev_req(6) is produced internally from the main request stream. It contributes to the device request transported to the target.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_06_req_o <= dev_req(6); maps whole bus_req_t to port

**`dev_06_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the amoop field of device-6 request, carrying dev_req(6).amoop out to the device; dev_req(6) is produced internally from the main request stream. This is part of the per-device request forwarded from main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_06_req_o <= dev_req(6); maps whole bus_req_t to port

**`dev_06_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Is forwarded from internal dev_req(6) to the external dev_06_req_o port as part of the whole-record concurrent assignment.
  - **roles** — byte-enable output field; carried from dev_req(6)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_06_req_o <= dev_req(6)

**`dev_06_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the data field from dev_req(6) to device 6 via the whole-record assignment dev_06_req_o <= dev_req(6).
  - **roles** — data output field; carried from dev_req(6)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_06_req_o <= dev_req(6)

**`dev_06_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the debug bit of device-6 request, carrying dev_req(6).debug out to the device; dev_req(6) is produced internally from the main request stream. It is one field of the per-device request forwarded from main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_06_req_o <= dev_req(6); maps whole bus_req_t to port

**`dev_06_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the fence bit of device-6 request, carrying dev_req(6).fence out to the device; dev_req(6) is produced internally from the main request stream. It helps form the request sent to the device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_06_req_o <= dev_req(6); maps whole bus_req_t to port

**`dev_06_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the lock bit of device-6 request, carrying dev_req(6).lock out to the device; dev_req(6) is produced internally from the main request stream. It is one field of the per-device request forwarded.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_06_req_o <= dev_req(6); maps whole bus_req_t to port

**`dev_06_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the priv bit of device-6 request, carrying dev_req(6).priv out to the device; dev_req(6) is produced internally from the main request stream. Part of the per-device request forwarded from main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_06_req_o <= dev_req(6); maps whole bus_req_t to port

**`dev_06_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the read/write flag from dev_req(6) to dev_06_req_o via the whole-record assignment dev_06_req_o <= dev_req(6).
  - **roles** — rw output field; carried from dev_req(6)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_06_req_o <= dev_req(6)

**`dev_06_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the source field from internal dev_req(6) to the external dev_06_req_o.src field by the whole-record concurrent assignment.
  - **roles** — source output field; carried from dev_req(6)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_06_req_o <= dev_req(6)

**`dev_06_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the strobe bit from internal dev_req(6) to the external dev_06_req_o.stb field via the whole-record assignment.
  - **roles** — strobe output field; carried from dev_req(6)
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — concurrent assignment: dev_06_req_o <= dev_req(6)

**`dev_06_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies the device-6 response record into the entity, feeding the internal dev_rsp(6) aggregate which is later reduced into the main response; the value originates outside and enters via the port.
  - **roles** — boundary input; supplies device response; part of response aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(6) <= dev_06_rsp_i; maps incoming bus_rsp_t into internal array

**`dev_06_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the ack bit from device-6 response, feeding dev_rsp(6).ack internally; the bit is read into the response aggregation logic that computes main_rsp.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(6) <= dev_06_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_06_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the 32-bit data field from device-6 response, feeding dev_rsp(6).data internally; the data is OR-ed into the aggregated response that becomes main_rsp.data.
  - **roles** — carries response field; boundary input; contributes to aggregated data
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(6) <= dev_06_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_06_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the err bit from device-6 response, feeding dev_rsp(6).err internally; this bit is OR-ed into the aggregated main response error flag.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(6) <= dev_06_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_07_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the full device-7 request record out to the attached device; the port is assigned the internal dev_req(7) aggregate which is produced from main_req and addressing logic. It transports that device's request to the external peripheral.
  - **roles** — boundary output; carries full device request; per-device request channel
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); maps internal dev_req(7) to port

**`dev_07_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit address field of device-7 request out to the device; this field is taken from the internal dev_req(7) record produced from main_req addressing. It forms the address supplied to the device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes addr

**`dev_07_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the amo bit of device-7 request out to the device, carrying dev_req(7).amo from the internally produced request. It is forwarded as part of the request record.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes amo

**`dev_07_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the amoop field of device-7 request out to the device, carrying dev_req(7).amoop from the internal request. It is part of the forwarded request control fields.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes amoop

**`dev_07_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the byte-enable field of device-7 request out to the device, carrying dev_req(7).ben from the internally constructed request. It determines which bytes of data are valid on the bus.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes ben

**`dev_07_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit data field of device-7 request out to the device; the field comes from internal dev_req(7), which is derived from the main request when applicable. It supplies write data to the device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes data

**`dev_07_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the debug bit of device-7 request out to the device, carrying dev_req(7).debug from the internally formed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes debug

**`dev_07_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the fence bit of device-7 request out to the device, carrying dev_req(7).fence from the internal request. It is forwarded as part of the per-device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes fence

**`dev_07_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the lock bit of device-7 request out to the device, carrying dev_req(7).lock from the internally constructed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes lock

**`dev_07_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the priv bit of device-7 request out to the device, carrying dev_req(7).priv from the internal request. It is one field of the per-device request supplied from main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes priv

**`dev_07_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the rw bit of device-7 request out to the device, carrying dev_req(7).rw from the internally assembled request. It indicates read or write for the per-device transaction.
  - **roles** — carries control bit; boundary output; part of request semantics
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes rw

**`dev_07_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the src bit of device-7 request out to the device, carrying dev_req(7).src from the internally generated request. It tags the request source as provided by main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes src

**`dev_07_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the stb (strobe) bit of device-7 request out to the device; the bit reflects dev_req(7).stb which is selectively asserted by the address match logic that builds dev_req(7) from main_req. It qualifies the request to the device.
  - **roles** — carries control bit; boundary output; qualifies device request
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_07_req_o <= dev_req(7); whole-record mapping includes stb

**`dev_07_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies the device-7 response record into the entity, assigned into the internal dev_rsp(7) which participates in the aggregation that forms main_rsp. The value originates externally and enters via this port.
  - **roles** — boundary input; supplies device response; part of response aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(7) <= dev_07_rsp_i; maps incoming bus_rsp_t into internal array

**`dev_07_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the ack bit from device-7 response, feeding dev_rsp(7).ack internally; this bit is OR-ed into the aggregated main response ack signal.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(7) <= dev_07_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_07_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the 32-bit data field from device-7 response, feeding dev_rsp(7).data internally; the data is OR-ed into the aggregated response that becomes main_rsp.data.
  - **roles** — carries response field; boundary input; contributes to aggregated data
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(7) <= dev_07_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_07_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the err bit from device-7 response, feeding dev_rsp(7).err internally; this bit is OR-ed into the aggregated main response error flag.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(7) <= dev_07_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_08_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the full device-8 request record out to the attached device; the port is assigned the internal dev_req(8) aggregate which is produced from main_req and addressing logic. It transports that device's request to the external peripheral.
  - **roles** — boundary output; carries full device request; per-device request channel
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); maps internal dev_req(8) to port

**`dev_08_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit address field of device-8 request out to the device; this field is taken from the internal dev_req(8) record produced from main_req addressing. It forms the address supplied to the device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes addr

**`dev_08_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the amo bit of device-8 request out to the device, carrying dev_req(8).amo from the internally produced request. It is forwarded as part of the request record.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes amo

**`dev_08_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the amoop field of device-8 request out to the device, carrying dev_req(8).amoop from the internal request. It is part of the forwarded request control fields.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes amoop

**`dev_08_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the byte-enable field of device-8 request out to the device, carrying dev_req(8).ben from the internally constructed request. It determines which bytes of data are valid on the bus.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes ben

**`dev_08_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit data field of device-8 request out to the device; the field comes from internal dev_req(8), which is derived from the main request when applicable. It supplies write data to the device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes data

**`dev_08_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the debug bit of device-8 request out to the device, carrying dev_req(8).debug from the internally formed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes debug

**`dev_08_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the fence bit of device-8 request out to the device, carrying dev_req(8).fence from the internal request. It is forwarded as part of the per-device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes fence

**`dev_08_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the lock bit of device-8 request out to the device, carrying dev_req(8).lock from the internally constructed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes lock

**`dev_08_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the priv bit of device-8 request out to the device, carrying dev_req(8).priv from the internal request. It is one field of the per-device request supplied from main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes priv

**`dev_08_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the rw bit of device-8 request out to the device, carrying dev_req(8).rw from the internally assembled request. It indicates read or write for the per-device transaction.
  - **roles** — carries control bit; boundary output; part of request semantics
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes rw

**`dev_08_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the src bit of device-8 request out to the device, carrying dev_req(8).src from the internally generated request. It tags the request source as provided by main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes src

**`dev_08_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the stb (strobe) bit of device-8 request out to the device; the bit reflects dev_req(8).stb which is selectively asserted by the address match logic that builds dev_req(8) from main_req. It qualifies the request to the device.
  - **roles** — carries control bit; boundary output; qualifies device request
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_08_req_o <= dev_req(8); whole-record mapping includes stb

**`dev_08_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies the device-8 response record into the entity, assigned into the internal dev_rsp(8) which participates in the aggregation that forms main_rsp. The value originates externally and enters via this port.
  - **roles** — boundary input; supplies device response; part of response aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(8) <= dev_08_rsp_i; maps incoming bus_rsp_t into internal array

**`dev_08_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the ack bit from device-8 response, feeding dev_rsp(8).ack internally; this bit is OR-ed into the aggregated main response ack signal.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(8) <= dev_08_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_08_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the 32-bit data field from device-8 response, feeding dev_rsp(8).data internally; the data is OR-ed into the aggregated response that becomes main_rsp.data.
  - **roles** — carries response field; boundary input; contributes to aggregated data
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(8) <= dev_08_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_08_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the err bit from device-8 response, feeding dev_rsp(8).err internally; this bit is OR-ed into the aggregated main response error flag.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(8) <= dev_08_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_09_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the full device-9 request record out to the attached device; the port is assigned the internal dev_req(9) aggregate which is produced from main_req and addressing logic. It transports that device's request to the external peripheral.
  - **roles** — boundary output; carries full device request; per-device request channel
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); maps internal dev_req(9) to port

**`dev_09_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit address field of device-9 request out to the device; this field is taken from the internal dev_req(9) record produced from main_req addressing. It forms the address supplied to the device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes addr

**`dev_09_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the amo bit of device-9 request out to the device, carrying dev_req(9).amo from the internally produced request. It is forwarded as part of the request record.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes amo

**`dev_09_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the amoop field of device-9 request out to the device, carrying dev_req(9).amoop from the internal request. It is part of the forwarded request control fields.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes amoop

**`dev_09_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the byte-enable field of device-9 request out to the device, carrying dev_req(9).ben from the internally constructed request. It determines which bytes of data are valid on the bus.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes ben

**`dev_09_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit data field of device-9 request out to the device; the field comes from internal dev_req(9), which is derived from the main request when applicable. It supplies write data to the device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes data

**`dev_09_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the debug bit of device-9 request out to the device, carrying dev_req(9).debug from the internally formed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes debug

**`dev_09_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the fence bit of device-9 request out to the device, carrying dev_req(9).fence from the internal request. It is forwarded as part of the per-device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes fence

**`dev_09_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the lock bit of device-9 request out to the device, carrying dev_req(9).lock from the internally constructed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes lock

**`dev_09_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the priv bit of device-9 request out to the device, carrying dev_req(9).priv from the internal request. It is one field of the per-device request supplied from main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes priv

**`dev_09_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the rw bit of device-9 request out to the device, carrying dev_req(9).rw from the internally assembled request. It indicates read or write for the per-device transaction.
  - **roles** — carries control bit; boundary output; part of request semantics
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes rw

**`dev_09_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the src bit of device-9 request out to the device, carrying dev_req(9).src from the internally generated request. It tags the request source as provided by main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes src

**`dev_09_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the stb (strobe) bit of device-9 request out to the device; the bit reflects dev_req(9).stb which is selectively asserted by the address match logic that builds dev_req(9) from main_req. It qualifies the request to the device.
  - **roles** — carries control bit; boundary output; qualifies device request
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_09_req_o <= dev_req(9); whole-record mapping includes stb

**`dev_09_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies the device-9 response record into the entity, assigned into the internal dev_rsp(9) which participates in the aggregation that forms main_rsp. The value originates externally and enters via this port.
  - **roles** — boundary input; supplies device response; part of response aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(9) <= dev_09_rsp_i; maps incoming bus_rsp_t into internal array

**`dev_09_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the ack bit from device-9 response, feeding dev_rsp(9).ack internally; this bit is OR-ed into the aggregated main response ack signal.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(9) <= dev_09_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_09_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the 32-bit data field from device-9 response, feeding dev_rsp(9).data internally; the data is OR-ed into the aggregated response that becomes main_rsp.data.
  - **roles** — carries response field; boundary input; contributes to aggregated data
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(9) <= dev_09_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_09_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the err bit from device-9 response, feeding dev_rsp(9).err internally; this bit is OR-ed into the aggregated main response error flag.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(9) <= dev_09_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_10_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the full device-10 request record out to the attached device; the port is assigned the internal dev_req(10) aggregate which is produced from main_req and addressing logic. It transports that device's request to the external peripheral.
  - **roles** — boundary output; carries full device request; per-device request channel
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); maps internal dev_req(10) to port

**`dev_10_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit address field of device-10 request out to the device; this field is taken from the internal dev_req(10) record produced from main_req addressing. It forms the address supplied to the device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes addr

**`dev_10_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the amo bit of device-10 request out to the device, carrying dev_req(10).amo from the internally produced request. It is forwarded as part of the request record.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes amo

**`dev_10_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the amoop field of device-10 request out to the device, carrying dev_req(10).amoop from the internal request. It is part of the forwarded request control fields.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes amoop

**`dev_10_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the byte-enable field of device-10 request out to the device, carrying dev_req(10).ben from the internally constructed request. It determines which bytes of data are valid on the bus.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes ben

**`dev_10_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit data field of device-10 request out to the device; the field comes from internal dev_req(10), which is derived from the main request when applicable. It supplies write data to the device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes data

**`dev_10_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the debug bit of device-10 request out to the device, carrying dev_req(10).debug from the internally formed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes debug

**`dev_10_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the fence bit of device-10 request out to the device, carrying dev_req(10).fence from the internal request. It is forwarded as part of the per-device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes fence

**`dev_10_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the lock bit of device-10 request out to the device, carrying dev_req(10).lock from the internally constructed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes lock

**`dev_10_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the priv bit of device-10 request out to the device, carrying dev_req(10).priv from the internal request. It is one field of the per-device request supplied from main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes priv

**`dev_10_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the rw bit of device-10 request out to the device, carrying dev_req(10).rw from the internally assembled request. It indicates read or write for the per-device transaction.
  - **roles** — carries control bit; boundary output; part of request semantics
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes rw

**`dev_10_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the src bit of device-10 request out to the device, carrying dev_req(10).src from the internally generated request. It tags the request source as provided by main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes src

**`dev_10_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the stb (strobe) bit of device-10 request out to the device; the bit reflects dev_req(10).stb which is selectively asserted by the address match logic that builds dev_req(10) from main_req. It qualifies the request to the device.
  - **roles** — carries control bit; boundary output; qualifies device request
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_10_req_o <= dev_req(10); whole-record mapping includes stb

**`dev_10_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies the device-10 response record into the entity, assigned into the internal dev_rsp(10) which participates in the aggregation that forms main_rsp. The value originates externally and enters via this port.
  - **roles** — boundary input; supplies device response; part of response aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(10) <= dev_10_rsp_i; maps incoming bus_rsp_t into internal array

**`dev_10_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the ack bit from device-10 response, feeding dev_rsp(10).ack internally; this bit is OR-ed into the aggregated main response ack signal.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(10) <= dev_10_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_10_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the 32-bit data field from device-10 response, feeding dev_rsp(10).data internally; the data is OR-ed into the aggregated response that becomes main_rsp.data.
  - **roles** — carries response field; boundary input; contributes to aggregated data
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(10) <= dev_10_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_10_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the err bit from device-10 response, feeding dev_rsp(10).err internally; this bit is OR-ed into the aggregated main response error flag.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(10) <= dev_10_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_11_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the full device-11 request record out to the attached device; the port is assigned the internal dev_req(11) aggregate which is produced from main_req and addressing logic. It transports that device's request to the external peripheral.
  - **roles** — boundary output; carries full device request; per-device request channel
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); maps internal dev_req(11) to port

**`dev_11_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit address field of device-11 request out to the device; this field is taken from the internal dev_req(11) record produced from main_req addressing. It forms the address supplied to the device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes addr

**`dev_11_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the amo bit of device-11 request out to the device, carrying dev_req(11).amo from the internally produced request. It is forwarded as part of the request record.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes amo

**`dev_11_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the amoop field of device-11 request out to the device, carrying dev_req(11).amoop from the internal request. It is part of the forwarded request control fields.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes amoop

**`dev_11_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the byte-enable field of device-11 request out to the device, carrying dev_req(11).ben from the internally constructed request. It determines which bytes of data are valid on the bus.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes ben

**`dev_11_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit data field of device-11 request out to the device; the field comes from internal dev_req(11), which is derived from the main request when applicable. It supplies write data to the device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes data

**`dev_11_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the debug bit of device-11 request out to the device, carrying dev_req(11).debug from the internally formed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes debug

**`dev_11_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the fence bit of device-11 request out to the device, carrying dev_req(11).fence from the internal request. It is forwarded as part of the per-device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes fence

**`dev_11_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the lock bit of device-11 request out to the device, carrying dev_req(11).lock from the internally constructed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes lock

**`dev_11_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the priv bit of device-11 request out to the device, carrying dev_req(11).priv from the internal request. It is one field of the per-device request supplied from main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes priv

**`dev_11_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the rw bit of device-11 request out to the device, carrying dev_req(11).rw from the internally assembled request. It indicates read or write for the per-device transaction.
  - **roles** — carries control bit; boundary output; part of request semantics
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes rw

**`dev_11_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the src bit of device-11 request out to the device, carrying dev_req(11).src from the internally generated request. It tags the request source as provided by main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes src

**`dev_11_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the stb (strobe) bit of device-11 request out to the device; the bit reflects dev_req(11).stb which is selectively asserted by the address match logic that builds dev_req(11) from main_req. It qualifies the request to the device.
  - **roles** — carries control bit; boundary output; qualifies device request
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_11_req_o <= dev_req(11); whole-record mapping includes stb

**`dev_11_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies the device-11 response record into the entity, assigned into the internal dev_rsp(11) which participates in the aggregation that forms main_rsp. The value originates externally and enters via this port.
  - **roles** — boundary input; supplies device response; part of response aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(11) <= dev_11_rsp_i; maps incoming bus_rsp_t into internal array

**`dev_11_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the ack bit from device-11 response, feeding dev_rsp(11).ack internally; this bit is OR-ed into the aggregated main response ack signal.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(11) <= dev_11_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_11_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the 32-bit data field from device-11 response, feeding dev_rsp(11).data internally; the data is OR-ed into the aggregated response that becomes main_rsp.data.
  - **roles** — carries response field; boundary input; contributes to aggregated data
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(11) <= dev_11_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_11_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the err bit from device-11 response, feeding dev_rsp(11).err internally; this bit is OR-ed into the aggregated main response error flag.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(11) <= dev_11_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_12_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the full device-12 request record out to the attached device; the port is assigned the internal dev_req(12) aggregate which is produced from main_req and addressing logic. It transports that device's request to the external peripheral.
  - **roles** — boundary output; carries full device request; per-device request channel
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); maps internal dev_req(12) to port

**`dev_12_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit address field of device-12 request out to the device; this field is taken from the internal dev_req(12) record produced from main_req addressing. It forms the address supplied to the device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes addr

**`dev_12_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the amo bit of device-12 request out to the device, carrying dev_req(12).amo from the internally produced request. It is forwarded as part of the request record.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes amo

**`dev_12_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the amoop field of device-12 request out to the device, carrying dev_req(12).amoop from the internal request. It is part of the forwarded request control fields.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes amoop

**`dev_12_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the byte-enable field of device-12 request out to the device, carrying dev_req(12).ben from the internally constructed request. It determines which bytes of data are valid on the bus.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes ben

**`dev_12_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit data field of device-12 request out to the device; the field comes from internal dev_req(12), which is derived from the main request when applicable. It supplies write data to the device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes data

**`dev_12_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the debug bit of device-12 request out to the device, carrying dev_req(12).debug from the internally formed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes debug

**`dev_12_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the fence bit of device-12 request out to the device, carrying dev_req(12).fence from the internal request. It is forwarded as part of the per-device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes fence

**`dev_12_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the lock bit of device-12 request out to the device, carrying dev_req(12).lock from the internally constructed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes lock

**`dev_12_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the priv bit of device-12 request out to the device, carrying dev_req(12).priv from the internal request. It is one field of the per-device request supplied from main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes priv

**`dev_12_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the rw bit of device-12 request out to the device, carrying dev_req(12).rw from the internally assembled request. It indicates read or write for the per-device transaction.
  - **roles** — carries control bit; boundary output; part of request semantics
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes rw

**`dev_12_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the src bit of device-12 request out to the device, carrying dev_req(12).src from the internally generated request. It tags the request source as provided by main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes src

**`dev_12_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the stb (strobe) bit of device-12 request out to the device; the bit reflects dev_req(12).stb which is selectively asserted by the address match logic that builds dev_req(12) from main_req. It qualifies the request to the device.
  - **roles** — carries control bit; boundary output; qualifies device request
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_12_req_o <= dev_req(12); whole-record mapping includes stb

**`dev_12_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies the device-12 response record into the entity, assigned into the internal dev_rsp(12) which participates in the aggregation that forms main_rsp. The value originates externally and enters via this port.
  - **roles** — boundary input; supplies device response; part of response aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(12) <= dev_12_rsp_i; maps incoming bus_rsp_t into internal array

**`dev_12_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the ack bit from device-12 response, feeding dev_rsp(12).ack internally; this bit is OR-ed into the aggregated main response ack signal.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(12) <= dev_12_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_12_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the 32-bit data field from device-12 response, feeding dev_rsp(12).data internally; the data is OR-ed into the aggregated response that becomes main_rsp.data.
  - **roles** — carries response field; boundary input; contributes to aggregated data
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(12) <= dev_12_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_12_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the err bit from device-12 response, feeding dev_rsp(12).err internally; this bit is OR-ed into the aggregated main response error flag.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(12) <= dev_12_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_13_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the full device-13 request record out to the attached device; the port is assigned the internal dev_req(13) aggregate which is produced from main_req and addressing logic. It transports that device's request to the external peripheral.
  - **roles** — boundary output; carries full device request; per-device request channel
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); maps internal dev_req(13) to port

**`dev_13_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit address field of device-13 request out to the device; this field is taken from the internal dev_req(13) record produced from main_req addressing. It forms the address supplied to the device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes addr

**`dev_13_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the amo bit of device-13 request out to the device, carrying dev_req(13).amo from the internally produced request. It is forwarded as part of the request record.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes amo

**`dev_13_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the amoop field of device-13 request out to the device, carrying dev_req(13).amoop from the internal request. It is part of the forwarded request control fields.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes amoop

**`dev_13_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Drives the byte-enable field of device-13 request out to the device, carrying dev_req(13).ben from the internally constructed request. It determines which bytes of data are valid on the bus.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes ben

**`dev_13_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the 32-bit data field of device-13 request out to the device; the field comes from internal dev_req(13), which is derived from the main request when applicable. It supplies write data to the device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes data

**`dev_13_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the debug bit of device-13 request out to the device, carrying dev_req(13).debug from the internally formed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes debug

**`dev_13_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the fence bit of device-13 request out to the device, carrying dev_req(13).fence from the internal request. It is forwarded as part of the per-device request.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes fence

**`dev_13_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the lock bit of device-13 request out to the device, carrying dev_req(13).lock from the internally constructed request. It is forwarded unchanged to the external device.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes lock

**`dev_13_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the priv bit of device-13 request out to the device, carrying dev_req(13).priv from the internal request. It is one field of the per-device request supplied from main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes priv

**`dev_13_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the rw bit of device-13 request out to the device, carrying dev_req(13).rw from the internally assembled request. It indicates read or write for the per-device transaction.
  - **roles** — carries control bit; boundary output; part of request semantics
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes rw

**`dev_13_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the src bit of device-13 request out to the device, carrying dev_req(13).src from the internally generated request. It tags the request source as provided by main_req.
  - **roles** — carries request field; boundary output; part of device request path
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes src

**`dev_13_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the stb (strobe) bit of device-13 request out to the device; the bit reflects dev_req(13).stb which is selectively asserted by the address match logic that builds dev_req(13) from main_req. It qualifies the request to the device.
  - **roles** — carries control bit; boundary output; qualifies device request
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → _(none)_
  - **evidence** — continuous assignment dev_13_req_o <= dev_req(13); whole-record mapping includes stb

**`dev_13_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Supplies the device-13 response record into the entity, assigned into the internal dev_rsp(13) which participates in the aggregation that forms main_rsp. The value originates externally and enters via this port.
  - **roles** — boundary input; supplies device response; part of response aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(13) <= dev_13_rsp_i; maps incoming bus_rsp_t into internal array

**`dev_13_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the ack bit from device-13 response, feeding dev_rsp(13).ack internally; this bit is OR-ed into the aggregated main response ack signal.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(13) <= dev_13_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_13_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies the 32-bit response data field from external device 13 into the switch; the value is forwarded into the internal dev_rsp(13) record and then OR-aggregated into the switch response vector.
  - **roles** — response data input; feeds internal response aggregator; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_rsp(13) <= dev_13_rsp_i;' and bus_response process ORs dev_rsp(i).data into tmp_v.data.

**`dev_13_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the err bit from device-13 response, feeding dev_rsp(13).err internally; this bit is OR-ed into the aggregated main response error flag.
  - **roles** — carries response field; boundary input; contributes to aggregation
  - **relationships** — **SOURCES** → _(none)_
  - **evidence** — continuous assignment dev_rsp(13) <= dev_13_rsp_i; incoming bus_rsp_t assigned into internal array

**`dev_14_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the complete device-14 request record out to the peripheral; the port is driven from the internal dev_req(14) record which itself is derived from main_req and address decoding.
  - **roles** — request record output; carries internal dev_req(14) to device; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_14_req_o <= dev_req(14);' in the concurrent statements that wire dev_req entries to ports.

**`dev_14_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the 32-bit address field of the internal dev_req(14) record to device 14; the address originates from the routed main_req and is forwarded combinationally to the port.
  - **roles** — address field output; forwards routed request address; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Subrecord of 'dev_14_req_o <= dev_req(14);' assignment; dev_req(14) is assigned from main_req in the bus_request generate.

**`dev_14_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the AMO single-bit flag from internal dev_req(14) to the device; the field is carried combinationally from the routed main_req record.
  - **roles** — AMO flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the concurrent assignment 'dev_14_req_o <= dev_req(14);' that connects internal request to the port.

**`dev_14_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit AMO opcode field from internal dev_req(14) to the peripheral; the field is carried unchanged from the routed main_req.
  - **roles** — AMO opcode output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Delivered as part of the record assignment 'dev_14_req_o <= dev_req(14);' in the concurrent assignments.

**`dev_14_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs the 4-bit byte-enable field from internal dev_req(14) to the device; the field is forwarded combinationally from the routed main_req.
  - **roles** — byte-enable output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the record assignment 'dev_14_req_o <= dev_req(14);' in the concurrent port wiring.

**`dev_14_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit data field from the internal dev_req(14) record to the external device; the field is carried unchanged from the routed main_req.
  - **roles** — data field output; forwards routed write data; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Driven by the concurrent assignment 'dev_14_req_o <= dev_req(14);' which forwards dev_req fields to the port.

**`dev_14_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the debug bit from the internal dev_req(14) record to the external device; the bit is carried unchanged from the routed main_req.
  - **roles** — debug flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the concurrent record assignment 'dev_14_req_o <= dev_req(14);' in the concurrent region.

**`dev_14_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the fence bit from internal dev_req(14) to the peripheral; carried unchanged from the routed main_req record.
  - **roles** — fence flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Field included in the concurrent assignment 'dev_14_req_o <= dev_req(14);' observed among port wiring.

**`dev_14_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock bit from the internal dev_req(14) record to the device; the bit is carried combinationally from the routed main_req.
  - **roles** — lock flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of 'dev_14_req_o <= dev_req(14);' which wires internal request fields to the external port.

**`dev_14_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the privilege bit from internal dev_req(14) to device 14; the bit is carried combinationally from the routed main_req record.
  - **roles** — privilege flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Delivered as part of 'dev_14_req_o <= dev_req(14);' which forwards internal request fields to the port.

**`dev_14_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the single-bit read/write flag from internal dev_req(14) to the peripheral; the flag is carried combinationally from the routed main_req.
  - **roles** — rw flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the record assignment 'dev_14_req_o <= dev_req(14);' connecting internal dev_req to output ports.

**`dev_14_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source bit from internal dev_req(14) to the external device; the bit is carried unchanged from the routed main_req record.
  - **roles** — source field output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Field is part of the concurrent assignment 'dev_14_req_o <= dev_req(14);' in the port wiring.

**`dev_14_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the single-bit strobe (stb) to device 14 from the internal dev_req(14).stb; that bit is set only when the main_req address matches device 14's base, otherwise it is cleared by the generated request logic.
  - **roles** — strobe output; reflects address-qualified request; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_req(i).stb is conditionally driven in the bus_request process; then 'dev_14_req_o <= dev_req(14);' forwards it to the port.

**`dev_14_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Receives the complete response record from device 14 and supplies it to the internal dev_rsp(14) entry; that internal entry is then aggregated by the bus_response process into main_rsp.
  - **roles** — response record input; feeds internal response aggregator; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_rsp(14) <= dev_14_rsp_i;' and bus_response process OR-aggregates dev_rsp entries.

**`dev_14_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies the single-bit ack from device 14 into the internal response record; that bit is OR-aggregated with others in the bus_response process to form main_rsp.ack.
  - **roles** — ack input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Assigned by 'dev_rsp(14) <= dev_14_rsp_i;' and then referenced in bus_response process where dev_rsp(i).ack is ORed into tmp_v.ack.

**`dev_14_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies the 32-bit response data from device 14 into the internal dev_rsp(14).data field; that data is OR-aggregated with other devices' data in bus_response into main_rsp.data.
  - **roles** — response data input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_rsp(14) <= dev_14_rsp_i;' and bus_response process ORs dev_rsp(i).data into tmp_v.data.

**`dev_14_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies the single-bit err flag from device 14 into the internal response record; bus_response ORs dev_rsp(i).err into the aggregated main response error flag.
  - **roles** — error input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Connected by 'dev_rsp(14) <= dev_14_rsp_i;' and bus_response process ORs dev_rsp(i).err into tmp_v.err.

**`dev_15_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the complete device-15 request record out to the peripheral; the port is driven from internal dev_req(15) which is derived from main_req guided by address decoding.
  - **roles** — request record output; carries internal dev_req(15) to device; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_15_req_o <= dev_req(15);' present in the port wiring region.

**`dev_15_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the 32-bit address field from internal dev_req(15) to device 15; address is forwarded from the routed main_req record.
  - **roles** — address field output; forwards routed request address; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the concurrent assignment 'dev_15_req_o <= dev_req(15);' wiring internal request to output.

**`dev_15_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the AMO bit from internal dev_req(15) to the peripheral; field is carried unchanged from the routed main_req.
  - **roles** — AMO flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the concurrent assignment 'dev_15_req_o <= dev_req(15);' in the port wiring section.

**`dev_15_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit AMO opcode from internal dev_req(15) to device 15; carried combinationally from main_req.
  - **roles** — AMO opcode output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Delivered as part of 'dev_15_req_o <= dev_req(15);' concurrent assignment.

**`dev_15_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit byte-enable field from internal dev_req(15) to device 15; carried combinationally from the routed main_req.
  - **roles** — byte-enable output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the record assignment 'dev_15_req_o <= dev_req(15);' that wires internal requests to ports.

**`dev_15_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit data field from internal dev_req(15) to the external device; the field is carried unchanged from main_req.
  - **roles** — data field output; forwards routed write data; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Driven by the concurrent assignment 'dev_15_req_o <= dev_req(15);' in the concurrent statements.

**`dev_15_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the debug bit from internal dev_req(15) to the external device; carried combinationally from the routed main_req.
  - **roles** — debug flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included within 'dev_15_req_o <= dev_req(15);' concurrent assignment wiring.

**`dev_15_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the fence bit from internal dev_req(15) to the peripheral; the bit is carried combinationally from routed main_req.
  - **roles** — fence flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the concurrent assignment 'dev_15_req_o <= dev_req(15);' connecting internal record to port.

**`dev_15_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock bit from internal dev_req(15) to the external device; bit carried unchanged from routed main_req.
  - **roles** — lock flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_15_req_o <= dev_req(15);' concurrent assignment forwards the field to the port.

**`dev_15_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the privilege bit from internal dev_req(15) to the peripheral; the bit is carried unchanged from routed main_req.
  - **roles** — privilege flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the concurrent record assignment 'dev_15_req_o <= dev_req(15);' connecting internal request fields to outputs.

**`dev_15_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the single-bit read/write flag from internal dev_req(15) to the peripheral; carried unchanged from main_req.
  - **roles** — rw flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the concurrent assignment 'dev_15_req_o <= dev_req(15);' connecting internal request to the port.

**`dev_15_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source bit from internal dev_req(15) to device 15; the bit is carried combinationally from the routed main_req.
  - **roles** — source field output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Delivered as part of 'dev_15_req_o <= dev_req(15);' in the concurrent port wiring.

**`dev_15_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the stb bit to device 15 from internal dev_req(15).stb; that bit is set only when main_req address matches device 15 base, otherwise it is cleared by the bus_request generate logic.
  - **roles** — strobe output; reflects address-qualified request; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — bus_request process conditionally assigns dev_req(i).stb, then 'dev_15_req_o <= dev_req(15);' forwards it.

**`dev_15_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Receives the response record from device 15 and supplies it to the internal dev_rsp(15) entry; bus_response then aggregates dev_rsp entries into main_rsp.
  - **roles** — response record input; feeds internal response aggregator; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_rsp(15) <= dev_15_rsp_i;' and later bus_response process OR-aggregates dev_rsp entries.

**`dev_15_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies device 15's ack bit into internal dev_rsp(15); bus_response ORs dev_rsp(i).ack into the aggregated main response ack.
  - **roles** — ack input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(15) <= dev_15_rsp_i;' and bus_response process which ORs dev_rsp(i).ack into tmp_v.ack.

**`dev_15_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies the 32-bit response data from device 15 into the internal dev_rsp(15).data field; bus_response OR-aggregates this into main_rsp.data.
  - **roles** — response data input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(15) <= dev_15_rsp_i;' and bus_response process ORs dev_rsp(i).data into tmp_v.data.

**`dev_15_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies device 15's err bit into internal dev_rsp(15); the bus_response process ORs dev_rsp(i).err into the aggregated main response error flag.
  - **roles** — error input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Connected by 'dev_rsp(15) <= dev_15_rsp_i;' and used in bus_response which ORs err bits.

**`dev_16_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the complete device-16 request record to the peripheral, forwarding internal dev_req(16) which is derived from main_req and address decoding logic.
  - **roles** — request record output; carries internal dev_req(16) to device; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_16_req_o <= dev_req(16);' in the concurrent wiring section.

**`dev_16_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit address from internal dev_req(16) to the device; the address originates from the routed main_req record.
  - **roles** — address field output; forwards routed request address; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of 'dev_16_req_o <= dev_req(16);' concurrent assignment wiring internal fields to ports.

**`dev_16_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the AMO bit from internal dev_req(16) to the peripheral; field carried combinationally from the routed main_req.
  - **roles** — AMO flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the concurrent record assignment 'dev_16_req_o <= dev_req(16);'.

**`dev_16_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit AMO opcode from internal dev_req(16) to the device; carried unchanged from main_req.
  - **roles** — AMO opcode output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_16_req_o <= dev_req(16);' concurrent assignment includes this field.

**`dev_16_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit byte-enable field from internal dev_req(16) to the device; field carried unchanged from routed main_req.
  - **roles** — byte-enable output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the record assignment 'dev_16_req_o <= dev_req(16);' wiring internal request to port.

**`dev_16_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit data field from internal dev_req(16) to the external device; carried combinationally from main_req.
  - **roles** — data field output; forwards routed write data; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Driven by the concurrent assignment 'dev_16_req_o <= dev_req(16);' in the concurrent region.

**`dev_16_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the debug bit from internal dev_req(16) to the external device; carried unchanged from routed main_req.
  - **roles** — debug flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in 'dev_16_req_o <= dev_req(16);' concurrent assignment wiring.

**`dev_16_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the fence bit from internal dev_req(16) to the external device; carried unchanged from routed main_req.
  - **roles** — fence flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_16_req_o <= dev_req(16);' concurrent assignment wires this field to the port.

**`dev_16_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock bit from internal dev_req(16) to the peripheral; field carried combinationally from routed main_req.
  - **roles** — lock flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the concurrent assignment 'dev_16_req_o <= dev_req(16);'.

**`dev_16_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the privilege bit from internal dev_req(16) to the device; the bit is carried combinationally from the routed main_req record.
  - **roles** — privilege flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the concurrent assignment 'dev_16_req_o <= dev_req(16);' in the port wiring.

**`dev_16_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the read/write flag from internal dev_req(16) to the peripheral; carried combinationally from the routed main_req.
  - **roles** — rw flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the concurrent assignment 'dev_16_req_o <= dev_req(16);' wiring internal record to port.

**`dev_16_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source bit from internal dev_req(16) to device 16; field carried unchanged from the routed main_req.
  - **roles** — source field output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_16_req_o <= dev_req(16);' concurrent assignment includes this field.

**`dev_16_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the stb bit to device 16 from internal dev_req(16).stb; that bit is conditionally asserted only when the routed main_req address matches device 16 base.
  - **roles** — strobe output; reflects address-qualified request; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — bus_request generate conditionally assigns dev_req(i).stb; then 'dev_16_req_o <= dev_req(16);' forwards it to the port.

**`dev_16_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Receives the response record from device 16 and supplies it to the internal dev_rsp(16) entry; bus_response aggregates dev_rsp array entries into main_rsp.
  - **roles** — response record input; feeds internal response aggregator; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_rsp(16) <= dev_16_rsp_i;' and bus_response process OR-aggregates dev_rsp entries.

**`dev_16_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies dev 16's ack bit into internal dev_rsp(16); bus_response ORs dev_rsp(i).ack into the aggregated main response ack.
  - **roles** — ack input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(16) <= dev_16_rsp_i;' plus bus_response process which ORs ack bits.

**`dev_16_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies the 32-bit response data from device 16 into internal dev_rsp(16).data; bus_response OR-aggregates this into the combined main response data.
  - **roles** — response data input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(16) <= dev_16_rsp_i;' and bus_response process ORs dev_rsp(i).data into tmp_v.data.

**`dev_16_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies dev 16's err bit into internal dev_rsp(16); bus_response ORs dev_rsp(i).err into the aggregated main response error flag.
  - **roles** — error input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(16) <= dev_16_rsp_i;' and bus_response process ORs err bits.

**`dev_17_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the complete device-17 request record to the peripheral, forwarding internal dev_req(17) driven from main_req and address decode logic.
  - **roles** — request record output; forwards internal dev_req(17); crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_17_req_o <= dev_req(17);' in the concurrent wiring area.

**`dev_17_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit address field from internal dev_req(17) to device 17; the address is carried from the routed main_req.
  - **roles** — address field output; forwards routed request address; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of 'dev_17_req_o <= dev_req(17);' concurrent assignment wiring internal fields to ports.

**`dev_17_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the AMO bit from internal dev_req(17) to the peripheral; carried combinationally from the routed main_req.
  - **roles** — AMO flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_17_req_o <= dev_req(17);' concurrent record assignment includes this field.

**`dev_17_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit AMO opcode from internal dev_req(17) to device 17; carried unchanged from main_req.
  - **roles** — AMO opcode output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of 'dev_17_req_o <= dev_req(17);' concurrent assignment wiring.

**`dev_17_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit byte-enable field from internal dev_req(17) to device 17; carried unchanged from the routed main_req.
  - **roles** — byte-enable output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in 'dev_17_req_o <= dev_req(17);' concurrent assignment wiring.

**`dev_17_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit data field from internal dev_req(17) to the external device; field carried combinationally from main_req.
  - **roles** — data field output; forwards routed write data; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Driven by the concurrent assignment 'dev_17_req_o <= dev_req(17);' in the port wiring.

**`dev_17_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the debug bit from internal dev_req(17) to the device; carried unchanged from the routed main_req.
  - **roles** — debug flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the concurrent assignment 'dev_17_req_o <= dev_req(17);'.

**`dev_17_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the fence bit from internal dev_req(17) to the external device; carried unchanged from routed main_req.
  - **roles** — fence flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the record assignment 'dev_17_req_o <= dev_req(17);' in the concurrent region.

**`dev_17_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock bit from internal dev_req(17) to the device; field carried combinationally from routed main_req.
  - **roles** — lock flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_17_req_o <= dev_req(17);' concurrent assignment includes this field.

**`dev_17_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the privilege bit from internal dev_req(17) to the external device; the bit is carried combinationally from routed main_req.
  - **roles** — privilege flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_17_req_o <= dev_req(17);' concurrent assignment wires internal request fields to the port.

**`dev_17_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the rw bit from internal dev_req(17) to the peripheral; carried combinationally from routed main_req.
  - **roles** — rw flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_17_req_o <= dev_req(17);' concurrent assignment includes this field.

**`dev_17_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source bit from internal dev_req(17) to device 17; carried unchanged from main_req.
  - **roles** — source field output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the concurrent record assignment 'dev_17_req_o <= dev_req(17);'.

**`dev_17_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the stb bit to device 17 from internal dev_req(17).stb; that bit is asserted only when the main_req address matches device 17 base as set by bus_request logic.
  - **roles** — strobe output; reflects address-qualified request; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — bus_request generate assigns dev_req(i).stb conditionally; 'dev_17_req_o <= dev_req(17);' forwards it.

**`dev_17_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Receives the response record from device 17 and supplies it to internal dev_rsp(17); bus_response then aggregates these responses into main_rsp.
  - **roles** — response record input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent 'dev_rsp(17) <= dev_17_rsp_i;' assignment and bus_response process which ORs fields into tmp_v.

**`dev_17_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies the ack bit from device 17 into internal dev_rsp(17); bus_response ORs dev_rsp(i).ack into tmp_v.ack for the aggregated main response.
  - **roles** — ack input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(17) <= dev_17_rsp_i;' and bus_response process ORs ack bits.

**`dev_17_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies 32-bit response data from device 17 into internal dev_rsp(17).data; bus_response OR-aggregates into main_rsp.data.
  - **roles** — response data input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(17) <= dev_17_rsp_i;' and bus_response process ORs dev_rsp(i).data into tmp_v.data.

**`dev_17_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies the err bit from device 17 into internal dev_rsp(17); bus_response ORs dev_rsp(i).err into the aggregated main response error flag.
  - **roles** — error input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(17) <= dev_17_rsp_i;' assignment and bus_response aggregation logic.

**`dev_18_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the complete device-18 request record to the peripheral by forwarding the internal dev_req(18) record derived from main_req and address decode.
  - **roles** — request record output; forwards internal dev_req(18); crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_18_req_o <= dev_req(18);' in the concurrent assignments.

**`dev_18_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit address from internal dev_req(18) to device 18; address is carried from routed main_req.
  - **roles** — address field output; forwards routed request address; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_18_req_o <= dev_req(18);' concurrent assignment wires this field to the port.

**`dev_18_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the AMO bit from internal dev_req(18) to the peripheral; carried combinationally from main_req.
  - **roles** — AMO flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_18_req_o <= dev_req(18);' concurrent assignment includes this field.

**`dev_18_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit AMO opcode from internal dev_req(18) to device 18; carried unchanged from routed main_req.
  - **roles** — AMO opcode output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_18_req_o <= dev_req(18);' concurrent assignment wiring internal fields to ports.

**`dev_18_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit byte-enable field from internal dev_req(18) to the device; carried unchanged from routed main_req.
  - **roles** — byte-enable output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_18_req_o <= dev_req(18);' concurrent assignment includes this field.

**`dev_18_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit write data from internal dev_req(18) to the device; carried combinationally from main_req.
  - **roles** — data field output; forwards routed write data; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of the concurrent assignment 'dev_18_req_o <= dev_req(18);'.

**`dev_18_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the debug bit from internal dev_req(18) to the device; carried unchanged from the routed main_req.
  - **roles** — debug flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Delivered as part of the record assignment 'dev_18_req_o <= dev_req(18);'.

**`dev_18_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the fence bit from internal dev_req(18) to device 18; carried unchanged from the routed main_req.
  - **roles** — fence flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_18_req_o <= dev_req(18);' concurrent assignment wires this field to the port.

**`dev_18_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock bit from internal dev_req(18) to the external device; carried combinationally from routed main_req.
  - **roles** — lock flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in 'dev_18_req_o <= dev_req(18);' concurrent assignment.

**`dev_18_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the privilege bit from internal dev_req(18) to the external device; the bit is carried combinationally from the routed main_req.
  - **roles** — privilege flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_18_req_o <= dev_req(18);' concurrent assignment includes this field.

**`dev_18_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards read/write bit from internal dev_req(18) to the peripheral; carried combinationally from main_req.
  - **roles** — rw flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the concurrent record assignment 'dev_18_req_o <= dev_req(18);'.

**`dev_18_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source bit from internal dev_req(18) to the device; field carried unchanged from routed main_req.
  - **roles** — source field output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of 'dev_18_req_o <= dev_req(18);' concurrent assignment wiring.

**`dev_18_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives stb to device 18 from internal dev_req(18).stb; that bit is asserted only when the routed main_req address matches device 18's base as set by address decode.
  - **roles** — strobe output; reflects address-qualified request; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — bus_request process conditionally assigns dev_req(i).stb; 'dev_18_req_o <= dev_req(18);' forwards it.

**`dev_18_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Receives the response record from device 18 and supplies it to internal dev_rsp(18); bus_response aggregates dev_rsp entries into the main response.
  - **roles** — response record input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_rsp(18) <= dev_18_rsp_i;' and bus_response process OR-aggregates dev_rsp fields.

**`dev_18_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies dev 18's ack bit into internal dev_rsp(18); bus_response ORs dev_rsp(i).ack into the aggregated main response ack.
  - **roles** — ack input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(18) <= dev_18_rsp_i;' plus bus_response process OR-aggregating ack bits.

**`dev_18_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies 32-bit response data from device 18 into internal dev_rsp(18).data; bus_response OR-aggregates this into the combined main response data.
  - **roles** — response data input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(18) <= dev_18_rsp_i;' and bus_response process which ORs dev_rsp(i).data into tmp_v.data.

**`dev_18_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies dev 18's err bit into internal dev_rsp(18); bus_response ORs dev_rsp(i).err into tmp_v.err for the aggregated main response.
  - **roles** — error input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(18) <= dev_18_rsp_i;' and bus_response process ORs err bits.

**`dev_19_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the complete device-19 request record to the peripheral by forwarding internal dev_req(19) derived from main_req and address decode.
  - **roles** — request record output; forwards internal dev_req(19); crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_19_req_o <= dev_req(19);' in the concurrent region.

**`dev_19_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit address from internal dev_req(19) to the device; address is carried from routed main_req.
  - **roles** — address field output; forwards routed request address; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_19_req_o <= dev_req(19);' concurrent assignment wires this field to the port.

**`dev_19_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the AMO bit from internal dev_req(19) to the peripheral; carried combinationally from main_req.
  - **roles** — AMO flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_19_req_o <= dev_req(19);' concurrent assignment includes this field.

**`dev_19_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit AMO opcode from internal dev_req(19) to device 19; carried unchanged from main_req.
  - **roles** — AMO opcode output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_19_req_o <= dev_req(19);' concurrent assignment wiring internal fields to ports.

**`dev_19_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit byte-enable from internal dev_req(19) to device 19; carried unchanged from routed main_req.
  - **roles** — byte-enable output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_19_req_o <= dev_req(19);' concurrent assignment includes this field.

**`dev_19_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit data field from internal dev_req(19) to the external device; carried combinationally from main_req.
  - **roles** — data field output; forwards routed write data; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the concurrent assignment 'dev_19_req_o <= dev_req(19);'.

**`dev_19_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the debug bit from internal dev_req(19) to the device; carried unchanged from routed main_req.
  - **roles** — debug flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the concurrent assignment 'dev_19_req_o <= dev_req(19);'.

**`dev_19_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the fence bit from internal dev_req(19) to device 19; carried unchanged from routed main_req.
  - **roles** — fence flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_19_req_o <= dev_req(19);' concurrent assignment wires this field to the port.

**`dev_19_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock bit from internal dev_req(19) to the peripheral; field carried combinationally from routed main_req.
  - **roles** — lock flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the concurrent assignment 'dev_19_req_o <= dev_req(19);'.

**`dev_19_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the privilege bit from internal dev_req(19) to the external device; carried combinationally from main_req.
  - **roles** — privilege flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_19_req_o <= dev_req(19);' concurrent assignment wires this field to the port.

**`dev_19_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the rw bit from internal dev_req(19) to the peripheral; carried combinationally from the routed main_req.
  - **roles** — rw flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_19_req_o <= dev_req(19);' concurrent assignment includes this field.

**`dev_19_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source bit from internal dev_req(19) to device 19; field carried unchanged from routed main_req.
  - **roles** — source field output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Part of 'dev_19_req_o <= dev_req(19);' concurrent assignment wiring internal request to the port.

**`dev_19_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives stb to device 19 from internal dev_req(19).stb; that bit is asserted only when main_req address matches device 19 base per bus_request logic.
  - **roles** — strobe output; reflects address-qualified request; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — bus_request process sets dev_req(i).stb conditionally; 'dev_19_req_o <= dev_req(19);' forwards it.

**`dev_19_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Receives the response record from device 19 and supplies it to internal dev_rsp(19); bus_response OR-aggregates dev_rsp entries into the main response.
  - **roles** — response record input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_rsp(19) <= dev_19_rsp_i;' and bus_response process that ORs fields.

**`dev_19_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies dev 19's ack bit into internal dev_rsp(19); bus_response ORs it into the aggregated main response ack.
  - **roles** — ack input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(19) <= dev_19_rsp_i;' and bus_response OR-aggregation of ack bits.

**`dev_19_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies 32-bit response data from device 19 into internal dev_rsp(19).data; bus_response OR-aggregates into main_rsp.data.
  - **roles** — response data input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(19) <= dev_19_rsp_i;' and bus_response OR-aggregates data fields.

**`dev_19_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies dev 19's err bit into internal dev_rsp(19); bus_response ORs dev_rsp(i).err into the combined main response error.
  - **roles** — error input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(19) <= dev_19_rsp_i;' and bus_response process which ORs err bits.

**`dev_20_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the complete device-20 request record to the peripheral by forwarding internal dev_req(20) derived from main_req and address decode.
  - **roles** — request record output; forwards internal dev_req(20); crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_20_req_o <= dev_req(20);' present in the concurrent assignments.

**`dev_20_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit address from internal dev_req(20) to device 20; the address is carried from routed main_req.
  - **roles** — address field output; forwards routed request address; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_20_req_o <= dev_req(20);' concurrent assignment wiring internal fields to the port.

**`dev_20_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the AMO bit from internal dev_req(20) to the device; carried combinationally from main_req.
  - **roles** — AMO flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_20_req_o <= dev_req(20);' concurrent assignment includes this field.

**`dev_20_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit AMO opcode from internal dev_req(20) to device 20; carried unchanged from routed main_req.
  - **roles** — AMO opcode output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_20_req_o <= dev_req(20);' concurrent assignment wiring internal fields to ports.

**`dev_20_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit byte-enable from internal dev_req(20) to device 20; carried unchanged from routed main_req.
  - **roles** — byte-enable output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_20_req_o <= dev_req(20);' concurrent assignment includes this field.

**`dev_20_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards 32-bit write data from internal dev_req(20) to the external device; carried combinationally from main_req.
  - **roles** — data field output; forwards routed write data; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in the concurrent assignment 'dev_20_req_o <= dev_req(20);'.

**`dev_20_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the debug bit from internal dev_req(20) to the peripheral; carried unchanged from routed main_req.
  - **roles** — debug flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Included in 'dev_20_req_o <= dev_req(20);' concurrent assignment.

**`dev_20_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the fence bit from internal dev_req(20) to device 20; carried unchanged from routed main_req.
  - **roles** — fence flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_20_req_o <= dev_req(20);' concurrent assignment wires this field to the port.

**`dev_20_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock bit from internal dev_req(20) to the peripheral; field carried combinationally from routed main_req.
  - **roles** — lock flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_20_req_o <= dev_req(20);' concurrent assignment includes this field.

**`dev_20_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the privilege bit from internal dev_req(20) to the external device; carried combinationally from routed main_req.
  - **roles** — privilege flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_20_req_o <= dev_req(20);' concurrent assignment includes this field.

**`dev_20_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the rw bit from internal dev_req(20) to the device; carried combinationally from routed main_req.
  - **roles** — rw flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_20_req_o <= dev_req(20);' concurrent assignment includes this field.

**`dev_20_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source bit from internal dev_req(20) to device 20; field carried unchanged from routed main_req.
  - **roles** — source field output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_20_req_o <= dev_req(20);' concurrent assignment wiring internal fields to port.

**`dev_20_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives stb to device 20 from internal dev_req(20).stb; asserted only when main_req address matches device 20 base per bus_request logic.
  - **roles** — strobe output; reflects address-qualified request; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — bus_request generate conditionally assigns dev_req(i).stb; 'dev_20_req_o <= dev_req(20);' forwards it.

**`dev_20_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Receives device 20's response record and supplies it to internal dev_rsp(20); bus_response aggregates dev_rsp entries into the final main response.
  - **roles** — response record input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_rsp(20) <= dev_20_rsp_i;' and bus_response process OR-aggregates dev_rsp fields.

**`dev_20_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies device 20's ack into internal dev_rsp(20); bus_response ORs dev_rsp(i).ack into the aggregated main response ack.
  - **roles** — ack input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(20) <= dev_20_rsp_i;' and bus_response OR-aggregates ack bits.

**`dev_20_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies 32-bit response data from device 20 into internal dev_rsp(20).data; bus_response OR-aggregates into the combined main response data.
  - **roles** — response data input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(20) <= dev_20_rsp_i;' and bus_response OR-aggregates data fields into tmp_v.data.

**`dev_20_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies device 20's err bit into internal dev_rsp(20); bus_response ORs dev_rsp(i).err into the aggregated main response error.
  - **roles** — error input; feeds response aggregation; crosses boundary (input)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_rsp(20) <= dev_20_rsp_i;' and bus_response process OR-aggregating err bits.

**`dev_21_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the device-21 request record to the peripheral by forwarding internal dev_req(21) which is derived from main_req and address decoding.
  - **roles** — request record output; forwards internal dev_req(21); crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment 'dev_21_req_o <= dev_req(21);' in the concurrent wiring section.

**`dev_21_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards the 32-bit address field from internal dev_req(21) to device 21; the address is carried from the routed main_req.
  - **roles** — address field output; forwards routed request address; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_21_req_o <= dev_req(21);' concurrent assignment wiring internal fields to the port.

**`dev_21_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs the internal dev_req(21).amo value to the external device port, forwarding the routed request's AMO indicator combinationally as part of the device request record.
  - **roles** — output interface; carries request bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_21_req_o <= dev_req(21); (see dev_00..dev_31 assignments).

**`dev_21_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs the internal dev_req(21).amoop vector to the external device port, forwarding the routed request's AMO opcode combinationally as part of the request record.
  - **roles** — output interface; carries request field combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_21_req_o <= dev_req(21); (see dev_00..dev_31 assignments).

**`dev_21_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the 4-bit byte-enable from internal dev_req(21) to device 21; carried unchanged from routed main_req.
  - **roles** — byte-enable output; forwards routed control bits; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_21_req_o <= dev_req(21);' concurrent assignment wiring internal record to port.

**`dev_21_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Forwards 32-bit data from internal dev_req(21) to the external device; carried combinationally from main_req.
  - **roles** — data field output; forwards routed write data; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_21_req_o <= dev_req(21);' concurrent assignment includes this field.

**`dev_21_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs the internal dev_req(21).debug value to the external device port, forwarding the routed request's debug bit combinationally. It is part of the device request record emitted to the device.
  - **roles** — output interface; carries request bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_21_req_o <= dev_req(21); (see dev_00..dev_31 assignments).

**`dev_21_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs the internal dev_req(21).fence value to the external device port, forwarding the routed request's fence bit combinationally as part of the device request record.
  - **roles** — output interface; carries request bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_21_req_o <= dev_req(21); (see dev_00..dev_31 assignments).

**`dev_21_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs the internal dev_req(21).lock value to the external device port, forwarding the routed request's lock bit combinationally as part of the device request record.
  - **roles** — output interface; carries request bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_21_req_o <= dev_req(21); (see dev_00..dev_31 assignments).

**`dev_21_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the privilege bit from internal dev_req(21) to the external device; the bit is carried combinationally from routed main_req.
  - **roles** — privilege flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_21_req_o <= dev_req(21);' concurrent assignment includes this field.

**`dev_21_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the rw bit from internal dev_req(21) to the peripheral; carried combinationally from routed main_req.
  - **roles** — rw flag output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_21_req_o <= dev_req(21);' concurrent assignment includes this field.

**`dev_21_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the source bit from internal dev_req(21) to device 21; field carried unchanged from routed main_req.
  - **roles** — source field output; forwards routed control bit; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — 'dev_21_req_o <= dev_req(21);' concurrent assignment wiring internal request to port.

**`dev_21_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives stb to device 21 from internal dev_req(21).stb; asserted only when main_req address matches device 21 base as set by the bus_request generate.
  - **roles** — strobe output; reflects address-qualified request; crosses boundary (output)
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — bus_request process conditionally assigns dev_req(i).stb; 'dev_21_req_o <= dev_req(21);' forwards it.

**`dev_21_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Provides the incoming device response record into the entity via dev_rsp(21) <= dev_21_rsp_i and thus supplies response fields that are aggregated into main_rsp. The whole record is sampled combinationally into the internal response array.
  - **roles** — input interface; supplies response to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Assignment dev_rsp(21) <= dev_21_rsp_i; and bus_response process that aggregates dev_rsp(i) into main_rsp.

**`dev_21_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_21_rsp_i.ack into the internal dev_rsp(21).ack via assignment dev_rsp(21) <= dev_21_rsp_i; that ack bit is then OR-aggregated into the main response (main_rsp) in bus_response.
  - **roles** — input interface; supplies response bit to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Assignment dev_rsp(21) <= dev_21_rsp_i; bus_response process reads dev_rsp(i).ack and ORs into tmp_v. (see dev_* assignments and bus_response).

**`dev_21_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides dev_21_rsp_i.data into internal dev_rsp(21).data via dev_rsp(21) <= dev_21_rsp_i; that data word is OR-aggregated with other device data into tmp_v.data and driven to main_rsp.
  - **roles** — input interface; supplies data to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Assignment dev_rsp(21) <= dev_21_rsp_i; bus_response process ORs dev_rsp(i).data into tmp_v.data.

**`dev_21_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_21_rsp_i.err into internal dev_rsp(21).err via dev_rsp(21) <= dev_21_rsp_i; that error bit is then OR-aggregated into the main response in the bus_response process.
  - **roles** — input interface; supplies error bit to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Assignment dev_rsp(21) <= dev_21_rsp_i; bus_response process reads dev_rsp(i).err and ORs into tmp_v.

**`dev_22_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the external device request port with the internal dev_req(22) record via continuous assignment, forwarding the routed request combinationally to the device.
  - **roles** — output interface; carries request record combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (see dev_00..dev_31 assignments).

**`dev_22_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(22).addr to the external device port by the continuous assignment dev_22_req_o <= dev_req(22), forwarding the routed address combinationally.
  - **roles** — output interface; carries address combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (dev_22 mapping in dev_00..dev_31 assignments).

**`dev_22_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(22).amo to the external device port by forwarding the internal request record via dev_22_req_o <= dev_req(22), carrying the AMO indicator combinationally.
  - **roles** — output interface; carries AMO flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (dev_22 mapping).

**`dev_22_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(22).amoop to the external device port by forwarding the internal request record via dev_22_req_o <= dev_req(22), carrying the AMO opcode combinationally.
  - **roles** — output interface; carries AMO opcode combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (dev_22 mapping).

**`dev_22_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(22).ben to the external device port by forwarding the internal request record via dev_22_req_o <= dev_req(22), passing through the byte-enable field combinationally.
  - **roles** — output interface; carries byte-enable combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (dev_22 mapping).

**`dev_22_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(22).data to the external device port via the continuous assignment dev_22_req_o <= dev_req(22), forwarding the routed data word combinationally.
  - **roles** — output interface; carries data combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (dev_22 mapping in dev_00..dev_31 assignments).

**`dev_22_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(22).debug to the external device port by forwarding the internal request record via dev_22_req_o <= dev_req(22), passing the debug bit combinationally.
  - **roles** — output interface; carries debug bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (dev_22 mapping).

**`dev_22_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(22).fence to the external device port by forwarding the internal request record via dev_22_req_o <= dev_req(22), carrying the fence bit combinationally.
  - **roles** — output interface; carries fence bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (dev_22 mapping).

**`dev_22_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(22).lock to the external device port by forwarding the internal request record via dev_22_req_o <= dev_req(22), delivering the lock bit combinationally.
  - **roles** — output interface; carries lock bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (dev_22 mapping).

**`dev_22_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(22).priv to the external device port by forwarding the internal request record via dev_22_req_o <= dev_req(22), delivering the privilege bit combinationally.
  - **roles** — output interface; carries privilege flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (dev_22 mapping).

**`dev_22_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(22).rw to the external device port by forwarding the internal request record via dev_22_req_o <= dev_req(22), delivering the read/write indicator combinationally.
  - **roles** — output interface; carries rw flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (dev_22 mapping).

**`dev_22_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(22).src to the external device port by forwarding the internal request record via dev_22_req_o <= dev_req(22), passing the source flag combinationally.
  - **roles** — output interface; carries source flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_22_req_o <= dev_req(22); (dev_22 mapping).

**`dev_22_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs the strobe bit from internal dev_req(22).stb to the external device port; the internal dev_req(22).stb is controlled by address comparison inside the bus_request process before being forwarded here.
  - **roles** — output interface; carries write strobe combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_22_req_o <= dev_req(22); dev_req(22).stb is set in bus_request process with address comparison.

**`dev_22_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Provides the incoming device response record into the entity via dev_rsp(22) <= dev_22_rsp_i; the response fields are then aggregated by the bus_response process into main_rsp.
  - **roles** — input interface; supplies response record to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Assignment dev_rsp(22) <= dev_22_rsp_i; bus_response process aggregates dev_rsp(i) into tmp_v/main_rsp.

**`dev_22_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_22_rsp_i.ack into internal dev_rsp(22).ack via assignment and that ack is OR-aggregated into the main response in bus_response.
  - **roles** — input interface; supplies ack to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(22) <= dev_22_rsp_i; bus_response reads dev_rsp(i).ack and ORs into tmp_v.

**`dev_22_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides dev_22_rsp_i.data into internal dev_rsp(22).data via assignment; that data word is OR-aggregated with other device data into tmp_v.data driven to main_rsp.
  - **roles** — input interface; supplies data to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(22) <= dev_22_rsp_i; bus_response ORs dev_rsp(i).data into tmp_v.data.

**`dev_22_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_22_rsp_i.err into internal dev_rsp(22).err via assignment and that error bit is OR-aggregated into the main response in bus_response.
  - **roles** — input interface; supplies error to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(22) <= dev_22_rsp_i; bus_response reads dev_rsp(i).err and ORs into tmp_v.

**`dev_23_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the external dev_23_req_o port with the internal dev_req(23) record via continuous assignment, forwarding the routed request combinationally to the device.
  - **roles** — output interface; carries request record combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (see dev_00..dev_31 assignments).

**`dev_23_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(23).addr to the external device port via the record forwarding dev_23_req_o <= dev_req(23), passing the address field combinationally.
  - **roles** — output interface; carries address combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (dev_23 mapping).

**`dev_23_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(23).amo to the device port by forwarding internal dev_req(23) via dev_23_req_o <= dev_req(23), carrying the AMO indicator combinationally.
  - **roles** — output interface; carries AMO flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (dev_23 mapping).

**`dev_23_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(23).amoop to the device port by forwarding internal dev_req(23) via dev_23_req_o <= dev_req(23), carrying the AMO opcode combinationally.
  - **roles** — output interface; carries AMO opcode combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (dev_23 mapping).

**`dev_23_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(23).ben to the external device port by forwarding the internal request record via dev_23_req_o <= dev_req(23), passing through byte-enable combinationally.
  - **roles** — output interface; carries byte-enable combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (dev_23 mapping).

**`dev_23_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(23).data to the external device port by forwarding the internal request record via dev_23_req_o <= dev_req(23), carrying the data word combinationally.
  - **roles** — output interface; carries data combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (dev_23 mapping).

**`dev_23_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(23).debug to the device port by forwarding internal dev_req(23) via dev_23_req_o <= dev_req(23), carrying the debug bit combinationally.
  - **roles** — output interface; carries debug bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (dev_23 mapping).

**`dev_23_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(23).fence to the device port by forwarding internal dev_req(23) via dev_23_req_o <= dev_req(23), carrying the fence bit combinationally.
  - **roles** — output interface; carries fence bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (dev_23 mapping).

**`dev_23_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(23).lock to the device port by forwarding internal dev_req(23) via dev_23_req_o <= dev_req(23), delivering the lock bit combinationally.
  - **roles** — output interface; carries lock bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (dev_23 mapping).

**`dev_23_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(23).priv to the device port by forwarding the internal request record via dev_23_req_o <= dev_req(23), delivering the privilege bit combinationally.
  - **roles** — output interface; carries privilege flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (dev_23 mapping).

**`dev_23_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(23).rw to the device port by forwarding the internal request record via dev_23_req_o <= dev_req(23), carrying the read/write indicator combinationally.
  - **roles** — output interface; carries rw flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (dev_23 mapping).

**`dev_23_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(23).src to the device port by forwarding the internal request record via dev_23_req_o <= dev_req(23), passing the source flag combinationally.
  - **roles** — output interface; carries source flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_23_req_o <= dev_req(23); (dev_23 mapping).

**`dev_23_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs the strobe bit from internal dev_req(23).stb to the external device port; the internal strobe is set/cleared in the bus_request process based on address match.
  - **roles** — output interface; carries strobe combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_23_req_o <= dev_req(23); bus_request process sets dev_req(i).stb based on address compare.

**`dev_23_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Provides the incoming device response into the entity via dev_rsp(23) <= dev_23_rsp_i; that record's fields are aggregated into main_rsp by the bus_response process.
  - **roles** — input interface; supplies response to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Assignment dev_rsp(23) <= dev_23_rsp_i; bus_response aggregates dev_rsp(i) into tmp_v/main_rsp.

**`dev_23_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_23_rsp_i.ack into internal dev_rsp(23).ack via assignment; bus_response ORs that ack into the aggregated main response.
  - **roles** — input interface; supplies ack to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(23) <= dev_23_rsp_i; bus_response reads dev_rsp(i).ack and ORs into tmp_v.

**`dev_23_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides dev_23_rsp_i.data into internal dev_rsp(23).data via assignment; bus_response OR-aggregates that data into tmp_v.data driven to main_rsp.
  - **roles** — input interface; supplies data to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(23) <= dev_23_rsp_i; bus_response ORs dev_rsp(i).data into tmp_v.data.

**`dev_23_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_23_rsp_i.err into internal dev_rsp(23).err via assignment; bus_response ORs that error bit into the aggregated main response.
  - **roles** — input interface; supplies error to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(23) <= dev_23_rsp_i; bus_response reads dev_rsp(i).err and ORs into tmp_v.

**`dev_24_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the external dev_24_req_o port with the internal dev_req(24) record via continuous assignment, forwarding the routed request combinationally to the device.
  - **roles** — output interface; carries request record combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (see dev_00..dev_31 assignments).

**`dev_24_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(24).addr to the device port by forwarding the internal request record via dev_24_req_o <= dev_req(24), passing the address combinationally.
  - **roles** — output interface; carries address combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (dev_24 mapping).

**`dev_24_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(24).amo to the device port by forwarding internal dev_req(24) via dev_24_req_o <= dev_req(24), carrying the AMO indicator combinationally.
  - **roles** — output interface; carries AMO flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (dev_24 mapping).

**`dev_24_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(24).amoop to the device port by forwarding internal dev_req(24) via dev_24_req_o <= dev_req(24), carrying the AMO opcode combinationally.
  - **roles** — output interface; carries AMO opcode combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (dev_24 mapping).

**`dev_24_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(24).ben to the device port by forwarding internal dev_req(24) via dev_24_req_o <= dev_req(24), passing the byte-enable field combinationally.
  - **roles** — output interface; carries byte-enable combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (dev_24 mapping).

**`dev_24_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(24).data to the device port by forwarding internal dev_req(24) via dev_24_req_o <= dev_req(24), carrying the data word combinationally.
  - **roles** — output interface; carries data combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (dev_24 mapping).

**`dev_24_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(24).debug to the device port by forwarding internal dev_req(24) via dev_24_req_o <= dev_req(24), carrying the debug bit combinationally.
  - **roles** — output interface; carries debug bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (dev_24 mapping).

**`dev_24_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(24).fence to the device port by forwarding internal dev_req(24) via dev_24_req_o <= dev_req(24), carrying the fence bit combinationally.
  - **roles** — output interface; carries fence bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (dev_24 mapping).

**`dev_24_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(24).lock to the device port by forwarding internal dev_req(24) via dev_24_req_o <= dev_req(24), delivering the lock bit combinationally.
  - **roles** — output interface; carries lock bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (dev_24 mapping).

**`dev_24_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(24).priv to the device port by forwarding internal dev_req(24) via dev_24_req_o <= dev_req(24), carrying the privilege bit combinationally.
  - **roles** — output interface; carries privilege flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (dev_24 mapping).

**`dev_24_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(24).rw to the device port by forwarding internal dev_req(24) via dev_24_req_o <= dev_req(24), carrying the rw flag combinationally.
  - **roles** — output interface; carries rw flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (dev_24 mapping).

**`dev_24_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(24).src to the device port by forwarding internal dev_req(24) via dev_24_req_o <= dev_req(24), delivering the source flag combinationally.
  - **roles** — output interface; carries source flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_24_req_o <= dev_req(24); (dev_24 mapping).

**`dev_24_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs the strobe bit from internal dev_req(24).stb to the device port; the internal strobe is computed in the bus_request process and then forwarded here.
  - **roles** — output interface; carries strobe combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_24_req_o <= dev_req(24); dev_req(24).stb set in bus_request process after address check.

**`dev_24_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Provides the incoming response record via dev_rsp(24) <= dev_24_rsp_i; its fields are aggregated into main_rsp by the bus_response process.
  - **roles** — input interface; supplies response to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Assignment dev_rsp(24) <= dev_24_rsp_i; bus_response aggregates dev_rsp entries into tmp_v/main_rsp.

**`dev_24_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_24_rsp_i.ack into dev_rsp(24).ack via assignment; bus_response ORs this ack into the aggregated main response.
  - **roles** — input interface; supplies ack to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(24) <= dev_24_rsp_i; bus_response reads dev_rsp(i).ack and ORs into tmp_v.

**`dev_24_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides dev_24_rsp_i.data into dev_rsp(24).data via assignment; bus_response OR-aggregates this data into tmp_v.data driven to main_rsp.
  - **roles** — input interface; supplies data to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(24) <= dev_24_rsp_i; bus_response ORs dev_rsp(i).data into tmp_v.data.

**`dev_24_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_24_rsp_i.err into dev_rsp(24).err via assignment; bus_response ORs this error into the aggregated main response.
  - **roles** — input interface; supplies error to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(24) <= dev_24_rsp_i; bus_response reads dev_rsp(i).err and ORs into tmp_v.

**`dev_25_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives dev_25_req_o from internal dev_req(25) via continuous assignment, forwarding the routed request combinationally to the external device.
  - **roles** — output interface; carries request record combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (see dev_00..dev_31 assignments).

**`dev_25_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(25).addr to the device port by forwarding internal dev_req(25) via dev_25_req_o <= dev_req(25), passing the address combinationally.
  - **roles** — output interface; carries address combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (dev_25 mapping).

**`dev_25_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(25).amo to the device port by forwarding internal dev_req(25) via dev_25_req_o <= dev_req(25), carrying the AMO indicator combinationally.
  - **roles** — output interface; carries AMO flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (dev_25 mapping).

**`dev_25_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(25).amoop to the device port by forwarding internal dev_req(25) via dev_25_req_o <= dev_req(25), carrying the AMO opcode combinationally.
  - **roles** — output interface; carries AMO opcode combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (dev_25 mapping).

**`dev_25_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(25).ben to the device port by forwarding internal dev_req(25) via dev_25_req_o <= dev_req(25), passing byte-enable combinationally.
  - **roles** — output interface; carries byte-enable combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (dev_25 mapping).

**`dev_25_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(25).data to the device port by forwarding internal dev_req(25) via dev_25_req_o <= dev_req(25), carrying the data word combinationally.
  - **roles** — output interface; carries data combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (dev_25 mapping).

**`dev_25_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(25).debug to the device port by forwarding internal dev_req(25) via dev_25_req_o <= dev_req(25), carrying the debug bit combinationally.
  - **roles** — output interface; carries debug bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (dev_25 mapping).

**`dev_25_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(25).fence to the device port by forwarding internal dev_req(25) via dev_25_req_o <= dev_req(25), carrying the fence bit combinationally.
  - **roles** — output interface; carries fence bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (dev_25 mapping).

**`dev_25_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(25).lock to the device port by forwarding internal dev_req(25) via dev_25_req_o <= dev_req(25), delivering the lock bit combinationally.
  - **roles** — output interface; carries lock bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (dev_25 mapping).

**`dev_25_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(25).priv to the device port by forwarding internal dev_req(25) via dev_25_req_o <= dev_req(25), carrying the privilege bit combinationally.
  - **roles** — output interface; carries privilege flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (dev_25 mapping).

**`dev_25_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(25).rw to the device port by forwarding internal dev_req(25) via dev_25_req_o <= dev_req(25), carrying the rw bit combinationally.
  - **roles** — output interface; carries rw flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (dev_25 mapping).

**`dev_25_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(25).src to the device port by forwarding internal dev_req(25) via dev_25_req_o <= dev_req(25), delivering the source flag combinationally.
  - **roles** — output interface; carries source flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_25_req_o <= dev_req(25); (dev_25 mapping).

**`dev_25_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs the strobe bit from internal dev_req(25).stb to the device port; that strobe is set in the bus_request process (address check) before being forwarded.
  - **roles** — output interface; carries strobe combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_25_req_o <= dev_req(25); dev_req(25).stb set/cleared in bus_request process.

**`dev_25_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Provides the incoming device response record into the entity via dev_rsp(25) <= dev_25_rsp_i; its fields are aggregated into main_rsp by the bus_response process.
  - **roles** — input interface; supplies response to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Assignment dev_rsp(25) <= dev_25_rsp_i; bus_response loop ORs fields into tmp_v.

**`dev_25_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_25_rsp_i.ack into internal dev_rsp(25).ack via assignment; that ack is OR-aggregated into the main response in bus_response.
  - **roles** — input interface; supplies ack to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(25) <= dev_25_rsp_i; bus_response reads and ORs dev_rsp(i).ack.

**`dev_25_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides dev_25_rsp_i.data into internal dev_rsp(25).data via assignment; bus_response OR-aggregates this data into tmp_v.data for main_rsp.
  - **roles** — input interface; supplies data to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(25) <= dev_25_rsp_i; bus_response ORs dev_rsp(i).data into tmp_v.data.

**`dev_25_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_25_rsp_i.err into internal dev_rsp(25).err via assignment; bus_response OR-aggregates this error into the main response.
  - **roles** — input interface; supplies error to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(25) <= dev_25_rsp_i; bus_response reads and ORs dev_rsp(i).err.

**`dev_26_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the external dev_26_req_o port with internal dev_req(26) via continuous assignment, forwarding the routed request combinationally to the device.
  - **roles** — output interface; carries request record combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (see dev_00..dev_31 assignments).

**`dev_26_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(26).addr to the device port by forwarding internal dev_req(26) via dev_26_req_o <= dev_req(26), passing the address combinationally.
  - **roles** — output interface; carries address combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (dev_26 mapping).

**`dev_26_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(26).amo to the device port by forwarding internal dev_req(26) via dev_26_req_o <= dev_req(26), carrying the AMO indicator combinationally.
  - **roles** — output interface; carries AMO flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (dev_26 mapping).

**`dev_26_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(26).amoop to the device port by forwarding internal dev_req(26) via dev_26_req_o <= dev_req(26), carrying the AMO opcode combinationally.
  - **roles** — output interface; carries AMO opcode combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (dev_26 mapping).

**`dev_26_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(26).ben to the device port by forwarding internal dev_req(26) via dev_26_req_o <= dev_req(26), passing byte-enable combinationally.
  - **roles** — output interface; carries byte-enable combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (dev_26 mapping).

**`dev_26_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(26).data to the device port by forwarding internal dev_req(26) via dev_26_req_o <= dev_req(26), carrying the data word combinationally.
  - **roles** — output interface; carries data combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (dev_26 mapping).

**`dev_26_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(26).debug to the device port by forwarding internal dev_req(26) via dev_26_req_o <= dev_req(26), carrying the debug bit combinationally.
  - **roles** — output interface; carries debug bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (dev_26 mapping).

**`dev_26_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(26).fence to the device port by forwarding internal dev_req(26) via dev_26_req_o <= dev_req(26), carrying the fence bit combinationally.
  - **roles** — output interface; carries fence bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (dev_26 mapping).

**`dev_26_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(26).lock to the device port by forwarding internal dev_req(26) via dev_26_req_o <= dev_req(26), delivering the lock bit combinationally.
  - **roles** — output interface; carries lock bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (dev_26 mapping).

**`dev_26_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(26).priv to the device port by forwarding internal dev_req(26) via dev_26_req_o <= dev_req(26), carrying the privilege bit combinationally.
  - **roles** — output interface; carries privilege flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (dev_26 mapping).

**`dev_26_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(26).rw to the device port by forwarding internal dev_req(26) via dev_26_req_o <= dev_req(26), carrying the rw bit combinationally.
  - **roles** — output interface; carries rw flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (dev_26 mapping).

**`dev_26_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(26).src to the device port by forwarding internal dev_req(26) via dev_26_req_o <= dev_req(26), delivering the source flag combinationally.
  - **roles** — output interface; carries source flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_26_req_o <= dev_req(26); (dev_26 mapping).

**`dev_26_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs the strobe bit from internal dev_req(26).stb to the device port; the strobe is computed in the bus_request process and then forwarded here.
  - **roles** — output interface; carries strobe combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_26_req_o <= dev_req(26); bus_request process sets dev_req(i).stb per address match.

**`dev_26_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Provides the incoming response record via dev_rsp(26) <= dev_26_rsp_i; its fields are OR-aggregated into main_rsp in bus_response.
  - **roles** — input interface; supplies response to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Assignment dev_rsp(26) <= dev_26_rsp_i; bus_response ORs dev_rsp fields into tmp_v.

**`dev_26_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_26_rsp_i.ack into dev_rsp(26).ack via assignment; bus_response OR-aggregates that ack into tmp_v for main_rsp.
  - **roles** — input interface; supplies ack to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(26) <= dev_26_rsp_i; bus_response reads dev_rsp(i).ack and ORs into tmp_v.

**`dev_26_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides dev_26_rsp_i.data into dev_rsp(26).data via assignment; bus_response OR-aggregates this data into tmp_v.data for main_rsp.
  - **roles** — input interface; supplies data to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(26) <= dev_26_rsp_i; bus_response ORs dev_rsp(i).data into tmp_v.data.

**`dev_26_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_26_rsp_i.err into dev_rsp(26).err via assignment; bus_response OR-aggregates that error into tmp_v for main_rsp.
  - **roles** — input interface; supplies error to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(26) <= dev_26_rsp_i; bus_response reads dev_rsp(i).err and ORs into tmp_v.

**`dev_27_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives dev_27_req_o from internal dev_req(27) via continuous assignment, forwarding the routed request combinationally to the device.
  - **roles** — output interface; carries request record combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (see dev_00..dev_31 assignments).

**`dev_27_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(27).addr to the device port by forwarding internal dev_req(27) via dev_27_req_o <= dev_req(27), passing the address combinationally.
  - **roles** — output interface; carries address combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (dev_27 mapping).

**`dev_27_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(27).amo to the device port by forwarding internal dev_req(27) via dev_27_req_o <= dev_req(27), carrying the AMO indicator combinationally.
  - **roles** — output interface; carries AMO flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (dev_27 mapping).

**`dev_27_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(27).amoop to the device port by forwarding internal dev_req(27) via dev_27_req_o <= dev_req(27), carrying the AMO opcode combinationally.
  - **roles** — output interface; carries AMO opcode combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (dev_27 mapping).

**`dev_27_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(27).ben to the device port by forwarding internal dev_req(27) via dev_27_req_o <= dev_req(27), passing byte-enable combinationally.
  - **roles** — output interface; carries byte-enable combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (dev_27 mapping).

**`dev_27_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(27).data to the device port by forwarding internal dev_req(27) via dev_27_req_o <= dev_req(27), carrying the data word combinationally.
  - **roles** — output interface; carries data combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (dev_27 mapping).

**`dev_27_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(27).debug to the device port by forwarding internal dev_req(27) via dev_27_req_o <= dev_req(27), carrying the debug bit combinationally.
  - **roles** — output interface; carries debug bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (dev_27 mapping).

**`dev_27_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(27).fence to the device port by forwarding internal dev_req(27) via dev_27_req_o <= dev_req(27), carrying the fence bit combinationally.
  - **roles** — output interface; carries fence bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (dev_27 mapping).

**`dev_27_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(27).lock to the device port by forwarding internal dev_req(27) via dev_27_req_o <= dev_req(27), delivering the lock bit combinationally.
  - **roles** — output interface; carries lock bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (dev_27 mapping).

**`dev_27_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(27).priv to the device port by forwarding internal dev_req(27) via dev_27_req_o <= dev_req(27), carrying the privilege bit combinationally.
  - **roles** — output interface; carries privilege flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (dev_27 mapping).

**`dev_27_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(27).rw to the device port by forwarding internal dev_req(27) via dev_27_req_o <= dev_req(27), carrying the rw bit combinationally.
  - **roles** — output interface; carries rw flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (dev_27 mapping).

**`dev_27_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(27).src to the device port by forwarding internal dev_req(27) via dev_27_req_o <= dev_req(27), delivering the source flag combinationally.
  - **roles** — output interface; carries source flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_27_req_o <= dev_req(27); (dev_27 mapping).

**`dev_27_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs the strobe bit from internal dev_req(27).stb to the device port; the strobe is determined in the bus_request process and forwarded here.
  - **roles** — output interface; carries strobe combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_27_req_o <= dev_req(27); dev_req(27).stb set in bus_request process based on address match.

**`dev_27_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Provides the incoming response record via dev_rsp(27) <= dev_27_rsp_i; bus_response aggregates the fields into main_rsp.
  - **roles** — input interface; supplies response to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(27) <= dev_27_rsp_i; bus_response loop ORs dev_rsp fields into tmp_v/main_rsp.

**`dev_27_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_27_rsp_i.ack into internal dev_rsp(27).ack via assignment; bus_response ORs that ack into the aggregated main response.
  - **roles** — input interface; supplies ack to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(27) <= dev_27_rsp_i; bus_response reads and ORs dev_rsp(i).ack.

**`dev_27_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides dev_27_rsp_i.data into internal dev_rsp(27).data via assignment; bus_response OR-aggregates that data into tmp_v.data for main_rsp.
  - **roles** — input interface; supplies data to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(27) <= dev_27_rsp_i; bus_response ORs dev_rsp(i).data into tmp_v.data.

**`dev_27_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_27_rsp_i.err into internal dev_rsp(27).err via assignment; bus_response OR-aggregates that error into the main response.
  - **roles** — input interface; supplies error to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(27) <= dev_27_rsp_i; bus_response reads and ORs dev_rsp(i).err.

**`dev_28_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives dev_28_req_o from internal dev_req(28) via continuous assignment, forwarding the routed request combinationally to the device.
  - **roles** — output interface; carries request record combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (see dev_00..dev_31 assignments).

**`dev_28_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(28).addr to the device port by forwarding internal dev_req(28) via dev_28_req_o <= dev_req(28), passing the address combinationally.
  - **roles** — output interface; carries address combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (dev_28 mapping).

**`dev_28_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(28).amo to the device port by forwarding internal dev_req(28) via dev_28_req_o <= dev_req(28), carrying the AMO indicator combinationally.
  - **roles** — output interface; carries AMO flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (dev_28 mapping).

**`dev_28_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(28).amoop to the device port by forwarding internal dev_req(28) via dev_28_req_o <= dev_req(28), carrying the AMO opcode combinationally.
  - **roles** — output interface; carries AMO opcode combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (dev_28 mapping).

**`dev_28_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs dev_req(28).ben to the device port by forwarding internal dev_req(28) via dev_28_req_o <= dev_req(28), passing byte-enable combinationally.
  - **roles** — output interface; carries byte-enable combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (dev_28 mapping).

**`dev_28_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs dev_req(28).data to the device port by forwarding internal dev_req(28) via dev_28_req_o <= dev_req(28), carrying the data word combinationally.
  - **roles** — output interface; carries data combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (dev_28 mapping).

**`dev_28_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(28).debug to the device port by forwarding internal dev_req(28) via dev_28_req_o <= dev_req(28), carrying the debug bit combinationally.
  - **roles** — output interface; carries debug bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (dev_28 mapping).

**`dev_28_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(28).fence to the device port by forwarding internal dev_req(28) via dev_28_req_o <= dev_req(28), carrying the fence bit combinationally.
  - **roles** — output interface; carries fence bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (dev_28 mapping).

**`dev_28_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(28).lock to the device port by forwarding internal dev_req(28) via dev_28_req_o <= dev_req(28), delivering the lock bit combinationally.
  - **roles** — output interface; carries lock bit combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (dev_28 mapping).

**`dev_28_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(28).priv to the device port by forwarding internal dev_req(28) via dev_28_req_o <= dev_req(28), carrying the privilege bit combinationally.
  - **roles** — output interface; carries privilege flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (dev_28 mapping).

**`dev_28_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(28).rw to the device port by forwarding internal dev_req(28) via dev_28_req_o <= dev_req(28), carrying the rw bit combinationally.
  - **roles** — output interface; carries rw flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (dev_28 mapping).

**`dev_28_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs dev_req(28).src to the device port by forwarding internal dev_req(28) via dev_28_req_o <= dev_req(28), delivering the source flag combinationally.
  - **roles** — output interface; carries source flag combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — Continuous assignment dev_28_req_o <= dev_req(28); (dev_28 mapping).

**`dev_28_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Outputs the strobe bit from internal dev_req(28).stb to the device port; the strobe is computed in the bus_request process and then forwarded here.
  - **roles** — output interface; carries strobe combinationally; crosses boundary outward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_28_req_o <= dev_req(28); dev_req(28).stb set/cleared in bus_request process.

**`dev_28_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Provides the incoming device response record via dev_rsp(28) <= dev_28_rsp_i; its fields are OR-aggregated by bus_response into main_rsp.
  - **roles** — input interface; supplies response to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(28) <= dev_28_rsp_i; bus_response process ORs dev_rsp fields into tmp_v/main_rsp.

**`dev_28_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_28_rsp_i.ack into dev_rsp(28).ack via assignment; bus_response ORs that ack into the aggregated main response.
  - **roles** — input interface; supplies ack to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(28) <= dev_28_rsp_i; bus_response reads dev_rsp(i).ack and ORs into tmp_v.

**`dev_28_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides dev_28_rsp_i.data into dev_rsp(28).data via assignment; bus_response OR-aggregates this data into tmp_v.data for main_rsp.
  - **roles** — input interface; supplies data to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(28) <= dev_28_rsp_i; bus_response ORs dev_rsp(i).data into tmp_v.data.

**`dev_28_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides dev_28_rsp_i.err into dev_rsp(28).err via assignment; bus_response OR-aggregates that error into the main response.
  - **roles** — input interface; supplies error to aggregator; crosses boundary inward
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — dev_rsp(28) <= dev_28_rsp_i; bus_response reads dev_rsp(i).err and ORs into tmp_v.

**`dev_29_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the external device-29 request port from the internal dev_req(29) vector; forwards the per-device request record to the device boundary combinationally.
  - **roles** — exports request to device 29; carries request combinationally
  - **relationships** — **CARRIES** → dev_req; **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment dev_29_req_o <= dev_req(29); binds internal dev_req(29) to port.

**`dev_29_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the address field of dev_req(29) to the device port; the field is the addr slice of the internal dev_req element and therefore forwarded outwards.
  - **roles** — exports request address; carries address field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29) concurrent assignment forwards the addr field.

**`dev_29_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the amo field from internal dev_req(29) to the device port, carrying the atomic-op indicator.
  - **roles** — exports amo flag; carries amo
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29) concurrent assignment forwards the amo field.

**`dev_29_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the amoop field vector from internal dev_req(29) to the device port, carrying AMO operation code bits.
  - **roles** — exports amoop field; carries amoop
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29) concurrent assignment forwards the amoop field.

**`dev_29_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the ben field from internal dev_req(29) to the device port, carrying byte-enable bits outwards.
  - **roles** — exports byte-enable; carries ben field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29) concurrent assignment forwards the ben field.

**`dev_29_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the data field of dev_req(29) to the external device port; forwards internal request data unchanged.
  - **roles** — exports request data; carries data field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29) concurrent assignment forwards the data field.

**`dev_29_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the debug field from internal dev_req(29) to the device port, carrying the debug indicator.
  - **roles** — exports debug flag; carries debug
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29) concurrent assignment forwards the debug field.

**`dev_29_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the fence field from internal dev_req(29) to the device port, carrying fence control bit outward.
  - **roles** — exports fence flag; carries fence
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29) concurrent assignment forwards the fence field.

**`dev_29_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock field from internal dev_req(29) to the device port, carrying the lock indicator outward.
  - **roles** — exports lock flag; carries lock
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29) concurrent assignment forwards the lock field.

**`dev_29_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the priv field from internal dev_req(29) to the device port, carrying privilege bit outward.
  - **roles** — exports priv bit; carries priv
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29) concurrent assignment forwards the priv field.

**`dev_29_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the rw field from internal dev_req(29) to the device port unchanged, carrying the read/write indicator outward.
  - **roles** — exports rw flag; carries rw field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29) concurrent assignment forwards the rw field.

**`dev_29_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the src field from internal dev_req(29) to the external device port, carrying the request source indicator.
  - **roles** — exports src field; carries src
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29) concurrent assignment forwards the src field.

**`dev_29_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the device strobe from the internal dev_req(29).stb value which is produced by the per-device request generator (either main_req.stb or '0').
  - **roles** — exports request strobe; carries gated stb field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_29_req_o <= dev_req(29); dev_req(29).stb is assigned in bus_request process from main_req.stb or '0'.

**`dev_29_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Accepts the external device-29 response record and provides it to the internal dev_rsp(29) element for aggregation into the host response.
  - **roles** — imports response from device 29; sources internal dev_rsp element
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — Concurrent assignment dev_rsp(29) <= dev_29_rsp_i; maps port into internal dev_rsp array.

**`dev_29_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies the ack bit from the device 29 response into dev_rsp(29).ack, which is later ORed into the aggregated main response.
  - **roles** — imports ack bit; sources aggregator input
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — dev_rsp(29) <= dev_29_rsp_i concurrent assignment; bus_response process ORs dev_rsp(i).ack into tmp_v.ack.

**`dev_29_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the response data vector from device 29 into dev_rsp(29).data, which is ORed into the aggregated main response data.
  - **roles** — imports response data; sources aggregated data
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — dev_rsp(29) <= dev_29_rsp_i concurrent assignment; bus_response process ORs dev_rsp(i).data into tmp_v.data.

**`dev_29_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies the err bit from device 29 into dev_rsp(29).err for the response aggregation that drives main_rsp.
  - **roles** — imports err bit; sources aggregator input
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — dev_rsp(29) <= dev_29_rsp_i concurrent assignment; bus_response process ORs dev_rsp(i).err into tmp_v.err.

**`dev_30_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the external device-30 request port from the internal dev_req(30) vector; forwards the per-device request record to the device boundary combinationally.
  - **roles** — exports request to device 30; carries request combinationally
  - **relationships** — **CARRIES** → dev_req; **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment dev_30_req_o <= dev_req(30); binds internal dev_req(30) to port.

**`dev_30_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the address field of dev_req(30) to the device port; the field is forwarded unchanged from the internal dev_req element.
  - **roles** — exports request address; carries address field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30) concurrent assignment forwards the addr field.

**`dev_30_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the amo field from internal dev_req(30) to the device port, carrying the atomic-op indicator.
  - **roles** — exports amo flag; carries amo
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30) concurrent assignment forwards the amo field.

**`dev_30_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the amoop field vector from internal dev_req(30) to the device port, carrying AMO operation code bits.
  - **roles** — exports amoop field; carries amoop
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30) concurrent assignment forwards the amoop field.

**`dev_30_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the ben field from internal dev_req(30) to the device port, carrying byte-enable bits outwards.
  - **roles** — exports byte-enable; carries ben field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30) concurrent assignment forwards the ben field.

**`dev_30_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the data field of dev_req(30) to the external device port; forwards internal request data unchanged.
  - **roles** — exports request data; carries data field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30) concurrent assignment forwards the data field.

**`dev_30_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the debug field from internal dev_req(30) to the device port, carrying the debug indicator.
  - **roles** — exports debug flag; carries debug
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30) concurrent assignment forwards the debug field.

**`dev_30_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the fence field from internal dev_req(30) to the device port, carrying fence control bit outward.
  - **roles** — exports fence flag; carries fence
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30) concurrent assignment forwards the fence field.

**`dev_30_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock field from internal dev_req(30) to the device port, carrying the lock indicator outward.
  - **roles** — exports lock flag; carries lock
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30) concurrent assignment forwards the lock field.

**`dev_30_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the priv field from internal dev_req(30) to the device port, carrying privilege bit outward.
  - **roles** — exports priv bit; carries priv
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30) concurrent assignment forwards the priv field.

**`dev_30_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the rw field from internal dev_req(30) to the device port unchanged, carrying the read/write indicator outward.
  - **roles** — exports rw flag; carries rw field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30) concurrent assignment forwards the rw field.

**`dev_30_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the src field from internal dev_req(30) to the external device port, carrying the request source indicator.
  - **roles** — exports src field; carries src
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30) concurrent assignment forwards the src field.

**`dev_30_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the device strobe from the internal dev_req(30).stb value which the request generator produces (either main_req.stb or '0').
  - **roles** — exports request strobe; carries gated stb field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_30_req_o <= dev_req(30); dev_req(30).stb is assigned in bus_request process from main_req.stb or '0'.

**`dev_30_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Accepts the external device-30 response record and provides it to the internal dev_rsp(30) element for aggregation into the host response.
  - **roles** — imports response from device 30; sources internal dev_rsp element
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — Concurrent assignment dev_rsp(30) <= dev_30_rsp_i; maps port into internal dev_rsp array.

**`dev_30_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies the ack bit from the device 30 response into dev_rsp(30).ack, which is ORed into the aggregated main response.
  - **roles** — imports ack bit; sources aggregator input
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — dev_rsp(30) <= dev_30_rsp_i concurrent assignment; bus_response process ORs dev_rsp(i).ack into tmp_v.ack.

**`dev_30_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the response data vector from device 30 into dev_rsp(30).data, which is ORed into the aggregated main response data.
  - **roles** — imports response data; sources aggregated data
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — dev_rsp(30) <= dev_30_rsp_i concurrent assignment; bus_response process ORs dev_rsp(i).data into tmp_v.data.

**`dev_30_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies the err bit from device 30 into dev_rsp(30).err for response aggregation driving main_rsp.
  - **roles** — imports err bit; sources aggregator input
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — dev_rsp(30) <= dev_30_rsp_i concurrent assignment; bus_response process ORs dev_rsp(i).err into tmp_v.err.

**`dev_31_req_o`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Drives the external device-31 request port from the internal dev_req(31) vector; forwards the per-device request record to the device boundary combinationally.
  - **roles** — exports request to device 31; carries request combinationally
  - **relationships** — **CARRIES** → dev_req; **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment dev_31_req_o <= dev_req(31); binds internal dev_req(31) to port.

**`dev_31_req_o.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the address field of dev_req(31) to the device port; the field is forwarded unchanged from the internal dev_req element.
  - **roles** — exports request address; carries address field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31) concurrent assignment forwards the addr field.

**`dev_31_req_o.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the amo field from internal dev_req(31) to the device port, carrying the atomic-op indicator.
  - **roles** — exports amo flag; carries amo
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31) concurrent assignment forwards the amo field.

**`dev_31_req_o.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the amoop field vector from internal dev_req(31) to the device port, carrying AMO operation code bits.
  - **roles** — exports amoop field; carries amoop
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31) concurrent assignment forwards the amoop field.

**`dev_31_req_o.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the ben field from internal dev_req(31) to the device port, carrying byte-enable bits outwards.
  - **roles** — exports byte-enable; carries ben field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31) concurrent assignment forwards the ben field.

**`dev_31_req_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the data field of dev_req(31) to the external device port; forwards internal request data unchanged.
  - **roles** — exports request data; carries data field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31) concurrent assignment forwards the data field.

**`dev_31_req_o.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the debug field from internal dev_req(31) to the device port, carrying the debug indicator.
  - **roles** — exports debug flag; carries debug
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31) concurrent assignment forwards the debug field.

**`dev_31_req_o.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the fence field from internal dev_req(31) to the device port, carrying fence control bit outward.
  - **roles** — exports fence flag; carries fence
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31) concurrent assignment forwards the fence field.

**`dev_31_req_o.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the lock field from internal dev_req(31) to the device port, carrying the lock indicator outward.
  - **roles** — exports lock flag; carries lock
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31) concurrent assignment forwards the lock field.

**`dev_31_req_o.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the priv field from internal dev_req(31) to the device port, carrying privilege bit outward.
  - **roles** — exports priv bit; carries priv
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31) concurrent assignment forwards the priv field.

**`dev_31_req_o.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the rw field from internal dev_req(31) to the device port unchanged, carrying the read/write indicator outward.
  - **roles** — exports rw flag; carries rw field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31) concurrent assignment forwards the rw field.

**`dev_31_req_o.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Forwards the src field from internal dev_req(31) to the external device port, carrying the request source indicator.
  - **roles** — exports src field; carries src
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31) concurrent assignment forwards the src field.

**`dev_31_req_o.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Drives the device strobe from the internal dev_req(31).stb value which the request generator produces (either main_req.stb or '0').
  - **roles** — exports request strobe; carries gated stb field
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — dev_31_req_o <= dev_req(31); dev_req(31).stb is assigned in bus_request process from main_req.stb or '0'.

**`dev_31_rsp_i`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Accepts the external device-31 response record and provides it to the internal dev_rsp(31) element for aggregation into the host response.
  - **roles** — imports response from device 31; sources internal dev_rsp element
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — Concurrent assignment dev_rsp(31) <= dev_31_rsp_i; maps port into internal dev_rsp array.

**`dev_31_rsp_i.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies the ack bit from the device 31 response into dev_rsp(31).ack, which is ORed into the aggregated main response.
  - **roles** — imports ack bit; sources aggregator input
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — dev_rsp(31) <= dev_31_rsp_i concurrent assignment; bus_response process ORs dev_rsp(i).ack into tmp_v.ack.

**`dev_31_rsp_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the response data vector from device 31 into dev_rsp(31).data, which is ORed into the aggregated main response data.
  - **roles** — imports response data; sources aggregated data
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — dev_rsp(31) <= dev_31_rsp_i concurrent assignment; bus_response process ORs dev_rsp(i).data into tmp_v.data.

**`dev_31_rsp_i.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies the err bit from device 31 into dev_rsp(31).err for response aggregation driving main_rsp.
  - **roles** — imports err bit; sources aggregator input
  - **relationships** — **SOURCES** → dev_rsp
  - **evidence** — dev_rsp(31) <= dev_31_rsp_i concurrent assignment; bus_response process ORs dev_rsp(i).err into tmp_v.err.

**`main_req_i`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Supplies the host request record to the internal routing logic (dev_req array) and to the instantiated register (host_req_i). The whole record is copied into dev_req(i) in the generate.
  - **roles** — input request carrier; feeds internal routing; passed to instantiated register
  - **relationships** — **SOURCES** → dev_req; **SOURCES** → neorv32_bus_reg_inst.host_req_i
  - **evidence** — bus_request generate: dev_req(i) <= main_req; component port map host_req_i => main_req_i

**`main_req_i.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the address slice that is compared against each device base to decide which dev_req(i).stb is enabled; the slice is read from the host request inside the bus_request generate.
  - **roles** — address field for decode; governs device STB enable
  - **relationships** — **CONSTRAINS** → dev_req
  - **evidence** — bus_request process comparison: main_req.addr(addr_hi_c downto addr_lo_c) = dev_base_list_c(i)(addr_hi_c downto addr_lo_c)

**`main_req_i.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded as part of the whole host request into dev_req(i), carrying the atomic memory operation indicator to devices.
  - **roles** — AMO flag carrier; forwarded to devices
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — bus_request process: dev_req(i) <= main_req (whole-record assignment)

**`main_req_i.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Is carried in the whole host request assignment into dev_req(i), forwarding the AMO operation code to the device request entries.
  - **roles** — AMO opcode carrier; forwarded to devices
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — bus_request process: dev_req(i) <= main_req (whole-record assignment)

**`main_req_i.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Is included in the whole host request that is assigned to dev_req(i), forwarding the transaction's byte-enable to the device-side request array.
  - **roles** — byte-enable carrier; forwarded to devices
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — bus_request process: dev_req(i) <= main_req (whole-record assignment)

**`main_req_i.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is forwarded as part of the whole host request into dev_req(i) assignments and thus supplies device request data to dev_req array; also passed to instantiated register via the host_req mapping.
  - **roles** — data field carrier; forwarded to devices; passed to instantiated register
  - **relationships** — **CARRIES** → dev_req; **SOURCES** → neorv32_bus_reg_inst.host_req_i
  - **evidence** — bus_request process: dev_req(i) <= main_req; component port map host_req_i => main_req_i

**`main_req_i.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is included in the whole host request assigned to dev_req(i), forwarding the debug control bit to device-side requests.
  - **roles** — debug flag carrier; forwarded to devices
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — bus_request process: dev_req(i) <= main_req (whole-record assignment)

**`main_req_i.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is carried in the whole host request assignment into dev_req(i), forwarding the fence indicator to device-side requests.
  - **roles** — fence flag carrier; forwarded to devices
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — bus_request process: dev_req(i) <= main_req (whole-record assignment)

**`main_req_i.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is included in the whole host request copied into dev_req(i), carrying the lock indicator to device requests.
  - **roles** — lock flag carrier; forwarded to devices
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — bus_request process: dev_req(i) <= main_req (whole-record assignment)

**`main_req_i.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is carried in the whole host request assignment into dev_req(i), forwarding privilege information to the device request array.
  - **roles** — privilege flag carrier; forwarded to devices
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — bus_request process: dev_req(i) <= main_req (whole-record assignment)

**`main_req_i.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded in the whole host request assignment into dev_req(i), carrying the read/write flag to device-side request entries.
  - **roles** — rw flag carrier; forwarded to devices
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — bus_request process: dev_req(i) <= main_req (whole-record assignment)

**`main_req_i.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded as part of the whole host request into dev_req(i), passing the request source field through to the device request array.
  - **roles** — source field carrier; forwarded to devices
  - **relationships** — **CARRIES** → dev_req
  - **evidence** — bus_request process: dev_req(i) <= main_req (whole-record assignment)

**`main_req_i.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is forwarded as part of the whole request into dev_req(i) and is also conditionally assigned to dev_req(i).stb depending on the address comparison, enabling the targeted device's transaction.
  - **roles** — strobe carrier; gates device request activation
  - **relationships** — **CARRIES** → dev_req; **SOURCES** → dev_req; **CONSTRAINS** → dev_req
  - **evidence** — bus_request process: dev_req(i) <= main_req; then if address match dev_req(i).stb <= main_req.stb else '0'

**`main_rsp_o`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Exposes the host-facing response port of this entity and is connected to the instantiated neorv32_bus_reg's host_rsp_o port via the component port map.
  - **roles** — host response output; driven by instantiated register
  - **relationships** — **SOURCES** → neorv32_bus_reg_inst.host_rsp_o
  - **evidence** — component port map: host_rsp_o => main_rsp_o

**`main_rsp_o.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is the ack field of the host response port that is driven out of this entity via the instantiated register's host_rsp_o mapping.
  - **roles** — ack output field; exported from instantiated register
  - **relationships** — **SOURCES** → neorv32_bus_reg_inst.host_rsp_o
  - **evidence** — component port map: host_rsp_o => main_rsp_o

**`main_rsp_o.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is the response data field exported at the entity boundary via the instantiated register's host_rsp_o mapping; the register instance ultimately drives this field.
  - **roles** — response data output; exported from instantiated register
  - **relationships** — **SOURCES** → neorv32_bus_reg_inst.host_rsp_o
  - **evidence** — component port map: host_rsp_o => main_rsp_o

**`main_rsp_o.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Is the error flag of the host response port, exported to the entity boundary through the instantiated register's host_rsp_o connection.
  - **roles** — error output field; exported from instantiated register
  - **relationships** — **SOURCES** → neorv32_bus_reg_inst.host_rsp_o
  - **evidence** — component port map: host_rsp_o => main_rsp_o

**`rstn_i`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Provides the active-low reset to the instantiated neorv32_bus_reg via port map so the register block can be reset by this signal.
  - **roles** — reset input; connects to instantiated register
  - **relationships** — **SOURCES** → neorv32_bus_reg_inst.rstn_i
  - **evidence** — component port map: rstn_i => rstn_i in neorv32_bus_reg_inst port map

**`clk_i`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Supplies the rising edge used by the request and response register processes to capture device_req_o and host_rsp_o when registers are enabled.
  - **roles** — clock source; sequences register updates
  - **relationships** — **SEQUENCES** → device_req_o, host_rsp_o
  - **evidence** — rising_edge(clk_i) in processes request_reg and response_reg (generate branches request_reg_enabled and response_reg_enabled).

**`device_req_o`** — neorv32_bus_reg · `bus_req_t`
  - **functionality** — Drives the device request either combinationally from host_req_i (when REQ_REG_EN false) or as a register capturing host_req_i on clock edges (when REQ_REG_EN true); reset assigns a terminate constant.
  - **roles** — output request; exports host request to device; holds value when request register enabled
  - **relationships** — **CAPTURES** → host_req_i; **CARRIES** → host_req_i
  - **evidence** — device_req_o <= host_req_i in request_reg_disabled generate; device_req_o <= host_req_i inside request_reg process gated by host_req_i.stb; reset assignment to req_terminate_c in request_reg.

**`device_req_o.addr`** — neorv32_bus_reg · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Receives the address field from host_req_i either directly (no register) or when the request register captures the host request; forwarded to the device address port.
  - **roles** — output address field; carried/sourced from host_req_i
  - **relationships** — **CAPTURES** → host_req_i.addr; **CARRIES** → host_req_i.addr
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg when host_req_i.stb='1'.

**`device_req_o.amo`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Supplies the amo flag to the device from host_req_i, either captured or forwarded combinationally.
  - **roles** — amo output bit; carried/sourced from host_req_i.amo
  - **relationships** — **CAPTURES** → host_req_i.amo; **CARRIES** → host_req_i.amo
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg when host_req_i.stb='1'.

**`device_req_o.amoop`** — neorv32_bus_reg · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Carries the amoop field from host_req_i to the device either by the request register capture or by direct forwarding when registers are disabled.
  - **roles** — amo opcode output; carried/sourced from host_req_i.amoop
  - **relationships** — **CAPTURES** → host_req_i.amoop; **CARRIES** → host_req_i.amoop
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i inside request_reg gated by host_req_i.stb.

**`device_req_o.ben`** — neorv32_bus_reg · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the byte-enable field from host_req_i to the device, either directly or captured by the request register.
  - **roles** — output ben field; carried/sourced from host_req_i
  - **relationships** — **CAPTURES** → host_req_i.ben; **CARRIES** → host_req_i.ben
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg when host_req_i.stb='1'.

**`device_req_o.data`** — neorv32_bus_reg · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Conveys the request data field from host_req_i to the device either via combinational forwarding or via the request register when enabled.
  - **roles** — output data field; carried/sourced from host_req_i
  - **relationships** — **CAPTURES** → host_req_i.data; **CARRIES** → host_req_i.data
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg when host_req_i.stb='1'.

**`device_req_o.debug`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Forwards the debug flag from host_req_i to the device either directly or when captured by the request register.
  - **roles** — debug output bit; carried/sourced from host_req_i.debug
  - **relationships** — **CAPTURES** → host_req_i.debug; **CARRIES** → host_req_i.debug
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg when host_req_i.stb='1'.

**`device_req_o.fence`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — The fence field is driven from host_req_i.fence each clock and is also forwarded combinationally when the request register is disabled.
  - **roles** — fence output bit; carried/sourced from host_req_i.fence
  - **relationships** — **CAPTURES** → host_req_i.fence; **CARRIES** → host_req_i.fence
  - **evidence** — device_req_o.fence <= host_req_i.fence in request_reg process; device_req_o <= host_req_i in request_reg_disabled.

**`device_req_o.lock`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — The lock field is assigned each clock from host_req_i.lock and otherwise forwarded; it is both part of whole-record transfers and explicitly driven into device_req_o.lock.
  - **roles** — lock output bit; carried/sourced from host_req_i.lock
  - **relationships** — **CAPTURES** → host_req_i.lock; **CARRIES** → host_req_i.lock
  - **evidence** — device_req_o.lock <= host_req_i.lock in request_reg process; device_req_o <= host_req_i when REQ_REG_EN disabled.

**`device_req_o.priv`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Carries the privilege flag from host_req_i to the device either by capture into the request register or by direct forwarding.
  - **roles** — priv output bit; carried/sourced from host_req_i.priv
  - **relationships** — **CAPTURES** → host_req_i.priv; **CARRIES** → host_req_i.priv
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i inside request_reg when host_req_i.stb='1'.

**`device_req_o.rw`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Conveys the rw bit from the host request to the device either by capture into the request register or by direct forwarding.
  - **roles** — rw output bit; carried/sourced from host_req_i.rw
  - **relationships** — **CAPTURES** → host_req_i.rw; **CARRIES** → host_req_i.rw
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg when host_req_i.stb='1'.

**`device_req_o.src`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Forwards the src bit from host_req_i to the device either via the request register or directly when registers are disabled.
  - **roles** — src output bit; carried/sourced from host_req_i.src
  - **relationships** — **CAPTURES** → host_req_i.src; **CARRIES** → host_req_i.src
  - **evidence** — device_req_o <= host_req_i in both request_reg (when captured) and request_reg_disabled (concurrent).

**`device_req_o.stb`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Reflects host_req_i.stb to the device; when request register is enabled stb is assigned each clock from host_req_i.stb and when disabled it is forwarded combinationally.
  - **roles** — strobe output; carried/sourced from host_req_i.stb
  - **relationships** — **CAPTURES** → host_req_i.stb; **CARRIES** → host_req_i.stb
  - **evidence** — device_req_o.stb <= host_req_i.stb in request_reg process; device_req_o <= host_req_i in request_reg_disabled.

**`device_rsp_i`** — neorv32_bus_reg · `bus_rsp_t`
  - **functionality** — Provides the device response that is either forwarded to host_rsp_o (when RSP_REG_EN false) or captured into the response register on clock edges (when RSP_REG_EN true).
  - **roles** — input response source; supplies host response fields
  - **relationships** — **SOURCES** → host_rsp_o; **CARRIES** → host_rsp_o
  - **evidence** — host_rsp_o <= device_rsp_i in response_reg process (captured) and host_rsp_o <= device_rsp_i in response_reg_disabled (concurrent).

**`device_rsp_i.ack`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Supplies the ack bit that is either forwarded to host_rsp_o.ack or captured into the response register, conveying device acknowledgement to the host.
  - **roles** — response ack source; sourced to host_rsp_o.ack
  - **relationships** — **SOURCES** → host_rsp_o.ack; **CARRIES** → host_rsp_o.ack
  - **evidence** — host_rsp_o <= device_rsp_i in response_reg (clocked) and response_reg_disabled (concurrent); field device_rsp_i.ack mapped to host_rsp_o.ack.

**`device_rsp_i.data`** — neorv32_bus_reg · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides response data that is forwarded to host_rsp_o.data either combinationally or captured into the response register on clock edges.
  - **roles** — response data source; sourced to host_rsp_o.data
  - **relationships** — **SOURCES** → host_rsp_o.data; **CARRIES** → host_rsp_o.data
  - **evidence** — host_rsp_o <= device_rsp_i in response_reg (captured) and response_reg_disabled (concurrent); maps device_rsp_i.data to host_rsp_o.data.

**`device_rsp_i.err`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Supplies the error bit to host_rsp_o.err either directly or via the response register capture on clock edges.
  - **roles** — response error source; sourced to host_rsp_o.err
  - **relationships** — **SOURCES** → host_rsp_o.err; **CARRIES** → host_rsp_o.err
  - **evidence** — host_rsp_o <= device_rsp_i in response_reg (clocked) and response_reg_disabled (concurrent); field mapping device_rsp_i.err.

**`host_req_i`** — neorv32_bus_reg · `bus_req_t`
  - **functionality** — Provides the host request record that is either forwarded to device_req_o (when REQ_REG_EN false) or captured into device_req_o on clock edges when host_req_i.stb='1' (when REQ_REG_EN true).
  - **roles** — input request source; supplies fields to device_req_o; gates captures via .stb
  - **relationships** — **SOURCES** → device_req_o; **CARRIES** → device_req_o; **GATES** → device_req_o
  - **evidence** — device_req_o <= host_req_i (concurrent in request_reg_disabled) and device_req_o <= host_req_i gated by if host_req_i.stb='1' in request_reg process.

**`host_req_i.addr`** — neorv32_bus_reg · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies the address field to device_req_o either directly (no register) or when captured into the request register; it is part of the whole-record transfers from host_req_i to device_req_o.
  - **roles** — request address operand; carried/sourced to device_req_o.addr
  - **relationships** — **SOURCES** → device_req_o.addr; **CARRIES** → device_req_o.addr
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i inside request_reg process when host_req_i.stb='1'.

**`host_req_i.amo`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Supplies the amo flag as part of the host request to device_req_o either directly or when captured into the request register.
  - **roles** — amo operand; carried/sourced to device_req_o.amo
  - **relationships** — **SOURCES** → device_req_o.amo; **CARRIES** → device_req_o.amo
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg when host_req_i.stb='1'.

**`host_req_i.amoop`** — neorv32_bus_reg · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the amoop field as part of the host request to device_req_o either directly or when captured by the request register.
  - **roles** — amo opcode operand; carried/sourced to device_req_o.amoop
  - **relationships** — **SOURCES** → device_req_o.amoop; **CARRIES** → device_req_o.amoop
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i inside request_reg when host_req_i.stb='1'.

**`host_req_i.ben`** — neorv32_bus_reg · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the byte-enable field as part of the host request to device_req_o either directly or when captured into the request register.
  - **roles** — byte-enable operand; carried/sourced to device_req_o.ben
  - **relationships** — **SOURCES** → device_req_o.ben; **CARRIES** → device_req_o.ben
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg process when host_req_i.stb='1'.

**`host_req_i.data`** — neorv32_bus_reg · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies the data field to device_req_o by whole-record transfer either combinationally or when captured by the request register.
  - **roles** — request data operand; carried/sourced to device_req_o.data
  - **relationships** — **SOURCES** → device_req_o.data; **CARRIES** → device_req_o.data
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg process when host_req_i.stb='1'.

**`host_req_i.debug`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Forwards the debug field from the host request to device_req_o as part of whole-record transfers, either captured or forwarded.
  - **roles** — debug operand; carried/sourced to device_req_o.debug
  - **relationships** — **SOURCES** → device_req_o.debug; **CARRIES** → device_req_o.debug
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg when host_req_i.stb='1'.

**`host_req_i.fence`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — The fence field is forwarded to device_req_o.fence each clock (explicit assignment) and is also part of the whole-record transfer from host_req_i to device_req_o.
  - **roles** — fence operand; carried/sourced to device_req_o.fence
  - **relationships** — **SOURCES** → device_req_o.fence; **CARRIES** → device_req_o.fence
  - **evidence** — device_req_o.fence <= host_req_i.fence in request_reg process; device_req_o <= host_req_i when REQ_REG_EN disabled.

**`host_req_i.lock`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — The lock field is forwarded to device_req_o.lock each clock (assigned explicitly) and is also part of the whole-record forward/capture from host_req_i to device_req_o.
  - **roles** — lock operand; carried/sourced to device_req_o.lock
  - **relationships** — **SOURCES** → device_req_o.lock; **CARRIES** → device_req_o.lock
  - **evidence** — device_req_o.lock <= host_req_i.lock in request_reg process; device_req_o <= host_req_i when REQ_REG_EN disabled.

**`host_req_i.priv`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Forwards the privilege field from the host request to device_req_o as part of the whole-record transfer, either captured or forwarded.
  - **roles** — privilege operand; carried/sourced to device_req_o.priv
  - **relationships** — **SOURCES** → device_req_o.priv; **CARRIES** → device_req_o.priv
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg when host_req_i.stb='1'.

**`host_req_i.rw`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Forwards the read/write flag as part of the host request to device_req_o either directly or when captured into the request register.
  - **roles** — rw operand; carried/sourced to device_req_o.rw
  - **relationships** — **SOURCES** → device_req_o.rw; **CARRIES** → device_req_o.rw
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i inside request_reg when host_req_i.stb='1'.

**`host_req_i.src`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Supplies the src field from the host request to device_req_o as part of the whole-record transfer, either captured or forwarded combinationally.
  - **roles** — src operand; carried/sourced to device_req_o.src
  - **relationships** — **SOURCES** → device_req_o.src; **CARRIES** → device_req_o.src
  - **evidence** — device_req_o <= host_req_i (concurrent) and device_req_o <= host_req_i in request_reg process when host_req_i.stb='1'.

**`host_req_i.stb`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Acts both as the gate for capturing the whole host_req_i into device_req_o (if '1') and as a field that is forwarded to device_req_o.stb every cycle; also forwarded combinationally when registers disabled.
  - **roles** — write-enable/gate; carried to device_req_o.stb
  - **relationships** — **GATES** → device_req_o; **SOURCES** → device_req_o.stb; **CARRIES** → device_req_o.stb
  - **evidence** — if (host_req_i.stb = '1') then device_req_o <= host_req_i; and device_req_o.stb <= host_req_i.stb in request_reg; device_req_o <= host_req_i when REQ_REG_EN disabled.

**`host_rsp_o`** — neorv32_bus_reg · `bus_rsp_t`
  - **functionality** — Drives the host response either directly from device_rsp_i (when RSP_REG_EN false) or from the response register captured on clock edges (when RSP_REG_EN true); reset sets a terminate constant.
  - **roles** — response output; reports device response; holds value when registered
  - **relationships** — **CAPTURES** → device_rsp_i; **CARRIES** → device_rsp_i
  - **evidence** — host_rsp_o <= device_rsp_i in response_reg process (captured) and host_rsp_o <= device_rsp_i in response_reg_disabled generate.

**`host_rsp_o.ack`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Driven from device_rsp_i.ack either captured into host_rsp_o on clock edges or forwarded combinationally, carrying the device ack to the host.
  - **roles** — response ack bit; carried/sourced from device_rsp_i
  - **relationships** — **CAPTURES** → device_rsp_i.ack; **CARRIES** → device_rsp_i.ack
  - **evidence** — host_rsp_o <= device_rsp_i in response_reg (clocked) and host_rsp_o <= device_rsp_i in response_reg_disabled (concurrent); field mapping from device_rsp_i.ack.

**`host_rsp_o.data`** — neorv32_bus_reg · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the device response data back to the host either directly or captured in the response register on clock edges, mirroring device_rsp_i.data.
  - **roles** — response data field; carried/sourced from device_rsp_i
  - **relationships** — **CAPTURES** → device_rsp_i.data; **CARRIES** → device_rsp_i.data
  - **evidence** — host_rsp_o <= device_rsp_i in response_reg (clocked) and host_rsp_o <= device_rsp_i in response_reg_disabled (concurrent); maps device_rsp_i.data.

**`host_rsp_o.err`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Reflects device_rsp_i.err to the host, either captured into host_rsp_o on clock edges or forwarded combinationally when response register is disabled.
  - **roles** — response error bit; carried/sourced from device_rsp_i
  - **relationships** — **CAPTURES** → device_rsp_i.err; **CARRIES** → device_rsp_i.err
  - **evidence** — host_rsp_o <= device_rsp_i in response_reg (clocked) and host_rsp_o <= device_rsp_i in response_reg_disabled (concurrent); field mapping from device_rsp_i.err.

**`rstn_i`** — neorv32_bus_reg · `std_ulogic`
  - **functionality** — Drives the reset branches of the request and response register processes, forcing device_req_o to req_terminate_c and host_rsp_o to rsp_terminate_c when asserted low.
  - **roles** — reset input; overrides register outputs on reset; sequences reset
  - **relationships** — **OVERRIDES** → device_req_o, host_rsp_o; **SEQUENCES** → device_req_o, host_rsp_o
  - **evidence** — if (rstn_i = '0') then ... branches in request_reg and response_reg processes (request_reg_enabled and response_reg_enabled generates).

**`a_req_i`** — neorv32_bus_switch · `bus_req_t`
  - **functionality** — Aggregates A's request fields (addr,data,stb,lock,...) which are read individually by the arbiter to decide grants and to form the forwarded x_req_o request.
  - **roles** — input bundle; supplies request fields
  - **relationships** — **AGGREGATES** → a_req_i.addr, a_req_i.data, a_req_i.ben, a_req_i.stb, a_req_i.rw, a_req_i.src, a_req_i.priv, a_req_i.debug, a_req_i.amo, a_req_i.amoop, a_req_i.lock, a_req_i.fence
  - **evidence** — a_req_i record fields (stb, addr, data, lock, ...) are read separately in arbiter_fsm and concurrent assignments to x_req_o.

**`a_req_i.addr`** — neorv32_bus_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies port A's address which is multiplexed onto x_req_o.addr when sel = '0' so A's address is forwarded to the external master when A is selected.
  - **roles** — request address; feeds x request address
  - **relationships** — **SOURCES** → x_req_o.addr
  - **evidence** — concurrent assignment x_req_o.addr <= a_req_i.addr when (sel = '0') else b_req_i.addr.

**`a_req_i.amo`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Provides A's AMO flag which is forwarded to x_req_o.amo when A is selected so atomic semantics are preserved on the forwarded request.
  - **roles** — atomic op flag; feeds x request amo
  - **relationships** — **SOURCES** → x_req_o.amo
  - **evidence** — x_req_o.amo <= a_req_i.amo when (sel = '0') else b_req_i.amo.

**`a_req_i.amoop`** — neorv32_bus_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Supplies A's AMO opcode vector which is forwarded to x_req_o.amoop when A is selected so the external master receives the AMO operation.
  - **roles** — AMO opcode; feeds x request amoop
  - **relationships** — **SOURCES** → x_req_o.amoop
  - **evidence** — x_req_o.amoop <= a_req_i.amoop when (sel = '0') else b_req_i.amoop.

**`a_req_i.ben`** — neorv32_bus_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Supplies A's byte-enable signals which are forwarded to x_req_o.ben according to the read-only generics and sel, enabling correct byte writes on the external request.
  - **roles** — write byte-enable; feeds x request byte-enables
  - **relationships** — **SOURCES** → x_req_o.ben
  - **evidence** — x_req_o.ben concurrent assignment uses a_req_i.ben for PORT_B_READ_ONLY or when sel = '0'.

**`a_req_i.data`** — neorv32_bus_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides A's write data which is forwarded to x_req_o.data when A is selected (or depending on PORT_A_READ_ONLY/PORT_B_READ_ONLY generics), so A's data reaches the external bus when applicable.
  - **roles** — request data; feeds x request data
  - **relationships** — **SOURCES** → x_req_o.data
  - **evidence** — concurrent assignment to x_req_o.data uses a_req_i.data in the PORT_*_READ_ONLY and sel-based branches.

**`a_req_i.debug`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies A's debug indicator which is forwarded to x_req_o.debug when A is selected so debug requests propagate externally.
  - **roles** — debug indicator; feeds x request debug
  - **relationships** — **SOURCES** → x_req_o.debug
  - **evidence** — x_req_o.debug <= a_req_i.debug when (sel = '0') else b_req_i.debug.

**`a_req_i.fence`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Provides A's fence flag which is ORed with B's fence and forwarded onto x_req_o.fence so fence semantics propagate to the external request.
  - **roles** — fence flag; feeds x request fence
  - **relationships** — **SOURCES** → x_req_o.fence
  - **evidence** — x_req_o.fence <= a_req_i.fence or b_req_i.fence.

**`a_req_i.lock`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies A's lock bit that is combined into locked_nxt and is checked by the FSM (when busy) to decide whether to remain busy or return to idle, thus affecting grant duration.
  - **roles** — lock indicator; influences grant duration; feeds locked_nxt
  - **relationships** — **SOURCES** → locked_nxt; **GATES** → state_nxt
  - **evidence** — locked_nxt <= b_req_i.lock & a_req_i.lock in others; a_req_i.lock compared in S_BUSY_A branch to set state_nxt <= S_IDLE.

**`a_req_i.priv`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies A's privilege indicator which is forwarded to x_req_o.priv when A is selected so the external request reflects privilege.
  - **roles** — privilege marker; feeds x request priv
  - **relationships** — **SOURCES** → x_req_o.priv
  - **evidence** — x_req_o.priv <= a_req_i.priv when (sel = '0') else b_req_i.priv.

**`a_req_i.rw`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies A's read/write bit which is forwarded onto x_req_o.rw when A is selected so the external request carries the correct access type.
  - **roles** — access type; feeds x request rw
  - **relationships** — **SOURCES** → x_req_o.rw
  - **evidence** — x_req_o.rw <= a_req_i.rw when (sel = '0') else b_req_i.rw.

**`a_req_i.src`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Provides A's source ID which is forwarded to x_req_o.src when A is selected so responses can be attributed to A.
  - **roles** — request source tag; feeds x request src
  - **relationships** — **SOURCES** → x_req_o.src
  - **evidence** — x_req_o.src <= a_req_i.src when (sel = '0') else b_req_i.src.

**`a_req_i.stb`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies A's strobe which both contributes to the latched a_req (captured in arbiter_sync) and is tested in the FSM to request grants and drive stb, thereby influencing selection and the forwarded x_req_o.stb.
  - **roles** — request handshake; drives latch and arbitration decisions
  - **relationships** — **SOURCES** → a_req; **SOURCES** → stb; **GATES** → state_nxt, sel, stb
  - **evidence** — a_req <= a_req or a_req_i.stb in arbiter_sync; a_req_i.stb used in arbiter_fsm conditions setting sel, stb, state_nxt; stb <= a_req_i.stb in S_BUSY_A branch.

**`a_rsp_o`** — neorv32_bus_switch · `bus_rsp_t`
  - **functionality** — Outputs A's response fields derived from x_rsp_i: data is forwarded unmodified; ack and err are gated so they are asserted only when A is selected (sel='0').
  - **roles** — output bundle; reports x response to A
  - **relationships** — **AGGREGATES** → a_rsp_o.ack, a_rsp_o.err, a_rsp_o.data
  - **evidence** — a_rsp_o.* assignments: data <= x_rsp_i.data; ack/err use sel-based conditional assignments.

**`a_rsp_o.ack`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Drives A's ack from x_rsp_i.ack when sel = '0', otherwise deasserts ack, so A only sees ack for responses routed to it.
  - **roles** — response handshake; drives ack to A
  - **relationships** — **DERIVES_FROM** → x_rsp_i.ack
  - **evidence** — a_rsp_o.ack <= x_rsp_i.ack when (sel = '0') else '0'.

**`a_rsp_o.data`** — neorv32_bus_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries x_rsp_i.data unchanged to A so the returned data from the external master is delivered to A.
  - **roles** — response data path; forwards external data to A
  - **relationships** — **CARRIES** → x_rsp_i.data
  - **evidence** — a_rsp_o.data <= x_rsp_i.data.

**`a_rsp_o.err`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Drives A's error flag from x_rsp_i.err when sel = '0', otherwise outputs '0', ensuring error is reported only to the selected requester.
  - **roles** — response error; reports x error to A
  - **relationships** — **DERIVES_FROM** → x_rsp_i.err
  - **evidence** — a_rsp_o.err <= x_rsp_i.err when (sel = '0') else '0'.

**`b_req_i`** — neorv32_bus_switch · `bus_req_t`
  - **functionality** — Aggregates B's request fields (addr,data,stb,lock,...) which are read individually by the arbiter to decide grants and to form the forwarded x_req_o request.
  - **roles** — input bundle; supplies request fields
  - **relationships** — **AGGREGATES** → b_req_i.addr, b_req_i.data, b_req_i.ben, b_req_i.stb, b_req_i.rw, b_req_i.src, b_req_i.priv, b_req_i.debug, b_req_i.amo, b_req_i.amoop, b_req_i.lock, b_req_i.fence
  - **evidence** — b_req_i record fields are read separately in arbiter_fsm and concurrent assignments to x_req_o.

**`b_req_i.addr`** — neorv32_bus_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies port B's address which is multiplexed onto x_req_o.addr when sel = '1' so B's address is forwarded when B is selected.
  - **roles** — request address; feeds x request address
  - **relationships** — **SOURCES** → x_req_o.addr
  - **evidence** — x_req_o.addr <= a_req_i.addr when (sel = '0') else b_req_i.addr.

**`b_req_i.amo`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Provides B's AMO flag which is forwarded to x_req_o.amo when B is selected so atomic semantics are preserved on the forwarded request.
  - **roles** — atomic op flag; feeds x request amo
  - **relationships** — **SOURCES** → x_req_o.amo
  - **evidence** — x_req_o.amo <= a_req_i.amo when (sel = '0') else b_req_i.amo.

**`b_req_i.amoop`** — neorv32_bus_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Provides B's AMO opcode vector which is forwarded to x_req_o.amoop when B is selected so the external master receives the AMO operation.
  - **roles** — AMO opcode; feeds x request amoop
  - **relationships** — **SOURCES** → x_req_o.amoop
  - **evidence** — x_req_o.amoop <= a_req_i.amoop when (sel = '0') else b_req_i.amoop.

**`b_req_i.ben`** — neorv32_bus_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Supplies B's byte-enable signals which are forwarded to x_req_o.ben according to the read-only generics and sel, enabling correct byte writes on the external request.
  - **roles** — write byte-enable; feeds x request byte-enables
  - **relationships** — **SOURCES** → x_req_o.ben
  - **evidence** — x_req_o.ben concurrent assignment uses b_req_i.ben for PORT_A_READ_ONLY or when sel = '1'.

**`b_req_i.data`** — neorv32_bus_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides B's write data which is forwarded to x_req_o.data when B is selected (subject to read-only generics), so B's data reaches the external bus when applicable.
  - **roles** — request data; feeds x request data
  - **relationships** — **SOURCES** → x_req_o.data
  - **evidence** — x_req_o.data uses b_req_i.data when PORT_A_READ_ONLY or in sel-based branch when sel = '1'.

**`b_req_i.debug`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies B's debug indicator which is forwarded to x_req_o.debug when B is selected so debug requests propagate externally.
  - **roles** — debug indicator; feeds x request debug
  - **relationships** — **SOURCES** → x_req_o.debug
  - **evidence** — x_req_o.debug <= a_req_i.debug when (sel = '0') else b_req_i.debug.

**`b_req_i.fence`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Provides B's fence flag which is ORed with A's fence and forwarded onto x_req_o.fence so fence semantics propagate to the external request.
  - **roles** — fence flag; feeds x request fence
  - **relationships** — **SOURCES** → x_req_o.fence
  - **evidence** — x_req_o.fence <= a_req_i.fence or b_req_i.fence.

**`b_req_i.lock`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Provides B's lock bit that is combined into locked_nxt and is checked by the FSM (when busy) to decide whether to remain busy or return to idle, thus affecting grant duration.
  - **roles** — lock indicator; influences grant duration; feeds locked_nxt
  - **relationships** — **SOURCES** → locked_nxt; **GATES** → state_nxt
  - **evidence** — locked_nxt <= b_req_i.lock & a_req_i.lock; b_req_i.lock compared in S_BUSY_B branch to set state_nxt <= S_IDLE.

**`b_req_i.priv`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies B's privilege indicator which is forwarded to x_req_o.priv when B is selected so the external request reflects privilege.
  - **roles** — privilege marker; feeds x request priv
  - **relationships** — **SOURCES** → x_req_o.priv
  - **evidence** — x_req_o.priv <= a_req_i.priv when (sel = '0') else b_req_i.priv.

**`b_req_i.rw`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies B's read/write bit which is forwarded onto x_req_o.rw when B is selected so the external request carries correct access type.
  - **roles** — access type; feeds x request rw
  - **relationships** — **SOURCES** → x_req_o.rw
  - **evidence** — x_req_o.rw <= a_req_i.rw when (sel = '0') else b_req_i.rw.

**`b_req_i.src`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Provides B's source ID which is forwarded to x_req_o.src when B is selected so responses can be attributed to B.
  - **roles** — request source tag; feeds x request src
  - **relationships** — **SOURCES** → x_req_o.src
  - **evidence** — x_req_o.src <= a_req_i.src when (sel = '0') else b_req_i.src.

**`b_req_i.stb`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies B's strobe which contributes to latched b_req and is tested by the FSM to request grants and drive stb, thus influencing selection and the forwarded x_req_o.stb.
  - **roles** — request handshake; drives latch and arbitration decisions
  - **relationships** — **SOURCES** → b_req; **SOURCES** → stb; **GATES** → state_nxt, sel, stb
  - **evidence** — b_req <= b_req or b_req_i.stb in arbiter_sync; b_req_i.stb used in arbiter_fsm conditions and stb <= b_req_i.stb in S_BUSY_B branch.

**`b_rsp_o`** — neorv32_bus_switch · `bus_rsp_t`
  - **functionality** — Outputs B's response fields derived from x_rsp_i: data is forwarded unmodified; ack and err are gated so they are asserted only when B is selected (sel='1').
  - **roles** — output bundle; reports x response to B
  - **relationships** — **AGGREGATES** → b_rsp_o.ack, b_rsp_o.err, b_rsp_o.data
  - **evidence** — b_rsp_o.* assignments: data <= x_rsp_i.data; ack/err use sel-based conditional assignments.

**`b_rsp_o.ack`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Drives B's ack from x_rsp_i.ack when sel = '1', otherwise deasserts ack, so B only sees ack for responses routed to it.
  - **roles** — response handshake; drives ack to B
  - **relationships** — **DERIVES_FROM** → x_rsp_i.ack
  - **evidence** — b_rsp_o.ack <= x_rsp_i.ack when (sel = '1') else '0'.

**`b_rsp_o.data`** — neorv32_bus_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries x_rsp_i.data unchanged to B so the returned data from the external master is delivered to B.
  - **roles** — response data path; forwards external data to B
  - **relationships** — **CARRIES** → x_rsp_i.data
  - **evidence** — b_rsp_o.data <= x_rsp_i.data.

**`b_rsp_o.err`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Drives B's error flag from x_rsp_i.err when sel = '1', otherwise outputs '0', ensuring error is reported only to the selected requester.
  - **roles** — response error; reports x error to B
  - **relationships** — **DERIVES_FROM** → x_rsp_i.err
  - **evidence** — b_rsp_o.err <= x_rsp_i.err when (sel = '1') else '0'.

**`clk_i`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies the clock edge used by the synchronous arbiter to update state, sel_q, locked, a_req and b_req on rising edges so the FSM and request latches progress each cycle.
  - **roles** — clock source; sequences internal registers
  - **relationships** — **SEQUENCES** → state, sel_q, locked, a_req, b_req
  - **evidence** — arbiter_sync process uses rising_edge(clk_i) to assign state, sel_q, locked, a_req, b_req.

**`rstn_i`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — When asserted low resets state, sel_q, locked, a_req and b_req to their initial values in the synchronous arbiter, establishing defined start-up state for the FSM and latches.
  - **roles** — reset source; initialises internal registers
  - **relationships** — **SEQUENCES** → state, sel_q, locked, a_req, b_req
  - **evidence** — arbiter_sync process has if (rstn_i = '0') then ... setting state, sel_q, locked, a_req, b_req.

**`x_req_o`** — neorv32_bus_switch · `bus_req_t`
  - **functionality** — Aggregates the selected request fields from A or B (subject to read-only generics and sel) and outputs them to the external master interface x_req_o.
  - **roles** — output bundle; forwards selected request to external master
  - **relationships** — **AGGREGATES** → x_req_o.addr, x_req_o.data, x_req_o.ben, x_req_o.stb, x_req_o.rw, x_req_o.src, x_req_o.priv, x_req_o.debug, x_req_o.amo, x_req_o.amoop, x_req_o.lock, x_req_o.fence
  - **evidence** — concurrent assignments build each x_req_o field from a_req_i/b_req_i and stb signal.

**`x_req_o.addr`** — neorv32_bus_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the selected address from A or B to the external master; sel chooses between a_req_i.addr and b_req_i.addr so the chosen requester address is forwarded.
  - **roles** — external address output; driven by selected port
  - **relationships** — **DERIVES_FROM** → a_req_i.addr, b_req_i.addr
  - **evidence** — x_req_o.addr <= a_req_i.addr when (sel = '0') else b_req_i.addr.

**`x_req_o.amo`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Forwards the selected AMO flag from A or B to the external master to preserve atomic operation semantics.
  - **roles** — external AMO flag; driven by selected port
  - **relationships** — **DERIVES_FROM** → a_req_i.amo, b_req_i.amo
  - **evidence** — x_req_o.amo <= a_req_i.amo when (sel = '0') else b_req_i.amo.

**`x_req_o.amoop`** — neorv32_bus_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the selected AMO opcode vector from A or B to the external master so AMO operations carry the correct opcode.
  - **roles** — external AMO opcode; driven by selected port
  - **relationships** — **DERIVES_FROM** → a_req_i.amoop, b_req_i.amoop
  - **evidence** — x_req_o.amoop <= a_req_i.amoop when (sel = '0') else b_req_i.amoop.

**`x_req_o.ben`** — neorv32_bus_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwards the selected byte-enable vector from A or B to the external master; selection follows the same read-only and sel rules as data.
  - **roles** — external byte-enable; driven by selected port
  - **relationships** — **DERIVES_FROM** → a_req_i.ben, b_req_i.ben
  - **evidence** — x_req_o.ben concurrent assignment mirrors x_req_o.data selection using PORT_*_READ_ONLY and sel.

**`x_req_o.data`** — neorv32_bus_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the selected write data from A or B to the external master; selection depends on PORT_A_READ_ONLY/PORT_B_READ_ONLY generics and sel so read-only ports invert selection logic.
  - **roles** — external data output; driven by selected port
  - **relationships** — **DERIVES_FROM** → a_req_i.data, b_req_i.data
  - **evidence** — complex concurrent assignment uses PORT_A_READ_ONLY/PORT_B_READ_ONLY and sel to choose between a_req_i.data and b_req_i.data.

**`x_req_o.debug`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Forwards the selected debug flag from A or B to the external master so debug requests are preserved on the forwarded interface.
  - **roles** — external debug flag; driven by selected port
  - **relationships** — **DERIVES_FROM** → a_req_i.debug, b_req_i.debug
  - **evidence** — x_req_o.debug <= a_req_i.debug when (sel = '0') else b_req_i.debug.

**`x_req_o.fence`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Outputs the OR of A and B fence flags to the external master so fence semantics are forwarded regardless of which port issued them.
  - **roles** — external fence; aggregates fence inputs
  - **relationships** — **DERIVES_FROM** → a_req_i.fence, b_req_i.fence
  - **evidence** — x_req_o.fence <= a_req_i.fence or b_req_i.fence.

**`x_req_o.lock`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Forwards the selected lock bit from A or B to the external master so locked transfers maintain atomic access across the external interface.
  - **roles** — external lock; driven by selected port
  - **relationships** — **DERIVES_FROM** → a_req_i.lock, b_req_i.lock
  - **evidence** — x_req_o.lock <= a_req_i.lock when (sel = '0') else b_req_i.lock.

**`x_req_o.priv`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Forwards the selected priv flag from A or B to the external master so the forwarded request carries correct privilege information.
  - **roles** — external privilege; driven by selected port
  - **relationships** — **DERIVES_FROM** → a_req_i.priv, b_req_i.priv
  - **evidence** — x_req_o.priv <= a_req_i.priv when (sel = '0') else b_req_i.priv.

**`x_req_o.rw`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Forwards the selected rw bit from A or B to the external master so the access type is preserved on the forwarded request.
  - **roles** — external access type; driven by selected port
  - **relationships** — **DERIVES_FROM** → a_req_i.rw, b_req_i.rw
  - **evidence** — x_req_o.rw <= a_req_i.rw when (sel = '0') else b_req_i.rw.

**`x_req_o.src`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Forwards the selected src field from A or B to the external master so responses can be routed back to the originating port.
  - **roles** — external source tag; driven by selected port
  - **relationships** — **DERIVES_FROM** → a_req_i.src, b_req_i.src
  - **evidence** — x_req_o.src <= a_req_i.src when (sel = '0') else b_req_i.src.

**`x_req_o.stb`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Drives the forwarded strobe to the external master from the FSM-generated stb signal, reflecting the active request cycle presented externally.
  - **roles** — external request handshake; forwards internal stb
  - **relationships** — **CARRIES** → stb
  - **evidence** — x_req_o.stb <= stb.

**`x_rsp_i`** — neorv32_bus_switch · `bus_rsp_t`
  - **functionality** — Aggregates the external master's response fields (ack,err,data) which are read to drive a_rsp_o and b_rsp_o and to influence FSM transitions (x_rsp_i.ack used to leave busy state).
  - **roles** — input bundle; supplies external response fields
  - **relationships** — **AGGREGATES** → x_rsp_i.ack, x_rsp_i.err, x_rsp_i.data
  - **evidence** — x_rsp_i fields are used in FSM (x_rsp_i.ack) and in concurrent assignments to a_rsp_o.* and b_rsp_o.*.

**`x_rsp_i.ack`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies the external ack which is tested by the FSM to release busy state and is forwarded to the selected requester (A when sel='0', B when sel='1').
  - **roles** — external handshake; gates FSM transitions; feeds selected response ack
  - **relationships** — **SOURCES** → a_rsp_o.ack, b_rsp_o.ack; **GATES** → state_nxt
  - **evidence** — x_rsp_i.ack tested in S_BUSY_* branches to set state_nxt <= S_IDLE; used in conditional assignments to a_rsp_o.ack and b_rsp_o.ack.

**`x_rsp_i.data`** — neorv32_bus_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies the external data which is forwarded unchanged to both A and B response data outputs so the requesting port receives returned data.
  - **roles** — external response data; forwards data to both ports
  - **relationships** — **SOURCES** → a_rsp_o.data, b_rsp_o.data
  - **evidence** — a_rsp_o.data <= x_rsp_i.data; b_rsp_o.data <= x_rsp_i.data.

**`x_rsp_i.err`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Supplies the external error which is forwarded to the selected requester (A or B) so the requester sees error responses from the external master.
  - **roles** — external error; forwards error to selected port
  - **relationships** — **SOURCES** → a_rsp_o.err, b_rsp_o.err
  - **evidence** — a_rsp_o.err and b_rsp_o.err assigned from x_rsp_i.err with sel-based condition.

### signals

**`arbiter`** — neorv32_bus_amo_rmw · `arbiter_t`
  - **functionality** — Holds the AMO FSM state, captured command, read and write data; it is updated each clock from arbiter_nxt and its fields control sys_req_o selections and core responses.
  - **roles** — state register; holds AMO cmd and operands; drives sys_req_o/core_rsp_o decisions
  - **relationships** — **CAPTURES** → arbiter_nxt
  - **evidence** — arbiter <= arbiter_nxt on rising_edge(clk_i) in arbiter_sync

**`arbiter.cmd`** — neorv32_bus_amo_rmw · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Holds the AMO opcode captured from arbiter_nxt.cmd; its low bits select the ALU operation executed into alu_res.
  - **roles** — command holder; selects ALU operation
  - **relationships** — **CAPTURES** → arbiter_nxt.cmd; **SELECTS** → alu_res
  - **evidence** — arbiter <= arbiter_nxt in clocked process; amo_alu uses case arbiter.cmd(2 downto 0)

**`arbiter.rdata`** — neorv32_bus_amo_rmw · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Holds the read data captured from arbiter_nxt.rdata (from sys_rsp_i.data) and supplies operands to comparisons, the ALU, and the core response when not idle.
  - **roles** — read-data register; supplies operands and response data
  - **relationships** — **CAPTURES** → arbiter_nxt.rdata; **SOURCES** → cmp_opa, alu_res, core_rsp_o.data
  - **evidence** — arbiter <= arbiter_nxt (clock); cmp_opa <= ... arbiter.rdata; alu_res cases use unsigned(arbiter.rdata)

**`arbiter.state`** — neorv32_bus_amo_rmw · `state_t`
  - **functionality** — Captures the next FSM state from arbiter_nxt.state at the clock edge; the stored state selects muxes for sys_req_o fields and core_rsp_o outputs.
  - **roles** — FSM state holder; selects request/response behavior; governs update sequencing
  - **relationships** — **CAPTURES** → arbiter_nxt.state; **SELECTS** → sys_req_o.stb, sys_req_o.data, sys_req_o.rw, core_rsp_o.data, core_rsp_o.err, core_rsp_o.ack
  - **evidence** — arbiter <= arbiter_nxt (clock); concurrent when expressions use (arbiter.state = S_WRITE/S_IDLE/etc.) to choose outputs

**`arbiter.wdata`** — neorv32_bus_amo_rmw · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Holds the write-data captured from arbiter_nxt.wdata (from core_req_i.data) and supplies operands to the ALU and comparison operand generation.
  - **roles** — write-data register; supplies ALU and compare operand
  - **relationships** — **CAPTURES** → arbiter_nxt.wdata; **SOURCES** → cmp_opb, alu_res
  - **evidence** — arbiter <= arbiter_nxt (clock); cmp_opb <= ... arbiter.wdata; amo_alu uses arbiter.wdata in cases

**`arbiter_nxt`** — neorv32_bus_amo_rmw · `arbiter_t`
  - **functionality** — Combinational next-state record that is initialized from arbiter then modified by core_req_i and sys_rsp_i to produce the next FSM state, cmd, rdata and wdata.
  - **roles** — next-state aggregator; combinational FSM update
  - **relationships** — **DERIVES_FROM** → arbiter, core_req_i.data, core_req_i.amoop, sys_rsp_i.data
  - **evidence** — arbiter_comb: arbiter_nxt <= arbiter; fields set from core_req_i and sys_rsp_i inside case on arbiter.state

**`arbiter_nxt.cmd`** — neorv32_bus_amo_rmw · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Carries the next AMO opcode, defaulting from arbiter or captured from core_req_i.amoop when an AMO is started.
  - **roles** — next command; captures requested AMO opcode
  - **relationships** — **DERIVES_FROM** → core_req_i.amoop, arbiter
  - **evidence** — arbiter_nxt <= arbiter then arbiter_nxt.cmd <= core_req_i.amoop in S_IDLE branch

**`arbiter_nxt.rdata`** — neorv32_bus_amo_rmw · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries read data sampled from the system response (sys_rsp_i.data) into the arbiter next-record when in READ_WAIT; otherwise preserves arbiter.rdata.
  - **roles** — next read-data; captures system response data
  - **relationships** — **DERIVES_FROM** → sys_rsp_i.data, arbiter
  - **evidence** — in S_READ_WAIT: arbiter_nxt.rdata <= sys_rsp_i.data; arbiter_nxt <= arbiter as default

**`arbiter_nxt.state`** — neorv32_bus_amo_rmw · `state_t`
  - **functionality** — Holds the computed next FSM state derived from current arbiter.state, core_req_i conditions and sys_rsp_i.ack; it determines the arbiter's next-mode to be captured on the clock edge.
  - **roles** — next-state value; computed FSM control
  - **relationships** — **DERIVES_FROM** → arbiter
  - **evidence** — arbiter_comb sets arbiter_nxt.state per case S_IDLE/S_READ_WAIT/... using core_req_i and sys_rsp_i conditions

**`arbiter_nxt.wdata`** — neorv32_bus_amo_rmw · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the core's write data into the arbiter next-record when an AMO is initiated, otherwise defaults from arbiter.
  - **roles** — next write-data; captures core write operand
  - **relationships** — **DERIVES_FROM** → core_req_i.data, arbiter
  - **evidence** — in S_IDLE: arbiter_nxt.wdata <= core_req_i.data; arbiter_nxt <= arbiter as default

**`cmp_less`** — neorv32_bus_amo_rmw · `std_ulogic`
  - **functionality** — Reflects the result of the signed less-than comparison between cmp_opa and cmp_opb and is then used to choose cmp_res.
  - **roles** — comparison result; feeds cmp_res selection
  - **relationships** — **DERIVES_FROM** → cmp_opa, cmp_opb
  - **evidence** — cmp_less <= '1' when (signed(cmp_opa) < signed(cmp_opb)) else '0'

**`cmp_opa`** — neorv32_bus_amo_rmw · `std_ulogic_vector(32 downto 0)`
  - **functionality** — Constructs the signed-extended operand A from arbiter.rdata and the sign bit selected by arbiter.cmd(3); it is consumed by the signed less-than comparison.
  - **roles** — compare operand; constructed from arbiter.rdata
  - **relationships** — **DERIVES_FROM** → arbiter.rdata, arbiter.cmd
  - **evidence** — cmp_opa <= (arbiter.rdata(arbiter.rdata'left) and arbiter.cmd(3)) & arbiter.rdata

**`cmp_opb`** — neorv32_bus_amo_rmw · `std_ulogic_vector(32 downto 0)`
  - **functionality** — Constructs the signed-extended operand B from arbiter.wdata and the sign bit selected by arbiter.cmd(3); it is consumed by the signed less-than comparison.
  - **roles** — compare operand; constructed from arbiter.wdata
  - **relationships** — **DERIVES_FROM** → arbiter.wdata, arbiter.cmd
  - **evidence** — cmp_opb <= (arbiter.wdata(arbiter.wdata'left) and arbiter.cmd(3)) & arbiter.wdata

**`cmp_res`** — neorv32_bus_amo_rmw · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Selects between the lower 32 bits of cmp_opa or cmp_opb based on cmp_less xor arbiter.cmd(0) and provides the fallback ALU result for certain AMO operations.
  - **roles** — compare result; fallback ALU operand
  - **relationships** — **DERIVES_FROM** → cmp_opa, cmp_opb, arbiter.cmd
  - **evidence** — cmp_res <= cmp_opa(31 downto 0) when ((cmp_less xor arbiter.cmd(0)) = '1') else cmp_opb(31 downto 0)

**`rvso`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Is a combinational signal that indicates an AMO RVS-type operation (core_req_i.amo and amoop(3 downto 2) = "10"); it gates state transitions and influences sys_req_o.stb and is an input to sc_fail.
  - **roles** — RVS detection signal; combinational control; gates state updates; influences sys_req_o.stb; feeds sc_fail
  - **relationships** — **DERIVES_FROM** → core_req_i.amo; **SLICES** → core_req_i.amoop; **GATES** → state, sys_req_o.stb; **SOURCES** → sc_fail
  - **evidence** — rvso <= '1' when (core_req_i.amo = '1') and (core_req_i.amoop(3 downto 2) = "10") else '0'; rvso used in rvs_control, bus_request and sc_result.

**`sc_fail`** — neorv32_bus_amo_rvs · `std_ulogic`
  - **functionality** — Captures a boolean indicating SC failure on the rising clock edge from an expression of rvso, core_req_i.stb, core_req_i.rw and state(1); it then contributes to core_rsp_o.ack and core_rsp_o.data.
  - **roles** — SC failure register; holds SC-fail across cycles; feeds core response ack and data
  - **relationships** — **CAPTURES** → rvso, core_req_i.stb, core_req_i.rw, state; **SOURCES** → core_rsp_o.ack, core_rsp_o.data
  - **evidence** — sc_fail assigned in sc_result clocked process: sc_fail <= rvso and core_req_i.stb and core_req_i.rw and (not state(1)); sc_fail used in core_rsp_o assignments.

**`int_rsp`** — neorv32_bus_gateway · `bus_rsp_t`
  - **functionality** — Carries the OR-aggregated response built from port_rsp entries (data, ack, err) and supplies rsp_o fields and bus_monitor with combined status.
  - **roles** — aggregated response; feeds rsp_o outputs; feeds keeper logic
  - **relationships** — **DERIVES_FROM** → port_rsp; **SOURCES** → rsp_o
  - **evidence** — response process builds tmp_v from port_rsp then int_rsp <= tmp_v; rsp_o.* <= int_rsp.* assignments and bus_monitor reads int_rsp.ack

**`int_rsp.ack`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Carries the OR of all port_rsp(i).ack values into int_rsp.ack and is used both to form rsp_o.ack and to influence keeper busy release in bus_monitor.
  - **roles** — aggregated ack bit; feeds external ack output; gates keeper release
  - **relationships** — **DERIVES_FROM** → port_rsp; **SOURCES** → rsp_o; **CONSTRAINS** → keeper.busy
  - **evidence** — response process ORs port_rsp(i).ack into tmp_v.ack; int_rsp.ack used in bus_monitor condition and rsp_o.ack assignment

**`int_rsp.data`** — neorv32_bus_gateway · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the OR-aggregated data from all port_rsp entries into int_rsp.data and forwards it to rsp_o.data.
  - **roles** — aggregated data; feeds rsp_o.data
  - **relationships** — **DERIVES_FROM** → port_rsp; **SOURCES** → rsp_o
  - **evidence** — response process ORs port_rsp(i).data into tmp_v.data; int_rsp.data forwarded to rsp_o.data

**`int_rsp.err`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Carries the OR of all port_rsp(i).err values into int_rsp.err and is combined into rsp_o.err.
  - **roles** — aggregated error bit; feeds external error output
  - **relationships** — **DERIVES_FROM** → port_rsp; **SOURCES** → rsp_o
  - **evidence** — response process ORs port_rsp(i).err into tmp_v.err; rsp_o.err <= int_rsp.err or keeper.err

**`keeper`** — neorv32_bus_gateway · `keeper_t`
  - **functionality** — Aggregates keeper.busy, lock, cnt, err, halt fields into one record used to track request timeout and locking; groups the monitor registers.
  - **roles** — state record; aggregates keeper fields; holds monitor state
  - **relationships** — **AGGREGATES** → keeper.busy, keeper.lock, keeper.cnt, keeper.err, keeper.halt
  - **evidence** — keeper declared as record and bus_monitor process assigns its fields

**`keeper.busy`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Holds whether a request is outstanding; captured from req_i.stb when free and cleared on ack, lock-release or timeout; gates which bus_monitor branch executes.
  - **roles** — holds busy across cycles; gates monitor updates; indicates outstanding request
  - **relationships** — **CAPTURES** → req_i.stb; **GATES** → keeper.cnt; **GATES** → keeper.lock; **GATES** → keeper.err
  - **evidence** — keeper.busy <= req_i.stb when keeper.busy='0' in bus_monitor; if (keeper.busy='0') branch governs other assignments

**`keeper.lock`** — neorv32_bus_gateway · `std_ulogic`
  - **functionality** — Captures the request lock bit when a request starts and is later tested with req_i.lock to decide early release of busy.
  - **roles** — holds lock flag; feeds release decision
  - **relationships** — **CAPTURES** → req_i.lock; **CONSTRAINS** → keeper.busy
  - **evidence** — keeper.lock <= req_i.lock in bus_monitor; ((keeper.lock = '1') and (req_i.lock = '0')) condition clears keeper.busy

**`port_req`** — neorv32_bus_gateway · `port_req_t`
  - **functionality** — Holds the candidate request for each port, built from req_i or terminated default and with stb masked by port_sel; drives the external a/b/c/x request outputs.
  - **roles** — carries per-port requests; inter-stage buffer; feeds external port outputs
  - **relationships** — **DERIVES_FROM** → req_i; **GATES** → port_sel; **SOURCES** → a_req_o, b_req_o, c_req_o, x_req_o
  - **evidence** — request process assigns port_req(i) and concurrent mappings a_req_o <= port_req(0) etc

**`port_rsp`** — neorv32_bus_gateway · `port_rsp_t`
  - **functionality** — Receives each external port's response (assigned from a_rsp_i..x_rsp_i) and provides the inputs that the response process OR-aggregates into int_rsp.
  - **roles** — collects external responses; feeds response aggregator; carries per-port responses
  - **relationships** — **CARRIES** → a_rsp_i, b_rsp_i, c_rsp_i, x_rsp_i; **SOURCES** → int_rsp
  - **evidence** — concurrent mappings port_rsp(i) <= a/b/c/x_rsp_i and response process reads port_rsp to build tmp_v then int_rsp

**`dev_req`** — neorv32_bus_io_switch · `dev_req_t`
  - **functionality** — Provides an array of per-device request records: each dev_req(i) is driven either from main_req (with stb gated by address match) when enabled or from a terminate constant when disabled; supplies device request ports.
  - **roles** — per-device request carrier; source for device ports; combines host input into per-device outputs
  - **relationships** — **DERIVES_FROM** → main_req; **SOURCES** → dev_29_req_o, dev_30_req_o, dev_31_req_o
  - **evidence** — bus_request generate: dev_req(i) <= main_req; disabled branch assigns req_terminate_c; concurrent assignments bind dev_req(i) to dev_x_req_o.

**`dev_rsp`** — neorv32_bus_io_switch · `dev_rsp_t`
  - **functionality** — Collects external device responses into an array; each dev_rsp(i) is driven from the corresponding dev_x_rsp_i port and is read by the response aggregator to form main_rsp.
  - **roles** — per-device response carrier; source for response aggregator
  - **relationships** — **DERIVES_FROM** → dev_29_rsp_i, dev_30_rsp_i, dev_31_rsp_i; **SOURCES** → main_rsp
  - **evidence** — Concurrent assignments dev_rsp(i) <= dev_x_rsp_i map port inputs into dev_rsp; bus_response process reads dev_rsp(i) fields.

**`main_req`** — neorv32_bus_io_switch · `bus_req_t`
  - **functionality** — Receives the (optionally registered) host request from the bus register instance (neorv32_bus_reg_inst.device_req_o) and supplies that request to per-device generators; its addr slice gates which device sees stb.
  - **roles** — internal host request; drives per-device demux; derived from bus register instance
  - **relationships** — **DERIVES_FROM** → neorv32_bus_reg_inst.device_req_o; **SOURCES** → dev_req; **CONSTRAINS** → dev_req
  - **evidence** — Instance port map device_req_o => main_req provides value; bus_request process uses main_req and its addr slice to build dev_req(i).stb.

**`main_req.addr`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Holds the address vector of the internal host request; the addr slice is compared to each device base to select which device's stb is enabled for the forwarded request.
  - **roles** — carries host address; governs device selection
  - **relationships** — **CONSTRAINS** → dev_req; **SOURCES** → dev_req
  - **evidence** — Condition in bus_request process: main_req.addr(addr_hi_c downto addr_lo_c) = dev_base_list_c(i)(addr_hi_c downto addr_lo_c) gates dev_req(i).stb assignment.

**`main_req.amo`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the atomic-op indicator from the host request and forwards it into per-device request copies.
  - **roles** — carries amo flag; feeds device request copies
  - **relationships** — **SOURCES** → dev_req
  - **evidence** — dev_req(i) <= main_req in bus_request process forwards amo field to dev_req.

**`main_req.amoop`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Carries the AMO operation code bits from the host request and forwards them into per-device request copies.
  - **roles** — carries amoop; feeds device request copies
  - **relationships** — **SOURCES** → dev_req
  - **evidence** — dev_req(i) <= main_req in bus_request process forwards amoop field to dev_req.

**`main_req.ben`** — neorv32_bus_io_switch · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Carries the byte-enable bits from the host request into the per-device request copies; forwarded unchanged into dev_req entries.
  - **roles** — carries ben field; feeds device request copies
  - **relationships** — **SOURCES** → dev_req
  - **evidence** — dev_req(i) <= main_req in bus_request process forwards ben field to dev_req.

**`main_req.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the request data field from the host (via instance) into the per-device request copy; forwarded into each enabled dev_req(i) by the request generator.
  - **roles** — carries request data; feeds device request copies
  - **relationships** — **SOURCES** → dev_req
  - **evidence** — bus_request process assigns dev_req(i) <= main_req, which forwards the data field into dev_req.

**`main_req.debug`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the debug bit from the host request and forwards it into per-device request copies.
  - **roles** — carries debug flag; feeds device request copies
  - **relationships** — **SOURCES** → dev_req
  - **evidence** — dev_req(i) <= main_req in bus_request process forwards debug field to dev_req.

**`main_req.fence`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the fence control bit from the host request and forwards it into per-device request copies.
  - **roles** — carries fence flag; feeds device request copies
  - **relationships** — **SOURCES** → dev_req
  - **evidence** — dev_req(i) <= main_req in bus_request process forwards fence field to dev_req.

**`main_req.lock`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the lock bit from the host request and forwards it into per-device request copies.
  - **roles** — carries lock flag; feeds device request copies
  - **relationships** — **SOURCES** → dev_req
  - **evidence** — dev_req(i) <= main_req in bus_request process forwards lock field to dev_req.

**`main_req.priv`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the privilege bit from the host request and forwards it into per-device request copies.
  - **roles** — carries priv bit; feeds device request copies
  - **relationships** — **SOURCES** → dev_req
  - **evidence** — dev_req(i) <= main_req in bus_request process forwards priv field to dev_req.

**`main_req.rw`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the read/write indicator from the host request and forwards it into per-device request copies.
  - **roles** — carries rw flag; feeds device request copies
  - **relationships** — **SOURCES** → dev_req
  - **evidence** — dev_req(i) <= main_req in bus_request process forwards rw field to dev_req.

**`main_req.src`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the source bit from the host request and forwards it into per-device request copies.
  - **roles** — carries src field; feeds device request copies
  - **relationships** — **SOURCES** → dev_req
  - **evidence** — dev_req(i) <= main_req in bus_request process forwards src field to dev_req.

**`main_req.stb`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Supplies the strobe bit used to signal a valid request; it is forwarded into dev_req(i) and is explicitly used to set dev_req(i).stb when the device base matches, otherwise dev_req(i).stb is '0'.
  - **roles** — carries request strobe; drives per-device stb
  - **relationships** — **SOURCES** → dev_req; **SOURCES** → dev_req
  - **evidence** — bus_request process: dev_req(i) <= main_req; dev_req(i).stb <= main_req.stb when address matches, else '0'.

**`main_rsp`** — neorv32_bus_io_switch · `bus_rsp_t`
  - **functionality** — Produces the host response by aggregating per-device responses: the bus_response process ORs dev_rsp(i).data/ack/err into tmp_v and assigns that to main_rsp, which is then presented to the bus register instance input.
  - **roles** — aggregator of device responses; feeds bus register instance input
  - **relationships** — **DERIVES_FROM** → dev_rsp; **SOURCES** → neorv32_bus_reg_inst.device_rsp_i
  - **evidence** — bus_response process builds tmp_v by ORing dev_rsp(i) fields and then main_rsp <= tmp_v; port map connects device_rsp_i => main_rsp.

**`main_rsp.ack`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the OR of device ack bits into the host response ack field; derived by OR-ing dev_rsp(i).ack across enabled devices.
  - **roles** — aggregated ack; feeds instance device_rsp_i
  - **relationships** — **DERIVES_FROM** → dev_rsp; **SOURCES** → neorv32_bus_reg_inst.device_rsp_i
  - **evidence** — bus_response process ORs dev_rsp(i).ack into tmp_v.ack then main_rsp <= tmp_v; main_rsp is mapped to instance device_rsp_i.

**`main_rsp.data`** — neorv32_bus_io_switch · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the OR-reduction of device response data words into the host response data field; derived by OR-ing dev_rsp(i).data across enabled devices and assigned to main_rsp.data.
  - **roles** — aggregated data; feeds instance device_rsp_i
  - **relationships** — **DERIVES_FROM** → dev_rsp; **SOURCES** → neorv32_bus_reg_inst.device_rsp_i
  - **evidence** — bus_response process: tmp_v.data := tmp_v.data or dev_rsp(i).data in loop; then main_rsp <= tmp_v; main_rsp mapped to instance device_rsp_i.

**`main_rsp.err`** — neorv32_bus_io_switch · `std_ulogic`
  - **functionality** — Carries the OR of device error bits into the host response err field; derived by OR-ing dev_rsp(i).err across enabled devices.
  - **roles** — aggregated error; feeds instance device_rsp_i
  - **relationships** — **DERIVES_FROM** → dev_rsp; **SOURCES** → neorv32_bus_reg_inst.device_rsp_i
  - **evidence** — bus_response process ORs dev_rsp(i).err into tmp_v.err then main_rsp <= tmp_v; main_rsp is mapped to instance device_rsp_i.

**`locked`** — neorv32_bus_switch · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Holds the two-bit latched lock state captured from locked_nxt each cycle; its per-bit values are checked in busy branches to decide whether to forward stb or to rely on per-port lock semantics.
  - **roles** — latched lock vector; holds lock bits across cycles; gates busy-branch behaviour
  - **relationships** — **CAPTURES** → locked_nxt; **GATES** → stb, state_nxt
  - **evidence** — locked <= locked_nxt in arbiter_sync; arbiter_fsm checks locked(0)/locked(1) in S_BUSY_* branches to choose stb and state transitions.

**`locked_nxt`** — neorv32_bus_switch · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Combinationally computes the next locked vector as the concatenation/combination of the current inputs (locked default then b_req_i.lock & a_req_i.lock) and is captured into locked on the next clock edge.
  - **roles** — next-lock combinational value; feeds locked register
  - **relationships** — **DERIVES_FROM** → locked, b_req_i.lock, a_req_i.lock; **SOURCES** → locked
  - **evidence** — locked_nxt <= locked default then locked_nxt <= b_req_i.lock & a_req_i.lock in others branch; locked <= locked_nxt on rising_edge.

**`sel_q`** — neorv32_bus_switch · `std_ulogic`
  - **functionality** — Holds the previous-cycle sel value (captured from sel) and is used by the FSM's round-robin logic to bias next arbitration decisions, thereby influencing which port is favored next.
  - **roles** — registered selection; biases next arbitration decisions; gates FSM selection logic
  - **relationships** — **CAPTURES** → sel; **GATES** → state_nxt, sel, stb
  - **evidence** — sel_q <= sel in arbiter_sync; sel_q used in arbiter_fsm condition (if sel_q = '1' or not ROUND_ROBIN_EN) then ... to choose priority.

**`state_nxt`** — neorv32_bus_switch · `state_t`
  - **functionality** — Holds the combinationally computed next FSM state (derived from state and request/response inputs) and is the value captured into state on the next clock edge.
  - **roles** — next-state combinational value; feeds state register
  - **relationships** — **DERIVES_FROM** → state; **SOURCES** → state
  - **evidence** — state_nxt <= state default then modified in arbiter_fsm case branches; state <= state_nxt on rising_edge(clk_i).


## neorv32_cache  (81 non-assets)

### ports

**`bus_req_o`** — neorv32_cache · `bus_req_t`
  - **functionality** — Carries a bus request to the external bus: default-copies host_req_i, but the controller overrides fields (addr, rw, stb, lock, fence) during clear and download sequences.
  - **roles** — bus request carrier; forwards host requests; driven by controller
  - **relationships** — **CARRIES** → host_req_i; **DERIVES_FROM** → ctrl.tag, ctrl.idx, ctrl.ofs
  - **evidence** — bus_req_o <= host_req_i; bus_req_o.addr <= ctrl.tag & ctrl.idx & ctrl.ofs & "00" in DOWNLOAD_REQ/RSP.

**`bus_req_o.addr`** — neorv32_cache · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Set from the host request by default and overridden during downloads to the assembled address from ctrl.tag, ctrl.idx and ctrl.ofs (LSB '00').
  - **roles** — bus address output; driven by controller during download
  - **relationships** — **DERIVES_FROM** → ctrl.tag, ctrl.idx, ctrl.ofs, host_req_i.addr
  - **evidence** — bus_req_o <= host_req_i and bus_req_o.addr <= ctrl.tag & ctrl.idx & ctrl.ofs & "00" in DOWNLOAD_REQ/RSP.

**`bus_req_o.amo`** — neorv32_cache · `std_ulogic`
  - **functionality** — Forwarded unchanged from host_req_i.amo into the bus request record.
  - **roles** — forwarded field
  - **relationships** — **SOURCES** → host_req_i.amo
  - **evidence** — bus_req_o <= host_req_i.

**`bus_req_o.amoop`** — neorv32_cache · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwarded unchanged from host_req_i.amoop into the bus request record.
  - **roles** — forwarded field
  - **relationships** — **SOURCES** → host_req_i.amoop
  - **evidence** — bus_req_o <= host_req_i.

**`bus_req_o.ben`** — neorv32_cache · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwarded from host_req_i.ben to the bus request record; used when the controller forwards writes.
  - **roles** — byte-enable output; forwarded field
  - **relationships** — **SOURCES** → host_req_i.ben
  - **evidence** — bus_req_o <= host_req_i.

**`bus_req_o.data`** — neorv32_cache · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries write data to the bus, forwarded from host_req_i.data by default.
  - **roles** — write data output; forwarded from host
  - **relationships** — **SOURCES** → host_req_i.data
  - **evidence** — bus_req_o <= host_req_i in ctrl_engine_comb.

**`bus_req_o.debug`** — neorv32_cache · `std_ulogic`
  - **functionality** — Forwarded unchanged from host_req_i.debug into bus_req_o.
  - **roles** — forwarded field
  - **relationships** — **SOURCES** → host_req_i.debug
  - **evidence** — bus_req_o <= host_req_i.

**`bus_req_o.fence`** — neorv32_cache · `std_ulogic`
  - **functionality** — Asserted by the controller during S_CLEAR (if READ_ONLY=false) to issue bus fence; otherwise part of forwarded host_req_i.
  - **roles** — fence output; driven during clear
  - **relationships** — **DERIVES_FROM** → ctrl.state, host_req_i.fence
  - **evidence** — S_CLEAR sets bus_req_o.fence <= '1' (conditional on READ_ONLY); bus_req_o <= host_req_i otherwise.

**`bus_req_o.lock`** — neorv32_cache · `std_ulogic`
  - **functionality** — Initially copied from host_req_i.lock; for block downloads the controller forces lock='1' on the bus request.
  - **roles** — lock flag output; forwarded then overridden
  - **relationships** — **SOURCES** → host_req_i.lock; **DERIVES_FROM** → ctrl.state
  - **evidence** — bus_req_o <= host_req_i; bus_req_o.lock <= '1' in S_DOWNLOAD_REQ/RSP.

**`bus_req_o.priv`** — neorv32_cache · `std_ulogic`
  - **functionality** — Forwarded unchanged from host_req_i.priv into the bus request record.
  - **roles** — forwarded field
  - **relationships** — **SOURCES** → host_req_i.priv
  - **evidence** — bus_req_o <= host_req_i.

**`bus_req_o.rw`** — neorv32_cache · `std_ulogic`
  - **functionality** — Forwarded from the host request by default; overridden by the controller to read ('0') during block-download requests.
  - **roles** — bus operation flag; overridden by controller for downloads
  - **relationships** — **SOURCES** → host_req_i.rw; **DERIVES_FROM** → ctrl.state
  - **evidence** — bus_req_o <= host_req_i; bus_req_o.rw <= '0' in S_DOWNLOAD_REQ/RSP.

**`bus_req_o.src`** — neorv32_cache · `std_ulogic`
  - **functionality** — Forwarded from host_req_i.src unchanged into the outgoing bus request record.
  - **roles** — forwarded field
  - **relationships** — **SOURCES** → host_req_i.src
  - **evidence** — bus_req_o <= host_req_i.

**`bus_req_o.stb`** — neorv32_cache · `std_ulogic`
  - **functionality** — Asserted by the controller to start external bus transactions; default '0' and set in LOOKUP, DIRECT and DOWNLOAD states when appropriate.
  - **roles** — transaction trigger; driven by FSM; outputs request start
  - **relationships** — **DERIVES_FROM** → ctrl.buf_dir, host_req_i.stb, ctrl.state
  - **evidence** — bus_req_o.stb <= '0' default; set to '1' in S_LOOKUP (direct/write) and S_DOWNLOAD_REQ.

**`bus_rsp_i`** — neorv32_cache · `bus_rsp_t`
  - **functionality** — Carries responses from the external bus into the controller; used for direct responses (copied to host_rsp_o) and for downloads (data/ack/err feed cache logic).
  - **roles** — bus response source; feeds download and direct flows
  - **relationships** — **SOURCES** → host_rsp_o, cache_o.data, ctrl_nxt.buf_err
  - **evidence** — host_rsp_o <= bus_rsp_i in S_DIRECT_RSP; cache_o.data <= bus_rsp_i.data in S_DOWNLOAD_RSP; ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err.

**`bus_rsp_i.ack`** — neorv32_cache · `std_ulogic`
  - **functionality** — Indicates completion of a bus transaction; used to advance the FSM (direct response completion and download word progression).
  - **roles** — transaction complete signal; drives FSM progress
  - **relationships** — **GATES** → ctrl_nxt.state, ctrl_nxt.ofs
  - **evidence** — If (bus_rsp_i.ack = '1') then ctrl_nxt.state <= S_IDLE in S_DIRECT_RSP; DOWNLOAD_RSP increments ctrl_nxt.ofs on ack.

**`bus_rsp_i.data`** — neorv32_cache · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries data from bus responses into the controller; used to supply cache_o.data during downloads and forwarded to the host on direct responses.
  - **roles** — download data source; forwarded to host
  - **relationships** — **SOURCES** → cache_o.data, host_rsp_o.data
  - **evidence** — cache_o.data <= bus_rsp_i.data in S_DOWNLOAD_RSP; host_rsp_o <= bus_rsp_i in S_DIRECT_RSP.

**`bus_rsp_i.err`** — neorv32_cache · `std_ulogic`
  - **functionality** — Signals bus transfer errors; ORed into ctrl_nxt.buf_err during downloads and forwarded to host in direct responses.
  - **roles** — error input; propagated into buffer error and host response
  - **relationships** — **SOURCES** → ctrl_nxt.buf_err, host_rsp_o.err
  - **evidence** — ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err; host_rsp_o <= bus_rsp_i in S_DIRECT_RSP.

**`clk_i`** — neorv32_cache · `std_ulogic`
  - **functionality** — Supplies the clock edge to the controller's sequential process that updates ctrl and is forwarded to the cache memory instance clock input.
  - **roles** — clock input; drives sequential update; propagates to cache memory
  - **relationships** — **SEQUENCES** → ctrl; **SOURCES** → neorv32_cache_memory_inst.clk_i
  - **evidence** — ctrl_engine_sync sensitivity list and rising_edge(clk_i) and instance port map (clk_i => clk_i).

**`host_req_i`** — neorv32_cache · `bus_req_t`
  - **functionality** — Supplies all host request fields to the controller; the record is copied to bus_req_o by default and individual fields feed cache_o and the control logic.
  - **roles** — input request carrier; supplies request fields to bus; source for cache inputs
  - **relationships** — **CARRIES** → bus_req_o; **SOURCES** → cache_o.addr, cache_o.data, cache_o.we
  - **evidence** — bus_req_o <= host_req_i; cache_o.addr <= host_req_i.addr; cache_o.data <= host_req_i.data in ctrl_engine_comb.

**`host_req_i.addr`** — neorv32_cache · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the 32-bit address to compute tag/index and to drive cache_o.addr and bus_req_o.addr (default or overridden during downloads).
  - **roles** — address operand; feeds tag/index extraction; drives bus/cache addresses
  - **relationships** — **SOURCES** → ctrl_nxt.tag, ctrl_nxt.idx; **SOURCES** → cache_o.addr; **SOURCES** → bus_req_o.addr
  - **evidence** — ctrl_nxt.tag <= host_req_i.addr(31 downto 32-tag_size_c); cache_o.addr <= host_req_i.addr; bus_req_o <= host_req_i.

**`host_req_i.amo`** — neorv32_cache · `std_ulogic`
  - **functionality** — If set it marks the request for direct bus forwarding by setting buf_dir in S_IDLE and is forwarded to the bus request record.
  - **roles** — AMO qualifier; enables direct forwarding; forwarded
  - **relationships** — **GATES** → ctrl_nxt.buf_dir; **SOURCES** → bus_req_o.amo
  - **evidence** — S_IDLE tests host_req_i.amo to set ctrl_nxt.buf_dir; bus_req_o <= host_req_i.

**`host_req_i.amoop`** — neorv32_cache · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Forwarded unchanged to bus_req_o as part of the forwarded host request; not inspected here.
  - **roles** — forwarded field; propagates to bus
  - **relationships** — **SOURCES** → bus_req_o.amoop
  - **evidence** — bus_req_o <= host_req_i.

**`host_req_i.ben`** — neorv32_cache · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Provides byte-enable mask for host writes; used to set cache_o.we on writes and forwarded to bus_req_o.ben by default.
  - **roles** — byte-enable operand; drives cache write mask; forwarded to bus
  - **relationships** — **SOURCES** → cache_o.we, bus_req_o.ben
  - **evidence** — cache_o.we <= host_req_i.ben when write path; bus_req_o <= host_req_i.

**`host_req_i.data`** — neorv32_cache · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies write data from the host; forwarded into cache_o.data for writes and into bus_req_o.data when requests are forwarded to the bus.
  - **roles** — write data source; forwarded to bus; supplies cache write data
  - **relationships** — **SOURCES** → cache_o.data, bus_req_o.data
  - **evidence** — cache_o.data <= host_req_i.data; bus_req_o <= host_req_i in ctrl_engine_comb.

**`host_req_i.debug`** — neorv32_cache · `std_ulogic`
  - **functionality** — If asserted in S_IDLE it forces the controller to mark the request for direct forwarding (buf_dir); otherwise forwarded into bus_req_o.
  - **roles** — control qualifier; enables direct forwarding; forwarded
  - **relationships** — **GATES** → ctrl_nxt.buf_dir; **SOURCES** → bus_req_o.debug
  - **evidence** — S_IDLE checks host_req_i.debug to set ctrl_nxt.buf_dir; bus_req_o <= host_req_i.

**`host_req_i.fence`** — neorv32_cache · `std_ulogic`
  - **functionality** — Requests cache synchronization/clear: sets ctrl_nxt.buf_sync and triggers S_CLEAR when asserted, and is also forwarded in host request copy.
  - **roles** — synchronization request; requests cache clear; forwarded
  - **relationships** — **SOURCES** → ctrl_nxt.buf_sync; **GATES** → ctrl_nxt.state
  - **evidence** — ctrl_nxt.buf_sync <= ctrl.buf_sync or host_req_i.fence; S_IDLE checks host_req_i.fence to go to S_CLEAR.

**`host_req_i.lock`** — neorv32_cache · `std_ulogic`
  - **functionality** — Initially forwarded into bus_req_o on record copy; for downloads the controller overrides lock to '1' when forming bus requests.
  - **roles** — forwarded field; initial bus lock source
  - **relationships** — **SOURCES** → bus_req_o.lock
  - **evidence** — bus_req_o <= host_req_i then bus_req_o.lock <= '1' in DOWNLOAD_REQ.

**`host_req_i.priv`** — neorv32_cache · `std_ulogic`
  - **functionality** — Passed through into bus_req_o unchanged; not otherwise consumed by this entity.
  - **roles** — forwarded field; propagates to bus
  - **relationships** — **SOURCES** → bus_req_o.priv
  - **evidence** — bus_req_o <= host_req_i.

**`host_req_i.rw`** — neorv32_cache · `std_ulogic`
  - **functionality** — Selects read versus write handling in S_LOOKUP: read may complete from cache, write triggers cache writes or direct bus transactions.
  - **roles** — operation selector; controls write vs read path
  - **relationships** — **GATES** → ctrl_nxt.state, cache_o.we
  - **evidence** — S_LOOKUP branches test host_req_i.rw to decide host_rsp_o.ack or set cache_o.we and bus_req_o.stb.

**`host_req_i.src`** — neorv32_cache · `std_ulogic`
  - **functionality** — Forwarded unchanged into bus_req_o when the host request is copied to the bus; not otherwise inspected here.
  - **roles** — forwarded field; passes through to bus
  - **relationships** — **SOURCES** → bus_req_o.src
  - **evidence** — bus_req_o <= host_req_i in ctrl_engine_comb.

**`host_req_i.stb`** — neorv32_cache · `std_ulogic`
  - **functionality** — Signals a new host request; sets ctrl_nxt.buf_req and participates in conditions that move the FSM into lookup state.
  - **roles** — request qualifier; triggers lookup; buffers requests
  - **relationships** — **SOURCES** → ctrl_nxt.buf_req; **GATES** → ctrl_nxt.state
  - **evidence** — ctrl_nxt.buf_req <= ctrl.buf_req or host_req_i.stb; used in S_IDLE condition (host_req_i.stb = '1').

**`host_rsp_o`** — neorv32_cache · `bus_rsp_t`
  - **functionality** — Reports responses to the host: by default data is driven from cache_i.data and ack/err default '0'; in S_DIRECT_RSP the whole bus_rsp_i record is copied to host_rsp_o.
  - **roles** — response carrier; reports cached or bus response; exports to host
  - **relationships** — **CARRIES** → bus_rsp_i; **CARRIES** → cache_i.data
  - **evidence** — host_rsp_o. data <= cache_i.data default; host_rsp_o <= bus_rsp_i in S_DIRECT_RSP; other host_rsp_o field assignments in case arms.

**`host_rsp_o.ack`** — neorv32_cache · `std_ulogic`
  - **functionality** — Signals request completion to the host; defaults to '0', asserted for cache-hit reads, on download completion or when a direct bus response is copied.
  - **roles** — response acknowledge; drives host handshake; derived from cache/bus and ctrl
  - **relationships** — **DERIVES_FROM** → bus_rsp_i.ack, cache_i.sta_hit, ctrl.buf_err
  - **evidence** — host_rsp_o.ack <= '0' default; host_rsp_o.ack <= '1' on cache hit and in S_DOWNLOAD_DONE when buf_err or when copying bus_rsp_i.

**`host_rsp_o.data`** — neorv32_cache · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides returned data to the host: by default from cache_i.data and in direct responses copied from bus_rsp_i.data.
  - **roles** — response data; forwards cache or bus data to host
  - **relationships** — **CARRIES** → bus_rsp_i.data; **CARRIES** → cache_i.data
  - **evidence** — host_rsp_o.data <= cache_i.data default; host_rsp_o <= bus_rsp_i in S_DIRECT_RSP.

**`host_rsp_o.err`** — neorv32_cache · `std_ulogic`
  - **functionality** — Reports errors to the host: default '0', set on download buffer error or when a direct bus response with err is forwarded.
  - **roles** — error reporting; reports bus/buffer error to host
  - **relationships** — **DERIVES_FROM** → bus_rsp_i.err, ctrl.buf_err
  - **evidence** — host_rsp_o.err <= '0' default; host_rsp_o.err <= '1' in S_DOWNLOAD_DONE when ctrl.buf_err; host_rsp_o <= bus_rsp_i in S_DIRECT_RSP.

**`rstn_i`** — neorv32_cache · `std_ulogic`
  - **functionality** — Provides asynchronous reset used to initialize ctrl fields on rstn_i='0' and is forwarded to the cache memory instance reset input.
  - **roles** — reset input; initialises ctrl; propagates to cache memory
  - **relationships** — **SEQUENCES** → ctrl; **SOURCES** → neorv32_cache_memory_inst.rstn_i
  - **evidence** — if (rstn_i = '0') branch in ctrl_engine_sync and instance port map (rstn_i => rstn_i).

**`clk_i`** — neorv32_cache_memory · `std_ulogic`
  - **functionality** — Clocks the three sequential processes; rising_edge(clk_i) sequences updates to valid_mem and valid_mem_rd, tag_mem and tag_mem_rd, and the data memories and rdata_o.
  - **roles** — clock for status, tag and data processes; synchronises register updates
  - **relationships** — **SEQUENCES** → valid_mem, valid_mem_rd, tag_mem, tag_mem_rd, data_mem_b0, data_mem_b1, data_mem_b2, data_mem_b3, rdata_o
  - **evidence** — rising_edge(clk_i) appears in status_memory, tag_memory and data_memory processes.

**`clr_i`** — neorv32_cache_memory · `std_ulogic`
  - **functionality** — When asserted at the clock edge inside status_memory, it forces valid_mem to all '0's, overriding per-index updates and other write conditions.
  - **roles** — global valid bits clear; overrides per-index updates
  - **relationships** — **OVERRIDES** → valid_mem
  - **evidence** — status_memory: if (clr_i = '1') then valid_mem <= (others => '0');

**`hit_o`** — neorv32_cache_memory · `std_ulogic`
  - **functionality** — Combinationally reports a hit when valid_mem_rd = '1' and the sampled tag (tag_mem_rd) equals acc_tag; it exports the internal hit decision.
  - **roles** — reports hit status; exports internal comparator result
  - **relationships** — **DERIVES_FROM** → valid_mem_rd, tag_mem_rd, acc_tag
  - **evidence** — concurrent assignment: hit_o <= '1' when (valid_mem_rd = '1') and (tag_mem_rd = acc_tag) else '0';

**`inv_i`** — neorv32_cache_memory · `std_ulogic`
  - **functionality** — When asserted at the clock edge inside status_memory, it clears the valid_mem bit at acc_idx, overriding normal updates for that index.
  - **roles** — index-specific invalidation; overrides valid_mem bit
  - **relationships** — **OVERRIDES** → valid_mem
  - **evidence** — status_memory: elsif (inv_i = '1') then valid_mem(to_integer(unsigned(acc_idx))) <= '0';

**`new_i`** — neorv32_cache_memory · `std_ulogic`
  - **functionality** — When asserted at the clock edge, it sets the valid_mem bit at acc_idx and writes acc_tag into tag_mem at acc_idx, enabling new-line installation logic.
  - **roles** — enable for installing new cache line; overrides per-index valid/tag updates
  - **relationships** — **OVERRIDES** → valid_mem, tag_mem
  - **evidence** — status_memory and tag_memory: elsif (new_i = '1') then valid_mem(...) <= '1'; tag_mem(...) <= acc_tag;

**`rdata_o`** — neorv32_cache_memory · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Registers and outputs the assembled 32-bit word composed of bytes read from data_mem_b0..b3 at acc_adr on the rising clock, making memory contents available externally.
  - **roles** — exports read data; registered read result
  - **relationships** — **CAPTURES** → data_mem_b0; **CAPTURES** → data_mem_b1; **CAPTURES** → data_mem_b2; **CAPTURES** → data_mem_b3
  - **evidence** — data_memory (rising_edge): rdata_o(7 downto 0) <= data_mem_b0(...); rdata_o(15 downto 8) <= data_mem_b1(...); etc.

**`rstn_i`** — neorv32_cache_memory · `std_ulogic`
  - **functionality** — Provides the reset condition used by the status_memory process; when '0' it forces valid_mem and valid_mem_rd to their reset values in the reset branch of that process.
  - **roles** — asynchronous reset; controls status_memory registers
  - **relationships** — **SEQUENCES** → valid_mem, valid_mem_rd
  - **evidence** — status_memory process sensitivity and reset branch: if (rstn_i = '0') then valid_mem/valid_mem_rd set (reset).

**`wdata_i`** — neorv32_cache_memory · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies 32-bit write data whose byte slices are written into data_mem_b0..b3 at acc_adr when corresponding we_i bits are set at the clock edge.
  - **roles** — provides bytes for writes; feeds data memory stores
  - **relationships** — **SOURCES** → data_mem_b0; **SOURCES** → data_mem_b1; **SOURCES** → data_mem_b2; **SOURCES** → data_mem_b3
  - **evidence** — data_memory: data_mem_b0(...) <= wdata_i(7 downto 0); etc., inside rising_edge when corresponding we_i bit is '1'.

### signals

**`cache_i`** — neorv32_cache · `cache_i_t`
  - **functionality** — Collects hit and read-data outputs from the cache memory instance and provides them to the controller logic (hit tests and host data).
  - **roles** — cache status/data receiver; supplies hit and read data to controller
  - **relationships** — **CARRIES** → neorv32_cache_memory_inst.rdata_o, neorv32_cache_memory_inst.hit_o; **SOURCES** → host_rsp_o.data
  - **evidence** — instance port map rdata_o => cache_i.data, hit_o => cache_i.sta_hit; cache_i.data used as host_rsp_o.data default.

**`cache_i.data`** — neorv32_cache · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries read data produced by the cache memory and is used as the default host response data when a cache hit occurs.
  - **roles** — read data source; forwards memory read data to host
  - **relationships** — **CARRIES** → neorv32_cache_memory_inst.rdata_o; **SOURCES** → host_rsp_o.data
  - **evidence** — port map rdata_o => cache_i.data; host_rsp_o.data <= cache_i.data in ctrl_engine_comb.

**`cache_o.addr`** — neorv32_cache · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the 32-bit address either taken from the host request or constructed from ctrl.tag/idx/ofs during downloads, and forwards it to the cache memory addr_i.
  - **roles** — address carrier; driven by host or controller
  - **relationships** — **DERIVES_FROM** → ctrl.tag, ctrl.idx, ctrl.ofs, host_req_i.addr; **SOURCES** → neorv32_cache_memory_inst.addr_i
  - **evidence** — cache_o.addr <= host_req_i.addr default; cache_o.addr <= ctrl.tag & ctrl.idx & ctrl.ofs & "00" in S_DOWNLOAD_REQ; port map addr_i => cache_o.addr.

**`cache_o.cmd_clr`** — neorv32_cache · `std_ulogic`
  - **functionality** — Asserted in the S_CLEAR arm to command cache memory clear; defaulted to '0' otherwise and forwarded to cache instance clr_i.
  - **roles** — control output; drives cache clear
  - **relationships** — **SOURCES** → neorv32_cache_memory_inst.clr_i
  - **evidence** — cache_o.cmd_clr <= '0' default and cache_o.cmd_clr <= '1' in S_CLEAR; port map clr_i => cache_o.cmd_clr.

**`cache_o.cmd_inv`** — neorv32_cache · `std_ulogic`
  - **functionality** — Asserted on download error to invalidate the newly downloaded line and forwarded to the cache instance inv_i.
  - **roles** — control output; invalidates cache line on error
  - **relationships** — **SOURCES** → neorv32_cache_memory_inst.inv_i
  - **evidence** — cache_o.cmd_inv <= '1' in S_DOWNLOAD_DONE when ctrl.buf_err = '1'; port map inv_i => cache_o.cmd_inv.

**`cache_o.cmd_new`** — neorv32_cache · `std_ulogic`
  - **functionality** — Asserted during block-download request (S_DOWNLOAD_REQ) to signal the memory instance that a new cache line will be written, forwarded to new_i.
  - **roles** — control output; starts cache line fill
  - **relationships** — **SOURCES** → neorv32_cache_memory_inst.new_i
  - **evidence** — cache_o.cmd_new <= '1' in S_DOWNLOAD_REQ; port map new_i => cache_o.cmd_new.

**`cache_o.data`** — neorv32_cache · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Holds write data either from the host or from bus responses during downloads and forwards it to the cache memory write-data input.
  - **roles** — write data buffer; forwards to memory
  - **relationships** — **DERIVES_FROM** → host_req_i.data, bus_rsp_i.data; **SOURCES** → neorv32_cache_memory_inst.wdata_i
  - **evidence** — cache_o.data <= host_req_i.data default; cache_o.data <= bus_rsp_i.data in S_DOWNLOAD_RSP; port map wdata_i => cache_o.data.

**`cache_o.we`** — neorv32_cache · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Carries the byte-enable mask for writes: set from host_req_i.ben for host writes and to all-ones during downloads; forwarded to the cache memory we_i.
  - **roles** — write mask; drives memory write lanes
  - **relationships** — **DERIVES_FROM** → host_req_i.ben; **SOURCES** → neorv32_cache_memory_inst.we_i
  - **evidence** — cache_o.we <= host_req_i.ben for host write path; cache_o.we <= (others => '1') in S_DOWNLOAD_RSP; port map we_i => cache_o.we.

**`ctrl`** — neorv32_cache · `ctrl_t`
  - **functionality** — Holds the FSM state and buffered request/address fields across clock edges; updated from ctrl_nxt on rising clock and cleared on reset.
  - **roles** — state holder; captures next-state fields; pipeline register
  - **relationships** — **CAPTURES** → ctrl_nxt
  - **evidence** — clked process ctrl_engine_sync: on rising_edge(clk_i) ctrl <= ctrl_nxt; reset branch assigns ctrl fields.

**`ctrl.buf_dir`** — neorv32_cache · `std_ulogic`
  - **functionality** — Latched qualifier indicating that the current request must be directly forwarded to the bus (bypassing cache) and used to select the direct-response path.
  - **roles** — direct-forward qualifier; gates direct bus path
  - **relationships** — **CAPTURES** → ctrl_nxt.buf_dir; **GATES** → bus_req_o.stb, ctrl_nxt.state
  - **evidence** — ctrl_nxt.buf_dir <= '1' in S_IDLE when address/amo/debug conditions; S_LOOKUP tests ctrl.buf_dir to start direct bus transaction.

**`ctrl.buf_err`** — neorv32_cache · `std_ulogic`
  - **functionality** — Accumulates transfer errors across downloads (ORed with bus_rsp_i.err) and, when set at download completion, causes invalidation and a host error response.
  - **roles** — latched error flag; drives invalidate and error response
  - **relationships** — **CAPTURES** → ctrl_nxt.buf_err; **GATES** → cache_o.cmd_inv, host_rsp_o.err, host_rsp_o.ack
  - **evidence** — ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err in S_DOWNLOAD_RSP; S_DOWNLOAD_DONE checks ctrl.buf_err to invalidate and set host_rsp_o.err.

**`ctrl.buf_req`** — neorv32_cache · `std_ulogic`
  - **functionality** — Latched request indicator held across cycles; set by host_req_i.stb and used to enter the lookup state when present.
  - **roles** — latched request flag; gates FSM entry
  - **relationships** — **CAPTURES** → ctrl_nxt.buf_req; **GATES** → ctrl_nxt.state
  - **evidence** — ctrl_nxt.buf_req <= ctrl.buf_req or host_req_i.stb; S_IDLE checks ctrl.buf_req to go to S_LOOKUP.

**`ctrl.idx`** — neorv32_cache · `std_ulogic_vector(index_size_c-1 downto 0)`
  - **functionality** — Holds the extracted index bits captured during lookup and supplies index bits when assembling addresses for downloads.
  - **roles** — stored index; addresses cache block
  - **relationships** — **CAPTURES** → ctrl_nxt.idx; **SOURCES** → bus_req_o.addr, cache_o.addr
  - **evidence** — ctrl_nxt.idx <= host_req_i.addr((offset_size_c+2+index_size_c)-1 downto offset_size_c+2) in S_LOOKUP; used in DOWNLOAD_REQ.

**`ctrl.ofs`** — neorv32_cache · `std_ulogic_vector(offset_size_c-1 downto 0)`
  - **functionality** — Holds the current word offset within a cache block during downloads, is incremented on bus_rsp_i.ack and used to form addresses until download completion.
  - **roles** — download offset counter; controls download sequence
  - **relationships** — **CAPTURES** → ctrl_nxt.ofs; **SOURCES** → bus_req_o.addr, cache_o.addr; **CONSTRAINS** → ctrl_nxt.state
  - **evidence** — ctrl_nxt.ofs <= std_ulogic_vector(unsigned(ctrl.ofs) + 1) on bus_rsp_i.ack in S_DOWNLOAD_RSP; and_reduce_f(ctrl.ofs) used to decide S_DOWNLOAD_DONE.

**`ctrl.state`** — neorv32_cache · `state_t`
  - **functionality** — Holds the current controller state across cycles and is used as the case selector in ctrl_engine_comb to choose outputs and next-state assignments.
  - **roles** — current state (register); selects behavior; governs outputs
  - **relationships** — **CAPTURES** → ctrl_nxt.state; **SELECTS** → cache_o.cmd_clr, cache_o.cmd_inv, cache_o.cmd_new, cache_o.addr, cache_o.we, cache_o.data, host_rsp_o, bus_req_o, ctrl_nxt.state
  - **evidence** — case ctrl.state is ... in ctrl_engine_comb assigns cache_o.*, host_rsp_o, bus_req_o and ctrl_nxt.state per state.

**`ctrl.tag`** — neorv32_cache · `std_ulogic_vector(tag_size_c-1 downto 0)`
  - **functionality** — Holds the extracted tag bits captured during lookup and supplies tag bits when forming bus and cache addresses during downloads.
  - **roles** — stored tag; provides download address bits
  - **relationships** — **CAPTURES** → ctrl_nxt.tag; **SOURCES** → bus_req_o.addr, cache_o.addr
  - **evidence** — ctrl_nxt.tag <= host_req_i.addr(31 downto 32-tag_size_c) in S_LOOKUP; ctrl.tag is used to form addresses in S_DOWNLOAD_REQ.

**`ctrl_nxt`** — neorv32_cache · `ctrl_t`
  - **functionality** — Holds combinational next-state and next control values computed from current ctrl, host_req_i, cache_i and bus_rsp_i; captured into ctrl on the clock edge.
  - **roles** — next-state aggregator; combinational driver for ctrl register
  - **relationships** — **DERIVES_FROM** → ctrl, host_req_i, cache_i, bus_rsp_i; **SOURCES** → ctrl
  - **evidence** — ctrl_engine_comb computes ctrl_nxt.* from ctrl, host_req_i, cache_i, bus_rsp_i; ctrl <= ctrl_nxt on rising edge.

**`ctrl_nxt.buf_dir`** — neorv32_cache · `std_ulogic`
  - **functionality** — Combinationally derived from host request address range, host_req_i.amo or host_req_i.debug in S_IDLE and captured into ctrl.buf_dir for next cycles.
  - **roles** — next direct-qualifier; drives direct forwarding decision
  - **relationships** — **DERIVES_FROM** → host_req_i.addr, host_req_i.amo, host_req_i.debug; **SOURCES** → ctrl
  - **evidence** — S_IDLE sets ctrl_nxt.buf_dir <= '1' when address range/amo/debug conditions hold; ctrl captures ctrl_nxt.

**`ctrl_nxt.buf_err`** — neorv32_cache · `std_ulogic`
  - **functionality** — Combines the existing buffered error with bus_rsp_i.err during downloads and is captured into ctrl.buf_err.
  - **roles** — next error flag; propagates download errors
  - **relationships** — **DERIVES_FROM** → ctrl.buf_err, bus_rsp_i.err; **SOURCES** → ctrl
  - **evidence** — ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err in S_DOWNLOAD_RSP; captured by ctrl_engine_sync.

**`ctrl_nxt.buf_req`** — neorv32_cache · `std_ulogic`
  - **functionality** — Combinational next value for buf_req derived from the current buf_req or host_req_i.stb and later captured into ctrl.buf_req.
  - **roles** — next buffer request; input to ctrl register
  - **relationships** — **DERIVES_FROM** → ctrl.buf_req, host_req_i.stb; **SOURCES** → ctrl
  - **evidence** — ctrl_nxt.buf_req <= ctrl.buf_req or host_req_i.stb in ctrl_engine_comb; captured by ctrl_engine_sync.

**`ctrl_nxt.buf_sync`** — neorv32_cache · `std_ulogic`
  - **functionality** — Combinationally set from ctrl.buf_sync or host_req_i.fence and then captured into ctrl.buf_sync.
  - **roles** — next fence flag; propagated to ctrl
  - **relationships** — **DERIVES_FROM** → ctrl.buf_sync, host_req_i.fence; **SOURCES** → ctrl
  - **evidence** — ctrl_nxt.buf_sync <= ctrl.buf_sync or host_req_i.fence in ctrl_engine_comb; captured on rising edge.

**`ctrl_nxt.idx`** — neorv32_cache · `std_ulogic_vector(index_size_c-1 downto 0)`
  - **functionality** — Combinationally loaded from host_req_i.addr slices during lookup and captured into ctrl.idx for subsequent download address formation.
  - **roles** — next index; feeds download address assembly
  - **relationships** — **DERIVES_FROM** → host_req_i.addr; **SOURCES** → ctrl
  - **evidence** — ctrl_nxt.idx <= host_req_i.addr((offset_size_c+2+index_size_c)-1 downto offset_size_c+2) in S_LOOKUP; captured at clock.

**`ctrl_nxt.ofs`** — neorv32_cache · `std_ulogic_vector(offset_size_c-1 downto 0)`
  - **functionality** — Set combinationally to zero in lookup, incremented in DOWNLOAD_RSP when bus_rsp_i.ack='1', and captured into ctrl.ofs to step through block words.
  - **roles** — next offset; controls download progress
  - **relationships** — **DERIVES_FROM** → ctrl.ofs, bus_rsp_i.ack; **SOURCES** → ctrl
  - **evidence** — ctrl_nxt.ofs <= (others => '0') in S_LOOKUP; ctrl_nxt.ofs <= std_ulogic_vector(unsigned(ctrl.ofs) + 1) when bus_rsp_i.ack in S_DOWNLOAD_RSP.

**`ctrl_nxt.state`** — neorv32_cache · `state_t`
  - **functionality** — Computed from current state, host request fields, cache hit and bus responses inside the comb process and then captured into ctrl.state on clock edge.
  - **roles** — next-state value; combinationally derived
  - **relationships** — **DERIVES_FROM** → ctrl.state, host_req_i.fence, host_req_i.stb, cache_i.sta_hit, bus_rsp_i.ack, ctrl.buf_dir, ctrl.buf_sync; **SOURCES** → ctrl
  - **evidence** — case ctrl.state is ... assigns ctrl_nxt.state based on host_req_i, cache_i.sta_hit and bus_rsp_i.ack in ctrl_engine_comb.

**`ctrl_nxt.tag`** — neorv32_cache · `std_ulogic_vector(tag_size_c-1 downto 0)`
  - **functionality** — Combinationally loaded from host_req_i.addr during lookup and then captured into ctrl.tag for use during downloads.
  - **roles** — next tag; feeds download address assembly
  - **relationships** — **DERIVES_FROM** → host_req_i.addr; **SOURCES** → ctrl
  - **evidence** — ctrl_nxt.tag <= host_req_i.addr(31 downto 32-tag_size_c) in S_LOOKUP; captured by ctrl_engine_sync.

**`acc_adr`** — neorv32_cache_memory · `std_ulogic_vector((index_size_c+offset_size_c)-1 downto 0)`
  - **functionality** — Is formed by concatenating acc_idx and acc_off (acc_idx & acc_off) and is used to index the byte-addressable data memories for reads and writes.
  - **roles** — combined address for data arrays; selects data memory entries
  - **relationships** — **AGGREGATES** → acc_idx, acc_off; **SELECTS** → data_mem_b0, data_mem_b1, data_mem_b2, data_mem_b3
  - **evidence** — concurrent: acc_adr <= acc_idx & acc_off; data_memory uses data_mem_bX(to_integer(unsigned(acc_adr))) for reads/writes.

**`acc_idx`** — neorv32_cache_memory · `std_ulogic_vector(index_size_c-1 downto 0)`
  - **functionality** — Carries index bits from addr_i, selects entries in valid_mem and tag_mem via to_integer(unsigned(acc_idx)), and forms part of acc_adr through concatenation.
  - **roles** — carries index bits; selects memory entries; feeds acc_adr formation
  - **relationships** — **CARRIES** → addr_i; **SELECTS** → valid_mem, tag_mem; **SOURCES** → acc_adr
  - **evidence** — concurrent: acc_idx <= addr_i(...); used as to_integer(unsigned(acc_idx)) indexing valid_mem and tag_mem; acc_adr <= acc_idx & acc_off.

**`acc_off`** — neorv32_cache_memory · `std_ulogic_vector(offset_size_c-1 downto 0)`
  - **functionality** — Carries block offset bits from addr_i and participates in acc_adr concatenation, contributing to the byte address used to index the data memories.
  - **roles** — carries offset bits; contributes to data memory address
  - **relationships** — **CARRIES** → addr_i; **SOURCES** → acc_adr
  - **evidence** — concurrent: acc_off <= addr_i(2+(offset_size_c-1) downto 2); acc_adr <= acc_idx & acc_off.

**`acc_tag`** — neorv32_cache_memory · `std_ulogic_vector(tag_size_c-1 downto 0)`
  - **functionality** — Carries the tag slice extracted from addr_i, is forwarded into tag_mem when new_i writes occur, and is compared with tag_mem_rd for the hit decision.
  - **roles** — carries tag bits; source for tag writes and comparator input
  - **relationships** — **CARRIES** → addr_i; **SOURCES** → tag_mem; **CONSTRAINS** → hit_o
  - **evidence** — concurrent: acc_tag <= addr_i(31 downto 31-(tag_size_c-1)); used by tag_memory (tag_mem <= acc_tag) and by hit_o comparator.

**`data_mem_b0`** — neorv32_cache_memory · `data_mem_t`
  - **functionality** — At the clock edge, writes wdata_i(7 downto 0) into the indexed byte when we_i(0) is '1', and supplies that byte to rdata_o(7 downto 0) on reads.
  - **roles** — stores byte 0 of data memory; provides low byte for read output
  - **relationships** — **CAPTURES** → wdata_i; **SOURCES** → rdata_o
  - **evidence** — data_memory: if (we_i(0)='1') then data_mem_b0(to_integer(unsigned(acc_adr))) <= wdata_i(7 downto 0); rdata_o(7 downto 0) <= data_mem_b0(...).

**`data_mem_b1`** — neorv32_cache_memory · `data_mem_t`
  - **functionality** — At the clock edge, writes wdata_i(15 downto 8) into the indexed byte when we_i(1) is '1', and supplies that byte to rdata_o(15 downto 8) on reads.
  - **roles** — stores byte 1 of data memory; provides second byte for read output
  - **relationships** — **CAPTURES** → wdata_i; **SOURCES** → rdata_o
  - **evidence** — data_memory: if (we_i(1)='1') then data_mem_b1(to_integer(unsigned(acc_adr))) <= wdata_i(15 downto 8); rdata_o(15 downto 8) <= data_mem_b1(...).

**`data_mem_b2`** — neorv32_cache_memory · `data_mem_t`
  - **functionality** — At the clock edge, writes wdata_i(23 downto 16) into the indexed byte when we_i(2) is '1', and supplies that byte to rdata_o(23 downto 16) on reads.
  - **roles** — stores byte 2 of data memory; provides third byte for read output
  - **relationships** — **CAPTURES** → wdata_i; **SOURCES** → rdata_o
  - **evidence** — data_memory: if (we_i(2)='1') then data_mem_b2(to_integer(unsigned(acc_adr))) <= wdata_i(23 downto 16); rdata_o(23 downto 16) <= data_mem_b2(...).

**`data_mem_b3`** — neorv32_cache_memory · `data_mem_t`
  - **functionality** — At the clock edge, writes wdata_i(31 downto 24) into the indexed byte when we_i(3) is '1', and supplies that byte to rdata_o(31 downto 24) on reads.
  - **roles** — stores byte 3 of data memory; provides high byte for read output
  - **relationships** — **CAPTURES** → wdata_i; **SOURCES** → rdata_o
  - **evidence** — data_memory: if (we_i(3)='1') then data_mem_b3(to_integer(unsigned(acc_adr))) <= wdata_i(31 downto 24); rdata_o(31 downto 24) <= data_mem_b3(...).

**`tag_mem`** — neorv32_cache_memory · `tag_mem_t`
  - **functionality** — Stores acc_tag into the indexed entry on new_i at the clock edge and provides entries to tag_mem_rd for hit comparison.
  - **roles** — holds per-block tags; updated on new_i events
  - **relationships** — **CAPTURES** → acc_tag; **SOURCES** → tag_mem_rd
  - **evidence** — tag_memory process: if (new_i = '1') then tag_mem(to_integer(unsigned(acc_idx))) <= acc_tag; tag_mem_rd <= tag_mem(to_integer(unsigned(acc_idx))).

**`tag_mem_rd`** — neorv32_cache_memory · `std_ulogic_vector(tag_size_c-1 downto 0)`
  - **functionality** — Captures the tag_mem entry at the selected index on the clock edge and supplies the sampled tag to the hit comparator (compared with acc_tag).
  - **roles** — sampled tag field; constrains hit comparator
  - **relationships** — **CAPTURES** → tag_mem; **CONSTRAINS** → hit_o
  - **evidence** — tag_memory: tag_mem_rd <= tag_mem(to_integer(unsigned(acc_idx))); hit_o compares tag_mem_rd to acc_tag.

**`valid_mem`** — neorv32_cache_memory · `std_ulogic_vector(NUM_BLOCKS-1 downto 0)`
  - **functionality** — Holds one validity bit per block and is updated on reset, on clr_i (all cleared), inv_i (indexed clear) and new_i (indexed set); its indexed value is read into valid_mem_rd.
  - **roles** — holds per-block validity; provides validity to hit logic
  - **relationships** — **SOURCES** → valid_mem_rd
  - **evidence** — status_memory assigns valid_mem in reset/branches and then sets valid_mem_rd <= valid_mem(to_integer(unsigned(acc_idx))).

**`valid_mem_rd`** — neorv32_cache_memory · `std_ulogic`
  - **functionality** — Captures the selected valid_mem bit at the clock edge (and reset), and supplies the validity test used by the hit comparator that drives hit_o.
  - **roles** — sampled valid bit; constrains hit decision
  - **relationships** — **CAPTURES** → valid_mem; **CONSTRAINS** → hit_o
  - **evidence** — status_memory: valid_mem_rd <= valid_mem(to_integer(unsigned(acc_idx))); hit_o uses (valid_mem_rd = '1') in its when guard.


## neorv32_cpu  (101 non-assets)

### ports

**`clk_i`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Supplies the clock to instantiated submodules; it sequences their synchronous processes by connecting to each instance clk_i port.
  - **roles** — global clock; timing source for instances
  - **relationships** — **SEQUENCES** → neorv32_cpu_frontend_inst.clk_i, neorv32_cpu_control_inst.clk_i, neorv32_cpu_counters_inst.clk_i, neorv32_cpu_regfile_inst.clk_i, neorv32_cpu_alu_inst.clk_i, neorv32_cpu_lsu_inst.clk_i, neorv32_cpu_pmp_inst.clk_i, neorv32_cpu_icc_inst.clk_i
  - **evidence** — clk_i connected in many port maps (e.g. frontend, control, alu, lsu) via port map lines.

**`dbus_req_o`** — neorv32_cpu · `bus_req_t`
  - **functionality** — Exports the data-bus request record to the system; this record is driven by the LSU instance's dbus_req_o port.
  - **roles** — data bus export; forwarded from LSU instance
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.addr`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the address field for data-bus requests as provided by the LSU instance.
  - **roles** — data address output; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.addr
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.amo`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs AMO indicator for data-bus accesses; forwarded from the LSU instance's request record.
  - **roles** — AMO flag output; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.amo
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.amoop`** — neorv32_cpu · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs the AMO operation code field for data-bus requests; carried from the LSU instance.
  - **roles** — AMO opcode output; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.amoop
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.ben`** — neorv32_cpu · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs the byte-enable field for data-bus accesses; forwarded unchanged from the LSU instance.
  - **roles** — byte-enable output; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.ben
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.data`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the data payload for data-bus requests; field is carried from the LSU instance.
  - **roles** — data payload output; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.data
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.debug`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs debug indicator for data-bus requests, forwarded from the LSU instance's request record.
  - **roles** — debug flag output; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.debug
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.fence`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs fence indicator for data-bus operations; the field is carried from the LSU instance's request record.
  - **roles** — fence flag output; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.fence
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.lock`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs the lock indicator for data-bus requests and forwards the field from the LSU instance.
  - **roles** — lock flag output; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.lock
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.priv`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs the privilege indicator for data-bus accesses; forwarded from the LSU instance.
  - **roles** — privilege flag output; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.priv
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.rw`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs read/write indicator for the data-bus request, forwarded from the LSU instance.
  - **roles** — read/write flag; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.rw
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.src`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs the source field of data-bus requests as provided by the LSU instance.
  - **roles** — request source output; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.src
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_req_o.stb`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs the strobe for data-bus requests, forwarded from the LSU instance's request record.
  - **roles** — request strobe; forwarded from LSU
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_lsu_inst.dbus_req_o.stb
  - **evidence** — lsu port map: dbus_req_o => dbus_req_o.

**`dbus_rsp_i`** — neorv32_cpu · `bus_rsp_t`
  - **functionality** — Receives the data-bus response record from outside and forwards it into the LSU instance's dbus_rsp_i port for consumption.
  - **roles** — data bus response input; forwarded into LSU
  - **relationships** — **SOURCES** → neorv32_cpu_lsu_inst.dbus_rsp_i
  - **evidence** — lsu port map: dbus_rsp_i => dbus_rsp_i.

**`dbus_rsp_i.ack`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Receives the ack bit of data-bus responses and forwards it into the LSU instance's response port.
  - **roles** — response ack input; forwarded into LSU
  - **relationships** — **SOURCES** → neorv32_cpu_lsu_inst.dbus_rsp_i.ack
  - **evidence** — lsu port map: dbus_rsp_i => dbus_rsp_i.

**`dbus_rsp_i.data`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Receives 32-bit response data from the data bus and forwards it to the LSU instance for use.
  - **roles** — response data input; forwarded into LSU
  - **relationships** — **SOURCES** → neorv32_cpu_lsu_inst.dbus_rsp_i.data
  - **evidence** — lsu port map: dbus_rsp_i => dbus_rsp_i.

**`dbus_rsp_i.err`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Receives the error flag for data-bus responses and forwards it into the LSU instance.
  - **roles** — response error input; forwarded into LSU
  - **relationships** — **SOURCES** → neorv32_cpu_lsu_inst.dbus_rsp_i.err
  - **evidence** — lsu port map: dbus_rsp_i => dbus_rsp_i.

**`ibus_req_o`** — neorv32_cpu · `bus_req_t`
  - **functionality** — Exports the instruction-bus request record to the system; it is driven by the frontend instance's ibus_req_o port.
  - **roles** — instruction bus export; forwarded from frontend instance
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o
  - **evidence** — port map in frontend: ibus_req_o => ibus_req_o.

**`ibus_req_o.addr`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the instruction bus address field; the field is carried from the frontend instance's ibus_req_o.addr through the entity boundary.
  - **roles** — instruction address output; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.addr
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_req_o.amo`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs AMO flag for instruction-side atomic operations, forwarded from the frontend instance request record.
  - **roles** — AMO flag output; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.amo
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_req_o.amoop`** — neorv32_cpu · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs the AMO operation code field from the frontend request record to external bus.
  - **roles** — AMO opcode output; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.amoop
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_req_o.ben`** — neorv32_cpu · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Outputs the instruction bus byte-enable field from the frontend instance to the external bus.
  - **roles** — instruction byte-enable; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.ben
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_req_o.data`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the instruction bus data field when applicable; forwarded from the frontend instance's request record.
  - **roles** — instruction bus data output; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.data
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_req_o.debug`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs instruction bus debug indicator; forwarded from the frontend instance's request record.
  - **roles** — debug flag output; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.debug
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_req_o.fence`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs the fence indicator for instruction requests, forwarded from the frontend instance's request record.
  - **roles** — fence flag output; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.fence
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_req_o.lock`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs the lock indicator for instruction bus access; carried from the frontend instance.
  - **roles** — lock flag output; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.lock
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_req_o.priv`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs the privilege indicator for instruction bus requests; forwarded unchanged from the frontend instance.
  - **roles** — privilege flag output; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.priv
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_req_o.rw`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs the read/write indication for instruction bus accesses; the bit is carried from the frontend instance.
  - **roles** — read/write flag; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.rw
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_req_o.src`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs the 'src' field of the instruction bus request as provided by the frontend instance.
  - **roles** — request source output; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.src
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_req_o.stb`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs a strobe signal for the instruction bus requests; forwarded from the frontend instance's request port.
  - **roles** — request strobe; forwarded from frontend
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_frontend_inst.ibus_req_o.stb
  - **evidence** — frontend port map: ibus_req_o => ibus_req_o.

**`ibus_rsp_i`** — neorv32_cpu · `bus_rsp_t`
  - **functionality** — Receives the instruction-bus response record from external bus and supplies it to the frontend instance via its ibus_rsp_i port.
  - **roles** — instruction bus response input; forwarded into frontend instance
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ibus_rsp_i
  - **evidence** — frontend port map: ibus_rsp_i => ibus_rsp_i.

**`ibus_rsp_i.ack`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Receives ack for instruction-bus responses and forwards it into the frontend instance's response port.
  - **roles** — response ack input; forwarded into frontend
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ibus_rsp_i.ack
  - **evidence** — frontend port map: ibus_rsp_i => ibus_rsp_i.

**`ibus_rsp_i.data`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Receives response data from the instruction bus and forwards the 32-bit data field to the frontend instance.
  - **roles** — response data input; forwarded into frontend
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ibus_rsp_i.data
  - **evidence** — frontend port map: ibus_rsp_i => ibus_rsp_i.

**`ibus_rsp_i.err`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Receives error indication for instruction-bus responses and forwards it to the frontend instance for handling.
  - **roles** — response error input; forwarded into frontend
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ibus_rsp_i.err
  - **evidence** — frontend port map: ibus_rsp_i => ibus_rsp_i.

**`icc_rx_i`** — neorv32_cpu · `icc_t`
  - **functionality** — Accepts the external ICC receive record; it is passed into the ICC instance's icc_rx_i port for consumption.
  - **roles** — imported ICC receive; forwarded into ICC instance
  - **relationships** — **SOURCES** → neorv32_cpu_icc_inst.icc_rx_i
  - **evidence** — icc instance port map: icc_rx_i => icc_rx_i.

**`icc_rx_i.ack`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Receives the ICC acknowledge input and forwards it into the ICC instance via its icc_rx_i port.
  - **roles** — imported ICC ack; forwarded into ICC instance
  - **relationships** — **SOURCES** → neorv32_cpu_icc_inst.icc_rx_i.ack
  - **evidence** — icc instance port map: icc_rx_i => icc_rx_i.

**`icc_rx_i.dat`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Receives the ICC data word and feeds it into the ICC instance through its icc_rx_i port.
  - **roles** — imported ICC data; forwarded into ICC instance
  - **relationships** — **SOURCES** → neorv32_cpu_icc_inst.icc_rx_i.dat
  - **evidence** — icc instance port map: icc_rx_i => icc_rx_i.

**`icc_rx_i.rdy`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Receives the ICC ready flag from outside and supplies it to the ICC instance's icc_rx_i port.
  - **roles** — imported ICC ready; forwarded into ICC instance
  - **relationships** — **SOURCES** → neorv32_cpu_icc_inst.icc_rx_i.rdy
  - **evidence** — icc instance port map: icc_rx_i => icc_rx_i.

**`icc_tx_o`** — neorv32_cpu · `icc_t`
  - **functionality** — Exposes the ICC transmit record to the outside; the record is sourced from the ICC instance when enabled or driven to a constant when ICC is disabled.
  - **roles** — exported ICC transmit; forwarded from ICC instance
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_icc_inst.icc_tx_o
  - **evidence** — icc instance port map: icc_tx_o => icc_tx_o; in disabled generate: icc_tx_o <= icc_terminate_c.

**`icc_tx_o.ack`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs the ICC acknowledge flag to external world; the bit is provided by the ICC instance via the port map when enabled.
  - **roles** — exported ICC ack; forwarded from ICC instance
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_icc_inst.icc_tx_o.ack
  - **evidence** — icc instance port map: icc_tx_o => icc_tx_o.

**`icc_tx_o.dat`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Outputs the ICC data word to external connection; the vector is forwarded from the ICC instance when enabled or set in disabled generate.
  - **roles** — exported ICC data; forwarded from ICC instance
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_icc_inst.icc_tx_o.dat
  - **evidence** — icc instance port map: icc_tx_o => icc_tx_o; icc_disabled assignment sets icc_tx_o.

**`icc_tx_o.rdy`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Outputs the ICC ready flag to the outside; the bit is forwarded from the ICC instance when present otherwise assigned in disabled generate.
  - **roles** — exported ICC ready; forwarded from ICC instance
  - **relationships** — **EXPORTS** → _(none)_; **CARRIES** → neorv32_cpu_icc_inst.icc_tx_o.rdy
  - **evidence** — port map in icc instance: icc_tx_o => icc_tx_o; assignment in icc_disabled generate.

**`rstn_i`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Provides active-low reset to instantiated submodules; it is forwarded into each instance rstn_i port to initialize/reset their state.
  - **roles** — global reset; timing/reset source for instances
  - **relationships** — **SEQUENCES** → neorv32_cpu_frontend_inst.rstn_i, neorv32_cpu_control_inst.rstn_i, neorv32_cpu_counters_inst.rstn_i, neorv32_cpu_regfile_inst.rstn_i, neorv32_cpu_alu_inst.rstn_i, neorv32_cpu_lsu_inst.rstn_i, neorv32_cpu_pmp_inst.rstn_i, neorv32_cpu_icc_inst.rstn_i
  - **evidence** — rstn_i connected in many port maps (e.g. frontend, control, alu, lsu) via port map lines.

### signals

**`alu_cmp`** — neorv32_cpu · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Carries the ALU compare result (two-bit) from the ALU instance and supplies it to the control unit where branch decisions are made.
  - **roles** — ALU compare result; forwarded to control
  - **relationships** — **CARRIES** → neorv32_cpu_alu_inst.cmp_o; **SOURCES** → neorv32_cpu_control_inst.alu_cmp_i
  - **evidence** — alu port map: cmp_o => alu_cmp; control port map: alu_cmp_i => alu_cmp.

**`alu_cp_done`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Receives the ALU coprocessor done/complete flag from the ALU instance and forwards it to the control unit (alu_cp_done_i) for sequencing control.
  - **roles** — ALU coprocessor done; forwarded to control
  - **relationships** — **CARRIES** → neorv32_cpu_alu_inst.done_o; **SOURCES** → neorv32_cpu_control_inst.alu_cp_done_i
  - **evidence** — alu port map: done_o => alu_cp_done; control port map: alu_cp_done_i => alu_cp_done.

**`ctrl`** — neorv32_cpu · `ctrl_bus_t`
  - **functionality** — Carries the control/control-status bus produced by the control instance and forwards its fields to frontend, regfile, ALU, LSU, PMP, counters and ICC where consumed.
  - **roles** — control bus carrier; holds forwarded control fields; exports control outputs to submodules
  - **relationships** — **CARRIES** → neorv32_cpu_control_inst.ctrl_o; **SOURCES** → neorv32_cpu_frontend_inst.ctrl_i, neorv32_cpu_counters_inst.ctrl_i, neorv32_cpu_regfile_inst.ctrl_i, neorv32_cpu_alu_inst.ctrl_i, neorv32_cpu_lsu_inst.ctrl_i, neorv32_cpu_pmp_inst.ctrl_i, neorv32_cpu_icc_inst.csr_we_i, neorv32_cpu_icc_inst.csr_re_i, neorv32_cpu_icc_inst.csr_addr_i, neorv32_cpu_icc_inst.csr_wdata_i
  - **evidence** — control port map: ctrl_o => ctrl; many instances map ctrl_i => ctrl; icc maps specific ctrl fields.

**`ctrl.alu_cp_alu`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the ALU coprocessor select bit (ALU path) from control to the ALU instance within the ctrl bus.
  - **roles** — ALU coprocessor select; forwarded to ALU
  - **relationships** — **SOURCES** → neorv32_cpu_alu_inst.ctrl_i
  - **evidence** — alu port map: ctrl_i => ctrl.

**`ctrl.alu_cp_cfu`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the CFU coprocessor selection bit from control to ALU/CFU-consumers via the ctrl record.
  - **roles** — CFU select; forwarded to ALU/CFU
  - **relationships** — **SOURCES** → neorv32_cpu_alu_inst.ctrl_i
  - **evidence** — alu port map: ctrl_i => ctrl.

**`ctrl.alu_cp_fpu`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the FPU coprocessor select bit from control inside the ctrl record to ALU/FPU consumers.
  - **roles** — FPU select; forwarded to ALU/FPU
  - **relationships** — **SOURCES** → neorv32_cpu_alu_inst.ctrl_i
  - **evidence** — alu port map: ctrl_i => ctrl.

**`ctrl.alu_imm`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the immediate operand field from control inside ctrl and supplies it to the ALU instance for operations using immediates.
  - **roles** — ALU immediate field; forwarded to ALU
  - **relationships** — **SOURCES** → neorv32_cpu_alu_inst.ctrl_i
  - **evidence** — alu port map: ctrl_i => ctrl.

**`ctrl.alu_op`** — neorv32_cpu · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Carries the ALU operation code field from the control instance inside ctrl and forwards it to the ALU instance via its ctrl_i input.
  - **roles** — ALU opcode; forwarded to ALU
  - **relationships** — **SOURCES** → neorv32_cpu_alu_inst.ctrl_i
  - **evidence** — alu port map: ctrl_i => ctrl.

**`ctrl.alu_opa_mux`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the operand-A multiplexer control from control to the ALU instance inside the ctrl record.
  - **roles** — ALU operand selector; forwarded to ALU
  - **relationships** — **SOURCES** → neorv32_cpu_alu_inst.ctrl_i
  - **evidence** — alu port map: ctrl_i => ctrl.

**`ctrl.alu_opb_mux`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the operand-B multiplexer control from the control instance to the ALU via ctrl.
  - **roles** — ALU operand selector; forwarded to ALU
  - **relationships** — **SOURCES** → neorv32_cpu_alu_inst.ctrl_i
  - **evidence** — alu port map: ctrl_i => ctrl.

**`ctrl.alu_sub`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the ALU subtract control bit from the control instance to the ALU via the ctrl bus.
  - **roles** — ALU subtract control; forwarded to ALU
  - **relationships** — **SOURCES** → neorv32_cpu_alu_inst.ctrl_i
  - **evidence** — alu port map: ctrl_i => ctrl.

**`ctrl.alu_unsigned`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the ALU unsigned arithmetic flag from control to the ALU instance via the ctrl record for signed/unsigned decisions.
  - **roles** — ALU unsigned flag; forwarded to ALU
  - **relationships** — **SOURCES** → neorv32_cpu_alu_inst.ctrl_i
  - **evidence** — alu port map: ctrl_i => ctrl.

**`ctrl.cnt_event`** — neorv32_cpu · `std_ulogic_vector(11 downto 0)`
  - **functionality** — Carries the event selector for counters from control and forwards it to the counters instance via the ctrl bus.
  - **roles** — counter event selector; forwarded to counters
  - **relationships** — **SOURCES** → neorv32_cpu_counters_inst.ctrl_i
  - **evidence** — counters port map: ctrl_i => ctrl.

**`ctrl.cnt_halt`** — neorv32_cpu · `std_ulogic_vector(15 downto 0)`
  - **functionality** — Carries counter halt mask field from control via the ctrl record to the counters instance when present.
  - **roles** — counter halt control; forwarded to counters
  - **relationships** — **SOURCES** → neorv32_cpu_counters_inst.ctrl_i
  - **evidence** — counters port map: ctrl_i => ctrl.

**`ctrl.cpu_debug`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the debug-mode indicator from the control instance and forwards it to modules (frontend, regfile, etc.) via the ctrl record.
  - **roles** — debug indicator; forwarded from control
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ctrl_i, neorv32_cpu_regfile_inst.ctrl_i
  - **evidence** — ctrl passed to frontend/regfile via port map: ctrl_i => ctrl.

**`ctrl.cpu_priv`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the CPU privilege level field from control and forwards it to LSU/PMP/other consumers that require privilege info via ctrl.
  - **roles** — privilege level field; forwarded to consumers
  - **relationships** — **SOURCES** → neorv32_cpu_lsu_inst.ctrl_i, neorv32_cpu_pmp_inst.ctrl_i
  - **evidence** — ctrl passed into LSU and PMP via ctrl_i => ctrl.

**`ctrl.cpu_sleep`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the CPU sleep control flag from control to any consumer that reads it via the ctrl record.
  - **roles** — sleep flag; forwarded from control
  - **relationships** — **SOURCES** → neorv32_cpu_control_inst.ctrl_o
  - **evidence** — ctrl produced by control.ctrl_o and distributed via ctrl_i mappings.

**`ctrl.cpu_trap`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the trap indicator from the control instance inside the ctrl record and is available to other modules via ctrl.
  - **roles** — trap indicator; forwarded from control
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ctrl_i, neorv32_cpu_regfile_inst.ctrl_i
  - **evidence** — ctrl passed to frontend/regfile via port maps.

**`ctrl.csr_addr`** — neorv32_cpu · `std_ulogic_vector(11 downto 0)`
  - **functionality** — Carries the CSR address field from control and supplies it to ICC (csr_addr_i) and other CSR consumers via ctrl.
  - **roles** — CSR address field; forwarded to ICC
  - **relationships** — **SOURCES** → neorv32_cpu_icc_inst.csr_addr_i
  - **evidence** — icc port map: csr_addr_i => ctrl.csr_addr.

**`ctrl.csr_re`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the CSR read-enable bit from control and supplies it to the ICC instance's csr_re_i port when ICC exists.
  - **roles** — CSR read enable; forwarded to ICC
  - **relationships** — **SOURCES** → neorv32_cpu_icc_inst.csr_re_i
  - **evidence** — icc port map: csr_re_i => ctrl.csr_re.

**`ctrl.csr_wdata`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries CSR write-data from control and forwards it into the ICC instance's csr_wdata_i port for CSR writes.
  - **roles** — CSR write data; forwarded to ICC
  - **relationships** — **SOURCES** → neorv32_cpu_icc_inst.csr_wdata_i
  - **evidence** — icc port map: csr_wdata_i => ctrl.csr_wdata.

**`ctrl.csr_we`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries CSR write-enable from the control instance and is delivered to the ICC instance's csr_we_i port (and other CSR consumers) to control CSR writes.
  - **roles** — CSR write enable; forwarded to ICC and CSR consumers
  - **relationships** — **SOURCES** → neorv32_cpu_icc_inst.csr_we_i, neorv32_cpu_control_inst.ctrl_o
  - **evidence** — icc port map: csr_we_i => ctrl.csr_we; ctrl is driven by control.ctrl_o.

**`ctrl.if_ack`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the frontend ack control bit from the control instance to the frontend module via the ctrl bus.
  - **roles** — frontend ack control; forwarded from control to frontend
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ctrl_i
  - **evidence** — ctrl passed to frontend via port map: ctrl_i => ctrl.

**`ctrl.if_fence`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the instruction-fetch fence control bit from the control instance through the ctrl bus into the frontend instance for consumption.
  - **roles** — frontend fence control; forwarded from control to frontend
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ctrl_i
  - **evidence** — ctrl is driven by control.ctrl_o and passed into frontend via ctrl_i => ctrl (port maps).

**`ctrl.if_reset`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the frontend reset control bit from control instance within the ctrl record to the frontend instance.
  - **roles** — frontend reset control; forwarded from control to frontend
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ctrl_i
  - **evidence** — ctrl passed to frontend via port map: ctrl_i => ctrl.

**`ctrl.ir_funct12`** — neorv32_cpu · `std_ulogic_vector(11 downto 0)`
  - **functionality** — Forwards the decoded funct12 immediate field from control to consumers via the ctrl bus.
  - **roles** — decoded funct12; forwarded to consumers
  - **relationships** — **SOURCES** → neorv32_cpu_alu_inst.ctrl_i
  - **evidence** — alu port map: ctrl_i => ctrl.

**`ctrl.ir_funct3`** — neorv32_cpu · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Carries the decoded funct3 field from control inside the ctrl record and forwards it to ALU/other consumers via ctrl.
  - **roles** — decoded opcode field; forwarded to consumers
  - **relationships** — **SOURCES** → neorv32_cpu_alu_inst.ctrl_i, neorv32_cpu_control_inst.ctrl_o
  - **evidence** — ctrl passed to ALU via ctrl_i => ctrl.

**`ctrl.ir_opcode`** — neorv32_cpu · `std_ulogic_vector(6 downto 0)`
  - **functionality** — Carries the decoded opcode field from control inside the ctrl record and forwards it to frontend/ALU as needed.
  - **roles** — opcode field; forwarded to consumers
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ctrl_i, neorv32_cpu_alu_inst.ctrl_i
  - **evidence** — ctrl passed to frontend and ALU via ctrl_i => ctrl.

**`ctrl.lsu_amo`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the atomic operation flag from control to the LSU instance via ctrl for atomic memory ops.
  - **roles** — LSU AMO control; forwarded to LSU
  - **relationships** — **SOURCES** → neorv32_cpu_lsu_inst.ctrl_i
  - **evidence** — lsu port map: ctrl_i => ctrl.

**`ctrl.lsu_fence`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards fence control for memory ops from control to the LSU instance via the ctrl record.
  - **roles** — LSU fence control; forwarded to LSU
  - **relationships** — **SOURCES** → neorv32_cpu_lsu_inst.ctrl_i
  - **evidence** — lsu port map: ctrl_i => ctrl.

**`ctrl.lsu_mo_we`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards memory-order write-enable control from the control unit into the LSU via the ctrl record.
  - **roles** — LSU memory-order control; forwarded to LSU
  - **relationships** — **SOURCES** → neorv32_cpu_lsu_inst.ctrl_i
  - **evidence** — lsu port map: ctrl_i => ctrl.

**`ctrl.lsu_priv`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the privilege level field from control into the LSU instance via the ctrl record to qualify memory accesses.
  - **roles** — LSU privilege field; forwarded to LSU
  - **relationships** — **SOURCES** → neorv32_cpu_lsu_inst.ctrl_i
  - **evidence** — lsu port map: ctrl_i => ctrl.

**`ctrl.lsu_req`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the LSU request enable/control bit from control to the LSU instance via ctrl for initiating memory operations.
  - **roles** — LSU request enable; forwarded to LSU
  - **relationships** — **SOURCES** → neorv32_cpu_lsu_inst.ctrl_i
  - **evidence** — lsu port map: ctrl_i => ctrl.

**`ctrl.lsu_rw`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the read/write control bit for the LSU from control to the LSU instance via ctrl.
  - **roles** — LSU read/write control; forwarded to LSU
  - **relationships** — **SOURCES** → neorv32_cpu_lsu_inst.ctrl_i
  - **evidence** — lsu port map: ctrl_i => ctrl.

**`ctrl.pc_cur`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the current PC field from control to frontend and other consumers via the ctrl record; forwarded unchanged from control instance.
  - **roles** — PC current field; forwarded to frontend/control consumers
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ctrl_i, neorv32_cpu_regfile_inst.ctrl_i
  - **evidence** — ctrl record passed to frontend and other modules via port map: ctrl_i => ctrl.

**`ctrl.pc_nxt`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the next-PC field from the control instance inside the ctrl record and forwards it to consumers via ctrl_i mappings.
  - **roles** — PC next field; forwarded from control
  - **relationships** — **SOURCES** → neorv32_cpu_frontend_inst.ctrl_i
  - **evidence** — ctrl passed into frontend via port map: ctrl_i => ctrl.

**`ctrl.pc_ret`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the PC return value produced by control; it is used in the rf_wdata selection expression to become a writeback source for the register file.
  - **roles** — PC return value; writeback source
  - **relationships** — **SOURCES** → rf_wdata; **SOURCES** → neorv32_cpu_frontend_inst.ctrl_i
  - **evidence** — rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret; ctrl passed to frontend via ctrl_i => ctrl.

**`ctrl.rf_rd`** — neorv32_cpu · `std_ulogic_vector(4 downto 0)`
  - **functionality** — Carries the destination register index from the control instance inside ctrl and supplies it to the regfile through ctrl_i for writes.
  - **roles** — rd index; forwarded to regfile
  - **relationships** — **SOURCES** → neorv32_cpu_regfile_inst.ctrl_i
  - **evidence** — regfile port map: ctrl_i => ctrl.

**`ctrl.rf_rs1`** — neorv32_cpu · `std_ulogic_vector(4 downto 0)`
  - **functionality** — Forwards the rs1 index field from the control instance through the ctrl bus into the regfile, which consumes it to select a register.
  - **roles** — rs1 index; forwarded to regfile
  - **relationships** — **SOURCES** → neorv32_cpu_regfile_inst.ctrl_i
  - **evidence** — regfile port map: ctrl_i => ctrl and regfile reads ctrl.rf_rs1 internally.

**`ctrl.rf_rs2`** — neorv32_cpu · `std_ulogic_vector(4 downto 0)`
  - **functionality** — Forwards the rs2 index field from the control instance to the regfile via the ctrl record for operand selection.
  - **roles** — rs2 index; forwarded to regfile
  - **relationships** — **SOURCES** → neorv32_cpu_regfile_inst.ctrl_i
  - **evidence** — regfile port map: ctrl_i => ctrl.

**`ctrl.rf_wb_en`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the register-file write-enable control bit from control instance inside ctrl and is consumed by the regfile via its ctrl_i input.
  - **roles** — register-file write-enable; forwarded from control to regfile
  - **relationships** — **SOURCES** → neorv32_cpu_regfile_inst.ctrl_i
  - **evidence** — regfile port map: ctrl_i => ctrl (control fields read by regfile).

**`ctrl.rf_zero_we`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Forwards the control bit that inhibits writes to x0 from the control instance to the regfile via the ctrl record.
  - **roles** — x0 write inhibit; forwarded to regfile
  - **relationships** — **SOURCES** → neorv32_cpu_regfile_inst.ctrl_i
  - **evidence** — regfile port map: ctrl_i => ctrl.

**`frontend`** — neorv32_cpu · `if_bus_t`
  - **functionality** — Carries the fetch-stage outputs (valid, instr, compr, fault, halted) from the frontend instance into this entity and supplies them to the control instance.
  - **roles** — frontend output bundle; forwarded to control instance
  - **relationships** — **CARRIES** → neorv32_cpu_frontend_inst.frontend_o; **SOURCES** → neorv32_cpu_control_inst.frontend_i
  - **evidence** — frontend port map: frontend_o => frontend; control port map: frontend_i => frontend.

**`frontend.compr`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the compression indicator from the frontend instance and forwards it to control via the frontend record.
  - **roles** — compression flag; forwarded from frontend to control
  - **relationships** — **CARRIES** → neorv32_cpu_frontend_inst.frontend_o.compr; **SOURCES** → neorv32_cpu_control_inst.frontend_i.compr
  - **evidence** — frontend port map and control port map: frontend_o => frontend; frontend_i => frontend.

**`frontend.fault`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the fetch fault indicator from the frontend instance into the control instance via the frontend bundle.
  - **roles** — fetch fault indicator; forwarded from frontend to control
  - **relationships** — **CARRIES** → neorv32_cpu_frontend_inst.frontend_o.fault; **SOURCES** → neorv32_cpu_control_inst.frontend_i.fault
  - **evidence** — frontend port map and control port map: frontend_o => frontend; frontend_i => frontend.

**`frontend.halted`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Carries the frontend halted indication from the frontend instance and forwards it to the control instance via the frontend record.
  - **roles** — frontend halted flag; forwarded from frontend to control
  - **relationships** — **CARRIES** → neorv32_cpu_frontend_inst.frontend_o.halted; **SOURCES** → neorv32_cpu_control_inst.frontend_i.halted
  - **evidence** — frontend port map and control port map: frontend_o => frontend; frontend_i => frontend.

**`frontend.instr`** — neorv32_cpu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the fetched 32-bit instruction from the frontend instance and forwards it to the control unit via the frontend record.
  - **roles** — fetched instruction; forwarded from frontend to control
  - **relationships** — **CARRIES** → neorv32_cpu_frontend_inst.frontend_o.instr; **SOURCES** → neorv32_cpu_control_inst.frontend_i.instr
  - **evidence** — frontend port map and control port map: frontend_o => frontend; frontend_i => frontend.

**`frontend.valid`** — neorv32_cpu · `std_ulogic`
  - **functionality** — Provides the valid flag from the frontend instance and forwards it to the control instance where it is consumed via frontend input.
  - **roles** — instruction valid flag; forwarded from frontend to control
  - **relationships** — **CARRIES** → neorv32_cpu_frontend_inst.frontend_o.valid; **SOURCES** → neorv32_cpu_control_inst.frontend_i.valid
  - **evidence** — frontend port map and control port map: frontend_o => frontend; frontend_i => frontend.

**`lsu_rdata`** — neorv32_cpu · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Carries read data produced by the LSU instance and is one of the inputs selected into rf_wdata for register writeback.
  - **roles** — LSU readback data; writeback source
  - **relationships** — **CARRIES** → neorv32_cpu_lsu_inst.rdata_o; **SOURCES** → rf_wdata
  - **evidence** — lsu port map: rdata_o => lsu_rdata; rf_wdata <= alu_res or lsu_rdata or csr_rdata or ctrl.pc_ret.

**`rs1`** — neorv32_cpu · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Receives rs1 data from the regfile instance and supplies it to the ALU and control instances as an operand or reference.
  - **roles** — operand A; forwarded from regfile to ALU/control
  - **relationships** — **CARRIES** → neorv32_cpu_regfile_inst.rs1_o; **SOURCES** → neorv32_cpu_alu_inst.rs1_i, neorv32_cpu_control_inst.rf_rs1_i
  - **evidence** — regfile port map: rs1_o => rs1; alu port map: rs1_i => rs1; control port map: rf_rs1_i => rs1.

**`rs2`** — neorv32_cpu · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Receives rs2 data from the regfile instance and supplies it to the ALU and LSU (as write data) via instance port connections.
  - **roles** — operand B / store data; forwarded from regfile to ALU/LSU
  - **relationships** — **CARRIES** → neorv32_cpu_regfile_inst.rs2_o; **SOURCES** → neorv32_cpu_alu_inst.rs2_i, neorv32_cpu_lsu_inst.wdata_i
  - **evidence** — regfile rs2_o => rs2; alu rs2_i => rs2; lsu wdata_i => rs2.

**`rs3`** — neorv32_cpu · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Carries rs3 data produced by the regfile and supplies it to the ALU instance (for three-operand ops) via port mapping.
  - **roles** — operand C; forwarded from regfile to ALU
  - **relationships** — **CARRIES** → neorv32_cpu_regfile_inst.rs3_o; **SOURCES** → neorv32_cpu_alu_inst.rs3_i
  - **evidence** — regfile port map: rs3_o => rs3; alu port map: rs3_i => rs3.

**`xcsr_alu`** — neorv32_cpu · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Receives CSR-related output from the ALU instance and contributes that value to the combined xcsr_res register read data.
  - **roles** — ALU CSR fragment; forwarded to xcsr_res; sourced from ALU instance
  - **relationships** — **CARRIES** → neorv32_cpu_alu_inst.csr_o; **SOURCES** → xcsr_res
  - **evidence** — alu port map: csr_o => xcsr_alu; xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc.

**`xcsr_cnt`** — neorv32_cpu · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Holds CSR data from the counters unit; driven by the counters instance rdata_o and forwarded into the aggregate xcsr_res.
  - **roles** — counter CSR fragment; forwarded to xcsr_res; sourced from counters instance
  - **relationships** — **CARRIES** → neorv32_cpu_counters_inst.rdata_o; **SOURCES** → xcsr_res
  - **evidence** — counters port map: rdata_o => xcsr_cnt; xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc.

**`xcsr_icc`** — neorv32_cpu · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Receives CSR read data from the ICC instance and supplies it into the combined xcsr_res value.
  - **roles** — ICC CSR fragment; forwarded to xcsr_res; sourced from ICC instance
  - **relationships** — **CARRIES** → neorv32_cpu_icc_inst.csr_rdata_o; **SOURCES** → xcsr_res
  - **evidence** — icc port map: csr_rdata_o => xcsr_icc; xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc.

**`xcsr_pmp`** — neorv32_cpu · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Carries CSR data from the PMP unit into the xcsr_res aggregate; it is produced by the PMP instance when enabled or set to zero when PMP is disabled.
  - **roles** — PMP CSR fragment; forwarded to xcsr_res; sourced from PMP instance
  - **relationships** — **CARRIES** → neorv32_cpu_pmp_inst.csr_o; **SOURCES** → xcsr_res
  - **evidence** — pmp port map: csr_o => xcsr_pmp; xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc; pmp_disabled assigns xcsr_pmp <= (others => '0').

**`xcsr_res`** — neorv32_cpu · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Combines CSR fragments (counter, ALU, PMP, ICC) by OR and supplies the result to the control unit's xcsr_rdata_i input.
  - **roles** — combined CSR readback; forwarded to control instance
  - **relationships** — **DERIVES_FROM** → xcsr_cnt, xcsr_alu, xcsr_pmp, xcsr_icc; **SOURCES** → neorv32_cpu_control_inst.xcsr_rdata_i
  - **evidence** — xcsr_res <= xcsr_cnt or xcsr_alu or xcsr_pmp or xcsr_icc; control port map: xcsr_rdata_i => xcsr_res.


## neorv32_cpu_cp_cfu  (18 non-assets)

### ports

**`clk_i`** — neorv32_cpu_cp_cfu · `std_ulogic`
  - **functionality** — Supplies the rising edge used to capture key_mem and xtea fields in the two clocked processes; it sequences all clocked updates for CSR writes and the XTEA core.
  - **roles** — sequence clock; drives register updates
  - **relationships** — **SEQUENCES** → key_mem, xtea, xtea.done, xtea.opa, xtea.opb, xtea.sum, xtea.res
  - **evidence** — rising_edge(clk_i) in csr_write_access and xtea_core processes

**`csr_rdata_o`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Exports the addressed key_mem entry to the entity boundary by carrying the selected key_mem element to the output port.
  - **roles** — read data export; carries key_mem value out
  - **relationships** — **CARRIES** → key_mem; **EXPORTS** → _(none)_
  - **evidence** — csr_rdata_o <= key_mem(to_integer(unsigned(csr_addr_i))) concurrent assignment

**`funct3_i`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Both gates internal xtea updates (sum/res computations) and selects among combinational alternatives: it controls xtea.sum and xtea.res branches, selects operands for tmp_* signals, and serves as the case selector that chooses result_o/valid_o branches.
  - **roles** — internal operation controller; selects combinational operands; chooses result branch
  - **relationships** — **GATES** → xtea.sum, xtea.res; **SELECTS** → tmp_a, tmp_b, tmp_x, tmp_y, tmp_z, result_o, valid_o
  - **evidence** — conditions in xtea_core (funct3_i(...) = ...) and tmp_* when ... else assignments and case funct3_i in result_select

**`funct7_i`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(6 downto 0)`
  - **functionality** — Declared but not referenced anywhere in this source; it does not affect behavior in this entity.
  - **roles** — unused port
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences of funct7_i in the source

**`rstn_i`** — neorv32_cpu_cp_cfu · `std_ulogic`
  - **functionality** — Active-low reset overrides and initializes key_mem and all xtea fields to zero in both clocked processes; it forces the recovery values on reset.
  - **roles** — reset override; initialises registers
  - **relationships** — **OVERRIDES** → key_mem, xtea, xtea.done, xtea.opa, xtea.opb, xtea.sum, xtea.res; **SEQUENCES** → key_mem, xtea, xtea.done, xtea.opa, xtea.opb, xtea.sum, xtea.res
  - **evidence** — if (rstn_i = '0') then ... end if in csr_write_access and xtea_core processes

**`rtype_i`** — neorv32_cpu_cp_cfu · `std_ulogic`
  - **functionality** — Controls which operation path is taken: it gates capture/start of the XTEA operation in the core and also gates the result_select process to enable result_o/valid_o when rtype matches r3type_c.
  - **roles** — operation type control; gates start and result selection
  - **relationships** — **GATES** → xtea.opa, xtea.opb, xtea.done, result_o, valid_o
  - **evidence** — used in if (start_i = '1') and (rtype_i = r3type_c) in xtea_core and if (rtype_i = r3type_c) in result_select

### signals

**`tmp_a`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Combinationally forwards either xtea.opb or xtea.opa depending on funct3_i(0); its value is used in the tmp_r arithmetic and later captured into xtea.res indirectly.
  - **roles** — operand selector; carries selected operand; feeds tmp_r
  - **relationships** — **CARRIES** → xtea.opb, xtea.opa; **SOURCES** → tmp_r
  - **evidence** — tmp_a <= xtea.opb when (funct3_i(0) = '0') else xtea.opa concurrent

**`tmp_b`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Combinationally forwards either xtea.opa or xtea.opb depending on funct3_i(0); it is used directly in the xtea.res capture as the add/sub operand.
  - **roles** — operand selector; carries selected operand; feeds xtea.res
  - **relationships** — **CARRIES** → xtea.opa, xtea.opb; **SOURCES** → xtea.res
  - **evidence** — tmp_b <= xtea.opa when (funct3_i(0) = '0') else xtea.opb concurrent

**`tmp_r`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Computes the combined arithmetic expression (xor/add/xor) from tmp_x,tmp_y,tmp_a,xtea.sum and tmp_z; its result is used to form xtea.res on the next clock.
  - **roles** — arithmetic intermediate; feeds xtea.res
  - **relationships** — **DERIVES_FROM** → tmp_x, tmp_y, tmp_a, xtea.sum, tmp_z; **SOURCES** → xtea.res
  - **evidence** — tmp_r <= std_ulogic_vector(unsigned(tmp_x xor tmp_y) + unsigned(tmp_a)) xor std_ulogic_vector(unsigned(xtea.sum) + unsigned(tmp_z)) concurrent

**`tmp_x`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Constructs a 32-bit value by concatenating xtea.opb(27 downto 0) or xtea.opa(27 downto 0) with "0000" depending on funct3_i(0); used in the tmp_r arithmetic.
  - **roles** — operand fragment; supplies rotated bits to tmp_r
  - **relationships** — **SLICES** → xtea.opb; **SLICES** → xtea.opa; **SOURCES** → tmp_r
  - **evidence** — tmp_x <= xtea.opb(27 downto 0) & "0000" when (funct3_i(0) = '0') else xtea.opa(27 downto 0) & "0000"

**`tmp_y`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Constructs a 32-bit value by concatenating "00000" with xtea.opb(31 downto 5) or xtea.opa(31 downto 5) depending on funct3_i(0); it participates in the tmp_r arithmetic.
  - **roles** — operand fragment; feeds tmp_r
  - **relationships** — **SLICES** → xtea.opb; **SLICES** → xtea.opa; **SOURCES** → tmp_r
  - **evidence** — tmp_y <= "00000" & xtea.opb(31 downto 5) when (funct3_i(0) = '0') else "00000" & xtea.opa(31 downto 5)

**`tmp_z`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Derives its value from key_mem selected by slices of xtea.sum (two different slice ranges depending on funct3_i(0)); its value enters tmp_r computation.
  - **roles** — indexed key word; feeds tmp_r
  - **relationships** — **DERIVES_FROM** → key_mem; **DERIVES_FROM** → xtea.sum; **SOURCES** → tmp_r
  - **evidence** — tmp_z <= key_mem(to_integer(unsigned(xtea.sum(1 downto 0)))) when ... else key_mem(to_integer(unsigned(xtea.sum(12 downto 11))))

**`xtea`** — neorv32_cpu_cp_cfu · `xtea_t`
  - **functionality** — Groups the XTEA internal fields (done, opa, opb, sum, res) which are reset and updated on clock edges; represents the core operation state.
  - **roles** — operation state aggregate; holds fields across cycles; supplies fields to combinational logic
  - **relationships** — **AGGREGATES** → xtea.done, xtea.opa, xtea.opb, xtea.sum, xtea.res
  - **evidence** — type xtea_t record and assignments xtea.done<=..., xtea.opa<=..., etc in xtea_core reset and clock branches

**`xtea.done`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Bit0 is set on a start condition and bit1 follows bit0 on the next clock; bit1 is used as the external valid flag for results.
  - **roles** — operation progress flag; pipeline stage (bit shift); drives valid_o
  - **relationships** — **CAPTURES** → xtea.done; **SOURCES** → valid_o
  - **evidence** — xtea.done(0)<= '0'; xtea.done(1)<= xtea.done(0); xtea.done(0)<= '1' in xtea_core; valid_o <= xtea.done(1) in result_select

**`xtea.opa`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Captures rs1_i into the opa field on a start condition and supplies opa to combinational tmp signals and to the sum computation when selected.
  - **roles** — holds operand A; captured on start; feeds tmp signals and sum
  - **relationships** — **CAPTURES** → rs1_i; **SOURCES** → tmp_a, tmp_b, tmp_x, tmp_y, xtea.sum
  - **evidence** — xtea.opa <= rs1_i on start in xtea_core; tmp_* assignments read xtea.opa; xtea.sum <= xtea.opa in xtea_core (funct3 branch)

**`xtea.opb`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Captures rs2_i into the opb field on a start condition and supplies opb to combinational tmp signals used in the round computation.
  - **roles** — holds operand B; captured on start; feeds tmp signals
  - **relationships** — **CAPTURES** → rs2_i; **SOURCES** → tmp_a, tmp_b, tmp_x, tmp_y
  - **evidence** — xtea.opb <= rs2_i on start in xtea_core; tmp_* assignments read xtea.opb

**`xtea.res`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Captures the round result computed from tmp_b and tmp_r (sum or difference) when xtea.done(0) is set, and supplies that held result to the result_o output.
  - **roles** — holds computed word; feeds result_o
  - **relationships** — **CAPTURES** → tmp_b, tmp_r; **SOURCES** → result_o
  - **evidence** — xtea.res <= std_ulogic_vector(unsigned(tmp_b) +/- unsigned(tmp_r)) in xtea_core; result_o <= xtea.res in result_select

**`xtea.sum`** — neorv32_cpu_cp_cfu · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is updated from opa or incremented/decremented by the delta according to funct3_i, and its low bits (and other slices) select key_mem entries and enter tmp_r arithmetic.
  - **roles** — accumulator/index; selects key word; feeds tmp_r computation
  - **relationships** — **CAPTURES** → xtea.opa, xtea.sum; **SELECTS** → key_mem; **SELECTS** → key_mem; **SOURCES** → tmp_r
  - **evidence** — xtea.sum <= xtea.opa or xtea.sum +/- xtea_delta_c in xtea_core; tmp_z uses xtea.sum(...); tmp_r expression uses xtea.sum


## neorv32_cpu_cp_muldiv  (58 non-assets)

### ports

**`clk_i`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Supplies the rising-edge timing and reset sensitivity for the entity's sequential processes; it times updates of ctrl, mul and div registers used to produce results. It is not read as a data operand.
  - **roles** — clock for registers; timing source for sequential updates
  - **relationships** — **SEQUENCES** → ctrl; **SEQUENCES** → ctrl.state, ctrl.cnt, ctrl.out_en; **SEQUENCES** → mul.dsp_x, mul.dsp_y, mul.prod; **SEQUENCES** → div.quotient, div.rs2_abs, div.sign_mod, div.remainder
  - **evidence** — process sensitivity lists and rising_edge(clk_i) in control, multiplier and divider processes

**`ctrl_i`** — neorv32_cpu_cp_muldiv · `ctrl_bus_t`
  - **functionality** — Provides the instruction and CPU control fields to this unit; the entity consumes specific fields of this record to detect multiply/divide commands and to guide execution. The record's individual fields are read, not forwarded.
  - **roles** — control record input; provides instruction fields (consumed)
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — individual fields of ctrl_i are referenced throughout (e.g. ctrl_i.ir_funct3), not the whole record

**`ctrl_i.alu_cp_alu`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Flags that the ALU coprocessor is targeted; it is read to form valid_cmd and thus starts mul/div handling. It helps qualify incoming commands to this unit.
  - **roles** — command qualifier; input consumed
  - **relationships** — **SOURCES** → valid_cmd
  - **evidence** — valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and ... else '0'

**`ctrl_i.alu_cp_cfu`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — CFU coprocessor qualifier is present in the record but not referenced by this module.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.alu_cp_fpu`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — FPU coprocessor qualifier is declared but not consumed here.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.alu_imm`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Immediate operand field exists on the control record but is not read by the multiply/divide logic.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.alu_op`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(2 downto 0)`
  - **functionality** — ALU operation code field exists but this coprocessor unit selects operations from instruction funct fields instead; alu_op is not read here.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.alu_opa_mux`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — ALU operand A multiplexer control is present in the record but not read here.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.alu_opb_mux`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — ALU operand B multiplexer control is declared but unused in this source.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.alu_sub`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — ALU subtract control is supplied in the record but not used by this multiplier/divider component.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.alu_unsigned`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Unsigned ALU mode is part of the control record but not consumed here; signedness decisions use ir_funct3 fields instead.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.cnt_event`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(11 downto 0)`
  - **functionality** — Event counter controls are present but not used by this multiplier/divider unit.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.cnt_halt`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(15 downto 0)`
  - **functionality** — Cycle-count halt field exists in the record but is not consumed by this entity.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.cpu_debug`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — CPU debug flag is present in the control record but not referenced in this module.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.cpu_priv`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — CPU privilege indicator is declared but not read in this unit.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.cpu_sleep`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — CPU sleep indicator is part of the record but unused locally.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.cpu_trap`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Supplies the CPU trap signal to the control FSM; when asserted it is tested in the busy-state condition and forces the state to S_DONE.
  - **roles** — external event input; gates state transitions
  - **relationships** — **GATES** → ctrl.state
  - **evidence** — control process: if (or_reduce_f(ctrl.cnt) = '0') or (ctrl_i.cpu_trap = '1') then ctrl.state <= S_DONE;

**`ctrl_i.csr_addr`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(11 downto 0)`
  - **functionality** — CSR address field is present in the control record but unused by this unit.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.csr_re`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — CSR read-enable field declared but not referenced here.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.csr_wdata`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(31 downto 0)`
  - **functionality** — CSR write-data field is declared but not read by this module.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.csr_we`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — CSR write-enable field is part of the record but not used by this module.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.if_ack`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Declared but not referenced in this entity; it is neither read nor forwarded.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.if_fence`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Declared as part of the control record but not read anywhere in this source; it is not used to influence logic here.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.if_reset`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Declared but not referenced in this entity; it is neither read nor forwarded.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.ir_funct12`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(11 downto 0)`
  - **functionality** — Part of the instruction word used to recognise multiply/divide opcode patterns; a slice (bits 11 downto 5) is compared to a constant to qualify valid_cmd.
  - **roles** — instruction field (consumed); qualifies command
  - **relationships** — **SLICES** → valid_cmd
  - **evidence** — valid_cmd <= '1' when ... (ctrl_i.ir_funct12(11 downto 5) = "0000001") ...

**`ctrl_i.ir_funct3`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Supplies the 3-bit instruction sub-opcode; it is consumed to decide signedness, whether mul or div is requested, and to select the result form. It both gates state transitions and selects result outputs.
  - **roles** — instruction opcode field (consumed); chooses operation subtype; gates state transitions
  - **relationships** — **SOURCES** → ctrl.rs1_is_signed, ctrl.rs2_is_signed, mul.start, div.start; **GATES** → ctrl.state; **SELECTS** → res_o, div.res_u; **SELECTS** → div.sign_mod; **SLICES** → valid_cmd
  - **evidence** — used in ctrl.rs1_is_signed/rs2_is_signed assignments, mul/div start when-expressions, control process condition, and operation_result case

**`ctrl_i.ir_opcode`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(6 downto 0)`
  - **functionality** — Opcode bits are read to qualify multiply/divide commands; bit 5 of ir_opcode is tested as part of valid_cmd generation.
  - **roles** — instruction field (consumed); qualifies command
  - **relationships** — **SLICES** → valid_cmd
  - **evidence** — valid_cmd <= '1' when ... (ctrl_i.ir_opcode(5) = '1') and ...

**`ctrl_i.lsu_amo`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Atomic memory operation flag is declared but unused in this entity.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.lsu_fence`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — LSU fence control is present in the record but not read by this unit.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.lsu_mo_we`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Load/store memory-order write-enable field exists but is not used here.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.lsu_priv`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Load/store privilege indicator is declared but not consumed here.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.lsu_req`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Load/store request flag exists in the record but is not used by this unit.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.lsu_rw`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Load/store read/write indicator is present but not read here.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.pc_cur`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Program counter current field is present in the control record but not used by this multiplier/divider unit.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.pc_nxt`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Program counter next is declared but not read in this entity.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.pc_ret`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Return-PC field exists in the record but is not used by this entity.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.rf_rd`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(4 downto 0)`
  - **functionality** — RF destination index exists in the record but is not used by this module.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.rf_rs1`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(4 downto 0)`
  - **functionality** — RF source index field is present but not read in this source; it is not used to compute results here.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.rf_rs2`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(4 downto 0)`
  - **functionality** — RF source index field is declared but not referenced in this entity.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.rf_wb_en`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Register-file writeback enable is available in the record but not consumed by this module.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`ctrl_i.rf_zero_we`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Declared but not referenced; the zero-write enable is not consumed here.
  - **roles** — unused record field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond port declaration

**`rstn_i`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Provides reset recovery to sequential registers in the entity; resets ctrl, mul and div registers to initial values in reset branches of clocked processes.
  - **roles** — reset for registers; initialises sequential state
  - **relationships** — **SEQUENCES** → ctrl; **SEQUENCES** → ctrl.state, ctrl.cnt, ctrl.out_en; **SEQUENCES** → mul.dsp_x, mul.dsp_y, mul.prod; **SEQUENCES** → div.quotient, div.rs2_abs, div.sign_mod, div.remainder
  - **evidence** — reset branches (if (rstn_i = '0')) in control, multiplier and divider processes

### signals

**`ctrl`** — neorv32_cpu_cp_muldiv · `ctrl_t`
  - **functionality** — Holds the module's FSM state, countdown, signedness flags and output-enable; these fields are updated in the control clocked process and used to steer multiply/divide sequencing and result gating.
  - **roles** — holds FSM state; carries control flags; gates outputs
  - **relationships** — **CAPTURES** → ctrl.state, ctrl.cnt, ctrl.out_en
  - **evidence** — control process assigns ctrl.state/cnt/out_en in reset and on rising_edge(clk_i)

**`ctrl.out_en`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Is set when an operation completes (S_DONE) and is used combinationally to allow res_o to be driven; it is updated in the control process and gates result selection.
  - **roles** — holds completion strobe; gates result export
  - **relationships** — **CAPTURES** → ctrl; **GATES** → res_o
  - **evidence** — control process sets ctrl.out_en <= '1' in S_DONE; operation_result checks ctrl.out_en

**`div`** — neorv32_cpu_cp_muldiv · `div_t`
  - **functionality** — Contains the per-division registers (quotient, remainder, rs2_abs, sign_mod, etc.); fields are updated in the divider clocked process and drive the combinational divider helpers.
  - **roles** — holds division state; carries iteration data
  - **relationships** — **CAPTURES** → div.quotient, div.rs2_abs, div.sign_mod, div.remainder
  - **evidence** — divider_core process assigns div fields on reset and rising_edge(clk_i)

**`div.quotient`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Holds the running quotient during division; it is initialised from rs1_i and shifted/updated each cycle and supplies bits to the div.sub concatenation and to the final result selection.
  - **roles** — holds quotient across iterations; feeds subtraction and result selection
  - **relationships** — **CAPTURES** → rs1_i; **SOURCES** → div.sub, div.res_u
  - **evidence** — divider_core assigns div.quotient <= rs1_i or std_ulogic_vector(0 - unsigned(rs1_i)); div.sub uses div.quotient(31)

**`div.remainder`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Maintains the current remainder during iterative division; it is updated in the divider clocked process and contributes its lower bits to the combinational div.sub calculation.
  - **roles** — holds remainder across iterations; supplies bits to subtraction
  - **relationships** — **CAPTURES** → div; **SLICES** → div.sub; **SOURCES** → div.sub, div.res_u
  - **evidence** — divider_core updates div.remainder; div.sub <= unsigned('0' & div.remainder(30 downto 0) & div.quotient(31)) - ...

**`div.res_u`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Combinationally selects either quotient or remainder as the unsigned result candidate depending on instruction sub-opcode bits; it is then possibly negated to produce div.res.
  - **roles** — selects unsigned result; feeds final result
  - **relationships** — **DERIVES_FROM** → div.quotient, div.remainder; **SELECTS** → div.res
  - **evidence** — div.res_u <= div.quotient when (ctrl_i.ir_funct3(2 downto 1) = op_div_c(2 downto 1)) else div.remainder;

**`div.rs2_abs`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Captured absolute value of rs2 during division initialisation; it is produced from rs2_i (possibly negated) and then used by the combinational subtraction div.sub.
  - **roles** — holds absolute divisor; feeds divisor subtraction
  - **relationships** — **CAPTURES** → rs2_i; **SOURCES** → div.sub
  - **evidence** — divider_core sets div.rs2_abs <= rs2_i or std_ulogic_vector(0 - unsigned(rs2_i)); div.sub <= ... - unsigned('0' & div.rs2_abs)

**`div.sign_mod`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Captured during divider initialisation to remember whether the final quotient/remainder must be negated; it is assigned in the clocked divider and selects whether div.res is negated.
  - **roles** — stores sign correction; overrides final result sign
  - **relationships** — **CAPTURES** → div; **OVERRIDES** → div.res; **SELECTS** → div.sign_mod
  - **evidence** — div.sign_mod assigned in divider_core during start and used in 'div.res <= ... when (div.sign_mod = '1') else div.res_u;'

**`div.sub`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(XLEN   downto 0)`
  - **functionality** — Combinationally computes remainder||quotient - divisor (extended); its MSB is used to decide next quotient bit and lower bits can replace remainder on successful subtraction.
  - **roles** — computes trial subtraction; constrains quotient/remainder updates
  - **relationships** — **DERIVES_FROM** → div.remainder, div.quotient, div.rs2_abs; **CONSTRAINS** → div.quotient, div.remainder
  - **evidence** — div.sub <= std_ulogic_vector(unsigned('0' & div.remainder(30 downto 0) & div.quotient(31)) - unsigned('0' & div.rs2_abs)); divider_core tests div.sub(32)

**`mul`** — neorv32_cpu_cp_muldiv · `mul_t`
  - **functionality** — Holds multiplier internal values (prod, add, dsp operands, etc.); fields are updated in either parallel or serial multiplier logic and supply data for result selection and serial updates.
  - **roles** — holds multiplication state; carries product and helper values
  - **relationships** — **CAPTURES** → mul.prod, mul.dsp_x, mul.dsp_y
  - **evidence** — mul record fields assigned in multiplier processes and concurrent assignments

**`mul.add`** — neorv32_cpu_cp_muldiv · `std_ulogic_vector(XLEN downto 0)`
  - **functionality** — Combinational helper value computed from product upper bits and (possibly) rs2; it is consumed in the serial multiplier to update product upper part on each iteration.
  - **roles** — computes adder input; feeds product update
  - **relationships** — **DERIVES_FROM** → mul.prod, rs2_i, ctrl.rs2_is_signed, ctrl.rs1_is_signed, ctrl.state; **SOURCES** → mul.prod
  - **evidence** — mul_update process computes mul.add from mul.prod, rs2_i and ctrl flags; serial multiplier uses mul.add to update mul.prod

**`mul.dsp_x`** — neorv32_cpu_cp_muldiv · `signed(XLEN downto 0)`
  - **functionality** — Signed extended rs1 captured into a DSP operand register when the parallel multiplier starts; it supplies one input to the combinational DSP multiplication mul.dsp_z.
  - **roles** — holds DSP operand; feeds parallel multiply
  - **relationships** — **CAPTURES** → rs1_i, ctrl.rs1_is_signed; **SOURCES** → mul.dsp_z
  - **evidence** — multiplier_core_in_reg captures mul.dsp_x <= signed((rs1_i(rs1_i'left) and ctrl.rs1_is_signed) & rs1_i); mul.dsp_z <= mul.dsp_x * mul.dsp_y

**`mul.dsp_y`** — neorv32_cpu_cp_muldiv · `signed(XLEN downto 0)`
  - **functionality** — Signed extended rs2 captured into a DSP operand register when the parallel multiplier starts; it supplies the other input to mul.dsp_z multiplication.
  - **roles** — holds DSP operand; feeds parallel multiply
  - **relationships** — **CAPTURES** → rs2_i, ctrl.rs2_is_signed; **SOURCES** → mul.dsp_z
  - **evidence** — multiplier_core_in_reg captures mul.dsp_y <= signed((rs2_i(rs2_i'left) and ctrl.rs2_is_signed) & rs2_i); mul.dsp_z <= mul.dsp_x * mul.dsp_y

**`mul.dsp_z`** — neorv32_cpu_cp_muldiv · `signed(2*XLEN+1 downto 0)`
  - **functionality** — Combinational product of dsp_x and dsp_y for the parallel multiplier; its lower 64 bits are captured into mul.prod by a clocked process.
  - **roles** — parallel product (combinational); feeds product register
  - **relationships** — **DERIVES_FROM** → mul.dsp_x, mul.dsp_y; **SOURCES** → mul.prod
  - **evidence** — mul.dsp_z <= mul.dsp_x * mul.dsp_y; multiplier_core_out_reg captures mul.prod <= std_ulogic_vector(mul.dsp_z(63 downto 0))

**`mul.p_sext`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Combinational single-bit derived from the product top bit and rs2 signedness, used as the sign-extension bit when forming add inputs in serial multiplication.
  - **roles** — sign-extension bit (combinational); feeds adder formation
  - **relationships** — **DERIVES_FROM** → mul.prod, ctrl.rs2_is_signed; **SOURCES** → mul.add
  - **evidence** — mul.p_sext <= mul.prod(mul.prod'left) and ctrl.rs2_is_signed; mul_update uses mul.p_sext & mul.prod(63 downto 32)

**`valid_cmd`** — neorv32_cpu_cp_muldiv · `std_ulogic`
  - **functionality** — Combinationally indicates a recognised multiply/divide instruction by testing ctrl_i fields and DIVISION_EN; it gates start signals and the control FSM entry.
  - **roles** — command detector; enables starts; gates control FSM
  - **relationships** — **DERIVES_FROM** → ctrl_i.alu_cp_alu, ctrl_i.ir_opcode, ctrl_i.ir_funct12, ctrl_i.ir_funct3; **GATES** → mul.start, div.start, ctrl.state
  - **evidence** — valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and (ctrl_i.ir_funct12(11 downto 5) = "0000001") and ((ctrl_i.ir_funct3(2) = '0') or ((ctrl_i.ir_funct3(2) = '1') and DIVISION_EN)) else '0'; control process tests valid_cmd


## neorv32_cpu_pmp  (56 non-assets)

### ports

**`clk_i`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Drives rising_edge sampling for PMP state elements. It times updates of pmpcfg, pmpaddr, addr_mask and the fault output so those registers change synchronously on clock edges.
  - **roles** — clock source; synchronises register updates
  - **relationships** — **SEQUENCES** → pmpcfg; **SEQUENCES** → pmpaddr; **SEQUENCES** → addr_mask; **SEQUENCES** → fault_o
  - **evidence** — rising_edge(clk_i) branches in csr_pmpcfg, csr_pmpaddr, addr_masking and fault_check processes

**`csr_o`** — neorv32_cpu_pmp · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Drives CSR read result to the outside based on ctrl_i.csr_addr: it presents packed pmpcfg bytes (cfg_rd32) or read-back addresses (addr_rd) onto the bus.
  - **roles** — CSR read output; exports internal readback
  - **relationships** — **DERIVES_FROM** → cfg_rd32; **DERIVES_FROM** → addr_rd; **SELECTS** → ctrl_i.csr_addr
  - **evidence** — csr_read_access process assigns csr_o <= cfg_rd32(...) or addr_rd(...) based on ctrl_i.csr_addr

**`ctrl_i.alu_cp_alu`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Present but not used here.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.alu_cp_alu in the source

**`ctrl_i.alu_cp_cfu`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Present but not used here.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.alu_cp_cfu in the source

**`ctrl_i.alu_cp_fpu`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Present but not used here.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.alu_cp_fpu in the source

**`ctrl_i.alu_imm`** — neorv32_cpu_pmp · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Not read by this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.alu_imm in the source

**`ctrl_i.alu_op`** — neorv32_cpu_pmp · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Part of the control bundle but not read here.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.alu_op in the source

**`ctrl_i.alu_opa_mux`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Not referenced in this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.alu_opa_mux in the source

**`ctrl_i.alu_opb_mux`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Not referenced in this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.alu_opb_mux in the source

**`ctrl_i.alu_sub`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Present in the record but not used by PMP logic here.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.alu_sub in the source

**`ctrl_i.alu_unsigned`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Not referenced in this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.alu_unsigned in the source

**`ctrl_i.cnt_event`** — neorv32_cpu_pmp · `std_ulogic_vector(11 downto 0)`
  - **functionality** — Part of the control record but not consumed in this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.cnt_event in the source

**`ctrl_i.cnt_halt`** — neorv32_cpu_pmp · `std_ulogic_vector(15 downto 0)`
  - **functionality** — Part of the control record but not consumed in this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.cnt_halt in the source

**`ctrl_i.cpu_debug`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Used to suppress fault reporting: the fault output samples (not ctrl_i.cpu_debug) AND fail(0) on clock edges, so cpu_debug effectively gates fault generation at the output.
  - **roles** — fault gate; combinational input
  - **relationships** — **GATES** → fault_o
  - **evidence** — fault_check process: fault_o <= (not ctrl_i.cpu_debug) and fail(0) on rising_edge(clk_i)

**`ctrl_i.cpu_priv`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Supplies the CPU privilege level used for instruction accesses and, when chosen into acc_priv, factors into allow(r) permission computation.
  - **roles** — privilege operand; combinational input
  - **relationships** — **SOURCES** → acc_priv; **SOURCES** → allow
  - **evidence** — acc_priv selection and perm_gen read ctrl_i.cpu_priv to decide allow(r)

**`ctrl_i.cpu_sleep`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Part of the bundle but unused by this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.cpu_sleep in the source

**`ctrl_i.cpu_trap`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Part of the bundle but unused by this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.cpu_trap in the source

**`ctrl_i.csr_addr`** — neorv32_cpu_pmp · `std_ulogic_vector(11 downto 0)`
  - **functionality** — Chooses which CSR word is read or which pmpcfg/pmpaddr write-lane to enable; its low bits index pmpcfg_we/pmpaddr_we and select entries from cfg_rd32/addr_rd for csr_o.
  - **roles** — index selector; CSR read/write selector
  - **relationships** — **SELECTS** → pmpcfg_we; **SELECTS** → pmpaddr_we; **SELECTS** → cfg_rd32; **SELECTS** → addr_rd; **SELECTS** → csr_o
  - **evidence** — csr_we_cfg and csr_we_addr processes index write enables; csr_read_access uses ctrl_i.csr_addr to choose cfg_rd32 or addr_rd outputs

**`ctrl_i.csr_re`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Declared but not used for CSR read selection inside this entity; csr_read_access uses csr_addr directly.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.csr_re in the source

**`ctrl_i.csr_wdata`** — neorv32_cpu_pmp · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies write data bits for PMP configuration and address writes; pmpcfg and pmpaddr capture slices of this vector when their write enables are active.
  - **roles** — write-data source; provides configuration bits
  - **relationships** — **SOURCES** → pmpcfg; **SOURCES** → pmpaddr
  - **evidence** — pmpcfg process assigns pmpcfg(i)(...) <= ctrl_i.csr_wdata(...); pmpaddr process assigns pmpaddr(i) <= "00" & ctrl_i.csr_wdata(XLEN-3 downto 0)

**`ctrl_i.csr_we`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Used to qualify CSR writes: combined with csr_addr it drives pmpcfg_we and pmpaddr_we signals that enable writes into PMP configuration and address registers.
  - **roles** — write enable input; gates CSR write strobes
  - **relationships** — **DERIVES_FROM** → pmpcfg_we; **DERIVES_FROM** → pmpaddr_we
  - **evidence** — csr_we_cfg and csr_we_addr processes compare ctrl_i.csr_we and ctrl_i.csr_addr to set pmpcfg_we/pmpaddr_we

**`ctrl_i.if_ack`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Not referenced in this source; it does not affect PMP logic here.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.if_ack in the source

**`ctrl_i.if_fence`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Not referenced anywhere in this source; the entity neither reads nor forwards this field.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.if_fence in the source

**`ctrl_i.if_reset`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Not referenced in this source; no logic consumes or forwards it here.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.if_reset in the source

**`ctrl_i.ir_funct12`** — neorv32_cpu_pmp · `std_ulogic_vector(11 downto 0)`
  - **functionality** — Not referenced in this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.ir_funct12 in the source

**`ctrl_i.ir_funct3`** — neorv32_cpu_pmp · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Not referenced in this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.ir_funct3 in the source

**`ctrl_i.ir_opcode`** — neorv32_cpu_pmp · `std_ulogic_vector(6 downto 0)`
  - **functionality** — Not referenced in this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.ir_opcode in the source

**`ctrl_i.lsu_amo`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Not referenced by the PMP logic here.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.lsu_amo in the source

**`ctrl_i.lsu_fence`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Not referenced by PMP logic in this source.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.lsu_fence in the source

**`ctrl_i.lsu_mo_we`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Controls whether acc_addr/acc_priv come from the core (pc_nxt/cpu_priv) or from the LSU (addr_ls_i/lsu_priv); it also selects the instruction vs memory permission branch in the allow computation.
  - **roles** — branch selector; gates address/privilege selection
  - **relationships** — **GATES** → acc_addr; **GATES** → acc_priv; **GATES** → allow
  - **evidence** — acc_addr and acc_priv conditional assignments; perm_gen's outer if (ctrl_i.lsu_mo_we = '0')

**`ctrl_i.lsu_priv`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Supplies the privilege level used for memory operations (chosen into acc_priv when lsu_mo_we = '1'), which then factors into the allow computation.
  - **roles** — privilege operand; combinational input
  - **relationships** — **SOURCES** → acc_priv; **SOURCES** → allow
  - **evidence** — acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv; perm_gen reads acc_priv and ctrl_i.lsu_priv in branches

**`ctrl_i.lsu_req`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Part of the bundle but not read in this source.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.lsu_req in the source

**`ctrl_i.lsu_rw`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Used by permission logic to choose the R or W permission check path when lsu_mo_we indicates a memory operation; it thus influences allow(r) computation.
  - **roles** — permission selector; combinational input
  - **relationships** — **GATES** → allow
  - **evidence** — perm_gen: branches using ctrl_i.lsu_rw to select read vs write permission path

**`ctrl_i.pc_cur`** — neorv32_cpu_pmp · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Declared in the control bundle but not read by this entity; it does not contribute to PMP decisions here.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.pc_cur in the source

**`ctrl_i.pc_nxt`** — neorv32_cpu_pmp · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies the PC value used as the access address when lsu_mo_we = '0'; that acc_addr is then used for matching and permission checks.
  - **roles** — address operand; combinational input
  - **relationships** — **SOURCES** → acc_addr
  - **evidence** — acc_addr <= ctrl_i.pc_nxt when (ctrl_i.lsu_mo_we = '0') else addr_ls_i

**`ctrl_i.pc_ret`** — neorv32_cpu_pmp · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Present in the control bundle but not read in this source.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.pc_ret in the source

**`ctrl_i.rf_rd`** — neorv32_cpu_pmp · `std_ulogic_vector(4 downto 0)`
  - **functionality** — Not referenced by this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.rf_rd in the source

**`ctrl_i.rf_rs1`** — neorv32_cpu_pmp · `std_ulogic_vector(4 downto 0)`
  - **functionality** — Not referenced by this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.rf_rs1 in the source

**`ctrl_i.rf_rs2`** — neorv32_cpu_pmp · `std_ulogic_vector(4 downto 0)`
  - **functionality** — Not referenced by this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.rf_rs2 in the source

**`ctrl_i.rf_wb_en`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Not referenced by this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.rf_wb_en in the source

**`ctrl_i.rf_zero_we`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Not referenced by this entity.
  - **roles** — unused
  - **relationships** — _none recorded_
  - **evidence** — no occurrences of ctrl_i.rf_zero_we in the source

**`rstn_i`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Asynchronously or synchronously forces initial values for PMP registers. It resets pmpcfg, pmpaddr, addr_mask and fault_o in the processes' reset branches.
  - **roles** — reset source; initialises registers
  - **relationships** — **SEQUENCES** → pmpcfg; **SEQUENCES** → pmpaddr; **SEQUENCES** → addr_mask; **SEQUENCES** → fault_o
  - **evidence** — if (rstn_i = '0') reset branches in csr_pmpcfg, csr_pmpaddr, addr_masking and fault_check processes

### signals

**`acc_addr`** — neorv32_cpu_pmp · `std_ulogic_vector(XLEN-1 downto 0)`
  - **functionality** — Combinationally selects the access address from ctrl_i.pc_nxt or addr_ls_i based on ctrl_i.lsu_mo_we; the chosen acc_addr is used for matching and comparison logic.
  - **roles** — combinational carrier; address source for matching
  - **relationships** — **DERIVES_FROM** → ctrl_i.pc_nxt; **DERIVES_FROM** → addr_ls_i; **GATES** → ctrl_i.lsu_mo_we; **SOURCES** → cmp_ge; **SOURCES** → cmp_lt; **SOURCES** → cmp_na
  - **evidence** — acc_addr <= ctrl_i.pc_nxt when (ctrl_i.lsu_mo_we = '0') else addr_ls_i; cmp_ge/cmp_lt/cmp_na use acc_addr in their comparisons

**`acc_priv`** — neorv32_cpu_pmp · `std_ulogic`
  - **functionality** — Combinationally selects privilege from cpu_priv or lsu_priv (based on lsu_mo_we) and supplies it to the permission logic for allow(r) decisions.
  - **roles** — privilege carrier; chosen by operation type
  - **relationships** — **DERIVES_FROM** → ctrl_i.cpu_priv; **DERIVES_FROM** → ctrl_i.lsu_priv; **GATES** → ctrl_i.lsu_mo_we; **SOURCES** → allow
  - **evidence** — acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv; perm_gen uses acc_priv to compute allow(r)

**`addr_mask`** — neorv32_cpu_pmp · `addr_mask_t`
  - **functionality** — Registered per-region mask that is loaded from addr_mask_napot when al bit is set; it is used in the NAPOT comparison to determine matches.
  - **roles** — registered mask; used for matching
  - **relationships** — **CAPTURES** → addr_mask_napot; **SOURCES** → cmp_na
  - **evidence** — addr_masking clocked process captures addr_mask_napot into addr_mask when pmpcfg(r)(cfg_al_c) = '1'; cmp_na uses addr_mask(r)

**`addr_mask_napot`** — neorv32_cpu_pmp · `addr_mask_t`
  - **functionality** — Combinationally builds the NPOT (NAPOT) match mask from pmpaddr bits for each region when NAP mode is enabled; the mask is a source for addr_mask assignment.
  - **roles** — mask generator; for NAPOT matching
  - **relationships** — **DERIVES_FROM** → pmpaddr; **SOURCES** → addr_mask
  - **evidence** — addr_mask_napot_gen generate assigns bits from pmpaddr; addr_masking process assigns addr_mask(r) <= addr_mask_napot(r)

**`addr_rd`** — neorv32_cpu_pmp · `csr_addr_rd_t`
  - **functionality** — Derived from pmpaddr and configuration bits (masks, TOR settings) to produce a canonical readback address; selected addr_rd entries drive csr_o for address CSR reads.
  - **roles** — readback address; derived output
  - **relationships** — **DERIVES_FROM** → pmpaddr; **DERIVES_FROM** → pmpcfg; **SOURCES** → csr_o
  - **evidence** — address_read_back process assigns addr_rd(i) from pmpaddr(i) and pmpcfg(i); csr_read_access uses addr_rd(...) to drive csr_o

**`allow`** — neorv32_cpu_pmp · `std_ulogic_vector(NUM_REGIONS-1 downto 0)`
  - **functionality** — Per-region permission bits computed from pmpcfg, acc_priv and the type of access (instruction/read/write as chosen by ctrl_i fields); an allow bit indicates the region permits execution/read/write for the current access.
  - **roles** — permission vector; operand for fault computation
  - **relationships** — **DERIVES_FROM** → pmpcfg; **DERIVES_FROM** → acc_priv; **GATES** → ctrl_i.lsu_mo_we; **GATES** → ctrl_i.lsu_rw
  - **evidence** — perm_gen process computes allow(r) via branches using pmpcfg(r) and acc_priv and tests ctrl_i.lsu_mo_we/ctrl_i.lsu_rw

**`cfg_rd`** — neorv32_cpu_pmp · `csr_cfg_rd_t`
  - **functionality** — Carries a direct copy of each pmpcfg entry for readback and packing; it is assigned the pmpcfg bytes and then aggregated into 32-bit words.
  - **roles** — readback source; carries pmpcfg value
  - **relationships** — **CARRIES** → pmpcfg; **AGGREGATES** → cfg_rd32
  - **evidence** — cfg_rd(i) <= pmpcfg(i); cfg_rd32 packed from cfg_rd entries

**`cfg_rd32`** — neorv32_cpu_pmp · `csr_cfg_rd32_t`
  - **functionality** — Aggregates four cfg_rd bytes into a 32-bit word for CSR reads; these words drive csr_o when CSR read selects them.
  - **roles** — packed readback; export source for csr_o
  - **relationships** — **AGGREGATES** → cfg_rd; **SOURCES** → csr_o
  - **evidence** — cfg_rd32(i) <= cfg_rd(i*4+3) & ... & cfg_rd(i*4+0); csr_read_access drives csr_o from cfg_rd32

**`cmp_ge`** — neorv32_cpu_pmp · `std_ulogic_vector(NUM_REGIONS-1 downto 0)`
  - **functionality** — Per-region comparison indicating acc_addr >= pmpaddr(r-1) used for TOR region lower-bound testing when TOR is enabled; feeds match decision for TOR regions.
  - **roles** — GE comparator; match input
  - **relationships** — **DERIVES_FROM** → acc_addr; **DERIVES_FROM** → pmpaddr; **SOURCES** → match
  - **evidence** — cmp_ge(r) <= '1' when (unsigned(acc_addr(...)) >= unsigned(pmpaddr(r-1)(...))) and TOR_EN else '0'

**`cmp_lt`** — neorv32_cpu_pmp · `std_ulogic_vector(NUM_REGIONS-1 downto 0)`
  - **functionality** — Per-region comparison indicating acc_addr < pmpaddr(r) used for TOR upper-bound testing when TOR is enabled; combined with cmp_ge to detect addresses inside TOR regions.
  - **roles** — LT comparator; match input
  - **relationships** — **DERIVES_FROM** → acc_addr; **DERIVES_FROM** → pmpaddr; **SOURCES** → match
  - **evidence** — cmp_lt(r) <= '1' when (unsigned(acc_addr(...)) < unsigned(pmpaddr(r)(...))) and TOR_EN else '0'

**`cmp_na`** — neorv32_cpu_pmp · `std_ulogic_vector(NUM_REGIONS-1 downto 0)`
  - **functionality** — Produces per-region 'NA' comparison results by comparing (acc_addr AND addr_mask) with (pmpaddr AND addr_mask) when NAP mode is enabled; its result is used to declare matches for NAPOT regions.
  - **roles** — NA comparator; match input
  - **relationships** — **DERIVES_FROM** → acc_addr; **DERIVES_FROM** → addr_mask; **DERIVES_FROM** → pmpaddr; **SOURCES** → match
  - **evidence** — cmp_na(r) <= '1' when ((acc_addr(...) and addr_mask(r)) = (pmpaddr(r)(...) and addr_mask(r))) and NAP_EN else '0'

**`match`** — neorv32_cpu_pmp · `std_ulogic_vector(NUM_REGIONS-1 downto 0)`
  - **functionality** — Per-region match result computed from pmpcfg mode and comparison signals (cmp_ge/cmp_lt for TOR, cmp_na for NAPOT); its asserted bits gate which region's permissions apply to an access.
  - **roles** — match vector; selects failing region
  - **relationships** — **DERIVES_FROM** → pmpcfg; **DERIVES_FROM** → cmp_ge; **DERIVES_FROM** → cmp_lt; **DERIVES_FROM** → cmp_na; **GATES** → fail
  - **evidence** — match_gen process sets match(r) from pmpcfg(...) and cmp_ge/cmp_lt/cmp_na

**`pmpaddr_we`** — neorv32_cpu_pmp · `std_ulogic_vector(15 downto 0)`
  - **functionality** — Derived from CSR address and csr_we; it selects which pmpaddr entry to write and thus gates pmpaddr register updates.
  - **roles** — write strobe; selects pmpaddr lane
  - **relationships** — **DERIVES_FROM** → ctrl_i.csr_addr; **DERIVES_FROM** → ctrl_i.csr_we; **GATES** → pmpaddr
  - **evidence** — csr_we_addr process sets pmpaddr_we based on ctrl_i.csr_addr(3 downto 0) and ctrl_i.csr_we

**`pmpcfg_we`** — neorv32_cpu_pmp · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Derived from CSR address and csr_we; it marks which pmpcfg byte-lane is being written and thus gates writes into pmpcfg registers.
  - **roles** — write strobe; selects pmpcfg lane
  - **relationships** — **DERIVES_FROM** → ctrl_i.csr_addr; **DERIVES_FROM** → ctrl_i.csr_we; **GATES** → pmpcfg
  - **evidence** — csr_we_cfg process sets pmpcfg_we based on ctrl_i.csr_addr(1 downto 0) and ctrl_i.csr_we


## neorv32_debug_dtm  (37 non-assets)

### ports

**`clk_i`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Provides the rising-edge timing for all synchronous processes. It sequences updates of tap_sync.*, tap_ctrl_state, dr_trigger.sreg, tap_reg.* and dmi_ctrl.* registers so they update on clk_i edges.
  - **roles** — clock source; sequences register updates; timing reference for internal state
  - **relationships** — **SEQUENCES** → tap_sync.tck_ff, tap_sync.tdi_ff, tap_sync.tms_ff, tap_ctrl_state, dr_trigger.sreg, tap_reg.ireg, tap_reg.idcode, tap_reg.dtmcs, tap_reg.dmi, tap_reg.bypass, dmi_ctrl.busy, dmi_ctrl.op, dmi_ctrl.dmihardreset, dmi_ctrl.dmireset, dmi_ctrl.err, dmi_ctrl.rdata, dmi_ctrl.wdata, dmi_ctrl.addr, jtag_tdo_o
  - **evidence** — Processes with "elsif rising_edge(clk_i) then" (tap_synchronizer, tap_control, update_trigger, reg_access, dmi_controller).

**`dmi_req_o`** — neorv32_debug_dtm · `dmi_req_t`
  - **functionality** — Forms and exports the DMI request record to the external DMI target by taking fields from the internal dmi_ctrl registers and presenting them at the entity boundary.
  - **roles** — exports DMI requests; carries request fields to outside; aggregate of internal dmi_ctrl fields
  - **relationships** — **AGGREGATES** → dmi_ctrl.op, dmi_ctrl.wdata, dmi_ctrl.addr; **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignments at end: dmi_req_o.op <= dmi_ctrl.op; dmi_req_o.data <= dmi_ctrl.wdata; dmi_req_o.addr <= dmi_ctrl.addr.

**`dmi_req_o.addr`** — neorv32_debug_dtm · `std_ulogic_vector(6 downto 0)`
  - **functionality** — Carries the 7-bit request address outwards; it is driven combinationally from internal dmi_ctrl.addr and exported to the DMI interface.
  - **roles** — exports address field; carries dmi_ctrl.addr to outside
  - **relationships** — **CARRIES** → dmi_ctrl.addr; **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment: dmi_req_o.addr <= dmi_ctrl.addr.

**`dmi_req_o.data`** — neorv32_debug_dtm · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries the 32-bit write data for DMI requests from internal dmi_ctrl.wdata to the external DMI interface.
  - **roles** — exports data field; carries dmi_ctrl.wdata
  - **relationships** — **CARRIES** → dmi_ctrl.wdata; **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment: dmi_req_o.data <= dmi_ctrl.wdata.

**`dmi_req_o.op`** — neorv32_debug_dtm · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Carries the 2-bit DMI operation code from internal dmi_ctrl.op to the external DMI request port.
  - **roles** — exports operation field; carries dmi_ctrl.op
  - **relationships** — **CARRIES** → dmi_ctrl.op; **EXPORTS** → _(none)_
  - **evidence** — Concurrent assignment: dmi_req_o.op <= dmi_ctrl.op.

**`dmi_rsp_i`** — neorv32_debug_dtm · `dmi_rsp_t`
  - **functionality** — Receives the response record from the external DMI target; its fields (data, ack) are consumed by the dmi_controller to capture read data and acknowledgements.
  - **roles** — imports DMI responses; supplies ack and response data
  - **relationships** — **SOURCES** → dmi_ctrl.rdata; **CONSTRAINS** → dmi_ctrl.busy
  - **evidence** — dmi_controller uses dmi_rsp_i.data to assign dmi_ctrl.rdata and checks dmi_rsp_i.ack in condition to clear busy.

**`dmi_rsp_i.ack`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Signals acknowledgement of a DMI response and constrains the dmi_controller flow; its asserted value causes dmi_ctrl.busy to be cleared.
  - **roles** — provides response ack; gates completion of DMI transaction
  - **relationships** — **CONSTRAINS** → dmi_ctrl.busy
  - **evidence** — dmi_controller checks "if (dmi_rsp_i.ack = '1') then dmi_ctrl.busy <= '0';"

**`dmi_rsp_i.data`** — neorv32_debug_dtm · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies response read-data to the dmi_controller; when a response arrives it is captured into dmi_ctrl.rdata for forwarding into tap_reg.dmi_nxt.
  - **roles** — feeds dmi_ctrl.rdata; carries external response data into entity
  - **relationships** — **SOURCES** → dmi_ctrl.rdata
  - **evidence** — In dmi_controller else branch: dmi_ctrl.rdata <= dmi_rsp_i.data.

**`jtag_tck_i`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Supplies the raw JTAG TCK level which is sampled into the three-stage synchronizer tap_sync.tck_ff; those samples are used to detect rising/falling edges used by TAP control.
  - **roles** — sampled input; drives synchronizer shift register; crosses entity boundary into tap_sync
  - **relationships** — **SOURCES** → tap_sync.tck_ff
  - **evidence** — tap_synchronizer process shifts jtag_tck_i into tap_sync.tck_ff (tap_synchronizer process rising_edge branch).

**`rstn_i`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Provides synchronous/asynchronous reset behavior: it initializes many internal registers and outputs to defined values in the reset branches of the clocked processes.
  - **roles** — reset source; initializes registers; controls recovery on reset
  - **relationships** — **SEQUENCES** → tap_sync.tck_ff, tap_sync.tdi_ff, tap_sync.tms_ff, tap_ctrl_state, dr_trigger.sreg, tap_reg.ireg, tap_reg.idcode, tap_reg.dtmcs, tap_reg.dmi, tap_reg.bypass, dmi_ctrl.busy, dmi_ctrl.op, dmi_ctrl.dmihardreset, dmi_ctrl.dmireset, dmi_ctrl.err, dmi_ctrl.rdata, dmi_ctrl.wdata, dmi_ctrl.addr, jtag_tdo_o
  - **evidence** — Processes use "if (rstn_i = '0') then" reset branches (tap_synchronizer, tap_control, update_trigger, reg_access, dmi_controller).

### signals

**`dmi_ctrl`** — neorv32_debug_dtm · `dmi_ctrl_t`
  - **functionality** — Aggregates busy, op, reset flags, error and read/write data/address registers which are updated by the dmi_controller FSM and supplied to tap_reg.dmi_nxt and dmi_req_o.
  - **roles** — holds DMI controller registers; aggregates control and data fields
  - **relationships** — **AGGREGATES** → dmi_ctrl.busy, dmi_ctrl.op, dmi_ctrl.dmihardreset, dmi_ctrl.dmireset, dmi_ctrl.err, dmi_ctrl.rdata, dmi_ctrl.wdata, dmi_ctrl.addr
  - **evidence** — dmi_ctrl record declared; fields assigned in dmi_controller process and consumed by tap_reg.dtmcs_nxt, tap_reg.dmi_nxt and dmi_req_o.

**`dmi_ctrl.addr`** — neorv32_debug_dtm · `std_ulogic_vector(6 downto 0)`
  - **functionality** — Captures the 7-bit address slice from tap_reg.dmi when a request is initiated and provides it to the external DMI request port.
  - **roles** — holds request address; drives dmi_req_o.addr
  - **relationships** — **CAPTURES** → tap_reg.dmi; **SOURCES** → dmi_req_o.addr
  - **evidence** — dmi_controller assigns dmi_ctrl.addr <= tap_reg.dmi(40 downto 34) when starting a request; dmi_req_o.addr <= dmi_ctrl.addr.

**`dmi_ctrl.dmihardreset`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Records the DMIHARDRESET control bit captured from tap_reg.dtmcs on DR_CAPTURE and is used in logic to control dmi_controller behavior and to be reflected back into dtmcs_nxt.
  - **roles** — holds hard reset bit; feeds dtmcs next-state; controls DMI controller resets
  - **relationships** — **CAPTURES** → tap_reg.dtmcs; **SOURCES** → tap_reg.dtmcs_nxt
  - **evidence** — dmi_controller sets dmihardreset <= tap_reg.dtmcs(17) when dr_trigger.valid and tap_reg.ireg = addr_dtmcs_c; tap_reg.dtmcs_nxt(17) <= dmi_ctrl.dmihardreset.

**`dmi_ctrl.dmireset`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Records the DMIRESET control bit captured from tap_reg.dtmcs and influences error clearing; it is also reflected into tap_reg.dtmcs_nxt.
  - **roles** — holds DMI reset bit; feeds dtmcs next-state; affects error handling
  - **relationships** — **CAPTURES** → tap_reg.dtmcs; **SOURCES** → tap_reg.dtmcs_nxt
  - **evidence** — dmi_controller sets dmireset <= tap_reg.dtmcs(16) when dr_trigger.valid and tap_reg.ireg = addr_dtmcs_c; tap_reg.dtmcs_nxt(16) <= dmi_ctrl.dmireset.

**`dmi_ctrl.err`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Records an error condition (set when a busy transaction collides with a new DR_UPDATE request) and is included in the dmi packed word (replicated) for tap_reg.dmi_nxt.
  - **roles** — holds error indicator; influences dmi_nxt status bits
  - **relationships** — **CAPTURES** → tap_reg.ireg; **SOURCES** → tap_reg.dmi_nxt
  - **evidence** — dmi_controller sets err <= '1' when busy='1' and dr_trigger.valid and tap_reg.ireg = addr_dmi_c; tap_reg.dmi_nxt uses replicate_f(dmi_ctrl.err,2).

**`dmi_ctrl.op`** — neorv32_debug_dtm · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Holds the 2-bit DMI operation to request (default nop each cycle); it is overridden with tap_reg.dmi(1 downto 0) when a valid DMI request is started and is forwarded to dmi_req_o.op.
  - **roles** — holds DMI op code; drives dmi_req_o.op
  - **relationships** — **CAPTURES** → tap_reg.dmi; **SOURCES** → dmi_req_o.op
  - **evidence** — dmi_controller assigns dmi_ctrl.op <= dmi_req_nop_c and conditionally <= tap_reg.dmi(1 downto 0); concurrent dmi_req_o.op <= dmi_ctrl.op.

**`dmi_ctrl.rdata`** — neorv32_debug_dtm · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Captures read data from the external DMI response (dmi_rsp_i.data) while busy and supplies those bits into tap_reg.dmi_nxt so they can be shifted out on subsequent DR_CAPTURE.
  - **roles** — holds response read data; feeds tap_reg.dmi_nxt
  - **relationships** — **CAPTURES** → dmi_rsp_i.data; **SOURCES** → tap_reg.dmi_nxt
  - **evidence** — In dmi_controller else branch: dmi_ctrl.rdata <= dmi_rsp_i.data; tap_reg.dmi_nxt concatenates dmi_ctrl.rdata.

**`dmi_ctrl.wdata`** — neorv32_debug_dtm · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Captures the write-data slice from tap_reg.dmi when a request is started and provides the 32-bit data to the external DMI via dmi_req_o.data.
  - **roles** — holds write data; drives dmi_req_o.data
  - **relationships** — **CAPTURES** → tap_reg.dmi; **SOURCES** → dmi_req_o.data
  - **evidence** — dmi_controller assigns dmi_ctrl.wdata <= tap_reg.dmi(33 downto 02) when starting a request; dmi_req_o.data <= dmi_ctrl.wdata.

**`dr_trigger`** — neorv32_debug_dtm · `dr_trigger_t`
  - **functionality** — Aggregates a 2-bit shift register sreg and a derived valid flag; sreg is clocked to detect DR_UPDATE events and valid is derived combinationally for use by the dmi_controller.
  - **roles** — detects DR_UPDATE events; provides trigger valid signal; aggregates trigger fields
  - **relationships** — **AGGREGATES** → dr_trigger.sreg, dr_trigger.valid
  - **evidence** — dr_trigger record declared; sreg assigned in update_trigger process and valid computed concurrently.

**`dr_trigger.sreg`** — neorv32_debug_dtm · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Is clocked on clk_i and captures a '1' when tap_ctrl_state = DR_UPDATE then shifts the bit through sreg to form a one-cycle pulse pattern used to derive dr_trigger.valid.
  - **roles** — holds update detection shift; captures DR_UPDATE events
  - **relationships** — **CAPTURES** → tap_ctrl_state; **SOURCES** → dr_trigger.valid
  - **evidence** — update_trigger process sets dr_trigger.sreg(0) <= '1' when tap_ctrl_state = DR_UPDATE and shifts sreg(1) <= sreg(0).

**`dr_trigger.valid`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Is a combinational flag that is '1' when dr_trigger.sreg equals "01" (one-cycle pulse) and is used to gate dmi_controller actions such as capturing dtmcs/dmi and initiating DMI operations.
  - **roles** — trigger pulse; gates DMI controller actions
  - **relationships** — **DERIVES_FROM** → dr_trigger.sreg; **GATES** → dmi_ctrl.dmireset, dmi_ctrl.dmihardreset, dmi_ctrl.err, dmi_ctrl.addr, dmi_ctrl.wdata, dmi_ctrl.op, dmi_ctrl.busy
  - **evidence** — dr_trigger.valid <= '1' when (dr_trigger.sreg = "01") else '0'; dmi_controller tests dr_trigger.valid to enable various updates.

**`tap_ctrl_state`** — neorv32_debug_dtm · `tap_ctrl_state_t`
  - **functionality** — Holds the current TAP state and updates on clk_i when tck rising is detected; tap_sync.tms chooses the next state and the current state enables IR/DR capture/shift/update behaviors.
  - **roles** — holds TAP FSM state; governs DR/IR capture/shift/update actions; registered control signal
  - **relationships** — **SEQUENCES** → clk_i; **GATES** → dr_trigger.sreg, tap_reg.ireg, tap_reg.idcode, tap_reg.dtmcs, tap_reg.dmi, tap_reg.bypass, jtag_tdo_o
  - **evidence** — tap_control updates tap_ctrl_state on rising_edge(clk_i) when tap_sync.tck_rising='1'; reg_access and update_trigger test tap_ctrl_state to drive registers.

**`tap_reg`** — neorv32_debug_dtm · `tap_reg_t`
  - **functionality** — Aggregates instruction register, bypass, idcode, dtmcs and dmi registers and their next-state signals; individual fields are captured in reg_access or derived concurrently.
  - **roles** — holds TAP registers collectively; aggregates IR/DR storage; carrier for register fields
  - **relationships** — **AGGREGATES** → tap_reg.ireg, tap_reg.bypass, tap_reg.idcode, tap_reg.dtmcs, tap_reg.dtmcs_nxt, tap_reg.dmi, tap_reg.dmi_nxt
  - **evidence** — tap_reg record declared and individual fields assigned in reg_access and by concurrent assigns (dtmcs_nxt, dmi_nxt).

**`tap_reg.bypass`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Holds the bypass bit captured/shifting in DR_SHIFT (others case) and is provided on jtag_tdo_o when the IR selects the bypass instruction.
  - **roles** — holds bypass bit; feeds jtag_tdo_o when selected; updated by serial input
  - **relationships** — **CAPTURES** → tap_sync.tdi; **SOURCES** → jtag_tdo_o
  - **evidence** — reg_access sets tap_reg.bypass <= '0' on reset and tap_reg.bypass <= tap_sync.tdi in DR_SHIFT; jtag_tdo_o <= tap_reg.bypass when others.

**`tap_reg.dmi`** — neorv32_debug_dtm · `std_ulogic_vector((7+32+2)-1 downto 0)`
  - **functionality** — Holds the concatenated DMI request/response field bits; it is captured from tap_reg.dmi_nxt on DR_CAPTURE or shifted in DR_SHIFT, and its slices supply dmi_ctrl.addr,wdata and op and feed jtag_tdo_o LSB.
  - **roles** — holds packed DMI word; source for dmi_ctrl fields; feeds jtag_tdo_o when selected
  - **relationships** — **CAPTURES** → tap_reg.dmi_nxt, tap_sync.tdi; **SLICES** → dmi_ctrl.addr; **SLICES** → dmi_ctrl.wdata; **SLICES** → dmi_ctrl.op; **SOURCES** → jtag_tdo_o
  - **evidence** — reg_access sets tap_reg.dmi <= tap_reg.dmi_nxt in DR_CAPTURE and shifts from tap_sync.tdi in DR_SHIFT; dmi_controller reads tap_reg.dmi slices to set dmi_ctrl.addr/wdata/op.

**`tap_reg.dmi_nxt`** — neorv32_debug_dtm · `std_ulogic_vector((7+32+2)-1 downto 0)`
  - **functionality** — Is the combinational concatenation of dmi_ctrl.addr, dmi_ctrl.rdata and replicated dmi_ctrl.err bits; it is captured into tap_reg.dmi on DR_CAPTURE.
  - **roles** — builds next DMI word; aggregates dmi_ctrl.addr,rdata,err into vector
  - **relationships** — **DERIVES_FROM** → dmi_ctrl.addr; **DERIVES_FROM** → dmi_ctrl.rdata; **DERIVES_FROM** → dmi_ctrl.err
  - **evidence** — Concurrent assignment: tap_reg.dmi_nxt <= dmi_ctrl.addr & dmi_ctrl.rdata & replicate_f(dmi_ctrl.err, 2).

**`tap_reg.dtmcs_nxt`** — neorv32_debug_dtm · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Is a combinationally-built next value for tap_reg.dtmcs assembled from constants, tap_reg.dmi_nxt bits and dmi_ctrl reset bits; it feeds tap_reg.dtmcs on DR_CAPTURE.
  - **roles** — next-state builder for dtmcs; aggregates dmi_ctrl and tap_reg.dmi_nxt fields
  - **relationships** — **DERIVES_FROM** → dmi_ctrl.dmihardreset; **DERIVES_FROM** → dmi_ctrl.dmireset; **DERIVES_FROM** → tap_reg.dmi_nxt
  - **evidence** — Concurrent assigns form tap_reg.dtmcs_nxt bits from constants, dmi_ctrl.dmihardreset, dmi_ctrl.dmireset and tap_reg.dmi_nxt slices.

**`tap_reg.idcode`** — neorv32_debug_dtm · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Holds the 32-bit IDCODE formed from generics on DR_CAPTURE or shifted from tap_sync.tdi during DR_SHIFT, and supplies its LSB to jtag_tdo_o when selected.
  - **roles** — holds IDCODE; feeds jtag_tdo_o when IDCODE selected
  - **relationships** — **CAPTURES** → tap_sync.tdi; **SOURCES** → jtag_tdo_o
  - **evidence** — reg_access assigns idcode <= IDCODE_VERSION & IDCODE_PARTID & IDCODE_MANID & '1' on DR_CAPTURE and shifts idcode <= tap_sync.tdi & idcode(...) in DR_SHIFT; jtag_tdo_o uses idcode(0).

**`tap_reg.ireg`** — neorv32_debug_dtm · `std_ulogic_vector(4 downto 0)`
  - **functionality** — Holds the current 5-bit IR; it is loaded with a default (addr_idcode_c) in reset/IR_CAPTURE, shifted from tap_sync.tdi during IR_SHIFT, and its value selects which DR (idcode, dtmcs, dmi, bypass) is active.
  - **roles** — holds current IR; selects DR via case; registered instruction
  - **relationships** — **CAPTURES** → tap_sync.tdi; **SELECTS** → tap_reg.idcode, tap_reg.dtmcs, tap_reg.dmi, tap_reg.bypass; **CONSTRAINS** → dmi_ctrl.dmireset, dmi_ctrl.dmihardreset, dmi_ctrl.err, dmi_ctrl.addr, dmi_ctrl.wdata, dmi_ctrl.op, dmi_ctrl.busy
  - **evidence** — reg_access sets tap_reg.ireg on LOGIC_RESET/IR_CAPTURE and shifts in IR_SHIFT; reg_access and dmi_controller use case/equals on tap_reg.ireg to select actions.

**`tap_sync`** — neorv32_debug_dtm · `tap_sync_t`
  - **functionality** — Aggregates the three-stage sampled vectors and derived edge/value signals (tck_ff, tdi_ff, tms_ff, tck_rising, tck_falling, tdi, tms); its fields are produced by the synchronizer and consumed by TAP control and shift logic.
  - **roles** — holds synchronizer fields; carries synchronized JTAG signals; aggregates derived edge and level signals
  - **relationships** — **AGGREGATES** → tap_sync.tck_ff, tap_sync.tdi_ff, tap_sync.tms_ff, tap_sync.tck_rising, tap_sync.tck_falling, tap_sync.tdi, tap_sync.tms
  - **evidence** — tap_sync record declared and its fields assigned in tap_synchronizer and concurrent assigns (tap_sync.tck_rising, tck_falling, tdi, tms).

**`tap_sync.tck_falling`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Is high when the sampled TCK transitions 1->0; it gates updates of the serial output jtag_tdo_o so the appropriate bit is presented on TDO on the falling edge.
  - **roles** — edge indicator; gates TDO updates
  - **relationships** — **DERIVES_FROM** → tap_sync.tck_ff; **GATES** → jtag_tdo_o
  - **evidence** — Concurrent assign: tap_sync.tck_falling <= '1' when (tap_sync.tck_ff(2 downto 1) = "10") else '0'; used in reg_access under "if (tap_sync.tck_falling = '1') then".

**`tap_sync.tck_ff`** — neorv32_debug_dtm · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Captures successive jtag_tck_i samples into a 3-bit shift register on clk_i; its bits are used to detect rising/falling TCK edges.
  - **roles** — sample shift-register; holds recent TCK samples; feeds edge detectors
  - **relationships** — **CAPTURES** → jtag_tck_i; **SOURCES** → tap_sync.tck_rising, tap_sync.tck_falling
  - **evidence** — Assigned in tap_synchronizer: tap_sync.tck_ff <= tap_sync.tck_ff(1 downto 0) & jtag_tck_i; used by tck_rising/tck_falling concurrent assigns.

**`tap_sync.tck_rising`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Is high when the sampled TCK transitioned 0->1 (tap_sync.tck_ff(2 downto 1) = "01"); it enables TAP control and shift/capture actions when asserted.
  - **roles** — edge indicator; enables TAP state transitions and shifts; gates register updates
  - **relationships** — **DERIVES_FROM** → tap_sync.tck_ff; **GATES** → tap_ctrl_state, tap_reg.ireg, tap_reg.idcode, tap_reg.dtmcs, tap_reg.dmi
  - **evidence** — Concurrent assign: tap_sync.tck_rising <= '1' when (tap_sync.tck_ff(2 downto 1) = "01") else '0'; used as condition in tap_control and reg_access.

**`tap_sync.tdi`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Holds the synchronized TDI bit (tap_sync.tdi_ff(2)) and supplies it as the serial input to IR/DR shift operations and bypass updates.
  - **roles** — synchronized TDI; feeds shift operations; carries sampled serial bit
  - **relationships** — **DERIVES_FROM** → tap_sync.tdi_ff; **SOURCES** → tap_reg.ireg, tap_reg.idcode, tap_reg.dtmcs, tap_reg.dmi, tap_reg.bypass
  - **evidence** — tap_sync.tdi <= tap_sync.tdi_ff(2); tap_sync.tdi used as RHS in reg_access shifts (tap_reg.* <= tap_sync.tdi & ...).

**`tap_sync.tdi_ff`** — neorv32_debug_dtm · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Samples jtag_tdi_i into a 3-bit shift register on clk_i; the most-significant stage provides the synchronized serial data bit tap_sync.tdi for IR/DR shifts.
  - **roles** — sample shift-register; holds recent TDI samples; feeds tap_sync.tdi
  - **relationships** — **CAPTURES** → jtag_tdi_i; **SOURCES** → tap_sync.tdi
  - **evidence** — tap_synchronizer shifts jtag_tdi_i into tap_sync.tdi_ff; tap_sync.tdi <= tap_sync.tdi_ff(2).

**`tap_sync.tms`** — neorv32_debug_dtm · `std_ulogic`
  - **functionality** — Provides the synchronized JTAG TMS value (tap_sync.tms_ff(2)) to the TAP controller; its value selects next TAP state in tap_control.
  - **roles** — synchronized TMS; governs TAP state transitions
  - **relationships** — **DERIVES_FROM** → tap_sync.tms_ff; **GATES** → tap_ctrl_state
  - **evidence** — tap_sync.tms <= tap_sync.tms_ff(2); tap_sync.tms appears in many conditions in tap_control case branches.

**`tap_sync.tms_ff`** — neorv32_debug_dtm · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Samples jtag_tms_i into a 3-bit shift register on clk_i; the top stage produces tap_sync.tms which the TAP controller uses to choose state transitions.
  - **roles** — sample shift-register; holds recent TMS samples; feeds tap_sync.tms
  - **relationships** — **CAPTURES** → jtag_tms_i; **SOURCES** → tap_sync.tms
  - **evidence** — tap_synchronizer shifts jtag_tms_i into tap_sync.tms_ff; tap_sync.tms <= tap_sync.tms_ff(2).


## neorv32_hwspinlock  (19 non-assets)

### ports

**`bus_req_i`** — neorv32_hwspinlock · `bus_req_t`
  - **functionality** — Record carrying bus request fields; the aggregate itself is not used as a whole in this source, its individual fields are read and acted upon instead.
  - **roles** — input record (fields consumed separately)
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — Only bus_req_i's fields (addr, stb, rw, etc.) are referenced in comparisons and assignments; no whole-record use appears.

**`bus_req_i.addr`** — neorv32_hwspinlock · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies address bits used to decode which spinlock index is selected (addr(6 downto 2)) and to choose between masked or full responses (addr(7)). It therefore selects sel bits and gates lock/read behavior.
  - **roles** — address decoder input; selects indexed lock; gates masked/full read
  - **relationships** — **SELECTS** → sel; **GATES** → lock_q; **GATES** → bus_rsp_o.data
  - **evidence** — sel(i) <= '1' when (bus_req_i.addr(6 downto 2) = to_unsigned(i,5)) else '0'; if (bus_req_i.addr(7) = '0') then branches in processes.

**`bus_req_i.amo`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — Declared AMO flag but not referenced in this source; the entity ignores it.
  - **roles** — unused request field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No usage of bus_req_i.amo in the provided code.

**`bus_req_i.amoop`** — neorv32_hwspinlock · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared AMO operation bits but not read or used here; the entity's logic does not reference them.
  - **roles** — unused request field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — bus_req_i.amoop is not present in any expression or assignment.

**`bus_req_i.ben`** — neorv32_hwspinlock · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared byte-enable field but not read or used in this entity's source; no logic depends on it here.
  - **roles** — unused request field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — bus_req_i.ben does not appear in any assignment, condition or expression.

**`bus_req_i.data`** — neorv32_hwspinlock · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Declared data field of the bus request but not referenced anywhere in this source; no logic reads or forwards it here.
  - **roles** — unused request field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.data in the processes or concurrent statements.

**`bus_req_i.debug`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — Declared debug flag but unused in the entity's logic; it is neither tested nor forwarded here.
  - **roles** — unused request field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — bus_req_i.debug does not appear in any condition or assignment.

**`bus_req_i.fence`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — Declared fence flag but not referenced in this entity; no logic consumes it here.
  - **roles** — unused request field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — bus_req_i.fence is absent from all conditions and assignments.

**`bus_req_i.lock`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — Declared lock control bit but not used in this source; lock control is implemented from addr/rw/stb rather than this field here.
  - **roles** — unused request field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — bus_req_i.lock is not referenced in the processes or concurrent assignment.

**`bus_req_i.priv`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — Declared privilege indicator but not referenced in this source; the entity does not consume or forward it here.
  - **roles** — unused request field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.priv in the code.

**`bus_req_i.rw`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — Supplies the read/write bit used to set a lock bit (lock_q <= not bus_req_i.rw) and is tested to enable read-response data generation (rw = '0').
  - **roles** — operation type input; drives lock updates; gates read response
  - **relationships** — **SOURCES** → lock_q; **GATES** → bus_rsp_o.data
  - **evidence** — lock_q(i) <= not bus_req_i.rw assigned in spinlock process; bus_response tests (bus_req_i.rw = '0') to drive data output.

**`bus_req_i.src`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — Declared source field of the request but not used anywhere in this entity's source; no logic reads it.
  - **roles** — unused request field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — bus_req_i.src is not referenced in assignments or conditions.

**`bus_req_i.stb`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — Acts as the bus transaction enable: when '1' it enables lock updates and response generation; its value is also captured into bus_rsp_o.ack on the next clock edge.
  - **roles** — transaction enable; gates updates; supplies ack
  - **relationships** — **SOURCES** → bus_rsp_o.ack; **GATES** → lock_q; **GATES** → bus_rsp_o.data
  - **evidence** — Condition (bus_req_i.stb = '1') guards lock_q update and data-response assignments; bus_rsp_o.ack <= bus_req_i.stb in bus_response process.

**`bus_rsp_o`** — neorv32_hwspinlock · `bus_rsp_t`
  - **functionality** — Constructs and presents the response record to the outside: its fields are produced in the clocked bus_response process from bus_req_i.stb, constants, and lock_q/sel and then exported off-chip.
  - **roles** — output response record; holds response fields across cycles; exports response
  - **relationships** — **EXPORTS** → _(none)_; **CAPTURES** → bus_req_i.stb, lock_q, sel
  - **evidence** — bus_response process assigns bus_rsp_o fields from bus_req_i.stb, constants and lock_q/sel and the record is output from the entity.

**`bus_rsp_o.ack`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — Captured from bus_req_i.stb on the rising clock edge and presented as the ack output; reset is provided by the response reset value in the reset branch.
  - **roles** — response ack output; captures transaction strobe; exported field
  - **relationships** — **CAPTURES** → bus_req_i.stb; **EXPORTS** → _(none)_
  - **evidence** — bus_rsp_o.ack <= bus_req_i.stb inside the bus_response process on rising_edge(clk_i).

**`bus_rsp_o.data`** — neorv32_hwspinlock · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Holds the read response data captured each clock: when reading it captures either lock_q masked by sel (addr(7)=0) or the full lock_q (addr(7)=1), and then exports this vector as the response data.
  - **roles** — response data output; captures lock state; exported field
  - **relationships** — **CAPTURES** → lock_q, sel; **EXPORTS** → _(none)_
  - **evidence** — bus_rsp_o.data <= lock_q and sel or bus_rsp_o.data <= lock_q inside bus_response process when bus_req_i.rw = '0'.

**`bus_rsp_o.err`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — Assigned a constant '0' each clock and forwarded to the outside as the err output; it does not depend on any internal declared signal.
  - **roles** — response error output; exported field
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — bus_rsp_o.err <= '0' in bus_response process; no declared source supplies its value.

**`clk_i`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — Supplies the rising edge timing for the entity's clocked processes; it sequences updates to lock_q and bus_rsp_o on rising edges. It is the process clock for both spinlock and response logic.
  - **roles** — clock input; synchronises register updates
  - **relationships** — **SEQUENCES** → lock_q, bus_rsp_o
  - **evidence** — rising_edge(clk_i) used in both spinlock and bus_response processes to update lock_q and bus_rsp_o.

**`rstn_i`** — neorv32_hwspinlock · `std_ulogic`
  - **functionality** — When low it resets lock_q bits and the bus_rsp_o response record; it is tested in the reset branch of the clocked processes to initialize state. It overrides normal updates during reset.
  - **roles** — reset input; initialises registers
  - **relationships** — **SEQUENCES** → lock_q, bus_rsp_o
  - **evidence** — if (rstn_i = '0') then branches in spinlock and bus_response processes set lock_q and bus_rsp_o to initial values.


## neorv32_imem  (24 non-assets)

### ports

**`bus_req_i`** — neorv32_imem · `bus_req_t`
  - **functionality** — Record bundle carrying bus request fields; the source fields (addr,data,ben,stb,rw) are consumed individually by internal logic rather than the aggregate itself.
  - **roles** — input bundle; forwards fields to internal logic
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — Only individual fields (bus_req_i.addr, .data, .ben, .stb, .rw) are referenced throughout the source (e.g. addr <= unsigned(bus_req_i.addr(...))).

**`bus_req_i.addr`** — neorv32_imem · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies the requested byte address bits; the slice addr(addr_hi_c downto 2) is converted to an unsigned index and assigned to internal addr, which then indexes memories and may be captured into addr_ff.
  - **roles** — address operand; carries bus address bits into entity
  - **relationships** — **SOURCES** → addr
  - **evidence** — addr <= unsigned(bus_req_i.addr(addr_hi_c downto 2));

**`bus_req_i.amo`** — neorv32_imem · `std_ulogic`
  - **functionality** — Declared AMO indication field; it is not referenced in this entity's source and is unused here.
  - **roles** — unused input field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.amo in the source.

**`bus_req_i.amoop`** — neorv32_imem · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared AMO operation field; not referenced anywhere in this source and therefore unused.
  - **roles** — unused input field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.amoop in the source.

**`bus_req_i.ben`** — neorv32_imem · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Its individual bits gate which byte lanes are written: ben(0..3) are tested and, when '1' with stb and rw, allow the corresponding mem_ram_bN byte to be written from bus_req_i.data.
  - **roles** — write byte-enable; qualifies memory byte writes
  - **relationships** — **GATES** → mem_ram_b0; **GATES** → mem_ram_b1; **GATES** → mem_ram_b2; **GATES** → mem_ram_b3
  - **evidence** — if (bus_req_i.ben(0) = '1') then mem_ram_b0(...) <= bus_req_i.data(7 downto 0); (and similar for ben(1..3)).

**`bus_req_i.data`** — neorv32_imem · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the 32-bit write data that supplies byte slices written into mem_ram_b0..3 when writes occur; each byte slice is captured into the corresponding mem_ram_bN element on a write.
  - **roles** — write-data operand; feeds memory byte writes
  - **relationships** — **SOURCES** → mem_ram_b0; **SOURCES** → mem_ram_b1; **SOURCES** → mem_ram_b2; **SOURCES** → mem_ram_b3
  - **evidence** — Assignments like mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0) inside mem_access process.

**`bus_req_i.debug`** — neorv32_imem · `std_ulogic`
  - **functionality** — Declared debug field; not referenced in this entity's source and therefore unused here.
  - **roles** — unused input field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.debug in the source.

**`bus_req_i.fence`** — neorv32_imem · `std_ulogic`
  - **functionality** — Declared fence field; not referenced in this source and unused by the entity.
  - **roles** — unused input field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.fence in the source.

**`bus_req_i.lock`** — neorv32_imem · `std_ulogic`
  - **functionality** — Declared lock field; not referenced in this source and unused by the entity.
  - **roles** — unused input field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.lock in the source.

**`bus_req_i.priv`** — neorv32_imem · `std_ulogic`
  - **functionality** — Declared privilege field; not referenced in this entity's source and therefore unused here.
  - **roles** — unused input field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.priv in the source.

**`bus_req_i.rw`** — neorv32_imem · `std_ulogic`
  - **functionality** — Distinguishes reads from writes; used together with stb to enable memory writes, and sampled (negated) with stb to form rden and to influence bus_rsp_o.ack generation.
  - **roles** — read/write control; qualifies write vs read operations
  - **relationships** — **GATES** → mem_ram_b0, mem_ram_b1, mem_ram_b2, mem_ram_b3; **SOURCES** → rden, bus_rsp_o.ack
  - **evidence** — Used in write condition and in rden <= bus_req_i.stb and (not bus_req_i.rw); bus_rsp_o.ack uses (not bus_req_i.rw) when IMEM_INIT.

**`bus_req_i.src`** — neorv32_imem · `std_ulogic`
  - **functionality** — Declared request source field; not referenced anywhere in this source, so the entity neither consumes nor forwards it.
  - **roles** — unused input field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.src in the source.

**`bus_req_i.stb`** — neorv32_imem · `std_ulogic`
  - **functionality** — Indicates an active bus transfer; it gates memory writes together with rw and ben, and it is sampled to form rden and to generate bus_rsp_o.ack according to IMEM_INIT.
  - **roles** — transfer strobe; qualifies writes and reads
  - **relationships** — **GATES** → mem_ram_b0, mem_ram_b1, mem_ram_b2, mem_ram_b3; **SOURCES** → rden, bus_rsp_o.ack
  - **evidence** — Used in conditions "if (bus_req_i.stb = '1') and (bus_req_i.rw = '1')" and in bus_feedback assignments for rden and bus_rsp_o.ack.

**`bus_rsp_o`** — neorv32_imem · `bus_rsp_t`
  - **functionality** — Output bundle carrying ack, err and data fields; the individual fields are driven inside this entity (ack registered, data and err driven concurrently), while the aggregate bus_rsp_o is not used as a whole.
  - **roles** — output bundle; forwards response fields to bus
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — Individual fields bus_rsp_o.ack, .data and .err are assigned separately (bus_rsp_o.data <= ..., bus_rsp_o.err <= '0', bus_rsp_o.ack <= ...).

**`bus_rsp_o.ack`** — neorv32_imem · `std_ulogic`
  - **functionality** — Registered output that is assigned in bus_feedback process from bus_req_i.stb and bus_req_i.rw (and reset to '0'); reports acceptance/acknowledge of read transfers according to IMEM_INIT.
  - **roles** — registered response flag; reports transfer acknowledgment
  - **relationships** — **CAPTURES** → bus_req_i.stb, bus_req_i.rw; **SEQUENCES** → clk_i, rstn_i
  - **evidence** — In bus_feedback: on reset ack <= '0'; on rising_edge(clk_i) ack <= bus_req_i.stb and (not bus_req_i.rw) or <= bus_req_i.stb (depending on IMEM_INIT).

**`bus_rsp_o.data`** — neorv32_imem · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Drives the response data bus from internal rdata when rden is '1', otherwise outputs zeros; thus its value is a function of rdata and the registered read-enable rden.
  - **roles** — combinational output data; carries read word to bus
  - **relationships** — **DERIVES_FROM** → rdata, rden
  - **evidence** — bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');

**`bus_rsp_o.err`** — neorv32_imem · `std_ulogic`
  - **functionality** — Constantly drives the error flag low; the entity does not derive it from any declared internal element.
  - **roles** — static error output
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — Concurrent assignment: bus_rsp_o.err  <= '0'.

**`clk_i`** — neorv32_imem · `std_ulogic`
  - **functionality** — Supplies the rising edge used by clocked processes; sequences updates of addr_ff, rdata (in some generates), mem_ram_b0..3 writes, rden and bus_rsp_o.ack. It times the entity's sequential behaviour.
  - **roles** — clock input; sequences register updates
  - **relationships** — **SEQUENCES** → addr_ff, rdata, mem_ram_b0, mem_ram_b1, mem_ram_b2, mem_ram_b3, rden, bus_rsp_o.ack
  - **evidence** — multiple processes with "if rising_edge(clk_i) then" assign addr_ff, rdata, mem_ram_b* and bus_feedback (lines with rising_edge(clk_i)).

**`rstn_i`** — neorv32_imem · `std_ulogic`
  - **functionality** — Acts as the asynchronous reset used by bus_feedback process; forces rden and bus_rsp_o.ack to '0' when asserted low, overriding their normal registered behaviour on reset.
  - **roles** — asynchronous reset input; overrides register values on reset
  - **relationships** — **SEQUENCES** → rden, bus_rsp_o.ack
  - **evidence** — bus_feedback process sensitivity list and "if (rstn_i = '0') then" branch sets rden and bus_rsp_o.ack to '0'.

### signals

**`addr_ff`** — neorv32_imem · `unsigned(index_size_f(IMEM_SIZE/4)-1 downto 0)`
  - **functionality** — Captures addr on the clock in alt_style branches (or is forced to zero in other generates) and provides a stable index (addr_ff) used for ROM/RAM reads into rdata.
  - **roles** — registered address; supplies delayed index to reads
  - **relationships** — **CAPTURES** → addr; **SOURCES** → rdata; **SELECTS** → mem_ram_b0, mem_ram_b1, mem_ram_b2, mem_ram_b3; **SEQUENCES** → clk_i
  - **evidence** — addr_ff <= addr on rising_edge(clk_i) in alt_style generate; rdata <= mem_rom_c(to_integer(addr_ff)) and mem_ram_bN(to_integer(addr_ff)) used to form rdata.

**`mem_ram_b0`** — neorv32_imem · `mem8_t(0 to IMEM_SIZE/4-1)`
  - **functionality** — Stores the least-significant byte of each 32-bit memory word; on writes (stb and rw and ben(0)) it captures bus_req_i.data(7 downto 0), and on reads supplies rdata(7 downto 0) via indexed accesses.
  - **roles** — RAM byte lane 0; stores LSB of memory words; feeds rdata low byte
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → rdata
  - **evidence** — mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0) inside mem_access; rdata(7 downto 0) <= mem_ram_b0(to_integer(addr)).

**`mem_ram_b1`** — neorv32_imem · `mem8_t(0 to IMEM_SIZE/4-1)`
  - **functionality** — Stores the second byte of each 32-bit memory word; captures bus_req_i.data(15 downto 8) on writes gated by ben(1), and supplies rdata(15 downto 8) on reads.
  - **roles** — RAM byte lane 1; stores second byte; feeds rdata byte 1
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → rdata
  - **evidence** — mem_ram_b1(to_integer(addr)) <= bus_req_i.data(15 downto 8); rdata(15 downto 8) <= mem_ram_b1(to_integer(addr)).

**`mem_ram_b2`** — neorv32_imem · `mem8_t(0 to IMEM_SIZE/4-1)`
  - **functionality** — Stores the third byte of each 32-bit memory word; captures bus_req_i.data(23 downto 16) on writes gated by ben(2), and supplies rdata(23 downto 16) on reads.
  - **roles** — RAM byte lane 2; stores third byte; feeds rdata byte 2
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → rdata
  - **evidence** — mem_ram_b2(to_integer(addr)) <= bus_req_i.data(23 downto 16); rdata(23 downto 16) <= mem_ram_b2(to_integer(addr)).

**`mem_ram_b3`** — neorv32_imem · `mem8_t(0 to IMEM_SIZE/4-1)`
  - **functionality** — Stores the most-significant byte of each 32-bit memory word; captures bus_req_i.data(31 downto 24) on writes gated by ben(3), and supplies rdata(31 downto 24) on reads.
  - **roles** — RAM byte lane 3; stores MSB of memory words; feeds rdata high byte
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → rdata
  - **evidence** — mem_ram_b3(to_integer(addr)) <= bus_req_i.data(31 downto 24); rdata(31 downto 24) <= mem_ram_b3(to_integer(addr)).


## neorv32_spi  (58 non-assets)

### ports

**`bus_req_i`** — neorv32_spi · `bus_req_t`
  - **functionality** — Declared bus request record; the source fields of this record are consumed individually (stb, rw, addr, data). The whole record identifier itself is not read as an aggregate here.
  - **roles** — input bus record; fields consumed individually
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — Only member fields (bus_req_i.stb, .rw, .addr, .data) are referenced in the source; bus_req_i as whole is not used

**`bus_req_i.addr`** — neorv32_spi · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Consumes addr(2) to choose between control register space and FIFO data space and gates read/write operations; it controls whether ctrl fields or FIFO data are accessed and gates FIFO read/write enables.
  - **roles** — address selector; gates register vs FIFO access
  - **relationships** — **GATES** → ctrl, tx_fifo.we, rx_fifo.re, bus_rsp_o.data
  - **evidence** — if (bus_req_i.addr(2) = '0') then ... in bus_access; used in concurrent tx_fifo.we and rx_fifo.re when expressions

**`bus_req_i.amo`** — neorv32_spi · `std_ulogic`
  - **functionality** — Declared but not referenced in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.amo in the source

**`bus_req_i.amoop`** — neorv32_spi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared but not referenced in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.amoop in the source

**`bus_req_i.ben`** — neorv32_spi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared but not referenced anywhere in this source; no functional effect inside this entity.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.ben in the source

**`bus_req_i.data`** — neorv32_spi · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies write-data bits that are captured into ctrl fields on bus writes and supplies the two slices used to form tx_fifo.wdata (data(31) and data(7 downto 0)).
  - **roles** — write-data source; feeds control and TX FIFO
  - **relationships** — **SOURCES** → ctrl.enable, ctrl.cpha, ctrl.cpol, ctrl.prsc, ctrl.cdiv, ctrl.highspeed, ctrl.irq_rx_avail, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.irq_idle; **SOURCES** → tx_fifo.wdata; **SOURCES** → tx_fifo.wdata
  - **evidence** — bus_access assigns ctrl.* <= bus_req_i.data(...); tx_fifo.wdata <= bus_req_i.data(31) & bus_req_i.data(7 downto 0)

**`bus_req_i.debug`** — neorv32_spi · `std_ulogic`
  - **functionality** — Declared but not referenced in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.debug in the source

**`bus_req_i.fence`** — neorv32_spi · `std_ulogic`
  - **functionality** — Declared but not referenced in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.fence in the source

**`bus_req_i.lock`** — neorv32_spi · `std_ulogic`
  - **functionality** — Declared but not referenced in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.lock in the source

**`bus_req_i.priv`** — neorv32_spi · `std_ulogic`
  - **functionality** — Declared but not referenced in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.priv in the source

**`bus_req_i.rw`** — neorv32_spi · `std_ulogic`
  - **functionality** — Chooses the write-versus-read path in bus_access and gates FIFO read/write enables; it governs whether ctrl fields are written or bus_rsp_o.data is driven from FIFOs.
  - **roles** — access direction selector; gates read/write branches
  - **relationships** — **GATES** → ctrl, tx_fifo.we, rx_fifo.re, bus_rsp_o.data
  - **evidence** — if (bus_req_i.rw = '1') then ... else ... in bus_access; used in when-expressions for tx_fifo.we and rx_fifo.re

**`bus_req_i.src`** — neorv32_spi · `std_ulogic`
  - **functionality** — Declared but not used in this entity.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.src in the source

**`bus_req_i.stb`** — neorv32_spi · `std_ulogic`
  - **functionality** — Gates bus-access activity and supplies the acknowledge value; it gates write/read handling, drives bus_rsp_o.ack and contributes to FIFO enables (tx_fifo.we, rx_fifo.re).
  - **roles** — access qualifier; gates writes/reads; supplies ack
  - **relationships** — **GATES** → ctrl, tx_fifo.we, rx_fifo.re, bus_rsp_o.data; **SOURCES** → bus_rsp_o.ack
  - **evidence** — if (bus_req_i.stb = '1') then ... in bus_access; tx_fifo.we and rx_fifo.re when-expressions use bus_req_i.stb; bus_rsp_o.ack <= bus_req_i.stb

**`bus_rsp_o`** — neorv32_spi · `bus_rsp_t`
  - **functionality** — Constructs the response record each clock from ack, err and data subfields; the record is assembled from internal bits (bus_rsp_o.ack, .err, .data) driven in bus_access.
  - **roles** — response aggregator; holds ack/err/data; exports bus reply
  - **relationships** — **AGGREGATES** → bus_rsp_o.ack, bus_rsp_o.err, bus_rsp_o.data
  - **evidence** — bus_rsp_o <= rsp_terminate_c at reset; individual bus_rsp_o.* assigned in bus_access process

**`bus_rsp_o.ack`** — neorv32_spi · `std_ulogic`
  - **functionality** — Captured each rising edge from bus_req_i.stb and exported to the bus; provides the acknowledge value derived directly from bus_req_i.stb.
  - **roles** — holds ack across cycles; exports acknowledge
  - **relationships** — **CAPTURES** → bus_req_i.stb; **EXPORTS** → _(none)_
  - **evidence** — bus_rsp_o.ack <= bus_req_i.stb inside rising_edge(clk_i) in bus_access

**`bus_rsp_o.data`** — neorv32_spi · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Holds readback and status bits constructed from ctrl fields, FIFO status and rx data; individual bits are carried or derived from ctrl.*, rx_fifo.rdata and fifo status signals to present status or read data on the bus.
  - **roles** — holds read data/status; exports internal status; assembled from multiple sources
  - **relationships** — **CARRIES** → ctrl.enable, ctrl.cpha, ctrl.cpol, ctrl.prsc, ctrl.cdiv, ctrl.highspeed, ctrl.irq_rx_avail, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.irq_idle; **CARRIES** → rx_fifo.avail; **DERIVES_FROM** → tx_fifo.avail, tx_fifo.half, tx_fifo.free, rtx_engine.busy; **CARRIES** → rx_fifo.rdata
  - **evidence** — bus_access assigns individual bus_rsp_o.data(bits) <= ctrl.* or fifo signals; bus_rsp_o.data(7 downto 0) <= rx_fifo.rdata(7 downto 0)

**`bus_rsp_o.err`** — neorv32_spi · `std_ulogic`
  - **functionality** — Captured each cycle and driven to the constant '0' in the bus_access process; reports no error from this entity (assigned literal).
  - **roles** — holds error flag; exports error state
  - **relationships** — **DERIVES_FROM** → _(none)_
  - **evidence** — bus_rsp_o.err <= '0' inside rising_edge(clk_i) in bus_access (assigned constant)

**`clk_i`** — neorv32_spi · `std_ulogic`
  - **functionality** — Supplies the rising_edge timing used by all clocked processes; sequences updates of bus_access, irq_generator, transceiver, chip_select and clock_generator registers such as ctrl, bus_rsp_o, irq_o, rtx_engine, spi_csn_o, spi_clk_en and cdiv_cnt.
  - **roles** — clock source; sequences registers; timing for state machines
  - **relationships** — **SEQUENCES** → bus_rsp_o, ctrl, irq_o, rtx_engine, spi_csn_o, spi_clk_en, cdiv_cnt
  - **evidence** — rising_edge(clk_i) used in bus_access, irq_generator, transceiver, chip_select, clock_generator processes

**`clkgen_i`** — neorv32_spi · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Supplies bits indexed by ctrl.prsc to the clock generator; the selected clkgen_i bit participates in the condition that enables spi_clk_en.
  - **roles** — clock selection input; source for clock gating
  - **relationships** — **SOURCES** → spi_clk_en
  - **evidence** — clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1' used in clock_generator condition

**`rstn_i`** — neorv32_spi · `std_ulogic`
  - **functionality** — Supplies asynchronous reset condition used by all clocked processes; on rstn_i='0' those processes reset ctrl, bus_rsp_o, irq_o, rtx_engine fields, spi_csn_o, spi_clk_en and cdiv_cnt.
  - **roles** — reset source; initializes registers
  - **relationships** — **SEQUENCES** → bus_rsp_o, ctrl, irq_o, rtx_engine, spi_csn_o, spi_clk_en, cdiv_cnt
  - **evidence** — if (rstn_i = '0') then branches in all clocked processes (bus_access, irq_generator, transceiver, chip_select, clock_generator)

**`spi_clk_o`** — neorv32_spi · `std_ulogic`
  - **functionality** — Driven directly from the internal rtx_engine.sck signal and exported off-chip; presents the engineered SPI SCK to the external pins.
  - **roles** — exports SPI clock; driven by engine
  - **relationships** — **CARRIES** → rtx_engine.sck; **EXPORTS** → _(none)_
  - **evidence** — spi_clk_o <= rtx_engine.sck (concurrent assignment)

### signals

**`cdiv_cnt`** — neorv32_spi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Counts up each cycle when ctrl.enable and the selected clkgen bit or highspeed condition allow; compared against ctrl.cdiv to generate a spi_clk_en pulse then resets to zero.
  - **roles** — holds divider count across cycles; compared to ctrl.cdiv
  - **relationships** — **CAPTURES** → cdiv_cnt; **CONSTRAINS** → spi_clk_en; **CONSTRAINS** → ctrl.cdiv
  - **evidence** — cdiv_cnt <= std_ulogic_vector(unsigned(cdiv_cnt) + 1) and compared (cdiv_cnt = ctrl.cdiv) in clock_generator

**`ctrl`** — neorv32_spi · `ctrl_t`
  - **functionality** — Aggregate register built from bus writes of bus_req_i.data; individual fields are captured on bus writes and used throughout the SPI logic (clock gen, transceiver and IRQ generator).
  - **roles** — holds configuration across cycles; forwards fields to logic; provides control for clocking and IRQs
  - **relationships** — **AGGREGATES** → ctrl.enable, ctrl.cpha, ctrl.cpol, ctrl.prsc, ctrl.cdiv, ctrl.highspeed, ctrl.irq_rx_avail, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.irq_idle
  - **evidence** — ctrl fields assigned in bus_access process from bus_req_i.data and reset at rstn_i

**`ctrl.cpha`** — neorv32_spi · `std_ulogic`
  - **functionality** — Captured from bus writes and used by the transceiver to influence sck transitions and sample timing; appears both as a condition and as an operand in sck assignments.
  - **roles** — holds phase config; governs sck generation and sampling
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → rtx_engine.sck; **SOURCES** → rtx_engine.sck
  - **evidence** — ctrl.cpha <= bus_req_i.data(ctrl_cpha_c) in bus_access; used in transceiver (if ctrl.cpha = '1', and in expressions ctrl.cpha xor ctrl.cpol)

**`ctrl.cpol`** — neorv32_spi · `std_ulogic`
  - **functionality** — Captured from bus writes and used to set the idle SCK level and to compute driven SCK values in the transceiver.
  - **roles** — holds polarity config; drives idle and active SCK levels
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → rtx_engine.sck
  - **evidence** — ctrl.cpol <= bus_req_i.data(ctrl_cpol_c) in bus_access; used in transceiver assignments to rtx_engine.sck

**`ctrl.highspeed`** — neorv32_spi · `std_ulogic`
  - **functionality** — Captured from bus writes and used together with the selected clkgen_i bit to immediately allow spi_clk_en pulses when set.
  - **roles** — holds highspeed flag; enables faster clock gating
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → spi_clk_en
  - **evidence** — ctrl.highspeed <= bus_req_i.data(ctrl_highspeed_c) in bus_access; used in clock_generator condition with clkgen_i(...)

**`ctrl.irq_idle`** — neorv32_spi · `std_ulogic`
  - **functionality** — Captured from bus writes and used in irq_o to enable idle-condition IRQ when TX FIFO empty and rtx_engine not busy.
  - **roles** — holds idle IRQ enable; qualifies irq generation on idle
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → irq_o
  - **evidence** — ctrl.irq_idle <= bus_req_i.data(ctrl_irq_idle_c); used in irq_generator expression

**`ctrl.irq_rx_avail`** — neorv32_spi · `std_ulogic`
  - **functionality** — Captured from bus writes and used in the irq_o expression to enable IRQ when RX FIFO has data.
  - **roles** — holds RX-available IRQ enable; qualifies irq generation
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → irq_o
  - **evidence** — ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c); used in irq_o <= ctrl.enable and (ctrl.irq_rx_avail and rx_fifo.avail) ...

**`ctrl.irq_tx_empty`** — neorv32_spi · `std_ulogic`
  - **functionality** — Captured from bus writes and used in irq_o to qualify an IRQ when TX FIFO is empty.
  - **roles** — holds TX-empty IRQ enable; qualifies irq generation
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → irq_o
  - **evidence** — ctrl.irq_tx_empty <= bus_req_i.data(ctrl_irq_tx_empty_c); used in irq_generator expression

**`ctrl.irq_tx_nhalf`** — neorv32_spi · `std_ulogic`
  - **functionality** — Captured from bus writes and used in irq_o to qualify an IRQ when TX FIFO not at half level.
  - **roles** — holds TX-nhalf IRQ enable; qualifies irq generation
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → irq_o
  - **evidence** — ctrl.irq_tx_nhalf <= bus_req_i.data(ctrl_irq_tx_nhalf_c); used in irq_generator expression

**`rtx_engine`** — neorv32_spi · `rtx_engine_t`
  - **functionality** — Record holding the state machine and its working registers (state, sreg, bitcnt, sdi_sync, sck, cs_ctrl, done); individual fields are updated in the transceiver process and used elsewhere (CS, RX FIFO, SPI outputs).
  - **roles** — holds transceiver state across cycles; forwards shifts and control to outputs
  - **relationships** — **AGGREGATES** → rtx_engine.state, rtx_engine.busy, rtx_engine.sreg, rtx_engine.bitcnt, rtx_engine.sdi_sync, rtx_engine.sck, rtx_engine.cs_ctrl, rtx_engine.done
  - **evidence** — rtx_engine fields assigned in transceiver process and used in chip_select, rx_fifo and spi outputs

**`rtx_engine.bitcnt`** — neorv32_spi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Incremented each relevant spi clock (when spi_clk_en) and tested to detect end-of-byte; used to decide last-bit behaviour and done set.
  - **roles** — counts bits during transfer; controls end-of-byte transitions
  - **relationships** — **CAPTURES** → rtx_engine.bitcnt; **CONSTRAINS** → rtx_engine.sreg, rtx_engine.done
  - **evidence** — rtx_engine.bitcnt <= std_ulogic_vector(unsigned(rtx_engine.bitcnt) + 1) in state "110"; tested if rtx_engine.bitcnt(3) = '1' in state "111"

**`rtx_engine.busy`** — neorv32_spi · `std_ulogic`
  - **functionality** — Combinationally derived from rtx_engine.state (non-zero low bits indicate activity); exposed to bus readback as part of ctrl_busy flag calculation.
  - **roles** — reflects engine activity; combinational status signal
  - **relationships** — **DERIVES_FROM** → rtx_engine.state
  - **evidence** — rtx_engine.busy <= '0' when (rtx_engine.state(1 downto 0) = "00") else '1' (concurrent)

**`rtx_engine.cs_ctrl`** — neorv32_spi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Captured from tx_fifo.rdata when a CS word is read and later used (bit3 as enable and bits2:0 as index) to select which spi_csn_o bit is asserted low.
  - **roles** — holds CS control; selects CS line
  - **relationships** — **CAPTURES** → tx_fifo.rdata; **GATES** → spi_csn_o
  - **evidence** — if tx_fifo.rdata(8) = '1' then rtx_engine.cs_ctrl <= tx_fifo.rdata(3 downto 0) in transceiver; chip_select uses rtx_engine.cs_ctrl(3) and rtx_engine.cs_ctrl(2 downto 0)

**`rtx_engine.done`** — neorv32_spi · `std_ulogic`
  - **functionality** — Set by the transceiver at the end of a byte and cleared each clock; its rising pulse causes writing into rx_fifo.we.
  - **roles** — one-cycle done indicator; enables RX FIFO write
  - **relationships** — **CAPTURES** → _(none)_; **SOURCES** → rx_fifo.we
  - **evidence** — rtx_engine.done <= '1' on final bit in state "111"; rx_fifo.we <= rtx_engine.done (concurrent)

**`rtx_engine.sck`** — neorv32_spi · `std_ulogic`
  - **functionality** — Registered internal clock line driven from ctrl.cpol/cpha logic in the transceiver and used to drive the external spi_clk_o output.
  - **roles** — holds SCK level across cycles; drives physical SCK output
  - **relationships** — **CAPTURES** → ctrl.cpol; **SOURCES** → spi_clk_o
  - **evidence** — rtx_engine.sck assigned variously from ctrl.cpol and (ctrl.cpha xor ctrl.cpol) in transceiver; spi_clk_o <= rtx_engine.sck

**`rtx_engine.sdi_sync`** — neorv32_spi · `std_ulogic`
  - **functionality** — Samples spi_dat_i into a registered signal during the transceiver sequence (on spi clock phases) and supplies the bit shifted into sreg.
  - **roles** — samples serial input; feeds shift register
  - **relationships** — **CAPTURES** → spi_dat_i; **SOURCES** → rtx_engine.sreg
  - **evidence** — rtx_engine.sdi_sync <= spi_dat_i in transceiver state "110"; used in sreg shift assignment

**`rtx_engine.sreg`** — neorv32_spi · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Holds the byte being shifted out/in; captured from tx_fifo.rdata on start, shifted in from rtx_engine.sdi_sync on bit transfers and feeds spi_dat_o and rx_fifo.wdata.
  - **roles** — holds shift data across cycles; supplies serial output bit; feeds RX FIFO on done
  - **relationships** — **CAPTURES** → tx_fifo.rdata; **CAPTURES** → rtx_engine.sdi_sync; **SOURCES** → spi_dat_o, rx_fifo.wdata
  - **evidence** — rtx_engine.sreg <= tx_fifo.rdata(7 downto 0) in state "100"; shifted via rtx_engine.sreg <= rtx_engine.sreg(6 downto 0) & rtx_engine.sdi_sync; rx_fifo.wdata <= '0' & rtx_engine.sreg

**`rtx_engine.state`** — neorv32_spi · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Captured and updated in the transceiver state machine; bit(2) is driven from ctrl.enable and the low bits select sub-states, which also select FIFO read and control flows.
  - **roles** — holds state across cycles; chooses transceiver actions; selects FIFO re
  - **relationships** — **CAPTURES** → ctrl.enable; **SELECTS** → tx_fifo.re; **SOURCES** → rtx_engine.busy
  - **evidence** — rtx_engine.state(2) <= ctrl.enable; case rtx_engine.state is ... controls behavior; tx_fifo.re <= '1' when (rtx_engine.state = "100")

**`rx_fifo`** — neorv32_spi · `fifo_t`
  - **functionality** — Aggregate of RX FIFO interface signals; instance provides rdata/avail/free/half and this entity drives we, wdata and re as its RX path.
  - **roles** — interface to RX FIFO instance; carries RX data and status
  - **relationships** — **AGGREGATES** → rx_fifo.we, rx_fifo.re, rx_fifo.wdata, rx_fifo.rdata, rx_fifo.avail, rx_fifo.free, rx_fifo.clear, rx_fifo.half
  - **evidence** — rx_fifo fields used in instance port map and in concurrent assignments

**`rx_fifo.avail`** — neorv32_spi · `std_ulogic`
  - **functionality** — Provided by the instance and used to indicate received-data availability in bus readback and in IRQ generation.
  - **roles** — status source; enables RX-available IRQ
  - **relationships** — **SOURCES** → bus_rsp_o.data, irq_o
  - **evidence** — bus_access uses rx_fifo.avail for ctrl_rx_avail readback; irq_generator uses rx_fifo.avail in irq expression

**`rx_fifo.clear`** — neorv32_spi · `std_ulogic`
  - **functionality** — Driven combinationally from ctrl.enable (negated) to clear the RX FIFO when the module is disabled.
  - **roles** — controls FIFO clear; driven by module enable
  - **relationships** — **DERIVES_FROM** → ctrl.enable
  - **evidence** — rx_fifo.clear <= not ctrl.enable (concurrent)

**`rx_fifo.free`** — neorv32_spi · `std_ulogic`
  - **functionality** — Provided by the instance; not referenced in this source other than via the instance (no explicit reads present here).
  - **roles** — unused here (instance-provided)
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — rx_fifo.free is part of FIFO port map but not referenced elsewhere in the source

**`rx_fifo.half`** — neorv32_spi · `std_ulogic`
  - **functionality** — Provided by the FIFO instance and available for readback; used for status but not otherwise processed in this source.
  - **roles** — status source
  - **relationships** — **SOURCES** → bus_rsp_o.data
  - **evidence** — rx_fifo.half is exposed via FIFO port map and reflected in bus_rsp_o.data for status

**`rx_fifo.rdata`** — neorv32_spi · `std_ulogic_vector(8 downto 0)`
  - **functionality** — Provided by the RX FIFO instance and read during bus reads to return the received byte on the bus.
  - **roles** — provides RX read word; feeds bus readback
  - **relationships** — **SOURCES** → bus_rsp_o.data
  - **evidence** — bus_access assigns bus_rsp_o.data(7 downto 0) <= rx_fifo.rdata(7 downto 0)

**`rx_fifo.re`** — neorv32_spi · `std_ulogic`
  - **functionality** — Derived combinationally from bus_req_i.stb, bus_req_i.rw and bus_req_i.addr(2); a bus read to the FIFO address asserts rx_fifo.re.
  - **roles** — drives RX FIFO read; gated by bus reads
  - **relationships** — **DERIVES_FROM** → bus_req_i.stb, bus_req_i.rw, bus_req_i.addr
  - **evidence** — rx_fifo.re <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '0') and (bus_req_i.addr(2) = '1') else '0'

**`rx_fifo.wdata`** — neorv32_spi · `std_ulogic_vector(8 downto 0)`
  - **functionality** — Composed from the current rtx_engine.sreg (MSB padded with '0') and presented to the RX FIFO when rtx_engine.done asserts.
  - **roles** — carries received byte to RX FIFO
  - **relationships** — **DERIVES_FROM** → rtx_engine.sreg
  - **evidence** — rx_fifo.wdata <= '0' & rtx_engine.sreg (concurrent)

**`rx_fifo.we`** — neorv32_spi · `std_ulogic`
  - **functionality** — Driven directly (concurrent) by rtx_engine.done to write the completed received byte into the RX FIFO.
  - **roles** — drives RX FIFO write; driven by transceiver done
  - **relationships** — **CARRIES** → rtx_engine.done
  - **evidence** — rx_fifo.we <= rtx_engine.done (concurrent assignment)

**`spi_clk_en`** — neorv32_spi · `std_ulogic`
  - **functionality** — Generated when cdiv_cnt equals ctrl.cdiv or when ctrl.highspeed is asserted; its pulses gate the transceiver's per-bit state transitions (many rtx_engine updates).
  - **roles** — one-cycle enable for SCK toggles; gates transceiver bit operations
  - **relationships** — **DERIVES_FROM** → cdiv_cnt, ctrl.cdiv, clkgen_i, ctrl.highspeed, ctrl.prsc; **GATES** → rtx_engine.sck, rtx_engine.sdi_sync, rtx_engine.bitcnt, rtx_engine.sreg, rtx_engine.state, rtx_engine.done
  - **evidence** — spi_clk_en set when (cdiv_cnt = ctrl.cdiv) or ctrl.highspeed or clkgen_i(...) in clock_generator; used as if (spi_clk_en = '1') then ... in transceiver

**`tx_fifo`** — neorv32_spi · `fifo_t`
  - **functionality** — Aggregate representation of the TX FIFO interface signals (we, re, wdata, rdata, avail, free, clear, half); individual fields are driven/consumed by this entity and by the instantiated FIFO.
  - **roles** — interface to TX FIFO instance; carries write/read/control signals
  - **relationships** — **AGGREGATES** → tx_fifo.we, tx_fifo.re, tx_fifo.wdata, tx_fifo.rdata, tx_fifo.avail, tx_fifo.free, tx_fifo.clear, tx_fifo.half
  - **evidence** — tx_fifo fields used in concurrent assignments and instance port map to neorv32_fifo

**`tx_fifo.avail`** — neorv32_spi · `std_ulogic`
  - **functionality** — Provided by the FIFO instance and used to indicate whether TX data is available; used in bus readback and in ctrl_busy calculation.
  - **roles** — status source; influences bus status and IRQ logic
  - **relationships** — **SOURCES** → bus_rsp_o.data; **SOURCES** → rtx_engine.busy
  - **evidence** — bus_access reads not tx_fifo.avail into bus_rsp_o.data; irq_generator and bus_access use tx_fifo.avail

**`tx_fifo.clear`** — neorv32_spi · `std_ulogic`
  - **functionality** — Driven combinationally from ctrl.enable (negated) to clear the TX FIFO when the module is disabled.
  - **roles** — controls FIFO clear; driven by module enable
  - **relationships** — **DERIVES_FROM** → ctrl.enable
  - **evidence** — tx_fifo.clear <= not ctrl.enable (concurrent)

**`tx_fifo.free`** — neorv32_spi · `std_ulogic`
  - **functionality** — Provided by the TX FIFO instance and used to reflect fullness status in bus readback (inverted to produce TX full indication).
  - **roles** — FIFO free status; used for TX full bit
  - **relationships** — **SOURCES** → bus_rsp_o.data
  - **evidence** — bus_access assigns bus_rsp_o.data(ctrl_tx_full_c) <= not tx_fifo.free

**`tx_fifo.half`** — neorv32_spi · `std_ulogic`
  - **functionality** — Provided by the FIFO instance and used to reflect a half-full condition in bus readback and in irq generation (negated as TX not-half).
  - **roles** — status source; influences bus status and IRQ logic
  - **relationships** — **SOURCES** → bus_rsp_o.data, irq_o
  - **evidence** — bus_access uses not tx_fifo.half for ctrl_tx_nhalf; irq_generator uses (not tx_fifo.half) in expression

**`tx_fifo.rdata`** — neorv32_spi · `std_ulogic_vector(8 downto 0)`
  - **functionality** — Provided by the instantiated TX FIFO and consumed by the transceiver to either load CS control or load the transmit shift register.
  - **roles** — provides FIFO read word; feeds transceiver on read
  - **relationships** — **SOURCES** → rtx_engine.sreg, rtx_engine.cs_ctrl; **SOURCES** → rtx_engine.cs_ctrl
  - **evidence** — transceiver reads tx_fifo.rdata(8) and either uses rdata(3 downto 0) or rdata(7 downto 0) in state "100"

**`tx_fifo.re`** — neorv32_spi · `std_ulogic`
  - **functionality** — Derived combinationally from the transceiver state; asserts a read when the engine is in the starting state to fetch the next word from TX FIFO.
  - **roles** — drives FIFO read enable; selected by transceiver state
  - **relationships** — **DERIVES_FROM** → rtx_engine.state
  - **evidence** — tx_fifo.re <= '1' when (rtx_engine.state = "100") else '0'

**`tx_fifo.wdata`** — neorv32_spi · `std_ulogic_vector(8 downto 0)`
  - **functionality** — Formed combinationally from bus_req_i.data(31) and bus_req_i.data(7 downto 0) and presented to the TX FIFO instance when tx_fifo.we is asserted.
  - **roles** — carries write payload to TX FIFO; assembled from bus write data
  - **relationships** — **DERIVES_FROM** → bus_req_i.data; **DERIVES_FROM** → bus_req_i.data
  - **evidence** — tx_fifo.wdata <= bus_req_i.data(31) & bus_req_i.data(7 downto 0)

**`tx_fifo.we`** — neorv32_spi · `std_ulogic`
  - **functionality** — Derived combinationally from bus_req_i.stb, bus_req_i.rw and bus_req_i.addr(2); enables writes into the instantiated TX FIFO when a bus write to FIFO address occurs.
  - **roles** — drives FIFO write enable; gated by bus access signals
  - **relationships** — **DERIVES_FROM** → bus_req_i.stb, bus_req_i.rw, bus_req_i.addr
  - **evidence** — tx_fifo.we <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0'


## neorv32_sys  (15 non-assets)

### ports

**`clk_i`** — neorv32_sys_clock · `std_ulogic`
  - **functionality** — Supplies the rising edge that sequences the ticker process; it times updates of en, cnt and cnt2 so the counter increments and outputs are generated on clock edges.
  - **roles** — clock input; sequences internal registers
  - **relationships** — **SEQUENCES** → en, cnt, cnt2
  - **evidence** — ticker process has rising_edge(clk_i) and assigns en, cnt and cnt2 inside that branch

**`rstn_i`** — neorv32_sys_clock · `std_ulogic`
  - **functionality** — Provides an asynchronous reset that forces en, cnt and cnt2 to their reset values when '0', overriding their normal clocked updates; it also appears in the process sensitivity list.
  - **roles** — reset input; overrides register values on low
  - **relationships** — **OVERRIDES** → en, cnt, cnt2; **SEQUENCES** → en, cnt, cnt2
  - **evidence** — if (rstn_i = '0') then ... in ticker process sensitivity list assigns en, cnt, cnt2 to zeros

**`clk_i`** — neorv32_sys_reset · `std_ulogic`
  - **functionality** — Provides the rising-edge timing for the sequencer and synchronizer processes, driving capture of sreg_ext, sreg_sys and the three registered outputs on clock edges.
  - **roles** — clock source; sequences register updates
  - **relationships** — **SEQUENCES** → sreg_ext, sreg_sys, rstn_ext_o, rstn_sys_o, xrstn_wdt_o, xrstn_ocd_o
  - **evidence** — rising_edge(clk_i) in both sequencer and synchronizer processes; clk_i in their sensitivity lists.

**`rstn_dbg_i`** — neorv32_sys_reset · `std_ulogic`
  - **functionality** — When low it forces sreg_sys cleared (gating the system reset path); it is also forwarded synchronously to xrstn_ocd_o on clock edges.
  - **roles** — reset source; gates system-reset shift register; synchronized output source
  - **relationships** — **GATES** → sreg_sys; **SOURCES** → xrstn_ocd_o
  - **evidence** — if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then sreg_sys <= (others => '0'); and xrstn_ocd_o <= rstn_dbg_i in synchronizer on rising_edge(clk_i).

**`rstn_ext_i`** — neorv32_sys_reset · `std_ulogic`
  - **functionality** — Acts as an active-low asynchronous reset; when '0' it clears sreg_ext and sreg_sys and forces all output reset ports low, overriding normal clocked updates.
  - **roles** — asynchronous reset input; gates register clears; overrides outputs
  - **relationships** — **GATES** → sreg_ext, sreg_sys, rstn_ext_o, rstn_sys_o, xrstn_wdt_o, xrstn_ocd_o
  - **evidence** — if (rstn_ext_i = '0') then ... branches in both sequencer and synchronizer processes assign zeros to registers and outputs.

**`rstn_ext_o`** — neorv32_sys_reset · `std_ulogic`
  - **functionality** — Drives the external reset output derived from the and-reduction of sreg_ext; is forced low during the asynchronous external reset branch and otherwise reflects sreg_ext state.
  - **roles** — exported reset; derived from sreg_ext; reports extended reset
  - **relationships** — **DERIVES_FROM** → sreg_ext; **EXPORTS** → _(none)_
  - **evidence** — rstn_ext_o <= and_reduce_f(sreg_ext) in rising_edge branch; rstn_ext_o <= '0' in the rstn_ext_i = '0' reset branch of sequencer.

**`rstn_sys_o`** — neorv32_sys_reset · `std_ulogic`
  - **functionality** — Drives the system reset output derived from the and-reduction of sreg_sys; is forced low by asynchronous external reset and otherwise reflects sreg_sys progression.
  - **roles** — exported reset; derived from sreg_sys; reports system reset
  - **relationships** — **DERIVES_FROM** → sreg_sys; **EXPORTS** → _(none)_
  - **evidence** — rstn_sys_o <= and_reduce_f(sreg_sys) in sequencer rising_edge branch; reset branch sets rstn_sys_o <= '0'.

**`rstn_wdt_i`** — neorv32_sys_reset · `std_ulogic`
  - **functionality** — When low it forces sreg_sys cleared (gating the system reset path); it is also forwarded synchronously to xrstn_wdt_o on clock edges.
  - **roles** — reset source; gates system-reset shift register; synchronized output source
  - **relationships** — **GATES** → sreg_sys; **SOURCES** → xrstn_wdt_o
  - **evidence** — if (rstn_wdt_i = '0') or (rstn_dbg_i = '0') then sreg_sys <= (others => '0'); and xrstn_wdt_o <= rstn_wdt_i in synchronizer on rising_edge(clk_i).

**`xrstn_ocd_o`** — neorv32_sys_reset · `std_ulogic`
  - **functionality** — Captured synchronously on clk_i from rstn_dbg_i and forced to '0' by external reset; forwards the synchronized debug reset to the entity output.
  - **roles** — exported synchronized reset; captures rstn_dbg_i; clocked output
  - **relationships** — **CAPTURES** → rstn_dbg_i; **EXPORTS** → _(none)_
  - **evidence** — in synchronizer process xrstn_ocd_o <= rstn_dbg_i on rising_edge(clk_i); reset branch sets xrstn_ocd_o <= '0'.

**`xrstn_wdt_o`** — neorv32_sys_reset · `std_ulogic`
  - **functionality** — Captured synchronously on clk_i from rstn_wdt_i and forced to '0' by external reset; forwards the synchronized watchdog reset to the entity output.
  - **roles** — exported synchronized reset; captures rstn_wdt_i; clocked output
  - **relationships** — **CAPTURES** → rstn_wdt_i; **EXPORTS** → _(none)_
  - **evidence** — in synchronizer process xrstn_wdt_o <= rstn_wdt_i on rising_edge(clk_i); reset branch sets xrstn_wdt_o <= '0'.

### signals

**`cnt`** — neorv32_sys_clock · `std_ulogic_vector(11 downto 0)`
  - **functionality** — Holds a 12-bit counter incremented each clock when en = '1' by using its prior value; it supplies bits to clk_en_o and is copied to cnt2 every cycle.
  - **roles** — holds counter across cycles; supplies divider bits; fed from previous count
  - **relationships** — **DERIVES_FROM** → cnt; **SOURCES** → cnt2; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o
  - **evidence** — cnt <= std_ulogic_vector(unsigned(cnt) + 1) when en='1' and cnt2 <= cnt copies cnt; cnt(i) used in clk_en_o assignments

**`cnt2`** — neorv32_sys_clock · `std_ulogic_vector(11 downto 0)`
  - **functionality** — Captured each clock as a copy of cnt to provide the previous-cycle counter value; its bits are used with cnt bits to detect rising transitions and form single-cycle pulses.
  - **roles** — holds previous counter value; supplies delayed bits for pulse detection
  - **relationships** — **CAPTURES** → cnt; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o; **SOURCES** → clk_en_o
  - **evidence** — cnt2 <= cnt in rising_edge branch; cnt2(i) used in clk_en_o(...) assignments as (not cnt2(i))

**`en`** — neorv32_sys_clock · `std_ulogic`
  - **functionality** — Captured on clk_i as the OR-reduction of enable_i; it holds whether counting is enabled and its value gates whether cnt increments each clock.
  - **roles** — holds enable across cycles; controls counter update; derived from enable_i
  - **relationships** — **CAPTURES** → enable_i; **GATES** → cnt
  - **evidence** — en <= or_reduce_f(enable_i) on rising_edge(clk_i); if (en = '1') then cnt <= unsigned(cnt)+1 else cnt <= (others=>'0')

**`sreg_ext`** — neorv32_sys_reset · `std_ulogic_vector(3 downto 0)`
  - **functionality** — 4-bit shift register that shifts in '1' each clock when not held by external reset and is cleared by asynchronous external reset; supplies rstn_ext_o via an and-reduction.
  - **roles** — holds external reset state; shift-register for rstn_ext; drives rstn_ext_o
  - **relationships** — **SOURCES** → rstn_ext_o
  - **evidence** — sreg_ext <= (others => '0') in reset branch or sreg_ext(sreg_ext'left-1 downto 0) & '1' on rising_edge; rstn_ext_o <= and_reduce_f(sreg_ext).

**`sreg_sys`** — neorv32_sys_reset · `std_ulogic_vector(3 downto 0)`
  - **functionality** — 4-bit shift register that shifts in '1' each clock when not held by watchdog/debug and is cleared by external reset or by rstn_wdt_i/rstn_dbg_i; supplies rstn_sys_o via an and-reduction.
  - **roles** — holds system reset state; shift-register for rstn_sys; drives rstn_sys_o
  - **relationships** — **SOURCES** → rstn_sys_o
  - **evidence** — sreg_sys <= (others => '0') or sreg_sys(sreg_sys'left-1 downto 0) & '1'; rstn_sys_o <= and_reduce_f(sreg_sys) in sequencer process.


## neorv32_trng  (49 non-assets)

### ports

**`clk_i`** — neoTRNG · `std_ulogic`
  - **functionality** — Supplies the clock edge to internal processes and to instantiated neoTRNG_cell instances; it sequences debiasing and sampling registers (debias_sreg, debias_state, sample_en, sample_cnt, sample_sreg) and clocks each cell instance.
  - **roles** — clock input; sequences internal registers; drives instantiated cells
  - **relationships** — **SEQUENCES** → debias_sreg, debias_state, sample_en, sample_cnt, sample_sreg; **SOURCES** → neoTRNG_cell_inst.clk_i
  - **evidence** — rising_edge(clk_i) in debiasing and sampling_control processes; port map clk_i => neoTRNG_cell_inst.clk_i in generate.

**`enable_i`** — neoTRNG · `std_ulogic`
  - **functionality** — Is sampled into internal sample_en on the clock edge and thereby enables or disables sampling; it sources sample_en which in turn controls cell enables and sampling counter behavior.
  - **roles** — input control; captured into sample_en; enables sampling
  - **relationships** — **SOURCES** → sample_en
  - **evidence** — sample_en <= enable_i inside rising_edge(clk_i) in sampling_control process.

**`rstn_i`** — neoTRNG · `std_ulogic`
  - **functionality** — Provides asynchronous reset to clocked processes and is forwarded to each neoTRNG_cell; it forces registers to their reset values in reset branches and is passed to instances' rstn_i ports.
  - **roles** — async reset input; overrides registers on reset; propagates to instantiated cells
  - **relationships** — **OVERRIDES** → debias_sreg, debias_state, sample_en, sample_cnt, sample_sreg; **SEQUENCES** → debias_sreg, debias_state, sample_en, sample_cnt, sample_sreg; **SOURCES** → neoTRNG_cell_inst.rstn_i
  - **evidence** — if (rstn_i = '0') then ... assignments in debiasing and sampling_control; port map rstn_i => neoTRNG_cell_inst.rstn_i in generate.

**`clk_i`** — neoTRNG_cell · `std_ulogic`
  - **functionality** — Provides rising-edge timing to sequential processes; it sequences the en_shift_reg and synchronizer registers and the simulator inverter process when present, driving register updates inside the entity.
  - **roles** — clock source; sequences internal registers
  - **relationships** — **SEQUENCES** → sreg; **SEQUENCES** → sync; **SEQUENCES** → inv_out
  - **evidence** — rising_edge(clk_i) in en_shift_reg, synchronizer and inverter_sim_ff processes

**`en_i`** — neoTRNG_cell · `std_ulogic`
  - **functionality** — Is shifted into the en shift-register on clock edges and also controls latch behavior: when '0' latch(i) is forced '0', otherwise latch may hold or follow inv_out depending on sreg(i).
  - **roles** — input enable; feeds shift register; gates latch zeroing
  - **relationships** — **SOURCES** → sreg; **GATES** → latch
  - **evidence** — en shifted in by sreg <= ... & en_i (en_shift_reg) and used in latch when (en_i = '0') condition

**`en_o`** — neoTRNG_cell · `std_ulogic`
  - **functionality** — Drives the external en_o port from the most-significant bit of the internal en shift-register sreg, exporting the shift-register's head bit.
  - **roles** — output; exports shift-register MSB
  - **relationships** — **SLICES** → sreg
  - **evidence** — continuous assignment en_o <= sreg(sreg'left)

**`rnd_o`** — neoTRNG_cell · `std_ulogic`
  - **functionality** — Drives the external rnd_o port from synchronizer stage sync(1), exporting the sampled/synchronized ring-oscillator bit to the outside.
  - **roles** — output; exports synchronized random bit
  - **relationships** — **SLICES** → sync
  - **evidence** — continuous assignment rnd_o <= sync(1)

**`rstn_i`** — neoTRNG_cell · `std_ulogic`
  - **functionality** — When '0' it forces reset branches in sequential processes, clearing sreg and sync to zeros and preventing normal updates until released.
  - **roles** — reset input; gates register reset behavior
  - **relationships** — **GATES** → sreg; **GATES** → sync
  - **evidence** — if (rstn_i = '0') branches in en_shift_reg and synchronizer processes

**`bus_req_i`** — neorv32_trng · `bus_req_t`
  - **functionality** — Aggregates bus request fields (stb, rw, addr, data, etc.) that are consumed individually by this entity to control read/write behavior and FIFO access.
  - **roles** — input bus request aggregator; supplies fields used to control logic
  - **relationships** — **AGGREGATES** → bus_req_i.addr, bus_req_i.data, bus_req_i.ben, bus_req_i.stb, bus_req_i.rw, bus_req_i.src, bus_req_i.priv, bus_req_i.debug, bus_req_i.amo, bus_req_i.amoop, bus_req_i.lock, bus_req_i.fence
  - **evidence** — port declaration; individual fields used throughout bus_access and concurrent assignments.

**`bus_req_i.addr`** — neorv32_trng · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Bit 2 of the address selects register versus data read in bus_access and, combined with stb and rw, participates in the condition that enables fifo.re for FIFO reads.
  - **roles** — read-address selector; selects register vs data read; gates FIFO read when combined with stb and rw
  - **relationships** — **SELECTS** → bus_rsp_o.data; **GATES** → fifo.re
  - **evidence** — uses bus_req_i.addr(2) in bus_access if to choose status vs data and in fifo.re concurrent assignment.

**`bus_req_i.amo`** — neorv32_trng · `std_ulogic`
  - **functionality** — Declared but not referenced in this source.
  - **roles** — input field, unused
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond the port declaration.

**`bus_req_i.amoop`** — neorv32_trng · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared but not used in this source; no references found.
  - **roles** — input field, unused
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond the port declaration.

**`bus_req_i.ben`** — neorv32_trng · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared but not referenced anywhere in this source; not read or tested by the entity.
  - **roles** — input field, unused
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond the port declaration.

**`bus_req_i.data`** — neorv32_trng · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies write-data bits; specific bits (ctrl_en_c, ctrl_fifo_clr_c) are read during write transactions to set internal enable and fifo_clr registers.
  - **roles** — write operand source; feeds control bits for enable and fifo_clr
  - **relationships** — **SOURCES** → enable, fifo_clr
  - **evidence** — enable <= bus_req_i.data(ctrl_en_c) and fifo_clr <= bus_req_i.data(ctrl_fifo_clr_c) inside bus_access write branch.

**`bus_req_i.debug`** — neorv32_trng · `std_ulogic`
  - **functionality** — Declared but not referenced in this source.
  - **roles** — input field, unused
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond the port declaration.

**`bus_req_i.fence`** — neorv32_trng · `std_ulogic`
  - **functionality** — Declared but not used in this source.
  - **roles** — input field, unused
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond the port declaration.

**`bus_req_i.lock`** — neorv32_trng · `std_ulogic`
  - **functionality** — Declared but not referenced in this source.
  - **roles** — input field, unused
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond the port declaration.

**`bus_req_i.priv`** — neorv32_trng · `std_ulogic`
  - **functionality** — Declared but unused in this source; not read or tested.
  - **roles** — input field, unused
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond the port declaration.

**`bus_req_i.rw`** — neorv32_trng · `std_ulogic`
  - **functionality** — Selects the write versus read path in bus_access (writes set internal control bits; reads produce bus_rsp_o.data) and is part of the fifo.re expression enabling FIFO reads.
  - **roles** — selects read/write path; gates write captures and read responses
  - **relationships** — **GATES** → enable, fifo_clr, bus_rsp_o, fifo.re
  - **evidence** — if (bus_req_i.rw = '1') then ... else ... ; bus_req_i.rw used in fifo.re concurrent assignment.

**`bus_req_i.src`** — neorv32_trng · `std_ulogic`
  - **functionality** — Declared but not referenced in this source; not read or tested.
  - **roles** — input field, unused
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond the port declaration.

**`bus_req_i.stb`** — neorv32_trng · `std_ulogic`
  - **functionality** — Gates handling of a bus transaction (if-statement) and is captured into bus_rsp_o.ack; it also contributes to the fifo.re enable expression used to pop the FIFO on reads.
  - **roles** — transaction strobe; enables bus handling; drives response ack and helps gate FIFO read
  - **relationships** — **SOURCES** → bus_rsp_o.ack; **GATES** → enable, fifo_clr, bus_rsp_o, fifo.re
  - **evidence** — bus_rsp_o.ack <= bus_req_i.stb; used in if (bus_req_i.stb='1') then ...; part of fifo.re concurrent conditional.

**`bus_rsp_o`** — neorv32_trng · `bus_rsp_t`
  - **functionality** — Constructs the response record from ack, err and data fields inside bus_access and exports that assembled response to the bus master.
  - **roles** — response aggregator; driven by sequential logic; exports response to bus master
  - **relationships** — **AGGREGATES** → bus_rsp_o.ack, bus_rsp_o.err, bus_rsp_o.data
  - **evidence** — bus_access process assigns bus_rsp_o fields (ack, err, data) including reset assignment bus_rsp_o <= rsp_terminate_c.

**`bus_rsp_o.ack`** — neorv32_trng · `std_ulogic`
  - **functionality** — Captured on the clock edge from bus_req_i.stb and provided as the ack bit of the bus response.
  - **roles** — acknowledge output; captured from bus strobe
  - **relationships** — **CAPTURES** → bus_req_i.stb
  - **evidence** — bus_rsp_o.ack <= bus_req_i.stb inside rising_edge(clk_i) branch of bus_access.

**`bus_rsp_o.data`** — neorv32_trng · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Assembles the 32-bit response data from control bits (enable), FIFO size, sim flag, FIFO avail and the FIFO read data slice; selected by addr(2) during reads.
  - **roles** — carries status and data to bus master; assembled from internal signals and constants
  - **relationships** — **SLICES** → enable; **SLICES** → fifo.avail; **SLICES** → fifo.rdata
  - **evidence** — bus_access assigns bus_rsp_o.data slices: ctrl_en_c<=enable; ctrl_avail_c<=fifo.avail; data bits ctrl_data_msb_c..ctrl_data_lsb_c<=fifo.rdata or zeros.

**`bus_rsp_o.err`** — neorv32_trng · `std_ulogic`
  - **functionality** — Captured each cycle as the constant '0' and supplied as the error bit of the bus response.
  - **roles** — error flag output
  - **relationships** — **CAPTURES** → _(none)_
  - **evidence** — bus_rsp_o.err <= '0' inside bus_access clocked process.

**`clk_i`** — neorv32_trng · `std_ulogic`
  - **functionality** — Supplies rising-edge timing to the bus_access process (sequencing assignments to bus_rsp_o, enable and fifo_clr) and is forwarded to instantiated components (neoTRNG_inst, rnd_pool_fifo_inst).
  - **roles** — clock source for sequential logic; forwarded to instantiated components
  - **relationships** — **SEQUENCES** → enable, fifo_clr, bus_rsp_o; **SOURCES** → neoTRNG_inst.clk_i, rnd_pool_fifo_inst.clk_i
  - **evidence** — process sensitivity and rising_edge(clk_i); clk_i port mapped to neoTRNG_inst and rnd_pool_fifo_inst.

**`rstn_i`** — neorv32_trng · `std_ulogic`
  - **functionality** — Drives the reset branch that initializes bus_rsp_o, fifo_clr and enable on '0' and is passed to the instantiated components' reset ports.
  - **roles** — reset source for sequential logic; forwarded to instantiated components
  - **relationships** — **SEQUENCES** → bus_rsp_o, fifo_clr, enable; **SOURCES** → neoTRNG_inst.rstn_i, rnd_pool_fifo_inst.rstn_i
  - **evidence** — if (rstn_i = '0') then ... in bus_access; rstn_i port mapped to neoTRNG_inst and rnd_pool_fifo_inst.

### signals

**`cell_en_in`** — neoTRNG · `std_ulogic_vector(NUM_CELLS-1 downto 0)`
  - **functionality** — Constructed from sample_en for element 0 and from a shifted slice of cell_en_out for higher bits; it forwards the cell enable vector into each neoTRNG_cell.en_i via instance port maps.
  - **roles** — combinational enable bus; forwards sample_en to first cell; cascades cell_en_out to next inputs
  - **relationships** — **AGGREGATES** → sample_en, cell_en_out
  - **evidence** — cell_en_in(0) <= sample_en and cell_en_in(NUM_CELLS-1 downto 1) <= cell_en_out(NUM_CELLS-2 downto 0) concurrent assignments.

**`cell_en_out`** — neoTRNG · `std_ulogic_vector(NUM_CELLS-1 downto 0)`
  - **functionality** — Driven by each neoTRNG_cell en_o port and presented as a vector; its bits are read back to build cell_en_in and the MSB is used in debias_state update.
  - **roles** — enable outputs from cells; feeds back to cell_en_in; supplies debias gating
  - **relationships** — **SOURCES** → neoTRNG_cell_inst.en_o; **SOURCES** → cell_en_in; **SOURCES** → debias_state
  - **evidence** — port map en_o => cell_en_out(i) in generate; cell_en_in assignment and debias_state <= ... cell_en_out(cell_en_out'left).

**`cell_rnd`** — neoTRNG · `std_ulogic_vector(NUM_CELLS-1 downto 0)`
  - **functionality** — Collects rnd_o from every instantiated neoTRNG_cell and supplies those bits to the combine process which XORs them into cell_sum.
  - **roles** — entropy bits from cells; feeds combine XOR
  - **relationships** — **SOURCES** → neoTRNG_cell_inst.rnd_o; **SOURCES** → cell_sum
  - **evidence** — port map rnd_o => cell_rnd(i) in generate; used in combine process loop tmp_v := tmp_v xor cell_rnd(i).

**`cell_sum`** — neoTRNG · `std_ulogic`
  - **functionality** — Computed as the XOR (parity) of all bits in cell_rnd inside the combine process and provided as the single combined entropy bit to the debias shift register.
  - **roles** — combined entropy bit; feeds debias logic
  - **relationships** — **DERIVES_FROM** → cell_rnd; **SOURCES** → debias_sreg
  - **evidence** — process combine computes tmp_v xor cell_rnd loop and assigns cell_sum <= tmp_v.

**`debias_data`** — neoTRNG · `std_ulogic`
  - **functionality** — Combinationally taken as debias_sreg(0); it is XORed into the sampling shift register to produce whitened sampled bits.
  - **roles** — debias output; feeds sample_sreg
  - **relationships** — **DERIVES_FROM** → debias_sreg; **SOURCES** → sample_sreg
  - **evidence** — debias_data <= debias_sreg(0); used in sample_sreg update sample_sreg <= ... & (sample_sreg(7) xor debias_data).

**`debias_sreg`** — neoTRNG · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Clocked two-bit shift register that captures the newest cell_sum and previous bit each rising edge; its bits produce debias_valid and supply debias_data for sampling.
  - **roles** — holds recent entropy samples; provides debias sample bit; register updated on clock
  - **relationships** — **CAPTURES** → debias_sreg, cell_sum; **SOURCES** → debias_valid, debias_data
  - **evidence** — debias_sreg <= debias_sreg(0) & cell_sum on rising_edge(clk_i); debias_valid and debias_data derived from debias_sreg.

**`debias_state`** — neoTRNG · `std_ulogic`
  - **functionality** — Captured on clock as (not debias_state) AND the MSB of cell_en_out; used with debias_sreg to form debias_valid. Reset clears this register.
  - **roles** — state register; gates debias_valid formation; captures cell_en_out condition
  - **relationships** — **CAPTURES** → debias_state, cell_en_out; **SOURCES** → debias_valid
  - **evidence** — debias_state <= (not debias_state) and cell_en_out(cell_en_out'left) on rising_edge(clk_i); reset branch sets debias_state <= '0'.

**`debias_valid`** — neoTRNG · `std_ulogic`
  - **functionality** — Combinationally derived from debias_state AND the XOR of debias_sreg bits; it gates sampling counter increment and shift-register updates when asserted.
  - **roles** — debias accept signal; gates sampling updates; combines debias_sreg and debias_state
  - **relationships** — **DERIVES_FROM** → debias_state, debias_sreg; **GATES** → sample_cnt, sample_sreg
  - **evidence** — debias_valid <= debias_state and (debias_sreg(1) xor debias_sreg(0)); used in sampling_control if (debias_valid = '1') then ...

**`sample_cnt`** — neoTRNG · `std_ulogic_vector(6 downto 0)`
  - **functionality** — Counts accepted debias_valid events by incrementing each clock when debias_valid='1'; it resets on disable or when its MSB becomes '1', and its MSB is exported as valid_o.
  - **roles** — samples counter; drives valid_o MSB; controls wrap/reset
  - **relationships** — **CAPTURES** → sample_cnt; **CONSTRAINS** → sample_cnt, sample_sreg; **SOURCES** → valid_o
  - **evidence** — sample_cnt incremented std_ulogic_vector(unsigned(sample_cnt)+1) on debias_valid; tested sample_cnt(sample_cnt'left) = '1' in sampling_control; valid_o <= sample_cnt(sample_cnt'left).

**`sample_en`** — neoTRNG · `std_ulogic`
  - **functionality** — Captured from external enable_i at clock edge; its registered value drives cell_en_in(0) combinationally and is tested in sampling_control to reset or allow sampling.
  - **roles** — synchronized enable; provides cell_en input; gates sampling logic
  - **relationships** — **CAPTURES** → enable_i; **SOURCES** → cell_en_in; **GATES** → sample_cnt, sample_sreg
  - **evidence** — sample_en <= enable_i on rising_edge(clk_i); cell_en_in(0) <= sample_en; sampling_control tests sample_en = '0'.

**`sample_sreg`** — neoTRNG · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Shift-register of 8 bits that is cleared on reset, shifted and updated with debias_data on accepted sampling clocks, and whose full contents are exported on data_o.
  - **roles** — holds sampled byte; driven to data_o; updated from debias_data
  - **relationships** — **CAPTURES** → sample_sreg, debias_data; **SOURCES** → data_o
  - **evidence** — sample_sreg <= sample_sreg(6 downto 0) & (sample_sreg(7) xor debias_data) on rising_edge(clk_i); data_o <= sample_sreg.

**`inv_in`** — neoTRNG_cell · `std_ulogic_vector(NUM_INV-1 downto 0)`
  - **functionality** — Constructs a rotated view of latch (inv_in(0)=latch(NUM_INV-1), others shifted) and supplies those bits to inv_out computation.
  - **roles** — feeds inverter inputs; conveys rotated latch state
  - **relationships** — **DERIVES_FROM** → latch; **SOURCES** → inv_out
  - **evidence** — inv_in(0) <= latch(NUM_INV-1) and inv_in(NUM_INV-1 downto 1) <= latch(NUM_INV-2 downto 0)

**`inv_out`** — neoTRNG_cell · `std_ulogic_vector(NUM_INV-1 downto 0)`
  - **functionality** — Drives each bit as logical not of inv_in (combinationally in normal mode); those outputs are the values that latch may sample when enabled.
  - **roles** — inverter outputs; drives latch input when selected
  - **relationships** — **DERIVES_FROM** → inv_in; **SOURCES** → latch
  - **evidence** — inverter_phy: inv_out(i) <= not inv_in(i); latch uses inv_out(i) as one assignment operand

**`latch`** — neoTRNG_cell · `std_ulogic_vector(NUM_INV-1 downto 0)`
  - **functionality** — Combinationally selects its value from '0', its own previous value, or inv_out(i) based on en_i and sreg(i); it then supplies the rotated latch vector inv_in.
  - **roles** — local latch per inverter; forwards inv_out when enabled; combinational control node
  - **relationships** — **DERIVES_FROM** → en_i, sreg, inv_out; **SOURCES** → inv_in
  - **evidence** — concurrent assignment latch(i) <= '0' when (en_i='0') else latch(i) when (sreg(i)='0') else inv_out(i); inv_in <= rotated latch assignments

**`sreg`** — neoTRNG_cell · `std_ulogic_vector(NUM_INV-1 downto 0)`
  - **functionality** — Holds NUM_INV bits and shifts in en_i on rising clk_i; it resets to zeros on rstn_i and its MSB is presented on en_o; individual bits gate latch updates.
  - **roles** — held enable history; gates latch updates; provides MSB to en_o
  - **relationships** — **CAPTURES** → en_i, sreg; **SOURCES** → en_o; **GATES** → latch
  - **evidence** — en_shift_reg process: reset branch sets sreg<= (others=>'0'); on rising_edge(clk_i) sreg <= sreg(sreg'left-1 downto 0) & en_i

**`sync`** — neoTRNG_cell · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Is reset to zeros on rstn_i and on rising clk_i shifts in latch(latch'left) via sync <= sync(0) & latch(latch'left); its stage sync(1) is exported as rnd_o.
  - **roles** — synchronizer stage; holds sampled bit across cycles; drives rnd_o
  - **relationships** — **CAPTURES** → sync, latch; **SOURCES** → rnd_o
  - **evidence** — synchronizer process: reset branch sets sync<= (others=>'0'); on rising_edge(clk_i) sync <= sync(0) & latch(latch'left); rnd_o <= sync(1)

**`fifo`** — neorv32_trng · `fifo_t`
  - **functionality** — Aggregate record holding FIFO control, data and status fields; its fields are individually driven or derived and connected to the instantiated FIFO and TRNG.
  - **roles** — aggregate of FIFO signals; forwards fields to/from instantiated FIFO and TRNG
  - **relationships** — **AGGREGATES** → fifo.we, fifo.re, fifo.clear, fifo.wdata, fifo.rdata, fifo.avail, fifo.half, fifo.free
  - **evidence** — type fifo_t record declaration and field connections in port maps to neoTRNG_inst and rnd_pool_fifo_inst.

**`fifo.clear`** — neorv32_trng · `std_ulogic`
  - **functionality** — Derived from enable and fifo_clr (clear asserted when enable='0' or fifo_clr='1') and forwarded to rnd_pool_fifo_inst.clear_i to clear or reset FIFO state as required.
  - **roles** — combinational FIFO-clear control; forwards clear to FIFO instance
  - **relationships** — **DERIVES_FROM** → enable, fifo_clr; **SOURCES** → rnd_pool_fifo_inst.clear_i
  - **evidence** — fifo.clear <= '1' when (enable = '0') or (fifo_clr = '1') else '0'; port mapped to rnd_pool_fifo_inst.clear_i.

**`fifo.half`** — neorv32_trng · `std_ulogic`
  - **functionality** — Captured from rnd_pool_fifo_inst.half_o and made available internally; not used elsewhere in this source.
  - **roles** — status output from FIFO; captured and unused
  - **relationships** — **CAPTURES** → rnd_pool_fifo_inst.half_o
  - **evidence** — rnd_pool_fifo_inst port map half_o => fifo.half; no other references found.

**`fifo.rdata`** — neorv32_trng · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Captured from rnd_pool_fifo_inst.rdata_o and supplied into bus responses: its full 8-bit value is placed into a slice of bus_rsp_o.data during data reads.
  - **roles** — provides FIFO output data; supplies read data slice into bus response
  - **relationships** — **CAPTURES** → rnd_pool_fifo_inst.rdata_o; **SLICES** → bus_rsp_o.data
  - **evidence** — rnd_pool_fifo_inst port map rdata_o => fifo.rdata; bus_access assigns bus_rsp_o.data(ctrl_data_msb_c downto ctrl_data_lsb_c) <= fifo.rdata.

**`fifo.wdata`** — neorv32_trng · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Captured from neoTRNG_inst.data_o (TRNG output bytes) and forwarded to rnd_pool_fifo_inst.wdata_i for storage in the FIFO.
  - **roles** — carries TRNG output to FIFO; forwarded between instances
  - **relationships** — **CAPTURES** → neoTRNG_inst.data_o; **SOURCES** → rnd_pool_fifo_inst.wdata_i
  - **evidence** — neoTRNG_inst port map data_o => fifo.wdata; rnd_pool_fifo_inst port map wdata_i => fifo.wdata.

**`fifo.we`** — neorv32_trng · `std_ulogic`
  - **functionality** — Driven by neoTRNG_inst.valid_o and forwarded to rnd_pool_fifo_inst.we_i to request writes into the FIFO when TRNG produces data.
  - **roles** — carries TRNG valid to FIFO write port; forwarded between instances
  - **relationships** — **CAPTURES** → neoTRNG_inst.valid_o; **SOURCES** → rnd_pool_fifo_inst.we_i
  - **evidence** — neoTRNG_inst port map valid_o => fifo.we; rnd_pool_fifo_inst port map we_i => fifo.we.


## neorv32_twi  (59 non-assets)

### ports

**`bus_req_i`** — neorv32_twi · `bus_req_t`
  - **functionality** — Receives the incoming bus transaction bundle and supplies fields (stb,rw,addr,data,...) used to update control registers, drive FIFOs and produce bus responses.
  - **roles** — input bus interface; drives control and FIFO writes; governs bus-access behaviour
  - **relationships** — **AGGREGATES** → bus_req_i.addr, bus_req_i.data, bus_req_i.ben, bus_req_i.stb, bus_req_i.rw, bus_req_i.src, bus_req_i.priv, bus_req_i.debug, bus_req_i.amo, bus_req_i.amoop, bus_req_i.lock, bus_req_i.fence
  - **evidence** — Port record declared in the port-clause and its fields are referenced in bus_access and concurrent assignments.

**`bus_req_i.addr`** — neorv32_twi · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies address bits (bit 2 tested) used to select CSR vs FIFO accesses and to qualify write/read actions; it gates control and FIFO-write/read assignments.
  - **roles** — address selector; gates CSR vs FIFO accesses; control branch condition
  - **relationships** — **GATES** → ctrl.enable, ctrl.prsc, ctrl.cdiv, ctrl.clkstr, bus_rsp_o.data, fifo.tx_we, fifo.rx_re
  - **evidence** — bus_req_i.addr(2) compared in bus_access and used in concurrent conditional assignments (e.g. fifo.tx_we, fifo.rx_re).

**`bus_req_i.amo`** — neorv32_twi · `std_ulogic`
  - **functionality** — Declared but not referenced in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No usage besides declaration.

**`bus_req_i.amoop`** — neorv32_twi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Present in the record but not used in this entity's logic.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences in the source apart from the port clause.

**`bus_req_i.ben`** — neorv32_twi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared as part of the bus request record but not referenced anywhere in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences besides the port declaration.

**`bus_req_i.data`** — neorv32_twi · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Carries write-data from the bus that is sampled to update ctrl fields and drives TX FIFO write data; consumed by bus_access and TX FIFO write path.
  - **roles** — write data source; updates control registers; supplies TX FIFO payload
  - **relationships** — **SOURCES** → ctrl.enable, ctrl.prsc, ctrl.cdiv, ctrl.clkstr, fifo.tx_wdata
  - **evidence** — bus_req_i.data bits are read to assign ctrl fields and fifo.tx_wdata in bus_access and concurrent assignments.

**`bus_req_i.debug`** — neorv32_twi · `std_ulogic`
  - **functionality** — Part of the bus request record but not referenced in this design unit.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — Only declared in the port clause; not used.

**`bus_req_i.fence`** — neorv32_twi · `std_ulogic`
  - **functionality** — Declared but not referenced in this entity.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No references other than declaration.

**`bus_req_i.lock`** — neorv32_twi · `std_ulogic`
  - **functionality** — Declared in the record but not read anywhere in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — Only in port declaration.

**`bus_req_i.priv`** — neorv32_twi · `std_ulogic`
  - **functionality** — Declared but not read or used in this entity's source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences besides the port declaration.

**`bus_req_i.rw`** — neorv32_twi · `std_ulogic`
  - **functionality** — Determines read vs write branch in bus_access and participates in the enable terms for FIFO write/read; it gates control register writes and data reads.
  - **roles** — selects read/write branch; gates FIFO/R/W
  - **relationships** — **GATES** → ctrl.enable, ctrl.prsc, ctrl.cdiv, ctrl.clkstr, bus_rsp_o.data, fifo.tx_we, fifo.rx_re
  - **evidence** — Used in if (bus_req_i.rw = '1') then ... in bus_access and in fifo.tx_we / fifo.rx_re enable conditions.

**`bus_req_i.src`** — neorv32_twi · `std_ulogic`
  - **functionality** — Declared in the bus request record but not used anywhere in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No references besides the port declaration.

**`bus_req_i.stb`** — neorv32_twi · `std_ulogic`
  - **functionality** — Used both as a gating condition for bus accesses and directly fed back as the response ack; it gates CSR/FIFO reads and writes and drives bus_rsp_o.ack.
  - **roles** — bus transaction qualifier; gates bus-access updates; feeds response ack
  - **relationships** — **GATES** → ctrl.enable, ctrl.prsc, ctrl.cdiv, ctrl.clkstr, bus_rsp_o.data, fifo.tx_we, fifo.rx_re; **SOURCES** → bus_rsp_o.ack
  - **evidence** — Tested in if (bus_req_i.stb = '1') and used in conditional concurrent assignments (e.g. fifo.tx_we) and assigned to bus_rsp_o.ack.

**`bus_rsp_o`** — neorv32_twi · `bus_rsp_t`
  - **functionality** — Provides the bus response bundle (ack, err, data) back to the bus master; its fields are driven in the clocked bus_access process from bus_req and internal status.
  - **roles** — output bus interface; reports ack/err/data; register group updated on bus cycles
  - **relationships** — **AGGREGATES** → bus_rsp_o.ack, bus_rsp_o.err, bus_rsp_o.data
  - **evidence** — Fields assigned in bus_access process (bus_rsp_o.ack, .err, .data).

**`bus_rsp_o.ack`** — neorv32_twi · `std_ulogic`
  - **functionality** — Captured each bus cycle from bus_req_i.stb inside bus_access and returned to the bus master as the ack field.
  - **roles** — response ack register; reports transaction acceptance
  - **relationships** — **DERIVES_FROM** → bus_req_i.stb
  - **evidence** — Assigned in bus_access: bus_rsp_o.ack <= bus_req_i.stb (inside rising_edge(clk_i)).

**`bus_rsp_o.data`** — neorv32_twi · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides readback data to the bus: on CSR reads it reports ctrl and status bits; on FIFO read it returns fifo.rx_rdata; constructed from ctrl fields, io_con samples, FIFO status and rx data.
  - **roles** — response data register; reports control/status fields; returns RX FIFO payload
  - **relationships** — **SLICES** → fifo.rx_rdata; **SLICES** → ctrl.enable; **SLICES** → ctrl.prsc; **SLICES** → ctrl.cdiv; **SLICES** → ctrl.clkstr; **SLICES** → io_con.scl_in_ff; **SLICES** → io_con.sda_in_ff; **SLICES** → fifo.tx_free; **SLICES** → fifo.rx_avail; **SLICES** → engine.busy
  - **evidence** — bus_rsp_o.data bits are assigned in bus_access from ctrl fields, io_con.s*_in_ff, fifo.rx_avail, fifo.tx_free and fifo.rx_rdata(8 downto 0).

**`bus_rsp_o.err`** — neorv32_twi · `std_ulogic`
  - **functionality** — Held as '0' by the bus_access process (error is not reported here); driven to a constant in the clocked response path.
  - **roles** — response error register; reports no-error state
  - **relationships** — **DERIVES_FROM** → _(none)_
  - **evidence** — bus_rsp_o.err <= '0' in the rising_edge(clk_i) branch of bus_access (assigned constant).

**`clk_i`** — neorv32_twi · `std_ulogic`
  - **functionality** — Supplies the rising_edge clock used by all clocked processes; sequences registers such as ctrl, engine, clk_gen, io_con and irq generation logic.
  - **roles** — clock source; sequences internal registers; drives rising_edge timing for processes
  - **relationships** — **SEQUENCES** → bus_rsp_o.ack, bus_rsp_o.err, bus_rsp_o.data, ctrl.enable, ctrl.prsc, ctrl.cdiv, ctrl.clkstr, clk_gen.tick, clk_gen.cnt, clk_gen.phase_gen, clk_gen.phase_gen_ff, io_con.sda_in_ff, io_con.scl_in_ff, io_con.sda_out, io_con.scl_out, engine.state, engine.bitcnt, engine.sreg, engine.done, irq_o
  - **evidence** — Used in rising_edge(clk_i) in multiple processes: bus_access, irq_generator, clock_generator, phase_generator, twi_engine.

**`clkgen_en_o`** — neorv32_twi · `std_ulogic`
  - **functionality** — Forwards the internal ctrl.enable bit to the outside as the clock-generator enable signal.
  - **roles** — exported enable; carries ctrl.enable
  - **relationships** — **CARRIES** → ctrl.enable
  - **evidence** — Concurrent assignment: clkgen_en_o <= ctrl.enable.

**`clkgen_i`** — neorv32_twi · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Provides selectable phase-enable bits; a single bit, indexed by ctrl.prsc, is tested in the clock_generator to gate cnt increments and ticking.
  - **roles** — clock selection bits; constrains tick generation
  - **relationships** — **CONSTRAINS** → clk_gen.tick, clk_gen.cnt
  - **evidence** — Tested as clkgen_i(to_integer(unsigned(ctrl.prsc))) = '1' in clock_generator process to gate counting/tick logic.

**`rstn_i`** — neorv32_twi · `std_ulogic`
  - **functionality** — Provides an asynchronous active-low reset that clears control, engine and clock-generator registers and initializes outputs in each process' reset branch.
  - **roles** — reset source; initialises registers; asynchronous reset for clocked processes
  - **relationships** — **SEQUENCES** → bus_rsp_o.ack, bus_rsp_o.err, bus_rsp_o.data, ctrl.enable, ctrl.prsc, ctrl.cdiv, ctrl.clkstr, clk_gen.tick, clk_gen.cnt, clk_gen.phase_gen, clk_gen.phase_gen_ff, io_con.sda_in_ff, io_con.scl_in_ff, io_con.sda_out, io_con.scl_out, engine.state, engine.bitcnt, engine.sreg, engine.done, irq_o
  - **evidence** — Tested as if (rstn_i = '0') then ... in reset branches of all clocked processes.

**`twi_scl_i`** — neorv32_twi · `std_ulogic`
  - **functionality** — Converted and provided as io_con.scl_in, then sampled into io_con.scl_in_ff for stretch detection and engine use.
  - **roles** — clock input; feeds io_con sampling chain
  - **relationships** — **SOURCES** → io_con.scl_in
  - **evidence** — Assigned: io_con.scl_in <= to_stdulogic(to_bit(twi_scl_i)).

**`twi_scl_o`** — neorv32_twi · `std_ulogic`
  - **functionality** — Drives the external SCL pin from the internal io_con.scl_out signal (forwarded combinationally).
  - **roles** — clock output; carries io_con.scl_out to external pin
  - **relationships** — **CARRIES** → io_con.scl_out
  - **evidence** — Concurrent assignment: twi_scl_o <= io_con.scl_out.

### signals

**`clk_gen`** — neorv32_twi · `clk_gen_t`
  - **functionality** — Holds internal clock-generation state (cnt,tick,phase_gen,phase_gen_ff,phase,halt) used to produce phased SCL/SDA control and ticks consumed by the engine and FIFO read pacing.
  - **roles** — clock generation state; holds counter and phase shift registers; feeds engine timing signals
  - **relationships** — **AGGREGATES** → clk_gen.cnt, clk_gen.tick, clk_gen.halt, clk_gen.phase_gen, clk_gen.phase_gen_ff, clk_gen.phase
  - **evidence** — clk_gen is a record with fields updated across clock_generator, phase_generator and concurrent assignments (phase, halt).

**`clk_gen.cnt`** — neorv32_twi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Counts up while ctrl.enable and the selected clkgen_i bit is '1'; compared to ctrl.cdiv to produce a tick and reset the counter on equality.
  - **roles** — tick counter; registered counter for divider
  - **relationships** — **CAPTURES** → clk_i; **CONSTRAINS** → clk_gen.tick; **DERIVES_FROM** → clk_gen.cnt, ctrl.cdiv, clkgen_i, ctrl.enable
  - **evidence** — Updated in clock_generator: increments or reset when (clk_gen.cnt = ctrl.cdiv) and gated by clkgen_i(index) and ctrl.enable.

**`clk_gen.halt`** — neorv32_twi · `std_ulogic`
  - **functionality** — Combinationally asserted when scl_out='1' and sampled scl_in_ff(1)='0' and ctrl.clkstr='1', preventing phase advancement (clock stretching).
  - **roles** — clock-stretch indicator; gates phase generator
  - **relationships** — **DERIVES_FROM** → io_con.scl_out, io_con.scl_in_ff, ctrl.clkstr
  - **evidence** — clk_gen.halt <= '1' when (io_con.scl_out = '1') and (io_con.scl_in_ff(1) = '0') and (ctrl.clkstr = '1') else '0'.

**`clk_gen.phase`** — neorv32_twi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Combinationally derived pulses from phase_gen_ff and phase_gen to indicate phase edges (phase(n) = phase_gen_ff(n) and not phase_gen(n)).
  - **roles** — phase pulses; combinational timing signals
  - **relationships** — **DERIVES_FROM** → clk_gen.phase_gen_ff, clk_gen.phase_gen
  - **evidence** — clk_gen.phase(i) <= clk_gen.phase_gen_ff(i) and (not clk_gen.phase_gen(i)) for i=0..3.

**`clk_gen.phase_gen`** — neorv32_twi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Holds the rotating one-hot phase pattern used to generate phases; shifted on each tick when not halted and loaded to default when disabled.
  - **roles** — phase shift register; registered phase pattern
  - **relationships** — **CAPTURES** → clk_i, rstn_i; **DERIVES_FROM** → clk_gen.phase_gen, clk_gen.tick, clk_gen.halt, ctrl.enable, engine.busy
  - **evidence** — Assigned in phase_generator process: shifts when clk_gen.tick='1' and clk_gen.halt='0', reset or initialized when disabled or engine.busy='0'.

**`clk_gen.phase_gen_ff`** — neorv32_twi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — A one-cycle delayed copy of phase_gen used to derive phase edges; updated each clock from phase_gen.
  - **roles** — phase pipeline stage; registered phase snapshot
  - **relationships** — **CAPTURES** → clk_i; **SOURCES** → clk_gen.phase
  - **evidence** — clk_gen.phase_gen_ff <= clk_gen.phase_gen executed in phase_generator process; clk_gen.phase uses phase_gen_ff combinationally.

**`clk_gen.tick`** — neorv32_twi · `std_ulogic`
  - **functionality** — One-cycle pulse generated when clk_gen.cnt equals ctrl.cdiv while the selected clkgen_i bit is set; used to pace engine start and FIFO reads.
  - **roles** — tick pulse; paced by counter and selection; drives engine/FIFO timing
  - **relationships** — **DERIVES_FROM** → clk_gen.cnt, ctrl.cdiv, clkgen_i, ctrl.prsc; **SOURCES** → fifo.tx_re, engine
  - **evidence** — clk_gen.tick set to '1' when clk_gen.cnt = ctrl.cdiv and clkgen_i(index) = '1' (clock_generator); used in fifo.tx_re condition and engine start logic.

**`ctrl`** — neorv32_twi · `ctrl_t`
  - **functionality** — Holds TWI configuration fields (enable, prsc, cdiv, clkstr) written by bus writes and read back on CSR reads; supplies clocking and engine configuration.
  - **roles** — configuration register group; holds controller settings; feeds clock generator and engine
  - **relationships** — **AGGREGATES** → ctrl.enable, ctrl.prsc, ctrl.cdiv, ctrl.clkstr
  - **evidence** — ctrl is a record signal whose fields are assigned in bus_access process from bus_req_i.data.

**`ctrl.clkstr`** — neorv32_twi · `std_ulogic`
  - **functionality** — Set by bus writes and used to qualify clk_gen.halt (clock stretching detection) and reported in CSR reads; gates halting of phase generator when stretch detected.
  - **roles** — clock-stretch enable; registered configuration; gates halt detection
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → clk_gen.halt
  - **evidence** — ctrl.clkstr <= bus_req_i.data(ctrl_clkstr_en_c) in bus_access; used in clk_gen.halt concurrent assignment.

**`engine`** — neorv32_twi · `engine_t`
  - **functionality** — Holds engine state, bit counter, shift register and completion flag; coordinates bit-level SCL/SDA activity according to phases and TX FIFO commands.
  - **roles** — engine register group; manages serial transfer state; drives io_con outputs and RX assembly
  - **relationships** — **AGGREGATES** → engine.state, engine.bitcnt, engine.sreg, engine.done, engine.busy
  - **evidence** — engine record fields are assigned inside twi_engine process and used across the design (state machine, shifting and FIFO interfacing).

**`engine.bitcnt`** — neorv32_twi · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Counts bits transmitted/received; incremented on phase(3) and compared to a terminal value to generate engine.done and control SDA behaviour.
  - **roles** — per-transaction bit counter; registered counter; constrains done condition
  - **relationships** — **CAPTURES** → clk_i; **CONSTRAINS** → engine.done, io_con.sda_out
  - **evidence** — engine.bitcnt incremented when clk_gen.phase(3) = '1' and tested for equality to "1001" to set engine.done and affect SDA output.

**`engine.busy`** — neorv32_twi · `std_ulogic`
  - **functionality** — Combinationally derived from engine.state to indicate that a transfer is in progress (state(2)=1 and state(1..0) != "00").
  - **roles** — busy status signal; reflects active engine state
  - **relationships** — **REFLECTS** → engine.state; **SOURCES** → bus_rsp_o.data, irq_o
  - **evidence** — engine.busy <= '1' when (engine.state(2) = '1') and (engine.state(1 downto 0) /= "00") else '0'.

**`engine.done`** — neorv32_twi · `std_ulogic`
  - **functionality** — Set when a byte-transfer completes (checked with bitcnt and phase), and cleared each clock; used to write received data into RX FIFO.
  - **roles** — completion flag; registered event indicator
  - **relationships** — **CAPTURES** → clk_i; **SOURCES** → fifo.rx_we
  - **evidence** — engine.done <= '1' set inside twi_engine when conditions met; fifo.rx_we <= engine.done.

**`engine.sreg`** — neorv32_twi · `std_ulogic_vector(8 downto 0)`
  - **functionality** — Loaded from fifo.tx_rdata at transaction start and shifted/updated from SDA input during transfers; supplies RX FIFO write data and drives SDA output bits.
  - **roles** — shift register; supplies RX FIFO payload; drives SDA transmit bit
  - **relationships** — **CAPTURES** → fifo.tx_rdata; **SOURCES** → fifo.rx_wdata, io_con.sda_out; **DERIVES_FROM** → io_con.sda_in_ff
  - **evidence** — engine.sreg <= fifo.tx_rdata(...) & (not fifo.tx_rdata(dcmd_ack_c)) and later shifted with io_con.sda_in_ff(1) inside twi_engine; fifo.rx_wdata built from engine.sreg.

**`engine.state`** — neorv32_twi · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Registers the 3-bit engine state; bit2 is fed by ctrl.enable and the 2 LSBs select the engine case that drives sda/scl outputs and sreg/bitcnt behavior.
  - **roles** — state register; chooses engine behaviour; holds enable sample
  - **relationships** — **CAPTURES** → ctrl.enable, fifo.tx_rdata; **SELECTS** → engine.bitcnt, engine.sreg, io_con.sda_out, io_con.scl_out, engine.done
  - **evidence** — engine.state(2) <= ctrl.enable; case engine.state is used in twi_engine to assign bitcnt, sreg, io_con outputs and done.

**`fifo`** — neorv32_twi · `fifo_t`
  - **functionality** — Groups control and data signals that interface to the TX/RX FIFO instances and to the engine; fields carry write/read enables, data and status between engine, bus and FIFO instances.
  - **roles** — FIFO port bundle; carries FIFO control and data; connects FIFOs to engine and bus logic
  - **relationships** — **AGGREGATES** → fifo.clear, fifo.rx_we, fifo.tx_we, fifo.rx_re, fifo.tx_re, fifo.rx_wdata, fifo.rx_rdata, fifo.tx_wdata, fifo.tx_rdata, fifo.rx_avail, fifo.tx_avail, fifo.rx_free, fifo.tx_free
  - **evidence** — fifo record declared and individual fields connected to instantiated FIFO ports and to engine/bus logic in port maps and concurrent assignments.

**`fifo.clear`** — neorv32_twi · `std_ulogic`
  - **functionality** — Driven as the inverted ctrl.enable and routed to the FIFO instances' clear inputs to assert FIFO clear when controller disabled.
  - **roles** — FIFO clear signal; forwards inverted enable to instances
  - **relationships** — **DERIVES_FROM** → ctrl.enable; **SOURCES** → tx_fifo_inst.clear_i, rx_fifo_inst.clear_i
  - **evidence** — fifo.clear <= not ctrl.enable; connected to clear_i in both tx_fifo_inst and rx_fifo_inst port maps.

**`fifo.rx_avail`** — neorv32_twi · `std_ulogic`
  - **functionality** — Provided by the RX FIFO instance indicating data available; used in bus read status and returned in CSR reads.
  - **roles** — RX FIFO status; reports data availability
  - **relationships** — **SOURCES** → bus_rsp_o.data; **SOURCES** → rx_fifo_inst.avail_o
  - **evidence** — rx_fifo_inst avail_o => fifo.rx_avail in port map; used in bus_access to set bus_rsp_o.data(ctrl_rx_avail_c).

**`fifo.rx_free`** — neorv32_twi · `std_ulogic`
  - **functionality** — Provided by the RX FIFO instance but not used by this entity's logic except present in the FIFO bundle and connected to instance free_o.
  - **roles** — RX FIFO status (unused)
  - **relationships** — **SOURCES** → rx_fifo_inst.free_o
  - **evidence** — rx_fifo_inst free_o => fifo.rx_free in port map; not referenced elsewhere.

**`fifo.rx_rdata`** — neorv32_twi · `std_ulogic_vector(8 downto 0)`
  - **functionality** — Receives rdata from the RX FIFO instance and is returned to the bus on reads (mapped to bus_rsp_o.data(8 downto 0)).
  - **roles** — RX FIFO output; provides data to bus reads
  - **relationships** — **SOURCES** → bus_rsp_o.data; **SOURCES** → rx_fifo_inst.rdata_o
  - **evidence** — rx_fifo_inst rdata_o => fifo.rx_rdata in port map; used in bus_access: bus_rsp_o.data(8 downto 0) <= fifo.rx_rdata.

**`fifo.rx_re`** — neorv32_twi · `std_ulogic`
  - **functionality** — Asserted when the bus performs a read to the FIFO address (bus_req_i.stb & rw='0' & addr(2)=1); presented to RX FIFO re_i.
  - **roles** — RX FIFO read enable; driven by bus read requests
  - **relationships** — **DERIVES_FROM** → bus_req_i.stb, bus_req_i.rw, bus_req_i.addr; **SOURCES** → rx_fifo_inst.re_i
  - **evidence** — fifo.rx_re <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '0') and (bus_req_i.addr(2) = '1') else '0'; mapped to rx_fifo_inst.re_i.

**`fifo.rx_wdata`** — neorv32_twi · `std_ulogic_vector(8 downto 0)`
  - **functionality** — Carries the assembled received byte from engine.sreg into the RX FIFO wdata input as a 9-bit vector.
  - **roles** — RX FIFO payload; forwarded from engine.sreg
  - **relationships** — **DERIVES_FROM** → engine.sreg; **SOURCES** → rx_fifo_inst.wdata_i
  - **evidence** — fifo.rx_wdata <= engine.sreg(0) & engine.sreg(8 downto 1); mapped to rx_fifo_inst.wdata_i.

**`fifo.rx_we`** — neorv32_twi · `std_ulogic`
  - **functionality** — Asserted by the engine's done signal to push received bytes into the RX FIFO; mapped to the RX FIFO instance we_i.
  - **roles** — RX FIFO write enable; driven by engine completion
  - **relationships** — **DERIVES_FROM** → engine.done; **SOURCES** → rx_fifo_inst.we_i
  - **evidence** — fifo.rx_we <= engine.done; rx_fifo_inst port map connects we_i => fifo.rx_we.

**`fifo.tx_avail`** — neorv32_twi · `std_ulogic`
  - **functionality** — Indicates TX FIFO has data (avail) from the TX FIFO instance; used to start engine transactions and reported in CSR busy calculation.
  - **roles** — TX FIFO status; triggers engine start; reported in status CSR
  - **relationships** — **SOURCES** → engine.state, bus_rsp_o.data; **SOURCES** → tx_fifo_inst.avail_o
  - **evidence** — tx_fifo_inst avail_o => fifo.tx_avail; used in fifo.tx_re condition and in bus_access to compute ctrl_busy_c.

**`fifo.tx_free`** — neorv32_twi · `std_ulogic`
  - **functionality** — Indicates TX FIFO free (not full) as provided by the TX FIFO instance; used in CSR read as ctrl_tx_full (inverted) and in bus_rsp_o.data mapping.
  - **roles** — TX FIFO status; reported in CSR
  - **relationships** — **SOURCES** → bus_rsp_o.data; **SOURCES** → tx_fifo_inst.free_o
  - **evidence** — tx_fifo_inst free_o => fifo.tx_free in port map; bus_access reads fifo.tx_free to drive bus_rsp_o.data(ctrl_tx_full_c) as not fifo.tx_free.

**`fifo.tx_rdata`** — neorv32_twi · `std_ulogic_vector(10 downto 0)`
  - **functionality** — Holds the command word read from the TX FIFO instance; consumed by the engine to load sreg and decide the command bits.
  - **roles** — TX FIFO output; supplies engine command word
  - **relationships** — **SOURCES** → engine.sreg, engine.state; **SOURCES** → tx_fifo_inst.rdata_o
  - **evidence** — tx_fifo_inst rdata_o => fifo.tx_rdata; used in twi_engine to load engine.sreg and engine.state bits.

**`fifo.tx_re`** — neorv32_twi · `std_ulogic`
  - **functionality** — Issued to read the next TX command when engine is idle, TX FIFO has data and clk tick occurs; mapped to TX FIFO re_i to consume commands into engine.
  - **roles** — TX FIFO read request; gated by engine and clock
  - **relationships** — **DERIVES_FROM** → engine.busy, fifo.tx_avail, clk_gen.tick; **SOURCES** → tx_fifo_inst.re_i
  - **evidence** — fifo.tx_re <= '1' when (engine.busy = '0') and (fifo.tx_avail = '1') and (clk_gen.tick = '1') else '0'; mapped to tx_fifo_inst.re_i.

**`fifo.tx_wdata`** — neorv32_twi · `std_ulogic_vector(10 downto 0)`
  - **functionality** — Carries the command word written by the bus (dcmd_cmd_hi_c downto dcmd_lsb_c) into the TX FIFO wdata input.
  - **roles** — TX FIFO payload; driven by bus write data
  - **relationships** — **DERIVES_FROM** → bus_req_i.data; **SOURCES** → tx_fifo_inst.wdata_i
  - **evidence** — fifo.tx_wdata <= bus_req_i.data(dcmd_cmd_hi_c downto dcmd_lsb_c); mapped to tx_fifo_inst.wdata_i.

**`fifo.tx_we`** — neorv32_twi · `std_ulogic`
  - **functionality** — Asserted when a bus write to the TX FIFO address occurs (bus_req_i.stb & rw & addr(2)=1); drives the TX FIFO we_i input.
  - **roles** — TX FIFO write enable; gated by bus write; exports to TX FIFO instance
  - **relationships** — **DERIVES_FROM** → bus_req_i.stb, bus_req_i.rw, bus_req_i.addr; **SOURCES** → tx_fifo_inst.we_i
  - **evidence** — fifo.tx_we <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.addr(2) = '1') else '0'; mapped to tx_fifo_inst.we_i.

**`io_con`** — neorv32_twi · `io_con_t`
  - **functionality** — Groups sampled inputs, direct inputs and outputs for SDA/SCL (sda_in_ff,scl_in_ff,sda_in,scl_in,sda_out,scl_out); mediates pin conversions and provides drive/monitor signals to the engine and CSR.
  - **roles** — IO sampling/drive bundle; connects pins to engine and status logic
  - **relationships** — **AGGREGATES** → io_con.sda_in_ff, io_con.scl_in_ff, io_con.sda_in, io_con.scl_in, io_con.sda_out, io_con.scl_out
  - **evidence** — io_con record declared and its fields are assigned in twi_engine, by pin conversions and used elsewhere (phase halt, CSR).

**`io_con.scl_in`** — neorv32_twi · `std_ulogic`
  - **functionality** — Combinationally converted from the external twi_scl_i pin and presented to the SCL sampler chain.
  - **roles** — pin-converted input; feeds scl_in_ff
  - **relationships** — **DERIVES_FROM** → twi_scl_i
  - **evidence** — io_con.scl_in <= to_stdulogic(to_bit(twi_scl_i)).

**`io_con.scl_in_ff`** — neorv32_twi · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Two-stage sampled version of SCL input; MSB is used for stretch detection and reported in CSR.
  - **roles** — input sampler; provides stable SCL sample
  - **relationships** — **CAPTURES** → io_con.scl_in; **SOURCES** → bus_rsp_o.data, clk_gen.halt
  - **evidence** — io_con.scl_in_ff <= io_con.scl_in_ff(0) & io_con.scl_in in twi_engine; io_con.scl_in_ff(1) used in bus_rsp_o.data and clk_gen.halt.

**`io_con.scl_out`** — neorv32_twi · `std_ulogic`
  - **functionality** — Registered drive level for SCL controlled by the engine and phase signals; forwarded to external twi_scl_o and used in halt detection.
  - **roles** — SCL drive register; drives external SCL pin; used for stretch detection
  - **relationships** — **CAPTURES** → engine.state, clk_gen.phase; **SOURCES** → twi_scl_o, clk_gen.halt
  - **evidence** — io_con.scl_out assigned in twi_engine branches; twi_scl_o <= io_con.scl_out and clk_gen.halt uses io_con.scl_out.

**`io_con.sda_in`** — neorv32_twi · `std_ulogic`
  - **functionality** — Combinationally converted from the external twi_sda_i pin and provided to the input sampler chain.
  - **roles** — pin-converted input; feeds sda_in_ff
  - **relationships** — **DERIVES_FROM** → twi_sda_i
  - **evidence** — io_con.sda_in <= to_stdulogic(to_bit(twi_sda_i)).

**`io_con.sda_in_ff`** — neorv32_twi · `std_ulogic_vector(1 downto 0)`
  - **functionality** — A two-bit shift that samples io_con.sda_in each clock (shift register); the MSB is used by the engine as the stable sampled SDA input and reported in CSR.
  - **roles** — input sampler; provides stable SDA sample; registered input pipeline
  - **relationships** — **CAPTURES** → io_con.sda_in; **SOURCES** → bus_rsp_o.data, engine.sreg, clk_gen.halt
  - **evidence** — io_con.sda_in_ff <= io_con.sda_in_ff(0) & io_con.sda_in in twi_engine; io_con.sda_in_ff(1) read into bus_rsp_o.data and engine.sreg; used in clk_gen.halt condition.

**`io_con.sda_out`** — neorv32_twi · `std_ulogic`
  - **functionality** — Registered drive level for SDA controlled by the engine state and phase logic; forwarded to the external twi_sda_o pin.
  - **roles** — SDA drive register; drives external SDA pin
  - **relationships** — **CAPTURES** → engine.state, clk_gen.phase; **SOURCES** → twi_sda_o
  - **evidence** — io_con.sda_out assigned in twi_engine case branches; twi_sda_o <= io_con.sda_out.


## neorv32_uart  (66 non-assets)

### ports

**`bus_req_i`** — neorv32_uart · `bus_req_t`
  - **functionality** — Carries bus transaction fields into the UART. The process bus_access reads its fields and uses them to update ctrl fields on writes and to form bus responses on reads, and other concurrent logic uses its fields for FIFO access.
  - **roles** — bus request carrier; controls register updates; gates FIFO accesses
  - **relationships** — **SOURCES** → ctrl.enable, ctrl.sim_mode, ctrl.hwfc_en, ctrl.prsc, ctrl.baud, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.clr_rx, ctrl.clr_tx, tx_fifo.wdata; **GATES** → ctrl.enable, ctrl.sim_mode, ctrl.hwfc_en, ctrl.prsc, ctrl.baud, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.clr_rx, ctrl.clr_tx, bus_rsp_o.data, tx_fifo.we, rx_fifo.re, bus_rsp_o.ack
  - **evidence** — bus_access process uses bus_req_i.stb/rw/addr/data to drive ctrl fields and FIFO enables and to form bus_rsp_o

**`bus_req_i.addr`** — neorv32_uart · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Provides the address bit(s) that select control vs data registers. The LSB bit addr(2) gates which ctrl fields are written or which response/data slice is returned on reads and also appears in simulation transmit condition.
  - **roles** — register selector; gates bus read/write targets
  - **relationships** — **GATES** → ctrl.enable, ctrl.sim_mode, ctrl.hwfc_en, ctrl.prsc, ctrl.baud, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.clr_rx, ctrl.clr_tx, bus_rsp_o.data, tx_fifo.we, rx_fifo.re, tx_fifo.wdata
  - **evidence** — if (bus_req_i.addr(2) = '0') then branches in bus_access and tx/rx FIFO we/re assignments and sim_tx condition

**`bus_req_i.amo`** — neorv32_uart · `std_ulogic`
  - **functionality** — Atomic memory operation flag is declared but not referenced by this UART implementation.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond declaration

**`bus_req_i.amoop`** — neorv32_uart · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared AMO operation subfield is not used in the entity's logic.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond declaration

**`bus_req_i.ben`** — neorv32_uart · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared bus byte-enable field is not read or used by this source; no process or assignment references it.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrence except DECL in provided source

**`bus_req_i.data`** — neorv32_uart · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies write data for control registers and TX FIFO. On writes it is sampled into ctrl fields and is mapped to tx_fifo.wdata for transmit requests; in simulation mode the lower byte is read for printing.
  - **roles** — write data source; feeds configuration and TX payload
  - **relationships** — **SOURCES** → ctrl.enable, ctrl.sim_mode, ctrl.hwfc_en, ctrl.prsc, ctrl.baud, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.clr_rx, ctrl.clr_tx, tx_fifo.wdata
  - **evidence** — bus_req_i.data(...) reads in bus_access and tx_fifo.wdata <= bus_req_i.data(7 downto 0)

**`bus_req_i.debug`** — neorv32_uart · `std_ulogic`
  - **functionality** — Declared but not read or used by any logic in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond declaration

**`bus_req_i.fence`** — neorv32_uart · `std_ulogic`
  - **functionality** — Declared but not referenced; the UART logic does not use fence information.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond declaration

**`bus_req_i.lock`** — neorv32_uart · `std_ulogic`
  - **functionality** — Declared lock field is not read or used by any logic in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond declaration

**`bus_req_i.priv`** — neorv32_uart · `std_ulogic`
  - **functionality** — Declared but not referenced in the provided source, so it has no role inside this entity.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond declaration

**`bus_req_i.rw`** — neorv32_uart · `std_ulogic`
  - **functionality** — Distinguishes read and write transfers inside bus_access and thereby gates whether ctrl fields are written or bus response/data are prepared; it appears in conditional branches controlling write vs read behaviour.
  - **roles** — read/write selector; gates write vs read paths
  - **relationships** — **GATES** → ctrl.enable, ctrl.sim_mode, ctrl.hwfc_en, ctrl.prsc, ctrl.baud, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.clr_rx, ctrl.clr_tx, bus_rsp_o.data, tx_fifo.we, rx_fifo.re
  - **evidence** — if (bus_req_i.rw = '1') then / else in bus_access chooses write or read branches

**`bus_req_i.src`** — neorv32_uart · `std_ulogic`
  - **functionality** — Declared bus source field is not read by this entity; no assignments or conditions reference it in this source.
  - **roles** — unused bus field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — no occurrences beyond declaration

**`bus_req_i.stb`** — neorv32_uart · `std_ulogic`
  - **functionality** — Indicates a valid bus transfer and both gates bus_access updates and directly sources bus response acknowledge and FIFO write/read enables. It is used as a condition and as the direct source of bus_rsp_o.ack.
  - **roles** — transaction qualifier; gates bus_access updates; directly sources bus_resp ack
  - **relationships** — **GATES** → ctrl.enable, ctrl.sim_mode, ctrl.hwfc_en, ctrl.prsc, ctrl.baud, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.clr_rx, ctrl.clr_tx, bus_rsp_o.data, tx_fifo.we, rx_fifo.re; **SOURCES** → bus_rsp_o.ack
  - **evidence** — if (bus_req_i.stb = '1') then in bus_access; bus_rsp_o.ack <= bus_req_i.stb; tx_fifo.we and rx_fifo.re use bus_req_i.stb

**`bus_rsp_o`** — neorv32_uart · `bus_rsp_t`
  - **functionality** — Provides the bus response back to the requester. The clocked bus_access process drives its fields (ack, err, data) each cycle to report ack and to return control or data fields derived from ctrl and FIFOs.
  - **roles** — response carrier; reports register and FIFO status; synchronised output
  - **relationships** — **CAPTURES** → bus_req_i.stb, bus_req_i.addr, ctrl.enable, ctrl.sim_mode, ctrl.hwfc_en, ctrl.prsc, ctrl.baud, rx_fifo.avail, rx_fifo.half, rx_fifo.free, tx_fifo.avail, tx_fifo.half, tx_fifo.free, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, rx_engine.over, tx_engine.busy
  - **evidence** — bus_access process (rising_edge(clk_i)) assigns bus_rsp_o.ack/err/data and slices from ctrl and FIFO signals

**`bus_rsp_o.ack`** — neorv32_uart · `std_ulogic`
  - **functionality** — Holds the sampled bus strobe to acknowledge a transaction. It is set each clock to bus_req_i.stb inside the clocked bus_access process.
  - **roles** — acknowledge output; synchronised to bus
  - **relationships** — **CAPTURES** → bus_req_i.stb
  - **evidence** — bus_rsp_o.ack <= bus_req_i.stb inside bus_access rising_edge(clk_i)

**`bus_rsp_o.data`** — neorv32_uart · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Delivers returned register or FIFO data on reads. The bus_access clocked process clears it each cycle and then assigns slices derived from ctrl fields, FIFO indicators and engine status into specific bit positions.
  - **roles** — read data output; aggregate of control and FIFO status
  - **relationships** — **CAPTURES** → ctrl.enable, ctrl.sim_mode, ctrl.hwfc_en, ctrl.prsc, ctrl.baud, rx_fifo.avail, rx_fifo.half, rx_fifo.free, tx_fifo.avail, tx_fifo.half, tx_fifo.free, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, rx_engine.over, tx_engine.busy, rx_fifo.rdata, log2_rx_fifo_c, log2_tx_fifo_c
  - **evidence** — bus_rsp_o.data <= (others => '0') and many slice assignments in bus_access process

**`bus_rsp_o.err`** — neorv32_uart · `std_ulogic`
  - **functionality** — Reports an error status (always '0' here). It is cleared on every clock by the bus_access process.
  - **roles** — response error flag; synchronised output
  - **relationships** — **CAPTURES** → _(none)_
  - **evidence** — bus_rsp_o.err <= '0' in bus_access process (rising_edge(clk_i))

**`clk_i`** — neorv32_uart · `std_ulogic`
  - **functionality** — Supplies the rising edge used to sequence internal registers and port outputs. It times the bus_access, transmitter, receiver, IRQ, FIFO-overrun and control processes and thereby controls updates to ctrl, tx_engine, rx_engine and outputs.
  - **roles** — clock source; sequences internal registers; synchronises bus and UART engines
  - **relationships** — **SEQUENCES** → bus_rsp_o, ctrl.enable, ctrl.sim_mode, ctrl.hwfc_en, ctrl.prsc, ctrl.baud, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.clr_rx, ctrl.clr_tx, tx_engine.cts, tx_engine.done, tx_engine.state, tx_engine.baudcnt, tx_engine.bitcnt, tx_engine.sreg, tx_engine.txd, rx_engine.sync, rx_engine.done, rx_engine.state, rx_engine.baudcnt, rx_engine.bitcnt, rx_engine.sreg, rx_engine.over, rx_fifo.clear, tx_fifo.clear, irq_tx_o, irq_rx_o, uart_rtsn_o
  - **evidence** — rising_edge(clk_i) appears in all named processes (bus_access, transmitter, receiver, irq generators, fifo_overrun, rtr_control)

**`clkgen_i`** — neorv32_uart · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Supplies prescaled clock bits; an indexed bit of this vector is sampled to produce uart_clk. The concurrent assignment reads clkgen_i at the index derived from ctrl.prsc.
  - **roles** — clock source vector; feeds internal uart clock
  - **relationships** — **SOURCES** → uart_clk
  - **evidence** — uart_clk <= clkgen_i(to_integer(unsigned(ctrl.prsc))) concurrent assignment

**`rstn_i`** — neorv32_uart · `std_ulogic`
  - **functionality** — Provides synchronous/asynchronous reset used by processes to initialise registers and outputs. It clears ctrl fields, engine state, FIFOs and IRQ outputs in each process's reset branch.
  - **roles** — reset source; initialises registers; synchronises reset behaviour
  - **relationships** — **SEQUENCES** → bus_rsp_o, ctrl.enable, ctrl.sim_mode, ctrl.hwfc_en, ctrl.prsc, ctrl.baud, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.clr_rx, ctrl.clr_tx, tx_engine.cts, tx_engine.done, tx_engine.state, tx_engine.baudcnt, tx_engine.bitcnt, tx_engine.sreg, tx_engine.txd, rx_engine.sync, rx_engine.done, rx_engine.state, rx_engine.baudcnt, rx_engine.bitcnt, rx_engine.sreg, rx_engine.over, irq_tx_o, irq_rx_o, uart_rtsn_o
  - **evidence** — if (rstn_i = '0') then branches in each process (bus_access, transmitter, receiver, irq generators, fifo_overrun, rtr_control)

### signals

**`ctrl`** — neorv32_uart · `ctrl_t`
  - **functionality** — Holds the UART configuration and IRQ enable/clear bits. Individual fields are captured from bus_req_i.data on writes in the bus_access clocked process and used across the entity to control engines, IRQs, and FIFO behaviour.
  - **roles** — configuration register file; holds enabled state; provides flags to engines and outputs
  - **relationships** — **CAPTURES** → bus_req_i.data; **AGGREGATES** → ctrl.enable, ctrl.sim_mode, ctrl.hwfc_en, ctrl.prsc, ctrl.baud, ctrl.irq_rx_nempty, ctrl.irq_rx_half, ctrl.irq_rx_full, ctrl.irq_tx_empty, ctrl.irq_tx_nhalf, ctrl.clr_rx, ctrl.clr_tx
  - **evidence** — bus_access process assigns ctrl.<fields> from bus_req_i.data on writes; ctrl fields used elsewhere

**`ctrl.clr_rx`** — neorv32_uart · `std_ulogic`
  - **functionality** — A writeable bit that is cleared each cycle and when asserted by a bus write causes rx_fifo.clear to be asserted (which forces the RX FIFO clear). It is captured from bus_req_i.data and cleared in bus_access between cycles.
  - **roles** — write-clear flag; gates rx_fifo.clear
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → rx_fifo.clear
  - **evidence** — ctrl.clr_rx <= bus_req_i.data(ctrl_rx_clr_c) in bus_access; ctrl.clr_rx is reset to '0' in same process and rx_fifo.clear uses ctrl.clr_rx

**`ctrl.clr_tx`** — neorv32_uart · `std_ulogic`
  - **functionality** — Writeable bit captured from bus writes that causes tx_fifo.clear to assert when set; it is cleared each cycle in bus_access to behave as a write-clear strobe.
  - **roles** — write-clear flag; gates tx_fifo.clear
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → tx_fifo.clear
  - **evidence** — ctrl.clr_tx <= bus_req_i.data(ctrl_tx_clr_c) in bus_access; tx_fifo.clear <= ... or ctrl.clr_tx = '1'

**`ctrl.hwfc_en`** — neorv32_uart · `std_ulogic`
  - **functionality** — Captures the hardware-flow-control enable from bus writes and is used to decide RTS behaviour and to qualify CTS usage in the transmit state machine.
  - **roles** — held hwfc enable; gates RTS and CTS handling
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → uart_rtsn_o, tx_engine.state
  - **evidence** — ctrl.hwfc_en <= bus_req_i.data(ctrl_hwfc_en_c) in bus_access; rtr_control uses ctrl.hwfc_en; transmitter tests ctrl.hwfc_en in state transitions

**`ctrl.irq_rx_full`** — neorv32_uart · `std_ulogic`
  - **functionality** — Held enable bit for RX full interrupt, captured from bus writes and used to compute irq_rx_o when rx_fifo.free is false.
  - **roles** — IRQ enable bit; gates RX full interrupt
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → irq_rx_o
  - **evidence** — ctrl.irq_rx_full <= bus_req_i.data(ctrl_irq_rx_full_c); rx_irq_generator uses ctrl.irq_rx_full and rx_fifo.free

**`ctrl.irq_rx_half`** — neorv32_uart · `std_ulogic`
  - **functionality** — Held enable bit for RX half-full interrupt; sampled from bus writes and used by rx_irq_generator together with rx_fifo.half.
  - **roles** — IRQ enable bit; gates RX half interrupt
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → irq_rx_o
  - **evidence** — ctrl.irq_rx_half <= bus_req_i.data(ctrl_irq_rx_half_c); used in rx_irq_generator

**`ctrl.irq_rx_nempty`** — neorv32_uart · `std_ulogic`
  - **functionality** — Captures the enable bit for RX non-empty interrupts from bus writes and is read by the rx_irq_generator to decide irq_rx_o assertion when rx_fifo.avail is true.
  - **roles** — IRQ enable bit; gates RX non-empty interrupt
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → irq_rx_o
  - **evidence** — ctrl.irq_rx_nempty <= bus_req_i.data(ctrl_irq_rx_nempty_c); rx_irq_generator uses ctrl.irq_rx_nempty

**`ctrl.irq_tx_empty`** — neorv32_uart · `std_ulogic`
  - **functionality** — Captured TX-empty interrupt enable bit; used by tx_irq_generator to assert irq_tx_o when TX FIFO becomes empty (not tx_fifo.avail).
  - **roles** — IRQ enable bit; gates TX empty interrupt
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → irq_tx_o
  - **evidence** — ctrl.irq_tx_empty <= bus_req_i.data(ctrl_irq_tx_empty_c); tx_irq_generator uses ctrl.irq_tx_empty

**`ctrl.irq_tx_nhalf`** — neorv32_uart · `std_ulogic`
  - **functionality** — Captured bit enabling TX near-half interrupt; tx_irq_generator uses it with tx_fifo.half to produce irq_tx_o.
  - **roles** — IRQ enable bit; gates TX near-half interrupt
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → irq_tx_o
  - **evidence** — ctrl.irq_tx_nhalf <= bus_req_i.data(ctrl_irq_tx_nhalf_c); used in tx_irq_generator

**`ctrl.sim_mode`** — neorv32_uart · `std_ulogic`
  - **functionality** — Holds the sim-mode enable written from the bus and gates simulation transmitter and FIFO clears. It is derived from bus_req_i.data and the SIM_MODE_EN generic and is used to force TX FIFO clear and to enable sim_tx path.
  - **roles** — held sim-mode flag; gates sim behaviour; affects FIFO clear
  - **relationships** — **CAPTURES** → bus_req_i.data; **GATES** → tx_fifo.clear, rx_fifo.clear
  - **evidence** — ctrl.sim_mode <= bus_req_i.data(ctrl_sim_en_c) and bool_to_ulogic_f(sim_mode_en_c); tx_fifo.clear and rx_fifo.clear use ctrl.sim_mode

**`rx_engine`** — neorv32_uart · `rx_engine_t`
  - **functionality** — Contains the receiver FSM, shift register, counters, synchroniser and status. Its subfields are updated in the receiver clocked process from uart_rxd_i and ctrl.baud and when done supply rx_fifo.wdata and rx_fifo.we.
  - **roles** — receive engine state; holds shift, counters and sync; produces RX bytes
  - **relationships** — **AGGREGATES** → rx_engine.state, rx_engine.sreg, rx_engine.bitcnt, rx_engine.baudcnt, rx_engine.done, rx_engine.sync, rx_engine.over
  - **evidence** — receiver process assigns rx_engine.<fields> on rising_edge(clk_i); rx_fifo.wdata <= rx_engine.sreg(7 downto 0); rx_fifo.we <= rx_engine.done

**`rx_engine.baudcnt`** — neorv32_uart · `std_ulogic_vector(9 downto 0)`
  - **functionality** — Counts uart_clk ticks down from a reload value derived from ctrl.baud to sample bits at the correct timing; it is reloaded from ctrl.baud and decremented each uart_clk event.
  - **roles** — baud countdown; times RX sampling
  - **relationships** — **CAPTURES** → ctrl.baud, uart_clk
  - **evidence** — rx_engine.baudcnt <= '0' & ctrl.baud(9 downto 1) on start and decremented when uart_clk = '1' in receiver

**`rx_engine.bitcnt`** — neorv32_uart · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Counts remaining bits to receive a character; initialised on start and decremented per baud timing until zero when rx_engine.done is asserted.
  - **roles** — receive bit counter; terminates character receive
  - **relationships** — **CAPTURES** → rx_engine.baudcnt, uart_clk; **GATES** → rx_engine.done
  - **evidence** — rx_engine.bitcnt <= "1010" on start, decremented in receiver when baudcnt expires; rx_engine.done set when bitcnt = "0000"

**`rx_engine.done`** — neorv32_uart · `std_ulogic`
  - **functionality** — Pulsed when a received character completes; the receiver process asserts this and rx_fifo.we is driven from it to write the assembled byte into the RX FIFO.
  - **roles** — completion indicator; enables RX FIFO write
  - **relationships** — **CAPTURES** → rx_engine.bitcnt; **SOURCES** → rx_fifo.we
  - **evidence** — rx_engine.done <= '1' when rx_engine.bitcnt = "0000"; rx_fifo.we <= rx_engine.done

**`rx_engine.over`** — neorv32_uart · `std_ulogic`
  - **functionality** — Indicates an RX FIFO overrun event when a write occurred while FIFO was full; fifo_overrun process sets or clears it depending on ctrl.enable and rx_fifo conditions and bus clears.
  - **roles** — overrun indicator; reported via bus_resp
  - **relationships** — **CAPTURES** → rx_fifo.we, rx_fifo.free, ctrl.enable; **SOURCES** → bus_rsp_o.data
  - **evidence** — fifo_overrun process sets rx_engine.over <= '1' when (rx_fifo.we='1') and (rx_fifo.free='0'); bus_access reports ctrl_rx_over_c <= rx_engine.over

**`rx_engine.sreg`** — neorv32_uart · `std_ulogic_vector(8 downto 0)`
  - **functionality** — Shifts sampled serial bits into a register during RX bit timing. When reception completes rx_engine.sreg(7 downto 0) is forwarded to rx_fifo.wdata and rx_engine.done strobes write-enable to the FIFO.
  - **roles** — RX shift register; supplies rx_fifo.wdata
  - **relationships** — **CAPTURES** → rx_engine.sync, rx_engine.baudcnt, uart_clk; **SOURCES** → rx_fifo.wdata
  - **evidence** — rx_engine.sreg <= rx_engine.sync(2) & rx_engine.sreg(... ) in receiver; rx_fifo.wdata <= rx_engine.sreg(7 downto 0)

**`rx_engine.state`** — neorv32_uart · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Two-bit RX FSM state where one bit is synchronised to ctrl.enable; it advances on start detection and counts bits using baud timing to assemble bytes, ultimately asserting rx_engine.done.
  - **roles** — FSM state holder; controls RX capture
  - **relationships** — **CAPTURES** → ctrl.enable, rx_engine.sync, uart_clk, rx_engine.baudcnt; **GATES** → rx_engine.done, rx_fifo.we
  - **evidence** — receiver sets rx_engine.state(1) <= ctrl.enable and uses rx_engine.sync for start detection; rx_engine.done set when rx_engine.bitcnt = "0000"

**`rx_engine.sync`** — neorv32_uart · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Three-stage synchroniser that samples uart_rxd_i into rx_engine.sync(2) each clock and shifts that sample down on uart_clk to produce stable sampled bits for the receive shift register and start detection.
  - **roles** — synchroniser; feeds RX sampling
  - **relationships** — **CAPTURES** → uart_rxd_i, uart_clk; **SOURCES** → rx_engine.sreg, rx_engine.state
  - **evidence** — rx_engine.sync(2) <= uart_rxd_i; if (uart_clk='1') then rx_engine.sync(1 downto 0) <= rx_engine.sync(2 downto 1) in receiver

**`rx_fifo`** — neorv32_uart · `fifo_t`
  - **functionality** — Represents the RX FIFO control/status interface: clear, we, re, wdata, rdata, free, avail, half. Fields are driven locally (clear/we/re/wdata) and read by bus_access and IRQ logic, while rdata/avail/free/half are produced by the instantiated fifo component via port map.
  - **roles** — RX FIFO interface; conveys FIFO status to other logic; connects to fifo instance
  - **relationships** — **AGGREGATES** → rx_fifo.clear, rx_fifo.we, rx_fifo.re, rx_fifo.wdata, rx_fifo.rdata, rx_fifo.free, rx_fifo.avail, rx_fifo.half; **SOURCES** → bus_rsp_o.data, irq_rx_o, uart_rtsn_o, rx_engine.over
  - **evidence** — rx FIFO instance port_map connects level/avail/free/half/rdata; rx_fifo.* signals assigned and read throughout source

**`rx_fifo.avail`** — neorv32_uart · `std_ulogic`
  - **functionality** — Status output from FIFO instance indicating non-empty; used by bus response and rx IRQ generation to report available data and for IRQ triggering when enabled.
  - **roles** — FIFO status; gates RX IRQ
  - **relationships** — **SOURCES** → bus_rsp_o.data, irq_rx_o
  - **evidence** — bus_access maps ctrl_rx_nempty_c <= rx_fifo.avail; rx_irq_generator uses rx_fifo.avail

**`rx_fifo.clear`** — neorv32_uart · `std_ulogic`
  - **functionality** — Combinationally asserted when ctrl.enable is '0', ctrl.sim_mode is '1', or ctrl.clr_rx is '1' to request FIFO clear. It is driven concurrently from ctrl signals and consumed by the instantiated FIFO component (clear_i).
  - **roles** — FIFO clear control; export to FIFO instance
  - **relationships** — **CARRIES** → ctrl.enable, ctrl.sim_mode, ctrl.clr_rx; **EXPORTS** → _(none)_
  - **evidence** — rx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_rx = '1') else '0'; connected to instance clear_i

**`rx_fifo.free`** — neorv32_uart · `std_ulogic`
  - **functionality** — Status bit from FIFO instance indicating whether FIFO has free space; used in bus responses to indicate RX not-full and in fifo_overrun logic to detect writes into a full FIFO.
  - **roles** — FIFO status; feeds overrun detection and bus status
  - **relationships** — **SOURCES** → bus_rsp_o.data, rx_engine.over
  - **evidence** — bus_access uses not rx_fifo.free for ctrl_rx_full_c; fifo_overrun checks rx_fifo.free with rx_fifo.we

**`rx_fifo.half`** — neorv32_uart · `std_ulogic`
  - **functionality** — Status output from FIFO indicating half-full threshold; used by the bus response and by rtr_control to decide RTS and by IRQ logic to trigger when enabled.
  - **roles** — FIFO status; gates RTS and RX IRQ
  - **relationships** — **SOURCES** → bus_rsp_o.data, irq_rx_o, uart_rtsn_o
  - **evidence** — bus_access maps ctrl_rx_half_c <= rx_fifo.half; rtr_control checks rx_fifo.half; rx_irq_generator uses rx_fifo.half

**`rx_fifo.rdata`** — neorv32_uart · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Provides data read from the RX FIFO to the bus. It is an output of the FIFO instance (rdata_o) and its value is sampled into bus_rsp_o.data slices when the bus reads the data register.
  - **roles** — FIFO output data; feeds bus read data
  - **relationships** — **SOURCES** → bus_rsp_o.data
  - **evidence** — rx_fifo.rdata connected to FIFO instance rdata_o; bus_access assigns bus_rsp_o.data(data_rtx_msb_c downto data_rtx_lsb_c) <= rx_fifo.rdata

**`rx_fifo.re`** — neorv32_uart · `std_ulogic`
  - **functionality** — Requests a read from the RX FIFO when the bus performs a read at the data address. It is asserted combinationally from bus_req_i.stb/rw/addr conditions and fed to the FIFO instance.
  - **roles** — FIFO read request; drives FIFO instance
  - **relationships** — **GATES** → rx_fifo.rdata; **SOURCES** → bus_req_i.stb, bus_req_i.rw, bus_req_i.addr
  - **evidence** — rx_fifo.re <= '1' when (bus_req_i.stb='1') and (bus_req_i.rw='0') and (bus_req_i.addr(2)='1') else '0'; connected to FIFO instance re_i

**`rx_fifo.wdata`** — neorv32_uart · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Carries the assembled received byte into the FIFO. It is assigned from rx_engine.sreg(7 downto 0) and presented to the FIFO instance as wdata_i.
  - **roles** — FIFO input data; supplied by RX engine
  - **relationships** — **CARRIES** → rx_engine.sreg
  - **evidence** — rx_fifo.wdata <= rx_engine.sreg(7 downto 0); connected to FIFO instance wdata_i

**`rx_fifo.we`** — neorv32_uart · `std_ulogic`
  - **functionality** — Drives the FIFO write-enable when the RX engine asserts rx_engine.done; the concurrent assignment ties rx_fifo.we directly to rx_engine.done so completed received bytes are written into the FIFO.
  - **roles** — FIFO write strobe; driven by RX engine
  - **relationships** — **CARRIES** → rx_engine.done; **EXPORTS** → _(none)_
  - **evidence** — rx_fifo.we <= rx_engine.done; connected to FIFO instance we_i

**`tx_engine`** — neorv32_uart · `tx_engine_t`
  - **functionality** — Contains the state machine, shift register, counters and status for transmit operations. Its subfields are updated in the transmitter clocked process from tx_fifo and ctrl values and feed uart_txd_o and tx_fifo.re.
  - **roles** — transmit engine state; holds shift and counters; controls TX timing
  - **relationships** — **AGGREGATES** → tx_engine.state, tx_engine.sreg, tx_engine.bitcnt, tx_engine.baudcnt, tx_engine.done, tx_engine.busy, tx_engine.cts, tx_engine.txd
  - **evidence** — transmitter process assigns many tx_engine.<fields> on rising_edge(clk_i)

**`tx_engine.baudcnt`** — neorv32_uart · `std_ulogic_vector(9 downto 0)`
  - **functionality** — Counts UART clock ticks down from ctrl.baud to time bit shifts. It is reloaded from ctrl.baud at the start of bits and decremented each uart_clk event to pace shifting.
  - **roles** — baud countdown; times bit shifts
  - **relationships** — **CAPTURES** → ctrl.baud, uart_clk, tx_engine.baudcnt
  - **evidence** — tx_engine.baudcnt <= ctrl.baud on state "100" and decremented when uart_clk = '1' in transmitter

**`tx_engine.bitcnt`** — neorv32_uart · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Counts remaining bits to shift for a character transmission. It is initialised on start and decremented when baud periods complete, and when it reaches zero tx_engine.done is asserted.
  - **roles** — transmit bit counter; terminates character transmit
  - **relationships** — **CAPTURES** → tx_engine.bitcnt, tx_engine.baudcnt, ctrl.baud, uart_clk; **GATES** → tx_engine.done
  - **evidence** — tx_engine.bitcnt <= "1011" at start, decremented in transmitter when baudcnt expires; tx_engine.done set when bitcnt = "0000"

**`tx_engine.busy`** — neorv32_uart · `std_ulogic`
  - **functionality** — Combinationally reflects whether the transmit FSM is active (state != "00"). It is assigned with a simple concurrent conditional and read by bus_resp to report TX busy status.
  - **roles** — status reflection; feeds bus status
  - **relationships** — **REFLECTS** → tx_engine.state; **SOURCES** → bus_rsp_o.data
  - **evidence** — tx_engine.busy <= '0' when (tx_engine.state(1 downto 0) = "00") else '1'; bus_access uses tx_engine.busy in response

**`tx_engine.cts`** — neorv32_uart · `std_ulogic_vector(1 downto 0)`
  - **functionality** — Two-bit shift register that samples uart_ctsn_i to create a small history for the transmitter to observe remote CTS. It is shifted each clock and used with ctrl.hwfc_en to decide transmit progression.
  - **roles** — CTS synchroniser; feeds HWFC decision
  - **relationships** — **CAPTURES** → uart_ctsn_i, tx_engine.cts; **SOURCES** → tx_engine.state
  - **evidence** — tx_engine.cts <= tx_engine.cts(0) & uart_ctsn_i in transmitter process

**`tx_engine.done`** — neorv32_uart · `std_ulogic`
  - **functionality** — Pulsed when a character transmission completes; it is cleared each cycle and set when tx_engine.bitcnt reaches zero, driving tx_fifo.re via tx_engine.state gating.
  - **roles** — completion indicator; gates FIFO read handshake
  - **relationships** — **CAPTURES** → tx_engine.bitcnt; **GATES** → tx_fifo.re
  - **evidence** — tx_engine.done <= '1' when tx_engine.bitcnt = "0000"; tx_engine.done cleared at each rising_edge

**`tx_engine.sreg`** — neorv32_uart · `std_ulogic_vector(8 downto 0)`
  - **functionality** — Holds the byte plus stop bit for serial transmission; it is loaded from tx_fifo.rdata & '0' when starting and shifted right during bit timing, supplying tx_engine.txd from its LSB.
  - **roles** — shift register; supplies serial bit output
  - **relationships** — **CAPTURES** → tx_fifo.rdata, tx_engine.sreg, tx_engine.baudcnt, uart_clk; **SOURCES** → tx_engine.txd
  - **evidence** — tx_engine.sreg <= tx_fifo.rdata & '0' on start; shifted in transmitter when baudcnt expires; tx_engine.txd <= tx_engine.sreg(0)

**`tx_engine.state`** — neorv32_uart · `std_ulogic_vector(2 downto 0)`
  - **functionality** — Holds the 3-bit state of the transmitter FSM; bit2 is driven by ctrl.enable each cycle and the lower bits transition based on FIFO status, uart_clk and CTS/hwfc decisions. It controls when tx_fifo.re is asserted and when transmission shifts occur.
  - **roles** — FSM state holder; governs tx actions; gates FIFO read
  - **relationships** — **CAPTURES** → ctrl.enable, tx_fifo.rdata, tx_fifo.avail, uart_clk, tx_engine.cts, ctrl.hwfc_en; **GATES** → tx_fifo.re
  - **evidence** — transmitter process sets tx_engine.state(2) <= ctrl.enable and case tx_engine.state ... tx_fifo.re <= '1' when (tx_engine.state = "100")

**`tx_engine.txd`** — neorv32_uart · `std_ulogic`
  - **functionality** — Holds the current serial output bit driven to uart_txd_o. It is defaulted to '1' each cycle and set to tx_engine.sreg(0) during sending states, and is exported directly to uart_txd_o.
  - **roles** — serial bit holder; feeds uart_txd_o
  - **relationships** — **CAPTURES** → tx_engine.sreg, tx_engine.state, uart_clk; **SOURCES** → uart_txd_o
  - **evidence** — tx_engine.txd <= '1' default then tx_engine.txd <= tx_engine.sreg(0) in state "111"; uart_txd_o <= tx_engine.txd

**`tx_fifo`** — neorv32_uart · `fifo_t`
  - **functionality** — Represents the TX FIFO control/status interface: clear, we, re, wdata, rdata, free, avail, half. Local logic drives clear/we/re/wdata and reads free/avail/half/rdata from the FIFO instance; tx_engine consumes rdata and the IRQ logic consumes status bits.
  - **roles** — TX FIFO interface; supplies TX bytes to engine; conveys FIFO status
  - **relationships** — **AGGREGATES** → tx_fifo.clear, tx_fifo.we, tx_fifo.re, tx_fifo.wdata, tx_fifo.rdata, tx_fifo.free, tx_fifo.avail, tx_fifo.half; **SOURCES** → tx_engine.sreg, tx_engine.state, irq_tx_o, bus_rsp_o.data
  - **evidence** — tx FIFO instance port_map binds tx_fifo.*; tx_engine loads tx_fifo.rdata; tx_irq_generator and bus_access use tx_fifo status

**`tx_fifo.avail`** — neorv32_uart · `std_ulogic`
  - **functionality** — Indicates whether TX FIFO contains data (avail). It is read by the transmitter to start transmissions and by bus_access and IRQ logic to report status and trigger interrupts.
  - **roles** — FIFO status; gates transmitter start and IRQ
  - **relationships** — **SOURCES** → tx_engine.state, irq_tx_o, bus_rsp_o.data
  - **evidence** — transmitter checks if (tx_fifo.avail = '1') to advance state; bus_access and tx_irq_generator read tx_fifo.avail

**`tx_fifo.clear`** — neorv32_uart · `std_ulogic`
  - **functionality** — Combinational clear request for the TX FIFO asserted when ctrl.enable is '0', ctrl.sim_mode is '1', or ctrl.clr_tx is '1'. Driven from ctrl signals and presented to the FIFO instance clear input.
  - **roles** — FIFO clear control; export to FIFO instance
  - **relationships** — **CARRIES** → ctrl.enable, ctrl.sim_mode, ctrl.clr_tx; **EXPORTS** → _(none)_
  - **evidence** — tx_fifo.clear <= '1' when (ctrl.enable = '0') or (ctrl.sim_mode = '1') or (ctrl.clr_tx = '1') else '0'; connected to FIFO instance clear_i

**`tx_fifo.free`** — neorv32_uart · `std_ulogic`
  - **functionality** — Status from FIFO instance indicating free space; used in bus responses to report TX fullness and in bus_access to compute ctrl_tx_full/status bits.
  - **roles** — FIFO status; feeds bus status and ctrl reporting
  - **relationships** — **SOURCES** → bus_rsp_o.data
  - **evidence** — bus_access uses not tx_fifo.free for ctrl_tx_full_c and reports it in bus_rsp_o.data

**`tx_fifo.half`** — neorv32_uart · `std_ulogic`
  - **functionality** — Status from the TX FIFO showing near-half threshold; used by IRQ generation and by bus response logic to report nearly-half/full states.
  - **roles** — FIFO status; feeds IRQ and status readout
  - **relationships** — **SOURCES** → irq_tx_o, bus_rsp_o.data
  - **evidence** — bus_access reads not tx_fifo.half/tx_fifo.half for status; tx_irq_generator uses tx_fifo.half

**`tx_fifo.rdata`** — neorv32_uart · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Data read from the TX FIFO provided to the transmitter. It is produced by the FIFO instance and sampled into the tx_engine.sreg when a transmission starts.
  - **roles** — FIFO output data; feeds tx_engine
  - **relationships** — **SOURCES** → tx_engine.sreg
  - **evidence** — tx_engine.sreg <= tx_fifo.rdata & '0' in transmitter when starting transmission; rdata_o is mapped to tx_fifo.rdata

**`tx_fifo.re`** — neorv32_uart · `std_ulogic`
  - **functionality** — Asserted when the transmit engine is in the startup state to fetch the next byte. It is driven combinationally from tx_engine.state and fed to the FIFO instance to produce rdata.
  - **roles** — FIFO read request; driven by tx_engine
  - **relationships** — **SOURCES** → tx_engine.state; **EXPORTS** → _(none)_
  - **evidence** — tx_fifo.re <= '1' when (tx_engine.state = "100") else '0'; connected to FIFO instance re_i

**`tx_fifo.wdata`** — neorv32_uart · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Carries the lower byte of the bus write data into the TX FIFO. It is directly assigned from bus_req_i.data(7 downto 0) and supplied to the FIFO instance.
  - **roles** — FIFO input data; fed from bus writes
  - **relationships** — **CARRIES** → bus_req_i.data
  - **evidence** — tx_fifo.wdata <= bus_req_i.data(data_rtx_msb_c downto data_rtx_lsb_c)

**`tx_fifo.we`** — neorv32_uart · `std_ulogic`
  - **functionality** — Strobes writes into the TX FIFO when a bus write to the TX data register occurs. It is asserted combinationally from bus_req_i.stb/rw/addr conditions and fed to the FIFO instance.
  - **roles** — FIFO write request; driven by bus writes
  - **relationships** — **SOURCES** → bus_req_i.stb, bus_req_i.rw, bus_req_i.addr; **EXPORTS** → _(none)_
  - **evidence** — tx_fifo.we <= '1' when (bus_req_i.stb='1') and (bus_req_i.rw='1') and (bus_req_i.addr(2)='1') else '0'; connected to FIFO instance we_i

**`uart_clk`** — neorv32_uart · `std_ulogic`
  - **functionality** — Derived bit from clkgen_i chosen by ctrl.prsc to clock UART bit timing. It is assigned combinationally from clkgen_i indexed by ctrl.prsc and is sampled by transmitter and receiver processes to time baud operations.
  - **roles** — internal clock; feeds transmitter and receiver
  - **relationships** — **DERIVES_FROM** → clkgen_i, ctrl.prsc
  - **evidence** — concurrent assignment uart_clk <= clkgen_i(to_integer(unsigned(ctrl.prsc)))


## neorv32_wdt  (31 non-assets)

### ports

**`bus_req_i`** — neorv32_wdt · `bus_req_t`
  - **functionality** — The aggregate record is not referenced as a whole in this source; individual fields of it are read instead (see field annotations).
  - **roles** — record wrapper (fields used individually)
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — Only bus_req_i fields (stb, rw, addr, data, ...) are used in bus_access; no whole-record use

**`bus_req_i.addr`** — neorv32_wdt · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Its bit 2 is tested to choose between control register writes and password write action; that selection directs which internal registers are updated.
  - **roles** — address selector; chooses write path
  - **relationships** — **SELECTS** → ctrl.enable, ctrl.lock, ctrl.strict, ctrl.timeout, reset_wdt, reset_force
  - **evidence** — if (bus_req_i.addr(2) = '0') then ... else ... in bus_access process

**`bus_req_i.amo`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Declared but not referenced anywhere in this source.
  - **roles** — unused field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.amo in source

**`bus_req_i.amoop`** — neorv32_wdt · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared but not referenced anywhere in this source.
  - **roles** — unused field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.amoop in source

**`bus_req_i.ben`** — neorv32_wdt · `std_ulogic_vector(3 downto 0)`
  - **functionality** — Declared bus byte-enable field is not read or used anywhere in this source.
  - **roles** — unused field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.ben in source

**`bus_req_i.data`** — neorv32_wdt · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Supplies bits and slices for register writes (ctrl fields) and is compared to the reset password; those reads drive control registers and determine reset_wdt/reset_force on writes.
  - **roles** — data source for writes; compared for password match
  - **relationships** — **SOURCES** → ctrl.enable, ctrl.lock, ctrl.strict, ctrl.timeout; **CONSTRAINS** → reset_wdt, reset_force
  - **evidence** — bus_req_i.data(...) assigned into ctrl fields and compared (bus_req_i.data(31 downto 0) = reset_pwd_c) in bus_access

**`bus_req_i.debug`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Declared but not read anywhere in this source (separate rstn_dbg_i input holds debug reset).
  - **roles** — unused field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.debug in source

**`bus_req_i.fence`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Declared but not referenced anywhere in this source.
  - **roles** — unused field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.fence in source

**`bus_req_i.lock`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Declared but not read anywhere in this source; the module has its own ctrl.lock internal field used for locking behaviour.
  - **roles** — unused field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.lock in source

**`bus_req_i.priv`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Declared but not read anywhere in this source.
  - **roles** — unused field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.priv in source

**`bus_req_i.rw`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Selects the write versus read branch in bus_access; when '1' the code updates control registers or password action, otherwise it prepares bus response data.
  - **roles** — branch selector; chooses write or read
  - **relationships** — **SELECTS** → ctrl.enable, ctrl.lock, ctrl.strict, ctrl.timeout, reset_wdt, reset_force, bus_rsp_o.data
  - **evidence** — if (bus_req_i.rw = '1') then ... else ... in bus_access

**`bus_req_i.src`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Declared but not read anywhere in this source.
  - **roles** — unused field
  - **relationships** — **ISOLATED** → _(none)_
  - **evidence** — No occurrences of bus_req_i.src in source

**`bus_req_i.stb`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Gates bus access handling (write/read) and is routed into the response ack field; when asserted it enables the read/write branching in bus_access and also directly becomes bus_rsp_o.ack.
  - **roles** — handshake input; gates bus accesses; feeds response ack
  - **relationships** — **SOURCES** → bus_rsp_o.ack; **GATES** → ctrl.enable, ctrl.lock, ctrl.strict, ctrl.timeout, reset_wdt, reset_force, bus_rsp_o.data
  - **evidence** — bus_rsp_o.ack <= bus_req_i.stb; if (bus_req_i.stb = '1') then ... in bus_access

**`bus_rsp_o`** — neorv32_wdt · `bus_rsp_t`
  - **functionality** — Drives the bus response bundle to the outside: ack, err and data fields are driven from internal logic and defaults (including reset) to form the module's bus reply.
  - **roles** — output response record; exports response state
  - **relationships** — **EXPORTS** → _(none)_
  - **evidence** — bus_rsp_o <= rsp_terminate_c in reset branch; individual fields assigned in bus_access process

**`bus_rsp_o.ack`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Is set each clock to the incoming strobe (bus_req_i.stb) and thus reports handshake acknowledgment to the bus master.
  - **roles** — ack output; reports bus transaction acceptance
  - **relationships** — **CAPTURES** → bus_req_i.stb; **EXPORTS** → _(none)_
  - **evidence** — bus_rsp_o.ack <= bus_req_i.stb in bus_access (rising_edge(clk_i))

**`bus_rsp_o.data`** — neorv32_wdt · `std_ulogic_vector(31 downto 0)`
  - **functionality** — Holds response data; defaulted to zeros each clock and selectively populated from control and reset_cause fields on read operations before being exported on the bus.
  - **roles** — response data output; exports control and reset fields
  - **relationships** — **CAPTURES** → ctrl.enable; **CAPTURES** → ctrl.lock; **CAPTURES** → reset_cause; **CAPTURES** → ctrl.strict; **CAPTURES** → ctrl.timeout; **EXPORTS** → _(none)_
  - **evidence** — bus_rsp_o.data(...) <= ctrl.* and bus_rsp_o.data <= (others => '0') in bus_access

**`bus_rsp_o.err`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Is driven low each clock in the bus_access process (constant '0'), providing the error indicator in the response.
  - **roles** — error flag output; driven low each cycle
  - **relationships** — **CAPTURES** → _(none)_; **EXPORTS** → _(none)_
  - **evidence** — bus_rsp_o.err <= '0' in bus_access process (rising_edge(clk_i))

**`clk_i`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Supplies the rising edge used by all clocked processes; sequences updates to bus response, control registers, counter, reset requests and reset_cause. It times the entity's sequential behaviour.
  - **roles** — clock source; sequences internal registers
  - **relationships** — **SEQUENCES** → bus_rsp_o, ctrl, reset_wdt, reset_force, cnt_inc, cnt_started, cnt, hw_rst_timeout, hw_rst_access, reset_cause
  - **evidence** — rising_edge(clk_i) used in processes bus_access, wdt_counter, reset_generator, reset_identifier

**`clkgen_i`** — neorv32_wdt · `std_ulogic_vector(7 downto 0)`
  - **functionality** — Provides prescaler ticks by indexing a selected bit; a selected bit of this vector is carried to prsc_tick for internal timing.
  - **roles** — timing input vector; sources prescaler tick
  - **relationships** — **SOURCES** → prsc_tick
  - **evidence** — prsc_tick <= clkgen_i(clk_div4096_c) concurrent assignment

**`rstn_dbg_i`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Is tested at clock edge to select the debug reset cause; when low it causes reset_cause to be set to "01" on the next rising edge.
  - **roles** — control input; chooses debug reset cause
  - **relationships** — **GATES** → reset_cause
  - **evidence** — if (rstn_dbg_i = '0') then reset_cause <= "01" in reset_identifier process

**`rstn_ext_i`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Acts as the asynchronous reset for the reset_identifier process; when asserted low it clears reset_cause to "00" at that process's reset branch.
  - **roles** — asynchronous reset input; initialises reset_cause
  - **relationships** — **SEQUENCES** → reset_cause
  - **evidence** — process reset_identifier sensitivity (rstn_ext_i) and if (rstn_ext_i = '0') then reset_cause <= "00"

**`rstn_o`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Drives the external reset output as the inverted OR of the two hardware reset request signals (hw_rst_timeout and hw_rst_access); reports whether a hardware reset is asserted.
  - **roles** — reset output; exports hardware reset state
  - **relationships** — **DERIVES_FROM** → hw_rst_timeout, hw_rst_access; **EXPORTS** → _(none)_
  - **evidence** — rstn_o <= not (hw_rst_timeout or hw_rst_access) concurrent assignment

**`rstn_sys_i`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Provides the asynchronous reset for the main clocked processes; when asserted low it clears bus_rsp_o, ctrl fields, counter state and reset request signals in their reset branches.
  - **roles** — asynchronous reset input; clears internal registers on assertion
  - **relationships** — **SEQUENCES** → bus_rsp_o, ctrl, reset_wdt, reset_force, cnt_inc, cnt_started, cnt, hw_rst_timeout, hw_rst_access
  - **evidence** — if (rstn_sys_i = '0') then ... in bus_access, wdt_counter, reset_generator processes

### signals

**`cnt_inc`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Captured each clock as the AND of prsc_tick and cnt_started; when high it gates the counter increment in the next step.
  - **roles** — held increment qualifier; gates counter increment
  - **relationships** — **DERIVES_FROM** → prsc_tick, cnt_started; **GATES** → cnt
  - **evidence** — cnt_inc <= prsc_tick and cnt_started in wdt_counter; used in if (cnt_inc = '1') then cnt <= cnt + 1

**`cnt_started`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Captured from the conjunction of ctrl.enable and prescaler activity (or prior started state); it records whether counting is active and is used in increment qualification and timeout logic.
  - **roles** — status flag; enables counting; participates in timeout compare
  - **relationships** — **DERIVES_FROM** → ctrl.enable, cnt_started, prsc_tick; **SOURCES** → cnt_inc, cnt_timeout
  - **evidence** — cnt_started <= ctrl.enable and (cnt_started or prsc_tick) in wdt_counter; cnt_started used in cnt_timeout and cnt_inc

**`ctrl`** — neorv32_wdt · `ctrl_t`
  - **functionality** — Holds the WDT control fields (enable, lock, strict, timeout) which are individually captured from bus writes and reset; the record groups those fields for internal use.
  - **roles** — configuration state; aggregate of control fields
  - **relationships** — **AGGREGATES** → ctrl.enable, ctrl.lock, ctrl.strict, ctrl.timeout
  - **evidence** — type ctrl_t record and individual field assignments in bus_access process

**`ctrl.strict`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Captured from a bus write and read back; when set it allows bus-induced accesses to request a hardware reset (used in hw_rst_access generation).
  - **roles** — held strict flag; enables hw access reset
  - **relationships** — **CAPTURES** → bus_req_i.data; **SOURCES** → hw_rst_access, bus_rsp_o.data
  - **evidence** — ctrl.strict <= bus_req_i.data(ctrl_strict_c) in bus_access; used in hw_rst_access <= ctrl.enable and ctrl.strict and reset_force

**`hw_rst_access`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Captured from ctrl.enable, ctrl.strict and reset_force; when asserted it contributes to the reset output and selects the access reset cause.
  - **roles** — held access request; sources reset output; governs reset cause
  - **relationships** — **DERIVES_FROM** → ctrl.enable, ctrl.strict, reset_force; **SOURCES** → rstn_o; **GATES** → reset_cause
  - **evidence** — hw_rst_access <= ctrl.enable and ctrl.strict and reset_force in reset_generator; used in rstn_o and reset_identifier

**`hw_rst_timeout`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Captured from ctrl.enable, cnt_timeout and prsc_tick; when asserted it contributes to the reset output and selects the timeout reset cause.
  - **roles** — held timeout request; sources reset output; governs reset cause
  - **relationships** — **DERIVES_FROM** → ctrl.enable, cnt_timeout, prsc_tick; **SOURCES** → rstn_o; **GATES** → reset_cause
  - **evidence** — hw_rst_timeout <= ctrl.enable and cnt_timeout and prsc_tick in reset_generator; used in rstn_o and reset_identifier

**`prsc_tick`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Carries a selected bit of clkgen_i into the internal tick signal and supplies timing to the counter logic and reset generator.
  - **roles** — timing tick; feeds counter increment; participates in reset request
  - **relationships** — **CARRIES** → clkgen_i; **SOURCES** → cnt_inc, cnt_started, hw_rst_timeout
  - **evidence** — prsc_tick <= clkgen_i(clk_div4096_c); prsc_tick used in wdt_counter and reset_generator

**`reset_force`** — neorv32_wdt · `std_ulogic`
  - **functionality** — Set when invalid register access or unauthorized write attempts occur (locked writes or wrong password); used as input to hw_rst_access generation.
  - **roles** — force-reset flag; enables hw access reset
  - **relationships** — **CAPTURES** → _(none)_; **SOURCES** → hw_rst_access; **GATES** → reset_force
  - **evidence** — reset_force <= '1' in bus_access when writes are invalid; used in hw_rst_access <= ctrl.enable and ctrl.strict and reset_force

