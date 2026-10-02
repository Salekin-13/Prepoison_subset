"""Counterfactuals on m7e194es0ist's own outputs (code, no model; tuning, 15 reference modules, 3 runs, strict). Each
row changes the lists the way a proposed fix would, to bound its effect before a new arm is built. Exploratory: not
pre-registered, so none of these rows is adoptable as such.

  T    drop transport record ports (meta_tools.convention_filter) and fields of ports
  I    promote every influence point the run listed to a reference (upper bound of removing the influence list)
  I*   promote only the influence points the run cites with GATES / SELECTS (decision elements), not forwarders
  BF   back-fill: add each whole input port (not clock / reset / transport / record field) whose flow-graph PATH reaches
       an element the same run reported as stores or computes
  MV   majority vote over the three runs (meta_tools.majority)
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "assetgen_meta", "blind_agent"):
    sys.path.insert(0, str(ROOT / p))
import eval_assets as ea          # noqa: E402
import meta_tools as mt           # noqa: E402
import trace_digest as TD         # noqa: E402
import diagnose as DG             # noqa: E402

V = "m7e194es0ist"
GT = ea.load_refs()["gt"]
MODS = sorted(m for m in GT if (ROOT / f"assets_tuning18_{V}_r0" / f"{m}.json").exists())
FLOW = ROOT / "assetgen_meta/traced_inputs/tuning/_flow"


def runs():
    return [{m: r[m] for m in MODS if m in r} for r in (ea.load_run(ROOT / f"assets_tuning18_{V}_r{k}") for k in range(3))]


def T(run):
    out = {}
    for m, lst in run.items():
        K = DG.kinds("tuning", m)
        kept = mt.convention_filter({m: lst})[m]
        out[m] = [x for x in kept if not K.get(x[1], "").startswith("port-field")]
    return out


def promote(run, k, only_decisions=False):
    out = {m: list(v) for m, v in run.items()}
    for m in MODS:
        o = TD._nested(V, k, m) or {}
        have = {x[1] for x in out.get(m, [])}
        for c in o.get("conceptual assets", []) or []:
            for ip in c.get("influence points", []) or []:
                if not isinstance(ip, dict):
                    continue
                t = ((ip.get("edge") or {}).get("type") or "")
                if only_decisions and t not in ("GATES", "SELECTS", "CONSTRAINS"):
                    continue
                n = ip.get("element")
                if n and n not in have:
                    out[m].append((ip.get("entity", ""), n, "Integrity")); have.add(n)
    return out


def backfill(run, k):
    out = {m: list(v) for m, v in run.items()}
    for m in MODS:
        f = FLOW / f"{m}.json"
        if not f.exists():
            continue
        fg = json.loads(f.read_text(encoding="utf-8"))
        o = TD._nested(V, k, m) or {}
        held = {s.get("asset rtl") for c in o.get("conceptual assets", []) or [] for s in c.get("related structural assets", []) or []
                if isinstance(s, dict) and s.get("realization") in ("stores", "computes")}
        have = {x[1] for x in out.get(m, [])}
        conv = {x[1] for x in out.get(m, [])} - {x[1] for x in mt.convention_filter({m: out.get(m, [])})[m]}
        for src, p in fg["paths"].items():
            if p["kind"] != "input" or "." in src or src in have or src in fg.get("clock_reset", []):
                continue
            if set(p["stores"]) & held:
                cand = [(fg["entity_of"].get(src, ""), src, "Integrity")]
                if mt.convention_filter({m: cand})[m]:          # not a transport record or clock / reset by name
                    out[m].append(cand[0]); have.add(src)
    return out


def score(lists):
    sc = [ea.score(r, GT, strict=True, only=set(MODS)) for r in lists]
    P = sum(s["precision"] for s in sc) / len(sc); R = sum(s["recall"] for s in sc) / len(sc)
    return f"P {P:.3f} R {R:.3f} F1 {2 * P * R / (P + R):.3f} emitted {sum(s['emit'] for s in sc) / len(sc):.1f}"


def main(log=print):
    import os
    os.chdir(ROOT)
    R = runs()
    rows = {
        "as run": R,
        "T": [T(r) for r in R],
        "I": [promote(r, k) for k, r in enumerate(R)],
        "I*": [promote(r, k, True) for k, r in enumerate(R)],
        "T + I*": [T(promote(r, k, True)) for k, r in enumerate(R)],
        "BF": [backfill(r, k) for k, r in enumerate(R)],
        "T + I* + BF": [T(backfill(promote(r, k, True), k)) for k, r in enumerate(R)],
    }
    for name, lists in rows.items():
        log(f"   {name:14s} {score(lists)}")
        if name in ("T", "T + I* + BF"):
            log(f"   {'MV + ' + name:14s} {score([mt.majority(lists)[0]])}")
    ism = [ea.load_run(ROOT / f"assets_tuning18_m7e194es0ism_r{k}") for k in range(3)]
    log(f"   {'ism as run':14s} {score([{m: r[m] for m in MODS if m in r} for r in ism])}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
