# -*- coding: utf-8 -*-
"""Run 6, part 2: the CODE CHECK list validate received, what it fixed, and what is left."""
import contextlib, io, json, os, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import build_occurrence_notebook_v2 as B
os.chdir(B.ROOT)
g = {"__name__": "nb"}
with contextlib.redirect_stdout(io.StringIO()):
    for c in (B.C_SETUP, B.C_PROMPTS, B.C_INPUTS, B.C_CHECKS, B.C_RULEBOOK):
        exec(c, g)
jobs = g["build_jobs"](g["MODULES"]["trng_cache"])
print("1. per batch: CODE CHECK items validate received, and the structure items it fixed")
tot = Counter()
for j in jobs:
    L, S_ = g["source_lines"](j["src"]), g["structures_of"](j["src"])
    cl = g["read_answer"]("classify", j)["parsed"]
    va = g["read_answer"]("validate", j)["parsed"]
    items = [l for l in g["code_checklist"](j, cl).splitlines() if l.startswith("- ")]
    kinds = Counter("structure" if "the program finds" in l else "line/ID" if "holds" in l or "Occurrence ID" in l
                    else "index/slice" if "position in parentheses" in l else "FIELD_USE" if "FIELD_USE" in l
                    else "target/slice rule" if "is tagged" in l else "role word" if "says what something is for" in l
                    else "other" for l in items)
    c = Counter()
    for n, rows in cl.items():
        vmap = {r.get("Occurrence ID"): r for r in va.get(n, [])}
        for r in rows:
            cc = g["structure_compare"](L, S_, r)
            v = vmap.get(r.get("Occurrence ID"))
            vc = g["structure_compare"](L, S_, v) if v else None
            if not cc["ok"]:
                c["listed"] += 1
                c["fixed"] += int(bool(vc and vc["ok"]))
    tot.update(c)
    print(f"   {j['entity']:<22} b{j['batch']}: {len(items):>3} items {dict(kinds)}; structure items fixed {c['fixed']}/{c['listed']}")
print(f"   all: structure items fixed {tot['fixed']}/{tot['listed']}")

print("\n2. the 22 entries whose Structure is still wrong: what the model gives vs the source")
pat = Counter()
for j in jobs:
    L, S_ = g["source_lines"](j["src"]), g["structures_of"](j["src"])
    va = g["read_answer"]("validate", j)["parsed"]
    for n, rows in va.items():
        for r in rows:
            if r["Occurrence Lines"] not in L:
                continue
            cmp_ = g["structure_compare"](L, S_, r)
            if cmp_["ok"]:
                continue
            miss = [x[0] for x in cmp_["missing"]]
            extra = [x[0] for x in cmp_["extra"]]
            if miss and not extra:
                pat["structures left out entirely"] += 1
            elif miss and extra and all(m in extra for m in miss):
                pat["right kinds, wrong lines or opener"] += 1
            else:
                pat["mixed"] += 1
print("   ", dict(pat))

print("\n3. how run 6 compares with run 5 (same 662 inventory occurrences)")
for label, sha_c, sha_v in (("run 5", "b16eb5801259", "c95be46430d8"), ("run 6", g["PROMPT_SHA"]["classify"], g["PROMPT_SHA"]["validate"])):
    n_ok = n = n_entries = 0
    for j in jobs:
        L, S_ = g["source_lines"](j["src"]), g["structures_of"](j["src"])
        for step, sha in (("validate", sha_v),):
            p = g["OUT_DIR"] / step / sha / g["out_path"](step, j).name
            parsed, _ = g["parse_answer"](step, json.loads(p.read_text(encoding="utf-8")), L)
            for name, rows in (parsed or {}).items():
                n_entries += len(rows)
                for r in rows:
                    if r["Occurrence Lines"] in L:
                        n += 1
                        n_ok += int(g["structure_compare"](L, S_, r)["ok"])
    print(f"   {label} validate: {n_entries} entries; Structure exact {n_ok} of {n}")
