# L2-controlled post-regeneration re-arm characterization — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Authority and fixed point

- Experiment: `qb-l2-rearm-sweep-l1p14-ib260-rj32-bjs400-v1-20260910`
- Preflight HEAD: `d9656152fc2a7f8ac45e0cf53b00e63db9d11266`
- Preregistration HEAD: `d9656152fc2a7f8ac45e0cf53b00e63db9d11266`
- Primary authority: `test/exploration/qb-l1p14-ib260-rj1-rearm-bjs400-v1-20260910`; source package SHA-256 `7b8da746829605973e0b8d469deccbf8e254df59d46bca02f4b181e584988ea8`.
- Fixed L1=1.4pH, IBias=260uA, RJ1=32ohm, BJS area=4 / Ic=400uA, terminal=10ohm.
- L2=2.0pH is historical immutable reuse; only L2=1.6/1.2/0.8pH are new physical values.
- The older no-history stimulus is not used.

## Exact matrix

- Logical cases: exactly 4 L2 values (2.0,1.6,1.2,0.8pH) x 2 masks (0001,0011) = 8.
- New physical solves: exactly 6: L2=1.6/1.2/0.8pH, each with 0001 and 0011.
- Historical reuse: exactly ARRAY_L1P14_IB260_RJ32_0001 and ARRAY_L1P14_IB260_RJ32_0011 at L2=2.0pH.
- Unauthorized extra solves: 0; no other L2, mask, SINGLE, retry or refinement.

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
- RJ1 I/V energy, L2/BJ2 extrema and L1 zero crossings are separated for CONTROL_ORIGIN and FINAL_ORIGIN; transitions use stored samples only, no interpolation.
- Terminal V(JTL6_OUT) signed areas are separately recorded in CONTROL_ORIGIN and FINAL_ORIGIN; whole-run area is labeled WHOLE_RUN_TOTAL_ONLY and is not a population count.
- I(B_JSL8) and I(LIN) [110,114.5) signed-area ratios are labeled MECHANICAL_PRE_SWITCH_PROXY; ambiguous denominators are UNKNOWN.

## Interpretation ceiling and outputs

- No control/final response is combined into an event count. No phase, voltage area, terminal area or current sign is called an SFQ count.
- Scientific interpretation is NOT_PERFORMED; no L2 threshold, re-arm conclusion, optimum, mechanism, control PASS/FAIL or follow-up is authorized.
- Output: exactly 18 standalone whole-run HTML and two comparison HTML; no permanent focused plots or duplicate plot CSV.
- Canonical package: `handoff/qb-l2-rearm-sweep-l1p14-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip`.

## Automatic preflight result

- RJ1=12 reuse comparability: `PASS`.
- New deck checks: `PASS`.
- Physical execution has not started at preflight.
