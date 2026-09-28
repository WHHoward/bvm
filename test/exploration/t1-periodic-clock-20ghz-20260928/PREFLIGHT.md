# T1 Scheme-B 20 GHz periodic clock-only preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- experiment_id: `t1-periodic-clock-20ghz-20260928`
- parent HEAD: `e1b7355f39ce7b9e8cb7d4c216bdbb398a99cc3c`
- solver: `build/josim-cli`; SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- solver version: `JoSIM: Josephson Junction Superconductive SPICE Circuit Simulator
Copyright (C) 2020 by Johannes Delport (jdelport@sun.ac.za)
v2.7.2837d13 compiled on May 30 2026 at 20:37:57`
- T1 source: `circuits/t1/t1_cell.cir` SHA-256 `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237`
- jjmit model: `circuits/models/jjmit.cir` SHA-256 `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`
- exact topology: one XT1 T1 instance; I pin connected to ground; no BVM/QB/CB/sJTL.
- T1 internal netlist is source-verified and unchanged; R_J4 remains 4 ohm.
- Scheme-B biases: V_BIAS1=1.8m, V_BIAS2=1.8m, V_BIAS3=1.8m.
- output loads: R_S=12 ohm, R_C=12 ohm.
- clock source: `V_TRIG_CLK CLK_RAW 0 PULSE(0 1.2m 170p 1p 1p 2p 50p)`.
- clock series path: `R_TRIG_CLK CLK_RAW CLK 5`; R_CLK_QUIET is absent.
- scheduled triggers: 170p, 220p, 270p, 320p; pulse falls by 174 ps.
- solver transient settings: DT=`0.01p`, STOP=`370p`.
- exact authorized run matrix: one solve `A001_T1_CLK_ONLY`; raw `runs/A001_T1_CLK_ONLY/raw.csv`.
- USER_CASE SHA-256: `1c759f4c2c1b53c4a267df1c323e1afeb2216c10209196af9b8255f29c01a690`; metric spec SHA-256: `5d6073756f8a0b8bc039b48f2eccbee4416968a224059a8471f64b75880cf4d6`.
- probe profile: DEBUG; exactly 101 probes (registered below).
- phase raw units: radians. Turn conversion is arithmetic only; not an SFQ count.
- voltage integrals use trapezoids on actual stored time rows; no interpolation or resampling.
- clock arrival uses the preregistered half-peak stored-sample bracket; no interpolated crossing.
- pre-clock window: [150p,170p); cycles: [170p,220p), [220p,270p), [270p,320p), [320p,370p).
- inter-pulse tail for each cycle: [cycle_start+4p,cycle_end).
- exact stored-grid integration endpoints use first/last rows inside each half-open window.
- timestep, parameter, and solver sensitivity are UNKNOWN; no convergence or sensitivity run is authorized.
- interpretation ceiling: mechanical QA and registered arithmetic only; no SFQ-event, logic, truth-table, or system-throughput claim.
- prohibited: integrated array solve, other masks/runs, sweeps, retry, parameter changes, or T1 internal netlist changes.

## Registered probes

- `V(CLK_RAW)`
- `V(CLK)`
- `I(R_TRIG_CLK)`
- `V(S)`
- `V(C)`
- `I(R_S)`
- `I(R_C)`
- `V(N_BIAS1)`
- `V(N_BIAS2)`
- `V(N_BIAS3)`
- `P(B_J1|XT1)`
- `V(B_J1|XT1)`
- `I(B_J1|XT1)`
- `P(B_J2|XT1)`
- `V(B_J2|XT1)`
- `I(B_J2|XT1)`
- `P(B_J3|XT1)`
- `V(B_J3|XT1)`
- `I(B_J3|XT1)`
- `P(B_J4|XT1)`
- `V(B_J4|XT1)`
- `I(B_J4|XT1)`
- `P(B_J5|XT1)`
- `V(B_J5|XT1)`
- `I(B_J5|XT1)`
- `P(B_J6|XT1)`
- `V(B_J6|XT1)`
- `I(B_J6|XT1)`
- `P(B_J7|XT1)`
- `V(B_J7|XT1)`
- `I(B_J7|XT1)`
- `P(B_J8|XT1)`
- `V(B_J8|XT1)`
- `I(B_J8|XT1)`
- `P(B_J9|XT1)`
- `V(B_J9|XT1)`
- `I(B_J9|XT1)`
- `P(B_J10|XT1)`
- `V(B_J10|XT1)`
- `I(B_J10|XT1)`
- `P(B_J11|XT1)`
- `V(B_J11|XT1)`
- `I(B_J11|XT1)`
- `I(L1|XT1)`
- `V(L1|XT1)`
- `I(L2|XT1)`
- `V(L2|XT1)`
- `I(L3|XT1)`
- `V(L3|XT1)`
- `I(L4|XT1)`
- `V(L4|XT1)`
- `I(L5|XT1)`
- `V(L5|XT1)`
- `I(L6|XT1)`
- `V(L6|XT1)`
- `I(L7|XT1)`
- `V(L7|XT1)`
- `I(L8|XT1)`
- `V(L8|XT1)`
- `I(L9|XT1)`
- `V(L9|XT1)`
- `I(L10|XT1)`
- `V(L10|XT1)`
- `I(L11|XT1)`
- `V(L11|XT1)`
- `I(L12|XT1)`
- `V(L12|XT1)`
- `I(L13|XT1)`
- `V(L13|XT1)`
- `I(L14|XT1)`
- `V(L14|XT1)`
- `I(L15|XT1)`
- `V(L15|XT1)`
- `I(L16|XT1)`
- `V(L16|XT1)`
- `I(L17|XT1)`
- `V(L17|XT1)`
- `I(RB1|XT1)`
- `V(RB1|XT1)`
- `I(RB2|XT1)`
- `V(RB2|XT1)`
- `I(RB3|XT1)`
- `V(RB3|XT1)`
- `I(R_J10|XT1)`
- `V(R_J10|XT1)`
- `I(R_J11|XT1)`
- `V(R_J11|XT1)`
- `I(R_J3|XT1)`
- `V(R_J3|XT1)`
- `I(R_J4|XT1)`
- `V(R_J4|XT1)`
- `I(R_J5|XT1)`
- `V(R_J5|XT1)`
- `I(R_J6|XT1)`
- `V(R_J6|XT1)`
- `I(R_J7|XT1)`
- `V(R_J7|XT1)`
- `I(R_J8|XT1)`
- `V(R_J8|XT1)`
- `I(R_J9|XT1)`
- `V(R_J9|XT1)`

## Required output artifacts

`actual_deck.cir`, `raw.csv`, `run.log`, `stdout.txt`, `stderr.txt`, `metadata.json`,
`provenance.json`, `source_manifest.json`, `probe_manifest.json`, `analysis/raw_qa.json`,
`analysis/clock_cycle_metrics.json`, `analysis/clock_cycle_metrics.csv`, `analysis/plot_manifest.json`,
`analysis/plot_qa.json`, and the registered classic full-run and per-cycle HTML pages.
