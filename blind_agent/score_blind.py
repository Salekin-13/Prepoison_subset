"""Score blind-agent runs with the project scorer (eval_assets.score, strict), after converting each output to the
format eval_assets.load_run reads. Prompt versions are never mixed: one folder per (split, version, run).

  outputs   blind_agent/runs/<split>/<version>/r<k>/<module>.json       written by the executor agents
  scored    blind_agent/scored/<split>/<version>_r<k>/<module>.json      {"Assets": [{"Entity", "Asset RTL", "Security Objective"}]}

Output contracts handled:
  blind      {"module", "assets": [{"element", "entity", "security_objective", "reason"}]}     (the brief's contract)
  nested     {"conceptual assets": [... "related structural assets": [...]]}                  (m7e194es0ism; meta_tools.flatten)
  flat       {"Assets": [{"Asset RTL", "Entity", "Security Objective", ...}]}                  (v2x3r8's contract)
An element listed twice in one output is kept once (first objective), as meta_tools.flatten does.

    python blind_agent/score_blind.py tuning A1 B1 C1 ...
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in ("", "assetgen_meta"):
    sys.path.insert(0, str(ROOT / p))
import eval_assets as ea      # noqa: E402
import meta_tools as mt       # noqa: E402

B = ROOT / "blind_agent"
PARSED = {"tuning": ROOT / "parsed_tuning18", "heldout": ROOT / "parsed_heldout26"}


def closed(split, m):
    d = json.loads((PARSED[split] / f"{m}.json").read_text(encoding="utf-8"))
    return {(e["entity"], e["name"]) for k in ("ports", "signals") for e in d[k]}


def to_flat(obj) -> list[dict]:
    if isinstance(obj, dict) and isinstance(obj.get("assets"), list):
        rows = [{"Entity": a.get("entity", ""), "Asset RTL": a.get("element", ""),
                 "Security Objective": a.get("security_objective", "")} for a in obj["assets"] if isinstance(a, dict)]
    elif isinstance(obj, dict) and isinstance(obj.get("conceptual assets"), list):
        rows = mt.flatten(obj)["Assets"]
    elif isinstance(obj, dict) and isinstance(obj.get("Assets"), list):
        rows = [a for a in obj["Assets"] if isinstance(a, dict)]
    else:
        raise ValueError("no known output contract")
    seen, out = set(), []
    for r in rows:
        k = (r.get("Entity", ""), r.get("Asset RTL", ""))
        if k[1] and k not in seen:
            seen.add(k)
            out.append({"Entity": k[0], "Asset RTL": k[1], "Security Objective": r.get("Security Objective", "")})
    return out


def convert(split, version, rep) -> dict:
    """-> {module: note}. note 'ok', 'missing', 'unparseable: ...'; plus ungrounded counts (names not declared)."""
    src = B / "runs" / split / version / f"r{rep}"
    dst = B / "scored" / split / f"{version}_r{rep}"
    dst.mkdir(parents=True, exist_ok=True)
    notes = {}
    for f in sorted(src.glob("neorv32_*.json")):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
            rows = to_flat(obj)
        except Exception as e:
            notes[f.stem] = f"unparseable: {type(e).__name__}: {str(e)[:80]}"
            (dst / f"{f.stem}.json").unlink(missing_ok=True)
            continue
        cs = closed(split, f.stem)
        names = {n for _e, n in cs}
        ung = sum(1 for r in rows if (r["Entity"], r["Asset RTL"]) not in cs and r["Asset RTL"] not in names)
        (dst / f"{f.stem}.json").write_text(json.dumps({"Assets": rows}, indent=1), encoding="utf-8")
        notes[f.stem] = f"ok ({len(rows)} listed, {ung} not declared)"
    return notes


def modules(split):
    return sorted(p.stem for p in (B / "inputs" / split).glob("neorv32_*.txt"))


def score_version(split, version, reps, refs=None) -> dict:
    refs = refs or ea.load_refs(parsed_dir=str(PARSED[split]))
    gt = refs["gt"]
    mods = set(modules(split)) & set(gt)
    rows = []
    for k in reps:
        convert(split, version, k)
        d = B / "scored" / split / f"{version}_r{k}"
        have = {p.stem for p in d.glob("neorv32_*.json")}
        missing = sorted(mods - have)
        s = ea.score(d, gt, strict=True, only=mods)
        p, r = s["precision"], s["recall"]
        rows.append({"rep": k, "P": p, "R": r, "F1": 2 * p * r / (p + r) if p + r else 0.0, "emit": s["emit"],
                     "missing": missing, "per_module": s["per_module"]})
    n = len(rows)
    mean = {x: sum(r[x] for r in rows) / n for x in ("P", "R", "F1", "emit")} if n else {}
    return {"version": version, "split": split, "runs": rows, "mean": mean,
            "ref_entries": sum(len(gt[m]) for m in mods), "modules": len(mods)}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    split, versions = sys.argv[1], sys.argv[2:]
    for v in versions:
        reps = sorted(int(p.name[1:]) for p in (B / "runs" / split / v).glob("r*") if p.is_dir())
        res = score_version(split, v, reps)
        m = res["mean"]
        print(f"{v:8s} runs {len(reps)}  P {m['P']:.3f}  R {m['R']:.3f}  F1 {m['F1']:.3f}  emitted/run {m['emit']:.1f}  "
              f"({res['modules']} modules, {res['ref_entries']} entries)  per run "
              + " ".join(f"[{r['P']:.3f}/{r['R']:.3f}{' missing ' + str(len(r['missing'])) if r['missing'] else ''}]" for r in res["runs"]))
