"""Structure stage: code finds the enclosing structure of every extract-inventory occurrence, BEFORE classify.

Pipeline position:  knowledge (LLM) -> extract (code) -> STRUCTURE (code, this file) -> classify (LLM) -> validate (LLM)

Why code: finding the enclosing structure is a parsing problem with one right answer. Run 6 measured the LLM on it:
classify got 185 of 661 chains wrong, and validate still left 21 wrong after being handed the correct chain for each.
All failures were at the if / branch / case-alternative level. Here a VHDL grammar answers it exactly.

Method: parse each file once with tree-sitter's VHDL grammar (tree-sitter-language-pack 1.20.0), index every name
node, match each inventory row (element, line, Name As Written, order on the line) to its node, walk up the ancestors.
Adapted from the repo-root vhdl_occurrence_context.py (left unedited). Changes that file needed:
  - every frame carries its span [first line, last line], not only its start;
  - the if / case block is a frame of its own, as well as the branch / alternative holding the occurrence;
  - rows are matched to the extract inventory's own occurrences, by column, so two occurrences on one line
    (a whole if-then-else written on one line) get their own chains;
  - port-map formals, component port clauses and labels are not candidates, because extract does not count them,
    and a field's declaration is its base's declaration line, as extract rule B.4 says.
Comments are separate nodes in the grammar, so no comment text can reach a frame or a condition.

OUTPUT, added to every inventory row:
  construct_chain  outermost -> innermost, each {"type", "span": [first, last], ...type-specific fields}
                   architecture {name, of} | declarative_part | entity {name} | port_clause | process {label,
                   sensitivity} | if {label} | branch {kind: then/elsif/else, arm, condition} | case {selector} |
                   case_alternative {choice} | generate {label, scheme} | generate_branch {kind, condition} |
                   loop {scheme} | instance {label} | port_map | when_else | with_select | function/procedure {name}
  path_condition   what must hold at the occurrence; an elsif/else arm carries not (...) of every earlier arm
  context_text     the chain as one line, innermost first, for the occurrence table's Context column
  column           1-based column of the occurrence on its line

Named deviation: LAsset section III-A.3 describes modular RTL parsing as LLM-based. Handing the model a deterministic
structure profile is an addition to the paper's method and must be logged as one.
"""
from __future__ import annotations

import contextlib, io, json, os, sys
from collections import defaultdict
from pathlib import Path

from tree_sitter_language_pack import get_parser

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BUILDER_DIR = ROOT / "bahavioral_patterns_of_assets/annotation_pack_elements/occurrence_prompts_v2/rulebook_edits"
_PARSER = get_parser("vhdl")
_TREES: dict[str, object] = {}


# ------------------------------------------------------------------ text helpers
def _txt(n) -> str:
    """Node text with comments removed and whitespace collapsed."""
    if n is None:
        return ""
    src, base, cuts, stack = n.text, n.start_byte, [], [n]
    while stack:
        m = stack.pop()
        if m.type == "comment":
            cuts.append((m.start_byte - base, m.end_byte - base)); continue
        stack.extend(m.children)
    out, pos = [], 0
    for a, b in sorted(cuts):
        out.append(src[pos:a]); pos = b
    out.append(src[pos:])
    return " ".join(b"".join(out).decode(errors="replace").split())


def _norm(s: str) -> str:
    return "".join(s.lower().split())


def _first_line(n) -> int:
    return n.start_point[0] + 1


def _last_line(n) -> int:
    """Last line holding a token of the node. A node that ends at column 0 ends on the line before."""
    r, c = n.end_point
    return r if c == 0 and r > n.start_point[0] else r + 1


def _up(n, types):
    while n is not None:
        if n.type in types:
            return n
        n = n.parent
    return None


def _contains(outer, inner) -> bool:
    return outer.start_byte <= inner.start_byte and inner.end_byte <= outer.end_byte


def _label(n) -> str | None:
    for c in n.children:
        if c.type == "label":
            return _txt(c).rstrip(":").strip()
    return None


def _cond_of(branch) -> str | None:
    for c in branch.children:
        if c.type == "conditional_expression":
            return _txt(c)
    return None


def _strip(c: str | None) -> str:
    """Drop parentheses that wrap the WHOLE condition: '(a = 1)' -> 'a = 1'; '(a) or (b)' is left alone."""
    c = (c or "").strip()
    while c.startswith("(") and c.endswith(")"):
        depth = 0
        for i, ch in enumerate(c):
            depth += (ch == "(") - (ch == ")")
            if depth == 0 and i < len(c) - 1:
                return c                               # the first '(' closes before the end: not one wrapper
        c = c[1:-1].strip()
    return c


def _atomic(c: str) -> bool:
    """One term, no space outside parentheses: rising_edge(clk_i), EN_ZKNE."""
    depth = 0
    for ch in c:
        depth += (ch == "(") - (ch == ")")
        if depth == 0 and ch == " ":
            return False
    return True


def _neg(c: str | None) -> str:
    c = _strip(c)
    return f"not {c}" if _atomic(c) else f"not ({c})"


def _choice_list(choices_node) -> list[str]:
    """`a | b | c` -> ['a', 'b', 'c']; `others` -> ['others']."""
    if choices_node is None:
        return ["?"]
    return [_txt(c) for c in choices_node.children if c.type not in ("|", "comment")] or ["?"]


def _is_range(c: str) -> bool:
    return any(w in c.lower().split() for w in ("to", "downto"))


