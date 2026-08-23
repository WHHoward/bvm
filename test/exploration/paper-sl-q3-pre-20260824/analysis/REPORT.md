# PAPER-SL-Q3-PRE 分析报告

## 范围与结论等级

本 checkpoint 只读取既有 Q0 68.4 µA positive-control、PAPER-SL-Q1 35 µA logical1 READ 和 PAPER-SL-Q2 40 µA logical1 READ raw。没有运行 JoSIM、没有重采样、没有改变 physical circuit。Q0 的周期 raw 使用包含其全局最大 BJs segment 的 210 ps pulse 做 aligned comparison；phase/area 比值仍使用各 JJ 在注册 activity windows 内的 global largest segment。

最终决策：**B. BJs→BJL1 更像 waveform/routing/timing-limited，而不是可由当前证据主要归因于 BJL1 threshold。** 这是受限于三个既有 fixture 的 mechanism inference，不是 topology 普遍结论。

## 实际 QB topology 与 KCL

```text
IN ── Lin ── node1 ── BJs ── node2
                           ├─ BJL1 || RJ1 ── GND
                           └─ L1 ── node3 ── L2 ── node4
                                      ▲          ├─ BJL2 || RJ2 ── GND
                                      │          └─ L0 ── OUT
                                    RB / IBIAS
```

按 netlist 元件方向直接审计：

- node2：`I(BJs) = I(L1) + I(BJL1) + I(RJ1)`；
- node3：`I(L1) + I(RB) = I(L2)`；
- node4：`I(L2) = I(L0) + I(BJL2) + I(RJ2)`。

三组 raw 的 node2/node3/node4 KCL residual 均为微安级以下的数值误差，见下表。

## Aligned continuous phase / same-JJ voltage-area

相对时间零点是该 case 的 dominant BJs segment 起点；Q0 的 absolute time 仍保留实际 210 ps pulse 时间。`ΔP` 是同一 JJ、同一 segment 的 unwrapped phase endpoint difference；area 使用该 JJ 直接 `V(B...)` 和 CSV 实际时间。

| case | JJ | absolute segment (ps) | relative segment (ps) | P start → P end (rad) | ΔP (rad) | Δturns | area (Φ0) | area residual (turn) | phase/area consistent |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Q0_68p4u | BJs | 210.5–230.4 | 0–19.9 | 389.271 → 492.462 | 103.191 | 16.4233 | 16.426 | 0.00267472 | yes |
| Q0_68p4u | BJL1 | 210–216.5 | -0.5–6 | 25.5662 → 33.2664 | 7.70021 | 1.22553 | 1.22678 | 0.00125086 | yes |
| Q0_68p4u | BJL2 | 210–217.1 | -0.5–6.6 | 25.5097 → 32.3962 | 6.88646 | 1.09601 | 1.09652 | 0.000501262 | yes |
| PAPER_SL_Q1_35u | BJs | 102.55–120.263 | 0–17.7125 | 1.77662 → 90.32 | 88.5434 | 14.0921 | 14.0921 | 2.26823e-05 | yes |
| PAPER_SL_Q1_35u | BJL1 | 102.638–109.125 | 0.0875–6.575 | 1.80782 → 7.0219 | 5.21408 | 0.829846 | 0.82988 | 3.37791e-05 | yes |
| PAPER_SL_Q1_35u | BJL2 | 103.038–109.65 | 0.4875–7.1 | 1.12199 → 6.7299 | 5.60791 | 0.892527 | 0.892537 | 9.77522e-06 | yes |
| PAPER_SL_Q2_40u | BJs | 102.55–120.263 | 0–17.7125 | 1.77662 → 90.32 | 88.5434 | 14.0921 | 14.0921 | 2.26823e-05 | yes |
| PAPER_SL_Q2_40u | BJL1 | 102.525–106.875 | -0.025–4.325 | 2.23797 → 7.36137 | 5.1234 | 0.815414 | 0.815445 | 3.12086e-05 | yes |
| PAPER_SL_Q2_40u | BJL2 | 100.262–107.425 | -2.2875–4.875 | 0.975354 → 6.90871 | 5.93336 | 0.944323 | 0.944333 | 1.04105e-05 | yes |

