"""Step 1 deliverable: the code-only relation map for the 15 ground-truth modules. No LLM, no API calls.

Two readers, both self-tested against hand-read RTL lines before anything is written:
  relmap_reader.py  - a token-level walker: container, driven_by, drives, controls, controlled_by, copy_only,
                      clock, reset, fanout, in_port_map, multiple_drivers, under_generate, unknown.
                      Self-test: 34 assertions over wdt, cpu_cp_muldiv, bus and cpu_pmp.
  rtl_features.py   - the statement reader used in the earlier error analysis: read_in_condition (which also counts
                      `when ... else` conditions, a construct the walker does not treat as a branch), only_relay,
                      relay_sources, n_computed, n_assigned. Self-test: hand-read lines of wdt and trng.
Both are merged per element so that later steps read one file per module.

KNOWN LIMITS, carried in the output rather than hidden:
  - `controlled_by` from the walker misses `when ... else` conditions; the merged field `read_in_condition` covers them.
  - A connection into an instantiated sub-block is recorded as in_port_map, not as `drives`.
  - A whole record's row does not aggregate its fields' relations; container.fields lists the children instead.
  - Elements the walker could not resolve carry a reason in `unknown`.

Usage: python step1/build_relation_map.py          -> writes step1/relation_map/<module>.json and prints coverage.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
import relmap_reader as W      # noqa: E402
import rtl_features as F       # noqa: E402

OUT = HERE / "relation_map"
FEATURE_KEYS = ("read_in_condition", "only_relay", "relay_sources", "n_computed", "n_assigned")


def row(n, e, r, elems):
    """One published element row (the prototype's emit shape) plus the merged statement features."""
    base = n.rsplit(".", 1)[0] if "." in n else None
    driven = bool(r["driven_by"]) or r["stmts"] > 0
    shapes = dict(r["shapes"])
    copy_only = None if not driven else (bool(shapes) and all(k in ("copy", "record") for k in shapes)
                                         and not r["controlled_by"])
    return {
        "name": n, "kind": e["kind"], "dir": e.get("dir"), "type": e["type"],
        "container": {"parent": base, "field": n.rsplit(".", 1)[1] if base else None,
                      "fields": sorted(x.rsplit(".", 1)[1] for x in elems if x.startswith(n + "."))},
        "driven_by": [{"name": k, "line": v} for k, v in sorted(r["driven_by"].items())],
        "drives": [{"name": k, "line": v} for k, v in sorted(r["drives"].items())],
        "controls": [{"name": k, "line": v[0], "site": v[1]} for k, v in sorted(r["controls"].items())],
        "controlled_by": [{"name": k, "line": v[0], "site": v[1]} for k, v in sorted(r["controlled_by"].items())],
        "under_generate": sorted(r["gen"]),
        "copy_only": copy_only, "rhs_shapes": shapes, "fanout": W.fanout_verdict(r),
        "clock": sorted(r["clock"]), "reset": sorted(r["reset"]),
        "n_driver_stmts": r["stmts"], "multiple_drivers": r["stmts"] > 1, "in_port_map": r["inst_driven"],
        "unknown": sorted(set((["no_internal_driver"] if not driven else [])
                              + (["driver_via_instance_port_map"] if r["inst_driven"] and not driven else [])
                              + (["rhs_names_outside_closed_set"] if r["unresolved_rhs"] else []))),
    }


def build_module(stem: str) -> dict:
    mods, _ = W.build(stem)
    rtl = ROOT / f"RTL_data/{stem}.vhd"
    out = {"schema": "relation-map-v1", "module": stem, "source": f"RTL_data/{stem}.vhd",
           "closed_set": f"parsed_tuning18/{stem}.json", "entities": {}}
    for ent, (elems, rec) in mods.items():
        dirs = {n: e.get("dir", "") for n, e in elems.items() if e.get("kind") == "port"}
        feats = F.module_features(str(rtl), sorted(elems), dirs)[0]
        rows = []
        for n, e in sorted(elems.items()):
            x = row(n, e, rec[n], elems)
            ft = feats.get(n, {})
            x["features"] = {k: ft.get(k) for k in FEATURE_KEYS}
            rows.append(x)
        out["entities"][ent] = rows
    return out


def main():
    W._selftest(); F.selftest()
    OUT.mkdir(exist_ok=True)
    tot = filled = fields = cond = copies = 0
    for stem in W.GT15:
        d = build_module(stem)
        (OUT / f"{stem}.json").write_text(json.dumps(d, indent=1, default=sorted), encoding="utf-8")
        for rows in d["entities"].values():
            for r in rows:
                con = r.get("container") or {}
                ft = r.get("features") or {}
                tot += 1
                filled += bool(any(r.get(k) for k in ("driven_by", "drives", "controls", "controlled_by", "clock", "reset"))
                               or con.get("parent") or con.get("fields"))
                fields += bool(con.get("parent"))
                cond += bool(ft.get("read_in_condition"))
                copies += bool(ft.get("only_relay"))
    print(f"wrote {len(W.GT15)} files to {OUT}")
    print(f"elements {tot} (exact) | at least one relation filled {filled} ({filled/tot:.1%}) | record fields {fields} "
          f"({fields/tot:.1%}) | read in a condition {cond} ({cond/tot:.1%}) | pure copies {copies} ({copies/tot:.1%})")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
