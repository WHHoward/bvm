# 结果摘要：QB_NODE2_OPERATING_POINT_DECOMPOSITION_V1

状态：`AWAITING_USER_REVIEW / STOP`

## 范围

本次是 `EXISTING_RAW_ONLY` 分析：`NO_CIRCUIT_CHANGE`、`NO_PARAMETER_CHANGE`、`NO_NEW_JOSIM`。动机是上一轮 matched-pair `LIN` removal 只得到 `QUICK_NO_EFFECT`，因此本次只检查物理输入与 QB 内部节点的第一处分歧，未获授权开展 BJs、bias 或 sweep 实验。

## 关键观察

1. I0 和 P0 满足 QB input/node2/node3/node4 KCL；G 只作为 grounded-source reference，不被当作 QB KCL case。所有 I0/P0 最大残差均远低于 `0.001 µA` 容差。
2. W2 的稳定工作点为 `RB≈35 µA`、`L1≈−15.12 µA`、`L2≈19.88 µA`；按 netlist 方向，`L1` 与 `RB` 对 node3 的贡献相反。BJs 的 W2 分母接近零，所以 node2 分流比例不定义。
3. W3 中 P0 的 BJs 仍有明显局部活动（电流 p2p `78.528 µA`、phase p2p `2.777 turns`），但 node2 的 BJL1/L1 分配与 I0 显著不同；I0 的 BJL1 phase endpoint 约 `+1.249 turns`，P0 约 `−0.0066 turns`。
4. 旧的 result-dependent 10% 规则保留为 `LEGACY_RELATIVE_FINAL_AMPLITUDE_ONSET` sensitivity-only view。主分析改为 `PRE_NOISE_REFERENCED_ONSET`：current=`max(floor, 5×W2 PRE p99(abs(I0−P0)))`，phase 同理，partition 固定 `0.10`；ACTIVE/READ 不参与阈值估计。
5. 主配置的 first layer 为 input/BJs `95.075 ps`、node2 `95.0875 ps`；按 `0.025 ps` tie tolerance 三者属于同一首组。固定矩阵共 24 个配置：12 个 `COUPLED_INPUT_BJS_NODE2`、12 个 `INPUT_BJS_LIMITATION_SUPPORTED`，故 robustness=`MIXED`，不能宣称 node2 具有稳健的最早顺序。
6. 时间网格实际为非均匀，`dt_min≈0.0125 ps`、`dt_max=0.025 ps`；`0.0125 ps` 只标为 `MINIMUM_OBSERVED_SAMPLE_SPACING`。主 persistence 为实际采样跨度至少 `0.025 ps` 或 3 个连续样本，并记录实际跨度。
7. 严格同一 BJL2 local arithmetic 中，I0 保留已冻结锚点：`103.0375–110.175 ps`、phase `1.0160289229 turns`、area `1.0160368344 Φ0`、`CLEAN_ONE_SFQ_CANDIDATE`；P0 为 `SUBTHRESHOLD`。这仍只是同一 JJ 的 phase/area compatibility，不是 SFQ count 或下游 JTL delivery。
8. 历史 supporting Q45/Q68 显示局部标量差异：Q45 的 BJL1/BJL2 pulse phase 约为 0，Q68 约为 `+1 turn`；由于其 standalone、时间网格和未冻结规则不同，这不能升级为通用阈值或当前机制的权威证据。

## 分类

旧分类：`NODE2_REDISTRIBUTION_SUPPORTED`。

修正后分类：`COUPLED_INPUT_BJS_NODE2`

`mechanism_disposition: EXPLORATORY`，`robustness: MIXED`，`causal_order: NOT_PROVEN`。含义是：当前 raw 独立支持 node2/downstream 差异观察，但 PRE-noise onset matrix 同时给出 input/BJs 与 node2 的首组/顺序差异，因此只能保留 coupled exploratory description，不能把 node2 认作稳健的最早根因。

`NODE2_REDISTRIBUTION_DIFFERENCE_OBSERVED=true`：BJL1 current/phase、L1 separation、稳定 RB、L2 downstream separation 以及 I0 clean/P0 subthreshold 的 BJL2 local contrast 均满足观察条件；这与 temporal causal order 分开记录。

## 证据层级

- Observed：raw 中的 branch current、phase、voltage 以及 G→I0 的 replay exact-grid closure。
- Derived：按实际 netlist 方向计算的 KCL residual、窗口统计、phase turns、积分、node2/node3 分解、I0/P0 first-divergence。
- Physics-based inference：在本组条件下，RB 保持 35 µA，node3 随 L1/L2 改变；onset robustness 是 MIXED，因此不把 node2 写成稳健的最早层或唯一原因。
- Unknown：BJs limitation 是否是唯一根因、最佳 bias/Ic、真实 SFQ event count、JTL 是否接收、timestep convergence、硬件行为。

## 明确不证明

本结果不证明唯一根因、最佳 bias/Ic、论文 Fig.7 的拓扑，不证明 Formal BVM→QB closure、JTL/T1 delivery、硬件行为、通用不可行性，也不把任何 local phase turn 当作 SFQ count。

本 corrective patch 不执行 follow-up；当前停止，等待用户 review。
