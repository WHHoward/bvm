# M7B A02-local Analysis — canonical JTL measurement-pipeline replay

- A01 raw CSV (read-only reference): `research/tasks/M7-LITE-001/attempts/A01/runs/m7-jtl-cal-20260812-01/raw/m7-jtl-cal-20260812-01.csv`
- A01 raw CSV SHA-256: `728c112ec18864a9f84a0f73e3ffedf39051b528c8e3785b5632f409190cda52`
- Declared window: `[6.000e-12, 5.000e-11)` (half-open, seconds; post-bias / end-of-run)
- Selected samples: first index 60 (t=6.000000e-12 s), last index 498 (t=4.990000e-11 s), count 439
- Integration: trapezoid on actual CSV time axis over the selected window samples; area_turns = area / Phi0 (Phi0 = 2.067833848e-15 Wb)

| junction | phase_delta_rad | phase_delta_turns | area_turns | residual_turns |
|---|---:|---:|---:|---:|
| B1|XDUT | 6.375604500000000e+00 | 1.014708971373932e+00 | 1.014850246883447e+00 | -1.412755095155926e-04 |
| B2|XDUT | 6.341850200000001e+00 | 1.009336807678325e+00 | 1.007923877022203e+00 | 1.412930656122136e-03 |

## Boundary (explicit, retained from A01)

- These are raw signed measurement-pipeline residuals, reported WITHOUT acceptance/rejection against any tolerance (tolerance freeze is M9).
- They establish NO local/JTL event, NO SFQ count, NO downstream reception, NO fluxoid, NO route result, NO Gate, and NO physical conclusion.
- LITE evidence cannot be promoted retrospectively to FROZEN.

## Computation

Elementary independent arithmetic (this file's generator): half-open window selection by actual time, `phase_delta = P[last] - P[first]`, trapezoid sum on the selected window samples' actual time axis, `area_turns = area / Phi0`. No production helper used for these numbers.
