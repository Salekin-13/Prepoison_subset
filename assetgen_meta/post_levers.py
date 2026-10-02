"""Post-generation levers, FROZEN: the code filters applied to the executor's asset lists after generation. No model call.

What each lever does (one run of the executor = one asset list per module; an "element" is one (entity, name) entry):
  NONE   drop an element whose trace path is "none": the reasoning quotes none of its lines AND the relation map does not
         confirm its realization label (assetgen_meta/asset_trace.py; also every element missing from the map).
  BF     back-fill: add a whole input port (not a record field) the run did not list, when its value reaches, within
         HOPS=2 CARRIES/SOURCES steps of the relation map, an element the SAME run labelled stores or computes.
         Never added: clock / reset / clock-enable inputs (a SEQUENCES or RESETS relationship, or a name matching
         (^|_)(clk|rst|rstn|clkgen)(_|$)) and record-typed ports (they carry whole bus transactions). Objective: Integrity.
  GUARD  drop an internal record field (a signal named <record>.<field>) that never appears in an if / when / case
         condition (SITE tags IF_COND, WHEN_COND, CASE_EXPR). Derived from the tuning ground truth: OVERFITTED, so it is
         only ever a secondary row.
  MV     majority vote over the 3 runs (meta_tools.majority): keep an element found in at least 2 of 3.
A stack name lists its filters in the order they are applied to each run; "MV+" means the vote is taken last, over the
three filtered runs. Example: "MV+NONE+BF+GUARD" = NONE, then BF, then GUARD on each run, then the vote.

The definitions are scratchpad levers.py's (whose self-test reproduced the recorded numbers), parameterised by: version,
run-folder stem, module list, map folder, RTL folder and the condition source. The condition source is "codetags" (the
code SITE tags saved beside each code map, step1/code_site_tags.py; works on any RTL) or "llm" (the v3d profiler's tags;
tuning modules only, kept for cross-checks).

Scoring is eval_assets.score, strict, on the given modules only. A stack without MV reports the MEAN of the 3 runs'
precision and recall; an MV stack reports the one voted list. The LAsset row scores ground_truth/lasset_initial.json
(LAsset's initial asset lists, before its CWE refinement) on the same modules: the external comparison row.

Self-test (python assetgen_meta/post_levers.py): on the 15 tuning modules, stem assets_tuning18, version m7e194es0ism,
the code-tag maps (step1/lasset_step1/relation_map_code_tuning/b0e767000ec2_codetags) and code-tag conditions, every
recorded stack result and the LAsset initial row must reproduce to 3 decimals. Nothing is reported if one does not.
"""
from __future__ import annotations

import contextlib
import json
import os
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eval_assets as ea          # noqa: E402
import meta_tools as mt           # noqa: E402
import asset_trace as AT          # noqa: E402
import gt_overlay                 # noqa: E402

CODE_PAIRS_SHA = "b0e767000ec2"
TUNING_MAP_DIR = ROOT / "step1/lasset_step1/relation_map_code_tuning" / f"{CODE_PAIRS_SHA}_codetags"
HELDOUT_MAP_DIR = ROOT / "step1/lasset_step1/relation_map_code_heldout" / f"{CODE_PAIRS_SHA}_codetags"
SITES_SUBDIR = "_sites"
WINNER = "m7e194es0ism"

# ---------------------------------------------------------------------------------------- frozen definitions ---
COND = frozenset({"IF_COND", "WHEN_COND", "CASE_EXPR"})              # GUARD: the condition SITEs
CLKRST = re.compile(r"(^|_)(clk|rst|rstn|clkgen)(_|$)", re.I)        # BF: clock / reset / clock-enable names
BF_SKIP_TYPES = {"SEQUENCES", "RESETS"}                              # BF: clock / reset by relationship type
BF_WALK_TYPES = ("CARRIES", "SOURCES")                               # BF: the value-flow relationships walked
BF_HELD_LABELS = {"stores", "computes"}                              # BF: what the run must have labelled
HOPS = 2
FILTERS = ("NONE", "GUARD", "BF")

