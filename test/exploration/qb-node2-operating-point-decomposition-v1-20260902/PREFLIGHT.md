# QB_NODE2_OPERATING_POINT_DECOMPOSITION_V1：Preflight

记录时间：2026-09-02T10:19:34+08:00

## 范围与授权

- 任务类型：`EXISTING_RAW_ONLY`、`Exploration`、物理机制分析。
- 分析对象：固定 13 ps、12×320 µA、`logical1/read`、scaled QB 条件下的 G、I0、P0。
- 已复核的前置任务：`BVM_QB_LIN_REMOVAL_MATCHED_PAIR_QUICK_V1`，结果为 `QUICK_NO_EFFECT`。
- 本次授权只覆盖现有 raw 分析；不覆盖 BJs Ic 实验、偏置实验、参数 sweep、优化、拓扑/路径改变、Promotion、Formal Gate 或 magnetic coupling 延续。

## 不变更声明

- `NO_NEW_JOSIM=true`：本次没有调用 JoSIM 求解器。
- `NO_CIRCUIT_CHANGE=true`：没有修改电路拓扑或模型。
- `NO_PARAMETER_CHANGE=true`：没有修改实验参数。
- `NO_HISTORICAL_RAW_REWRITE=true`：没有覆盖、重写或删除历史 raw。
- 只新增本任务目录中的分析脚本、派生指标、报告和一张总览图；历史原始数据仍通过路径和 SHA-256 引用。

## 当前仓库与求解器记录

- 分析起始基线 HEAD：`853a722feaa047bafdc82eb6b6f3c0faa0c432e4`。
- preflight 时工作树因本任务输出及前置 human-gate 更新而为 dirty；状态由 `analysis/provenance.json` 保存。
- 记录的 solver：`build/josim-cli` v`2.7.2837d13`，SHA-256 为 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`；本次未执行。
- 指标规范：`docs/research/METRIC_SPEC_V2.md`，SHA-256 为 `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`。

## 主要 raw 输入

| case | 含义 | raw | SHA-256 |
|---|---|---|---|
| G | BVM → 12×320 JSL → ground source reference | `test/exploration/bvm-load-qb-matrix-v1-20260901/raw/source/13ps/12x320/logical1_read/run-01.csv` | `b92056235a06f86fdbc55b670656aecab834ab728d4fc44ba128ca0a30a809de` |
| I0 | G 的冻结源波形 replay 到 scaled QB | `test/exploration/bvm-load-qb-matrix-v1-20260901/raw/replay/13ps/12x320/logical1_read/run-01.csv` | `be7e0403586b8819a9f4d7e4f4400af90e640b281b7a3ae4e1331d351c866d4c` |
| P0 | BVM → 12×320 JSL → scaled QB physical connection | `test/exploration/bvm-load-qb-matrix-v1-20260901/raw/physical/13ps/12x320/logical1_read/run-01.csv` | `9aecc3f626148737bbd14e8cdb42a546002d7b2f268cc39badc430647c877d66` |

G/I0/P0 均为 13,599 个样本，时间范围 `0–169.9875 ps`，实际时间步为非均匀网格：最小约 `0.0125 ps`、最大 `0.025 ps`。

## supporting raw

| case | 输入 | raw | SHA-256 | 权限边界 |
|---|---:|---|---|---|
| Q45 | 45 µA | `test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-45u.csv` | `cc702632dad106f324004dd429dd94e9a4ad38d0cda300671c29b4ea76865517` | `HISTORICAL_SUPPORTING_REFERENCE` |
| Q68 | 68.4 µA | `test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv` | `0b3fab3ba7357d2475ffadb174f0d48ad33b7e7c934962a687074d4739468bdb` | `HISTORICAL_SUPPORTING_REFERENCE` |

Q45/Q68 的输入 deck、scaled QB/JJ model、35 µA bias、10 Ω load、周期 stimulus 和 raw 哈希均已检查通过；它们使用历史 standalone、0.1 ps 级时间网格及未冻结的局部诊断规则。因此只报告 scalar/dimensionless signatures，不做与 G/I0/P0 的 pointwise 比较、插值或阈值推广。

## QB 拓扑与方向

使用的 QB snapshot：`test/exploration/bvm-load-qb-matrix-v1-20260901/inputs/bq_cell.cir`，语义 hash 为 `b026981dbed5b8772ba3f928597d1b0750f133246763ba997caff3094c613063`；对应 scaled QB 参数为 `IBIAS=35 µA`、`R_LOAD=10 Ω`。当前 canonical QB 文件与 snapshot 的语义一致，但本次分析以 primary deck 中的 snapshot 为 provenance authority。

从实际 netlist 得到的 branch orientation：

```text
Lin  IN -> 1       BJs  1 -> 2       BJL1 2 -> 0       RJ1 2 -> 0
L1   2 -> 3        RB   IB -> 3      L2   3 -> 4       BJL2 4 -> 0
RJ2  4 -> 0        L0   4 -> OUT
```

对应的 KCL 为：

```text
I(Lin) - I(BJs) = 0
I(BJs) - I(BJL1) - I(RJ1) - I(L1) = 0
I(L1) + I(RB) - I(L2) = 0
I(L2) - I(BJL2) - I(RJ2) - I(L0) = 0
```

## 预注册窗口与停止条件

- W2：`[80,90) ps`；W3：`[95,110) ps`；W4：`[110,130) ps`。
- 严格 node4 local anchor：activity `[95,115) ps`，post `[115,130) ps`，tail `[125,130) ps`。
- I0 的严格锚点必须保持 phase `1.0160289228944646 turns`、area `1.0160368344325381 Φ0`、segment `103.0375–110.175 ps`、`CLEAN_ONE_SFQ_CANDIDATE`；若漂移则停止，不得替换为新解释。
- first-divergence 使用 W2 中心化后的 exact-grid 轨迹、当前任务预注册的 current/phase/partition 阈值；一个 native timestep `0.0125 ps` 内的 crossings 记为 `TIE`。
- 完成后状态固定为 `AWAITING_USER_REVIEW / STOP`，不得自动执行 follow-up。
