# PAPER-SL-Q4 — constant-sum L1/L2 placement test

状态：`PREREGISTERED_SINGLE_POINT`

记录时间：`2026-08-24T07:46:01+08:00`

Parent HEAD 必须为：

`bfc3c6ee600f30d27078b53ed09b23053a5191e3`

## 唯一科学问题

在完全冻结的 PAPER-SL-Q2 replay 与 QB 参数下，将额外的 `0.59 pH` 从
central-bias node 上游的 L1 移到下游的 L2，是否能区分：

1. Q3 的弱增益是总电感 `L1+L2` 的 common effect；
2. Q3 的弱增益是 proximal-L1 placement effect；
3. downstream reflected impedance / timing 是否真正改变 BJL1 的正负波形抵消。

本轮只运行一个 Q4 point，不把 `0.9505 turn` 强行解释为完整 event。

## Q2/Q3/Q4 定义

| fixture | L1 | L2 | L1+L2 | provenance |
|---|---:|---:|---:|---|
| Q2 reference | 3.91 pH | 3.91 pH | 7.82 pH | accepted PAPER-SL-Q2 `inputs/40u` |
| Q3 sibling | 4.50 pH | 3.91 pH | 8.41 pH | accepted PAPER-SL-Q3 |
| **Q4 test** | **3.91 pH** | **4.50 pH** | **8.41 pH** | this Exploration |

Q4 必须直接从 accepted Q2 `inputs/40u` fixture 构建：只将 local QB snapshot
中的 `L2 3 4 3.91p` 改为 `L2 3 4 4.50p`。禁止从 Q3 deck 派生，避免遗留
`L1=4.50p`。

## 冻结参数

| 参数 | 冻结值 |
|---|---:|
| `IBIAS` | **40 uA**；四个 deck 直接包含 `I_IBIAS 0 IBIAS pwl(... 40u ...)` |
| `L1` | 3.91 pH |
| `L2` | 4.50 pH（唯一变更） |
| `Lin` | 0.80 pH |
| `L0` | 1.323 pH |
| `BJs/BJL1/BJL2 AREA` | 0.50 / 0.36 / 0.54 |
| `RJ1/RJ2` | 33 / 22 ohm |
| `RB` | 6 ohm |
| output load | 10 ohm |
| JJ model | accepted Q2 `jjmit.cir` snapshot |
| source replay | accepted Q2 `inputs/40u` decks，逐字复制 |
| timestep / stop | 0.0125 ps / 170 ps |
| main / post window | `[94,130) ps` / `[140,170) ps` |

## 拓扑与 KCL

```text
IN ── Lin ── node1 ── BJs ── node2
                           ├─ BJL1 || RJ1 ── GND
                           └─ L1=3.91p ── node3 ── L2=4.50p ── node4
                                                ▲             ├─ BJL2 || RJ2
                                                │             └─ L0 → OUT
                                              RB / IBIAS
```

直接验证：

- node2：`I(BJs)=I(L1)+I(BJL1)+I(RJ1)`；
- node3：`I(L1)+I(RB)=I(L2)`；
- node4：`I(L2)=I(L0)+I(BJL2)+I(RJ2)`。

## Matched cases 与停止规则

执行顺序：

1. `logical1 + READ=0 control`；
2. `logical0 + READ=0 control`；
3. `logical0 + canonical READ`；
4. `logical1 + canonical READ`。

首个 control 若出现 artifact/solver failure、startup/free-running 或完整
phase/area-consistent transition，立即停止。其余 case 只有在 control bounded
时才执行。

完成四个 case 后无条件停止。禁止追加 L1/L2 point、bias、Ic/AREA、RJ、波形
重塑、physical BVM→12JSL→QB 或 JTL。

## 预注册测量

每个 case 直接保存 BJs/BJL1/BJL2 的 `P/V/I`，以及 `I(L1)`、`I(L2)`、
`I(Lin)`、`I(RB)`、`I(RJ1)`、`I(RJ2)`、`I(L0)`。

### Phase/area event evidence

所有 event claim 必须同时满足：

- continuous unwrapped phase；
- 同一个 JJ、同一个 monotonic segment；
- 该 segment 的直接同-JJ voltage area `∫Vdt/Φ0` 与 phase evolution 一致；
- post bounded/retrap，无第二完整 event。

`I>Ic`、voltage peak、total phase range 和旧 `fast_events` 不能单独作为 event
证据。

### Node routing / KCL

在 dominant comparison interval 报告三条 KCL 的 max-abs 与 RMS residual，并
比较 Q2/Q3/Q4 的 `F_local`、`F_L1` 和 control-subtracted `G_local`。

### BJL1 current decomposition

对每个 read1 dominant BJL1 comparison interval，分别报告：

- `∫max(I_BJL1,0)dt`；
- `∫min(I_BJL1,0)dt`；
- signed `∫I_BJL1 dt`；
- positive/negative area ratio或 cancellation fraction（仅作 diagnostic）。

不得用 signed area 的绝对值替代正负分解。

### Major phase segments and timing

分别报告 BJL1 的 major positive 与 major negative monotonic segments，包括
起止时间、phase turns、同段 area、方向和是否 complete。这样可区分 backward
phase motion 减小与 forward drive 增加。

对 BJs→BJL1 与 BJL1→BJL2 分别报告 dominant segment 的 onset、delay、overlap；
同时报告 BJL1 forward/backward phase、BJL2 phase 和 `BJL2/BJL1` transfer ratio。

## 机制分类

- Q4≈Q2：支持 proximal-L1-specific Q3 effect；
- Q4≈Q3：支持 common/total-inductance effect；
- Q4 减少 BJL1 cancellation 且 phase 超过 Q3：支持 downstream reflected-impedance/timing；
- Q4 反向/削弱 Q3：说明 L1/L2 placement 有 directional dynamic effect。

机制结论必须同时得到 current decomposition、phase dynamics、timing 和 KCL
的一致支持，不能由单一 scalar metric 决定。
