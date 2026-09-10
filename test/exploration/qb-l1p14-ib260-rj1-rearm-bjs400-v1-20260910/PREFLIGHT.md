# Combined L1 + IBias + RJ1 interaction near clean-control boundary — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Authority and fixed point

- Experiment: `qb-l1p14-ib260-rj1-rearm-bjs400-v1-20260910`
- Preflight HEAD: `314afe6115d488dab68b97a9609e4312763ee2d8`
- Preregistration HEAD: `e91beb80acd009ce47fbd3a3c70a9315a579d3ad`
- Primary authority: `test/exploration/qb-l1-ibias-full-grid-bjs400-v1-20260910`; source package SHA-256 `7ccb82a479f792a14e8f1e6bbe66f7f8acd51ef133f6fbe23175b74306c0ab18`.
- Fixed L1=1.4pH, IBias=260uA, BJS area=4 / Ic=400uA, terminal=10ohm.
- RJ1=12ohm is historical immutable reuse; only RJ1=16/24/32ohm are new physical values.
- The older no-history stimulus is not used.

## Exact matrix

- Logical cases: exactly 4 RJ1 values (12,16,24,32ohm) x 2 masks (0001,0011) = 8.
- New physical solves: exactly 6: RJ1=16/24/32ohm, each with 0001 and 0011.
- Historical reuse: exactly ARRAY_L1P14_IB260_0001 and ARRAY_L1P14_IB260_0011 at RJ1=12ohm.
- Unauthorized extra solves: 0; no other RJ1, mask, SINGLE, retry or refinement.

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
- RJ1 I/V extrema and V*I energy are separated for CONTROL_ORIGIN and FINAL_ORIGIN; L1 zero crossings use stored sample transition times only, no interpolation.
- POST_FIRST_BJ1_REARM_DIAGNOSTICS uses the first FINAL-origin BJ1 +0.5-turn timing diagnostic as t_BJ1_half; L1 negative-to-positive is MECHANICAL_REARM_PROXY_ONLY.
- Post-anchor L2 local maxima separated by at least 1.0ps are MECHANICAL_SECOND_SURGE_PROXY_ONLY; BJ2 +1.5 and JTL +0.5/+1.5 fields are mechanical threshold/candidate diagnostics only.
- Terminal V(JTL6_OUT) signed areas are separately recorded in CONTROL_ORIGIN and FINAL_ORIGIN; whole-run area is labeled WHOLE_RUN_TOTAL_ONLY and is not a population count.
- I(B_JSL8) and I(LIN) [110,114.5) signed-area ratios are labeled MECHANICAL_PRE_SWITCH_PROXY; ambiguous denominators are UNKNOWN.

## Interpretation ceiling and outputs

- No control/final response is combined into an event count. No phase, voltage area, terminal area or current sign is called an SFQ count.
- Scientific interpretation is NOT_PERFORMED; no exact RJ1 threshold, optimum, mechanism, control PASS/FAIL or follow-up is authorized.
- Output: exactly 18 standalone whole-run HTML and two comparison HTML; no permanent focused plots or duplicate plot CSV.
- Canonical package: `handoff/qb-l1p14-ib260-rj1-rearm-bjs400-v1-20260910_raw_handoff.zip`.

## Automatic preflight result

- RJ1=12 reuse comparability: `PASS`.
- New deck checks: `PASS`.
- Physical execution has not started at preflight.
