# R9-A 结果报告：native-QB output-side L2 load-line single point

日期：2026-08-23（Asia/Shanghai）
实验目录：`test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/`
父基线：R7-A，`test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/`
本轮唯一 receiver 变更：`L2: 3.91 pH → 2.50 pH`。

## Verdict

`ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED`

这个 verdict 只表示：在本模型、该 R7-A source/receiver fixture、四个 matched
case 和 `[94,130) ps` routing window 下，L2/BJL2 的 control-subtracted
dynamic transfer 增加，同时 read0/control 仍没有 complete BJL2 transition，
canonical BVM source/storage guard 没有出现 R6-A 级别的恶化。

它**不**表示 BJL2 已完成 local event，也不表示已有 threshold-like nonlinear
amplification 或 downstream SFQ delivery。`ISOLATED_NATIVE_QB_LOCAL_PASS`
没有满足。

## Artifact 与执行

- 四个 case 均退出码 0；每个成功 raw 为 `run-02.csv`，共 13599 行数据、39
  列，时间从 `0` 到 `169.9875 ps`，时间严格递增；`dt` 为 `0.0125/0.025 ps`
  的 solver 输出组合。
- `raw/read1/run-02.csv`、`raw/read0/run-02.csv`、两个 READ=0 control 的
  finite/column/time-axis QA 均通过，artifact status 为 `VALID`。
- 初次 launch 的 `run-01` 只因从 exploration cwd 使用了不存在的相对
  `build/josim-cli` 路径而失败，没有写入 raw；失败 stderr 保留，成功 run-02
  使用绝对路径重新执行。该 artifact-only launch failure 不改变四个物理
  case 的成功运行数。
