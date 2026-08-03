"""icl_examples_02.py -- variant of icl_examples_01 with a different AES example.

EXAMPLE 1 -- omsp_gpio        identical to icl_examples_01 (byte-for-byte)
EXAMPLE 2 -- aes_highthroughput_lowarea  replaces tiny_aes

WHY THE SWAP. Scored against the blocks of IEEE P3164 Figure 4 (Config Regs, Status Regs,
Key Reg, IV Reg, Input/Output Buffer), the reference asset lists map as:
    tiny_aes                        2/5 blocks   4 assets   (Key Reg, Buffers only)
    aes_highthroughput_lowarea      4/5 blocks  10 assets   (+ Config Regs, Status Regs)
    systemcaes                      4/5 blocks  10 assets
    aes (OpenTitan)                 4/5 blocks  84 assets   -- 37 files / 14,756 lines, too large
No AES in the benchmark set has an IV register, so 4/5 is the ceiling. This variant exists to
test whether the richer architectural match teaches better than tiny_aes's fully-sourced but
sparser one.

THE PROVENANCE DIFFERENCE -- READ THIS BEFORE COMPARING THE TWO VARIANTS.
  icl_examples_01 / tiny_aes : element list from the manual reference AND objective,
      functionality and justification from LAsset's own asset_list_tiny_aes_initial.json.
      Nothing about the labels was authored here.
  icl_examples_02 / this file: tiny_aes is the ONLY AES in the set that LAsset labelled.
      For aes_highthroughput_lowarea the element list is still the published manual reference
      (Dataset.xlsx, 'Crypto_asset' -> aes_highthroughput_lowarea_latest, Asset List
      (Manual), 10 entries), but the Security Objective, Functionality and Justification are
      DERIVED HERE by applying P3164's own per-block verdicts from 3.2.3. They are reasoned
      from the standard, not taken from LAsset.
  So a difference in downstream scores between 01 and 02 confounds two variables: the IP and
  the label provenance. Treat 02 as the architectural-fidelity arm, not as a clean ablation.

SOURCES
  RTL                    IPs/Crypto/aes_highthroughput_lowarea_latest/rtl/*.v, comment-
                         stripped -- the form the asset stage receives after
                         rtl_parse.strip_comments(). 8 of the 9 files, 1,247 of 1,394 lines:
                         aes_top_example.v is EXCLUDED. It is an integration wrapper, not part
                         of the core -- it adapts the wide key and data ports to a 32-bit bus,
                         which is exactly the inherited-fabric plumbing the NEORV32 targets
                         must learn NOT to nominate. Its entity is dropped from the closed set
                         as well, so the RTL shown and the closed set shown describe the same
                         design (asserted in the builder). It also carried ports named
                         i_data_valid, o_ready and o_data_valid that collide with three
                         genuine assets of entity `aes`; removing it removes that ambiguity.
  PARSED PORTS/SIGNALS   extracted from that RTL; `function` strings produced by running the
                         pipeline's own PARSE_PORTS_ANNOTATE_SYSTEM and
                         PARSE_SIGNALS_ANNOTATE_SYSTEM prompts over the raw commented source,
                         exactly as the notebook's parse stage does.
  EMITTED ELEMENTS       the 10 manual reference assets, all of which bind EXACTLY to the
                         parsed closed set (verified): i_key, i_data, rd_data, ende, enable,
                         key_start, key_ready, i_data_valid, o_ready, o_data_valid.
  OBJECTIVE / TEXT       derived here from P3164 3.2.3 (see the mapping below).

HOW P3164's CIA VERDICTS ATTACH TO THESE STRUCTURAL ELEMENTS
  P3164 (C) "the plaintext data and key values are secrets ... any block that supports these
            secrets will be a conceptual asset: Key Reg, Enc/Dec Engine, Input Buffer,
            Output Buffer"
        ->  i_key (aes)          the cipher key as presented to the core
        ->  rd_data (ram_16x64)  the expanded round keys read back from the key RAM; the RTL
                                 builds the applied round key as {rd_data0, rd_data1}
        ->  i_data (aes)         the plaintext block
  P3164 (I) "the key, IV, input data, and its configuration should not be modified ...
            Key Reg, IV Reg, Input Buffer, and Config Regs ... require integrity", with
            Table 1 listing "AES mode, operation, start/stop" as Configuration
        ->  ende (sbox)          encrypt/decrypt operation select
        ->  enable (sbox)        operation enable reaching the substitution stage
        ->  key_start (key_exp)  starts the key-schedule build
  P3164 (A) "Data_Out can be blocked ... thus making the Enc/Dec Engine a conceptual asset"
        ->  key_ready (key_exp), o_ready (aes), o_data_valid (aes), i_data_valid (aes)
            -- reached by a different route: this core has no debug interface, so the way
            service can be denied is the handshake a consumer waits on.
  P3164 (U) answered YES for its AES via the debug interface substituting a test key/IV.
            Answered NO here: no debug mode and no Debug Values block exist in this design.
            This is the one verdict that differs, and it differs structurally.

RESULTING OBJECTIVE MIX: 3 Confidentiality + 3 Integrity + 4 Availability, so this example
alone exercises all three objectives (icl_examples_01 needed both examples to do that).

KNOWN LIMITATIONS
  * The objectives are reasoned from P3164 rather than taken from a published label set --
    see the provenance note above. They are defensible but they are this file's judgement.
  * P3164's "Output Buffer" is a Confidentiality asset in the standard, and o_data exists in
    this design, but it is absent from the manual reference list, so it is not emitted.
  * 10 assets from a 221-element closed set is 4.5%; NEORV32 ground truth sits near 7%.
  * The RTL is Verilog while the NEORV32 targets are VHDL, as in icl_examples_01.
"""

