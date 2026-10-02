"""relmap_proto.py -- PROTOTYPE code-only relation reader (Step 1 feasibility probe).

Read-only on the repo. Writes nothing into it. Purpose: measure how far a token-level
VHDL reader (no LLM, no external parser) can fill the six roadmap relations over the
closed set in parsed_tuning18/, and where it must say "unknown".

Self-test first: _selftest() asserts hand-read lines from RTL_data/neorv32_wdt.vhd,
neorv32_cpu_cp_muldiv.vhd and neorv32_bus.vhd. Nothing is reported if it fails.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(r"E:\jobs\ff\test\Prepoison_subset")
RTL = REPO / "RTL_data"
PARSED = REPO / "parsed_tuning18"

# ---------------------------------------------------------------- lexer ---

_KW = {
    "architecture", "entity", "is", "begin", "end", "process", "if", "then", "elsif",
    "else", "case", "when", "loop", "for", "while", "generate", "port", "map", "generic",
    "signal", "variable", "constant", "type", "subtype", "record", "of", "array", "in",
    "out", "inout", "buffer", "component", "block", "others", "null", "return", "downto",
    "to", "and", "or", "xor", "xnor", "nand", "nor", "not", "mod", "rem", "abs", "sll",
    "srl", "sla", "sra", "rol", "ror", "select", "with", "assert", "report", "severity",
    "wait", "until", "function", "procedure", "use", "library", "package", "body",
    "attribute", "alias", "exit", "next", "range", "linkage", "shared", "file", "new",
    "all", "open", "after", "transport", "inertial", "reject", "guarded", "label",
    "postponed", "pure", "impure", "units", "group", "literal", "access", "disconnect",
    "configuration", "on", "elsegenerate",
}

_TOK = re.compile(
    r"(?P<ws>\s+)"
    r"|(?P<cmt>--[^\n]*)"
    r"|(?P<str>\"[^\"\n]*\")"
    r"|(?P<bit>[0-9]*[a-zA-Z]?\"[^\"\n]*\")"
    r"|(?P<id>[A-Za-z][A-Za-z0-9_]*)"
    r"|(?P<num>[0-9][0-9_]*(?:\.[0-9_]+)?(?:[eE][+-]?[0-9]+)?)"
    r"|(?P<op><=|:=|=>|/=|>=|\*\*|<>|\?\?|.)",
    re.S,
)


class Tok:
    __slots__ = ("k", "t", "lo", "line")

    def __init__(self, k, t, lo, line):
        self.k, self.t, self.lo, self.line = k, t, lo, line

    def __repr__(self):
        return f"<{self.k}:{self.t}@{self.line}>"


def tokenize(text):
    """-> [Tok]. Comments dropped. Character literals folded to kind 'lit'."""
    out = []
    line = 1
    i = 0
    n = len(text)
    while i < n:
        m = _TOK.match(text, i)
        if not m:
            i += 1
            continue
        s = m.group(0)
        k = m.lastgroup
        if k == "ws" or k == "cmt":
            line += s.count("\n")
            i = m.end()
            continue
        if s == "'":
            # char literal only when the previous token cannot end an expression;
            # otherwise it is the attribute tick (cnt'length, rs1_i'left).
            prev = out[-1] if out else None
            attr_ctx = prev is not None and (
                prev.k in ("id", "kw") or prev.t in (")", "]")
            )
            if not attr_ctx and i + 2 < n and text[i + 2] == "'":
                out.append(Tok("lit", text[i:i + 3], i, line))
                i += 3
                continue
            out.append(Tok("op", "'", i, line))
            i += 1
            continue
        if k == "id":
            lo = s.lower()
            out.append(Tok("kw" if lo in _KW else "id", s, lo, line))
        elif k in ("str", "bit", "num"):
            out.append(Tok("lit", s, s.lower(), line))
        else:
            out.append(Tok("op", s, s, line))
        line += s.count("\n")
        i = m.end()
    return out


def kw(t, *names):
    return t is not None and t.k == "kw" and t.lo in names


# ------------------------------------------------- structural splitting ---

def split_units(toks):
    """-> [(kind, name, start, end)] for entity / architecture-of at top level."""
    units = []
    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        if kw(t, "entity") and i + 2 < n and toks[i + 1].k == "id" and kw(toks[i + 2], "is"):
            units.append(["entity", toks[i + 1].lo, i, None])
        elif (kw(t, "architecture") and i + 4 < n and toks[i + 1].k == "id"
              and kw(toks[i + 2], "of") and toks[i + 3].k == "id"):
            units.append(["architecture", toks[i + 3].lo, i, None])
        i += 1
    for j, u in enumerate(units):
        u[3] = units[j + 1][2] if j + 1 < len(units) else n
    return [tuple(u) for u in units]


def find_arch_begin(toks, start, end):
    """Index of the architecture's own `begin`, skipping subprogram bodies."""
    i = start
    depth = 0
    while i < end:
        t = toks[i]
        if kw(t, "function", "procedure"):
            # subprogram body if an `is` follows before the `;`
            j = i + 1
            par = 0
            body = False
            while j < end:
                if toks[j].t == "(":
                    par += 1
                elif toks[j].t == ")":
                    par -= 1
                elif par == 0 and toks[j].t == ";":
                    break
                elif par == 0 and kw(toks[j], "is"):
                    body = True
                    break
                j += 1
            if body:
                depth += 1
            i = j + 1
            continue
        if kw(t, "begin"):
            if depth == 0:
                return i
            i += 1
            continue
        if kw(t, "end"):
            if depth > 0:
                depth -= 1
        i += 1
    return None


# ---------------------------------------------------------- name reader ---

_ATTR_SKIP = 1


