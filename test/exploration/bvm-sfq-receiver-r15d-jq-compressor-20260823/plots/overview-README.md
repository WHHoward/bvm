# bvm-sfq-receiver-r15d-jq-compressor-20260823 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

plot role: RESULT；required-case coverage 由 alignment manifest 管理，不由目录中是否存在 HTML 判断。
原始 JoSIM P(...) 连续轨迹显示为 φ/2π（turn）；未做基线相减、未按脉冲归零；不等于 SFQ 计数。

## cases

- `logical0-read`
- `logical0-read0-control`
- `logical1-read`
- `logical1-read0-control`

## exact displayed columns

- phase: `P(B_DET|XR15D)` → rad/2π turns
- phase: `P(B_JM1|XBVM1)` → rad/2π turns
- phase: `P(B_JM2|XBVM1)` → rad/2π turns
- phase: `P(B_JS1|XBVM1)` → rad/2π turns
- voltage: `V(SL1)` → µV
- voltage: `V(N6|XBVM1)` → µV
- current: `I(L_SL|XBVM1)` → µA
- current: `I(I_BL1)` → µA
- current: `I(I_WL1)` → µA
- current: `I(R_IN|XR15D)` → µA

正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。
