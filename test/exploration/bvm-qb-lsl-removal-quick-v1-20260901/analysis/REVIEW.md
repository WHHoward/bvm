# BVM_QB_LSL_REMOVAL_QUICK_V1 数值与对抗性复核

- 审查时间：`2026-09-01T19:27:52+08:00`
- 审查对象：本目录的 candidate raw、固定窗派生统计、brief、唯一 overview
- 审查边界：只读 raw/netlist/配置和派生证据；不修改 raw，不重跑 JoSIM，不扩大 Quick
- 复核结论：`REVIEW_PASS_WITH_BOUNDED_QUICK_SCOPE`
- 科学层 disposition 仍为：`INCONCLUSIVE`

## 最强有界声明

本轮只声称：在固定 `13 ps / 12×320 / logical1 READ / scaled QB / 35 µA bias /
10 ohm load / 0.0125 ps timestep / 170 ps stop` 条件下，把 canonical BVM 输出链的
`L_SL=0.4 pH` 移除并将 `R_SL` 直接接到 `SL`，没有显示出使 physical
`BVM→JSL→QB` READ trajectory 按预注册 `20%` RMS-distance 标准明显靠近既有
grounded-source / ideal-replay reference。

它不声称 `L_SL` 是唯一根因、硬件行为、timestep convergence、SFQ 计数、JTL/T1
delivery、系统 Gate 或论文级结论。

## 数值复核

| 检查项 | 结果 | 证据 |
|---|---|---|
| 单位与相位换算 | `PASS` | raw 的 `time` 按秒读取；固定窗报告为 ps；相位轨迹只有在比较/报告时按 `rad/(2π)` 写成 turns；电流面积仍标为 `µA·ps`，没有写成 SFQ/Φ0。 |
| 窗口边界 | `PASS` | 独立 raw-only 复核严格使用 `[80,90)` ps 和 `[95,110)` ps；得到与报告一致的 W2 phase 最大差 `1.32894377482e-05 turns`、source current 最大差 `0.000800136 µA`。 |
| 符号与重复列 | `PASS` | `I(B_LD1)` occurrence 0 被明确读取；baseline 列索引 `[14,18]`、candidate `[13,17]`，各自重复列逐点相等，没有偷换 occurrence。 |
| raw 健康 | `PASS` | grounded、ideal replay、baseline、candidate 均为 `13599` 行，时间严格递增，数值有限，覆盖 `0–169.9875 ps`；candidate solver return code 为 `0`。 |
| 独立 raw cross-check | `PASS` | 不读取 `metrics.json`，用独立 CSV parser 直接重算 source 与四个 QB primary RMS distance；source `-0.288175915%`，BJS `+0.871821439%`，L1 `-1.144005307%`，BJL1 `-0.448068497%`，BJL2 `-0.366914238%`，与报告一致。 |
| 阈值/strict local | `PASS` | BJL2 使用 task-local frozen compatibility arithmetic；`SUBTHRESHOLD` 仅表示同一 JJ 的局部 phase/area activity 不满足本地完整段条件，不是 SFQ event count。 |
| 收敛与敏感性 | `UNKNOWN` | 只有登记的 `0.0125 ps` 条件；没有 timestep ladder、controls 或参数 sweep，因此不作收敛/稳健裕量结论。 |

复核过程中第一次 raw-only 探针遗漏了 W2 mask，得到的是全时段差异；该输出已丢弃，
没有写入结果或用于判断。修正为严格窗口后才形成上表，这是复核过程中的工具错误，
不是实验 raw 错误。

## 对抗性复核

| 隐藏错误假设 | 探针 | 结果 |
|---|---|---|
| intervention 是 no-op | 对 canonical 与 candidate BVM 做结构 diff，并比较 raw hash/READ 轨迹 | `L_SL` 被作为真实元件移除，`R_SL` 直接接 `SL`；canonical 未改；candidate raw hash 为 `d31cdf...`，且 W3 JS1/JS2 与 baseline 有非零差异。未见恒等输出。 |
| wrong branch / stale duplicate | 直接按 header occurrence 读取 `I(B_LD1)`，检查两个同名列 | 两个 raw 的重复列各自逐点相等，occurrence 0 语义保持；未发现第二列被误用。 |
| 旧 raw 或旧派生物被引用 | 检查 candidate raw、sidecar、solver log、parent baseline hash 与报告 raw records | candidate raw 与 sidecar 一致；baseline 使用父矩阵已存在的 `9aecc3...` raw，模型/solver/spec 与 parent manifest 匹配；首次后处理大小写错误被单独保留，修正分析没有重跑 science case。 |
| weak oracle | 用独立标准库 CSV 读取和 numpy 计算 W2/W3 关键统计，不读取本目录 metrics/report | source peak、RMS distance 和四个 QB primary RMS distance 均与派生报告一致；这支持机械一致性，不升级为第二 solver 权威。 |
| window contamination | 故意审视 W2/W3 边界，记录并废弃一次无 mask 探针后重算 | 修正结果只使用预注册窗口；没有用全时段差异判定 pre-READ safety。 |
| overclaim | 搜索 brief/report 的 event、SFQ、JTL/T1、hardware、convergence 语义并核对边界段落 | 已明确 local-only、INCONCLUSIVE、无系统 Gate/硬件/收敛外推；overview 只作描述性可视化。 |

## Residual uncertainty

- 仅有一个 LSL-removed candidate，没有 logical0/no-read、timestep ladder、负载/参数
  sweep 或独立初始条件，因此 `QUICK_NO_EFFECT` 不能外推为普遍无效。
- source 与 QB 轨迹的变化仍是总体 dynamic load interaction 的观察，不能由本轮
  单变量 probe 唯一定位内部器件机制。
- BJL2 strict classification 是同一 JJ 的局部 phase/voltage-area arithmetic；不
  等于下游 SFQ delivery，也不等于系统事件计数。
- HTML overview 由 `josim-plot2.py` 生成，只保留 7 组关键轨迹；图形不能替代 raw
  或独立数值审查。

## 审查处置

机械证据和关键数值复核未发现足以推翻本轮有界结果的单位、窗口、分支或 stale-artifact
问题。保留 `QUICK_NO_EFFECT / INCONCLUSIVE / AWAITING_USER_REVIEW / STOP`，不自动
Promotion，不启动下一实验，不更新 HANDOVER、project-todo 或 paper claim。
