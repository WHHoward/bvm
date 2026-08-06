# scripts — 工具脚本索引

> **维护规则 (2026-08-06)**: 新脚本在此登记；脚本放 scripts/（勿放 circuits/ 等元件目录）。

| 脚本 | 用途 | 状态 |
|------|------|------|
| `run_exp.sh` | **一键实验**：仿真→指标→md5 确定性（Phase 1+ 标准动作） | 🟢 使用中 |
| `sfq_metrics.py` | 冻结指标脚本（net/TV/fast_events/dPdt，JSON 输出） | 🟢 冻结口径 |
| `josim-plot.py` | 波形绘图 | 🟡 使用中（与 plot2 并存，待确认规范） |
| `josim-plot2.py` | 波形绘图（另一版本，2026-04-23 晚于 plot） | 🟡 并存，未删除（见"整理原则"） |
| `ivcurve.py` | I-V 曲线 | 🟡 参考 |
| `plot-compare.py` | 波形对比 | 🟡 参考 |
| `noise_insert.py` | 噪声注入（论文扩展用） | 🔴 备用 |
| `sp_generator.py` | SP 网表生成 | 🟡 参考 |
| `JoSIM_n++_UDL.xml` | 编辑器语法高亮 | 📚 参考 |
| `MC_conclu.py` | 蒙特卡洛结论分析（2026-08-06 自 circuits/ 归位） | 🟡 参考 |

**整理原则 (2026-08-06)**: 旧/重复脚本不删除（保留历史），仅索引标注；正式结论只依赖 `run_exp.sh` + `sfq_metrics.py`。
