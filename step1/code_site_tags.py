"""Code SITE tagger: the SITE tags of the occurrence profiler, written by code instead of the LLM classify / validate calls.

A SITE says what one occurrence of an element does on its line (declared, assigned, read in an if condition, ...). The
names and their triggers are the v3d rulebook's
(bahavioral_patterns_of_assets/annotation_pack_elements/occurrence_prompts_v3d/rulebook.json).

Method. Each profile row (element, Occurrence ID) is placed at its exact column with the profiler's own
occurrence_matches, then read off the token-level statement model that step1/code_pairs_v2.py already uses
(_CPWriter.scan: every element reference with its role -- target, if, when, case, with, lhs_index, rhs, variable_rhs --
and its index / slice / attribute flags). Declarations, port-map actuals, sensitivity lists and case choices produce no
reference there; they are read from the row's Context (code, from the tree-sitter structure stage) and the line text.

One choice the rulebook does not make: the selector of a selected signal assignment (`with <sel> select`) is tagged
CASE_EXPR, since it plays the case expression's part. The tuning set has no such statement, so this choice cannot move
any tuning-set number; on held-out RTL it decides whether such a selector counts as "in a condition" for GUARD.

API
    tag_entity(E, cols) -> ({(element, occurrence id): [SITE...]}, stats)
        E    = one entity in relation_stage.load_module's format (src, ports, signals, profile rows)
        cols = {(element, occurrence id): (line, column in the numbered line text, name as written)}
    tagger(E, cols)     -> the dict only (the callable step1/build_heldout_code_map.entities takes)
    COND                the condition SITEs the GUARD lever reads (IF_COND, WHEN_COND, CASE_EXPR)

CLI (any working directory)
    python step1/code_site_tags.py            self-test on hand-read lines (4 modules, 2 of them held-out)
    python step1/code_site_tags.py --check    self-test, then agreement with the LLM profiler's tags on the 15 tuning
                                              modules (tag sets per row; "occurs in a condition" per element)
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import code_pairs_v2 as V          # noqa: E402

COND = frozenset({"IF_COND", "WHEN_COND", "CASE_EXPR"})
LHS = {"LHS_PROC", "LHS_CONC"}


def _addon(ref):
    if not ref.get("indexed"):
        return []
    return ["INDEXED_NAME"] if ref.get("bit_index") else ["PART_SELECT"]


def _is_edge(W, ref):
    p = ref["pos"]
    return p >= 2 and W.v[p - 1] == "(" and W.v[p - 2] in ("rising_edge", "falling_edge")


def _whole_rhs(W, ref):
    st = ref.get("stmt")
    if not st or st["selector"] is not None or st["guards"] or len(st["values"]) != 1:
        return False
    e = st["values"][0]
    lo, hi = W._strip(e["lo"], e["hi"])
    return ref["pos"] == lo and ref["end"] == hi


def tag_entity(E: dict, cols: dict) -> tuple[dict, dict]:
    """-> ({(element, occurrence id): [SITE...]}, stats). See the module docstring."""
    W = V._CPWriter({"src": E["src"], "ports": E["ports"], "signals": E["signals"], "profile": {}})
    W.scan()
    at = {}
    for r in W.references:
        if r["kind"] != "element":
            continue
        t = W.tokens[r["pos"]]
        at.setdefault((t.line, t.column), []).append(r)
    L = {}
    for ln in E["src"].splitlines():
        m = re.match(r"\s*(\d+) \| ?(.*)$", ln)
        if m:
            L[int(m.group(1))] = m.group(2)
    ports = {p["name"] for p in E["ports"]}
    out, stats = {}, {"rows": 0, "by_ref": 0, "by_text": 0, "uncovered": 0}
    for n, rows in E["profile"].items():
        for r in rows:
            k = r["Occurrence ID"]
            stats["rows"] += 1
            ln, col, _w = cols[(n, k)]
            text = L.get(ln, "")
            ctx = r.get("Context") or ""
            inner = ctx.split(" in ")[0]
            tags = None
            # declarations: a field on its base's declaration line, or the name declared in a port clause / declarative part
            if col < 0:
                tags = ["DECL_FIELD"]
            elif inner.startswith("port clause") or (inner.startswith("declarative part") and
                                                      re.match(r"\s*signal\b", text, re.I) and ":" in text[col:]
                                                      and ":" not in text[:col].split("signal", 1)[-1].replace(",", "")):
                tags = ["DECL_FIELD"] if "." in n else ["DECL_PORT" if n in ports else "DECL_SIGNAL"]
            elif "." not in n and re.match(r"\s*\.\s*\w", text[col + len(n):]):
                tags = ["FIELD_USE"]                                    # a record base reaching one of its fields
            if tags is None:
                refs = [x for x in at.get((ln, col + 1), []) if x["name"] == n.lower() or x["path"] == n.lower()]
                if refs:
                    ref = refs[0]
                    role, add = ref["role"], _addon(ref)
                    in_proc = ref.get("stmt") and ref["stmt"]["pid"] is not None
                    if role == "target":
                        tags = (["LHS_PROC"] if in_proc else ["LHS_CONC"]) + add
                    elif role == "lhs_index":
                        tags = ["INDEX"] + add
                    elif role == "if":
                        tags = ["EDGE_CHECK"] if _is_edge(W, ref) else ["IF_COND"] + add + (["INDEX"] if ref["index"] else [])
                    elif role == "when":
                        tags = ["WHEN_COND"] + add + (["INDEX"] if ref["index"] else [])
                    elif role in ("case", "with"):
                        tags = ["CASE_EXPR"] + add + (["INDEX"] if ref["index"] else [])
                    elif role == "variable_rhs":
                        tags = (["INDEX"] if ref["index"] else ["VAR_RHS_OPERAND"]) + add
                    elif role == "rhs":
                        st = ref.get("stmt") or {}
                        if ref["index"]:
                            tags = ["INDEX"] + add
                        elif st.get("guards") or st.get("selector") is not None:
                            tags = ["WHEN_EXPR"] + add
                        elif _whole_rhs(W, ref):
                            tags = ["DIRR_ASS"] if ref["exact"] else (add or ["RHS_OPERAND"])
                        else:
                            tags = ["RHS_OPERAND"] + add
                    if tags is not None:
                        stats["by_ref"] += 1
            if tags is None:
                if "port map" in ctx or "generic map" in ctx:
                    tags = ["ASSOC_ACTUAL"] + (["INDEXED_NAME"] if re.match(r"\s*\(", text[col + len(n):]) else [])
                elif re.search(rf"\bprocess\s*\([^)]*(?<![\w.]){re.escape(n)}(?![\w])", text, re.I):
                    tags = ["PROCESS_TRIG"]
                elif re.match(r"\s*'", text[col + len(n):]):
                    tags = ["ATTR_PREFIX"]
                elif re.search(rf"\bwhen\b[^=]*(?<![\w.]){re.escape(n)}(?![\w])[^=]*=>", text, re.I):
                    tags = ["CASE_COND"]
                if tags is not None:
                    stats["by_text"] += 1
            if tags is None:
                tags = []
                stats["uncovered"] += 1
            out[(n, k)] = tags
    return out, stats


def tagger(E, cols):
    return tag_entity(E, cols)[0]


# ------------------------------------------------------------------------------------------------- self-test ---
# (module, element, original line, k-th occurrence of the element on that line, expected SITE set, start of the line
# text). Read by hand from the RTL files on 2026-10-01; the expected tags follow the v3d rulebook triggers.
HAND = [
    # RTL_data/neorv32_wdt.vhd (tuning)
    ("neorv32_wdt", "clk_i", 20, 0, {"DECL_PORT"}, "clk_i       : in  std_ulogic"),
    ("neorv32_wdt", "bus_req_i.addr", 24, 0, {"DECL_FIELD"}, "bus_req_i   : in  bus_req_t"),
    ("neorv32_wdt", "ctrl.enable", 54, 0, {"DECL_FIELD"}, "signal ctrl : ctrl_t"),
    ("neorv32_wdt", "cnt", 57, 0, {"DECL_SIGNAL"}, "signal cnt "),
    ("neorv32_wdt", "clk_i", 71, 0, {"PROCESS_TRIG"}, "bus_access: process(rstn_sys_i, clk_i)"),
    ("neorv32_wdt", "rstn_sys_i", 73, 0, {"IF_COND"}, "if (rstn_sys_i = '0') then"),
    ("neorv32_wdt", "ctrl.enable", 75, 0, {"LHS_PROC"}, "ctrl.enable  <= '0'"),
    ("neorv32_wdt", "ctrl", 75, 0, {"FIELD_USE"}, "ctrl.enable  <= '0'"),
    ("neorv32_wdt", "clk_i", 81, 0, {"EDGE_CHECK"}, "elsif rising_edge(clk_i) then"),
    ("neorv32_wdt", "bus_rsp_o.ack", 83, 0, {"LHS_PROC"}, "bus_rsp_o.ack  <= bus_req_i.stb"),
    ("neorv32_wdt", "bus_req_i.stb", 83, 0, {"DIRR_ASS"}, "bus_rsp_o.ack  <= bus_req_i.stb"),
    ("neorv32_wdt", "bus_req_i.addr", 92, 0, {"IF_COND", "INDEXED_NAME"}, "if (bus_req_i.addr(2) = '0') then"),
    ("neorv32_wdt", "ctrl.lock", 93, 0, {"IF_COND"}, "if (ctrl.lock = '0') then"),
    ("neorv32_wdt", "bus_req_i.data", 94, 0, {"INDEXED_NAME"}, "ctrl.enable  <= bus_req_i.data(ctrl_enable_c)"),
    ("neorv32_wdt", "ctrl.enable", 95, 0, {"RHS_OPERAND"}, "ctrl.lock    <= bus_req_i.data(ctrl_lock_c) and ctrl.enable"),
    ("neorv32_wdt", "bus_req_i.data", 102, 0, {"IF_COND", "PART_SELECT"}, "if (bus_req_i.data(31 downto 0) = reset_pwd_c)"),
    ("neorv32_wdt", "bus_rsp_o.data", 109, 0, {"LHS_PROC", "INDEXED_NAME"}, "bus_rsp_o.data(ctrl_enable_c)"),
    ("neorv32_wdt", "ctrl.enable", 109, 0, {"DIRR_ASS"}, "bus_rsp_o.data(ctrl_enable_c)"),
    ("neorv32_wdt", "bus_rsp_o.data", 111, 0, {"LHS_PROC", "PART_SELECT"}, "bus_rsp_o.data(ctrl_rcause_hi_c downto"),
    ("neorv32_wdt", "ctrl.enable", 131, 0, {"IF_COND"}, "if (ctrl.enable = '0') or (reset_wdt = '1')"),
    ("neorv32_wdt", "reset_wdt", 131, 0, {"IF_COND"}, "if (ctrl.enable = '0') or (reset_wdt = '1')"),
    ("neorv32_wdt", "cnt", 134, 0, {"LHS_PROC"}, "cnt <= std_ulogic_vector(unsigned(cnt) + 1)"),
    ("neorv32_wdt", "cnt", 134, 1, {"RHS_OPERAND"}, "cnt <= std_ulogic_vector(unsigned(cnt) + 1)"),
    ("neorv32_wdt", "clkgen_en_o", 140, 0, {"LHS_CONC"}, "clkgen_en_o <= ctrl.enable"),
    ("neorv32_wdt", "ctrl.enable", 140, 0, {"DIRR_ASS"}, "clkgen_en_o <= ctrl.enable"),
    ("neorv32_wdt", "prsc_tick", 141, 0, {"LHS_CONC"}, "prsc_tick   <= clkgen_i(clk_div4096_c)"),
    ("neorv32_wdt", "clkgen_i", 141, 0, {"INDEXED_NAME"}, "prsc_tick   <= clkgen_i(clk_div4096_c)"),
    ("neorv32_wdt", "cnt_timeout", 144, 0, {"LHS_CONC"}, "cnt_timeout <= '1' when (cnt_started = '1')"),
    ("neorv32_wdt", "cnt_started", 144, 0, {"WHEN_COND"}, "cnt_timeout <= '1' when (cnt_started = '1')"),
    ("neorv32_wdt", "cnt", 144, 0, {"WHEN_COND"}, "cnt_timeout <= '1' when (cnt_started = '1')"),
    ("neorv32_wdt", "ctrl.timeout", 144, 0, {"WHEN_COND"}, "cnt_timeout <= '1' when (cnt_started = '1')"),
    ("neorv32_wdt", "hw_rst_timeout", 161, 0, {"RHS_OPERAND"}, "rstn_o <= not (hw_rst_timeout or hw_rst_access)"),
    ("neorv32_wdt", "rstn_dbg_i", 171, 0, {"IF_COND"}, "if (rstn_dbg_i = '0') then"),
    # RTL_heldout/neorv32_cpu_cp_crypto.vhd (held-out): conditional and selected signal assignments
    ("neorv32_cpu_cp_crypto", "sm3_res", 441, 0, {"LHS_CONC"}, "sm3_res <= (rs1 xor rol_f(rs1, 9)"),
    ("neorv32_cpu_cp_crypto", "rs1", 441, 0, {"WHEN_EXPR"}, "sm3_res <= (rs1 xor rol_f(rs1, 9)"),
    ("neorv32_cpu_cp_crypto", "funct12", 441, 0, {"WHEN_COND", "INDEXED_NAME"}, "sm3_res <= (rs1 xor rol_f(rs1, 9)"),
    ("neorv32_cpu_cp_crypto", "funct12", 456, 0, {"CASE_EXPR", "PART_SELECT"}, "with funct12(11 downto 10) select rs2_sel <="),
    ("neorv32_cpu_cp_crypto", "rs2_sel", 456, 0, {"LHS_CONC"}, "with funct12(11 downto 10) select rs2_sel <="),
    ("neorv32_cpu_cp_crypto", "rs2", 457, 0, {"WHEN_EXPR", "PART_SELECT"}, "rs2(07 downto 00) when \"00\","),
    ("neorv32_cpu_cp_crypto", "funct12", 468, 0, {"CASE_EXPR", "PART_SELECT"}, "with funct12(11 downto 10) select rol_res <="),
    ("neorv32_cpu_cp_crypto", "rol_in", 469, 0, {"WHEN_EXPR", "PART_SELECT"}, "rol_in(31 downto 0)"),
    ("neorv32_cpu_cp_crypto", "rs1", 475, 0, {"RHS_OPERAND"}, "blk_res <= rs1 xor rol_res"),
    # RTL_heldout/neorv32_cpu_control.vhd (held-out)
    ("neorv32_cpu_control", "csr.operand", 1059, 0, {"LHS_CONC"}, "csr.operand <= rf_rs1_i when (exe_engine.ir"),
    ("neorv32_cpu_control", "rf_rs1_i", 1059, 0, {"WHEN_EXPR"}, "csr.operand <= rf_rs1_i when"),
    ("neorv32_cpu_control", "exe_engine.ir", 1059, 0, {"WHEN_COND", "INDEXED_NAME"}, "csr.operand <= rf_rs1_i when"),
    ("neorv32_cpu_control", "exe_engine.ir", 1059, 1, {"WHEN_EXPR", "PART_SELECT"}, "csr.operand <= rf_rs1_i when"),
    ("neorv32_cpu_control", "exe_engine.ir", 1062, 0, {"CASE_EXPR", "PART_SELECT"}, "with exe_engine.ir(instr_funct3_msb_c-1"),
    ("neorv32_cpu_control", "csr.wdata", 1062, 0, {"LHS_CONC"}, "with exe_engine.ir(instr_funct3_msb_c-1"),
    ("neorv32_cpu_control", "csr.rdata", 1063, 0, {"WHEN_EXPR"}, "csr.rdata or       csr.operand  when \"10\""),
    ("neorv32_cpu_control", "csr.operand", 1063, 0, {"WHEN_EXPR"}, "csr.rdata or       csr.operand  when \"10\""),
    ("neorv32_cpu_control", "rstn_i", 1072, 0, {"IF_COND"}, "if (rstn_i = '0') then"),
    ("neorv32_cpu_control", "csr.we", 1073, 0, {"LHS_PROC"}, "csr.we             <= '0'"),
    # RTL_heldout/neorv32_gpio.vhd (held-out): declarations, a case statement, a variable assignment, a function call
    ("neorv32_gpio", "gpio_i", 27, 0, {"DECL_PORT"}, "gpio_i    : in  std_ulogic_vector(31 downto 0)"),
    ("neorv32_gpio", "port_in", 44, 0, {"DECL_SIGNAL"}, "signal port_in, port_out"),
    ("neorv32_gpio", "port_out", 44, 0, {"DECL_SIGNAL"}, "signal port_in, port_out"),
    ("neorv32_gpio", "rstn_i", 57, 0, {"IF_COND"}, "if (rstn_i = '0') then"),
    ("neorv32_gpio", "clk_i", 64, 0, {"EDGE_CHECK"}, "elsif rising_edge(clk_i) then"),
    ("neorv32_gpio", "bus_req_i.addr", 73, 0, {"CASE_EXPR", "PART_SELECT"}, "case bus_req_i.addr(4 downto 2) is"),
    ("neorv32_gpio", "port_out", 74, 0, {"LHS_PROC"}, "when addr_out_c => port_out <= bus_req_i.data"),
    ("neorv32_gpio", "bus_req_i.data", 74, 0, {"PART_SELECT"}, "when addr_out_c => port_out <= bus_req_i.data"),
    ("neorv32_gpio", "bus_rsp_o.data", 83, 0, {"LHS_PROC", "PART_SELECT"}, "when addr_in_c  => bus_rsp_o.data"),
    ("neorv32_gpio", "port_in", 83, 0, {"DIRR_ASS"}, "when addr_in_c  => bus_rsp_o.data"),
    ("neorv32_gpio", "gpio_i", 103, 0, {"PART_SELECT"}, "port_in  <= gpio_i(GPIO_NUM-1 downto 0)"),
    ("neorv32_gpio", "port_in2", 104, 0, {"LHS_PROC"}, "port_in2 <= port_in"),
    ("neorv32_gpio", "port_in", 104, 0, {"DIRR_ASS"}, "port_in2 <= port_in"),
    ("neorv32_gpio", "port_out", 109, 0, {"PROCESS_TRIG"}, "output_stage: process(port_out)"),
    ("neorv32_gpio", "gpio_o", 112, 0, {"LHS_PROC", "PART_SELECT"}, "gpio_o(GPIO_NUM-1 downto 0) <= port_out"),
    ("neorv32_gpio", "irq_typ", 120, 0, {"PROCESS_TRIG"}, "irq_trigger: process(port_in, port_in2, irq_typ, irq_pol)"),
    ("neorv32_gpio", "irq_typ", 123, 0, {"VAR_RHS_OPERAND", "INDEXED_NAME"}, "sel_v := irq_typ(i) & irq_pol(i)"),
    ("neorv32_gpio", "irq_trig", 125, 0, {"LHS_PROC", "INDEXED_NAME"}, "when \"00\"   => irq_trig(i) <= not port_in(i)"),
    ("neorv32_gpio", "port_in", 125, 0, {"RHS_OPERAND", "INDEXED_NAME"}, "when \"00\"   => irq_trig(i) <= not port_in(i)"),
    ("neorv32_gpio", "irq_pend", 141, 0, {"LHS_PROC"}, "irq_pend  <= irq_en and ((irq_pend and irq_clrn) or irq_trig)"),
    ("neorv32_gpio", "irq_pend", 141, 1, {"RHS_OPERAND"}, "irq_pend  <= irq_en and ((irq_pend and irq_clrn) or irq_trig)"),
    ("neorv32_gpio", "cpu_irq_o", 142, 0, {"LHS_PROC"}, "cpu_irq_o <= or_reduce_f(irq_pend)"),
    ("neorv32_gpio", "irq_pend", 142, 0, {"RHS_OPERAND"}, "cpu_irq_o <= or_reduce_f(irq_pend)"),
]


def selftest(log=print) -> bool:
    """Tags of the hand-read occurrences, with the profiler's code extract. -> True when every one matches."""
    import build_heldout_code_map as CM
    fails, prof = [], {}
    # parsed_heldout26/ is written by build_heldout_code_map after its closed-set self-test; before that, the copy in
    # parsed_tuning18/ (equal file for file, checked there) is read
    held = CM.HELDOUT if CM.PARSED_HELDOUT.is_dir() else CM.Source(CM.HELD_RTL, CM.PARSED_TUNING)
    for m in sorted({h[0] for h in HAND}):
        src = CM.TUNING if m in CM.tuning_modules() else held
        prof[m] = {n: rs for E in CM.entities(m, src, tagger) for n, rs in E["profile"].items()}
    for m, n, ln, k, want, text in HAND:
        rs = [r for r in prof[m].get(n, []) if r["Occurrence Lines"] == ln]
        got = set(rs[k]["SITE Tagged"]) if k < len(rs) else None
        line_ok = k < len(rs) and rs[k]["Line Text"].startswith(text)
        if got != want or not line_ok:
            fails.append((m, n, ln, k, sorted(want), sorted(got) if got is not None else None,
                          rs[k]["Line Text"][:60] if k < len(rs) else None))
    mods = sorted({h[0] for h in HAND})
    log(f"   code SITE tagger, {len(HAND)} hand-read occurrences in {len(mods)} modules "
        f"({', '.join(x.replace('neorv32_', '') for x in mods)}): {'PASS' if not fails else 'FAIL'}")
    for f in fails:
        log(f"      {f}")
    return not fails


