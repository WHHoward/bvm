---
name: josim-evidence-audit
description: Audit JoSIM phase, voltage-area, SFQ counting, JTL propagation, state preservation, convergence, and paper claims from raw CSV/netlist evidence. Use when interpreting `P(...)`, deciding whether a phase change is an event, reviewing historical metrics or plots, comparing BQ and DCSFQ routes, or issuing `PASS/FAIL/INCONCLUSIVE`; do not use derivative samples or visualization alone as event counts.
---

# JoSIM 证据审计

## 必读合同

凡涉及相位、SFQ、事件数或传播结论，先完整阅读 [phase-evidence-contract.md](references/phase-evidence-contract.md)。数值容差只从当前版本化 `METRIC_SPEC_V2` 读取；skill 本身不得发明或复制临时阈值。

若审计来自 `research/tasks/<task-id>/`，同时使用 `josim-handoff`：先验证 request/ACK/receipt 的哈希与路径范围，再进行物理证据审计。机械合同通过不代表科学证据通过。

## 审计流程

1. **确认主张**：把待审计句子改写成可检验对象，例如“JTL 末级在 read1 后增加一个稳定相位平台”。
2. **定位原始证据**：读取网表、CSV 表头、manifest、JoSIM/脚本/规格版本和匹配对照；旧 JSON 只能定位历史，不优先于 raw CSV。
3. **检查有效性**：检查退出状态、NaN/缺列、时间轴、方向、稳定窗、控制、负载和步长。缺关键项时输出 `INCONCLUSIVE`。
4. **计算本地量**：保留 `phase_delta_rad`，再计算 `phase_delta_turns = phase_delta_rad/(2π)`；使用 CSV 实际时间列积分同一 JJ 的直接电压。
5. **检查双证据**：相位和面积必须对应同一个 JJ、同一对端点、同一方向、同一时间窗。无法建立映射时不判本地事件。
6. **检查传播**：确认输出实际连接标准负载/JTL，并逐级检查稳定平台；没有 JTL 的网表不得判传播成功或失败。
7. **检查系统逻辑**：read1、read0、重复读、状态保持和收敛均满足冻结规范后，才允许系统 `PASS`。
8. **审计措辞**：区分直接观察、与数据相容的解释、已排除解释和未知机制。

## 固定证据层级

| 层级 | 可以声称 | 不能自动声称 |
|---|---|---|
| Artifact | 数据完整且可追溯 | 电路物理正确 |
| Activity | 存在快速变化候选区 | 一个 SFQ 或一次开关 |
| Local | 同一 JJ 的净相位和电压面积与一次事件相容 | 下游已接收、环 fluxoid 改变 |
| Downstream | 加载后的 JTL 逐级出现对应平台 | 系统逻辑和存储保持都通过 |
| System | read1/read0/重复/状态/收敛满足冻结 Gate | 硬件一定可工作 |

## 三态判定

- `PASS`：当前主张所需的全部预先声明条件满足。
- `FAIL`：数据有效，且至少一个必要条件明确不满足。
- `INCONCLUSIVE`：缺列、方向未知、缺控制、未稳定、无适当负载、无冻结容差或步长改变分类。

不得把缺证据当作失败，也不得把“与一次事件相容”简写成“已证明一个 SFQ”。

## 输出格式

以紧凑表格报告：待审计主张、所需层级、原始证据、计算量、缺失项、判定和允许的最强措辞。每个数字附单位、窗口/控制、信号方向和数据路径；列出替代解释及下一项最小判别实验。

有 handoff task 时，把最终判定写入 audit verdict，并分别填写 artifact status、physical verdict 和 audit disposition。执行者的 proposal 只是待核验输入，不得直接复制为裁决。
