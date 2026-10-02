"""Six-fix code writer, on gpt-6-astra, frozen before it meets the gold set.
 1. astra writes step1/code_pairs_v2.py (code_pairs(ent), same interface) from the current code, the definitions and the
    DEVELOPMENT set only: the 114 earlier adjudication keys (42 current-code errors with source excerpts, 72 regressions).
 2. dev self-test on those 114 keys; up to two astra repair rounds on the failures.
 3. FREEZE (sha of the file), then score on the held-out gold set (bakeoff/gold_final.json) against E3 x3, paired bootstrap.
 4. astra analyses the result.
Run: python codefix.py"""
import hashlib, json, os, random, re, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; os.chdir(ROOT)  # the repo root
sys.path.insert(0, str(ROOT / "step1")); sys.path.insert(0, str(ROOT / "assetgen_meta")); sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent; SP = HERE.parent; sys.path.insert(0, str(SP))
for l in (ROOT / "API.env").read_text(encoding="utf-8").splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k, v = l.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
import importlib, meta_tools as mt, astra_adjud as AA
import relation_stage as RS, relation_experiments as RX, lasset_step1 as S
from openai import OpenAI
client = OpenAI().with_options(timeout=120, max_retries=2)   # background mode: short requests only
OUT = ROOT / "step1" / "code_pairs_v2.py"
LOGD = HERE / "codefix"; LOGD.mkdir(exist_ok=True)
spent = 0.0


def ask(user, tag, max_out=48000):
    """Background-mode call: the request runs server-side and is polled, so a long reasoning phase cannot hit a client
    read timeout (the first attempt timed out three times at 30 minutes)."""
    import time
    global spent
    f = LOGD / f"{tag}.json"
    if f.exists():                                            # resume: never pay twice for a finished call
        A = json.loads(f.read_text(encoding="utf-8"))["answer"]; print(f"{tag}: cached", flush=True); return A
    r = client.responses.create(model="gpt-6-astra", instructions="You write correct, tested Python for hardware-analysis "
                                "tools. Return only the json object asked for.", input=user, reasoning={"effort": "high"},
                                max_output_tokens=max_out, text={"format": {"type": "json_object"}}, background=True)
    print(f"{tag}: submitted {r.id}", flush=True)
    t0 = time.time()
    while r.status in ("queued", "in_progress"):
        time.sleep(20)
        try:
            r = client.responses.retrieve(r.id)
        except Exception as e:                                # a failed poll is retried; the job keeps running
            print(f"   poll error {type(e).__name__}", flush=True)
    print(f"{tag}: {r.status} after {(time.time() - t0) / 60:.1f} min", flush=True)
    if r.status != "completed":
        raise RuntimeError(f"{tag}: {r.status} {getattr(r, 'incomplete_details', None)} {getattr(r, 'error', None)}")
    txt = r.output_text
    u = {"in": r.usage.input_tokens, "out": r.usage.output_tokens, "reasoning": r.usage.output_tokens_details.reasoning_tokens}
    A = mt.loads(txt); c = u["in"] * 10 / 1e6 + u["out"] * 50 / 1e6; spent += c
    (LOGD / f"{tag}.json").write_text(json.dumps({"usage": u, "answer": A}, indent=1), encoding="utf-8")
    print(f"{tag}: ~${c:.2f}", flush=True)
    return A


# ---------------------------------------------------------------- development set (earlier adjudication, NOT the gold)
rows = json.loads((SP / "adjud_scored.json").read_text(encoding="utf-8"))
items = {it["item"]: it for c in range(4) for it in json.loads((SP / f"adjud/chunk{c}.json").read_text(encoding="utf-8"))}
ents = {}
def ent(m, en):
    if (m, en) not in ents:
        for e in RS.load_module(m, RX.where(None)):
            ents[(m, e["entity"])] = e
    return ents[(m, en)]


def types_at(P, el, occ, target):
    out = set()
    for y, yi, x, xi, t in P:
        if y == el and yi == occ and x == target: out.add(t)
        if x == el and xi == occ and y == target: out.add(RS.MIRROR[t])
    return sorted(out)


