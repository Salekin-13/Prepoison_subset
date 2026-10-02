# Fault report: tuning_gpt5mini_ist2 (tuning, gpt-5-mini ist2)

How the generator's false positives (FP: listed, not in the reference) relate to its hits (TP: listed and in the reference), seen through the relationship types the map records for each element and the occurrence the generator cited for it. All numbers are computed by `assetgen_meta/fault_reporter.py`. This is the code-only report: no LLM was run, so R5 and the synthesis are absent.

Runs: assets_tuning18_m7e194es0ist2_r0, assets_tuning18_m7e194es0ist2_r1, assets_tuning18_m7e194es0ist2_r2. Listed 712 (hits 244, FP 468), pooled over runs; 333 reference entries over these runs.

## Answer

- **Hits and FPs share their relationship types.** 21 of 21 relationship-class tokens occur on both. 19% of FPs have exactly the profile of some hit. In clusters of similar profiles (cut 0.35), 52% of FPs sit in clusters where hits are at least a fifth of the members (77% in clusters with any hit).
- **The profile predicts the reference's decision only weakly on a new module.** AUC for hit vs FP (0.5 = chance, 1 = perfect) from relationship classes: 0.75 in-sample, 0.615 leave one module out (logistic regression), 0.612 from the nearest profiles of other modules; with one row per element, 0.625 and 0.583. From exact record types: 0.813 in-sample, 0.641 leave one module out.
- **General rules cut FPs, but only at a cost and only part of them.** For 41 of 46 clusters with FPs (8 clusters hold hits only), a rule of the searched form drops some of the cluster's FPs and none of its hits; applied to every listed element, 9 of them drop hits elsewhere. All 41 together, on these elements (in-sample): 396 of 468 FPs and 108 of 244 hits dropped; P 0.343 -> 0.654, R 0.733 -> 0.408, F1 0.467 -> 0.503. For 5 clusters no rule of the searched form drops an FP without a hit; the largest of them by FP count are C9 (14 FP), C11 (14 FP), C27 (6 FP), C32 (5 FP), C45 (1 FP).

## R1. Relationship classes of hits and FPs

Share of hits and of FPs that have each token (pooled over runs).

| token | hits with it | share of hits | FPs with it | share of FPs |
|---|---|---|---|---|
| kind: signal | 148 | 61% | 322 | 69% |
| constant driver | 133 | 55% | 231 | 49% |
| record field | 76 | 31% | 270 | 58% |
| storage: stored | 120 | 49% | 215 | 46% |
| reset | 114 | 47% | 196 | 42% |
| controlled <- internal | 94 | 38% | 184 | 39% |
| control -> internal | 100 | 41% | 158 | 34% |
| data <- internal | 66 | 27% | 159 | 34% |
| controlled <- input port | 96 | 39% | 128 | 27% |
| storage: comb | 72 | 30% | 146 | 31% |
| data -> internal | 79 | 32% | 118 | 25% |
| data -> output port | 71 | 29% | 121 | 26% |
| data <- input port | 62 | 25% | 123 | 26% |
| storage: not assigned here | 52 | 21% | 107 | 23% |
| kind: port-out | 54 | 22% | 78 | 17% |
| kind: port-in | 42 | 17% | 68 | 14% |
| updates itself (data) | 16 | 7% | 57 | 12% |
| control -> output port | 32 | 13% | 38 | 8% |
| sub-unit port in | 14 | 6% | 49 | 10% |
| sub-unit port out | 13 | 5% | 34 | 7% |
| updates itself (control) | 15 | 6% | 15 | 3% |

## R2. Clusters of similar relationship profiles

| cut | clusters | FPs in clusters with any hit | share | FPs in clusters where hits are at least a fifth | share |
|---|---|---|---|---|---|
| 0.0 | 170 | 91 | 19% | 56 | 12% |
| 0.2 | 110 | 218 | 47% | 147 | 31% |
| 0.35 | 54 | 359 | 77% | 241 | 52% |
| 0.5 | 19 | 434 | 93% | 377 | 81% |

Exact record types instead of classes:

| cut | clusters | FPs in clusters with any hit | share |
|---|---|---|---|
| 0.0 | 203 | 72 | 15% |
| 0.2 | 146 | 176 | 38% |
| 0.35 | 75 | 317 | 68% |
| 0.5 | 33 | 411 | 88% |

Clusters at cut 0.35, most FPs first (listings pooled over runs):

| cluster | listings | hits | FPs | hit share | tokens in every member | hits in modules | FPs in modules | cited edges |
|---|---|---|---|---|---|---|---|---|
| C1 | 59 | 9 | 50 | 15% | constant driver; kind: signal; reset; storage: stored | bus, cpu_cp_muldiv, debug_dtm | cpu_cp_cfu, cpu_cp_muldiv, debug_dtm, spi, trng, twi, uart | {'CLOCKED_BY': 56, 'DERIVES_FROM': 1, 'COPIES': 1, 'CARRIES': 1} |
| C2 | 88 | 42 | 46 | 48% | data <- input port; kind: signal; storage: stored | cpu_cp_cfu, spi, trng, twi, uart, wdt | cpu_cp_cfu, cpu_cp_muldiv, spi, sys, trng, twi, uart, wdt | {'CLOCKED_BY': 79, 'DERIVES_FROM': 9} |
| C3 | 33 | 7 | 26 | 21% | constant driver; control -> internal; kind: signal; reset; storage: stored | bus, cpu_cp_muldiv, wdt | bus, debug_dtm, spi, twi, uart, wdt | {'CLOCKED_BY': 32, 'DERIVES_FROM': 1} |
| C4 | 35 | 13 | 22 | 37% | constant driver; control -> internal; kind: signal; reset; storage: stored | bus, cpu_cp_muldiv, debug_dtm, wdt | bus, debug_dtm, spi, trng, twi, wdt | {'CLOCKED_BY': 33, 'GATED_BY': 2} |
| C5 | 39 | 19 | 20 | 49% | data <- internal; kind: port-out; storage: comb | spi, trng, twi, uart, wdt | bus, cache, debug_dtm, spi, twi, wdt | {'DERIVES_FROM': 10, 'COPIES': 29} |
| C6 | 28 | 9 | 19 | 32% | control -> internal; kind: port-in; storage: not assigned here | cpu_cp_cfu, cpu_cp_muldiv | bus, cache, cpu_cp_muldiv, cpu_pmp, spi, twi, uart, wdt | {'GATES': 22, 'SOURCES': 6} |
| C7 | 17 | 0 | 17 | 0% | controlled <- input port; controlled <- internal; kind: signal; storage: stored |  | cache, imem | {'CLOCKED_BY': 17} |
| C8 | 19 | 3 | 16 | 16% | data <- internal; kind: signal; storage: comb; sub-unit port in | cpu | cpu, spi, twi, uart | {'DERIVES_FROM': 13, 'COPIES': 4, 'CONNECTS': 2} |
| C9 | 42 | 28 | 14 | 67% | data -> internal; kind: port-in; storage: not assigned here | cpu, cpu_cp_cfu, cpu_pmp, debug_dtm, spi, sys, uart | bus, cpu_pmp, debug_dtm, spi, trng, twi, wdt | {'GATED_BY': 1, 'SOURCES': 27, 'CARRIES': 14} |
| C10 | 17 | 3 | 14 | 18% | data <- input port; kind: signal; storage: comb | cpu | cache, spi, twi, uart | {'SELECTED_BY': 2, 'DERIVES_FROM': 11, 'CONNECTS': 4} |
| C11 | 15 | 1 | 14 | 7% | kind: port-in; storage: not assigned here | cpu_pmp | bus, cpu_cp_muldiv, hwspinlock, imem, trng, twi, uart, wdt | {'SOURCES': 10, 'GATES': 5} |
| C12 | 14 | 0 | 14 | 0% | kind: port-out; storage: comb |  | bus, cache | {'COPIES': 4, 'DERIVES_FROM': 10} |
| C13 | 16 | 3 | 13 | 19% | control -> internal; controlled <- input port; kind: signal; storage: comb | hwspinlock | bus, cpu_cp_muldiv, cpu_pmp | {'GATED_BY': 7, 'SELECTED_BY': 3, 'DERIVES_FROM': 6} |
| C14 | 16 | 4 | 12 | 25% | control -> output port; kind: port-in; storage: not assigned here | cpu_cp_cfu, cpu_pmp | cpu_cp_cfu, trng, uart | {'SELECTS': 3, 'GATES': 12, 'CARRIES': 1} |
| C15 | 15 | 3 | 12 | 20% | data -> output port; kind: signal; record field; storage: not assigned here; sub-unit port out | trng | cache, spi, trng, twi, uart | {'CONNECTS': 14, 'SOURCES': 1} |