def _sel_cond(sel: str, choices: list[str], all_choices: list[str]) -> str | None:
    """The condition a case / with-select arm stands for.
       single choice      sel = a
       several, or range  sel in {a, b}
       others             not (sel in {every other choice of the same case})"""
    if [c.lower() for c in choices] == ["others"]:
        rest = [c for c in all_choices if c.lower() != "others"]
        return f"not ({sel} in {{{', '.join(rest)}}})" if rest else None
    if len(choices) == 1 and not _is_range(choices[0]):
        return f"{sel} = {choices[0]}"
    return f"{sel} in {{{', '.join(choices)}}}"


def _when_arms(cw) -> list[tuple]:
    """Arms of a conditional assignment `y <= a when c1 else b when c2 else d`: [(waveforms, condition or None)]."""
    arms, stack = [], [cw]
    while stack:
        n = stack.pop(0)
        wf = next((c for c in n.children if c.type == "waveforms"), None)
        cn = next((c for c in n.children if c.type == "conditional_expression"), None)
        if wf is not None:
            arms.append((wf, cn))
        stack[0:0] = [c for c in n.children if c.type == "alternative_conditional_waveforms"]
    return arms


def _select_arms(sw) -> list[tuple]:
    """Arms of `with s select y <= a when c1, b when c2 | c3, d when others`: [(waveforms, [choices])]."""
    arms, stack = [], [sw]
    while stack:
        n = stack.pop(0)
        wf = next((c for c in n.children if c.type == "waveforms"), None)
        ch = next((c for c in n.children if c.type == "choices"), None)
        if wf is not None:
            arms.append((wf, _choice_list(ch)))
        stack[0:0] = [c for c in n.children if c.type == "alternative_selected_waveforms"]
    return arms


_STATIC: dict[int, set] = {}
_OPS = {"true", "false", "not", "and", "or", "xor", "nand", "nor", "xnor", "mod", "rem", "abs"}


def _static_names(node) -> set:
    """Generics and constants declared in the node's own file (package constants are not visible here)."""
    root = node
    while root.parent is not None:
        root = root.parent
    if root.id not in _STATIC:
        names, st = set(), [root]
        while st:
            n = st.pop(); st.extend(n.children)
            if n.type in ("constant_declaration", "constant_interface_declaration") or \
                    (n.type.endswith("interface_declaration") and _up(n, ("generic_clause",)) is not None):
                for c in n.children:
                    if c.type == "identifier_list":
                        names |= {_txt(i).lower() for i in c.children if i.type == "identifier"}
                    elif c.type == "identifier":
                        names.add(_txt(c).lower())
        _STATIC[root.id] = names
    return _STATIC[root.id]


def _tag(c: str, raw: str, node) -> str:
    """'[static] c' when every name in the condition is a generic or constant of this file: the condition is fixed
    when the design is built, so it selects hardware and gates nothing at run time. Conservative: a condition with
    one unresolved name (a package constant, a variable, a function) stays untagged."""
    ids = {w.lower() for w in __import__("re").findall(r"[A-Za-z_]\w*",
                                                        __import__("re").sub(r'"[^"]*"|\'.\'', " ", raw or ""))}
    return f"[static] {c}" if ids and ids <= (_static_names(node) | _OPS) and ids - _OPS else c


def tree(path):
    key = str(Path(path).resolve())
    if key not in _TREES:
        _TREES[key] = _PARSER.parse(Path(path).read_bytes())
    return _TREES[key]


# ------------------------------------------------------------------ candidates
def _candidates(root) -> dict[int, list[dict]]:
    """Every name node that could be an occurrence, indexed by line, in column order.

    Not candidates, because extract does not count them: labels, port-map formals (left of =>), names in a
    component declaration's port clause, and a record field's suffix (`addr` in `bus.addr` is not signal `addr`).
    A record prefix is lifted to its full selected name, so `ctrl` in `ctrl.state` reads `ctrl.state`.
    """
    by_line: dict[int, list[dict]] = defaultdict(list)
    seen, stack = set(), [root]
    while stack:
        n = stack.pop()
        stack.extend(reversed(n.children))
        if n.type not in ("simple_name", "identifier"):
            continue
        p = n.parent
        if p is not None and p.type == "label":
            continue
        if p is not None and p.type == "selected_name" and p.children and p.children[0].id != n.id:
            continue
        if _up(n, ("component_declaration",)) is not None:
            continue
        assoc = _up(n, ("named_association_element",))
        if assoc is not None:
            kids = [c for c in assoc.children if c.is_named]
            if kids and _contains(kids[0], n):
                continue
        hit = n
        while hit.parent is not None and hit.parent.type == "selected_name" and hit.parent.children[0].id == hit.id:
            hit = hit.parent
        if hit.id in seen:
            continue
        seen.add(hit.id)
        decl = n.type == "identifier" and _up(n, ("signal_interface_declaration", "signal_declaration",
                                                  "variable_declaration", "constant_declaration")) is not None
        by_line[_first_line(hit)].append({"node": hit, "base": _norm(_txt(n)), "full": _norm(_txt(hit)),
                                          "col": hit.start_point[1], "decl": decl})
    for v in by_line.values():
        v.sort(key=lambda h: h["col"])
    return by_line


def _matches(h: dict, element: str) -> bool:
    e = _norm(element)
    if "." in e:
        return h["full"] == e or h["full"].startswith(e + ".") or h["full"].startswith(e + "(")
    return h["base"] == e


