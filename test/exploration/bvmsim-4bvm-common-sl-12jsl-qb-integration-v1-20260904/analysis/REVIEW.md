# Numerical / adversarial review record

## Review scope

这是对本轮 raw、分析和可视化的机械与反事实检查记录，不是 Formal scientific Gate。最终人工状态仍为 `AWAITING_USER_REVIEW`。

## Numerical checks

- 10 个 receiver raw 均由固定 solver `v2.7.2837d13` 返回 exit code 0，且每个 run 有独立 deck/raw/log/metadata。
- 每个 raw 有 1549 个样本，范围为 45.0--199.9 ps；`.tran 0.1p` 是 nominal 请求步长，实际保存网格为非均匀 0.1--0.2 ps，并在 62.8→63.0 ps 出现一个 0.2 ps 间隔。receiver-loaded 10 个 raw 之间，以及与 prior passive same-mask raw 之间，时间网格均逐点一致；READ 窗口不包含该间隔，积分使用实际 time，分析使用 `interpolation=None`。
- 原始 `P(...)` 按 JoSIM radians 处理；只有明确的 phase table/plot 渲染使用 `continuous_unwrap(rad)/(2*pi)`。HTML 使用 `josim-plot2.py -t sep_comb -c dark -j 2pi`，可视化 QA 检查到 54 个 phase pages，0 个 Unknown axis title。
- common-SL KCL、JSL series KCL、JSL12→LIN boundary KCL 和 QB 内部三个节点 KCL 均用 `bvmtools.kcl` 计算；最大 READ residual 分别约为 `6.0e-5 µA`、0、`1.0e-7 µA` 和 `1.2e-4 µA` 量级。
- BJ2/JTL phase 与 voltage-area 只在同一 JJ、同一 READ window 上交叉检查；strict event list 使用共享 `bvmtools.sfq`，其 task-local thresholds 明确标为 `POST_HOC_EXPLORATORY`，结果仍只标为 local diagnostic。

## Adversarial checks

- 约 3 turns 的 BJ2 continuous running 被保留为 running trajectory，没有改写成 3 个 clean SFQ；population 2 的最大段 `0.995929 turns` 则明确记录为接近但未达到 `1.0-turn` threshold 的边界分类。
- JTL6 的 local clean segments 没有被倒推为 BJ2 已产生或系统已接收相同数量的 SFQ；population 3 的 JTL6 B02 首段 segment-start `116.6 ps` 早于 JTL1 B01 complete-segment start `119.6 ps`，构成端到端因果次序反例。
- receiver-loaded 与 passive 的上游差异按 same-mask raw 直接报告，未把它隐藏在 JSL chain 的 series consistency 后面；该表述排除了绘图、插值和后处理来源，但没有声称已排除 timestep/discretization 影响。
- 单 active 四个位置逐点相同的结果没有被扩大为所有 array/topology 的位置无关性结论。
- 设置提交后工作树清洁才运行；没有修改 canonical BVM、历史 passive raw、QB/JTL source 文件或任何实验参数。
- 没有运行 timestep sweep、20 GHz、参数 sweep、direct-QB/open boundary 或自动 follow-up。
- `upstream_unclassified_change_count=0` 只表示预检器覆盖的 BVM/source/JSL tuple 未改变；它不是对任意额外器件的通用证明。对本轮十份 deck 做了直接枚举，未发现额外的上游物理器件差异。

## Open limitations

- 本轮不是 timestep convergence proof；`.tran` 设置固定，实际保存网格含一个 0.2 ps 间隔，且 strict tolerance 是 task-local `POST_HOC_EXPLORATORY` diagnostic，不是 Formal freeze。
- 机制归因仍是 bounded inference：目前能定位到“终端边界变化造成 loading/back-action”，不能唯一定位到 QB 内部哪个动态支路是原因。
- population 2 的 BJ2 `0.995929 turns` 位于 complete threshold `1.0 turns` 附近；因此该处的 0-complete 标签不应被解读为稳健的无局部活动结论。
- JTL6 B02 的 segment-start timestamp 不是已校准的 SFQ 到达时间；JTL6 local segments 与 BJ2/JTL1 的事件身份和时序未形成端到端闭环。
- 仍需用户审阅后才能决定是否授权后续工作。

## Sol XHigh review record

- 首次只读审阅结论为 `REWORK_REQUIRED`，原因是证据等级、实际保存网格、阈值邻近性、JTL 局部时间戳和最终 hash closure 的记录需要收窄；不是 raw 或核心算术失效。
- 已按审阅意见修正：明确 `POST_HOC_EXPLORATORY`；记录 1549 点、45.0--199.9 ps 和 62.8→63.0 ps 间隔；把 JTL6 时间称为 segment-start timestamp；补充 population 2 的 `0.995929-turn` 边界；把 passive baseline 改为中性 comparison baseline；缩窄 `upstream_unclassified_change_count` 的证明范围；并在最终 provenance 中覆盖结论、入口和 setup 文件。
- JTL1 B01 的事实表述已校正为“有 complete segment、无 clean separated segment”；population 3 的 JTL6 B02 首段仍早于该段起点，因此不构成端到端 event identity。
- 本记录不把 reviewer 的审阅变成用户批准；最终 gate 仍是 `AWAITING_USER_REVIEW`。

## Disposition

```yaml
artifact_status: VALID_AT_REVIEW_SNAPSHOT
analysis_arithmetic: VALID
source_back_action_inference: SUPPORTED_BOUNDED
strict_local_classification: POST_HOC_DIAGNOSTIC_ONLY
end_to_end_bj2_to_jtl6_transport: INCONCLUSIVE
qb_logic_or_sfq_count: NOT_ESTABLISHED
timestep_convergence: NOT_ESTABLISHED
review_status: REWORK_CORRECTED_PENDING_PROVENANCE
user_reviewed: false
next_step_authorized: false
automatic_followup: false
state: AWAITING_USER_REVIEW
next_action: STOP
```
