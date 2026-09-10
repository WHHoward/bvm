# Raw evidence handoff

This directory is an evidence-only handoff for
`qb-l1-ibias-full-grid-bjs400-v1-20260910`.

- New physical solves: exactly 10; each has `deck.cir`, `raw.csv`, `metadata.json` and `run.log`.
- Historical reuse: exactly 14; the immutable source/archive hashes and exact-comparability checks are in `REUSED_REFERENCE_MANIFEST.json`.
- Mechanical QA: `qa/raw_qa.json`, `qa/deck_diff_qa.json`, `qa/provenance.json`, `qa/execution_summary.json`, `qa/transformation_registry.json` and `mechanical_summary.json`.
- Visualization: whole-run raw-direct standalone pages under `plots/runs/` and exactly two full-grid comparison pages under `plots/comparison/`.
- Canonical ZIP: `handoff/qb-l1-ibias-full-grid-bjs400-v1-20260910_raw_handoff_v2.zip`.
- The uncommitted first packaging attempt is retained as `handoff/qb-l1-ibias-full-grid-bjs400-v1-20260910_raw_handoff.zip` and marked invalid in `handoff/PACKAGE_QA_v1_INVALID.json`.
- Detached package QA: `handoff/PACKAGE_QA.json`.

Raw P values are radians. Any display conversion to turns is continuous unwrap
followed by division by `2*pi`; no phase displacement is an SFQ count. Scientific
interpretation, event classification, parameter ranking and follow-up are not
performed.
