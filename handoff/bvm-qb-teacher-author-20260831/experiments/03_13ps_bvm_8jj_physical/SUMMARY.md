# BVM_JSL8_500_PHYSICAL_QB_RECHECK_V1

- **正式分类**：`PAPER_JSL8_IMPROVES_PHYSICAL_MARGIN`
- **拓扑**：canonical BVM SL → 8×`jjmit AREA=5` → frozen scaled QB → 10 Ω load
- **13 ps logical1 READ**：BJs `+6.899196 turn` local multi-turn；BJL1 `−0.275370 turn`；BJL2 `−0.124996 turn / −0.125006 Φ0`，均未形成 BJL2 one-SFQ。
- **logical0/read=0**：BJL2 仍为 bounded subthreshold/zero controls，无 complete event。
- **JSL guard**：8 个 JSL 均 non-switching；series current 最大 deviation 约 `1.0×10⁻⁹ µA`。
- **比较**：相对 12×320，`I(L_SL)` p2p 94.526→115.998 µA；`V(SL1)` 4.117→3.541 mV；`V(IN)` 2.511→3.115 mV；动态 load-line 改变。
- **边界**：BJs multi-turn 不是 downstream SFQ；BJL1/BJL2 仍反向/subthreshold；最有证据支持的是 `QB internal load-line mismatch`，不是唯一根因证明。
- **下一步**：允许另立 `SOURCE_MATCHED_QB_V1`，本轮 STOP；未运行 14 ps、dt ladder、rewrite/read、magnetic coupling、JTL、T1 或 QB sweep。

详见 [`REPORT.md`](REPORT.md)、[`manifest.yaml`](manifest.yaml) 和
[`analysis/comparison-12x320-vs-8x500.json`](analysis/comparison-12x320-vs-8x500.json)。
