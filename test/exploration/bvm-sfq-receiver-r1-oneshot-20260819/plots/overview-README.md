# bvm-sfq-receiver-r1-oneshot-20260819 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

## cases

- `a050-b15/logical0-read0-control`
- `a050-b15/logical1-read0-control`
- `a050-b15/read0`
- `a050-b15/read1`
- `a050-b15-lq10/logical0-read0-control`
- `a050-b15-lq10/logical1-read0-control`
- `a050-b15-lq10/read0`
- `a050-b15-lq10/read1`
- `a050-b15-rq100/logical0-read0-control`
- `a050-b15-rq100/logical1-read0-control`
- `a050-b15-rq100/read0`
- `a050-b15-rq100/read1`
- `a050-b15-rq1k/logical0-read0-control`
- `a050-b15-rq1k/logical1-read0-control`
- `a050-b15-rq1k/read0`
- `a050-b15-rq1k/read1`

## exact displayed columns

- phase: `P(B_OUT|XTRIG)` → rad/2π turns
- phase: `P(B_TRIG|XTRIG)` → rad/2π turns
- phase: `P(B_JM1|XBVM1)` → rad/2π turns
- phase: `P(B_JM2|XBVM1)` → rad/2π turns
- voltage: `V(B_OUT|XTRIG)` → µV
- voltage: `V(B_TRIG|XTRIG)` → µV
- current: `I(L_SL|XBVM1)` → µA
- current: `I(I_BL1)` → µA
- current: `I(I_WL1)` → µA
- current: `I(L_SEC|XTRIG)` → µA

正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。
