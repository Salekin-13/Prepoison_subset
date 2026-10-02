"""ICL_ASSET_EXAMPLES_01 with a ConceptualAssets section added to both worked outputs.

WHY THIS EXISTS. v01c4 asked the model for a top-level "ConceptualAssets" array and got it
in 0 of 90 files, while the "Concept" field -- which sits INSIDE "Assets", a place the
examples do show -- was adopted in 85 of 90. The examples demonstrate an output shape with
exactly two top-level keys, and that demonstration beat the written contract. This module
makes the demonstration agree with the instruction. It is the direct test of that
explanation: if the array now appears, the examples were the blocker.

BUILT BY TRANSFORMATION, NOT COPY. icl_examples_01 is imported and rewritten in memory, so
this file cannot drift from it, and v01 / v01c2 / v01c3 keep the byte-identical original.
Every edit is asserted; a silent no-op is impossible.

THE GROUPINGS ARE AUTHORED, NOT MECHANICAL. Each one is a real idea that several elements
carry between them, which is what P3164 3.1.2 describes -- the RTL that produces, stores and
transports one conceptual asset is usually several elements. GPIO's six p*_dout_en signals
genuinely are one idea; so are its six p*_sel signals. The AES key concept covers two
elements and the ciphertext concept covers one, deliberately: not every idea fans out, and
showing only fan-out would teach the model that concepts must always be plural.
"""
from __future__ import annotations

import json

import icl_examples_01 as _base

# concept id -> (text, objective, [element names it covers])
_GPIO_CONCEPTS = [
    ("C1", "Peripheral register write access -- whether a bus write is allowed to land in "
           "the GPIO register file at all", "Integrity", ["per_en", "per_we"]),
    ("C2", "Pin direction configuration -- which pins the device drives versus samples",
     "Integrity", [f"p{i}_dout_en" for i in range(1, 7)]),
    ("C3", "Pin function selection -- whether a pin is under GPIO control or handed to an "
           "alternate on-chip function", "Integrity", [f"p{i}_sel" for i in range(1, 7)]),
]

_AES_CONCEPTS = [
    ("C1", "Cipher key material -- the secret key as it enters the core and as it is "
           "presented to the final round", "Confidentiality", ["key", "key_in"]),
    ("C2", "Intermediate cipher state -- the partially transformed block between rounds",
     "Confidentiality", ["state_in"]),
    ("C3", "Ciphertext output -- the finished block leaving the core", "Availability",
     ["state_out"]),
]


def _span(s: str, needle: str):
    """Byte span of the JSON object containing `needle`, by brace matching."""
    k = s.index(needle)
    i = s.rindex("{", 0, k)
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return i, j + 1
    raise ValueError(f"unbalanced braces around {needle!r}")


def _rewrite(src: str, ip: str, concepts) -> str:
    a, b = _span(src, f'"IP": "{ip}"')
    obj = json.loads(src[a:b])

    # Original serialisation must round-trip, or the substitution would silently reformat
    # 97k characters of examples and make the diff unreadable.
    assert json.dumps(obj, indent=1) == src[a:b], f"{ip}: indent style is not json indent=1"

    owner = {e: cid for cid, _t, _o, elems in concepts for e in elems}
    covered = {e for _c, _t, _o, elems in concepts for e in elems}
    have = {x["Asset RTL"] for x in obj["Assets"]}
    assert covered == have, f"{ip}: concepts cover {sorted(covered)} but assets are {sorted(have)}"

    out = {"IP": obj["IP"],
           "ConceptualAssets": [{"id": cid, "Concept": text, "Security Objective": objective,
                                 "Why": why}
                                for cid, text, objective, why in
                                [(c, t, o, _why(ip, c)) for c, t, o, _e in concepts]],
           "Assets": [{**{"Asset Name": x["Asset Name"], "Concept": owner[x["Asset RTL"]]},
                       **{k: v for k, v in x.items() if k != "Asset Name"}}
                      for x in obj["Assets"]]}
    return src[:a] + json.dumps(out, indent=1) + src[b:]


_WHY = {
    ("omsp_gpio", "C1"): "Integrity: if writes can be forced or suppressed, every register "
                         "below is reachable by an attacker regardless of its own protection.",
    ("omsp_gpio", "C2"): "Integrity: flipping a pin from input to output lets the device "
                         "drive a line the board expects it to sample, and vice versa.",
    ("omsp_gpio", "C3"): "Integrity: re-selecting a pin hands it to a different on-chip "
                         "function, bypassing whatever the GPIO path was enforcing.",
    ("tiny_aes", "C1"): "Confidentiality: the key is the secret the whole core exists to "
                        "protect; exposure defeats the cipher outright.",
    ("tiny_aes", "C2"): "Confidentiality: the intermediate state is key-dependent, so "
                        "leaking it narrows the key search.",
    ("tiny_aes", "C3"): "Availability: if the output block can be stalled or corrupted the "
                        "core stops delivering usable ciphertext.",
}


def _why(ip, cid):
    return _WHY[(ip, cid)]


ICL_ASSET_EXAMPLES_01B = _rewrite(
    _rewrite(_base.ICL_ASSET_EXAMPLES_01, "omsp_gpio", _GPIO_CONCEPTS),
    "tiny_aes", _AES_CONCEPTS)

assert ICL_ASSET_EXAMPLES_01B != _base.ICL_ASSET_EXAMPLES_01, "01B is a no-op"
assert ICL_ASSET_EXAMPLES_01B.count('"ConceptualAssets"') == 2, "expected exactly 2 sections"
assert ICL_ASSET_EXAMPLES_01B.count('"Concept":') == 2 * 3 + 18, \
    "expected 6 concept definitions and 18 per-asset Concept ids"
