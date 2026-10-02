"""Fault reporter: what rules on relationship types can and cannot do against the generator's false positives, shown
from the relationship types of its hits and false positives and the occurrences it cited. Code computes every number; an LLM (OpenAI, default
gpt-5.4) explains each cluster's fault from the cited occurrences; code checks every claim the LLM makes.

Steps
  1. Evidence. For every element a complete run lists (fp_diagnosis.rows_for_run: labelled by the scorer's own
     matching; the cited occurrence -> line -> RTL text; the cited edge), its relationship profile from the map:
       class  data out / data in / control out / controlled / reset / sub-unit port / clocks or resets others, each
              with what is on the other end (an internal element, an input port, an output port), plus kind, storage,
              record field, constant driver, and self-updates (through data or through control) as one token each
       type   the exact record types with their ends (CLOCKED_BY and RESET_BY without an end)
  2. Overlap (code). Per token: share of hits and of FPs that have it. Clusters: average linkage on the Jaccard
     distance between profiles, at several cut heights (0 = identical profiles); per cut, the share of FPs in clusters
     that also hold hits (any hit, and hits at least a fifth of the cluster). Separability: area under the ROC curve
     (AUC; 0.5 = chance, 1 = perfect) of hit vs FP from the profile, in-sample and leave one module out (logistic
     regression; the share of hits among the nearest profiles of other modules, ties included), on all pooled rows and
     on one row per element. Rules: per cluster, the best rule of the searched form (the cluster's shared tokens, plus up
     to two tokens, minus at most one 'unless' token) that drops FPs and none of the cluster's hits; each rule and all
     rules together tested on every listed element and, when given, on runs of other modules (precision, recall, F1).
  3. LLM, one call per cluster with FPs (largest first): what the members share, why the FPs were listed, what differs
     between hits and FPs in the cited evidence, whether the tokens separate them, a candidate rule, and evidence cited
     as module / element / occurrence / line. Then one synthesis call.
  4. Checks (code). An answer of the wrong shape is not cached and is reported. Every cited element is a member of the
     cluster with that label; every occurrence is an integer, the element's own, and its line matches; whether it is
     the occurrence the generator cited; duplicates removed; enough hits and FPs cited; every rule token is in the
     vocabulary and every rule is tested; the separability claim is compared with the best clean rule of the code's
     search and of the LLM's rule; every number in an answer's text must appear in what that call was given.
  5. Report: assetgen_meta/fault_reporter/<label>/report.md (+ facts.json, ledger.csv, _llm/ cache).

    python assetgen_meta/fault_reporter.py --selftest      (no API call)
"""
from __future__ import annotations

import csv
import hashlib
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

import fp_diagnosis as fd        # noqa: E402

OUT = HERE / "fault_reporter"
PROMPT = HERE / "fault_reporter_prompt.md"
SYNTH = HERE / "fault_reporter_synthesis_prompt.md"
REPORTER_MODEL = "gpt-5.4"
CUTS = (0.0, 0.2, 0.35, 0.5)
MAIN_CUT = 0.35
DRV = {"CARRIES": "data", "SOURCES": "data", "GATES": "control", "SELECTS": "control", "CONSTRAINS": "control",
       "SEQUENCES": "clocks or resets others", "RESETS": "clocks or resets others"}
RCV = {"COPIES": "data", "DERIVES_FROM": "data", "GATED_BY": "controlled", "SELECTED_BY": "controlled",
       "CONSTRAINED_BY": "controlled", "CLOCKED_BY": "clocked", "RESET_BY": "reset"}
IN_MODES, OUT_MODES = fd.IN_MODES, fd.OUT_MODES


# ------------------------------------------------------------------------------------------------ 1. evidence ---
def _end(e: dict, mod: dict, t: str) -> str:
    if t == e["name"]:
        return "itself"
    md = mod["ports"].get(e.get("entity"), {}).get(t)
    if md in IN_MODES and md in OUT_MODES:
        return "inout port"
    if md in IN_MODES:
        return "input port"
    if md in OUT_MODES:
        return "output port"
    return "internal"


def profile(e: dict, mod: dict, level: str = "class") -> frozenset:
    """The element's relationship profile as tokens. 'class' groups record types by meaning and merges tokens that
    always occur together (a self-update recorded on both sides; stored = clocked); 'type' keeps the record types."""
    f = fd.features(e, mod)
    t = {f"kind: {f['kind']}", f"storage: {f['storage']}"}
    if f["field"]:
        t.add("record field")
    for r in e.get("relationship", []) or []:
        ty = r.get("type")
        for tg in r.get("targets", []) or []:
            end = _end(e, mod, tg)
            if level == "type":
                if ty in DRV:
                    t.add(f"{ty} -> {end}")
                elif ty in ("CLOCKED_BY", "RESET_BY"):
                    t.add(ty)
                elif ty in RCV:
                    t.add(f"{ty} <- {end}")
                continue
            if end == "itself" and ty in DRV and DRV[ty] in ("data", "control"):
                t.add(f"updates itself ({DRV[ty]})")
            elif end == "itself" and ty in RCV and RCV[ty] in ("data", "controlled"):
                t.add("updates itself (data)" if RCV[ty] == "data" else "updates itself (control)")
            elif ty in DRV:
                t.add(DRV[ty] if DRV[ty] == "clocks or resets others" else f"{DRV[ty]} -> {end}")
            elif ty == "CLOCKED_BY":
                pass                                           # always with "storage: stored"
            elif ty == "RESET_BY":
                t.add("reset")
            elif ty in RCV:
                t.add(f"{RCV[ty]} <- {end}")
    for c in e.get("connections", []) or []:
        t.add("sub-unit port in" if c.get("mode") in IN_MODES else "sub-unit port out")
    if e.get("constant_drivers"):
        t.add("constant driver")
    return frozenset(t)


def evidence(run_sets: dict, split: str = "tuning", mods: dict | None = None, log=print) -> tuple[list[dict], dict]:
    """Rows of every complete run of every set, with profiles and what the LLM is shown; and the reference entries
    per set (summed over its runs, for recall)."""
    mods = mods if mods is not None else {}
    rows, refs = [], Counter()
    for label, runs in run_sets.items():
        for r in runs or []:
            if not (fd.run_dir(r) / "_nested").exists():
                continue
            if not fd.complete(r, split):
                log(f"   skipped incomplete run {Path(r).name} (a module without output)")
                continue
            rr, s = fd.rows_for_run(r, split, mods)
            refs[label] += s["tp"] + s["fn"]
            for x in rr:
                if not x["in_map"]:
                    continue
                mod = mods[x["module"]]
                e = mod["els"].get((x["entity"], x["element"])) or next(v for k, v in mod["els"].items() if k[1] == x["element"])
                x.update(set=label, run=Path(r).name, prof_class=profile(e, mod, "class"), prof_type=profile(e, mod, "type"),
                         records=_records_text(e, mod), conns=[f"{c.get('instance')}.{c.get('formal')} ({c.get('mode')})"
                                                              for c in e.get("connections", []) or []],
                         const=[str(c.get("value")) for c in e.get("constant_drivers", []) or []],
                         occ_lines={o.get("id"): o.get("line") for o in e.get("occurrences", []) or []})
                rows.append(x)
    return rows, dict(refs)


def _records_text(e, mod, max_rec: int = 14, max_t: int = 6, max_l: int = 4) -> list[str]:
    rel = e.get("relationship", []) or []
    out = []
    for q in rel[:max_rec]:
        tg = q.get("targets", []) or []
        ln = q.get("lines", []) or []
        tt = ", ".join(f"{x} [{_end(e, mod, x)}]" for x in tg[:max_t]) + (f" (+{len(tg) - max_t} more)" if len(tg) > max_t else "")
        ll = ",".join(map(str, ln[:max_l])) + (f" (+{len(ln) - max_l} more)" if len(ln) > max_l else "")
        out.append(f"{q.get('type')} {tt} (lines {ll})")
    if len(rel) > max_rec:
        out.append(f"(+{len(rel) - max_rec} more records)")
    return out