def dev_test(fn):
    cache, res = {}, []
    for r in rows:
        m, en = "neorv32_" + r["module"], items[r["item"]]["entity"]
        if (m, en) not in cache:
            try:
                cache[(m, en)] = fn(ent(m, en))
            except Exception as e:
                cache[(m, en)] = e
        P = cache[(m, en)]
        got = f"ERROR {type(P).__name__}: {P}" if isinstance(P, Exception) else types_at(P, r["el"], r["occ"], r["target"])
        res.append({**{k: r[k] for k in ("item", "cls", "module", "el", "occ", "target", "truth", "note")},
                    "old": r["code"], "got": got, "ok": got == sorted(r["truth"])})
    return res


src = (ROOT / "step1/relation_stage.py").read_text(encoding="utf-8")
CURRENT = src[src.index("DRIVING = ("):src.index("PRICE =")] + "\n...\n" + \
    src[src.index("# ------------------------------------------------------------------ the table, implemented in code"):
        src.index("# ------------------------------------------------------------------ batching, messages")]
e0 = ent("neorv32_hwspinlock", "neorv32_hwspinlock")
SAMPLE = {"ent keys": sorted(e0), "ports (first 4)": e0["ports"][:4], "signals (first 4)": e0["signals"][:4],
          "src (first 25 lines, numbered, comments removed)": "\n".join(e0["src"].splitlines()[:25]),
          "_occs(ent) rows (8)": [{k: (sorted(v) if isinstance(v, set) else v) for k, v in o.items()} for o in RS._occs(e0)[:8]]}
base = dev_test(RS.code_pairs)
wrong = [r for r in base if not r["ok"]]
print(f"dev set, current code: {sum(r['ok'] for r in base)}/{len(base)} right", flush=True)


def case_text(r):
    return (json.dumps({k: r[k] for k in ("item", "module", "el", "occ", "target", "truth", "old", "note")}) +
            "\nEXCERPT:\n" + AA.excerpt(items[r["item"]]))


TASK = f"""Rewrite the deterministic relationship writer code_pairs(ent) of a VHDL analysis tool so that it follows the
definitions below exactly. It returns a set of (Y, y_occurrence_id, X, x_occurrence_id, DRIVING_TYPE) pairs, as now.

DEFINITIONS (sections 3, 4 and 8 of the specification the tool implements):
<<<
{AA.SPEC}
>>>

CURRENT CODE (module relation_stage.py; constants, helpers and code_pairs):
<<<
{CURRENT}
>>>

THE DATA (one real entity; ent["src"] lines are "<line number> | <text>", comments removed):
{json.dumps(SAMPLE, indent=1)[:9000]}

SIX KNOWN GAPS (all 42 current-code errors on a hand-adjudicated development set fall in them):
1. A statement over several lines: L4 pairs right-hand-side occurrences only with an assignment on the SAME line, so
   operands on continuation lines get no pair. Take the statement's extent from the source (from the target's "<=" to
   the terminating ";"), for signal assignments and when/else and with/select.
2. Several statements on one line ("a <= x; b <= y;"): the same-line rule pairs x with b. Pair only within one statement.
3. cond_type reads the whole line text, so "if (s = '0') then q <= R; else q <= T; end if;" sees q and "<=" and types
   a literal comparison as CONSTRAINS. Type a condition from the condition expression only (the if/elsif condition,
   the when condition, or the Path entry that names Y), splitting on top-level and/or.
4. The operand form of GATES demands the whole right-hand side be one flat operator (_flat_logic). The definition asks
   only that Y be a single-bit operand, bare or as not Y, of the TOP-LEVEL and/or/nand/nor of the right-hand side of a
   single-bit X; the other operands may be parenthesised sub-expressions. An operand inside a nested sub-expression
   is SOURCES.
5. A run-time index inside a condition: Y used as a run-time index (inside the parentheses of an indexed name) in X's
   condition is SELECTS (rule 7 and the priority), not CONSTRAINS/GATES.
6. Process variables are not followed: implement the PROCESS VARIABLES paragraph (elements read in a variable's
   assignment, and elements in conditions/selectors governing it, relate to each X whose assignment in the same
   process reads the variable; in a loop, every assignment to the variable in the body). Parse variables from the
   source of the enclosing process (ent["src"] and the process frame in Context). Where a condition of X's Path reads a
   variable, follow the development set's reading (item Q079: RHS forwarding only, not the condition).

DEVELOPMENT CASES the new code must get right (truth = the adjudicated types from the element's side at that
occurrence toward the target; old = current code). The 42 current errors, with source excerpts:
{chr(10).join(case_text(r) for r in wrong)}

REGRESSION CASES the current code already gets right (keep them right):
{json.dumps([{k: r[k] for k in ("module", "el", "occ", "target", "truth")} for r in base if r["ok"]])}

REQUIREMENTS: a complete Python module (standard library only) that does `from relation_stage import *` style imports
of what it needs (MIRROR, LHS, RHS, ADDON, SINGLE_BIT, _frames, _key, _occs, _rhs, _collapse_bits, _single_bit,
_names_re, _same_stmt, _edge_arms) and defines code_pairs(ent) -> set; deterministic; no I/O; never raises on odd
input (skip what it cannot parse). Keep every behaviour the definitions and the regression cases need.
Return one json object: {{"code": "<the module source>", "notes": ["<one line per fix: what it does>"]}}"""

