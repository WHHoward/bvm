# BVM→QB Lin removal matched-pair Quick 报告

## 状态：`QUICK_NO_EFFECT` / `INCONCLUSIVE` / `AWAITING_USER_REVIEW` / `STOP`

本报告只描述当前 13 ps、12×320、logical1/read、scaled-QB 模型下的两次候选仿真。
它不升级为硬件测量、正式接口 Gate 或普遍 Lin 结论。

## 1. 实验边界

- P0/I0/G 是父矩阵已有 raw；本次新增且仅新增 P1 physical 与 I1 ideal replay。
- P1：physical BVM → 12×320 JSL → QB，删除 `Lin=0.8 pH`。
- I1：使用与 I0 完全相同的 grounded-source PWL，QB 同样删除 Lin。
- 其他 BVM/JSL/QB 参数、IBIAS=35 µA、R_LOAD=10 Ω、0.0125 ps timestep 和 170 ps stop 固定。
- 比较窗口：W2 `[80,90)` ps、W3 `[95,110)` ps、W4 `[110,130)` ps；所有比较 exact-grid、无插值。

## 2. 预注册 primary matched gap

`D0(signal)=RMS(P0,I0)`，`D1(signal)=RMS(P1,I1)`，均在 W3 计算；gap reduction = `1-D1/D0`。

| signal | D0 | D1 | gap reduction | unit |
|---|---:|---:|---:|---|
| `P(BJS|XBQ)` | 2.2452 | 2.20492 | 0.0179419 | turns |
| `I(L1|XBQ)` | 28.3754 | 29.0629 | -0.0242281 | uA |
| `P(BJL1|XBQ)` | 0.519117 | 0.523841 | -0.00909924 | turns |
| `I(L2|XBQ)` | 28.3754 | 29.0629 | -0.0242281 | uA |
| `P(BJL2|XBQ)` | 0.43001 | 0.433204 | -0.00742804 | turns |

解释：5 个 primary 信号的 reduction 为弱变化，均未达到预注册的 20% directional threshold。
这支持当前 Quick 的 `QUICK_NO_EFFECT` 标签，但只限于本模型、单一 Lin intervention 和固定窗口。

## 3. source-side 与 pre-READ

| signal | G↔P0 W3 RMS | G↔P1 W3 RMS | reduction | unit |
|---|---:|---:|---:|---|
| `I(B_LD1)` | 28.4735 | 28.6732 | -0.00701641 | uA |
| `I(B_LD12)` | 28.4735 | 28.6732 | -0.00701641 | uA |
| `I(L_PSL|XBVM1)` | 28.4735 | 28.6732 | -0.00701641 | uA |
| `V(SL1)` | 0.895583 | 0.891404 | 0.00466626 | mV |

预注册 pre-READ safety：BVM phase 最大差 2.67699e-05 turns （limit 0.01），source current 最大差 0.0426984 µA（limit 5），结果为 `True`。

## 4. BJL2 严格本地诊断

| case | classification | largest segment | complete segments | second complete? | post bounded? |
|---|---|---|---:|---|---|
| P0 | `SUBTHRESHOLD` | Δphase -0.122128 turns / area -0.122131 Φ0 / residual 3.23871e-06 turns | 0 | 否 | 是 |
| P1 | `SUBTHRESHOLD` | Δphase -0.121121 turns / area -0.121126 Φ0 / residual 4.62602e-06 turns | 0 | 否 | 是 |
| I0 | `CLEAN_ONE_SFQ_CANDIDATE` | Δphase 1.01603 turns / area 1.01604 Φ0 / residual -7.91154e-06 turns | 1 | 否 | 是 |
| I1 | `CLEAN_ONE_SFQ_CANDIDATE` | Δphase 1.01603 turns / area 1.01604 Φ0 / residual -7.91154e-06 turns | 1 | 否 | 是 |

I0 strict anchor：phase `1.0160289228944646` turns、area `1.0160368344325381 Φ0`、segment `[103.0375,110.175] ps`、`CLEAN_ONE_SFQ_CANDIDATE`，回归检查 PASS。
严格表格仅表示同一 BJL2 的 raw `P()` 与直接 `V()` 的局部 compatibility arithmetic；不表示 SFQ 数量、下游 QB/JTL 接收或系统逻辑成功。

## 5. 证据分层

### Observed

- 两条新增 case 返回码为 0，CSV 完整，13599 samples，时间范围 0–169.9875 ps；stderr 为空。
- I0/I1 的 frozen PWL block 和 `I(I_REPLAY)` 序列 exact-match。
- P0/P1 都是 BJL2 subthreshold；I0/I1 都保留同一 local compatibility classification。

### Derived

- 相位由 raw JoSIM radians 连续 unwrap 后除以 `2π` 报为 turns；电流/电压保留明确单位。
- D0/D1 和 source distortion 都是在同一 full time grid 上的固定窗口 RMS；没有插值。
- 图只保留 7 组关键轨迹，由 classic `josim-plot2.py` 的 `sep_comb/dark/-j 2pi` 生成。

### Inference

- 在当前条件下，删除 QB Lin 没有产生预注册意义上的 physical-to-ideal QB trajectory gap 收窄；不能据此断言 Lin 对其他 READ 宽度、负载、偏置或硬件实现都无关。

### Unknown / not tested

- 没有 logical0/no-read control、Lin sweep、其他 BJs/bias/L、timestep ladder、JTL/T1、magnetic coupling 或硬件测量；也没有建立系统级 Gate。
- 当前证据不能区分所有可能的接口失配机制，也不提供“Lin 越小越好”的优化结论。

## 6. 交付物

- `analysis/metrics.json`：固定窗口、匹配距离、严格本地诊断和 outcome 机器可读结果。
- `analysis/provenance.json`：raw/model/deck/solver/runner/plot 来源与 hash。
- `plots/RESULT_OVERVIEW.html`：唯一 compact classic key-data overview。
- `analysis/human-gate.yaml`：`AWAITING_USER_REVIEW`，不自动推进。
