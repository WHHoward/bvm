# BVM_QB_LIN_REMOVAL_MATCHED_PAIR_QUICK_V1 preflight

- 记录时间：`2026-09-01T20:30:45+08:00`
- 实验前 HEAD：`8c78cd41c616353623f429f43af4a89b8ebba0f5`
- 实验前 Git dirty：`false`
- 本次授权的新 science runs：恰好 2 个（P1 physical、I1 ideal replay）
- 本次唯一科学变量：QB `Lin` 从 `0.8 pH` 移除；其余 QB/BVM/JSL/偏置/负载/时间步保持不变

## Solver and frozen models

- solver：`build/josim-cli`，版本 `v2.7.2837d13`
- solver SHA-256：`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- latest-HEAD canonical QB：`circuits/qb/bq_cell.cir`，SHA-256
  `7e019511c0615e1208b1887e49b0a33e61d18e5423134984f052318f494856ce`
- P0/I0 frozen QB input：`test/exploration/bvm-load-qb-matrix-v1-20260901/inputs/bq_cell.cir`，
  SHA-256 `5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2`
- canonical BVM：`circuits/bvm/bvm_cell.cir`，SHA-256
  `ea7346546bef091dc2efa39ab6f0abcfa54f833aeeabb909dcf3815cdaea42a4`
- JJ model：`circuits/models/jjmit.cir`，SHA-256
  `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`

P0/I0/G 使用父矩阵中已经存在的 13 ps、12×320、logical1/read raw；I1 必须复用
I0 使用的同一 frozen source waveform，不从 P1 物理电流重新构造 replay。实验完成后
只写入本实验唯一目录，不覆盖父矩阵或 canonical 文件。
