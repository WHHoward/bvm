# PREFLIGHT — QB RJ1/L1 local sensitivity

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Status: **PASS**
- Preflight time: `2026-09-09T10:20:29+08:00`
- HEAD at preflight: `08c7320bdd6e871d9b9536dcd27f5e8b2b0d5604`
- Role: `Experimental Operator + Evidence Packager`
- Study phase: `EXPLORATORY / QUICK`; this is a registered local sensitivity matrix, not an optimization sweep.

## Exact authorized physical solves

| run | RJ1 | L1 | purpose |
|---|---:|---:|---|
| NOMINAL | 12.0 ohm | 2.0 pH | new internal matched baseline |
| L1_DOWN | 12.0 ohm | 1.9 pH | L1 decrease intervention |
| L1_UP | 12.0 ohm | 2.1 pH | opposite-direction L1 control |
| RJ1_UP_05 | 12.5 ohm | 2.0 pH | small RJ1 increase |
| RJ1_UP_10 | 13.0 ohm | 2.0 pH | larger RJ1 increase |

Exactly five physical solves are authorized. No combined RJ1+L1 point, other mask, other parameter, timestep/solver sensitivity or automatic follow-up is authorized.

## Frozen fixture and input closure

- Fixture: `test/exploration/bvmsim-jm2-single-vs-4bvm-shared-sl-v1-20260907/runs/array/deck.cir`, SHA-256 `85227538d48d69251f4276b94b28adfc83cd25f95aa6609fa9eb2375c873f1cf`; historical array reference raw SHA-256 `8543abc6d7a7d276c0bfa3159a4d3d37d569200e5fa30082466e66df8ab24dc2`.
- BVM: historical JM2-connected variant, SHA-256 `0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54`; canonical BVM is not used.
- JJ model: `circuits/models/jjmit.cir`, SHA-256 `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`.
- QB base: `BVMSim/BQ.cir`, SHA-256 `f3dcbf5f9bb3898faf5194b5f7c4771df3fa1ed16150496de4b52cb6f7256dfd`. The local derived parameterized copy is `ff67dbbe42feb6a33d4573fdfd84e4657d1d0fd241f9b497e231b23a936afe10` and changes only active `L1`/`RJ1` to registered parameter references.
- JTL: `BVMSim/library_josim/jtl2.cir`, SHA-256 `ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a`.
- Solver: `build/josim-cli`, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
- Topology: four BVMs on `COMMON_SL`; 8 x `jjmit area=5.0` JSL; QB; six JTL stages; `R_TERM=10 ohm`.

## Frozen stimulus and windows

Stored-1111 protocol; BVM1 final READ mask 1000; BVM1 `WL1=+100uA`, `BL1=0`, `SE1=+100uA`; BVM2--4 are quiet at final READ. Rise/fall are 1 ps and the plateau is 9 ps. `.tran 0.1p 200p` is fixed. Windows are half-open and use actual stored timestamps: `PRE_FINAL=[101,110) ps`, `EARLY_TRIGGER=[110,116) ps`, `FULL_READ=[110,121) ps`, `TAIL=[121,200) ps`, `FULL_FINAL=[110,200) ps`.

## Probes and analysis ceiling

The deck retains full registered BVM, COMMON_SL, 8-JSL, QB and all-six-stage JTL probes, including P/V/I where requested. Missing columns emitted by the solver are recorded as `UNKNOWN`; no signal is fabricated. Metrics use actual-grid trapezoid integration. Raw phase is radians; independent unwrap followed by explicit division by `2*pi` is display/derived arithmetic only. Phase displacement, voltage area, `I>Ic`, or a pulse-like trace is not an SFQ count.

## Mechanical gate

- Parameterized deck normalized text must equal the frozen ARRAY fixture template.
- Each variant may differ from NOMINAL in exactly one registered `.param` line.
- Raw outputs must not exist before execution; raw files are never overwritten.
- No interpolation, resampling, smoothing, time shift, alignment or parameter tuning is permitted.

Machine records: `analysis/preflight.json` and `analysis/deck_diff_qa.json`.

## Decision

Preflight passed. The five registered physical solves may execute directly.

Final state after the exact matrix and QA is `AWAITING_USER_REVIEW`.
