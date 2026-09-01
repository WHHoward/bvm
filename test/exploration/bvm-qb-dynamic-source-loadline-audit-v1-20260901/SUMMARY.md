# BVM_QB_DYNAMIC_SOURCE_LOADLINE_AUDIT_V1

状态：`DYNAMIC_SOURCE_LOADLINE_MECHANISM_SUPPORTED`

只读分析既有 48-run matrix raw；没有新 JoSIM、扫参或电路修改。

- A/B 105 ps 前 identity：12x320 `PASS`；8x500 `PASS`
- B/C pre-state guard：`CHANGED`
- H4 overall source-load interaction：`SUPPORTED`；H5 scalar fit：`DISFAVORED`；H6 non-scalar family：`SUPPORTED`
- DeltaI max abs：`8.45943e-05 A`；scalar raw fit residual：`0.665945`

关键证据：

- `analysis/source-waveform-comparison.csv`
- `analysis/qb-internal-comparison.csv`
- `analysis/divergence-timeline.json`
- `analysis/scalar-attenuation-test.json`
- `analysis/dynamic-port-diagnostics.csv`
- `analysis/hypothesis-table.json`
- `analysis/independent-raw-recheck.json`
- `analysis/raw-provenance.json`

图只作描述性展示；严格事件、同段 phase/area、控制和步长边界不被机制图替代。
本任务到此停止；下一实验必须另行 preregister。
