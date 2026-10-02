"""Draft the seed-method worked examples with gpt-6-astra, check them with code, and revise once on hard problems.

Per design (omsp_gpio, tiny_aes): the drafter gets the seed execution prompt with line numbers (the PROCEDURE), the
design's RTL with line numbers, a code-built declaration inventory, and the VERIFIED annotation (concepts and element
list, fixed). It returns the private analysis in the seed's stages a-f, the final object, and tables that tie every
departure from the verified annotation to seed lines. seedmethod_examples.check_draft() then checks every name, quote
and label against the RTL. Outputs: assetgen_meta/hand_arms/seedmethod_drafts/<ip>.json (+ .check.json, usage)."""
from __future__ import annotations

import json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "assetgen_meta")); sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8")
for line in (ROOT / "API.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
from openai import OpenAI
import meta_tools as mt
import seedmethod_examples as sx

OUT = HERE / "seedmethod_drafts"; OUT.mkdir(exist_ok=True)
MODEL = "gpt-6-astra"

SYSTEM = """You write ONE worked example that demonstrates an execution procedure (the PROCEDURE, given below with line numbers) on one Verilog design. The example will be appended to the PROCEDURE and shown to a smaller model that must apply the PROCEDURE to other designs. So the example must apply the PROCEDURE exactly: its stages, rules, labels, precedence and evidence standard as written. It must never contradict, weaken, extend or add to a rule. Where the PROCEDURE is terse, the example shows how a stated rule applies to concrete RTL; that is its purpose. It may not introduce any criterion the PROCEDURE does not state.

FIXED INPUTS, from a verified annotation of this design. Do not change them.
- The conceptual assets, with their exact wording. Use each one verbatim as a "concept" of the output, in the given order, and evaluate it under the PROCEDURE.
- The verified element list. Every listed element is a correct primary asset of its concept, with the given entity. Keep every one. Show, under the PROCEDURE's own rules, why each is a structural reference of its concept and which realization label applies. If you believe a PROCEDURE rule excludes a verified element, keep the element anyway and report the conflict in "verified_conflicts" with the PROCEDURE line numbers. Never bend a rule to hide a conflict.

WHAT YOU DECIDE, by the PROCEDURE alone:
- The security objective of each concept: apply the PROCEDURE's sections 4, 6 and 7 and its serialization rule (line 275) to the RTL alone. If yours differs from the verified objective, record it in "objective_changes".
- Further structural references for the SAME concepts. The PROCEDURE requires every demonstrated eligible realization point of an Established concept to be considered (line 265): for example an element that stores the concept's value (line 216), an input port its declaring entity reads to store, compute from or decide on the value (lines 13, 206), an output port through which the value leaves its entity (lines 208, 217), including elements of other entities in the same RTL (lines 230, 288). Report those, and nothing the PROCEDURE calls secondary, forwarding, gating, a carrier, clock or reset (lines 15, 212-219). Record every element you add in "departures". Do not add new concepts.
- Other flows: if the PROCEDURE would establish further conceptual assets in this design, list them in "other_established_concepts" (short). They are not part of this example's output.

EVIDENCE FORMAT
- The smaller model receives RTL without line numbers. So cite RTL by quoting code in backticks, copied exactly from ONE line of the RTL listing (leave out the line-number prefix; whitespace may be collapsed). A program checks every backtick quote against the RTL; a quote that is not on one line fails. Bare element names in backticks are fine.
- In "analysis" and in each "reasoning", refer to PROCEDURE rules by their words (a short quote), never by line numbers. Line numbers appear only in the four tables.
- Write no counts of expected assets, quotas, thresholds or percentages. Name no other design. Do not mention the verified annotation, the tables or these instructions in "analysis" or "output": the example must read as the PROCEDURE applied to the RTL.
- Keep it compact: where the RTL repeats a structure (several identical ports or rounds), show one instance and state that the others follow identically, naming them.

ANALYSIS: the PROCEDURE's private stages, section 9 a-f, in its own terms:
 a_closed_set: the candidate universe (entities; ports with directions; the internal signals and registers that matter), summarized.
 b_relationships: the data-flow, control-flow, state and structural facts that matter, each with a quote.
 c_flows: the use-case flows the RTL implements, all of them briefly, including those outside this example's output.
 d_conceptual: each fixed concept with its evidence level for each objective and the chain "RTL evidence -> identifiable value, state, or decision -> security significance -> objective"; say which objectives are not established and why.
 e_structural: for each concept, each reference with its realization label and the PROCEDURE rule that makes it eligible; then the notable candidates that are NOT references and the rule that excludes each.
 f_validation: the PROCEDURE's section 10 checks, applied.
Each "reasoning" in the output follows line 277: concept, implemented flow, supporting RTL behavior (with quotes), security property, basis of the structural realization.

Return ONE JSON object and nothing else:
{"analysis": {"a_closed_set": "", "b_relationships": "", "c_flows": "", "d_conceptual": "", "e_structural": "", "f_validation": ""},
 "output": <the final object, exactly in the PROCEDURE's EXECUTOR OUTPUT SCHEMA>,
 "verified_placement": [{"element": "", "entity": "", "realization": "", "seed_lines": [0], "why": ""}],
 "departures": [{"element": "", "entity": "", "realization": "", "concept": "", "seed_lines": [0], "why": ""}],
 "objective_changes": [{"concept": "", "verified_objective": "", "output_objective": "", "seed_lines": [0], "why": ""}],
 "verified_conflicts": [{"element": "", "entity": "", "seed_lines": [0], "why": ""}],
 "other_established_concepts": [{"concept": "", "objective": "", "seed_lines": [0], "why": ""}]}"""


def numbered(text: str) -> str:
    return "\n".join(f"{i:4d}| {l}" for i, l in enumerate(text.splitlines(), 1))


def user_message(case: dict, seed: str) -> str:
    inv = sx.inventory(case["rtl"])
    by_mod = {}
    for (m, n), d in inv.items():
        by_mod.setdefault(m, []).append(f"{n}:{d['kind']}{'(reg)' if d['output_reg'] else ''}")
    concepts = "\n".join(f"- {c['id']} | verified objective {c['objective']} | {c['concept']}" for c in case["concepts"])
    elems = "\n".join(f"- {e['entity']}.{e['name']} -> {e['concept']} (verified note: {e['justification']})" for e in case["elements"])
    return (f"PROCEDURE (the execution prompt, with line numbers):\n{numbered(seed)}\n\n"
            f"DESIGN: {case['ip']}. The smaller model will receive exactly this user message:\n"
            f"TARGET IP MODULE: {case['ip']}\n\n=== RTL ===\n<the RTL below, without line numbers>\n\n"
            f"RTL WITH LINE NUMBERS:\n{numbered(case['rtl'])}\n\n"
            f"DECLARATION INVENTORY (built by a program from the RTL; module: name:kind):\n"
            + "\n".join(f"{m}: {', '.join(v)}" for m, v in by_mod.items()) +
            f"\n\nFIXED CONCEPTS (use verbatim, in this order):\n{concepts}\n\nVERIFIED ELEMENTS (keep all):\n{elems}\n")


def draft(client, case: dict, seed: str, feedback: str | None = None, previous: dict | None = None):
    user = user_message(case, seed)
    if feedback:
        user += ("\n\nYOUR PREVIOUS DRAFT failed a program check. Fix every listed problem and return the whole object "
                 f"again.\nPROBLEMS:\n{feedback}\n\nPREVIOUS DRAFT:\n{json.dumps(previous, ensure_ascii=False)}")
    txt, usage, status = mt.call_text(client, MODEL, SYSTEM, user, "high", 65536, json_mode=True)
    return mt.loads(txt), usage, status


def main(ips=("omsp_gpio", "tiny_aes")):
    sx.selftest()
    seed = sx.SEED_PATH.read_text(encoding="utf-8")
    client = OpenAI(); usage_all = []
    for ip in ips:
        case = sx.load_case(ip)
        d, u, st = draft(client, case, seed); usage_all.append(u)
        chk = sx.check_draft(case, d)
        print(time.strftime("%H:%M:%S"), ip, "draft 1: hard", len(chk["hard"]), "flags", len(chk["flags"]), flush=True)
        if chk["hard"]:
            (OUT / f"{ip}.draft1.json").write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
            d, u, st = draft(client, case, seed, "\n".join(chk["hard"]), d); usage_all.append(u)
            chk = sx.check_draft(case, d)
            print(time.strftime("%H:%M:%S"), ip, "draft 2: hard", len(chk["hard"]), "flags", len(chk["flags"]), flush=True)
        (OUT / f"{ip}.json").write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
        (OUT / f"{ip}.check.json").write_text(json.dumps(chk, indent=1, ensure_ascii=False), encoding="utf-8")
    tin = sum(x["in"] for x in usage_all if x); tout = sum(x["out"] for x in usage_all if x)
    (OUT / "usage.json").write_text(json.dumps({"model": MODEL, "calls": len(usage_all), "in": tin, "out": tout,
                                                "usd_at_10_50": tin * 10 / 1e6 + tout * 50 / 1e6}, indent=1), encoding="utf-8")
    print(f"tokens in {tin} out {tout}; at $10/$50 per M: ${tin * 10 / 1e6 + tout * 50 / 1e6:.2f}")


if __name__ == "__main__":
    main(tuple(sys.argv[1:]) or ("omsp_gpio", "tiny_aes"))
