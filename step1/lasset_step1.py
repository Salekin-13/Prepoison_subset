"""LAsset replication, Step 1, on the 15 test modules (the RTL_data modules that have manual GT).

  1. closed set     code     rtl_parse.parse_rtl_file, the mechanical extractor the parser has always used
  2. occurrence     v3b      the fine-tuned occurrence profiler, run unchanged: its own notebook cells are executed with
     profiles                only the module list, the closed-set folder and the output folder swapped
  3. relationships  LLM      relation_stage (prompt relation_prompts_v1/relation_system_prompt.md) on those profiles

Every JSON file goes under step1/lasset_step1/:
  closed_set/<module>.json                                  the closed set, in the element-list format the profiler reads
  occurrence_profiles/extract/<code sha>/<module>__<entity>__bNN.json      inventory + Context + Path (code)
  occurrence_profiles/classify/<prompt sha>/<module>__<entity>__bNN.json   SITE + Role (gpt-5-mini)
  occurrence_profiles/validate/<prompt sha>/<module>__<entity>__bNN.json   the checked profiles (gpt-5-mini)
  relation_out/<prompt sha>/<module>__<entity>__bNN.json    the relation annotator's raw answers
  relation_map/<prompt sha>/<module>.json                   the final traceable map {"ports": [...], "signals": [...]}
"""
from __future__ import annotations

import contextlib, io, json, os, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BPA = ROOT / "bahavioral_patterns_of_assets"
PACK = BPA / "annotation_pack_elements"
BUILDER = PACK / "occurrence_prompts_v2/rulebook_edits"
GT_FILE = ROOT / "data/ground_truth/manual_gt_neorv32.json"

OUT_ROOT = HERE / "lasset_step1"
CLOSED = OUT_ROOT / "closed_set"
PROFILES = OUT_ROOT / "occurrence_profiles"
REL_OUT = OUT_ROOT / "relation_out"
REL_MAP = OUT_ROOT / "relation_map"

PROMPT_VERSION = "occurrence_prompts_v3d"   # v3 prompts + the v3d rulebook (v3c's two fixes + the parentheses rules)
APPROVED_RULEBOOK = "c748e39bfc05"          # v3d round 3, 2026-09-29 (see occurrence_prompts_v3d/RULEBOOK_CHANGELOG.md)
PROMPT_SHAS = {"classify": "97ef25455d47", "validate": "021e62bcd902"}   # v3d; the profiler asserts they still hold
# v3d also adds two facts to validate's CODE CHECK (position_facts below); they change validate's input, not its prompt
WHERE = {"elem_dir": CLOSED, "profile": (PROFILES, PROMPT_SHAS["validate"]), "out": REL_OUT, "map": REL_MAP}


@contextlib.contextmanager
def _at(path):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def test_modules() -> list[str]:
    """The RTL_data modules that have manual GT: the development / test set used while tuning."""
    gt = json.loads(GT_FILE.read_text(encoding="utf-8"))["modules"]
    mods = sorted(p.stem for p in (BPA / "data/RTL_data").glob("*.vhd") if p.stem in gt)
    assert len(mods) == 15, f"expected 15 test modules, found {len(mods)}: {mods}"
    return mods


# ---------------------------------------------------------------------------------------------- 1. closed set
def _parse(module: str, registry: dict) -> dict:
    sys.path.insert(0, str(BPA))
    import rtl_parse
    path = BPA / "data/RTL_data" / f"{module}.vhd"
    d = rtl_parse.parse_rtl_file(path, registry)
    return {"module": module, "source": f"data/RTL_data/{module}.vhd", "entities": d["entities"]}


def _registry() -> dict:
    """Record types across the package and every RTL file, so a port typed bus_req_t expands to its fields."""
    sys.path.insert(0, str(BPA))
    import rtl_parse
    return rtl_parse.build_record_registry(sorted((BPA / "data/RTL_data").glob("*.vhd")))


