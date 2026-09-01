# BVM_QB_DYNAMIC_SOURCE_LOADLINE_AUDIT_V1

## 1. Executive scientific result: `DYNAMIC_SOURCE_LOADLINE_MECHANISM_SUPPORTED`

本轮是只读 physics-first mechanism audit：没有运行 JoSIM、没有扫参、没有修改 QB/BVM/JSL、读宽、拓扑、JTL、T1 或 magnetic coupling。所有 raw 证据来自已存在的 48-run matrix；既有 strict BJL2 分类只作为冻结 reference 使用。

最强有界结论：当前证据支持整体 dynamic source-load interaction，并且 scalar attenuation 不能充分描述 physical source waveform；不能唯一定位到某一颗器件。

A/B 105 ps 前 identity：12x320=`PASS`，8x500=`PASS`；B/C pre-state guard：`CHANGED`；QB KCL closure：ideal/physical=`PASS`/`PASS`。

## 2. Observed

- 输入目录为 `test/exploration/bvm-load-qb-matrix-v1-20260901`；48/48 raw 的 hash、sidecar、执行返回码、列和时间轴 QA：`PASS`。
- 9/13 ps source 的首个 JSL branch `I(B_LD1)` 在 12x320 activity 指标分别为 peak `7.90668e-05` / `7.90668e-05` A，signed area `516.362` / `863.198` uA·ps；这些是 waveform diagnostics，不是 SFQ quantity。
- 13 ps / 12x320 grounded source 与 physical JSL 的 `DeltaI=I_grounded-I_physical`：max abs `8.45943e-05` A，RMS `2.31956e-05` A，signed area `518.423` uA·ps，最大差时间 `108.7` ps。
- scalar fit raw-origin：k=`0.542136`，normalized residual=`0.665945`，correlation=`0.723162`，peak shift=`-0.475` ps，status=`FAIL`；baseline-corrected status=`FAIL`。

## 3. Derived

- A/B 轨迹的 source、QB input、BJs、node2/BJL1、node3、BJL2、OUT 的 earliest divergence 使用预注册的 numerical floor 和连续两个采样点规则；同 sampling bin 记 TIE，不超过当前时间分辨率解释。详情见 `analysis/divergence-timeline.json`。
- source current 的正/负/带符号面积、centroid、first moment 和 difference-area 分解均使用 raw 实际 time 的梯形积分；它们描述 source waveform，不是量子数或事件数。
- `V(IN)`–`I(LIN|XBQ)` 是有记忆的 dynamic port trajectory；`Z_sec` 仅作为 **TWO-BOUNDARY DYNAMIC SECANT DIAGNOSTIC** 保存，并已 mask 小 denominator。它不是 Thévenin impedance、不是 small-signal impedance、不是 constant physical resistor。
- KCL residual 使用 netlist 端点方向：`I(LIN)=IN→1`、`I(BJs)=1→2`、`I(BJL1/RJ1)=2→0`、`I(L1)=2→3`、`I(RB)=IB→3`、`I(L2)=3→4`、`I(L0)=4→OUT`、`I(BJL2/RJ2)=4→0`。
- `analysis/independent-raw-recheck.json` 通过不复用主分析函数的 raw-only 路径复算 source peak/area、B/C DeltaI、scalar residual 和 QB KCL 子集；它是机械一致性检查，不是第二个科学权威。

## 4. Physics-based inference（有界）

- A→B：READ extension 的 causally allowed difference 只能在 105 ps 之后；若 source difference-area 主要集中在延长区，它支持“输入可用 duration/area 参与跨越 boundary”的 family-level inference，但不排除 trailing shape/timing。
- B→C：grounded source、physical JSL 和 QB `I(LIN)` 的差异支持整体 source/load closure 改变了 QB 所见 trajectory。若 pre-state 已不同，不能写成 READ 期间某一个 lobe 单独摧毁事件。
- H5 scalar attenuation 的结果只说明拟合是否足够；即使 correlation 较高，也不证明 attenuation 是 QB failure 的充分原因。
- 本报告不把 13 ps / 12x320 的 local BJL2 candidate 写成 JTL delivery，也不把 physical failure 归因为某一颗 BVM/JSL/QB 器件。

## 5. Competing hypotheses

