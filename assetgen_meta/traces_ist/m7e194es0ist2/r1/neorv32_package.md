# neorv32_package

**Purpose (model):** VHDL package that declares compile-time configuration constants (memory-map and I/O base addresses, XLEN, hw version, CSR and trap/IRQ identifiers, clock/divider and other configuration constants), record and type definitions (bus_req_t, bus_rsp_t, ctrl_bus_t, if_bus_t, etc.), default terminate constants, utility functions, and the neorv32_top component interface used by the CPU RTL.

## Use-case flows

| flow | value | path | lines (cited / in RTL) |
|---|---|---|---|
