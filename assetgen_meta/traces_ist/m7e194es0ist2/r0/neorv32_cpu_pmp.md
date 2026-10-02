# neorv32_cpu_pmp

**Purpose (model):** PMP unit: accepts CSR writes that configure per-region PMP entries (pmpcfg and pmpaddr), provides CSR readback, takes an access address and privilege inputs, computes region matches (TOR/NAPOT) and per-region allow decisions, aggregates a fail vector and produces a fault output when an access is disallowed.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | PMP region configuration bytes (permission bits, mode, lock) written into pmpcfg by CSR writes |  | 9 / 9 |
| configure | PMP region addresses written into pmpaddr by CSR writes |  | 7 / 7 |
| lock | cfg_l (lock) bit that freezes a region's pmpcfg/pmpaddr from further CSR updates |  | 3 / 3 |
| operate | Access evaluation: compute address masks, compare acc_addr vs stored pmpaddr (NAPOT/TOR), select matching region and derive per-region allow bit |  | 18 / 18 |
| report | Aggregate fail vector into a fault indication and drive fault_o when an access is disallowed and not in debug |  | 7 / 7 |
| read out | CSR readback of packed pmpcfg words (cfg_rd32) and readback of stored addresses (addr_rd) onto csr_o |  | 11 / 11 |
| reset | Resetting stored PMP state (pmpcfg, pmpaddr, addr_mask) and clearing fault_o |  | 5 / 5 |

## Concept: PMP region configuration (per-region permission bits, address-matching mode, lock bit L)

- confidentiality: yes-assumed, line 190 `csr_o <= cfg_rd32(to_integer(unsigned(ctrl_i.csr_addr(1 downto 0))));` via csr_o -- The CSR read path copies pmpcfg to cfg_rd and into cfg_rd32 and drives csr_o when a CSR read selects the PMP config (csr_read_access -> csr_o at line 190), so external software can read the configuration; the integrator may treat these bits as secret.
- integrity: yes-rtl, line 127 `if (pmpcfg_we(i/4) = '1') and (pmpcfg(i)(cfg_l_c) = '0') then` via ctrl_i.csr_wdata -- pmpcfg fields are written from ctrl_i.csr_wdata under the guard (pmpcfg_we(i/4) = '1') and (pmpcfg(i)(cfg_l_c) = '0') (if at line 127) and these bits decide permissions used by perm_gen (line 323), so CSR writes can change protection while the system runs.
- availability: yes-rtl, line 127 `if (pmpcfg_we(i/4) = '1') and (pmpcfg(i)(cfg_l_c) = '0') then` via pmpcfg(i)(cfg_l_c) (settable via ctrl_i.csr_wdata) -- The CSR-write guard checks the lock bit pmpcfg(i)(cfg_l_c) (line 127) and that lock bit is itself written from CSR (line 145), so an external CSR can set L and freeze further pmpcfg updates, preventing reconfiguration.
- undermined behavior: no, line 129 `pmpcfg(i)(cfg_r_c) <= ctrl_i.csr_wdata((i mod 4)*8+cfg_r_c);` -- pmpcfg is driven only by the csr_pmpcfg process from CSR writes (assignments such as line 129) and there is no alternate debug/test override path in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| pmpcfg | neorv32_cpu_pmp | stores | 4 -> 129 `pmpcfg(i)(cfg_r_c) <= ctrl_i.csr_wdata((i mod 4)*8+cfg_r_c);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl_i | neorv32_cpu_pmp | sets | 6 -> 129 `pmpcfg(i)(cfg_r_c) <= ctrl_i.csr_wdata((i mod 4)*8+cfg_r_c);` | SOURCES pmpcfg | verified | (via field ctrl_i.csr_wdata) | hit |
| pmpcfg_we | neorv32_cpu_pmp | computes | 3 -> 114 `pmpcfg_we(to_integer(unsigned(ctrl_i.csr_addr(1 downto 0)))) <= '1';` | SELECTED_BY ctrl_i.csr_addr | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): pmpcfg <- pmpcfg, pmpcfg_we; pmpcfg_we <- ctrl_i.csr_addr, ctrl_i.csr_we

## Concept: PMP region base addresses (per-region pmpaddr values used for matching)

- confidentiality: yes-assumed, line 192 `csr_o <= addr_rd(to_integer(unsigned(ctrl_i.csr_addr(3 downto 0))));` via csr_o -- pmpaddr is copied into addr_rd (lines 207-208) and csr_read_access drives addr_rd onto csr_o when address readback is selected (line 192), so external software can read the stored addresses; integrator may treat them as secret.
- integrity: yes-rtl, line 170 `if (pmpaddr_we(i) = '1') and (pmpcfg(i)(cfg_l_c) = '0') then` via ctrl_i.csr_wdata -- pmpaddr(i) is written from ctrl_i.csr_wdata when pmpaddr_we(i)='1' and pmpcfg(i)(cfg_l_c)='0' (guard at line 170) and pmpaddr is used by the comparators (cmp_ge/cmp_lt, lines 295-296) to select regions, so CSR writes can change which region matches during operation.
- availability: yes-rtl, line 170 `if (pmpaddr_we(i) = '1') and (pmpcfg(i)(cfg_l_c) = '0') then` via pmpcfg(i)(cfg_l_c) (settable via ctrl_i.csr_wdata) -- pmpaddr writes are gated by the lock bit pmpcfg(i)(cfg_l_c) (checked at line 170), and an external CSR write can set that lock (line 145) or refrain from asserting pmpaddr_we (line 158) to stop/address updates, freezing address configuration.
- undermined behavior: no, line 173 `pmpaddr(i) <= "00" & ctrl_i.csr_wdata(XLEN-3 downto 0);` -- pmpaddr is driven only by the csr_pmpaddr process from CSR write data (assignment example at line 173) and the RTL contains no separate debug/test override path for pmpaddr.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| pmpaddr | neorv32_cpu_pmp | stores | 3 -> 173 `pmpaddr(i) <= "00" & ctrl_i.csr_wdata(XLEN-3 downto 0);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl_i | neorv32_cpu_pmp | sets | 15 -> 173 `pmpaddr(i) <= "00" & ctrl_i.csr_wdata(XLEN-3 downto 0);` | SOURCES pmpaddr | verified | (via field ctrl_i.csr_wdata) | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): pmpaddr <- pmpaddr_we, pmpcfg

