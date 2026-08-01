"""icl_examples_0.py -- ICL examples built ONLY from IEEE P3164 §3.1-§3.2.

PURPOSE (ablation baseline "v0")
--------------------------------
This variant deliberately does NOT match the shape of the runtime input or the
required output. It reproduces the standard's own worked analyses and nothing
else:

  * no PARSED PORTS / PARSED INTERNAL SIGNALS blocks  -- P3164 analyses architectural
    block diagrams, not parsed netlists;
  * no 5-section TECHNICAL SUMMARY                    -- P3164 gives a prose paragraph;
  * no {"IP": ..., "Assets": [...]} emission          -- P3164's own Asset Definition
    object has an entirely different schema (Name / Description / Family / Type /
    Database_ID), and it is reproduced here as the standard states it;
  * assets are named as BLOCKS ("the mux gates", "Coeff ROM"), not as closed-set
    element names, because that is the granularity the standard works at.

The experiment this supports: can the model learn the CSA *concepts* -- the four
rubric questions, what counts as a conceptual asset, the conceptual->structural
mapping, and the asset/attack-point distinction -- from examples whose format
differs from its task, relying on ASSET_PRIMARY_CORE alone to supply the output
contract and the closed-set binding rule?

FIDELITY
--------
Every verdict, asset list and conclusion below is taken from the standard:
  GPIO  §3.2.1   C No  / I Yes / A Yes / U No
  GNG   §3.2.2   C Yes / I Yes / A No  / U Yes
  AES   §3.2.3   C Yes / I Yes / A Yes / U Yes
Prose is condensed rather than copied verbatim; the technical content, the
answers, and the named assets follow the source. Section numbers are retained so
any claim here can be checked against the document.

Nothing in this file is inferred, extended, or adapted to our pipeline. For the
adapted variants -- closed-set element names, our output contract, added
structural mappings -- see icl_asset_examples.py.
"""

# ---------------------------------------------------------------------------
# The rubric, as P3164 §3.1.1 poses it, with the standard's own closing rule.
# ---------------------------------------------------------------------------

P3164_RUBRIC = """\
IEEE P3164 Conceptual-and-Structural Analysis (CSA) -- the conceptual phase asks four
questions of an IP:

1. Confidentiality: Are there any elements in the IP that can leak or expose material
   that may need confidentiality?
2. Integrity: Are there any elements in the IP that can modify material an integrator
   may deem as sensitive?
3. Availability: Are there any elements in the IP that, if unavailable, can prohibit
   operational behavior?
4. Undermined Expected Behavior: Are there elements that could be impacted by behaviors
   at the integration level to undermine the functionality of the IP under normal
   operation?

If the answer is "No" to all four, the standard states it is probably safe to assume the
element is not an asset and requires no associated SA-EDI objects.

Structural analysis (§3.1.2) then locates the conceptual assets in the design: the intent
is to look through the RTL and identify the material that supports each conceptual asset.
Where a use case requires confidentiality on data generated within the IP, the structural
assets are the RTL that PRODUCES that data and STORES and TRANSPORTS its value -- the
registers and wires. Those code parts are the structural assets and each should have an
associated Asset Definition object.
"""

# ---------------------------------------------------------------------------
# §3.2.1 -- Simple GPIO pad.  Chosen by the standard for its minimal use cases,
# so the methodology is the focus rather than the IP.
# ---------------------------------------------------------------------------

EXAMPLE_0_GPIO = """\
### P3164 §3.2.1 -- SIMPLE GPIO PAD

Architecture (Figure 1): a pad cell whose only interface ports are two data ports and a
Direction Select. Direction Select steers a pair of mux gates that decide which way data
flows through the pad.

Conceptual phase:

1. Confidentiality -- NO. The gates inside the IP do not leak any information.

2. Integrity -- YES. If Direction Select were toggled during a runtime sample, Data could
   also toggle in value, potentially producing an error. The mux gates can be considered
   conceptual assets.

3. Availability -- YES. Direction Select can reverse the data flow on the Data ports,
   which can be a denial of service. The elements impacted by this attack are the mux
   gates, and they should be considered conceptual assets.

4. Undermined Expected Behavior -- NO. The IP has no privilege or bypassing mechanisms
   that will alter its normal behavior.

Conclusion: the assessment triggered questions 2 and 3, so there is at least one
conceptual asset -- the mux gates. The structural assets that create the Asset Definition
objects would be the RTL of those gates.

Note the distinction the standard draws: the Direction Select port can be used as the
ATTACK POINT to violate both objectives, but an attack point is not itself the asset. The
asset is the state the attack point manipulates.
"""

# ---------------------------------------------------------------------------
# §3.2.2 -- Gaussian Noise Generator (OpenCores, modified by the standard).
# The one example for which P3164 shows a concrete structural binding and a
# complete Asset Definition object.
# ---------------------------------------------------------------------------

