# BVM_LOAD_QB_MATRIX_V1 关键可视化

这些页面是描述性可视化，不是物理 Gate。原始 CSV 位于 `raw/`；
每个页面旁边的 `.metadata.json` 记录原始输入和选取的列。

## 12 个聚焦页面

- [BVM/JSL/QB source | 9 ps | 12x320](plots/9ps-12x320-source-key.html) — `source`；精简关键轨迹，输入文件 `analysis/derived_inputs/9ps-12x320-source-key.csv`。
- [BVM/JSL/QB physical | 9 ps | 12x320](plots/9ps-12x320-physical-key.html) — `physical`；精简关键轨迹，输入文件 `analysis/derived_inputs/9ps-12x320-physical-key.csv`。
- [BVM/JSL/QB replay | 9 ps | 12x320](plots/9ps-12x320-replay-key.html) — `replay`；精简关键轨迹，输入文件 `analysis/derived_inputs/9ps-12x320-replay-key.csv`。
- [BVM/JSL/QB source | 9 ps | 8x500](plots/9ps-8x500-source-key.html) — `source`；精简关键轨迹，输入文件 `analysis/derived_inputs/9ps-8x500-source-key.csv`。
- [BVM/JSL/QB physical | 9 ps | 8x500](plots/9ps-8x500-physical-key.html) — `physical`；精简关键轨迹，输入文件 `analysis/derived_inputs/9ps-8x500-physical-key.csv`。
- [BVM/JSL/QB replay | 9 ps | 8x500](plots/9ps-8x500-replay-key.html) — `replay`；精简关键轨迹，输入文件 `analysis/derived_inputs/9ps-8x500-replay-key.csv`。
- [BVM/JSL/QB source | 13 ps | 12x320](plots/13ps-12x320-source-key.html) — `source`；精简关键轨迹，输入文件 `analysis/derived_inputs/13ps-12x320-source-key.csv`。
- [BVM/JSL/QB physical | 13 ps | 12x320](plots/13ps-12x320-physical-key.html) — `physical`；精简关键轨迹，输入文件 `analysis/derived_inputs/13ps-12x320-physical-key.csv`。
- [BVM/JSL/QB replay | 13 ps | 12x320](plots/13ps-12x320-replay-key.html) — `replay`；精简关键轨迹，输入文件 `analysis/derived_inputs/13ps-12x320-replay-key.csv`。
- [BVM/JSL/QB source | 13 ps | 8x500](plots/13ps-8x500-source-key.html) — `source`；精简关键轨迹，输入文件 `analysis/derived_inputs/13ps-8x500-source-key.csv`。
- [BVM/JSL/QB physical | 13 ps | 8x500](plots/13ps-8x500-physical-key.html) — `physical`；精简关键轨迹，输入文件 `analysis/derived_inputs/13ps-8x500-physical-key.csv`。
- [BVM/JSL/QB replay | 13 ps | 8x500](plots/13ps-8x500-replay-key.html) — `replay`；精简关键轨迹，输入文件 `analysis/derived_inputs/13ps-8x500-replay-key.csv`。

## 读图说明

- source 页：看 BVM SL 电流、首末 JSL 电流、BVM 节点和末级 JSL 相位。
- physical 页：看 QB 输入、BJs→BJL1→BJL2 相位轨迹和 `V(OUT)`/`I(R_LOAD)`。
- replay 页：看同一源波形直接驱动 QB 时的对应输入和输出。
- P 图只把原始 rad 乘以 `1/(2*pi)` 显示为 continuous phase turns；不能直接当作 SFQ 事件数。
- 需要定量结论时回到 `analysis/metrics.json` 和原始 CSV，不从图形单独判定事件。
