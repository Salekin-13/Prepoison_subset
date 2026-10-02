"""The pre-registered readings of the held-out run (assetgen_meta/HELDOUT_PREREG.md). Code only: no model call.

    read()            the held-out readings, ONCE, after the three executor runs assets_heldout26_m7e194es0ism_r0..2:
                        1. refuses to run if any file pinned in HELDOUT_PREREG.md has a different sha12 now;
                        2. refuses to run if a run folder holds another prompt, model or closed-set folder;
                        3. scores only the modules present in all 3 runs (the rest are listed);
                        4. writes the traces under assetgen_meta/traces/assets_heldout26/ and the numbers to
                           assetgen_meta/heldout_readings.json;
                        5. prints R1-R6, with the LAsset initial row (no CWE refinement) next to every stack.
    dry_run_tuning()  the same code path on the 15 tuning modules (stem assets_tuning18). It reads no held-out file and
                      writes nothing; it shows the code runs and prints the tuning reference value of every reading.

Run from anywhere:  python assetgen_meta/heldout_readings.py --tuning      (dry run)
                    python assetgen_meta/heldout_readings.py --heldout     (the one held-out reading)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import post_levers as PL          # noqa: E402
import meta_tools as mt           # noqa: E402
import asset_trace as AT          # noqa: E402

PREREG = HERE / "HELDOUT_PREREG.md"
VERSION, PROMPT_SHA12, MODEL = "m7e194es0ism", "0d0def4c6fe3", "gpt-5-mini"
STEM_HELDOUT, PARSED_HELDOUT, RTL_HELDOUT = "assets_heldout26", "parsed_heldout26", ROOT / "RTL_heldout"
OUT_JSON = HERE / "heldout_readings.json"

PRIMARY, VS = "MV+NONE+BF", "MV"                                  # R1
SECONDARY = ("MV+NONE+GUARD+BF", "MV+NONE+BF+GUARD")              # R2 (GUARD: overfitted, never adopted)
RECALL_BAR = 0.83
BOOT_N, BOOT_SEED, THIN_DRAWS, THIN_SEED = 10000, 0, 1000, 0
FALSIFY = {"NONE_fp_share_min": 0.90, "GUARD_margin_over_random": 0.05, "GUARD_recall_change_min": -0.08,
           "BF_tp_share_min": 0.50, "leak_move_max": 0.01}


# ------------------------------------------------------------------------------------------ pre-registration ---
def sha12_of(rel: str, kind: str) -> str:
    """kind 'bytes': sha256 of the file's bytes; 'text': of its text as Python reads it (newlines normalised), which
    is how meta_tools.run_version records the prompt; 'dir': of every file under the folder, sorted by relative path
    (path and bytes)."""
    p = ROOT / rel
    if kind == "text":
        return hashlib.sha256(p.read_text(encoding="utf-8").encode("utf-8")).hexdigest()[:12]
    if kind == "bytes":
        return hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    if kind == "dir":
        h = hashlib.sha256()
        for f in sorted((x for x in p.rglob("*") if x.is_file()), key=lambda x: x.relative_to(p).as_posix()):
            h.update(f.relative_to(p).as_posix().encode("utf-8") + b"\0" + f.read_bytes() + b"\0")
        return h.hexdigest()[:12]
    raise ValueError(kind)


def prereg_table(path: Path = PREREG) -> list[tuple[str, str, str]]:
    """[(relative path, kind, sha12)] from the table rows | `path` | kind | `sha12` | of HELDOUT_PREREG.md."""
    rows = re.findall(r"^\|\s*`([^`]+)`\s*\|\s*(bytes|text|dir)\s*\|\s*`([0-9a-f]{12})`\s*\|", path.read_text(encoding="utf-8"), re.M)
    if not rows:
        raise RuntimeError(f"{path.name}: no pinned files found")
    return rows


def verify_prereg(log=print) -> bool:
    bad = [(rel, want, sha12_of(rel, kind) if (ROOT / rel).exists() else "missing") for rel, kind, want in prereg_table()
           if not (ROOT / rel).exists() or sha12_of(rel, kind) != want]
    log(f"pre-registered files: {len(prereg_table()) - len(bad)}/{len(prereg_table())} unchanged"
        + ("" if not bad else "; CHANGED: " + "; ".join(f"{r} (pinned {w}, now {n})" for r, w, n in bad)))
    return not bad


def check_runs(stem: str, version: str, modules, parsed_dir: str | None, log=print) -> tuple[bool, list[str]]:
    """Each run folder: prompt sha, model, closed-set folder. -> (ok, modules present in every run)."""
    ok, present = True, set(modules)
    for k in (0, 1, 2):
        d = ROOT / f"{stem}_{version}_r{k}"
        if not (d / "_run_meta.json").exists():
            log(f"   {d.name}: no run folder (or no _run_meta.json) -- REFUSED")
            ok, present = False, set()
            continue
        meta = json.loads((d / "_run_meta.json").read_text(encoding="utf-8"))
        got = {f.stem for f in d.glob("*.json") if not f.name.startswith("_")}
        probs = []
        if meta.get("system_prompt_sha256", "")[:12] != PROMPT_SHA12:
            probs.append(f"prompt {meta.get('system_prompt_sha256', 'none')[:12]}")
        if meta.get("model") != MODEL:
            probs.append(f"model {meta.get('model')}")
        if parsed_dir and Path(meta.get("parsed_dir", "")).name != parsed_dir:
            probs.append(f"closed set {meta.get('parsed_dir')}")
        ok &= not probs
        present &= got
        log(f"   {d.name}: {len(got & set(modules))}/{len(modules)} modules; "
            f"missing {sorted(set(modules) - got) or 'none'}; {'OK' if not probs else 'REFUSED: ' + ', '.join(probs)}")
    return ok, sorted(present)


# ---------------------------------------------------------------------------------------------------- readings ---
def _f(s):
    return f"P {s['precision']:.3f} R {s['recall']:.3f} emit {s['emit']:6.1f} TP {s['tp']:5.1f} FP {s['fp']:5.1f}"


def readings(L: PL.Levers, log=print) -> dict:
    """R1-R6 on the Levers' modules. Every number with its denominator."""
    out = {"modules": L.modules, "gt_entries_per_list": None}
    lo, lc = L.lasset("original"), L.lasset("corrected")
    out["lasset_initial"] = {"original": lo, "corrected": lc}
    log(f"\nmodules scored: {len(L.modules)}; GT entries per scored list: {lo['ref']} original, {lc['ref']} corrected (exact)")
    log(f"LAsset initial (no CWE refinement), same modules: P {lo['precision']:.3f} R {lo['recall']:.3f} emitted {lo['emit']} "
        f"(TP {lo['tp']}, FP {lo['fp']}); corrected GT P {lc['precision']:.3f} R {lc['recall']:.3f}")
    # ---- every stack, with the LAsset row next to it
    rows = {}
    log(f"\n{'stack':18s} {'original GT':52s} | {'corrected GT':16s} | LAsset initial")
    for name in PL.STACKS:
        so, sc = L.score(name, "original"), L.score(name, "corrected")
        rows[name] = {"original": {k: v for k, v in so.items() if k != "per_module"},
                      "corrected": {k: v for k, v in sc.items() if k != "per_module"}}
        log(f"{name:18s} {_f(so):52s} | P {sc['precision']:.3f} R {sc['recall']:.3f} | P {lo['precision']:.3f} R {lo['recall']:.3f}")
    out["stacks"], out["gt_entries_per_list"] = rows, rows["base"]["original"]["ref"]
    log("(stacks without MV: mean of the 3 runs; MV stacks: the one voted list)")
    # ---- R1
    s1, bs = L.score(PRIMARY), L.bootstrap(PRIMARY, VS, n=BOOT_N, seed=BOOT_SEED)
    base, mvs = L.score("base"), L.score(VS)
    r1 = bs["dP_lo"] > 0 and s1["recall"] >= RECALL_BAR
    out["R1"] = {"bootstrap": bs, "recall": s1["recall"], "tp": s1["tp"], "ref": s1["ref"], "pass": r1,
                 "descriptive": {"P_minus_base": s1["precision"] - base["precision"], "R_minus_MV": s1["recall"] - mvs["recall"]}}
    log(f"\nR1 primary {PRIMARY}: P {s1['precision']:.3f}, R {s1['recall']:.3f} (TP {s1['tp']:.0f}/{s1['ref']}).")
    log(f"   precision gain over {VS}: {bs['dP']:+.3f}, 95% module-bootstrap interval [{bs['dP_lo']:+.3f}, {bs['dP_hi']:+.3f}] "
        f"({BOOT_N:,} resamples of {bs['modules']} modules, seed {BOOT_SEED}); recall change {bs['dR']:+.3f} "
        f"[{bs['dR_lo']:+.3f}, {bs['dR_hi']:+.3f}]")
    log(f"   pass needs interval low end > 0 AND recall >= {RECALL_BAR}: {'PASS' if r1 else 'FAIL'}"
        f"  (descriptive only: P minus base {s1['precision'] - base['precision']:+.3f}, R minus MV {s1['recall'] - mvs['recall']:+.3f})")
    # ---- R2
    out["R2"] = {}
    log("\nR2 secondary, GUARD (overfitted on tuning; reported, never adopted), against random thinning of equal strength "
        f"({THIN_DRAWS:,} draws, seed {THIN_SEED}):")
    for name in ("GUARD",) + SECONDARY:
        t, b = L.random_thinning(name, draws=THIN_DRAWS, seed=THIN_SEED), L.bootstrap(name, VS if name.startswith("MV") else "base")
        out["R2"][name] = {"thinning": t, "bootstrap": b}
        log(f"   {name:18s} P {t['guard_P']:.3f} R {t['guard_R']:.3f} | random thinning P {t['rand_P_mean']:.3f} "
            f"[{t['rand_P_lo']:.3f}, {t['rand_P_hi']:.3f}] R {t['rand_R_mean']:.3f}; share of draws at or above GUARD's P "
            f"{t['share_rand_P_ge_guard']:.3f} | vs {b['b']}: dP {b['dP']:+.3f} [{b['dP_lo']:+.3f}, {b['dP_hi']:+.3f}], "
            f"dR {b['dR']:+.3f} [{b['dR_lo']:+.3f}, {b['dR_hi']:+.3f}]")
    # ---- R3
    eff = {lv: L.lever_effect(lv) for lv in PL.FILTERS}
    bp = base["precision"]
    guard_r = L.score("GUARD")["recall"] - base["recall"]
    f3 = {"NONE": eff["NONE"]["share_fp_of_removed"] is not None and eff["NONE"]["share_fp_of_removed"] < FALSIFY["NONE_fp_share_min"],
          "GUARD": (eff["GUARD"]["share_fp_of_removed"] is not None
                    and eff["GUARD"]["share_fp_of_removed"] <= (1 - bp) + FALSIFY["GUARD_margin_over_random"])
                   or guard_r < FALSIFY["GUARD_recall_change_min"],
          "BF": eff["BF"]["share_tp_of_added"] is not None and eff["BF"]["share_tp_of_added"] < FALSIFY["BF_tp_share_min"]}
    out["R3"] = {"effects": eff, "falsified": f3, "base_precision": bp, "guard_recall_change": guard_r}
    sh = lambda x: "n/a (nothing changed)" if x is None else f"{x:.3f}"
    log("\nR3 each filter alone on the unfiltered runs (mean per run):")
    log(f"   NONE  removes {eff['NONE']['removed']:.1f}: FP {eff['NONE']['fp_removed']:.1f}, TP {eff['NONE']['tp_lost']:.1f}; "
        f"FP share {sh(eff['NONE']['share_fp_of_removed'])} (falsified if < {FALSIFY['NONE_fp_share_min']}): "
        f"{'FALSIFIED' if f3['NONE'] else 'holds'}")
    log(f"   GUARD removes {eff['GUARD']['removed']:.1f}: FP {eff['GUARD']['fp_removed']:.1f}, TP {eff['GUARD']['tp_lost']:.1f}; "
        f"FP share {sh(eff['GUARD']['share_fp_of_removed'])} (falsified if <= 1 - base P + 0.05 = {(1 - bp) + 0.05:.3f}, "
        f"or if the recall change {guard_r:+.3f} is < {FALSIFY['GUARD_recall_change_min']}): {'FALSIFIED' if f3['GUARD'] else 'holds'}")
    log(f"   BF    adds {eff['BF']['added']:.1f}: TP {eff['BF']['tp_gained']:.1f}, FP {eff['BF']['fp_added']:.1f}; "
        f"TP share {sh(eff['BF']['share_tp_of_added'])} (falsified if < {FALSIFY['BF_tp_share_min']}): {'FALSIFIED' if f3['BF'] else 'holds'}")
    # ---- R4 (descriptive, computed after scoring): the GUARD separator on this GT
    gt = L.refs["original"]
    gt_fields, gt_in, other, other_in = 0, 0, 0, 0
    for m in L.modules:
        gnames = {n for n, _o in gt[m]}
        for (ent, n), e in L.MAP[m].items():
            if "." not in n or e["_arr"] != "signals":
                continue
            inc = L.in_guard(m, ent, n)
            if n in gnames:
                gt_fields += 1; gt_in += inc
            else:
                other += 1; other_in += inc
    out["R4"] = {"gt_fields": gt_fields, "gt_in_condition": gt_in, "other_fields": other, "other_in_condition": other_in}
    log(f"\nR4 GUARD separator (descriptive): GT internal record fields in a condition {gt_in}/{gt_fields}; "
        f"other internal record fields {other_in}/{other}")
    # ---- R5 leak checks
    b_nr = L.bootstrap(PRIMARY, VS, n=BOOT_N, seed=BOOT_SEED, bf_name_rule=False)
    with PL._at(ROOT):
        b_cv = L.bootstrap(PRIMARY, VS, n=BOOT_N, seed=BOOT_SEED, post=mt.convention_filter)
    conv = L.convention_matches()
    moved = max(abs(b_nr["dP"] - bs["dP"]), abs(b_cv["dP"] - bs["dP"]))
    claim = min(bs["dP"], b_nr["dP"], b_cv["dP"]) if moved > FALSIFY["leak_move_max"] else bs["dP"]
    out["R5"] = {"bf_type_rule_only": b_nr, "convention_neutral": b_cv, "convention_matches_per_run": conv,
                 "max_move": moved, "claimed_dP": claim}
    log(f"\nR5 overlap checks on R1's precision gain {bs['dP']:+.3f}:")
    log(f"   BF with the relationship-type exclusion only: {b_nr['dP']:+.3f} [{b_nr['dP_lo']:+.3f}, {b_nr['dP_hi']:+.3f}]")
    log(f"   convention-neutral (meta_tools.convention_filter on both): {b_cv['dP']:+.3f} [{b_cv['dP_lo']:+.3f}, {b_cv['dP_hi']:+.3f}]")
    log(f"   convention-matching emissions per run: {conv}; largest move {moved:.3f} "
        f"(rule: above {FALSIFY['leak_move_max']}, the claim uses the lowest of the three gains); claimed gain {claim:+.3f}")
    # ---- R6
    per = L.score("base")["per_list"]
    out["R6"] = {"base_per_run": per}
    log("\nR6 per run, base: " + "; ".join(f"r{k}: P {p:.3f} R {r:.3f} emit {e}" for k, (p, r, e, _t, _f) in enumerate(per)))
    nb = L.bootstrap("NONE+BF", "base")
    out["R6"]["NONE+BF_vs_base"] = nb
    log(f"   NONE+BF minus base (no vote): dP {nb['dP']:+.3f} [{nb['dP_lo']:+.3f}, {nb['dP_hi']:+.3f}], dR {nb['dR']:+.3f}")
    # ---- decision
    adopt = PRIMARY if r1 else "none (the filters did not generalise; report base and MV)"
    out["decision"] = adopt
    log(f"\nDECISION (pre-registered rule): adopt {adopt}. GUARD stacks are reported, never adopted.")
    return out