FIX = """The module you wrote fails these development cases (got = your output). Return the corrected complete module as
{{"code": "...", "notes": ["..."]}}; keep everything that works.
FAILURES:
{fails}
YOUR MODULE:
<<<
{code}
>>>"""


def load_fn(code):
    OUT.write_text(code, encoding="utf-8")
    import code_pairs_v2 as V
    importlib.reload(V)
    return V.code_pairs


A = ask(TASK, "gen")
code = A["code"]; res = None
for rnd in range(3):
    try:
        fn = load_fn(code); res = dev_test(fn)
        ok = sum(r["ok"] for r in res)
        print(f"dev round {rnd}: {ok}/{len(res)} right (current code {sum(r['ok'] for r in base)}); "
              f"regressions {sum(1 for a, b in zip(base, res) if a['ok'] and not b['ok'])}", flush=True)
        fails = [r for r in res if not r["ok"]]
    except Exception as e:
        fails = [{"error": f"import failed: {type(e).__name__}: {e}"}]; print("import failed:", e, flush=True)
    if not fails or rnd == 2:
        break
    ft = "\n\n".join((case_text({**r, "old": r["old"]}) + f"\nGOT: {r['got']}") if "item" in r else json.dumps(r) for r in fails[:30])
    code = ask(FIX.format(fails=ft, code=code), f"fix{rnd + 1}")["code"]

# ---------------------------------------------------------------- FREEZE, then the held-out gold set
fn = load_fn(code)
sha = hashlib.sha256(OUT.read_bytes()).hexdigest()[:12]
dev = dev_test(fn)
print(f"FROZEN step1/code_pairs_v2.py sha {sha}; dev {sum(r['ok'] for r in dev)}/{len(dev)} "
      f"(current code {sum(r['ok'] for r in base)}/{len(base)})", flush=True)
(LOGD / "dev_result.json").write_text(json.dumps({"sha": sha, "dev": dev}, indent=1), encoding="utf-8")

B = HERE
G = json.loads((B / "gold_items.json").read_text(encoding="utf-8")); gitems, POP = G["items"], G["population"]
gold = json.loads((B / "gold_final.json").read_text(encoding="utf-8"))
n_g = Counter(it["group"] for it in gitems); W = {g: POP[g] / n_g[g] for g in n_g}
key = {it["item"]: (it["module"], it["entity"], it["element"]["name"], it["occurrence"]["id"]) for it in gitems}
truth = {it["item"]: {(r["type"], r["target"]) for r in (gold[it["item"]] or {}).get("records", [])} for it in gitems}
need = {(it["module"], it["entity"]) for it in gitems}


def at_occ(pairs_fn):
    out = defaultdict(set)
    for m, en in need:
        for y, yi, x, xi, t in pairs_fn(ent(m, en)):
            out[(m, en, y, yi)].add((t, x)); out[(m, en, x, xi)].add((RS.MIRROR[t], y))
    return out


def at_occ_llm(w, prompt):
    out = defaultdict(set); ps = RX.psha(prompt)
    for m in sorted({m for m, _ in need}):
        for en, rs in RS.check(m, psha=ps, where=w, log=lambda *a: None)["records"].items():
            for n, a, t, x, _b in rs:
                out[(m, en, n, a)].add((t, x))
    return out


