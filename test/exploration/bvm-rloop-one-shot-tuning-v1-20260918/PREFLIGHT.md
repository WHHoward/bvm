# BVM R-loop one-shot readout tuning v1

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Registration

- Experiment ID: `bvm-rloop-one-shot-tuning-v1-20260918`
- Study phase: `EXPLORATORY`
- Role: `Experimental Operator + Evidence Packager`
- Parent HEAD: `a80302e44a75a42991a00f0175fb93ac580dd42`
- `bvm/master` at registration: `a80302e44a75a42991a00f0175fb93ac580dd42`
- Scientific review authorized: `false`
- Scientific interpretation: `NOT_PERFORMED`
- Automatic follow-up: `NONE`

## Question

For the current canonical BVM topology and current QB held fixed, does equal
parallel damping on JS1 and JS2 expose a damping region in which post-read
multiple progression is reduced while S-loop storage and passive population
output remain reviewable?

This platform does not answer that question automatically.

## Frozen authority

- JJ model: `circuits/models/jjmit.cir`
  - SHA-256: `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`
- Canonical BVM source: `test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/bvm_jm2_connected.cir`
  - SHA-256: `0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54`
- Current QB: `circuits/qb/bq_parameterized_v1.cir`
  - SHA-256: `f676ba1ecb9b2607631a5cfc2f99b7d67e09b9e821457015fba375b8a39f13b0`
- JTL: `test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/jtl2.cir`
  - SHA-256: `ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a`
- JoSIM: `build/josim-cli`, `v2.7.2837d13`, recorded at solve time.

Current canonical BVM values read from the authority source:

```text
JS1_AREA=0.74
JS2_AREA=0.74
LS1=0.5p
LS2=0.5p
LS3=0.5p
RS=3.0
LPSL=0.5p
RSL=12.0
LSL=0.4p
```

The parameterized clone keeps the canonical topology and these values for the
registered Stage A. The only Stage-A additions are `R_JS1_SHUNT` and
`R_JS2_SHUNT`; `OPEN` omits the corresponding resistor.

## Exact Stage-A solve authorization

- `A000_CANONICAL`: PASSIVE, OPEN/OPEN, masks `0000,0001,0011,0111,1111`
- `A001`: PASSIVE, 20/20 ohm, the same five masks
- `A002`: PASSIVE, 12/12 ohm, the same five masks
- `A003`: PASSIVE, 8/8 ohm, the same five masks
- Total: exactly `4 × 5 = 20` physical solves.

No 5 ohm point, no other shunt, no amplitude scaling, no QB tuning, no LS3/RS
tuning, no sentinel follow-up, and no automatic sweep are registered.

## Stimulus and windows

- Bit order: `b3b2b1b0=BVM1/BVM2/BVM3/BVM4`
- IDLE `0–50 ps`
- WRITE0 `50–61 ps`
- post-WRITE0 settle `61–70 ps`
- zero-state read control `70–81 ps`
- post-control `81–90 ps`
- WRITE1 `90–101 ps`
- pre-final-read settle `101–110 ps`
- final read `110–121 ps`
- immediate recovery `121–130 ps`
- long tail `150–200 ps`
- pulse amplitude `100 uA`, edge `1 ps`, plateau `9 ps`
- `.tran 0.1p 200p`

## Observability and analysis boundary

The raw manifest requests JM1/JM2 P/V/I, LM1/LM2/LM3/LPM I/V, WL/BL/SE,
JS1/JS2 P/V/I, LS1/LS2/LS3/RS/LPSL/RSL/LSL I/V, COMMON_SL, all JSL P/V/I,
and closed-mode QB/JTL/terminal signals. Unsupported raw quantities are listed
explicitly in each manifest and are never silently removed.

Gate-S metrics are protocol-window arithmetic against A000; no fixed 5% or 10%
threshold is introduced. Gate-R reports raw radians, unwrapped radians,
rad/(2*pi) navigation turns, voltage area, crossing locations, and event-like
activity descriptions. Phase turns are not formal SFQ counts.

Population output is measured from passive `I(B_JSL8)` using peak, signed area,
absolute area, RMS, support duration, lobe timing, and zero crossings. No strict
1:2:3:4 requirement is imposed.

## Stop rule

After exact solves, mechanical QA, compact visualization, evidence packaging,
and commit, stop at:

`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`

