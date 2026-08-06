# test/final — 项目电路测试目录索引

> **维护规则 (2026-08-06)**: 只追加不删除；新测试目录需在此登记；历史/参考目录标注清晰。

| 目录 | 内容 | 状态 (2026-08-06) |
|------|------|------------------|
| `interface/` | **DCSFQ_BVM 接口元件 Phase 0/1**（P0_LOG.md 汇总 + P0_LOG_P00-P03） | 🟢 当前主线 |
| `single_bvm_qb/` | BVM→BQ 冻结基线（BASELINE.md） | 🟢 冻结基准 |
| `bvm/` | BVM 独立测试 | 🟡 参考（jjmit 时代） |
| `qb/` | BQ 独立测试（v2/v4 实验 + data/） | 🟡 历史（BQ 路线已排除） |
| `t1/` | T1 全加器测试 | 🔴 未完成验证 |
| `array/` | 阵列相关 | 🔴 未开始 |
| `sfq_gen_clk/` `sfq_gen_i/` | 单结 SFQ 发生器 | ⏸️ 已放弃（触发电阻分压） |
| `ref_tests/` | 上游参考测试 | 📚 参考（勿改） |

**约定**: 每个实验目录含 `data/`（原始 CSV 必须提交，禁 /tmp）；指标用 `scripts/sfq_metrics.py`；批量实验优先 `scripts/run_exp.sh`。
