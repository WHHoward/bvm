# R1c B_OUT receiver bias margin diagnostic

## Verdict

`R1c FAIL` for the bounded bias matrix.  The frozen AREA=0.10 differential
receiver produced a state-dependent B_OUT transient at every operating point,
but no read1 B_OUT segment reached one complete turn.  Therefore no tested
bias point satisfies the required read1-complete/read0-incomplete window.

This is a local receiver-JJ result only.  No B_OUT phase excursion is called
downstream SFQ delivery; there is no JTL in this Exploration.

## Scope and frozen topology

Only `I_OUT_BIAS` was changed.  The canonical BVM, SL route, transformer,
secondary connection, B_OUT AREA, JJ model, damping, probes, time window, and
matched cases were held fixed.  The receiver is:

```text
SL -> R_IN=12 ohm -> L_TX=0.20 pH -> B_TRIG(area=0.50, bias=15 uA)
                                      |
                         K=0.80       L_SEC=2 pH -> R_SEC_LOAD=12 ohm -> ground
                                      |
                                  N_SEC -> B_OUT(area=0.10) -> ground
                                  N_SEC <- I_OUT_BIAS
                                  N_SEC -> R_OUT_DAMP=100 ohm -> ground
```

For currents defined positive from `N_SEC` to ground, the receiver-node KCL
is `i_BOUT = I_OUT_BIAS - i_LSEC - i_R_DAMP`.  Thus the secondary current
contribution is present at the differential B_OUT node.  The B_OUT model at
AREA=0.10 has `Ic=10 uA`, `RN=160 ohm`, `R0=1600 ohm`, and `C=7 fF` under the
actual JoSIM AREA semantics.  The intrinsic `beta_c` is approximately 5.445;
the 100-ohm shunt diagnostic is approximately 0.805.  These are model
diagnostics, not event criteria.

Bias points were 6, 7, 8, 9, and 10 uA, corresponding to 0.60, 0.70, 0.80,
0.90, and 1.00 of the nominal AREA-scaled `Ic`.  Each point used the same
four cases: canonical logical1 +READ, canonical logical0 +READ, logical1
READ=0 control, and logical0 READ=0 control.

## Raw and numerical QA

- 20 raw CSVs were generated without overwriting existing artifacts.
- Each CSV has 13,599 samples from 0 to 169.9875 ps.
- Requested timestep was 0.0125 ps; observed CSV intervals were
  0.01249999999996021 to 0.025000000000000133 ps.
- All CSVs are finite, strictly time-increasing, have the required probes,
  and have empty solver stderr logs.
- The independent raw cross-check passed for all 20 cases.
- No timestep-convergence study was performed in this diagnostic Exploration.

## B_OUT comparison

`B_OUT turn` is the largest absolute monotonic segment phase evolution in the
declared output window.  `V-area` is the signed same-JJ integral
`integral(V(B_OUT) dt)/Phi0` over that same segment.  A complete event requires
at least 1.0 turn plus same-segment area consistency; current and voltage
peaks are not event oracles.

| bias (uA) | read1 B_OUT turn | read1 V-area (turns) | read0 B_OUT turn | read0 V-area (turns) | max control phase range (turns) | read1 complete | read0 complete | controls complete | local SFQ complete? |
|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|:---:|
| 6  | 0.022189621 | +0.022199122 | 0.005173761 | +0.005176064 | 0.003475801 | no | no | no | no |
| 7  | 0.022058350 | +0.022067654 | 0.005159931 | +0.005162242 | 0.003707005 | no | no | no | no |
| 8  | 0.021829708 | +0.021839035 | 0.005133527 | +0.005135823 | 0.004172931 | no | no | no | no |
| 9  | 0.021386445 | +0.021395460 | 0.005238744 | −0.005241000 | 0.007353754 | no | no | no | no |
| 10 | 0.020449819 | −0.020454733 | 0.005441030 | −0.005443058 | 0.039203205 | no | no | no | no |

The signed sub-turn area values are reported for transparency.  At 9 and
10 uA, the small read0 phase/area excursions change sign while remaining far
below one turn; they do not qualify as switching.

