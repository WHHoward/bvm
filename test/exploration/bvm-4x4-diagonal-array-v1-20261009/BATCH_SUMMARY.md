# BVM 4×4 diagonal-array batch summary

Experiment: `bvm-4x4-diagonal-array-v1-20261009`  
Parent HEAD: `df0249419c7a91ceb72b1fb0ed1d04981a5f6c1b`  
Authorized/actual solves: **6/6**, serial D3_N0→D3_N4 then PAPER_1101_1101.  
State: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`; interpretation
`NOT_PERFORMED`.

Solver: `/home/howard/JoSIM/build/josim-cli`, JoSIM `v2.7.2837d13`, SHA-256
`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
Canonical BVM/QB/sJTL/CB/JJMIT hashes are in
`analysis/source_manifest.json`. T1 is reference-only; the current deck has
`T1_MODE=OFF`, no T1/CBU/DFF, and seven independent 2 Ω terminals.

## Run evidence

| Run | Case | Raw bytes | Raw SHA-256 | Probes | Artifact/QA |
|---|---|---:|---|---:|---|
| A001_D3_N0 | D3 SE mask empty | 81,217,670 | `af13bc5105c12919b7d93817d21ebd4a3f31123fb18f1e1d39b6a90958199c4d` | 242 | VALID / PASS |
| A002_D3_N1 | D3: R1C1 | 81,225,009 | `f977347a31d24a932262d2a87a145d344b96b56393bce99ebf592cf6dd7a2be2` | 242 | VALID / PASS |
| A003_D3_N2 | D3: R1C1,R2C2 | 81,226,282 | `62301133c8faa92e078032270091920710ff361ba052450c4c006092308e9ec4` | 242 | VALID / PASS |
| A004_D3_N3 | D3: R1C1,R2C2,R3C3 | 81,234,107 | `79357f4a5401f11cae7fc5ec1ba496b81a30fec24c6d426982f42c6fcbb56908` | 242 | VALID / PASS |
| A005_D3_N4 | D3: R1C1,R2C2,R3C3,R4C4 | 81,239,978 | `3b8cb325ed025ae83c3be83226284473357d5e7ec3a472dda6c75fcdd4050060` | 242 | VALID / PASS |
| A006_PAPER_1101_1101 | paper row/column masks | 81,256,691 | `a318d8c09a958886ab1b3ec8ed636bf42c7b46b7fc9055353cff47ae0432b9cc` | 242 | VALID / PASS |

Raw total: **487,399,737 bytes**. All runs have 24,999 samples with stored
`dt` from approximately 0.01 to 0.02 ps. The raw files were hash-checked before
and after analysis/plotting; no interpolation, resampling, or lossy transform
was used. No solver warning/error/missing-model marker was found in the scanned
logs.

## DOUT arithmetic

For each D0–D6 cell, the value is `signed area / 10^-20 V·s ; positive maximum
in µV @ time ps` over `[110,250) ps`. Full min/max/p2p values and the two
subwindows are in each run's `metrics.json`.

| Run | D0 | D1 | D2 | D3 | D4 | D5 | D6 |
|---|---|---|---|---|---|---|---|
| A001_D3_N0 | 1.5413; 0.05266@124.20 | 1.0635; 0.05057@112.81 | 1.0640; 0.05066@112.82 | 1.0646; 0.05069@112.82 | 1.0640; 0.05066@112.82 | 1.0635; 0.05057@112.81 | 1.5413; 0.05266@124.20 |
| A002_D3_N1 | 1.5413; 0.05407@124.20 | 1.0635; 0.05069@112.81 | 1.0640; 0.05079@112.82 | 1.0646; 0.05082@112.82 | 1.0640; 0.05079@112.82 | 1.0635; 0.05069@112.81 | 1.5413; 0.05407@124.20 |
| A003_D3_N2 | 1.5413; 0.05474@124.20 | 1.0635; 0.05127@112.81 | 1.0640; 0.05092@112.82 | 1.0646; 0.05095@112.82 | 1.0640; 0.05092@112.82 | 1.0635; 0.05127@112.81 | 1.5413; 0.05474@124.20 |
| A004_D3_N3 | 1.5413; 0.05541@124.20 | 1.0635; 0.05140@112.81 | 1.0640; 0.05151@112.82 | 1.0646; 0.05337@112.86 | 1.0640; 0.05151@112.82 | 1.0635; 0.05140@112.81 | 1.5413; 0.05541@124.20 |
| A005_D3_N4 | 1.5413; 0.05684@124.21 | 1.0635; 0.05198@112.82 | 1.0640; 0.05209@112.82 | 1.0646; 0.7772@124.67 | 1.0640; 0.05209@112.82 | 1.0635; 0.05198@112.82 | 1.5413; 0.05684@124.21 |
| A006_PAPER_1101_1101 | 1.5413; 0.8181@124.52 | 1.0635; 0.7899@124.66 | 1.0640; 0.02909@124.10 | 1.0646; 0.7939@124.67 | 1.0640; 0.04856@112.86 | 1.0635; 0.7907@124.66 | 1.5413; 0.8181@124.52 |