# Every stack the readings use. The tuning reference values (precision, recall; 111 GT entries per run) are the
# recorded ones this module's self-test must reproduce.
TUNING_RECORDED = {
    "base": (0.344, 0.847), "NONE": (0.376, 0.844), "GUARD": (0.451, 0.793), "BF": (0.350, 0.874),
    "NONE+BF": (0.382, 0.871), "GUARD+BF": (0.453, 0.805), "NONE+GUARD": (0.471, 0.790), "NONE+GUARD+BF": (0.473, 0.802),
    "MV": (0.357, 0.874), "MV+NONE": (0.388, 0.874), "MV+GUARD": (0.472, 0.820), "MV+BF": (0.362, 0.901),
    "MV+NONE+BF": (0.394, 0.901), "MV+GUARD+BF": (0.472, 0.829), "MV+NONE+GUARD": (0.495, 0.820),
    "MV+NONE+GUARD+BF": (0.495, 0.829), "MV+NONE+BF+GUARD": (0.500, 0.847)}
LASSET_TUNING_RECORDED = (0.737, 0.910, 137)
STACKS = tuple(TUNING_RECORDED)


def parse_stack(name: str) -> tuple[tuple[str, ...], bool]:
    """'MV+NONE+BF' -> (('NONE', 'BF'), True); 'base' -> ((), False). RAND is GUARD's random-thinning stand-in."""
    parts = [] if name in ("base", "MV") else name.split("+")
    mv = name == "MV" or (parts[:1] == ["MV"])
    filt = tuple(p for p in parts if p != "MV")
    bad = [p for p in filt if p not in FILTERS + ("RAND",)]
    if bad:
        raise ValueError(f"unknown filter(s) {bad} in stack {name!r}")
    return filt, mv


@contextlib.contextmanager
def _at(path):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def references(root: Path = ROOT) -> dict:
    """{'original': manual GT, 'corrected': gt_overlay-corrected GT, 'lasset_initial': LAsset's initial lists}."""
    refs = ea.load_refs(gt_dir=Path(root) / "ground_truth", parsed_dir=Path(root) / "parsed_tuning18")
    return {"original": refs["gt"], "corrected": gt_overlay.corrected(refs["gt"]), "lasset_initial": refs["paper"]}


def load_sites_codetags(m: str, map_dir: Path) -> dict:
    d = json.loads((Path(map_dir) / SITES_SUBDIR / f"{m}.json").read_text(encoding="utf-8"))
    return {(ent, n): {s for tags in occ.values() for s in tags} for ent, els in d.items() for n, occ in els.items()}


def load_sites_llm(m: str) -> dict:
    sys.path.insert(0, str(ROOT / "step1"))
    import relation_experiments as RX
    import relation_stage as RS
    return {(e["entity"], n): {s for r in rows for s in r.get("SITE Tagged", [])}
            for e in RS.load_module(m, RX.where(None)) for n, rows in e["profile"].items()}


