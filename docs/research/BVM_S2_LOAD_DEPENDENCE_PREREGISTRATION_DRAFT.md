# BVM-S2：固定协议下的 SL 纯电阻负载依赖（预注册草案）

> 状态：**DRAFT — waiting for user review**。本文件是科学设计，不是 execution
> request，不授权修改网表、生成 run root、运行 JoSIM 或接入 receiver。
>
> 设计输入：S1 的最终裁决为 raw artifact `VALID`、numerical convergence
> `INCONCLUSIVE`；其唯一 evidence/provenance authority 是
> `JH-20260817-BVM-S1-SEAL-004/C01`，科学 disposition 为
> `JH-20260817-BVM-S1-002/C01`。

## 1. 单一研究问题与边界

在**固定** BVM/model closure、两种 operational initialization、单次 read PWL 和
固定窗口下，只改变 SL 端外接纯电阻 `R_LD` 时，source-port
`V(SL1)` 和 `I(L_SL|XBVM1)` 对 positive/negative initialization 如何改变？

S2 是 `CALIBRATION + CRITICAL + FROZEN` 候选任务。它仅建立各已测负载下的
source-side simulation facts，并检验一个有限、经验性的仿射 load-line 描述是否与
已测数据相容。它不评价候选电路。

明确不做：BQ、DCSFQ_BVM、JTL、receiver、`INTERFACE_GATE_V1`、T1、参数调优、
电感/电容/偏置/Ic/read-amplitude sweep、logical read0/read1、state-preservation、
SFQ/event、fluxoid、hardware 或 universal source-impedance claim。

## 2. 从 S1 继承、但不升级的条件

除外接 `R_LD` 外，下列条件逐字节或逐项固定，并在正式合同中重新复制与哈希：

- `circuits/bvm/bvm_cell.cir`、`circuits/models/jjmit.cir` 的 active closure；
  cell 内部 `R_SL n_psl N8 12 Ω` **保持不变**。S2 的唯一自变量是外部
  `R_LD SL1 0 R`。
- `build/josim-cli` 绝对路径、版本和 SHA-256；170 ps stop time 及 solver/options。
- S1 operational `init_positive` / `init_negative` procedure；它们不是逻辑 1/0。
- 单次 WL+SE read PWL：95 ps 前为零、96 ps 到 `+100 µA`、持有至 105 ps、
  106 ps 回零。matched zero-read control 保留相同 knot times，但 read 段幅度为零。
- 半开窗：PRE `[80,90)` ps、activity `[94,108)` ps、source `[94,130)` ps、
  POST `[140,150)` ps。
- source probe directions：`V(SL1)` 为 `SL1 -> 0`；
  `I(L_SL|XBVM1)` 为 `N8 -> SL1`。

S1 的 12 Ω / 0.0125 ps waveform、约 `+0.904 mV/+75.34 µA` 与
`-0.317 mV/-26.41 µA` 的 named observations、以及低 residual controls，只能作为
S2 的**falsifiable context prediction**。因 S1 未建立数值收敛，S2 必须 fresh-run
12 Ω，不得把 S1 CSV 拼入 cross-load fit，也不得把 S1 当作 converged anchor。

## 3. 推荐的最小负载集合

| 外接 `R_LD` | 角色 | 选择理由 |
|---:|---|---|
| 1 Ω | finite low-impedance endpoint | 避免直接短路的病态/差条件，同时给出低 Z 端点。 |
| 12 Ω | central reference | 与 S1 fixture 相同，但 S2 重新运行以提供同一实验包中的第三点。 |
| 50 Ω | high-impedance endpoint | 与历史约 40 Ω 经验线索同量级，提供高 Z bracket；不是把历史 fit 当作事实。 |

三个点是最小辨识集合：两个点可以确定一个仿射
`V = V_th - R_th I` 关系；第三点可直接暴露在该协议和负载范围内的非仿射性。
不使用 `R=0`、开路或 reactive load；结果不得向 `R→0` 或 `R→∞` 外推。结果只可称
为 1–50 Ω、具体 initialization/read protocol/feature/time 下的局部经验近似。

## 4. 预注册 run matrix 与成本

主工作 timestep 是 **0.0125 ps**：它是 S1 最细的、已保存 source 观察点，能避免把
S1 的粗 0.05 ps under-resolution 当作 load effect；但它本身不等于 S1 convergence。

| block | loads | cases | timestep | runs |
|---|---|---|---:|---:|
| primary load matrix | 1, 12, 50 Ω | positive/negative × read/matched-control | 0.0125 ps | 12 |
| narrowly scoped numerical spot-check | 12 Ω | positive read + its matched control | 0.00625 ps | 2 |
| **total** | | | | **14** |

这个 spot-check 只针对 S1 在 positive branch 的 0.025→0.0125 ps RMS 未通过风险：
它检查 12 Ω positive descriptor 的符号、primary-lobe identity、FWHM existence 和
descriptor order 是否在再细一步发生离散改变。它不重新开启 S1、不给 S2 数值
convergence `PASS`，也不触发自适应第四/第五 timestep。若它暴露离散变化，S2 的
跨负载 shape/fit interpretation 为 `INCONCLUSIVE`；若未暴露，只说明该有限 descriptor
guard 未发现该风险。

按 170 ps / 0.0125 ps，primary matrix 约 163,200 sample rows；spot-check 约 54,400
rows，总约 217,600 rows，约为 S1 采样行数的 2.3 倍。实际 wall time 需在执行前记录，
不得以估计值替代。

## 5. 观测合同

