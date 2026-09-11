# BVM QB L3/BJ2 targeted combination

This is a preregistered, bounded full closed-loop experiment. The target is
`L3=2.0 pH + BJ2 area=2.2`; only masks `0011` and `0111` are screening solves.
Three pairs of existing raw files are immutable references: canonical
`L3=1.3/BJ2=2.0`, L3-only `L3=2.0/BJ2=2.0`, and BJ2-only
`L3=1.3/BJ2=2.2`.

No phase landmark, voltage area, terminal area, threshold activity or current
peak is an SFQ count. Scientific interpretation is NOT PERFORMED before an
explicit scientific review; unauthorized follow-up is none.

## Final evidence-only outcome

- Two new full closed-loop physical solves completed at exactly `L3=2.0 pH +
  BJ2 area=2.2`: `0011` and `0111`. The three comparison pairs were reused
  byte-for-byte and were not rerun.
- OBSERVED: both new cases were CLEAN in the registered 70–110 ps history
  windows. The `0011` case produced one complete ordered response candidate
  (`N2_NOT_2`). The `0111` case produced four raw candidates with ordered
  vector `{1:true, 2:true, 3:false, 4:true}`; its strict classification is
  `N3_MULTIPLICITY_AMBIGUOUS`, not a complete 1/4 chain.
- OBSERVED: for the target `0111` case, the fourth navigation landmarks were
  BJ1 `122.9 ps`, BJ2 `126.5 ps`, JTL1 `128.0 ps`, JTL6 `144.8 ps`, and
  terminal `146.6 ps`; BJ1→BJ2 handoff latency was `3.6 ps`. These are phase
  navigation/arrival diagnostics, not SFQ counts.
- OBSERVED: the target differential reset integrals were
  `+2.4932e-16 V s` (118–121 ps), `-3.7179e-16 V s` (121–124 ps), and
  `-2.9966e-16 V s` (124–128 ps), computed on the actual stored grid. The
  target `I(L1)` maximum/minimum in 121–130 ps were `+288.7284 µA` and
  `-185.0674 µA`; its first zero/sign-change diagnostic was `121.4 ps`.
- OBSERVED: target `I(B_JSL8)` signed areas were `3.9046e-17 A s`
  (110–112 ps), `9.6450e-16 A s` (110–121 ps), `2.6378e-16 A s`
  (121–124 ps), and `2.3289e-16 A s` (121–126 ps); maximum positive current
  was `237.4574 µA`, with the first positive-to-negative crossing at
  `123.8 ps`.
- OBSERVED comparison of the registered raw pairs:

  | condition | N2 candidate/class | N3 candidate/class | N2 BJ1_2 | N3 BJ1_4 | N3 BJ2_4 | BJ1→BJ2 #4 | N3 JTL6_4 | N3 terminal_4 |
  |---|---|---|---:|---:|---:|---:|---:|---:|
  | canonical L3=1.3, BJ2=2.0 | 2 / N2_2_COMPLETE | 4 / N3_4_COMPLETE | 125.9 ps | 124.2 ps | 124.8 ps | 0.6 ps | 143.8 ps | 145.6 ps |
  | L3-only L3=2.0, BJ2=2.0 | 2 / N2_2_COMPLETE | 4 / N3_MULTIPLICITY_AMBIGUOUS | 123.0 ps | 122.7 ps | 124.7 ps | 2.0 ps | 143.9 ps | 145.8 ps |
  | BJ2-only L3=1.3, BJ2=2.2 | 1 / N2_NOT_2 | 4 / N3_4_COMPLETE | — | 125.1 ps | 126.1 ps | 1.0 ps | 144.3 ps | 146.1 ps |
  | target L3=2.0, BJ2=2.2 | 1 / N2_NOT_2 | 4 / N3_MULTIPLICITY_AMBIGUOUS | — | 122.9 ps | 126.5 ps | 3.6 ps | 144.8 ps | 146.6 ps |

  Times in this table are phase-navigation or arrival diagnostics; they are
  not SFQ counts. The target N3 order vector is `{1:true,2:true,3:false,4:true}`.
- OBSERVED source-feedback comparison for `I(B_JSL8)` (actual-grid signed
  areas in A s; maximum current in µA):

  | condition | 110–112 | 110–121 | 121–124 | 121–126 | max positive | first +→− |
  |---|---:|---:|---:|---:|---:|---:|
  | canonical | 3.8176e-17 | 9.5057e-16 | 2.6517e-16 | 1.8701e-16 | 220.2255 | 123.8 ps |
  | L3-only | 3.7975e-17 | 9.3916e-16 | 2.4903e-16 | 1.8428e-16 | 242.2992 | 123.6 ps |
  | BJ2-only | 3.9096e-17 | 9.7185e-16 | 2.8453e-16 | 2.3058e-16 | 208.0719 | 123.9 ps |
  | target | 3.9046e-17 | 9.6450e-16 | 2.6378e-16 | 2.3289e-16 | 237.4574 | 123.8 ps |
- DERIVED: using the registered response-authority and outcome mapping, the
  result is `D / N3_FOURTH_HANDOFF_BOUNDARY_CASE`. Conditional `0001/1111`
  validation was not run because a clean ordered 2/3 screening pair was not
  observed.
- UNKNOWN: timestep convergence, behavior outside this single combination,
  full-population response beyond the registered screening pair, hardware
  equivalence, and any mechanism beyond these bounded observations.

QA status: raw/deck QA PASS, independent raw reread PASS, visualization QA
PASS. Scientific interpretation remains NOT PERFORMED; status is
`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
