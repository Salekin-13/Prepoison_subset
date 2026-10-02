"""Pre-registered readings for the four-question arms (m7e194es0ismq vs m7e194es0ism; m7e194es0ismrq vs m7e194es0ismr).
All counts from the nested outputs and eval_assets.score; 15 GT modules, 3 runs each."""
import json, re, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "assetgen_meta"))
import eval_assets as ea, rtl_parse

PAIRS = {"m7e194es0ismq": "m7e194es0ism", "m7e194es0ismrq": "m7e194es0ismr"}
QS = ("confidentiality", "integrity", "availability", "undermined behavior")
norm = lambda s: re.sub(r"\s+", " ", (s or "").lower()).strip()


def read(arm, base=None, log=print):
    base = base or PAIRS[arm]
    gt = ea.load_refs()["gt"]; runs = ea.collect([base, arm]); common = ea.common_modules(runs, gt)
    rtl = {m: norm(rtl_parse.strip_comments(Path(f"RTL_data/{m}.vhd").read_text(encoding="utf-8", errors="ignore"), vhdl=True)) for m in common}
    gtn = {m: {n for n, _o in gt[m]} for m in common}
    c = Counter(); ans = Counter(); obj = Counter(); excl_gt = []
    for k in range(3):
        for m in common:
            f = Path(f"assets_tuning18_{arm}_r{k}/_nested/{m}.json")
            if not f.exists(): continue
            o = json.loads(f.read_text(encoding="utf-8"))
            for ce in o.get("conceptual assets", []) or []:
                c["concepts"] += 1; obj[ce.get("security objective")] += 1
                sq = ce.get("security questions") or {}
                c["four answers present"] += all(isinstance(sq.get(q), dict) and sq[q].get("answer") in ("yes", "no") for q in QS)
                for q in QS:
                    a = sq.get(q) if isinstance(sq.get(q), dict) else None
                    if not a: continue
                    ans[(q, a.get("answer"))] += 1
                    st = norm(a.get("statement"))
                    if a.get("answer") == "yes" and st:
                        c["yes with statement"] += 1; c["yes statement verbatim in RTL"] += (len(st) >= 12 and st in rtl[m])
            ex = o.get("excluded values") or []
            c["excluded values"] += len(ex)
            for e in ex:
                txt = " ".join(str(e.get(x, "")) for x in ("value", "failed", "statement"))
                hit = [n for n in gtn[m] if re.search(r"(?<![\w.])" + re.escape(n) + r"(?![\w])", txt)]
                if hit: excl_gt.append((k, m[8:], hit[:3]))
    log(f"{arm} vs {base} on {len(common)} modules, 3 runs")
    log(f"   compliance: concepts {c['concepts']}, with all four answers {c['four answers present']} "
        f"({c['four answers present'] / max(c['concepts'], 1):.0%}); yes answers with a statement {c['yes with statement']}, "
        f"verbatim in the RTL {c['yes statement verbatim in RTL']} ({c['yes statement verbatim in RTL'] / max(c['yes with statement'], 1):.0%})")
    for q in QS:
        y, n = ans[(q, "yes")], ans[(q, "no")]
        log(f"   {q:22s} yes {y:4d}  no {n:4d}")
    log(f"   objective mix: {dict(obj)}")
    log(f"   excluded values: {c['excluded values']} ({c['excluded values'] / 45:.1f} per module-run); naming a GT asset: {len(excl_gt)} "
        f"({len(excl_gt) / 3:.1f} per run; fail if > 1 per run) e.g. {excl_gt[:6]}")
    for v in (base, arm):
        sc = [ea.score(Path(f"assets_tuning18_{v}_r{k}"), gt, strict=True, only=common) for k in range(3)]
        log(f"   {v:16s} P {sum(s['precision'] for s in sc) / 3:.3f} R {sum(s['recall'] for s in sc) / 3:.3f} "
            f"emitted/run {sum(s['emit'] for s in sc) / 3:.1f}  (runs P {[round(s['precision'], 3) for s in sc]} R {[round(s['recall'], 3) for s in sc]})")


if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    for a in (sys.argv[1:] or PAIRS):
        read(a); print()
