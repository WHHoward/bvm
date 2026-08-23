# QB-Q1 总结：canonical BVM → frozen scaled QB compatibility

## Verdict

主 verdict：`QB_SOURCE_BACKACTION_FAILURE`

次级观察：`QB_BVM_SUBTHRESHOLD`

四组 matched cases 均成功完成，且没有运行参数 sweep、没有修改 canonical BVM/QB、没有连接 JTL/T1。直接 galvanic `SL1 → QB IN` 在本冻结点上确实传递了 state-dependent waveform，但同时明显改变了 BVM source/storage 状态；BJL2 没有形成 complete local event。

## 核心结果

| case | BJs local units | BJL1 units | BJL2 units | BJL2 最大单调段 | 同段电压面积 | 结论 |
|---|---:|---:|---:|---:|---:|---|
| logical1 + READ=0 | 0 | 0 | 0 | `1.66e-6 turn` | `1.64e-6 Φ0` | 无 event |
| logical1 + READ | 4 | 0 | 0 | `0.0980 turn` | `0.0980 Φ0` | BJL2 subthreshold |
| logical0 + READ | 0 | 0 | 0 | `0.0302 turn` | `0.0302 Φ0` | BJL2 subthreshold |
| logical0 + READ=0 | 0 | 0 | 0 | `1.70e-6 turn` | `1.69e-6 Φ0` | 无 event |

`BJs` 的 read1 activity 是前级局部行为，不等于 BJL2 quantization，也不等于 downstream SFQ delivery。BJL2 所有 case 都没有满足连续单调 `≥1 turn` 且同段 `∫Vdt/Φ0` 一致的 complete event。

## 实际输入与 source loading

- read1 的实际 `I(Lin)` activity range：`−39.13 … +60.49 µA`；read0：`−24.85 … +19.76 µA`。因此 QB 输入并非没有 state-selective signal。
- read1 的 `V(SL)` activity range：`−1.036 … +1.866 mV`；read0：`−0.361 … +0.444 mV`。
- 相对 canonical no-receiver baseline，read1 的 `JS1/JS2` post-state 中位偏移约 `−2.997/−2.998 turn`，不是可以忽略的额外 loading。
- logical1 + READ=0 control 的 `SL` activity p2p 从 canonical baseline 的约 `0.0000206 mV` 增至 `0.000719 mV`，即约 `0.0206 µV → 0.719 µV`；control 虽无 QB event，但 source boundary 已出现可见 ringing。

## 证据分层

### Observed

- 四个 raw CSV 均由记录的 JoSIM binary 正常完成；请求的 `.tran` step 为 `0.0125 ps`，每个 CSV 有 `13,599` 个样本、终点 `169.9875 ps`，并在 `1.8375→1.8625 ps` 处共同出现一个确定性的 `0.025 ps` 输出间隔。该间隔早于 `[94,130) ps` activity window。
- read1 明显驱动 BJs，并且 read1/read0 的 QB input current/voltage 分离存在。
- BJL1/BJL2 没有 complete event；read0 与两个 READ=0 control 也没有 complete event。
- raw phase、同一 JJ 同一单调段的直接电压面积，以及 post window 均已记录。

### Derived

- phase turns 使用 raw `P()` 的 radians 除以 `2π`。
- BJL2 read1 最大段约 `0.0980 turn`、同段面积约 `0.0980 Φ0`，距离 complete event 仍很远。
- 这是当前 direct galvanic interface 的 loaded result；不能把绝对 logical1 canonical JS running 本身误判为 receiver loading，故 source guard 使用 loaded-minus-canonical differential。

### Inference

- 当前冻结点的主要失败位置是 source/storage back-action，而不应表述为“scaled QB 参数已被证明无效”。
- 输入 coupling 存在，前级 BJs 有 read1 activity；但由于 source guard 已失败，现有数据不足以把剩余瓶颈唯一归因于 JL1 routing 或 BJL2 threshold。

### Unknown / stop boundary

- 尚未在 source-isolated interface 下测试该 frozen QB，因此不能据此否定 QB family。
- 没有优化或 sweep QB AREA、bias、load、transformer 或 BVM 参数。
- 下一步若继续，先分离 input coupling、internal routing、BJL2 threshold 与 source back-action；不得从本结果自动开始参数扫描。

## Provenance

- Parent HEAD：`f800df0eab8c9402ec521d0c9e96fbc6d7a79e32`
- Exploration 目录：`test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/`
- Frozen QB：QB-Q0 scaled cell，`BJs=.50 / BJL1=.36 / BJL2=.54 / IB=35 µA`，其余参数见 `PREREGISTRATION.md`。
- 本轮未连接 DCSFQ、JTL 或 T1；本地 JJ activity 不自动等于 SFQ delivery。
