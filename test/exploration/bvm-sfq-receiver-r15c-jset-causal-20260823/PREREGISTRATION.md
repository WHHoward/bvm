# R15-C J_SET causal fixture

日期：2026-08-23

模式：Exploration / single-point causal fixture

父 evidence：R15-B `2622201e7e6ab72ce2a5066ccdbf3fd1c0ea65d7`

## Scientific question

在保持 canonical BVM 和 frozen R0b B_DET 不变的情况下，给 J_SET bias
增加一个有限阻抗 current-summing return，能否使 R15-B 中已经存在的
read1/read0-dependent mutual transient 真正进入 `I(B_SET)`，而不是只表现为
ideal current-source compliance voltage？

本轮不接 J_Q、J_OUT、DCSFQ、JTL 或 T1。

## Analytic precheck

先使用 R15-B 已保存的四组 `I(L_TX)(t)` raw，按实际 CSV time column
逐段积分：

\[
L_\Sigma\frac{d\delta I_{JSET}}{dt}
+R_{BIAS}\delta I_{JSET}
=-M\frac{dI_{TX}}{dt}
\]

固定：

- `LΣ=55 pH`；
- `R_BIAS=27.5 Ω`；
- `M=-2.529822 pH`；
- baseline `I_SET=5.6 µA`；
- `Ic(B_SET)=8 µA`；
- initial `δI_JSET=0`。

报告每个 case 的 predicted `I_JSET(t)`、modulation max/min、read1/read0
separation、`M·dI_TX/dt` 与 modulation 的 polarity/timing，以及 controls。

不得使用已撤销的 `8.342/6.721 µA` static estimate。

### Precheck decision

- 若 read1 存在明显、state-selective、与 mutual term 方向/时间一致的 causal
  modulation，则进入唯一 JoSIM fixture；
- 若 read1/read0/control 没有可解释分离，则 `PRECHECK_NO_GO`，不运行 JoSIM；
- 该 precheck 不以 `I>Ic` 作为唯一判断，也不把 predicted current 当 event evidence。

## Frozen JoSIM topology

```text
I_SET   0      N_S0     5.6u
R_BIAS  N_S0   0        27.5
L_RET   N_S0   N_S1     5p
L_S     N_S1   N_S2     50p
B_SET   N_S2   0        jjmit area=.08
K_IN    L_TX  L_S       -.80
```

`R_BIAS` 是 bias current-summing return，不是直接跨 B_SET 的 damping shunt。
上游只保留 canonical BVM、`R_IN/L_TX/B_DET/I_DET` 的 frozen R0b detector。

唯一新参数为 `R_BIAS=27.5 Ω`，其来源是 R15-C architecture review 的
single-point designed hypothesis，满足 `(L_RET+L_S)/R_BIAS≈2 ps`；不是
evidence-derived optimum。

## Matched cases

1. logical1 + canonical READ
2. logical0 + canonical READ
3. logical1 + READ=0 control
4. logical0 + READ=0 control

全部使用 R15-B 相同的 canonical source PWL、`dt=0.0125 ps`、stop time
`170 ps` 和 BVM initial/write timing。

## Required evidence

- `P/V/I(B_DET)`；
- `P/V/I(B_SET)`；
- `I(I_SET)`、`I(R_BIAS)`、`I(L_RET)`、`I(L_S)`、`I(L_TX)`；
- direct KCL residual `I(I_SET)-I(R_BIAS)-I(B_SET)`；
- `V(SL)`、`V(N6)`、`I(L_SL)`；
- `JM1/JM2`、`JS1/JS2` source/storage guards。

J_SET event 必须满足：continuous unwrapped phase、同一 JJ/同一 segment
voltage-area consistency、bounded post/retrap。`I>Ic`、voltage peak 或
phase range alone 不能宣称 event。

## Verdict classes

- `JSET_CAUSAL_ONE_SHOT_PASS`：read1 一个 bounded complete J_SET transition，
  read0/control 零完整 transition，且 retrap/source guard 可接受；
- `CAUSAL_NEAR_THRESHOLD`：read1 有明确 selective current modulation，但没有完整 event；
- `CAUSAL_TRANSFER_FAILURE`：`I(B_SET)` 仍不含 read1/read0 difference；
- `BACK_ACTION_FAILURE`：causal modulation 存在，但 BVM source/storage disturbance
  明显超过 R15-B 可接受边界；
- `NONSELECTIVE_OR_FREE_RUNNING`：read0/control 完整 transition 或无界 running；
- `INCONCLUSIVE`：artifact、KCL、方向、phase/area 或 post stability 证据不足。

## Stop rule

single point only。失败后不 sweep `R_BIAS`、K、L、AREA 或 bias；不自动接
J_Q/J_OUT/DCSFQ。若 `I(B_SET)` 仍没有 state-dependent modulation，则停止
当前 active-stage family，重新审视 detector output variable。
