# Experimental Contract

状态：`ACTIVE / V1`（2026-09-09 evidence-first amendment）

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

实验设计阶段 MUST 优先 full probe。如果某个内部 node、branch 或 JJ 未来可能
用于机制判断，执行者 MUST 在 solve 前 probe；MUST NOT 等 solve 后才发现没有
数据。

QB 类实验默认 MUST probe：input boundary、LIN、BJS、L1、BJ1、RJ1、L2、IB、
BJ2、RJ2、L3 和 QBOUT。JJ MUST 保存可用的 P/V/I；inductor 和 resistor
MUST 保存可用的 I/V（若具体工具不提供某列，必须在 preflight 和 QA 标为
`UNKNOWN`，不能伪造或省略该缺失）。

JTL 实验 MUST probe 全部级别，不能只 probe JTL1/JTL6。JTL1/JTL6 MAY 作为
summary visualization，但 raw MUST NOT 只保留 endpoint。

BVM 实验至少 MUST 覆盖 storage core、R-loop、output path、shared boundary、
target controls 和当前问题需要的 quiet branches。

## VI. VISUALIZATION IS REQUIRED EVIDENCE

实验交付 MUST NOT 只有 `raw.csv + metrics.json + RESULT_BRIEF.md`。每个
physical run MUST 有 human-readable standalone visualization；paired runs
MUST 有 comparison visualization；注册的 critical windows MUST 有 zoomed
visualization；有意义时 MUST 同时提供 raw tracks 和 comparison/delta；机制
敏感 block MUST 有 complete internal view。

standalone visualization MUST 先于 comparison visualization 完成并独立 QA。
每一张图 MUST 标明 signal name、case、raw 或 derived、units、time axis 和
phase display convention；MUST NOT 用漂亮的 summary 隐藏 full internal raw。
默认使用仓库接受的 `scripts/josim-plot2.py`、`sep_comb`、`dark` 和 `-j 2pi`
语言。图是 descriptive evidence，MUST NOT 单独认证 SFQ、Gate 或机制。

未来 BVM→QB→JTL 实验的 standard visualization MUST 使用 V2.1 semantic
structure：

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
中登记真实 semantic boundary，不得伪造 probe。

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

`analysis/` 至少 MUST 包含 mechanical QA、provenance/hash QA、visualization QA
和 transformation registry。machine-readable scientific interpretations 只在
`SCIENTIFIC_REVIEW_AUTHORIZED` 后作为独立、版本化 artifact 出现。
`plots/` MUST 包含可人工审阅的 standalone 和 comparison evidence；每个 run 的
standalone 页面与其 raw 的直接 provenance MUST 可反查。

每个未来完成的正式实验还 MUST 生成并提交：

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

`PACKAGE_QA.json` MUST 在重新打开 ZIP 后验证 authorized runs、raw/deck hashes、
required definitions、mechanical QA 和 visualization artifacts。它记录最终
package SHA-256；为避免自哈希循环，QA 文件保持在 ZIP 外。PACKAGE_QA FAIL 时
MUST NOT commit package，状态为 `ARTIFACT_INVALID` 并 STOP。

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
