# Experimental Contract

状态：`ACTIVE / V1`（2026-09-09 evidence-first amendment；2026-10-09 前瞻性风险分级修订）

本合同适用于本仓库中的所有 simulation experiments、replay experiments、
parameter studies、read-only raw analyses 和 evidence-packaging tasks。它
冻结实验执行、证据保存、可视化和结论边界；它不追溯改写历史实验、raw、
deck、报告、指标定义或科学结论。

本合同是强制规则，不是建议。除非用户明确指出要覆盖哪一条具体规则，
执行者 MUST 遵守本合同。若 `docs/HANDOVER.md`、`memory/project-todo.md`、
冻结 metric/source/spec 或任务合同有更严格的限制，执行者 MUST 采用更严格
的限制。任何显式覆盖 MUST 被记录在该任务的 PREFLIGHT 和 provenance 中。

## I. ROLE

默认角色是 **Experimental Operator + Evidence Packager**。

执行者 MUST：

- inspect repository、当前 HEAD 和 authoritative sources；
- preregister the exact experiment；
- create the registered decks and probes；
- execute exactly the authorized solves；
- preserve raw evidence；
- perform artifact and mechanical/registered-arithmetic QA；
- generate only the standard descriptive visualization by default；
- package the immutable evidence and perform package QA；
- preserve provenance；
- report evidence readiness without scientific interpretation。

除非用户在当前 review 阶段明确给出
`SCIENTIFIC_REVIEW_AUTHORIZED`，执行者 MUST NOT 进行 scientific analysis、
root-cause analysis、mechanism interpretation、parameter ranking、winner
selection、next-experiment design、post-hoc threshold invention 或额外 solve。
执行成功不等于 artifact 有效、物理结论成立或 Gate 通过；`PASS`、`FAIL`、
`INCONCLUSIVE` 和 artifact `INVALID` MUST 分开记录。

`MECHANICAL_QA` 可以包含固定定义的纯数值 consistency check，例如 KCL/KVL、
series-current residual、actual-grid arithmetic 和 phase `rad/(2*pi)` display
conversion；这些操作不构成 scientific interpretation。

## II. PREFLIGHT

每一个 physical solve experiment MUST 先生成该实验目录中的 `PREFLIGHT.md`。
每个新的 experiment directory 的 `PREFLIGHT.md` MUST 原样包含：

> This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

Preflight 是 **automatic execution gate**，不是等待用户手工批准的 gate：

1. Codex 或执行者 MUST 先生成 `PREFLIGHT.md`。
2. 执行者 MUST NOT 等待用户人工 approve 才执行已经授权的 runs。
3. machine preflight `PASS` 后，执行者 MUST 自动执行且只能执行已授权的 run matrix。
4. machine gate `FAIL` 时，执行者 MUST 停止并报告，不能带着失败状态运行物理仿真。
5. 用户/assistant MUST 在结果产生后共同审阅 PREFLIGHT 和 results；结果审阅
   不是 preflight 的隐式补票。

`PREFLIGHT.md` MUST 冻结至少：

- HEAD；
- authoritative circuit sources、include/model closure 和 source identity；
- exact topology；
- exact parameters、parameter provenance 和 perturbation；
- exact stimulus、polarity、load 和 controls；
- exact timing、time step、stop time、save start 和 analysis windows；
- exact authorized run matrix；
- exact probes 及其端点、方向和单位；
- exact preregistered metrics、thresholds 和 tolerances；
- exact output paths 和 expected raw filenames；
- known `UNKNOWN`s、interpretation ceiling 和 prohibited follow-ups。

Read-only existing-raw analysis MUST also have a machine-readable analysis scope
and MUST explicitly declare that no solver, raw mutation, circuit change,
parameter change or timing change is authorized.

## II-A. EXPERIMENT RISK LEVEL

每个未来 work unit MUST 在执行前登记 `experiment_risk_level`：
`QUICK | NORMAL | FORMAL`。这不是 research tier
(`Exploration/Candidate/Authority`)，也不是协作任务风险
(`NORMAL/CRITICAL`)；MUST NOT 使用裸字段 `risk` 混写这些维度。

- `QUICK`：低风险、方向性或小参数/激励改动；只回答预注册问题和最小
  run matrix。QUICK 不可作为 Candidate、Authority、Gate、metric freeze
  或 paper-level claim 的充分依据。
- `NORMAL`：有界的常规研究，包括新拓扑、4×4 阵列或多级链路。执行前冻结
  当前问题需要的 focus probes、窗口、QA 和 interpretation ceiling；默认不
  要求 Formal 独立审计。
