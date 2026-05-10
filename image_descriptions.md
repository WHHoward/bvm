# 三张图片的结构化文字说明

下面的内容按固定模板组织，尽量让大模型可以直接提取「图像类型、主要对象、标注文字、时序关系、信号含义、结论」这些信息。

## 图 1：BVM 单元模型与 I/O 信号示意图

### 1. 图像类型
电路结构示意图，展示一个 BVM cell model 的组成及输入输出信号连接关系。

### 2. 主要视觉元素
- 顶部有两条水平控制线：红色 SE，蓝色 WL。
- 左侧有蓝色竖向虚线标注 BL。
- 右侧有红色竖向虚线标注 SL，并在下方标有 Data Out 和向下箭头。
- 电路中心分成左右两个主要区域：左侧蓝紫色的 S-Loop，右侧红色的 R-Loop。
- S-Loop 左下方有接地符号，表示参考地。
- R-Loop 右侧继续连接黑色输出/感测网络。

### 3. 可见文字与元件标注
- S-Loop 区域内可见 J_M1、J_M2、L_M1、L_M2、L_M3、L_PM。
- R-Loop 区域内可见 L_S1、J_S1、R_S、L_S3、L_S2、J_S2。
- 右侧黑色网络可见 L_PSL、R_SL、L_SL。
- 图注为 Figure 1: BVM cell model with I/O signals.

### 4. 结构关系
- 左侧 S-Loop 通过电感和结元件与中间区域耦合。
- 中间 R-Loop 负责读出相关结构。
- 右侧 SL 端是最终数据输出路径，Data Out 从这里读出。
- 图中颜色不是装饰，而是在区分不同功能回路和信号通路。

### 5. 元件连接关系
- 左侧蓝色部分可以看成一个以 J_M1 和 L_M1 为主的竖向支路，J_M1 在上、L_M1 在下，沿同一路径连接到地端，呈现明显的串联关系。
- 左上方的 L_M2 把 BL 侧输入引到 J_M2，再连接到中间节点，表示一条从 BL 进入 S-Loop 的上方串接通路。
- S-Loop 中间节点向下还连接到 L_M3 和 L_PM 两个电感支路，这两个支路分别与上方通路相连，形成分支/并列耦合的结构，而不是单一闭环直串。
- 红色 R-Loop 内部，L_S1、J_S1、R_S、L_S3、L_S2、J_S2 分布在同一读出通路上，其中上下两条支路围绕中心节点展开，表现为多个串联元件加一个局部并行/分流的回路结构。
- 右侧黑色输出段中，L_PSL、R_SL、L_SL 沿 SL 方向顺次连接，属于典型的串联输出负载链路。
- 从整体上看，左侧 S-Loop 和右侧 R-Loop 不是简单的严格串联或并联关系，而是通过中间耦合节点和公共信号线连接起来的两个功能子回路。

### 5.1 按节点抽象的连接拓扑（基于图中几何连接）
- 可把图中连接点抽象为 5 个关键节点：
- N1：左侧 WL/BL 进入 S-Loop 的上方汇入点（靠近 L_M2、J_M2 一带）。
- N2：S-Loop 中央耦合点（靠近 L_M3、L_PM 与红色回路左侧接口处）。
- N3：R-Loop 上支路中心点（靠近 J_S1 与 R_S、L_S3 连接处）。
- N4：R-Loop 下支路中心点（靠近 J_S2 与 R_S、L_S3、L_PSL 连接处）。
- N5：右侧输出链路节点（L_PSL -> R_SL -> L_SL -> SL/Data Out）。

### 5.2 S-Loop 的支路展开
- 支路 S1（左竖支）：N1 -> J_M1 -> L_M1 -> GND，属于同一路径串联。
- 支路 S2（上横支）：BL 侧输入 -> L_M2 -> J_M2 -> N2，属于 BL 注入到 S-Loop 的串联上支路。
- 支路 S3（中下电感支）：N2 -> L_M3 ->（回到中间耦合线），是从 N2 分出的局部电感分支。
- 支路 S4（下接地支）：N2 -> L_PM -> GND，是 S-Loop 的另一条下拉支路。
- S3 与 S4 相对 S2/S1 属于“共享 N2 的并列分支”，即它们不是首尾直串，而是从同一耦合点分出。

