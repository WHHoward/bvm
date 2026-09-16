# Numerical review — mechanical only

Scientific interpretation is not performed in this artifact.

- Exact fidelity status: `PASS`.
- Independent fresh-CSV grid check: `True`.
- Independent ordered-navigation counts: `{"CANONICAL_0011": 2, "CANONICAL_0111": 4, "EXACT_0011": 2, "EXACT_0111": 4, "DELAY0P3_0011": 2, "DELAY0P3_0111": 4, "DELAY0P6_0011": 2, "DELAY0P6_0111": 4}`.
- P(...) remains raw radians; turns use independent unwrap/(2*pi).
- Phase-area checks use the same JJ, endpoints, direction, half-open window, and actual-grid trapezoid.
- No timestep convergence or solver sensitivity was authorized: UNKNOWN.