- `FORMAL`：Authority、系统 Gate、metric freeze、scientific baseline、route
  selection 或 paper-level quantitative claim。必须有冻结输入闭包、claim-
  relevant full probe coverage、问题需要的 controls/convergence 和独立
  evidence audit。

Authority MUST 使用 FORMAL。Candidate 的 clean rerun 与独立机械复算要求继续
有效。执行风险级别不授予科学解释或额外 solve；结果升级必须经新预注册和授权，
不得追溯重标旧 run。风险级别也不能覆盖冻结的 task/source/metric/handoff
合同；更严格要求优先。当前通用 `scripts/bvm-exp.py` schema/runner 仍仅支持
QUICK；不得将其 QUICK 产物事后标成 NORMAL 或 FORMAL。自定义平台可在 task-local
PREFLIGHT/manifest 中登记其风险级别与验证范围。

本修订仅适用于生效后的新 work unit。历史实验、raw、ZIP、QA、review、状态与
科学结论保持原样，不因新分级重分类、补票或升级。所有级别继续受 exact
authorized runs、raw immutability、provenance、units/directions、evidence labels、
measurement/SFQ 边界、package integrity 和 no-silent-follow-up 约束。

## III. EXACTLY AUTHORIZED RUNS

执行者 MUST 只运行用户明确授权的 solve matrix。执行者 MUST NOT：

- 自动 sweep；
- 自动追加 experiment 或 condition；
- “顺便再跑一个”；
- 因为结果奇怪就改参数重跑；
- 因为 physical failure 就调 physics；
- 自动改变 receiver、BVM、load、bias、timing 或 topology。

若错误属于 tool/path/include/format error，执行者 MAY 修复并重试，但前提是
registered physics、run matrix 和 interpretation ceiling 完全不变；每一次
失败 attempt MUST 保留 command、HEAD、输入 provenance、日志和 artifact 状态。
若错误属于 physical/model failure，执行者 MUST 停止并报告，MUST NOT 调参或
偷偷扩大 scope。

## IV. RAW IMMUTABILITY

Raw 是最高优先级证据。每一个 physical solve MUST 产生独立 raw；raw 文件
MUST NOT 被覆盖、静默删除或就地修订。执行者 MUST：

- 计算并保存每个 raw 的 SHA-256；
- 在 analysis 前后比较 raw hash；
- 保存 sample count；
- 保存 actual time range；
- 检查 time monotonicity；
- 记录 irregular time steps 和实际 stored grid；
- 使用 actual stored time values 做 integration。

除非 transformation 本身被用户明确授权并在 preflight 注册，执行者 MUST NOT
对 raw 做 interpolation、smoothing、resampling、scaling、time shifting、
silent sign correction 或 silent unit correction。任何获授权的 transformation
MUST 以 machine-readable registry 保存，且原始 raw MUST 保留不动。

## V. PROBE POLICY

所有级别 MUST 在 solve 前冻结 probe manifest，记录 signal、节点/器件端点、
方向、单位、用途和缺失时的 claim consequence。MUST NOT 在看过结果后补造 probe
语义或扩大 interpretation ceiling。

QUICK 和 NORMAL MAY 使用预注册的 `focus_probe_set`。其覆盖 MUST 与主要问题
相称，至少包括需要判断的 input boundary、目标内部状态/改变器件、output
boundary、注册 controls/quiet branches，以及已注册同 JJ arithmetic 所需的
P/V 证据。未被 probe 支持的结论 MUST 标为 `UNKNOWN` 或 `INCONCLUSIVE`；不得
把少量 endpoint 伪装成 full internal evidence。NORMAL 的 focus 选择及理由
必须在 solve 前冻结。

FORMAL MUST 使用 claim-relevant full probe coverage。QB 的完整覆盖继续包括 input
boundary、LIN、BJS、L1、BJ1、RJ1、L2、IB、BJ2、RJ2、L3 与 QBOUT；JTL 声明
必须保留所有被声明级别的相关 P/V/I，而不能只保留 JTL1/JTL6；BVM 需覆盖
claim 所需 storage core、R-loop、output path、shared boundary、controls 和
quiet branches。JJ 保存可用 P/V/I；inductor/resistor 按 claim 需要保存可用
I/V，缺失列标 `UNKNOWN`，不得伪造。

Read-only existing-raw analysis 只能使用现有 raw columns；缺失 probe 不授权
新 solve，也不得以推断补齐。

## VI. VISUALIZATION IS REQUIRED EVIDENCE

实验交付 MUST NOT 只有 `raw.csv + metrics.json + RESULT_BRIEF.md`。每个
physical run MUST 有可人工审阅、能反查 raw SHA-256 的 standalone descriptive
visualization。

