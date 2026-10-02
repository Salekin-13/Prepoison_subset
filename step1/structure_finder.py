# -*- coding: utf-8 -*-
"""Enclosing-structure finder for VHDL sources given as {line number: text} with comments already
blanked and blank lines left out (exactly what the annotator is shown).

structures(L) -> list of {"kind", "lines": [first, last], "opened by"}; spans use shown lines only.
chain(S, line) -> the structures that contain the line, outermost first.

Kinds: port clause, declarative part, architecture body, generate, process, loop, if, branch, case,
alternative, association list.  Branch "opened by": EDGE_CHECK | IF_COND | else.  Alternative
"opened by": the choice text.  Anything the finder cannot place raises StructureError, so a
construct it does not know stops the run instead of producing a wrong span."""
import re

KINDS = ("port clause", "declarative part", "architecture body", "generate", "process", "loop", "if",
         "branch", "case", "alternative", "association list")


class StructureError(Exception):
    pass


def _blank_strings(t):
    return re.sub(r'"[^"\n]*"', lambda m: '"' + " " * (len(m.group(0)) - 2) + '"', t)


def structures(L):
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
        _body(T, [n for n in nums if b < n < e], prev, add)
    return out


def _body(T, lines, prev, add):
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


def chain(S, line):
    inside = [s for s in S if s["lines"][0] <= line <= s["lines"][1]]
    return sorted(inside, key=lambda s: (s["lines"][0], -s["lines"][1], KINDS.index(s["kind"]) if s["kind"] in ("if", "branch", "case", "alternative") else 0))


def render(ch):
    return "; ".join(f"{s['kind']} {s['lines'][0]}-{s['lines'][1]}" + (f" ({s['opened by']})" if s["opened by"] else "")
                     for s in ch)