## Concept: Access address used for match (acc_addr derived from pc_nxt or load/store address)

- confidentiality: yes-assumed, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via fault_o -- acc_addr is selected from ctrl_i.pc_nxt or addr_ls_i (line 244) and participates in match/comparison logic that gates fail(0) and therefore fault_o (line 363), so observing fault_o can leak information about the accessed address; integrator may treat addresses as sensitive.
- integrity: yes-assumed, line 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` via ctrl_i.pc_nxt / addr_ls_i -- acc_addr is taken directly from external inputs (ctrl_i.pc_nxt or addr_ls_i) via the combinational selection at line 244, so whichever master drives those inputs can change the access address used for matching.
- availability: no, line 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` -- acc_addr is a combinational selection from inputs (line 244) and is not gated or stalled inside this PMP module, so nothing internal to the module can freeze its update.
- undermined behavior: no, line 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` -- acc_addr has a single combinational driver (line 244) selecting between pc_nxt and addr_ls_i and there is no separate debug/test bypass in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| acc_addr | neorv32_cpu_pmp | computes | 2 -> 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` | DERIVES_FROM ctrl_i.pc_nxt | verified |  | not listed |
| ctrl_i | neorv32_cpu_pmp | sets | 22 -> 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` | SOURCES acc_addr | verified | (via field ctrl_i.pc_nxt) | hit |
| addr_ls_i | neorv32_cpu_pmp | sets | 2 -> 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` | SOURCES acc_addr | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): acc_addr <- ctrl_i.lsu_mo_we

## Concept: Access privilege used in permission decisions (acc_priv from cpu_priv or lsu_priv)

- confidentiality: yes-assumed, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via fault_o -- acc_priv is selected from ctrl inputs (line 245) and influences the fail/ fault decision (seed at line 351 and fault_o at line 363), so external observation of faults can reveal privilege information; integrator may treat privilege as sensitive.
- integrity: yes-assumed, line 245 `acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv;` via ctrl_i.cpu_priv / ctrl_i.lsu_priv -- acc_priv is taken directly from ctrl inputs (line 245) and is used by perm_gen (lines 321-341) to compute allow, so an external agent that drives those inputs can change the privilege used for permission decisions.
- availability: no, line 245 `acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv;` -- acc_priv is combinationally selected from inputs (line 245) and there is no internal enable or stall that can freeze it inside the PMP module.
- undermined behavior: no, line 245 `acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv;` -- acc_priv has a single combinational source from ctrl_i fields (line 245) and the RTL provides no alternate debug/test override.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| acc_priv | neorv32_cpu_pmp | computes | 2 -> 245 `acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv;` | DERIVES_FROM ctrl_i.cpu_priv | verified |  | not listed |
| ctrl_i | neorv32_cpu_pmp | sets | 24 -> 245 `acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv;` | SOURCES acc_priv | verified | (via field ctrl_i.lsu_priv) | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): acc_priv <- ctrl_i.lsu_mo_we