# ------------------------------------------------------------------------------------------------- 2. overlap ---
def token_table(rows, key="prof_class") -> list[dict]:
    tp = [r for r in rows if r["label"] == "TP"]
    fp = [r for r in rows if r["label"] == "FP"]
    c_tp, c_fp = Counter(t for r in tp for t in r[key]), Counter(t for r in fp for t in r[key])
    out = []
    for tok in set(c_tp) | set(c_fp):
        a, b = c_tp[tok] / max(len(tp), 1), c_fp[tok] / max(len(fp), 1)
        out.append({"token": tok, "hits_with": c_tp[tok], "hits_share": round(a, 3), "fp_with": c_fp[tok], "fp_share": round(b, 3),
                    "both": bool(c_tp[tok] and c_fp[tok])})
    return sorted(out, key=lambda x: (-(x["hits_with"] + x["fp_with"]), x["token"]))


def _matrix(rows, key):
    import numpy as np
    vocab = sorted({t for r in rows for t in r[key]})
    ix = {t: i for i, t in enumerate(vocab)}
    X = np.zeros((len(rows), len(vocab)), dtype=bool)
    for i, r in enumerate(rows):
        for t in r[key]:
            X[i, ix[t]] = True
    return X, vocab


def cluster(rows, key="prof_class", cut=MAIN_CUT) -> list[int]:
    """Average-linkage clusters on Jaccard distance; cut 0 groups identical profiles."""
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import pdist
    if cut == 0.0:
        ids = {}
        return [ids.setdefault(r[key], len(ids) + 1) for r in rows]
    X, _ = _matrix(rows, key)
    Z = linkage(pdist(X, metric="jaccard"), method="average")
    return list(fcluster(Z, t=cut, criterion="distance"))


def overlap_by_cut(rows, key="prof_class") -> list[dict]:
    out = []
    for cut in CUTS:
        lab = cluster(rows, key, cut)
        by = defaultdict(Counter)
        for c, r in zip(lab, rows):
            by[c][r["label"]] += 1
        fp = sum(b["FP"] for b in by.values()) or 1
        mixed = sum(b["FP"] for b in by.values() if b["TP"])
        mixed20 = sum(b["FP"] for b in by.values() if b["TP"] / (b["TP"] + b["FP"]) >= 0.2)
        out.append({"cut": cut, "clusters": len(by), "fp_in_mixed": mixed, "fp_in_mixed_share": round(mixed / fp, 3),
                    "fp_in_clusters_with_hit_share_ge_0.2": mixed20, "fp_in_clusters_with_hit_share_ge_0.2_share": round(mixed20 / fp, 3)})
    return out


def separability(rows, key="prof_class", k: int = 15) -> dict:
    """AUC of hit vs FP from the profile: logistic regression in-sample and leave one module out; the share of hits
    among the k nearest profiles of other modules (every row tied with the k-th distance included). On all pooled rows
    and on one row per (module, element)."""
    import numpy as np
    from scipy.spatial.distance import cdist
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    def one(rs):
        X, _ = _matrix(rs, key)
        y = np.array([r["label"] == "TP" for r in rs])
        g = np.array([r["module"] for r in rs])
        if len(set(y)) < 2:
            return {"n": len(rs), "hits": int(y.sum())}
        o = {"n": len(rs), "hits": int(y.sum())}
        o["logistic_in_sample_auc"] = round(float(roc_auc_score(y, LogisticRegression(max_iter=2000).fit(X, y).predict_proba(X)[:, 1])), 3)
        p = np.zeros(len(rs))
        for m in sorted(set(g)):
            te = g == m
            p[te] = (LogisticRegression(max_iter=2000).fit(X[~te], y[~te]).predict_proba(X[te])[:, 1]
                     if len(set(y[~te])) == 2 else y[~te].mean())
        o["logistic_leave_one_module_out_auc"] = round(float(roc_auc_score(y, p)), 3)
        D = cdist(X, X, metric="jaccard")
        q = np.zeros(len(rs))
        for i in range(len(rs)):
            other = np.where(g != g[i])[0]
            d = D[i, other]
            kth = np.sort(d)[min(k, len(d)) - 1]
            q[i] = y[other[d <= kth]].mean()
        o[f"knn{k}_leave_one_module_out_auc"] = round(float(roc_auc_score(y, q)), 3)
        return o
    seen, uniq = set(), []
    for r in sorted(rows, key=lambda r: (r["module"], r["element"], r.get("entity") or "", r.get("run") or "")):
        if (r["module"], r["element"]) not in seen:
            seen.add((r["module"], r["element"]))
            uniq.append(r)
    return {"pooled": one(rows), "one_row_per_element": one(uniq)}


def _apply_rule(rule, toks) -> bool:
    """True when the rule drops the element. A rule needs a non-empty list of tokens in drop_if_all."""
    if not isinstance(rule, dict) or not isinstance(rule.get("drop_if_all"), list) or not rule["drop_if_all"]:
        return False
    unless = rule.get("unless_any") if isinstance(rule.get("unless_any"), list) else []
    return set(rule["drop_if_all"]) <= toks and not (set(unless) & toks)


def _prf(tp, fp, ref):
    P = tp / (tp + fp) if tp + fp else 0.0
    R = tp / ref if ref else 0.0
    return round(P, 3), round(R, 3), round(2 * P * R / (P + R), 3) if P + R else 0.0


def test_rules_together(rules: list, rows, key="prof_class", total_ref: int | None = None) -> dict:
    """Drop an element when any of the rules drops it. total_ref (reference entries of these runs) adds recall and F1."""
    drop = [r for r in rows if any(_apply_rule(u, r[key]) for u in rules)]
    n_tp = sum(1 for r in rows if r["label"] == "TP")
    n_fp = len(rows) - n_tp
    d_tp = sum(1 for r in drop if r["label"] == "TP")
    d_fp = len(drop) - d_tp
    out = {"rules": len(rules), "fp_removed": d_fp, "fp_total": n_fp, "hits_lost": d_tp, "hits_total": n_tp,
           "precision_before": _prf(n_tp, n_fp, 0)[0], "precision_after": _prf(n_tp - d_tp, n_fp - d_fp, 0)[0]}
    if total_ref:
        out["before"] = dict(zip(("P", "R", "F1"), _prf(n_tp, n_fp, total_ref)))
        out["after"] = dict(zip(("P", "R", "F1"), _prf(n_tp - d_tp, n_fp - d_fp, total_ref)))
    return out


def test_rule(rule, rows, key="prof_class", subset=None, total_ref: int | None = None) -> dict:
    return test_rules_together([rule], rows if subset is None else subset, key, total_ref)


def best_rule(members, rows, key="prof_class") -> dict | None:
    """The best clean rule of the searched form: drop an element that has every token all members share, plus up to
    two more tokens, unless it has one 'unless' token; clean = drops at least one FP and no hit of the cluster. Ties go
    to the rule losing fewest hits on all listed elements, then to the fewest tokens."""
    if not any(r["label"] == "FP" for r in members):
        return None
    core = frozenset(set.intersection(*[set(r[key]) for r in members]))
    vocab = sorted({t for r in members for t in r[key]} - core)
    toks = [r[key] for r in members]
    labs = [r["label"] for r in members]
    adds = [()] + [(a,) for a in vocab] + [(a, b) for i, a in enumerate(vocab) for b in vocab[i + 1:]]
    best, best_key = None, None
    for add in adds:
        need = core | set(add)
        hit = [i for i, s in enumerate(toks) if need <= s]
        if not any(labs[i] == "FP" for i in hit):
            continue
        for u in [None] + vocab:
            if u is not None and u in add:
                continue
            drop = [i for i in hit if u is None or u not in toks[i]]
            if any(labs[i] == "TP" for i in drop):
                continue
            fp = sum(labs[i] == "FP" for i in drop)
            if fp == 0:
                continue
            rule = {"drop_if_all": sorted(need), "unless_any": [u] if u else []}
            k = (-fp, None, len(add) + (u is not None))
            if best_key is not None and k[0] > best_key[0]:
                continue
            lost = test_rule(rule, rows, key)["hits_lost"]
            k = (-fp, lost, len(add) + (u is not None))
            if best_key is None or k < best_key:
                best, best_key = (rule, add, u), k
    if best is None:
        return None
    rule, add, u = best
    return {"rule": rule, "separating": list(add), "unless": u, "in_cluster": test_rule(rule, members, key)}


