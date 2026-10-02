import contextlib, io, json, os, sys
from collections import defaultdict, Counter
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
CH = {("neorv32_trng", 0): "trng", ("neorv32_trng", 1): "trng", ("neoTRNG", 0): "neoTRNG", ("neoTRNG_cell", 0): "neoTRNG_cell",
      ("neorv32_cache", 0): "cache_a", ("neorv32_cache", 1): "cache_a", ("neorv32_cache", 2): "cache_b1",
      ("neorv32_cache", 3): "cache_b2", ("neorv32_cache_memory", 0): "cache_memory", ("neorv32_cache_memory", 1): "cache_memory"}
out = HERE / "review"
out.mkdir(parents=True, exist_ok=True)
chunks = defaultdict(lambda: {"entries": [], "elements": []})
for j in jobs:
    name = CH[(j["entity"], j["batch"])]
    L = g["source_lines"](j["src"])
    inv = g["code_inventory"](j)
    va = g["read_answer"]("validate", j)["parsed"]
    ch = chunks[name]
    ch["module"], ch["entity"] = j["module"], j["entity"]
    lo, hi = min(L), max(L)
    ch["range"] = (min(ch.get("range", (lo, hi))[0], lo), max(ch.get("range", (lo, hi))[1], hi))
    for e in j["elems"]:
        n = e["name"]
        ch["elements"].append({k: e.get(k) for k in ("name", "kind", "direction", "type") if e.get(k) is not None})
        w = defaultdict(list)
        for r in inv[n]:
            w[r["Occurrence Lines"]].append(r["Name As Written"])
        for r in sorted(va.get(n, []), key=lambda r: (r["Occurrence Lines"], r.get("Occurrence ID") or 0)):
            ln = r["Occurrence Lines"]
            ch["entries"].append({"element": n, "id": r.get("Occurrence ID"), "line": ln, "line_text": L.get(ln, "").strip(),
                                  "written_on_line": w.get(ln, []), "SITE Tagged": r["SITE Tagged"], "Role": r.get("Role", "")})
for name, ch in chunks.items():
    if name == "cache_b1":
        base = {k: v for k, v in ch.items() if k not in ("entries", "elements")}
        first = [e for e in ch["elements"] if not e["name"].startswith("ctrl_nxt")]
        second = [e for e in ch["elements"] if e["name"].startswith("ctrl_nxt")]
        for nm, els in (("cache_b1", first), ("cache_b2x", second)):
            names = {e["name"] for e in els}
            x = dict(base, elements=els, entries=[e for e in ch["entries"] if e["element"] in names])
            json.dump(x, open(out / (nm + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            print(nm, len(els), "elements", len(x["entries"]), "entries")
        continue
    json.dump(ch, open(out / (name + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(name, ch["module"], ch["entity"], "lines", ch["range"], "elements", len(ch["elements"]), "entries", len(ch["entries"]))
