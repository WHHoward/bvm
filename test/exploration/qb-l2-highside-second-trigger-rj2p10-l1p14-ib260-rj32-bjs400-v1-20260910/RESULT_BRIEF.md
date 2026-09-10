# High-L2 second-trigger search — evidence-only result

Scientific interpretation is `NOT_PERFORMED`.

This experiment fixes L1=1.4pH, RJ2=10ohm, IBias=260uA, RJ1=32ohm and the
BJS400 ARRAY stored history. L2=2.0pH is an exact immutable reuse from the
previous canonical RJ2 high-side experiment; L2=2.4/2.8/3.2pH are the only
new physical values.

The mechanical audit identifies the first CONTROL guardrail failure at
L2=2.4pH. The executor's second-complete-candidate stop condition was recorded
later, after L2=2.8pH / 0011; L2=3.2pH was not solved and its registered decks
remain preserved. This ordering is recorded as a protocol-audit deviation,
not silently repaired.

The evidence separates the first positive L1 excursion from later positive
candidates after the first FINAL-origin BJ2 +0.9 navigation anchor. It records
positive dwell, rollback, BJ1 current/phase load-line diagnostics, source and
receiver support, READ-end timing, direct voltage/differential areas and the
full second-chain candidate checks. No L1 crossing, phase turn, voltage area,
terminal area or current ratio is an SFQ count.

If the registered second-complete-response or first-response/control failure
stop condition occurs, the executed matrix and stop reason are preserved in
`qa/execution_summary.json`; no unregistered L2 point is added.

Bounded guardrail outcome: `OUTCOME_C_FIRST_RESPONSE_OR_CONTROL_GUARDRAIL_FAILURE`,
with first control-failure boundary L2=2.4pH. Scientific interpretation is
still pending.

Final state: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
