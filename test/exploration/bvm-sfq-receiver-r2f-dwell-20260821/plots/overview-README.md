# bvm-sfq-receiver-r2f-dwell-20260821 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

## cases

- `h00`
- `h05`
- `h10`
- `h20`

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
