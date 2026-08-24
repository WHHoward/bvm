# PAPER-SL-Q6 topology / load precheck

## Provenance

Q6 使用 accepted Q5 `(L1,L2)=(4.50,4.50) pH, IBIAS=40 µA` replay decks作为唯一 source；JTL 采用 R11-A 已验证的 `circuits/standard/JTL.cir`。R11-A positive-control 已证明同一 `THmitll_JTL` 两-cell chain 可以在四颗 JJ 上形成 phase/voltage-area 一致的传播 event，因此 Q6 不重复 positive-control execution。

## Closed netlist

```text
I_REPLAY 0 IN <Q5 byte-identical source>
XBQ IN OUT IBIAS BQ
R_LOAD OUT 0 10
I_IBIAS 0 IBIAS pwl(... 40u ...)

XJTL1 OUT JTL_MID THmitll_JTL
XJTL2 JTL_MID JTL_OUT THmitll_JTL
R_TERM JTL_OUT 0 1
```

`BQ` 内部保持 Q5：

```text
Lin IN 1 0.8p
L0 4 OUT 1.323p
L1 2 3 4.50p
L2 3 4 4.50p
BJs 1 2 jjmit area=0.50
BJL1 2 0 jjmit area=0.36
BJL2 4 0 jjmit area=0.54
RJ1 2 0 33
RJ2 4 0 22
RB IBIAS 3 6
```

## KCL / DC path

- `OUT` 是 `L0`、保留的 `R_LOAD` 和 `XJTL1.a` 的唯一公共节点。`L0` 在 DC 是短路，因此 QB node4 的 output current 可同时流入 `R_LOAD` 和 JTL input；Q6 不假设任何一个 branch 独占 output current。
- `XJTL1.a=OUT`，其内部 `L1` 先进入第一 cell node 1；cell 内的 JJ、bias tee、电感和接地 LP branches提供完整 DC/transient return。`XJTL1.q=JTL_MID=XJTL2.a`，第二 cell 继续使用原标准 chain；`XJTL2.q=JTL_OUT` 通过 `R_TERM=1 Ω`回到 ground。
- `R_LOAD` 是 Q5 的原 external output load，明确保留；JTL input 是新增 load，不是替换或静默并入。
- `IB1`、RB1/RB2 和 JTL 内部 `LRB` 按标准 subcircuit 原样提供偏置 return。Q6 不向 JTL 注入新的 bias source。
- 该网表没有 floating output node、undefined DC return 或未声明的 common-mode source。代价是 Q5 output load-line确实改变；这正是本 compatibility point 要测的 coupling/back-action，而非被隐藏的 fixture修补。

## Polarity / measurement boundary

JTL cell instances和元件方向原样来自 `JTL.cir`；Q6 只把 `OUT` 放在第一 cell `a` 端，不引入 mutual coupling或额外极性翻转。所有 event claim使用 raw P、同 JJ V 和同 segment direct area；QB local activity与JTL propagated event分开判定。

## Pre-run acceptance

只有以下条件同时成立才运行：Q5 source deck hash匹配 accepted Q5；JTL hash匹配 accepted R11-A；`R_LOAD=10 Ω`在 deck中保留且仅一次；两 cell实例和 output termination各一次；`.tran 0.0125p 170p`；四 case replay source不被改写。

