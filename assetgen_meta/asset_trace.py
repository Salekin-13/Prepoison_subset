"""Asset trace: rebuild, after generation, the evidence path behind every structural asset the generator reported.

For each structural asset in a generator output (assets_tuning18_<version>_r<rep>/_nested/<module>.json) the trace
follows one path, with code only -- no model call and no prompt change:

    quoted RTL line -> occurrence ID -> relationship records -> does the map confirm the realization label -> why

 * quoted RTL line   The concept's reasoning usually writes RTL statements out verbatim, without quote marks. A line on
                     which the element occurs is "quoted" when the reasoning contains the whole line ("full") or a
                     fragment of the line that contains the element's name, as a whole identifier, plus at least
                     PARTIAL_EXTRA more characters ("partial"). Both texts are compared lower-case with every
                     whitespace character removed, so spacing and missing quote marks do not matter.
 * occurrence ID     The code-written relation map (rel_view.CODE_MAP_DIR) lists every occurrence of an element with its
                     ORIGINAL file line. A quote carries the IDs of the element's occurrences on the quoted line.
 * records           The element's relationship records whose `at` holds one of those IDs.
 * confirmation      One code rule per realization label (RULES) says whether the map supports the label, and at
                     which occurrences. The rules are evaluation code; they are never prompt text.
 * why               The concept's reasoning, complete.

Path status of one record:
    full                         a quoted occurrence is one that confirms the label
    confirmed, quoted elsewhere  the label is confirmed; the reasoning quotes other occurrences of the element
    confirmed, not quoted        the label is confirmed; no occurrence of the element is quoted
    quoted, not confirmed        occurrences are quoted; the label is not confirmed
    none                         neither (also every element that is not in the map)

The generator saw the comment-stripped RTL (rtl_parse.strip_comments, as meta_tools.run_version reads it), whose line
numbers differ from the file's; line_table() converts between the two. Elements are keyed by (module, entity, name),
never by (module, name): two entities of one file can declare the same name.

A trace record holds no ground-truth field, so it can be built for a module that has no ground truth. evaluate() adds
TP/FP in memory with the project's scorer matching (eval_assets._hit_idx, strict, each prediction consumed once, as
eval_assets.score does) and checks its result against eval_assets.score for every module-run.

Files (all under assetgen_meta/traces/):
    <version>/r<rep>/<module>.json   the trace records of one module-run (a JSON list)
    <version>/r<rep>/_index.json     map folder, rules, record counts for that run
    <version>/trace_report.md        readable report of every record of the traced runs
    <version>/summary.json           evaluate() results: the only file with TP/FP counts
    <version>/audit_sample.json      blind audit sample (CLI --audit); the key is in audit_key.json
A map folder other than rel_view.CODE_MAP_DIR writes under traces/<version>@<map folder name>/ instead, so traces built
on two maps never mix. A run-folder stem other than assets_tuning18 (trace_run(..., stem=, rtl_dir=), e.g. the held-out
run assets_heldout26 read from RTL_heldout/) writes under traces/<stem>/ with the same layout.

Run from the repo root; the self-test runs first and nothing is reported if it fails:
    python assetgen_meta/asset_trace.py m7e194es0ism m7e194es0c m7e194es0ismr [--audit]
"""
from __future__ import annotations

import json
import random
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eval_assets as ea   # noqa: E402  (repo root)
import rel_view as rv      # noqa: E402  (assetgen_meta)
import rtl_parse           # noqa: E402  (repo root)

RTL_DIR = ROOT / "RTL_data"
TRACE_DIR = HERE / "traces"
GT_DIR, PARSED_DIR = ROOT / "ground_truth", ROOT / "parsed_tuning18"
REPS = (0, 1, 2)
FULL_MIN = 10        # a whole line shorter than this (whitespace-free, trailing ';' dropped) is too generic to count
PARTIAL_EXTRA = 6    # a partial quote holds the element's name plus at least this many more characters of the line

PATHS = ("full", "confirmed, quoted elsewhere", "confirmed, not quoted", "quoted, not confirmed", "none")
RANK = {p: i for i, p in enumerate(PATHS)}          # lower is better; an element takes its best record's path
LABELS = ("stores", "sets", "computes", "exit port")

# ------------------------------------------------------------------------------------------------ rules ---
# Confirmation rules, evaluation code only. Per label: the condition, and the record types whose `at` occurrences
# confirm it.  stores: storage == "edge";  exit port: boundary mode "out";  sets: boundary mode "in" AND a record of
# the listed types (an internal element labelled sets is not confirmed);  computes: a record of the listed types.
DRIVING = ("CARRIES", "SOURCES", "SELECTS", "CONSTRAINS", "GATES")
RECEIVING = ("COPIES", "DERIVES_FROM", "CLOCKED_BY", "RESET_BY", "SELECTED_BY", "CONSTRAINED_BY", "GATED_BY")
RULES = {
    "default": {"stores": ("CLOCKED_BY",), "exit port": RECEIVING, "sets": DRIVING,
                "computes": ("DERIVES_FROM", "GATED_BY", "SELECTED_BY", "CONSTRAINED_BY")},
    # As the scratchpad prototype coded them (q3bc_trace.py confirm / q3f_path.py confirming_ids). Kept only to
    # show that the numbers reproduce; sets also took SEQUENCES/RESETS, computes lacked CONSTRAINED_BY.
    "prototype": {"stores": ("CLOCKED_BY",), "exit port": RECEIVING, "sets": DRIVING + ("SEQUENCES", "RESETS"),
                  "computes": ("DERIVES_FROM", "GATED_BY", "SELECTED_BY")},
}


def rule_text(label: str, rules: str = "default") -> str:
    t = ", ".join(RULES[rules].get(label, ()))
    return {"stores": "stores: assigned on a clock edge (map storage 'edge'); confirming occurrences: its CLOCKED_BY records",
            "exit port": f"exit port: port with boundary mode 'out'; confirming occurrences: its receiving records ({t})",
            "sets": f"sets: input port (boundary mode 'in') with a driving record ({t}); an internal element is not confirmed",
            "computes": f"computes: a receiving record ({t})"}.get(label, f"no rule for the label '{label}'")


# ------------------------------------------------------------------------------------------- line table ---

