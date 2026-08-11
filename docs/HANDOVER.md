# JoSIM × BVM 项目交接文档（审计修订版）

> 用途：给下一次会话提供当前可信状态和行动顺序。完整原理与项目教学见 `docs/guide/project-guide.md`。
>
> 审计日期：2026-08-09；**被审计的前置基线 commit**：`eb51576`（不包含本轮未提交文档）；研究使用的二进制报告 `v2.7.2837d13`。
>
> 重要：2026-08-06 版“冻结口径”已因相位单位错误失效；不得从旧日志复制 SFQ 数或 `fast_events` 结论。

## 0. 新会话第一步

```bash
cd /home/howard/JoSIM
git status --short
git log --oneline -8
build/josim-cli --version
```

然后按顺序读：

1. `docs/guide/project-guide.md`：审计后的完整教学、证据边界和计划；
2. 本文件：当前执行状态；
3. `memory/project-todo.md`：任务清单；
4. 若执行 Codex 委派任务，读 `research/CLAUDE_EXECUTOR.md` 和指定 `research/tasks/<task-id>/request.yaml`；
5. 原始网表和 CSV；旧 BASELINE/P0/P2/证据链仅作历史记录，先看其顶部审计警告。

### 0.1 Codex–Claude 分工（2026-08-09）

本仓库采用文件化任务合同：Codex 负责计划、签发 request 和独立审计；Claude Code 只在 ACK 后执行授权路径并提交 receipt；用户批准路线变化、指标冻结和论文主张。完整状态机、所有权和命令见 `research/WORKFLOW.md`。

`execution_status=COMPLETED` 只表示执行结束，不代表证据有效或物理成功。必须分别记录 artifact `VALID/INVALID`、physical `PASS/FAIL/INCONCLUSIVE` 和 audit `ACCEPTED/REWORK_REQUIRED/REJECTED`；只有接受的审计才能更新本文件或主任务表。

## 1. 项目定义

目标是验证并设计：

```text
BVM 状态相关读电流
    → BQ 或 DCSFQ_BVM 接口
    → 恰好一个可被标准 JTL 接收的 SFQ 事件
    → T1 / RSFQ 计数和计算
```

本项目没有修改 JoSIM 核心。对 `src/`、`include/`、`cmake/`、根 `CMakeLists.txt` 和 `test/CMakeLists.txt` 的 Git 核验表明，它们与上游树一致。研究层新增的是网表、实验、数据、脚本、论文和文档。

## 2. 最高优先级事故：相位指标单位错误

JoSIM 默认 phase 模式的 `P(JJ)` 是原始相位 \(\phi\)，单位 rad。证据：

- `src/Output.cpp` 直接输出相位差，没有除以 \(2\pi\)；
- `docs/tech_disc.md` 使用 \(V=(\Phi_0/2\pi)d\phi/dt\)；
- `scripts/josim-plot2.py` 默认标 `Phase (rad)`，`-j 2pi` 才归一化；
- 官方 JTL 示例在两个输入后相位约 13 rad，接近 \(4\pi\)。

但 `scripts/sfq_metrics.py` 直接把 raw rad 标为 SFQ，并把每个满足 `|ΔP|>0.3` 的采样间隔计成 `fast_events`。

正确关系：

\[
N_{\Phi_0}=\Delta\phi_{\rm rad}/(2\pi)
\]

这是某个 JJ 的净相位绕转数，不自动等于完整环 fluxoid 数。与电压面积交叉校验时，必须使用同一 JJ、同一对端点、同一方向和同一时间窗。

而 `fast_events` 是过阈值样本数，不是脉冲数。一个已知 JTL 事件会跨多个样本。

### 直接后果

- Step 0 的“基线冻结”失败；脚本在修复前暂停作为物理 Gate。
- 所有 phase 数字和事件数必须从原始 CSV 重算。
- Phase 1 计划暂停，先执行 Phase −1。
- 旧论文证据链的“八轮系统排除”不再成立。
- 哈希一致仍证明数值文件可重复，但不证明指标正确。

## 3. 经重算后的关键事实

### 3.1 BVM→BQ 基线

| 结 | 原始净相位 | 正确归一化 |
|---|---:|---:|
| BVM JM1 | −5.909806 rad | −0.940575 圈 |
| BQ BJs | +6.272743 rad | +0.998338 圈 |
| BJL1 | +0.443319 rad | +0.070556 圈 |
| BJL2 | +0.375836 rad | +0.059816 圈 |

`V(OUT_Q)` 峰值约 157 µV。该基线的 `OUT_Q` 只接 10 Ω 电阻，没有 JTL；因而它没有实际测试标准 JTL 接收。

可信结论：BJs 的净变化约一圈，但 BJL1/BJL2 未完成完整绕转，因而当前数据没有证明 BQ 完成有效量化；JTL 传播未测。不能再称 BJs 滑移 6.27 个量子，也不能用 `fast_events=0` 证明它“不是相位事件”。仅凭净值也不能排除正反过程抵消，需要完整轨迹、稳定窗和同一 JJ 两端电压面积。

