---
name: project-todo
description: JoSIM × BVM 项目主任务清单 — 2026-08-09 相位单位审计后重建
metadata:
  type: project
  node_type: memory
  last_updated: 2026-08-13
---

# JoSIM × BVM 项目主任务清单

> 状态：🔴未开始　🟡进行中　🟢完成　⏸️暂停/被取代
>
> 当前唯一优先级：Phase −1 计量修复。旧 Step 0“冻结基线”、BQ 系统排除和 DCSFQ Phase 1 Gate 已因 `P()` 单位错误失效。

## A. 🟡 Phase −1：修复测量管线与重建基线

| # | 任务 | 状态 | 完成标准 |
|---|---|---|---|
| M1 | 明确 `P()` 原始单位为 rad | 🟢 | 源码、JoSIM 文档、绘图脚本和 JTL 示例四重核验 |
| M2 | 审计旧指标影响范围 | 🟢 | BASELINE、P0、P2、v4、证据链和 Phase 1 已定位 |
| M3 | 为旧权威文档加 superseded 警告 | 🟢 | HANDOVER、BASELINE、P0、P2、证据链、计划均有入口警告 |
| M4 | 修复/替换 `scripts/sfq_metrics.py` | 🟢（2026-08-11） | `scripts/sfq_metrics_v2.py` 明确 rad→圈转换；活动只报告样本/区间，不叫事件；合同 `JH-20260811-M4-003` 的独立审计为 `ACCEPTED` |
| M5 | 实现事件窗口和零输入控制 | 🟢（2026-08-11） | `M5-LITE-PILOT-001` A02 经 Copilot 复审与 Codex 接受：pre/activity/post 稳定窗、显式方向、匹配零输入控制和活动聚类有统一实现；不构成物理 Gate |
| M6 | 加电压面积交叉校验 | 🟢（2026-08-12） | `JH-20260812-M6-002` 的 FROZEN 复现已用同一 JJ、同方向、同一实际采样端点窗口的直接 `V(B...)`/`P(B...)` 报告 `∫Vdt/Φ0` 与 `Δφ/2π` 的带符号残差；M9 冻结测量/报告语义，全局接受容差仍为 UNFROZEN |
| M7 | 指标单元/回归测试（拆三子项） | 🟢（2026-08-12） | `M7-LITE-001` A02 经 Copilot 复审与 Codex 接受：M7A/B/C 均通过；仅建立校准实现与确定性回归，不构成物理 Gate |
| M7A | Mathematical unit tests | 🟢（2026-08-12） | 合成 ground truth（zero trace、±2π 阶跃、双转换、已知电压面积脉冲、sign 反转、窗口边界）：验证公式/单位/sign/window/cluster/integration；不证明任何 BQ/DCSFQ/BVM candidate 物理正确 |
| M7B | Canonical circuit validation | 🟢（2026-08-12） | 直接同 JJ V/P 探针的 canonical JTL 运行与独立实际时间轴算术一致；残差只报告，M9 冻结测量/报告语义而非全局接受容差；不证明 BQ v4/DCSFQ_BVM 成功 |
| M7C | Historical regression | 🟢（2026-08-12） | DCSFQ 300 µA 控制重放和 BQ v4 六周期平台常量以预注册独立值通过；只证明新 pipeline 未重新误读历史 raw，不把周期平台称为物理事件或 Gate |
| M8 | 有界时间步收敛（预注册 procedure） | 🟢（2026-08-12） | `JH-20260812-M8-001` 在运行前固定 0.1/0.05/0.025 ps、六次匹配控制运行、窗口、观测量、任务局部稳定带宽与最大深度停止规则；其闭环合同缺陷被保留为 REWORK 历史，`JH-20260812-M8-002` 以冻结原始 CSV 完成独立重算和审计接受。仅证明 loaded canonical JTL 校准 fixture 的有界数值收敛，不冻结 M9 容差或任何物理 Gate |
| M9 | 只冻结 `METRIC_SPEC_V2.md`（怎么测） | 🟢（2026-08-13） | `docs/research/METRIC_SPEC_V2.md` v2.0.0 由 `JH-20260813-M9-004` 接受：冻结 phase normalization、same-JJ P/V mapping、双符号、窗口/控制、activity、实际时间面积、收敛和输出契约；全局数值容差仍 UNFROZEN；**不定义**接口成功标准（独立 `INTERFACE_GATE_V1`） |
| M10 | 重生 JSON 和审计表 | 🟢（2026-08-13） | `JH-20260813-M10-004` 已接受：BASELINE/P0/P2/v4 的 `data/metrics_v2/` 重建产物、central correction table 和历史文档 SUPERSEDED banner 均已 hash-bound；旧文件/原文保留，结论限 endpoint arithmetic/provenance，不构成物理 Gate |
| M11 | 新基线冻结（双子门） | 🟡（M11A 已接受；M11B 重签中） | **M11A** Measurement Calibration Baseline 已由 `JH-20260813-M11A-001` A02/C02 接受：M4–M10 accepted evidence、MetricSpec、tests/raw/controls、fixture-local convergence 与 M10 historical provenance 已 hash-bound，全球容差仍 UNFROZEN。**M11B** 将以 superseding FROZEN 合同冻结统一 object matrix：BVM storage、BVM source/output、published QB、BQ v4、standard DCSFQ、DCSFQ_BVM、canonical JTL 的 current evidence / observable / characterization / reproduction / UNKNOWN / discriminator；矩阵满足 W5B provenance 纪律后与 M11B 一并闭环。两个子门都通过才标绿 |
| M12 | 修复 `josim-plot2.py -j` 布局缩放 | 🟢（2026-08-11） | `M12-LITE-PILOT-001` 经 Copilot 独立复核与 Codex 接受：五种布局对 phase 一致缩放、标签为 turns、回归测试覆盖旧“只改标签”错误；无物理结论 |

