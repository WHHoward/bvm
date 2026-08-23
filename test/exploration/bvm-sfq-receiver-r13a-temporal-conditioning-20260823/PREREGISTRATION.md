# R13-A：canonical-BVM temporal-conditioning requirement experiment

日期：2026-08-23
模式：`EXPLORATORY` / requirements experiment
基线：R12-A commit `ebe24984771255f002499ec9bef35e9953c87d28`

## Scientific question

在不修改 `DCSFQ_BVM.cir` 内部参数、不增加 amplitude gain 的条件下，canonical
BVM read1 的实际输入为什么不能把 B3 推入 R12 Phase-A 已观察到的约一圈
regenerative regime：

1. opposite-polarity cancellation；
2. useful dwell 不足；
3. 两者共同；
4. temporal conditioning 不够，仍需 active/regenerative gain。

本轮只建立 frozen-regenerator 对理想输入变换的 requirements evidence，不把
任何 conditioning PASS 称为完整 BVM→SFQ receiver。

## Frozen source and topology

- 输入直接取 R12 Phase-B raw 的 `I(L1|XCONV)`。`DCSFQ_BVM.cir` 中
  `L1 a 1 1.672p`，JoSIM branch-current 正方向为 `a→node1`；该方向与
  Phase-A `I_IN 0 IN1` 的正 bump 一致。
- Phase-A 300 µA 正 bump 的 B3 transition 方向为正向 `+1.03011 turn`，
  因此 positive `I(L1)` 定义为 favorable polarity。
- replay fixture 只包含原样 `THmitll_DCSFQ_BVM a q` 和 `R_LOAD=10 Ω`；
  不接 BVM、JTL、transformer 或额外 matching 元件。
- replay 使用 R12 的 `dt=0.0125 ps`、stop `170 ps`，PWL 逐样本重放实际
  `I(L1)`，并在 `170 ps` 保持最后一个采样值至停止点。该 surrogate 是
  behavioral current-source replay，不声称复制 direct SL 的源阻抗。

## Matched cases

每个 raw replay 和 C1/C2/C3 都使用四个完全匹配的 source waveforms：

- `read1`：logical1 + canonical READ；
- `read0`：logical0 + canonical READ；
- `logical1-read0-control`；
- `logical0-read0-control`。

控制波形也经过同一算法；不为 read1 注入特殊幅值。

## Registered transforms

令 `i(t)=I(L1|XCONV)`，`f(t)=max(i(t),0)` 为 favorable component，
`r(t)=min(i(t),0)` 为 opposite component。所有 `i` 保持原始安培尺度，
不乘任何 gain。transform 只在 `[94,130) ps` activity window 内寻找峰值；
controls 也使用各自 raw waveform 的同一规则。

### Raw replay

`I_REPLAY= i(t)`。这是 waveform-surrogate validity test，预期定性复现
R12：read1 > read0 >> controls，B3 sub-turn，post bounded。

### C1 — polarity-selective rectification

`I_C1(t)=f(t)`。保留 positive favorable lobe 的实际 timing/amplitude，
将 negative/opposite component 置零；不延长、不放大。

### C2 — amplitude-preserving 20 ps hold/stretch

设 `Ipk=max(f)`，`tpk` 为 activity window 内第一次达到 `Ipk` 的时间，
`H(t)=Ipk` for `t∈[tpk,tpk+20 ps)`，否则为零。C2 为 hold-only diagnostic：

```text
I_C2(t) = r(t) + H(t)       during hold window
           i(t)             outside hold window
```

因此 favorable component 被延长到 20 ps，而 original opposite component
仍然保留；positive component 不超过原始 `Ipk`。20 ps 只采用 R2-F 的历史
有效-dwell diagnostic point，不是 universal requirement。

### C3 — rectification + 20 ps hold

```text
I_C3(t) = H(t)       during hold window
           f(t)       outside hold window
```

它在同一 20 ps hold 下去除 opposite component；不增加 peak。C2/C3 的
duration、峰值规则和 source case 完全相同。

## Required measurements and event evidence

每个 run 直接 probe `P/V/I(B1|XDCSFQ)`、`B2`、`B3`、`I(L1..L6)`、`q` 和
`R_LOAD`。分析记录：

- continuous/unwrapped phase；
- largest monotonic segment、onset/end；
- 同 JJ、同端点、同方向、同段 `∫Vdt/Φ0`；
- current waveform、q waveform、post p2p/retrap。

完整 local event 只能由 continuous ≥1-turn monotonic phase、同段电压面积一致、
以及 event 后 bounded/retrap 联合支持。`I>Ic`、voltage peak 或 phase range
单独不能定义 event。

如果某个 read1 conditioning case 产生合格 B3 event，才追加同一冻结输入的
two-cell standard-JTL transport check；没有 B3 local event 则不接 JTL。

## Classification and stop rules

- `DWELL_LIMITED`：C2 或 C3 selective exactly-one，raw/C1 fail；
- `POLARITY_CANCELLATION_LIMITED`：C1 selective exactly-one；
- `RECTIFY_AND_HOLD_REQUIRED`：只有 C3 selective exactly-one；
- `TEMPORAL_CONDITIONING_INSUFFICIENT`：C1/C2/C3 全部 sub-turn；
- `NONSELECTIVE_CONDITIONING`：read0 或 controls 有完整 event；
- `MULTIPULSE_CONDITIONING`：read1 超过一个 complete event。

不 sweep amplitude/duration，不改 canonical BVM 或 DCSFQ_BVM，不恢复旧
45–55 µA 假设，不设计 DFF/NDRO，不接 T1。该单点 batch 不提供物理
conditioner implementation，也不升级 Candidate。
