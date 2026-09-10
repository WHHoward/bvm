# RJ2 high-side second-trigger search — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Authority and fixed point

- Experiment: `qb-rj2-highside-second-trigger-l1p14-l2p20-ib260-rj32-bjs400-v2-20260910`
- Preflight HEAD: `86e332d2805a8606939b5ead5873f6efa8b99afe`
- Preregistration HEAD: `a7575054f54ad0847e4d4ff64b45bfecff07f436`
- Primary authority: `test/exploration/qb-rj2-highside-rearm-boundary-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910`; source package SHA-256 `9b7422ff45a55f002c4b4f9d0501e63f3b4d48d7a1e19f42641c122b8f1fc42a`.
- Fixed L1=1.4pH, L2=2.0pH, IBias=260uA, RJ1=32ohm, BJS area=4 / Ic=400uA, terminal=10ohm.
- RJ2=10ohm is historical immutable reuse; only RJ2=12/14/16ohm are new physical values.
- The older no-history stimulus is not used.

## Exact matrix

- Logical cases: exactly 4 RJ2 values (10,12,14,16ohm) x 2 masks (0001,0011) = 8.
- Maximum new physical solves: exactly 6: RJ2=12/14/16ohm, each with 0001 and 0011.
- Historical reuse: exactly ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0001 and ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011 at RJ2=10ohm.
- Unauthorized extra solves: 0; no other RJ2, mask, intermediate point or refinement.
- Mandatory sequential execution: after each completed pair, guardrail and second-trigger QA must produce CONTINUE before the next pair may run.

## Frozen protocol

- History: WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL.
- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; idle 81–90ps.
- WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.
- WL/BL/SE amplitude 100uA; 1ps rise/fall; 9ps plateau; `.tran 0.1p 200p`.
- Mask bit order b3b2b1b0=BVM1/BVM2/BVM3/BVM4; 0001 activates BVM4, 0011 activates BVM3+BVM4 during FINAL READ only.

## Registered mechanical windows and diagnostics

- CONTROL_ORIGIN: [70,110)ps; baseline [61,70)ps. FINAL_ORIGIN: [110,200)ps; baseline [101,110)ps.
- BJ1/BJ2 phase is independently unwrapped from raw radians and displayed as rad/(2*pi) turns; +0.5 timing is a navigation diagnostic, never an event time/count.
- JTL progression candidate uses fixed +0.5-turn stage-B01 timing in order across JTL1..JTL6; a second candidate uses fixed +1.5-turn timing. Both are MECHANICAL_CANDIDATE_ONLY, not SFQ/event classifiers.
- BJ1/BJ2/L1/L2/RJ2/L3 and source-side data are separated for CONTROL_ORIGIN, first response and post-first-BJ2 candidate windows; transitions use stored samples only.
- First versus strongest later positive L1 segments record dwell, rollback, BJ1 current/phase, nominal-Ic ratio, BJ2, L2, source support and READ-end timing.
- Each first response and any second response retains BJ1 -> BJ2 -> QBOUT -> ordered JTL1..JTL6 -> terminal checks as a mechanical multi-evidence candidate.
- Direct BJ1 and BJ2 voltage areas and V(BJ1)-V(BJ2) differential areas are recorded for all registered windows and cumulative 110-to-t landmarks.
- Terminal V(JTL6_OUT) signed areas are separately recorded in CONTROL_ORIGIN and FINAL_ORIGIN; whole-run area is labeled WHOLE_RUN_TOTAL_ONLY and is not a population count.
- I(B_JSL8) and I(LIN) [110,114.5) signed-area ratios are labeled MECHANICAL_PRE_SWITCH_PROXY; ambiguous denominators are UNKNOWN.

## Interpretation ceiling and outputs

- No control/final response is combined into an event count. No phase, voltage area, terminal area or current sign is called an SFQ count.
- Scientific interpretation is NOT_PERFORMED; no RJ2 threshold, second-trigger conclusion, optimum, mechanism or follow-up is authorized.
- Output: three raw-direct whole-run pages per executed new case and two mask-preserving comparisons; no duplicate plot CSV.
- Canonical package: `handoff/qb-rj2-highside-second-trigger-l1p14-l2p20-ib260-rj32-bjs400-v2-20260910_raw_handoff.zip`.

## Automatic preflight result

- RJ2=10ohm reuse comparability: `PASS`.
- New deck checks: `PASS`.
- Physical execution has not started at preflight.
