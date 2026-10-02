# neorv32_cpu_pmp

**Purpose (model):** Implements the RISC-V physical memory protection (PMP) unit: it holds per-region configuration and address registers written via CSR, decodes an access address and privilege (from pc_nxt or LSU address/privilege), computes per-region match and allow decisions, combines them into a fail vector, and raises a latched fault_o output when a protected access is denied and not in debug.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | write per-region PMP configuration bytes (pmpcfg) via CSR writes |  | 13 / 13 |
| configure | write per-region PMP address registers (pmpaddr) via CSR writes |  | 8 / 8 |
| operate | evaluate an access: select acc_addr and acc_priv, compute region match and per-region allow, build fail vector and latch fault when denial occurs |  | 19 / 19 |
| read out | CSR readback of configuration and address registers (cfg_rd / addr_rd) returning values on csr_o |  | 15 / 15 |
| lock | lock bit (cfg_l) that freezes a region's configuration / address from CSR writes |  | 5 / 5 |
| reset | reset-to-zero of stored PMP state (pmpcfg, pmpaddr, addr_mask) and clear of latched fault_o |  | 10 / 10 |

## Concept: Per-region PMP configuration bytes (pmpcfg): the 8-bit fields holding permissions (R/W/X), mode and the lock bit

- confidentiality: yes-assumed, line 190 `csr_o <= cfg_rd32(to_integer(unsigned(ctrl_i.csr_addr(1 downto 0))));` via csr_o -- pmpcfg bytes are emitted for CSR readback via cfg_rd/cfg_rd32 into csr_o (csr read selection at line 190), so an external CSR read can observe these configuration bytes and the integrator may treat them as secret.
- integrity: yes-rtl, line 127 `if (pmpcfg_we(i/4) = '1') and (pmpcfg(i)(cfg_l_c) = '0') then` via ctrl_i.csr_wdata -- pmpcfg fields are written from ctrl_i.csr_wdata on the clock when pmpcfg_we(i/4) = '1' and the lock bit is '0' (guard at line 127) and those bits directly determine access permissions (perm_gen uses them at line 323), so external CSR writes can change protection decisions.
- availability: yes-rtl, line 127 `if (pmpcfg_we(i/4) = '1') and (pmpcfg(i)(cfg_l_c) = '0') then` via ctrl_i.csr_wdata -- CSR write path (pmpcfg written from ctrl_i.csr_wdata under pmpcfg_we, guard at line 127) lets an external CSR interface set or lock pmpcfg bits which can force denies (manifested as fault_o at line 363) and thus affect forward progress.
- undermined behavior: no, line 129 `pmpcfg(i)(cfg_r_c) <= ctrl_i.csr_wdata((i mod 4)*8+cfg_r_c);` via ctrl_i.csr_wdata -- pmpcfg is driven only via the CSR write path under the pmpcfg write-enable and reset (assignments such as line 129) and there is no separate runtime debug/test override that substitutes a different driver.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| pmpcfg | neorv32_cpu_pmp | stores | 4 -> 129 `pmpcfg(i)(cfg_r_c) <= ctrl_i.csr_wdata((i mod 4)*8+cfg_r_c);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl_i.csr_wdata | neorv32_cpu_pmp | sets | 2 -> 129 `pmpcfg(i)(cfg_r_c) <= ctrl_i.csr_wdata((i mod 4)*8+cfg_r_c);` | SOURCES pmpcfg | verified |  | not listed |
| pmpcfg_we | neorv32_cpu_pmp | sets | 3 -> 114 `pmpcfg_we(to_integer(unsigned(ctrl_i.csr_addr(1 downto 0)))) <= '1';` | SELECTED_BY ctrl_i.csr_addr | verified |  | not listed |
| csr_o | neorv32_cpu_pmp | exit port | 2 -> 190 `csr_o <= cfg_rd32(to_integer(unsigned(ctrl_i.csr_addr(1 downto 0))));` | DERIVES_FROM cfg_rd32 | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): pmpcfg <- pmpcfg, pmpcfg_we; pmpcfg_we <- ctrl_i.csr_addr, ctrl_i.csr_we; csr_o <- ctrl_i.csr_addr

## Concept: Per-region PMP address registers (pmpaddr): the stored region address words used to define boundaries for matching

- confidentiality: yes-assumed, line 192 `csr_o <= addr_rd(to_integer(unsigned(ctrl_i.csr_addr(3 downto 0))));` via csr_o -- pmpaddr words are read back via addr_rd -> csr_o (addr_rd built from pmpaddr at line 208 and selected to csr_o at line 192), so external CSR reads can observe stored region addresses.
- integrity: yes-rtl, line 173 `pmpaddr(i) <= "00" & ctrl_i.csr_wdata(XLEN-3 downto 0);` via ctrl_i.csr_wdata -- pmpaddr entries are written from ctrl_i.csr_wdata under pmpaddr_we when pmpcfg(i)(cfg_l_c) = '0' (guard/assignment at lines 170-173), and those addresses are used by the comparators to decide region matches (lines 295-296), so CSR writes can change which addresses match.
- availability: yes-rtl, line 170 `if (pmpaddr_we(i) = '1') and (pmpcfg(i)(cfg_l_c) = '0') then` via ctrl_i.csr_wdata -- pmpaddr updates are gated by pmpaddr_we (driven from CSR, see lines 156-158) and by pmpcfg lock checks (line 170), so the CSR interface can force, withhold or block address updates and thereby influence denial/fault behavior that affects progress.
- undermined behavior: no, line 173 `pmpaddr(i) <= "00" & ctrl_i.csr_wdata(XLEN-3 downto 0);` via ctrl_i.csr_wdata -- pmpaddr values are driven only via the CSR write path under the pmpaddr write-enable and reset (assignments at lines 173/176/168) and there is no alternative runtime debug/test path that supplies different drivers.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| pmpaddr | neorv32_cpu_pmp | stores | 3 -> 173 `pmpaddr(i) <= "00" & ctrl_i.csr_wdata(XLEN-3 downto 0);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl_i.csr_wdata | neorv32_cpu_pmp | sets | 7 -> 173 `pmpaddr(i) <= "00" & ctrl_i.csr_wdata(XLEN-3 downto 0);` | SOURCES pmpaddr | verified |  | not listed |
| pmpaddr_we | neorv32_cpu_pmp | sets | 3 -> 158 `pmpaddr_we(to_integer(unsigned(ctrl_i.csr_addr(3 downto 0)))) <= '1';` | SELECTED_BY ctrl_i.csr_addr | verified |  | not listed |
| csr_o | neorv32_cpu_pmp | exit port | 3 -> 192 `csr_o <= addr_rd(to_integer(unsigned(ctrl_i.csr_addr(3 downto 0))));` | DERIVES_FROM addr_rd | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): pmpaddr <- pmpaddr_we, pmpcfg; pmpaddr_we <- ctrl_i.csr_addr, ctrl_i.csr_we; csr_o <- ctrl_i.csr_addr