class LineTable:
    """Original file line <-> line of the comment-stripped text the generator saw (both 1-based).

    to_stripped[L] is None for a line that stripping removes (comment-only or blank). code[L] is the comment-stripped
    text of original line L, exactly as it appears in the generator's input."""

    def __init__(self, module: str, rtl_dir: Path = RTL_DIR):
        raw = (Path(rtl_dir) / f"{module}.vhd").read_text(encoding="utf-8", errors="ignore")   # as run_version reads it
        self.module = module
        self.original = raw.splitlines()
        self.to_stripped: dict[int, int | None] = {}
        self.to_original: dict[int, int] = {}
        self.code: dict[int, str] = {}
        kept = []
        for i, line in enumerate(self.original, 1):
            s = rtl_parse.strip_comments(line, vhdl=True)       # VHDL has line comments only: per line == whole file
            if s:
                kept.append(s)
                self.to_stripped[i], self.to_original[len(kept)], self.code[i] = len(kept), i, s
            else:
                self.to_stripped[i] = None
        self.stripped_text = rtl_parse.strip_comments(raw, vhdl=True)
        if "\n".join(kept) != self.stripped_text:
            raise AssertionError(f"{module}: per-line stripping differs from whole-file stripping")


@lru_cache(maxsize=None)
def line_table(module: str, rtl_dir: Path = RTL_DIR) -> LineTable:
    """rtl_dir: the folder the run read the module from (RTL_heldout/ for the held-out run)."""
    return LineTable(module, Path(rtl_dir))


# ------------------------------------------------------------------------------------------------- map ---

@lru_cache(maxsize=None)
def load_map(module: str, map_dir: Path = rv.CODE_MAP_DIR) -> dict:
    """{(entity, name): element} for one module; {} when the folder has no map for it."""
    p = rv.map_path(module, Path(map_dir))
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for arr in ("ports", "signals"):
        for e in d.get(arr, []):
            key = (e["entity"], e["name"])
            if key in out:
                raise AssertionError(f"{module}: element {key} listed twice")
            out[key] = e
    return out


def _rels(e):
    return (e or {}).get("relationship") or []


def _mode(e):
    return ((e or {}).get("boundary") or {}).get("mode")


def _occ_line(e):
    return {o["id"]: o["line"] for o in (e or {}).get("occurrences", [])}


# -------------------------------------------------------------------------------------------- matching ---

def nows(s: str) -> str:
    """Lower case, every whitespace character removed."""
    return re.sub(r"\s+", "", s or "").lower()


def _grow(t: str, R: str, s0: int, e0: int) -> tuple[int, int]:
    """Longest t[s:e] with s <= s0 and e >= e0 that is a substring of R, as (s, e); (s0, s0) when t[s0:e0] is not.
    The prototype's version carried the right end across left steps without re-checking it and could overstate
    the length; here the end is shrunk back until the fragment is in R again."""
    best, e = (s0, s0), e0
    for s in range(s0, -1, -1):
        if t[s:e0] not in R:
            break
        e = max(e, e0)
        while e > e0 and t[s:e] not in R:
            e -= 1
        while e < len(t) and t[s:e + 1] in R:
            e += 1
        if e - s > best[1] - best[0]:
            best = (s, e)
    return best


def _grow_v0(t, R, s0, e0):
    """The prototype's grow (scratchpad q3bc_trace.py), verbatim, for matcher='prototype' only."""
    best, e = 0, e0
    for s in range(s0, -1, -1):
        if t[s:e0] not in R:
            break
        e = max(e, e0)
        while e < len(t) and t[s:e + 1] in R:
            e += 1
        best = max(best, e - s)
    return best


def _name_spans(code: str, name: str) -> list[tuple[int, int]]:
    """(start, end) in nows(code) of every whole-identifier occurrence of `name` in the line.
    A record's base name counts before a field ('ctrl' in 'ctrl.enable'), as the map counts it."""
    low = code.lower()
    pre, n = [], 0                          # pre[i] = non-whitespace characters before position i
    for ch in low:
        pre.append(n)
        n += not ch.isspace()
    pre.append(n)
    nm = name.lower()
    return [(pre[m.start()], pre[m.start()] + len(nows(nm)))
            for m in re.finditer(rf"(?<![\w.]){re.escape(nm)}(?![\w])", low)]


def match_line(code: str, name: str, R: str, matcher: str = "default") -> tuple[str | None, str]:
    """-> ("full" | "partial" | None, matched whitespace-free text). R is nows(reasoning).
    matcher='prototype' reproduces the scratchpad prototype: the name may sit inside a longer identifier, and its
    grow() may overstate a fragment."""
    t = nows(code)
    tt = t.rstrip(";")
    if len(tt) >= FULL_MIN and tt in R:
        return "full", tt
    nm = nows(name)
    need = len(nm) + PARTIAL_EXTRA
    if matcher == "prototype":
        for mo in re.finditer(re.escape(nm), t):
            if _grow_v0(t, R, mo.start(), mo.end()) >= need:
                return "partial", t[mo.start():mo.end()]
        return None, ""
    best = (0, 0)
    for s0, e0 in _name_spans(code, name):
        s, e = _grow(t, R, s0, e0)
        if e - s > best[1] - best[0]:
            best = (s, e)
    if best[1] - best[0] >= need:
        return "partial", t[best[0]:best[1]]
    return None, ""


def quotes_for(e: dict, name: str, R: str, lt: LineTable, matcher: str = "default") -> list[dict]:
    """The element's occurrence lines that the reasoning quotes, one entry per line, in line order."""
    by_line = defaultdict(list)
    for o in e.get("occurrences", []):
        by_line[o["line"]].append(o["id"])
    out = []
    for L in sorted(by_line):
        code = lt.code.get(L)
        if code is None:
            raise AssertionError(f"{lt.module}: occurrence line {L} of {name} vanishes after comment stripping")
        kind, frag = match_line(code, name, R, matcher)
        if kind:
            out.append({"text": code.strip(), "original_line": L, "stripped_line": lt.to_stripped[L],
                        "occurrence_ids": sorted(by_line[L]), "match": kind, "matched": frag})
    return out


def records_at(e: dict, ids) -> list[dict]:
    """The element's relationship records whose `at` holds one of `ids`, one row per (occurrence, record)."""
    out = []
    for i in sorted(set(ids)):
        for r in _rels(e):
            if i in (r.get("at") or []):
                out.append({"occurrence_id": i, "type": r["type"], "targets": list(r.get("targets", [])),
                            "guard": r.get("guard")})
    return out


