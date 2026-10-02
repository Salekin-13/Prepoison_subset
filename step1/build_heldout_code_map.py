"""Code-only relation maps for modules that have no LLM occurrence profile (the 26 held-out modules). No model call.

Per module:
  1. closed set       held-out: parsed_heldout26/<module>.json (written here by rtl_parse, in the parsed_tuning18 format),
                      regrouped by entity. Tuning: the Step 1 closed set step1/lasset_step1/closed_set/<module>.json, which
                      is what the stored tuning maps were built from.
  2. occurrence rows  the v3b profiler's own code extract: build_jobs -> code_inventory (occurrence_matches, then the
                      tree-sitter structure stage for Context and Path). The builder's program cells run exactly as
                      lasset_step1.Profiler runs them, minus the API-key, client and rulebook cells (none of them is
                      read by the extract).
  3. SITE tags        step1/code_site_tags.py (code; replaces the profiler's LLM classify / validate calls)
  4. relationships    step1/code_pairs_v2.code_pairs (frozen, sha256[:12] b0e767000ec2)
  5. final map        relation_stage.merge, with `functionality` left empty (no lever reads it)

Output
  step1/lasset_step1/relation_map_code_heldout/b0e767000ec2_codetags/<module>.json         the map (26 held-out modules)
  step1/lasset_step1/relation_map_code_heldout/b0e767000ec2_codetags/_sites/<module>.json  {entity: {element: {occ id: [SITE]}}}
  step1/lasset_step1/relation_map_code_tuning/b0e767000ec2_codetags/...                   the same for the 15 tuning
                                                                                            modules (self-test (b))
  parsed_heldout26/<module>.json                                                            the held-out closed sets
merge() must write under the repo root: its log line calls relative_to(repo root).

Self-tests, in this order; nothing is written to the held-out map folder if one fails:
  (a) closed set: the rtl_parse route reproduces parsed_tuning18/neorv32_wdt.json (entity, name, dir, type, in order);
      neorv32_gpio's ports and signals equal the hand-read lines 22-28 and 44-49 of RTL_heldout/neorv32_gpio.vhd; every
      held-out file equals the copy step2/build_heldout_parse.py wrote to parsed_tuning18/, and its base elements equal
      parsed_heldout_raw/ (that folder was parsed without the package's record types, so it has no record fields).
      Then parsed_heldout26/ is written.
  (t) the code SITE tagger on its hand-read lines (code_site_tags.selftest; 4 modules, 2 held-out).
  (b) the 15 tuning maps rebuilt from code tags equal rel_view.CODE_MAP_DIR on entity, name, boundary, storage,
      occurrences (id, line) and relationship (type, targets, at), element by element.
  (c) after the build: hand-read facts of the held-out gpio map (storage, boundary, relationships), RTL only.

CLI (from anywhere):  python step1/build_heldout_code_map.py            self-tests, then build the 26 held-out maps
                      python step1/build_heldout_code_map.py --selftest  self-tests only
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
import time
from collections import Counter
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BPA = ROOT / "bahavioral_patterns_of_assets"
BUILDER = BPA / "annotation_pack_elements/occurrence_prompts_v2/rulebook_edits"
for _p in (str(ROOT), str(ROOT / "assetgen_meta"), str(HERE), str(BUILDER)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Imported before the builder cells run, so every later import resolves to the repo-root copies, as in the prototypes.
import code_pairs_v2 as V          # noqa: E402
import relation_stage as RS        # noqa: E402
import lasset_step1 as S           # noqa: E402
import code_site_tags as CT        # noqa: E402

CODE_PAIRS_SHA = "b0e767000ec2"
TUNE_RTL, HELD_RTL, BPA_RTL = ROOT / "data/RTL_data", ROOT / "data/RTL_heldout", BPA / "data/RTL_data"
PARSED_TUNING, PARSED_HELDOUT, PARSED_RAW = ROOT / "data/parsed_tuning18", ROOT / "data/parsed_heldout26", ROOT / "data/parsed_heldout_raw"
MAP_HELDOUT = HERE / "lasset_step1" / "relation_map_code_heldout" / f"{CODE_PAIRS_SHA}_codetags"
MAP_TUNING = HERE / "lasset_step1" / "relation_map_code_tuning" / f"{CODE_PAIRS_SHA}_codetags"
SITES_SUBDIR = "_sites"


@contextlib.contextmanager
def _at(path):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


# ------------------------------------------------------------------------------------------------ module lists ---
def tuning_modules() -> list[str]:
    """The 15 tuning modules with GT (lasset_step1.test_modules)."""
    return S.test_modules()


def heldout_modules(rtl_dir: Path = HELD_RTL) -> list[str]:
    """The RTL_heldout modules that have manual GT. Only the module NAMES are read from the GT file."""
    gt = json.loads((ROOT / "data/ground_truth/manual_gt_neorv32.json").read_text(encoding="utf-8"))["modules"]
    mods = sorted(p.stem for p in Path(rtl_dir).glob("*.vhd") if p.stem in gt)
    assert len(mods) == 26, f"expected 26 held-out modules, found {len(mods)}"
    return mods


# ---------------------------------------------------------------------------------------------- 1. closed set ---
def _flatten(stem: str, parsed: dict) -> dict:
    """step2/build_heldout_parse.flatten: per-entity parse -> the parsed_tuning18 format."""
    ports, signals, ents = [], [], []
    for e in parsed["entities"]:
        ents.append(e["entity"])
        ports += [{"entity": e["entity"], **p} for p in e.get("ports", [])]
        signals += [{"entity": e["entity"], **s} for s in e.get("signals", [])]
    return {"module": stem, "entities": ents, "ports": ports, "signals": signals}


@lru_cache(maxsize=1)
def _registry():
    """Record types from the whole corpus: they live in neorv32_package.vhd (RTL_data), and held-out ports use them."""
    import rtl_parse
    return rtl_parse.build_record_registry(sorted(TUNE_RTL.glob("*.vhd")) + sorted(HELD_RTL.glob("*.vhd")))


def parse_closed(stem: str, rtl_dir: Path) -> dict:
    import rtl_parse
    return _flatten(stem, rtl_parse.parse_rtl_file(str(Path(rtl_dir) / f"{stem}.vhd"), _registry()))


def write_closed_sets(modules, rtl_dir: Path = HELD_RTL, out_dir: Path = PARSED_HELDOUT) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    n = Counter()
    for m in modules:
        d = parse_closed(m, rtl_dir)
        (out_dir / f"{m}.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
        n["modules"] += 1; n["ports"] += len(d["ports"]); n["signals"] += len(d["signals"])
    return dict(n)


def load_closed(m: str, parsed_dir: Path | None) -> list[tuple[str, list[dict]]]:
    """[(entity, [element dict])] in closed-set order. parsed_dir None: the Step 1 closed set (tuning modules)."""
    if parsed_dir is None:
        d = json.loads((S.CLOSED / f"{m}.json").read_text(encoding="utf-8"))
        return [(e["entity"], e["ports"] + e["signals"]) for e in d["entities"]]
    d = json.loads((Path(parsed_dir) / f"{m}.json").read_text(encoding="utf-8"))
    by = {e: [] for e in d["entities"]}
    for x in d["ports"] + d["signals"]:
        by.setdefault(x["entity"], []).append({k: x[k] for k in ("name", "dir", "type") if k in x})
    return [(e, v) for e, v in by.items() if v]


# -------------------------------------------------------------------------------------- 2. the profiler's extract ---
@lru_cache(maxsize=1)
def builder() -> dict:
    """The v3b builder's program cells (setup, prompts, inputs, checks) in one namespace, as lasset_step1.Profiler
    runs them; the API-key, client and rulebook cells are not run."""
    import build_occurrence_notebook_v3b as B
    g = {"__name__": "code_map_profiler"}
    buf = io.StringIO()
    with _at(B.ROOT), contextlib.redirect_stdout(buf):
        exec(B.C_SETUP, g)
        g["OUT_DIR"] = S.PROFILES
        g["PROMPT_DIR"] = g["ELEM_DIR"] / S.PROMPT_VERSION
        g["RULEBOOK_FILE"] = g["PROMPT_DIR"] / "rulebook.json"
        for c in (B.C_PROMPTS, B.C_INPUTS):
            exec(c, g)
        g["MODULES"] = {}
        exec(B.C_CHECKS, g)
    g["_setup_log"], g["_B"] = buf.getvalue(), B
    if not g.get("SELFTEST_OK"):
        raise AssertionError("the v3b builder's own self-tests failed:\n" + g["_setup_log"][-2000:])
    return g


class Source:
    """Where one module's inputs come from: its RTL folder and its closed set (parsed_dir None = Step 1 closed set)."""

    def __init__(self, rtl_dir: Path, parsed_dir: Path | None):
        self.rtl_dir, self.parsed_dir = Path(rtl_dir), (Path(parsed_dir) if parsed_dir else None)

    def run(self, m: str, fn):
        g = builder()
        keep = g["load_elements"], g["RTL_DIR"]
        g["load_elements"], g["RTL_DIR"] = (lambda mod: load_closed(mod, self.parsed_dir)), self.rtl_dir
        try:
            with _at(g["_B"].ROOT):
                return fn(g)
        finally:
            g["load_elements"], g["RTL_DIR"] = keep


