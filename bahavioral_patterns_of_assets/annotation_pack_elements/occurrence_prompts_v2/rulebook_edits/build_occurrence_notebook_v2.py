# -*- coding: utf-8 -*-
"""Write notebooks/occurrence_profiles_v2.ipynb: the four-step pipeline. Each code cell starts with
a [tag] comment so the pre-flight can run the same cells with a stubbed model."""
import json
from pathlib import Path

ROOT = Path("E:/jobs/ff/test/Prepoison_subset/bahavioral_patterns_of_assets")
NB = ROOT / "notebooks" / "occurrence_profiles_v2.ipynb"
ref = json.loads((ROOT / "notebooks" / "parser_v4.ipynb").read_text(encoding="utf-8"))

MD0 = r"""# Occurrence profiles v2: four steps

| Step | Prompt | Calls | What it does |
|---|---|---|---|
| 1 knowledge | `1_knowledge.md` | once | turns `SITES_draft_v2.md` into `rulebook.json`: a decision rule per SITE, and rules for look-alike SITEs. **You read and approve it before anything else runs.** |
| 2 extract | code, no model | per batch | lists every occurrence of every element: Occurrence ID, line, name as written, line text. |
| 3 classify | `3_classify.md` + `annotate_rules.md` + rulebook | per batch | for every occurrence: its enclosing structures (section D, structural navigation), its role, and its SITEs. |
| 4 validate | `4_validate.md` + `annotate_rules.md` + rulebook | per batch | re-derives every entry from the source and the rulebook, and returns corrected profiles. |

`SITES_draft_v2.md` reaches only step 1 and the check of the rulebook's basis quotes. Steps 3 and 4 never see it: the rulebook is the taxonomy, including the SITEs it adds (`added_sites`).

Prompts live in `annotation_pack_elements/occurrence_prompts_v2/`. Answers go to `occurrence_profiles_v2/<step>/<prompt sha>/`, so a changed prompt never overwrites an older run.

**Check before trusting it.** `RUN_ON = "boot_rom"` runs steps 2-4 on `neorv32_boot_rom`; the compare cell scores each step against `boot_rom_expected_v2.json`. Only the six `hand` elements are a real answer; the `predicted` fields are what v2 says, never checked by hand.

**Checks that use no model** (parse cell): the answer's shape; every tag is in the taxonomy; every occurrence has one entry; every entry carries the inventory's Occurrence ID for its line; every Structure equals the structures a self-tested finder reads off the source; indexed and sliced names carry INDEXED_NAME / PART_SELECT; FIELD_USE sits only on an occurrence written `<element>.<field>`; a position inside the parentheses of an assignment target is not tagged LHS_PROC / LHS_CONC; a whole-right-hand-side slice is PART_SELECT alone; no Role says what something is for. Classify's accuracy on these is the model's own; validate gets every mismatch on its CODE CHECK list. In the tables, the Context is the finder's structures followed by the model's Role; the model's Structure stays in the answers for scoring. Tables go to `occurrence_profiles_v2/tables/<classify sha>_<validate sha>/`.

Run from top to bottom. Change only the three settings in the run cell."""

C_SETUP = r"""# [setup]
import os, sys, json, re, hashlib
from pathlib import Path
from collections import Counter
from functools import lru_cache

if Path.cwd().name == "notebooks":
    os.chdir(Path.cwd().parent)
sys.path.insert(0, str(Path.cwd()))
print("cwd:", Path.cwd())

RTL_DIR       = Path("data/RTL_data")
ELEM_DIR      = Path("annotation_pack_elements")               # the element lists the parser sees
PROMPT_DIR    = ELEM_DIR / "occurrence_prompts_v2"             # the step prompts
SITES_FILE    = ELEM_DIR / "SITES_draft_v2.md"
RULEBOOK_FILE = PROMPT_DIR / "rulebook.json"                   # written by step 1; read it before approving
EXPECTED_FILE = ELEM_DIR / "boot_rom_expected_v2.json"
OUT_DIR       = ELEM_DIR / "occurrence_profiles_v2"
GT_FILE       = Path("ground_truth/manual_gt_neorv32.json")
REF_DIR       = Path("parsed_tuning18")

MODULES = {"boot_rom":   ["neorv32_boot_rom"],
           "trng_cache": ["neorv32_trng", "neorv32_cache"]}
STEPS   = ("extract", "classify", "validate")                  # step 1, knowledge, runs once before them

GEN_MODEL  = "gpt-5-mini"
EFFORT     = "medium"
BATCH      = 20        # elements per call
MAX_TOKENS = 64000     # reasoning tokens count against this too; a cut-off answer is invalid JSON.
                       # boot_rom used ~196 output tokens per entry per call; cache batch 2 has 160+
                       # occurrence lines, so 32000 would sit at the edge. Only tokens used are billed.
WORKERS    = 4

for p in (RTL_DIR, PROMPT_DIR, SITES_FILE, EXPECTED_FILE, GT_FILE, REF_DIR):
    print(f"  {str(p):58s} {'OK' if p.exists() else 'MISSING'}")"""

C_ENV = r"""# [env]
def load_env_file(path="API.env"):
    p = Path(path); loaded = []
    if not p.exists(): return loaded
    for raw in p.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k: os.environ[k] = v; loaded.append(k)
    return loaded

print("loaded from API.env:", load_env_file() or "nothing")
assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY missing -- put it in API.env"
print(f"OPENAI_API_KEY: present ({len(os.environ['OPENAI_API_KEY'])} chars)")"""

C_CLIENT = r"""# [client]  -- same client as parser_v4.ipynb cell 4
import time, random
from openai import OpenAI

class LLMClient:
    def __init__(self, model=GEN_MODEL, effort=EFFORT, max_retries=6):
        self.c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.model, self.effort, self.r = model, effort, max_retries
        self.usage = []

    def _call(self, system, user, json_mode, max_tokens, effort):
        kw = dict(model=self.model, instructions=system, input=user,
                  reasoning={"effort": effort or self.effort},
                  max_output_tokens=max_tokens)
        if json_mode:
            kw["text"] = {"format": {"type": "json_object"}}
        wait = 2.0
        for a in range(self.r):
            try:
                r = self.c.responses.create(**kw)
                if getattr(r, "status", None) == "incomplete":
                    why = getattr(getattr(r, "incomplete_details", None), "reason", "?")
                    print(f"    [llm warn] incomplete ({why}) at max_output_tokens={max_tokens}")
                u = r.usage
                self.usage.append({"in": u.input_tokens, "out": u.output_tokens,
                                   "reasoning": u.output_tokens_details.reasoning_tokens,
                                   "cached_in": getattr(u.input_tokens_details, "cached_tokens", 0)})
                return r.output_text
            except Exception as e:
                if a == self.r - 1: raise
                time.sleep(wait + random.uniform(0, 1)); wait *= 2

    def complete(self, system, user, max_tokens=4096, effort=None):
        return self._call(system, user, True, max_tokens, effort)

    def cost(self, price_in=0.25, price_out=2.00, price_cached=0.025):
        i = sum(u["in"] - u["cached_in"] for u in self.usage)
        c = sum(u["cached_in"] for u in self.usage)
        o = sum(u["out"] for u in self.usage)
        return {"calls": len(self.usage), "in": i, "cached_in": c, "out": o,
                "usd": round((i*price_in + c*price_cached + o*price_out)/1e6, 4)}

client = LLMClient()
print("client ready:", GEN_MODEL, "| effort", EFFORT)"""

C_PROMPTS = r"""# [prompts]  -- the step prompts, assembled at run time from PROMPT_DIR and SITES v2
from prompts_parse_v3 import BANNED_IN_OUTPUT, EDGE_TYPES

def sha12(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]

def read_prompt(name):
    return (PROMPT_DIR / name).read_text(encoding="utf-8")

def fill(text, **slots):
    for k, v in slots.items():
        n = text.count(f"<<{k}>>")
        assert n == 1, f"slot <<{k}>> found {n} times"
        text = text.replace(f"<<{k}>>", v)
    return text

SITES_MD  = SITES_FILE.read_text(encoding="utf-8").strip()
V2_SITES  = re.findall(r"^- ([A-Z_]+):", SITES_MD, re.M)
SITES     = list(V2_SITES)     # the taxonomy; the rulebook cell adds the rulebook's added_sites
SITES_SHA = sha12(SITES_MD)
ELEMENT_LIST_RULE = ("Only a name that appears in the list of elements given to you gets a site. "
                     "Every other name gets none: literals, named constants, aggregates, generics, "
                     "loop parameters, enumeration values, and the names of functions and types.")

# corpus identifiers: every reference-set name and every closed-set name, whole and split at dots
_names = set()
for d in json.load(open(GT_FILE, encoding="utf-8"))["modules"].values():
    for a in d["assets"]:
        _names.add(a["element"].strip()); _names.update(a["element"].strip().split("."))
for f in REF_DIR.glob("*.json"):
    _d = json.load(open(f, encoding="utf-8"))
    for e in _d.get("ports", []) + _d.get("signals", []):
        _names.add(e["name"]); _names.update(e["name"].split("."))

def _blank_placeholders(s):
    # a <placeholder> such as <condition> is not an identifier; blank innermost outwards
    while True:
        nxt = re.sub(r"<[A-Za-z_][\w ]*>", " ", s)
        if nxt == s:
            return s
        s = nxt

def audit_prompt(text, code=()):
    # The standing prompt rules, as a list of problems: no corpus identifier, no banned word,
    # no numeric emission hint, no edge type name, no SITE-like name that v2 does not define.
    t = _blank_placeholders(text)
    code_text = " ".join(re.findall(r"`[^`\n]+`", t)) + " " + " ".join(
        _blank_placeholders(c) for c in code)
    out = []
    leaks = sorted(n for n in _names if len(n) > 3 and (
        ("_" in n and re.search(rf"(?<![\w.]){re.escape(n)}(?![\w])", t)) or
        ("_" not in n and re.search(rf"(?<![\w.]){re.escape(n)}(?![\w])", code_text))))
    if leaks:
        out.append(f"corpus identifier(s): {leaks}")
    low = text.lower()
    banned = [w.strip() for w in BANNED_IN_OUTPUT if w in low]
    if banned:
        out.append(f"banned word(s): {banned}")
    hints = [h for h in ("%", "at most 20", "no more than 20", "at least half") if h in text]
    if hints:
        out.append(f"numeric emission hint(s): {hints}")
    edges = [e for e in EDGE_TYPES if re.search(rf"\b{e}\b", text)]
    if edges:
        out.append(f"edge type name(s): {edges}")
    odd = sorted(set(re.findall(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b", text))
                 - set(SITES) - {"SITE_RULES", "CONFLICT_RULES"})
    if odd:
        out.append(f"SITE-like name(s) not in v2: {odd}")
    return out

KNOWLEDGE_SYSTEM = fill(read_prompt("1_knowledge.md"), SITES_DEFINITIONS=SITES_MD)

def annotate_systems(rulebook_text):
    # classify and validate follow the rulebook alone; v2 only feeds step 1 and the basis-quote check
    rules = fill(read_prompt("annotate_rules.md"), RULEBOOK=rulebook_text)
    return {"classify": fill(read_prompt("3_classify.md"), ANNOTATE_RULES=rules),
            "validate": fill(read_prompt("4_validate.md"), ANNOTATE_RULES=rules)}

# classify and validate get their sha once the rulebook is loaded (rulebook cell)
SYSTEM     = {"knowledge": KNOWLEDGE_SYSTEM, "classify": None, "validate": None}
PROMPT_SHA = {k: (sha12(v) if v else None) for k, v in SYSTEM.items()}
# step 2 is code: its answers go to a folder named after this version; change it whenever the inventory
# or structure code in the checks cell changes
EXTRACT_CODE_VERSION = "code-inventory-v1"
PROMPT_SHA["extract"] = sha12(EXTRACT_CODE_VERSION)

_bad = {}
for label, text in [("knowledge", KNOWLEDGE_SYSTEM), *annotate_systems("(rulebook goes here)").items()]:
    p = audit_prompt(text)
    if label != "knowledge" and ELEMENT_LIST_RULE not in re.sub(r"\s+", " ", text):
        p.append("the element-list rule is missing")
    if re.findall(r"<<[A-Z_]+>>", text):
        p.append(f"unfilled slot(s): {re.findall(r'<<[A-Z_]+>>', text)}")
    if p:
        _bad[label] = p
    kind = "template" if label in ("classify", "validate") else sha12(text)
    print(f"  {label:9s} {kind:12s} {len(text):>7,} chars   {'OK' if not p else p}")
assert not _bad, f"prompt audit failed: {_bad}"
print(f"{len(V2_SITES)} SITEs from v2 ({SITES_SHA}):", ", ".join(V2_SITES))"""

