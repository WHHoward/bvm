# BVM two-parameter full closed-loop combination

This experiment tests only the nine registered two-parameter combinations in
`screening/COMBINATION_MATRIX.json`. Every new case is a physical
`BVM1..4 -> COMMON_SL/JSL -> QB -> six-stage JTL -> R_TERM` solve with the
stored 100 uA history and `.tran 0.1p 200p`; replay, passive capture, source
scaling, JTL changes and timestep changes are excluded.

The corrected CONTROL/history rule looks for an unintended complete downstream
chain only in the registered 70–110 ps history windows. Final-read/tail phase
rollback is retained as a separate diagnostic and cannot contaminate CONTROL.
P(...) is raw radians; `rad/(2*pi)` is navigation/display only, never an SFQ
count. The final state is `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
