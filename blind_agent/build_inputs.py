"""Inputs for the blind asset agent: one text file per module = the module's RTL (comments blanked, blank lines left out,
each line prefixed with its ORIGINAL line number) + the code-built relation map (compact view). Nothing else: no closed
set, no reference list, no prompt text, no LLM output.

  blind_agent/inputs/design/<m>.txt   neorv32_boot_rom, neorv32_fifo: the 2 tuning-folder modules with NO reference
                                      entries (LAsset pruned them); the only RTL the prompt designers may read.
  blind_agent/inputs/tuning/<m>.txt   the 15 tuning modules (selection)
  blind_agent/inputs/heldout/<m>.txt  the 26 held-out modules (one validation run of the selected prompt)

RTL text: the occurrence profiler's own numbered_entity_source (v3b builder), entity by entity in closed-set order, so
the map's `lines` (original file line numbers) point at the same text the agent reads.
Maps: step1/code_pairs_v2.py (frozen b0e767000ec2) + code SITE tags, no model; `functionality` is empty in these maps
and rel_view.compact() drops empty fields. The 2 design maps are built here by build_heldout_code_map.build_module into
step1/lasset_step1/relation_map_code_design/b0e767000ec2_codetags/.

Self-test (before writing): (1) hand-read: neorv32_hwspinlock line 41 is `if (rstn_i = '0') then` and line 43 is
`elsif rising_edge(clk_i) then`, and the map puts rstn_i / clk_i occurrences there; (2) every occurrence of every map
element: its recorded line text equals the numbered line in the agent's RTL text (reported as a count, must be all).
Needs the conda Python (tree_sitter_language_pack): %USERPROFILE%\\miniconda3\\python.exe blind_agent/build_inputs.py
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in ("", "assetgen_meta", "step1"):
    sys.path.insert(0, str(ROOT / p))
sys.stdout.reconfigure(encoding="utf-8")
import rel_view as rv                      # noqa: E402
import build_heldout_code_map as B         # noqa: E402

OUT = ROOT / "blind_agent" / "inputs"
MAPS = {"tuning": ROOT / "step1/lasset_step1/relation_map_code_tuning/b0e767000ec2_codetags",
        "heldout": ROOT / "step1/lasset_step1/relation_map_code_heldout/b0e767000ec2_codetags",
        "design": ROOT / "step1/lasset_step1/relation_map_code_design/b0e767000ec2_codetags"}
RTL = {"tuning": ROOT / "RTL_data", "heldout": ROOT / "RTL_heldout", "design": ROOT / "RTL_data"}
PARSED = {"tuning": ROOT / "parsed_tuning18", "heldout": ROOT / "parsed_heldout26", "design": ROOT / "parsed_tuning18"}
DESIGN = ["neorv32_boot_rom", "neorv32_fifo"]


def modules(split):
    if split == "design":
        return DESIGN
    return sorted(p.stem for p in MAPS[split].glob("neorv32_*.json"))


def rtl_text(split, m):
    g = B.builder()
    ents = json.loads((PARSED[split] / f"{m}.json").read_text(encoding="utf-8"))["entities"]
    with B._at(g["_B"].ROOT):
        return "\n\n".join(g["numbered_entity_source"](RTL[split] / f"{m}.vhd", e) for e in ents)


def the_map(split, m):
    return json.loads((MAPS[split] / f"{m}.json").read_text(encoding="utf-8"))


MAXLEN = 1500     # the agent's file reader may cut very long lines: no line of the input is longer than this
GUARD_MAX = 400   # a `guard` (the condition text of a GATES / SELECTS / CONSTRAINS record) longer than this is cut;
CUT = " ... [condition cut; read it at the cited lines]"   # the full condition is the RTL at the record's `lines`
CUT_COUNT = {}


def cut_guard(r: dict) -> dict:
    g = r.get("guard")
    if isinstance(g, str) and len(g) > GUARD_MAX:
        return {**r, "guard": g[:GUARD_MAX] + CUT}
    return r


def _chunks(key, items):
    """{key: [slice]} lines, each under MAXLEN."""
    out, chunk = [], []
    for x in items + [None]:
        if x is None or (chunk and len(json.dumps({key: chunk + [x]}, separators=(",", ":"))) > MAXLEN - 8):
            if chunk:
                out.append("    " + json.dumps({key: chunk}, separators=(",", ":")))
            chunk = []
        if x is not None:
            chunk.append(x)
    return out


LISTS = ("constant_drivers", "configuration", "connections")


def map_lines(cm: dict) -> list[str]:
    """The compact map, one JSON object per line: an element line (every field except `relationship` and the list
    fields constant_drivers / configuration / connections), then, indented, one line per slice of each list field
    ({"<field>": [...]}) and one line per relationship record. A record whose `targets` list would make the line too
    long is written as several lines with the same type and lines, each holding a slice of the targets. The only loss:
    a guard over GUARD_MAX characters is cut (counted in CUT_COUNT)."""
    out = []
    for arr, tag in (("ports", "PORT"), ("signals", "SIGNAL")):
        for e in cm.get(arr, []):
            out.append(f"{tag} " + json.dumps({k: v for k, v in e.items() if k != "relationship" and k not in LISTS},
                                              separators=(",", ":")))
            for k in LISTS:
                out += _chunks(k, list(e.get(k, [])))
            for r0 in e.get("relationship", []):
                r = cut_guard(r0)
                CUT_COUNT[r is not r0] = CUT_COUNT.get(r is not r0, 0) + 1
                tg = r.get("targets", [])
                chunk = []
                for t in tg + [None]:
                    trial = json.dumps({**r, "targets": chunk + ([t] if t else [])}, separators=(",", ":"))
                    if t is None or (len(trial) > MAXLEN - 8 and chunk):
                        out.append("    " + json.dumps({**r, "targets": chunk} if tg else r, separators=(",", ":")))
                        chunk = []
                    if t is not None:
                        chunk.append(t)
    return out


def text(split, m):
    mp = "\n".join(map_lines(rv.compact(the_map(split, m))))
    return (f"MODULE: {m}\n\n=== RTL (VHDL; comments removed, blank lines left out; each line starts with its line number "
            f"in the source file) ===\n{rtl_text(split, m)}\n\n"
            f"=== RELATION MAP (written by a static analyser from the RTL above; `lines` are those line numbers. "
            f"One element per PORT / SIGNAL line, as JSON; each indented JSON line under it is either a slice of one of its "
            f"list fields (constant_drivers, configuration, connections) or one of its relationship records) ===\n{mp}\n")


def roundtrip(split, m) -> bool:
    """The line format parses back to exactly the compact map (targets slices re-joined; over-long guards cut as in
    map_lines)."""
    cm, back, cur = rv.compact(the_map(split, m)), {"ports": [], "signals": []}, None
    for l in map_lines(cm):
        if l.startswith("    "):
            o = json.loads(l)
            k = next((k for k in LISTS if k in o), None)
            if k:
                cur.setdefault(k, []).extend(o[k])
            else:
                cur.setdefault("relationship", []).append(o)
        else:
            tag, js = l.split(" ", 1)
            cur = json.loads(js)
            back["ports" if tag == "PORT" else "signals"].append(cur)
    def norm(d):
        out = []
        for a in ("ports", "signals"):
            for e in d[a]:
                rs = {}
                for r in map(cut_guard, e.get("relationship", [])):
                    key = json.dumps({k: v for k, v in r.items() if k != "targets"}, sort_keys=True)
                    rs.setdefault(key, []).extend(r.get("targets", []))
                out.append((a, json.dumps({k: v for k, v in e.items() if k != "relationship"}, sort_keys=True),
                            sorted((k, json.dumps(v)) for k, v in rs.items())))
        return out
    return norm(cm) == norm(back)


def build_design_maps():
    src = B.Source(ROOT / "RTL_data", ROOT / "parsed_tuning18")
    MAPS["design"].mkdir(parents=True, exist_ok=True)
    for m in DESIGN:
        if not (MAPS["design"] / f"{m}.json").exists():
            print(m, B.build_module(m, src, MAPS["design"]))


def numbered_lines(t):
    out = {}
    for l in t.split("\n"):
        if "|" in l and l.split("|", 1)[0].strip().isdigit():
            n, s = l.split("|", 1)
            out[int(n)] = s.strip()
    return out


def selftest():
    ok = True
    L = numbered_lines(rtl_text("tuning", "neorv32_hwspinlock"))
    d = the_map("tuning", "neorv32_hwspinlock")
    occ = {(e["name"], o["id"]): o["line"] for a in ("ports", "signals") for e in d[a] for o in e["occurrences"]}
    for (n, i), (ln, want) in {("rstn_i", 3): (41, "if (rstn_i = '0') then"), ("clk_i", 3): (43, "elsif rising_edge(clk_i) then")}.items():
        good = occ[(n, i)] == ln and L.get(ln) == want
        ok &= good
        print(f"   hand-read {n} occurrence {i}: map line {occ[(n, i)]}, RTL line {ln} {L.get(ln)!r}: {'ok' if good else 'MISMATCH'}")
    for split in ("design", "tuning", "heldout"):
        n = bad = 0
        for m in modules(split):
            L = numbered_lines(rtl_text(split, m))
            for a in ("ports", "signals"):
                for e in the_map(split, m)[a]:
                    for o in e["occurrences"]:
                        n += 1
                        bad += L.get(o["line"]) != o["text"].strip()
        ok &= bad == 0
        print(f"   {split}: {n - bad}/{n} map occurrences match the numbered RTL line exactly")
        rt = [m for m in modules(split) if not roundtrip(split, m)]
        longest = max(len(l) for m in modules(split) for l in text(split, m).split("\n"))
        ok &= not rt and longest <= MAXLEN
        print(f"   {split}: map line format parses back to the compact map in {len(modules(split)) - len(rt)}/{len(modules(split))} "
              f"modules; longest input line {longest} chars (limit {MAXLEN})")
    return ok


if __name__ == "__main__":
    build_design_maps()
    assert selftest(), "self-test failed: nothing written"
    CUT_COUNT.clear()
    for split in ("design", "tuning", "heldout"):
        (OUT / split).mkdir(parents=True, exist_ok=True)
        sizes = []
        for m in modules(split):
            t = text(split, m)
            (OUT / split / f"{m}.txt").write_text(t, encoding="utf-8")
            sizes.append((len(t), m))
        print(f"{split}: {len(sizes)} modules, chars total {sum(s for s, _ in sizes):,}, max {max(sizes)[0]:,} ({max(sizes)[1]})")
        print(f"   guards cut so far: {CUT_COUNT.get(True, 0)} of {sum(CUT_COUNT.values())} relationship records")
