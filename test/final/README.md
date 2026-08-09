# test/final — 项目电路测试目录索引

> **维护规则 (2026-08-09)**: 原始实验只追加不覆盖；旧结论通过 superseded 警告保留。当前先完成 Phase −1 计量修复。

| 目录 | 内容 | 状态 (2026-08-09) |
|------|------|------------------|
| `interface/` | DCSFQ_BVM Phase 0 数据与历史日志 | 🟡 待 v2 指标重建；路线候选 |
| `single_bvm_qb/` | BVM→BQ 历史基线 | 🟡 原始 CSV 可用；旧冻结指标失效 |
| `bvm/` | BVM 独立测试 | 🟡 待 v2 指标重建 |
| `qb/` | BQ v2/v4 实验与数据 | 🟡 v4 已重开为候选，完整 Gate 未通过 |
| `t1/` | T1 全加器测试 | 🔴 未完成验证 |
| `array/` | 阵列相关 | 🔴 未开始 |
| `sfq_gen_clk/` `sfq_gen_i/` | 单结 SFQ 发生器 | ⏸️ 已放弃（触发电阻分压） |
| `ref_tests/` | 上游参考测试 | 📚 参考（勿改） |

**约定**: 保留原始 CSV、网表、控制、版本和方向；新结论级运行使用唯一 run ID，不覆盖历史。`scripts/sfq_metrics.py` 与 `scripts/run_exp.sh` 仅供历史追溯，不得作为当前物理 Gate。执行与审计分别遵循 `josim-experiment` 和 `josim-evidence-audit`。
