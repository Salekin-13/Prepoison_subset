# Error patterns across four prompt versions: synthesis report

**Scope.** This report covers 15 modules, with 111 ground-truth (GT) entries per run. That denominator is exact.
- Baseline v2x3r8 has 3 runs. Its figures are per-run means unless marked otherwise. "Majority" means the element appears in at least 2 of the 3 runs.
- The three generated prompts, m4bc606 s0, s1 and s2, have 1 run each.
- Precision = TP / predicted elements. Recall = TP / 111.

**How the numbers were made.** Every count below was re-run in this task with pandas on `error_table.csv`.
- The main table is `.../scratchpad/analysis/synthesis/UK.pkl`.
- The scripts in the same folder are: `build_unified.py`, `partition.py`, `rules.py`, `combine.py`, `final_packages.py`, `cross.py`, `cross2.py`, `cex.py`, `verify_*.py` and `rule_texts.py`.

**Self-tests, all re-run in this task and all PASS:**
- `build_table.selftest`: hand-read wdt and trng statements.
- `baseline_fp/selftest_graph.py`: 12 hand-read statements.
- `generated_fn/selftest_uses.py`: 9 hand-read statements.

**Rule effects are oracle simulations.** Matching predictions are deleted, or matching elements are added, and nothing is re-run. So each effect is an upper bound, and it assumes the model obeys the rule exactly and does not substitute other elements.

| version | runs | predicted | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|---|
| baseline v2x3r8 | 3 | 304 / 330 / 325 | 88 / 100 / 96 | 216 / 230 / 229 | 23 / 11 / 15 | 0.289 / 0.303 / 0.295 (mean 0.296) | 0.793 / 0.901 / 0.865 (mean 0.853) |
| s0 | 1 | 304 | 74 | 230 | 37 | 0.243 | 0.667 |
| s1 | 1 | 243 | 64 | 179 | 47 | 0.263 | 0.577 |
| s2 | 1 | 165 | 45 | 120 | 66 | 0.273 | 0.405 |

---

## A. Executive findings

1. **Transaction records are the largest FP source in every version, and they are never right. (MEASURED)**
   - A transaction record is a bus or debug request/response record type. The model reports it whole, by field, or as an internal copy.
   - This group has 0 TP and 0 FN in all 6 runs.
   - FP: s0 89 of 230, s1 67 of 179, s2 35 of 120, baseline 40.67 of 225 per run.
   - Removing it raises precision to 0.344 / 0.364 / 0.346, and the baseline to a mean of 0.339. Recall does not change.
   - The form differs by version:
     - The baseline names whole peripheral bus ports: 24.0 per run outside the interconnect module.
     - The generated prompts name port fields: 47 / 22 / 31, against 0 in every baseline run.
     - s0 and s1 also name per-destination interconnect ports: 41 / 39 in the interconnect module, against 0 in s2.
2. **The generated prompts' recall gap is mostly input ports. (MEASURED)**
   - Input-port recall is 5/26, 4/26 and 1/26, against the baseline's 21/26, 22/26 and 19/26.
   - All three generated prompts say an input port does not qualify just because a value enters through it.
   - The baseline instead asks "which port carries it across the boundary?".
   - REASONING: this is the likely cause, but it is confounded. The baseline also has worked examples; the generated prompts are zero-shot.
3. **The second recall loss is internal signals, mostly in s1 and s2. (MEASURED)**
   - Signal recall: 24/32, 17/32 and 15/32, against the baseline's 24/32, 31/32 and 29/32.
   - Two patterns cause it:
     - (a) An element named in the model's own reasoning but reported at a neighbour instead: FN 6 / 11 / 13.
     - (b) Whole concepts never reported: FN 1 / 6 / 20.
   - REASONING: (a) fits the generated definition "secondary = influences a primary asset". (b) comes from one run per prompt and may be noise.
4. **Several FP patterns are shared by all four versions at similar size. (MEASURED)** They are definition weaknesses common to both prompt families:
   - Fields that only connect to an instantiated sub-block: baseline 39.67 per run; s0/s1/s2 24 / 32 / 21. 12 distinct elements are FP in all four.
   - The reset network, storage arrays, per-field configuration bits, registers copied to an output, and datapath registers.
   - REASONING: both families tell the model to report several elements per concept:
     - Generated: "One conceptual asset usually has several structural references along its path."
     - Baseline: "emit one object per element", with "STORES, CARRIES, GENERATES, or GATES".
5. **About a third of baseline FPs sit where the GT keeps some elements and drops others of the same kind. No feature rule separates them. (MEASURED)**
   - These are control state, decision chains, non-record ports, glue and read-back status (clusters K10–K14).
   - Baseline FP there is 67 / 73 / 75 per run. In the K11–K14 part, precision is about 0.50 in every run and TP is 62 / 74 / 70.
6. **A package of rules with no TP cost here would raise precision in every version without changing recall. (MEASURED, oracle upper bound)**
   - The rules: transaction records (F1), sub-block connection fields (F3), the closed-set post-filter (F13), clock-enable ticks (F4), interrupt-mask bits (F5), and a register copied unchanged to a plain output (F7).
   - Precision 0.423 / 0.457 / 0.421, baseline mean 0.416. Recall unchanged.
   - Adding the input-port rule (F2) to the generated prompts: precision 0.465 / 0.491 / 0.482, recall 0.838 / 0.757 / 0.613.
7. **Not recommended:**
   - Reset-network exclusion, storage-array exclusion, self-clearing bits, protocol-variant bits, and "register or port, not both".
   - The literal form of the in-transit-register rule, and the decision-holding inclusion rule in its current form.
   - Reasons are in section F.

**Numbers that changed from the three analyses** (re-derived here; the new figure is used below):
- Counterfactual wording in baseline justifications: 79.3% of FP rows (535/675, summed over 3 runs) against 79.2% of TP rows (225/284). The analysis reported 83.4% against 87.0%. My keyword list differs. The conclusion, that this wording does not separate FP from TP, is unchanged.
- External-context words in generated reasoning: 11 of 774 concept–element pairs (8 FP, 3 TP). The analysis reported 21. Still rare.
- Fan-out buckets, pooled over the three generated runs: 36/89, 98/277 and 49/344. The analysis reported 36/90 and 49/345.
- Transaction-record removal in the generated runs gives precision 0.344 / 0.364 / 0.346. The analysis reported 0.341 / 0.362 / 0.346, because my predicate also covers internal copies of these records.
- Rule B recovers FN 3 / 8 / 11. The analysis reported 4 / 9 / 12. The GT lists `state` twice, and one prediction can match only one of the two.
- Reset network, generated runs: FP 13 / 10 / 9 with the hand-labelled role set. The analysis reported 10 / 7 / 7 with a different predicate.
- 'Exit port' on non-record, non-reset ports: 19/24, 19/24 and 11/17. The analysis reported 19/26, 19/26 and 11/19.
- Recall ceiling: 109 of 111 GT names exist in this RTL. Only 106 have RTL behaviour to ground them on, because `active_i`, `rs3_i` and trng `fifo.free` are never read.

