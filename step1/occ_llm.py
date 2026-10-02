"""Occurrence profiling for Step 1: code where the model is weak, model where it is strong.

WHAT THE MEASUREMENT SAID (run 6 audit, 661 entries over trng and cache):
  the model's enclosing-structure chains matched the code finder's on 476 of 661 (185 wrong, 28%). All the error is at
  the branch level: branch 106 wrong end, 158 missing or wrong start, of 408; if 112 missing. Containers were perfect
  (architecture body 519/0, process 415/0, case 163/0, port clause 75/0, association list 48/0, generate 22/0).
  Run 5's hand review called the same thing context_span_wrong 104, context_structure_wrong 59 of 662.
SO: the occurrence inventory and the structure chain come from code, and the model is asked only for Role and SITE
tags. Every Structure is then overwritten with the code chain, and the overwrites are counted, so the correction is
visible rather than assumed.

PROMPT: the run-6 classify prompt, rebuilt from the files that produced it. The rulebook (rulebook.json, file sha
34d10274b852 = the run-6 approved one) is injected SLIM, without its basis quotes, exactly as
build_occurrence_notebook_v2.py lines 1285-1287 do it. classify_system() reports whether the result matches run 6's
recorded sha 6f4f22e256e3; today it is 41 characters longer, because annotate_rules.md was edited later the same day.

ANSWER SHAPE (annotate_rules.md section L): a dict KEYED BY ELEMENT NAME, each value a list of occurrence records
whose five fields are "Occurrence ID", "Occurrence Lines", "Structure" (a LIST of {kind, lines, opened by} objects),
"Role" and "SITE Tagged". An earlier draft of this file looked for an "Element" field inside each record and parsed
Structure as a string; it matched nothing, and a whole run was wasted.

CONVENTIONS THAT MUST MATCH THE EXPERIMENT (an earlier draft of this file got these wrong):
  - Occurrence ID is an INTEGER per element, 1-based, as in "inventory Occurrence ID 30 at line 246".
  - A name can occur several times on one line; each occurrence is its own inventory row, numbered by "Occurrence on
    line", and the profile carries one entry per occurrence.
  - Batches are about 60 occurrences, the size run 6 used (trng+cache: 662 entries over 10 batches).
"""
from __future__ import annotations

import hashlib, json, random, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
import occurrence_profile as OP   # noqa: E402

PROMPTS = ROOT / "bahavioral_patterns_of_assets/annotation_pack_elements/occurrence_prompts_v2"
PROFILES = HERE / "occurrence_profiles"
RUN6_CLASSIFY_SHA = "6f4f22e256e3"      # recorded in _audit_2026-09-16_run6/run6_outputs.txt line 48
BATCH_OCCURRENCES = 60
STRUCT = re.compile(r"(port clause|declarative part|architecture body|generate|process|loop|if|branch|case|alternative|"
                    r"association list)\s+(\d+)\s*[-–]\s*(\d+)", re.I)


def sha12(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:12]


def classify_system() -> tuple[str, str, bool]:
    """-> (system prompt, sha12, matches the run-6 prompt). Same assembly as annotate_systems()."""
    fill = lambda t, **s: re.sub(r"<<(\w+)>>", lambda m: s.get(m.group(1), m.group(0)), t)
    # run 6 injected the rulebook WITHOUT its basis quotes (they repeat section M of annotate_rules word for word):
    # build_occurrence_notebook_v2.py lines 1285-1287.
    rb = json.loads((PROMPTS / "rulebook.json").read_text(encoding="utf-8"))
    slim = {"SITE_RULES": {s: {k: v for k, v in r.items() if k != "basis"} for s, r in rb["SITE_RULES"].items()},
            "CONFLICT_RULES": [{k: v for k, v in c.items() if k != "basis"} for c in rb["CONFLICT_RULES"]]}
    rulebook_text = json.dumps(slim, indent=1, ensure_ascii=False)
    rules = fill((PROMPTS / "annotate_rules.md").read_text(encoding="utf-8"), RULEBOOK=rulebook_text)
    sysmsg = fill((PROMPTS / "3_classify.md").read_text(encoding="utf-8"), ANNOTATE_RULES=rules)
    assert "<<" not in sysmsg or not re.search(r"<<\w+>>", sysmsg), "a prompt slot was left unfilled"
    s = sha12(sysmsg)
    return sysmsg, s, s == RUN6_CLASSIFY_SHA


def code_profile(module: str) -> dict:
    p = PROFILES / f"{module}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else OP.profile_module(module)


def numbered_source(module: str) -> str:
    L = OP.masked_lines(ROOT / f"RTL_data/{module}.vhd")
    return "\n".join(f"{n}: {t}" for n, t in L.items())


