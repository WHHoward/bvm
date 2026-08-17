# BVM-S2：固定协议下的 SL 纯电阻负载依赖（修订预注册草案）

> 状态：**DRAFT — waiting for user review**。本文件是科学设计，不是 execution request；不授权修改网表、建立 run root、运行 JoSIM 或接入 receiver。
>
> 设计输入：S1 的最终裁决保持为 raw artifact `VALID`、numerical convergence `INCONCLUSIVE`。S1 的 evidence/provenance authority 是 `JH-20260817-BVM-S1-SEAL-004/C01`，scientific disposition 是 `JH-20260817-BVM-S1-002/C01`。S2 不重开、不修复、也不以任何方式升级 S1。

## 1. 单一研究问题与边界

在**固定** BVM/model closure、两种 operational initialization、单次 read PWL 和固定窗口下，只改变 SL 端外接纯电阻 `R_LD` 时，source-port `V(SL1)` 与 `I(L_SL|XBVM1)` 对 positive/negative initialization 如何改变？

S2 是 `CALIBRATION + CRITICAL + FROZEN` 候选任务。它在一个**指定离散化**下建立各负载的 source-side simulation facts，并检查有限的经验性 terminal affine load-line 是否与这些 facts 相容。它不评价候选电路，也不建立 numerical convergence verdict：0.0125 ps 是本任务的注册工作步长，**不是**已证明收敛的步长。

明确不做：BQ、DCSFQ_BVM、JTL、receiver、`INTERFACE_GATE_V1`、T1、参数调优、电感/电容/偏置/Ic/read-amplitude sweep、logical read0/read1、state-preservation、SFQ/event、fluxoid、hardware 或 universal source-impedance claim。

## 2. 从 S1 继承、但不升级的条件

除外接 `R_LD` 外，下列条件逐字节或逐项固定，并在正式合同中重新复制与哈希：

- `circuits/bvm/bvm_cell.cir`、`circuits/models/jjmit.cir` 的 active closure；cell 内部 `R_SL n_psl N8 12 Ω` **保持不变**。S2 的唯一自变量是外部 `R_LD SL1 0 R`。
- `build/josim-cli` 绝对路径、版本和 SHA-256；170 ps stop time 及 solver/options。
- S1 operational `init_positive` / `init_negative` procedure；它们不是逻辑 1/0。
- 单次 WL+SE read PWL：95 ps 前为零、96 ps 到 `+100 µA`、持有至 105 ps、106 ps 回零。matched zero-read control 保留相同 knot times，但 read 段幅度为零。
- 半开窗：PRE `[80,90)` ps、activity `[94,108)` ps、source `[94,130)` ps、recovery `[108,130)` ps、POST `[140,150)` ps。
- source probe directions：`V(SL1)` 为 `SL1 -> 0`；`I(L_SL|XBVM1)` 为 `N8 -> SL1`。
- inherited operational readiness：每一个 load/init 的 PRE window 内，JM1 与 JM2 的 p2p 均须 `<=0.020 rad`；同一 load 下 positive/negative 的 JM1/JM2 PRE mean-vector `L∞` separation 须 `>=0.100 rad`。这是跨负载可比性/readiness 条件，不是 memory/state Gate。

S1 的 12 Ω / 0.0125 ps waveform、约 `+0.904 mV/+75.34 µA` 与 `-0.317 mV/-26.41 µA` 的 named observations、以及低 residual controls，只能作为 S2 的**可证伪背景预测**。S2 必须 fresh-run 12 Ω，不得把 S1 CSV 拼入 cross-load fit，也不得把 S1 当作 converged anchor。S2 中未解析的单步长离散化影响仍须明示，不能把“未见差异”表述为 load independence 或 numerical convergence。

## 3. 推荐的最小负载集合

