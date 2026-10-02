# Asset reliability clusters (9 runs: seed, seed+examples, +map)

| cluster | module | asset | hits | outputs naming it | kind | relationship pattern (code map) | decision role | top SITEs | model's realization labels |
|---|---|---|---|---|---|---|---|---|---|
| reliable | bus | a_req | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+IF_COND | {'stores': 9} |
| reliable | bus | b_req | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+IF_COND | {'stores': 9} |
| reliable | bus | sel | 9/9 | 9 | signal | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | WHEN_COND+LHS_PROC | {'computes': 9} |
| reliable | bus | port_sel | 9/9 | 9 | signal | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | INDEXED_NAME+LHS_CONC | {'computes': 9} |
| reliable | bus | stb | 9/9 | 9 | signal | drives and receives | no decision role | LHS_PROC+DIRR_ASS | {'computes': 9} |
| reliable | bus | keeper.err | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+RHS_OPERAND | {'stores': 9} |
| reliable | bus | keeper.halt | 7/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+IF_COND | {'stores': 7} |
| reliable | bus | keeper.cnt | 8/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+RHS_OPERAND | {'stores': 8} |
| reliable | bus | state | 14/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+RHS_OPERAND | {'stores': 14} |
| reliable | bus | state | 14/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+RHS_OPERAND | {'stores': 14} |
| reliable | bus | alu_res | 9/9 | 9 | register | drives and receives | no decision role | LHS_PROC+WHEN_EXPR | {'stores': 9} |
| reliable | cache | cache_i.sta_hit | 8/9 | 9 | signal | drives only | decides (GATES/SELECTS/CONSTRAINS) | IF_COND+ASSOC_ACTUAL | {'stores': 3, 'sets': 5} |
| reliable | cpu | msi_i | 8/9 | 9 | port in | drives only | no decision role | RHS_OPERAND | {'sets': 8} |
| reliable | cpu | mei_i | 8/9 | 9 | port in | drives only | no decision role | RHS_OPERAND | {'sets': 8} |
| reliable | cpu | irq_machine | 9/9 | 9 | signal | receives only | no decision role | ASSOC_ACTUAL+LHS_CONC | {'stores': 4, 'computes': 5} |
| reliable | cpu | mti_i | 8/9 | 9 | port in | drives only | no decision role | RHS_OPERAND | {'sets': 8} |
| reliable | cpu | pmp_fault | 8/9 | 8 | signal | wired only (connections, no relationship) | no decision role | ASSOC_ACTUAL+LHS_CONC | {'stores': 6, 'sets': 2} |
| reliable | cpu | rf_wdata | 9/9 | 9 | signal | receives only | no decision role | ASSOC_ACTUAL+LHS_CONC | {'stores': 4, 'computes': 5} |
| reliable | cpu | csr_rdata | 7/9 | 9 | signal | drives only | no decision role | ASSOC_ACTUAL+RHS_OPERAND | {'stores': 5, 'computes': 1, 'sets': 3} |
| reliable | cpu_cp_cfu | key_mem | 9/9 | 9 | register | drives and receives | no decision role | INDEXED_NAME+LHS_PROC | {'stores': 9} |
| reliable | cpu_cp_cfu | csr_we_i | 8/9 | 9 | port in | drives only | decides (GATES/SELECTS/CONSTRAINS) | IF_COND | {'sets': 8} |
| reliable | cpu_cp_cfu | csr_addr_i | 9/9 | 9 | port in | drives only | decides (GATES/SELECTS/CONSTRAINS) | INDEX | {'sets': 9} |
| reliable | cpu_cp_cfu | csr_wdata_i | 9/9 | 9 | port in | relay (COPIES/CARRIES only) | no decision role | DIRR_ASS | {'sets': 9} |
| reliable | cpu_cp_cfu | rs1_i | 9/9 | 9 | port in | relay (COPIES/CARRIES only) | no decision role | DIRR_ASS | {'sets': 9} |
| reliable | cpu_cp_cfu | rs2_i | 9/9 | 9 | port in | relay (COPIES/CARRIES only) | no decision role | DIRR_ASS | {'sets': 9} |
| reliable | cpu_cp_cfu | result_o | 9/9 | 9 | port out | receives only | no decision role | LHS_PROC | {'exit port': 9} |
| reliable | cpu_cp_cfu | valid_o | 9/9 | 9 | port out | receives only | no decision role | LHS_PROC | {'exit port': 9} |
| reliable | cpu_cp_muldiv | ctrl.cnt | 8/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+RHS_OPERAND | {'stores': 8} |
| reliable | cpu_cp_muldiv | ctrl.state | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+IF_COND | {'stores': 11} |
| reliable | cpu_cp_muldiv | ctrl.rs1_is_signed | 8/9 | 9 | signal | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | IF_COND+LHS_CONC | {'stores': 1, 'computes': 7} |
| reliable | cpu_cp_muldiv | ctrl.rs2_is_signed | 8/9 | 9 | signal | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | RHS_OPERAND+LHS_CONC | {'stores': 1, 'computes': 7} |
| reliable | cpu_cp_muldiv | mul.prod | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | PART_SELECT+LHS_PROC | {'stores': 9} |
| reliable | cpu_cp_muldiv | div.res | 9/9 | 9 | signal | drives and receives | no decision role | LHS_CONC+PROCESS_TRIG | {'stores': 3, 'computes': 6} |
| reliable | cpu_cp_muldiv | rs1_i | 8/9 | 8 | port in | drives only | decides (GATES/SELECTS/CONSTRAINS) | RHS_OPERAND+INDEXED_NAME | {'sets': 8} |
| reliable | cpu_cp_muldiv | rs2_i | 8/9 | 8 | port in | drives only | decides (GATES/SELECTS/CONSTRAINS) | RHS_OPERAND+INDEXED_NAME | {'sets': 8} |
| reliable | cpu_cp_muldiv | res_o | 9/9 | 9 | port out | receives only | no decision role | LHS_PROC | {'exit port': 10} |
| reliable | cpu_cp_muldiv | valid_o | 8/9 | 8 | port out | receives only | no decision role | LHS_CONC | {'exit port': 8} |
| reliable | cpu_pmp | pmpcfg | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | INDEXED_NAME+IF_COND | {'stores': 11, 'sets': 2} |
| reliable | cpu_pmp | pmpaddr | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | INDEXED_NAME+PART_SELECT | {'stores': 9, 'sets': 2} |
| reliable | cpu_pmp | fault_o | 9/9 | 9 | port out | receives only | no decision role | LHS_PROC | {'exit port': 9} |
| reliable | debug_dtm | jtag_tdo_o | 9/9 | 9 | port out | receives only | no decision role | LHS_PROC | {'exit port': 25} |
| reliable | debug_dtm | tap_reg.dtmcs | 9/9 | 9 | register | drives and receives | no decision role | LHS_PROC+INDEXED_NAME | {'stores': 9, 'sets': 2} |
| reliable | debug_dtm | dmi_ctrl.busy | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+IF_COND | {'stores': 9} |
| reliable | hwspinlock | lock_q | 9/9 | 9 | register | drives and receives | no decision role | LHS_PROC+INDEXED_NAME | {'stores': 13} |
| reliable | hwspinlock | sel | 9/9 | 9 | signal | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | INDEXED_NAME+IF_COND | {'computes': 13} |
| reliable | imem | rdata | 9/9 | 9 | signal | drives and receives | no decision role | PART_SELECT+LHS_PROC | {'stores': 9} |
| reliable | imem | addr | 9/9 | 9 | signal | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | INDEX+DIRR_ASS | {'stores': 1, 'sets': 4, 'computes': 4} |
| reliable | imem | rden | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+WHEN_COND | {'stores': 9} |
| reliable | spi | ctrl.enable | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | DIRR_ASS+RHS_OPERAND | {'stores': 9} |
| reliable | spi | ctrl.cdiv | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+DIRR_ASS | {'stores': 9} |
| reliable | spi | ctrl.prsc | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+DIRR_ASS | {'stores': 9} |
| reliable | spi | spi_csn_o | 9/9 | 9 | port out | receives only | no decision role | LHS_PROC+INDEXED_NAME | {'exit port': 9} |
| reliable | spi | clkgen_en_o | 8/9 | 9 | port out | relay (COPIES/CARRIES only) | no decision role | LHS_CONC | {'exit port': 8} |
| reliable | spi | spi_dat_o | 7/9 | 7 | port out | receives only | no decision role | LHS_CONC | {'exit port': 7} |
| reliable | spi | irq_o | 7/9 | 9 | port out | receives only | no decision role | LHS_PROC | {'exit port': 7} |
| reliable | sys | clk_en_o | 9/9 | 9 | port out | receives only | no decision role | LHS_CONC+INDEXED_NAME | {'exit port': 9} |
| reliable | trng | data_o | 9/9 | 9 | port out | relay (COPIES/CARRIES only) | no decision role | LHS_CONC | {'exit port': 10} |
| reliable | trng | enable | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+DIRR_ASS | {'stores': 9} |
| reliable | trng | valid_o | 8/9 | 9 | port out | receives only | no decision role | LHS_CONC | {'exit port': 9} |
| reliable | trng | fifo.avail | 9/9 | 9 | signal | drives only | decides (GATES/SELECTS/CONSTRAINS) | DIRR_ASS+IF_COND | {'stores': 8, 'sets': 1} |
| reliable | twi | ctrl.enable | 8/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | DIRR_ASS+LHS_PROC | {'stores': 9} |
| reliable | twi | ctrl.cdiv | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+DIRR_ASS | {'stores': 9} |
| reliable | twi | ctrl.prsc | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+DIRR_ASS | {'stores': 9} |
| reliable | twi | twi_sda_o | 9/9 | 9 | port out | relay (COPIES/CARRIES only) | no decision role | LHS_CONC | {'exit port': 9} |
| reliable | twi | irq_o | 9/9 | 9 | port out | receives only | no decision role | LHS_PROC | {'exit port': 9} |
| reliable | uart | ctrl.enable | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | DIRR_ASS+IF_COND | {'stores': 9} |
| reliable | uart | ctrl.baud | 9/9 | 9 | register | drives and receives | no decision role | DIRR_ASS+LHS_PROC | {'stores': 9} |
| reliable | uart | ctrl.prsc | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+DIRR_ASS | {'stores': 9} |
| reliable | uart | clkgen_en_o | 8/9 | 9 | port out | relay (COPIES/CARRIES only) | no decision role | LHS_CONC | {'exit port': 8} |
| reliable | uart | irq_rx_o | 9/9 | 9 | port out | receives only | no decision role | LHS_PROC | {'exit port': 9} |
| reliable | uart | irq_tx_o | 9/9 | 9 | port out | receives only | no decision role | LHS_PROC | {'exit port': 9} |
| reliable | uart | uart_txd_o | 8/9 | 8 | port out | relay (COPIES/CARRIES only) | no decision role | LHS_CONC | {'exit port': 8} |
| reliable | uart | uart_rtsn_o | 9/9 | 9 | port out | receives only | no decision role | LHS_PROC | {'exit port': 9} |
| reliable | wdt | ctrl.enable | 7/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | RHS_OPERAND+LHS_PROC | {'stores': 7} |
| reliable | wdt | ctrl.lock | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+IF_COND | {'stores': 9} |
| reliable | wdt | ctrl.timeout | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+DIRR_ASS | {'stores': 9} |
| reliable | wdt | cnt | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+RHS_OPERAND | {'stores': 9} |
| reliable | wdt | reset_cause | 9/9 | 9 | register | drives and receives | no decision role | LHS_PROC+DIRR_ASS | {'stores': 9} |
| reliable | wdt | reset_wdt | 9/9 | 9 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+IF_COND | {'stores': 9} |
| reliable | wdt | clkgen_en_o | 9/9 | 9 | port out | relay (COPIES/CARRIES only) | no decision role | LHS_CONC | {'exit port': 9} |
| difficult | cache | ctrl.buf_sync | 6/9 | 6 | signal | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+RHS_OPERAND | {'stores': 6} |
| difficult | cache | we_i | 4/9 | 9 | port in | drives only | decides (GATES/SELECTS/CONSTRAINS) | IF_COND+INDEXED_NAME | {'sets': 4} |
| difficult | cache | addr_i | 5/9 | 6 | port in | drives only | no decision role | PART_SELECT | {'sets': 6} |
| difficult | cpu | lsu_err | 4/9 | 4 | signal | wired only (connections, no relationship) | no decision role | ASSOC_ACTUAL | {'stores': 4} |
| difficult | cpu | lsu_wait | 3/9 | 3 | signal | wired only (connections, no relationship) | no decision role | ASSOC_ACTUAL | {'stores': 3} |
| difficult | cpu | dbi_i | 3/9 | 3 | port in | wired only (connections, no relationship) | no decision role | ASSOC_ACTUAL | {'sets': 3} |
| difficult | cpu | alu_res | 6/9 | 9 | signal | drives only | no decision role | RHS_OPERAND+ASSOC_ACTUAL | {'stores': 2, 'computes': 3, 'sets': 2} |
| difficult | cpu | alu_add | 4/9 | 4 | signal | wired only (connections, no relationship) | no decision role | ASSOC_ACTUAL | {'stores': 2, 'sets': 1, 'computes': 1} |
| difficult | cpu | lsu_mar | 3/9 | 3 | signal | wired only (connections, no relationship) | no decision role | ASSOC_ACTUAL | {'stores': 3} |
| difficult | cpu_cp_cfu | start_i | 6/9 | 9 | port in | drives only | decides (GATES/SELECTS/CONSTRAINS) | IF_COND | {'sets': 10} |
| difficult | cpu_cp_muldiv | mul.start | 5/9 | 9 | signal | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | IF_COND+LHS_CONC | {'sets': 1, 'computes': 4} |
| difficult | cpu_cp_muldiv | div.start | 5/9 | 9 | signal | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_CONC+IF_COND | {'sets': 1, 'computes': 4} |
| difficult | cpu_pmp | ctrl_i | 6/9 | 9 | port in | no relationship | no decision role | FIELD_USE+PROCESS_TRIG | {'sets': 32} |
| difficult | cpu_pmp | addr_ls_i | 6/9 | 9 | port in | drives only | no decision role | WHEN_EXPR | {'sets': 6} |
| difficult | cpu_pmp | fail | 6/9 | 9 | signal | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | INDEXED_NAME+LHS_CONC | {'computes': 6} |
| difficult | debug_dtm | jtag_tdi_i | 6/9 | 6 | port in | drives only | no decision role | RHS_OPERAND | {'sets': 7} |
| difficult | sys | enable_i | 5/9 | 9 | port in | drives only | no decision role | RHS_OPERAND | {'sets': 5} |
| difficult | trng | fifo.re | 6/9 | 6 | signal | receives only | no decision role | ASSOC_ACTUAL+LHS_CONC | {'computes': 6} |
| difficult | trng | fifo_clr | 6/9 | 8 | register | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_PROC+WHEN_COND | {'stores': 6} |
| difficult | uart | uart_ctsn_i | 6/9 | 6 | port in | drives only | no decision role | RHS_OPERAND | {'sets': 6} |
| difficult | wdt | cnt_timeout | 6/9 | 9 | signal | drives and receives | decides (GATES/SELECTS/CONSTRAINS) | LHS_CONC+RHS_OPERAND | {'computes': 6} |
| chance | cpu | firq_i | 2/9 | 2 | port in | wired only (connections, no relationship) | no decision role | ASSOC_ACTUAL | {'sets': 2} |
| chance | debug_dtm | jtag_tms_i | 1/9 | 1 | port in | drives only | no decision role | RHS_OPERAND | {'sets': 1} |
| chance | spi | spi_dat_i | 2/9 | 3 | port in | relay (COPIES/CARRIES only) | no decision role | DIRR_ASS | {'sets': 2} |
| chance | twi | twi_sda_i | 1/9 | 6 | port in | drives only | no decision role | RHS_OPERAND | {'sets': 1} |
| chance | uart | uart_rxd_i | 2/9 | 3 | port in | relay (COPIES/CARRIES only) | no decision role | DIRR_ASS | {'sets': 2} |
| never seen | cache | cache_o.cmd_dir | 0/9 | 0 | not in map | None | None | None | {} |
| never seen | cache | inval_i | 0/9 | 0 | not in map | None | None | None | {} |
| never seen | cpu_cp_cfu | rs3_i | 0/9 | 0 | port in | no relationship | no decision role | none | {} |
| never seen | cpu_cp_cfu | active_i | 0/9 | 0 | port in | no relationship | no decision role | none | {} |
| never seen | trng | fifo.free | 0/9 | 0 | signal | wired only (connections, no relationship) | no decision role | ASSOC_ACTUAL | {} |
