# RESULT_BRIEF

实验：`bvmsim-jm2-single-vs-4bvm-shared-sl-v1-20260907`
结论级别：**EXPLORATION / QUICK；有界仿真证据**

## OBSERVED

- 仅执行了登记的两个物理求解：`SINGLE` 与 `ARRAY`；两次 solver 返回成功。
- 两个 raw CSV 都通过有限值、严格递增时间轴、探针完整性和 raw 不可变检查；两者各有 1999 个样本，存储时间戳逐点一致，最后一个样本为 199.9 ps（对应 `.tran 0.1p 200p` 的 solver 输出约定）。
- `SINGLE` 使用历史 JM2-connected BVM 变体；`ARRAY` 使用 4 个相同变体，共享 `COMMON_SL`，最终读取只激励 BVM1，BVM2–BVM4 保持 quiet。
- 两个 fixture 都使用 8 个 `jjmit area=5.0` JSL、相同 `BQ.cir`、6 级相同 JTL 和 10 Ω 终端；raw 保留 BVM、全部 8 个 JSL、QB 及全部 JTL 的 P/V/I（或适用的 I/V）探针。
- 目标 BVM1 的 WL/BL/SE 原始控制电流在两个 fixture 间逐点完全相等：最大差和 RMS 差均为 0。
- `PRE_FINAL_READ` 窗口（101–110 ps）已经观察到目标 BVM 内部状态差异；这只是窗口内轨迹差异记录，不是机制判定。

## DERIVED

以下均为 `ARRAY BVM1 − SINGLE`，窗口为半开区间 `[110,121) ps` 的描述性差值：

- `JM2` 连续相位：最大绝对差 `1.0572891 rad`（显示图中的 phase turns 由连续 unwrap 后再除以 `2π` 得到）。
- `LS2` 电流：最大绝对差 `236.517 uA`。
- `SL/COMMON_SL` 边界电压：最大绝对差 `1.2574601 mV`。
- `JSL1` 与 `JSL8` 相位：最大绝对差均为 `0.23798488 rad`。
- QB `BJ2` 连续相位：最大绝对差 `5.309605 rad`。
- `JTL1` 的 `B01` 连续相位最大绝对差为 `5.0518175 rad`；`JTL6` 的 `B01` 最大绝对差约 `8.0e-7 rad`；终端电流最大绝对差约 `1.01e-5 uA`。

数值来自 [metrics.json](analysis/metrics.json)，独立 raw 复算和数值/对抗审查见 [REVIEW.md](analysis/REVIEW.md)。

## BOUNDED_RESULT

在本次固定的历史 JM2-connected BVM、时序、8×500-uA JSL、QB、6 级 JTL 和 10 Ω 负载条件下，孤立 SINGLE 与共享 `COMMON_SL` 的 ARRAY BVM1 在 `PRE_FINAL_READ` 和 `FINAL_READ` 的目标轨迹并不逐点相同；差异可在 BVM、JSL、QB 以及 JTL1 等记录信号中观察到。该结果支持一个有界的 SINGLE/ARRAY A/B 轨迹比较。

这不等同于物理机制、因果根因、SFQ 接收/传输或硬件行为的证明。

## UNKNOWN / LIMITS

- 未建立时间步长收敛或参数敏感性结论。
- 没有定义或报告 SFQ 事件计数；相位位移、电压面积、阈值活动和 crossing 均不被当作 SFQ 数量。
- `V(IB|XBQ1)` 虽在 deck 中请求，但当前 JoSIM raw schema 不输出该可选列；`I(IB|XBQ1)` 已保留。
- 未评估 canonical BVM、工艺裕量、硬件测量或普遍的 isolation/非-isolation 命题。

## ARTIFACTS

- [experiment.yaml](experiment.yaml) / [PREFLIGHT.md](PREFLIGHT.md)
- [SINGLE deck](runs/single/deck.cir) / [SINGLE raw](runs/single/raw.csv)
- [ARRAY deck](runs/array/deck.cir) / [ARRAY raw](runs/array/raw.csv)
- [artifact QA](analysis/artifact_qa.json) / [control QA](analysis/control_equivalence.json) / [numerical QA](analysis/numerical_qa.json)
- [plot manifest](plots/plot_manifest.json) / [visualization QA](analysis/viz_qa.json)
- standalone pages: [SINGLE JSL endpoints](plots/single/JSL_ENDPOINTS.html), [ARRAY JSL endpoints](plots/array/JSL_ENDPOINTS.html)
- comparison page: [JSL endpoints SINGLE/ARRAY/DELTA](plots/comparison/JSL_ENDPOINTS_RAW_DELTA.html)

Raw SHA-256：SINGLE `26a70e75afced6e91a7f75e9048b2700839051f38bcd2844d3f153b04ef0939a`；ARRAY `8543abc6d7a7d276c0bfa3159a4d3d37d569200e5fa30082466e66df8ab24dc2`。
