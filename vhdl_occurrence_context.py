"""
vhdl_occurrence_context.py — deterministic enclosing-structure extractor for VHDL.

Given a VHDL file and an identifier (port / signal / register / generic), find every
occurrence and report, for each one:
  * role     : what the occurrence is syntactically (LHS_SEQ, LHS_COMB, COND, CASE_SEL,
               SENS, PORT_MAP, RHS, ...)
  * context  : the stack of enclosing constructs, outermost -> innermost
               (architecture, process, if/elsif/else branch, case alternative,
                generate, loop, instantiation, when/else, function/procedure)
  * path     : the guarding predicates for this site, with elsif/else branches carrying
               the negation of every earlier branch condition

Parser: tree-sitter VHDL grammar (via tree-sitter-language-pack). No LLM involved.
Limitation: tree-sitter is syntactic only — no name resolution. A local variable or
subprogram parameter that shadows a signal name is reported as a hit; see `shadowed`.

Usage:  python vhdl_occurrence_context.py <file.vhd> <identifier> [--json]
"""
from __future__ import annotations
import json
import sys
from dataclasses import dataclass, field, asdict

from tree_sitter_language_pack import get_parser

_PARSER = get_parser("vhdl")


def _txt(n) -> str:
    """Node text with comments removed and whitespace collapsed. Comments are dropped
    on purpose: they are not semantics, and anything they carry (including injected
    instructions) must not leak into conditions/statements handed to a downstream LLM."""
    if n.child_count == 0:
        return "" if n.type == "comment" else n.text.decode(errors="replace")
    src = n.text
    base = n.start_byte
    out, pos = [], 0
    stack = [n]
    comments = []
    while stack:
        m = stack.pop()
        if m.type == "comment":
            comments.append((m.start_byte - base, m.end_byte - base))
            continue
        stack.extend(m.children)
    for a, b in sorted(comments):
        out.append(src[pos:a]); pos = b
    out.append(src[pos:])
    return " ".join(b"".join(out).decode(errors="replace").split())


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


@dataclass
class Frame:
    kind: str                 # PROCESS, IF, ELSIF, ELSE, CASE_WHEN, IF_GENERATE, FOR_GENERATE, ...
    label: str | None = None
    detail: str | None = None  # condition / choice / selector / loop range
    line: int = 0


@dataclass
class Occurrence:
    line: int
    col: int
    text: str                 # the matched name as written (e.g. ctrl.rf_wb_en)
    role: str
    statement: str            # the innermost enclosing statement, one line
    context: list[Frame] = field(default_factory=list)
    path: list[str] = field(default_factory=list)
    shadowed: bool = False


# ---------------------------------------------------------------- role
def _role(name_node) -> str:
    """Classify the syntactic site by walking up to the first deciding ancestor."""
    child, n = name_node, name_node.parent
    while n is not None:
        t = n.type
        # assignment targets: the matched name sits under the 'target' field
        if t in ("simple_waveform_assignment", "simple_variable_assignment",
                 "conditional_signal_assignment", "selected_signal_assignment"):
            tgt = n.child_by_field_name("target")
            if tgt is not None and _contains(tgt, name_node):
                return "LHS_VAR" if t == "simple_variable_assignment" else "LHS_SEQ"
            return "RHS"
        if t in ("simple_concurrent_signal_assignment",
                 "conditional_concurrent_signal_assignment",
                 "selected_concurrent_signal_assignment"):
            tgt = n.child_by_field_name("target")
            if tgt is not None and _contains(tgt, name_node):
                return "LHS_COMB"
            if t == "selected_concurrent_signal_assignment" and child.type == "expression":
                return "SEL_SEL"
            return "COND" if _under(name_node, n, "conditional_expression") else "RHS"
        if t == "sensitivity_list":
            return "SENS"
        if t == "named_association_element":
            # formal => actual ; the matched name is on the actual side for local signals
            kids = [c for c in n.children if c.is_named]
            if kids and _contains(kids[0], name_node):
                return "PORT_MAP_FORMAL"
            return "PORT_MAP_ACTUAL"
        if t == "positional_association_element" and _up_to(n, ("port_map_aspect", "generic_map_aspect")):
            return "PORT_MAP_ACTUAL"
        if t == "case_statement" and child.type == "expression":
            return "CASE_SEL"
        if t == "conditional_expression" and n.parent is not None and n.parent.type in (
                "if", "elsif", "if_generate", "elsif_generate", "while_loop"):
            return "COND"
        if t in ("if", "elsif", "else", "sequence_of_statements", "process_statement",
                 "architecture_body", "design_unit"):
            break
        child, n = n, n.parent
    return "OTHER"


