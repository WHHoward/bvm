# R15-B AFQ-3 magnetic constitutive topology correction

日期：2026-08-23
父 checkpoint：`571fa918f9623e24ea8038bfb24c32087494316e`
模式：只读解析；未运行 JoSIM
解析结论：**`R15B_SINGLE_POINT_WORTH_TESTING`**

## 1. 问题边界

R15-A 的节点 KCL/DC path 有定义，但共享 `L_F` 的磁性 constitutive
matrix 无效：`L_Q--K=.90--L_F--K=.90--L_CTL` 且 `K_Q_CTL=0` 给出
determinant `−0.62`。本轮不降低既有 K 值来使求解器通过，而是比较两种
物理拓扑解释。

R15-A 没有有效 scientific raw run；以下 source 数值只使用其接受父证据中
保存的 R1a/R15-A analytic estimates，不能冒充新的 simulation observation。

## 2. 路线 A：true three-winding common magnetic structure

按 `[Q,F,CTL]` 排列，若保持 `K_QF=K_FO=.90`，补充
`K_QO=c`，则：

\[
\mathbf K_A=
\begin{bmatrix}
1&0.9&c\\
0.9&1&0.9\\
c&0.9&1
\end{bmatrix},
\qquad
\det(\mathbf K_A)=(1-c)(c-0.62).
\]

严格正定要求：

\[
0.62 < K_{QO} < 1.0.
\]

因此 `K_QO` 不能是微小修正；它必须是强 direct Q→CTL mutual。作为
解析比较点取 `K_QO=.80`：

- normalized determinant：`0.036`
- normalized eigenvalues：`[0.0658336, 0.2, 2.7341664]`
- `M_QF=M_FO=8.0498447 pH`
- `M_QO=3.2 pH`
- actual matrix eigenvalues：`[0.5401378, 0.8, 26.6598622] pH`

该路线确实可以构成有效的三绕组 common-core model，但 direct Q→CTL
反馈会改变原本由 `J_Q/R_Q/L_Q` 定义的 refractory/state-compression
load-line。以 `R_OUT_SH || R_N(B_OUT)=1.92 Ω` 作为局部输出负载近似：

\[
|Z_{Q\leftarrow CTL}|\approx
\left|\frac{(\omega M_{QO})^2}
{1.92+j\omega L_{CTL}}\right|
\]

约为：

| 时间尺度 | 直接 Q→CTL 反射量 |
|---:|---:|
| 10 ps | `1.28 Ω` |
| 20 ps | `0.44 Ω` |

10 ps 下该量已经接近 `R_Q=2 Ω`。此外，若 CTL 近似低阻，Q 的有效电感
会出现类似 `L_Q(1-K_QO²)` 的显著变化；这不是“保留原 refractory”可以
直接假定的情形。

A 的优点是不用新增 winding，且仍保留独立 `I_OUT=275 µA` 的 active
energy source。缺点是 direct Q→CTL path 可能让 Q 的多次 activity 直接
进入 output valve，增加 multi-fire、refractory 缩短和后端反灌风险。

## 3. 路线 B：split-winding / two-core

推荐将原共享 `L_F` 拆为两个不同磁芯上的 winding：

```text
                         Core-Q             Core-O
L_Q ── K_QFQ=+.90 ── L_FQ ── N_FX ── L_FO ── K_FOCTL=-.90 ── L_CTL
                       N_FQ                         0
                        │
                        └──────── R_F=20 Ω ──────── GND
```

精确 netlist 关系为：

```text
L_FQ    N_FQ   N_FX     20 pH
L_FO    N_FX   0        20 pH
R_F     N_FQ   0        20 Ω
K_QFQ   L_Q    L_FQ     +0.90
K_FOCTL L_FO   L_CTL    -0.90
```

`L_FQ`/`L_FO` 之间没有 mutual，`L_Q`/`L_CTL` 之间也没有 direct mutual。
两个 winding 通过同一 series damped loop 的电流传递状态，而不是通过
一个不可能的共享绕组直接同时耦合两个磁芯。

这里选择 `20/20 pH` 与 `R_F=20 Ω`，而不是 Sol review 中更保守的
`10/10 pH, 10 Ω` 点，理由是：

