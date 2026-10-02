"""Score a hand arm against the seed (and other references), with the readouts pre-registered on the roadmap page.

score(new, refs) prints:
 1 precision / recall / items per run (strict, the 15 development modules, 111 ground-truth entries)
 2 the Step 1b verdict: counts iff mean-of-3 recall >= 0.83 and mean precision >= 0.326
 3 exact permutation tests against the seed (3 vs 3 runs; p = 0.10 is the lowest possible)
 4 ground-truth hits and false positives per run by element kind; input-port hits (the seed has 15.0 per run)
 5 realization labels and objectives per run; parse / validation problems
 6 majority vote (a separate number, not the Step 1b metric)
 7 the seed's usual misses the new arm finds, and new misses
The element-kind classifier and the permutation test are self-tested (hand-read lines of RTL_data/neorv32_uart.vhd).
Moved here from the session scratchpad (score_bases.py / score_i01b.py, validated by reproducing v5s's known numbers).
"""
from __future__ import annotations

import io, contextlib, itertools, json, re, statistics as st, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "assetgen_meta"))
import eval_assets as ea   # noqa: E402
import meta_tools as mt    # noqa: E402

SEED, BASELINE = "m7e194es0c", "v2x3r8"
TXN = re.compile(r"\bbus_(req|rsp)_t\b")
OTHER_RR = re.compile(r"\b(dev|port|dmi)_(req|rsp)_t\b")
CLKRST = re.compile(r"(clk|rst|rstn)(_|$)")


