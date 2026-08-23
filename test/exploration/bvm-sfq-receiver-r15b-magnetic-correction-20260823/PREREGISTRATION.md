# R15-B AFQ-3 magnetic constitutive topology correction

日期：2026-08-23
模式：Exploration / analytic preregistration only
父 checkpoint：`571fa918f9623e24ea8038bfb24c32087494316e`

## Status

`PREREGISTERED_PENDING_EXECUTION`

本文件定义一个新的 R15-B hypothesis；不修改 R15-A、canonical BVM、
`DCSFQ_BVM.cir` 或任何 accepted raw。R15-A 的 invalid mutual point 不被
偷偷修正或复用。

本轮尚未运行 JoSIM。

## Scientific question

在保持 R0b detector、J_SET/J_Q refractory stage、独立 J_OUT bias-powered
output valve 和 frozen DCSFQ backend 的前提下，physically realizable 的
split-winding/two-core transfer loop 是否能把 read1-selective Q-state
transient 传给 J_OUT，并避免原 R15-A 的非正定 mutual matrix、direct
Q→CTL bypass 和 passive-only R14 bottleneck？

## Frozen single point

### Unchanged from R15-A

- `R_IN=12 Ω`
- `L_TX=0.20 pH`
- `B_DET AREA=.50`, `I_DET=15 µA`
- `K_IN=-.80`
- `L_RET=5 pH`, `L_S=50 pH`
- `B_SET AREA=.08`, `I_SET=5.6 µA`
- `R_Q=2 Ω`, `L_Q=4 pH`, `B_Q AREA=.50`
- `L_CTL=4 pH`
- `B_OUT AREA=3.0`, `I_OUT=275 µA`, `R_OUT_SH=3 Ω`
- `R_SRC=.75 Ω`, `L_INJ=2 pH`
- frozen `DCSFQ_BVM.cir`, canonical BVM, loads, PWL timing

### New R15-B topology values

```text
L_FQ        N_FQ        N_FX       20 pH
L_FO        N_FX        0          20 pH
R_F         N_FQ        0          20 Ω
K_QFQ       L_Q         L_FQ       +0.90
K_FOCTL     L_FO        L_CTL      -0.90
K_QCTL      0
K_FQFO      0
```

`L_FQ` 和 `L_FO` 位于两个物理独立磁芯；二者通过 series damped current
loop 电连接，但没有 mutual。`R_F` 跨接整个 `L_FQ+L_FO` series branch。

### Parameter provenance

| parameter | provenance |
|---|---|
| R0b/DCSFQ/BVM values | `[FROZEN_FROM_ACCEPTED_EVIDENCE]` |
| `L_FQ=L_FO=20 pH` | `[DERIVED]`: preserve each R15-A local mutual numerator |
| `R_F=20 Ω` | `[DERIVED]`: preserve `(L_FQ+L_FO)/R_F=2 ps` |
| `K_QFQ=+.90` | `[DESIGNED_FROM_R15-A_LOCAL_COUPLING]` |
| `K_FOCTL=-.90` | `[DESIGNED_POLARITY_HYPOTHESIS]` for reverse-dotted output core |
| `K_QCTL=K_FQFO=0` | `[TOPOLOGY_CONSTRAINT]` from two-core interpretation |

## Matched cases

Exactly four cases are preregistered, using identical receiver and solver
settings:

1. logical1 + canonical READ
2. logical0 + canonical READ
3. logical1 + READ=0 control
4. logical0 + READ=0 control

`dt=0.0125 ps`、stop time `170 ps`、canonical source PWL、DCSFQ 10 Ω output
load and all observation windows are inherited from R15-A. The first runtime
check is the logical1 READ=0 control because J_OUT remains near critical at
`275/300=0.9167 Ic`.

## Required probes

Direct AFQ probes:

- `P/V/I(B_DET)`, `P/V/I(B_SET)`, `P/V/I(B_Q)`, `P/V/I(B_OUT)`;
- `I(L_TX)`, `I(L_S)`, `I(L_Q)`, `I(L_FQ)`, `I(L_FO)`, `I(L_CTL)`, `I(L_INJ)`;
- `I(R_Q)`, `I(R_F)`, `I(R_SRC)`, `I(I_DET)`, `I(I_SET)`, `I(I_OUT)`.

Frozen backend/source probes:

- DCSFQ B1/B2/B3 direct `P/V/I`, `I(L1)`, `V(DCS_A)`, `V(DCS_Q)`;
- `V(SL)`, `V(N6)`, `I(L_SL)`;
- `JM1/JM2/JS1/JS2` P/V and relevant branch currents.

## Success ladder and event evidence

Any complete local event must use the same JJ, same endpoints, same direction
and same time segment for:

- continuous unwrapped phase;
- monotonic segment reaching at least one full turn;
- same-JJ voltage-time area divided by `Φ0`;
- phase/area consistency;
- bounded post-event retrap with no second event/free-running.

The first-run ladder is:

1. `CONSTITUTIVE_AND_ARTIFACT_VALID`: four cases solve with finite, complete raw;
2. `DETECTOR_PRESERVED`: B_DET read1 retains strong activity and read0/control
   remain separated;
3. `ACTIVE_STATE_COMPRESSION`: J_SET/J_Q/J_OUT show bounded read1-selective
   sequence, with read0/control zero and no free-running;
4. `ACTIVE_GAIN_ESTABLISHED`: DCSFQ input is above R1a passive scale and is
   compared with 68.4/110.2/300 µA references;
5. `DCSFQ_ONE_SHOT`: B3 exactly one qualifying local event, read0/control zero,
   retrap and no second event.

A B3 event is not downstream JTL/SFQ delivery; no JTL/T1 is attached.

## Stop rules

Stop at the first valid occurrence of:

- `PRECHECK_NO_GO`
- `DETECTOR_LOADING_FAILURE`
- `POLARITY_FAILURE`
- `ACTIVE_STAGE_NO_TRIGGER`
- `ACTIVE_GAIN_ESTABLISHED_DCSFQ_SUBTHRESHOLD`
- `DCSFQ_ONE_SHOT_PASS`
- `MULTIFIRE`
- `NONSELECTIVE_TRIGGER`
- `FREE_RUNNING`
- `BACK_ACTION_FAILURE`
- `INCONCLUSIVE`

No post-result sweep or silent change to `K`, `L`, `R`, AREA, bias, BVM or
DCSFQ is allowed. If this point establishes active state compression but not
B3, the next question must concern interstage→DCSFQ matching, not a return to
R15-A's invalid mutual point.
