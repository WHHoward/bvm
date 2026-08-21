# R1b differential secondary-to-output-JJ activation Exploration

日期：2026-08-21；层级：Exploration；父 checkpoint：`7ea6373c43edbb47ba90a8365d696e899a7c02c1`

## Verdict

**R1b FAIL（artifact-valid physical failure）。**

本轮唯一必要条件是 canonical read1 在 `B_OUT` 上出现至少一个、由同一
`B_OUT` 的连续/单调 phase trajectory 与同段 voltage area 同时支持的完整
`2π` transition。四个 matched case 的 raw CSV 均有效，然而按允许的一次
root-cause correction 重新运行后，read1 的最大 `B_OUT` 单调段仅为
`0.0220583499` turn，same-JJ voltage area 为 `0.0220676540` turn。因此
没有 output-JJ complete transition，R1b 不能 PASS。

这不是把 `I > Ic` 或 voltage peak 当作 switching 判据：`B_OUT` 确实出现了
state-dependent differential transient，但 phase/area criterion 未闭合。
read0 和两个 `READ=0` control 没有完整 `B_OUT` transition，也没有
free-running；这些是通过的子条件，不能抵消 read1 activation 的失败。

## 1. Topology and KCL/KVL

保留 canonical BVM、canonical `SL` route、R0b/R1a series pickup 和
`B_TRIG` operating point。修正后的 receiver 是：

```text
canonical SL -- R_IN(12 ohm) -- L_TX(0.20 pH) -- B_TRIG -> ground
                                      || K=0.80
                          L_SEC -> N_SEC_RTN -- R_SEC_LOAD(12 ohm) -> ground
                              N_SEC -- B_OUT -> ground
                              N_SEC -- R_OUT_DAMP(100 ohm) -> ground
                              independent I_OUT_BIAS(0 -> N_SEC, 7 uA)
```

`B_OUT` 直接连接 `N_SEC` 到 ground，所以测得的 `V(B_OUT)` 是
`V(N_SEC)-V(0)`；它不是两个跟随节点之差，也没有 common-mode observer
的悬浮参考。修正 fixture 中显式采用以下电流方向：所有从 `N_SEC` 流向
ground/return 的支路电流为正：

```text
at N_SEC: i_LSEC + i_BOUT + i_RDAMP - I_BIAS = 0
i_BOUT = I_BIAS - i_LSEC - i_RDAMP
at N_SEC_RTN: i_LSEC = i_RSEC_LOAD
```

因此 mutual transient 通过 `L_SEC` 进入 `N_SEC` 的 KCL；它会调制直接
跨接 `N_SEC`-ground 的 `B_OUT` current，而不会再被构造成
`V(N_OUT)-V(N_SEC)` 的 common-mode 数值零。

### Initial point and the one permitted correction

初始点使用了 `L_SEC N_SEC 0` 与 `R_SEC_LOAD N_SEC 0` 的 parallel return。
它虽然让 `B_OUT` 参考 ground，但理想电感在 DC 是 zero-voltage branch，约
`6.599 uA` 的独立 `7 uA` bias 被该 branch 分流，初始 read1 的
`I(B_OUT)` 只有约 `0.401 uA` 的 pre-bias，而不是预期的 7 uA。这个
KCL 失败是唯一允许拓扑修正的明确原因。

修正为 `L_SEC N_SEC N_SEC_RTN` 串联 `R_SEC_LOAD N_SEC_RTN 0`，只改变
secondary 的 DC return，不改变 `AREA`、output bias 或 damping。修正后
`B_OUT` 的 pre-bias 恢复为约 `7 uA`，且 read1 `I(B_OUT)` 在 activity
window 内约为 `5.165--8.240 uA`；这些数值仅作 branch/activity diagnostics，
不是 event count。

## 2. Frozen parameters and actual JJ semantics

