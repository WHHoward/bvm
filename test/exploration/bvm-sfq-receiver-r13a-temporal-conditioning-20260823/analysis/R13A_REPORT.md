# R13-A temporal-conditioning requirement report

日期：2026-08-23

基线：R12-A `ebe24984771255f002499ec9bef35e9953c87d28`

实验目录：`test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/`

## Verdict

`TEMPORAL_CONDITIONING_INSUFFICIENT`

R12 的实际 read1 输入做 raw replay、单独正极性整流（C1）、20 ps
amplitude-preserving hold（C2）以及整流+20 ps hold（C3）后，四个 matched
case 中都没有 B3 的 qualifying complete event。每个 read1 最大单调段都只有
约 `0.0236--0.0245 turn`；read0 和两个 READ=0 control 也没有完整 event。

因此本轮只证明：在当前 frozen DCSFQ_BVM、当前实际输入幅度以及这个诊断性
20 ps dwell 下，理想的 polarity/dwell conditioning 仍不足以触发 B3。它不证明
所有物理 conditioner 都失败，也不把 20 ps 当作 universal requirement。

没有接 standard JTL：没有任何 read1 B3 event 满足进入下一 gate 的条件。

## 1. 输入提取和极性

输入列是 R12 Phase-B raw 的 `I(L1|XCONV)`。`DCSFQ_BVM.cir` 中
`L1 a 1 1.672p`，该 branch current 的方向是 `a -> node1`。R12 Phase-A
300 µA 正向 controlled bump 产生约 `+1.03011 turn` 的 B3 regenerative
local response，因此本轮将正的 `I(L1)` 定义为 favorable polarity。

固定 activity window 为 `[94,130) ps`。从实际 raw 提取的输入量为：

| case | peak + (µA) | peak − (µA) | signed area (µA·ps) | absolute area (µA·ps) | favorable positive area (µA·ps) | opposite negative area (µA·ps) |
|---|---:|---:|---:|---:|---:|---:|
| read1 | 110.200 | −44.274 | 517.106 | 697.965 | 607.536 | −90.430 |
| read0 | 29.777 | −32.544 | 0.006 | 142.278 | 71.142 | −71.136 |
| logical1 READ=0 | 0.000778 | −0.000955 | −0.000227 | 0.010201 | 0.004987 | −0.005214 |
| logical0 READ=0 | 0.000959 | −0.000781 | 0.000227 | 0.010234 | 0.005231 | −0.005003 |

read1 的 read1-specific positive running-derived tail 在描述性 marker 下从
约 `97.2125 ps` 延续到 `116.05 ps`；10 µA 只是 envelope marker，不是
event 或 transform threshold。read0 的正负面积近似抵消，而 read1 保留明显
正向净驱动。

## 2. Replay validity

replay 只包含原样 `THmitll_DCSFQ_BVM`、10 Ω `R_LOAD` 和由 raw 样本构成的
current PWL；不包含 canonical BVM 或 JTL。四个 replay 均为 13,600 行，
`dt=0.0125 ps`，stop=`170 ps`。

raw replay 的 B3 结果满足 surrogate 的定性检查：read1 明显高于 read0，
read0 高于两个近零 control；read1 仍为 sub-turn，post window 有界。

| case | B3 activity range (turn) | largest monotonic segment (turn) | same-segment V-area (turn) | area residual (turn) | post phase p2p (turn) |
|---|---:|---:|---:|---:|---:|
| read1 | 0.0332590 | −0.0308173 | −0.0308267 | −9.33e−6 | 9.46e−4 |
| read0 | 0.0097646 | 0.0083671 | 0.0083691 | 2.05e−6 | 2.44e−4 |
| logical1 READ=0 | 4.14e−7 | 4.14e−7 | 4.00e−7 | −1.36e−8 | 6.37e−8 |
| logical0 READ=0 | 4.14e−7 | −4.14e−7 | −3.99e−7 | 1.47e−8 | 6.37e−8 |

这证明 current-source replay 在定性层面是有效 surrogate；它不证明 replay
保留了 direct SL 的源阻抗或 back-action。

## 3. C1/C2/C3 B3 evidence

下表的 segment 和 voltage area 来自同一个 B3、同一个时间段、同一个方向；
它们的接近只说明 phase/V 积分一致，不能单独把 sub-turn activity 称为 event。

| transform | case | activity range (turn) | largest segment (turn) | same-segment V-area (turn) | residual (turn) | post p2p (turn) |
|---|---|---:|---:|---:|---:|---:|
| C1 rectification | read1 | 0.0266792 | 0.0236159 | 0.0236209 | 4.94e−6 | 5.36e−4 |
| C1 rectification | read0 | 0.0061637 | −0.0061637 | −0.0061650 | −1.32e−6 | 1.22e−4 |
| C2 20 ps hold | read1 | 0.0264141 | 0.0244917 | 0.0244969 | 5.20e−6 | 3.52e−3 |
| C2 20 ps hold | read0 | 0.0083136 | 0.0079293 | 0.0079311 | 1.88e−6 | 3.40e−4 |
| C3 rectify+hold | read1 | 0.0241426 | 0.0236159 | 0.0236209 | 4.94e−6 | 3.65e−3 |
| C3 rectify+hold | read0 | 0.0060474 | −0.0052413 | −0.0052422 | −8.66e−7 | 2.42e−4 |

