"""Blindness audit: read every agent transcript of a workflow run and list each tool call. An agent passes only if
every call is on its allowlist. No reference file, score, prompt of this project, or other file may be touched.

    python blind_agent/audit.py <workflow transcript dir> <role>      role: designer | executor | critic

designer : Read of TASK_BRIEF.md, MAP_FORMAT.md, inputs/design/*, the 5 PDFs, its own prompts/<id>/ files (round 2 also
           its executor outputs and critic report); Write of prompts/<id>/prompt.md and rationale.md only.
executor : Read of exactly the prompt file and the input file named in its task; Write of exactly its output file.
critic   : Read of MAP_FORMAT.md, the prompt it critiques, the outputs and the inputs it names; Write of its report only.
The allowlist for each agent is rebuilt from the paths in that agent's own first message, so the check needs no
side table: any path the agent was not handed is a violation.
"""
import json, re, sys
from collections import Counter
from pathlib import Path

PAPERS = {"2601.02624v2.pdf", "IEEE_P3164_Asset_Identification.pdf", "Accellera_SA-EDI_Standard_v10.pdf", "2502.04648.pdf",
          "SAIF_Automated_Asset_Identification_for_Security_Verification_at_the_Register_Transfer_Level.pdf"}
NO_PATH_TOOLS = {"StructuredOutput"}                 # the schema return; carries no file access


def norm(p: str) -> str:
    return str(p).replace("\\", "/").lower().rstrip("/")


def first_user_text(lines):
    """All user text before the agent's first reply: the workflow harness sends the relayed user request, then the
    computed task (which holds the paths)."""
    out = []
    for l in lines:
        if l.get("type") == "assistant":
            break
        m = l.get("message", {}) or {}
        if l.get("type") == "user" and m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                out.append(c)
            elif isinstance(c, list):
                out += [x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"]
    return "\n".join(out)


def tool_calls(lines):
    out = []
    for l in lines:
        m = l.get("message", {})
        if l.get("type") == "assistant" and isinstance(m.get("content"), list):
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    out.append((b.get("name"), b.get("input", {})))
    return out


def handed_paths(text):
    """Every absolute path in the agent's task text (E:/... or E:\\...)."""
    return {norm(p.rstrip(".,;:)`'\"")) for p in re.findall(r"[A-Za-z]:[\\/][^\s`'\"<>|]+", text)}


def audit_agent(path: Path):
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    task = first_user_text(lines)
    handed = handed_paths(task)
    calls = tool_calls(lines)
    bad = []
    for name, inp in calls:
        if name in NO_PATH_TOOLS:
            continue
        if name in ("Grep",) and inp.get("path") and norm(inp["path"]) in handed:
            continue                                     # a search inside ONE handed file is a read of that file
        if name in ("Read", "Write", "Edit"):            # Edit = rewriting part of one of its own handed files
            p = norm(inp.get("file_path", ""))
            ok = p in handed or (name == "Read" and Path(p).name in {x.lower() for x in PAPERS} and
                                 any(Path(h).name == Path(p).name for h in handed))
            if not ok:
                bad.append(f"{name} {inp.get('file_path')}")
        else:
            bad.append(f"{name} {json.dumps(inp)[:160]}")
    head = task.split("computed task text follows:", 1)[-1].strip()[:90].replace("\n", " ")
    return {"agent": path.stem, "task_head": head, "calls": Counter(n for n, _ in calls),
            "violations": bad}


def audit_dir(d):
    return [audit_agent(p) for p in sorted(Path(d).glob("agent-*.jsonl"))]


def selftest(tmp: Path) -> bool:
    """Three synthetic transcripts: clean (pass), a read of the reference file (void), a shell command (void)."""
    task = {"type": "user", "message": {"role": "user", "content": "computed task text follows:\n read E:/x/blind_agent/p.md and "
                                                                    "E:/x/blind_agent/inputs/tuning/m.txt, write E:/x/out/m.json"}}
    def tr(calls):
        return [task] + [{"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": n, "input": i}]}} for n, i in calls]
    cases = {"clean": (tr([("Read", {"file_path": "E:\\x\\blind_agent\\p.md"}), ("Read", {"file_path": "E:/x/blind_agent/inputs/tuning/m.txt", "offset": 2000}),
                           ("Write", {"file_path": "E:/x/out/m.json", "content": "{}"})]), False),
             "reads reference": (tr([("Read", {"file_path": "E:/x/ground_truth/manual_gt_neorv32.json"})]), True),
             "runs command": (tr([("Bash", {"command": "ls"})]), True),
             "greps handed file": (tr([("Grep", {"pattern": "x", "path": "E:/x/blind_agent/inputs/tuning/m.txt"})]), False),
             "greps a folder": (tr([("Grep", {"pattern": "x", "path": "E:/x"})]), True)}
    ok = True
    tmp.mkdir(parents=True, exist_ok=True)
    for k, (lines, want_void) in cases.items():
        p = tmp / f"agent-{k.replace(' ', '_')}.jsonl"
        p.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
        void = bool(audit_agent(p)["violations"])
        ok &= void == want_void
        print(f"   selftest {k}: {'VOID' if void else 'pass'} ({'ok' if void == want_void else 'WRONG'})")
    return ok


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "--selftest":
        sys.exit(0 if selftest(Path(sys.argv[2])) else 1)
    res = audit_dir(sys.argv[1])
    nbad = 0
    for r in res:
        nbad += bool(r["violations"])
        print(f"{'VOID' if r['violations'] else 'ok  '} {r['agent']} {dict(r['calls'])} | {r['task_head']}")
        for v in r["violations"]:
            print("      ", v)
    print(f"{len(res) - nbad}/{len(res)} agents pass the blindness audit")