## B. 已重算、当前可用的事实

| 项目 | 状态 | 说明 |
|---|---|---|
| BVM→BQ 基线 | 🟢 已人工重算 | JM1 −0.9406 圈，BJs +0.9983 圈；BJL1/BJL2 净值仅 0.0706/0.0598 圈；该网表未接 JTL，只能判断 BQ 输出支路未证明完成量化 |
| BVM P2 | 🟢 已人工重算 | W1/W0 约 +0.938/−0.937 圈；100 µA 读近似非破坏；120 µA R0 擦除 |
| 标准 DCSFQ 300 µA | 🟢 已控制相减 | B1/B2/B3 输入诱导量约 −1/+1/+1 圈，不是多滑移爆发 |
| BQ v4 电流扫 | 🟢 已逐周期复核 | 已测 70/90 µA 无逐周期累积；110–150 µA 六输入对应下游约六个整数相位增量，与约 1:1 相容，不是已通过完整事件 Gate |
| BVM 负载规格 | 🟢 | 43.9–97.8 µA、FWHM 6.8–11.2 ps；相位单位不影响 |
| DCSFQ_BVM 分流 | 🟢 | 68.4 µA 测试输入下未见完整输出；增量耦合约 0.285 |

人工重算用于纠正路线判断，但在 M4–M11 完成前不能称为新的自动冻结基线。

**2026-08-12 更新**：M4 建立 raw rad→圈与活动命名基础；M5 已接受 pre/activity/post 窗口、显式方向、匹配零输入对照与连续活动聚类的实现和确定性回归。M6 已接受 FROZEN 同 JJ 相位—电压面积测量管线复现：它使用直接 `V(B...)`、相同方向/端点窗口和 CSV 实际时间轴梯形积分，报告残差但不冻结接受容差。M7 已接受 M7A 合成 ground truth、M7B canonical JTL 同 JJ V/P 校准与 M7C 历史回归；三者均只构成 CALIBRATION LITE 证据。M8 已接受预注册的 0.1/0.05/0.025 ps 有界收敛 procedure：六份 loaded canonical JTL 匹配控制 raw 的注册量均在两个相邻 refinement 带宽内；结论仅限该校准 fixture 的数值收敛。M4–M8 都不构成物理 Gate 或 SFQ 事件计数；M9–M11 仍未完成且等待用户授权。M8 验收证据：`research/tasks/JH-20260812-M8-002/audits/C01/verdict.yaml`；M7 验收证据：`research/tasks/M7-LITE-001/attempts/A02/CODEX-AUDIT.md`；M6 验收证据：`research/tasks/JH-20260812-M6-002/audits/C01/verdict.yaml`。

**2026-08-13 authority sync**：M9 已由 `JH-20260813-M9-004/audits/C01/verdict.yaml` 接受，冻结测量/报告语义而不冻结全局数值容差或接口成功标准。用户已授权 M10；其执行合同必须先复核本 authority 状态。上面的 2026-08-12 历史更新不再表示当前任务状态。

