# BVM R-loop branch timing decomposition (bvm-rloop-branch-timing-decomposition-v1-20260916)

- Status: `ANALYSIS_COMPLETE`
- Artifact status: `VALID`
- Scientific interpretation: `NOT_PERFORMED`; final branch category: `SCIENTIFIC_REVIEW_REQUIRED`.
- HEAD: `7ade840c731bc078eae0c87e42ca983aa74700dd`; exact grid `.tran 0.1p 200p`; delay is exactly `0.3 ps = 3 stored samples`.
- Forward path remains canonical BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> terminal.
- Intervention is per-instance ideal current forcing from node6 to node10; it is not a physical delay network or R_S/L_S3 equivalent.

## Mechanical exact gate

| family | mask | exact status | canonical candidates | exact candidates | BJ1/BJ2 first timing delta (ps) |
|---|---|---|---:|---:|---:|
| `RS` | `0011` | `PASS` | 2 | 2 | 0 |
| `RS` | `0111` | `PASS` | 4 | 4 | 0 |
| `LS3` | `0011` | `PASS` | 2 | 2 | 0 |
| `LS3` | `0111` | `PASS` | 4 | 4 | 0 |

## Delayed raw observations

| run | family | mask | ordered candidates | first BJ1/BJ2 (ps) | second BJ1/BJ2 (ps) | N3 JS1/JS2 focus p2p (turns) |
|---|---|---|---:|---|---|---|
| `RS_EXACT_0011` | RS | 0011 | 2 | 115.2/116.1 | 125.9/126.4 | 0.30890494/0.24523248 |
| `RS_EXACT_0111` | RS | 0111 | 4 | 113.8/114.8 | 117.4/118.3 | 6.3864044/6.3605665 |
| `LS3_EXACT_0011` | LS3 | 0011 | 2 | 115.2/116.1 | 125.9/126.4 | 0.30890494/0.24523248 |
| `LS3_EXACT_0111` | LS3 | 0111 | 4 | 113.8/114.8 | 117.4/118.3 | 6.3864044/6.3605665 |
| `RS_DELAY0P3_0011` | RS | 0011 | 2 | 115.2/116 | 125.9/126.4 | 0.31544148/0.24987246 |
| `RS_DELAY0P3_0111` | RS | 0111 | 4 | 113.8/114.8 | 117.3/118.3 | 6.4291018/6.4008697 |
| `LS3_DELAY0P3_0011` | LS3 | 0011 | 2 | 115.4/116.3 | 126.6/127.3 | 0.30185879/0.2549411 |
| `LS3_DELAY0P3_0111` | LS3 | 0111 | 3 | 113.9/114.9 | 117.9/119 | 5.8213298/5.9002429 |

All phase turns are raw-radian independent navigation values, never SFQ counts. `I_TOTAL` is imposed plus physical-branch current and is compared on the actual stored grid. Ideal-source power uses `P_absorb=Vbridge*I_source`; canonical energy is a physical bridge reference, not ideal-source energy.

Bridge sign audit, canonical/total/branch current comparison, source recovery, LS3/RS branch constitution, bridge voltage, energy, effect fraction `F_B`, active-cell symmetry, JM1/JM2, QB/JTL, and terminal records are in `provenance.json.analysis`.

Previous total-bridge replay, QBIN-boundary replay, LS3 static intervention, and TLINE evidence are referenced by hash only; no old artifact is modified or repackaged.

No final scientific category is assigned. `Outcome A-D` interpretation, mechanism ranking, physical implementation, and follow-up design remain UNKNOWN/review-gated.

- Raw/deck/metadata/log: `runs/`.
- PWL source data: `inputs/replay_sources/`.
- Mechanical QA/reviews/manifests: `analysis/`.
- Descriptive plots: `plots/`.
- Drive-only ZIP identity: `delivery_manifest.json`.

Stop marker: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
