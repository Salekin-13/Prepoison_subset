# Evidence layer on LAsset's list `rtl_only` (heldout)

As published: P 0.730, R 0.757, F1 0.743 (196 items, 189 reference entries). P = precision (share of listed items in the reference); R = recall (share of reference entries listed). Labels by the scorer's own matching.

| items | hits | false positives |
|---|---|---|
| single-element (the tested population) | 142 | 44 |
| compound (always kept) | 0 | 5 |
| name not in this RTL version (never dropped) | 1 | 4 |

Trace levels of resolved items (descriptive; T3 = use traced, close to universal):

| | items | T1 no record | T2 records, no use | T3 use traced |
|---|---|---|---|---|
| hits | 142 | 0% | 1% | 99% |
| false positives | 49 | 0% | 4% | 96% |

Resolution rules used: {'R1': 197, 'R2': 2}.

## H1, audit: does map evidence rank LAsset's held-out hits above its false positives?

Model trained on the tuning single-element items of this list, applied to the 186 held-out single-element items: AUC 0.639 (97.5% module-bootstrap interval 0.495 to 0.768). Within held-out, leave one module out: 0.768 (descriptive).

## H2, filter: does the map-based filter raise LAsset's held-out precision beyond random removal?

Threshold fixed on tuning: 0.000. Dropped 0 single-element items (0 hits, 0 false positives) in 0 modules.

| | P | R | F1 |
|---|---|---|---|
| as published | 0.730 | 0.757 | 0.743 |
| after the filter | 0.730 | 0.757 | 0.743 |

Change in P +0.000 (97.5% interval +0.000 to +0.000); change in R +0.000 (+0.000 to +0.000). Random removal of the same number per module: mean P 0.730 (97.5% range 0.730 to 0.730); share of random draws reaching the filter's P: 100.0%.

## Back-fill (descriptive only)

Added 4 input ports in 3 modules (pool 39), 3 of them hits; list after: P 0.730, R 0.772.

## Pre-registered verdicts (PREREG.md section 3)

- H1, audit (interval lower bound above 0.5): **does not hold**.
- H2, filter (precision interval above 0 and under 2.5% of random removals reaching it; not testable if fewer than 4 modules touched): **not testable**.
- What the data supports: **audit trail only: the map traces LAsset's items but does not tell its hits from its false positives**.

