"""Where is the recall actually lost? Per-stage ceiling analysis.

In a pipeline, tuning the wrong stage costs months. The way to find the right one is to
ask, per stage: if this stage were PERFECT, how much would the end metric improve? That
bounds the payoff available in each stage before any tuning is done.

  stage 4 (LLMparse)  ceiling = fraction of ground-truth elements that are IN the closed
                      set at all. An element that is not there cannot be emitted.
  stage 5 (LLMasset)  the remaining gap, i.e. everything reachable but not emitted.

Also measures the parser's OTHER effect, which is on precision rather than recall: the
closed set is the list of candidates shown to the model, so its size is the distractor
count.
"""
import io
import json
import sys
from pathlib import Path

PROJ = Path(r"E:\jobs\ff\test\Prepoison_subset")
sys.path.insert(0, str(PROJ))
import eval_assets as EA                                              # noqa: E402

gt = EA.load_refs(PROJ / "ground_truth")["gt"]
closed, dotted = {}, {}
for f in sorted((PROJ / "parsed_tuning18").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    els = d.get("ports", []) + d.get("signals", [])
    closed[f.stem] = {e["name"] for e in els}
    dotted[f.stem] = {e["name"] for e in els if "." in e["name"]}

print("=" * 86)
print("CLOSED-SET SIZE vs GROUND-TRUTH SIZE  (the model picks k assets out of N candidates)")
print("=" * 86)
print(f"{'module':26s} {'N closed':>9s} {'of which dotted':>16s} {'GT k':>5s} {'k/N':>7s}")
tot_n = tot_d = tot_k = 0
for m in sorted(closed):
    if m not in gt:
        continue
    n, dd, k = len(closed[m]), len(dotted[m]), len(gt[m])
    tot_n += n; tot_d += dd; tot_k += k
    print(f"{m:26s} {n:9d} {dd:9d} ({100*dd/n:3.0f}%) {k:5d} {k/n:7.3f}")
print("-" * 86)
print(f"{'TOTAL':26s} {tot_n:9d} {tot_d:9d} ({100*tot_d/tot_n:3.0f}%) {tot_k:5d} {tot_k/tot_n:7.3f}")

print("\n" + "=" * 86)
print("PER-STAGE RECALL CEILING")
print("=" * 86)
reach = sum(1 for m in gt if m in closed
            for e, _o in gt[m]
            if e in closed[m] or e.split(".")[0] in closed[m]
            or any(c.split(".")[0] == e for c in closed[m]))
tot = sum(len(gt[m]) for m in gt if m in closed)
print(f"  ground-truth elements in scoreable modules : {tot}")
print(f"  reachable in the closed set                : {reach}")
print(f"  -> stage 4 (LLMparse) recall ceiling       : {reach/tot:.3f}")
print(f"     loss attributable to parsing            : {1-reach/tot:.3f}")
print()
print("  Stage 5 owns everything between its measured recall and that ceiling:")
print("  the whole gap between an arm's measured recall and this number.")