def read_names(toks, a, b):
    """Every dotted name in toks[a:b], index expressions included.

    -> [(dotted_lower, line)]. `std_ulogic_vector(unsigned(cnt)+1)` yields
    std_ulogic_vector, unsigned and cnt; the caller resolves which are elements.
    `dev_req(i).stb` yields dev_req.stb and i. `cnt'length` yields cnt.
    """
    out = []
    i = a
    while i < b:
        t = toks[i]
        if t.k != "id":
            i += 1
            continue
        parts = [t.lo]
        line = t.line
        i += 1
        while i < b:
            if toks[i].t == "(":
                # index / slice / call argument -- skip the group, names inside are
                # emitted by the outer loop when we recurse below
                d = 0
                j = i
                while j < b:
                    if toks[j].t == "(":
                        d += 1
                    elif toks[j].t == ")":
                        d -= 1
                        if d == 0:
                            break
                    j += 1
                out.extend(read_names(toks, i + 1, j))
                i = j + 1
                continue
            if toks[i].t == "." and i + 1 < b and toks[i + 1].k in ("id", "kw"):
                parts.append(toks[i + 1].lo)
                i += 2
                continue
            if toks[i].t == "'" and i + 1 < b and toks[i + 1].k in ("id", "kw"):
                i += 2  # attribute name is not an element
                continue
            break
        out.append((".".join(parts), line))
    return out


def read_target(toks, a, b):
    """The assignment target's dotted path, with index groups removed.
    `dev_req(i).stb` -> ('dev_req.stb', ['i']).  Returns (path, extra_names)."""
    parts = []
    extra = []
    i = a
    if i >= b or toks[i].k != "id":
        return None, []
    parts.append(toks[i].lo)
    i += 1
    while i < b:
        if toks[i].t == "(":
            d = 0
            j = i
            while j < b:
                if toks[j].t == "(":
                    d += 1
                elif toks[j].t == ")":
                    d -= 1
                    if d == 0:
                        break
                j += 1
            extra.extend(read_names(toks, i + 1, j))
            i = j + 1
            continue
        if toks[i].t == "." and i + 1 < b and toks[i + 1].k in ("id", "kw"):
            parts.append(toks[i + 1].lo)
            i += 2
            continue
        break
    return ".".join(parts), extra


# ------------------------------------------------------- statement walk ---

class Assign:
    __slots__ = ("target", "rhs", "guards", "kind", "line", "in_reset", "clock",
                 "reset", "gen", "proc", "is_var", "rhs_shape")

    def __init__(self, **kw_):
        for k in self.__slots__:
            setattr(self, k, kw_.get(k))


def _cond_names(toks, a, b):
    return read_names(toks, a, b)


def _matching(toks, i, end):
    """i is at '('; return index of its ')'."""
    d = 0
    j = i
    while j < end:
        if toks[j].t == "(":
            d += 1
        elif toks[j].t == ")":
            d -= 1
            if d == 0:
                return j
        j += 1
    return end - 1


def _stmt_end(toks, i, end):
    """Index of the ';' closing a simple statement starting at i."""
    d = 0
    j = i
    while j < end:
        if toks[j].t == "(":
            d += 1
        elif toks[j].t == ")":
            d -= 1
        elif toks[j].t == ";" and d == 0:
            return j
        j += 1
    return end


def _rhs_shape(toks, a, b):
    """'copy' when the right-hand side is one plain name (possibly indexed/sliced or
    wrapped only in type-conversion calls), 'expr' otherwise, 'const' if literals only."""
    ops = {"and", "or", "xor", "xnor", "nand", "nor", "not", "mod", "rem", "abs",
           "sll", "srl", "sla", "sra", "rol", "ror"}
    sym = {"+", "-", "*", "/", "&", "=", "/=", "<", ">", "<=", ">=", "**"}
    has_op = False
    ids = 0
    lits = 0
    d = 0
    for j in range(a, b):
        t = toks[j]
        if t.t == "(":
            d += 1
        elif t.t == ")":
            d -= 1
        elif t.k == "kw" and t.lo in ops:
            has_op = True
        elif t.k == "op" and t.t in sym:
            has_op = True
        elif t.k == "id":
            ids += 1
        elif t.k == "lit":
            lits += 1
    if ids == 0:
        return "const"
    if has_op:
        return "expr"
    return "copy"


def walk(toks, a, b, ctx, out):
    """Sequential/concurrent statement walk. ctx carries the guard stack."""
    i = a
    while i < b:
        t = toks[i]
        if t.t == ";":
            i += 1
            continue
        # ---- if ----
        if kw(t, "if"):
            j = i + 1
            while j < b and not kw(toks[j], "then", "generate"):
                if toks[j].t == "(":
                    j = _matching(toks, j, b)
                j += 1
            conds = list(_cond_names(toks, i + 1, j))
            if kw(toks[j] if j < b else None, "generate"):
                # if-generate
                k = _gen_end(toks, j + 1, b)
                c2 = dict(ctx)
                c2["gen"] = ctx.get("gen", []) + [(x, l, "generate") for x, l in conds]
                walk_region(toks, j + 1, k, c2, out)
                i = _skip_end(toks, k, b)
                continue
            # a bare `if rising_edge(clk)` with no reset arm still names the clock
            edge_here = [x for x, _ in conds if x in ("rising_edge", "falling_edge")]
            if edge_here:
                ctx = dict(ctx)
                ctx["clock"] = [x for x, _ in conds
                                if x not in ("rising_edge", "falling_edge")]
                conds = []
            # detect the async-reset test: `if (X = '0'/'1') then ... elsif *_edge(clk)`
            is_reset = _is_reset_if(toks, i, b)
            branch_end, branches = _if_branches(toks, j + 1, b)
            for bstart, bend, bconds, kind in branches:
                c2 = dict(ctx)
                allc = conds if kind == "then" else bconds
                if is_reset and kind == "then":
                    c2 = dict(ctx)
                    c2["in_reset"] = True
                    c2["reset"] = [x for x, _ in conds]
                elif is_reset and kind == "elsif":
                    c2["clock"] = [x for x, _ in bconds if not x.endswith("_edge")]
                    c2["clock"] = [x for x in c2["clock"]
                                   if x not in ("rising_edge", "falling_edge")]
                else:
                    c2["guards"] = ctx.get("guards", []) + \
                        [(x, l, "if") for x, l in (conds if kind != "elsif" else bconds)]
                walk(toks, bstart, bend, c2, out)
            i = branch_end
            continue
        # ---- case ----
        if kw(t, "case"):
            j = i + 1
            while j < b and not kw(toks[j], "is"):
                if toks[j].t == "(":
                    j = _matching(toks, j, b)
                j += 1
            sel = list(_cond_names(toks, i + 1, j))
            cend = _block_end(toks, j + 1, b, "case")
            c2 = dict(ctx)
            c2["guards"] = ctx.get("guards", []) + [(x, l, "case") for x, l in sel]
            walk(toks, j + 1, cend, c2, out)
            i = _skip_end(toks, cend, b)
            continue
        # ---- when (inside case) ----
        if kw(t, "when"):
            j = i + 1
            while j < b and toks[j].t != "=>":
                if toks[j].t == "(":
                    j = _matching(toks, j, b)
                j += 1
            i = j + 1
            continue
        # ---- loop ----
        if kw(t, "for", "while"):
            j = i + 1
            while j < b and not kw(toks[j], "loop", "generate"):
                if toks[j].t == "(":
                    j = _matching(toks, j, b)
                j += 1
            rng = list(_cond_names(toks, i + 1, j))
            if kw(toks[j] if j < b else None, "generate"):
                k = _gen_end(toks, j + 1, b)
                c2 = dict(ctx)
                c2["gen"] = ctx.get("gen", []) + [(x, l, "for-generate") for x, l in rng]
                walk_region(toks, j + 1, k, c2, out)
                i = _skip_end(toks, k, b)
                continue
            lend = _block_end(toks, j + 1, b, "loop")
            c2 = dict(ctx)
            c2["loopvars"] = set(ctx.get("loopvars", set())) | \
                ({toks[i + 1].lo} if i + 1 < b and toks[i + 1].k == "id" else set())
            walk(toks, j + 1, lend, c2, out)
            i = _skip_end(toks, lend, b)
            continue
        # ---- nested process / generate at concurrent level handled by walk_region ----
        if kw(t, "end"):
            return
        # ---- assignment or call ----
        e = _stmt_end(toks, i, b)
        op = None
        for j in range(i, e):
            if toks[j].t in ("<=", ":="):
                # `<=` can be the relational operator; only an assignment when it is the
                # first one at depth 0 and the left side is a plain name
                op = j
                break
            if toks[j].t in ("(",):
                j2 = _matching(toks, j, e)
                if j2 > j:
                    pass
        if op is not None:
            tgt, extra = read_target(toks, i, op)
            if tgt:
                out.append(Assign(
                    target=tgt,
                    rhs=read_names(toks, op + 1, e) + extra,
                    guards=list(ctx.get("guards", [])),
                    kind=ctx.get("kind", "comb"),
                    line=toks[i].line,
                    in_reset=bool(ctx.get("in_reset")),
                    clock=list(ctx.get("clock") or []),
                    reset=list(ctx.get("reset") or []),
                    gen=list(ctx.get("gen") or []),
                    proc=ctx.get("proc"),
                    is_var=(toks[op].t == ":="),
                    rhs_shape=_rhs_shape(toks, op + 1, e),
                ))
        i = e + 1


