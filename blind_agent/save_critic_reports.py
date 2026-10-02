"""Round 2 deviation record: the harness refused the critics' Write of report.md ("Subagents should return findings as
text"), so each critic returned its report as its final text. This copies those texts from the workflow journal to
blind_agent/critic/<version>/report.md verbatim, for the record. The round-2 revisers did NOT see them.

    python blind_agent/save_critic_reports.py <workflow transcript dir>
"""
import json, re, sys
from pathlib import Path

B = Path(__file__).resolve().parent
d = Path(sys.argv[1])
label = {}
for l in (d / "journal.jsonl").read_text(encoding="utf-8").splitlines():
    o = json.loads(l)
    if o.get("type") == "started":
        label[o["key"]] = o.get("label", "")
    if o.get("type") == "result" and label.get(o["key"], "").startswith("critic "):
        v = label[o["key"]].split()[1]
        out = B / "critic" / v / "report.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(str(o["result"]), encoding="utf-8")
        print(v, len(str(o["result"])), "chars ->", out)