---

## B. Generated-version false negatives

FN per run: s0 37, s1 47, s2 66, of 111.
- A miss is **"introduced"** when the baseline finds that GT element in at least 2 of its 3 runs.
- Counts are per distinct GT element.
- Clusters are assigned in priority order C0 > C1 > C2 > C3 > C4 > C5, and every FN row gets exactly one.

| cluster | predicate (pandas, on UK.pkl) | FN s0 / s1 / s2 | introduced |
|---|---|---|---|
| C1 input port the entity reads | ``status=='FN' and `class`=='port' and dir=='in' and not bus_typed and not clk_rst_named and (u_body>0 or u_pm>0)`` | 19 / 20 / 23 | 18 / 18 / 21 |
| C4 named in reasoning, reported at a neighbour | FN, not C0–C3, element name appears in the concept or reasoning text of that module | 6 / 11 / 13 | 4 / 8 / 10 |
| C5 concept never reported | FN, not C0–C3, not named | 1 / 6 / 20 | 0 / 6 / 20 |
| C2 wire carrying a sub-instance result | ``status=='FN' and `class`=='signal' and n_assign==0 and portmap_actual`` | 5 / 4 / 5 | 3 / 3 / 3 |
| C3 entity-prefixed name | a port of another entity in the file, emitted as `<entity>.<port>` | 1 / 1 / 0 | 0 |
| C0 unreachable (GT limit, or never read) | see verify_fn.py | 5 / 5 / 5 | 0 |

### C1: input ports (the largest cause)

**Behaviour (MEASURED).** The model reports the first internal element that samples or combines the input, and not the input itself.
- `neorv32_cpu:mei_i/msi_i/mti_i`. RTL_data/neorv32_cpu.vhd:276 `irq_machine <= mti_i & mei_i & msi_i;`. The s0 concept is "Machine interrupt vector (irq_machine) assembled from external interrupt inputs", and only `irq_machine` is reported.
- `neorv32_uart:uart_ctsn_i`. RTL_data/neorv32_uart.vhd:337 `tx_engine.cts <= tx_engine.cts(0) & uart_ctsn_i;`. The s1 concept is "Sampled CTS state"; its reasoning names `uart_ctsn_i`, but it reports only `tx_engine.cts`.
- `neorv32_cpu_pmp:addr_ls_i`. RTL_data/neorv32_cpu_pmp.vhd:244 `acc_addr <= ctrl_i.pc_nxt when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;`.
- `neorv32_debug_dtm:jtag_tdi_i`. RTL_data/neorv32_debug_dtm.vhd:100 `tap_sync.tdi_ff <= tap_sync.tdi_ff(1 downto 0) & jtag_tdi_i;`.
- The missed input is named in the model's own reasoning in 10/19, 12/20 and 8/23 cases.
- When a generated run did report an input port, the role was always 'sets': 14 / 6 / 1 ports.

**Which inputs the GT keeps (MEASURED; exact, 134 distinct input ports):**
- Bus-record inputs: 0 of 55 are GT.
- Clock/reset-named inputs: 0 of 35 are GT.
- All other inputs: 26 of 44 are GT. The baseline finds 21 / 22 / 19 of these 26 per run.

**Chain:**
1. Recurring pattern: the value's entry point is dropped, and the value is realised at its first internal sink.
2. Criterion applied wrongly: the definition says a structural reference is "where its value is stored, set, or computed, or the port through which it leaves its entity".
   - The model reads "set" as the internal register.
   - The input-port sentence rules out the port. s0 L231: "An input-only port is not an exit port and does not qualify merely because a meaningful value enters through it". s1 L224 and s2 L106 say the same.
3. Missing or ambiguous rule: where a value that comes from outside is "set" in this entity. The definition names only ports through which a value leaves.
4. Candidate: **F2** (input port that the entity reads).

### C4: element named in the reasoning, but reported at a neighbour

**Behaviour (MEASURED):**
- `neorv32_wdt:cnt_timeout` (s1, s2). wdt.vhd:144 `cnt_timeout <= '1' when (cnt_started = '1') and (cnt = ctrl.timeout) else '0';` and :155 `hw_rst_timeout <= ctrl.enable and cnt_timeout and prsc_tick;`. The s1 reasoning names `cnt_timeout`, but only `hw_rst_timeout` is reported.
- `neorv32_cpu_pmp:fail` (s0). pmp.vhd:354 `fail(r) <= not allow(r) when (match(r) = '1') else fail(r+1);` and :363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);`. The s0 reasoning says "The fail vector is derived from match and allow"; it reports `fault_o` only.
- `neorv32_imem:rden`. imem.vhd:176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` and :185 `bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');`.
- `neorv32_hwspinlock:sel`. hwspinlock.vhd:51 and :68.

**Chain:**
1. Recurring pattern: one realization is kept per concept, usually the sink.
2. Criterion applied wrongly: all three generated prompts define a secondary asset as "an internal signal or register that influences a primary asset".
   - s1 L228: "Do not report upstream controls, resets, enables, or dependency registers solely because they affect a primary value".
   - s2 L108: "Do not promote supporting clocks, resets, enables, counters, or other influences".
   - The GT counts such counters, comparison results and strobes as primary.
3. Missing rule: a way to tell an element that holds its own decision value from an element that only influences one.
4. Candidate: **F10**, tentative. As an inclusion rule it lowers precision (section F).

### C5: concept never reported (mostly s2)

**Behaviour (MEASURED):**
- Concept counts are 118 / 99 / 65.
- In uart, s2 reports 3 concepts with references and 0 of the 10 uart GT entries. s0 and s1 find 8 of 10.
  - Examples: uart.vhd:179 `ctrl.enable <= bus_req_i.data(ctrl_en_c);`, :228 `clkgen_en_o <= ctrl.enable;`, :392 `uart_txd_o <= tx_engine.txd;`.
- In muldiv, s2 misses `mul.start` (muldiv.vhd:154), `div.start` and the operand sign flags.
- All 20 of s2's C5 rows are baseline-majority finds.

**Chain:**
1. Recurring pattern: whole flows are left out.
2. Criterion applied: a strict "Established" bar.
   - s2 L134: "Avoid generic assumptions such as 'all configuration is sensitive'".
   - s2 L136 and s1 L139 require a specific production or delivery property.
