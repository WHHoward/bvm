# BVM 2×2 → T1_C1 batch summary

Batch `BVM2X2_T1_C1_20261008` completed as registered: **8 physical solves**,
in order Q0–Q3 then P0–P3; no retries or follow-up solves. Status:
`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.

Remote `master` parent HEAD: `7eb7983c8091a3933e871246754a47d199cabd67`.
The implementation/evidence and package commits are recorded in the Git history
and detached package QA files. Solver: `/home/howard/JoSIM/build/josim-cli`,
JoSIM `v2.7.2837d13`, SHA-256
`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.

## Frozen setup and artifact status

Only C1 was connected to canonical T1 through `V_T1_LINK`; C2 remained a
separate 2 Ω terminal. The two column chains remained isolated. All runs used
SHARED/CELL/CROSSPOINT, `QB_CB=0,0`, `SJTL_COUNT=1,1`,
`POST_SJTL_CB=1,1`, Bias B `1.8m/1.8m/1.8m`, `R_S=R_C=12 Ω`,
`DT=0.01p`, `STOP=250p`. PULSE used the registered
`PULSE(0 1.2m 170p 1p 1p 2p 50p)` through 2 Ω; QUIET used only
`R_CLK_QUIET=5 Ω`.

| Run | ROW/COL | Clock | Probes | Raw bytes | Raw SHA-256 | Static/raw/stimulus/plot/provenance/mechanical |
|---|---|---:|---:|---:|---|---|
| A019_T1_C1_Q0 | 00/00 | QUIET | 151 | 50,708,661 | `7a5b865cc087243e1d4189cadebc6ce6c2ccdc8f20c40744517ae3944c349b13` | PASS / PASS / PASS / PASS / PASS / PASS |
| A020_T1_C1_Q1 | 10/10 | QUIET | 151 | 50,741,476 | `58a39f34eb364f1665b2b5374957ef1d1820b0523cd19dfb6e4fcc39ea1f0e37` | PASS / PASS / PASS / PASS / PASS / PASS |
| A021_T1_C1_Q2 | 01/10 | QUIET | 151 | 50,726,760 | `5c711d54cd1c8a5466595b9b4c2cc4bd50959962a99f02bd9b8e003318fecd89` | PASS / PASS / PASS / PASS / PASS / PASS |
| A022_T1_C1_Q3 | 11/10 | QUIET | 151 | 50,722,627 | `b84d57037580201a145d55148cca143aaf1b85ab44a35080a4bd68ef41610bb3` | PASS / PASS / PASS / PASS / PASS / PASS |
| A023_T1_C1_P0 | 00/00 | PULSE | 152 | 51,087,559 | `b8ebafc5283bff0187e30a7984d9b4f7889533a6b23b50c0defb44e8463f2d61` | PASS / PASS / PASS / PASS / PASS / PASS |
| A024_T1_C1_P1 | 10/10 | PULSE | 152 | 51,083,593 | `45a0dddf579adbfa8ff0ada085185f9983dba8448609a76286987b2d45d8498c` | PASS / PASS / PASS / PASS / PASS / PASS |
| A025_T1_C1_P2 | 01/10 | PULSE | 152 | 51,085,250 | `e6d653c9e232ab7a5dd936bf8aec05ca3b210d9818ca08e62882881c4cd5c958` | PASS / PASS / PASS / PASS / PASS / PASS |
| A026_T1_C1_P3 | 11/10 | PULSE | 152 | 51,077,361 | `441bcc0cac88fe37a6e12d6f34b60ae4d7ad0f399acf4aa2b1a24bbd650bef74` | PASS / PASS / PASS / PASS / PASS / PASS |

All raw files contain 24,999 stored rows; recorded `dt_min=0.01 ps`,
`dt_max=0.02 ps` (adaptive, nonuniform grid). Raw total: **407,233,287 bytes**.
Compared with A018's 284 probes / 95,388,793 raw bytes, this profile uses
151 QUIET / 152 PULSE probes and averages about **46.6% fewer raw bytes** per
run. No timestep increase, downsampling, interpolation, or lossy conversion was
used. Each run retains one stdout and one stderr file.

The canonical source hashes were unchanged and recorded per run:
BVM `ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7`,
QB `82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a`,
sJTL `3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688`,
CB `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370`,
T1 `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237`,
and shared jjmit `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`.

## Raw-grid arithmetic highlights

