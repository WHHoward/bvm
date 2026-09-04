# OLD-1111 vs NEW-1111 HISTORY-DIFFERENCE CAUSAL AUDIT

本报告是只读分析，不是新的物理实验，也不判断 4 圈或 5 圈哪一个“正确”。所有差分约定为 **NEW − OLD**。

## 1. Question

本轮只追踪 `4 → 5` 的历史因果链：

1. 70 ps 前两套轨迹是否逐点一致；
2. 110 ps 的 READ1 开始前是否仍有可观测状态差异；
3. NEW 的第五个整数相位 crossing 是前四个几乎不变、尾部再多一圈，还是 READ1 一开始就已经进入了不同的 QB 轨迹。

## 2. Data authority and no-new-simulation boundary

- OLD deck/raw：`test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/deck.cir` / `test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/raw.csv`
- NEW deck/raw：`test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/deck.cir` / `test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/raw.csv`
- 两套 fixture 都是 `HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT`；本轮没有以 canonical BVM 替代它们。
- 只消费 OLD ∩ NEW 的共同探针；没有 zero-fill、替代 NEW-only branch probe 或插值。
- `simulation_invoked = false`；旧/新 raw 在分析前后 SHA256 均未改变。

## 3. Deck/protocol difference audit

机械 diff 的结论：`fixed_core_equal_after_excluding_controls_prints_comments = true`，未分类的非注释/非 `.print`/非控制源差异数量为 `0`。

真正的 protocol 差异是 70–81 ps：

- OLD：四个 BVM 都有 `WL=+100 µA` 和 `SE=+100 µA` 的 71–80 ps 平台；
- NEW：70–90 ps 为 no-op；
- 两套在 WRITE1（95 ps 代表点）和最终 READ1（115 ps 代表点）的源语义相同。

NEW 另外追加了直接 branch `.print` 探针；这是可观测性变化，不是物理方程变化。完整逐行分类见 [`deck_diff_summary.json`](deck_diff_summary.json)。

## 4. 45–70 ps parity

OLD 有 158 个表头（含 `time`），NEW 有 230 个；共同的非时间探针为 **157** 个。两套时间 token 和浮点 time tuple 都完全一致：True，窗口实际覆盖 `45–70 ps`。

在所有共同探针、全部 `249` 个 baseline 样本上，逐点差分都为 0：

- 最大绝对差：`0`（native）；
- RMS：`0`（native）；
- 非零差分样本：`0`。

因此可以把 70 ps 作为本次 history intervention 的 causal anchor：在现有可观测共同探针上，70 ps 前没有先行差异。70.0 ps 存储点也仍相等；第一批 exact unequal samples 出现在 70.1 ps。

## 5. First divergence and 70–81 ps history intervention

下表的 robust 时间只是 task-local 描述性诊断：相对各信号自身后段幅度的 `1e-6`，并要求 3 个连续 exact-grid 样本；它不是物理 Gate。

| layer | first exact unequal (ps) | first descriptive robust (ps) |
|---|---:|---:|
| controls | 70.1 (I(I_SE1)) | 70.1 (I(I_SE1)) |
| bvm_r_loop | 70.1 (I(B_JM1|XBVM1)) | 70.1 (I(B_JM1|XBVM1)) |
| sl | 70.1 (I(L_PSL|XBVM1)) | 70.1 (I(L_PSL|XBVM1)) |
| sensing | 70.1 (I(B_LD01)) | 70.1 (I(B_LD01)) |
| qbin_lin | 70.1 (I(LIN|XBQ1)) | 70.1 (I(LIN|XBQ1)) |
| qb_internal | 70.1 (I(BJ1|XBQ1)) | 70.1 (I(BJ1|XBQ1)) |
| jtl | 70.1 (P(B01|XJTL1_1)) | 70.2 (V(B01|XJTL1_1)) |

观察到的层级顺序是：70.1 ps 控制源差异、BVM 内部/SL/QBIN/QB 差异已经出现；JTL 在 70.1 ps 已有数值不等式，但达到描述性 robust 尺度要晚一些（不同 JTL observable 约 70.2–70.6 ps）。这只是观察到的时间顺序，不能单凭时间顺序把网络响应证明成唯一因果。

70–81 ps 的动态扰动以关键 common probes 表示如下（完整逐探针统计在 `history_intervention`）：

