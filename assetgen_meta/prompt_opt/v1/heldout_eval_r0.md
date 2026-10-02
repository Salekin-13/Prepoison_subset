# v1 heldout run 0: P 0.329 R 0.931 F1 0.486 emitted 535 (26 modules, 189 reference entries)

missing outputs: []
citation statuses: {'verified': 594, 'map gap claimed': 25, 'occurrence only': 3}
FP by kind: {'signal': 67, 'port-in': 34, 'signal-field': 239, 'port-out': 19}
FP by role: {'computes': 97, 'stores': 200, 'sets': 43, 'exit port': 19}
FN by kind: {'absent': 2, 'signal': 4, 'port-in': 2, 'signal-field': 3, 'port-out': 2}
FN placement: {'nowhere in the output': 2, "mentioned in a concept's text only": 11}

| module | ref | TP | FP | FN | concepts |
|---|---|---|---|---|---|
| neorv32_cpu_alu | 11 | 11 | 9 | 0 | 7 |
| neorv32_cpu_control | 11 | 10 | 84 | 1 | 24 |
| neorv32_cpu_counters | 11 | 10 | 6 | 1 | 5 |
| neorv32_cpu_cp_bitmanip | 7 | 7 | 15 | 0 | 9 |
| neorv32_cpu_cp_cond | 6 | 6 | 1 | 0 | 3 |
| neorv32_cpu_cp_crypto | 6 | 6 | 6 | 0 | 6 |
| neorv32_cpu_cp_fpu | 12 | 11 | 52 | 1 | 12 |
| neorv32_cpu_cp_shifter | 11 | 9 | 3 | 2 | 5 |
| neorv32_cpu_decompressor | 3 | 3 | 1 | 0 | 2 |
| neorv32_cpu_frontend | 3 | 1 | 12 | 2 | 12 |
| neorv32_cpu_icc | 5 | 5 | 4 | 0 | 7 |
| neorv32_cpu_lsu | 10 | 10 | 3 | 0 | 9 |
| neorv32_cpu_regfile | 8 | 8 | 1 | 0 | 2 |
| neorv32_debug_auth | 5 | 4 | 1 | 1 | 1 |
| neorv32_debug_dm | 6 | 6 | 39 | 0 | 17 |
| neorv32_dmem | 3 | 2 | 0 | 1 | 4 |
| neorv32_gpio | 9 | 9 | 2 | 0 | 8 |
| neorv32_gptmr | 6 | 6 | 3 | 0 | 8 |
| neorv32_neoled | 6 | 6 | 17 | 0 | 11 |
| neorv32_onewire | 6 | 5 | 20 | 1 | 11 |
| neorv32_pwm | 9 | 7 | 9 | 2 | 5 |
| neorv32_sdi | 5 | 5 | 15 | 0 | 13 |
| neorv32_slink | 13 | 13 | 15 | 0 | 15 |
| neorv32_sysinfo | 1 | 1 | 2 | 0 | 4 |
| neorv32_twd | 7 | 6 | 34 | 1 | 16 |
| neorv32_xbus | 9 | 9 | 5 | 0 | 7 |
