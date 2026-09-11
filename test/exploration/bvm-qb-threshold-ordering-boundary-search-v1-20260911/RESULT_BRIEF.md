# QB threshold-ordering boundary search

This is a bounded four-solve full closed-loop experiment at fixed L3=1.6 pH.
Read PREFLIGHT.md, boundary/BOUNDARY_TABLE.md, boundary/BOUNDARY_RESULTS.md,
QA and raw evidence before using the midpoint outcome.

The only new cases are L2=1.8 pH and IBias=250 uA, each with masks 0011 and
0111. Existing low/high endpoint raw is copied byte-for-byte as context. No
N1/N4 validation, extra midpoint, third parameter or timestep refinement is
automatic. Phase, voltage area, terminal area and peak activity are not SFQ
counts.

## Final evidence-only outcome

- Four new full closed-loop physical solves completed: Stage A L2=1.8 pH and
  Stage B IBias=250 uA, each with masks 0011 and 0111.
- OBSERVED: both midpoints were history/control CLEAN; both produced N2=1
  complete-response candidate and N3=4 complete-response candidates under the
  registered multi-stream navigation rule.
- DERIVED: both axes are classified as
  UNFAVORABLE_THRESHOLD_ORDERING at the tested midpoint, with no direct 2/3
  point. This is only a bounded three-point ordering statement, not an exact
  continuous threshold.
- UNKNOWN: whether a 2/3 interval exists between the registered endpoint and
  midpoint; no additional midpoint was authorized.
- No N1/N4 validation, third-parameter solve or timestep refinement was run.
