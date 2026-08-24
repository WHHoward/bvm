# QB-Q0 standalone 可视化

来源是本 Exploration 已接受的 `raw/scaled` 与 `raw/paper` CSV；没有重新运行 JoSIM，也没有复制或修改 raw。

- `scaled-0uA.html`、`scaled-45uA.html`、`scaled-68p4uA.html`、`scaled-90uA.html`：四个 scaled ideal-current level。
- `scaled-comparison.html`：四个 level 的 BJs/BJL1/BJL2 phase、BJL2 voltage 和 OUT 对照。
- `68p4-paper-reference.html`、`90-paper-reference.html`、`paper-reference-comparison.html`：paper-original standalone 对照。

相位显示为原始 `P(...)` 除以 `2π` 的 turns；它是连续 phase activity，不是 SFQ count。正式结论仍以 `analysis/QB_Q0_REPORT.md` 为准：scaled 68.4 µA 是 standalone exactly-one reference，90 µA 为 multi-event。

图形使用 `scripts/josim-plot2.py` 的 dark/`sep_comb` 约定；HTML 使用 Plotly 3.1.0 CDN。