### 3.2 BVM P2

- W1/W0 稳态 JM1 分别约 `+0.938/−0.937` 圈；
- WL=80 µA 不写，100/120 µA 可进入近一圈状态；
- 100 µA 读相位漂移约 0.004–0.009 圈，读电流重复性在约 1% 内；
- 120 µA 的 R0 测试会擦除负态；
- 单个 JM1 相位不能独立证明完整环 fluxoid 数，需完整环量子化计算。

用 `P(JM1)≈±5.9` 直接证明“\(\pm6\) 多涡旋”和“没有单涡旋工作点”的旧证据链已被推翻。完整环 fluxoid 数仍未由本次审计独立确定。

### 3.3 BQ v4

电流扫测试有六个周期输入：

- 70/90 µA：已测点的下游没有逐周期累积；
- 110/130/150 µA：以首脉冲前参考点为基准，BJL1/BJL2 和 JTL 各约增加六圈，其相位平台与每输入约一个下游事件相容；单脉冲电压面积、聚类和步长 Gate 尚未通过；
- 在 110–150 µA 输出点，输入 BJs 仍每周期运行约 18–22 圈；完整 70–150 µA 扫描范围为约 16–22 圈。

所以当前只能说：在这个理想周期电流测试台的已测点中，90 µA 没有逐周期输出，110 µA 已出现与约 1:1 传播相容的相位平台；实际边界尚待细扫，不称为已确定阈值。68.4 µA 是旧 BQ-v2 加载基线值，v4 改变输入阻抗后的真实 BVM 波形尚未知，真实级联仍未成功。

结论：BQ v4 重新列为候选；既不能称“已排除”，也不能称“接口完成”。

### 3.4 DCSFQ / DCSFQ_BVM

标准 DCSFQ：

- 已测至 150 µA 未见输入诱导的完整内部相位绕转；
- 300 µA 减去 0 µA 偏置启动控制后，B1/B2/B3 分别为 `−1/+1/+1` 圈；
- bump 与 sustained 的最终响应相同，保持平台不继续积累。

缩放版 DCSFQ_BVM：

- B1/B2 从 225 µA 缩至 80 µA，IB1 从 275 µA 缩至 100 µA，输出级保持标准 250 µA；
- 68.4 µA 下未触发完整输出；
- 输入增量进入 L3/结支路的比例约 0.285。

“300 µA 多滑移爆发”和由此推导的 45–55 µA 目标均失效。已测点只能说 150 µA 未见完整内部绕转、300 µA 见约一圈；这不是已定位的合格输出或 JTL 接收阈值。ColdFlux 手册原本把 DCSFQ 定义为电压脉冲→SFQ，本项目的慢/电流接口用法必须重新验证。

## 4. 不受相位单位影响的结果

- BVM 负载扫描：峰值电流约 43.9–97.8 µA；
- FWHM：约 6.8–11.2 ps；
- 特定波形的有效峰值 Thevenin 拟合：约 40 Ω、4 mV；
- 基线 BQ 输出电压峰值约 157 µV；
- DCSFQ_BVM 增量分流约 0.285；
- P2 读电流、重复性和 120 µA R0 擦除；
- 已保存运行的字节级重复哈希。

Thevenin 值是已测范围的经验拟合，不是 BVM 的普适线性源阻抗。哈希是确定性证据，不是数值收敛或物理正确性证据。

## 5. 当前不可作为事实的旧解释

- BQ 失败必然由 BJs 裸结欠阻尼唯一造成；
- 低 \(I_c\) 因 Josephson 电感增大而对所有拓扑都数学无解；
- BQ 输出电流小于 JTL 结的 \(I_c\)，所以必然推不动；
- K 互感只适合 MHz–GHz 而不适合皮秒；
- RB+LRB 的数值证明完整单元恰好临界阻尼；
- DCSFQ 平台不累积的详细机理已经确认；
- 本地论文足以证明“全球首次/文献空白已确认”。

这些可以作为假设设计对照实验，不能作为冻结物理结论。

## 6. 当前任务：Phase −1

### A. 修复测量管线

1. `P()` 明确为 rad，派生相位统一除以 \(2\pi\)；
2. 用事件前后稳定窗或匹配的零输入控制；
3. 把连续快速样本聚类，停止把样本数叫事件数；
4. 对同一 JJ 的同一对端点，按同一方向和同一时间窗计算电压面积 `∫Vdt/Φ0`；
5. 以标准 JTL 两事件、DCSFQ 300 µA 对照和 BQ v4 六个整数下游相位增量作为回归样例；
6. 补 0.1/0.05/0.025 ps 步长收敛；
7. 先用校准数据建立并冻结 `METRIC_SPEC_V2.md`，明确整数残差、相位—电压面积误差、BVM 漂移、步长差异及幅度/抖动容差；
8. 在各实验目录的 `data/metrics_v2/` 中重建 BASELINE/P0/P2/v4 JSON 和结论，不覆盖旧文件。

