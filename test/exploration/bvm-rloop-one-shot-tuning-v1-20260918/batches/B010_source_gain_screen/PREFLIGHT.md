# B010 — BVM source-gain sensitivity screen

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

Status: PRE-REGISTERED / PASSIVE ONLY / AWAITING MECHANICAL QA

Parent HEAD at registration: `1ffa76d7`.

Question: under the fixed asymmetric-shunt BVM baseline, which one-factor
direction changes the registered PASSIVE N1 source output while retaining the
N4 R-loop stress check?

Fixed topology and sources:

- PASSIVE BVM + COMMON_SL/JSL only; no QB, JTL, or terminal in these runs.
- `JS1_AREA=0.52`, `JS2_AREA=0.74`, `RSH_JS1=12`, `RSH_JS2=20` baseline.
- All BVM, stimulus, timing, DT, STOP, and source identities remain current
  registered values except the single listed variant knob.
- `MODE=passive`, `MASKS=0001,1111`, `DT=0.1p`, `STOP=200p`.

Registered variants:

| variant | changed knob | value |
|---|---|---|
| B0 | none | baseline |
| G1 | `JS1_AREA` | `0.46` |
| G2 | `LM3` | `8.0p` |
| G3 | `LM3` | `9.0p` |
| G4 | `RSL` | `10` |
| G5 | `CONTROL_SE_AMP` and `READ_SE_AMP` as one registered read-drive pair | `110u` |
| G6 | `RS` | `3.5` |

Authorized matrix: exactly seven independent user cases × two masks (`0001`,
`1111`), maximum fourteen new physical solves. No automatic sweep, no 2-D
combination, no CLOSED follow-up, no QB/JTL change, and no sentinel follow-up.

Required evidence: immutable raw CSV/deck/log/provenance, raw QA, plot QA,
full registered BVM probes, actual stored-grid arithmetic, and per-variant
strict one-knob provenance. Scientific Gate-R/Gate-S/Gate-Z interpretation,
gain-efficiency ranking, direction classification, and CLOSED recommendations
remain `SCIENTIFIC_REVIEW_REQUIRED` until explicitly authorized.
