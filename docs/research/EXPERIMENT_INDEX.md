# BVM→QB Experiment Index

## 当前实验流程规范

未来新实验的规范入口是
[EXPERIMENT_WORKFLOW_V1.md](EXPERIMENT_WORKFLOW_V1.md)。它冻结
QUESTION → PREREGISTER → FREEZE DECK → PREFLIGHT → RUN → QA →
STANDALONE VISUALIZATION → COMPARISON → ANALYSIS → REVIEW → HUMAN GATE
的顺序，以及 runs/<condition>/deck.cir 的 executed-deck 权威边界。
下方历史实验不批量迁移；旧的 V2/Compact 文档只作为兼容性和历史参考。

这是当前高价值 BVM→QB lineage 的复盘入口。它是导航索引，不替代各实验的
raw、analysis、报告或 accepted audit。历史条目没有被虚构为 `USER_REVIEWED`。

| Family / Experiment | Scientific question | What changed | Key result | Evidence tier | Status | User-review state | Current authority | Superseded by / Next |
|---|---|---|---|---|---|---|---|---|
| `bvm-internal-readout-20260819` | BVM logical state/read 的内部轨迹是什么？ | 2×2 state/READ matrix | logical1 canonical read 为 strong multi-turn response；不得把约 3 turn 写成 3 SFQ | Exploration | COMPLETE | `N/A_HISTORICAL` | `analysis/` raw/report | receiver/transducer characterization，需新授权 |
| `bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824` | BVM read width 与 JSL/QB 轨迹如何关联？ | read-width/physical/replay fixture | 提供 bounded source/replay/physical observations；不是 exactly-one/JTL closure | Exploration | COMPLETE | `N/A_HISTORICAL` | experiment report/raw | later load matrix and strict reclassification |
| `bvm-load-qb-matrix-v1-20260901` | 9/13 ps、12×320/8×500 在 source/replay/physical 路线中有何 bounded difference？ | read width、JSL load、fixture kind | 48 个既有 raw case 形成 source/replay/physical matrix；只支持对应 fixture 内的比较 | Exploration | COMPLETE | `N/A_HISTORICAL` | `manifest.yaml` + raw/analysis | strict-event reclassification / dynamic loadline audit |
| `bvm-load-qb-strict-event-reclassification-v1-20260901` | 既有 BJL2 轨迹按 strict phase/area 口径如何分类？ | 只读重算，不改 raw | 9 ps/12×320 replay 最大 segment `0.892527...` turn，`SUBTHRESHOLD`；13 ps/12×320 replay `1.016029...` turn，`CLEAN_ONE_SFQ_CANDIDATE`；仍非 downstream proof | Exploration | COMPLETE | `N/A_HISTORICAL` | `analysis/strict-event-summary.csv` + report | shared `bvmtools.sfq` regression anchors |
| `bvm-qb-dynamic-source-loadline-audit-v1-20260901` | physical source/load interaction 是否只是 scalar attenuation？ | 只读 source/QB trajectory audit | 当前 bounded evidence 支持 dynamic source-load interaction；不能唯一定位某一器件或把 scalar fit 当充分原因 | Exploration | COMPLETE | `N/A_HISTORICAL` | `REPORT.md` + raw/analysis | 等用户理解后再决定最小判别任务 |

## 索引规则

- 新实验先登记 family、baseline/candidate、changed/fixed、证据层级和用户 review 状态；
- `AWAITING_USER_REVIEW` 是工具链默认终态；`USER_REVIEWED` 只能由用户明确表达后登记；
- `Current authority` 指向已有事实层/报告，不把 plot 或索引升级为科学权威；
- 历史实验保持原目录和原始 raw，不因 shared tooling 出现而批量迁移。