def jobs(module: str, cap: int | None = 40, seed: int = 0, batch: int = BATCH_OCCURRENCES) -> list[dict]:
    """Classify jobs for one module: the closed-set slice, the code inventory and the code chains, in batches."""
    prof = code_profile(module)
    rows = [v for v in prof["elements"].values() if v["occurrences"]]
    if cap and len(rows) > cap:
        rows = sorted(random.Random(seed).sample(rows, cap), key=lambda v: (v["entity"], v["name"]))
    src = numbered_source(module)
    out, elems, inv, chains, n = [], [], [], {}, 0
    entity = [None]

    def flush():
        if elems:
            out.append({"module": module, "entity": entity[0], "batch": len(out), "elements": list(elems),
                        "inventory": list(inv), "chains": dict(chains), "source": src})
        elems.clear(); inv.clear(); chains.clear()

    # one job covers ONE entity, as the prompt states ("the source of ONE entity"); a file can declare several
    rows = sorted(rows, key=lambda v: (v["entity"], v["name"]))
    for v in rows:
        if (n and n + len(v["occurrences"]) > batch) or (entity[0] is not None and v["entity"] != entity[0]):
            flush(); n = 0
        entity[0] = v["entity"]
        elems.append({"name": v["name"], "kind": v["kind"], "entity": v["entity"]})
        for i, o in enumerate(v["occurrences"], 1):             # Occurrence ID: integer, 1-based, per element
            inv.append({"Occurrence ID": i, "Element": v["name"], "Line": o["line"],
                        "Occurrence on line": o["on_line"], "Name as written": v["name"],
                        "Line text": o["text"]})
            chains[f"{v['name']}|{i}"] = {"structure": o["structure"], "roles": o["roles"], "line": o["line"],
                                          "element": v["name"], "in_branch": o["in_branch"]}
        n += len(v["occurrences"])
    flush()
    return out


def user_message(j: dict) -> str:
    return (f"ENTITY: {j.get('entity') or j['module']}   (module {j['module']})\n\n"
            f"SOURCE of this entity. Comments removed; each line starts with its line number:\n\n{j['source']}\n\n"
            f"CLOSED SET, in this order:\n{json.dumps(j['elements'], indent=1)}\n"
            f"\nOCCURRENCE INVENTORY, made by a program:\n{json.dumps(j['inventory'], indent=1)}\n"
            f"\nReturn one JSON object in the format given in your instructions.\n")


def entries_of(answer) -> list[tuple[str, dict]]:
    """-> [(element name, occurrence record)].

    The contract (annotate_rules.md section L) is a dict KEYED BY ELEMENT NAME whose values are lists of occurrence
    records; the element name is the key, not a field of the record. Other shapes are accepted defensively.
    """
    out = []
    if isinstance(answer, dict):
        for k, v in answer.items():
            if isinstance(v, list) and all(isinstance(x, dict) for x in v):
                if k in ("entries", "profiles", "occurrence_profiles", "occurrences", "elements", "profile"):
                    out += [(str(_get(x, "element", "name") or ""), x) for x in v]      # flat list with the name inside
                else:
                    out += [(k, x) for x in v]                                          # the contract shape
            elif isinstance(v, dict):
                if any(str(kk).lower().replace(" ", "_") in ("occurrence_id", "id") for kk in v):
                    out.append((k, v))                                  # element -> one occurrence record
                else:
                    for kk, vv in v.items():
                        if isinstance(vv, list):
                            out += [(kk, x) for x in vv if isinstance(x, dict)]
                        elif isinstance(vv, dict):
                            out.append((kk, vv))
    elif isinstance(answer, list):
        out += [(str(_get(x, "element", "name") or ""), x) for x in answer if isinstance(x, dict)]
    return out


def _get(e: dict, *names):
    for n in names:
        for k in e:
            if k.lower().replace(" ", "_") == n:
                return e[k]
    return None


def triples(s) -> set | None:
    """(kind, start, end) from either the contract's list of objects or a rendered chain; None if nothing parses."""
    if not s:
        return None
    if isinstance(s, list):                       # [{"kind": ..., "lines": [a, b], "opened by": ...}]
        t = set()
        for x in s:
            if isinstance(x, dict) and isinstance(x.get("lines"), (list, tuple)) and len(x["lines"]) == 2:
                try:
                    t.add((str(x.get("kind", "")).lower(), int(x["lines"][0]), int(x["lines"][1])))
                except (TypeError, ValueError):
                    pass
        return t or None
    t = {(m.group(1).lower(), int(m.group(2)), int(m.group(3))) for m in STRUCT.finditer(str(s))}
    return t or None


