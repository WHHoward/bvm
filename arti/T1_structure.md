**T1 图像 — 结构化说明（仅结构，按图中标注逐项列出）**

来源：仓库中图片（见插图与图注），图中所有器件与数值均按图注列出。此文档只列结构（器件、连线、节点、端口），不包含工作行为或操作说明。

一、端口与显著标注
- `I`：主输入，位于图左下，箭头指向右。
- `C`：主输出，位于图右下，箭头指向右。
- `CLK`：时钟/控制线，位于图顶行左侧（标注为 `CLK`，连入顶行）。
- 顶行右侧标注为 `S`（图中箭头向右），为顶行输出/信号点（在结构上独立于 `C`）。

二、器件清单与标注值（按图注）
- 电感（Lx）：
  - L1 = 0.213 pH
  - L2 = 1.6 pH
  - L3 = 2.028 pH
  - L4 = 0.153 pH
  - L5 = 0.6 pH
  - L6 = 2.337 pH
  - L7 = 1.219 pH
  - L8 = 1.383 pH
  - L9 = 5.366 pH
  - L10 = 0.905 pH
  - L11 = 0.957 pH
  - L12 = 1.219 pH
  - L13 = 1.009 pH
  - L14 = 4.6 pH
  - L15 = 1.297 pH
  - L16 = 4.644 pH
  - L17 = 2.0 pH
- 电阻（RBx）：
  - RB1 = 6.8 Ω
  - RB2 = 6.8 Ω
  - RB3 = 16 Ω
- 约瑟夫森结（Jx，Ic 按图注）
  - J1 = 350 µA
  - J2 = 350 µA
  - J3 = 180 µA
  - J4 = 80.3 µA
  - J5 = 77.9 µA
  - J6 = 105.1 µA
  - J7 = 100 µA
  - J8 = 100 µA
  - J9 = 100 µA
  - J10 = 86.9 µA
  - J11 = 150 µA

三、总体拓扑概览（行/列分区）
- 顶行（从左到右，控制/输出线）
  - `CLK` → L4 → L5 → L6 → （连接处带 J3） → L13 → L14 → 右侧 `S` 输出方向
  - 在顶行靠近左中部有竖直的 RB2（向上标箭）连接到顶行节点（标示为一并联阻尼/偏置点）。

- 中央方框/耦合网络（位于顶行与底行之间）
  - 中央为一闭合/框架状的耦合网络：由 L8、L9、L7、L11、L12 等电感以及 J4、J5、J6 等结交织形成一个矩形耦合单元（图中为中心矩形结构）。
  - 在中央上侧顶端有 RB3（箭示向上）与 L8 相连（表示 RB3 为该节点的偏置/阻尼元件）。

- 底行（主传输链，从左 `I` 到右 `C`）：
  - `I` → L1 → （在 L1 右侧上方并连 RB1） → L2 → J1（立在上方） → L3 → L7 → L10 → L15 → L16 → L17 → `C`
  - 底行在靠近中部到右侧处串联有若干结 J6、J8、J10、J11（如图所示），并在中央处通过 L10/L11/L12 与中心耦合网络相连。

四、详细连接与节点抽象（以节点名表示，便于程序化处理）
注：下列节点名为本文所定义的抽象节点，映射到图上物理位置（左→右、上→下）以便核对。

- 节点列表（建议）
  - `NT1`..`NT6`：顶行节点自左向右分段（顶行含 `CLK` 与 `S`）。
  - `NC1`..`NC6`：中央耦合网络关键节点（对应中心矩形的角与中心节点）。
  - `NB1`..`NB8`：底行节点自左向右分段（包含 `I` 与 `C` 端）。

