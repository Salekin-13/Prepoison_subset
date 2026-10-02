"""Relation stage: an LLM writes the relationships of every element of an entity from its occurrence profile.

Pipeline:  ... classify / validate (LLM: SITE, Role)  ->  RELATION (LLM: functionality + relationship pairs)  ->  merge (code)

The annotator (gpt-5-mini) follows relation_prompts_v1/relation_system_prompt.md, written by gpt-6-astra from
META_PROMPT.md. It receives the comment-stripped source of one entity, the closed set (ports and signals), the occurrence
profile of EVERY element of the entity (Context and Path by code, SITE and Role by the occurrence validate step), and a
batch of elements. It writes both sides of every pair, each at its own occurrence (RELATIONSHIP_DEFINITIONS.md v2).

Code writes no relationship. It checks the answer (shape, occurrence IDs, closed-set targets, type allowed for each SITE,
pairs written from both sides, agreement with the same table implemented in code), then adds the fields the prompt
reserves for the program: kind, handling, guard, boundary, storage, constant_drivers, configuration, connections.

Final file: step1/relation_map_v1/<module>.json = {"ports": [...], "signals": [...]}.
"""
from __future__ import annotations

import contextlib, hashlib, io, json, os, re, sys, time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PACK = ROOT / "bahavioral_patterns_of_assets/annotation_pack_elements"
PROMPT_FILE = PACK / "relation_prompts_v1/relation_system_prompt.md"
BUILDER = PACK / "occurrence_prompts_v2/rulebook_edits"
OUT = HERE / "relation_out"
MAP = HERE / "relation_map_v1"

# where each module's occurrence profile comes from (Context/Path by code; SITE/Role by the occurrence validate step)
PROFILE = {"neorv32_boot_rom": ("occurrence_profiles_v3", "cb5e024b7d65"),
           "neorv32_trng":     ("occurrence_profiles_v3", "cb5e024b7d65"),
           "neorv32_cache":    ("occurrence_profiles_v3b", "cb5e024b7d65")}

DRIVING = ("SEQUENCES", "RESETS", "SELECTS", "CONSTRAINS", "GATES", "CARRIES", "SOURCES")
MIRROR = {"CARRIES": "COPIES", "SOURCES": "DERIVES_FROM", "SEQUENCES": "CLOCKED_BY", "RESETS": "RESET_BY",
          "SELECTS": "SELECTED_BY", "CONSTRAINS": "CONSTRAINED_BY", "GATES": "GATED_BY"}
MIRROR.update({v: k for k, v in list(MIRROR.items())})
RECEIVING = tuple(MIRROR[t] for t in DRIVING)
CONTROL = {"SEQUENCES", "RESETS", "SELECTS", "CONSTRAINS", "GATES",
           "CLOCKED_BY", "RESET_BY", "SELECTED_BY", "CONSTRAINED_BY", "GATED_BY"}
LHS = {"LHS_PROC", "LHS_CONC"}
RHS = {"DIRR_ASS", "RHS_OPERAND", "WHEN_EXPR", "INDEX"}
ADDON = {"INDEXED_NAME", "PART_SELECT"}
# section 4 of the meta prompt: the driving types each SITE allows (receiving types only at an assignment)
ALLOWED = {"EDGE_CHECK": {"SEQUENCES"}, "IF_COND": {"RESETS", "CONSTRAINS", "GATES"},
           "WHEN_COND": {"CONSTRAINS", "GATES"}, "CASE_EXPR": {"SELECTS"}, "INDEX": {"SELECTS"},
           "DIRR_ASS": {"CARRIES"}, "RHS_OPERAND": {"GATES", "SOURCES"}, "WHEN_EXPR": {"SOURCES"},
           "VAR_RHS_OPERAND": {"SOURCES", "GATES"}, "INDEXED_NAME": {"SOURCES"}, "PART_SELECT": {"SOURCES"}}
sys.path.insert(0, str(ROOT))
from prompts_parse_v3 import BANNED_IN_OUTPUT as BANNED      # the project's list, not a copy that could drift
NOT_READ = {"DECL_PORT", "DECL_SIGNAL", "DECL_FIELD", "ASSOC_ACTUAL", "PROCESS_TRIG"}
DECL = {"DECL_PORT", "DECL_SIGNAL", "DECL_FIELD"}


def _banned(text: str) -> list[str]:
    """Forbidden words in text, matched as parse_v3.check_annotation matches them: substrings of the lowercased text
    padded with spaces (so "untrusted" is caught by "trusted", and "may " needs the word to end)."""
    low = " " + text.lower() + " "
    return sorted({w.strip() for w in BANNED if w in low})
SINGLE_BIT = {"std_ulogic", "std_logic", "bit", "boolean"}
PRICE = {"in": 0.25e-6, "cached": 0.025e-6, "out": 2.0e-6}          # gpt-5-mini, per token