def merge(j: dict, answer) -> dict:
    """Overwrite every Structure with the code chain; keep the model's Role and SITE tags. Count what changed."""
    out, seen = [], set()
    st = {"corrected": 0, "same": 0, "unparseable": 0, "unknown element": 0, "added by the model": 0,
          "branch corrections": 0}
    known = {e["name"] for e in j["elements"]}
    lower = {n.lower(): n for n in known}
    ent = (j.get("entity") or "") + "."

    def resolve(name: str) -> str | None:
        """The model may quote the name, or prefix it with its entity. Anything else is not in the closed set."""
        n = str(name).strip().strip('"\'')
        if n in known:
            return n
        if n.startswith(ent) and n[len(ent):] in known:
            return n[len(ent):]
        return lower.get(n.lower())

    for el, e in entries_of(answer):
        el = resolve(el)
        oid = _get(e, "occurrence_id", "id")
        try:
            key = f"{el}|{int(oid)}" if el else None
        except (TypeError, ValueError):
            key = None
        c = j["chains"].get(key) if key else None
        if c is None:
            # the prompt allows the model to ADD an occurrence the program missed, with the next unused ID
            st["added by the model" if el else "unknown element"] += 1
            if el:
                out.append({"Occurrence ID": oid, "Element": el, "Line": _get(e, "occurrence_lines", "line"),
                            "Structure": None, "Structure (model, replaced)": _get(e, "structure", "structures"),
                            "Role": _get(e, "role") or "", "SITE Tagged": _get(e, "site_tagged", "sites") or [],
                            "code roles": None, "in_branch": None, "added by the model": True})
            continue
        seen.add(key)
        model_struct = _get(e, "structure", "structures", "context")
        tm, tc = triples(model_struct), triples(c["structure"])
        if tm is None:
            st["unparseable"] += 1
        elif tm == tc:
            st["same"] += 1
        else:
            st["corrected"] += 1
            st["branch corrections"] += bool({x for x in (tm ^ (tc or set())) if x[0] in ("branch", "if")})
        out.append({"Occurrence ID": int(oid), "Element": c["element"], "Line": c["line"],
                    "Structure": c["structure"], "Structure (model, replaced)": model_struct,
                    "Role": _get(e, "role") or "", "SITE Tagged": _get(e, "site_tagged", "sites", "site") or [],
                    "code roles": c["roles"], "in_branch": c["in_branch"]})
    for key, c in j["chains"].items():
        if key not in seen:
            out.append({"Occurrence ID": int(key.split("|")[1]), "Element": c["element"], "Line": c["line"],
                        "Structure": c["structure"], "Structure (model, replaced)": None, "Role": None,
                        "SITE Tagged": [], "code roles": c["roles"], "in_branch": c["in_branch"]})
    stats = {"occurrences": len(j["chains"]), "answered": len(seen), "missing": len(j["chains"]) - len(seen), **st}
    return {"module": j["module"], "batch": j["batch"], "entries": out, "stats": stats}


def selftest():
    sysmsg, s, ok = classify_system()
    js = jobs("neorv32_wdt", cap=6, seed=0)
    inv = js[0]["inventory"]
    assert all(isinstance(r["Occurrence ID"], int) and r["Occurrence ID"] >= 1 for r in inv), "ids must be integers"
    assert all(r["Occurrence on line"] >= 1 for r in inv), "each occurrence carries its index on the line"
    assert max(len(j["chains"]) for j in js) <= BATCH_OCCURRENCES + 40, "batches must stay near the run-6 size"
    # a model answer that echoes the inventory must merge with zero invented ids and zero corrections
    def as_objects(rendered):
        return [{"kind": k, "lines": [a, b]} for k, a, b in sorted(triples(rendered) or [])]
    fake = {}
    for r in inv:
        ch = js[0]["chains"][f"{r['Element']}|{r['Occurrence ID']}"]
        fake.setdefault(r["Element"], []).append(
            {"Occurrence ID": r["Occurrence ID"], "Occurrence Lines": r["Line"],
             "Structure": as_objects(ch["structure"]), "Role": "reads the value", "SITE Tagged": ["RHS_OPERAND"]})
    m = merge(js[0], fake)
    assert m["stats"]["unknown element"] == 0 and m["stats"]["added by the model"] == 0, m["stats"]
    assert m["stats"]["missing"] == 0, m["stats"]
    assert m["stats"]["corrected"] == 0 and m["stats"]["same"] == len(inv), m["stats"]
    # a wrong branch span must be caught as a correction
    r0 = inv[0]; k0 = f"{r0['Element']}|{r0['Occurrence ID']}"
    bad = {r0["Element"]: [{"Occurrence ID": r0["Occurrence ID"], "Occurrence Lines": r0["Line"],
                            "Structure": [{"kind": "architecture body", "lines": [1, 999]},
                                          {"kind": "branch", "lines": [5, 6], "opened by": "IF_COND"}], "Role": "x"}]}
    mb = merge(js[0], bad)
    assert mb["stats"]["corrected"] == 1, mb["stats"]
    print(f"occ_llm selftest PASS | classify prompt {len(sysmsg):,} chars sha {s} "
          f"{'== run 6' if ok else '!= run 6 (' + RUN6_CLASSIFY_SHA + ')'} | wdt: {len(js)} batch(es)")
    return ok


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    selftest()
