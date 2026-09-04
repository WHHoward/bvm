# COMMON-SL → 12×500 µA JSL → frozen QB/JTL integration Quick

## 当前状态

本轮是 `EXPLORATION / QUICK`，当前状态为 `AWAITING_USER_REVIEW`。本结果只适用于本轮固定的 historical JM2-connected BVM、COMMON_SL、12 个 500 µA JSL、`BVMSim/BQ.cir`、六级 `BVMSim/library_josim/jtl2.cir`、10 Ω 终端和 0.1 ps `.tran` 设置。

## 改变与保持不变

上一轮的边界是：

```text
COMMON_SL → B_JSL01 ... B_JSL12 → GND
```

本轮唯一授权的拓扑边界变化是：

```text
COMMON_SL → 同一组 B_JSL01 ... B_JSL12 → QBIN
          → frozen BVMSim BQ → frozen JTL1 ... JTL6 → 10 Ω → GND
```

静态预检确认 10 个 mask 中 BVM 实例、stimulus、JSL 的模型/面积/顺序/上游连接均与 passive baseline 一致；没有 per-cell JSL、第二负载、残留 daisy segment 或 canonical BVM。设置已在 commit `5d19d166` 冻结后才运行。

## 重要观察（Observed）

1. 10 个 receiver-loaded run 均成功，raw/header/metadata QA 和控制时序 QA 通过；接收端与 passive same-mask 的存储时间网格逐点一致，没有插值。

2. QB 边界确实改变了上游 COMMON_SL source。`READ=[110,170)` ps 内，`SUM_LSL` 的 receiver-loaded minus passive same-mask 最大绝对差为：`0000: 1.226 µA`、单 active: `13.749 µA`、2 active: `87.490 µA`、3 active: `100.436 µA`、`1111: 202.437 µA`。这不是数值显示误差，而是加载边界改变后的波形级 back-action 观察。

3. 12 个 JSL 的串联电流保持一致：`I(B_JSL01)` 到各后续 JSL 的 READ KCL residual 最大值为 0（按保存数值计算）；`I(B_JSL12)-I(LIN|XBQ1)` 的最大 READ residual 约 `1.0×10^-7 µA`。COMMON_SL 的四路 `L_SL` 求和与 `I(B_JSL01)` 的最大 residual 约 `6.0×10^-5 µA`。因此当前主要差异不是由 JSL 链路断开造成的。

4. QB 输入的 READ 波形随 commanded population 增长，但不是一个简单的 0/1/2/3/4 事件计数：`|I(LIN)|` 的代表性最大值约为 `4.04, 48.90, 60.37, 217.07, 352.33 µA`（population 0、1、2、3、4）。单 active 的四个位置在本 symmetric fixture 中逐点相同。

5. `BJ2` 的累计 phase displacement（这里只是 `continuous_unwrap(P rad)/(2π)`，不是 SFQ count）在 representative population 0/1/2/3/4 中约为 `-0.0008/-0.0008/0.9991/2.9990/2.9991 turns`。严格分段结果为：population 0/1/2 的 BJ2 complete segment 分别为 `0/0/0`，population 3/4 各为 `1`；但后两者都是 continuous multi-turn running，clean separated event 为 `0`，不能写成 3 个或 4 个 clean SFQ。

6. JTL6 B02 的 local strict diagnostic 在 population 2/3/4 分别得到 `1/3/3` 个 clean separated local segments（onset 约为 `116.8 ps`；`116.6,136.6,142.8 ps`；`116.4,134.9,139.5 ps`）。但这些是 JTL6 junction-local 观察；BJ2 没有对应的 clean separated event，因而不能升级为 BJ2→JTL1→…→JTL6 的端到端 SFQ transport count。12 个 JSL 的 local diagnostic 在所有 mask 中没有 complete event。

## 物理含义（Inference，限于本 fixture）

把同一 12-JSL stack 的终端从 GND 接到 frozen QB/JTL 后，receiver loading 会反馈到 COMMON_SL、四个 BVM 的 SL branches 和 QB trajectory；这种反馈随 population 增强。当前证据更支持“拓扑边界改变造成可观测 loading/back-action，并且高 population 下出现非线性响应”，而不是支持“共享 SL 近似无扰动地线性累加并稳定地产生 0–4 个端到端 SFQ”。

## 尚未证明（Unknown / interpretation ceiling）

- 不证明 canonical BVM、论文机制、硬件行为或工艺 margin；本轮没有使用 canonical BVM。
- 不证明 timestep convergence；本轮只有固定的 `.tran 0.1p 200p 45p`。
- 不把 phase displacement、voltage area、I>Ic、integer crossing 或 JTL6 local event 数叫作系统 SFQ count。
- 不证明 QB 逻辑正确，也不证明 local JTL event 已从 BJ2 离散传输而来。
- 不据此选择新参数；本轮没有调 BVM/JSL/QB/JTL、bias、timing 或终端。

## 证据与可视化

- [主结果可视化](plots/RESULT_OVERVIEW.html)
- [每个 run 的图和比较图索引](plots/plot_manifest.json)
- [数值分析](analysis/metrics.json)
- [独立 raw 复算](analysis/independent_check.json)
- [拓扑 ASCII 与静态预检](analysis/TOPOLOGY_ASCII.md)、[machine preflight](analysis/topology_preflight.json)
- [可视化 QA](analysis/viz_qa.json)

## 可能的下一步（最多三项；本轮不执行）

1. 先由用户审阅本轮 source back-action、BJ2 与 JTL6 分层证据，并决定是否接受当前因果解释。
2. 如获单独授权，设计一个只针对 QB boundary/loading 机制的后续 analysis/Quick，并继续冻结本轮 BVM、JSL、QB、JTL 参数。
3. 只有在另行授权并重新预注册后，才考虑 canonical BVM 或其它参数/数值问题；它们不属于本轮结果。

本轮结束动作：`STOP`。
