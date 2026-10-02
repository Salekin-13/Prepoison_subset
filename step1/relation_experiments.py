"""Relation-annotator experiments on the 15 test modules (Step 1). One change per experiment; each writes its own folder.

  E0  baseline     prompt v1 (a44eebd83bf7), declaration-order batches          step1/lasset_step1/relation_out, relation_map
  E1  noise floor  E0 again, unchanged, on neorv32_cache, neorv32_spi, neorv32_uart
  E2  batching     prompt v1, batches that keep linked elements together (relation_stage.linked_batches)
  E3  prompt       prompt v2 (8406f390b729: two-pass pair-first section 7, examples E-G), batching chosen after E2
  E4  repair       one call per batch holding an unpartnered record, shown next to the other call's record; on the
                   best of E0/E2/E3

Log: step1/lasset_step1/RELATION_EXPERIMENTS_LOG.md -- the numbers are appended by log_entry(); the analysis is added
after each run.
"""
from __future__ import annotations

import datetime as dt, json, re, shutil, sys, time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lasset_step1 as S
import relation_stage as RS

EXP = S.OUT_ROOT / "relation_exp"
LOG = S.OUT_ROOT / "RELATION_EXPERIMENTS_LOG.md"
PROMPT_V1 = RS.PROMPT_FILE
PROMPT_V2 = RS.PACK / "relation_prompts_v2" / "relation_system_prompt.md"
NOISE_MODULES = ["neorv32_cache", "neorv32_spi", "neorv32_uart"]


def where(exp: str | None) -> dict:
    """The folders of an experiment; None is the E0 baseline."""
    if exp is None:
        return S.WHERE
    return {**S.WHERE, "out": EXP / exp / "relation_out", "map": EXP / exp / "relation_map"}


