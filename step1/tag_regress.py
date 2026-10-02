"""Code checks for SITE-tag patterns that the rulebook forbids, used to catch regressions between profiler versions
(Step 1, 15 test modules). A regression is a flagged entry whose tags differ from the previous version's.

  R1  RHS_OPERAND / VAR_RHS_OPERAND with ATTR_PREFIX, where no operator sits in the innermost parentheses around the
      occurrence            e.g. keeper.halt <= port_sel(port_sel'left);      the attribute is a position, not an operand
  R2  RHS_OPERAND / VAR_RHS_OPERAND with INDEX, same test
                            e.g. csr_o <= cfg_rd32(to_integer(unsigned(ctrl_i.csr_addr(1 downto 0))));
  R3  INDEX on the prefix of an indexed target (the element written before its parentheses, left of <=)
                            e.g. tx_engine.state(2) <= ctrl.enable;           the prefix is INDEXED_NAME
  R4  LHS_PROC / LHS_CONC on an occurrence right of the assignment symbol, or missing on the target left of it
                            e.g. engine.bitcnt <= std_ulogic_vector(unsigned(engine.bitcnt) + 1);  tags swapped
  R5  RHS_OPERAND / VAR_RHS_OPERAND on an occurrence outside all parentheses, on a right-hand side with no operator
                            e.g. keeper.halt <= port_sel(port_sel'left);      the prefix: INDEXED_NAME alone

Occurrence IDs number an element's occurrences left to right (occurrence_matches), so an ID gives a column.
"""
from __future__ import annotations

import re
from collections import defaultdict

OPERATOR = re.compile(r"[-+*/&<>=]|\b(?:and|or|nand|nor|xor|xnor|not|mod|rem|sll|srl|sla|sra|rol|ror)\b", re.I)
RHS_OP = {"RHS_OPERAND", "VAR_RHS_OPERAND"}
LHS = {"LHS_PROC", "LHS_CONC"}


def _innermost(text: str, col: int) -> str | None:
    """The contents of the innermost parentheses that enclose column col, or None when there are none."""
    opens = []
    for i, ch in enumerate(text[:col]):
        if ch == "(":
            opens.append(i)
        elif ch == ")" and opens:
            opens.pop()
    if not opens:
        return None
    start = opens[-1] + 1
    d, j = 0, start
    while j < len(text):
        if text[j] == "(":
            d += 1
        elif text[j] == ")":
            if d == 0:
                break
            d -= 1
        j += 1
    return text[start:j]


def _stmt_start(text: str) -> int:
    """Column where the statement starts: after "when <choice> =>" in a case alternative, else the first non-blank."""
    m0 = re.match(r"\s*when\b.*?=>\s*", text, re.I)
    return m0.end() if m0 else len(text) - len(text.lstrip())


def _assign_col(text: str) -> int | None:
    """Column of the assignment symbol; None for a condition line (a "<=" there compares)."""
    if not re.match(r"\s*when\b", text, re.I) and re.match(r"\s*(?:if|elsif|while|case|return)\b", text, re.I):
        return None
    start = _stmt_start(text)
    m = re.search(r"<=|:=", text[start:])
    return start + m.start() if m else None


def _without(name: str, text: str) -> str:
    return re.sub(rf"(?<![\w.]){re.escape(name)}(?![\w])", " ", text)


def _enclosing_prefixes(text: str, col: int) -> list[str]:
    """The names written just before each parenthesis that encloses column col, innermost first."""
    opens = []
    for i, ch in enumerate(text[:col]):
        if ch == "(":
            opens.append(i)
        elif ch == ")" and opens:
            opens.pop()
    out = []
    for i in reversed(opens):
        m = re.search(r"([A-Za-z_][\w.]*)\s*$", text[:i])
        out.append(m.group(1) if m else "")
    return out


