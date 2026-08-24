# JTL_TRANSPORT_GATE_V1 numerical-freeze pilot — summary

## Pilot disposition

`PILOT_INCONCLUSIVE_PENDING_STRICT_REPLAY`

## Observed

- The initial pilot produced the expected four-stage `+1` settled-well vectors
  for R11 and the pulse-5 original replay, and a non-transport reverse replay.
- Strict local segment evidence remains separate from settled-well transport;
  the latter does not relabel sub-turn downstream segments as local events.
- The pilot was not used to freeze the gate because its analysis implementation
  applied an unwrapped-phase transform to raw `P(...)`, did not bind every
  source/input hash before execution, and used coupled rather than independent
  pre/post perturbation views.

## Boundary

This directory preserves the first bounded pilot raw and analysis. It is not a
numerical freeze, physical BVM→JTL evidence, universal JTL acceptance spec, or
T1 result. The strict hash-bound successor is recorded separately below.

See [PREREGISTRATION.md](PREREGISTRATION.md),
[pilot disposition](analysis/PILOT_DISPOSITION.md), and the successor
directory `jtl-transport-gate-v1-numerical-freeze-20260824-rerun`.
