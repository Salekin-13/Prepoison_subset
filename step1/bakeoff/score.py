"""Bake-off scoring against the astra gold set: typed records (type, target) at each sampled occurrence, for the current
code reference, E0 x3 and E3 x3. Precision/recall weighted by stratum (population / sample), 95% bootstrap intervals
(resampling items within strata), the paired E3-E0 difference, then the analysis by gpt-6-astra.
  python score.py          (needs gold_final.json and the replicate folders)"""
import json, os, random, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; os.chdir(ROOT)  # the repo root
sys.path.insert(0, str(ROOT / "step1")); sys.path.insert(0, str(ROOT / "assetgen_meta")); sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent; SP = HERE.parent; sys.path.insert(0, str(SP))
import relation_stage as RS, relation_experiments as RX, lasset_step1 as S
noop = lambda *a: None

G = json.loads((HERE / "gold_items.json").read_text(encoding="utf-8"))
items, POP, ALLOC = G["items"], G["population"], G["alloc"]
gold = json.loads((HERE / "gold_final.json").read_text(encoding="utf-8"))
n_g = Counter(it["group"] for it in items)
W = {g: POP[g] / n_g[g] for g in n_g}
SYSTEMS = {"E0 r1": (RX.where(None), RX.PROMPT_V1), "E0 r2": (RX.where("E0_rep2"), RX.PROMPT_V1),
           "E0 r3": (RX.where("E0_rep3"), RX.PROMPT_V1), "E3 r1": (RX.where("E3_pairfirst_declaration"), RX.PROMPT_V2),
           "E3 r2": (RX.where("E3_rep2"), RX.PROMPT_V2), "E3 r3": (RX.where("E3_rep3"), RX.PROMPT_V2)}
need = {(it["module"], it["entity"]) for it in items}
mods = sorted({m for m, _ in need})


def at_occ_llm(w, prompt):
    out = defaultdict(set); ps = RX.psha(prompt)
    for m in mods:
        res = RS.check(m, psha=ps, where=w, log=noop)
        for en, rs in res["records"].items():
            for n, a, t, x, _b in rs:
                out[(m, en, n, a)].add((t, x))
    return out


def at_occ_code():
    out = defaultdict(set)
    for m in mods:
        for e in RS.load_module(m, RX.where(None)):
            if (m, e["entity"]) not in need:
                continue
            for y, yi, x, xi, t in RS.code_pairs(e):
                out[(m, e["entity"], y, yi)].add((t, x)); out[(m, e["entity"], x, xi)].add((RS.MIRROR[t], y))
    return out


rec = {"code (current)": at_occ_code()}
for k, (w, p) in SYSTEMS.items():
    rec[k] = at_occ_llm(w, p)
truth = {it["item"]: {(r["type"], r["target"]) for r in (gold[it["item"]] or {}).get("records", [])} for it in items}
key = {it["item"]: (it["module"], it["entity"], it["element"]["name"], it["occurrence"]["id"]) for it in items}


def counts(sysrec, ids, typed=True):
    tp = fp = fn = 0.0
    for i in ids:
        it = next(x for x in items if x["item"] == i) if False else None
        g = BYID[i]["group"]; w = W[g]
        s, t = sysrec.get(key[i], set()), truth[i]
        if not typed:
            s, t = {x for _, x in s}, {x for _, x in t}
        tp += w * len(s & t); fp += w * len(s - t); fn += w * len(t - s)
    return tp, fp, fn


BYID = {it["item"]: it for it in items}
IDS = list(BYID)


def pr(sysrec, ids, typed=True):
    tp, fp, fn = counts(sysrec, ids, typed)
    return (tp / (tp + fp) if tp + fp else float("nan"), tp / (tp + fn) if tp + fn else float("nan"))


_self = pr({key[i]: truth[i] for i in IDS}, IDS)              # self-test: the gold scored against itself
assert _self == (1.0, 1.0) or not any(truth.values()), _self
_drop = {key[i]: set(list(truth[i])[:-1]) for i in IDS}       # one record fewer per item: precision 1, recall < 1
assert pr(_drop, IDS)[0] == 1.0 and pr(_drop, IDS)[1] < 1.0
print("scorer self-test PASS")
strata = defaultdict(list)
for i in IDS:
    strata[BYID[i]["group"]].append(i)
rnd = random.Random(7)
boots = [[rnd.choice(v) for v in strata.values() for _ in v] for _ in range(1000)]


def ci(vals):
    v = sorted(x for x in vals if x == x)
    return (v[int(.025 * len(v))], v[int(.975 * len(v)) - 1]) if v else (float("nan"),) * 2


