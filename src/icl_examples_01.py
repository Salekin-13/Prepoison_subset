"""icl_examples_01.py -- worked input/output ICL examples with P3164 reasoning.

Unlike icl_examples_0.py (which reproduces IEEE P3164's own block-diagram analyses at the
standard's level of abstraction), this file gives a COMPLETE input -> reasoning -> output
triples in exactly the shape the runtime task uses, built from published sources.

EXAMPLE 1 -- omsp_gpio (openMSP430 digital I/O)   14 assets, all Integrity
EXAMPLE 2 -- tiny_aes (unrolled AES-128 core)      4 assets, 3 Confidentiality + 1 Availability
Both are from the LAsset IP benchmark set, so neither leaks a NEORV32 module.
Together they cover all three security objectives.

PROVENANCE -- what is sourced vs. what is written here
  PARSED I/O PORTS / INTERNAL SIGNALS   extracted from the LAsset repo RTL. For omsp_gpio
                                        every `function` string comes from the module's
                                        specification tables; for tiny_aes (no spec exists)
                                        they are derived from the RTL structure, which is
                                        what the annotation stage does at runtime.
  RTL                                   the COMPLETE file, comments stripped.
  EMITTED OUTPUT -- which elements      the 14 MANUALLY identified assets from
                                        Dataset.xlsx, sheet 'Interface-GPIO_asset',
                                        column 'Asset List (Manual)' -- the human reference
                                        labels published with Nath & Tan, ISQED 2025
                                        (github.com/CalgaryISH/Asset_Dataset_using_PKG).
  EMITTED OUTPUT -- Asset Name,         asset_list_omsp_gpio_final.json (LAsset release).
                    Functionality,
                    Security Objective
  EMITTED OUTPUT -- Justification       asset_list_omsp_gpio_initial.json (LAsset release).
  TECHNICAL SUMMARY                     written here, condensed from the omsp_gpio
                                        specification into the 5-section format this
                                        pipeline's summary stage produces.
  CSA ANALYSIS (reasoning)              written here, applying the IEEE P3164 3.1.1 rubric
                                        and 3.1.2 structural mapping. The (C)/(I)/(A)/(U)
                                        answers follow P3164's own GPIO walkthrough (3.2.1).

WHY THE RTL IS COMPLETE AND COMMENT-STRIPPED. Both examples embed the whole source file,
not an excerpt, with comments removed -- byte-for-byte the form the asset stage now
receives, because generate_assets() applies rtl_parse.strip_comments() before prompting.
(Stripping is applied at the ASSET stage only: the port/signal ANNOTATION prompt is
explicitly told to use in-source comments, so it still gets the raw file.) An earlier
draft carried hand-added "<-- this is the asset" markers; those were removed, because
they taught the model to expect signposts that do not exist at runtime.

CROSS-VALIDATION AGAINST IEEE P3164 3.2.1
  P3164 GPIO      omsp_gpio (this example)                       agree?
  (C) NO          no Confidentiality asset among the 14          yes
  (I) YES,        p1_sel..p6_sel are the mux; p1_dout_en..       yes -- P3164's "mux gates"
      mux gates   p6_dout_en are the Direction Select                 instantiated per port
  (A) YES,        same elements; emitted as Integrity with the   yes -- P3164 also maps BOTH
      same gates  DoS consequence noted in the Justification           (I) and (A) to one asset
  (U) NO          no privileged/bypass mechanism documented      yes

SCHEMA NOTE. The emitted object follows THIS PIPELINE's contract --
{"IP": ..., "Assets": [{Asset Name, Asset RTL, Entity, Functionality,
Security Objective, Justification}]} -- which is also the shape of the SoC-level
asset_list_neorv32_initial.json. The IP-level asset_list_omsp_gpio_initial.json uses a
different schema (nested under "Verilog/SystemVerilog Modules", carries "Secondary Assets",
and has no "Entity"); its Justification text is reused here, but its structure is
deliberately NOT copied, because "Secondary Assets" belong to a later stage and "Entity" is
required by the primary-asset contract and by validate_primary().

EXAMPLE 2 -- tiny_aes, ADDITIONAL NOTES

  Why tiny_aes: it is the only AES among the 21 IPs in the LAsset benchmark set, and its
  manual reference labels exist in the same Dataset.xlsx sheet family used for Example 1.

  Sources: elements from Dataset.xlsx 'Crypto_asset' -> tiny_aes_latest, Asset List
  (Manual) = [key, state_in, key_in, state_out]. Asset Name / Functionality / Security
  Objective / Justification from asset_list_tiny_aes_initial.json (that file is malformed
  JSON -- trailing commas -- so it is read with a regex, and Entity is taken from the
  enclosing "Verilog/SystemVerilog Module" block).

  Entity binding: `key` is bound at aes_128, where the cipher key enters the design --
  the attribution asset_list_tiny_aes_final.json itself uses ("key (aes_128)"). The other
  three are bound in final_round, the one entity where all three co-exist. tiny_aes is a
  9-entity design that reuses names across entities (clk, key, state_in, state_out, in,
  out, s0..s3, k0..k3), which is why every check here is keyed by (entity, name) -- the
  same rule validate_primary() uses, and the reason verify_icl.py was corrected.

  CROSS-VALIDATION AGAINST IEEE P3164 3.2.3
    P3164's AES is a full crypto peripheral (Config Regs, Status Regs, Key Reg, IV Reg,
    Input/Output Buffers, Enc/Dec Engine, Debug). tiny_aes is the cipher datapath only.
      (C) YES in both. P3164: "the plaintext data and key values are secrets ... any block
          that supports these secrets will be a conceptual asset." -> key, key_in, state_in.
      (I) YES in both, narrower here: no IV and no configuration exist to protect, so
          integrity attaches to the key and state paths (recorded inside the state_in
          Justification, with Confidentiality dominant).
      (A) YES in both, by a DIFFERENT route: P3164 reaches availability through the debug
          interface blocking Data_Out; tiny_aes has no debug interface, so availability
          attaches to the ciphertext output the consumer waits on.
      (U) P3164 YES, tiny_aes NO -- P3164's undermining path is the debug interface
          substituting a test key/IV, and tiny_aes has no debug mode at all.
    The two (A)/(U) divergences follow from the designs differing, which is the CSA method
    behaving correctly; no P3164 verdict is contradicted.

  INDEPENDENT CORROBORATION (peer-reviewed, verified by reading the papers)
    Transys (Zhang & Sturton, IEEE S&P 2020) states security properties over named AES
    signals and independently agrees with P3164 and with these labels: "The key should
    never be altered" (key integrity); the IFT assertion "set key[0] := high; assert
    cipher[0] == high" (key confidentiality, ciphertext as the authorised sink); and "the
    round constant for each round of the key expansion should be correct" (rcon integrity,
    matching LAsset's rcon = Integrity). Its element vocabulary overlaps tiny_aes on key,
    state, out, rcon and key_in.
    Nath & Tan (ISQED 2025) supplies the MANUAL LABELS used here, but it does NOT support
    the conceptual step: it is a structural classifier (partial keywords plus control /
    configuration / status / data signal categories) with no CIA objectives and no rubric.
    It is cited for the reference list, not for the reasoning.

  SCOPE CAVEAT. P3164 is maximally inclusive for crypto IPs -- "every block in the IP,
  except the Debug Values block, can be considered a conceptual asset" -- and then notes
  the result "may be too numerous to comprehend". LAsset's own initial list for tiny_aes
  has 14 assets; the manual reference keeps 4, the canonical representative of each
  conceptual asset where it enters, is applied, or leaves the cipher. The example follows
  the manual reference, so it is markedly sparser than P3164's stance would imply
  (4 of 142 elements = 3%, against GPIO's 14 of 67 = 21%).

KNOWN LIMITATIONS (Example 1).
  * All 14 reference assets carry the Integrity objective. Example 2 supplies the
    Confidentiality and Availability cases. The two Availability assets LAsset
    identifies for this module (irq_port1, irq_port2) are absent from the manual reference
    list and are therefore not emitted.
  * The example emits 14 assets from a 67-element closed set (21%). NEORV32 ground truth
    runs near 7%, so this example teaches a denser-than-target emission rate. That suits a
    recall-first generation stage but should be watched if precision regresses.
  * The RTL is Verilog while the NEORV32 target modules are VHDL. Converting it was
    considered and rejected: the 14 reference labels were produced against this Verilog, so
    a hand-converted VHDL version would be a fabricated artifact with no provenance. The
    closed-set block, where binding actually happens, is language-neutral in structure.
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


EXAMPLE_02_TINY_AES = """\
### CASE STUDY 2: tiny_aes (unrolled AES-128 encryption core)

