# Current QB N0-N4 closed/passive/replay baseline

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Registration

- Experiment ID: `bvm-qb-current-baseline-n0-n4-closed-passive-replay-v1-20260917`
- Parent HEAD: `b5be6a270960005d746ca3420891659bff54682f`; remote `bvm/master`: `b5be6a270960005d746ca3420891659bff54682f`.
- Study phase: `CALIBRATION`; role: `Experimental Operator + Evidence Packager`.
- Scientific interpretation: not authorized; this series reports exhaustive raw, mechanical statistics, and visualization QA only.
- Bit order: `b3b2b1b0=BVM1/BVM2/BVM3/BVM4`. Masks are N0=`0000`, N1=`0001`, N2=`0011`, N3=`0111`, N4=`1111`.
- Exact authorized solve count: `15`, in family order CLOSED N0-N4, PASSIVE N0-N4, REPLAY N0-N4.

## Frozen source authority

- JJ model: `../../../circuits/models/jjmit.cir`; SHA-256 `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`.
- BVM: `../../../test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/bvm_jm2_connected.cir`; SHA-256 `0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54`.
- Current QB: `../../../circuits/qb/bq_parameterized_v1.cir`; SHA-256 `f676ba1ecb9b2607631a5cfc2f99b7d67e09b9e821457015fba375b8a39f13b0`.
- JTL: `../../../test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/jtl2.cir`; SHA-256 `ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a`.
- Current QB extraction: `{"BJ1_area": 0.9, "BJ2_area": 2.0, "BJS_area": 4.0, "IBias_uA": 260.0, "L1_pH": 1.4, "L2_pH": 2.0, "L3_pH": 1.3, "Lin_pH": 1.5, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0}`; expected values: `{"BJ1_area": 0.9, "BJ2_area": 2.0, "BJS_area": 4.0, "IBias_uA": 260.0, "L1_pH": 1.4, "L2_pH": 2.0, "L3_pH": 1.3, "Lin_pH": 1.5, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0}`; status `PASS`.

## Frozen stimulus

- IDLE 0-50 ps; WRITE0 50-61 ps; zero-state read control 70-81 ps; WRITE1 90-101 ps; SETTLE 101-110 ps; final READ 110-121 ps; TAIL 121-200 ps.
- Amplitude 100 uA; edge 1 ps; plateau 9 ps; `.tran 0.1p 200p`; expected raw grid 0-199.9 ps.
- Only the final-read mask differs across N0-N4. No timing or amplitude modification is registered.

## Families

- CLOSED: BVM array -> COMMON_SL -> JSL1..8 -> current QB -> six-stage JTL -> 10 ohm terminal.
- PASSIVE: BVM array -> COMMON_SL -> JSL1..8; QB/JTL/terminal removed; `B_JSL8 JSL_NODE7 0` retained as the established passive endpoint convention.
- REPLAY: exact stored `I(B_JSL8)` from this experiment's PASSIVE raw -> `I_REPLAY 0 QBIN` -> current QB -> six-stage JTL -> 10 ohm terminal. No interpolation, smoothing, resampling, scaling, or sign correction.

## Analysis and visualization boundary

- Each run retains untouched raw, actual deck, stimulus, logs, metadata, and signal manifest.
- `V(IB|XBQ1)` is requested where applicable; if JoSIM does not emit that current-source voltage column, the per-run signal manifest records the known unsupported quantity explicitly rather than silently dropping it.
- Per-signal windows are 0-50, 50-61, 61-70, 70-81, 81-90, 90-101, 101-110, 110-121, 121-130, 130-150, 150-200, and 0-200 ps.
- Phase is retained in raw radians; unwrapped radians and `rad/(2*pi)` turns are navigation views only, never formal SFQ counts.
- No cross-run comparison visualization and no scientific mechanism, winner, or population interpretation is generated.

Final stop marker: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
