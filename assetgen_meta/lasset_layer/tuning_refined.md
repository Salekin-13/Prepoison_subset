# Evidence layer on LAsset's list `refined` (tuning)

As published: P 0.800, R 0.901, F1 0.847 (125 items, 111 reference entries). P = precision (share of listed items in the reference); R = recall (share of reference entries listed). Labels by the scorer's own matching.

| items | hits | false positives |
|---|---|---|
| single-element (the tested population) | 99 | 22 |
| compound (always kept) | 0 | 1 |
| name not in this RTL version (never dropped) | 1 | 2 |

Trace levels of resolved items (descriptive; T3 = use traced, close to universal):

| | items | T1 no record | T2 records, no use | T3 use traced |
|---|---|---|---|---|
| hits | 99 | 1% | 3% | 96% |
| false positives | 23 | 0% | 0% | 100% |

Resolution rules used: {'R1': 125}.

## Development reading (fixes what held-out will use)

- Single-element items: 121. Leave-one-module-out AUC of the map model (hits vs false positives, 0.5 = chance): 0.600.
- Threshold chosen on tuning (leave-one-module-out probabilities, maximizing F1): 0.000; tuning F1 after that filter 0.847 against 0.847 as published.