3. Missing rule: guidance that a block's own outputs and on/off or rate configuration meet the bar.
4. Candidate: **F11**, tentative. There is one run per prompt, so noise cannot be ruled out.

### C2: wire carrying a result from an unsupplied sub-instance

This occurs in one module only (neorv32_cpu).
- `alu_add`: cpu.vhd:370 `add_o => alu_add,`.
- `lsu_mar`: cpu.vhd:389 `mar_o => lsu_mar,`.
- Criterion applied: the unavailable implementation is treated as an opaque boundary, so the wire becomes a carrier. s2 L56: "Treat unavailable implementations as opaque boundaries".
- Candidate: **F12**, tentative.

### C3: entity-prefixed name

- `neorv32_trng:data_o` belongs to the second entity in the file. trng.vhd:366 `data_o <= sample_sreg;`.
- s0 and s1 emitted it as `neoTRNG.data_o`, which scores as 1 FP plus 1 FN.
- This is an output-format issue. Candidate: **F14**.

### C0: unreachable

- The 5 rows per run are `inval_i` and `cache_o.cmd_dir` (GT limits), `active_i` and `rs3_i` (declared at cfu.vhd:26 and :38, never read), and trng `fifo.free` (trng.vhd:163, never read).
- Forcing them in would add 70 / 70 / 74 FP for 5 TP. No rule.

---

## C. Generated-version false positives

The unified FP partition below is applied identically to all four versions. It is ordered, and the first matching predicate wins. Every FP row gets exactly one label: totals are 230 / 179 / 120 and 216 / 230 / 229.

| cluster | predicate | FP s0 / s1 / s2 | FP baseline mean (runs) | TP s0 / s1 / s2 | TP baseline mean |
|---|---|---|---|---|---|
| K0 not in closed set / repeat | ``(`class`=='absent') or repeat_emit`` | 3 / 2 / 2 | 4.00 (1/5/6) | 0 | 0 |
| K1 transaction record, whole port or internal | ``(bus_base or dmi_base) and `class` in ('port','signal')`` | 42 / 44 / 4 | 40.00 (43/41/36) | 0 | 0 |
| K2 transaction record, port field | ``class=='port-field'`` | 47 / 22 / 31 | 0.00 | 0 | 0 |
| K3 sub-block connection field | ``class=='signal-field' and portmap_actual`` | 24 / 32 / 21 | 39.67 (32/45/42) | 2 / 2 / 2 | 3.00 |
| K4 reset network (hand role set) | `reset_role` | 13 / 10 / 9 | 13.67 | 0 | 0 |
| K5 clock-enable ticks (hand role set) | `tick` | 6 / 2 / 4 | 10.33 | 0 | 0 |
| K6 storage array | `is_int and (storage_array or (registered and indexed_write))` | 10 / 10 / 10 | 10.00 | 3 / 3 / 3 | 3.00 |
| K7a interrupt-mask bit | `bus_cfg_write and only_feeds_nonbus_out and not read_in_condition` | 9 / 4 / 4 | 7.00 | 0 | 0 |
| K7b protocol-variant bit (hand role set) | `mode_bit` | 5 / 4 / 5 | 6.67 | 0 | 0 |
| K7c self-clearing command | `bus_cfg_write and n_const>=2` | 2 / 2 / 2 | 2.00 | 1 / 1 / 1 | 1.00 |
| K8 register copied to one output | `is_int and fwd_nonbus and only_feeds_nonbus_out` | 8 / 6 / 4 | 7.67 | 0 | 0 |
| K9 datapath intermediate | `is_int and registered and not width1 and not read_in_condition and not readback_only and not only_feeds_nonbus_out` | 13 / 9 / 3 | 12.33 | 1 / 1 / 1 | 1.00 |
| K10 read-back-only status | `is_int and readback_only and not read_in_condition` | 2 / 3 / 2 | 4.00 | 6 / 4 / 4 | 6.00 |
| K11 registered control state | `is_int and registered` | 21 / 10 / 9 | 22.00 | 11 / 6 / 4 | 11.33 |
| K12 combinational decision chain | `is_int and not registered and n_computed>0` | 10 / 7 / 4 | 14.33 | 11 / 9 / 5 | 12.00 |
| K13 non-record port | ``class=='port'`` | 11 / 5 / 6 | 15.67 | 24 / 23 / 13 | 39.33 |
| K14 internal glue | `is_int` | 4 / 7 / 0 | 15.67 | 3 / 3 / 3 | 6.00 |

### C-1. Port fields of transaction records (K2): generated prompts only

**Behaviour (MEASURED).** 47 / 22 / 31 FP, 0 TP, 0 FN. The baseline has 0 in every run. There are 56 distinct elements; 7 are FP in all three generated runs.
- `neorv32_spi:bus_rsp_o.data`, labelled 'exit port'. spi.vhd:146 `ctrl.irq_rx_avail <= bus_req_i.data(ctrl_irq_rx_avail_c);`; the field is the register read-back. The s0 concept "Interrupt enable flags (...)" lists four `ctrl.irq_*` fields plus `bus_rsp_o.data`, 5 references in all.
- `neorv32_imem:bus_req_i.data`, labelled 'sets'. imem.vhd:116 `mem_ram_b0(to_integer(addr)) <= bus_req_i.data(7 downto 0);`.
- `neorv32_bus:a_req_i.lock`. bus.vhd:111 `locked_nxt <= b_req_i.lock & a_req_i.lock;`. The value is held in `locked`.

**Chain:**
1. Recurring pattern: the read-back path is reported as the 'exit port', and the write path's input fields as 'sets'.
2. Criteria applied wrongly:
   - The exit-port rule is applied even to a relay. s0 L227: "even when the port is driven by a relay". s1 L222: "A directly connected outward port still qualifies as an exit port". s2 L106: "even when the port merely forwards it".
   - Field-level evaluation is applied to port records. s0 L239: "Evaluate a record and its fields independently."
3. Missing rule: the baseline's "Record-typed PORTS are named WHOLE" has no counterpart in the generated prompts. There is also no transport exclusion. (MEASURED from the prompt texts.)
   - The generated closed-set definition lists only "fields of internal record signals". So these outputs also break the prompt's own definition.
4. Candidate: **F1** (transport records; ports named whole).

### C-2. Per-destination interconnect ports (K1 in the interconnect module): s0 and s1

**Behaviour (MEASURED).**
- K1 FP in `neorv32_bus`: s0 41, s1 39, s2 0; baseline 19 / 17 / 12.
- `neorv32_bus:dev_05_req_o`. bus.vhd:622 `dev_05_req_o <= dev_req(5);` is a plain copy.
- The s0 concept "Device selection and per-device request strobes" alone has 32 exit-port references in the table (MEASURED). The generated FP analysis reports it has 0 TP; that figure was not re-derived here.
- s1 has one concept with 39 references (MEASURED); per the generated FP analysis it holds 1 TP, `port_sel` (not re-derived here).