EXAMPLE_01_OMSP_GPIO = """\
### CASE STUDY 1: omsp_gpio (openMSP430 digital I/O interface)

TARGET IP MODULE: omsp_gpio

=== TECHNICAL SUMMARY ===
MODULE: omsp_gpio
1. FUNCTION AND ROLE
Digital I/O interface managing up to six GPIO ports for an openMSP430-class system. Each
port provides configurable input/output operation with per-bit direction control, an
alternate-function multiplexer, and edge-triggered interrupt generation. The module is a
memory-mapped peripheral: a higher-level system configures it over a peripheral address and
data bus, and the module drives the pad-side output, output-enable and function-select
buses. It operates standalone, instantiating only omsp_sync_cell to synchronize pad inputs
into the mclk domain.
2. REGISTERS, CSRS, AND FLAGS
- P1DIR..P6DIR — r/w — 0x00 — per-bit direction (input/output) for each port; drives the port output enable
- P1SEL..P6SEL — r/w — 0x00 — per-bit GPIO vs. alternate-function selection for each port
- P1OUT..P6OUT — r/w — 0x00 — per-bit output data driven onto the pads
- P1IN..P6IN — r/- — not stated — synchronized pad input data
- P1IE, P2IE — r/w — 0x00 — per-bit interrupt enable
- P1IES, P2IES — r/w — 0x00 — per-bit interrupt edge select (rising or falling)
- P1IFG, P2IFG — r/w — 0x00 — per-bit interrupt flag, set by the selected edge
3. CONFIGURATION
- P1_EN..P6_EN — build-time — enable or remove each port; ports 1 and 2 default enabled, 3 to 6 disabled
- DEC_WD — build-time — decoder bit width for register address decoding (value 6)
4. CROSS-MODULE INTERACTION
The module is reached exclusively through the peripheral bus: per_addr selects a register,
per_en qualifies the access, per_we selects which byte of the addressed register is written,
per_din carries write data and per_dout returns read data. Any bus master able to issue
transactions in this address window can therefore reprogram direction, function select,
output data and interrupt configuration; no privilege level, lock bit or authentication on
that access is documented. On the pad side the module drives p1_dout_en..p6_dout_en and
p1_sel..p6_sel, which determine whether each pin drives or floats and whether it is owned by
GPIO or by an alternate on-chip function. irq_port1 and irq_port2 are raised to the
processor's interrupt inputs.
5. SECURITY-RELEVANT BEHAVIOR
No access-control, protection, or privileged mechanisms are documented for this module. No
keys, entropy, passwords or boot images are handled; the payload is ordinary I/O data. The
security-relevant state is configuration state: the direction registers decide whether a pin
drives the external world or tri-states, and the function-select registers decide which
on-chip block owns the pin. Both are freely writable over the peripheral bus and persist
until rewritten. Interrupt generation depends on edge detection against a delayed copy of
the synchronized input, gated by the per-bit enable and edge-select registers.

=== PARSED I/O PORTS (JSON) ===
[
 {
  "entity": "omsp_gpio",
  "name": "irq_port1",
  "dir": "output",
  "type": "wire",
  "function": "Port 1 interrupt"
 },
 {
  "entity": "omsp_gpio",
  "name": "irq_port2",
  "dir": "output",
  "type": "wire",
  "function": "Port 2 interrupt"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1_dout",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 1 data output"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1_dout_en",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 1 data output enable"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1_sel",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 1 function select"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2_dout",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 2 data output"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2_dout_en",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 2 data output enable"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2_sel",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 2 function select"
 },
 {
  "entity": "omsp_gpio",
  "name": "p3_dout",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 3 data output"
 },
 {
  "entity": "omsp_gpio",
  "name": "p3_dout_en",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 3 data output enable"
 },
 {
  "entity": "omsp_gpio",
  "name": "p3_sel",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 3 function select"
 },
 {
  "entity": "omsp_gpio",
  "name": "p4_dout",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 4 data output"
 },
 {
  "entity": "omsp_gpio",
  "name": "p4_dout_en",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 4 data output enable"
 },
 {
  "entity": "omsp_gpio",
  "name": "p4_sel",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 4 function select"
 },
 {
  "entity": "omsp_gpio",
  "name": "p5_dout",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 5 data output"
 },
 {
  "entity": "omsp_gpio",
  "name": "p5_dout_en",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 5 data output enable"
 },
 {
  "entity": "omsp_gpio",
  "name": "p5_sel",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 5 function select"
 },
 {
  "entity": "omsp_gpio",
  "name": "p6_dout",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 6 data output"
 },
 {
  "entity": "omsp_gpio",
  "name": "p6_dout_en",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 6 data output enable"
 },
 {
  "entity": "omsp_gpio",
  "name": "p6_sel",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Port 6 function select"
 },
 {
  "entity": "omsp_gpio",
  "name": "per_dout",
  "dir": "output",
  "type": "wire[15:0]",
  "function": "Peripheral data output"
 },
 {
  "entity": "omsp_gpio",
  "name": "mclk",
  "dir": "input",
  "type": "wire",
  "function": "Main system clock"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1_din",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Port 1 data input"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2_din",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Port 2 data input"
 },
 {
  "entity": "omsp_gpio",
  "name": "p3_din",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Port 3 data input"
 },
 {
  "entity": "omsp_gpio",
  "name": "p4_din",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Port 4 data input"
 },
 {
  "entity": "omsp_gpio",
  "name": "p5_din",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Port 5 data input"
 },
 {
  "entity": "omsp_gpio",
  "name": "p6_din",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Port 6 data input"
 },
 {
  "entity": "omsp_gpio",
  "name": "per_addr",
  "dir": "input",
  "type": "wire[13:0]",
  "function": "Peripheral address"
 },
 {
  "entity": "omsp_gpio",
  "name": "per_din",
  "dir": "input",
  "type": "wire[15:0]",
  "function": "Peripheral data input"
 },
 {
  "entity": "omsp_gpio",
  "name": "per_en",
  "dir": "input",
  "type": "wire",
  "function": "Peripheral enable (active high)"
 },
 {
  "entity": "omsp_gpio",
  "name": "per_we",
  "dir": "input",
  "type": "wire[1:0]",
  "function": "Peripheral write enable (active high)"
 },
 {
  "entity": "omsp_gpio",
  "name": "puc_rst",
  "dir": "input",
  "type": "wire",
  "function": "Main system reset"
 }
]

=== PARSED INTERNAL SIGNALS (JSON) ===
[
 {
  "entity": "omsp_gpio",
  "name": "p1in",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Synchronization of Port 1 input data"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1out",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 1 output data register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1dir",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 1 direction register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1ifg",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 1 interrupt flag register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1ifg_set",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Port 1 interrupt flag set"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1ies",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 1 interrupt edge select"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1ie",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 1 interrupt enable"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1sel",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 1 select register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2in",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Synchronization of Port 2 input data"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2out",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 2 output data register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2dir",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 2 direction register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2ifg",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 2 interrupt flag register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2ifg_set",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Port 2 interrupt flag set"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2ies",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 2 interrupt edge select"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2ie",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 2 interrupt enable"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2sel",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 2 select register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p3in",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Synchronization of Port 3 input data"
 },
 {
  "entity": "omsp_gpio",
  "name": "p3out",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 3 output data register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p3dir",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 3 direction register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p3sel",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 3 select register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p4in",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Synchronization of Port 4 input data"
 },
 {
  "entity": "omsp_gpio",
  "name": "p4out",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 4 output data register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p4dir",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 4 direction register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p4sel",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 4 select register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p5in",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Synchronization of Port 5 input data"
 },
 {
  "entity": "omsp_gpio",
  "name": "p5out",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 5 output data register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p5dir",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 5 direction register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p5sel",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 5 select register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p6in",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Synchronization of Port 6 input data"
 },
 {
  "entity": "omsp_gpio",
  "name": "p6out",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 6 output data register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p6dir",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 6 direction register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p6sel",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Port 6 select register"
 },
 {
  "entity": "omsp_gpio",
  "name": "p1in_dly",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Previous state of Port 1 input for edge detection"
 },
 {
  "entity": "omsp_gpio",
  "name": "p2in_dly",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "Previous state of Port 2 input for edge detection"
 }
]

=== RTL ===
module  omsp_gpio (
    irq_port1,
    irq_port2,
    p1_dout,
    p1_dout_en,
    p1_sel,
    p2_dout,
    p2_dout_en,
    p2_sel,
    p3_dout,
    p3_dout_en,
    p3_sel,
    p4_dout,
    p4_dout_en,
    p4_sel,
    p5_dout,
    p5_dout_en,
    p5_sel,
    p6_dout,
    p6_dout_en,
    p6_sel,
    per_dout,
    mclk,
    p1_din,
    p2_din,
    p3_din,
    p4_din,
    p5_din,
    p6_din,
    per_addr,
    per_din,
    per_en,
    per_we,
    puc_rst
);
parameter           P1_EN = 1'b1;
parameter           P2_EN = 1'b1;
parameter           P3_EN = 1'b0;
parameter           P4_EN = 1'b0;
parameter           P5_EN = 1'b0;
parameter           P6_EN = 1'b0;
output              irq_port1;
output              irq_port2;
output        [7:0] p1_dout;
output        [7:0] p1_dout_en;
output        [7:0] p1_sel;
output        [7:0] p2_dout;
output        [7:0] p2_dout_en;
output        [7:0] p2_sel;
output        [7:0] p3_dout;
output        [7:0] p3_dout_en;
output        [7:0] p3_sel;
output        [7:0] p4_dout;
output        [7:0] p4_dout_en;
output        [7:0] p4_sel;
output        [7:0] p5_dout;
output        [7:0] p5_dout_en;
output        [7:0] p5_sel;
output        [7:0] p6_dout;
output        [7:0] p6_dout_en;
output        [7:0] p6_sel;
output       [15:0] per_dout;
input               mclk;
input         [7:0] p1_din;
input         [7:0] p2_din;
input         [7:0] p3_din;
input         [7:0] p4_din;
input         [7:0] p5_din;
input         [7:0] p6_din;
input        [13:0] per_addr;
input        [15:0] per_din;
input               per_en;
input         [1:0] per_we;
input               puc_rst;
parameter              P1_EN_MSK   = {8{P1_EN[0]}};
parameter              P2_EN_MSK   = {8{P2_EN[0]}};
parameter              P3_EN_MSK   = {8{P3_EN[0]}};
parameter              P4_EN_MSK   = {8{P4_EN[0]}};
parameter              P5_EN_MSK   = {8{P5_EN[0]}};
parameter              P6_EN_MSK   = {8{P6_EN[0]}};
parameter       [14:0] BASE_ADDR   = 15'h0000;
parameter              DEC_WD      =  6;
parameter [DEC_WD-1:0] P1IN        = 'h20,
                       P1OUT       = 'h21,
                       P1DIR       = 'h22,
                       P1IFG       = 'h23,
                       P1IES       = 'h24,
                       P1IE        = 'h25,
                       P1SEL       = 'h26,
                       P2IN        = 'h28,
                       P2OUT       = 'h29,
                       P2DIR       = 'h2A,
                       P2IFG       = 'h2B,
                       P2IES       = 'h2C,
                       P2IE        = 'h2D,
                       P2SEL       = 'h2E,
                       P3IN        = 'h18,
                       P3OUT       = 'h19,
                       P3DIR       = 'h1A,
                       P3SEL       = 'h1B,
                       P4IN        = 'h1C,
                       P4OUT       = 'h1D,
                       P4DIR       = 'h1E,
                       P4SEL       = 'h1F,
                       P5IN        = 'h30,
                       P5OUT       = 'h31,
                       P5DIR       = 'h32,
                       P5SEL       = 'h33,
                       P6IN        = 'h34,
                       P6OUT       = 'h35,
                       P6DIR       = 'h36,
                       P6SEL       = 'h37;
parameter              DEC_SZ      =  (1 << DEC_WD);
parameter [DEC_SZ-1:0] BASE_REG    =  {{DEC_SZ-1{1'b0}}, 1'b1};
parameter [DEC_SZ-1:0] P1IN_D      =  (BASE_REG << P1IN),
                       P1OUT_D     =  (BASE_REG << P1OUT),
                       P1DIR_D     =  (BASE_REG << P1DIR),
                       P1IFG_D     =  (BASE_REG << P1IFG),
                       P1IES_D     =  (BASE_REG << P1IES),
                       P1IE_D      =  (BASE_REG << P1IE),
                       P1SEL_D     =  (BASE_REG << P1SEL),
                       P2IN_D      =  (BASE_REG << P2IN),
                       P2OUT_D     =  (BASE_REG << P2OUT),
                       P2DIR_D     =  (BASE_REG << P2DIR),
                       P2IFG_D     =  (BASE_REG << P2IFG),
                       P2IES_D     =  (BASE_REG << P2IES),
                       P2IE_D      =  (BASE_REG << P2IE),
                       P2SEL_D     =  (BASE_REG << P2SEL),
                       P3IN_D      =  (BASE_REG << P3IN),
                       P3OUT_D     =  (BASE_REG << P3OUT),
                       P3DIR_D     =  (BASE_REG << P3DIR),
                       P3SEL_D     =  (BASE_REG << P3SEL),
                       P4IN_D      =  (BASE_REG << P4IN),
                       P4OUT_D     =  (BASE_REG << P4OUT),
                       P4DIR_D     =  (BASE_REG << P4DIR),
                       P4SEL_D     =  (BASE_REG << P4SEL),
                       P5IN_D      =  (BASE_REG << P5IN),
                       P5OUT_D     =  (BASE_REG << P5OUT),
                       P5DIR_D     =  (BASE_REG << P5DIR),
                       P5SEL_D     =  (BASE_REG << P5SEL),
                       P6IN_D      =  (BASE_REG << P6IN),
                       P6OUT_D     =  (BASE_REG << P6OUT),
                       P6DIR_D     =  (BASE_REG << P6DIR),
                       P6SEL_D     =  (BASE_REG << P6SEL);
wire              reg_sel      =  per_en & (per_addr[13:DEC_WD-1]==BASE_ADDR[14:DEC_WD]);
wire [DEC_WD-1:0] reg_addr     =  {1'b0, per_addr[DEC_WD-2:0]};
wire [DEC_SZ-1:0] reg_dec      =  (P1IN_D   &  {DEC_SZ{(reg_addr==(P1IN  >>1))  &  P1_EN[0]}})  |
                                  (P1OUT_D  &  {DEC_SZ{(reg_addr==(P1OUT >>1))  &  P1_EN[0]}})  |
                                  (P1DIR_D  &  {DEC_SZ{(reg_addr==(P1DIR >>1))  &  P1_EN[0]}})  |
                                  (P1IFG_D  &  {DEC_SZ{(reg_addr==(P1IFG >>1))  &  P1_EN[0]}})  |
                                  (P1IES_D  &  {DEC_SZ{(reg_addr==(P1IES >>1))  &  P1_EN[0]}})  |
                                  (P1IE_D   &  {DEC_SZ{(reg_addr==(P1IE  >>1))  &  P1_EN[0]}})  |
                                  (P1SEL_D  &  {DEC_SZ{(reg_addr==(P1SEL >>1))  &  P1_EN[0]}})  |
                                  (P2IN_D   &  {DEC_SZ{(reg_addr==(P2IN  >>1))  &  P2_EN[0]}})  |
                                  (P2OUT_D  &  {DEC_SZ{(reg_addr==(P2OUT >>1))  &  P2_EN[0]}})  |
                                  (P2DIR_D  &  {DEC_SZ{(reg_addr==(P2DIR >>1))  &  P2_EN[0]}})  |
                                  (P2IFG_D  &  {DEC_SZ{(reg_addr==(P2IFG >>1))  &  P2_EN[0]}})  |
                                  (P2IES_D  &  {DEC_SZ{(reg_addr==(P2IES >>1))  &  P2_EN[0]}})  |
                                  (P2IE_D   &  {DEC_SZ{(reg_addr==(P2IE  >>1))  &  P2_EN[0]}})  |
                                  (P2SEL_D  &  {DEC_SZ{(reg_addr==(P2SEL >>1))  &  P2_EN[0]}})  |
                                  (P3IN_D   &  {DEC_SZ{(reg_addr==(P3IN  >>1))  &  P3_EN[0]}})  |
                                  (P3OUT_D  &  {DEC_SZ{(reg_addr==(P3OUT >>1))  &  P3_EN[0]}})  |
                                  (P3DIR_D  &  {DEC_SZ{(reg_addr==(P3DIR >>1))  &  P3_EN[0]}})  |
                                  (P3SEL_D  &  {DEC_SZ{(reg_addr==(P3SEL >>1))  &  P3_EN[0]}})  |
                                  (P4IN_D   &  {DEC_SZ{(reg_addr==(P4IN  >>1))  &  P4_EN[0]}})  |
                                  (P4OUT_D  &  {DEC_SZ{(reg_addr==(P4OUT >>1))  &  P4_EN[0]}})  |
                                  (P4DIR_D  &  {DEC_SZ{(reg_addr==(P4DIR >>1))  &  P4_EN[0]}})  |
                                  (P4SEL_D  &  {DEC_SZ{(reg_addr==(P4SEL >>1))  &  P4_EN[0]}})  |
                                  (P5IN_D   &  {DEC_SZ{(reg_addr==(P5IN  >>1))  &  P5_EN[0]}})  |
                                  (P5OUT_D  &  {DEC_SZ{(reg_addr==(P5OUT >>1))  &  P5_EN[0]}})  |
                                  (P5DIR_D  &  {DEC_SZ{(reg_addr==(P5DIR >>1))  &  P5_EN[0]}})  |
                                  (P5SEL_D  &  {DEC_SZ{(reg_addr==(P5SEL >>1))  &  P5_EN[0]}})  |
                                  (P6IN_D   &  {DEC_SZ{(reg_addr==(P6IN  >>1))  &  P6_EN[0]}})  |
                                  (P6OUT_D  &  {DEC_SZ{(reg_addr==(P6OUT >>1))  &  P6_EN[0]}})  |
                                  (P6DIR_D  &  {DEC_SZ{(reg_addr==(P6DIR >>1))  &  P6_EN[0]}})  |
                                  (P6SEL_D  &  {DEC_SZ{(reg_addr==(P6SEL >>1))  &  P6_EN[0]}});
wire              reg_lo_write =  per_we[0] & reg_sel;
wire              reg_hi_write =  per_we[1] & reg_sel;
wire              reg_read     = ~|per_we   & reg_sel;
wire [DEC_SZ-1:0] reg_hi_wr    = reg_dec & {DEC_SZ{reg_hi_write}};
wire [DEC_SZ-1:0] reg_lo_wr    = reg_dec & {DEC_SZ{reg_lo_write}};
wire [DEC_SZ-1:0] reg_rd       = reg_dec & {DEC_SZ{reg_read}};
wire [7:0] p1in;
omsp_sync_cell sync_cell_p1in_0 (.data_out(p1in[0]), .data_in(p1_din[0] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_1 (.data_out(p1in[1]), .data_in(p1_din[1] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_2 (.data_out(p1in[2]), .data_in(p1_din[2] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_3 (.data_out(p1in[3]), .data_in(p1_din[3] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_4 (.data_out(p1in[4]), .data_in(p1_din[4] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_5 (.data_out(p1in[5]), .data_in(p1_din[5] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_6 (.data_out(p1in[6]), .data_in(p1_din[6] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_7 (.data_out(p1in[7]), .data_in(p1_din[7] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p1out;
wire       p1out_wr  = P1OUT[0] ? reg_hi_wr[P1OUT] : reg_lo_wr[P1OUT];
wire [7:0] p1out_nxt = P1OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p1out <=  8'h00;
  else if (p1out_wr)  p1out <=  p1out_nxt & P1_EN_MSK;
assign p1_dout = p1out;
reg  [7:0] p1dir;
wire       p1dir_wr  = P1DIR[0] ? reg_hi_wr[P1DIR] : reg_lo_wr[P1DIR];
wire [7:0] p1dir_nxt = P1DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p1dir <=  8'h00;
  else if (p1dir_wr)  p1dir <=  p1dir_nxt & P1_EN_MSK;
assign p1_dout_en = p1dir;
reg  [7:0] p1ifg;
wire       p1ifg_wr  = P1IFG[0] ? reg_hi_wr[P1IFG] : reg_lo_wr[P1IFG];
wire [7:0] p1ifg_nxt = P1IFG[0] ? per_din[15:8]    : per_din[7:0];
wire [7:0] p1ifg_set;
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p1ifg <=  8'h00;
  else if (p1ifg_wr)  p1ifg <=  (p1ifg_nxt | p1ifg_set) & P1_EN_MSK;
  else                p1ifg <=  (p1ifg     | p1ifg_set) & P1_EN_MSK;
reg  [7:0] p1ies;
wire       p1ies_wr  = P1IES[0] ? reg_hi_wr[P1IES] : reg_lo_wr[P1IES];
wire [7:0] p1ies_nxt = P1IES[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p1ies <=  8'h00;
  else if (p1ies_wr)  p1ies <=  p1ies_nxt & P1_EN_MSK;
reg  [7:0] p1ie;
wire       p1ie_wr  = P1IE[0] ? reg_hi_wr[P1IE] : reg_lo_wr[P1IE];
wire [7:0] p1ie_nxt = P1IE[0] ? per_din[15:8]   : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p1ie <=  8'h00;
  else if (p1ie_wr)  p1ie <=  p1ie_nxt & P1_EN_MSK;
reg  [7:0] p1sel;
wire       p1sel_wr  = P1SEL[0] ? reg_hi_wr[P1SEL] : reg_lo_wr[P1SEL];
wire [7:0] p1sel_nxt = P1SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p1sel <=  8'h00;
  else if (p1sel_wr) p1sel <=  p1sel_nxt & P1_EN_MSK;
assign p1_sel = p1sel;
wire [7:0] p2in;
omsp_sync_cell sync_cell_p2in_0 (.data_out(p2in[0]), .data_in(p2_din[0] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_1 (.data_out(p2in[1]), .data_in(p2_din[1] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_2 (.data_out(p2in[2]), .data_in(p2_din[2] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_3 (.data_out(p2in[3]), .data_in(p2_din[3] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_4 (.data_out(p2in[4]), .data_in(p2_din[4] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_5 (.data_out(p2in[5]), .data_in(p2_din[5] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_6 (.data_out(p2in[6]), .data_in(p2_din[6] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_7 (.data_out(p2in[7]), .data_in(p2_din[7] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p2out;
wire       p2out_wr  = P2OUT[0] ? reg_hi_wr[P2OUT] : reg_lo_wr[P2OUT];
wire [7:0] p2out_nxt = P2OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p2out <=  8'h00;
  else if (p2out_wr)  p2out <=  p2out_nxt & P2_EN_MSK;
assign p2_dout = p2out;
reg  [7:0] p2dir;
wire       p2dir_wr  = P2DIR[0] ? reg_hi_wr[P2DIR] : reg_lo_wr[P2DIR];
wire [7:0] p2dir_nxt = P2DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p2dir <=  8'h00;
  else if (p2dir_wr)  p2dir <=  p2dir_nxt & P2_EN_MSK;
assign p2_dout_en = p2dir;
reg  [7:0] p2ifg;
wire       p2ifg_wr  = P2IFG[0] ? reg_hi_wr[P2IFG] : reg_lo_wr[P2IFG];
wire [7:0] p2ifg_nxt = P2IFG[0] ? per_din[15:8]    : per_din[7:0];
wire [7:0] p2ifg_set;
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p2ifg <=  8'h00;
  else if (p2ifg_wr)  p2ifg <=  (p2ifg_nxt | p2ifg_set) & P2_EN_MSK;
  else                p2ifg <=  (p2ifg     | p2ifg_set) & P2_EN_MSK;
reg  [7:0] p2ies;
wire       p2ies_wr  = P2IES[0] ? reg_hi_wr[P2IES] : reg_lo_wr[P2IES];
wire [7:0] p2ies_nxt = P2IES[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p2ies <=  8'h00;
  else if (p2ies_wr)  p2ies <=  p2ies_nxt & P2_EN_MSK;
reg  [7:0] p2ie;
wire       p2ie_wr  = P2IE[0] ? reg_hi_wr[P2IE] : reg_lo_wr[P2IE];
wire [7:0] p2ie_nxt = P2IE[0] ? per_din[15:8]   : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p2ie <=  8'h00;
  else if (p2ie_wr)  p2ie <=  p2ie_nxt & P2_EN_MSK;
reg  [7:0] p2sel;
wire       p2sel_wr  = P2SEL[0] ? reg_hi_wr[P2SEL] : reg_lo_wr[P2SEL];
wire [7:0] p2sel_nxt = P2SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p2sel <=  8'h00;
  else if (p2sel_wr) p2sel <=  p2sel_nxt & P2_EN_MSK;
assign p2_sel = p2sel;
wire  [7:0] p3in;
omsp_sync_cell sync_cell_p3in_0 (.data_out(p3in[0]), .data_in(p3_din[0] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_1 (.data_out(p3in[1]), .data_in(p3_din[1] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_2 (.data_out(p3in[2]), .data_in(p3_din[2] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_3 (.data_out(p3in[3]), .data_in(p3_din[3] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_4 (.data_out(p3in[4]), .data_in(p3_din[4] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_5 (.data_out(p3in[5]), .data_in(p3_din[5] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_6 (.data_out(p3in[6]), .data_in(p3_din[6] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_7 (.data_out(p3in[7]), .data_in(p3_din[7] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p3out;
wire       p3out_wr  = P3OUT[0] ? reg_hi_wr[P3OUT] : reg_lo_wr[P3OUT];
wire [7:0] p3out_nxt = P3OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p3out <=  8'h00;
  else if (p3out_wr)  p3out <=  p3out_nxt & P3_EN_MSK;
assign p3_dout = p3out;
reg  [7:0] p3dir;
wire       p3dir_wr  = P3DIR[0] ? reg_hi_wr[P3DIR] : reg_lo_wr[P3DIR];
wire [7:0] p3dir_nxt = P3DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p3dir <=  8'h00;
  else if (p3dir_wr)  p3dir <=  p3dir_nxt & P3_EN_MSK;
assign p3_dout_en = p3dir;
reg  [7:0] p3sel;
wire       p3sel_wr  = P3SEL[0] ? reg_hi_wr[P3SEL] : reg_lo_wr[P3SEL];
wire [7:0] p3sel_nxt = P3SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p3sel <=  8'h00;
  else if (p3sel_wr) p3sel <=  p3sel_nxt & P3_EN_MSK;
assign p3_sel = p3sel;
wire  [7:0] p4in;
omsp_sync_cell sync_cell_p4in_0 (.data_out(p4in[0]), .data_in(p4_din[0] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_1 (.data_out(p4in[1]), .data_in(p4_din[1] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_2 (.data_out(p4in[2]), .data_in(p4_din[2] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_3 (.data_out(p4in[3]), .data_in(p4_din[3] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_4 (.data_out(p4in[4]), .data_in(p4_din[4] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_5 (.data_out(p4in[5]), .data_in(p4_din[5] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_6 (.data_out(p4in[6]), .data_in(p4_din[6] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_7 (.data_out(p4in[7]), .data_in(p4_din[7] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p4out;
wire       p4out_wr  = P4OUT[0] ? reg_hi_wr[P4OUT] : reg_lo_wr[P4OUT];
wire [7:0] p4out_nxt = P4OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p4out <=  8'h00;
  else if (p4out_wr)  p4out <=  p4out_nxt & P4_EN_MSK;
assign p4_dout = p4out;
reg  [7:0] p4dir;
wire       p4dir_wr  = P4DIR[0] ? reg_hi_wr[P4DIR] : reg_lo_wr[P4DIR];
wire [7:0] p4dir_nxt = P4DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p4dir <=  8'h00;
  else if (p4dir_wr)  p4dir <=  p4dir_nxt & P4_EN_MSK;
assign p4_dout_en = p4dir;
reg  [7:0] p4sel;
wire       p4sel_wr  = P4SEL[0] ? reg_hi_wr[P4SEL] : reg_lo_wr[P4SEL];
wire [7:0] p4sel_nxt = P4SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p4sel <=  8'h00;
  else if (p4sel_wr) p4sel <=  p4sel_nxt & P4_EN_MSK;
assign p4_sel = p4sel;
wire  [7:0] p5in;
omsp_sync_cell sync_cell_p5in_0 (.data_out(p5in[0]), .data_in(p5_din[0] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_1 (.data_out(p5in[1]), .data_in(p5_din[1] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_2 (.data_out(p5in[2]), .data_in(p5_din[2] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_3 (.data_out(p5in[3]), .data_in(p5_din[3] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_4 (.data_out(p5in[4]), .data_in(p5_din[4] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_5 (.data_out(p5in[5]), .data_in(p5_din[5] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_6 (.data_out(p5in[6]), .data_in(p5_din[6] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_7 (.data_out(p5in[7]), .data_in(p5_din[7] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p5out;
wire       p5out_wr  = P5OUT[0] ? reg_hi_wr[P5OUT] : reg_lo_wr[P5OUT];
wire [7:0] p5out_nxt = P5OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p5out <=  8'h00;
  else if (p5out_wr)  p5out <=  p5out_nxt & P5_EN_MSK;
assign p5_dout = p5out;
reg  [7:0] p5dir;
wire       p5dir_wr  = P5DIR[0] ? reg_hi_wr[P5DIR] : reg_lo_wr[P5DIR];
wire [7:0] p5dir_nxt = P5DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p5dir <=  8'h00;
  else if (p5dir_wr)  p5dir <=  p5dir_nxt & P5_EN_MSK;
assign p5_dout_en = p5dir;
reg  [7:0] p5sel;
wire       p5sel_wr  = P5SEL[0] ? reg_hi_wr[P5SEL] : reg_lo_wr[P5SEL];
wire [7:0] p5sel_nxt = P5SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p5sel <=  8'h00;
  else if (p5sel_wr) p5sel <=  p5sel_nxt & P5_EN_MSK;
assign p5_sel = p5sel;
wire  [7:0] p6in;
omsp_sync_cell sync_cell_p6in_0 (.data_out(p6in[0]), .data_in(p6_din[0] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_1 (.data_out(p6in[1]), .data_in(p6_din[1] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_2 (.data_out(p6in[2]), .data_in(p6_din[2] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_3 (.data_out(p6in[3]), .data_in(p6_din[3] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_4 (.data_out(p6in[4]), .data_in(p6_din[4] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_5 (.data_out(p6in[5]), .data_in(p6_din[5] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_6 (.data_out(p6in[6]), .data_in(p6_din[6] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_7 (.data_out(p6in[7]), .data_in(p6_din[7] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p6out;
wire       p6out_wr  = P6OUT[0] ? reg_hi_wr[P6OUT] : reg_lo_wr[P6OUT];
wire [7:0] p6out_nxt = P6OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p6out <=  8'h00;
  else if (p6out_wr)  p6out <=  p6out_nxt & P6_EN_MSK;
assign p6_dout = p6out;
reg  [7:0] p6dir;
wire       p6dir_wr  = P6DIR[0] ? reg_hi_wr[P6DIR] : reg_lo_wr[P6DIR];
wire [7:0] p6dir_nxt = P6DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p6dir <=  8'h00;
  else if (p6dir_wr)  p6dir <=  p6dir_nxt & P6_EN_MSK;
assign p6_dout_en = p6dir;
reg  [7:0] p6sel;
wire       p6sel_wr  = P6SEL[0] ? reg_hi_wr[P6SEL] : reg_lo_wr[P6SEL];
wire [7:0] p6sel_nxt = P6SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p6sel <=  8'h00;
  else if (p6sel_wr) p6sel <=  p6sel_nxt & P6_EN_MSK;
assign p6_sel = p6sel;
reg    [7:0] p1in_dly;
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)  p1in_dly <=  8'h00;
  else          p1in_dly <=  p1in & P1_EN_MSK;
wire   [7:0] p1in_re   =   p1in & ~p1in_dly;
wire   [7:0] p1in_fe   =  ~p1in &  p1in_dly;
assign       p1ifg_set = {p1ies[7] ? p1in_fe[7] : p1in_re[7],
                          p1ies[6] ? p1in_fe[6] : p1in_re[6],
                          p1ies[5] ? p1in_fe[5] : p1in_re[5],
                          p1ies[4] ? p1in_fe[4] : p1in_re[4],
                          p1ies[3] ? p1in_fe[3] : p1in_re[3],
                          p1ies[2] ? p1in_fe[2] : p1in_re[2],
                          p1ies[1] ? p1in_fe[1] : p1in_re[1],
                          p1ies[0] ? p1in_fe[0] : p1in_re[0]} & P1_EN_MSK;
assign       irq_port1 = |(p1ie & p1ifg) & P1_EN[0];
reg    [7:0] p2in_dly;
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)  p2in_dly <=  8'h00;
  else          p2in_dly <=  p2in & P2_EN_MSK;
wire   [7:0] p2in_re   =   p2in & ~p2in_dly;
wire   [7:0] p2in_fe   =  ~p2in &  p2in_dly;
assign       p2ifg_set = {p2ies[7] ? p2in_fe[7] : p2in_re[7],
                          p2ies[6] ? p2in_fe[6] : p2in_re[6],
                          p2ies[5] ? p2in_fe[5] : p2in_re[5],
                          p2ies[4] ? p2in_fe[4] : p2in_re[4],
                          p2ies[3] ? p2in_fe[3] : p2in_re[3],
                          p2ies[2] ? p2in_fe[2] : p2in_re[2],
                          p2ies[1] ? p2in_fe[1] : p2in_re[1],
                          p2ies[0] ? p2in_fe[0] : p2in_re[0]} & P2_EN_MSK;
assign      irq_port2 = |(p2ie & p2ifg) & P2_EN[0];
wire [15:0] p1in_rd   = {8'h00, (p1in  & {8{reg_rd[P1IN]}})}  << (8 & {4{P1IN[0]}});
wire [15:0] p1out_rd  = {8'h00, (p1out & {8{reg_rd[P1OUT]}})} << (8 & {4{P1OUT[0]}});
wire [15:0] p1dir_rd  = {8'h00, (p1dir & {8{reg_rd[P1DIR]}})} << (8 & {4{P1DIR[0]}});
wire [15:0] p1ifg_rd  = {8'h00, (p1ifg & {8{reg_rd[P1IFG]}})} << (8 & {4{P1IFG[0]}});
wire [15:0] p1ies_rd  = {8'h00, (p1ies & {8{reg_rd[P1IES]}})} << (8 & {4{P1IES[0]}});
wire [15:0] p1ie_rd   = {8'h00, (p1ie  & {8{reg_rd[P1IE]}})}  << (8 & {4{P1IE[0]}});
wire [15:0] p1sel_rd  = {8'h00, (p1sel & {8{reg_rd[P1SEL]}})} << (8 & {4{P1SEL[0]}});
wire [15:0] p2in_rd   = {8'h00, (p2in  & {8{reg_rd[P2IN]}})}  << (8 & {4{P2IN[0]}});
wire [15:0] p2out_rd  = {8'h00, (p2out & {8{reg_rd[P2OUT]}})} << (8 & {4{P2OUT[0]}});
wire [15:0] p2dir_rd  = {8'h00, (p2dir & {8{reg_rd[P2DIR]}})} << (8 & {4{P2DIR[0]}});
wire [15:0] p2ifg_rd  = {8'h00, (p2ifg & {8{reg_rd[P2IFG]}})} << (8 & {4{P2IFG[0]}});
wire [15:0] p2ies_rd  = {8'h00, (p2ies & {8{reg_rd[P2IES]}})} << (8 & {4{P2IES[0]}});
wire [15:0] p2ie_rd   = {8'h00, (p2ie  & {8{reg_rd[P2IE]}})}  << (8 & {4{P2IE[0]}});
wire [15:0] p2sel_rd  = {8'h00, (p2sel & {8{reg_rd[P2SEL]}})} << (8 & {4{P2SEL[0]}});
wire [15:0] p3in_rd   = {8'h00, (p3in  & {8{reg_rd[P3IN]}})}  << (8 & {4{P3IN[0]}});
wire [15:0] p3out_rd  = {8'h00, (p3out & {8{reg_rd[P3OUT]}})} << (8 & {4{P3OUT[0]}});
wire [15:0] p3dir_rd  = {8'h00, (p3dir & {8{reg_rd[P3DIR]}})} << (8 & {4{P3DIR[0]}});
wire [15:0] p3sel_rd  = {8'h00, (p3sel & {8{reg_rd[P3SEL]}})} << (8 & {4{P3SEL[0]}});
wire [15:0] p4in_rd   = {8'h00, (p4in  & {8{reg_rd[P4IN]}})}  << (8 & {4{P4IN[0]}});
wire [15:0] p4out_rd  = {8'h00, (p4out & {8{reg_rd[P4OUT]}})} << (8 & {4{P4OUT[0]}});
wire [15:0] p4dir_rd  = {8'h00, (p4dir & {8{reg_rd[P4DIR]}})} << (8 & {4{P4DIR[0]}});
wire [15:0] p4sel_rd  = {8'h00, (p4sel & {8{reg_rd[P4SEL]}})} << (8 & {4{P4SEL[0]}});
wire [15:0] p5in_rd   = {8'h00, (p5in  & {8{reg_rd[P5IN]}})}  << (8 & {4{P5IN[0]}});
wire [15:0] p5out_rd  = {8'h00, (p5out & {8{reg_rd[P5OUT]}})} << (8 & {4{P5OUT[0]}});
wire [15:0] p5dir_rd  = {8'h00, (p5dir & {8{reg_rd[P5DIR]}})} << (8 & {4{P5DIR[0]}});
wire [15:0] p5sel_rd  = {8'h00, (p5sel & {8{reg_rd[P5SEL]}})} << (8 & {4{P5SEL[0]}});
wire [15:0] p6in_rd   = {8'h00, (p6in  & {8{reg_rd[P6IN]}})}  << (8 & {4{P6IN[0]}});
wire [15:0] p6out_rd  = {8'h00, (p6out & {8{reg_rd[P6OUT]}})} << (8 & {4{P6OUT[0]}});
wire [15:0] p6dir_rd  = {8'h00, (p6dir & {8{reg_rd[P6DIR]}})} << (8 & {4{P6DIR[0]}});
wire [15:0] p6sel_rd  = {8'h00, (p6sel & {8{reg_rd[P6SEL]}})} << (8 & {4{P6SEL[0]}});
wire [15:0] per_dout  =  p1in_rd   |
                         p1out_rd  |
                         p1dir_rd  |
                         p1ifg_rd  |
                         p1ies_rd  |
                         p1ie_rd   |
                         p1sel_rd  |
                         p2in_rd   |
                         p2out_rd  |
                         p2dir_rd  |
                         p2ifg_rd  |
                         p2ies_rd  |
                         p2ie_rd   |
                         p2sel_rd  |
                         p3in_rd   |
                         p3out_rd  |
                         p3dir_rd  |
                         p3sel_rd  |
                         p4in_rd   |
                         p4out_rd  |
                         p4dir_rd  |
                         p4sel_rd  |
                         p5in_rd   |
                         p5out_rd  |
                         p5dir_rd  |
                         p5sel_rd  |
                         p6in_rd   |
                         p6out_rd  |
                         p6dir_rd  |
                         p6sel_rd;
endmodule

Identify the primary security assets for 'omsp_gpio' and return the JSON object per the contract.

CSA ANALYSIS (internal working; not emitted).

P3164 3.1.1 rubric -- answer, then the conceptual asset it yields:

 (C) Any element that can leak or expose material needing confidentiality?
     NO. Summary 5: no keys, entropy, passwords or boot images; payload is ordinary I/O
     data. P3164 answers NO for its own GPIO pad ("the gates inside the IP do not leak any
     information"). Observability alone is not a confidentiality argument.
 (I) Any element that can modify material an integrator may deem sensitive?
     YES. P3164: toggling Direction Select mid-sample toggles the sampled Data -- "the mux
     gates can be considered conceptual assets". Here that is (a) per-port direction, which
     decides drive vs. tri-state, and (b) per-port function select, which decides whether
     GPIO or an alternate block owns the pin -- this is P3164's mux. Both are writable over
     the peripheral bus with no documented privilege check and persist until rewritten.
     Reaching either is qualified by (c) the bus enable and byte write strobes.
 (A) Any element that, if unavailable, can prohibit operational behavior?
     YES, on the SAME elements. P3164: Direction Select "can reverse the data flow ... which
     can be a denial of service. The elements impacted by this attack are the mux gates" --
     note P3164 maps both (I) and (A) to one conceptual asset rather than inventing a second.
 (U) Privileged mode, override, bypass or injection path?
     NO. No debug mode, lock bit or privileged override is documented; configuration is
     simply writable. P3164 answers NO for the same reason.

Conceptual assets: (a) pad direction control, (b) pad function selection, (c) register
access qualification.

P3164 3.1.2 structural mapping -- find the RTL that produces, stores and transports each:
     (a) registers p1dir..p6dir  ->  leave the module as p1_dout_en..p6_dout_en
     (b) registers p1sel..p6sel  ->  leave the module as p1_sel..p6_sel
     (c) ports per_en, per_we
Each pair carries one value ("assign p1_dout_en = p1dir;"). Bind where the control LEAVES
the module and becomes visible system-wide; the register is its storage and belongs to the
later secondary-asset stage.

Objective: (a) and (b) answered YES to both (I) and (A). A wrong value is believed and acted
on, so Integrity dominates and the denial-of-service consequence goes in the Justification,
not into a second asset. (c) is Integrity.

NON-assets: p*_dout / p*_din are ordinary I/O payload -- the data P3164 describes as being
corrupted THROUGH the direction control, not the asset. per_addr / per_din / per_dout are the
bus address and payload path. mclk, puc_rst are infrastructure. reg_sel, reg_addr, reg_dec,
reg_lo_wr, reg_hi_wr, reg_rd, reg_read are decode plumbing downstream of per_en/per_we, which
are what an external agent actually drives. irq_port1/irq_port2 are a real availability
concern but sit outside the reference asset list scoped here.

EMITTED OUTPUT:
{
 "IP": "omsp_gpio",
 "Assets": [
  {
   "Asset Name": "Peripheral enable",
   "Asset RTL": "per_en",
   "Entity": "omsp_gpio",
   "Functionality": "Qualifies peripheral bus access and gates register read/write within the GPIO address space.",
   "Security Objective": "Integrity",
   "Justification": "If an attacker can assert/deassert the enable at the wrong time, writes could be dropped or unintended registers accessed. Preserving the correctness of bus qualification is essential to keep GPIO configuration state from being corrupted."
  },
  {
   "Asset Name": "Peripheral write enable byte strobes",
   "Asset RTL": "per_we",
   "Entity": "omsp_gpio",
   "Functionality": "Selects which byte(s) of the targeted register are written (high/low) during a bus transaction.",
   "Security Objective": "Integrity",
   "Justification": "Manipulating write strobes can partially overwrite control registers, leading to inconsistent configuration. Correct write granularity is required to preserve register integrity."
  },
  {
   "Asset Name": "Port 1 output enable mask",
   "Asset RTL": "p1_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 1 bit (derived from direction), controlling tri-state behavior.",
   "Security Objective": "Integrity",
   "Justification": "Improper enable can force-drive lines or leave them floating, potentially damaging hardware or violating protocol. The correctness of drive enable must be preserved."
  },
  {
   "Asset Name": "Port 2 output enable mask",
   "Asset RTL": "p2_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 2 bit (derived from direction).",
   "Security Objective": "Integrity",
   "Justification": "Unauthorized changes can cause bus contention or unintended signal assertion, compromising system correctness."
  },
  {
   "Asset Name": "Port 3 output enable mask",
   "Asset RTL": "p3_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 3 bit (derived from direction).",
   "Security Objective": "Integrity",
   "Justification": "Correct direction/enable settings are critical to safe pin driving; tampering compromises signal integrity."
  },
  {
   "Asset Name": "Port 4 output enable mask",
   "Asset RTL": "p4_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 4 bit (derived from direction).",
   "Security Objective": "Integrity",
   "Justification": "Misconfiguration allows unintended driving or tri-stating of lines, breaking expected operation."
  },
  {
   "Asset Name": "Port 5 output enable mask",
   "Asset RTL": "p5_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 5 bit (derived from direction).",
   "Security Objective": "Integrity",
   "Justification": "Ensures only intended pins drive; corruption endangers correct I/O behavior and external interfaces."
  },
  {
   "Asset Name": "Port 6 output enable mask",
   "Asset RTL": "p6_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 6 bit (derived from direction).",
   "Security Objective": "Integrity",
   "Justification": "Prevents unintended drive conditions that could violate system-level correctness."
  },
  {
   "Asset Name": "Port 1 function select",
   "Asset RTL": "p1_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 1 pin.",
   "Security Objective": "Integrity",
   "Justification": "Unauthorised switching of pin function can reroute signals and break higher-level protocols. Maintaining correct selection protects system behavior."
  },
  {
   "Asset Name": "Port 2 function select",
   "Asset RTL": "p2_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 2 pin.",
   "Security Objective": "Integrity",
   "Justification": "Wrong function routing can connect/disconnect critical signals, so selection must remain trustworthy."
  },
  {
   "Asset Name": "Port 3 function select",
   "Asset RTL": "p3_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 3 pin.",
   "Security Objective": "Integrity",
   "Justification": "Altering selection changes signal routing on the pad, potentially disrupting system operation."
  },
  {
   "Asset Name": "Port 4 function select",
   "Asset RTL": "p4_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 4 pin.",
   "Security Objective": "Integrity",
   "Justification": "Protecting this configuration prevents unintended re-mapping of pins that could break interfaces."
  },
  {
   "Asset Name": "Port 5 function select",
   "Asset RTL": "p5_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 5 pin.",
   "Security Objective": "Integrity",
   "Justification": "Misrouting pins changes system connectivity; integrity of this control is essential."
  },
  {
   "Asset Name": "Port 6 function select",
   "Asset RTL": "p6_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 6 pin.",
   "Security Objective": "Integrity",
   "Justification": "Ensures intended signal routing; tampering could disconnect required signals or connect the wrong ones."
  }
 ]
}
"""


