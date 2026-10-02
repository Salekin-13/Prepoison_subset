"""Hand arm m7e194es0i01b: the seed's execution prompt + the baseline's two port-heavy worked examples.

WHAT. System prompt = seed exec prompt (m7e194es0c, meta sample 7e194e/sample_0) + "\n\n" + the omsp_gpio and tiny_aes
case studies in their RTL-only form (icl_examples_01b_noparse.ICL_ASSET_EXAMPLES_01B_NOPARSE, the block the baseline
v2x3r8 used before the OpenTitan case was appended). Joined by code, as the baseline joins its core and examples.

WHY (pre-registered on the roadmap page, rev 4). Step 1b is blocked by recall: the seed misses input ports (15.0 hits
per run against the baseline's 20.7). In v1 arm A-01 these two examples raised port recall by 0.181. The OpenTitan case
is left out: it lowered port recall in X-3 and fails check_exec_prompt (clk_i in its RTL).

EDITS TO THE EXAMPLE BLOCK, all asserted:
1. Each EMITTED OUTPUT object is converted from the old flat format ({"IP", "ConceptualAssets", "Assets"}) to the seed's
   nested schema. Copied unchanged: module name (= IP), concept text, concept security objective, element name, entity.
   "reasoning" = the concept's "Why" sentence, verbatim. "realization" = "sets" for an input port and "exit port" for an
   output port (seed lines 206 and 208); directions are read per declaring entity from the example's own RTL and must
   equal a hand-read table. Per-asset Asset Name / Functionality / Justification have no slot in the schema and are dropped.
2. Three sentences (the preamble and one in each case study) say a secondary consequence goes in the "Justification",
   a field the new format does not have; each is reworded to "reasoning" (an inconsistency caused by edit 1).
Nothing else in the seed or the examples changes.
"""
from __future__ import annotations

import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "assetgen_meta"))
from icl_examples_01b_noparse import ICL_ASSET_EXAMPLES_01B_NOPARSE as SRC  # noqa: E402

VERSION = "m7e194es0i01b"
SEED_PATH = ROOT / "assetgen_meta/runs/meta_7e194e6254be_gpt-6-astra/sample_0/exec_prompt.txt"
OUT_DIR = ROOT / "assetgen_meta/hand_arms" / VERSION

# Hand-read from the example RTL (declaring entity, element) -> direction. The regex reader below must agree.
HAND = {("omsp_gpio", "per_en"): "input", ("omsp_gpio", "per_we"): "input",
        **{("omsp_gpio", f"p{i}_dout_en"): "output" for i in range(1, 7)},
        **{("omsp_gpio", f"p{i}_sel"): "output" for i in range(1, 7)},
        ("aes_128", "key"): "input", ("final_round", "key_in"): "input",
        ("final_round", "state_in"): "input", ("final_round", "state_out"): "output"}
REALIZATION = {"input": "sets", "output": "exit port"}

# (old, new): every sentence that names the dropped "Justification" field, reworded to the schema's "reasoning".
REWORD = [
    ("and give each one exactly one dominant Security Objective with any secondary consequence noted in the "
     "Justification.",
     "and give each conceptual asset exactly one dominant security objective, with any secondary consequence "
     "noted in its reasoning."),
    ("the denial-of-service consequence goes in the Justification, not into a second asset.",
     "the denial-of-service consequence goes in the reasoning, not into a second asset."),
    ("the integrity consequence is recorded in its Justification.",
     "the integrity consequence is recorded in its reasoning."),
]


def reword(text: str, old: str, new: str) -> str:
    """Replace one sentence whose words may be wrapped across lines; the original line breaks are kept."""
    pat = r"\s+".join(re.escape(w) for w in old.split())
    hits = list(re.finditer(pat, text))
    assert len(hits) == 1, f"sentence not found exactly once ({len(hits)}): {old[:60]}"
    m = hits[0]
    seps = re.findall(r"\s+", m.group(0))
    words = new.split()
    assert len(words) == len(old.split()) or len(seps) == len(old.split()) - 1
    if len(words) == len(old.split()):          # same word count: keep the source's own spacing and line breaks
        out = words[0] + "".join(s + w for s, w in zip(seps, words[1:]))
    else:
        out = new
    return text[:m.start()] + out + text[m.end():]


def span(s: str, needle: str):
    k = s.index(needle); i = s.rindex("{", 0, k); d = 0
    for j in range(i, len(s)):
        d += (s[j] == "{") - (s[j] == "}")
        if d == 0:
            return i, j + 1
    raise ValueError(needle)


