"""Generate notebooks/parser_verifier.ipynb"""
import nbformat as nbf, os, sys, io, json

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "notebooks"); os.makedirs(OUT, exist_ok=True)
nb = nbf.v4.new_notebook(); C = []
def md(s): C.append(nbf.v4.new_markdown_cell(s.strip()))
def co(s): C.append(nbf.v4.new_code_cell(s.strip()))

md(r"""
# Parser Verifier — RTL-grounded behavioral audit

Audits the behavioral claims in `data/parsed_v3_tuning18/*.json` against the authoritative
RTL in `data/RTL_data/*.vhd`.

> **The RTL is the authoritative source. The parsed JSON is a hypothesis to be checked.**

**Scope — behavioral fidelity only.** functionality · roles · relationships · relationship
targets · evidence.

**Explicitly out of scope.** No asset identification, no C/I/A/U, no security relevance, no
use of `back_test.md` or the asset labels, no security implications, no rewriting or silently
correcting parser output, no external documentation, no general NEORV32 knowledge used to
fill gaps, no assuming similarly-named signals behave alike.

The verifier is an **auditor, not a second parser**. The required reasoning is
`Parser says X -> find X in RTL -> does the RTL directly support X?`, never
`Parser says X -> what do I think X probably means?`

## Statuses

| status | meaning |
|---|---|
| `SUPPORTED` | RTL directly supports the claim |
| `PARTIALLY_SUPPORTED` | broadly correct but omits a condition, branch, mode, generate guard, limitation, or target |
| `CONTRADICTED` | RTL directly shows behavior inconsistent with the claim |
| `NOT_ESTABLISHED` | plausible, but the supplied RTL does not establish it |
| `UNVERIFIABLE` | required RTL / entity / target cannot be located or mapped confidently |

Absence of evidence is `NOT_ESTABLISHED`, **never** `CONTRADICTED`.

## Anti-drift

A verification run never reads a previous verification result. Every run independently
compares `parser output <-> RTL`. Earlier runs feed aggregate statistics only, so an early
verifier mistake cannot become pseudo-ground-truth later. This is asserted in code.
""")

# ------------------------------------------------------------------ config
md("## 1. Configuration")

co(r'''
import os, sys, io, re, json, time, hashlib, random, subprocess
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
import pandas as pd

HERE = Path.cwd() if Path.cwd().name != "notebooks" else Path.cwd().parent

CONFIG = {
    "parsed_dir":        str(HERE / "data" / "parsed_v3_tuning18"),
    "rtl_dir":           str(HERE / "data" / "RTL_data"),
    "results_root":      str(HERE / "verification_results"),

    # provenance recorded in the manifest
    "parser_prompt_version": "v3_tuning18",
    "parsed_data_version":   "parsed_v3_tuning18",
    "rtl_dataset_version":   "RTL_data",
    "verifier_prompt_version": "VP3",

    "env_file":          str(HERE / "API.env"),
    "provider":          "openai",
    "model":             "gpt-5-mini",
    "api_key_env":       "OPENAI_API_KEY",

    # Reasoning models are driven through the Responses API with `reasoning.effort`.
    # They do NOT accept temperature or seed, so those knobs do not exist here --
    # run-to-run determinism comes from the response cache, not from decoding params.
    "reasoning_effort":  "medium",
    "max_output_tokens": 12000,
    # local RNG only (retry jitter). NOT an API parameter -- the Responses API
    # accepts no seed, so this does not make model output reproducible.
    "seed":              20260818,
    # reasoning tokens share the output budget, so a verbose schema can exhaust it
    # and return empty text. On `incomplete`, retry with a bigger budget.
    "escalate_on_incomplete":    True,
    "max_output_tokens_ceiling": 24000,
    # only sent for models that support it; auto-detected from the model name
    "force_reasoning":   None,      # True / False to override auto-detection
    "temperature":       0.0,       # anthropic path only; ignored by Responses API

    # per-1M-token prices for the cost report (defaults: gpt-5-mini)
    "price_in":          0.25,
    "price_cached_in":   0.025,
    "price_out":         2.00,

    "max_retries":       6,
    "backoff_base_s":    2.0,
    "backoff_cap_s":     60.0,
    "request_timeout_s": 180,
    "parallel_workers":  4,
    "cache_enabled":     True,

    # RTL context budget per element (characters)
    "ctx_window_lines":  6,      # +/- lines around each hit
    "ctx_max_hits":      40,     # cap hits per symbol
    "ctx_max_chars":     22000,  # hard cap on assembled RTL context
}

random.seed(CONFIG["seed"])
print("parsed :", CONFIG["parsed_dir"], Path(CONFIG["parsed_dir"]).exists())
print("rtl    :", CONFIG["rtl_dir"], Path(CONFIG["rtl_dir"]).exists())
''')

co(r'''
def load_env_file(path):
    """Minimal .env reader. Tolerates `KEY = value`, quotes, comments, and a
    missing trailing newline. Values are never printed."""
    p = Path(path); loaded = []
    if not p.exists(): return loaded
    for raw in p.read_text(encoding="utf-8-sig").splitlines() or [p.read_text(encoding="utf-8-sig")]:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        k = k.strip(); v = v.strip().strip('"').strip("'")
        if k:
            os.environ[k] = v; loaded.append(k)
    return loaded

_loaded = load_env_file(CONFIG["env_file"])
print(f"loaded from {Path(CONFIG['env_file']).name}: {_loaded or 'nothing'}")

API_KEY = os.environ.get(CONFIG["api_key_env"], "").strip()
if not API_KEY:
    raise RuntimeError(
        f"{CONFIG['api_key_env']} not found in {CONFIG['env_file']} or the environment.\n"
        f"Expected a line like  {CONFIG['api_key_env']}=sk-...  in API.env.\n"
        f"Never hard-code the key in this notebook.")
print(f"{CONFIG['api_key_env']}: present ({len(API_KEY)} chars, "
      f"ends ...{API_KEY[-4:]})")

# Reasoning models take `reasoning.effort` and reject temperature/seed.
def _is_reasoning_model(m):
    m = m.lower()
    return m.startswith(("gpt-5", "o1", "o3", "o4")) or "-reasoning" in m
USE_REASONING = (CONFIG["force_reasoning"]
                 if CONFIG["force_reasoning"] is not None
                 else _is_reasoning_model(CONFIG["model"]))
print(f"model {CONFIG['model']}: reasoning={USE_REASONING}"
      + (f", effort={CONFIG['reasoning_effort']}" if USE_REASONING else ""))
''')

co(r'''
# ---- run directory: never overwrite a previous run ---------------------------
def next_run_dir(root):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    n = 1 + max([int(p.name.split("_")[1]) for p in root.glob("run_*") if p.name.split("_")[-1].isdigit()] or [0])
    d = root / f"run_{n:03d}"
    d.mkdir(parents=True, exist_ok=False)
    return d

RUN_DIR = next_run_dir(CONFIG["results_root"])
CACHE_DIR = Path(CONFIG["results_root"], "_cache"); CACHE_DIR.mkdir(parents=True, exist_ok=True)
print("run dir:", RUN_DIR)

# ---- ANTI-DRIFT GUARD (instructions section 22) ------------------------------
# No verification result from any previous run may enter this run as evidence.
_FORBIDDEN_READ = [p for p in Path(CONFIG["results_root"]).glob("run_*") if p != RUN_DIR]
def assert_no_prior_results_used(text, where):
    """Called on every payload sent to the model."""
    for p in _FORBIDDEN_READ:
        if p.name in str(text):
            raise AssertionError(f"anti-drift violation: prior run {p.name} referenced in {where}")
    for tok in ["overall_status", "functionality_check", "role_checks", "relationship_checks",
                "verification_results"]:
        if tok in str(text):
            raise AssertionError(f"anti-drift violation: verifier-output vocabulary '{tok}' in {where}")
print(f"anti-drift guard armed; {len(_FORBIDDEN_READ)} prior run(s) quarantined")
''')

# ------------------------------------------------------------------ load
md(r"""
## 2. Load parsed JSON

Schema observed in `parsed_v3_tuning18`:

```
{ "module": str, "entities": [str], "ports": [element], "signals": [element], "_issues": {...} }
element = { entity, name, type, function, functionality, role[], relationship[{type,targets[]}],
            evidence, dir?, kind? }
```

`_issues` is the parser's own self-report and is loaded as deterministic context, not as truth.
""")

co(r'''
ELEMENT_KEYS = ["entity", "name", "type", "function", "functionality",
                "role", "relationship", "evidence", "dir", "kind"]

def load_parsed(parsed_dir):
    recs, files, malformed = [], {}, []
    for p in sorted(Path(parsed_dir).glob("*.json")):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            malformed.append({"file": p.name, "error": f"JSON_SYNTAX: {e}"}); continue
        files[p.stem] = {"path": str(p), "module": j.get("module", p.stem),
                         "entities": j.get("entities", []) or [],
                         "issues": j.get("_issues", {}) or {}}
        for bucket in ("ports", "signals"):
            for i, e in enumerate(j.get(bucket, []) or []):
                if not isinstance(e, dict) or "name" not in e or "entity" not in e:
                    malformed.append({"file": p.name, "bucket": bucket, "index": i,
                                      "error": "MALFORMED_RECORD: missing name/entity"})
                    continue
                r = {k: e.get(k) for k in ELEMENT_KEYS}
                r.update(source_file=p.name, module=j.get("module", p.stem),
                         bucket=bucket, index=i)
                r["role"] = r["role"] or []
                r["relationship"] = r["relationship"] or []
                recs.append(r)
    return recs, files, malformed

PARSED, FILES, MALFORMED = load_parsed(CONFIG["parsed_dir"])
for r in PARSED:
    r["element_id"] = "el_" + hashlib.sha256(
        f"{r['module']}\x00{r['entity']}\x00{r['name']}".encode()).hexdigest()[:16]

pdf = pd.DataFrame(PARSED)
print("files:", len(FILES), "| elements:", len(pdf), "| malformed:", len(MALFORMED))
print("modules:", pdf.module.nunique(), "| entities:", pdf.entity.nunique())
print("relationship types present in data:")
rt = Counter(x.get("type") for r in PARSED for x in r["relationship"])
print("  ", dict(rt.most_common()))
dupes = pdf.duplicated(subset=["module", "entity", "name"], keep=False)
print("duplicate (module,entity,name) rows:", int(dupes.sum()))
if MALFORMED: display(pd.DataFrame(MALFORMED).head())
''')

md(r"""
> **Relationship vocabulary discrepancy — read this.**
> The specification lists eight types: `CAPTURES DERIVES_FROM GATES SELECTS SOURCES
> CONSTRAINS CARRIES SEQUENCES`. The parsed data also uses `EXPORTS`, `ISOLATED`,
> `OVERRIDES`, `AGGREGATES`, `SLICES`, `REFLECTS`.
>
> These are **not** treated as errors — the parser may legitimately have a wider vocabulary.
> They are flagged deterministically as `type_outside_spec_vocabulary` so you can decide
> whether the parser prompt or the spec should change. The verifier is told to audit them
> literally, by their plain meaning, exactly as it does the eight specified types.
""")

# ------------------------------------------------------------------ rtl index
md(r"""
## 3. RTL index and file mapping

A `.vhd` file may hold several entities (`neorv32_bus.vhd` holds six), so mapping is
**entity -> (file, line span)**, not module -> file. An entity is only mapped when its
`entity <name> is` declaration is actually found; a filename resembling an entity name is
never sufficient. Unmapped entities are recorded `UNVERIFIABLE_FILE_MAPPING` and are not
guessed.
""")

