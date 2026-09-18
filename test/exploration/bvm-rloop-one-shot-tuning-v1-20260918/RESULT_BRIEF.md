# BVM R-loop one-shot tuning v1 — evidence brief

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Status

- Registered Stage A solves: `20`
- Completed physical solves: `20/20`
- Raw QA: `PASS`
- Compact visualization QA: `PASS`
- Scientific interpretation: `NOT_PERFORMED`
- Gate-S: `REVIEW_REQUIRED` for human review; no fixed percentage threshold was applied.
- Gate-R: `AMBIGUOUS` descriptive label; no formal one-shot/SFQ classifier was applied.
- Automatic follow-up: `NONE`

## Exact matrix

`A000_CANONICAL` (OPEN/OPEN), `A001` (20/20 ohm), `A002` (12/12 ohm), and
`A003` (8/8 ohm), each with PASSIVE masks `0000`, `0001`, `0011`, `0111`,
and `1111`. No closed solve or extra shunt point was run.

## Evidence retained

- Raw CSV, immutable deck, stimulus, solver log, metadata, and signal manifest under `runs/<CASE_ID>/cases/`.
- JM1/JM2 P/V/I, S-loop branch I/V, JS1/JS2 P/V/I, R-loop branch I/V, COMMON_SL, and JSL P/V/I are requested and manifest-checked.
- `analysis/case_metrics.json` contains windowed S-loop state metrics, R-loop navigation/activity metrics, same-JJ voltage-area cross-checks, and passive `I(B_JSL8)` population metrics.
- `analysis/gate_s_comparison.json` contains candidate-minus-A000 mechanical window arithmetic.
- `analysis/per_signal_window_metrics.csv` and `analysis/population_metrics.csv` are raw-derived tables.
- `plots/<CASE_ID>/review.html` is a compact five-page-style review view; no exhaustive atlas and no cross-run comparison plots were generated.

Phase `P(...)` values remain raw radians. `rad/(2*pi)` turns are navigation only,
not formal SFQ counts.

## Stop

`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`