### 5.3 R-Loop 的支路展开
- 上支路 R1：N2 -> L_S1 -> J_S1 -> N3。
- 下支路 R2：N2 -> L_S2 -> J_S2 -> N4。
- 桥接支路 R3：N3 <-> R_S <-> N4，起到上下支路之间的电阻耦合/泄放连接。
- 侧向耦合支路 R4：N3/N4 区域通过 L_S3 接到右侧输出接口前级（图中位于 R_S 右侧）。
- 因此 R-Loop 不是单纯一根串联链，而是“上支路 + 下支路 + 中间桥接（R_S）”的双支路耦合网络。

### 5.4 输出链路（SL 方向）
- 右侧黑色链路可按串联写成：N4（经耦合接口） -> L_PSL -> R_SL -> L_SL -> SL。
- Data Out 箭头与 SL 同轴向下，表示判读电流/信号在此端提取。

### 5.5 串并联关系总结
- 明确串联：
- J_M1 与 L_M1 串联。
- L_M2 与 J_M2 串联。
- L_PSL、R_SL、L_SL 串联。
- 明确并行/分支：
- 在 N2 处，S-Loop 内至少有多条分支（通向 L_M3、L_PM 及 R-Loop 接口）。
- R-Loop 的上支路（L_S1-J_S1）与下支路（L_S2-J_S2）共享左侧入口，并通过 R_S 桥接耦合，构成并行分支加桥接网络。
- 跨回路耦合：
- S-Loop 与 R-Loop 通过 N2 附近的共享连接区耦合，不是彼此独立。

### 5.6 半网表格式（基于 description.md 的干净版本）

说明：本节严格以 `description.md` 为准，用 N1..N8（+ GND）作为主体节点名，允许使用 `INT_*` 作为内部串联端点占位以清晰表达元件串接关系，但功能性判断以 N1..N8 为主。

#### 节点登记（N1..N8）
- N1：S-Loop 左上角节点；左接 BL，向上连 WL；向右连 LM2->JM2->N2；向下连 JM1->LM1->GND。
- N2：S-Loop 与 R-Loop 共享耦合节点（左中）。
- N3：R-Loop 左上/上中节点；上接 SE；左接 JS1；右直接连 N4；下通过 RS 连到 N6。
- N4：R-Loop 右上节点；左连 N3；下连 LS3->N7。
- N5：S-Loop 下侧共享节点；上接 LM3->N2；右接 LS2->JS2->N6；下接 LPM->GND。
- N6：桥网络下侧节点；上接 RS；左接 JS2；右连 N7。
- N7：桥网络右下/输出前节点；上接 LS3；左连接 N6；右接 L_PSL->R_SL->N8。
- N8：最终输出节点（SL 侧）；左接 R_SL；上接 SL；下接 L_SL->DataOut。
- GND：参考地。

#### 元件端点映射（简洁版）
JM1: N1 -> INT_N1 -> LM1 -> GND
LM2: N1 -> INT_N1B -> JM2 -> N2
LM3: N2 -> N5
LPM: N5 -> GND
LS1: N2 -> INT_JS1 -> JS1 -> N3
LS2: N5 -> INT_JS2 -> JS2 -> N6
RS: N3 -> N6
LS3: N4 -> N7
L_PSL: N7 -> INT_N5A -> R_SL -> N8
L_SL: N8 -> DataOut

#### 节点邻接表（简洁版）
N1: [BL, WL, LM2, JM2, JM1]
N2: [JM2, LM3, LS1, LS2]
N3: [SE, JS1, RS, N4]
N4: [N3, LS3, N7]
N5: [LM3, LS2, LPM]
N6: [RS, JS2, N7]
N7: [LS3, N6, L_PSL]
N8: [R_SL, SL, L_SL]
GND: [LM1, LPM]

#### 主路径库（便于理解）
P_WRITE_IN: BL -> LM2 -> JM2 -> N2
P_STORAGE_DOWN: N1 -> JM1 -> LM1 -> GND
P_COUPLE: N2 -> LM3 -> N5
P_READ_UPPER: N2 -> LS1 -> JS1 -> N3
P_READ_LOWER: N5 -> LS2 -> JS2 -> N6
P_BRIDGE: N3 -> RS -> N6
P_OUTPUT: N7 -> L_PSL -> R_SL -> N8 -> L_SL -> DataOut

