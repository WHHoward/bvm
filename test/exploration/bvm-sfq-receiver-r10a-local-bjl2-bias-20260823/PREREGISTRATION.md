# R10-A preregistration: output-side local BJL2 bias routing

日期：2026-08-23（Asia/Shanghai）
父基线：R9-A，`333945981332f9b37b4228e71d82201427b782cd`
研究阶段：`EXPLORATORY`
实验类型：single-point physics-informed exploration；不做 local-bias sweep。

## 唯一研究问题

在冻结 R9-A 的 native-QB topology、BVM、R6-B transformer、JJ/L/R/load 和
`IB=90 µA` 的前提下，output-side local BJL2 bias routing 能否把已经存在的
read1 state-selective BJL2 transient 推入 nonlinear/quantizing regime，同时
read0、两个 READ=0 controls 和 canonical BVM source/storage guard 保持有效？

## 物理预检与唯一选点

解析预检见 `analysis/R10A_ANALYTIC_PRECHECK.md` 及同目录 JSON。它使用 R9-A
`[80,90) ps` settled raw 校准完整三结 nonlinear load-line，而不是假设 local
current 全部流入 BJL2。

冻结唯一 local feed point：

| quantity | value |
|---|---:|
| injection node | native QB node 4 = BJL2 top terminal |
| source | independent voltage source, ramped to DC |
| source DC value | `21.4 mV` |
| expected DC feed | `214.0 µA` source → node 4 |
| series resistance | `R_LOCAL_BJL2=100 Ω` |
| series inductance | `L_LOCAL_BJL2=10 pH` |
| DC source impedance | `100 Ω` |
| impedance at 1.5 ps | `100+j41.89 Ω`, magnitude `108.42 Ω` |
| source return | independent voltage-source negative terminal to ground |

The branch is `BIAS → R_LOCAL_BJL2 → L_LOCAL_BJL2 → node 4`. It is a finite-
impedance active bias feed. It is not a resistor or passive branch placed directly
across BJL2; the independent source and series impedance remain explicit.

The calibrated continuation places the positive coupled static fold at
`216.223788 µA`. The selected point is `214.0 µA`, with predicted settled phase
`P(BJL2)=1.675409 rad`, coupled-fold distance `2.223788 µA`, and predicted split
`I(BJL2)=187.966748 µA`, `I(L2)=-26.033252 µA`. R9 read1's positive BJL2
activity excursion was `+2.590650 µA`; read0's was `+0.566390 µA`. The
first-order equivalent-feed margins are read1 `-0.366862 µA` and read0
`+1.657398 µA`. These values select the point only; neither static fold crossing
nor `I/Ic` is an event criterion.

## Frozen receiver and source

The following are unchanged from R9-A:

- canonical BVM topology and parameters;
- `SL → R_PRI=12 Ω → L_PRI=0.20 pH`, `L_SEC=1.00 pH`, `K=0.70710678`;
- native QB: `Lin=0.8 pH`, `L0=1.323 pH`, `L1=L2=2.50 pH`;
- `BJs AREA=1.33`, `BJL1 AREA=1.12`, `BJL2 AREA=1.89`;
- `RB=8.5 Ω`, `IB=90 µA`, `RJ1=33 Ω`, `RJ2=22 Ω`, `OUT` load `10 Ω`;
- `dt=0.0125 ps`, stop time `170 ps`, source PWLs and windows.

The experiment-local QB copy adds only the local feed branch to node 4. It does
not alter the native JJ model. With `jjmit.cir`, the actual area-scaled values are:

| JJ | AREA | Ic | C | RN | R0 |
|---|---:|---:|---:|---:|---:|
| BJs | 1.33 | 133 µA | 93.1 fF | 12.030 Ω | 120.301 Ω |
| BJL1 | 1.12 | 112 µA | 78.4 fF | 14.286 Ω | 142.857 Ω |
| BJL2 | 1.89 | 189 µA | 132.3 fF | 8.466 Ω | 84.656 Ω |

## Matched cases

Exactly one run per case, with the same receiver and local source:

1. `read1`: logical1 + canonical positive READ;
2. `read0`: logical0 + canonical positive READ;
3. `logical1-read0-control`: logical1 + READ=0;
4. `logical0-read0-control`: logical0 + READ=0.

## Required probes and windows

Directly probe `P/V/I(BJs|XBQ)`, `P/V/I(BJL1|XBQ)`, and `P/V/I(BJL2|XBQ)`;
`I(Lin|XBQ)`, `I(L1|XBQ)`, `I(L2|XBQ)`, `I(L0|XBQ)`, `I(RB|XBQ)`,
`I(RJ1|XBQ)`, `I(RJ2|XBQ)`; local branch currents `I(R_LOCAL_BJL2|XBQ)`,
`I(L_LOCAL_BJL2|XBQ)`, source current `I(V_BJL2_BIAS)`, `V(BIAS)` and
`V(N_LOCAL_BJL2|XBQ)`; `SL/N6`, `OUT_Q`, transformer currents/voltages, and
`JM1/JM2/JS1/JS2`.

Use half-open windows:

- settled operating point: `[80,90) ps`;
- causal activity: `[94,130) ps`;
- post/retrap and source guard: `[150,170) ps`;
- storage read-state guard: `[20,90) ps`.

## Event and verdict rules

An output-local event requires all of:

- continuous unwrapped `P(BJL2|XBQ)` trajectory;
- at least one monotonic segment with `|Δphase|/(2π) >= 1`;
- same segment, same JJ and same voltage direction, direct `V(BJL2|XBQ)` area
  consistent with the phase evolution;
- post-event bounded retrap, with no subsequent free-running or second complete
  segment.

Current above `Ic`, a voltage peak, activity range, or static saddle crossing alone
cannot qualify an event. There is no JTL/T1 in this experiment, so no downstream
SFQ-delivery claim is possible.

Primary classifications:

- `BJL2_LOCAL_PASS_WITH_SELECTIVITY` only if read1 has qualifying local activity,
  read0/controls have zero qualifying segments, and source/retrap guards pass;
- `NONLINEAR_LOCAL_GAIN_WITH_SELECTIVITY` if read1 becomes strongly nonlinear but
  no complete local event is established;
- `PROPORTIONAL_SUBTURN_GAIN_CLOSE_LOCAL_BIAS_ROUTE` if read1/read0 remain bounded,
  phase/area-consistent sub-turn activity without threshold-like separation;
- `BACK_ACTION_OR_NONSELECTIVE_FAILURE` for source/storage guard failure,
  free-running, or control/read0 complete activity;
- `INCONCLUSIVE` for invalid/truncated data or missing required probes.

If the result is only proportional sub-turn gain, stop local-bias routing and move
the next design question to explicit temporal rectification/hold in a BVM-specific
QB redesign. Do not sweep this local bias point.

## Artifact policy

Raw CSVs, netlists, command logs, analysis script, report, summary and SHA-256 list
are immutable outputs of this independent Exploration directory. The canonical BVM
and existing R9-A evidence are not modified.
