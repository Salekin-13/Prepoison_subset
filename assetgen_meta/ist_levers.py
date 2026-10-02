"""Evaluation-layer levers for the traced arms (m7e194es0ist, m7e194es0ist2): code applied to the executor's lists after
generation, each reported as its own labelled row (ASSET_DEFINITION.md section 4). No model call.

  T   drop transport record ports and clock / reset inputs (meta_tools.convention_filter) and every field of a port
      (the closed set excludes port fields; the reference lists none). Basis: the winner's transport and port rules.
  BF  back-fill: add each whole input port, not clock / reset / transport / record field, whose flow-graph PATH reaches
      an element the same run reported as stores or computes (the consumed-input rule applied by code; the lever
      adopted on held-out, here driven by the code flow graph instead of quote traces).
  MV  majority vote over the runs (meta_tools.majority).
Stacks compose left to right, e.g. "T+BF", "MV+T+BF" (MV last).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT), str(HERE), str(ROOT / "blind_agent")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eval_assets as ea          # noqa: E402
import meta_tools as mt           # noqa: E402

FLOW = HERE / "traced_inputs" / "tuning" / "_flow"


def _port_fields(m: str) -> set:
    d = json.loads((ROOT / "parsed_tuning18" / f"{m}.json").read_text(encoding="utf-8"))
    return {e["name"] for e in d["ports"] if "." in e["name"]}


def T(run: dict) -> dict:
    out = {}
    for m, lst in run.items():
        pf = _port_fields(m)
        out[m] = [x for x in mt.convention_filter({m: lst})[m] if x[1] not in pf]
    return out


def BF(run: dict, nested: dict) -> dict:
    """nested: {module: the run's nested output} (for the realization labels)."""
    out = {m: list(v) for m, v in run.items()}
    for m in out:
        f = FLOW / f"{m}.json"
        if not f.exists():
            continue
        fg = json.loads(f.read_text(encoding="utf-8"))
        o = nested.get(m) or {}
        held = {s.get("asset rtl") for c in o.get("conceptual assets", []) or [] if isinstance(c, dict)
                for s in c.get("related structural assets", []) or [] if isinstance(s, dict) and s.get("realization") in ("stores", "computes")}
        have = {x[1] for x in out[m]}
        for src, p in fg["paths"].items():
            if p["kind"] != "input" or "." in src or src in have or src in fg.get("clock_reset", []):
                continue
            if set(p["stores"]) & held:
                cand = [(fg["entity_of"].get(src, ""), src, "Integrity")]
                if mt.convention_filter({m: cand})[m]:
                    out[m].append(cand[0]); have.add(src)
    return out


def stack(version: str, name: str, reps=(0, 1, 2), modules=None, stem="assets_tuning18") -> list[dict]:
    """The scored lists of a stack: one per run, or the voted list for an MV stack."""
    parts = [p for p in name.split("+") if p and p != "base"]
    mv = "MV" in parts
    runs = []
    for k in reps:
        d = ROOT / f"{stem}_{version}_r{k}"
        run = ea.load_run(d)
        if modules is not None:
            run = {m: v for m, v in run.items() if m in modules}
        nested = {m: json.loads((d / "_nested" / f"{m}.json").read_text(encoding="utf-8")) for m in run
                  if (d / "_nested" / f"{m}.json").exists()}
        for p in parts:
            if p == "T":
                run = T(run)
            elif p == "BF":
                run = BF(run, nested)
        runs.append(run)
    return [mt.majority(runs)[0]] if mv else runs


def score(version: str, name: str, gt: dict, modules, reps=(0, 1, 2)) -> dict:
    lists = stack(version, name, reps, set(modules))
    sc = [ea.score(r, gt, strict=True, only=set(modules)) for r in lists]
    n = len(sc)
    return {"precision": sum(s["precision"] for s in sc) / n, "recall": sum(s["recall"] for s in sc) / n,
            "emit": sum(s["emit"] for s in sc) / n}


def selftest(log=print) -> bool:
    """The same rows as hand_arms/counterfactuals_ist.py computed independently on m7e194es0ist: T 0.396 / 0.688,
    BF 0.369 / 0.733 (3 decimals)."""
    gt = ea.load_refs()["gt"]
    mods = sorted(m for m in gt if (ROOT / "RTL_data" / f"{m}.vhd").exists())
    ok = True
    for name, want in (("T", (0.396, 0.688)), ("BF", (0.369, 0.733))):
        s = score("m7e194es0ist", name, gt, mods)
        got = (round(s["precision"], 3), round(s["recall"], 3))
        ok &= got == want
        log(f"   ist_levers {name}: {got} (counterfactuals_ist {want}) {'ok' if got == want else 'MISMATCH'}")
    return ok


if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(0 if selftest() else 1)