The preregistered PAPER target vector `[1,1,1,3,1,1,1]` remains a theoretical
reference, not an inferred event count. No threshold or event classifier was
registered.

## D3 key JJ arithmetic

In `[110,250) ps`, the largest absolute D3-chain phase delta across the six
runs was `0.001413 rad` at `P(BJ2|XBQ_R4C4)`. The D3 terminal CB (`XCB_D3_L4`)
had `BJ1 Δphase=7.73e-5 rad`, same-JJ voltage area about `2.5443e-20 V·s`;
`BJ2 Δphase=-1.60e-4 rad`, area about `-5.2586e-20 V·s`. Across the registered
JJ pairs/windows the maximum phase-vs-area residual was approximately
`1.90e-6` navigation turns. Complete QB/sJTL/CB per-junction P/V and
same-JJ area rows are preserved in the per-run `metrics.json`. These values are
arithmetic only and do not classify SFQ transmission or physical correctness.

## Visualization and reserved modes

Each run has the three requested classic `josim-plot2.py` pages; the D3
progression comparison is `plots/comparison/01_D3_progression.html`. Standalone
and comparison QA PASS, using native samples without resampling. HTML and
Plotly JS remain local and are excluded from archives.

`DIAGONAL_TERMINAL` is the only executable mode. `DIAGONAL_T1_INDEPENDENT` and
`DIAGONAL_T1_CHAIN` fail closed; the editable `config/T1_PARAMS.env` is
reference-only while `T1_MODE=OFF`. CBU, T1, and DFF were not implemented or
simulated.

## Archive

Raw total exceeds the single-archive safety target; the submit workflow creates
six per-run raw ZIPs plus one shared metadata ZIP. ZIP/member SHA and CRC QA are
detached in `PACKAGE_QA.json` files. Package identities will be filled here by
the one scoped submit operation:

<!-- PACKAGE_TABLE -->
| Archive | Bytes | SHA-256 |
|---|---:|---|
| `bvm-4x4-diagonal-array-v1-20261009_raw_handoff_A001_D3_N0_BVM4X4_20261009.zip` | 19097542 | `a720b89bfc318937c22e8c456cad80000b5aa47527d1470e4577b2413c851585` |
| `bvm-4x4-diagonal-array-v1-20261009_raw_handoff_A002_D3_N1_BVM4X4_20261009.zip` | 19238492 | `8e3d18c8ca9d24c4c88a2cd7bb34826154a2556d8d4b034a81d3bdf78c7ee063` |
| `bvm-4x4-diagonal-array-v1-20261009_raw_handoff_A003_D3_N2_BVM4X4_20261009.zip` | 19385661 | `a41e44a10b6021560a329047490b2b79b18a2f49d5d6bef145d81b46bba8a306` |
| `bvm-4x4-diagonal-array-v1-20261009_raw_handoff_A004_D3_N3_BVM4X4_20261009.zip` | 19517181 | `b8af1acc2241e56c77374734336f49719f1e476717c5b1337592c1409bb874f9` |
| `bvm-4x4-diagonal-array-v1-20261009_raw_handoff_A005_D3_N4_BVM4X4_20261009.zip` | 19573321 | `83e7d33b8ea44af3e80a7254596a93bf2b73ce51315add066a3f14a8dde1ec4d` |
| `bvm-4x4-diagonal-array-v1-20261009_raw_handoff_A006_PAPER_1101_1101_BVM4X4_20261009.zip` | 20384318 | `c3cd4bd7477b3b5b43b78313a9392808d78da9949d3a8feb593ca72bfbf28c46` |

