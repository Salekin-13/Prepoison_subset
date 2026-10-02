"""Step 8 (after the winner D1 was selected): the two prompts the winner is compared with, written verbatim as prompt
files for the same blind executor protocol.
  prompts/CUR/prompt.md   our current prompt m7e194es0ism (hand_arms/m7e194es0ism/exec_prompt.txt; sha12 0d0def4c6fe3)
  prompts/BASE/prompt.md  the baseline v2x3r8: prompts_v2.ASSET_V2_R8 + "\\n\\n" + icl_examples_01b_ot.ICL_ASSET_EXAMPLES_01B_OT
                          (its runs record system_prompt_sha256 3c543758f459..., 110,540 chars)
Each must reproduce the recorded fingerprint byte for byte, or nothing is written."""
import hashlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in ("", "assetgen_meta"):
    sys.path.insert(0, str(ROOT / p))
import meta_tools as mt           # noqa: E402
import prompts_v2                 # noqa: E402
import icl_examples_01b_ot        # noqa: E402

cur = (ROOT / "assetgen_meta/hand_arms/m7e194es0ism/exec_prompt.txt").read_text(encoding="utf-8")
base = prompts_v2.ASSET_V2_R8 + "\n\n" + icl_examples_01b_ot.ICL_ASSET_EXAMPLES_01B_OT
sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
assert mt.sha12(cur) == "0d0def4c6fe3", mt.sha12(cur)
assert sha(base).startswith("3c543758f459") and len(base) == 110540, (sha(base)[:12], len(base))
for v, t in (("CUR", cur), ("BASE", base)):
    d = ROOT / "blind_agent/prompts" / v
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.md").write_text(t, encoding="utf-8", newline="")
    back = (d / "prompt.md").read_bytes().decode("utf-8")
    assert back == t, f"{v}: file differs from the prompt"
    print(f"{v}: {len(t):,} chars, sha256 {sha(t)[:12]} -> {d / 'prompt.md'}")
