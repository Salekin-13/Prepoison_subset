# -*- coding: utf-8 -*-
"""Run 6 (rulebook 34d10274b852; classify 6f4f22e256e3, validate f4082229020d) against run 5 and the audited run 4."""
import contextlib, io, json, os, re, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
S = HERE.parent
sys.path.insert(0, str(S))
import build_occurrence_notebook_v2 as B

os.chdir(B.ROOT)
g = {"__name__": "nb"}
with contextlib.redirect_stdout(io.StringIO()):
    for c in (B.C_SETUP, B.C_PROMPTS, B.C_INPUTS, B.C_CHECKS, B.C_RULEBOOK):
        exec(c, g)
assert g["SELFTEST_OK"] and g["RULEBOOK_SHA"] == "34d10274b852"
jobs = g["build_jobs"](g["MODULES"]["trng_cache"])
OUT = g["OUT_DIR"]
OLD = {"run5": {"classify": "b16eb5801259", "validate": "c95be46430d8"},
       "run4": {"validate": "0cc1dedc8ba4"}}

def answers(step, sha):
    out = {}
    for j in jobs:
        p = OUT / step / sha / g["out_path"](step, j).name
        rec = json.loads(p.read_text(encoding="utf-8"))
        parsed, _ = g["parse_answer"](step, rec, g["source_lines"](j["src"]))
        for n, rows in (parsed or {}).items():
            out[(j["entity"], n)] = rows
    return out

def current(step):
    out = {}
    for j in jobs:
        a = g["read_answer"](step, j)
        for n, rows in (a["parsed"] or {}).items():
            out[(j["entity"], n)] = rows
    return out

V6, C6 = current("validate"), current("classify")
V5, V4 = answers("validate", OLD["run5"]["validate"]), answers("validate", OLD["run4"]["validate"])
INV = {}
for j in jobs:
    for n, rows in g["code_inventory"](j).items():
        INV[(j["entity"], n)] = rows

def tagmap(P):
    m = defaultdict(list)
    for k, rows in P.items():
        for r in sorted(rows, key=lambda r: (r["Occurrence Lines"], r.get("Occurrence ID") or 0)):
            m[(k[0], k[1], r["Occurrence Lines"])].append(tuple(sorted(r.get("SITE Tagged") or [])))
    return {k: sorted(v) for k, v in m.items()}

T6, T5, T4 = tagmap(V6), tagmap(V5), tagmap(V4)
aud = json.load(open(OUT / "_audit_2026-09-15" / "audit_results.json", encoding="utf-8"))
verdict = defaultdict(list)
for r in aud:
    for f in r.get("findings", []):
        verdict[(r["entity"], f["element"], f["line"])].append((f["verdict"], f.get("verified_category")))

print("1. tags: run 6 vs run 5 (validate), by line")
same = diff = 0
rows_out = []
for k in sorted(set(T6) | set(T5), key=str):
    a, b = T5.get(k), T6.get(k)
    if a == b:
        same += len(b or [])
    else:
        diff += 1
        rows_out.append((k, a, b, verdict.get(k, [])))
print(f"   entries on lines with identical tag lists: {same}; lines that differ: {diff}")
for k, a, b, vv in rows_out:
    print(f"   {k[0]} {k[1]} @ {k[2]}: run5 {a} -> run6 {b}   run-4 audit: {vv}")

print("\n2. the run-5 tag errors, as run 6 tags them")
KNOWN = [("neorv32_cache", "ctrl.buf_req", 118), ("neorv32_cache", "ctrl.buf_req", 137), ("neorv32_cache", "ctrl.buf_req", 170),
         ("neorv32_cache", "ctrl.tag", 225), ("neorv32_cache", "ctrl.ofs", 244), ("neorv32_cache", "ctrl.ofs", 245),
         ("neorv32_cache", "ctrl.buf_err", 254), ("neorv32_cache", "host_req_i.addr", 180), ("neorv32_cache", "host_req_i.addr", 181),
         ("neorv32_cache_memory", "acc_idx", 383), ("neorv32_cache_memory", "acc_adr", 414), ("neorv32_cache_memory", "acc_adr", 423)]
for k in KNOWN:
    print(f"   {k[1]} @ {k[2]}: run5 {T5.get(k)} -> run6 {T6.get(k)}")

print("\n3. structures still wrong in run 6 validate, grouped by element")
bad = Counter()
for j in jobs:
    L, S_ = g["source_lines"](j["src"]), g["structures_of"](j["src"])
    for e in j["elems"]:
        for r in V6.get((j["entity"], e["name"]), []):
            if r["Occurrence Lines"] in L and not g["structure_compare"](L, S_, r)["ok"]:
                bad[(j["entity"], e["name"])] += 1
print("   ", dict(bad), "total", sum(bad.values()))

print("\n4. classify -> validate transitions (run 6), Structure")
trans = Counter()
for j in jobs:
    L, S_ = g["source_lines"](j["src"]), g["structures_of"](j["src"])
    for e in j["elems"]:
        k = (j["entity"], e["name"])
        cm = {r.get("Occurrence ID"): r for r in C6.get(k, [])}
        for r in V6.get(k, []):
            c = cm.get(r.get("Occurrence ID"))
            v_ok = g["structure_compare"](L, S_, r)["ok"]
            if c is None:
                trans[("no classify entry", v_ok)] += 1
                continue
            trans[(g["structure_compare"](L, S_, c)["ok"], v_ok)] += 1
for t, n in sorted(trans.items(), key=str):
    print("   classify ok" if t[0] is True else "   classify wrong" if t[0] is False else f"   {t[0]}",
          "-> validate ok" if t[1] else "-> validate wrong", ":", n)

print("\n5. Roles: numbers, length, FIELD_USE naming a field, actuals naming a formal")
roles = [(k, r) for k, rows in V6.items() for r in rows]
digits = [(k[1], r["Occurrence Lines"]) for k, r in roles if re.search(r"\b\d{2,}\b", r.get("Role", ""))]
fu_no_field = [(k[1], r["Occurrence Lines"], r["Role"]) for k, r in roles
               if "FIELD_USE" in r["SITE Tagged"] and not re.search(r"field\s+\w+", r.get("Role", ""), re.I)]
aa_no_formal = [(k[1], r["Occurrence Lines"], r["Role"]) for k, r in roles
                if "ASSOC_ACTUAL" in r["SITE Tagged"] and not re.search(r"formal", r.get("Role", ""), re.I)]
lens = sorted(len(r.get("Role", "").split()) for k, r in roles)
print(f"   entries {len(roles)}; Roles with a 2+ digit number {len(digits)}; FIELD_USE Roles not naming a field {len(fu_no_field)}; "
      f"ASSOC_ACTUAL Roles not naming a formal {len(aa_no_formal)}; words min {lens[0]} median {lens[len(lens)//2]} max {lens[-1]}")
for x in fu_no_field[:5] + aa_no_formal[:5]:
    print("     ", x)
json.dump([{"entity": k[0], "element": k[1], "id": r.get("Occurrence ID"), "line": r["Occurrence Lines"],
            "tags": r["SITE Tagged"], "role": r.get("Role", ""),
            "run5_tags": None} for k, r in roles], open(HERE / "validate_entries_run6.json", "w", encoding="utf-8"), indent=1)
