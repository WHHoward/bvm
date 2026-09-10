# High-L2 second-trigger search — evidence-only result

Scientific interpretation is `NOT_PERFORMED`.

This experiment fixes L1=1.4pH, RJ2=10ohm, IBias=260uA, RJ1=32ohm and the
BJS400 ARRAY stored history. L2=2.0pH is an exact immutable reuse from the
previous canonical RJ2 high-side experiment; L2=2.4/2.8/3.2pH are the only
new physical values.

The evidence separates the first positive L1 excursion from later positive
candidates after the first FINAL-origin BJ2 +0.9 navigation anchor. It records
positive dwell, rollback, BJ1 current/phase load-line diagnostics, source and
receiver support, READ-end timing, direct voltage/differential areas and the
full second-chain candidate checks. No L1 crossing, phase turn, voltage area,
terminal area or current ratio is an SFQ count.

If the registered second-complete-response or first-response/control failure
stop condition occurs, the executed matrix and stop reason are preserved in
`qa/execution_summary.json`; no unregistered L2 point is added.

Final state: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