def _field_decl(h: dict, element: str) -> bool:
    """Extract rule B.4: a field has no declaration of its own; the line declaring its base is its declaration."""
    return "." in element and h["decl"] and h["base"] == _norm(element).split(".")[0]


# ------------------------------------------------------------------ the chain
def _frame(type_: str, n, **kw) -> dict:
    f = {"type": type_, "span": [_first_line(n), _last_line(n)]}
    f.update({k: v for k, v in kw.items() if v not in (None, "")})
    return f


_ARM = {"if": "then", "elsif": "elsif", "else": "else"}


def construct_chain(node) -> tuple[list[dict], list[str]]:
    """Frames outermost -> innermost, and the path condition.

    path_condition reads as a conjunction, outermost first. Every construct that selects between alternatives
    contributes: an if / elsif / else arm (else and elsif carry not (...) of every earlier arm), a case alternative
    (sel = a | sel in {a, b} | not (sel in {every other choice}) for `others`), a when-else arm, a with-select arm,
    and an if/elsif/else-generate branch ([generic] ...). A for-generate or for-loop adds its index range.
    An occurrence that IS a condition is not guarded by that condition, only by the arms before it.
    """
    frames, path = [], []
    child, n = node, node.parent
    while n is not None:
        t = n.type
        if t == "if_statement":
            branches = [c for c in n.children if c.type in ("if", "elsif", "else")]
            earlier = []
            for i, b in enumerate(branches, 1):
                if b.id == child.id:
                    c = _cond_of(b)
                    in_cond = any(x.type == "conditional_expression" and _contains(x, node) for x in b.children)
                    frames.append(_frame("branch", b, kind=_ARM[b.type], arm=i, condition=_strip(c) if c else None,
                                         static=True if c and _tag("x", c, node) != "x" else None))
                    path[:0] = [_tag(_neg(e), e, node) for e in earlier] + \
                               ([_tag(_strip(c), c, node)] if c and not in_cond else [])
                    break
                if _cond_of(b):
                    earlier.append(_cond_of(b))
            frames.append(_frame("if", n, label=_label(n)))
        elif t == "case_statement_alternative":
            case = n.parent
            sel = _strip(next((_txt(c) for c in case.children if c.type == "expression"), "?"))
            choices = _choice_list(next((c for c in n.children if c.type == "choices"), None))
            everyone = [x for a in case.children if a.type == "case_statement_alternative"
                        for x in _choice_list(next((c for c in a.children if c.type == "choices"), None))]
            frames.append(_frame("case_alternative", n, choice=" | ".join(choices),
                                 choices=choices if len(choices) > 1 else None))
            cond = _sel_cond(sel, choices, everyone)
            if cond:
                path.insert(0, cond)
        elif t == "case_statement":
            frames.append(_frame("case", n, label=_label(n),
                                 selector=_strip(next((_txt(c) for c in n.children if c.type == "expression"), None))))
        elif t == "process_statement":
            frames.append(_frame("process", n, label=_label(n),
                                 sensitivity=next((_txt(c) for c in n.children if c.type == "sensitivity_list"), None)))
        elif t in ("if_generate", "elsif_generate", "else_generate"):
            sibs = [s for s in n.parent.children if s.type in ("if_generate", "elsif_generate", "else_generate")]
            earlier = [_cond_of(s) for s in sibs[:[s.id for s in sibs].index(n.id)] if _cond_of(s)]
            c = _cond_of(n)
            in_cond = any(x.type == "conditional_expression" and _contains(x, node) for x in n.children)
            frames.append(_frame("generate_branch", n, kind=t.split("_")[0], condition=_strip(c) if c else None))
            path[:0] = [f"[generic] {_neg(e)}" for e in earlier] + ([f"[generic] {_strip(c)}"] if c and not in_cond else [])
        elif t.endswith("generate_statement"):
            scheme = "for" if t.startswith("for") else "if" if t.startswith("if") else "case" if t.startswith("case") else None
            rng = next((_txt(c) for c in n.children if c.type == "parameter_specification"), None)
            frames.append(_frame("generate", n, label=_label(n), scheme=scheme, range=rng))
            if rng:
                path.insert(0, f"[for-generate] {rng}")
        elif t == "loop_statement":
            sch = next((c for c in n.children if c.type in ("for_loop", "while_loop")), None)
            frames.append(_frame("loop", n, label=_label(n), scheme=_txt(sch) if sch else None))
            if sch is not None:
                path.insert(0, f"[loop] {_txt(sch)}")
        elif t in ("assertion_statement", "concurrent_assertion_statement"):
            frames.append(_frame("assertion", n))       # a check, not hardware: nothing here drives anything
        elif t == "component_instantiation_statement":
            frames.append(_frame("instance", n, label=_label(n)))
        elif t == "port_map_aspect":
            frames.append(_frame("port_map", n))
        elif t == "generic_map_aspect":
            frames.append(_frame("generic_map", n))
        elif any(c.type == "conditional_waveforms" for c in n.children):
            # when-else, concurrent or (VHDL-2008) sequential: which arm holds the occurrence?
            cw = next(c for c in n.children if c.type == "conditional_waveforms")
            arm = None
            if _contains(cw, node):                       # not the target, which every arm assigns
                arms = _when_arms(cw)
                for k, (wf, cn) in enumerate(arms, 1):
                    earlier = [_txt(x[1]) for x in arms[:k - 1] if x[1] is not None]
                    if _contains(wf, node) or (cn is not None and _contains(cn, node)):
                        arm = (k, _strip(_txt(cn)) if cn is not None else None, len(arms))
                        path[:0] = [_tag(_neg(e), e, node) for e in earlier] + \
                                   ([_tag(_strip(_txt(cn)), _txt(cn), node)]
                                    if cn is not None and _contains(wf, node) else [])
                        break
            frames.append(_frame("when_else", n, arm=arm and arm[0], arms=arm and arm[2],
                                 condition=arm and arm[1]))
        elif any(c.type == "selected_waveforms" for c in n.children):
            # with-select: which arm holds the occurrence?
            sw = next(c for c in n.children if c.type == "selected_waveforms")
            sel = _strip(next((_txt(c) for c in n.children if c.type == "expression"), "?"))
            arm = None
            if _contains(sw, node):
                arms = _select_arms(sw)
                everyone = [x for _w, chs in arms for x in chs]
                for k, (wf, chs) in enumerate(arms, 1):
                    if _contains(wf, node):
                        arm = (k, " | ".join(chs))
                        cond = _sel_cond(sel, chs, everyone)
                        if cond:
                            path.insert(0, cond)
                        break
            frames.append(_frame("with_select", n, selector=sel, arm=arm and arm[0], choice=arm and arm[1]))
        elif t in ("function_body", "procedure_body"):
            nm = n.child_by_field_name("designator")
            frames.append(_frame(t.split("_")[0], n, name=_txt(nm) if nm else None))
        elif t == "block_statement":
            frames.append(_frame("block", n, label=_label(n)))
        elif t == "port_clause":
            frames.append(_frame("port_clause", n))
        elif t == "entity_declaration":
            frames.append(_frame("entity", n, name=_txt(n.child_by_field_name("name"))))
        elif t == "architecture_body":
            if child is not None and "declarative" in child.type:
                frames.append(_frame("declarative_part", child))
            frames.append(_frame("architecture", n, name=_txt(n.child_by_field_name("name")),
                                 of=_txt(n.child_by_field_name("entity"))))
        child, n = n, n.parent
    frames.reverse()
    return frames, path


