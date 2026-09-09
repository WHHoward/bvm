# RESULT_BRIEF — QB RJ1/L1 local sensitivity

## Experiment identity

`qb-rj1-l1-local-sensitivity-v1-20260909` is an `EXPLORATORY / QUICK`
five-run local parameter-sensitivity experiment on the historical 4-BVM
shared-`COMMON_SL` ARRAY fixture. It is not an optimization sweep. The
authoritative setup and machine gate are in [experiment.yaml](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/experiment.yaml), [PREFLIGHT.md](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/PREFLIGHT.md), and [preflight.json](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/preflight.json).

## Exact authorized run matrix

| run | RJ1 | L1 | purpose |
|---|---:|---:|---|
| `NOMINAL` | 12.0 ohm | 2.0 pH | new matched internal baseline |
| `L1_DOWN` | 12.0 ohm | 1.9 pH | L1 decrease |
| `L1_UP` | 12.0 ohm | 2.1 pH | opposite-direction L1 control |
| `RJ1_UP_05` | 12.5 ohm | 2.0 pH | small RJ1 increase |
| `RJ1_UP_10` | 13.0 ohm | 2.0 pH | larger RJ1 increase |

Exactly five solver solves were executed. No additional mask, combined
RJ1+L1 point, replay, timestep run or follow-up was executed.

## Artifact QA

- Execution: `RUN_PASS`, exactly 5/5 registered solves.
- Raw artifact: `VALID`; each raw has 1999 samples from 0 to 199.9 ps,
  strictly increasing time and finite values.
- Stored grid: all five raw files have exact identical time tokens; the actual
  grid includes a recorded 0.2 ps interval, so all integration uses actual
  timestamps.
- Full probe status: `UNKNOWN` only for the optional `V(IB|XBQ1)` column,
  which JoSIM did not emit; no missing signal was fabricated. `I(IB|XBQ1)` is
  present.
- Raw hashes before/after analysis: unchanged for all five runs.
- Deck diff QA: PASS; every intervention differs from `NOMINAL` by exactly
  its one registered `.param` line.
- Independent raw arithmetic: PASS; see [independent_check.json](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/independent_check.json).
- Visualization: standalone QA PASS before comparison; final QA PASS for 40
  visualization entries.

## OBSERVED

- In the L1 family, `I(L1|XBQ1)` remains negative through `FULL_FINAL` for
  all three values; no stored-sample negative-to-nonnegative bracket occurs.
- `FULL_READ` maximum BJ1 relative progression is 0.194062238 turns
  (`L1_DOWN`), 0.188484175 (`NOMINAL`) and 0.183404745 (`L1_UP`). The raw
  phase is radians; turns are only the independent unwrap divided by `2*pi`.
- In the RJ1 family, maximum BJ1 progression is 0.188484175, 0.189896198 and
  0.191231985 turns for 12.0, 12.5 and 13.0 ohm. The maximum occurs at the
  same 120.9 ps stored sample in all three runs.
- Positive `V(BJ1)` duration in `FULL_READ` is 8.4, 8.5 and 8.4 ps for
  RJ1=12.0, 12.5 and 13.0 ohm; it is not monotonic.

### L1 family (`FULL_READ`)

| run | L1 (pH) | I(L1)@110 (uA) | max I(L1) (uA) | max BJ1 progression (turns) | max I(L2) (uA) |
|---|---:|---:|---:|---:|---:|
| L1_DOWN | 1.9 | -90.549510 | -17.928370 | 0.194062238 | 232.071600 |
| NOMINAL | 2.0 | -90.052980 | -20.599240 | 0.188484175 | 229.400800 |
| L1_UP | 2.1 | -89.541980 | -22.963580 | 0.183404745 | 227.036400 |

### RJ1 family (`FULL_READ`)