# ----------------------------------------------------------------------------------------------------- 3. LLM ---
def _round_robin(rs, cap):
    by = defaultdict(list)
    for r in sorted(rs, key=lambda r: (r["module"], r["element"], r["run"])):
        if all((x["module"], x["element"]) != (r["module"], r["element"]) for x in by[r["module"]]):
            by[r["module"]].append(r)
    out, i = [], 0
    while len(out) < cap and any(i < len(v) for v in by.values()):
        for m in sorted(by):
            if i < len(by[m]) and len(out) < cap:
                out.append(by[m][i])
        i += 1
    return out


def cluster_message(cid, members, vocab, key="prof_class", cap: int = 10) -> str:
    """The user message for one cluster: the token vocabulary and up to `cap` hits and `cap` FPs, taken in turn from
    each module (deterministic)."""
    shared = Counter(t for r in members for t in r[key])
    n_el = {lab: len({(r["module"], r["element"]) for r in members if r["label"] == lab}) for lab in ("TP", "FP")}
    L = [f"CLUSTER {cid}", "", "TOKEN VOCABULARY (use only these in candidate_rule):", " | ".join(vocab), "",
         f"TOKENS OF THIS CLUSTER (token: members that have it, of {len(members)} listings over all runs):",
         " | ".join(f"{t}: {c}" for t, c in shared.most_common())]
    for lab, name in (("TP", "hit"), ("FP", "false positive")):
        picked = _round_robin([r for r in members if r["label"] == lab], cap)
        L += ["", f"{name.upper()}S ({len(picked)} shown of {n_el[lab]} distinct elements)"]
        for r in picked:
            L += [f"- module {r['module']}, element {r['element']}, label {name}, role {r['role']}, storage "
                  f"{r['features']['storage']}, record field {'yes' if r['features']['field'] else 'no'}",
                  f"  tokens: {' | '.join(sorted(r[key]))}",
                  f"  cited occurrence {r['occurrence']} -> line {r['line']}: {r['rtl']}",
                  f"  cited edge: {r['edge'] or 'none'}",
                  "  records: " + "; ".join(r["records"])]
            if r["conns"]:
                L.append("  connections: " + "; ".join(r["conns"]))
            if r["const"]:
                L.append("  constant drivers: " + "; ".join(r["const"]))
    return "\n".join(L) + "\n"


def _cache_key(system: str, user: str, model: str) -> str:
    return hashlib.sha256((model + "\n" + system + "\n" + user).encode("utf-8")).hexdigest()[:16]


def valid_cluster_answer(a) -> list[str]:
    """Shape problems of a per-cluster answer (empty = usable)."""
    if not isinstance(a, dict):
        return ["not a JSON object"]
    p = []
    for k in ("shared_evidence", "generator_fault", "difference", "separable_by_relationship_types"):
        if not isinstance(a.get(k), str):
            p.append(f"'{k}' is not a string")
    ev = a.get("evidence")
    if not isinstance(ev, list) or not all(isinstance(x, dict) for x in ev):
        p.append("'evidence' is not a list of objects")
    else:
        for x in ev:
            if not isinstance(x.get("module"), str) or not isinstance(x.get("element"), str):
                p.append("an evidence item has a non-string module or element")
                break
            if any(not (x.get(k) is None or isinstance(x.get(k), (int, str))) for k in ("occurrence", "line", "label", "point")):
                p.append("an evidence item has an occurrence, line, label or point that is not a number or text")
                break
    r = a.get("candidate_rule")
    if r is not None and not (isinstance(r, dict) and isinstance(r.get("drop_if_all", []), list)
                              and isinstance(r.get("unless_any", []) or [], list)
                              and all(isinstance(t, str) for t in (r.get("drop_if_all") or []) + (r.get("unless_any") or []))):
        p.append("'candidate_rule' is not {drop_if_all: [str], unless_any: [str]} or null")
    return p


def valid_synthesis(a) -> list[str]:
    if not isinstance(a, dict):
        return ["not a JSON object"]
    p = [f"'{k}' is not a string" for k in ("what_rules_achieve", "missing_information", "limits") if not isinstance(a.get(k), str)]
    fc = a.get("fault_classes")
    if not isinstance(fc, list) or not all(isinstance(c, dict) and isinstance(c.get("clusters", []), list) for c in fc):
        p.append("'fault_classes' is not a list of {name, clusters: [...], description}")
    return p


def ask(client, model, system, user, cache_dir: Path, name: str, stub=None, validate=None, log=print) -> dict | None:
    """One cached JSON call (meta_tools.call_text, effort high). An answer that fails `validate` is kept as raw text
    but not cached as parsed, so a re-run asks again. stub: a function user -> dict, for a plumbing test."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(system, user, model if stub is None else "stub")
    f = cache_dir / f"{name}.{key}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    if stub is not None:
        res, usage, status = stub(user), None, "stub"
    else:
        import meta_tools as mt
        txt, usage, status = mt.call_text(client, model, system, user, "high", 32768, json_mode=True)
        (cache_dir / f"{name}.{key}.raw.txt").write_text(txt, encoding="utf-8")
        res = mt.loads(txt)
    probs = validate(res) if validate else ([] if isinstance(res, dict) else ["not a JSON object"])
    if probs:
        log(f"   {name}: answer not usable ({'; '.join(probs)}; status {status}); not cached, re-run to ask again")
        return None
    if usage:
        res["_usage"] = usage
    f.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


# -------------------------------------------------------------------------------------------------- 4. checks ---
_NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?!\w)(?!\.\d)")


def _numbers(s: str) -> set:
    return set(_NUM.findall(s or ""))


def _int_strict(x):
    return x if isinstance(x, int) and not isinstance(x, bool) else None


def _level(res: dict | None, n_fp: int) -> str:
    """Separability level of one clean rule's in-cluster result."""
    if not res or res["hits_lost"] or not res["fp_removed"]:
        return "no"
    return "yes" if res["fp_removed"] == n_fp else "partly"


def _shown(user: str) -> set:
    return set(re.findall(r"^- module (\S+), element (\S+), label ", user, re.M))


