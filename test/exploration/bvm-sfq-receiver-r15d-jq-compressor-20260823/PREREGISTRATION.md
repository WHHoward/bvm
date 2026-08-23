# R15-D — split-node + independent J_Q bias + RL refractory compressor

## Status

- Tier: Exploration, single frozen point
- Date: 2026-08-23
- Parent evidence: R15-C `97598b4dc3d461b79310a15108f170eb16f7fb91`
- Scientific question: can the causal, read1-selective R15-C J_SET modulation drive a bounded, refractory J_Q state when J_SET and J_Q are connected at a split node and J_Q receives independent bias energy?
- Scope: canonical BVM → frozen R0b B_DET → R15-C finite-impedance J_SET network → R15-D J_Q compressor

This is a new independent Exploration. Existing canonical circuits and R15-C raw evidence are not modified or overwritten.

## Frozen topology and point

R15-C upstream values remain frozen, except for the required split-node interface:

```text
R_IN    IN     N_PICK   12 Ω
L_TX    N_PICK N_DET    0.20 pH
B_DET   N_DET  0        jjmit AREA=0.50
I_DET   0      N_DET    15 µA DC PWL
I_SET   0      N_S0    5.6 µA DC PWL
R_BIAS  N_S0   0       27.5 Ω
L_RET   N_S0   N_S1     5 pH
L_S     N_S1   N_S2    50 pH
B_SET   N_S2   N_QJ    jjmit AREA=0.08
K_IN    L_TX   L_S    -0.80

I_Q     0      N_QB    PWL: 0 at 0 ps, 2.30 µA at 2 ps,
                       2.30 µA through 170 ps
R_Q     N_QB   0        2 Ω
L_Q     N_QB   N_QJ    40 pH
B_Q     N_QJ   0       jjmit AREA=0.10
```

The B_SET lower terminal change from ground to `N_QJ` is the single required interface extension. It changes the loaded boundary and therefore all R15-C B_SET waveforms must be re-established from R15-D raw data.

The intended DC paths are:

```text
I_SET → N_S0 → (R_BIAS || L_RET) → ground / N_S1 → L_S → B_SET → N_QJ → B_Q → ground
I_Q   → N_QB → (R_Q || L_Q) → N_QJ → B_Q → ground
```

At the split node, the B_SET current and the L_Q current combine through B_Q. The independent I_Q source supplies the possible regeneration energy; the BVM and B_DET supply state information, not the intended J_Q switching energy.

## Matched cases and execution order

All cases use the same netlist, model snapshots, PWL source timing, timestep, stop time, and probes:

1. `logical1-read0-control` — run first.
2. `logical1-read` — run only if case 1 is bounded and source-stable.
3. `logical0-read`.
4. `logical0-read0-control`.

Simulation settings: `.tran 0.0125p 170p`; the canonical BVM state/write/read PWL sources are inherited from R15-C wrappers.

If the first control has startup/self-running, a complete control event, or obvious BVM source instability, stop without running the other three cases.

## Preregistered evidence

For B_DET, B_SET, and B_Q, use raw continuous phase, unwrapped phase, monotonic segments, same-JJ/same-segment voltage area, event onset, and post-event behavior. A current peak, voltage peak, or phase range alone is not an event.

For this local Exploration, a complete candidate is a continuous monotonic segment with phase change ≥ 1.0 turn and same-segment voltage area within 5% of the phase change (plus an absolute residual allowance of 0.02 turn). This is a task-local reporting rule, not a global SFQ metric freeze.

For the refractory check, compare `I(L_Q)` with the settled pre-read window `[80, 90) ps`:

- depletion depth: pre-event median minus the post-event minimum;
- minimum time: time of that minimum;
- recovery: first post-minimum time at which 90% of the depletion has recovered, if present, and the post window `[150,170] ps` median.

The timing of the depletion/minimum must be compared with later B_DET lobes. Absence of a second event alone is not refractory evidence.

Source guards are compared against the R15-C raw cases and the canonical/no-receiver baseline as documented by the accepted R15-C report: `V(SL)`, `V(N6)`, `I(L_SL)`, `JM1/JM2`, and `JS1/JS2` post-window behavior.

## Preregistered staged interpretation

- Stage 1 `UPSTREAM_CAUSAL_PRESERVED`: B_DET discrimination remains intact; loaded B_SET retains state-selective read1 response and read0/control margin.
- Stage 2 `JQ_ONE_SHOT`: read1 has one complete bounded B_Q transition; read0/control have zero complete B_Q transitions.
- Stage 3 `REFRACTORY_ESTABLISHED`: the first B_Q event/activity is accompanied by directly observed L_Q depletion and later recovery aligned with subsequent detector lobes.
- Stage 4 `SOURCE_GUARD`: source/storage disturbance is not materially worse than the accepted R15-C comparison.

Overall labels are selected only after the four cases:

`JQ_CAUSAL_NEAR_THRESHOLD`, `JQ_ONE_SHOT_REFRACTORY_PASS`, `NONSELECTIVE_TRIGGER`, `MULTIFIRE`, `UPSTREAM_CAUSAL_LOADING_FAILURE`, `FREE_RUNNING`, or `INCONCLUSIVE`.

No automatic change to `I_Q`, `R_Q`, `L_Q`, B_Q AREA, B_SET AREA, bias, coupling, or any DCSFQ/JTL/T1 element is authorized by this preregistration.

