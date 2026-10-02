"""ICL_ASSET_EXAMPLES_01B_NOSUM with the PARSED PORTS/SIGNALS blocks removed as well.

WHY THIS EXISTS. Arm P-2 removes the parsed closed set from line 5's input and re-sources the
closed-set contract from the RTL's own declarations. Doing only that would leave the worked
examples showing a task that HAS two JSON blocks the real task no longer receives -- the same
input-parity failure that nearly wrecked P-1, and v01c4 established how strongly the examples
drive behaviour. This module makes the demonstration agree with the task.

WHAT IS AND IS NOT REMOVED. The two `=== PARSED ... (JSON) ===` blocks go, in both case
studies. The REASONING is untouched: every sentence in it that says "closed set" stays
literally true, because the core prompt now defines the closed set as the RTL's entity/port
and architecture-signal declarations rather than as the JSON blocks. Only one phrase moves --
"the closed set YOU ARE GIVEN" is no longer accurate once the model derives it -- and that is
a four-word deletion, not a rewrite. Contrast P-1, where the reasoning cited the summary BY
SECTION and genuinely could not survive its removal.

That distinction is the whole point of the arm: P-2 tests whether the model can build the
closed set itself. If the examples had to be re-reasoned to make that possible, the arm would
be measuring authored text rather than the model.

BUILT BY TRANSFORMATION, NOT COPY. icl_examples_01b_nosum is imported and rewritten in
memory, so this file cannot drift from it, and v01c6p1 keeps the byte-identical original.
"""
from __future__ import annotations

import icl_examples_01b_nosum as _base

_PORTS_HEAD = "=== PARSED I/O PORTS (JSON) ==="
_RTL_HEAD = "=== RTL ==="

# (old, new) -- the phrase is only true while the closed set arrives ready-made
_DECITE = (
    ("bind every asset to an exact name from the closed set you are given",
     "bind every asset to an exact name from the closed set"),
)


def _drop_parsed_blocks(text: str) -> str:
    """Remove every [PARSED I/O PORTS ... ) RTL] span, leaving the RTL header in place.

    Each case study lays its inputs out as PORTS, then SIGNALS, then RTL, so one span per
    case study covers both JSON blocks. Asserted rather than assumed: the count of removed
    spans must equal the number of case studies, and no PARSED header may survive.
    """
    out, removed = [], 0
    rest = text
    while True:
        i = rest.find(_PORTS_HEAD)
        if i < 0:
            out.append(rest)
            break
        j = rest.find(_RTL_HEAD, i)
        assert j > i, "a PARSED block is not followed by an RTL block -- layout changed"
        out.append(rest[:i])
        removed += 1
        rest = rest[j:]
    joined = "".join(out)
    assert removed == 2, f"expected 2 PARSED spans (one per case study), removed {removed}"
    return joined


_text = _drop_parsed_blocks(_base.ICL_ASSET_EXAMPLES_01B_NOSUM)
for _old, _new in _DECITE:
    assert _text.count(_old) == 1, f"de-citation anchor matches {_text.count(_old)}x: {_old[:50]!r}"
    _text = _text.replace(_old, _new)

ICL_ASSET_EXAMPLES_01B_NOPARSE = _text

# ---------------------------------------------------------------- invariants ---
# Gone: the blocks themselves and every field name that only existed inside them.
for _gone in (_PORTS_HEAD, "=== PARSED INTERNAL SIGNALS (JSON) ===", '"function":',
              '"dir":', '"kind":', "you are given"):
    assert _gone not in ICL_ASSET_EXAMPLES_01B_NOPARSE, \
        f"P-2 ICL: {_gone!r} survived the drop"

# Kept: both case studies, both RTL bodies, the reasoning, and the emitted objects. If any
# of these went with the JSON, the arm would be measuring a mutilated example set.
for _kept in ("### CASE STUDY 1: omsp_gpio", "### CASE STUDY 2: tiny_aes",
              "TARGET IP MODULE: omsp_gpio", "TARGET IP MODULE: tiny_aes",
              "module  omsp_gpio (", "module aes_128(clk, state, key, out);",
              "P3164 3.1.2 structural mapping", "closed set", "ConceptualAssets",
              '"Asset RTL"', '"Concept"'):
    assert _kept in ICL_ASSET_EXAMPLES_01B_NOPARSE, \
        f"P-2 ICL: {_kept!r} was lost -- the examples have been damaged, not ablated"

assert ICL_ASSET_EXAMPLES_01B_NOPARSE.count(_RTL_HEAD) == 2, "an RTL block was consumed"
assert len(ICL_ASSET_EXAMPLES_01B_NOPARSE) < len(_base.ICL_ASSET_EXAMPLES_01B_NOSUM), "no-op"