The complete per-run, per-junction and per-window calculation is in
`analysis/t1_batch_arithmetic.json`; its independent QA is
`analysis/t1_batch_arithmetic_qa.json`. Phase is radians. `rad/(2π)` and
voltage-area/Φ0 are arithmetic/navigation only, not event counts. The table
below reports positive maxima and signed area; each cell is `min..max mV;
positive-maximum time ps; signed area in 10^-15 V·s`. `CLK_RAW` is absent in
QUIET. The timestamp is a peak timestamp, not a threshold-defined arrival.
C2 lists measured VOUT peak-to-peak mV in that window.

| Run | Window (ps) | CLK_RAW max mV@ps | CLK max mV@ps | T1_I max mV@ps | S min..max; t+; area | C min..max; t+; area | C2 p2p mV |
|---|---|---:|---:|---:|---|---|---:|
| A019_T1_C1_Q0 | 110–170 | — | 5.752e-06@110.33 | 5.767e-05@112.30 | -1.009e-05..1.107e-05;110.31;3.002e-06 | -1.909e-05..1.994e-05;110.69;7.513e-06 | 0.0001037 |
| A019_T1_C1_Q0 | 170–220 | — | 3.837e-14@172.93 | 1.230e-11@170.12 | -7.796e-13..7.899e-13;171.16;2.101e-13 | -2.604e-12..1.816e-12;171.45;-3.102e-13 | 3.134e-11 |
| A019_T1_C1_Q0 | 220–250 | — | 1.644e-14@220.54 | 5.481e-14@221.76 | -3.151e-14..3.699e-14;238.13;5.834e-15 | -1.678e-14..2.124e-14;220.00;1.836e-14 | 0 |
| A020_T1_C1_Q1 | 110–170 | — | 0.03639@134.12 | 1.079@133.15 | -0.0901..0.1088;134.02;0.1766 | -0.2273..0.1431;134.33;0.03217 | 0.0001114 |
| A020_T1_C1_Q1 | 170–220 | — | 9.405e-10@170.52 | 1.624e-08@170.00 | -2.169e-09..3.269e-09;170.60;1.822e-09 | -3.302e-09..3.737e-09;171.01;1.546e-09 | 9.499e-10 |
| A020_T1_C1_Q1 | 220–250 | — | 5.481e-15@220.00 | 2.192e-13@224.52 | -8.495e-14..1.452e-13;225.19;2.114e-14 | -1.343e-13..1.466e-13;225.84;2.357e-14 | 0 |
| A021_T1_C1_Q2 | 110–170 | — | 0.03639@126.89 | 1.077@125.93 | -0.09001..0.1088;126.79;0.1766 | -0.2274..0.1434;127.10;0.03217 | 0.0002234 |
| A021_T1_C1_Q2 | 170–220 | — | 6.722e-10@171.09 | 1.046e-08@170.48 | -2.740e-09..2.221e-09;171.17;5.092e-10 | -3.863e-09..2.563e-09;171.58;-9.328e-10 | 2.985e-09 |
| A021_T1_C1_Q2 | 220–250 | — | 2.740e-14@220.04 | 2.192e-13@236.11 | -7.399e-14..1.206e-13;230.40;1.699e-13 | -1.336e-13..1.240e-13;233.91;6.612e-14 | 3.014e-13 |
| A022_T1_C1_Q3 | 110–170 | — | 0.03744@136.72 | 1.085@125.81 | -0.2836..0.1092;126.67;2.992e-06 | -0.2274..0.8431;138.09;2.068 | 0.0002813 |
| A022_T1_C1_Q3 | 170–220 | — | 2.928e-09@170.68 | 5.445e-08@170.17 | -5.112e-09..7.769e-09;170.87;3.894e-09 | -2.097e-08..1.641e-08;171.18;3.351e-09 | 3.407e-09 |
| A022_T1_C1_Q3 | 220–250 | — | 3.563e-14@223.76 | 2.087e-11@226.81 | -2.644e-13..3.028e-13;224.28;-1.929e-14 | -1.008e-12..1.337e-12;239.94;5.270e-13 | 3.288e-13 |
| A023_T1_C1_P0 | 110–170 | 0@110.00 | 4.341e-06@110.30 | 5.769e-05@112.30 | -1.051e-05..1.155e-05;110.29;2.960e-06 | -1.911e-05..1.998e-05;110.69;7.527e-06 | 0.0001037 |
| A023_T1_C1_P0 | 170–220 | 1.2@171.00 | 1.304@173.00 | 0.02904@173.68 | -0.7603..0.6539;173.67;-9.836e-09 | -0.03392..0.02883;173.76;-1.349e-09 | 4.280e-09 |
| A023_T1_C1_P0 | 220–250 | 1.2@221.00 | 1.304@223.00 | 0.02904@223.68 | -0.7603..0.6539;223.67;-1.153e-08 | -0.03392..0.02883;223.76;-7.351e-09 | 4.281e-09 |
| A024_T1_C1_P1 | 110–170 | 0@110.00 | 0.02902@134.18 | 1.079@133.15 | -0.0911..0.1078;134.01;0.1766 | -0.2271..0.1429;134.33;0.03217 | 0.0001114 |
| A024_T1_C1_P1 | 170–220 | 1.2@171.00 | 1.371@172.84 | 0.03037@173.66 | -0.07882..1.079;173.54;1.891 | -0.05535..0.03387;173.75;-0.03216 | 5.997e-09 |
| A024_T1_C1_P1 | 220–250 | 1.2@221.00 | 1.304@223.00 | 0.02904@223.68 | -0.7603..0.6539;223.67;-1.153e-08 | -0.03392..0.02883;223.76;-7.356e-09 | 4.281e-09 |
| A025_T1_C1_P2 | 110–170 | 0@110.00 | 0.02898@126.95 | 1.077@125.93 | -0.09101..0.1079;126.78;0.1766 | -0.2272..0.1433;127.10;0.03217 | 0.0002234 |
| A025_T1_C1_P2 | 170–220 | 1.2@171.00 | 1.371@172.84 | 0.03037@173.66 | -0.07882..1.079;173.54;1.891 | -0.05535..0.03387;173.75;-0.03216 | 5.975e-09 |
| A025_T1_C1_P2 | 220–250 | 1.2@221.00 | 1.304@223.00 | 0.02904@223.68 | -0.7603..0.6539;223.67;-1.153e-08 | -0.03392..0.02883;223.76;-7.357e-09 | 4.281e-09 |
| A026_T1_C1_P3 | 110–170 | 0@110.00 | 0.02908@126.83 | 1.085@125.81 | -0.2824..0.1082;126.66;2.962e-06 | -0.2272..0.8430;138.09;2.068 | 0.0002813 |
| A026_T1_C1_P3 | 170–220 | 1.2@171.00 | 1.304@173.00 | 0.02904@173.68 | -0.7603..0.6539;173.67;-1.422e-09 | -0.03392..0.02883;173.76;2.523e-09 | 5.569e-09 |
| A026_T1_C1_P3 | 220–250 | 1.2@221.00 | 1.304@223.00 | 0.02904@223.68 | -0.7603..0.6539;223.67;-1.153e-08 | -0.03392..0.02883;223.76;-7.350e-09 | 4.281e-09 |

