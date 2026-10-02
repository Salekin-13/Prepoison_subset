# Why precision does not improve: tuning_gpt5mini_ist2 (tuning, 3 runs)

Evidence comes from what the model reads and cites: the occurrence IDs and the relationship map of its input. Every count below is computed from the runs and the maps by `assetgen_meta/fp_diagnosis.py`; nothing is estimated. Precision (P) = share of listed elements that are in the reference; recall (R) = share of reference entries that were listed. TP = listed and in the reference; FP = listed and not in it.

Runs: assets_tuning18_m7e194es0ist2_r0 P 0.363 R 0.775 (TP 86, FP 151); assets_tuning18_m7e194es0ist2_r1 P 0.339 R 0.721 (TP 80, FP 156); assets_tuning18_m7e194es0ist2_r2 P 0.326 R 0.703 (TP 78, FP 161). Mean P 0.343, R 0.733.

## Answer

- **Citations.** 83% of FP citations are verified (the cited occurrence is the element's own and the cited edge exists there and fits the role), against 97% for TPs. Verified is a necessary condition: it shows the model read the RTL as the map records it, not that the element is an asset.
- **Shared signatures.** 57% of FPs have a behaviour signature (L2) that at least one TP in these runs also has; with the exact set of record types (L3), 24%. A rule stated on the signature cannot drop those FPs without dropping the TPs that share it.
- **Signature-rate selectors over the whole map** (all 1,641 elements; list a signature when its reference rate on the other modules is high enough; best of L1-L3, threshold read off this set's curve, so optimistic): precision 0.17 (R 0.856) at recall >= 0.85 and 0.248 (R 0.793) at recall >= 0.70. With the rates fitted to this set itself (in-sample): 0.655 (R 0.856) at recall >= 0.85. The runs: P 0.343 at R 0.733. 2 of 111 reference entries have no element of that exact name in the map.
- **A filter on the model's own list** (keep an element when its signature's hit rate among the other modules' listed elements is high enough; best of L1-L3, threshold read off this set's curve): precision unreachable at recall >= 0.85 and 0.364 (R 0.712) at recall >= 0.70.
- **Whole concepts.** 264 FPs (56%) sit in 124 of 298 concepts (per run) that contain no reference element.
- **The precision edits** (D6), re-applied as code filters over 3 run(s): edit A would still drop 16 FPs and 3 TPs, edit B 31 FPs and 0 TPs, both (A then B) 46 FPs and 3 TPs.

Reading (each line follows from the numbers above):
- Precision 0.85 at recall >= 0.85 is not reached by any selector or filter of these forms with rates learnt on other modules (best leave-one-module-out 0.170; the in-sample values in D3 and D3b are fitted to the labels they score).
- Recall 0.85 is out of reach for any filter on this list: the runs' recall is 0.733.
- Hypothesis, not measured here: the FPs that share a signature with TPs (57% at L2) are decided by conventions of the reference that the RTL structure does not record. D4 shows pairs; the fault reporter tests this per relationship type.

## D1. Are false positives misreadings? (citation status)

| label | listed | verified | statuses |
|---|---|---|---|
| TP | 244 | 97% | {'verified': 236, 'occurrence only': 2, 'edge, role unfit': 6} |
| FP | 468 | 83% | {'occurrence only': 38, 'verified': 390, 'edge, role unfit': 40} |

## D2. Do false positives look like hits? (signature shared with a TP)

| level | signatures | FP in a signature that also holds a TP | share | FP in signatures with no TP |
|---|---|---|---|---|
| L1 | 13 | 433 of 468 | 92% | 35 |
| L2 | 72 | 267 of 468 | 57% | 201 |
| L3 | 180 | 114 of 468 | 24% | 354 |

Largest behaviour signatures (L2), pooled over runs:

| signature | FP | TP | TP in modules | FP in modules |
|---|---|---|---|---|
| port-out, comb; no local use | 27 | 33 | cpu_cp_cfu, cpu_cp_muldiv, spi, sys, trng, twi | bus, cpu_cp_cfu, cpu_pmp, hwspinlock, spi, trng |
| signal field, comb; feeds a sub-unit, used here | 25 | 1 | trng | cache, spi, trng, twi, uart |
| port-in field, not assigned here; controls another element, used here | 20 | 1 | cpu_pmp | bus, cache, cpu_cp_muldiv, cpu_pmp, trng, uart |
| signal field, stored; carries data into an output, written from an input, used here | 19 | 3 | uart | spi, uart |
| signal, stored; controls another element, used here | 18 | 9 | bus, imem, wdt | bus, imem, spi, sys, wdt |
| signal field, stored; updates itself, controls another element, used here | 17 | 9 | bus, cpu_cp_muldiv, debug_dtm | cpu_cp_cfu, debug_dtm, spi, twi, uart |
| signal field, stored; carries data into an output, used here | 17 | 0 |  | cpu_cp_cfu, debug_dtm, twi, uart |
| signal field, stored; controls another element, carries data into an output, written from an input, used here | 15 | 30 | spi, twi, uart, wdt | spi, twi, uart, wdt |
| signal field, comb; written from an input, feeds a sub-unit, used here | 15 | 0 |  | cache, spi, twi, uart |
| port-in, not assigned here; no local use | 14 | 1 | cpu_pmp | bus, cpu_cp_muldiv, hwspinlock, imem, trng, twi |
| port-out field, comb; no local use | 13 | 0 |  | bus, cache, debug_dtm |
| signal field, not assigned here; carries data into an output, fed by a sub-unit, used here | 12 | 0 |  | cache, spi, trng, twi, uart |

## D3. Signature-rate selectors over the whole map (model-independent)

All 1,641 elements of the tuning maps; 111 reference entries, 2 with no element of that exact name (recall by exact name can reach at most 0.982; the scorer also credits a record against one of its fields). A selector lists every element whose signature's reference rate is above a threshold. In-sample rates are fitted to the reference itself; leave-one-module-out rates come from the other modules only. In both, the best point at each recall is read off the curve of this set, so the values are optimistic. These are selectors of one form (signature rates); they do not bound a method that uses other information.

| level | signatures | in-sample P@R>=0.5 | P@R>=0.7 | P@R>=0.85 | leave-one-out P@R>=0.5 | P@R>=0.7 | P@R>=0.85 |
|---|---|---|---|---|---|---|---|
| L1 | 14 | 0.238 (R 0.514, 239 listed) | 0.211 (R 0.748, 393 listed) | 0.198 (R 0.892, 499 listed) | 0.192 (R 0.838, 484 listed) | 0.192 (R 0.838, 484 listed) | 0.17 (R 0.856, 559 listed) |
| L2 | 95 | 0.431 (R 0.595, 153 listed) | 0.382 (R 0.703, 204 listed) | 0.332 (R 0.856, 286 listed) | 0.248 (R 0.793, 355 listed) | 0.248 (R 0.793, 355 listed) | 0.066 (R 0.982, 1641 listed) |
| L3 | 275 | 0.925 (R 0.559, 67 listed) | 0.81 (R 0.73, 100 listed) | 0.655 (R 0.856, 145 listed) | 0.245 (R 0.721, 326 listed) | 0.245 (R 0.721, 326 listed) | 0.066 (R 0.982, 1641 listed) |

For comparison, the runs above: P 0.343 at R 0.733.

### D3b. A code filter on the model's own list

Each listed element gets its signature's hit rate among the listed elements; the filter keeps elements above a threshold. Leave-one-module-out rates come from the other modules' rows only. Recall counts the reference entries of all pooled runs (333).

| level | in-sample P@R>=0.7 | P@R>=0.85 | leave-one-out P@R>=0.7 | P@R>=0.85 |
|---|---|---|---|---|
| L1 | 0.385 (R 0.712, 615 listed) | - | 0.364 (R 0.712, 651 listed) | - |
| L2 | 0.577 (R 0.709, 409 listed) | - | 0.343 (R 0.733, 712 listed) | - |
| L3 | 0.827 (R 0.706, 284 listed) | - | 0.343 (R 0.733, 712 listed) | - |

Reference listing rate of the largest L2 signatures (all map elements):

| signature | elements | in the reference | rate |
|---|---|---|---|
| port-in, not assigned here; used here | 58 | 15 | 0.259 |
| port-out, comb; no local use | 64 | 13 | 0.203 |
| signal field, stored; controls another element, carries data into an output, written from an input, used here | 15 | 10 | 0.667 |
| port-out, stored; no local use | 11 | 8 | 0.727 |
| port-in, not assigned here; controls another element, used here | 15 | 6 | 0.4 |
| signal field, comb; controls another element, used here | 22 | 5 | 0.227 |
| signal field, stored; updates itself, controls another element, used here | 18 | 4 | 0.222 |
| signal, not assigned here; feeds a sub-unit, fed by a sub-unit, used here | 11 | 4 | 0.364 |
| signal, stored; updates itself, controls another element, used here | 9 | 4 | 0.444 |
| port-in, not assigned here; no local use | 19 | 3 | 0.158 |
| signal, stored; controls another element, used here | 13 | 3 | 0.231 |
| signal, stored; carries data into an output, used here | 3 | 3 | 1.0 |
| signal, comb; controls another element, used here | 14 | 2 | 0.143 |
| port-in, not assigned here; feeds a sub-unit, used here | 10 | 2 | 0.2 |

## D4. Minimal pairs: same map evidence, opposite reference decision

**port-in field, not assigned here; controls another element, used here, GATES** (L3; 17 FP, 1 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | cpu_pmp | `ctrl_i.cpu_debug` | sets | 2 -> 363 | GATES fault_o | `fault_o <= (not ctrl_i.cpu_debug) and fail(0);` | verified |
| FP | bus | `req_i.addr` | sets | 2 -> 356 | GATES port_sel | `port_sel(0) <= '1' when A_EN and (req_i.addr(31 downto a_lo_c) = A_BASE(31 downto a_lo_c))` | verified |

Record types: TP GATES; FP GATES.

**port-in, not assigned here; no local use** (L3; 14 FP, 1 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | cpu_pmp | `ctrl_i` | sets | 6 -> 129 | SOURCES pmpcfg | `pmpcfg(i)(cfg_r_c) <= ctrl_i.csr_wdata((i mod 4)*8+cfg_r_c);` | verified |
| FP | cpu_cp_muldiv | `ctrl_i` | sets | 2 -> 97 | GATES valid_cmd | `valid_cmd <= '1' when (ctrl_i.alu_cp_alu = '1') and (ctrl_i.ir_opcode(5) = '1') and` | verified |

Record types: TP ; FP .

**signal field, stored; controls another element, carries data into an output, written from an input, used here, is gated, is reset, CARRIES, CLOCKED_BY, DERIVES_FROM, GATED_BY, GATES, RESET_BY** (L3; 9 FP, 3 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | wdt | `ctrl.enable` | stores | 3 -> 94 | CLOCKED_BY clk_i | `ctrl.enable  <= bus_req_i.data(ctrl_enable_c);` | verified |
| FP | spi | `ctrl.highspeed` | stores | 3 -> 145 | CLOCKED_BY clk_i | `ctrl.highspeed    <= bus_req_i.data(ctrl_highspeed_c);` | verified |

Record types: TP CARRIES, CLOCKED_BY, DERIVES_FROM, GATED_BY, GATES, RESET_BY; FP CARRIES, CLOCKED_BY, DERIVES_FROM, GATED_BY, GATES, RESET_BY.

**port-in field, not assigned here; used here, carries data inward, SOURCES** (L3; 9 FP, 1 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | cpu_pmp | `ctrl_i.cpu_priv` | sets | 2 -> 245 | SOURCES acc_priv | `acc_priv <= ctrl_i.cpu_priv when (ctrl_i.lsu_mo_we = '0') else ctrl_i.lsu_priv;` | verified |
| FP | spi | `bus_req_i.data` | sets | 2 -> 140 | SOURCES ctrl.enable | `ctrl.enable       <= bus_req_i.data(ctrl_en_c);` | verified |

Record types: TP SOURCES; FP SOURCES.

**signal field, comb; feeds a sub-unit, used here, is gated, GATED_BY** (L3; 8 FP, 1 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | trng | `fifo.re` | sets | 3 -> 171 | GATED_BY bus_req_i.stb | `fifo.re    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '0') and (bus_req_i.addr(` | verified |
| FP | spi | `tx_fifo.we` | sets | 3 -> 212 | GATED_BY bus_req_i.stb | `tx_fifo.we    <= '1' when (bus_req_i.stb = '1') and (bus_req_i.rw = '1') and (bus_req_i.ad` | verified |

Record types: TP GATED_BY; FP GATED_BY.

**port-out, comb; COPIES** (L3; 7 FP, 14 TP in these runs)

| | module | element | role | occurrence -> line | cited edge | RTL line | status |
|---|---|---|---|---|---|---|---|
| TP | trng | `data_o` | exit port | 2 -> 366 | COPIES sample_sreg | `data_o  <= sample_sreg;` | verified |
| FP | spi | `spi_clk_o` | exit port | 2 -> 344 | COPIES rtx_engine.sck | `spi_clk_o <= rtx_engine.sck;` | verified |

Record types: TP COPIES; FP COPIES.

## D5. Whole concepts the reference does not have

124 of 298 concepts (pooled over runs) contain no TP. They hold 264 FPs, 56% of all. The rest are extra elements inside concepts the reference does have.

## D6. Did the model follow the precision edits? (entries each edit would still remove)

| run | P | R | edit A removes FP / TP | edit B removes FP / TP |
|---|---|---|---|---|
| assets_tuning18_m7e194es0ist2_r0 | 0.363 | 0.775 | 2 / 1 | 10 / 0 |
| assets_tuning18_m7e194es0ist2_r1 | 0.339 | 0.721 | 6 / 1 | 11 / 0 |
| assets_tuning18_m7e194es0ist2_r2 | 0.326 | 0.703 | 8 / 1 | 10 / 0 |

Edit A: a stored internal signal, whatever role it was given, is listed only when its records show a use (it controls another element, carries data into an output, or feeds a sub-unit), or it is a setting written from an input that a computation here reads. Edit B, as shipped: a register whose value-taking records name one other listed element and nothing else, not even itself, is a one-clock copy, unless that element is combinational and copies it or drives only it. For a run of a prompt without these edits the numbers show what they would remove; for a run with them, the FPs are entries the model kept against the edit.

## D7. Which families moved between versions (mean per run, FP / TP)

| family | gpt-5-mini ist2 (3 runs) | Claude final (3 runs) | Claude ist2 prompt (2 runs) |
|---|---|---|---|
| internal state register | 34.3 / 11.0 | 48.3 / 15.0 | 54.5 / 15.0 |
| setting written from an input | 24.3 / 18.0 | 30.3 / 18.0 | 41.0 / 18.0 |
| sub-unit interface signal | 25.7 / 6.7 | 31.0 / 11.3 | 29.5 / 9.5 |
| combinational decision | 8.0 / 7.3 | 20.7 / 8.7 | 20.0 / 8.5 |
| output port | 17.0 / 18.0 | 14.3 / 21.0 | 14.0 / 21.0 |
| data register | 8.0 / 4.0 | 11.7 / 3.0 | 14.5 / 3.0 |
| input port | 11.7 / 13.3 | 13.3 / 24.0 | 13.0 / 21.5 |
| input port field | 11.0 / 0.7 | 0 / 0 | 0 / 0 |
| combinational data | 6.7 / 2.3 | 6.0 / 2.7 | 9.0 / 2.0 |
| output port field | 9.0 / 0.0 | 0 / 0 | 0 / 0 |
| signal not assigned here | 0.3 / 0.0 | 0 / 0 | 0 / 0 |

Read across a row: a family whose FPs fall while its TPs stay is one an edit moved.