co(r'''
ENT_RE  = re.compile(r"(?im)^\s*entity\s+(\w+)\s+is\b")
ARCH_RE = re.compile(r"(?im)^\s*architecture\s+(\w+)\s+of\s+(\w+)\s+is\b")
END_RE  = re.compile(r"(?im)^\s*end\s+(?:entity|architecture)?\s*;?\s*$")

def build_rtl_index(rtl_dir):
    idx, files = {}, {}
    for p in sorted(Path(rtl_dir).glob("*.vhd")):
        src = p.read_text(encoding="utf-8", errors="replace")
        lines = src.split("\n")
        # comment-stripped mirror: an identifier mentioned only in a comment is NOT
        # evidence that the signal exists in the design.
        code = [l.split("--")[0] for l in lines]
        files[p.name] = {"path": str(p), "lines": lines, "code": code,
                         "sha256": hashlib.sha256(src.encode("utf-8", "replace")).hexdigest()}
        spans = []
        for m in ENT_RE.finditer(src):
            spans.append(("entity", m.group(1), src[:m.start()].count("\n")))
        for m in ARCH_RE.finditer(src):
            spans.append(("arch", m.group(2), src[:m.start()].count("\n")))
        spans.sort(key=lambda t: t[2])
        for i, (kind, name, ln) in enumerate(spans):
            end = spans[i + 1][2] if i + 1 < len(spans) else len(lines)
            e = idx.setdefault(name.lower(), {"entity": name, "file": p.name, "decl": None,
                                              "arch": None})
            if e["file"] != p.name:      # same entity name in two files -> ambiguous
                e["ambiguous"] = True
            if kind == "entity": e["decl"] = (ln, end)
            else: e["arch"] = (ln, end)
        # constants that gate generate branches (section 11)
        consts = {}
        for m in re.finditer(r"(?im)^\s*constant\s+(\w+)\s*:\s*boolean\s*:=\s*(true|false)\s*;", src):
            consts[m.group(1).lower()] = (m.group(2).lower() == "true")
        files[p.name]["bool_constants"] = consts
    return idx, files

RTL_INDEX, RTL_FILES = build_rtl_index(CONFIG["rtl_dir"])

# Union of every identifier occurring in actual RTL code (comments excluded).
# Used to decide which tokens in a prose `evidence` string are plausibly meant as
# signal references at all. Without this, prose words ("assignment", "concurrent",
# "the") get reported as missing signals and swamp the real findings.
_IDENT = re.compile(r"[A-Za-z_]\w*")
GLOBAL_RTL_IDENTS = set()
for _f in RTL_FILES.values():
    for _l in _f["code"]:
        GLOBAL_RTL_IDENTS.update(t.lower() for t in _IDENT.findall(_l))
print("rtl files:", len(RTL_FILES), "| indexed entities:", len(RTL_INDEX),
      "| distinct code identifiers:", len(GLOBAL_RTL_IDENTS))
mapped = sum(1 for e in pdf.entity.unique() if e.lower() in RTL_INDEX)
print(f"parsed entities mapped to an RTL entity declaration: {mapped}/{pdf.entity.nunique()}")
unmapped = sorted(e for e in pdf.entity.unique() if e.lower() not in RTL_INDEX)
if unmapped: print("UNVERIFIABLE_FILE_MAPPING:", unmapped)
amb = [k for k, v in RTL_INDEX.items() if v.get("ambiguous")]
if amb: print("ambiguous entity names (same name, multiple files):", amb)
print("boolean constants found (generate guards):",
      {f: c for f, d in RTL_FILES.items() if (c := d["bool_constants"])})
''')

# ------------------------------------------------------------------ context
md(r"""
## 4. RTL context extraction

Whole files cannot be sent (some exceed 40k chars), so per element we assemble a slice that
preserves exactly what the audit rules need:

- the **entity port clause** (so port direction/type claims are checkable);
- every line mentioning the element, its **record base** (`core_req_i.stb` -> `core_req_i`),
  and every **relationship target**, with surrounding context;
- the **enclosing construct header** for each hit — `process`, `if`, `elsif`, `case`, `when`,
  `generate` — so conditional, generate and reset context (sections 10–12) is visible rather
  than inferred;
- 1-based **line numbers** on every line, so the model can populate `rtl_location`.

This is line-oriented extraction, not a VHDL parser. When a symbol has more hits than
`ctx_max_hits`, the slice is truncated and the model is told so explicitly — a truncated
slice must yield `NOT_ESTABLISHED`, never a confident verdict.
""")

co(r'''
ENCLOSING_RE = re.compile(
    r"(?i)\b(process|if\b|elsif\b|else\b|case\b|when\b|for\b|generate|begin|end\s+process)")

def _base(name):
    """core_req_i.stb -> core_req_i ; keeps arrays like x(3) -> x"""
    return re.split(r"[.\(]", str(name))[0].strip()

def _enclosing_headers(lines, i, look=90):
    """Walk back for the process/if/case/generate headers that contain line i."""
    out, depth_seen = [], set()
    for j in range(i, max(-1, i - look), -1):
        s = lines[j].strip()
        if not s or s.startswith("--"): continue
        m = re.match(r"(?i)^(\w+\s*:\s*)?(process|if|elsif|case|when|for)\b|.*\bgenerate\b", s)
        if m and j != i:
            key = s[:60]
            if key not in depth_seen:
                depth_seen.add(key); out.append((j + 1, lines[j].rstrip()))
        if len(out) >= 4: break
    return list(reversed(out))

def symbol_hits(lines, sym, max_hits, code=None):
    """Match against comment-stripped code so a mention inside a comment never
    counts as the signal existing. `lines` is still used for display."""
    pat = re.compile(r"(?<![\w.])" + re.escape(sym) + r"(?![\w])", re.I)
    src = code if code is not None else lines
    hits = [i for i, l in enumerate(src) if pat.search(l)]
    return hits[:max_hits], len(hits)

STD_TYPES = {"std_ulogic","std_logic","std_ulogic_vector","std_logic_vector","integer",
             "natural","boolean","bit","bit_vector","unsigned","signed","string","real"}

def _package_type_decls(entity_span_lines):
    """Record/type declarations for the non-standard types used in an entity's port
    clause, pulled from the package file(s).

    Without this the verifier sees `bus_req_i : in bus_req_t` and no definition of
    bus_req_t, so it cannot confirm any claim about a record field and raises
    UNVERIFIABLE/EVIDENCE errors that are artifacts of the excerpt, not parser
    faults. Record-typed ports are the norm in this design, so omitting these
    declarations would inject a systematic false-error mode across the whole run."""
    names = set()
    for l in entity_span_lines:
        for m in re.finditer(r":\s*(?:in|out|inout|buffer)\s+([A-Za-z_]\w*)", l, re.I):
            t = m.group(1)
            if t.lower() not in STD_TYPES: names.add(t)
    if not names: return ""
    out = []
    for pf in [f for f in RTL_FILES if "package" in f.lower()]:
        lines = RTL_FILES[pf]["lines"]
        for nm in sorted(names):
            m = re.search(r"(?im)^\s*type\s+" + re.escape(nm) + r"\s+is\b", "\n".join(lines))
            if not m: continue
            start = "\n".join(lines)[:m.start()].count("\n")
            end = start
            for j in range(start, min(start + 60, len(lines))):
                end = j
                if re.search(r"(?i)end\s+record\s*;|;\s*$", lines[j]) and j > start:
                    if re.search(r"(?i)end\s+record", lines[j]) or ";" in lines[j]: break
            out.append(f"--- type `{nm}` from {pf} ---")
            out += [f"{i+1:5d} | {lines[i].rstrip()}" for i in range(start, end + 1)]
    return "\n".join(out)

def rtl_context_for(rec, cfg=CONFIG):
    """-> (context_text, meta). meta carries mapping status and truncation flags."""
    ent = RTL_INDEX.get(str(rec["entity"]).lower())
    meta = {"entity": rec["entity"], "rtl_file": None, "mapping": "UNVERIFIABLE_FILE_MAPPING",
            "truncated": False, "symbols": {}, "arch_span": None}
    if not ent:
        return "", meta
    f = RTL_FILES[ent["file"]]
    lines = f["lines"]
    meta.update(rtl_file=ent["file"], mapping="MAPPED", rtl_sha256=f["sha256"][:16])
    lo, hi = (ent["arch"] or ent["decl"] or (0, len(lines)))
    meta["arch_span"] = [lo + 1, hi]

    keep = set()
    # entity port clause
    if ent["decl"]:
        d0, d1 = ent["decl"]
        keep.update(range(d0, min(d1, d0 + 120)))
    syms = [str(rec["name"]), _base(rec["name"])]
    for r in rec["relationship"]:
        for t in (r.get("targets") or []):
            syms += [str(t), _base(t)]
    seen = set()
    for s in syms:
        if not s or s.lower() in seen: continue
        seen.add(s.lower())
        hits, total = symbol_hits(lines, s, cfg["ctx_max_hits"], code=f["code"])
        meta["symbols"][s] = {"hits_shown": len(hits), "hits_total": total,
                              "present": total > 0}
        if total > len(hits): meta["truncated"] = True
        for i in hits:
            keep.update(range(max(0, i - cfg["ctx_window_lines"]),
                              min(len(lines), i + cfg["ctx_window_lines"] + 1)))
            for ln, _ in _enclosing_headers(lines, i):
                keep.add(ln - 1)

    out, prev = [], None
    for i in sorted(keep):
        if prev is not None and i > prev + 1:
            out.append("        ...")
        out.append(f"{i+1:5d} | {lines[i].rstrip()}")
        prev = i
    txt = "\n".join(out)
    if len(txt) > cfg["ctx_max_chars"]:
        txt = txt[:cfg["ctx_max_chars"]] + "\n        ... [CONTEXT TRUNCATED]"
        meta["truncated"] = True
    # append record/type declarations for the entity's non-standard port types
    if ent["decl"]:
        d0, d1 = ent["decl"]
        tdecl = _package_type_decls(lines[d0:d1])
        if tdecl:
            txt += "\n\n## TYPE DECLARATIONS (from the package, for the port types above)\n" + tdecl
            meta["type_decls_included"] = True
    return txt, meta

_probe = PARSED[0]
_c, _m = rtl_context_for(_probe)
print("probe:", _probe["module"], "/", _probe["entity"], "/", _probe["name"])
print("meta :", json.dumps({k: v for k, v in _m.items() if k != "symbols"}, default=str))
print("symbols:", json.dumps(_m["symbols"])[:300])
print("context chars:", len(_c))
print("\n".join(_c.split("\n")[:14]))
''')

# ------------------------------------------------------------------ deterministic
md(r"""
## 5. Deterministic checks (run before the LLM)

The static layer must not decide anything semantic. If it labelled reset-guarded assignments
or unresolved citations as *errors*, it would be telling the verifier what the parser got
wrong before any RTL comparison happened — which defeats the point of an independent audit.
So its output is split three ways, and only the first is a judgement:

| bucket | contents | weight given to the verifier |
|---|---|---|
| **confirmed problems** | duplicate record key, malformed record, entity absent from the RTL set | mechanical, indisputable |
| **facts** | assignment style (`combinational`/`clocked`/`both`/`none`), reset-guarded assignment, generate guards and their constant values, symbol-resolution tier | reliable measurements, no verdict |
| **review hints** | reset-branch assignment under a `SEQUENCES` claim, generate-guarded target, unresolved citation, non-spec relationship type | **questions only** — carry no presumption of error |

Every hint ships with the question the verifier must answer, and the prompt states that a hint
is not evidence and must never be cited as justification.

### Symbol resolution is graded, not binary

`found / not found` was wrong: a cited `bus_req_i.priv` may live in a package type
declaration, reach the entity through a port map, or belong to another entity entirely.
`resolve_symbol` returns the strongest tier it can establish:

`DIRECT_SYMBOL_MATCH` → `RECORD_BASE_MATCH` → `RECORD_FIELD_MATCH` → `PORT_MAP_MATCH` →
`PACKAGE_TYPE_MATCH` → `CROSS_ENTITY_MATCH` → `NOT_ESTABLISHED_BY_STATIC_CHECK`

The last tier means *the static matcher failed*, not *the symbol is absent*. It is passed as a
hint, never as an evidence error.
""")

