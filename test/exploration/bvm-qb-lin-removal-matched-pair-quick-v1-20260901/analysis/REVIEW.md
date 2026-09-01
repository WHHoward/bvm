# BVM_QB_LIN_REMOVAL_MATCHED_PAIR_QUICK_V1 review

审查时间：`2026-09-01T20:45:16+08:00`

## 审查 disposition

- artifact / analysis review：`PASS`
- scientific disposition：`INCONCLUSIVE`
- final workflow state：`AWAITING_USER_REVIEW / STOP`
- 本文件只记录审查，不修改 raw、netlist、预注册规则或 outcome。

## 被审查的最强有界声明

在固定 13 ps、12×320、logical1/read、scaled-QB 和固定 W3 窗口下，删除 QB
`Lin=0.8 pH` 后，五个 primary QB matched trajectory gap 没有达到预注册的
20% 收窄，因此本次 Quick 标记为 `QUICK_NO_EFFECT`。该声明不延伸到其他参数、
硬件或系统级 Gate。

## Adversarial probes

| 隐蔽错误假设 | 探针 | 结果 |
|---|---|---|
| phase turns 漏掉或重复除以 `2π` | 独立用 stdlib 从 P0/I0/P1/I1 raw 读取，连续 unwrap 后显式除以 `2π`，重算 W3 D0/D1 | `PASS`；结果与 `analysis/metrics.json` 相符。审查器第一次临时尝试漏除 `2π`，已废弃且未用于结论 |
| 选错重复的 `I(B_LD1)` / `I(B_LD12)` 列 | 检查 raw header occurrence，按 preregistered occurrence `0` 选择；不允许隐式 collapse | `PASS`；重复列被保留并显式选择 |
| 实际跑了旧 case、第三条 case 或 stale raw | 检查 runner case IDs、return code、raw hash、`run/cases/*/raw/run-01.csv` 数量 | `PASS`；恰为 P1/I1 两条新 science raw，均 return code 0 |
| Lin intervention 是 no-op 或误接了节点 | 检查 candidate 中没有物理 `Lin` element 且存在 `BJs IN 2`，baseline 仍有 `Lin IN 1 0.8p` | `PASS`；candidate topology intervention 与预注册一致 |
| I1 replay 输入被重塑、重采样或换源 | 比较 I0/I1 `I_REPLAY` PWL block hash 和 raw `I(I_REPLAY)` exact sequence/grid | `PASS`；两者均 exact，block hash 为 `6ce48ff4...` |
| W3 边界或插值改变了 gap | 独立检查 exact full time grid，半开窗口 `[95,110)` 的样本数 | `PASS`；五条 raw grid 相同，W3 为 1200 samples，无插值 |
| local strict label 被过度解释成 SFQ delivery | 检查 strict spec、报告免责声明和 Gate 文件 | `PASS`；明确为 same-JJ local phase/area arithmetic，不是事件计数、下游接收或 system Gate |

## Numerical review

- 单位：`P()` raw radians → continuous unwrap / `2π` → turns；电流为 A→µA，电压为 V→mV；`PASS`。
- 符号/方向：D0/D1 使用右侧减左侧但 RMS 不改变方向；BJL2 phase 与同一 BJL2 direct voltage 使用声明方向；没有以绝对值掩盖判定；`PASS`。
- 积分/采样：strict area 使用实际 CSV time 列的梯形积分；非均匀 time grid 被保留而非假定固定间隔；`PASS`。
- 容差/阈值：20% 规则来自候选运行前的预注册；strict 本地容差来自冻结 task-local spec；没有事后调阈值；`PASS`。
- 数值健康：五条 raw 均通过 NaN/Inf、严格递增时间和完整 CSV QA；`PASS`。
- I0 anchor：独立复算 `1.0160289228944646` turns、`1.0160368344325381 Φ0`、
  `[103.0375,110.175] ps`，并得到 `CLEAN_ONE_SFQ_CANDIDATE`；`PASS`。
- 复现性：solver 为记录的 `build/josim-cli v2.7.2837d13`，binary hash 与 parent
  一致；输入快照、raw hash、命令、日志和 plot provenance 已保存；`PASS`。
- 收敛/敏感性：本 Quick 没有 timestep ladder、参数 sweep 或硬件复测；`UNKNOWN`，
  不能把当前单点标签升级为稳定性或普遍性结论。

## 关键独立复算值

| signal | D0 | D1 | reduction |
|---|---:|---:|---:|
| `P(BJS|XBQ)` | 2.24520197348247 turns | 2.20491872195116 turns | 0.0179419277228013 |
| `I(L1|XBQ)` | 28.3754441957857 µA | 29.0629265352794 µA | -0.0242280732153559 |
| `P(BJL1|XBQ)` | 0.519117425552821 turns | 0.523840998864030 turns | -0.00909923858976436 |
| `I(L2|XBQ)` | 28.3754449188809 µA | 29.0629273323834 µA | -0.0242280752061441 |
| `P(BJL2|XBQ)` | 0.430009706908926 turns | 0.433203836242592 turns | -0.00742804007060083 |

## Residual uncertainty

- 没有 logical0/no-read control、其他 Lin 点、其他偏置/负载或 timestep ladder。
- P0/P1 的 BJL2 仍是 subthreshold；I0/I1 的 local strict classification 相同，
  但 local phase/area 兼容性不构成 downstream reception 证据。
- 当前 reduction 是窗口化 waveform metric；它不独立确定接口失配的唯一物理机制。
