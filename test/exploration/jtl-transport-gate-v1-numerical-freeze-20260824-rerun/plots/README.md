# JTL transport Gate V1 数值冻结可视化

来源为本 rerun 的九个 immutable raw：`r11`、`pulse5-original`、`pulse5-reverse` 各自的 `0.025/0.0125/0.00625 ps`。

每个 timestep 有独立 HTML，另有三个 timestep comparison。图中显示四颗 JJ 的连续 phase、直接 voltage，以及 exact output/branch probes。phase 显示为 `rad/2π` turns；不能把 full-window settled one-well 直接当作 local SFQ event。

当前正式 disposition 保持 **`JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE`**，因为 pulse5-original 的注册 window robustness 未闭合。可视化不改变该结论。
