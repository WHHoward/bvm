# QB load-boundary matrix topology precheck

## Common QB output boundary

每个 Q0/Q5 deck 保留原始：

```text
XBQ IN OUT IBIAS BQ
```

OPEN fixture 只删除原始 `R_LOAD OUT 0 10`；没有新增 load。

JTL-only fixture 使用：

```text
XJTL1 OUT      JTL_MID THmitll_JTL
XJTL2 JTL_MID  JTL_OUT THmitll_JTL
R_TERM JTL_OUT 0 1
```

并删除原始 10Ω。parallel fixture 在该连接之外保留原始 `R_LOAD OUT 0 10`。

## KCL / DC paths

- `OUT` 是 QB `L0`、可选 `R_LOAD` 和可选 `XJTL1.a` 的公共 node；没有假定 `L0` current 自动等于 JTL input current。
- JTL `a` 直接进入标准 cell 的内部 `L1`，由 standard JTL 内部 JJ、bias tee、电感和 ground branches 提供 DC/transient return。
- JTL `q` 连接下一 cell 的 `a`；最后 `q` 通过 frozen `R_TERM=1Ω` 回 ground。
- OPEN 没有额外 output return；Q0/Q5 的 BJL2/RJ2/L0 network仍是原 cell 的唯一 output-side path。
- 没有 floating JTL output、undefined DC return、额外 common-mode source 或未经解释的 matching branch。

## Independent build rule

`analysis/build_matrix.py` 从 accepted Q0 deck 或 accepted Q5 deck读入原文，在本 fixture自己的目录写出独立 deck。Q0 A/B/C 不互相复制；Q5 D/E 不互相复制；每个生成 deck 均检查 source prefix、R_LOAD 次数、JTL instance 次数、`.tran` 和原始 replay/pulse文本。

## Frozen provenance

- standard JTL：`circuits/standard/JTL.cir`，沿用 accepted R11-A hash；
- Q0 model/cell：accepted QB-Q0 input snapshots；
- Q5 model/cell/replay：accepted PAPER-SL-Q5 input snapshots；
- no canonical BVM, physical 12-JSL, transformer, DCSFQ or T1 is connected。