def _is_reset_if(toks, i, b):
    """True when this `if` is the async-reset arm of a clocked process."""
    j = i
    depth = 0
    while j < b:
        if kw(toks[j], "if"):
            depth += 1
        elif kw(toks[j], "end") and kw(toks[j + 1] if j + 1 < b else None, "if"):
            depth -= 1
            if depth == 0:
                return False
        elif depth == 1 and kw(toks[j], "elsif"):
            for k in range(j, min(j + 12, b)):
                if toks[k].k == "id" and toks[k].lo in ("rising_edge", "falling_edge"):
                    return True
                if kw(toks[k], "then"):
                    break
            return False
        j += 1
    return False


def _if_branches(toks, a, b):
    """-> (index after `end if;`, [(start, end, conds, kind)])"""
    branches = []
    depth = 1
    start = a
    conds = []
    kind = "then"
    i = a
    while i < b:
        t = toks[i]
        if kw(t, "if") and not kw(toks[i - 1] if i else None, "end"):
            depth += 1
        elif kw(t, "case"):
            depth += 1
        elif kw(t, "loop"):
            depth += 1
        elif kw(t, "end"):
            nx = toks[i + 1] if i + 1 < b else None
            if kw(nx, "if", "case", "loop"):
                depth -= 1
                if depth == 0:
                    branches.append((start, i, conds, kind))
                    return i + 3, branches
                i += 2
                continue
        elif depth == 1 and kw(t, "elsif"):
            branches.append((start, i, conds, kind))
            j = i + 1
            while j < b and not kw(toks[j], "then"):
                if toks[j].t == "(":
                    j = _matching(toks, j, b)
                j += 1
            conds = list(_cond_names(toks, i + 1, j))
            kind = "elsif"
            start = j + 1
            i = j + 1
            continue
        elif depth == 1 and kw(t, "else"):
            branches.append((start, i, conds, kind))
            conds = list(conds)
            kind = "else"
            start = i + 1
        i += 1
    branches.append((start, b, conds, kind))
    return b, branches


def _block_end(toks, a, b, what):
    depth = 1
    i = a
    while i < b:
        if kw(toks[i], what if what != "case" else "case"):
            depth += 1
        elif kw(toks[i], "if") and what == "if":
            depth += 1
        elif kw(toks[i], "end"):
            nx = toks[i + 1] if i + 1 < b else None
            if kw(nx, what):
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        i += 1
    return b


def _gen_end(toks, a, b):
    depth = 1
    i = a
    while i < b:
        if kw(toks[i], "generate"):
            depth += 1
        elif kw(toks[i], "end") and kw(toks[i + 1] if i + 1 < b else None, "generate"):
            depth -= 1
            if depth == 0:
                return i
            i += 1
        i += 1
    return b


def _skip_end(toks, i, b):
    j = i
    while j < b and toks[j].t != ";":
        j += 1
    return j + 1


