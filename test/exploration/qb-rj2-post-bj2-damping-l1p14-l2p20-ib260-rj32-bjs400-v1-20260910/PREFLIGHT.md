# RJ2-controlled post-BJ2 damping characterization — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Authority and fixed point

- Experiment: `qb-rj2-post-bj2-damping-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910`
- Preflight HEAD: `9e1401021c4247017f5459d2c6c0cd67dcac1c30`
- Preregistration HEAD: `9e1401021c4247017f5459d2c6c0cd67dcac1c30`
- Primary authority: `test/exploration/qb-l1p14-ib260-rj1-rearm-bjs400-v1-20260910`; source package SHA-256 `7b8da746829605973e0b8d469deccbf8e254df59d46bca02f4b181e584988ea8`.
- Fixed L1=1.4pH, IBias=260uA, RJ1=32ohm, BJS area=4 / Ic=400uA, terminal=10ohm.
- L2=2.0pH and RJ1=32ohm are frozen; RJ2=4ohm is historical immutable reuse and only RJ2=2/3/6ohm are new physical values.
- The older no-history stimulus is not used.

## Exact matrix

- Logical cases: exactly 4 RJ2 values (4,2,3,6ohm) x 2 masks (0001,0011) = 8.
- New physical solves: exactly 6: RJ2=2/3/6ohm, each with 0001 and 0011.
- Historical reuse: exactly ARRAY_L1P14_IB260_RJ32_0001 and ARRAY_L1P14_IB260_RJ32_0011 at RJ2=4ohm.
- Unauthorized extra solves: 0; no other RJ2, mask, SINGLE, retry or refinement.

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
- RJ2/BJ2 I/V energy, L2/BJ2 extrema and L1 zero crossings are separated for CONTROL_ORIGIN and FINAL_ORIGIN; transitions use stored samples only, no interpolation.
- Terminal V(JTL6_OUT) signed areas are separately recorded in CONTROL_ORIGIN and FINAL_ORIGIN; whole-run area is labeled WHOLE_RUN_TOTAL_ONLY and is not a population count.
- I(B_JSL8) and I(LIN) [110,114.5) signed-area ratios are labeled MECHANICAL_PRE_SWITCH_PROXY; ambiguous denominators are UNKNOWN.

## Interpretation ceiling and outputs

- No control/final response is combined into an event count. No phase, voltage area, terminal area or current sign is called an SFQ count.
- Scientific interpretation is NOT_PERFORMED; no RJ2 threshold, damping/re-arm conclusion, optimum, mechanism, control PASS/FAIL or follow-up is authorized.
- Output: exactly 18 standalone whole-run HTML and two comparison HTML; no permanent focused plots or duplicate plot CSV.
- Canonical package: `handoff/qb-rj2-post-bj2-damping-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip`.

## Automatic preflight result

- RJ2=4ohm reuse comparability: `PASS`.
- New deck checks: `PASS`.
- Physical execution has not started at preflight.
