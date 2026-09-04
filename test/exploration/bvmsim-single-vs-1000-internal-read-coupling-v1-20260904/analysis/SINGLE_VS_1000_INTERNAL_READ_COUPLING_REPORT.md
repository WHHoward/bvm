# SINGLE-vs-1000 INTERNAL READ COUPLING ANALYSIS

## 1. Question

本分析只回答一个问题：在同一 JM2-connected historical BVMSim shared-sensing
fixture 中，把 BVM1 从 `0` 改成 `1` 后，仍为 commanded-0 的 BVM2/BVM3/BVM4
是否出现 READ-associated 内部/输出波形变化；并用 single-BVM `S0/S1` 作物理
参考。

## 2. Data reused / no new simulation

只读取已有的 `S0-J-JM2C`、`S1-J-JM2C`、4-BVM `1000` 和同拓扑 `0000` raw、deck
及其历史模型。没有执行 JoSIM 仿真，只记录 solver 版本信息；没有生成新的 raw，
没有覆盖旧报告或旧 metrics。
所有 raw 使用共享 `bvmtools.raw` 精确列名读取；本任务涉及的 raw 无重复列。

## 3. What was held fixed

`1000` 与 `0000` 共享 4-BVM topology、JM2-connected BVM variant、sensing line、
original QB、six-stage historical JTL、10 ohm termination、stimulus protocol、
timestep 和 prior READ0 history；主要 state-conditioned 改变是 BVM1 的 WRITE1
bit。需要保留的因果边界是：现有 protocol 的 READ0 在 WRITE1 之前，且没有
WRITE1 之后的 state-matched READ=0/no-read control；因此 `1000-0000` 是
state-conditioned 对照，不是把 READ 驱动、自由演化和 shared-load feedback
完全分离的纯 READ 因果对照。single reference 只用于参考，不被当作严格同历史
A/B 因果对照。canonical
`circuits/bvm/bvm_cell.cir` 未使用；本报告的 source authority 是 historical
BVMSim JM2-connected variant。

## 4. Analysis limitations

- single 与 4-BVM raw 的完整时间列各有历史输出间隔差异，故没有全窗硬拼；PRE_READ
  用 single `[65,70)` 对齐 4-BVM `[105,110)`，READ overlay 用 single `[70,130)`
  对齐 4-BVM `[110,170)`。这些比较均只使用 exact shifted stored timestamps，
  不插值。
- `1000-0000` 是 exact full-grid difference；centered difference-in-differences
  仅作为 READ-associated 的描述性辅助，中心为各 trace 自己的 PRE_READ1 median。
- `P(...)` 原始单位是 rad；本报告的 phase turns 只来自 continuous unwrap(rad)/(2*pi)。
  phase displacement、voltage area 和局部波形都不等于 SFQ count。
- 当前 raw 没有 `I(R_S)`、`I(L_S3)` 的直接 probe；这两个并联支路的分流不能唯一
  拆分，属于 `OBSERVABILITY_GAP`。`R_JM1` 由实际 topology 的 `V(B_JM1)/8 ohm`
  重建；`I(L_S1)`、`I(L_S2)` 和 `I(R_SL)` 可分别由已确认的串联关系用已有
  `I(B_JS1)`、`I(B_JS2)` 和 `I(L_PSL)/I(L_SL)` 得到，不能再列为同等级缺口。
- 本任务 provenance 绑定了本次实际读取的 raw、deck、模型和分析/绘图工具哈希；
  父实验的执行元数据仍以父目录的历史记录为准，本任务不重建或改写它们。

## 5. OBSERVED — single S0/S1 internal reference

- S0 PRE_READ 的循环电流均值（uA）：LM1=43.31，LM2=-43.31，LM3=-25.12，LPM=-43.94。
- S1 PRE_READ 的循环电流均值（uA）：LM1=-43.31，LM2=43.31，LM3=25.12，LPM=43.94。

这些数值是 raw window means，不是先验模式。完整的 JM1/JM2/JS1/JS2 P/V/I、各
loop branch 和同 JJ phase-area 数值在 `analysis/metrics.json` 的 `single` 中。
READ 的 phase-area 也只作为同一 JJ 的一致性描述，不作为事件计数。

## 6. OBSERVED — 1000 PRE_READ1 vs single references

`BVM1` 对 single `S1`，`BVM2–4` 对 single `S0`；下表给出 PRE_READ matching
window 的 phase level（turns）、以及 target-reference 的均值差。电流单位 uA，
SL 电压单位 mV。