TUNING = Source(BPA_RTL, None)          # the profiler's own RTL folder (byte-identical to RTL_data/, checked in selftest)
HELDOUT = Source(HELD_RTL, PARSED_HELDOUT)


def extract(m: str, src: Source) -> tuple[dict, dict]:
    """-> (rows, cols). rows {(entity, element, occ id): inventory row with Context and Path};
    cols {(entity, element, occ id): (line, column in the numbered line text, name as written)}."""
    def f(g):
        rows, cols = {}, {}
        for j in g["build_jobs"]([m]):
            L = g["source_lines"](j["src"])
            for e in j["elems"]:
                for k, (ln, col, w) in enumerate(g["occurrence_matches"](L, e["name"]), 1):
                    cols[(j["entity"], e["name"], k)] = (ln, col, w)
            for n, rs in g["code_inventory"](j).items():
                for r in rs:
                    rows[(j["entity"], n, r["Occurrence ID"])] = dict(r)
        return rows, cols
    return src.run(m, f)


def entities(m: str, src: Source, tagger=CT.tagger) -> list[dict]:
    """relation_stage.load_module's entity format built by code: rows from the profiler's code extract, SITE tags from
    `tagger(E, cols)` (None leaves 'SITE Tagged' empty)."""
    g = builder()
    rows, cols = extract(m, src)
    out = []
    for ent, els in load_closed(m, src.parsed_dir):
        with _at(g["_B"].ROOT):
            text = g["numbered_entity_source"](src.rtl_dir / f"{m}.vhd", ent)
        prof = {}
        for e in els:
            rs = sorted((r for (en, n, _i), r in rows.items() if en == ent and n == e["name"]), key=lambda r: r["Occurrence ID"])
            prof[e["name"]] = [{**r, "SITE Tagged": [], "Role": "code"} for r in rs]
        E = {"module": m, "entity": ent, "src": text, "profile": prof, "missing_site": 0,
             "ports": [{"name": e["name"], "dir": e.get("dir"), "type": e.get("type")} for e in els if e.get("dir")],
             "signals": [{"name": e["name"], "type": e.get("type")} for e in els if not e.get("dir")]}
        if tagger is not None:
            tags = tagger(E, {k[1:]: v for k, v in cols.items() if k[0] == ent})
            for n, rs in prof.items():
                for r in rs:
                    r["SITE Tagged"] = list(tags.get((n, r["Occurrence ID"]), []))
        out.append(E)
    return out