## Concept: Access request context (acc_addr and acc_priv): the address and privilege used to evaluate PMP rules for each access

- confidentiality: yes-assumed, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via fault_o -- acc_addr and acc_priv are external request/context values used in match/permission logic whose outcomes drive fail and fault_o (fault export at line 363), so observers can infer information about the request context from fault behavior.
- integrity: yes-assumed, line 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` via ctrl_i.pc_nxt, addr_ls_i, ctrl_i.cpu_priv, ctrl_i.lsu_priv -- acc_addr and acc_priv are assigned directly from external ctrl_i inputs (lines 244-245), so those external writers can change the request context and the module does not internally protect those inputs.
- availability: yes-rtl, line 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` via ctrl_i.lsu_mo_we -- the selection between pc_nxt and addr_ls_i and between cpu_priv and lsu_priv is controlled by the external input ctrl_i.lsu_mo_we (lines 244-245), so that external signal can force or freeze the request context and thereby affect progress.
- undermined behavior: no, line 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` via ctrl_i.lsu_mo_we -- acc_addr and acc_priv are produced by a single combinational selection from the listed inputs (lines 244-245) with no alternate debug/test override inside this module.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| acc_addr | neorv32_cpu_pmp | computes | 2 -> 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` | DERIVES_FROM ctrl_i.pc_nxt | verified |  | not listed |
| ctrl_i.pc_nxt | neorv32_cpu_pmp | sets | 2 -> 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` | SOURCES acc_addr | verified |  | not listed |
| addr_ls_i | neorv32_cpu_pmp | sets | 2 -> 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` | SOURCES acc_addr | verified |  | hit |
| acc_priv | neorv32_cpu_pmp | computes | 2 -> 245 `acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv;` | DERIVES_FROM ctrl_i.cpu_priv | verified |  | not listed |
| ctrl_i.cpu_priv | neorv32_cpu_pmp | sets | 2 -> 245 `acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv;` | SOURCES acc_priv | verified |  | not listed |
| ctrl_i.lsu_priv | neorv32_cpu_pmp | sets | 2 -> 245 `acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv;` | SOURCES acc_priv | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): acc_addr <- ctrl_i.lsu_mo_we; acc_priv <- ctrl_i.lsu_mo_we

