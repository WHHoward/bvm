# BVM_QB_SINGLE_BVMSIM_BVM_TO_QB_MATCHED_2X2_QUICK_V1

## 1. What changed

本次只建立并运行了一个 single historical BVMSim BVM → QB 的匹配 2×2 Quick：

- `S0-R` / `S1-R`：单个 `BVMSim/bvm_cell.cir`，端接 11 个 `B_LD4_01..B_LD4_11` 加 `BVMout`，共 12 个 area=3.2 JJ，接 `BQ_BVMSIM_V1` 和 10 Ω。
- `S0-J` / `S1-J`：相同 BVM、sensing line 和 QB，改为 `QB → JTL1..JTL6 → 10 Ω`。
- S0/S1 只改变现有 BVMSim 写入波形的 WL/BL 符号；QB 偏置固定为 250 µA。
- 所有条件使用 `.tran 0.025p 200p`，从 t=0 保存。

QB 电路文件为 [`circuits/qb/bq_cell_bvmsim_v1.cir`](../../../circuits/qb/bq_cell_bvmsim_v1.cir)，接口为 `BQ_BVMSIM_V1 IN OUT BIAS`。原始 BVMSim BVM 未修改，也没有替换成 canonical BVM。

## 2. What held fixed

本阶段固定了 historical BVMSim BVM、12-JJ sensing line、BVMSim QB 参数和 250 µA 外部 bias、BVMSim `jtl2.cir`、正读脉冲形状与时序、solver 和时间步长。`BVMSim/bvm_cell.cir` 与 canonical `circuits/bvm/bvm_cell.cir` 仍是不同 authority；例如 historical BVMSim 的 `R_JM1=8 Ω`，canonical BVM 为 `6 Ω`。

没有运行 canonical BVM、4-BVM、单 BVM 参数扫描、QB bias sweep、JTL 重设计、磁耦合、T1 或自动 follow-up。

## 3. Why tested

问题是区分：

1. BVM 波形是否在 QB 内产生可分离且 retrapped 的本地事件；
2. QB 活动是否以离散事件身份逐级通过六级 JTL；
3. JTL 负载是否改变 QB 的 BJ2 operating trajectory。

事件分析采用本实验局部预注册规则：电压活动 → 静默间隔分段 → 同一 JJ 的相位变化与 `∫Vdt/Φ0` → 前后低电压/retrap。没有把整窗相位圈数当作 SFQ 数量。

## 4. What happened

- 四个 raw 均成功生成并通过基本 QA：7999 点，`0..199.975 ps`；四个条件时间网格逐点一致。实际保存网格包含一个 `0.05 ps` 间隔，其余约为 `0.025 ps`，分析使用实际网格而没有插值。
- `BVMout` 在四个条件都没有 complete phase/area candidate；全窗最大 terminal phase candidate 只有约 `1.43×10⁻⁴` 圈。QB 的早期活动不能直接当成 BVM read 输出。
- S0-R 和 S0-J 的 BJ2 都没有 complete candidate；BJ2 最大候选分别约 `0.1493` 和 `0.1429` 圈。
- S1-R 的 BJ2 是一个从约 `0.175 ps` 延伸到 `95.3 ps` 的单一候选，`Δφ/(2π)=2.147763` 圈、`∫Vdt/Φ0=2.147770` 圈，没有 retrap；S1-J 的 BJ2 是一个从约 `0.15 ps` 到 `104.2 ps` 的单一候选，分别为 `1.142140` 和 `1.142145` 圈，也没有 retrap。两者都不是 clean separated SFQ。
- S1-R/S1-J 的 QB 链中第一个完整候选都先出现在 `BJ1`，约 `0.1 ps`；它在 READ 之前已经开始，并跨越了写入/读出关联窗口。没有出现一个 onset 位于 READ 窗口内、且有独立 retrap 的 QB candidate。
- S1-J 中 JTL1–JTL6 的 B01 和 B02 各自都表现为一个长的 complete phase/area segment，但 clean separated event count 全部为 0；因此目前只能说连续活动被各级看见，不能说离散 SFQ event identity 被传输了。BJ2 从 10 Ω 到 JTL 负载的 READ 窗口基线对齐相位差最大约 `0.5643` 圈、RMS `0.2230` 圈，说明 S1 下存在明显 load backaction；S0 对应最大约 `0.00455` 圈、RMS `0.00189` 圈。

## 5. Physical meaning

当前证据更支持“250 µA QB 偏置下很早出现连续内部活动；S1 的活动在不同负载下被改变，并在 JTL 各级形成对应的连续活动段”这一有限描述。它没有支持 `READ1 → 一个或多个 clean separated SFQ → 六级 JTL 离散传输`。这是本次 A001 按当前 raw 和新的电压静默间隔规则重新得到的 classification，不是沿用旧 Stage A 结果。本结果的 primary classification 是：

`CONTINUOUS_MULTI_TURN_RUNNING_STATE`

Quick label：`QUICK_OPPOSITE_OR_AMBIGUOUS`。

可视化纠正：初版合并标签把条件前缀放在 `P/V/I` 之前，导致 `josim-plot2.py -j 2pi` 未能识别相位列。现已将条件改为信号标签后的后缀并重新生成五个 HTML；例如修正后的 `S1-J` `P(BJ2|XBQ1)` 最大值为 `1.15520339528` turns，约 `7.18 rad` 的原始值不再被误显示为 turns。raw CSV、metrics 和物理分类未改变。

## 6. What it does NOT prove

这不是 canonical BVM 兼容性结论，也不是对单 BVM 普适行为、工艺裕量、时间步收敛、论文机制身份或唯一 QB operating mechanism 的证明。它也没有证明 BVM 没有任何作用；只是当前 BVMout 的量化 terminal phase activity 很小，而 QB/JTL 的主要候选在 read 之前已开始。

## 7. Current status

Artifact status：`VALID`。物理结论为本 fixture 的 exploratory observation，不是 Formal Gate 或 paper claim。

Human gate：`AWAITING_USER_REVIEW`；`user_reviewed=false`；`next_step_authorized=false`；`automatic_next_experiment=false`；`stage_b_authorized=false`。

关键文件：

- [`analysis/metrics.json`](analysis/metrics.json)
- [`analysis/provenance.json`](analysis/provenance.json)
- [`analysis/REVIEW.md`](analysis/REVIEW.md)
- [`analysis/human-gate.yaml`](analysis/human-gate.yaml)
- [`plots/RESULT_OVERVIEW.html`](plots/RESULT_OVERVIEW.html)
- [`plots/RESULT_BVM_INTERFACE.html`](plots/RESULT_BVM_INTERFACE.html)
- [`plots/RESULT_QB_INTERNAL.html`](plots/RESULT_QB_INTERNAL.html)
- [`plots/RESULT_TRANSPORT_VOLTAGE.html`](plots/RESULT_TRANSPORT_VOLTAGE.html)
- [`plots/RESULT_TRANSPORT_PHASE.html`](plots/RESULT_TRANSPORT_PHASE.html)

## 8. Possible next options

1. 用户先审阅本次四条件 raw、metrics 和聚焦图。
2. 若仍需隔离 BVM 贡献，再单独授权一个明确的 bias/read 控制 Quick。
3. 若需要比较 canonical BVM，再另行授权独立实验；本次没有执行。
