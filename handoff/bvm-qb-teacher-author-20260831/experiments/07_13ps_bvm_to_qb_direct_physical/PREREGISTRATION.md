# PHYSICAL_BVM_JSL12_QB_SFQ_CLOSURE_V1

## 状态与边界

- tier：`Exploration`
- parent HEAD：`52fdd7212e44dff1d94a6f64b21a31f9927ec4c3`
- canonical BVM：`circuits/bvm/bvm_cell.cir`，本轮不修改
- solver：`build/josim-cli`，v`2.7.2837d13`
- baseline timestep：`dt=0.0125 ps`
- stop time：`170 ps`
- 本轮不接 standard JTL/T1，不优化 QB，不扫描 JSL 数量/AREA/宽度/参数。

## Scientific question

真实电气级联

```text
canonical BVM SL → 12 × series JSL (AREA=3.2) → frozen scaled QB → BJL2
```

是否仍能保留上一轮 canonical ideal-current replay 的 `read1=1 / read0=0 /
no-read=0` 选择性本地事件候选？重点区分 physical QB loading、JSL load-line
变化与 BVM source back-action。

## Frozen topology

每个 JSL 元件为 `jjmit AREA=3.2`，从 `SL1` 串到 `IN`：

```text
SL1--B_LD1--B_LD2--...--B_LD12--IN--QB.Lin--QB
```

`B_LD12` 的末端 `IN` 是 QB 的真实输入；没有 JSL 到 GND 的并行/终端支路，
没有 ideal replay source。QB 使用冻结 scaled-Q0 cell：

```text
BJs=.50, BJL1=.36, BJL2=.54
Lin=.8 pH, L0=1.323 pH, L1=L2=3.91 pH
RJ1=33 Ω, RJ2=22 Ω, RB=6 Ω, IBIAS=35 µA, R_LOAD=10 Ω
```

## Cases

每个宽度只注册四个 matched roles：

| role | initialization | READ | width |
|---|---|---|---|
| `logical1_read` | WL=BL=+100 µA | WL=SE=+100 µA | 13 ps primary；14 ps backup |
| `logical0_read` | WL=BL=-100 µA | 同一正 WL+SE READ | 13 ps primary；14 ps backup |
| `logical1_no_read_control` | WL=BL=+100 µA | 无 READ | 同上 |
| `logical0_no_read_control` | WL=BL=-100 µA | 无 READ | 同上 |

先执行 13 ps。若 13 ps 是 `1/0/0` subthreshold 且 source/JSL 没有明显
collapse，才执行已注册的 14 ps backup；若 13 ps 达到 candidate，停止，不运行
14 ps。不得运行 15 ps。

## Event contract

所有 BJL2 event claim 必须同时满足：

1. 同一 BJL2 的 continuous unwrapped phase；
2. 一个 continuous monotonic segment，`|Δφ|/(2π) >= 1`；
3. 同一 JJ、同一 segment、同一端点方向的 `∫Vdt/Φ0` 与 phase 一致，残差
   `<= max(0.05 turn, 10% × |Δturn|)`；
4. event 后 bounded/retrap，无第二个完整 segment。

为区分理想 13/14 ps 候选与 15 ps overdrive，预先登记工程分类带：
`0.95 <= |Δturn| <= 1.15` 且满足上述双证据时记作
`CLEAN_ONE_SFQ_CANDIDATE`；低于 1 为 `SUBTHRESHOLD`，高于 1.15 或出现
额外完整段为 `OVERDRIVEN_ONE_PLUS_RESIDUAL`/`MULTI_EVENT`。这只是本
Exploration 的分类带，不是全局 JJ 或硬件阈值。

## Measurements

- BVM：`P/V(JM1,JM2,JS1,JS2)`, `I(L_PSL)`, `I(L_SL)`, `V(SL1)`, `V(N6)`。
- JSL：12 个 `P/V/I(B_LDk)`，`I(B_LD1)`, `I(B_LD12)`，用于 series KCL、
  switching/load-line 与首个明显响应判断。
- QB：`P/V/I(BJs,BJL1,BJL2)`, `V(IN)`, `V(OUT)`, `I(Lin,L0,L1,L2,RB,RJ1,RJ2)`,
  `I(R_LOAD)`, `I(I_IBIAS)`。

phase plots 统一声明 `phase_semantics=continuous_absolute`，纵轴为原始
JoSIM `P/(2π)` 连续相位（turn），不等于 SFQ count。

## Predeclared decisions

- 13 ps `1/0/0` + BVM/JSL guards：`PHYSICAL_BVM_JSL12_QB_SELECTIVE_ONE_SFQ_CANDIDATE`；
- 13 ps subthreshold、source 保持，14 ps `1/0/0`：同一 candidate，但工作点为 14 ps；
- 13/14 均 subthreshold 且相对 ideal replay BJL2 下降：`PHYSICAL_BACKACTION_PREVENTS_CLOSURE`；
- BVM/JSL waveform collapse：`SOURCE_INTERFACE_BACKACTION`；
- source 保持而 QB 内部未闭合：`QB_SOURCE_MATCHING_REQUIRED`；
- 13 ps overdrive/multifire：`PHYSICAL_OVERDRIVE`，不在本轮修正。

首个 candidate 之后才允许追加 `dt=0.00625 ps`；若至少两个 timestep 的
classification 不一致，改为 `PHYSICAL_CANDIDATE_NUMERICALLY_UNSTABLE`。若
timestep 稳定，才追加一次 `write/read → rewrite → read`，不得自动展开为
参数扫描。

## Provenance

输入源波形复用上一轮已接受的 canonical PWL 语义，但本轮 `.cir` 重新建立
真实 BVM/JSL/QB 级联。上一轮 ideal replay 只作为后验 comparison reference，
不能作为本轮 physical primary evidence。该文档不是 scientific verdict。
