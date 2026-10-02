# Engineer prompt v1: blind SoC-security analysis from RTL + relation map (2026-10-01)

`engineer_prompt_v1.md` is a prompt written from the task alone (IEEE P3164's four questions applied to flows drawn
from the relation map's typed edges; roles stores / sets / computes / exit port; influence points reported separately),
not from any tested asset prompt. It passes the project's prompt checks (no corpus identifier, no numeric hint, no use
of comments).

Seven blind Claude analysts (Opus), one per module, saw only the module's comment-stripped RTL with original line numbers
and its code-written relation map (`step1/lasset_step1/relation_map_code/b0e767000ec2_func-8406f390b729/`), plus the prompt.
Scored afterwards against the ground truth (strict names), primary elements only, and with the secondary list added:

| module | GT | engineer primary P / R | with secondary R | winner m7e194es0ism P / R (mean of 3 runs) |
|---|---|---|---|---|
| hwspinlock | 2 | 1.00 / 1.00 | 1.00 | 1.00 / 1.00 |
| wdt | 8 | 0.57 / 1.00 | 1.00 | 0.55 / 0.96 |
| cpu_cp_muldiv | 12 | 0.44 / 0.67 | 1.00 | 0.56 / 0.86 |
| cache | 6 | 0.05 / 0.33 | 0.67 | 0.11 / 0.50 |
| sys | 2 | 0.00 / 0.00 | 0.00 | 0.13 / 0.67 |
| debug_dtm | 5 | 0.22 / 0.80 | 1.00 | 0.20 / 0.80 |
| spi | 8 | 0.32 / 1.00 | 1.00 | 0.25 / 0.83 |

All 7: primary P 0.262 R 0.744 (tp 32, fp 90, GT 43); primary + secondary P 0.204 R 0.907; winner P 0.294 R 0.814.
Every primary citation (122 of 122) resolves to a real occurrence id of the element in the map.

What the reference counts that the P3164 primary framing demotes to "influence": start strobes (mul.start, div.start),
sign flags (ctrl.rs*_is_signed), the TMS pin, a write enable (we_i), a hit flag (cache_i.sta_hit). What the analysts
report that the reference omits: every stored or exported point along a flow (data arrays, FIFO fields, config bits
such as ctrl.cpha/cpol/strict, reset outputs, DMI request fields). sys: the analyst answered all four questions "no"
for the clock-enable path (the reference's two assets) and reported the reset generator instead.

Files: results/<module>.json (flows, four-question answers, primary/secondary/excluded with occurrence ids, map
assessment, process notes); scores.json; model_reasoning_audit.json (audit of the winner's and the map arm's reasoning
on the same modules); build_packs.py, score_results.py. Log: step1/lasset_step1/RELATION_EXPERIMENTS_LOG.md.
