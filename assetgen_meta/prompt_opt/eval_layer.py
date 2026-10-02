"""Evaluation-layer row R1a (ASSET_DEFINITION.md section 3/5): a code filter applied after generation, reported as its
own labelled row next to the headline, never folded into it. Basis: none (derived from reference counts), like GUARD.

R1a removes a listed element that is a stored signal (storage edge or mixed) with no connection of mode in into a
sub-unit, whose driving records (self-targets and read-backs into output-port fields left out) all target whole output
ports of its entity, none of them CARRIES. Origin: prompt-optimization iteration 2 (edit D, withdrawn from the prompt).
Moved here from scratch_archive/v1err/{mapparse,multi,rules}.py; same logic, split-aware.

Random-thinning baseline: remove the same number of listed entries uniformly at random (fixed seed, 2000 draws) and
report the mean precision after, and the share of draws whose precision reaches R1a's.

    python assetgen_meta/prompt_opt/eval_layer.py --selftest
    python assetgen_meta/prompt_opt/eval_layer.py <run dir> [--heldout]
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import eval_assets as ea  # noqa: E402

DRIVE = {"CARRIES", "SOURCES", "GATES", "SELECTS", "CONSTRAINS", "SEQUENCES", "RESETS"}


def parse(split: str, module: str) -> dict:
    els, cur = {}, None
    inp = ROOT / "assetgen_meta/traced_inputs_v2" / split / f"{module}.txt"
    for line in inp.read_text(encoding="utf-8").splitlines():
        if line.startswith("=== RELATIONSHIP MAP: FLOW GRAPH"):
            break
        m = re.match(r"^(PORT|SIGNAL) (\{.*\})$", line)
        if m:
            d = json.loads(m.group(2))
            d.update(cls=m.group(1), records=[], connections=[])
            cur = (d["entity"], d["name"])
            els[cur] = d
            continue
        if cur and line.startswith("    {"):
            r = json.loads(line.strip())
            if "connections" in r:
                els[cur]["connections"] += r["connections"]
            elif "type" in r and "occurrences" not in r:
                els[cur]["records"].append(r)
        elif not line.startswith("    "):
            cur = None
    return els


def _target_class(els, ent, me, t):
    if t == me:
        return "self"
    ports = {k[1]: v for k, v in els.items() if k[0] == ent and v["cls"] == "PORT"}
    if t in ports:
        if "." in t:
            return "portfield-" + ports[t]["boundary"]["mode"]
        has_fields = any(k.startswith(t + ".") for k in ports)
        return ("recport-" if has_fields else "port-") + ports[t]["boundary"]["mode"]
    return "int"


def R1a(d: dict, els: dict) -> bool:
    if d["cls"] != "SIGNAL" or d.get("storage") not in ("edge", "mixed"):
        return False
    if any(c.get("mode") == "in" for c in d["connections"]):
        return False
    dl = [(rec["type"], _target_class(els, d["entity"], d["name"], t))
          for rec in d["records"] if rec["type"] in DRIVE for t in rec["targets"]]
    dl = [x for x in dl if x[1] not in ("self", "portfield-out")]
    return bool(dl) and all(c == "port-out" for _, c in dl) and not any(ty == "CARRIES" for ty, _ in dl)


def apply(run: str | Path, split: str = "tuning", draws: int = 2000, seed: int = 0, only: set | None = None) -> dict:
    import opt_tools as OT
    gt = ea.load_refs()["gt"]
    mods = sorted(only) if only else OT.modules(split)
    run = Path(run) if Path(run).is_absolute() else ROOT / run
    res = ea.score(run, gt, strict=True, only=set(mods))
    TP0, FP0, FN0 = res["tp"], res["fp"], res["fn"]
    rows, fp_hit, tp_hit = [], [], []
    for m in mods:
        f = run / f"{m}.json"
        if not f.exists():
            continue
        els = parse(split, m)
        fpm = Counter(res["per_module"].get(m, {}).get("fp", []))
        for a in json.loads(f.read_text(encoding="utf-8"))["Assets"]:
            n, ent = a["Asset RTL"], a["Entity"]
            lab = "FP" if fpm[n] > 0 else "TP"
            if lab == "FP":
                fpm[n] -= 1
            rows.append(lab)
            d = els.get((ent, n)) or next((v for k, v in els.items() if k[1] == n), None)
            if d is not None and R1a(d, els):
                (fp_hit if lab == "FP" else tp_hit).append((m, n))
    f1 = lambda P, R: 2 * P * R / (P + R) if P + R else 0.0
    P0, R0 = TP0 / (TP0 + FP0), TP0 / (TP0 + FN0)
    TP, FP = TP0 - len(tp_hit), FP0 - len(fp_hit)
    P, R = TP / (TP + FP), TP / (TP0 + FN0)
    k = len(fp_hit) + len(tp_hit)
    rnd = random.Random(seed)
    ps = []
    for _ in range(draws):
        drop = rnd.sample(rows, k) if k <= len(rows) else rows
        dt = sum(1 for x in drop if x == "TP")
        ps.append((TP0 - dt) / (TP0 + FP0 - k) if TP0 + FP0 - k else 0.0)
    return {"run": run.name, "split": split, "base": (TP0, FP0, FN0, round(P0, 3), round(R0, 3), round(f1(P0, R0), 3)),
            "removed_fp": len(fp_hit), "removed_tp": len(tp_hit), "tp_lost": tp_hit,
            "after": (TP, FP, FN0 + len(tp_hit), round(P, 3), round(R, 3), round(f1(P, R), 3)),
            "thinning_mean_P": round(sum(ps) / len(ps), 3), "thinning_share_ge": round(sum(p >= P for p in ps) / len(ps), 4)}


def selftest() -> bool:
    """Reproduces the iteration-2/3 measurements made with the scratch scripts in this session (2026-10-02)."""
    want = {"assets_opt_v1_r0": (21, 0, 0.570), "assets_opt_v1_r1": (21, 0, 0.557),
            "assets_opt_v0_r0": (22, 0, 0.500), "assets_opt_v0_r1": (22, 0, 0.528)}
    ok = True
    for run, (fp, tp, F1) in want.items():
        r = apply(run, "tuning", draws=10)
        good = (r["removed_fp"], r["removed_tp"], r["after"][5]) == (fp, tp, F1)
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {run}: removes FP {r['removed_fp']} TP {r['removed_tp']}, F1 -> {r['after'][5]} (want {fp}/{tp}/{F1})")
    print("self-test", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "--selftest":
        sys.exit(0 if selftest() else 1)
    print(json.dumps(apply(sys.argv[1], "heldout" if "--heldout" in sys.argv else "tuning"), indent=1))