## Concept: Region-match decision (which PMP region matches the access: TOR / NAPOT selection)

- confidentiality: yes-assumed, line 354 `fail(r) <= not allow(r) when (match(r) = '1') else fail(r+1);` via fault_o -- match selects which region's deny/allow feeds the fail chain (assignment at line 354) and that chain drives fault_o (line 363), so external observation of faults can leak which region matched; integrator may treat the matching decision as sensitive.
- integrity: yes-rtl, line 305 `match(r) <= cmp_ge(r) and cmp_lt(r);` via pmpcfg / pmpaddr / acc_addr (driven via ctrl_i.csr_wdata, ctrl_i.pc_nxt, addr_ls_i) -- match is computed from pmpcfg, pmpaddr and acc_addr (match_gen, lines 301-314) and those inputs are writable/driven from CSR or the control bus, so external CSR writes or input changes can alter which region matches while accesses are decided.
- availability: no, line 305 `match(r) <= cmp_ge(r) and cmp_lt(r);` -- match is combinationally evaluated in match_gen (assignment at line 305) and there is no run-enable or stall input inside the PMP that can freeze the match computation.
- undermined behavior: no, line 305 `match(r) <= cmp_ge(r) and cmp_lt(r);` -- match is produced only by the match_gen logic (lines 301-314) and the RTL contains no alternate debug/test bypass that substitutes a different match result.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| match | neorv32_cpu_pmp | computes | 2 -> 305 `match(r) <= cmp_ge(r) and cmp_lt(r);` | GATED_BY cmp_ge | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): match <- cmp_ge, cmp_lt, pmpcfg

## Concept: Per-region allow decision (allow(r)) that grants or denies the access

- confidentiality: yes-assumed, line 354 `fail(r) <= not allow(r) when (match(r) = '1') else fail(r+1);` via fault_o -- allow decisions flow into the fail chain (line 354) that drives fault_o (line 363), so observing fault events can reveal whether particular accesses were allowed; integrator may treat permission decisions as sensitive.
- integrity: yes-rtl, line 323 `allow(r) <= pmpcfg(r)(cfg_x_c) or (not pmpcfg(r)(cfg_l_c));` via pmpcfg / acc_priv / ctrl_i.lsu_mo_we / ctrl_i.lsu_rw -- allow is computed from pmpcfg and acc_priv under control of lsu_mo_we/lsu_rw in perm_gen (assign at line 323), and those inputs are externally writable/controllable (CSR writes, control bus), so an external actor can change allow while an access is being decided.
- availability: no, line 323 `allow(r) <= pmpcfg(r)(cfg_x_c) or (not pmpcfg(r)(cfg_l_c));` -- allow is computed combinationally in the perm_gen process (assignment example at line 323) and no internal run-enable/stall blocks its evaluation.
- undermined behavior: no, line 323 `allow(r) <= pmpcfg(r)(cfg_x_c) or (not pmpcfg(r)(cfg_l_c));` -- allow is produced only by perm_gen from pmpcfg/acc_priv/control inputs and there is no alternate debug/test override of the allow assignments in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| allow | neorv32_cpu_pmp | computes | 3 -> 325 `allow(r) <= pmpcfg(r)(cfg_x_c);` | DERIVES_FROM pmpcfg | verified |  | not listed |
| ctrl_i | neorv32_cpu_pmp | sets | 28 -> 321 `if (ctrl_i.lsu_mo_we = '0') then` | GATES allow | verified | (via field ctrl_i.lsu_mo_we) | hit |
| ctrl_i | neorv32_cpu_pmp | sets | 29 -> 328 `elsif (ctrl_i.lsu_rw = '0') then` | GATES allow | verified | (via field ctrl_i.lsu_rw) | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): allow <- acc_priv, ctrl_i.lsu_mo_we, ctrl_i.lsu_rw, pmpcfg

## Concept: Aggregated access-fail decision (fail vector, and specifically fail(0) used to fault)

