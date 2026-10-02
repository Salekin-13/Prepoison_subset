"""Pre-registered readings for arm m7e194es0ismd (definition rules) against the winner m7e194es0ism. Fixed 2026-10-01,
before the arm ran. Tuning set, 15 GT modules, 3 runs per version, strict scorer. Roles from the code-written map.
 R0  P / R / emitted per run, both versions, with the LAsset initial row (0.737 / 0.910, 137 emitted).
 R1  transit rule: false-positive run-slots on internal data-only elements (no decision record) must fall by >= 20%.
 R2  decider rule: reference hit run-slots on entries whose element decides (GATES / SELECTS / CONSTRAINS) must not fall.
 R3  protected references, the elements the transit rule must NOT drop (registers that hold a value at rest, written in and
     read out): imem rdata, muldiv mul.prod, cfu key_mem, hwspinlock lock_q, uart ctrl.baud: each must stay in >= 2 of 3 runs.
 R4  decider cost: false-positive run-slots on internal deciding elements (reported; the precision price of R2).
 R5  emission guard: emitted per run within +/-10% of the winner (more = the rule became a quota; less = under-writing).
 Adoption: the Step 1b bar (P >= 0.374 at R >= 0.83), and R1-R3 hold."""
import json, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "assetgen_meta"))
import eval_assets as ea, rel_view as rv

PROTECTED = [("neorv32_imem", "rdata"), ("neorv32_cpu_cp_muldiv", "mul.prod"), ("neorv32_cpu_cp_cfu", "key_mem"),
             ("neorv32_hwspinlock", "lock_q"), ("neorv32_uart", "ctrl.baud")]
TRANSIT = [("neorv32_debug_dtm", "dr_trigger.sreg"), ("neorv32_imem", "addr_ff"), ("neorv32_spi", "rtx_engine.sreg"),
           ("neorv32_spi", "rx_fifo.rdata"), ("neorv32_spi", "rx_fifo.wdata"), ("neorv32_spi", "tx_fifo.rdata"),
           ("neorv32_spi", "tx_fifo.wdata"), ("neorv32_trng", "fifo.rdata"), ("neorv32_trng", "fifo.wdata"),
           ("neorv32_twi", "engine.sreg"), ("neorv32_twi", "io_con.scl_in_ff"), ("neorv32_twi", "io_con.sda_in_ff"),
           ("neorv32_uart", "rx_engine.sreg"), ("neorv32_uart", "rx_fifo.rdata"), ("neorv32_uart", "rx_fifo.wdata"),
           ("neorv32_uart", "tx_engine.sreg"), ("neorv32_uart", "tx_fifo.rdata")]


def roles(mods):
    out = {}
    for m in mods:
        d = json.loads(rv.map_path(m, rv.CODE_MAP_DIR).read_text(encoding="utf-8"))
        for a in ("ports", "signals"):
            for e in d[a]:
                ts = {r["type"] for r in e.get("relationship", [])}
                b = (e.get("boundary") or {}).get("mode")
                r = "port" if b else ("decides" if ts & {"GATES", "SELECTS", "CONSTRAINS"} else ("data-only" if ts else "no relation"))
                out.setdefault((m, e["name"]), set()).add(r)
    return out


def slots(version, gt, mods):
    hit, fp, em = Counter(), Counter(), []
    for k in range(3):
        s = ea.score(Path(f"assets_tuning18_{version}_r{k}"), gt, strict=True, only=set(mods))
        em.append((s["precision"], s["recall"], s["emit"]))
        for m in mods:
            miss = Counter(s["per_module"][m]["fn"])
            for n, _o in gt[m]:
                if miss[n] > 0: miss[n] -= 1
                else: hit[(m, n)] += 1
            for n in s["per_module"][m]["fp"]: fp[(m, n)] += 1
    return hit, fp, em


