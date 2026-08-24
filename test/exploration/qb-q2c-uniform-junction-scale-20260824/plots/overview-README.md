# qb-q2c-uniform-junction-scale-20260824 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

plot role: RESULT；required-case coverage 由 alignment manifest 管理，不由目录中是否存在 HTML 判断。
原始 JoSIM P(...) 连续轨迹显示为 φ/2π（turn）；未做基线相减、未按脉冲归零；不等于 SFQ 计数。

## cases

- `S055/logical0-read`
- `S055/logical0-read0-control`
- `S055/logical1-read`
- `S055/logical1-read0-control`
- `S070/logical0-read`
- `S070/logical0-read0-control`
- `S070/logical1-read`
- `S070/logical1-read0-control`
- `S085/logical0-read`
- `S085/logical0-read0-control`
- `S085/logical1-read`
- `S085/logical1-read0-control`

## exact displayed columns

- phase: `P(BJL2|XBQ)` → rad/2π turns
- phase: `P(BJL1|XBQ)` → rad/2π turns
- phase: `P(BJS|XBQ)` → rad/2π turns
- voltage: `V(OUT)` → µV
- voltage: `V(BJL2|XBQ)` → µV
- current: `I(BJL1|XBQ)` → µA
- current: `I(L1|XBQ)` → µA
- current: `I(BJL2|XBQ)` → µA
- current: `I(L2|XBQ)` → µA

正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。
