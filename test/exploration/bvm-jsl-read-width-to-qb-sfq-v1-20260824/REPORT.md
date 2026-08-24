# BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1 — final Exploration report

## Objective

验证延长 canonical BVM READ plateau 是否能在保持 read0/READ=0 discrimination
和 source/storage guard 的前提下，增加 external 12-JSL source 的 useful
read1 waveform，并将其推动 frozen scaled QB 进入 exactly-one window。

## Frozen boundaries

- canonical `circuits/bvm/bvm_cell.cir` 不变；
- Phase A 使用 external `R_LD=12 Ω`；
- Phase B 使用 accepted external-series 12×`jjmit AREA=3.2` JSL load，canonical
  BVM 内部 `L_SL/R_SL/L_PSL` 不替换；
- Phase C 使用 frozen scaled QB：BJs/BJL1/BJL2 AREA `.50/.36/.54`，
  `IBIAS=35 µA`，`Lin/L0/L1/L2=.80/1.323/3.91/3.91 pH`，
  `RJ1/RJ2=33/22 Ω`，`RB=6 Ω`，`R_LOAD=10 Ω`；
- 不接 JTL/T1，不做注册范围外的 sweep。

## Verdicts

| stage | verdict | meaning |
|---|---|---|
| Phase A | `DURATION_SUPPORTED` | 12 ps 是本 fixture 中最短的 useful read1 width point |
| Phase B | `PAPER_JSL_WSTAR_SOURCE_VALID` | W*=12 的 external 12-JSL source bounded 且 state-selective，可进入 replay gate |
| Phase C | `WIDTH_IMPROVES_QB_MARGIN_BUT_SUBTHRESHOLD` | frozen QB read1 margin 增强，但 BJL2 没有完整 event |

## Result chain

Phase A 的 read1 positive baseline-subtracted `I(L_SL)` area 为：

```text
9 ps   357.742 µA·ps
12 ps  466.278 µA·ps
15 ps  568.366 µA·ps
20 ps  775.590 µA·ps
```

logical0 在这些点约为 `56.6–57.5 µA·ps`，READ=0 controls 接近零；因此
注册选择规则选择最短有效点 `W*=12 ps`，而不是 15/20 ps。

Phase B 中，W*=12 的 12 个 JSL 均没有 complete local event。read1 的
`I(L_SL)` range 为 `−21.0247…79.0668 µA`，logical0 为
`−3.51369…3.63586 µA`；SL/N6 与 JM/JS guards 仍保持 bounded。

Phase C 的关键 QB comparison 为：

```text
                     BJL2 largest segment       same-JJ voltage area
accepted Q1 9 ps     0.892527 turn              0.892537 Phi0
W*=12 ps             0.975402 turn              0.975411 Phi0
```

W*=12 logical0 的最大段约为 `−0.00528549 turn`，READ=0 controls 约为
`±2.5×10⁻⁵ turn`，全部为 zero complete event。read1 的改善是实质的
near-threshold response gain，但仍没有达到 `≥1 turn` 的同段 phase/area
判据。

## Event and interpretation policy

本报告不把以下任何单项当作 SFQ event：总 phase range、单点 voltage peak、
`I>Ic`、或旧 fast-event heuristic。只有同一 JJ、同一连续单调段满足完整
phase evolution、同段直接 voltage area consistency，并且 post bounded/retrap，
才可计为 local event。

## Evidence classification

### Observed

- Phase-A、Phase-B、Phase-C raw 和 generated inputs/logs 均保存在本目录；
- Phase-C replay 保留 W*=12 JSL current 的实际 CSV time grid、原极性和原幅值；
- read1/read0/control 的 QB activity 分离保持。

### Derived

- 12 ps 是注册候选中的最短 source-side useful width；
- W*=12 的 ideal replay 相比 accepted 9 ps comparator 将 BJL2 最大同向段从
  `0.892527` 推到 `0.975402 turn`，但 event count 仍为 0。

### Inference

- frozen scaled QB 的 dynamic window 仍未被 READ-width-only conditioning 关闭；
- 该结果支持“width 可改善 margin”，不支持“width alone 足以产生 exactly-one”。

### Unknown

- 尚未测 physical `BVM → 12-JSL → QB` 的联合 load-line/back-action；
- 尚未测 JTL/T1 传播；
- 不能据此判定其它 QB 参数或其它 conditioner route 的普遍不可能性。

## Source/provenance boundary

Phase-B 的 logical0 accepted source fixture 保留其原始 deck 语义：该 accepted
deck 只有一个 active `+100 µA` READ transition，而不是 canonical BVM
`WL+SE` 双 transition。该已接受 raw 没有被静默修正；它的作用仅限于 Phase-B
source-stage comparison。Phase-A 的 logical0 使用 canonical internal-readout
accepted raw。

电流 waveform 的可视化单独保存在
`plots/9ps-vs-Wstar-qb-current-comparison.html`，覆盖 BJs、BJL1、BJL2 和
`I(I_REPLAY)`，用于查看 current partition 与 source replay 差异；它不替代
phase/voltage-area event analysis。

## Stop rule

本 Exploration 在 Phase C 结束后停止。下一步若要继续，必须另开并重新
preregister physical BVM→12-JSL→QB 的 load-line experiment；本报告不授权该
实验。