TARGET IP MODULE: tiny_aes

=== TECHNICAL SUMMARY ===
MODULE: tiny_aes
1. FUNCTION AND ROLE
Fully unrolled AES-128 encryption core. A 128-bit plaintext block and a 128-bit cipher key
enter together; the key is XORed into the plaintext for the initial AddRoundKey while a
ten-stage key expansion derives one round key per round. Nine identical cipher rounds and a
final round then transform the state into the ciphertext. Every stage is registered, so the
design is a deep pipeline that accepts a new block each cycle. Substitution is implemented by
T-table/S-box lookup submodules.
2. REGISTERS, CSRS, AND FLAGS
Not documented for this module. The core exposes no memory-mapped register interface: there
are no control, status, mode or interrupt registers. Its only state is the pipeline registers
holding the evolving cipher state and key schedule.
3. CONFIGURATION
Not documented for this module. Key length, round count and the round constants are fixed in
the structure of the design; there are no generics, parameters or run-time configuration.
4. CROSS-MODULE INTERACTION
The core has no bus interface, no interrupt line and no configuration or debug port. It
connects to the rest of a system only through its data ports: the integrator supplies the
plaintext block and the cipher key and consumes the ciphertext block, with the clock shared
from the surrounding design. Whatever protects the key before it reaches this port, and
whatever consumes the ciphertext afterwards, lies outside this module.
5. SECURITY-RELEVANT BEHAVIOR
Security-critical by function: the module exists to protect data, and both of its inputs are
secret material. The cipher key is a long-term secret and the input block is private
plaintext. No access control, privilege level, lock or key-clearing mechanism is documented
or implemented; the key is presented on a port and propagates through the key-expansion
pipeline, so key-derived material is held in registers at every stage for the duration of the
pipeline. There is no debug or test mode, so no path exists to substitute a test key, observe
intermediate state, or halt the datapath from outside. Correct ciphertext depends on the
round keys and round constants being exactly right; a wrong round constant or round key
silently produces a wrong result rather than an error.

=== PARSED I/O PORTS (JSON) ===
[
 {
  "entity": "aes_128",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "Pipeline clock; every round stage registers on its rising edge."
 },
 {
  "entity": "aes_128",
  "name": "state",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "128-bit plaintext block entering the cipher."
 },
 {
  "entity": "aes_128",
  "name": "key",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "128-bit cipher key; XORed with the plaintext for the initial AddRoundKey and fed to the key expansion."
 },
 {
  "entity": "aes_128",
  "name": "out",
  "dir": "output",
  "type": "wire[127:0]",
  "function": "128-bit ciphertext block produced by the final round."
 },
 {
  "entity": "expand_key_128",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "Clock for the registered round-key output."
 },
 {
  "entity": "expand_key_128",
  "name": "in",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "Previous round key entering this key-expansion stage."
 },
 {
  "entity": "expand_key_128",
  "name": "rcon",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Round constant for this expansion stage; fixes the round's key schedule."
 },
 {
  "entity": "expand_key_128",
  "name": "out_1",
  "dir": "output",
  "type": "wire[127:0]",
  "function": "Registered next round key, passed to the following expansion stage."
 },
 {
  "entity": "expand_key_128",
  "name": "out_2",
  "dir": "output",
  "type": "wire[127:0]",
  "function": "Round key presented to the round datapath for AddRoundKey."
 },
 {
  "entity": "one_round",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "Clock registering this round's output state."
 },
 {
  "entity": "one_round",
  "name": "state_in",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "128-bit state entering this cipher round."
 },
 {
  "entity": "one_round",
  "name": "key",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "128-bit round key applied by this round's AddRoundKey."
 },
 {
  "entity": "one_round",
  "name": "state_out",
  "dir": "output",
  "type": "wire[127:0]",
  "function": "128-bit state leaving this cipher round."
 },
 {
  "entity": "final_round",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "Clock registering the final-round output."
 },
 {
  "entity": "final_round",
  "name": "state_in",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "128-bit state entering the final AES round."
 },
 {
  "entity": "final_round",
  "name": "key_in",
  "dir": "input",
  "type": "wire[127:0]",
  "function": "128-bit round key applied in the final AddRoundKey."
 },
 {
  "entity": "final_round",
  "name": "state_out",
  "dir": "output",
  "type": "wire[127:0]",
  "function": "128-bit ciphertext registered at the end of the final round."
 },
 {
  "entity": "table_lookup",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "Clock for the registered table outputs."
 },
 {
  "entity": "table_lookup",
  "name": "state",
  "dir": "input",
  "type": "wire[31:0]",
  "function": "32-bit state word entering the T-table substitution."
 },
 {
  "entity": "table_lookup",
  "name": "p0",
  "dir": "output",
  "type": "wire[31:0]",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "table_lookup",
  "name": "p1",
  "dir": "output",
  "type": "wire[31:0]",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "table_lookup",
  "name": "p2",
  "dir": "output",
  "type": "wire[31:0]",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "table_lookup",
  "name": "p3",
  "dir": "output",
  "type": "wire[31:0]",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "S4",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "Clock."
 },
 {
  "entity": "S4",
  "name": "in",
  "dir": "input",
  "type": "wire[31:0]",
  "function": "Input word to this substitution stage."
 },
 {
  "entity": "S4",
  "name": "out",
  "dir": "output",
  "type": "wire[31:0]",
  "function": "Registered output of this substitution stage."
 },
 {
  "entity": "T",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "Clock."
 },
 {
  "entity": "T",
  "name": "in",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Input word to this substitution stage."
 },
 {
  "entity": "T",
  "name": "out",
  "dir": "output",
  "type": "wire[31:0]",
  "function": "Registered output of this substitution stage."
 },
 {
  "entity": "S",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "Clock."
 },
 {
  "entity": "S",
  "name": "in",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Input word to this substitution stage."
 },
 {
  "entity": "S",
  "name": "out",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Registered output of this substitution stage."
 },
 {
  "entity": "xS",
  "name": "clk",
  "dir": "input",
  "type": "wire",
  "function": "Clock."
 },
 {
  "entity": "xS",
  "name": "in",
  "dir": "input",
  "type": "wire[7:0]",
  "function": "Input word to this substitution stage."
 },
 {
  "entity": "xS",
  "name": "out",
  "dir": "output",
  "type": "wire[7:0]",
  "function": "Registered output of this substitution stage."
 }
]