def check_cluster_answer(ans: dict, cid, members, vocab, rows, key="prof_class", user: str = "") -> dict:
    by = {}
    for r in sorted(members, key=lambda r: (r["module"], r["element"], r["run"])):   # the row the message shows
        by.setdefault((r["module"], r["element"]), r)
    seen, checks = set(), []
    for x in ans.get("evidence") or []:
        k = tuple(str(x.get(f)) for f in ("module", "element", "occurrence", "line"))
        if k in seen:
            continue
        seen.add(k)
        r = by.get((x.get("module"), x.get("element")))
        occ, line = _int_strict(x.get("occurrence")), _int_strict(x.get("line"))
        lab = {"hit": "TP", "false positive": "FP"}.get(x.get("label")) if isinstance(x.get("label"), str) else None
        ok_member = r is not None
        ok_label = ok_member and lab == r["label"]
        ok_occ = ok_member and occ is not None and occ in r["occ_lines"]
        ok_line = ok_occ and line is not None and line == r["occ_lines"][occ]
        checks.append({"module": x.get("module"), "element": x.get("element"), "occurrence": x.get("occurrence"), "line": x.get("line"),
                       "claimed_label": x.get("label"), "point": x.get("point", ""),
                       "label": r["label"] if ok_member else None, "member": ok_member, "label_ok": ok_label,
                       "occurrence_own": ok_occ, "line_ok": ok_line, "the_cited_occurrence": ok_member and occ == r["occurrence"],
                       "grounded": ok_member and ok_label and ok_occ and ok_line})
    n_tp = len({(r["module"], r["element"]) for r in members if r["label"] == "TP"})
    n_fp = len({(r["module"], r["element"]) for r in members if r["label"] == "FP"})
    g_tp = len({(c["module"], c["element"]) for c in checks if c["grounded"] and c["label"] == "TP"})
    g_fp = len({(c["module"], c["element"]) for c in checks if c["grounded"] and c["label"] == "FP"})
    rule = ans.get("candidate_rule") if isinstance(ans.get("candidate_rule"), dict) else None
    toks = ((rule or {}).get("drop_if_all") or []) + ((rule or {}).get("unless_any") or [])
    bad_tokens = [t for t in toks if t not in vocab]
    texts = " ".join(str(ans.get(k, "")) for k in ("shared_evidence", "generator_fault", "difference", "reference_convention_hypothesis")) + \
        " " + " ".join(str(x.get("point", "")) for x in ans.get("evidence") or [])
    res = {"cluster": cid, "evidence_n": len(checks), "evidence_grounded": sum(c["grounded"] for c in checks),
           "evidence_checks": checks, "cites_hits": g_tp, "cites_fps": g_fp,
           "evidence_enough": g_tp >= min(2, n_tp) and g_fp >= min(2, n_fp),
           "numbers_not_in_input": sorted(_numbers(texts) - _numbers(user)),
           "rule": rule, "rule_tokens_unknown": bad_tokens,
           "rule_problem": (None if rule is None else "drop_if_all is empty: the rule drops nothing" if not rule.get("drop_if_all")
                            else "unknown tokens" if bad_tokens else None)}
    if rule and not res["rule_problem"]:
        res["rule_in_cluster"] = test_rule(rule, members, key)
        res["rule_all_listed"] = test_rule(rule, rows, key)
    # The claim is about the members the LLM was shown; it is compared on those (the cluster-wide level is reported too)
    shown = _shown(user)
    sm = [r for r in members if (r["module"], r["element"]) in shown] or members
    order = {"no": 0, "partly": 1, "yes": 2}
    code_best_s = best_rule(sm, rows, key)
    lv = max(_level(code_best_s["in_cluster"] if code_best_s else None, sum(r["label"] == "FP" for r in sm)),
             _level(test_rule(rule, sm, key) if rule and not res["rule_problem"] else None, sum(r["label"] == "FP" for r in sm)),
             key=order.get)
    code_best = best_rule(members, rows, key)
    res["separable_code_whole_cluster"] = max(_level(code_best["in_cluster"] if code_best else None, sum(r["label"] == "FP" for r in members)),
                                              _level(res.get("rule_in_cluster"), sum(r["label"] == "FP" for r in members)), key=order.get)
    claim = ans.get("separable_by_relationship_types")
    claim = claim.strip().lower() if isinstance(claim, str) else None
    res["separable_claim"] = claim
    res["separable_code"] = lv
    res["claim_vs_code"] = ("invalid claim" if claim not in order else "agrees" if claim == lv else
                            f"claim '{claim}', but on the members shown the best clean rule found (code search or the analyst's "
                            f"rule) is '{lv}'")
    res["n_distinct"] = {"hits": n_tp, "fps": n_fp}
    return res


def check_synthesis(ans: dict, facts_text: str, cluster_ids) -> dict:
    texts = " ".join(str(ans.get(k, "")) for k in ("what_rules_achieve", "missing_information", "limits")) + " " + \
        " ".join(f"{c.get('name', '')} {c.get('description', '')}" for c in ans.get("fault_classes", []) or [] if isinstance(c, dict))
    ids = {str(c) for c in cluster_ids}
    named = {str(c) for fc in ans.get("fault_classes", []) or [] if isinstance(fc, dict) for c in fc.get("clusters", []) or []}
    return {"numbers_not_in_facts": sorted(_numbers(texts) - _numbers(facts_text)), "unknown_cluster_ids": sorted(named - ids),
            "clusters_covered": len(named & ids), "clusters_total": len(ids)}


