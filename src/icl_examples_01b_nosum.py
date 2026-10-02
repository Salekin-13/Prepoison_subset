"""ICL_ASSET_EXAMPLES_01B with the technical summary removed from both worked examples.

WHY THIS EXISTS. Arm P-1 removes the technical summary from line 5's input and from the core
prompt's declarations. Doing only that would leave the ICL examples showing a task that HAS a
summary -- and worse, their reasoning cites it by section:

    "NO. Summary 5: no keys, entropy, passwords or boot images ..."
    "... will be a conceptual asset." Summary section 5 says the same of this core ..."

So the model would be shown a worked procedure -- consult the summary -- that it cannot carry
out on the real task. Given what v01c4 established about how strongly the examples drive
behaviour, that is a confound rather than an ablation. This module makes the demonstration
agree with the task.

BUILT BY TRANSFORMATION, NOT COPY. icl_examples_01b is imported and rewritten in memory, so
this file cannot drift from it, and v01c5 / v01c6 keep the byte-identical original.

THE DE-CITATIONS ARE DELETIONS, NOT REWRITES. Each removes the pointer to the summary while
leaving the claim and its P3164 grounding untouched -- "Summary 5: no keys, entropy ..."
becomes "No keys, entropy ...". No reasoning is authored. That distinction matters: the v1
examples were rejected precisely because their content was invented rather than sourced.
"""
from __future__ import annotations

import icl_examples_01b as _base

_SUMMARY_HEAD = "=== TECHNICAL SUMMARY ==="
_NEXT_BLOCK = "=== PARSED I/O PORTS (JSON) ==="

# (old, new) -- pointer removed, claim and P3164 citation preserved verbatim
_DECITE = (
    ("     NO. Summary 5: no keys, entropy, passwords or boot images; payload is ordinary I/O\n",
     "     NO. No keys, entropy, passwords or boot images; payload is ordinary I/O\n"),
    ('     Therefore, any block ... that supports these secrets will be a conceptual asset." Summary\n'
     "     section 5 says the same of this core: the cipher key is a long-term secret and the input\n",
     '     Therefore, any block ... that supports these secrets will be a conceptual asset." The\n'
     "     same is true of this core: the cipher key is a long-term secret and the input\n"),
)


def _strip_summary_blocks(s: str) -> tuple:
    """Remove every '=== TECHNICAL SUMMARY ===' block up to the next parsed-ports header.

    Each block is preceded by 'TARGET IP MODULE: <name>\\n\\n', so removing it leaves exactly
    the shape build_asset_user(..., {"summary": False}) produces -- the example and the task
    then have identical structure.
    """
    out, n = s, 0
    while _SUMMARY_HEAD in out:
        i = out.index(_SUMMARY_HEAD)
        j = out.index(_NEXT_BLOCK, i)
        out = out[:i] + out[j:]
        n += 1
        assert n <= 4, "runaway strip -- more summary headers than expected"
    return out, n


_src = _base.ICL_ASSET_EXAMPLES_01B
_out, _n = _strip_summary_blocks(_src)
assert _n == 2, f"expected 2 summary blocks, removed {_n}"

for _old, _new in _DECITE:
    _c = _out.count(_old)
    assert _c == 1, f"de-citation anchor matches {_c} times, expected 1: {_old[:60]!r}"
    _out = _out.replace(_old, _new)

ICL_ASSET_EXAMPLES_01B_NOSUM = _out

# --- guarantees -------------------------------------------------------------------
assert _SUMMARY_HEAD not in ICL_ASSET_EXAMPLES_01B_NOSUM, "a summary block survived"
assert "Summary" not in ICL_ASSET_EXAMPLES_01B_NOSUM, "a summary reference survived"
assert "summary" not in ICL_ASSET_EXAMPLES_01B_NOSUM, "a summary reference survived"
# the examples must still demonstrate every OTHER block, and the whole output contract
for _probe, _want in ((_NEXT_BLOCK, 2), ("=== PARSED INTERNAL SIGNALS (JSON) ===", 2),
                      ("=== RTL ===", 2), ("TARGET IP MODULE", 2), ("EMITTED OUTPUT", 2),
                      ('"ConceptualAssets"', 2)):
    assert ICL_ASSET_EXAMPLES_01B_NOSUM.count(_probe) == _want, \
        f"{_probe!r}: expected {_want}, got {ICL_ASSET_EXAMPLES_01B_NOSUM.count(_probe)}"
# the P3164 grounding the de-citations sit inside must be untouched
assert ICL_ASSET_EXAMPLES_01B_NOSUM.count(
    'P3164 answers NO for its own GPIO pad') == 1, "GPIO P3164 citation damaged"
assert ICL_ASSET_EXAMPLES_01B_NOSUM.count(
    'Since this is a crypto IP, the plaintext data and key values are secrets') == 1, \
    "AES P3164 citation damaged"
assert _base.ICL_ASSET_EXAMPLES_01B == _src, "the base module was mutated"

del _src, _out, _n, _old, _new, _c, _probe, _want
