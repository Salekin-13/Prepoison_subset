# neorv32_cpu_pmp

**Purpose (model):** Holds per-region PMP configuration and addresses (written via CSR), selects the effective access address/privilege, compares the access against configured regions to compute per-region match and allow decisions, accumulates a failure chain and latches an externally visible fault signal; provides CSR readback of configuration and addresses via csr_o.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | write a PMP configuration byte into a region's pmpcfg register (R/W/X/mode/lock fields) |  | 8 / 8 |
| configure | write a PMP region address into a region's pmpaddr register |  | 6 / 6 |
| read out | CSR readback of PMP configuration or PMP region address returned on csr_o |  | 8 / 8 |
| operate | select effective access context (address and privilege), match it against configured regions, compute per-region allow, fold results into fail(0), and update fault_o |  | 21 / 21 |
| lock | PMP region lock bit (cfg_l) stored in pmpcfg that prevents further writes to that region's configuration |  | 4 / 4 |
| reset | reset clears stored PMP state (pmpcfg, pmpaddr, addr_mask) and clears fault_o |  | 4 / 4 |

## Concept: Per-region PMP configuration bytes (R/W/X, mode fields, lock bit) that determine which operations are allowed and how regions are interpreted

- confidentiality: yes-assumed, line 190 `csr_o <= cfg_rd32(to_integer(unsigned(ctrl_i.csr_addr(1 downto 0))));` via csr_o -- pmpcfg contents are exposed by CSR readback to csr_o (csr_read_access) at line 190, so an external observer can learn the stored configuration.
- integrity: yes-rtl, line 127 `if (pmpcfg_we(i/4) = '1') and (pmpcfg(i)(cfg_l_c) = '0') then` via ctrl_i.csr_wdata -- pmpcfg is written from CSR data on the rising clock when pmpcfg_we is asserted and the lock bit is '0' (guard at line 127, assignments at 129-145) and those bits are used by perm_gen for allow decisions (e.g. line 323), so CSR writes can change protection while it is in use.
- availability: yes-rtl, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via ctrl_i.csr_wdata -- external CSR writes (ctrl_i.csr_wdata -> pmpcfg, lines 129-145) can set configuration to deny accesses which causes fail->fault_o to be asserted (fault assignment at line 363), preventing progress.
- undermined behavior: no, line 129 `pmpcfg(i)(cfg_r_c) <= ctrl_i.csr_wdata((i mod 4)*8+cfg_r_c);` via ctrl_i.csr_wdata -- pmpcfg is driven only by the csr_pmpcfg process from CSR write data (assignments at lines 129-145) and there is no alternate debug/test driver that replaces or bypasses those assignments.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| pmpcfg | neorv32_cpu_pmp | stores | 4 -> 129 `pmpcfg(i)(cfg_r_c) <= ctrl_i.csr_wdata((i mod 4)*8+cfg_r_c);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl_i.csr_wdata | neorv32_cpu_pmp | sets | 2 -> 129 `pmpcfg(i)(cfg_r_c) <= ctrl_i.csr_wdata((i mod 4)*8+cfg_r_c);` | SOURCES pmpcfg | verified |  | not listed |
| csr_o | neorv32_cpu_pmp | exit port | 2 -> 190 `csr_o <= cfg_rd32(to_integer(unsigned(ctrl_i.csr_addr(1 downto 0))));` | DERIVES_FROM cfg_rd32 | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): pmpcfg <- pmpcfg, pmpcfg_we; csr_o <- ctrl_i.csr_addr

## Concept: Per-region PMP address registers (the stored region addresses used for matching)

- confidentiality: yes-assumed, line 192 `csr_o <= addr_rd(to_integer(unsigned(ctrl_i.csr_addr(3 downto 0))));` via csr_o -- pmpaddr values are read back through addr_rd and exposed on csr_o by csr_read_access at line 192, so external observers can learn stored region addresses.
- integrity: yes-rtl, line 170 `if (pmpaddr_we(i) = '1') and (pmpcfg(i)(cfg_l_c) = '0') then` via ctrl_i.csr_wdata -- pmpaddr is written from CSR data when pmpaddr_we is asserted and the lock bit is '0' (guard at line 170, assignments at 173/176) and those addresses are used by comparators for match (lines 295-296), so CSR writes can change which region matches while operations run.
- availability: yes-rtl, line 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` via ctrl_i.csr_wdata -- external CSR writes can change pmpaddr so that matches/permissions cause fail and fault_o is asserted (fault assignment at line 363), which can stop progress.
- undermined behavior: no, line 173 `pmpaddr(i) <= "00" & ctrl_i.csr_wdata(XLEN-3 downto 0);` via ctrl_i.csr_wdata -- pmpaddr is driven only by the csr_pmpaddr process from CSR data (assignments at lines 173-176) and there is no alternate debug/test override for pmpaddr in the RTL.

| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| pmpaddr | neorv32_cpu_pmp | stores | 3 -> 173 `pmpaddr(i) <= "00" & ctrl_i.csr_wdata(XLEN-3 downto 0);` | CLOCKED_BY clk_i | verified |  | hit |
| ctrl_i.csr_wdata | neorv32_cpu_pmp | sets | 7 -> 173 `pmpaddr(i) <= "00" & ctrl_i.csr_wdata(XLEN-3 downto 0);` | SOURCES pmpaddr | verified |  | not listed |
| csr_o | neorv32_cpu_pmp | exit port | 3 -> 192 `csr_o <= addr_rd(to_integer(unsigned(ctrl_i.csr_addr(3 downto 0))));` | DERIVES_FROM addr_rd | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): pmpaddr <- pmpaddr_we, pmpcfg; csr_o <- ctrl_i.csr_addr

## Concept: Access context — the effective access address and privilege the PMP checks (the address and privilege selected for the current operation)


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| acc_addr | neorv32_cpu_pmp | computes | 2 -> 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` | DERIVES_FROM ctrl_i.pc_nxt | verified |  | not listed |
| ctrl_i.pc_nxt | neorv32_cpu_pmp | sets | 2 -> 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` | SOURCES acc_addr | verified |  | not listed |
| addr_ls_i | neorv32_cpu_pmp | sets | 2 -> 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` | SOURCES acc_addr | verified |  | hit |
| acc_priv | neorv32_cpu_pmp | computes | 2 -> 245 `acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv;` | DERIVES_FROM ctrl_i.cpu_priv | verified |  | not listed |
| ctrl_i.cpu_priv | neorv32_cpu_pmp | sets | 2 -> 245 `acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv;` | SOURCES acc_priv | verified |  | not listed |
| ctrl_i.lsu_mo_we | neorv32_cpu_pmp | sets | 2 -> 244 `acc_addr <= ctrl_i.pc_nxt   when (ctrl_i.lsu_mo_we = '0') else addr_ls_i;` | GATES acc_addr | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): acc_addr <- ctrl_i.lsu_mo_we; acc_priv <- ctrl_i.lsu_mo_we

## Concept: Per-region permission result (allow) — the computed predicate whether the present access is permitted by a region


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| allow | neorv32_cpu_pmp | computes | 3 -> 325 `allow(r) <= pmpcfg(r)(cfg_x_c);` | DERIVES_FROM pmpcfg | verified |  | not listed |
| ctrl_i.lsu_mo_we | neorv32_cpu_pmp | sets | 4 -> 321 `if (ctrl_i.lsu_mo_we = '0') then` | GATES allow | verified |  | not listed |
| ctrl_i.lsu_rw | neorv32_cpu_pmp | sets | 2 -> 328 `elsif (ctrl_i.lsu_rw = '0') then` | GATES allow | verified |  | not listed |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): allow <- acc_priv, ctrl_i.lsu_mo_we, ctrl_i.lsu_rw, pmpcfg

## Concept: Region-match decision (match) — which region, if any, matches the effective access address


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| match | neorv32_cpu_pmp | computes | 4 -> 310 `match(r) <= cmp_na(r);` | DERIVES_FROM cmp_na | verified |  | not listed |
| pmpcfg | neorv32_cpu_pmp | sets | 22 -> 318 `perm_gen: process(ctrl_i, acc_priv, pmpcfg)` | GATES match | occurrence only | no GATES record to 'match' at occurrence 22 | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): match <- cmp_ge, cmp_lt, pmpcfg; pmpcfg <- pmpcfg, pmpcfg_we

## Concept: Fail vector (fail) — the folded per-region denial result culminating in fail(0)


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| fail | neorv32_cpu_pmp | computes | 3 -> 354 `fail(r) <= not allow(r) when (match(r) = '1') else fail(r+1);` | DERIVES_FROM allow | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fail <- acc_priv, match

## Concept: Fault indicator output (fault_o) — the latched external signal that reports a PMP fault


| element | entity | role | occurrence -> line | edge | status | why | reference |
|---|---|---|---|---|---|---|---|
| fault_o | neorv32_cpu_pmp | exit port | 3 -> 363 `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` | GATED_BY fail | verified |  | hit |

Influence points (code, from the map's GATED_BY / SELECTED_BY / CONSTRAINED_BY records): fault_o <- ctrl_i.cpu_debug, fail
