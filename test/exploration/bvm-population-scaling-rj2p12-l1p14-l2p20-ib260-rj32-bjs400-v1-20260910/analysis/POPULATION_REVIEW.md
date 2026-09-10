# Selected-mask population scaling review

Scientific interpretation: NOT_PERFORMED.

Selected-mask classification: `SELECTED_MASK_EXPECTED_SCALING_NOT_OBSERVED`.
Weight-2 position classification: `NO_POSITION_DEPENDENCE_OBSERVED_AT_WEIGHT_2`.
Weight-3 position classification: `NO_POSITION_DEPENDENCE_OBSERVED_AT_WEIGHT_3`.
Saturation classification: `NO_REGISTERED_SATURATION_CLASSIFICATION`.

| mask | active BVMs | weight | control | BJ1 clusters | BJ2 clusters | QBOUT clusters | complete ordered response indices | terminal pulses | classification |
|:---:|:---|---:|:---|---:|---:|---:|:---|---:|:---|
| 0001 | BVM4 | 1 | CLEAN | 1 | 1 | 1 | [1] | 1 | 1_COMPLETE_RESPONSE_CANDIDATE |
| 0011 | BVM3,BVM4 | 2 | CLEAN | 2 | 2 | 2 | [1, 2] | 2 | 2_COMPLETE_RESPONSE_CANDIDATE |
| 0110 | BVM2,BVM3 | 2 | CLEAN | 2 | 2 | 2 | [1, 2] | 2 | 2_COMPLETE_RESPONSE_CANDIDATE |
| 1100 | BVM1,BVM2 | 2 | CLEAN | 2 | 2 | 2 | [1, 2] | 2 | 2_COMPLETE_RESPONSE_CANDIDATE |
| 1110 | BVM1,BVM2,BVM3 | 3 | CLEAN | 1 | 2 | 2 | [] | 4 | 0_COMPLETE_RESPONSE_CANDIDATE |
| 0111 | BVM2,BVM3,BVM4 | 3 | CLEAN | 1 | 2 | 2 | [] | 4 | 0_COMPLETE_RESPONSE_CANDIDATE |
| 1111 | BVM1,BVM2,BVM3,BVM4 | 4 | CLEAN | 2 | 3 | 2 | [] | 4 | 0_COMPLETE_RESPONSE_CANDIDATE |

Source-side [110,114.5)ps extrema and signed areas for active branches, I(B_JSL8), I(LIN), V(QBIN) and V(COMMON_SL) are stored per case in `mechanical_summary.json`.

Hamming weight is used only in this final comparison table; the generalized oracle receives no expected weight. Phase landmarks, voltage areas, terminal areas and response candidates are not SFQ counts.
