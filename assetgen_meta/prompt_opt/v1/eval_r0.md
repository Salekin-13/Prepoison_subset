# v1 tuning run 0: P 0.378 R 0.937 F1 0.539 emitted 275 (15 modules, 111 reference entries)

missing outputs: []
citation statuses: {'verified': 295, 'map gap claimed': 11}
FP by kind: {'signal-field': 99, 'signal': 45, 'port-in': 13, 'port-out': 14}
FP by role: {'stores': 93, 'computes': 46, 'sets': 18, 'exit port': 14}
FN by kind: {'absent': 2, 'signal': 2, 'port-in': 2, 'signal-field': 1}
FN placement: {'nowhere in the output': 3, "mentioned in a concept's text only": 4}

| module | ref | TP | FP | FN | concepts |
|---|---|---|---|---|---|
| neorv32_bus | 11 | 11 | 8 | 0 | 15 |
| neorv32_cache | 6 | 4 | 23 | 2 | 11 |
| neorv32_cpu | 14 | 13 | 11 | 1 | 10 |
| neorv32_cpu_cp_cfu | 11 | 9 | 6 | 2 | 5 |
| neorv32_cpu_cp_muldiv | 12 | 12 | 4 | 0 | 7 |
| neorv32_cpu_pmp | 6 | 6 | 6 | 0 | 7 |
| neorv32_debug_dtm | 5 | 5 | 11 | 0 | 10 |
| neorv32_hwspinlock | 2 | 2 | 0 | 0 | 2 |
| neorv32_imem | 3 | 2 | 0 | 1 | 4 |
| neorv32_spi | 8 | 8 | 21 | 0 | 12 |
| neorv32_sys | 2 | 2 | 10 | 0 | 5 |
| neorv32_trng | 7 | 6 | 13 | 1 | 8 |
| neorv32_twi | 6 | 6 | 22 | 0 | 18 |
| neorv32_uart | 10 | 10 | 29 | 0 | 17 |
| neorv32_wdt | 8 | 8 | 7 | 0 | 9 |
