# R1b B_OUT AREA=.08 activation-margin Exploration

父 checkpoint：`e3a18da0b42bfdfdd1d36886cbad8b04d77617c9`。本目录是独立
Exploration，不修改 accepted AREA=.10 baseline 或 canonical BVM。

## Verdict

**Q1：NO。AREA=.08 没有提高 read1 B_OUT activation 到完整 switching。**

四个 matched raw CSV 均 artifact-valid。AREA=.08 read1 的最大连续单调
`B_OUT` 段只有 `0.0201217685` turn，same-JJ voltage-time integral 为
`-0.0201271525` turn；其绝对值远小于完整一圈。read0 也没有完整段，两个
`READ=0` controls 没有完整段或 free-running。因此这个单点是
**R1b AREA=.08 FAIL**，不是 INVALID。

这次结果也不能写成“降低 Ic 后仍然不可能 switching”：AREA 同时改变了
`Ic/RN/R0/C`，所以它是一个有界的 activation-barrier operating point test，
不是纯 Ic 消融。

## 1. Frozen topology and single variable

沿用 e3a18da 的 differential receiver：

```text
SL -> R_IN(12 ohm) -> L_TX(0.20 pH) -> B_TRIG -> ground
                                  || K=0.80
                       L_SEC -> R_SEC_LOAD(12 ohm) -> ground
                         N_SEC -> B_OUT -> ground
                         N_SEC <- I_OUT_BIAS(7 uA)
                         N_SEC -> R_OUT_DAMP(100 ohm) -> ground
```

`B_OUT` 仍直接是 `N_SEC` 到 ground，故 `V(B_OUT)=V(N_SEC)-V(0)`；
secondary return、mutual polarity、R_IN、L_TX、K、B_TRIG bias、B_OUT bias
和 damping 均未变。唯一电路变量是：

| quantity | accepted AREA=.10 | this point AREA=.08 |
|---|---:|---:|
| B_OUT Ic | 10 uA | 8 uA |
| B_OUT RN | 160 ohm | 200 ohm |
| B_OUT R0 | 1600 ohm | 2000 ohm |
| B_OUT C | 7 fF | 5.6 fF |
| B_OUT bias | 7 uA | 7 uA |
| R_OUT_DAMP | 100 ohm | 100 ohm |
| bias/Ic | 0.70 | 0.875 |

根据实际 `src/JJ.cpp` AREA semantics，`Ic,C` 按 AREA 缩放、`RN,R0` 按
AREA 反比缩放。intrinsic `beta_c` 仍约 `5.4450545`；把外部 100 ohm
shunt 与 RN 合并的 diagnostic 从 AREA=.10 的约 `0.8054814` 变为
AREA=.08 的约 `0.6050061`。这说明该单点同时改变了 dynamic damping/
energy-storage 条件。

其他冻结参数：B_TRIG `AREA=.50/Ic=50 uA/bias=15 uA`；`L_SEC=2 pH`；
`R_SEC_LOAD=12 ohm`；requested `dt=.0125 ps`；stop `170 ps`。

## 2. Matched raw evidence

相位为 raw `P(...)` 的 rad，经 `delta/(2*pi)` 转成 turns；voltage area
使用同一个 JJ、同一端点、同一方向、同一 segment 和 CSV 实际 timestamp。

| case | B_TRIG largest monotonic segment (phase / area turns) | B_OUT largest monotonic segment (phase / area turns) | B_OUT activity |
|---|---|---|---|
| read1 | 102.9375--110.7125 ps; `+3.9165106227 / +3.9165373234` | 103.2375--104.6375 ps; `-0.0201217685 / -0.0201271525` | `V` abs peak `73.9138 uV`; `I` `5.393--8.164 uA` |
| read0 | 106.5875--108.2125 ps; `+0.1848807799 / +0.1849041341` | 104.8125--106.0875 ps; `-0.0052866497 / -0.0052890792` | `V` abs peak `14.0936 uV`; `I` `6.463--7.578 uA` |
| logical1 + READ=0 | `8.4241e-5 / 8.4248e-5` | `7.9577e-7 / 7.0076e-7` | no complete transition |
| logical0 + READ=0 | `2.5417e-4 / 2.5422e-4` | `4.7746e-7 / 3.2045e-7` | no complete transition |

`B_TRIG` read1 remains complete and read0/control remain incomplete. `B_OUT`
read1 的 signed phase/area 片段在本点为 decreasing，但两者仍相互一致；
这只是一个 subturn excursion，不是 switching event。read1 output post
window phase range 约 `0.0008337 turn`，没有观察到 free-running output。

特别注意：AREA=.08 read1 的 `I(B_OUT)` 峰值约 `8.1637 uA`，略高于
其 nominal `Ic=8 uA`，但 phase 仍只有 `0.0201 turn`。这直接说明
`I > Ic` 样本不能替代完整 continuous phase/voltage-area 判据。

