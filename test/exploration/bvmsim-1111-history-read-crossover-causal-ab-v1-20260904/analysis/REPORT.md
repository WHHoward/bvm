# 1111 HISTORY-READ CROSSOVER CAUSAL A/B

本报告只分析四个条件 `O+ / O- / N- / N+` 的 crossover；不把最终 4/5 表象单独当作因果结论。所有 `P(...)` 原始值是 rad；显示的 turns 仅由 continuous unwrap(rad)/(2π) 得到。

## 1. Question

检验 70–81 ps `HISTORY_READ_PRESENT/ABSENT` 是否比 OLD/NEW deck context 更能解释 BVM internal state、LSL、LIN/QBIN 和 QB BJ2 trajectory。

## 2. Existing evidence and four-condition design

| condition | context | history | authority |
|---|---|---|---|
| O+ | OLD | PRESENT | immutable existing raw |
| O- | OLD | ABSENT | new physical run |
| N- | NEW | ABSENT | immutable existing raw |
| N+ | NEW | PRESENT | new physical run |

O+ 和 N- 的原始 CSV 未重跑、未覆盖；O- 和 N+ 是本轮唯一新增的两个物理条件。

## 3. What changed / what did not change

O- 仅移除 OLD 母本的 70–81 ps all-BVM positive history read；N+ 仅把 exact OLD history waveform 放入 NEW 母本。其它物理主体、WRITE1、final READ1、QB/JTL/load、模型、`dt=0.1 ps` 和停止时间均冻结。O- 采用完整 branch probe schema 的额外 `.print` 只改变 observability。

## 4. Static deck-diff proof

见 `analysis/static_preflight.json`：未分类 physics difference 为 0；history present/absent 的源波形比较最大差均为 0 A；BL、WRITE1、final READ1、history 窗外源波形比较最大差均为 0 A；完整 probe schema 为 229 项。

## 5. Artifact validity

post-run QA: **PASS**。四组均为 1549 个样本，存储时间 45.0–199.9 ps；四组 float/time-token grid exact equal；比较无插值。原始存储间隔实际包含 0.1/0.2 ps，`0.1 ps` 是 requested timestep。

## 6. 70 ps pre-intervention parity

在 `baseline_common=[45,70) ps`，O+ vs O- 与 N+ vs N- 的 common probes 逐点一致；完整 pair exactness 也见 `exact_common_grid_pairs`。因此本 crossover 的 history intervention 有明确的 70 ps anchor。

## 7. History intervention and control semantics

`HISTORY_READ_PRESENT` 的 75 ps 检查为 WL=+100 µA、BL=0、SE=+100 µA；`HISTORY_READ_ABSENT` 为三者 0。95 ps WRITE1 与 115 ps final READ1 的控制语义保持一致。详情见 `controls`。

## 8. PRE_READ1 logical-state marker

四条件的 protocol state target 都是 1111。109.9 ps 的 `JM1_positive_marker` 仅作极性/存储方向描述；不使用 `JM1 AND JM2 >= 0.25 turn` 作为唯一逻辑判据。实际的 JM1/JM2/JS1/JS2/LM1/LM2/LM3/LPM 数值和单位见 `pre_read1_state_vectors_at_109_9ps`。

| condition | BVM | JM1 phase (turns) | JM2 phase (turns) | LM3 (µA) | LPM (µA) | JS1 phase (turns) | JS2 phase (turns) |
|---|---:|---:|---:|---:|---:|---:|---:|
| O+ | BVM1 | 0.941416926 | 0.071979637 | 27.145120 | 41.743580 | 0.011121178 | -0.090520488 |
| O+ | BVM2 | 0.941369021 | 0.072951326 | 27.538820 | 41.551410 | 0.009331880 | -0.094337183 |
| O+ | BVM3 | 0.941274801 | 0.074241452 | 28.473350 | 41.821520 | 0.020854979 | -0.087368217 |
| O+ | BVM4 | 0.941200476 | 0.074033691 | 28.137040 | 43.063470 | 0.045258732 | -0.060863747 |
| O- | BVM1 | 0.942715153 | 0.068165394 | 22.313290 | 42.766940 | 0.039309695 | -0.038765497 |
| O- | BVM2 | 0.942611384 | 0.068364497 | 23.015410 | 42.761370 | 0.041201920 | -0.040308138 |
| O- | BVM3 | 0.942266336 | 0.068803764 | 24.294050 | 42.940180 | 0.045044669 | -0.042580091 |
| O- | BVM4 | 0.941602501 | 0.069323787 | 25.084880 | 43.386500 | 0.048286973 | -0.042752487 |
| N- | BVM1 | 0.942715153 | 0.068165394 | 22.313290 | 42.766940 | 0.039309695 | -0.038765497 |
| N- | BVM2 | 0.942611384 | 0.068364497 | 23.015410 | 42.761370 | 0.041201920 | -0.040308138 |
| N- | BVM3 | 0.942266336 | 0.068803764 | 24.294050 | 42.940180 | 0.045044669 | -0.042580091 |
| N- | BVM4 | 0.941602501 | 0.069323787 | 25.084880 | 43.386500 | 0.048286973 | -0.042752487 |
| N+ | BVM1 | 0.941416926 | 0.071979637 | 27.145120 | 41.743580 | 0.011121178 | -0.090520488 |
| N+ | BVM2 | 0.941369021 | 0.072951326 | 27.538820 | 41.551410 | 0.009331880 | -0.094337183 |
| N+ | BVM3 | 0.941274801 | 0.074241452 | 28.473350 | 41.821520 | 0.020854979 | -0.087368217 |
| N+ | BVM4 | 0.941200476 | 0.074033691 | 28.137040 | 43.063470 | 0.045258732 | -0.060863747 |