**Chain:**
1. Recurring pattern: one routing decision is reported once per destination copy.
2. Criterion applied wrongly: "Apply exit-port analysis at every supplied entity boundary" (s1 L222), combined with the relay clauses above.
3. Missing rule: copies of one decision, one per destination, are not separate realizations.
4. Candidate: **F1** covers these ports.
5. REASONING: the s2 figure of 0 comes from one concept decision in one run. It is not evidence that s2's wording works.

### C-3. Sub-block connection fields (K3): shared

**Behaviour (MEASURED).** 24 / 32 / 21 FP, against a baseline of 39.67 per run. 12 distinct elements are FP in all four versions.
- `neorv32_uart:tx_fifo.wdata`. uart.vhd:250 `wdata_i => tx_fifo.wdata,` and :260 `tx_fifo.wdata <= bus_req_i.data(...)`.
- `neorv32_cache:cache_o.data`. cache.vhd:151 `cache_o.data <= host_req_i.data;`.
- The s1 uart reasoning walks the whole path: "Integrity of the received byte across rx_engine.sreg, rx_fifo.wdata, rx_fifo.rdata and the bus response".

**Chain:**
1. Recurring pattern: a port-map connection to a FIFO or memory is labelled 'stores'.
2. Criterion applied wrongly:
   - s0 L224: "A state-holding element remains a realization even if it later forwards that value."
   - s2 L104: "Storage remains a realization point even when loaded from another source."
   - Together with "several structural references along its path".
3. Missing rule: storage means the element is assigned in this entity. A field connected to a sub-block is a connection.
4. Candidate: **F3**.

### C-4. Fan-out and labels that contradict the RTL (cross-cutting; symptoms of C-1 to C-3)

**Fan-out (MEASURED).** Precision by the size of the smallest concept an element appears in, pooled over the 3 generated runs:

| concept size | all elements | excluding transaction records |
|---|---|---|
| 1 reference | 36/89 = 0.40 | 36/81 = 0.44 |
| 2–3 references | 98/277 = 0.35 | 98/229 = 0.43 |
| 4 or more | 49/344 = 0.14 | 49/211 = 0.23 |

- Concepts with no TP: 58/118, 51/99 and 29/65.
- Concepts named after a mechanism (FIFO, request, response, strobe, counter, ...) are almost never right. Concept–element pairs: 13 TP / 123 FP, 16 / 115 and 8 / 56. Other concepts: 62 / 139, 48 / 72 and 39 / 83.

**Labels (MEASURED).** Precision by realization label, pooled over the 3 generated runs:
- stores: 88/304
- sets: 19/105
- computes: 27/69
- exit port: 49/234

'Exit port' on plain non-record, non-reset ports is right most of the time: 19/24, 19/24 and 11/17.

Specific contradictions with the RTL:
- 'stores' on an element that no clocked process of this RTL assigns: FP 27 / 16 / 9, TP 7 / 2 / 2.
- 'sets' on an input port: FP 22 / 8 / 7, TP 5 / 4 / 1.

**Chain.** The shared definition sentence "One conceptual asset usually has several structural references along its path" (s0 L17, s1 L13, s2 L13) invites the model to list every hop.
- Candidate: **F9**, a definition rewrite. It is tentative.
- REASONING: the label errors are symptoms of the same fan-out, not an independent cause.

### C-5. Other generated FPs

These are mostly inherited from the baseline:
- 123 / 108 / 85 generated FPs are also baseline-majority FPs.
- Of the 107 / 71 / 35 that are not, transaction records account for 84 / 58 / 31.
- s0 adds serial-engine internals, visible in its K9 and K11 counts (13 and 21).
- The reset clauses in s1 and s2 did not remove the reset network: K4 is 13 / 10 / 9, against 13.67 in the baseline.

---

## D. Baseline false positives

**Mechanism (MEASURED + REASONING).**
- The baseline's justification is a counterfactual ("if X is tampered, behaviour changes"). The wording appears in 79.3% of FP rows and 79.2% of TP rows, so the model's own test does not separate them.
- 108.33 FP per run (102 / 104 / 119) sit in concepts with no TP. 116.67 per run sit in concepts that also contain a TP.
- 87.0 FP per run are one assignment hop from a TP of the same run. So are 37.0 TP per run. Adjacency alone cannot be a rule.

**Baseline-characteristic FPs** (larger than in every generated run):

| pattern | baseline per run | s0 / s1 / s2 |
|---|---|---|
| whole peripheral transaction ports (K1 outside the interconnect) | 24.0 | 1 / 5 / 4 |
| clock-enable tick plumbing (K5) | 10.33 | 6 / 2 / 4 |
| no-rule region (K10–K14) | 71.67 | 48 / 32 / 21 |
| internal glue (K14) | 15.67 | 4 / 7 / 0 |

**Chains for the separable baseline clusters:**

- **K1, whole peripheral bus ports.**
  - Example: `neorv32_uart:bus_req_i`, FP in 3/3 runs; the RTL uses it only as the access port (uart.vhd:179 `ctrl.enable <= bus_req_i.data(ctrl_en_c);`). Model: "If bus_req_i is forged or altered, writes/reads that update ctrl ... can be corrupted".
  - Criteria applied wrongly:
    - The (C) clause redirects buses instead of excluding them: "A plain data/address/control bus with no secret is NOT confidential -- evaluate it under (I)/(A) instead".
    - "which port carries it across the boundary?"
    - "Record-typed PORTS are named WHOLE ... the asset is the port itself".
  - Missing rule: a transport exclusion. Candidate: **F1**.

- **K3, sub-block connection fields: 39.67 per run.** Driven by "one conceptual asset normally maps to several: emit one object per element" and "Record-typed INTERNAL signals ... there the field is the asset". Candidate: **F3**.

- **K5, ticks.**
  - Example: `neorv32_wdt:prsc_tick`. wdt.vhd:141 `prsc_tick <= clkgen_i(clk_div4096_c);`. Model: "Tampering with prsc_tick ...".
  - The exclusion names only "Global clock and reset ports", so tick vectors slip through.
  - Candidate: **F4**.

- **K7a, interrupt-mask bits.**
  - Example: `neorv32_uart:ctrl.irq_rx_nempty`. uart.vhd:185 and :315–316 `irq_rx_o <= ctrl.enable and ((ctrl.irq_rx_nempty and rx_fifo.avail) or ...`.
  - The control-register concept is expanded field by field.
  - Candidate: **F5**.

