# JTL_TRANSPORT_GATE_V1 summary

父级 HEAD：`edf9b6d6c9a26c999a9f95f8ca604993475c51d4`。

本目录是 analysis-only、回顾性的 provisional methodology checkpoint，消费 R11、M1、M5-PC 和 pulse-5
原/反极性 replay 的既有 raw；没有新的 JoSIM run。

## Verdict

- `R11-positive-control`: `JTL_TRANSPORT_REFERENCE_PASS`
- `M1-ideal-replay`: `JTL_TRANSPORT_PASS_COUNTERFACTUAL`
- `pulse5-original`: `JTL_TRANSPORT_PASS_COUNTERFACTUAL`
- `pulse5-reverse`: `REVERSE_POLARITY_NOT_A_ONE_WELL_TRANSPORT_EVENT`
- `M5-positive-control`: `MULTI_WELL_TRANSPORT_NOT_ONE_TURN`

R11 与 pulse-5 original 在本批 provisional transport gate 下具有相同的四颗 `+1` well
vector、bounded pre/post 和正确 t50 order；这只是 transport-level classification，
不是 physical QB→JTL compatibility。

strict local vector 仍独立保留：R11/M1/pulse5 original 为 `[1,0,0,0]`，M5-PC
为 `[1,1,0,0]`，反极性为 `[0,0,0,0]`。因此 full-window/pre→post 证据没有被
错误升级为 strict local event。

该分类不是 global Authority metric freeze。完整逐 JJ 数据、容差、raw hashes 和运行脚本见 `analysis/REPORT.md`、
`analysis/results.json`、`analysis/SHA256SUMS.txt`。
