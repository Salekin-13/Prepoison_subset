"""rtl_parse.py -- deterministic VHDL element extraction (ground truth for Task 3).
LLM annotates meaning; the RTL text is authoritative for what exists.
Elements are linked to their owning entity; record-typed signals/ports are
expanded to their fields (name.field), using record defs from this file AND
an external registry (e.g. neorv32_package's bus_req_t / bus_rsp_t)."""
import re
from pathlib import Path
from stage_a import _mask_comments   # reuse the offset-preserving masker

_ENTITY    = re.compile(r"\bentity\s+(\w+)\s+is\b(.*?)\bend\b", re.IGNORECASE | re.DOTALL)
# Type group runs to the ';' (NOT [^:;]) so that a default value survives the match;
# _split_type() then strips it. With [^:;] a declaration like
#   signal x : std_ulogic := '0';
# matched nothing and the element vanished from the closed set.
_SIGNAL    = re.compile(r"^[ \t]*signal\s+([\w\s,]+?)\s*:\s*([^;]+?)\s*;", re.IGNORECASE | re.MULTILINE)
_PORT_DECL = re.compile(r"(\w[\w\s,]*?)\s*:\s*(in|out|inout|buffer)\s+([^;]+?)\s*(?:;|$)", re.IGNORECASE)
# start of any design unit -- used to bound one architecture's region
_UNIT_START = re.compile(r"\b(?:architecture\s+\w+\s+of\s+\w+\s+is|entity\s+\w+\s+is|"
                         r"package(?:\s+body)?\s+\w+\s+is)\b", re.IGNORECASE)
_RECORD    = re.compile(r"\btype\s+(\w+)\s+is\s+record\b(.*?)\bend\s+record\b", re.IGNORECASE | re.DOTALL)
_FIELD     = re.compile(r"([\w\s,]+?)\s*:\s*([^;]+?)\s*;", re.IGNORECASE)

def _split_names(blob):
    return [n.strip() for n in blob.split(",") if n.strip()]

def _split_type(t):
    """'std_ulogic := '0'' -> 'std_ulogic'. Drops a default/initial value so the type
    string handed to the LLM (and _base_type) is the type alone."""
    return t.split(":=")[0].strip()

def _base_type(t):                       # 'std_ulogic_vector(31 downto 0)'->'std_ulogic_vector'
    return _split_type(t).split("(")[0].strip().lower()

def _arch_re(ename):                     # exact entity match ('neorv32_cache' != 'neorv32_cache_memory')
    return re.compile(r"architecture\s+\w+\s+of\s+" + re.escape(ename) + r"\s+is\b",
                      re.IGNORECASE)

def arch_region(masked, ename):
    """Text of one architecture, from its 'is' to the start of the next design unit.

    Deliberately NOT cut at the first 'begin': an architecture whose declarative part
    contains a function or procedure body hits that inner 'begin' first, which hid every
    signal declared after it (neorv32_cpu_cp_crypto lost all 16 of its signals this way).
    Scanning the whole region is safe because VHDL only permits 'signal' declarations in
    a declarative part -- a process body uses 'variable' -- so no statement-region text
    can match _SIGNAL. Signals declared inside a block statement are picked up too, which
    is correct: they are internal design elements of this entity.
    """
    m = _arch_re(ename).search(masked)
    if not m:
        return None
    nxt = _UNIT_START.search(masked, m.end())
    return masked[m.end(): nxt.start() if nxt else len(masked)]

def _balanced_block(text, kw):
    m = re.search(kw + r"\s*\(", text, re.IGNORECASE)
    if not m: return None
    i = m.end() - 1; depth, start = 0, i + 1
    for j in range(i, len(text)):
        if text[j] == '(': depth += 1
        elif text[j] == ')':
            depth -= 1
            if depth == 0: return text[start:j]
    return None

def collect_records(masked):
    """{record_type_lower: [(field, field_type), ...]} from 'type X is record ... end record'."""
    recs = {}
    for name, body in _RECORD.findall(masked):
        fields = []
        for fnames, ftype in _FIELD.findall(body):
            for fn in _split_names(fnames):
                fields.append((fn, ftype.strip()))
        recs[name.lower()] = fields
    return recs

def build_record_registry(paths):
    """Merge record defs across files (call with the package + all RTL) so record-typed
    ports like host_req_i:bus_req_t expand even though bus_req_t is declared elsewhere."""
    reg = {}
    for p in paths:
        reg.update(collect_records(_mask_comments(
            Path(p).read_text(encoding="utf-8", errors="ignore"), vhdl=True)))
    return reg

def _expand(name, typ, records):
    """Base entry + one dotted entry per record field (single level)."""
    typ = _split_type(typ)
    out = [(name, typ)]
    for fn, ft in records.get(_base_type(typ), []):
        out.append((f"{name}.{fn}", _split_type(ft)))
    return out

def parse_ports(ent_block, records):
    body = _balanced_block(ent_block, "port")
    if body is None: return []
    ports = []
    for names, direction, ptype in _PORT_DECL.findall(body):
        for nm in _split_names(names):
            if nm.lower() == "port": continue
            for enm, etyp in _expand(nm, ptype, records):
                ports.append({"name": enm, "dir": direction.lower(), "type": etyp})
    return ports

def parse_signals(masked_arch, records):
    sigs = []
    for names, stype in _SIGNAL.findall(masked_arch):
        for nm in _split_names(names):
            for enm, etyp in _expand(nm, stype, records):
                sigs.append({"name": enm, "type": etyp})
    return sigs

def parse_rtl_file(path, records=None):
    raw    = Path(path).read_text(encoding="utf-8", errors="ignore")
    masked = _mask_comments(raw, vhdl=True)
    reg = dict(records or {}); reg.update(collect_records(masked))   # external + this file's records
    entities = []
    for em in _ENTITY.finditer(masked):                              # multiple entities per file
        ename = em.group(1)
        ports = parse_ports(em.group(0), reg)
        region = arch_region(masked, ename)
        signals = parse_signals(region, reg) if region is not None else []
        entities.append({"entity": ename, "ports": ports, "signals": signals})
    return {"file": Path(path).stem, "entities": entities}