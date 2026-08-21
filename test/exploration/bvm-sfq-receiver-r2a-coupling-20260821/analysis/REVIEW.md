# R2-A numerical and adversarial review

## Review scope

The strongest bounded claim is: “increasing only transformer K increases the
useful secondary transfer and may activate B_OUT.”  This review tests that
claim against the five preregistered K points and four matched cases per point.
It does not upgrade the result to a route Gate or Candidate.

## Numerical checks

1. `P(B_TRIG|XTRIG)` and `P(B_OUT|XTRIG)` are treated as raw radians and
   continuously unwrapped by adjacent samples inside the declared windows.
   Turns are `delta(phi)/(2*pi)`.
2. `V(B_TRIG|XTRIG)` and `V(B_OUT|XTRIG)` are integrated over the exact same
   monotonic segment endpoints using the CSV `time` column, then divided by
   `Phi0`.  No fixed-step assumption is used.
3. A complete local event requires a monotonic segment with at least 1.0 turn,
   start no later than 130 ps, and same-segment area residual <=0.05 turn.
   No `I_peak > Ic`, voltage peak, or whole-window phase range is used as an
   event oracle.
4. The largest read1 B_OUT result is 0.026122419 turn at K=0.95, with
   same-JJ area 0.026133408 turn.  Both are consistent sub-turn activity,
   not a complete transition.
5. All 20 raw files contain 13,599 rows, finite values, increasing time, and
   the same observed time-step range 0.01249999999996021–0.025000000000000133
   ps.  No convergence claim is made from this single timestep setting.

## Independent evidence

`analysis/independent_crosscheck.py` independently rereads each raw CSV and
recomputes B_TRIG/B_OUT phase segments, same-JJ voltage areas, secondary
activity, and JM1/JM2 pre/post medians.  All 20 cross-checks pass.  Aggregate
guards are:

```text
artifact_valid_all_points                 = True
independent_crosscheck_all_points         = True
btrig_guard_all_points                    = True
storage_sign_guard_all_points             = True
control_free_running_any_point            = False
coupling_window_points                    = []
```

The K=0.80 raw files are byte-identical to the R1c 7-uA baseline raw files.
This is a differential no-op check that the K=0.80 point uses the intended
baseline and that the parameterized runner did not alter the source or
measurement path.

## Adversarial probes

- **No-op / wrong parameter branch:** inspected all five receiver fixtures and
  all case `.include` lines.  Each case includes its matching receiver; each
  receiver has exactly the declared K value and the same 7-uA B_OUT bias.
- **Stale-artifact mixing:** every primary JSON, cross-check JSON, raw path,
  and point ID carries the R2-A K identifier.  No R1 CSV was used as an R2
  raw output; the K=0.80 byte identity is reported only as an explicit
  baseline check.
- **Weak event oracle:** rejected current-only and voltage-only declarations.
  The K=0.95 B_OUT phase/area pair is still 0.026 turn.
- **Common-mode measurement:** rejected for this fixture.  B_OUT is the direct
  `N_SEC -> ground` JJ; its phase, voltage, and current are printed directly.
  Secondary voltage and return current are separately probed.
- **Input disappearance:** rejected within the bounded guard.  B_TRIG remains
  about 3.915–3.918 turns for read1 and about 0.185 turns for read0, while
  source/storage signs remain state-distinct.
- **Control self-running:** rejected.  Neither READ=0 control reaches one
  turn; maximum full-control phase range is 0.004307 turn.
- **Back-action hiding source behavior:** inspected SL/N6 and B_TRIG across K.
  Source amplitudes shift modestly with loading, but the state-dependent
  separation remains and the B_TRIG guard passes.
- **Overclaim:** the report separates the observed monotonic K response from
  the inference that dynamic receiver limitation is more plausible.  It does
  not claim universal impossibility, SFQ delivery, or hardware behavior.

## Fixed-variable audit

AREA, JJ model, B_OUT bias, R_OUT_DAMP, R_IN, L_TX, L_SEC, R_SEC_LOAD, B_TRIG,
canonical BVM, PWL sources, probes, windows, solver binary, timestep, and stop
time are identical across K points.  Only `K_TX` changes.  Existing R1 raw and
accepted artifacts are untouched.

## Disposition

The R2-A artifacts are valid.  The bounded physical result is
`R2A_FAIL_NO_COMPLETE_BOUT_IN_BOUNDED_K_MATRIX`.  K is a real transfer-margin
variable, but increasing it to 0.95 does not close B_OUT activation.  The
remaining dynamic/damping explanation is plausible but not proven by this
K-only experiment.  No topology redesign or Candidate upgrade is justified.