def key(f: dict) -> str:
    """Short name of a frame, as the tests and the Context text use it."""
    if f["type"] == "branch":
        return f"{f['kind']} branch"
    if f["type"] == "generate_branch":
        return f"generate {f['kind']} branch"
    return f["type"]


def render(chain: list[dict]) -> str:
    """Innermost first: 'else branch 193-196 in if 190-197 in ... in architecture 44-294'."""
    out = []
    for f in reversed(chain):
        extra = f.get("choice") or f.get("selector") or f.get("label") or ""
        out.append(f"{key(f).replace('_', ' ')}{' ' + extra if extra and f['type'] != 'branch' else ''} "
                   f"{f['span'][0]}-{f['span'][1]}")
    return " in ".join(out)


# ------------------------------------------------------------------ the stage
PACK_MODULES = {"boot_rom", "trng_cache"}      # module sets run 6's extract knows by name


def _flat_elements(module: str):
    """Closed set from parsed_tuning18/<module>.json (flat format) in the shape run 6's extract expects."""
    d = json.loads((ROOT / "parsed_tuning18" / f"{module}.json").read_text(encoding="utf-8"))
    by_ent = {e: [] for e in d["entities"]}
    for x in d["ports"] + d["signals"]:
        by_ent.setdefault(x["entity"], []).append({k: x[k] for k in ("name", "dir", "type") if k in x})
    return [(e, v) for e, v in by_ent.items() if v]


def extract_inventory(modules=("boot_rom", "trng_cache")) -> tuple[list[dict], dict]:
    """Run 6's own code extract, unchanged: jobs and their occurrence inventory. Restores the working directory.

    `modules` holds run-6 set names ("boot_rom", "trng_cache") and/or plain module names ("neorv32_spi"). A plain
    module takes its closed set from parsed_tuning18/ and its RTL from RTL_data/ or RTL_heldout/.
    """
    sys.path.insert(0, str(BUILDER_DIR))
    import build_occurrence_notebook_v2 as B
    cwd = os.getcwd()
    try:
        os.chdir(B.ROOT)
        g = {"__name__": "nb"}
        with contextlib.redirect_stdout(io.StringIO()):
            for c in (B.C_SETUP, B.C_PROMPTS, B.C_INPUTS, B.C_CHECKS):
                exec(c, g)
        jobs = []
        for m in modules:
            if m in PACK_MODULES:
                js = g["build_jobs"](g["MODULES"][m])
                for j in js:
                    j["path"] = str(Path(B.ROOT) / g["RTL_DIR"] / f"{j['module']}.vhd")
            else:
                rtl = next((ROOT / d / f"{m}.vhd" for d in ("RTL_data", "RTL_heldout")
                            if (ROOT / d / f"{m}.vhd").exists()), None)
                if rtl is None:
                    raise FileNotFoundError(f"{m}.vhd in neither RTL_data/ nor RTL_heldout/")
                keep = g["load_elements"], g["RTL_DIR"]
                g["load_elements"], g["RTL_DIR"] = _flat_elements, rtl.parent
                try:
                    js = g["build_jobs"]([m])
                finally:
                    g["load_elements"], g["RTL_DIR"] = keep
                for j in js:
                    j["path"] = str(rtl)
            jobs += js
        for j in jobs:
            j["inventory"] = g["code_inventory"](j)
        return jobs, g
    finally:
        os.chdir(cwd)