co(r'''
SPEC_TYPES = {"CAPTURES","DERIVES_FROM","GATES","SELECTS","SOURCES","CONSTRAINS",
              "CARRIES","SEQUENCES"}
IDENT_RE = re.compile(r"[A-Za-z_]\w*(?:\.\w+)*")
VHDL_KW = set("""and or not xor nand nor if then else elsif end when case is of process begin
signal port map in out inout std_ulogic std_logic vector downto to others rising_edge
falling_edge if_else generate constant variable type record integer boolean natural true
false null return function procedure architecture entity use library work all""".split())

# English prose that appears in the parser's evidence sentences. These are never
# signal references, and some of them do occur inside VHDL string literals, so
# the global-identifier test alone does not exclude them.
PROSE_STOPWORDS = set("""the this that these those into onto from with without for and but
not are was were its it has have had been being when where which while whether then than
also only both each every any all via per use used uses using set sets same other another
such more most less least internal external direct directly indirect indirectly
respectively otherwise however therefore here there they them their one two three first
second next last new old full empty high low active inactive value values bit bits byte
e.g i.e etc vs eg ie
bytes word words line lines cycle cycles time times mode modes state states side sides
above below across between during before after within under over out off down up left
right whole part parts field fields list lists item items note notes case cases""".split())

DUP_KEYS = Counter((r["module"], r["entity"], r["name"]) for r in PARSED)

def _assignment_style(lines, sym, span):
    lo, hi = span
    clocked = comb = False
    pat = re.compile(r"(?<![\w.])" + re.escape(_base(sym)) + r"\b[^<]*<=", re.I)
    for i in range(lo, min(hi, len(lines))):
        if not pat.search(lines[i]): continue
        ctx = "\n".join(lines[max(lo, i - 40):i + 1]).lower()
        tail = ctx.rsplit("process", 1)
        if "rising_edge" in ctx or "falling_edge" in ctx:
            if len(tail) > 1 and ("rising_edge" in tail[1] or "falling_edge" in tail[1]):
                clocked = True
            else: comb = True
        else: comb = True
    return "both" if (clocked and comb) else ("clocked" if clocked else
           ("combinational" if comb else "none"))

def resolve_symbol(sym, own_file):
    """Graded static resolution of a cited identifier.

    Returns the STRONGEST match tier found, never a verdict. `NOT_ESTABLISHED_BY
    _STATIC_CHECK` means the static checker could not place the symbol -- it does
    NOT mean the parser is wrong; the verifier decides that from the RTL.
    """
    base = _base(sym); tail = sym.split(".")[-1] if "." in sym else None
    own = RTL_FILES[own_file]["code"]; blob = "\n".join(own)
    W = lambda s, txt: re.search(r"(?<![\w.])" + re.escape(s) + r"(?![\w])", txt, re.I)

    if W(sym, blob):                          return "DIRECT_SYMBOL_MATCH", own_file
    if W(base, blob):                         return "RECORD_BASE_MATCH", own_file
    if tail and re.search(r"\." + re.escape(tail) + r"(?![\w])", blob, re.I):
        return "RECORD_FIELD_MATCH", own_file
    # instance port maps: `.foo => bar` or `foo => bar`
    if re.search(r"(?<![\w.])" + re.escape(base) + r"\s*=>", blob, re.I):
        return "PORT_MAP_MATCH", own_file
    # package / shared type declarations
    for pf in [f for f in RTL_FILES if "package" in f.lower()]:
        pb = "\n".join(RTL_FILES[pf]["code"])
        if W(sym, pb) or W(base, pb) or (tail and re.search(r"\." + re.escape(tail) + r"(?![\w])", pb, re.I)) \
           or (tail and W(tail, pb)):
            return "PACKAGE_TYPE_MATCH", pf
    # any other entity's source
    for of in RTL_FILES:
        if of == own_file: continue
        ob = "\n".join(RTL_FILES[of]["code"])
        if W(sym, ob) or W(base, ob):
            return "CROSS_ENTITY_MATCH", of
    return "NOT_ESTABLISHED_BY_STATIC_CHECK", None


def deterministic_checks(rec, ctx_meta):
    """-> (problems, facts, hints)

    problems = genuinely mechanical defects. No semantic judgement is possible to
               dispute them (malformed record, duplicate key, entity not in RTL).
    facts    = measurements. Assignment style, reset-guarded assignment, generate
               guards, symbol resolution tier. No verdict attached.
    hints    = "look at this" pointers for the verifier. Explicitly NOT claims
               that the parser is wrong; each carries the question to answer.

    Nothing semantic is ever placed in `problems`. Whether a reset-guarded
    SEQUENCES claim, an inactive-generate reference, or an unresolvable citation
    is actually an error is a semantic judgement, and that belongs to the verifier
    reading the RTL -- not to this layer.
    """
    problems, hints = [], []
    if DUP_KEYS[(rec["module"], rec["entity"], rec["name"])] > 1:
        problems.append({"check": "duplicate_element", "detail":
                         "more than one parsed record shares (module, entity, name)"})
    if ctx_meta["mapping"] != "MAPPED":
        problems.append({"check": "UNVERIFIABLE_FILE_MAPPING",
                         "detail": f"no `entity {rec['entity']} is` declaration found in RTL_data"})
        return problems, {}, hints
    ent = RTL_INDEX[str(rec["entity"]).lower()]
    lines = RTL_FILES[ent["file"]]["lines"]
    consts = RTL_FILES[ent["file"]]["bool_constants"]
    span = ent["arch"] or ent["decl"] or (0, len(lines))

    tier, where = resolve_symbol(str(rec["name"]), ent["file"])
    if tier == "NOT_ESTABLISHED_BY_STATIC_CHECK":
        hints.append({"hint": "element_name_unresolved_by_static_check",
                      "detail": f"static checks could not place `{rec['name']}` in {ent['file']}",
                      "question": "Does the element appear in the RTL excerpt under another "
                                  "form (record field, aggregate, port map)? If genuinely absent, "
                                  "that bears on every claim about it."})

    facts = {"rtl_file": ent["file"], "arch_span": ctx_meta["arch_span"],
             "element_symbol_resolution": {"tier": tier, "found_in": where},
             "assignment_style_of_element": _assignment_style(lines, rec["name"], span),
             "targets": {}}

    for r in rec["relationship"]:
        t = str(r.get("type", ""))
        # Relationship vocabulary is a RUN-LEVEL property of the parser, not a
        # per-element observation. Emitting it per element produced 631 identical
        # hints and risked training the verifier to read "non-spec" as "wrong".
        # It is reported once, in the manifest; the prompt tells the verifier to
        # audit any type literally regardless of vocabulary.
        for tgt in (r.get("targets") or []):
            ttier, twhere = resolve_symbol(str(tgt), ent["file"])
            present = ttier != "NOT_ESTABLISHED_BY_STATIC_CHECK"
            info = {"symbol_resolution": {"tier": ttier, "found_in": twhere},
                    "assignment_style": None, "assigned_under_reset": False,
                    "in_generate_branch": None}
            if present and twhere == ent["file"]:
                info["assignment_style"] = _assignment_style(lines, tgt, span)
                pat = re.compile(r"(?<![\w.])" + re.escape(_base(tgt)) + r"\b[^<]*<=", re.I)
                for i in range(span[0], min(span[1], len(lines))):
                    if not pat.search(lines[i]): continue
                    back = "\n".join(lines[max(span[0], i - 25):i]).lower()
                    if re.search(r"if\s+.*rstn?\w*\s*=\s*'0'|if\s+.*\breset\b", back):
                        info["assigned_under_reset"] = True
                    g = re.findall(r"if\s+(\w+)\s+generate", back)
                    if g:
                        info["in_generate_branch"] = {gg: consts.get(gg.lower()) for gg in g}
            facts["targets"][str(tgt)] = info

            if not present:
                hints.append({"hint": "target_unresolved_by_static_check",
                              "detail": f"relationship {t} target `{tgt}` was not placed by any "
                                        f"static tier (direct / record base / record field / "
                                        f"port map / package / cross-entity)",
                              "question": "Locate the target in the RTL excerpt yourself. If it "
                                          "truly is not referenced, judge the relationship "
                                          "accordingly; if it is present in a form the static "
                                          "check missed, ignore this hint."})
            # Scope: the section-12 concern is a reset dependency being described as
            # ordinary sequencing, i.e. `rstn_i SEQUENCES ctrl`. Firing on every
            # relationship whose target happens to touch a reset branch produced 1570
            # hints (~1 per relationship) and drowned the signal. Fire only when the
            # source element is reset-like, or the claimed type is one that asserts
            # clock-driven state progression.
            _src_is_reset = bool(re.search(r"(?i)(^|_)(rstn?|reset)(_|$|\d)", str(rec["name"])))
            if info["assigned_under_reset"] and (_src_is_reset or
                                                 t.upper() in {"SEQUENCES", "CAPTURES"}):
                hints.append({"hint": "target_assigned_in_reset_branch",
                              "detail": f"`{tgt}` has at least one assignment inside a "
                                        f"reset-guarded branch; parser claims `{t}`",
                              "question": f"Does `{t}` accurately describe the dependency between "
                                          f"`{rec['name']}` and `{tgt}`? A reset that DRIVES a "
                                          f"register is not the same as one that SEQUENCES it. "
                                          f"Both readings are possible -- decide from the RTL."})
            if info["in_generate_branch"]:
                gv = info["in_generate_branch"]
                inactive = any(v is False for v in gv.values())
                hints.append({"hint": "target_in_generate_branch",
                              "detail": f"`{tgt}` is assigned under generate guard(s) {gv}"
                                        + (" — guard constant is FALSE, so that branch is not "
                                           "active in the default configuration" if inactive else
                                           " (guard value is not a literal boolean constant here)"),
                              "question": "A parser may correctly describe an alternative "
                                          "implementation IF it presents it as conditional. This "
                                          "is an error only if inactive behaviour is presented as "
                                          "the active/default behaviour. Judge the phrasing."})

    # ---- evidence citations -------------------------------------------------
    # This check exists to catch the parser citing a signal that does not exist.
    # It must be conservative: a false "missing signal" is fed to the verifier as
    # reliable evidence and would corrupt the audit. Three filters, all needed:
    #   1. prose stopwords are never signal references
    #   2. the token must look like an identifier the parser meant to cite
    #   3. presence is matched LOOSELY -- a cited `addr` is satisfied by
    #      `bus_req_i.addr`, and a cited `dev_00` by `dev_00_req_o`. Only a token
    #      absent even under loose matching is reported.
    ev = str(rec.get("evidence") or "")
    code_blob = "\n".join(RTL_FILES[ent["file"]]["code"])
    ev_res = {}
    for ident in set(IDENT_RE.findall(ev)):
        low = ident.lower().strip("_")
        if not low or low in VHDL_KW or low in PROSE_STOPWORDS or len(low) < 3: continue
        plausible = ("_" in ident) or ("." in ident) or (low in GLOBAL_RTL_IDENTS)
        if not plausible: continue
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(low), code_blob, re.I):
            continue                                   # resolved in own file, nothing to say
        etier, ewhere = resolve_symbol(ident, ent["file"])
        ev_res[ident] = {"tier": etier, "found_in": ewhere}
        if etier == "NOT_ESTABLISHED_BY_STATIC_CHECK":
            hints.append({"hint": "evidence_citation_unresolved_by_static_check",
                          "detail": f"evidence cites `{ident}`; no static tier placed it "
                                    f"(direct / record base / record field / port map / "
                                    f"package / cross-entity)",
                          "question": "Check the RTL excerpt directly. The citation may still be "
                                      "a valid paraphrase, or reference a form the static check "
                                      "missed. Only call it an evidence error if the RTL shows "
                                      "the cited construct is absent."})
        else:
            hints.append({"hint": "evidence_citation_resolved_elsewhere",
                          "detail": f"evidence cites `{ident}`, not found in {ent['file']} but "
                                    f"resolved as {etier} in {ewhere}",
                          "question": "Is the parser citing a construct that belongs to a "
                                      "different entity or to a package type declaration? That "
                                      "may be legitimate or may be a cross-entity error."})
    if ev_res: facts["evidence_symbol_resolution"] = ev_res
    return problems, facts, hints

_f, _facts, _hints = deterministic_checks(_probe, _m)
print("problems (mechanical only):", json.dumps(_f, indent=1)[:300])
print("review hints             :", json.dumps(_hints, indent=1)[:700])
print("facts                    :", json.dumps(_facts, indent=1)[:600])
''')

