# RJ1 switched-regime characterization under D working point — evidence manifest

This is an evidence-only experiment package. Scientific interpretation is
NOT_PERFORMED.

- Experiment: qb-rj1-switched-regime-characterization-bjs400-v1-20260910
- Fixed D point: L1=1.6pH, IBias=260uA, BJS area=4, BJS Ic=400uA.
- New RJ1 values: 10/14/16ohm.
- RJ1=12ohm: two exact historical D raw references.
- Masks: 0001 and 0011 only.
- History: WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE ->
  mask-selective FINAL READ -> TAIL.
- New physical solves: exactly 6; reused physical cases: exactly 2.
- Mechanical summary: mechanical_summary.json; first +0.5-turn values are timing
  diagnostics, not event times.
- QA: qa/raw_qa.json, qa/deck_diff_qa.json and qa/visualization_qa.json.
- Visualization: visualization/manifest.json and visualization/run_summaries/.
- Canonical ZIP:
  handoff/qb-rj1-switched-regime-characterization-bjs400-v1-20260910_raw_handoff.zip
- PACKAGE_QA: adjacent handoff/PACKAGE_QA.json; detached to avoid self-hash recursion.
- No event/SFQ classifier, mechanism analysis, ranking, tuning or follow-up.
- Final state: AWAITING_SCIENTIFIC_REVIEW.

