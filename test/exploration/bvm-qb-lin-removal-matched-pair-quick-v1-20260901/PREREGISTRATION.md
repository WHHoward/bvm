# BVM_QB_LIN_REMOVAL_MATCHED_PAIR_QUICK_V1

## Scope

这是一个已授权的最小物理 QUICK probe，不是优化、sweep 或 Formal Gate。目标是
区分 QB 输入边界 `Lin=0.8 pH` 是否影响 physical `BVM→12×320 JSL→QB` 的动态
接口匹配。唯一科学 intervention 是：

- P0/I0 baseline：QB `Lin=0.8 pH`；复用父矩阵已有 raw；
- P1/I1 candidate：删除 `Lin`，把原 node 1 合并到 QB `IN`；各运行一次；
- I1 replay 输入必须与 I0 完全相同的 frozen grounded-source `I(B_LD1)` waveform，
  不 reshape、scale、hold、retime、resample 或 interpolation。

本任务严格只新增两个 science runs：P1 physical 与 I1 ideal replay。P0/I0/G 只读
复用。不得修改 `circuits/qb/bq_cell.cir`、canonical BVM、JSL、BJs、bias、L1/L2、
READ width、timestep、load、JTL/T1 或 magnetic coupling。

## Frozen conditions

| item | value |
|---|---|
| READ | 13 ps, logical1/read |
| source | canonical BVM → 12×320 JSL |
| QB bias | `IBIAS=35 uA` |
| output load | `R_LOAD=10 ohm` to ground |
| timestep / stop | `0.0125 ps / 170 ps` |
| baseline QB | `Lin IN 1 0.8p` |
| candidate QB | `Lin` removed; `BJs IN 2 jjmit area=0.5` |
| solver | `build/josim-cli v2.7.2837d13` |

Fixed windows use half-open semantics:

- W2 pre-READ idle: `[80,90)` ps;
- W3 READ waveform comparison: `[95,110)` ps;
- W4 post-READ observation: `[110,130)` ps;
- BJL2 strict activity: `[95,115)` ps;
- BJL2 post: `[115,130)` ps;
- BJL2 post tail: `[125,130)` ps.

W3 remains the waveform comparison window and is not used as the strict activity cutoff.
The BJL2 strict result is same-JJ local phase/area compatibility arithmetic, not an SFQ
count, downstream delivery, or system Gate.

## Questions and outcome rule

The primary comparison is matched physical-to-ideal gap:

`D0(signal) = RMS(P0, I0)` and `D1(signal) = RMS(P1, I1)` in W3,
with `gap_reduction = 1 - D1/D0` and no interpolation. Primary QB signals are
`P(BJS)`, `I(L1)`, `P(BJL1)`, `I(L2)`, and `P(BJL2)`. Supporting input/bias signals
are reported only where the branch exists; candidate `I(Lin)` is not fabricated.

Source-side comparison is G↔P0 versus G↔P1 for `I(B_LD1)`, `I(B_LD12)`,
`I(L_PSL|XBVM1)`, and `V(SL1)`, with BVM phase support `JS1`, `JS2`, and `JM2`.

The directional threshold is a pre-registered `20%` exact-grid W3 RMS-distance reduction;
it is not a universal physical tolerance. The four allowed Quick labels are
`QUICK_PROMISING`, `QUICK_NO_EFFECT`, `QUICK_OPPOSITE`, and `QUICK_AMBIGUOUS`.
No label promotes the route automatically.

## Evidence boundary

Report each of P0/I0/P1/I1 with raw QA, fixed-window statistics, same-JJ BJL2 P/V strict
arithmetic, complete-segment count, second-event check, and post boundedness. Keep these
separate:

- observed source/internal waveform changes;
- derived exact-grid distances and gap reductions;
- physics-based inference about input matching or dynamic isolation;
- unknowns: controls, sweep, timestep ladder, hardware behavior, JTL/T1 delivery and
  universal Lin optimum are not addressed by this Quick.

The final state after the two runs is `AWAITING_USER_REVIEW / STOP`; no next Lin sweep or
other experiment is authorized automatically.
