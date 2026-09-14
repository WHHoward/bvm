# BVM -> QB -> T1 interface topology v1 — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `bvm-qb-t1-interface-topology-v1-20260914`
- Generated at: `2026-09-14T12:28:07+08:00`
- Registration HEAD: `c5b6de3ecdc4acf9f2e41d3845a6ff5d446aed67`
- Remote `bvm/master` at registration: `c5b6de3ecdc4acf9f2e41d3845a6ff5d446aed67`
- Preflight status: `PASS`; solver has not been invoked at preflight.
- Solver: `JoSIM: Josephson Junction Superconductive SPICE Circuit Simulator
Copyright (C) 2020 by Johannes Delport (jdelport@sun.ac.za)
v2.7.2837d13 compiled on May 30 2026 at 20:37:57`; SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`

## Frozen source closure

- `canonical_qb`: `circuits/qb/bq_parameterized_v1.cir`; SHA-256 `f676ba1ecb9b2607631a5cfc2f99b7d67e09b9e821457015fba375b8a39f13b0`; frozen canonical QB include; exact user-registered text.
- `t1_cell`: `circuits/t1/t1_cell.cir`; SHA-256 `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237`; current T1 cell; no modification.
- `bvm_jm2_connected`: `test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/bvm_jm2_connected.cir`; SHA-256 `0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54`; current JM2-connected BVM source used by the latest 4x1 closure.
- `jtl2_source`: `test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/jtl2.cir`; SHA-256 `ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a`; current JTL source used for the six- and two-stage chains.
- `josim_solver`: `build/josim-cli`; SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`; recorded solver binary.
- `plotter`: `scripts/josim-plot2.py`; SHA-256 `0aaf0b4bfd148e073d318c9a0762ec13995045abd88cad28336fb8128c33a1d6`; standard descriptive visualization renderer.

The canonical QB file is byte-checked against the exact registered text. No deck defines QB parameters or copies the QB source. Existing BVM/JTL files are referenced by repository-relative includes; no old raw/reference artifact is copied.
The current `circuits/t1/t1_cell.cir` is included without modification and has `B_J7 N13 N17` plus `R_J7 N13 N17 10`; the old `R_J7 N18 N17` definition is absent.

## Exact run matrix and automatic gate

- Stage A: `jtl6/{0000,0001,0011,0111,1111}`.
- If the registered sanity screen flags `JTL6_T1_INTEGRATION_SANITY_FAILED`, stop and do not invoke `jtl2` or `direct`.
- If sane: Stage B `jtl2/{0000,0001,0011,0111,1111}`; Stage C `direct/{0000,0001,0011,0111,1111}`.
- Maximum and, if Stage A passes, exact physical solve count: 15. No retries, replay, parameter sweep, timing change, or follow-up solve.

## Frozen topology, timing, and bias

- `jtl6`: `4xBVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> T1.I`.
- `jtl2`: `4xBVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..2 -> T1.I`.
- `direct`: `4xBVM -> COMMON_SL -> JSL1..8 -> canonical QB -> T1.I`.
- Full galvanic BVM/JSL↔QB loop is retained; no passive capture, source replacement/scaling/filtering, topology modification, or extra/matching resistor is added. The only zero-drop link is the named `T1_I` observation terminal.
- History: `IDLE 0-50; WRITE0 50-61; IDLE 61-70; ZERO_STATE_READ_CONTROL 70-81; IDLE 81-90; WRITE1 90-101; SETTLE 101-110; FINAL READ 110-121; TAIL 121-200 ps`.
- Amplitude `100uA`, 1 ps rise/fall, 9 ps plateau; `.tran 0.1p 200p`. Masks are exactly `0000`, `0001`, `0011`, `0111`, `1111` with bit order `b3b2b1b0 = BVM1/BVM2/BVM3/BVM4`.
- T1: current unmodified cell; `V_BIAS1=1.67m`, `V_BIAS2=1.67m`, `I_BIAS3=35u`, `R_S=12`, `R_C=12`, `R_CLK_QUIET=5`; no clock source and CLK is not floating.

## Probes and registered arithmetic

- Every BVM: P/V/I for `B_JM1`, `B_JM2`, `B_JS1`, `B_JS2`; currents `L_M1`, `L_M2`, `L_M3`, `L_PM`, `L_PSL`, `L_SL`; drive-source currents are `I(I_WLn)`, `I(I_BLn)`, `I(I_SEn)`.
- Shared/JSL: `V(COMMON_SL)`, P/V/I `B_JSL1..8`, `I(B_JSL8)`, `V(QBIN)`.
- QB: I/V `LIN`, `L1`, `L2`, `L3`; P/V/I `BJS`, `BJ1`, `BJ2`; I `RJ1`, `RJ2`; `V(QBOUT)`.
- All present JTL levels: P/V/I `B01/B02`, `V(JTLx_OUT)`; T1 all 11 junctions and the requested input/output/inductor probes.
- Analysis windows use actual stored timestamps: `[70,81)`, `[90,101)`, `[101,110)`, `[110,121)`, `[121,126)`, `[126,150)`, `[150,200)` ps. Integrals are actual-grid trapezoids with no interpolation.
- P(...) is raw radians. Displayed turns are explicitly `rad/(2*pi)` and are navigation only, never an SFQ count.

## Mechanical sanity flags

- Voltage activity: at least `3` actual samples with `abs(V) >= 0.0002 V` in registered quiet/tail windows.
- Phase activity: `1` turn navigation threshold, activity only; T1 quiet/clock monitors and 0000 carry/J1 tail are checked.
- JTL6-to-T1.I link consistency: max `abs(V(JTL6_OUT)-V(T1_I)) <= 1e-09 V`.
- These are stop flags only, not SFQ, switching, Gate, or physical correctness criteria.

## Minimal layout override and stop

The user-requested minimal layout omits `screening/`, `references/`, `qa/`, `handoff/`, `visualization/run_summaries/`, and `analysis/archive/`; root-level machine-readable evidence is retained. Each run contains only `deck.cir`, `raw.csv`, `run.log`, and `plots/`.
After package QA and commit, stop at `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`; scientific interpretation, parameter modification, and follow-up solves are not authorized.
