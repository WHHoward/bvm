# QB_IDEAL_PHYSICAL_INTERNAL_TRAJECTORY_AUDIT_V1

## 当前状态

- revision：`r4`，前三次 `SOL_XHIGH_PHYSICS_ARCHITECT` 审阅发现并登记了
  12×320 run-input provenance mismatch；本文件是再次修订后的 preregistration。
- scientific parent HEAD：`f9a1cc24aae575182c0643092a4f008f12df0458`
- pre-analysis checkpoint：上一版已提交为 `fa7d591f72d91e72b4adb4022058cc7e67101ca2`；
  r4 也必须在正式 analysis 前提交。
- 修订记录时间：`2026-08-25T01:06:08+08:00`
- 本轮类型：`ANALYSIS ONLY`
- r4 必须先作为 pre-analysis checkpoint 提交进 HEAD；正式 analysis 尚未开始，等待同一个 Sol XHigh agent 最终返回
  `APPROVED_ANALYSIS_PLAN`。

## 不变边界

本轮只消费已有 raw 和已解析的 netlist provenance：

- 不运行新的 JoSIM；
- 不改变 BVM、QB、JSL、READ width、bias、load 或任何参数；
- 不做 parameter sweep、magnetic coupling、JTL 或 T1；
- 不把旧 ignored JSON/HTML 当作当前科学 authority；
- 不把 BJs multi-turn 当作 overdrive/failure；QB 的 one-SFQ 观察门仍是
  BJL2，BJs 只作内部 trajectory/activity 诊断。

本轮的唯一科学问题是：同一个 frozen scaled QB 在 13 ps ideal-current
replay 中可出现 BJL2 `+1` turn，而在 physical BVM/JSL drive 中出现约
`−0.12` turn 时，最早可信的动力学分叉发生在 PRE operating point、输入
port、BJs、node2/BJL1、node3 partition，还是 node4/BJL2。

## 首轮审阅提出的 artifact 修订

首轮审阅确认五组 reference 的核心 P/V/I 信号存在，但发现以下边界；本轮
不静默修复历史文件：

1. 上一轮 JSL8 的 `analysis/physical-13ps-metrics.json`、
   `analysis/comparison-12x320-vs-8x500.json` 和正式 HTML plots 在工作树中
   可见但不属于当前 HEAD 的 tracked authority。本轮从 raw 重新生成本目录
   的 derived artifacts，并给每个输入、输出和脚本建立 SHA-256 inventory。
   本目录的 preregistration 先单独提交；正式 analysis 完成后，所有被报告引用
   的 JSON/CSV/HTML/报告/脚本必须用 `git add -f` 纳入同一个可复核 checkpoint，
   并通过 fresh-checkout `git ls-files` 与 `git show HEAD:<path>` 检查。只写哈希
   而不进入 HEAD 的文件不算 artifact authority。
2. 上一轮报告中的 metric-spec 路径 `docs/METRIC_SPEC_V2.md` 不存在；本轮
   唯一引用为 `docs/research/METRIC_SPEC_V2.md`，当前 SHA-256 为
   `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`。
3. ideal replay provenance 中声称存在的
   `reference/control-provenance.yaml` 当前缺失；登记为
   `PROVENANCE_REFERENCE_MISSING`。不得新造一个历史文件，也不得把该缺失
   改写为 raw 信号缺失或电路失败。

## 五组 reference 与 raw authority

| ID | 角色 | 当前 raw | 解释边界 |
|---|---|---|---|
| `REF-A45` | scaled Q0 45 µA | `test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-45u.csv` | 六周期 ideal-current subthreshold reference；`dt=0.1 ps`，不能逐时刻对齐 13 ps raw |
| `REF-B68P4` | scaled Q0 68.4 µA | `test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv` | 六周期 ideal-current local exactly-one reference；不是 universal threshold |
| `REF-C13` | 13 ps ideal-current replay | `test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/raw/replay/13ps/{logical1_read,logical0_read,logical1_no_read_control,logical0_no_read_control}/run-01.csv` | frozen scaled QB 的 ideal replay；`I(I_REPLAY)` 是强制源，不是 physical source evidence |
| `REF-D12` | 13 ps physical 12×320 | `test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/raw/13/{logical1_read,logical0_read,logical1_no_read_control,logical0_no_read_control}/run-01.csv` | canonical BVM → 12 JSL → frozen QB |
| `REF-E8` | 13 ps physical 8×500 | `test/exploration/bvm-jsl8-500-physical-qb-recheck-v1-20260824/raw/13/{logical1_read,logical0_read,logical1_no_read_control,logical0_no_read_control}/run-01.csv` | canonical BVM → 8 JSL → frozen QB |

