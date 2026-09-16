# LS3-only delay population validation — bvm-rloop-ls3-delay-population-validation-v1-20260916

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Registration

- Registration HEAD: `2099471a24f7938056ac762ff60c89636dcafa7d`; remote `bvm/master`: `2099471a24f7938056ac762ff60c89636dcafa7d`.
- Study phase: `EXPLORATORY`; role: `Experimental Operator + Evidence Packager`.
- Scientific review authorization: `false`; this run records mechanical evidence only.
- Previous N2/N3 LS3 branch-decomposition artifacts are immutable read-only context.

## Single question

Does the registered LS3-only 0.3-ps timing intervention preserve N1≈1 and N4≈4 while retaining the already-established N2=2 / N3=3 behavior?

This is an instance-specific ideal replay of canonical LS3 current, not a physical delay element or passive-equivalence proof.

## Frozen fixture

- Working point: L1=1.4 pH, L2=2.0 pH, IBias=260 µA, RJ1=32 Ω, RJ2=12 Ω, BJS area=4, `.tran 0.1p 200p`.
- Forward path: `BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> 10 Ω terminal`.
- Per instance: retain `R_S 6 10 3.0`; remove `L_S3 6 10 0.5P`; impose same-instance canonical `I(L_S3)` from node6 to node10.
- QB, QBIN, JSL, JTL, terminal, BVM parameters, stimulus and timestep are unchanged.
- Actual stored grid is retained; expected 1999 rows, 0–199.9 ps, and the only delay is `0.3 ps = 3 stored samples`.
- Delay: t<110 ps same sample; [110,110.3) ps holds the 110-ps sample; t≥110.3 ps uses exact index i−3.
- No interpolation, smoothing, resampling, amplitude scaling, sign modification, other delay, sweep, sentinel, or READ extension.

## Source raw authority

- `0001`: `test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910/references/reused/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001/raw.csv`; SHA-256 `7411226d2231dca0e1a3948660a82d7d88112baab8c18349cd83f4f94e6cf1b3`.
- `1111`: `test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910/runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111/raw.csv`; SHA-256 `0497b2d6822378c5b7491ab00abdfcf00d624ba9dd7e7a1c02046b5d4c3ed48c`.

## Mechanical source audit

- Canonical branch direction/KCL audit: `{"0001": "PASS", "1111": "PASS"}`.
- Checks: V(R_S)≈3I(R_S), V(L_S3)=V(R_S), node6/node10 KCL, positive node6→node10 orientation.
- Failure of this audit blocks source construction.

## Authorized solve order

1. `LS3_EXACT_0001`
2. `LS3_DELAY0P3_0001`
3. `LS3_EXACT_1111`
4. `LS3_DELAY0P3_1111`

No other physical solve is authorized. Exact fidelity is gated independently per mask; a delayed raw may be mechanically recorded after a failed exact gate but is marked uninterpretable for validation.

## Interpretation ceiling

N1 uses one ordered BJ1→BJ2→JTL1..6 candidate plus terminal clusters/area as corroboration. N4 uses phase landmarks, ordered JTL phase chains, JTL6/terminal valleys and total terminal area; the historical strict `complete_response_count` is shown but is not the primary N4 oracle.

All phase values remain raw radians; turns are independent unwrap/(2π) navigation only and are not SFQ counts. Final population labels and mechanism conclusions remain `NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED`.

Stop marker: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
