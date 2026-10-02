"""Check that the layout move kept every pre-registered pin verifiable.

For each row of the three pin tables, as they stand at the git tag prereg-layout-before:
  1. the pinned bytes at the tag still hash to the registered sha12 (the pin held before the move);
  2. the same item at its new path either hashes to the same sha12 (moved byte-for-byte), or
  3. is a Python file whose new bytes equal the tagged bytes with some string literals rewritten, where every
     rewritten literal is the old literal with a moved root name prefixed by its new folder (data/, src/, runs/).
     Nothing else may differ: not code, not comments, not whitespace.
Prints one line per row and exits 1 on any failure. Run from the repo root:  python src/verify_layout_move.py
No file is written."""
from __future__ import annotations

import hashlib, io, re, subprocess, sys, tokenize

TAG = "prereg-layout-before"
TABLES = ["assetgen_meta/lasset_layer/PREREG.md", "assetgen_meta/HELDOUT_PREREG.md", "assetgen_meta/prompt_opt/HELDOUT_CHECK_PREREG.md"]
ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(?:(bytes|text|dir)\s*\|\s*)?`([0-9a-f]{12})`\s*\|", re.M)
DATA = ["RTL_data", "RTL_heldout", "ground_truth", "LAsset_initial_results", "parsed_tuning18", "parsed_heldout26", "parsed_heldout_raw"]
SRC = ["diagnose_step1", "eval_assets", "gt_extract", "icl_asset_examples", "icl_examples_0", "icl_examples_01", "icl_examples_01b",
       "icl_examples_01b_noparse", "icl_examples_01b_nosum", "icl_examples_01b_ot", "icl_examples_02", "parse_audit", "parse_roles",
       "parse_v3", "prompts", "prompts_parse_v2", "prompts_parse_v3", "prompts_v2", "rtl_parse", "stage_a", "stage_ceilings",
       "verify_icl", "vhdl_occurrence_context"]
MOVE = {**{d: "data/" + d for d in DATA}, **{m + ".py": "src/" + m + ".py" for m in SRC}}
START = r"(?<![\w/.\\-])"                       # a name that starts a path, not one inside another folder's path
REWRITES = [(re.compile(START + r"(" + "|".join(DATA) + r")(?![\w])"), r"data/\1"),
            (re.compile(START + r"((?:" + "|".join(SRC) + r")\.py)"), r"src/\1"),
            (re.compile(START + r"(assets_(?:tuning18|heldout26|opt)\w*|\{stem\}_)"), r"runs/\1")]


def git(*a, binary=False):
    r = subprocess.run(["git", *a], capture_output=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.decode(errors='replace').strip()}")
    return r.stdout if binary else r.stdout.decode("utf-8")


def new_path(p):
    for old, new in MOVE.items():
        if p == old or p.startswith(old + "/"):
            return new + p[len(old):]
    return p


def blobs(rev, p):
    """{relative path: bytes} of every tracked file at rev under p (a file gives {'': bytes})."""
    out = {}
    for line in git("ls-tree", "-r", "-z", rev, "--", p).split("\0"):
        if line:
            meta, path = line.split("\t", 1)
            rel = path[len(p):].lstrip("/")
            if "__pycache__" not in rel.split("/"):
                out[rel] = git("cat-file", "blob", meta.split()[2], binary=True)
    return out


def sha12(files, kind):
    if kind == "text":
        b = files[""].decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        return hashlib.sha256(b).hexdigest()[:12]
    if list(files) == [""]:
        return hashlib.sha256(files[""]).hexdigest()[:12]
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode("utf-8") + b"\0" + files[rel] + b"\0")
    return h.hexdigest()[:12]


def rewrite(lit):
    for rx, rep in REWRITES:
        lit = rx.sub(rep, lit)
    return lit


def units(src: str):
    """Tokens, with each f-string merged into one unit whose text is its whole source span."""
    toks = list(tokenize.generate_tokens(io.StringIO(src, newline="").readline))
    lines = src.splitlines(keepends=True)
    FS, FE = getattr(tokenize, "FSTRING_START", -1), getattr(tokenize, "FSTRING_END", -2)
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t.type == FS:
            depth, j = 0, i
            while True:
                depth += toks[j].type == FS
                depth -= toks[j].type == FE
                if depth == 0:
                    break
                j += 1
            e = toks[j]
            text = lines[t.start[0] - 1][t.start[1]:e.end[1]] if t.start[0] == e.end[0] else None
            out.append(("LIT", text if text is not None else "".join(x.string for x in toks[i:j + 1]), t.start, e.end))
            i = j + 1
            continue
        out.append(("LIT" if t.type == tokenize.STRING else tokenize.tok_name[t.type], t.string, t.start, t.end))
        i += 1
    return out


