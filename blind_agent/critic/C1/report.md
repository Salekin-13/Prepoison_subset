Note: the report file could not be written. The Write tool refused it with "Subagents should return findings as text, not write report files." The full report follows.

# Critic report: prompt C1, tuning run r0 (15 modules)

## Scope and method

- **Read:** TASK_BRIEF.md, MAP_FORMAT.md, prompts/C1/prompt.md, and all 15 executor outputs.
- **Inputs read (RTL and map), three only:**
  - **neorv32_cpu:** it has the longest list (31 entries) and is the only module that lists whole records.
  - **neorv32_bus:** it has six entities and router and mux logic, so parallel-structure errors are most likely.
  - **neorv32_cache:** the map has storage gaps on record fields, and the data path is built from FORWARDS fields.
- **Other 12 modules:** points about them rest only on the executor's own triage text. Their RTL was not read, and those points are marked "(RTL not read)".
- **Counts:** no commands were allowed. Every count is a hand count from files read in this session.
- **Line references:**
  - "Prompt line N" is the line in prompt.md.
  - "RTL N" is the source line number printed in the input file.
  - "map file line N" is the line in the input file.
- **Measured vs argued:** sections 1, 2, 3 and 5 report what the files say. Sections 4 and 6 are my argument.

## Answer first

The executor followed the step order and the output shape well. It also correctly overrode three map errors by reading the RTL:
- cpu `icc_tx_o` is marked tied in the map, but RTL 447 drives it.
- bus `arbiter.*` has storage none in the map, but RTL 763 clocks it.
- cache `ctrl.*` has storage none in the map, but RTL 126 clocks it.

Most faults come from three places where the prompt's own role tests disagree with each other:
1. records, pass-through and sub-unit wiring;
2. event flags and event inputs, which have no role;
3. addresses, which are called both primary and secondary.

Where the prompt disagreed with itself, the executor chose a different side in different modules.

## 1. Instructions ignored, misread or applied inconsistently

**1.1 cpu: whole records were listed against the granularity rule.**
- The listed records are `icc_tx_o`, `icc_rx_i`, `ibus_req_o`, `ibus_rsp_i`, `dbus_req_o`, `dbus_rsp_i` and `frontend`.
- Their fields have their own map lines (file lines 360-381 and 475-479).
- Prompt line 214 says: "List a record field, not its record, when the fields have their own lines."
- The executor followed prompt lines 129-130 instead: "Judge the record itself only if none of its fields has records." (See 4.1.)

**1.2 cpu: the "unused" rule and the FORWARDS rule were not applied to the `ctrl` fields.**
- The listed fields are `ctrl.pc_cur`, `ctrl.pc_nxt`, `ctrl.cpu_priv`, `ctrl.lsu_priv` and `ctrl.cpu_debug`.
- In the map (file lines 432, 433, 469, 455, 472) each has no records, no constant drivers, storage "not assigned", handling FORWARDS, and no connection of its own.
- None of these names appears in any RTL statement. Only the whole `ctrl` appears, in port maps (RTL 194, 253, 297, 321, 362, 384, 414).
- Two prompt rules exclude them: lines 127-128 (unused) and lines 175-176 (a field with handling FORWARDS is pass-through).
- The executor did apply this rule to the same record fields in cp_muldiv and cpu_pmp.

**1.3 cpu: "created output" was used where the definition does not hold.**
- `ibus_req_o` and `dbus_req_o` have drive `undriven` in the map (file lines 368 and 387).
- They are only wired to sub-unit ports (RTL 196 and 394).
- Prompt line 150 requires "drive driven, or a field with handling ORIGINATES … made in this module". Neither condition holds.

**1.4 cache: the FORWARDS = pass-through rule was used in bus but dropped in cache.**
- Three FORWARDS fields were listed:
  - `host_req_i.data` CARRIES `cache_o.data` (RTL 151);
  - `bus_rsp_i.data` CARRIES `cache_o.data` (RTL 236);
  - `host_rsp_o.data` COPIES `cache_i.data` (RTL 156).
