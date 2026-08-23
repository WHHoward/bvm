# R15-A AFQ-3 single-point execution

日期：2026-08-23
模式：`exploratory`，single-point gated execution
基线：`3113a4640c74e515cc6fe991f1c37752b168e8c2`

## Primary question

在保持 canonical BVM 与 frozen `DCSFQ_BVM.cir` 不变的前提下，AFQ-3 是否能
把 BVM 的 read1-selective detector activity 转换成由独立 bias 供能的 bounded
active state transition，并向 DCSFQ input 提供明显高于 R1a passive secondary
的 drive？

本轮不接 JTL/T1，不 sweep，不修改 canonical BVM、DCSFQ backend 或 R0b/R1a
参数。只有 Gate 0–4 全部没有 analytic contradiction 才执行四个 matched cases。
Gate 2 的 no-input stability 以 `logical1-read0-control` 作为首个执行 case；若
出现 startup running 或 free-running，立即停止其余 cases。

## Frozen nominal point

### Existing detector

- `R_IN=12 Ω`
- `L_TX=0.20 pH`
- `B_DET AREA=.50`, bias `+15 µA`
- `K_IN=-.80`，符号按 `L_TX: N_PICK→N_DET`、`L_S: N_S1→N_S2` 冻结

### New AFQ-3 hypothesis

- `L_RET=5.0 pH`, `L_S=50.0 pH`, `J_SET AREA=.08`
- `I_SET=5.6 µA`
- `R_Q=2 Ω`, `L_Q=4.0 pH`, `J_Q AREA=.50`
- `L_F=20.0 pH`, `R_F=10 Ω`, `K_QF=.90`, `K_FO=.90`
- `L_CTL=4.0 pH`, `J_OUT AREA=3.0`, `I_OUT=275 µA`
- `R_OUT_SH=3 Ω`
- `R_SRC=.75 Ω`, `L_INJ=2.0 pH`

All new values are hypotheses, not literature or prior measured parameters.

## Gate 0–4 pre-run requirements

1. **Topology closure**：every AFQ node has a declared DC path or declared
   inductive/JJ loop path to ground; KCL for `J_SET`, `J_Q/R_Q/L_Q`, `L_F/R_F`,
   `J_OUT`, current-steering output and DCSFQ `a` is recorded. Any floating node,
   undefined return or hidden common-mode bias path is `PRECHECK_NO_GO`.
2. **Actual `jjmit` reconstruction**：recompute `Ic`, `C`, `RN`, `R0`, intrinsic
   `βc` and external-shunt `βc` from the copied model. Do not reuse hand estimates.
3. **No-input stability**：analytic DC/small-signal ratios must not show an
   already-supercritical static point or missing equilibrium. `J_OUT` near-critical
   bias is a hard risk; the first matched control is also a no-read startup check.
4. **Discrimination estimate**：using R1a raw `I(L_TX)` and declared winding
   polarity, report coupled current/flux, read1/read0 margin and reflected loading.
   `I>Ic` is not an event criterion.
5. **Active-output scale**：first-order loaded current division must contain an
   independent bias-powered boost and must not remain single-digit/tens-of-µA
   without a nonlinear mechanism. It is not a DCSFQ success prediction.

## Matched cases

- `logical1-read`: logical1 write, canonical positive READ
- `logical0-read`: logical0 write, canonical positive READ
- `logical1-read0-control`: logical1 write, READ amplitude zero
- `logical0-read0-control`: logical0 write, READ amplitude zero

All cases use identical topology, `dt=0.0125 ps`, stop `170 ps`, source PWL timing,
loads and probes. Windows: PRE `[80,90) ps`, activity `[94,130) ps`, POST
`[150,170) ps`; read window `[96,105) ps`.

## Required probes

Direct AFQ `P/V/I`: `B_DET`, `B_SET`, `B_Q`, `B_OUT`. Also direct currents through
`L_TX`, `L_S`, `L_Q`, `L_F`, `L_CTL`, `L_INJ`, `R_Q`, `R_F`, `R_SRC`, `I_DET`,
`I_SET`, `I_OUT`. Frozen DCSFQ `B1/B2/B3 P/V/I`, `I(L1)`, `V(DCS_A)`, `V(DCS_Q)`;
canonical `SL/N6/I(L_SL)`, `JM1/JM2`, `JS1/JS2` and relevant BVM branches.

## Event and stage criteria

Any complete-event claim requires a continuous monotonic unwrapped phase segment,
same-JJ/same-segment voltage area consistent with the phase, and bounded post/retrap.
Voltage peak, current above `Ic`, activity range, or phase range alone is insufficient.

- Stage 1 `DETECTOR_PRESERVED`: B_DET read1 remains strongly complete and read0/
  controls retain margin; BVM source/storage guards remain acceptable.
- Stage 2 `ACTIVE_STATE_COMPRESSION`: read1 produces one bounded AFQ regenerative
  sequence, read0/controls zero, no free-running/multifire.
- Stage 3 `ACTIVE_GAIN_ESTABLISHED`: loaded DCSFQ input drive is quantitatively above
  R1a passive `5.564 µA`, with relation to `68.4/110.2/300 µA` references reported.
- Stage 4 `DCSFQ_ONE_SHOT`: read1 B3 exactly one complete local event; read0/
  controls zero; post retrap and no second event.

## Predeclared stop/verdict rules

Stop at the first valid hard result: `PRECHECK_NO_GO`, `DETECTOR_LOADING_FAILURE`,
`ACTIVE_STAGE_NO_TRIGGER`, `ACTIVE_GAIN_ESTABLISHED_DCSFQ_SUBTHRESHOLD`,
`DCSFQ_ONE_SHOT_PASS`, `MULTIFIRE`, `NONSELECTIVE_TRIGGER`, `FREE_RUNNING`,
`BACK_ACTION_FAILURE` or `INCONCLUSIVE`. Failed raw is retained. No post-result
change to any AREA, bias, K, L, R or DCSFQ parameter.

`DCSFQ_ONE_SHOT` is local B3 evidence only and is not downstream SFQ/JTL delivery.