class Levers:
    """The frozen levers on one executor version's runs. Nothing is written."""

    def __init__(self, version: str = WINNER, stem: str = "assets_tuning18", modules=None, map_dir: Path = TUNING_MAP_DIR,
                 rtl_dir: Path = ROOT / "RTL_data", cond: str = "codetags", reps=(0, 1, 2), root: Path = ROOT):
        self.version, self.stem, self.reps, self.root = version, stem, tuple(reps), Path(root)
        self.map_dir, self.rtl_dir, self.cond = Path(map_dir), Path(rtl_dir), cond
        self.dirs = [self.root / f"{stem}_{version}_r{k}" for k in self.reps]
        self.runs = [ea.load_run(d) for d in self.dirs]
        self.modules = sorted(modules) if modules is not None else sorted(set.intersection(*(set(r) for r in self.runs)))
        self.M = set(self.modules)
        self.refs = references(self.root)
        self.MAP, self.SITES, self.TR = {}, {}, {}
        for m in self.modules:
            d = json.loads((self.map_dir / f"{m}.json").read_text(encoding="utf-8"))
            self.MAP[m] = {(e["entity"], e["name"]): dict(e, _arr=a) for a in ("ports", "signals") for e in d[a]}
            for k, v in (load_sites_codetags(m, self.map_dir) if cond == "codetags" else load_sites_llm(m)).items():
                self.SITES[(m,) + k] = v
        for i, d in enumerate(self.dirs):
            for m in self.modules:
                idx = defaultdict(lambda: {"paths": set(), "labels": set()})
                f = d / "_nested" / f"{m}.json"
                concepts = json.loads(f.read_text(encoding="utf-8")).get("conceptual assets", []) if f.exists() else []
                for r in AT.trace_concepts(m, concepts, map_dir=self.map_dir, rtl_dir=self.rtl_dir):
                    idx[(r.get("entity", ""), r["element"])]["paths"].add(r["path"])
                    idx[(r.get("entity", ""), r["element"])]["labels"].add(r["realization"])
                self.TR[(i, m)] = idx

    # ------------------------------------------------------------------ element facts (levers.py, unchanged)
    def mentry(self, m, ent, name):
        e = self.MAP[m].get((ent, name))
        if e is None:
            c = [x for (en, n), x in self.MAP[m].items() if n == name]
            e = c[0] if len(c) == 1 else None
        return e

    def internal_field(self, m, ent, name):
        e = self.mentry(m, ent, name)
        return bool(e) and "." in name and e["_arr"] == "signals"

    def in_guard(self, m, ent, name):
        e = self.mentry(m, ent, name)
        en = e["entity"] if e else ent
        return bool(self.SITES.get((m, en, name), set()) & COND)

    def trace_of(self, i, m, ent, name):
        t = self.TR[(i, m)]
        if (ent, name) in t:
            return t[(ent, name)]
        hits = [x for (en, n), x in t.items() if n == name]
        return hits[0] if hits else {"paths": set(), "labels": set()}

    # ------------------------------------------------------------------ the filters on one run (i = run index)
    def f_none(self, i, run):
        return {m: [x for x in lst if m not in self.M or self.trace_of(i, m, x[0], x[1])["paths"] - {"none"}]
                for m, lst in run.items()}

    def f_guard(self, i, run):
        return {m: [x for x in lst if m not in self.M or not self.internal_field(m, x[0], x[1]) or self.in_guard(m, x[0], x[1])]
                for m, lst in run.items()}

    def f_backfill(self, i, run, hops=HOPS, name_rule=True):
        out = {m: list(lst) for m, lst in run.items()}
        for m in self.modules:
            rep = {(x[0], x[1]) for x in run.get(m, [])}
            held = {key for key in rep if self.trace_of(i, m, *key)["labels"] & BF_HELD_LABELS}
            held_names = {n for _e, n in held}
            for (ent, name), e in self.MAP[m].items():
                if e["_arr"] != "ports" or "." in name or (e.get("boundary") or {}).get("mode") != "in" or (ent, name) in rep:
                    continue
                if any(n.startswith(name + ".") for (en, n) in self.MAP[m] if en == ent):      # record-typed port
                    continue
                ts = {r["type"] for r in e.get("relationship", [])}
                if ts & BF_SKIP_TYPES or (name_rule and CLKRST.search(name)):                 # clock / reset / enable
                    continue
                frontier, seen = {name}, set()
                for _ in range(hops):
                    nxt = set()
                    for n in frontier:
                        for r in (self.MAP[m].get((ent, n)) or {}).get("relationship", []):
                            if r["type"] in BF_WALK_TYPES:
                                nxt |= set(r["targets"])
                    seen |= nxt
                    frontier = nxt
                if seen & held_names:
                    out.setdefault(m, []).append((ent, name, "Integrity"))
        return out

    def f_rand(self, i, run, rng):
        """GUARD's random-thinning stand-in: in each module, drop as many elements as GUARD would drop from this same
        input, chosen uniformly at random from the module's listed elements."""
        g = self.f_guard(i, run)
        out = {}
        for m, lst in run.items():
            if m not in self.M:
                out[m] = list(lst)
                continue
            drop = set(rng.sample(range(len(lst)), len(lst) - len(g[m])))
            out[m] = [x for j, x in enumerate(lst) if j not in drop]
        return out

    # ------------------------------------------------------------------ stacks and scoring
    def filtered_runs(self, name, bf_name_rule=True, rng=None, post=None) -> list[dict]:
        """The three runs after the stack's filters (no vote). post(run) is applied last (e.g. convention_filter)."""
        filt, _mv = parse_stack(name)
        out = []
        for i, run in enumerate(self.runs):
            r = run
            for f in filt:
                r = (self.f_none(i, r) if f == "NONE" else self.f_guard(i, r) if f == "GUARD" else
                     self.f_backfill(i, r, name_rule=bf_name_rule) if f == "BF" else self.f_rand(i, r, rng))
            out.append(post(r) if post else r)
        return out

    def lists(self, name, **kw) -> list[dict]:
        """The scored asset lists of a stack: the 3 filtered runs, or the 1 voted list for an MV stack."""
        runs = self.filtered_runs(name, **kw)
        return [mt.majority(runs)[0]] if parse_stack(name)[1] else runs

    def _score(self, lists, gt):
        sc = [ea.score(r, self.refs[gt], strict=True, only=self.M) for r in lists]
        n = len(sc)
        return {"precision": sum(s["precision"] for s in sc) / n, "recall": sum(s["recall"] for s in sc) / n,
                "emit": sum(s["emit"] for s in sc) / n, "tp": sum(s["tp"] for s in sc) / n, "fp": sum(s["fp"] for s in sc) / n,
                "ref": sc[0]["ref"], "lists": n,
                "per_list": [(s["precision"], s["recall"], s["emit"], s["tp"], s["fp"]) for s in sc],
                "per_module": [{m: (s["per_module"][m]["tp"], len(s["per_module"][m]["fp"]), s["per_module"][m]["ref"])
                                for m in self.modules if m in s["per_module"]} for s in sc]}

    def score(self, name="base", gt="original", **kw) -> dict:
        """P / R / emitted / TP / FP of a stack (mean of 3 runs, or the voted list), on self.modules."""
        with _at(self.root):                       # convention_filter, when passed as post, reads parsed_tuning18/
            return self._score(self.lists(name, **kw), gt)

    def lasset(self, gt="original", which="lasset_initial") -> dict:
        """The external row: LAsset's initial asset lists (no CWE refinement) on the same modules."""
        s = ea.score(self.refs[which], self.refs[gt], strict=True, only=self.M)
        return {"precision": s["precision"], "recall": s["recall"], "emit": s["emit"], "tp": s["tp"], "fp": s["fp"],
                "ref": s["ref"], "modules": sorted(set(s["per_module"]))}

    # ------------------------------------------------------------------ uncertainty and baselines
    @staticmethod
    def _pr(pm_list, mods):
        ps, rs = [], []
        for pm in pm_list:
            tp = sum(pm[m][0] for m in mods if m in pm); fp = sum(pm[m][1] for m in mods if m in pm)
            g = sum(pm[m][2] for m in mods if m in pm)
            ps.append(tp / max(tp + fp, 1)); rs.append(tp / max(g, 1))
        return sum(ps) / len(ps), sum(rs) / len(rs)

    def bootstrap(self, a: str, b: str, gt="original", n=10000, seed=0, **kw) -> dict:
        """a minus b, precision and recall, with a module bootstrap 95% interval: resample the modules with
        replacement (random.Random(seed), n resamples), recompute both stacks' P and R on the resample.
        kw (bf_name_rule, post) is applied to both stacks."""
        A, B = self.score(a, gt, **kw)["per_module"], self.score(b, gt, **kw)["per_module"]
        pa, ra = self._pr(A, self.modules); pb, rb = self._pr(B, self.modules)
        rng, dp, dr = random.Random(seed), [], []
        for _ in range(n):
            mods = [rng.choice(self.modules) for _ in self.modules]
            x, y = self._pr(A, mods), self._pr(B, mods)
            dp.append(x[0] - y[0]); dr.append(x[1] - y[1])
        dp.sort(); dr.sort()
        lo, hi = int(0.025 * n), int(0.975 * n)
        return {"a": a, "b": b, "dP": pa - pb, "dP_lo": dp[lo], "dP_hi": dp[hi], "dR": ra - rb, "dR_lo": dr[lo], "dR_hi": dr[hi],
                "resamples": n, "seed": seed, "modules": len(self.modules)}

    def random_thinning(self, name: str, gt="original", draws=1000, seed=0) -> dict:
        """The stack with GUARD replaced by RAND (same number dropped per run and module, chosen at random)."""
        assert "GUARD" in parse_stack(name)[0], name
        rname = name.replace("GUARD", "RAND")
        rng, ps, rs = random.Random(seed), [], []
        for _ in range(draws):
            s = self.score(rname, gt, rng=rng)
            ps.append(s["precision"]); rs.append(s["recall"])
        g = self.score(name, gt)
        srt = sorted(ps)
        return {"stack": name, "guard_P": g["precision"], "guard_R": g["recall"], "rand_P_mean": sum(ps) / draws,
                "rand_R_mean": sum(rs) / draws, "rand_P_lo": srt[int(0.025 * draws)], "rand_P_hi": srt[int(0.975 * draws)],
                "share_rand_P_ge_guard": sum(p >= g["precision"] - 1e-12 for p in ps) / draws, "draws": draws, "seed": seed}

    def lever_effect(self, lever: str, gt="original") -> dict:
        """One filter alone on each unfiltered run, mean per run: what it removes or adds and how much is FP / TP."""
        tot = defaultdict(float)
        for i, run in enumerate(self.runs):
            after = self.filtered_runs(lever)[i]
            s0 = ea.score(run, self.refs[gt], strict=True, only=self.M); s1 = ea.score(after, self.refs[gt], strict=True, only=self.M)
            b = {(m, x[0], x[1]) for m in self.modules for x in run.get(m, [])}
            a = {(m, x[0], x[1]) for m in self.modules for x in after.get(m, [])}
            tot["removed"] += len(b - a); tot["added"] += len(a - b)
            tot["fp_removed"] += max(s0["fp"] - s1["fp"], 0); tot["tp_lost"] += max(s0["tp"] - s1["tp"], 0)
            tot["tp_gained"] += max(s1["tp"] - s0["tp"], 0); tot["fp_added"] += max(s1["fp"] - s0["fp"], 0)
        n = len(self.runs)
        out = {k: v / n for k, v in tot.items()}
        out["share_fp_of_removed"] = tot["fp_removed"] / tot["removed"] if tot["removed"] else None
        out["share_tp_of_added"] = tot["tp_gained"] / tot["added"] if tot["added"] else None
        return out

    def convention_matches(self) -> list[int]:
        """Per run: elements meta_tools.convention_filter would drop (bus-transaction records, clk*/rst* inputs)."""
        with _at(self.root):
            return [sum(len(r.get(m, [])) - len(mt.convention_filter({m: r.get(m, [])})[m]) for m in self.modules)
                    for r in self.runs]

    def missing(self, modules) -> list[list[str]]:
        """Per run: requested modules with no output file."""
        return [sorted(set(modules) - set(r)) for r in self.runs]