def psha(prompt_file) -> str:
    return RS._sha(Path(prompt_file).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ metrics
def summarize(modules, w, prompt_file=PROMPT_V1) -> dict:
    """Everything the log records for one run, from the saved answers (no call). Exact counts."""
    ps = psha(prompt_file)
    t = Counter()
    per = {}
    for m in modules:
        ents = {e["entity"]: e for e in RS.load_module(m, w)}
        answers = RS._answers(m, ps, w["out"])
        if not answers:
            continue
        r = RS.check(m, psha=ps, answers=answers, ents=list(ents.values()), log=lambda *a: None, where=w)
        batch_of = {(ent, n): b for (ent, b), (rec, _a) in answers.items() for n in rec["names"]}
        c = Counter()
        for (ent, b), (rec, _a) in answers.items():
            u = rec.get("usage") or {}
            c["calls"] += 1; c["in"] += u.get("in", 0); c["out"] += u.get("out", 0)
        for ent, rs in r["records"].items():
            # the headline (astra review of E1/E2): an expected occurrence pair counts only when BOTH records exist,
            # with the reference's type and its mirror. Precision: of the driving records whose mirror exists, the
            # share that match an expected pair. The reference's CONSTRAINS / operand-GATES typing is approximate.
            recs = {(n, a, tt, x) for n, a, tt, x, _b in rs}
            ref_occ = RS.code_pairs(ents[ent])
            for y, yi, x, xi, tt in ref_occ:
                c["expected pairs"] += 1
                c["mirrored pairs found"] += (y, yi, tt, x) in recs and (x, xi, RS.MIRROR[tt], y) in recs
            ref_drv = {(y, yi, tt, x) for y, yi, x, _xi, tt in ref_occ}
            has_mirror = {(n, x, tt) for n, _a, tt, x in recs if tt in RS.RECEIVING}
            mirrored_drv = [(n, a, tt, x) for n, a, tt, x in recs if tt in RS.DRIVING and (x, n, RS.MIRROR[tt]) in has_mirror]
            c["model mirrored driving"] += len(mirrored_drv)
            c["model mirrored driving in reference"] += sum(r_ in ref_drv for r_ in mirrored_drv)
            ref = {(y, x) for y, _yi, x, _xi, _t in RS.code_pairs(ents[ent]) if y != x}
            for y, x in ref:
                c["ref pairs"] += 1
                c["ref pairs in one call"] += batch_of.get((ent, y)) == batch_of.get((ent, x))
            have = {(n, tt, x) for n, _a, tt, x, _b in rs}
            by_pair = defaultdict(set)
            for n, _a, tt, x, _b in rs:
                by_pair[(n, x)].add(tt)
            for n, a, tt, x, _b in rs:
                c["records"] += 1
                if (x, RS.MIRROR[tt], n) in have:
                    continue
                pair = (n, x) if tt in RS.DRIVING else (x, n)
                k = "type disagreement" if by_pair.get((x, n)) else ("omission" if pair in {(y, x2) for y, x2 in ref}
                                                                     else "wrong side")
                c[k] += 1
        for k, v in r["agreement"].items():
            c[k] += v
        c["check failures"] += sum(r["issues"].values())
        for k, v in r["issues"].items():
            c["fail: " + k] += v
        per[m] = c
        t.update(c)
    t["usd_upper"] = round(t["in"] * RS.PRICE["in"] + t["out"] * RS.PRICE["out"], 4)
    return {"total": t, "per_module": per, "prompt_sha": ps}


def rates(t) -> dict:
    """The headline figures, with their denominators."""
    f = lambda a, b: (a / b) if b else 0.0
    unp = t["omission"] + t["type disagreement"] + t["wrong side"]
    return {"mirrored_recall": f(t["mirrored pairs found"], t["expected pairs"]),
            "mirrored_precision": f(t["model mirrored driving in reference"], t["model mirrored driving"]),
            "records": t["records"], "unpartnered": unp, "unpartnered_rate": f(unp, t["records"]),
            "omission": t["omission"], "type disagreement": t["type disagreement"], "wrong side": t["wrong side"],
            "pair_recall": f(t["both"], t["reference pairs"]), "pair_precision": f(t["both"], t["model pairs"]),
            "typed_recall": f(t["records both"], t["reference records"]),
            "typed_precision": f(t["records both"], t["model records"]),
            "pairs_in_one_call": f(t["ref pairs in one call"], t["ref pairs"]),
            "check_failures": t["check failures"], "calls": t["calls"], "usd_upper": t["usd_upper"]}


def show(label, s, log=print):
    r = rates(s["total"])
    log(f"   {label}: MIRRORED TYPED PAIRS recall {r['mirrored_recall']:.1%} precision {r['mirrored_precision']:.1%}; "
        f"records {r['records']}, unpartnered {r['unpartnered']} ({r['unpartnered_rate']:.1%}: omission "
        f"{r['omission']}, type disagreement {r['type disagreement']}, wrong side {r['wrong side']}); element pairs "
        f"R {r['pair_recall']:.1%} P {r['pair_precision']:.1%}; typed R {r['typed_recall']:.1%} P "
        f"{r['typed_precision']:.1%}; pairs in one call {r['pairs_in_one_call']:.0%}; check failures "
        f"{r['check_failures']}; {r['calls']} calls, at most ${r['usd_upper']:.2f}")
    return r


def compare_runs(modules, w_a, w_b, prompt_a=PROMPT_V1, prompt_b=PROMPT_V1) -> dict:
    """Two runs on the same modules: how many records (element, occurrence, type, target) and element pairs differ."""
    out = Counter()
    for m in modules:
        ra = RS.check(m, psha=psha(prompt_a), where=w_a, log=lambda *a: None)
        rb = RS.check(m, psha=psha(prompt_b), where=w_b, log=lambda *a: None)
        for ent in set(ra["records"]) | set(rb["records"]):
            A = {(n, a, t, x) for n, a, t, x, _b in ra["records"].get(ent, [])}
            B = {(n, a, t, x) for n, a, t, x, _b in rb["records"].get(ent, [])}
            out["records a"] += len(A); out["records b"] += len(B); out["records both"] += len(A & B)
            pa = {(n, x) if t in RS.DRIVING else (x, n) for n, _a, t, x in A}
            pb = {(n, x) if t in RS.DRIVING else (x, n) for n, _a, t, x in B}
            out["pairs a"] += len(pa); out["pairs b"] += len(pb); out["pairs both"] += len(pa & pb)
    out["records differing"] = out["records a"] + out["records b"] - 2 * out["records both"]
    out["pairs differing"] = out["pairs a"] + out["pairs b"] - 2 * out["pairs both"]
    return dict(out)


# ------------------------------------------------------------------ E4: the repair pass
def repair_items(module, w, prompt_file) -> dict:
    """{(entity, element): [item lines]} for every record without a mirrored partner, given to BOTH sides' batches."""
    ps = psha(prompt_file)
    r = RS.check(module, psha=ps, where=w, log=lambda *a: None)
    ents = {e["entity"]: e for e in RS.load_module(module, w)}
    items = defaultdict(list)
    for ent, rs in r["records"].items():
        occ = {(o["el"], o["id"]): o for o in RS._occs(ents[ent])}
        have = {(n, t, x) for n, _a, t, x, _b in rs}
        written = defaultdict(list)
        for n, a, t, x, _b in rs:
            written[(n, x)].append((t, a))
        for n, a, t, x, _b in rs:
            if (x, RS.MIRROR[t], n) in have:
                continue
            o = occ.get((n, a)) or {}
            other = written.get((x, n), [])
            other_txt = ("; ".join(f"{t2} -> {n} at occurrence {a2}" for t2, a2 in sorted(set(other)))
                         if other else f"nothing toward {n}")
            line = (f"- {n}, occurrence {a} (line {o.get('line')}: {(o.get('text') or '').strip()[:100]}): "
                    f"{t} -> {x}. The other side, {x}, has: {other_txt}.")
            items[(ent, n)].append(line)
            items[(ent, x)].append(line)
    return items


REPAIR_TEXT = """REPAIR. A program compared the answers of all calls for this entity. The items below are records that have
no mirrored partner record: a record written for a batch element, or a record another call wrote toward a batch
element. Check each item against the profiles and the rules, then return the complete answer for this batch again,
in the format of section 6:
  - where the pair holds and a side of it belongs to a batch element, write that side, with the type from the same
    row of section 3 as the other side;
  - where the two sides disagree on the type, choose the type the rules give for the pair, and write this batch's
    side with it;
  - where a driving type stands at an assignment occurrence, replace it with the receiving type of the same row;
  - where the profile and the source show no pair, withdraw the record.
Keep every other record as it is. Write no record only to complete a pair (G6).
ITEMS:
"""


def run_repair(modules, w_from, w_to, prompt_file, client, batching="declaration", workers=20, dry=False,
               log=print) -> dict:
    """Copy the base run's answers to w_to, then re-call each batch that holds an item with the items appended to its
    usual message. The system prompt is the base run's, unchanged."""
    ps = psha(prompt_file)
    system = Path(prompt_file).read_text(encoding="utf-8")
    src, dst = Path(w_from["out"]) / ps, Path(w_to["out"]) / ps
    dst.mkdir(parents=True, exist_ok=True)
    cost, todo = Counter(), []
    for m in modules:
        for f in src.glob(f"{m}__*.json"):
            if not (dst / f.name).exists():
                shutil.copy2(f, dst / f.name)
        items = repair_items(m, w_from, prompt_file)
        for ent in RS.load_module(m, w_from):
            for b, batch in enumerate(RS.batches_for(ent, batching)):
                lines = sorted({ln for n in batch for ln in items.get((ent["entity"], n), [])})
                if not lines:
                    continue
                msg = RS.user_message(ent, batch).replace(
                    "Return one json object in the format given in your instructions.",
                    REPAIR_TEXT + "\n".join(lines) + "\n\nReturn one json object in the format given in your instructions.")
                p = dst / f"{m}__{ent['entity']}__b{b:02d}.json"
                prev = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
                if prev.get("input_sha") == RS._sha(msg):
                    continue                                  # this repair is already done
                todo.append({"module": m, "entity": ent["entity"], "b": b, "batch": batch, "msg": msg, "p": p,
                             "n_occ": sum(len(ent["profile"].get(n, [])) for n in batch), "system": system,
                             "psha": ps, "record": {"repair_items": len(lines)}})
    log(f"   repair: {len(todo)} batch(es) to re-call, {sum(j['record']['repair_items'] for j in todo)} item lines in all")
    if dry or not todo:
        return {"calls": 0, "planned": len(todo)}
    cost.update(RS.call_pool(todo, client, "gpt-5-mini", "medium", workers, log))
    cost["usd_upper"] = round(cost["in"] * RS.PRICE["in"] + cost["out"] * RS.PRICE["out"], 4)
    return dict(cost)


# ------------------------------------------------------------------ the log
def log_entry(exp: str, config: str, lines: list[str]):
    head = "" if LOG.exists() else (
        "# Relation annotator experiments (Step 1, 15 test modules)\n\n"
        "One change per experiment, each in its own folder under `step1/lasset_step1/relation_exp/`. Numbers are "
        "written by `relation_experiments.log_entry()` from the saved answers; the analysis under each entry is added "
        "after the run. Metrics: records = relationship records (element, occurrence, type, target); unpartnered = "
        "records whose mirrored record is absent, split into omission (the other side wrote nothing for the pair, "
        "which the code reference links), type disagreement (the other side wrote a different type) and wrong side "
        "(a type from the other end of the pair); element pairs and typed records are agreement with the code "
        "reference, not accuracy.\n")
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(head + f"\n## {exp} ({stamp})\n\n{config}\n\n" + "\n".join(lines) + "\n")
