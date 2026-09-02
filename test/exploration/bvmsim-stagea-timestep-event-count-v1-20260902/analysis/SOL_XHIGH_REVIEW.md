# Sol XHigh 科学审阅

- reviewer：`josim_architect`（Sol XHigh，read-only）
- agent：`01a061fe-4cc0-7d01-8d77-472b0b1f09e9`
- 审阅记录时间：`2026-09-02T20:16:29+08:00`
- 审阅动作：未修改文件，未运行 JoSIM、测试或新物理实验
- 处置：`PARTIALLY_SUPPORTED`

## 总结 verdict

对“timestep-induced numerical branch change candidate”是**部分支持（中等偏强）**。

更精确的表述是：在固定的 4-BVM exploratory fixture、固定 JoSIM binary 和相同有效电路下，仅改变 `.tran` nominal timestep 时，0.1 ps 轨迹稳定复现约 4-turn 分支，而 0.05/0.025/0.0125 ps 落入约 5-turn 的另一数值轨迹分支。这支持 timestep-conditioned/induced numerical branch-change candidate，但不证明 timestep convergence、正确物理解、4→5 个 SFQ event，或第五事件完成了 BJ2→JTL6 传输。

实验 artifact 可判为 `VALID`；事件计数、event identity transport 和收敛结论仍为 `INCONCLUSIVE`。

## Observed

- T100 raw 与 Stage-A M0 raw 的 SHA-256 相同；与历史 BVMSim raw 的 1549 个共同时间点、16 个共同列逐点吻合。电流和 phase token-exact，电压差约 `1e-13 V` 或更小。不同列集合的文件不应被称为整体 byte-identical。
- T100_FULL 与 T100 在 45 ps 之后的 1549 个共同样本上吻合，因此 print-start 不是 4-turn 轨迹的充分解释。
- T025 raw 与 Stage-A S1 raw 的 SHA-256 相同。
- 五个有效 migrated deck 在归一化 `.tran` 后相同；BVM、QB、六级 JTL、source、bias、load、模型和 solver binary 固定。有效 include 路径解析到已记录的仓库文件。
- BJ2 READ1 net phase 为：T100 `3.999517`、T050 `4.998204`、T025 `4.999188`、T0125 `4.999092` turns。
- BJ2 在每个 timestep 都是一个连续多-turn 主段，而非四个或五个 clean separated events：T100 主段约 `3.985 turns`，细 timestep 主段约 `4.011–4.024 turns`，随后为约 `0.923–0.974 turn` 的不足一转残余；strict helper 给出一个 complete segment、零个 clean separated event。
- READ0 的 QB/JTL junction 在所有 timestep 下均无 complete 或 clean segment；非 READ1 窗口没有完整额外事件。T100 WRITE1 的 JTL1.B01 有约 `0.984-turn` 的近阈值段。
- JTL 的数值是 B01/B02 本地 stage summary，不能解释成守恒 transported count。细 timestep 下 JTL6.B02 有第五个完整 clean segment，但其 B01 只有两个 clean segment，且首个 B02 clean segment早于首个 B01 clean segment。
- KCL 最大绝对残差约 `1.4e-4 µA`；这支持电流方向和算术自洽，不证明分支正确、收敛或事件来源。

## Derived

- T050/T025/T0125 在约 5-turn 轨迹上有定性稳定性；T025 与 T0125 的 BJ2 net-turn 差约 `9.65e-5 turn`。这不是 convergence proof，因为没有误差阶、外推、预注册停止带或不同积分控制验证。
- `.tran` 是矩阵中唯一改变的有效 deck 项，因此 timestep intervention 与轨迹分支改变的关联很强；但数值积分路径、未充分收敛和非线性吸引域/分支选择仍是竞争解释。
- 117.3 ps 是 JTL1.B01 phase-only 阈值交叉，120.4 ps 是 BJ2 phase+voltage paired 阈值交叉。它们使用不同判据，不能推出 JTL 先导致 BJ2，也不能反向推出 BJ2 先导致 JTL。
- `independent_recheck.json` 独立复算了 unwrap、net phase 和同段梯形 voltage-area，但复用了主分析给出的 segment boundaries；它验证算术，不构成独立事件分割、event identity 或因果验证。

