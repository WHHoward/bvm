# qb-q1-canonical-bvm-scaled-qb-compatibility-20260824 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

plot role: RESULT；required-case coverage 由 alignment manifest 管理，不由目录中是否存在 HTML 判断。
原始 JoSIM P(...) 连续轨迹显示为 φ/2π（turn）；未做基线相减、未按脉冲归零；不等于 SFQ 计数。

## cases

- `logical0-read`
- `logical0-read0-control`
- `logical1-read`
- `logical1-read0-control`

## exact displayed columns

- phase: `P(BJL2|XBQ)` → rad/2π turns
- phase: `P(BJL1|XBQ)` → rad/2π turns
- phase: `P(BJS|XBQ)` → rad/2π turns
- phase: `P(B_JM1|XBVM1)` → rad/2π turns
- voltage: `V(OUT_Q)` → µV
- voltage: `V(SL1)` → µV
- current: `I(L_SL|XBVM1)` → µA
- current: `I(BJL1|XBQ)` → µA
- current: `I(I_BL1)` → µA
- current: `I(I_WL1)` → µA

正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。
