"""Bake-off re-runs: E0 (prompt v1) and E3 (prompt v2), declaration batches, replicates 2 and 3 on the 15 test modules.
Each replicate writes its own folder under relation_exp/. The E0 and E3 pools run side by side (20 calls each)."""
import os, sys, threading
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; os.chdir(ROOT)  # the repo root
sys.path.insert(0, str(ROOT / "step1")); sys.stdout.reconfigure(encoding="utf-8")
for l in (ROOT / "API.env").read_text(encoding="utf-8").splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k, v = l.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
import relation_stage as RS, relation_experiments as RX, lasset_step1 as S
from openai import OpenAI
client = OpenAI().with_options(timeout=900, max_retries=0)
T = S.test_modules()
lock = threading.Lock()
def log(*a):
    with lock:
        print(*a, flush=True)

def arm(name, prompt):
    for rep in (2, 3):
        w = RX.where(f"{name}_rep{rep}")
        c = RS.run_many(T, client=client, where=w, workers=20, prompt_file=prompt, log=lambda *a: None)["cost"]
        log(f"{name} rep{rep}: calls {c.get('calls', 0)}, failed {c.get('failed', 0)}, {c.get('minutes')} min, <= ${c.get('usd_upper')}")
        ps = RX.psha(prompt)
        for m in T:
            RS.merge(m, RS.check(m, psha=ps, where=w, log=lambda *a: None), where=w, log=lambda *a: None)
        r = RX.rates(RX.summarize(T, w, prompt)["total"])
        log(f"{name} rep{rep}: mirrored recall {r['mirrored_recall']:.1%} precision {r['mirrored_precision']:.1%}")

# one arm per PROCESS: relation_stage builds its loader with a temporary chdir, so two threads in one process collide
arm(sys.argv[1], {"E0": RX.PROMPT_V1, "E3": RX.PROMPT_V2}[sys.argv[1]])
log("RERUNS DONE")