def load_decl(parsed_dir=ROOT / "data/parsed_tuning18"):
    out = {}
    for f in sorted(Path(parsed_dir).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        ports, sigs = defaultdict(list), defaultdict(list)
        for e in d["ports"]:
            ports[e["name"]].append(e)
        for e in d["signals"]:
            sigs[e["name"]].append(e)
        out[f.stem] = (ports, sigs)
    return out


def kind(mod, name, ent, decl):
    ports, sigs = decl.get(mod, ({}, {}))
    base, dotted = name.split(".")[0], "." in name

    def pick(tbl, n):
        lst = tbl.get(n, [])
        return next((e for e in lst if e.get("entity") == ent), lst[0] if lst else None)

    if base in ports:
        e = pick(ports, base); t = e.get("type", "")
        if TXN.search(t):
            return "txn bus_req/rsp_t (port" + (" field)" if dotted else ")")
        if OTHER_RR.search(t):
            return "other req/rsp record (port" + (" field)" if dotted else ")")
        if dotted:
            return "port-field"
        if e.get("dir") == "in" and CLKRST.match(base):
            return "clock/reset input"
        return "port-in" if e.get("dir") == "in" else "port-out"
    if base in sigs:
        e = pick(sigs, base); t = e.get("type", "")
        if TXN.search(t):
            return "txn bus_req/rsp_t (signal" + (" field)" if dotted else ")")
        if OTHER_RR.search(t):
            return "other req/rsp record (signal" + (" field)" if dotted else ")")
        return "signal-field" if dotted else "signal"
    return "absent from closed set"


def perm_p(a, b):
    """Exact two-sided permutation p for a difference in means, all relabellings."""
    pool, k = list(a) + list(b), len(a)
    obs = abs(st.mean(a) - st.mean(b)); n = hit = 0
    for idx in itertools.combinations(range(len(pool)), k):
        x = [pool[i] for i in idx]; y = [pool[i] for i in range(len(pool)) if i not in idx]
        n += 1; hit += abs(st.mean(x) - st.mean(y)) >= obs - 1e-12
    return hit / n


def selftest(decl):
    rtl = (ROOT / "data/RTL_data/neorv32_uart.vhd").read_text(encoding="utf-8", errors="ignore").splitlines()
    assert re.match(r"\s*clk_i\s*:\s*in\s+std_ulogic", rtl[31]), rtl[31]
    assert re.match(r"\s*bus_req_i\s*:\s*in\s+bus_req_t", rtl[33]), rtl[33]
    assert re.match(r"\s*clkgen_en_o\s*:\s*out\s+std_ulogic", rtl[35]), rtl[35]
    assert re.match(r"\s*signal uart_clk\s*:\s*std_ulogic", rtl[90]), rtl[90]
    assert re.match(r"\s*signal ctrl\s*:\s*ctrl_t", rtl[107]), rtl[107]
    m = "neorv32_uart"
    exp = {"clk_i": "clock/reset input", "bus_req_i": "txn bus_req/rsp_t (port)", "clkgen_en_o": "port-out",
           "uart_clk": "signal", "ctrl.enable": "signal-field", "uart_rxd_i": "port-in", "no_such_thing": "absent from closed set"}
    got = {n: kind(m, n, m, decl) for n in exp}
    assert got == exp, got
    assert abs(perm_p([1, 2, 3], [4, 5, 6]) - 0.10) < 1e-12 and perm_p([1, 1, 1], [1, 1, 1]) == 1.0


def score(new: str, refs=(BASELINE, SEED), n_runs=3):
    with contextlib.redirect_stdout(io.StringIO()):
        gt = ea.load_refs()["gt"]
        runs = ea.collect(list(refs) + [new])
    decl = load_decl(); selftest(decl)
    assert new in runs and len(runs[new]) >= n_runs, f"{new}: {len(runs.get(new, []))} complete runs, need {n_runs}"
    common = ea.common_modules(runs, gt); NGT = sum(len(gt[m]) for m in common)
    print(f"{len(common)} modules, {NGT} ground-truth entries (exact); runs { {v: len(r) for v, r in runs.items()} }")
    sc = {v: [ea.score(r, gt, strict=True, only=common) for r in runs[v]] for v in runs}
    order = list(refs) + [new]

    print("\n1) precision / recall / items per run (strict)")
    for v in order:
        s = sc[v]; P = st.mean(x["precision"] for x in s); R = st.mean(x["recall"] for x in s); E = st.mean(x["emit"] for x in s)
        print(f"   {v:14s} P {P:.3f} R {R:.3f} items {E:6.1f} ({E / NGT:.2f}x GT) | per run P {[round(x['precision'], 3) for x in s]} "
              f"R {[round(x['recall'], 3) for x in s]} items {[x['emit'] for x in s]}")
    Pn = st.mean(x["precision"] for x in sc[new]); Rn = st.mean(x["recall"] for x in sc[new])
    print(f"\n2) STEP 1b VERDICT: recall {Rn:.3f} {'>=' if Rn >= 0.83 else '<'} 0.83; precision {Pn:.3f} "
          f"{'>=' if Pn >= 0.326 else '<'} 0.326 -> {'COUNTS' if Rn >= 0.83 and Pn >= 0.326 else 'does NOT count'}")

    if SEED in sc:
        print("\n3) exact permutation test against the seed (3 vs 3; p = 0.10 is the lowest possible)")
        for key in ("precision", "recall", "emit", "tp", "fp"):
            a = [x[key] for x in sc[SEED]]; b = [x[key] for x in sc[new]]
            print(f"   {key:9s} seed {[round(x, 3) for x in a]} new {[round(x, 3) for x in b]} "
                  f"diff {st.mean(b) - st.mean(a):+.3f} p={perm_p(a, b):.2f}")

    print("\n4) ground-truth hits and false positives per run, by element kind")
    gt_kind = Counter(kind(m, e, m, decl) for m in common for e, _o in gt[m])

    def per_kind(v):
        hit, fp = Counter(), Counter()
        for r, s in zip(runs[v], sc[v]):
            for m in common:
                pm = s["per_module"][m]
                got = Counter(e for e, _o in gt[m]) - Counter(pm["fn"])
                for e, c in got.items():
                    hit[kind(m, e, m, decl)] += c
                for n in pm["fp"]:
                    ent = next((x[0] for x in r.get(m, []) if x[1] == n), m)
                    fp[kind(m, n, ent, decl)] += 1
        k = len(runs[v])
        return {c: hit[c] / k for c in hit}, {c: fp[c] / k for c in fp}
    H = {v: per_kind(v) for v in order}
    print(f"   {'kind':32s} {'GT':>4s} | hits/run " + " ".join(f"{v[:12]:>12s}" for v in order) + " | FP/run " +
          " ".join(f"{v[:12]:>12s}" for v in order))
    for c in sorted(set(gt_kind) | {k for v in order for k in H[v][1]}):
        print(f"   {c:32s} {gt_kind.get(c, 0):4d} | " + " ".join(f"{H[v][0].get(c, 0):12.1f}" for v in order) + " |        " +
              " ".join(f"{H[v][1].get(c, 0):12.1f}" for v in order))
    inp = H[new][0].get("port-in", 0)
    print(f"   input-port hits per run: {inp:.1f} (seed {H[SEED][0].get('port-in', 0) if SEED in H else float('nan'):.1f})")

    print("\n5) realization labels and objectives per run; parse and validation")
    for v in [x for x in order if x.startswith("m")]:
        lab, obj, missing = Counter(), Counter(), 0
        for rep in range(len(runs[v])):
            d = ROOT / f"runs/assets_tuning18_{v}_r{rep}"
            for m in common:
                f = d / "_nested" / f"{m}.json"
                if not f.exists():
                    missing += 1; continue
                o = json.loads(f.read_text(encoding="utf-8"))
                for ca in o.get("conceptual assets", []):
                    obj[ca.get("security objective")] += 1
                    for sa in ca.get("related structural assets", []):
                        lab[sa.get("realization")] += 1
        k = len(runs[v])
        print(f"   {v:14s} realization/run { {a: round(b / k, 1) for a, b in lab.most_common()} } | objectives/run "
              f"{ {a: round(b / k, 1) for a, b in obj.most_common()} } | missing nested files {missing}")
    for rep in range(len(runs[new])):
        vp = ROOT / f"runs/assets_tuning18_{new}_r{rep}/_validation.json"
        if vp.exists():
            val = json.loads(vp.read_text(encoding="utf-8"))
            print(f"   {new} r{rep}: validation issues {sum(len(x) for x in val.values())} "
                  f"{dict(Counter(i['kind'] for x in val.values() for i in x))}")

    print("\n6) majority vote (a separate number, not the Step 1b metric)")
    for v in order:
        mv, _c = mt.majority(runs[v]); s = ea.score(mv, gt, strict=True, only=common)
        print(f"   {v:14s} P {s['precision']:.3f} R {s['recall']:.3f} items {s['emit']}")

    if SEED in sc:
        def misses(v):
            c = Counter((m, e) for s in sc[v] for m, pm in s["per_module"].items() for e in pm["fn"])
            return {k for k, n in c.items() if n >= 2}
        ms, mn = misses(SEED), misses(new)
        print(f"\n7) missed in >= 2 of 3 runs: seed {len(ms)}, new {len(mn)}; recovered {len(ms - mn)}, newly lost {len(mn - ms)}")
        print(f"   recovered: {sorted(f'{m[8:]}:{e}' for m, e in ms - mn)}")
        print(f"   newly lost: {sorted(f'{m[8:]}:{e}' for m, e in mn - ms)}")
    return {"P": Pn, "R": Rn}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    score(sys.argv[1] if len(sys.argv) > 1 else "m7e194es0i01b", tuple(sys.argv[2:]) or (BASELINE, SEED))