def attach(jobs: list[dict]) -> dict:
    """Add construct_chain, path_condition, context_text and column to every inventory row."""
    stats = {"rows": 0, "matched": 0, "unmatched": [], "name_mismatch": []}
    for j in jobs:
        cand = _candidates(tree(j["path"]).root_node)
        for element, rows in j["inventory"].items():
            by_line = defaultdict(list)
            for r in rows:
                by_line[r["Occurrence Lines"]].append(r)
            for ln, rs in by_line.items():
                hits = [h for h in cand.get(ln, []) if _matches(h, element)]
                if not hits:
                    hits = [h for h in cand.get(ln, []) if _field_decl(h, element)]
                rs.sort(key=lambda r: r["Occurrence ID"])
                for k, r in enumerate(rs):
                    stats["rows"] += 1
                    if k >= len(hits):
                        r["construct_chain"] = r["path_condition"] = r["context_text"] = None
                        stats["unmatched"].append((j["module"], j["entity"], element, ln, r["Name As Written"]))
                        continue
                    h = hits[k]
                    naw = _norm(r["Name As Written"])
                    if not (naw.startswith(h["full"]) or h["full"].startswith(naw) or naw.startswith(h["base"])):
                        stats["name_mismatch"].append((j["entity"], element, ln, r["Name As Written"], h["full"]))
                    ch, pa = construct_chain(h["node"])
                    r.update({"column": h["col"] + 1, "construct_chain": ch, "path_condition": pa,
                              "context_text": render(ch)})
                    stats["matched"] += 1
    return stats


def row(jobs, module, element, line, k=0) -> dict | None:
    """The k-th inventory row (in Occurrence ID order) of an element on a line."""
    rs = sorted((r for j in jobs if j["module"] == module for r in j["inventory"].get(element, [])
                 if r["Occurrence Lines"] == line), key=lambda r: r["Occurrence ID"])
    return rs[k] if k < len(rs) else None


def write_outputs(jobs, out_dir) -> list[str]:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    by_mod = {}
    for j in jobs:
        ent = by_mod.setdefault(j["module"], {}).setdefault(j["entity"], {})
        for el, rows in j["inventory"].items():
            ent.setdefault(el, []).extend(rows)
    for mod, ents in by_mod.items():
        (out_dir / f"{mod}.json").write_text(json.dumps(
            {"schema": "structure-stage-v2", "module": mod, "built_by": "tree-sitter VHDL grammar; no model",
             "entities": ents}, indent=1), encoding="utf-8")
    return sorted(by_mod)


# ------------------------------------------------------------------ hand-read self-tests
# Every expected span was read by hand from the source file, not taken from this parser or from the old finder.
# Each case: module, element, line, k (which occurrence of the element on that line), the innermost frames.
HAND_PACK = [   # the lines run 6 got wrong
    ("neorv32_boot_rom", "rdata", 48, 0, [("then branch", 47, 48), ("if", 47, 49), ("process", 45, 50)]),
    ("neorv32_boot_rom", "rden", 60, 0, [("elsif branch", 59, 60), ("if", 57, 61), ("process", 55, 62)]),
    ("neorv32_boot_rom", "rden", 64, 0, [("when_else", 64, 64)]),
    ("neorv32_trng", "enable", 105, 0, [("then branch", 104, 106), ("if", 104, 120), ("then branch", 103, 120),
                                        ("if", 103, 121), ("elsif branch", 96, 121), ("if", 92, 122),
                                        ("process", 90, 123)]),
    ("neorv32_trng", "fifo_clr", 101, 0, [("elsif branch", 96, 121), ("if", 92, 122), ("process", 90, 123)]),
    ("neorv32_trng", "sample_sreg", 357, 0, [("then branch", 355, 357), ("if", 355, 361),
                                             ("elsif branch", 353, 361), ("if", 349, 362), ("process", 347, 363)]),
    ("neorv32_trng", "clk_i", 25, 0, [("port_clause", 24, 29)]),
    ("neorv32_cache", "cache_o.we", 194, 0, [("else branch", 193, 196), ("if", 190, 197), ("elsif branch", 189, 197),
                                             ("if", 186, 205), ("case_alternative", 178, 205), ("case", 164, 267)]),
    ("neorv32_cache", "ctrl_nxt", 200, 0, [("then branch", 199, 200), ("if", 199, 204), ("else branch", 198, 204),
                                           ("if", 186, 205), ("case_alternative", 178, 205), ("case", 164, 267)]),
    ("neorv32_cache", "bus_req_o", 202, 0, [("else branch", 201, 203), ("if", 199, 204), ("else branch", 198, 204)]),
    ("neorv32_cache", "bus_req_o", 217, 0, [("then branch", 216, 217), ("if", 216, 218),
                                            ("case_alternative", 214, 221), ("case", 164, 267)]),
    ("neorv32_cache", "ctrl_nxt.buf_dir", 173, 0, [("then branch", 171, 173), ("if", 171, 174),
                                                   ("elsif branch", 170, 175), ("if", 168, 176),
                                                   ("case_alternative", 166, 176)]),
    ("neorv32_cache", "ctrl_nxt.state", 265, 0, [("case_alternative", 263, 265), ("case", 164, 267)]),
]
HAND_BUGS = [   # the four defects of the old regex finder
    # spi: case choices are quoted literals; the old finder blanks them to " "
    ("neorv32_spi", "tx_fifo.avail", 288, 0, [("then branch", 288, 294), ("if", 288, 295), ("case_alternative", 284, 295)]),
    ("neorv32_spi", "spi_clk_en", 299, 0, [("then branch", 299, 303), ("if", 299, 304), ("case_alternative", 297, 304)]),
    ("neorv32_spi", "ctrl.cpha", 300, 0, [("then branch", 300, 301), ("if", 300, 302), ("then branch", 299, 303),
                                          ("if", 299, 304), ("case_alternative", 297, 304)]),
    # debug_dtm: a whole if-then-else-end-if on line 123; tap_ctrl_state sits in the then arm AND the else arm
    ("neorv32_debug_dtm", "tap_ctrl_state", 123, 0, [("then branch", 123, 123), ("if", 123, 123),
                                                     ("case_alternative", 123, 123)]),
    ("neorv32_debug_dtm", "tap_ctrl_state", 123, 1, [("else branch", 123, 123), ("if", 123, 123),
                                                     ("case_alternative", 123, 123)]),
    # cpu_cp_crypto: with-select (456-460) and when-else (463-465) inside an if-generate (452)
    ("neorv32_cpu_cp_crypto", "rs2_sel", 456, 0, [("with_select", 456, 460)]),
    ("neorv32_cpu_cp_crypto", "rol_in", 463, 0, [("when_else", 463, 465)]),
]


