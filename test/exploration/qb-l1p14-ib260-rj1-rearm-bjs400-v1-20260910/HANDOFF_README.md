# Raw evidence handoff

Evidence-only handoff for `qb-l1p14-ib260-rj1-rearm-bjs400-v1-20260910`.

- Fixed point: L1=1.4pH, IBias=260uA, BJS=400uA.
- RJ1=12ohm: two exact historical references; RJ1=16/24/32ohm: six new solves.
- Mechanical QA: `qa/` and `mechanical_summary.json`.
- `mechanical_summary.json` keeps CONTROL_ORIGIN, FINAL_ORIGIN and
  POST_FIRST_BJ1_REARM_DIAGNOSTICS separate.
- Visualization: 18 raw-direct standalone pages and two whole-run comparisons.
- Canonical ZIP: `handoff/qb-l1p14-ib260-rj1-rearm-bjs400-v1-20260910_raw_handoff.zip`.

Raw phase is radians. Turns display uses continuous unwrap divided by `2*pi`
and is never an SFQ/event count. Scientific interpretation and follow-up are
not performed.