QUICK 和 NORMAL 默认每 run 生成一组 `CLASSIC_LOCKED` focus figures，使用
`scripts/josim-plot2.py`、`sep_comb`、`dark` 和 `-j 2pi`。一组可以包含 whole-run
overview 与预注册 focus/window panels；只画预注册 probes 和 signal schema，
不要求未注册 full dashboard。图必须标 signal、case、raw/derived、units、time
axis 和 phase display convention。只有当 paired comparison 本身属于预注册问题、
metric 或 acceptance evidence 时，才额外强制生成一组 focused comparison；该
comparison 与 standalone 使用同一 signal schema，并注明是否使用相同网格或
独立 stored grids。不得用 summary 图替代 immutable raw 或缺失证据。

FORMAL 继续使用 standalone-first、claim-relevant complete internal views、
注册 critical windows 的 visualization 和适用的 comparisons。未来 BVM→QB→JTL
FORMAL system visualization 使用 V2.1 semantic structure：

```text
01_SIGNAL_TIMING
02_BVM_STATE
03_JSL_CHAIN
04_QB_STATE
05_JTL_CHAIN
```

每个 subsystem view MUST 明确 `INPUT BOUNDARY -> INTERNAL STATE -> OUTPUT
BOUNDARY`，并同时提供 whole-run `OVERVIEW` 与注册的 focused windows。Standalone
与 comparison MUST 使用同一 semantic signal schema；comparison 只能增加 case
dimension，不能另挑一套“interesting signals”。额外 mechanism/dashboard/phase-plane
图默认不生成。若具体 fixture 不含一个假定的 top-level node，MUST 在 manifest
中登记真实 semantic boundary，不得伪造 probe。图均为 descriptive evidence，不能
单独认证 SFQ、Gate 或机制。

## VII. PHASE HANDLING

JoSIM `P(...)` raw value MUST 按 radians 保存和注明。phase comparison MUST：

1. 对每个 case independently unwrap；
2. 然后才 subtract 或 compare；
3. 保留 raw phase provenance in radians；
4. 仅在显式计算 `rad/(2*pi)` 后才可 display as turns；
5. MUST NOT 做 wrapped-phase subtraction。

Continuous phase winding、phase displacement 或 phase range MUST NOT 自动写成
SFQ event count，也 MUST NOT 写成 closed-loop fluxoid count。

## VIII. SFQ EVIDENCE RULE

执行者 MUST NOT 从单一证据宣称 SFQ count、switching 或 transmitted event。
单独的 `I > Ic`、raw phase winding、一个 voltage spike、一个 voltage area
或一个 pulse-like waveform 都不足以完成该声明；尤其 `I > Ic` MUST NOT 直接
推断 JJ switching。

若要把 transmitted event 称作 SFQ，执行者 MUST 要求尽可能独立且一致的
证据：stage-by-stage propagation、相关 JJ 约 `2*pi` phase slip、下游传播
一致性、terminal voltage-time area 与 `Phi0` 的相容性，以及正确 temporal
ordering；缺少其中的关键独立证据时 MUST 降级为 `INCONCLUSIVE` 或
`UNKNOWN`。即使多条证据一致，措辞也 MUST 限定为“in this simulation / under
this fixed condition”，不得外推硬件。缺少同 JJ、同端点/方向/窗口的 phase-area
交叉证据、matched control、JTL 或收敛证据时，执行者 MUST 使用
`INCONCLUSIVE` 或 `UNKNOWN`，不能用图形替代缺失证据。

## IX. EVIDENCE LABELS

所有科学报告、machine-readable interpretations 和 evidence tables MUST 使用
以下标签，并保持含义不变：

- `OBSERVED`：raw 直接可见，不依赖机制假设；
- `DERIVED`：从 raw 通过明确注册的数学运算得到；
- `BOUNDED_RESULT`：只在当前 topology、timing、parameters、solver 和 window
  下成立；
- `UNKNOWN`：当前证据不能可靠判断。

执行者 MUST NOT 把 `UNKNOWN` 包装成 mechanism conclusion。artifact validity、
activity、local JJ evidence、loaded downstream reception 和 system logic
evidence MUST 分层记录。

## X. CAUSAL CLAIM DISCIPLINE

以下措辞默认 MUST NOT 使用，除非有真正的 intervention evidence：`root cause`、
`proves mechanism`、`saturation`、`dead-time limited`、`switching because I > Ic`、
`passive isolation`、`perfectly preserved state`、`hardware-safe` 和
`general solution`。