def _innermost(r, n):
    return [(key(f), f["span"][0], f["span"][1]) for f in reversed(r["construct_chain"])][:n]


def selftest(jobs, cases) -> list[str]:
    fails = []
    for mod, el, ln, k, want in cases:
        r = row(jobs, mod, el, ln, k)
        if r is None or not r.get("construct_chain"):
            on_line = sorted({e for j in jobs if j["module"] == mod for e, rs in j["inventory"].items()
                              for x in rs if x["Occurrence Lines"] == ln})
            fails.append(f"{mod}:{el}@{ln}#{k}: no row with a chain (elements on that line: {on_line})"); continue
        got = _innermost(r, len(want))
        if got != want:
            fails.append(f"{mod}:{el}@{ln}#{k}\n      want {want}\n      got  {got}")
    mods = {c[0] for c in cases}

    def chk(cond, msg):
        if not cond:
            fails.append(msg)

    if "neorv32_cache" in mods:
        r = row(jobs, "neorv32_cache", "cache_o.we", 194)
        chk(r and any(p.startswith("not (") and "host_req_i.rw" in p for p in r["path_condition"]),
            f"cache_o.we@194: the else arm's path lacks the negated condition: {r and r['path_condition']}")
        r = row(jobs, "neorv32_cache", "ctrl_nxt", 200)
        chk(r and any(f.get("choice") == "S_LOOKUP" for f in r["construct_chain"]),
            "ctrl_nxt@200: the case alternative's choice should be S_LOOKUP (S_DOWNLOAD_REQ is the value assigned)")
    if "neorv32_spi" in mods:
        r = row(jobs, "neorv32_spi", "spi_clk_en", 299)
        chk(r and any(f.get("choice") == '"101"' for f in r["construct_chain"]),
            f"spi_clk_en@299: case choice should read \"101\": {r and [f.get('choice') for f in r['construct_chain']]}")
        chk(r and any(f.get("selector") == "rtx_engine.state" for f in r["construct_chain"]),
            "spi_clk_en@299: case selector should read rtx_engine.state")
    if "neorv32_debug_dtm" in mods:
        a, b = row(jobs, "neorv32_debug_dtm", "tap_ctrl_state", 123, 0), row(jobs, "neorv32_debug_dtm", "tap_ctrl_state", 123, 1)
        chk(a and b and a["column"] < b["column"], "tap_ctrl_state@123: the two occurrences should sit at different columns")
        chk(b and any(p.startswith("not (") and "tap_sync.tms" in p for p in b["path_condition"]),
            f"tap_ctrl_state@123#1 (else arm): path lacks not (tap_sync.tms = '0'): {b and b['path_condition']}")
    if "neorv32_cpu_cp_crypto" in mods:
        r = row(jobs, "neorv32_cpu_cp_crypto", "sm4", 268)
        dp = [f for f in (r or {}).get("construct_chain") or [] if f["type"] == "declarative_part"]
        chk(r and dp and dp[0]["span"][0] <= 121 and dp[0]["span"][1] >= 268 and
            not any(f["type"] == "function" for f in r["construct_chain"]),
            f"sm4@268: should be in the declarative part (which contains function xperm8_f at 121), not in a function "
            f"or the statement part: {r and r['context_text']}")
        r = row(jobs, "neorv32_cpu_cp_crypto", "rs2_sel", 456)
        chk(r and any(f["type"] == "generate" for f in r["construct_chain"]) and
            any(p.startswith("[generic]") and "EN_ZKNE" in p for p in r["path_condition"]),
            f"rs2_sel@456: should sit in the if-generate at 452 with [generic] EN_ZKNE... in its path: {r and r['path_condition']}")

    # exact path_condition, read by hand from the source; each covers one gap the first version left open
    for mod, el, ln, k, want in PATHS:
        if mod not in mods:
            continue
        r = row(jobs, mod, el, ln, k)
        chk(r is not None and r["path_condition"] == want,
            f"{mod}:{el}@{ln}#{k} path\n      want {want}\n      got  {r and r['path_condition']}")

    # none of the three old forms may survive anywhere
    bad = {"'= others'": [], "'a | b' used as one value": [], "doubled parentheses": []}
    for j in jobs:
        for rows in j["inventory"].values():
            for r in rows:
                for p in r.get("path_condition") or []:
                    if "= others" in p.lower():
                        bad["'= others'"].append((j["module"], r["Occurrence Lines"], p))
                    if " | " in p and " in {" not in p:
                        bad["'a | b' used as one value"].append((j["module"], r["Occurrence Lines"], p))
                    q = p.split("] ", 1)[1] if p.startswith("[") else p
                    if q.startswith("not ((") and _strip(q[5:-1]) != q[5:-1]:
                        bad["doubled parentheses"].append((j["module"], r["Occurrence Lines"], p))
    for lab, xs in bad.items():
        chk(not xs, f"{len(xs)} path entries with {lab}, e.g. {xs[:2]}")
    return fails