两个 READ=0 controls 在 C1/C2/C3 的 B3 最大段均约 `2e−7--4e−7 turn`，
没有完整 transition，也没有 free-running。C2/C3 的 read1 post p2p 比
raw 稍大，但仍远小于一圈；post window 只有 bounded residual activity，
并非 event 后第二次运行。

read1 的 B3 current activity range（µA）也只显示有限扰动，而不是 event
判据：

| transform | read1 B3 current min..max (µA) | read0 B3 current min..max (µA) | read1 `V(Q_REPLAY)` min..max (µV) |
|---|---:|---:|---:|
| raw replay | 146.496..201.010 | 165.568..178.903 | −52.803..50.470 |
| C1 | 153.661..198.034 | 169.344..177.447 | −38.757..42.147 |
| C2 | 155.996..201.536 | 166.963..182.112 | −39.743..43.661 |
| C3 | 155.548..200.125 | 167.813..179.371 | −38.898..42.147 |

`V(Q_REPLAY)` 和 10 Ω load current 均已直接保存；例如 C3 read1 的
`V(Q_REPLAY)` activity peak 约 `+42.15/−38.90 µV`，两个 controls 仅约
`±0.0000004 µV` 量级。电压峰值没有被用作 switching 判据。

## 4. B1/B2/B3 phase routing

read1 的最大单调 segment（turn；随后为同段 V-area）为：

| transform | B1 | B2 | B3 |
|---|---:|---:|---:|
| raw replay | −0.110431 / −0.110467 | −0.111670 / −0.111714 | −0.030817 / −0.030827 |
| C1 | −0.098699 / −0.098732 | −0.097649 / −0.097695 | 0.023616 / 0.023621 |
| C2 | −0.098263 / −0.098281 | −0.079723 / −0.079741 | 0.024492 / 0.024497 |
| C3 | −0.103073 / −0.103092 | −0.084912 / −0.084932 | 0.023616 / 0.023621 |

front stages 的 read1 nonlinear activity 确实可见，但 B3 没有从约百分之几
turn 跃迁到 `>=1 turn`。所有阶段的 same-JJ phase/area residual 都很小，
所以本轮的 negative result 不是由 phase/voltage area 不一致造成的。

## 5. Observed / Derived / Inference / Unknown

### Observed

- R12 `I(L1|XCONV)` 的正向 read1 amplitude、净面积和中段 running tail
  明显高于 read0。
- raw replay、C1、C2、C3 均产生 read1-selective 的 B1/B2/B3 sub-turn activity。
- 所有 read1 B3 最大 monotonic segment 小于 `0.025 turn`；read0/control
  没有完整 B3 transition。
- B3 同段 voltage area 与 phase segment 一致；post windows 没有完整第二段
  或 free-running。

### Derived

- C1 去除 opposite-polarity component 后，B3 read1 仍只有约 `0.0236 turn`。
- C2 在不提高 peak 的前提下增加 20 ps favorable hold 后，B3 read1 仍只有
  `0.0245 turn`。
- C3 同时整流和 hold 后，B3 read1 仍只有约 `0.0236 turn`。
- 因而在这组 frozen converter 和 single diagnostic dwell 下，三种理想
  temporal transform 都不能提供完整 B3 event。

### Inference

- cancellation 和 useful dwell 可能影响波形，但在本轮幅度不变的条件下，
  去除 cancellation、延长 dwell，或两者同时使用，都不足以跨入已知的
  regenerative regime。
- 当前 evidence 更支持“仍缺少 active/regenerative gain 或等价的物理
  energy transfer”这一 requirements inference，而不是单纯把问题归因于
  polarity 或 dwell。

### Unknown

- 还没有证明哪一种物理 rectifier/hold topology 能无失真地产生 C1/C2/C3
  变换。
- 还没有测量实际物理 conditioner 的源阻抗、back-action、噪声和 rearm。
- 20 ps 只来自 R2-F 的历史 bounded diagnostic point；duration window 尚未
  被 sweep 或冻结为 receiver hard specification。
- replay 没有证明 canonical BVM 在接入未来 conditioner 后仍保持 source/storage
  guards。

## 6. Architecture consequence

本轮关闭的是“仅靠理想 polarity/dwell temporal conditioning 就足够”的
requirements hypothesis，不是所有 temporal conditioner family。下一阶段若
继续，应是一个最小、可隔离验证的 physical temporal conditioner，并显式包含
active/regenerative gain 或等价的能量保持机制；先验证它能否把实际 BVM
transient 推入 frozen regenerator，再讨论 downstream JTL。此建议不构成
implementation，也不升级 Candidate。

## 7. Provenance

- JoSIM: `build/josim-cli` v2.7.2837d13，SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`。
- `jjmit.cir`: `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`。
- `DCSFQ_BVM.cir`: `398e9c656f4e6e7b8a866800f019cc8fef3def30da8d508322bb89183d144d95`。
- R12 source raw hashes和所有 R13 raw/output hashes见 `sha256sums.txt`。
- 输入、命令、logs、raw CSV、分析脚本和结构化 metrics 均保存在本目录。
