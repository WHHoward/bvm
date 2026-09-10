# Raw evidence handoff

Evidence-only handoff for `qb-l2-rearm-sweep-l1p14-ib260-rj32-bjs400-v1-20260910`.

- Fixed point: L1=1.4pH, IBias=260uA, RJ1=32ohm, BJS=400uA.
- L2=2.0pH: two exact historical references; L2=1.6/1.2/0.8pH: six new solves.
- Mechanical QA: `qa/` and `mechanical_summary.json`.
- Dedicated sections: CONTROL_ORIGIN, FINAL_ORIGIN,
  POST_FIRST_BJ2_REARM and DIFFERENTIAL_VOLTAGE_IMPULSE.
- Visualization: 18 raw-direct standalone pages and two whole-run comparisons.
- Canonical ZIP: `handoff/qb-l2-rearm-sweep-l1p14-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip`.

Raw phase is radians. Any turns display is continuous unwrap divided by `2*pi`
and is never an SFQ/event count. Scientific interpretation and follow-up are
not performed.
