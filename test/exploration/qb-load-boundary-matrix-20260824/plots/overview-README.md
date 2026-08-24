# qb-load-boundary-matrix-20260824 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

plot role: RESULT；required-case coverage 由 alignment manifest 管理，不由目录中是否存在 HTML 判断。
原始 JoSIM P(...) 连续轨迹显示为 φ/2π（turn）；未做基线相减、未按脉冲归零；不等于 SFQ 计数。

## cases

- `A-q0-open/scaled-iin-68p4u`
- `B-q0-jtl-only/scaled-iin-68p4u`
- `C-q0-10ohm-parallel-jtl/scaled-iin-68p4u`
- `D-q5-open/paper-j0-logical0-read`
- `D-q5-open/paper-j0-logical0-read0-control`
- `D-q5-open/paper-j1-logical1-read`
- `D-q5-open/paper-j1-logical1-read0-control`
- `E-q5-jtl-only/paper-j0-logical0-read`
- `E-q5-jtl-only/paper-j0-logical0-read0-control`
- `E-q5-jtl-only/paper-j1-logical1-read`
- `E-q5-jtl-only/paper-j1-logical1-read0-control`

## exact displayed columns

- phase: `P(BJL2|XBQ)` → rad/2π turns
- phase: `P(BJL1|XBQ)` → rad/2π turns
- phase: `P(BJS|XBQ)` → rad/2π turns
- phase: `P(B2|XJTL1)` → rad/2π turns
- voltage: `V(JTL_OUT)` → µV
- voltage: `V(OUT)` → µV
- current: `I(B1|XJTL1)` → µA
- current: `I(B2|XJTL1)` → µA
- current: `I(BJL1|XBQ)` → µA
- current: `I(IB1|XJTL1)` → µA

正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。