def walk_region(toks, a, b, ctx, out):
    """Concurrent region: processes, generates, instantiations, concurrent assignments."""
    i = a
    while i < b:
        t = toks[i]
        if t.t == ";":
            i += 1
            continue
        if kw(t, "end"):
            return
        # optional label
        lbl = None
        j = i
        if t.k == "id" and i + 1 < b and toks[i + 1].t == ":":
            lbl = t.lo
            j = i + 2
        nt = toks[j] if j < b else None
        if kw(nt, "process"):
            k = j + 1
            if k < b and toks[k].t == "(":
                k = _matching(toks, k, b) + 1
            bgn = k
            while bgn < b and not kw(toks[bgn], "begin"):
                bgn += 1
            pend = _proc_end(toks, bgn + 1, b)
            clocked = any(toks[x].k == "id" and toks[x].lo in ("rising_edge", "falling_edge")
                          for x in range(bgn, pend))
            c2 = dict(ctx)
            c2["proc"] = lbl
            c2["kind"] = "clocked" if clocked else "comb"
            walk(toks, bgn + 1, pend, c2, out)
            i = _skip_end(toks, pend, b)
            continue
        if kw(nt, "if", "for") and _has_generate(toks, j, b):
            hdr = j
            while hdr < b and not kw(toks[hdr], "generate"):
                hdr += 1
            gend = _gen_end(toks, hdr + 1, b)
            # BOUNDED. Handing `walk` the whole region let it run past `end generate`
            # and read later concurrent `when/else` assignments as sequential ones,
            # which turned every `when` condition into a data driver.
            walk(toks, j, gend, dict(ctx), out)
            i = _skip_end(toks, gend, b)
            continue
        if kw(nt, "block"):
            bgn = j
            while bgn < b and not kw(toks[bgn], "begin"):
                bgn += 1
            bend = _block_end(toks, bgn + 1, b, "block")
            walk_region(toks, bgn + 1, bend, dict(ctx), out)
            i = _skip_end(toks, bend, b)
            continue
        e = _stmt_end(toks, i, b)
        # instantiation?
        if lbl and _is_inst(toks, j, e):
            out.extend(_port_map(toks, j, e, lbl, ctx))
            i = e + 1
            continue
        # concurrent assignment (incl. when/else and with/select)
        if kw(nt, "with"):
            sel_end = j + 1
            while sel_end < e and not kw(toks[sel_end], "select"):
                sel_end += 1
            sel = read_names(toks, j + 1, sel_end)
            _conc_assign(toks, sel_end + 1, e, ctx, out, extra_guards=sel)
            i = e + 1
            continue
        _conc_assign(toks, j, e, ctx, out)
        i = e + 1


def _has_generate(toks, a, b):
    for j in range(a, min(a + 400, b)):
        if kw(toks[j], "generate"):
            return True
        if toks[j].t == ";":
            return False
    return False


def _proc_end(toks, a, b):
    depth = 0
    i = a
    while i < b:
        if kw(toks[i], "if", "case", "loop") and not kw(toks[i - 1] if i else None, "end"):
            depth += 1
        elif kw(toks[i], "end"):
            nx = toks[i + 1] if i + 1 < b else None
            if kw(nx, "process"):
                return i
            if kw(nx, "if", "case", "loop"):
                depth -= 1
                i += 1
        i += 1
    return b


def _is_inst(toks, a, b):
    for j in range(a, b - 1):
        if kw(toks[j], "port") and kw(toks[j + 1], "map"):
            return True
        if kw(toks[j], "generic") and kw(toks[j + 1], "map"):
            return True
    return False


def _port_map(toks, a, b, lbl, ctx):
    """Associations become two half-edges each; direction is resolved later."""
    out = []
    j = a
    while j < b - 1:
        if kw(toks[j], "port") and kw(toks[j + 1], "map"):
            break
        j += 1
    if j >= b - 1:
        return out
    k = j + 2
    while k < b and toks[k].t != "(":
        k += 1
    close = _matching(toks, k, b)
    # split at depth-1 commas
    d = 0
    seg = k + 1
    parts = []
    for x in range(k + 1, close):
        if toks[x].t == "(":
            d += 1
        elif toks[x].t == ")":
            d -= 1
        elif toks[x].t == "," and d == 0:
            parts.append((seg, x))
            seg = x + 1
    parts.append((seg, close))
    for s, e in parts:
        arrow = None
        for x in range(s, e):
            if toks[x].t == "=>":
                arrow = x
                break
        if arrow is None:
            continue
        formal, _ = read_target(toks, s, arrow)
        actual = read_names(toks, arrow + 1, e)
        out.append(Assign(target=f"@inst:{lbl}:{formal}", rhs=actual, guards=[],
                          kind="instance", line=toks[s].line, in_reset=False,
                          clock=[], reset=[], gen=list(ctx.get("gen") or []),
                          proc=lbl, is_var=False, rhs_shape="copy"))
    return out


def _conc_assign(toks, a, b, ctx, out, extra_guards=()):
    op = None
    for j in range(a, b):
        if toks[j].t == "<=":
            op = j
            break
        if toks[j].t == "(":
            j2 = _matching(toks, j, b)
    if op is None:
        return
    tgt, extra = read_target(toks, a, op)
    if not tgt:
        return
    # split waveform at `when`/`else` to separate guards from data
    guards = list(extra_guards)
    data_spans = []
    seg = op + 1
    j = op + 1
    d = 0
    mode = "data"
    while j < b:
        if toks[j].t == "(":
            d += 1
        elif toks[j].t == ")":
            d -= 1
        elif d == 0 and kw(toks[j], "when"):
            data_spans.append((seg, j))
            seg = j + 1
            mode = "cond"
        elif d == 0 and kw(toks[j], "else"):
            if mode == "cond":
                guards.extend(read_names(toks, seg, j))
            else:
                data_spans.append((seg, j))
            seg = j + 1
            mode = "data"
        j += 1
    if mode == "cond":
        guards.extend(read_names(toks, seg, b))
    else:
        data_spans.append((seg, b))
    rhs = []
    shapes = []
    for s, e in data_spans:
        rhs.extend(read_names(toks, s, e))
        shapes.append(_rhs_shape(toks, s, e))
    shape = "copy" if all(x in ("copy", "const") for x in shapes) and "copy" in shapes \
        else ("const" if all(x == "const" for x in shapes) else "expr")
    out.append(Assign(target=tgt, rhs=rhs + extra,
                      guards=ctx.get("guards", []) + [(x, l, "when-else") for x, l in guards],
                      kind="concurrent", line=toks[a].line, in_reset=False,
                      clock=[], reset=[], gen=list(ctx.get("gen") or []),
                      proc=None, is_var=False, rhs_shape=shape))


# ------------------------------------------------------------ resolution ---

_REC = re.compile(r"\btype\s+(\w+)\s+is\s+record\b(.*?)\bend\s+record\b", re.I | re.S)
_ARR = re.compile(r"\btype\s+(\w+)\s+is\s+array\s*\((.*?)\)\s*of\s+([A-Za-z]\w*)", re.I | re.S)
_FLD = re.compile(r"([\w\s,]+?)\s*:\s*([^;]+?)\s*;", re.I)
_TYPE_CACHE = {}