- confidentiality: yes-assumed, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via fault_o -- fail(0) is used to drive the external fault output (line 363), so observing fault_o reveals whether the aggregated fail chain determined an access failure and thereby leaks internal match/allow results; integrator may treat this as sensitive.
- integrity: yes-rtl, line 354 `fail(r) <= not allow(r) when (match(r) = '1') else fail(r+1);` via allow / match (driven by pmpcfg/pmpaddr/ctrl inputs) -- fail entries are assigned from allow and match (line 354); allow and match are derived from pmpcfg/pmpaddr/acc_priv which are writable/controllable from CSR and control inputs, so external changes can alter fail and thereby change enforcement.
- availability: yes-rtl, line 351 `fail(NUM_REGIONS) <= '1' when (acc_priv /= priv_mode_m_c) else '0';` via acc_priv -- fail(NUM_REGIONS) is seeded from acc_priv (line 351), an external control input, so an actor controlling privilege inputs can force the seed value and thereby cause the fail chain to assert and block progress.
- undermined behavior: yes-rtl, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via ctrl_i.cpu_debug -- cpu_debug gates the external fault output (fault_o <= (not ctrl_i.cpu_debug) and fail(0) at line 363), allowing a debug mode to suppress reporting of fail states even when fail indicates an access denial.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| fail | neorv32_cpu_pmp | computes | 3 -> 354 `fail(r) <= not allow(r) when (match(r) = '1') else fail(r+1);` | DERIVES_FROM allow | verified |  | hit |
| fail | neorv32_cpu_pmp | computes | 2 -> 351 `fail(NUM_REGIONS) <= '1' when (acc_priv /= priv_mode_m_c) else '0';` | GATED_BY acc_priv | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fail <- acc_priv, match

## Concept: Fault indication exported (fault_o) that signals a disallowed access

- confidentiality: yes-assumed, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via fault_o -- fault_o is an external port driven from internal fail(0) and cpu_debug (line 363), so external observers learn when accesses are disallowed and the integrator may treat those events as sensitive.
- integrity: yes-rtl, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via ctrl_i.cpu_debug -- fault_o is assigned from (not ctrl_i.cpu_debug) and fail(0) on the rising clock (line 363), so the cpu_debug input (and any inputs that influence fail(0)) can change the externally observed fault signal.
- availability: yes-rtl, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via ctrl_i.cpu_debug -- ctrl_i.cpu_debug directly gates fault_o at line 363, enabling an external debug mode to suppress (block) fault reporting and thereby affect availability of the fault indication.
- undermined behavior: yes-rtl, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via ctrl_i.cpu_debug -- cpu_debug selects a different externally visible behavior for fault_o (it masks the signal at line 363), providing a special-mode bypass of external fault reporting.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| fault_o | neorv32_cpu_pmp | exit port | 3 -> 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` | GATED_BY fail | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fault_o <- ctrl_i.cpu_debug, fail

## Concept: CSR readback values (packed cfg_rd32 and addr_rd driven onto csr_o)

- confidentiality: yes-assumed, line 190 `csr_o <= cfg_rd32(to_integer(unsigned(ctrl_i.csr_addr(1 downto 0))));` via csr_o -- The CSR read path drives cfg_rd32 or addr_rd onto the external port csr_o when ctrl_i.csr_addr selects the PMP CSR (csr_read_access assigns csr_o at line 190/192), so readback exposes configuration and addresses; integrator may treat those values as secret.
- integrity: yes-assumed, line 203 `cfg_rd(i) <= pmpcfg(i);` via pmpcfg / pmpaddr (driven by ctrl_i.csr_wdata) -- cfg_rd and addr_rd are derived from pmpcfg and pmpaddr (cfg_rd <= pmpcfg at line 203 and addr_rd assigned from pmpaddr at lines 207-208) which are themselves writable via CSR, so readback values can be changed by CSR writes and their trust depends on integration.
- availability: no, line 186 `csr_read_access: process(ctrl_i.csr_addr, cfg_rd32, addr_rd)` -- csr_o is produced combinationally by csr_read_access (process starting at line 186) and will reflect cfg_rd32 or addr_rd whenever ctrl_i.csr_addr selects the PMP CSR; there is no internal run-enable that freezes readback.
- undermined behavior: no, line 190 `csr_o <= cfg_rd32(to_integer(unsigned(ctrl_i.csr_addr(1 downto 0))));` -- csr_o is driven only by the csr_read_access selection (example assignment at line 190) and the RTL includes no alternate debug/test path that substitutes different readback values.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| csr_o | neorv32_cpu_pmp | exit port | 2 -> 190 `csr_o <= cfg_rd32(to_integer(unsigned(ctrl_i.csr_addr(1 downto 0))));` | DERIVES_FROM cfg_rd32 | verified |  | not listed |
| cfg_rd32 | neorv32_cpu_pmp | computes | 4 -> 236 `cfg_rd32(i) <= cfg_rd(i*4+3) & cfg_rd(i*4+2) & cfg_rd(i*4+1) & cfg_rd(i*4+0);` | DERIVES_FROM cfg_rd | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): csr_o <- ctrl_i.csr_addr