1. 每个局部 mutual numerator 保持 R15-A 的
   `0.90·sqrt(4·20)=8.0498447 pH`，避免把 Q→output passive transfer
   再降低约一半；
2. 总 series-loop `L=40 pH`、`R=20 Ω`，所以 `L/R=2 ps`，保留原
   `20 pH/10 Ω=2 ps` 的 bridge time scale；
3. 在 loop impedance 主导的一阶模型下，同时把 L、R、M 按相应比例扩大，
   reflected-load magnitude 与原先 `10/10` split 点近似相同；
4. 这是单一 `[DERIVED]` working point，不是 sweep，也不是偷偷修改
   R15-A 的 K 值。

第二磁芯采用反绕方向，故冻结 `K_FOCTL=-.90`。若未来执行时 read1 的
`J_Q` lobe 方向与该 preregistered polarity 相反，应判 polarity failure，
不能事后翻转 winding。

## 4. 推荐 topology 的完整磁性矩阵

按
`[L_TX,L_S,L_RET,L_Q,L_FQ,L_FO,L_CTL,L_INJ]` 排列，R15-B AFQ 部分的
完整电感矩阵为：

\[
\mathbf L_B=
\begin{bmatrix}
0.2&-2.529822&0&0&0&0&0&0\\
-2.529822&50&0&0&0&0&0&0\\
0&0&5&0&0&0&0&0\\
0&0&0&4&8.049845&0&0&0\\
0&0&0&8.049845&20&0&0&0\\
0&0&0&0&0&20&-8.049845&0\\
0&0&0&0&0&-8.049845&4&0\\
0&0&0&0&0&0&0&2
\end{bmatrix}\ \mathrm{pH}.
\]

其中：

- source block determinant：`3.6 pH²`；
- 每个 split-core block determinant：`15.2 pH²`；
- full determinant：`8317.44 pH⁸`；
- actual eigenvalues：
  `[0.071816, 0.650991, 0.650991, 2, 5, 23.349009, 23.349009, 50.128184] pH`；
- normalized determinant：`0.012996`；
- 所有 eigenvalues 严格为正。

DCSFQ 内部没有声明 mutual 的电感只是额外正对角项，不改变上述
constitutive positive-definite 结论。

## 5. KCL/DC closure

R15-B 保留 R15-A 的 detector、SET/Q 和 output/DC injection paths：

```text
SL → R_IN → L_TX → B_DET → GND
I_SET → L_RET → L_S → B_SET → N_QMODE
N_QMODE → R_Q → GND
N_QMODE → L_Q → B_Q → GND
I_OUT → N_DRV
N_DRV → L_CTL → (B_OUT || R_OUT_SH) → GND
N_DRV → R_SRC → L_INJ → DCSFQ.a
DCSFQ.a → L1 → node1 → L2 → GND
```

split transfer loop 的逐节点 KCL 为：

\[
I_{L_{FQ}}=I_{L_{FO}},
\qquad
I_{L_{FQ}}+I_{R_F}=0.
\]

`N_FX` 是两个 series winding 之间的内部节点；它通过 `L_FO` 到 ground，
`N_FQ` 通过 `R_F` 和 series winding 到 ground，不存在 floating island。

output node 仍满足：

\[
I_{OUT}=I_{L_{CTL}}+I_{R_{SRC}},
\qquad
I_{L_{CTL}}=I_{B_{OUT}}+I_{R_{OUT\_SH}},
\qquad
I_{R_{SRC}}=I_{L_{INJ}}.
\]

DCSFQ 内部 `IB1/IB2` 仍可能经 `L1` 对 `DCS_A` backfeed，但没有新的
AFQ→BVM common-mode bias path。BVM 侧仍只有已接受的 `K_IN=-.80`
source coupling。

## 6. 一阶 reflected loading

series transfer loop 的近似阻抗为：

\[
Z_F(\omega)=20+j\omega(40\ \mathrm{pH}),
\qquad M_{QFQ}=8.0498447\ \mathrm{pH}.
\]

忽略 JJ 的 nonlinear impedance，Q 侧 mediated reflected load：

