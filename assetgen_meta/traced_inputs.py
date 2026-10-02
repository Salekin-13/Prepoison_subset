"""Inputs of the traced arm (m7e194es0ist): one text per module with exactly two sources, both derived from the RTL.

  1. RTL       the module's entities as the occurrence profiler numbers them: comments blanked, blank lines left out,
               every line prefixed with its line number in the source file (numbers skip where lines were left out).
  2. MAP       the code-built relationship map (step1/code_pairs_v2.py, frozen b0e767000ec2; code SITE tags; no model),
               one element per line WITH its occurrence IDs, one relationship record per line with `at` (the element's
               occurrence IDs where the record holds) and `lines`; then a FLOW GRAPH section computed here from those
               records (no model): edge-symmetry check, the paths from every input port, input field and constant-driven
               element to the stored elements, output ports and sub-block connections they reach, and the elements
               with no local use.

  assetgen_meta/traced_inputs/<split>/<module>.txt       the user-message body (split: tuning = the 18 RTL_data files,
                                                          heldout = the 26 RTL_heldout files)
  assetgen_meta/traced_inputs/<split>/_flow/<module>.json the flow graph as data (for trace_check.py)

Maps: tuning step1/lasset_step1/relation_map_code_tuning/b0e767000ec2_codetags (equal to the stored maps on 1,641/1,641
elements); boot_rom and fifo from relation_map_code_design/ (blind_agent/build_inputs.py); package has none.
Run with the conda Python (tree_sitter_language_pack):  %USERPROFILE%\\miniconda3\\python.exe assetgen_meta/traced_inputs.py
Self-tests run first; nothing is written if one fails.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT), str(HERE), str(ROOT / "step1")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = HERE / "traced_inputs"
MAPS = {"tuning": [ROOT / "step1/lasset_step1/relation_map_code_tuning/b0e767000ec2_codetags",
                   ROOT / "step1/lasset_step1/relation_map_code_design/b0e767000ec2_codetags"],
        "heldout": [ROOT / "step1/lasset_step1/relation_map_code_heldout/b0e767000ec2_codetags"]}
RTL = {"tuning": ROOT / "RTL_data", "heldout": ROOT / "RTL_heldout"}
PARSED = {"tuning": ROOT / "parsed_tuning18", "heldout": ROOT / "parsed_heldout26"}
DATA = ("CARRIES", "SOURCES")                         # driving value edges Y -> X
CONTROL = ("GATES", "SELECTS", "CONSTRAINS")          # driving control edges (influence points)
CLOCKRESET = ("SEQUENCES", "RESETS")
MIRROR = {"CARRIES": "COPIES", "SOURCES": "DERIVES_FROM", "SEQUENCES": "CLOCKED_BY", "RESETS": "RESET_BY",
          "SELECTS": "SELECTED_BY", "CONSTRAINS": "CONSTRAINED_BY", "GATES": "GATED_BY"}
MAXLEN, GUARD_MAX = 1500, 400
CUT = " ... [condition cut; read it at the cited lines]"
NO_MAP = "(no map: the analyser wrote no relationship map for this file)"


def modules(split):
    return sorted(p.stem for p in RTL[split].glob("*.vhd"))


def map_path(split, m):
    for d in MAPS[split]:
        if (d / f"{m}.json").exists():
            return d / f"{m}.json"
    return None


_PORT_DIRS: dict | None = None


def port_dirs() -> dict:
    """{entity: {port: dir}} from every parsed closed set (tuning and held-out files declare all the sub-units)."""
    global _PORT_DIRS
    if _PORT_DIRS is None:
        _PORT_DIRS = {}
        for d in (PARSED["tuning"], PARSED["heldout"]):
            for f in d.glob("*.json"):
                for p in json.loads(f.read_text(encoding="utf-8")).get("ports", []):
                    _PORT_DIRS.setdefault(p.get("entity"), {}).setdefault(p.get("name"), p.get("dir"))
    return _PORT_DIRS


def instances(split, m) -> dict:
    """{instance label: entity} from the module's RTL ('<label>: entity <lib>.<entity>')."""
    import re
    txt = (RTL[split] / f"{m}.vhd").read_text(encoding="utf-8", errors="ignore")
    return {a: b for a, b in re.findall(r"(\w+)\s*:\s*entity\s+(?:\w+\.)?(\w+)", txt)}


