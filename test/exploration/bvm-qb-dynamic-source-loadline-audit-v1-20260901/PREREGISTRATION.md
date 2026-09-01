# BVM_QB_DYNAMIC_SOURCE_LOADLINE_AUDIT_V1

## 记录与范围

- 记录时间：`2026-09-01T15:33:35+08:00`
- 分析前 HEAD：`b761ba948d0cf64affdc0b9fb623fab05197cf21`
- 分析前工作树：clean
- study mode：`EXPLORATORY / PHYSICS-FIRST MECHANISM AUDIT`
- 输入：`test/exploration/bvm-load-qb-matrix-v1-20260901/raw/`
- strict 参考：`test/exploration/bvm-load-qb-strict-event-reclassification-v1-20260901/`
- 输出：本目录；不改写输入 raw、旧报告、旧 strict 分类或矩阵网表

本任务只对已经存在的 source、ideal replay、physical cascade raw CSV 做后处理。
不运行 JoSIM，不扫参，不改 QB/BVM/JSL、读宽、拓扑、JTL、T1 或 magnetic
coupling。结果是当前模型、单一已运行步长和已登记激励下的 bounded simulation
mechanism evidence，不是硬件测量、鲁棒裕度或系统 Gate。

## 主要科学问题

解释匹配三角形：

- A：9 ps / 12x320 / ideal replay，BJL2 `0.892527234 turn`，`SUBTHRESHOLD`
- B：13 ps / 12x320 / ideal replay，BJL2 `1.016028923 turn`，
  `CLEAN_ONE_SFQ_CANDIDATE`
- C：13 ps / 12x320 / physical，BJL2 `-0.122127800 turn`，`SUBTHRESHOLD`

辅助比较：

- D：13 ps / 8x500 / ideal replay，BJL2 `0.973287067 turn`，`SUBTHRESHOLD`
- E：13 ps / 8x500 / physical，BJL2 `-0.124996234 turn`，`SUBTHRESHOLD`

这些 strict 数值来自先前已完成的 strict reclassification；本任务不重新解释、
不改写其事件分类。`turn` 始终表示同一 BJL2 连续相位轨迹的
`delta_phi_rad/(2*pi)`；它不是论文对 BJL2 的定义，也不是闭环 fluxoid 计数。

## 预冻结 competing hypotheses

在分析新诊断前冻结以下假说，不预先决定正确者：

| ID | 假说 | 可证伪的观测预期 |
|---|---|---|
| H1 | READ extension 主要增加有用 source-current duration/area，使 QB 完成 BJL2 transition | A/B 在 105 ps 前一致；B 相对 A 的主要 source 差异落在 READ 延长区，且 source area/duration 与 BJL2 由 `<1` 到 `>=1` 的变化同向；若形状/内部支路改变同样主导，则 H1 仅部分相容 |
| H2 | READ extension 不只是 duration，而改变 source waveform shape、trailing lobe 或 timing，使 node2 dynamics 进入另一 nonlinear branch | A/B 出现显著 trailing-lobe、极值时间、centroid、差分面积分解或内部轨迹形状变化，且不能由简单持续时间解释 |
| H3 | 关键 discriminator 是 BJs/BJL1/node2 的 current partition，而不是 source peak 单独决定 | BJL1/node2 current partition 或 phase trajectory 在 BJL2 divergence 之前出现可重复差异，且 source peak 单指标不能解释 strict 分类 |
| H4 | physical connection 显著改变 BVM/JSL source load-line，使 QB 没有得到 grounded ideal replay 的 trajectory | grounded source、physical JSL、physical QB `I(LIN)` 之间存在可测 back-action；physical QB 内部轨迹偏离 B，而不是仅输出显示不同 |
| H5 | physical failure 主要是 grounded source waveform 的 scalar attenuation | 固定窗口内存在单一 `k`，使 `I_physical≈k I_grounded`，且残差、相关性、peak timing 和 polarity 均在预注册 fit band 内 |
| H6 | physical trajectory 不能由 scalar attenuation 表示，需要 waveform/ timing/ polarity/ internal routing reshaping | H5 fit band 被拒绝，并同时观察到非比例形状、时序或内部 current partition 差异；结论只到 bounded mechanism family |
| H7 | 12x320 与 8x500 的差异主要来自 source/load-line，而非 BJL2 内部的 fundamental change | 13 ps 两个 ideal replay 的 source/load-line observables 与 BJL2 之前的内部轨迹差异可解释 `1.016` vs `0.973`；若没有隔离性证据，H7 保持 unresolved |

