# PAPER-SL-Q5 execution record

四个 case 按预注册顺序完成；先运行 logical1 + READ=0 control，确认没有
solver error、startup/free-running 或完整 output transition 后才继续其余 case。

| case | JoSIM exit code | stderr bytes | raw rows |
|---|---:|---:|---:|
| paper-j1-logical1-read0-control | 0 | 0 | 13,599 |
| paper-j0-logical0-read0-control | 0 | 0 | 13,599 |
| paper-j0-logical0-read | 0 | 0 | 13,599 |
| paper-j1-logical1-read | 0 | 0 | 13,599 |

执行输出在 `logs/<case>.stdout`、`logs/<case>.stderr`、`logs/<case>.exitcode`；
raw CSV 在 `raw/q5-l1-4p50-l2-4p50/`。

配置积分 timestep 为 0.0125 ps，实际 CSV 时间轴严格递增至 169.9875 ps；
分析使用 CSV 实际时间，不重采样、不修改 Q2/Q3/Q4 raw。
