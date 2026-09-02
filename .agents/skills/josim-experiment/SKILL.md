---
name: josim-experiment
description: Design or run a reproducible JoSIM/BVM Quick or explicitly requested Formal experiment. Use for circuit changes, new raw data, or candidate evaluation; do not use it to interpret physical SFQ claims without josim-evidence-audit.
---

# JoSIM/BVM 实验

## 默认：Compact Quick

普通研究默认是 QUICK，先回答一个问题、改变一个中心变量，并只运行足够
区分方向的最小 case。新实验目录优先使用 experiment.yaml、run.sh、
RESULT_BRIEF.md、runs/A001/{deck.cir,raw.csv,run.log,result.yaml} 和
plots/RESULT_OVERVIEW.html。

用 ./run.sh 或 scripts/bvm-exp.py run <experiment-dir> 创建下一个不可覆盖的
Axxx。analyze 只读已有 raw，plot 只重建 classic 图，inspect 只输出问题、
改变项、attempt、HEAD、结果和状态。结果完成后停在 AWAITING_USER_REVIEW；
代理不得自动运行下一项物理实验。

配置必须明确 question、changed、frozen、网表、求解器和最少关键指标。
每个 attempt 保存 Git HEAD、solver identity/version、命令、deck/raw SHA-256、
artifact validity、相关 metrics、outcome 和 status。raw、deck、log 和 result
不得覆盖；重复运行生成新的 attempt。

## 按风险增加验证

| 风险 | 在 Quick 中追加 |
|---|---|
| 参数或输入小改动 | raw QA + 目标 waveform/metric |
| 新拓扑或节点重连 | KCL/拓扑连线检查 |
| 电路迁移 | 一次等价性比较 |
| 共享科学工具改动 | focused tests + frozen anchors |
| QB→JTL 主张 | 同 JJ local phase/area + 逐级 transport evidence |
| Formal、论文或系统 Gate | matched controls、收敛、完整 provenance、独立复核 |

不要为了流程仪式自动要求时间步梯、完整控制矩阵、全量哈希或长报告；
缺少与当前问题相关的证据时，再把结果降为 INCONCLUSIVE。

## 共用边界

- 优先复用 scripts/bvmtools/、scripts/bvmtools/presets.yaml 和
  scripts/josim-plot2.py；不要在实验目录复制 raw parser、phase 或事件算法。
- JoSIM P(...) 保留 raw radians；相位圈数显式除以 2π，不等于 SFQ 或
  fluxoid count。需要相位、事件数、JTL 或 Gate 解释时加载
  josim-evidence-audit。
- raw QA 失败是 artifact INVALID，不是电路功能 FAIL；观察、推断和未知
  分开写入 RESULT_BRIEF.md。
- Compact Quick 不自动扫参、升级 Formal、创建控制矩阵或修改项目路线。

## Formal

只有用户明确要求时才进入 FORMAL。此时阅读 references/run-protocol.md，
按问题冻结输入闭包、控制、窗口、指标、收敛和独立复核。josim-handoff 只在
存在明确 Codex↔Claude 合同、ACK/receipt、正式委派审计或等价多代理交接时加载。