**2026-08-13 M10 接受更新**：`JH-20260813-M10-004/audits/C01/verdict.yaml` 已接受 scope-correct 的重封存。BASELINE、P0、P2 与 BQ v4 的 V2 JSON、correction table 和历史 superseded banners 均与保存的 A01 产物逐字节核验；M10-003 的封存缺陷保留为历史 REWORK。M10 只完成 historical endpoint arithmetic/provenance 重建；不冻结全局容差，也不建立 SFQ、fluxoid、下游、candidate 或系统 Gate 结论。

## C. ⏸️ 候选路线 1：BQ v4（等待 Phase −1）

> 依赖 M4–M11；在指标、容差和新基线冻结前不启动候选参数宣判。

| # | 任务 | 状态 | Gate |
|---|---|---|---|
| Q1 | 单次 PWL 电流测试 | 🔴 | 每次激励的输入、内部和下游响应可独立归因 |
| Q2 | 90–110 µA 边界细扫 | 🔴 | 在验证单调性的同时定位 0→1 输出边界及容差 |
| Q3 | 真实 BVM 波形驱动 | 🔴 | 不用理想矩形代替真实源波形 |
| Q4 | 读 0/读 1/重复读 | 🔴 | 下游 0/1，且无多发和 backfire |
| Q5 | v4 多变量消融 | 🔴 | L0、Ic、RJ 改动能区分主效应 |
| Q6 | 负载/偏置/参数/步长裕度 | 🔴 | 声明明确可用范围 |

说明：v4 不再标为“Gate 失败/拓扑排除”。已测 110–150 µA 理想周期电流下与约 1:1 相容的相位平台是重新开放该路线的证据；单脉冲完整 Gate 和真实 BVM 级联仍未通过。

## D. ⏸️ 候选路线 2：DCSFQ_BVM（等待 Phase −1）

> 依赖 M4–M11；当前 150/300 µA 只是两个离散的内部相位响应点，不是已定位输出阈值。

| # | 任务 | 状态 | Gate |
|---|---|---|---|
| D1 | 新口径下复测标准/缩放响应曲线 | 🔴 | 撤回固定 45–55 µA，检查单调性并由数据定位边界 |
| D2 | 正确输入极性对照 | 🔴 | 反转源方向，不交换 a/q 端口 |
| D3 | 有界 area/IB1/L2/L3 扫描 | 🔴 | 单变量或预先定义小矩阵，不无限试参 |
| D4 | 无输入稳定 + 单理想脉冲 | 🔴 | 无自发事件；每输入恰好一事件 |
| D5 | 标准 JTL 接收 | 🔴 | JTL 两级逐事件 +1，读 0 为 0 |
| D6 | 真实 BVM 级联 | 🔴 | 最终 0/1 Gate 且不破坏存储 |

ColdFlux 原 DCSFQ 是电压脉冲→SFQ 单元；将其用于 BVM 电流接口是项目新设计，不能把库手册当作成功保证。

## E. 系统验收与 T1

| # | 任务 | 状态 | 说明 |
|---|---|---|---|
| S1 | 接口系统 Gate | 🔴 | 使用 `METRIC_SPEC_V2.md` 的测量语义；读 1/读 0/重复与状态保持等成功判据须由独立 `INTERFACE_GATE_V1` 事先冻结 |
| S2 | 参数/偏置/负载裕度 | 🔴 | 关键 R/L/C/Ic 和偏置范围 |
| S3 | 研究测试接入 CTest | 🔴 | 自动数值断言，不只人工看图 |
| S4 | ColdFlux 代表单元回归 | 🔴 | 补完整真值表、输出负载和相位单位 |
| S5 | T1 计数/时序验证 | 🔴 | n 输入的 sum/carry、时钟、JTL 负载 |
| S6 | 端到端 BVM→接口→JTL→T1 | 🔴 | 只有接口 Gate 通过后开展 |

## F. 文档与论文

