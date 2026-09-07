# N3/N4 replay deep dive — internal-time-aligned evidence pack

本页是已有 N3/N4 replay raw 的 **READ-ONLY ANALYSIS / EVIDENCE PACKAGING** 修订版。本轮没有新增 JoSIM solve，没有改变 circuit、parameter、timing、replay waveform 或任何 existing raw；所有派生积分都使用 CSV 实际存储的 time grid。

证据标签：`OBSERVED`=raw 直接可见；`DERIVED`=从 raw 按注册数学运算得到；`BOUNDED_RESULT`=只在本固定 replay fixture、参数和窗口内成立；`UNKNOWN`=当前证据不能可靠分离。P(...) raw 单位为 radians；显示 turns 只代表 `rad/(2*pi)`，不代表 SFQ 或 event count。current/voltage area 也不是 SFQ count。

## 1. 时间参考修正：internal response 与 downstream arrival 分开

`OBSERVED/DERIVED`：下表保留原先的前三个 descriptive response timing chain。`JTL1`、`JTL6` 和 `R_TERM` 是下游传播/终端参考，不能回写成 QB 内部发生时间。

| case | response | BJ1 | BJ2 | QBOUT | JTL1 | JTL6 | R_TERM |
|---|---:|---:|---:|---:|---:|---:|---:|
| N3_REPLAY | 1 | 113.4 ps | 115.2 ps | 115.4 ps | 116.4 ps | 131.2 ps | 132.8 ps |
| N3_REPLAY | 2 | 117.8 ps | 119.6 ps | 119.7 ps | 120.8 ps | 136.8 ps | 138.4 ps |
| N3_REPLAY | 3 | 122.3 ps | 125.4 ps | 125.9 ps | 126.6 ps | 142.6 ps | 144.2 ps |
| N4_REPLAY | 1 | 113.0 ps | 114.5 ps | 114.7 ps | 115.8 ps | 130.5 ps | 132.1 ps |
| N4_REPLAY | 2 | 116.1 ps | 118.3 ps | 118.4 ps | 119.5 ps | 135.4 ps | 137.0 ps |
| N4_REPLAY | 3 | **120.0 ps** | **121.4 ps** | **121.9 ps** | **123.3 ps** | **140.1 ps** | **141.6 ps** |

因此本轮明确定义：`t3_BJ1=120.0 ps`、`t3_BJ2=121.4 ps`、`t3_QBOUT=121.9 ps` 是 N4 第三个内部参考；`t3_JTL1=123.3 ps`、`t3_JTL6=140.1 ps`、`t3_RTERM=141.6 ps` 是下游参考。`141.6 ps` 仍是有效的 `OBSERVED` terminal arrival，但不是 QB internal third-response reference。

旧 `analysis/n4_post_third_response.json` 保留不动，但其中以 `[141.6,200) ps` 作为 source residual 起点的解释已被当前 artifact supersede。最终使用的版本是 `analysis/n3_n4_internal_time_aligned_analysis_v3.json`。

## 2. N4 source drive：围绕三个 internal reference 重算

`OBSERVED/DERIVED`：以下均为 `I(I_REPLAY)`，窗口为半开区间 `[reference,135) ps`；面积单位为 `uA*ps`，阈值正向跨度使用 5 uA 描述性 activity threshold。`significant-positive covered` 是实际相邻存储样本区间的总时长；这些量都不是事件数。

| internal reference | samples | positive peak | negative peak | max abs | RMS | signed area | positive / negative area | significant-positive span / covered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| after `t3_BJ1=120.0 ps` | 150 | 235.526 uA | -37.658 uA | 235.526 uA | 66.836 uA | 426.196 | 500.188 / -73.992 | 14.9 / 8.4 ps |
| after `t3_BJ2=121.4 ps` | 136 | 85.951 uA | -37.658 uA | 85.951 uA | 29.316 uA | 160.535 | 234.527 / -73.992 | 13.5 / 7.0 ps |
| after `t3_QBOUT=121.9 ps` | 131 | 70.275 uA | -37.658 uA | 70.275 uA | 26.779 uA | 128.512 | 202.504 / -73.992 | 13.0 / 6.5 ps |

`N1_REPLAY` first-response source reference 是 `[110,138.8) ps`：positive peak `68.414 uA`、RMS `26.489 uA`、signed/positive/negative area `519.158 / 529.909 / -10.751 uA*ps`。它只是 bounded first-response reference，不是“一份完整第四 pulse”的证明。

