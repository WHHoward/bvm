# Final v2 execution record

执行时间：`2026-08-24T09:20:36+08:00`（Asia/Shanghai）  
parent HEAD：`d05d96ab3eb13dc19af9dbaa0b7a5d3ac92ac63d`

## Tool provenance

- JoSIM `v2.7.2837d13`；binary SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`；
- jjmit SHA-256
  `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`；
- standard `JTL.cir` SHA-256
  `ac02fc931742bb857723f9fbb57ac97a179beb6a6466d5a1184e7cf937f599aa`；
- Q0 `bq_cell.cir` SHA-256
  `5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2`。

## Final jobs

每个 job 使用 `josim-cli -o <private raw csv> <private deck>`，stdout、stderr
和 exitcode 均写入同名 private log directory。最终 v2 jobs：

1. M1 ideal replay；
2. M2 `R_ISO=10 Ω`；
3. M3 `R_SER=10 Ω`；
4. M4 `L_ISO=10 pH`；
5. M5 scaled-JTL positive control；
6. M5 Q0 coupling（在 positive-control pass 后执行）。

六个最终 jobs 的 exitcode 均为 `0`，stderr 均为空；Q0 raw 各为 `3000`
行（含 header），M5 positive-control raw 为 `13600` 行（含 header）。

M5-Q0 的 positive control gate 已先在同一 v2 scaled-JTL point 上通过，随后
才执行 Q0 coupling。v1 raw 保留在 `raw/`，v2 仅新增 interface-current
probes，供最终报告使用。

## Analysis

最终分析：`analysis-v2/REPORT.md`、`analysis-v2/results.json`、
`analysis-v2/summary.json`。分析使用 continuous unwrapped phase、同一
JJ/同一 monotonic segment direct voltage area 和 post window；未调用
legacy `fast_events`。