def read(arm="m7e194es0ismd", base="m7e194es0ism", log=print):
    R = ea.load_refs(); gt = R["gt"]
    mods = sorted(m for m in gt if rv.map_path(m, rv.CODE_MAP_DIR).exists())
    role = roles(mods)
    ini = ea.score({m: R["paper"][m] for m in mods}, gt, strict=True, only=set(mods))
    log(f"m7e194es0ismd readings, {len(mods)} tuning modules, {sum(len(gt[m]) for m in mods)} reference entries, 3 runs each")
    log(f"   R0  LAsset initial (no CWE refinement)   P {ini['precision']:.3f} R {ini['recall']:.3f} emitted {ini['emit']}")
    res = {}
    for v in (base, arm):
        h, f, em = slots(v, gt, mods); res[v] = (h, f, em)
        log(f"   R0  {v:36s} P {sum(e[0] for e in em) / 3:.3f} R {sum(e[1] for e in em) / 3:.3f} emitted/run {sum(e[2] for e in em) / 3:.1f}"
            f"   (runs P {[round(e[0], 3) for e in em]} R {[round(e[1], 3) for e in em]})")
    (hb, fb, eb), (ha, fa, ea_) = res[base], res[arm]
    has = lambda k, r: r in role.get(k, set())
    t_b = sum(c for k, c in fb.items() if has(k, "data-only") and not has(k, "port")); t_a = sum(c for k, c in fa.items() if has(k, "data-only") and not has(k, "port"))
    tr_b, tr_a = sum(fb[k] for k in TRANSIT), sum(fa[k] for k in TRANSIT)
    log(f"   R1  FP slots on the transit list: {tr_b} -> {tr_a} ({(tr_a - tr_b) / max(tr_b, 1):+.0%}; pass if <= -50%)"
        f"  {'PASS' if tr_a <= 0.5 * tr_b else 'FAIL'}")
    log(f"   R1b FP slots on all internal data-only elements: {t_b} -> {t_a} ({(t_a - t_b) / max(t_b, 1):+.0%}; reported)")
    d_b = sum(c for k, c in hb.items() if has(k, "decides")); d_a = sum(c for k, c in ha.items() if has(k, "decides"))
    n_d = sum(1 for m in mods for n, _o in gt[m] if has((m, n), "decides"))
    log(f"   R2  reference hit slots on deciding elements: {d_b} -> {d_a} of {3 * n_d} (pass if not lower)  {'PASS' if d_a >= d_b else 'FAIL'}")
    for k in PROTECTED:
        log(f"   R3  {k[0][8:]}/{k[1]}: {hb[k]}/3 -> {ha[k]}/3 (pass if >= 2)  {'PASS' if ha[k] >= 2 else 'FAIL'}")
    c_b = sum(c for k, c in fb.items() if has(k, "decides") and not has(k, "port")); c_a = sum(c for k, c in fa.items() if has(k, "decides") and not has(k, "port"))
    log(f"   R4  FP slots on internal deciding elements: {c_b} -> {c_a} (the precision price of the decider rule)")
    mb, ma = sum(e[2] for e in eb) / 3, sum(e[2] for e in ea_) / 3
    log(f"   R5  emitted per run {mb:.1f} -> {ma:.1f} ({(ma - mb) / mb:+.0%}; pass if within +/-10%)  {'PASS' if abs(ma - mb) <= 0.1 * mb else 'FAIL'}")
    pa, ra = sum(e[0] for e in ea_) / 3, sum(e[1] for e in ea_) / 3
    log(f"   Step 1b bar (P >= 0.374 at R >= 0.83): P {pa:.3f} R {ra:.3f} -> {'counts' if pa >= 0.374 and ra >= 0.83 else 'does not count'}")
    watch = sorted({k for k in set(fb) | set(fa) if has(k, "data-only") and not has(k, "port") and (fb[k] >= 2 or fa[k] >= 2)})
    log("   transit watch (internal data-only FPs in >= 2 runs of either version): " +
        ", ".join(f"{m[8:]}/{n} {fb[(m, n)]}->{fa[(m, n)]}" for m, n in watch[:40]))


if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    read(*(sys.argv[1:3] or ()))