每一 run 均输出完整 raw CSV、stdout/stderr、copied inputs/closure/hash、manifest 和
actual time。正式 contract 将冻结如下 P/V probe 字符串、端点与方向：

| role | required probe | direction / purpose |
|---|---|---|
| source | `V(SL1)` | `SL1 -> 0` |
| source | `I(L_SL|XBVM1)` | `N8 -> SL1` |
| input witness | `I(I_WL1)`, `I(I_BL1)`, `I(I_SE1)` | source definitions；证明输入固定 |
| JM1 | direct `P(B_JM1|XBVM1)`, `V(B_JM1|XBVM1)` | `N1 -> n_jm1o`, `vts=+1`, `rd=+1` |
| JM2 | direct `P(B_JM2|XBVM1)`, `V(B_JM2|XBVM1)` | `n_jm2i -> N2`, `vts=+1`, `rd=+1` |
| JS1 | direct `P(B_JS1|XBVM1)`, `V(B_JS1|XBVM1)` | `n_js1p -> N3`, `vts=+1`, `rd=+1` |
| JS2 | direct `P(B_JS2|XBVM1)`, `V(B_JS2|XBVM1)` | `n_js2p -> N6`, `vts=+1`, `rd=+1` |

JM/JS direct P/V provides only same-JJ Josephson-linked consistency. It is an
internal read-dynamics witness, not independent state preservation, an event,
an SFQ, or a loop-fluxoid measurement. For each witness, report PRE/POST
means (raw rad and derived turns) and activity-window phase/area quantities
only if the frozen same-JJ, endpoint, direction and actual-time conditions hold.

For every load and initialization, report control-corrected source waveform,
signed/absolute primary peak, latency from 96 ps, primary-lobe FWHM when two
half-height crossings exist, following opposite-lobe peak and ratio,
zero-crossing-bounded lobe duration, signed/absolute `∫Vdt` and `∫Idt`,
settling/activity duration, and control residual max/RMS/L1. Lobe segmentation
and zero-crossing tie rules must be stated before execution; lobes are never
called events.

## 6. Cross-load local empirical approximation

At exact common absolute timestamps, without interpolation, resampling,
cross-correlation or peak alignment, calculate from 1 Ω and 50 Ω endpoint data:

\[
\hat R(t)=-\frac{V_{50}(t)-V_1(t)}{I_{50}(t)-I_1(t)},\qquad
\hat V_{th}(t)=V_1(t)+\hat R(t)I_1(t).
\]

Use the 12 Ω data only as the third-point test:

\[
e_{12}(t)=V_{12}(t)-[\hat V_{th}(t)-\hat R(t)I_{12}(t)].
\]

This calculation is eligible only where the endpoint spans satisfy
`|I50-I1| >= 0.5 µA` and `|V50-V1| >= 5 µV`; these are fresh S2
conditioning floors, not hardware or interface tolerances. At each eligible
timestamp, call the local affine approximation *compatible* only when

\[
|e_{12}(t)| \le \max(5\ \mu V,\ 0.01|V_{50}(t)-V_1(t)|).
\]

Report the entire eligible-time residual distribution and intervals that are
compatible/not-compatible; do not collapse it into a whole-waveform PASS.
At a qualified point above the residual band, the bounded result is
`affine approximation NOT_SUPPORTED at that time/feature`, not circuit FAIL.
If endpoint conditioning fails, report `INCONCLUSIVE at that time` rather than
dividing by a small current span.

Separately report simultaneous source `V,I` feature pairs. Because their peaks
may occur at different times across loads, a fit through signed peak pairs is
only a **peak-envelope load-line**; it must never be named instantaneous
Thevenin resistance. `V(SL1)-R_LD I(L_SL|XBVM1)` is port-QA for a pure resistor,
not evidence for source impedance.

## 7. Validity, stop rules, and allowed conclusions

Artifact is `INVALID` for closure/binary/probe/direction/hash failure, missing
matched control, NaN/Inf, nonmonotonic/duplicate time, solver failure, or an
uncovered registered window. S2 load-dependence interpretation is
`INCONCLUSIVE` if readiness/control separation/exact timestamp matching fails,
the 12 Ω spot-check changes its registered discrete descriptor, or a required
V–I point is ill-conditioned. A valid nonlinear result can still establish
per-load observations and show the local affine description is not supported
at named times; nonlinearity itself is not an invalid artifact.

Strongest possible positive wording:

> In the copied BVM closure, fixed operational initialization/read protocol,
> 1–50 Ω pure-resistor load range, declared timestep and named waveform feature
> or timestamp subset, the measured source V–I data are compatible with a local
> empirical affine load-line approximation.

Even this does **not** establish universal BVM source impedance, hardware
specification, receiver compatibility, BQ/DCSFQ_BVM route viability, logical
read0/read1, SFQ/fluxoid behavior, or an Interface Gate.

## 8. Prerequisites before any issuance

1. Freeze a new unique run ID and no-overwrite path.
2. Freeze a METRIC_SPEC_V2 section 11.1-complete analysis schema/provenance
   envelope; do not copy S1 A02's missing metadata, reversed residual sign or
   non-frozen Phi0 constant.
3. Freeze JS1/JS2 exact direct P/V probe syntax in generated netlists and
   confirm headers at preflight.
4. Freeze primary/opposite lobe, zero-crossing and spot-check descriptor rules.
5. Freeze the 14-run maximum and no-extension rule.

No exploratory task is currently required: the active closure, source port,
initialization, stimulus, load insertion point and probes are concrete. A
preflight mismatch stops the later execution task rather than expanding scope.