Hypothesis status 只允许 `SUPPORTED`、`DISFAVORED`、`UNRESOLVED`。统计/相关
结果不能单独升级为 unique causation。

## 冻结数据与时间定义

### 共用条件

- CSV `time` 原单位为秒；所有显示时间转为 ps。
- 不重采样、不插值、不假定固定 dt；积分使用 raw 实际时间列梯形法。
- common activity window：`[94 ps, 130 ps)`，与 strict reclassification 一致。
- A/B causal pre-divergence check：`t <= 105 ps`，包含 105 ps 已有样本；不得把
  105 ps 前的差异解释为 READ extension 的因果结果。
- A/B post-knot decomposition：`[94,105]`、`[105,106]`、`[106,109]`、
  `[109,110]`、`[110,130)` ps；端点使用实际存在的 CSV 样本，积分区间重合的
  单点不产生面积贡献。
- B/C back-action 与 scalar fit：固定使用 13 ps / 12x320 / logical1_read 的
  `[94,130)` activity window。
- 所有 raw case 必须保留 path、SHA-256、sidecar SHA（若存在）、列名、样本数、
  时间单调性和打印时间 gap。

### 精确 raw 列映射

source fixture 使用：

- `I(B_LD1)`：首个 JSL branch reference/source current；
- `I(B_LD12)`（12x320）或 `I(B_LD8)`（8x500）：末端 JSL branch；
- `I(L_SL|XBVM1)`、`V(SL1)`；若存在则 `V(N6|XBVM1)`、`I(L_PSL|XBVM1)`。

QB fixture 使用原始精确列名：

- input：`I(I_REPLAY)`、`V(IN)`、`I(LIN|XBQ)`；
- BJs：`P(BJS|XBQ)`、`V(BJS|XBQ)`、`I(BJS|XBQ)`；
- node2/BJL1：`P(BJL1|XBQ)`、`V(BJL1|XBQ)`、`I(BJL1|XBQ)`、
  `I(RJ1|XBQ)`、`I(L1|XBQ)`；
- node3：`I(RB|XBQ)`、`I(L2|XBQ)`；
- BJL2/output：`P(BJL2|XBQ)`、`V(BJL2|XBQ)`、`I(BJL2|XBQ)`、
  `I(RJ2|XBQ)`、`I(L0|XBQ)`、`V(OUT)`、`I(R_LOAD)`。

若一个 required column 缺失、重复列映射不明确或端点方向不能确认，该 case
记为 artifact `INVALID`，不以别的信号替代。

所有 `P(...)` 比较先对整条 raw 轨迹做 continuous `unwrap`，再以 common
pre-divergence 首样本对齐；phase 比较的单位记录为 rad 或 turns，不能直接把
raw phase 样本当事件数。

## 冻结诊断

### 1. A→B source waveform

对 9/13 ps 的 source fixture 分别按 12x320 primary、8x500 secondary 比较
`I(B_LD1)`、terminal `I(B_LDN)`、`I(L_SL|XBVM1)`、`V(SL1)`，存在时附加
`V(N6|XBVM1)`、`I(L_PSL|XBVM1)`。

对每个 signal 在 fixed activity window 记录：

- positive peak/minimum 及其 first-sample time；
- signed area `∫I dt`；positive area `∫max(I,0)dt`；negative area
  `∫min(I,0)dt`，单位为 `A*s`，报告中可另显示 `uA*ps`；
- signed centroid/first moment：`t_c = ∫t_ps I(t)dt / ∫I(t)dt`。若
  `|∫I dt| <= 1e-20 A*s`，centroid 记为 undefined，不强行解释；同时保留
  positive/negative-lobe centroid（各自以 `∫t_ps*max(±I,0)dt / ∫max(±I,0)dt`
  定义）与极值时间；任何小分母均 mask；
- `I_13ps-I_9ps` difference waveform、按冻结 sub-window 的 signed/positive/
  negative difference-area decomposition、最大绝对差及其 first-sample time。

这些 area 只是 source-waveform diagnostic，不命名为 SFQ quantity。

### 2. A→B QB internal trajectory

只比较 ideal replay A/B，报告 input、BJs、node2/BJL1、node3、BJL2/output 的
固定窗口峰值、signed area（只对电流）、轨迹差和 divergence time。BJL2 strict
event 只复用已有 strict summary/details；不创造新的 event metric，不使用 VOUT
peak/p2p、`I>Ic`、whole-window displacement 或 `fast_events` 计数。

