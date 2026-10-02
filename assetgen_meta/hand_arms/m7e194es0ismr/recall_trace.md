# Recall trace: m7e194es0ismr vs m7e194es0ism

Lost = found by m7e194es0ism in >=2 of 3 runs, missed by m7e194es0ismr in >=2 of 3. Map = `step1\lasset_step1\relation_exp\E3_pairfirst_declaration\relation_map\8406f390b729`. Occurrence IDs and lines come from the map's `occurrences`.

Lost 12, gained 3, missed by both 11, of 111 ground-truth assets.

## neorv32_bus / keeper.halt  (register, drives and receives; named in 3 of 3 ismr outputs)
- functionality: A register capturing the selected port bit: cleared on reset, sampled from port_sel on each rising clock edge, and evaluated in a condition that influences keeper.err and keeper.busy.
- GATES -> keeper.err at occurrence [4] = line [423]
- GATES -> keeper.busy at occurrence [4] = line [423]
- CLOCKED_BY -> clk_i at occurrence [3] = line [416]
- RESET_BY -> rstn_i at occurrence [2] = line [413]
- DERIVES_FROM -> port_sel at occurrence [3] = line [416]

## neorv32_bus / state  (register, drives and receives; named in 3 of 3 ismr outputs)
- functionality: Hold the current arbiter state and drive the case selector that controls FSM assignments and routing decisions.
- SELECTS -> sel, state_nxt, stb at occurrence [8] = line [83]
- SELECTS -> locked_nxt at occurrence [8] = line [83]
- GATES -> a_req at occurrence [4] = line [58]
- GATES -> b_req at occurrence [5] = line [63]
- RESET_BY -> rstn_i at occurrence [2] = line [49]
- COPIES -> state_nxt at occurrence [3] = line [55]

## neorv32_bus / state  (register, drives and receives; named in 3 of 3 ismr outputs)
- functionality: Hold the current arbiter state and drive the case selector that controls FSM assignments and routing decisions.
- SELECTS -> sel, state_nxt, stb at occurrence [8] = line [83]
- SELECTS -> locked_nxt at occurrence [8] = line [83]
- GATES -> a_req at occurrence [4] = line [58]
- GATES -> b_req at occurrence [5] = line [63]
- RESET_BY -> rstn_i at occurrence [2] = line [49]
- COPIES -> state_nxt at occurrence [3] = line [55]

## neorv32_cache / we_i  (port in, drives only; named in 3 of 3 ismr outputs)
- functionality: Byte-write enable vector; each bit gates a corresponding byte write into the data memory on the clock edge.
- GATES -> data_mem_b0 at occurrence [2] = line [413]
- GATES -> data_mem_b1 at occurrence [3] = line [416]
- GATES -> data_mem_b2 at occurrence [4] = line [419]
- GATES -> data_mem_b3 at occurrence [5] = line [422]

## neorv32_cpu / lsu_err  (signal, no relationships; named in 0 of 3 ismr outputs)
- functionality: Carries the LSU error vector output and is provided to the control unit through port connections.

## neorv32_cpu / dbi_i  (port in, no relationships; named in 0 of 3 ismr outputs)
- functionality: Debug interrupt input passed into the control instance as irq_dbg_i.

## neorv32_cpu / alu_res  (signal, drives only; named in 3 of 3 ismr outputs)
- functionality: Carries the result produced by the ALU instance and supplies that result as one of the sources for write-back data.
- SOURCES -> rf_wdata at occurrence [2] = line [330]

## neorv32_cpu / alu_add  (signal, no relationships; named in 1 of 3 ismr outputs)
- functionality: Conveys the address result from the ALU instance and is routed to control, the LSU and the PMP via port associations.

## neorv32_cpu / lsu_mar  (signal, no relationships; named in 0 of 3 ismr outputs)
- functionality: Holds the memory address register value output by the LSU and routed to control and other units via ports.

## neorv32_cpu / csr_rdata  (signal, drives only; named in 3 of 3 ismr outputs)
- functionality: Carries CSR read data from the control unit and contributes to the register file write-back data.
- SOURCES -> rf_wdata at occurrence [3] = line [330]

## neorv32_spi / spi_dat_o  (port out, receives only; named in 1 of 3 ismr outputs)
- functionality: Drives the SPI data output with the most-significant bit of the transmit shift register.
- DERIVES_FROM -> rtx_engine.sreg at occurrence [2] = line [343]

## neorv32_trng / fifo.re  (signal, receives only; named in 0 of 3 ismr outputs)
- functionality: Read-enable field driven by a concurrent when expression; it asserts on bus read requests that match the when condition.
- GATED_BY -> bus_req_i.addr, bus_req_i.rw, bus_req_i.stb at occurrence [3] = line [171]
