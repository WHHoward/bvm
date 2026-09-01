# BVM_LOAD_QB_STRICT_EVENT_RECLASSIFICATION_V1

状态：`STRICT_EVENT_RECLASSIFICATION_COMPLETE`

本轮只重新分析已有矩阵 raw，没有重跑 JoSIM 或改变电路。

- source identity：`LEGACY_NEW_SOURCE_IDENTITY = PASS`
- replay fixture equivalence：`LEGACY_NEW_REPLAY_FIXTURE_EQUIVALENCE = PASS`
- regression：`PASS`

| fixture | width | load | largest BJL2 segment | area | classification |
|---|---:|---|---:|---:|---|
| physical | 9 | 12x320 | -0.104071401 | -0.104078803 | `SUBTHRESHOLD` |
| physical | 9 | 8x500 | -0.146871253 | -0.146879579 | `SUBTHRESHOLD` |
| physical | 13 | 12x320 | -0.1221278 | -0.122131039 | `SUBTHRESHOLD` |
| physical | 13 | 8x500 | -0.124996234 | -0.125006108 | `SUBTHRESHOLD` |
| replay | 9 | 12x320 | 0.892527234 | 0.892537009 | `SUBTHRESHOLD` |
| replay | 9 | 8x500 | 0.877365815 | 0.877377688 | `SUBTHRESHOLD` |
| replay | 13 | 12x320 | 1.01602892 | 1.01603683 | `CLEAN_ONE_SFQ_CANDIDATE` |
| replay | 13 | 8x500 | 0.973287067 | 0.973297156 | `SUBTHRESHOLD` |

`window_phase_delta_turns` 与 strict event count 分开保存；窗口端点位移不能替代连续单调段。
全部 32 个 case 的逐行结果见 `analysis/strict-event-summary.csv`，完整 segment 证据见 `analysis/strict-event-details.json`。
本任务到此停止；不自动进入下一实验。
