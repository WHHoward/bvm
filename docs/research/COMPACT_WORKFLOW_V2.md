# Compact JoSIM Research Workflow V2

> 当前未来实验的规范已冻结在
> [EXPERIMENT_WORKFLOW_V1.md](EXPERIMENT_WORKFLOW_V1.md)。本文仅保留既有
> Compact Quick 目录和命令的历史兼容说明，不覆盖 V1 的执行顺序、冻结
> deck 权威、两阶段 preflight、standalone-first 可视化和 human-gate 要求。

## 默认路径

PRE-REGISTER → PREFLIGHT → PHYSICAL SOLVE → MECHANICAL QA → STANDARD
VISUALIZATION → EVIDENCE PACKAGE → COMMIT EXPERIMENT + PACKAGE → STOP /
AWAITING_SCIENTIFIC_REVIEW

普通 Quick 使用一个中心问题、一个主要改变项和最少能区分方向的 case。
它不是 Formal，也不会自动升级为物理 Gate。

## 目录和命令

新实验目录包含：

experiment.yaml
run.sh
PREFLIGHT.md
RESULT_BRIEF.md
runs/A001/
  deck.cir
  raw.csv
  run.log
  result.yaml
  metadata.json
analysis/
  raw_qa.json
  deck_diff_qa.json
  provenance.json
  execution_summary.json
  transformation_registry.json
  visualization_manifest.json
  visualization_qa.json
  run_summaries/A001.md
human-gate.yaml
EVIDENCE_MANIFEST.md
SOURCE_MANIFEST.json
RAW_ANALYSIS_HANDOFF_MANIFEST.json
plots/RESULT_OVERVIEW.html
handoff/<experiment_id>_raw_handoff.zip
handoff/PACKAGE_QA.json

以 scripts/templates/compact-quick/ 为起点。薄 run.sh 只转发命令，不含
科学算法：

    ./run.sh
    ./run.sh run
    ./run.sh analyze A001
    ./run.sh analyze A001 --scientific-review-authorized
    ./run.sh plot A001
    ./run.sh package A001
    ./run.sh inspect A001

run 自动创建一个不可覆盖的 Axxx，绝不覆盖已有 attempt；它默认只执行
mechanical QA，不计算 scientific metrics。analyze 默认只重做 raw-only QA；
只有显式 `--scientific-review-authorized` 才生成独立、版本化的 scientific
review artifact。plot 只生成 descriptive classic 图，package 只打包现有证据，
inspect 只打印状态。完成 package 后状态为
`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`，代理不自动执行下一项
物理实验。

result.yaml 是未来 Quick 的小型机器记录，至少包含 Git HEAD、solver
identity/version、命令、deck/raw 哈希、artifact validity、mechanical QA、
evidence-ready outcome 和 status。raw、deck、log、metadata 和 result 属于
attempt；raw 与 package 不得覆盖。`PACKAGE_QA.json` 在重新打开 ZIP 后验证
全部 authorized runs 和 hash，ZIP 默认直接提交 Git；QA 文件因自哈希循环保持
在 ZIP 外。

## Quick 与 Formal

- QUICK：方向性实验执行；默认只做 raw/mechanical QA、标准 descriptive
  visualization、短的 evidence-only summary 和 immutable evidence ZIP。
- FORMAL：只有用户明确要求才进入；追加匹配 controls、时间步/收敛、完整
  provenance、独立复核和更强 claim criteria。

任何 scientific interpretation、parameter ranking、winner、root cause 或
机制分析都必须在停止后的独立 review 阶段，并有明确
`SCIENTIFIC_REVIEW_AUTHORIZED`；该授权不等于新的 solve authorization。

不再把 PROMOTION 当作独立生命周期。Evidence-only summary 不提出 Formal 或
下一实验建议；用户可在独立 review 后另行授权新的注册流程。

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

BVM→QB→JTL 的标准 profile 使用 V2.1 五层：
`01_SIGNAL_TIMING`、`02_BVM_STATE`、`03_JSL_CHAIN`、`04_QB_STATE`、
`05_JTL_CHAIN`；每层必须有 `INPUT -> INTERNAL -> OUTPUT`、whole-run
overview 和 registered focused windows。Standalone 与 comparison 复用同一
semantic signal schema；额外 mechanism/dashboard 图不属于默认输出。

历史实验目录、raw、旧报告、josim-handoff/v1 和旧协议引用不批量迁移。显式
Codex↔Claude 合同、ACK/receipt 或正式委派审计仍单独使用 josim-handoff。

## 当前科学状态

截至 2026-09-02，Stage A 已导入 BQ_BVMSIM_V1 并完成迁移等价性；strict
诊断未支持四个 separated SFQ，而是得到
CONTINUOUS_MULTI_TURN_RUNNING_STATE。canonical BVM→该 QB 尚未测试，Stage B
未授权。最新证据入口见 docs/research/CURRENT.md。
