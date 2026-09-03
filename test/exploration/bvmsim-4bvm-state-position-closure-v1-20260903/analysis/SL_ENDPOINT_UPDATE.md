# SL endpoint visualization update

本次更新是对已完成六状态 PHASE-B 实验的观测扩展，不是新的器件或拓扑
实验。原始 `runs/<state>/raw.csv` 保持不变；由于原始 print 中只有 BVM4
的 SL 首/末结，新增了 `runs_sl_endpoints/<state>/`，仅增加 BVM1--BVM3
的 18 个 P/V/I 探针。

## 观测对象

| BVM | SL 首结 | SL 末结 |
|---|---|---|
| BVM1 | `B_LD01` | `B_LD12` |
| BVM2 | `B_LD2_01` | `B_LD2_12` |
| BVM3 | `B_LD3_01` | `B_LD3_12` |
| BVM4 | `B_LD4_01` | `B_LD4_11` |

每张图同时保留 `BVMout` 的 P/V/I、`V(QBIN)`、`V(QBOUT)` 和
`I(LIN|XBQ1)`。BVM4 的 `BVMout` 是独立的 top-level JJ，不把它误标作
SL 内部首/末结。

## Probe-only parity

六个新 raw 都有 158 个唯一列，较父 raw 多 18 列；共同的 140 个信号逐点
数值完全一致，时间网格完全一致，且没有模型告警。新 raw 的变化来自新增
`.print`，不是物理参数、控制波形、拓扑或求解设置变化。

## 可视化

使用 `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`，每个状态一张：

`plots/sl_endpoints/<state>/BVMOUT_QB_INPUT_SL_ENDPOINTS.html`

索引：`plots/sl_endpoints/INDEX.html`。所有 `P(...)` 原始值仍是 radians，
图中按 `rad/(2*pi)` 显示为 phase turns；图只做描述，不把 phase turns
当作 SFQ count。

## Commands

```text
python3 test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903/analysis/extend_sl_endpoint_decks.py --check-only  # exit 0
python3 test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903/analysis/run_sl_endpoint_probes.py                    # exit 0; 6/6
python3 test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903/analysis/check_sl_endpoint_parity.py                  # exit 0; PROBE_EXTENSION_PARITY_PASS
python3 test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903/analysis/render_sl_endpoint_plots.py                 # exit 0; 6 plots
```
