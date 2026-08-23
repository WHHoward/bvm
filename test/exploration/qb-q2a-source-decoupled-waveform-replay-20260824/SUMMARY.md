# QB-Q2A 总结：source-decoupled waveform replay diagnosis

## Verdict

`QB_DYNAMIC_WINDOW_MISMATCH`

A positive control 通过，但 canonical no-receiver logical1 的 source-isolated voltage replay 仍没有让 frozen scaled QB 的 BJL2 完成 local event。因此当前证据不支持 `SOURCE_ISOLATION_PRIMARY_LIMIT`；它支持的是：在本冻结 QB 和原始 canonical waveform 下，dynamic window 仍不足。

该结论只适用于本次 ideal replay fixture、波形、负载、模型、时间步和 local phase/area 规则；不是对 QB family 的普遍否定。

## 四个 case

| case | BJs units | BJL1 units | BJL2 units | BJL2 最大段 | 同段面积 | classification |
|---|---:|---:|---:|---:|---:|---|
| A: Q0 68.4 µA ideal current | 94 | 6 | 6 | `1.0960 turn` | `1.0965 Φ0` | positive control valid |
| B: Q1 loaded `V(SL1)` replay | 4 | 0 | 0 | `−0.0980 turn` | `−0.0980 Φ0` | no complete event |
| C: canonical logical1 `V(SL1)` replay | 1 | 0 | 0 | `0.1776 turn` | `0.1776 Φ0` | no complete event |
| C0: canonical logical0 `V(SL1)` replay | 0 | 0 | 0 | `0.0311 turn` | `0.0311 Φ0` | no complete event |

所有 event 判断均使用同一 JJ 的 continuous phase、同一 monotonic segment 的直接 voltage area 和 bounded post window；未使用 voltage peak、`I>Ic` 或旧 `fast_events`。

## Evidence layers

### Observed

- A 在六个 Q0 historical pulse windows 中逐 pulse 产生一个 bounded BJL2 phase/area-consistent unit，无 post candidate。
- B、C、C0 的 replay source 全部使用 raw `V(SL1)` 全采样点、原始极性和原始幅度；没有 rectify、hold、normalize 或 amplitude scaling。
- C logical1 的 BJL2 activity 明显高于 C0，但仍只有 `0.1776 turn` 对 `0.0311 turn`。

### Derived

- C replay 的 QB `I(Lin)` 范围约 `−53.4…+58.5 µA`；C0 约 `−23.3…+13.4 µA`。
- B replay 的 QB `I(Lin)` 范围约 `−39.1…+60.5 µA`，但 BJL2 最大段方向为负且仅 `0.0980 turn`。

### Inference

- canonical logical1 source waveform在理想 source-port replay 下仍不足以把当前 frozen scaled QB 推入 BJL2 quantizing window；因此 Q1 direct failure 不能主要归因于 source back-action alone。

### Unknown / boundary

- ideal voltage replay移除了真实 source impedance，不能证明可实现的 isolation/buffer。
- 没有改变 QB 参数、BVM、load 或 waveform；没有接 transformer、DCSFQ、JTL 或 T1。
- 未对 replay 的 amplitude/duration 做 sweep，不能推导 threshold 或 universal dwell。
