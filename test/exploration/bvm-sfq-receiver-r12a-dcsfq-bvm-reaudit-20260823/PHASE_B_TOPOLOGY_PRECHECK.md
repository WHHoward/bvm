# R12-A Phase-B topology/load precheck

日期：2026-08-23
前提：Phase A 已在 300 µA controlled bump 下观察到一个 B3 differential
continuous monotonic segment（约 1 turn，且同段电压面积一致）；因此满足
进入 cascade compatibility test 的 gate。Phase-A converter topology、参数和
`jjmit` model 不变。

## Frozen topology

`circuits/interface/DCSFQ_BVM.cir` 的唯一 subcircuit 是：

```text
.subckt THmitll_DCSFQ_BVM a q
```

本阶段采用：

```text
XBVM1  WL1 BL1 SE1 SL1       BVM
XCONV  SL1  CONV_Q          THmitll_DCSFQ_BVM
XJTL1  CONV_Q JTL_MID       THmitll_JTL
XJTL2  JTL_MID JTL_OUT      THmitll_JTL
R_TERM JTL_OUT 0            1 ohm
```

没有 transformer、放大器、matching network、额外整形器或新 bias source。
两颗 JTL cell 使用 repository `circuits/standard/JTL.cir` 原样 topology 和
参数；该两-cell fixture 的 positive-control validation 已在 R11-A 通过。

## DC and transient loading

- `SL1` 是 BVM 的 canonical `SL` port。BVM 内部 `N6 → L_PSL → R_SL →
  N8 → L_SL → SL1` 保留不变；没有删除或替换 `R_SL/L_SL`。
- `THmitll_DCSFQ_BVM` 的 `a` 端经内部 `L1=1.672 pH` 接到 converter
  front node，并通过其 loop/bias network 形成真实 galvanic DC/transient
  load。它不是无负载的 waveform probe。
- converter 的 `q` 端直接作为第一颗 JTL 的 `a`；第一颗 `q` 直接作为第二颗
  JTL 的 `a`。这保留了 direct port compatibility 的因果路径。
- converter bias `IB1=100 µA`、`IB2=B3*Ic0*BiasCoef=175 µA` 是
  `DCSFQ_BVM.cir` 内部固定 PWL bias；JTL 内部 bias 也由原始 `JTL.cir`
  固定。没有外加 bias 或 DC return。
- `R_TERM=1 ohm` 仅为标准两-cell output termination；它不是 BVM source
  boundary 的替换。

因此 canonical SL 的 source guard 将与 no-receiver baseline 比较，而不会被
解释为 source-isolated measurement。若 loading 破坏 BVM read/storage，结果
按 `SOURCE_BACK_ACTION_FAILURE`，不升级为 converter 或 JTL 的 intrinsic
结论。