### 3. A→B causal timeline

每个 observable family 的 first divergence 定义为：在 `t>105 ps`，配对 raw
时间样本上连续至少两个采样点满足

`abs(x_13-x_9) > max(10*baseline_p99_9, 1e-12*scale, 100*eps*scale)`，

其中 `baseline_p99_9` 是同一 signal 在 `t<=105 ps` 的绝对差 99.9 percentile，
`scale=max(1, max(abs(x_9),abs(x_13)))`，`eps` 是 IEEE double machine epsilon。
该规则、系数和连续样本要求在看分类前冻结；不手工移动阈值。若同一 sampling
bin 首次超限，报告为 `TIE`；不宣称超出实际 timestep 的因果分辨率。

family 顺序固定为 source waveform → QB IN/Lin → BJs → node2/BJL1 → node3 →
BJL2 → OUT。family 内任一注册 signal 首先满足条件即为该 family onset，并保存
signal-level 证据。

### 4. B→C source-load back-action

固定比较 13 ps / 12x320 / logical1_read：

- grounded source `I_source_grounded = I(B_LD1)`；
- physical `I_physical_JSL = I(B_LD1)`；
- physical `I(L_SL|XBVM1)`；
- ideal replay `I(I_REPLAY)` 作为 source-to-replay identity control。

定义 `DeltaI(t)=I_source_grounded(t)-I_physical_JSL(t)`，在 `[94,130)` 报告
max abs、RMS、signed integral、positive/negative integral 和最大差 first-sample
time；不把差值直接称为阻抗或唯一原因。

在解释 READ 期间的 back-action 前，先比较 physical 与 ideal replay 的 QB
pre-window `[80,94)` phase/current 状态以及 BVM source pre-state；若 pre-state
已经超过同一数值 floor，结论只能写成“load interaction 已改变初始轨迹”，不能
归因于 READ 期间某一个 lobe。对 QB netlist 的 node1/node2/node3/node4 使用
声明方向的带符号 KCL residual 做 closure guard；串联的 physical JSL terminal
current 与 `I(LIN|XBQ)` 不当作两份独立证据。

KCL 数值 bound 沿用本仓库既有 QB raw 审计的 CSV 十进制输出精度约定，并在本轮
执行前固定为：

```text
abs_tol = 1.0e-12 A
rel_tol = 1.0e-6
bound(t) = max(abs_tol, rel_tol * sum(abs(all terms in the relevant KCL equation)))
```

该 bound 是输出精度/数值 QA floor，不从本轮 residual 反推，也不作为物理事件或
机制证据；单点超过 bound 仍原样保留，不能通过删除样本修复。

### 5. Dynamic port/load-line diagnostic

physical 13 ps / 12x320 primary 必须生成 `V(IN)` vs `I(LIN|XBQ)` 的 parametric
trajectory，并以 raw time 做 hover/标记；同时生成 `V(SL1)` vs JSL/source
current 的 source-side trajectory。

可选的次级量明确命名为 **TWO-BOUNDARY DYNAMIC SECANT DIAGNOSTIC**：

`Z_sec(t)=V_IN(t)/(I_source_grounded(t)-I_physical_JSL(t))`。

仅在 `abs(denominator) > max(1e-18 A, 1e-12*max_abs_source)` 时保留；否则
mask。它不是 Thévenin impedance、不是 small-signal impedance、不是 constant
physical resistor，也不得单独决定 H4/H6。

### 6. H5 scalar-attenuation test

固定 13 ps / 12x320 logical1_read 的 activity window，计算无截距最小二乘：

`k = sum(I_grounded*I_physical)/sum(I_grounded^2)`；
`normalized_residual = ||I_physical-k*I_grounded||_2/||I_physical||_2`；
Pearson correlation；signed/positive/negative area ratios；signed centroid
shift；positive-peak time shift；最大残差时间。

fit 判断的 task-local band 预注册为：normalized residual `<=0.25`、correlation
`>=0.90`、positive-peak time shift `<=0.05 ps`、两波形不发生符号反转。
这些是模型拟合描述的审计带，不是物理常数；若 denominator/variance 不足，
fit 为 `INCONCLUSIVE`。同时报告 raw-origin fit 和分别减去 pre-window median 后的
baseline-corrected fit；两者若给出不同模型状态，H5/H6 保持 `UNRESOLVED`。超出 band 时只支持
`WAVEFORM/LOADLINE_RESHAPING_REQUIRED` 这一 bounded inference。