- JoSIM：`build/josim-cli`，`v2.7.2837d13`，SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`。
- metric semantics：`docs/research/METRIC_SPEC_V2.md` v2.0.0，SHA-256
  `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`。

## 1. Settled operating point：static bias redistribution

以下是 `[80,90) ps` median；四个 R9 case 的 settled receiver point 相同，
因此表中只列一次，并与 R7-A 对照。电流单位为 µA，phase 为 raw `P(...)`
rad。`I(RJ1/RJ2)` 在 settled window 仍接近零。

| 量 | R7-A (`L2=3.91 pH`) | R9-A (`L2=2.50 pH`) | 变化 |
|---|---:|---:|---:|
| `P(BJs)` | `-0.1590093` | `-0.1390070` | `+0.0200023 rad` |
| `I(BJs)=I(Lin)` | `-21.05925` | `-18.42847` | `+2.63078` |
| `P(BJL1)` | `+0.2741902` | `+0.2397992` | `-0.0343910 rad` |
| `I(BJL1)` | `+30.32595` | `+26.60084` | `-3.72511` |
| `P(BJL2)` | `+0.2057599` | `+0.2402445` | `+0.0344846 rad` |
| `I(BJL2)=I(L2)` | `+38.61479` | `+44.97069` | `+6.35590` |
| `I(L1)` | `-51.38521` | `-45.02931` | `+6.35590` |
| `I(RB)` | `+90.00000` | `+90.00000` | `0` |

因此，L2 change 明显重新分配了 native loop 的 static current/phase：BJL2/L2
branch 增加约 `6.36 µA`，L1 branch 向零移动同样的量，前级 Lin/BJs 也移动
约 `2.63 µA`。这不是“只改变 AC reactance 而 DC 工作点不变”。

用预检中声明的一阶 inductive-flux proxy 重算：

\[
 L_1I_{L1}+L_2I_{L2}
 = 2.50(-45.02931)+2.50(44.97069)
 = -0.14655\;pH\,µA
 \simeq -7.09\times10^{-5}\Phi_0.
\]

R7-A 对应 proxy 是 `22.5208039 pH·µA = 0.0108910 Φ0`。这个巨大差异说明
实际 nonlinear network 的 settled load-line 随 L2 改变；proxy 仅用于预检选点，
不能当作完整 fluxoid balance。

## 2. Control-subtracted dynamic routing

定义保持预注册：

\[
\delta I_x(t)=I_{read}(t)-I_{matching\ READ=0\ control}(t),
\]

窗口为半开 `[94,130) ps`，RMS 单位为 µA。R7-A 和 R9-A 如下：

| case | `G_L2` R7-A | `G_L2` R9-A | 变化 | `G_BJL2` R7-A | `G_BJL2` R9-A | 变化 |
|---|---:|---:|---:|---:|---:|---:|
| read1 | 0.244831 | 0.330925 | +35.2% | 0.220688 | 0.301494 | +36.6% |
| read0 | 0.455252 | 0.625842 | +37.5% | 0.406046 | 0.561687 | +38.3% |

绝对 RMS 也增加：

- read1：`δI_L2 0.743809 → 0.911356 µA`，`δI_BJL2 0.670463 →
  0.830304 µA`；
- read0：`δI_L2 0.144816 → 0.191185 µA`，`δI_BJL2 0.129164 →
  0.171586 µA`。

这支持真实的 dynamic routing gain，而不是只看 settled current。然而 read0
的 routing 也几乎同比增加，故 L2 没有建立更宽的 state-selective margin：
`G_BJL2(read1)/G_BJL2(read0)` 从 `0.5435` 变为 `0.5368`，只有轻微变差。
因此“selectivity preserved”是指 read1 仍明显强于 read0、controls inactive，
不是指 L2 使 selectivity ratio 改善。

## 3. BJL2 phase / same-JJ voltage-area evidence

所有量均来自同一 BJL2、同一方向、同一 `[94,130) ps` window；phase 是连续
unwrapped trajectory，area 是同一段直接 `V(BJL2|XBQ)` 的时间积分除以
`Φ0`。

| case | activity range (turn) | largest monotonic segment (turn) | same-segment area (turn) | residual (turn) | current p2p (µA) | `|V|` peak (µV) |
|---|---:|---:|---:|---:|---:|---:|
| R9 read1 | 0.00423465 | `-0.00226164` | `-0.00226229` | `+6.49e-7` | 5.03326 | 11.1682 |
| R9 read0 | 0.00106433 | `+0.000478372` | `+0.000478517` | `-1.45e-7` | 1.11168 | 3.00811 |
| R9 logical1 READ=0 | `~0` | 0 | `+1.72e-10` | `-1.72e-10` | numerical | numerical |
| R9 logical0 READ=0 | `~0` | 0 | `-1.67e-10` | `+1.67e-10` | numerical | numerical |

相对于 R7-A，read1 BJL2 的 activity range 增加约 `19.0%`，largest segment
和 same-JJ area 增加约 `19.9%`，current p2p 增加 `24.6%`，voltage peak
增加 `15.6%`。read0 也增加：activity range `25.0%`、largest segment/area
约 `26.6%`、current p2p `34.9%`。read1 largest segment 与 read0 的比值仍约
`4.73`，且两者都远小于 `1 turn`。

因此：

- read1/read0 separation 保持；
- 四 case 都没有 qualifying complete BJL2 segment；
- phase/area consistency 只说明这些是小的 local activity excursions，不能把
  它们称为 SFQ event；
- 没有 post-event retrap 问题可审计，因为没有 first complete event；
- 没有 free-running output observation。

`BJL2` 的 `Ic=189 µA`（AREA=1.89，jjmit scaling）只作为局部工作点参考：
R9 settled `I/Ic=0.2379`，read1 activity peak `I/Ic=0.2516`，read0 peak
`I/Ic=0.2409`。这些比值不能作为 switching/event 判据。

## 4. BJs/BJL1 与 loop redistribution

R9 read1 的 activity range / largest segment：

| JJ | range (turn) | largest segment (turn) | same-segment area (turn) |
|---|---:|---:|---:|
| BJs | 0.0154489 | +0.0152069 | +0.0152120 |
| BJL1 | 0.0131278 | -0.0120946 | -0.0121008 |
| BJL2 | 0.00423465 | -0.00226164 | -0.00226229 |

相比 R7-A，BJs/BJL1 的 read1 activity 没有呈现与 BJL2 相同的单调增大；
BJL2 的变化主要表现为 L2/output-side branch 的 redistribution，而不是
一个已出现的 output quantization jump。READ=0 controls 三颗 JJ 均保持
数值噪声量级。

## 5. Canonical BVM source/storage guards

以下为 read1/read0 activity peak 或 post-window 指标；同时列出 R7-A 与
canonical no-receiver 作为参照。JS1/JS2 的 canonical read1 约 `-3 turns`
running 不计作 receiver back-action；只比较额外扰动、JM drift、SL/N6。

| case/metric | canonical | R7-A | R9-A |
|---|---:|---:|---:|
| read1 `peak I(L_SL)` (µA) | 75.34089 | 75.30207 | 75.28556 |
| read1 `peak V(SL1)` (µV) | 904.0907 | 905.3122 | 905.5102 |
| read1 `peak V(N6)` (µV) | 1814.477 | 1816.541 | 1816.571 |
| read1 JM1 drift (turn) | +7.7906e-5 | +8.0771e-5 | +8.0851e-5 |
| read1 JM2 drift (turn) | +5.7527e-5 | +3.9240e-5 | +3.9486e-5 |
| read1 JS1 post p2p (turn) | 0.0089190 | 0.0089095 | 0.0089095 |
| read1 JS2 post p2p (turn) | 0.0008817 | 0.0008881 | 0.0008865 |
| read0 `peak I(L_SL)` (µA) | 26.41147 | 26.23638 | 26.23870 |
| read0 `peak V(SL1)` (µV) | 316.9376 | 319.2597 | 319.2513 |
| read0 `peak V(N6)` (µV) | 652.9926 | 653.3906 | 653.3973 |
| read0 JM1 drift (turn) | -5.9683e-6 | -5.9683e-6 | -5.9683e-6 |
| read0 JM2 drift (turn) | +2.3077e-4 | +2.3090e-4 | +2.3092e-4 |
| read0 JS1 post p2p (turn) | 0.0015339 | 0.0015373 | 0.0015373 |
| read0 JS2 post p2p (turn) | 0.0001781 | 0.0001805 | 0.0001805 |

R9 与 R7-A 的 source numbers 基本重合，且相对 canonical 的变化仍是小的
fixture-level difference；没有观察到 R6-A direct-SL native-QB 的 post-state
multi-turn drift。source/storage guard 判定为保持。

## 6. Observed / Derived / Inference / Unknown

### Observed

- 四个 R9 raw artifact 有效，且 read1/read0/control 使用相同 receiver 与
  `L2=2.50 pH`。
- settled KCL/phase 显著重排：BJL2/L2 增加 `6.35590 µA`，L1 相反移动，
  BJs/BJL1 也移动。
- `[94,130) ps` control-subtracted `G_L2`、`G_BJL2` 对 read1 和 read0
  都增加；read1 仍比 read0 强。
- BJL2 最大 monotonic segment 仅 `0.00226164 turn`，同段 area 相符但远未
  达到一 turn；read0/control 没有 complete segment。
- BVM SL/N6、JM1/JM2、JS1/JS2 相对于 R7-A/canonical 保持在同一 bounded
  source behavior。

### Derived

- R9 read1 `G_L2` 相对 R7-A 增加 `35.2%`，`G_BJL2` 增加 `36.6%`；这是
  control-subtracted dynamic metric 的直接比较。
- BJL2 read1 phase/area activity 约增加 `20%`，但没有从小信号 excursion
  跳到 `0.1–1 turn` 的 threshold-like regime。
- read0 BJL2 activity 也增加约 `25–35%`，所以 selectivity 保持但 margin
  没有改善。

### Inference

- L2 reduction 确实改善了 node3→node4/BJL2 的 dynamic routing，但该单点的
  主要可辨识机制同时包含 static bias redistribution 和 load-line change；
  不能归因于 `X_L2` 单因素。
- read1/read0 近似同比增强、且同段 phase/area 仍线性一致，说明此点更像
  bounded routing/load-line gain，而不是 output-stage quantization onset。
- 在不改变 IB/JJ AREA/L1/transformer 的边界内，继续 L2 微调的预期信息增益
  很低；passive load-line routing 分支应停止。

### Unknown

- 本轮没有 timestep refinement；结论仍是 Exploration-tier、fixture-local。
- 没有证明完整 native-QB BJL2 local event、retrap/rearm、JTL/T1 transport
  或 downstream SFQ delivery。
- 没有由单点分离出 L2 reactance、static current redistribution 与 nonlinear
  load-line curvature 各自的独立因果贡献。

## Final classification and next boundary

R9-A 的主 verdict 是：

`ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED`

同时记录：`ISOLATED_NATIVE_QB_LOCAL_PASS = NOT MET`，
`threshold-like nonlinear amplification = NOT OBSERVED`。

由于本单点没有产生明显 BJL2 nonlinear/quantizing gain，停止当前 passive
load-line routing branch；下一阶段只应重新设计一个可解释的 bias-routing 或
BVM-specific QB operating-point hypothesis。该建议不在 R9-A 中实施，也不接
JTL/T1。
