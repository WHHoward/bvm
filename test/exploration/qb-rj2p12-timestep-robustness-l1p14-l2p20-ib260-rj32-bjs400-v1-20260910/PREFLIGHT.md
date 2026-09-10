# RJ2=12 timestep robustness spot-check — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `qb-rj2p12-timestep-robustness-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910`
- Preflight HEAD: `edd55f9899ccb71e0a42a079d4842b1faa6876cc`
- Phase A oracle repair commit: `fd1fc5cf`; oracle SHA-256 `f5365ba4651cc1828b32a5932eb5c4cab7bda3317c81563e0cbb6571abe7230f`.
- Canonical timestep remains `.tran=0.1p`; this experiment uses 0.05ps and 0.025ps only as local robustness spot-checks.
- Fixed L1=1.4pH, L2=2.0pH, IBias=260uA, RJ1=32ohm, RJ2=12ohm, BJS area=4/Ic=400uA, BJ1/BJ2/L3/load/topology/history unchanged.

## Exact matrix

- 0.1ps: exact immutable reuse for masks 0001 and 0011; no 0.1ps solver invocation.
- 0.05ps: new physical solves for masks 0001 and 0011.
- 0.025ps: new physical solves for masks 0001 and 0011.
- Total: 6 logical timestep/mask cases, 2 reuse cases, exactly 4 new solves; no RJ2=14/16 finer rerun or other parameter sweep.

## Frozen protocol and interpretation ceiling

- IDLE 0–50ps; WRITE0 50–61ps; IDLE 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; IDLE 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.
- Amplitude 100uA, rise/fall 1ps, plateau 9ps, stop time 200ps; only the `.tran` timestep changes.
- Repaired oracle uses FINAL baseline [101,110)ps, cumulative +0.5/+1.5 navigation landmarks, direct voltage clusters and valley-gated terminal pulse segmentation.
- Phase, pulse area, current peak, L1 crossing and terminal area are not SFQ counts. A stable classification here is a finite `TIMESTEP_ROBUST_CANDIDATE_WITHIN_TESTED_DT`, not convergence or final SFQ proof.

## Automatic preflight result

- Exact 0.1ps reuse: `PASS`; deck checks: `PASS`.
- Physical execution has not started at preflight.