def resolve_modes(split, m, d: dict) -> int:
    """Fill a connection's missing "mode" from the instantiated entity's port declaration (in place). -> count filled."""
    inst, dirs, n = instances(split, m), port_dirs(), 0
    for a in ("ports", "signals"):
        for e in d.get(a, []):
            for c in e.get("connections", []) or []:
                if c.get("mode") is None:
                    md = dirs.get(inst.get(c.get("instance")), {}).get(c.get("formal"))
                    if md:
                        c["mode"] = md
                        n += 1
    return n


def load_map(split, m):
    """The code map, with sub-unit connection directions filled from the sub-units' declarations."""
    p = map_path(split, m)
    if not p:
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    resolve_modes(split, m, d)
    return d


# ------------------------------------------------------------------------------------------------ RTL view ---
def rtl_text(split, m) -> str:
    import build_heldout_code_map as B
    g = B.builder()
    ents = json.loads((PARSED[split] / f"{m}.json").read_text(encoding="utf-8")).get("entities", [])
    with B._at(g["_B"].ROOT):
        parts = [g["numbered_entity_source"](RTL[split] / f"{m}.vhd", e) for e in ents]
    if parts:
        return "\n\n".join(parts)
    # a file with no entity (a package): every non-blank line, comments blanked, with its number
    masked = g["_mask_comments"]((RTL[split] / f"{m}.vhd").read_text(encoding="utf-8", errors="ignore"), vhdl=True) \
        if "_mask_comments" in g else (RTL[split] / f"{m}.vhd").read_text(encoding="utf-8", errors="ignore")
    return "\n".join(f"{i:>5} | {l.rstrip()}" for i, l in enumerate(masked.splitlines(), 1) if l.strip())


def numbered_lines(t: str) -> dict[int, str]:
    out = {}
    for l in t.split("\n"):
        if "|" in l and l.split("|", 1)[0].strip().isdigit():
            n, s = l.split("|", 1)
            out[int(n)] = s.strip()
    return out


# ------------------------------------------------------------------------------------------------ map view ---
def _cut(r):
    g = r.get("guard")
    return {**r, "guard": g[:GUARD_MAX] + CUT} if isinstance(g, str) and len(g) > GUARD_MAX else r


def _clean(d):
    return {k: v for k, v in d.items() if v not in (None, [], {}, "")}


def element_view(e: dict) -> dict:
    """Element fields for the map line: everything except occurrences (given as {id: line}), relationships and the
    list fields (written on their own lines)."""
    v = _clean({k: x for k, x in e.items() if k not in ("occurrences", "relationship", "constant_drivers",
                                                        "configuration", "connections", "functionality")})
    v["occurrences"] = {str(o["id"]): o["line"] for o in e.get("occurrences", [])}
    return v


def record_view(r: dict, line_of: dict) -> dict:
    v = _clean({k: x for k, x in r.items() if k != "partner_at"})
    v["lines"] = sorted({line_of[i] for i in (r.get("at") or []) if i in line_of})
    return _cut(v)


def _chunks(prefix_obj: dict, key: str, items: list) -> list[str]:
    out, chunk = [], []
    for x in items + [None]:
        if x is None or (chunk and len(json.dumps({**prefix_obj, key: chunk + [x]}, separators=(",", ":"))) > MAXLEN - 8):
            if chunk:
                out.append("    " + json.dumps({**prefix_obj, key: chunk}, separators=(",", ":")))
            chunk = []
        if x is not None:
            chunk.append(x)
    return out