- **K8, register copied to one output.**
  - Example: `neorv32_uart:tx_engine.txd`. uart.vhd:392 `uart_txd_o <= tx_engine.txd;`. The port is TP; the register is FP. Model: "the final internal serial bit before it is driven out".
  - Driven by "ask BOTH: which port ... which internal signal ... Emit an object for each that exists".
  - Candidate: **F7**.

- **K9, datapath intermediates.**
  - Example: `neorv32_cpu_cp_muldiv:div.quotient`. muldiv.vhd:264 `div.quotient <= std_ulogic_vector(0 - unsigned(rs1_i));`. Model: "the primary internal operand used by the iterative divider".
  - "STORES" is read as "every register on the path".
  - Candidate: **F8**, tentative.

**GT-disputed baseline clusters (no rule):**
- K4, reset network: 13.67 per run.
  - `neorv32_sys:rstn_sys_o`: sys.vhd:57 `sreg_sys <= sreg_sys(sreg_sys'left-1 downto 0) & '1';` and :59 `rstn_sys_o <= and_reduce_f(sreg_sys);`.
  - `neorv32_wdt:rstn_o`: wdt.vhd:161 `rstn_o <= not (hw_rst_timeout or hw_rst_access);`.
  - REASONING: the baseline prompt itself allows reset when "clock/reset control is the module's actual function".
- K6, storage arrays: 10 per run. 4 of these are the known imem GT omission.
- K7c, self-clearing bits: 2 per run. The GT keeps trng `fifo_clr` (trng.vhd:101, :106), which has the same role.

---

## E. Cross-version comparison

All rows are MEASURED. "All four" means the number of distinct elements that are FP in the baseline majority and in all three generated runs.

| pattern | baseline per run | s0 | s1 | s2 | in all four | classification |
|---|---|---|---|---|---|---|
| transaction record, any form (K1+K2) | 40.00 | 89 | 66 | 35 | form differs | **common**; form is version-sensitive |
| — port fields (K2) | 0 | 47 | 22 | 31 | 0 | **generated only**; associated with the missing "ports named WHOLE" clause |
| — per-destination interconnect ports | 16.0 | 41 | 39 | 0 | 0 | **s0/s1**; one concept each; associated with the exit-port-on-relay clauses |
| — whole peripheral bus ports | 24.0 | 1 | 5 | 4 | 0 | **baseline-characteristic**; associated with the (C)→(I)/(A) redirect |
| sub-block connection fields (K3) | 39.67 | 24 | 32 | 21 | 12 | **common** |
| reset network (K4) | 13.67 | 13 | 10 | 9 | 9 | **common**; not reduced by the s1/s2 reset clauses |
| clock-enable ticks (K5) | 10.33 | 6 | 2 | 4 | 0 | **baseline-heavier**; lower with the generated "enables … influences" clauses (association) |
| storage arrays (K6) | 10 | 10 | 10 | 10 | 10 | **common**, identical; GT limit |
| config bits (K7a/b/c) | 15.67 | 16 | 10 | 11 | 8 | **common** |
| register copied to one output (K8) | 7.67 | 8 | 6 | 4 | 3 | **common** |
| datapath intermediates (K9) | 12.33 | 13 | 9 | 3 | 2 | **common**; s0 adds extras |
| no-rule region (K10–K14) FP | 71.67 | 48 | 32 | 21 | 14 | **baseline-heavier**, but TP in K11–K14 also falls: 68.67 per run against 49 / 41 / 25 |
| input-port recall | 20.67/26 | 5/26 | 4/26 | 1/26 | — | **generated only** (FN) |
| signal recall | 28.0/32 | 24/32 | 17/32 | 15/32 | — | **s1, s2** |
| output-port recall | 18.67/21 | 19/21 | 19/21 | 12/21 | — | **s2 only** |
| concept never reported (C5) | — | 1 | 6 | 20 | — | **s2 mostly**; one run, may be noise |
| entity-prefixed name (C3) | 0 | 1 | 1 | 0 | — | **s0/s1** |
| unreachable (C0) | 5 | 5 | 5 | 5 | 5 | **common**; GT/RTL limit |

**Shared failure modes (task-formulation and definition weaknesses).**
- Both families tell the model to report several elements per concept. Neither says what is transport.
- Neither separates "assigned in this entity" (storage) from "connected to a sub-block".
- Neither gives a dedup rule between a register and the output port that copies it.
- Both expand configuration registers field by field.
- These shared patterns hold about 100 FP per run in the baseline (K3 + K4 + K6 + K7 + K8 + K9 = 39.67 + 13.67 + 10 + 15.67 + 7.67 + 12.33 = 99.0).

**Version-sensitive patterns:**
- Port fields: the baseline clause is present and they are absent.
- Input ports: the generated clause is present and they are lost.
- Per-destination exit ports: the s0/s1 relay and every-boundary clauses.
- Missing concepts: s2's evidence bar.
- Tick plumbing: baseline.

**Confounds (REASONING).** Every baseline-vs-generated difference is also a difference between worked examples and zero-shot, and between a 6.9k-character prompt and a longer generated one. The generated figures come from 1 run each. Baseline run-to-run spread inside one cluster reaches 13 FP (K3: 32 to 45). So only differences clearly larger than that spread are safe:
- Port fields.
- The interconnect ports.
- The input-port recall gap: 16 to 21 per run.
- s2's missing concepts: 20 against 1 or 6, but that comes from one run.

---

## F. Candidate rule set

Every predicate below was run on all four versions (6 runs).
- For exclusions, the counts are FP removed, TP lost, and FN inside the predicate (the elements it could never recover).
- For inclusions, the counts are FN recovered and TN newly predicted (the precision cost).
- Every effect is an oracle upper bound.
- Rule texts passed three checks in `rule_texts.py`: `prompts_v2.audit`, the underscored-corpus-identifier scan used by `audit_against_corpus`, and the numeric-hint scan.
- Any change needs its own output directory. It breaks direct comparability with the m4bc606 and v2x3r8 runs. Changes to the generated DEFINITIONS block need a new meta-prompt id.

### Summary

