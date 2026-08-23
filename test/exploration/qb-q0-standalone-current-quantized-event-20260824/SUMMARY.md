# QB-Q0 standalone QB re-audit summary

## 结论

在当前 `jjmit` phase/同一 JJ 电压面积口径下，scaled `circuits/qb/bq_cell.cir` 的独立理想电流 fixture 建立了一个有限输入窗口：

- `68.4 µA`：BJL2 每个六个周期脉冲各有一个完整的同段 phase/area-consistent local turn，约 `1.096014 turn / 1.096515 Φ0`，post window 无第二个完整候选；判为 `EXACTLY_ONE`（本地 BJL2 诊断意义）。
- `90 µA`：BJL2 每脉冲约 `2.006059 turn / 2.006689 Φ0`，因此是 `MULTI_EVENT`，不能把一个约两圈的单调段误称 exactly-one。
- `45 µA`：BJL2 最大约 `0.09215 turn`，无完整候选；判为 `NO_COMPLETE_EVENT`。
- `0 µA`：无完整候选；判为 `ZERO_EVENT`。

因此 scaled QB 存在一个 bounded local exactly-one window，但这不是 canonical BVM 结果，也不是下游 SFQ delivery 证据。

## Paper-original standalone comparison

在保留 paper JJ class、`RB=8.5 Ω`、并采用历史 BVM-paper fixture 的 `IBIAS=90 µA` 作为 standalone bias provenance 时：

- `68.4 µA`：BJL2 最大约 `0.03784 turn`；
- `90 µA`：BJL2 最大约 `0.05637 turn`；
- 两点均无完整 local BJL2 event；`0 µA` control 亦无事件。

该比较替换了 BVM 为理想 current source，只是 topology/scale 对照，不是 paper 全链路复现。

## 实际 model scaling

快照中的 `jjmit` 为 `icrit=0.1m`、`CAP=0.07p`、`rn=16 Ω`、`r0=160 Ω`；因此 AREA 同时改变 `Ic/C/RN/R0`。scaled BJL2 为 `Ic=54 µA, C=37.8 fF, RN=29.63 Ω, R0=296.30 Ω`；paper BJL2 为 `189 µA, 132.3 fF, 8.47 Ω, 84.66 Ω`。完整表见 `analysis/QB_Q0_REPORT.md`。

## Evidence boundary

- 事件判据直接使用 raw `P/V/I`：连续 unwrapped phase、同一单调 segment 的 `∫Vdt/Φ0`、post-window bounded/retrap 检查。
- 约两圈的同一单调 segment 按其包含的完整 turn units 计数，所以 scaled `90 µA` 被标为 `MULTI_EVENT`。
- 没有使用旧 `fast_events`、旧 JSON 或历史 “190 SFQ / 5/5 correct” claim。
- 所有七个 raw run exit code 为 `0`，每个包含 2999 个 `0.1 ps` 时间采样点，时间从 `0` 到 `299.9 ps`；无 BVM、DCSFQ、JTL、T1。

## Observed / Derived / Inference / Unknown

### Observed

七个固定 case 均成功运行；scaled `68.4 µA` 的 BJL2 event-count vector 为 `[1,1,1,1,1,1]`，scaled `90 µA` 为 `[2,2,2,2,2,2]`，两者 post complete-event count 均为零。

### Derived

phase turns 为 `ΔP/(2π)`；同段面积为直接 JJ `V` 在同一 segment 上积分后除以 `Φ0`。本轮使用的 `|Δturn|≥1` 和 residual 规则是 exploration-local、明确未冻结的 diagnostic rule。

### Inference

scaled QB 的 `68.4 µA` 点值得作为下一轮独立 QB-Q1 的 frozen standalone reference candidate；它仍需经过 canonical BVM 接入测试，不能提前外推为 BVM receiver。

### Unknown

尚未测试 canonical BVM source impedance/back-action、单次非周期输入下的长期 re-arm、或 JTL propagation。Q0 不进行任何参数优化。

## Next boundary

本 checkpoint 只关闭 standalone re-audit。若启动下一轮，应单独定义 `QB-Q1: canonical BVM → frozen scaled QB point`，并重新冻结 source/load、matched controls 与 receiver evidence 判据。
