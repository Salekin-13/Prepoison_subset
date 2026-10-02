"""Arm m7e194es0ist2: two calls.

GENERATION (exec_prompt.txt): m7e194es0ist restructured by the diagnosis (RELATION_EXPERIMENTS_LOG.md, "Traced arm
m7e194es0ist: results and diagnosis") and the evidence workflow (evidence_v1v2_theory_evaluation.json):
  - removed from the call: the four questions (ismq / ismrq / ist lost about 0.09 recall to them), the model-chosen
    influence-point list (v2sec: a destination absorbs borderline primaries), the hypotheses and exclusions lists, the
    flows' element paths (output doubled while concepts fell 21%);
  - restored: ism's established-value criteria (sections 5-8 of the winner), except the confidentiality sentence that
    required an RTL restriction (it made confidentiality "no" on 276/276 concepts; the labelling call now owns it);
  - citation rules: a transport record is never cited through a field (98 of 112 transport references in ist used
    that route); a plain internal signal driven by a sub-unit output may cite that connection as "computes"
    (connection directions now come from the sub-unit's declaration: traced_inputs_v2);
  - kept: every ASSET_DEFINITION.md section 3 rule, the citations (occurrence + edge), the map and the flow graph.
CIA LABELLING (cia_instructions.md): a second call on the fixed list; IEEE P3164 3.1.1 questions answered the way an
SoC security engineer answers them for an IP of unknown use (yes-RTL / yes-assumed / no / unknown, a line for every
yes and no), taught with P3164's worked judgements, paraphrased.

Writes exec_prompt.txt and build_info.json; refuses if a check fails."""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in ("", "assetgen_meta", "blind_agent", str(HERE)):
    sys.path.insert(0, str(ROOT / p) if not Path(p).is_absolute() else p)
import meta_tools as mt          # noqa: E402
import leak_check as LC          # noqa: E402
import examples_ist2 as EX       # noqa: E402

V = "m7e194es0ist2"
INTRO = ("WORKED EXAMPLES\n\nThe cases below apply the procedure above to designs outside the evaluation set. Each shows the "
         "input as you receive it (the relationship map is shortened to the elements the example cites; a real input lists "
         "every element), the private analysis stage by stage, and the final object. The analysis is shown only to "
         "demonstrate the procedure: your answer is the final JSON object alone. Each final object contains the conceptual "
         "assets worked through in its analysis. Where an analysis names further established conceptual assets of its "
         "design, a complete answer reports those as well.\n\n")

if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    sys.stdout.reconfigure(encoding="utf-8")
    assert EX.check(), "examples fail their checks: not built"
    instr = (HERE / "instructions.md").read_text(encoding="utf-8").rstrip() + "\n\n"
    full = instr + INTRO + EX.assemble_all()
    names = LC.names()
    for label, text, exe in ((V, full, True), (V + " cia", (HERE / "cia_instructions.md").read_text(encoding="utf-8"), False)):
        r = mt.check_exec_prompt(text, mt.corpus_names(), label) if exe else mt.check_prompt(text, mt.corpus_names(), label)
        assert r["ok"], (label, r["problems"])
        r = mt.check_prompt(text, names, label)
        assert r["ok"], (label, r["problems"])
    (HERE / "exec_prompt.txt").write_text(full, encoding="utf-8")
    cia = (HERE / "cia_instructions.md").read_text(encoding="utf-8")
    ist = (ROOT / "assetgen_meta/hand_arms/m7e194es0ist/exec_prompt.txt").read_text(encoding="utf-8")
    info = {"version": V, "base": {"version": "m7e194es0ist", "system_sha12": mt.sha12(ist)},
            "system_sha12": mt.sha12(full), "cia_sha12": mt.sha12(cia),
            "chars": {"instructions": len(instr), "examples": len(full) - len(instr), "system": len(full), "cia": len(cia)},
            "inputs": "assetgen_meta/traced_inputs_v2 (connection directions from the sub-units' declarations)",
            "inputs_sha12": {s: hashlib.sha256(b"".join(p.read_bytes() for p in sorted((ROOT / "assetgen_meta/traced_inputs_v2" / s).glob("*.txt")))).hexdigest()[:12]
                             for s in ("tuning", "heldout")},
            "checks": "examples_ist2 check 1-7 PASS; check_exec_prompt PASS; leak check (tuning + held-out names) PASS on both prompts",
            "readings": "hand_arms/read_ist2.py (fixed before the run)"}
    (HERE / "build_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"{V}: generation sha {info['system_sha12']}, {len(full):,} chars (instructions {len(instr):,}); CIA prompt sha "
          f"{info['cia_sha12']}, {len(cia):,} chars; checks PASS")
