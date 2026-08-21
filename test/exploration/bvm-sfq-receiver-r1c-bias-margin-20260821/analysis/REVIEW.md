# R1c numerical and adversarial review

## Scope

This review covers the five fixed-topology B_OUT bias points and four matched
cases per point.  It is an Exploration review, not an independent scientific
Gate or Candidate review.

## Numerical checks

1. The primary analysis reads raw CSV timestamps rather than assuming the
   requested timestep.  It integrates `V(B_OUT|XTRIG)` over the exact endpoints
   of the same monotonic `P(B_OUT|XTRIG)` segment and divides by the declared
   `Phi0`.
2. Phase is read as raw radians and unwrapped only by adjacent samples within
   each declared analysis window.  Turns are `delta(phi)/(2*pi)`.
3. The event oracle requires a monotonic segment of at least 1.0 turn, start
   no later than 130 ps, and same-segment voltage-area residual no larger than
   0.05 turn.  A current peak, voltage peak, or whole-window phase range is not
   substituted for this criterion.
4. The largest read1 B_OUT segment is 0.022189621 turn at 6 uA; the smallest
   is 0.020449819 turn at 10 uA.  These are two orders of magnitude below the
   complete-event threshold.  The associated areas track the small phase
   excursions, not a one-flux-quantum area.
5. The 10-uA read1 current peak is about 11.677 uA while the AREA-scaled
   nominal `Ic` is 10 uA.  The phase/area result remains non-complete, so the
   report does not use `I > Ic` as a switching claim.
6. All 20 files have 13,599 rows, finite values, strictly increasing time,
   and actual time intervals from 0.01249999999996021 to 0.025000000000000133
   ps.  No convergence conclusion is drawn from this one requested-timestep
   run.

## Independent cross-check

`analysis/independent_crosscheck.py` re-reads every raw CSV independently,
recomputes adjacent phase unwrapping, monotonic B_TRIG/B_OUT segments,
same-segment voltage areas, secondary amplitudes, and JM1/JM2 pre/post
medians.  All 20 per-case comparisons pass.  The aggregate guard fields are:

```text
artifact_valid_all_points                 = True
independent_crosscheck_all_points         = True
btrig_guard_all_points                    = True
storage_sign_guard_all_points             = True
bias_window_points_uA                     = []
```

## Adversarial checks

- **Hidden current-threshold claim:** rejected.  The 10-uA point exceeds the
  nominal `Ic` in an instantaneous current diagnostic without completing a
  phase/area event.
- **Hidden voltage-spike claim:** rejected.  `V(B_OUT)` peaks are reported as
  activity only and do not establish an event.
- **Whole-window phase-range inflation:** rejected.  The criterion is a
  monotonic segment with same-JJ area, not an aggregate phase range.
- **Read1-only selection:** rejected.  All five points include read1, read0,
  logical1 READ=0, and logical0 READ=0 cases; controls remain non-complete.
- **Common-mode or detached measurement:** rejected for this fixture.  B_OUT
  is directly `N_SEC -> ground`; the analysis probes the same B_OUT JJ phase,
  voltage, and current and separately records secondary voltage/return current.
- **BVM back-action blindness:** checked through B_TRIG, SL/N6, JM1/JM2, and
  readout probes.  B_TRIG remains approximately 3.916-turn read1 versus
  0.185-turn read0, and storage signs remain logical-state distinct.
- **Control free-running:** no control has a complete B_OUT segment; the
  largest full-control B_OUT range is 0.039203205 turn at 10 uA.
- **Stale artifact mixing:** each point's primary JSON, cross-check JSON, and
  raw path contain the point ID; the hash inventory is generated from this
  new directory only and excludes no raw CSV or solver log.

## Fixed-variable audit

The five receiver fixtures differ only in the plateau values of
`I_OUT_BIAS`: 6, 7, 8, 9, and 10 uA.  AREA remains 0.10; `R_IN=12 ohm`,
`L_TX=0.20 pH`, `K=0.80`, `L_SEC=2 pH`, `R_SEC_LOAD=12 ohm`,
`R_OUT_DAMP=100 ohm`, B_TRIG AREA=0.50, B_TRIG bias=15 uA, `jjmit.cir`,
canonical `bvm_cell.cir`, all probes, windows, solver binary, requested
timestep, and stop time are unchanged.  Existing accepted artifacts were not
edited.

## Review disposition

The artifacts are valid for this bounded diagnostic.  The physical result is
`R1c FAIL_NO_COMPLETE_BOUT_IN_BOUNDED_BIAS_MATRIX`, not `INVALID`.  The result
supports a state-dependent but subcritical loaded response and does not by
itself distinguish insufficient effective input energy from damping dynamics.
No topology change is recommended or implemented by this review; no Candidate
upgrade is justified.
