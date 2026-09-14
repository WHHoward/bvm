# BVM QB L1/L3/BJ2 targeted 4x1 closure

This is a preregistered, bounded full physical closed-loop experiment. The
target changes exactly three QB parameters from canonical: `L1=1.2 pH`,
`L3=2.0 pH`, and `BJ2 area=2.2`. Only masks `0011` and `0111` are authorized
new solves. Canonical, L1-only, and L3/BJ2 barrier raw pairs are immutable
references.

No phase landmark, voltage area, terminal area, threshold activity or current
peak is an SFQ count. Scientific interpretation is NOT PERFORMED; no third
solve or validation is authorized without explicit scientific review.

## Final evidence-only outcome

- Two new full physical closed-loop solves completed at exactly
  `L1=1.2 pH + L3=2.0 pH + BJ2 area=2.2`: `0011` (T01) and `0111` (T02).
  No third solve, validation mask, parameter sweep or timestep refinement was
  run.
- OBSERVED T01: history/control was CLEAN; the raw response candidate count was
  1 with ordered vector `{1:true}`. The second response was not supported, so
  0011 did not reach N2=2. In post-read 121–200 ps, `I(L1)` had maximum
  `-14.5953 µA`, minimum `-101.9767 µA`, no sustained negative→positive
  crossing, and zero positive dwell under the registered diagnostic.
- OBSERVED T02: history/control was CLEAN; the raw candidate count was 4 with
  ordered vector `{1:true,2:true,3:false,4:true}`. The fourth navigation
  landmarks were BJ1 `122.9 ps`, BJ2 `126.3 ps`, JTL1 `127.8 ps`, JTL6
  `144.6 ps`, and terminal `146.4 ps`; BJ1→BJ2 latency was `3.4 ps`. Because
  response 3 is not ordered, this is not a complete N3=4 chain.
- OBSERVED T02 differential reset integrals, using the actual stored grid, were
  `+1.9045e-16 V s` (118–121 ps), `-3.8516e-16 V s` (121–124 ps),
  `-9.4797e-17 V s` (124–128 ps), and `-2.9903e-16 V s` (128–132 ps).
  The 121–130 ps `I(L1)` maximum/minimum were `+306.7923 µA` and
  `-188.8954 µA`; the first sign-change diagnostic was `121.4 ps`.
- OBSERVED target `I(B_JSL8)` signed areas were `3.9049e-17 A s`
  (110–112 ps), `9.5991e-16 A s` (110–121 ps), `2.6363e-16 A s`
  (121–124 ps), and `2.3539e-16 A s` (121–126 ps). Maximum positive current
  was `243.193 µA`, with the first positive→negative crossing at `123.8 ps`.
- OBSERVED registered reference comparison:

  | condition | N2 | N3 raw candidates/order | BJ1_4 | BJ2_4 | BJ1→BJ2 #4 | JTL6_4 | terminal_4 |
  |---|---|---|---:|---:|---:|---:|---:|
  | R0 canonical `L1=1.4,L3=1.3,BJ2=2.0` | 2 | 4 / all ordered | 124.2 ps | 124.8 ps | 0.6 ps | 143.8 ps | 145.6 ps |
  | R1 L1 rescue `L1=1.2,L3=1.3,BJ2=2.0` | 2 | 4 / all ordered | 124.3 ps | 124.8 ps | 0.5 ps | 143.8 ps | 145.6 ps |
  | R2 barrier `L1=1.4,L3=2.0,BJ2=2.2` | 1 | 4 / `{1:true,2:true,3:false,4:true}` | 122.9 ps | 126.5 ps | 3.6 ps | 144.8 ps | 146.6 ps |
  | target `L1=1.2,L3=2.0,BJ2=2.2` | 1 | 4 / `{1:true,2:true,3:false,4:true}` | 122.9 ps | 126.3 ps | 3.4 ps | 144.6 ps | 146.4 ps |

  All phase values in this table are navigation diagnostics; they are not SFQ
  counts. The full raw-derived comparison, including `I(L1)`, `I(L2)`,
  `I(L3)`, reset integrals and source feedback, is in the machine-readable
  result artifact.
- DERIVED: the registered result is
  `N3_FOURTH_HANDOFF_BOUNDARY_CASE`. A clean 2/3 candidate was not observed,
  so the reserved `0001/1111` validation gate remains untouched.
- UNKNOWN: timestep convergence, parameter sensitivity, behavior outside this
  single triple point, full-population closure, hardware equivalence, and any
  mechanism beyond the recorded bounded observations.

QA status: raw/deck QA PASS, independent raw reread PASS, V2.1 visualization
QA PASS. Scientific interpretation remains NOT PERFORMED; final state is
`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