EXAMPLE_0_GNG = """\
### P3164 §3.2.2 -- GAUSSIAN NOISE GENERATOR (GNG)

Architecture (Figure 2): three LFSRs primed by three initialization vectors (INIT_Z1..3)
feed an XOR block; the combined output drives Split logic and a leading-zero detector
(LZD) that forms an ADDR into a coefficient ROM (Coeff ROM); a Swizzle/Mask/Mux path
produces Data_Out. Two ports were added by the standard to challenge the methodology:
Split_Inp, an output test port used to observe the randomness going into the split logic,
and Addr_OvR, which overrides the address created by the LZD logic for testing the
coefficient ROM. Data_Out is the Gaussian noise the IP produces.

Conceptual phase:

1. Confidentiality -- YES. The output value of the XOR block can be deemed a seed and, if
   observed, may be used to predict the noise. This assumes the IC considers the generated
   noise a secret. The conceptual assets are the XOR and LFSR blocks.

2. Integrity -- YES. The address into the Coeff ROM should not be modified once the
   INIT_Z inputs are set; using a different coefficient than intended may reduce the
   randomness of the output. The conceptual assets are the ADDR block and Coeff ROM.

3. Availability -- NO. There is no means at the integration level to disable or impede
   Data_Out.

4. Undermined Expected Behavior -- YES. Addr_OvR can force the IP to select an unintended
   coefficient, which may produce an invalid result on Data_Out depending on the use case.
   Coeff ROM is therefore a conceptual asset.

Conclusion: every question except 3 identified a conceptual asset. The assets are XOR,
LFSR, ADDR and Coeff ROM, and the RTL that constructs these blocks is the structural
asset set.

Structural binding, as the standard gives it: the output value of Coeff ROM is located in
gng_coef.v at line 51, and the Asset Definition object for it may be defined as

{
 "Name" : "gng.gng_interp.gng_coef.d",
 "Description" : "Output from Coeff ROM",
 "Family" : ["Accelerator"],
 "Type" : ["Sensitive"],
 "Database_ID" : ["CWE VIEW: Hardware Design"]
}

Observe what that binding does: a conceptual asset named as a BLOCK ("Coeff ROM") is
resolved to one concrete named element of the RTL ("...gng_coef.d") in a specific file and
line. That resolution step is the conceptual-to-structural mapping.
"""

# ---------------------------------------------------------------------------
# §3.2.3 -- AES engine.  All four questions answer YES; the standard uses it to
# discuss what to do when the asset set becomes too large.
# ---------------------------------------------------------------------------

EXAMPLE_0_AES = """\
### P3164 §3.2.3 -- AES ENGINE

Architecture (Figure 4): Config Regs, Status Regs, Key Reg, IV Reg, an Enc/Dec Engine, an
Input Buffer, an Output Buffer, and a Debug Values block. Signal descriptions (Table 1):

  Configuration  Read/Write  configuration registers for the Enc/Dec Engine -- key size,
                             AES mode, operation, start/stop, and so on
  Status         Read        status registers for error codes, state, completion
  Debug          Read/Write  signals used to debug the Enc/Dec Engine, including complete
                             observability and control; when entering debug mode the IV
                             and key values are replaced with debug values hardcoded in
                             the RTL
  Key            Write       key value for encrypt/decrypt operation
  IV             Write       initialization vector for AES cryptography
  Data_In        Write       input data to be encrypted/decrypted
  Data_Out       Read        output data from the encrypt/decrypt engine

Conceptual phase:

1. Confidentiality -- YES. Since this is a crypto IP, the plaintext data and key values
   are secrets, so any block supporting those secrets is a conceptual asset: Key Reg,
   Enc/Dec Engine, Input Buffer and Output Buffer. In addition the Status Regs may leak
   confidential information, since they provide information about the Enc/Dec Engine, so
   that block may also be considered a conceptual asset.

2. Integrity -- YES. While the Enc/Dec Engine is operating, the key, IV, input data and
   configuration should not be modified. Key Reg, IV Reg, Input Buffer and Config Regs are
   therefore conceptual assets requiring integrity.

3. Availability -- YES. The debug interface allows complete control of the Enc/Dec Engine,
   so Data_Out can be blocked through that interface, making the Enc/Dec Engine a
   conceptual asset.

4. Undermined Expected Behavior -- YES. The debug interface allows the IP to
   encrypt/decrypt using the test key and IV values, which may result in a loss of
   security strength, making the Enc/Dec Engine a conceptual asset.

Conclusion: every block in the IP EXCEPT the Debug Values block can be considered a
conceptual asset. The RTL in those blocks would be the structural assets, and the
resulting Asset Definition objects may be too numerous to comprehend -- which the standard
notes is common for IPs making security claims such as cryptography.

Two remedies the standard offers for that numerosity, both stated to be acceptable and to
yield the same objects: assert that the entire IP is one structural asset with the top RTL
module as the single Asset Definition object; or analyze the IP from a vulnerability
perspective, which can help identify assets that are false positives. Note that neither
remedy is to DROP assets -- the choice is between enumerating them and aggregating them.
"""

# ---------------------------------------------------------------------------
# Splice.  Concatenation only: the examples contain literal JSON braces, so an
# f-string would either raise or need every brace escaped.
#   ASSET_PRIMARY_SYSTEM = ASSET_PRIMARY_CORE + "\n\n" + ICL_ASSET_EXAMPLES_0
# ---------------------------------------------------------------------------

ICL_ASSET_EXAMPLES_0 = (
    "The following is the asset-identification method of IEEE P3164 together with the "
    "standard's own worked examples. They are given at the standard's level of "
    "abstraction: the analysis is performed on architectural block diagrams, conceptual "
    "assets are named as functional BLOCKS, and only one example shows a concrete "
    "structural binding. Learn the METHOD from them -- the four questions, what makes an "
    "element an asset, how a conceptual asset is resolved to concrete RTL, and the "
    "difference between an asset and an attack point. Do NOT imitate their formatting: "
    "your own answer must name elements from the closed set you are given and must follow "
    "the output contract stated above.\n\n"
    + P3164_RUBRIC + "\n"
    + EXAMPLE_0_GPIO + "\n"
    + EXAMPLE_0_GNG + "\n"
    + EXAMPLE_0_AES
)

if __name__ == "__main__":
    print(ICL_ASSET_EXAMPLES_0)
