# T1 independent seven-output array batch preflight

> This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Identity and authorization

- Work unit: `BVM4X4_T1_ALL_20261009`; risk level: `NORMAL`.
- Parent HEAD: `c42ad75d39cf796cfe863b836f6f8154388a048a`.
- Exactly four JoSIM solves are authorized: A013 quiet/all, A014 pulse/all,
  A015 quiet/paper, and A016 pulse/paper. The runner stops at the first solver
  or mechanical-artifact failure; no retry or follow-up is authorized.
- This is an exploratory seven-output T1 integration, not a T1 truth-table or
  throughput Gate. Scientific interpretation is not authorized in this work unit.

## Sources and circuit boundary

- Reuse the live 4×4 BVM/QB/sJTL/CB generator and canonical sources; do not edit
  BVM, QB, sJTL, CB, or `jjmit`.
- Canonical T1: `circuits/t1/t1_cell.cir`, SHA-256
  `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237`.
- Shared `jjmit`: `circuits/models/jjmit.cir`, SHA-256
  `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`.
- The runner makes a run-local T1 source from `T1_PARAMS.env`; its default
  effective subcircuit body must match canonical T1. Canonical source stays
  unchanged.
- Each `DOUT_Dk` connects only through `V_T1_LINK_Dk` to `T1_I_Dk` and the
  matching `XT1_Dk`. Each channel has private CLK, Bias1/2/3, S and C nodes.
  All seven 2 Ω DOUT terminations are removed in this mode. No CBU, DFF, or
  added JTL is instantiated. The existing serial MERGE and configured sJTL/CB
  chain remains unchanged.
- `DIAGONAL_TERMINAL` remains the default and must reproduce immutable A012's
  deck SHA `6c539bcd9a5d670766fa873dc4ae48e39e07e5097174af07ac7cb7edad955318`
  in a render-only compatibility check.

## Frozen BVM baseline and run matrix

All four runs use the same existing write/read stimulus and these values:

```ini
ROW_WL_WRITE_AMPLITUDE=400u
COL_BL_WRITE_AMPLITUDE=400u
ROW_WL_READ_AMPLITUDE=400u
COL_SE_READ_AMPLITUDE=100u
SE_ENABLE_MASK=ALL
SJTL_COUNT_D0=1
SJTL_COUNT_D1=1,1
SJTL_COUNT_D2=1,1,1
SJTL_COUNT_D3=1,2,2,1
SJTL_COUNT_D4=1,1,1
SJTL_COUNT_D5=1,1
SJTL_COUNT_D6=1
DT=0.01p
STOP=250p
```

The only difference within each matched pair is `T1_CLK_MODE`.

| Run | ROW_BITS | COL_BITS | T1 clock | Configured inputs D0…D6 |
|---|---|---|---|---|
| A013_T1_ALL_QUIET | 1111 | 1111 | QUIET | 1,2,3,4,3,2,1 |
| A014_T1_ALL_CLOCK | 1111 | 1111 | PULSE | 1,2,3,4,3,2,1 |
| A015_T1_PAPER_QUIET | 1101 | 1101 | QUIET | 1,1,1,3,1,1,1 |
| A016_T1_PAPER_CLOCK | 1101 | 1101 | PULSE | 1,1,1,3,1,1,1 |

The configured input counts are topology arithmetic, not measured pulses or
received-event counts.

## T1 configuration

- All seven T1s use independent 1.8 mV Bias1/2/3 sources and independent 12 Ω
  S/C loads.
- QUIET: one independent 5 Ω clock-to-ground clamp per T1, no pulse source.
- PULSE: one independent source and 2 Ω series branch per T1:
  `PULSE(0 1.2m 170p 1p 1p 2p 50p)`.
- No clock phase/frequency/amplitude sweep is authorized.

## Probes, arithmetic, and interpretation ceiling

- Each channel records DOUT, T1 input voltage and link current; S/C voltage and
  load current; CLK (and pulse source node/current in PULSE); independent Bias
  branch currents; last CB BJ1/BJ2 P/V; and T1 B_J1/B_J2/B_J9/B_J10/B_J11 P/V.
- `P(...)` is radians. For each same JJ, actual stored rows and direction are
  used for unwrapped endpoint Δphase and trapezoid voltage area; report both in
  rad and V·s/Φ0 arithmetic, never as an SFQ count.
- Half-open windows use actual stored timestamps: PRE_CLOCK `[110,170)` ps,
  CLOCK_1 `[170,220)` ps, CLOCK_2 `[220,250)` ps, TOTAL `[110,250)` ps.
- Report signed area, extrema, peak timestamps and actual current/voltage branch
  values. A descriptive lobe-candidate rule is frozen in `METRIC_SPEC.json`;
  it is not an event/SFQ classifier. No binary Sum/Carry success threshold is
  registered.
- Timestep convergence and hardware behavior remain UNKNOWN. A local T1 JJ
  phase change alone does not establish downstream event reception or logic.

## Artifacts and stop

- Raw runs: `runs/A013_T1_ALL_QUIET` through `runs/A016_T1_PAPER_CLOCK`.
- Three classic responsive Plotly pages per run: overview, clock/output,
  selected D3 internal focus. HTML stays local and is excluded from ZIPs.
- Batch arithmetic/summary: `analysis/t1-array-20261009/`.
- Preserve every deck, log, source snapshot, raw, QA and SHA. Package only after
  all four have mechanical QA; then commit/push once and wait for user review.
