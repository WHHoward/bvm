# bvm-sfq-receiver-r0-20260819 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

## cases

- `logical0-read0-control`
- `logical1-read0-control`
- `read0`
- `read1`

## exact displayed columns

- phase: `P(B_TRIG|XTRIG)` → rad/2π turns
- phase: `P(B_JM1|XBVM1)` → rad/2π turns
- phase: `P(B_JM2|XBVM1)` → rad/2π turns
- phase: `P(B_JS1|XBVM1)` → rad/2π turns
- voltage: `V(B_TRIG|XTRIG)` → µV
- voltage: `V(SL1)` → µV
- current: `I(L_SL|XBVM1)` → µA
- current: `I(I_BL1)` → µA
- current: `I(I_WL1)` → µA
- current: `I(R_IN|XTRIG)` → µA

正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。
