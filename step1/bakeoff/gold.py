"""Bake-off gold set: a stratified sample of occurrences (15 test modules, none from the earlier 114-key adjudication),
for each of which gpt-6-astra lists EVERY relationship record the occurrence carries, from the RTL and the definitions,
blind to all systems. Two independent passes (items in opposite order); a third call settles every split.
  python gold.py build   -> sample + items (no API)
  python gold.py judge   -> judges + resolve (astra)"""
import json, os, random, re, sys, concurrent.futures as cf
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; os.chdir(ROOT)  # the repo root
sys.path.insert(0, str(ROOT / "step1")); sys.path.insert(0, str(ROOT / "assetgen_meta")); sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent; SP = HERE.parent
sys.path.insert(0, str(SP))
import astra_adjud as AA                      # SPEC (sections 3, 4, 8 of relation prompt v1) and call()
import relation_stage as RS, relation_experiments as RX, lasset_step1 as S

GROUPS = {"LHS": {"LHS_PROC", "LHS_CONC"}, "EDGE": {"EDGE_CHECK"}, "IF": {"IF_COND"}, "WHEN": {"WHEN_COND"},
          "CASE": {"CASE_EXPR"}, "RHS": {"DIRR_ASS", "RHS_OPERAND", "WHEN_EXPR", "INDEX", "INDEXED_NAME", "PART_SELECT",
                                         "VAR_RHS_OPERAND"}}
ALLOC = {"LHS": 34, "RHS": 30, "IF": 18, "WHEN": 10, "CASE": 10, "EDGE": 8, "OTHER": 10}
TYPES = sorted(RS.DRIVING + RS.RECEIVING)


def group(sites):
    for g, s in GROUPS.items():
        if sites & s:
            return g
    return "OTHER"


def src_map(ent):
    return {int(a): b for a, _, b in (l.partition("|") for l in ent["src"].splitlines()) if a.strip().isdigit()}


def excerpt(o, L, cap=180):
    fr = [f for f in o["fr"] if not f[0].startswith(("architecture", "entity"))]
    ln = int(str(o["line"]).split("-")[0])
    keep = set(range(ln - 10, ln + 11))
    for _k, a, b in fr:
        keep |= {a, b}
    if fr and fr[0][2] - fr[0][1] <= 90:
        keep |= set(range(fr[0][1], fr[0][2] + 1))
    if fr and fr[-1][2] - fr[-1][1] <= 130:
        keep |= set(range(fr[-1][1], fr[-1][2] + 1))
    elif fr:
        keep |= {a for a in range(fr[-1][1], fr[-1][2] + 1) if re.search(r":=|\bvariable\b", L.get(a, ""), re.I)}
    ks = sorted(k for k in keep if k in L)
    if len(ks) > cap:
        core = set(range(ln - 10, ln + 11)) | {x for _k, a, b in fr for x in (a, b)}
        if fr and fr[0][2] - fr[0][1] <= 90:
            core |= set(range(fr[0][1], fr[0][2] + 1))
        ks = sorted(k for k in core if k in L)
    rows, prev = [], None
    for a in ks:
        if prev is not None and a != prev + 1:
            rows.append("   ...")
        rows.append(f"{a:5d} |{L[a]}"); prev = a
    return "\n".join(rows), ks