EXAMPLE_02_AES_HT = """\
### CASE STUDY 2: aes_highthroughput_lowarea (AES-128/192/256 encrypt/decrypt core)

TARGET IP MODULE: aes_highthroughput_lowarea

=== TECHNICAL SUMMARY ===
MODULE: aes_highthroughput_lowarea
1. FUNCTION AND ROLE
AES encryption/decryption core supporting 128-, 192- and 256-bit keys, built for high
throughput at low area by sharing one substitution pipeline across rounds. Operation has two
phases. First a key-expansion unit derives the full round-key schedule from the supplied
cipher key and writes it into an on-chip key RAM, raising a done indication when finished.
Then, for each data block presented on the input port, the core iterates the shared
round datapath -- substitution, shift-rows, mix-columns and AddRoundKey -- reading the
appropriate round key back out of the key RAM each round, and presents the result with an
output-valid indication. A mode input selects encryption or decryption; the substitution
stage switches between the forward and inverse S-box accordingly.
2. REGISTERS, CSRS, AND FLAGS
Not documented for this module. The core has no memory-mapped register interface. Its
software-visible controls are direct ports (enable, mode, key-length select, key-expansion
start) and its status is reported on direct ports (key-expansion done, ready-for-input,
output-valid) rather than through readable registers. Internally it holds the expanded round
keys in a key RAM and the evolving block in the round datapath registers.
3. CONFIGURATION
- i_key_mode — run-time — key length select: 0 => 128, 1 => 192, 2 => 256 bits
- i_ende — run-time — mode of operation: 0 => encryption, 1 => decryption
- i_enable — run-time — enables core operation
4. CROSS-MODULE INTERACTION
The core is driven directly by surrounding logic rather than over a bus: the integrator
supplies the cipher key, the key-length and mode selects, the enable, the key-expansion start
pulse and the data blocks, and consumes the output block. Flow control is by handshake -- the
core asserts ready when it can accept a new block, asserts output-valid when a result is
available, and asserts key-expansion-done when the schedule is built. Whatever supplies the
key and whatever consumes the ciphertext lie outside this module.
5. SECURITY-RELEVANT BEHAVIOR
Security-critical by function: the module exists to protect data, and both the cipher key and
the input block are secret material. No access control, privilege level, lock or key-clearing
mechanism is documented or implemented. The cipher key is presented on a port and is expanded
into a full round-key schedule that persists in the on-chip key RAM until the next expansion,
so key-derived material is retained across data blocks. There is no debug or test mode, so no
external path exists to substitute a test key, observe intermediate round state, or halt the
datapath. Correct output depends on the mode select, the enable and the key-expansion
sequencing being exactly right; a wrong mode or a corrupted round key silently produces a
wrong result rather than an error, as the core reports no error status.

=== PARSED I/O PORTS (JSON) ===
[
 {
  "entity": "aes",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "core global clock"
 },
 {
  "entity": "aes",
  "name": "reset",
  "dir": "input",
  "type": "wire",
  "function": "core global asynchronous reset"
 },
 {
  "entity": "aes",
  "name": "i_start",
  "dir": "input",
  "type": "wire",
  "function": "key expansion start pulse"
 },
 {
  "entity": "aes",
  "name": "i_enable",
  "dir": "input",
  "type": "wire",
  "function": "enable encryption/decryption core operation"
 },
 {
  "entity": "aes",
  "name": "i_key_mode",
  "dir": "input",
  "type": "wire[1:0]",
  "function": "select key length (0=128,1=192,2=256)"
 },
 {
  "entity": "aes",
  "name": "i_key",
  "dir": "input",
  "type": "wire[255:0]",
  "function": "256-bit input key (upper bits unused for smaller keys)"
 },
 {
  "entity": "aes",
  "name": "i_data",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "128-bit plaintext/ciphertext data input"
 },
 {
  "entity": "aes",
  "name": "i_data_valid",
  "dir": "input",
  "type": "wire",
  "function": "input data valid strobe"
 },
 {
  "entity": "aes",
  "name": "i_ende",
  "dir": "input",
  "type": "wire",
  "function": "mode select: 0=encryption, 1=decryption"
 },
 {
  "entity": "aes",
  "name": "o_ready",
  "dir": "output",
  "type": "wire",
  "function": "core ready for new input next cycle"
 },
 {
  "entity": "aes",
  "name": "o_data",
  "dir": "output",
  "type": "wire[127:0]",
  "function": "128-bit data output (cipher/plain)"
 },
 {
  "entity": "aes",
  "name": "o_data_valid",
  "dir": "output",
  "type": "wire",
  "function": "data output valid strobe"
 },
 {
  "entity": "aes",
  "name": "o_key_ready",
  "dir": "output",
  "type": "wire",
  "function": "indicates key expansion procedure completed"
 },
 {
  "entity": "inv_shift_rows",
  "name": "si",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "input 128-bit AES state to inverse ShiftRows"
 },
 {
  "entity": "inv_shift_rows",
  "name": "so",
  "dir": "output",
  "type": "wire[127:0]",
  "function": "output 128-bit AES state after inverse ShiftRows"
 },
 {
  "entity": "key_exp",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "global clock for key expansion logic"
 },
 {
  "entity": "key_exp",
  "name": "reset",
  "dir": "input",
  "type": "wire",
  "function": "global asynchronous reset for module registers"
 },
 {
  "entity": "key_exp",
  "name": "key_in",
  "dir": "input",
  "type": "wire[255:0]",
  "function": "256-bit initial cipher key input"
 },
 {
  "entity": "key_exp",
  "name": "key_mode",
  "dir": "input",
  "type": "wire[1:0]",
  "function": "selects key length: 0=128,1=192,2=256"
 },
 {
  "entity": "key_exp",
  "name": "key_start",
  "dir": "input",
  "type": "wire",
  "function": "pulse to start key expansion procedure"
 },
 {
  "entity": "key_exp",
  "name": "wr",
  "dir": "output",
  "type": "wire",
  "function": "write-enable signal for key expansion RAM writes"
 },
 {
  "entity": "key_exp",
  "name": "wr_addr",
  "dir": "output",
  "type": "wire[4:0]",
  "function": "5-bit write address for expanded key RAM"
 },
 {
  "entity": "key_exp",
  "name": "wr_data",
  "dir": "output",
  "type": "wire[63:0]",
  "function": "64-bit data bus for writing expanded keys"
 },
 {
  "entity": "key_exp",
  "name": "key_ready",
  "dir": "output",
  "type": "wire",
  "function": "indicates key expansion finished and ready"
 },
 {
  "entity": "xtimes",
  "name": "in",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Multiply input byte by 2 in GF(2^8)"
 },
 {
  "entity": "xtimes",
  "name": "out",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Result byte: input multiplied by 2 in GF(2^8)"
 },
 {
  "entity": "MUL3",
  "name": "in",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "input byte to be multiplied by 3 in GF(2^8)"
 },
 {
  "entity": "MUL3",
  "name": "out",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "output byte = 3 * in (GF(2^8)) for MixColumns"
 },
 {
  "entity": "MULE",
  "name": "in",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "GF(2^8) byte input to multiply-by-0x0E block"
 },
 {
  "entity": "MULE",
  "name": "out",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "GF(2^8) result: input multiplied by 0x0E (inv mixcolumns)"
 },
 {
  "entity": "MULB",
  "name": "in",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Multiply input by 0x0B in GF(2^8) (inv mix columns)"
 },
 {
  "entity": "MULB",
  "name": "out",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Multiply input by 0x0B in GF(2^8) (inv mix columns)"
 },
 {
  "entity": "MULD",
  "name": "in",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "input byte to multiply by 0x0D in GF(256)"
 },
 {
  "entity": "MULD",
  "name": "out",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "output byte equal input multiplied by 0x0D in GF(256)"
 },
 {
  "entity": "MUL9",
  "name": "in",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "8-bit input byte to multiply-by-9 (GF(2^8))"
 },
 {
  "entity": "MUL9",
  "name": "out",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "8-bit output = input multiplied by 9 in GF(2^8)"
 },
 {
  "entity": "byte_mix_columns",
  "name": "a",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "input byte; multiplied by 2 for mix-column computation"
 },
 {
  "entity": "byte_mix_columns",
  "name": "b",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "input byte; multiplied by 3 for mix-column computation"
 },
 {
  "entity": "byte_mix_columns",
  "name": "c",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "input byte XORed directly into mix-column result"
 },
 {
  "entity": "byte_mix_columns",
  "name": "d",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "input byte XORed directly into mix-column result"
 },
 {
  "entity": "byte_mix_columns",
  "name": "out",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "output byte = 2*a ^ 3*b ^ c ^ d (mix column)"
 },
 {
  "entity": "inv_byte_mix_columns",
  "name": "a",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "input byte multiplied by 0x0e for inverse mixcolumns"
 },
 {
  "entity": "inv_byte_mix_columns",
  "name": "b",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "input byte multiplied by 0x0b for inverse mixcolumns"
 },
 {
  "entity": "inv_byte_mix_columns",
  "name": "c",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "input byte multiplied by 0x0d for inverse mixcolumns"
 },
 {
  "entity": "inv_byte_mix_columns",
  "name": "d",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "input byte multiplied by 0x09 for inverse mixcolumns"
 },
 {
  "entity": "inv_byte_mix_columns",
  "name": "out",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "output byte: XOR of products (inverse mixcolumns result)"
 },
 {
  "entity": "word_mix_columns",
  "name": "in",
  "dir": "input",
  "type": "wire[31:0]",
  "function": "32-bit input word for MixColumns (encryption)"
 },
 {
  "entity": "word_mix_columns",
  "name": "out",
  "dir": "output",
  "type": "wire[31:0]",
  "function": "32-bit output word after MixColumns (encryption)"
 },
 {
  "entity": "inv_word_mix_columns",
  "name": "in",
  "dir": "input",
  "type": "wire[31:0]",
  "function": "32-bit input word for inverse MixColumns"
 },
 {
  "entity": "inv_word_mix_columns",
  "name": "out",
  "dir": "output",
  "type": "wire[31:0]",
  "function": "32-bit output word from inverse MixColumns"
 },
 {
  "entity": "mix_columns",
  "name": "in",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "128-bit state input to MixColumns transformation"
 },
 {
  "entity": "mix_columns",
  "name": "out",
  "dir": "output",
  "type": "wire[127:0]",
  "function": "128-bit state output from MixColumns transformation"
 },
 {
  "entity": "inv_mix_columns",
  "name": "in",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "128-bit input state to inverse MixColumns transformation"
 },
 {
  "entity": "inv_mix_columns",
  "name": "out",
  "dir": "output",
  "type": "wire[127:0]",
  "function": "128-bit output state from inverse MixColumns transformation"
 },
 {
  "entity": "ram_16x64",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "memory clock input, synchronous operations"
 },
 {
  "entity": "ram_16x64",
  "name": "wr",
  "dir": "input",
  "type": "wire",
  "function": "write enable signal (active high) for mem write"
 },
 {
  "entity": "ram_16x64",
  "name": "rd",
  "dir": "input",
  "type": "wire",
  "function": "read enable signal (registered, samples rd_addr on clock) "
 },
 {
  "entity": "ram_16x64",
  "name": "wr_addr",
  "dir": "input",
  "type": "wire[3:0]",
  "function": "4-bit write address to select memory location"
 },
 {
  "entity": "ram_16x64",
  "name": "rd_addr",
  "dir": "input",
  "type": "wire[3:0]",
  "function": "4-bit read address to select memory location (sampled) "
 },
 {
  "entity": "ram_16x64",
  "name": "wr_data",
  "dir": "input",
  "type": "wire[63:0]",
  "function": "64-bit input data bus for write operations"
 },
 {
  "entity": "ram_16x64",
  "name": "rd_data",
  "dir": "output",
  "type": "wire[63:0]",
  "function": "64-bit output data bus presenting read memory word"
 },
 {
  "entity": "sbox",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "global clock"
 },
 {
  "entity": "sbox",
  "name": "reset",
  "dir": "input",
  "type": "wire",
  "function": "global asynchronous reset"
 },
 {
  "entity": "sbox",
  "name": "enable",
  "dir": "input",
  "type": "wire",
  "function": "enable pipeline registers/process"
 },
 {
  "entity": "sbox",
  "name": "din",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "8-bit input byte to S-box"
 },
 {
  "entity": "sbox",
  "name": "ende",
  "dir": "input",
  "type": "wire",
  "function": "mode select: 0 encrypt, 1 decrypt"
 },
 {
  "entity": "sbox",
  "name": "en_dout",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "8-bit S-box output for encryption"
 },
 {
  "entity": "sbox",
  "name": "de_dout",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "8-bit S-box output for decryption"
 },
 {
  "entity": "sbox",
  "name": "data",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "unclear from RTL"
 },
 {
  "entity": "sbox",
  "name": "d1",
  "dir": "input",
  "type": "wire[3:0]",
  "function": "4-bit multiplicand input for GF(16) multiply"
 },
 {
  "entity": "sbox",
  "name": "d2",
  "dir": "input",
  "type": "wire[3:0]",
  "function": "4-bit multiplicand input for GF(16) multiply"
 },
 {
  "entity": "sbox",
  "name": "p",
  "dir": "input",
  "type": "wire[3:0]",
  "function": "4-bit GF(16) nibble for GF16/256 transform"
 },
 {
  "entity": "sbox",
  "name": "q",
  "dir": "input",
  "type": "wire[3:0]",
  "function": "4-bit GF(16) nibble for GF16/256 transform"
 },
 {
  "entity": "shift_rows",
  "name": "si",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "128-bit state input for AES ShiftRows operation"
 },
 {
  "entity": "shift_rows",
  "name": "so",
  "dir": "output",
  "type": "wire[127:0]",
  "function": "128-bit state output after AES ShiftRows permutation"
 },
 {
  "entity": "xram_16x64",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "memory clock input (rising-edge synchronous)"
 },
 {
  "entity": "xram_16x64",
  "name": "wr",
  "dir": "input",
  "type": "wire",
  "function": "write enable signal for memory write"
 },
 {
  "entity": "xram_16x64",
  "name": "wr_addr",
  "dir": "input",
  "type": "wire[3:0]",
  "function": "4-bit write address selecting memory word"
 },
 {
  "entity": "xram_16x64",
  "name": "rd_addr",
  "dir": "input",
  "type": "wire[3:0]",
  "function": "4-bit read address selecting memory word"
 },
 {
  "entity": "xram_16x64",
  "name": "wr_data",
  "dir": "input",
  "type": "wire[63:0]",
  "function": "64-bit input data bus for write operations"
 },
 {
  "entity": "xram_16x64",
  "name": "rd_data",
  "dir": "output",
  "type": "wire[63:0]",
  "function": "64-bit output read data from addressed memory"
 }
]

=== PARSED INTERNAL SIGNALS (JSON) ===
[
 {
  "entity": "aes",
  "name": "final_round",
  "type": "wire",
  "kind": "signal",
  "function": "indicates if current sb_round_cnt3 equals max_round"
 },
 {
  "entity": "aes",
  "name": "max_round",
  "type": "reg[3:0]",
  "kind": "signal",
  "function": "maximum round count based on key size"
 },
 {
  "entity": "aes",
  "name": "en_sb_data",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "S-box output for encryption bytes"
 },
 {
  "entity": "aes",
  "name": "de_sb_data",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "S-box output for decryption bytes"
 },
 {
  "entity": "aes",
  "name": "sr_data",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "shift-rows output selected by mode"
 },
 {
  "entity": "aes",
  "name": "mc_data",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "mix-columns output for encryption path"
 },
 {
  "entity": "aes",
  "name": "imc_data",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "inverse mix-columns output for decryption path"
 },
 {
  "entity": "aes",
  "name": "ark_data",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "selected data after adding round key"
 },
 {
  "entity": "aes",
  "name": "sb_data",
  "type": "reg[127:0]",
  "kind": "register",
  "function": "registered bytes after S-box stage"
 },
 {
  "entity": "aes",
  "name": "i_data_L",
  "type": "reg[127:0]",
  "kind": "register",
  "function": "latched input data for initial round key add"
 },
 {
  "entity": "aes",
  "name": "i_data_valid_L",
  "type": "reg",
  "kind": "register",
  "function": "latched input data valid indicator"
 },
 {
  "entity": "aes",
  "name": "round_valid",
  "type": "reg",
  "kind": "register",
  "function": "indicates an ongoing non-final round pipeline stage"
 },
 {
  "entity": "aes",
  "name": "sb_valid",
  "type": "reg[2:0]",
  "kind": "register",
  "function": "3-stage pipeline validity for S-box pipeline"
 },
 {
  "entity": "aes",
  "name": "round_cnt",
  "type": "reg[3:0]",
  "kind": "register",
  "function": "current round counter (starts at 1)"
 },
 {
  "entity": "aes",
  "name": "sb_round_cnt1",
  "type": "reg[3:0]",
  "kind": "register",
  "function": "round count delayed by one pipeline stage"
 },
 {
  "entity": "aes",
  "name": "sb_round_cnt2",
  "type": "reg[3:0]",
  "kind": "register",
  "function": "round count delayed by two pipeline stages"
 },
 {
  "entity": "aes",
  "name": "sb_round_cnt3",
  "type": "reg[3:0]",
  "kind": "register",
  "function": "round count delayed by three pipeline stages"
 },
 {
  "entity": "aes",
  "name": "round_key",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "current 128-bit round key read from RAMs"
 },
 {
  "entity": "aes",
  "name": "rd_data0",
  "type": "wire[63:0]",
  "kind": "signal",
  "function": "lower 64 bits read from key RAM bank0"
 },
 {
  "entity": "aes",
  "name": "rd_data1",
  "type": "wire[63:0]",
  "kind": "signal",
  "function": "upper 64 bits read from key RAM bank1"
 },
 {
  "entity": "aes",
  "name": "wr",
  "type": "wire",
  "kind": "signal",
  "function": "write enable from key expansion module"
 },
 {
  "entity": "aes",
  "name": "wr_addr",
  "type": "wire[4:0]",
  "kind": "signal",
  "function": "write address for key expansion RAMs"
 },
 {
  "entity": "aes",
  "name": "wr_data",
  "type": "wire[63:0]",
  "kind": "signal",
  "function": "64-bit write data from key expansion"
 },
 {
  "entity": "aes",
  "name": "imc_round_key",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "inverse-mix-columns applied to round_key"
 },
 {
  "entity": "aes",
  "name": "en_ark_data",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "encryption path data XORed with round key"
 },
 {
  "entity": "aes",
  "name": "de_ark_data",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "decryption path data XORed with inverse round key"
 },
 {
  "entity": "aes",
  "name": "ark_data_final",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "data XOR round key for final round"
 },
 {
  "entity": "aes",
  "name": "ark_data_init",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "initial data XOR round key for first round"
 },
 {
  "entity": "aes",
  "name": "shrows",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "shift-rows transformation output (encryption)"
 },
 {
  "entity": "aes",
  "name": "ishrows",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "inverse shift-rows transformation output (decryption)"
 },
 {
  "entity": "aes",
  "name": "rd_addr",
  "type": "reg[3:0]",
  "kind": "register",
  "function": "read address for key RAMs (registered)"
 },
 {
  "entity": "key_exp",
  "name": "rcon",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "AES round constant (32-bit) register"
 },
 {
  "entity": "key_exp",
  "name": "rcon_is_1b",
  "type": "reg",
  "kind": "register",
  "function": "flag when rcon became 0x1b"
 },
 {
  "entity": "key_exp",
  "name": "state",
  "type": "reg[1:0]",
  "kind": "register",
  "function": "key expansion FSM current state"
 },
 {
  "entity": "key_exp",
  "name": "nstate",
  "type": "reg[1:0]",
  "kind": "signal",
  "function": "next state combinational value for FSM"
 },
 {
  "entity": "key_exp",
  "name": "pstate",
  "type": "reg[1:0]",
  "kind": "register",
  "function": "previous FSM state register"
 },
 {
  "entity": "key_exp",
  "name": "round",
  "type": "reg[3:0]",
  "kind": "register",
  "function": "key expansion round counter"
 },
 {
  "entity": "key_exp",
  "name": "sbox_in_valid",
  "type": "reg",
  "kind": "register",
  "function": "indicates sbox input valid (one-hot pipeline)"
 },
 {
  "entity": "key_exp",
  "name": "sbox_in",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "32-bit input word to sbox (rotword)"
 },
 {
  "entity": "key_exp",
  "name": "valid",
  "type": "reg[4:0]",
  "kind": "register",
  "function": "5-stage validity shift register for sbox pipeline"
 },
 {
  "entity": "key_exp",
  "name": "sbox_out_valid",
  "type": "wire",
  "kind": "signal",
  "function": "sbox output valid one-cycle indicator"
 },
 {
  "entity": "key_exp",
  "name": "sbox_out",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "32-bit sbox output word"
 },
 {
  "entity": "key_exp",
  "name": "w0_next",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "next value for w0 during expansion"
 },
 {
  "entity": "key_exp",
  "name": "w1_next",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "next value for w1 during expansion"
 },
 {
  "entity": "key_exp",
  "name": "w2_next",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "next value for w2 during expansion"
 },
 {
  "entity": "key_exp",
  "name": "w3_next",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "next value for w3 during expansion"
 },
 {
  "entity": "key_exp",
  "name": "w4_next1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "aux next value for w4 in 192-bit mode"
 },
 {
  "entity": "key_exp",
  "name": "w5_next1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "aux next value for w5 in 192-bit mode"
 },
 {
  "entity": "key_exp",
  "name": "w6_next",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "next value for w6 during expansion"
 },
 {
  "entity": "key_exp",
  "name": "w7_next",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "next value for w7 during expansion"
 },
 {
  "entity": "key_exp",
  "name": "w4_next2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "alternate next value for w4 in 256-bit mode"
 },
 {
  "entity": "key_exp",
  "name": "w5_next2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "alternate next value for w5 in 256-bit mode"
 },
 {
  "entity": "key_exp",
  "name": "w0",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "expanded key word 0 (32-bit)"
 },
 {
  "entity": "key_exp",
  "name": "w1",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "expanded key word 1 (32-bit)"
 },
 {
  "entity": "key_exp",
  "name": "w2",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "expanded key word 2 (32-bit)"
 },
 {
  "entity": "key_exp",
  "name": "w3",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "expanded key word 3 (32-bit)"
 },
 {
  "entity": "key_exp",
  "name": "w4",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "expanded key word 4 (32-bit)"
 },
 {
  "entity": "key_exp",
  "name": "w5",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "expanded key word 5 (32-bit)"
 },
 {
  "entity": "key_exp",
  "name": "w6",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "expanded key word 6 (32-bit)"
 },
 {
  "entity": "key_exp",
  "name": "w7",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "expanded key word 7 (32-bit)"
 },
 {
  "entity": "key_exp",
  "name": "wr1",
  "type": "wire",
  "kind": "signal",
  "function": "write strobe stage 1 to RAM"
 },
 {
  "entity": "key_exp",
  "name": "wr2",
  "type": "wire",
  "kind": "signal",
  "function": "write strobe stage 2 to RAM"
 },
 {
  "entity": "key_exp",
  "name": "wr3",
  "type": "wire",
  "kind": "signal",
  "function": "write strobe stage 3 to RAM"
 },
 {
  "entity": "key_exp",
  "name": "init_wr1",
  "type": "wire",
  "kind": "signal",
  "function": "initial write strobe for key segment 1"
 },
 {
  "entity": "key_exp",
  "name": "init_wr2",
  "type": "wire",
  "kind": "signal",
  "function": "initial write strobe for key segment 2"
 },
 {
  "entity": "key_exp",
  "name": "init_wr3",
  "type": "wire",
  "kind": "signal",
  "function": "initial write strobe for key segment 3"
 },
 {
  "entity": "key_exp",
  "name": "init_wr4",
  "type": "wire",
  "kind": "signal",
  "function": "initial write strobe for key segment 4"
 },
 {
  "entity": "key_exp",
  "name": "wr_data1",
  "type": "wire[63:0]",
  "kind": "signal",
  "function": "64-bit write data option 1 for RAM"
 },
 {
  "entity": "key_exp",
  "name": "wr_data2",
  "type": "wire[63:0]",
  "kind": "signal",
  "function": "64-bit write data option 2 for RAM"
 },
 {
  "entity": "key_exp",
  "name": "wr_data3",
  "type": "wire[63:0]",
  "kind": "signal",
  "function": "64-bit write data option 3 for RAM"
 },
 {
  "entity": "key_exp",
  "name": "key_start_L",
  "type": "reg",
  "kind": "register",
  "function": "key_start delayed by one cycle"
 },
 {
  "entity": "key_exp",
  "name": "key_start_L2",
  "type": "reg",
  "kind": "register",
  "function": "key_start delayed by two cycles"
 },
 {
  "entity": "key_exp",
  "name": "key_start_L3",
  "type": "reg",
  "kind": "register",
  "function": "key_start delayed by three cycles"
 },
 {
  "entity": "key_exp",
  "name": "wr_256",
  "type": "reg",
  "kind": "register",
  "function": "selects 256-bit write packing mode"
 },
 {
  "entity": "key_exp",
  "name": "max_round_p1",
  "type": "wire[3:0]",
  "kind": "signal",
  "function": "max rounds + 1 based on key mode"
 },
 {
  "entity": "xtimes",
  "name": "xt",
  "type": "wire[3:0]",
  "kind": "signal",
  "function": "intermediate bits for multiply-by-2 (xtimes) GF(256) operation"
 },
 {
  "entity": "MUL3",
  "name": "xt",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "output of xtimes module (input multiplied by 2)"
 },
 {
  "entity": "MULE",
  "name": "xt1",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "intermediate xtimes output (first multiply-by-x result)"
 },
 {
  "entity": "MULE",
  "name": "xt2",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "intermediate xtimes output (second multiply-by-x result)"
 },
 {
  "entity": "MULE",
  "name": "xt3",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "intermediate xtimes output (third multiply-by-x result)"
 },
 {
  "entity": "MULB",
  "name": "xt1",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "first xtimes output (2*x) intermediate for multiply-by-B"
 },
 {
  "entity": "MULB",
  "name": "xt2",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "second xtimes output (4*x) intermediate value"
 },
 {
  "entity": "MULB",
  "name": "xt3",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "third xtimes output (8*x) intermediate for final XOR"
 },
 {
  "entity": "MULD",
  "name": "xt1",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input multiplied by 2 (xtimes intermediate) "
 },
 {
  "entity": "MULD",
  "name": "xt2",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input multiplied by 4 (second xtimes) "
 },
 {
  "entity": "MULD",
  "name": "xt3",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input multiplied by 8 (third xtimes) "
 },
 {
  "entity": "MUL9",
  "name": "xt1",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "first xtimes output (2\\u00d7in) for MUL9 computation"
 },
 {
  "entity": "MUL9",
  "name": "xt2",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "second xtimes output (4\\u00d7in) for MUL9 computation"
 },
 {
  "entity": "MUL9",
  "name": "xt3",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "third xtimes output (8\\u00d7in) for MUL9 computation"
 },
 {
  "entity": "byte_mix_columns",
  "name": "mul2",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "a multiplied by 2 in GF(2^8) for MixColumns"
 },
 {
  "entity": "byte_mix_columns",
  "name": "mul3",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "b multiplied by 3 in GF(2^8) for MixColumns"
 },
 {
  "entity": "inv_byte_mix_columns",
  "name": "mule",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "product of a multiplied by 0xE in GF(2^8)"
 },
 {
  "entity": "inv_byte_mix_columns",
  "name": "mulb",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "product of b multiplied by 0xB in GF(2^8)"
 },
 {
  "entity": "inv_byte_mix_columns",
  "name": "muld",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "product of c multiplied by 0xD in GF(2^8)"
 },
 {
  "entity": "inv_byte_mix_columns",
  "name": "mul9",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "product of d multiplied by 0x9 in GF(2^8)"
 },
 {
  "entity": "word_mix_columns",
  "name": "si0",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input byte extracted from in[31:24]"
 },
 {
  "entity": "word_mix_columns",
  "name": "si1",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input byte extracted from in[23:16]"
 },
 {
  "entity": "word_mix_columns",
  "name": "si2",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input byte extracted from in[15:8]"
 },
 {
  "entity": "word_mix_columns",
  "name": "si3",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input byte extracted from in[7:0]"
 },
 {
  "entity": "word_mix_columns",
  "name": "so0",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "output byte: mixed column result for word byte0"
 },
 {
  "entity": "word_mix_columns",
  "name": "so1",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "output byte: mixed column result for word byte1"
 },
 {
  "entity": "word_mix_columns",
  "name": "so2",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "output byte: mixed column result for word byte2"
 },
 {
  "entity": "word_mix_columns",
  "name": "so3",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "output byte: mixed column result for word byte3"
 },
 {
  "entity": "inv_word_mix_columns",
  "name": "si0",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input byte 0 extracted from 31:24 of input word"
 },
 {
  "entity": "inv_word_mix_columns",
  "name": "si1",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input byte 1 extracted from 23:16 of input word"
 },
 {
  "entity": "inv_word_mix_columns",
  "name": "si2",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input byte 2 extracted from 15:8 of input word"
 },
 {
  "entity": "inv_word_mix_columns",
  "name": "si3",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input byte 3 extracted from 7:0 of input word"
 },
 {
  "entity": "inv_word_mix_columns",
  "name": "so0",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "output byte 0 from inv_byte_mix_columns"
 },
 {
  "entity": "inv_word_mix_columns",
  "name": "so1",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "output byte 1 from inv_byte_mix_columns"
 },
 {
  "entity": "inv_word_mix_columns",
  "name": "so2",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "output byte 2 from inv_byte_mix_columns"
 },
 {
  "entity": "inv_word_mix_columns",
  "name": "so3",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "output byte 3 from inv_byte_mix_columns"
 },
 {
  "entity": "mix_columns",
  "name": "so0",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "mixed column output word for input segment [127:96]"
 },
 {
  "entity": "mix_columns",
  "name": "so1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "mixed column output word for input segment [95:64]"
 },
 {
  "entity": "mix_columns",
  "name": "so2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "mixed column output word for input segment [63:32]"
 },
 {
  "entity": "mix_columns",
  "name": "so3",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "mixed column output word for input segment [31:0]"
 },
 {
  "entity": "inv_mix_columns",
  "name": "so0",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "32-bit output word from inv_word_mix_columns instance"
 },
 {
  "entity": "inv_mix_columns",
  "name": "so1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "32-bit output word from inv_word_mix_columns instance"
 },
 {
  "entity": "inv_mix_columns",
  "name": "so2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "32-bit output word from inv_word_mix_columns instance"
 },
 {
  "entity": "inv_mix_columns",
  "name": "so3",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "32-bit output word from inv_word_mix_columns instance"
 },
 {
  "entity": "ram_16x64",
  "name": "srd_addr",
  "type": "reg[3:0]",
  "kind": "register",
  "function": "registered read address sampled on rd assertion"
 },
 {
  "entity": "sbox",
  "name": "first_matrix_out",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "GF16 representation output of input byte"
 },
 {
  "entity": "sbox",
  "name": "first_matrix_in",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "input to GF256->GF16 transformation"
 },
 {
  "entity": "sbox",
  "name": "last_matrix_out_enc",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "affine-transformed GF16->GF256 encryption output"
 },
 {
  "entity": "sbox",
  "name": "last_matrix_out_dec",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "GF16->GF256 decryption output (pre-affine)"
 },
 {
  "entity": "sbox",
  "name": "p2",
  "type": "wire[3:0]",
  "kind": "signal",
  "function": "square of GF16 component p"
 },
 {
  "entity": "sbox",
  "name": "q2",
  "type": "wire[3:0]",
  "kind": "signal",
  "function": "square of GF16 component q"
 },
 {
  "entity": "sbox",
  "name": "sumpq",
  "type": "wire[3:0]",
  "kind": "signal",
  "function": "bitwise XOR sum of p and q"
 },
 {
  "entity": "sbox",
  "name": "sump2q2",
  "type": "wire[3:0]",
  "kind": "signal",
  "function": "combined polynomial p2 + pq + q2B"
 },
 {
  "entity": "sbox",
  "name": "inv_sump2q2",
  "type": "wire[3:0]",
  "kind": "signal",
  "function": "multiplicative inverse of sump2q2 in GF16"
 },
 {
  "entity": "sbox",
  "name": "p_new",
  "type": "wire[3:0]",
  "kind": "signal",
  "function": "computed new p in GF16 before pipeline"
 },
 {
  "entity": "sbox",
  "name": "q_new",
  "type": "wire[3:0]",
  "kind": "signal",
  "function": "computed new q in GF16 before pipeline"
 },
 {
  "entity": "sbox",
  "name": "mulpq",
  "type": "wire[3:0]",
  "kind": "signal",
  "function": "product of p and q in GF16"
 },
 {
  "entity": "sbox",
  "name": "q2B",
  "type": "wire[3:0]",
  "kind": "signal",
  "function": "linear combination of q2 bits used in inverse"
 },
 {
  "entity": "sbox",
  "name": "first_matrix_out_L",
  "type": "reg[7:0]",
  "kind": "register",
  "function": "pipeline register holding first_matrix_out"
 },
 {
  "entity": "sbox",
  "name": "p_new_L",
  "type": "reg[3:0]",
  "kind": "register",
  "function": "pipeline register holding computed p_new"
 },
 {
  "entity": "sbox",
  "name": "q_new_L",
  "type": "reg[3:0]",
  "kind": "register",
  "function": "pipeline register holding computed q_new"
 },
 {
  "entity": "sbox",
  "name": "a",
  "type": "reg",
  "kind": "signal",
  "function": "temporary variable inside GF256/GF16 functions"
 },
 {
  "entity": "sbox",
  "name": "b",
  "type": "reg",
  "kind": "signal",
  "function": "temporary variable inside GF256/GF16 functions"
 },
 {
  "entity": "sbox",
  "name": "c",
  "type": "reg",
  "kind": "signal",
  "function": "temporary variable inside GF256/GF16 functions"
 },
 {
  "entity": "sbox",
  "name": "d",
  "type": "reg",
  "kind": "signal",
  "function": "temporary variable inside inverse affine function"
 }
]

=== RTL ===
`define XILINX		1
module aes (
	clk, reset,
	i_start, i_enable,
	i_ende, i_key,
	i_key_mode, i_data,
	i_data_valid, o_ready,
	o_data, o_data_valid,
	o_key_ready
);
input			clk;
input			reset;
input			i_start;
input			i_enable;
input	[1:0]	i_key_mode;
input	[255:0]	i_key;
input	[127:0]	i_data;
input			i_data_valid;
input			i_ende;
output			o_ready;
output	[127:0]	o_data;
output			o_data_valid;
output			o_key_ready;
genvar i;
wire           final_round;
reg   [3:0]    max_round;
wire  [127:0]  en_sb_data,de_sb_data,sr_data,mc_data,imc_data,ark_data;
reg   [127:0]  sb_data,o_data,i_data_L;
reg            i_data_valid_L;
reg            round_valid;
reg   [2:0]    sb_valid;
reg            o_data_valid;
reg   [3:0]    round_cnt,sb_round_cnt1,sb_round_cnt2,sb_round_cnt3;
wire  [127:0]  round_key;
wire  [63:0]   rd_data0,rd_data1;
wire           wr;
wire  [4:0]    wr_addr;
wire  [63:0]   wr_data;
wire  [127:0]  imc_round_key,en_ark_data,de_ark_data,ark_data_final,ark_data_init;
assign final_round = sb_round_cnt3[3:0] == max_round[3:0];
assign o_ready = ~sb_valid[0];
always @ (*)
begin
   case (i_key_mode)
      2'b00: max_round[3:0] = 4'd10;
      2'b01: max_round[3:0] = 4'd12;
      default: max_round[3:0] = 4'd14;
   endcase
end
generate
for (i=0;i<16;i=i+1)
begin : sbox_block
   sbox u_sbox (
      .clk(clk),
      .reset(reset),
      .enable(i_enable),
      .ende(i_ende),
      .din(o_data[i*8+7:i*8]),
      .en_dout(en_sb_data[i*8+7:i*8]),
      .de_dout(de_sb_data[i*8+7:i*8])
   );
end
endgenerate
always @ (posedge clk or posedge reset)
begin
   if (reset)
      sb_data[127:0] <= 128'b0;
   else if (i_enable)
      sb_data[127:0] <= i_ende ? de_sb_data[127:0] : en_sb_data[127:0];
end
wire [127:0] shrows, ishrows;
shift_rows u_shrows (.si(sb_data[127:0]), .so(shrows));
inv_shift_rows u_ishrows (.si(sb_data[127:0]), .so(ishrows));
assign sr_data[127:0] = i_ende ? ishrows : shrows;
mix_columns mxc_u (.in(sr_data), .out(mc_data));
always @ (posedge clk or posedge reset)
begin
   if (reset)
   begin
      i_data_valid_L  <= 1'b0;
      i_data_L[127:0] <= 128'b0;
   end
   else
   begin
      i_data_valid_L  <= i_data_valid;
      i_data_L[127:0] <=i_data[127:0];
   end
end
inv_mix_columns imxc_u (.in(sr_data), .out(imc_data));
inv_mix_columns imxk_u (.in(round_key), .out(imc_round_key));
assign ark_data_final[127:0] = sr_data[127:0] ^ round_key[127:0];
assign ark_data_init[127:0] = i_data_L[127:0] ^ round_key[127:0];
assign en_ark_data[127:0] = mc_data[127:0] ^ round_key[127:0];
assign de_ark_data[127:0] = imc_data[127:0] ^ imc_round_key[127:0];
assign ark_data[127:0] = i_data_valid_L ? ark_data_init[127:0] :
                           (final_round ? ark_data_final[127:0] :
                                (i_ende ? de_ark_data[127:0] : en_ark_data[127:0]));
always @ (posedge clk or posedge reset)
begin
   if (reset)
      o_data[127:0] <= 128'b0;
   else if (i_enable && (i_data_valid_L || sb_valid[2]))
      o_data[127:0] <= ark_data[127:0];
end
always @ (posedge clk or posedge reset)
begin
   if (reset)
   begin
      round_valid  <= 1'b0;
      sb_valid[2:0] <= 3'b0;
      o_data_valid  <= 1'b0;
   end
   else if (i_enable)
   begin
      o_data_valid  <= sb_valid[2] && final_round;
      round_valid   <= (sb_valid[2] && !final_round) || i_data_valid_L;
      sb_valid[2:0] <= {sb_valid[1:0],round_valid};
   end
end
always @ (posedge clk or posedge reset)
begin
   if (reset)                      round_cnt[3:0] <= 4'd0;
   else if (i_data_valid_L) round_cnt[3:0] <= 4'd1;
   else if (i_enable && sb_valid[2])  round_cnt[3:0] <= sb_round_cnt3[3:0] + 1'b1;
end
always @ (posedge clk or posedge reset)
begin
   if (reset)
   begin
      sb_round_cnt1[3:0] <= 4'd0;
      sb_round_cnt2[3:0] <= 4'd0;
      sb_round_cnt3[3:0] <= 4'd0;
   end
   else if (i_enable)
   begin
      if (round_valid) sb_round_cnt1[3:0] <= round_cnt[3:0];
      if (sb_valid[0]) sb_round_cnt2[3:0] <= sb_round_cnt1[3:0];
      if (sb_valid[1]) sb_round_cnt3[3:0] <= sb_round_cnt2[3:0];
   end
end
assign round_key[127:0] = {rd_data0[63:0],rd_data1[63:0]};
`ifdef XILINX
reg [3:0] rd_addr;
always @ (posedge clk or posedge reset)
begin
	if (reset)
		rd_addr <= 4'b0;
	else if (sb_valid[1] | i_data_valid)
	begin
		if (i_ende)
		begin
			if (i_data_valid)
				rd_addr <= max_round[3:0];
			else
				rd_addr <= max_round[3:0] - sb_round_cnt2[3:0];
		end
		else
		begin
			if (i_data_valid)
				rd_addr <= 4'b0;
			else
				rd_addr <= sb_round_cnt2[3:0];
		end
	end
end
xram_16x64 u_ram_0
(
	.clk(clk),
	.wr(wr & ~wr_addr[0]),
	.wr_addr(wr_addr[4:1]),
	.wr_data(wr_data[63:0]),
	.rd_addr(rd_addr[3:0]),
	.rd_data(rd_data0[63:0])
);
xram_16x64 u_ram_1
(
	.clk(clk),
	.wr(wr & wr_addr[0]),
	.wr_addr(wr_addr[4:1]),
	.wr_data(wr_data[63:0]),
	.rd_addr(rd_addr[3:0]),
	.rd_data(rd_data1[63:0])
);
`else
wire [3:0] rd_addr;
assign rd_addr[3:0] = i_ende ? (i_data_valid ? max_round[3:0] : (max_round[3:0] - sb_round_cnt2[3:0])) :
                               (i_data_valid ? 4'b0 : sb_round_cnt2[3:0]);
ram_16x64 u_ram_0
(
	.clk(clk),
	.wr(wr & ~wr_addr[0]),
	.wr_addr(wr_addr[4:1]),
	.wr_data(wr_data[63:0]),
	.rd_addr(rd_addr[3:0]),
	.rd_data(rd_data0[63:0]),
	.rd(sb_valid[1] | i_data_valid)
);
ram_16x64 u_ram_1
(
	.clk(clk),
	.wr(wr & wr_addr[0]),
	.wr_addr(wr_addr[4:1]),
	.wr_data(wr_data[63:0]),
	.rd_addr(rd_addr[3:0]),
	.rd_data(rd_data1[63:0]),
	.rd(sb_valid[1] | i_data_valid)
);
`endif
key_exp u_key_exp (
   .clk(clk),
   .reset(reset),
   .key_in(i_key[255:0]),
   .key_mode(i_key_mode[1:0]),
   .key_start(i_start),
   .wr(wr),
   .wr_addr(wr_addr[4:0]),
   .wr_data(wr_data[63:0]),
   .key_ready(o_key_ready)
);
endmodule
module inv_shift_rows (
	si, so
);
input	[127:0]	si;
output	[127:0]	so;
wire [127:0] so;
assign 	so[127:96] = {si[127:120],si[23:16],si[47:40],si[71:64]};
assign 	so[95:64] = {si[95:88],si[119:112],si[15:8],si[39:32]};
assign 	so[63:32] = {si[63:56],si[87:80],si[111:104],si[7:0]};
assign 	so[31:0] = {si[31:24],si[55:48],si[79:72],si[103:96]};
endmodule
module key_exp (
   clk,
   reset,
   key_in,
   key_mode,
   key_start,
   wr,
   wr_addr,
   wr_data,
   key_ready
);
input             clk;
input             reset;
input   [255:0]   key_in;
input   [1:0]     key_mode;
input             key_start;
output            wr;
output  [4:0]     wr_addr;
output  [63:0]    wr_data;
output            key_ready;
reg [31:0]  rcon;
reg         rcon_is_1b;
reg [1:0]   state,nstate,pstate;
reg [3:0]   round;
reg         sbox_in_valid;
reg [31:0]  sbox_in;
reg [4:0]   valid;
wire        sbox_out_valid;
wire [31:0] sbox_out;
wire [31:0] w0_next,w1_next,w2_next,w3_next,w4_next1,w5_next1,w6_next,w7_next;
wire [31:0] w4_next2,w5_next2;
reg [31:0]  w0,w1,w2,w3,w4,w5,w6,w7;
wire        wr1,wr2,wr3,init_wr1,init_wr2,init_wr3,init_wr4;
reg         wr;
wire [63:0] wr_data1,wr_data2,wr_data3;
reg         key_start_L,key_start_L2,key_start_L3;
reg         wr_256;
reg [4:0]   wr_addr;
reg [63:0]  wr_data;
reg         key_ready;
wire   [3:0] max_round_p1;
parameter   IDLE       = 2'b00,
            START      = 2'b01,
            GENKEY1    = 2'b10,
            GENKEY_256 = 2'b11;
assign max_round_p1[3:0] = (key_mode == 2'b00) ? 4'd11 : (key_mode == 2'b01 ? 4'd13 : 4'd15);
always @ (posedge clk or posedge reset)
begin
   if (reset)
   begin
      rcon[31:0] <= 32'h01000000;
      rcon_is_1b <= 1'b0;
   end
   else if (key_start)
   begin
      rcon[31:0] <= 32'h01000000;
      rcon_is_1b <= 1'b0;
   end
   else if (sbox_out_valid && (state[1:0] == GENKEY1))
   begin
      if (rcon[31])
      begin
         rcon[31:0] <= 32'h1b000000;
         rcon_is_1b <= 1'b1;
      end
      else if (rcon_is_1b)
      begin
         rcon[31:0] <= 32'h36000000;
         rcon_is_1b <= 1'b1;
      end
      else
         rcon[31:0] <= {rcon[30:0],1'b0};
   end
end
always @ (posedge clk or posedge reset)
begin
   if (reset)
   begin
      state[1:0]  <= IDLE;
      pstate[1:0] <= IDLE;
   end
   else
   begin
      state[1:0]  <= nstate[1:0];
      pstate[1:0] <= state[1:0];
   end
end
always @ (*)
begin
   nstate[1:0] = state[1:0];
   case (state[1:0])
      IDLE:
         if (key_start) nstate[1:0] = START;
      START:
      begin
         nstate[1:0] = GENKEY1;
      end
      GENKEY1:
      begin
         if (sbox_out_valid)
         begin
            if (key_mode == 2'b00)
               if (round[3:0] == 4'd10)   nstate[1:0] = IDLE;
               else                       nstate[1:0] = START;
            else if (key_mode == 2'b01)
               if (round[3:0] == 4'd8) nstate[1:0] = IDLE;
               else                    nstate[1:0] = START;
            else if (round[3:0] == 4'd7)
               nstate[1:0] = IDLE;
            else
               nstate[1:0] = GENKEY_256;
         end
      end
      GENKEY_256:
      begin
         if (sbox_out_valid)
            nstate[1:0] = START;
      end
   endcase
end
always @ (posedge clk or posedge reset)
begin
   if (reset)
      round[3:0] <= 1'b0;
   else if (nstate[1:0] == IDLE)
      round[3:0] <= 4'b0;
   else if (state[1:0] == START)
      round[3:0] <= round[3:0] + 1'b1;
end
always @ (posedge clk or posedge reset)
begin
   if (reset)
   begin
      sbox_in_valid <= 1'b0;
      sbox_in[31:0] <= 32'b0;
   end
   else if (state[1:0] == START)
   begin
      sbox_in_valid <= 1'b1;
      if (key_mode == 2'b00)
         sbox_in[31:0] <= {w3[23:0],w3[31:24]};
      else if (key_mode == 2'b01)
         sbox_in[31:0] <= {w5[23:0],w5[31:24]};
      else
         sbox_in[31:0] <= {w7[23:0],w7[31:24]};
   end
   else if ((state[1:0] == GENKEY_256) && (pstate[1:0] ==GENKEY1))
   begin
      sbox_in_valid <= 1'b1;
      sbox_in[31:0] <= w3[31:0];
   end
   else
      sbox_in_valid <= 1'b0;
end
always @ (posedge clk or posedge reset)
begin
   if (reset)
      valid[4:0] <= 5'b0;
   else
      valid[4:0] <= {valid[3:0],sbox_in_valid};
end
assign sbox_out_valid = valid[1];
sbox u_0(.clk(clk),.reset(reset),.enable(1'b1),.din(sbox_in[7:0]),.ende(1'b0),.en_dout(sbox_out[7:0]),.de_dout());
sbox u_1(.clk(clk),.reset(reset),.enable(1'b1),.din(sbox_in[15:8]),.ende(1'b0),.en_dout(sbox_out[15:8]),.de_dout());
sbox u_2(.clk(clk),.reset(reset),.enable(1'b1),.din(sbox_in[23:16]),.ende(1'b0),.en_dout(sbox_out[23:16]),.de_dout());
sbox u_3(.clk(clk),.reset(reset),.enable(1'b1),.din(sbox_in[31:24]),.ende(1'b0),.en_dout(sbox_out[31:24]),.de_dout());
assign w0_next[31:0]  = sbox_out[31:0] ^ rcon[31:0]^w0[31:0];
assign w1_next[31:0]  = w0_next[31:0]  ^ w1[31:0];
assign w2_next[31:0]  = w1_next[31:0]  ^ w2[31:0];
assign w3_next[31:0]  = w2_next[31:0]  ^ w3[31:0];
assign w4_next1[31:0] = w3_next[31:0]  ^ w4[31:0];
assign w5_next1[31:0] = w4_next1[31:0] ^ w5[31:0];
assign w4_next2[31:0] = sbox_out[31:0] ^ w4[31:0];
assign w5_next2[31:0] = w4_next2[31:0] ^ w5[31:0];
assign w6_next[31:0]  = w5_next2[31:0] ^ w6[31:0];
assign w7_next[31:0]  = w6_next[31:0]  ^ w7[31:0];
always @ (posedge clk or posedge reset)
begin
   if (reset)
   begin
      {w0[31:0],w1[31:0],w2[31:0],w3[31:0],w4[31:0],w5[31:0],w6[31:0],w7[31:0]} <= 256'b0;
   end
   else if (key_start)
   begin
      {w0[31:0],w1[31:0],w2[31:0],w3[31:0],w4[31:0],w5[31:0],w6[31:0],w7[31:0]} <= key_in[255:0];
   end
   else if ((key_mode[1:0] == 2'b10) && sbox_out_valid)
   begin
      if (state[1:0] == GENKEY1)
      begin
         w0[31:0] <= w0_next[31:0];
         w1[31:0] <= w1_next[31:0];
         w2[31:0] <= w2_next[31:0];
         w3[31:0] <= w3_next[31:0];
      end
      else
      begin
         w4[31:0] <= w4_next2[31:0];
         w5[31:0] <= w5_next2[31:0];
         w6[31:0] <= w6_next[31:0];
         w7[31:0] <= w7_next[31:0];
      end
   end
   else if (sbox_out_valid)
   begin
      w0[31:0] <= w0_next[31:0];
      w1[31:0] <= w1_next[31:0];
      w2[31:0] <= w2_next[31:0];
      w3[31:0] <= w3_next[31:0];
      if (key_mode[1:0] == 2'b01)
      begin
         w4[31:0] <= w4_next1[31:0];
         w5[31:0] <= w5_next1[31:0];
      end
   end
end
assign init_wr1 = key_start;
assign init_wr2 = key_start_L;
assign init_wr3 = key_start_L2 && (key_mode[1:0] != 2'b00);
assign init_wr4 = key_start_L3 && (key_mode[1:0] == 2'b10);
assign wr1 = valid[2];
assign wr2 = valid[3];
assign wr3 = valid[4] && (key_mode[1:0] == 2'b01) && (state[1:0] != IDLE);
assign wr_data1[63:0] = wr_256 ?{w4[31:0],w5[31:0]} : {w0[31:0],w1[31:0]};
assign wr_data2[63:0] = wr_256 ?{w6[31:0],w7[31:0]} : {w2[31:0],w3[31:0]};
assign wr_data3[63:0] = {w4[31:0],w5[31:0]};
always @ (posedge clk or posedge reset)
begin
   if (reset)
      wr_256 <= 1'b0;
   else if (key_start)
      wr_256 <= 1'b0;
   else if (sbox_out_valid && (state[1:0] == GENKEY_256))
      wr_256 <= 1'b1;
   else if (sbox_out_valid)
      wr_256 <= 1'b0;
end
always @ (posedge clk or posedge reset)
begin
   if (reset)
      {key_start_L3,key_start_L2,key_start_L} <= 3'b0;
   else
      {key_start_L3,key_start_L2,key_start_L} <= {key_start_L2,key_start_L,key_start};
end
always @ (posedge clk or posedge reset)
begin
   if (reset)
      wr <= 1'b0;
   else
      wr <= wr1 || wr2 || wr3 || init_wr1 || init_wr2 || init_wr3 || init_wr4;
end
always @ (posedge clk or posedge reset)
begin
   if (reset)
   begin
      wr_data[63:0] <= 64'b0;
   end
   else
   begin
      if (init_wr1)
         wr_data[63:0] <= key_in[255:192];
      else if (init_wr2)
         wr_data[63:0] <= key_in[191:128];
      else if (init_wr3)
         wr_data[63:0] <= key_in[127:64];
      else if (init_wr4)
         wr_data[63:0] <= key_in[63:0];
      else if (wr1)
         wr_data[63:0] <= wr_data1[63:0];
      else if (wr2)
         wr_data[63:0] <= wr_data2[63:0];
      else if (wr3)
         wr_data[63:0] <= wr_data3[63:0];
   end
end
always @ (posedge clk or posedge reset)
begin
   if (reset)
      wr_addr[4:0] <= 5'b0;
   else if (key_start)
      wr_addr[4:0] <= 5'd0;
   else if (wr)
      wr_addr[4:0] <= wr_addr[4:0] + 1'b1;
end
always @ (posedge clk or posedge reset)
begin
   if (reset)
      key_ready <= 1'b0;
   else if (key_start)
      key_ready <= 1'b0;
   else if (wr_addr[4:1] == max_round_p1[3:0])
      key_ready <= 1'b1;
end
endmodule
module xtimes (
	in, out
);
input	[7:0]	in;
output	[7:0]	out;
wire [3:0] xt;
assign xt[3] = in[7];
assign xt[2] = in[7];
assign xt[1] = 1'b0;
assign xt[0] = in[7];
assign out[7:5] = in[6:4];
assign out[4:1] = xt[3:0] ^ in[3:0];
assign out[0]   = in[7];
endmodule
module MUL3 (
	in, out
);
input	[7:0]	in;
output	[7:0]	out;
wire [7:0] xt;
xtimes xt_u (.in(in), .out(xt));
assign out = xt ^ in;
endmodule
module MULE (
	in, out
);
input	[7:0]	in;
output	[7:0]	out;
wire [7:0] xt1, xt2, xt3;
xtimes xt_u1 (.in(in), .out(xt1));
xtimes xt_u2 (.in(xt1), .out(xt2));
xtimes xt_u3 (.in(xt2), .out(xt3));
assign out = xt3 ^ xt2 ^ xt1;
endmodule
module MULB (
	in, out
);
input	[7:0]	in;
output	[7:0]	out;
wire [7:0] xt1, xt2, xt3;
xtimes xt_u1 (.in(in), .out(xt1));
xtimes xt_u2 (.in(xt1), .out(xt2));
xtimes xt_u3 (.in(xt2), .out(xt3));
assign out = xt3 ^ xt1 ^ in;
endmodule
module MULD (
	in, out
);
input	[7:0]	in;
output	[7:0]	out;
wire [7:0] xt1, xt2, xt3;
xtimes xt_u1 (.in(in), .out(xt1));
xtimes xt_u2 (.in(xt1), .out(xt2));
xtimes xt_u3 (.in(xt2), .out(xt3));
assign out = xt3 ^ xt2 ^ in;
endmodule
module MUL9 (
	in, out
);
input	[7:0]	in;
output	[7:0]	out;
wire [7:0] xt1, xt2, xt3;
xtimes xt_u1 (.in(in), .out(xt1));
xtimes xt_u2 (.in(xt1), .out(xt2));
xtimes xt_u3 (.in(xt2), .out(xt3));
assign out = xt3 ^ in;
endmodule
module byte_mix_columns (
	a, b, c, d, out
);
input	[7:0]	a, b, c, d;
output	[7:0]	out;
wire [7:0] mul2, mul3;
xtimes xt_u (.in(a), .out(mul2));
MUL3 mul3_u (.in(b), .out(mul3));
assign out = mul2 ^ mul3 ^ c ^ d;
endmodule
module inv_byte_mix_columns (
	a, b, c, d, out
);
input	[7:0]	a, b, c, d;
output	[7:0]	out;
wire [7:0] mule, mulb, muld, mul9;
MULE mule_u (.in(a), .out(mule));
MULB mulb_u (.in(b), .out(mulb));
MULD muld_u (.in(c), .out(muld));
MUL9 mul9_u (.in(d), .out(mul9));
assign out = mule ^ mulb ^ muld ^ mul9;
endmodule
module word_mix_columns (
	in, out
);
input	[31:0]	in;
output	[31:0]	out;
wire [7:0] si0,si1,si2,si3;
wire [7:0] so0,so1,so2,so3;
assign si0[7:0] = in[31:24];
assign si1[7:0] = in[23:16];
assign si2[7:0] = in[15:8];
assign si3[7:0] = in[7:0];
byte_mix_columns so0_u (.a(si0), .b(si1), .c(si2), .d(si3), .out(so0));
byte_mix_columns so1_u (.a(si1), .b(si2), .c(si3), .d(si0), .out(so1));
byte_mix_columns so2_u (.a(si2), .b(si3), .c(si0), .d(si1), .out(so2));
byte_mix_columns so3_u (.a(si3), .b(si0), .c(si1), .d(si2), .out(so3));
assign out = {so0, so1, so2, so3};
endmodule
module inv_word_mix_columns (
	in, out
);
input	[31:0]	in;
output	[31:0]	out;
wire [7:0] si0,si1,si2,si3;
wire [7:0] so0,so1,so2,so3;
assign si0 = in[31:24];
assign si1 = in[23:16];
assign si2 = in[15:8];
assign si3 = in[7:0];
inv_byte_mix_columns so0_u (.a(si0), .b(si1), .c(si2), .d(si3), .out(so0));
inv_byte_mix_columns so1_u (.a(si1), .b(si2), .c(si3), .d(si0), .out(so1));
inv_byte_mix_columns so2_u (.a(si2), .b(si3), .c(si0), .d(si1), .out(so2));
inv_byte_mix_columns so3_u (.a(si3), .b(si0), .c(si1), .d(si2), .out(so3));
assign out = {so0, so1, so2, so3};
endmodule
module mix_columns (
	in, out
);
input	[127:0]	in;
output	[127:0]	out;
wire [31:0] so0,so1,so2,so3;
word_mix_columns so0_u (.in(in[127:96]), .out(so0));
word_mix_columns so1_u (.in(in[95:64]),  .out(so1));
word_mix_columns so2_u (.in(in[63:32]),  .out(so2));
word_mix_columns so3_u (.in(in[31:0]),   .out(so3));
assign out = {so0, so1, so2, so3};
endmodule
module inv_mix_columns (
	in, out
);
input	[127:0]	in;
output	[127:0]	out;
wire [31:0] so0,so1,so2,so3;
inv_word_mix_columns so0_u (.in(in[127:96]), .out(so0));
inv_word_mix_columns so1_u (.in(in[95:64]),  .out(so1));
inv_word_mix_columns so2_u (.in(in[63:32]),  .out(so2));
inv_word_mix_columns so3_u (.in(in[31:0]),   .out(so3));
assign out = {so0, so1, so2, so3};
endmodule
module ram_16x64 (clk,wr,wr_addr,wr_data,rd,rd_addr,rd_data);
input clk,wr,rd;
input [3:0] wr_addr,rd_addr;
input [63:0] wr_data;
output [63:0] rd_data;
reg [63:0] mem[15:0];
wire [63:0] rd_data;
always @ (posedge clk)
begin
   if (wr)
      mem[wr_addr] <= wr_data;
end
reg [3:0] srd_addr;
always @ (posedge clk)
begin
	if (rd)
		srd_addr <= rd_addr;
end
assign rd_data = mem[srd_addr];
endmodule
module sbox(
	clk,
	reset,
	enable,
	din,
	ende,
	en_dout,
	de_dout);
input		clk;
input		reset;
input		enable;
input	[7:0]	din;
input		ende;
output	[7:0]	en_dout;
output	[7:0]	de_dout;
wire [7:0] first_matrix_out,first_matrix_in,last_matrix_out_enc,last_matrix_out_dec;
wire [3:0] p,q,p2,q2,sumpq,sump2q2,inv_sump2q2,p_new,q_new,mulpq,q2B;
reg [7:0]  first_matrix_out_L;
reg [3:0]  p_new_L,q_new_L;
assign first_matrix_in[7:0] = ende ? INV_AFFINE(din[7:0]): din[7:0];
assign first_matrix_out[7:0] = GF256_TO_GF16(first_matrix_in[7:0]);
always @ (posedge clk or posedge reset)
begin
	if (reset)
		first_matrix_out_L[7:0] <= 8'b0;
	else if (enable)
		first_matrix_out_L[7:0] <= first_matrix_out[7:0];
end
assign p[3:0] = first_matrix_out_L[3:0];
assign q[3:0] = first_matrix_out_L[7:4];
assign p2[3:0] = SQUARE(p[3:0]);
assign q2[3:0] = SQUARE(q[3:0]);
assign sumpq[3:0] = p[3:0] ^ q[3:0];
assign mulpq[3:0] = MUL(p[3:0],q[3:0]);
assign q2B[0]=q2[1]^q2[2]^q2[3];
assign q2B[1]=q2[0]^q2[1];
assign q2B[2]=q2[0]^q2[1]^q2[2];
assign q2B[3]=q2[0]^q2[1]^q2[2]^q2[3];
assign sump2q2[3:0] = q2B[3:0] ^ mulpq[3:0] ^ p2[3:0];
assign inv_sump2q2[3:0] = INVERSE(sump2q2[3:0]);
assign p_new[3:0] = MUL(sumpq[3:0],inv_sump2q2[3:0]);
assign q_new[3:0] = MUL(q[3:0],inv_sump2q2[3:0]);
always @ (posedge clk or posedge reset)
begin
	if (reset)
		{p_new_L[3:0],q_new_L[3:0]} <= 8'b0;
	else if (enable)
		{p_new_L[3:0],q_new_L[3:0]} <= {p_new[3:0],q_new[3:0]};
end
assign last_matrix_out_dec[7:0] = GF16_TO_GF256(p_new_L[3:0],q_new_L[3:0]);
assign last_matrix_out_enc[7:0] = AFFINE(last_matrix_out_dec[7:0]);
assign en_dout[7:0] = last_matrix_out_enc[7:0];
assign de_dout[7:0] = last_matrix_out_dec[7:0];
function [7:0] GF256_TO_GF16;
input [7:0] data;
reg a,b,c;
begin
	a = data[1]^data[7];
	b = data[5]^data[7];
	c = data[4]^data[6];
	GF256_TO_GF16[0] = c^data[0]^data[5];
	GF256_TO_GF16[1] = data[1]^data[2];
	GF256_TO_GF16[2] = a;
	GF256_TO_GF16[3] = data[2]^data[4];
	GF256_TO_GF16[4] = c^data[5];
	GF256_TO_GF16[5] = a^c;
	GF256_TO_GF16[6] = b^data[2]^data[3];
	GF256_TO_GF16[7] = b;
end
endfunction
function [3:0] SQUARE;
input [3:0] data;
begin
	SQUARE[0] = data[0]^data[2];
	SQUARE[1] = data[2];
	SQUARE[2] = data[1]^data[3];
	SQUARE[3] = data[3];
end
endfunction
function [3:0] INVERSE;
input [3:0] data;
reg a;
begin
	a=data[1]^data[2]^data[3]^(data[1]&data[2]&data[3]);
	INVERSE[0]=a^data[0]^(data[0]&data[2])^(data[1]&data[2])^(data[0]&data[1]&data[2]);
	INVERSE[1]=(data[0]&data[1])^(data[0]&data[2])^(data[1]&data[2])^data[3]^
		(data[1]&data[3])^(data[0]&data[1]&data[3]);
	INVERSE[2]=(data[0]&data[1])^data[2]^(data[0]&data[2])^data[3]^
		(data[0]&data[3])^(data[0]&data[2]&data[3]);
	INVERSE[3]=a^(data[0]&data[3])^(data[1]&data[3])^(data[2]&data[3]);
end
endfunction
function [3:0] MUL;
input [3:0] d1,d2;
reg a,b;
begin
	a=d1[0]^d1[3];
	b=d1[2]^d1[3];
	MUL[0]=(d1[0]&d2[0])^(d1[3]&d2[1])^(d1[2]&d2[2])^(d1[1]&d2[3]);
	MUL[1]=(d1[1]&d2[0])^(a&d2[1])^(b&d2[2])^((d1[1]^d1[2])&d2[3]);
	MUL[2]=(d1[2]&d2[0])^(d1[1]&d2[1])^(a&d2[2])^(b&d2[3]);
	MUL[3]=(d1[3]&d2[0])^(d1[2]&d2[1])^(d1[1]&d2[2])^(a&d2[3]);
end
endfunction
function [7:0] GF16_TO_GF256;
input [3:0] p,q;
reg a,b;
begin
	a=p[1]^q[3];
	b=q[0]^q[1];
	GF16_TO_GF256[0]=p[0]^q[0];
	GF16_TO_GF256[1]=b^q[3];
	GF16_TO_GF256[2]=a^b;
	GF16_TO_GF256[3]=b^p[1]^q[2];
	GF16_TO_GF256[4]=a^b^p[3];
	GF16_TO_GF256[5]=b^p[2];
	GF16_TO_GF256[6]=a^p[2]^p[3]^q[0];
	GF16_TO_GF256[7]=b^p[2]^q[3];
end
endfunction
function [7:0] AFFINE;
input [7:0] data;
begin
	AFFINE[0]=(!data[0])^data[4]^data[5]^data[6]^data[7];
	AFFINE[1]=(!data[0])^data[1]^data[5]^data[6]^data[7];
	AFFINE[2]=data[0]^data[1]^data[2]^data[6]^data[7];
	AFFINE[3]=data[0]^data[1]^data[2]^data[3]^data[7];
	AFFINE[4]=data[0]^data[1]^data[2]^data[3]^data[4];
	AFFINE[5]=(!data[1])^data[2]^data[3]^data[4]^data[5];
	AFFINE[6]=(!data[2])^data[3]^data[4]^data[5]^data[6];
	AFFINE[7]=data[3]^data[4]^data[5]^data[6]^data[7];
end
endfunction
function [7:0] INV_AFFINE;
input [7:0] data;
reg a,b,c,d;
begin
	a=data[0]^data[5];
	b=data[1]^data[4];
	c=data[2]^data[7];
	d=data[3]^data[6];
	INV_AFFINE[0]=(!data[5])^c;
	INV_AFFINE[1]=data[0]^d;
	INV_AFFINE[2]=(!data[7])^b;
	INV_AFFINE[3]=data[2]^a;
	INV_AFFINE[4]=data[1]^d;
	INV_AFFINE[5]=data[4]^c;
	INV_AFFINE[6]=data[3]^a;
	INV_AFFINE[7]=data[6]^b;
end
endfunction
endmodule
module shift_rows (
	si, so
);
input	[127:0]	si;
output	[127:0]	so;
wire [127:0] so;
assign so[127:96] = {si[127:120],si[87:80],si[47:40],si[7:0]};
assign so[95:64] = {si[95:88],si[55:48],si[15:8],si[103:96]};
assign so[63:32] = {si[63:56],si[23:16],si[111:104],si[71:64]};
assign so[31:0] = {si[31:24],si[119:112],si[79:72],si[39:32]};
endmodule
module xram_16x64
(
	clk, wr,
	wr_addr, wr_data,
	rd_addr, rd_data
);
input clk, wr;
input [3:0] wr_addr, rd_addr;
input [63:0] wr_data;
output [63:0] rd_data;
reg [63:0] mem [15:0];
wire [63:0] rd_data;
always @ (posedge clk)
begin
   if (wr)
      mem[wr_addr] <= wr_data;
end
assign rd_data = mem[rd_addr];
endmodule

Identify the primary security assets for 'aes_highthroughput_lowarea' and return the JSON object per the contract.

CSA ANALYSIS (internal working; not emitted).

P3164 3.1.1 rubric -- answer, then the conceptual asset it yields. P3164's AES walkthrough
(3.2.3) analyses the block diagram of Figure 4: Config Regs, Status Regs, Key Reg, IV Reg,
Input Buffer, Output Buffer, an Enc/Dec Engine, and a Debug interface fed by hardcoded Debug
Values. This core carries most of those blocks, so most of P3164's reasoning transfers
directly; it has no IV and no debug interface, and those two absences change exactly one
answer.

 (C) Any element that can leak or expose material needing confidentiality?
     YES. P3164: "Since this is a crypto IP, the plaintext data and key values are secrets.
     Therefore, any block in Figure 3 that supports these secrets will be a conceptual asset.
     These assets are Key Reg, Enc/Dec Engine, Input Buffer, and Output Buffer." Both secrets
     are present here: the cipher key enters on a port, is expanded into a full round-key
     schedule and retained in the key RAM; the plaintext block enters on its own port.
     P3164 adds a qualified fifth: "In addition, the Status Regs may leak confidential
     information since it provides information about the Enc/Dec Engine. Therefore, this
     block may also be considered a conceptual asset." Note the hedge -- "may". The status
     elements here are handshake flags that report only whether the core is busy or done,
     not anything about the key or the block, so the leak P3164 hedges about does not
     materialise in this design; they are scored under (A) below. This is the general rule:
     an element gets ONE dominant objective and any weaker secondary consequence is written
     into its Justification, never emitted as a second asset.
 (I) Any element that can modify material an integrator may deem sensitive?
     YES. P3164: "When the Enc/Dec Engine is operating, the key, IV, input data, and its
     configuration should not be modified. Therefore, Key Reg, IV Reg, Input Buffer, and
     Config Regs are conceptual assets that require integrity." This core has no IV, but it
     does have configuration -- Table 1 of P3164 lists "AES mode, operation, start/stop" as
     Configuration, and this design exposes exactly those: the encryption/decryption mode
     select, the core enable, and the key-expansion start.
 (A) Any element that, if unavailable, can prohibit operational behavior?
     YES, by a different route than P3164's. P3164 reached availability through the debug
     interface -- "The debug interface allows complete control of the Enc/Dec Engine.
     Therefore, 'Data_Out' can be blocked by this interface, thus making the Enc/Dec Engine
     a conceptual asset". This core has no debug
     interface; availability instead attaches to the handshake by which work is accepted and
     results are delivered. If ready never asserts, no block is ever accepted; if
     output-valid never asserts, no result is ever consumed; if key-expansion-done never
     asserts, encryption never begins.
 (U) Privileged mode, override, bypass or injection path?
     NO -- and this is the one answer that differs from P3164 for a structural reason.
     P3164 answered YES because "the debug interface allows the IP to encrypt/decrypt using
     the test key and IV values, which may result in a loss of security strength". This core
     has no debug mode and no hardcoded Debug Values block, so that undermining route does
     not exist here.

Conceptual assets: (a) the cipher key and the round-key schedule derived from it,
(b) the plaintext block, (c) the operating configuration, (d) delivery of the service.

P3164 3.1.2 structural mapping -- P3164 names conceptual assets as BLOCKS; resolve each block
to the concrete elements of this closed set that produce, store or transport it:
     P3164 "Key Reg"       ->  i_key (aes)            key as presented to the core
                           ->  rd_data (ram_16x64)    expanded round keys read back from the
                                                      key RAM; the RTL forms the applied
                                                      round key as {rd_data0, rd_data1}
     P3164 "Input Buffer"  ->  i_data (aes)
     P3164 "Config Regs"   ->  ende (sbox)            encrypt/decrypt operation select
                           ->  enable (sbox)          operation enable reaching the datapath
                           ->  key_start (key_exp)    starts the key-schedule build
     P3164 "Status Regs"   ->  key_ready (key_exp), o_data_valid (aes), o_ready (aes),
                               i_data_valid (aes)
     P3164 "Enc/Dec Engine"->  the shared round datapath (sbox / mix_columns / shift_rows)
     P3164 "Output Buffer" ->  o_data (aes) -- present in the design but NOT in the reference
                               asset list used here
     P3164 "IV Reg", "Debug Values" -> no counterpart exists in this design

Objective per element, following P3164's own per-block verdicts:
  Confidentiality -- i_key, rd_data, i_data. These are the designated secret material
      P3164 identifies for a crypto IP: the key, the key schedule derived from it, and the
      plaintext. Disclosure defeats the cipher regardless of algorithmic strength.
  Integrity -- ende, enable, key_start. P3164 places configuration under integrity: it "should
      not be modified" while the engine operates. A flipped mode select silently decrypts when
      encryption was asked for; a disturbed enable or start corrupts the schedule build. These
      are values the datapath believes and acts on, so integrity dominates even though
      clearing them also stops the core -- that denial-of-service consequence is recorded in
      each Justification rather than becoming a second asset.
  Availability -- key_ready, o_ready, o_data_valid, i_data_valid. These are the flow-control
      signals a consumer waits on. Stuck or suppressed, they answer P3164's (A) question
      directly: operational behaviour is prohibited without any value being corrupted.

NON-assets: clk and reset are infrastructure. i_key_mode selects key length but is not in the
reference list. The round datapath internals (sbox partials, mix-columns products,
shift-rows permutations, the key-schedule word registers w0..w7, the round and state
counters) carry conceptual assets (a) and (b) through the pipeline and belong to the later
secondary-asset stage. The key RAM write path (wr, wr_addr, wr_data) builds the schedule that
rd_data later returns, and is likewise secondary to it.

EMITTED OUTPUT:
{
 "IP": "aes_highthroughput_lowarea",
 "Assets": [
  {
   "Asset Name": "Cipher key input",
   "Asset RTL": "i_key",
   "Entity": "aes",
   "Functionality": "256-bit input key (upper bits unused for smaller keys)",
   "Security Objective": "Confidentiality",
   "Justification": "P3164 3.2.3 makes the key value a secret of a crypto IP: \\"the plaintext data and key values are secrets\\". This port carries the long-term key into the core; disclosure compromises every block encrypted under it regardless of algorithmic strength. Its integrity also matters during operation, but disclosure is the dominant risk for key material."
  },
  {
   "Asset Name": "Round key read from the key RAM",
   "Asset RTL": "rd_data",
   "Entity": "ram_16x64",
   "Functionality": "64-bit output data bus presenting read memory word",
   "Security Objective": "Confidentiality",
   "Justification": "The expanded key schedule is stored in the on-chip key RAM and read back each round; the RTL forms the applied round key as {rd_data0, rd_data1}. Round keys are key-equivalent -- recovering them recovers the cipher key -- so this read port is the stored form of the same secret P3164 assigns to the Key Reg."
  },
  {
   "Asset Name": "Plaintext block input",
   "Asset RTL": "i_data",
   "Entity": "aes",
   "Functionality": "128-bit plaintext/ciphertext data input",
   "Security Objective": "Confidentiality",
   "Justification": "P3164 names the Input Buffer a conceptual asset because \\"the plaintext data ... are secrets\\". This port carries the private block the core exists to protect; observation at or before the boundary discloses it directly. Modification also corrupts the result, but the material is secret, so confidentiality dominates."
  },
  {
   "Asset Name": "Encryption/decryption mode select",
   "Asset RTL": "ende",
   "Entity": "sbox",
   "Functionality": "mode select: 0 encrypt, 1 decrypt",
   "Security Objective": "Integrity",
   "Justification": "P3164 Table 1 lists \\"operation\\" as Configuration, and 3.2.3 requires that configuration \\"should not be modified\\" while the engine operates. This select chooses the forward or inverse S-box; flipping it silently decrypts when encryption was requested, producing a wrong result with no error reported. Suppressing it also stalls the substitution stage, but the value is believed and acted on, so integrity dominates."
  },
  {
   "Asset Name": "Substitution stage operation enable",
   "Asset RTL": "enable",
   "Entity": "sbox",
   "Functionality": "enable pipeline registers/process",
   "Security Objective": "Integrity",
   "Justification": "The operation enable reaching the datapath; P3164 places start/stop control under Configuration and requires its integrity during operation. A disturbed enable admits or drops substitution cycles, corrupting the block being processed. The fact that clearing it also halts the core is a denial-of-service consequence, not the dominant objective."
  },
  {
   "Asset Name": "Key expansion start",
   "Asset RTL": "key_start",
   "Entity": "key_exp",
   "Functionality": "pulse to start key expansion procedure",
   "Security Objective": "Integrity",
   "Justification": "Starts the build of the round-key schedule. P3164 treats start/stop as Configuration requiring integrity; a spurious or mistimed start rebuilds or truncates the schedule while data is in flight, so subsequent rounds apply wrong round keys and the ciphertext is silently wrong."
  },
  {
   "Asset Name": "Key expansion done indication",
   "Asset RTL": "key_ready",
   "Entity": "key_exp",
   "Functionality": "indicates key expansion finished and ready",
   "Security Objective": "Availability",
   "Justification": "P3164 asks under (A) whether an element, if unavailable, can prohibit operational behaviour. Encryption cannot begin until the schedule is built and this indication is raised; if it never asserts the core never proceeds, and if it asserts early the datapath runs against an incomplete schedule. The consumer waits on it, so availability is the dominant objective."
  },
  {
   "Asset Name": "Ready for new input data",
   "Asset RTL": "o_ready",
   "Entity": "aes",
   "Functionality": "core ready for new input next cycle",
   "Security Objective": "Availability",
   "Justification": "Signals that the core can accept a new block on the next cycle. Held low, no block is ever accepted and the encryption service is denied without any value being corrupted -- P3164's (A) question answered directly."
  },
  {
   "Asset Name": "Output data valid",
   "Asset RTL": "o_data_valid",
   "Entity": "aes",
   "Functionality": "data output valid strobe",
   "Security Objective": "Availability",
   "Justification": "Marks a result as available on the output port. Suppressed, results are never consumed and the service is denied; asserted spuriously, the consumer latches a stale block. The consumer waits on this signal, so availability dominates."
  },
  {
   "Asset Name": "Input data valid",
   "Asset RTL": "i_data_valid",
   "Entity": "aes",
   "Functionality": "input data valid strobe",
   "Security Objective": "Availability",
   "Justification": "The handshake by which a block is offered to the core. Suppressed, no work is ever accepted and operation is prohibited, which is P3164's (A) criterion; the core also acts on it to latch the input, so its corruption has an integrity consequence recorded here."
  }
 ]
}
"""


# ---------------------------------------------------------------------------
# Splice by CONCATENATION -- the examples contain literal JSON braces.
#   ASSET_PRIMARY_SYSTEM = ASSET_PRIMARY_CORE + "\n\n" + ICL_ASSET_EXAMPLES_02
# ---------------------------------------------------------------------------

ICL_ASSET_EXAMPLES_02 = (
    "The following worked case studies show the complete task: the inputs you receive, the "
    "IEEE P3164 reasoning that turns them into conceptual assets, the structural mapping "
    "that binds each conceptual asset to a named element of the closed set, and the object "
    "to emit. Reproduce the DISCIPLINE -- answer all four rubric questions with a reason, "
    "state the non-asset decisions explicitly, bind every asset to an exact name from the "
    "closed set you are given, and give each one exactly one dominant Security Objective "
    "with any secondary consequence noted in the Justification. The CSA ANALYSIS block is "
    "internal: emit only the final JSON object.\n\n"
    + EXAMPLE_01_OMSP_GPIO + "\n" + EXAMPLE_02_AES_HT
)

if __name__ == "__main__":
    print(ICL_ASSET_EXAMPLES_02)