| 外接 `R_LD` | 角色 | 选择理由 |
|---:|---|---|
| 1 Ω | finite low-impedance endpoint | 避免直接短路的病态/差条件，同时给出低 Z 端点。 |
| 12 Ω | inherited central reference | 与 S1 fixture 相同，但在 S2 包中重新运行；不引用 S1 CSV 作拟合点。 |
| 25 Ω | second interior discriminator | 使 1–50 Ω endpoint line 有两个独立中间检验点，降低 12 Ω 单点偶然相交或漏掉高负载侧曲率的风险。 |
| 50 Ω | high-impedance endpoint | 与历史约 40 Ω 经验线索同量级，提供高 Z bracket；不是把历史 fit 当作事实。 |

1 Ω 与 50 Ω 仅构造一个 endpoint affine reference；12 Ω 与 25 Ω 各自独立检验该 reference。四点不是 universal circuit model，也不授权向 `R→0` 或 `R→∞` 外推。任何正面措辞均限于 1–50 Ω、指定 initialization/read protocol、指定 feature 或 absolute time，以及注册的 0.0125 ps 工作步长。

## 4. 预注册 run matrix、成本与取消细化的理由

| block | loads | cases | timestep | runs |
|---|---|---|---:|---:|
| primary load matrix | 1, 12, 25, 50 Ω | positive/negative × read/matched-control | 0.0125 ps | 16 |
| **total** | | | | **16** |

本修订选择 16-run 方案，而不采用“3 loads + 12 Ω positive 的 0.00625 ps spot-check”。两种方案的 sample-row 预算近似相同（约 217,600 行）：前者为 `16 × 13,600`，后者为 `12 × 13,600 + 2 × 27,200`。但后者仅检查一个 positive/12 Ω 小分支，既不能证明 0.0125 ps 收敛，也不能覆盖 negative 或 endpoints；四负载方案则提供两个独立的 interior affine checks，直接服务于 S2 的 load-dependence 问题。

因此，取消 spot-check **不**意味着 0.0125 ps 已 numerical-converged，也不改变 S1 的 `INCONCLUSIVE`。S2 不产生 S1 式的 timestep-convergence `PASS/FAIL`；它只报告“at the registered 0.0125 ps working timestep”的 bounded observations。后续若需 resolution claim，必须另行预注册，不能由本矩阵后加 timestep。

按 170 ps / 0.0125 ps，预计约 217,600 CSV rows。实际 wall time、每 run 的 binary identity、closure、raw、stdout/stderr、manifest、hash、actual time axis 和失败 artifacts 必须保存；估算成本不能替代这些记录。

## 5. 观测合同与测量语义

每一 run 输出完整 raw CSV、stdout/stderr、copied inputs/closure/hash、manifest 和 actual time。正式 contract 将冻结如下 probe 字符串、端点与方向：

| role | required probe | direction / purpose |
|---|---|---|
| source | `V(SL1)` | `SL1 -> 0` |
| source | `I(L_SL|XBVM1)` | `N8 -> SL1` |
| input witness | `I(I_WL1)`, `I(I_BL1)`, `I(I_SE1)` | source definitions；证明输入固定 |
| JM1 | direct `P(B_JM1|XBVM1)`, `V(B_JM1|XBVM1)` | `N1 -> n_jm1o`, `vts=+1`, `rd=+1` |
| JM2 | direct `P(B_JM2|XBVM1)`, `V(B_JM2|XBVM1)` | `n_jm2i -> N2`, `vts=+1`, `rd=+1` |
| JS1 | direct `P(B_JS1|XBVM1)`, `V(B_JS1|XBVM1)` | `n_js1p -> N3`, `vts=+1`, `rd=+1` |
| JS2 | direct `P(B_JS2|XBVM1)`, `V(B_JS2|XBVM1)` | `n_js2p -> N6`, `vts=+1`, `rd=+1` |

JM/JS direct P/V only provides same-JJ Josephson-linked consistency. It is an internal read-dynamics witness, not independent state preservation, an event, an SFQ, or a loop-fluxoid measurement. For each witness, report PRE/POST means (raw rad and derived turns) and activity-window phase/area quantities only when the frozen same-JJ, endpoint, direction and actual-time conditions hold.