def literal_only(old: bytes, new: bytes):
    """-> (ok, [(line, old literal, new literal)], reason). ok only if new == old with allowed literal rewrites."""
    try:
        o, n = old.decode("utf-8"), new.decode("utf-8")
        to, tn = units(o), units(n)
    except (tokenize.TokenError, SyntaxError, UnicodeDecodeError) as e:
        return False, [], f"cannot tokenize ({e})"
    if len(to) != len(tn):
        return False, [], f"token count {len(to)} -> {len(tn)}"
    lines, edits, rebuilt = o.splitlines(keepends=True), [], {}
    for a, b in zip(to, tn):
        if a[:2] == b[:2]:
            continue
        if a[0] != b[0] or a[0] != "LIT":
            return False, edits, f"line {a[2][0]}: non-literal token changed ({a[1]!r} -> {b[1]!r})"
        if b[1] != rewrite(a[1]):
            return False, edits, f"line {a[2][0]}: literal {a[1]!r} -> {b[1]!r} is not a move rewrite"
        if a[2][0] != a[3][0]:
            return False, edits, f"line {a[2][0]}: multi-line literal changed"
        edits.append((a[2][0], a[1], b[1]))
        rebuilt.setdefault(a[2][0], []).append((a[2][1], a[3][1], b[1]))
    for ln, subs in rebuilt.items():           # old text with only these literals replaced must equal the new text
        s = lines[ln - 1]
        for c0, c1, txt in sorted(subs, reverse=True):
            s = s[:c0] + txt + s[c1:]
        lines[ln - 1] = s
    if "".join(lines) != n:
        return False, edits, "bytes outside the rewritten literals differ"
    return True, edits, ""


def selftest():
    cases = [(b'x = ROOT / "RTL_data"\n', b'x = ROOT / "data/RTL_data"\n', True),
             (b'p = ROOT / f"{stem}_{v}_r{k}"\n', b'p = ROOT / f"runs/{stem}_{v}_r{k}"\n', True),
             (b'a, b = ROOT / "RTL_data", BPA / "data/RTL_data"\n', b'a, b = ROOT / "data/RTL_data", BPA / "data/RTL_data"\n', True),
             (b'n = 3\n', b'n = 4\n', False),                                                         # code changed
             (b'x = ROOT / "RTL_data"\n', b'x = ROOT / "data/RTL_heldout"\n', False),                 # wrong target
             (b'x = 1  # RTL_data\n', b'x = 1  # data/RTL_data\n', False),                            # comment changed
             (b'x = ROOT / "RTL_data"\n', b'x = ROOT  /  "data/RTL_data"\n', False),                  # spacing changed
             (b'x = str(ROOT)\n', b'x = str(ROOT / "src")\n', False)]                                 # path expression, not literal
    ok = all(literal_only(a, b)[0] is want for a, b, want in cases)
    # hand-read line: eval_assets.py line 25 at the tag
    tagged = blobs(TAG, "eval_assets.py")[""].decode("utf-8").splitlines()[24]
    ok &= tagged == 'GT_DIR = Path("ground_truth")' and rewrite('"ground_truth"') == '"data/ground_truth"'
    return ok


def main():
    if not selftest():
        print("self-test FAIL: nothing below is reported")
        return 1
    print("self-test PASS (8 planted cases, 1 hand-read line)")
    fails, n = 0, 0
    for table in TABLES:
        for path, kind, want in ROW.findall(git("show", f"{TAG}:{table}")):
            n += 1
            kind = kind or "bytes"
            old = blobs(TAG, path)
            new_p = new_path(path)
            new = {k: v for k, v in blobs("HEAD", new_p).items()}
            before = sha12(old, kind) if old else "missing"
            after = sha12(new, kind) if new else "missing"
            if before != want:
                status, fails = f"FAIL: the pin did not hold at {TAG}", fails + 1
            elif after == want:
                status = "moved, bytes unchanged" if new_p != path else "unchanged"
            elif list(old) == [""] and list(new) == [""] and path.endswith(".py"):
                ok, edits, why = literal_only(old[""], new[""])
                status = f"path literals only: {len(edits)} rewritten on lines {sorted({e[0] for e in edits})}" if ok else f"FAIL: {why}"
                fails += not ok
            else:
                status, fails = "FAIL: changed and not a Python file", fails + 1
            print(f"{table.split('/')[-1]:24s} {path[:62]:62s} -> {new_p[:67]:67s} {want} {after} {status}")
    print(f"{n} rows, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
