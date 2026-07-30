"""
In-context learning (ICL) examples for the LAsset Asset Generation stage
(primary-asset prompt, ASSET_PRIMARY_SYSTEM). REGENERATED against the
corrected closed-set contract.

Contract this version teaches (matching the repo's asset_list output):
  * CLOSED SET = parsed I/O ports UNION parsed internal signals/registers.
    Primaries may bind to EITHER (repo evidence: pmpcfg, addsub_res,
    irq_machine are internal-signal primaries). The earlier "ports-only,
    defer internals to the secondary stage" rule was WRONG and is removed.
  * One emitted object per structural element; a conceptual asset may fan
    out to several objects (rs1_i/rs2_i/rs3_i pattern).
  * Output = ONE JSON object {"IP": "<module>", "Assets": [...]}; each
    Assets entry uses the repo generation-stage keys, exactly:
      Asset Name, Asset RTL, Entity, Functionality,
      Security Objective (single enum value), Justification.
    (Secondary Assets are attached by the separate secondary stage.)
  * Parsed elements mirror the repo's real parsed shape: ports carry
    {entity, name, dir, type, function}; internal signals carry
    {entity, name, type, kind, function} with kind "register"|"signal".
  * Security Objective: exactly one dominant value; Undermine (U) findings
    fold into Integrity or Availability; other objectives may be noted
    inside Justification.
  * Entity = the VHDL entity DECLARING the element (not the file name).
  * Global clk/rst and boilerplate are non-assets unless clock/reset
    control is the module's function.

Ground truth: IEEE P3164 white paper §3.2 CSA walkthroughs (GPIO, GNG, AES).
CIA/Undermine verdicts reproduce the paper. Structural mappings are extended
per the LAsset paper's coverage bias: elements that produce, store, OR carry
a conceptual asset are structural assets (P3164 §3.1.2), so secret-carrying
output ports are included (mirrors the repo's neorv32_trng data_o primary).
RTL provenance: GNG abbreviates the real OpenCores design (coeff reg `d` is
gng_coef.v line 51); GPIO and AES are illustrative reconstructions of the
P3164 block diagrams. Each example shows REASONING (marked internal, ending
with explicit NON-asset decisions) followed by EMITTED OUTPUT (one strict
JSON object) so the model learns both the rubric walk and the strict output
contract.

Machine-verifiable structure: the blocks after "PARSED PORTS:",
"PARSED INTERNAL SIGNALS:" and "EMITTED OUTPUT:" are strict JSON
(see verify_icl.py).
"""

# ============================================================================
# EXAMPLE 1 -- Simple GPIO Pad  (Family: Bus/Interface)
# Teaches: C and U legitimately NO; a control PORT as the sole primary;
# a legitimately EMPTY internal-signal set; data ports as non-assets.
# ============================================================================

