# The evidence layer on LAsset's own lists: result (2026-10-02)

Notebook `lasset_evidence_layer.ipynb` (executed once, headless); code `assetgen_meta/lasset_layer.py`; pre-registration
`assetgen_meta/lasset_layer/PREREG.md` (design v2, pins verified at run time); reports `assetgen_meta/lasset_layer/`.

Confirmatory (held-out, 26 modules, 189 entries, LAsset RTL-only list as published: P 0.730, R 0.757, 196 items):
- H1, audit: map-profile model trained on tuning, AUC 0.639, 97.5% interval 0.495 to 0.768 -> does not hold (lower
  bound under 0.5).
- H2, filter: threshold fixed on tuning was 0 (no threshold raised tuning F1), so nothing dropped -> not testable, as
  recorded in PREREG section 4 before the reading.
- Claim the data supports: "audit trail only".
Secondary, no decision rule: Spec+RTL AUC 0.674 [0.556, 0.788], filter drops 2 items (P 0.734 -> 0.741); refined
0.643 [0.493, 0.776]; within-held-out leave-one-module-out AUC 0.768 (RTL-only); back-fill +4 ports, 3 hits
(R 0.757 -> 0.772); 99% of hits and 96% of false positives have a traced use.
Design v1 was replaced after a tuning-only review (version drift and "used" were driving it); see PREREG section 1.
