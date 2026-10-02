"""Split the winner's two worked examples (m7e194es0ism exec_prompt.txt after 'WORKED EXAMPLES') into parts for the
traced arm: the RTL numbered as the traced inputs are (each line prefixed with its line number, blank lines left out),
the old private analysis, and the old final object. Writes examples/<name>.source.json. The example decisions (the
concepts and their structural references) are kept; only the evidence is added later."""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
W = (ROOT / "assetgen_meta/hand_arms/m7e194es0ism/exec_prompt.txt").read_text(encoding="utf-8")
head, ex = W.split("\nWORKED EXAMPLES\n", 1)
intro, rest = ex.split("### WORKED EXAMPLE 1:", 1)
blocks = re.split(r"\n### WORKED EXAMPLE \d+: ", "### WORKED EXAMPLE 1:" + rest)
out = HERE / "examples"
out.mkdir(exist_ok=True)
for b in blocks:
    b = b.replace("### WORKED EXAMPLE 1:", "").strip()
    name = b.split("\n", 1)[0].strip()
    rtl = b.split("=== RTL ===\n", 1)[1].split("\nIdentify the primary security assets for", 1)[0].rstrip("\n")
    analysis = b.split("PRIVATE ANALYSIS (a demonstration of the procedure; never part of an answer)\n", 1)[1].split("\nFINAL OBJECT\n", 1)[0]
    final = json.loads(b.split("\nFINAL OBJECT\n", 1)[1].strip())
    lines = rtl.split("\n")
    numbered = "\n".join(f"{i:>5} | {l.rstrip()}" for i, l in enumerate(lines, 1) if l.strip())
    refs = [(c["concept"], s["asset rtl"], s["entity"], s["realization"]) for c in final["conceptual assets"] for s in c["related structural assets"]]
    (out / f"{name}.source.json").write_text(json.dumps({"name": name, "rtl_numbered": numbered, "old_analysis": analysis,
                                                          "old_final": final, "n_refs": len(refs)}, indent=1), encoding="utf-8")
    print(f"{name}: {len(lines)} RTL lines ({numbered.count(chr(10)) + 1} non-blank), {len(final['conceptual assets'])} concepts, "
          f"{len(refs)} structural references, old analysis {len(analysis):,} chars")
print("intro:", intro.strip()[:200])