`earliest divergence`、`missing progression` 和 `correlation` MUST NOT 被写成
root cause 或 causation。若任务只有 observation、replay 或 A/B comparison，
报告最多只能给 bounded causal evidence；没有 intervention 的机制解释 MUST
标成 `UNKNOWN` 或 hypothesis。

## XI. REPLAY EXPERIMENT RULE

Replay MUST 明确区分 waveform sufficiency oracle 与 circuit-equivalent
reconstruction。Ideal current replay 移除了 finite source impedance 以及
source/load self-consistent back-action，因此它只能回答：

> 这个 captured current waveform 在 ideal forcing 下是否足以驱动 receiver？

Replay MUST NOT 被描述为 Thevenin source、Norton source、原始 BVM/JSL network
或真实 source impedance 的重建，除非另有独立授权和证据。

## XII. ANALYSIS WINDOW DISCIPLINE

analysis window MUST 与问题的物理位置一致。执行者 MUST NOT 把 downstream
arrival time 当成 upstream/internal event timing，除非显式校正 propagation
delay。报告 MUST 区分 source time、front-end time、internal receiver time、
JTL time 和 terminal arrival time。

研究 recovery 或 fourth attempt 时，窗口 MUST 围绕 internal response time
对齐，而不是 terminal arrival time。窗口起点、终点、半开/闭语义、参考信号和
offset MUST 在 machine-readable artifact 中保存。

## XIII. QA

每个实验 MUST 提供 machine-readable QA，至少检查：

- HEAD 和 provenance；
- raw hash、no overwrite 和 raw 前后不变；
- sample count、actual time range、time monotonicity 和 stored grid；
- integration 是否使用 actual grid；
- finite values；
- required probes 和重复列处理；
- unit handling、sign/direction 和 phase unwrap；
- arithmetic reproduction；
- visualization source hashes；
- stale artifact detection；
- transformation registry；
- overclaim review。
- evidence manifest、ZIP contents、archived raw/deck hash 和 detached package QA；
- package bytes、repository-relative path 和 package SHA-256。

QA 失败的 artifact MUST 标为 `ARTIFACT_INVALID`，不能改写成 physical `FAIL`。
分析工具失败而 raw 有效时，MUST 保留原 raw/deck/log/metadata，修复工具后只
能对同一个 immutable raw 重新 QA，MUST NOT 因 analyzer 退出 1 而重跑 physics。

QUICK 和 NORMAL MAY 将无重复的静态、raw、provenance、注册算术和可视化检查
汇总为一个 canonical QA result set，并通过 per-run 字段或 hash-bound compatibility
views 供工具读取。合并只减少重复文件/重复计算，不得删除 §XIII 中的检查项；
每项必须记录输入 SHA/spec/checker identity、status，或给出 `NOT_APPLICABLE`
及理由。PACKAGE_QA 是独立 archive-level QA，不能由 run QA 替代；每个最终
package version 只需且必须有一份 package-bound PACKAGE_QA。FORMAL 还须有绑定
最终 package SHA、由独立 reviewer 执行的 evidence audit；该 audit 不授予科学
解释权限。

## XIV. CONVERGENCE / SENSITIVITY

如果实际没有做 timestep convergence、parameter sensitivity 或 solver sensitivity，
报告 MUST 写 `UNKNOWN`。单个 dt 看起来平滑不能被写成 converged；MUST NOT
自动补跑 convergence 或 sensitivity，除非用户明确授权并把它们加入新的
registered matrix。

## XV. RESULT PACKAGE

每个实验目录原则上 MUST 包含：

```text
PREFLIGHT.md
RESULT_BRIEF.md
runs/
analysis/
plots/
```

`analysis/` 至少 MUST 包含 canonical mechanical/raw QA、provenance/hash QA、
visualization QA 和适用的 transformation registry；QUICK/NORMAL 可以按 §XIII
合并不重复的 QA 记录。machine-readable scientific interpretations 只在
`SCIENTIFIC_REVIEW_AUTHORIZED` 后作为独立、版本化 artifact 出现。`plots/` MUST
包含每个 run 的一组可人工审阅 standalone focus visualization 和其 raw 的直接
provenance；若 comparison 是 preregistered evidence，也须包含 focused comparison。

每个未来完成的 QUICK/NORMAL/FORMAL physical-solve work unit MUST 生成并提交：

```text
handoff/<experiment_id>_raw_handoff.zip
handoff/PACKAGE_QA.json
```

ZIP MUST 至少包含 experiment definition、`PREFLIGHT.md`、每个 authorized run
的 `deck.cir`/`raw.csv`/`metadata.json`/`run.log`、experiment-local inputs 或
`SOURCE_MANIFEST.json`、mechanical QA/provenance、standard visualization
manifest/QA、per-run navigation、`EVIDENCE_MANIFEST.md` 和
`RAW_ANALYSIS_HANDOFF_MANIFEST.json`。`raw.csv` 是 immutable solver output，
不得用 selected/resampled/cropped/processed 文件替代。

