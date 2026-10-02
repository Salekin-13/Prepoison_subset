# v0 run 1: P 0.343 R 0.919 F1 0.500 emitted 297 (15 modules, 111 reference entries)

missing outputs: []
citation statuses: {'verified': 320, 'map gap claimed': 12}
FP by kind: {'signal-field': 112, 'signal': 56, 'port-in': 13, 'port-out': 14}
FP by role: {'stores': 120, 'computes': 43, 'sets': 18, 'exit port': 14}
FN by kind: {'absent': 2, 'signal': 3, 'port-in': 2, 'signal-field': 2}
FN placement: {'nowhere in the output': 2, "mentioned in a concept's text only": 7}

| module | ref | TP | FP | FN | concepts |
|---|---|---|---|---|---|
| neorv32_bus | 11 | 11 | 11 | 0 | 12 |
| neorv32_cache | 6 | 4 | 25 | 2 | 12 |
| neorv32_cpu | 14 | 13 | 11 | 1 | 10 |
| neorv32_cpu_cp_cfu | 11 | 9 | 8 | 2 | 7 |
| neorv32_cpu_cp_muldiv | 12 | 11 | 9 | 1 | 7 |
| neorv32_cpu_pmp | 6 | 6 | 6 | 0 | 8 |
| neorv32_debug_dtm | 5 | 5 | 12 | 0 | 9 |
| neorv32_hwspinlock | 2 | 1 | 0 | 1 | 1 |
| neorv32_imem | 3 | 2 | 4 | 1 | 4 |
| neorv32_spi | 8 | 8 | 22 | 0 | 13 |
| neorv32_sys | 2 | 2 | 11 | 0 | 6 |
| neorv32_trng | 7 | 6 | 14 | 1 | 8 |
| neorv32_twi | 6 | 6 | 23 | 0 | 11 |
| neorv32_uart | 10 | 10 | 32 | 0 | 16 |
| neorv32_wdt | 8 | 8 | 7 | 0 | 9 |
