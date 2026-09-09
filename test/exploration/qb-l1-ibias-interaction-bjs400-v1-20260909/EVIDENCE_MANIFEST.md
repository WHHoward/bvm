# Minimal L1 x IBias interaction under BJS400 — evidence manifest

This is an evidence-only experiment package. Scientific interpretation is
NOT_PERFORMED.

- Experiment: qb-l1-ibias-interaction-bjs400-v1-20260909
- Physical/stimulus authority: qb-bjs400-array-population-single-matched-v1-20260909
- Matrix: A=(2.0pH,250uA), B=(2.0pH,260uA), C=(1.6pH,250uA), D=(1.6pH,260uA).
- B is represented by two exact historical BJS400 raw references.
- New physical solves: exactly 6. Reused physical cases: exactly 2.
- BJS area=4 and RJ1=12ohm; all other fixture values and history remain frozen.
- History: WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE ->
  mask-selective FINAL READ -> TAIL.
- Visualization: three raw-direct standalone pages per new run and exactly two
  whole-run interaction comparison pages.
- QA: see qa/raw_qa.json, qa/deck_diff_qa.json and qa/visualization_qa.json.
- Reuse provenance: REUSED_REFERENCE_MANIFEST.json.
- Canonical ZIP:
  handoff/qb-l1-ibias-interaction-bjs400-v1-20260909_raw_handoff_v2.zip
- PACKAGE_QA: adjacent handoff/PACKAGE_QA.json; detached to avoid self-hash recursion.
- No scientific interpretation, event classification, ranking, tuning or follow-up.
- Final state: AWAITING_SCIENTIFIC_REVIEW.
