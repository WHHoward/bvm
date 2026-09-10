# High-L2 second-trigger search at RJ2=10ohm — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Authority and fixed point

- Experiment: `qb-l2-highside-second-trigger-rj2p10-l1p14-ib260-rj32-bjs400-v1-20260910`
- Preflight HEAD: `993602c964be53a7f32d44b54d9b38ab842f5527`
- Preregistration HEAD: `345d54e6ebf9f0e8b39af616d942ff800ea4e0a7`
- Primary authority: `test/exploration/qb-rj2-highside-rearm-boundary-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910`; source package SHA-256 `9b7422ff45a55f002c4b4f9d0501e63f3b4d48d7a1e19f42641c122b8f1fc42a`.
- Fixed L1=1.4pH, RJ2=10ohm, IBias=260uA, RJ1=32ohm, BJS area=4 / Ic=400uA, L3=1.3pH and canonical terminal/load.
- L2=2.0pH is the exact immutable reused baseline; only L2=2.4/2.8/3.2pH are new physical values.

## Exact matrix

- Logical cases: exactly 4 L2 values (2.0,2.4,2.8,3.2pH) x 2 masks (0001,0011) = 8.
- New physical solves: exactly 6: L2=2.4/2.8/3.2pH, each with 0001 and 0011.
- Historical reuse: exactly ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0001 and ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011 at L2=2.0pH/RJ2=10ohm.
- Unauthorized extra solves: 0; no other L2, mask, retry, intermediate point or refinement.
- Execution order is ascending L2 pair order; a second complete multi-evidence response candidate or first-response/control failure stops later L2 pairs.

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
- L1 records every post-anchor sign transition, positive dwell, local positive maxima and rollback; L1>0 is not a second regeneration.
- First-vs-second receiver state records include I(BJ1), BJ1 phase, BJ2, I(L2), source support, QBOUT, ordered JTL and terminal candidates.
- Direct BJ1 and BJ2 voltage areas and V(BJ1)-V(BJ2) differential areas are recorded for all nine registered windows, including READ-end timing relative to 121ps.
- BJ1 nominal Ic and max|I(BJ1)|/Ic are load-line diagnostics only; no single threshold is switching proof.
- Terminal V(JTL6_OUT) signed areas are separately recorded in CONTROL_ORIGIN and FINAL_ORIGIN; whole-run area is labeled WHOLE_RUN_TOTAL_ONLY and is not a population count.
- I(B_JSL8) and I(LIN) [110,114.5) signed-area ratios are labeled MECHANICAL_PRE_SWITCH_PROXY; ambiguous denominators are UNKNOWN.

## Interpretation ceiling and outputs

- No control/final response is combined into an event count. No phase, voltage area, terminal area or current sign is called an SFQ count.
- Scientific interpretation is NOT_PERFORMED; no L2 threshold, second-trigger conclusion, mechanism, optimum or follow-up is authorized.
- Output: 18 standalone whole-run HTML and two comparison HTML for the full matrix when no early stop occurs; an early stop produces only the executed-case pages.
- Canonical package: `handoff/qb-l2-highside-second-trigger-rj2p10-l1p14-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip`.

## Automatic preflight result

- L2=2.0pH/RJ2=10ohm reuse comparability: `PASS`.
- New deck checks: `PASS`.
- Physical execution has not started at preflight.