co(r'''
# ---- run deterministic layer over everything (no API cost) -------------------
DET = {}
for r in PARSED:
    _, m = rtl_context_for(r)
    fnd, facts, hts = deterministic_checks(r, m)
    DET[r["element_id"]] = {"findings": fnd, "facts": facts, "hints": hts, "ctx_meta":
                            {k: v for k, v in m.items() if k != "symbols"}}
cnt = Counter(f["check"] for d in DET.values() for f in d["findings"])
ncnt = Counter(n["hint"] for d in DET.values() for n in d["hints"])
tiers = Counter()
for d in DET.values():
    er = (d["facts"] or {}).get("element_symbol_resolution") or {}
    if er.get("tier"): tiers[er["tier"]] += 1
    for t in ((d["facts"] or {}).get("targets") or {}).values():
        tiers[(t.get("symbol_resolution") or {}).get("tier", "?")] += 1
print("CONFIRMED DETERMINISTIC PROBLEMS (mechanical, not semantic):")
for k, v in cnt.most_common():
    print("   %-34s %5d" % (k, v))
if not cnt: print("   (none)")
print()
print("REVIEW HINTS (questions for the verifier, NOT assertions of error):")
for k, v in ncnt.most_common():
    print("   %-44s %5d" % (k, v))
print()
print("DETERMINISTIC FACT: symbol resolution tier (elements + relationship targets):")
for k, v in tiers.most_common():
    print("   %-44s %5d" % (k, v))
det_df = pd.DataFrame(
    [{"item": k, "count": v, "class": "confirmed_problem"} for k, v in cnt.most_common()]
    + [{"item": k, "count": v, "class": "review_hint"} for k, v in ncnt.most_common()]
    + [{"item": k, "count": v, "class": "fact_resolution_tier"} for k, v in tiers.most_common()])
det_df
''')

# ------------------------------------------------------------------ prompt
md("## 6. Verifier prompt (versioned)")

co(r'''
VERIFIER_PROMPT_VERSION = CONFIG["verifier_prompt_version"]
VERIFIER_SYSTEM = r"""
You are an RTL auditor. You verify whether behavioral claims made by an automated parser are
actually supported by the VHDL source. You are NOT a parser and you do not produce new
behavioral descriptions of your own.

# Source hierarchy — strict
1. The supplied RTL excerpt is the authoritative source.
2. The parser claims are a hypothesis to be checked.
3. Nothing else may be used as factual evidence.

Never use external documentation. Never use general knowledge of NEORV32 or of any CPU to
fill a gap. Never assume a signal behaves a certain way because its name resembles another
signal's name. If the supplied RTL does not establish a claim, say so — do not invent an
explanation.

# Absolutely out of scope
Do not identify security assets. Do not assign C/I/A/U. Do not decide whether anything is
security-relevant, exploitable, an attack path, an information leak, or affects integrity.
Do not rewrite, improve, or silently correct the parser output. Your only sentence form is:
"the parser claims X; the RTL supports / partially supports / contradicts / does not
establish X."

# Statuses — use exactly these
- SUPPORTED — the RTL directly supports the claim.
- PARTIALLY_SUPPORTED — broadly correct but omits an important condition, branch, mode,
  generate guard, limitation, or target.
- CONTRADICTED — the RTL directly shows behavior inconsistent with the claim.
- NOT_ESTABLISHED — plausible, but the supplied RTL does not provide sufficient evidence.
- UNVERIFIABLE — the required RTL, entity, or target is not present in what you were given.

Absence of evidence is NOT_ESTABLISHED or UNVERIFIABLE. It is NEVER CONTRADICTED.
If the context is marked truncated and the missing part would decide the claim, use
NOT_ESTABLISHED rather than guessing.

CONTRADICTED requires POSITIVE RTL evidence that the claim is false — RTL you can point at
and quote. A failed static check, an unresolved symbol, or a review hint is never sufficient
grounds for CONTRADICTED. If a static check could not place something but the RTL neither
shows nor refutes it, that is NOT_ESTABLISHED.

# Review hints are questions, not findings
The payload may contain REVIEW HINTS. A hint means an automated check noticed something worth
your attention — a reset-guarded assignment, a generate guard, an unresolved citation. A hint
is NOT evidence that the parser is wrong, and it carries no presumption either way. Answer the
hint's question from the RTL. If the RTL supports the parser's claim, mark it SUPPORTED even
though a hint was raised. Never cite a hint as your justification; cite RTL.

# Judge semantics, not wording, and not abstraction level
Do not mark a claim wrong merely because the parser's wording differs from the RTL, or because
it describes behaviour at a higher level of abstraction than the statements themselves. Judge
semantic equivalence. Equally, do not accept a claim merely because it sounds plausible.

Both of these are acceptable paraphrases, not errors:
  RTL:    cache_o.we <= host_req_i.ben;
  parser: "host_req_i.ben provides the byte-enable mask used for cache writes."
  RTL:    ctrl_nxt.buf_req <= ctrl.buf_req or host_req_i.stb;
  parser: "host_req_i.stb records a pending request."
Distinguish *different wording* from *different behaviour*. Only the second is an error.

# You may trace short local dependency chains — under strict limits
You are not restricted to the single line the parser happened to cite. To check a claim you
may and should read the surrounding expression, the enclosing process, and the local
assignments feeding the signals involved — anything visible in the supplied excerpt. Do not
conclude NOT_ESTABLISHED merely because the parser's cited line was incomplete, when the
surrounding RTL you were given does establish the behaviour.

Limits, all binding:
- Trace at most 3 hops, and ONLY to establish the parser's stated claim. Tracing is not
  exploration; you are not mapping the design.
- Every hop must be a concrete RTL statement you can quote and cite by line number.
- Stop at the final traced RTL relationship. Do NOT infer consequences beyond it, and do not
  extrapolate what the design "therefore" does.
- Nothing outside the supplied excerpt may enter the chain.
- If a chain needs a hop you cannot see, stop and answer NOT_ESTABLISHED.

When you trace, record it in `rtl_trace` as an ordered list of DEPENDENCY HOPS -- one entry
per signal-to-signal step in the chain, each with its line reference. `rtl_trace` is not a
bibliography: if a single step is supported by several places in the RTL, keep it as ONE entry
and put the extra locations in that entry's `rtl_location` (e.g. "L110-L116; L243-L246").
A chain of 3 hops has 3 entries. An untraceable claim is NOT_ESTABLISHED, never CONTRADICTED.

# Classify the KIND of evidence behind every status
Each check carries `evidence_type`, exactly one of:
- `DIRECT_RTL`     — RTL statements demonstrate the claim outright.
- `TRACED_RTL`     — you had to FOLLOW A DEPENDENCY from one signal to another to establish
                     the claim; `rtl_trace` lists those hops.
- `INTERPRETATION` — the RTL is clear, but deciding whether it matches the parser's *wording*
                     required a semantic judgement on your part.

Choose between DIRECT_RTL and TRACED_RTL by **whether you traversed a dependency chain**, NOT
by how many lines you cited. Citing several locations for one fact is still `DIRECT_RTL` —
put those locations in `rtl_location` (e.g. "L101; L114-L126; L170-L176") and leave
`rtl_trace` as []. Only signal-to-signal traversal makes it `TRACED_RTL`.

Hard rule: `TRACED_RTL` REQUIRES at least one entry in `rtl_trace`. If you cannot name the
hops you followed, then you did not trace anything — use `DIRECT_RTL` instead. A `TRACED_RTL`
with an empty `rtl_trace` is an invalid response and will be rejected.

Only DIRECT_RTL and TRACED_RTL are factual evidence. INTERPRETATION marks your own judgement
call, and you must use it honestly — when a status turns on how the parser phrased something
rather than on what the RTL does, say INTERPRETATION. This distinction is what later separates
"the parser was inaccurate" from "the verifier made an interpretive call", so do not inflate
a judgement into DIRECT_RTL.

# What is under audit, and what is not
Audit exactly five things: functionality, each role, each relationship (type AND target),
and the evidence. The supplied `declared_type`, `declared_dir` and `declared_kind` are
CONTEXT to help you read the RTL -- they are NOT claims under audit. Do not raise errors
about them and do not mark a check UNVERIFIABLE because a type declaration is absent; judge
the behavioural claim instead.

# Claim-by-claim
Never judge the element with one global "correct"/"incorrect". Decompose:
- functionality — one status
- each role — its own status, independently
- each relationship (type AND target together) — its own status
- evidence — one status

## functionality
Check what the element actually carries; what assigns it; what reads it; whether it is
combinational or registered; whether it is captured or continuously propagated; what logic it
affects and what affects it; whether behavior changes under reset, under conditionals, or
under generate statements; and whether the description wrongly merges alternative
implementations into one unconditional description.

## roles
Verify each role independently. Ask whether the RTL supports it, whether it is too broad, and
whether it introduces semantics the RTL does not show. A signal being a control signal does
not by itself establish a role such as "security control" or "privilege control".

## relationships
Verify BOTH the type and the target. Take the type literally:
  CAPTURES     — a value stored on a clock edge
  DERIVES_FROM — computed from
  GATES        — controls whether another operation occurs
  SELECTS      — used to choose among alternatives
  SOURCES      — drives / is assigned into (x <= y supports SOURCES from y to x)
  CONSTRAINS   — bounds or limits
  CARRIES      — conveys a value across
  SEQUENCES    — clock-driven sequencing of state
The parser may use relationship types outside this list. Audit any such type literally, by its
plain meaning, on the same evidentiary standard. A type lying outside the list above is NOT by
itself an error and must never be reported as one — judge only whether the RTL supports the
stated dependency between the source element and the target.

Do not infer a relationship type merely because two signals appear in the same process. A
reset that overrides a register must NOT automatically be classified as SEQUENCES — if the
RTL shows `if rstn_i = '0' then ctrl <= ...`, then a claim `rstn_i SEQUENCES ctrl` is using
SEQUENCES to mean ordinary clock-driven sequencing and should be flagged.

## relationship targets
A relationship is wrong if the target is wrong even when the type is right. For each target:
confirm it exists, locate the connection, and determine whether the stated dependency
actually holds. If the target is only affected indirectly through another signal, do not
silently treat the indirect chain as a direct relationship — report the distinction and use
PARTIALLY_SUPPORTED.

## evidence — stricter than the prose
Locate the cited construct, confirm it exists, and confirm it actually supports the claim.
Distinguish "evidence exists" from "evidence proves the claim". `bus_req_o <= host_req_i`
supports a pass-through; it does not prove every field is separately consumed or interpreted.
Citing a process that merely contains rstn_i does not establish that rstn_i sequences a
register. Record the RTL location and say whether the evidence is direct or only indirect.

## conditionals, generates, active configuration
Pay attention to if / elsif / case / when / generate / generic-dependent branches /
constants controlling implementation style / reset branches. Do not merge mutually exclusive
behaviors into one unconditional description. If a constant such as
`constant alt_style_c : boolean := false;` gates an `if alt_style_c generate` block, behavior
inside that block is NOT active in the default configuration, and describing it as
unconditional is PARTIALLY_SUPPORTED or CONTRADICTED depending on severity. Do not assume
every branch is simultaneously active.

## reset
Distinguish asynchronous reset, synchronous reset, reset-driven override, and ordinary
clocked state update. Do not classify reset behavior as ordinary sequencing.

## combinational vs registered
Distinguish combinational, registered, latched, asynchronous, directly assigned, and derived.
Do not call a combinational wire persistent state. Do not call a registered signal a
transient combinational value. Do not infer persistence merely from participation in a
multi-cycle process.

## cross-entity
If a claim crosses an entity boundary, verify the instance port map, the source port and the
destination port, and distinguish direct RTL evidence from downstream inference. Do not
invent downstream behavior of another entity unless that entity's RTL was supplied.

# Deterministic inputs — three kinds, three different weights
- CONFIRMED MECHANICAL PROBLEMS: structural facts with no semantics involved (a duplicate
  record key, an entity with no declaration in the RTL set). Reliable.
- DETERMINISTIC FACTS: measurements — assignment style, reset-guarded assignment, generate
  guards, and the tier at which each symbol resolved. Reliable as measurements. They carry no
  verdict. In particular a symbol resolution of NOT_ESTABLISHED_BY_STATIC_CHECK means the
  static matcher failed, not that the symbol is absent from the design.
- REVIEW HINTS: questions only. See above. No presumption of error.

You decide every status yourself, from the RTL.

# Error categories — use exactly these
FUNCTIONALITY_ERROR, ROLE_ERROR, RELATIONSHIP_ERROR, RELATIONSHIP_TARGET_ERROR,
EVIDENCE_ERROR, MISSING_BEHAVIOR, CONDITIONAL_BEHAVIOR_ERROR, RESET_BEHAVIOR_ERROR,
COMBINATIONAL_REGISTER_ERROR, CROSS_ENTITY_ERROR, UNVERIFIABLE_FILE_MAPPING,
UNVERIFIABLE_CLAIM

Severity: CRITICAL (directly contradicts RTL) / MAJOR (materially changes the behavioral
interpretation) / MINOR (imprecise or incomplete, behavior unchanged) / NONE.

# Output — strict JSON only, no prose, no markdown fence
{
  "module": "...", "entity": "...", "element": "...",
  "functionality_check": {"status": "...", "evidence_type": "...", "confidence": 0.0,
                          "parser_claim": "...", "rtl_evidence": "...", "rtl_location": "...",
                          "rtl_trace": [{"step": "...", "rtl_location": "..."}],
                          "interpretation": ""},
  "role_checks": [{"role": "...", "status": "...", "evidence_type": "...", "confidence": 0.0,
                   "rtl_evidence": "...", "rtl_location": "...", "rtl_trace": [], "interpretation": ""}],
  "relationship_checks": [{"type": "...", "target": "...", "status": "...", "evidence_type": "...",
                           "confidence": 0.0, "rtl_evidence": "...", "rtl_location": "...",
                           "rtl_trace": [], "interpretation": ""}],
  "evidence_check": {"status": "...", "evidence_type": "...", "confidence": 0.0,
                     "parser_evidence": "...", "rtl_evidence": "...", "rtl_location": "...",
                     "rtl_trace": [], "interpretation": ""},
  "overall_status": "...", "overall_confidence": 0.0,
  "errors": [{"error_type": "...", "field": "...", "claim": "...", "status": "...",
              "rtl_evidence": "...", "rtl_location": "...", "severity": "...", "explanation": "..."}]
}

rtl_location must cite line numbers from the supplied excerpt, e.g. "L412-L418".
"errors" is [] when nothing is wrong. Emit one relationship_check per (type, target) pair.

`status` and `evidence_type` are two DIFFERENT fields with two DIFFERENT vocabularies. Do not
mix them up:
  "status"        takes ONLY: SUPPORTED | PARTIALLY_SUPPORTED | CONTRADICTED |
                              NOT_ESTABLISHED | UNVERIFIABLE      (the verdict)
  "evidence_type" takes ONLY: DIRECT_RTL | TRACED_RTL | INTERPRETATION  (how you know)
Putting DIRECT_RTL/TRACED_RTL/INTERPRETATION in "status", or a verdict in "evidence_type",
makes the whole response invalid. Every check object needs both fields, each from its own
list.

"confidence" is a number in [0,1] recording how firmly the RTL settles that status. It is a
diagnostic, NOT a substitute for evidence: every status still needs rtl_evidence and
rtl_location regardless of confidence. Never raise confidence to compensate for weak evidence,
and never use it to soften a status you cannot support. A CONTRADICTED at 0.99 must still
quote the RTL that contradicts the claim.

"rtl_trace" is required and non-empty when evidence_type is TRACED_RTL, and [] otherwise.
"interpretation" is required and non-empty when evidence_type is INTERPRETATION — state
plainly what the judgement was — and "" otherwise.
""".strip()

VERIFIER_PROMPT_SHA = hashlib.sha256(VERIFIER_SYSTEM.encode()).hexdigest()
print("verifier prompt", VERIFIER_PROMPT_VERSION, "sha", VERIFIER_PROMPT_SHA[:16],
      "|", len(VERIFIER_SYSTEM), "chars")

# scope guard: the verifier prompt must not carry asset/security vocabulary as an instruction
for bad in ["back_test", "C/I/A/U asset", "is an asset", "Confidentiality:"]:
    assert bad not in VERIFIER_SYSTEM, f"scope leak in verifier prompt: {bad}"
print("scope guard: clean")
''')

