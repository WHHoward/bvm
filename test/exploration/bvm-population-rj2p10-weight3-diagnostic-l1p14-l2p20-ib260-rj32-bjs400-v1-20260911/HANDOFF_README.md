# RJ2=10 weight-3 diagnostic handoff

Evidence-only handoff for the frozen BVM → COMMON_SL/JSL → QB → six-stage JTL
topology.

- Exactly one fresh physical solve: `ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111`.
- Frozen canonical protocol: `.tran 0.1p 200p`, FINAL READ 110–121ps, TAIL
  121–200ps; no READ extension or timestep refinement.
- RJ2=10/0011 is the same-RJ2 weight-2 comparison reference; RJ2=11 and
  RJ2=12/0011,0111 are immutable boundary references.
- The 0111 fourth-candidate region 121–130ps is retained with BJ1/BJ2,
  QBOUT, JTL and terminal evidence plus source/receiver state metrics.
- Raw CSV, deck, metadata and run log are immutable after execution.

P values are raw radians. Phase navigation is shown as `rad/(2*pi)` turns and
is not an SFQ count. Scientific interpretation remains `NOT_PERFORMED`.
