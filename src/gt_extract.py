"""gt_extract.py -- build machine-readable reference sets from the LAsset release.

Two references are produced, both keyed by our RTL file stem (e.g. "neorv32_trng"):

  manual_gt_neorv32.json   the MANUAL ground truth -- sheet 'Assets (Manual)' of
                           Asset_Dataset_Statistics_NEORV32.xlsx. This is the paper's
                           "True Assets" column and the thing to score against.
  lasset_<stage>.json      the paper's own published output per stage (initial /
                           refined / final), normalised to the same shape.

Multi-element cells are expanded: one manual row reading "rs1_i, rs2_i, rs3_i" becomes
three elements, which is what makes the row count (246) reconcile with the paper's
element count (302).

Usage:
    python gt_extract.py                     # uses the default paths below
    python gt_extract.py <repo_root> <out_dir>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# LAsset release checkout (the repo published with the paper)
DEFAULT_LASSET = Path(r"E:\jobs\ff\test\LAsset-Security-Assets")
DEFAULT_OUT = Path("ground_truth")

# Sheet-label -> our RTL file stem. Only modules we actually parse need an entry;
# unmapped labels are still exported under their original label with stem = None.
IP_LABEL_TO_STEM = {
    "CPU": "neorv32_cpu",
    "ALU": "neorv32_cpu_alu",
    "Control Unit": "neorv32_cpu_control",
    "Counters": "neorv32_cpu_counters",
    "BitManip": "neorv32_cpu_cp_bitmanip",
    "CFU": "neorv32_cpu_cp_cfu",
    "Cond. Ops Unit": "neorv32_cpu_cp_cond",
    "Crypto Unit": "neorv32_cpu_cp_crypto",
    "FPU": "neorv32_cpu_cp_fpu",
    "Mul/Div Unit": "neorv32_cpu_cp_muldiv",
    "Shifter Unit": "neorv32_cpu_cp_shifter",
    "Decompressor Unit": "neorv32_cpu_decompressor",
    "FrontEnd Unit": "neorv32_cpu_frontend",
    "ICC": "neorv32_cpu_icc",
    "LSU": "neorv32_cpu_lsu",
    "PMP": "neorv32_cpu_pmp",
    "regfile": "neorv32_cpu_regfile",
    "Debug_Auth": "neorv32_debug_auth",
    "Debug_DM": "neorv32_debug_dm",
    "Debug_DTM": "neorv32_debug_dtm",
    "DMEM": "neorv32_dmem",
    "IMEM": "neorv32_imem",
    "Cache": "neorv32_cache",
    "Bus": "neorv32_bus",
    "Xbus": "neorv32_xbus",
    "GPIO": "neorv32_gpio",
    "GPTMR": "neorv32_gptmr",
    "Hardware Spinlocks": "neorv32_hwspinlock",
    "NEOLED": "neorv32_neoled",
    "ONEWIRE": "neorv32_onewire",
    "PWM": "neorv32_pwm",
    "SDI": "neorv32_sdi",
    "SLINK": "neorv32_slink",
    "SPI": "neorv32_spi",
    "SYS": "neorv32_sys",
    "SYSINFO": "neorv32_sysinfo",
    "TRNG": "neorv32_trng",
    "TWD": "neorv32_twd",
    "TWI": "neorv32_twi",
    "UART1": "neorv32_uart",
    "WDT": "neorv32_wdt",
}

_IDENT = re.compile(r"[A-Za-z_][\w.]*")
_OBJ_WORDS = (("Confidentiality", "conf"), ("Integrity", "integ"), ("Availability", "avail"))


def split_elements(cell: str) -> list:
    """'rs1_i, rs2_i, rs3_i' -> 3 names; 'fifo.wdata / fifo.rdata (contents)' -> 2 names.

    Parenthetical commentary is dropped, '/' is treated as a separator, and any leftover
    prose is mined for identifier-shaped tokens so composite cells still yield elements.

    A REPEATED name in an explicit list is kept, because it denotes two distinct assets
    that happen to share a name in different entities of the same file. neorv32_bus's cell
    is literally 'state/state': the arbiter FSM state in neorv32_bus_switch and the
    reservation FSM state in neorv32_bus_amo_rvs. De-duplicating it collapsed them into one
    and was the sole reason this extraction totalled 301 elements against the paper's
    stated 302.

    Identifiers MINED FROM PROSE are still de-duplicated -- a sentence naming the same
    signal twice describes one asset, not two.
    """
    s = re.sub(r"\([^()]*\)", " ", str(cell))       # drop parentheticals
    s = re.sub(r"\s*/\s*", ",", s)                  # 'a / b' -> 'a,b'
    out, mined = [], set()
    for part in re.split(r"[,\n]", s):
        part = part.strip(" .;:\u2013-")
        if not part:
            continue
        if re.fullmatch(r"[A-Za-z_][\w.]*", part):
            out.append(part)                         # explicit: repeats are meaningful
        else:                                        # prose cell: mine identifiers
            for t in _IDENT.findall(part):
                if ("_" in t or "." in t) and t not in mined and t not in out:
                    mined.add(t)
                    out.append(t)
    return out


def normalise_objective(raw: str) -> list:
    """'Integrity/ Availability' -> ['Integrity', 'Availability']."""
    low = (raw or "").lower()
    return [name for name, key in _OBJ_WORDS if key in low]


def extract_manual_gt(xlsx: Path) -> dict:
    """Parse sheet 'Assets (Manual)' into {stem: {...}}."""
    try:
        import openpyxl
    except ImportError:
        sys.exit("openpyxl is required:  pip install openpyxl")

    ws = openpyxl.load_workbook(xlsx, data_only=True)["Assets (Manual)"]
    groups, current = {}, None
    for row in ws.iter_rows(min_row=2, values_only=True):
        cell = lambda i: (str(row[i]).strip() if i < len(row) and row[i] is not None else "")
        ip, asset, obj, why, cwe = cell(0), cell(1), cell(2), cell(3), cell(4)
        if ip:
            current = ip
            groups.setdefault(current, [])
        if asset and current:
            groups[current].append({"raw": asset, "objective_raw": obj, "why": why, "cwe": cwe})

    modules = {}
    for label, rows in groups.items():
        last_obj = ""
        assets = []
        for r in rows:
            # merged cells leave the objective blank on continuation rows
            if r["objective_raw"]:
                last_obj = r["objective_raw"]
            objs = normalise_objective(r["objective_raw"] or last_obj)
            for el in split_elements(r["raw"]):
                assets.append({
                    "element": el,
                    "objectives": objs,
                    "objective": objs[0] if objs else "",
                    "raw_cell": r["raw"],
                    "why": r["why"],
                    "cwe": r["cwe"],
                })
        stem = IP_LABEL_TO_STEM.get(label)
        modules[stem or label] = {"ip_label": label, "rtl_stem": stem,
                                  "n_rows": len(rows), "assets": assets}
    return {"source": str(xlsx), "sheet": "Assets (Manual)",
            "note": "paper's 'True Assets'; multi-element cells expanded",
            "modules": modules}


def _load_json_lenient(path: Path):
    """The published lists are occasionally concatenated JSON arrays."""
    txt = path.read_text(encoding="utf-8", errors="replace")
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        dec, i, out = json.JSONDecoder(), 0, []
        while i < len(txt):
            while i < len(txt) and txt[i] in " \r\n\t,":
                i += 1
            if i >= len(txt):
                break
            val, i = dec.raw_decode(txt, i)
            out.extend(val if isinstance(val, list) else [val])
        return out


def _asset_row(a: dict, entity_hint: str = "") -> dict:
    return {
        "element": a.get("Asset RTL", ""),
        "objective": a.get("Security Objective", ""),
        "asset_name": a.get("Asset Name", ""),
        "entity": a.get("Entity", entity_hint),
        "secondary": a.get("Secondary Assets", []),
    }


def extract_lasset_stage(path: Path) -> dict:
    """Normalise a published asset_list_neorv32_<stage>.json to {stem: {...}}.

    Two shapes exist in the release:
      initial : {"IP": ..., "Assets": [...]}
      refined : {"IP": ..., "VHDL Entities": [{"VHDL Entity": ..., "Assets": [...]}]}
    """
    data = _load_json_lenient(path)
    modules = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        stem = entry.get("IP", "")
        assets = [_asset_row(a) for a in (entry.get("Assets") or [])]
        for ent in entry.get("VHDL Entities") or []:            # refined/final shape
            if isinstance(ent, dict):
                name = ent.get("VHDL Entity", "")
                assets += [_asset_row(a, name) for a in (ent.get("Assets") or [])]
        modules[stem] = {"rtl_stem": stem, "assets": assets}
    return {"source": str(path), "modules": modules}


def main(lasset_root: Path = DEFAULT_LASSET, out_dir: Path = DEFAULT_OUT) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    xlsx = lasset_root / "SoC" / "Asset_Dataset_Statistics_NEORV32.xlsx"
    if not xlsx.exists():
        sys.exit(f"not found: {xlsx}")

    gt = extract_manual_gt(xlsx)
    (out_dir / "manual_gt_neorv32.json").write_text(json.dumps(gt, indent=1), encoding="utf-8")
    n_mod = len(gt["modules"])
    n_el = sum(len(m["assets"]) for m in gt["modules"].values())
    n_rows = sum(m["n_rows"] for m in gt["modules"].values())
    unmapped = [m["ip_label"] for m in gt["modules"].values() if not m["rtl_stem"]]
    print(f"manual GT : {n_mod} modules, {n_rows} rows -> {n_el} elements "
          f"-> {out_dir/'manual_gt_neorv32.json'}")
    print(f"            (paper's Statistics sheet reports 302 True Assets)")
    if unmapped:
        print(f"            UNMAPPED labels (add to IP_LABEL_TO_STEM): {unmapped}")

    for stage in ("initial", "refined", "final"):
        src = lasset_root / "SoC" / "Spec.+RTL" / f"asset_list_neorv32_{stage}.json"
        if not src.exists():
            continue
        d = extract_lasset_stage(src)
        if not d["modules"]:
            print(f"lasset {stage:8s}: empty, skipped")
            continue
        (out_dir / f"lasset_{stage}.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
        n = sum(len(m["assets"]) for m in d["modules"].values())
        print(f"lasset {stage:8s}: {len(d['modules'])} modules, {n} assets "
              f"-> {out_dir/f'lasset_{stage}.json'}")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LASSET
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    main(root, out)
