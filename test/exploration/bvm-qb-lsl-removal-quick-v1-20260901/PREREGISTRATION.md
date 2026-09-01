# BVM_QB_LSL_REMOVAL_QUICK_V1

## Scope and single intervention

这是一个用户明确授权的物理 `QUICK PROBE`，只运行一个新 science case：
`13 ps / 12×320 / logical1_read`。唯一科学 intervention 是：

- BASELINE：canonical BVM 的 `L_SL = 0.4 pH`；
- CANDIDATE：删除 `L_SL`，将 `R_SL` 输出节点直接作为 `SL` port。

canonical `circuits/bvm/bvm_cell.cir` 不修改。candidate 使用本目录的
`inputs/bvm_cell_lsl_removed.cir` 和 candidate deck；其它 BVM/QB/JSL 参数、
source timing、模型、步长和输出负载保持不变。候选 deck 仅删除已不存在的
`I(L_SL|XBVM1)` print probe，保留 `V(SL1)` 作为 source-port 观测。

baseline 不重跑，复用父矩阵中已有且 hash/provenance/solver/spec 一致的
physical raw。另以已有 grounded-JSL source 和 ideal replay QB 作为只读参考。
本轮不加入 logical0、no-read、timestep ladder、其它 L_SL、8×500、JTL、T1
或 magnetic coupling。

## Fixed windows and evidence chain

使用真实 CSV time 列的半开窗口，不按结果选窗：

| Window | interval | purpose |
|---|---:|---|
| W2 | [80,90) ps | pre-READ idle / stored-state safety |
| W3 | [95,110) ps | READ dynamic mismatch |
| W4 | [110,130) ps | post-READ observation |

核心链条为：`BVM JS1/JS2 → L_PSL/source current → JSL current → QB Lin →
BJs → L1 → BJL1 → L2 → BJL2`。所有 exact-grid 比较均使用 `right - left`，
不插值；raw `P(...)` 为 rad，phase turns 只由 continuous unwrap 后除以
`2π` 得到，不称 SFQ count。

## Required directional measurements

### Source/BVM

比较 baseline physical 与 LSL-removed candidate，并各自相对 grounded-JSL
reference，记录 JM1/JM2/JS1/JS2 phase 的 W2/W3/W4 median、p2p、endpoint
displacement 和 exact-grid difference；记录 `I(L_PSL|XBVM1)`、`I(B_LD1)`、
`I(B_LD12)` 与 `V(SL1)`。

W3 的 `I(B_LD1)` 必须报告 positive peak、peak time、positive area、negative
area、signed area、RMS 和 baseline-candidate max pointwise difference。current-time
area 只是 waveform diagnostic，不是 SFQ quantity。主要 source 判据是
`|I_candidate-I_grounded|` 是否以 exact-grid trajectory distance 减小，不能只
看 scalar attenuation。

### QB internal trajectory

以已有 ideal replay QB 为 target，比较 baseline/candidate 的 `P(BJS|XBQ)`、
`I(L1|XBQ)`、`P(BJL1|XBQ)`、`I(LIN|XBQ)`、`I(L2|XBQ)`、`P(BJL2|XBQ)`，至少
报告 W2/W3 的 phase median/p2p/trajectory distance、current mean/p2p/RMS/maxabs
和 exact-grid target distance。`I(RB|XBQ)` 作为固定 bias support 保留。

`BJL2` 使用 shared `bvmtools.sfq` 的同一 JJ、同一 `P(BJL2|XBQ)`/
`V(BJL2|XBQ)`、同一方向、同一实际时间网格和 task-local frozen compatibility
算术；报告最大同一 continuous monotonic segment、phase turns、同段
`∫Vdt/Φ0`、residual、segment count 和 classification。它只是 local diagnostic，
不升级为 Formal PASS、下游接收或系统 Gate。

## Outcome rule and interpretation

Outcome rule 在 candidate run 前固定于 `experiment.yaml`：candidate 必须先满足
W2 pre-READ safety，再由多个 source/QB exact-grid RMS trajectory distances 同时
向两个只读 reference 改善至少 20%，且 BJL2 不变差，才能标
`QUICK_PROMISING`。若各 primary distance 均在 ±20% 内为 `QUICK_NO_EFFECT`；若
source 或 QB primary distance 至少恶化 20% 且没有跨层一致改善为 `QUICK_OPPOSITE`；
否则为 `QUICK_AMBIGUOUS`。

这些是本任务的方向性 Quick 分类，不是全局物理容差。无论结果如何，不声称
`L_SL` 是唯一根因、不声称复现论文 Fig.7、不声称完整 BVM→QB/JTL/T1 或硬件
已解决。允许的最强措辞是：在这个固定 Quick 条件下，移除 `L_SL` 是否使
physical BVM→JSL→QB READ trajectory 发生方向性变化。

完成 candidate、QA、分析、`RESULT_BRIEF.md` 和唯一 compact classic overview 后，
写入 `AWAITING_USER_REVIEW` / `STOP`；不自动 Promotion 或下一实验。
