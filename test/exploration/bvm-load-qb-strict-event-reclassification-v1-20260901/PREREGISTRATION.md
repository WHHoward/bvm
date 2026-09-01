# BVM_LOAD_QB_STRICT_EVENT_RECLASSIFICATION_V1

## 状态与范围

- 记录时间：`2026-09-01T14:56:16+08:00`
- 分析前 HEAD：`d1e5134ac40e60f39dc90fa1c294ef7b81a9c635`
- 模式：Exploration / deterministic evidence re-analysis
- 输入：`test/exploration/bvm-load-qb-matrix-v1-20260901/raw/`
- 输出：本目录；不改写输入 raw、旧报告或旧分类

本任务只重新计算已有 CSV 证据。禁止新的 JoSIM 运行、参数/网表/读时序
/BVM/JSL/QB 改动，也不加入 JTL、T1 或 magnetic coupling。source-only
CSV 只用于 provenance 和 JSL 系列电流等价性；严格事件 authority 只在
包含 QB 的 replay/physical CSV 上使用 `BJL2`。

## Provenance 预注册

分析开始前先做两组身份检查：

1. `paper-sl-l0-20260824/raw/logical1-read/run-01.csv` 与矩阵的
   `raw/source/9ps/12x320/logical1_read/run-01.csv` 比较 SHA-256、样本数、
   完整时间轴和第一份 `I(B_LD1)` 序列。重复表头的列按出现顺序处理；
   第一份是比较所用的列。
2. 旧 `paper-sl-q1-20260824` replay deck 与矩阵代表性 replay deck 比较
   `bq_cell.cir`、`jjmit.cir` 的字节/SHA，以及 IBIAS、R_LOAD、`.tran` 步长、
   `I_REPLAY` 两个端点/方向。只有这些检查全部通过，历史 strict 数值才可
   作为同一 fixture 的回归锚点；否则列出差异并将历史比较记为不可比。

## 窗口与列

- `ACTIVITY = [94 ps, 130 ps)`
- `POST = [140 ps, 170 ps)`
- 严格事件列：`P(BJL2|XBQ)`、`V(BJL2|XBQ)`；同一 raw、同一方向、同一
  选定 segment、同一时间样本
- `window_phase_delta_turns` 保留 activity 窗口连续相位首末端点差，作为
  窗口位移诊断；它不具有事件计数权力，明确满足
  `WINDOW_PHASE_DISPLACEMENT != EVENT_COUNT`。

## 冻结的严格算法

### 相位、分段和面积

1. 读取 JoSIM raw `P()` radians，先在整条 raw 时间序列上使用确定性的
   continuous unwrap（`numpy.unwrap` 默认 `π` 跳变判据）。不把相位样本或
   导数样本直接当作 SFQ。
2. 在窗口内对解包相位的相邻差取 `sign(diff)`，沿用已验证的
   PAPER-SL-Q1 `monotonic_runs` 实现：第一个非零符号作为当前方向；每个
   后续非零符号改变处切段；零差被视为中性，不触发反转。没有平滑、插值、
   重采样或手工合并，因此任意非零小 reversal 都保留为分界。
3. 分界采用实际 CSV 样本索引。反转所在的 turning-point 样本同时作为前一
   段终点和后一段起点；不生成分界处的插值样本。段端点因此是确定的
   `[first_selected_sample, last_selected_sample]`。
4. 每一段分别计算：

   ```text
   delta_phase_turns = (P_unwrapped[last] - P_unwrapped[first]) / (2*pi)
   voltage_area_turns = trapezoid(V_BJL2, actual_time_seconds) / Phi0
   phase_area_residual_turns = delta_phase_turns - voltage_area_turns
   ```

   `Phi0 = 2.067833848e-15 Wb`。面积只对该段的实际 CSV 时间点做梯形积分，
   不假定固定 dt；报告同时保留历史方向的 `area_minus_phase` 作为审计辅助。

### 冻结容差

这些是本任务在查看新矩阵分类前冻结的 task-local 容差，不是全局物理标准：

- `phase_area_residual_tolerance = max(0.05 turn, 0.10 * abs(delta_phase_turns))`
  （继承 PAPER-SL-Q1 已使用的 phase/area 一致性规则）
