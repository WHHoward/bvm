# bvm-sfq-receiver-r9a-l2-routing-20260823 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

## cases

- `logical0-read0-control/run-02`
- `logical1-read0-control/run-02`
- `read0/run-02`
- `read1/run-02`

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
