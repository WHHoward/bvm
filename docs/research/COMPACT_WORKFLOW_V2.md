# Compact JoSIM Research Workflow V2

> 当前未来实验的规范已冻结在
> [EXPERIMENT_WORKFLOW_V1.md](EXPERIMENT_WORKFLOW_V1.md)。本文仅保留既有
> Compact Quick 目录和命令的历史兼容说明，不覆盖 V1 的执行顺序、冻结
> deck 权威、两阶段 preflight、standalone-first 可视化和 human-gate 要求。

## 默认路径

QUESTION → MINIMUM QUICK → RESULT → USER REVIEW → NEXT or ARCHIVE

普通 Quick 使用一个中心问题、一个主要改变项和最少能区分方向的 case。
它不是 Formal，也不会自动升级为物理 Gate。

## 目录和命令

新实验目录包含：

experiment.yaml
run.sh
RESULT_BRIEF.md
runs/A001/
  deck.cir
  raw.csv
  run.log
  result.yaml
plots/RESULT_OVERVIEW.html

以 scripts/templates/compact-quick/ 为起点。薄 run.sh 只转发命令，不含
科学算法：

    ./run.sh
    ./run.sh run
    ./run.sh analyze A001
    ./run.sh plot A001
    ./run.sh inspect A001

run 自动创建下一个 Axxx，绝不覆盖已有 attempt。analyze 只读现有 raw，
plot 只生成 classic 图，inspect 只打印问题、changed、attempt、HEAD、结果
和状态。一次结果完成后状态为 AWAITING_USER_REVIEW；只有用户明确审阅后才
能变成 REVIEWED，代理不自动执行下一项物理实验。

result.yaml 是未来 Quick 的小型机器记录，至少包含 Git HEAD、solver
identity/version、命令、deck/raw 哈希、artifact validity、相关 metrics、
outcome 和 status。raw、deck、log 和 result 属于 attempt；重复执行创建新的
attempt。当前图是可再生的 human-facing convenience，不改变 raw 或结果判定。

## Quick 与 Formal

- QUICK：方向性筛选，默认 raw QA、目标 metric、简短 RESULT_BRIEF 和一张
  compact classic 图。
- FORMAL：只有用户明确要求才进入；追加匹配 controls、时间步/收敛、完整
  provenance、独立复核和更强 claim criteria。

不再把 PROMOTION 当作独立生命周期。Quick 可以在摘要中建议 Formal，但不能
自动生成或执行它。

## 风险触发验证

| 当前风险 | 追加验证 |
|---|---|
| 参数/输入小改动 | raw QA + 目标 waveform/metric |
| 新拓扑/节点重连 | KCL 和拓扑端点检查 |
| 电路迁移 | 一次等价性比较 |
| 共享科学工具改动 | focused tests + frozen anchors |
| QB→JTL 主张 | 同 JJ phase/area + 逐级 transport evidence |
| Formal/论文/system Gate | matched controls + convergence + 完整 provenance + 独立复核 |

这不是降低科研标准，而是把成本放到当前风险真正需要的位置。不要为普通
Quick 机械要求时间步梯、全控制矩阵、KCL、迁移等价性、独立 reviewer、长报告
或每个 Git 输入的重复哈希。

## 证据与可视化不变量

继续复用 scripts/bvmtools/；JoSIM raw P(...) 是 radians，turns 必须显式
除以 2π。local phase 不自动是 SFQ，local event 不自动是 downstream
transport。需要这些解释时加载 josim-evidence-audit。

默认可视化为 CLASSIC_LOCKED、sep_comb、dark、compact，使用
scripts/josim-plot2.py，只展示关键数据。拓扑图使用 josim-viz 的元件符号
和端点验证；Graphviz 只作 debug/provenance。

历史实验目录、raw、旧报告、josim-handoff/v1 和旧协议引用不批量迁移。显式
Codex↔Claude 合同、ACK/receipt 或正式委派审计仍单独使用 josim-handoff。

## 当前科学状态

截至 2026-09-02，Stage A 已导入 BQ_BVMSIM_V1 并完成迁移等价性；strict
诊断未支持四个 separated SFQ，而是得到
CONTINUOUS_MULTI_TURN_RUNNING_STATE。canonical BVM→该 QB 尚未测试，Stage B
未授权。最新证据入口见 docs/research/CURRENT.md。
