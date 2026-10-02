# -*- coding: utf-8 -*-
"""Run the v3b notebook's own cells with a stubbed model. No API call; answers go to a temp folder, nothing is
written to the repo. v3b = v3 with batches capped by occurrence count (MAX_OCC), so this checks the batch plan first,
then the same end-to-end path as the v3 preflight."""
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
import build_occurrence_notebook_v3b as B  # noqa: E402

os.chdir(B.ROOT)
g = {"__name__": "nb"}
fails = []
V3 = {"classify": "94e281c90090", "validate": "cb5e024b7d65"}


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
    def __init__(self):
        self.calls = Counter()

    def complete(self, system, user, max_tokens=0, effort=None):
        assert "json" in user.lower(), "API would refuse: the input does not contain 'json'"
        step = next(k for k, v in g["SYSTEM"].items() if v == system)
        self.calls[step] += 1
        names = [e["name"] for e in json.loads(user.split("CLOSED SET, in this order:\n", 1)[1].split("\n\n", 1)[0])]
        inv, _ = json.JSONDecoder().raw_decode(user.split("OCCURRENCE INVENTORY, made by a program:\n", 1)[1])
        return json.dumps({n: [{"Occurrence ID": r["Occurrence ID"], "Occurrence Lines": r["Occurrence Lines"],
                                "Role": "stub role", "SITE Tagged": ["RHS_OPERAND"]} for r in inv[n]] for n in names})

    def cost(self):
        return {"calls": sum(self.calls.values()), "usd": 0.0}


print("A. setup, prompts, checks")
ex(B.C_SETUP)
ok(str(g["OUT_DIR"]).replace("\\", "/").endswith("occurrence_profiles_v3b"), "answers go to occurrence_profiles_v3b")
tmp = Path(tempfile.mkdtemp())
g["OUT_DIR"] = tmp / "out"
out = ex(B.C_PROMPTS)
ok("audit failed" not in out, "prompts pass the builder's audit")
ex(B.C_INPUTS)
out = ex(B.C_CHECKS)
ok(g["SELFTEST_OK"], "all self-tests in the checks cell pass")
ok("cache:" in out and "occurrences" in out, "the batch plan prints at the end of the checks cell")
stub = Stub()
g["client"] = stub
ex(B.C_RULEBOOK)
ok(g["RULEBOOK_SHA"] == "c44db45cd3ed", "the v3 rulebook", g["RULEBOOK_SHA"])
ok(g["PROMPT_SHA"]["classify"] == V3["classify"] and g["PROMPT_SHA"]["validate"] == V3["validate"],
   "the same classify and validate prompts as v3: only the batching differs",
   f"{g['PROMPT_SHA']['classify']} / {g['PROMPT_SHA']['validate']}")

print("\nB. the batch plan")
cap, maxel = g["MAX_OCC"], g["BATCH"]
over, total, calls = [], 0, {}
for s, mods in g["MODULES"].items():
    js = g["build_jobs"](mods)
    calls[s] = 2 * len(js)
    for m in mods:
        for ent, elems in g["load_elements"](m):
            got = [e["name"] for j in js if j["entity"] == ent for e in j["elems"]]
            ok(got == [e["name"] for e in elems], f"{ent}: every element in exactly one batch, closed-set order kept")
    for j in js:
        L = g["source_lines"](j["src"])
        n = sum(len(g["occurrence_matches"](L, e["name"])) for e in j["elems"])
        total += n
        if len(j["elems"]) > maxel or (n > cap and len(j["elems"]) > 1):
            over.append((j["entity"], j["batch"], len(j["elems"]), n))
        if s == "cache":
            print(f"      cache: {j['entity']} batch {j['batch']}: {len(j['elems'])} elements, {n} occurrences")
ok(not over, f"no batch over {maxel} elements or {cap} occurrences (a lone element may exceed the cap)", str(over))
ok(total == 707, "707 occurrences across all batches, as in run 6 and v3", str(total))
print(f"      model calls per run set: {calls}")

print("\nC. the whole pipeline with the stub model")
for m in ("boot_rom", "trng", "cache"):
    ex(B.C_RUN, **{'RUN_ON            = "none"': f'RUN_ON            = "{m}"',
                   'APPROVED_RULEBOOK = ""': f'APPROVED_RULEBOOK = "{g["RULEBOOK_SHA"]}"'})
want = sum(calls.values()) // 2
ok(stub.calls["classify"] == want and stub.calls["validate"] == want, "one classify and one validate call per batch",
   str(dict(stub.calls)))
out = ex(B.C_PARSE)
ok("entry fields differ" not in out and "occurrences with no entry:                            0 of" in out,
   "parse cell: clean")
ex(B.C_DIFF)
out = ex(B.C_RENDER)
n = sum(int(x.split(" for ")[1].split(" of ")[0]) for x in out.splitlines() if " for " in x and " of " in x)
ok(n == 707, "every table row has its Context and Path", f"{n} of 707")

print(f"\n{'ALL PASS' if not fails else f'{len(fails)} FAIL: ' + '; '.join(fails)}")
print(f"(temp folder {tmp} holds the stub run; nothing was written to the repo)")