C_INPUTS = r"""# [inputs]  -- one entity's source with ORIGINAL line numbers, its closed set, the messages
import rtl_parse
from stage_a import _mask_comments

@lru_cache(maxsize=None)
def numbered_entity_source(path, ename):
    # Comments are blanked, not deleted, so every line keeps its original number -- the tables
    # then line up with the hand-made profiles. Blank lines are left out to save tokens.
    raw    = Path(path).read_text(encoding="utf-8", errors="ignore")
    masked = _mask_comments(raw, vhdl=True)
    lines  = masked.splitlines()
    spans  = []
    em = next((m for m in rtl_parse._ENTITY.finditer(masked)
               if m.group(1).lower() == ename.lower()), None)
    if em:
        spans.append((masked.count("\n", 0, em.start()), masked.count("\n", 0, em.end())))
    am = rtl_parse._arch_re(ename).search(masked)
    if am:
        nxt = rtl_parse._UNIT_START.search(masked, am.end())
        end = masked.count("\n", 0, nxt.start()) - 1 if nxt else len(lines) - 1
        spans.append((masked.count("\n", 0, am.start()), end))
    out = []
    for a, b in spans:
        for i in range(a, min(b, len(lines) - 1) + 1):
            if lines[i].strip():
                out.append(f"{i + 1:>5} | {lines[i].rstrip()}")
        out.append("")
    return "\n".join(out).rstrip()

def load_elements(module):
    d = json.load(open(ELEM_DIR / f"{module}.json", encoding="utf-8"))
    return [(e["entity"], e["ports"] + e["signals"]) for e in d["entities"]]

def build_jobs(modules):
    jobs = []
    for m in modules:
        for ent, elems in load_elements(m):
            src = numbered_entity_source(RTL_DIR / f"{m}.vhd", ent)
            for b in range(0, len(elems), BATCH):
                jobs.append({"module": m, "entity": ent, "batch": b // BATCH,
                             "elems": elems[b:b + BATCH], "src": src})
    return jobs

def user_message(step, job, up):
    # source first: every batch of an entity shares the long prefix, so it caches
    msg = (f"ENTITY: {job['entity']}   (module {job['module']})\n\n"
           f"SOURCE of this entity. Comments removed; each line starts with its line number:\n\n"
           f"{job['src']}\n\n"
           f"CLOSED SET, in this order:\n{json.dumps(job['elems'], indent=1)}\n")
    if step == "extract":
        return msg                                  # the inventory is made by code; this only fixes its input
    msg += f"\nOCCURRENCE INVENTORY, made by a program:\n{json.dumps(up['extract'], indent=1)}\n"
    if step == "validate":
        msg += f"\nOCCURRENCE PROFILES to check:\n{json.dumps(up['classify'], indent=1)}\n"
        msg += code_checklist(job, up["classify"])
    # the API refuses JSON mode unless the input itself says "json"
    return msg + "\nReturn one JSON object in the format given in your instructions.\n"

def out_path(step, job):
    sha = PROMPT_SHA.get(step)
    if not sha:
        return None
    return OUT_DIR / step / sha / f"{job['module']}__{job['entity']}__b{job['batch']:02d}.json"

for s, mods in MODULES.items():
    js = build_jobs(mods)
    print(f"{s}: {len(js)} batch(es) -> {len(js) * 2} model calls (classify, validate); extract is code")
    for j in js:
        print(f"   {j['module']}/{j['entity']} batch {j['batch']}: "
              f"{len(j['elems'])} elements, {j['src'].count(chr(10)) + 1} source lines")"""