Six per-run ZIP total: **117,196,515 bytes**.
| metadata v1 — superseded | 43,299 | `b707abbba18f9381ed60be0425ea5373630ad609cc48d1c46c8e38551891d30d` |
| metadata v2 — canonical | 44,789 | `19af77800333d2c596b25606c26ac84fbd0ae4101b5b14f83fefc121c5975be1` |

`metadata v1` is retained but **SUPERSEDED**: its embedded BATCH_SUMMARY hash
does not match the summary at its declared source commit. The six per-run ZIPs
and their raw hashes remain valid and unchanged. `metadata v2` is the bound
shared package, created from metadata commit `364dd2b6dc0589f1ca1de614a16583a32331a51d`;
package commit `5e4d085ebe82b69a8388d4b0de91532ce3e9c877` contains v2 and its
detached CRC/member-SHA QA. The metadata ZIP's own hash is recorded here and in
that QA sidecar; its embedded summary snapshot necessarily predates the
self-hash row. See `analysis/PACKAGE_SUPERSESSION.json` for the v1/v2 binding
record. The v1 ZIP remains in Git and the local mirror, unchanged and not used
as the canonical Drive archive.

Canonical archive set: six run ZIPs + metadata v2, **117,241,304 bytes** total.
Each ZIP's detached `PACKAGE_QA.json` is the member/CRC/SHA authority.

The Drive `BVM_Backages` folder link below is the archive entry point. The
current summary file is also uploaded separately so it includes the final
package table; the metadata ZIP retains its immutable source-commit snapshot.