- 元件到节点的结构性映射（简洁版）
  - `I` -> NB1
  - L1: NB1 -> NB2
  - RB1: 并联/偏置于 NB2（图示为竖直箭头向上）
  - L2: NB2 -> NB3
  - J1: NB3 -> 顶部相邻节点（上连，图中为立式结）
  - L3: NB3 -> NB4
  - L7: NB4 -> NC4（底行连入中央网络左侧）
  - L10: NB5 -> NB6（底行中段连接）
  - J6: 底行与中央网络右侧交界处的结
  - L15: NB6 -> NB7
  - L16: NB7 -> NB8
  - L17: NB8 -> C

  - 顶行映射：
    - `CLK` -> NT1
    - L4: NT1 -> NT2
    - L5: NT2 -> NT3
    - L6: NT3 -> NT4
    - J3: NT4 -> NT5
    - L13: NT5 -> NT6
    - L14: NT6 -> S
    - RB2: 并联接在 NT2/NT3 区域（图中位于顶行左中）

  - 中央耦合网络映射（示意）：
    - L8: NC1 -> NC2
    - L9: NC2 -> NC3
    - L11: NC3 -> NC4
    - L12: NC4 -> NC1
    - L7: NB4 -> NC4
    - J4/J5/J6: 分布于 NC 节点各侧并与 L8/L9/L11/L12 的端点相连
    - RB3: 并联/偏置在 NC1（中央上侧）

五、逐支路展开（便于核对图中每条支路是否都列出）
- 顶行主支路（CLK 支路）
  - CLK -> L4 -> L5 -> L6 -> (J3) -> L13 -> L14 -> S
  - RB2 并联于顶行左中段

- 底行主支路（输入到输出）
  - I -> L1 -> (RB1 并联点) -> L2 -> (J1 立式连接到上方) -> L3 -> L7 -> L10 -> (J6/J8/J10/J11 等系列结) -> L15 -> L16 -> L17 -> C

- 中央耦合支路（连接顶行与底行）
  - 底行通过 L7/L10 与 NC 节点连接，NC 节点由 L8/L9/L11/L12 构成矩形耦合网络，网络上挂有 J4/J5/J6；网络顶部有 RB3；同时网络在图中与顶行及底行中段有明确电气连接点。

六、严格行格式（程序友好，供快速比对）
ELEMENT,TYPE,NODE_A,NODE_B,VALUE,NOTE
L1,L,NB1,NB2,0.213p,
RB1,R,NB2,NB2_up,6.8,parallel bias on left-bottom
L2,L,NB2,NB3,1.6p,
J1,JJ,NB3,NT_up,350uA,vertical junction near left
L3,L,NB3,NB4,2.028p,
L4,L,NT1,NT2,0.153p,CLK input line
L5,L,NT2,NT3,0.6p,
L6,L,NT3,NT4,2.337p,
J3,JJ,NT4,NT5,180uA,top-mid junction
L7,L,NB4,NC4,1.219p,connect to central network
L8,L,NC1,NC2,1.383p,central top-left
RB3,R,NC1,NC1_up,16,central bias/damp
L9,L,NC2,NC3,5.366p,central mid
L10,L,NB5,NB6,0.905p,bottom middle connector
J6,JJ,NB5,NC3,105.1uA,bottom-right connection
L11,L,NC3,NC4,0.957p,central right vertical
L12,L,NC4,NC1,1.219p,central bottom
L13,L,NT5,NT6,1.009p,
L14,L,NT6,S,4.6p,top-right to S
L15,L,NB6,NB7,1.297p,
L16,L,NB7,NB8,4.644p,
L17,L,NB8,C,2.0p,
RB2,R,NT2,NT2_up,6.8,parallel on top-left
J4,JJ,NC_left,NC_left_up,80.3uA,central left
J5,JJ,NC1,NC1_up,77.9uA,central top
J7,JJ,NC3,NT4,100uA,side junction (per figure)
J8,JJ,NB5,NB6,100uA,bottom-side junction
J9,JJ,NT5,NC3,100uA,top-right side junction
J10,JJ,NB6,NB7,86.9uA,bottom-right near output
J11,JJ,NB8,C,150uA,rightmost output-side junction

（注：表中 `?` 表示图中元素位置明确但在本文定义的抽象节点集合下需精确配对；如需我可将 `?` 处补齐为 `NBx/NCx/NTx` 的具体节点编号。）

七、核对清单（确保图中所有结构项已被列出）
- 顶行：`CLK`、L4、L5、L6、J3、L13、L14、`S`、RB2 — 已列出。
- 中央：L8、L9、L11、L12、J4、J5、J6、RB3 — 已列出。
- 底行：`I`、L1、L2、L3、L7、L10、L15、L16、L17、J1、J2、J6、J7、J8、J9、J10、J11、RB1 — 已列出（个别 J 的节点化可按需要补全）。

— 结束 —

文件已写入 `arti/T1_structure.md`。如需，我可以把 `?` 处精确化为具体节点编号并更新为严格的 `N1..N8` 风格映射。
