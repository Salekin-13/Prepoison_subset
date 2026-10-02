"""The relationship map as an input of the asset executor (Step 1b arm m7e194es0ismr).

The maps are the final JSON files written by the LAsset Step 1 run (lasset_step1.ipynb, cell 1c:
relation_stage.merge), one per module:

    step1/lasset_step1/relation_map/<relation prompt sha>/<module>.json

with <relation prompt sha> = a44eebd83bf7 (relation_prompts_v1/relation_system_prompt.md). Experiment E3 (prompt v2,
8406f390b729) writes the same format to step1/lasset_step1/relation_exp/E3_pairfirst_declaration/relation_map/
8406f390b729/<module>.json; this arm reads E3's maps (see REL_MAP_DIR). Only the 15 test modules have a map;
boot_rom, fifo and package get the "(none for this module)" block.

The executor gets a COMPACT view of each file: the per-element `occurrences` list (line text the RTL already holds)
and `partner_at` are dropped, and every Occurrence ID in `at` becomes its RTL line number (`lines`). Nothing else is
changed. The view is about a third of the file's size (bus: 287k characters instead of 728k).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REL_PROMPT_SHA = "8406f390b729"                                          # relation prompt v2 (experiment E3)
# E3 run 1 maps: the most accurate relation maps measured (bake-off 2026-09-30, astra gold set: typed precision ~0.98,
# recall ~0.90 over three E3 runs, against E0 ~0.93 / ~0.83). The E0 Step 1 maps stay at
# step1/lasset_step1/relation_map/a44eebd83bf7/<module>.json.
REL_MAP_DIR = ROOT / "step1" / "lasset_step1" / "relation_exp" / "E3_pairfirst_declaration" / "relation_map" / REL_PROMPT_SHA   # <-- the relation maps this arm reads
BLOCK = "=== RELATIONSHIP MAP ==="
NONE_TEXT = "(none for this module)"


def _lines(ids, line):
    ids = ids if isinstance(ids, list) else [ids]
    return sorted({line[a] for a in ids if a in line})


def compact(d: dict) -> dict:
    """The final map without occurrence lists; Occurrence IDs replaced by RTL line numbers; empty fields dropped."""
    out = {}
    for arr in ("ports", "signals"):
        rows = []
        for e in d.get(arr, []):
            line = {o["id"]: o["line"] for o in e.get("occurrences", [])}
            r = {k: v for k, v in e.items() if k != "occurrences" and v not in (None, [], {}, "")}
            if e.get("relationship"):
                r["relationship"] = [{**{k: v for k, v in x.items() if k not in ("at", "partner_at") and v not in (None, [], {}, "")},
                                      "lines": _lines(x.get("at", []), line)} for x in e["relationship"]]
            for key in ("configuration", "constant_drivers"):
                if r.get(key):
                    r[key] = [({**{k: v for k, v in c.items() if k != "at"}, "lines": _lines(c["at"], line)}
                               if isinstance(c, dict) and "at" in c else c) for c in r[key]]
            rows.append(r)
        out[arr] = rows
    return out


# The code-written maps (arm m7e194es0ismc): relationship by step1/code_pairs_v2.py (frozen sha b0e767000ec2),
# functionality from E3 run 1's answers; built by build_code_map_arm.py.
CODE_MAP_DIR = ROOT / "step1" / "lasset_step1" / "relation_map_code" / "b0e767000ec2_func-8406f390b729"   # <-- code maps


def map_path(stem: str, map_dir: Path | None = None) -> Path:
    return Path(map_dir or REL_MAP_DIR) / f"{stem}.json"


def map_text(stem: str, map_dir: Path | None = None) -> str:
    """The block body for one module: the compact map as JSON, or NONE_TEXT when no map was written for it."""
    p = map_path(stem, map_dir)
    if not p.exists():
        return NONE_TEXT
    return json.dumps(compact(json.loads(p.read_text(encoding="utf-8"))), separators=(",", ":"))


def build_user(stem: str, rtl: str, map_dir: Path | None = None) -> str:
    """meta_tools.build_user with the map block between the RTL and the closing instruction."""
    return (f"TARGET IP MODULE: {stem}\n\n=== RTL ===\n{rtl}\n\n{BLOCK}\n{map_text(stem, map_dir)}\n\n"
            f"Identify the primary security assets for '{stem}' and return the JSON object per the contract.")


def make_build(map_dir: Path):
    """build_user bound to one map folder (for meta_tools.run_version(build=...))."""
    return lambda stem, rtl: build_user(stem, rtl, map_dir)
