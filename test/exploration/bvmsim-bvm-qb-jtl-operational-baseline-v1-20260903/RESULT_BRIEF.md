# Historical BVMSim operational baseline V1

## 1. What changed

建立并运行了 historical BVMSim original-QB baseline：single-BVM 2×2、完整
4-BVM 16-state 矩阵，以及每个 run 的独立关键数据可视化。`RJ1=12 Ω` 保持
nominal；本轮没有把任何其它阻值替换成设计值。

## 2. What held fixed

使用 `BVMSim/bvm_cell.cir`、`BVMSim/BQ.cir`、`BVMSim/library_josim/jtl2.cir`，
QB=`IB 250 µA, RJ1=12 Ω, RJ2=4 Ω`，JTL 六级、280 µA 内部 bias、末端 10 Ω，
工作步长 `0.1 ps`。未使用 canonical BVM、未改 RJ2/JJ area/L/C/JTL/timestep，
未进入 T1。第一次 single-JTL deck 漏掉了 JTL P/V 探针；旧 raw 保留，新增
`attempt-02` 只补探针后重新采集，物理 netlist/参数不变。

需要特别区分 model closure：single-BVM original-BQ deck 的日志出现
`Missing model: JJMIT`/`Using default model`，而 4-BVM historical fixture 有可见的
顶层 `jjmit` model。本轮没有偷偷加入 shared model；因此四个 single-BVM 记录的
intended-model artifact status 是 `INVALID`，不把它们当作与 4-BVM 同一有效材料模型
下的物理 PASS/FAIL。

## 3. What happened

- single-BVM：raw-derived 观察中两个 logical-0 control 的 QB/output-side burst
  为 0，两个 logical-1 run 的 QB（JTL run 的 JTL6 也为 0）未出现 burst；但由于上述 model closure warning，四个记录均为
  `ARTIFACT_INVALID`，只作 historical 2×2 诊断，不形成 single-BVM 物理 verdict。
- 4-BVM：16 个状态均已运行；`0000` 和 `0100` 的 burst 与预期相符，`1111`
  的 burst-total 为约 4，但 `0001`、`0010` 以及多数多 active 状态出现高于
  `popcount` 的输出。故 historical fixture 的 commanded-state mapping 失败。
- `1111` 的 QB `BJ2` 是一个约 3.985-turn 的连续 running segment，不是四个
  clean separated QB events；JTL6 的 `B02` 可见 4 个 output-facing local
  transitions。逐级 integer phase crossing 的时序顺序支持有限的 forward burst
  propagation 描述，但不支持“四个 QB 独立 SFQ”或逐事件身份追踪。
- 五个 4-BVM 非 READ1 窗口中，QB BJ2/JTL6 没有 complete spontaneous/extra
  event；QB 内部三个 KCL 方程的最大 READ1 残差不超过 `0.00014 µA`。所有 raw
  requested `0.1 ps`，但存储网格各有一次 `62.8→63.0 ps` 的 `0.2 ps` 间隔，
  并非严格 uniform grid；分析使用实际时间列且不插值。

详表见 [`analysis/BASELINE_REPORT.md`](analysis/BASELINE_REPORT.md)，图索引和
raw/hash QA 见 [`analysis/visualization_manifest.json`](analysis/visualization_manifest.json)。

## 4. Physical meaning

本轮支持的最稳妥解释是：在 historical BVMSim source、nominal original QB 和
`0.1 ps` operational profile 下，historical fixture 的 commanded-state output
对 state/position 很敏感，部分状态出现明显的 burst-total count mismatch；QB
局部连续运行与 JTL 后段的 output-facing event-like structure 不同。这里的
“overdrive” 只是允许的探索性分类，不是已经证明的器件机理；BVM2–BVM4 的内部
存储态也没有被当前 probes 完整闭合，因此不能把 mismatch 唯一归因于 QB。

## 5. What this does NOT prove

不证明 canonical BVM compatibility、single-BVM 普遍兼容或不兼容、timestep
convergence、process/RJ1 working margin、T1 compatibility、论文机制身份或唯一
QB operating mechanism，也不证明一个 BVM contribution 必然对应一个 downstream
SFQ。

## 6. Current status

`BASELINE_FUNCTIONAL_FAIL`；evidence descriptor=`HISTORICAL_FIXTURE_COUNT_MISMATCH`；
允许的探索性 primary classification=`SELECTIVITY_OR_OVERDRIVE_FAILURE`；quick
label=`QUICK_OPPOSITE`。由于 nominal baseline 未通过预注册 stop rule，IB、RJ1、
input-alpha 以及 pairwise margin 均为 `NOT_RUN`；`RJ1=12 Ω` 未被替换。具体
strict-event 阈值属于 post-hoc exploratory diagnostic，不是 Formal acceptance Gate。

## 7. Possible next options（均未执行）

1. 用户审阅本轮 raw、独立图和 baseline failure 证据。
2. 另行授权针对失败状态的 bounded diagnostic，先确认 state/position 依赖。
3. 另行授权 canonical-BVM 对照或 T1 integration；不由本轮自动触发。

## Current gate

`AWAITING_USER_REVIEW`；`user_reviewed=false`；`next_step_authorized=false`；
`automatic_next_experiment=false`；`stage_b_authorized=false`。
