# Tooling incident ANALYSIS-01

- First analysis run: `2026-09-07T13:20:05+08:00`
- Findings: the initial QA treated the solver's final stored sample at `199.9 ps` as a failure against `.tran ... 200p`, and required `V(IB|XBQ1)` even though JoSIM did not emit a voltage column for the current-source branch.
- Physical execution: both registered solver runs had already passed; no raw, deck, model, timing, topology, or parameter was changed.
- Correction: accept the documented solver output convention when the final sample is within one nominal output interval of the registered stop time, and classify `V(IB|XBQ1)` as an unsupported optional branch-voltage probe while retaining `I(IB|XBQ1)`.
- Preservation: the first failed QA JSON is retained under `analysis/attempts/ANALYSIS-01/`.
