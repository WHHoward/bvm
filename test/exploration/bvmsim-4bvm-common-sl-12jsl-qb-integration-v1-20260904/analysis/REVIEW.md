# Numerical / adversarial review record

## Review scope

这是对本轮 raw、分析和可视化的机械与反事实检查记录，不是 Formal scientific Gate。最终人工状态仍为 `AWAITING_USER_REVIEW`。

## Numerical checks

- 10 个 receiver raw 均由固定 solver `v2.7.2837d13` 返回 exit code 0，且每个 run 有独立 deck/raw/log/metadata。
- receiver-loaded 10 个 raw 之间，以及与 passive same-mask raw 之间，时间网格均逐点一致；分析使用 `interpolation=None`。
- 原始 `P(...)` 按 JoSIM radians 处理；只有明确的 phase table/plot 渲染使用 `continuous_unwrap(rad)/(2*pi)`。HTML 使用 `josim-plot2.py -t sep_comb -c dark -j 2pi`，可视化 QA 检查到 54 个 phase pages，0 个 Unknown axis title。
- common-SL KCL、JSL series KCL、JSL12→LIN boundary KCL 和 QB 内部三个节点 KCL 均用 `bvmtools.kcl` 计算；最大 READ residual 分别约为 `6.0e-5 µA`、0、`1.0e-7 µA` 和 `1.2e-4 µA` 量级。
- BJ2/JTL phase 与 voltage-area 只在同一 JJ、同一 READ window 上交叉检查；strict event list 使用共享 `bvmtools.sfq`，其结果仍标为 local diagnostic。

## Adversarial checks

- 约 3 turns 的 BJ2 continuous running 被保留为 running trajectory，没有改写成 3 个 clean SFQ。
- JTL6 的 local clean segments 没有被倒推为 BJ2 已产生或系统已接收相同数量的 SFQ。
- receiver-loaded 与 passive 的上游差异按 same-mask 直接报告，未把它隐藏在 JSL chain 的 series consistency 后面。
- 单 active 四个位置逐点相同的结果没有被扩大为所有 array/topology 的位置无关性结论。
- 设置提交后工作树清洁才运行；没有修改 canonical BVM、历史 passive raw、QB/JTL source 文件或任何实验参数。
- 没有运行 timestep sweep、20 GHz、参数 sweep、direct-QB/open boundary 或自动 follow-up。

## Open limitations

- 本轮不是 timestep convergence proof；`.tran` 设置固定，且 strict tolerance 是 task-local exploratory diagnostic，不是 Formal freeze。
- 机制归因仍是 bounded inference：目前能定位到“终端边界变化造成 loading/back-action”，不能唯一定位到 QB 内部哪个动态支路是原因。
- 仍需用户审阅后才能决定是否授权后续工作。

## Disposition

```yaml
artifact_status: VALID
analysis_status: VALID
physical_interpretation: BOUNDED_DESCRIPTIVE_ONLY
user_reviewed: false
next_step_authorized: false
automatic_followup: false
state: AWAITING_USER_REVIEW
next_action: STOP
```
