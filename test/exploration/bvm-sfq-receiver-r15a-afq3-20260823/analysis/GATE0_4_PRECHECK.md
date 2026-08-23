# R15-A Gate 0–4 SPICE-level analytic/pre-run gate

日期：2026-08-23
基线：`3113a4640c74e515cc6fe991f1c37752b168e8c2`
结论：**`PRECHECK_NO_GO`**

本结论在任何有效的四-case scientific JoSIM run 之前作出。AFQ-3 的节点
KCL/DC closure 有定义，但 nominal magnetic constitutive network 不成立：
`L_Q`、`L_F`、`L_CTL` 的互感矩阵不是正定矩阵。因而不能把后续求解器挂起或
未产生 CSV 的尝试解释为电路物理结果，也不能通过私自改变 `K` 来修复本点。

## Gate 0 — topology closure and constitutive magnetic validity

AFQ-3 的唯一 netlist 是 `inputs/afq3.cir`。

### 节点与 KCL

```text
SL1 → R_IN → N_PICK → L_TX → N_DET → B_DET → GND
                                      ↑ I_DET from GND
L_TX == K_IN=-0.80 == L_S
```

`B_DET` 两端是 `N_DET`/ground。`L_TX` 的声明方向是 `N_PICK→N_DET`；
`L_S` 的声明方向是 `N_S1→N_S2`。

```text
I_SET: GND → N_S0
N_S0 ─ L_RET ─ N_S1 ─ L_S ─ N_S2 ─ B_SET ─ N_QMODE
                                            │
                              ┌─────────────┴─────────────┐
                              │                           │
                         R_Q=2Ω→GND              L_Q→N_QJ→B_Q→GND
```

`B_SET`（概念名称 J_SET）两端精确为 `N_S2`/`N_QMODE`。`R_Q` 是从
`N_QMODE` 到 ground 的耗散支路；它不是跨 `B_SET` 的 shunt。`L_Q` 与
`B_Q` 构成从 `N_QMODE` 到 ground 的另一条串联支路。

```text
N_F ─ L_F ─ GND
N_F ─ R_F ─ GND
```

`L_F` 与 `R_F` 精确并联；`L_F` 只通过互感连接 `L_Q` 与 `L_CTL`，没有
galvanic connection 到这两支路。

```text
I_OUT: GND → N_DRV
N_DRV ─ L_CTL ─ N_OUTJ ─ (B_OUT || R_OUT_SH) ─ GND
  │
  └─ R_SRC ─ N_INJ ─ L_INJ ─ DCS_A (= DCSFQ_BVM.a)
```

因此 `N_DRV` 的 KCL 是：

\[
I_{OUT}=I_{L\_CTL}+I_{R\_SRC}.
\]

`B_OUT` 两端是 `N_OUTJ`/ground，`R_OUT_SH=3 Ω` 与它并联。`J_OUT` 的
DC return 通过 `L_CTL`、`B_OUT/R_OUT_SH` 到 ground；另有
`R_SRC/L_INJ/DCSFQ.a` 的负载支路。

DCSFQ 内部 `a→L1→node1→L2→ground` 提供 AFQ `L_INJ` 的外部 DC return；
其 `IB1/IB2` 不是直接接 AFQ 节点的独立 bias source，但内部 bias current
可以经 `L1` 对 `DCS_A` 产生 backfeed。该路径是已识别的动态/静态负载，
不是未声明的 common-mode voltage source。

### Gate 0 的硬失败：互感矩阵

nominal netlist 声明：

```text
L_Q   = 4.0 pH
L_F   = 20.0 pH
L_CTL = 4.0 pH
K_QF  = +0.90
K_FO  = +0.90
```

没有 `L_Q–L_CTL` 的第三个 mutual。因此按 `[L_Q,L_F,L_CTL]` 排列，归一化
矩阵是：

\[
\mathbf K=
\begin{bmatrix}
1&0.9&0\\
0.9&1&0.9\\
0&0.9&1
\end{bmatrix}.
\]

其 determinant 与最小特征值为：

\[
\det(\mathbf K)=1-0.9^2-0.9^2=-0.62,
\qquad
\lambda_{min}=1-\sqrt{0.9^2+0.9^2}=-0.2727922.
\]

