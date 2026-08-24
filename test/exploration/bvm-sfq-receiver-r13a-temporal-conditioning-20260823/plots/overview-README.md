# bvm-sfq-receiver-r13a-temporal-conditioning-20260823 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

plot role: RESULT；required-case coverage 由 alignment manifest 管理，不由目录中是否存在 HTML 判断。
原始 JoSIM P(...) 连续轨迹显示为 φ/2π（turn）；未做基线相减、未按脉冲归零；不等于 SFQ 计数。

## cases

- `c1-rectify/logical0-read0-control`
- `c1-rectify/logical1-read0-control`
- `c1-rectify/read0`
- `c1-rectify/read1`
- `c2-hold20/logical0-read0-control`
- `c2-hold20/logical1-read0-control`
- `c2-hold20/read0`
- `c2-hold20/read1`
- `c3-rectify-hold20/logical0-read0-control`
- `c3-rectify-hold20/logical1-read0-control`
- `c3-rectify-hold20/read0`
- `c3-rectify-hold20/read1`
- `raw-replay/logical0-read0-control`
- `raw-replay/logical1-read0-control`
- `raw-replay/read0`
- `raw-replay/read1`

## exact displayed columns

- phase: `P(B3|XREPLAY)` → rad/2π turns
- phase: `P(B2|XREPLAY)` → rad/2π turns
- phase: `P(B1|XREPLAY)` → rad/2π turns
- voltage: `V(B1|XREPLAY)` → µV
- voltage: `V(B2|XREPLAY)` → µV
- current: `I(L1|XREPLAY)` → µA
- current: `I(L2|XREPLAY)` → µA
- current: `I(B1|XREPLAY)` → µA
- current: `I(B2|XREPLAY)` → µA

正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。
