"""Recover examples/<name>.adapted.json of arm m7e194es0ist from its built prompt (exec_prompt.txt, sha fa07ad720438).
Needed once (2026-10-02): a concurrent run of an old version of m7e194es0ist2/examples_ist2.py check overwrote both files
with the ist2 format. The prompt holds the examples exactly as check_examples.assemble wrote them, so each part is cut
back out, and the recovery is accepted only if re-assembling the recovered parts reproduces the prompt byte for byte."""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1])); sys.path.insert(0, str(HERE.parents[2]))
import check_examples as CE      # noqa: E402

P = (HERE / "exec_prompt.txt").read_text(encoding="utf-8")
assert hashlib.sha256(P.encode("utf-8")).hexdigest()[:12] == "fa07ad720438"
instr = (HERE / "instructions.md").read_text(encoding="utf-8").rstrip() + "\n\n"
blocks = []
for i, n in ((1, "omsp_gpio"), (2, "tiny_aes")):
    start = P.index(f"### WORKED EXAMPLE {i}: {n}")
    end = P.index("### WORKED EXAMPLE 2:") if i == 1 else len(P)
    b = P[start:end]
    mp = b.split(CE.HEAD_MAP + "\n", 1)[1].split("\n\n" + CE.HEAD_FLOW + "\n", 1)[0]
    fl = b.split(CE.HEAD_FLOW + "\n", 1)[1].split("\n\nIdentify the primary security assets for", 1)[0]
    an = b.split("PRIVATE ANALYSIS (a demonstration of the procedure; never part of an answer)\n", 1)[1].split("\n\nFINAL OBJECT\n", 1)[0]
    fo = json.loads(b.split("\nFINAL OBJECT\n", 1)[1])
    ad = {"map_excerpt": mp, "flow_excerpt": fl, "analysis": an, "final_object": fo}
    src = json.loads((HERE / "examples" / f"{n}.source.json").read_text(encoding="utf-8"))
    blocks.append((n, ad, CE.assemble(i, src, ad)))
rebuilt = P[:P.index("### WORKED EXAMPLE 1:")] + "\n".join(x[2] for x in blocks)
same = rebuilt == P
print("re-assembled prompt equals exec_prompt.txt byte for byte:", same)
assert same, "recovery does not reproduce the prompt: nothing written"
for n, ad, _t in blocks:
    (HERE / "examples" / f"{n}.adapted.json").write_text(json.dumps(ad, indent=1), encoding="utf-8")
    k = ad["final_object"]["conceptual assets"][0].keys()
    print(f"recovered {n}: final object keys {sorted(k)}; hypotheses {'hypotheses' in ad['final_object']}")