C_CHECKS = r"""# [checks]  -- deterministic checks that use no model, and reading the saved answers
def source_lines(src):
    out = {}
    for l in src.splitlines():
        m = re.match(r"\s*(\d+) \| ?(.*)$", l)
        if m:
            out[int(m.group(1))] = m.group(2)
    return out

def _name_re(name):
    parts = [re.escape(p) for p in name.split(".")]
    return re.compile(r"(?<![\w.])" + r"\s*\.\s*".join(parts) + r"(?!\w)", re.I)

def written_lines(lines, name):
    # every line where the name is written as a whole name; a base also matches <base>.<field>
    rx = _name_re(name)
    return {n for n, t in lines.items() if rx.search(t)}

def occurrence_lines(lines, name):
    # Lines holding an occurrence by the extract prompt's rules: a name left of => does not count,
    # nor one inside a component declaration or a record type declaration; a field also occurs
    # on the line that declares its base.
    skip, until = set(), None
    for n in sorted(lines):
        t = lines[n]
        if until is None:
            if re.match(r"\s*component\s+\w+", t, re.I):
                until = r"\bend\s+component\b"
            elif re.search(r"\bis\s+record\b", t, re.I):
                until = r"\bend\s+record\b"
        if until:
            skip.add(n)
            if re.search(until, t, re.I):
                until = None
    rx, hits = _name_re(name), set()
    for n, t in lines.items():
        if n not in skip and any(not re.match(r"\s*=>", t[m.end():]) for m in rx.finditer(t)):
            hits.add(n)
    if "." in name:
        base = occurrence_lines(lines, name.rsplit(".", 1)[0])
        if base:
            hits.add(min(base))
    return hits

def _selftest_lines():
    fails = []
    # 1. hand-read lines: boot_rom, every element's occurrence lines equal the expected file's lines
    exp = json.load(open(EXPECTED_FILE, encoding="utf-8"))
    L = source_lines(numbered_entity_source(RTL_DIR / f"{exp['module']}.vhd", exp["entity"]))
    for e in exp["elements"]:
        want, got = {r["line"] for r in e["rows"]}, occurrence_lines(L, e["name"])
        if got != want:
            fails.append((e["name"], sorted(want), sorted(got)))
    # 2. each exclusion, on hand-written lines
    toy = {10: "  component other_unit is", 11: "    port (sig_a : in std_ulogic);",
           12: "  end component;", 13: "  type rec_t is record", 14: "    sig_a : std_ulogic;",
           15: "  end record;", 16: "  signal sig_a, sig_ab : std_ulogic;", 17: "  signal r : rec_t;",
           18: "  u0: other_unit port map (sig_a => sig_ab);",
           19: "  u1: other_unit port map (sig_a => sig_a);", 20: "  sig_ab <= r.sig_a and SIG_A;"}
    for n, want in {"sig_a": {16, 19, 20}, "sig_ab": {16, 18, 20},
                    "r": {17, 20}, "r.sig_a": {17, 20}}.items():
        got = occurrence_lines(toy, n)
        if got != want:
            fails.append((n, sorted(want), sorted(got)))
    return fails

_st = _selftest_lines()
SELFTEST_OK = not _st
print("line-check self-test:", "PASS" if SELFTEST_OK else f"FAIL {_st}")

# Words that say what a signal or a branch is for. annotate_rules.md section G forbids them in a Role.
# The list is not exhaustive, so a count is a lower bound.
DESIGN_WORDS = ("reset", "clock", "clocked", "clocking", "enable", "enabled", "register", "registered",
                "flip-flop", "flop", "latch", "latched", "memory", "rom", "ram", "fifo", "combinational",
                "synchronous", "asynchronous", "synchronizer", "state machine", "fsm", "counter", "strobe",
                "handshake", "interrupt", "initialization", "initialisation")

def design_words(ctx, names):
    # Quoted source text is ignored, and so is any word that is an element name of the entity:
    # a signal named enable, written as a name, is not a design word.
    t = re.sub(r"'[^']*'|\"[^\"]*\"|`[^`]*`", " ", str(ctx))
    t = re.sub(r"\b\w+\s*:\s*(?=(process|block|entity|for|if)\b)", " ", t, flags=re.I)   # a label is a name
    skip = {p.lower() for n in names for p in n.split(".")}
    return [w for w in DESIGN_WORDS
            if w not in skip and re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", t, re.I)]

def _selftest_design_words():
    cases = [("process, lines 55-62; branch opened by IF_COND at lines 57-58 (the reset branch).", [], ["reset"]),
             ("in the if condition '(rst = '1')', IF_COND", [], []),
             ("the element enable is the target on the left of <=", ["enable"], []),
             ("a clocked process, lines 1-9", [], ["clocked"]),
             ("process block, lines 45-50, in the sensitivity list", [], []),
             ("reset_n is joined by an operator", [], []),
             ("the value goes to a flip-flop", [], ["flip-flop"]),
             ("statement 'x <= fifo_rdata;' copied", [], []),
             ("process, lines 465-472, header synchronizer: process(rstn_i, clk_i)", [], []),
             ("Base of a field selection reaching field buf_req in initialization.", [], ["initialization"])]
    return [(c, w, design_words(c, n)) for c, n, w in cases if design_words(c, n) != w]

_sw = _selftest_design_words()
WORDS_SELFTEST_OK = not _sw
print("design-word self-test:", "PASS" if WORDS_SELFTEST_OK else f"FAIL {_sw}")

def occurrence_counts(lines, name):
    # occurrences per line: every match of the name, with the exclusions of occurrence_lines;
    # a field on its base's declaration line counts once
    rx, out = _name_re(name), Counter()
    for n in occurrence_lines(lines, name):
        k = sum(1 for m in rx.finditer(lines[n]) if not re.match(r"\s*=>", lines[n][m.end():]))
        out[n] = max(k, 1)
    return out

def _selftest_counts():
    fails = []
    exp = json.load(open(EXPECTED_FILE, encoding="utf-8"))
    L = source_lines(numbered_entity_source(RTL_DIR / f"{exp['module']}.vhd", exp["entity"]))
    total = sum(sum(occurrence_counts(L, e["name"]).values()) for e in exp["elements"])
    if total != 45:
        fails.append(("boot_rom occurrences, 45 read by hand", total))
    if dict(occurrence_counts(L, "bus_req_i")) != {23: 1, 48: 1, 60: 2}:
        fails.append(("boot_rom bus_req_i", dict(occurrence_counts(L, "bus_req_i"))))
    toy = {1: "  signal s : t;", 2: "  u: c port map (s => s);", 3: "  x <= s and s;", 4: "  y <= r.s;"}
    if dict(occurrence_counts(toy, "s")) != {1: 1, 2: 1, 3: 2}:
        fails.append(("toy", dict(occurrence_counts(toy, "s"))))
    return fails

def paren_kinds(line, name):
    # For each occurrence of the name on the line: "index" when parentheses holding one position follow it,
    # "slice" when they hold a range (downto / to outside any inner parentheses), None otherwise.
    out = []
    for m in _name_re(name).finditer(line):
        rest = line[m.end():]
        if re.match(r"\s*=>", rest):
            continue
        if not re.match(r"\s*\(", rest):
            out.append(None)
            continue
        i = rest.index("(") + 1
        j, depth = i, 1
        while j < len(rest) and depth:
            depth += {"(": 1, ")": -1}.get(rest[j], 0)
            j += 1
        flat = rest[i:j - 1]
        while re.search(r"\([^()]*\)", flat):
            flat = re.sub(r"\([^()]*\)", " ", flat)
        out.append("slice" if re.search(r"\b(downto|to)\b", flat, re.I) else "index")
    return out

def addon_gaps(lines, name, rows):
    # lines where the INDEXED_NAME / PART_SELECT tags differ in number from the indexed / sliced occurrences
    gaps = []
    for ln in sorted(set(occurrence_counts(lines, name)) | {r.get("Occurrence Lines") for r in rows}):
        if ln not in lines:
            continue
        k = Counter(paren_kinds(lines[ln], name))
        tags = Counter(x for r in rows if r.get("Occurrence Lines") == ln for x in (r.get("SITE Tagged") or []))
        if k["index"] != tags["INDEXED_NAME"] or k["slice"] != tags["PART_SELECT"]:
            gaps.append((ln, k["index"], tags["INDEXED_NAME"], k["slice"], tags["PART_SELECT"]))
    return gaps

def _selftest_paren_kinds():
    fails = []
    for line, name, want in [("q <= a(3 downto 0) & b(1);", "a", ["slice"]), ("q <= a(3 downto 0) & b(1);", "b", ["index"]),
                             ("x(i) <= y((n-1) downto 0);", "y", ["slice"]), ("x(i) <= y((n-1) downto 0);", "x", ["index"]),
                             ("z <= m(to_integer(unsigned(p)));", "m", ["index"]), ("z <= m(to_integer(unsigned(p)));", "p", [None]),
                             ("z <= r.f(1);", "r.f", ["index"]), ("z <= r.f(1);", "r", [None]),
                             ("u: c port map (s => s(2));", "s", ["index"]), ("w <= v'left;", "v", [None])]:
        if paren_kinds(line, name) != want:
            fails.append((line, name, want, paren_kinds(line, name)))
    exp = json.load(open(EXPECTED_FILE, encoding="utf-8"))
    L = source_lines(numbered_entity_source(RTL_DIR / f"{exp['module']}.vhd", exp["entity"]))
    got = {(e["name"], ln): Counter(paren_kinds(L[ln], e["name"]))
           for e in exp["elements"] for ln in occurrence_counts(L, e["name"])}
    found = {k: dict(v) for k, v in got.items() if v["index"] or v["slice"]}
    if found != {("bus_req_i.addr", 48): {"slice": 1}}:      # read by hand: the only index or slice on an element
        fails.append(("boot_rom", found))
    return fails

_sc = _selftest_counts() + _selftest_paren_kinds()
SELFTEST_OK = SELFTEST_OK and not _sc
print("occurrence-count self-test:", "PASS" if not _sc else f"FAIL {_sc}")

# ---- enclosing structures (annotate_rules.md section D), read off the source by code
STRUCTURE_KINDS = ("port clause", "declarative part", "architecture body", "generate", "process", "loop", "if",
         "branch", "case", "alternative", "association list")


class StructureError(Exception):
    pass


def _blank_strings(t):
    return re.sub(r'"[^"\n]*"', lambda m: '"' + " " * (len(m.group(0)) - 2) + '"', t)


def find_structures(L):
    nums = sorted(L)
    T = {n: _blank_strings(L[n]) for n in nums}
    prev = {nums[i]: nums[i - 1] for i in range(1, len(nums))}
    out = []

    def add(kind, a, b, opened=None):
        out.append({"kind": kind, "lines": [a, b], "opened by": opened})

    # ---- parenthesised lists: entity/component port clauses and association lists
    flat, pos = "", []                               # text with a line map, to match parentheses
    for n in nums:
        pos.append((len(flat), n))
        flat += T[n] + "\n"

    def line_at(i):
        lo, hi = 0, len(pos) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if pos[mid][0] <= i:
                lo = mid
            else:
                hi = mid - 1
        return pos[lo][1]

    def close_paren(i):
        d = 1
        while i < len(flat) and d:
            d += {"(": 1, ")": -1}.get(flat[i], 0)
            i += 1
        if d:
            raise StructureError(f"unclosed parenthesis from line {line_at(i - 1)}")
        return line_at(i - 1)

    comp_spans = []
    for m in re.finditer(r"^[ \t]*component\s+\w+.*?^[ \t]*end\s+component\b", flat, re.I | re.M | re.S):
        comp_spans.append((line_at(m.start()), line_at(m.end() - 1)))
    in_comp = lambda n: any(a <= n <= b for a, b in comp_spans)
    for m in re.finditer(r"\b(port|generic)\s+map\s*\(", flat, re.I):
        add("association list", line_at(m.start()), close_paren(m.end()))
    for m in re.finditer(r"\bport\s*\(", flat, re.I):
        n = line_at(m.start())
        if re.search(r"\bmap\s*$", flat[max(0, m.start() - 10):m.start()], re.I) or in_comp(n):
            continue
        add("port clause", n, close_paren(m.end()))

    # ---- architectures: declarative part, body, and the statements inside the body
    heads = [n for n in nums if re.match(r"\s*architecture\s+\w+\s+of\s+\w+\s+is\b", T[n], re.I)]
    for h in heads:
        name = re.match(r"\s*architecture\s+(\w+)", T[h], re.I).group(1).lower()
        after = [n for n in nums if n > h]
        begins = [n for n in after if re.match(r"\s*begin\b", T[n], re.I)]
        if not begins:
            raise StructureError(f"architecture at {h}: no begin")
        b = begins[0]
        if any(re.search(r"\b(function|procedure)\b[^;]*\bis\s*$", T[n], re.I) for n in after if n < b):
            raise StructureError(f"architecture at {h}: a subprogram body in the declarative part is not handled")
        ends = [n for n in after if n > b and re.match(rf"\s*end\s*(architecture\s*)?({name}\s*)?;", T[n], re.I)]
        if not ends:
            raise StructureError(f"architecture at {h}: no end")
        e = ends[-1]
        decl = [n for n in after if n < b]
        if decl:
            add("declarative part", decl[0], decl[-1])
        add("architecture body", b, e)
        _structure_body(T, [n for n in nums if b < n < e], prev, add)
    return out


def _structure_body(T, lines, prev, add):
    stack = []                                         # [kind, start, extra]

    def cond_kind(n):
        text, k = "", n
        idx = lines.index(n)
        for k in lines[idx:idx + 6]:
            text += " " + T[k]
            if re.search(r"\bthen\b", T[k], re.I):
                break
        return "EDGE_CHECK" if re.search(r"\b(rising_edge|falling_edge)\s*\(", text, re.I) else "IF_COND"

    def is_generate_if(n, col):
        text = T[n][col:]
        idx = lines.index(n)
        for k in lines[idx:idx + 6]:
            if k != n:
                text += " " + T[k]
            mt, mg = re.search(r"\bthen\b", text, re.I), re.search(r"\bgenerate\b", text, re.I)
            if mt or mg:
                return bool(mg) and (not mt or mg.start() < mt.start())
        return False

    def close(kind, n):
        if not stack or stack[-1][0] != kind:
            raise StructureError(f"line {n}: end {kind} does not match the open {stack[-1][0] if stack else 'nothing'}")
        k, a, extra = stack.pop()
        add(kind, a, n)
        if kind in ("if", "case") and extra:
            starts = extra + [(n, None)]
            for i in range(len(extra)):
                add("branch" if kind == "if" else "alternative", extra[i][0], prev[starts[i + 1][0]], extra[i][1])

    tok = re.compile(r"\bend\s+(process|if|case|loop|generate)\b|\belsif\b|\belse\b|\bif\b|\bcase\b|\bloop\b|"
                     r"\bgenerate\b|\bprocess\b|^\s*when\b", re.I)
    in_when = False                                    # inside a conditional or selected assignment
    for n in lines:
        t = T[n]
        if re.search(r"\bwhen\b", t, re.I) and not re.match(r"\s*(when\b[^;]*=>|exit\b|next\b)", t, re.I):
            in_when = True
        for m in tok.finditer(t):
            w = re.sub(r"\s+", " ", m.group(0).strip().lower())
            if w.startswith("end "):
                close(w.split()[1], n)
            elif w == "process":
                if re.match(r"\s*(\w+\s*:\s*)?(postponed\s+)?process\b", t, re.I):
                    stack.append(["process", n, None])
            elif w == "if":
                if is_generate_if(n, m.start()):
                    continue                           # counted at its generate keyword
                stack.append(["if", n, [(n, cond_kind(n))]])
            elif w == "elsif":
                if not stack or stack[-1][0] != "if":
                    raise StructureError(f"line {n}: elsif outside an if")
                stack[-1][2].append((n, cond_kind(n)))
            elif w == "else":
                if in_when:
                    continue                           # the else of a when ... else, on any of its lines
                if not stack or stack[-1][0] != "if":
                    raise StructureError(f"line {n}: else outside an if")
                stack[-1][2].append((n, "else"))
            elif w == "case":
                stack.append(["case", n, []])
            elif w == "when":
                if "=>" in t and stack and stack[-1][0] == "case":
                    choice = re.sub(r"\s+", " ", t.split("=>", 1)[0].strip()[4:].strip())
                    stack[-1][2].append((n, choice))
            elif w == "loop":
                stack.append(["loop", n, None])
            elif w == "generate":
                start = n
                if n in prev and re.match(r"\s*\w+\s*:\s*$", T[prev[n]]):
                    start = prev[n]                    # the label stands alone on the line above
                stack.append(["generate", start, None])
        if ";" in t:
            in_when = False
    if stack:
        raise StructureError(f"left open at the end of the body: {[(k, a) for k, a, _ in stack]}")


def structure_chain(S, line):
    inside = [s for s in S if s["lines"][0] <= line <= s["lines"][1]]
    return sorted(inside, key=lambda s: (s["lines"][0], -s["lines"][1], STRUCTURE_KINDS.index(s["kind"]) if s["kind"] in ("if", "branch", "case", "alternative") else 0))


def render_structure(ch):
    return "; ".join(f"{s['kind']} {s['lines'][0]}-{s['lines'][1]}" + (f" ({s['opened by']})" if s["opened by"] else "")
                     for s in ch)


@lru_cache(maxsize=None)
def structures_of(src):
    return find_structures(source_lines(src))

def _selftest_structures():
    fails = []
    def ch(mod, ent, line, tail=True):
        L = numbered_entity_source(RTL_DIR / f"{mod}.vhd", ent)
        out = [(s["kind"], s["lines"][0], s["lines"][1], s["opened by"]) for s in structure_chain(structures_of(L), line)]
        return out[1:] if tail else out
    # spans read by hand from the source
    cases = [
        (("neorv32_boot_rom", "neorv32_boot_rom", 21, False), [("port clause", 20, 25, None)]),
        (("neorv32_boot_rom", "neorv32_boot_rom", 38, False), [("declarative part", 31, 39, None)]),
        (("neorv32_boot_rom", "neorv32_boot_rom", 60, False), [("architecture body", 41, 69, None), ("process", 55, 62, None),
                                                               ("if", 57, 61, None), ("branch", 59, 60, "EDGE_CHECK")]),
        (("neorv32_boot_rom", "neorv32_boot_rom", 64, False), [("architecture body", 41, 69, None)]),
        (("neorv32_trng", "neorv32_trng", 109), [("process", 90, 123, None), ("if", 92, 122, None), ("branch", 96, 121, "EDGE_CHECK"),
                                                 ("if", 103, 121, None), ("branch", 103, 120, "IF_COND"), ("if", 104, 120, None),
                                                 ("branch", 107, 119, "else"), ("if", 108, 119, None), ("branch", 108, 112, "IF_COND")]),
        (("neorv32_trng", "neoTRNG", 304), [("generate", 294, 308, None), ("association list", 301, 307, None)]),
        (("neorv32_trng", "neoTRNG", 320), [("process", 315, 323, None), ("loop", 319, 321, None)]),
        (("neorv32_trng", "neoTRNG_cell", 449), [("generate", 431, 454, None), ("generate", 444, 452, None), ("process", 446, 451, None),
                                                 ("if", 448, 450, None), ("branch", 448, 449, "EDGE_CHECK")]),
        (("neorv32_trng", "neoTRNG_cell", 435), [("generate", 431, 454, None)]),
        (("neorv32_cache", "neorv32_cache", 173), [("process", 133, 268, None), ("case", 164, 267, None), ("alternative", 166, 176, "S_IDLE"),
                                                   ("if", 168, 176, None), ("branch", 170, 175, "IF_COND"), ("if", 171, 174, None),
                                                   ("branch", 171, 173, "IF_COND")]),
        (("neorv32_cache", "neorv32_cache", 284), [("association list", 278, 292, None)]),
        (("neorv32_cache", "neorv32_cache_memory", 381), [("process", 374, 389, None), ("if", 376, 388, None), ("branch", 379, 387, "EDGE_CHECK"),
                                                          ("if", 380, 386, None), ("branch", 380, 381, "IF_COND")]),
    ]
    for args, want in cases:
        try:
            got = ch(*args)
        except StructureError as e:
            got = str(e)
        if got != want:
            fails.append((args, want, got))
    toy = {1: "architecture a of e is", 2: "begin", 3: "  v <= '1' when (a = '1') and", 4: "         (b = '0') else '0';",
           5: "  p: process (c)", 6: "  begin", 7: '    report "if case end process" severity note;', 8: "    if s = '1' then",
           9: "      x <= y when (a = '1') and", 10: "           (b = '1') else", 11: "           z;", 12: "    else",
           13: "      x <= z;", 14: "    end if;", 15: "  end process p;", 16: "end a;"}
    got = [(s["kind"], *s["lines"], s["opened by"]) for s in structure_chain(find_structures(toy), 13)]
    if got != [("architecture body", 2, 16, None), ("process", 5, 15, None), ("if", 8, 14, None), ("branch", 12, 13, "else")]:
        fails.append(("toy: strings, multi-line when-else", got))
    return fails

def _written(t, m):
    # the name as written at this occurrence, with the field, attribute or parentheses right after it
    out, rest = t[m.start():m.end()], t[m.end():]
    f = re.match(r"\s*(\.\s*\w+|'\s*\w+)", rest)
    if f:
        out += re.sub(r"\s+", "", f.group(1))
    elif re.match(r"\s*\(", rest):
        j, depth = rest.index("(") + 1, 1
        while j < len(rest) and depth:
            depth += {"(": 1, ")": -1}.get(rest[j], 0)
            j += 1
        out += re.sub(r"\s+", " ", rest[rest.index("("):j])[:60]
    return out

def occurrence_matches(lines, name):
    # (line, column, name as written) for every occurrence, with the exclusions of occurrence_lines
    rx, out = _name_re(name), []
    for n in sorted(occurrence_lines(lines, name)):
        t = lines[n]
        ms = [m for m in rx.finditer(t) if not re.match(r"\s*=>", t[m.end():])]
        if not ms:                                  # a field, on the line that declares its base
            out.append((n, -1, f"{name.rsplit('.', 1)[0]} (declaration of the base)"))
        for m in ms:
            out.append((n, m.start(), _written(t, m)))
    return out

def code_inventory(job):
    L = source_lines(job["src"])
    inv = {}
    for e in job["elems"]:
        inv[e["name"]] = [{"Occurrence ID": k + 1, "Occurrence Lines": n, "Name As Written": w, "Line Text": L[n].strip()}
                          for k, (n, col, w) in enumerate(occurrence_matches(L, e["name"]))]
    return inv

def _selftest_inventory():
    fails = []
    exp = json.load(open(EXPECTED_FILE, encoding="utf-8"))
    job = {"src": numbered_entity_source(RTL_DIR / f"{exp['module']}.vhd", exp["entity"]),
           "elems": [{"name": e["name"]} for e in exp["elements"]]}
    inv = code_inventory(job)
    if sum(len(v) for v in inv.values()) != 45:
        fails.append(("boot_rom inventory size, 45 read by hand", sum(len(v) for v in inv.values())))
    w60 = [r["Name As Written"] for r in inv["bus_req_i"] if r["Occurrence Lines"] == 60]
    if w60 != ["bus_req_i.stb", "bus_req_i.rw"]:
        fails.append(("bus_req_i at 60", w60))
    if [r["Name As Written"] for r in inv["bus_req_i.addr"]][0] != "bus_req_i (declaration of the base)":
        fails.append(("bus_req_i.addr declaration", inv["bus_req_i.addr"][0]))
    return fails

def _valid_id(x):
    return isinstance(x, int) and not isinstance(x, bool)

def _line_key(x):
    return (not isinstance(x, int), x if isinstance(x, int) else 0)

def id_line_issues(inv, rows):
    # One element: its inventory rows and its profile entries, compared line by line, so an answer that renumbers its
    # entries does not make lines that have their entries look empty. Returns (lines, added, bad):
    #   lines: (line, occurrences, entries, uncarried [(ID, name as written)], repeated [ID], foreign [(ID, line the
    #          inventory gives that ID, or None)]) for every line where the entries and the inventory disagree
    #   added: (ID, line, highest inventory ID) for an entry whose ID is above the inventory's and unique in the
    #          profile: an occurrence the model added, as the classify prompt allows; not counted on its line
    #   bad:   (ID as given, line) for an ID that is not a whole number
    line_of = {r["Occurrence ID"]: r["Occurrence Lines"] for r in inv}
    top = max(line_of, default=0)
    occ_at = {}
    for r in inv:
        occ_at.setdefault(r["Occurrence Lines"], []).append(r)
    id_count = Counter(r.get("Occurrence ID") for r in rows if _valid_id(r.get("Occurrence ID")))
    carried, foreign, entries, added, bad = {}, {}, Counter(), [], []
    for r in rows:
        oid, ln = r.get("Occurrence ID"), r.get("Occurrence Lines")
        if not _valid_id(oid):
            bad.append((oid, ln))
            entries[ln] += 1
        elif oid in line_of:
            entries[ln] += 1
            if line_of[oid] == ln:
                carried.setdefault(ln, Counter())[oid] += 1
            else:
                foreign.setdefault(ln, []).append((oid, line_of[oid]))
        elif oid > top and id_count[oid] == 1:
            added.append((oid, ln, top))
        else:
            entries[ln] += 1
            foreign.setdefault(ln, []).append((oid, None))
    lines = []
    for ln in sorted(set(occ_at) | set(foreign) | set(carried), key=_line_key):
        occ, c = occ_at.get(ln, []), carried.get(ln, Counter())
        uncarried = [(o["Occurrence ID"], o["Name As Written"]) for o in occ if c[o["Occurrence ID"]] == 0]
        repeated = sorted(i for i, k in c.items() if k > 1)
        fo = foreign.get(ln, [])
        if entries[ln] < len(occ) or uncarried or repeated or fo:
            lines.append((ln, len(occ), entries[ln], uncarried, repeated, fo))
    return lines, added, bad

def field_use_off_field(inv, rows, name):
    # FIELD_USE on an occurrence not written <element>.<field>; FIELD_USE belongs only to a record base written with
    # one of its fields. Returns (line, [IDs named], entries wrong, exact). exact: the entries carry their line's
    # inventory ID, so each is checked against its own occurrence. Otherwise the line's FIELD_USE entries without such
    # an ID are counted against the line's field-written occurrences that no checked entry took; the item names them
    # all, since the program cannot tell which is wrong.
    by_id = {r["Occurrence ID"]: r for r in inv}
    dotted_at = Counter(r["Occurrence Lines"] for r in inv if r["Name As Written"].startswith(name + "."))
    exact, loose, taken = {}, {}, Counter()
    for r in rows:
        if "FIELD_USE" not in (r.get("SITE Tagged") or []):
            continue
        oid, ln = r.get("Occurrence ID"), r.get("Occurrence Lines")
        row = by_id.get(oid) if _valid_id(oid) else None
        if row is not None and row["Occurrence Lines"] == ln:
            if row["Name As Written"].startswith(name + "."):
                taken[ln] += 1
            else:
                exact.setdefault(ln, []).append(oid)
        else:
            loose.setdefault(ln, []).append(oid)
    out = [(ln, ids, len(ids), True) for ln, ids in exact.items()]
    for ln, ids in loose.items():
        free = max(dotted_at[ln] - taken[ln], 0)
        if len(ids) > free:
            out.append((ln, ids, len(ids) - free, False))
    return sorted(out, key=lambda x: (_line_key(x[0]), not x[3]))

_NOT_TARGET = {"if", "elsif", "while", "case", "when", "assert", "report", "return", "wait", "for", "not", "and",
               "or", "until", "process", "port", "generic", "map", "loop", "else", "then", "begin", "end", "variable",
               "signal", "constant", "exit", "next", "null", "with", "select", "generate", "block", "type", "subtype",
               "function", "procedure"}

def _assignment_parts(t):
    # For a line that starts a signal assignment <target> <= ..., where the target is a name with zero or more
    # parenthesised groups: (column spans inside the target's parentheses, column where the right-hand side starts).
    # None for any other line.
    t = re.sub(r"--.*", "", t)
    m = re.match(r"\s*(?:\w+\s*:\s*)?([A-Za-z_][\w.]*)\s*", t)
    if not m or m.group(1).lower() in _NOT_TARGET:
        return None
    j, spans = m.end(), []
    while j < len(t) and t[j] == "(":
        depth, k = 1, j + 1
        while k < len(t) and depth:
            depth += {"(": 1, ")": -1}.get(t[k], 0)
            k += 1
        if depth:
            return None
        spans.append((j + 1, k - 1))
        j = k
        while j < len(t) and t[j] in " \t":
            j += 1
    if t[j:j + 2] != "<=":
        return None
    j += 2
    while j < len(t) and t[j] in " \t":
        j += 1
    return spans, j

def target_position_ids(lines, name):
    # Inventory Occurrence IDs (numbered as code_inventory numbers them) of the occurrences written inside the
    # parentheses of the target of a signal assignment: <array_label>(... <element> ...) <= ...
    out = set()
    for k, (n, col, w) in enumerate(occurrence_matches(lines, name)):
        parts = _assignment_parts(lines[n]) if col >= 0 else None
        if parts and any(a <= col < b for a, b in parts[0]):
            out.add(k + 1)
    return out

def whole_rhs_slice_ids(lines, name):
    # Inventory Occurrence IDs of the occurrences that are the whole right-hand side of a signal assignment, written as
    # a slice: <target> <= <element>(<high> downto <low>);
    out, rx = set(), _name_re(name)
    for k, (n, col, w) in enumerate(occurrence_matches(lines, name)):
        t = re.sub(r"--.*", "", lines[n])
        parts = _assignment_parts(t) if col >= 0 else None
        if not parts or parts[1] != col:
            continue
        m = rx.match(t, col)
        rest = t[m.end():] if m else ""
        if not re.match(r"\s*\(", rest):
            continue
        i = rest.index("(") + 1
        j, depth = i, 1
        while j < len(rest) and depth:
            depth += {"(": 1, ")": -1}.get(rest[j], 0)
            j += 1
        flat = rest[i:j - 1]
        while re.search(r"\([^()]*\)", flat):
            flat = re.sub(r"\([^()]*\)", " ", flat)
        if not depth and re.search(r"\b(downto|to)\b", flat, re.I) and re.fullmatch(r"\s*;\s*", rest[j:]):
            out.add(k + 1)
    return out

def rule_decision_gaps(lines, inv, rows, name):
    # The owner's two decisions, checked on entries that carry their line's inventory ID:
    #   target: (ID, line, tags) for a position inside a target's parentheses tagged LHS_PROC or LHS_CONC
    #   slice:  (ID, line, tags) for a whole-right-hand-side slice not tagged PART_SELECT alone
    line_of = {r["Occurrence ID"]: r["Occurrence Lines"] for r in inv}
    tp, ws = target_position_ids(lines, name), whole_rhs_slice_ids(lines, name)
    target, slices = [], []
    for r in rows:
        oid, ln, tags = r.get("Occurrence ID"), r.get("Occurrence Lines"), list(r.get("SITE Tagged") or [])
        if not _valid_id(oid) or line_of.get(oid) != ln:
            continue
        if oid in tp and {"LHS_PROC", "LHS_CONC"} & set(tags):
            target.append((oid, ln, tags))
        if oid in ws and tags != ["PART_SELECT"]:
            slices.append((oid, ln, tags))
    return target, slices

def _selftest_id_and_field_use():
    fails = []
    def chk(label, got, want):
        if got != want:
            fails.append((label, got))
    inv = [{"Occurrence ID": 1, "Occurrence Lines": 10, "Name As Written": "s"},
           {"Occurrence ID": 2, "Occurrence Lines": 12, "Name As Written": "s.a"},
           {"Occurrence ID": 3, "Occurrence Lines": 12, "Name As Written": "s.b"},
           {"Occurrence ID": 4, "Occurrence Lines": 15, "Name As Written": "s.c"}]
    R = lambda *p: [{"Occurrence ID": i, "Occurrence Lines": l} for i, l in p]
    chk("short line and a renumbered entry", id_line_issues(inv, R((1, 10), (2, 12), (3, 15))),
        ([(12, 2, 1, [(3, "s.b")], [], []), (15, 1, 1, [(4, "s.c")], [], [(3, 12)])], [], []))
    chk("repeated ID on a line", id_line_issues(inv, R((1, 10), (2, 12), (2, 12), (4, 15))),
        ([(12, 2, 2, [(3, "s.b")], [2], [])], [], []))
    chk("ID written as text", id_line_issues(inv, R(("1", 10), (2, 12), (3, 12), (4, 15))),
        ([(10, 1, 1, [(1, "s")], [], [])], [], [("1", 10)]))
    chk("ID true", id_line_issues(inv, R((True, 10), (2, 12), (3, 12), (4, 15)))[2], [(True, 10)])
    chk("an added occurrence", id_line_issues(inv, R((1, 10), (2, 12), (3, 12), (4, 15), (5, 12))), ([], [(5, 12, 4)], []))
    chk("an added ID used twice", id_line_issues(inv, R((1, 10), (2, 12), (3, 12), (4, 15), (5, 12), (5, 15)))[0],
        [(12, 2, 3, [], [], [(5, None)]), (15, 1, 2, [], [], [(5, None)])])
    chk("short line whose entry carries another line's ID", id_line_issues(inv, R((1, 10), (4, 12), (4, 15))),
        ([(12, 2, 1, [(2, "s.a"), (3, "s.b")], [], [(4, 15)])], [], []))
    F = lambda *p: [{"Occurrence ID": i, "Occurrence Lines": l, "SITE Tagged": t} for i, l, t in p]
    chk("FIELD_USE on the bare occurrence", field_use_off_field(inv, F((1, 10, ["FIELD_USE"]), (2, 12, ["FIELD_USE"]),
                                                                     (3, 12, ["FIELD_USE"])), "s"), [(10, [1], 1, True)])
    mixed = [{"Occurrence ID": 7, "Occurrence Lines": 50, "Name As Written": "c"},
             {"Occurrence ID": 8, "Occurrence Lines": 50, "Name As Written": "c.st"}]
    chk("mixed line, FIELD_USE on the bare one", field_use_off_field(mixed, F((7, 50, ["FIELD_USE"]), (8, 50, ["LHS_PROC"])), "c"),
        [(50, [7], 1, True)])
    chk("mixed line, FIELD_USE on both", field_use_off_field(mixed, F((7, 50, ["FIELD_USE"]), (8, 50, ["FIELD_USE"])), "c"),
        [(50, [7], 1, True)])
    chk("three FIELD_USE without their IDs, one written with a field",
        field_use_off_field(mixed, F((20, 50, ["FIELD_USE"]), (21, 50, ["FIELD_USE"]), (22, 50, ["FIELD_USE"])), "c"),
        [(50, [20, 21, 22], 2, False)])
    # boot_rom, read by hand: line 60 writes bus_req_i.stb and bus_req_i.rw; line 48 writes the field
    # bus_req_i.addr followed by a range, not by another field
    exp = json.load(open(EXPECTED_FILE, encoding="utf-8"))
    job = {"src": numbered_entity_source(RTL_DIR / f"{exp['module']}.vhd", exp["entity"]),
           "elems": [{"name": e["name"]} for e in exp["elements"]]}
    binv = code_inventory(job)
    base = [dict(r, **{"SITE Tagged": ["FIELD_USE"]}) for r in binv["bus_req_i"] if r["Occurrence Lines"] == 60]
    chk("boot_rom bus_req_i @ 60", field_use_off_field(binv["bus_req_i"], base, "bus_req_i"), [])
    fld = [dict(r, **{"SITE Tagged": ["FIELD_USE"]}) for r in binv["bus_req_i.addr"] if r["Occurrence Lines"] == 48]
    chk("boot_rom bus_req_i.addr @ 48", [x[0] for x in field_use_off_field(binv["bus_req_i.addr"], fld, "bus_req_i.addr")], [48])
    # the two rule decisions, on lines read by hand:
    #   neorv32_cache.vhd 383   valid_mem(to_integer(unsigned(acc_idx))) <= '0';
    #   neorv32_fifo.vhd  150   fifo_mem(to_integer(unsigned(w_pnt(w_pnt'left-1 downto 0)))) <= wdata_i;
    #   neorv32_cache.vhd 367   acc_idx <= addr_i(31-tag_size_c downto 2+offset_size_c);
    #   neorv32_cache.vhd 180   ctrl_nxt.tag <= host_req_i.addr(31 downto 32-tag_size_c);
    #   neorv32_boot_rom  48    rdata <= mem_rom_c(to_integer(unsigned(bus_req_i.addr(boot_rom_size_index_c+1 downto 2))));
    def lines_of(mod, ent, name, ids):
        L = source_lines(numbered_entity_source(RTL_DIR / f"{mod}.vhd", ent))
        m = occurrence_matches(L, name)
        return sorted(m[i - 1][0] for i in ids)
    def ids(fn, mod, ent, name):
        L = source_lines(numbered_entity_source(RTL_DIR / f"{mod}.vhd", ent))
        return lines_of(mod, ent, name, fn(L, name))
    chk("target position acc_idx", ids(target_position_ids, "neorv32_cache", "neorv32_cache_memory", "acc_idx"), [383, 385, 398])
    chk("target position valid_mem", [x for x in ids(target_position_ids, "neorv32_cache", "neorv32_cache_memory", "valid_mem")
                                       if x in (383, 385)], [])
    chk("target position w_pnt", [x for x in ids(target_position_ids, "neorv32_fifo", "neorv32_fifo", "w_pnt") if x == 150],
        [150, 150])
    chk("whole right-hand-side slice addr_i", ids(whole_rhs_slice_ids, "neorv32_cache", "neorv32_cache_memory", "addr_i"),
        [366, 367, 368])
    chk("whole right-hand-side slice acc_idx", [x for x in ids(whole_rhs_slice_ids, "neorv32_cache", "neorv32_cache_memory",
                                                              "acc_idx") if x == 367], [])
    chk("whole right-hand-side slice host_req_i.addr", [x for x in ids(whole_rhs_slice_ids, "neorv32_cache", "neorv32_cache",
                                                                       "host_req_i.addr") if x in (180, 181)], [180, 181])
    chk("whole right-hand-side slice host_req_i", [x for x in ids(whole_rhs_slice_ids, "neorv32_cache", "neorv32_cache",
                                                                  "host_req_i") if x in (180, 181)], [])
    chk("boot_rom bus_req_i.addr @ 48, neither", (ids(target_position_ids, "neorv32_boot_rom", "neorv32_boot_rom", "bus_req_i.addr"),
                                                  ids(whole_rhs_slice_ids, "neorv32_boot_rom", "neorv32_boot_rom", "bus_req_i.addr")),
        ([], []))
    toy = {1: "  mem(i) <= i;", 2: "  x <= a(3 downto 0) when c = '1' else b;", 3: "  if (a(1) <= b) then",
           4: "  y <= a(7 downto 4); -- comment", 5: "  lbl: z <= a(1);"}
    chk("toy target", sorted(n for n, c, w in [occurrence_matches(toy, "i")[k - 1] for k in target_position_ids(toy, "i")]), [1])
    chk("toy slices", sorted(occurrence_matches(toy, "a")[k - 1][0] for k in whole_rhs_slice_ids(toy, "a")), [4])
    return fails

_ss = _selftest_structures() + _selftest_inventory() + _selftest_id_and_field_use()
SELFTEST_OK = SELFTEST_OK and not _ss
print("structure and inventory self-test:", "PASS" if not _ss else f"FAIL {_ss}")

def _norm_opener(kind, o):
    if kind == "branch":
        return str(o or "").strip().upper().replace("ELSE", "else")
    if kind == "alternative":
        return re.sub(r"[\s\"']", "", str(o or "")).lower()
    return ""

def structure_compare(L, S_, entry):
    # the finder's chain for the entry's line against the entry's Structure; spans compared on shown lines
    def trim(a, b):
        while a < b and a not in L:
            a += 1
        while b > a and b not in L:
            b -= 1
        return a, b
    want = [(s["kind"], s["lines"][0], s["lines"][1], _norm_opener(s["kind"], s["opened by"]))
            for s in structure_chain(S_, entry["Occurrence Lines"])]
    got, bad = [], 0
    for s in entry.get("Structure") if isinstance(entry.get("Structure"), list) else []:
        try:
            k = str(s["kind"]).strip().lower()
            a, b = trim(int(s["lines"][0]), int(s["lines"][1]))
            got.append((k, a, b, _norm_opener(k, s.get("opened by"))))
        except Exception:
            bad += 1
    wc, gc = Counter(want), Counter(got)
    return {"ok": wc == gc and not bad, "want": want, "got": got, "missing": list((wc - gc).elements()),
            "extra": list((gc - wc).elements()), "malformed": bad}

def _show(ch):
    return "; ".join(f"{k} {a}-{b}" + (f" ({o})" if o else "") for k, a, b, o in ch) or "none"

def code_checklist(job, profiles):
    # Facts a program found, for validate to check: lines where the entries and the inventory disagree (missing
    # entries, IDs from another line, repeated IDs), IDs that are not whole numbers, occurrences the model added,
    # Structures that differ from the source, indexed or sliced names without INDEXED_NAME / PART_SELECT, FIELD_USE on
    # an occurrence not written <element>.<field>, a position inside a target tagged as the target, a
    # whole-right-hand-side slice not tagged PART_SELECT alone, and Roles with words that say what something is for.
    L = source_lines(job["src"])
    inv = code_inventory(job)
    ent_names = next([e["name"] for e in elems] for ent, elems in load_elements(job["module"])
                     if ent == job["entity"])
    items = []
    try:
        S_ = structures_of(job["src"])
    except StructureError as ex:
        S_ = None
        items.append(f"- (the program could not read the structures of this entity: {ex}; no structure item follows)")
    for e in job["elems"]:
        n = e["name"]
        rows = [r for r in profiles.get(n, []) if isinstance(r, dict)]
        inv_n = inv.get(n, [])
        id_lines, added, bad = id_line_issues(inv_n, rows)
        for ln, k, g, uncarried, repeated, foreign in id_lines:
            listed = ", ".join("%s (%s)" % (o["Occurrence ID"], o["Name As Written"]) for o in inv_n
                               if o["Occurrence Lines"] == ln)
            s = (f"- {n}: line {ln} holds {k} occurrence(s) of the element" +
                 (f" (inventory Occurrence ID(s) {listed})" if k else "") +
                 f"; the profile has {g} entr{'y' if g == 1 else 'ies'} there.")
            if uncarried:
                s += f" No entry there carries Occurrence ID(s) {', '.join(str(i) for i, _ in uncarried)}."
            s += "".join(f" Occurrence ID {i} is carried by more than one entry there." for i in repeated)
            s += "".join(f" An entry there carries Occurrence ID {i}, which the inventory gives to line {l2}." if l2 is not None
                         else f" An entry there carries Occurrence ID {i}, which is not an inventory Occurrence ID of the element."
                         for i, l2 in foreign)
            items.append(s)
        items += [f"- {n}: the entry at line {ln} carries Occurrence ID {json.dumps(i)}, which is not a whole number."
                  for i, ln in bad]
        items += [f"- {n}: the entry at line {ln} carries Occurrence ID {i}, above the inventory's highest ({top}): an "
                  f"occurrence the program did not list. Keep it only if the source shows an occurrence of the element "
                  f"there that no other entry accounts for."
                  for i, ln, top in added]
        for ln, ids, wrong, exact in field_use_off_field(inv_n, rows, n):
            if exact:
                items.append(f"- {n}: at line {ln}, the entr{'y' if len(ids) == 1 else 'ies'} with Occurrence ID(s) "
                             f"{', '.join(map(str, ids))} carr{'ies' if len(ids) == 1 else 'y'} FIELD_USE, but that "
                             f"occurrence is not written <element>.<field>. FIELD_USE belongs only to a record base "
                             f"written with one of its fields; a field gets the SITEs any other element would get.")
            else:
                items.append(f"- {n}: at line {ln}, {len(ids)} entries without their line's inventory Occurrence ID "
                             f"({', '.join(map(str, ids))}) carry FIELD_USE, {wrong} more than the occurrences written "
                             f"<element>.<field> there. FIELD_USE belongs only to a record base written with one of its "
                             f"fields.")
        tgt, slc = rule_decision_gaps(L, inv_n, rows, n)
        items += [f"- {n}: the entry with Occurrence ID {i} at line {ln} is tagged {', '.join(tags)}, but that "
                  f"occurrence is inside the parentheses of the assignment's target, so it is not the target: no "
                  f"LHS_PROC or LHS_CONC."
                  for i, ln, tags in tgt]
        items += [f"- {n}: the entry with Occurrence ID {i} at line {ln} is tagged {', '.join(tags) or 'nothing'}, but "
                  f"that occurrence is a slice that is the whole right-hand side of a signal assignment: PART_SELECT "
                  f"alone."
                  for i, ln, tags in slc]
        for r in rows:
            if S_ is not None and isinstance(r.get("Occurrence Lines"), int) and r["Occurrence Lines"] in L:
                cmp_ = structure_compare(L, S_, r)
                if not cmp_["ok"]:
                    items.append(f"- {n}: the entry with Occurrence ID {r.get('Occurrence ID')} at line {r['Occurrence Lines']} "
                                 f"gives the structures {_show(cmp_['got'])}; the program finds {_show(cmp_['want'])}.")
        for ln, ki, ti, ks, ts in addon_gaps(L, n, rows):
            items.append(f"- {n}: line {ln} writes the element with one position in parentheses {ki} time(s) and with "
                         f"a range {ks} time(s); the profile has INDEXED_NAME {ti} time(s) and PART_SELECT {ts} time(s) "
                         f"there.")
        items += [f"- {n}: the Role of the entry at line {r.get('Occurrence Lines')} uses '{w}', which says "
                  f"what something is for."
                  for r in rows for w in design_words(r.get("Role", ""), ent_names)]
    body = "\n".join(items) if items else "- no item"
    return f"\nCODE CHECK, from a program that compared the profiles with the source:\n{body}\n"



FIELDS = {"extract":  ("Occurrence ID", "Occurrence Lines", "Name As Written", "Line Text"),
          "classify": ("Occurrence ID", "Occurrence Lines", "Structure", "Role", "SITE Tagged"),
          "validate": ("Occurrence ID", "Occurrence Lines", "Structure", "Role", "SITE Tagged")}

def parse_answer(step, rec, src_lines):
    issues, dups = Counter(), []
    def hook(pairs):
        seen = set()
        for k, _ in pairs:
            if k in seen:
                dups.append(k)
            seen.add(k)
        return dict(pairs)
    try:
        d = json.loads(rec["raw"], object_pairs_hook=hook)
    except Exception:
        issues["answer is not valid JSON"] += 1
        return None, issues
    if not isinstance(d, dict):
        issues["answer is not a JSON object"] += 1
        return None, issues
    for k in dups:
        issues[f"duplicate key: {k}"] += 1
    for n in d:
        if n not in rec["names"]:
            issues["element not in the closed set"] += 1
    out = {}
    for n in rec["names"]:
        if n not in d:
            issues["element missing from the answer"] += 1
            continue
        if not isinstance(d[n], list):
            issues["profile is not a list"] += 1
            continue
        if not d[n]:
            issues["element with no entry (review)"] += 1
        rows = []
        for r in d[n]:
            if not isinstance(r, dict):
                issues["entry is not an object"] += 1
                continue
            if set(r) != set(FIELDS[step]):
                issues["entry fields differ from the format"] += 1
            oid = r.get("Occurrence ID")
            if not isinstance(oid, int) or isinstance(oid, bool):
                issues["Occurrence ID is not an integer"] += 1
            ln = r.get("Occurrence Lines")
            if not isinstance(ln, int) or isinstance(ln, bool):
                issues["line is not an integer"] += 1
                continue
            if ln not in src_lines:
                issues["line not shown in the source"] += 1
            if step != "extract":
                tags = r.get("SITE Tagged")
                if not isinstance(tags, list):
                    issues["SITE Tagged is not a list"] += 1
                    tags = [tags] if isinstance(tags, str) else []
                tags = [t for t in tags if isinstance(t, str)]
                for t in tags:
                    if t not in SITES:
                        issues[f"site not in v2 or added_sites: {t}"] += 1
                if len(tags) != len(set(tags)):
                    issues["tag repeated in one list"] += 1
                if not tags:
                    issues["entry with no SITE, empty list (review)"] += 1
                r = dict(r, **{"SITE Tagged": tags})
                st = r.get("Structure")
                if not isinstance(st, list) or not all(isinstance(s, dict) and s.get("kind") in STRUCTURE_KINDS
                                                       and isinstance(s.get("lines"), list) and len(s["lines"]) == 2
                                                       for s in st):
                    issues["Structure malformed or with an unknown kind"] += 1
                if not isinstance(r.get("Role"), str) or not r.get("Role", "").strip():
                    issues["Role missing"] += 1
            rows.append(r)
        ids = [r.get("Occurrence ID") for r in rows]
        if len(ids) != len(set(ids)):
            issues["Occurrence ID repeated in one profile"] += 1
        out[n] = rows
    return out, issues

def read_answer(step, job):
    # None when not on disk. Otherwise {"stale", "parsed", "issues"}: stale means the answer was
    # made from upstream answers that have since changed, or that are missing.
    p = out_path(step, job)
    if p is None or not p.exists():
        return None
    rec = json.loads(p.read_text(encoding="utf-8"))
    up = upstream(step, job)
    if up is None or rec.get("input_sha") != sha12(user_message(step, job, up)):
        return {"stale": True, "parsed": None, "issues": Counter()}
    parsed, iss = parse_answer(step, rec, source_lines(job["src"]))
    return {"stale": False, "parsed": parsed, "issues": iss}

def upstream(step, job):
    got = {}
    for s in {"extract": (), "classify": ("extract",), "validate": ("extract", "classify")}[step]:
        a = read_answer(s, job)
        if a is None or a["stale"] or a["parsed"] is None:
            return None
        got[s] = a["parsed"]
    return got

def profiles_of(step, modules):
    prof, issues = {}, Counter()
    for job in build_jobs(modules):
        a = read_answer(step, job)
        if a is None:
            issues["batch not on disk"] += 1
            continue
        if a["stale"]:
            issues["batch made from an older upstream answer (not used)"] += 1
            continue
        issues.update(a["issues"])
        for n, rows in (a["parsed"] or {}).items():
            prof[(job["module"], job["entity"], n)] = rows
    return prof, issues"""

