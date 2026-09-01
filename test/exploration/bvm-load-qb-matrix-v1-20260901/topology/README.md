# BVM_LOAD_QB_MATRIX_V1 拓扑包

这些图从本 Exploration 的代表性 JoSIM deck 生成，用于说明三种实验边界，
不是科学结论。图中的 BVM、JSL JJ、QB 内部 JJ/电感、R_LOAD、偏置和端口均
按电路元件语义绘制；完整端点和被省略的模型/探针细节保留在 `schematic.json`
与代表性 `.cir` 中。

## 拓扑入口

- [BVM → 12×JSL source](publication/BVM_JSL_SOURCE/README.md)：JSL 末端接地。
- [BVM → 8×JSL source](publication/BVM_JSL8_SOURCE/README.md)：JSL 末端接地。
- [BVM → 12×JSL → scaled QB](publication/BVM_JSL12_SCALED_QB_PHYSICAL/README.md)：JSL 末端直接接 QB `IN`。
- [BVM → 8×JSL → scaled QB](publication/BVM_JSL8_SCALED_QB_PHYSICAL/README.md)：JSL 末端直接接 QB `IN`。
- [ideal replay → scaled QB](publication/SCALED_QB_REPLAY/README.md)：`I_REPLAY` 直接接 QB `IN`。

## 代表性 deck 与变体边界

代表性 deck 都是 13 ps、logical1/read；9 ps、logical0/read 和 no-read
只改变 PWL 角色或读宽，不改变相同 fixture 的元件连接。12×320 与 8×500
改变 JSL 结数和单结模型面积，因此分别保留 source/physical 拓扑图；ideal
replay 不含 JSL，单独保留 QB replay 图。

include 快照为 `jjmit.cir`、`bvm_cell.cir` 和 physical/replay 使用的
`bq_cell.cir`，实际路径和 SHA-256 以 `manifest.yaml` 及各 package 的
`schematic.json` 为准。

## 验证边界

每个 publication package 都包含 `schematic.svg/png/pdf`、annotated 版本、
`schematic.json`、`schematic-validation.json`、`geometric-connectivity.json`
和 `geometric-connectivity-validation.json`。这些验证检查图与代表性 deck
的端点和元件登记，不把图升级为物理 Gate，也不替代原始 CSV。