For every load and initialization, report control-corrected source waveform, signed/absolute primary peak, latency from 96 ps, primary-lobe FWHM when two half-height crossings exist, following opposite-lobe peak and ratio, zero-crossing-bounded lobe duration, signed/absolute `∫Vdt` and `∫Idt`, settling/activity duration, and control residual max/RMS/L1. Lobe segmentation and zero-crossing tie rules must be stated before execution; lobes are never called events.

All cross-load comparisons use literal CSV timestamps parsed as exact decimals. For a comparison row, every participating run must have the same decimal time value; there is no tolerance, interpolation, resampling, cross-correlation or time/peak alignment. A missing exact common timestamp in a registered window is an `INVALID` comparison artifact, not an invitation to change grids.

## 6. Terminal load-line: an observation, not an internal impedance model

Use matched-control-corrected source traces `Ṽ_L(t)=V_read,L(t)-V_control,L(t)` and `Ĩ_L(t)=I_read,L(t)-I_control,L(t)`. At exact common absolute timestamps, construct an endpoint reference from 1 Ω and 50 Ω:

\[
\hat R(t)=-\frac{\tilde V_{50}(t)-\tilde V_1(t)}{\tilde I_{50}(t)-\tilde I_1(t)},\qquad
\hat V_{th}(t)=\tilde V_1(t)+\hat R(t)\tilde I_1(t).
\]

Evaluate **both** interior loads separately:

\[
e_L(t)=\tilde V_L(t)-[\hat V_{th}(t)-\hat R(t)\tilde I_L(t)],\quad L\in\{12,25\}\ \Omega.
\]

Eligibility requires `|Ĩ50-Ĩ1| >= 0.5 µA` and `|Ṽ50-Ṽ1| >= 5 µV`. These are task-local conditioning floors, not hardware, interface, or physical tolerances. For every eligible timestamp, report `e12`, `e25`, their normalized residuals, and the full compatible/not-compatible intervals under the frozen band `|eL| <= max(5 µV, 0.01 |Ṽ50-Ṽ1|)`. This is an observed **terminal affine compatibility** diagnostic only. A non-compatible result is useful evidence that this affine approximation is not supported at that named time or feature; it is not a circuit `FAIL`.

Separately report signed simultaneous source `V,I` feature pairs. Because their peaks may occur at different times across loads, a fit through signed peak pairs is only a **peak-envelope load-line**, never an instantaneous Thevenin resistance. `V(SL1)-R_LD I(L_SL|XBVM1)` is port-QA for a pure resistor, not evidence for source impedance.

## 7. Internal trajectory / load-back-action observation layer

The terminal calculation in §6 must not be interpreted as a fixed internal Thevenin source: BVM is a stateful nonlinear JJ network. S2 therefore measures whether changing `R_LD` is associated with a resolved change in internal, control-corrected read dynamics.

For each direct witness `J∈{JM1,JM2,JS1,JS2}`, load `L`, initialization and exact timestamp, construct:

\[
p^*_{J,L}(t)=[P^{read}_{J,L}(t)-\overline{P}^{read}_{J,L,PRE}]-[P^{ctrl}_{J,L}(t)-\overline{P}^{ctrl}_{J,L,PRE}],
\]

\[
v^*_{J,L}(t)=V^{read}_{J,L}(t)-V^{ctrl}_{J,L}(t),\qquad a^*_{J,L}(t)=\Phi_0^{-1}\int_{94\,ps}^{t}v^*_{J,L}(\tau)d\tau,
\]

where `Φ0=2.067833848e-15 Wb`, actual-time trapezoidal integration is used, and `a*` has the same frozen direction as `P`. `p*/(2π)` and `a*` are compared as complete paths, not merely endpoints; agreement remains a same-JJ check, not independent event evidence.

