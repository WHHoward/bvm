# Visualization Reading Guide

本指南由 alignment manifest 生成，基线 HEAD：`3e714f3fdd593511971136ee470ec0418d775d24`。

| 想确认什么 | 实验 | 先打开 | 看什么 | 不能据此推出什么 |
|---|---|---|---|---|
|我想确认 scaled QB 的输入窗口|QB-Q0|qb-q0-standalone-current-quantized-event-20260824/plots/scaled-comparison.html|看 scaled 0/45/68.4/90 的 BJL2 连续轨迹；paper 只作历史对照。|不推出 canonical BVM compatibility。|
|我想看 paper-JSL 是否驱动 QB|PAPER-SL-Q1|paper-sl-q1-20260824/plots/qb-replay/comparison.html|看 BJs/BJL1/BJL2 的 read1/read0/control 分离。|不要把 paper-JSL source 图当 QB response。|
|我想比较 37.5 与 40 µA|PAPER-SL-Q2|paper-sl-q2-20260824/plots/bias-37p5-vs-40-comparison.html|看 BJL1/BJL2 phase 与 current。|不能只看 37.5 单点。|
|我想看 L1/L2 factorial|Q2–Q5|paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html|看四点的 BJL1/BJL2 与 routing current。|phase range 不自动等于 event。|
|我想看 output boundary|QB load-boundary|qb-load-boundary-matrix-20260824/plots/q0-complete-boundary-comparison.html|看同一 Q0 的 10Ω/OPEN/JTL/parallel。|Q5 boundary 是 secondary comparison。|
|我想看 JTL polarity/convergence|JTL methodology|jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-timestep-comparison.html|同时打开 R11 与 reverse。|严格 Gate 仍 INCONCLUSIVE。|
|我想看 R13 conditioning|R13-A|bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-vs-c1-vs-c2-vs-c3.html|逐条件查看 raw/C1/C2/C3 的 B3。|理想 replay 不是 physical implementation。|
|我想看 Q5 接 JTL 的变化|PAPER-SL-Q6|paper-sl-q6-qb-jtl-compatibility-20260824/plots/q5-standalone-vs-q6-coupled.html|直接比较 BJL1/BJL2/V(OUT)。|不把耦合系统成功等同 isolated QB event。|

## Phase semantics

- `continuous_absolute`：原始 JoSIM P(t)/(2π) 连续相位轨迹；未基线相减、未按脉冲归零；不等于 SFQ 计数。
- `relative_to_baseline`：相对登记 baseline 的 [P(t)-P_pre]/(2π)。
- `event_delta`：登记同一 JJ、同一 monotonic segment 的 ΔP/(2π)。
- `settled_well`：pre/post 稳定势阱变化 Δn；不能由连续轨迹本身替代。