- 完整段必须 `abs(delta_phase_turns) >= 1.0 turn`、phase/area 同号且残差在
  上述容差内
- `clean_one_upper_turns = 1.15 turn`；完整段 `1.0..1.15 turn` 才能成为
  clean-one candidate
- `post_bounded_range_max = 1.0 turn`；`post_tail_window = [165,170) ps`，
  `post_tail_p2p_max = 0.25 turn`。`post_bounded` 只有在 POST 有效、没有
  POST complete segment、POST 总相位 range 不超过 1 turn 且 tail p2p 不超过
  0.25 turn 时为 true。这是有限窗口内 retrap/boundedness，不是无限时间稳定性。
- 回归数值比较容差：phase/area `1e-9 turn`，端点时间 `1e-9 ps`；这是
  结果复现检查，不是物理事件容差。
- source 的 JSL 系列电流等价性使用预注册的逐样本绝对数值容差
  `1e-13 A`；这是浮点数值比较，不是物理阈值。超过该容差才记为
  `SERIES_JSL_CURRENT_EQUIVALENCE = FAIL`。

### 分类规则

分类只看 BJL2 的上述 segment 记录：

- `NO_EVENT`：BJL2 在 activity 内没有可计算的非零单调段。
- `SUBTHRESHOLD`：有有效 activity 段，但没有 phase/area 一致且至少一圈的
  complete segment；不把窗口末端位移称为事件。
- `CLEAN_ONE_SFQ_CANDIDATE`：activity 内恰有一个 complete segment，幅度在
  `1.0..1.15` turn，同段 area 一致，POST `post_bounded=true`，且没有第二个
  activity/POST complete segment。
- `OVERDRIVEN_ONE_PLUS_RESIDUAL`：只有一个 activity complete segment、POST
  bounded 且无第二个 complete segment，但该段超过 `1.15 turn`。
- `MULTI_EVENT`：activity 内至少两个 complete segments，或 activity 的一个
  complete segment 后在 POST 又出现 complete segment。
- `INCONCLUSIVE`：raw QA、窗口覆盖、相位/面积映射或 POST boundedness 不足，
  或出现达到一圈但 phase/area 不一致的候选，不能安全归入事件/非事件。

`complete_segment_count` 在摘要 CSV 中定义为 activity 窗口内的 complete
segment 数；POST 数量和 total 数量在 details JSON 中完整保存。
`second_complete_segment_present` 覆盖 activity 第二段和 activity→POST 的
第二段。任何分类都不使用 VOUT peak/p2p、I>Ic、whole-window phase p2p、
phase p2p 或 `fast_events`。

## 回归锚点与停止规则

在新矩阵分类前冻结以下两个同算法锚点：

- 旧 9 ps / 12x320 ideal replay：BJL2 最大段约 `+0.8925272335342432 turn`，
  同段 area 约 `+0.8925370087565057 Phi0`，应为
  `SUBTHRESHOLD` / no complete event。
- 旧 13 ps / 12x320 ideal replay：BJL2 最大段约 `+1.0160289228944646 turn`，
  同段 area 约 `+1.0160368344325381 Phi0`，应为
  `CLEAN_ONE_SFQ_CANDIDATE`。

新严格分析在相同 raw/等价 fixture 上若与锚点不一致，立即记录
`STRICT_EVENT_REGRESSION_MISMATCH`，停止物理解释，不覆盖旧 evidence。

## 计划输出

- `analysis/strict-event-summary.csv`：全部 replay + physical 的 32 个 case
- `analysis/strict-event-details.json`：所有 segment、post、QA、窗口位移和
  完整计数
- `analysis/provenance-equivalence.json`
- `analysis/jsl-series-current-equivalence.csv`
- `analysis/regression-check.json`
- `analysis/REVIEW.md`、`REPORT.md`、`SUMMARY.md`
- 仅三张聚焦图：9 ps/12x320 replay、13 ps/12x320 replay、严格事件矩阵

所有图只作描述性展示；raw、同段 phase/area、控制和报告才是证据。完成本
任务后停止，不自动更新 HANDOVER 或 todo，也不执行下一任务。