Q0 的 paired window 是 `[210,235)` ps；其中 BJs global largest 为 `[210.5,230.4]` ps，BJL1 paired segment 为 `[210.0,216.5]` ps。Q0 BJL1 的 global largest amplitude 出现在 `[160.0,166.5]` ps，但同一脉冲形状的 210 ps paired segment 用于时序/KCL 对齐，避免把不同 pulse 拼接成一个因果轨迹。

## Requested transfer ratios

这些比值采用每个 case 各 JJ 的 global largest monotonic segment；不是 total phase range，也不是 event count。

| case | BJs largest (turn) | BJL1 largest (turn) | BJL2 largest (turn) | BJL1/BJs | BJL2/BJL1 | BJL2/BJs |
|---|---:|---:|---:|---:|---:|---:|
| Q0_68p4u | 16.4233 | 1.22553 | 1.09601 | 0.0746213 | 0.89432 | 0.0667353 |
| PAPER_SL_Q1_35u | 14.0921 | 0.829846 | 0.892527 | 0.0588873 | 1.07553 | 0.0633352 |
| PAPER_SL_Q2_40u | 14.0921 | 0.815414 | 0.944323 | 0.0578631 | 1.15809 | 0.0670107 |

按请求参考值独立复算：Q0 = `16.423294 / 1.225528 / 1.096014`；Q1-35 = `14.092115 / 0.829846 / 0.892527`；Q2-40 = `14.092115 / 0.815414 / 0.944323`。

## Timing overlap / delay

| case | BJs dominant interval (ps) | paired BJL1 interval (ps) | BJL1 start delay from BJs start (ps) | overlap (ps) | BJs duration | BJL1 duration |
|---|---:|---:|---:|---:|---:|---:|
| Q0_68p4u | 210.5–230.4 | 210–216.5 | -0.5 | 6 | 19.9 | 6.5 |
| PAPER_SL_Q1_35u | 102.55–120.263 | 102.638–109.125 | 0.0875 | 6.4875 | 17.7125 | 6.4875 |
| PAPER_SL_Q2_40u | 102.55–120.263 | 102.525–106.875 | -0.025 | 4.325 | 17.7125 | 4.35 |

Q0/Q1/Q2 的 BJL1 segment 都在 BJs 主活动开始附近出现，并非明显的长延迟输出。Q2 的 global BJL2 segment 可早于 paired BJL1 segment，这不改变本节只审计 BJs→BJL1 的结论。

## BJL1 operating point during dominant BJs segment

单位为 µA；`RB` 是 bias branch。此表展示 BJs 主 segment 内的瞬时 branch operating range/mean，而不是用 `I/Ic` 宣称 event。