co(r'''
def build_user_payload(rec, ctx, ctx_meta, det_findings, det_facts, det_hints=None):
    claims = {
        "module": rec["module"], "entity": rec["entity"], "element": rec["name"],
        "declared_type": rec.get("type"), "declared_dir": rec.get("dir"),
        "declared_kind": rec.get("kind"),
        "function": rec.get("function"),
        "functionality": rec.get("functionality"),
        "role": rec.get("role"),
        "relationship": rec.get("relationship"),
        "evidence": rec.get("evidence"),
    }
    parts = [
        "## PARSER CLAIMS (hypothesis to be checked)",
        json.dumps(claims, indent=2, ensure_ascii=False),
        "",
        "## CONFIRMED MECHANICAL PROBLEMS (structural only, no semantics involved)",
        json.dumps(det_findings, indent=2, ensure_ascii=False) if det_findings else "[] (none)",
        "",
        "## DETERMINISTIC FACTS (measurements, no verdict attached)",
        json.dumps(det_facts, indent=2, ensure_ascii=False) if det_facts else "{}",
        "",
        "## REVIEW HINTS — these are QUESTIONS, NOT findings of error.",
        "A hint means a static check noticed something worth your attention. It is NOT",
        "evidence that the parser is wrong. Answer each question from the RTL below. If",
        "the RTL supports the parser, say SUPPORTED regardless of the hint.",
        json.dumps(det_hints or [], indent=2, ensure_ascii=False) if det_hints else "[] (none)",
        "",
        f"## RTL EXCERPT — file {ctx_meta.get('rtl_file')}, "
        f"architecture lines {ctx_meta.get('arch_span')}, "
        f"truncated={ctx_meta.get('truncated')}",
        "Line numbers are 1-based from the original file. `...` marks elided regions.",
        "",
        ctx if ctx else "(NO RTL COULD BE MAPPED FOR THIS ENTITY)",
        "",
        # REQUIRED by the Responses API: with text.format=json_object the literal
        # word "json" must appear in `input`. It is not enough for `instructions`
        # to say JSON -- the check runs against the input messages, and omitting
        # it fails every call with HTTP 400 before any tokens are billed.
        "Return your audit as a single json object exactly matching the schema given in the "
        "instructions. Output json only — no prose, no markdown fence.",
    ]
    return "\n".join(parts)

_payload = build_user_payload(_probe, _c, _m, _f, _facts, _hints)
assert_no_prior_results_used(_payload, "probe payload")
print(_payload[:900])
print("\n... payload chars:", len(_payload))
''')

# ------------------------------------------------------------------ client
md(r"""
## 7. API client and response validation

Matches the client used for generation: OpenAI **Responses API** with `instructions` /
`input`, `reasoning={"effort": ...}`, `max_output_tokens`, JSON-object output, per-call token
accounting and a USD cost report.

**No temperature, no seed.** Reasoning models reject both. The knob is `reasoning_effort`, and
run-to-run stability comes from the response cache — keyed on
`sha256(provider + model + effort + reasoning_flag + max_tokens + prompt_sha + payload)`.
The manifest says this outright rather than implying determinism the API cannot give.

**Budget escalation.** For a reasoning model the reasoning trace shares `max_output_tokens`
with the answer, so a verbose schema can consume the whole budget and return empty text. That
is a budget problem, not a model failure, and booking it as `parse_error` would corrupt the
parse-error rate. On `status == "incomplete"` the call retries at double the budget up to
`max_output_tokens_ceiling`; escalations, and anything still incomplete at the ceiling, are
counted and reported.

`max_output_tokens` defaults to 6000 rather than something smaller because this schema emits a
check per role and per relationship target, each with `rtl_evidence`, `rtl_location`,
`rtl_trace` and `interpretation`.

Failures are recorded, never silently skipped. Malformed JSON is stored raw and marked
`parse_error` so genuine parse failures stay measurable.
""")