- Prompt lines 175-176 make each of these pass-through, and lines 189-190 say pass-through ports are not listed.
- In bus, the executor used this same rule to drop gateway `req_i.data`, amo_rvs `core_req_i.data`, io_switch `main_req_i.*` and bus_reg `host_req_i.*`.

**1.5 bus: two listed registers have roles the prompt does not allow.**
- `keeper.err` was labelled "status". It is cleared every cycle (RTL 415) and set for one cycle on timeout (RTL 424).
- `sc_fail` was labelled "status / result". It is recomputed every cycle (RTL 957).
- Neither one is sticky. Lines 192-194 and the checklist at lines 302-304 allow only data store, secret, setting, operating state and sticky status.

**1.6 bus: `keeper.cnt` was listed as "operating state".**
- It is a timeout wait counter (RTL 418-423).
- Prompt line 170 names "wait counter" as a pacing counter.
- The executor used the "count is the module's job" escape in lines 170-171. But the gateway's job is routing, not counting.

**1.7 bus: the switch host data inputs were dropped as "pass-through" against the definition.**
- `a_req_i.data` and `b_req_i.data` have handling CONSUMES and SOURCE `x_req_o.data` (RTL 150-152).
- Pass-through (lines 175-176) needs COPIES/CARRIES or FORWARDS. Neither holds.
- The data-input definition (lines 147-149) does hold.
- The same applies to amo_rvs `sys_rsp_i.data`, which SOURCES `core_rsp_o.data` (RTL 964).

**1.8 bus: amo_rmw `core_req_i.amoop` was labelled "control input".**
- It CARRIES `arbiter_nxt.cmd` (RTL 778).
- Line 162 defines a control input as one with only GATES, SELECTS or comparison records.
- `core_req_i.data` has the same pattern (CARRIES `arbiter_nxt.wdata`, RTL 779), and it was listed.

**1.9 cache: "address registers" were ignored.**
- `ctrl.tag` and `ctrl.idx` are loaded from `host_req_i.addr` (RTL 180-181), held (RTL 141-142), and drive the refill address (RTL 225-238).
- Lines 141-143 put "address registers" under operating state. The executor labelled them "timing copy".
- `bus_req_o.addr` is ORIGINATES, driven, and DERIVES_FROM `ctrl.tag/idx/ofs` (map file lines 367-370). That makes it a computed output.
- The executor put `bus_req_o.addr` under an invented role, "address output".

**1.10 hwspinlock: `bus_req_i.rw` was listed as a data input (RTL not read).**
- Lines 163 and 168 name the read/write flag as a control input and a handshake.
- In all six other bus peripherals, the executor marked `bus_req_i.rw` as a control input.

**1.11 sys: `sreg_sys`, `sreg_ext` and `cnt` were listed (RTL not read).**
- The executor calls `sreg_sys` and `sreg_ext` "stretch and synchronize" shift registers. Line 172 makes such registers a timing copy.
- `cnt` is a tick divider. Line 170 makes a tick divider a pacing counter.

**1.12 wdt: the triage decision column says "judge its fields".** Line 282 allows only "primary / secondary / not an asset". This is cosmetic.

## 2. Inconsistent decisions (same role, different decision)

**2.1 Record ports wired straight to or from a sub-unit.**
- In io_switch, `main_req_i` and `main_rsp_o` (RTL 608-609) were not listed.
- In cpu, `ibus_*` (RTL 196-197), `dbus_*` (RTL 394-395) and `icc_*` (RTL 447-448) were all listed.
- The map facts are the same in both modules.

**2.2 Lock-capture registers.**
- Switch `locked` was listed. It captures the lock request at grant (RTL 111), holds it through `locked_nxt` (RTL 78), and gates `state_nxt`/`stb` (RTL 88, 100).
- Gateway `keeper.lock` was dropped as a "timing copy". It captures `req_i.lock` at transfer start (RTL 420), holds it, and gates `keeper.busy` (RTL 426).
- The only difference is coding style. (See 4.8.)

