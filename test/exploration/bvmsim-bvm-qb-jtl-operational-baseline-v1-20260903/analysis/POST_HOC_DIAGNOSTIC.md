# Post-hoc strict diagnostic notes

本文件记录 raw 采集完成后用于复算的探索性诊断参数，不是运行前预注册的
acceptance contract，也不授权任何后续实验。记录时间：2026-09-03T14:43:54+08:00。

## Scope

- 输入是本目录已经保存的 immutable raw；不重写 raw，也不重新运行 JoSIM。
- phase/voltage-area 算术仍调用共享 `bvmtools.phase`、`bvmtools.waveform` 和
  `bvmtools.sfq.strict_event_list`。
- 这些参数只用于列出 burst-total、monotonic segment、retrap 和 clean-band
  诊断；它们不应被描述成运行前冻结的科学 Gate。
- 共享 `StrictLocalEventSpec` 使用显式的 `POST_HOC_EXPLORATORY` readiness 状态，
  仅表示参数完整、可复算，不表示 protocol freeze 或 scientific acceptance。

## Parameters used

- burst-total integer display tolerance：`0.25 turns`；
- same-JJ phase/area residual：`max(0.05 turns, 0.10 × max(|phase|, |area|, 1))`；
- complete segment：`|delta phase| >= 1.0 turn` 且同段 phase/area 一致；
- clean upper band：`1.15 turns`；
- bounded retrap tail：`0.25 turns` peak-to-peak。

## Interpretation boundary

`BASELINE_FUNCTIONAL_FAIL` 的稳健部分是 raw 中大量 commanded-state 输出与
`popcount` 预期相差完整整数级别；它不依赖把一个连续多圈段改写成多个 clean
SFQ，也不依赖 `Vpeak`、`I/Ic` 或旧 `fast_events`。但本文件中的具体 strict
segment/clean-event 数字属于 post-hoc exploratory diagnostics，不能回写成
预注册阈值已经通过的结论。