# ------------------------------------------------------------------------------------------------- self-test ---
def selftest(log=print) -> dict:
    """The tuning reproduction. -> {stack: score dict}; raises AssertionError when a number does not reproduce."""
    sys.path.insert(0, str(ROOT / "step1"))
    import lasset_step1 as S
    tune = S.test_modules()
    L = Levers(WINNER, "assets_tuning18", tune, TUNING_MAP_DIR, ROOT / "RTL_data", cond="codetags")
    res, bad = {}, []
    for name, want in TUNING_RECORDED.items():
        s = L.score(name)
        res[name] = s
        if (round(s["precision"], 3), round(s["recall"], 3)) != want:
            bad.append((name, want, (round(s["precision"], 3), round(s["recall"], 3))))
    la = L.lasset()
    if (round(la["precision"], 3), round(la["recall"], 3), la["emit"]) != LASSET_TUNING_RECORDED:
        bad.append(("LAsset initial", LASSET_TUNING_RECORDED, (round(la["precision"], 3), round(la["recall"], 3), la["emit"])))
    res["LAsset initial"] = la
    if res["base"]["ref"] != 111 or len(tune) != 15:
        bad.append(("denominator", (15, 111), (len(tune), res["base"]["ref"])))
    if bad:
        raise AssertionError(f"post_levers self-test FAIL: {bad}")
    log(f"post_levers self-test PASS: {len(TUNING_RECORDED)} stacks and the LAsset initial row reproduce to 3 decimals "
        f"(15 tuning modules, {res['base']['ref']} GT entries per run, code-tag maps and conditions)")
    return res


def table(res: dict, lasset: dict, log=print) -> None:
    log(f"{'stack':20s} {'P':>6s} {'R':>6s} {'emit':>6s} {'TP':>6s} {'FP':>6s}   | LAsset initial, same modules: "
        f"P {lasset['precision']:.3f} R {lasset['recall']:.3f} emitted {lasset['emit']}")
    for name, s in res.items():
        if name == "LAsset initial":
            continue
        log(f"{name:20s} {s['precision']:6.3f} {s['recall']:6.3f} {s['emit']:6.1f} {s['tp']:6.1f} {s['fp']:6.1f}"
            f"   ({'1 voted list' if s['lists'] == 1 else 'mean of 3 runs'})")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        r = selftest()
    except AssertionError as e:
        print(e, "\nnothing is reported")
        sys.exit(1)
    table(r, r["LAsset initial"])