def type_registry(stem):
    """{record_type: [fields]} and {array_type: element_type}, from the package + module."""
    if stem in _TYPE_CACHE:
        return _TYPE_CACHE[stem]
    from importlib import import_module
    sys.path.insert(0, str(REPO))
    mask = import_module("stage_a")._mask_comments
    recs, arrs = {}, {}
    for p in (RTL / "neorv32_package.vhd", RTL / f"{stem}.vhd"):
        txt = mask(p.read_text(encoding="utf-8", errors="ignore"), vhdl=True)
        for nm, body in _REC.findall(txt):
            fs = []
            for fn, _ft in _FLD.findall(body):
                fs.extend(x.strip().lower() for x in fn.split(",") if x.strip())
            recs[nm.lower()] = fs
        for nm, _rng, el in _ARR.findall(txt):
            arrs[nm.lower()] = el.lower()
    _TYPE_CACHE[stem] = (recs, arrs)
    return recs, arrs


def base_type(t):
    return (t or "").split(":=")[0].split("(")[0].strip().lower()


def closed_set(stem):
    j = json.loads((PARSED / f"{stem}.json").read_text())
    per = defaultdict(dict)
    for p in j["ports"]:
        per[p["entity"].lower()][p["name"].lower()] = dict(p, kind="port")
    for s in j["signals"]:
        per[s["entity"].lower()][s["name"].lower()] = dict(s, kind="signal")
    return j, per


def resolve(name, elems):
    """Map a dotted source name onto a closed-set key, or None."""
    n = name.lower()
    if n in elems:
        return n
    parts = n.split(".")
    while len(parts) > 1:
        parts.pop()
        cand = ".".join(parts)
        if cand in elems:
            return cand
    return None


def analyse(stem):
    raw = (RTL / f"{stem}.vhd").read_text(encoding="utf-8", errors="ignore")
    toks = tokenize(raw)
    units = split_units(toks)
    parsed, per_ent = closed_set(stem)
    ent_arch = {}
    for kind, name, s, e in units:
        if kind == "architecture":
            ent_arch[name] = (s, e)
    result = {}
    for ename, elems in per_ent.items():
        if ename not in ent_arch:
            result[ename] = {"assigns": [], "elems": elems, "missing_arch": True}
            continue
        s, e = ent_arch[ename]
        bgn = find_arch_begin(toks, s, e)
        out = []
        if bgn is not None:
            walk_region(toks, bgn + 1, e, {"kind": "concurrent"}, out)
        result[ename] = {"assigns": out, "elems": elems, "missing_arch": False,
                         "span": (s, e)}
    return result, parsed


# ------------------------------------------------------- relation build ---

def build(stem):
    res, parsed = analyse(stem)
    mods = {}
    for ename, d in res.items():
        elems = d["elems"]
        rec = {n: {"driven_by": {}, "drives": {}, "controlled_by": {}, "controls": {},
                   "clock": set(), "reset": set(), "stmts": 0, "shapes": Counter(),
                   "gen": set(), "unresolved_rhs": Counter(), "var_rhs": 0,
                   "inst_driven": 0, "reset_only_stmts": 0,
                   "clock_fanout": 0, "reset_fanout": 0}
               for n in elems}
        var_drivers = defaultdict(set)

        def vlook(nm):
            """A variable name, or any variable it is a field of / whose field it is."""
            got = set()
            for k, v in var_drivers.items():
                if k == nm or k.startswith(nm + ".") or nm.startswith(k + "."):
                    got |= v
            return got

        # pass 1: variables, twice so that a := b := c chain settles
        for _ in range(3):
            for a in d["assigns"]:
                if a.is_var:
                    for nm, _ in a.rhs:
                        r = resolve(nm, elems)
                        if r:
                            var_drivers[a.target].add(r)
                        else:
                            var_drivers[a.target] |= vlook(nm)
        for a in d["assigns"]:
            if a.target.startswith("@inst:"):
                continue
            if a.is_var:
                continue
            t = resolve(a.target, elems)
            if t is None:
                continue
            r = rec[t]
            r["stmts"] += 1
            r["shapes"][a.rhs_shape] += 1
            if a.in_reset:
                r["reset_only_stmts"] += 1
            for g in a.gen:
                r["gen"].add(g[0])
            for c in a.clock:
                r["clock"].add(c)
            for c in a.reset:
                r["reset"].add(c)
            if a.in_reset:
                continue     # reset values are not data drivers
            for nm, ln in a.rhs:
                rr = resolve(nm, elems)
                if rr:
                    r["driven_by"].setdefault(rr, ln)
                    rec[rr]["drives"].setdefault(t, ln)
                elif vlook(nm):
                    r["var_rhs"] += 1
                    for vv in vlook(nm):
                        r["driven_by"].setdefault(vv, a.line)
                        rec[vv]["drives"].setdefault(t, a.line)
                else:
                    r["unresolved_rhs"][nm] += 1
            for nm, ln, site in a.guards:
                rr = resolve(nm, elems)
                if rr:
                    r["controlled_by"].setdefault(rr, (ln, site))
                    rec[rr]["controls"].setdefault(t, (ln, site))
        # ---- record broadcast: `whole <= other` reaches every matching field ----
        kids = defaultdict(list)
        for n in elems:
            if "." in n:
                kids[n.rsplit(".", 1)[0]].append(n.rsplit(".", 1)[1])
        recs, arrs = type_registry(stem)

        def vkids(n):
            """Field names reachable through n: real closed-set children, or -- for an
            array of records, which rtl_parse does NOT expand -- the element record's."""
            if n in kids:
                return set(kids[n]), True
            bt = base_type(elems[n]["type"]) if n in elems else ""
            while bt in arrs:
                bt = arrs[bt]
            return set(recs.get(bt, [])), False

        def side(n, f, real):
            return f"{n}.{f}" if real else n

        bcast = 0
        for a in d["assigns"]:
            if a.target.startswith("@inst:") or a.is_var or a.in_reset:
                continue
            t = resolve(a.target, elems)
            if t is None:
                continue
            tk, treal = vkids(t)
            if not tk:
                continue
            for nm, ln in a.rhs:
                rr = resolve(nm, elems)
                if rr is None or rr == t:
                    continue
                rk, rreal = vkids(rr)
                if not rk:
                    continue
                for f in (tk & rk):
                    tf, rf = side(t, f, treal), side(rr, f, rreal)
                    if tf not in rec or rf not in rec or tf == rf:
                        continue
                    if rf not in rec[tf]["driven_by"]:
                        bcast += 1
                    rec[tf]["driven_by"].setdefault(rf, ln)
                    rec[rf]["drives"].setdefault(tf, ln)
                    rec[tf]["shapes"]["record"] += 1
                    for c in a.clock:
                        rec[tf]["clock"].add(c)
                    for c in a.reset:
                        rec[tf]["reset"].add(c)
                    for g, gl, gs in a.guards:
                        gg = resolve(g, elems)
                        if gg:
                            rec[tf]["controlled_by"].setdefault(gg, (gl, gs))
        # instance port maps: actual is driven or drives depending on formal direction,
        # which we do not know here -> record both ends as "instance", flagged unknown.
        for a in d["assigns"]:
            if not a.target.startswith("@inst:"):
                continue
            for nm, ln in a.rhs:
                rr = resolve(nm, elems)
                if rr:
                    rec[rr]["inst_driven"] += 1
        # ---- clock / reset fan-out, read off every clocked process ----
        for n, r in rec.items():
            for c in r["clock"]:
                if c in rec:
                    rec[c]["clock_fanout"] += 1
            for c in r["reset"]:
                if c in rec:
                    rec[c]["reset_fanout"] += 1
        mods[ename] = (elems, rec)
    return mods, parsed


