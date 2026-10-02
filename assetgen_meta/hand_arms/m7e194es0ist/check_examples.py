"""Code checks of the adapted worked examples (examples/<name>.adapted.json) before they enter the prompt:
  1. every map-excerpt element is declared, and its occurrence list equals the code table (IDs and lines)
  2. every record's "lines" are exactly the lines of its "at" IDs, and "at" IDs belong to the element
  3. every edge the final object cites has its mirror record on the partner (driving <-> receiving)
  4. the final object's (concept, asset rtl, entity, realization) set equals the old final object's
  5. trace_check: every structural reference and influence point is 'verified' against the excerpt; every "yes"
     line and flow line is an RTL line of the example
  6. leak check on the assembled example text (no corpus identifier, no numeric hint, no comment use)
Prints one line per check per example; exit code 1 if any fails."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in ("", "assetgen_meta", "blind_agent"):
    sys.path.insert(0, str(ROOT / p))
import trace_check as TC      # noqa: E402

MIRROR = {"CARRIES": "COPIES", "SOURCES": "DERIVES_FROM", "SEQUENCES": "CLOCKED_BY", "RESETS": "RESET_BY",
          "SELECTS": "SELECTED_BY", "CONSTRAINS": "CONSTRAINED_BY", "GATES": "GATED_BY"}
MIRROR.update({v: k for k, v in list(MIRROR.items())})
HEAD_RTL = "=== RTL (comments removed, blank lines left out; each line starts with its line number in the source file) ==="
HEAD_MAP = "=== RELATIONSHIP MAP: ELEMENTS AND RECORDS (excerpt: the elements this example cites; a real input lists every element) ==="
HEAD_FLOW = "=== RELATIONSHIP MAP: FLOW GRAPH (excerpt) ==="


def _body(t: str) -> str:
    """An excerpt without a header line of its own (the assembler writes the header)."""
    ls = t.strip().split("\n")
    while ls and ls[0].lstrip().startswith("=== "):
        ls = ls[1:]
    return "\n".join(ls).strip()


def assemble(n: int, src: dict, ad: dict) -> str:
    name = src["name"]
    return (f"### WORKED EXAMPLE {n}: {name}\n\nTARGET IP MODULE: {name}\n\n{HEAD_RTL}\n{src['rtl_numbered']}\n\n{HEAD_MAP}\n"
            f"{_body(ad['map_excerpt'])}\n\n{HEAD_FLOW}\n{_body(ad['flow_excerpt'])}\n\n"
            f"Identify the primary security assets for '{name}' and return the JSON object per the contract.\n\n"
            f"PRIVATE ANALYSIS (a demonstration of the procedure; never part of an answer)\n{ad['analysis'].strip()}\n\n"
            f"FINAL OBJECT\n{json.dumps(ad['final_object'], indent=1)}\n")


def refs(final):
    return sorted((c["concept"], s["asset rtl"], s["entity"], s["realization"])
                  for c in final.get("conceptual assets", []) for s in c.get("related structural assets", []))


def check(n: int, name: str, log=print, ad: dict | None = None) -> bool:
    """ad: the adapted example to check (default: read examples/<name>.adapted.json; nothing is ever written)."""
    src = json.loads((HERE / "examples" / f"{name}.source.json").read_text(encoding="utf-8"))
    if ad is None:
        p = HERE / "examples" / f"{name}.adapted.json"
        if not p.exists():
            log(f"{name}: adapted file missing"); return False
        ad = json.loads(p.read_text(encoding="utf-8"))
    text = assemble(n, src, ad)
    mapd = TC.parse_map_text(text.replace(HEAD_MAP, "=== RELATIONSHIP MAP: ELEMENTS AND RECORDS").replace(HEAD_FLOW, "=== RELATIONSHIP MAP: FLOW GRAPH"))
    els = {e["name"]: e for a in ("ports", "signals") for e in mapd[a]}
    ok = True
    # 1, 2
    bad1, bad2 = [], []
    for e in (x for a in ("ports", "signals") for x in mapd[a]):
        nm = e["name"]
        want = src["occurrences"].get(e.get("entity"), {}).get(nm)
        got = [{"id": o["id"], "line": o["line"]} for o in e["occurrences"]]
        if want is None or got != want:
            bad1.append(nm)
        ids = {o["id"]: o["line"] for o in e["occurrences"]}
        for r in e["relationship"]:
            if any(i not in ids for i in r.get("at", [])) or sorted(r.get("lines", [])) != sorted({ids[i] for i in r.get("at", []) if i in ids}):
                bad2.append(f"{nm} {r['type']}")
    log(f"{name} 1 occurrences equal the code table: {len(els) - len(bad1)}/{len(els)} elements {'ok' if not bad1 else 'FAIL ' + str(bad1[:8])}")
    log(f"{name} 2 record lines match their IDs: {'ok' if not bad2 else 'FAIL ' + str(bad2[:8])}")
    ok &= not bad1 and not bad2
    # 3 mirrors of cited edges
    final = ad["final_object"]
    cited = [(s.get("asset rtl"), s.get("entity"), (s.get("edge") or {}).get("type"), (s.get("edge") or {}).get("partner"))
             for c in final.get("conceptual assets", []) for s in c.get("related structural assets", [])]
    cited += [(s.get("element"), s.get("entity"), (s.get("edge") or {}).get("type"), (s.get("edge") or {}).get("partner"))
              for c in final.get("conceptual assets", []) for s in c.get("influence points", []) or []]
    by_ent = {(e.get("entity"), e["name"]): e for a in ("ports", "signals") for e in mapd[a]}
    nomirror = []
    for x, ent, t, y in cited:
        if not t or t == "CONNECTS" or t not in MIRROR:
            continue
        pe = by_ent.get((ent, y))             # the partner is declared in the same entity
        if pe is None or not any(r["type"] == MIRROR[t] and x in r.get("targets", []) for r in pe["relationship"]):
            nomirror.append(f"{x}@{ent} {t} {y}")
    log(f"{name} 3 cited edges have their mirror on the partner: {len(cited) - len(nomirror)}/{len(cited)} {'ok' if not nomirror else 'FAIL ' + str(nomirror[:8])}")
    ok &= not nomirror
    # 4 decisions unchanged
    same = refs(final) == refs(src["old_final"])
    log(f"{name} 4 references equal the old example's ({len(refs(src['old_final']))}): {'ok' if same else 'FAIL'}")
    if not same:
        a, b = set(refs(final)), set(refs(src["old_final"]))
        log(f"      added {sorted(a - b)[:6]}  removed {sorted(b - a)[:6]}")
    ok &= same
    # 5 trace_check
    lines = TC.numbered_lines(text)
    chk = TC.check_output(final, mapd, lines)
    s = TC.summarize({name: chk})
    good = s["ref_status"]["verified"] == s["refs"] and s["influence_status"]["verified"] == s["influence"] \
        and s["yes_with_rtl_line"] == s["yes_answers"] and s["flow_lines_in_rtl"] == s["flow_lines_cited"]
    log(f"{name} 5 trace_check: refs verified {s['ref_status']['verified']}/{s['refs']}, influence verified "
        f"{s['influence_status']['verified']}/{s['influence']}, yes lines {s['yes_with_rtl_line']}/{s['yes_answers']}, flow lines "
        f"{s['flow_lines_in_rtl']}/{s['flow_lines_cited']}: {'ok' if good else 'FAIL'}")
    if not good:
        for r in chk["refs"] + chk["influence"]:
            if r["status"] != "verified":
                log(f"      {r['element']} {r['role']} occ {r['occurrence']} edge {r.get('edge')}: {r['status']} ({r.get('why')})")
    ok &= good
    # 6 leak check
    import leak_check as LC, meta_tools as mt
    r = mt.check_prompt(text, LC.names(), name)
    log(f"{name} 6 leak check: {'ok' if r['ok'] else 'FAIL ' + str(r['problems'][:6])}")
    ok &= r["ok"]
    return ok


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    import os
    os.chdir(ROOT)
    res = [check(i, n) for i, n in ((1, "omsp_gpio"), (2, "tiny_aes"))]
    sys.exit(0 if all(res) else 1)
