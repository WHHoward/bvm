# qb-q2a-source-decoupled-waveform-replay-20260824 overview

此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。

## cases

- `A-q0-68p4u-positive-control`
- `B-q1-loaded-vsl-replay`
- `C-canonical-logical1-vsl-replay`
- `C0-canonical-logical0-vsl-replay`

## exact displayed columns

- phase: `P(BJL2|XBQ)` → rad/2π turns
- phase: `P(BJL1|XBQ)` → rad/2π turns
- phase: `P(BJS|XBQ)` → rad/2π turns
- voltage: `V(OUT)` → µV
- voltage: `V(BJL2|XBQ)` → µV
- current: `I(BJL1|XBQ)` → µA
- current: `I(L1|XBQ)` → µA
- current: `I(BJL2|XBQ)` → µA
- current: `I(L2|XBQ)` → µA

正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。