对应 provenance 文件也必须纳入 inventory：

- `test/exploration/qb-q0-standalone-current-quantized-event-20260824/manifest.yaml`
- `test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/manifest.yaml`
- `test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/reference/source-manifest.json`
- `test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/manifest.yaml`
- `test/exploration/bvm-jsl8-500-physical-qb-recheck-v1-20260824/manifest.yaml`
- `docs/research/METRIC_SPEC_V2.md`

每个 raw 必须记录路径、存在性、字节数、行数、表头 SHA-256、raw SHA-256、
时间起止和实际步长。任一 raw 缺失、截断、列不完整、含 NaN/Inf、时间不严格
递增或哈希无法复核时，artifact 标为 `INVALID`，停止机制结论。

inventory 还必须递归覆盖实际使用的 case decks 和 include closure：Q0 的 scaled
QB/model/decks；ideal replay 的四份 replay deck、`bq_cell.cir`、`qb-jjmit.cir`
和 source-manifest 指向的 source raw/snapshot；physical 12×320 与 8×500 的
case decks、BVM/QB/model snapshots；以及本目录的 preregistration、analysis
scripts、derived outputs、plot metadata 和报告。每一个列入报告或 manifest 的
路径都必须在 fresh checkout 中通过 `git ls-files --error-unmatch` 且
`git show HEAD:<path>` 非空；被 `.gitignore` 匹配的正式 JSON/HTML 必须显式
force-add，不能只依赖当前工作树。

## D12 历史 run-input provenance disposition

只读 git 追溯没有找到与 physical 12×320 manifest 声明 SHA 相符的不可变 case
deck。当前四个 deck 的实际 SHA 与历史 manifest 声明如下：

| case | manifest SHA 前缀 | 当前 HEAD deck SHA 前缀 | disposition |
|---|---|---|---|
| `13ps/logical1_read` | `dece76aa1806` | `1a07bdb7690a` | `RUN_INPUT_HASH_MISMATCH` |
| `13ps/logical1_no_read_control` | `cf6902529d41` | `c920c59629d1` | `RUN_INPUT_HASH_MISMATCH` |
| `13ps/logical0_read` | `e7cc641a1c57` | `5b45f703a119` | `RUN_INPUT_HASH_MISMATCH` |
| `13ps/logical0_no_read_control` | `ad5a2abb02ec` | `ecdc770e53a5` | `RUN_INPUT_HASH_MISMATCH` |

不修改历史 manifest，不重签旧 run，不把当前 deck 伪装成 manifest 声明的
deck。D12 raw 仍可做以下受限用途：

- raw completeness、P/V/I、KCL、trajectory 和 current partition 的
  `DESCRIPTIVE_RAW_OBSERVATION`；
- 与 D12 当前 deck/topology 相容性的结构检查；
- 作为 `C13↔D12` 的 provenance-inconclusive pair，不能进入认证的机制排序。

D12 不可支持“raw 确由当前 deck 生成”的强断言。由于本任务的完整机制目标
注册了 C13↔D12 与 C13↔E8 两个 primary pair，只要 D12 provenance 未恢复，
总 disposition 至少为 `MECHANISM_AUDIT_INCONCLUSIVE`；不得用 E8 单独结果把
总审计升级为 `MECHANISM_AUDIT_COMPLETE`。E8 pair 可以在 Sol 批准后独立分析，
并明确标注 D12 pair 的缺陷。

## 历史 manifest exception inventory

以下是既有文件中的历史错误/缺失引用，不属于本轮 dependency closure；本轮只
登记，不静默修复：

- `reference/control-provenance.yaml`：`PROVENANCE_REFERENCE_MISSING`；
- `docs/METRIC_SPEC_V2.md`：历史错误路径；本轮只用
  `docs/research/METRIC_SPEC_V2.md`；
- 旧 `analysis/topology-precheck.json` 和旧 8×500 comparison JSON：旧的
  ignored/非 HEAD 派生产物；本轮不引用；
- physical 12×320 manifest 中四个 case deck SHA：
  `RUN_INPUT_HASH_MISMATCH`，不得重写。

本次 analysis dependency closure 只要求当前 tracked raw、当前实际使用的
deck/include/source snapshot、正确 metric spec、source-manifest 及本目录产物
可取得且哈希可复核。历史 exception 不自动使无关 raw 变成 physical `FAIL`。

## Ideal source-chain content closure

