# PHYSICAL_BVM_JSL12_QB_SFQ_CLOSURE_V1

- **正式 verdict**：`PHYSICAL_BACKACTION_PREVENTS_CLOSURE`
- **拓扑**：canonical BVM SL → 12×`jjmit AREA=3.2` series JSL → frozen scaled QB → `R_LOAD=10 Ω`
- **13 ps**：read1 BJL2 最大连续段 `−0.122128 turn / −0.122131 Φ0`，subthreshold；read0/control zero complete event。
- **14 ps**：read1 BJL2 最大连续段 `−0.121434 turn / −0.121438 Φ0`，subthreshold；read0/control zero complete event。
- **对照**：ideal replay 的 read1 BJL2 为 `+1.016/+1.061 turn` candidate；physical cascade 约为其绝对值的 `0.120/0.115`，且 polarity reversed。
- **机制边界**：I(L_SL) 没有数量级 collapse，但 V(SL)/N6、JSL/QB load-line 和 QB current partition 改变；不能把失败归结为单一 source collapse 或单一 QB 参数。
- **未做**：candidate 才允许的 timestep/rewrite-repeat；standard JTL/T1。

详见 [REPORT.md](REPORT.md)、`analysis/physical-13ps-metrics.json`、`analysis/physical-14ps-metrics.json`。