Across all runs, the extrema of the 11 T1 junctions in each window were:

| Window | Δphase min (run/JJ) | Δphase max (run/JJ) | Same-JJ voltage-area min (run/JJ) | Same-JJ voltage-area max (run/JJ) | Max phase-vs-area residual (turn arithmetic) |
|---|---|---|---|---|---:|
| 110–170 ps | -0.0002174 (A020/B_J1) | 12.5661522 (A022/B_J1) | -4.0611847e-16 V·s (A021/B_J8) | 4.1355961e-15 V·s (A026/B_J1) | 1.4371e-07 |
| 170–220 ps | -5.049191 (A024/B_J8) | 6.2831853 (A023/B_J2) | -1.6617189e-15 V·s (A024/B_J8) | 2.0678338e-15 V·s (A023/B_J3) | 1.4487e-07 |
| 220–250 ps | -1.0e-07 (A023/B_J6) | 6.283189 (A023/B_J3) | -5.8129e-24 V·s (A026/B_J11) | 2.0678338e-15 V·s (A026/B_J3) | 5.9848e-07 |

The `T1_PRE_CLOCK`, `T1_CLOCK_1`, and `T1_CLOCK_2` intervals are half-open
and independently calculated from stored timestamps. Full J1–J11 phase,
voltage, peak-time and signed-area values for every run are in the arithmetic
JSON. No threshold or event classifier was registered.

## Front-end and mode comparisons

Classic comparison pages use exact common stored timestamps, no interpolation;
each matched pre-clock comparison has **6,000** common samples in `[110,170)` ps:

- `plots/comparison/T1_C1_quiet_vs_pulse_exact_grid.html`
- `plots/comparison/T1_C1_vs_A013_A016_terminal_frontend.html`

For C1 `VOUT`, the pre-clock signed areas for terminal-reference / QUIET /
PULSE were: mask 0 `-2.20138e-20 / -2.32265e-20 / -2.32127e-20`; mask 1
`2.06711e-15 / 2.05104e-15 / 2.05104e-15`; mask 2
`2.06763e-15 / 2.05104e-15 / 2.05104e-15`; mask 3
`4.13490e-15 / 4.13564e-15 / 4.13564e-15 V·s`. The terminal controls
A013–A016 use the old 2 Ω C1 load, while T1_C1 uses the T1 input; these are
not matched-load comparisons. C2 remains a separate terminal and its per-window
voltage extrema/areas are retained in `analysis/cell_metrics.json`.