对 `REF-C13` 每个 role，正式 analysis 必须逐项验证：

1. source-manifest 指向的 source raw 存在且 hash 一致；
2. replay snapshot 的 source current/voltage 列存在且 hash 一致；
3. replay deck 的 `I_REPLAY 0 IN PWL(...)` time/current 序列与 snapshot
   的 registered source sequence 完全一致，未 rectify、hold、normalize、
   rescale 或重采样；
4. deck 使用的 `bq_cell.cir`、`qb-jjmit.cir` 和 bias/load 与 manifest 一致；
5. 四个 role 的 READ/no-read 控制关系可由当前 tracked source chain 复核。

若第 1–4 项失败，ideal replay 该 role 的 source-chain artifact 为
`INVALID`；若仅第 5 项依赖缺失的历史 YAML，则该 control/selectivity claim
为 `INCONCLUSIVE`，primary logical1 trajectory 不自动作废。`control-provenance.yaml`
始终保持 `PROVENANCE_REFERENCE_MISSING`。

## 预冻结的 sign/orientation Gate

统一待检验约定：`positive_current_into_QB_IN`。

| source | netlist branch direction | 正方向假设 | pointwise Gate |
|---|---|---|---|
| ideal replay | `I_REPLAY 0 IN ...` | `0→IN`，电流进入 QB `IN` | `I(I_REPLAY) - I(Lin|XBQ)` |
| physical 12×320 | `B_LD12 upstream IN` | 最后一个 JSL 电流进入 `IN` | `I(B_LD12) - I(Lin|XBQ)` |
| physical 8×500 | `B_LD8 upstream IN` | 最后一个 JSL 电流进入 `IN` | `I(B_LD8) - I(Lin|XBQ)` |
| QB input | `Lin IN 1` | `IN→node1`，电流离开 `IN` 进入 QB | 同一 IN-node KCL |

正式分析必须从 raw 逐 timestep 报告上述 residual 的 PRE、ACTIVE、TRANSITION、
POST 最大值和 p95，并同时核对 `V(IN)`、BJs/BJL1/BJL2 的声明端点。netlist
拓扑一致不等于 raw orientation Gate 已通过。

在查看正式结果前冻结当前版本的数值 Gate（电流单位 A）：

```text
abs_tol = 1.0e-12 A
rel_tol = 1.0e-6
bound(t) = abs_tol + rel_tol * sum(abs(all terms in the relevant KCL equation))
```

该 floor 取自 CSV 十进制输出的固定量级，且不是从本轮观察到的 residual 反推；
不得随结果移动。对每个 orientation/KCL equation，`max(|r|/bound)` 与
`p95(|r|/bound)` 必须同时 `<= 1`，并且不存在连续 3 个 samples 超过 bound。
单个超过 bound 的 sample 仍须原样记录，不可删除。

- expected sign 通过：`ORIENTATION_KCL_PASS`；
- expected sign 失败、相反 sign 同时通过：`PORT_SIGN_ORIENTATION_ERROR`，STOP；
- 两种 sign 都失败：`ORIENTATION_KCL_INCONCLUSIVE`，artifact 不得升级为物理
  机制结论；
- raw 列、时间轴或精度损坏：artifact `INVALID`，不评价电路功能。

只有 orientation/KCL Gate 通过，才允许继续 load-line 和 first-divergence
解释。

## 时间窗与 operating-point 表示

所有 13 ps ideal/physical raw 使用同一组注册窗：

- `PRE = [80, 94) ps`
- `ACTIVE = [94, 130) ps`
- `TRANSITION = [130, 140) ps`
- `POST = [140, 170) ps`

`TRANSITION` 是为避免漏掉 commit/retrap 而新增的诊断窗；它不改变原先
ACTIVE/POST 的事件合同。

对每个 registered P/V/I/branch signal 同时保存：

1. continuous absolute phase `P(t)`，原始单位 rad；
2. `sin(P)`、`cos(P)`，用于 modulo-​`2π` state comparison；
3. `relative_to_PRE = P(t) - median(P[PRE])`，再按 `2π` 转为 turns；
4. PRE median、p2p、MAD-derived scale、ACTIVE extrema、TRANSITION extrema、
   POST p2p；
5. raw current 与 `delta_current = I(t) - median(I[PRE])`；
6. 实际 CSV time 列上的 signed integral，明确区分 raw DC-dominated integral
   和 baseline-subtracted dynamic integral。

absolute phase 不因出现整数偏移就预称为 gauge；relative phase 也不能替代
完整环 fluxoid 计算。`I/Ic` 只作 operating-point diagnostic，不拥有事件
计数权力。