| id | rule | type | kind | verdict |
|---|---|---|---|---|
| F1 | transaction records are transport; ports named whole | structural realization, primary/secondary | new (generated) / conflict resolution (baseline redirect, exit-on-relay) | **keep** |
| F2 | an input port the entity reads is where the value is set | structural realization, data-flow | conflict resolution (replaces the input-port sentence) | **keep for the generated prompts** |
| F3 | a sub-block connection field is a carrier unless tested or computed here | primary/secondary, data-flow | clarification of "stores" | **keep** |
| F4 | clock-enable ticks are timing plumbing | security relevance | strengthening of the clock/reset exclusion | **keep** (hand role set) |
| F5 | an interrupt-enable mask bit is covered by its interrupt output | primary/secondary (granularity) | new | **tentative** (2 modules) |
| F6 | protocol-variant config bits are not reported | security relevance | test-specific heuristic | **do not promote** |
| F7 | a register copied unchanged to one plain output: report the port | structural realization (dedup) | conflict resolution ("ask BOTH") | **keep, narrow** |
| F8 | in-transit registers are stages, not assets | data-flow | new | **tentative** |
| F9 | fan-out definition rewrite | primary/secondary definition | clarification / conflict resolution | **tentative** |
| F10 | decision-holding internals are evaluated on their own | control-flow, primary/secondary | conflict resolution with the secondary definition | **tentative; not as an inclusion rule** |
| F11 | evaluate every plain output before calling its concept not established | evidence sufficiency | clarification | **tentative** |
| F12 | a wire driven by a sub-instance output is where its result exists | contextual information | clarification | **tentative** |
| F13 | closed-set post-filter and one row per element | output format / validation | code post-filter | **keep** |
| F14 | bare element names; the entity goes only in the entity field | output format | clarification | **keep** |
| F15 | labels tied to RTL facts | structural realization, output format | clarification | **tentative; self-check only** |

### F1. Transaction records are transport; ports are named whole

**Text:** "A port or signal whose record type carries complete read or write transactions between this block and an interconnect (address, write data, byte enables, strobe, acknowledge, read data) is transport. Do not report it, whole or by field. Do not use it as the exit of a value that a register holds and software can read back, or as the element that sets a value written into this block. Report the element inside the block that stores or decides the value. A port is a single candidate: name it whole; never report a field of a port."

- **Problem:** C-1 and C-2 in section C, and K1 in section D.
- **Predicate:** `bus_base or dmi_base`, where the base type is a bus or debug request/response record.
- **Evidence (MEASURED):**
  - FP removed: s0 89, s1 67, s2 35; baseline 43 / 42 / 37 (mean 40.67).
  - TP lost: 0 in all 6 runs. FN in the predicate: 0.
  - Precision after: 0.344 / 0.364 / 0.346; baseline 0.337 / 0.347 / 0.333. Recall unchanged.
  - Interconnect-module FP falls from 68 / 48 / 21 to 9 / 3 / 4.
  - FP rows come from 11 modules; the interconnect module holds 54% of them.
- **Modifies:**
  - Generated: resolves the conflict with the exit-port-on-relay clauses, and adds the missing "named whole" clause.
  - Baseline: replaces the (C)→(I)/(A) redirect for buses.
- **Recall risk (REASONING):** the model may extend "transport" to plain operand or data inputs, which the GT keeps (cfu `rs1_i`, `csr_wdata_i`). Read input-port recall after the next run.
- **Counterexamples:**
  - None in the GT.
  - `neorv32_cpu_pmp:ctrl_i` (control-bus record type) is GT and is FN in all 3 generated runs. It is not a transaction record and stays outside the predicate.
  - `neorv32_cpu_cp_muldiv:ctrl_i` has the same type but is not GT. So the rule must not widen to "all record ports".
  - A bus that carries a secret, such as a key-load port, is absent from this corpus. The rule would need an exception there (REASONING).
- **Falsified if:** transaction-record FP stays above 0 after the next run, or input-port or GT recall falls.

### F2. An input port the entity reads is where the value is set

**Text:** "An input port whose value this block itself reads, to store it, compute from it, or decide on it, is where that value enters the block. Report it as a structural reference of the concept it carries, with role sets. Do not report clock, clock-enable or reset inputs, or a port whose record type carries complete bus transactions."

- **Problem:** C1 in section B.
- **Predicate:** ``class=='port' and dir=='in' and not bus_typed and not clk_rst_named and (u_body>0 or u_pm>0) and not tick and element!='jtag_tck_i'``. The last two terms stand in for "clock-enable input". They come from a hand role set.
- **Evidence (MEASURED):**
  - Generated: FN recovered 19 / 20 / 23; TN added 7 / 12 / 12. Precision 0.282 / 0.305 / 0.340. Recall 0.838 / 0.757 / 0.613.
  - Baseline: +3.33 FN and +4.0 TN per run (mean). Precision 0.300, recall 0.883. The baseline already does most of this.
  - The FN rows come from 10 modules. The largest share is neorv32_cpu, at 24%.
- **Modifies:** replaces s0 L231, s1 L224 and s2 L106. In the meta prompt it defines "set" as including the input port that the entity reads.
- **Recall risk:** none; it is an inclusion. The precision risk is the TN list below.
- **Counterexamples (opposite decision correct):**
  - Non-GT inputs that would become FP: cache sub-entity `clr_i`, `inv_i`, `new_i`, `wdata_i`; cfu `funct3_i`, `rtype_i`; muldiv `ctrl_i`; dtm `dmi_rsp_i`; trng `en_i`, `enable_i`; twi `twi_scl_i`; cpu `icc_rx_i`.
  - The GT is inconsistent here: `twi_sda_i` is GT but `twi_scl_i` is not; pmp `ctrl_i` is GT but muldiv `ctrl_i` is not.
- **Confound:** the worked examples. See test G2.

### F3. A sub-block connection field is a carrier

**Text:** "A field of an internal record that only connects this block to an instantiated sub-block, receiving one of its outputs or passing a value unchanged to one of its inputs, is a carrier. Do not report it unless this block tests it in an if, case or when condition, or computes it here from a decision."

- **Problem:** C-3 in section C, and K3 in section D.
- **Predicate (X2c):** ``class=='signal-field' and portmap_actual and not read_in_condition and n_computed==0``.
- **Evidence (MEASURED):**
  - FP removed: s0 16, s1 24, s2 11; baseline 22 / 25 / 29 (mean 25.33).
  - TP lost: 0 in all 6 runs. FN in the predicate: trng `fifo.free`, which is never read and so unreachable.
  - Precision 0.257 / 0.292 / 0.292; baseline 0.321. Recall unchanged.
- **Stronger variant** (drop the "computed here" exception):
  - Removes 22 / 27 / 19 FP and 34.33 per run in the baseline.
  - Costs 1 TP per baseline run: trng `fifo.re` at trng.vhd:171 `fifo.re <= '1' when (bus_req_i.stb = '1') and ...`, which is computed here.
  - Default: keep the exception.
- **Counterexamples** (kept by the condition exception):
  - `neorv32_cache:cache_i.sta_hit`: cache.vhd:286 `hit_o => cache_i.sta_hit,` and :189 `elsif (cache_i.sta_hit = '1') then`.
  - `neorv32_trng:fifo.avail`: trng.vhd:167 and :114.
