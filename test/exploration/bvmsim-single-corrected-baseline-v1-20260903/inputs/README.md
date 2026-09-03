# Corrected single-BVM task-local decks

这些 deck 只用于本轮 corrected single-BVM 2×2。它们从已提交的 historical
baseline deck 读取拓扑，再显式补上：

- top-level `circuits/models/jjmit.cir` model closure；
- `WRITE = WL + BL`；
- 两个 logical state 共用的 `READ = WL + SE`，且 READ 时 `BL = 0`；
- 原始 `BVMSim/BQ.cir`、12-JJ terminal sensing line、0.1 ps profile。

`BVMSim/` 源文件以及旧 single-BVM raw 均不在这里修改。deck 由
`generate_corrected_decks.py` 生成并在运行目录再次保存。