## PRE state classification

PRE state 先于 READ 解释。对同一 signal 的两个 run，定义：

```text
scale_pre = max(1.4826 * MAD(PRE),
                1e-12 * max(1, max(abs(PRE))))
pair_limit = 5 * sqrt(scale_pre_a^2 + scale_pre_b^2)
```

其中 floor 只是数值 floor，不是物理容差。绝对 phase 不进入 state-match 的
唯一判据；phase 以 `sin/cos` 和 relative trajectory 辅助，current/voltage
及 branch partition 是主判据。

- `PRE_STATE_MATCHED`：所有预注册 port、BJs/BJL1/BJL2 current/voltage 和
  branch-partition feature 的 PRE median 差均未超过对应 `pair_limit`，且
  `sin/cos` 没有持续超过同一规则的差异。
- `PRE_BIAS_REPARTITIONED`：至少一个上述 feature 在整个 PRE 中持续超出
  `pair_limit`，并且不是单个采样点异常。
- `INCONCLUSIVE`：输入时间网格、端点或控制 provenance 无法建立匹配。

无论 PRE 分类如何，报告仍保留五组 reference 的 absolute、modulo 和
relative 数值，避免把 PRE 差异藏进 normalization。

## ACTIVE first-divergence rule

primary comparison matrix 固定为两组，不能按结果挑选：

1. `REF-C13.logical1_read ↔ REF-D12.logical1_read`；
2. `REF-C13.logical1_read ↔ REF-E8.logical1_read`。

`REF-D12 ↔ REF-E8` 只作 physical sizing diagnostic，不能代替 ideal-versus-
physical first divergence。logical0/read0/no-read cases 只作 matched controls，
用于检查选择性和 PRE/POST 背景，不得充当 primary pair。

每一组 primary pair 都独立检查 orientation、PRE、first divergence、tie 和
分层分类。两组 primary pair 若首层不同，必须保留 pair-specific 结果，并以
`MULTI_STAGE_COUPLED_DIVERGENCE` 或 `INCONCLUSIVE` 汇总，不能选择更符合偏好的
一个 pair。仅对 `REF-C13`、`REF-D12`、`REF-E8` 做统一 13 ps timeline；三者
必须先通过相同时间网格检查，否则不插值而判 `INCONCLUSIVE`。

对每个 comparison feature，先减去各自 PRE median，再用两 run 的 pooled
PRE scale 定义差异阈值：

```text
credible_difference = abs(delta_a - delta_b)
                     > 5 * sqrt(scale_pre_a^2 + scale_pre_b^2)
```

first credible divergence 必须：

- 在 `ACTIVE ∪ TRANSITION` 内首次越过该阈值；
- 连续至少 3 个原始 samples 保持越界；
- 不是单个 NaN、solver artifact 或同一采样级的方向抖动；
- 记录 exact first sample、time、feature、sign、持续样本数和对应 raw paths。

若多个 feature 的 first sample 相差不超过一个 sample（13 ps raw 的
`0.0125 ps`），报告 `TIE`，不得强行排列因果顺序。若最早可信差异已在 PRE，
ACTIVE 不再被包装为 first cause。first divergence 是时间上的最早可信分叉，
不自动等于唯一根因。

feature 分层固定为：

1. input port：`I(source)`, `I(Lin)`, `V(IN)`；
2. BJs trajectory：P/V/I(BJs)；
3. node2：`I(L1)`, `I(BJL1)`, `I(RJ1)`；
4. node3：`I(RB)`, `I(L2)`；
5. node4/output：`I(L0)`, `I(BJL2)`, `I(RJ2)`, `V(OUT)`。

## KCL/current-partition contract

逐 timestep 重建并报告 raw residual 与 baseline-subtracted residual：

```text
IN:    I(source) = I(Lin)
node2: I(BJs) = I(L1) + I(BJL1) + I(RJ1)
node3: I(L1) + I(RB) = I(L2)
node4: I(L2) = I(L0) + I(BJL2) + I(RJ2)
```

每条 branch 输出 PRE median、ACTIVE/TRANSITION extrema、POST p2p、signed
dynamic integral 和 residual 的 max/p95。KCL residual 只作数值 QA；它本身
不证明事件或机制。

## Q0 45/68.4 mechanism reference rule

Q0 使用其自己的注册 pulse starts `[10, 60, 110, 160, 210, 260] ps`、
`dt=0.1 ps` 和窗口规则：

