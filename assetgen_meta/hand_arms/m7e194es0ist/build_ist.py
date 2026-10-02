"""Arm m7e194es0ist (traced): the winner m7e194es0ism restructured into the user's eight parts (inputs, definition,
purpose and flows, flow graph, four questions per value, roles along the path, exclusions with reasons, checks), with
a cited occurrence and edge for every decision. Input: numbered RTL + the code-built relationship map with occurrence
IDs + a flow graph computed by code (assetgen_meta/traced_inputs.py).

Kept from the winner (ASSET_DEFINITION.md section 3 rows with a measured contribution, verbatim): the consumed-input
"sets" rule and the several-references-per-flow rule (winner line 13), carriers secondary (13, 15, 17), transport
excluded whole and by field (16, 221-222), sub-block connection fields (17, 223-224), clock / clock-enable / reset
(13, 219), port named whole (16, 19, 220), the four realization labels (205-208), the restrictions (212-226), the
precedence rule (228), the naming rule (230), the objective serialization (275), the evidence criteria for C / I / A
(section 6); the worked examples keep their decisions exactly (check_examples.py check 4).
Added from ASSET_DEFINITION.md section 2: the definition paragraph, the state / setting / decision sentence (row 1),
the objective by what the consumer loses. Not added (evaluation layer only): reset generation, memory arrays, GUARD.

Writes exec_prompt.txt and build_info.json. Refuses if check_examples.py or meta_tools.check_exec_prompt fails."""
import hashlib, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in ("", "assetgen_meta"):
    sys.path.insert(0, str(ROOT / p))
import meta_tools as mt          # noqa: E402
import check_examples as CE      # noqa: E402

V = "m7e194es0ist"
INTRO = ("WORKED EXAMPLES\n\nThe cases below apply the procedure above to designs outside the evaluation set. Each shows the "
         "input as you receive it (the relationship map is shortened to the elements the example cites; a real input lists "
         "every element), the private analysis stage by stage, and the final object. The analysis is shown only to "
         "demonstrate the procedure: your answer is the final JSON object alone. Each final object contains the conceptual "
         "assets worked through in its analysis. Where an analysis names further established conceptual assets of its "
         "design, a complete answer reports those as well.\n\n")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    import os
    os.chdir(ROOT)
    assert all(CE.check(i, n) for i, n in ((1, "omsp_gpio"), (2, "tiny_aes"))), "examples fail their checks: not built"
    instr = (HERE / "instructions.md").read_text(encoding="utf-8").rstrip() + "\n\n"
    ex = []
    for i, n in ((1, "omsp_gpio"), (2, "tiny_aes")):
        src = json.loads((HERE / "examples" / f"{n}.source.json").read_text(encoding="utf-8"))
        ad = json.loads((HERE / "examples" / f"{n}.adapted.json").read_text(encoding="utf-8"))
        ex.append(CE.assemble(i, src, ad))
    full = instr + INTRO + "\n".join(ex)
    chk = mt.check_exec_prompt(full, mt.corpus_names(), V)
    assert chk["ok"], chk["problems"]
    sys.path.insert(0, str(ROOT / "blind_agent"))
    import leak_check as LC
    r = mt.check_prompt(full, LC.names(), V)
    assert r["ok"], r["problems"]
    (HERE / "exec_prompt.txt").write_text(full, encoding="utf-8")
    win = (ROOT / "assetgen_meta/hand_arms/m7e194es0ism/exec_prompt.txt").read_text(encoding="utf-8")
    info = {"version": V, "base": {"version": "m7e194es0ism", "system_sha12": mt.sha12(win)}, "system_sha12": mt.sha12(full),
            "chars": {"instructions": len(instr), "examples": len(full) - len(instr), "system": len(full)},
            "input": "numbered RTL + relationship map with occurrence IDs + code flow graph (assetgen_meta/traced_inputs.py)",
            "inputs_sha12": {split: hashlib.sha256(b"".join(p.read_bytes() for p in sorted((ROOT / "assetgen_meta/traced_inputs" / split).glob("*.txt")))).hexdigest()[:12]
                             for split in ("tuning", "heldout")},
            "checks": "check_exec_prompt PASS; leak check (tuning + held-out names) PASS; check_examples PASS",
            "readings": "hand_arms/read_trace_arm.py (fixed before the run)"}
    (HERE / "build_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"{V}: sha {info['system_sha12']}, {len(full):,} chars (instructions {len(instr):,}, examples {len(full) - len(instr):,}); checks PASS")
