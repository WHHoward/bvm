# PAPER-SL-Q1 可视化

`qb-replay/` 直接读取 Q1 frozen scaled QB 的四个 matched raw，并另列 Q0 68.4 µA positive-control。显示 BJs/BJL1/BJL2 phase、JJ voltage/current、input、bias、loop/load currents、OUT。

phase 统一显示为 `rad/2π` turns，不是 SFQ count。Q1 的 source-loaded verdict 与 back-action 仍以 `REPORT.md`/analysis 为准。
