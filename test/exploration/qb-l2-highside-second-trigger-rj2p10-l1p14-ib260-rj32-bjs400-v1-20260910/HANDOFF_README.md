# Raw evidence handoff

Evidence-only handoff for
`qb-l2-highside-second-trigger-rj2p10-l1p14-ib260-rj32-bjs400-v1-20260910`.

- Frozen point: L1=1.4pH, RJ2=10ohm, IBias=260uA, RJ1=32ohm, BJS=400uA.
- L2=2.0pH: exact immutable reuse from the prior canonical RJ2 high-side experiment.
- L2=2.4/2.8/3.2pH: newly authorized values, two masks each.
- First control-failure boundary: L2=2.4pH. The executor later recorded a
  second-candidate stop at L2=2.8pH / 0011; this ordering is preserved in the
  protocol audit. L2=3.2pH was not run and its decks are retained.
- Mechanical QA: `qa/` and `mechanical_summary.json`.
- Independent review: `analysis/REVIEW.md` and `qa/independent_review.json`.
- Protocol audit: `qa/protocol_audit.json`.
- Visualization: 12 whole-run raw-direct pages and two mask-preserving comparisons for the four executed new cases.
- Canonical ZIP: `handoff/qb-l2-highside-second-trigger-rj2p10-l1p14-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip`.

Raw phase is radians. Turns display uses continuous unwrap divided by `2*pi`
and is diagnostic navigation only, never an SFQ/event count. Scientific
interpretation and follow-up are not performed here.