- **GT inconsistency:** trng FIFO fields are GT, but the same fields in uart, spi and twi are not.
- Evidence comes from 6 modules. No single module holds more than 28% of the FP rows.

### F4. Clock-enable ticks

**Text:** "Clock-enable ticks received from a shared prescaler, the single tick selected from them, and the local counters or one-cycle pulses that turn them into bit-rate strobes are timing plumbing. The configuration field that selects the rate is the asset; the tick is not."

- **Predicate:** `tick`, a hand-labelled role set of 17 elements in 5 modules, checked against the RTL.
- **Evidence (MEASURED):**
  - FP removed: baseline 11 / 10 / 10 (mean 10.33); s0 6, s1 2, s2 4.
  - TP lost 0. FN 0.
  - Baseline precision 0.306.
- **Counterexamples:** `neorv32_sys:clk_en_o` is GT. It is the generator's output port and sits outside the set. The rate-select fields (`ctrl.prsc`, `ctrl.cdiv`, `ctrl.baud`) are TP and are kept by the text.
- **Risk:** this is a semantic role. Features cannot check compliance, and the set must be re-labelled for new modules.

### F5. Interrupt-enable mask bits

**Text:** "A per-cause interrupt-enable bit whose only use is to be combined into an interrupt output is covered by that output. Report the interrupt output, not each mask bit."

- **Predicate:** `bus_cfg_write and only_feeds_nonbus_out and not read_in_condition`.
- **Evidence (MEASURED):**
  - FP removed: baseline 9 / 6 / 6 (mean 7.0); s0 9, s1 4, s2 4.
  - TP lost 0. FN 0.
- **Why tentative:** all the evidence comes from 2 modules (uart and spi). The interrupt outputs themselves are TP and stay.

### F6. Protocol-variant configuration bits (do not promote)

- **Predicate:** `mode_bit and element!='ctrl.strict'`.
- **Evidence (MEASURED):** removes 5.67 FP per run in the baseline and 4 / 3 / 4 in the generated runs. TP lost 0.
- **Why not promote:**
  - These fields have the same features as the TP configuration fields. The split follows GT taste only.
  - The evidence is a hand set of 6 elements in 3 modules.
  - REASONING: the security basis is weak. For example, flipping clock polarity breaks the link.

### F7. A register copied unchanged to one plain output: report the port

**Text:** "If an internal register's only use is to be copied unchanged to one output port that is not a transaction record, the register and the port are one asset at two places. Report the port only."

- **Predicate (X6b):** `is_int and fwd_nonbus and only_feeds_nonbus_out and not bus_cfg_write and not forwarded_to_out_port.str.contains('dmi_')`.
- **Evidence (MEASURED):**
  - FP removed: baseline 6 / 5 / 6 (mean 5.67); s0 6, s1 4, s2 2.
  - TP lost 0.
- **Counterexamples:** these TPs are correctly outside the predicate:
  - `neorv32_cpu_pmp:fail`: feeds `fault_o` through logic, pmp.vhd:363.
  - `neorv32_cpu_cp_muldiv:div.res`: feeds its output through a mux.
  - `ctrl.enable` → `clkgen_en_o`: `ctrl.enable` has other readers.
- **Broader "register or port, not both":** costs 6 TP per baseline run and 6 / 5 / 4 in the generated runs. Rejected.
- **Conflict with F1:** without the transaction-record exception, a dtm `dmi_ctrl.*` register copied into the debug request record would vanish entirely.
- **Substitution risk (REASONING):** the rule pushes toward the port. For spi `rtx_engine.sck`, that port is `spi_clk_o`, which is not GT.

### F8. In-transit registers (tentative)

**Text:** "A register that only holds a value in transit (a shift register that assembles or serialises a word, an operand copied in for timing, a partial result of a multi-cycle arithmetic operation, an address held during a transfer) is a stage of a value reported at its source or its result. Do not report it."

- **Evidence (MEASURED):**
  - Precise predicate: removes FP 13.33 per baseline run and 14 / 10 / 4 in the generated runs. Costs 1 TP in every run: `neorv32_debug_dtm:tap_reg.dtmcs`, dtm.vhd:195. It is a shift register that is also the control/status register.
  - Literal reading (any multi-bit register not tested in a condition): removes 30.0 FP but loses 8.0 TP per baseline run, and 8 / 7 / 5 in the generated runs.
- **Why tentative:** the prompt text cannot carry all of the predicate's exclusions.

### F9. Fan-out definition (tentative)

**Text:** "Report where the value enters this block, where it is decided or held, and the port through which it leaves. Elements between those points are carriers, even when they are registers or connections to a sub-block."

It replaces "One conceptual asset usually has several structural references along its path".
- **Evidence:** the concept-size precision table in section C-4. It cannot be simulated with an oracle.
- **Recall risk:** the TPs inside concepts of 4 or more references are 22 / 13 / 14.
- **Counterexample:** the GT itself keeps several elements per concept, for example `ctrl.enable` together with `clkgen_en_o`, and `fail` together with `fault_o`.

### F10. Decision-holding internals (tentative; not as an inclusion rule)

- **Predicate:** `is_int and registered and read_in_condition`.
- **Evidence (MEASURED):**
  - FN recovered 3 / 8 / 11, but TN added 27 / 38 / 40.
  - Precision falls to 0.231 / 0.249 / 0.259. Recall rises to 0.694 / 0.649 / 0.505.
  - Baseline: +3.33 FN and +25 TN per run.
  - 72% of the FN rows under the variant that excludes tick, reset and wiring are in one module (the interconnect).
- **Counterexamples:** non-GT elements of the same role, such as `keeper.busy`, cache `ctrl.buf_req`, spi `rtx_engine.state`, and twi `engine.state`.
- **Better route (REASONING):** a definition test. Remove "or an internal signal or register that influences a primary asset" from the secondary definition, then re-measure (test G6).

### F11. Plain output ports (tentative)

- **Predicate:** ``class=='port' and dir=='out' and not bus_typed and not dmi_base and not clk_rst_named``.
- **Evidence (MEASURED):** FN recovered 2 / 2 / 9, TN added 4 / 5 / 4. Precision 0.245 / 0.264 / 0.303. Recall 0.685 / 0.595 / 0.486.
- **Counterexamples:** trng `en_o` and `rnd_o`; cpu `icc_tx_o`; pmp `csr_o`; `spi_clk_o`; cache `rdata_o`.
- **Why tentative:** the gain is concentrated in s2's uart (a single run).

### F12. Sub-instance output wires (tentative)

- **Predicate:** ``class=='signal' and n_assign==0 and portmap_actual``.
- **Evidence (MEASURED):** FN recovered 5 / 4 / 5, TN added 9 / 8 / 10. Precision is about neutral: 0.248 / 0.267 / 0.278.
- **Why tentative:** all of the evidence is in neorv32_cpu.

