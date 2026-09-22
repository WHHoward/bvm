# ARRAY_SIZE platform regression preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Scope

- Purpose: mechanical backward-compatibility regression of the refactored fan-in renderer.
- Parent HEAD before physical regression: `862feaebc0ee32def81a315227e80c06c047e4d1`.
- No U039/JSL/QB/JTL physical parameter change is authorized.
- Scientific interpretation is not authorized; results are artifact and numerical-equivalence evidence only.

## Registered matrix

- `ARRAY_SIZE=4`
- Mode: `closed`
- Parameters: exact `U136_QB_BJ1_screen_qb_bj1_area_0p75/config_snapshot.env` values.
- Masks: `0000`, `0001`, `0011` only.
- Expected physical solves: exactly 3.
- Reference raw: `runs/U136_QB_BJ1_screen_qb_bj1_area_0p75/cases/CLOSED_N0_0000`, `CLOSED_N1_0001`, `CLOSED_N2_0011`.
- No reuse is allowed for the regression case; the new renderer must produce fresh raw for direct comparison.

## Frozen topology and protocol

- Exactly four BVM instances, `COMMON_SL`, JSL1..JSL8, QB, JTL1..JTL6 and `R_TERM`.
- DT `0.1p`, STOP `200p`, normal protocol timings/amplitudes unchanged.
- Probes include all four BVMs, shared boundary, JSL, QB, all JTL stages and terminal.

## Mechanical acceptance

- New raw must be present, finite, monotonic and raw-QA PASS.
- New and reference headers, stored sample count/time grid and raw values must be compared.
- The registered key signals are compared pointwise; exact raw hash equality is the preferred result.
- Any non-equality is `REVIEW_REQUIRED`, not a scientific failure.
- ARRAY_SIZE=1/2/3 are render/topology/CONTROL_ONLY smoke tests only; no physical solve is authorized for them.

## Prohibited actions

- No sweep, optimization, fan-in scientific comparison, control interpretation, sentinel or follow-up solve.
- Do not modify or stage unrelated `scripts/MC_conclu.py` changes.
