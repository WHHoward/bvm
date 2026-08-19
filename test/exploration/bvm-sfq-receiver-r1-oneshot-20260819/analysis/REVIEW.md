# R1 numerical and adversarial review

## Disposition

The artifact set is internally valid for this Exploration, but the scientific
R1 one-shot criterion is **FAIL** because read1 has zero complete output units.
The negative controls are not used to upgrade that result.

## Numerical checks

1. `P(B_TRIG|XTRIG)` and `P(B_OUT|XTRIG)` are consumed as raw radians. The
   analysis adds continuous adjacent-sample unwrapped columns without changing
   the CSV.
2. Phase turns use `delta_rad/(2*pi)`. Voltage areas use the actual CSV `time`
   values in seconds and the same phase-segment endpoints and direction.
3. Segment-level residuals are reported. The largest non-complete B_TRIG
   segments have phase/area agreement at roughly 1e-4 turns or better; this
   validates the integration bookkeeping but is not a switching criterion.
4. A monotonic segment is counted in complete units, not as one event merely
   because it is long. This prevents the prior R0b-style multi-turn trigger
   from being mislabelled as one-shot output.
5. All 16 files have 15,999 intervals, strictly increasing time, finite
   numeric fields, and actual spacing 0.0125–0.025 ps. Requested dt is
   preserved in each input netlist. No timestep-convergence claim is made.
6. The independent raw re-read reports
   `all_comparisons_pass=True`, with SHA, trigger-unit, and output-unit
   comparisons passing for all 16 cases.

## Adversarial checks

1. **Missing output probe:** the CSV header contains the direct B_OUT phase,
   voltage, current, feedback currents, output-loop currents, SL/N6, JM1/JM2,
   JS1/JS2, and BVM/source probes required by the preregistration.
2. **Static-bias false positive:** B_OUT is biased at 35 uA against a 50 uA Ic.
   Its direct P/V trajectory stays static; the tiny `4.77464829e-8`-turn
   startup segment is explicitly not counted.
3. **Voltage-peak shortcut:** no output voltage peak is called an event. The
   read1 output voltage remains numerical-zero scale and has no complete
   phase segment or same-segment one-turn area.
4. **Trigger/output conflation:** B_TRIG sub-turn activity is reported
   separately. No B_TRIG turn is counted as output delivery.
5. **Control leakage:** both logical READ=0 controls use the same receiver and
   output bias, and both have zero complete output units over the full window.
6. **Startup/free-running:** output counting begins at 20 ps, while the
   read-trigger requirement additionally requires a qualifying segment to
   start in 94–140 ps. POST is checked independently through 200 ps.
7. **Receiver loading:** SL/N6, receiver input current, storage, and readout
   probes are retained; loaded read1/read0 separation is reported rather than
   silently assuming the R0b baseline survives.
8. **Model semantics:** AREA=0.50 is evaluated with Ic/C multiplication and
   RN/R0 division. The actual beta_c used for the receiver JJ is about 5.445,
   not 0.0544.
9. **Mutual-inductance execution:** simulator stdout contains the
   `Adding Mutual Inductances` marker for the runs. That confirms stamping was
   attempted, not that the coupling produced a useful output pulse.

## Remaining limitation

The failed topology never produces a complete trigger, so the data cannot
distinguish “output transfer is intrinsically too weak” from “trigger never
entered the running state.” A future continuation would need a topology-level
design decision (likely a series-injection/isolated transfer arrangement) before
another one-shot parameter study. This Exploration does not implement that
continuation.
