# Figure 4: BQ 元件结构化描述

## 1. 图像类型

Figure 4 是一个单通道的 Buffer/Quantizer（BQ）电路结构图，输入端为 `In`，输出端为 `Out`。电路主体由一条串联主通路、两个并联到地的 Josephson junction 分支、一个偏置电阻支路，以及若干串联电感组成。该结构的作用是将输入环路中的正负磁通变化进行累积，再根据磁通变化产生量化后的 SFQ 脉冲输出。

## 2. 主要视觉元素

- 左侧是输入端 `In`。
- 从左到右依次为 `Lin`、`JS`、`L1`、`L2`、`L0`、`Out`。
- `JL1` 从 `JS` 后的节点向下接地。
- `JL2` 从 `L2` 和 `L0` 之间的节点向下接地。
- `RB` 从 `L1` 和 `L2` 之间的节点向上连接到偏置电流 `IBias`。
- 图中明确标注了元件参数：`Lin = 0.8 pH`，`L0 = 1.323 pH`，`L1 = L2 = 3.91 pH`，`JS = 133 μA`，`JL1 = 112 μA`，`JL2 = 189 μA`，`RB = 8.5 Ω`。

## 3. 可见文字与元件标注

- 输入端：`In`
- 输出端：`Out`
- 电感：`Lin`、`L1`、`L2`、`L0`
- Josephson junction：`JS`、`JL1`、`JL2`
- 电阻：`RB`
- 偏置电流：`IBias`
- 图注说明该 BQ 电路的功能类似数字 SQUID，能够根据环路磁通变化输出量化的 SFQ 脉冲。

## 4. 结构关系

- `Lin` 位于最左侧，串接在输入端与主量化支路之间。
- `JS` 位于 `Lin` 之后，是主通路上的串联约瑟夫森结。
- `JL1` 从 `JS` 后的节点分支到地，构成左侧并联泄放/量子支路。
- `L1` 和 `L2` 位于主通路中间，形成连续串联链路。
- `RB` 从 `L1` 与 `L2` 中间节点向上连接到 `IBias`，提供偏置通路。
- `JL2` 从 `L2` 与 `L0` 之间的节点分支到地，构成右侧并联支路。
- `L0` 位于主通路末端，连接到输出端 `Out`。

## 5. 元件连接关系

- 左侧输入路径为 `In -> Lin -> JS`，属于明显的串联输入链路。
- `JS` 后的节点同时向下连接 `JL1 -> GND`，说明这里存在一个从主通路分出的并联到地支路。
- `JS` 后的主路径继续向右进入 `L1`。
- `L1` 后连接到中间节点，该节点一方面继续串联到 `L2`，另一方面向上连接 `RB -> IBias`。
- `L2` 后进入右侧节点，该节点向下连接 `JL2 -> GND`，同时主路径继续经 `L0` 到 `Out`。
- 因此，BQ 的本质结构可以理解为：一条由 `Lin + JS + L1 + L2 + L0` 组成的主串联链，辅以 `JL1` 和 `JL2` 两个并联到地的非线性支路，以及 `RB` 提供的偏置支路。

## 5.1 按节点抽象的连接拓扑

为便于从图转网表，下面把 BQ 电路抽象成几个关键节点：

- `N_in`：输入节点，对应 `In`。
- `N_js_in`：`Lin` 与 `JS` 之间的内部节点。
- `N_js_out`：`JS` 后的节点，同时也是 `JL1` 的上端、`L1` 的起点。
- `N_mid`：`L1` 与 `L2` 之间的中间节点，同时是 `RB` 下端连接点。
- `N_pre_out`：`L2` 与 `L0` 之间的节点，同时也是 `JL2` 的上端。
- `N_out`：输出节点，对应 `Out`。
- `GND`：地节点。
- `IBias`：偏置电流节点，连接在 `RB` 上端。

### 5.1.1 主路径

- `N_in -> Lin -> N_js_in -> JS -> N_js_out -> L1 -> N_mid -> L2 -> N_pre_out -> L0 -> N_out`

### 5.1.2 并联支路

- `N_js_out -> JL1 -> GND`
- `N_pre_out -> JL2 -> GND`

### 5.1.3 偏置支路

- `IBias -> RB -> N_mid`

## 5.2 串并联关系总结

- 明确串联：
- `Lin`、`JS`、`L1`、`L2`、`L0` 在主通路上依次串联。
- 明确并联：
- `JL1` 从 `JS` 后节点分支到地。
- `JL2` 从 `L2` 后节点分支到地。
- 明确偏置：
- `RB` 从主链中间节点连接到 `IBias`，用于注入偏置电流。

## 5.3 适合网表化的严格行格式

格式：`ELEMENT,TYPE,NODE_A,NODE_B,PARAMS,ROLE,CONFIDENCE`

```text
Lin,L,N_in,N_js_in,L=0.8pH,input-inductor,high
JS,JJ,N_js_in,N_js_out,Ic=133uA,series-junction,high
JL1,JJ,N_js_out,GND,Ic=112uA,left-shunt-junction,high
L1,L,N_js_out,N_mid,L=3.91pH,series-inductor-1,high
L2,L,N_mid,N_pre_out,L=3.91pH,series-inductor-2,high
RB,R,N_mid,IBias,R=8.5,bias-resistor,high
JL2,JJ,N_pre_out,GND,Ic=189uA,right-shunt-junction,high
L0,L,N_pre_out,N_out,L=1.323pH,output-inductor,high
```

## 5.4 节点邻接表

```text
N_in: [Lin]
N_js_in: [Lin, JS]
N_js_out: [JS, JL1, L1]
N_mid: [L1, L2, RB]
N_pre_out: [L2, JL2, L0]
N_out: [L0]
GND: [JL1, JL2]
IBias: [RB]
```

## 5.5 主路径库

- `P_INPUT`: `In -> Lin -> JS -> L1 -> L2 -> L0 -> Out`
- `P_LEFT_SHUNT`: `JS后节点 -> JL1 -> GND`
- `P_RIGHT_SHUNT`: `L2/L0前节点 -> JL2 -> GND`
- `P_BIAS`: `IBias -> RB -> L1/L2中间节点`

## 5.6 连接判定与置信度

- 高置信：图中明确标注的元件与参数，且连线顺序清晰。
- 中置信：内部节点命名是为了网表化而引入的抽象名，但与图中连接顺序一致。
- 低置信：若你后续希望把 `In` 和 `Out` 映射到其他全局节点（例如 `N7/N8`），需要你再确认一次全局命名方式。

## 6. 适合模型理解的摘要

BQ 是一个典型的 Buffer/Quantizer 结构：输入信号先经过 `Lin` 和主串联结 `JS`，在中间通过 `L1/L2` 和偏置电阻 `RB` 形成可量化的磁通响应，两个并联到地的 Josephson junction `JL1`、`JL2` 提供分支和泄放路径，最终由 `L0` 输出到 `Out`。其核心特征是“串联主链 + 双并联结 + 偏置支路”。
