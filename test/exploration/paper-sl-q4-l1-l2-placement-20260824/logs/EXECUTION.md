# PAPER-SL-Q4 execution record

四个 case 按 preregistration 顺序完成；先运行 logical1 + READ=0 control，确认
无 solver error、startup/free-running 或完整 transition 后才继续其余三个 case。

| case | JoSIM exit code | stderr bytes | raw rows |
|---|---:|---:|---:|
| paper-j1-logical1-read0-control | 0 | 0 | 13,599 |
| paper-j0-logical0-read0-control | 0 | 0 | 13,599 |
| paper-j0-logical0-read | 0 | 0 | 13,599 |
| paper-j1-logical1-read | 0 | 0 | 13,599 |

执行输出分别保存在 `logs/<case>.stdout`、`logs/<case>.stderr`、
`logs/<case>.exitcode`；原始 CSV 保存在 `raw/q4-l1-3p91-l2-4p50/`。

分析使用实际 CSV 时间轴：0 至 169.9875 ps；配置的积分 timestep 为
0.0125 ps。CSV 时间戳严格递增，实际相邻输出间隔为约 0.0125–0.025 ps，
其中每个 deck 有一个 0.025 ps gap（源 deck 的原始 PWL 时间点缺口）；没有
重采样，也没有修改已有 Q2/Q3 raw。
