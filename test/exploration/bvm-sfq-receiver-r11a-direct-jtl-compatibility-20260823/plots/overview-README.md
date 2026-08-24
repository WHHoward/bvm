# bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

plot role: RESULT；required-case coverage 由 alignment manifest 管理，不由目录中是否存在 HTML 判断。
原始 JoSIM P(...) 连续轨迹显示为 φ/2π（turn）；未做基线相减、未按脉冲归零；不等于 SFQ 计数。

## cases

- `logical0-read0-control`
- `logical1-read0-control`
- `positive-control/run-02`
- `read0`
- `read1`

## exact displayed columns

- phase: `P(B2|XJTL1)` → rad/2π turns
- phase: `P(B2|XJTL2)` → rad/2π turns
- phase: `P(B1|XJTL1)` → rad/2π turns
- phase: `P(B1|XJTL2)` → rad/2π turns
- voltage: `V(JTL_OUT)` → µV
- voltage: `V(SFQ_OUT)` → µV
- current: `I(L_SL|XBVM1)` → µA
- current: `I(B1|XJTL1)` → µA
- current: `I(B2|XJTL1)` → µA
- current: `I(IB1|XJTL1)` → µA

正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。
