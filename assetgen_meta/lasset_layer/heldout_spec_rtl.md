# Evidence layer on LAsset's list `spec_rtl` (heldout)

As published: P 0.734, R 0.862, F1 0.793 (222 items, 189 reference entries). P = precision (share of listed items in the reference); R = recall (share of reference entries listed). Labels by the scorer's own matching.

| items | hits | false positives |
|---|---|---|
| single-element (the tested population) | 162 | 55 |
| compound (always kept) | 0 | 2 |
| name not in this RTL version (never dropped) | 1 | 2 |

Trace levels of resolved items (descriptive; T3 = use traced, close to universal):

| | items | T1 no record | T2 records, no use | T3 use traced |
|---|---|---|---|---|
| hits | 162 | 1% | 2% | 98% |
| false positives | 57 | 0% | 5% | 95% |

Resolution rules used: {'R1': 222, 'R3': 1}.

## H1, audit: does map evidence rank LAsset's held-out hits above its false positives?

Model trained on the tuning single-element items of this list, applied to the 217 held-out single-element items: AUC 0.674 (97.5% module-bootstrap interval 0.556 to 0.788). Within held-out, leave one module out: 0.823 (descriptive).

## H2, filter: does the map-based filter raise LAsset's held-out precision beyond random removal?

Threshold fixed on tuning: 0.322. Dropped 2 single-element items (0 hits, 2 false positives) in 2 modules.

| | P | R | F1 |
|---|---|---|---|
| as published | 0.734 | 0.862 | 0.793 |
| after the filter | 0.741 | 0.862 | 0.797 |

Change in P +0.007 (97.5% interval +0.000 to +0.019); change in R +0.000 (+0.000 to +0.000). Random removal of the same number per module: mean P 0.734 (97.5% range 0.732 to 0.741); share of random draws reaching the filter's P: 5.9%.

## Back-fill (descriptive only)

Added 4 input ports in 4 modules (pool 35), 1 of them hits; list after: P 0.726, R 0.868.

Secondary list: secondary list: no decision rule.