# ------------------------------------------------------------------------------------------------ 5. analyse ---
def analyse(run_sets: dict, primary: str, label: str, split: str = "tuning", client=None, model: str = REPORTER_MODEL,
            max_clusters: int = 8, min_fp: int = 3, stub: bool = False, key: str = "prof_class", log=print, llm: bool = True,
            transfer_runs: list[str] | None = None, transfer_split: str = "heldout") -> dict:
    """Everything for the primary run set (clusters, rules, LLM, checks), with the overlap measures for every set.
    transfer_runs: runs of other modules (for example the held-out set) on which every rule is also tested as is."""
    mods: dict = {}
    allrows, refs = evidence(run_sets, split, mods, log)
    rows = [r for r in allrows if r["set"] == primary]
    assert rows, f"no complete run of {primary}"
    trows, trefs = evidence({"transfer": transfer_runs}, transfer_split, {}, log) if transfer_runs else ([], {})
    out_dir = OUT / label
    out_dir.mkdir(parents=True, exist_ok=True)
    ref_p, ref_t = refs.get(primary, 0), trefs.get("transfer", 0)
    facts = {"label": label, "split": split, "primary": primary, "runs": sorted({r["run"] for r in rows}),
             "listed": len(rows), "hits": sum(r["label"] == "TP" for r in rows), "false_positives": sum(r["label"] == "FP" for r in rows),
             "reference_entries": ref_p,
             "token_table_class": token_table(rows, "prof_class"), "token_table_type": token_table(rows, "prof_type"),
             "overlap_class": overlap_by_cut(rows, "prof_class"), "overlap_type": overlap_by_cut(rows, "prof_type"),
             "separability_class": separability(rows, "prof_class"), "separability_type": separability(rows, "prof_type"),
             "by_set": {}}
    for s in run_sets:
        sr = [r for r in allrows if r["set"] == s]
        if sr and s != primary:
            facts["by_set"][s] = {"listed": len(sr), "hits": sum(r["label"] == "TP" for r in sr),
                                  "overlap_class": overlap_by_cut(sr, "prof_class"), "separability_class": separability(sr, "prof_class")}
    lab = cluster(rows, key, MAIN_CUT)
    groups = defaultdict(list)
    for c, r in zip(lab, rows):
        groups[int(c)].append(r)
    order = sorted(groups, key=lambda c: (-sum(r["label"] == "FP" for r in groups[c]), -len(groups[c]), c))
    rename = {c: f"C{i + 1}" for i, c in enumerate(order)}
    for c in order:
        for r in groups[c]:
            r["cluster_id"] = rename[c]
    vocab = sorted({t for r in rows for t in r[key]})
    clusters = []
    for c in order:
        m = groups[c]
        shared = Counter(t for r in m for t in r[key])
        tp, fp = sum(r["label"] == "TP" for r in m), sum(r["label"] == "FP" for r in m)
        br = best_rule(m, rows, key)
        clusters.append({"id": rename[c], "size": len(m), "hits": tp, "false_positives": fp, "hit_share": round(tp / len(m), 3),
                         "tokens_in_all": sorted(t for t, k in shared.items() if k == len(m)),
                         "modules_hits": sorted({r["module"][8:] for r in m if r["label"] == "TP"}),
                         "modules_fps": sorted({r["module"][8:] for r in m if r["label"] == "FP"}),
                         "roles": dict(Counter(r["role"] for r in m)), "cited_edges": dict(Counter((r["edge"] or "none").split(" ")[0] for r in m)),
                         "code_best_rule": br, "code_best_rule_all_listed": test_rule(br["rule"], rows, key, total_ref=ref_p) if br else None,
                         "code_best_rule_transfer": test_rule(br["rule"], trows, key, total_ref=ref_t) if br and trows else None})
    facts["clusters"] = clusters
    facts["transfer"] = {"runs": transfer_runs or [], "split": transfer_split if trows else None, "listed": len(trows),
                         "hits": sum(r["label"] == "TP" for r in trows), "reference_entries": ref_t}
    code_rules = [c["code_best_rule"]["rule"] for c in clusters if c["code_best_rule"]]
    facts["code_rules_together"] = {"all_listed": test_rules_together(code_rules, rows, key, ref_p),
                                    "transfer": test_rules_together(code_rules, trows, key, ref_t) if trows else None}
    # LLM per cluster
    system = PROMPT.read_text(encoding="utf-8")
    picked = [c for c in clusters if c["false_positives"] >= min_fp][:max_clusters] if (llm or stub) else []
    answers, checks, failed = {}, {}, []
    for c in picked:
        members = [r for r in rows if r["cluster_id"] == c["id"]]
        user = cluster_message(c["id"], members, vocab, key)
        a = ask(client, model, system, user, out_dir / "_llm", f"cluster_{c['id']}", stub=_stub_cluster if stub else None,
                validate=valid_cluster_answer, log=log)
        if a is None:
            failed.append(c["id"])
            continue
        answers[c["id"]] = a
        checks[c["id"]] = check_cluster_answer(a, c["id"], members, vocab, rows, key, user)
        if checks[c["id"]].get("rule_all_listed"):
            checks[c["id"]]["rule_all_listed"] = test_rule(checks[c["id"]]["rule"], rows, key, total_ref=ref_p)
            if trows:
                checks[c["id"]]["rule_transfer"] = test_rule(checks[c["id"]]["rule"], trows, key, total_ref=ref_t)
    facts["llm_model"] = "STUB (plumbing test, not an analysis)" if stub else (model if llm else "none (code only)")
    facts["llm_clusters"] = list(answers)
    facts["llm_failed"] = failed
    facts["checks"] = checks
    facts_text = synthesis_facts(facts)
    findings = {cid: {k: v for k, v in a.items() if not k.startswith("_") and k != "evidence"} | {"check": {
        "evidence_grounded": f"{checks[cid]['evidence_grounded']} of {checks[cid]['evidence_n']}",
        "separable_by_code": checks[cid]["separable_code"], "claim_vs_code": checks[cid]["claim_vs_code"]}}
        for cid, a in answers.items()}
    sa = ask(client, model, SYNTH.read_text(encoding="utf-8"),
             "FACTS\n" + facts_text + "\n\nPER-CLUSTER FINDINGS (checked by the program)\n" + json.dumps(findings, indent=1),
             out_dir / "_llm", "synthesis", stub=(lambda u: _stub_synth(u, list(answers))) if stub else None,
             validate=valid_synthesis, log=log) if answers else None
    facts["synthesis"] = sa
    facts["synthesis_check"] = check_synthesis(sa, facts_text, list(answers)) if sa else None
    (out_dir / "facts.json").write_text(json.dumps(facts, indent=1, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else str(o)),
                                        encoding="utf-8")
    _ledger(rows, answers, out_dir / "ledger.csv")
    (out_dir / "report.md").write_text(report_md(facts, answers), encoding="utf-8")
    log(f"report: {out_dir / 'report.md'}")
    facts["_rows"] = rows
    return facts


def synthesis_facts(f: dict) -> str:
    sc, st = f["separability_class"]["pooled"], f["separability_type"]["pooled"]
    L = [f"Listed elements {f['listed']} (hits {f['hits']}, false positives {f['false_positives']}) over runs {', '.join(f['runs'])}; "
         f"reference entries {f['reference_entries']}."]
    for o in f["overlap_class"]:
        L.append(f"Relationship classes, cut {o['cut']}: {o['clusters']} clusters; false positives in clusters that also hold a hit: "
                 f"{o['fp_in_mixed']} (share {o['fp_in_mixed_share']}); in clusters where hits are at least a fifth: "
                 f"{o['fp_in_clusters_with_hit_share_ge_0.2']} (share {o['fp_in_clusters_with_hit_share_ge_0.2_share']}).")
    L.append(f"AUC hit vs false positive from relationship classes: in-sample {sc.get('logistic_in_sample_auc')}, leave one module out "
             f"{sc.get('logistic_leave_one_module_out_auc')} (logistic), {sc.get('knn15_leave_one_module_out_auc')} (nearest profiles).")
    L.append(f"AUC from exact record types: in-sample {st.get('logistic_in_sample_auc')}, leave one module out "
             f"{st.get('logistic_leave_one_module_out_auc')} (logistic), {st.get('knn15_leave_one_module_out_auc')} (nearest profiles).")
    both = [t for t in f["token_table_class"] if t["both"]]
    L.append(f"Relationship-class tokens: {len(f['token_table_class'])}, of which {len(both)} occur on both hits and false positives.")
    tog = f.get("code_rules_together") or {}
    for k, name in (("all_listed", "on these elements (in-sample: the rules were found on them)"),
                    ("transfer", f"on the {f['transfer']['split']} runs (never seen when the rules were found)")):
        a = tog.get(k)
        if a and a.get("before"):
            L.append(f"All {a['rules']} code rules together {name}: drop {a['fp_removed']} of {a['fp_total']} false positives and "
                     f"{a['hits_lost']} of {a['hits_total']} hits; precision {a['before']['P']} -> {a['after']['P']}, recall "
                     f"{a['before']['R']} -> {a['after']['R']}, F1 {a['before']['F1']} -> {a['after']['F1']}.")
    for c in f["clusters"]:
        if c["id"] in f["llm_clusters"]:
            b = c["code_best_rule"]
            L.append(f"Cluster {c['id']}: {c['size']} listings, {c['hits']} hits, {c['false_positives']} false positives. " +
                     (f"Best clean rule of the searched form drops {b['in_cluster']['fp_removed']} of its false positives and no hit; on all "
                      f"listed elements it drops {c['code_best_rule_all_listed']['fp_removed']} false positives and "
                      f"{c['code_best_rule_all_listed']['hits_lost']} hits." if b else
                      "No rule of the searched form drops one of its false positives without one of its hits."))
            x = c.get("code_best_rule_transfer")
            if x:
                L.append(f"Cluster {c['id']} rule on the {f['transfer']['split']} runs: drops {x['fp_removed']} false positives and {x['hits_lost']} hits.")
    return "\n".join(L)


def _ledger(rows, answers, path: Path):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["run", "module", "element", "label", "role", "occurrence", "line", "rtl", "cited_edge", "citation_status",
                    "cluster", "cluster-level fault hypothesis (LLM; its citations are checked, this text is not)"])
        for r in sorted(rows, key=lambda r: (r["label"] != "FP", r["cluster_id"], r["module"], r["element"], r["run"])):
            a = answers.get(r["cluster_id"], {})
            w.writerow([r["run"], r["module"], r["element"], r["label"], r["role"], r["occurrence"], r["line"], r["rtl"],
                        r["edge"], r["status"], r["cluster_id"], a.get("generator_fault", "") if r["label"] == "FP" else ""])


def _fmt_t(a):
    return f"P {a['before']['P']} -> {a['after']['P']}, R {a['before']['R']} -> {a['after']['R']}, F1 {a['before']['F1']} -> {a['after']['F1']}"