def map_lines(d: dict) -> list[str]:
    out = []
    for arr, tag in (("ports", "PORT"), ("signals", "SIGNAL")):
        for e in d.get(arr, []):
            line_of = {o["id"]: o["line"] for o in e.get("occurrences", [])}
            ev = element_view(e)
            occ = ev.pop("occurrences")
            head = json.dumps(ev, separators=(",", ":"))
            out.append(f"{tag} {head}")
            items = list(occ.items())
            out += _chunks({}, "occurrences", [{"id": int(k), "line": v} for k, v in items])
            for k in ("constant_drivers", "configuration", "connections"):
                vals = []
                for c in e.get(k, []) or []:
                    if isinstance(c, dict) and "at" in c:
                        ats = c["at"] if isinstance(c["at"], list) else [c["at"]]
                        c = {**{kk: vv for kk, vv in c.items()}, "lines": sorted({line_of[a] for a in ats if a in line_of})}
                    vals.append(c)
                out += _chunks({}, k, vals)
            for r in e.get("relationship", []) or []:
                rv_ = record_view(r, line_of)
                tg = rv_.get("targets", [])
                if not tg:
                    out.append("    " + json.dumps(rv_, separators=(",", ":")))
                else:
                    out += _chunks({k: x for k, x in rv_.items() if k != "targets"}, "targets", list(tg))
    return out


# ------------------------------------------------------------------------------------------------ flow graph ---
def flow_graph(d: dict) -> dict:
    """Computed from the map's records only. Nodes are element names; a sub-block port is '<instance>.<formal>'."""
    els = {e["name"]: e for a in ("ports", "signals") for e in d.get(a, [])}
    ent_of = {e["name"]: e.get("entity", "") for e in els.values()}
    data, control = defaultdict(set), defaultdict(set)          # Y -> {X}
    clockreset = set()
    driving, receiving = set(), set()
    for y, e in els.items():
        for r in e.get("relationship", []) or []:
            t = r["type"]
            for x in r.get("targets", []):
                if t in MIRROR:
                    driving.add((y, t, x))
                else:
                    receiving.add((y, t, x))
                if t in DATA:
                    data[y].add(x)
                elif t in CONTROL:
                    control[y].add(x)
                elif t in CLOCKRESET:
                    clockreset.add(y)
        for c in e.get("connections", []) or []:
            node = f"{c.get('instance', '?')}.{c.get('formal', '?')}"
            mode = c.get("mode")
            if mode in ("in", "inout", None):
                data[y].add(node)
            if mode in ("out", "buffer", "inout", None):
                data[node].add(y)
    inv = {v: k for k, v in MIRROR.items()}
    unmatched_drv = sorted(f"{y} {t} {x}" for y, t, x in driving if (x, MIRROR[t], y) not in receiving)
    unmatched_rcv = sorted(f"{x} {t} {y}" for x, t, y in receiving if t in inv and (y, inv[t], x) not in driving)

    def mode(n):
        return ((els.get(n) or {}).get("boundary") or {}).get("mode")

    def stored(n):
        return (els.get(n) or {}).get("storage") in ("edge", "mixed")

    def subblock(n):
        return n not in els

    records = sorted(n for n in els if any(o.startswith(n + ".") for o in els))
    self_state = sorted(n for n in els if n in data.get(n, ()))
    sources = []
    for n, e in els.items():
        if n in records:
            continue
        if mode(n) in ("in", "inout") and n not in clockreset:
            sources.append((n, "input"))
        elif e.get("constant_drivers") and not any(n in xs for y, xs in data.items() if y != n):
            sources.append((n, "constant-valued"))
    paths = {}
    for s, kind in sources:
        seen, q = {s}, deque([s])
        while q:
            u = q.popleft()
            for v in data.get(u, ()):
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        seen.discard(s)
        ends = {"stores": sorted(n for n in seen if stored(n)),
                "exits": sorted(n for n in seen if mode(n) in ("out", "inout", "buffer")),
                "sub-block": sorted(n for n in seen if subblock(n))}
        paths[s] = {"kind": kind, **ends,
                    "influence": sorted({y for y, xs in control.items() for x in xs if x in seen or x == s} - {s})}
    reached = {n for p in paths.values() for k in ("stores", "exits", "sub-block") for n in p[k]}
    on_path = reached | set(paths)
    for s in paths:
        seen = {s}
        q = deque([s])
        while q:
            u = q.popleft()
            for v in data.get(u, ()):
                if v not in seen:
                    seen.add(v); q.append(v)
        on_path |= seen
    no_use = sorted(n for n, e in els.items() if not (e.get("relationship") or e.get("connections"))
                    and not e.get("constant_drivers") and n not in records)
    control_only = sorted(s for s, p in paths.items() if not (p["stores"] or p["exits"] or p["sub-block"]) and control.get(s))
    off_path = sorted(n for n in els if n not in on_path and n not in no_use and n not in clockreset
                      and n not in records and n not in self_state)
    return {"elements": len(els), "entity_of": ent_of,
            "symmetry": {"driving": len(driving), "receiving": len(receiving),
                         "driving_without_receiving": unmatched_drv, "receiving_without_driving": unmatched_rcv},
            "clock_reset": sorted(clockreset), "records": records, "self_updating": self_state,
            "control_only_inputs": {s: sorted(control[s]) for s in control_only},
            "paths": paths, "no_local_use": no_use, "not_on_an_input_path": off_path}