def _levers(stem, modules, map_dir, rtl_dir):
    return PL.Levers(VERSION, stem, modules, map_dir, rtl_dir, cond="codetags")


def dry_run_tuning(log=print) -> dict:
    """Same code path on the tuning set; no held-out file is read and nothing is written."""
    sys.path.insert(0, str(ROOT / "step1"))
    import lasset_step1 as S
    PL.selftest(log)
    tune = S.test_modules()
    ok, present = check_runs("assets_tuning18", VERSION, tune, None, log)
    return readings(_levers("assets_tuning18", present, PL.TUNING_MAP_DIR, ROOT / "RTL_data"), log)


def read(log=print, again: bool = False) -> dict:
    """The held-out readings. Refuses on any changed pinned file or any run folder that does not match, and refuses a
    second reading (heldout_readings.json exists) unless again=True; a second reading must be reported as one."""
    if OUT_JSON.exists() and not again:
        log(f"REFUSED: {OUT_JSON.name} exists, so the held-out set has been read once already. Pass again=True only to "
            f"reprint the same numbers, and say so.")
        return {}
    if not verify_prereg(log):
        log("REFUSED: a pre-registered file changed. Nothing is scored.")
        return {}
    PL.selftest(log)
    sys.path.insert(0, str(ROOT / "step1"))
    import build_heldout_code_map as CM
    held = CM.heldout_modules()
    ok, present = check_runs(STEM_HELDOUT, VERSION, held, PARSED_HELDOUT, log)
    if not ok:
        log("REFUSED: a run folder is missing or holds another prompt, model or closed set. Nothing is scored.")
        return {}
    if len(present) < len(held):
        log(f"scoring the {len(present)} modules present in all 3 runs; excluded {sorted(set(held) - set(present))}")
    for k in (0, 1, 2):
        n = len(AT.trace_run(VERSION, k, map_dir=PL.HELDOUT_MAP_DIR, stem=STEM_HELDOUT, rtl_dir=RTL_HELDOUT))
        log(f"   traces r{k}: {n} records -> {AT.out_root(VERSION, PL.HELDOUT_MAP_DIR, STEM_HELDOUT).relative_to(ROOT)}/r{k}")
    L = _levers(STEM_HELDOUT, present, PL.HELDOUT_MAP_DIR, RTL_HELDOUT)
    for m in L.modules:                      # the GT overlay touches tuning modules only
        assert L.refs["corrected"][m] == L.refs["original"][m], m
    res = readings(L, log)
    res["excluded_modules"] = sorted(set(held) - set(present))
    OUT_JSON.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    log(f"\nwrote {OUT_JSON.relative_to(ROOT)}")
    return res


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--heldout" in sys.argv[1:]:
        read()
    elif "--tuning" in sys.argv[1:]:
        dry_run_tuning()
    else:
        print(__doc__)
