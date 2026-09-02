# BOUNDARY_SPEC_V1

```yaml
spec_version: BOUNDARY_SPEC_V1
status: EXPLORATORY_ANALYSIS_CONTRACT
scope: retrospective analysis of frozen A001 raw only
physical_gate: false
strict_claim_ceiling: NOT_YET_QUALIFIED without convergence and robustness evidence
```

## 1. Evidence scope

本规范只定义现有 single-BVMSim matched 2×2 A001 的 Boundary 责任、局部窗口和
报告口径。它不授权重新运行 JoSIM，不改变任何网表、参数、raw CSV 或旧的
full-trace diagnostic。raw authority 是：

```text
test/exploration/bvmsim-bvm-qb-single-2x2-quick-v1-20260902/
  runs/A001/{S0-R,S1-R,S0-J,S1-J}/raw.csv
```

其中 `S0` 是 logical 0，`S1` 是 logical 1；`R` 是末端 10 Ω direct load，`J`
是六级 `jtl` 后接 10 Ω。所有数值必须注明 raw 路径、信号方向、单位和窗口。
本规范不把仿真写成硬件测量，也不把 Boundary verdict 升级为论文或路线结论。

## 2. Boundary responsibility

### B0 — BVM sensing / SL transmission

职责是：

```text
BVM stored state → state-dependent sensing waveform → 12-JJ SL load → QBin
```

B0 不要求 `BVMout` 或任何 `B_LD` junction 发生 `2π` phase slip。12-JJ SL
load 的主要职责是传递 sensing waveform；在没有不期望的完整 phase slip 时，
该 load 行为作为 guard / desired behavior 报告，不因此判 FAIL。

B0 检查：

- logical 0 与 logical 1 在 READ 附近的 `V(SL1)`、`I(L_SL|XBVM1)`、
  `V(QBIN)` 是否可区分；
- sensing waveform 是否到达 `QBin`；
- `I(BVMOUT)`、`V(BVMOUT)` 和 12-JJ line 是否显示不期望的 full phase-slip；
- `R` 与 `J` downstream load 存在时，state distinction 是否仍可见。

`BVMout` 没有 SFQ 不构成 B0 失败理由。

### B1 — selective QB triggering

职责是：

```text
state-dependent QBin waveform → state-selective QB switching response
```

核心检查为 state selectivity、READ timing association、`BJs/BJ1/BJ2` 响应和
false-trigger absence：logical 0 不应有目标 QB READ response，logical 1 应有
明确的 READ-associated response。B1 不要求输出已经恰好等于 `1 Phi0`；量子化
属于 B2。

`t≈0` 的 bias initialization activity 必须与 READ-local response 分开报告，
不能自动并入 READ event。

### B2 — local quantization

B2 的证据等级分为：

1. `SFQ_LIKE_RESPONSE`
   - READ-associated localized voltage response；
   - 有对应的 phase step / settling；
   - logical 1 明显而 logical 0 不出现同等级响应；
   - 不声称 exactly `1 Phi0`。
2. `QUANTIZED_LOCAL_SFQ_CANDIDATE`
   - 同一个局部 READ event 的 `|∫Vdt|/Phi0` 接近 1；
   - 同一 event 的 phase increment 与 voltage area 一致；
   - 不能由 initialization-only response 解释；
   - 没有第二个同等级、明显独立的 READ-local event。

   本次 exploratory engineering band 暂定为 `0.8–1.2 Phi0`，是 heuristic，
   不是物理自然边界；必须同时报告精确 area、phase、残差和相对 `1 Phi0`
   的偏差。
3. `STRICT_CLEAN_SFQ`
   - 还需要明确 event separation、退出主要 voltage state、无 uncontrolled
     running、count/polarity preservation、timestep convergence、对
     event-boundary/threshold 不敏感，以及必要的 robustness/repeat evidence。

A001 没有 timestep convergence，因此即使 local functional evidence 良好，
也只能标 `NOT_YET_QUALIFIED`，不能标 `STRICT_PASS`，更不能因缺少 strict
qualification 把 functional evidence 判成 FAIL。

### B3a — JTL acceptance / launch

职责是 `QB local response → QBOUT → JTL1`。在目标 JTL load 存在时检查：

- JTL1 是否接受 QB switching response；
- QB→10 Ω 与 QB→JTL 的差异作为 load backaction 报告，backaction 本身不判 FAIL；
- 目标 `QB+JTL1` 是否形成可工作的 operating behavior。

