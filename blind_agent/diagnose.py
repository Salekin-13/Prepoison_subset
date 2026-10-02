"""Reference-side diagnosis of blind-agent runs (for the main loop's analysis ONLY; never shown to a designer or critic).
Per version: reference hits and false positives by element kind (input port, output port, internal signal, internal
record field, port record field), and emitted per module. Kinds from the closed set.

    python blind_agent/diagnose.py tuning A1 B1 ...
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in ("", "assetgen_meta", "blind_agent"):
    sys.path.insert(0, str(ROOT / p))
import eval_assets as ea      # noqa: E402
import score_blind as SB      # noqa: E402


def kinds(split, m):
    d = json.loads((SB.PARSED[split] / f"{m}.json").read_text(encoding="utf-8"))
    out = {}
    for e in d["ports"]:
        out.setdefault(e["name"], ("port-field " if "." in e["name"] else "port-") + (e.get("dir") or "?"))
    for e in d["signals"]:
        out.setdefault(e["name"], "signal-field" if "." in e["name"] else "signal")
    return out


def diagnose(split, version, reps):
    refs = ea.load_refs(parsed_dir=str(SB.PARSED[split]))
    gt = refs["gt"]
    res = SB.score_version(split, version, reps, refs)
    ref_k, hit_k, fp_k = Counter(), Counter(), Counter()
    for r in res["runs"]:
        for m, pm in r["per_module"].items():
            K = kinds(split, m)
            miss = Counter(pm["fn"])
            for n, _o in gt[m]:
                k = K.get(n, "absent")
                ref_k[k] += 1
                if miss[n] > 0:
                    miss[n] -= 1
                else:
                    hit_k[k] += 1
            for n in pm["fp"]:
                fp_k[K.get(n, "absent")] += 1
    n = len(res["runs"])
    return res, {k: (ref_k[k] / n, hit_k[k] / n, fp_k[k] / n) for k in sorted(set(ref_k) | set(fp_k))}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    split, versions = sys.argv[1], sys.argv[2:]
    for v in versions:
        reps = sorted(int(p.name[1:]) for p in (SB.B / "runs" / split / v).glob("r*") if p.is_dir())
        res, tab = diagnose(split, v, reps)
        m = res["mean"]
        print(f"{v}: P {m['P']:.3f} R {m['R']:.3f} emitted/run {m['emit']:.1f}")
        for k, (nr, h, f) in tab.items():
            print(f"   {k:16s} reference {nr:5.1f}  hit {h:5.1f}  FP {f:5.1f}")