**2.3 One-cycle flags that drive an event output.**
- bus `keeper.err` (RTL 415/424, feeding `rsp_o.err` at RTL 401) was listed.
- bus `sc_fail` was listed.
- wdt `hw_rst_timeout` and `hw_rst_access` were not listed. The executor's own triage describes them as "one-cycle registered reset pulses feeding rstn_o" (RTL not read).

**2.4 Error outputs that pass on a device error.**
- Listed: gateway `rsp_o.err` and cache `host_rsp_o.err`.
- Not listed: switch `a_rsp_o.err` and `b_rsp_o.err` (ORIGINATES, driven, gated by `sel`, RTL 165 and 169), and amo_rmw `core_rsp_o.err` (RTL 827).
- The tie-break at lines 118-120 says an error output is an event output "even when it is copied from an internal flag".

**2.5 Addresses.**
- Listed in debug_dtm: `dmi_ctrl.addr` and `dmi_req_o.addr`.
- Not listed: cache `ctrl.tag`, `ctrl.idx` and `bus_req_o.addr`, and cpu `lsu_mar` and `alu_add`.

**2.6 Privilege and debug fields that are only passed on.**
- cpu `ctrl.cpu_priv`, `ctrl.lsu_priv` and `ctrl.cpu_debug` were listed. No cpu statement uses them.
- Fields with the same role were dropped as "only forwarded / never used" in:
  - every bus entity (for example amo_rmw `core_req_i.priv`, RTL 818);
  - uart, spi, twi, trng, wdt, imem and hwspinlock.

**2.7 Response data in the two parallel atomic units.**
- amo_rmw `sys_rsp_i.data` was listed.
- amo_rvs `sys_rsp_i.data` was not, although the output it SOURCES was listed (RTL 964).

**2.8 Synchronizer shift registers.**
- sys `sreg_sys` and `sreg_ext` were listed.
- uart `rx_engine.sync`, twi `io_con.*_ff`, trng cell `sync`/`sreg` and debug_dtm `tap_sync.*_ff`/`dr_trigger.sreg` were not.

**2.9 Clock ticks and dividers.**
- Every peripheral treats `clkgen_i` ticks as clock, which line 124 says is never an asset.
- sys lists the tick source `clk_en_o` and its divider `cnt`.
- spi `cdiv_cnt` and twi `clk_gen.cnt` are labelled pacing counters.

## 3. Listed elements that contradict the definition; omissions the definition demands

**Listed, although the executor's own reason contradicts the prompt:**
- **cpu `ibus_req_o`:** its reason names "the instruction fetch address and its privilege/debug attributes". The prompt calls both of those secondary (lines 29-31 and 166).
- **cpu `ctrl.cpu_priv` and `ctrl.lsu_priv`:** the reason says the sub-units use them. A mode attribute input must be one "that the module uses" (lines 155-156), and this module does not use them.
- **cpu `msi_i`, `mei_i`, `mti_i`, `firq_i`:**
  - They are labelled "data input", but they are single-bit request lines.
  - Their only use is being concatenated into a sub-unit input (RTL 276 and 266-268).
  - No data-input example in lines 148-149 is an event request. No prompt role fits these lines.
- **bus:** `keeper.cnt`, `keeper.err` and `sc_fail` (see 1.5 and 1.6).
- **cache:** the three FORWARDS fields from 1.4.
  - `cache_i.data` and `host_rsp_o.data` are both listed, but one only COPIES the other (RTL 156). Line 30 makes "passes it along" secondary, while D-c forces `cache_i.data` onto the list.
- **hwspinlock** `rw`, and **sys** `sreg_*`, `cnt` and `clk_en_o`.

**Omitted, although the prompt's own definitions include them.** This says nothing about whether they are in the reference.
- **cache:** `ctrl.tag`, `ctrl.idx` and `bus_req_o.addr`.
  - `ctrl.ofs` is borderline. It is the refill word pointer and part of `bus_req_o.addr` (RTL 227).