若 JTL load 使 QB waveform 更接近量子化，可作为有益 matching effect 报告，
但仍需相位—面积和因果证据。

### B3b — JTL transport

职责是：

```text
JTL1 → JTL2 → ... → JTL6
```

逐级检查 event/response 是否到达、timing 是否正向递增、polarity 是否保持、
是否丢失、是否额外 regeneration，以及每一级 output-side switching 的
`∫Vdt/Phi0` 与 phase increment。

根据冻结的 `BVMSim/library_josim/jtl2.cir`：`B01` 在输入侧，`B02` 位于
`L03/L04` 后并连接 cell output，因此本规范将 `B02` 作为 output-facing
transport marker；`B01` 作为 input-side/internal comparison marker。一个
JTL cell 内的 `B01` 与 `B02` 共同完成一颗 propagating SFQ 时，不把它们计成
两颗 SFQ。

### B4 — logic consumption

A001 没有 T1 或 downstream logic，因此：

```text
B4 = NOT_TESTED
```

## 3. Verdict vocabulary

每个 Boundary 分别报告两种层级：

### Functional verdict

允许：

```text
NOT_TESTED
EVIDENCE_OBSERVED
FUNCTIONAL_PASS
INCONCLUSIVE
FAIL
```

`FUNCTIONAL_PASS` 只表示当前 evidence 已证明该 Boundary 的核心功能成立，
项目可以合理继续向下一个 Boundary 推进；不表示 paper-grade convergence、
极端小 ringing、完整 margin sweep 或 formal robustness。

### Strict verdict

允许：

```text
STRICT_PASS
NOT_YET_QUALIFIED
```

缺少 strict 所需的 convergence、robustness 或重复证据时，使用
`NOT_YET_QUALIFIED`，不能反写成 functional `FAIL`。

## 4. Frozen local windows

时间列按 JoSIM CSV 的秒解释；以下窗口是半开区间 `[start,end)`，按实际采样
时间选择，不插值、不重采样：

| window | interval (ps) | purpose |
|---|---:|---|
| `INITIAL_BIAS` | `[0,50)` | 分离 t≈0 bias initialization activity |
| `PRE_READ` | `[65,70)` | READ 前 sensing/QB baseline |
| `READ_DRIVE` | `[70,81)` | 70 ps 起始、71–80 ps +100 µA、81 ps 回零的 drive context |
| `READ_RESPONSE_TAIL` | `[81,110)` | read pulse 后的局部 response 与 tail |
| `POST_SETTLING` | `[110,130)` | 主响应后的 settling / phase drift 检查 |
| `POST_REST` | `[130,200]` | 尾部是否有新 spontaneous activity |
| `READ_LOCAL` | `[70,110)` | READ-associated local response 的关联窗 |

窗口只用于 association 和 platform comparison；真实 voltage-active segment
若跨越边界，不机械截断。event onset/end 使用该 event 的实际 response boundary，
并在报告中说明其与窗口的关系。

## 5. Measurement rules

- `P(...)` 先作为 raw radians 保留；phase turns 始终为明确参考窗或 event
  端点的 `Δphi_rad/(2*pi)`。
- phase—area cross-check 必须使用同一 JJ、同一端点/方向、同一运行、同一
  实际时间列和同一 event boundary；面积为实际 CSV grid 上的梯形积分。
- 先报告 per-run raw rad、turns、voltage area、residual 和 signed polarity，
  再给 state/load comparison。
- `Vpeak`、`I>Ic`、导数活动、whole-window phase、旧 `fast_events` 都不是
  SFQ count。
- Functional settling 主要看主 voltage response 是否结束、post-event mean
  是否回到 baseline 附近、phase 是否进入新平台、剩余是否只是小幅 ringing；
  旧 strict `|V|<0.2 µV`/`0.25 ps` 只保留为 diagnostic，不是一票否决规则。
- local QB activity 不等于 loaded downstream reception；B3 必须逐级检查。

## 6. Reporting and claim ceiling

最终报告必须分开写：

```text
OBSERVED
INFERENCE
UNKNOWN
```

并提供：

```text
Boundary | Functional verdict | Strict verdict | Why
```

旧的 `CONTINUOUS_MULTI_TURN_RUNNING_STATE` 可以作为 detector diagnostic 保留，
但不能覆盖新版 Boundary verdict。

本规范不证明 canonical BVM compatibility、exactly-one SFQ、timestep convergence、
process margin、T1 logic、paper mechanism identity 或 unique QB operating mechanism。
