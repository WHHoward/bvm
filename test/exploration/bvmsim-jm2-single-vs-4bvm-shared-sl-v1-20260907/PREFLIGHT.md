# PREFLIGHT — JM2-connected SINGLE vs 4-BVM shared-SL

- Status: **PASS**
- Preflight time: `2026-09-07T13:15:24+08:00`
- HEAD at preflight: `36a59701acc535d3ff98ffa590640555ada898ac`
- Scientific tier: `EXPLORATION / QUICK`; no physical mechanism interpretation is registered.

## Frozen scope

- BVM source is the historical JM2-connected variant; `circuits/bvm/bvm_cell.cir` is not used.
- Both fixtures use exactly 8 `jjmit area=5.0` JSL junctions, the exact `BVMSim/BQ.cir`, the exact six-stage `BVMSim/library_josim/jtl2.cir`, and one 10-ohm termination.
- The target controls and absolute timing are registered identically; ARRAY BVM2–BVM4 are quiet only during the final selective READ.
- Full P/V/I probe coverage is retained in both raw runs, including JSL2–JSL7 and ARRAY BVM2–BVM4.

## Mechanical checks

| check | result |
|---|---|
| SINGLE topology | `PASS`; 1 BVM, 8 JSL, 1 QB, 6 JTL, 1 × 10 Ω |
| ARRAY topology | `PASS`; 4 BVM, 8 shared JSL, 1 QB, 6 JTL, 1 × 10 Ω |
| JM2 variant diff | `PASS`; only registered `L_M2` node 4 → 3 |
| downstream identity | `PASS` |
| target static control identity | `PASS` |
| full probe schema | `PASS` |

## Decision

Preflight passed. The two registered physical runs may execute directly.

Machine record: `analysis/topology_preflight.json`.
