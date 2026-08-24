# BVM_JSL8_500_PHYSICAL_QB_RECHECK_V1

## 结论先行

本轮在当前 HEAD `ff80ce285a2ce97f2414a19a7f8d6b92d8b1d3ae` 下完成了预注册的
13 ps 四工况 physical recheck：

```text
canonical BVM SL → 8 × jjmit AREA=5 → frozen scaled QB → R_LOAD=10 Ω
```

正式 Exploration 分类为：

```text
PAPER_JSL8_IMPROVES_PHYSICAL_MARGIN
```

这表示相对已接受的 12×320 physical reference，logical1 的 BJL1/BJL2
subthreshold excursion 有小幅幅度恢复；它不表示 one-SFQ closure。新
logical1 BJL2 的最大同段证据为：

```text
ΔP/(2π) = −0.124996 turn
∫Vdt/Φ0 = −0.125006 Φ0
```

仍远低于 1 turn，方向也没有从旧 physical 的 `−0.122128 turn` 转向 ideal
replay 的 `+1.016029 turn`。四个工况均没有 complete BJL2 event；8 个 JSL
均没有 complete phase/voltage event。因此没有得到 physical `1/0/0`，也没有
进入 timestep ladder、rewrite/read、JTL 或 T1。

本轮的下一阶段状态是：**允许另立一个独立的 `SOURCE_MATCHED_QB_V1`
Exploration，但本报告结束即 STOP，本轮不自动启动它。** 这是下一测试方向，
不是已经证明的唯一物理根因。

## Artifact / provenance

