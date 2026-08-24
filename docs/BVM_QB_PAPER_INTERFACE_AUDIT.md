# BVM→QB 论文接口 provenance audit

status: `PAPER_PROVENANCE_AUDIT_V1`
recorded_at: `2026-08-24T23:41:41+08:00`
scope: `BVM_JSL8_500_PHYSICAL_QB_RECHECK_V1`

本文件只建立论文用途与仓库拓扑的 provenance 边界，不把论文仿真、仓库
历史 raw 或本文新的 JoSIM raw 自动升级为硬件测量或 SFQ/Gate 结论。

## 1. Primary sources

### Paper A

M. A. Karamuftuoglu et al., “Superconductor bistable vortex memory for data
storage and readout,” *Superconductor Science and Technology* 38 (2025)
015020, DOI [10.1088/1361-6668/ad9863](https://doi.org/10.1088/1361-6668/ad9863).
本文使用公开 [publisher/NSF PDF](https://par.nsf.gov/servlets/purl/10579139)
作为页码和图号依据。

Paper A 的相关边界：

- §2.4 / Fig.4 的单元 readout 与 Fig.5 的小阵列 readout 使用 sense-line
  上的 `12` 个 non-switching `320 µA` junctions；Fig.6 的 32×32 memory
  demonstration 仍使用 `320 µA` sense-line load。
- §3.2 / Fig.7 是 BVM→QB readout 场景：QB 把输入电流转换为 SFQ；正文说
  QB 被修改为检测单个 BVM 输出，两个 BVM 共用一列，SL 连接到一个 QB，存储
  `1` 时 QB 输出一个 pulse。Fig.7 图面是本次 `8×500` paper-like
  provenance 的来源；图面标签应与正文语义分开记录，不能用 OCR 缺失或旧
  raw 代替图面证据。
- §4 / Fig.8–9 是 8×8 accumulation demonstration；Fig.9 的每条 sense
  line 使用 `12` 个 non-switching junctions，每个 `500 µA`。这不是 Fig.7
  的 single-BVM→QB testbench。
- 论文说明 JSL 是 sense-line 上的非开关 junction stack，用于替代/实现
  sense-line load；本实验只复用其 load-sizing/topology 线索，不声称复现
  论文完整版图或所有寄生参数。

因此，以下三种条件必须始终分开：

| 条件 | 论文用途 | 本项目标签 |
|---|---|---|
| `12×320 µA` | 单元/小阵列/32×32 readout load | `12x320_PHYSICAL_REFERENCE` |
| `8×500 µA` | Fig.7 single-BVM→QB readout provenance；本轮待检验 | `PAPER_JSL8_500_RECHECK` |
| `12×500 µA` | 8×8 simultaneous accumulation load | `ACCUMULATION_12x500_REFERENCE` |

不得把三者写成同一个 topology、同一个 experiment 或同一个 acceptance
condition。

### Paper B

M. A. Karamuftuoglu et al., “Optimized Bistable Vortex Memory Arrays for
Superconducting In-Memory Matrix-Vector Multiplication,” arXiv:2507.04648v1,
[HTML](https://arxiv.org/html/2507.04648v1),
[record/PDF](https://arxiv.org/abs/2507.04648)。

Paper B §2.2 的接口语义是：BVM 输出电流进入 QB；QB 是 thresholding
element；其阈值被调整到单个 BVM cell 的 output level；多个同时读取的
`1` 会在 SL 上累加，并对应可变数量的 SFQ pulses。Paper B §3 的
diagonal-SL/direct-input 结构是 multiplier-array optimization。

本轮只保留 Paper B 的“single BVM output level 是 QB matching target”
作为后续 source-matching 的设计动机；不引入 diagonal SL、direct-input
array、T1 或大规模 QB sweep。

## 2. Repository provenance

仓库中已有两个 8×500 相关历史 deck：

- `test/final/single_bvm_qb/single_bvm_qb.cir`：canonical BVM → 8 个
  `jjmit area=5` → tuned/scaled QB；
- `test/final/single_bvm_qb/test_bvm_paper_bq.cir`：canonical BVM → 8 个
  `jjmit area=5` → `BQ_PAPER`。

它们只能作为 `HISTORICAL_TOPOLOGY_REFERENCE`。其旧 phase/SFQ/event 计量
口径已经被当前 `METRIC_SPEC_V2` 与项目审计 supersede；不得引用旧
`fast_events`、把 raw `P(...)` 直接当 turns、或引用旧 SFQ count。

当前 recheck 的 primary topology 必须重新生成并重新 hash：

```text
canonical BVM SL
  → B_LD1 ... B_LD8, each jjmit AREA=5 (nominal Ic≈500 µA)
  → physical QB IN
  → frozen scaled QB, R_LOAD=10 Ω
```

历史 deck 不提供当前 run 的 timing、metric、event count 或 verdict。

## 3. Current experiment boundary

`BVM_JSL8_500_PHYSICAL_QB_RECHECK_V1` 只改变 JSL configuration，相对已接受
的 `physical-bvm-jsl12-qb-sfq-closure-v1-20260824` 保持 BVM、READ protocol、
QB 参数、bias、output load、timestep、stop time、measurement windows 和
四工况角色不变；唯一物理自变量是 `12×AREA=3.2` → `8×AREA=5`。

canonical roles remain:

- `logical1_read`: positive WL+BL initialization + positive WL+SE READ；
- `logical0_read`: negative WL+BL initialization + the same positive WL+SE READ；
- `logical1_no_read_control`；
- `logical0_no_read_control`。

本轮不修改 canonical BVM，不增加 READ width，不做 magnetic coupling，不接
standard JTL/T1，不先优化 QB，也不进入大规模参数 sweep。

## 4. Evidence labels

- **Paper fact**：论文正文或图面明确写出的用途、负载或接口语义；
- **Repository topology provenance**：历史 `.cir` 对接线/元件数量的记录；
- **Current observed**：本轮新 raw 直接观察到的波形、JSL guard、KCL 或
  phase/area arithmetic；
- **Derived**：按 `METRIC_SPEC_V2` 和本轮预注册窗口计算的量；
- **Inference**：与对照相容的 load-line/source-matching 解释；
- **Unknown**：论文未给出或本轮未测的参数、收敛、重复读和下游传播。

尤其注意：论文中的 “SFQ pulse” 是论文电路描述；本项目仍必须用同一 JJ、
同一端点、同一连续单调 segment、同一时间窗的 phase/voltage-area 双证据
审计当前仿真，不能由论文文字替代当前 event evidence。

## 5. Topology discrepancy disposition

当前没有发现阻止本轮的 topology discrepancy：仓库历史 8×500 deck 与本轮
要求均为 8 个 `AREA=5` JSL 串联，末端进入物理 QB 输入，且不含 ideal replay
source。新 fixture 仍须在运行前机械检查 exactly 8、每个 `AREA=5`、无
JSL-to-ground 终端、single QB、unchanged QB local bias/load；任何检查失败
都必须将 artifact 标为 `INVALID` 并停止，不得强行修线。