C_RULEBOOK = r"""# [rulebook]  -- step 1's output: read, check, and fill the classify and validate prompts
def make_rulebook():
    print("knowledge: 1 call")
    text = client.complete(KNOWLEDGE_SYSTEM, "Build the rulebook from the SITE definitions in "
                           "your instructions. Return it as one JSON object in the format given "
                           "there.", max_tokens=MAX_TOKENS)
    arch = OUT_DIR / "knowledge" / PROMPT_SHA["knowledge"] / "rulebook_raw.json"
    arch.parent.mkdir(parents=True, exist_ok=True)
    arch.write_text(json.dumps({"prompt_sha": PROMPT_SHA["knowledge"], "sites_sha": SITES_SHA,
                                "model": GEN_MODEL, "effort": EFFORT, "raw": text}, indent=1),
                    encoding="utf-8")
    try:
        d = json.loads(text)
    except Exception:
        print("   the answer is not valid JSON; raw kept at", arch)
        return
    d = {"sites_sha": SITES_SHA, "knowledge_prompt_sha": PROMPT_SHA["knowledge"], **d}
    RULEBOOK_FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    print("   wrote", RULEBOOK_FILE)

def load_rulebook():
    # Returns (usable, sha). Problems block the run; review items are for you to read.
    SYSTEM.update(classify=None, validate=None)
    PROMPT_SHA.update(classify=None, validate=None)
    SITES[:] = V2_SITES
    if not RULEBOOK_FILE.exists():
        print("no rulebook yet: step 1 writes it on the first run")
        return False, None
    raw = RULEBOOK_FILE.read_text(encoding="utf-8")
    sha = sha12(raw)
    try:
        d = json.loads(raw)
    except Exception as e:
        print(f"rulebook {sha}: not valid JSON ({e})")
        return False, sha
    problems, review = [], []
    if d.get("sites_sha") != SITES_SHA:
        # v2 no longer reaches the classify and validate prompts, so a v2 edit is a note, not a stop
        review.append(f"SITES_draft_v2.md changed since the rulebook was built (rulebook {d.get('sites_sha')}, "
                      f"v2 now {SITES_SHA}). Check whether the rulebook needs the change, then set its "
                      f"sites_sha to {SITES_SHA}. Deleting rulebook.json rebuilds it and loses the hand "
                      f"edits and added_sites.")
    rules = d.get("SITE_RULES") if isinstance(d.get("SITE_RULES"), dict) else {}
    conflicts = d.get("CONFLICT_RULES") if isinstance(d.get("CONFLICT_RULES"), list) else []
    # a SITE the rulebook defines beyond v2 must be listed in added_sites
    added = d.get("added_sites") if isinstance(d.get("added_sites"), list) else []
    bad = [s for s in added if s in V2_SITES or not re.fullmatch(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+", str(s))]
    if bad:
        problems.append(f"added_sites already in v2, or not a SITE name: {bad}")
    taxonomy = V2_SITES + [s for s in added if s not in V2_SITES and s not in bad]
    if [s for s in taxonomy if s not in rules]:
        problems.append(f"SITEs missing: {[s for s in taxonomy if s not in rules]}")
    if [s for s in rules if s not in taxonomy]:
        problems.append(f"SITEs neither in v2 nor in added_sites: {[s for s in rules if s not in taxonomy]}")
    SITES[:] = taxonomy                     # so the audit below accepts the added names
    for s, r in rules.items():
        for k in ("trigger", "required_structure", "context", "exclusion", "basis"):
            if k not in r:
                review.append(f"{s}: no '{k}'")
    norm = lambda x: re.sub(r"\s+", " ", re.sub(r"[`*]", "", str(x))).strip().lower().rstrip(".")
    v2 = norm(SITES_MD)
    quotes = [(s, q) for s, r in rules.items() for q in (r.get("basis") or [])]
    quotes += [("/".join(c.get("sites", [])), q) for c in conflicts for q in (c.get("basis") or [])]
    for where, q in quotes:
        if norm(q) not in v2:
            review.append(f"{where}: basis not found word for word in v2: {q!r}")
    # the prompt carries the rulebook without its basis quotes, which repeat section M word for word
    slim = {"SITE_RULES": {s: {k: v for k, v in r.items() if k != "basis"} for s, r in rules.items()},
            "CONFLICT_RULES": [{k: v for k, v in c.items() if k != "basis"} for c in conflicts]}
    text = json.dumps(slim, indent=1, ensure_ascii=False)
    code = [p for r in rules.values() for p in (r.get("required_structure") or []) if isinstance(p, str)]
    problems += audit_prompt(text, code=code)
    print(f"rulebook {sha}: {len(rules)} SITE rules, {len(conflicts)} conflict rules, "
          f"{len(quotes)} basis quotes")
    if added:
        print(f"   SITEs added by the rulebook, not in v2: {added}")
    for p in problems:
        print("   PROBLEM", p)
    for r in review:
        print("   review ", r)
    if problems:
        SITES[:] = V2_SITES
        return False, sha
    SYSTEM.update(annotate_systems(text))
    PROMPT_SHA.update(classify=sha12(SYSTEM["classify"]), validate=sha12(SYSTEM["validate"]))
    print(f"   classify prompt {PROMPT_SHA['classify']} ({len(SYSTEM['classify']):,} chars), "
          f"validate prompt {PROMPT_SHA['validate']} ({len(SYSTEM['validate']):,} chars)")
    return True, sha

RULEBOOK_USABLE, RULEBOOK_SHA = load_rulebook()"""

