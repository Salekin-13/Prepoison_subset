"""Helpers for assetgen_meta.ipynb: prompt checks, the meta call, splitting its reply,
and the adapter that lets eval_assets score the new executor schema unchanged.

Import from the repo root (the notebook sits there), so eval_assets and prompts_v2 resolve.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

HERE = Path(__file__).parent
M_METH, M_EXEC = "=== METHODOLOGY ===", "=== EXECUTION PROMPT ==="
SCHEMA_KEYS = ('"module name"', '"conceptual assets"', '"concept"', '"security objective"',
               '"reasoning"', '"related structural assets"', '"asset rtl"', '"entity"', '"realization"')


def sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


# ------------------------------------------------------------------ checks ---

_NUMERIC = [
    r"\b(at (most|least)|no more than|no fewer than|up to|maximum of|minimum of)\s+(\d+|half|a (third|quarter))\b",
    r"\d+\s*%|\bper ?cent\b",
    r"\b\d+\s+(assets?|elements?|signals?|ports?|concepts?|entries)\b",
]
_COMMENT_USE = r"\b(read|use|rely on|consult|check|inspect|from)\s+(the\s+)?comments?\b"


def corpus_names(root=".") -> set[str]:
    """Identifier-like names from the ground truth (41 modules) and the parsed closed sets.
    Only names with '_' or '.' are kept, so plain English words ('state', 'enable') are not flagged."""
    names = set()
    gt = json.loads((Path(root) / "data/ground_truth/manual_gt_neorv32.json").read_text(encoding="utf-8"))["modules"]
    for mod, v in gt.items():
        names.add(mod)
        names.update(a.get("element", "") for a in v["assets"])
    for f in (Path(root) / "data/parsed_tuning18").glob("*.json"):
        names.add(f.stem)
        d = json.loads(f.read_text(encoding="utf-8"))
        for key in ("ports", "signals"):
            for e in d.get(key, []) if isinstance(d, dict) else []:
                n = e.get("name") if isinstance(e, dict) else e
                if isinstance(n, str):
                    names.add(n)
    names.add("neorv32")
    return {n for n in names if n and len(n) >= 4 and ("_" in n or "." in n or n == "neorv32")}


def check_prompt(text: str, names: set[str], label: str) -> dict:
    """-> {"label", "ok", "problems": [...]}. Never raises; the notebook prints the result."""
    probs = []
    try:
        import prompts_v2
        prompts_v2.audit(text, label)
    except AssertionError as e:
        probs.append(f"prompts_v2.audit: {e}")
    low = text.lower()
    for pat in _NUMERIC:
        for m in re.finditer(pat, low):
            probs.append(f"numeric hint: '{m.group(0)}'")
    for n in sorted(names):
        if re.search(rf"(?<![\w.]){re.escape(n.lower())}(?![\w])", low):
            probs.append(f"corpus identifier: '{n}'")
    for m in re.finditer(_COMMENT_USE, low):
        # A prohibition ("do not use comments", "never rely on comments") is what the prompt
        # SHOULD say; only an unnegated instruction to use comments is a problem.
        if re.search(r"\b(not|never|no|don't|cannot|without)\b[\w\s,]{0,20}$", low[max(0, m.start() - 30):m.start()]):
            continue
        probs.append(f"comment used as evidence: '{m.group(0)}'")
    return {"label": label, "ok": not probs, "problems": probs}


def check_exec_prompt(text: str, names: set[str], label: str) -> dict:
    r = check_prompt(text, names, label)
    missing = [k for k in SCHEMA_KEYS if k not in text]
    if missing:
        r["problems"].append(f"schema keys missing: {missing}")
    for v in ('"stores"', '"sets"', '"computes"', '"exit port"'):
        if v not in text:
            r["problems"].append(f"realization value missing: {v}")
    if not re.search(r"only the final|nothing else", text, re.I):
        r["problems"].append("no instruction to return only the final JSON object")
    r["ok"] = not r["problems"]
    return r


def recheck(out_dir, names: set[str]) -> None:
    """Re-run check_exec_prompt on every finished sample and rewrite its checks.json."""
    for d in sorted(Path(out_dir).glob("sample_*")):
        exe = d / "exec_prompt.txt"
        if not exe.exists():
            print(f"{d.name}: no exec_prompt.txt, skipped")
            continue
        chk = check_exec_prompt(exe.read_text(encoding="utf-8"), names, d.name)
        (d / "checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
        print(f"{d.name}: {'PASS' if chk['ok'] else chk['problems']}")


# ------------------------------------------------------------------- reply ---

def split_reply(text: str) -> tuple[str, str]:
    """-> (methodology, execution_prompt). Raises ValueError if a marker is missing or out of order."""
    i, j = text.find(M_METH), text.find(M_EXEC)
    if i < 0 or j < 0 or j < i:
        raise ValueError(f"markers missing or out of order (methodology at {i}, execution prompt at {j})")
    return text[i + len(M_METH):j].strip(), text[j + len(M_EXEC):].strip()


# -------------------------------------------------------------------- call ---

def call_text(client, model, system, user, effort="high", max_tokens=65536, retries=5, json_mode=False):
    """One Responses API call. -> (text, usage dict, status). json_mode matches the baseline's
    asset calls (text.format json_object); the meta call is plain text."""
    wait = 2.0
    kw = {"text": {"format": {"type": "json_object"}}} if json_mode else {}
    for a in range(retries):
        try:
            r = client.responses.create(model=model, instructions=system, input=user,
                                        reasoning={"effort": effort}, max_output_tokens=max_tokens, **kw)
            u = r.usage
            usage = {"in": u.input_tokens, "out": u.output_tokens,
                     "reasoning": u.output_tokens_details.reasoning_tokens}
            return r.output_text, usage, getattr(r, "status", "?")
        except Exception:
            if a == retries - 1:
                raise
            time.sleep(wait)
            wait *= 2


# ----------------------------------------------------------------- scoring ---

def flatten(result: dict) -> dict:
    """New executor schema -> the per-module format eval_assets.load_run reads.
    An element listed under several concepts is kept once (first concept's objective):
    the schema allows one element to realize several concepts, so repeats are not new emissions."""
    seen, assets = set(), []
    for c in result.get("conceptual assets", []) or []:
        if not isinstance(c, dict):
            continue                                   # a malformed entry (e.g. a stray string) is skipped
        for s in c.get("related structural assets", []) or []:
            if not isinstance(s, dict):
                continue
            key = (s.get("entity", ""), s.get("asset rtl", ""))
            if not key[1] or key in seen:
                continue
            seen.add(key)
            assets.append({"Asset RTL": key[1], "Entity": key[0],
                           "Security Objective": c.get("security objective", ""),
                           "Realization": s.get("realization", "")})
    return {"IP": result.get("module name", ""), "Assets": assets}


# ---------------------------------------------------------------- executor ---
# Mirrors v2x3r8's Stage B exactly where it matters for comparability: gpt-5-mini, effort
# high, 65536-token ceiling, JSON mode, comment-stripped RTL only, the same user-message
# wrapper, parse-valid results cached only, and NO validation retry (the baseline's
# RETRY_ON_VALIDATION is off for arms without the parsed block). Validation is recorded.

OBJ = {"Confidentiality", "Integrity", "Availability"}
REAL = {"stores", "sets", "computes", "exit port"}


def rtl_modules(rtl_dir="data/RTL_data"):
    """The 18-module tuning set, as finetuning_assetgen_v2.discover_modules()."""
    return [(p.stem, p) for p in sorted(Path(rtl_dir).glob("*.vhd"))]


def build_user(stem, rtl):
    """Byte-identical to finetuning_assetgen_v2.build_asset_user with summary/parsed off."""
    return (f"TARGET IP MODULE: {stem}\n\n=== RTL ===\n{rtl}\n\n"
            f"Identify the primary security assets for '{stem}' and return the JSON object per the contract.")


def loads(txt):
    """Same salvage rule as the baseline's _loads."""
    try:
        return json.loads(txt)
    except Exception:
        pass
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def closed_set(stem, parsed_dir="data/parsed_tuning18"):
    d = json.loads((Path(parsed_dir) / f"{stem}.json").read_text(encoding="utf-8"))
    return [(e["entity"], e["name"]) for e in d["ports"] + d["signals"]]


def validate_nested(res, closed):
    """-> [issue]. Names checked against the parsed closed set, as validate_primary does."""
    keys, ents, out = set(closed), {}, []
    for en, n in closed:
        ents.setdefault(n, set()).add(en)
    for c in res.get("conceptual assets", []) or []:
        if not isinstance(c, dict):
            out.append({"kind": "malformed_entry", "detail": f"concept entry is not an object: {str(c)[:60]!r}"})
            continue
        if c.get("security objective") not in OBJ:
            out.append({"kind": "bad_objective", "detail": f"concept '{c.get('concept')}': '{c.get('security objective')}'"})
        for s in c.get("related structural assets", []) or []:
            if not isinstance(s, dict):
                out.append({"kind": "malformed_entry", "detail": f"structural entry is not an object: {str(s)[:60]!r}"})
                continue
            n, en = s.get("asset rtl"), s.get("entity")
            if n not in ents:
                out.append({"kind": "ungrounded", "name": n, "detail": f"ungrounded '{n}'"})
            elif (en, n) not in keys:
                out.append({"kind": "entity_mismatch", "name": n, "detail": f"'{n}': entity '{en}' not in {sorted(ents[n])}"})
            if s.get("realization") not in REAL:
                out.append({"kind": "bad_realization", "name": n, "detail": f"'{n}': realization '{s.get('realization')}'"})
    return out


def run_dir(version, rep, stem="assets_tuning18"):
    return Path(f"runs/{stem}_{version}_r{rep}")


def run_version(client, version, rep, system, modules, extra_meta=None, model="gpt-5-mini", workers=6,
                build=None, input_note="comment-stripped RTL only", stem="assets_tuning18", parsed_dir="data/parsed_tuning18"):
    """Generate one repeat into <stem>_<version>_r<rep>/ (default assets_tuning18_<version>_r<rep>/). Cached modules
    are skipped, so an interrupted run resumes. Refuses to mix two prompts in one directory.
    build(stem, rtl) -> user message; None = build_user (RTL only, byte-identical to earlier arms).
    Arm m7e194es0ismr passes rel_view.build_user (RTL + relationship map).
    stem / parsed_dir: the run-folder prefix and the closed-set folder validate_nested checks names against; the
    held-out run uses stem="assets_heldout26", parsed_dir="parsed_heldout26". A non-default value is recorded in
    _run_meta.json; with the defaults the file is written exactly as before."""
    import rtl_parse
    from concurrent.futures import ThreadPoolExecutor, as_completed
    out = run_dir(version, rep, stem)
    where = {} if (stem, str(parsed_dir)) == ("assets_tuning18", "data/parsed_tuning18") else {"stem": stem, "parsed_dir": str(parsed_dir)}
    (out / "_raw").mkdir(parents=True, exist_ok=True)
    (out / "_nested").mkdir(exist_ok=True)
    sha = hashlib.sha256(system.encode("utf-8")).hexdigest()
    mp = out / "_run_meta.json"
    if mp.exists():
        old = json.loads(mp.read_text(encoding="utf-8"))
        if old.get("system_prompt_sha256") != sha:
            raise RuntimeError(f"{out} holds prompt {old.get('system_prompt_sha256', '?')[:12]}, current is {sha[:12]}")
    else:
        mp.write_text(json.dumps({"version": version, "repeat": rep, "model": model, "effort": "high",
                                  "system_prompt_sha256": sha, "system_prompt_chars": len(system),
                                  "input": input_note, "retry_on_validation": False,
                                  "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), **where, **(extra_meta or {})}, indent=2),
                      encoding="utf-8")

    def one(stem, path):
        if (out / f"{stem}.json").exists():
            return stem, "cached", None
        rtl = rtl_parse.strip_comments(Path(path).read_text(encoding="utf-8", errors="ignore"), vhdl=True)
        txt, usage, status = call_text(client, model, system, (build or build_user)(stem, rtl), "high", 65536, json_mode=True)
        (out / "_raw" / f"{stem}.json").write_text(txt, encoding="utf-8")
        obj = loads(txt)
        if not (isinstance(obj, dict) and isinstance(obj.get("conceptual assets"), list)
                and all(isinstance(c, dict) for c in obj["conceptual assets"])):
            return stem, f"UNPARSEABLE (status {status}); nothing cached, re-run the cell to retry", usage
        obj["module name"] = stem
        (out / "_nested" / f"{stem}.json").write_text(json.dumps(obj, indent=2), encoding="utf-8")
        (out / f"{stem}.json").write_text(json.dumps(flatten(obj), indent=2), encoding="utf-8")
        return stem, "ok", usage

    notes, tokens = {}, {"in": 0, "out": 0}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(one, s, p): s for s, p in modules}
        for fut in as_completed(futs):
            try:
                stem, note, usage = fut.result()
            except Exception as e:
                stem, note, usage = futs[fut], f"ERROR {type(e).__name__}: {e}", None
            notes[stem] = note
            if usage:
                tokens["in"] += usage["in"]; tokens["out"] += usage["out"]
    val = {}
    for stem, _p in modules:
        f = out / "_nested" / f"{stem}.json"
        if f.exists():
            val[stem] = validate_nested(json.loads(f.read_text(encoding="utf-8")), closed_set(stem, parsed_dir))
    (out / "_validation.json").write_text(json.dumps(val, indent=1), encoding="utf-8")
    done = sum((out / f"{s}.json").exists() for s, _ in modules)
    return {"dir": str(out), "complete": done == len(modules), "modules_done": done, "notes": notes,
            "tokens": tokens, "issues": sum(len(v) for v in val.values()),
            "issue_kinds": dict(__import__("collections").Counter(i["kind"] for v in val.values() for i in v))}


def realization_counts(version, rep):
    from collections import Counter
    c = Counter()
    for f in (run_dir(version, rep) / "_nested").glob("*.json"):
        for a in flatten(json.loads(f.read_text(encoding="utf-8")))["Assets"]:
            c[a["Realization"]] += 1
    return dict(c)


# ----------------------------------------------------------------- scoring ---

def f13_filter(run: dict) -> dict:
    """F13, a CODE post-filter (not prompt text): keep only names in the parsed closed set
    (parsed_tuning18, the regex-fixed closed set) and one row per (entity, element).
    Applied identically to every version so the comparison stays fair; always reported
    as a separately labelled number, never as the primary result."""
    out = {}
    for m, lst in run.items():
        p = Path("data/parsed_tuning18") / f"{m}.json"
        names = {n for _e, n in closed_set(m)} if p.exists() else None
        seen, keep = set(), []
        for ent, name, obj in lst:
            if names is not None and name not in names:
                continue
            if (ent, name) in seen:
                continue
            seen.add((ent, name)); keep.append((ent, name, obj))
        out[m] = keep
    return out


def convention_filter(run: dict) -> dict:
    """EVALUATION-PROTOCOL filter for the annotator's conventions (not theory, so never in a prompt):
    drops elements whose type is a bus transaction record and input ports named clk*/rst*/rstn*.
    Reported as a separately labelled number, like f13_filter."""
    out = {}
    for m, lst in run.items():
        p = Path("data/parsed_tuning18") / f"{m}.json"
        if not p.exists():
            out[m] = list(lst); continue
        d = json.loads(p.read_text(encoding="utf-8"))
        typ = {e["name"]: e.get("type", "") for e in d["ports"] + d["signals"]}
        din = {e["name"]: e.get("dir", "") for e in d["ports"]}
        keep = []
        for ent, name, obj in lst:
            base = name.split(".")[0]
            if re.search(r"\bbus_(req|rsp)_t\b", typ.get(name, typ.get(base, "")) or ""):
                continue
            if din.get(base) == "in" and re.match(r"(clk|rst|rstn)(_|$)", base):
                continue
            keep.append((ent, name, obj))
        out[m] = keep
    return out


def seed_diff(seed: str, revised: str) -> dict:
    """How much of a seeded execution prompt survived verbatim (sentence level, whitespace-normalised)."""
    def sents(t):
        return [" ".join(s.split()) for s in re.split(r"(?<=[.;:])\s+|\n+", t) if len(" ".join(s.split())) > 25]
    a, b = sents(seed), sents(revised)
    sb, sa = set(b), set(a)
    kept = [s for s in a if s in sb]
    return {"seed_sentences": len(a), "kept": len(kept), "kept_share": len(kept) / len(a) if a else 0.0,
            "removed": [s for s in a if s not in sb], "removed_n": len([s for s in a if s not in sb]),
            "added": [s for s in b if s not in sa], "added_n": len([s for s in b if s not in sa])}


def recovered_from(version, reference="m7e194es0c"):
    """GT elements the reference missed in most of its runs: which does `version` find in most of its runs?
    -> (recovered set, still-missed set) of (module, element)."""
    from collections import Counter
    import eval_assets as ea
    gt = ea.load_refs()["gt"]
    runs = ea.collect([version, reference])
    common = ea.common_modules(runs, gt)
    def missed(v):
        c = Counter()
        for r in runs[v]:
            s = ea.score(r, gt, strict=True, only=common)
            c.update((m, e) for m in common for e in s["per_module"][m]["fn"])
        return {k for k, x in c.items() if x > len(runs[v]) / 2}
    ref, mine = missed(reference), missed(version)
    return ref - mine, ref & mine


def score_versions(versions, baseline="v2x3r8", post=None):
    """Mean P/R/F1 over repeats, strict, on the modules common to every run of every version
    listed (plus the baseline) and the ground truth. `post` (e.g. f13_filter) is applied to
    every run of every version before scoring. -> (common modules, {version: row}, GT entries)."""
    import statistics as st
    import eval_assets as ea
    gt = ea.load_refs()["gt"]
    runs = ea.collect(list(versions) + [baseline])
    common = ea.common_modules(runs, gt)
    rows = {}
    for v, rr in runs.items():
        sc = [ea.score(post(r) if post else r, gt, strict=True, only=common) for r in rr]
        rows[v] = {"runs": len(sc), "P": st.mean(s["precision"] for s in sc), "R": st.mean(s["recall"] for s in sc),
                   "F1": st.mean(s["f1"] for s in sc), "emit": st.mean(s["emit"] for s in sc),
                   "per_run": [(round(s["precision"], 3), round(s["recall"], 3)) for s in sc]}
    return common, rows, sum(len(gt[m]) for m in common)


def majority(runs):
    """Self-consistency at the answer level: keep (entity, name) found in more than half the runs.
    -> (voted run dict, {(module, entity, name): runs it appeared in})."""
    from collections import Counter
    need, voted, counts = len(runs) // 2 + 1, {}, {}
    for m in set().union(*runs):
        cnt, objs = Counter(), {}
        for r in runs:
            seen = set()
            for ent, name, obj in r.get(m, []):
                if (ent, name) in seen:
                    continue
                seen.add((ent, name)); cnt[(ent, name)] += 1
                objs.setdefault((ent, name), Counter())[obj] += 1
        voted[m] = [(k[0], k[1], objs[k].most_common(1)[0][0]) for k, c in cnt.items() if c >= need]
        counts.update({(m, k[0], k[1]): c for k, c in cnt.items()})
    return voted, counts


def rtl_lines(path, name, cap=6):
    """-> (declaration, writes/connections, reads) as 'line: text' strings from the ORIGINAL file,
    so line numbers match what you open. Comment tails are ignored when matching."""
    pat = re.escape(name)
    decl, w, r = [], [], []
    for i, l in enumerate(Path(path).read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        code = l.split("--")[0]
        if not re.search(rf"(?<![\w.]){pat}(?![\w])", code):
            continue
        s = f"{i}: {l.strip()}"
        if re.search(rf"(?<![\w.]){pat}\s*:(?!=)", code):
            decl.append(s)
        # A write is `name <=` at the START of a statement (optionally labelled). Anywhere else,
        # `<=` is VHDL's less-or-equal (if/elsif/when conditions) and the element is being read.
        elif (re.match(rf"\s*(\w+\s*:\s*)?{pat}(\s*\([^)]*\))?\s*<=", code)
              or re.search(rf"=>\s*{pat}(?![\w])", code)):
            w.append(s)
        else:
            r.append(s)
    return " | ".join(decl[:2]), " | ".join(w[:cap]), " | ".join(r[:cap])


def fp_sample(version, csv_path, n=40, seed=0, baseline="v2x3r8", rtl_dir="data/RTL_data"):
    """Random sample of the majority-vote false positives of `version`, pre-filled for grouping
    by hand; the 'family' and 'note' columns are left empty. -> (rows written, voted FP total)."""
    import csv
    import random
    import eval_assets as ea
    gt = ea.load_refs()["gt"]
    runs = ea.collect([version, baseline])
    common = ea.common_modules(runs, gt)
    voted, counts = majority(runs[version])
    s = ea.score(voted, gt, strict=True, only=common)
    ent_of = {(m, name): ent for m, lst in voted.items() for ent, name, _o in lst}
    obj_of = {(m, name): o for m, lst in voted.items() for _e, name, o in lst}
    fps = sorted((m, name) for m, rec in s["per_module"].items() for name in rec["fp"])
    pick = random.Random(seed).sample(fps, min(n, len(fps)))
    reps = sorted(Path(".").glob(f"runs/assets_tuning18_{version}_r*"))
    rows = []
    for m, name in sorted(pick):
        concept, reasoning, reals = "", "", []
        for d in reps:
            f = d / "_nested" / f"{m}.json"
            if not f.exists():
                continue
            for c in json.loads(f.read_text(encoding="utf-8")).get("conceptual assets", []):
                for a in c.get("related structural assets", []) or []:
                    if a.get("asset rtl") == name:
                        reals.append(a.get("realization", ""))
                        if not concept:
                            concept, reasoning = c.get("concept", ""), c.get("reasoning", "")
        decl, w, r = rtl_lines(Path(rtl_dir) / f"{m}.vhd", name)
        rows.append({"module": m, "element": name, "entity": ent_of.get((m, name), ""),
                     "runs_in": counts.get((m, ent_of.get((m, name), ""), name), ""),
                     "objective": obj_of.get((m, name), ""),
                     "realization": __import__("collections").Counter(reals).most_common(1)[0][0] if reals else "",
                     "concept": concept, "reasoning": reasoning,
                     "declared": decl, "written_or_connected": w, "read": r, "family": "", "note": ""})
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["module"])
        wr.writeheader(); wr.writerows(rows)
    return len(rows), len(fps)


def diagnostics(version, common, n_modules=18) -> dict:
    """Refinement metrics D1-D7 for one version, over the given scoring modules. Prints a
    compact report and returns it. Realization and concept metrics need the new schema's
    files, so they read N/A for the baseline."""
    import statistics as st
    from collections import Counter, defaultdict
    from itertools import combinations
    import eval_assets as ea
    gt, closed = ea.load_refs()["gt"], ea.load_closed()
    n_ref = sum(len(gt[m]) for m in common)
    dirs = [d for d in sorted(Path(".").glob(f"runs/assets_tuning18_{version}_r*")) if d.is_dir()]
    runs = [(d, ea.load_run(d)) for d in dirs]
    runs = [(d, r) for d, r in runs if common <= set(r)]          # complete on the scoring modules
    if not runs:
        print(f"{version}: no complete run"); return {}
    sc = [ea.score(r, gt, strict=True, only=common) for _d, r in runs]
    rep = {"version": version, "runs": len(sc), "P": st.mean(s["precision"] for s in sc),
           "R": st.mean(s["recall"] for s in sc)}
    rep["D1_emit_ratio"] = st.mean(s["emit"] for s in sc) / n_ref
    real, cls = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0, 0])   # [emitted, fp]; [tp, fp, fn]
    fan_c, fan_s, kinds, missing = [], [], Counter(), 0
    fp_mod, fn_seen = Counter(), Counter()
    for (d, _r), s in zip(runs, sc):
        for m in common:
            fp_left = Counter(s["per_module"][m]["fp"])
            f = d / f"{m}.json"
            for a in json.loads(f.read_text(encoding="utf-8")).get("Assets", []):
                k = a.get("Realization")
                if not k:
                    continue
                real[k][0] += 1
                if fp_left[a["Asset RTL"]] > 0:
                    fp_left[a["Asset RTL"]] -= 1; real[k][1] += 1
            fp_mod[m] += len(s["per_module"][m]["fp"])
            fn_seen.update((m, n) for n in s["per_module"][m]["fn"])
        for k, v in ea.by_class(s, gt, closed).items():
            cls[k][0] += v["tp"]; cls[k][1] += v["fp"]; cls[k][2] += v["fn"]
        for f in (d / "_nested").glob("*.json") if (d / "_nested").exists() else []:
            cs = json.loads(f.read_text(encoding="utf-8")).get("conceptual assets", [])
            fan_c.append(len(cs)); fan_s += [len(c.get("related structural assets", []) or []) for c in cs]
        vf = d / "_validation.json"
        if vf.exists():   # the baseline pipeline wrote a different format; count only records with a "kind"
            vd = json.loads(vf.read_text(encoding="utf-8"))
            for v in (vd.values() if isinstance(vd, dict) else []):
                kinds.update(i["kind"] for i in (v if isinstance(v, list) else []) if isinstance(i, dict) and "kind" in i)
        missing += n_modules - sum(1 for x in d.glob("*.json") if not x.name.startswith("_"))
    rep["D2_precision_by_realization"] = {k: (v[0], round(1 - v[1] / v[0], 3)) for k, v in real.items() if v[0]} or "N/A"
    rep["D3_by_class"] = {k: {"P": round(v[0] / (v[0] + v[1]), 3) if v[0] + v[1] else None,
                              "R": round(v[0] / (v[0] + v[2]), 3) if v[0] + v[2] else None,
                              "FP_per_run": round(v[1] / len(sc), 1)}
                          for k, v in cls.items() if sum(v)}
    rep["D4_concepts_per_module"] = round(st.mean(fan_c), 2) if fan_c else "N/A"
    rep["D4_elements_per_concept"] = round(st.mean(fan_s), 2) if fan_s else "N/A"
    rep["D5_validity"] = {"modules_missing": missing, **dict(kinds)}
    sets = [{(m, a[1]) for m in common for a in r.get(m, [])} for _d, r in runs]
    rep["D6_stability"] = ({"P_sd": round(st.pstdev(s["precision"] for s in sc), 3),
                            "R_sd": round(st.pstdev(s["recall"] for s in sc), 3),
                            "jaccard": round(st.mean(len(a & b) / len(a | b) for a, b in combinations(sets, 2)), 3)}
                           if len(sc) > 1 else "N/A (one run)")
    rep["D7_worst_modules_by_FP"] = [(m, round(n / len(sc), 1)) for m, n in fp_mod.most_common(5)]
    rep["D7_missed_in_most_runs"] = sorted(f"{m}:{n} ({elem_class_safe(m, n, closed)})"
                                           for (m, n), c in fn_seen.items() if c > len(sc) / 2)
    print(f"\n== {version}: {len(sc)} run(s), {len(common)} modules, {n_ref} ground-truth entries (exact)")
    print(f"   precision {rep['P']:.3f}  recall {rep['R']:.3f}")
    for k, v in rep.items():
        if k.startswith("D"):
            print(f"   {k}: {v}")
    return rep


