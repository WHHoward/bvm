# R14-A report: B_DET to frozen DCSFQ_BVM interface precheck

日期：2026-08-23
模式：lightweight Exploration；analytic precheck only
基线：R13-A，`abad1d46e5f50b0f0796f00e84f1cdd3bb12bca6`

## Verdict

`PRECHECK_NO_GO`

本轮没有运行 JoSIM，没有生成 R14 raw CSV，也没有修改 canonical BVM、R1a
termination、DCSFQ_BVM 或任何既有 evidence。

## Quantitative interstage-scale check

提取自 R1a read1 raw 的 `N_SEC` transient：

- `V(N_SEC)` 正峰：`+50.08963 µV`，负峰：`−66.76842 µV`；
- 正负峰时间分别为 `102.7375 ps` 和 `104.2750 ps`，局部峰间尺度
  `T=1.5375 ps`；
- `I(R_SEC_LOAD)` 与 `I(L_SEC)` 的绝对峰值均为 `5.564035 µA`。

并列的后端 reference 是：

| reference | value | meaning |
|---|---:|---|
| R1a secondary termination branch | `5.564 µA` | 已测 secondary branch current |
| R13 actual DCSFQ `I(L1)` read1 peak | `110.200 µA` | canonical replay 的实际 input scale，仍无 B3 event |
| R12 controlled bump | `68.4 µA` | 当前 fixture 下无完整 B3 event |
| R12 controlled bump | `300 µA` | 当前 fixture 下约 `1.03011` turn 的 bounded B3 local event |

`68.4 µA` 和 `300 µA` 不是 universal thresholds；它们只是同一 DCSFQ
fixture 的受控尺度参照。R13 更显示：实际 canonical read1 波形即使直接送入
frozen DCSFQ，`I(L1)` 峰值约 `110.2 µA`，且理想 polarity/dwell diagnostic
仍没有形成完整 B3 event。因此 `B_DET` 的 nonlinear activity 不能自动解释为
DCSFQ 已获得 active current gain。

在 proposed point `L1=1.672 pH` 下，用 raw-derived `T` 做有利于 DCSFQ 的一阶
估算：

\[
X_{L1}=2\pi L_1/T=6.8328\ \Omega,
\qquad
|I_{DCSFQ,L1}|_{est}=|V_{SEC}|/X_{L1}=9.7717\ \mu A.
\]

该值假定全部 measured secondary voltage 都落到 DCSFQ `L1` 上，尚未扣除
reflected loading 和 nonlinear impedance effects，因而是 optimistic estimate，
不是仿真结果。保留的 `12 Ω` branch 约为 `5.5640 µA`，两支路的 optimistic
parallel magnitude 约 `15.3357 µA`。即便把局部时间尺度放宽到 `3 ps`，同类
估算也只有约 `19.1 µA`，仍低于 `68.4 µA` 的 no-event controlled reference。

所以该 single point 没有足够的 interstage-scale 证据值得运行；按预注册规则
停止，而不是把 `B_DET active` 当成 DCSFQ active gain。

## Secondary termination audit

R1a 的真实 secondary topology 是：

```text
L_TX -- K -- L_SEC(N_SEC, 0)
                    │
                    └── R_SEC_LOAD=12 Ω ── ground
```

`R_SEC_LOAD` 是 R1a 的 physical termination/passive return，同时定义了 R1a
secondary voltage/current characterization。它不是可以在接入 DCSFQ 后静默删除的
观测 dummy。

若把 DCSFQ `a` 直接接到相同的 `N_SEC`，KCL 是：

\[
I_{sec,source}(t)=I_{RSEC}(t)+I_{DCSFQ,a}(t).
\]

其中 `I_DCSFQ,a` 是经 `DCSFQ_BVM` 的 `L1`、内部 loop 和 bias network 的动态
支路，不是固定电阻电流。因此相对 R1a 会出现 intentional parallel
double-loading：secondary voltage 可能下降，primary reflected load 可能变化，
而 read1/read0 margin 也可能改变。

本次 precheck 没有运行 loaded netlist，所以真实 nonlinear current split、
voltage collapse 和 back-action 仍是 `Unknown`。若未来要测试“DCSFQ input
取代 R1a termination”，必须建立独立 topology，而不能混入本 single point。

## Evidence classification

### Observed

- R1a raw secondary voltage/current values listed above；
- R13 actual DCSFQ input peak and R12 controlled references；
- R1a netlist contains `R_SEC_LOAD=12 Ω` as the secondary return.

### Derived

- `M=K√(L_PRI L_SEC)=0.505964 pH`；
- `X_L1=6.8328 Ω` at the raw-derived local lobe timescale；
- optimistic DCSFQ branch `9.7717 µA` and parallel total `15.3357 µA`。

### Inference

- 当前 point 更可能复用 detector discrimination，而没有提供已证实的
  DCSFQ-scale active gain；
- 保留 termination 是 provenance/source-boundary 保守选择，但会增加 reflected
  loading risk。

### Unknown

- loaded nonlinear DCSFQ input impedance and actual current split；
- 是否存在不牺牲 BVM source guard 的 active interstage gain；
- 后续 conditioner 是否能在 read0 margin 下提供足够 dwell/energy。

## Stop disposition

不运行 R14 四 matched cases；不 sweep `K/L/bias/load`；不接 JTL/T1。下一步若
继续，须另行设计能明确提供 temporal conditioning 与 active/regenerative gain 的
BVM-specific interface，不能把本次 `PRECHECK_NO_GO` 扩大解释为整个 detector
或 DCSFQ family 的 universal impossibility。