\[
Z_{Q\leftarrow F}\approx
\frac{(\omega M_{QFQ})^2}{Z_F(\omega)}.
\]

| 时间尺度 | `Z_F` | `Z_Q←F` | `|Z_Q←F|` |
|---:|---:|---:|---:|
| 2 ps | `20+j125.66 Ω` | `0.790−j4.964 Ω` | `5.026 Ω` |
| 10 ps | `20+j25.13 Ω` | `0.496−j0.623 Ω` | `0.796 Ω` |
| 20 ps | `20+j12.57 Ω` | `0.229−j0.144 Ω` | `0.271 Ω` |

因此 B 消除了 A 的 direct Q→CTL term，但并不声称 Q 动力学完全不变。
10–20 ps 区间的 mediated load 小于 `R_Q=2 Ω`，其方向/幅度仍须由实际
nonlinear waveform 验证。

## 7. J_SET discrimination 与 active output scale

前端完全继承 R15-A：

\[
M_{IN}=0.80\sqrt{0.20\cdot50}=2.529822\ \mathrm{pH},
\qquad |M|/L_S=0.0505964.
\]

来自已保存 R1a input peak 的一阶 estimate：

| case | coupled increment | total with `I_SET=5.6 µA` | relative to `Ic=8 µA` |
|---|---:|---:|---:|
| read1 | `+2.74231 µA` | `8.34231 µA` | `1.0428 Ic` |
| read0 worst | `+1.12127 µA` | `6.72127 µA` | `0.8402 Ic` |

margin 为 `1.62104 µA`；绝对 coupled flux estimate 为 read1 `0.06631 Φ0`
和 read0 `0.02711 Φ0`。这只是 discrimination estimate，不是 event
判据，`I>Ic`、voltage peak 或活动样本均不能替代 phase/V-area evidence。

J_OUT 仍为 AREA `3.0`、`Ic≈300 µA`、`I_OUT=275 µA`，其独立 bias energy
保持。考虑 `R_OUT_SH=3 Ω` 与 `RN≈5.333 Ω` 的并联以及
`R_SRC=.75 Ω/L_INJ=2 pH`，一阶 DCSFQ input bracket 为：

| 假定 favorable duration | 条件性 `I(L1)` | 条件性 `V(DCS_A)` |
|---:|---:|---:|
| 10 ps | `78.4–152.0 µA` | `127.6–369.6 µV` |
| 20 ps | `119.6–188.5 µA` | `84.1–262.9 µV` |

这些量级高于 R1a passive `5.564 µA` 和 R14 optimistic loaded single-digit
µA scale；但仍不能把 R12 `300 µA` 当 universal threshold，也不能据此
预测 DCSFQ B3 event。

## 8. Luna adjudication

Sol XHigh 与本地解析一致推荐路线 B，但 Sol 的初始单点为
`L_FQ=L_FO=10 pH, R_F=10 Ω`。Luna 选择本报告的
`20/20 pH, 20 Ω` 单点，理由是它在不改变 `L/R=2 ps` 的同时保留 R15-A
每个 interface 的 `M=8.0498447 pH`，从而不因 split topology 再引入一个
额外的 passive transfer attenuation。该分歧是显式记录的单点选择，不是
隐藏 sweep。

路线 A 没有被证明数学上不可能；它被降级的原因是为了正定必须引入强的
`K_QO`，而这会直接改变 Q refractory/load-line 和 output back-action。

## 9. Observed / Derived / Inference / Unknown

- **Observed**：R15-A nominal matrix 无效；R1a read1/read0 input scale；
  R14 passive transfer 为 single-digit µA；R13/R12 output-scale references。
- **Derived**：路线 A 的正定条件；路线 B 的完整矩阵、determinant、eigenvalues、
  loop time constant、reflected loading、J_SET margin 和 DCSFQ current bracket。
- **Inference**：路线 B 是当前唯一同时满足 constitutive validity、Q→CTL
  direct isolation、独立 J_OUT 供能和非 passive-only output path 的可辩护
  next topology。
- **Unknown**：实际 `J_Q` refractory、polarity 是否在 read1 有利、J_OUT
  startup/free-running、active state compression、DCSFQ B3 response、BVM
  storage guard 和 timestep convergence。
