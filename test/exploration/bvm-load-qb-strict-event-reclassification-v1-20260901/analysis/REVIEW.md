# Independent raw recheck

本复核从当前矩阵 raw 重新读取 BJL2 P/V/time，不读取 summary CSV 作为事件计数输入，且不调用 `scripts/sfq_metrics.py`。

## Mechanical checks

- raw cases checked: `32`
- raw QA invalid: `0`
- strict classifications inconclusive: `0`
- legacy/new source identity: `LEGACY_NEW_SOURCE_IDENTITY = PASS`
- legacy/new replay fixture equivalence: `LEGACY_NEW_REPLAY_FIXTURE_EQUIVALENCE = PASS`
- JSL series-current equivalence: `SERIES_JSL_CURRENT_EQUIVALENCE = PASS`; numerical tolerance `1.0e-13 A`; per-branch max/RMS/p95 differences are recorded in `analysis/jsl-series-current-equivalence.csv`.
- independent raw recheck artifact: `analysis/independent-raw-recheck.json`; separate execution is `PASS` for all 32 QB raw cases and does not import the main analyzer.
- regression: `PASS`

## Adversarial boundaries

- 通过窗口首末端点构造一个假的事件计数不会影响本复核；strict count 来自 `monotonic_runs` 的实际 segment 列表。
- 面积使用同一个 BJL2、同一 segment 和 raw time；不同 JJ、不同窗口或重采样后的面积没有进入判定。
- phase/area residual 使用 `phase - area` 的 signed convention；历史实现的 `area - phase` 只作为反号辅助字段保留。
- 同一个 turning-point sample 可作为相邻段共享端点；没有人工移动 start/end 或对期待分类调 threshold。
- raw sidecar/hash、重复表头一致性、时间单调性和 post/tail 覆盖均由脚本逐 case 检查。