### 7. 12x320 vs 8x500 discriminator

固定比较 13 ps ideal replay（必要时对应 13 ps source fixture），并报告：source
peak/min、signed/positive/negative area、centroid/peak timing、effective
duration、`V(SL1)`、`I(LIN|XBQ)`、BJs/BJL1/BJL2 phase trajectory 和 current
partition。`0.0427 turn` 只作为已知 strict 数值差，不称 8x500 为 candidate。

这里的 `effective duration` 冻结定义为：先用 pre window `[80,94)` 的中位数作为
该 signal 的 baseline，在 activity window 内寻找
`abs(signal-baseline) >= max(1e-18 signal-unit, 0.05*max_abs_activity)` 的
首末 raw 样本，duration 为两者时间差；无满足样本则为 undefined。这是波形描述
量，不是事件判据。

## 假说状态的机械边界

- H1 的 bounded support 条件为：A/B pre-105 ps identity 通过，且 source current
  的绝对差分面积中至少 80% 位于 `[105,110] ps`；否则 H1 只能为
  `UNRESOLVED` 或 `DISFAVORED`，不把共同 stimulus 之后的差异自动归因于 duration。
- H2 的 bounded support 条件为：在 `[105,110] ps` 之外仍有超过 divergence floor
  的 source shape/timing difference，或 A/B 的 current centroid/positive/negative
  lobe timing 改变不能由单一延长区解释；若只有延长区增量，则 H2 不被单独支持。
- H3、H7 的“critical/primarily”措辞没有单变量干预支持，默认保持
  `UNRESOLVED`；内部轨迹只能作为 mediator/compatibility evidence。
- H4 的 support 只表示整体 source-load coupling 与 physical deviation 相容；若
  B/C 的 pre-state guard 已失败，必须同时标记“pre-state changed”，不得写成
  READ 期间的唯一 back-action。
- H5/H6 使用上一节冻结的 raw-origin 与 baseline-corrected 两套 scalar fit；两套
  fit 状态不一致时均为 `UNRESOLVED`，一致拒绝/支持才可给出相应 bounded status。

## Guard 与停止规则

- read0、logical0、两个 no-read controls 只做 guard，不作为机制拟合样本。
- 不得把任何 source current-time area 称为 SFQ；不把 BJL2 local candidate 称为
  JTL delivery；本矩阵没有 JTL/T1。
- 13ps/12x320 的 `1.016` 与 13ps/8x500 的 `0.973` 都贴近一圈，当前只有
  0.0125 ps 请求步长；不能称 robust operating margin。下一轮 candidate 前
  必须另行预注册 0.025/0.0125/0.00625 ps validation，本任务不执行。
- 若 A/B 在 `t<=105 ps` 的 pointwise identity 失败，立即标记
  `STOP_NUMERICAL_OR_DECK_IDENTITY`，停止因果机制解释。
- 若 required raw QA、时间网格、方向、面积映射或控制失败，整体为
  `DYNAMIC_SOURCE_LOADLINE_AUDIT_INCONCLUSIVE`，不是电路 FAIL。
- 仅当 source/load-line 变化与 internal trajectory 的 matched evidence 同时
  支持时，才允许 bounded mechanism family inference；不得从相关性写 unique
  causation。
- 本轮不实际调整参数；只有 evidence 足够时，报告下一实验的 parameter family
  及其 target quantity、falsifiable signature、stop rule；否则明确写
  `MECHANISM_AUDIT_INCONCLUSIVE`。

## 预期交付

- `REPORT.md`、`SUMMARY.md`；
- `analysis/source-waveform-comparison.csv`；
- `analysis/qb-internal-comparison.csv`；
- `analysis/divergence-timeline.json`；
- `analysis/scalar-attenuation-test.json`；
- `analysis/dynamic-port-diagnostics.csv`；
- `analysis/hypothesis-table.json`；
- `analysis/reviewer-notes.md`；
- `analysis/independent-raw-recheck.json`，用不复用主分析函数的 raw-only 路径复算关键量；
- `analysis/raw-provenance.json`，记录全部输入 raw SHA-256；
- `analysis/run_analysis.py`、`analysis/generate_plots.py`；
- `plots/` 下六张高价值 HTML 图：source A/B、QB internal A/B、source-load B/C、
  dynamic input IV、13ps load discriminator、causal timeline。

所有图只作描述性展示；raw、固定定义的数值表、strict reference 和控制才是
机制审计证据。完成后停止，不自动启动下一实验、不更新 HANDOVER/todo。
