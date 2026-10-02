# v0 run 0: P 0.326 R 0.856 F1 0.473 emitted 291 (15 modules, 111 reference entries)

missing outputs: []
citation statuses: {'verified': 312, 'map gap claimed': 12}
FP by kind: {'signal-field': 117, 'signal': 52, 'port-in': 13, 'port-out': 14}
FP by role: {'stores': 122, 'computes': 40, 'sets': 20, 'exit port': 14}
FN by kind: {'absent': 2, 'port-in': 7, 'signal': 5, 'signal-field': 2}
FN placement: {'nowhere in the output': 7, "mentioned in a concept's text only": 9}

| module | ref | TP | FP | FN | concepts |
|---|---|---|---|---|---|
| neorv32_bus | 11 | 11 | 10 | 0 | 13 |
| neorv32_cache | 6 | 4 | 31 | 2 | 10 |
| neorv32_cpu | 14 | 5 | 9 | 9 | 6 |
| neorv32_cpu_cp_cfu | 11 | 9 | 8 | 2 | 6 |
| neorv32_cpu_cp_muldiv | 12 | 11 | 9 | 1 | 6 |
| neorv32_cpu_pmp | 6 | 6 | 6 | 0 | 7 |
| neorv32_debug_dtm | 5 | 5 | 14 | 0 | 10 |
| neorv32_hwspinlock | 2 | 2 | 0 | 0 | 2 |
| neorv32_imem | 3 | 2 | 4 | 1 | 3 |
| neorv32_spi | 8 | 8 | 22 | 0 | 12 |
| neorv32_sys | 2 | 2 | 11 | 0 | 7 |
| neorv32_trng | 7 | 6 | 14 | 1 | 10 |
| neorv32_twi | 6 | 6 | 23 | 0 | 12 |
| neorv32_uart | 10 | 10 | 28 | 0 | 16 |
| neorv32_wdt | 8 | 8 | 7 | 0 | 10 |