#### 严格行格式（程序友好）
ELEMENT,TYPE,NODE_A,NODE_B,DOMAIN,ROLE
JM1,JJ,N1,INT_N1,S-Loop,storage-up-junction
LM1,L,INT_N1,GND,S-Loop,storage-ground-inductor
LM2,L,N1,INT_N1B,S-Loop,write-injection
JM2,JJ,INT_N1B,N2,S-Loop,entry-coupler
LM3,L,N2,N5,S-Loop/R-Loop,shared-coupling-inductor
LPM,L,N5,GND,S-Loop,pull-down-inductor
LS1,L,N2,INT_JS1,R-Loop,upper-read-inductor
JS1,JJ,INT_JS1,N3,R-Loop,upper-junction
LS2,L,N5,INT_JS2,R-Loop,lower-read-inductor
JS2,JJ,INT_JS2,N6,R-Loop,lower-junction
RS,R,N3,N6,R-Loop,bridge-resistor
LS3,L,N4,N7,R-Loop,side-coupling-inductor
L_PSL,L,N7,INT_N5A,Output,output-front-inductor
R_SL,R,INT_N5A,N8,Output,output-load-resistor
L_SL,L,N8,DataOut,Output,output-tail-inductor

#### 连接判定与置信度
- 以 description.md 为主；INT_* 仅为串联占位。
- 高置信：N2-LM3-N5、N5-LS2-JS2-N6、N7-L_PSL-R_SL-N8 等直接由描述文件给定的连接。
- 中置信：INT_* 的引入用于表达图中串联序列的内部端点。
- 低置信：未给出细粒度信息（绕线方向、互感等）不作推断。

<!-- end of cleaned 5.6 -->

### 7. 适合模型理解的摘要

- 桥接：若元件连接两条主链中间节点（例如 N3 与 N4），优先判为桥接，不判为主串联路径。
- 耦合优先级：N2 是一级耦合核心节点；N3/N4 是二级读出耦合节点；N_SL 是终端输出节点。

#### 5.6.7 不确定性标注（避免过拟合）
- 高置信：由元件符号直接连线可确定的端点关系（如 L_PSL-R_SL-L_SL 串联）。
- 中置信：由几何邻接推断的功能角色（如 L_S3 为侧向耦合路径）。
- 低置信：图中未给出显式电气方向时的端口正负定义，仅用于一致化表示，不代表真实器件极性。

### 7. 适合模型理解的摘要
这张图表达的是一个包含写入路径、存储回路、读出回路和输出端的超导单元结构。BL、WL、SE、SL 分别是不同控制/读出信号，S-Loop 与 R-Loop 是两个核心功能模块。

## 图 2：写操作 W 的仿真结果图

### 1. 图像类型
多子图时间序列图，展示 BVM cell 在写操作 W 下的动态响应。

### 2. 全局信息
- 图题说明这是 JoSIM 的仿真结果。
- 仿真频率为 50 GHz。
- 横轴为 Time (ps)，单位是皮秒。
- 该图由三层上下排列的子图组成。

### 3. 子图 1：IWL
- 纵轴为 IWL (mA)。
- 曲线是蓝色阶跃脉冲，带有明显的正负切换。
- 顶部标有 W1、W0、W1，表示不同写入控制阶段。
- 虚线竖线标出阶段边界。

### 4. 子图 2：IBL
- 纵轴为 IBL (mA)。
- 同样是蓝色脉冲波形。
- 与 IWL 一样会随写入状态改变，但脉冲分布不同。

### 5. 子图 3：内部状态与器件响应
- 蓝色曲线为 I_LM1 (mA)。
- 红色曲线为 V_JM1 (mV)，右侧有红色纵轴。
- 蓝色曲线幅度更大，存在多个脉冲和局部尖峰。
- 红色曲线围绕零附近变化，在关键时刻出现峰值。
- 图中标有 Data 0 和 Data 1，用来区分不同数据态。

### 6. 视觉上的趋势
- 写入时，控制线电流呈周期性脉冲输入。
- 内部支路电流和结电压会出现明显响应，说明写入动作会改变器件状态。
- 图的重点不是单个脉冲绝对大小，而是不同控制组合带来的响应差异。

### 7. 适合模型理解的摘要
这张图展示的是：在 50 GHz 的写入条件下，WL 和 BL 的脉冲组合会驱动器件内部产生不同的电流、电压响应，最终形成可区分的数据状态 0 和 1。