| # | 任务 | 状态 | 说明 |
|---|---|---|---|
| W1 | 审计版完整理解指南 | 🟢 | `docs/guide/project-guide.md` |
| W2 | 审计版 HANDOVER | 🟢 | `docs/HANDOVER.md` |
| W3 | 更新全部旧日志正文数值 | 🔴 | 先完成自动重算，不删除历史原始数据 |
| W4 | 重写论文证据链 | 🔴 | 撤销“八轮系统排除”和未验证根因 |
| W5 | 文献/来源/作者（拆三子项） | 🔴 | 见 W5A/B/C |
| W5A | Literature boundary | 🔴 | 记录 database/query/date/closest prior art/already does/does not report/allowed novelty wording；W5A 未完成前禁止 first/no prior work/literature blank confirmed |
| W5B | Reference provenance | 🟡（由 M11B 统一闭环） | M11B object matrix 是唯一 canonical provenance/reproduction/characterization 事实层；完成时必须统一标记 [PUBLISHED]/[AUTHOR_PROVIDED]/[DERIVED]/[INFERRED]/[DESIGNED]/[TUNED]/[UNKNOWN]，并禁止将 [INFERRED]/[DESIGNED]/[TUNED] 逐渐写成 paper parameter。审计接受 M11B 前不得标绿，也不得另建重复 provenance 记录 |
| W5C | Author inquiry | 🔴（可选） | 联系 BVM 作者询问 modified-QB netlist/参数/JM1 shunt/`.model`/testbench/bias-timestep；发送前需用户明确授权；收到信息标 [AUTHOR_PROVIDED] 不等同 [PUBLISHED]；time-box（发送→一次 follow-up→预设期限无充分回复→继续项目，回退 R0/partial-R1 + UNKNOWN list） |
| W6 | 论文接口章节 | 🔴 | 至少一条路线通过系统 Gate 后定稿 |

## G. 已暂停/被取代的旧状态

- ⏸️ Step 0“冻结指标脚本和基线”：指标定义错误；只保留原始 CSV 与可追溯历史。
- ⏸️ Step 1“BQ v4 Gate 未通过”：其“38 个失控事件”判读被正确单位下与约 1:1 相容的 JTL 相位平台反证；新 Gate 尚未通过。
- ⏸️ Step 3“八轮系统排除 BQ”：因相位/事件计量错误撤回。
- ⏸️ 旧 DCSFQ Phase 1 计划：目标阈值、V1/V2 Gate、脚本调用和极性测试均需重写。
- ⏸️ 用 `P(JM1)≈±5.9` 证明“BVM ±6 多涡旋”：旧证据链被约 ±0.94 个 JJ 相位圈的正确换算推翻；严格 fluxoid 数待算。

## H. 实验不变量

1. 保存原始 CSV，不覆盖历史；
2. 每个数字附单位、参考窗、控制和信号方向；
3. 相位报告 raw rad 与除 \(2\pi\) 后的圈数；
4. 事件数必须经聚类/平台/同一 JJ 同端点、同方向、同窗口电压积分，以及下游共同确认；
5. 哈希重复与步长收敛分别验证；
6. 周期 `pulse()` 不能当单次输入；因果测试优先 `pwl()`；
7. 解释性机制必须标记并通过单变量对照；
8. 论文仿真不写成硬件实测。

## I. 研究阶段与来源纪律（2026-08-12 采纳）

1. **Study Phase**：每个科研任务声明 `EXPLORATORY | CALIBRATION | CONFIRMATORY`。EXPLORATORY（debug/参数扫描/机制假设）不直接成为 final Gate 或 paper-critical evidence，不得事后补票改名 CONFIRMATORY；CALIBRATION（M7–M10/M11A：metric/regression/convergence/baseline/tolerance）；CONFIRMATORY（route verdict/final Interface Gate/final margin/paper-critical result）运行前必须冻结关键变量与判据，使用 CRITICAL+FROZEN + fresh-context independent review。
2. **Parameter provenance**：参数标记 `[PUBLISHED]`/`[AUTHOR_PROVIDED]`/`[DERIVED]`/`[INFERRED]`/`[DESIGNED]`/`[TUNED]`/`[UNKNOWN]`；`[INFERRED]`/`[DESIGNED]`/`[TUNED]` 参数不得在后续总结中逐渐写成 paper parameter；索引见 `docs/research/REFERENCE_PROVENANCE.md`（W5B）。
3. **Reproduction levels**：R0 topology reconstruction / R1 published nominal-parameter reconstruction / R2 behavioral reproduction / R3 independent full reproduction；R3 必须在预声明的 model closure、testbench、parameter provenance、numerical settings 与 observation tolerance 下满足全部 reproduction criteria；参数缺失时明确 `R0 / partial-R1`，不得把项目参数冒充论文参数。
4. **Source/Receiver/Interface 分层**：BVM source characterization 与 receiver characterization 的测量语义必须引用 `METRIC_SPEC_V2`（不另行定义）；`INTERFACE_GATE_V1` 在 Reference/Source/Receiver 事实层建立后独立冻结；正式 candidate tuning 与 route verdict 等待 M11（M11A+M11B）完成。