**M4 交接状态（2026-08-11 纠正）**：M4-001 的候选实现 `scripts/sfq_metrics_v2.py` 与 16 个单元测试仍保留在 `/home/howard/JoSIM-m4`，但不构成已完成任务。Codex 已以 `REJECTED` 审查 stand-in `S01`：它重签了已封存 request，且 A01 receipt 披露过未授权删除日志；因此不得接受、合并或上推 M4。M4 仍为 🔴，下一步是从干净基线签发 superseding 合同并重做实现级测试；不据此形成任何物理 Gate。

### B. 公平重测两条接口路线

**BQ v4**（等待 Phase −1 指标与容差冻结）：单次 PWL、90–110 µA 细扫、真实 BVM 波形、读 0/1、下游 JTL、参数单变量与鲁棒性。

**DCSFQ_BVM**（等待 Phase −1 指标与容差冻结）：重新定位响应边界；正确反转输入源极性；有限扫描 area/IB1/L2/L3；先理想单脉冲和 JTL，再真实 BVM 级联。

### C. 系统 Gate

- 读 1：下游 JTL 恰好一个事件；
- 读 0：零事件；
- 重复读：不丢失、不多发；
- BVM 状态不被破坏；
- 步长和关键参数扰动下仍成立。

上述“恰好”、“不被破坏”和“仍成立”的数值容差必须在 `METRIC_SPEC_V2.md` 中由校准数据事先冻结，不得在看到候选设计结果后移动。

在这些完成前，不启动最终论文结论和 T1 端到端声称。

## 7. 关键资产

| 类别 | 路径 |
|---|---|
| 完整审计教程 | `docs/guide/project-guide.md` |
| JoSIM 相位输出 | `src/Output.cpp`, `docs/tech_disc.md`, `docs/ex_usage.md` |
| 错误指标脚本 | `scripts/sfq_metrics.py` |
| BVM | `circuits/bvm/bvm_cell.cir` |
| BQ / v4 | `circuits/qb/bq_cell.cir`, `circuits/qb/bq_cell_v4.cir` |
| DCSFQ / 改版 | `circuits/standard/DCSFQ.cir`, `circuits/interface/DCSFQ_BVM.cir` |
| JTL | `circuits/standard/JTL.cir` |
| T1 | `circuits/t1/t1_cell.cir` |
| BVM→BQ 基线 | `test/final/single_bvm_qb/` |
| BQ v4 扫描 | `test/final/qb/test_bq_v4_sweep.cir`, `test/final/qb/data/bq_v4_sweep*.csv` |
| Phase 0 | `test/final/interface/` |
| P2 | `test/final/bvm/` |
| 论文 | `arti/` |
| 项目工作流 skills | `.agents/skills/`（canonical），`.claude/skills/`（兼容链接） |
| Codex–Claude 完整工作流 | `research/WORKFLOW.md` |
| Claude Code 执行入口 | `research/CLAUDE_EXECUTOR.md` |
| 文件化任务包 | `research/tasks/<task-id>/` |

## 8. 实验纪律

1. 使用并记录 `build/josim-cli` 版本，不混用系统安装的旧二进制；
2. 原始 CSV 保存到仓库实验目录，绝不只留 `/tmp`；
3. 使用单次 `pwl(...)` 做因果实验；`pulse(... period)` 会重复；
4. 每次记录时间步、窗口、对照、单位和列方向；
5. 不用人工目测代替可执行指标，但指标必须先有单元测试；
6. 同时报告原始 rad、归一化圈数、电压积分和下游响应；
7. 机制解释标为“推断”，除非有单变量对照；
8. 固定网表重复哈希与时间步收敛分别检查；
9. 研究单元目前未接入 CTest，不能把人工波形测试称为正式回归；
10. 不覆盖旧原始数据；用审计警告和新版本结果保留可追溯性。
11. `josim-plot2.py -j 2pi` 当前仅 `combined`/`sep_comb` 真正缩放相位；`grid`/`stacked`/`square` 只改标签。修复 M12 前遵循 `josim-viz` 的布局限制。
12. 委派执行必须先验证签名 request 并 ACK；执行者不得修改 request、审计、todo、HANDOVER、CHANGELOG 或冻结 raw。合同完成与物理 Gate 分开裁决。

## 9. 当前一句话状态

> BVM 的稳定相位状态和状态相关电流已有仿真支持；直接 BVM→当前 BQ 基线的输出支路未完成完整绕转，且该网表未测 JTL；BQ v4 在理想周期电流的 110–150 µA 已测点显示与约 1:1 JTL 传播相容的相位平台，完整 Gate 尚未通过；DCSFQ_BVM 在 68.4 µA 测试输入下未见完整输出。第一优先级是修复相位/事件计量、冻结容差并重建基线，然后用同一 Gate 复核两条候选路线。
