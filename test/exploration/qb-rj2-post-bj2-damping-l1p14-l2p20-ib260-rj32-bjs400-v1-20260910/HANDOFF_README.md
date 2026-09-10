# Raw evidence handoff

Evidence-only handoff for `qb-rj2-post-bj2-damping-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910`.

- Fixed point: L1=1.4pH, L2=2.0pH, IBias=260uA, RJ1=32ohm, BJS=400uA.
- RJ2=4ohm: two exact historical references; RJ2=2/3/6ohm: six new solves.
- Mechanical QA: `qa/` and `mechanical_summary.json`.
- Dedicated sections: CONTROL_ORIGIN, FINAL_ORIGIN,
  POST_FIRST_BJ2_REARM and DIFFERENTIAL_VOLTAGE_IMPULSE.
- Visualization: 18 raw-direct standalone pages and two whole-run comparisons.
- Canonical ZIP: `handoff/qb-rj2-post-bj2-damping-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip`.

Raw phase is radians. Turns display uses continuous unwrap divided by `2*pi`
and never represents an SFQ/event count. Scientific interpretation and any
follow-up experiment are not performed.
