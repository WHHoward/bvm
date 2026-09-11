# L3 high-side selective-window search

This is a bounded full closed-loop L3 search. Read PREFLIGHT.md,
screening/L3_TABLE.md, screening/L3_RESULTS.md, QA and raw evidence before
using a classification. The only new L3 values are 1.8 pH and conditionally
2.0 pH; L3=1.6 pH is immutable reference.

No phase landmark, voltage area, terminal area, threshold activity or current
peak is an SFQ count. No extra L3 value, N1/N4 validation, third parameter or
timestep refinement starts automatically.

## Final evidence-only outcome

- Four new full closed-loop physical solves completed: H1 L3=1.8 pH and H2
  L3=2.0 pH, each with masks 0011 and 0111. The immutable L3=1.6 pH
  reference was not rerun.
- OBSERVED: both H1 and H2 were history/control CLEAN. Their 0011 runs had
  N2=2 complete response candidates. Their 0111 runs had four raw response
  candidates, but strict full-chain ordering was ambiguous for candidates 3
  and 4; the same ordering ambiguity is present in the immutable L3=1.6
  reference.
- OBSERVED: the registered fourth-response diagnostics showed no meaningful
  high-side weakening: terminal fourth-response area ratios were 0.999337
  (H1) and 0.998450 (H2), with JTL6 fourth-response delays of 0.1 ps in both
  cases. These areas and delays are diagnostics, not SFQ counts.
- DERIVED: under the registered screening mapping, both points are class B,
  `STILL_2_TO_4` (with the N3 multiplicity/order caveat above). The bounded
  stopping state is `L3_HIGHSIDE_NO_SELECTIVE_WINDOW_IN_TESTED_RANGE`.
- UNKNOWN: behavior outside L3=1.6, 1.8 and 2.0 pH, full-population masks,
  timestep sensitivity, and whether a continuous selective interval exists.
- No N1/N4 validation, third-parameter solve, replay, source modification,
  JTL modification or timestep refinement was run. Scientific review remains
  pending.
