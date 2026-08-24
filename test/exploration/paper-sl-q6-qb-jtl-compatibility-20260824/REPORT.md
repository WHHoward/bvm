# PAPER-SL-Q6 report：frozen Q5 QB → standard two-cell JTL

主 verdict：**`NO_JTL_TRIGGER`**

本报告只分析 Q6 coupling fixture 的 raw CSV；没有重跑 JTL positive control。positive-control provenance 与同一两-cell standard chain 的有效性来自 accepted R11-A。Q5 的 `R_LOAD OUT 0 10Ω` 在 Q6 中保留，并与第一 cell input network 并联。

## Artifact / execution

- 四个 case 均应有 exit=0、stderr 空、13,599 个 data rows；时间来自 CSV，median `dt=0.0125 ps`，不得用旧 `fast_events`。
- Q5 QB、`IBIAS=40 µA`、replay、所有 QB L/R/AREA/model 参数未改；新增只有标准 `JTL.cir` include、两 cell、`R_TERM=1Ω` 和 probes。
- 这是 Q5 replay fixture，不是 physical BVM connection；因此本报告不声称新的 `SL/N6/JM/JS` source guard。

## Event evidence: four standard-JTL junctions

| case | JJ | activity range (turn) | largest monotonic (turn) | same-segment area (Φ0) | residual (turn) | complete events | post complete | onset→end (ps) | post p2p (turn) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| paper-j1-logical1-read0-control | `B1|XJTL1` | 2.4207467e-05 | 2.4207467e-05 | 2.4219404e-05 | 1.1937503e-08 | 0 | 0 | 94→94.975 | 9.8676065e-07 |
| paper-j1-logical1-read0-control | `B2|XJTL1` | 1.5374368e-05 | 1.5374368e-05 | 1.537765e-05 | 3.2827777e-09 | 0 | 0 | 94.7375→95.8375 | 5.8887329e-07 |
| paper-j1-logical1-read0-control | `B1|XJTL2` | 1.0583804e-05 | -1.0583804e-05 | -1.0580404e-05 | 3.3996053e-09 | 0 | 0 | 94.4625→95.575 | 4.4563384e-07 |
| paper-j1-logical1-read0-control | `B2|XJTL2` | 1.0122254e-05 | 1.0122254e-05 | 1.0116487e-05 | -5.7671607e-09 | 0 | 0 | 94.1875→95.3 | 4.1380285e-07 |
| paper-j1-logical1-read | `B1|XJTL1` | 0.068937757 | -0.063032854 | -0.06303502 | -2.1664836e-06 | 0 | 0 | 107.325→109.9125 | 0.0068322511 |
| paper-j1-logical1-read | `B2|XJTL1` | 0.020663882 | -0.017496603 | -0.01749758 | -9.7716303e-07 | 0 | 0 | 107.575→110.25 | 0.0054369716 |
| paper-j1-logical1-read | `B1|XJTL2` | 0.0071443222 | -0.0051175635 | -0.0051190693 | -1.5057346e-06 | 0 | 0 | 122.925→124.0625 | 0.0027497677 |
| paper-j1-logical1-read | `B2|XJTL2` | 0.0028848107 | -0.002821658 | -0.0028224874 | -8.2943271e-07 | 0 | 0 | 125.7375→126.875 | 0.0025050988 |
| paper-j0-logical0-read | `B1|XJTL1` | 0.0032953668 | 0.0032953668 | 0.0032963992 | 1.0324543e-06 | 0 | 0 | 111.5125→112.6125 | 0.00081619429 |
| paper-j0-logical0-read | `B2|XJTL1` | 0.0016719863 | -0.0016719863 | -0.0016725096 | -5.2322086e-07 | 0 | 0 | 113.35→114.4625 | 0.00050662201 |
| paper-j0-logical0-read | `B1|XJTL2` | 0.00079851218 | 0.00079851218 | 0.00079875582 | 2.4364178e-07 | 0 | 0 | 115.2125→116.325 | 0.00029072833 |
| paper-j0-logical0-read | `B2|XJTL2` | 0.00047658948 | -0.00047658948 | -0.0004767281 | -1.3862602e-07 | 0 | 0 | 119.1625→120.275 | 0.00027850523 |
| paper-j0-logical0-read0-control | `B1|XJTL1` | 2.4207467e-05 | -2.4207467e-05 | -2.4219721e-05 | -1.2254525e-08 | 0 | 0 | 94→94.975 | 9.8676065e-07 |
| paper-j0-logical0-read0-control | `B2|XJTL1` | 1.5374368e-05 | -1.5374368e-05 | -1.5367269e-05 | 7.0984662e-09 | 0 | 0 | 94.725→95.8375 | 6.0478878e-07 |
| paper-j0-logical0-read0-control | `B1|XJTL2` | 1.0583804e-05 | 1.0583804e-05 | 1.0579694e-05 | -4.1096794e-09 | 0 | 0 | 94.4625→95.575 | 4.2971835e-07 |
| paper-j0-logical0-read0-control | `B2|XJTL2` | 1.0106339e-05 | -1.0106339e-05 | -1.0108751e-05 | -2.4117794e-09 | 0 | 0 | 94.1875→95.3125 | 4.2971835e-07 |