EXAMPLE_GPIO = """\
### CASE STUDY 1: simple_gpio_pad (Family: Bus/Interface)

TECHNICAL SUMMARY:
MODULE: simple_gpio_pad
1. FUNCTION AND ROLE
Single GPIO pad cell with direction select. In output mode the core-side data
drives the external pad; in input mode the pad value is sampled to the core.
Purely combinational mux/tristate logic; no registers, no software-visible
state, no debug or privileged modes.
2. REGISTERS, CSRS, AND FLAGS
Not documented for this module.
3. CONFIGURATION
Not documented for this module.
4. CROSS-MODULE INTERACTION
The direction select is typically driven by a pad-control register elsewhere
in the SoC; the cell itself connects the core-side data path to one external
bidirectional pin. No bus interface, interrupts, or privilege transitions.
5. SECURITY-RELEVANT BEHAVIOR
No access-control, protection, or privileged mechanisms are documented for
this module. The data-flow direction is controlled at runtime by an external
agent and is not latched or locked by the cell itself.

PARSED PORTS:
[
 {"entity": "simple_gpio_pad", "name": "dir_sel_i", "dir": "in", "type": "std_ulogic",
  "function": "Direction select: 1 = output mode (core drives pad), 0 = input mode (pad drives core); controls data-flow direction."},
 {"entity": "simple_gpio_pad", "name": "data_i", "dir": "in", "type": "std_ulogic",
  "function": "Core-side data driven onto the pad in output mode."},
 {"entity": "simple_gpio_pad", "name": "data_o", "dir": "out", "type": "std_ulogic",
  "function": "Pad value sampled to the core in input mode."},
 {"entity": "simple_gpio_pad", "name": "pad_io", "dir": "inout", "type": "std_logic",
  "function": "External bidirectional pad."}
]

PARSED INTERNAL SIGNALS:
[]

RTL:
    module simple_gpio_pad (
      input  wire dir_sel_i,
      input  wire data_i,
      output wire data_o,
      inout  wire pad_io
    );
      assign pad_io = dir_sel_i ? data_i : 1'bz;   // output-mode driver
      assign data_o = dir_sel_i ? 1'b0   : pad_io; // input-mode sample
    endmodule

REASONING (internal -- not part of the emitted output):
(C) NO. Combinational pass-through; nothing is stored and nothing is exposed
    beyond the intended data path itself.
(I) YES. Toggling the direction select during a runtime sample can toggle the
    sampled data and produce an error; the data-flow direction state realized
    by the mux gates must stay immutable while a transfer is in flight.
    -> conceptual asset: pad direction control.
(A) YES. Driving the direction select reverses the data flow on the pad --
    a denial of service on the data path at integration level. -> same
    conceptual asset.
(U) NO. No privileged mode, override, bypass, or injection path exists.
Structural mapping: the mux gates embody the direction state; with an empty
internal-signal set, dir_sel_i is the closed-set element that realizes and
fully determines it. Dominant objective: Integrity (availability noted in
justification).
NON-assets: data_i / data_o / pad_io carry no CIA objective assigned by this
IP in isolation -- they are attack points on the direction-control asset, not
assets themselves. No clk/rst exists in this cell.

EMITTED OUTPUT:
{"IP": "simple_gpio_pad",
 "Assets": [
 {"Asset Name": "Pad direction control",
  "Asset RTL": "dir_sel_i",
  "Entity": "simple_gpio_pad",
  "Functionality": "Selects the data-flow direction through the pad mux/tristate logic: 1 drives the pad from core data, 0 samples the pad to the core.",
  "Security Objective": "Integrity",
  "Justification": "Mid-transfer modification corrupts sampled data by reversing the mux path, violating integrity of the transfer; the same control also enables denial of service by reversing the data flow (availability), but integrity of in-flight transfers is the dominant concern."}
]}
"""

# ============================================================================
# EXAMPLE 2 -- Gaussian Noise Generator  (Family: Accelerator)
# Teaches: Availability legitimately NO; primaries drawn from BOTH ports and
# internal registers (incl. P3164's own gng_coef.d); one conceptual asset
# fanning out to several per-element objects; test/override ports as assets.
# ============================================================================

