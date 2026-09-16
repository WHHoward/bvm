# BVM -> QB boundary timing replay (bvm-qb-boundary-timing-replay-v1-20260916)

- Status: DELAYED_CASES_ANALYZED
- Final state: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
- Scientific review: PASS; only the preregistered `DELAY_0P6` and `DELAY_1P2` cases were authorized and run.
- Fixture: 4 BVM -> COMMON_SL -> 8 JSL -> QBIN ideal voltage replay; QB/JTL/terminal remain removed.
- The answer below is limited to the timing causal question in this fixed replay counterfactual.

## Timing comparison

Phase values are raw radians; displayed turns use independent continuous unwrap(rad)/(2*pi) for navigation only. They are not SFQ counts.

| case | JS1 [110,121) p2p (turns) | JS2 [110,121) p2p (turns) | JS1 -0.5 crossing (ps) | JS2 -0.5 crossing (ps) |
|---|---:|---:|---:|---:|
| `EXACT_N3` | 6.3864044 | 6.3605665 | 113.4 | 112.4 |
| `DELAY_0P6` | 4.96737 | 4.8701895 | 113.6 | 112.5 |
| `DELAY_1P2` | 3.6979326 | 3.3915287 | 113.7 | 112.6 |

The detailed `114.8 ps` / `115.0 ps` JS1/JS2 raw samples, largest one-sample phase-step navigation landmarks, all active BVMs, JSL1..JSL8, COMMON_SL, LS3/RS, replay-source current, and JM1/JM2 navigation are in `result.json`.

## Same-JJ phase / voltage-area cross-check

Actual CSV timestamps are used for trapezoid integration. The area is a consistency cross-check, not an event count.

| case | signal | phase delta (turns) | V-area/Phi0 (turns) | residual (turns) |
|---|---|---:|---:|---:|
| `EXACT_N3` | `P(B_JS1|XBVM2)` | -6.3528459 | -6.3551239 | 0.002277971 |
| `EXACT_N3` | `P(B_JS2|XBVM2)` | -6.3323218 | -6.3340876 | 0.0017658254 |
| `DELAY_0P6` | `P(B_JS1|XBVM2)` | -4.9311466 | -4.9313442 | 0.00019762131 |
| `DELAY_0P6` | `P(B_JS2|XBVM2)` | -4.8405307 | -4.8386038 | -0.0019268597 |
| `DELAY_1P2` | `P(B_JS1|XBVM2)` | -3.6612366 | -3.6638982 | 0.0026615696 |
| `DELAY_1P2` | `P(B_JS2|XBVM2)` | -3.1865257 | -3.1841407 | -0.002384926 |

## Bounded timing answer

PASS: within this fixed ideal-voltage causal replay, delaying only the QBIN boundary evolution delays selected JS1/JS2 navigation landmarks and reduces the active-BVM JS1/JS2 trajectory excursion; the 1.2 ps delay produces the stronger bounded suppression.

This assessment is limited to the two ideal-voltage delay interventions. It does not treat replay as a physical QB/source equivalent, does not infer SFQ counts, and does not claim JTL or hardware behavior.

- `DELAY_0P6` and `DELAY_1P2` use exact stored-index shifts with a hold at the 110 ps sample; no interpolation or resampling was used.
- Pre-110 ps nonanticipation deltas and post-110 ps trajectory deltas are retained per shared signal.
- The final timing assessment is bounded to N3, the fixed amplitude/shape, BVM/R-loop parameters, solver, and 0–200 ps window.

## Evidence paths

- Raw/deck/log: `runs/EXACT_N3/`, `runs/DELAY_0P6/`, `runs/DELAY_1P2/`.
- Full-window standalone plots: `plots/EXACT_N3/`, `plots/DELAY_0P6/`, `plots/DELAY_1P2/`.
- Full-window comparison plots: `plots/comparisons/`.
- Machine evidence: `provenance.json` and `result.json`.
- Raw evidence ZIP: Drive only; the earlier exact-only ZIP remains immutable and is not overwritten.

Stop marker: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