| position | single ref | JM1 ref mean (turns) | 1000 mean (turns) | JM1 mean diff (turns) | LM1 mean diff (uA) | LSL mean diff (uA) | SL voltage mean diff (mV) |
|---|---|---:|---:|---:|---:|---:|---:|
| BVM1 | S1 | 0.9396 | 0.9399 | 0.0003306 | -0.08599 | 0.1998 | 0.04148 |
| BVM2 | S0 | -0.9396 | -0.9407 | -0.001148 | 0.4009 | -0.7791 | 0.01304 |
| BVM3 | S0 | -0.9396 | -0.9407 | -0.001117 | 0.3525 | -0.6766 | -0.005488 |
| BVM4 | S0 | -0.9396 | -0.9407 | -0.001091 | 0.3385 | -0.6609 | -0.01758 |

这一步只能支持“PRE_READ 内部水平与 isolated reference 的数值相似/不同”的
观察，不能写成 state completely identical。各 signal 的 mean difference、
relative/absolute difference、p2p 和 target retention 见 `pre_read_reference_comparison`。

## 7. OBSERVED — 1000 vs 0000 state-conditioned response

原始差分定义为 `1000 - 0000`。READ1 中 BVM2/BVM3/BVM4 的 `I(L_SL)` 差分相对其
PRE_READ1 差分分别为：BVM2 93.3 vs PRE 1.007 uA max_abs, BVM3 78.9 vs PRE 0.8575 uA max_abs, BVM4 54.88 vs PRE 0.5544 uA max_abs。
最大 victim 差分为 BVM2 的 93.3 uA。
“READ 中有变化”在本窗口的描述性判断为 `True`，但这里不设物理
阈值，需结合波形和 retention 一起审阅。

| position | Delta JM1 phase max_abs (turns) | Delta JM2 phase max_abs (turns) | Delta LSL max_abs (uA) | Delta SL max_abs (mV) | centered Delta LSL max_abs (uA) |
|---|---:|---:|---:|---:|---:|
| BVM1 | 1.901 | 0.2323 | 103.2 | 2.061 | 103.3 |
| BVM2 | 0.05779 | 0.2413 | 93.3 | 2.314 | 93.29 |
| BVM3 | 0.04535 | 0.08428 | 78.9 | 1.982 | 78.75 |
| BVM4 | 0.05013 | 0.08811 | 54.88 | 1.526 | 55.03 |

这些是 readout waveform changes。BVM2/BVM3/BVM4 的 JM1/JM2 storage markers 的
PRE_READ1→TAIL 数值保留在 `metrics.json` 的 `retention`；本轮不把 commanded-0
自动升级为 universally correct stored-0。

### Victim R-loop phase activity

`1000` 中 commanded-0 victim 的 JS1/JS2 在 READ1 出现了大幅 local phase-area
变化；下表同时保留同位置 `0000` control。它们是同一 JJ 的端点 phase delta 与
`V dt / Phi0` area 一致性描述，不是 SFQ event count，也不是完整 fluxoid retention。

| position | 1000 JS1 phase delta (turns) | 1000 JS1 Vdt (turns) | 1000 JS2 phase delta (turns) | 1000 JS2 Vdt (turns) | 0000 JS1 phase delta (turns) | 0000 JS2 phase delta (turns) |
|---|---:|---:|---:|---:|---:|---:|
| BVM2 | -5.986 | -5.986 | -5.986 | -5.985 | 0.01614 | 0.01905 |
| BVM3 | -3.014 | -3.014 | -3.016 | -3.016 | -0.01098 | -0.007397 |
| BVM4 | -2.01 | -2.01 | -2.012 | -2.012 | -0.02333 | -0.02027 |

## 8. OBSERVED — RJM1 current reconstruction + LM1 KCL

variant topology 明确为 `B_JM1: 2->7`、`R_JM1: 2->7`、`L_M1: 7->0`，因此固定
使用：`I(L_M1) - I(B_JM1) - V(B_JM1)/8 ohm = 0`。没有翻转符号来追求好结果。

| context | window | KCL residual max_abs (uA) | KCL residual RMS (uA) |
|---|---|---:|---:|
| single_S0 | READ | 9.5e-05 | 3.457e-05 |
| single_S1 | READ | 1e-05 | 4.577e-06 |
| 1000_BVM1 | READ1 | 1e-05 | 4.156e-06 |
| 1000_BVM2 | READ1 | 9.75e-05 | 1.571e-05 |
| 1000_BVM3 | READ1 | 8.462e-05 | 1.559e-05 |
| 1000_BVM4 | READ1 | 9.75e-05 | 1.727e-05 |
| 0000_BVM1 | READ1 | 9.5e-05 | 1.646e-05 |
| 0000_BVM2 | READ1 | 9.75e-05 | 1.469e-05 |
| 0000_BVM3 | READ1 | 8.625e-05 | 1.472e-05 |
| 0000_BVM4 | READ1 | 8.738e-05 | 1.575e-05 |

完整的重建电流与每个窗口 residual 在 `metrics.json` 的 `rjm1_kcl`。这是对
LM1 变化中 Josephson branch 与 8 ohm shunt 分配的约束；不是隐藏 branch 的直接
观测。

