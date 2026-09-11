# BVM full closed-loop QB parameter screening

Scientific interpretation is bounded to the registered screening matrix and
the raw evidence in this directory.

This experiment changes one QB parameter at a time in the full physical
`BVM -> COMMON_SL/JSL -> QB -> six-stage JTL -> terminal` topology. It does not
use replay, passive-ground capture, JTL optimization or timestep refinement.

The maximum first-stage matrix is 37 non-baseline parameter points × two masks
(`0011`, `0111`) = 74 logical cases. Existing strictly equivalent RJ2=10,
RJ2=11 and RJ2=12 cases are archived as reuse/context references and are not
counted as new physical solves. If a raw-supported S candidate is found, broad
screening stops and only the registered 0001/1111 validation solves may follow.

Read `PREFLIGHT.md`, `screening/SCREENING_MATRIX.json`, `qa/execution_summary.json`,
`screening/SCREENING_TABLE.md`, the raw QA and independent review before using a
candidate label. Phase navigation, voltage area, terminal area, current
thresholds and activity segments are not SFQ counts.

Final state: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