table = {}
for name, r in rec.items():
    p, rc = pr(r, IDS); pu, ru = pr(r, IDS, typed=False)
    bp = [pr(r, b) for b in boots]
    table[name] = {"precision": round(p, 3), "recall": round(rc, 3),
                   "precision_ci": [round(x, 3) for x in ci([x[0] for x in bp])],
                   "recall_ci": [round(x, 3) for x in ci([x[1] for x in bp])],
                   "untyped_precision": round(pu, 3), "untyped_recall": round(ru, 3)}
    print(f"{name:15s} typed P {p:.3f} {table[name]['precision_ci']}  R {rc:.3f} {table[name]['recall_ci']}  | target-only P {pu:.3f} R {ru:.3f}")


def mean_arm(arm):
    return {i: None for i in IDS}, [rec[f"{arm} r{k}"] for k in (1, 2, 3)]


diff = {}
for metric, idx in (("precision", 0), ("recall", 1)):
    d = []
    for b in [IDS] + boots:
        e0 = sum(pr(rec[f"E0 r{k}"], b)[idx] for k in (1, 2, 3)) / 3
        e3 = sum(pr(rec[f"E3 r{k}"], b)[idx] for k in (1, 2, 3)) / 3
        d.append(e3 - e0)
    diff[metric] = {"E3 minus E0 (mean of 3 runs)": round(d[0], 3), "ci": [round(x, 3) for x in ci(d[1:])]}
print("paired difference:", diff)
per_group = {}
for g, ids in strata.items():
    per_group[g] = {name: {"P": round(pr(r, ids)[0], 3), "R": round(pr(r, ids)[1], 3)} for name, r in rec.items()}
    per_group[g]["gold records"] = sum(len(truth[i]) for i in ids)
jud = (HERE / "judge.log").read_text(encoding="utf-8")
agree_line = next((l for l in jud.splitlines() if l.startswith("judge agreement")), "")
flags = {"site_wrong": sum(1 for i in IDS if gold[i] and not gold[i].get("site_ok", True)),
         "spec_ambiguous": sum(1 for i in IDS if gold[i] and gold[i].get("spec_ambiguous"))}
out = {"table": table, "paired_difference": diff, "per_group": per_group, "population": POP, "sample": dict(n_g),
       "gold_records": sum(len(v) for v in truth.values()), "judges": agree_line, "gold_flags": flags}
(HERE / "score.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(agree_line, "| gold records", out["gold_records"], "| flags", flags)

# ---- the analysis, on astra
from openai import OpenAI
import meta_tools as mt
for l in (ROOT / "API.env").read_text(encoding="utf-8").splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k, v = l.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
ASK = f"""A head-to-head test of three ways to write relationship records between the ports and signals of VHDL entities
(driving record at Y's occurrence, receiving record at X's assignment, 14 types): the current deterministic code
reference (known to have six parse gaps: multi-line statements, several statements on one line, condition typed from
the whole line, operand-GATES test too strict, run-time index in a condition, process variables not followed), and an
LLM (gpt-5-mini) with prompt v1 (E0) or prompt v2 (E3, two-pass pair-first + contrastive examples), 3 runs each.
Gold: a stratified sample of 120 occurrences from 15 modules (held out from the earlier adjudication and from any code
fix), for which gpt-6-astra listed every record from the RTL and the definitions, blind to all systems (two passes, a
third call on splits). Scores: typed records (type, target) at each sampled occurrence; precision/recall weighted by
stratum (population / sample); 95% bootstrap intervals; "target-only" ignores the type.
RESULTS (json):
{json.dumps(out, indent=1)}
Answer from the results; label inference. Each answer at most 110 words.
Q1 Which system is most accurate, on precision and on recall, and which differences are beyond the intervals?
Q2 Is E3 better than E0 on true accuracy (paired difference)? Adopt, reject or inconclusive.
Q3 Where does each system fail (per stratum; typed vs target-only)? What does that say about the code's six gaps and
   the LLM's omission problem?
Q4 Should relationships be written by code (after the six fixes) or by the LLM? What would a fixed code need to reach
   on this gold set to settle it, and which strata must it fix first?
Q5 How trustworthy is the gold set (judge agreement, flags, stratum sizes), and what limits the conclusions?
Q6 One concrete next step.
Return one json object {{"q1": "...", "q2": "...", "q3": "...", "q4": "...", "q5": "...", "q6": "...",
"verdicts": {{"E3_vs_E0": "adopt | reject | inconclusive", "writer": "code | llm | undecided"}}, "confidence": "low | medium | high"}}"""
client = OpenAI().with_options(timeout=1500, max_retries=0)
txt, u, st = mt.call_text(client, "gpt-6-astra", "You are a careful ML evaluation analyst. Return only the json object.",
                          ASK, "high", 16000, retries=3, json_mode=True)
A = mt.loads(txt)
(HERE / "astra_bakeoff.json").write_text(json.dumps({"usage": u, "answer": A}, indent=1), encoding="utf-8")
print(f"\nastra ~${u['in'] * 10 / 1e6 + u['out'] * 50 / 1e6:.2f}")
print(json.dumps(A, indent=1))
