"""Code leak check for a blind-agent prompt: no corpus identifier (tuning + held-out closed sets and the reference's
element names: anything with '_' or '.' of 4+ characters, plus 'neorv32'), no numeric emission hint, no instruction to
use comments (meta_tools.check_prompt's patterns), and prompts_v2.audit's known-identifier lists.
Reports only the offending strings found IN THE PROMPT, never the name list.

    python blind_agent/leak_check.py blind_agent/prompts/A1/prompt.md [...]
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in ("", "assetgen_meta"):
    sys.path.insert(0, str(ROOT / p))
sys.stdout.reconfigure(encoding="utf-8")
import meta_tools as mt     # noqa: E402


def names() -> set[str]:
    out = set(mt.corpus_names(str(ROOT)))
    for f in (ROOT / "parsed_heldout26").glob("*.json"):
        out.add(f.stem)
        d = json.loads(f.read_text(encoding="utf-8"))
        for k in ("ports", "signals"):
            out.update(e.get("name", "") for e in d.get(k, []) if isinstance(e, dict))
        out.update(d.get("entities", []))
    return {n for n in out if n and len(n) >= 4 and ("_" in n or "." in n or n == "neorv32")}


def check(path) -> dict:
    return mt.check_prompt(Path(path).read_text(encoding="utf-8"), names(), str(path))


if __name__ == "__main__":
    bad = 0
    for p in sys.argv[1:]:
        r = check(p)
        bad += not r["ok"]
        print(("PASS " if r["ok"] else "FAIL ") + p + ("" if r["ok"] else "\n   " + "\n   ".join(r["problems"])))
    sys.exit(1 if bad else 0)