def fanout_verdict(r):
    """'clock' / 'reset' / 'clock+reset' / 'data' / 'none'."""
    data_use = bool(r["drives"]) or bool(r["controls"])
    tags = []
    if r["clock_fanout"]:
        tags.append("clock")
    if r["reset_fanout"]:
        tags.append("reset")
    if not tags:
        return "data" if data_use else "none"
    return ("+".join(tags)) + ("+data" if data_use else "_only")


def fanout_role(name, elems, rec, assigns):
    """clock / reset / none / unknown, from how the name is USED."""
    r = rec[name]
    used_clock = name in r["clock"]
    used_reset = name in r["reset"]
    return used_clock, used_reset


# ------------------------------------------------------------ self-test ---

def _get(stem, entity, name):
    mods, _ = build(stem)
    elems, rec = mods[entity]
    return rec[name]


def _selftest(verbose=False):
    """Hand-read lines. Every assertion names file and line."""
    fails = []

    def ck(cond, msg):
        if not cond:
            fails.append(msg)

    # ---- neorv32_wdt.vhd ----
    mods, _ = build("neorv32_wdt")
    elems, rec = mods["neorv32_wdt"]
    # line 140: clkgen_en_o <= ctrl.enable;
    ck(set(rec["clkgen_en_o"]["driven_by"]) == {"ctrl.enable"},
       f"wdt:140 clkgen_en_o driven_by = {set(rec['clkgen_en_o']['driven_by'])}")
    ck(rec["clkgen_en_o"]["shapes"]["copy"] == 1, "wdt:140 clkgen_en_o should be a copy")
    # line 141: prsc_tick <= clkgen_i(clk_div4096_c);
    ck(set(rec["prsc_tick"]["driven_by"]) == {"clkgen_i"},
       f"wdt:141 prsc_tick driven_by = {set(rec['prsc_tick']['driven_by'])}")
    # line 144: cnt_timeout <= '1' when (cnt_started='1') and (cnt=ctrl.timeout) else '0';
    ck(set(rec["cnt_timeout"]["controlled_by"]) == {"cnt_started", "cnt", "ctrl.timeout"},
       f"wdt:144 cnt_timeout controlled_by = {set(rec['cnt_timeout']['controlled_by'])}")
    ck(set(rec["cnt_timeout"]["driven_by"]) == set(),
       f"wdt:144 cnt_timeout driven_by = {set(rec['cnt_timeout']['driven_by'])}")
    # lines 90-97: ctrl.enable <= bus_req_i.data(...) under four nested conditions
    ck(set(rec["ctrl.enable"]["driven_by"]) == {"bus_req_i.data"},
       f"wdt:94 ctrl.enable driven_by = {set(rec['ctrl.enable']['driven_by'])}")
    ck({"bus_req_i.stb", "bus_req_i.rw", "bus_req_i.addr", "ctrl.lock"}
       <= set(rec["ctrl.enable"]["controlled_by"]),
       f"wdt:90-93 ctrl.enable controlled_by = {set(rec['ctrl.enable']['controlled_by'])}")
    ck(rec["ctrl.enable"]["clock"] == {"clk_i"},
       f"wdt:81 ctrl.enable clock = {rec['ctrl.enable']['clock']}")
    ck(rec["ctrl.enable"]["reset"] == {"rstn_sys_i"},
       f"wdt:73 ctrl.enable reset = {rec['ctrl.enable']['reset']}")
    # line 134: cnt <= ... unsigned(cnt)+1  -> self-driven, guarded by 131/133
    ck("cnt" in rec["cnt"]["driven_by"], "wdt:134 cnt must be driven by itself")
    ck({"ctrl.enable", "reset_wdt", "cnt_inc"} <= set(rec["cnt"]["controlled_by"]),
       f"wdt:131-133 cnt controlled_by = {set(rec['cnt']['controlled_by'])}")
    # line 161: rstn_o <= not (hw_rst_timeout or hw_rst_access);
    ck(set(rec["rstn_o"]["driven_by"]) == {"hw_rst_timeout", "hw_rst_access"},
       f"wdt:161 rstn_o driven_by = {set(rec['rstn_o']['driven_by'])}")
    ck(rec["rstn_o"]["shapes"]["expr"] == 1, "wdt:161 rstn_o is an expression, not a copy")
    # line 171: rstn_dbg_i is an ordinary control inside the clocked branch, NOT a reset
    ck("reset_cause" in rec["rstn_dbg_i"]["drives"] or
       "rstn_dbg_i" in rec["reset_cause"]["controlled_by"],
       "wdt:171 rstn_dbg_i must control reset_cause")
    ck(rec["reset_cause"]["reset"] == {"rstn_ext_i"},
       f"wdt:168 reset_cause reset = {rec['reset_cause']['reset']}")
    # line 83: bus_rsp_o.ack <= bus_req_i.stb  (a copy)
    ck(set(rec["bus_rsp_o.ack"]["driven_by"]) == {"bus_req_i.stb"},
       f"wdt:83 bus_rsp_o.ack driven_by = {set(rec['bus_rsp_o.ack']['driven_by'])}")

    # ---- neorv32_cpu_cp_muldiv.vhd ----
    mods, _ = build("neorv32_cpu_cp_muldiv")
    elems, rec = mods["neorv32_cpu_cp_muldiv"]
    # line 178: mul.dsp_z <= mul.dsp_x * mul.dsp_y;  inside `if FAST_MUL_EN generate`
    ck(set(rec["mul.dsp_z"]["driven_by"]) >= {"mul.dsp_x", "mul.dsp_y"},
       f"muldiv:178 mul.dsp_z driven_by = {set(rec['mul.dsp_z']['driven_by'])}")
    ck("fast_mul_en" in rec["mul.dsp_z"]["gen"],
       f"muldiv:161 mul.dsp_z gen = {rec['mul.dsp_z']['gen']}")
    # line 130: ctrl.cnt <= unsigned(ctrl.cnt)-1 under `case ctrl.state`
    ck("ctrl.state" in rec["ctrl.cnt"]["controlled_by"],
       f"muldiv:116 ctrl.cnt controlled_by = {set(rec['ctrl.cnt']['controlled_by'])}")
    # line 184: mul.prod clocked by clk_i with NO reset (process(clk_i) only)
    ck("clk_i" in rec["mul.prod"]["clock"],
       f"muldiv:183 mul.prod clock = {rec['mul.prod']['clock']}")
    # line 145: valid_o <= '1' when (ctrl.state = S_DONE) else '0';
    ck(set(rec["valid_o"]["controlled_by"]) == {"ctrl.state"},
       f"muldiv:145 valid_o controlled_by = {set(rec['valid_o']['controlled_by'])}")
    # line 97-99: valid_cmd from three ctrl_i fields
    ck({"ctrl_i.alu_cp_alu", "ctrl_i.ir_opcode", "ctrl_i.ir_funct12", "ctrl_i.ir_funct3"}
       <= set(rec["valid_cmd"]["controlled_by"]),
       f"muldiv:97 valid_cmd controlled_by = {set(rec['valid_cmd']['controlled_by'])}")
    # line 325-329: res_o driven by mul.prod and div.res under case ctrl_i.ir_funct3
    ck({"mul.prod", "div.res"} <= set(rec["res_o"]["driven_by"]),
       f"muldiv:325 res_o driven_by = {set(rec['res_o']['driven_by'])}")
    ck("ctrl_i.ir_funct3" in rec["res_o"]["controlled_by"],
       f"muldiv:323 res_o controlled_by = {set(rec['res_o']['controlled_by'])}")

    # ---- neorv32_bus.vhd ----
    mods, _ = build("neorv32_bus")
    # line 140: x_req_o.addr <= a_req_i.addr when (sel='0') else b_req_i.addr;
    elems, rec = mods["neorv32_bus_switch"]
    ck(set(rec["x_req_o.addr"]["driven_by"]) == {"a_req_i.addr", "b_req_i.addr"},
       f"bus:140 x_req_o.addr driven_by = {set(rec['x_req_o.addr']['driven_by'])}")
    ck(set(rec["x_req_o.addr"]["controlled_by"]) == {"sel"},
       f"bus:140 x_req_o.addr controlled_by = {set(rec['x_req_o.addr']['controlled_by'])}")
    # line 148: x_req_o.fence <= a_req_i.fence or b_req_i.fence;  (expr, no guard)
    ck(set(rec["x_req_o.fence"]["controlled_by"]) == set(),
       f"bus:148 x_req_o.fence must have no control")
    # line 61: a_req <= a_req or a_req_i.stb under `if (state = S_BUSY_A)`
    ck({"a_req", "a_req_i.stb"} <= set(rec["a_req"]["driven_by"]),
       f"bus:61 a_req driven_by = {set(rec['a_req']['driven_by'])}")
    ck("state" in rec["a_req"]["controlled_by"],
       f"bus:58 a_req controlled_by = {set(rec['a_req']['controlled_by'])}")
    # gateway line 377-378: port_req(i) <= req_i ; port_req(i).stb <= port_sel(i) and req_i.stb
    elems, rec = mods["neorv32_bus_gateway"]
    ck({"req_i", "port_sel", "req_i.stb"} <= set(rec["port_req"]["driven_by"]),
       f"bus:377 port_req driven_by = {set(rec['port_req']['driven_by'])}")
    # line 390-395: int_rsp.data <= tmp_v where tmp_v := tmp_v or port_rsp(i).data
    ck("port_rsp" in rec["int_rsp"]["driven_by"],
       f"bus:390 int_rsp driven_by (via variable) = {set(rec['int_rsp']['driven_by'])}")
    # line 416: keeper.halt <= port_sel(port_sel'left)
    ck(set(rec["keeper.halt"]["driven_by"]) == {"port_sel"},
       f"bus:416 keeper.halt driven_by = {set(rec['keeper.halt']['driven_by'])}")
    # line 422-427: keeper.cnt self-driven, controlled by keeper.busy
    ck("keeper.busy" in rec["keeper.cnt"]["controlled_by"],
       f"bus:417 keeper.cnt controlled_by = {set(rec['keeper.cnt']['controlled_by'])}")
    # io_switch line 617: dev_00_req_o <= dev_req(0)
    elems, rec = mods["neorv32_bus_io_switch"]
    ck(set(rec["dev_00_req_o"]["driven_by"]) == {"dev_req"},
       f"bus:617 dev_00_req_o driven_by = {set(rec['dev_00_req_o']['driven_by'])}")
    # io_switch line 660-664 inside for-generate + if-generate
    ck({"main_req", "main_req.stb"} <= set(rec["dev_req"]["driven_by"]),
       f"bus:660 dev_req driven_by = {set(rec['dev_req']['driven_by'])}")
    # amo_rmw line 813
    elems, rec = mods["neorv32_bus_amo_rmw"]
    ck({"alu_res", "core_req_i.data"} <= set(rec["sys_req_o.data"]["driven_by"]),
       f"bus:813 sys_req_o.data driven_by = {set(rec['sys_req_o.data']['driven_by'])}")
    ck("arbiter.state" in rec["sys_req_o.data"]["controlled_by"],
       f"bus:813 sys_req_o.data controlled_by = {set(rec['sys_req_o.data']['controlled_by'])}")
    # line 763: arbiter <= arbiter_nxt (whole-record copy)
    ck("arbiter_nxt" in rec["arbiter"]["driven_by"],
       f"bus:763 arbiter driven_by = {set(rec['arbiter']['driven_by'])}")

    # ---- neorv32_cpu_pmp.vhd: regression for the generate-overrun bug ----
    mods, _ = build("neorv32_cpu_pmp")
    elems, rec = mods["neorv32_cpu_pmp"]
    # line 244: acc_addr <= ctrl_i.pc_nxt when (ctrl_i.lsu_mo_we='0') else addr_ls_i;
    ck(set(rec["acc_addr"]["driven_by"]) == {"ctrl_i.pc_nxt", "addr_ls_i"},
       f"pmp:244 acc_addr driven_by = {set(rec['acc_addr']['driven_by'])}")
    ck(set(rec["acc_addr"]["controlled_by"]) == {"ctrl_i.lsu_mo_we"},
       f"pmp:244 acc_addr controlled_by = {set(rec['acc_addr']['controlled_by'])}")
    # line 321: the same name is a CONTROL of allow, never a driver of it
    ck("ctrl_i.lsu_mo_we" in rec["allow"]["controlled_by"],
       f"pmp:321 allow controlled_by = {set(rec['allow']['controlled_by'])}")
    ck("ctrl_i.lsu_mo_we" not in rec["allow"]["driven_by"],
       "pmp:321 lsu_mo_we must not be a data driver of allow")

    if fails:
        print("SELF-TEST FAILED (%d):" % len(fails))
        for f in fails:
            print("   -", f)
        return False
    print("SELF-TEST PASSED: %d hand-read assertions" % 34)
    return True