| run | RJ1 (ohm) | max BJ1 progression (turns) | time of max (ps) | max V(BJ1) (mV) | +V duration (ps) |
|---|---:|---:|---:|---:|---:|
| NOMINAL | 12.0 | 0.188484175 | 120.9 | 0.1227016 | 8.4 |
| RJ1_UP_05 | 12.5 | 0.189896198 | 120.9 | 0.1242360 | 8.5 |
| RJ1_UP_10 | 13.0 | 0.191231985 | 120.9 | 0.1256916 | 8.4 |

## DERIVED

- For the L1 family, `FULL_READ` maximum `I(L1)` is -17.928370, -20.599240
  and -22.963580 uA for 1.9, 2.0 and 2.1 pH; corresponding maximum `I(L2)`
  is 232.071600, 229.400800 and 227.036400 uA.
- `EARLY_TRIGGER` `W_QBIN` is 5.6184005, 5.5830098 and 5.5494725 zJ for
  `L1_DOWN`, `NOMINAL` and `L1_UP`. It is a derived port-work diagnostic,
  not a trigger-energy threshold.
- `I(L2)-I(IB)-I(L1)` maximum absolute residual is about 5.0e-11 A in
  `FULL_READ`; BJ1 same-JJ phase/voltage-area residual is about -3.0e-4
  turns. These are arithmetic diagnostics, not acceptance Gates.
- Source-side `I_quiet_total`, `V(COMMON_SL)`, JSL currents and `V(QBIN)`
  vary with the registered local interventions; exact values are preserved in
  [metrics.json](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/metrics.json).

## BOUNDED_RESULT

Under this fixed historical fixture, L1 decrease is associated with a larger
BJ1 relative progression and a less-negative `I(L1)` maximum, but it does not
produce a nonnegative `I(L1)` crossing. RJ1 increase changes BJ1 magnitude
metrics, while the registered duration and maximum-time diagnostics do not
show a consistent persistence ordering. Source/interface tracks co-vary with
the local QB changes, but the data do not isolate a source-side mechanism or
provide a current fraction.

These statements are bounded to the registered topology, stimulus, parameters,
solver, 0.1 ps timestep and windows. They do not establish a complete trigger,
an SFQ count or a system-level transmission result.

## UNKNOWN

- Timestep/solver convergence and sensitivity outside the exact five-run
  matrix.
- Mechanistic interpretation of the BJ1/L1/RJ1 trajectory or quiet-cell
  response.
- SFQ event count, exactly-one transmission, system Gate status and hardware
  behavior.
- Any optimum or parameter recommendation.

## Evidence links

- [Raw QA](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/raw_qa.json) · [deck diff QA](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/deck_diff_qa.json) · [execution summary](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/execution_summary.json) · [provenance](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/provenance.json)
- [Interpretations](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/interpretations.json) · [numerical/adversarial review](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/REVIEW.md) · [transformation registry](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/transformation_registry.json)
- Standalone run pages: [NOMINAL](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/standalone/nominal/) · [L1_DOWN](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/standalone/l1_down/) · [L1_UP](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/standalone/l1_up/) · [RJ1_UP_05](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/standalone/rj1_up_05/) · [RJ1_UP_10](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/standalone/rj1_up_10/)
- Critical zooms: [NOMINAL 110--116 ps](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/zoom/nominal/110_116ps.html) · [NOMINAL 110--121 ps](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/zoom/nominal/110_121ps.html)
- Family comparisons: [L1 family](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/compare_l1/L1_FAMILY.html) · [RJ1 family](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/compare_rj1/RJ1_FAMILY.html)
- Mechanism views: [BJ1 phase-plane L1](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/mechanism/BJ1_PHASE_PLANE_L1.html) · [BJ1 phase-plane RJ1](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/mechanism/BJ1_PHASE_PLANE_RJ1.html) · [source decomposition 110--116 ps](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/mechanism/ARRAY_SOURCE_DECOMPOSITION_110_116ps.html)

Final status: `AWAITING_USER_REVIEW`.
