"""Prompt optimization loop (user request 2026-10-02): Claude agents execute each prompt version on the 15 tuning
modules; code scores, maps every error, and keeps every version. The reference (ground_truth/) and the evaluation set
are never modified. Optimization log: assetgen_meta/prompt_opt/OPTIMIZATION_LOG.md.

  versions   assetgen_meta/prompt_opt/v<i>/{instructions.md, exec_prompt.txt, build_info.json, change.md}
             exec_prompt = instructions + the ist2 worked examples (hand_arms/m7e194es0ist2/examples, decisions fixed)
  runs       assets_opt_v<i>_r<k>/_nested/<module>.json   (executor output)   and   <module>.json (flattened, scored)
  inputs     assetgen_meta/traced_inputs_v2/tuning/<module>.txt (numbered RTL + map + flow graph)

    python assetgen_meta/prompt_opt/opt_tools.py build v<i>      checks + assemble
    python assetgen_meta/prompt_opt/opt_tools.py eval v<i> [k] [prev] [--heldout]   flatten, score, error map -> v<i>/[heldout_]eval_r<k>.json/.md
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in ("", "assetgen_meta", "blind_agent", "assetgen_meta/hand_arms/m7e194es0ist2"):
    sys.path.insert(0, str(ROOT / _p))

import eval_assets as ea          # noqa: E402
import meta_tools as mt           # noqa: E402

STEM = "assets_opt"
IST2 = ROOT / "assetgen_meta/hand_arms/m7e194es0ist2"
INTRO = ("WORKED EXAMPLES\n\nThe cases below apply the procedure above to designs outside the evaluation set. Each shows the "
         "input as you receive it (the relationship map is shortened to the elements the example cites; a real input lists "
         "every element), the private analysis stage by stage, and the final object. The analysis is shown only to "
         "demonstrate the procedure: your answer is the final JSON object alone. Each final object contains the conceptual "
         "assets worked through in its analysis. Where an analysis names further established conceptual assets of its "
         "design, a complete answer reports those as well.\n\n")


def modules(split: str = "tuning"):
    gt = ea.load_refs()["gt"]
    src = ROOT / ("RTL_data" if split == "tuning" else "RTL_heldout")
    return sorted(m for m in gt if (src / f"{m}.vhd").exists())


def stem(split: str = "tuning") -> str:
    """Run folders: assets_opt_<v>_r<k> (tuning), assets_opt_heldout_<v>_r<k> (held-out); never mixed in one metric."""
    return STEM if split == "tuning" else f"{STEM}_heldout"


def build(v: str, log=print) -> dict:
    import examples_ist2 as EX
    import leak_check as LC
    d = HERE / v
    instr = (d / "instructions.md").read_text(encoding="utf-8").rstrip() + "\n\n"
    assert EX.check(log=lambda *a: None), "worked examples fail their checks"
    full = instr + INTRO + EX.assemble_all()
    r = mt.check_exec_prompt(full, mt.corpus_names(), v)
    assert r["ok"], r["problems"]
    r = mt.check_prompt(instr, LC.names(), v)            # instructions: no tuning or held-out identifier, no quota
    assert r["ok"], r["problems"]
    (d / "exec_prompt.txt").write_text(full, encoding="utf-8")
    info = {"version": v, "system_sha12": mt.sha12(full), "instructions_sha12": mt.sha12(instr), "chars": len(full),
            "instructions_chars": len(instr), "inputs": "assetgen_meta/traced_inputs_v2/tuning",
            "checks": "examples_ist2 7 checks; check_exec_prompt; leak check on the instructions (tuning + held-out names)"}
    (d / "build_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    log(f"{v}: sha {info['system_sha12']}, {len(full):,} chars (instructions {len(instr):,}); checks PASS")
    return info


def flatten_run(v: str, k: int = 0, split: str = "tuning") -> int:
    d = ROOT / f"{stem(split)}_{v}_r{k}"
    n = 0
    for f in sorted((d / "_nested").glob("*.json")):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        obj["module name"] = f.stem
        (d / f"{f.stem}.json").write_text(json.dumps(mt.flatten(obj), indent=1), encoding="utf-8")
        n += 1
    return n


def kind(m, n):
    d = json.loads((ROOT / "parsed_tuning18" / f"{m}.json").read_text(encoding="utf-8"))
    for e in d["ports"]:
        if e["name"] == n:
            return ("port-field " if "." in n else "port-") + (e.get("dir") or "?")
    for e in d["signals"]:
        if e["name"] == n:
            return "signal-field" if "." in n else "signal"
    return "absent"


def evaluate(v: str, k: int = 0, prev: str | None = None, log=print, split: str = "tuning") -> dict:
    import trace_check as TC
    import trace_digest as TD
    import traced_inputs as TI
    gt = ea.load_refs()["gt"]
    mods = modules(split)
    st = stem(split)
    n_flat = flatten_run(v, k, split)
    d = ROOT / f"{st}_{v}_r{k}"
    s = ea.score(d, gt, strict=True, only=set(mods))
    P, R = s["precision"], s["recall"]
    F1 = 2 * P * R / (P + R) if P + R else 0.0
    missing = sorted(set(mods) - {f.stem for f in (d / "_nested").glob("*.json")})
    per_mod, fpk, fnk, where, roles_fp, status = {}, Counter(), Counter(), Counter(), Counter(), Counter()
    fn_list, fp_list = [], []
    for m in mods:
        pm = s["per_module"].get(m)
        if not pm:
            continue
        o = TD._nested(v, k, m, st)
        lines = TC.numbered_lines((ROOT / "assetgen_meta/traced_inputs_v2" / split / f"{m}.txt").read_text(encoding="utf-8"))
        chk = TC.check_output(o or {}, TI.load_map(split, m) or {"ports": [], "signals": []}, lines, m)
        role = {r["element"]: r["role"] for r in chk["refs"]}
        status.update(r["status"] for r in chk["refs"])
        nref = len(gt[m])
        tp = nref - len(pm["fn"])
        per_mod[m] = {"ref": nref, "tp": tp, "fp": len(pm["fp"]), "fn": len(pm["fn"]),
                      "concepts": len((o or {}).get("conceptual assets", []) or [])}
        for n in pm["fp"]:
            kd = kind(m, n); fpk[kd] += 1; roles_fp[role.get(n, "?")] += 1
            fp_list.append({"module": m, "element": n, "kind": kd, "role": role.get(n, "?")})
        for n in pm["fn"]:
            kd = kind(m, n); fnk[kd] += 1
            w = TD._where(n, o or {}, chk) if o else "no output"
            where[w.split(" (")[0]] += 1
            fn_list.append({"module": m, "element": n, "kind": kd, "where": w})
    res = {"version": v, "run": k, "split": split, "reference_entries": sum(len(gt[m]) for m in mods), "modules_scored": len(per_mod), "missing_outputs": missing, "flattened": n_flat,
           "P": P, "R": R, "F1": F1, "emitted": s["emit"], "per_module": per_mod, "fp_by_kind": dict(fpk),
           "fn_by_kind": dict(fnk), "fn_where": dict(where), "fp_by_role": dict(roles_fp), "citation_status": dict(status),
           "false_positives": fp_list, "false_negatives": fn_list}
    if prev:
        ps = ea.score(ROOT / f"{st}_{prev}_r0", gt, strict=True, only=set(mods))
        hit = lambda sc: {(m, n) for m in mods for n, _o in gt[m]} - {(m, n) for m in mods for n in sc["per_module"].get(m, {}).get("fn", [])}
        fps = lambda sc: {(m, n) for m in mods for n in sc["per_module"].get(m, {}).get("fp", [])}
        res["vs_prev"] = {"prev": prev, "gained_hits": sorted(hit(s) - hit(ps)), "lost_hits": sorted(hit(ps) - hit(s)),
                          "new_fp": len(fps(s) - fps(ps)), "removed_fp": len(fps(ps) - fps(s))}
    (HERE / v).mkdir(exist_ok=True)
    tag = "" if split == "tuning" else f"{split}_"
    (HERE / v / f"{tag}eval_r{k}.json").write_text(json.dumps(res, indent=1, default=list), encoding="utf-8")
    L = [f"# {v} {split} run {k}: P {P:.3f} R {R:.3f} F1 {F1:.3f} emitted {s['emit']} ({len(per_mod)} modules, {res['reference_entries']} reference entries)", "",
         f"missing outputs: {missing}", f"citation statuses: {dict(status)}", f"FP by kind: {dict(fpk)}", f"FP by role: {dict(roles_fp)}",
         f"FN by kind: {dict(fnk)}", f"FN placement: {dict(where)}", "", "| module | ref | TP | FP | FN | concepts |", "|---|---|---|---|---|---|"]
    L += [f"| {m} | {x['ref']} | {x['tp']} | {x['fp']} | {x['fn']} | {x['concepts']} |" for m, x in per_mod.items()]
    (HERE / v / f"{tag}eval_r{k}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    log(f"{v} {split} r{k}: P {P:.3f} R {R:.3f} F1 {F1:.3f} emitted {s['emit']}; FN where {dict(where)}; citations {dict(status)}"
        + (f"; vs {prev}: +{len(res['vs_prev']['gained_hits'])} / -{len(res['vs_prev']['lost_hits'])} hits, "
           f"FP +{res['vs_prev']['new_fp']} / -{res['vs_prev']['removed_fp']}" if prev else "") + (f"; MISSING {missing}" if missing else ""))
    return res


if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    sys.stdout.reconfigure(encoding="utf-8")
    cmd, v = sys.argv[1], sys.argv[2]
    if cmd == "build":
        build(v)
    else:
        args = [a for a in sys.argv[3:] if a != "--heldout"]
        k = int(args[0]) if args else 0
        prev = args[1] if len(args) > 1 else None
        evaluate(v, k, prev, split="heldout" if "--heldout" in sys.argv else "tuning")