def build():
    old = {(k["module"], k["entity"], k["el"], k["occ"]) for k in json.loads((SP / "adjud_key.json").read_text(encoding="utf-8"))}
    pop = defaultdict(list); ents = {}
    for m in S.test_modules():
        for e in RS.load_module(m, RX.where(None)):
            ents[(m, e["entity"])] = e
            for o in RS._occs(e):
                if (m, e["entity"], o["el"], o["id"]) not in old:
                    pop[group(o["sites"])].append((m, e["entity"], o["el"], o["id"]))
    rnd = random.Random(20260930)
    items, sizes = [], {g: len(v) for g, v in pop.items()}
    for g, n in ALLOC.items():
        for m, en, el, oid in rnd.sample(sorted(pop[g]), min(n, len(pop[g]))):
            e = ents[(m, en)]; L = src_map(e)
            o = next(x for x in RS._occs(e) if x["el"] == el and x["id"] == oid)
            text, ks = excerpt(o, L)
            shown = "\n".join(L[k] for k in ks)
            decl = {x["name"]: x for x in e["ports"] + e["signals"]}
            near = sorted(n for n in decl if re.search(rf"(?<![\w.]){re.escape(n)}(?![\w])", shown, re.I))
            r = next(r for r in e["profile"][el] if r["Occurrence ID"] == oid)
            items.append({"item": f"G{len(items):03d}", "group": g, "module": m, "entity": en,
                          "element": {"name": el, "dir": decl[el].get("dir"), "type": decl[el].get("type")},
                          "occurrence": {"id": oid, "line": r["Occurrence Lines"], "text": r["Line Text"],
                                         "SITE": r["SITE Tagged"], "Context": r.get("Context"), "Path": r.get("Path") or []},
                          "elements_in_excerpt": [{"name": n, "dir": decl[n].get("dir"), "type": decl[n].get("type")} for n in near],
                          "excerpt": text})
    rnd.shuffle(items)
    for i, it in enumerate(items):
        it["item"] = f"G{i:03d}"
    (HERE / "gold_items.json").write_text(json.dumps({"population": sizes, "alloc": ALLOC, "items": items}, indent=1), encoding="utf-8")
    print("population by group:", sizes); print("sampled:", Counter(i["group"] for i in items), "total", len(items))
    print("excerpt lines: max", max(i["excerpt"].count("\n") + 1 for i in items), "| items with no element in excerpt besides itself:",
          sum(len(i["elements_in_excerpt"]) <= 1 for i in items))


RULES = f"""You are an SoC hardware engineer building a reference answer key for relationship records in VHDL. The definitions
below are the standard.

DEFINITIONS (section 3: the relationship pairs, type rules 1-10, process variables; section 4: linking rules L1-L5 and
the SITE table; section 8: worked examples):
<<<
{AA.SPEC}
>>>

Each item gives ONE occurrence of an ELEMENT (Occurrence ID, line, line text, SITE tags, Context = enclosing constructs
innermost first with line spans, Path = conditions that must hold), the elements whose names appear in the excerpt, and
a numbered source excerpt ("..." marks skipped lines).

For each item list EVERY relationship record this one occurrence carries under the definitions, as {{type, target}}:
- If this occurrence is an assignment of the element (the element is the target of <= in that statement), list its
  receiving records: COPIES, DERIVES_FROM, CLOCKED_BY, RESET_BY, SELECTED_BY, CONSTRAINED_BY, GATED_BY, one per element
  that relates to this assignment (by its statement, its Path conditions and selectors, and process variables it reads).
- Otherwise list its driving records: CARRIES, SOURCES, SEQUENCES, RESETS, SELECTS, CONSTRAINS, GATES, one per element
  whose assignment this occurrence relates to (a condition or selector: every element assigned under it, by L1-L3,
  rule 3 and the negation rule; a right-hand-side occurrence: the target of its statement).
- target: an element name exactly as in elements_in_excerpt (a record field by its dotted name, never its base when
  the field is meant). Several records with the same target only when different occurrences of it take different types.
- An empty list when the occurrence carries no record (declarations, attribute prefixes, association actuals, process
  sensitivity lists, literals-only conditions over generics or constants).
SITE tags, Context and Path come from an automated step: hints only; decide from the source. site_ok false if a SITE tag
is wrong (name the right one in note). spec_ambiguous true only if the definitions genuinely allow two readings (give
your best reading, name both in note). note: at most 30 words. If the excerpt lacks a line you need, say so in note.

Return one json object: {{"verdicts": [{{"item": "G000", "records": [{{"type": "...", "target": "..."}}], "site_ok": true,
"spec_ambiguous": false, "note": "..."}}]}}, one verdict per item, types only from {TYPES}."""


