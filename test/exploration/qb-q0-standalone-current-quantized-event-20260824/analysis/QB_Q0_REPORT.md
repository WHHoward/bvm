# QB-Q0 standalone current-to-quantized-event re-audit

## Verdict

This is an exploratory local-JJ phase/voltage-area audit. It does not test canonical BVM compatibility or downstream SFQ delivery.

## Core result

| fixture | Iin (µA) | N(BJs) | N(BJL1) | N(BJL2) | BJL2 per-pulse | classification |
|---|---:|---:|---:|---:|---|---|
| scaled | 0 | 0 | 0 | 0 | `0,0,0,0,0,0` | `ZERO_EVENT` |
| scaled | 45 | 67 | 0 | 0 | `0,0,0,0,0,0` | `NO_COMPLETE_EVENT` |
| scaled | 68.4 | 94 | 6 | 6 | `1,1,1,1,1,1` | `EXACTLY_ONE` |
| scaled | 90 | 96 | 6 | 12 | `2,2,2,2,2,2` | `MULTI_EVENT` |
| paper | 0 | 0 | 0 | 0 | `0,0,0,0,0,0` | `ZERO_EVENT` |
| paper | 68.4 | 0 | 0 | 0 | `0,0,0,0,0,0` | `NO_COMPLETE_EVENT` |
| paper | 90 | 0 | 0 | 0 | `0,0,0,0,0,0` | `NO_COMPLETE_EVENT` |

`N(...)` counts complete turn units inside same-JJ, same-segment phase/area-consistent candidates; it is a local diagnostic count, not an SFQ-delivery count. Candidate segment counts are retained in the CSV/JSON.

## Actual jjmit scaling used

The copied model is `jjmit(RTYPE=1, VG=2.8m, CAP=0.07p, r0=160, rn=16, icrit=0.1m)`. These values are reconstructed from the actual model's first-order AREA scaling, not from the old fast-event analysis.

| fixture | JJ | AREA | Ic (µA) | C (fF) | RN (Ω) | R0 (Ω) |
|---|---|---:|---:|---:|---:|---:|
| scaled | BJs | 0.5 | 50 | 35 | 32 | 320 |
| scaled | BJL1 | 0.36 | 36 | 25.2 | 44.4444 | 444.444 |
| scaled | BJL2 | 0.54 | 54 | 37.8 | 29.6296 | 296.296 |
| paper | BJs | 1.33 | 133 | 93.1 | 12.0301 | 120.301 |
| paper | BJL1 | 1.12 | 112 | 78.4 | 14.2857 | 142.857 |
| paper | BJL2 | 1.89 | 189 | 132.3 | 8.46561 | 84.6561 |

## BJL2 pulse-by-pulse/reset audit

| fixture | Iin (µA) | complete units per pulse | max post-window phase p2p (turn) | post complete units | event-count repeatability |
|---|---:|---|---:|---:|---|
| scaled | 0 | `0,0,0,0,0,0` | 0 | 0 | stable |
| scaled | 45 | `0,0,0,0,0,0` | 0 | 0 | stable |
| scaled | 68.4 | `1,1,1,1,1,1` | 0 | 0 | stable |
| scaled | 90 | `2,2,2,2,2,2` | 0 | 0 | stable |
| paper | 0 | `0,0,0,0,0,0` | 1.5915e-08 | 0 | stable |
| paper | 68.4 | `0,0,0,0,0,0` | 3.3391e-05 | 0 | stable |
| paper | 90 | `0,0,0,0,0,0` | 5.6293e-05 | 0 | stable |

## Activity and same-JJ area

| fixture | Iin (µA) | JJ | max activity p2p (turn) | largest Δphase (turn) | same-segment area (Φ0) | residual (turn) |
|---|---:|---|---:|---:|---:|---:|
| scaled | 0 | BJs | 0 | — | — | — |
| scaled | 0 | BJL1 | 1.6552e-06 | -1.6552e-06 | -1.6958e-06 | -4.061e-08 |
| scaled | 0 | BJL2 | 1.3846e-06 | 1.3846e-06 | 1.4085e-06 | 2.3874e-08 |
| scaled | 45 | BJs | 14.494 | 14.494 | 14.496 | 0.0016936 |
| scaled | 45 | BJL1 | 0.19548 | -0.19548 | -0.19617 | -0.00068511 |
| scaled | 45 | BJL2 | 0.09215 | -0.09215 | -0.092343 | -0.00019348 |
| scaled | 68.4 | BJs | 16.423 | 16.423 | 16.426 | 0.0026747 |
| scaled | 68.4 | BJL1 | 1.2255 | 1.2255 | 1.2268 | 0.0012493 |
| scaled | 68.4 | BJL2 | 1.096 | 1.096 | 1.0965 | 0.00050126 |
| scaled | 90 | BJs | 16.457 | 16.457 | 16.455 | -0.0018725 |
| scaled | 90 | BJL1 | 2.0292 | 1.8223 | 1.8241 | 0.0018219 |
| scaled | 90 | BJL2 | 2.0061 | 2.0061 | 2.0067 | 0.0006295 |
| paper | 0 | BJs | 0 | — | — | — |
| paper | 0 | BJL1 | 0.00057118 | -0.00057118 | -0.00057974 | -8.5606e-06 |
| paper | 0 | BJL2 | 0.0014071 | 0.0014071 | 0.0014249 | 1.7759e-05 |
| paper | 68.4 | BJs | 0.2512 | -0.23806 | -0.23943 | -0.0013618 |
| paper | 68.4 | BJL1 | 0.18383 | -0.14803 | -0.14878 | -0.0007475 |
| paper | 68.4 | BJL2 | 0.046582 | -0.037838 | -0.038044 | -0.00020601 |
| paper | 90 | BJs | 0.39668 | -0.37509 | -0.37709 | -0.0019962 |
| paper | 90 | BJL1 | 0.27879 | -0.21905 | -0.22036 | -0.0013132 |
| paper | 90 | BJL2 | 0.073438 | -0.056371 | -0.056707 | -0.00033616 |

## Observed

- The table reports direct `P`, `V`, and `I` traces from the same JJ and the same monotonic segment.
- The input is periodic: six starts at 10, 60, 110, 160, 210, and 260 ps. Per-pulse vectors are retained in `q0-execution-metrics.json`.
- A voltage peak or a current above a nominal Ic is not used as event evidence.

## Derived

- Phase turns are `ΔP/(2π)` from raw JoSIM phase in radians.
- Same-segment voltage area is `∫Vdt/Φ0` using the direct JJ voltage column.
- The exploratory candidate rule is `|Δturn|≥1`, matching area sign, and residual within `max(0.05, 0.10|Δturn|)` turn. It is task-local and explicitly unfrozen.

## Inference

- `EXACTLY_ONE` means one complete turn unit in BJL2 in every nonzero ideal-current pulse window, with no post-window candidate; a single approximately 2-turn monotonic segment is therefore `MULTI_EVENT`, not exactly-one.
- `NO_COMPLETE_EVENT` means no qualifying local BJL2 phase/area candidate was found under this exploratory rule; it is not a universal impossibility result.

## Unknown / limits

- No canonical BVM, transformer, DCSFQ, JTL, or T1 is connected.
- The periodic six-pulse fixture is a historical re-audit, not a single-pulse reset characterization or a convergence study.
- The paper comparison uses 90 µA bias from the historical BVM-paper fixture as provenance, while replacing the BVM input with an ideal-current source; it is not a reproduction of the paper's full experiment.
- No parameter optimization or automatic follow-up was performed.
