# BVM4X4 V9 Static QA

Status: **PASS**; `solver_invoked=false`; `physical_solve_count=0`.

- Parent HEAD: `54aecc583c1366878caa41ba5a8d617eb0aeb93f`
- V9 template topology equivalence (excluding only `.print`/`.tran`): `True`
- BVM/QB: 16/16; shared buses: WL=4, BL=4, row-SE=4; clock sources=8; total stimulus sources=20.
- Physical chain: array CB=16; carry CB=6; carry sJTL counts `{"D1": 1, "D2": 1, "D3": 5, "D4": 2, "D5": 1, "D6": 1}`; T1=7; Sum JTL2=14; DCSFQ2/JTL2 clock branches=8/8; DFF=1.
- V9 256 input encodings: `PASS` (256 configs generated; no solves); 11×13 mapping: SE `['SE_R1', 'SE_R2', 'SE_R4']`, BL `['BL_C1', 'BL_C2', 'BL_C4']`.
- Focus probes: 168; conservative raw estimate including 5% margin: 94712327 bytes / PASS against 100000000.
- New run IDs: `A109_V9_A0_B0_80P68, A110_V9_A1_B1_80P68, A111_V9_A11_B13_80P68, A112_V9_A15_B15_80P68`; all verified absent before launch.
- V9 historical RUN/SOURCE/PACKAGE manifests are explicitly not treated as current hash authority.
- Protected V9 reference raw/deck/stimulus SHA checks: PASS; no reference files changed.
- Legacy runner source/profile behavior is not replaced; this task uses explicit `--v9-multiply-batch` mode.