def _rules_bullet(f: dict) -> str:
    rs = [c for c in f["clusters"] if c["code_best_rule"]]
    none = [c["id"] for c in f["clusters"] if not c["code_best_rule"] and c["false_positives"] > 0]
    nofp = sum(1 for c in f["clusters"] if c["false_positives"] == 0)
    if not rs:
        return "- **No rule of the searched form drops a false positive of any cluster without dropping one of its hits.**"
    lose = [c for c in rs if c["code_best_rule_all_listed"]["hits_lost"] > 0]
    tog = f.get("code_rules_together") or {}
    a, x = tog.get("all_listed"), tog.get("transfer")
    s = (f"- **General rules cut FPs, but only at a cost and only part of them.** For {len(rs)} of "
         f"{len(f['clusters']) - nofp} clusters with FPs ({nofp} clusters hold hits only), "
         f"a rule of the searched form drops some of the cluster's FPs and none of its hits; applied to every listed element, "
         f"{len(lose)} of them drop hits elsewhere. ")
    if a and a.get("before"):
        s += f"All {a['rules']} together, on these elements (in-sample): {a['fp_removed']} of {a['fp_total']} FPs and {a['hits_lost']} of {a['hits_total']} hits dropped; {_fmt_t(a)}. "
    if x and x.get("before"):
        s += (f"On the {f['transfer']['split']} runs, never seen when the rules were found: {x['fp_removed']} of {x['fp_total']} FPs and "
              f"{x['hits_lost']} of {x['hits_total']} hits dropped; {_fmt_t(x)}. ")
    big = [c for c in f["clusters"] if c["id"] in none][:6]
    if big:
        s += (f"For {len(none)} clusters no rule of the searched form drops an FP without a hit; the largest of them by FP count "
              f"are {', '.join(c['id'] + ' (' + str(c['false_positives']) + ' FP)' for c in big)}.")
    return s