其中 `complete events` 只统计 continuous unwrapped phase 的单调 segment：幅度至少 1 turn，且同一 JJ/同一 segment 的 direct voltage area 与 phase 的 residual 在预注册容差内。phase range、voltage peak、I>Ic 不能单独形成 event。

## QB local response and output loading

| case | BJs largest / source activity | BJL1 largest / area / events | BJL2 largest / area / events | OUT activity p2p (V) | L0 activity p2p (A) | JTL input I(L1) activity p2p (A) |
|---|---:|---:|---:|---:|---:|---:|
| paper-j1-logical1-read0-control | 0.00018038771 / source | -9.6718459e-05 / -9.6744495e-05 / 0 | -1.7459297e-05 / -1.7455334e-05 / 0 | 4.564695e-08 | 2.267e-08 | 1.822e-08 |
| paper-j1-logical1-read | 14.092115 / source | -0.73054583 / -0.7305636 / 0 | -0.22924971 / -0.22925513 / 0 | 0.0002982167 | 0.00010596386 | 9.926065e-05 |
| paper-j0-logical0-read | 0.023675727 / source | 0.021945095 / 0.021951203 / 0 | 0.0050798916 / 0.0050813269 / 0 | 1.5058267e-05 | 4.41298e-06 | 3.35293e-06 |
| paper-j0-logical0-read0-control | -0.00018038771 / source | 9.6718459e-05 / 9.6743966e-05 / 0 | 1.7459297e-05 / 1.7449997e-05 / 0 | 4.564649e-08 | 2.266e-08 | 1.822e-08 |

| case | I(R_LOAD) pre median (µA) | activity p2p (µA) | I(L0|XBQ) pre median (µA) | JTL mid p2p (µV) | JTL out p2p (µV) | I(R_TERM) activity p2p (µA) |
|---|---:|---:|---:|---:|---:|---:|
| paper-j1-logical1-read0-control | 0.00018477935 | 0.004564695 | -16.362355 | 0.0235997 | 0.007152743 | 0.007152743 |
| paper-j1-logical1-read | 0.00018477935 | 29.82167 | -16.362355 | 26.47273 | 2.0877 | 2.0877 |
| paper-j0-logical0-read | -0.00018475825 | 1.5058267 | -16.36421 | 3.154552 | 0.3461361 | 0.3461361 |
| paper-j0-logical0-read0-control | -0.00018475825 | 0.004564649 | -16.36421 | 0.02359992 | 0.007152375 | 0.007152375 |

Q5 isolated replay 的 accepted read1 reference 是 BJL1 forward `0.74886825` turn、BJL2 largest `0.96817867` turn、BJL2 complete count=0；Q6 的 coupling 结果必须与这些值分开解释。Q6 read1 BJL2 complete count=0，四颗 JTL JJ 是否各 exactly-one：`False`。

## Observed

- verdict 对应的 JTL count 向量为：read1 `[0, 0, 0, 0]`；read0 `[0, 0, 0, 0]`；两个 READ=0 controls 分别 `[[0, 0, 0, 0], [0, 0, 0, 0]]`。
- 逐颗 JJ 的最大 monotonic segment、同段 area、onset/end 和 post p2p 已在上表给出；QB BJs 的 multi-turn source activity不被当作 JTL delivery。
- `R_LOAD` 与 JTL input branch 的活动电流分开记录，未把 OUT 电流默认归属于任一 branch。

## Derived

- 若四颗 JTL JJ 都 exactly-one 且 onset 顺序为 `XJTL1.B1 → XJTL1.B2 → XJTL2.B1 → XJTL2.B2`，才构成 full tested chain 的 propagated event；否则不能称 propagated success。
- `COUPLED_QB_JTL_CLOSURE` 需要额外满足 read1 的 BJL2 也有一个同段 phase/area-consistent complete event；JTL 成功本身不自动证明 isolated QB event。

## Inference

在本固定 Q5 load + standard JTL input 边界下，结果属于 `NO_JTL_TRIGGER`。该结论只覆盖这一 coupling point；若 JTL 无触发，表示 frozen Q5 output 在该真实 load boundary 下不足以触发标准 JTL，不否定其他带 conditioner 的 receiver。若 JTL 触发，也只能称耦合系统的 regenerative compatibility，不能回写为 isolated QB SFQ generation。

## Unknown / boundary

- 没有 physical BVM、12-JSL 或 canonical SL/N6 raw 参与本轮，故不报告 BVM back-action；Q6 是 accepted paper-JSL-shaped replay 到 JTL 的 coupling probe。
- 保留 10Ω load 会让 OUT 同时承受 Q5 external load 与 JTL input network；这是 preregistered load choice，不是对 JTL 或 QB 的参数优化。
- 本轮停止后不调 JTL/QB，不接 T1，不把单点结果升级为 architecture-wide theorem。

## Stop rule

本 checkpoint 完成后停止，不提出或执行下一枚参数点。