def check(log=print) -> dict:
    """Agreement with the LLM profiler's (v3d validate) tags on the 15 tuning modules: identical tag set per row, and
    'occurs in a condition' (any COND tag on any row) per element. Expected 5,734/5,760 rows and 1,641/1,641 elements."""
    import build_heldout_code_map as CM
    import relation_experiments as RX
    import relation_stage as RS
    rows = exact = 0
    st, cond = Counter(), Counter()

    def counting_tagger(E, cols):
        t, s = tag_entity(E, cols)
        st.update(s)
        return t
    for m in CM.tuning_modules():
        llm = {e["entity"]: e for e in RS.load_module(m, RX.where(None))}
        for E in CM.entities(m, CM.TUNING, tagger=counting_tagger):
            tags = {(n, r["Occurrence ID"]): r["SITE Tagged"] for n, rs in E["profile"].items() for r in rs}
            L = llm[E["entity"]]
            fields = {s["name"] for s in L["signals"] if "." in s["name"]}
            for n, rs in L["profile"].items():
                a_el = b_el = False
                for r in rs:
                    a, b = set(r["SITE Tagged"]), set(tags.get((n, r["Occurrence ID"]), []))
                    rows += 1; exact += a == b
                    a_el |= bool(a & COND); b_el |= bool(b & COND)
                for scope in (("all",) + (("field",) if n in fields else ())):
                    cond[(scope, "n")] += 1
                    cond[(scope, "agree")] += a_el == b_el
                    cond[(scope, "yes")] += a_el
    res = {"rows": rows, "tag set identical": exact, "code stats": dict(st),
           "elements": cond[("all", "n")], "condition agree": cond[("all", "agree")], "condition yes (LLM)": cond[("all", "yes")],
           "internal fields": cond[("field", "n")], "field condition agree": cond[("field", "agree")],
           "field condition yes (LLM)": cond[("field", "yes")]}
    log(f"   --check (15 tuning modules): tag set identical to the LLM's on {exact:,}/{rows:,} rows; "
        f"'occurs in a condition' agrees on {res['condition agree']:,}/{res['elements']:,} elements "
        f"({res['condition yes (LLM)']} yes), on internal record fields {res['field condition agree']}/{res['internal fields']} "
        f"({res['field condition yes (LLM)']} yes); rows tagged by the statement model {st['by_ref']:,}, by Context/text "
        f"{st['by_text']:,}, uncovered {st['uncovered']}")
    return res


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if not selftest():
        print("SELF-TEST FAIL: nothing is reported")
        sys.exit(1)
    if "--check" in sys.argv[1:]:
        r = check()
        sys.exit(0 if (r["tag set identical"], r["rows"], r["condition agree"], r["elements"]) == (5734, 5760, 1641, 1641) else 1)
