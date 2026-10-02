# Evidence layer on LAsset's list `refined` (heldout)

As published: P 0.791, R 0.862, F1 0.825 (206 items, 189 reference entries). P = precision (share of listed items in the reference); R = recall (share of reference entries listed). Labels by the scorer's own matching.

| items | hits | false positives |
|---|---|---|
| single-element (the tested population) | 162 | 41 |
| compound (always kept) | 0 | 1 |
| name not in this RTL version (never dropped) | 1 | 1 |

Trace levels of resolved items (descriptive; T3 = use traced, close to universal):

| | items | T1 no record | T2 records, no use | T3 use traced |
|---|---|---|---|---|
| hits | 162 | 1% | 2% | 98% |
| false positives | 42 | 0% | 5% | 95% |

Resolution rules used: {'R1': 207}.

## H1, audit: does map evidence rank LAsset's held-out hits above its false positives?

Model trained on the tuning single-element items of this list, applied to the 203 held-out single-element items: AUC 0.643 (97.5% module-bootstrap interval 0.493 to 0.776). Within held-out, leave one module out: 0.791 (descriptive).

## H2, filter: does the map-based filter raise LAsset's held-out precision beyond random removal?

Threshold fixed on tuning: 0.000. Dropped 0 single-element items (0 hits, 0 false positives) in 0 modules.

| | P | R | F1 |
|---|---|---|---|
| as published | 0.791 | 0.862 | 0.825 |
| after the filter | 0.791 | 0.862 | 0.825 |

Change in P +0.000 (97.5% interval +0.000 to +0.000); change in R +0.000 (+0.000 to +0.000). Random removal of the same number per module: mean P 0.791 (97.5% range 0.791 to 0.791); share of random draws reaching the filter's P: 100.0%.

## Back-fill (descriptive only)

Added 3 input ports in 3 modules (pool 35), 1 of them hits; list after: P 0.785, R 0.868.

Secondary list: secondary list: no decision rule.