def closed_set_selftest(log=print) -> bool:
    """Two checks before any closed set is written. (a) The three pack modules re-extracted here must equal the element
    lists the profiler was tuned on (annotation_pack_elements/<module>.json). (b) boot_rom against the hand-read source
    (neorv32_boot_rom.vhd lines 21-24 and 38-39)."""
    reg = _registry()
    ok = True
    for m in ("neorv32_boot_rom", "neorv32_trng", "neorv32_cache"):
        want = json.loads((PACK / f"{m}.json").read_text(encoding="utf-8"))["entities"]
        got = _parse(m, reg)["entities"]
        same = got == want
        ok &= same
        log(f"   {m}: re-extracted closed set {'equals' if same else 'DIFFERS FROM'} the tuned element list "
            f"({sum(len(e['ports']) + len(e['signals']) for e in got)} elements, {len(got)} entities)")
    e = _parse("neorv32_boot_rom", reg)["entities"][0]
    hand_ports = [("clk_i", "in", "std_ulogic"), ("rstn_i", "in", "std_ulogic"), ("bus_req_i", "in", "bus_req_t"),
                  ("bus_rsp_o", "out", "bus_rsp_t")]
    hand_sigs = [("rden", "std_ulogic"), ("rdata", "std_ulogic_vector")]
    base_ports = [(p["name"], p["dir"], p["type"]) for p in e["ports"] if "." not in p["name"]]
    base_sigs = [(s["name"], s["type"].split("(")[0].strip()) for s in e["signals"] if "." not in s["name"]]
    fields = [p["name"] for p in e["ports"] if "." in p["name"]]
    hand_ok = (base_ports == hand_ports and base_sigs == hand_sigs and "bus_req_i.addr" in fields
               and "bus_rsp_o.ack" in fields)
    ok &= hand_ok
    log(f"   neorv32_boot_rom against the hand-read lines 21-24, 38-39: {'PASS' if hand_ok else 'FAIL'} "
        f"(ports {base_ports}, signals {base_sigs}, {len(fields)} record fields)")
    log(f"   closed-set self-test: {'PASS' if ok else 'FAIL'}")
    return ok