- `pre=[s−10,s−1)`；
- `activity=[s,s+25)`；
- `post=[s+25,min(s+49,300))`。

不把 Q0 与 13 ps raw 逐时刻对齐。对六个 pulse 分别提取 BJs/BJL1/BJL2
phase/area segment、current partition envelope 和 post boundedness，再报告
六 pulse 的 median、范围、方向一致性和重复性。只允许形成有限的：

- `TRAJECTORY_RESEMBLANCE_TO_SUBTHRESHOLD`
- `TRAJECTORY_RESEMBLANCE_TO_QUANTIZED`
- `TRAJECTORY_RESEMBLANCE_MIXED_OR_INCONCLUSIVE`

相似性不等于机制同一性；`68.4 µA` 不称 universal threshold，Q0 周期 raw
也不与 13 ps 单次 raw 混作 timestep/convergence 证据。

## 事件与物理措辞边界

本轮主要结论是 internal trajectory/mechanism，不把 visualization 或导数
样本作为 event count。若复核 BJL2 local event，仍需同一 JJ、同一端点、同一
方向、同一连续单调 segment 的 `ΔP/(2π)` 与 `∫Vdt/Φ0` 双证据及 bounded post。

明确禁止：

- `BJs multi-turn = failure/overdrive`；
- 仅凭 `I/Ic`、电压峰值或 total variation 计事件；
- 把 physical BJL2 负向 subthreshold 直接归因于 amplitude insufficient；
- 把 first temporal divergence 直接写成唯一物理根因；
- 把 8×500 的旧 `PAPER_JSL8_IMPROVES_PHYSICAL_MARGIN` 沿用为方向性恢复。

## 计划中的新产物（均从 raw 重建）

```text
analysis/reference-integrity.json
analysis/orientation-audit.json
analysis/pre-bias-state.csv
analysis/divergence-timeline.csv
analysis/node-partition-summary.csv
analysis/trajectory-audit.json
analysis/independent-raw-recheck.json
REPORT.md
SUMMARY.md
```

只生成支撑机制结论的注册关键图；每张图仍保留 exact source paths、case role、
phase semantics 和 raw/derived 边界。拟生成的关键页面为：

```text
plots/pre-bias-state-comparison.html
plots/input-port-orientation-kcl.html
plots/node2-current-partition.html
plots/node3-current-partition.html
plots/node4-current-partition.html
plots/bjs-vs-bjl1-phase-trajectory.html
plots/bjl1-vs-bjl2-phase-trajectory.html
plots/vin-vs-ilin-port-trajectory.html
plots/standalone45-vs68p4-vs-physical-trajectory.html
```

这些图是 mechanism diagnostics，不是 event/Gate authority；报告和 raw-derived
metrics 才是正式证据。图中相位若归一化，只标为 continuous phase `φ/2π`
（turns），不标为 SFQ count。

正式 checkpoint 还必须包含一个独立 raw recheck。它不得读取本目录生成的
`orientation-audit.json`、`pre-bias-state.csv`、`divergence-timeline.csv` 或
`trajectory-audit.json` 来证明自己；必须从五组 raw 和 netlist 重新计算并至少
复核：

- 一个 `I(source)-I(Lin)` 和一个 QB node KCL residual；
- 一个 PRE scale/limit 与 `PRE_STATE_MATCHED`/`PRE_BIAS_REPARTITIONED` 判定；
- 每组 primary pair 的 first-divergence timestamp；
- 所有报告引用的 BJL2 phase/同 JJ voltage-area 数字。

独立复算任一项不一致时，输出 `MECHANISM_AUDIT_INCONCLUSIVE` 并 STOP。

derived JSON/CSV/HTML 不具有独立 authority；authority 顺序固定为：tracked
raw → tracked netlist/include/provenance → derived evidence → diagnostic HTML。

## 最终判定与 STOP

最终只允许输出：

- `MECHANISM_AUDIT_COMPLETE`
- `MECHANISM_AUDIT_INCONCLUSIVE`

并分别报告 artifact status、Observed、Derived、Inference、Unknown、最强机制
分类、remaining competing explanations 和下一参数族建议。下一参数族必须由
first divergence 决定，并写清 existing evidence、physical model、target
quantity、falsifiable hypothesis、controls、predicted signatures、decision tree
和 stop rule；本轮不执行它。

同一个 Sol XHigh 完成 final review。如果 Luna 与其对关键科学结论有实质分歧，
输出 `SCIENTIFIC_ARBITRATION_REQUIRED` 并 STOP。不得把本轮 Agent/Model 分工
写入全局永久规则。