`BOUNDED_RESULT`：第三个 N4 QB 内部响应之后，尤其从 `t3_QBOUT=121.9 ps` 起，source 仍有约 `70.275 uA` positive peak、`26.779 uA` RMS 和 `202.504 uA*ps` positive area；因此不能再写“第三个 response 后 source 已基本耗尽”。这些量只说明仍有 non-negligible source drive，并不说明后续一定形成完整 response。

## 3. `[120,135) ps` fourth-attempt search

`OBSERVED/BOUNDED_RESULT`：`N4_REPLAY` 在内部窗口中有 residual activity/candidate，但证据不支持把它升级为一个完整第四 response：

- `QBIN`：`122.8 ps` 的约 `+0.619 mV` 以及后续正负 excursion，标为 **partial excursion candidate**。
- `BJS`：约 `123.4–134.9 ps` 仍有交替电压 activity，标为 **residual nonlinear activity**，没有逐响应分配。
- `BJ1`：`122.8 ps` 约 `+0.450 mV`，以及之后较小的正负 activity，标为 **partial excursion / failed candidate**。
- `QBOUT`：`123.4 ps` 约 `+0.565 mV`，但与第三个输出尾部/`JTL1` downstream timing 相邻，标为 **ambiguous post-QBOUT activity**。
- `BJ2`：从 `122.0 ps` 起没有超过注册 `0.5 mV` 的可分离 positive/absolute candidate；没有观察到完整的 post-QBOUT BJ2 progression。
- `JTL1`：从第三个 `123.3 ps` reference 后没有新的可分离 `0.5 mV` candidate；`JTL6`/`R_TERM` 只保留 downstream residual checks，也没有新的一条完整第四级联链。

所以 `fourth partial attempt` 的准确表述是：**观察到 bounded candidate activity（QBIN/BJS/BJ1/QBOUT），但不是 confirmed fourth response；完整 BJ2 trajectory 和 downstream continuation 未观察到**。最早缺失的完整 progression 位于 residual front-end/internal activity 与 `BJ1→BJ2` 之间，精确边界为 `UNKNOWN`；earliest divergence / missing progression 不是 root cause。

## 4. response spacing 与 event-local state

`OBSERVED` spacing 保留如下：

- N3：BJ1 `4.4/4.5 ps`，BJ2 `4.4/5.8 ps`；R_TERM `5.6/5.8 ps`。
- N4：BJ1 `3.1/3.9 ps`，BJ2 `3.8/3.1 ps`；R_TERM `4.9/4.6 ps`。

`DERIVED` event-local state 使用每个 case 的 BJ1 internal reference，并对每个 response 统一取 `-0.5, 0, +0.5, +1, +2, +3 ps`；比较 BJS、BJ1、BJ2、L1/L2/L3、相关 current/voltage 和 independently-unwrapped continuous phase。对应的全量状态在 `analysis/n3_n4_internal_time_aligned_analysis_v3.json` 中保存。

`UNKNOWN / NOT ESTABLISHED`：固定 offset 下的 current、voltage 和 continuous-phase state 有 response-dependent differences，但没有预注册的单一 unrecovered-state scalar、阈值或单调趋势可以把它们唯一解释为 recovery/dead-time failure。spacing 变短本身不是 dead time；source 后期减小本身也不是 stimulus exhaustion 的证明。

## 5. bottleneck classification

`BOUNDED_RESULT`：当前选择改为 **F. MIXED_OR_UNRESOLVED**。旧的 **D. EFFECTIVE_STIMULUS_LIMIT** 不再作为首选；它只能作为待区分候选。证据矩阵为：

| candidate | bounded assessment | 支持/反对的关键 raw evidence |
|---|---|---|
| A. FRONT_END_ACCEPTANCE_LIMIT | INCONCLUSIVE | QBIN/BJS residual activity 存在，但 front-end acceptance boundary 未被唯一定位 |
| B. INTERNAL_REGENERATION_LIMIT | INCONCLUSIVE | partial BJ1 且无 post-QBOUT BJ2 candidate；但前三条链完整到达下游，缺少 intervention isolation |
| C. RECOVERY_OR_DEAD_TIME_LIMIT | UNKNOWN | N4 spacing 较短；统一 offset state 没有单调 unrecovered-state evidence |
| D. EFFECTIVE_STIMULUS_LIMIT | INCONCLUSIVE | source trajectory 逐渐衰减，但 internal windows 仍有几十 uA 级 drive，不支持“已耗尽” |
| E. DOWNSTREAM_PROPAGATION_LIMIT | NOT SUPPORTED AS PRIMARY | 前三条 QB response 均到达 JTL6/termination；第四条在完整 BJ2 之前已缺 progression |
| F. MIXED_OR_UNRESOLVED | SELECTED | A/B/C/D 无法由当前 replay 唯一分离，且存在 partial internal activity + missing progression |

