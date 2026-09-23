# Evidence-only result — bvm-bq-cb-gap-2x1-v2-20260923

Status: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
Scientific interpretation: `NOT PERFORMED` (the required authorization token was not supplied).
V2 physical solve count: 4/4. Cumulative JoSIM transient invocations including the unretained v1 incident: 5; the v1 output is excluded from evidence. Automatic follow-up: none.

## OBSERVED

All four registered runs completed with raw mechanical QA plus an independent Decimal arithmetic cross-check; the raw probe set and classic standalone/comparison visualizations are retained.
The table reports measured local phase endpoint progression (turns are `rad/(2π)` navigation) and signed voltage-time area on the same JJ and registered `[110,121)` stored-sample window. Terminal area is signed `V(R_TERM)` integral divided by Φ0 on `[110,200)`. These values are not event counts or functional classifications.

| mask/run | ACC1 BJ1 phase / area | GAP1 BJ1 phase / area | ACC2 BJ1 phase / area | GAP2 BJ1 phase / area | terminal signed area `[110,200)` |
|---|---:|---:|---:|---:|---:|
| 00 / N0_00 | phase 4.90197e-05 turn-nav; area 4.91305e-05 Φ0 | phase -0.000116772 turn-nav; area -0.000116782 Φ0 | phase 7.33704e-05 turn-nav; area 7.34762e-05 Φ0 | phase -4.17941e-05 turn-nav; area -4.17971e-05 Φ0 | -1.93459e-06 Φ0 |
| 01 / N1_01 | phase 0.000362237 turn-nav; area 0.000362321 Φ0 | phase 0.00078691 turn-nav; area 0.000786854 Φ0 | phase 0.00791382 turn-nav; area 0.00791378 Φ0 | phase 0.000949884 turn-nav; area 0.000949847 Φ0 | 11.8347 Φ0 |
| 10 / N1_10 | phase 0.00870498 turn-nav; area 0.00870497 Φ0 | phase 0.00120401 turn-nav; area 0.00120393 Φ0 | phase 0.000392635 turn-nav; area 0.000392649 Φ0 | phase 0.000218934 turn-nav; area 0.000218936 Φ0 | 12.343 Φ0 |
| 11 / N2_11 | phase 0.00904143 turn-nav; area 0.00904149 Φ0 | phase 0.00211945 turn-nav; area 0.00211933 Φ0 | phase 0.00825171 turn-nav; area 0.00825164 Φ0 | phase 0.00121612 turn-nav; area 0.00121609 Φ0 | 0.999998 Φ0 |

## DERIVED

Terminal pointwise deltas versus `N0_00` are included only where actual stored timestamps match exactly; otherwise the paired subtraction is `UNKNOWN`. See `analysis/terminal_delta_vs_N0_00.csv` and `analysis/comparison_summary.json`.
No population truth-table verdict, event count, SFQ-delivery claim, earliest-failure localization, mechanism explanation, convergence claim, or parameter recommendation is assigned in this operator report.

## Evidence

- Per-run classic review and stimulus/output pages: `plots/N*/review.html`, `plots/N*/stimulus.html`.
- Four-run classic comparison index: `plots/comparison/index.html`.
- Per-run raw metrics and QA: `runs/N*/analysis/`.
- Independent arithmetic reproduction from raw: `runs/N*/analysis/independent_check.json`.
- Machine preflight, execution and plot QA: `analysis/PREFLIGHT_QA.json`, `analysis/EXECUTION.json`, `qa/plot_qa.json`, `qa/comparison_qa.json`.
- Provenance: `analysis/SOURCE_LOCK.json`, each run's `metadata.json` and `source_manifest.json`.
- Raw files are immutable; no interpolation/resampling was performed; plots are descriptive only.
