# Raw evidence handoff

Evidence-only handoff for
`qb-rj2-highside-second-trigger-l1p14-l2p20-ib260-rj32-bjs400-v2-20260910`.

- Frozen point: L1=1.4pH, L2=2.0pH, IBias=260uA, RJ1=32ohm, BJS=400uA.
- RJ2=10ohm is an exact immutable reuse from the canonical high-side experiment.
- RJ2=12/14/16ohm are registered new values, each executed as a two-mask stage.
- Each next stage requires a recorded `CONTINUE`; a control, first-response or
  eligible second-response guardrail produces `STOP` and preserves later decks.
- Mechanical QA is in `qa/` and `mechanical_summary.json`; per-stage snapshots
  are in `qa/stages/`.
- Visualization uses raw-direct standalone pages and two mask-preserving
  whole-run comparisons. Plots are descriptive evidence only.

Raw `P(...)` is phase in radians. Any turns display uses continuous unwrap
divided by `2*pi` and is a navigation diagnostic, never an SFQ/event count.
Scientific interpretation, route selection and follow-up are not performed.
