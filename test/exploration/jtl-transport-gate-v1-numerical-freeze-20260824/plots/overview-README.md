# jtl-transport-gate-v1-numerical-freeze-20260824 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

## cases

- `pulse5-original/0p00625/run`
- `pulse5-original/0p0125/run`
- `pulse5-original/0p025/run`
- `pulse5-reverse/0p00625/run`
- `pulse5-reverse/0p0125/run`
- `pulse5-reverse/0p025/run`
- `r11/0p00625/run`
- `r11/0p0125/run`
- `r11/0p025/run`

## exact displayed columns

- phase: `P(B2|XJTL1)` → rad/2π turns
- phase: `P(B2|XJTL2)` → rad/2π turns
- phase: `P(B1|XJTL1)` → rad/2π turns
- phase: `P(B1|XJTL2)` → rad/2π turns
- voltage: `V(JTL_OUT)` → µV
- voltage: `V(SFQ_OUT)` → µV
- current: `I(B1|XJTL1)` → µA
- current: `I(B2|XJTL1)` → µA
- current: `I(IB1|XJTL1)` → µA
- current: `I(L1|XJTL1)` → µA

正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。
