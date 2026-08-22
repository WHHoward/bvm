# R11-A standard-JTL direct compatibility topology precheck

日期：2026-08-23  
实验级别：Exploration / architecture-control  
基线：canonical BVM，当前 HEAD `6c2530555e239552d611bf9519126e5e596b3cd6`

## 标准 JTL 端口事实

`circuits/standard/JTL.cir` 定义：

```text
.subckt THmitll_JTL a q
```

其外部端口只有 `a`（输入）和 `q`（输出）。每个 cell 内固定两颗 JJ：

```text
a -- L1 -- node 1 -- B1 -- node 2 -- LP1 -- GND
                 |                 
                 L2                
                 |                 
                 node 3 -- L3 -- node 5 -- B2 -- node 6 -- LP2 -- GND
                   |                          |
                  LB1                         L4 -- q
                   |
                  node 4 <- IB1
```

`IB1` 是 JTL 内部从地到 node 4 的固定 PWL bias，参数为 `IC=2.5`、`Ic0=100 µA`、`BiasCoef=0.7`，即 350 µA；`B1/B2` 均为 `jjmit area=2.5`，对应模型标称 `Ic=250 µA`。`RB1/RB2` 与 `LRB1/LRB2` 是标准 bias tee。R11-A 不改这些参数。

## BVM→JTL 实际连接

四个 BVM 网表均使用：

```text
XBVM1 WL1 BL1 SE1 SL1 BVM
XJTL1 SL1 JTL_MID THmitll_JTL
XJTL2 JTL_MID JTL_OUT THmitll_JTL
R_TERM JTL_OUT 0 1
```

即 canonical `SL1` 直接连接第一颗 JTL 的 `a`，第一颗 `q` 直接连接第二颗的 `a`。这是 galvanic direct screening；没有加入 transformer、串联 pickup、额外整形器或未经解释的电阻/电感。

## canonical SL source/load 语义

`circuits/bvm/bvm_cell.cir` 内部输出路径保持原样：

```text
N6 -> L_PSL(0.5 pH) -> R_SL(12 ohm) -> N8 -> L_SL(0.4 pH) -> SL
```

因此 R11-A 不替换或删除 BVM 内部的 `R_SL/L_SL`。canonical BVM subcircuit 没有一个独立、可替换的外部 SL termination；JTL chain 是新增加的实际负载。末端 `R_TERM=1 ohm` 沿用 `test/standard/test_jtl.cir`，只负责标准 chain 输出端 termination。

从 DC/KCL 角度，`SL1` 经 BVM 内部 `L_SL`（DC short）和 `R_SL` 回到 BVM R-loop 的 `N6`；同时经第一 JTL 的 `L1`（DC short）进入 JTL node 1/偏置 tee/JJ 网络。故 direct test 有真实 reflected DC/transient loading，不能把它解释成无负载的 source replay。这正是本 screening 要测的兼容性条件。

## positive-control port

positive control 使用同一两级 `THmitll_JTL` chain，并复用 `test/standard/test_jtl.cir` 的单次输入：

```text
V_IN IN 0 pwl(0 0 10p 0 11p 1.5m 13p 1.5m 14p 0 170p 0)
R_IN IN N1 3
L_IN N1 SFQ_IN 0.5p
```

它是仓库已有 standard JTL regression 的 source stimulus，不是为 R11-A 调出来的参数。R11-A 只把时间步细化为冻结的 `0.0125 ps`、仿真延长至 `170 ps`，不改 stimulus amplitude/width 或 JTL 参数。

## 结论性 precheck

direct galvanic connection 在网表拓扑上是合法且可解释的；它必然改变 SL 的边界负载，但不删除 canonical BVM 内部 termination。若 positive control 不能在同一 chain 上传播，则停止 BVM compatibility interpretation，判为 fixture/port/model issue；若 positive control 通过，BVM 四-case 结果只归因于本次 direct-loading screening，不外推为整个 direct-JTL family 的普遍结论。
