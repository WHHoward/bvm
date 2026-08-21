# R2-B numerical and adversarial review

## Review scope

The strongest bounded claim is: "at the frozen R2-A K=0.95 operating point, weakening only R_OUT_DAMP from 100 to 330 Ω does not unlock complete B_OUT switching; the read1 largest monotonic segment grows only ~11 %." This review tests that claim against the four preregistered points and sixteen matched runs. It does not upgrade the result to a route Gate or Candidate, and it does not certify any next-step design.

## Numerical checks

1. `P(B_OUT|XTRIG)` and `P(B_TRIG|XTRIG)` are consumed as raw radians and continuously unwrapped by adjacent samples inside declared windows; turns are delta(phi)/(2π). No fixed-timestep assumption is used anywhere; voltage areas integrate over actual CSV timestamps.
2. Event oracle is exactly the preregistered one: monotonic unwrapped segment ≥1.0 turn, start ≤130 ps, same-segment direct V(B_OUT|XTRIG) trapezoid area within 0.05 turn. I_peak > Ic, voltage peaks, ringing, and whole-window ranges are recorded as diagnostics only.
3. Largest read1 result is 0.028961 turn at 330 Ω with same-segment area residual +1.3e-05 turn — consistent sub-turn activity, not a transition. No complete_2pi segment exists in any of the 16 runs (checked programmatically: `any_complete_2pi_anywhere=false`).
4. Controls are exactly zero activity at all points (`any_control_activity_above_0.001_turn=false`), so no control artifact can mimic or suppress the effect.
5. All 16 CSVs: 13,599 rows, finite, strictly increasing time, dt range ≈0.0125–0.025 ps, no missing columns. Single timestep setting — no convergence claim made or implied.
6. Determinism check: k095-r100 raw matrix is byte-identical to R2-A k095 for all four cases, verifying the parameterized runner introduced no hidden change at the baseline point.
7. Independent crosscheck recomputes phase/area/completeness/secondary/storage metrics from raw CSVs in a separate implementation: all comparisons pass for all points.

## Adversarial checks

1. **Could the weak response be an analysis artifact?** No: the same pipeline reports 3.9-turn B_TRIG segments in the same runs, so a real multi-turn excursion would be detected. The B_OUT segments are small because the trajectory is small.
2. **Could the damper change have silently altered something else?** Input diffs against the R2-A k095 masters show only the header comment, the include filename, and the single `R_OUT_DAMP` value line. The byte-identical r100 replay bounds hidden changes to zero at baseline.
3. **Is "I(B_OUT) peak < Ic" a safe switching-impossibility argument?** Used only as a diagnostic, not as the event oracle. The verdict rests on the phase/area criterion; the current reading is corroborating. Caveat recorded in Unknown: JoSIM's reported branch-current decomposition vs ideal RCSJ components is not independently verified here.
4. **Could a longer/different window reveal a late transition?** POST window (130–170 ps) was analyzed separately in the per-point JSONs; largest post segments remain sub-turn (no qualifying event). The observed transients are confined to the READ window.
5. **Situation-C risk of hiding near-threshold behavior?** At 330 Ω there is no ringing burst, no free-running, no read0 activity; nothing suggests a threshold was just missed inside the tested range. The claim is bounded to ≤330 Ω.
6. **Guard integrity:** secondary separation ratio stays ~5.8, storage signs preserved in every run, trigger guard intact, source signals unchanged — receiver-side parameter changes did not corrupt BVM state or readout.
7. **Interpretation discipline:** Observed/Derived are separated; the injection-limitation story is labeled Inference (falsifiable), not fact; Unknown lists five explicit gaps including the untested >330 Ω region and single-timestep limitation.

## Disposition

Artifact set valid; preregistered analysis executed as registered; **scientific answer to the preregistered question is negative for H2 within the tested range** (Situation B). This is a useful bounded negative: it redirects attention from output-stage damping to the secondary-to-output injection mechanism, exactly as the manifest's interpretation plan anticipated. No further damping sweep, AREA/bias/C/K sweep, or topology redesign was started without authorization.
