# neorv32_package

**Purpose (model):** Defines compile-time configuration constants, types and record formats (memory map, IO base addresses, CSR encodings, feature enables, default terminate constants), a neorv32_top component interface (generics and ports), and numerous utility functions (bit/byte helpers, reductions, mem initialization, string/print helpers) that other units use; the package itself contains no runtime ports or internal signals.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
| configure | Provide compile-time configuration and platform parameters (memory map bases and sizes, IO base addresses, CSR encodings, XLEN, feature/IO enables, clock-divider encodings, PMP/XBUS and other build-time parameters) used at elaboration/synthesis time by other units. |  | 63 / 63 |
| operate | Provide pure/impure utility functions that compute and return values when called (index_size_f, conditional selects, max/min, bool-to-ulogic, bitwise reductions, hex conversion, bit reversing, power-of-two test, byte-swap, popcount, leading-zero count, replicate, mem32_init_f, print_version_f, match_f). |  | 200 / 200 |
| report | Emit VHDL report messages on exceptional conditions inside utility routines (mem32_init_f warns on oversized init image; match_f reports an error when input and pattern lengths differ). |  | 4 / 4 |
