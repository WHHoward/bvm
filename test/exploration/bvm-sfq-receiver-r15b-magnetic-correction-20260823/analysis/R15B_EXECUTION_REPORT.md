# R15-B split-winding single-point execution report

日期：2026-08-23
父 analytic checkpoint：`83ff0f2cba1dbf0dbf3e1ae63d80a32a66606372`
实验模式：Exploration；单一冻结点；四 matched cases

## Verdict

主 verdict：**`ACTIVE_STAGE_NO_TRIGGER`**

R15-B 的 split-winding/two-core 磁性拓扑可以在 `logical1 + READ` 中保留
`B_DET` 的强 nonlinear detector response，但 `B_DET → J_SET/J_Q/J_OUT`
没有形成 read1-selective 的 active state-compression sequence。后端
`DCSFQ_BVM` 看到的 `I(L1)` 只有约 `0.511 µA` 的峰值，而且四个 case
基本相同；没有 active gain，也没有 B3 local event。

附加 source disposition：**`BOUNDED_EXTRA_BACK_ACTION_NOT_ISOLATED`**。
READ=0 control 稳定、没有 free-running，JM1/JM2 的 logical sign 保持，
但 read1 后的 SL/N6 和 JS1/JS2 ringing 明显高于 no-receiver baseline。
因此不能把本点称为 source-isolated success；这个 bounded disturbance 没有
被升级为主 verdict `BACK_ACTION_FAILURE`，因为没有观察到 control running、
storage sign collapse 或未收敛的 post state。

没有接 JTL/T1，没有修改 canonical BVM、`DCSFQ_BVM.cir` 或任何 frozen
参数，也没有 sweep。

## 1. Artifact and solver validity

四个 CSV 均有 `13,599` 行，时间范围 `0–169.9875 ps`，中位步长
`0.0125 ps`，时间严格递增且数值有限。四次 JoSIM exit code 均为 `0`。

使用的 solver：`build/josim-cli` `v2.7.2837d13`，binary SHA-256：

```text
48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2
```

原始输入、命令日志、CSV 和结构化指标保存在本目录；分析脚本是
`analysis/analyze_r15b_execution.py`，结果是
`analysis/r15b-execution-metrics.json` 和 `analysis/r15b-case-summary.csv`。

## 2. First control gate

首先运行 `logical1 + READ=0`。在 `94–130 ps` 中：

| junction | largest monotonic phase segment | same-JJ voltage area | result |
|---|---:|---:|---|
| B_DET | `−0.0000841 turn` | `−0.0000841 turn` | no event |
| B_SET | `+0.0018509 turn` | `+0.0018512 turn` | no event |
| B_Q | `−0.00001138 turn` | `−0.00001138 turn` | no event |
| B_OUT | `+0.0006132 turn` | `+0.0006132 turn` | no event |
| DCSFQ B3 | `−0.00005774 turn` | `−0.00005773 turn` | no event |

所有 phase/area 都是同一 JJ、同一 segment 的配对结果；没有任何 segment
达到一圈。`150–170 ps` 仍无 complete segment，且 SL/N6、JS/JM ringing
衰减。因此 control 没有命中 `FREE_RUNNING` 或 `NONSELECTIVE_TRIGGER`，
按 preregistration 继续其余三个 case。

## 3. Detector evidence

下表的 segment 和 voltage area 均来自同一 junction、同一连续 monotonic
segment、同一时间端点。read1 的 `B_DET` segment 是局部 detector evidence，
不是 downstream SFQ delivery。

| case | B_DET activity range | largest monotonic segment | same-JJ V-area | residual | segment window |
|---|---:|---:|---:|---:|---|
| logical1 + READ | `4.309386 turn` | `+3.913019 turn` | `+3.913047 turn` | `2.73e−5 turn` | `102.9375–110.7000 ps` |
| logical0 + READ | `0.189157 turn` | `+0.184906 turn` | `+0.184929 turn` | `2.33e−5 turn` | `106.5875–108.2125 ps` |
| logical1 + READ=0 | `8.41e−5 turn` | `−8.41e−5 turn` | `−8.41e−5 turn` | `−1.01e−8 turn` | `94.8250–96.3625 ps` |
| logical0 + READ=0 | `2.55e−4 turn` | `+2.55e−4 turn` | `+2.55e−4 turn` | `4.53e−8 turn` | `94.0375–95.5750 ps` |

`B_DET` 的 read1/read0 separation 与 R0b 类似地保留：read1 有多圈
continuous activity，read0 只有约 `0.185 turn`，两个 control 没有完整
transition。B_DET activity-window voltage/current 也保持 state-dependent：