| signal | max |NEW−OLD| | RMS | peak time |
|---|---:|---:|---:|
| `P(B_JM1|XBVM1)` | 0.179427 turns | 0.143762 turns | 73.2 ps |
| `P(B_JM2|XBVM1)` | 0.0459296 turns | 0.0318785 turns | 71.9 ps |
| `I(L_M3|XBVM1)` | 61.1226 µA | 46.456 µA | 71.6 ps |
| `V(SL1)` | 0.998919 mV | 0.337961 mV | 80.9 ps |
| `V(QBIN)` | 0.16912 mV | 0.0554678 mV | 80.9 ps |
| `I(LIN|XBQ1)` | 21.7776 µA | 11.6124 µA | 72.5 ps |

四颗 BVM 的主要内部响应（同一 70–81 ps 窗口）为：

| BVM | JM1 phase max diff (turns) | JM2 phase max diff (turns) | LM3 max diff (µA) |
|---|---:|---:|---:|
| BVM1 | 0.17943 | 0.04593 | 61.123 |
| BVM2 | 0.17881 | 0.046044 | 60.88 |
| BVM3 | 0.17779 | 0.046395 | 60.096 |
| BVM4 | 0.17645 | 0.047349 | 57.794 |

## 6. 81–90 ps recovery

| checkpoint | BVM internal max (unit/signals) | SL max | QB input max | QB internal max | JTL max |
|---:|---|---|---|---|---|
| 81 | 27.653 uA (I(B_JM1|XBVM4)) | 13.415 uA (I(L_PSL|XBVM4)) | 17.945 uA (I(LIN|XBQ1)) | 17.945 uA (I(BJS|XBQ1)) | 0.0019617 mV (V(B01|XJTL1_1)) |
| 85 | 17.662 uA (I(B_JS1|XBVM3)) | 4.5292 uA (I(L_PSL|XBVM4)) | 10.398 uA (I(LIN|XBQ1)) | 10.398 uA (I(BJS|XBQ1)) | 0.0017363 mV (V(B01|XJTL1_1)) |
| 89.9 | 6.0697 uA (I(B_JS1|XBVM3)) | 2.3921 uA (I(L_PSL|XBVM4)) | 5.7804 uA (I(LIN|XBQ1)) | 5.7804 uA (I(BJS|XBQ1)) | 0.0018714 mV (V(B01|XJTL1_1)) |
| 90 | 3.8442 uA (I(B_JS1|XBVM3)) | 1.923 uA (I(L_PSL|XBVM4)) | 5.2336 uA (I(LIN|XBQ1)) | 5.2336 uA (I(BJS|XBQ1)) | 0.0021831 mV (V(B01|XJTL1_1)) |

这些数值说明 READ0 的影响没有在 81 ps 立刻变成共同轨迹；在 WRITE1 开始的 90 ps，仍可从共同探针中看到 residual difference。这里没有对差异强行拟合单指数。

## 7. WRITE1 trajectory from different histories

两套在 90–101 ps 施加相同的 WRITE1 输入，但内部状态不同。下表是每颗 BVM 在该窗口的最大轨迹差；phase 已按连续 unwrap 后除以 `2π`，current 为 µA。

| BVM | JM1 phase max diff (turns) | JM2 phase max diff (turns) | LM3 max diff (µA) | JS1 phase max diff (turns) | JS2 phase max diff (turns) |
|---|---:|---:|---:|---:|---:|
| BVM1 | 0.0050147 | 0.0095455 | 12.403 | 0.13446 | 0.11805 |
| BVM2 | 0.0044361 | 0.010075 | 11.838 | 0.1298 | 0.1109 |
| BVM3 | 0.004249 | 0.010746 | 10.387 | 0.11399 | 0.098439 |
| BVM4 | 0.0030429 | 0.011241 | 8.1073 | 0.077797 | 0.06748 |

因此“相同 WRITE1 输入”并没有把两套 waveform 重新合并成逐点相同的 trajectory。这个结果支持 history-dependent initial condition / network-state sensitivity，但不是单独证明唯一机制。

## 8. PRE_READ1：110 ps 前的四颗 BVM state