MD_RUN = r"""## Run

- `RUN_ON = "none"` makes no API call and prints what would run.
- `RUN_ON = "boot_rom"` runs `neorv32_boot_rom`, for the check against your hand profile.
- `RUN_ON = "trng_cache"` runs `neorv32_trng` and `neorv32_cache`.

The first real run makes one call, writes `occurrence_prompts_v2/rulebook.json`, and stops. Read the rulebook, edit it if a rule is wrong, then paste the sha printed for it into `APPROVED_RULEBOOK`. Any edit changes the sha, so an edited rulebook needs approving again.

Each call's raw answer is saved before anything reads it. A batch whose current answer is on disk is skipped; an answer that is not valid JSON is called again, and the bad one kept beside it. Put a step name in `REDO` to call it again anyway."""

C_RUN = r"""# [run]
RUN_ON            = "none"   # "none": no API call | "boot_rom": the check | "trng_cache"
APPROVED_RULEBOOK = ""       # paste the sha printed for rulebook.json, after reading it
REDO              = []       # steps to call again although a current answer is on disk, e.g. ["validate"]

from concurrent.futures import ThreadPoolExecutor, as_completed

def call_step(step, jobs):
    waiting, todo = [], []
    for j in jobs:
        if upstream(step, j) is None:
            waiting.append(j)
            continue
        a = read_answer(step, j)
        if a is None or a["stale"] or a["parsed"] is None or step in REDO:
            todo.append(j)
    print(f"  {step:9s} {len(todo)} {'batch(es) to build by code' if step == 'extract' else 'call(s) to make'}, {len(jobs) - len(todo) - len(waiting)} current "
          f"on disk, {len(waiting)} waiting on an earlier step")

    def one(j):
        msg = user_message(step, j, upstream(step, j))
        if step == "extract":
            text, model = json.dumps(code_inventory(j), indent=1), "code"
        else:
            text, model = client.complete(SYSTEM[step], msg, max_tokens=MAX_TOKENS), GEN_MODEL
        p = out_path(step, j)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            a = read_answer(step, j)
            if a and not a["stale"] and a["parsed"] is None:
                p.replace(p.with_suffix(".invalid.json"))
        p.write_text(json.dumps({
            "step": step, "prompt_sha": PROMPT_SHA[step], "input_sha": sha12(msg),
            "model": model, "effort": EFFORT if model != "code" else "", "module": j["module"], "entity": j["entity"],
            "batch": j["batch"], "names": [e["name"] for e in j["elems"]], "raw": text}, indent=1),
            encoding="utf-8")
        return j

    with ThreadPoolExecutor(WORKERS) as ex:
        for f in as_completed([ex.submit(one, j) for j in todo]):
            j = f.result()
            print(f"     done  {j['module']}/{j['entity']} batch {j['batch']}")

def run():
    global RULEBOOK_USABLE, RULEBOOK_SHA
    if RUN_ON == "none":
        print("RUN_ON = 'none': no API call made.")
        print(f"  knowledge: {'rulebook.json on disk' if RULEBOOK_FILE.exists() else '1 call, then stop for approval'}")
        for s, mods in MODULES.items():
            js = build_jobs(mods)
            print(f"  {s}: {len(js)} batch(es) x 2 model steps = {len(js) * 2} calls (extract is code)")
            for step in STEPS:
                cur = 0
                for j in js:
                    a = read_answer(step, j)
                    cur += bool(a and not a["stale"] and a["parsed"] is not None)
                print(f"     {step:9s} {cur} of {len(js)} current on disk")
        return
    assert RUN_ON in MODULES, f"RUN_ON must be 'none' or one of {list(MODULES)}"
    if not SELFTEST_OK:
        print("stopped: a self-test in the checks cell failed; the inventory and the structure checks cannot be trusted")
        return
    if not RULEBOOK_FILE.exists():
        make_rulebook()
    RULEBOOK_USABLE, RULEBOOK_SHA = load_rulebook()
    if not RULEBOOK_USABLE:
        print("stopped: fix rulebook.json (deleting it rebuilds it and loses the hand edits)")
        return
    if RULEBOOK_SHA != APPROVED_RULEBOOK:
        print(f"stopped: rulebook {RULEBOOK_SHA} is not approved. Read {RULEBOOK_FILE}, edit it if "
              f"needed, then set APPROVED_RULEBOOK = \"{RULEBOOK_SHA}\" and run this cell again.")
        return
    jobs = build_jobs(MODULES[RUN_ON])
    for step in STEPS:
        call_step(step, jobs)
    print("cost so far:", json.dumps(client.cost()))

run()"""