def directions(rtl: str) -> dict:
    """(module, port) -> input|output|inout, from Verilog declarations inside each module ... endmodule."""
    out = {}
    for m in re.finditer(r"^\s*module\s+(\w+)(.*?)^\s*endmodule", rtl, re.M | re.S):
        mod, body = m.group(1), m.group(2)
        for d in re.finditer(r"^\s*(input|output|inout)\b([^;]*);", body, re.M):
            names = re.sub(r"\[[^\]]*\]", " ", d.group(2))
            names = re.sub(r"\b(reg|wire|signed|logic)\b", " ", names)
            for n in re.findall(r"\b[A-Za-z_]\w*\b", names):
                out[(mod, n)] = d.group(1)
    return out


def convert(src: str, ip: str) -> tuple[str, list]:
    a, b = span(src, f'"IP": "{ip}"')
    obj = json.loads(src[a:b])
    assert json.dumps(obj, indent=1) == src[a:b], f"{ip}: source JSON is not indent=1"
    head = src.rindex("### CASE STUDY", 0, a)
    rtl = src[src.index("=== RTL ===", head):src.index("EMITTED OUTPUT:", head)]
    dirs = directions(rtl)
    concepts = []
    for c in obj["ConceptualAssets"]:
        refs = []
        for x in obj["Assets"]:
            if x["Concept"] != c["id"]:
                continue
            key = (x["Entity"], x["Asset RTL"])
            assert dirs.get(key) == HAND[key], f"{key}: RTL says {dirs.get(key)}, hand table {HAND[key]}"
            refs.append({"asset rtl": x["Asset RTL"], "entity": x["Entity"], "realization": REALIZATION[HAND[key]]})
        concepts.append({"concept": c["Concept"], "security objective": c["Security Objective"],
                         "reasoning": c["Why"], "related structural assets": refs})
    new = {"module name": obj["IP"], "conceptual assets": concepts}
    assert sorted(r["asset rtl"] for c in concepts for r in c["related structural assets"]) == \
        sorted(x["Asset RTL"] for x in obj["Assets"]), f"{ip}: element set changed"
    return src[:a] + json.dumps(new, indent=1) + src[b:], [(obj["IP"], x["Entity"], x["Asset RTL"]) for x in obj["Assets"]]


def build() -> tuple[str, str, dict]:
    seed = SEED_PATH.read_text(encoding="utf-8")
    ex, kept = SRC, []
    for ip in ("omsp_gpio", "tiny_aes"):
        ex, k = convert(ex, ip)
        kept += k
    for old, new in REWORD:
        ex = reword(ex, old, new)
    # no old-format keys may survive; the only 'Justification' left must be none
    for bad in ('"IP":', '"ConceptualAssets"', '"Assets"', '"Asset RTL"', '"Justification"', "Justification"):
        assert bad not in ex, f"old-format text survives: {bad}"
    assert len(kept) == 18 and len(HAND) == 18 and {(e, n) for _ip, e, n in kept} == set(HAND)
    assert "OpenTitan" not in ex and "clk_i" not in ex
    system = seed + "\n\n" + ex
    info = {"version": VERSION, "seed_sha12": hashlib.sha256(seed.encode()).hexdigest()[:12],
            "example_source": "icl_examples_01b_noparse.ICL_ASSET_EXAMPLES_01B_NOPARSE",
            "example_sha12": hashlib.sha256(SRC.encode()).hexdigest()[:12],
            "system_sha12": hashlib.sha256(system.encode()).hexdigest()[:12],
            "chars": {"seed": len(seed), "examples": len(ex), "system": len(system)},
            "elements": len(kept), "realization": {k[1]: REALIZATION[v] for k, v in HAND.items()}}
    return system, ex, info


def selftest():
    """The direction reader against hand-read declarations (lines quoted from the example RTL)."""
    t = directions("module m1 (a, b, c);\n input a;\n input [1:0] b;\n output reg [7:0] c;\nendmodule\n"
                   "module m2 (x, key);\n input [127:0] x, key;\n output y;\nendmodule\n")
    assert t == {("m1", "a"): "input", ("m1", "b"): "input", ("m1", "c"): "output",
                 ("m2", "x"): "input", ("m2", "key"): "input", ("m2", "y"): "output"}, t


if __name__ == "__main__":
    selftest()
    system, ex, info = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "exec_prompt.txt").write_text(system, encoding="utf-8")
    (OUT_DIR / "examples_converted.txt").write_text(ex, encoding="utf-8")
    (OUT_DIR / "build_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(json.dumps(info, indent=2))