## 9. OBSERVED — timing / propagation

对 `1000-0000` delta，abs-peak time 不依赖 threshold。固定 1 uA/1 uV 只用于
描述性 activity localization；下面的“首个持续阈值样本”不是响应 onset。若
PRE_READ1 已经越过阈值，则标记为 `PRE_EXISTING_ACTIVITY_LEFT_CENSORED`，不能用作
传播延迟。READ1 结果如下，时间为 raw absolute ps。

| position | Delta V(SL) abs peak (ps) | Delta V(SL) window-first threshold (ps) | V threshold status | Delta I(LSL) abs peak (ps) | Delta I(LSL) window-first threshold (ps) | I threshold status |
|---|---:|---:|---|---:|---:|---|
| BVM1 | 115.7 | 110 | PRE_EXISTING_ACTIVITY_LEFT_CENSORED | 118 | 111 | PRE_EXISTING_ACTIVITY_LEFT_CENSORED |
| BVM2 | 120 | 110 | PRE_EXISTING_ACTIVITY_LEFT_CENSORED | 124.4 | 111.3 | PRE_EXISTING_ACTIVITY_LEFT_CENSORED |
| BVM3 | 120.9 | 110 | PRE_EXISTING_ACTIVITY_LEFT_CENSORED | 121.7 | 111.5 | THRESHOLD_FIRST_OBSERVED_IN_OR_AFTER_WINDOW |
| BVM4 | 120.9 | 110.1 | PRE_EXISTING_ACTIVITY_LEFT_CENSORED | 118.9 | 112.2 | THRESHOLD_FIRST_OBSERVED_IN_OR_AFTER_WINDOW |

`BVM1` 与 BVM2–4 的 pairwise correlation（正 lag 表示右侧/下游位置较晚）如下：

| signal | pair | best lag (ps) | zero-lag r | best-lag r |
|---|---|---:|---:|---:|
| V(SL) | BVM1_vs_BVM2 | -0.1 | 0.5904 | 0.5921 |
| V(SL) | BVM1_vs_BVM3 | -0.2 | 0.7053 | 0.7219 |
| V(SL) | BVM1_vs_BVM4 | 2.9 | 0.3002 | 0.6189 |
| I(L_SL) | BVM1_vs_BVM2 | 4.4 | 0.3756 | 0.7117 |
| I(L_SL) | BVM1_vs_BVM3 | 3 | 0.07284 | 0.604 |
| I(L_SL) | BVM1_vs_BVM4 | 5.1 | -0.5936 | 0.4276 |

若多个位置接近同步或 lag 方向不稳定，应优先讨论 common READ drive、global
boundary perturbation 和 shared-load feedback；这些 timing/correlation 结果
不能单独证明单向 traveling disturbance 或唯一传播路径。完整的 JS1/JS2、LM3、
LPM timing 也在 `metrics.json`。

## 10. INFERENCE

在当前历史 fixture 和当前观测窗口内，`1000-0000` 若干 commanded-0 BVM 的
READ-associated `LSL/SL/internal` delta 明显高于其 PRE_READ1 delta，且其 JM1/JM2
retention marker 没有被同样地解释为 storage command 改变，则证据与如下解释相容：

`BVM1 stored-state / READ dynamics -> BVM1 LSL branch -> shared sensing-line
boundary -> other BVM boundary conditions -> their R-loop/internal redistribution`。

这应称为 shared-sensing-network readout cross-coupling / back-action / cross-loading
的 bounded inference，而不是“BVM1 电流直接流进 BVM2”。single-vs-1000 只提供
reference context；`1000-0000` 只能提供 state-conditioned association/localization，
不能单独分离 READ 驱动、自由演化与 shared-load feedback，也不能确定唯一 causal
path。

## 11. UNKNOWN

- `R_S || L_S3` 两支电流没有直接 probe，当前不能唯一决定 resistive 与 inductive
  partition；状态：`OBSERVABILITY_GAP`。
- 未证明 canonical BVM、单 BVM 与 4-BVM 完全可互换、QB 无关、论文机制身份、纯
  电阻/纯电感作用、单向传播或任何普适器件结论。
- 未将任何 phase turn 解释为 SFQ count；未做新事件实验、timestep convergence、
  margin、sweep 或参数优化。

## 12. Minimal next option

`PROPOSED_NOT_AUTHORIZED`：若用户审阅后仍需拆分 R-loop branch，只做 probe-only
rerun，增加 `I(R_S|XBVM1..4)`、`I(L_S3|XBVM1..4)`；本轮没有运行该建议。

## 13. Human gate

`AWAITING_USER_REVIEW`

- `user_reviewed: false`
- `next_step_authorized: false`
- `automatic_next_experiment: false`

本轮到此停止。