## R3. Can relationship types predict hit vs FP?

| profile | rows | in-sample AUC | leave-one-module-out AUC (logistic) | leave-one-module-out AUC (15 nearest, ties included) |
|---|---|---|---|---|
| relationship classes | all runs pooled (712) | 0.75 | 0.615 | 0.612 |
| relationship classes | one row per element (351) | 0.759 | 0.625 | 0.583 |
| exact record types | all runs pooled (712) | 0.813 | 0.641 | 0.558 |
| exact record types | one row per element (351) | 0.808 | 0.656 | 0.55 |

Other run sets (relationship classes, all runs pooled):

| run set | listed | hits | FPs with exactly the profile of a hit | leave-one-module-out AUC |
|---|---|---|---|---|
| Claude final | 838 | 311 | 26% | 0.629 |
| Claude ist2 prompt | 588 | 197 | 24% | 0.67 |

## R4. Rules found by code inside each cluster, tested on every listed element

The searched form: drop an element that has every token all members of the cluster share, plus up to two more tokens, unless it has one 'unless' token. A rule is clean when it drops some of the cluster's FPs and none of its hits; the table shows the clean rule dropping the most FPs (ties: fewest hits lost on all listed elements). It is then applied, as is, to every listed element.

| cluster | tokens beyond the cluster's own | unless | FPs dropped in the cluster | all listed: FPs / hits dropped | all listed: P before -> after |
|---|---|---|---|---|---|
| C1 | data -> output port + record field | data -> internal | 24 of 50 | 54 / 24 | 0.343 -> 0.347 |
| C2 | record field | data -> output port | 9 of 46 | 20 / 0 | 0.343 -> 0.353 |
| C3 | controlled <- internal + data <- internal | data <- input port | 17 of 26 | 26 / 0 | 0.343 -> 0.356 |
| C4 | controlled <- internal | updates itself (control) | 15 of 22 | 44 / 19 | 0.343 -> 0.347 |
| C5 | record field | - | 8 of 20 | 10 / 0 | 0.343 -> 0.348 |
| C6 | record field | - | 15 of 19 | 23 / 0 | 0.343 -> 0.354 |
| C7 | (none) | - | 17 of 17 | 41 / 22 | 0.343 -> 0.342 |
| C8 | record field | - | 13 of 16 | 15 / 0 | 0.343 -> 0.35 |
| C9 | no clean rule of the searched form | - | 0 of 14 | - | - |
| C10 | record field | - | 14 of 14 | 16 / 0 | 0.343 -> 0.351 |
| C11 | no clean rule of the searched form | - | 0 of 14 | - | - |
| C12 | (none) | - | 14 of 14 | 55 / 33 | 0.343 -> 0.338 |
| C13 | (none) | data -> output port | 13 of 13 | 13 / 10 | 0.343 -> 0.34 |
| C14 | control -> internal + record field | - | 8 of 12 | 8 / 0 | 0.343 -> 0.347 |
| C15 | (none) | control -> output port | 12 of 12 | 12 / 0 | 0.343 -> 0.349 |

All 41 rules together on these elements (in-sample): 396 of 468 FPs and 108 of 244 hits dropped; P 0.343 -> 0.654, R 0.733 -> 0.408, F1 0.467 -> 0.503.
## R6. Fault ledger

`ledger.csv` lists every listed element with its cited occurrence, line, RTL text, edge, citation status, cluster and, for FPs, the cluster-level fault hypothesis. It traces each error to the evidence the generator used; the hypothesis is the LLM's, its citations are checked, its prose is not.

