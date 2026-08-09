---
name: josim-experiment
description: Design, create, run, sweep, reproduce, or document JoSIM/BVM `.cir` experiments with preregistered questions, matched controls, immutable raw outputs, provenance, and timestep checks. Use whenever changing a research netlist, generating CSV data, testing BVM/BQ/DCSFQ/JTL/T1 behavior, or evaluating a candidate circuit; use `josim-evidence-audit` separately for physical Gate conclusions.
---

# JoSIM 严谨实验

## 开始前

1. 阅读 `docs/HANDOVER.md` 的当前事故边界和执行顺序。
2. 对结论级实验，完整阅读 [run-protocol.md](references/run-protocol.md)。
3. 使用 [run-manifest.yaml](assets/run-manifest.yaml) 和 [analysis-template.md](assets/analysis-template.md) 建立唯一 run 记录。
4. 先写一个主要研究问题、主假设、替代解释以及 `PASS/FAIL/INCONCLUSIVE` 的预期观察，再编辑网表。

## 当前硬停止条件

在 `memory/project-todo.md` 的 M4–M11 完成并有版本化替代物前：

- 不得把 `scripts/sfq_metrics.py` 的 `net_delta_sfq`、`fast_events` 或旧 JSON 当作物理指标；
- 不得把 `scripts/run_exp.sh` 称为标准结论流水线；
- 可以复现历史文件，但必须标为 historical/provisional，且不能覆盖旧数据；
- 候选实验若缺少冻结的 `METRIC_SPEC_V2`，只能标为 calibration/exploratory，不能宣布 Gate `PASS`。

## 实验流程

1. **预检**：记录 Git HEAD/dirty 状态、`build/josim-cli` 路径/版本/SHA-256、网表及 include 闭包、模型、请求步长和信号方向。
2. **设计对照**：至少考虑匹配零输入、read0、已知正例、反极性、真实负载和更细步长。零输入对照除激励外保持完全相同。
3. **设计因果输入**：单事件研究优先单次 `pwl(...)`；周期 `pulse(...)` 只能明确标成 periodic regression。
4. **声明测量**：若要审计某个 JJ，输出其直接 `P(B...)` 和 `V(B...)`；记录端点和正方向。不能用无关节点对地电压替代结电压。
5. **保存产物**：创建唯一目录，保存输入快照、原始 CSV、stdout/stderr、manifest 和哈希。路径已存在时停止，不覆盖、不删除。
6. **数据 QA**：检查退出码、solver 警告、缺列、NaN、时间严格递增、仿真终点和事件后稳定时间。数据问题判 `INVALID`，不是电路 `FAIL`。
7. **分析**：使用 `josim-evidence-audit`；将观察、推断和未知分开。
8. **收敛**：对名义通过、边界和失败代表点比较至少三个预先声明的步长。分类随步长变化时判 `INCONCLUSIVE`。
9. **记录**：填写分析模板，保留失败运行，并把上层文档链接到 run ID，而非复制整份数据。

## 扫描纪律

- 预先记录参数、范围、步长、最大运行数和停止规则。
- 先检查单调性，再把两个相邻测试点描述成边界区间；不得由 90 失败、110 通过直接宣称阈值为 100。
- 同时改多个参数只能证明组合效果，不能证明单个元件的原因。
- 自适应扩大扫描时创建新实验 ID，并记录为何改变计划。
- 没有工艺分布时只称“灵敏度分析”，不称“良率”。

## 结果措辞

只在对应证据层级成立时声明结果。找不到通过点时写：

> 在给定模型、激励、负载、参数范围、步长和指标版本下未找到通过点。

不得写成拓扑普遍不可能，也不得把 JoSIM 仿真写成硬件实测。
