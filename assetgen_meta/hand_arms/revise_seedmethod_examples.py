"""Revise a drafted seed-method example from a consolidated review (seedmethod_drafts/<ip>.feedback.txt), then re-check.
The previous draft is kept as <ip>.v<N>.json. Usage: python revise_seedmethod_examples.py omsp_gpio tiny_aes"""
from __future__ import annotations

import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import draft_seedmethod_examples as dr  # noqa: E402  (loads API.env, paths, SYSTEM)
import seedmethod_examples as sx         # noqa: E402

HEADER = ("\n\nREVIEW OF YOUR PREVIOUS DRAFT. Two independent reviewers checked it against the PROCEDURE and the RTL; "
          "the maintainer consolidated their findings below. Apply every item. Where an item removes an element, remove "
          "it from the output and from the tables, and adjust the analysis so it states the PROCEDURE rule that excludes "
          "it when that helps the demonstration. Keep everything that no item touches. Return the whole object again.\n"
          "CONSOLIDATED REVIEW:\n")


def main(ips):
    seed = sx.SEED_PATH.read_text(encoding="utf-8")
    client = dr.OpenAI(); usage = []
    for ip in ips:
        case = sx.load_case(ip)
        cur = dr.OUT / f"{ip}.json"
        prev = json.loads(cur.read_text(encoding="utf-8"))
        n = 1
        while (dr.OUT / f"{ip}.v{n}.json").exists():
            n += 1
        (dr.OUT / f"{ip}.v{n}.json").write_text(json.dumps(prev, indent=1, ensure_ascii=False), encoding="utf-8")
        fb = (dr.OUT / f"{ip}.feedback.txt").read_text(encoding="utf-8")
        user = dr.user_message(case, seed) + HEADER + fb + "\n\nPREVIOUS DRAFT:\n" + json.dumps(prev, ensure_ascii=False)
        txt, u, _st = dr.mt.call_text(client, dr.MODEL, dr.SYSTEM, user, "high", 65536, json_mode=True)
        usage.append(u); d = dr.mt.loads(txt)
        chk = sx.check_draft(case, d)
        print(time.strftime("%H:%M:%S"), ip, f"revision (prev kept as v{n}): hard {chk['hard']} flags {chk['flags']} "
              f"elements {len(chk['reported'])} additions {len(chk['additions'])}", flush=True)
        cur.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
        (dr.OUT / f"{ip}.check.json").write_text(json.dumps(chk, indent=1, ensure_ascii=False), encoding="utf-8")
    tin = sum(x["in"] for x in usage if x); tout = sum(x["out"] for x in usage if x)
    print(f"tokens in {tin} out {tout}; at $10/$50 per M: ${tin * 10 / 1e6 + tout * 50 / 1e6:.2f}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["omsp_gpio", "tiny_aes"])
