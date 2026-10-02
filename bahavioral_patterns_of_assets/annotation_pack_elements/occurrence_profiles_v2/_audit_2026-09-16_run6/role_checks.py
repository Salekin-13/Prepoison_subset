import contextlib, io, json, os, re, sys
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
RUNS = {"run 5": "c95be46430d8", "run 6": g["PROMPT_SHA"]["validate"]}
for label, sha in RUNS.items():
    tot = fu = fu_bad = ps = ps_bad = df = df_bad = aa = aa_bad = 0
    lens = []
    for j in jobs:
        L = g["source_lines"](j["src"])
        p = g["OUT_DIR"] / "validate" / sha / g["out_path"]("validate", j).name
        parsed, _ = g["parse_answer"]("validate", json.loads(p.read_text(encoding="utf-8")), L)
        for n, rows in (parsed or {}).items():
            for r in rows:
                role, tags = r.get("Role", ""), r["SITE Tagged"]
                tot += 1
                lens.append(len(role.split()))
                if "FIELD_USE" in tags:
                    fu += 1
                    fld = n.split(".")[-1] if "." in n else None
                    fu_bad += int(not re.search(r"field", role, re.I))
                if "PART_SELECT" in tags:
                    ps += 1
                    ps_bad += int(not re.search(r"downto|\bto\b|range|bits", role, re.I))
                if "DECL_FIELD" in tags:
                    df += 1
                    df_bad += int(not re.search(r"in this source|outside", role, re.I))
                if "ASSOC_ACTUAL" in tags:
                    aa += 1
                    aa_bad += int(not re.search(r"formal|associated with|=>", role, re.I))
    lens.sort()
    print(f"   {label}: {tot} entries; Role words median {lens[len(lens)//2]}, max {lens[-1]}")
    print(f"      FIELD_USE Roles not naming a field: {fu_bad} of {fu}; PART_SELECT Roles without a range: {ps_bad} of {ps}; "
          f"DECL_FIELD Roles not saying where the record type is: {df_bad} of {df}; actual Roles without a formal: {aa_bad} of {aa}")
