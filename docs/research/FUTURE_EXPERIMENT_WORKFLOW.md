# Future Experiment Workflow V2

本文是普通 JoSIM/BVM 研究的 Compact Quick 入口。显式 Codex↔Claude 合同仍由
research/WORKFLOW.md 的冻结 josim-handoff/v1 处理；历史实验目录不批量迁移。

未来新的 BVM→QB→JTL→T1 功能验收默认使用：

```text
docs/research/BOUNDARY_SPEC_V2.md
```

`BOUNDARY_SPEC_V1.md` 仅保留为旧 A001 retrospective contract，不追溯改写历史结果。
测量/报告语义仍由 frozen `docs/research/METRIC_SPEC_V2.md` 定义。

## 日常路径

QUESTION → MINIMUM QUICK → RESULT → USER REVIEW → NEXT or ARCHIVE

普通 Quick 默认只回答一个主要问题，改变一个中心变量，并采用最少的方向性
case。结果必须停止在 AWAITING_USER_REVIEW，不自动设计或执行下一项物理实验。

## Compact 目录

experiment.yaml
run.sh
RESULT_BRIEF.md
runs/A001/deck.cir
runs/A001/raw.csv
runs/A001/run.log
runs/A001/result.yaml
plots/RESULT_OVERVIEW.html

使用 scripts/templates/compact-quick/ 的薄 run.sh。入口命令为：

    ./run.sh
    ./run.sh run
    ./run.sh analyze A001
    ./run.sh plot A001
    ./run.sh inspect A001

run 使用 scripts/bvm-exp.py 创建下一个 Axxx，绝不覆盖已有 attempt。analyze
只读现有 raw；plot 只重建 CLASSIC_LOCKED classic 图；inspect 只打印
question、changed、attempt、HEAD、result 和 status。result.yaml 是小型机器
记录，不再要求普通 Quick 额外维护 PREFLIGHT、REPORT、REVIEW、human-gate、
provenance 或 metrics 文件。

## 两种生命周期

- QUICK：raw QA、相关 metric、RESULT_BRIEF 和 compact classic visualization。
- FORMAL：只有用户明确要求时才启用 controls、收敛、完整 provenance 和独立复核。

不再把 PROMOTION 作为单独生命周期。Quick 可以提出 Formal 选项，但用户决定
是否继续，工具不自动升级。

## 风险触发验证

| 风险 | 追加验证 |
|---|---|
| 参数或输入小改动 | raw QA + 目标 waveform/metric |
| 新拓扑或节点重连 | KCL/拓扑端点验证 |
| canonical vs historical source 切换 | source identity + topology/parameter diff；禁止默认等价 |
| 电路迁移 | 一次等价性比较 |
| 共享科学工具改动 | focused tests + frozen anchors |
| QB quantization/count 主张 | `BOUNDARY_SPEC_V2` B1/B2 + same-JJ phase/area + expected-count check |
| QB→JTL 主张 | `BOUNDARY_SPEC_V2` B3 + burst-total/count/polarity/forward-transport evidence |
| BVM stored-state/flux claim | registered closed-loop fluxoid consistency；不能只看单个 JJ 或 `LI/Phi0` |
| Formal、论文或 system Gate | matched controls + preregistered timestep/convergence + 完整 provenance + 独立复核 |

默认 Quick 不机械要求时间步梯、完整四角色控制矩阵、KCL、迁移等价性、独立
reviewer、长报告或每个 Git 输入的重复哈希；这些要求由风险触发。

但一旦结论用于**设计参数推荐、正确 pulse/count 主张或推进 system boundary**，
`BOUNDARY_SPEC_V2` 将 numerical robustness 视为硬条件：关键功能分类必须在
预注册的 fine refinements 上保持一致；不得用一个较粗 timestep 的有利结果覆盖
更细 timestep 的功能变化。

## 共享规则

优先复用 scripts/bvmtools/、presets 和 scripts/josim-plot2.py。raw P(...) 保留
radians；turns 显式除以 2π。local phase/activity 不自动是 SFQ，local event 不
自动是 downstream transport；需要物理解释时加载 josim-evidence-audit。

从 `BOUNDARY_SPEC_V2` 起采用 **functional-first**：

- dense SFQ burst 可以是正常工作方式；不冻结统一 minimum inter-pulse spacing；
- 旧 `0.25 ps` quiescent gap 仅是 strict/diagnostic，不是 Functional PASS 硬门槛；
- expected QB count、JTL end-to-end count/polarity、downstream logic correctness 是硬功能标准；
- same-JJ phase/area 与注册 closed-loop fluxoid consistency 是硬 physics supporting checks；
- exact per-stage pulse separation、很小 ringing、理想 pulse morphology 属于 strict/robustness 层，除非它们已经破坏功能。

默认可视化为 sep_comb、dark、compact、CLASSIC_LOCKED，只画关键数据。拓扑图
由 josim-viz 使用实际网表和元件符号；Graphviz 仅作 debug/provenance。

## 状态

允许的简单状态为 READY、RUNNING、AWAITING_USER_REVIEW、REVIEWED、ARCHIVED。
用户审阅是唯一重要 gate；代理不得自行填写 REVIEWED、扩大 scope 或启动下一项
实验。项目当前科学状态见 docs/research/CURRENT.md。
