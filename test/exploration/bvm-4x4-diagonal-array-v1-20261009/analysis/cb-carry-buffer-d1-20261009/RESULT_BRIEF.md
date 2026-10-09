# A025/A026 D1 carry-side CB_0928 — evidence handoff

- Artifact/mechanical status: `PASS`; physical solves: `2`; scientific interpretation: `NOT PERFORMED`.
- The registered matrix is A025 (1111/1111) and A026 (1101/1101), global single clock at 200 ps.
- The A021→A023→A025 and A022→A024→A026 tables contain only actual-grid descriptive metrics; they do not classify SFQ events or mechanism.
- `P(...)` is stored in radians. `delta/(2π)` and voltage-area/Φ0 are navigation/arithmetic columns, not event counts.
- Same-JJ phase/voltage arithmetic uses identical raw samples and half-open registered windows; interpolation/resampling was not used.
- Independent reread of A025/A026 raw reproduced 330 registered waveform/current/phase-area values; max arithmetic discrepancy was 0.0 in stored precision (`NUMERICAL_RECHECK.json`).
- Timestep convergence: `UNKNOWN`; no follow-up solve authorized.

| Run | Raw bytes | Raw SHA-256 | Sample count | Mechanical QA |
|---|---:|---|---:|---|
| A021_CHAIN_ALL_GLOBAL_CLOCK | 95684744 | `85ffd3a00a6815115307d917c9b35d3b06dd7ac240c61ca8bfd47b957e975e9e` | 29999 | PASS |
| A023_CB_DIRECT_D1_ALL_CLOCK | 94468129 | `c56ed579b684cdb1fe122488ce1de85e544e9797710ff7443e8dd1c6097b280a` | 29999 | PASS |
| A025_CARRY_CB_D1_ALL_CLOCK | 76296565 | `c9b3f6b2c3f707c599794658950de7bbbd3bfd6b51455d637ac3e0eee14369c9` | 29999 | PASS |
| A022_CHAIN_PAPER_GLOBAL_CLOCK | 95786305 | `2095fc87f129e844abfe21a0ccafb21e9ef2c72b67e7b6c34c8ca8f50935d9cb` | 29999 | PASS |
| A024_CB_DIRECT_D1_PAPER_CLOCK | 94583444 | `20cb27683ab2455df6e424dcc74ab09446902389c62fb310b3cc2f4146ee86ed` | 29999 | PASS |
| A026_CARRY_CB_D1_PAPER_CLOCK | 76382166 | `f9b198ecad7a7eef7181d6f99c1d8febc28db5b47e11956f91ca3beb6b29f7aa` | 29999 | PASS |

Machine-readable arithmetic: `BATCH_ANALYSIS.json` and the CSV tables in this directory.
Standalone run HTML and the two classic common-signal triplet pages are under `plots/` and are not packaged.
No mechanism, isolation, SFQ-count, or multiplier-function conclusion is issued.
