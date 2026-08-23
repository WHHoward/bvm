# R14-A analytic interface precheck

日期：2026-08-23

## Verdict

`PRECHECK_NO_GO`

本轮不运行 JoSIM。原因不是证明该 topology 普遍不可能，而是当前唯一冻结
point 的 loaded-network first-order scale estimate 仍没有显示足够的
DCSFQ input drive，且 B_DET 的 active/nonlinear behavior 不能自动等同于
DCSFQ input current gain。

## 1. Empirical interstage-scale check

并列比较如下：

| quantity | value | evidence meaning |
|---|---:|---|
| R1a read1 `I(R_SEC_LOAD)` peak | `5.564 µA` | 已测 secondary branch current，带 `R_SEC_LOAD=12 Ω` |
| R1a read1 `|V(N_SEC)|` peak | `66.768 µV` | 同一 secondary transient 的 measured voltage |
| R13 actual DCSFQ read1 `I(L1)` peak | `110.200 µA` | canonical current replay 的实际 input scale；仍未触发 B3 |
| R12 controlled `68.4 µA` | no complete B3 event | historical controlled point，不是 universal threshold |
| R12 controlled `300 µA` | `1.03011-turn` B3 local event | strong controlled positive evidence，不是 universal threshold |

R12 的受控对照说明 DCSFQ_BVM 的 event regime 至少与 `300 µA` 级输入相容，
而 `68.4 µA` 不足以在该 fixture 中形成完整 B3。R13 更严格：即使直接把
实际 canonical read1 waveform 重放到 DCSFQ input，`I(L1)` 峰值约 `110.2 µA`，
并施加理想 polarity/dwell transform，B3 仍只有约 `0.024 turn`。这些数字不被
当作 universal threshold；它们只限定当前模型、输入波形和后端的经验尺度。

### Proposed loaded estimate

R1a read1 secondary 的两个主要 voltage extrema 相隔约 `1.5375 ps`。用该
raw-derived local timescale 估算 DCSFQ input `L1=1.672 pH` 的 reactance：

\[
X_{L1}=2\pi L_1/T\approx6.83\ \Omega.
\]

使用 R1a 实测 `|V_SEC|=66.768 µV`，并作一个对 DCSFQ 有利的 optimistic
假设（全部 secondary voltage 都落在 L1、尚未发生 reflected-load voltage
collapse）：

\[
I_{DCSFQ,L1}^{est}\approx|V_{SEC}|/X_{L1}
\approx9.77\ \mu A.
\]

保留 `R_SEC_LOAD=12 Ω` 时：

\[
I_{RSEC}^{est}=|V_{SEC}|/12\Omega\approx5.56\ \mu A,
\]

所以二次侧两个并联 branch 的 optimistic total magnitude 约为
`15.34 µA`。真实 nonlinear DCSFQ input impedance 和 mutual reflected loading
只会让这个简单估计失效或降低可用 voltage；它不能被解释成已获得
`110 µA` 或 `300 µA` 的 active gain。

即使把 lobe timescale 放宽到 `3 ps` 作敏感性 sanity check，L1 branch 估计
也只有约 `19.1 µA`，仍显著低于 R12 `68.4 µA` no-event point 和 R13
`110.2 µA` actual input peak。这里的 3 ps 不是新的 sweep 或 threshold，只是
验证 no-go 不是由 `1.5375 ps` 单一取值造成的。

因此当前 proposed pickup 没有足够的 empirical interstage-scale 依据值得
直接运行；按 preregistered rule 判 `PRECHECK_NO_GO`。

## 2. Secondary termination audit

### Provenance

`R_SEC_LOAD=12 Ω` 不是仅为事后观察而添加的 dummy resistor。R1a native
pickup fixture 的真实 topology 是：

```text
L_TX -- K -- L_SEC(N_SEC, 0)
                     │
                     R_SEC_LOAD=12 Ω → 0
```

它同时提供：

- secondary 的明确 passive current return；
- R1a measured `V(N_SEC)` / `I(R_SEC_LOAD)` 的定义负载；
- 使 R1a read1/read0 transfer ratio 有明确物理 reference。

### Proposed parallel connection

在 R14 point 中，`DCSFQ_BVM.a` 与 `N_SEC` 同节点，故 KCL 应写成：

\[
I_{sec,source}(t)=I_{RSEC}(t)+I_{DCSFQ,a}(t),
\]

其中 `I_DCSFQ,a` 不是固定电阻电流，而是由 `L1 a→node1`、`L2`、B1/B2
network 和内部 bias 共同决定的 dynamic branch current。`R_SEC_LOAD` 不会
自动被 DCSFQ input “取代”。

这会形成相对 R1a 的 intentional double-loading：一个已知 `12 Ω` passive
termination 加一个未知 nonlinear DCSFQ input load。它不是 netlist wiring
错误，但会降低 secondary voltage、改变 reflected primary loading，并可能
改变 B_DET 的 read1/read0 margin。

### Decision

本轮若运行，`R_SEC_LOAD=12 Ω` 应保留，理由是保持 R1a termination provenance
和定义的 passive return；不能为追求较大 DCSFQ voltage 擅自删除。要测试
“DCSFQ input 取代 R1a termination”的拓扑，必须另开一个独立 interface
experiment，不能混入本 single point。

由于本 precheck 已经是 `NO_GO`，实际 double-loaded JoSIM KCL 尚未运行验证，
这里只报告 topology-derived expectation，不声称 measured branch split。

## 3. Observed / Derived / Inference / Unknown

### Observed

- R1a actual read1 secondary current peak `5.564 µA`、voltage peak
  `66.768 µV`。
- R13 actual DCSFQ input read1 `I(L1)` peak `110.200 µA`，ideal C1/C2/C3
  仍无 B3 event。
- R12 `68.4 µA` controlled point 无完整 B3，`300 µA` controlled point 有
 约 `1.03011-turn` bounded B3 local event。
- R1a `R_SEC_LOAD=12 Ω` 是 native physical termination and return branch。

### Derived

- Proposed point `M=0.505964 pH`。
- `X_L1≈6.83 Ω` at the measured `1.5375 ps` local lobe timescale。
- Optimistic DCSFQ L1 branch estimate `≈9.77 µA`；RSEC branch `≈5.56 µA`；
  parallel total `≈15.34 µA`。
- R14 single point lacks demonstrated current/energy scale transfer into the
  DCSFQ input.

### Inference

- The proposed topology likely reuses B_DET discrimination but does not yet
  provide the active current gain that R13 identified as missing.
- Keeping RSEC is source/termination conservative but increases reflected-load
  risk; deleting it would answer a different question.

### Unknown

- Exact nonlinear DCSFQ input impedance and branch current under the secondary
  transient.
- Whether a different secondary voltage/current transfer mechanism can supply
  DCSFQ-scale drive without BVM back-action.
- Whether a future active interstage amplifier/regenerator can preserve read0
  margin and avoid R10-like free-running.

## Stop disposition

`PRECHECK_NO_GO`：不创建 R14 raw CSV，不运行 JoSIM，不接 JTL/T1，不改变
R0b/R1a/R12/R13 evidence，也不 sweep K/L/bias/load。