Drive target: [BVM_Backages](https://drive.google.com/drive/folders/1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh).

No SFQ count, mechanism, logic-function, throughput, or convergence conclusion
is made. Timestep convergence remains `UNKNOWN`; automatic follow-up is false.

## BUS400 diagnostic batch — BVM4X4_BUS400_20261009

This is a separate, additive registration from A001–A006. The user-supplied raw
review classifies A001–A006 as `LOW_DRIVE_BASELINE / FUNCTION_NOT_ESTABLISHED`:
their artifact/mechanical QA remains valid, but they are not normal 4×4 function
evidence. Their raw, run manifests, and old ZIPs were not changed or reread.

- Starting parent HEAD: `3de08ba0fd5997b253269849dbc1a535786c8fd6`.
- Execution source HEAD: `3c1b5a197742526059dd368da1a865c1aed95162`.
- JoSIM: `v2.7.2837d13`, binary SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
- Exact solves: 2, serial; A007 then A008. Shared WL/BL source totals are 400 µA,
  cell-local SE is 100 µA, and all other topology/timing values remain frozen.
  The only case difference is the FINAL_READ SE mask: none vs R1C1.
- Both runs have 124 probes, 24,999 samples, stored time 0–249.99 ps,
  `dt_min=0.01 ps`, `dt_max=0.02 ps`; per-run static/raw/mechanical/standalone
  plot QA is `PASS`, artifact `VALID`. Solver stdout/stderr scan found no warning,
  non-convergence, or missing-model marker. The same raw SHA was observed before
  and after per-run analysis/plotting and again during paired comparison.

| Run | Mask | Raw bytes | Raw SHA-256 | Probe/QA |
|---|---|---:|---|---|
| A007_BUS400_D3_N0 | none | 41,641,922 | `eb6807ea87f2e19c92605e86a0b1ff53058d47ef1316e17366be1d88a78b9dc0` | 124 / VALID-PASS |
| A008_BUS400_D3_N1 | R1C1 | 41,610,504 | `6ff7e9676da5a87c334826aeed1e9b4eb81421a2fa77f7a523e1fa06c1b6bd7a` | 124 / VALID-PASS |

New raw total: **83,252,426 bytes**. This focus set is 124 signals versus 242
in A001–A006; each new raw is about 48.7% smaller than the prior 81 MB raw
reference. HTML remains local. Each run has two classic `josim-plot2.py` pages;
the matched comparison is
`plots/comparison/BUS400_D3_matched.html` (QA PASS, SHA-256
`a3f639ed6db970eba1ab7a0b62277a3fa7e30c08d9cfdc466d15669614251e2f`).

### Per-cell input branch arithmetic

The table gives the range across 16 BVM cells of each branch's signed time-mean
current, computed as registered `charge_c / (last_stored_s - first_stored_s)`
on actual stored samples. It is not a source-setpoint conversion or an equal-share
assumption; every cell's min/max/mean/charge is in its run's `metrics.json`.

| Window | WL per-cell time mean | BL per-cell time mean | SE per-cell time mean |
|---|---:|---:|---:|
| WRITE0 (both) | −90.992…−90.991 µA | −90.992…−90.991 µA | 0 |
| READ0 (both) | +90.991 µA (about ±0.001 µA across cells) | approximately 0 | +90.991 µA each cell |
| WRITE1 (both) | +90.991 µA (about ±0.001 µA across cells) | +90.991 µA (about ±0.001 µA across cells) | 0 |
| FINAL_READ N0 | +90.991 µA | approximately 0 | 0 all cells |
| FINAL_READ N1 | +90.055…+91.304 µA | −0.937…+0.312 µA | R1C1 +90.991 µA; other 15 cells 0 |

For A008, instantaneous FINAL_READ BL branch samples span −12.294 mA to
+10.529 mA across cells; this is retained as a measured transient, not assigned a
physical mechanism. All branch directions and exact per-cell/window arithmetic
remain in the run metrics.

### Output and same-JJ arithmetic

`FINAL_READ_RESPONSE=[110,250) ps` DOUT signed areas are in `10⁻¹⁵ V·s`; peaks
are positive maxima in µV at the shown stored-sample time. These are arithmetic,
not event counts.

| Run | D | Signed area (10⁻¹⁵ V·s) | Positive max (µV @ ps) |
|---|---|---:|---:|
| A007 | D0 | −0.000012378 | 0.1261 @ 124.19 |
| A007 | D1 | −0.000022014 | 0.1124 @ 112.79 |
| A007 | D2 | −0.000022714 | 0.1122 @ 112.80 |
| A007 | D3 | −0.000022739 | 0.1123 @ 112.80 |
| A007 | D4 | −0.000022714 | 0.1122 @ 112.80 |
| A007 | D5 | −0.000022014 | 0.1124 @ 112.79 |
| A007 | D6 | −0.000012378 | 0.1261 @ 124.19 |
| A008 | D0 | −0.000012378 | 0.1338 @ 124.18 |
| A008 | D1 | −0.000022014 | 0.1126 @ 112.79 |
| A008 | D2 | −0.000022714 | 0.1124 @ 112.79 |
| A008 | D3 | +2.067811 | 465.636 @ 139.53 |
| A008 | D4 | −0.000022714 | 0.1124 @ 112.79 |
| A008 | D5 | −0.000022014 | 0.1126 @ 112.79 |
| A008 | D6 | −0.000012378 | 0.1338 @ 124.18 |

Each run contains 138 same-JJ/window P/V arithmetic rows for the registered
focus set, including D3 BVM JM1/JM2, QB_R1C1, and every D3 sJTL/CB stage. The
maximum absolute phase-minus-voltage-area residual was `5.73e-6` navigation turns
in A007 and `9.91e-6` in A008. Raw phases remain radians; no JJ/event outcome is
classified here.

### Post-processing incident and archive plan

After both successful solves, the paired plot initially failed because a shared
raw reader applied its exact-header rule to a two-signal subset request. The
reader now allows subset reads for focused visualization while raw QA still
enforces the exact registered header. The comparison and handoff manifests were
rebuilt from the same two immutable raws; both SHA-256 values above were
unchanged. No solver was rerun.

The single delta is planned as
`handoff/bvm-4x4-diagonal-array-v1-20261009_delta_BVM4X4_BUS400_20261009.zip`.
Base is Git commit `3de08ba…`, metadata-v2 package
`bvm-4x4-diagonal-array-v1-20261009_metadata_v2_BVM4X4_20261009.zip` (SHA-256
`19af77800333d2c596b25606c26ac84fbd0ae4101b5b14f83fefc121c5975be1`), plus the
six immutable A001–A006 raw-package identities recorded in `DELTA_MANIFEST.json`.
It contains only new/modified files and A007/A008 raw; old raw is referenced, not
copied. The detached `PACKAGE_QA.json` is the final ZIP SHA/member/CRC authority.

Status remains `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW` after package
and commit; scientific interpretation is `NOT_PERFORMED`, and there is no
authorized follow-up.
