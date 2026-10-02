# -*- coding: utf-8 -*-
"""Run the v3 notebook's own cells with a stubbed model. No API call; answers go to a temp folder, nothing is
written to the repo. Covers what v3 changed: the structure step (2b), the prompts, the answer format without
Structure, the CODE CHECK without structure items, and the parse / diff / render cells."""
import contextlib
import io
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

S = Path(__file__).parent
sys.path.insert(0, str(S))
import build_occurrence_notebook_v3 as B  # noqa: E402

os.chdir(B.ROOT)
g = {"__name__": "nb"}
fails = []
RUN6 = {"classify": "6f4f22e256e3", "validate": "f4082229020d"}


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


class Stub:
    """Answers classify and validate in the v3 format: four fields per inventory occurrence."""
    def __init__(self):
        self.calls, self.last = Counter(), {}

    def complete(self, system, user, max_tokens=0, effort=None):
        assert "json" in user.lower(), "API would refuse: the input does not contain 'json'"
        step = next(k for k, v in g["SYSTEM"].items() if v == system)
        self.calls[step] += 1
        self.last[step] = user
        names = [e["name"] for e in json.loads(user.split("CLOSED SET, in this order:\n", 1)[1].split("\n\n", 1)[0])]
        inv, _ = json.JSONDecoder().raw_decode(user.split("OCCURRENCE INVENTORY, made by a program:\n", 1)[1])
        return json.dumps({n: [{"Occurrence ID": r["Occurrence ID"], "Occurrence Lines": r["Occurrence Lines"],
                                "Role": "stub role", "SITE Tagged": ["RHS_OPERAND"]} for r in inv[n]] for n in names})

    def cost(self):
        return {"calls": sum(self.calls.values()), "usd": 0.0}


print("A. setup, prompts, inputs, self-tests")
ex(B.C_SETUP)
tmp = Path(tempfile.mkdtemp())
g["OUT_DIR"] = tmp / "out"
ok(str(g["PROMPT_DIR"]).replace("\\", "/").endswith("occurrence_prompts_v3"), "prompts read from occurrence_prompts_v3")
out = ex(B.C_PROMPTS, show=True)
ok("audit failed" not in out, "v3 prompts pass the builder's prompt audit")
out = ex(B.C_INPUTS)
ok("boot_rom: 2 batch(es)" in out and "trng_cache: 10 batch(es)" in out, "same batch plan as run 6")
out = ex(B.C_CHECKS)
ok(g["SELFTEST_OK"], "all self-tests in the checks cell pass")
stub = Stub()
g["client"] = stub
out = ex(B.C_RULEBOOK, show=True)
v2rb = json.loads((B.ROOT / "annotation_pack_elements/occurrence_prompts_v2/rulebook.json").read_text(encoding="utf-8"))
v3rb = json.loads(Path(g["RULEBOOK_FILE"]).read_text(encoding="utf-8"))
DECIDE = ("trigger", "required_structure", "exclusion", "basis", "kind")
same = all(v2rb["SITE_RULES"][s].get(k) == v3rb["SITE_RULES"][s].get(k) for s in v2rb["SITE_RULES"] for k in DECIDE) \
    and set(v2rb["SITE_RULES"]) == set(v3rb["SITE_RULES"]) \
    and [(c["sites"], c.get("basis")) for c in v2rb["CONFLICT_RULES"]] == [(c["sites"], c.get("basis")) for c in v3rb["CONFLICT_RULES"]]
ok(same, "rulebook: every SITE's trigger, required structure, exclusions, basis and kind are run 6's; only context "
   "sentences that pointed at the removed Structure field changed", f"v3 sha {g['RULEBOOK_SHA']} (run 6: 34d10274b852)")
ok("Structure" not in json.dumps({"S": v3rb["SITE_RULES"], "C": v3rb["CONFLICT_RULES"]}),
   "no rule text that reaches the prompt mentions Structure")
ok(g["PROMPT_SHA"]["classify"] not in (None, RUN6["classify"]) and g["PROMPT_SHA"]["validate"] not in (None, RUN6["validate"]),
   "new classify and validate prompt shas, so run 6's answers are never read as v3's",
   f"{g['PROMPT_SHA']['classify']} / {g['PROMPT_SHA']['validate']}")
for step in ("classify", "validate"):
    sysp = g["SYSTEM"][step]
    ok("Structure" not in sysp and "Context" in sysp and "Path" in sysp,
       f"{step} prompt: no Structure, reads Context and Path", f"{len(sysp):,} chars")

print("\nB. step 2b: Context and Path on every inventory row")
jobs = [j for m in ("boot_rom", "trng_cache") for j in g["build_jobs"](g["MODULES"][m])]
rows = [(j, n, r) for j in jobs for n, rs in g["code_inventory"](j).items() for r in rs]
ok(len(rows) == 707, "707 inventory rows, as run 6's extract", str(len(rows)))
ok(all(set(r) == set(g["FIELDS"]["extract"]) for _j, _n, r in rows), "every row has exactly the six extract fields")
none = [(j["entity"], n, r["Occurrence Lines"]) for j, n, r in rows if r["Context"].startswith("none")]
ok(not none, "every row got a Context from the grammar", str(none[:3]))