def report_md(f: dict, answers: dict) -> str:
    sc, st = f["separability_class"], f["separability_type"]
    o = {x["cut"]: x for x in f["overlap_class"]}
    both = [t for t in f["token_table_class"] if t["both"]]
    L = [f"# Fault report: {f['label']} ({f['split']}, {f['primary']})", ""]
    if f["llm_model"].startswith("STUB"):
        L += ["> **STUB ANSWERS: this report tests the plumbing only. Every LLM section below is fake.**", ""]
    L += ["How the generator's false positives (FP: listed, not in the reference) relate to its hits (TP: listed and in the "
          "reference), seen through the relationship types the map records for each element and the occurrence the generator "
          "cited for it. All numbers are computed by `assetgen_meta/fault_reporter.py`. "
          + ("This is the code-only report: no LLM was run, so R5 and the synthesis are absent." if f["llm_model"].startswith("none")
             else f"The explanations per cluster come from an LLM ({f['llm_model']}), and the program checks every citation and every rule in them."), "",
          f"Runs: {', '.join(f['runs'])}. Listed {f['listed']} (hits {f['hits']}, FP {f['false_positives']}), pooled over runs; "
          f"{f['reference_entries']} reference entries over these runs.", "", "## Answer", "",
          f"- **Hits and FPs share their relationship types.** {len(both)} of {len(f['token_table_class'])} relationship-class "
          f"tokens occur on both. {o[0.0]['fp_in_mixed_share']:.0%} of FPs have exactly the profile of some hit. In clusters of "
          f"similar profiles (cut {MAIN_CUT}), {o[MAIN_CUT]['fp_in_clusters_with_hit_share_ge_0.2_share']:.0%} of FPs sit in "
          f"clusters where hits are at least a fifth of the members ({o[MAIN_CUT]['fp_in_mixed_share']:.0%} in clusters with any hit).",
          f"- **The profile predicts the reference's decision only weakly on a new module.** AUC for hit vs FP (0.5 = chance, "
          f"1 = perfect) from relationship classes: {sc['pooled'].get('logistic_in_sample_auc')} in-sample, "
          f"{sc['pooled'].get('logistic_leave_one_module_out_auc')} leave one module out (logistic regression), "
          f"{sc['pooled'].get('knn15_leave_one_module_out_auc')} from the nearest profiles of other modules; with one row per "
          f"element, {sc['one_row_per_element'].get('logistic_leave_one_module_out_auc')} and "
          f"{sc['one_row_per_element'].get('knn15_leave_one_module_out_auc')}. From exact record types: "
          f"{st['pooled'].get('logistic_in_sample_auc')} in-sample, {st['pooled'].get('logistic_leave_one_module_out_auc')} leave one module out.",
          _rules_bullet(f), ""]
    if f.get("llm_failed"):
        L += [f"LLM answers not usable (wrong shape; not cached, re-run to ask again): {', '.join(f['llm_failed'])}.", ""]
    if f.get("synthesis"):
        s, ck = f["synthesis"], f["synthesis_check"]
        L += ["## Synthesis (LLM; checked by the program)", "",
              f"Check: numbers not found anywhere in the facts given to it: {ck['numbers_not_in_facts'] or 'none'}; unknown "
              f"cluster ids: {ck['unknown_cluster_ids'] or 'none'}; clusters covered {ck['clusters_covered']} of {ck['clusters_total']}. "
              "A number found in the facts is not proof that it is used for the right quantity.", "", "**Fault classes**", ""]
        L += [f"- **{c.get('name')}** ({', '.join(map(str, c.get('clusters', [])))}): {c.get('description')}"
              for c in s.get("fault_classes", []) or [] if isinstance(c, dict)]
        L += ["", f"**What rules on relationship types achieve, and what they do not.** {s.get('what_rules_achieve', '')}", "",
              f"**Missing information.** {s.get('missing_information', '')}", "", f"**Limits.** {s.get('limits', '')}", ""]
    L += ["## R1. Relationship classes of hits and FPs", "", "Share of hits and of FPs that have each token (pooled over runs).", "",
          "| token | hits with it | share of hits | FPs with it | share of FPs |", "|---|---|---|---|---|"]
    L += [f"| {t['token']} | {t['hits_with']} | {t['hits_share']:.0%} | {t['fp_with']} | {t['fp_share']:.0%} |" for t in f["token_table_class"]]
    L += ["", "## R2. Clusters of similar relationship profiles", "",
          "| cut | clusters | FPs in clusters with any hit | share | FPs in clusters where hits are at least a fifth | share |", "|---|---|---|---|---|---|"]
    L += [f"| {x['cut']} | {x['clusters']} | {x['fp_in_mixed']} | {x['fp_in_mixed_share']:.0%} | {x['fp_in_clusters_with_hit_share_ge_0.2']} | "
          f"{x['fp_in_clusters_with_hit_share_ge_0.2_share']:.0%} |" for x in f["overlap_class"]]
    L += ["", "Exact record types instead of classes:", "", "| cut | clusters | FPs in clusters with any hit | share |", "|---|---|---|---|"]
    L += [f"| {x['cut']} | {x['clusters']} | {x['fp_in_mixed']} | {x['fp_in_mixed_share']:.0%} |" for x in f["overlap_type"]]
    L += ["", f"Clusters at cut {MAIN_CUT}, most FPs first (listings pooled over runs):", "",
          "| cluster | listings | hits | FPs | hit share | tokens in every member | hits in modules | FPs in modules | cited edges |",
          "|---|---|---|---|---|---|---|---|---|"]
    L += [f"| {c['id']} | {c['size']} | {c['hits']} | {c['false_positives']} | {c['hit_share']:.0%} | {'; '.join(c['tokens_in_all'])} | "
          f"{', '.join(c['modules_hits'])} | {', '.join(c['modules_fps'])} | {c['cited_edges']} |" for c in f["clusters"][:15]]
    L += ["", "## R3. Can relationship types predict hit vs FP?", "",
          "| profile | rows | in-sample AUC | leave-one-module-out AUC (logistic) | leave-one-module-out AUC (15 nearest, ties included) |",
          "|---|---|---|---|---|"]
    for name, s in (("relationship classes", sc), ("exact record types", st)):
        for k, lab in (("pooled", "all runs pooled"), ("one_row_per_element", "one row per element")):
            v = s[k]
            L.append(f"| {name} | {lab} ({v['n']}) | {v.get('logistic_in_sample_auc')} | {v.get('logistic_leave_one_module_out_auc')} | "
                     f"{v.get('knn15_leave_one_module_out_auc')} |")
    if f["by_set"]:
        L += ["", "Other run sets (relationship classes, all runs pooled):", "",
              "| run set | listed | hits | FPs with exactly the profile of a hit | leave-one-module-out AUC |", "|---|---|---|---|---|"]
        L += [f"| {s} | {v['listed']} | {v['hits']} | {v['overlap_class'][0]['fp_in_mixed_share']:.0%} | "
              f"{v['separability_class']['pooled'].get('logistic_leave_one_module_out_auc')} |" for s, v in f["by_set"].items()]
    tr = f["transfer"]["split"]
    L += ["", "## R4. Rules found by code inside each cluster, tested on every listed element", "",
          "The searched form: drop an element that has every token all members of the cluster share, plus up to two more tokens, "
          "unless it has one 'unless' token. A rule is clean when it drops some of the cluster's FPs and none of its hits; the "
          "table shows the clean rule dropping the most FPs (ties: fewest hits lost on all listed elements). It is then applied, "
          "as is, to every listed element" + (f" and to the {tr} runs ({', '.join(f['transfer']['runs'])})." if tr else "."), "",
          "| cluster | tokens beyond the cluster's own | unless | FPs dropped in the cluster | all listed: FPs / hits dropped | "
          "all listed: P before -> after |" + (f" {tr}: FPs / hits dropped | {tr}: P before -> after |" if tr else ""),
          "|---|---|---|---|---|---|" + ("---|---|" if tr else "")]
    for c in f["clusters"][:15]:
        b, a, x = c["code_best_rule"], c["code_best_rule_all_listed"], c.get("code_best_rule_transfer")
        if b:
            L.append(f"| {c['id']} | {' + '.join(b['separating']) or '(none)'} | {b['unless'] or '-'} | {b['in_cluster']['fp_removed']} of "
                     f"{b['in_cluster']['fp_total']} | {a['fp_removed']} / {a['hits_lost']} | {a['precision_before']} -> {a['precision_after']} |"
                     + (f" {x['fp_removed']} / {x['hits_lost']} | {x['precision_before']} -> {x['precision_after']} |" if x else (" - | - |" if tr else "")))
        else:
            L.append(f"| {c['id']} | " + ("no FP to drop" if c["false_positives"] == 0 else "no clean rule of the searched form")
                     + f" | - | 0 of {c['false_positives']} | - | - |" + (" - | - |" if tr else ""))
    tog = f.get("code_rules_together") or {}
    for k, name in (("all_listed", "on these elements (in-sample)"), ("transfer", f"on the {tr} runs")):
        a = tog.get(k)
        if a and a.get("before"):
            L += ["", f"All {a['rules']} rules together {name}: {a['fp_removed']} of {a['fp_total']} FPs and {a['hits_lost']} of "
                  f"{a['hits_total']} hits dropped; {_fmt_t(a)}."]
    if answers:
        L += ["", "## R5. The generator's fault per cluster (LLM; every citation and rule checked by the program)", ""]
    for cid, a in answers.items():
        ck = f["checks"][cid]
        c = next(x for x in f["clusters"] if x["id"] == cid)
        L += [f"### {cid}: {c['hits']} hit listings, {c['false_positives']} FP listings "
              f"({ck['n_distinct']['hits']} and {ck['n_distinct']['fps']} distinct elements)", "",
              f"- Evidence: {ck['evidence_grounded']} of {ck['evidence_n']} citations grounded (a member of the cluster, the right "
              f"label, an integer occurrence that is the element's own, the matching line); grounded hits {ck['cites_hits']}, FPs "
              f"{ck['cites_fps']}{'' if ck['evidence_enough'] else ' (fewer than the prompt asks for)'}; "
              f"{sum(1 for x in ck['evidence_checks'] if x['the_cited_occurrence'])} cite the occurrence the generator cited.",
              f"- Numbers in the text not found in the input it was given: {ck['numbers_not_in_input'] or 'none'}.",
              f"- Shared evidence: {a.get('shared_evidence', '')}",
              f"- Generator fault (hypothesis): {a.get('generator_fault', '')}",
              f"- Hits vs FPs: {a.get('difference', '')}",
              f"- Separable by relationship types: claim '{ck['separable_claim']}'; best clean rule found on the members shown: "
              f"'{ck['separable_code']}' ({ck['claim_vs_code']}); on the whole cluster: '{ck['separable_code_whole_cluster']}'."]
        if ck.get("rule"):
            if ck["rule_problem"]:
                L.append(f"- Candidate rule {ck['rule']} rejected: {ck['rule_problem']}"
                         + (f" {ck['rule_tokens_unknown']}" if ck["rule_tokens_unknown"] else ""))
            elif ck.get("rule_all_listed"):
                ri, ra = ck["rule_in_cluster"], ck["rule_all_listed"]
                L.append(f"- Candidate rule {ck['rule']}: in the cluster drops {ri['fp_removed']} FPs and {ri['hits_lost']} hits; on all "
                         f"listed elements {ra['fp_removed']} FPs and {ra['hits_lost']} hits ({_fmt_t(ra)})"
                         + (f"; on {tr}: {ck['rule_transfer']['fp_removed']} FPs and {ck['rule_transfer']['hits_lost']} hits ({_fmt_t(ck['rule_transfer'])})."
                            if ck.get("rule_transfer") else "."))
        if a.get("reference_convention_hypothesis"):
            L.append(f"- Reference convention (hypothesis): {a['reference_convention_hypothesis']}")
        L += ["", "| label | module | element | occurrence -> line | grounded | the cited one | point |", "|---|---|---|---|---|---|---|"]
        for k in ck["evidence_checks"]:
            L.append(f"| {k['claimed_label']} | {k['module']} | `{k['element']}` | {k['occurrence']} -> {k['line']} | "
                     f"{'yes' if k['grounded'] else 'NO'} | {'yes' if k['the_cited_occurrence'] else 'no'} | {k['point']} |")
        L += [""]
    L += ["## R6. Fault ledger", "", "`ledger.csv` lists every listed element with its cited occurrence, line, RTL text, edge, "
          "citation status, cluster and, for FPs, the cluster-level fault hypothesis. It traces each error to the evidence the "
          "generator used; the hypothesis is the LLM's, its citations are checked, its prose is not.", ""]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------------------------- stubs, plot ---
def _stub_cluster(user: str) -> dict:
    """A deterministic answer built from the message, with planted errors the checks must catch: a wrong line, a
    repeated citation, an unknown rule token, and a number that is not in the input."""
    cid = re.search(r"^CLUSTER (\S+)", user, re.M).group(1)
    mem = re.findall(r"^- module (\S+), element (\S+), label (hit|false positive),.*\n  tokens: .*\n  cited occurrence (\S+) -> line (\S+):",
                     user, re.M)
    ev = [{"module": m, "element": e, "occurrence": int(o) if o.isdigit() else o, "line": int(l) if l.isdigit() else l,
           "label": lab, "point": "stub"} for m, e, lab, o, l in mem[:4]]
    if ev:
        ev += [dict(ev[0]), dict(ev[0], line=-1, point="stub: wrong line on purpose")]
    vocab = user.split("TOKEN VOCABULARY (use only these in candidate_rule):\n", 1)[1].split("\n", 1)[0].split(" | ")
    return {"cluster": cid, "shared_evidence": "stub", "generator_fault": "stub 98765", "difference": "none found",
            "separable_by_relationship_types": "no", "candidate_rule": {"drop_if_all": [vocab[0], "not a token"], "unless_any": []},
            "reference_convention_hypothesis": "stub", "evidence": ev}