# -------------------------------------------------------------------------------------------- confirm ---

_WHOLE = r"^\s*(?:\w+\s*:\s*)?{}\s*<="        # '<base> <= ...' (optionally labelled): the whole record is the target


def confirm(e: dict | None, label: str, rules: str = "default", name: str = "", base: dict | None = None,
            extension: bool = False) -> dict:
    """-> {rule, confirmed, occurrence_ids, evidence}. occurrence_ids are the element's confirming occurrences
    (empty when the label is not confirmed).
    extension=True: a record FIELD labelled stores whose base record is assigned whole on a clock edge
    ('<rec> <= <rec>_nxt;' under rising_edge) is confirmed although the field's own storage is not 'edge'. The
    confirming occurrences then belong to the base, not the field, so occurrence_ids stays empty and the evidence
    names them; such a record can never have path 'full'."""
    rule = rule_text(label, rules)
    if label not in RULES[rules]:
        return {"rule": rule, "confirmed": False, "occurrence_ids": [], "evidence": ""}
    if e is None:
        return {"rule": rule, "confirmed": False, "occurrence_ids": [], "evidence": "element not in the map under this entity"}
    types = RULES[rules][label]
    have = [r for r in _rels(e) if r["type"] in types]
    ids = sorted({i for r in have for i in (r.get("at") or [])})
    ln = _occ_line(e)
    where = (f"{'/'.join(sorted({r['type'] for r in have}))} at occurrence(s) {ids} (line(s) "
             f"{sorted({ln[i] for i in ids if i in ln})})") if have else f"no {'/'.join(types)} record"
    mode, storage = _mode(e), e.get("storage")
    if label == "stores":
        ok, ev = storage == "edge", f"storage '{storage}'; {where}"
    elif label == "exit port":
        ok, ev = mode == "out", f"boundary mode '{mode}'; {where}"
    elif label == "sets":
        ok, ev = mode == "in" and bool(have), f"boundary mode '{mode}'; {where}"
    else:
        ok, ev = bool(have), where
    res = {"rule": rule, "confirmed": ok, "occurrence_ids": ids if ok else [], "evidence": ev}
    if extension and label == "stores" and not ok and "." in name and base is not None:
        bname, bl = base["name"], _occ_line(base)
        btext = {o["id"]: o["text"] for o in base.get("occurrences", [])}
        whole = sorted({i for r in _rels(base) if r["type"] == "CLOCKED_BY" for i in (r.get("at") or [])
                        if re.match(_WHOLE.format(re.escape(bname)), btext.get(i, ""), re.I)})
        if whole:
            res = {"rule": rule + " [extension: a field whose base record is assigned whole on a clock edge]",
                   "confirmed": True, "occurrence_ids": [], "via_extension": True,
                   "evidence": (f"field storage '{storage}'; base record '{bname}' assigned whole on a clock edge at its "
                                f"occurrence(s) {whole}: " + "; ".join(f"L{bl[i]} '{btext[i].strip()}'" for i in whole))}
    return res


def path_status(in_map: bool, quotes: list, conf: dict) -> str:
    if not in_map:
        return "none"
    quoted = {i for q in quotes for i in q["occurrence_ids"]}
    if conf["confirmed"]:
        if quoted & set(conf["occurrence_ids"]):
            return "full"
        return "confirmed, quoted elsewhere" if quotes else "confirmed, not quoted"
    return "quoted, not confirmed" if quotes else "none"


# ---------------------------------------------------------------------------------------------- trace ---

STEM = "assets_tuning18"      # the run-folder prefix of the tuning runs; another stem (e.g. assets_heldout26) traces
                              # under traces/<stem>/ so the tuning traces are never touched


def run_dir(version: str, rep: int, stem: str = STEM) -> Path:
    return ROOT / f"{stem}_{version}_r{rep}"


def out_root(version: str, map_dir: Path = rv.CODE_MAP_DIR, stem: str = STEM) -> Path:
    same = Path(map_dir).resolve() == Path(rv.CODE_MAP_DIR).resolve()
    return (TRACE_DIR if stem == STEM else TRACE_DIR / stem) / (version if same else f"{version}@{Path(map_dir).name}")


def trace_concepts(module: str, concepts: list, map_dir: Path = rv.CODE_MAP_DIR, rules: str = "default",
                   extension: bool = False, matcher: str = "default", rtl_dir: Path = RTL_DIR) -> list[dict]:
    """One trace record per structural asset listed under the concepts (the generator's 'conceptual assets')."""
    el, lt, out = load_map(module, Path(map_dir)), line_table(module, Path(rtl_dir)), []
    for c in concepts or []:
        why = c.get("reasoning", "") or ""
        R = nows(why)
        for a in c.get("related structural assets", []) or []:
            name, ent, label = a.get("asset rtl"), a.get("entity", "") or "", a.get("realization", "")
            if not name:
                continue
            e = el.get((ent, name))
            quotes = quotes_for(e, name, R, lt, matcher) if e else []
            base = el.get((ent, name.split(".")[0])) if "." in name else None
            conf = confirm(e, label, rules, name, base, extension)
            out.append({"module": module, "entity": ent, "element": name, "realization": label,
                        "concept": c.get("concept", ""), "objective": c.get("security objective", ""),
                        "why": why, "in_map": e is not None, "quotes": quotes,
                        "records": records_at(e, {i for q in quotes for i in q["occurrence_ids"]}) if e else [],
                        "confirmation": conf, "path": path_status(e is not None, quotes, conf)})
    return out