## 3. AREA=.08 versus accepted AREA=.10

独立脚本直接读取 e3a18da 的 accepted raw 和本点 raw，未使用旧 JSON 作为
数值来源：

| case / metric | AREA=.10 | AREA=.08 | bounded change |
|---|---:|---:|---:|
| read1 B_OUT phase magnitude | `0.0220583499 turn` | `0.0201217685 turn` | `-8.78%` |
| read1 B_OUT area magnitude | `0.0220676540 turn` | `0.0201271525 turn` | `-8.79%` |
| read1 secondary V | `75.0610 uV` | `73.9145 uV` | `-1.53%` |
| read1 secondary return I | `2.0960 uA` | `1.8597 uA` | `-11.27%` |
| read1 B_OUT current peak | `8.2396 uA` | `8.1637 uA` | `-0.92%` |
| read0 B_OUT phase magnitude | `0.0051599306 turn` | `0.0052866497 turn` | `+2.46%` |
| read0 secondary V | `13.0214 uV` | `14.0944 uV` | `+8.24%` |
| read0 secondary return I | `0.6203 uA` | `0.6047 uA` | `-2.51%` |

AREA=.08 的 secondary 仍有明显 state dependence：read1/read0 voltage ratio
约 `5.245`，return-current ratio 约 `3.075`；controls 仍在 sub-nV/sub-100-pA
量级。故 transformer route 没有消失或 polarity 反转，但 loaded transfer
不是完全不变，且 read1 transfer current 比 AREA=.10 小。

## 4. Q2: A/B/C bounded interpretation

### A. Ic margin

“Ic margin 是唯一主要原因”没有被支持为充分解释：nominal Ic 从 10 uA
降到 8 uA 后，read1 phase/area 反而下降，仍无完整 transition。由于 AREA
同时改变 RN/R0/C，不能从这一点单独排除 Ic 的贡献；能确定的是降低 AREA
这一 activation-barrier 点没有解决问题。

### B. Transformer coupling/current transfer

不是 topology/polarity 失效：B_TRIG read1 仍约 `3.9165 turn`，secondary
仍保持 read1/read0 separation。但 read1 secondary return-current activity
从 `2.0960` 降到 `1.8597 uA`，说明 output loading 与 transfer margin 有
定量影响。因此 B 是可能的 contributing limitation，而不是“没有 signal”。

### C. Damping dynamics

这是当前更强的 bounded explanation：AREA=.08 的 RN 从 160 增至 200 ohm、C
从 7 降至 5.6 fF，在固定 100 ohm 外部 shunt 下 diagnostic beta 从约
`0.805` 降至 `0.605`；同时 B_OUT phase、voltage area 和 current peak
都没有增大。即使有略高于 nominal Ic 的 current sample，也没有持续相位
转变，说明 dynamic damping/energy storage 参与限制。

综合判断：**更接近 C + B 的 loaded dynamic/transfer limitation，而不是
A（纯 Ic margin）单独主导。** 仅凭这一个 AREA 点不能把 B 与 C 唯一分离；
本轮不扩展为额外 sweep。

## 5. BVM back-action and controls

- 四 case 的 BVM logical-sign guard 通过；read1 storage drift 为
  `JM1 +0.0005753 turn`、`JM2 -0.0005807 turn`，read0 的 signs 仍保持。
- read1 source activity 为 `SL≈1.8822 mV`、`N6≈2.1177 mV`、
  `I(L_SL)≈54.16 uA`；B_TRIG 与 accepted AREA=.10 基线几乎不变，前端
  discrimination 未被破坏。
- read0 B_OUT 最大仅 `0.00528665 turn`；两个 controls 最大约
  `7.96e-7` / `4.77e-7 turn`，无完整 transition 或 free-running。
- storage logical sign 保持不等于 exact state preservation；本点未建立
  长时 storage fidelity 或 convergence Gate。

## 6. Artifact and evidence labels

### Observed

四个 raw CSV、`P/V/I(B_OUT)`、`P/V/I(B_TRIG)`、secondary V/I、SL/N6、
JM1/JM2、solver logs、baseline comparison 和独立 cross-check。

### Derived

same-JJ phase turns、same-segment voltage areas、AREA-scaled JJ 参数、
beta diagnostics、read1/read0 ratios、实际 CSV dt 和 output activity ranges。

### Inference

AREA=.08 没有提高本 receiver 的 read1 activation；当前 evidence 更支持
loaded transfer 与 damping dynamics 共同限制，而非纯 Ic barrier 不足。

### Unknown

单点不能分离 B 与 C，不能建立纯 Ic 消融结论；未测试其他 AREA、固定 RN/C
的 model variant、timestep convergence、exactly-one/self-quench、JTL 或
downstream SFQ delivery。

最终停止：不改 topology、不改 BVM、不启动 R1c，不扩大 sweep，不升级
Candidate。