def elem_class_safe(m, n, closed):
    import eval_assets as ea
    return ea.elem_class(m, n, closed)


def selftest(root=".") -> None:
    """Adapter + scorer on a hand-built result for one real module (neorv32_wdt).
    Expected, from the ground truth and wdt lines 151/177: ctrl.enable and clkgen_en_o are
    true positives, rstn_o a false positive, and the repeated ctrl.enable is dropped."""
    import eval_assets as ea
    fake = {"module name": "neorv32_wdt", "conceptual assets": [
        {"concept": "enable", "security objective": "Integrity", "reasoning": "-",
         "related structural assets": [
             {"asset rtl": "ctrl.enable", "entity": "neorv32_wdt", "realization": "stores"},
             {"asset rtl": "clkgen_en_o", "entity": "neorv32_wdt", "realization": "exit port"}]},
        {"concept": "reset request", "security objective": "Availability", "reasoning": "-",
         "related structural assets": [
             {"asset rtl": "rstn_o", "entity": "neorv32_wdt", "realization": "exit port"},
             {"asset rtl": "ctrl.enable", "entity": "neorv32_wdt", "realization": "stores"}]}]}
    flat = flatten(fake)
    assert [a["Asset RTL"] for a in flat["Assets"]] == ["ctrl.enable", "clkgen_en_o", "rstn_o"], flat
    run = {"neorv32_wdt": [(a["Entity"], a["Asset RTL"], a["Security Objective"]) for a in flat["Assets"]]}
    gt = ea.load_refs()["gt"]
    s = ea.score(run, gt, strict=True, only={"neorv32_wdt"})
    assert (s["tp"], s["fp"]) == (2, 1), (s["tp"], s["fp"], s["per_module"]["neorv32_wdt"]["fp"])
    assert s["per_module"]["neorv32_wdt"]["fp"] == ["rstn_o"]
    assert split_reply(f"{M_METH}\nA\n{M_EXEC}\nB") == ("A", "B")
    try:
        split_reply(f"{M_EXEC}\nB\n{M_METH}\nA")
        raise AssertionError("out-of-order markers accepted")
    except ValueError:
        pass
    names = corpus_names(root)
    assert "ctrl.enable" in names and "clkgen_en_o" in names, "corpus name list is missing known names"
    bad = check_prompt("Report at most 5 assets; check ctrl.enable; read the comments.", names, "neg")
    assert len(bad["problems"]) >= 3, bad
    good = check_prompt("Do not use comments as evidence. Never rely on comments.", names, "pos")
    assert good["ok"], good
    # executor side: validation, RTL line lookup, majority vote
    iss = validate_nested({"conceptual assets": [{"concept": "x", "security objective": "Secrecy",
                           "related structural assets": [{"asset rtl": "no_such_sig", "entity": "neorv32_wdt", "realization": "holds"}]}]},
                          closed_set("neorv32_wdt"))
    assert {i["kind"] for i in iss} == {"bad_objective", "ungrounded", "bad_realization"}, iss
    assert validate_nested(fake, closed_set("neorv32_wdt")) == [], validate_nested(fake, closed_set("neorv32_wdt"))
    _d, w, _r = rtl_lines(Path(root) / "data/RTL_data/neorv32_wdt.vhd", "rstn_o")
    assert "rstn_o <= not (hw_rst_timeout or hw_rst_access)" in w, w
    _d, w2, r2 = rtl_lines(Path(root) / "data/RTL_data/neorv32_wdt.vhd", "cnt")
    assert not any(re.search(r"^\d+:\s*(if|elsif)\b", x.strip()) for x in w2.split(" | ") if x), w2
    v, c = majority([{"m": [("e", "a", "I"), ("e", "b", "I")]}, {"m": [("e", "a", "A")]}, {"m": [("e", "a", "I")]}])
    assert v == {"m": [("e", "a", "I")]} and c[("m", "e", "b")] == 1, (v, c)
    assert build_user("x", "R").startswith("TARGET IP MODULE: x\n\n=== RTL ===\nR\n\n")
    f = f13_filter({"neorv32_wdt": [("neorv32_wdt", "ctrl.enable", "I"), ("neorv32_wdt", "ctrl.enable", "I"),
                                    ("neorv32_wdt", "no_such_sig", "I")]})
    assert f == {"neorv32_wdt": [("neorv32_wdt", "ctrl.enable", "I")]}, f
    cf = convention_filter({"neorv32_wdt": [("neorv32_wdt", "bus_req_i", "I"), ("neorv32_wdt", "clk_i", "A"),
                                            ("neorv32_wdt", "ctrl.enable", "I")]})
    assert cf == {"neorv32_wdt": [("neorv32_wdt", "ctrl.enable", "I")]}, cf
    sd = seed_diff("Keep this sentence exactly as it is. Change this sentence in the revision please.",
                   "Keep this sentence exactly as it is. A different sentence was written here instead.")
    assert (sd["kept"], sd["removed_n"], sd["added_n"]) == (1, 1, 1), sd
    print(f"selftest PASS: adapter, scorer (TP 2 / FP 1 on wdt), reply split, "
          f"{len(names)} corpus names, negative prompt caught {len(bad['problems'])} problems")