## Concept: Per-region allow decision (allow): the computed permission bit that determines whether an access type and privilege are permitted by a region

- confidentiality: yes-assumed, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via fault_o -- allow decisions drive the fail vector (line 354) and the exported fault_o (line 363), so external observers can infer permission outcomes from fault events and timing.
- integrity: yes-rtl, line 323 `allow(r) <= pmpcfg(r)(cfg_x_c) or (not pmpcfg(r)(cfg_l_c));` via pmpcfg -- allow is computed from pmpcfg bits and control inputs in perm_gen (example assignment at line 323) and directly determines whether accesses are permitted (used by fail at line 354), so CSR writes or control inputs that change pmpcfg or request type can change this protection decision.
- availability: yes-rtl, line 321 `if (ctrl_i.lsu_mo_we = '0') then` via ctrl_i.lsu_mo_we -- perm_gen branches on ctrl_i.lsu_mo_we and ctrl_i.lsu_rw (starting at line 321) so external control signals select which permission (X/R/W) is checked and can thereby force or block allow and affect progress.
- undermined behavior: no, line 323 `allow(r) <= pmpcfg(r)(cfg_x_c) or (not pmpcfg(r)(cfg_l_c));` via pmpcfg -- allow is computed only in perm_gen from pmpcfg and access-type inputs (assignment at line 323) and there is no separate debug/test override that replaces this computation.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| allow | neorv32_cpu_pmp | computes | 3 -> 325 `allow(r) <= pmpcfg(r)(cfg_x_c);` | DERIVES_FROM pmpcfg | verified |  | not listed |
| ctrl_i.lsu_mo_we | neorv32_cpu_pmp | sets | 4 -> 321 `if (ctrl_i.lsu_mo_we = '0') then` | GATES allow | verified |  | not listed |
| ctrl_i.lsu_rw | neorv32_cpu_pmp | sets | 2 -> 328 `elsif (ctrl_i.lsu_rw = '0') then` | GATES allow | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): allow <- acc_priv, ctrl_i.lsu_mo_we, ctrl_i.lsu_rw, pmpcfg

## Concept: Latched PMP fault indicator (fault_o): the exported fault signal that reports a denied access (fail(0)) when not in CPU debug

- confidentiality: yes-assumed, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via fault_o -- fault_o is exported directly (assignment at line 363) and reveals denied-access events and therefore internal permission outcomes, so integrators may treat it as sensitive.
- integrity: yes-rtl, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via ctrl_i.cpu_debug -- fault_o is driven as (not ctrl_i.cpu_debug) and fail(0) (line 363), so the external cpu_debug input can mask or change the exported fault signal independent of the computed fail value.
- availability: yes-rtl, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via ctrl_i.cpu_debug -- cpu_debug gates the export of fail to fault_o (line 363), so an external debug mode input can suppress or force the observable fault and thereby affect the system's ability to observe or react to faults.
- undermined behavior: yes-rtl, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via ctrl_i.cpu_debug -- the cpu_debug input acts as a special mode that overrides the exported fault (fault_o <= (not ctrl_i.cpu_debug) and fail(0) at line 363), providing an alternate path that changes observed behavior.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| fault_o | neorv32_cpu_pmp | exit port | 3 -> 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` | GATED_BY fail | verified |  | hit |
| fail | neorv32_cpu_pmp | computes | 3 -> 354 `fail(r) <= not allow(r) when (match(r) = '1') else fail(r+1);` | DERIVES_FROM allow | verified |  | hit |
| ctrl_i.cpu_debug | neorv32_cpu_pmp | sets | 2 -> 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` | GATES fault_o | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fault_o <- ctrl_i.cpu_debug, fail; fail <- acc_priv, match
