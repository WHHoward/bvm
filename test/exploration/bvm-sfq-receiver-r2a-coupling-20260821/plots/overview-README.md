# bvm-sfq-receiver-r2a-coupling-20260821 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

plot role: RESULT；required-case coverage 由 alignment manifest 管理，不由目录中是否存在 HTML 判断。
原始 JoSIM P(...) 连续轨迹显示为 φ/2π（turn）；未做基线相减、未按脉冲归零；不等于 SFQ 计数。

## cases

- `diff-a010-b007-k060/logical0-read0-control`
- `diff-a010-b007-k060/logical1-read0-control`
- `diff-a010-b007-k060/read0`
- `diff-a010-b007-k060/read1`
- `diff-a010-b007-k070/logical0-read0-control`
- `diff-a010-b007-k070/logical1-read0-control`
- `diff-a010-b007-k070/read0`
- `diff-a010-b007-k070/read1`
- `diff-a010-b007-k080/logical0-read0-control`
- `diff-a010-b007-k080/logical1-read0-control`
- `diff-a010-b007-k080/read0`
- `diff-a010-b007-k080/read1`
- `diff-a010-b007-k090/logical0-read0-control`
- `diff-a010-b007-k090/logical1-read0-control`
- `diff-a010-b007-k090/read0`
- `diff-a010-b007-k090/read1`
- `diff-a010-b007-k095/logical0-read0-control`
- `diff-a010-b007-k095/logical1-read0-control`
- `diff-a010-b007-k095/read0`
- `diff-a010-b007-k095/read1`

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