C_PARSE = r"""# [parse]  -- shape of each answer, and the occurrence checks (no model)
def occurrence_checks(step, modules):
    prof, _ = profiles_of(step, modules)
    rows = off = excluded = missed = merged = total = 0
    shown = []
    for job in build_jobs(modules):
        L = source_lines(job["src"])
        for e in job["elems"]:
            key = (job["module"], job["entity"], e["name"])
            if key not in prof:
                continue
            cnt = occurrence_counts(L, e["name"])
            allowed = written_lines(L, e["name"]) | set(cnt)
            got = Counter(r["Occurrence Lines"] for r in prof[key])
            rows += len(prof[key])
            for n, k in sorted(got.items()):
                if n not in allowed:
                    off += k
                    shown.append(f"{e['name']} @ {n}: element not written there")
                elif n not in cnt:
                    excluded += k
                    shown.append(f"{e['name']} @ {n}: component port clause, left of =>, or record type declaration")
            for n, want in sorted(cnt.items()):
                total += want
                if got[n] < want:
                    missed += want - got[n]
                    merged += (want - got[n]) if got[n] else 0
                    shown.append(f"{e['name']} @ {n}: {want} occurrence(s), {got[n]} "
                                 f"entr{'y' if got[n] == 1 else 'ies'}")
    return rows, off, excluded, missed, merged, total, shown

def inventory_checks(step, modules):
    # Compared with the inventory, entry by entry (id_line_issues, field_use_off_field, rule_decision_gaps):
    # ID problems (another line's ID, a repeated ID, not a whole number), occurrences the model added,
    # FIELD_USE on an occurrence not written <element>.<field>, and the owner's two rule decisions.
    inv, _ = profiles_of("extract", modules)
    prof, _ = profiles_of(step, modules)
    out = {"id": [], "n_id": 0, "added": [], "fu": [], "n_fu": 0, "fu_exact": True, "target": [], "slice": []}
    for job in build_jobs(modules):
        L = source_lines(job["src"])
        for e in job["elems"]:
            key = (job["module"], job["entity"], e["name"])
            if key not in prof or key not in inv:
                continue
            rows, n = prof[key], e["name"]
            id_lines, added, bad = id_line_issues(inv[key], rows)
            for ln, k, g, uncarried, repeated, foreign in id_lines:
                probs = [f"ID {i} belongs to line {l2}" if l2 is not None else f"ID {i} is not an inventory ID"
                         for i, l2 in foreign]
                probs += [f"ID {i} on more than one entry" for i in repeated]
                if probs:
                    out["id"].append(f"{n} @ {ln}: " + "; ".join(probs))
                out["n_id"] += len(foreign) + sum(
                    Counter(r.get("Occurrence ID") for r in rows if r.get("Occurrence Lines") == ln)[i] - 1 for i in repeated)
            out["id"] += [f"{n} @ {ln}: ID {json.dumps(i)} is not a whole number" for i, ln in bad]
            out["n_id"] += len(bad)
            out["added"] += [f"{n} @ {ln}: ID {i} (inventory's highest {top})" for i, ln, top in added]
            for ln, ids, wrong, exact in field_use_off_field(inv[key], rows, n):
                out["n_fu"] += wrong
                out["fu_exact"] = out["fu_exact"] and exact
                out["fu"].append(f"{n} @ {ln}: FIELD_USE on ID(s) {ids}" + ("" if exact else f", {wrong} too many for the line"))
            tgt, slc = rule_decision_gaps(L, inv[key], rows, n)
            out["target"] += [f"{n} @ {ln} (ID {i}): {tags}" for i, ln, tags in tgt]
            out["slice"] += [f"{n} @ {ln} (ID {i}): {tags}" for i, ln, tags in slc]
    return out

def structure_checks(step, modules):
    prof, _ = profiles_of(step, modules)
    tot, wrong_by_kind, listing, failed = Counter(), Counter(), [], []
    for job in build_jobs(modules):
        L = source_lines(job["src"])
        try:
            S_ = structures_of(job["src"])
        except StructureError as ex:
            failed.append(f"{job['entity']} batch {job['batch']}: not checked, the structure finder failed ({ex})")
            continue
        for e in job["elems"]:
            for r in prof.get((job["module"], job["entity"], e["name"]), []):
                if r["Occurrence Lines"] not in L:
                    continue
                cmp_ = structure_compare(L, S_, r)
                tot["entries"] += 1
                tot["entries correct"] += int(cmp_["ok"])
                for k, a, b, o in cmp_["want"]:
                    tot["structures"] += 1
                    wrong_by_kind[(k, "total")] += 1
                for k, a, b, o in cmp_["missing"]:
                    near = [x for x in cmp_["extra"] if x[0] == k and x[1] == a]
                    wrong_by_kind[(k, "wrong end" if near else "missing or wrong start/opener")] += 1
                for k, a, b, o in cmp_["extra"]:
                    if not [x for x in cmp_["missing"] if x[0] == k and x[1] == a]:
                        wrong_by_kind[(k, "extra")] += 1
                if not cmp_["ok"]:
                    listing.append(f"{e['name']} @ {r['Occurrence Lines']} (ID {r.get('Occurrence ID')}): gives {_show(cmp_['got'])} | "
                                   f"source {_show(cmp_['want'])}")
    return tot, wrong_by_kind, listing, failed

def design_word_hits(step, modules):
    prof, _ = profiles_of(step, modules)
    names = {}
    for m in modules:
        for ent, elems in load_elements(m):
            names[(m, ent)] = [e["name"] for e in elems]
    hits, n = [], 0
    for (m, ent, name), rows in prof.items():
        for r in rows:
            if step == "extract":
                continue
            n += 1
            w = design_words(r.get("Role", ""), names[(m, ent)])
            if w:
                hits.append(f"{name} @ {r['Occurrence Lines']}: {', '.join(w)}")
    return hits, n

for set_name, mods in MODULES.items():
    print(f"===== {set_name} =====")
    for step in STEPS:
        prof, iss = profiles_of(step, mods)
        n_rows = sum(len(v) for v in prof.values())
        print(f"  {step}: {len(prof)} element profiles, {n_rows} entries")
        for k, v in iss.most_common():
            print(f"     {k}: {v}")
        if not prof:
            continue
        if not SELFTEST_OK:
            print("     occurrence checks not reported: a self-test failed")
            continue
        rows, off, excl, missed, merged, total, shown = occurrence_checks(step, mods)
        print(f"     entries on a line where the element is not written:   {off} of {rows}  (exact)")
        print(f"     entries on a line the extract rules exclude:          {excl} of {rows}  (exact)")
        print(f"     occurrences with no entry:                            {missed} of {total}  (exact under the check's rules)")
        print(f"       of those, on a line that has some entry (merged):   {merged}")
        for s in shown:
            print("        ", s)
        if step != "extract":
            agaps = []
            P = profiles_of(step, mods)[0]
            for job in build_jobs(mods):
                L = source_lines(job["src"])
                for e in job["elems"]:
                    key = (job["module"], job["entity"], e["name"])
                    if key in P:
                        agaps += [f"{e['name']} @ {ln}: index {ki} vs INDEXED_NAME {ti}, slice {ks} vs PART_SELECT {ts}"
                                  for ln, ki, ti, ks, ts in addon_gaps(L, e["name"], P[key])]
            print(f"     lines where INDEXED_NAME / PART_SELECT tags differ from the source: {len(agaps)}")
            for s in agaps:
                print("        ", s)
            tot, wk, listing, failed = structure_checks(step, mods)
            for s in failed:
                print("     ", s)
            print(f"     entries whose Structure equals the source's: {tot['entries correct']} of {tot['entries']}  "
                  f"(exact under the finder's rules; spans compared on shown lines"
                  + (f"; {len(failed)} batch(es) not checked" if failed else "") + ")")
            kinds = sorted({k for k, _ in wk})
            print("       per kind (in the source / wrong end / missing or wrong start / extra): " +
                  ", ".join(f"{k} {wk[(k, 'total')]}/{wk[(k, 'wrong end')]}/{wk[(k, 'missing or wrong start/opener')]}/{wk[(k, 'extra')]}"
                            for k in kinds))
            for s in listing[:40]:
                print("        ", s)
            if len(listing) > 40:
                print(f"         ... and {len(listing) - 40} more")
            ic = inventory_checks(step, mods)
            print(f"     entries with an Occurrence ID problem (another line's ID, repeated, not a whole number): {ic['n_id']} of {rows}  (exact)")
            for s in ic["id"][:40]:
                print("        ", s)
            if len(ic["id"]) > 40:
                print(f"         ... and {len(ic['id']) - 40} more")
            print(f"     entries added by the model (ID above the inventory's): {len(ic['added'])} of {rows}")
            for s in ic["added"]:
                print("        ", s)
            print(f"     FIELD_USE entries on an occurrence not written <element>.<field>: {ic['n_fu']} of {rows}  "
                  + ("(exact)" if ic["fu_exact"] else "(counted per line where IDs are wrong)"))
            for s in ic["fu"]:
                print("        ", s)
            print(f"     positions inside a target's parentheses tagged LHS_PROC or LHS_CONC: {len(ic['target'])} of {rows}  "
                  f"(exact for entries that carry their line's inventory ID)")
            for s in ic["target"]:
                print("        ", s)
            print(f"     whole-right-hand-side slices not tagged PART_SELECT alone: {len(ic['slice'])} of {rows}  "
                  f"(exact for entries that carry their line's inventory ID)")
            for s in ic["slice"]:
                print("        ", s)
            if not WORDS_SELFTEST_OK:
                print("     design-word check not reported: its self-test failed")
                continue
            hits, n = design_word_hits(step, mods)
            print(f"     Roles with a design word (word list {sha12(' '.join(DESIGN_WORDS))}, lower bound): {len(hits)} of {n}  (read the list)")
            for h in hits:
                print("        ", h)"""