| ID | status | 证据摘要 | 允许措辞 |
|---|---|---|---|
| H1 | `DISFAVORED` | {"pre_identity":true,"absolute_difference_area_uA_ps":416.5443002334625,"extension_105_110_share":0.48869290880893884,"strict_boundary_reference":"A SUBTHRESHOLD -> B CLEAN_ONE reference"} | bounded source-area/duration compatibility; not unique causation |
| H2 | `SUPPORTED` | {"outside_105_110_absolute_difference_share":0.5113070911910611,"decomposition_windows":["94_105ps","105_106ps","106_109ps","109_110ps","110_130ps"]} | only a shape/timing family statement if outside-extension signature is present |
| H3 | `UNRESOLVED` | {"timeline_12x320":[{"family":"source waveform","signal":"I(B_LD1)","time_ps":105.0125,"tie":true},{"family":"QB IN/Lin","signal":"I(I_REPLAY)","time_ps":105.0125,"tie":true},{"family":"BJs","signal":"P(BJS|XBQ)","time_ps":105.0125,"tie":true},{"family":"node2/BJL1","signal":"P(BJL1|XBQ)","time_ps":105.0125,"tie":true},{"family":"node3","signal":"I(L2|XBQ)","time_ps":105.0125,"tie":true},{"family":"BJL2","signal":"V(BJL2|XBQ)","time_ps":105.0125,"tie":true},{"family":"OUT","signal":"V(OUT)","time_ps":105.02499999999999,"tie":false}],"kcl_status":{"ideal_replay_13ps_12x320":"PASS","physical_13ps_12x320":"PASS"}} | mediator/compatibility evidence only; no independent intervention |
| H4 | `SUPPORTED` | {"delta_i_max_A":8.4594322e-05,"delta_i_rms_A":2.3195592255848504e-05,"pre_state_guard":"CHANGED","dynamic_input_difference_max_A":6.81454e-05} | overall dynamic source-load interaction is supported if report conditions pass |
| H5 | `DISFAVORED` | {"raw_origin":{"status":"FAIL","mode":"raw_origin","k":0.5421357301046518,"normalized_residual":0.6659450141958494,"correlation":0.7231616473844803,"signed_area_ratio":0.39941627322363354,"positive_area_ratio":0.554995968833263,"negative_area_ratio":4.275249242235859,"grounded_signed_area_As":8.631984286286892e-16,"physical_signed_area_As":3.4477549941536766e-16,"grounded_positive_area_As":8.992970861413087e-16,"physical_positive_area_As":4.99106257591926e-16,"grounded_negative_area_As":-3.609865751261952e-17,"physical_negative_area_As":-1.5433075817655837e-16,"timing_residual_ps":-9.36640214322631,"grounded_signed_centroid_ps":105.08884422306787,"physical_signed_centroid_ps":95.72244207984156,"grounded_positive_peak_time_ps":104.2375,"physical_positive_peak_time_ps":103.76249999999999,"peak_time_shift_ps":-0.4750000000000085,"max_residual":5.029477480711765e-05,"max_residual_time_ps":108.675,"polarity_preserved":true,"fit_checks":{"normalized_residual":false,"correlation":false,"positive_peak_time_shift":false,"polarity_preserved":true},"tolerances":{"normalized_residual_max":0.25,"correlation_min":0.9,"peak_time_shift_max_ps":0.05}},"baseline_corrected":{"status":"FAIL","mode":"baseline_corrected","k":0.542167657277274,"normalized_residual":0.6659267942124746,"correlation":0.7231616473844803,"signed_area_ratio":0.3994674182479163,"positive_area_ratio":0.5550346194067453,"negative_area_ratio":4.273662512033557,"grounded_signed_area_As":8.631495847202705e-16,"physical_signed_area_As":3.4480013616996757e-16,"grounded_positive_area_As":8.99259076972125e-16,"physical_positive_area_As":4.991199195352844e-16,"grounded_negative_area_As":-3.610949225185452e-17,"physical_negative_area_As":-1.5431978336531686e-16,"timing_residual_ps":-9.36484878643104,"grounded_signed_centroid_ps":105.08845348826199,"physical_signed_centroid_ps":95.72360470183095,"grounded_positive_peak_time_ps":104.2375,"physical_positive_peak_time_ps":103.76249999999999,"peak_time_shift_ps":-0.4750000000000085,"max_residual":5.0295740069726556e-05,"max_residual_time_ps":108.675,"polarity_preserved":true,"fit_checks":{"normalized_residual":false,"correlation":false,"positive_peak_time_shift":false,"polarity_preserved":true},"tolerances":{"normalized_residual_max":0.25,"correlation_min":0.9,"peak_time_shift_max_ps":0.05}}} | fit property only; attenuation is not a sufficient-cause proof |
| H6 | `SUPPORTED` | {"scalar_model_status":"DISFAVORED","raw_origin_normalized_residual":0.6659450141958494,"baseline_corrected_normalized_residual":0.6659267942124746} | bounded non-scalar waveform/load-line family, not unique device mechanism |
| H7 | `UNRESOLVED` | {"strict_reference_difference_turns":"1.016028923 - 0.973287067","source_and_internal_comparison":"recorded in qb-internal-comparison.csv"} | junction count and Ic/area are confounded; no primary attribution |

