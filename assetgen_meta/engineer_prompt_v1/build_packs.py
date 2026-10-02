"""Blind packs for the engineer analysis: per module, the comment-stripped VHDL with ORIGINAL line numbers (one block per
entity) and the code-written relation map, nothing else. Also writes the engineered prompt and checks it against the
project's prompt constraints (corpus identifiers, numeric hints, comment use)."""
import json, shutil, sys, os
from pathlib import Path
ROOT = Path("E:/jobs/ff/test/Prepoison_subset"); os.chdir(ROOT)
for p in ("", "assetgen_meta", "step1"): sys.path.insert(0, str(ROOT / p))
sys.stdout.reconfigure(encoding="utf-8")
import relation_stage as RS, relation_experiments as RX, rel_view as rv, meta_tools as mt
HERE = Path(__file__).parent; PACKS = HERE / "packs"; PACKS.mkdir(exist_ok=True)
MODULES = ["neorv32_hwspinlock", "neorv32_wdt", "neorv32_cpu_cp_muldiv", "neorv32_cache", "neorv32_sys", "neorv32_debug_dtm", "neorv32_spi"]
for m in MODULES:
    d = PACKS / m[8:]; d.mkdir(exist_ok=True)
    ents = RS.load_module(m, RX.where(None))
    src = "\n\n".join(f"===== ENTITY {e['entity']} =====\n{e['src']}" for e in ents)
    (d / "rtl_numbered.txt").write_text(src, encoding="utf-8")
    shutil.copy2(rv.map_path(m, rv.CODE_MAP_DIR), d / "relation_map.json")
    print(f"{m[8:]:14s} entities {len(ents)}, rtl {len(src):7,d} chars, map {(d / 'relation_map.json').stat().st_size:7,d} bytes")
PROMPT = (HERE / "engineer_prompt_v1.md").read_text(encoding="utf-8")
r = mt.check_prompt(PROMPT, mt.corpus_names(), "engineer_prompt_v1")
print("prompt constraints:", "PASS" if r["ok"] else r["problems"])