# ------------------------------------------------------------------------------------------- 3-5. map building ---
def code_records(ents) -> dict:
    """{entity: [(Y, y_id, TYPE, X, None)]}, both sides of every code_pairs_v2 pair (as relation_stage expects)."""
    return {e["entity"]: sorted({r for y, yi, x, xi, t in V.code_pairs(e) for r in ((y, yi, t, x, None), (x, xi, RS.MIRROR[t], y, None))},
                                key=str) for e in ents}


def build_module(m: str, src: Source, out_dir: Path) -> dict:
    """Write <out_dir>/<m>.json and <out_dir>/_sites/<m>.json. -> per-module counts."""
    ents = entities(m, src)
    out_dir = Path(out_dir)
    RS.merge(m, {"prompt_sha": f"{CODE_PAIRS_SHA}_codetags", "records": code_records(ents), "functionality": {}},
             ents=ents, out_dir=out_dir, log=lambda *a: None)
    sites = {E["entity"]: {n: {str(r["Occurrence ID"]): r["SITE Tagged"] for r in rs} for n, rs in E["profile"].items()}
             for E in ents}
    (out_dir / SITES_SUBDIR).mkdir(parents=True, exist_ok=True)
    (out_dir / SITES_SUBDIR / f"{m}.json").write_text(json.dumps(sites, indent=1), encoding="utf-8")
    d = json.loads((out_dir / f"{m}.json").read_text(encoding="utf-8"))
    els = [e for a in ("ports", "signals") for e in d[a]]
    allrows = [r for E in ents for rs in E["profile"].values() for r in rs]
    site_of = {(E["entity"], n): {s for r in rs for s in r["SITE Tagged"]} for E in ents for n, rs in E["profile"].items()}
    fields = [e for e in d["signals"] if "." in e["name"]]
    return {"entities": len(ents), "elements": len(els), "rows": len(allrows),
            "rows untagged": sum(1 for r in allrows if not r["SITE Tagged"]),
            "rows in a selected signal assignment": sum(1 for r in allrows if "with select" in (r.get("Context") or "")),
            "rows the structure stage could not place": sum(1 for r in allrows if (r.get("Context") or "").startswith("none")),
            "relationship records (file entries)": sum(len(e["relationship"]) for e in els),
            "relationship triples (type, target, occurrence)": sum(len(r["targets"]) * len(r["at"]) for e in els for r in e["relationship"]),
            "internal record fields": len(fields),
            "internal record fields in a condition": sum(bool(site_of.get((e["entity"], e["name"]), set()) & CT.COND) for e in fields),
            "whole input ports": sum(1 for e in d["ports"] if "." not in e["name"] and (e.get("boundary") or {}).get("mode") == "in")}