- artifact status：`VALID_FOR_EXPLORATION`
- parent HEAD：`ff80ce285a2ce97f2414a19a7f8d6b92d8b1d3ae`
- solver：`build/josim-cli v2.7.2837d13`
- solver SHA-256：`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- `dt=0.0125 ps`，stop=`170 ps`
- 4 个 raw、4 个 stdout/stderr、输入 deck、include snapshot、manifest 和
  SHA-256 清单均保留；stderr 均为空。
- topology precheck：`PASS`；8 个 AREA=5 JSL，`B_LD8→IN`，无 JSL GND 终端、
  无 ideal replay、单一 QB、单一 bias/load、无 magnetic coupling。
- source reference：
  `test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/raw/13/`
  的四个同名 case；reference raw 未被修改。

详细机器结果见 [`analysis/physical-13ps-metrics.json`](analysis/physical-13ps-metrics.json)、
[`analysis/comparison-12x320-vs-8x500.json`](analysis/comparison-12x320-vs-8x500.json)、
[`analysis/13ps-summary.csv`](analysis/13ps-summary.csv) 和
[`manifest.yaml`](manifest.yaml)。

## Evidence labels

- **Observed**：JoSIM raw CSV 中直接读取的 phase、voltage、current、时间窗口和
  KCL residual。
- **Derived**：同一 JJ、同一 continuous monotonic segment 的
  `ΔP/(2π)`、`∫Vdt/Φ0`、p2p、current partition 和 12×320/8×500 比值。
- **Inference**：与当前证据一致的 `QB internal load-line mismatch` 边界；它
  不是已经隔离完成的单一机制证明。
- **Unknown**：本轮没有把 BVM termination、JSL distributed dynamics、QB Lin
  输入阻抗与 QB 内部 branch mismatch 分离；也没有硬件测量或 downstream
  transport evidence。

所有 phase 数字都是原始 JoSIM `P(t)/(2π)` continuous absolute turns，不是
SFQ count。phase activity、导数阈值、局部 junction current 或 BJs 的 multi-turn
都不单独代表下游 SFQ delivery。

## 1. 两篇 paper 分别如何描述 BVM→QB

### Paper A

Paper A（*Superconductor bistable vortex memory for data storage and readout*）
把 BVM readout 的 sense-line junction 作为 non-switching load，并说明 QB 将
输入电流转换为 SFQ；在 single-BVM readout 中，QB 的 threshold 要能识别单个
BVM cell 的输出，stored `1` 产生输出 pulse。两个 BVM 可以共享 column/SL，
再进入一个 QB。Paper A 中的 `8×500` 是 Fig.7 single-BVM→QB readout 的
paper-like interface；`12×320` 是单元/小规模 memory demonstration 的
non-switching JSL；`12×500` 属于 8×8 accumulation 的另一种 source/load
角色。不能把三者合并为一个 JSL 参数。

Paper A primary source：
[NSF-hosted PDF](https://par.nsf.gov/servlets/purl/10579139)，另见
[DOI record](https://doi.org/10.1088/1361-6668/ad9863)。本仓库的逐项接口审计见
[`docs/BVM_QB_PAPER_INTERFACE_AUDIT.md`](../../../docs/BVM_QB_PAPER_INTERFACE_AUDIT.md)。

### Paper B

Paper B（*Optimized Bistable Vortex Memory Arrays for Superconducting
In-Memory Matrix-Vector Multiplication*）讨论的是更广的 matrix-vector
architecture：QB threshold 调整到 single-BVM output level，多个 BVM 的
simultaneous output current 可以积累，并映射为 variable SFQ pulse count。
diagonal-SL/direct-input 是阵列 multiplier 的结构优化，不是本轮 single-BVM
closure 的 topology 变量。

Paper B primary source：[arXiv HTML](https://arxiv.org/html/2507.04648v1)。

因此，本轮只验证一个受限问题：frozen scaled QB 是否能承受并正确量化真实
`BVM→8×500 JSL` interface；没有把本轮结果写成阵列乘法或 variable-pulse
硬件结论。

## 2. 8×500 与 12×320 testbench 的角色

| fixture | 本轮角色 | 是否 primary |
|---|---|---|
| `8×500` | Paper-A-like single-BVM→QB physical recheck；8 个 JSL 直接串到 QB `IN` | 是，本轮 primary |
| `12×320` | 已接受 physical BVM→QB 的 matched source/load reference | 是 comparison reference，不是新 raw |
| `12×500` | Paper-A 8×8 accumulation/load 角色 | 否，本轮不导入 |

两者共同冻结 canonical BVM、正向 READ、QB scaled parameters、bias、10 Ω
load、dt 和 stop；本轮唯一 causal change 是 `12×AREA=3.2` →
`8×AREA=5`。

zero-phase 小信号量只作诊断：12×320 约 `12.34 pH`，8×500 约 `5.27 pH`，
比值约 `0.427`，标记为 `ZERO_PHASE_SMALL_SIGNAL_ESTIMATE_ONLY`，不作为
transient equivalent inductance 或 SFQ 预测。

## 3. 历史 8×500 fixtures 与旧 metrics 的边界

仓库历史的 [`test/final/single_bvm_qb/single_bvm_qb.cir`](../../../test/final/single_bvm_qb/single_bvm_qb.cir)
和 [`test/final/single_bvm_qb/test_bvm_paper_bq.cir`](../../../test/final/single_bvm_qb/test_bvm_paper_bq.cir)
可以作为 BVM→JSL→QB 拓扑和 terminal provenance：前者是 canonical BVM→8×
`jjmit AREA=5`→tuned/scaled QB，后者是 BVM→8×500→`BQ_PAPER`。

但这些历史 deck 的 phase/SFQ/event metrics 不能直接复用：它们没有本轮冻结
的 current source/load-line、同一 QB 参数、同一窗口与同一 phase/voltage
双证据契约。`BQ_PAPER` 只保留为 secondary reference，不能未经验证地写成
Paper A Fig.7 QB。新 primary raw 是本目录四个 13 ps case。

## 4. 8×500 是否改变 V(SL)-I(SL) / V(IN)-I(Lin) load-line

**Observed / Derived：是，transient trajectory 明显改变；这不是静态阻抗拟合。**

对 logical1 READ 的 `[94,130) ps` activity window：

| 信号 | 12×320 | 8×500 | 8×500 / 12×320 |
|---|---:|---:|---:|
| `I(L_SL)` p2p | 94.526 µA | 115.998 µA | 1.227 |
| `V(SL1)` p2p | 4.117 mV | 3.541 mV | 0.860 |
| `V(N6)` p2p | 3.752 mV | 3.403 mV | 0.907 |
| `V(IN)` p2p | 2.511 mV | 3.115 mV | 1.240 |
| `I(Lin)` p2p | 94.526 µA | 115.998 µA | 1.227 |

这同时说明两点：source current 没有 collapse，且 source-side voltage 与
QB-port voltage trajectory 都变了。`V(IN)`–`I(Lin)` 页面是时间参数化
load-line view，不把它解释成一个静态 `R/L` 等效值。

图：[`12x320-vs-8x500-source-loadline.html`](plots/12x320-vs-8x500-source-loadline.html)、
[`12x320-vs-8x500-port-trajectory.html`](plots/12x320-vs-8x500-port-trajectory.html)。

## 5. BJs multi-turn 是否缓解

**没有缓解，反而增强。** logical1 READ 的 BJs 最大同段从 12×320 的
`+5.9510118 turn` 变为 8×500 的 `+6.8991954 turn`；activity p2p 从
`6.1681431` 变为 `7.2795267 turn`。这只是 BJs local activity，不能称为
downstream SFQ。8×500 把 upstream excursion 增强了，但没有把它转成 BJL2
one-SFQ。

## 6. BJL1 是否恢复正确方向

**没有。** logical1 READ 的 BJL1 最大同段为：

```text
12×320: −0.251930 turn / −0.251955 Φ0
 8×500: −0.275370 turn / −0.275406 Φ0