=== PARSED INTERNAL SIGNALS (JSON) ===
[
 {
  "entity": "aes_128",
  "name": "s0",
  "type": "reg[127:0]",
  "kind": "register",
  "function": "Registered state after the initial AddRoundKey (state XOR key)."
 },
 {
  "entity": "aes_128",
  "name": "k0",
  "type": "reg[127:0]",
  "kind": "register",
  "function": "Registered copy of the cipher key, source of the key expansion chain."
 },
 {
  "entity": "aes_128",
  "name": "s1",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "aes_128",
  "name": "s2",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "aes_128",
  "name": "s3",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "aes_128",
  "name": "s4",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "aes_128",
  "name": "s5",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "aes_128",
  "name": "s6",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "aes_128",
  "name": "s7",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "aes_128",
  "name": "s8",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "aes_128",
  "name": "s9",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "aes_128",
  "name": "k1",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "aes_128",
  "name": "k2",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "aes_128",
  "name": "k3",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "aes_128",
  "name": "k4",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "aes_128",
  "name": "k5",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "aes_128",
  "name": "k6",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "aes_128",
  "name": "k7",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "aes_128",
  "name": "k8",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "aes_128",
  "name": "k9",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "aes_128",
  "name": "k0b",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "aes_128",
  "name": "k1b",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "aes_128",
  "name": "k2b",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "aes_128",
  "name": "k3b",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "aes_128",
  "name": "k4b",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "aes_128",
  "name": "k5b",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "aes_128",
  "name": "k6b",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "aes_128",
  "name": "k7b",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "aes_128",
  "name": "k8b",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "aes_128",
  "name": "k9b",
  "type": "wire[127:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "expand_key_128",
  "name": "k0",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "expand_key_128",
  "name": "k1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "expand_key_128",
  "name": "k2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "expand_key_128",
  "name": "k3",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "expand_key_128",
  "name": "v0",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Intermediate value inside the S-box/xtime network."
 },
 {
  "entity": "expand_key_128",
  "name": "v1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Intermediate value inside the S-box/xtime network."
 },
 {
  "entity": "expand_key_128",
  "name": "v2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Intermediate value inside the S-box/xtime network."
 },
 {
  "entity": "expand_key_128",
  "name": "v3",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Intermediate value inside the S-box/xtime network."
 },
 {
  "entity": "expand_key_128",
  "name": "k0a",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "unclear from RTL"
 },
 {
  "entity": "expand_key_128",
  "name": "k1a",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "unclear from RTL"
 },
 {
  "entity": "expand_key_128",
  "name": "k2a",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "unclear from RTL"
 },
 {
  "entity": "expand_key_128",
  "name": "k3a",
  "type": "reg[31:0]",
  "kind": "register",
  "function": "unclear from RTL"
 },
 {
  "entity": "expand_key_128",
  "name": "k0b",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "expand_key_128",
  "name": "k1b",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "expand_key_128",
  "name": "k2b",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "expand_key_128",
  "name": "k3b",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round key delivered to the corresponding cipher round."
 },
 {
  "entity": "expand_key_128",
  "name": "k4a",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "unclear from RTL"
 },
 {
  "entity": "one_round",
  "name": "s0",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "one_round",
  "name": "s1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "one_round",
  "name": "s2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "one_round",
  "name": "s3",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "one_round",
  "name": "z0",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Column result after substitution and AddRoundKey."
 },
 {
  "entity": "one_round",
  "name": "z1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Column result after substitution and AddRoundKey."
 },
 {
  "entity": "one_round",
  "name": "z2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Column result after substitution and AddRoundKey."
 },
 {
  "entity": "one_round",
  "name": "z3",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Column result after substitution and AddRoundKey."
 },
 {
  "entity": "one_round",
  "name": "p00",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p01",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p02",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p03",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p10",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p11",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p12",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p13",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p20",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p21",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p22",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p23",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p30",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p31",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p32",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "p33",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "one_round",
  "name": "k0",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "one_round",
  "name": "k1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "one_round",
  "name": "k2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "one_round",
  "name": "k3",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "final_round",
  "name": "s0",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "final_round",
  "name": "s1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "final_round",
  "name": "s2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "final_round",
  "name": "s3",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Round state word between cipher stages."
 },
 {
  "entity": "final_round",
  "name": "z0",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Column result after substitution and AddRoundKey."
 },
 {
  "entity": "final_round",
  "name": "z1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Column result after substitution and AddRoundKey."
 },
 {
  "entity": "final_round",
  "name": "z2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Column result after substitution and AddRoundKey."
 },
 {
  "entity": "final_round",
  "name": "z3",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Column result after substitution and AddRoundKey."
 },
 {
  "entity": "final_round",
  "name": "k0",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "final_round",
  "name": "k1",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "final_round",
  "name": "k2",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "final_round",
  "name": "k3",
  "type": "wire[31:0]",
  "kind": "signal",
  "function": "Key-schedule word between expansion stages."
 },
 {
  "entity": "final_round",
  "name": "p00",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p01",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p02",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p03",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p10",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p11",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p12",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p13",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p20",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p21",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p22",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p23",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p30",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p31",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p32",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "final_round",
  "name": "p33",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "Partial substitution result from the S-box/T-table."
 },
 {
  "entity": "table_lookup",
  "name": "b0",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "unclear from RTL"
 },
 {
  "entity": "table_lookup",
  "name": "b1",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "unclear from RTL"
 },
 {
  "entity": "table_lookup",
  "name": "b2",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "unclear from RTL"
 },
 {
  "entity": "table_lookup",
  "name": "b3",
  "type": "wire[7:0]",
  "kind": "signal",
  "function": "unclear from RTL"
 }
]