EXAMPLE_GNG = """\
### CASE STUDY 2: gng (Gaussian Noise Generator, Family: Accelerator)

TECHNICAL SUMMARY:
MODULE: gng
1. FUNCTION AND ROLE
Generates white Gaussian noise for ML/DSP workloads. A 64-bit combined
Tausworthe generator (three LFSRs, XOR-combined) produces uniform randomness,
seeded by three initialization vectors. A leading-zero detector forms an
address into a coefficient ROM; polynomial coefficients (c0, c1, c2) shape the
uniform stream into a normal distribution.
2. REGISTERS, CSRS, AND FLAGS
Not documented for this module.
3. CONFIGURATION
Not documented for this module. The three initialization vectors are runtime
input ports rather than build-time parameters.
4. CROSS-MODULE INTERACTION
Consumes three externally supplied seed vectors and delivers Gaussian noise
samples to downstream logic. Two test facilities cross the module boundary:
an output tap observing the raw randomness entering the split logic, and an
address override forcing the coefficient-ROM address.
5. SECURITY-RELEVANT BEHAVIOR
Security-critical by function: the module generates randomness whose
unpredictability downstream consumers may rely on. The seed vectors fully
determine the generated sequence; the test tap exposes the raw internal
randomness at the module boundary; the address override can force coefficient
selection during normal-looking operation. No gating or authentication on
either test facility is documented.

PARSED PORTS:
[
 {"entity": "gng", "name": "clk", "dir": "in", "type": "std_ulogic",
  "function": "Global clock; carries no sensitive data."},
 {"entity": "gng", "name": "rstn", "dir": "in", "type": "std_ulogic",
  "function": "Global active-low reset."},
 {"entity": "gng", "name": "init_z1", "dir": "in", "type": "std_ulogic_vector(63 downto 0)",
  "function": "Seed / initialization vector priming LFSR-1; determines the random sequence."},
 {"entity": "gng", "name": "init_z2", "dir": "in", "type": "std_ulogic_vector(63 downto 0)",
  "function": "Seed / initialization vector priming LFSR-2."},
 {"entity": "gng", "name": "init_z3", "dir": "in", "type": "std_ulogic_vector(63 downto 0)",
  "function": "Seed / initialization vector priming LFSR-3."},
 {"entity": "gng", "name": "addr_ovr", "dir": "in", "type": "std_ulogic_vector(7 downto 0)",
  "function": "Test override forcing the LZD-generated address into the coefficient ROM."},
 {"entity": "gng", "name": "split_inp", "dir": "out", "type": "std_ulogic_vector(63 downto 0)",
  "function": "Test observation tap exposing the raw XOR-combined randomness entering the split logic."},
 {"entity": "gng", "name": "data_out", "dir": "out", "type": "std_ulogic_vector(15 downto 0)",
  "function": "Gaussian noise output sample."}
]

PARSED INTERNAL SIGNALS:
[
 {"entity": "gng", "name": "lfsr_state", "type": "std_ulogic_vector(191 downto 0)", "kind": "register",
  "function": "Concatenated state registers of the three Tausworthe LFSRs; evolves each cycle from the seeds."},
 {"entity": "gng", "name": "u_noise", "type": "std_ulogic_vector(63 downto 0)", "kind": "signal",
  "function": "XOR combination of the three LFSR outputs; the raw uniform random stream."},
 {"entity": "gng", "name": "lzd_addr", "type": "std_ulogic_vector(7 downto 0)", "kind": "signal",
  "function": "Coefficient-ROM address produced by the leading-zero detector, unless overridden."},
 {"entity": "gng_coef", "name": "d", "type": "std_ulogic_vector(52 downto 0)", "kind": "register",
  "function": "Coefficient word {c0, c1, c2} read from the coefficient ROM; parameterizes the polynomial approximation."}
]

RTL (abbreviated; full design in OpenCores gng):
    // ctg: lfsr_state <= next(lfsr_state, init_z1..3); u_noise = xor(lfsr taps)
    // gng_coef.v:  reg [52:0] d;  // {c0, c1, c2}
    //   addr = addr_ovr_valid ? addr_ovr : lzd_addr;  d <= coeff_rom[addr];
    // interp: data_out <= f(u_noise, c0, c1, c2);  split_inp <= u_noise;

REASONING (internal -- not part of the emitted output):
(C) YES. The XOR-combined LFSR stream is seed-equivalent state: observing it
    (split_inp) or knowing the seeds (init_z1..3) makes the Gaussian output
    predictable, assuming the integrator treats the noise as secret.
    -> conceptual asset: random state / seed material. Structural fan-out:
    init_z1, init_z2, init_z3 (entry), lfsr_state (store), u_noise (the
    generated stream itself), split_inp (observation surface), data_out
    (the carried product).
(I) YES. Once seeds are set, the coefficient-ROM address path must not be
    modified; substituting coefficients silently degrades the randomness.
    -> conceptual asset: coefficient selection. Structural: lzd_addr (the
    generated address), d (the coefficient store -- P3164's own structural
    example) and addr_ovr (the override that influences it).
(A) NO. Nothing at the integration level can gate or impede data_out;
    availability is not an objective for this IP.
(U) YES. addr_ovr forces an unintended coefficient under normal-looking
    operation -- folded into the Integrity objective of the coefficient path.
NON-assets: clk / rstn are the only non-assets -- global infrastructure
(this module's function is not clock/reset control). Note that internal
signals that GENERATE or carry a conceptual asset (u_noise, lzd_addr) are
emitted as primaries in their own right, not deferred to the secondary
stage.

EMITTED OUTPUT:
{"IP": "gng",
 "Assets": [
 {"Asset Name": "LFSR seed vector 1",
  "Asset RTL": "init_z1",
  "Entity": "gng",
  "Functionality": "Initialization vector priming LFSR-1; together with the other seeds it fully determines the generated random sequence.",
  "Security Objective": "Confidentiality",
  "Justification": "Knowledge of the seeds makes the entire noise stream predictable, defeating its purpose as randomness; disclosure directly violates confidentiality of the seed material."},
 {"Asset Name": "LFSR seed vector 2",
  "Asset RTL": "init_z2",
  "Entity": "gng",
  "Functionality": "Initialization vector priming LFSR-2 of the combined Tausworthe generator.",
  "Security Objective": "Confidentiality",
  "Justification": "Same seed-disclosure argument as init_z1: exposure allows reconstruction of the random stream."},
 {"Asset Name": "LFSR seed vector 3",
  "Asset RTL": "init_z3",
  "Entity": "gng",
  "Functionality": "Initialization vector priming LFSR-3 of the combined Tausworthe generator.",
  "Security Objective": "Confidentiality",
  "Justification": "Same seed-disclosure argument as init_z1: exposure allows reconstruction of the random stream."},
 {"Asset Name": "Combined LFSR internal state",
  "Asset RTL": "lfsr_state",
  "Entity": "gng",
  "Functionality": "Registered state of the three LFSRs; the evolving seed-equivalent internal randomness of the generator.",
  "Security Objective": "Confidentiality",
  "Justification": "Reading this state at any cycle is equivalent to knowing the seed from that point on, allowing prediction of all future output; it is the stored form of the confidential material."},
 {"Asset Name": "Raw uniform random stream",
  "Asset RTL": "u_noise",
  "Entity": "gng",
  "Functionality": "XOR combination of the three LFSR outputs; the generated uniform randomness feeding the split logic and interpolation.",
  "Security Objective": "Confidentiality",
  "Justification": "The stream is seed-equivalent: observing it at any cycle permits prediction of all subsequent output, so the generated randomness itself must remain unobservable outside intended paths."},
 {"Asset Name": "Raw randomness observation tap",
  "Asset RTL": "split_inp",
  "Entity": "gng",
  "Functionality": "Test output exposing the raw XOR-combined uniform randomness entering the split logic.",
  "Security Objective": "Confidentiality",
  "Justification": "A port that carries the seed-equivalent stream across the module boundary; if reachable at integration it is a direct leak path for the confidential state."},
 {"Asset Name": "Gaussian noise output",
  "Asset RTL": "data_out",
  "Entity": "gng",
  "Functionality": "Delivers the shaped Gaussian noise samples consumed by the integrator.",
  "Security Objective": "Confidentiality",
  "Justification": "The output carries the product the integrator may deem secret; unintended observation of it (or correlation with internal state) weakens any use of the noise as unpredictable material."},
 {"Asset Name": "Coefficient ROM address",
  "Asset RTL": "lzd_addr",
  "Entity": "gng",
  "Functionality": "Address into the coefficient ROM produced by the leading-zero detector from the uniform stream.",
  "Security Objective": "Integrity",
  "Justification": "Once the seeds are set the address path must select only the intended coefficients; modifying it substitutes coefficients and silently degrades the statistical quality of the output while the IP appears to operate normally."},
 {"Asset Name": "Polynomial coefficient word",
  "Asset RTL": "d",
  "Entity": "gng_coef",
  "Functionality": "Registered coefficient word {c0, c1, c2} read from the coefficient ROM; parameterizes the polynomial that shapes uniform randomness into a Gaussian distribution.",
  "Security Objective": "Integrity",
  "Justification": "Substituting or corrupting the coefficients silently degrades the statistical quality of the output while the IP appears to operate normally; the coefficient store must stay immutable after initialization."},
 {"Asset Name": "Coefficient address override",
  "Asset RTL": "addr_ovr",
  "Entity": "gng",
  "Functionality": "Test input that forces the coefficient-ROM address in place of the LZD-generated address.",
  "Security Objective": "Integrity",
  "Justification": "An override/bypass path that can select unintended coefficients under normal-looking operation, undermining output correctness; folded under integrity of the coefficient-selection path."}
]}
"""

