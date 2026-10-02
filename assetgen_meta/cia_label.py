"""The CIA labelling call of arm m7e194es0ist2: after the generation call has fixed the asset list, a second call answers
the four security questions (confidentiality, integrity, availability, undermined behavior) for each conceptual
asset, the way an SoC security engineer answers them for an IP of unknown use (IEEE P3164 3.1.1 and its worked
examples; prompt hand_arms/m7e194es0ist2/cia_instructions.md). It never adds or removes an element, so it cannot move
precision or recall; its answers feed the trace reports, the objective, and one evaluation-layer row.

  user message  = the module's traced input (numbered RTL + relationship map + flow graph, the generation call's input)
                  + CONCEPTS TO REVIEW (each concept, its reasoning, its references with role and cited line)
  output        = {stem}_{version}_r<k>/_cia/<module>.json (parsed and validated), _cia/_raw/<module>.txt

merged(version, k, module) returns the generation object with "questions" and the final "security objective" from
the labelling call; trace_digest and trace_check read it, so the reports show the engineer's answers.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import meta_tools as mt          # noqa: E402

PROMPT = HERE / "hand_arms" / "m7e194es0ist2" / "cia_instructions.md"
QS = ("confidentiality", "integrity", "availability", "undermined behavior")
ANSWERS = {"confidentiality": {"yes-RTL", "yes-assumed", "no", "unknown"}, "integrity": {"yes-RTL", "yes-assumed", "no", "unknown"},
           "availability": {"yes-RTL", "no", "unknown"}, "undermined behavior": {"yes-RTL", "no", "unknown"}}
OBJ = {"Confidentiality", "Integrity", "Availability", "none"}


def _norm_name(s) -> str:
    """A concept name with case and every non-alphanumeric run ignored (for matching labels to concepts)."""
    return re.sub(r"[^0-9a-z]+", " ", str(s or "").lower()).strip()


def run_dir(version, k, stem="assets_tuning18"):
    return ROOT / f"{stem}_{version}_r{k}"


def concepts_block(obj: dict, lines: dict) -> list[dict]:
    out = []
    for c in obj.get("conceptual assets", []) or []:
        if not isinstance(c, dict):
            continue
        refs = []
        for s in c.get("related structural assets", []) or []:
            if isinstance(s, dict):
                refs.append({"element": s.get("asset rtl"), "entity": s.get("entity"), "role": s.get("realization"),
                             "occurrence": s.get("occurrence"), "edge": s.get("edge")})
        out.append({"concept": c.get("concept"), "reasoning": str(c.get("reasoning", ""))[:700], "structural references": refs})
    return out


def build_user(m: str, obj: dict, inputs: str = "traced_inputs_v2", split: str = "tuning") -> str:
    txt = (HERE / inputs / split / f"{m}.txt").read_text(encoding="utf-8")
    body = txt.rsplit("\n\nIdentify the primary security assets for", 1)[0]
    return (body + "\n\n=== CONCEPTS TO REVIEW (from the earlier analysis; judge these, do not change them) ===\n"
            + json.dumps(concepts_block(obj, {}), indent=1)
            + f"\n\nAnswer the four security questions for every concept of '{m}' and return the JSON object per the contract.")


def validate(res: dict, obj: dict, lines: dict) -> list[str]:
    """-> problems: a concept given but not answered (or answered twice), an unknown answer value or objective, a
    "yes" or "no" without an RTL line of this input."""
    probs = []
    given = [c.get("concept") for c in obj.get("conceptual assets", []) or [] if isinstance(c, dict)]
    got = [c.get("concept") for c in res.get("concepts", []) or [] if isinstance(c, dict)]
    for g in given:
        if got.count(g) != 1:
            probs.append(f"concept answered {got.count(g)} times: {str(g)[:60]}")
    for c in res.get("concepts", []) or []:
        if not isinstance(c, dict):
            probs.append("malformed concept entry"); continue
        if c.get("security objective") not in OBJ:
            probs.append(f"objective {c.get('security objective')!r}")
        for q in QS:
            a = (c.get("answers") or {}).get(q)
            if not isinstance(a, dict) or a.get("answer") not in ANSWERS[q]:
                probs.append(f"{q}: answer {a.get('answer') if isinstance(a, dict) else a!r}"); continue
            if a["answer"] != "unknown" and _int(a.get("line")) not in lines:
                probs.append(f"{q}: {a['answer']} without an RTL line of this input ({a.get('line')!r})")
    return probs


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def label(client, version: str, reps=(0, 1, 2), modules=None, model="gpt-5-mini", workers=6, stem="assets_tuning18",
          inputs="traced_inputs_v2", log=print) -> dict:
    """One labelling call per (run, module) that has a generation output and no saved labels yet (resumable)."""
    import trace_check as TC
    from concurrent.futures import ThreadPoolExecutor, as_completed
    system = PROMPT.read_text(encoding="utf-8")
    jobs = []
    for k in reps:
        d = run_dir(version, k, stem)
        for f in sorted((d / "_nested").glob("*.json")):
            if modules and f.stem not in modules:
                continue
            if not (d / "_cia" / f"{f.stem}.json").exists():
                jobs.append((k, f.stem))

    def one(k, m):
        d = run_dir(version, k, stem)
        obj = json.loads((d / "_nested" / f"{m}.json").read_text(encoding="utf-8"))
        if not obj.get("conceptual assets"):
            res = {"module name": m, "concepts": []}
            (d / "_cia").mkdir(exist_ok=True)
            (d / "_cia" / f"{m}.json").write_text(json.dumps({**res, "_problems": []}, indent=1), encoding="utf-8")
            return k, m, "no concepts", None
        user = build_user(m, obj, inputs)
        txt, usage, status = mt.call_text(client, model, system, user, "high", 65536, json_mode=True)
        (d / "_cia" / "_raw").mkdir(parents=True, exist_ok=True)
        (d / "_cia" / "_raw" / f"{m}.txt").write_text(txt, encoding="utf-8")
        res = mt.loads(txt)
        if not isinstance(res, dict) or not isinstance(res.get("concepts"), list):
            return k, m, f"UNPARSEABLE (status {status}); re-run to retry", usage
        lines = TC.numbered_lines((HERE / inputs / "tuning" / f"{m}.txt").read_text(encoding="utf-8"))
        res["_problems"] = validate(res, obj, lines)
        (d / "_cia" / f"{m}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        return k, m, f"ok ({len(res['_problems'])} problems)", usage

    tok = Counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(one, k, m) for k, m in jobs]):
            k, m, note, u = fut.result()
            if u:
                tok["in"] += u["in"]; tok["out"] += u["out"]
            if not note.startswith("ok (0"):
                log(f"   r{k} {m}: {note}")
    log(f"labelling {version}: {len(jobs)} calls, tokens {dict(tok)}")
    return {"calls": len(jobs), "tokens": dict(tok)}


def merged(version: str, k: int, m: str, stem="assets_tuning18") -> dict | None:
    """The generation object with each concept's "questions" (answer, line, via, reason, as labelled) and the labelled
    objective (when not "none"; the generation objective is kept as "generation objective")."""
    d = run_dir(version, k, stem)
    f = d / "_nested" / f"{m}.json"
    if not f.exists():
        return None
    obj = json.loads(f.read_text(encoding="utf-8"))
    cf = d / "_cia" / f"{m}.json"
    if not cf.exists():
        return obj
    labs = [c for c in json.loads(cf.read_text(encoding="utf-8")).get("concepts", []) if isinstance(c, dict)]
    lab = {c.get("concept"): c for c in labs}
    # The labelling model sometimes changes punctuation in a concept name it copies (an em dash or a multiplication sign
    # dropped). In the ist2 runs, 286 of 333 concepts matched exactly, 45 more with punctuation and case ignored, and 2
    # stayed unmatched. The fallback is used only when the normalized name is unique among the labels not already
    # matched exactly AND among the generation concepts, so a label is never attached to two concepts.
    concepts = [c for c in obj.get("conceptual assets", []) or [] if isinstance(c, dict)]
    exact = {c.get("concept") for c in concepts if c.get("concept") in lab}
    by_norm = defaultdict(list)
    for c in labs:
        if c.get("concept") not in exact:
            by_norm[_norm_name(c.get("concept"))].append(c)
    gen_norm = Counter(_norm_name(c.get("concept")) for c in concepts)
    ans = lambda L, q: (L.get("answers") or {}).get(q) if isinstance((L.get("answers") or {}).get(q), dict) else {}
    for c in concepts:
        L = lab.get(c.get("concept"))
        nn = _norm_name(c.get("concept"))
        if L is None and len(by_norm.get(nn, [])) == 1 and gen_norm[nn] == 1:
            L = by_norm[nn][0]
        if L is not None:
            # an answer that is not an object (e.g. "integrity": "no") is kept as its text, with no line
            c["questions"] = {q: ({"answer": ans(L, q).get("answer"), "line": ans(L, q).get("line"), "via": ans(L, q).get("via"),
                                   "reason": ans(L, q).get("reason")} if ans(L, q) else
                                  {"answer": (L.get("answers") or {}).get(q) if isinstance((L.get("answers") or {}).get(q), str) else None,
                                   "line": None, "via": None, "reason": None}) for q in QS}
            c["kind"] = L.get("kind")
            c["generation objective"] = c.get("security objective")
            c["labelled objective"] = L.get("security objective")
    return obj