def load_sites(m: str, map_dir: Path) -> dict:
    """{(entity, element): set of SITE tags over all its occurrence rows} from <map_dir>/_sites/<m>.json."""
    d = json.loads((Path(map_dir) / SITES_SUBDIR / f"{m}.json").read_text(encoding="utf-8"))
    return {(ent, n): {s for tags in occ.values() for s in tags} for ent, els in d.items() for n, occ in els.items()}


# ------------------------------------------------------------------------------------------------- self-tests ---
# Hand-read on 2026-10-01 from RTL_heldout/neorv32_gpio.vhd: ports lines 22-28, signals lines 44-49.
GPIO_PORTS = [("clk_i", "in", "std_ulogic"), ("rstn_i", "in", "std_ulogic"), ("bus_req_i", "in", "bus_req_t"),
              ("bus_rsp_o", "out", "bus_rsp_t"), ("gpio_o", "out", "std_ulogic_vector(31 downto 0)"),
              ("gpio_i", "in", "std_ulogic_vector(31 downto 0)"), ("cpu_irq_o", "out", "std_ulogic")]
GPIO_SIGNALS = ["port_in", "port_out", "irq_typ", "irq_pol", "irq_en", "irq_clrn", "port_in2", "irq_trig", "irq_pend"]


def selftest_closed(log=print) -> bool:
    import rtl_parse  # noqa: F401  (repo-root copy; byte-identical to the pack's, checked below)
    fails = []
    if (ROOT / "src/rtl_parse.py").read_bytes() != (BPA / "rtl_parse.py").read_bytes():
        fails.append("rtl_parse.py differs between the repo root and the pack")
    diff_rtl = [p.name for p in TUNE_RTL.glob("*.vhd") if p.read_bytes() != (BPA_RTL / p.name).read_bytes()]
    if diff_rtl or len(list(TUNE_RTL.glob("*.vhd"))) != 18:
        fails.append(f"RTL_data and the pack's RTL differ: {diff_rtl}")
    # the tuning file also carries 'function' / 'kind' notes from an older LLM parse; the closed set is entity, name,
    # dir and type, in order
    key = lambda d: [(x["entity"], x["name"], x.get("dir"), x.get("type")) for x in d["ports"] + d["signals"]]
    ref = json.loads((PARSED_TUNING / "neorv32_wdt.json").read_text(encoding="utf-8"))
    if key(parse_closed("neorv32_wdt", TUNE_RTL)) != key(ref):
        fails.append("rtl_parse route does not reproduce parsed_tuning18/neorv32_wdt.json (entity, name, dir, type)")
    g = parse_closed("neorv32_gpio", HELD_RTL)
    if [(p["name"], p["dir"], p["type"]) for p in g["ports"] if "." not in p["name"]] != GPIO_PORTS:
        fails.append(f"gpio ports differ from hand-read lines 22-28: {[p['name'] for p in g['ports'] if '.' not in p['name']]}")
    if [s["name"] for s in g["signals"]] != GPIO_SIGNALS:
        fails.append(f"gpio signals differ from hand-read lines 44-49: {[s['name'] for s in g['signals']]}")
    if not {"bus_req_i.addr", "bus_req_i.stb", "bus_rsp_o.ack", "bus_rsp_o.data"} <= {p["name"] for p in g["ports"]}:
        fails.append("gpio record ports did not expand into fields")
    same_t18 = same_raw = 0
    held = heldout_modules()
    for m in held:
        d = parse_closed(m, HELD_RTL)
        same_t18 += d == json.loads((PARSED_TUNING / f"{m}.json").read_text(encoding="utf-8"))
        # parsed_heldout_raw was parsed without the package's record types, so it lacks record fields; compare the
        # base elements (names without '.') with their dir and type
        raw = json.loads((PARSED_RAW / f"{m}.json").read_text(encoding="utf-8"))
        a = sorted((x["entity"], x["name"], x.get("dir"), x.get("type")) for x in d["ports"] + d["signals"] if "." not in x["name"])
        b = sorted((e["entity"], x["name"], x.get("dir"), x.get("type")) for e in raw["entities"]
                   for x in e["ports"] + e["signals"] if "." not in x["name"])
        same_raw += a == b
    if same_t18 != len(held) or same_raw != len(held):
        fails.append(f"held-out closed sets: equal to parsed_tuning18 copy {same_t18}/{len(held)}, "
                     f"base names equal to parsed_heldout_raw {same_raw}/{len(held)}")
    log(f"   (a) closed set: wdt reproduced; gpio = hand-read lines 22-28 / 44-49; held-out files equal to the "
        f"parsed_tuning18 copy {same_t18}/{len(held)}, base names equal to parsed_heldout_raw {same_raw}/{len(held)}: "
        f"{'PASS' if not fails else 'FAIL ' + str(fails)}")
    return not fails


