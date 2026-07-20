"""rtl_parse.py -- deterministic VHDL element extraction (ground truth for Task 3).
LLM annotates meaning; the RTL text is authoritative for what exists."""
import re
from pathlib import Path
from stage_a import _mask_comments   # reuse the offset-preserving masker

_PORT_BLOCK = re.compile(r"\bport\s*\((.*?)\)\s*;", re.IGNORECASE | re.DOTALL)
_ENTITY     = re.compile(r"\bentity\s+(\w+)\s+is\b(.*?)\bend\b", re.IGNORECASE | re.DOTALL)
_SIGNAL     = re.compile(r"^\s*signal\s+([\w\s,]+?)\s*:\s*([^:;]+?)\s*;", re.IGNORECASE | re.MULTILINE)
_PORT_DECL  = re.compile(
    r"(\w[\w\s,]*?)\s*:\s*(in|out|inout|buffer)\s+([^;]+?)\s*(?:;|$)", re.IGNORECASE)

def _split_names(blob):                       # "a, b , c" -> ["a","b","c"]
    return [n.strip() for n in blob.split(",") if n.strip()]

def _balanced_block(text, kw):
    """Return the content inside the parens following keyword `kw` (e.g. 'port'),
    matching nested parentheses correctly. None if not found."""
    m = re.search(kw + r"\s*\(", text, re.IGNORECASE)
    if not m: return None
    i = m.end() - 1                      # position of the opening '('
    depth, start = 0, i + 1
    for j in range(i, len(text)):
        if text[j] == '(': depth += 1
        elif text[j] == ')':
            depth -= 1
            if depth == 0:
                return text[start:j]     # content between the outer parens
    return None                          # unbalanced (shouldn't happen in valid VHDL)

def parse_ports(ent_block):
    body = _balanced_block(ent_block, "port")
    if body is None: return []
    ports = []
    for names, direction, ptype in _PORT_DECL.findall(body):
        for nm in _split_names(names):
            if nm.lower() == "port": continue
            ports.append({"name": nm, "dir": direction.lower(), "type": ptype.strip()})
    return ports

def parse_signals(masked_arch):
    sigs = []
    for names, stype in _SIGNAL.findall(masked_arch):
        for nm in _split_names(names):
            sigs.append({"name": nm, "type": stype.strip()})
    return sigs

def parse_rtl_file(path):
    raw    = Path(path).read_text(encoding="utf-8", errors="ignore")
    masked = _mask_comments(raw, vhdl=True)
    entities = []
    # each entity: header (entity..end) gives ports; matching architecture gives signals
    for em in _ENTITY.finditer(masked):
        ename = em.group(1)
        ports = parse_ports(em.group(0))
        # architecture body for THIS entity: 'architecture X of <ename> is ... begin'
        arch_re = re.compile(
            r"architecture\s+\w+\s+of\s+" + re.escape(ename) +
            r"\s+is\b(.*?)\bbegin\b", re.IGNORECASE | re.DOTALL)
        am = arch_re.search(masked)
        signals = parse_signals(am.group(1)) if am else []
        entities.append({"entity": ename, "ports": ports, "signals": signals})
    return {"file": Path(path).stem, "entities": entities}