def trace_run(version: str, rep: int, map_dir: Path = rv.CODE_MAP_DIR, rules: str = "default",
              extension: bool = False, matcher: str = "default", write: bool = True, stem: str = STEM,
              rtl_dir: Path = RTL_DIR) -> list[dict]:
    """Trace every module of one run. Writes traces/<version>/r<rep>/<module>.json only for the default
    configuration (rules 'default', no extension, default matcher); other configurations stay in memory.
    stem / rtl_dir: the run-folder prefix and the RTL folder of the run (held-out: assets_heldout26, RTL_heldout/);
    a non-default stem writes under traces/<stem>/."""
    nd = run_dir(version, rep, stem) / "_nested"
    if not nd.is_dir():
        raise FileNotFoundError(nd)
    default = rules == "default" and not extension and matcher == "default"
    od = out_root(version, map_dir, stem) / f"r{rep}"
    if write and default:
        od.mkdir(parents=True, exist_ok=True)
    allrec, idx = [], {}
    for f in sorted(nd.glob("*.json")):
        m = f.stem
        recs = trace_concepts(m, json.loads(f.read_text(encoding="utf-8")).get("conceptual assets", []),
                              map_dir, rules, extension, matcher, rtl_dir)
        allrec += recs
        idx[m] = {"has_map": bool(load_map(m, Path(map_dir))), "records": len(recs),
                  "paths": dict(Counter(r["path"] for r in recs))}
        if write and default:
            (od / f"{m}.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")
    if write and default:
        (od / "_index.json").write_text(json.dumps({
            "version": version, "rep": rep, "source": str(nd.relative_to(ROOT)),
            "map_dir": str(Path(map_dir).resolve().relative_to(ROOT)),
            "rules": {lab: rule_text(lab) for lab in LABELS}, "matcher": {"full_min": FULL_MIN, "partial_extra": PARTIAL_EXTRA},
            "modules": idx}, indent=1), encoding="utf-8")
    return allrec


def load_traces(version: str, rep: int, map_dir: Path = rv.CODE_MAP_DIR, stem: str = STEM) -> list[dict] | None:
    d = out_root(version, map_dir, stem) / f"r{rep}"
    if not (d / "_index.json").exists():
        return None
    return [r for f in sorted(d.glob("*.json")) if not f.name.startswith("_")
            for r in json.loads(f.read_text(encoding="utf-8"))]


# ------------------------------------------------------------------------------------------- evaluate ---

def load_gt() -> dict:
    return ea.load_refs(gt_dir=GT_DIR, parsed_dir=PARSED_DIR)["gt"]


def classify(version: str, rep: int, gt: dict, modules) -> tuple[dict, dict]:
    """{(module, entity, name): 'TP' | 'FP'} for one run, with eval_assets.score's matching: reference entries in
    order, each takes the first unused prediction by eval_assets._hit_idx (strict). Checked against score()."""
    run = ea.load_run(run_dir(version, rep))
    sc = ea.score(run, gt, strict=True, only=set(modules))
    cls = {}
    for m in modules:
        preds, used = run.get(m, []), set()
        for rname, _o in gt[m]:
            pi = ea._hit_idx({i: preds[i][1] for i in range(len(preds)) if i not in used}, rname, True)
            if pi is not None:
                used.add(pi)
        for i, (ent, name, _o) in enumerate(preds):
            if (m, ent, name) in cls:
                raise AssertionError(f"{version} r{rep} {m}: ({ent}, {name}) listed twice in the flat file")
            cls[(m, ent, name)] = "TP" if i in used else "FP"
        fp = sorted(n for (mm, _e, n), c in cls.items() if mm == m and c == "FP")
        tp = sum(1 for (mm, _e, _n), c in cls.items() if mm == m and c == "TP")
        if fp != sc["per_module"][m]["fp"] or tp != sc["per_module"][m]["tp"]:
            raise AssertionError(f"{version} r{rep} {m}: TP/FP differ from eval_assets.score")
    return cls, run


def _modules(version: str, gt: dict, reps, map_dir) -> list[str]:
    """Modules with ground truth, a map, and an output in every run."""
    return sorted(m for m in gt if load_map(m, Path(map_dir))
                  and all((run_dir(version, k) / "_nested" / f"{m}.json").exists() for k in reps))


def _pct(a, n):
    return f"{a}/{n} ({a / n:.1%})" if n else f"{a}/0"


def evaluate(version: str, gt: dict | None = None, reps=REPS, map_dir: Path = rv.CODE_MAP_DIR,
             rules: str = "default", extension: bool = False, matcher: str = "default") -> dict:
    """TP/FP shares by path. Units:
      element  = one scored prediction, i.e. a distinct (module, entity, name) per run; its path is the best path of
                 its records (full > confirmed, quoted elsewhere > confirmed, not quoted > quoted, not confirmed > none),
                 and 'label confirmed' means any of its labels is confirmed. The denominators equal the scorer's TP and
                 FP counts, pooled over the runs.
      label    = a distinct (element, realization label) pair per run; path = best record with that label.
    Only modules with ground truth and a map count. The default configuration reads the written trace files."""
    gt = gt if gt is not None else load_gt()
    mods = _modules(version, gt, reps, map_dir)
    default = rules == "default" and not extension and matcher == "default"
    ann, per_run = [], {}
    for rep in reps:
        recs = (load_traces(version, rep, map_dir) if default else None) or \
            trace_run(version, rep, map_dir, rules, extension, matcher, write=False)
        cls, _run = classify(version, rep, gt, mods)
        seen = set()
        for i, r in enumerate(recs):
            if r["module"] not in mods:
                continue
            k = (r["module"], r["entity"], r["element"])
            if k not in cls:
                raise AssertionError(f"{version} r{rep}: {k} is in _nested but not in the flat file")
            ann.append({**r, "_rep": rep, "_order": i, "class": cls[k]})
            seen.add(k)
        missing = set(cls) - seen
        if missing:
            raise AssertionError(f"{version} r{rep}: flat predictions without a nested record: {sorted(missing)[:5]}")
    el, lab = {}, {}
    for r in ann:
        k = (r["_rep"], r["module"], r["entity"], r["element"])
        x = el.setdefault(k, {"class": r["class"], "path": "none", "confirmed": False})
        x["path"] = min(x["path"], r["path"], key=RANK.get)
        x["confirmed"] |= r["confirmation"]["confirmed"]
        y = lab.setdefault(k + (r["realization"],), {"class": r["class"], "path": "none", "confirmed": False,
                                                     "ext": r["confirmation"].get("via_extension", False)})
        y["path"] = min(y["path"], r["path"], key=RANK.get)
        y["confirmed"] |= r["confirmation"]["confirmed"]
    res = {"version": version, "reps": list(reps), "rules": rules, "extension": extension, "matcher": matcher,
           "map_dir": str(Path(map_dir).resolve().relative_to(ROOT)), "modules": mods,
           "gt_entries_per_run": sum(len(gt[m]) for m in mods)}
    res["elements"] = {c: {"n": sum(1 for x in el.values() if x["class"] == c),
                           "label_confirmed": sum(1 for x in el.values() if x["class"] == c and x["confirmed"]),
                           "paths": {p: sum(1 for x in el.values() if x["class"] == c and x["path"] == p) for p in PATHS}}
                       for c in ("TP", "FP")}
    res["records"] = {c: {"n": sum(1 for r in ann if r["class"] == c),
                          "paths": {p: sum(1 for r in ann if r["class"] == c and r["path"] == p) for p in PATHS}}
                      for c in ("TP", "FP")}
    labels = sorted({k[-1] for k in lab}, key=lambda s: (LABELS.index(s) if s in LABELS else 9, s))
    res["by_label"] = {L: {c: {"n": sum(1 for k, x in lab.items() if k[-1] == L and x["class"] == c),
                               "confirmed": sum(1 for k, x in lab.items() if k[-1] == L and x["class"] == c and x["confirmed"]),
                               "via_extension": sum(1 for k, x in lab.items() if k[-1] == L and x["class"] == c and x["ext"]),
                               "paths": {p: sum(1 for k, x in lab.items() if k[-1] == L and x["class"] == c and x["path"] == p)
                                         for p in PATHS}}
                           for c in ("TP", "FP")} for L in labels}
    for rep in reps:
        per_run[rep] = {c: {"n": sum(1 for k, x in el.items() if k[0] == rep and x["class"] == c),
                            "full": sum(1 for k, x in el.items() if k[0] == rep and x["class"] == c and x["path"] == "full"),
                            "label_confirmed": sum(1 for k, x in el.items() if k[0] == rep and x["class"] == c and x["confirmed"])}
                        for c in ("TP", "FP")}
    res["per_run"] = per_run
    res["filters"] = _filters(version, reps, gt, mods, el)
    res["_annotated"] = ann
    res["_elements"] = el
    res["_labels"] = lab
    return res


