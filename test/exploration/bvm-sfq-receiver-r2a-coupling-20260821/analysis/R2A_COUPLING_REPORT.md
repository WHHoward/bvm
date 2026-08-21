# R2-A receiver input-flux transfer diagnostic

## Verdict

`R2-A FAIL` for the bounded mutual-coupling matrix as a complete B_OUT
activation experiment.  Increasing `K` produces a clear, monotonic,
state-dependent increase in secondary voltage/current and in B_OUT phase
activity, but the largest read1 B_OUT segment at `K=0.95` is only
`0.026122419` turn with same-segment voltage area `0.026133408` turn.  No
tested point reaches the preregistered complete-transition criterion of one
turn plus same-JJ voltage-area consistency.

This is a bounded local receiver result.  It is not a claim that all larger
coupling values, other damping values, or other receiver topologies are
impossible.  A local B_OUT phase response is not called downstream SFQ
delivery; this fixture has no JTL.

## Frozen configuration

Only `K_TX` changed:

| Parameter | Frozen value |
|---|---:|
| canonical BVM | unchanged |
| route | canonical SL |
| `R_IN` | 12 ohm |
| `L_TX` | 0.20 pH |
| `L_SEC` | 2.0 pH |
| `R_SEC_LOAD` | 12 ohm |
| B_TRIG AREA / bias | 0.50 / 15 uA |
| B_OUT AREA / bias | 0.10 / 7 uA |
| `R_OUT_DAMP` | 100 ohm |
| requested timestep / stop | 0.0125 ps / 170 ps |

The actual AREA-scaled B_OUT model is `Ic=10 uA`, `RN=160 ohm`,
`R0=1600 ohm`, and `C=7 fF`.  The mutual inductance values are derived from
`M=K*sqrt(L_TX*L_SEC)` and are recorded in the manifest.

## K matrix and B_OUT results

`B_OUT phase` is the largest absolute monotonic segment
`abs(delta(phi))/(2*pi)` in the declared output window.  `V-area` is the
signed integral of the same direct `V(B_OUT|XTRIG)` segment divided by
`Phi0`.  Current and voltage peaks are activity diagnostics only.

| K | M (pH) | read1 B_OUT phase (turns) | read1 V-area (turns) | read0 B_OUT phase (turns) | read0 V-area (turns) | read1 complete | read0 complete |
|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 0.60 | 0.3794733 | 0.016588561 | +0.016595577 | 0.003871826 | +0.003873546 | no | no |
| 0.70 | 0.4427189 | 0.019329638 | +0.019337804 | 0.004516117 | +0.004518137 | no | no |
| 0.80 | 0.5059644 | 0.022058350 | +0.022067654 | 0.005159931 | +0.005162242 | no | no |
| 0.90 | 0.5692099 | 0.024772069 | +0.024782509 | 0.005803187 | +0.005805790 | no | no |
| 0.95 | 0.6008327 | 0.026122419 | +0.026133408 | 0.006124585 | +0.006127323 | no | no |

The K=0.80 raw matrix is byte-identical to the corresponding R1c 7-uA
baseline raw matrix, providing a direct no-op/reproduction check for the
parameterized R2-A runner.

## Transfer and guards

- Read1 secondary voltage activity rises from 56.569 uV at `K=0.60` to
  88.732 uV at `K=0.95`; secondary return-current activity rises from 1.578
  uA to 2.482 uA.
- Read0 secondary voltage rises from 9.808 uV to 15.407 uV and remains well
  below read1.  The read1/read0 secondary-voltage ratio stays approximately
  5.759–5.768; the return-current ratio stays approximately 3.355–3.407.
- B_TRIG remains guarded: read1 largest phase activity is 3.915127–3.918462
  turns, while read0 is 0.184871–0.184892 turn.  The small K-dependent change
  is bounded loading/back-action, not loss of the R0 trigger separation.
- Loaded source signals remain state-dependent.  Read1 SL activity is about
  1.881–1.884 mV versus about 0.442 mV in magnitude for read0; N6 is about
  2.117–2.118 mV versus about 0.721 mV in magnitude.
- READ=0 controls have no complete B_OUT transition and no free-running phase.
  The largest control phase range is 0.004307 turn.
- JM1/JM2 storage signs remain logical-state distinct at all K points.  Read1
  post medians remain near `JM1=+5.915 rad`, `JM2=+0.314 rad`; read0 remains
  near `JM1=-5.911 rad`, `JM2=-0.321 rad`.

For activity context only, read1 `abs(V(B_OUT))` rises from about 56.6 to
88.7 uV and `abs(I(B_OUT))` from about 7.94 to 8.46 uA.  These peaks are not
used to declare switching.

## Artifact and numerical QA

- 5 K points × 4 matched cases = 20 new raw CSVs.
- Every CSV has 13,599 samples from 0 to 169.9875 ps.
- Actual CSV intervals are 0.01249999999996021–0.025000000000000133 ps.
- All required phase, direct same-JJ voltage, current, secondary, source,
  storage, and readout columns are present and finite.
- Solver stderr is empty for all runs.
- Primary analysis and an independent raw-CSV cross-check both pass for all
  20 cases.
- No time-step convergence matrix was run; this remains an Exploration
  limitation and no convergence claim is made.

## Physical interpretation

### Observed

- Increasing K from 0.60 to 0.95 increases read1 secondary voltage by about
  57% and read1 B_OUT phase activity by about 57.5%.
- The increase is state-dependent and preserves read1/read0 secondary
  separation.
- Despite the increased transfer, read1 B_OUT remains sub-turn at every K;
  read0 and controls remain sub-turn.

### Derived

- The complete read1/read0 bias-window set for this K matrix is empty.
- The read1 B_OUT response changes from 0.01659 to 0.02612 turn, not from
  approximately 0.02 turn toward one turn.
- Same-JJ phase and voltage-area values agree for each reported sub-turn
  segment; this validates the local activity calculation, not a switching
  event.

### Inference

- **Case A / H1:** increased mutual coupling does improve effective input
  transfer and therefore contributes to B_OUT activation.  However, the
  tested K increase is insufficient to close the one-turn gap.
- **Case B / H2:** the result is more consistent with a receiver-limited
  dynamic bottleneck, or with an input threshold outside the bounded K range,
  than with a simple lack of any transformer signal.  The experiment does not
  isolate damping from a still-insufficient effective drive; it only shows
  that increasing K alone does not solve activation here.

### Unknown

- Whether a K value closer to unity would ever produce a complete transition
  is not established, and no extrapolation beyond K=0.95 is made.
- Whether changing `R_OUT_DAMP` or another receiver dynamic parameter would
  convert the enhanced transient into a complete transition is not tested.
- No statement is made about exactly-one behavior, self-quenching, JTL
  reception, or hardware operation.

## Next-step recommendation

Do not perform further K sweep or topology redesign from this result.  If a
new diagnostic is authorized, the smallest discriminating follow-up is to
hold `K=0.95` and the full R2-A baseline fixed, then vary only the local
B_OUT damping/receiver dynamic parameter in a separately preregistered small
matrix.  That would test H2 directly after the maximum tested transfer has
already been established.  No such follow-up is implemented here.