rec = {"code (current)": at_occ(RS.code_pairs), "code (fixed)": at_occ(fn),
       "E3 r1": at_occ_llm(RX.where("E3_pairfirst_declaration"), RX.PROMPT_V2),
       "E3 r2": at_occ_llm(RX.where("E3_rep2"), RX.PROMPT_V2), "E3 r3": at_occ_llm(RX.where("E3_rep3"), RX.PROMPT_V2)}
IDS = [it["item"] for it in gitems]; GRP = {it["item"]: it["group"] for it in gitems}


def pr(r, ids, typed=True):
    tp = fp = fn_ = 0.0
    for i in ids:
        s, t = r.get(key[i], set()), truth[i]
        if not typed: s, t = {x for _, x in s}, {x for _, x in t}
        w = W[GRP[i]]; tp += w * len(s & t); fp += w * len(s - t); fn_ += w * len(t - s)
    return (tp / (tp + fp) if tp + fp else float("nan"), tp / (tp + fn_) if tp + fn_ else float("nan"))


strata = defaultdict(list)
for i in IDS: strata[GRP[i]].append(i)
rng = random.Random(7)
boots = [[rng.choice(v) for v in strata.values() for _ in v] for _ in range(1000)]
ci = lambda v: (lambda s: [round(s[int(.025 * len(s))], 3), round(s[int(.975 * len(s)) - 1], 3)])(sorted(v))
table = {}
for name, r in rec.items():
    p, rc = pr(r, IDS); pu, ru = pr(r, IDS, False); bp = [pr(r, b) for b in boots]
    table[name] = {"precision": round(p, 3), "precision_ci": ci([x[0] for x in bp]), "recall": round(rc, 3),
                   "recall_ci": ci([x[1] for x in bp]), "target_only": [round(pu, 3), round(ru, 3)]}
    print(f"{name:15s} typed P {p:.3f} {table[name]['precision_ci']}  R {rc:.3f} {table[name]['recall_ci']}  | target-only P {pu:.3f} R {ru:.3f}", flush=True)
diff = {}
for metric, j in (("precision", 0), ("recall", 1)):
    d = [pr(rec["code (fixed)"], b)[j] - sum(pr(rec[f"E3 r{k}"], b)[j] for k in (1, 2, 3)) / 3 for b in [IDS] + boots]
    diff[metric] = {"fixed code minus E3 (mean of 3 runs)": round(d[0], 3), "ci": ci(d[1:])}
print("paired:", diff, flush=True)
per_group = {g: {n: dict(zip(("P", "R"), [round(x, 3) for x in pr(r, ids)])) for n, r in rec.items()} for g, ids in strata.items()}
out = {"frozen_sha": sha, "dev": {"fixed": sum(r["ok"] for r in dev), "current": sum(r["ok"] for r in base), "n": len(dev)},
       "table": table, "paired": diff, "per_group": per_group}
(LOGD / "gold_result.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

ANA = f"""A deterministic code writer of VHDL relationship records (typed pairs) was fixed for six known parse gaps on a
development set of 114 hand-adjudicated keys, frozen (sha recorded), then scored on a separate held-out gold set of 120
occurrences (records listed blind by gpt-6-astra, two passes agreed 117/120) against the best LLM writer (E3, gpt-5-mini,
3 runs). Precision/recall of typed records per occurrence, weighted by stratum, 95% bootstrap intervals; paired =
fixed code minus the E3 mean. Earlier on the same gold: E0 (older prompt) precision about 0.93, recall about 0.83.
RESULTS: {json.dumps(out, indent=1)}
Answer from the results, label inference, each answer at most 90 words.
Q1 Does the fixed code beat, match or trail E3 on precision and recall (paired intervals)?
Q2 Which writer should produce the relationship records, and why (accuracy, determinism, cost, traceability)?
Q3 What errors remain in the winner (strata, typed vs target-only), and are they worth fixing?
Q4 Any sign the dev loop overfit (dev vs gold), or other threat to the conclusion?
Return one json object {{"q1": "...", "q2": "...", "q3": "...", "q4": "...", "writer": "code | llm | hybrid | undecided", "confidence": "low | medium | high"}}"""
V = ask(ANA, "analysis", 12000)
print(json.dumps(V, indent=1))
print(f"astra total this script ~${spent:.2f}")