## 6. A → B：9 ps subthreshold 到 13 ps clean-one reference

A/B strict 数值不在本轮重新解释；这里只审计它们对应的 source 与 QB internal trajectory。A/B pre-105 identity、差分面积窗口和 earliest divergence 顺序见分析 CSV/JSON。

12x320 source `I(B_LD1)`：A peak/area=`7.90668e-05 A`/`516.362 uA·ps`；B peak/area=`7.90668e-05 A`/`863.198 uA·ps`。
12x320 causal timeline first family records：source waveform@105.013ps TIE; QB IN/Lin@105.013ps TIE; BJs@105.013ps TIE; node2/BJL1@105.013ps TIE; node3@105.013ps TIE; BJL2@105.013ps TIE; OUT@105.025ps。

## 7. B → C：ideal clean-one reference 到 physical subthreshold

B/C source-load difference 的 `DeltaI` 最大绝对值为 `8.45943e-05 A`，不是静态阻抗；pre-state guard=`CHANGED`。
physical 与 ideal replay 的 input/current trajectory、BJs/BJL1/BJL2 和 KCL closure 见 `analysis/qb-internal-comparison.csv` 及 `analysis/divergence-timeline.json`。

## 8. 12x320 vs 8x500

13 ps ideal 的 12x320/8x500 strict reference 分别为既有 `1.016...` 与 `0.973...` turns；本轮只比较 source、input、内部 phase/current partition。由于 JSL 数量和 JJ area/Ic 同时变化，H7 的“primarily”保持 UNRESOLVED，不能把接近一圈写成 candidate 或 margin。
source 侧 8x500→12x320 的 `I(B_LD1)` peak=`8.92835e-05`→`7.90668e-05` A，signed area=`688.317`→`863.198` uA·ps，effective duration=`31.15`→`32.1375` ps；`V(SL1)` peak=`0.00111101`→`0.00119352` V。完整 source-side、QB input、BJs/BJL1/BJL2/current-partition 对照见 `analysis/source-waveform-comparison.csv` 和 `analysis/qb-internal-comparison.csv`。

## 9. Dynamic load-line interpretation

`V(IN)` vs `I(LIN|XBQ)` 和 `V(SL1)` vs source/JSL current 以时间可追踪的 parametric HTML 图保存。它们展示 trajectory，不是静态 load line；`Z_sec` 的全部定义、mask 和限制写在 `analysis/dynamic-port-diagnostics.csv`。

## 10. What is still unknown

- H1 与 H2 的 duration/area 和 shape/timing 唯一分解；
- H3 具体哪一颗内部 JJ/哪条支路是 critical cause；当前只有 mediator evidence；
- B/C 差异来自 pre-state、READ-period reshaping，还是二者共同作用；
- 12x320 与 8x500 中 JSL 数量、Ic/area 各自贡献；
- scalar fit 对 QB failure 的充分性；
- Thévenin/small-signal impedance、论文 Fig.7 的器件映射、timestep robustness、无限时间稳定性、硬件行为、JTL/T1 接收和 system Gate。

## 11. Parameter recommendation gate

本轮不推荐具体参数或方向，也不启动 sweep。下一候选轮必须另行 preregister，并在至少 0.025/0.0125/0.00625 ps 下验证；当前 1.016 与 0.973 只能作为靠近一圈 boundary 的 mechanism reference，不能称 robust operating margin。

## Provenance and evidence boundary

全部 raw SHA-256 见 `analysis/raw-provenance.json`；strict reference 见 `test/exploration/bvm-load-qb-strict-event-reclassification-v1-20260901/analysis/strict-event-summary.csv`（SHA `f18f6809729a75ff5f6d32e457079e3dfb214a3515d9c377e03b2e910c850243`）。Sol XHigh read-only pre-review 见 `analysis/reviewer-notes.md`。

本任务完成后停止，不更新 HANDOVER/todo，不执行下一实验。
