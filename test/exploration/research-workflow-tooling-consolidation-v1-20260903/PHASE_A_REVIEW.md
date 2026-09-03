# PHASE A review — tooling consolidation and golden parity

## Scope

本复核只覆盖共享 measurement tooling 与旧 raw 的回归 parity；没有调用
JoSIM，也没有产生新的物理证据。PHASE B 尚未开始。

## Numerical review

- `P(...)` 保持 JoSIM 原始弧度；只有在 `phase_area_window` 中按
  `phase_delta_rad / (2*pi)` 转换为 turns。
- 电压面积使用同一 junction 的实际存储时间网格和梯形积分；没有插值，
  时间窗采用左闭右开语义。
- phase/area 的 parity 容差预注册为 turns 的绝对/相对 `1e-12`；展示型
  波形指标的容差为绝对 `1e-9`、相对 `1e-12`。这些是代码重算的一致性
  容差，不是物理工程容差。
- 旧 single-BVM 与 4-BVM golden raw 以 SHA-256 固定；parity 运行前后未
  改写这些文件。
- 独立检查结果：`94` 项通过，`0` 项失败；parity JSON 明确记录
  `simulation_invoked: false`。

## Adversarial review

本轮最强的可支持结论只有“共享测量实现与既有 golden 结果一致”。针对会
让结果看似正确但实际失真的路径，检查了以下项目：

- 旧 single-BVM 的 S0/S1 分支和旧 4-BVM `1111` 分支均被实际读取并重算，
  不是只检查文件存在性或常数输出。
- phase 与 voltage-area 在同一 junction、同一窗口、同一方向上配对；没有
  把 whole-window phase displacement 当作 SFQ count。
- 旧 raw 的重复列不被 pandas 式自动重命名；未使用的重复 `V(O2)` 不参与
  parity authority。
- stimulus 语义由 task-local 调用者显式提供；共享层只验证 WL+BL WRITE
  与 WL+SE READ，不自行猜测实验语义。
- deck QA 只做 include/model/probe/topology/timestep 等静态 artifact 检查，
  不把 QA 状态升级成物理 verdict。
- 测试包含 malformed/non-finite/非单调输入的边界检查，以及严格事件列表
  的既有锚点；共享测量代码新增的 focused suite 与既有 bvmtools suite
  均通过。

## Remaining limits

这次 parity 不能证明共享 API 的物理正确性、JoSIM 数值收敛、BVM/QB/JTL
机制，也不能证明 PHASE B 的六状态结果。旧实验的历史语义和原始 raw 仍然
是各自实验的 authority；新 API 通过 parity 后才作为后续新实验的测量实现
入口。

## Review disposition

`PHASE_A_REVIEW_PASS`（仅 tooling regression scope）。满足 preregistered
gate，可以进入 PHASE B；PHASE B 仍必须单独运行、分析和审阅。