| case | interval | branch | min | max | mean | RMS | signed current area (µA·ps) |
|---|---|---|---:|---:|---:|---:|---:|
| Q0_68p4u | bjs_interval_currents | I(BJS|XBQ) | 0 | 68.4 | 20.178 | 36.3229 | 401.85 |
| Q0_68p4u | bjs_interval_currents | I(BJL1|XBQ) | -36.3424 | 42.8597 | 14.4689 | 20.1128 | 286.775 |
| Q0_68p4u | bjs_interval_currents | I(RJ1|XBQ) | -18.2812 | 20.5852 | 3.08334 | 8.01279 | 61.3253 |
| Q0_68p4u | bjs_interval_currents | I(L1|XBQ) | -32.0698 | 85.2719 | 2.62575 | 30.0571 | 53.7502 |
| Q0_68p4u | bjs_interval_currents | I(RB|XBQ) | 35 | 35 | 35 | 35 | 696.5 |
| Q0_68p4u | bjs_interval_currents | I(L2|XBQ) | 2.93024 | 120.272 | 37.6257 | 48.0857 | 750.25 |
| PAPER_SL_Q1_35u | bjs_interval_currents | I(BJS|XBQ) | -20.0366 | 79.0668 | 12.9786 | 27.3624 | 229.662 |
| PAPER_SL_Q1_35u | bjs_interval_currents | I(BJL1|XBQ) | -51.3624 | 51.4603 | 9.16657 | 20.8849 | 162.118 |
| PAPER_SL_Q1_35u | bjs_interval_currents | I(RJ1|XBQ) | -11.71 | 16.7428 | 2.86757 | 7.41996 | 50.8297 |
| PAPER_SL_Q1_35u | bjs_interval_currents | I(L1|XBQ) | -32.2057 | 54.7499 | 0.944433 | 24.6823 | 16.7145 |
| PAPER_SL_Q1_35u | bjs_interval_currents | I(RB|XBQ) | 35 | 35 | 35 | 35 | 619.938 |
| PAPER_SL_Q1_35u | bjs_interval_currents | I(L2|XBQ) | 2.79429 | 89.7499 | 35.9444 | 43.5927 | 636.652 |
| PAPER_SL_Q2_40u | bjs_interval_currents | I(BJS|XBQ) | -20.0366 | 79.0668 | 12.9786 | 27.3624 | 229.662 |
| PAPER_SL_Q2_40u | bjs_interval_currents | I(BJL1|XBQ) | -57.8066 | 44.0258 | 13.251 | 21.4141 | 234.547 |
| PAPER_SL_Q2_40u | bjs_interval_currents | I(RJ1|XBQ) | -11.6207 | 23.0976 | 2.66669 | 8.2344 | 47.2567 |
| PAPER_SL_Q2_40u | bjs_interval_currents | I(L1|XBQ) | -34.2375 | 78.7242 | -2.93912 | 27.8071 | -52.1419 |
| PAPER_SL_Q2_40u | bjs_interval_currents | I(RB|XBQ) | 40 | 40 | 40 | 40 | 708.5 |
| PAPER_SL_Q2_40u | bjs_interval_currents | I(L2|XBQ) | 5.76247 | 118.724 | 37.0609 | 46.2396 | 656.358 |

在 paired largest BJL1 segment 内，直接支路的 signed current-area（用于描述波形极性，不是 event 判据）如下：

| case | BJL1 area | RJ1 area | L1 area | BJs area | local `(BJL1+RJ1)/BJs` | L1/BJs |
|---|---:|---:|---:|---:|---:|---:|
| Q0_68p4u | 75.7359 | 76.8719 | 249.242 | 401.85 | 0.379763 | 0.620237 |
| PAPER_SL_Q1_35u | -7.25141 | 52.0016 | 183.706 | 228.456 | 0.195881 | 0.804119 |
| PAPER_SL_Q2_40u | -2.88744 | 51.0971 | 172.268 | 220.477 | 0.21866 | 0.78134 |

这个 split 是本轮最有信息量的内部 routing observable：Q0 的 signed BJL1 direct branch area 为正，而 Q1/Q2 略为负；Q1/Q2 的输入电流更多被 `L1` 及 `RJ1`/并联网络重新分配。

## KCL closure

Residual 是在 dominant BJs segment 上计算的 µA 数值残差。

| case | node2 max abs / RMS (µA) | node3 max abs / RMS (µA) | node4 max abs / RMS (µA) |
|---|---:|---:|---:|
| Q0_68p4u | 1e-05 / 4.23417e-06 | 5e-05 / 7.84411e-06 | 5e-05 / 8.74e-06 |
| PAPER_SL_Q1_35u | 1e-05 / 3.64942e-06 | 5e-06 / 1.75826e-06 | 1.4e-05 / 4.48074e-06 |
| PAPER_SL_Q2_40u | 1e-05 / 3.82119e-06 | 5e-05 / 7.11273e-06 | 5.5e-05 / 8.37259e-06 |

## Observed