实际 pH 矩阵为：

\[
\begin{bmatrix}
4&8.0498447&0\\
8.0498447&20&8.0498447\\
0&8.0498447&4
\end{bmatrix}\ \mathrm{pH},
\]

其 determinant 为 `−198.4 pH³`。符号翻转不能修复这一问题，因为在没有
第三个 mutual 的情况下该条件由两个耦合系数的平方决定。

所以：

- node-level KCL/DC closure：`PASS_ANALYTIC`；
- physical mutual-inductance closure：`FAIL`；
- Gate 0 overall：**`FAIL_INVALID_MUTUAL_INDUCTANCE_MATRIX`**。

`K_IN=-0.80` 的二线圈块本身满足 `1−K_IN²=0.36>0`；失败来自两个
`.90` coupling 共享同一个 `L_F` 的三线圈块，而不是 BVM、DCSFQ 或
`K_IN` source route。

## Gate 1 — actual `jjmit` reconstruction

直接从本 exploration snapshot 的 `inputs/jjmit.cir`/当前仓库 model 解析：

```text
.model jjmit jj(RTYPE=1, VG=2.8m, CAP=0.07p,
+ r0=160, rn=16, icrit=0.1m)
```

按 JoSIM 的实际 AREA semantics：`Ic,C ∝ AREA`，`RN,R0 ∝ 1/AREA`。

| JJ | AREA | Ic | C | RN | R0 | βc(intrinsic) | RN·C | R0·C |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `B_SET` / J_SET | .08 | 8 µA | 5.6 fF | 200 Ω | 2 kΩ | 5.4450545 | 1.12 ps | 11.2 ps |
| `B_Q` / J_Q | .50 | 50 µA | 35 fF | 32 Ω | 320 Ω | 5.4450545 | 1.12 ps | 11.2 ps |
| `B_DET` | .50 | 50 µA | 35 fF | 32 Ω | 320 Ω | 5.4450545 | 1.12 ps | 11.2 ps |
| `B_OUT` / J_OUT | 3.0 | 300 µA | 210 fF | 5.333333 Ω | 53.333333 Ω | 5.4450545 | 1.12 ps | 11.2 ps |

额外的 AFQ time estimates：

- `L_Q/R_Q = 4 pH / 2 Ω = 2.0 ps`；
- `(L_RET+L_S+L_Q)/R_Q = 59 pH / 2 Ω = 29.5 ps`，这是整条 SET/Q
  return loop 的 `L/R` 估计，不是 JJ event 判据；
- `L_F/R_F = 20 pH / 10 Ω = 2.0 ps`。

Gate 1 的 model reconstruction 本身通过，但不覆盖 Gate 0 的矩阵失败。

## Gate 2 — no-input stability estimate

nominal bias/Ic ratios：

| branch | nominal bias | Ic | ratio |
|---|---:|---:|---:|
| `B_DET` | 15 µA | 50 µA | .300 |
| `B_SET` | 5.6 µA | 8 µA | .700 |
| `B_Q` | nominally about 5.6 µA | 50 µA | .112 |
| `B_OUT` | 275 µA | 300 µA | .9167 |
| DCSFQ B1/B2 bias source vs 80 µA class | 100 µA | 80 µA | 1.25 |
| DCSFQ B3 bias source vs 250 µA class | 175 µA | 250 µA | .700 |

`B_OUT` 的 `275/300 µA` 近临界状态是主要 startup/free-running risk。
没有在错误的 mutual matrix 上运行 no-input DC/small-signal solver；因此
Gate 2 只能标记为：**`NOT_EXECUTED_GATE0_FAILED`**。不能把上述 ratios
写成“存在稳定工作点”的证据。

## Gate 3 — read1/read0 discrimination estimate

从已接受 R1a raw 的 `[94,130) ps` 窗口提取 `I(L_TX|XTRIG)`：

| case | positive peak | negative peak | absolute peak |
|---|---:|---:|---:|
| read1 | +54.19963 µA | −43.98011 µA | 54.19963 µA |
| read0 | +17.09002 µA | −22.16104 µA | 22.16104 µA |

