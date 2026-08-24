# BVM READ semantics + JSL width bracket

Verdict: `IDEAL_REPLAY_SELECTIVE_ONE_SFQ_CANDIDATE`

- 13 ps：`CLEAN_ONE_SFQ_CANDIDATE`；14 ps：已执行的同类 post-candidate observation。
- 15 ps：`OVERDRIVEN_ONE_PLUS_LARGE_RESIDUAL`；不能等同于 clean single-SFQ operating point。
- 执行记录：`EARLY_STOP_EXECUTION_DEVIATION`；13 ps 是已注册的首个选择性 candidate；更宽的 width 只是 candidate 之后已执行的 bounded observation，不具有 operating-point 选择权。

本轮完成 READ 语义审计、12 ps canonical logical0 correction 与注册宽度 bracket；详见 `REPORT.md`。