| case | `I(B_DET)` min..max | `V(B_DET)` min..max |
|---|---:|---:|
| logical1 + READ | `−29.360..+69.231 µA` | `−1050.452..+1971.729 µV` |
| logical0 + READ | `−7.178..+32.100 µA` | `−290.432..+382.786 µV` |
| logical1 + READ=0 | `14.99958..15.00034 µA` | `−0.179..+0.197 µV` |
| logical0 + READ=0 | `14.99940..15.00059 µA` | `−0.508..+0.541 µV` |

## 4. Settled operating point

`80–90 ps` 是 READ 前 settled window。以下以 `logical1 + READ` 的 median
为代表；四个 case 的 receiver DC operating point相同到记录精度。

| element/branch | settled phase or current |
|---|---:|
| B_DET phase | `0.3046785 rad`; `I(B_DET)=15.00009 µA` |
| B_SET phase | `0.7763639 rad`; `I(B_SET)=5.60000 µA` |
| B_Q phase | `0.1123729 rad`; `I(B_Q)=5.60682 µA` |
| B_OUT phase | `1.1523295 rad`; `I(B_OUT)=274.1148 µA` |
| DCSFQ B1/B2/B3 current | `−41.6715 / +60.6310 / +172.7026 µA` |
| `I(L1)` | `+0.841032 µA` |
| `I(L_S)` / `I(L_Q)` | `5.60000 / 5.60682 µA` |
| `I(L_FQ)` / `I(L_FO)` | `0.0212794 / 0.0212794 µA` |
| `I(L_CTL)` | `274.159 µA` |
| `I(R_F)` / `I(R_Q)` | `−0.0212794 / −0.0068237 µA` |
| `I(R_SRC)` / `I(I_OUT)` | `0.841032 / 275.000 µA` |

按实际 `jjmit` model，B_DET AREA `.50` 为 `Ic=50 µA`，B_SET AREA `.08`
为 `Ic=8 µA`，B_Q AREA `.50` 为 `Ic=50 µA`，B_OUT AREA `3.0` 为
`Ic=300 µA`。J_OUT 的 bias 约为 `275/300=0.9167 Ic`；这只是 operating
point 风险指标，不是 switching 判据。

## 5. Active-stage result

### J_SET/J_Q/J_OUT

| case | B_SET largest segment | B_Q largest segment | B_OUT largest segment |
|---|---:|---:|---:|
| logical1 + READ | `+0.00185094` | `−0.00001138` | `+0.00061322` |
| logical0 + READ | `+0.00185094` | `−0.00001138` | `+0.00061322` |
| logical1 + READ=0 | `+0.00185094` | `−0.00001138` | `+0.00061322` |
| logical0 + READ=0 | `+0.00185094` | `−0.00001138` | `+0.00061322` |

这些小 segment 主要是共同 startup/settling trajectory；它们在四个 case
完全相同，不是 read1-selective active sequence。没有任何 J_SET、J_Q 或
J_OUT segment 达到一圈，因此 Stage 2 `ACTIVE_STATE_COMPRESSION` 不成立。

### DCSFQ input and steering

冻结后端的 `I(L1|XDCS)` 在四个 case 中也相同：

| case | min..max `I(L1)` | signed area | positive area | favorable positive span |
|---|---:|---:|---:|---:|
| logical1 + READ | `+0.069940..+0.510835 µA` | `+7.97993 µA·ps` | `+7.97993 µA·ps` | `35.9875 ps` |
| logical0 + READ | `+0.069940..+0.510835 µA` | `+7.97993 µA·ps` | `+7.97993 µA·ps` | `35.9875 ps` |
| logical1 + READ=0 | `+0.069940..+0.510835 µA` | `+7.97993 µA·ps` | `+7.97993 µA·ps` | `35.9875 ps` |
| logical0 + READ=0 | `+0.069940..+0.510835 µA` | `+7.97993 µA·ps` | `+7.97993 µA·ps` | `35.9875 ps` |

这里没有负向 lobe；表中的 min/max 被保留为实际 waveform 范围，不能把
`+0.510835 µA` 解读成有效 read1 drive。`V(DCS_A)` 的 activity-window
范围同样为约 `−126.903..−17.341 µV`，四 case相同。source steering
branch 的 activity-window peak 为：

| branch | min..max |
|---|---:|
| `I(L_INJ)=I(R_SRC)` | `+0.06994..+0.51084 µA` |
| `I(L_FQ)=I(L_FO)` | `+0.001761..+0.012899 µA` |
| `I(L_CTL)` | `274.489..274.930 µA` |