`101–110 ps` 是半开区间，最后存储点为 109.9 ps。下表是该点 `NEW−OLD` 的 BVM 状态差；phase 为 turns，current 为 µA。

| BVM | ΔJM1 phase | ΔJM2 phase | ΔLM1 | ΔLM2 | ΔLM3 | ΔLPM |
|---|---:|---:|---:|---:|---:|---:|
| BVM1 | 0.00129823 | -0.00381424 | -1.3819 | 1.3819 | -4.83183 | 1.02336 |
| BVM2 | 0.00124236 | -0.00458683 | -1.34859 | 1.34859 | -4.52341 | 1.20996 |
| BVM3 | 0.000991535 | -0.00543769 | -1.3043 | 1.3043 | -4.1793 | 1.11866 |
| BVM4 | 0.000402025 | -0.0047099 | -0.9825 | 0.9825 | -3.05216 | 0.32303 |

在 109.9 ps，网络/QB 共同探针的差异为：`V(SL1)=-0.218441 mV`，`V(SL2)=-0.148088 mV`，`V(SL3)=-0.0353755 mV`，`V(SL4)=0.0303159 mV`，`P(BVMOUT)=-0.00090776 turns`，`V(QBIN)=0.00727888 mV`，`I(LIN)=1.3423 µA`，`P(BJ2)=0.000359165 turns`。

这直接回答问题②：在现有可观测量上，READ1 开始前两套系统仍没有重新收敛到同一状态。辅助的 isolated single-BVM S1 reference 仅用于量级/状态参照；它的 READ 时序与本 4-BVM old/new 不相同，因此不被当作 universal stored-1 threshold，也不把相似数值升级成逻辑状态证明。

作为辅助参照，BVM1 在 109.9 ps 的部分状态与 isolated S1 的同一采样点如下；S1 不是同 protocol 对照：

| quantity | OLD | NEW | isolated S1 | NEW−OLD |
|---|---:|---:|---:|---:|
| JM1_phase_turns | 0.9414169 | 0.9427152 | 0.9415923 | 0.001298227 |
| JM2_phase_turns | 0.07197964 | 0.06816539 | 0.07769034 | -0.003814244 |
| LM1_current_uA | -41.79045 | -43.17235 | -42.99614 | -1.3819 |
| LM2_current_uA | 41.79045 | 43.17235 | 42.99614 | 1.3819 |
| LM3_current_uA | 27.14512 | 22.31329 | 20.49247 | -4.83183 |
| LPM_current_uA | 41.74358 | 42.76694 | 42.72535 | 1.02336 |

## 9. READ1 input comparison

110–121 ps 的 WL/BL/SE common control raw waveform 逐点完全相同：`all_common_controls_exactly_equal = true`。

但 QB 输入在 READ1 的起点已经不是同一 waveform：

- `V(QBIN)` 在 110–121 ps 的最大差为 `0.530648 mV`，RMS 为 `0.180555 mV`，峰值差出现在 `120.8 ps`；
- `I(LIN|XBQ1)` 最大差为 `35.0537 µA`，RMS 为 `13.4658 µA`，峰值差出现在 `120.9 ps`；
- 两个 QB input signal 在 110.0 ps 的 `first exact unequal` 已经成立，而不是等到第五圈尾部才第一次分叉。

## 10. BJ2：四圈与五圈的 trajectory

同一 JJ、同一 `P(BJ2|XBQ1)` 和 `V(BJ2|XBQ1)`，窗口为 `[110,170) ps`：

| quantity | OLD | NEW |
|---|---:|---:|
| phase endpoint delta | 3.999197998 turns | 4.999159911 turns |
| same-JJ voltage area / Φ0 | 3.999179665 turns | 4.999143858 turns |
| phase-area residual | 1.8333116e-05 turns | 1.6052401e-05 turns |
| integer crossings observed | 4 | 5 |

相位差轨迹 `Δφ = unwrap(NEW) − unwrap(OLD)` 在 110 ps 为 `0.00024891833 turns`，到 115 ps 为 `0.030209518 turns`，到 120 ps 为 `0.10495314 turns`，到 138.8 ps 为 `0.97945862 turns`，到 169.9 ps 为 `1.0002108 turns`。这不是简单的一个末端孤立尖峰。

## 11. Extra-turn localization and pattern

