# JTL_TRANSPORT_GATE_V1 — methodology checkpoint

日期：2026-08-24  
父级 accepted HEAD：`edf9b6d6c9a26c999a9f95f8ca604993475c51d4`

本 checkpoint 只消费已经提交的 CSV、netlist、metric 规格和 provenance hash；不运行
JoSIM，不改变任何 physical circuit，也不重写既有 raw。它冻结两个不同层级的
证据：`STRICT_LOCAL_EVENT` 与 `JTL_TRANSPORT_EVENT`。

## 1. Strict local event（保持既有口径）

对同一颗 JJ、同一端点、同一方向和同一 CSV 时间窗：

1. 对 raw `P(...)` 做 continuous unwrap，随后用 `Δφ/(2π)` 报告 turns；
2. 在一个 continuous monotonic segment 中，绝对 phase change 至少 1 turn；
3. 同一 segment 的直接 `V(JJ)` 梯形积分除以 `Φ0` 与 phase change 同号且残差在既有
   segment-local rule `max(0.02, 0.05*|turns|)` 内；
4. segment 后检查 bounded/retrap，不能由后窗继续产生额外完整 segment。

这只证明局部 JJ 轨迹，不自动证明 downstream SFQ delivery。大于 1 turn 的 segment
可以记录为 multi-turn local activity，但不能被称为 exactly-one。

## 2. JTL transport event（独立于 strict local event）

under-damped JTL JJ 可能表现为：稳定前井 → barrier crossing/ringing → 稳定后井。
因此，即使最大严格单调 segment 小于 1 turn，也可以单独报告 transport evidence；但
full-window 约一圈本身不能充当 strict local event。

单颗 JTL JJ 的 transport-qualified 条件为：

- pre/post phase p2p 有界；
- pre→post median phase change 是预期方向的一个相邻井；
- activity-window endpoint phase change 同样接近一个相邻井；
- activity-window 直接 `∫Vdt/Φ0` 与该同一 JJ 的 endpoint phase change 一致；
- 不出现 ±2 或更高 integer-well transition；
- post window 没有额外完整 local segment；
- onset marker 存在，并且四颗 JJ 的 onset 顺序保持
  `JTL1.B1 → JTL1.B2 → JTL2.B1 → JTL2.B2`。

整条 two-cell chain 只有在四颗 JJ 都满足上述条件时，才可标记
`JTL_TRANSPORT_PASS`。这仍然是冻结 JTL/ideal replay fixture 的 transport evidence，
不是 physical QB→JTL interface 或 T1 evidence。

## 3. 容差来源与预注册值

容差由本批已接受的 R11 standard-JTL positive control、M1 ideal Q0 replay、M5-PC
和 pulse-5 replay 的实际数值决定；不是为某个待判样本单独选择。

| quantity | frozen tolerance / marker | basis |
|---|---:|---|
| one-well platform delta | `0.02 turn` | R11 四颗 JJ 的 mean platform delta 最大偏离 +1 为 `0.013484 turn`，向上取整 |
| one-well activity phase/area residual | `2e-4 turn` | 参考样本最大 full-window residual 为 M1 B1 的 `1.91204e-4 turn`，向上取整 |
| pre-well p2p | `0.01 turn` | 参考集合最大 pre p2p 为 `0.00626138 turn`，留有数值余量 |
| post-well p2p | `0.07 turn` | 包含已接受 bounded M5-PC reference 的最大 post p2p `0.0657819 turn` |
| onset marker | `t50`：从 pre-mean 出发的 signed `0.5 turn` crossing | 只用于 timing/order；不是 event threshold |
| downstream onset order slack | `0.5 ps` provisional | 覆盖当前 reference 的采样量级；由于 M1 使用约 `0.1/0.2 ps` 间隔且没有 refinement uncertainty，不能升级为 global tolerance |

其中 full-window phase/area 的一-well判断仍使用 `0.02 turn`；`2e-4` 只用于同一
window 内同一 JJ 的 `phase-area` 一致性。所有时间使用 CSV 的实际 `time` 列。

这些是本批 retrospective/task-local provisional bands，不是 resolution-independent
或跨拓扑的 Authority metric freeze；正式 Gate 还需要同一 JTL fixture 的 timestep
ladder/repeatability evidence。

## 4. 预注册对象和边界

对象为：

- R11 standard-JTL positive control；
- M1 Q0 `V(OUT)` ideal replay；
- accepted pulse-5 original-polarity ideal replay；
- accepted pulse-5 reverse-polarity replay；
- M5-PC scaled-JTL positive control，用于发现旧 predicate 的 two-well 问题。

反极性 replay 是 polarity diagnostic，不是 logical0 control。M1 与 pulse-5 是
ideal voltage-source counterfactual，不是 physical Q0→JTL 接口。M5 的 topology/scale
也不等同于 standard JTL。

## 5. 停止规则

本批只做方法学重算和文档同步。不得运行 JoSIM、不得做 R/L/Ic/bias sweep、不得
连接 T1、不得修改 QB/JTL topology。physical interface 是否可行留给后续独立
architecture review。