- **bus switch:** `a_req_i.data` and `b_req_i.data`.
- **bus error outputs:** switch `a_rsp_o.err` and `b_rsp_o.err`, and amo_rmw `core_rsp_o.err`.
- **bus amo_rmw** `core_req_i.amoop`, and **amo_rvs** `sys_rsp_i.data`.
- **Borderline:** switch `x_req_o.data` (ORIGINATES, driven, selects host data, RTL 150-152). The prompt names a "read-back selection of registers" but not a selection among inputs.
- **The lock pair:** `keeper.lock` and `locked` should either both be listed or both be dropped.

## 4. Prompt wording that is ambiguous, conflicting or easy to misapply

**4.1 The two record rules conflict.**
- Step C (lines 129-130) says to judge the record when no field has records.
- Step E (line 214) says to list fields whenever they have their own lines.
- Under Step C, the outcome depends on unrelated fields. cpu `ctrl` is split into fields only because `ctrl.pc_ret` is read at RTL 330, so `ctrl.pc_cur` and the others get listed. `frontend` has no field records, so the whole record is listed instead.
- This explains 1.1, 1.2, 2.1 and 2.6.

**4.2 The pass-through definition (lines 175-176) is too narrow and too wide.**
- **Too narrow:** muxes, OR-combiners and routers are not covered. Examples are the switch (RTL 140-152), the gateway (RTL 384-401) and io_switch (RTL 679-691). The executor improvised a rule that a selected value is pass-through.
- **Too wide:** "a field with handling FORWARDS" also catches write data that is stored inside a sub-unit, such as cache `host_req_i.data`.
- No sentence covers a value that is stored only inside a sub-unit.
- This explains 1.4, 1.7 and 2.7.

**4.3 D-c (line 191) lists every sub-unit link with no condition.**
- It runs before any pass-through test.
- The link definition (lines 157-158) needs the connection `mode`. In the cpu map, `mode` is null everywhere from file line 343 on, so the executor had to guess direction from port names.
- In a wiring-only top module, almost every wire becomes primary. This is how the cpu reached 31 entries.

**4.4 "Made in this module" (lines 150-152) is unclear.** It does not say whether the output of an instantiated sub-unit counts. This explains 1.3.

**4.5 "Tied … or an element that only ever gets constants" (line 126) catches real event flags.**
- A decoded flag set to '0' or '1' under conditions only ever gets constants. Examples are cache `host_rsp_o.err` (RTL 155 and 257) and bus `keeper.err` (RTL 412, 415 and 424).
- Read literally, this clause drops every such flag.
- The executor ignored the clause here, but used it for cp_muldiv `ctrl.out_en`.

**4.6 Two roles are missing.**
- There is no role for a one-cycle event register that is not sticky.
- There is no role for an event or request input: interrupt, reset request or debug-halt request.
- The executor improvised: "status" in bus, "data input" in cpu, and "secondary" in sys.

**4.7 Addresses are called both primary and secondary.**
- **Primary:** "pointers and addresses" (line 101) and "address registers" (lines 142-143).
- **Secondary:** "addresses it" and "keeps a short-lived copy" (line 30), and "address input" (line 166).
- Address outputs have no role at all.
- This explains 1.9 and 2.5.

**4.8 The operating-state test (lines 141-144) measures coding style.**
- With a default `x_nxt <= x` assignment (cache RTL 136-143, bus RTL 772, switch RTL 77-78), every register passes the test.
- With implicit hold, as in `keeper.lock`, a register fails it.
- This explains 2.2.

**4.9 "Count is the module's job" (lines 170-171) is a judgement call.** It explains why `keeper.cnt` and sys `cnt` were listed while spi `cdiv_cnt` and twi `clk_gen.cnt` were not.

**4.10 Record fields clocked as a whole show storage `none` in the map.**
- Examples: cache `ctrl.*` (map file lines 493-551) and bus `arbiter.*` (map file lines 2047-2077).
- D-d and D-e (lines 192 and 195) would drop them as combinational.
- The executor caught this from the RTL. But the prompt only warns in general terms (line 79).

**4.11 The data-input and control-input hints pull against the mechanical tests.** "Usually several bits wide" and "Usually a single bit" (lines 149 and 163) conflict with the CARRIES and SOURCES tests. hwspinlock `rw` and the cpu interrupt lines fall between the two.

## 5. Output faults

