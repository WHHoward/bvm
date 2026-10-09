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
Package creation pending.

Drive target: [BVM_Backages](https://drive.google.com/drive/folders/1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh).

No SFQ count, mechanism, logic-function, throughput, or convergence conclusion
is made. Timestep convergence remains `UNKNOWN`; automatic follow-up is false.
