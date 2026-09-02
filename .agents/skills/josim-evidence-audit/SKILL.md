---
name: josim-evidence-audit
description: Interpret JoSIM raw evidence for phase, voltage-area, SFQ event, JTL transport, convergence, or scientific claims. Use only when a Quick result needs physical interpretation; plots and execution success are never sufficient.
---

# JoSIM 证据审计

涉及相位、SFQ、事件数、传播或 Gate 时，先读
references/phase-evidence-contract.md；本入口只保留稳定判断边界，不复制完整
算法或易变项目状态。

## 不可替代的核心

- raw CSV、网表、日志、版本和匹配控制是证据；图和摘要只是展示层。
- JoSIM P(...) 是 raw radians。保留 Δφ_rad，再计算 Δφ_rad/(2π)；一结
  相位圈不自动是 SFQ 或闭环 fluxoid。
- 事件必须绑定同一 JJ、同一端点/方向、同一连续 monotonic segment，并用
  实际时间列的同 JJ V(...) 面积交叉检查。
- Vpeak、I>Ic、导数过阈值、whole-window turns、fast_events 都不是 SFQ count。
- local activity 不等于 loaded downstream reception；JTL 传播必须逐级检查，
  并确认因果顺序、负载和事件后不持续 running。
- 缺少方向、端点、稳定窗、read0/零输入、适用容差或收敛证据时只能
  INCONCLUSIVE，不能用“没有看到”补齐证据。

## 审计输出

用紧凑表格分别报告：

1. Artifact：文件/时间轴/列/日志是否有效；
2. Observed：raw 直接读到或独立重算的事实；
3. Inference：与事实相容但未被对照证明的解释；
4. Unknown：缺失的控制、端点、负载、收敛或机制；
5. 允许的最强措辞与 PASS/FAIL/INCONCLUSIVE/INVALID。

关键数字必须注明单位、窗口、信号方向和 raw 路径。结论只限于声明的模型、
激励、负载、参数、时间步和指标版本，不把仿真写成硬件实测。

## 共用实现

优先调用 scripts/bvmtools.raw、phase、sfq、waveform 和 compare。共享 helper
的回归通过不等于电路 Gate 通过；不要在本 skill 或实验目录重写事件检测器。
需要数值单位、符号、积分、窗口或精度的独立复核时，显式调用保留的
reviewer-numerical 专项技能。