这只是固定 replay 的 bounded raw classification，不是 saturation、dead-time、recovery、bias 或其它机制的已证实 root cause；也不是硬件结论。

## 6. 当前 evidence pack

每个 standalone 图都明确标出 case、signal、raw/derived、单位和时间窗；P(...) 的 raw 来源保留 radians，图的 `-j 2pi` 只显示 `rad/(2*pi)` turns。comparison 图先分别 independently unwrap phase，再计算 delta；没有 wrapped-phase subtraction。连续 phase winding、phase displacement、voltage/current area 和 threshold activity 均不作 SFQ count。

### Standalone QB full internal

- [N3_REPLAY QB full internal](plots/deep_dive/internal_time_aligned_v2/N3_REPLAY_QB_FULL_INTERNAL.html)
- [N4_REPLAY QB full internal](plots/deep_dive/internal_time_aligned_v2/N4_REPLAY_QB_FULL_INTERNAL.html)

两页均覆盖：`I_REPLAY`、`QBIN`、LIN I/V、BJS P/V/I、L1 I/V、BJ1 P/V/I、RJ1 I/V、L2 I/V、IB current、BJ2 P/V/I、RJ2 I/V、L3 I/V、`QBOUT`。

### QB comparison / critical zoom

- [N3 vs N4 QB full internal raw + delta](plots/deep_dive/internal_time_aligned_v2/N3_VS_N4_QB_FULL_INTERNAL.html)
- [N4 fourth-attempt zoom, 118–140 ps](plots/deep_dive/internal_time_aligned_v2/N4_FOURTH_ATTEMPT_ZOOM_118_140.html)
- [event 1 N3/N4 internal-time aligned](plots/deep_dive/internal_time_aligned_v2/EVENT1_N3_N4_INTERNAL_ALIGNED.html)
- [event 2 N3/N4 internal-time aligned](plots/deep_dive/internal_time_aligned_v2/EVENT2_N3_N4_INTERNAL_ALIGNED.html)
- [event 3 N3/N4 internal-time aligned](plots/deep_dive/internal_time_aligned_v2/EVENT3_N3_N4_INTERNAL_ALIGNED.html)

### Standalone and comparison JTL full chain

- [N3_REPLAY JTL1–JTL6 full chain](plots/deep_dive/internal_time_aligned_v2/N3_REPLAY_JTL_FULL_CHAIN.html)
- [N4_REPLAY JTL1–JTL6 full chain](plots/deep_dive/internal_time_aligned_v2/N4_REPLAY_JTL_FULL_CHAIN.html)
- [N3 vs N4 JTL1–JTL6 full-chain raw + delta](plots/deep_dive/internal_time_aligned_v2/N3_VS_N4_JTL_FULL_CHAIN.html)

JTL machine data 保留 JTL1–JTL6 每一级的 B01/B02 P/V/I 及各级 output voltage，另含 `I(R_TERM)`；human-readable 页面按单位分组显示，但没有丢弃中间级。

### Machine-readable / QA

- 当前分析：[analysis/n3_n4_internal_time_aligned_analysis_v3.json](analysis/n3_n4_internal_time_aligned_analysis_v3.json)
- raw/provenance QA：[analysis/internal_time_aligned_v2_qa.json](analysis/internal_time_aligned_v2_qa.json)
- 独立标准库复算：[analysis/internal_time_aligned_v2_independent_check.json](analysis/internal_time_aligned_v2_independent_check.json)
- plot manifest：[analysis/internal_time_aligned_v2_plot_manifest.json](analysis/internal_time_aligned_v2_plot_manifest.json)
- visualization QA：[analysis/internal_time_aligned_v2_viz_qa.json](analysis/internal_time_aligned_v2_viz_qa.json)
- analysis / rendering scripts：[analysis/internal_time_aligned.py](analysis/internal_time_aligned.py)、[analysis/render_internal_time_aligned.py](analysis/render_internal_time_aligned.py)、[analysis/internal_time_aligned_independent_check.py](analysis/internal_time_aligned_independent_check.py)

`internal_time_aligned_v2_viz_qa.json` 为 `PASS`：10/10 页面、standalone coverage、comparison 双轨、critical zoom 均通过；独立数值复算为 `PASS`（33 项比较）；N1/N3/N4 raw hashes 前后 unchanged。该 evidence pack 仍停留在 read-only bounded analysis，不自动开始下一轮实验。
