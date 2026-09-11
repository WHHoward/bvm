# Evidence handoff — closed-boundary current replay

Scientific interpretation is `NOT_PERFORMED`.

This experiment contains the Stage A N2 calibration replay only. It uses the
immutable current RJ2=12 `0011` closed-loop raw and replays its exact stored
`I(B_JSL8)` samples as `I_REPLAY 0 QBIN` into the isolated canonical receiver.
The closed-loop source raw is a reference and was not rerun.

Stage B N3 is recorded as deferred. It requires both a Stage A scientific pass
and the explicit `SCIENTIFIC_REVIEW_AUTHORIZED` token; no N3 source or N3
solver artifact is created in this turn.

Raw CSVs, decks, logs, metadata, exact-fidelity QA, raw navigation, plots and
the immutable source reference are the review inputs. The replay is ideal
current forcing, not a Thevenin/Norton or circuit-equivalent source.

Final state: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