`PACKAGE_QA.json` MUST 在 ZIP 完成后重新打开一次，验证 authorized runs、required
members、raw/deck hashes、canonical QA references、visualization evidence、package
bytes、repository-relative path 和 package SHA-256。每个最终 package version 只
生成一份 detached PACKAGE_QA；为避免自哈希循环，QA 文件保持在 ZIP 外。
PACKAGE_QA FAIL 时 MUST NOT commit package，状态为 `ARTIFACT_INVALID` 并 STOP。
任何 member、scope 或 ZIP bytes 改变都会使原 QA 失效，必须生成新版本和新 QA。
FORMAL 的独立 evidence audit 在 ZIP 外绑定同一 package SHA，不修改 ZIP，也不
自动产生 scientific verdict。

ZIP 一旦提交即 immutable。后续 scientific review 只能引用相同 package SHA；若
packaging 确实有错误，必须生成 versioned `_v2.zip` 并保留旧 ZIP，不能静默覆盖。
若 package 过大，工具只记录 `STORAGE_POLICY_REVIEW_RECOMMENDED`，不得自行切换
Git LFS、release artifact 或外部存储。

## XVI. RESULT_BRIEF STYLE

默认的 `RESULT_BRIEF.md` / `EVIDENCE_MANIFEST.md` MUST 是 evidence-only、
answer-first、短而可审计，优先顺序是：

1. experiment identity；
2. exact run matrix；
3. QA status；
4. `OBSERVED`；
5. `DERIVED`（仅已注册的 mechanical arithmetic）；
6. `BOUNDED_RESULT`（仅在另一个明确授权的 scientific review 中）；
7. `UNKNOWN`；
8. raw、plots、package 和 machine-readable artifacts 的 links。

默认 summary MUST 明确 `scientific interpretation = NOT PERFORMED`、
`unauthorized follow-up = none` 和 `status = AWAITING_SCIENTIFIC_REVIEW`，不得
写 mechanism、root cause、parameter recommendation、winner 或 physical
`BOUNDED_RESULT` interpretation。

它 MUST NOT 以长篇 mechanism essay 代替 raw、human-readable visual evidence
和 reproducibility。没有证据支持的 mechanism、hardware claim、Gate 或 universal
law MUST NOT 通过篇幅升级。

## XVII. NO SILENT FOLLOW-UP

实验完成后，执行者 MUST NOT 自动 tune、redesign、sweep、launch next experiment、
change receiver、change BVM、change load、change timing 或从结果推导下一项
recommendation。完成 package 和 commit 后必须 STOP，状态为
`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`。`AWAITING_SCIENTIFIC_REVIEW`
之后不得自动扩大 scope 或启动新的 physical solve。

只有用户明确给出 `SCIENTIFIC_REVIEW_AUTHORIZED` 才能进入独立 scientific
review；该 review 不修改原始 evidence ZIP，也不授予新的 solve authorization。

## XVIII. DEFAULT LIFECYCLE AND GIT POLICY

未来标准实验的默认顺序是：

```text
PRE-REGISTER -> PREFLIGHT -> PHYSICAL SOLVE -> MECHANICAL QA
-> STANDARD VISUALIZATION -> EVIDENCE PACKAGE
-> COMMIT EXPERIMENT + PACKAGE -> STOP
-> AWAITING_SCIENTIFIC_REVIEW
```

Codex 的默认职责固定为 `Experimental Operator + Evidence Packager`。标准工具
必须默认执行 exact authorized solves、raw/provenance/QA、标准可视化、package
integrity QA 和 Git commit；不默认执行 scientific analysis。正式实验 ZIP
默认直接提交 Git，同时记录 bytes、repository-relative path 和 SHA-256。历史
实验、历史 ZIP 和 legacy protocol 不因本节而迁移或重写。

## XIX. SCIENTIFIC STATE PRESERVATION

如果后续 analysis 推翻旧 interpretation，执行者 MUST：

- preserve old raw and old artifact；
- create a new versioned analysis；
- explicitly mark the old interpretation as superseded；
- state exactly why the interpretation changed；
- retain the provenance and QA that connect both versions。

执行者 MUST NOT 静默删除、覆盖或重写历史实验。新的 analysis 只改变其声明的
证据层；任何上层 summary、HANDOVER、project todo、route、metric freeze 或
paper-level claim 的更新 MUST 等待相应审阅/授权。
