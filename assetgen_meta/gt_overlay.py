"""Ground-truth overlay: the two reference names that do not exist in the RTL the generator is given.

The reference list (ground_truth/manual_gt_neorv32.json, read by eval_assets.load_refs) was written against a NEORV32
version other than the evaluated one for neorv32_cache. 109 of its 111 names are in RTL_data; two are not:

  inval_i           renamed. The older source in neorv32/rtl/core/neorv32_cache.vhd (hw_version 01.11.00.06) declares
                    `inval_i : in std_ulogic` ("make accessed block invalid") and tests `if (inval_i = '1')`. The evaluated
                    RTL_data/neorv32_cache.vhd (hw_version 01.11.04.03) declares `inv_i : in std_ulogic` ("invalidate
                    accessed block", lines 65 and 325) and tests `elsif (inv_i = '1')` (line 382). Same port, new name.
  cache_o.cmd_dir   no counterpart. RTL_data's cache_o record has cmd_clr, cmd_inv, cmd_new only; the older source has no
                    `cmd_dir` either (its matches are `cache_cmd_dirty`). Nothing in the evaluated RTL can be credited.

The reference file is NOT edited. corrected() returns a copy with the rename applied and the name without a counterpart
removed (110 entries). Report both: the original keeps every earlier number comparable; the corrected one is the
recall that is reachable on the evaluated RTL.
"""
from __future__ import annotations

OVERLAY = {
    "neorv32_cache": {
        "rename": {"inval_i": "inv_i"},
        "no_counterpart": ["cache_o.cmd_dir"],
    },
}


def corrected(gt: dict) -> dict:
    """{module: [(name, objective)]} with the overlay applied. Raises if the overlay no longer fits the reference."""
    out = {m: list(rows) for m, rows in gt.items()}
    for m, ov in OVERLAY.items():
        names = [n for n, _o in out[m]]
        for old, new in ov.get("rename", {}).items():
            assert old in names and new not in names, f"{m}: rename {old} -> {new} does not fit the reference"
        for n in ov.get("no_counterpart", []):
            assert n in names, f"{m}: {n} is not in the reference"
        out[m] = [(ov.get("rename", {}).get(n, n), o) for n, o in out[m] if n not in ov.get("no_counterpart", [])]
    return out


def report(versions, log=print) -> dict:
    """Mean precision / recall of each version's runs, on the modules all of them finished, under both references."""
    import eval_assets as ea
    gt = ea.load_refs()["gt"]; gc = corrected(gt)
    runs = ea.collect(list(versions)); common = ea.common_modules(runs, gt)
    n0, n1 = sum(len(gt[m]) for m in common), sum(len(gc[m]) for m in common)
    log(f"reference entries on the {len(common)} common modules: original {n0}, corrected {n1}")
    out = {}
    for v in versions:
        row = {}
        for tag, ref in (("original", gt), ("corrected", gc)):
            sc = [ea.score(r, ref, strict=True, only=common) for r in runs[v]]
            row[tag] = (sum(s["precision"] for s in sc) / len(sc), sum(s["recall"] for s in sc) / len(sc), len(sc))
        out[v] = row
        log(f"   {v:15s} original P {row['original'][0]:.3f} R {row['original'][1]:.3f} | corrected P "
            f"{row['corrected'][0]:.3f} R {row['corrected'][1]:.3f}   ({row['original'][2]} runs)")
    return out


if __name__ == "__main__":
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "assetgen_meta"))
    import json, os
    os.chdir(ROOT)
    import eval_assets as ea, rel_view as rv
    gt = ea.load_refs()["gt"]; gc = corrected(gt)
    # self-test: the rename target is a declared element of the evaluated RTL, the dropped name is not
    d = json.loads(rv.map_path("neorv32_cache", rv.CODE_MAP_DIR).read_text(encoding="utf-8"))
    names = {e["name"] for a in ("ports", "signals") for e in d[a]}
    assert "inv_i" in names and "inval_i" not in names and "cache_o.cmd_dir" not in names
    assert sum(map(len, gt.values())) - sum(map(len, gc.values())) == 1
    assert ("inv_i", "Availability") in gc["neorv32_cache"]
    print("overlay self-test PASS")
    report(sys.argv[1:] or ["v2x3r8", "m7e194es0c", "m7e194es0ism", "m7e194es0ismr"])
