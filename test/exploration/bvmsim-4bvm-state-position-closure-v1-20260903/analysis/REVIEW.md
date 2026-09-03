# PHASE B numerical and adversarial review

## Numerical checks

- 所有 phase 输入首先按完整 raw 轨迹连续展开；turns 只用
  `rad/(2*pi)`。没有把 phase range 或 cumulative phase 当成 SFQ count。
- phase/area 使用同一 junction、同一 READ1 窗口和同一实际采样网格；六个
  raw 的 time token 逐项相同，比较中没有插值。
- 独立的 stdlib CSV 重算（不调用 task-local analyzer）重新计算了六个状态
  的 BJ2/JTL6 phase-area、weight-1 Lin 峰值、PRE_READ1 state levels 和
  READ1 QB KCL 残差：`30` 个断言全部通过，exit code `0`。
- 六个 raw 的 SHA-256 在仿真后和可视化前后均保持不变；metadata 中的 raw
  hash 与文件一致。
- `bvmtools.kcl` 被用于三个 QB 内部节点方程；电流方向和方程写在
  `analysis/metrics.json`，没有在 task-local 重新实现 KCL 算术。

## Adversarial checks

本轮最强的结论是一个有边界的“状态 basis 闭合 + 位置依赖输入 + count
mismatch”观察，而不是功能 PASS。针对可能让结果看似正确的路径，检查了：

1. source branch：六个 deck 都直接包含历史 BVMSim BVM/QB/JTL；canonical
   BVM 明确没有替换。
2. stale/wrong raw：每个 run 有独立 metadata、log 和 hash；所有 solver
   exit code 为零且无模型默认告警。
3. wrong control semantics：WL+BL WRITE、WL+SE READ 由 task-local 显式
   传给共享 stimulus API；六个状态的 invariant WL/SE waveform 比较为零。
4. duplicate/hidden columns：新 raw 无重复 header；原始 phase/current
   标签由精确名称读取。
5. phase-as-count error：BJ2 的约 2/3/4 turns 被 strict list 分成一个
   continuous multi-turn segment，并在报告中明确排除 clean separated SFQ
   解释；JTL6 的 separated counts 单独列出。
6. window-boundary error：association windows 使用半开区间，plateau 验证
   使用不含边沿的 `[51,60)`, `[71,80)`, `[91,100)`, `[111,120)`。
7. plot-only overclaim：plot2 仅负责描述；最终分类来自 metrics 和独立
   recheck，不来自 HTML 外观。

## Corrective analysis trace

运行期间发现并修正了三个实现层问题：初版 state discriminator 错把“零位
保持不变”视为 inconclusive；随后发现已经是 µA 的 display peak 又被乘了
一次 `1e6`；最后修正了 plot 输出目录、Plotly 内置 JS 中无关 `Unknown`
文本的 QA 以及 manifest 文本封装。每次修正都没有重跑仿真，raw hash 未变；
过渡分析输出保留在本地的 `metrics_initial_analysis_bug_v1.json`、
`metrics_intermediate_analysis_bug_v2.json`、`metrics_unit_fix_v3.json`，
不作为 authority。当前 `analysis/metrics.json` 是修正后的唯一分析入口。

## Disposition

`ANALYSIS_REVIEW_PASS_WITH_BOUNDED_EXPLORATORY_RESULT`。artifact 和数值
重算通过；科学含义仍受历史 fixture、task-local state basis 和严格事件
定义限制。用户复核前不启动任何 follow-up。
