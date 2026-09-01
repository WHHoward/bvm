# Tool Consolidation Plan V1

## 目标

把未来的“科学问题 → 可复盘结果”收敛到少量共享工具和显式配置，同时
保留既有历史实验的原始证据与可复现路径。本计划不搬迁历史目录，不改变
`josim-handoff/v1`、`METRIC_SPEC_V2` 或任何电路/物理结论。

## 已完成的盘点

盘点范围写入 [`TOOL_REGISTRY.yaml`](TOOL_REGISTRY.yaml)，覆盖：

- `scripts/**/*.py`、`scripts/**/*.sh`；
- `.agents/skills/**` 中的脚本；
- `test/exploration/**/*.py`、`test/exploration/**/*.sh`；
- experiment-local builder、analyzer、plotter、verifier。

旧工具采用 logical archiving：登记 `CORE`、`SUPPORTED`、`LEGACY` 或
`SUPERSEDED`，不做 physical mass relocation。

## 未来默认路径

```text
physical question
  → minimal hypothesis
  → reuse TOOL_REGISTRY / scripts/bvmtools / presets
  → QUICK
  → RESULT_BRIEF.md + compact CLASSIC visualization
  → AWAITING_USER_REVIEW
  → explicit user authorization
  → close / another Quick / Promotion plan / Formal
```

Agent 不得因为一个 Quick 结果自动设计或执行下一个物理实验。

## 共享核心

`scripts/bvmtools/` 的 V1 边界是：

| 模块 | 唯一职责 |
|---|---|
| `raw.py` | 保留 exact labels、duplicate occurrence、实际时间轴与基础 QA |
| `provenance.py` | SHA-256、Git、solver 和输入快照 |
| `phase.py` | raw rad、continuous unwrap、rad→turns、既有 deterministic segmentation |
| `sfq.py` | 同一 JJ、同一 segment、带显式映射/溯源/spec 的 phase/area arithmetic 与 guarded local compatibility label |
| `waveform.py` | waveform diagnostics；current-time area 不是 SFQ quantity |
| `compare.py` | exact-grid comparison；默认不插值 |

strict-event classification 不使用共享隐含阈值：缺少完整 `StrictLocalEventSpec`
或 hash-bound provenance 时只返回 arithmetic 和 `INCONCLUSIVE`。只有出现立即的重复需求，才新增 `runner.py`、`plotting.py`、`report.py` 或
`netlist.py`；V1 用 `bvm-exp.py` 和既有 `josim-plot2.py` 完成 Quick。

## Rule of Two

一个新 diagnostic 第一次可以在 experiment-local 文件中实现，并标记
`EXPERIMENTAL_LOCAL`。第二个实验需要同样功能时必须停止复制，先提升到
`scripts/bvmtools/`、加入 focused test、更新 registry，再让新实验使用它。

## 三种模式

- `QUICK`：1–4 个显式 case、一个中心变量、基础 raw QA、共享 metrics、一个
  compact classic 结果；结果只能是 `QUICK_PROMISING`、`QUICK_NO_EFFECT`、
  `QUICK_OPPOSITE`、`QUICK_AMBIGUOUS` 或 `QUICK_INVALID`。
- `PROMOTED`：只生成 `PROMOTION_PLAN.md`，它是 planning gate，不自动运行大矩阵。
- `FORMAL`：沿用当前严格 provenance、matched controls、timestep、独立复核和
  bounded claim 要求。

三种模式都在结果交付后进入 `AWAITING_USER_REVIEW`。`USER_REVIEWED` 和
`NEXT_STEP_AUTHORIZED` 不能由 agent 自行填写。

## 可视化规则

默认是 `visualization.mode: compact` 和 `CLASSIC_LOCKED`：使用
`josim-plot2.py -t sep_comb -c dark -j 2pi`，只选 2–5 条与问题直接相关的
信号。`full` 只增加信号数量，不改变 classic visual language；必须在配置或
用户请求中明确 opt-in。替代视觉风格需要用户明确授权，V1 不提供另一套后端。

## 迁移边界

历史 local analyzer/builder/plotter 保留原路径；不批量删除、不批量改写、不
重生成历史 raw、不把旧 v1 runner 升级为 Formal。未来 family 使用：

```text
test/exploration/<family-id>/
├── FAMILY.md
├── experiment.yaml
├── quick/<probe-id>/
├── formal/<formal-id>/
└── FINAL_REPORT.md
```

当前 V1 只要求 `experiment.yaml` 和显式 `cases`；不实现万能 circuit DSL 或
arbitrary topology mutation。

## 验收依据

共享核心的 Anchor A/B、raw QA、waveform、compare 和 `josim-plot2` 回归测试，
以及 tooling-only smoke test，均必须通过后才可将整合报告标为
`TOOLING_CONSOLIDATION_V1_ACCEPTED`。这些测试只验证工具链，不制造新的 science
result。