```

幅度有小幅增加，但方向仍为负；没有恢复到 ideal replay 所需的正向方向。
因此这不是 clean downstream transfer，只是 QB internal branch 的 bounded
subthreshold response。

## 7. BJL2 是否从 −0.122 向 ideal +1.016 恢复

**没有。** logical1 READ 的同段 phase/area 为：

| boundary | phase | voltage area |
|---|---:|---:|
| 12×320 physical | `−0.122128 turn` | `−0.122131 Φ0` |
| 8×500 physical | `−0.124996 turn` | `−0.125006 Φ0` |
| ideal replay reference | `+1.016029 turn` | `+1.016037 Φ0` |

8×500 相对旧 physical 的绝对幅度变化仅约 `+0.002868 turn`，而不是朝
`+1.016029` 恢复；符号也仍然相反。BJL2 的 phase/area 双证据本身是一致的，
但它明确证明的是一个约 `0.125 turn` 的 bounded subthreshold excursion。

## 8. 是否得到 physical 1/0/0

**没有。** 四个 case 的 BJL2 分类均为 `SUBTHRESHOLD`：

| case | BJL2 最大同段 | 同段 area | 分类 |
|---|---:|---:|---|
| logical1 READ | `−0.124996 turn` | `−0.125006 Φ0` | `SUBTHRESHOLD` |
| logical0 READ | `−0.023009 turn` | `−0.023011 Φ0` | `SUBTHRESHOLD` |
| logical1 READ=0 | `−0.00000215 turn` | `−0.00000214 Φ0` | bounded zero control |
| logical0 READ=0 | `+0.00000218 turn` | `+0.00000217 Φ0` | bounded zero control |

8 个 JSL 的 series current 最大跨 junction deviation 为约
`1.0×10⁻⁹ µA`，四个 case 都没有 JSL complete phase/area segment；因此
`PAPER_JSL_NONSWITCHING_ASSUMPTION_VIOLATED` 未触发。QB node2/node3/node4
最大 KCL residual 约为 `1.3×10⁻⁵ µA`、`5.0×10⁻⁶ µA`、`1.3×10⁻⁵ µA`，
KCL 没有成为失败原因。

## 9. 失败更接近 JSL sizing insufficient 还是 QB source matching required

本轮正式分类不是 `JSL_SIZING_NOT_SUFFICIENT`：8×500 对 BJL1/BJL2 的
subthreshold 幅度相对 12×320 有小幅恢复，因此 JSL sizing 确实改变了
physical margin。但它仍没有 closure，且 BJs 继续 multi-turn、BJL1/BJL2
仍反向/subthreshold。当前最有证据支持的边界是：

```text
QB internal load-line mismatch
```

这不等价于已经证明“唯一根因就是 QB source matching”。正确的研究结论是：
**JSL8 的 sizing effect 不足以闭合；下一项可区分机制的测试应保持 BVM/JSL8
冻结，另立 `SOURCE_MATCHED_QB_V1` 去测试 QB source matching。** 本轮没有
同时 retune BJs/BJL1/BJL2/RB/IBIAS/L1/L2，所以 JSL effect 与 QB retuning
仍然分开。

## 10. 是否授权下一阶段 SOURCE_MATCHED_QB_V1

**条件性允许另立，但本轮不执行。** 依据预注册 decision tree，8×500 已经
显示小幅 margin improvement 但没有 one-SFQ closure，因此可以提出新的
`SOURCE_MATCHED_QB_V1` Exploration，约束为：

- canonical BVM frozen；
- 8×500 physical JSL topology frozen；
- 只改变并预注册 QB source-matching 变量；
- 不与 JTL/T1、magnetic coupling、READ width sweep 或大规模 QB sweep 合并。

本报告到此 STOP。没有运行 14 ps backup；由于本轮不是 candidate，也没有运行
`dt=0.00625 ps` 或 rewrite/re-read。

## 附录：图、结构图与分析边界

- source/load-line：[`12x320-vs-8x500-source-loadline.html`](plots/12x320-vs-8x500-source-loadline.html)
- QB transfer/KCL context：[`12x320-vs-8x500-qb-transfer.html`](plots/12x320-vs-8x500-qb-transfer.html)
- port trajectory：[`12x320-vs-8x500-port-trajectory.html`](plots/12x320-vs-8x500-port-trajectory.html)
- JSL current/phase：[`12x320-vs-8x500-jsl-current-phase.html`](plots/12x320-vs-8x500-jsl-current-phase.html)
- four case pages：[`plots/cases/`](plots/cases/)
- publication schematic：[`schematic.svg`](topology/publication/BVM_JSL8_SCALED_QB_PHYSICAL/schematic.svg)
- annotated schematic：[`schematic-annotated.svg`](topology/publication/BVM_JSL8_SCALED_QB_PHYSICAL/schematic-annotated.svg)
- semantic validation：`PASS`；geometric validation：`PASS`

本报告没有把 visualization、raw replay、局部 phase activity 或 deterministic
hash replay 升格为硬件 measurement，也没有把 bounded negative result 升格为
universal impossibility。