# ------------------------------------------------------------------ the prompt audit
def audit_prompt(log=print, prompt_file=None) -> bool:
    """The project constraints on the system prompt the stage sends: the sha recorded by the astra run, sections 3-6
    of META_PROMPT.md carried word for word, comments declared removed, forbidden words only in the one paragraph that
    forbids them, no numeric emission hints, no corpus identifier."""
    sys.path.insert(0, str(ROOT / "assetgen_meta"))
    import meta_tools as mt
    pf = Path(prompt_file) if prompt_file else PROMPT_FILE
    P = pf.read_text(encoding="utf-8")
    META = (pf.parent / "META_PROMPT.md").read_text(encoding="utf-8")
    rec = json.loads((pf.parent / "astra_meta_run.json").read_text(encoding="utf-8"))
    norm = lambda t: " ".join(t.split())
    fails = []
    if _sha(P) != rec["prompt_sha"]:
        fails.append(f"prompt sha {_sha(P)} differs from the astra run's {rec['prompt_sha']}: the file was edited")
    for sec, nxt in (("3. THE RELATIONSHIP PAIRS", "4. FROM SITE"), ("4. FROM SITE TO RELATIONSHIP", "5. GUARDS"),
                     ("5. GUARDS AGAINST", "6. THE OUTPUT"), ("6. THE OUTPUT CONTRACT", "7. HARD")):
        body = META.split(sec, 1)[1].split("=" * 50, 2)[1].split(nxt)[0].split("=" * 50)[0]
        if norm(body) not in norm(P):
            fails.append(f"section {sec!r} not carried word for word")
    if "comments removed" not in P.lower():
        fails.append("'comments removed' is not declared")
    paras = re.split(r"\n\s*\n", P)
    listing = [i for i, p in enumerate(paras) if sum(1 for w in BANNED if w.strip() in p.lower()) >= len(BANNED) - 2]
    hits = _banned("\n".join(p for i, p in enumerate(paras) if i not in listing))
    if len(listing) != 1 or hits:
        fails.append(f"forbidden-word paragraphs {len(listing)}; forbidden words elsewhere {hits}")
    if "Use none of these words in functionality" not in P:
        fails.append("the forbidden-word section does not open with the sentence META_PROMPT.md section 7 gives")
    for t in ("3. THE RELATIONSHIP PAIRS", "4. FROM SITE TO RELATIONSHIP", "5. GUARDS AGAINST INVENTED RELATIONSHIPS",
              "6. THE OUTPUT CONTRACT"):
        if t not in P:
            fails.append(f"title {t!r} missing")
    leak = sorted({m.group(0) for m in re.finditer(r"word for word|carry (?:this|these)|into the prompt|rulebook|\bmeta\b|"
                                                   r"prompt writer|writer of the prompt", P, re.I)})
    if leak:
        fails.append(f"text addressed to the prompt writer, or naming what the annotator does not receive: {leak}")
    num = [m.group(0) for p in mt._NUMERIC for m in re.finditer(p, P, re.I)]
    if num:
        fails.append(f"numeric emission hints {num}")
    ids = sorted(n for n in mt.corpus_names(str(ROOT)) if re.search(r"(?<![\w<])" + re.escape(n) + r"(?![\w>])", P))
    if ids:
        fails.append(f"corpus identifiers {ids[:10]}")
    log(f"   prompt {pf.parent.name}/{pf.name}: {len(P):,} chars, sha {_sha(P)}; audit {'PASS' if not fails else 'FAIL'}")
    for x in fails:
        log(f"      FAIL {x}")
    return not fails


# ------------------------------------------------------------------ inputs
def _builder():
    """The v3b builder's own input functions, run with its working directory."""
    sys.path.insert(0, str(BUILDER))
    import build_occurrence_notebook_v3b as B
    g, cwd = {"__name__": "nb"}, os.getcwd()
    try:
        os.chdir(B.ROOT)
        with contextlib.redirect_stdout(io.StringIO()):
            for c in (B.C_SETUP, B.C_PROMPTS, B.C_INPUTS):
                exec(c, g)
    finally:
        os.chdir(cwd)
    return B, g


def _latest(paths):
    best = {}
    for p in paths:
        if p.name not in best or p.stat().st_mtime > best[p.name].stat().st_mtime:
            best[p.name] = p
    return list(best.values())


def _where(module, where=None) -> dict:
    """The folders of one run set: the closed set (None: the builder's element lists), the occurrence profiles (their
    root and validate prompt sha), the model's answers, and the final maps. Without `where`: the three-module pack."""
    if where:
        return where
    folder, vsha = PROFILE[module]
    return {"elem_dir": None, "profile": (PACK / folder, vsha), "out": OUT, "map": MAP}