## 9. PRE_READ1 analog-state crossover

不把不同量纲裸相加；pairwise comparison 使用每个 signal 独立的 robust scale（四条件、该窗口的 p95 absolute deviation，floor=1e-12 display unit），同时保留逐 signal absolute/RMS difference。

- `bvm_internal` (pre_read1): history-pair median normalized RMS=0，context-pair median normalized RMS=0.284654；`history_grouping_observed=True`。
- `sl` (read1_response): history-pair median normalized RMS=0，context-pair median normalized RMS=0.260749；`history_grouping_observed=True`。
- `qbin_lin` (read1_response): history-pair median normalized RMS=0，context-pair median normalized RMS=0.22075；`history_grouping_observed=True`。
- `qb_trajectory` (trajectory): history-pair median normalized RMS=0，context-pair median normalized RMS=0.199046；`history_grouping_observed=True`。

## 10. BVM internal crossover

重点信号覆盖 JM1、JM2、LM3、JS1、JS2、LM1、LM2、LPM；完整逐信号 pair metrics 在 `pairwise.bvm_internal`，不只看 JM1。R_S/LS3 虽在 O−/N−/N+ 的 full-probe raw 中保留，但不可修改的 O+ historical raw 缺少这两列，因此不纳入四条件聚合，跨四条件结论记为 UNKNOWN。

## 11. BVM LSL output crossover

四颗 BVM 的 `I(L_SL|XBVMn)` 均作为独立 waveform 统计；各自的 min/max/p2p/RMS/signed integral/peak time 在 `bvm_lsl_waveforms`，四条件同图在 `plots/comparison/BVM1_LSL_CROSSOVER.html` 等四张图中。

## 12. ΣLSL → LIN closure

使用共享 `bvmtools.kcl.linear_kcl_residual`，方向固定为 `I(LIN) - Σ I(L_SL)`；并对四个 pair 的差分验证相同关系。`lin_minus_sum_lsl_closure` 同时给出 history window、PRE_READ1 和 final response 的 max-abs/RMS KCL residual，单位 µA。

## 13. QB input crossover

先比较 BVM/LSL 与 LIN，再看 QB；`V(QBIN)`、`I(LIN|XBQ1)`、`V(QBOUT)` 的四条件 waveform 和 pairwise distances 在 `qbin_lin_waveforms` 与 `pairwise.qbin_lin`。

## 14. BJ2 trajectory crossover

| condition | endpoint Δphase (turns) | same-JJ V area/Φ0 (turns) | phase-area residual (turns) | integer crossing markers |
|---|---:|---:|---:|---|
| O+ | 3.999197998 | 3.999179665 | 1.833e-05 | 118.3, 121.7, 125.5, 138.8 ps |
| O- | 4.999159911 | 4.999143858 | 1.605e-05 | 118.1, 121.4, 124.9, 129.5, 141.4 ps |
| N- | 4.999159911 | 4.999143858 | 1.605e-05 | 118.1, 121.4, 124.9, 129.5, 141.4 ps |
| N+ | 3.999197998 | 3.999179665 | 1.833e-05 | 118.3, 121.7, 125.5, 138.8 ps |

这些是同一 BJ2 的 phase/voltage trajectory markers；integer crossing 数和 cumulative turns **不是 clean SFQ event count**。`BJ2_CROSSING_TIMELINE_2X2.html` 只作轨迹显示。

## 15. History grouping vs context grouping

当前 crossover assessment: **HISTORY_GROUPING_OBSERVED_ACROSS_KEY_LAYERS_WITH_EXACT_COMMON_GRID_MATCHES**。history grouping across BVM internal / SL / LIN-QBIN / QB trajectory = `True`；O+≈N+ 和 O-≈N- 在 common raw samples 上同时 exact = `True`；两组 context pair 均出现可观测差异 = `True`。

这里的“≈”首先按 exact stored-grid comparison 报告；若不是 0，则报告实际 max/RMS，不事后引入 5%/10% 工程容差。

## 16. OBSERVED

- 两个新 artifact 通过 solver/raw/header/time-grid/model-warning QA。
- 70 ps 前同 context 的 history intervention pair 逐点一致；history waveform 本身与静态预检 exact match。
- 四条件的 history pairs 与 context pairs 已同时纳入；不能只根据最终 4/5 交换下结论。
- 本次实际观察到 O+≈N+ 且 O-≈N- 横跨 BVM internal、LSL、LIN/QBIN、BJ2；这是“按 history 分组”的观察，不是唯一机制证明。

## 17. INFERENCE

本次四层均满足 history grouping，因此在本模型、此 stimulus、此负载和 dt=0.1 ps 的有界 crossover 因果范围内，previous-read preconditioning 得到强支持，可作为解释 4/5 trajectory split 的主要驱动因素；这不是“history 是唯一原因”的证明。

## 18. UNKNOWN

本轮不证明 clean SFQ count、数值收敛、过程裕度、canonical BVM compatibility、single-BVM compatibility、硬件行为、论文机制身份或唯一 root cause；也不把局部 JJ phase 当成下游 SFQ 接收。

## 19. Interpretation ceiling and next options

本轮只允许给出有界的 history-vs-context crossover 观察。可能的后续选项（均未执行）：(1) 在同一 NEW fixture 中重复一组更严格的 history-only A/B；(2) 经用户授权后做 history timing sensitivity；(3) 经用户授权后再做独立 timestep/initial-state 检查。

## 20. Human gate

`AWAITING_USER_REVIEW`；`user_reviewed=false`；`next_step_authorized=false`；`automatic_next_experiment=false`；`next_action=STOP`。本轮不自动启动任何后续物理实验。
