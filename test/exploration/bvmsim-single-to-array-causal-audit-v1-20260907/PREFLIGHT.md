# Single → 4×1 shared-SL causal audit — preflight

本任务是 `EXPLORATION / QUICK`，目标是定位从 isolated historical
JM2-connected single BVM 到 4×1 COMMON_SL array 的轨迹分歧来源。comparison
HTML 是验收项；metrics 和报告不能替代图。

## Scope lock

- 不修改 `circuits/bvm/bvm_cell.cir`、historical JM2-connected variant、`BVMSim/BQ.cir`、historical JTL 或任何旧 experiment。
- 不 sweep 参数，不优化 RSL/JJ Ic/QB bias/timing/timestep，不运行 canonical BVM。
- 先分析 existing raw；只有为拆分 protocol/sensing/quiet-cell/active-cell 混杂所必需时，才建立 G1/G2。现有 G3/G4 raw 复用并核验，不重复执行。
- 到 G4 后停止，人工审阅前不自动 follow-up。

## Starting state

- HEAD before setup: `470ad38cdaea0e55ed2a77d5e72c3ec7d001192e`
- preflight time: `2026-09-07T11:04:31+08:00`（后续 provenance 以脚本实际写入时间为准）
- initial `git status --short --untracked-files=all`: clean
- solver: `build/josim-cli`, `JoSIM v2.7.2837d13`
- solver SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`

## Authority boundary

本审计的 BVM authority 是：

`test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir`

它是 historical JM2-connected variant，`L_M2 2 3 24.5P`。`circuits/bvm/bvm_cell.cir`
不是本任务输入，因此所有结果都不能写成 canonical BVM 结果。

## Existing raw first

| role | source |
|---|---|
| G0 / Golden single S1 | `bvmsim-jm2-connected-single-rloop-observability-v1-20260904/runs/S1-J-RLOOP/raw.csv` |
| 4×1 QB-loaded array | `bvmsim-4bvm-common-sl-12jsl-qb-integration-v1-20260904/runs/<mask>/raw.csv` |
| 4×1 passive boundary | `bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904/runs/<mask>/raw.csv` |

R-loop single raw 为 `0–199.9 ps`，array raw 为 `45–199.9 ps`；比较只取精确重叠
stored grid。array raw 的实际网格保留其 `0.1–0.2 ps` 记录，不把 nominal
`.tran 0.1p` 当成每个相邻点都等距。

## Registered causal bridge

```text
G0: one BVM + historical single sensing boundary + single S1 protocol
  ↓ sensing boundary only
G1: one BVM + 12×area=5 JSL COMMON_SL→QBIN + same G0 protocol
  ↓ history/protocol only
G2: one BVM + same G1 boundary + array history/final READ protocol
  ↓ three connected quiet BVMs
G3: four BVMs on COMMON_SL, BVM1 READ active, existing mask 1000
  ↓ second active READ
G4: four BVMs on COMMON_SL, BVM1+BVM2 active, existing mask 1100
```

G1/G2 的生成与运行必须在本 preregistration setup commit 之后进行。G3/G4
不是新的物理 run，而是现有 raw 的 hash-bound reuse。

## Visualization acceptance

必须使用 `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`。每个 comparison
page 的输入 CSV 保留 P 的 raw radians，plotter 只做一次
`continuous_unwrap(rad)/(2*pi)` 显示转换；不得把 turns 命名成 SFQ count，且
不得出现 `Unknown` axis。必须生成并检查 `plots/plot_manifest.json` 和
`analysis/viz_qa.json`。