\[
M=|K_{IN}|\sqrt{L_{TX}L_S}=2.5298221\ \mathrm{pH},
\quad |M|/L_S=0.0505964.
\]

按冻结的 favorable polarity，得到一阶 estimate：

- read1 incremental current：`+2.74231 µA`；
- read0 worst-absolute incremental current：`1.12127 µA`；
- J_SET total：`8.34231 µA = 1.0428 Ic` vs `6.72127 µA = 0.8402 Ic`；
- read1/read0 current margin：`1.62104 µA`；
- corresponding absolute coupled flux：read1 `0.06631 Φ0`，read0
  `0.02711 Φ0`。

这些是 coupled-current/flux estimates，不是 event evidence；尤其不使用
`I>Ic` 宣称 J_SET switching。反向 read1 lobe 约为 `−2.225 µA`，真实
branch sign、相位和后续 load-line 只能由一个有效 netlist 运行后判定。
一阶 reflected-impedance estimate 约为 `0.34 Ω`（2 ps scale）和
`0.068 Ω`（10 ps scale），但在当前 invalid magnetic block 下不能验证。

Gate 3：**`PASS_AS_NOMINAL_ESTIMATE_ONLY`**。

## Gate 4 — active-output scale estimate

若暂时把 `B_OUT` switching state 当作一个独立电流-steering state，使用
`I_OUT=275 µA`、`R_OUT_SH=3 Ω`、`R_SRC=.75 Ω`、`L_INJ=2 pH` 与 frozen
DCSFQ 的 `L1/L2` 做一阶 current-division bracket：

| assumed favorable duration | estimated `I(L1)` | estimated `V(DCS_A)` |
|---:|---:|---:|
| 10 ps | 105.5–152.0 µA | 110.9–532.4 µV |
| 20 ps | 150.1–188.5 µA | 78.9–330.1 µV |

该 bracket 高于 R1a passive `5.564 µA`、R12 `68.4 µA` no-event reference，
覆盖 R13 actual `110.2 µA` subthreshold scale，但低于 R12 `300 µA` positive
reference。`300 µA` 不是 hard threshold；duration、DCSFQ load-line 和
实际 steering waveform 都未知。

由于 Gate 0 失败，这只是独立 bias source 的量纲/量级诊断，不能称为本
AFQ-3 已建立 active gain，也不能作为 DCSFQ drive 的实测值。

Gate 4：**`NOT_EXECUTED_AS_LOADED_NETWORK`; diagnostic scale only**。

## Execution disposition

最终 verdict：**`PRECHECK_NO_GO`**。

有一次在旧版、尚未包含互感正定性检查的 precheck 输出下启动的
`logical1-read0-control` 诊断进程。它只输出 JoSIM banner，未产生 CSV；
随后在发现 Gate 0 硬失败后被精确停止。该日志被保留，但不属于 scientific
case，不产生任何 phase/voltage-area/event 结论。四 matched cases 没有一个
通过有效 pre-run gate，因此没有运行/保存任何 raw result。

本轮不修改 `K_QF`、`K_FO`、inductance、JJ AREA、bias、DCSFQ 或 canonical
BVM；也不自动提出修复点。任何 retry 都必须先另行定义一个物理可实现的
multi-winding topology（包括完整互感矩阵/第三 mutual 或不同的耦合方式），
再重新 preregister，不能把本轮结果解释为 AFQ architecture 的物理失败。

### Observed / Derived / Inference / Unknown

- **Observed**：nominal netlist 的三线圈 mutual coefficients；Gate 0 计算
  得到负 determinant/negative eigenvalue；旧诊断进程无 CSV；canonical 与
  copied input files 未修改。
- **Derived**：jjmit AREA 参数、`βc`、`L/R`、R1a coupled-current
  estimate、active-output first-order bracket。
- **Inference**：当前 AFQ-3 nominal point 在运行前就没有可接受的被动互感
  constitutive model；挂起/无输出不是 detector、regenerator 或 DCSFQ 的
  evidence。
- **Unknown**：修复后的 AFQ topology 是否能压缩 B_DET、是否能提供 DCSFQ
  one-shot、是否满足 source/storage guards；本轮没有数据回答这些问题。