def flow_lines(fg: dict) -> list[str]:
    s = fg["symmetry"]
    out = [f"MAP CHECK {json.dumps({'elements': fg['elements'], 'driving records': s['driving'], 'receiving records': s['receiving'], 'driving without receiving': len(s['driving_without_receiving']), 'receiving without driving': len(s['receiving_without_driving'])}, separators=(',', ':'))}"]
    for k in ("driving_without_receiving", "receiving_without_driving"):
        if s[k]:
            out += _chunks({}, k.replace("_", " "), s[k])
    out += _chunks({}, "clock or reset (drive SEQUENCES / RESETS)", fg["clock_reset"])
    out += _chunks({}, "whole records (their fields carry the records)", fg["records"])
    out += _chunks({}, "self-updating (X is computed from X: counters, state registers)", fg["self_updating"])
    for src, p in sorted(fg["paths"].items()):
        if not any(p[k] for k in ("stores", "exits", "sub-block")):
            continue
        out.append(f"PATH {json.dumps({'from': src, 'source': p['kind']}, separators=(',', ':'))}")
        for k in ("stores", "exits", "sub-block", "influence"):
            if p[k]:
                out += _chunks({}, k, p[k])
    for s, xs in sorted(fg["control_only_inputs"].items()):
        out.append("CONTROL-ONLY " + json.dumps({"from": s, "source": fg["paths"][s]["kind"],
                                                 "gates or selects": xs[:40] + (["..."] if len(xs) > 40 else [])}, separators=(",", ":")))
    out += _chunks({}, "no local use (no relationship, connection or constant driver)", fg["no_local_use"])
    out += _chunks({}, "not reached from an input or constant-valued element", fg["not_on_an_input_path"])
    return out


def text(split, m) -> tuple[str, dict | None]:
    d = load_map(split, m)
    rtl = rtl_text(split, m)
    if d is None:
        return (f"TARGET IP MODULE: {m}\n\n=== RTL (comments removed, blank lines left out; each line starts with its "
                f"line number in the source file) ===\n{rtl}\n\n=== RELATIONSHIP MAP ===\n{NO_MAP}\n\n"
                f"Identify the primary security assets for '{m}' and return the JSON object per the contract."), None
    fg = flow_graph(d)
    body = (f"TARGET IP MODULE: {m}\n\n=== RTL (comments removed, blank lines left out; each line starts with its line "
            f"number in the source file) ===\n{rtl}\n\n=== RELATIONSHIP MAP: ELEMENTS AND RECORDS ===\n"
            + "\n".join(map_lines(d)) + "\n\n=== RELATIONSHIP MAP: FLOW GRAPH (computed by a program from the records above) ===\n"
            + "\n".join(flow_lines(fg)) +
            f"\n\nIdentify the primary security assets for '{m}' and return the JSON object per the contract.")
    return body, fg


