# Evidence layer on LAsset's list `rtl_only` (tuning)

As published: P 0.680, R 0.748, F1 0.712 (122 items, 111 reference entries). P = precision (share of listed items in the reference); R = recall (share of reference entries listed). Labels by the scorer's own matching.

| items | hits | false positives |
|---|---|---|
| single-element (the tested population) | 82 | 26 |
| compound (always kept) | 0 | 11 |
| name not in this RTL version (never dropped) | 1 | 2 |

Trace levels of resolved items (descriptive; T3 = use traced, close to universal):

| | items | T1 no record | T2 records, no use | T3 use traced |
|---|---|---|---|---|
| hits | 82 | 1% | 2% | 96% |
| false positives | 37 | 0% | 5% | 95% |

Resolution rules used: {'R1': 133, 'R2': 3}.

## Development reading (fixes what held-out will use)

- Single-element items: 108. Leave-one-module-out AUC of the map model (hits vs false positives, 0.5 = chance): 0.448.
- Threshold chosen on tuning (leave-one-module-out probabilities, maximizing F1): 0.000; tuning F1 after that filter 0.712 against 0.712 as published.

