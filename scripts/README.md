# scripts — 工具脚本索引

> **维护规则 (2026-08-09)**: 新脚本在此登记；脚本放 scripts/（勿放 circuits/ 等元件目录）。2026-08-06 的 v1 指标冻结已被相位单位审计撤销。

| 脚本 | 用途 | 状态 |
|------|------|------|
| `run_exp.sh` | 历史一键实验器；会覆盖固定输出并调用失效 v1 指标 | ⏸️ 仅历史复现，不得用于物理 Gate |
| `sfq_metrics.py` | v1 历史指标；raw rad 误标 SFQ、过阈值样本误标事件 | ⏸️ 已失效，等待 M4–M9 替代 |
| `josim-plot.py` | 波形绘图 | 🟡 使用中（与 plot2 并存，待确认规范） |
| `josim-plot2.py` | 波形绘图；五种布局均通过 `-j 2pi` 相位归一化回归 | 🟢 新实验默认的 compact classic 后端 |
| `ivcurve.py` | I-V 曲线 | 🟡 参考 |
| `plot-compare.py` | 波形对比 | 🟡 参考 |
| `noise_insert.py` | 噪声注入（论文扩展用） | 🔴 备用 |
| `sp_generator.py` | SP 网表生成 | 🟡 参考 |
| `JoSIM_n++_UDL.xml` | 编辑器语法高亮 | 📚 参考 |
| `MC_conclu.py` | 蒙特卡洛结论分析（2026-08-06 自 circuits/ 归位） | 🟡 参考 |
| `bvmtools/` | 未来实验共享 raw/provenance/phase/strict-event/waveform/compare 核心 | 🟢 新实验优先复用；不直接给物理 Gate |
| `bvm-exp.py` | 显式 case 的 Quick runner；生成 RESULT_BRIEF、classic compact plot 和 AWAITING_USER_REVIEW | 🟢 V1 Quick；不自动 Promotion/Formal |

**整理原则 (2026-08-09)**: 旧脚本保留用于追溯并明确标为 superseded。正式结论应依赖不可覆盖的 raw run、版本化 v2 指标、匹配控制和收敛 Gate；在 M4–M11 完成前不存在冻结的自动物理结论流水线。

**Tool consolidation (2026-09-01)**: 新工具先查 `docs/research/TOOL_REGISTRY.yaml`，
再复用 `scripts/bvmtools/` 和 `scripts/bvmtools/presets.yaml`。旧 experiment-local
脚本不批量搬迁；`run_exp.sh`、`sfq_metrics.py` 和旧 plotting paths 只按 registry
中的历史边界使用。未来 Quick 默认使用 `bvm-exp.py` 与
`josim-plot2.py` 的 compact classic profile，并在 `AWAITING_USER_REVIEW` 停止。
完整 future workflow 见 [`docs/research/FUTURE_EXPERIMENT_WORKFLOW.md`](../docs/research/FUTURE_EXPERIMENT_WORKFLOW.md)。