C_COMPARE = r"""# [compare]  -- each step on boot_rom against boot_rom_expected_v2.json
def compare_to_expected(step):
    exp = json.load(open(EXPECTED_FILE, encoding="utf-8"))
    prof, _ = profiles_of(step, MODULES["boot_rom"])
    print(f"== {step} ==")
    if not prof:
        print("   no current boot_rom answer on disk")
        return
    m, ent = exp["module"], exp["entity"]
    pct = lambda a, b: f"{a}/{b} = {100 * a / b:.0f}%" if b else "n/a"
    for group in ("hand", "predicted"):
        L, P, diffs = Counter(), Counter(), []
        for e in exp["elements"]:
            if e["source"] != group:
                continue
            got = prof.get((m, ent, e["name"]), [])
            ml, el = {r["Occurrence Lines"] for r in got}, {r["line"] for r in e["rows"]}
            L["hit"] += len(ml & el); L["model"] += len(ml); L["exp"] += len(el)
            if step == "extract":
                if ml != el:
                    diffs.append((e["name"], sorted(el - ml), sorted(ml - el)))
                continue
            mp = {(r["Occurrence Lines"], t) for r in got for t in r["SITE Tagged"]}
            ep = {(r["line"], r["site"]) for r in e["rows"]}
            P["hit"] += len(mp & ep); P["model"] += len(mp); P["exp"] += len(ep)
            if mp != ep:
                diffs.append((e["name"], sorted(ep - mp), sorted(mp - ep)))
        print(f"  {group.upper()} elements   (exact counts; pairs compared as sets)")
        print(f"     occurrence lines     recall {pct(L['hit'], L['exp']):>14}   "
              f"precision {pct(L['hit'], L['model'])}")
        if step != "extract":
            print(f"     (line, SITE) pairs   recall {pct(P['hit'], P['exp']):>14}   "
                  f"precision {pct(P['hit'], P['model'])}")
        for n, miss, extra in diffs:
            print(f"        {n}:  expected, not produced {miss}   produced, not expected {extra}")

for step in STEPS:
    compare_to_expected(step)"""