def flags(profile_rows: dict, columns: dict, positions: dict | None = None) -> dict:
    """profile_rows: {key: row}; columns: {key: column of the occurrence in Line Text}; positions: {key: set of names
    whose parentheses hold a position or range (the entity's elements and named constants)}. Returns {check: [keys]}.
      R6  RHS_OPERAND / VAR_RHS_OPERAND on an attribute occurrence inside an element's or constant's parentheses
      R7  an occurrence inside an element's or constant's parentheses (a call nested there included) without INDEX,
          ATTR_PREFIX or FIELD_USE
      R8  INDEX on the prefix of an indexed name or slice (the element written just before "("), without
          INDEXED_NAME or PART_SELECT"""
    out = defaultdict(list)
    for k, r in profile_rows.items():
        s, t, col = set(r["SITE Tagged"]), r["Line Text"], columns.get(k)
        if col is None or col < 0:
            continue
        name = k[2]
        inner = _innermost(t, col)
        no_op = inner is not None and not OPERATOR.search(_without(name, inner))
        if s & RHS_OP and "ATTR_PREFIX" in s and no_op:
            out["R1"].append(k)
        if s & RHS_OP and "INDEX" in s and no_op:
            out["R2"].append(k)
        if positions is not None and k in positions:
            inside = any(p in positions[k] for p in _enclosing_prefixes(t, col))
            attr = t[col + len(name):].lstrip().startswith("'")
            if attr and inside and s - {"ATTR_PREFIX"}:
                out["R6"].append(k)            # revised rule: an attribute inside a position is ATTR_PREFIX alone
            if inside and not s & {"INDEX", "ATTR_PREFIX", "FIELD_USE"}:
                out["R7"].append(k)
            if t[col + len(name):].lstrip().startswith("(") and "INDEX" in s and not s & {"INDEXED_NAME", "PART_SELECT"} \
                    and not inside:
                out["R8"].append(k)
        a = _assign_col(t)
        if a is None or len(re.findall(r"<=|:=", t[_stmt_start(t):])) > 1:
            continue                  # no assignment, or several statements on the line: position checks not decidable
        target = col == _stmt_start(t) and col < a
        if "INDEX" in s and target and t[col + len(name):a].lstrip().startswith("(") \
                and not s & {"INDEXED_NAME", "PART_SELECT"}:
            out["R3"].append(k)
        if s & LHS and col > a:
            out["R4"].append(k)
        if target and not s & LHS and not s & {"FIELD_USE"} and re.match(rf"{re.escape(name)}\s*(?:\(|<=|:=)", t[col:]):
            out["R4"].append(k)
        rhs = t[a + 2:].split(";")[0]
        if s & RHS_OP and col > a and inner is None and not OPERATOR.search(_without(name, rhs)):
            out["R5"].append(k)
        # R9  DIRR_ASS where the right-hand side is not exactly the element
        if "DIRR_ASS" in s and col > a and " when " not in f" {rhs} " and rhs.strip().lower() != name.lower():
            out["R9"].append(k)
    return out


POSITIONS: dict = {}


def load_rows(S, RS, modules, vsha: str, profiler_g, root=None) -> tuple[dict, dict]:
    """Rows of one validate version and the column of every occurrence (from the code inventory). Also fills
    POSITIONS: for every key, the names whose parentheses hold a position (the entity's elements and constants)."""
    W = dict(S.WHERE, profile=(root or S.PROFILES, vsha))
    rows, cols = {}, {}
    g = profiler_g
    for m in modules:
        for e in RS.load_module(m, W):
            L = g["source_lines"](e["src"])
            names = {x["name"] for x in e["ports"] + e["signals"]} | set(re.findall(r"\bconstant\s+(\w+)", e["src"], re.I))
            for n in e["profile"]:
                for r in e["profile"][n]:
                    POSITIONS[(m, e["entity"], n, r["Occurrence ID"])] = names
            for n, rs in e["profile"].items():
                matches = g["occurrence_matches"](L, n)
                for r in rs:
                    k = (m, e["entity"], n, r["Occurrence ID"])
                    rows[k] = r
                    i = r["Occurrence ID"] - 1
                    if 0 <= i < len(matches) and matches[i][0] == r["Occurrence Lines"]:
                        line, col, _w = matches[i]
                        cols[k] = None if col < 0 else col - (len(L[line]) - len(L[line].lstrip()))
    return rows, cols