The B_OUT activity diagnostics also show why a current-only rule is invalid:
at 10 uA the read1 `abs(I(B_OUT))` peak is about 11.677 uA, above the nominal
10 uA `Ic`, yet the largest same-JJ phase segment is only 0.02045 turn and
its same-segment voltage area is only 0.02045 turn.

## Trigger, transfer, and BVM guards

- `B_TRIG` retained a complete read1 guard at every bias: largest read1
  segment 3.916110–3.916901 turns.  Read0 remained about 0.184869–0.184883
  turn, and both controls had no complete trigger segment.
- The secondary remained state-dependent.  Read1 secondary voltage activity
  was 75.023–75.691 uV versus 13.008–13.281 uV for read0, giving a ratio of
  5.699–5.767.  Secondary return-current activity was 2.043–2.450 uA versus
  0.617–0.714 uA, giving a ratio of 3.310–3.587.
- The loaded canonical source remained discriminating: activity-scale SL was
  approximately 1.882–1.883 mV for read1 versus 0.442 mV in magnitude for
  read0; N6 was approximately 2.118 mV versus 0.721 mV in magnitude over the
  same read activity window.
- JM1/JM2 logical storage signs passed at all points.  Representative read1
  post medians at 7 uA were `JM1=+5.914717 rad`, `JM2=+0.314090 rad`; read0
  was `JM1=-5.911083 rad`, `JM2=-0.321222 rad`.  The small bias-dependent
  drift did not invert the logical signs.
- READ=0 controls showed no complete B_OUT transition and no free-running
  phase.  The 10-uA controls had the largest bounded activity, about 0.0392
  turns in the full control phase-range guard, still far below one turn.

## Interpretation

### Observed

- The 6–10 uA bias matrix is artifact-valid and independently reproducible.
- Increasing B_OUT bias did not produce a read1 complete transition.  Read1
  activity was largest at 6 uA (0.02219 turn) and smallest at 10 uA
  (0.02045 turn); read0 remained sub-turn throughout.
- Secondary transfer, B_TRIG trigger discrimination, SL/N6 response, and
  JM1/JM2 storage signs remained present.

### Derived

- No tested point has a complete B_OUT phase/area-consistent segment.
- The qualifying bias-window set is empty: `[]` uA.
- The observed read1/read0 B_OUT phase-activity ratio is approximately 3.76
  to 4.29 across the matrix, but both states remain non-switching.

### Inference

- **Q1 — Does increasing bias improve read1 activation?** No monotonic
  activation improvement was observed in this bounded matrix.  The read1
  complete-event criterion was not reached at any bias.
- **Q2 — Is there a read1-switch/read0-no-switch bias window?** No such window
  was observed for 6–10 uA under the frozen receiver and model.
- **Q3 — A/B/C diagnosis?** This experiment does not uniquely separate A
  (insufficient effective input energy) from C (loaded dynamic damping).  It
  does not support B as a sufficient simple bias-operating-point remedy: the
  full tested bias interval contains no activation window, and the 10-uA
  current excursion still does not yield a phase/area-consistent event.  The
  bounded result is therefore `A or C`, rather than a static `Ic` threshold
  failure alone.

### Unknown

- This matrix cannot determine whether more transferred flux/energy or a
  different damping condition would complete B_OUT; those would be separate
  variables and were intentionally not changed here.
- No claim is made about bias values outside 6–10 uA, other JJ models, or
  downstream JTL reception.

## Recommendation and disposition

Do not change the receiver topology based on this diagnostic alone.  Keep the
accepted R1a/R1b series-pickup differential route as the reference, mark R1c
as a bounded diagnostic `FAIL`, and do not upgrade to Candidate.  No R1c
topology change, self-quench loop, output JTL, T1, or Candidate activity was
performed.

Raw case directories are under `raw/<point>/<case>/run-01.csv`; the structured
per-point analyses are `analysis/diff-a010-b*-analysis.json`, the independent
cross-checks are `analysis/diff-a010-b*-crosscheck.json`, and the aggregate is
`analysis/bias-summary.json`.
