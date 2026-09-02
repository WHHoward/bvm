# 结果摘要：QB_NODE2_OPERATING_POINT_DECOMPOSITION_V1

状态：`AWAITING_USER_REVIEW / STOP`

## 范围

本次是 `EXISTING_RAW_ONLY` 分析：`NO_CIRCUIT_CHANGE`、`NO_PARAMETER_CHANGE`、`NO_NEW_JOSIM`。动机是上一轮 matched-pair `LIN` removal 只得到 `QUICK_NO_EFFECT`，因此本次只检查物理输入与 QB 内部节点的第一处分歧，未获授权开展 BJs、bias 或 sweep 实验。

## 关键观察

1. G/I0/P0 在输入节点、node2、node3、node4 的三段窗口中均满足当前方向定义下的 KCL；所有最大残差均远低于 `0.001 µA` 容差。
2. W2 的稳定工作点为 `RB≈35 µA`、`L1≈−15.12 µA`、`L2≈19.88 µA`；按 netlist 方向，`L1` 与 `RB` 对 node3 的贡献相反。BJs 的 W2 分母接近零，所以 node2 分流比例不定义。
3. W3 中 P0 的 BJs 仍有明显局部活动（电流 p2p `78.528 µA`、phase p2p `2.777 turns`），但 node2 的 BJL1/L1 分配与 I0 显著不同；I0 的 BJL1 phase endpoint 约 `+1.249 turns`，P0 约 `−0.0066 turns`。
4. I0/P0 预中心化 exact-grid first-divergence 的最早 resolved layer 是 node2 partition `95.2 ps`；输入/L1 BJs 在 `97.9 ps` 同时 crossing，node3/node4 在 `98.3375 ps` 同时 crossing。`0.0125 ps` 内只作 tie，不作因果排序。
5. 严格同一 BJL2 local arithmetic 中，I0 保留已冻结锚点：`103.0375–110.175 ps`、phase `1.0160289229 turns`、area `1.0160368344 Φ0`、`CLEAN_ONE_SFQ_CANDIDATE`；P0 为 `SUBTHRESHOLD`。这仍只是同一 JJ 的 phase/area compatibility，不是 SFQ count 或下游 JTL delivery。
6. 历史 supporting Q45/Q68 显示局部标量差异：Q45 的 BJL1/BJL2 pulse phase 约为 0，Q68 约为 `+1 turn`；由于其 standalone、时间网格和未冻结规则不同，这不能升级为通用阈值或当前机制的权威证据。

## 分类

`NODE2_REDISTRIBUTION_SUPPORTED`

`mechanism_disposition: EXPLORATORY`。含义是：当前 raw 支持“差异首先表现为 node2 内部支路重新分配”的描述；它不唯一确定根因，也不排除输入 BJs 与 node2 的耦合机制。

## 证据层级

- Observed：raw 中的 branch current、phase、voltage 以及 G→I0 的 replay exact-grid closure。
- Derived：按实际 netlist 方向计算的 KCL residual、窗口统计、phase turns、积分、node2/node3 分解、I0/P0 first-divergence。
- Physics inference：在本组条件下，node2 partition 是最早的 resolved descriptive difference；RB 保持 35 µA，node3 后续随 L1/L2 改变。
- Unknown：BJs limitation 是否是唯一根因、最佳 bias/Ic、真实 SFQ event count、JTL 是否接收、timestep convergence、硬件行为。

## 明确不证明

本结果不证明唯一根因、最佳 bias/Ic、论文 Fig.7 的拓扑，不证明 Formal BVM→QB closure、JTL/T1 delivery、硬件行为、通用不可行性，也不把任何 local phase turn 当作 SFQ count。

## 未执行的后续（最多三项）

1. 由用户选择一个受控候选（例如只固定其余条件改变单一 bias/Ic），重新预注册 matched controls。
2. 在同一 netlist 与同一输入下做更细 timestep 的 clean rerun，并单独检查收敛。
3. 取得可作为 authority 的 receiver/JTL event 证据后，再评估是否值得升级 Candidate/Authority。

以上三项本轮均未执行。当前停止，等待用户 review。