## QA, visualization, and archive

- Per-run outputs: four classic `josim-plot2.py` HTML pages; two exact-grid
  comparison pages. HTML is intentionally excluded from packages and remains
  local. `plot_qa.json` and comparison QA passed.
- Independent Decimal-time arithmetic audit: 8/8 PASS, no mismatches; raw SHA
  before/after is identical. The post-run audit-script correction and hashes
  are recorded in `analysis/t1_audit_patch_record.json`.
- Solver logs: one `stdout.txt` and one `stderr.txt` per run; no warning,
  error, missing-model, failed, or non-convergence marker was found in the
  scanned logs.
- Archive plan: eight per-run DELTA ZIPs plus one metadata ZIP, no HTML. The
  407 MB aggregate raw exceeds the submitter's 100 MB uncompressed per-group
  guard, so the established split strategy is used; each individual run remains
  under 100 MB. Detached `PACKAGE_QA.json` records each ZIP SHA-256, byte size,
  CRC/member hashes and source/base ancestry. Exact ZIP identities, Google Drive
  file links, and final commit IDs are being finalized. The targeted package
  preflight selected the existing full base
  `bvm-2x2-rowcol-selection-v1-20260928_snapshot_bvm2x2-rowcol-a001.zip`
  (SHA-256 `90b174f0f7ea71c6d41bcf85db1d999af9c173c0b0ecbb8de31f1c96bb4e3f50`,
  base commit `4035a3d6adcc841f4bd4269fbc32b9a3c897746a`) and previous delta
  head `1685ac25d57c0d9d761b8033ae8bdd75507dc930`. It references 18 existing
  raw CSVs without copying them, plans 236 changed/new non-HTML files into 8
  run groups plus metadata, and excludes 160 local HTML files. No historical
  ZIP was reopened or historical raw rehashed for this targeted plan.
- Drive archive folder:
  [BVM_Backages](https://drive.google.com/drive/folders/1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh).
  All nine archives passed full ZIP CRC and included-member SHA-256 QA:

| Archive group | ZIP bytes | ZIP SHA-256 |
|---|---:|---|
| A019_T1_C1_Q0 | 10,885,806 | `baf52d1884b9f9a75db960a3facc6fe8ebd5f4d1190ceac5fb0ec5f28cfe0ea0` |
| A020_T1_C1_Q1 | 11,977,302 | `e132744c0f67fd7affd7f7488c1a97f007c0c22404a3ed1f792cebb52a04a6cd` |
| A021_T1_C1_Q2 | 11,885,320 | `3a6901fce2b32c6d130d756980ccd2018bad2baadb9f82114c6b12e7704c4cf6` |
| A022_T1_C1_Q3 | 12,100,388 | `fce7989c235ba8ddaad875bc61b0378a1cc41fb2ef20f2f5cb01309445a83c6f` |
| A023_T1_C1_P0 | 12,652,826 | `d9298b6860cf1b4003308df07cb3ba296464396f0c0ce3321670bf32aba2989e` |
| A024_T1_C1_P1 | 13,290,687 | `5d89518be97d393e4470128b0cbb6ee767bb8d7ff089b78b517218f6e475fc85` |
| A025_T1_C1_P2 | 13,207,731 | `142bb8d7d2e59af00a868f8fa757881dc8ab73f03718adb1e182d19beae76af0` |
| A026_T1_C1_P3 | 13,255,000 | `b097650af7e1bb2b4f7759320474fa26e55f1f81b267d9394a9e9c23a2800520` |
| metadata | 224,778 | `3ef24f8fa3ed318fe677fbe3ba4afac74fb7d98e72db3facf17ca4974f97e592` |

Total compressed package bytes: **99,479,838**. The metadata ZIP's own hash
is repeated here only in the Git/Drive summary; its detached
`PACKAGE_QA.json` is the checksum authority. The metadata ZIP contains the
source-commit summary snapshot from before package identities were known; this
final post-package summary is committed separately and uploaded to the same
Drive folder. The raw/data bundles are unchanged by that summary update.

## Interpretation boundary

This is simulated raw evidence plus arithmetic, not a hardware measurement.
Scientific interpretation is **NOT PERFORMED**. No SFQ reception, T1 truth
table/logic function, throughput, causal mechanism, convergence, or parameter
optimization claim is made. The task stops after this batch and archive delivery.