G_CRYPTO = "[generic] EN_ZKNE or EN_ZKND or EN_ZKSED"
PATHS = [   # module, element, line, k, the exact path_condition, derived by hand from the source
    # boot_rom 57-60: if (rstn_i = '0') ... elsif rising_edge(clk_i) -- the doubled parentheses case
    ("neorv32_boot_rom", "rden", 60, 0, ["not (rstn_i = '0')", "rising_edge(clk_i)"]),
    # boot_rom 64: bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');
    ("neorv32_boot_rom", "rdata", 64, 0, ["rden = '1'"]),          # value of arm 1
    ("neorv32_boot_rom", "rden", 64, 0, []),                       # it IS arm 1's condition: nothing before it
    ("neorv32_boot_rom", "bus_rsp_o.data", 64, 0, []),             # the target, assigned whichever arm is taken
    # cache 263-265: when others, after the seven named states of `case ctrl.state`
    # cache 214-217: when S_CLEAR => if (READ_ONLY = false) then bus_req_o.fence <= '1';  READ_ONLY is a generic
    ("neorv32_cache", "bus_req_o", 217, 0, ["ctrl.state = S_CLEAR", "[static] READ_ONLY = false"]),
    ("neorv32_cache", "ctrl_nxt.state", 265, 0,
     ["not (ctrl.state in {S_IDLE, S_LOOKUP, S_DIRECT_RSP, S_CLEAR, S_DOWNLOAD_REQ, S_DOWNLOAD_RSP, S_DOWNLOAD_DONE})"]),
    # crypto 463-465: rol_in <= aes.mix2 when (not EN_ZKSED) else sm4.rnd when (not EN_ZKNE) and (not EN_ZKND)
    #                  else aes.mix2 when (funct12(8) = '0') else sm4.rnd;   (inside the if-generate at 452)
    ("neorv32_cpu_cp_crypto", "rol_in", 463, 0, [G_CRYPTO]),        # target
    # EN_ZKSED, EN_ZKNE, EN_ZKND are generics (fixed at build time -> [static]); funct12 is a signal
    ("neorv32_cpu_cp_crypto", "aes.mix2", 463, 0, [G_CRYPTO, "[static] not EN_ZKSED"]),
    ("neorv32_cpu_cp_crypto", "sm4.rnd", 464, 0, [G_CRYPTO, "[static] not (not EN_ZKSED)",
                                                  "[static] (not EN_ZKNE) and (not EN_ZKND)"]),
    ("neorv32_cpu_cp_crypto", "aes.mix2", 465, 0, [G_CRYPTO, "[static] not (not EN_ZKSED)",
                                                   "[static] not ((not EN_ZKNE) and (not EN_ZKND))", "funct12(8) = '0'"]),
    ("neorv32_cpu_cp_crypto", "funct12", 465, 0, [G_CRYPTO, "[static] not (not EN_ZKSED)",
                                                  "[static] not ((not EN_ZKNE) and (not EN_ZKND))"]),
    ("neorv32_cpu_cp_crypto", "sm4.rnd", 465, 0, [G_CRYPTO, "[static] not (not EN_ZKSED)",
                                                  "[static] not ((not EN_ZKNE) and (not EN_ZKND))", "not (funct12(8) = '0')"]),
    # crypto 456-460 and 468-472: with funct12(11 downto 10) select ... when "00", "01", "10", others
    ("neorv32_cpu_cp_crypto", "rs2", 457, 0, [G_CRYPTO, 'funct12(11 downto 10) = "00"']),
    ("neorv32_cpu_cp_crypto", "rs2", 460, 0, [G_CRYPTO, 'not (funct12(11 downto 10) in {"00", "01", "10"})']),
    ("neorv32_cpu_cp_crypto", "rol_in", 469, 0, [G_CRYPTO, 'funct12(11 downto 10) = "00"']),
    ("neorv32_cpu_cp_crypto", "rol_in", 470, 1, [G_CRYPTO, 'funct12(11 downto 10) = "01"']),
    ("neorv32_cpu_cp_crypto", "rol_in", 472, 0, [G_CRYPTO, 'not (funct12(11 downto 10) in {"00", "01", "10"})']),
]


