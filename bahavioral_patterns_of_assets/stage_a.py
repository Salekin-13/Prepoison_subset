"""
stage_a_module_extraction.py -- Stage A (SoC baseline), DETERMINISTIC ONLY
=========================================================================
UNIT OF WORK = one RTL file = one IP module.

  extract_ip_modules(repo) -> one Module per file (name = filename stem),
                              with the design units inside and a header.
  render_modules(mods, enrich) -> the exact list string handed to the LLM.
  save_lists(mods) / load_modules(path) -> disk round-trip for the notebook.

No LLM here. The keep/drop call lives in the notebook (see prompts.py + cells).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
import json
import re
import sys

VERILOG_EXTS = {".v", ".vh", ".sv", ".svh"}
VHDL_EXTS    = {".vhd", ".vhdl"}
HEADER_CAP   = 240

_V_LINE_COMMENT    = re.compile(r"//[^\n]*")
_V_BLOCK_COMMENT   = re.compile(r"/\*.*?\*/", re.DOTALL)
_VHDL_LINE_COMMENT = re.compile(r"--[^\n]*")

_ENTITY_RE  = re.compile(r"\bentity\s+(\w+)\s+is\b", re.IGNORECASE)
_PACKAGE_RE = re.compile(r"\bpackage\s+(\w+)\s+is\b", re.IGNORECASE)
_MODULE_RE  = re.compile(r"\bmodule\s+(\w+)", re.IGNORECASE)

_BOILERPLATE = ("copyright", "license", "warrant", "damage", "$id", "$revision",
                "$locker", "$state", "cvs log", "www.", "http", "change history",
                "website", "github", "software", "contract", "distribut",
                "derivative", "redistribut", "provided that", "all rights reserved",
                "synopsys", "translate_off", "translate_on", "pragma",
                "verilator", "synthesis")
_META_LABEL_RE = re.compile(
    r"^\s*(file|author|date|created|modified|revision|version|company|engineer|"
    r"project|source|built|design\s*name|module\s*name)\s*:", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+")
_DESC_RE  = re.compile(r"\b(description|brief|purpose|function|summary)\s*:\s*(.+)", re.IGNORECASE)
_NEXT_LABEL_RE = re.compile(r"^\s*[A-Za-z][\w ]{1,20}:\s")


@dataclass
class Module:
    name: str
    file: str
    lang: str
    units: list = field(default_factory=list)
    header: str = ""
    # --- filled by the LLM classification (notebook side) ---
    family: str = ""                # SA-EDI IP family (V2 prompt)
    keep: Optional[bool] = None
    cia: list = field(default_factory=list)
    confidence: float = 0.0
    rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _mask_comments(text: str, vhdl: bool) -> str:
    def blank(m):
        return "".join("\n" if c == "\n" else " " for c in m.group(0))
    if vhdl:
        return _VHDL_LINE_COMMENT.sub(blank, text)
    return _V_LINE_COMMENT.sub(blank, _V_BLOCK_COMMENT.sub(blank, text))


def _lang_for(ext: str) -> str:
    if ext in {".sv", ".svh"}:
        return "systemverilog"
    if ext in VHDL_EXTS:
        return "vhdl"
    return "verilog"


def _v_comment_body(line: str):
    s = line.strip()
    if s.startswith("//"): return s[2:].strip()
    if s.startswith("/*"): return s[2:].replace("*/", "").strip()
    if s.startswith("*"):  return s[1:].replace("*/", "").strip()
    return None


def _vhdl_comment_body(line: str):
    s = line.strip()
    if not s.startswith("--"): return None
    s = s[2:]
    if s.rstrip().endswith("--"): s = s.rstrip()[:-2]
    return s.strip()


def _is_disclaimer(core: str) -> bool:
    letters = [c for c in core if c.isalpha()]
    if len(letters) < 12: return False
    return sum(c.isupper() for c in letters) / len(letters) > 0.8


def _looks_like_code(core: str) -> bool:
    s = core.strip()
    return "::" in s or s.endswith(";")


def _is_noise(core: str) -> bool:
    if not core or set(core) <= set("/*-=_ "): return True
    if _META_LABEL_RE.match(core): return True
    if _is_disclaimer(core) or _EMAIL_RE.search(core) or _looks_like_code(core): return True
    low = core.lower()
    return any(w in low for w in _BOILERPLATE)


def _finalize_header(lines: list, budget: int) -> str:
    for idx, ln in enumerate(lines):
        m = _DESC_RE.search(ln)
        if m:
            parts = [m.group(2).strip()]
            for nxt in lines[idx + 1:]:
                if _NEXT_LABEL_RE.match(nxt): break
                parts.append(nxt.strip())
            return " ".join(p for p in parts if p)[:budget].strip()
    return " ".join(lines)[:budget].strip()


def _contig_header(raw_lines, decl_idx, body_fn, budget, max_lines=14, region_start=0):
    content = []
    for i in range(decl_idx - 1, region_start - 1, -1):
        body = body_fn(raw_lines[i])
        if body is None:
            if content and raw_lines[i].strip() != "": break
            continue
        core = body.strip("/*-= \t")
        if _is_noise(core): continue
        content.append(core)
        if len(content) >= max_lines: break
    content.reverse()
    return _finalize_header(content, budget)


def _vhdl_header(raw_lines, masked_lines, decl_idx, budget=HEADER_CAP):
    link_idx = None
    for i in range(decl_idx - 1, -1, -1):
        low = masked_lines[i].lower()
        if "stnolting/neorv32" in low or "neorv32 risc-v processor" in low:
            link_idx = i; break
    if link_idx is None:
        return _contig_header(raw_lines, decl_idx, _vhdl_comment_body, budget)
    content = []
    for i in range(link_idx - 1, -1, -1):
        body = _vhdl_comment_body(raw_lines[i])
        if body is None: break
        is_rule = body.strip() != "" and set(body.strip()) <= set("=- ")
        if is_rule:
            if "=" in body and content: break
            continue
        core = body.strip("=- \t")
        if core and not _is_noise(core): content.append(core)
    content.reverse()
    if content: return _finalize_header(content, budget)
    below = []
    for i in range(link_idx + 1, min(link_idx + 6, len(raw_lines))):
        body = _vhdl_comment_body(raw_lines[i])
        if body is None: break
        core = body.strip("=- \t")
        if core and not _is_noise(core): below.append(core)
    return _finalize_header(below, budget)


def _verilog_header(raw_lines, masked_lines, decl_idx, budget=HEADER_CAP):
    start = 0
    for i in range(decl_idx - 1, -1, -1):
        if re.search(r"\bendmodule\b", masked_lines[i], re.IGNORECASE):
            start = i + 1; break
    return _contig_header(raw_lines, decl_idx, _v_comment_body, budget, region_start=start)


def extract_ip_modules(repo_root: str) -> list:
    root = Path(repo_root)
    mods = []
    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in VERILOG_EXTS | VHDL_EXTS)
    for path in files:
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        vhdl = path.suffix.lower() in VHDL_EXTS
        masked = _mask_comments(raw, vhdl)
        raw_lines, masked_lines = raw.splitlines(), masked.splitlines()
        if vhdl:
            decls = list(_ENTITY_RE.finditer(masked)) or list(_PACKAGE_RE.finditer(masked))
        else:
            decls = list(_MODULE_RE.finditer(masked))
        units, headers = [], []
        for m in decls:
            units.append(m.group(1))
            decl_idx = masked[:m.start()].count("\n")
            h = (_vhdl_header(raw_lines, masked_lines, decl_idx) if vhdl
                 else _verilog_header(raw_lines, masked_lines, decl_idx))
            if h and h not in headers: headers.append(h)
        mods.append(Module(name=path.stem, file=str(path.relative_to(root)),
                           lang=_lang_for(path.suffix.lower()), units=units,
                           header=" | ".join(headers)[:HEADER_CAP].strip()))
    return mods


def render_modules(mods: list, enrich: bool = False) -> str:
    lines = []
    for i, m in enumerate(mods, 1):
        if enrich and m.header:
            lines.append(f"{i}. {m.name} -- {m.header}")
        else:
            lines.append(f"{i}. {m.name}")
    return "\n".join(lines)


def save_lists(mods: list, out_dir: str = "stage_a_out") -> str:
    """Write the notebook's inputs: structured JSON (source of truth) + the two
    exact prompt-ready list strings."""
    d = Path(out_dir); d.mkdir(parents=True, exist_ok=True)
    (d / "ip_modules.json").write_text(json.dumps([m.to_dict() for m in mods], indent=2))
    (d / "list_names.txt").write_text(render_modules(mods, enrich=False))
    (d / "list_enriched.txt").write_text(render_modules(mods, enrich=True))
    return str(d)


def load_modules(path: str = "stage_a_out/ip_modules.json") -> list:
    """Reload Module objects (notebook side)."""
    data = json.loads(Path(path).read_text())
    return [Module(**d) for d in data]


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    if not Path(root).exists():
        sys.exit(f"path not found: {root}")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "stage_a_out"
    mods = extract_ip_modules(root)
    d = save_lists(mods, out_dir)
    print(f"Extracted {len(mods)} IP modules from {root}")
    print(f"Saved -> {d}/ip_modules.json, list_names.txt, list_enriched.txt")