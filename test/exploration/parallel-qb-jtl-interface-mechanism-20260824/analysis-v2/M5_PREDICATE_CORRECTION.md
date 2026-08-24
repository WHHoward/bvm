# M5 positive-control predicate correction

日期：2026-08-24  
适用对象：历史 `analysis-v2/REPORT.md` 中的 `M5-positive-control` label。

历史脚本 `analysis/analyze_m1_m5.py` 的 `positive_control_valid()` 只检查：

```text
abs(full_window_turns) >= 0.90
```

没有设置 one-turn 的上界。因此 M5-PC 的约 `1.95–2.01` full-window/pre→post
phase turns 被旧谓词误纳入 “approximately one-turn positive control”。旧 raw、旧
报告和旧 label 保留为不可变历史记录；本文件明确 supersede 该 label 的 exactly-one
含义。

在 `JTL_TRANSPORT_GATE_V1` 重算中，M5-PC 四颗 scaled-JTL JJ 均约完成 `+2`
adjacent-well transition，故当前 disposition 为：

`MULTI_WELL_TRANSPORT_NOT_ONE_TURN`

它可以作为 bounded multi-well/scaled-JTL control，但不能作为 exactly-one 或
approximately-one-turn positive control，也不能支持 standard-JTL positive-control
或 physical QB→JTL claim。

校正依据：

- `test/exploration/jtl-transport-gate-v1-methodology-20260824/PREREGISTRATION.md`
- `test/exploration/jtl-transport-gate-v1-methodology-20260824/analysis/REPORT.md`
- M5 raw SHA-256：`9f98897978748b618d900538701be2f8e12cdecafe677f181ee402ab05bbc939`

对应 generated input copies 中的旧注释也属于该历史 fixture provenance；为保持已接受
fixture 的字节边界，本次不改写这些 copies，而以本 correction note 统一标记其
“5/5 correct”文字已 superseded。不要重跑 M5 raw；不要把该文档改写成新的 physical
result。
