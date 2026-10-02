"""Step 2: apply the frozen relation rules (step2/RULES.md) to stored asset lists and score. No LLM, no API calls.

Every fact comes from step1/relation_map/<module>.json. Usage:
    python step2/apply_rules.py [version ...]      default: the Step 1b winner and its two comparisons
"""
from __future__ import annotations

import json, re, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "assetgen_meta"))
import eval_assets as ea      # noqa: E402
import meta_tools as mt       # noqa: E402

MAP_DIR = ROOT / "step1/relation_map"
CLOCK_RESET_FUNCTION = {"neorv32_sys"}          # the only module here whose function is reset/clock control
TXN = re.compile(r"\bbus_(req|rsp)_t\b")


def load_map(module: str) -> dict:
    """element name -> merged relation row (entities flattened; a name declared twice keeps the richer row)."""
    p = MAP_DIR / f"{module}.json"
    if not p.exists():
        return {}
    out = {}
    for rows in json.loads(p.read_text(encoding="utf-8"))["entities"].values():
        for r in rows:
            cur = out.get(r["name"])
            if cur is None or len(json.dumps(r)) > len(json.dumps(cur)):
                out[r["name"]] = r
    return out


def source_of(row) -> str | None:
    """The single element this one is a plain copy of, when no condition reads it."""
    f = row.get("features") or {}
    src = [s for s in (f.get("relay_sources") or "").split(";") if s]
    if f.get("only_relay") and len(src) == 1 and not f.get("read_in_condition"):
        return src[0].split("(")[0].strip()
    return None


# ---- the frozen rules. Each takes (map, reported list) -> kept list.
def r1_carrier_copy(M, lst):
    names = {x[1] for x in lst}
    out = []
    for x in lst:
        row = M.get(x[1])
        s = source_of(row) if row else None
        if not s or row.get("kind") == "port":
            out.append(x); continue
        if s in names:
            continue                                   # its source is already reported
        out.append((x[0], s, x[2])); names.add(s)      # report the source instead
    return out


def r2_carrier_field(M, lst):
    keep = []
    for x in lst:
        row = M.get(x[1]); f = (row or {}).get("features") or {}
        inert = ("." in x[1] and row is not None and not f.get("read_in_condition")
                 and (f.get("n_computed") or 0) == 0)
        if not inert:
            keep.append(x)
    return keep


def r3_port_forwarding(M, lst):
    names = {x[1] for x in lst}
    keep = []
    for x in lst:
        row = M.get(x[1])
        s = source_of(row) if row else None
        src_row = M.get(s) if s else None
        if s and src_row and src_row.get("kind") == "port" and s in names and row.get("kind") != "port":
            continue
        keep.append(x)
    return keep


def r4_clock_reset(M, lst, module=None):
    if module in CLOCK_RESET_FUNCTION:
        return lst
    keep = []
    for x in lst:
        row = M.get(x[1].split(".")[0]) or {}
        if row.get("kind") == "port" and row.get("dir") == "in" and re.match(r"(clk|rst|rstn)(_|$)", x[1].split(".")[0]):
            continue
        keep.append(x)
    return keep


def r5_transport(M, lst):
    keep = []
    for x in lst:
        row = M.get(x[1]) or M.get(x[1].split(".")[0]) or {}
        if TXN.search(row.get("type") or ""):
            continue
        keep.append(x)
    return keep


def r6_record_beside_fields(M, lst):
    names = {x[1] for x in lst}
    return [x for x in lst if not ((M.get(x[1]) or {}).get("kind") == "signal"
                                   and any(n.split(".")[0] == x[1] and "." in n for n in names))]


RULES = [("R1 carrier copy", r1_carrier_copy), ("R2 carrier field", r2_carrier_field),
         ("R3 port forwarding", r3_port_forwarding), ("R4 clock and reset", r4_clock_reset),
         ("R5 transport records", r5_transport), ("R6 record beside its fields", r6_record_beside_fields)]


def apply_rules(run: dict, rules) -> dict:
    out = {}
    for m, lst in run.items():
        M = load_map(m)
        if not M:
            out[m] = lst; continue
        for _name, f in rules:
            lst = f(M, lst, m) if f is r4_clock_reset else f(M, lst)
        out[m] = lst
    return out


def main(versions):
    gt = ea.load_refs()["gt"]
    runs = ea.collect(versions)
    common = set(ea.common_modules(runs, gt))
    ngt = sum(len(gt[m]) for m in common)
    print(f"{len(common)} modules, {ngt} ground-truth entries (exact); relation map: {MAP_DIR}")
    mean = lambda sc, k: sum(s[k] for s in sc) / len(sc)
    for v in versions:
        rr = runs.get(v)
        if not rr:
            print(f"{v}: no runs found"); continue
        print(f"\n=== {v} ({len(rr)} runs)")
        base = [ea.score(r, gt, strict=True, only=common) for r in rr]
        print(f"   {'before':34s} P {mean(base,'precision'):.3f}  R {mean(base,'recall'):.3f}  items {mean(base,'emit'):6.1f}")
        for i in range(1, len(RULES) + 1):
            sc = [ea.score(apply_rules(r, RULES[:i]), gt, strict=True, only=common) for r in rr]
            print(f"   + {RULES[i-1][0]:32s} P {mean(sc,'precision'):.3f}  R {mean(sc,'recall'):.3f}  items {mean(sc,'emit'):6.1f}")
        after = [ea.score(apply_rules(r, RULES), gt, strict=True, only=common) for r in rr]
        dP, dR = mean(after, "precision") - mean(base, "precision"), mean(after, "recall") - mean(base, "recall")
        verdict = "SUBSTANTIAL" if dP >= 0.10 and dR >= -0.03 else "not substantial"
        print(f"   {'all rules':34s} precision {dP:+.3f}, recall {dR:+.3f}  -> {verdict} (bar: +0.10 and no worse than -0.03)")
        voted = mt.majority([apply_rules(r, RULES) for r in rr])[0]
        s = ea.score(voted, gt, strict=True, only=common)
        print(f"   {'all rules + majority vote':34s} P {s['precision']:.3f}  R {s['recall']:.3f}  items {s['emit']}"
              f"   (one list from the 3 runs, reported separately)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:] or ["m7e194es0ism", "v2x3r8", "m7e194es0c"])
