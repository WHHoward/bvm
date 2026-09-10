# Raw evidence handoff

Evidence-only handoff for
`qb-rj2-highside-rearm-boundary-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910`.

- Frozen point: L1=1.4pH, L2=2.0pH, IBias=260uA, RJ1=32ohm, BJS=400uA.
- RJ2=6ohm: exact immutable reuse from the prior canonical RJ2 experiment.
- RJ2=8/10/12ohm: newly authorized high-side values, two masks each.
- Early stop: strict stored-sample `I(L1)` negative-to-positive transition
  observed at RJ2=10ohm / 0011; RJ2=12ohm was not run and its decks are retained.
- Mechanical QA: `qa/` and `mechanical_summary.json`.
- Independent review: `analysis/REVIEW.md` and `qa/independent_review.json`.
- Visualization: 12 raw-direct standalone pages and two whole-run comparisons for the four executed new cases.
- Canonical ZIP: `handoff/qb-rj2-highside-rearm-boundary-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip`.

Raw phase is radians. Any turns display uses continuous unwrap divided by
`2*pi` and is a navigation diagnostic, never an SFQ/event count. Scientific
interpretation, route selection and follow-up are not performed here.
