# Numerical and adversarial review

## Scope

这是对本轮 crossover artifact、计算和解释边界的 task-local review，不是 Formal scientific gate，也不是外部审稿结论。审阅重点是防止把“4/5 trajectory split”误写成未经验证的事件计数或唯一根因。

## Numerical review

- `P(...)` 按 JoSIM 原始 rad 处理；只有对同一 junction 做 continuous unwrap 后，才以 `rad/(2*pi)` 显示 turns。
- BJ2 phase 与 `V(BJ2)` 的面积使用同一 run、同一 branch、同一 `[110,170) ps` trajectory window 和实际存储时间网格；没有插值，也没有把 phase displacement 当作 clean SFQ count。
- 四组 raw 都有 1549 行，时间范围为 45.0--199.9 ps；common-probe 比较使用 157 个共同列和 exact stored time grid。四组 float grid 与 time tokens 均一致。
- `I(LIN|XBQ1) - Σ I(L_SL|XBVMn)` 使用共享 `bvmtools.kcl.linear_kcl_residual`，方向约定明确为 LIN 减去四个 LSL；四组 `[110,160) ps` 最大残差只有 0.00006--0.00007 µA，独立 checker 复算一致。
- `R_S`/`L_S3` 在 O−/N−/N+ 的 full-probe raw 中可见，但不可修改的 O+ historical raw 没有这两列。它们没有被填充、替代或从缺失列推断，故四条件层面的 R_S/LS3 结论保持 UNKNOWN。
- 新 raw 的 solver、header、model-warning、NaN/Inf、重复列和时间网格 QA 均通过。存储间隔出现 0.1/0.2 ps 是 JoSIM 输出网格事实；requested timestep 仍为 0.1 ps。

数值审阅结论：**artifact-level PASS**。这不等于物理机制或 clean-event 结论 PASS。

## Adversarial review

- **旧证据被覆盖？** O+ 与 N− 使用的历史 raw 未重跑/覆盖；四个 raw 的 SHA-256 已记录，且 O− 与 N− raw hash 相同。
- **deck 偷换了物理条件？** 静态 preflight 报告中 physics difference count 为 0；只允许 history waveform 变化和 O− 的 observability-only print additions。BL、WRITE1、final READ1 与 history 窗外 source 均 exact。
- **是否只比较了最终 QB？** 没有。四条件同时比较 BVM internal、四条 LSL、LIN/QBIN 和 BJ2 trajectory；报告同时列 history pairs 与 context pairs。
- **是否把新增的 R_S/LS3 探针伪装成四条件证据？** 没有。不可修改的 O+ historical raw 缺少这两列，分析明确将其排除出 common-probe 聚合并标记为 UNKNOWN。
- **是否把 70 ps 前的偶然不一致误判为历史效应？** O+ vs O− 和 N+ vs N− 在 `[45,70) ps` 的 157 个 common probes 逐点 exact。
- **是否使用同一个分析器自证？** `independent_check.py` 直接重新读取 raw CSV，独立计算 pre-70 parity、history-pair exactness、context nonzero、BJ2 markers 和 LIN closure，不读取 `metrics.json` 或 `REPORT.md`。
- **是否把整数 crossing 当 SFQ count？** 没有。报告将 crossing 和 cumulative turns 明确标为 trajectory markers；O+/N+ 的最大 monotonic segment 约 3.98 turns，O−/N− 约 4.03 turns，故不声明 clean separated SFQ event count。
- **是否从四层分组跳到了唯一根因？** 没有。结论限于当前模型、stimulus、load 和 `dt=0.1 ps` 下的有界 history-vs-context 因果支持；hidden state、收敛、唯一 root cause、硬件和论文机制仍是 UNKNOWN。
- **可视化工具失败是否污染物理结论？** 首次 comparison HTML 生成只在链接路径阶段失败；修复后用同一 raw 重新生成并通过，未发生新的 JoSIM 调用。

## Review disposition

`O+≈N+` 与 `O−≈N−` 在四个关键层级同时成立，且两组 context pair 均非零；因此 previous-read preconditioning 在本轮受控 crossover 中得到强支持，可作为 4/5 trajectory split 的主要候选驱动因素。该表述不是“history 是唯一原因”的证明，也不是 SFQ transport Gate。

当前 gate：`AWAITING_USER_REVIEW`。不自动开始任何后续实验。
