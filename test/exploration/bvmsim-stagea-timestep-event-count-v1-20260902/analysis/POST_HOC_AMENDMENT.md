# 严格事件分析的后置说明

记录时间：`2026-09-02T20:12:18+08:00`

Sol XHigh reviewer 指出：实验预注册文件已经声明了事件的主要概念边界（同一 JJ、同一连续单调段、相位/电压面积一致、至少 1 turn、clean 上限 1.15 turn），但本次实际使用的可复用 `strict_event_list` helper 是在 raw 产生后才补入共享工具的；完整的 retrap/bounded 参数也没有在最初的 `experiment.yaml` 中逐项冻结。

因此，本目录中的严格事件枚举在 provenance 中明确标记为：

```yaml
status: POST_HOC_EXPLORATORY
```

本后置说明冻结的“分析后验输入”仅用于如实描述已完成的重分类，不是新的物理运行授权：

- `complete_min_abs_turns = 1.0`
- `clean_upper_abs_turns = 1.15`
- `retrap_max_p2p_turns = 0.25`
- `post_range_max_turns = 1.0`
- scan window：`[0, 200] ps`
- association windows：`[0,50)`, `[50,70)`, `[70,90)`, `[90,110)`, `[110,170)`, `[170,200] ps`

这次修正没有修改任何历史 raw 或新 raw，没有重新运行 JoSIM，只重新运行分析器和独立算术复核。由此，事件计数和 retrap 分类只能作为 exploratory evidence；不能升级为预注册 Formal/Candidate Gate，也不能改变用户 review gate。

## 影响

- `net turns` 与 `clean separated event count` 继续严格分开。
- BJ2 的 `1` 个 complete、`0` 个 clean separated event 和连续多-turn 主段结论，是后置 exploratory classification，不是硬件/论文级事件计数。
- JTL 的计数字段改名为 `local_stage_summary_count`，并显式标记 `NO_EVENT_IDENTITY_MATCH`；它们不能被称为守恒 transported event count。
- `event5_origin` 改名为 `event5_candidate_ladder`，仅表示描述性候选顺序，不表示因果来源。

原始 `experiment.yaml` 的 required-table 文本中仍保留了预注册阶段的
`*_transported_event_count` 术语；该文件作为历史预注册记录不回写。最终
`metrics.json` 和结果报告没有使用该术语，而是使用
`local_stage_summary_count`，并明确 `NO_EVENT_IDENTITY_MATCH`，以避免把
未完成身份配对的本地计数伪装成 transport count。
