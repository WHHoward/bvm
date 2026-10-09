# CB_DIRECT D1 A023/A024 evidence manifest

State: `MECHANICAL_QA_PASS_AWAITING_USER_REVIEW`  
Physical solves: exactly 2  
Scientific interpretation / event classification: `NOT_PERFORMED` / `NOT_CLASSIFIED`

Canonical CB_0928 remains unchanged and is identified in each run's source manifest by SHA-256 `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370`. New D1 connectivity has two zero-volt current-sensor branches meeting at CBU_JOIN_D1; no isolation or extra sJTL is present.

| Run | Raw bytes | Raw SHA-256 | Deck SHA-256 | Artifact / QA |
|---|---:|---|---|---|
| A023_CB_DIRECT_D1_ALL_CLOCK | 94468129 | `c56ed579b684cdb1fe122488ce1de85e544e9797710ff7443e8dd1c6097b280a` | `46263c34dbc04627dff5b9b584f3e06eac1cf25c602d39874bca6392e46c93b4` | VALID / PASS |
| A024_CB_DIRECT_D1_PAPER_CLOCK | 94583444 | `20cb27683ab2455df6e424dcc74ab09446902389c62fb310b3cc2f4146ee86ed` | `46263c34dbc04627dff5b9b584f3e06eac1cf25c602d39874bca6392e46c93b4` | VALID / PASS |

Matched pairs: A021/A023 (ALL) and A022/A024 (PAPER).

- Mechanical comparison: `analysis/cb-direct-d1-20261009/CB_DIRECT_D1_COMPARISON.json` (SHA-256 `b1dac2d53e4a91d72f576a61a5b8b8c51137ce976eee94392bf17b488aa60037`).
- Paired plot QA: `analysis/cb-direct-d1-20261009/COMPARISON_PLOT_QA.json` (SHA-256 `02928adeab59fbea85afc20974ba549e4b3190819baade489e82d25a1b61f2ae`).
- All-run metrics: `analysis/cb-direct-d1-20261009/CB_DIRECT_D1_METRICS.csv`.
- Paired common-signal metrics: `analysis/cb-direct-d1-20261009/PAIRED_COMPARISON.csv`.
- CB_DIRECT D1 focus metrics: `analysis/cb-direct-d1-20261009/CB_DIRECT_D1_FOCUS.csv`.
- Independent read-only same-JJ/raw arithmetic recheck: `analysis/cb-direct-d1-20261009/NUMERICAL_RECHECK.json`; 80 junction/window checks reproduced the stored phase and voltage-area metrics exactly, with both raw hashes unchanged.
- HTML is local and excluded from DELTA ZIPs.
- A001-A022 raw is referenced by exact package/raw identity, not recopied.
- No physical result is upgraded to SFQ count or functional success.
