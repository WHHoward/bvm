# RJ2 high-side post-BJ2 re-arm boundary search — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Authority and fixed point

- Experiment: `qb-rj2-highside-rearm-boundary-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910`
- Preflight HEAD: `c8fc8c5b6483d65e7b2e04e470e81ca07c95fd3f`
- Preregistration HEAD: `c8fc8c5b6483d65e7b2e04e470e81ca07c95fd3f`
- Primary authority: `test/exploration/qb-rj2-post-bj2-damping-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910`; source package SHA-256 `897a8c2cbf17f9aba4fdc688a82b62080a1398b4afcacbde30db9411bd9dfb09`.
- Fixed L1=1.4pH, IBias=260uA, RJ1=32ohm, BJS area=4 / Ic=400uA, terminal=10ohm.
- L2=2.0pH and RJ1=32ohm are frozen; RJ2=6ohm is historical immutable reuse and only RJ2=8/10/12ohm are new physical values.
- The older no-history stimulus is not used.

## Exact matrix

- Logical cases: exactly 4 RJ2 values (6,8,10,12ohm) x 2 masks (0001,0011) = 8.
- New physical solves: exactly 6: RJ2=8/10/12ohm, each with 0001 and 0011.
- Historical reuse: exactly ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P6_0001 and ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P6_0011 at RJ2=6ohm.
- Unauthorized extra solves: 0; no other RJ2, mask, SINGLE, retry or refinement.
- Execution order is ascending RJ2 pair order; after each completed 0011 member, a strict stored-sample post-anchor L1 negative-to-positive transition stops the remaining high-side sweep.

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
- L1 records anchor value, post-anchor extrema, exact-zero samples, stored-sample sign transitions and positive dwell; only an observed negative-to-positive adjacent pair receives OBSERVED_L1_RECROSSING.
- Each first response and any second post-anchor response retains BJ1 -> BJ2 -> QBOUT -> ordered JTL1..JTL6 -> terminal checks as a mechanical multi-evidence candidate.
- Direct BJ1 and BJ2 voltage areas and V(BJ1)-V(BJ2) differential areas are recorded for anchor->121ps, 121->140ps, anchor->140ps, anchor->200ps, 110->121ps, 110->140ps and 110->200ps.
- Terminal V(JTL6_OUT) signed areas are separately recorded in CONTROL_ORIGIN and FINAL_ORIGIN; whole-run area is labeled WHOLE_RUN_TOTAL_ONLY and is not a population count.
- I(B_JSL8) and I(LIN) [110,114.5) signed-area ratios are labeled MECHANICAL_PRE_SWITCH_PROXY; ambiguous denominators are UNKNOWN.

## Interpretation ceiling and outputs

- No control/final response is combined into an event count. No phase, voltage area, terminal area or current sign is called an SFQ count.
- Scientific interpretation is NOT_PERFORMED; no RJ2 threshold, damping/re-arm conclusion, optimum, mechanism, control PASS/FAIL or follow-up is authorized.
- Output: exactly 18 standalone whole-run HTML and two comparison HTML; no permanent focused plots or duplicate plot CSV.
- Canonical package: `handoff/qb-rj2-highside-rearm-boundary-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip`.

## Automatic preflight result

- RJ2=6ohm reuse comparability: `PASS`.
- New deck checks: `PASS`.
- Physical execution has not started at preflight.
