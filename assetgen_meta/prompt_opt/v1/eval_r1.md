# v1 run 1: P 0.366 R 0.946 F1 0.528 emitted 287 (15 modules, 111 reference entries)

missing outputs: []
citation statuses: {'verified': 305, 'map gap claimed': 11}
FP by kind: {'signal-field': 100, 'signal': 53, 'port-in': 14, 'port-out': 15}
FP by role: {'stores': 97, 'computes': 51, 'sets': 19, 'exit port': 15}
FN by kind: {'absent': 2, 'port-in': 2, 'signal': 1, 'signal-field': 1}
FN placement: {'nowhere in the output': 4, "mentioned in a concept's text only": 2}

| module | ref | TP | FP | FN | concepts |
|---|---|---|---|---|---|
| neorv32_bus | 11 | 11 | 9 | 0 | 13 |
| neorv32_cache | 6 | 4 | 23 | 2 | 11 |
| neorv32_cpu | 14 | 14 | 13 | 0 | 12 |
| neorv32_cpu_cp_cfu | 11 | 9 | 6 | 2 | 6 |
| neorv32_cpu_cp_muldiv | 12 | 12 | 4 | 0 | 5 |
| neorv32_cpu_pmp | 6 | 6 | 8 | 0 | 9 |
| neorv32_debug_dtm | 5 | 5 | 11 | 0 | 10 |
| neorv32_hwspinlock | 2 | 2 | 0 | 0 | 2 |
| neorv32_imem | 3 | 2 | 4 | 1 | 4 |
| neorv32_spi | 8 | 8 | 21 | 0 | 10 |
| neorv32_sys | 2 | 2 | 10 | 0 | 5 |
| neorv32_trng | 7 | 6 | 14 | 1 | 8 |
| neorv32_twi | 6 | 6 | 22 | 0 | 16 |
| neorv32_uart | 10 | 10 | 30 | 0 | 17 |
| neorv32_wdt | 8 | 8 | 7 | 0 | 9 |
