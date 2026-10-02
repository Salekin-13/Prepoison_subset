"""Pre-registered readings for hand arm m7e194es0ismcap (the captured-input bullet), against the winner m7e194es0ism.
Counts are run-slots: one per (element, run) over 3 runs, from eval_assets.score's fp/fn lists (strict, 15 GT modules).
Thresholds were fixed before the arm ran (Claude review, 2026-10-01)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "step1"))
import eval_assets as ea

TARGET = [("neorv32_debug_dtm", "jtag_tms_i"), ("neorv32_spi", "spi_dat_i"), ("neorv32_sys", "enable_i"), ("neorv32_uart", "uart_rxd_i")]
CAPTURED_GT = TARGET + [("neorv32_cpu_cp_cfu", "csr_wdata_i"), ("neorv32_cpu_cp_cfu", "rs1_i"), ("neorv32_cpu_cp_cfu", "rs2_i"),
                        ("neorv32_cpu_cp_muldiv", "rs1_i"), ("neorv32_cpu_cp_muldiv", "rs2_i"), ("neorv32_debug_dtm", "jtag_tdi_i"),
                        ("neorv32_uart", "uart_ctsn_i")]
CLOCK_RESET = [("neorv32_debug_dtm", "jtag_tck_i"), ("neorv32_sys", "rstn_wdt_i"), ("neorv32_sys", "rstn_dbg_i")]
FIRST_STAGE = [("neorv32_debug_dtm", "tap_sync.tdi_ff"), ("neorv32_debug_dtm", "tap_sync.tms_ff"), ("neorv32_debug_dtm", "tap_sync.tck_ff"),
               ("neorv32_spi", "rtx_engine.sdi_sync"), ("neorv32_uart", "rx_engine.sync")]
NEW_FP = [("neorv32_trng", "en_i"), ("neorv32_cache", "wdata_i"), ("neorv32_trng", "enable_i")]
PMP_CTRL = [("neorv32_cpu_pmp", "ctrl_i")]
READINGS = [  # (label, slots, fail rule as text, fail test on the arm's count)
    ("target GT inputs (main test)", TARGET, "fail if <= 4 of 12", lambda c, n: c <= 4),
    ("all 11 GT captured scalar inputs", CAPTURED_GT, "fail if below the winner", None),
    ("clock/reset-role inputs (exclusion guard)", CLOCK_RESET, "fail if >= 3 of 9", lambda c, n: c >= 3),
    ("first-stage pin registers (stage-listing guard)", FIRST_STAGE, "fail if >= 3 of 15", lambda c, n: c >= 3),
    ("non-GT inputs the rule may add", NEW_FP, "the precision cost, ceiling 9", None),
    ("pmp ctrl_i (transport-wording guard)", PMP_CTRL, "fail if 0 of 3", lambda c, n: c == 0),
]


def record_inputs(gt):
    """Non-GT whole input ports of a record type carrying transactions (transport guard: 0 of 54 slots today)."""
    import relation_stage as RS, lasset_step1 as S
    out = []
    for m in gt:
        try:
            ents = RS.load_module(m, S.WHERE)
        except Exception:
            continue
        names = {n for n, _o in gt[m]}
        for e in ents:
            for p in e["ports"]:
                t = (p.get("type") or "").lower()
                if p.get("dir") == "in" and "." not in p["name"] and ("req_t" in t or "rsp_t" in t) and p["name"] not in names:
                    out.append((m, p["name"]))
    return sorted(set(out))


def slots(version, items, gt, common):
    n = 0
    for k in range(3):
        s = ea.score(Path(f"assets_tuning18_{version}_r{k}"), gt, strict=True, only=common)["per_module"]
        for m, name in items:
            if m not in s:
                continue
            n += (name in s[m]["fp"]) if name not in {x for x, _o in gt[m]} else (name not in s[m]["fn"])
    return n


def read(version="m7e194es0ismcap", winner="m7e194es0ism", log=print):
    gt = ea.load_refs()["gt"]; runs = ea.collect([winner, version]); common = ea.common_modules(runs, gt)
    log(f"readings on {len(common)} modules, run-slots over 3 runs (arm vs winner)")
    rows = READINGS + [("non-GT record-typed inputs (transport guard)", record_inputs(gt), "fail if >= 3", lambda c, n: c >= 3)]
    for label, items, rule, test in rows:
        a, w = slots(version, items, gt, common), slots(winner, items, gt, common)
        n = 3 * len(items)
        verdict = "" if test is None else ("  <-- FAIL" if test(a, n) else "  ok")
        if label.startswith("all 11") and a < w:
            verdict = "  <-- FAIL (fell below the winner)"
        log(f"   {label:48s} arm {a:3d} / {n:3d}   winner {w:3d} / {n:3d}   {rule}{verdict}")
    for v in (winner, version):
        sc = [ea.score(Path(f"assets_tuning18_{v}_r{k}"), gt, strict=True, only=common) for k in range(3)]
        log(f"   {v:16s} P {sum(s['precision'] for s in sc) / 3:.3f} R {sum(s['recall'] for s in sc) / 3:.3f} "
            f"emitted/run {sum(s['emit'] for s in sc) / 3:.1f} (quota-spill guard: the winner's is the reference)")


if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    read(*(sys.argv[1:3] or ()))
