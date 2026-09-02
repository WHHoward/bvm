# QB_NODE2_OPERATING_POINT_DECOMPOSITION_V1

这是一次只消费既有 raw 的 Exploration：分解 13 ps、12×320、`logical1/read`、scaled QB 条件下 G、I0、P0 的 QB 输入、node2、node3、node4 轨迹，并以 Q45/Q68 作为历史 supporting scalar reference。

本目录不包含新 JoSIM 运行，不改变电路、参数或历史 raw。结果不是 Formal BVM→QB Gate，也不是硬件结论。

建议阅读顺序：

1. [RESULT_BRIEF.md](RESULT_BRIEF.md)：结论摘要和停止边界。
2. [analysis/REPORT.md](analysis/REPORT.md)：完整的窗口、KCL、节点分解和 provenance 说明。
3. [analysis/REVIEW.md](analysis/REVIEW.md)：数值与 adversarial review。
4. [plots/RESULT_OVERVIEW.html](plots/RESULT_OVERVIEW.html)：唯一一张关键数据总览图。

机器可读产物：

- [analysis/metrics.json](analysis/metrics.json)
- [analysis/provenance.json](analysis/provenance.json)
- [analysis/plot_metadata.json](analysis/plot_metadata.json)
- [plots/RESULT_OVERVIEW.metadata.json](plots/RESULT_OVERVIEW.metadata.json)
- [analysis/plot_input.csv](analysis/plot_input.csv)

重现分析（不会运行 JoSIM）：

```bash
python3 test/exploration/qb-node2-operating-point-decomposition-v1-20260902/analysis/analyze_node2.py
```

分析脚本只读取预先登记的 raw/deck/model/manifest，计算 KCL、窗口统计、strict local compatibility、exact-grid 差异和 supporting scalar；本次修正复用 `scripts/bvmtools` 的 phase/waveform/onset/KCL 原语，未因指标修正而重生成已有关键图。

当前状态：`COUPLED_INPUT_BJS_NODE2`，`mechanism_disposition: EXPLORATORY`，robustness `MIXED`，等待用户 review 后停止。该标签不证明 causal order；`causal_order: NOT_PROVEN`。