def _contains(outer, inner) -> bool:
    return outer.start_byte <= inner.start_byte and inner.end_byte <= outer.end_byte


def _under(node, stop, typ) -> bool:
    n = node.parent
    while n is not None and n != stop:
        if n.type == typ:
            return True
        n = n.parent
    return False


def _up_to(node, types) -> bool:
    n = node.parent
    while n is not None:
        if n.type in types:
            return True
        n = n.parent
    return False


# ---------------------------------------------------------------- context
def _context(name_node) -> tuple[list[Frame], list[str]]:
    frames: list[Frame] = []
    path: list[str] = []
    child, n = name_node, name_node.parent
    while n is not None:
        t = n.type
        ln = n.start_point[0] + 1
        if t == "if_statement":
            # which branch holds `child`?  if / elsif k / else
            branches = [c for c in n.children if c.type in ("if", "elsif", "else")]
            earlier = []
            for b in branches:
                if b.id == child.id:
                    c = _cond_of(b)
                    in_cond = c is not None and any(
                        x.type == "conditional_expression" and _contains(x, name_node) for x in b.children)
                    frames.append(Frame(b.type.upper(), _label(n), c, b.start_point[0] + 1))
                    if not in_cond:   # the site is inside the branch body, so it's guarded
                        guard = [f"not ({e})" for e in earlier] + ([c] if c else [])
                        path[:0] = guard
                    else:             # the site IS the condition; only earlier branches guard it
                        path[:0] = [f"not ({e})" for e in earlier]
                    break
                c = _cond_of(b)
                if c:
                    earlier.append(c)
        elif t == "case_statement_alternative":
            case = n.parent
            sel = next((_txt(c) for c in case.children if c.type == "expression"), "?")
            ch = next((_txt(c) for c in n.children if c.type == "choices"), "?")
            frames.append(Frame("CASE_WHEN", _label(case), f"{sel} = {ch}", ln))
            path.insert(0, f"{sel} = {ch}")
        elif t == "process_statement":
            sens = next((_txt(c) for c in n.children if c.type == "sensitivity_list"), None)
            frames.append(Frame("PROCESS", _label(n), f"sensitivity: {sens}" if sens else "wait-based", ln))
        elif t in ("if_generate", "elsif_generate", "else_generate"):
            gen = n.parent
            c = _cond_of(n)
            frames.append(Frame(t.upper(), _label(gen), c, ln))
            if c:
                path.insert(0, f"[generic] {c}")
        elif t == "for_generate_statement":
            ps = next((_txt(c) for c in n.children if c.type == "parameter_specification"), None)
            frames.append(Frame("FOR_GENERATE", _label(n), ps, ln))
        elif t == "loop_statement":
            scheme = next((_txt(c) for c in n.children if c.type in ("for_loop", "while_loop")), None)
            frames.append(Frame("LOOP", _label(n), scheme, ln))
        elif t in ("component_instantiation_statement",):
            unit = next((_txt(c) for c in n.children
                         if c.type in ("component_instantiation", "entity_instantiation")), None)
            frames.append(Frame("INSTANCE", _label(n), unit, ln))
        elif t == "conditional_concurrent_signal_assignment":
            frames.append(Frame("WHEN_ELSE", _label(n), None, ln))
        elif t == "selected_concurrent_signal_assignment":
            frames.append(Frame("WITH_SELECT", _label(n), None, ln))
        elif t in ("function_body", "procedure_body"):
            nm = n.child_by_field_name("designator")
            frames.append(Frame(t.split("_")[0].upper(), _txt(nm) if nm else None, None, ln))
        elif t == "architecture_body":
            nm = n.child_by_field_name("name")
            ent = n.child_by_field_name("entity")
            frames.append(Frame("ARCHITECTURE", _txt(nm) if nm else None,
                                f"of {_txt(ent)}" if ent else None, ln))
        elif t == "package_body":
            frames.append(Frame("PACKAGE_BODY", None, None, ln))
        child, n = n, n.parent
    frames.reverse()
    return frames, path


# ---------------------------------------------------------------- statement
_STMT = {"simple_waveform_assignment", "simple_variable_assignment",
         "simple_concurrent_signal_assignment", "conditional_concurrent_signal_assignment",
         "selected_concurrent_signal_assignment", "procedure_call_statement",
         "component_instantiation_statement", "sensitivity_list", "if", "elsif",
         "case_statement", "signal_declaration", "variable_declaration", "constant_declaration"}


