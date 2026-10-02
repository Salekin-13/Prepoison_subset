# v1 tuning run 2: P 0.370 R 0.919 F1 0.527 emitted 276 (15 modules, 111 reference entries)

missing outputs: []
citation statuses: {'verified': 297, 'map gap claimed': 12}
FP by kind: {'signal-field': 97, 'signal': 50, 'port-in': 13, 'port-out': 14}
FP by role: {'stores': 95, 'computes': 50, 'sets': 15, 'exit port': 14}
FN by kind: {'absent': 2, 'signal': 3, 'port-in': 2, 'signal-field': 2}
FN placement: {'nowhere in the output': 4, "mentioned in a concept's text only": 5}

| module | ref | TP | FP | FN | concepts |
|---|---|---|---|---|---|
| neorv32_bus | 11 | 11 | 10 | 0 | 12 |
| neorv32_cache | 6 | 4 | 23 | 2 | 11 |
| neorv32_cpu | 14 | 13 | 11 | 1 | 9 |
| neorv32_cpu_cp_cfu | 11 | 9 | 6 | 2 | 7 |
| neorv32_cpu_cp_muldiv | 12 | 11 | 4 | 1 | 6 |
| neorv32_cpu_pmp | 6 | 6 | 9 | 0 | 7 |
| neorv32_debug_dtm | 5 | 5 | 11 | 0 | 9 |
| neorv32_hwspinlock | 2 | 1 | 0 | 1 | 1 |
| neorv32_imem | 3 | 2 | 0 | 1 | 4 |
| neorv32_spi | 8 | 8 | 22 | 0 | 14 |
| neorv32_sys | 2 | 2 | 10 | 0 | 5 |
| neorv32_trng | 7 | 6 | 13 | 1 | 8 |
| neorv32_twi | 6 | 6 | 21 | 0 | 14 |
| neorv32_uart | 10 | 10 | 26 | 0 | 16 |
| neorv32_wdt | 8 | 8 | 8 | 0 | 10 |