def row(ent, name, line, k=0):
    return sorted((r for j, n, r in rows if j["entity"] == ent and n == name and r["Occurrence Lines"] == line),
                  key=lambda r: r["Occurrence ID"])[k]


r = row("neorv32_cache", "cache_o.we", 194)
ok(r["Context"].startswith("else branch 193-196 in if 190-197 in elsif branch 189-197"), "cache_o.we @ 194 Context",
   r["Context"][:80])
ok(r["Path"][-1] == "not ((host_req_i.rw = '0') or (READ_ONLY = true))", "cache_o.we @ 194: the else arm's negated "
   "condition is in its Path", r["Path"][-1])
ok(row("neorv32_boot_rom", "rdata", 64)["Path"] == ["rden = '1'"], "boot_rom rdata @ 64: when-else arm in the Path")
ok(row("neorv32_boot_rom", "rden", 60)["Path"] == ["not (rstn_i = '0')", "rising_edge(clk_i)"], "boot_rom rden @ 60 Path")

print("\nC. answer format, CODE CHECK")
j = next(x for x in jobs if x["entity"] == "neorv32_boot_rom")
inv = g["code_inventory"](j)
msg = g["user_message"]("classify", j, {"extract": inv})
ok('"Context"' in msg and '"Path"' in msg and "construct_chain" not in msg and '"column"' not in msg,
   "classify's input carries Context and Path, not the internal chain")
L = g["source_lines"](j["src"])
names = [e["name"] for e in j["elems"]]
good = {n: [{"Occurrence ID": r["Occurrence ID"], "Occurrence Lines": r["Occurrence Lines"], "Role": "stub role",
             "SITE Tagged": ["RHS_OPERAND"]} for r in inv[n]] for n in names}
parsed, iss = g["parse_answer"]("classify", {"raw": json.dumps(good), "names": names}, L)
ok("entry fields differ from the format" not in iss, "a four-field answer parses clean", str(dict(iss)))
old = {n: [dict(e, Structure=[]) for e in es] for n, es in good.items()}
_p, iss = g["parse_answer"]("classify", {"raw": json.dumps(old), "names": names}, L)
ok(iss["entry fields differ from the format"] > 0, "an answer that still carries Structure is flagged",
   str(iss["entry fields differ from the format"]))
cl = g["code_checklist"](j, parsed)
ok("gives the structures" not in cl and "program finds" not in cl, "the CODE CHECK has no structure items")

print("\nD. the whole pipeline with the stub model, boot_rom and trng_cache")
for m in ("boot_rom", "trng_cache"):
    out = ex(B.C_RUN, show=False, **{'RUN_ON            = "none"': f'RUN_ON            = "{m}"',
                                     'APPROVED_RULEBOOK = ""': f'APPROVED_RULEBOOK = "{g["RULEBOOK_SHA"]}"'})
ok(stub.calls["classify"] == 12 and stub.calls["validate"] == 12, "12 classify and 12 validate calls, none for knowledge",
   str(dict(stub.calls)))
ok("OCCURRENCE PROFILES to check" in stub.last["validate"] and "gives the structures" not in stub.last["validate"],
   "validate's input: the profiles and a CODE CHECK without structure items")
written = sorted(p.relative_to(tmp).as_posix() for p in (tmp / "out").rglob("*.json"))
ok(all("/" + g["PROMPT_SHA"][s] + "/" in "/" + w for s in ("classify", "validate") for w in written if w.startswith(s)),
   "answers written under the v3 prompt shas", f"{len(written)} files")
out = ex(B.C_PARSE, show=False)
ok("Structure: owned by code" in out and "entry fields differ" not in out, "parse cell: clean, Structure owned by code")
out = ex(B.C_DIFF, show=False)
ok("Structure" not in out, "diff cell runs, no Structure comparison")
out = ex(B.C_RENDER, show=True)
tables = sorted((tmp / "out" / "tables").rglob("*.md"))
t = tables[0].read_text(encoding="utf-8") if tables else ""
ok(len(tables) == 3 and "| Occurrence Lines | Context | Path | SITE Tagged |" in t, "three tables, with Context and Path")
ok("for 707 of 707" in out.replace(",", "") or sum(int(x.split(" of ")[0].split()[-1]) for x in out.splitlines()
   if "Context and Path from the structure step for" in x) == 707, "every table row has its Context and Path")

print(f"\n{'ALL PASS' if not fails else f'{len(fails)} FAIL: ' + '; '.join(fails)}")
print(f"(temp folder {tmp} holds the stub run; nothing was written to the repo)")
