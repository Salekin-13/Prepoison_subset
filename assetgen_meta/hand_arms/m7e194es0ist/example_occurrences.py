"""Occurrence tables for the two Verilog worked examples, computed by code so the hand-written map excerpts cannot
invent IDs. Per module (entity) of the file: every declared port / wire / reg name (declarations may span several lines
and list several names), and each whole-word appearance of it inside that module, in order, IDs from 1, as the real
map numbers occurrences per (entity, element). Adds "declared" {module: {name: {kind, decl_line}}} and "occurrences"
{module: {name: [{id, line}]}} to examples/<name>.source.json.
Self-test: hand-read lines of omsp_gpio (per_dout declared as an output; p1dir assigned under p1dir_wr) and of tiny_aes
(z0 and k9b, declared on continuation lines, are found)."""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
START = re.compile(r"^\s*(input|output|inout|wire|reg)\b")
KEYWORDS = {"input", "output", "inout", "wire", "reg", "signed", "assign", "always", "begin", "end", "if", "else", "posedge",
            "negedge", "or", "and", "case", "endcase", "default", "module", "endmodule", "parameter", "localparam"}


def rows(numbered: str):
    for l in numbered.split("\n"):
        n, s = l.split("|", 1)
        yield int(n), s.strip()


def modules(numbered: str) -> dict:
    """{module: [(line, text)]} from 'module X' to 'endmodule'."""
    out, cur = {}, None
    for n, s in rows(numbered):
        m = re.match(r"^module\s+(\w+)", s)
        if m:
            cur = m.group(1)
            out[cur] = []
        if cur is not None:
            out[cur].append((n, s))
        if re.match(r"^endmodule\b", s):
            cur = None
    return out


def declared(body) -> dict:
    out, stmt, first, kind = {}, "", None, None
    for n, s in body:
        if stmt == "":
            m = START.match(s)
            if not m:
                continue
            kind, first, stmt = m.group(1), n, s
        else:
            stmt += " " + s
        if ";" in stmt or stmt.rstrip().endswith(")") or (kind in ("input", "output", "inout") and stmt.rstrip().endswith(",")):
            decl = stmt.split(";", 1)[0]
            decl = START.sub("", decl)
            decl = re.sub(r"\b(wire|reg|signed)\b", " ", decl)
            decl = re.sub(r"\[[^\]]*\]", " ", decl)
            parts = [re.sub(r"=.*", "", p) for p in decl.split(",")]
            for p in parts:
                for nm in re.findall(r"[A-Za-z_]\w*", p)[:1]:
                    if nm not in KEYWORDS and nm not in out:
                        out[nm] = {"kind": kind, "decl_line": first}
            stmt = ""
    return out


def occurrences(body, names) -> dict:
    occ = {nm: [] for nm in names}
    for n, s in body:
        for nm in names:
            for _m in re.finditer(rf"(?<![\w$.]){re.escape(nm)}(?![\w$])", s):
                occ[nm].append({"id": len(occ[nm]) + 1, "line": n})
    return occ


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for f in sorted((HERE / "examples").glob("*.source.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        mods = modules(d["rtl_numbered"])
        dec = {m: declared(b) for m, b in mods.items()}
        occ = {m: occurrences(b, dec[m]) for m, b in mods.items()}
        refs = {(s["entity"], s["asset rtl"]) for c in d["old_final"]["conceptual assets"] for s in c["related structural assets"]}
        missing = sorted(r for r in refs if r[1] not in dec.get(r[0], {}))
        print(f"{d['name']}: modules {list(mods)}; declared {sum(len(v) for v in dec.values())} names, "
              f"{sum(len(x) for v in occ.values() for x in v.values())} occurrences; references not declared in their entity: {missing}")
        L = {n: s for n, s in rows(d["rtl_numbered"])}
        if d["name"] == "omsp_gpio":
            g = dec["omsp_gpio"]
            wr = [o["line"] for o in occ["omsp_gpio"].get("p1dir", []) if "p1dir_wr" in L[o["line"]] and "p1dir <=" in L[o["line"]]]
            ok = g.get("per_dout", {}).get("kind") == "output" and bool(wr) and "reg_lo_write" in g
            print(f"   selftest omsp_gpio: per_dout output, p1dir written under p1dir_wr at {wr}, reg_lo_write declared: {'ok' if ok else 'FAIL'}")
            assert ok
        if d["name"] == "tiny_aes":
            found = {nm: [m for m in dec if nm in dec[m]] for nm in ("z0", "k9b")}
            ok = all(found.values())
            print(f"   selftest tiny_aes: z0 / k9b declared in {found}: {'ok' if ok else 'FAIL'}")
            assert ok
            print("   largest per-module lists:", sorted(((len(v), m, nm) for m in occ for nm, v in occ[m].items()), reverse=True)[:4])
        d["declared"], d["occurrences"] = dec, occ
        f.write_text(json.dumps(d, indent=1), encoding="utf-8")