| block | parameters |
|---|---|
| trigger `B_TRIG` | `AREA=.50`, `Ic=50 uA`, `RN=32 ohm`, `R0=320 ohm`, `C=35 fF`, bias `15 uA` |
| pickup | `R_IN=12 ohm`, `L_TX=.20 pH`, `L_SEC=2 pH`, `K=.80`, `M=sqrt(K L_TX L_SEC)=.5059644 pH`, `R_SEC_LOAD=12 ohm` |
| output `B_OUT` | `AREA=.10`, `Ic=10 uA`, `RN=160 ohm`, `R0=1600 ohm`, `C=7 fF`, bias `7 uA`, `R_DAMP=100 ohm` |
| solver | `build/josim-cli` v`2.7.2837d13`; SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`; requested `dt=.0125 ps`, stop `170 ps` |

`jjmit` 的实际 AREA semantics 来自本轮保存的 model/source fixture：`Ic` 和
`C` 随 AREA 相乘，`RN` 和 `R0` 按 AREA 除。故 output intrinsic
`beta_c≈5.4450545`；`RN || 100 ohm≈61.538 ohm` 时的并联 shunt diagnostic
约为 `0.8054814`。这些 beta/current 数值用于 topology/operating-point
物理诊断，不替代 phase-transition 判据。

本轮没有继续 `AREA`/bias/shunt sweep；只执行 preregistered initial point
和一次 KCL-driven series-return correction。

## 3. Matched four-case evidence

修正点 `diff-a010-b07-r100-series-return` 的最大同向单调段如下。所有
phase 是 raw `P(...)` radians 经 `delta/(2*pi)` 转成 turns；voltage area
使用同一个 JJ、同一段 endpoint 和 raw CSV 实际 timestamp。

| case | `B_TRIG` segment (time, phase / area turns) | `B_OUT` segment (time, phase / area turns) | `V(N_SEC)` activity peak | `I(R_SEC_LOAD)` activity peak | result |
|---|---|---|---:|---:|---|
| read1 | 102.950--110.7125 ps; `3.9168206565 / 3.9168478680` | 104.650--107.125 ps; `0.0220583499 / 0.0220676540` | `75.0610 uV` | `2.0960 uA` | BTRIG complete; BOUT incomplete |
| read0 | 106.0875--108.2125 ps; `0.1848812892 / 0.1849046337` | 106.0875--107.3875 ps; `0.0051599306 / 0.0051622416` | `13.0214 uV` | `0.6203 uA` | no complete transition |
| logical1 + READ=0 | 94.8125--96.350 ps; `0.0000842407 / 0.0000842502` | 94.700--96.0625 ps; `1.7507e-7 / 1.5976e-7` | `0.4642 nV` | `6.062 pA` | inactive |
| logical0 + READ=0 | 94.0375--95.575 ps; `0.0002541864 / 0.0002542299` | 94.4875--95.9125 ps; `2.5465e-7 / -2.4088e-7` | `0.6648 nV` | `8.797 pA` | inactive |

`B_OUT` read1 segment 的 phase-area residual 为 `+9.3041e-6 turn`，read0
为 `+2.3110e-6 turn`；两者说明同-JJ voltage integration 与 observed
subturn trajectory 相符，但都远小于 1 turn，更不满足 2π。read1 的
`V(B_OUT)` activity range 为约 `-75.061--52.663 uV`，`I(B_OUT)` 为
约 `5.165--8.240 uA`；这些是可见 transient，不是 switching success。

read1 output post window `130--170 ps` 的 phase range 约 `0.0008344 turn`，
read0 约 `0.0001055 turn`，control 约为零；在本次未发生 output event 的
前提下，未观察到 output free-running。由于没有 output complete event，
“event 后 reset”不是可宣称的 one-shot 结果。

## 4. R0b/BVM guard and back-action

与 accepted R1a raw baseline 的独立 comparison：

- read1 `B_TRIG`: R1a `3.9437708405` turn，loaded correction
  `3.9168206565` turn；仍为 complete segment。
- read0 `B_TRIG`: `0.1847573234` → `0.1848812892` turn；仍不 complete。
- 两个 `READ=0` control 均保持远低于 1 turn。
- loaded read1/read0 `SL` peak 分别约 `1.882218 mV` / `0.441924 mV`；
  `N6` peak 分别约 `2.117676 mV` / `0.720822 mV`。与 R1a 的独立
  comparison 没有显示 R0b trigger discrimination 被破坏。
- secondary 的 read1/read0 ratio：电压约 `5.764`，return-current
  activity 约 `3.379`；相对两个 controls 分别超过 `1e5` 与 `2e5` 量级。

`JM1/JM2` 的 logical-sign guard 在四个 case 都通过。修正 read1 的
post-minus-pre 为：`JM1 +0.0005818705 turn`，`JM2 -0.0004995078 turn`；
read0 为 `JM1 -0.0000035014`、`JM2 -0.0006365084 turn`。这些证明所选
窗口内没有 logical-sign inversion，但不等价于“storage state 完全未受
影响”：R1a read1 的 `JM2` drift 约 `+0.005032 turn`，本轮修正后定量轨迹
不同，故 exact state preservation 仍是未验证项。

## 5. Artifact and audit status

- 四个 correction CSV 各 `13,599` rows，时间 `0--169.9875 ps`，finite、
  strictly increasing、无缺列；实际 timestamp `dt` 为
  `0.0125--0.025 ps`，分析使用实际 timestamp。
- `analysis/independent-crosscheck.json` 对四个 case 的 phase、same-JJ
  area、complete flag、secondary 与 JM1/JM2 全部 comparison pass。
- 首次初始点 invocation 因 case fixture 错实例化为
  `SERIES_PICKUP_OUTPUT` 而未产生 raw CSV；stdout/stderr 和
  `analysis/invalid-run-01-analysis.json` 原样保留，随后修正后的 initial
  valid run 使用 `run-02`，没有覆盖 invalid artifact。
- canonical BVM fixture 只读复制并 hash-bound；canonical topology 未修改。

## 6. Evidence labels

### Observed

raw CSV 中的 `P/V/I(B_TRIG)`、`P/V/I(B_OUT)`、`V(N_SEC)`、secondary return
current、`SL/N6`、`JM1/JM2` 与四 case 的 QA/phase/area metrics；以及
R1a-vs-loaded independent comparison。

### Derived

`turn = delta_phase_rad/(2*pi)`；同段 voltage area；KCL 中的 output
branch relation；JJ 的 AREA-scaled `Ic/C`、inverse-area `RN/R0`；actual
CSV timestamp 的 dt range；上述 ratio 和 post-minus-pre values。

### Inference

series-return correction 确实把 receiver 从初始 bias-diversion 状态改为
真正以 `N_SEC`-ground 为参考、具有 state-dependent B_OUT transient 的
拓扑；但在固定 `AREA=.10`, `7 uA`, `R_DAMP=100 ohm` 下，read1 transfer
仍不足以完成 output-JJ phase transition。因此当前失败点是“differential
drive 已建立但 activation margin 未闭合”的 bounded result，而不是旧的
common-mode numerical-zero 复现。

### Unknown / not established

没有证明 output JJ 的 exactly-one 行为、self-quench、downstream SFQ/JTL
delivery、不同 output AREA/bias/damping 的可行 operating window、长时间
storage fidelity，或 phase transition 的 timestep-convergence gate。本轮
也没有实施 R1c/JTL，不能把任何 local phase activity 称为 downstream SFQ。

## 7. Scope closure

本 checkpoint 到此停止：R1b 为 **FAIL**；不升级 Candidate，不启动 R1c，
不接 JTL，不修改 canonical BVM，也不回到 parallel `L_Q-R_Q` topology。
所有 raw、input、command/log、analysis、review 与 hash inventory 均保存在
本目录。
