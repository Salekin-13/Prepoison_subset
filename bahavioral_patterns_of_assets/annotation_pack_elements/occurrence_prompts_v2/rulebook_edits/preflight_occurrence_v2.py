# -*- coding: utf-8 -*-
"""Run the v2 notebook's own cells with a stubbed model. No API call, nothing written to the repo."""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

S = Path(__file__).parent
sys.path.insert(0, str(S))
import build_occurrence_notebook_v2 as B  # noqa: E402

os.chdir(B.ROOT)
g = {"__name__": "nb"}
fails = []


def ok(cond, label, detail=""):
    print(f"   {'PASS' if cond else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not cond:
        fails.append(label)


def ex(src, show=False, **subs):
    for a, b in subs.items():
        assert src.count(a) == 1, f"substitution anchor {a!r} found {src.count(a)} times"
        src = src.replace(a, b)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(src, g)
    out = buf.getvalue()
    if show:
        print("\n".join("      | " + l for l in out.splitlines()))
    return out


def run_cell(run_on, approved="", redo="[]", show=False):
    return ex(B.C_RUN, show=show,
              **{'RUN_ON            = "none"': f'RUN_ON            = "{run_on}"',
                 'APPROVED_RULEBOOK = ""': f'APPROVED_RULEBOOK = "{approved}"',
                 'REDO              = []': f'REDO              = {redo}'})


print("A. prompts, inputs, self-tests")
ex(B.C_SETUP)
tmp = Path(tempfile.mkdtemp())
g["OUT_DIR"] = tmp / "out"
g["RULEBOOK_FILE"] = tmp / "rulebook.json"
out = ex(B.C_PROMPTS, show=True)
ok("OK" in out and "audit failed" not in out, "knowledge, classify and validate prompts pass the audit")
ok(len(g["SITES"]) == 15, "15 SITEs read from v2", str(len(g["SITES"])))
out = ex(B.C_INPUTS, show=True)
ok("boot_rom: 2 batch(es)" in out and "trng_cache: 10 batch(es)" in out and "extract is code" in out, "batch plan")
out = ex(B.C_CHECKS, show=True)
ok(g["SELFTEST_OK"], "all self-tests in the checks cell pass")
ok(g["WORDS_SELFTEST_OK"] and "design-word self-test: PASS" in out, "design-word self-test passes")
ok("occurrence-count self-test: PASS" in out, "occurrence-count and index/slice self-tests pass (boot_rom)")
ok("structure and inventory self-test: PASS" in out, "structure finder and code inventory self-tests pass")
L = g["source_lines"](g["numbered_entity_source"](Path("data/RTL_data/neorv32_boot_rom.vhd"), "neorv32_boot_rom"))
ok(g["occurrence_lines"](L, "rden") == {38, 58, 60, 64, 65}, "rden lines read off the source",
   str(sorted(g["occurrence_lines"](L, "rden"))))
ok(g["occurrence_lines"](L, "bus_rsp_o.err") == {24, 66}, "a field gets its base's declaration line")

print("\nB. stub model")
EXP = json.load(open(g["EXPECTED_FILE"], encoding="utf-8"))
BY = {e["name"]: e["rows"] for e in EXP["elements"]}


def stub_rulebook():
    rules = {}
    for s in g["SITES"]:
        body = re.search(rf"^- {s}:\s*(.+?)(?=^- [A-Z_]+:|\Z)", g["SITES_MD"], re.S | re.M).group(1)
        first = re.split(r"(?<=\.)\s", body.strip(), maxsplit=1)[0]
        rules[s] = {"trigger": "stub", "required_structure": ["<target_label> <= <element_label>;"],
                    "context": "stub", "exclusion": [], "basis": [first]}
    return {"SITE_RULES": rules,
            "CONFLICT_RULES": [{"sites": ["EDGE_CHECK", "IF_COND"], "rule": "stub",
                                "basis": ["The edge function, `rising_edge(...)` or `falling_edge(...)`, "
                                          "is what identifies this site."]}]}


def structure_for(src, line, bad_name=None):
    ch = g["structure_chain"](g["structures_of"](src), line)
    out = [{"kind": s["kind"], "lines": list(s["lines"]), **({"opened by": s["opened by"]} if s["opened by"] else {})}
           for s in ch]
    if bad_name == "rdata" and line == 48:
        out = [dict(s, lines=[s["lines"][0], s["lines"][1] + 1]) if s["kind"] == "branch" else s for s in out]
    if bad_name == "rstn_i" and line == 57:
        out = [s for s in out if s["kind"] != "branch"]
    return out


class Stub:
    def __init__(self):
        self.usage, self.calls, self.mode, self.last = [], Counter(), "good", {}

    def complete(self, system, user, max_tokens=0, effort=None):
        # the real API returns 400 in JSON mode when the input does not contain the word "json"
        assert "json" in user.lower(), "API would refuse: the input does not contain 'json'"
        self.usage.append({"in": 0, "out": 0, "reasoning": 0, "cached_in": 0})
        step = next(k for k, v in g["SYSTEM"].items() if v == system)
        self.calls[step] += 1
        self.last[step] = self.last.get(step, "") + user
        if step == "knowledge":
            return json.dumps(stub_rulebook())
        src = user.split("line number:\n\n", 1)[1].split("\n\nCLOSED SET", 1)[0]
        names = [e["name"] for e in json.loads(
            user.split("CLOSED SET, in this order:\n", 1)[1].split("\n\n", 1)[0])]
        inv_text = user.split("OCCURRENCE INVENTORY, made by a program:\n", 1)[1]
        inventory, _ = json.JSONDecoder().raw_decode(inv_text)
        bad = self.mode == "bad" and step == "classify"
        if self.mode == "broken" and step == "validate":
            return '{"not json'
        ans = {}
        for n in names:
            tags_at = {}
            for r in BY[n]:
                tags_at.setdefault(r["line"], []).append(r["site"])
            entries = []
            seen_lines = Counter()
            for inv in inventory[n]:
                ln, oid = inv["Occurrence Lines"], inv["Occurrence ID"]
                seen_lines[ln] += 1
                tags = list(tags_at.get(ln, []))
                if bad and n == "rden" and ln == 64:
                    continue                                   # planted: dropped occurrence
                if bad and n == "rden" and ln == 65:
                    tags = ["RHS_OPERAND"]                     # planted: wrong tag
                if bad and n == "bus_req_i" and ln == 60 and seen_lines[ln] > 1:
                    continue                                   # planted: two occurrences merged
                if bad and n == "bus_req_i.addr" and ln == 48:
                    tags = [t for t in tags if t != "PART_SELECT"] + ["INPUT_OP"]   # planted: add-on gap, invented site
                if bad and n == "bus_rsp_o.ack" and ln == 65:
                    tags = ["FIELD_USE"]                       # planted: FIELD_USE on a field
                if bad and n == "clk_i":
                    oid = oid % len(inventory[n]) + 1          # planted: clk_i renumbered in a cycle
                if bad and n == "bus_rsp_o.err" and ln == 66:
                    oid = str(oid)                             # planted: an ID written as text
                if bad and n == "rstn_i" and ln == 57:
                    oid = oid - 1                              # planted: another line's ID, with a wrong Structure
                entries.append({"Occurrence ID": oid,
                                "Occurrence Lines": ln,
                                "Structure": structure_for(src, ln, n if bad else None),
                                "Role": "stub role" + (" (the reset branch, in initialization)"
                                                       if bad and n == "rden" and ln == 58 else ""),
                                "SITE Tagged": tags})
            if bad and n == "rden":
                entries.append({"Occurrence ID": 100, "Occurrence Lines": 59, "Structure": structure_for(src, 59),
                                "Role": "stub role", "SITE Tagged": ["IF_COND"]})   # planted: line without the element
            ans[n] = entries
        return json.dumps(ans)

    def cost(self):
        return {"calls": len(self.usage)}


stub = Stub()
g["client"] = stub
out = ex(B.C_RULEBOOK, show=True)
ok("no rulebook yet" in out, "rulebook cell runs with no rulebook on disk")

out = run_cell("none", show=True)
ok("1 call, then stop for approval" in out and "= 20 calls" in out and "= 4 calls" in out,
   "RUN_ON none prints the plan and makes no call")
ok(sum(stub.calls.values()) == 0, "no call made")

out = run_cell("boot_rom", show=True)
ok(stub.calls["knowledge"] == 1 and stub.calls["classify"] == 0 and "is not approved" in out,
   "first run: one knowledge call, then stops for approval")
sha = g["RULEBOOK_SHA"]
ok(g["RULEBOOK_USABLE"] and "review" not in out and "PROBLEM" not in out,
   "stub rulebook passes its checks (basis quotes found in v2)")

out = run_cell("boot_rom", approved=sha, show=True)
ok(stub.calls["extract"] == 0 and stub.calls["classify"] == 2 and stub.calls["validate"] == 2
   and len(list((g["OUT_DIR"] / "extract").rglob("*.json"))) == 2,
   "approved run: extract built by code (2 files, no call), 2 classify, 2 validate calls", str(dict(stub.calls)))

print("\nC. good answers")
out = ex(B.C_PARSE, show=True)
boot = out.split("===== trng_cache")[0]
boot_issues = "\n".join(l for l in boot.splitlines() if "per kind (" not in l)
ok(not any(w in boot_issues for w in ("not in v2", "missing", "not valid", "malformed")), "no shape issue")
ok(boot.count("not written:   0 of") == 3 and boot.count("exclude:          0 of") == 3
   and boot.count("occurrences with no entry:                            0 of") == 3,
   "occurrence checks all zero on all three steps")
ok(boot.count("entries whose Structure equals the source's: 45 of 45") == 2, "every Structure equals the source's")
ok(boot.count("entries with an Occurrence ID problem (another line's ID, repeated, not a whole number): 0 of 45") == 2
   and boot.count("entries added by the model (ID above the inventory's): 0 of 45") == 2
   and boot.count("FIELD_USE entries on an occurrence not written <element>.<field>: 0 of 45  (exact)") == 2
   and boot.count("positions inside a target's parentheses tagged LHS_PROC or LHS_CONC: 0 of 45") == 2
   and boot.count("whole-right-hand-side slices not tagged PART_SELECT alone: 0 of 45") == 2,
   "no ID problem, no added entry, no FIELD_USE on a field, no rule-decision gap on the correct answers")
out = ex(B.C_COMPARE, show=True)
ok(out.count("= 100%") == 20, "all 20 recall/precision figures are 100%", str(out.count("= 100%")))
out = ex(B.C_DIFF, show=True)
ok("0 of 21 profiles changed" in out and "entries whose Structure validate changed: 0 of 45 paired entries" in out
   and "0 entries without a partner" in out, "validate changed nothing")
n0 = sum(stub.calls.values())
run_cell("boot_rom", approved=sha)
ok(sum(stub.calls.values()) == n0, "a re-run with answers on disk makes no call")

print("\nD. planted errors")
stub.mode = "bad"
stub.last = {}
run_cell("boot_rom", approved=sha, redo='["extract", "classify", "validate"]')
out = ex(B.C_PARSE, show=True)
cp = out.split("classify:")[1].split("validate:")[0]
ok("rden @ 59: element not written there" in cp, "an entry on a line without the element is named")
ok("site not in v2 or added_sites: INPUT_OP" in cp, "a site outside the taxonomy is reported")
ok("rden @ 64: 1 occurrence(s), 0 entries" in cp, "the dropped occurrence is named")
ok("bus_req_i @ 60: 2 occurrence(s), 1 entry" in cp and "(merged):   1" in cp,
   "two occurrences merged into one entry are counted as merged")
INV_B = {}
for j in g["build_jobs"](["neorv32_boot_rom"]):
    INV_B.update(g["code_inventory"](j))
n_clk = len(INV_B["clk_i"])
clk_lines = [r["Occurrence Lines"] for r in INV_B["clk_i"]]
m = re.search(r"entries with an Occurrence ID problem \(another line's ID, repeated, not a whole number\): (\d+) of 44", cp)
ok(bool(m) and int(m.group(1)) == n_clk + 2,
   f"ID problems counted: {n_clk} renumbered clk_i entries, one ID written as text, one entry with another line's ID",
   m.group(0) if m else "")
ok(all(f"clk_i @ {clk_lines[k]}: ID {(k + 1) % n_clk + 1} belongs to line {clk_lines[(k + 1) % n_clk]}" in cp
       for k in range(n_clk))
   and 'bus_rsp_o.err @ 66: ID "2" is not a whole number' in cp and "rstn_i @ 57: ID 2 belongs to line 55" in cp,
   "each ID problem is listed with its line and the line its ID belongs to")
ok("entries added by the model (ID above the inventory's): 1 of 44" in cp and "rden @ 59: ID 100 (inventory's highest 5)" in cp,
   "an entry with an ID above the inventory's is listed as added, not as an ID problem")
ok("FIELD_USE entries on an occurrence not written <element>.<field>: 1 of 44  (exact)" in cp
   and "bus_rsp_o.ack @ 65: FIELD_USE on ID(s) [2]" in cp,
   "FIELD_USE on a field is counted and named by its ID")
m = re.search(r"entries whose Structure equals the source's: (\d+) of (\d+)", cp)
ok(bool(m) and int(m.group(2)) - int(m.group(1)) == 2 and "rdata @ 48" in cp and "rstn_i @ 57" in cp,
   "the two planted Structure errors are counted and listed", m.group(0) if m else "")
ok("branch 3/1/1/0" in cp or re.search(r"branch \d+/1/1/0", cp) is not None,
   "per kind: one branch with a wrong end, one missing branch")
ok("bus_req_i.addr @ 48: index 0 vs INDEXED_NAME 0, slice 1 vs PART_SELECT 0" in cp, "a missing PART_SELECT is reported")
ok(re.search(r"Roles with a design word \(word list [0-9a-f]{12}, lower bound\): 1 of", cp) is not None
   and "rden @ 58: reset, initialization" in cp,
   "design words in a Role are flagged, 'initialization' included, with the word list's sha")
ok("Roles with a design word" not in out.split("extract:")[1].split("classify:")[0], "extract is not checked for Roles")
vm = stub.last.get("validate", "")
ok("- bus_req_i: line 60 holds 2 occurrence(s) of the element (inventory Occurrence ID(s) 3 (bus_req_i.stb), "
   "4 (bus_req_i.rw)); the profile has 1 entry there. No entry there carries Occurrence ID(s) 4." in vm
   and "- rden: line 64 holds 1 occurrence(s) of the element (inventory Occurrence ID(s) 4 (rden)); the profile has 0 "
   "entries there. No entry there carries Occurrence ID(s) 4." in vm
   and "uses 'reset'" in vm and "uses 'initialization'" in vm
   and "- bus_req_i.addr: line 48 writes the element with one position in parentheses 0 time(s) and with a range 1 time(s)" in vm,
   "validate receives the per-line occurrence items with their inventory IDs, the add-on and the design-word items")
clk_items = [l for l in vm.splitlines() if l.startswith("- clk_i: line ")]
ok(len(clk_items) == n_clk and all("which the inventory gives to line" in l and "No entry there carries" in l
                                   for l in clk_items),
   "validate receives one item per renumbered clk_i line, naming the ID it lacks and the line its ID belongs to")
ok("- rstn_i: line 57 holds 1 occurrence(s) of the element (inventory Occurrence ID(s) 3 (rstn_i)); the profile has 1 "
   "entry there. No entry there carries Occurrence ID(s) 3. An entry there carries Occurrence ID 2, which the inventory "
   "gives to line 55." in vm
   and '- bus_rsp_o.err: the entry at line 66 carries Occurrence ID "2", which is not a whole number.' in vm
   and "- rden: the entry at line 59 carries Occurrence ID 100, above the inventory's highest (5)" in vm,
   "validate receives the another-line ID, text ID and added-occurrence items")
ok("- bus_rsp_o.ack: at line 65, the entry with Occurrence ID(s) 2 carries FIELD_USE, but that occurrence is not "
   "written <element>.<field>." in vm,
   "validate receives the FIELD_USE-on-a-field item, naming the one wrong ID")
ok("- rdata: the entry with Occurrence ID 2 at line 48 gives the structures architecture body 41-69; process 45-50; if 47-49; "
   "branch 47-49 (EDGE_CHECK); the program finds architecture body 41-69; process 45-50; if 47-49; branch 47-48 (EDGE_CHECK)." in vm,
   "validate receives the exact Structure correction")
out = ex(B.C_COMPARE, show=True)
cls = out.split("== classify ==")[1].split("== validate ==")[0]
val = out.split("== validate ==")[1]
m = re.search(r"\(line, SITE\) pairs\s+recall\s+(\d+)/(\d+)", cls)
ok(bool(m) and m.group(1) != m.group(2), "classify hand pair recall falls below 100%",
   f"{m.group(1)}/{m.group(2)}" if m else "not found")
ok(val.count("= 100%") == 8, "validate, which returned the correct answer, scores 100%")
out = ex(B.C_DIFF, show=True)
ok("rden:" in out and "(64, 'WHEN_COND')" in out and "(48, 'INPUT_OP')" in out
   and re.search(r"entries whose Structure validate changed: 2 of \d+ paired entries \(paired inside each element and "
                 r"line; 3 entries without a partner not compared\)", out) is not None,
   "diff names what validate changed; the rstn_i entry whose ID validate corrected is still paired and counted")

print("\nD2. the two rule decisions, on real cache lines read by hand")
cjob = next(j for j in g["build_jobs"](["neorv32_cache"]) if j["entity"] == "neorv32_cache_memory"
            and "acc_idx" in [e["name"] for e in j["elems"]] and "addr_i" in [e["name"] for e in j["elems"]])
cinv = g["code_inventory"](cjob)
cL = g["source_lines"](cjob["src"])


def tagged(name, line_tags):
    return [dict(r, **{"SITE Tagged": line_tags.get(r["Occurrence Lines"], ["X"])}) for r in cinv[name]]


rows_idx = tagged("acc_idx", {383: ["LHS_PROC", "INDEX"], 385: ["INDEX"]})
rows_adr = tagged("addr_i", {367: ["DIRR_ASS", "PART_SELECT"], 366: ["PART_SELECT"]})
t1, s1 = g["rule_decision_gaps"](cL, cinv["acc_idx"], rows_idx, "acc_idx")
t2, s2 = g["rule_decision_gaps"](cL, cinv["addr_i"], rows_adr, "addr_i")
ok([x[1] for x in t1] == [383] and [x[1] for x in s2 if x[1] in (366, 367)] == [367],
   "cache 383 acc_idx tagged LHS_PROC + INDEX and cache 367 addr_i tagged DIRR_ASS + PART_SELECT are found; "
   "385 INDEX alone and 366 PART_SELECT alone are not", f"{t1} {s2}")
txt = g["code_checklist"](cjob, {"acc_idx": rows_idx, "addr_i": rows_adr})
ok("- acc_idx: the entry with Occurrence ID" in txt and "at line 383 is tagged LHS_PROC, INDEX, but that occurrence is "
   "inside the parentheses of the assignment's target" in txt
   and "at line 367 is tagged DIRR_ASS, PART_SELECT, but that occurrence is a slice that is the whole right-hand side" in txt,
   "validate receives both rule-decision items")

print("\nE. stale answers and invalid JSON")
stub.mode = "good"
run_cell("boot_rom", approved=sha, redo='["extract", "classify", "validate"]')
job = g["build_jobs"](["neorv32_boot_rom"])[0]
p = g["out_path"]("extract", job)
rec = json.loads(p.read_text(encoding="utf-8"))
d = json.loads(rec["raw"])
first = job["elems"][0]["name"]
d[first] = d[first][:-1]
rec["raw"] = json.dumps(d)
p.write_text(json.dumps(rec), encoding="utf-8")
ok(g["read_answer"]("classify", job)["stale"], "an edited inventory makes classify stale")
before = dict(stub.calls)
run_cell("boot_rom", approved=sha)
ok(stub.calls["classify"] == before["classify"] + 1 and stub.calls["validate"] == before["validate"] + 1,
   "only the stale batch's classify and validate are called again")
stub.mode = "broken"
run_cell("boot_rom", approved=sha, redo='["validate"]')
out = ex(B.C_PARSE)
ok("answer is not valid JSON: 2" in out, "invalid JSON is reported")
stub.mode = "good"
run_cell("boot_rom", approved=sha)
ok(len(list((g["OUT_DIR"] / "validate").rglob("*.invalid.json"))) == 2,
   "invalid answers are called again, and the bad ones kept beside them")

print("\nF. rulebook problems")
rb = json.loads(g["RULEBOOK_FILE"].read_text(encoding="utf-8"))
rb["SITE_RULES"].pop("INDEX")
rb["SITE_RULES"]["IF_COND"]["exclusion"] = ["an edge condition is INPUT_OP"]
rb["SITE_RULES"]["DIRR_ASS"]["required_structure"] = ["bus_rsp_o <= <element_label>;"]
rb["SITE_RULES"]["WHEN_COND"]["basis"] = ["A sentence that v2 does not contain."]
g["RULEBOOK_FILE"].write_text(json.dumps(rb), encoding="utf-8")
out = ex(B.C_RULEBOOK, show=True)
ok("SITEs missing: ['INDEX']" in out and "INPUT_OP" in out and "bus_rsp_o" in out,
   "missing SITE, invented SITE name and corpus identifier all block the rulebook")
ok("WHEN_COND: basis not found" in out, "a basis quote not in v2 is listed for review")
out = run_cell("boot_rom", approved=g["RULEBOOK_SHA"])
ok("stopped: fix rulebook.json" in out, "the run refuses a rulebook with problems")

print("\nG. render")
g["RULEBOOK_FILE"].write_text(json.dumps({"sites_sha": g["SITES_SHA"], **stub_rulebook()}, indent=2),
                              encoding="utf-8")
ex(B.C_RULEBOOK)
out = ex(B.C_RENDER, show=True)
md = g["OUT_DIR"] / "tables" / f"{g['PROMPT_SHA']['classify']}_{g['PROMPT_SHA']['validate']}" / "neorv32_boot_rom.md"
text = md.read_text(encoding="utf-8") if md.exists() else ""
ok("| Occurrence Lines | Context | SITE Tagged |" in text and "INDEX, PART_SELECT" in text
   and not (g["OUT_DIR"] / "neorv32_boot_rom.md").exists(),
   "tables use the annotation_process.md format, with tag lists, in a folder named by the prompt shas")
ok("architecture body 41-69; process 45-50; if 47-49; branch 47-48 (EDGE_CHECK); stub role" in text,
   "the Context is built by code from the structures and the Role")
m = re.search(r"structures from the finder for (\d+) of (\d+) entries; 0 of those differ", out)
n_render = int(m.group(2)) if m else -1
ok(bool(m) and m.group(1) == m.group(2)
   and f"Count: structures from the finder for {n_render} of {n_render} entries; 0 of those differ" in text,
   "render says where its structures come from, in the log and in the table file", m.group(0) if m else "")
vjob = next(j for j in g["build_jobs"](["neorv32_boot_rom"]) if "rdata" in [e["name"] for e in j["elems"]])
vp = g["out_path"]("validate", vjob)
vrec = json.loads(vp.read_text(encoding="utf-8"))
vd = json.loads(vrec["raw"])
for r in vd["rdata"]:
    if r["Occurrence Lines"] == 48:
        r["Structure"] = [dict(s, lines=[s["lines"][0], s["lines"][1] + 1]) if s["kind"] == "branch" else s
                          for s in r["Structure"]]
vrec["raw"] = json.dumps(vd)
vp.write_text(json.dumps(vrec), encoding="utf-8")
ok(not g["read_answer"]("validate", vjob)["stale"], "the edited validate answer is still current")
out = ex(B.C_RENDER, show=True)
rrow = md.read_text(encoding="utf-8").split("### rdata\n")[1].split("###")[0]
ok("branch 47-48 (EDGE_CHECK); stub role" in rrow and "47-49 (EDGE_CHECK)" not in rrow
   and f"structures from the finder for {n_render} of {n_render} entries; 1 of those differ" in out,
   "a wrong Structure in the answer is replaced by the finder's in the table, and counted")
real_structures_of = g["structures_of"]


def failing_finder(src):
    # fails only when the render cell asks, so the answers can still be read
    if sys._getframe(1).f_code.co_name == "render":
        raise g["StructureError"]("planted")
    return real_structures_of(src)


g["structures_of"] = failing_finder
out = ex(B.C_RENDER, show=True)
g["structures_of"] = real_structures_of
rrow = md.read_text(encoding="utf-8").split("### rdata\n")[1].split("###")[0]
ok("the structure finder failed" in out and "(the model's Structure) architecture body" in rrow
   and "branch 47-49 (EDGE_CHECK); stub role" in rrow
   and f"structures from the finder for 0 of {n_render} entries" in out,
   "where the finder fails, each row falls back to the model's Structure and says so")
vd["rdata"].append({"Occurrence ID": 99, "Occurrence Lines": 42, "Structure": [{"kind": "process", "lines": [900, 901]}],
                    "Role": "stub role", "SITE Tagged": []})
vrec["raw"] = json.dumps(vd)
vp.write_text(json.dumps(vrec), encoding="utf-8")
out = ex(B.C_RENDER, show=True)
rrow = md.read_text(encoding="utf-8").split("### rdata\n")[1].split("###")[0]
ok("| line 42 | (the model's Structure: line not in the source) process 900-901; stub role |" in rrow
   and f"structures from the finder for {n_render} of {n_render + 1} entries" in out,
   "an entry on a line the source does not show keeps the model's Structure, marked, and is counted")


def failing_everywhere(src):
    raise g["StructureError"]("planted")


g["structures_of"] = failing_everywhere
job_b = g["build_jobs"](["neorv32_boot_rom"])[0]
cl_b = g["read_answer"]("classify", job_b)
try:
    txt = g["code_checklist"](job_b, cl_b["parsed"] if cl_b and cl_b["parsed"] else {})
    tot_b, _, listing_b, failed_b = g["structure_checks"]("classify", g["MODULES"]["boot_rom"])
    out_p = ex(B.C_PARSE)
    survived = True
except Exception as ex_:  # noqa: BLE001
    txt, listing_b, failed_b, out_p, survived = str(ex_), [], [], "", False
g["structures_of"] = real_structures_of
ok(survived and "could not read the structures of this entity" in txt and "the program finds" not in txt
   and len(failed_b) == 2 and not listing_b and "entries whose Structure equals the source's: 0 of 0" in out_p
   and "2 batch(es) not checked" in out_p and out_p.count("not checked, the structure finder failed") >= 2,
   "a finder failure does not stop the CODE CHECK list or the parse cell; both say what they skipped")

print("\nH. SITEs added by the rulebook")
base_rb = {"sites_sha": g["SITES_SHA"], **stub_rulebook()}


def load_with(mutate):
    rb = json.loads(json.dumps(base_rb))
    mutate(rb)
    g["RULEBOOK_FILE"].write_text(json.dumps(rb, indent=2), encoding="utf-8")
    return ex(B.C_RULEBOOK)


def add_case(rb):
    rb["added_sites"] = ["CASE_EXPR"]
    rb["SITE_RULES"]["CASE_EXPR"] = {"trigger": "stub", "required_structure": ["case <element_label> is"],
                                     "context": "stub", "exclusion": ["CASE_EXPR is not IF_COND"],
                                     "basis": []}


out = load_with(add_case)
ok(g["RULEBOOK_USABLE"] and "PROBLEM" not in out and "CASE_EXPR" in g["SITES"] and len(g["SITES"]) == 16,
   "a SITE listed in added_sites is accepted and joins the taxonomy", str(len(g["SITES"])))
rec = {"raw": json.dumps({"x": [{"Occurrence ID": 1, "Occurrence Lines": 21, "Structure": [], "Role": "r",
                                 "SITE Tagged": ["CASE_EXPR"]}]}), "names": ["x"]}
_, iss = g["parse_answer"]("classify", rec, {21: "line"})
ok(not any("added_sites" in k for k in iss), "an answer using the added SITE has no taxonomy issue")
out = load_with(lambda rb: (add_case(rb), rb.pop("added_sites")))
ok("SITEs neither in v2 nor in added_sites: ['CASE_EXPR']" in out and len(g["SITES"]) == 15,
   "a SITE rule not listed in added_sites blocks the rulebook, and the taxonomy falls back to v2")
out = load_with(lambda rb: (add_case(rb), rb["added_sites"].append("IF_COND")))
ok("added_sites already in v2" in out and not g["RULEBOOK_USABLE"], "added_sites naming a v2 SITE blocks it")
_, iss = g["parse_answer"]("classify", rec, {21: "line"})
ok(any("CASE_EXPR" in k for k in iss), "with the rulebook blocked, CASE_EXPR in an answer is reported")

print("\nI. prompt layout")
load_with(lambda rb: None)
v2_line = "The structure/basic syntax of a port declaration statement:"
ok(v2_line in g["SITES_MD"] and all(v2_line not in g["SYSTEM"][s] for s in ("classify", "validate")),
   "no v2 text in the classify or validate prompt")
ok(all("N. ANNOTATION RULEBOOK" in g["SYSTEM"][s] for s in ("classify", "validate")),
   "the rulebook is section N of both prompts")
ok(all(0 < g["SYSTEM"][s].index("D. STRUCTURAL NAVIGATION") < g["SYSTEM"][s].index("F. SITE-DISAMBIGUATION RULES")
       < g["SYSTEM"][s].index("N. ANNOTATION RULEBOOK") for s in ("classify", "validate")),
   "structural navigation comes before the site rules and the rulebook")
out = load_with(lambda rb: rb.update(sites_sha="000000000000"))
ok(g["RULEBOOK_USABLE"] and "review  SITES_draft_v2.md changed" in out and "PROBLEM" not in out,
   "a v2 edit after the rulebook was built is a review note, not a stop")

shutil.rmtree(tmp, ignore_errors=True)
print("\n" + "=" * 60)
print("ALL CHECKS PASS" if not fails else f"{len(fails)} FAILED: {fails}")
