# Tooling corrective note

记录时间：`2026-09-02T12:02:15+08:00`。

运行后首次分析发现 `experiment.yaml` 中 `docs/research/METRIC_SPEC_V2.md` 的冻结
SHA-256 文本误少了两个字符，因此 shared `strict_event_summary` 的 provenance
guard 按设计停止分析。当前文件真实 SHA-256 为：

`f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`

本修正只恢复了完整的 64 位 hash；没有改变实验输入、QB 参数、solver、时间步长、
窗口、容差、outcome rule、raw 或科学运行次数。首次失败的分析过程保留在会话记录中，
RP science raw 不覆盖；修正后重新分析仍只消费同一份 `RP/run-01` raw。
