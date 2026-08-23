# QB-Q2A — source-decoupled waveform replay diagnosis

## 研究问题

在不改变 QB-Q0 scaled cell 的任何参数、也不整形输入波形的前提下，区分：

1. canonical BVM read1 waveform 本身是否足以驱动 frozen scaled QB；
2. QB-Q1 direct galvanic failure 中有多少来自 source impedance / back-action。

这是 requirements/counterfactual replay Exploration，不是物理硬件接口证据，也不证明一个实际 conditioner 已经存在。

## Frozen QB

完全沿用 QB-Q0/QB-Q1 scaled cell：

```text
BJs AREA=.50     BJL1 AREA=.36     BJL2 AREA=.54
Lin=.8 pH        L0=1.323 pH       L1=L2=3.91 pH
RJ1=33 Ω         RJ2=22 Ω          RB=6 Ω
IBIAS=35 µA      R_LOAD=10 Ω
```

实际 `jjmit.cir` 和 `bq_cell.cir` 快照保存在 `inputs/`；不连接 BVM、DCSFQ、transformer、JTL 或 T1。

## Replay input definitions

四个 case 使用一个相同的 standalone `XBQ IN OUT IBIAS BQ` topology：

| case | input source | provenance | purpose |
|---|---|---|---|
| A | ideal current `I_IN 0 IN pulse(0 68.4u 10p 1p 1p 5p 50p)` | QB-Q0 scaled positive point | positive control；应复现 Q0 的 exactly-one local BJL2 window |
| B | ideal voltage replay of Q1 loaded `V(SL1)` | QB-Q1 `logical1-read` raw | 保留 direct-failure 的实际 loaded waveform shape/amplitude，同时移除再次加载 source 的反馈 |
| C | ideal voltage replay of canonical no-receiver logical1 `V(SL1)` | accepted canonical no-receiver raw | source-isolated logical1 counterfactual |
| C0 | ideal voltage replay of canonical no-receiver logical0 `V(SL1)` | accepted canonical no-receiver raw | source-isolated logical0 counterfactual |

B/C/C0 的 replay voltage 使用 raw CSV 的全部时间点和原始极性，不 rectify、hold、normalize、rescale 或重新采样。原始 Q1 `I(Lin|XBQ)` 与 canonical `I(L_SL|XBVM1)` 另存为 input provenance，不能与 replay voltage 数值直接互换。

## Timings

- A 复用 QB-Q0 historical periodic fixture：`.tran 0.1p 300p`，六个 pulse starts 为 10/60/110/160/210/260 ps；它是 positive-control regression，不是 canonical BVM single-read proof。
- B/C/C0 复用 source CSV 的 `0…169.9875 ps` 时间轴和 nominal `.tran 0.0125p 170p`；每个 raw source 共同保留 `1.8375→1.8625 ps` 的 `0.025 ps` 输出间隔。
- B/C/C0 的 read activity window 为 `[94,130) ps`，post window 为 `[150,170] ps`；A 使用 Q0 每 pulse 的 `[s,s+25) ps` activity 与 post windows。

## Measurement contract

直接保存 `P/V/I`：`BJs`、`BJL1`、`BJL2`；另保存 `Lin/L0/L1/L2/RB/RJ1/RJ2`、input source current、`V(IN)`、`V(OUT)`、`I(R_LOAD)` 和 `IBIAS` branch。

每个候选 event 必须同时满足：

- 同一 JJ raw unwrapped phase 的连续 monotonic segment `|Δphase|≥1 turn`；
- 同一 JJ、同一方向、同一时间端点的直接 voltage area `∫Vdt/Φ0` 与 phase 一致；
- post window bounded/retrap，无第二个完整 event 或 free-running。

不得使用 voltage peak、`I>Ic`、phase activity range 或旧 `fast_events` 单独判 event。

## 判定预注册

- A positive control 不能复现 Q0 的 bounded exactly-one BJL2 local behavior：`REPLAY_FIXTURE_INVALID`，停止，不解释 B/C。
- C read1 有 exactly-one BJL2 local event 且 C0 为零：`SOURCE_ISOLATION_PRIMARY_LIMIT`。
- C read1 仍 subthreshold：`QB_DYNAMIC_WINDOW_MISMATCH`；不能把该 bounded result 写成 QB family 普遍不可能。
- B/C 结果不一致时，报告 B 的 loaded-waveform replay 与 C 的 canonical source-isolated replay差异，不自动设计接口或 sweep。
- 任一 replay 出现 read0-like nonselectivity、multiple event、free-running 或 phase/area 不一致，保留对应 bounded failure/`INCONCLUSIVE`，停止追加实验。

## Stop boundary

只运行 A/B/C/C0 一次；不改变 QB AREA、bias、L、R、load，不 sweep，不接 transformer/buffer/JTL/T1。结果只回答 requirements-level waveform sufficiency 与 source-decoupling diagnosis。