co(r'''
class TransientError(Exception): pass
STATUSES = {"SUPPORTED","PARTIALLY_SUPPORTED","CONTRADICTED","NOT_ESTABLISHED","UNVERIFIABLE"}
ERROR_TYPES = {"FUNCTIONALITY_ERROR","ROLE_ERROR","RELATIONSHIP_ERROR","RELATIONSHIP_TARGET_ERROR",
               "EVIDENCE_ERROR","MISSING_BEHAVIOR","CONDITIONAL_BEHAVIOR_ERROR","RESET_BEHAVIOR_ERROR",
               "COMBINATIONAL_REGISTER_ERROR","CROSS_ENTITY_ERROR","UNVERIFIABLE_FILE_MAPPING",
               "UNVERIFIABLE_CLAIM"}
SEVERITIES = {"CRITICAL","MAJOR","MINOR","NONE"}
EVIDENCE_TYPES = {"DIRECT_RTL","TRACED_RTL","INTERPRETATION"}

def _cache_key(payload, cfg):
    """Effort replaces temperature/seed: those are the knobs that actually vary
    the output for a reasoning model."""
    h = hashlib.sha256()
    for p in [cfg["provider"], cfg["model"], str(cfg["reasoning_effort"]),
              str(USE_REASONING), str(cfg["max_output_tokens"]),
              VERIFIER_PROMPT_SHA, payload]:
        h.update(p.encode("utf-8")); h.update(b"\x00")
    return h.hexdigest()

USAGE = []          # per-call token accounting, same shape as the generation client

def _call(system, user, cfg, max_tokens=None):
    max_tokens = max_tokens or cfg["max_output_tokens"]
    if cfg["provider"] == "openai":
        from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError, InternalServerError
        cl = OpenAI(api_key=API_KEY, timeout=cfg["request_timeout_s"])
        kw = dict(model=cfg["model"], instructions=system, input=user,
                  max_output_tokens=max_tokens,
                  text={"format": {"type": "json_object"}})
        if USE_REASONING:
            kw["reasoning"] = {"effort": cfg["reasoning_effort"]}
        try:
            r = cl.responses.create(**kw)
        except (APITimeoutError, APIConnectionError, RateLimitError, InternalServerError) as e:
            raise TransientError(f"{type(e).__name__}: {e}")
        u = r.usage
        rt = getattr(getattr(u, "output_tokens_details", None), "reasoning_tokens", 0) or 0
        ci = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
        usage = {"model": cfg["model"], "in": u.input_tokens, "out": u.output_tokens,
                 "reasoning": rt, "cached_in": ci,
                 "incomplete": getattr(r, "status", None) == "incomplete",
                 "incomplete_reason": getattr(getattr(r, "incomplete_details", None),
                                              "reason", None),
                 "budget": max_tokens}
        USAGE.append(usage)
        return (r.output_text or ""), usage
    elif cfg["provider"] == "anthropic":
        import anthropic
        cl = anthropic.Anthropic(api_key=API_KEY, timeout=cfg["request_timeout_s"])
        try:
            r = cl.messages.create(model=cfg["model"], system=system,
                                   messages=[{"role":"user","content":user}],
                                   temperature=cfg["temperature"],
                                   max_tokens=cfg["max_output_tokens"])
        except (anthropic.APITimeoutError, anthropic.APIConnectionError,
                anthropic.RateLimitError, anthropic.InternalServerError) as e:
            raise TransientError(f"{type(e).__name__}: {e}")
        usage = {"model": cfg["model"], "in": r.usage.input_tokens,
                 "out": r.usage.output_tokens, "reasoning": 0, "cached_in": 0,
                 "incomplete": False, "incomplete_reason": None, "budget": max_tokens}
        USAGE.append(usage)
        return "".join(b.text for b in r.content if getattr(b,"type","")=="text"), usage
    raise ValueError(f"unknown provider {cfg['provider']!r}")

def call_with_retry(system, user, cfg):
    """Retries transient errors with exponential backoff, and separately escalates
    the output budget when the model ran out of tokens mid-answer. For a reasoning
    model the reasoning trace shares `max_output_tokens`, so a verbose schema can
    consume the whole budget and return empty text -- that is a budget problem, not
    a model failure, and must not be recorded as a parse error."""
    last, budget, escalations = None, cfg["max_output_tokens"], 0
    for a in range(cfg["max_retries"]):
        try:
            t0 = time.time(); txt, usage = _call(system, user, cfg, max_tokens=budget)
            if usage.get("incomplete") and cfg["escalate_on_incomplete"] \
               and budget < cfg["max_output_tokens_ceiling"]:
                budget = min(budget * 2, cfg["max_output_tokens_ceiling"])
                escalations += 1
                print(f"    [llm warn] incomplete ({usage.get('incomplete_reason')}) "
                      f"-> retrying at max_output_tokens={budget}")
                continue
            return {"text": txt, "usage": usage, "latency_s": round(time.time()-t0,3),
                    "retries": a, "escalations": escalations, "error": None,
                    "incomplete": bool(usage.get("incomplete"))}
        except TransientError as e:
            last = str(e)
            time.sleep(min(cfg["backoff_cap_s"], cfg["backoff_base_s"]*(2**a))*(0.5+random.random()/2))
        except Exception as e:
            return {"text":"","usage":{},"latency_s":0.0,"retries":a,
                    "escalations":escalations,"error":f"{type(e).__name__}: {e}",
                    "incomplete":False}
    return {"text":"","usage":{},"latency_s":0.0,"retries":cfg["max_retries"],
            "escalations":escalations,"incomplete":False,
            "error":f"exhausted retries: {last}"}

def cost(cfg=CONFIG, usage=None):
    """USD for calls so far, at per-1M-token prices."""
    us = USAGE if usage is None else usage
    i  = sum(u["in"] - u.get("cached_in", 0) for u in us)
    c  = sum(u.get("cached_in", 0) for u in us)
    o  = sum(u["out"] for u in us)
    rt = sum(u.get("reasoning", 0) for u in us)
    total = (i*cfg["price_in"] + c*cfg["price_cached_in"] + o*cfg["price_out"]) / 1e6
    return {"calls": len(us), "in": i, "cached_in": c, "out": o, "reasoning": rt,
            "incomplete": sum(1 for u in us if u.get("incomplete")),
            "usd": round(total, 4)}

def project_cost(n_elements, cfg=CONFIG):
    """Extrapolate a full run from calls made so far. Only meaningful after a pilot."""
    if not USAGE: return {"note": "no calls yet"}
    c = cost(cfg); per = c["usd"] / max(1, c["calls"])
    return {"calls_so_far": c["calls"], "usd_so_far": c["usd"],
            "usd_per_call": round(per, 5),
            f"projected_usd_for_{n_elements}": round(per * n_elements, 2)}

def validate_verification(raw):
    """Strict. No silent repair."""
    if not raw or not raw.strip(): return None, "parse_error", "empty response"
    t = raw.strip()
    if t.startswith("```"): t = re.sub(r"^```(?:json)?\s*|\s*```$","",t,flags=re.S).strip()
    try: o = json.loads(t)
    except Exception as e: return None, "parse_error", f"json decode: {e}"
    if not isinstance(o, dict): return None, "parse_error", "top level not an object"
    for k in ["functionality_check","evidence_check"]:
        if not isinstance(o.get(k), dict): return None, "parse_error", f"missing {k}"
        if o[k].get("status") not in STATUSES:
            return None, "parse_error", f"{k}.status={o[k].get('status')!r}"
    for k in ["role_checks","relationship_checks","errors"]:
        if not isinstance(o.get(k), list): return None, "parse_error", f"{k} not a list"
    for c in o["role_checks"] + o["relationship_checks"]:
        if not isinstance(c, dict) or c.get("status") not in STATUSES:
            return None, "parse_error", f"bad check status {c!r}"[:120]
    if o.get("overall_status") not in STATUSES:
        return None, "parse_error", f"overall_status={o.get('overall_status')!r}"
    # evidence_type IS part of the audit contract -- it separates fact from the
    # verifier's own judgement -- so it is enforced strictly, no repair.
    missing_conf, deep_traces = [], []
    for label, node in ([("functionality", o["functionality_check"]),
                         ("evidence", o["evidence_check"])]
                        + [(f"role[{i}]", c) for i, c in enumerate(o["role_checks"])]
                        + [(f"rel[{i}]", c) for i, c in enumerate(o["relationship_checks"])]):
        et = node.get("evidence_type")
        if et not in EVIDENCE_TYPES:
            return None, "parse_error", f"{label}.evidence_type={et!r} not in {sorted(EVIDENCE_TYPES)}"
        tr = node.get("rtl_trace", [])
        if tr is None: tr = []
        if not isinstance(tr, list):
            return None, "parse_error", f"{label}.rtl_trace is not a list"
        for st in tr:
            if not isinstance(st, dict) or "rtl_location" not in st:
                return None, "parse_error", f"{label}.rtl_trace step missing rtl_location"
        # Depth >3 is recorded, not fatal. The drift guard targets INFERENCE depth,
        # but models legitimately use trace steps to enumerate several evidence
        # locations for one step. Failing those discarded 25% of a valid smoke run.
        if len(tr) > 6:
            return None, "parse_error", f"{label}.rtl_trace has {len(tr)} steps, hard cap is 6"
        if len(tr) > 3:
            deep_traces.append(f"{label}:{len(tr)}")
        if et == "TRACED_RTL" and not tr:
            return None, "parse_error", f"{label}.evidence_type=TRACED_RTL but rtl_trace is empty"
        if et == "INTERPRETATION" and not str(node.get("interpretation", "")).strip():
            return None, "parse_error", f"{label}.evidence_type=INTERPRETATION but interpretation is empty"
        node["rtl_trace"] = tr
        # confidence is a diagnostic, not contract. Validate when present; record
        # absence explicitly rather than discarding an otherwise valid audit.
        c = node.get("confidence")
        if c is None:
            missing_conf.append(label); continue
        if not isinstance(c, (int, float)) or not (0.0 <= float(c) <= 1.0):
            return None, "parse_error", f"{label}.confidence={c!r} not a number in [0,1]"
        node["confidence"] = float(c)
    oc = o.get("overall_confidence")
    if oc is not None and (not isinstance(oc, (int, float)) or not (0.0 <= float(oc) <= 1.0)):
        return None, "parse_error", f"overall_confidence={oc!r} not a number in [0,1]"
    if oc is None: missing_conf.append("overall")
    o["_confidence_missing"] = missing_conf
    o["_trace_depth_over_3"] = deep_traces
    for e in o["errors"]:
        if not isinstance(e, dict): return None, "parse_error", "error entry not an object"
        if e.get("error_type") not in ERROR_TYPES:
            return None, "parse_error", f"error_type={e.get('error_type')!r}"
        if e.get("severity") not in SEVERITIES:
            return None, "parse_error", f"severity={e.get('severity')!r}"
        if e.get("status") not in STATUSES:
            return None, "parse_error", f"error.status={e.get('status')!r}"
    return o, "ok", ""
print("client ready | provider:", CONFIG["provider"], "| model:", CONFIG["model"],
      "| reasoning:", USE_REASONING)
print("validator ready | statuses:", len(STATUSES), "| evidence types:", sorted(EVIDENCE_TYPES))
''')

# ------------------------------------------------------------------ run
md("## 8. Verification runner")

co(r'''
from concurrent.futures import ThreadPoolExecutor, as_completed

def verify_element(rec, cfg=CONFIG):
    ctx, meta = rtl_context_for(rec, cfg)
    det = DET.get(rec["element_id"]) or {}
    findings, facts = det.get("findings", []), det.get("facts", {})
    hints = det.get("hints", [])

    # entity unmappable -> deterministic UNVERIFIABLE, no API call
    if meta["mapping"] != "MAPPED":
        return {"element_id": rec["element_id"], "module": rec["module"],
                "entity": rec["entity"], "element": rec["name"],
                "rtl_file": None, "parse_status": "ok", "parse_detail": "",
                "cached": False, "api_error": None, "latency_s": 0.0, "retries": 0,
                "verification": {"module": rec["module"], "entity": rec["entity"],
                    "element": rec["name"],
                    "functionality_check": {"status":"UNVERIFIABLE","evidence_type":"DIRECT_RTL",
                                            "confidence":0.0,"parser_claim":rec.get("functionality"),
                                            "rtl_evidence":"","rtl_location":"","rtl_trace":[],
                                            "interpretation":""},
                    "role_checks": [{"role":r,"status":"UNVERIFIABLE","evidence_type":"DIRECT_RTL",
                                     "confidence":0.0,"rtl_evidence":"","rtl_location":"",
                                     "rtl_trace":[],"interpretation":""} for r in rec["role"]],
                    "relationship_checks": [{"type":x.get("type"),"target":t,"status":"UNVERIFIABLE",
                                             "evidence_type":"DIRECT_RTL","confidence":0.0,
                                             "rtl_evidence":"","rtl_location":"","rtl_trace":[],
                                             "interpretation":""}
                                            for x in rec["relationship"] for t in (x.get("targets") or [])],
                    "evidence_check": {"status":"UNVERIFIABLE","evidence_type":"DIRECT_RTL",
                                       "confidence":0.0,"parser_evidence":rec.get("evidence"),
                                       "rtl_evidence":"","rtl_location":"","rtl_trace":[],
                                       "interpretation":""},
                    "overall_status": "UNVERIFIABLE",
                    "errors": [{"error_type":"UNVERIFIABLE_FILE_MAPPING","field":"entity",
                                "claim":rec["entity"],"status":"UNVERIFIABLE","rtl_evidence":"",
                                "rtl_location":"","severity":"NONE",
                                "explanation":"No `entity <name> is` declaration found in the RTL dataset; not guessed."}]},
                "deterministic_findings": findings, "raw_response": ""}

    payload = build_user_payload(rec, ctx, meta, findings, facts, hints)
    assert_no_prior_results_used(payload, f"payload for {rec['element_id']}")
    key = _cache_key(payload, cfg)
    cp = CACHE_DIR / key[:2] / (key + ".json")
    if cfg["cache_enabled"] and cp.exists():
        d = json.loads(cp.read_text(encoding="utf-8")); d["cached"] = True; return d

    res = call_with_retry(VERIFIER_SYSTEM, payload, cfg)
    parsed, status, detail = validate_verification(res["text"])
    row = {"element_id": rec["element_id"], "module": rec["module"], "entity": rec["entity"],
           "element": rec["name"], "rtl_file": meta.get("rtl_file"),
           "parse_status": status, "parse_detail": detail, "cached": False,
           "api_error": res["error"], "latency_s": res["latency_s"], "retries": res["retries"],
           "escalations": res.get("escalations", 0), "incomplete": res.get("incomplete", False),
           "usage": res.get("usage", {}),
           "verification": parsed, "deterministic_findings": findings,
           "raw_response": res["text"]}
    # Cache RESULTS, not failures. A parse_error is a real observation about the
    # model's output and is cached so the rate stays measurable. An API-level
    # failure (4xx/5xx, exhausted retries) is not a result -- caching it would
    # freeze a transient or configuration fault permanently into the run.
    if res["error"] is None:
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
    else:
        print(f"    [not cached] {rec['module']}/{rec['name']}: {str(res['error'])[:110]}")
    return row

def run_verification(records=None, cfg=CONFIG, limit=None, show_every=25):
    recs = records if records is not None else PARSED
    if limit: recs = recs[:limit]
    out, done = [], 0
    with ThreadPoolExecutor(max_workers=cfg["parallel_workers"]) as ex:
        futs = [ex.submit(verify_element, r, cfg) for r in recs]
        for f in as_completed(futs):
            out.append(f.result()); done += 1
            if done % show_every == 0: print(f"  {done}/{len(recs)}", flush=True)
    ok  = sum(1 for o in out if o["parse_status"] == "ok")
    esc = sum(o.get("escalations", 0) for o in out)
    inc = sum(1 for o in out if o.get("incomplete"))
    print(f"verified {len(out)} | parsed_ok {ok/max(1,len(out)):.1%} | "
          f"cached {sum(1 for o in out if o.get('cached'))} | "
          f"budget escalations {esc} | still incomplete {inc}")
    if inc:
        print(f"  !! {inc} response(s) hit the token ceiling. Raise "
              f"max_output_tokens_ceiling or lower reasoning_effort.")
    print("  cost so far:", json.dumps(cost(cfg)))
    return out
print("run_verification() ready")
''')