## 图 3：读操作 R 的仿真结果图

### 1. 图像类型
多子图时间序列图，展示 BVM cell 在读操作 R 下的输出响应。

### 2. 全局信息
- 图题说明读取是在不同写入状态之后进行的。
- 仿真频率为 50 GHz。
- SL 端负载被设定为 12 个 non-switching junctions，每个临界电流为 320 μA。
- 横轴为 Time (ps)，时间窗口大约是 45 ps 到 125 ps。
- 该图由四层上下排列的子图组成。

### 3. 子图 1：IWL
- 纵轴为 IWL (mA)。
- 蓝色波形为分段脉冲。
- 顶部标有 W0、R、W1、R，表示写和读交替出现。

### 4. 子图 2：IBL
- 纵轴为 IBL (mA)。
- 前段有负向脉冲，中后段出现正向脉冲，之后回到零附近。

### 5. 子图 3：ISE
- 纵轴为 ISE (mA)。
- 读操作窗口内出现明显正脉冲，说明选择线在读出阶段被激活。

### 6. 子图 4：ISL
- 纵轴为 ISL (mA)。
- 这是最关键的输出信号。
- 曲线整体在低电流水平附近波动，但在后段明显抬升，形成更高的输出脉冲。
- 图中用红色数字 0 和 1 标出不同判决状态。

### 7. 视觉上的趋势
- 读操作的核心是观察 SL 输出电流是否出现足够明显的状态差异。
- 这张图里的信息不是“内部回路变化有多复杂”，而是“读出端是否能把 0 和 1 区分开”。

### 8. 适合模型理解的摘要
这张图表达的是：在写入不同状态之后执行读操作，SL 端的电流响应会呈现状态相关差异，因此可以用来判定存储的是 0 还是 1。

## 三图合并总览

- 图 1：电路结构和信号拓扑。
- 图 2：写操作时各控制线和内部器件的动态响应。
- 图 3：读操作时 SL 输出如何区分存储状态。

## 给大模型的简化理解方式

如果要把这三张图压缩成一句话，可以理解为：
“这是一个带写入线、位线、选择线和感测线的超导存储单元模型，左图说明结构，中图说明写入时序与内部响应，右图说明读出时如何通过 SL 电流判断存储态。”

---

# JoSIM BVM 建模进展与 v5 拓扑

## 拓扑演化历史

| 版本 | S-Loop | WL/BL | LPM | R-Loop | 写操作 | 读操作 |
|------|--------|-------|-----|--------|--------|--------|
| v1 | 串联 DC-SQUID | 合并 | N2→SE | 单链 | 脉冲后归零 | — |
| v2 | 并联 DC-SQUID | 合并 | N2→SE | 单链 | 脉冲后归零 | — |
| v3 | JM1+LM1→GND, LM2→JM2→N2 | ✓ 合并 N1 | ✗ N2→SE | 单链 n_se | ✓ 锁存 | 未测试 |
| v4 | 同v3 | ✗ 分离 N1/N_BL | ✓ N2→GND | ✓ 双支路N2 | △ 100uA写0弱 | ✗ SL=0 |
| **v5** | **同v3** | **✓ 合并 N1** | **✓ N2→GND** | **✓ 双支路N2** | **✓ 锁存** | **✗ SL=0** |
| **v6** | **同v3** | **✓ 合并 N1** | **N2→LM3→N5→GND** | **8节点桥网络** | **✓ 锁存** | **△ JS有响应但SL对称** |

## v5 最终拓扑（当前）

```
WL ──RWL(20)──LPRWL(0.5p)──┐
                            ├── N1 ── JM1(120uA) ── LM1(12.5p) ── GND
BL ──RBL(20)──LPRBL(0.5p)──┘    │
                                 └── LM2(24.5p) ── JM2(140uA) ── N2
                                                                      │
                                        ┌── LM3(8.5p) ── N2A         │
                                        ├── LPM(0.5p) ── GND (环闭合) │
SE ──RSE(20)──LPRSE(0.5p)─────────────┤                               │
                                        ├── LS1(0.5p) ── JS1(74uA) ── N3 ──┐
                                        │         RS(3Ω) ∥ LS3(0.5p)        ├── N4
                                        └── LS2(0.5p) ── JS2(74uA) ── N4 ──┘
                                                                             │
                                                          LPSL(0.5p) ── RSL(12) ── LSL(0.4p) ── SL
```

