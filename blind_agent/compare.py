"""Step 8 analysis (after selection): where the winner D1 and the comparison prompts differ, element by element, on the
same executor and inputs (tuning, 2 runs each), and code counterfactuals that apply one of the other prompts'
behaviours to D1's own outputs (no new run):
  CF1  drop port record fields (CUR and BASE list none)
  CF2  add every reference entry CUR finds in both runs and D1 in neither (upper bound of "adopt CUR's coverage")
Reference-side; main loop only.

    python blind_agent/compare.py
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in ("", "assetgen_meta", "blind_agent"):
    sys.path.insert(0, str(ROOT / p))
import eval_assets as ea      # noqa: E402
import score_blind as SB      # noqa: E402
import diagnose as DG         # noqa: E402

REFS = ea.load_refs()
GT = REFS["gt"]
MODS = set(SB.modules("tuning")) & set(GT)


def hits(version, reps=(0, 1)):
    """{(module, ref name): hit runs}, {(module, fp name): fp runs}."""
    h, f = Counter(), Counter()
    for k in reps:
        SB.convert("tuning", version, k)
        s = ea.score(SB.B / "scored/tuning" / f"{version}_r{k}", GT, strict=True, only=MODS)
        for m in MODS:
            miss = Counter(s["per_module"][m]["fn"])
            for n, _o in GT[m]:
                if miss[n] > 0:
                    miss[n] -= 1
                else:
                    h[(m, n)] += 1
            for n in set(s["per_module"][m]["fp"]):
                f[(m, n)] += 1
    return h, f


def kind(m, n):
    return DG.kinds("tuning", m).get(n, "absent")


def table(a, b, ha, hb):
    only_b = sorted(k for k in set(hb) | set(ha) if hb[k] == 2 and ha[k] == 0)
    only_a = sorted(k for k in set(hb) | set(ha) if ha[k] == 2 and hb[k] == 0)
    for title, L in ((f"reference entries {b} finds in both runs, {a} in neither", only_b),
                     (f"reference entries {a} finds in both runs, {b} in neither", only_a)):
        by = defaultdict(list)
        for m, n in L:
            by[kind(m, n)].append(f"{m[8:]}/{n}")
        print(f"  {title}: {len(L)}")
        for k, xs in sorted(by.items()):
            print(f"     {k:15s} {len(xs):3d}: " + ", ".join(xs))
    return only_b


def run_lists(version, reps=(0, 1)):
    return [ea.load_run(SB.B / "scored/tuning" / f"{version}_r{k}") for k in reps]


def score_lists(lists):
    sc = [ea.score(r, GT, strict=True, only=MODS) for r in lists]
    P = sum(s["precision"] for s in sc) / len(sc)
    R = sum(s["recall"] for s in sc) / len(sc)
    return P, R, 2 * P * R / (P + R), sum(s["emit"] for s in sc) / len(sc)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    H = {v: hits(v) for v in ("D1", "CUR", "BASE")}
    print("D1 vs CUR")
    cur_only = table("D1", "CUR", H["D1"][0], H["CUR"][0])
    print("D1 vs BASE")
    table("D1", "BASE", H["D1"][0], H["BASE"][0])
    d1 = run_lists("D1")
    print("\ncounterfactuals on D1's own two runs (code, no new run):")
    print("   D1 as run                    P %.3f R %.3f F1 %.3f emitted %.1f" % score_lists(d1))
    cf1 = [{m: [x for x in r[m] if not ("." in x[1] and kind(m, x[1]).startswith("port"))] for m in r} for r in d1]
    print("   CF1 drop port record fields  P %.3f R %.3f F1 %.3f emitted %.1f" % score_lists(cf1))
    cf2 = [{m: r[m] + [("", n, "Integrity") for (mm, n) in cur_only if mm == m] for m in r} for r in cf1]
    print("   CF1 + CF2 add CUR-only hits  P %.3f R %.3f F1 %.3f emitted %.1f   (upper bound: only the reference entries, no extra FP)" % score_lists(cf2))
