import contextlib, io, json, os, sys
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
RUNS = {"run 5": ("b16eb5801259", "c95be46430d8"), "run 6": (g["PROMPT_SHA"]["classify"], g["PROMPT_SHA"]["validate"])}
for label, (sc, sv) in RUNS.items():
    for step, sha in (("classify", sc), ("validate", sv)):
        need = miss = 0
        for j in jobs:
            L, S_ = g["source_lines"](j["src"]), g["structures_of"](j["src"])
            p = g["OUT_DIR"] / step / sha / g["out_path"](step, j).name
            parsed, _ = g["parse_answer"](step, json.loads(p.read_text(encoding="utf-8")), L)
            for n, rows in (parsed or {}).items():
                for r in rows:
                    if r["Occurrence Lines"] not in L or not ({"LHS_PROC", "IF_COND", "EDGE_CHECK"} & set(r["SITE Tagged"])):
                        continue
                    cmp_ = g["structure_compare"](L, S_, r)
                    encl = {x for x in cmp_["want"] if x[0] in ("branch", "alternative")}
                    if encl:
                        need += 1
                        miss += int(not (encl & set(cmp_["got"])))
        print(f"   {label} {step}: entries inside a branch or alternative with no correct enclosing one: {miss} of {need}")