**环路闭合**：N1 → JM1 → LM1 → GND → LPM → N2 → JM2 → LM2 → N1

**KCL 验证**（论文 eq.1-4）：
- N1: IM2 + IWL + IBL = IM1 ✓
- N2: IM3 = IM2 + IS1 ✓
- N3/N4: IS1 + ISE = IRS + IS3 ✓

## 论文对照

| 论文关键描述 | v5 匹配 |
|-------------|---------|
| “cumulative current from WL and BL” (p.4) | ✓ WL+BL 在 N1 汇合 |
| “total applied current surpasses JM1 IC” (p.6) | ✓ 累计电流驱动 JM1 |
| “LPM in the ground path” (p.4) | ✓ N2→GND |
| “RS in parallel with LS3” (p.7) | ✓ N3↔N4 |
| “JM2 creates DC-SQUID, non-switching” (p.6) | △ JM2 仍有开关 |
| “JS1,JS2 continuously switching” during read (p.6) | ✗ 不切换 |
| “output current on SL when stored 1” (p.6) | ✗ SL=0 |

## v5 测试结果 (150μA 写, 120μA SE 读)

```
W1后(t=45ps):    P_JM1 = 50.6 rad  ★ 锁存 “1”
Read-1(t=60ps):  I_SL  =  0.0 uA   ✗ 无输出（期望>0）
W0后(t=185ps):   P_JM1 =  0.2 rad  ★ 锁存 “0”  
Read-0(t=200ps): I_SL  =  0.0 uA   ✓ 无输出（期望=0）
W1后(t=285ps):   P_JM1 = 50.1 rad  ★ 锁存 “1”
Read-1(t=300ps): I_SL  = -0.1 uA   ✗ 无输出（期望>0）
```

**写入完全正常，状态持久锁存。读操作仍无 SL 输出。**

## 待解决

- SE=120μA 分流到 LS1/LS2 两支路各约 60μA，低于 JS1/JS2 的 IC=74μA → 结不开关 → 无输出
- 需要 S-Loop 环流对 N2 产生足够的不对称偏置，使 SE 电流集中到一支路
- 可能原因：LM3(8.5p) 或 LPM(0.5p) 与 R-Loop 的耦合方式需要调整

## v6 拓扑（基于 description.md 的 8 节点模型）

### 节点定义
- N1: WL+BL 汇入点，S-Loop 入口
- N2: S-Loop/R-Loop 耦合点
- N3: SE 入口，JS1 终端，桥网络上角
- N4: 桥网络右上角
- N5: LM3 终端，LS2 起点，LPM 下拉点
- N6: JS2 终端，RS 终端，桥网络下角
- N7: 桥网络右下角，输出起点
- N8: SL 输出节点

### 连接表（对应 description.md）

| 元件 | 节点+ | 节点- | 域 |
|------|-------|-------|-----|
| RWL+LPRWL | WL | N1 | 输入 |
| RBL+LPRBL | BL | N1 | 输入 |
| JM1 | N1 | LM1 | S-Loop |
| LM1 | JM1 | GND | S-Loop |
| LM2 | N1 | JM2 | S-Loop |
| JM2 | LM2 | N2 | S-Loop |
| LM3 | N2 | N5 | S-Loop/R-Loop 共享 |
| LPM | N5 | GND | S-Loop |
| LS1 | N2 | JS1 | R-Loop 上支路 |
| JS1 | LS1 | N3 | R-Loop 上支路 |
| RSE+LPRSE | SE | N3 | 输入 |
| (导线) | N3 | N4 | 桥网络 |
| RS | N3 | N6 | 桥网络 |
| LS3 | N4 | N7 | 桥网络 |
| LS2 | N5 | JS2 | R-Loop 下支路 |
| JS2 | LS2 | N6 | R-Loop 下支路 |
| (导线) | N6 | N7 | 桥网络 |
| LPSL | N7 | RSL | 输出 |
| RSL | LPSL | N8 | 输出 |
| LSL | N8 | SL | 输出 |

### v6 测试结果（150μA 写, 120μA SE 读）

写入与 v5 一致正常。读出时 JS1/JS2 有微小相位偏移（~1-2 rad）但未达到 2π 开关阈值，I_SL 在两种状态下对称（~0.8μA），无法区分 0/1。
