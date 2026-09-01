# Future Experiment Workflow V1

本文是 `RESEARCH_WORKFLOW_TOOLING_CONSOLIDATION_V1` 产生的 future scientific
experiment 使用指南。它是 `research/WORKFLOW.md`（`josim-handoff/v1`）之外的
sidecar，不修改 handoff v1 的合同、schema、验证器或历史记录。

## 默认路径

```text
scientific question
  → minimal hypothesis
  → Reuse First / TOOL_REGISTRY / bvmtools / presets
  → QUICK (1–4 explicit cases)
  → RESULT_BRIEF + compact classic visualization
  → AWAITING_USER_REVIEW
  → stop
  → explicit user understanding and authorization
```

新实验必须显式记录 `baseline`、`candidate`、`changed_variables` 和
`held_fixed`。第一次缺少共享 diagnostic 时可以在实验目录中标记
`EXPERIMENTAL_LOCAL`；第二次遇到相同需求时必须先提升到
`scripts/bvmtools/` 并补 focused regression（Rule of Two）。历史 local
builder/analyzer/plotter/verifier 只登记，不批量搬迁或删除。

## 三条独立轴

- `evidence_tier`：`EXPLORATION`、`CANDIDATE`、`AUTHORITY`；
- `workflow_stage`：`QUICK`、`PROMOTION_PLAN`、`FORMAL`；
- `review_state`：`AWAITING_USER_REVIEW`、`USER_REVIEWED`、
  `NEXT_STEP_AUTHORIZED`。

V1 CLI 只执行 `QUICK`。Promotion 只应形成计划，Formal 继续使用现有严格
流程；两者都不能由 Quick 自动启动。`USER_REVIEWED` 和
`NEXT_STEP_AUTHORIZED` 只能由用户明确产生，代理不得代填。

## Quick 与可视化

入口：

```bash
python3 scripts/bvm-exp.py quick path/to/experiment.yaml
```

Quick 输出 `RESULT_BRIEF.md`、`human-gate.yaml` 和
`plots/RESULT_OVERVIEW.html`，并在 `AWAITING_USER_REVIEW` 停止。默认只展示
2–5 条关键波形：

```yaml
visualization:
  mode: compact
  style: CLASSIC_LOCKED
```

经典后端固定为 `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`。
`-j 2pi` 是对 raw phase radians 做数值 `/(2*pi)`，不是 SFQ 计数。`full`
必须显式 opt-in，仍保持 classic style；alternative style 需要用户明确授权，
且 V1 不提供第二套 backend。

## Strict local evidence

`scripts/bvmtools/phase.py` 和 `sfq.py` 提供共享算术和确定性 segment 路径。
任何分类必须携带完整的 `StrictLocalEventSpec`：同一 JJ 的 phase/voltage
列、端点、`voltage_to_phase_sign`、`reporting_direction`、run/window、raw
SHA-256、METRIC_SPEC 版本/hash 和 task-local frozen tolerance。缺少其中任一
项时只报告 raw arithmetic，classification 为 `INCONCLUSIVE`。

公共工具输出的 compatibility label 只用于明确的历史 Anchor 兼容 profile。
`complete_segment_count`、`whole_turns_floor_diagnostic` 和 waveform activity
都不是 event/SFQ count；local phase/area 也不证明 downstream reception 或
system Gate。

## Result brief 的固定内容

每个 future result 必须回答：

1. WHAT WE CHANGED；
2. WHAT WAS HELD FIXED；
3. WHAT HAPPENED；
4. WHAT IT MEANS；
5. WHAT IT DOES NOT PROVE；
6. 图的位置；
7. 当前状态和最多三个下一选项。

工具不会自动设计、扫参、Promotion 或下一项物理实验。