因此 J_OUT 的 `275 µA` bias 没有被 read1 detector state 转换成有效的
DCSFQ input pulse；output current steering 仍是静态 bias path。

与已知尺度并列：

| reference | current | meaning |
|---|---:|---|
| R1a passive secondary | `5.564 µA` | passive extraction scale |
| R12 controlled | `68.4 µA` | frozen DCSFQ 中无完整 B3 event |
| R13 actual canonical replay | `110.2 µA` | frozen DCSFQ 中仍 sub-threshold |
| R12 controlled | `300 µA` | bounded约 `1.03-turn` B3 local positive reference |
| R15-B actual `I(L1)` | `0.511 µA` peak | 本轮没有 active gain |

所以 Stage 3 `ACTIVE_GAIN_ESTABLISHED` 不成立；本点甚至没有超过 R1a 的
passive current scale。

## 6. DCSFQ B3 event check

四个 case 的 B3 最大 monotonic segment均为 `−0.00005774 turn`，同段
voltage area为 `−0.00005773 turn`，残差约 `8.80e−9 turn`。phase/area
一致只说明这是一个很小的连续响应，不能称作 event。没有 `>=1 turn`，没有
retrap-after-event 或 exactly-one evidence；Stage 4 不成立。

## 7. BVM source/storage guard

与 accepted canonical no-receiver raw 做同窗口比较：

| quantity, read1 post `[150,170) ps` | R15-B | canonical no receiver |
|---|---:|---:|
| `V(SL1)` p2p | `386.08 µV` | `1.631 µV` |
| `V(N6)` p2p | `385.80 µV` | `3.271 µV` |
| `I(L_SL)` p2p | `0.3966 µA` | `0.1359 µA` |
| JS1 p2p | `0.50997 rad` | `0.05604 rad` |
| JS2 p2p | `0.59001 rad` | `0.00554 rad` |
| JM2 p2p | `0.39639 rad` | `0.26827 rad` |

这是明确的额外 source/back-action ringing，且不应被描述为“canonical
waveform unchanged”。另一方面，ringing 从 `110–120 ps` 到
`160–170 ps` 单调衰减；READ=0 control 没有 complete sequence，JM1/JM2
和 JS1/JS2 的 logical sign 也没有翻转。read0 的 JM1/JM2 sign 与 read1
仍分离。因此本报告将其标为 bounded extra back-action，而不是把它升级成
free-running 或 storage collapse。

## 8. Observed / Derived / Inference / Unknown

### Observed

- 四次 artifact 有效且同一 timestep/stop time。
- R15-B split-winding point 保留 read1 B_DET 的 `3.913-turn` continuous
  detector segment；read0 为 `0.185-turn`，control 为零事件。
- J_SET、J_Q、J_OUT 和 DCSFQ B1/B2/B3 的 activity 对四个 case 相同到
  raw precision，没有 read1-selective downstream sequence。
- `I(L1)` 约 `0.511 µA` peak，不高于 R1a passive scale。
- source/storage logical sign 保持，但 read1 后有明显额外衰减 ringing。

### Derived

- B_DET read1 segment 的 phase/area residual为 `2.73e−5 turn`，满足本地
  detector segment 的 phase/area consistency；这不是 SFQ delivery evidence。
- B3 最大 segment `5.77e−5 turn`，与同段 area一致，但远未达到一圈。
- R15-B 的 Q→FQ→FO→CTL split-winding path 在本实际 loaded run 中没有把
  detector state 变成可见的 current-steering output。

### Inference

- 本单点失败位置最接近 `B_DET → J_SET/J_Q` 的 state-compression/transfer
  mechanism，而非 DCSFQ B3 本身的 one-shot evidence。
- 失败不是 R15-A 非正定 mutual matrix 的重现；R15-B constitutive topology
  已能运行并产生合法 detector response。
- source isolation 仍不够干净；后续若重用该 detector，必须把额外 source
  loading作为一级约束。

### Unknown

- 单点结果不能证明所有 split-winding 或所有 active interstage 都不可行。
- 没有测试另一组 K/L/R/AREA/bias，也不能从本点推出 universal threshold。
- 没有接 JTL/T1，因此没有 downstream transport evidence。

## 9. Stop disposition

本轮停止于 `ACTIVE_STAGE_NO_TRIGGER`。不自动修改 J_SET/J_Q/J_OUT 的
AREA、bias、K、L、R 或 polarity；不接 JTL/T1。若继续，问题应回到
`J_SET/J_Q/J_OUT` 的 state-compression mechanism，并先处理 detector 到
active stage 的因果 transfer 和 BVM back-action；不得把本结果写成对整个
active-regenerative receiver family 的 universal impossibility。
