"""Hand arm m7e194es0ism: the seed's execution prompt + two worked examples that apply the SEED'S OWN procedure.

Examples: omsp_gpio and tiny_aes, the baseline's two port-heavy designs. Their verified concepts and verified element
lists are kept (every verified element is in the final object); each example's private analysis walks the seed's
stages a-f, and anything added to the verified list is a realization point the seed's rules require for the same
concept (tables in seedmethod_drafts/<ip>.json, tied to seed line numbers). Drafted by gpt-6-astra
(draft_seedmethod_examples.py), checked by seedmethod_examples.check_draft, reviewed by two independent auditors.

System prompt = seed + "\\n\\n" + the example block, joined by code as the baseline joins its core and examples.
"""
from __future__ import annotations

import hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "assetgen_meta")); sys.path.insert(0, str(HERE))
import seedmethod_examples as sx  # noqa: E402

VERSION = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "m7e194es0ism"
DRAFTS = HERE / "seedmethod_drafts"
OUT_DIR = HERE / VERSION
ORDER = ("omsp_gpio", "tiny_aes")
STAGES = (("a_closed_set", "a. Build the closed set."), ("b_relationships", "b. Derive relationships."),
          ("c_flows", "c. Derive use-case flows."), ("d_conceptual", "d. Identify conceptual assets."),
          ("e_structural", "e. Identify structural references."), ("f_validation", "f. Validate."))

PREAMBLE = ("WORKED EXAMPLES\n\n"
            "The cases below apply the procedure above to designs outside the evaluation set. Each shows the input exactly "
            "as you receive it, the private analysis stage by stage, and the final object. The analysis is shown only to "
            "demonstrate the procedure: your answer is the final JSON object alone. Each final object contains the "
            "conceptual assets worked through in its analysis. Where an analysis names further Established conceptual "
            "assets of its design, a complete answer reports those as well.")

LEAKS = [r"\bline \d+", r"\blines \d+", r"\bL\d{2,3}\b", r"\bverified\b", r"\bannotation\b", r"\bdeparture", r"\bgolden\b",
         r"\bPROCEDURE\b"]


def example_text(k: int, ip: str, d: dict) -> str:
    case = sx.load_case(ip)
    parts = [f"### WORKED EXAMPLE {k}: {ip}", "",
             f"TARGET IP MODULE: {ip}", "", "=== RTL ===", case["rtl"], "",
             f"Identify the primary security assets for '{ip}' and return the JSON object per the contract.", "",
             "PRIVATE ANALYSIS (a demonstration of the procedure; never part of an answer)"]
    for key, title in STAGES:
        # The drafter states in stage d that the design has further Established concepts a full answer would report;
        # the audit asked for that sentence in its own words rather than appended here.
        parts += [title, d["analysis"][key].strip()]
    parts += ["", "FINAL OBJECT", json.dumps(d["output"], indent=1, ensure_ascii=False)]
    return "\n".join(parts)


def build():
    seed = sx.SEED_PATH.read_text(encoding="utf-8")
    blocks, info = [PREAMBLE], {"version": VERSION, "examples": {}}
    for k, ip in enumerate(ORDER, 1):
        d = json.loads((DRAFTS / f"{ip}.json").read_text(encoding="utf-8"))
        chk = sx.check_draft(sx.load_case(ip), d)
        assert not chk["hard"], f"{ip}: hard problems remain: {chk['hard']}"
        txt = example_text(k, ip, d)
        prose = txt[txt.index("PRIVATE ANALYSIS"):]
        for pat in LEAKS:
            hit = re.search(pat, prose)
            assert not hit, f"{ip}: example text leaks {hit.group(0)!r}: ...{prose[max(0, hit.start() - 60):hit.end() + 60]}..."
        blocks.append(txt)
        info["examples"][ip] = {"elements": len(chk["reported"]), "additions": len(chk["additions"]),
                                "verified": len(sx.load_case(ip)["elements"]), "flags": chk["flags"]}
    ex = "\n\n".join(blocks)
    system = seed + "\n\n" + ex
    info.update({"seed_sha12": hashlib.sha256(seed.encode()).hexdigest()[:12],
                 "system_sha12": hashlib.sha256(system.encode()).hexdigest()[:12],
                 "chars": {"seed": len(seed), "examples": len(ex), "system": len(system)}})
    return system, ex, info


if __name__ == "__main__":
    import meta_tools as mt
    system, ex, info = build()
    chk = mt.check_exec_prompt(system, mt.corpus_names(str(ROOT)), VERSION)
    assert chk["ok"], chk
    assert system.startswith(sx.SEED_PATH.read_text(encoding="utf-8") + "\n\n")
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "exec_prompt.txt").write_text(system, encoding="utf-8")
    (OUT_DIR / "examples.txt").write_text(ex, encoding="utf-8")
    (OUT_DIR / "build_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(json.dumps(info, indent=2))
