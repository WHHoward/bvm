# R15-C J_SET causal fixture summary

日期：2026-08-23  
模式：Exploration / single-point causal fixture  
父 evidence：R15-B `2622201e7e6ab72ce2a5066ccdbf3fd1c0ea65d7`

## Verdict

`CAUSAL_NEAR_THRESHOLD`

本点没有建立完整 J_SET event，因此不能称为 `JSET_CAUSAL_ONE_SHOT_PASS`。
但也不是 `CAUSAL_TRANSFER_FAILURE`：有限阻抗 bias return 已使 `I(B_SET)`
真正包含 read-state-dependent mutual response。

## Waveform-level analytic precheck

对 R15-B 四组真实 `I(L_TX)` raw 数值积分

```text
55 pH*d(delta_I_JSET)/dt + 27.5 ohm*delta_I_JSET
    = -(-2.529822 pH)*dI_TX/dt
```

得到的线性 pre-switch 预测为：

| case | predicted `I_JSET` min..max (µA) | forcing peak (mV) @ ps | response peak (µA) @ ps |
|---|---:|---:|---:|
| logical1 + READ | 3.114047..7.657608 | -0.383599 @ 104.125 | -2.485953 @ 104.525 |
| logical0 + READ | 4.763195..6.208259 | -0.152901 @ 105.000 | -0.836805 @ 106.000 |
| logical1 + READ=0 | 5.599981..5.600016 | -0.000002 @ 94.000 | -0.000019 @ 94.413 |
| logical0 + READ=0 | 5.599973..5.600026 | -0.000003 @ 94.963 | -0.000027 @ 95.575 |

forcing 是 `-M·dI_TX/dt`，response 的延迟来自 `LΣ/R_BIAS=2 ps` 的有限阻抗
网络。analytic read1/read0 modulation p2p ratio 约 `3.144`；该结果只是进入
JoSIM 的 causal-go 依据，不是 event evidence。

## Frozen point

只改变 R15-B 的 J_SET input fixture：

```text
I_SET   0      N_S0     5.6u
R_BIAS  N_S0   0        27.5
L_RET   N_S0   N_S1     5p
L_S     N_S1   N_S2     50p
B_SET   N_S2   0        jjmit area=.08
K_IN    L_TX  L_S      -.80
```

canonical BVM、R0b `B_DET`、`R_IN/L_TX`、source PWL、`dt=0.0125 ps` 和
四个 matched cases 均保持；没有 J_Q、J_OUT、DCSFQ、JTL 或 T1，也没有
参数 sweep。

## Evidence

| case | B_DET 最大单调段 (turn) | B_SET 最大单调段 (turn) | 同段 V-area (turn) | `I_JSET` activity p2p (µA) | KCL 最大绝对残差 (µA) |
|---|---:|---:|---:|---:|---:|
| logical1 + READ | 4.973019 | 0.224437 | 0.224483 | 7.031724 | `5.0e-7` |
| logical0 + READ | 0.184724 | 0.033851 | 0.033859 | 1.394338 | `5.0e-7` |
| logical1 + READ=0 | -0.000083 | -0.000001 | -0.000001 | `3.3e-5` | `5.0e-7` |
| logical0 + READ=0 | 0.000256 | -0.000002 | -0.000002 | `3.8e-5` | `5.0e-7` |

read1/read0 J_SET current-modulation p2p ratio 为约 `5.04`，read1/control
约 `1.85×10^5`。read1 的 B_SET phase 与同一 monotonic segment 的 voltage
area 一致，但只有约 `0.224 turn`；四 case 均为零 complete-event candidate。

直接检查同一 raw run 的：

```text
I(I_SET) = I(R_BIAS) + I(B_SET)
```

成立，窗口内最大残差约 `0.5 pA`。因此 R15-B 中由 ideal current source
把 B_SET branch current 锁死的 topology 问题，在 R15-C fixture 中得到
因果修正。

四个 JoSIM raw 均 exit `0`、各有 `13,599` 行，median `dt=0.0125 ps`。
每个 raw 在 `1.8375–1.8625 ps` 有一个 `0.025 ps` 输出间隔；该间隔与
matching R15-B raw 完全相同，且在所有分析窗口之外，不改变本轮 activity/event
判定。

## Source/back-action boundary

与 matching R15-B raw 的 post-window p2p 比较中，logical1 的
`V(SL) / V(N6) / I(L_SL) / JM1 / JM2 / JS1 / JS2` p2p 均未增加；分别为
`-46.903 µV / -44.7225 µV / -0.0177439 µA / -0.003858 rad /
-0.0850407 rad / -0.07525 rad / -0.10085 rad` 的 R15-C minus R15-B
差值。R15-B 已有的 bounded extra back-action 仍然存在，不能据此升级为
source-isolated success；但本点没有用 J_SET switching 换取更大的 post-window
p2p disturbance。JS1/JS2 的绝对 running-phase offset 另行保留为解释边界，
不单独作为 source failure 判据。

READ=0 controls 保持 inactive；未观察到 free-running 或 control event。

## Observed / Derived / Inference / Unknown

- **Observed:** R15-B 的强 B_DET read1 activity 在 finite-impedance J_SET
  network 中转化为明显的 read1-selective `I(B_SET)` modulation。
- **Derived:** read1 modulation p2p `7.031724 µA`，read0 `1.394338 µA`；
  B_SET 最大 segment/同段 area 分别为 `0.2244365/0.2244834 turn`。
- **Inference:** 当前瓶颈已从“detector state 没有进入 J_SET current degree of
  freedom”推进到“存在 causal near-threshold drive，但尚未完成 J_SET
  quantization”。
- **Unknown:** 仅凭本点不能判断哪一种后续 active-state compression 能将该
  sub-turn response 变成 bounded one-shot；本轮没有接回 J_Q/J_OUT/DCSFQ。

## Stop / next boundary

R15-C 是单点 causal fixture，至此停止；不 sweep `R_BIAS`、K、L、AREA 或
bias，不自动接 J_Q。后续若继续，问题应针对从已验证的 J_SET causal state
到 active interstage 的压缩机制，而不是把本点误写成完整 SFQ delivery。

完整 raw、netlist、commands、analysis 和 SHA-256 见本目录及
`analysis/sha256sums.txt`。
