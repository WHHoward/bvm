# RJ2=11 midpoint handoff

Evidence-only handoff for the frozen BVM → COMMON_SL/JSL → QB → six-stage JTL
topology.

- Physical parameter delta: `RJ2=12ohm -> 11ohm` only.
- Fresh solves: exactly `0001`, `0011`, `0111`, `1111`.
- RJ2=12 references are copied byte-for-byte from the latest canonical Drive
  handoff and are used only for comparison.
- Canonical timestep remains `.tran 0.1p 200p`; no timestep sweep or READ
  extension is allowed.
- Raw CSV, deck, metadata and run log are immutable after execution.
- The 0111 case receives explicit first/second/third/fourth and 121–130ps
  post-READ analysis; 0011 receives explicit second-response analysis.

P values are raw radians. Phase navigation is displayed as `rad/(2*pi)` turns;
it is not an SFQ count. Scientific interpretation remains `NOT_PERFORMED`.
