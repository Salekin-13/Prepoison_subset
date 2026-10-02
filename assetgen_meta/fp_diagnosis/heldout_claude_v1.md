# Why precision does not improve: heldout_claude_v1 (heldout, 1 run)

Evidence comes from what the model reads and cites: the occurrence IDs and the relationship map of its input. Every count below is computed from the runs and the maps by `assetgen_meta/fp_diagnosis.py`; nothing is estimated. Precision (P) = share of listed elements that are in the reference; recall (R) = share of reference entries that were listed. TP = listed and in the reference; FP = listed and not in it.

Runs: assets_opt_heldout_v1_r0 P 0.329 R 0.931 (TP 176, FP 359). Mean P 0.329, R 0.931.

## Answer

- **Citations.** 93% of FP citations are verified (the cited occurrence is the element's own and the cited edge exists there and fits the role), against 100% for TPs. Verified is a necessary condition: it shows the model read the RTL as the map records it, not that the element is an asset.
- **Shared signatures.** 54% of FPs have a behaviour signature (L2) that at least one TP in these runs also has; with the exact set of record types (L3), 25%. A rule stated on the signature cannot drop those FPs without dropping the TPs that share it.
- **Signature-rate selectors over the whole map** (all 1,713 elements; list a signature when its reference rate on the other modules is high enough; best of L1-L3, threshold read off this set's curve, so optimistic): precision 0.425 (R 0.878) at recall >= 0.85 and 0.544 (R 0.72) at recall >= 0.70. With the rates fitted to this set itself (in-sample): 0.724 (R 0.862) at recall >= 0.85. The runs: P 0.329 at R 0.931. 2 of 189 reference entries have no element of that exact name in the map.
- **A filter on the model's own list** (keep an element when its signature's hit rate among the other modules' listed elements is high enough; best of L1-L3, threshold read off this set's curve): precision 0.537 (R 0.852) at recall >= 0.85 and 0.615 (R 0.762) at recall >= 0.70.
- **Learnt on tuning, applied here once** (level and threshold chosen on tuning only, by training F1: L3; in-sample training F1 favours the finest level): P 0.551, R 0.571, F1 0.561, against the runs' P 0.329, R 0.931, F1 0.486. All levels are in D3c.
- **Whole concepts.** 239 FPs (67%) sit in 96 of 209 concepts (per run) that contain no reference element.
- **The precision edits** (D6), re-applied as code filters over 1 run(s): edit A would still drop 16 FPs and 0 TPs, edit B 2 FPs and 0 TPs, both (A then B) 17 FPs and 0 TPs.

Reading (each line follows from the numbers above):
- Precision 0.85 at recall >= 0.85 is not reached by any selector or filter of these forms with rates learnt on other modules (best leave-one-module-out 0.537; the in-sample values in D3 and D3b are fitted to the labels they score).
- A filter of these forms raises precision at recall >= 0.85 by up to +0.208: part of the FPs can be removed by structure, at a recall cost.
- The filter carried from tuning raises F1 by +0.075: a structural filter learnt elsewhere removes part of the FPs here. This is an exploratory reading of outputs already used once, not a result; it needs a fresh check before use.
- 17 FPs are still removable by the edits' own rules (A then B) without losing a TP: the model did not follow the edits fully on those (D6).
- Hypothesis, not measured here: the FPs that share a signature with TPs (54% at L2) are decided by conventions of the reference that the RTL structure does not record. D4 shows pairs; the fault reporter tests this per relationship type.

## D1. Are false positives misreadings? (citation status)

| label | listed | verified | statuses |
|---|---|---|---|
| TP | 176 | 100% | {'verified': 176} |
| FP | 359 | 93% | {'verified': 334, 'map gap claimed': 24, 'occurrence only': 1} |

## D2. Do false positives look like hits? (signature shared with a TP)

| level | signatures | FP in a signature that also holds a TP | share | FP in signatures with no TP |
|---|---|---|---|---|
| L1 | 10 | 350 of 359 | 98% | 9 |
| L2 | 67 | 195 of 359 | 54% | 164 |
| L3 | 242 | 91 of 359 | 25% | 268 |

Largest behaviour signatures (L2), pooled over runs:

| signature | FP | TP | TP in modules | FP in modules |
|---|---|---|---|---|
| signal field, stored; controls another element, used here | 42 | 2 | cpu_cp_shifter | cpu_control, cpu_cp_bitmanip, cpu_cp_fpu, debug_dm, neoled, onewire |
| signal field, stored; updates itself, controls another element, used here | 23 | 0 |  | cpu_control, cpu_cp_bitmanip, cpu_cp_fpu, cpu_frontend, debug_dm, neoled |
| signal field, comb; controls another element, used here | 21 | 0 |  | cpu_control, cpu_cp_bitmanip, cpu_cp_crypto, cpu_cp_fpu, cpu_cp_shifter, cpu_frontend |
| signal field, stored; carries data into an output, written from an input, used here | 20 | 2 | debug_dm, neoled | cpu_control, cpu_frontend, debug_dm, neoled, sdi, slink |
| signal field, stored; carries data into an output, used here | 18 | 0 |  | cpu_control, cpu_cp_fpu, debug_dm, twd |
| signal field, comb; feeds a sub-unit, used here | 18 | 0 |  | cpu_frontend, debug_dm, neoled, onewire, sdi, slink |
| port-in, not assigned here; controls another element, used here | 16 | 20 | cpu_control, cpu_cp_cond, cpu_cp_fpu, cpu_cp_shifter, cpu_decompressor, cpu_icc | cpu_control, cpu_counters, cpu_cp_fpu |
| signal, comb; controls another element, used here | 15 | 3 | cpu_control, cpu_counters, cpu_decompressor | cpu_control, cpu_counters, cpu_cp_bitmanip, cpu_cp_crypto, cpu_cp_fpu, debug_dm |
| signal field, stored; used here | 15 | 0 |  | cpu_control, cpu_cp_fpu, debug_dm, sdi, twd |
| port-out, comb; no local use | 14 | 32 | cpu_alu, cpu_counters, cpu_cp_bitmanip, cpu_cp_cond, cpu_cp_crypto, cpu_cp_fpu | cpu_control, cpu_counters, cpu_cp_fpu, cpu_lsu, onewire, pwm |
| port-in, not assigned here; used here | 12 | 26 | cpu_control, cpu_counters, cpu_cp_bitmanip, cpu_cp_crypto, cpu_cp_fpu, cpu_regfile | cpu_control, cpu_counters, cpu_cp_fpu, debug_auth, pwm, sdi |
| signal field, stored; controls another element, carries data into an output, written from an input, used here | 11 | 8 | debug_dm, gptmr, neoled, onewire, sdi, slink | debug_dm, neoled, onewire, twd |

## D3. Signature-rate selectors over the whole map (model-independent)

All 1,713 elements of the heldout maps; 189 reference entries, 2 with no element of that exact name (recall by exact name can reach at most 0.989; the scorer also credits a record against one of its fields). A selector lists every element whose signature's reference rate is above a threshold. In-sample rates are fitted to the reference itself; leave-one-module-out rates come from the other modules only. In both, the best point at each recall is read off the curve of this set, so the values are optimistic. These are selectors of one form (signature rates); they do not bound a method that uses other information.

| level | signatures | in-sample P@R>=0.5 | P@R>=0.7 | P@R>=0.85 | leave-one-out P@R>=0.5 | P@R>=0.7 | P@R>=0.85 |
|---|---|---|---|---|---|---|---|
| L1 | 14 | 0.437 (R 0.783, 339 listed) | 0.437 (R 0.783, 339 listed) | 0.375 (R 0.868, 437 listed) | 0.437 (R 0.783, 339 listed) | 0.437 (R 0.783, 339 listed) | 0.374 (R 0.868, 439 listed) |
| L2 | 112 | 0.692 (R 0.571, 156 listed) | 0.652 (R 0.704, 204 listed) | 0.568 (R 0.862, 287 listed) | 0.566 (R 0.566, 189 listed) | 0.544 (R 0.72, 250 listed) | 0.425 (R 0.878, 391 listed) |
| L3 | 429 | 0.927 (R 0.534, 109 listed) | 0.822 (R 0.709, 163 listed) | 0.724 (R 0.862, 225 listed) | 0.561 (R 0.63, 212 listed) | 0.52 (R 0.704, 256 listed) | 0.406 (R 0.852, 397 listed) |

For comparison, the runs above: P 0.329 at R 0.931.

### D3b. A code filter on the model's own list

Each listed element gets its signature's hit rate among the listed elements; the filter keeps elements above a threshold. Leave-one-module-out rates come from the other modules' rows only. Recall counts the reference entries of all pooled runs (189).

| level | in-sample P@R>=0.7 | P@R>=0.85 | leave-one-out P@R>=0.7 | P@R>=0.85 |
|---|---|---|---|---|
| L1 | 0.629 (R 0.762, 229 listed) | 0.377 (R 0.921, 462 listed) | 0.615 (R 0.762, 234 listed) | 0.388 (R 0.852, 415 listed) |
| L2 | 0.714 (R 0.751, 199 listed) | 0.652 (R 0.862, 250 listed) | 0.61 (R 0.72, 223 listed) | 0.537 (R 0.852, 300 listed) |
| L3 | 0.842 (R 0.704, 158 listed) | 0.768 (R 0.857, 211 listed) | 0.597 (R 0.714, 226 listed) | 0.329 (R 0.931, 535 listed) |

### D3c. Learnt on tuning (assets_opt_v1_r0, assets_opt_v1_r1, assets_opt_v1_r2), applied here

The 'fixed' columns use the threshold that maximizes F1 on the training set, applied once. The other columns pick the best point on this set's curve, which uses this set's labels for the threshold (optimistic).

| level | own list, fixed threshold P / R / F1 (listed) | own list best P@R>=0.7 | own list best P@R>=0.85 | all map elements, fixed P / R / F1 | all map elements best P@R>=0.85 |
|---|---|---|---|---|---|
| L1 | 0.553 / 0.831 / 0.664 (284) | 0.622 (R 0.767, 233 listed) | 0.37 (R 0.915, 468 listed) | 0.255 / 0.958 / 0.403 | 0.27 (R 0.873, 612 listed) |
| L2 | 0.578 / 0.688 / 0.628 (225) | 0.591 (R 0.741, 237 listed) | 0.404 (R 0.852, 399 listed) | 0.516 / 0.508 / 0.512 | 0.322 (R 0.868, 509 listed) |
| L3 | 0.551 / 0.571 / 0.561 (196) | 0.565 (R 0.778, 260 listed) | 0.329 (R 0.931, 535 listed) | 0.473 / 0.37 / 0.415 | 0.109 (R 0.989, 1713 listed) |

Reference listing rate of the largest L2 signatures (all map elements):

| signature | elements | in the reference | rate |
|---|---|---|---|
| port-out, comb; no local use | 57 | 34 | 0.596 |
| port-in, not assigned here; used here | 42 | 26 | 0.619 |
| port-in, not assigned here; controls another element, used here | 38 | 20 | 0.526 |
| port-out, stored; no local use | 20 | 17 | 0.85 |
| port-in, not assigned here; no local use | 29 | 9 | 0.31 |
| signal field, stored; controls another element, carries data into an output, written from an input, used here | 19 | 8 | 0.421 |
| signal, stored; carries data into an output, written from an input, used here | 12 | 8 | 0.667 |
| signal, stored; controls another element, carries data into an output, written from an input, used here | 8 | 7 | 0.875 |
| signal, comb; controls another element, used here | 29 | 5 | 0.172 |
| signal, comb; controls another element, written from an input, used here | 10 | 4 | 0.4 |
| signal, comb; feeds a sub-unit, used here | 9 | 3 | 0.333 |
| port-in, not assigned here; feeds a sub-unit, used here | 7 | 3 | 0.429 |
| signal, stored; carries data into an output, used here | 6 | 3 | 0.5 |
| port-out, comb; written from an input | 4 | 3 | 0.75 |

## D4. Minimal pairs: same map evidence, opposite reference decision

**signal field, stored; controls another element, used here, is gated, is reset, CLOCKED_BY, GATED_BY, GATES, RESET_BY** (L3; 10 FP, 2 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | cpu_cp_shifter | `shifter.busy` | stores | 4 -> 88 | CLOCKED_BY clk_i | `shifter.busy <= '1';` | verified |
| FP | cpu_control | `trap_ctrl.env_entered` | stores | 4 -> 991 | CLOCKED_BY clk_i | `trap_ctrl.env_entered <= '1';` | verified |

Record types: TP CLOCKED_BY, GATED_BY, GATES, RESET_BY; FP CLOCKED_BY, GATED_BY, GATES, RESET_BY.

**port-in, not assigned here; controls another element, used here, GATES** (L3; 9 FP, 11 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | cpu_control | `alu_cp_done_i` | sets | 3 -> 505 | GATES exe_engine_nxt.state | `if (alu_cp_done_i = '1') or (trap_ctrl.exc_buf(exc_illegal_c) = '1') then` | verified |
| FP | cpu_counters | `re_i` | sets | 3 -> 345 | GATES rdata_o | `if (re_i = '1') and (CNT_WIDTH > 0) then` | verified |

Record types: TP GATES; FP GATES.

**signal, comb; controls another element, used here, is gated, GATED_BY, GATES** (L3; 8 FP, 1 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | cpu_counters | `cfg_we` | computes | 2 -> 85 | GATED_BY ctrl_i.csr_we | `cfg_we(i) <= cfg_acc and sel(i) and ctrl_i.csr_we;` | verified |
| FP | cpu_control | `csr_valid` | computes | 16 -> 742 | GATED_BY csr.prv_level_eff | `csr_valid(0) <= '0';` | verified |

Record types: TP GATED_BY, GATES; FP GATED_BY, GATES.

**port-in, not assigned here; used here, carries data inward, CARRIES** (L3; 7 FP, 12 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | cpu_cp_bitmanip | `rs1_i` | sets | 2 -> 189 | CARRIES rs1_reg | `rs1_reg  <= rs1_i;` | verified |
| FP | cpu_control | `lsu_mar_i` | sets | 2 -> 1239 | CARRIES csr.mtval | `csr.mtval <= lsu_mar_i;` | verified |

Record types: TP CARRIES; FP CARRIES.

**signal field, stored; controls another element, written from an input, used here, is gated, is reset, CLOCKED_BY, DERIVES_FROM, GATED_BY, GATES, RESET_BY** (L3; 6 FP, 1 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | onewire | `ctrl.clear` | stores | 4 -> 143 | CLOCKED_BY clk_i | `ctrl.clear    <= bus_req_i.data(ctrl_clear_c);` | verified |
| FP | debug_dm | `dm_reg.req_res` | stores | 6 -> 427 | CLOCKED_BY clk_i | `dm_reg.req_res            <= dmi_req_i.data(30);` | verified |

Record types: TP CLOCKED_BY, DERIVES_FROM, GATED_BY, GATES, RESET_BY; FP CLOCKED_BY, DERIVES_FROM, GATED_BY, GATES, RESET_BY.

**port-out, comb; COPIES** (L3; 5 FP, 17 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | cpu_alu | `cmp_o` | exit port | 2 -> 102 | COPIES cmp | `cmp_o            <= cmp;` | verified |
| FP | cpu_control | `csr_rdata_o` | exit port | 2 -> 1595 | COPIES csr.rdata | `csr_rdata_o <= csr.rdata;` | verified |

Record types: TP COPIES; FP COPIES.

## D5. Whole concepts the reference does not have

96 of 209 concepts (pooled over runs) contain no TP. They hold 239 FPs, 67% of all. The rest are extra elements inside concepts the reference does have.

## D6. Did the model follow the precision edits? (entries each edit would still remove)

| run | P | R | edit A removes FP / TP | edit B removes FP / TP |
|---|---|---|---|---|
| assets_opt_heldout_v1_r0 | 0.329 | 0.931 | 16 / 0 | 2 / 0 |

Edit A: a stored internal signal, whatever role it was given, is listed only when its records show a use (it controls another element, carries data into an output, or feeds a sub-unit), or it is a setting written from an input that a computation here reads. Edit B, as shipped: a register whose value-taking records name one other listed element and nothing else, not even itself, is a one-clock copy, unless that element is combinational and copies it or drives only it. For a run of a prompt without these edits the numbers show what they would remove; for a run with them, the FPs are entries the model kept against the edit.

## D7. Which families moved between versions (mean per run, FP / TP)

| family | Claude ist2 prompt held-out (1 runs) | Claude final held-out (1 runs) |
|---|---|---|
| internal state register | 104.0 / 7.0 | 99.0 / 7.0 |
| setting written from an input | 75.0 / 36.0 | 66.0 / 35.0 |
| combinational decision | 46.0 / 7.0 | 45.0 / 7.0 |
| data register | 42.0 / 3.0 | 37.0 / 3.0 |
| sub-unit interface signal | 35.0 / 5.0 | 38.0 / 6.0 |
| input port | 31.0 / 55.0 | 34.0 / 61.0 |
| combinational data | 26.0 / 2.0 | 21.0 / 2.0 |
| output port | 19.0 / 55.0 | 19.0 / 55.0 |

Read across a row: a family whose FPs fall while its TPs stay is one an edit moved.

