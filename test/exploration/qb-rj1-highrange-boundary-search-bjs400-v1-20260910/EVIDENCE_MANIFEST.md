# High-range RJ1 boundary search under frozen BJS400 D working point — evidence manifest

This is an evidence-only experiment package. Scientific interpretation is
NOT_PERFORMED.

- Experiment: qb-rj1-highrange-boundary-search-bjs400-v1-20260910
- Fixed point: L1=1.6pH, IBias=260uA, BJS area=4, BJS Ic=400uA.
- Historical trend references: RJ1=10/12/14/16ohm for masks 0001 and 0011.
- New physical values: RJ1=20/24/32/48ohm for masks 0001 and 0011.
- READ protocol: UNCHANGED/FROZEN.
- History: WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE ->
  mask-selective FINAL READ -> TAIL.
- New physical solves: exactly 8; historical reference cases: exactly 8.
- Mechanical summary: mechanical_summary.json; diagnostics are not event counts
  or boundary classifications.
- QA: qa/raw_qa.json, qa/deck_diff_qa.json and qa/visualization_qa.json.
- Visualization: visualization/manifest.json and visualization/run_summaries/.
- Canonical ZIP:
  handoff/qb-rj1-highrange-boundary-search-bjs400-v1-20260910_raw_handoff.zip
- PACKAGE_QA: adjacent handoff/PACKAGE_QA.json; detached to avoid self-hash recursion.
- No focused-window, event/SFQ, mechanism, ranking, refinement or follow-up artifact.
- Final state: AWAITING_SCIENTIFIC_REVIEW.