def _stub_synth(user: str, ids) -> dict:
    return {"fault_classes": [{"name": "stub", "clusters": list(ids) + ["C999"], "description": "stub 12345."}],
            "what_rules_achieve": "stub", "missing_information": "stub", "limits": "stub"}


def plot(facts: dict, ax=None, key: str = "prof_class"):
    """2-D map of the profiles (multidimensional scaling of the Jaccard distances): hits and FPs."""
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.spatial.distance import pdist, squareform
    from sklearn.manifold import MDS
    rows = facts["_rows"]
    X, _ = _matrix(rows, key)
    D = squareform(pdist(X, metric="jaccard"))
    xy = MDS(n_components=2, dissimilarity="precomputed", random_state=0, n_init=1, max_iter=300).fit_transform(D)
    jit = np.random.default_rng(0).normal(0, 0.012, xy.shape)
    ax = ax or plt.gca()
    for lab, col, name in (("FP", "tab:red", "false positive"), ("TP", "tab:blue", "hit")):
        i = [k for k, r in enumerate(rows) if r["label"] == lab]
        ax.scatter(xy[i, 0] + jit[i, 0], xy[i, 1] + jit[i, 1], s=10, alpha=0.45, color=col, label=f"{name} ({len(i)})")
    ax.set(title=f"relationship profiles ({'classes' if key == 'prof_class' else 'record types'}): {facts['label']}",
           xticks=[], yticks=[])
    ax.legend(fontsize=8)
    return ax


# ------------------------------------------------------------------------------------------------ self-test ---
def selftest(log=print) -> bool:
    """Hand-read map lines (traced_inputs_v2/tuning: wdt.txt 286-296, uart.txt 730-741, read 2026-10-02), the rule and
    check logic on small cases, the stub plumbing on a real run, and the checks catching planted errors. No API call."""
    import shutil
    ok = True

    def chk(c, msg):
        nonlocal ok
        ok &= bool(c)
        log(f"{'ok  ' if c else 'FAIL'} {msg}")
    wdt, uart = fd.load_module("tuning", "neorv32_wdt"), fd.load_module("tuning", "neorv32_uart")
    cnt, bit = wdt["els"][("neorv32_wdt", "cnt")], uart["els"][("neorv32_uart", "tx_engine.bitcnt")]
    # wdt.txt 286-296: CONSTRAINS cnt_timeout; SOURCES and DERIVES_FROM cnt; CLOCKED_BY clk_i; RESET_BY rstn_sys_i;
    # GATED_BY ctrl.enable / reset_wdt / cnt_inc; constant drivers
    want_t = {"kind: signal", "storage: stored", "CONSTRAINS -> internal", "SOURCES -> itself", "CLOCKED_BY", "RESET_BY",
              "GATED_BY <- internal", "DERIVES_FROM <- itself", "constant driver"}
    chk(profile(cnt, wdt, "type") == want_t, f"wdt cnt record-type profile {sorted(profile(cnt, wdt, 'type'))}")
    a = profile(cnt, wdt, "class")
    chk(a == {"kind: signal", "storage: stored", "control -> internal", "updates itself (data)", "controlled <- internal", "reset",
              "constant driver"}, f"wdt cnt class profile {sorted(a)}")
    # uart.txt 730-741: the same classes, plus 'record field'
    b = profile(bit, uart, "class")
    chk(b == a | {"record field"}, f"uart tx_engine.bitcnt class profile = wdt cnt's + record field ({sorted(b - a)})")
    chk(abs((1 - len(a & b) / len(a | b)) - 0.125) < 1e-9, "Jaccard distance wdt cnt vs uart tx_engine.bitcnt (classes) = 0.125")
    # rule logic on a small cluster
    R = lambda lab, toks, m="m1", e="x": {"label": lab, "pc": frozenset(toks), "module": m, "element": e}
    mem = [R("TP", {"a", "b", "h"}, e="t1"), R("FP", {"a", "b"}, e="f1"), R("FP", {"a", "b", "c"}, e="f2")]
    chk(_apply_rule({"drop_if_all": ["a"], "unless_any": ["h"]}, frozenset({"a", "b"})) and
        not _apply_rule({"drop_if_all": ["a"], "unless_any": ["h"]}, frozenset({"a", "h"})) and
        not _apply_rule({"drop_if_all": [], "unless_any": ["h"]}, frozenset({"a"})), "rule: drop_if_all with unless_any; empty drop_if_all drops nothing")
    br = best_rule(mem, mem, "pc")
    chk(br and br["unless"] == "h" and br["in_cluster"]["fp_removed"] == 2 and br["in_cluster"]["hits_lost"] == 0,
        f"best_rule finds the clean 'unless' rule ({br and br['rule']})")
    chk(_level({"fp_removed": 2, "hits_lost": 0}, 2) == "yes" and _level({"fp_removed": 1, "hits_lost": 0}, 2) == "partly"
        and _level({"fp_removed": 2, "hits_lost": 1}, 2) == "no", "separability levels yes / partly / no")
    chk(_numbers("drops 999. and 0.48. but line 61") == {"999", "0.48", "61"}, "number check sees numbers that end a sentence")
    chk(valid_cluster_answer({"evidence": ["x"]}) and valid_cluster_answer({"shared_evidence": "s", "generator_fault": "g", "difference": "d",
        "separable_by_relationship_types": "no", "evidence": [], "candidate_rule": {"drop_if_all": "a"}}),
        "malformed answers are refused (evidence of strings; a rule given as a string)")
    chk(valid_cluster_answer({"shared_evidence": "s", "generator_fault": "g", "difference": "d", "separable_by_relationship_types": "no",
                              "evidence": [{"module": "m", "element": "e", "occurrence": [5], "line": 3}], "candidate_rule": None}),
        "an answer with an occurrence given as a list is refused (it would crash the checks after caching)")
    # the stub on a real run: plumbing, planted errors caught, rows equal the scorer
    f = analyse({"claude v1": ["assets_opt_v1_r0"]}, "claude v1", "_selftest", stub=True, max_clusters=2, log=lambda *x: None)
    cks = list(f["checks"].values())
    chk(len(cks) == 2, "two clusters analysed with the stub")
    chk(all(c["evidence_n"] == c["evidence_grounded"] + 1 for c in cks), "the repeated citation is removed and the wrong line is the only ungrounded one")
    chk(all("not a token" in c["rule_tokens_unknown"] for c in cks), "an unknown rule token is rejected")
    chk(all("98765" in c["numbers_not_in_input"] for c in cks), "a number not in the input is flagged in a cluster answer")
    chk("12345" in f["synthesis_check"]["numbers_not_in_facts"] and "C999" in f["synthesis_check"]["unknown_cluster_ids"],
        "the synthesis check catches an invented number (ending a sentence) and an unknown cluster id")
    chk(f["listed"] == 275 and f["hits"] == 104 and f["reference_entries"] == 111, "rows match the scorer on v1 r0 (275 listed, 104 hits, 111 entries)")
    s = f["separability_class"]["pooled"]
    chk(all(0 <= s[k] <= 1 for k in ("logistic_in_sample_auc", "logistic_leave_one_module_out_auc", "knn15_leave_one_module_out_auc")),
        "separability returns AUCs in [0, 1]")
    chk(f["overlap_class"][0]["clusters"] == len({r["prof_class"] for r in f["_rows"]}), "cut 0 = one cluster per identical profile")
    shutil.rmtree(OUT / "_selftest", ignore_errors=True)
    log("self-test " + ("PASS" if ok else "FAIL"))
    return ok


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    import os
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