### F13. Closed-set post-filter (code, not prompt text)

- **What it does:** drops names that are not in the parsed closed set, and keeps one row per (entity, element).
- **Evidence (MEASURED):** FP removed: baseline 1 / 5 / 6 (mean 4.0); s0 3, s1 2, s2 2. TP lost 0.
- **Examples:**
  - imem `mem_rom_c` is a constant, imem.vhd:44.
  - dtm `jtag_tdi_i` was emitted twice in baseline run 2.
- **Check first:** confirm it against the existing `verify_against_cache` path before adding it.

### F14. Bare names

**Text:** "Write the element as its bare declared name, also for a port of another entity in the same file; the entity goes only in the entity field."

- **Evidence (MEASURED):** +1 TP and −1 FP in s0 and in s1 (trng `data_o`).
- **Alternative:** a scorer normaliser would also fix it, but that changes the metric across versions.

### F15. Labels tied to RTL facts (self-check only)

- **Proposed checks:** 'stores' only for elements assigned in a clocked process of this block; 'computes' only when the right-hand side is an operation rather than a copy.
- **Evidence (MEASURED):**
  - As a filter, 'stores' on an unregistered element removes 27 / 16 / 9 FP but costs 7 / 2 / 2 TP. Recall drops by 0.063 / 0.018 / 0.018.
  - Deleting 'sets' on input ports would cost 5 / 4 / 1 TP and contradicts F2. So it is rejected.

### Rejected rules (MEASURED impact)

| rule | FP removed | TP lost / FN recovered | why rejected |
|---|---|---|---|
| reset network (`reset_role`) | 13.67 per baseline run; 13 / 10 / 9 generated | 0 TP lost | GT disagreement; contradicts the prompt's own reset-function exception; 2 modules |
| self-clearing command bits | 2 per run in every version | −1 TP in every run (trng `fifo_clr`) | GT is inconsistent |
| storage arrays | 10 per run in every version | −3 TP in every run (`key_mem`, `pmpcfg`, `pmpaddr`) | 4 of the 10 FP are the imem GT omission |
| register or port, not both | 11.67 per baseline run | −6 TP per baseline run | GT keeps both in several places |
| forcing never-read GT elements in | — | +5 FN recovered, +70 to 74 FP added | no RTL behaviour to ground them |

### Combined packages (MEASURED, oracle upper bound)

| package | s0 P / R | s1 P / R | s2 P / R | baseline mean P / R |
|---|---|---|---|---|
| as is | 0.243 / 0.667 | 0.263 / 0.577 | 0.273 / 0.405 | 0.296 / 0.853 |
| F1 + F3 + F13 | 0.378 / 0.667 | 0.427 / 0.577 | 0.385 / 0.405 | 0.378 / 0.853 |
| + F4 + F5 + F7 | 0.423 / 0.667 | 0.457 / 0.577 | 0.421 / 0.405 | 0.416 / 0.853 |
| + F2 | 0.465 / 0.838 | 0.491 / 0.757 | 0.482 / 0.613 | 0.418 / 0.883 |
| + F2 + F11 | 0.461 / 0.856 | 0.483 / 0.775 | 0.500 / 0.694 | 0.420 / 0.904 |

---

## G. Additional tests

| # | test | behavioural property isolated | hypotheses it separates | what to read |
|---|---|---|---|---|
| G1 | rerun s0, s1 and s2 unchanged, 3 runs each | sampling stability of concept selection | s2's evidence bar causes missing concepts **vs** a one-off sample | concept count per run; C5 FN; input-port recall |
| G2 | baseline R8 without worked examples, 3 runs | effect of examples on port binding | input-port loss caused by the generated input-port sentence **vs** by zero-shot prompting | input-port recall (now 19–22 of 26); port-field FP |
| G3 | s0 with only its input-port sentence replaced by F2 | the entry-point definition alone | the sentence causes C1 **vs** other generated wording does | input-port TP (now 5/26); TN inputs predicted; whether the internal sampler is dropped (substitution) |
| G4 | s0 plus only "a port is a single candidate; name it whole" | field-level wording vs exit-on-relay | port fields come from field wording **vs** from the exit rule | port-field FP (now 47); whole transaction-port FP (a rise means the transport sentence is also needed) |
| G5 | baseline plus F1, 3 runs | compliance with the transport rule and substitution | the model drops transport cleanly **vs** replaces it with internal copies or loses plain inputs | transaction-record FP (target 0); plain input-port recall; FP on K3 and K8 |
| G6 | generated DEFINITIONS with the "influences a primary asset" clause removed (new meta id) | the secondary definition's effect on internal decisions | C4 caused by the definition **vs** a preference for sinks | signal recall (now 24 / 17 / 15 of 32); FP on the F10 predicate |
| G7 | generated DEFINITIONS with F9 in place of "several structural references along its path" | fan-out | the fan-out sentence drives K3/K9/K11 FPs **vs** the concept framing does | precision in the concept-size-4+ bucket; TP in the 1–3 buckets |
| G8 | parse more GT modules beyond the 15 scored, and score F1, F3, F4 and F5 there | generality | the rules generalise **vs** they are tuned to these 15 modules | FP removed and TP lost on the new modules |
| G9 | on any held-out module whose port carries a secret value, if one exists | the F1 exception | "bus is plumbing" **vs** "bus can carry the asset" | absent from this corpus; state that before claiming F1 is safe in general |

---

## H. Prompt-refinement priorities

1. **F1 (transaction records are transport, ports named whole), in every version.** It has the largest effect and 0 TP cost in all 6 runs. Confirm with G5.
2. **F2 (input ports), in the generated prompts, through the meta-prompt definition of "set".** It carries the largest recall gain. Run G2 and G3 first, because the worked-example confound is untested.
3. **F13 in code, and F14 in the output-format section.** Mechanical fixes with 0 TP cost.
4. **F3 (connection fields) in its exception form.** 0 TP cost. The stronger form trades 9 FP for 1 TP per baseline run; that choice is the user's. Default: the exception form.
5. **F4, F5, F7.** Small, with 0 TP cost here. F5 rests on 2 modules, and F4 on a hand role set.
6. **Hold until tested:**
   - F9 and F10: definition changes; tests G6 and G7.
   - F11: needs G1.
   - F8, F12 and F15.
7. **Do not promote:** F6, the reset network, storage arrays, self-clearing bits, and "register or port, not both". They encode GT taste or cost TP.
8. **For every change:**
   - Write to a new output directory.
   - Re-read per-class recall (input ports, output ports, signals, signal fields) and FP on each rule's predicate.
   - Treat any TP lost on a predicate that was 0 here as falsifying that rule.
