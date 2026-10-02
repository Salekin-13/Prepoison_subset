# v0 heldout run 0: P 0.310 R 0.899 F1 0.461 emitted 548 (26 modules, 189 reference entries)

missing outputs: []
citation statuses: {'verified': 624, 'map gap claimed': 11, 'occurrence only': 3}
FP by kind: {'signal': 80, 'port-in': 31, 'signal-field': 248, 'port-out': 19}
FP by role: {'computes': 93, 'stores': 226, 'sets': 40, 'exit port': 19}
FN by kind: {'port-in': 8, 'absent': 2, 'signal': 5, 'signal-field': 2, 'port-out': 2}
FN placement: {'nowhere in the output': 4, "mentioned in a concept's text only": 15}

| module | ref | TP | FP | FN | concepts |
|---|---|---|---|---|---|
| neorv32_cpu_alu | 11 | 10 | 7 | 1 | 8 |
| neorv32_cpu_control | 11 | 10 | 80 | 1 | 30 |
| neorv32_cpu_counters | 11 | 9 | 4 | 2 | 4 |
| neorv32_cpu_cp_bitmanip | 7 | 7 | 19 | 0 | 7 |
| neorv32_cpu_cp_cond | 6 | 6 | 1 | 0 | 3 |
| neorv32_cpu_cp_crypto | 6 | 6 | 12 | 0 | 8 |
| neorv32_cpu_cp_fpu | 12 | 11 | 55 | 1 | 10 |
| neorv32_cpu_cp_shifter | 11 | 10 | 3 | 1 | 5 |
| neorv32_cpu_decompressor | 3 | 3 | 1 | 0 | 2 |
| neorv32_cpu_frontend | 3 | 1 | 9 | 2 | 10 |
| neorv32_cpu_icc | 5 | 5 | 4 | 0 | 6 |
| neorv32_cpu_lsu | 10 | 10 | 3 | 0 | 12 |
| neorv32_cpu_regfile | 8 | 8 | 1 | 0 | 2 |
| neorv32_debug_auth | 5 | 4 | 1 | 1 | 1 |
| neorv32_debug_dm | 6 | 6 | 42 | 0 | 20 |
| neorv32_dmem | 3 | 2 | 4 | 1 | 3 |
| neorv32_gpio | 9 | 9 | 3 | 0 | 7 |
| neorv32_gptmr | 6 | 6 | 4 | 0 | 8 |
| neorv32_neoled | 6 | 6 | 16 | 0 | 11 |
| neorv32_onewire | 6 | 5 | 24 | 1 | 18 |
| neorv32_pwm | 9 | 7 | 9 | 2 | 11 |
| neorv32_sdi | 5 | 5 | 19 | 0 | 13 |
| neorv32_slink | 13 | 8 | 15 | 5 | 11 |
| neorv32_sysinfo | 1 | 1 | 2 | 0 | 4 |
| neorv32_twd | 7 | 6 | 35 | 1 | 18 |
| neorv32_xbus | 9 | 9 | 5 | 0 | 8 |