md(r"""
### Reset-hint distribution

512 reset hints only matters if they sit on the claims that are actually interesting. The
section-12 case is a **reset signal claimed to SEQUENCE a register**; a reset assignment
merely appearing somewhere downstream of an ordinary signal is far weaker. This splits them.
""")

co(r'''
def reset_hint_distribution():
    rows = []
    for r in PARSED:
        d = DET.get(r["element_id"]) or {}
        if not any(h["hint"] == "target_assigned_in_reset_branch" for h in d.get("hints", [])):
            continue
        src_reset = bool(re.search(r"(?i)(^|_)(rstn?|reset)(_|$|\d)", str(r["name"])))
        for rel in r["relationship"]:
            t = str(rel.get("type", "")).upper()
            for tgt in (rel.get("targets") or []):
                info = ((d.get("facts") or {}).get("targets") or {}).get(str(tgt)) or {}
                if not info.get("assigned_under_reset"): continue
                if src_reset and t == "SEQUENCES":   cat = "reset source -> SEQUENCES"
                elif src_reset:                      cat = f"reset source -> {t}"
                elif t == "SEQUENCES":               cat = "non-reset source -> SEQUENCES"
                elif t == "CAPTURES":                cat = "non-reset source -> CAPTURES"
                else:                                cat = f"non-reset source -> {t}"
                rows.append({"category": cat, "module": r["module"], "entity": r["entity"],
                             "element": r["name"], "type": t, "target": str(tgt)})
    df_ = pd.DataFrame(rows)
    if not len(df_):
        print("no reset hints"); return df_
    summ = df_.groupby("category").size().reset_index(name="count").sort_values("count", ascending=False)
    print("reset-related review hints by category:")
    for _, x in summ.iterrows(): print("   %-40s %5d" % (x["category"], x["count"]))
    print()
    top = df_[df_.category == "reset source -> SEQUENCES"]
    print(f"the genuinely interesting category (reset source -> SEQUENCES): {len(top)}")
    for _, x in top.head(8).iterrows():
        print(f"   {x['module']}/{x['entity']}/{x['element']} SEQUENCES -> {x['target']}")
    return df_

RESET_DIST = reset_hint_distribution()
''')

md(r"""
## 8b. Curated smoke set — inspect before spending 1689 calls

The point of this sample is **not** to measure accuracy. It is to check that the verifier
behaves like an auditor rather than a second parser or an error generator. Read the four
columns together: parser claim → deterministic facts → the verifier's RTL evidence → its
status and reasoning.

The set is chosen to cover the cases most likely to expose bad behaviour:

| case | why it is in the set |
|---|---|
| a reset port (`rstn_i`) | the section-12 `SEQUENCES` trap |
| a generate-dependent element (`addr_ff`, `alt_style_c=false`) | inactive-branch-as-active |
| an ordinary data/address field | the baseline; over-flagging shows up here |
| a record field resolving via the package | tests the resolution hierarchy |
| a relationship using a non-spec type | must not be called an error for that reason |
| an element with an unresolved evidence citation | must yield NOT_ESTABLISHED, not CONTRADICTED |
""")

co(r'''
def build_smoke_set():
    picked, seen = [], set()
    def take(rec, why):
        if rec is None or rec["element_id"] in seen: return
        seen.add(rec["element_id"]); picked.append((why, rec))
    def first(pred):
        return next((r for r in PARSED if pred(r)), None)

    take(first(lambda r: re.fullmatch(r"(?i)rstn?_i", str(r["name"])) and
               any(str(x.get("type","")).upper() == "SEQUENCES" for x in r["relationship"])),
         "reset port with a SEQUENCES claim")
    take(first(lambda r: str(r["name"]) == "addr_ff"), "generate-dependent element")
    take(first(lambda r: any((DET.get(r["element_id"]) or {}).get("hints", []) and
               h["hint"] == "target_in_generate_branch"
               for h in (DET.get(r["element_id"]) or {}).get("hints", []))),
         "target under a generate guard")
    take(first(lambda r: str(r["name"]).endswith(".addr") and r["relationship"]),
         "ordinary address field (baseline)")
    take(first(lambda r: any(h["hint"] == "evidence_citation_resolved_elsewhere"
               for h in (DET.get(r["element_id"]) or {}).get("hints", []))),
         "citation resolving via package / other entity")
    take(first(lambda r: any(str(x.get("type","")).upper() not in SPEC_TYPES
               for x in r["relationship"])), "relationship using a non-spec type")
    take(first(lambda r: any(h["hint"] == "evidence_citation_unresolved_by_static_check"
               for h in (DET.get(r["element_id"]) or {}).get("hints", []))),
         "unresolved evidence citation (must be NOT_ESTABLISHED, not CONTRADICTED)")
    take(first(lambda r: not r["relationship"]), "element with no relationships")
    return picked

SMOKE_SET = build_smoke_set()
print(f"curated smoke set: {len(SMOKE_SET)} elements\n")
for why, r in SMOKE_SET:
    print(f"  {why:56s} {r['module']}/{r['entity']}/{r['name']}")
''')

co(r'''
# ---- run the curated smoke set (one API call each) ----------------------------
# COMMENTED OUT after a clean 8/8 pass. Re-enable only if the verifier prompt,
# the payload builder, or the RTL context extractor changes -- any of those
# invalidates the cache and the smoke set is the cheapest way to re-validate.
SMOKE_ENABLED = False

if not SMOKE_ENABLED:
    print("smoke set disabled (SMOKE_ENABLED = False). Last result: 8/8 parsed, "
          "0 API errors, 0 escalations, max trace depth 3.")
    print(f"{len(SMOKE_SET)} elements are selected and ready if you re-enable it.")
else:
    SMOKE = run_verification([r for _, r in SMOKE_SET], show_every=1)

def inspect(results, smoke_set):
    idx = {r["element_id"]: (why, r) for why, r in smoke_set}
    for res in results:
        why, rec = idx.get(res["element_id"], ("", {}))
        v = res.get("verification") or {}
        print("=" * 100)
        print(f"[{why}]  {res['module']}/{res['entity']}/{res['element']}   file={res['rtl_file']}")
        print(f"  PARSER functionality : {str(rec.get('functionality'))[:190]}")
        print(f"  PARSER roles         : {rec.get('role')}")
        print(f"  PARSER relationships : {rec.get('relationship')}")
        print(f"  PARSER evidence      : {str(rec.get('evidence'))[:190]}")
        d = DET.get(res["element_id"]) or {}
        print(f"  DET hints            : {[h['hint'] for h in d.get('hints', [])] or 'none'}")
        print(f"  DET facts            : style={(d.get('facts') or {}).get('assignment_style_of_element')}")
        if res["parse_status"] != "ok":
            print(f"  !! PARSE ERROR: {res['parse_detail']}\n  raw: {res['raw_response'][:300]}")
            continue
        fc = v.get("functionality_check", {})
        print(f"  VERIFIER functionality: {fc.get('status')} [{fc.get('evidence_type')}] "
              f"conf={fc.get('confidence')}")
        print(f"     rtl_evidence: {str(fc.get('rtl_evidence'))[:170]}")
        print(f"     rtl_location: {fc.get('rtl_location')}   trace={len(fc.get('rtl_trace') or [])} hops")
        if fc.get("interpretation"): print(f"     interpretation: {fc['interpretation'][:170]}")
        for c in v.get("relationship_checks", []):
            print(f"  VERIFIER rel {c.get('type')} -> {c.get('target')}: {c.get('status')} "
                  f"[{c.get('evidence_type')}] @ {c.get('rtl_location')}")
            print(f"     {str(c.get('rtl_evidence'))[:170]}")
        ec = v.get("evidence_check", {})
        print(f"  VERIFIER evidence     : {ec.get('status')} [{ec.get('evidence_type')}]")
        print(f"  OVERALL               : {v.get('overall_status')}  errors={len(v.get('errors') or [])}")
        for e in (v.get("errors") or []):
            print(f"     - {e.get('error_type')} / {e.get('severity')} / {e.get('status')}: "
                  f"{str(e.get('explanation'))[:180]}")

    inspect(SMOKE, SMOKE_SET)
    print("=" * 100)
    print("token usage / cost for the smoke set:")
    print(json.dumps(cost(), indent=2))
    print()
    print("projected full run:")
    print(json.dumps(project_cost(len(PARSED)), indent=2))
''')

md(r"""
**What to look for, in order of importance**

1. Does any status say `CONTRADICTED` where the RTL merely fails to show something? That is
   the failure mode the whole design guards against.
2. Did a review hint get echoed back as the justification? Justifications must cite RTL.
3. Is the non-spec relationship type treated as an error *because* it is non-spec?
4. Is `evidence_type` honest — are `INTERPRETATION` calls labelled as such, or dressed up as
   `DIRECT_RTL`?
5. Does `rtl_trace` actually contain the hops, and do the line numbers land on real statements?
6. On the ordinary address field, is the verifier inventing problems? Over-flagging the
   baseline case means the prompt is still pushing toward error generation.

If those all look right, scale up. If not, fix the prompt before spending the full run.
""")

# ------------------------------------------------------------------ aggregate
md(r"""
## 9. Aggregation and recurring error patterns

Section 21 of the spec: aggregate recurring parser errors so the **parser prompt** can be
improved. The output describes patterns; it never rewrites the prompt automatically.

Pattern detection is deterministic — it reads the verifier's own structured fields plus the
deterministic facts, so a pattern count is reproducible rather than a second LLM judgement.
""")