# ------------------------------------------------------------------ report
def report(jobs, stats, g, cases, examples=()) -> None:
    print("1. parse")
    for p in sorted({j["path"] for j in jobs}):
        print(f"   {Path(p).name:26s} parse errors: {'YES' if tree(p).root_node.has_error else 'none'}")

    print(f"\n2. coverage: extract inventory rows {stats['rows']} | given a chain {stats['matched']} | "
          f"unmatched {len(stats['unmatched'])} | matched name differs from 'Name As Written' "
          f"{len(stats['name_mismatch'])}")
    for u in stats["unmatched"][:10]:
        print("   unmatched:", u)
    for m in stats["name_mismatch"][:10]:
        print("   name differs:", m)

    fails = selftest(jobs, cases)
    print(f"\n3. hand-read self-test: {len(cases)} chain cases + targeted checks -> "
          f"{'PASS' if not fails else f'{len(fails)} FAIL'}")
    for f in fails:
        print("   FAIL", f)

    c = compare_with_finder(jobs, g)
    print(f"\n4. against the old regex finder (if / branch / case / alternative / process / loop spans): "
          f"identical {c['same']} of {c['rows']}")
    for k, lab in (("label_blanked", "defect 1: quoted case choice blanked in the old label (old, new)"),
                   ("reversed_span", "defect 2: old finder gives a span that ends before it starts"),
                   ("same_line_split", "defect 2: lines where occurrences of one element sit in different arms "
                                       "(one chain from a line-based finder, one each from the grammar)"),
                   ("declarative_boundary", "defect 3: grammar says declarative part, old finder says architecture body"),
                   ("when_else_with_select", "defect 4: inside a when-else / with-select, for which the old finder has no frame"),
                   ("unexplained", "span differences NOT explained by the four known defects")):
        print(f"   {len(c[k]):4d}  {lab}")
        for x in c[k][:3 if k != "unexplained" else 10]:
            print(f"            {x}")

    print("\n5. construct_chain examples")
    for mod, el, ln, k in examples:
        r = row(jobs, mod, el, ln, k)
        if r:
            print(f"   {mod}:{el} @ {ln}  (Occurrence ID {r['Occurrence ID']}, column {r['column']})")
            print(f"      context_text:   {r['context_text']}")
            print(f"      path_condition: {r['path_condition']}")
            print("      construct_chain:\n" + "\n".join(f"         {json.dumps(f)}" for f in r["construct_chain"]))


# ------------------------------------------------------------------ comparison with the old regex finder
_OLD = {"if": "if", "branch": "branch", "case": "case", "alternative": "case_alternative", "process": "process",
        "loop": "loop"}


def _old_chain(g, j, line):
    return g["structure_chain"](g["structures_of"](j["src"]), line)


def compare_with_finder(jobs, g) -> dict:
    """Span agreement with the regex finder run 6 was scored against, on the control levels only (containers use
    different line conventions: the old finder starts 'architecture body' at `begin`, the grammar at the header).
    Differences are sorted into the old finder's four known defects; anything else is listed as unexplained."""
    res = {"rows": 0, "same": 0, "label_blanked": [], "reversed_span": [], "same_line_split": [],
           "declarative_boundary": [], "when_else_with_select": [], "unexplained": []}
    S_cache = {}
    for j in jobs:
        S_ = S_cache.setdefault(id(j["src"]), g["structures_of"](j["src"]))
        # a span ending before it starts can never contain its line, so it drops OUT of every chain instead of
        # appearing wrong in one; find those lines from the whole structure list
        reversed_at = {s["lines"][0] for s in S_ if s["lines"][1] < s["lines"][0]}
        for element, rows in j["inventory"].items():
            per_line = defaultdict(list)
            for r in rows:
                if not r.get("construct_chain"):
                    continue
                res["rows"] += 1
                ln = r["Occurrence Lines"]
                old_ch = g["structure_chain"](S_, ln)
                old = {(_OLD[s["kind"]], s["lines"][0], s["lines"][1]) for s in old_ch if s["kind"] in _OLD}
                new = {("branch" if f["type"] == "branch" else f["type"], f["span"][0], f["span"][1])
                       for f in r["construct_chain"] if f["type"] in _OLD.values()}
                where = (j["module"], element, ln, r["Occurrence ID"])
                per_line[ln].append(r)
                # defect 1: a quoted case choice blanked in the old label
                for s in old_ch:
                    if s["kind"] == "alternative" and not (s.get("opened by") or "").replace('"', "").strip():
                        nf = next((f for f in r["construct_chain"] if f["type"] == "case_alternative"
                                   and f["span"] == list(s["lines"])), None)
                        if nf and nf.get("choice"):
                            res["label_blanked"].append(where + (repr(s.get("opened by")), nf["choice"]))
                # defect 3: declarative part the old finder calls architecture body
                if any(f["type"] == "declarative_part" for f in r["construct_chain"]) and \
                        any(s["kind"] == "architecture body" for s in old_ch):
                    res["declarative_boundary"].append(where)
                # defect 4: when-else / with-select, which the old finder has no frame for
                if any(f["type"] in ("when_else", "with_select") for f in r["construct_chain"]):
                    res["when_else_with_select"].append(where)
                if old == new:
                    res["same"] += 1
                elif ln in reversed_at:
                    res["reversed_span"].append(where + (sorted(old - new), sorted(new - old)))   # defect 2
                else:
                    res["unexplained"].append(where + (sorted(old - new), sorted(new - old)))
            # defect 2, second face: two occurrences on one line in different arms; a line-based finder gives both
            # the same chain, the grammar gives each its own
            for ln, rs in per_line.items():
                chains = {json.dumps(x["construct_chain"]) for x in rs}
                if len(rs) > 1 and len(chains) > 1:
                    res["same_line_split"].append((j["module"], element, ln, len(rs)))
    return res