def load_module(module: str, where: dict | None = None) -> list[dict]:
    """One dict per entity: closed set (ports, signals), numbered source, and the occurrence profile of every element."""
    w = _where(module, where)
    B, g = _builder()
    cwd = os.getcwd()
    try:
        os.chdir(B.ROOT)
        if w["elem_dir"]:
            d = json.loads((Path(w["elem_dir"]) / f"{module}.json").read_text(encoding="utf-8"))
            listed = [(e["entity"], e["ports"] + e["signals"]) for e in d["entities"]]
        else:
            listed = g["load_elements"](module)
        ents = [(e, els, g["numbered_entity_source"](g["RTL_DIR"] / f"{module}.vhd", e)) for e, els in listed]
    finally:
        os.chdir(cwd)
    root, vsha = w["profile"]
    rows = {}
    for f in _latest((Path(root) / "extract").rglob(f"{module}__*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        for n, rs in json.loads(rec["raw"]).items():
            for r in rs:
                rows[(rec["entity"], n, r["Occurrence ID"])] = dict(r)
    for f in (Path(root) / "validate" / vsha).glob(f"{module}__*.json"):
        rec = json.loads(f.read_text(encoding="utf-8"))
        ans = json.loads(re.sub(r"^```[a-z]*\n|\n```$", "", rec["raw"].strip()))
        for n, rs in ans.items():
            for r in rs if isinstance(rs, list) else []:
                k = (rec["entity"], n, r.get("Occurrence ID"))
                if isinstance(r, dict) and k in rows and rows[k]["Occurrence Lines"] == r.get("Occurrence Lines"):
                    rows[k]["SITE Tagged"] = list(r.get("SITE Tagged") or [])
                    rows[k]["Role"] = r.get("Role", "")
    out = []
    for ent, els, src in ents:
        ports = [{"name": e["name"], "dir": e.get("dir"), "type": e.get("type")} for e in els if e.get("dir")]
        sigs = [{"name": e["name"], "type": e.get("type")} for e in els if not e.get("dir")]
        prof = {}
        for e in els:
            rs = sorted((r for (en, n, _i), r in rows.items() if en == ent and n == e["name"]),
                        key=lambda r: r["Occurrence ID"])
            prof[e["name"]] = [{**r, "SITE Tagged": r.get("SITE Tagged", []), "Role": r.get("Role", "")} for r in rs]
        out.append({"module": module, "entity": ent, "ports": ports, "signals": sigs, "src": src, "profile": prof,
                    "missing_site": sum(1 for rs in prof.values() for r in rs if "Role" not in r or r["Role"] == "")})
    return out


# ------------------------------------------------------------------ the table, implemented in code (the reference)
def _frames(ctx: str):
    out = []
    for piece in (ctx or "").split(" in "):
        m = re.match(r"^(.*?) (\d+)-(\d+)$", piece.strip())
        if not m:
            continue
        k = m.group(1)
        kind = ("branch:" + k.split()[0]) if " branch" in k and not k.startswith("generate") else \
               "alt" if k.startswith("case alternative") else "case" if k.startswith("case ") else \
               "if" if k == "if" or k.startswith("if ") else "when_else" if k.startswith("when else") else \
               "with" if k.startswith("with select") else k.split()[0]
        out.append((kind, int(m.group(2)), int(m.group(3))))
    return out


def _key(f):
    return ("branch" if f[0].startswith("branch") else f[0], f[1], f[2])


def _occs(ent):
    out = []
    for n, rs in ent["profile"].items():
        for r in rs:
            out.append({"el": n, "id": r["Occurrence ID"], "line": r["Occurrence Lines"], "text": r["Line Text"],
                        "fr": _frames(r.get("Context")), "ctx": r.get("Context"), "path": r.get("Path") or [], "sites": set(r["SITE Tagged"])})
    return out


def _rhs(text):
    return text.split("<=", 1)[1] if "<=" in text else ""


def _collapse_bits(text: str, names=()) -> str:
    """<element>(<one position>) -> <element>: a single bit written by index is one operand. Only element names are
    collapsed, so a function call f(a) is never read as an operand f."""
    low = {n.lower() for n in names}
    rx = re.compile(r"([A-Za-z_][\w.]*)\s*\(([^()]*)\)")
    def one(m):
        if m.group(1).lower() in low and not re.search(r"\b(?:downto|to)\b", m.group(2), re.I):
            return m.group(1)
        return m.group(0)
    return rx.sub(one, text)


def _single_bit(name, typ, text, names=()) -> bool:
    """Single-bit as the prompt reads it: declared single-bit, or written with one position, <element>(<index>)."""
    if (typ or "").lower() in SINGLE_BIT:
        return True
    uses = re.findall(rf"(?<![\w.]){re.escape(name)}(?![\w])\s*(\(([^()]*)\))?", text, re.I)
    return bool(uses) and all(u[0] and not re.search(r"\b(?:downto|to)\b", u[1], re.I) for u in uses)


def _flat_logic(rhs: str, names=()) -> bool:
    """The operand form of GATES (section 3): one flat and / or / nand / nor over bare names or single bits written by
    index, each optionally under not, parentheses ignored. Mixed operators, which VHDL makes the writer bracket, do
    not count."""
    t = re.sub(r"[()]", " ", _collapse_bits(rhs.split("--")[0], names)).strip().rstrip(";").strip()
    ok = re.fullmatch(r"(?:not\s+)?[\w.]+(?:\s+(?:and|or|nand|nor)\s+(?:not\s+)?[\w.]+)+", t, re.I)
    return bool(ok) and len({o.lower() for o in re.findall(r"\b(and|or|nand|nor)\b", t, re.I)}) == 1


def _same_stmt(a, b):
    """L4: the same statement. A when-else is one statement across its lines; otherwise the same line."""
    wa = next((f for f in a["fr"] if f[0] == "when_else"), None)
    wb = next((f for f in b["fr"] if f[0] == "when_else"), None)
    return (wa is not None and wa == wb) or (a["line"] == b["line"] and wa is None and wb is None)


def _edge_arms(occ):
    return {_key(o["fr"][0]) for o in occ if "EDGE_CHECK" in o["sites"] and o["fr"]}


def _in_reset_arm(a, edge_arms):
    """An assignment directly in an arm of an if whose later arm is the clock-edge arm (RESETS, section 3)."""
    if len(a["fr"]) < 2 or not a["fr"][0][0].startswith("branch"):
        return False
    br, ifr = _key(a["fr"][0]), _key(a["fr"][1])
    return any(f[1] > br[1] and ifr[1] <= f[1] <= ifr[2] for f in edge_arms)


def code_pairs(ent) -> set[tuple]:
    """(Y, y_id, X, x_id, driving type) by the linking rules L1-L5 and the SITE table. Pairs are exact under those rules;
    the CONSTRAINS and GATES-operand distinctions are approximate (they read the line text and the declared types)."""
    occ = _occs(ent)
    names = {e["name"] for e in ent["ports"] + ent["signals"]}
    types = {e["name"]: (e.get("type") or "").lower() for e in ent["ports"] + ent["signals"]}
    assigns = [o for o in occ if o["sites"] & LHS]
    edge_arms = {_key(o["fr"][0]) for o in occ if "EDGE_CHECK" in o["sites"] and o["fr"]}
    wname = _names_re
    same_stmt = _same_stmt

    def reset_arm(br, ifr):
        return any(f[1] > br[1] and ifr[1] <= f[1] <= ifr[2] for f in edge_arms)

    def const_rhs(a):
        return not any(wname(n).search(_rhs(a["text"])) for n in names)

    def cond_type(y, cond):
        term = next((t for t in re.split(r"\b(?:and|or)\b", cond, flags=re.I) if wname(y["el"]).search(t)), cond)
        others = [n for n in names if n != y["el"] and wname(n).search(term)]
        return "CONSTRAINS" if others and re.search(r"/=|<=|>=|=|<|>", term) else "GATES"

    P = set()
    for y in occ:
        s, fr = y["sites"], y["fr"]
        tg = []
        if "EDGE_CHECK" in s and fr:
            br = _key(fr[0])
            tg = [(a, "SEQUENCES") for a in assigns if br in map(_key, a["fr"])]
        elif "IF_COND" in s and len(fr) > 1:
            br, ifr = _key(fr[0]), _key(fr[1])
            cond = y["text"]
            rs = reset_arm(br, ifr)
            for a in assigns:
                keys = list(map(_key, a["fr"]))
                if br in keys:
                    tg.append((a, "RESETS" if rs and const_rhs(a) else cond_type(y, cond)))
                elif not rs and ifr in keys and any(k[0] == "branch" and k[1] > br[1] and ifr[1] <= k[1] <= ifr[2] for k in keys):
                    tg.append((a, cond_type(y, cond)))
        elif "WHEN_COND" in s:
            f0 = next((f for f in fr if f[0] == "when_else"), None)
            cond = re.split(r"\bwhen\b", y["text"], maxsplit=1, flags=re.I)[-1]
            tg = [(a, cond_type(y, cond)) for a in assigns if f0 and f0 in a["fr"] and a["line"] <= f0[2]]
        elif "CASE_EXPR" in s:
            f0 = next((f for f in fr if f[0] == "case"), None)
            tg = [(a, "SELECTS") for a in assigns if f0 and f0 in a["fr"]]
        elif fr and fr[0][0] == "with" and not s & LHS:
            tg = [(a, "SELECTS") for a in assigns if a["fr"] and a["fr"][0] == fr[0]]
        elif s & RHS or (s & ADDON and not s & LHS) or "VAR_RHS_OPERAND" in s:
            for a in assigns:
                if not same_stmt(a, y):
                    continue
                if "INDEX" in s:
                    t = "SELECTS"
                elif "DIRR_ASS" in s:
                    t = "CARRIES"
                elif "RHS_OPERAND" in s and _flat_logic(_rhs(a["text"]), names) and \
                        _single_bit(a["el"], types.get(a["el"]), a["text"].split("<=", 1)[0], names) and \
                        _single_bit(y["el"], types.get(y["el"]), _rhs(a["text"]), names):
                    t = "GATES"            # single-bit as written (sys 140-147: clk_en_o(k) <= cnt(i) and (not cnt2(i)))
                else:
                    t = "SOURCES"
                tg.append((a, t))
        for a, t in tg:
            if not (a["el"] == y["el"] and a["id"] == y["id"]):
                P.add((y["el"], y["id"], a["el"], a["id"], t))
    return P


# ------------------------------------------------------------------ batching, messages
def linked_batches(ent, max_occ=85, max_el=20) -> list[list[str]]:
    """Batches that keep related elements together, under the same caps as batches(). A batch starts at the free
    element with the most links to other free elements, then takes the free element with the most links into the
    batch; when no linked element fits, it fills with the next free elements in declaration order. Links are the
    element pairs of the code reference (code_pairs), which reads only positions (L1-L5) and SITEs."""
    order = [e["name"] for e in ent["ports"] + ent["signals"]]
    rank = {n: i for i, n in enumerate(order)}
    occ = {n: len(ent["profile"].get(n, [])) for n in order}
    adj = defaultdict(Counter)
    for y, _yi, x, _xi, _t in code_pairs(ent):
        if y != x:
            adj[y][x] += 1
            adj[x][y] += 1
    left, out = set(order), []
    while left:
        seed = max(left, key=lambda n: (sum(adj[n][m] for m in left), -rank[n]))
        cur, n_occ = [seed], occ[seed]
        left.discard(seed)
        while len(cur) < max_el:
            fit = [m for m in left if occ[m] + n_occ <= max_occ]
            if not fit:
                break
            best = max(fit, key=lambda m: (sum(adj[m][c] for c in cur), -rank[m]))
            if sum(adj[best][c] for c in cur) == 0:
                best = min(fit, key=lambda m: rank[m])
            cur.append(best)
            n_occ += occ[best]
            left.discard(best)
        out.append(sorted(cur, key=lambda n: rank[n]))      # closed-set order inside a batch, as section 6 asks
    return out


def batches_for(ent, batching="declaration", max_occ=85):
    return linked_batches(ent, max_occ) if batching == "linked" else batches(ent, max_occ)


def batches(ent, max_occ=85, max_el=20) -> list[list[str]]:
    order = [e["name"] for e in ent["ports"] + ent["signals"]]
    out, cur, n = [], [], 0
    for el in order:
        c = len(ent["profile"].get(el, []))
        if cur and (len(cur) >= max_el or n + c > max_occ):
            out.append(cur); cur, n = [], 0
        cur.append(el); n += c
    if cur:
        out.append(cur)
    return out


def user_message(ent, batch: list[str]) -> str:
    prof = {n: [{k: r[k] for k in ("Occurrence ID", "Occurrence Lines", "Name As Written", "Line Text", "Context",
                                    "Path", "SITE Tagged", "Role")} for r in rs] for n, rs in ent["profile"].items()}
    ports = {e["name"] for e in ent["ports"]}
    # the fixed prefix first (source, closed set, whole profile), so every batch of the entity reuses the cached part
    return (f"ENTITY: {ent['entity']}   (module {ent['module']})\n\n"
            f"SOURCE of this entity. Comments removed; each line starts with its line number:\n\n{ent['src']}\n\n"
            f"CLOSED SET\nPORTS:\n{json.dumps(ent['ports'], indent=1)}\nSIGNALS:\n{json.dumps(ent['signals'], indent=1)}\n\n"
            f"OCCURRENCE PROFILE of every element of the entity:\n{json.dumps(prof, indent=1)}\n\n"
            f"BATCH, the elements to annotate in this call:\n"
            f"PORTS: {json.dumps([n for n in batch if n in ports])}\n"
            f"SIGNALS: {json.dumps([n for n in batch if n not in ports])}\n\n"
            f"Return one json object in the format given in your instructions.\n")


def _sha(s):
    return hashlib.sha256(s.encode()).hexdigest()[:12]


# ------------------------------------------------------------------ the model call
def _plan(module, where=None, batching="declaration", prompt_file=None, max_occ=85, log=print, dry=False):
    """The calls a module still needs: one job per batch whose answer is missing or was made from another input."""
    system = Path(prompt_file or PROMPT_FILE).read_text(encoding="utf-8")
    psha = _sha(system)
    w = _where(module, where)
    cost, todo = Counter(), []
    for ent in load_module(module, where):
        for b, batch in enumerate(batches_for(ent, batching, max_occ)):
            msg = user_message(ent, batch)
            p = Path(w["out"]) / psha / f"{module}__{ent['entity']}__b{b:02d}.json"
            n_occ = sum(len(ent["profile"].get(n, [])) for n in batch)
            if p.exists() and json.loads(p.read_text(encoding="utf-8")).get("input_sha") == _sha(msg):
                log(f"   current  {ent['entity']} b{b}: {len(batch)} elements, {n_occ} occurrences")
                continue
            if dry:
                log(f"   to call  {ent['entity']} b{b}: {len(batch)} elements, {n_occ} occurrences, "
                    f"input {len(system) + len(msg):,} chars")
                cost["calls"] += 1
                cost["input_chars"] += len(system) + len(msg)
                continue
            todo.append({"module": module, "entity": ent["entity"], "b": b, "batch": batch, "msg": msg, "p": p,
                         "n_occ": n_occ, "system": system, "psha": psha, "record": {}})
    return psha, cost, todo


def _attempt(client, model, system, msg, effort, attempts=6, first_wait=15.0):
    """One model call with patient retries: under many parallel calls a rate-limit or timeout error is waited out
    (15 s, 30 s, 60 s, ... with jitter) instead of failing the batch."""
    import random
    sys.path.insert(0, str(ROOT / "assetgen_meta")); import meta_tools as mt
    wait = first_wait
    for a in range(attempts):
        try:
            return mt.call_text(client, model, system, msg, effort, 64000, retries=1, json_mode=True)
        except Exception:
            if a == attempts - 1:
                raise
            time.sleep(wait * (0.75 + random.random() / 2))
            wait = min(wait * 2, 240)


def call_pool(jobs, client, model="gpt-5-mini", effort="medium", workers=20, log=print) -> Counter:
    """Run jobs from any number of modules in ONE pool of `workers` parallel calls, the largest input first, so the
    slowest calls start at once and the run ends with the short ones. Each job writes its own answer file; a job that
    still fails after its retries is counted and named, never stops the others (re-running calls only what is missing)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    jobs = sorted(jobs, key=lambda j: -len(j["msg"]))
    cost, t_start = Counter(), time.time()

    def one(j):
        t0 = time.time()
        txt, u, status = _attempt(client, model, j["system"], j["msg"], effort)
        j["p"].parent.mkdir(parents=True, exist_ok=True)
        j["p"].write_text(json.dumps({"prompt_sha": j["psha"], "input_sha": _sha(j["msg"]), "model": model,
                                      "effort": effort, "module": j["module"], "entity": j["entity"], "batch": j["b"],
                                      "names": j["batch"], "status": status, "usage": u,
                                      "seconds": round(time.time() - t0), **j["record"], "raw": txt}, indent=1),
                          encoding="utf-8")
        return u, round(time.time() - t0)

    if not jobs:
        return cost
    log(f"   calling  {len(jobs)} batch(es) from {len({j['module'] for j in jobs})} module(s), {workers} at a time, "
        f"largest first ...")
    with ThreadPoolExecutor(max(1, workers)) as ex:
        futs = {ex.submit(one, j): j for j in jobs}
        for f in as_completed(futs):
            j = futs[f]
            try:
                u, s = f.result()
            except Exception as e:
                cost["failed"] += 1
                log(f"   FAILED   {j['module']}/{j['entity']} b{j['b']}: {type(e).__name__}: {str(e)[:120]}")
                continue
            cost["calls"] += 1; cost["in"] += u["in"]; cost["out"] += u["out"]
            log(f"   done {cost['calls']:3d}/{len(jobs)}  {j['module'][8:]}/{j['entity']} b{j['b']}: {len(j['batch'])} "
                f"elements, {j['n_occ']} occurrences, {s} s, out {u['out']:,} tokens, {(time.time() - t_start) / 60:.1f} min")
    cost["minutes"] = round((time.time() - t_start) / 60, 1)
    return cost


def run(module, client=None, model="gpt-5-mini", effort="medium", max_occ=85, dry=False, log=print,
        where: dict | None = None, workers: int = 1, batching: str = "declaration", prompt_file=None) -> dict:
    """Annotate every batch of every entity of a module. Answers are cached by prompt and input sha. `workers` calls
    run in parallel (each writes its own file); the batches of one entity share the cached prefix either way."""
    psha, cost, todo = _plan(module, where, batching, prompt_file, max_occ, log, dry)
    cost.update(call_pool(todo, client, model, effort, workers, log))
    cost["usd_upper"] = round(cost["in"] * PRICE["in"] + cost["out"] * PRICE["out"], 4)
    return {"prompt_sha": psha, "cost": dict(cost)}


def run_many(modules, client=None, model="gpt-5-mini", effort="medium", max_occ=85, dry=False, log=print,
             where: dict | None = None, workers: int = 20, batching: str = "declaration", prompt_file=None) -> dict:
    """run() over several modules with all their calls in one pool, so no module waits for another to finish."""
    psha, cost, todo = None, Counter(), []
    for m in modules:
        psha, c, t = _plan(m, where, batching, prompt_file, max_occ, lambda *a: None, dry)
        cost.update(c); todo += t
    if dry:
        log(f"   {cost['calls']} call(s) to make over {len(modules)} module(s)")
    cost.update(call_pool(todo, client, model, effort, workers, log))
    cost["usd_upper"] = round(cost["in"] * PRICE["in"] + cost["out"] * PRICE["out"], 4)
    return {"prompt_sha": psha, "cost": dict(cost)}


# ------------------------------------------------------------------ checks
GUARDED = {"GATES", "SELECTS", "CONSTRAINS", "GATED_BY", "SELECTED_BY", "CONSTRAINED_BY"}
LLM_KEYS = {"name", "functionality", "relationship"}
REL_KEYS = {"type", "targets", "at", "bits"}


def _names_re(n):
    """n as a whole name: not part of a longer name, and a record base does not match its fields."""
    return re.compile(rf"(?<![\w.]){re.escape(n)}(?!\w|\.\w)", re.I)


def _answers(module, psha, out_dir=None):
    out = {}
    for p in sorted((Path(out_dir or OUT) / psha).glob(f"{module}__*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        try:
            out[(rec["entity"], rec["batch"])] = (rec, json.loads(re.sub(r"^```[a-z]*\n|\n```$", "", rec["raw"].strip())))
        except Exception:
            out[(rec["entity"], rec["batch"])] = (rec, None)
    return out


def check(module, psha=None, answers=None, ents=None, log=print, where: dict | None = None) -> dict:
    """Every check the prompt's guards make verifiable by code. Returns counts, examples and the records."""
    psha = psha or _sha(PROMPT_FILE.read_text(encoding="utf-8"))
    ents = {e["entity"]: e for e in (ents or load_module(module, where))}
    answers = answers if answers is not None else _answers(module, psha, _where(module, where)["out"])
    issues, ex = Counter(), defaultdict(list)
    recs, func = defaultdict(list), {}
    for (entn, b), (rec, ans) in sorted(answers.items()):
        ent = ents[entn]
        names = {e["name"] for e in ent["ports"] + ent["signals"]}
        ports = {e["name"] for e in ent["ports"]}
        if not isinstance(ans, dict) or set(ans) != {"ports", "signals"}:
            issues["answer is not {ports, signals}"] += 1; ex["shape"].append((entn, b)); continue
        seen = Counter()
        for arr in ("ports", "signals"):
            for e in ans.get(arr) or []:
                if not isinstance(e, dict):
                    issues["entry is not an object"] += 1; continue
                n = e.get("name")
                seen[n] += 1
                if n not in rec["names"]:
                    issues["element outside the batch"] += 1; ex["outside batch"].append(n); continue
                if (arr == "ports") != (n in ports):
                    issues["element in the wrong array"] += 1; ex["wrong array"].append(n)
                if set(e) - LLM_KEYS:
                    issues["a field the model must not write"] += 1; ex["extra field"].append((n, sorted(set(e) - LLM_KEYS)))
                f = str(e.get("functionality", ""))
                func[(entn, n)] = f
                bw = _banned(f)
                if bw:
                    issues["functionality with a forbidden word"] += 1; ex["forbidden word"].append((n, bw))
                if len(f.split()) > 45:
                    issues["functionality over 45 words"] += 1
                prof = {r["Occurrence ID"]: r for r in ent["profile"].get(n, [])}
                for r in e.get("relationship") or []:
                    t = r.get("type")
                    if t not in DRIVING + RECEIVING:
                        issues["type not one of the fourteen"] += 1; ex["unknown type"].append((n, t)); continue
                    if set(r) - REL_KEYS:
                        issues["a relationship key the model must not write"] += 1
                        ex["extra key"].append((n, sorted(set(r) - REL_KEYS)))
                    ats, tgts = r.get("at") or [], r.get("targets") or []
                    bad_at = [a for a in ats if a not in prof]
                    bad_t = [x for x in tgts if x not in names]
                    if bad_at:
                        issues["at: not an Occurrence ID of the element (G1)"] += 1; ex["G1 at"].append((n, t, bad_at))
                    if bad_t:
                        issues["target outside the closed set (G1)"] += 1; ex["G1 target"].append((n, t, bad_t))
                    for a in ats:
                        if a not in prof:
                            continue
                        sites = set(prof[a]["SITE Tagged"])
                        ctx0 = (prof[a].get("Context") or "").split(" in ")[0]
                        ok = (t in RECEIVING and sites & LHS) or (t in DRIVING and (
                            any(t in ALLOWED.get(s, set()) for s in sites) or
                            (not sites and t in ("SOURCES", "GATES")) or
                            (t == "SELECTS" and ctx0.startswith("with select"))))
                        if not ok:
                            issues["type not allowed for the SITE of its occurrence (G3)"] += 1
                            ex["G3"].append((n, a, t, sorted(sites)))
                        for x in tgts:
                            if x in names:
                                recs[entn].append((n, a, t, x, r.get("bits")))
        for n in rec["names"]:
            if seen[n] != 1:
                issues["batch element missing or repeated"] += 1; ex["missing or repeated"].append((n, seen[n]))
    # pairs written from both sides, and agreement with the table implemented in code
    pair, agree, diag = Counter(), Counter(), defaultdict(list)
    for entn, rs in recs.items():
        P = code_pairs(ents[entn])
        link_d, link_r = {(y, yi, x) for y, yi, x, _xi, _t in P}, {(x, xi, y) for y, _yi, x, xi, _t in P}
        for n, a, t, x, _b in rs:
            if (n, a, x) not in (link_d if t in DRIVING else link_r):
                diag["occurrence x target not linked by L1-L5 (G2/G7, or a pair through a process variable)"].append(
                    (entn, n, a, t, x))
        have = {(n, t, x) for n, a, t, x, _b in rs}
        for n, a, t, x, _b in rs:
            pair["records"] += 1
            pair["with partner" if (x, MIRROR[t], n) in have else "without partner"] += 1
        llm = {(n, x) if t in DRIVING else (x, n) for n, a, t, x, _b in rs}
        done = {n for (e2, _b), (rec, _a) in answers.items() if e2 == entn for n in rec["names"]}
        ref = {(y, x) for y, _yi, x, _xi, _t in P if y in done and x in done}
        agree["reference pairs"] += len(ref); agree["model pairs"] += len(llm); agree["both"] += len(ref & llm)
        # the stricter view: one record per (element, occurrence, type, target), both sides, batch elements only
        typed_ref = {r for y, yi, x, xi, t in P for r in ((y, yi, t, x), (x, xi, MIRROR[t], y)) if r[0] in done}
        typed = {(n, a, t, x) for n, a, t, x, _b in rs}
        agree["reference records"] += len(typed_ref); agree["model records"] += len(typed)
        agree["records both"] += len(typed_ref & typed)
        for k, v in (("record not in the reference (type or place differs)", typed - typed_ref),
                     ("reference record the model did not write", typed_ref - typed)):
            if v:
                diag[k] += [(entn,) + r for r in sorted(v)]
    res = {"issues": dict(issues), "examples": {k: v[:4] for k, v in ex.items()}, "pairing": dict(pair),
           "agreement": dict(agree), "records": recs, "functionality": func,
           "prompt_sha": psha, "diagnostics": {k: len(v) for k, v in diag.items()}, "diagnostic_examples": {k: v[:4] for k, v in diag.items()}}
    log(f"   relationship records (one per occurrence x target) {pair['records']}: partner written "
        f"{pair['with partner']}, partner missing {pair['without partner']}")
    if agree["reference pairs"]:
        log(f"   element pairs, model vs the table run by code: reference {agree['reference pairs']}, model "
            f"{agree['model pairs']}, both {agree['both']}. Recall {agree['both'] / agree['reference pairs']:.1%}, "
            f"precision {agree['both'] / max(agree['model pairs'], 1):.1%}  (agreement with the code reference, "
            f"exact denominators; not accuracy against a hand label)")
        log(f"   typed records (element, occurrence, type, target), model vs the same reference: reference "
            f"{agree['reference records']}, model {agree['model records']}, both {agree['records both']}. Recall "
            f"{agree['records both'] / max(agree['reference records'], 1):.1%}, precision "
            f"{agree['records both'] / max(agree['model records'], 1):.1%}  (the reference's CONSTRAINS / GATES-operand "
            f"typing is approximate: read the differences before calling one a model error)")
    log(f"   check failures: {dict(issues) or 'none'}")
    for k, v in diag.items():
        log(f"   diagnostic, {k}: {len(v)} of {pair['records']} records; e.g. {v[:3]}")
    for k, v in res["examples"].items():
        log(f"      e.g. {k}: {v}")
    return res


# ------------------------------------------------------------------ the program's fields, and the final file
def _instance_entity(src, first_line):
    for ln in src.splitlines():
        m = re.match(r"^\s*(\d+) \| (.*)$", ln)
        if m and int(m.group(1)) == first_line:
            e = re.search(r"\bentity\s+(?:\w+\.)?(\w+)", m.group(2), re.I) or \
                re.search(r"^\s*\w+\s*:\s*(?:component\s+)?(\w+)", m.group(2), re.I)
            return e.group(1) if e else None
    return None


def _guard(occ, x, xi, y):
    """The guard of a pair, read at X's assignment: the Path entries that name Y; where none does (an operand of
    and/or, a run-time index), the right-hand side of the statement."""
    o = occ.get((x, xi))
    if not o:
        return None
    hit = [p for p in o["path"] if _names_re(y).search(p)]
    if hit:
        return " and ".join(hit)
    conds = [c.strip() for yo in occ.values() if yo["el"] == y and "WHEN_COND" in yo["sites"] and _same_stmt(o, yo)
             for c in re.findall(r"\bwhen\b(.*?)(?=\belse\b|;|$)", yo["text"], re.I) if _names_re(y).search(c)]
    if conds:
        return " | ".join(dict.fromkeys(conds))
    rhs = re.split(r"<=|:=", o["text"], maxsplit=1)
    return rhs[1].strip().rstrip(";").strip() if len(rhs) > 1 else None


def merge(module, res, ents=None, out_dir=None, log=print, where: dict | None = None) -> Path:
    """Add the program's fields to the model's records and write {"ports": [...], "signals": [...]}."""
    ents = ents or load_module(module, where)
    out_dir = Path(out_dir or Path(_where(module, where)["map"]) / res["prompt_sha"])
    modes = {e["entity"].lower(): {p["name"].lower(): (p.get("dir") or "").lower() for p in e["ports"]} for e in ents}
    final = {"ports": [], "signals": []}
    no_guard = 0
    for ent in ents:
        occ = {(o["el"], o["id"]): o for o in _occs(ent)}
        edges = _edge_arms(occ.values())
        names = {e["name"] for e in ent["ports"] + ent["signals"]}
        inputs = {p["name"] for p in ent["ports"] if (p.get("dir") or "").lower() in ("in", "inout")}
        variables = set(re.findall(r"\bvariable\s+(\w+)", ent["src"], re.I))   # process variables
        all_assigns = [o for o in occ.values() if o["sites"] & LHS]
        # received: an input port, or an element this entity never assigns whose name or record base is wired to a
        # sub-block (so the sub-block drives it)
        wired = {o["el"] for o in occ.values() if "ASSOC_ACTUAL" in o["sites"]}
        assigned = {o["el"] for o in all_assigns}
        inputs |= {x for x in names if x not in assigned and (x in wired or x.split(".")[0] in wired)}
        clocked = lambda o: any(re.search(r"\b(rising|falling)_edge\s*\(", p) and not p.startswith("not (") for p in o["path"])
        link = defaultdict(set)                                  # (Y, y_id, X) -> X's assignment occurrences
        link_r = defaultdict(set)                                # (X, x_id, Y) -> Y's occurrences
        for y, yi, x, xi, _t in code_pairs(ent):
            link[(y, yi, x)].add(xi)
            link_r[(x, xi, y)].add(yi)
        rs = res["records"].get(ent["entity"], [])
        written = defaultdict(set)                               # (element, type, target) -> the model's at
        for y, a, t, x, _b in rs:
            written[(y, t, x)].add(a)

        def partner(n, a, t, x):
            """Where the partner record sits: the target's occurrences in the model's own mirror record, narrowed to
            those L1-L5 link to this occurrence when any are linked (a process-variable pair has no code link)."""
            cand = written[(x, MIRROR[t], n)]
            linked = (link if t in DRIVING else link_r)[(n, a, x)]
            return (cand & linked) or cand

        for arr, els in (("ports", ent["ports"]), ("signals", ent["signals"])):
            for e in els:
                n = e["name"]
                mine = [o for (el, _i), o in occ.items() if el == n]
                assigns = [o for o in mine if o["sites"] & LHS]
                on_edge = [any(re.search(r"\b(rising|falling)_edge\s*\(", p) and not p.startswith("not (") for p in o["path"])
                           for o in assigns if not _in_reset_arm(o, edges)]
                storage = "not assigned" if not assigns else "edge" if on_edge and all(on_edge) else \
                          "none" if not any(on_edge) else "mixed"
                consts = [o for o in assigns if not any(_names_re(x).search(_rhs(o["text"])) for x in names | variables)]
                # relationship: the model's records, regrouped with the guard the program reads. Each record keeps
                # exactly the occurrence x target pairs the model wrote: occurrences are grouped only with others
                # that relate to the same targets, so no pair is created by the merge (G7)
                grp = defaultdict(lambda: defaultdict(set))           # (type, bits, guard) -> at -> targets
                pmap = defaultdict(set)                               # (type, bits, guard, at, target) -> partner ids
                for y, a, t, x, bits in rs:
                    if y != n:
                        continue
                    g = None
                    if t in GUARDED:
                        if t in RECEIVING:
                            g = _guard(occ, n, a, x)
                        else:
                            xs = link.get((n, a, x)) or {o["id"] for (el, _i), o in occ.items()
                                                         if el == x and o["sites"] & LHS and
                                                         any(_names_re(n).search(p) for p in o["path"])}
                            gs = sorted({_guard(occ, x, xi, n) for xi in xs} - {None})
                            g = gs[0] if len(gs) == 1 else " | ".join(gs) if gs else None
                    grp[(t, bits, g)][a].add(x)
                    pmap[(t, bits, g, a, x)] |= partner(n, a, t, x)
                rel = []
                for (t, bits, g), per_at in sorted(grp.items(), key=lambda kv: (DRIVING + RECEIVING).index(kv[0][0])):
                    same = defaultdict(list)                          # one target set -> its occurrences
                    for a, xs in per_at.items():
                        same[tuple(sorted(xs))].append(a)
                    for xs, ats in sorted(same.items(), key=lambda kv: min(kv[1])):
                        r = {"type": t, "targets": list(xs), "at": sorted(ats)}
                        if t in GUARDED:
                            r["guard"] = g
                            no_guard += g is None
                        r["partner_at"] = {x: sorted(set().union(*(pmap[(t, bits, g, a, x)] for a in ats))) for x in xs}
                        if bits:
                            r["bits"] = bits
                        rel.append(r)
                entry = {"name": n, "entity": ent["entity"]}      # a file can hold several entities
                if arr == "signals":
                    entry["kind"] = "register" if storage in ("edge", "mixed") else "signal"
                entry["functionality"] = res["functionality"].get((ent["entity"], n), "")
                if "." in n:
                    # prompts_parse_v3 STEP 2c: ORIGINATES, the value is built here (assigned from this entity's logic,
                    # a clocked copy included, since the entity then holds it); CONSUMES, the value is read and acted on
                    # (a condition, an index, an operand, or a copy kept on a clock edge); FORWARDS, the value is passed
                    # on unchanged in the same form (an unclocked exact copy in or out, or the whole record passed on)
                    copy_in = lambda o: _rhs(o["text"]).strip().rstrip(";").strip() in inputs and not clocked(o)
                    kept = lambda o: any(clocked(a) for a in all_assigns if _same_stmt(a, o) and a is not o)
                    reads = [o for o in mine if not o["sites"] & LHS and o["sites"] - NOT_READ]
                    base = n.split(".")[0]
                    h = []
                    if any(not copy_in(o) for o in assigns):
                        h.append("ORIGINATES")
                    if any(o["sites"] - {"DIRR_ASS"} or kept(o) for o in reads):
                        h.append("CONSUMES")
                    if any(copy_in(o) for o in assigns) or any(o["sites"] <= {"DIRR_ASS"} and not kept(o) for o in reads) \
                            or any(o["sites"] & {"DIRR_ASS", "ASSOC_ACTUAL"} for (el, _i), o in occ.items() if el == base):
                        h.append("FORWARDS")
                    entry["handling"] = h
                if arr == "ports":
                    mode = (e.get("dir") or "").lower()
                    only_config = all(all(p.startswith(("[generic]", "[static]", "[for-generate]")) for p in o["path"])
                                      for o in consts)
                    entry["boundary"] = {"mode": mode, "drive": "n/a" if mode == "in" else "undriven" if not assigns
                                         else "tied" if len(consts) == len(assigns) and only_config else "driven"}
                entry["storage"] = storage
                entry["constant_drivers"] = [{"at": o["id"], "value": _rhs(o["text"]).strip().rstrip(";").strip()}
                                             for o in consts]
                # the [generic] / [static] conditions under which the element is declared or driven, with where
                cfg = defaultdict(set)
                for o in mine:
                    if o["sites"] & (LHS | DECL):
                        for p in o["path"]:
                            if p.startswith(("[generic]", "[static]")):
                                cfg[p].add(o["id"])
                entry["configuration"] = [{"condition": c, "at": sorted(v)} for c, v in sorted(cfg.items())]
                conns = []
                for o in mine:
                    if "ASSOC_ACTUAL" in o["sites"] and "=>" in o["text"]:
                        inst = next((f for f in o["fr"] if f[0] == "instance"), None)
                        label = re.search(r"instance (\S+) \d+-\d+", o["ctx"] or "")
                        child = _instance_entity(ent["src"], inst[1]) if inst else None
                        formal = o["text"].split("=>")[0].strip()
                        conns.append({"at": o["id"], "instance": label.group(1) if label else None, "formal": formal,
                                      "mode": modes.get((child or "").lower(), {}).get(formal.lower())})
                entry["connections"] = conns
                entry["relationship"] = rel
                # traceability: every Occurrence ID used above resolves here to its source line
                entry["occurrences"] = [{"id": o["id"], "line": o["line"], "text": o["text"].strip()}
                                        for o in sorted(mine, key=lambda o: o["id"])]
                final[arr].append(entry)
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{module}.json"
    p.write_text(json.dumps(final, indent=1), encoding="utf-8")
    log(f"   wrote {p.relative_to(ROOT)}: {len(final['ports'])} ports, {len(final['signals'])} signals; "
        f"guarded records with no guard found: {no_guard}")
    return p


# ------------------------------------------------------------------ self-test without the model
def selftest_stub(module, log=print, where: dict | None = None) -> bool:
    """Build a perfect answer from the code reference and push it through check() and merge(). Every check must pass,
    every record must have its partner, agreement must be complete, and the final file must have exactly the fields
    of the format. Tests the plumbing; costs nothing."""
    ents = load_module(module, where)
    answers = {}
    for ent in ents:
        P = code_pairs(ent)
        ports = {e["name"] for e in ent["ports"]}
        for b, batch in enumerate(batches(ent)):
            arr = {"ports": [], "signals": []}
            for n in batch:
                per_at = defaultdict(set)                          # (type, at) -> targets
                for y, yi, x, xi, t in P:
                    if y == n:
                        per_at[(t, yi)].add(x)
                    if x == n:
                        per_at[(MIRROR[t], xi)].add(y)
                grp = defaultdict(set)                             # (type, targets) -> occurrences
                for (t, a), xs in per_at.items():
                    grp[(t, tuple(sorted(xs)))].add(a)
                rel = [{"type": t, "targets": list(xs), "at": sorted(ats)} for (t, xs), ats in grp.items()]
                arr["ports" if n in ports else "signals"].append({"name": n, "functionality": "stub.", "relationship": rel})
            answers[(ent["entity"], b)] = ({"names": batch, "raw": ""}, arr)
    res = check(module, psha="stub", answers=answers, ents=ents, log=log)
    p = merge(module, res, ents=ents, out_dir=Path(_where(module, where)["out"]) / "stub_map", log=log)
    final = json.loads(p.read_text(encoding="utf-8"))
    want_p = ["name", "entity", "functionality", "boundary", "storage", "constant_drivers", "configuration", "connections",
              "relationship", "occurrences"]
    want_s = ["name", "entity", "kind", "functionality", "storage", "constant_drivers", "configuration", "connections",
              "relationship", "occurrences"]
    bad = [e["name"] for e in final["ports"] if [k for k in e if k != "handling"] != want_p] + \
          [e["name"] for e in final["signals"] if [k for k in e if k != "handling"] != want_s]
    bad += [e["name"] for a in final.values() for e in a if ("handling" in e) != ("." in e["name"])]
    bad_r = [(e["name"], r["type"]) for a in final.values() for e in a for r in e["relationship"]
             if set(r) - {"type", "targets", "at", "guard", "partner_at", "bits"}
             or (("guard" in r) != (r["type"] in GUARDED)) or (r["type"] in GUARDED and not r.get("guard"))]
    # traceability: every Occurrence ID in the file resolves to a line of its element, and every partner is found
    ids = {(e["entity"], e["name"]): {o["id"]: o["line"] for o in e["occurrences"]} for a in final.values() for e in a}
    untraced = [(e["name"], "at", i) for a in final.values() for e in a
                for i in [i for r in e["relationship"] for i in r["at"]] + [c["at"] for c in e["constant_drivers"]]
                + [c["at"] for c in e["connections"]] + [i for c in e["configuration"] for i in c["at"]]
                if i not in ids[(e["entity"], e["name"])]]
    untraced += [(e["name"], "partner_at", x, i) for a in final.values() for e in a for r in e["relationship"]
                 for x in r["targets"] for i in (r["partner_at"].get(x) or [None]) if i not in ids.get((e["entity"], x), {})]
    ok = not res["issues"] and not res["diagnostics"] and res["pairing"].get("without partner", 0) == 0 and \
        res["agreement"].get("both") == res["agreement"].get("reference pairs") and not bad and not bad_r \
        and not untraced
    log(f"   final-format check: entries with wrong fields {len(bad)}, records with wrong keys {len(bad_r)}, "
        f"Occurrence IDs that do not resolve to a line {len(untraced)} {untraced[:3]}")
    log(f"   stub self-test: {'PASS' if ok else 'FAIL'}")
    return ok
