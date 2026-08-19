# R1b numerical and adversarial review

## Numerical review

- The recorded solver is `build/josim-cli` v2.7.2837d13 with SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
- All four corrected CSVs contain 13,599 finite rows, strictly increasing
  time, and no missing probe columns.  The requested `.tran` step is 0.0125
  ps.  Actual recorded adjacent intervals are approximately 0.0125--0.025
  ps; phase/area integration used the actual timestamps rather than assuming
  a uniform step.
- `P(B_TRIG|XTRIG)` and `P(B_OUT|XTRIG)` were treated as raw radians.  Phase
  unwrapping used only adjacent samples and turns were computed as delta
  radians divided by `2*pi`.
- The B_TRIG read1 segment is 3.9130310 turns with direct same-segment
  voltage area 3.9130585 turns; residual is 0.0000275 turns.  The read0 and
  control segments are far below one turn.
- B_OUT has no nonzero monotonic segment in any case.  Consequently no
  B_OUT voltage area was manufactured by integrating a broad window, and no
  voltage peak or current threshold was used as a switching event.
- `analysis/independent-crosscheck.py` independently rereads the raw CSVs,
  reconstructs B_TRIG/B_OUT trajectories and areas, and reports
  `all_comparisons_pass=true` for the primary analysis.

## Adversarial review

- Initial raw data was not overwritten.  The initial common-mode failure and
  the corrected loop have separate point IDs and separate CSV directories.
- The output criterion was checked on the output JJ itself, not on
  `V(N_SEC)`, `V(N_OUT)`, `I(B_OUT)`, or a voltage peak.  The observed
  state-dependent `V(N_SEC)` transient therefore cannot create a false output
  PASS.
- READ=0 controls were run with the same receiver and show no B_TRIG or B_OUT
  complete segment and no free-running output phase.
- The B_TRIG guard was checked after output loading and remains complete for
  read1 and incomplete for read0/controls.
- JM1/JM2 were retained.  Logical signs remain distinct, but the read1 JM2
  drift change from the R1a reference is reported as a back-action caveat,
  not silently treated as exact storage preservation.
- No local phase transition was relabeled as an SFQ delivery event.  There is
  no JTL in this fixture.

## Disposition

Artifact validity: PASS.

Physical R1b output-JJ activation criterion: **FAIL** because read1 has no
complete B_OUT transition.  The result is bounded to the two tested fixtures
and does not establish impossibility of another output topology.