def _filters(version, reps, gt, mods, el) -> dict:
    """Re-scored with eval_assets.score after dropping elements: P and R as the mean of the runs (GT per run fixed)."""
    out = {}
    for name, keep in (("all elements (baseline)", lambda x: True),
                       ("keep elements with path full", lambda x: x["path"] == "full"),
                       ("keep elements with a confirmed label", lambda x: x["confirmed"])):
        ps, rs, emit = [], [], []
        for rep in reps:
            run = ea.load_run(run_dir(version, rep))
            f = {m: [p for p in run.get(m, []) if keep(el[(rep, m, p[0], p[1])])] for m in mods}
            s = ea.score(f, gt, strict=True, only=set(mods))
            ps.append(s["precision"]); rs.append(s["recall"]); emit.append(s["emit"])
        out[name] = {"precision_mean": round(st.mean(ps), 4), "recall_mean": round(st.mean(rs), 4),
                     "emitted_mean": round(st.mean(emit), 2), "per_run_precision": [round(p, 4) for p in ps],
                     "per_run_recall": [round(r, 4) for r in rs]}
    return out


def _public(ev: dict) -> dict:
    return {k: v for k, v in ev.items() if not k.startswith("_")}


def _ext_delta(base: dict, ext: dict) -> dict:
    """What the extension adds over the default: newly confirmed stores labels and elements, TP and FP."""
    out = {}
    for c in ("TP", "FP"):
        out[c] = {"stores_labels_newly_confirmed": sum(1 for k, y in ext["_labels"].items()
                                                      if y["class"] == c and y["ext"] and not base["_labels"][k]["confirmed"]),
                  "elements_newly_confirmed": sum(1 for k, x in ext["_elements"].items()
                                                  if x["class"] == c and x["confirmed"] and not base["_elements"][k]["confirmed"]),
                  "element_path_changes": dict(Counter(f"{base['_elements'][k]['path']} -> {x['path']}"
                                                       for k, x in ext["_elements"].items()
                                                       if x["class"] == c and x["path"] != base["_elements"][k]["path"]))}
    return out


