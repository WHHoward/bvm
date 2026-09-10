# RJ2 high-side re-arm boundary search — evidence-only result

Scientific interpretation is `NOT_PERFORMED`.

This experiment holds L1=1.4pH, L2=2.0pH, IBias=260uA, RJ1=32ohm and the
BJS400 ARRAY history fixed. RJ2=6ohm is an exact immutable reuse from the
previous canonical RJ2 experiment; RJ2=8/10/12ohm are the only newly
authorized values, with masks 0001 and 0011.

The evidence records the ZERO_STATE_READ_CONTROL guardrail, separate 0001 and
0011 first-response candidates, first-FINAL-origin BJ2 +0.9 navigation,
stored-sample L1 re-crossing and positive dwell, second-response candidate
evidence, direct voltage/differential areas, source-side support and receiver
diagnostics. All labels remain OBSERVED, DERIVED, BOUNDED_RESULT or UNKNOWN;
none is an SFQ count or a mechanism claim.

If an early-stop condition is observed, the run matrix and stop reason are
preserved in `qa/execution_summary.json`; no later RJ2 value is added.

Final state: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