GT15 = ['neorv32_bus', 'neorv32_cache', 'neorv32_cpu', 'neorv32_cpu_cp_cfu',
        'neorv32_cpu_cp_muldiv', 'neorv32_cpu_pmp', 'neorv32_debug_dtm',
        'neorv32_hwspinlock', 'neorv32_imem', 'neorv32_spi', 'neorv32_sys',
        'neorv32_trng', 'neorv32_twi', 'neorv32_uart', 'neorv32_wdt']


def mention_index(stem):
    """{entity: set(lowercase dotted names and bare ids mentioned in its statements)}"""
    raw = (RTL / f"{stem}.vhd").read_text(encoding="utf-8", errors="ignore")
    toks = tokenize(raw)
    out = {}
    for kind, name, s, e in split_units(toks):
        if kind != "architecture":
            continue
        bgn = find_arch_begin(toks, s, e)
        if bgn is None:
            out[name] = set()
            continue
        names = set()
        for nm, _ in read_names(toks, bgn + 1, e):
            names.add(nm)
            parts = nm.split(".")
            while len(parts) > 1:
                parts.pop()
                names.add(".".join(parts))
        out[name] = names
    return out


def coverage():
    tot = Counter()
    per_mod = {}
    for stem in GT15:
        mods, parsed = build(stem)
        ment = mention_index(stem)
        c = Counter()
        for ename, (elems, rec) in mods.items():
            seen = ment.get(ename, set())
            for n in elems:
                r = rec[n]
                if r["driven_by"] or r["drives"] or r["stmts"]:
                    continue
                # silent: is the name in the statement text at all?
                if n in seen:
                    c["silent_but_mentioned"] += 1
                elif "." in n and n.rsplit(".", 1)[0] in seen:
                    c["silent_base_mentioned"] += 1
                else:
                    c["silent_absent"] += 1
        for ename, (elems, rec) in mods.items():
            for n, e in elems.items():
                r = rec[n]
                c["elements"] += 1
                if r["driven_by"]:
                    c["has_driver"] += 1
                if r["drives"]:
                    c["has_load"] += 1
                if r["controlled_by"]:
                    c["has_control"] += 1
                if r["controls"]:
                    c["is_a_control"] += 1
                c["fanout_" + fanout_verdict(r)] += 1
                if (r["driven_by"] or r["drives"] or r["controlled_by"] or r["controls"]
                        or r["clock_fanout"] or r["reset_fanout"]):
                    c["any_relation"] += 1
                if r["stmts"]:
                    c["assigned"] += 1
                if r["clock"]:
                    c["has_clock"] += 1
                if r["reset"]:
                    c["has_reset"] += 1
                if not r["driven_by"] and not r["drives"] and not r["stmts"]:
                    c["silent"] += 1
                if r["stmts"] > 1:
                    c["multi_driver"] += 1
                if r["shapes"] and all(k == "copy" for k in r["shapes"]) \
                        and not r["controlled_by"]:
                    c["copy_only"] += 1
                if r["unresolved_rhs"]:
                    c["unresolved_rhs_names"] += 1
                if r["inst_driven"]:
                    c["in_port_map"] += 1
                if "." in n:
                    c["field"] += 1
                if e["kind"] == "port":
                    c["port"] += 1
                else:
                    c["signal"] += 1
        per_mod[stem] = c
        tot.update(c)
    return tot, per_mod


if __name__ == "__main__":
    ok = _selftest()
    if not ok and "--force" not in sys.argv:
        sys.exit(1)
    tot, per = coverage()
    print()
    print("COVERAGE over the 15 ground-truth modules")
    n = tot["elements"]
    for k in ("elements", "port", "signal", "field", "any_relation", "assigned",
              "has_driver", "has_load", "has_control", "is_a_control",
              "has_clock", "has_reset", "copy_only", "multi_driver",
              "silent", "silent_absent", "silent_base_mentioned", "silent_but_mentioned",
              "unresolved_rhs_names", "in_port_map",
              "fanout_clock_only", "fanout_reset_only", "fanout_clock+reset_only",
              "fanout_clock+data", "fanout_reset+data", "fanout_data", "fanout_none"):
        print(f"  {k:24s} {tot[k]:6d}   {100.0*tot[k]/n:5.1f}%  of {n}")
    print()
    print("per module: elements / driver / load / control / silent")
    for s in GT15:
        c = per[s]
        print(f"  {s:26s} {c['elements']:5d} {c['has_driver']:5d} {c['has_load']:5d} "
              f"{c['has_control']:5d} {c['silent']:5d}")
