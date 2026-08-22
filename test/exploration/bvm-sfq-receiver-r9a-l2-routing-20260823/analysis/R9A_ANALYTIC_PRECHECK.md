# R9-A L2 analytic precheck

日期：2026-08-23（Asia/Shanghai）
基线：R7-A accepted point，输入数据来自
`test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/`。
本文件只记录运行前的 physics-informed 选择；它不是 JoSIM 结果。

## 研究边界

只改变 native QB 的 `L2`。恢复并冻结 R7-A 的其余 receiver/source 条件：

- BJs AREA = 1.33；BJL1 AREA = 1.12；BJL2 AREA = 1.89；
- `L1=2.50 pH`、`IB=90 µA`、`Lin=0.8 pH`、`L0=1.323 pH`；
- `RJ1=33 Ω`、`RJ2=22 Ω`、`RB=8.5 Ω`、10 Ω output load；
- R6-B transformer：`L_PRI=0.20 pH`、`L_SEC=1.00 pH`、`K=0.70710678`、`R_PRI=12 Ω`；
- canonical BVM、source PWL、`dt=0.0125 ps`、stop time `170 ps` 和四-case matrix 全部不变。

## 已有 R7-A settled/read1 输入量

R7-A READ=0 control 的 `[80,90) ps` median 为：

| 量 | 数值 |
|---|---:|
| `P(BJs)` | `-0.1590093 rad` |
| `I(BJs)=I(Lin)` | `-21.05925 µA` |
| `P(BJL1)` | `+0.2741902 rad` |
| `I(BJL1)` | `+30.32595 µA` |
| `P(BJL2)` | `+0.2057599 rad` |
| `I(BJL2)=I(L2)` | `+38.61479 µA` |
| `I(L1)` | `-51.38521 µA` |
| `I(RB)` | `+90.00000 µA` |

在该 settled window 中 `I(RJ1/RJ2)` 近似为零，因此 `I(L2)` 与 BJL2 的
静态 branch current 可作一致性检查。R7-A 的 L1/L2 静态感应量 proxy 为

\[
 L_1 I_{L1}+L_2 I_{L2}
 =2.50(-51.38521)+3.91(38.61479)
 =22.5208039\;pH\,µA
 =0.0108910\,\Phi_0.
\]

这只是用于选择点的**一阶 flux-preserving proxy**，不是把三 JJ、RB、RJ 和
外部输入全部消去后的 nonlinear loop equation，也不直接决定 fluxoid state。

## 动态 reactance

R7-A raw 的 read1 BJL2/L2 transient 在约 `1.5 ps` 量级有主导振荡。取

\[
 f\simeq(1.5\;ps)^{-1},\qquad
 \omega\simeq4.18879\times10^{12}\;rad/s,
 \qquad X_{L2}=\omega L_2 .
\]

候选点的量级如下：

| L2 | `X_L2` at 1.5 ps | 相对 R7-A 的 reactance 变化 | flux-proxy 预测 `I(L2)` | `I/Ic(BJL2)` |
|---:|---:|---:|---:|---:|
| 3.91 pH（R7-A） | 16.378 Ω | — | 38.615 µA | 0.2043 |
| 3.00 pH | 12.566 Ω | −23.3% | 50.328 µA（+30.3%） | 0.2663 |
| **2.50 pH** | **10.472 Ω** | **−36.1%** | **60.394 µA（+56.4%）** | **0.3195** |
| 2.00 pH | 8.378 Ω | −48.8% | 75.492 µA（+95.5%） | 0.3994 |

这里使用的 `Ic(BJL2)=189 µA` 来自 `jjmit` 的 AREA scaling；并没有把
`I/Ic` 当作 event 判据。AREA 不变，所以此次 L2 选择不会改变 JJ 的
`Ic/C/RN/R0`；它改变的是 `X_L2`、loop flux/current split 以及 nonlinear
load-line。

## 点选择与风险控制

- `3.00 pH` 的 reactance reduction 较温和，可能不足以把已经很小的
  BJL2 dynamic segment 推入新的 regime。
- `2.00 pH` 的 proxy static current shift 接近翻倍，虽然仍低于 bare
  `Ic`，但对 read0 margin、RB bias split 和 loop branch stability 的风险
  最大；它不是本轮所需的最小有信息增益点。
- `2.50 pH` 是两者之间的唯一中间点：在约 1.5 ps 处给出约 36% 的
  inductive impedance reduction，同时把 proxy static redistribution 控制在
  约 56% 的 branch-current 增量，而不是 2.0 pH 的约 96%。

因此本轮冻结唯一 operating point：**`L2=2.50 pH`**。这不是从三点
simulation sweep 得出的最优值，而是运行前基于 R7-A settled KCL/phase/flux
proxy 和动态 reactance 的局部诊断点。

## 预期可证伪观察

若 `L2=2.50 pH` 只改变 settled current/phase，却没有增加 control-subtracted
`G_L2`/`G_BJL2` 或 BJL2 same-JJ activity，说明本点只产生 static redistribution，
不能支持 passive load-line routing gain。若 read0/control 出现非选择性 activity
或 source guard 明显恶化，则说明此点过于激进或引入 reflected/back-action
问题。任何完整 local event 仍必须由同一 BJL2 的 continuous unwrapped phase、
monotonic segment、同段 voltage area 和 post-event retrap 联合证明。