# ============================================================================
# EXAMPLE 3 -- AES Engine  (Family: Security)
# Teaches: all four rubric questions YES; primaries mixed across internal
# registers and ports; single dominant objective with others noted; the
# Debug-Values constant block as an explicit NON-asset; no collapse to a
# single module-level asset.
# ============================================================================

EXAMPLE_AES = """\
### CASE STUDY 3: aes_engine (Family: Security)

TECHNICAL SUMMARY:
MODULE: aes_engine
1. FUNCTION AND ROLE
AES encryption/decryption engine with separated data-in/data-out paths.
Write-only key and IV inputs load the Key Reg and IV Reg; input and output
buffers stage plaintext/ciphertext through the Enc/Dec Engine.
2. REGISTERS, CSRS, AND FLAGS
- Config Regs — r/w — not stated — key size, AES mode, operation, start/stop for the Enc/Dec Engine
- Status Regs — r/- — not stated — error codes, engine state, completion
- Key Reg — -/w — not stated — key value for encrypt/decrypt operation
- IV Reg — -/w — not stated — initialization vector for AES cryptography
3. CONFIGURATION
Not documented for this module.
4. CROSS-MODULE INTERACTION
Configuration, status, key, IV, and data are accessed over the
integrator-facing interface. The debug interface grants an external agent
complete observability and control of the Enc/Dec Engine; no gating or
authentication on that access is documented.
5. SECURITY-RELEVANT BEHAVIOR
Handles secret key material and private plaintext by function. When entering
the debug mode, the IV and key values are replaced with debug values
hardcoded in the RTL, and the debug interface can fully control the engine,
including blocking its output. The key and IV are write-only from the
integrator side; status reads expose engine-internal state at the boundary.

PARSED PORTS:
[
 {"entity": "aes_engine", "name": "clk", "dir": "in", "type": "std_ulogic",
  "function": "Global clock; carries no sensitive data."},
 {"entity": "aes_engine", "name": "rstn", "dir": "in", "type": "std_ulogic",
  "function": "Global active-low reset."},
 {"entity": "aes_engine", "name": "cfg_i", "dir": "in", "type": "std_ulogic_vector(31 downto 0)",
  "function": "Write access to configuration registers (mode, operation, key size, start/stop); carries control state."},
 {"entity": "aes_engine", "name": "status_o", "dir": "out", "type": "std_ulogic_vector(31 downto 0)",
  "function": "Read-only status (error codes, engine state, completion); observes engine internals."},
 {"entity": "aes_engine", "name": "dbg_io", "dir": "inout", "type": "std_ulogic_vector(31 downto 0)",
  "function": "Debug interface with complete observability/control of the Enc/Dec Engine; substitutes hardcoded debug key/IV when active."},
 {"entity": "aes_engine", "name": "key_i", "dir": "in", "type": "std_ulogic_vector(255 downto 0)",
  "function": "Write-only key value loaded into the Key Reg; carries secret material."},
 {"entity": "aes_engine", "name": "iv_i", "dir": "in", "type": "std_ulogic_vector(127 downto 0)",
  "function": "Write-only initialization vector loaded into the IV Reg."},
 {"entity": "aes_engine", "name": "data_in", "dir": "in", "type": "std_ulogic_vector(127 downto 0)",
  "function": "Plaintext/ciphertext input staged through the Input Buffer; carries secret data."},
 {"entity": "aes_engine", "name": "data_out", "dir": "out", "type": "std_ulogic_vector(127 downto 0)",
  "function": "Encrypted/decrypted output from the Output Buffer."}
]

PARSED INTERNAL SIGNALS:
[
 {"entity": "aes_engine", "name": "key_reg", "type": "std_ulogic_vector(255 downto 0)", "kind": "register",
  "function": "Stores the active encryption/decryption key loaded from key_i."},
 {"entity": "aes_engine", "name": "iv_reg", "type": "std_ulogic_vector(127 downto 0)", "kind": "register",
  "function": "Stores the initialization vector loaded from iv_i."},
 {"entity": "aes_engine", "name": "cfg_regs", "type": "std_ulogic_vector(31 downto 0)", "kind": "register",
  "function": "Configuration registers: mode, operation, key size, start/stop."},
 {"entity": "aes_engine", "name": "in_buf", "type": "std_ulogic_vector(127 downto 0)", "kind": "register",
  "function": "Input buffer staging plaintext/ciphertext toward the engine."},
 {"entity": "aes_engine", "name": "out_buf", "type": "std_ulogic_vector(127 downto 0)", "kind": "register",
  "function": "Output buffer holding the engine result before data_out."},
 {"entity": "aes_engine", "name": "dbg_mode", "type": "std_ulogic", "kind": "register",
  "function": "Debug-mode flag; when set, engine control and key/IV substitution are driven from the debug interface."}
]

RTL (abbreviated; block-level per architecture):
    // key_reg <= key_i;  iv_reg <= iv_i;  cfg_regs <= cfg_i;  in_buf <= data_in;
    // out_buf <= aes(in_buf, dbg_mode ? DBG_KEY : key_reg,
    //                        dbg_mode ? DBG_IV  : iv_reg, cfg_regs);
    // status_o <= {err, state, done};  data_out <= out_buf;
    // dbg_io: full engine observe/control; asserts dbg_mode.

REASONING (internal -- not part of the emitted output):
(C) YES. Crypto IP: key and plaintext are secrets; every element storing or
    carrying them qualifies -- key_reg, in_buf, out_buf, data_in/data_out --
    and status_o may leak engine-internal information.
(I) YES. During operation the key, IV, input data, and configuration must not
    change -> key_reg, iv_reg, in_buf, cfg_regs.
(A) YES. The debug interface has complete engine control and can block
    output -> dbg_io / dbg_mode.
(U) YES. Debug mode substitutes hardcoded test key/IV, voiding security
    strength under normal-looking operation -> folded into the objectives of
    the debug-control elements.
Each element gets ONE dominant objective; secondary objectives are noted in
the justification. Do NOT collapse to a single module-level asset (P3164
permits it for crypto IPs; LAsset keeps element granularity so secondary
assets and DoI can be derived).
NON-assets: the hardcoded DBG_KEY/DBG_IV constants store no secret -- their
values are fixed, known, and valueless; the debug INTERFACE that swaps them
in is the asset-relevant element, not the constant block. clk / rstn are
global infrastructure. data_out and iv_i are boundary carriers of assets
already captured (out_buf, iv_reg) and are left to the secondary stage here
to illustrate that the port/register pair need not be double-listed when one
member is clearly the store; include both only when each adds a distinct
exposure argument (as data_in does for entry-side plaintext).

EMITTED OUTPUT:
{"IP": "aes_engine",
 "Assets": [
 {"Asset Name": "Active cipher key register",
  "Asset RTL": "key_reg",
  "Entity": "aes_engine",
  "Functionality": "Stores the key used by the Enc/Dec Engine for all encryption/decryption operations.",
  "Security Objective": "Confidentiality",
  "Justification": "Exposure of the stored key breaks confidentiality of all traffic protected by it; its integrity during operation also matters (mid-operation modification corrupts the cipher), but disclosure is the dominant risk for key material."},
 {"Asset Name": "Initialization vector register",
  "Asset RTL": "iv_reg",
  "Entity": "aes_engine",
  "Functionality": "Stores the IV parameterizing the cipher mode for the current operation.",
  "Security Objective": "Integrity",
  "Justification": "Modification of the IV during operation weakens or corrupts the cipher mode (e.g., forcing IV reuse), undermining the cryptographic guarantees; the IV need not be secret, so integrity dominates."},
 {"Asset Name": "Cipher configuration registers",
  "Asset RTL": "cfg_regs",
  "Entity": "aes_engine",
  "Functionality": "Hold mode, operation, key size, and start/stop controlling the Enc/Dec Engine.",
  "Security Objective": "Integrity",
  "Justification": "Unauthorized modification (e.g., key-size downgrade or mode change) silently weakens the cipher while the IP appears functional; configuration must stay immutable during operation."},
 {"Asset Name": "Plaintext input",
  "Asset RTL": "data_in",
  "Entity": "aes_engine",
  "Functionality": "Carries plaintext (or ciphertext for decryption) into the Input Buffer.",
  "Security Objective": "Confidentiality",
  "Justification": "The input data is the secret the engine exists to protect; observation at or before the boundary discloses it directly."},
 {"Asset Name": "Input staging buffer",
  "Asset RTL": "in_buf",
  "Entity": "aes_engine",
  "Functionality": "Registers the input block on its way to the Enc/Dec Engine.",
  "Security Objective": "Confidentiality",
  "Justification": "Holds plaintext in the clear inside the module; any unintended read path over it discloses the protected data (integrity during operation is a secondary concern noted for completeness)."},
 {"Asset Name": "Engine result buffer",
  "Asset RTL": "out_buf",
  "Entity": "aes_engine",
  "Functionality": "Holds the engine output block before it is presented on data_out.",
  "Security Objective": "Confidentiality",
  "Justification": "For decryption operations this buffer holds recovered plaintext; exposure discloses the protected data."},
 {"Asset Name": "Engine status output",
  "Asset RTL": "status_o",
  "Entity": "aes_engine",
  "Functionality": "Read-only status reporting error codes, engine state, and completion.",
  "Security Objective": "Confidentiality",
  "Justification": "Engine-internal state visible at the boundary can leak information about operations and data (e.g., error-based or timing-correlated inference), a recognized side-information channel on crypto engines."},
 {"Asset Name": "Debug control interface",
  "Asset RTL": "dbg_io",
  "Entity": "aes_engine",
  "Functionality": "Grants complete observability and control of the Enc/Dec Engine; activates debug mode.",
  "Security Objective": "Availability",
  "Justification": "Full engine control can block or stall output (denial of service); the same path also undermines security strength by substituting hardcoded key/IV, so its compromise dominates the module's availability and correctness."},
 {"Asset Name": "Debug mode flag",
  "Asset RTL": "dbg_mode",
  "Entity": "aes_engine",
  "Functionality": "Registered flag selecting debug-driven control and hardcoded key/IV substitution.",
  "Security Objective": "Integrity",
  "Justification": "If this flag can be set outside a legitimate debug session, the engine silently encrypts with known key/IV -- an override that voids all cryptographic protection while appearing operational; its state must be tamper-proof."}
]}
"""

# ----------------------------------------------------------------------------
# Concatenation for prompt injection (order: simple -> medium -> hard).
# Splice by CONCATENATION with the core prompt (never via f-string):
#   ASSET_PRIMARY_SYSTEM = ASSET_PRIMARY_CORE + "\n\n" + ICL_ASSET_EXAMPLES
# ----------------------------------------------------------------------------

ICL_ASSET_EXAMPLES = (
    "The following worked case studies illustrate the method. Follow their "
    "discipline exactly: every rubric question answered YES or NO with a "
    "justification; explicit NON-asset decisions; one Assets entry per "
    "structural element, drawn from ports AND internal signals; exactly one "
    "dominant Security Objective per entry; reasoning stays internal and "
    'only the single JSON object {"IP": ..., "Assets": [...]} is emitted.\n\n'
    + EXAMPLE_GPIO + "\n" + EXAMPLE_GNG + "\n" + EXAMPLE_AES
)

if __name__ == "__main__":
    print(ICL_ASSET_EXAMPLES)