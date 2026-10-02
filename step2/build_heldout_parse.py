"""Build closed-set files for the 26 never-tuned ground-truth modules, in the same shape as parsed_tuning18/.

Record types live in neorv32_package.vhd, so the record registry is built from the whole corpus (RTL_data plus
RTL_heldout) before any file is parsed; otherwise record fields would not expand and the closed set would be wrong.
Writes parsed_tuning18/<module>.json for the held-out modules only; the 18 existing files are never touched.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import eval_assets as ea      # noqa: E402
import rtl_parse              # noqa: E402

DEV, HELD, OUT = ROOT / "RTL_data", ROOT / "RTL_heldout", ROOT / "parsed_tuning18"


def flatten(stem: str, parsed: dict) -> dict:
    ports, signals, ents = [], [], []
    for e in parsed["entities"]:
        ents.append(e["entity"])
        for p in e.get("ports", []):
            ports.append({"entity": e["entity"], **p})
        for s in e.get("signals", []):
            signals.append({"entity": e["entity"], **s})
    return {"module": stem, "entities": ents, "ports": ports, "signals": signals}


def main():
    gt = ea.load_refs()["gt"]
    dev = {p.stem for p in DEV.glob("*.vhd")}
    held = sorted(set(gt) - dev)
    records = rtl_parse.build_record_registry(sorted(DEV.glob("*.vhd")) + sorted(HELD.glob("*.vhd")))
    # self-test: the same code must reproduce an existing dev closed set exactly
    ref = json.loads((OUT / "neorv32_wdt.json").read_text(encoding="utf-8"))
    mine = flatten("neorv32_wdt", rtl_parse.parse_rtl_file(str(DEV / "neorv32_wdt.vhd"), records))
    for k in ("ports", "signals"):
        a = sorted((x["entity"], x["name"]) for x in ref[k])
        b = sorted((x["entity"], x["name"]) for x in mine[k])
        assert a == b, f"self-test failed on {k}: {set(a) ^ set(b)}"
    print(f"self-test PASS: reproduces parsed_tuning18/neorv32_wdt.json ({len(ref['ports'])} ports, {len(ref['signals'])} signals)")

    tot = reach = 0
    for m in held:
        d = flatten(m, rtl_parse.parse_rtl_file(str(HELD / f"{m}.vhd"), records))
        (OUT / f"{m}.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
        names = {e["name"] for e in d["ports"] + d["signals"]}
        for e, _o in gt[m]:
            tot += 1; reach += e in names
    print(f"wrote {len(held)} closed sets. Ground-truth entries held out: {tot}; present in our parse: {reach} "
          f"({reach/tot:.0%}) - the rest cannot be scored as hits, exactly as on the development set.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