For comparisons with 12 Ω and adjacent pairs `1↔12`, `12↔25`, `25↔50` and full span `1↔50`, report in each PRE/activity/recovery/POST window:

- raw PRE/POST P mean and p2p; cross-load initialized-vector dispersion;
- control-corrected phase and voltage path max-absolute difference and actual-time RMS difference;
- extrema, lobe sign/order, phase excursion, `a*` path, and activity-only total variation; and
- control-envelope max/RMS differences for the same probes and windows.

`RESOLVED_LOAD_ASSOCIATED_INTERNAL_TRAJECTORY_DIFFERENCE` is a descriptive, task-local label—not a physical state or mechanism verdict—and requires all of:

1. exact-time, closure, control and input-witness QA pass;
2. the cross-load PRE mean-vector dispersion is reported. If any JM1/JM2 component's load-to-12 Ω PRE mean difference exceeds `max(0.020 rad, 5× the corresponding cross-load control PRE-mean difference)`, emit `LOAD_EFFECT_ON_INITIALIZATION_OR_UNRESOLVED`; a later difference may then not be attributed exclusively to read-time back-action;
3. for **two physically distinct** direct JJ witnesses, a load-to-12 Ω path difference persists for at least 0.25 ps and exceeds both five times that witness's cross-load control envelope and the registered numerical floors: phase max/RMS `0.020/0.005 rad`, voltage max/RMS `5/1 µV`; and
4. the corresponding same-JJ `p*` and `a*` paths have the registered direction consistency (no sign reversal attributable solely to endpoint cancellation).

The floors and five-times rule are S2 **effect-size discriminators** to avoid calling control-scale numerical residue “material”; they are neither universal numerical tolerances nor physical/interface acceptance bands. If the PRE state already differs across loads, report `LOAD_EFFECT_ON_INITIALIZATION_OR_UNRESOLVED` rather than attributing any later difference exclusively to read-time back-action. If conditions 1–4 are not met, report the complete effect-size table without claiming absence of internal influence. These labels never establish state-preservation, an SFQ/event, fluxoid, logic, or a confirmed mechanism.

## 8. Validity, stop rules, and allowed conclusions

Artifact is `INVALID` for closure/binary/probe/direction/hash failure, missing matched control, NaN/Inf, nonmonotonic/duplicate time, solver failure, or an uncovered registered window. A named analysis is `INCONCLUSIVE` if its readiness/control separation/exact timestamp matching/input witness/conditioning requirements fail. A valid nonlinear result can still establish per-load facts and show that the terminal affine description is not supported at named times; nonlinearity itself is not an invalid artifact.

Strongest possible positive wording:

> At the registered 0.0125 ps working timestep, in the copied BVM closure, fixed operational initialization/read protocol, 1–50 Ω pure-resistor range, and named feature or timestamp subset, the observed terminal source V–I data are compatible with a local empirical affine load-line approximation.

If §7's discriminator passes, the strongest added wording is only that a registered control-corrected internal trajectory difference was resolved at the named load/window and working timestep. Neither wording establishes numerical convergence, universal BVM source impedance, hardware specification, receiver compatibility, BQ/DCSFQ_BVM route viability, logical read0/read1, state preservation, SFQ/fluxoid behavior, or an Interface Gate.

## 9. Prerequisites before any issuance

1. Freeze a new unique run ID and no-overwrite path.
2. Freeze a METRIC_SPEC_V2 §11.1-complete analysis schema/provenance envelope; do not copy S1 A02's missing metadata, reversed residual sign or non-frozen `Phi0` constant.
3. Freeze JS1/JS2 exact direct P/V probe syntax in generated netlists and confirm headers at preflight.
4. Freeze primary/opposite lobe, zero-crossing and half-height tie rules.
5. Freeze the 16-run maximum, with no additional timestep or load allowed.

No exploratory task is currently required: the active closure, source port, initialization, stimulus, load insertion point and probes are concrete. A preflight mismatch stops the later execution task rather than expanding scope.
