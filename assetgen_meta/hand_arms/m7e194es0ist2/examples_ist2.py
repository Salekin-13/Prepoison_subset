"""Worked examples of arm m7e194es0ist2, derived from m7e194es0ist's checked examples.

  transform  (code)  the final object loses "questions", "influence points", "hypotheses", "exclusions" and the flows'
                     "path"; references and their citations are kept exactly. The map and flow excerpts are kept.
                     Writes examples/<name>.ist2.json with the ist analysis as a placeholder.
  check      (code)  the ist checks (occurrences equal the code table, record lines, mirrors, decisions unchanged,
                     every citation verified under trace_check.fits, leak check) plus: no removed field remains, and the
                     analysis has no stage on the four questions or on influence points.

    python assetgen_meta/hand_arms/m7e194es0ist2/examples_ist2.py transform | check
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IST = HERE.parent / "m7e194es0ist"
ROOT = HERE.parents[2]
for p in ("", "assetgen_meta", "blind_agent", str(IST)):
    sys.path.insert(0, str(ROOT / p) if not p.startswith("E:") and not Path(p).is_absolute() else p)
import check_examples as CE      # noqa: E402  (the ist checks and assembler)
import trace_check as TC         # noqa: E402

NAMES = ((1, "omsp_gpio"), (2, "tiny_aes"))
REMOVED = ("questions", "influence points", "hypotheses", "exclusions")


def transform():
    (HERE / "examples").mkdir(exist_ok=True)
    for _i, n in NAMES:
        ad = json.loads((IST / "examples" / f"{n}.adapted.json").read_text(encoding="utf-8"))
        fo = json.loads(json.dumps(ad["final_object"]))
        for k in ("hypotheses", "exclusions"):
            fo.pop(k, None)
        for f in fo.get("use-case flows", []):
            f.pop("path", None)
        for c in fo.get("conceptual assets", []):
            for k in ("questions", "influence points"):
                c.pop(k, None)
        out = {"map_excerpt": ad["map_excerpt"], "flow_excerpt": ad["flow_excerpt"], "analysis": ad["analysis"],
               "final_object": fo, "analysis_rewritten": False}
        (HERE / "examples" / f"{n}.ist2.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"{n}: final object transformed ({sum(len(c['related structural assets']) for c in fo['conceptual assets'])} references kept)")


def check(log=print) -> bool:
    ok = True
    for i, n in NAMES:
        src = json.loads((IST / "examples" / f"{n}.source.json").read_text(encoding="utf-8"))
        ad = json.loads((HERE / "examples" / f"{n}.ist2.json").read_text(encoding="utf-8"))
        # the ist checks, on this object (no file is written)
        ok &= CE.check(i, n, log=lambda s: log("   " + s), ad=ad)
        fo = ad["final_object"]
        left = [k for k in ("hypotheses", "exclusions") if k in fo] + \
               [k for c in fo.get("conceptual assets", []) for k in ("questions", "influence points") if k in c] + \
               ["path" for f in fo.get("use-case flows", []) if "path" in f]
        stale = [w for w in ("four questions", "influence point", "Influence point", "hypothes", "Exclusions (") if w in ad["analysis"]]
        good = not left and not stale and ad.get("analysis_rewritten") is True
        ok &= good
        log(f"   {n} 7 ist2 format: removed fields left {sorted(set(left))}; analysis mentions {stale}; analysis rewritten "
            f"{ad.get('analysis_rewritten')}: {'ok' if good else 'FAIL'}")
    return ok


def assemble_all() -> str:
    out = []
    for i, n in NAMES:
        src = json.loads((IST / "examples" / f"{n}.source.json").read_text(encoding="utf-8"))
        ad = json.loads((HERE / "examples" / f"{n}.ist2.json").read_text(encoding="utf-8"))
        out.append(CE.assemble(i, src, ad))
    return "\n".join(out)


if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:] == ["transform"]:
        transform()
    else:
        sys.exit(0 if check() else 1)
