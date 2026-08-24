# BVM_JSL8_500_PHYSICAL_QB_RECHECK_V1

## 状态与边界

- tier：`Exploration`
- recorded_at：`2026-08-24T23:45:09+08:00`
- parent HEAD：`ff80ce285a2ce97f2414a19a7f8d6b92d8b1d3ae`
- 研究对象：`canonical BVM SL → 8×jjmit AREA=5 → frozen scaled QB`
- 参考对象：已接受的 `physical-bvm-jsl12-qb-sfq-closure-v1-20260824` 的
  13 ps、12×AREA=3.2 physical raw；它只作 matched reference，不替代本轮
  raw 的证据。
- canonical BVM、`bq_cell.cir` 的 frozen QB 参数、WL/BL/SE 语义、QB bias 与
  `R_LOAD=10 Ω` 均冻结；本轮只改变 JSL 数量/AREA 这一项。
- 本轮只运行 13 ps 四工况。没有 magnetic coupling、READ width sweep、JTL、
  T1、QB retuning、QB optimization 或 canonical BVM 修改。

## 论文接口审计边界

Paper A 是 *Superconductor bistable vortex memory for data storage and readout*：
`12×320` 属于单元/小规模 memory demo 的 non-switching JSL，`8×500` 是
Fig.7 的 single-BVM→QB readout interface，`12×500` 属于 8×8 accumulation
的不同结构。它们不能合并成一个 “JSL width” 参数。Paper B 的 QB threshold、
multiple-BVM current accumulation、variable SFQ pulse 与 diagonal-SL/direct-input
优化也不导入本轮 single-BVM closure。