def _statement(node) -> str:
    n = node.parent
    while n is not None and n.type not in _STMT:
        n = n.parent
    if n is None:
        return ""
    if n.type in ("if", "elsif"):
        return f"{n.type} {_cond_of(n)} then"
    if n.type == "case_statement":
        sel = next((_txt(c) for c in n.children if c.type == "expression"), "?")
        return f"case {sel} is"
    if n.type == "component_instantiation_statement":
        # just the association that holds the hit
        m = node.parent
        while m is not None and m.type not in ("named_association_element", "positional_association_element"):
            m = m.parent
        return _txt(m) if m is not None else _txt(n)[:120]
    s = _txt(n)
    return s if len(s) <= 160 else s[:157] + "..."


# ---------------------------------------------------------------- matching
def _local_decls(tree_root) -> list[tuple[int, int, set[str]]]:
    """(start_byte, end_byte, names) for every process / subprogram declarative region,
    so a same-named variable/parameter can be flagged as shadowing."""
    regions = []

    def walk(n):
        if n.type in ("process_statement", "function_body", "procedure_body"):
            names = set()
            for d in _iter(n):
                if d.type in ("variable_declaration", "constant_declaration",
                              "interface_variable_declaration", "interface_signal_declaration",
                              "interface_constant_declaration", "parameter_specification"):
                    for idl in d.children:
                        if idl.type == "identifier_list":
                            names |= {_txt(i).lower() for i in idl.children if i.type == "identifier"}
                        elif idl.type == "identifier":
                            names.add(_txt(idl).lower())
            regions.append((n.start_byte, n.end_byte, names))
        for c in n.children:
            walk(c)

    walk(tree_root)
    return regions


def _iter(n):
    yield n
    for c in n.children:
        yield from _iter(c)


def find(src: bytes, ident: str) -> list[Occurrence]:
    """ident may be a plain name (`clk_i`) or a dotted record path (`ctrl.rf_wb_en`).
    Plain names match the name itself AND the prefix of record selections (`ctrl` in
    `ctrl.rf_wb_en`); a dotted query matches that selection and its sub-selections."""
    tree = _PARSER.parse(src)
    q = ident.lower()
    dotted = "." in q
    regions = _local_decls(tree.root_node)
    out: list[Occurrence] = []
    seen = set()

    for n in _iter(tree.root_node):
        hit = None
        if dotted and n.type == "selected_name":
            t = _txt(n).lower().replace(" ", "")
            if t == q or t.startswith(q + ".") or t.startswith(q + "("):
                # report the outermost selected_name only
                if not (n.parent and n.parent.type == "selected_name"):
                    hit = n
        elif not dotted and n.type in ("simple_name", "identifier"):
            if _txt(n).lower() == q:
                p = n.parent
                # skip labels, and record-field suffixes (`bus.addr` is not signal `addr`)
                if p is not None and p.type == "label":
                    continue
                if p is not None and p.type == "selected_name" and p.children[0].id != n.id:
                    continue
                hit = n
                # lift to the full selected name if this is the record prefix
                while hit.parent is not None and hit.parent.type == "selected_name" \
                        and hit.parent.children[0].id == hit.id:
                    hit = hit.parent
        if hit is None or hit.id in seen:
            continue
        seen.add(hit.id)
        if _up_to(hit, ("signal_declaration", "port_clause", "entity_declaration")) \
                and not _up_to(hit, ("architecture_body",)):
            role = "DECL"
        elif _up_to(hit, ("signal_declaration", "variable_declaration", "constant_declaration")) \
                and n.type == "identifier":
            role = "DECL"
        else:
            role = _role(hit)
        frames, path = _context(hit)
        sh = any(a <= hit.start_byte < b and q.split(".")[0] in names for a, b, names in regions) \
            and role != "DECL"
        out.append(Occurrence(hit.start_point[0] + 1, hit.start_point[1] + 1, _txt(hit),
                              role, _statement(hit), frames, path, sh))
    return out


def render(occs: list[Occurrence]) -> str:
    lines = []
    for o in occs:
        lines.append(f"L{o.line}:{o.col}  {o.role:<16} {o.text}" + ("   [!] possibly shadowed" if o.shadowed else ""))
        lines.append(f"    stmt : {o.statement}")
        for f in o.context:
            lab = f"{f.label}: " if f.label else ""
            det = f"  {f.detail}" if f.detail else ""
            lines.append(f"    ctx  : {f.kind:<13} {lab}(L{f.line}){det}")
        if o.path:
            lines.append("    path : " + "  AND  ".join(o.path))
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    occs = find(open(sys.argv[1], "rb").read(), sys.argv[2])
    if "--json" in sys.argv:
        print(json.dumps([asdict(o) for o in occs], indent=2))
    else:
        print(render(occs))