def item_text(it):
    return json.dumps({k: it[k] for k in ("item", "element", "occurrence", "elements_in_excerpt")}, indent=0) + \
        "\nSOURCE EXCERPT (numbered, comments removed):\n" + it["excerpt"]


def key(v):
    return tuple(sorted((r["type"], r["target"]) for r in (v or {}).get("records", [])))


def judge():
    G = json.loads((HERE / "gold_items.json").read_text(encoding="utf-8"))["items"]
    chunks = [G[i::6] for i in range(6)]
    out = HERE / "gold_astra"; out.mkdir(exist_ok=True)
    AA.SP = HERE; (HERE / "astra_adjud").mkdir(exist_ok=True)      # AA.call writes <SP>/astra_adjud/<tag>.json
    jobs = {}
    for c, ch in enumerate(chunks):
        for j, order in (("A", ch), ("B", list(reversed(ch)))):
            tag = f"gold_chunk{c}{j}"
            if not (HERE / "astra_adjud" / f"{tag}.json").exists():
                jobs[tag] = RULES + "\n\nITEMS:\n\n" + "\n\n----\n\n".join(item_text(it) for it in order)
    cost = 0.0
    with cf.ThreadPoolExecutor(12) as ex:
        for tag, A, u in ex.map(lambda kv: AA.call(kv[1], kv[0]), jobs.items()):
            c = u["in"] * 10 / 1e6 + u["out"] * 50 / 1e6; cost += c
            print(f"{tag}: {len(A.get('verdicts', []))} verdicts, ~${c:.2f}", flush=True)
    load = lambda t: {v["item"]: v for v in json.loads((HERE / "astra_adjud" / f"{t}.json").read_text(encoding="utf-8"))["answer"].get("verdicts", [])}
    a = {k: v for c in range(6) for k, v in load(f"gold_chunk{c}A").items()}
    b = {k: v for c in range(6) for k, v in load(f"gold_chunk{c}B").items()}
    byid = {it["item"]: it for it in G}
    splits = [i for i in byid if key(a.get(i)) != key(b.get(i)) or i not in a or i not in b]
    print(f"judge agreement: {len(byid) - len(splits)} of {len(byid)} items identical; splits {len(splits)}", flush=True)
    res = {}
    parts = [splits[i:i + 20] for i in range(0, len(splits), 20)]
    rjobs = {}
    for p, ids in enumerate(parts):
        tag = f"gold_resolve{p}"
        if not (HERE / "astra_adjud" / f"{tag}.json").exists():
            rjobs[tag] = (RULES + "\n\nTwo independent judges disagreed on the items below; their answers follow each item. "
                          "Either may be wrong, or both. Re-derive each item from the excerpt and the definitions and return "
                          "your final verdict for exactly these items.\n\n" +
                          "\n\n====\n\n".join(item_text(byid[i]) + "\nJUDGE 1: " + json.dumps(a.get(i)) + "\nJUDGE 2: " +
                                              json.dumps(b.get(i)) for i in ids))
    with cf.ThreadPoolExecutor(6) as ex:
        for tag, A, u in ex.map(lambda kv: AA.call(kv[1], kv[0]), rjobs.items()):
            c = u["in"] * 10 / 1e6 + u["out"] * 50 / 1e6; cost += c
            print(f"{tag}: {len(A.get('verdicts', []))} verdicts, ~${c:.2f}", flush=True)
    for p in range(len(parts)):
        res.update(load(f"gold_resolve{p}"))
    final = {i: (res.get(i) if i in splits else a[i]) for i in byid}
    miss = [i for i, v in final.items() if v is None]
    (HERE / "gold_final.json").write_text(json.dumps(final, indent=0), encoding="utf-8")
    print(f"astra this run ~${cost:.2f}; final verdicts {len(final) - len(miss)}, missing {miss}")


if __name__ == "__main__":
    {"build": build, "judge": judge}[sys.argv[1]]()
