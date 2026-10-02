# Evidence layer on LAsset's list `spec_rtl` (tuning)

As published: P 0.737, R 0.910, F1 0.815 (137 items, 111 reference entries). P = precision (share of listed items in the reference); R = recall (share of reference entries listed). Labels by the scorer's own matching.

| items | hits | false positives |
|---|---|---|
| single-element (the tested population) | 100 | 31 |
| compound (always kept) | 0 | 2 |
| name not in this RTL version (never dropped) | 1 | 3 |

Trace levels of resolved items (descriptive; T3 = use traced, close to universal):

| | items | T1 no record | T2 records, no use | T3 use traced |
|---|---|---|---|---|
| hits | 100 | 1% | 3% | 96% |
| false positives | 33 | 0% | 6% | 94% |

Resolution rules used: {'R1': 138}.

## Development reading (fixes what held-out will use)

- Single-element items: 131. Leave-one-module-out AUC of the map model (hits vs false positives, 0.5 = chance): 0.676.
- Threshold chosen on tuning (leave-one-module-out probabilities, maximizing F1): 0.322; tuning F1 after that filter 0.824 against 0.815 as published.