## Inference

- “固定数值 fixture 中存在 timestep-conditioned numerical branch-change candidate”：**中等偏强支持**。
- 当前允许的 primary label `CONTINUOUS_MULTI_TURN_RUNNING_STATE` 可保留，但应按“有限约四-turn 连续段，随后不足一圈残余、较晚 tail 稳定”理解；不能声称主段后的严格 retrap/bounded gate 已通过，也不能把它理解成无界自由运行。
- `QUICK_OPPOSITE` 仅表示它与 clean、分离、逐事件传输预期相反；不表示 artifact invalid、branch candidate 被否定、整个架构失败或物理上不存在 SFQ 活动。
- JTL6.B02 第五完整段只能作为一个 per-junction 本地候选记录；不能称为第五个 BJ2 event，也不能称为已验证的 transported event。不同 junction 的候选顺序不承载起源、前驱或因果传播。

## Unknown

- 约 5-turn 分支是否为 timestep 收敛极限、正确物理解或稳定物理工作点。
- 0.1 ps 分支是积分误差、吸引域切换、非线性分支选择，还是其组合。
- BJ2 连续多-turn 段及不足一转残余如何映射到可识别 SFQ event。
- JTL6.B02 第五段的局部生成、重整形、反馈和上游残余各自贡献。

## 对报告/工具的要求及已落实修正

1. 本实验保留允许的 `CONTINUOUS_MULTI_TURN_RUNNING_STATE` 标签，并在分类 reason/结果摘要中说明它是有限约四-turn 连续段加不足一圈残余和较晚稳定 tail；不声称严格 retrap/bounded gate 已通过，也不是无界 free-running。
2. `transport_read1.stages.*` 改用 `local_stage_summary_count`，并显式写入 `NO_EVENT_IDENTITY_MATCH`；矩阵摘要不再使用 `transported_event_count` 命名。
3. `event5_origin` 改为 `event5_candidate_ladder`，按 junction 做描述性候选排序，不暗示因果来源；可视化也改名为 `RESULT_EVENT5_CANDIDATE_ORDER`。
4. 共享 `StrictLocalEventSpec` 保留其为完成严格分类所需的操作性 `FROZEN` 阈值，同时增加独立的 `provenance_status: POST_HOC_EXPLORATORY`；后置性质写入 `analysis/POST_HOC_AMENDMENT.md`，不把后置分析包装成预注册 Gate。
5. `FIRST_DIVERGENCE.md` 已明确 117.3/120.4 ps 是不同判据的 threshold crossings，不承载因果顺序。
6. `EVENT_COUNT_CONVERGENCE.md` 已将细网格定性稳定性与 timestep convergence proof 分开。

## 明确回答 4→5

- 对“改变 timestep 后，在固定 fixture 中选择了另一条 deterministic numerical trajectory branch”：**部分支持，中等偏强**。
- 对“已经证明 timestep convergence 或唯一数值机制”：**不可判定**。
- 对“4 个事件变成 5 个 SFQ event”：**不支持**。
- 对“第五个 BJ2 event 被完整传输至 JTL6”：**不支持；当前 event identity 无法配对**。

因此只保留 branch-change **candidate**，维持 Exploration/Quick 身份，不升级为 physical Gate、metric freeze、route conclusion 或 paper-level mechanism claim。用户 review 仍是最终人类 gate。

## 最终修正后复核

- reviewer：`josim_architect`（Sol XHigh，read-only）
- agent：`01a0620d-21c1-70c3-b4c8-7f3cea8c23a4`
- 复核时间：`2026-09-02T20:31:13+08:00`
- 结果：`PASS`

复核确认：metrics 仅保留 `candidate_caveat / definition / ladder`，明确为 per-junction 描述性排序；分类理由正确限定为有限连续多-turn 段、亚单位残余和较晚稳定 tail；analyzer、independent recheck、renderer 的哈希与 provenance 一致。最终科学 verdict 不变：artifact `VALID`；branch-change candidate 部分支持（中等偏强）；timestep convergence、事件身份和机制仍为 `INCONCLUSIVE`；`CONTINUOUS_MULTI_TURN_RUNNING_STATE` 与 `QUICK_OPPOSITE` 保留限定语义。用户 review 仍是最终 gate。