def build_closed_set(modules: list[str], log=print) -> dict:
    """Write closed_set/<module>.json for every module; return {module: (entities, ports, signals)}."""
    reg = _registry()
    CLOSED.mkdir(parents=True, exist_ok=True)
    summary = {}
    for m in modules:
        d = _parse(m, reg)
        (CLOSED / f"{m}.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
        np = sum(len(e["ports"]) for e in d["entities"])
        ns = sum(len(e["signals"]) for e in d["entities"])
        summary[m] = (len(d["entities"]), np, ns)
    return summary


# ---------------------------------------------------------------------------------------------- 2. occurrence profiles
def position_facts(job, profiles, g) -> list[str]:
    """Two facts a program can read off the source, for validate's CODE CHECK (added with v3d, 2026-09-29). They target
    the spots that flip between identical runs: the two occurrences of x <= f(x) + 1 swapping target and operand SITEs,
    and DIRR_ASS on a right-hand side that is not exactly the element (or missing where it is).
      target: the occurrence written first in an assignment, left of <=, is its target and takes LHS_PROC or LHS_CONC;
              an occurrence right of <= never does.
      whole:  an occurrence that is the whole right-hand side of a signal assignment is DIRR_ASS; DIRR_ASS on any
              other occurrence is wrong.
    Only contradictions of the given profiles are reported; a line with several statements is left alone."""
    import tag_regress as T
    L = g["source_lines"](job["src"])
    items = []
    for e in job["elems"]:
        n = e["name"]
        matches = g["occurrence_matches"](L, n)
        for r in profiles.get(n, []) or []:
            if not isinstance(r, dict) or not isinstance(r.get("Occurrence ID"), int):
                continue
            i = r["Occurrence ID"] - 1
            if not (0 <= i < len(matches)) or matches[i][0] != r.get("Occurrence Lines") or matches[i][1] < 0:
                continue
            ln, col, _w = matches[i]
            t, tags = L[ln], set(r.get("SITE Tagged") or [])
            a = T._assign_col(t)
            if a is None or len(re.findall(r"<=|:=", t[T._stmt_start(t):])) > 1 or t[a:a + 2] != "<=":
                continue
            oid = r["Occurrence ID"]
            target = col == T._stmt_start(t) and col < a and re.match(rf"{re.escape(n)}\s*(?:\(|<=)", t[col:])
            if target and not tags & T.LHS:
                items.append(f"- {n}: at line {ln}, Occurrence ID {oid} is written first, left of <=: it is the target "
                             f"of the assignment and takes LHS_PROC or LHS_CONC (with INDEXED_NAME or PART_SELECT where "
                             f"written). It is tagged {', '.join(sorted(tags)) or 'nothing'}.")
            if col > a and tags & T.LHS:
                items.append(f"- {n}: at line {ln}, Occurrence ID {oid} is right of <=, on the right-hand side: it is "
                             f"not the target, so it takes no LHS_PROC or LHS_CONC.")
            rhs = t[a + 2:].split(";")[0].strip()
            if col > a and " when " not in f" {rhs} ":
                whole = rhs.lower() == n.lower()
                if whole and "DIRR_ASS" not in tags:
                    items.append(f"- {n}: at line {ln}, Occurrence ID {oid} is the whole right-hand side of the signal "
                                 f"assignment, with nothing else there: DIRR_ASS. It is tagged "
                                 f"{', '.join(sorted(tags)) or 'nothing'}.")
                if not whole and "DIRR_ASS" in tags:
                    items.append(f"- {n}: at line {ln}, Occurrence ID {oid} is tagged DIRR_ASS, but the right-hand side "
                                 f"is not exactly the element: not DIRR_ASS.")
    return items


def _with_position_facts(original, g):
    def code_checklist(job, profiles):
        text = original(job, profiles)
        extra = position_facts(job, profiles, g)
        if not extra:
            return text
        body = "\n".join(extra)
        return text.replace("\n- no item\n", f"\n{body}\n") if "\n- no item\n" in text else text.rstrip("\n") + f"\n{body}\n"
    return code_checklist


class Profiler:
    """The v3b occurrence profiler, run from its own notebook cells. Only three things differ from
    notebooks/occurrence_profiles_v3b.ipynb: MODULES (one set per test module), load_elements (reads closed_set/), and
    OUT_DIR (occurrence_profiles/ here). Prompts, rulebook, model, effort, batching and checks are v3b's."""

    def __init__(self, modules: list[str], log=print, prompt_version: str | None = None, out_dir=None):
        sys.path.insert(0, str(BUILDER))
        import build_occurrence_notebook_v3b as B
        self.B, self.modules, self.log = B, list(modules), log
        g = self.g = {"__name__": "lasset_step1_profiler"}
        buf = io.StringIO()
        with _at(B.ROOT), contextlib.redirect_stdout(buf):
            exec(B.C_SETUP, g)
            g["MODULES"] = {m: [m] for m in self.modules}
            g["OUT_DIR"] = Path(out_dir) if out_dir else PROFILES
            g["PROMPT_DIR"] = g["ELEM_DIR"] / (prompt_version or PROMPT_VERSION)   # v3 and v3b keep theirs
            g["RULEBOOK_FILE"] = g["PROMPT_DIR"] / "rulebook.json"
            for c in (B.C_ENV, B.C_CLIENT, B.C_PROMPTS, B.C_INPUTS):
                exec(c, g)
            g["load_elements"] = lambda module: [
                (e["entity"], e["ports"] + e["signals"])
                for e in json.loads((CLOSED / f"{module}.json").read_text(encoding="utf-8"))["entities"]]
            g["MODULES"] = {}                       # the checks cell prints a batch plan for MODULES; done by plan()
            exec(B.C_CHECKS, g)
            g["code_checklist"] = _with_position_facts(g["code_checklist"], g)
            g["MODULES"] = {m: [m] for m in self.modules}
            exec(B.C_RULEBOOK, g)
            exec(B.C_RUN.rstrip().rsplit("\nrun()", 1)[0], g)      # the run cell's functions, without running it
            self.rulebook_usable, self.rulebook_sha = g["load_rulebook"]()   # fills the classify / validate prompts
        self.setup_log = buf.getvalue()
        bad = [l for l in self.setup_log.splitlines() if re.search(r"MISSING|FAIL|PROBLEM|Traceback", l)]
        got = {k: g["PROMPT_SHA"][k] for k in PROMPT_SHAS}
        log(f"   profiler loaded -- prompts and rulebook from {g['PROMPT_DIR'].name}, program code from the v3b builder's "
            f"cells: self-tests {'PASS' if g['SELFTEST_OK'] else 'FAIL'}; rulebook "
            f"{self.rulebook_sha} ({'approved' if self.rulebook_sha == APPROVED_RULEBOOK else 'NOT the approved one'}); "
            f"prompts {got} ({'as pinned' if got == PROMPT_SHAS else 'NOT the pinned shas'}); {len(bad)} warning line(s) {bad[:3]}")

    def _jobs(self, modules):
        with _at(self.B.ROOT):
            return self.g["build_jobs"](modules)

    def plan(self, modules=None, log=None) -> dict:
        """Batches, calls and what is already on disk, per module. No API call."""
        log = log or self.log
        out, g = {}, self.g
        with _at(self.B.ROOT):
            for m in modules or self.modules:
                js = g["build_jobs"]([m])
                n_occ = sum(len(g["occurrence_matches"](g["source_lines"](j["src"]), e["name"]))
                            for j in js for e in j["elems"])
                done = {}
                for step in g["STEPS"]:
                    done[step] = sum(bool(a and not a["stale"] and a["parsed"] is not None)
                                     for a in (g["read_answer"](step, j) for j in js))
                out[m] = {"batches": len(js), "elements": sum(len(j["elems"]) for j in js), "occurrences": n_occ,
                          "calls": 2 * len(js), "done": done}
                log(f"   {m:24s} {len(js):>2} batches, {out[m]['elements']:>4} elements, {n_occ:>5} occurrences, "
                    f"{2 * len(js):>2} calls | on disk: extract {done['extract']}, classify {done['classify']}, "
                    f"validate {done['validate']} of {len(js)}")
        tot = sum(v["calls"] for v in out.values())
        left = sum(2 * v["batches"] - v["done"]["classify"] - v["done"]["validate"] for v in out.values())
        log(f"   total: {tot} model calls for {len(out)} modules; {left} still to make")
        return out

    def reuse(self, source_dir: Path, modules=None) -> int:
        """Copy answers of the same v3b version from another output folder (the pipeline re-checks each copy's
        input sha, so a copy made from a different closed set or source is treated as stale and called again)."""
        n = 0
        for step_dir in Path(source_dir).iterdir():
            if step_dir.name not in self.g["STEPS"]:
                continue
            sha = self.g["PROMPT_SHA"].get(step_dir.name)
            if not sha or not (step_dir / sha).is_dir():
                continue                              # a different prompt version: nothing of it is reused
            for f in (step_dir / sha).glob("*.json"):
                if any(f.name.startswith(f"{m}__") for m in (modules or self.modules)):
                    dst = PROFILES / f.relative_to(source_dir)   # same step / sha / name
                    if not dst.exists():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, dst)
                        n += 1
        return n

    def run(self, modules, log=None, only=None, approved=None) -> dict:
        """extract (code, with structure) -> classify -> validate for the modules; returns the client's cost.
        only: a set of (module, entity, batch) to restrict the run to (a test run). approved: (rulebook sha, prompt
        shas) for a prompt version under test; by default the pinned APPROVED_RULEBOOK and PROMPT_SHAS."""
        log = log or self.log
        g = self.g
        want_rb, want_shas = approved or (APPROVED_RULEBOOK, PROMPT_SHAS)
        if not g["SELFTEST_OK"]:
            log("   stopped: a self-test of the profiler's checks failed")
            return {}
        with _at(self.B.ROOT):
            usable, sha = g["load_rulebook"]()
            if not usable or sha != want_rb:
                log(f"   stopped: rulebook {sha} is not the approved {want_rb}")
                return {}
            got = {k: g["PROMPT_SHA"][k] for k in want_shas}
            if got != want_shas:
                log(f"   stopped: prompt shas {got} differ from the pinned {want_shas}")
                return {}
            jobs = g["build_jobs"](list(modules))
            if only is not None:
                jobs = [j for j in jobs if (j["module"], j["entity"], j["batch"]) in only]
            for step in g["STEPS"]:
                g["call_step"](step, jobs)
            return g["client"].cost()

    def report(self, modules):
        """The profiler's own check report (its parse cell), for these modules."""
        g = self.g
        g["MODULES"] = {m: [m] for m in modules}
        with _at(self.B.ROOT):
            exec(self.B.C_PARSE, g)
        g["MODULES"] = {m: [m] for m in self.modules}


# ---------------------------------------------------------------------------------------------- 3. relationships
def profile_complete(module) -> tuple[bool, int, int]:
    """(ready, occurrences, occurrences without a validated SITE/Role) from the Step 1 profiles."""
    import relation_stage as RS
    ents = RS.load_module(module, WHERE)
    n = sum(len(rs) for e in ents for rs in e["profile"].values())
    miss = sum(e["missing_site"] for e in ents)
    return n > 0 and miss == 0, n, miss
