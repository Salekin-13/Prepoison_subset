"""Main-loop analysis only (reference-side): per version, the reference entries missed in EVERY run and the false
positives listed in EVERY run, with element kind and the map's storage. Prints counts by kind and the element lists.

    python blind_agent/misses.py tuning D1 [CUR ...]
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

MAPS = {"tuning": ROOT / "step1/lasset_step1/relation_map_code_tuning/b0e767000ec2_codetags",
        "heldout": ROOT / "step1/lasset_step1/relation_map_code_heldout/b0e767000ec2_codetags"}


def storage(split, m):
    d = json.loads((MAPS[split] / f"{m}.json").read_text(encoding="utf-8"))
    return {e["name"]: e.get("storage", "?") for a in ("ports", "signals") for e in d[a]}


def always(split, version, reps):
    refs = ea.load_refs(parsed_dir=str(SB.PARSED[split]))
    res = SB.score_version(split, version, reps, refs)
    miss, fp = Counter(), Counter()
    for r in res["runs"]:
        for m, pm in r["per_module"].items():
            for n in set(pm["fn"]):
                miss[(m, n)] += 1
            for n in set(pm["fp"]):
                fp[(m, n)] += 1
    n = len(res["runs"])
    return res, sorted(k for k, c in miss.items() if c == n), sorted(k for k, c in fp.items() if c == n)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    split, versions = sys.argv[1], sys.argv[2:]
    for v in versions:
        reps = sorted(int(p.name[1:]) for p in (SB.B / "runs" / split / v).glob("r*") if p.is_dir())
        res, M, F = always(split, v, reps)
        for title, L in (("missed in every run", M), ("false positive in every run", F)):
            by = defaultdict(list)
            for m, n in L:
                K, S = DG.kinds(split, m), storage(split, m)
                by[K.get(n, "absent")].append(f"{m[8:]}/{n}[{S.get(n, '?')[:4]}]")
            print(f"{v} ({len(reps)} runs) {title}: {len(L)}")
            for k, xs in sorted(by.items()):
                print(f"   {k:15s} {len(xs):3d}: " + ", ".join(xs))