# ------------------------------------------------------------------------------------------------ self-tests ---
def selftest(log=print) -> bool:
    ok = True
    # (1) hand-read: hwspinlock line 41 `if (rstn_i = '0') then`, line 43 `elsif rising_edge(clk_i) then`;
    #     the map's rstn_i occurrence 3 and clk_i occurrence 3 sit on them.
    t, _ = text("tuning", "neorv32_hwspinlock")
    L = numbered_lines(t.split("=== RELATIONSHIP MAP")[0])
    d = load_map("tuning", "neorv32_hwspinlock")
    occ = {(e["name"], o["id"]): o["line"] for a in ("ports", "signals") for e in d[a] for o in e["occurrences"]}
    for (n, i), (ln, want) in {("rstn_i", 3): (41, "if (rstn_i = '0') then"),
                               ("clk_i", 3): (43, "elsif rising_edge(clk_i) then")}.items():
        good = occ[(n, i)] == ln and L.get(ln) == want and f'"id":{i},"line":{ln}' in t
        ok &= good
        log(f"   hand-read {n} occurrence {i} -> line {ln} {L.get(ln)!r}: {'ok' if good else 'MISMATCH'}")
    # (2) hand-read flow (boot_rom lines 48, 60, 64-65): bus_req_i.addr SELECTS rdata (control); rdata SOURCES
    #     bus_rsp_o.data; bus_req_i.stb GATES rden; rden CARRIES bus_rsp_o.ack. So no data path from bus_req_i.addr,
    #     rden is driven only under control, and rdata reaches the exit bus_rsp_o.data.
    fg = flow_graph(load_map("tuning", "neorv32_boot_rom"))
    p = fg["paths"]
    good = ("clk_i" in fg["clock_reset"] and "rstn_i" in fg["clock_reset"] and "clk_i" not in p
            and "bus_req_i.addr" in p and p["bus_req_i.addr"]["stores"] == [] and p["bus_req_i.addr"]["exits"] == [])
    ok &= good
    log(f"   boot_rom flow: clock/reset {fg['clock_reset']}, bus_req_i.addr reaches stores {p.get('bus_req_i.addr', {}).get('stores')} "
        f"exits {p.get('bus_req_i.addr', {}).get('exits')} (hand-read: none, it only SELECTS): {'ok' if good else 'MISMATCH'}")
    # (2b) connection direction (hand-read RTL_data/neorv32_cpu.vhd line 335 `neorv32_cpu_alu_inst: entity
    #      neorv32.neorv32_cpu_alu`; that entity declares res_o as an output, clk_i as an input): in the cpu map the
    #      element wired to neorv32_cpu_alu_inst.res_o gets mode "out", the one wired to its clk_i gets mode "in".
    dc = load_map("tuning", "neorv32_cpu")
    got = {(c["instance"], c["formal"]): c.get("mode") for a in ("ports", "signals") for e in dc[a] for c in e.get("connections", []) or []}
    want = {("neorv32_cpu_alu_inst", "res_o"): "out", ("neorv32_cpu_alu_inst", "clk_i"): "in"}
    good = all(got.get(k) == v for k, v in want.items())
    left = sum(1 for v in got.values() if v is None)
    ok &= good
    log(f"   cpu connection directions: {[(k, got.get(k)) for k in want]}; still unknown {left} of {len(got)}: {'ok' if good else 'MISMATCH'}")
    # (3) every occurrence of every map element in every module: its recorded text is the numbered RTL line
    for split in ("tuning", "heldout"):
        n = bad = 0
        longest = 0
        for m in modules(split):
            d = load_map(split, m)
            t, _fg = text(split, m)
            longest = max(longest, max(len(l) for l in t.split("\n")))
            if d is None:
                continue
            L = numbered_lines(t.split("=== RELATIONSHIP MAP")[0])
            for a in ("ports", "signals"):
                for e in d[a]:
                    for o in e["occurrences"]:
                        n += 1
                        bad += L.get(o["line"]) != o["text"].strip()
        good = bad == 0 and longest <= MAXLEN
        ok &= good
        log(f"   {split}: {n - bad}/{n} occurrences on their numbered RTL line; longest input line {longest} (limit {MAXLEN}): "
            f"{'ok' if good else 'FAIL'}")
    return ok


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--out" in sys.argv:              # a new input version gets its own folder (m7e194es0ist2: traced_inputs_v2)
        OUT = HERE / sys.argv[sys.argv.index("--out") + 1]
    assert selftest(), "self-test failed: nothing written"
    for split in ("tuning", "heldout"):
        (OUT / split / "_flow").mkdir(parents=True, exist_ok=True)
        sizes = []
        for m in modules(split):
            t, fg = text(split, m)
            (OUT / split / f"{m}.txt").write_text(t, encoding="utf-8")
            if fg is not None:
                (OUT / split / "_flow" / f"{m}.json").write_text(json.dumps(fg, indent=1), encoding="utf-8")
            sizes.append((len(t), m))
        print(f"{split}: {len(sizes)} inputs, {sum(s for s, _ in sizes):,} chars, largest {max(sizes)[0]:,} ({max(sizes)[1]})")
