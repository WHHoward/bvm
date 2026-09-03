# REVIEW — JM2-connected 4-BVM six-state A/B Quick

## Adversarial checks

- A/B 的 `0000` baseline 分侧使用；没有用 active state 或跨拓扑 baseline。
- state mapping 固定为 `b3b2b1b0 -> BVM1/BVM2/BVM3/BVM4`；zero-cell 主表保留
  完整 4×3 pair，不用总和掩盖位置和符号。
- 四条轨迹（A one-hot、A 0000、B one-hot、B 0000）逐点比较前有 hard exact-grid
  gate；不满足时分析直接失败，禁止插值。
- `READ0` 作为 WRITE1 前负控制；`PRE_READ1` 到 `TAIL` 的 retention 先报告，
  不机械重用旧 ±0.938 turn threshold。
- BJ2 以及 JTL 的 B01/B02 均用同一个共享 strict-event-list helper 扫描
  `PRE/WRITE0/READ0/WRITE1/READ1/TAIL`；事件按 onset 归窗，连续多圈仍不计为 SFQ。
- exact raw labels、duplicate header、metadata/hash、solver exit、model warning、
  variant identity 和 canonical BVM 排除均检查。
- plot2 只负责描述图；phase display 使用 rad/(2*pi)，不从 HTML 外观推断事件。

## Independent numerical check

`analysis/independent_check.py` 不读取 `metrics.json`，独立复算 Lin position 峰值、
zero-cell Delta I 和 BJ2 phase-area；主分析与其有 `22` 项匹配断言。

## 限制与审阅状态

这是 historical BVMSim task-local variant 的 exploratory A/B。zero-cell response
的机制解释必须保持 bounded inference；本文件不授予 Formal/Gate/paper authority。
Sol XHigh 只读复核结果为 `NEED_REVISION`；其指出的交付层问题已修正，复核不修改
raw、不要求重跑 JoSIM，也不改变本轮 human gate。完整意见见
`analysis/SOL_XHIGH_REVIEW.md`。