C_DIFF = r"""# [diff]  -- what validate changed in classify's profiles
def validation_changes(modules):
    c, _ = profiles_of("classify", modules)
    v, _ = profiles_of("validate", modules)
    keys = [k for k in c if k in v]
    if not keys:
        print("   no element has both a classify and a validate answer")
        return
    pairs = lambda rows: {(r["Occurrence Lines"], t) for r in rows for t in (r["SITE Tagged"] or ["(none)"])}
    removed = added = 0
    changed = []
    for k in keys:
        cp, vp = pairs(c[k]), pairs(v[k])
        removed += len(cp - vp); added += len(vp - cp)
        if cp != vp:
            changed.append((k[2], sorted(cp - vp), sorted(vp - cp)))
    print(f"   {len(changed)} of {len(keys)} profiles changed: {removed} (line, SITE) pairs removed, "
          f"{added} added   ('(none)' = empty SITE list)")
    # Structures: classify and validate entries are paired one to one inside each element and line, first on equal
    # Occurrence IDs, then the rest in ID order, so an ID that validate corrected still pairs.
    st = lambda r: json.dumps(r.get("Structure"), sort_keys=True)
    changed_st = paired = unpaired = 0
    for k in keys:
        at = {}
        for side, rows in (("c", c[k]), ("v", v[k])):
            for r in rows:
                at.setdefault(r.get("Occurrence Lines"), {"c": [], "v": []})[side].append(r)
        for ln, sides in at.items():
            cs, vs = list(sides["c"]), list(sides["v"])
            pairs = []
            for rc in list(cs):
                rv = next((x for x in vs if x.get("Occurrence ID") == rc.get("Occurrence ID")), None)
                if rv is not None:
                    pairs.append((rc, rv)); cs.remove(rc); vs.remove(rv)
            order = lambda r: (not isinstance(r.get("Occurrence ID"), int), str(r.get("Occurrence ID")))
            pairs += list(zip(sorted(cs, key=order), sorted(vs, key=order)))
            unpaired += abs(len(cs) - len(vs))
            paired += len(pairs)
            changed_st += sum(1 for rc, rv in pairs if st(rc) != st(rv))
    print(f"   entries whose Structure validate changed: {changed_st} of {paired} paired entries "
          f"(paired inside each element and line; {unpaired} entries without a partner not compared)")
    for n, rem, add in changed:
        print(f"      {n}:  removed {rem}   added {add}")

for set_name, mods in MODULES.items():
    print(f"===== {set_name} =====")
    validation_changes(mods)"""

C_RENDER = r"""# [render]  -- the tables, in the format of annotation_process.md
# The structure part of each Context is read off the source by the self-tested finder (section D rules). The model's
# Structure stays in the answers and is scored in the parse cell; where the finder fails on an entity, or an entry's
# line is not in the source, the row falls back to the model's Structure and says so. Tables go to a folder named by
# the classify and validate prompt shas, so a new prompt version never overwrites an older run's tables.
def render(set_name):
    for m in MODULES[set_name]:
        v, _ = profiles_of("validate", [m])
        c, _ = profiles_of("classify", [m])
        if not v and not c:
            continue
        out = [f"# Occurrence profiles: {m}", "",
               f"rulebook `{RULEBOOK_SHA}` · classify `{PROMPT_SHA['classify']}` · "
               f"validate `{PROMPT_SHA['validate']}` · model `{GEN_MODEL}` · effort `{EFFORT}`", "",
               "Context: the enclosing structures are read off the source by code (the structure finder); "
               "the role and the SITE tags are the model's.", ""]
        n_rows = n_finder = n_differ = 0
        for ent, elems in load_elements(m):
            out += [f"## Entity {ent}", ""]
            src = numbered_entity_source(RTL_DIR / f"{m}.vhd", ent)
            L = source_lines(src)
            try:
                S_ = structures_of(src)
            except StructureError as ex:
                S_ = None
                print(f"   {ent}: the structure finder failed ({ex}); its tables use the model's Structure")
                out += [f"(the structure finder failed on this entity: the Context uses the model's Structure)", ""]
            for e in elems:
                key = (m, ent, e["name"])
                rows, step = (v[key], "validate") if key in v else (c.get(key), "classify")
                if rows is None:
                    out += [f"### {e['name']}", "", "(no answer)", ""]
                    continue
                out += [f"### {e['name']}", "", f"from {step}", "",
                        "| Occurrence Lines | Context | SITE Tagged |", "| --- | --- | --- |"]
                for r in sorted(rows, key=lambda r: (r["Occurrence Lines"], r["Occurrence ID"]
                                                     if isinstance(r.get("Occurrence ID"), int) else 0)):
                    n_rows += 1
                    if S_ is not None and r["Occurrence Lines"] in L:
                        prefix = render_structure(structure_chain(S_, r["Occurrence Lines"]))
                        n_finder += 1
                        n_differ += int(not structure_compare(L, S_, r)["ok"])
                    else:
                        note = ("(the model's Structure: line not in the source) " if S_ is not None
                                else "(the model's Structure) ")
                        st = r.get("Structure") if isinstance(r.get("Structure"), list) else []
                        try:
                            prefix = "; ".join(f"{s['kind']} {s['lines'][0]}-{s['lines'][1]}" +
                                               (f" ({s['opened by']})" if s.get("opened by") else "") for s in st)
                        except Exception:
                            prefix = json.dumps(st)
                        prefix = note + prefix
                    ctx = (prefix + "; " if prefix else "") + str(r.get("Role", ""))
                    ctx = ctx.replace("|", "\\|")
                    tags = ", ".join(r["SITE Tagged"])      # blank where no SITE matched
                    out.append(f"| line {r['Occurrence Lines']} | {ctx} | {tags} |")
                out.append("")
        counts = (f"structures from the finder for {n_finder} of {n_rows} entries; "
                  f"{n_differ} of those differ from the model's Structure")
        out[4:4] = [f"Count: {counts}.", ""]
        p = OUT_DIR / "tables" / f"{PROMPT_SHA['classify']}_{PROMPT_SHA['validate']}" / f"{m}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(out), encoding="utf-8")
        print(f"wrote {p}: {counts}")

for set_name in MODULES:
    render(set_name)"""

C_COST = r"""# [cost]
print(json.dumps(client.cost(), indent=2))"""

cells = [("markdown", MD0), ("code", C_SETUP), ("code", C_ENV), ("code", C_CLIENT),
         ("code", C_PROMPTS), ("code", C_INPUTS), ("code", C_CHECKS), ("code", C_RULEBOOK),
         ("markdown", MD_RUN), ("code", C_RUN), ("code", C_PARSE), ("code", C_COMPARE),
         ("code", C_DIFF), ("code", C_RENDER), ("code", C_COST)]


def cell(kind, src):
    lines = src.split("\n")
    body = [l + "\n" for l in lines[:-1]] + [lines[-1]]
    c = {"cell_type": kind, "metadata": {}, "source": body}
    if kind == "code":
        c.update({"execution_count": None, "outputs": []})
    return c


if __name__ == "__main__":
    nb = {"cells": [cell(k, s) for k, s in cells], "metadata": ref.get("metadata", {}),
          "nbformat": 4, "nbformat_minor": ref.get("nbformat_minor", 5)}
    import sys
    if NB.exists() and "--replace" not in sys.argv:
        raise SystemExit(f"{NB} already exists -- pass --replace (only while no kernel has it open)")
    NB.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {NB} ({len(cells)} cells)")
