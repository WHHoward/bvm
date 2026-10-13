# Three-round per-bit output table

`DERIVED` output voltage-area screen; Φ0-normalized terminal areas are not SFQ counts. Event count status is `INCONCLUSIVE`.

| round | window (ps) | bit | signal | expected | signed area / Φ0 | absolute area / Φ0 | area screen | SFQ event count |
|---:|:---:|---:|---|---:|---:|---:|:---:|:---:|
| 1 | [180, 250) | 0 | `V(S_D0_OUT)` | 1 | -0.000355 | 0.016858 | FAIL | INCONCLUSIVE |
| 1 | [180, 250) | 1 | `V(S_D1_OUT)` | 0 | 1.000352 | 1.166491 | FAIL | INCONCLUSIVE |
| 1 | [180, 250) | 2 | `V(S_D2_OUT)` | 0 | 1.000352 | 1.164489 | FAIL | INCONCLUSIVE |
| 1 | [180, 250) | 3 | `V(S_D3_OUT)` | 0 | 1.000341 | 1.169604 | FAIL | INCONCLUSIVE |
| 1 | [180, 250) | 4 | `V(S_D4_OUT)` | 0 | 0.999600 | 1.173144 | FAIL | INCONCLUSIVE |
| 1 | [180, 250) | 5 | `V(S_D5_OUT)` | 1 | 1.000529 | 1.172546 | PASS | INCONCLUSIVE |
| 1 | [180, 250) | 6 | `V(S_D6_OUT)` | 1 | -0.000040 | 0.025559 | FAIL | INCONCLUSIVE |
| 1 | [180, 250) | 7 | `V(DFF_O)` | 1 | 1.003337 | 1.446786 | PASS | INCONCLUSIVE |
| 2 | [250, 320) | 0 | `V(S_D0_OUT)` | 1 | 1.000000 | 1.163739 | PASS | INCONCLUSIVE |
| 2 | [250, 320) | 1 | `V(S_D1_OUT)` | 0 | -0.000352 | 0.029927 | PASS | INCONCLUSIVE |
| 2 | [250, 320) | 2 | `V(S_D2_OUT)` | 0 | -0.000350 | 0.043453 | PASS | INCONCLUSIVE |
| 2 | [250, 320) | 3 | `V(S_D3_OUT)` | 0 | -0.000244 | 0.036866 | PASS | INCONCLUSIVE |
| 2 | [250, 320) | 4 | `V(S_D4_OUT)` | 0 | 0.999999 | 1.169955 | FAIL | INCONCLUSIVE |
| 2 | [250, 320) | 5 | `V(S_D5_OUT)` | 1 | 0.000045 | 0.032318 | FAIL | INCONCLUSIVE |
| 2 | [250, 320) | 6 | `V(S_D6_OUT)` | 1 | 1.000030 | 1.170444 | PASS | INCONCLUSIVE |
| 2 | [250, 320) | 7 | `V(DFF_O)` | 1 | 0.993745 | 1.494960 | PASS | INCONCLUSIVE |
| 3 | [320, 400) | 0 | `V(S_D0_OUT)` | 1 | 0.000000 | 0.021717 | FAIL | INCONCLUSIVE |
| 3 | [320, 400) | 1 | `V(S_D1_OUT)` | 0 | -0.000000 | 0.021960 | PASS | INCONCLUSIVE |
| 3 | [320, 400) | 2 | `V(S_D2_OUT)` | 0 | -0.000002 | 0.021971 | PASS | INCONCLUSIVE |
| 3 | [320, 400) | 3 | `V(S_D3_OUT)` | 0 | 0.999892 | 1.165813 | FAIL | INCONCLUSIVE |
| 3 | [320, 400) | 4 | `V(S_D4_OUT)` | 0 | -0.000001 | 0.021979 | PASS | INCONCLUSIVE |
| 3 | [320, 400) | 5 | `V(S_D5_OUT)` | 1 | 0.999424 | 1.163950 | PASS | INCONCLUSIVE |
| 3 | [320, 400) | 6 | `V(S_D6_OUT)` | 1 | 0.000004 | 0.021963 | FAIL | INCONCLUSIVE |
| 3 | [320, 400) | 7 | `V(DFF_O)` | 1 | 0.961833 | 1.390957 | PASS | INCONCLUSIVE |

Area-screen thresholds are the pre-registered task-local rule: ±0.30 Φ0 from the expected bit, with absolute-area limits 0.5 Φ0 (expected 0) and 1.6 Φ0 (expected 1). `FAIL` is only a screen result, not a physical verdict.