详细来源和 legacy deck 边界见
[`docs/BVM_QB_PAPER_INTERFACE_AUDIT.md`](../../../docs/BVM_QB_PAPER_INTERFACE_AUDIT.md)。
主要论文来源为 [Paper A PDF](https://par.nsf.gov/servlets/purl/10579139) 与
[Paper B HTML](https://arxiv.org/html/2507.04648v1)。

## Scientific question

在 frozen BVM/QB/read/bias/load 条件下，把已失败的 physical
`12×320` JSL 换成 Paper-A-like `8×500` JSL，是否能在 13 ps 恢复
`logical1_read` 的 BJL2 one-SFQ candidate，同时保持 logical0、READ=0
controls 为零/有界，并保持 8 个 JSL non-switching？

因果图：

```text
canonical BVM SL ── B_LD1 ... B_LD8 (AREA=5) ── QB IN ── frozen scaled QB
```

JSL8 的末端必须是 QB 的真实 `IN`；不允许 JSL 接地终止、ideal replay source、
并行替代支路或第二个 QB。

## Frozen numerical setup

- solver：`build/josim-cli v2.7.2837d13`
- solver SHA-256：`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- timestep：`dt=0.0125 ps`
- stop：`170 ps`
- READ：正向 WL+SE，`96–109 ps`，与 12×320 physical 13 ps reference 相同
- write：WL/BL 在 `11–20 ps` 施加 `±100 µA`，之后归零
- QB：BJs=.50、BJL1=.36、BJL2=.54，Lin=.8 pH，L0=1.323 pH，
  L1=L2=3.91 pH，RJ1=33 Ω，RJ2=22 Ω，RB=6 Ω，IBIAS=35 µA，RLOAD=10 Ω
- metric spec：`docs/METRIC_SPEC_V2.md`，SHA-256
  `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`

### 小信号诊断（不是 transient 等效）

只记录 `ZERO_PHASE_SMALL_SIGNAL_ESTIMATE_ONLY`：按 JSL junction 小信号电感
估算，12×320 约 `12.34 pH`，8×500 约 `5.27 pH`，比值约 `0.427`。该值不能
替代 transient load-line、不能证明 back-action 改善，也不能用来预测 SFQ。

## Registered cases

| case | state | READ | 预注册用途 |
|---|---|---|---|
| `logical1_read` | WL=BL=+100 µA | 正向 WL+SE | primary positive |
| `logical0_read` | WL=BL=-100 µA | 同一正向 WL+SE | negative control |
| `logical1_no_read_control` | WL=BL=+100 µA | 无 READ | zero control |
| `logical0_no_read_control` | WL=BL=-100 µA | 无 READ | zero control |

## Measurements and evidence contract

- BVM：JM1/JM2、JS1/JS2 的 P/V，`I(L_PSL)`、`I(L_SL)`、`V(SL1)`、`V(N6)`。
- JSL：B_LD1…B_LD8 的 P/V/I；检查 series current、phase activity 与是否有
  complete same-segment phase/voltage evidence。
- QB：BJs/BJL1/BJL2 的 P/V/I，`V(IN)`，`I(Lin)`，以及 L1/L2/L0/RB/RJ1/RJ2
  branch currents；直接检查 node2/node3/node4 KCL。
- 所有 P 图使用原始 JoSIM phase `P(t)/(2π)` 的 continuous absolute turns。
  它不是 SFQ count；导数、阈值样本、局部 JJ activity 都不单独构成 event。
- BJL2 event 只有在同一 JJ、同一连续单调 segment、同一端点方向的 phase
  `|ΔP|/(2π)≥1` 与 `∫Vdt/Φ0` 同时成立，且残差
  `≤ max(0.05 turn, 10%×|Δturn|)`，并且 post window 没有第二个完整段，才可
  进入 one-SFQ classification。
- 所有 B_LD1…B_LD8 的 complete phase/area segment 都会触发
  `PAPER_JSL_NONSWITCHING_ASSUMPTION_VIOLATED`；JSL activity 不能被写成
  downstream SFQ delivery。

窗口：`PRE=[80,94) ps`、`ACTIVE=[94,130) ps`、`POST=[140,170) ps`。

## Comparison pages registered before execution

必须由标准 `scripts/josim-plot2.py` 生成，且保留 metadata：

- `plots/12x320-vs-8x500-source-loadline.html`
- `plots/12x320-vs-8x500-qb-transfer.html`
- `plots/12x320-vs-8x500-port-trajectory.html`
- `plots/12x320-vs-8x500-jsl-current-phase.html`
- 四个 13 ps case pages

comparison 至少覆盖同一 case 的 `I(L_SL)`、`V(SL1)`、`V(IN)`、`I(Lin)`、
BJs/BJL1/BJL2，以及 JSL current/phase。`port-trajectory` 是以时间参数化的
`V(IN)`–`I(Lin)` load-line view；它不会被解释为静态等效阻抗。

## Decision tree

1. 若 13 ps `logical1_read` 为 `CLEAN_ONE_SFQ_CANDIDATE`，logical0/read=0
   controls 为零/有界、BVM guard 保持 bounded、8 个 JSL 均 non-switching：
   `PAPER_JSL8_500_PHYSICAL_ONE_SFQ_CANDIDATE`。只有这一项成立，才允许另行
   追加 `dt=0.00625 ps` 和 rewrite/read；本轮不自动追加。
2. 若 BJL1/BJL2 相对 12×320 有可见恢复但仍低于 one-SFQ：
   `PAPER_JSL8_IMPROVES_PHYSICAL_MARGIN`；仅此时 14 ps backup 获得授权，
   但本轮不自动运行。
3. 若改善不足：`JSL_SIZING_NOT_SUFFICIENT`，停止；后续方向只能另立
   `SOURCE_MATCHED_QB_V1`。
4. 若 BJs 仍 multi-turn、BJL1/BJL2 仍反向或 subthreshold：报告
   `QB internal load-line mismatch` 这一证据支持的机制边界，不再增加 width。
5. 任一 JSL complete event：`PAPER_JSL_NONSWITCHING_ASSUMPTION_VIOLATED`，
   不得称 paper-like candidate。

本预注册只约束本轮 Exploration；它不冻结全局硬件阈值，也不把 bounded
negative observation 升格为 universal impossibility。最终报告完成上述十项
问题后停止，不自动启动下一阶段。