=== RTL ===
module aes_128(clk, state, key, out);
    input          clk;
    input  [127:0] state, key;
    output [127:0] out;
    reg    [127:0] s0, k0;
    wire   [127:0] s1, s2, s3, s4, s5, s6, s7, s8, s9,
                   k1, k2, k3, k4, k5, k6, k7, k8, k9,
                   k0b, k1b, k2b, k3b, k4b, k5b, k6b, k7b, k8b, k9b;
    always @ (posedge clk)
      begin
        s0 <= state ^ key;
        k0 <= key;
      end
    expand_key_128
        a1 (clk, k0, k1, k0b, 8'h1),
        a2 (clk, k1, k2, k1b, 8'h2),
        a3 (clk, k2, k3, k2b, 8'h4),
        a4 (clk, k3, k4, k3b, 8'h8),
        a5 (clk, k4, k5, k4b, 8'h10),
        a6 (clk, k5, k6, k5b, 8'h20),
        a7 (clk, k6, k7, k6b, 8'h40),
        a8 (clk, k7, k8, k7b, 8'h80),
        a9 (clk, k8, k9, k8b, 8'h1b),
       a10 (clk, k9,   , k9b, 8'h36);
    one_round
        r1 (clk, s0, k0b, s1),
        r2 (clk, s1, k1b, s2),
        r3 (clk, s2, k2b, s3),
        r4 (clk, s3, k3b, s4),
        r5 (clk, s4, k4b, s5),
        r6 (clk, s5, k5b, s6),
        r7 (clk, s6, k6b, s7),
        r8 (clk, s7, k7b, s8),
        r9 (clk, s8, k8b, s9);
    final_round
        rf (clk, s9, k9b, out);
endmodule
module expand_key_128(clk, in, out_1, out_2, rcon);
    input              clk;
    input      [127:0] in;
    input      [7:0]   rcon;
    output reg [127:0] out_1;
    output     [127:0] out_2;
    wire       [31:0]  k0, k1, k2, k3,
                       v0, v1, v2, v3;
    reg        [31:0]  k0a, k1a, k2a, k3a;
    wire       [31:0]  k0b, k1b, k2b, k3b, k4a;
    assign {k0, k1, k2, k3} = in;
    assign v0 = {k0[31:24] ^ rcon, k0[23:0]};
    assign v1 = v0 ^ k1;
    assign v2 = v1 ^ k2;
    assign v3 = v2 ^ k3;
    always @ (posedge clk)
        {k0a, k1a, k2a, k3a} <= {v0, v1, v2, v3};
    S4
        S4_0 (clk, {k3[23:0], k3[31:24]}, k4a);
    assign k0b = k0a ^ k4a;
    assign k1b = k1a ^ k4a;
    assign k2b = k2a ^ k4a;
    assign k3b = k3a ^ k4a;
    always @ (posedge clk)
        out_1 <= {k0b, k1b, k2b, k3b};
    assign out_2 = {k0b, k1b, k2b, k3b};
endmodule
module one_round (clk, state_in, key, state_out);
    input              clk;
    input      [127:0] state_in, key;
    output reg [127:0] state_out;
    wire       [31:0]  s0,  s1,  s2,  s3,
                       z0,  z1,  z2,  z3,
                       p00, p01, p02, p03,
                       p10, p11, p12, p13,
                       p20, p21, p22, p23,
                       p30, p31, p32, p33,
                       k0,  k1,  k2,  k3;
    assign {k0, k1, k2, k3} = key;
    assign {s0, s1, s2, s3} = state_in;
    table_lookup
        t0 (clk, s0, p00, p01, p02, p03),
        t1 (clk, s1, p10, p11, p12, p13),
        t2 (clk, s2, p20, p21, p22, p23),
        t3 (clk, s3, p30, p31, p32, p33);
    assign z0 = p00 ^ p11 ^ p22 ^ p33 ^ k0;
    assign z1 = p03 ^ p10 ^ p21 ^ p32 ^ k1;
    assign z2 = p02 ^ p13 ^ p20 ^ p31 ^ k2;
    assign z3 = p01 ^ p12 ^ p23 ^ p30 ^ k3;
    always @ (posedge clk)
        state_out <= {z0, z1, z2, z3};
endmodule
module final_round (clk, state_in, key_in, state_out);
    input              clk;
    input      [127:0] state_in;
    input      [127:0] key_in;
    output reg [127:0] state_out;
    wire [31:0] s0,  s1,  s2,  s3,
                z0,  z1,  z2,  z3,
                k0,  k1,  k2,  k3;
    wire [7:0]  p00, p01, p02, p03,
                p10, p11, p12, p13,
                p20, p21, p22, p23,
                p30, p31, p32, p33;
    assign {k0, k1, k2, k3} = key_in;
    assign {s0, s1, s2, s3} = state_in;
    S4
        S4_1 (clk, s0, {p00, p01, p02, p03}),
        S4_2 (clk, s1, {p10, p11, p12, p13}),
        S4_3 (clk, s2, {p20, p21, p22, p23}),
        S4_4 (clk, s3, {p30, p31, p32, p33});
    assign z0 = {p00, p11, p22, p33} ^ k0;
    assign z1 = {p10, p21, p32, p03} ^ k1;
    assign z2 = {p20, p31, p02, p13} ^ k2;
    assign z3 = {p30, p01, p12, p23} ^ k3;
    always @ (posedge clk)
        state_out <= {z0, z1, z2, z3};
endmodule
module table_lookup (clk, state, p0, p1, p2, p3);
    input clk;
    input [31:0] state;
    output [31:0] p0, p1, p2, p3;
    wire [7:0] b0, b1, b2, b3;
    assign {b0, b1, b2, b3} = state;
    T
        t0 (clk, b0, {p0[23:0], p0[31:24]}),
        t1 (clk, b1, {p1[15:0], p1[31:16]}),
        t2 (clk, b2, {p2[7:0],  p2[31:8]} ),
        t3 (clk, b3, p3);
endmodule
module S4 (clk, in, out);
    input clk;
    input [31:0] in;
    output [31:0] out;
    S
        S_0 (clk, in[31:24], out[31:24]),
        S_1 (clk, in[23:16], out[23:16]),
        S_2 (clk, in[15:8],  out[15:8] ),
        S_3 (clk, in[7:0],   out[7:0]  );
endmodule
module T (clk, in, out);
    input         clk;
    input  [7:0]  in;
    output [31:0] out;
    S
        s0 (clk, in, out[31:24]);
    assign out[23:16] = out[31:24];
    xS
        s4 (clk, in, out[7:0]);
    assign out[15:8] = out[23:16] ^ out[7:0];
endmodule
module S (clk, in, out);
    input clk;
    input [7:0] in;
    output reg [7:0] out;
    always @ (posedge clk)
    case (in)
    8'h00: out <= 8'h63;
    8'h01: out <= 8'h7c;
    8'h02: out <= 8'h77;
    8'h03: out <= 8'h7b;
    8'h04: out <= 8'hf2;
    8'h05: out <= 8'h6b;
    8'h06: out <= 8'h6f;
    8'h07: out <= 8'hc5;
    8'h08: out <= 8'h30;
    8'h09: out <= 8'h01;
    8'h0a: out <= 8'h67;
    8'h0b: out <= 8'h2b;
    8'h0c: out <= 8'hfe;
    8'h0d: out <= 8'hd7;
    8'h0e: out <= 8'hab;
    8'h0f: out <= 8'h76;
    8'h10: out <= 8'hca;
    8'h11: out <= 8'h82;
    8'h12: out <= 8'hc9;
    8'h13: out <= 8'h7d;
    8'h14: out <= 8'hfa;
    8'h15: out <= 8'h59;
    8'h16: out <= 8'h47;
    8'h17: out <= 8'hf0;
    8'h18: out <= 8'had;
    8'h19: out <= 8'hd4;
    8'h1a: out <= 8'ha2;
    8'h1b: out <= 8'haf;
    8'h1c: out <= 8'h9c;
    8'h1d: out <= 8'ha4;
    8'h1e: out <= 8'h72;
    8'h1f: out <= 8'hc0;
    8'h20: out <= 8'hb7;
    8'h21: out <= 8'hfd;
    8'h22: out <= 8'h93;
    8'h23: out <= 8'h26;
    8'h24: out <= 8'h36;
    8'h25: out <= 8'h3f;
    8'h26: out <= 8'hf7;
    8'h27: out <= 8'hcc;
    8'h28: out <= 8'h34;
    8'h29: out <= 8'ha5;
    8'h2a: out <= 8'he5;
    8'h2b: out <= 8'hf1;
    8'h2c: out <= 8'h71;
    8'h2d: out <= 8'hd8;
    8'h2e: out <= 8'h31;
    8'h2f: out <= 8'h15;
    8'h30: out <= 8'h04;
    8'h31: out <= 8'hc7;
    8'h32: out <= 8'h23;
    8'h33: out <= 8'hc3;
    8'h34: out <= 8'h18;
    8'h35: out <= 8'h96;
    8'h36: out <= 8'h05;
    8'h37: out <= 8'h9a;
    8'h38: out <= 8'h07;
    8'h39: out <= 8'h12;
    8'h3a: out <= 8'h80;
    8'h3b: out <= 8'he2;
    8'h3c: out <= 8'heb;
    8'h3d: out <= 8'h27;
    8'h3e: out <= 8'hb2;
    8'h3f: out <= 8'h75;
    8'h40: out <= 8'h09;
    8'h41: out <= 8'h83;
    8'h42: out <= 8'h2c;
    8'h43: out <= 8'h1a;
    8'h44: out <= 8'h1b;
    8'h45: out <= 8'h6e;
    8'h46: out <= 8'h5a;
    8'h47: out <= 8'ha0;
    8'h48: out <= 8'h52;
    8'h49: out <= 8'h3b;
    8'h4a: out <= 8'hd6;
    8'h4b: out <= 8'hb3;
    8'h4c: out <= 8'h29;
    8'h4d: out <= 8'he3;
    8'h4e: out <= 8'h2f;
    8'h4f: out <= 8'h84;
    8'h50: out <= 8'h53;
    8'h51: out <= 8'hd1;
    8'h52: out <= 8'h00;
    8'h53: out <= 8'hed;
    8'h54: out <= 8'h20;
    8'h55: out <= 8'hfc;
    8'h56: out <= 8'hb1;
    8'h57: out <= 8'h5b;
    8'h58: out <= 8'h6a;
    8'h59: out <= 8'hcb;
    8'h5a: out <= 8'hbe;
    8'h5b: out <= 8'h39;
    8'h5c: out <= 8'h4a;
    8'h5d: out <= 8'h4c;
    8'h5e: out <= 8'h58;
    8'h5f: out <= 8'hcf;
    8'h60: out <= 8'hd0;
    8'h61: out <= 8'hef;
    8'h62: out <= 8'haa;
    8'h63: out <= 8'hfb;
    8'h64: out <= 8'h43;
    8'h65: out <= 8'h4d;
    8'h66: out <= 8'h33;
    8'h67: out <= 8'h85;
    8'h68: out <= 8'h45;
    8'h69: out <= 8'hf9;
    8'h6a: out <= 8'h02;
    8'h6b: out <= 8'h7f;
    8'h6c: out <= 8'h50;
    8'h6d: out <= 8'h3c;
    8'h6e: out <= 8'h9f;
    8'h6f: out <= 8'ha8;
    8'h70: out <= 8'h51;
    8'h71: out <= 8'ha3;
    8'h72: out <= 8'h40;
    8'h73: out <= 8'h8f;
    8'h74: out <= 8'h92;
    8'h75: out <= 8'h9d;
    8'h76: out <= 8'h38;
    8'h77: out <= 8'hf5;
    8'h78: out <= 8'hbc;
    8'h79: out <= 8'hb6;
    8'h7a: out <= 8'hda;
    8'h7b: out <= 8'h21;
    8'h7c: out <= 8'h10;
    8'h7d: out <= 8'hff;
    8'h7e: out <= 8'hf3;
    8'h7f: out <= 8'hd2;
    8'h80: out <= 8'hcd;
    8'h81: out <= 8'h0c;
    8'h82: out <= 8'h13;
    8'h83: out <= 8'hec;
    8'h84: out <= 8'h5f;
    8'h85: out <= 8'h97;
    8'h86: out <= 8'h44;
    8'h87: out <= 8'h17;
    8'h88: out <= 8'hc4;
    8'h89: out <= 8'ha7;
    8'h8a: out <= 8'h7e;
    8'h8b: out <= 8'h3d;
    8'h8c: out <= 8'h64;
    8'h8d: out <= 8'h5d;
    8'h8e: out <= 8'h19;
    8'h8f: out <= 8'h73;
    8'h90: out <= 8'h60;
    8'h91: out <= 8'h81;
    8'h92: out <= 8'h4f;
    8'h93: out <= 8'hdc;
    8'h94: out <= 8'h22;
    8'h95: out <= 8'h2a;
    8'h96: out <= 8'h90;
    8'h97: out <= 8'h88;
    8'h98: out <= 8'h46;
    8'h99: out <= 8'hee;
    8'h9a: out <= 8'hb8;
    8'h9b: out <= 8'h14;
    8'h9c: out <= 8'hde;
    8'h9d: out <= 8'h5e;
    8'h9e: out <= 8'h0b;
    8'h9f: out <= 8'hdb;
    8'ha0: out <= 8'he0;
    8'ha1: out <= 8'h32;
    8'ha2: out <= 8'h3a;
    8'ha3: out <= 8'h0a;
    8'ha4: out <= 8'h49;
    8'ha5: out <= 8'h06;
    8'ha6: out <= 8'h24;
    8'ha7: out <= 8'h5c;
    8'ha8: out <= 8'hc2;
    8'ha9: out <= 8'hd3;
    8'haa: out <= 8'hac;
    8'hab: out <= 8'h62;
    8'hac: out <= 8'h91;
    8'had: out <= 8'h95;
    8'hae: out <= 8'he4;
    8'haf: out <= 8'h79;
    8'hb0: out <= 8'he7;
    8'hb1: out <= 8'hc8;
    8'hb2: out <= 8'h37;
    8'hb3: out <= 8'h6d;
    8'hb4: out <= 8'h8d;
    8'hb5: out <= 8'hd5;
    8'hb6: out <= 8'h4e;
    8'hb7: out <= 8'ha9;
    8'hb8: out <= 8'h6c;
    8'hb9: out <= 8'h56;
    8'hba: out <= 8'hf4;
    8'hbb: out <= 8'hea;
    8'hbc: out <= 8'h65;
    8'hbd: out <= 8'h7a;
    8'hbe: out <= 8'hae;
    8'hbf: out <= 8'h08;
    8'hc0: out <= 8'hba;
    8'hc1: out <= 8'h78;
    8'hc2: out <= 8'h25;
    8'hc3: out <= 8'h2e;
    8'hc4: out <= 8'h1c;
    8'hc5: out <= 8'ha6;
    8'hc6: out <= 8'hb4;
    8'hc7: out <= 8'hc6;
    8'hc8: out <= 8'he8;
    8'hc9: out <= 8'hdd;
    8'hca: out <= 8'h74;
    8'hcb: out <= 8'h1f;
    8'hcc: out <= 8'h4b;
    8'hcd: out <= 8'hbd;
    8'hce: out <= 8'h8b;
    8'hcf: out <= 8'h8a;
    8'hd0: out <= 8'h70;
    8'hd1: out <= 8'h3e;
    8'hd2: out <= 8'hb5;
    8'hd3: out <= 8'h66;
    8'hd4: out <= 8'h48;
    8'hd5: out <= 8'h03;
    8'hd6: out <= 8'hf6;
    8'hd7: out <= 8'h0e;
    8'hd8: out <= 8'h61;
    8'hd9: out <= 8'h35;
    8'hda: out <= 8'h57;
    8'hdb: out <= 8'hb9;
    8'hdc: out <= 8'h86;
    8'hdd: out <= 8'hc1;
    8'hde: out <= 8'h1d;
    8'hdf: out <= 8'h9e;
    8'he0: out <= 8'he1;
    8'he1: out <= 8'hf8;
    8'he2: out <= 8'h98;
    8'he3: out <= 8'h11;
    8'he4: out <= 8'h69;
    8'he5: out <= 8'hd9;
    8'he6: out <= 8'h8e;
    8'he7: out <= 8'h94;
    8'he8: out <= 8'h9b;
    8'he9: out <= 8'h1e;
    8'hea: out <= 8'h87;
    8'heb: out <= 8'he9;
    8'hec: out <= 8'hce;
    8'hed: out <= 8'h55;
    8'hee: out <= 8'h28;
    8'hef: out <= 8'hdf;
    8'hf0: out <= 8'h8c;
    8'hf1: out <= 8'ha1;
    8'hf2: out <= 8'h89;
    8'hf3: out <= 8'h0d;
    8'hf4: out <= 8'hbf;
    8'hf5: out <= 8'he6;
    8'hf6: out <= 8'h42;
    8'hf7: out <= 8'h68;
    8'hf8: out <= 8'h41;
    8'hf9: out <= 8'h99;
    8'hfa: out <= 8'h2d;
    8'hfb: out <= 8'h0f;
    8'hfc: out <= 8'hb0;
    8'hfd: out <= 8'h54;
    8'hfe: out <= 8'hbb;
    8'hff: out <= 8'h16;
    endcase
endmodule
module xS (clk, in, out);
    input clk;
    input [7:0] in;
    output reg [7:0] out;
    always @ (posedge clk)
    case (in)
    8'h00: out <= 8'hc6;
    8'h01: out <= 8'hf8;
    8'h02: out <= 8'hee;
    8'h03: out <= 8'hf6;
    8'h04: out <= 8'hff;
    8'h05: out <= 8'hd6;
    8'h06: out <= 8'hde;
    8'h07: out <= 8'h91;
    8'h08: out <= 8'h60;
    8'h09: out <= 8'h02;
    8'h0a: out <= 8'hce;
    8'h0b: out <= 8'h56;
    8'h0c: out <= 8'he7;
    8'h0d: out <= 8'hb5;
    8'h0e: out <= 8'h4d;
    8'h0f: out <= 8'hec;
    8'h10: out <= 8'h8f;
    8'h11: out <= 8'h1f;
    8'h12: out <= 8'h89;
    8'h13: out <= 8'hfa;
    8'h14: out <= 8'hef;
    8'h15: out <= 8'hb2;
    8'h16: out <= 8'h8e;
    8'h17: out <= 8'hfb;
    8'h18: out <= 8'h41;
    8'h19: out <= 8'hb3;
    8'h1a: out <= 8'h5f;
    8'h1b: out <= 8'h45;
    8'h1c: out <= 8'h23;
    8'h1d: out <= 8'h53;
    8'h1e: out <= 8'he4;
    8'h1f: out <= 8'h9b;
    8'h20: out <= 8'h75;
    8'h21: out <= 8'he1;
    8'h22: out <= 8'h3d;
    8'h23: out <= 8'h4c;
    8'h24: out <= 8'h6c;
    8'h25: out <= 8'h7e;
    8'h26: out <= 8'hf5;
    8'h27: out <= 8'h83;
    8'h28: out <= 8'h68;
    8'h29: out <= 8'h51;
    8'h2a: out <= 8'hd1;
    8'h2b: out <= 8'hf9;
    8'h2c: out <= 8'he2;
    8'h2d: out <= 8'hab;
    8'h2e: out <= 8'h62;
    8'h2f: out <= 8'h2a;
    8'h30: out <= 8'h08;
    8'h31: out <= 8'h95;
    8'h32: out <= 8'h46;
    8'h33: out <= 8'h9d;
    8'h34: out <= 8'h30;
    8'h35: out <= 8'h37;
    8'h36: out <= 8'h0a;
    8'h37: out <= 8'h2f;
    8'h38: out <= 8'h0e;
    8'h39: out <= 8'h24;
    8'h3a: out <= 8'h1b;
    8'h3b: out <= 8'hdf;
    8'h3c: out <= 8'hcd;
    8'h3d: out <= 8'h4e;
    8'h3e: out <= 8'h7f;
    8'h3f: out <= 8'hea;
    8'h40: out <= 8'h12;
    8'h41: out <= 8'h1d;
    8'h42: out <= 8'h58;
    8'h43: out <= 8'h34;
    8'h44: out <= 8'h36;
    8'h45: out <= 8'hdc;
    8'h46: out <= 8'hb4;
    8'h47: out <= 8'h5b;
    8'h48: out <= 8'ha4;
    8'h49: out <= 8'h76;
    8'h4a: out <= 8'hb7;
    8'h4b: out <= 8'h7d;
    8'h4c: out <= 8'h52;
    8'h4d: out <= 8'hdd;
    8'h4e: out <= 8'h5e;
    8'h4f: out <= 8'h13;
    8'h50: out <= 8'ha6;
    8'h51: out <= 8'hb9;
    8'h52: out <= 8'h00;
    8'h53: out <= 8'hc1;
    8'h54: out <= 8'h40;
    8'h55: out <= 8'he3;
    8'h56: out <= 8'h79;
    8'h57: out <= 8'hb6;
    8'h58: out <= 8'hd4;
    8'h59: out <= 8'h8d;
    8'h5a: out <= 8'h67;
    8'h5b: out <= 8'h72;
    8'h5c: out <= 8'h94;
    8'h5d: out <= 8'h98;
    8'h5e: out <= 8'hb0;
    8'h5f: out <= 8'h85;
    8'h60: out <= 8'hbb;
    8'h61: out <= 8'hc5;
    8'h62: out <= 8'h4f;
    8'h63: out <= 8'hed;
    8'h64: out <= 8'h86;
    8'h65: out <= 8'h9a;
    8'h66: out <= 8'h66;
    8'h67: out <= 8'h11;
    8'h68: out <= 8'h8a;
    8'h69: out <= 8'he9;
    8'h6a: out <= 8'h04;
    8'h6b: out <= 8'hfe;
    8'h6c: out <= 8'ha0;
    8'h6d: out <= 8'h78;
    8'h6e: out <= 8'h25;
    8'h6f: out <= 8'h4b;
    8'h70: out <= 8'ha2;
    8'h71: out <= 8'h5d;
    8'h72: out <= 8'h80;
    8'h73: out <= 8'h05;
    8'h74: out <= 8'h3f;
    8'h75: out <= 8'h21;
    8'h76: out <= 8'h70;
    8'h77: out <= 8'hf1;
    8'h78: out <= 8'h63;
    8'h79: out <= 8'h77;
    8'h7a: out <= 8'haf;
    8'h7b: out <= 8'h42;
    8'h7c: out <= 8'h20;
    8'h7d: out <= 8'he5;
    8'h7e: out <= 8'hfd;
    8'h7f: out <= 8'hbf;
    8'h80: out <= 8'h81;
    8'h81: out <= 8'h18;
    8'h82: out <= 8'h26;
    8'h83: out <= 8'hc3;
    8'h84: out <= 8'hbe;
    8'h85: out <= 8'h35;
    8'h86: out <= 8'h88;
    8'h87: out <= 8'h2e;
    8'h88: out <= 8'h93;
    8'h89: out <= 8'h55;
    8'h8a: out <= 8'hfc;
    8'h8b: out <= 8'h7a;
    8'h8c: out <= 8'hc8;
    8'h8d: out <= 8'hba;
    8'h8e: out <= 8'h32;
    8'h8f: out <= 8'he6;
    8'h90: out <= 8'hc0;
    8'h91: out <= 8'h19;
    8'h92: out <= 8'h9e;
    8'h93: out <= 8'ha3;
    8'h94: out <= 8'h44;
    8'h95: out <= 8'h54;
    8'h96: out <= 8'h3b;
    8'h97: out <= 8'h0b;
    8'h98: out <= 8'h8c;
    8'h99: out <= 8'hc7;
    8'h9a: out <= 8'h6b;
    8'h9b: out <= 8'h28;
    8'h9c: out <= 8'ha7;
    8'h9d: out <= 8'hbc;
    8'h9e: out <= 8'h16;
    8'h9f: out <= 8'had;
    8'ha0: out <= 8'hdb;
    8'ha1: out <= 8'h64;
    8'ha2: out <= 8'h74;
    8'ha3: out <= 8'h14;
    8'ha4: out <= 8'h92;
    8'ha5: out <= 8'h0c;
    8'ha6: out <= 8'h48;
    8'ha7: out <= 8'hb8;
    8'ha8: out <= 8'h9f;
    8'ha9: out <= 8'hbd;
    8'haa: out <= 8'h43;
    8'hab: out <= 8'hc4;
    8'hac: out <= 8'h39;
    8'had: out <= 8'h31;
    8'hae: out <= 8'hd3;
    8'haf: out <= 8'hf2;
    8'hb0: out <= 8'hd5;
    8'hb1: out <= 8'h8b;
    8'hb2: out <= 8'h6e;
    8'hb3: out <= 8'hda;
    8'hb4: out <= 8'h01;
    8'hb5: out <= 8'hb1;
    8'hb6: out <= 8'h9c;
    8'hb7: out <= 8'h49;
    8'hb8: out <= 8'hd8;
    8'hb9: out <= 8'hac;
    8'hba: out <= 8'hf3;
    8'hbb: out <= 8'hcf;
    8'hbc: out <= 8'hca;
    8'hbd: out <= 8'hf4;
    8'hbe: out <= 8'h47;
    8'hbf: out <= 8'h10;
    8'hc0: out <= 8'h6f;
    8'hc1: out <= 8'hf0;
    8'hc2: out <= 8'h4a;
    8'hc3: out <= 8'h5c;
    8'hc4: out <= 8'h38;
    8'hc5: out <= 8'h57;
    8'hc6: out <= 8'h73;
    8'hc7: out <= 8'h97;
    8'hc8: out <= 8'hcb;
    8'hc9: out <= 8'ha1;
    8'hca: out <= 8'he8;
    8'hcb: out <= 8'h3e;
    8'hcc: out <= 8'h96;
    8'hcd: out <= 8'h61;
    8'hce: out <= 8'h0d;
    8'hcf: out <= 8'h0f;
    8'hd0: out <= 8'he0;
    8'hd1: out <= 8'h7c;
    8'hd2: out <= 8'h71;
    8'hd3: out <= 8'hcc;
    8'hd4: out <= 8'h90;
    8'hd5: out <= 8'h06;
    8'hd6: out <= 8'hf7;
    8'hd7: out <= 8'h1c;
    8'hd8: out <= 8'hc2;
    8'hd9: out <= 8'h6a;
    8'hda: out <= 8'hae;
    8'hdb: out <= 8'h69;
    8'hdc: out <= 8'h17;
    8'hdd: out <= 8'h99;
    8'hde: out <= 8'h3a;
    8'hdf: out <= 8'h27;
    8'he0: out <= 8'hd9;
    8'he1: out <= 8'heb;
    8'he2: out <= 8'h2b;
    8'he3: out <= 8'h22;
    8'he4: out <= 8'hd2;
    8'he5: out <= 8'ha9;
    8'he6: out <= 8'h07;
    8'he7: out <= 8'h33;
    8'he8: out <= 8'h2d;
    8'he9: out <= 8'h3c;
    8'hea: out <= 8'h15;
    8'heb: out <= 8'hc9;
    8'hec: out <= 8'h87;
    8'hed: out <= 8'haa;
    8'hee: out <= 8'h50;
    8'hef: out <= 8'ha5;
    8'hf0: out <= 8'h03;
    8'hf1: out <= 8'h59;
    8'hf2: out <= 8'h09;
    8'hf3: out <= 8'h1a;
    8'hf4: out <= 8'h65;
    8'hf5: out <= 8'hd7;
    8'hf6: out <= 8'h84;
    8'hf7: out <= 8'hd0;
    8'hf8: out <= 8'h82;
    8'hf9: out <= 8'h29;
    8'hfa: out <= 8'h5a;
    8'hfb: out <= 8'h1e;
    8'hfc: out <= 8'h7b;
    8'hfd: out <= 8'ha8;
    8'hfe: out <= 8'h6d;
    8'hff: out <= 8'h2c;
    endcase
endmodule

Identify the primary security assets for 'tiny_aes' and return the JSON object per the contract.

CSA ANALYSIS (internal working; not emitted).

P3164 3.1.1 rubric -- answer, then the conceptual asset it yields. P3164's own AES
walkthrough (3.2.3) analyses a full crypto peripheral with Config Regs, Status Regs, Key Reg,
IV Reg, Input/Output Buffers, an Enc/Dec Engine and a Debug interface. This core is the
cipher datapath only: it has no configuration, status, IV or debug. The questions are
therefore answered against THIS design, and two of the four answers differ from P3164's for
that reason -- which is the method working as intended, not a disagreement with it.

 (C) Any element that can leak or expose material needing confidentiality?
     YES. P3164: "Since this is a crypto IP, the plaintext data and key values are secrets.
     Therefore, any block ... that supports these secrets will be a conceptual asset." Summary
     section 5 says the same of this core: the cipher key is a long-term secret and the input
     block is private plaintext. Both enter on ports and are held, round by round, in the
     pipeline registers.
 (I) Any element that can modify material an integrator may deem sensitive?
     YES, but narrower than P3164's. P3164 lists Key Reg, IV Reg, Input Buffer and Config
     Regs as needing integrity during operation. This core has no IV and no configuration, so
     integrity applies only to the key and state paths: a modified round key, round constant
     or round state silently yields a wrong ciphertext with no error signalled.
 (A) Any element that, if unavailable, can prohibit operational behavior?
     YES, by a different route than P3164's. P3164 reached availability through the debug
     interface -- "the debug interface allows complete control of the Enc/Dec Engine.
     Therefore Data_Out can be blocked by this interface". This core has no debug interface;
     availability instead attaches to the ciphertext output itself, on which the consumer
     waits and without which the encryption service does not exist.
 (U) Privileged mode, override, bypass or injection path?
     NO -- and here the designs genuinely differ. P3164 answered YES for its AES because
     "the debug interface allows the IP to encrypt/decrypt using the test key and IV values".
     This core has no debug mode, no privileged path and no configuration to override, so the
     undermining route P3164 describes does not exist here.

Conceptual assets: (a) the cipher key and the round keys derived from it, (b) the plaintext
and the state derived from it, (c) delivery of the ciphertext.

P3164 3.1.2 structural mapping -- P3164 names conceptual assets as BLOCKS; resolve each block
to the concrete elements of this closed set that produce, store or transport it:
     P3164 "Key Reg"        ->  key (aes_128), key_in (final_round)
     P3164 "Input Buffer"   ->  state_in (final_round)
     P3164 "Output Buffer"  ->  state_out (final_round)
     P3164 "Enc/Dec Engine" ->  the one_round / final_round / table_lookup datapath
     P3164 "IV Reg", "Config Regs", "Status Regs", "Debug Values" -> no counterpart exists
Bind to the element where the material enters, is applied, or leaves. The intermediate
pipeline stages (s1..s9, k1..k9, the expansion outputs and the S-box partials) carry the same
two conceptual assets and belong to the later secondary-asset stage, not here.

Objective: key, key_in and state_in are Confidentiality -- they are the designated secret
material P3164 identifies for a crypto IP. state_in additionally answers YES to integrity
(altering it changes the ciphertext); Confidentiality dominates because the material is
secret, and the integrity consequence is recorded in its Justification. state_out is
Availability: the consumer waits on the ciphertext.

Scope note: P3164 is maximally inclusive for crypto IPs -- "every block in the IP, except the
Debug Values block, can be considered a conceptual asset", and then observes the result "may
be too numerous to comprehend". The reference list used here keeps only the canonical
representative of each conceptual asset at the point where it enters, is applied, or leaves
the cipher. That is a deliberate narrowing of P3164's stance, not a contradiction of it.

NON-assets: clk is infrastructure. The S-box and T-table internals (S4, T, S, xS and their
partial results) implement the substitution and are downstream of state already captured.
The per-round pipeline registers are stages of conceptual assets (a) and (b) rather than
independent assets.

EMITTED OUTPUT:
{
 "IP": "tiny_aes",
 "Assets": [
  {
   "Asset Name": "Encryption key input",
   "Asset RTL": "key",
   "Entity": "aes_128",
   "Functionality": "Provides the 128-bit cipher key used for the initial AddRoundKey and fed into the key expansion pipeline.",
   "Security Objective": "Confidentiality",
   "Justification": "This port carries the long-term secret used to protect data. Disclosure of the key compromises all encrypted data regardless of algorithmic strength."
  },
  {
   "Asset Name": "Final-round input state",
   "Asset RTL": "state_in",
   "Entity": "final_round",
   "Functionality": "128-bit input state to the final AES round; split into s0\\\\u2013s3, substituted via S4 and combined.",
   "Security Objective": "Confidentiality",
   "Justification": "This final-round state is still sensitive as it is a direct function of plaintext and key. Any modification changes the final ciphertext, violating correctness."
  },
  {
   "Asset Name": "Final-round key input",
   "Asset RTL": "key_in",
   "Entity": "final_round",
   "Functionality": "128-bit key for the final round used in AddRoundKey.",
   "Security Objective": "Confidentiality",
   "Justification": "It is secret key material; disclosure directly compromises encryption security. It is XORed with substituted bytes to produce the final ciphertext."
  },
  {
   "Asset Name": "Ciphertext output",
   "Asset RTL": "state_out",
   "Entity": "final_round",
   "Functionality": "128-bit final encrypted output registered at the end of the final round.",
   "Security Objective": "Availability",
   "Justification": "System operation depends on timely production of ciphertext; if this output is unavailable, encryption service is effectively denied. It is the culmination of all pipeline stages."
  }
 ]
}
"""

# ---------------------------------------------------------------------------
# Splice by CONCATENATION -- the example contains literal JSON braces, so an
# f-string would need every brace escaped.
#   ASSET_PRIMARY_SYSTEM = ASSET_PRIMARY_CORE + "\n\n" + ICL_ASSET_EXAMPLES_01
# ---------------------------------------------------------------------------

ICL_ASSET_EXAMPLES_01 = (
    "The following worked case study shows the complete task: the inputs you receive, the "
    "IEEE P3164 reasoning that turns them into conceptual assets, the structural mapping "
    "that binds each conceptual asset to a named element of the closed set, and the object "
    "to emit. Reproduce the DISCIPLINE -- answer all four rubric questions with a reason, "
    "state the non-asset decisions explicitly, bind every asset to an exact name from the "
    "closed set you are given, and give each one exactly one dominant Security Objective "
    "with any secondary consequence noted in the Justification. The REASONING block is "
    "internal: emit only the final JSON object.\n\n"
    + EXAMPLE_01_OMSP_GPIO + "\n" + EXAMPLE_02_TINY_AES
)

if __name__ == "__main__":
    print(ICL_ASSET_EXAMPLES_01)