以下 crossing 是连续相位轨迹的整数 crossing marker，**不是 clean SFQ event count**，也没有用 whole-window phase displacement 代替严格事件判定。

| crossing index | OLD sample time (ps) | NEW sample time (ps) | NEW−OLD timing (ps) |
|---:|---:|---:|---:|
| 1 | 118.3 | 118.1 | -0.2 |
| 2 | 121.7 | 121.4 | -0.3 |
| 3 | 125.5 | 124.9 | -0.6 |
| 4 | 138.8 | 129.5 | -9.3 |
| 5 | — | 141.4 | — |
| 6 | — | — | — |

第一至第三个 crossing 的时间仍较接近，但第四个 crossing 已从 OLD 的 `138.8 ps` 移到 NEW 的 `129.5 ps`；NEW 的第五个 crossing 为 `141.4 ps`，此时 OLD 已接近四圈后的 quiescent-like tail。因此最准确的描述是：

**不是“前四圈基本相同、只在尾部追加第五圈”。** 更符合现有 raw 的是 **READ1 一开始就存在小的状态/输入差异，随后整个 QB trajectory 逐步分叉，并在后段表现为 NEW 多出第五个 crossing**。也就是说，结果同时包含“late extra turn”这个表象，但因果形状更接近 `WHOLE_TRAJECTORY_CHANGE_WITH_LATE_EXTRA_TURN`。

这仍然不是 4/5 个 clean SFQ 的结论；需要独立的同 JJ segment/retrap 事件证据才能谈严格事件数。

## 12. Retrapping / tail

本报告只使用一个透明的描述性指示器：最后一个整数 crossing 之后，`|V(BJ2)| ≤ 0.05 mV` 持续 3 个 exact-grid 样本。它不是 global retrap metric。

| run | last integer crossing | quiescent-like voltage return | tail phase delta 160–170 ps |
|---|---:|---:|---:|
| OLD | 138.8 ps | 138.9 ps | 0.00046154933 turns |
| NEW | 141.4 ps | 141.5 ps | -7.1619724e-05 turns |

NEW 的 quiescent-like voltage return 比 OLD 晚约 `2.6 ps`，这与 NEW 在后段仍继续运行并获得第五个 crossing 的观察相符。

## 13. Downstream JTL

| stage | OLD B02 crossing count | NEW B02 crossing count | NEW fifth crossing |
|---|---:|---:|---:|
| JTL1 | 4 | 5 | 142.3 ps |
| JTL2 | 4 | 5 | 145.5 ps |
| JTL3 | 4 | 5 | 146.7 ps |
| JTL4 | 4 | 5 | 149.8 ps |
| JTL5 | 4 | 5 | 152.7 ps |
| JTL6 | 4 | 5 | 153.4 ps |

在现有 common JTL phase probes 中，第五个 integer crossing 已经在 QB `BJ2` 出现，并随后在 `JTL1` 的 B02 可见；六级 JTL 继续保留它。因此当前证据更支持“QB 已先产生不同的源 trajectory，JTL 传递该差异”，不支持“第五个响应只由后级 JTL 新产生”。这仍是 trajectory-marker 证据，不是 clean SFQ transport Gate。

## 14. Compact causal timeline

| time | observed state |
|---:|---|
| 45–70 ps | 所有 157 个共同探针逐点相等。 |
| 70.0 ps | OLD/NEW 仍相等；history intervention 的边界。 |
| 70.1 ps | OLD 的 all-BVM positive READ 与 NEW no-op 造成控制差异；BVM/SL/QBIN/QB 共同探针同步出现 exact difference。 |
| 约 70.2–70.6 ps | JTL observable 由数值微差进入描述性 robust 差异，具体时间依 observable 而变。 |
| 81–90 ps | READ0 结束后差异衰减但未消失。 |
| 90–101 ps | 相同 WRITE1 从不同 history state 出发，BVM 内部 trajectory 仍不同。 |
| 109.9 ps | final READ1 前，四颗 BVM、SL、BVMout、QBIN/LIN、BJ2 均仍有可观测 residual difference。 |
| 110.0 ps | READ1 控制相同，但 QB input 已不是同一 waveform。 |
| 118.1 / 118.3 ps | NEW / OLD first BJ2 integer crossing。 |
| 129.5 ps | NEW fourth BJ2 crossing；OLD 尚未到第四个 crossing。 |
| 138.8 ps | OLD fourth BJ2 crossing。 |
| 141.4 ps | NEW fifth BJ2 crossing；OLD 已接近四圈 tail。 |
| 138.9 / 141.5 ps | OLD / NEW 的描述性 quiescent-like voltage return。 |

