# High-range RJ1 boundary search under frozen BJS400 D working point — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Authority

- Primary physical/stimulus authority: test/exploration/qb-rj1-switched-regime-characterization-bjs400-v1-20260910
- Preflight HEAD: 9f3412453b2f617e39245a34c73af3f0c20881d4
- Fixed point: L1=1.6pH, IBias=260uA, BJS area=4, BJS Ic=400uA.
- READ protocol: UNCHANGED/FROZEN.
- New RJ1 values: 20/24/32/48ohm.
- Historical trend references: 10/12/14/16ohm for masks 0001 and 0011.

## Frozen history

WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL

- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps.
- ZERO_STATE_READ_CONTROL 70–81ps; idle 81–90ps.
- WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.
- WL/BL/SE amplitude 100uA, 1ps edges, 9ps plateau, .tran 0.1p 200p.
- Masks only: 0001 (BVM4 active) and 0011 (BVM3+BVM4 active).

## Exact matrix

- New physical solves: exactly 8 = four new RJ1 values × two masks.
- Historical references: exactly 8 = 10/12/14/16ohm × two masks.
- No extra RJ1 value, mask, READ change, retry, tuning, refinement or follow-up.

## Preflight results

- Historical reference comparability: PASS.
- New deck diff: PASS.
- Broad raw probe declarations and mandatory BJS/JTL current probes are registered.
- Raw execution has not started at preflight.

Scientific interpretation is NOT_PERFORMED.