def summary(version: str, gt: dict | None = None, reps=REPS, map_dir: Path = rv.CODE_MAP_DIR,
            write: bool = True) -> dict:
    """Print the default numbers, the prototype-compatible numbers and the extension's additions; write summary.json."""
    gt = gt if gt is not None else load_gt()
    ev = evaluate(version, gt, reps, map_dir)
    proto = evaluate(version, gt, reps, map_dir, rules="prototype", matcher="prototype")
    ext = evaluate(version, gt, reps, map_dir, extension=True)
    delta = _ext_delta(ev, ext)
    E = ev["elements"]
    print(f"\n=== {version}: runs r{', r'.join(map(str, reps))}; {len(ev['modules'])} modules with ground truth and a map; "
          f"{ev['gt_entries_per_run']} GT entries per run (exact)")
    print("Unit: element = one scored prediction, a distinct (module, entity, name) per run; pooled over the runs.")
    print(f"TP elements {E['TP']['n']}, FP elements {E['FP']['n']} (the scorer's own TP/FP counts, exact).")
    print(f"{'path (best record of the element)':34s} {'TP (share of TP elements)':>27s} {'FP (share of FP elements)':>27s}")
    for p in PATHS:
        print(f"  {p:32s} {_pct(E['TP']['paths'][p], E['TP']['n']):>27s} {_pct(E['FP']['paths'][p], E['FP']['n']):>27s}")
    print(f"  {'label confirmed (any label)':32s} {_pct(E['TP']['label_confirmed'], E['TP']['n']):>27s} "
          f"{_pct(E['FP']['label_confirmed'], E['FP']['n']):>27s}")
    print("By realization label (unit: distinct element-label pair per run):")
    for L, d in ev["by_label"].items():
        t, f = d["TP"], d["FP"]
        print(f"  {L:10s} TP n={t['n']:3d} confirmed {_pct(t['confirmed'], t['n']):>15s} full {_pct(t['paths']['full'], t['n']):>15s} | "
              f"FP n={f['n']:3d} confirmed {_pct(f['confirmed'], f['n']):>15s} full {_pct(f['paths']['full'], f['n']):>15s}")
        for p in PATHS[1:]:
            print(f"      {p:30s} TP {t['paths'][p]:3d}   FP {f['paths'][p]:3d}")
    print("Per run (elements): " + "; ".join(
        f"r{k}: TP {v['TP']['n']} (full {v['TP']['full']}, confirmed {v['TP']['label_confirmed']}), "
        f"FP {v['FP']['n']} (full {v['FP']['full']}, confirmed {v['FP']['label_confirmed']})" for k, v in ev["per_run"].items()))
    print("Filters, re-scored with eval_assets.score (precision and recall = mean of the runs; recall against the GT):")
    for k, v in ev["filters"].items():
        print(f"  {k:40s} P {v['precision_mean']:.3f}  R {v['recall_mean']:.3f}  emitted/run {v['emitted_mean']:.1f}")
    P = proto["elements"]
    print(f"Prototype-compatible (prototype rules and matcher): full TP {P['TP']['paths']['full']}/{P['TP']['n']}, "
          f"FP {P['FP']['paths']['full']}/{P['FP']['n']}; label confirmed TP {P['TP']['label_confirmed']}/{P['TP']['n']}, "
          f"FP {P['FP']['label_confirmed']}/{P['FP']['n']}")
    X = ext["elements"]
    print(f"Extension (field of a record assigned whole on a clock edge counts as stores), NOT in the default numbers:")
    for c in ("TP", "FP"):
        d = delta[c]
        print(f"  {c}: stores labels newly confirmed {d['stores_labels_newly_confirmed']}; elements newly confirmed "
              f"{d['elements_newly_confirmed']} (label confirmed {E[c]['label_confirmed']} -> {X[c]['label_confirmed']} of {E[c]['n']}); "
              f"path changes {d['element_path_changes'] or 'none'}")
    out = {"default": _public(ev), "prototype_compatible": _public(proto), "extension": _public(ext),
           "extension_adds": delta}
    if write:
        od = out_root(version, map_dir)
        od.mkdir(parents=True, exist_ok=True)
        (od / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------------------------- report ---

def _short(xs, n=6):
    xs = list(xs)
    return ", ".join(xs[:n]) + (f" (+{len(xs) - n} more)" if len(xs) > n else "")


def write_report(version: str, reps=REPS, map_dir: Path = rv.CODE_MAP_DIR) -> Path:
    """traces/<version>/trace_report.md from the written trace files. No TP/FP in it."""
    od = out_root(version, map_dir)
    L = [f"# Asset trace: {version}", "",
         "What this is: for every structural asset the generator reported, the path from the RTL line its reasoning "
         "quotes, to the occurrence ID of the element on that line, to the relationship records at that occurrence, "
         "to whether the map confirms the realization label. Built by code after generation "
         "(`assetgen_meta/asset_trace.py`), no model call. No ground truth is used here.", "",
         f"Map: `{Path(map_dir).resolve().relative_to(ROOT).as_posix()}`. Line numbers are ORIGINAL file lines; "
         "'stripped' is the line in the comment-stripped text the generator saw.", "",
         "Path status: **full** = a quoted occurrence is one that confirms the label; **confirmed, quoted elsewhere**; "
         "**confirmed, not quoted**; **quoted, not confirmed**; **none**.", "", "Confirmation rules:", ""]
    L += [f"- {rule_text(lab)}" for lab in LABELS]
    for rep in reps:
        recs = load_traces(version, rep, map_dir)
        if recs is None:
            continue
        L += ["", f"## Run r{rep}", "", "Records per path: " + ", ".join(
            f"{p} {sum(1 for r in recs if r['path'] == p)}" for p in PATHS) + f" (of {len(recs)} records)."]
        by_mod = defaultdict(list)
        for r in recs:
            by_mod[r["module"]].append(r)
        for m in sorted(by_mod):
            L += ["", f"### {m} (r{rep})", ""]
            for r in by_mod[m]:
                c = r["confirmation"]
                L.append(f"- **{r['element']}** (entity `{r['entity']}`), label `{r['realization']}`, path **{r['path']}**"
                         f"{'' if r['in_map'] else ', NOT IN MAP'} - concept: {r['concept']} ({r['objective']})")
                L.append(f"  - confirmation: {'confirmed' if c['confirmed'] else 'not confirmed'}; {c['evidence']}"
                         + (f"; confirming occurrence(s) {c['occurrence_ids']}" if c["occurrence_ids"] else ""))
                conf = set(c["occurrence_ids"])
                qs = sorted(r["quotes"], key=lambda q: (not (set(q["occurrence_ids"]) & conf), q["match"] != "full",
                                                        q["original_line"]))
                for q in qs[:3]:
                    tag = " (confirming)" if set(q["occurrence_ids"]) & conf else ""
                    L.append(f"  - quoted L{q['original_line']} (stripped L{q['stripped_line']}), occurrence "
                             f"{', '.join(map(str, q['occurrence_ids']))}, {q['match']}{tag}: `{q['text']}`")
                    for x in [x for x in r["records"] if x["occurrence_id"] in q["occurrence_ids"]][:6]:
                        L.append(f"    - occ {x['occurrence_id']}: {x['type']} -> {_short(x['targets'])}"
                                 + (f"; guard `{x['guard']}`" if x.get("guard") else ""))
                if len(qs) > 3:
                    L.append(f"  - (+{len(qs) - 3} more quoted lines)")
                if not qs:
                    L.append("  - no occurrence line of this element is quoted")
                L.append(f"  - why: {' '.join(r['why'].split())[:300]}")
    p = od / "trace_report.md"
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


# ----------------------------------------------------------------------------------------------- audit ---

def audit_sample(version: str = "m7e194es0ism", gt: dict | None = None, seed: int = 20260930, n_tp: int = 20,
                 n_fp: int = 10, reps=REPS, map_dir: Path = rv.CODE_MAP_DIR) -> tuple[Path, Path]:
    """Blind audit sample: n_tp distinct (module, entity, element) true positives and n_fp distinct false positives,
    all with path 'full', drawn with random.Random(seed) from the runs; shuffled; ids T01.. assigned after the
    shuffle. audit_sample.json has no TP/FP information; audit_key.json maps id -> 'TP' | 'FP'."""
    ev = evaluate(version, gt, reps, map_dir)
    cand = {"TP": defaultdict(list), "FP": defaultdict(list)}
    for r in ev["_annotated"]:
        if r["path"] == "full":
            cand[r["class"]][(r["module"], r["entity"], r["element"])].append(r)
    rng = random.Random(seed)
    pick_tp = rng.sample(sorted(cand["TP"]), n_tp)
    pick_fp = rng.sample(sorted(k for k in cand["FP"] if k not in set(pick_tp)), n_fp)
    items = []
    for cls, keys in (("TP", pick_tp), ("FP", pick_fp)):
        for k in keys:
            r = rng.choice(sorted(cand[cls][k], key=lambda x: (x["_rep"], x["_order"])))
            conf = set(r["confirmation"]["occurrence_ids"])
            q = next(q for q in r["quotes"] if set(q["occurrence_ids"]) & conf)
            oid = min(set(q["occurrence_ids"]) & conf)
            items.append((cls, {"module": r["module"], "entity": r["entity"], "element": r["element"],
                                "run": f"r{r['_rep']}", "realization": r["realization"], "concept": r["concept"],
                                "quote": {"original_line": q["original_line"], "text": q["text"], "occurrence_id": oid},
                                "records": [{k2: x[k2] for k2 in ("type", "targets", "guard")}
                                            for x in r["records"] if x["occurrence_id"] == oid],
                                "confirmation": {k2: v for k2, v in r["confirmation"].items() if k2 != "via_extension"}}))
    rng.shuffle(items)
    sample, key = [], {}
    for i, (cls, it) in enumerate(items, 1):
        sample.append({"id": f"T{i:02d}", **it})
        key[f"T{i:02d}"] = cls
    od = out_root(version, map_dir)
    ps, pk = od / "audit_sample.json", od / "audit_key.json"
    ps.write_text(json.dumps(sample, indent=1, ensure_ascii=False), encoding="utf-8")
    pk.write_text(json.dumps(key, indent=1), encoding="utf-8")
    return ps, pk


# -------------------------------------------------------------------------------------------- selftest ---

# Hand-read on 2026-09-30 by opening RTL_data/<module>.vhd and the code map JSON: (module, entity, element,
# original line, stripped line counted by hand, the element's occurrence IDs on that line, start of the line's code).
HAND = [
    ("neorv32_wdt", "neorv32_wdt", "cnt", 57, 36, [1], "signal cnt            : std_ulogic_vector(23 downto 0);"),
    ("neorv32_wdt", "neorv32_wdt", "ctrl.enable", 94, 66, [3], "ctrl.enable  <= bus_req_i.data(ctrl_enable_c);"),
    ("neorv32_wdt", "neorv32_wdt", "cnt", 134, 102, [4, 5], "cnt <= std_ulogic_vector(unsigned(cnt) + 1);"),
    ("neorv32_wdt", "neorv32_wdt", "clkgen_en_o", 140, 106, [2], "clkgen_en_o <= ctrl.enable;"),
    ("neorv32_wdt", "neorv32_wdt", "ctrl.enable", 156, 116, [10], "hw_rst_access  <= ctrl.enable and ctrl.strict and reset_force;"),
    ("neorv32_hwspinlock", "neorv32_hwspinlock", "lock_q", 45, 25, [3], "lock_q(i) <= not bus_req_i.rw;"),
    ("neorv32_hwspinlock", "neorv32_hwspinlock", "sel", 51, 29, [3], "sel(i) <= '1' when (bus_req_i.addr(6 downto 2)"),
    ("neorv32_hwspinlock", "neorv32_hwspinlock", "bus_rsp_o.data", 68, 41, [3], "bus_rsp_o.data <= lock_q and sel;"),
    ("neorv32_sys", "neorv32_sys_reset", "sreg_sys", 57, 33, [4, 5, 6], "sreg_sys <= sreg_sys(sreg_sys'left-1 downto 0) & '1';"),
    ("neorv32_sys", "neorv32_sys_reset", "xrstn_wdt_o", 72, 44, [3], "xrstn_wdt_o <= rstn_wdt_i;"),
    ("neorv32_sys", "neorv32_sys_clock", "cnt", 131, 78, [3, 4], "cnt <= std_ulogic_vector(unsigned(cnt) + 1);"),
    ("neorv32_cache", "neorv32_cache", "ctrl", 126, 88, [10], "ctrl <= ctrl_nxt;"),
]


def selftest() -> None:
    """Hand-read lines, then synthetic reasonings through the full trace. Raises AssertionError on any failure."""
    # 1. line table and occurrence IDs on hand-read lines
    for m, ent, name, L, S, ids, text in HAND:
        lt, e = line_table(m), load_map(m).get((ent, name))
        assert e is not None, (m, ent, name)
        assert lt.to_stripped[L] == S and lt.to_original[S] == L, (m, L, S, lt.to_stripped[L])
        assert lt.code[L].strip().startswith(text), (m, L, lt.code[L])
        assert lt.stripped_text.splitlines()[S - 1] == lt.code[L], (m, S)
        assert sorted(o["id"] for o in e["occurrences"] if o["line"] == L) == ids, (m, name, L)
    assert all(line_table("neorv32_wdt").to_stripped[i] is None for i in range(1, 11))       # header comment + blank
    assert (("neorv32_sys", "neorv32_sys_reset", "cnt") not in {("neorv32_sys",) + k for k in load_map("neorv32_sys")}
            and ("neorv32_sys_clock", "clk_i") in load_map("neorv32_sys") and ("neorv32_sys_reset", "clk_i") in load_map("neorv32_sys"))
    # every map occurrence of every module: its line survives stripping and holds the occurrence text
    n = 0
    for p in sorted(Path(rv.CODE_MAP_DIR).glob("*.json")):
        lt = line_table(p.stem)
        for e in load_map(p.stem).values():
            for o in e["occurrences"]:
                assert lt.to_stripped.get(o["line"]) and nows(o["text"]) == nows(lt.code[o["line"]]), (p.stem, e["name"], o)
                n += 1

    def one(m, ent, name, label, reasoning, **kw):
        recs = trace_concepts(m, [{"concept": "c", "security objective": "Integrity", "reasoning": reasoning,
                                   "related structural assets": [{"asset rtl": name, "entity": ent, "realization": label}]}], **kw)
        assert len(recs) == 1
        return recs[0]

    W, H, S, C = "neorv32_wdt", "neorv32_hwspinlock", "neorv32_sys", "neorv32_cache"
    # 2. a real statement, re-spaced and wrapped in backticks: full quote -> occurrence 3 -> CLOCKED_BY -> full path
    r = one(W, W, "ctrl.enable", "stores", "bus_access writes `ctrl.enable  <=  bus_req_i.data( ctrl_enable_c );` on writes")
    assert [(q["original_line"], q["stripped_line"], q["occurrence_ids"], q["match"]) for q in r["quotes"]] == [(94, 66, [3], "full")], r["quotes"]
    assert r["confirmation"]["confirmed"] and r["confirmation"]["occurrence_ids"] == [3] and r["path"] == "full"
    assert any(x["type"] == "CLOCKED_BY" and x["targets"] == ["clk_i"] and x["occurrence_id"] == 3 for x in r["records"])
    # 3. invented statements must NOT match
    r = one(W, W, "ctrl.enable", "stores", "the module assigns ctrl.enable <= ctrl.timeout(3) xor reset_wdt; to arm itself")
    assert r["quotes"] == [] and r["path"] == "confirmed, not quoted", r["quotes"]
    inv = "the unit does cnt <= cnt_timeout and prsc_tick; on overflow"          # 'cnt' only inside 'cnt_timeout'
    r = one(W, W, "cnt", "stores", inv)
    assert r["quotes"] == [] and r["path"] == "confirmed, not quoted", r["quotes"]
    assert one(W, W, "cnt", "stores", inv, matcher="prototype")["quotes"], "prototype matcher should (wrongly) match"
    assert one(W, W, "clkgen_en_o", "exit port", "clkgen_en_o is driven by the enable bit")["quotes"] == []
    # an invented statement sharing a long prefix with a real one is at most PARTIAL, never full
    r = one(W, W, "ctrl.enable", "stores", "it assigns ctrl.enable <= bus_req_i.data(ctrl_lock_c) there")
    assert [q["match"] for q in r["quotes"]] == ["partial"] and r["quotes"][0]["original_line"] == 94
    # 4. exit port: COPIES at occurrence 2 (L140)
    r = one(W, W, "clkgen_en_o", "exit port", "and 'clkgen_en_o <= ctrl.enable' exports it")
    assert r["path"] == "full" and r["confirmation"]["occurrence_ids"] == [2] and r["records"][0]["type"] == "COPIES"
    # 5. declaration only: confirmed, quoted elsewhere
    r = one(W, W, "cnt", "stores", "declared as 'signal cnt : std_ulogic_vector(23 downto 0)'")
    assert [q["occurrence_ids"] for q in r["quotes"]] == [[1]] and r["path"] == "confirmed, quoted elsewhere"
    # 6. identical text on two lines of one module: both lines are quoted (L127 reset branch, L132 clocked branch)
    r = one(W, W, "cnt", "stores", "clears it with cnt <= (others => '0');")
    assert [q["original_line"] for q in r["quotes"]] == [127, 132] and r["path"] == "full"
    # 7. sets on an internal element is never confirmed; computes via GATED_BY; partial quote
    r = one(H, H, "lock_q", "sets", "claims with lock_q(i) <= not bus_req_i.rw on a read")
    assert r["path"] == "quoted, not confirmed" and r["quotes"][0]["occurrence_ids"] == [3]
    r = one(H, H, "sel", "computes", "decodes sel(i) <= '1' when the address matches")
    assert [(q["original_line"], q["match"]) for q in r["quotes"]] == [(51, "partial")] and r["path"] == "full"
    # 8. sets on an input port: SOURCES (default and prototype); clk_i with only SEQUENCES: prototype rule only
    r = one(W, W, "clkgen_i", "sets", "prsc_tick <= clkgen_i(clk_div4096_c) samples it")
    assert r["path"] == "full" and r["confirmation"]["occurrence_ids"] == [2]
    assert not one(W, W, "clk_i", "sets", "x")["confirmation"]["confirmed"]
    assert one(W, W, "clk_i", "sets", "x", rules="prototype")["confirmation"]["confirmed"]
    # 9. entity keying: sys_reset has no 'cnt'; sys_clock's cnt L131 is found under its own entity
    assert not one(S, "neorv32_sys_reset", "cnt", "stores", "cnt <= std_ulogic_vector(unsigned(cnt) + 1);")["in_map"]
    r = one(S, "neorv32_sys_clock", "cnt", "stores", "cnt <= std_ulogic_vector(unsigned(cnt) + 1);")
    assert r["path"] == "full" and r["quotes"][0]["occurrence_ids"] == [3, 4] and r["quotes"][0]["stripped_line"] == 78
    # 10. extension: cache ctrl.state (storage 'none'); base ctrl assigned whole at occurrence 10 (L126)
    r = one(C, C, "ctrl.state", "stores", "the FSM state")
    assert not r["confirmation"]["confirmed"] and r["path"] == "none"
    r = one(C, C, "ctrl.state", "stores", "the FSM state", extension=True)
    assert r["confirmation"]["confirmed"] and r["confirmation"]["via_extension"] and "L126" in r["confirmation"]["evidence"]
    assert r["path"] == "confirmed, not quoted"
    assert not one(W, W, "ctrl.enable", "computes", "x", extension=True)["confirmation"].get("via_extension")
    # 11. no ground-truth field in a trace record
    assert set(r) == {"module", "entity", "element", "realization", "concept", "objective", "why", "in_map", "quotes",
                      "records", "confirmation", "path"}
    # 12. the corrected grow() never reports a fragment that is not in the reasoning; the prototype's could
    assert _grow("xabcdefy", "..abcdef..xab..", 1, 3) == (1, 7) and _grow_v0("xabcdefy", "..abcdef..xab..", 1, 3) == 7
    print(f"SELF-TEST PASS: {len(HAND)} hand-read lines in {len({h[0] for h in HAND})} modules; {n} map occurrences "
          f"found on their stripped lines; synthetic reasonings: full, partial, declaration-only, duplicate-text lines, "
          f"entity keying, all four labels, both rule sets, the extension, 3 invented statements left unmatched")


# ------------------------------------------------------------------------------------------------- CLI ---

def main(argv: list[str]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    audit = "--audit" in argv
    versions = [a for a in argv if not a.startswith("--")]
    if not versions:
        print(__doc__)
        return
    try:
        selftest()
    except AssertionError as e:
        print(f"SELF-TEST FAIL: {e!r}. Nothing is reported.")
        sys.exit(1)
    gt = load_gt()
    for v in versions:
        for rep in REPS:
            recs = trace_run(v, rep)
            print(f"{v} r{rep}: {len(recs)} trace records written to {(out_root(v) / f'r{rep}').relative_to(ROOT)}")
        summary(v, gt)
        print(f"report: {write_report(v).relative_to(ROOT)}")
        if audit and v == "m7e194es0ism":
            ps, pk = audit_sample(v, gt)
            print(f"audit sample: {ps.relative_to(ROOT)}; key: {pk.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