## 15. OBSERVED

- 70 ps 前，在当前共同探针上逐点一致；没有发现 pre-intervention hidden difference 的证据。
- 70–81 ps 的 READ0 protocol 差异确实先改变了 BVM/SL/QB 可观测轨迹，并且差异持续到 109.9 ps。
- 110 ps 的 READ1 控制相同，但 QB input 和 BJ2 trajectory 从起点已有差异。
- NEW 的第四个 crossing 明显提前，第五个 crossing 发生在 OLD 已接近 retrap-like tail 之后。
- JTL1–JTL6 的 B02 trajectory 都保留 NEW 的第五个 integer crossing；未观察到后级 JTL 首次创造第五圈。

## 16. INFERENCE

- 70–81 ps 的 history 是 `4→5` 改变的强候选前置条件；因为该 protocol 差异在 70 ps 前后具有清晰时间锚点，并在 PRE_READ1 仍可见。
- 轨迹形状不是“完全相同的前四圈 + 独立尾部第五圈”。更合理的 task-local 描述是：不同 history 造成 preconditioning，READ1 从一开始就进入略有不同的 QB 动力学轨迹，差异在后段积累为额外 crossing。
- 现有证据支持“QB 先分叉、JTL 后传递”，但不把时间先后单独当作唯一因果证明。

## 17. UNKNOWN / OBSERVABILITY GAP

- 这不是 one-variable causal A/B：OLD/NEW 的整份 deck 生成上下文和 `.print` 集合并非完全相同，虽然机械审计已将可见差异分类为 READ0 protocol 与 observability-only changes。
- 不能仅凭本轮共同 probe 断言未观测的 hidden state 没有差异；只能说当前可观测 state 已不同。
- 不能由整数 phase crossings 或 whole-window 4/5 turns 推导 clean SFQ event count、retrap event identity、收敛性或哪一结果物理正确。
- 不能据此证明 canonical BVM、single-BVM、过程裕度、T1、论文机制或唯一工作机理。

## 18. Minimal future causal experiment (PROPOSED_NOT_AUTHORIZED)

如果用户审阅后仍需做真正的因果 A/B，最小方案是在同一 NEW all-one 1111 fixture 中只切换 70–81 ps：`READ0-present` vs `READ0-absent`，其余 deck、source、probe、timestep、stop time 全部相同。该方案本轮 **未生成、未运行、未授权**。

## 19. Human gate

`state: AWAITING_USER_REVIEW`

`analysis_completed: true`

`user_reviewed: false`

`next_physical_experiment_authorized: false`

`automatic_next_experiment: false`

`next_action: STOP`

## Plots

- [OLD_NEW_PROTOCOL_CONTROL.html](../plots/OLD_NEW_PROTOCOL_CONTROL.html)
- [PRE70_PARITY.html](../plots/PRE70_PARITY.html)
- [READ0_HISTORY_DIVERGENCE_BVM.html](../plots/READ0_HISTORY_DIVERGENCE_BVM.html)
- [WRITE1_HISTORY_DEPENDENCE.html](../plots/WRITE1_HISTORY_DEPENDENCE.html)
- [PRE_READ1_STATE_COMPARISON.html](../plots/PRE_READ1_STATE_COMPARISON.html)
- [READ1_QBIN_LIN_COMPARISON.html](../plots/READ1_QBIN_LIN_COMPARISON.html)
- [BJ2_4_VS_5_TURN.html](../plots/BJ2_4_VS_5_TURN.html)
- [BJ2_CROSSING_TIMELINE.html](../plots/BJ2_CROSSING_TIMELINE.html)
- [QB_RETRAP_TAIL_COMPARISON.html](../plots/QB_RETRAP_TAIL_COMPARISON.html)
- [JTL6_4_VS_5.html](../plots/JTL6_4_VS_5.html)
- [OLD_MINUS_NEW_MULTI_LAYER.html](../plots/OLD_MINUS_NEW_MULTI_LAYER.html)