MAP_KEYS = ("entity", "name", "boundary", "storage")


def _rel_key(e):
    return sorted((r["type"], tuple(r["targets"]), tuple(r["at"])) for r in e.get("relationship", []))


def compare_maps(a: dict, b: dict) -> Counter:
    """Element-by-element agreement of two map files on entity, name, boundary, storage, occurrences, relationship."""
    c = Counter()
    for arr in ("ports", "signals"):
        c["count differs"] += len(a[arr]) != len(b[arr])
        for x, y in zip(a[arr], b[arr]):
            c["elements"] += 1
            same_f = all(x.get(k) == y.get(k) for k in MAP_KEYS)
            same_o = [(o["id"], o["line"]) for o in x["occurrences"]] == [(o["id"], o["line"]) for o in y["occurrences"]]
            same_r = _rel_key(x) == _rel_key(y)
            c["entity/name/boundary/storage equal"] += same_f
            c["occurrences equal"] += same_o
            c["relationship equal"] += same_r
            c["all equal"] += same_f and same_o and same_r
    return c


def selftest_tuning_maps(log=print) -> bool:
    import rel_view as rv
    tot = Counter()
    for m in tuning_modules():
        build_module(m, TUNING, MAP_TUNING)
        tot += compare_maps(json.loads((MAP_TUNING / f"{m}.json").read_text(encoding="utf-8")),
                            json.loads(rv.map_path(m, rv.CODE_MAP_DIR).read_text(encoding="utf-8")))
    ok = tot["all equal"] == tot["elements"] and tot["count differs"] == 0 and tot["elements"] > 0
    log(f"   (b) 15 tuning maps rebuilt from code tags vs rel_view.CODE_MAP_DIR: all six fields equal on "
        f"{tot['all equal']}/{tot['elements']} elements (entity/name/boundary/storage {tot['entity/name/boundary/storage equal']}, "
        f"occurrences {tot['occurrences equal']}, relationship {tot['relationship equal']}); element-count mismatches "
        f"{tot['count differs']}: {'PASS' if ok else 'FAIL'}")
    return ok


