# N3/N4 replay deep dive

范围：已有 `N1_REPLAY` 作为 first-response source reference，主分析为 `N3_REPLAY`/`N4_REPLAY`；`FINAL_READ_RESPONSE=[110,200) ps`。本轮未新增 JoSIM solve，未改变 circuit、parameter、timing 或 raw。

证据标签：`OBSERVED`=raw 直接观测；`DERIVED`=按实际 time 列独立重算；`BOUNDED_RESULT`=声明窗口内的有界比较；`UNKNOWN`=raw 不能可靠分离。连续 Cphi/Cv 不是 SFQ event count。

## 1. N3/N4 前三个 response 的 QB→JTL→termination 时间链

`OBSERVED/DERIVED`：时间来自直接电压峰和 `I(R_TERM)>5 uA` 描述性峰值探针；BJS 不做强行分配。

| case | response | descriptive chain |
|---|---:|---|
| N3_REPLAY | 1 | BJ1 113.4 ps; BJ2 115.2 ps; QBOUT 115.4 ps; JTL1 116.4 ps; JTL6 131.2 ps; R_TERM 132.8 ps; BJS UNKNOWN |
| N3_REPLAY | 2 | BJ1 117.8 ps; BJ2 119.6 ps; QBOUT 119.7 ps; JTL1 120.8 ps; JTL6 136.8 ps; R_TERM 138.4 ps; BJS UNKNOWN |
| N3_REPLAY | 3 | BJ1 122.3 ps; BJ2 125.4 ps; QBOUT 125.9 ps; JTL1 126.6 ps; JTL6 142.6 ps; R_TERM 144.2 ps; BJS UNKNOWN |
| N4_REPLAY | 1 | BJ1 113.0 ps; BJ2 114.5 ps; QBOUT 114.7 ps; JTL1 115.8 ps; JTL6 130.5 ps; R_TERM 132.1 ps; BJS UNKNOWN |
| N4_REPLAY | 2 | BJ1 116.1 ps; BJ2 118.3 ps; QBOUT 118.4 ps; JTL1 119.5 ps; JTL6 135.4 ps; R_TERM 137.0 ps; BJS UNKNOWN |
| N4_REPLAY | 3 | BJ1 120.0 ps; BJ2 121.4 ps; QBOUT 121.9 ps; JTL1 123.3 ps; JTL6 140.1 ps; R_TERM 141.6 ps; BJS UNKNOWN |

这些是联合 raw 轨迹中的描述性位置，不是离散事件计数；完整累计相位/同 JJ `Cv` 见 [N3 cumulative](plots/deep_dive/N3_REPLAY_CUMULATIVE.html)、[N4 cumulative](plots/deep_dive/N4_REPLAY_CUMULATIVE.html) 和 [N3 vs N4 cumulative](plots/deep_dive/N3_VS_N4_CUMULATIVE.html)。

## 2. N4 第三个 response 后是否仍有 source drive

`OBSERVED/BOUNDED_RESULT`：`t3=141.6 ps`。在 `[t3,200) ps`，`I(I_REPLAY)` signed area=-2.126 uA·ps，positive area=29.510 uA·ps，negative area=-31.636 uA·ps，positive peak=8.144 uA，sample RMS=1.919 uA；按 5 uA 描述性阈值的正向样本跨度为 6.5 ps。
相对于 N1 first-response reference `[110,138.8) ps` 的 positive area=529.909 uA·ps、peak=68.414 uA，N4 residual/N1-first 比值分别为 area=0.0557、peak=0.1190。因此可报告为：第三次 response 后仍有短时、振荡的正向 residual drive，但没有一份 N1-class 的独立 fourth-drive 规模；area 不是 SFQ count。

## 3. 最早观察到的第四 response 缺失位置

`BOUNDED_RESULT/UNKNOWN`：在 `144.6–200 ps` 的第四候选探针中，未观察到可分离的第四个 QBIN excursion、BJ1/BJ2 progression、QBOUT pulse-like candidate、JTL1/JTL6 或 R_TERM downstream candidate；BJS 仍可见振铃样残余，但不能标成第四次 nonlinear response。因此 earliest observed missing-response location 只能写成 **QB front-end / BJS→BJ1 progression boundary**，BJS 与 BJ1 的精确边界为 `UNKNOWN`，不是 root-cause 结论。

## 4. response spacing 与 unrecovered-state evidence

`OBSERVED`：
- N3_REPLAY: terminal Δt12/Δt23 = 5.6/5.8 ps; BJ1 = 4.4/4.5 ps; BJ2 = 4.4/5.8 ps.
- N4_REPLAY: terminal Δt12/Δt23 = 4.9/4.6 ps; BJ1 = 3.1/3.9 ps; BJ2 = 3.8/3.1 ps.

`DERIVED/BOUNDED_RESULT`：
- N3_REPLAY: fixed-offset BJ1 Cphi range 0.02809 turns; BJ2 Cphi range 0.00505 turns.
- N4_REPLAY: fixed-offset BJ1 Cphi range 0.02450 turns; BJ2 Cphi range 0.00833 turns.

N4 的前三次 spacing 比 N3 更短；固定 offset 的 BJ1/BJ2 Cphi plateau 没有给出随 response 单调扩大的偏离证据，电流/电压状态仍有差异但不足以单独判定 dead time 或 physical recovery mechanism。

## 5. 当前 bottleneck classification

`BOUNDED_RESULT`：最符合的是 **D. EFFECTIVE_STIMULUS_LIMIT**；由于 BJS 残余活动与 BJ1 的精确缺失边界不可唯一定位，同时保留 **F. MIXED_OR_UNRESOLVED**。这表示声明窗口内的 raw 拟合分类，不是 saturation、recovery、bias 的已证实机制，也不是硬件结论。

产物入口：
- [N3 QB internal](plots/deep_dive/N3_REPLAY_QB_INTERNAL.html)；[N4 QB internal](plots/deep_dive/N4_REPLAY_QB_INTERNAL.html)
- [EVENT1](plots/deep_dive/EVENT1_N3_VS_N4.html)；[EVENT2](plots/deep_dive/EVENT2_N3_VS_N4.html)；[EVENT3](plots/deep_dive/EVENT3_N3_VS_N4.html)；[POST EVENT3](plots/deep_dive/POST_EVENT3_N3_VS_N4.html)
- machine-readable: `analysis/n3_n4_event_timeline.json`、`analysis/n4_post_third_response.json`、`analysis/n3_n4_recovery_compare.json`；raw/hash QA: `analysis/n3_n4_raw_qa.json`；visual QA: `analysis/deep_dive_viz_qa.json`。

raw QA status: `PASS`, raw hashes before/after unchanged=`True`。
