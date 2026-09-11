# QB threshold-ordering boundary search

This is a bounded four-solve full closed-loop experiment at fixed L3=1.6 pH.
Read PREFLIGHT.md, boundary/BOUNDARY_TABLE.md, boundary/BOUNDARY_RESULTS.md,
QA and raw evidence before using the midpoint outcome.

The only new cases are L2=1.8 pH and IBias=250 uA, each with masks 0011 and
0111. Existing low/high endpoint raw is copied byte-for-byte as context. No
N1/N4 validation, extra midpoint, third parameter or timestep refinement is
automatic. Phase, voltage area, terminal area and peak activity are not SFQ
counts.