- **Names:**
  - In cpu, bus and cache, every listed element and entity matches a map line exactly. The hand check covered 64 entries: 31 in cpu, 17 in bus and 16 in cache.
  - The other 12 modules were not checked, because their inputs were not read.
- **Duplicates:**
  - No (element, entity) pair is repeated.
  - Two names repeat across entities in bus: `state` (switch and amo_rvs) and `core_rsp_o.data` (amo_rmw and amo_rvs). The contract allows this. It is a risk only if scoring matches on name alone.
- **Granularity:** cpu lists 7 whole records whose fields have their own lines. The brief's contract allows this, but prompt line 214 forbids it.
- **Triage format:** the wdt decision column (see 1.12).
- **Shape:** all 15 files have `module` first and `assets` last, with all keys present. Every objective is one of the three allowed words.
- **Objectives (not scored):** two parallel cpu fault events disagree. `lsu_err` is Availability and `pmp_fault` is Integrity.

## 6. The three prompt changes to make first

This section is reasoning. Each change needs a source and page in rationale.md (brief rule 4). The direction of each change, toward primary or toward secondary, must come from the sources, not from these outputs.

**1. One rule for values that only move through a module.**
- **Tied to:** 1.1-1.4, 1.7, 2.1, 2.6, 2.7, section 3, and 4.1-4.4.
- **What to change:**
  - Settle the conflict between Step C and Step E: always judge at field level, and say what to do with a field that has no records.
  - Give one decision each for:
    - a record port wired only to a sub-unit;
    - a FORWARDS field;
    - a value selected or OR-combined from inputs;
    - a value stored only inside a sub-unit.
  - Put D-c under the same test.
  - Do not rely on the connection `mode`, which can be null.
- **What it breaks:** cpu, bus and cache results will no longer be comparable with r0.
- **What to measure after the next run:**
  - (a) Listed elements that are FORWARDS-only or have drive `undriven`, and are not allowed by the new rule. This should be zero.
  - (b) Whether the cpu and io_switch structural pairs get the same decision.
  - (c) Precision and recall on cpu, bus and cache, each reported separately.
- **What would falsify it:** the same-structure pairs still get different decisions.

**2. Close the role gaps for events.**
- **Tied to:** 1.5, 2.3, 2.4, section 3, 4.5 and 4.6.
- **What to change:**
  - Add one role, with one decision, for a single-cycle event register.
  - Add one role, with one decision, for event and request inputs.
  - Narrow "tied" to elements whose value never changes.
  - State whether an error output that passes on a device error is an event output.
- **What it breaks:** decisions in bus, wdt, cpu and cache.
- **What to measure after the next run:**
  - Whether `keeper.err`, `sc_fail` and `hw_rst_*` all get the same decision.
  - Whether `a_rsp_o.err` and `rsp_o.err` get the same decision.
  - Precision and recall on bus, wdt and cpu.

**3. One rule for addresses.**
- **Tied to:** 1.9, 2.5, section 3 and 4.7. The coding-style wording (4.8) and the counter wording (4.9) can be fixed in the same edit.
- **What to change:**
  - Decide whether address registers, address outputs and held copies of a request address are primary or secondary.
  - Delete the opposing wording at line 101, lines 142-143 and line 30.
- **What it breaks:** debug_dtm and cache.
- **What to measure after the next run:**
  - Whether `dmi_ctrl.addr`/`dmi_req_o.addr` and `ctrl.tag`/`ctrl.idx`/`bus_req_o.addr` get the same decision.
  - Precision and recall on debug_dtm and cache.

Relevant paths:
- E:/jobs/ff/test/Prepoison_subset/blind_agent/prompts/C1/prompt.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/inputs/tuning/neorv32_cpu.txt
- E:/jobs/ff/test/Prepoison_subset/blind_agent/inputs/tuning/neorv32_bus.txt
- E:/jobs/ff/test/Prepoison_subset/blind_agent/inputs/tuning/neorv32_cache.txt
- E:/jobs/ff/test/Prepoison_subset/blind_agent/critic/C1/report.md (intended target; not written)

DONE