co(r'''
def flatten(results):
    rows = []
    for r in results:
        v = r.get("verification") or {}
        base = {k: r[k] for k in ["element_id","module","entity","element","rtl_file",
                                  "parse_status","cached"]}
        rows.append({**base, "field": "functionality", "claim_key": "",
                     "status": (v.get("functionality_check") or {}).get("status"),
                     "overall": v.get("overall_status")})
        for c in v.get("role_checks", []) or []:
            rows.append({**base, "field": "role", "claim_key": c.get("role"),
                         "status": c.get("status"), "overall": v.get("overall_status")})
        for c in v.get("relationship_checks", []) or []:
            rows.append({**base, "field": "relationship",
                         "claim_key": f"{c.get('type')} -> {c.get('target')}",
                         "status": c.get("status"), "overall": v.get("overall_status")})
        rows.append({**base, "field": "evidence", "claim_key": "",
                     "status": (v.get("evidence_check") or {}).get("status"),
                     "overall": v.get("overall_status")})
    return pd.DataFrame(rows)

def error_summary(results):
    c = Counter(); sev = Counter()
    for r in results:
        for e in ((r.get("verification") or {}).get("errors") or []):
            c[e.get("error_type")] += 1; sev[(e.get("error_type"), e.get("severity"))] += 1
    return {"error_summary": dict(c.most_common()),
            "by_severity": {f"{k[0]}|{k[1]}": v for k, v in sev.most_common()}}

PATTERNS = {
 "async_reset_labeled_SEQUENCES":
   lambda r, d: any(f["check"]=="target_assigned_under_reset" for f in d),
 "inactive_generate_branch_described_as_active":
   lambda r, d: any(f["check"]=="target_in_generate_branch" and "False" in f["detail"] for f in d),
 "relationship_target_absent_from_rtl":
   lambda r, d: any(f["check"]=="target_not_found_in_rtl" for f in d),
 "evidence_cites_symbol_absent_from_rtl":
   lambda r, d: any(f["check"]=="evidence_symbol_not_found" for f in d),
 "element_name_absent_from_rtl":
   lambda r, d: any(f["check"]=="name_not_found_in_rtl" for f in d),
 "relationship_type_outside_spec_vocabulary":
   lambda r, d: any(f["check"]=="type_outside_spec_vocabulary" for f in d),
 "indirect_dependency_as_direct":
   lambda r, d: any(c.get("status")=="PARTIALLY_SUPPORTED"
                    for c in ((r.get("verification") or {}).get("relationship_checks") or [])),
 "combinational_described_as_state":
   lambda r, d: any(e.get("error_type")=="COMBINATIONAL_REGISTER_ERROR"
                    for e in ((r.get("verification") or {}).get("errors") or [])),
 "omitted_conditional_branch":
   lambda r, d: any(e.get("error_type")=="CONDITIONAL_BEHAVIOR_ERROR"
                    for e in ((r.get("verification") or {}).get("errors") or [])),
 "reset_behavior_misdescribed":
   lambda r, d: any(e.get("error_type")=="RESET_BEHAVIOR_ERROR"
                    for e in ((r.get("verification") or {}).get("errors") or [])),
 "parser_claims_use_of_unused_field":
   lambda r, d: any(e.get("error_type")=="MISSING_BEHAVIOR"
                    for e in ((r.get("verification") or {}).get("errors") or [])),
}

def pattern_report(results):
    hits = Counter(); examples = defaultdict(list)
    for r in results:
        d = r.get("deterministic_findings", []) or []
        for name, fn in PATTERNS.items():
            try: ok = fn(r, d)
            except Exception: ok = False
            if ok:
                hits[name] += 1
                if len(examples[name]) < 5:
                    examples[name].append(f"{r['module']}/{r['entity']}/{r['element']}")
    return pd.DataFrame([{"pattern": k, "count": v, "examples": ", ".join(examples[k])}
                         for k, v in hits.most_common()])

def status_table(flat):
    t = flat.pivot_table(index="field", columns="status", values="element_id",
                         aggfunc="count", fill_value=0)
    t["total"] = t.sum(axis=1)
    for s in ["SUPPORTED","PARTIALLY_SUPPORTED","CONTRADICTED","NOT_ESTABLISHED","UNVERIFIABLE"]:
        if s in t.columns: t[s+"_pct"] = (100*t[s]/t["total"]).round(1)
    return t
print("aggregation ready")
''')

# ------------------------------------------------------------------ save
md("## 10. Save results and manifest (never overwrite; never touch data/)")

co(r'''
def save_run(results, cfg=CONFIG, note=""):
    # HARD GUARANTEE: nothing is written under data/
    assert Path(cfg["parsed_dir"]).resolve() not in RUN_DIR.resolve().parents, "would write into data/"
    per = RUN_DIR / "per_file"; per.mkdir(exist_ok=True)
    by = defaultdict(list)
    for r in results:
        src = next((x["source_file"] for x in PARSED if x["element_id"] == r["element_id"]), "unknown.json")
        by[src].append(r)
    for src, rows in by.items():
        (per / f"{Path(src).stem}_verification.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    flat = flatten(results)
    flat.to_csv(RUN_DIR / "claim_status.csv", index=False)
    status_table(flat).to_csv(RUN_DIR / "status_by_field.csv")
    pattern_report(results).to_csv(RUN_DIR / "error_patterns.csv", index=False)
    (RUN_DIR / "error_summary.json").write_text(
        json.dumps(error_summary(results), indent=2), encoding="utf-8")
    (RUN_DIR / "verifier_prompt.md").write_text(VERIFIER_SYSTEM, encoding="utf-8")

    try:
        git = subprocess.run(["git","rev-parse","HEAD"], capture_output=True, text=True,
                             cwd=str(HERE)).stdout.strip() or None
    except Exception: git = None
    manifest = {
        "run_dir": RUN_DIR.name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "note": note, "git_commit": git, "python": sys.version.split()[0],
        "parser_prompt_version": cfg["parser_prompt_version"],
        "parsed_data_version": cfg["parsed_data_version"],
        "rtl_dataset_version": cfg["rtl_dataset_version"],
        "verifier_prompt_version": VERIFIER_PROMPT_VERSION,
        "verifier_prompt_sha256": VERIFIER_PROMPT_SHA,
        "llm": {"provider": cfg["provider"], "model": cfg["model"],
                "reasoning": USE_REASONING,
                "reasoning_effort": cfg["reasoning_effort"] if USE_REASONING else None,
                "max_output_tokens": cfg["max_output_tokens"],
                "max_output_tokens_ceiling": cfg["max_output_tokens_ceiling"],
                "note": "Responses API; reasoning models accept no temperature or seed, "
                        "so run-to-run determinism comes from the response cache"},
        "usage_and_cost": cost(cfg),
        "prices_per_1m": {"in": cfg["price_in"], "cached_in": cfg["price_cached_in"],
                          "out": cfg["price_out"]},
        "counts": {"elements_verified": len(results),
                   "parse_ok": int(sum(1 for r in results if r["parse_status"]=="ok")),
                   "budget_escalations": int(sum(r.get("escalations",0) for r in results)),
                   "still_incomplete": int(sum(1 for r in results if r.get("incomplete"))),
                   "unverifiable_mapping": int(sum(
                       1 for r in results if (r.get("verification") or {}).get("overall_status")=="UNVERIFIABLE"))},
        "inputs": [{"json": s, "rtl": sorted({r["rtl_file"] for r in rows if r["rtl_file"]}),
                    "n_elements": len(rows)} for s, rows in sorted(by.items())],
        "rtl_sha256": {k: v["sha256"][:16] for k, v in RTL_FILES.items()},
        "anti_drift": "no prior verification result was read as evidence; guard asserted per payload",
    }
    (RUN_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("saved ->", RUN_DIR)
    return manifest

# MANIFEST = save_run(RESULTS, note="first full verification pass")
print("save_run() ready")
''')

md(r"""
## 11. Full run

Running the notebook top-to-bottom stops after the **8-call smoke set**. The full pass is
deliberately left commented so it cannot fire by accident.

Work up in stages — each stage is cached, so nothing is ever paid for twice:
""")

co(r'''
# =============================================================================
#  STAGE = 0  -> no API calls. Prints the plan and per-module counts only.
#  STAGE = 1  -> one module (set MOD). ~27 calls for neorv32_imem, ~$0.20.
#  STAGE = 2  -> full pass, 1689 elements, ~$13. Resumable; cached calls are free.
# =============================================================================
STAGE = 0
MOD   = "neorv32_imem"

if STAGE == 0:
    print("STAGE = 0 : no API calls will be made. Set STAGE = 1 or 2 to run.")
elif STAGE in (1, 2):
    todo = [r for r in PARSED if r["module"] == MOD] if STAGE == 1 else PARSED
    label = f"module {MOD}" if STAGE == 1 else "full pass"
    print(f"STAGE {STAGE}: {label} -> {len(todo)} elements "
          f"(cached ones cost nothing)\n")
    RESULTS = run_verification(todo)
    flat = flatten(RESULTS)
    display(status_table(flat))
    display(pattern_report(RESULTS))
    print(json.dumps(error_summary(RESULTS), indent=2))
    MANIFEST = save_run(RESULTS, note=f"stage {STAGE}: {label}, parser "
                                      f"{CONFIG['parser_prompt_version']}, verifier "
                                      f"{VERIFIER_PROMPT_VERSION}")
    print(json.dumps(cost(), indent=2))
    if STAGE == 1:
        print(json.dumps(project_cost(len(PARSED)), indent=2))
else:
    raise ValueError("STAGE must be 0, 1 or 2")

print()
print(f"corpus: {len(PARSED)} elements across {len({r['module'] for r in PARSED})} modules")
for m, n in Counter(r["module"] for r in PARSED).most_common():
    print(f"   {m:28s} {n:5d}")
''')

md(r"""
## 12. Workflow

```python
RESULTS  = run_verification()                 # all 1689 elements (cached, resumable)
flat     = flatten(RESULTS)
status_table(flat)                            # SUPPORTED / PARTIAL / CONTRADICTED per field
error_summary(RESULTS)                        # counts by error category and severity
pattern_report(RESULTS)                       # recurring parser-error patterns
MANIFEST = save_run(RESULTS, note="...")
```

Cost: one call per element, ~1689 for a full pass. Start with
`run_verification(PARSED[:25])`. Responses are cached on
`sha256(model + decoding + verifier_prompt + payload)`, so an interrupted pass resumes free,
and only elements whose RTL context or claims changed re-issue calls.

### The loop

```
RTL -> Parser -> Parsed JSON -> RTL-grounded Verifier -> Verified Error Report
    -> Aggregate Error Patterns -> Improve Parser Prompt -> Parser again -> Verifier again
```

Bump `parser_prompt_version` and point `parsed_dir` at the new parser output. A fresh
`run_NNN/` is created every time; nothing is overwritten and `data/` is never written to.

### What this notebook will not do

It will not tell you whether anything is a security asset. Every status is of the form
*"the parser claims X; the RTL supports / partially supports / contradicts / does not
establish X."* Absence of evidence is `NOT_ESTABLISHED`, never `CONTRADICTED`.
""")

nb["cells"] = C
nb["metadata"] = {"kernelspec": {"display_name":"Python 3","language":"python","name":"python3"},
                  "language_info": {"name":"python","version":"3.13"}}
p = os.path.join(OUT, "parser_verifier.ipynb")

# ---------------------------------------------------------------------------
# The notebook has been hand-edited since this builder last generated it, and
# this script was NOT kept in step. Regenerating blind silently reverts those
# edits -- and the folder is not under git, so there is nothing to recover from.
#
# The guard is CONTENT-based, not mtime-based: mtime says nothing about whether
# the difference matters, and touching this file would defeat it. Compare the
# code cells this run would write against the code cells already on disk, and
# refuse if they differ.
# ---------------------------------------------------------------------------
def _codecells(cells):
    return [("".join(c["source"]) if isinstance(c.get("source"), list) else c.get("source", ""))
            for c in cells if c.get("cell_type") == "code"]

if os.path.exists(p) and "--force" not in sys.argv:
    try:
        _disk = _codecells(json.load(io.open(p, encoding="utf-8"))["cells"])
    except Exception:
        _disk = None
    _new = _codecells(C)
    if _disk is not None and _disk != _new:
        _diff = [i for i in range(max(len(_disk), len(_new)))
                 if (_disk[i] if i < len(_disk) else None) != (_new[i] if i < len(_new) else None)]
        raise SystemExit(
            "REFUSING TO OVERWRITE: %s\n"
            "  code cells on disk differ from what this builder generates: %s\n"
            "  (cell indices are into the CODE cells only, not the full cell list)\n"
            "The notebook carries edits this script does not have. Port them into\n"
            "this file first, or re-run with --force to discard them.\n"
            "Take a copy before forcing -- this folder is not under git."
            % (p, _diff))

nbf.write(nb, p)
print("wrote", p, "|", len(C), "cells")
