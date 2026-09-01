# BVM_QB_IDLE_AND_READ_BOUNDARY_STATE_DECOMPOSITION_V1

## Scope

这是一个 `EXISTING_RAW_ONLY` 的 QUICK 分析。只读取父矩阵中同一工作点的三份
已有 raw：

1. `A`：canonical BVM → 12×320 JSL → ground，作为 grounded-JSL source reference；
2. `B`：把同一 source 波形理想电流重放给 QB；
3. `C`：canonical BVM → 12×320 JSL → physical QB。

这里的 A 是带 12×320 JSL 接地端的源参考，不是 unloaded/open-circuit BVM。
本轮不运行 JoSIM、不改网表、不改参数、不修改 raw，也不继续 magnetic coupling。

## Fixed analysis before reading the outcome

使用真实 time 列的半开区间 `[start, end)`，不按结果重新选窗：

| Window | Time (ps) | Intended meaning |
|---|---:|---|
| W0 | [2, 9) | QB bias established, before BVM initialization |
| W1 | [10, 21) | BVM initialization |
| W2 | [80, 90) | settled idle / stored-state |
| W3 | [95, 110) | READ |
| W4 | [110, 130) | post-READ settling |

另外预先登记父实验的历史核对窗口 `[94, 130)`，只用于复核冻结的
`I(B_LD1)` 对照数值，不替代 W3。

所有成对比较要求 exact time grid，禁止隐式插值；差值定义为
`right - left`。原始 `P(...)` 仍以 rad 保存，显示 turns 时才除以 `2π`。

## Questions and signals

### Q1: Does physical QB alter BVM state?

Compare A↔C in W0–W4 for:

- `P(B_JM1|XBVM1)`、`P(B_JM2|XBVM1)`；
- `P(B_JS1|XBVM1)`、`P(B_JS2|XBVM1)`；
- supporting `I(L_PSL|XBVM1)`、`I(L_SL|XBVM1)`、`I(B_LD1)`、
  `I(B_LD12)`、`V(SL1)`。

In W3, `I(B_LD1)` must report positive peak, positive area, negative area,
signed area, peak time, RMS and exact-grid pointwise difference. These are
current-waveform diagnostics, not SFQ counts.

### Q2: Is QB preloaded before READ or does it diverge during READ?

Compare B↔C in W2 and W3 for QB internal signals:

- phase: `P(BJS|XBQ)`、`P(BJL1|XBQ)`、`P(BJL2|XBQ)`；
- current: `I(L1|XBQ)`、`I(LIN|XBQ)`、`I(RB|XBQ)`、`I(L2|XBQ)`。

For phase, report median, p2p and exact-grid difference in turns. For current,
report mean, p2p, RMS and max absolute difference in physical units.

## Bounded competing hypotheses

- `H-A`：persistent QB-bias backfeed changes BVM idle state；
- `H-B`：QB mainly changes BVM initialization，留下 persistent stored-state difference；
- `H-C`：BVM stored state largely preserved，but JSL/QB interface preload differs；
- `H-D`：pre-READ states approximately preserved，dominant incompatibility emerges during READ。

每条结论必须区分 `OBSERVED`、`PHYSICS-BASED INFERENCE` 和 `UNKNOWN`，不强行
选择唯一机制。局部 JJ phase turn 不等同于下游收到的 SFQ。

## Visualization and stop rule

只生成一张紧凑的 `plots/RESULT_OVERVIEW.html`，沿用项目既有命令：

```text
scripts/josim-plot2.py -t sep_comb -c dark -j 2pi
```

图中只保留五组关键 paired signals：BVM `I(B_LD1)`、BVM `JM2` phase、QB
`BJS` phase、QB `L1` current、QB `BJL1` phase。分析完成后状态固定为
`QUICK_AMBIGUOUS` / `AWAITING_USER_REVIEW`，并在 `RESULT_BRIEF.md` 后停止；
不执行下一步选项。
