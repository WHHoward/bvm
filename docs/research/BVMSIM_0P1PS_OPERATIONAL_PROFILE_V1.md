# BVMSim 0.1 ps Operational Profile V1

```yaml
profile: BVMSIM_0P1PS_OPERATIONAL_PROFILE_V1
source_class: HISTORICAL_BVMSIM
role: PROJECT_OPERATIONAL_BASELINE
convergence_claim: NOT_CLAIMED
finer_timestep_history_preserved: true
bvm_source: BVMSim/bvm_cell.cir
qb_source: BVMSim/BQ.cir
qb_rj1_nominal_ohm: 12
qb_rj2_nominal_ohm: 4
qb_bias_nominal_uA: 250
jtl_source: BVMSim/library_josim/jtl2.cir
jtl_stages: 6
jtl_bias_nominal_uA: 280
termination_ohm: 10
simulation_timestep_ps: 0.1
solver: build/josim-cli
```

## 目的与边界

本 profile 冻结 historical BVMSim 的当前 operational reference，用于本
轮的 single-BVM、4-BVM 16-state baseline 以及后续有限 working-margin
characterization。`0.1 ps` 是工程工作步长，不是 `dt -> 0` 的收敛结论；过去
已经完成的更细步长实验继续保留，不能被本 profile 追溯改写。

本轮的 BVM authority 是 `BVMSim/bvm_cell.cir`，不是
`circuits/bvm/bvm_cell.cir`。两者不默认 electrically equivalent；已知差异为
historical `R_JM1=8 ohm`、canonical `R_JM1=6 ohm`。因此本 profile 不能被
解释为“canonical BVM 驱动 original QB”。

## 冻结的 nominal fixture

- QB 使用 `BVMSim/BQ.cir` 的 active `BQ IN OUT`，内部 bias 为
  `IB 0 3 pwl(0 0 1p 250u)`；原文件只读保留。
- QB 的 nominal shunt 是 `RJ1 2 0 12`，`RJ2 2 0 4`。本轮 RJ1 只作为
  `BJ1` 显式 shunt/component-design margin 轴，12 ohm 始终是 nominal，
  不因 margin 结果自动替换设计。
- BVM 到 QB 的 shared sensing line 沿用 historical 4-BVM fixture：每级
  12 个 `area=3.2` 的 JJ，最后一级的 `BVMout` 接入 `QBin`。
- JTL 使用原始 `BVMSim/library_josim/jtl2.cir`，六级串联，每级内部
  `IB01` 的 nominal bias 为 280 uA；末端使用 10 ohm 负载。
- 统一使用仓库记录的 `build/josim-cli`。

## 状态时序

4-BVM baseline 保留 historical 的实际时序：

1. `50--61 ps`：四个 BVM 都写入 logical-0（WL、BL 为 -100 uA）；
2. `70--81 ps`：READ0，作为 0-count control；
3. `90--101 ps`：按状态字对每个 BVM 写入 logical-0 或 logical-1，
   logical-1 的 WL、BL 为 +100 uA；
4. `110--121 ps`：READ1，状态 `b3b2b1b0` 的预期 active count 为
   `popcount(state)`。

因此 `1111` 与 historical active fixture 的 READ1 完全对应；16-state
不会改变初始化阶段。状态字的最高位对应 `BVM1`，最低位对应 `BVM4`，并在
每个 deck 的 metadata 中显式记录。

功能计数以同一 burst 窗口内的 phase/voltage-area 一致性和 downstream
JTL6 output-facing marker 为依据。phase 原始单位是 rad；报告中的 turns
只能由 continuous unwrap 后除以 `2*pi` 得到。net/burst phase turns、
burst area/Phi0、可解析的局部 event 结构和 downstream count 分开报告，
不把相位累计自动等同于 SFQ 计数。

## 变体规则

后续 margin 变体只能是 task-local derivative：`IB`、`RJ1` 和真实 baseline
`I(Lin|XBQ1)` 的 replay scale `alpha`。所有 BVM/JTL 拓扑、RJ2、JJ area、
JJ Ic、L/C、JTL bias、timestep、canonical BVM 和 T1 均保持冻结，除非另有
明确授权。margin 是对 nominal 12 ohm operational tolerance 的测量，不是
优化或替换 nominal 设计。