def selftest_heldout_gpio(out_dir: Path, log=print) -> bool:
    """Hand-read facts of RTL_heldout/neorv32_gpio.vhd, checked on the built map (no ground truth involved).
    L59 port_out reset arm, L74 port_out <= bus_req_i.data(GPIO_NUM-1 downto 0) under rising_edge (L64): storage edge.
    L111-112 gpio_o assigned in the combinational process output_stage: storage none; gpio_o boundary out, driven.
    L103 port_in <= gpio_i(GPIO_NUM-1 downto 0): a slice as the whole right-hand side -> gpio_i SOURCES port_in.
    L104 port_in2 <= port_in: the whole right-hand side -> port_in CARRIES port_in2, and port_in2 COPIES port_in.
    L57/L64 the clocked processes: port_in2 CLOCKED_BY clk_i."""
    d = json.loads((Path(out_dir) / "neorv32_gpio.json").read_text(encoding="utf-8"))
    el = {e["name"]: e for a in ("ports", "signals") for e in d[a]}
    line = lambda n: {o["id"]: o["line"] for o in el[n]["occurrences"]}

    def has(n, typ, target, at_line):
        return any(r["type"] == typ and target in r["targets"] and any(line(n)[i] == at_line for i in r["at"])
                   for r in el[n]["relationship"])
    checks = {"port_out storage edge": el["port_out"]["storage"] == "edge",
              "gpio_o storage none": el["gpio_o"]["storage"] == "none",
              "gpio_o boundary out/driven": el["gpio_o"]["boundary"] == {"mode": "out", "drive": "driven"},
              "gpio_i boundary in": el["gpio_i"]["boundary"]["mode"] == "in",
              "gpio_i SOURCES port_in at L103": has("gpio_i", "SOURCES", "port_in", 103),
              "port_in CARRIES port_in2 at L104": has("port_in", "CARRIES", "port_in2", 104),
              "port_in2 COPIES port_in at L104": has("port_in2", "COPIES", "port_in", 104),
              "port_in2 CLOCKED_BY clk_i": any(r["type"] == "CLOCKED_BY" and "clk_i" in r["targets"] for r in el["port_in2"]["relationship"]),
              "functionality empty": all(e["functionality"] == "" for e in el.values())}
    bad = [k for k, v in checks.items() if not v]
    log(f"   (c) held-out gpio map, {len(checks)} hand-read facts: {'PASS' if not bad else 'FAIL ' + str(bad)}")
    return not bad


def selftest(log=print) -> bool:
    """(a) closed set; then parsed_heldout26/ is written (the tagger's held-out hand-read lines need it); the tagger's
    hand-read lines (code_site_tags.selftest); (b) the tuning maps."""
    log("build_heldout_code_map self-tests:")
    if not selftest_closed(log):
        return False
    n = write_closed_sets(heldout_modules())
    log(f"   wrote {PARSED_HELDOUT.relative_to(ROOT)}/: {n['modules']} modules, {n['ports']} ports, {n['signals']} signals")
    return CT.selftest(log) and selftest_tuning_maps(log)


def build_heldout(log=print) -> dict:
    """Self-tests (a), tagger, (b); then the 26 held-out maps; then self-test (c)."""
    if not selftest(log):
        log("SELF-TEST FAIL: nothing is written to the held-out map folder")
        return {}
    held = heldout_modules()
    t0, per, tot = time.time(), {}, Counter()
    for m in held:
        per[m] = build_module(m, HELDOUT, MAP_HELDOUT)
        tot.update(per[m])
    if not selftest_heldout_gpio(MAP_HELDOUT, log):
        log("SELF-TEST (c) FAIL: the held-out maps were written but must not be used")
        return {}
    log(f"   held-out maps: {len(held)} modules in {time.time() - t0:.0f} s -> {MAP_HELDOUT.relative_to(ROOT)}")
    for k, v in tot.items():
        log(f"      {k:50s} {v:>7,}")
    (MAP_HELDOUT.parent / f"{MAP_HELDOUT.name}_build_summary.json").write_text(
        json.dumps({"modules": held, "totals": dict(tot), "per_module": per}, indent=1), encoding="utf-8")
    return {"totals": dict(tot), "per_module": per}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--selftest" in sys.argv[1:]:
        sys.exit(0 if selftest() else 1)
    sys.exit(0 if build_heldout() else 1)