- Q0 的 BJs global largest segment 为约 `16.4233 turn`，BJL1 为 `1.22553 turn`；Q1/Q2 的 BJs 都是约 `14.0921 turn`，而 BJL1 分别为 `0.829846` 和 `0.815414 turn`。三组 largest segment 的 same-JJ voltage-area 与 phase endpoint 均一致到报告精度。
- Q0 的 BJL1 paired segment 与 BJs 主 segment 重叠约 `6.0 ps`；Q1 为约 `6.49 ps`，Q2 为约 `4.33 ps`。没有看到需要数十 ps 的明显 interstage delay 才能解释差异。
- 在 BJL1 paired segment 上，Q0 的 `I(BJL1)` signed area 约 `+75.74 µA·ps`；Q1/Q2 分别约 `−7.25/−2.89 µA·ps`。Q1 的 BJL1 current peak 约 `±51 µA`、Q2 约 `−57.8/+44.0 µA`，并不低于 Q0 的 `−36.3/+42.9 µA`。
- Q0/Q1/Q2 的 node2/node3/node4 KCL residual 均保持在约 `10⁻5–10⁻4 µA` 量级，说明分流差异不是由列方向/KCL 不闭合造成的。

## Derived

- 相对于 Q0，Q1 的 BJL1/BJs phase-transfer ratio 低约 21%，Q2 低约 22%；Q2 的 BJL2/BJL1 ratio 反而升高到约 `1.158`，因此当前主要差异出现在 BJs→BJL1，而不是 BJL1→BJL2 的单调 threshold 缺口。
- 以 paired BJL1 segment 的 signed current-area 定义 node2 local-branch fraction `(BJL1+RJ1)/BJs`，Q0/Q1/Q2 约为 `0.3798/0.1959/0.2187`；其互补的 L1 fraction 约为 `0.6202/0.8041/0.7813`。这是对实际拓扑 KCL 的派生 routing 指标，不是新的 acceptance threshold。
- Q0 的 BJL1 same-segment phase/area 已满足局部完整转变的现有 exploratory diagnostic；Q1/Q2 的 `0.8–0.82 turn` 仅是 sub-turn activity，不能称 event。

## Inference

判定选择 **B：BJs→BJL1 主要表现为 waveform/routing/timing limitation**。依据是：Q1/Q2 并非缺少 BJL1 branch current peak；相反，BJL1 current 波形的峰值可与 Q0 相当或更大，但其 signed transfer、local `(BJL1+RJ1)` 分流份额和 BJL1 phase segment 明显不同。固定 `BJL1 AREA/Ic` 前，最有信息量的单一内部 routing variable 是 node2 的 local-branch split waveform，建议用 `F_local(t) = [I(BJL1)+I(RJ1)]` 相对于 `I(BJs)` 的 actual-time integrated fraction 表征；其互补量是 `I(L1)` transfer。

这不排除 BJs 幅度差异对阈值有贡献：Q0 BJs 最大段比 Q1/Q2 大约 16.5%。但仅凭该幅度差、`I>Ic` 或 voltage peak 无法解释 Q1/Q2 在 BJL1 branch 上更大的峰值却没有完整 segment，因此不应先把原因归结为 BJL1 Ic。

## Unknown

- 三组 raw 的 timestep 不同（Q0 `0.1 ps`，Q1/Q2 `0.0125 ps`）；本轮未做新的 convergence run，因此 sub-ps onset/delay 只能按各自实际采样报告，不能当作 resolution-independent timing constant。
- 现有 raw 没有一个独立的 BJL1 threshold-only matched ratio experiment；因此 B 的 mechanism inference 不能证明 threshold 完全无关。
- 未连接 physical BVM/JSL/QB、未改变任何 junction ratio、未接 JTL；本报告不回答 physical compatibility 或 downstream delivery。

## Decision output

**B. BJs→BJL1 looks primarily waveform/routing/timing-limited.** 在改变 BJL1 threshold 之前，最高信息量的单一内部变量是 node2 的 `I(L1)` / local `(BJL1+RJ1)` KCL split，优先冻结并比较其 actual-time waveform/integrated fraction。按照本 checkpoint 要求，到此停止；不降低 BJL2 AREA、不连接 physical BVM→12JSL→QB、不接 JTL。

## Provenance

完整 raw/netlist/model provenance 与 SHA-256 记录在 `reference/source-provenance.yaml`；本目录不复制或修改既有 raw。
