# bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

plot role: RESULT；required-case coverage 由 alignment manifest 管理，不由目录中是否存在 HTML 判断。
原始 JoSIM P(...) 连续轨迹显示为 φ/2π（turn）；未做基线相减、未按脉冲归零；不等于 SFQ 计数。

## cases

- `phase-a-bump-300u`
- `phase-a-bump-68u4`
- `phase-a-zero`
- `phase-b-logical0-read0-control`
- `phase-b-logical1-read0-control`
- `phase-b-read0`
- `phase-b-read1`

## exact displayed columns

- phase: `P(B3|XCONV)` → rad/2π turns
- phase: `P(B3|XDCSFQ)` → rad/2π turns
- phase: `P(B2|XCONV)` → rad/2π turns
- phase: `P(B2|XDCSFQ)` → rad/2π turns
- voltage: `V(JTL_OUT)` → µV
- voltage: `V(OUT1)` → µV
- current: `I(L_SL|XBVM1)` → µA
- current: `I(B1|XJTL1)` → µA
- current: `I(B2|XJTL1)` → µA
- current: `I(L1|XCONV)` → µA

正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。
