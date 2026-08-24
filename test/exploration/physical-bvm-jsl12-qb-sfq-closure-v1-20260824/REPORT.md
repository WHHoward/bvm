# PHYSICAL_BVM_JSL12_QB_SFQ_CLOSURE_V1

## 结论摘要

本 Exploration 的物理级联已经按预注册拓扑完成 13 ps 与 14 ps 的四工况矩阵：

`canonical BVM SL → B_LD1…B_LD12（12×jjmit AREA=3.2）→ QB IN → frozen scaled QB`

13 ps 与 14 ps 的四个 matched cases 都成功生成了有效 raw。两种宽度下
`logical1_read` 的 BJL2 都只有约 `0.12 turn` 的反向 sub-turn excursion；
没有满足同一连续单调段 `≥1 turn` 且 voltage-area 一致的 BJL2 event。
logical0 与两个 READ=0 controls 也没有完整 BJL2 event，且没有发现
JSL switching/free-running。

**正式 verdict：`PHYSICAL_BACKACTION_PREVENTS_CLOSURE`。**

这不是说 BVM、JSL12 或 frozen QB 各自失效：13/14 ps ideal replay 的
`logical1_read` 仍分别为 `1.016/1.061 turn` 的 `CLEAN_ONE_SFQ_CANDIDATE`。
本次证据说明的是：把 JSL12 与 QB 做成真实串联 physical boundary 后，
source current 没有塌缩，但 source voltage/load-line 与 QB 内部 current
partition 改变，使理想 replay 中的 downstream BJL2 closure 不再保留。

## 1. Observed

- 两个宽度均完成四个角色：`logical1_read`、`logical0_read`、
  `logical1_no_read_control`、`logical0_no_read_control`。
- 12 个 JSL junction 的 series current 在每个 case 内一致；最大跨 junction
  deviation 约 `1e-9 µA`。JSL junction 未出现完整 event。
- 13 ps physical `logical1_read`：BJs 最大正向段约 `+5.951 turn`，
  BJL1 最大段约 `−0.252 turn`，BJL2 最大段约 `−0.122128 turn`，
  同段 voltage area 约 `−0.122131 Φ0`。
- 14 ps physical `logical1_read`：BJs 最大正向段约 `+8.802 turn`，
  BJL1 最大段约 `−0.252 turn`，BJL2 最大段约 `−0.121434 turn`，
  同段 voltage area 约 `−0.121438 Φ0`。
- 13 ps / 14 ps physical `logical0_read` 的 BJL2 最大段分别约
  `−0.018376/−0.017324 turn`；两个 READ=0 controls 约 `9e-6 turn`，
  均为 bounded sub-turn。
- 13 ps `logical1_read` 的 `I(L_SL)` activity p2p 为 `94.526 µA`，
  14 ps 为 `116.115 µA`；对应 source-only read1 参考的比例约为
  `1.010/1.060`，因此没有观察到 source current 的数量级 collapse。
- physical `V(SL1)` 的 p2p 相对 source-only reference 分别约为 `1.567/1.382`
  倍；这表明 loaded voltage waveform 与 source-only waveform 明显不同。
- physical BVM 的 `V(N6)`、`I(L_SL)`、`JM1/JM2`、`JS1/JS2` 均有记录；
  post-window 仍为 bounded，没有 READ=0 自发活动或 free-running。

## 2. Derived

### BJL2 phase / area 判据

| width | case | BJL2 最大单调段 | 同段 area | 分类 |
|---|---|---:|---:|---|
| 13 ps | logical1 READ | −0.122128 turn | −0.122131 Φ0 | SUBTHRESHOLD |
| 13 ps | logical0 READ | −0.018376 turn | −0.018377 Φ0 | SUBTHRESHOLD |
| 13 ps | logical1 READ=0 | +0.0000089 turn | +0.0000089 Φ0 | ZERO / bounded |
| 13 ps | logical0 READ=0 | −0.0000088 turn | −0.0000088 Φ0 | ZERO / bounded |
| 14 ps | logical1 READ | −0.121434 turn | −0.121438 Φ0 | SUBTHRESHOLD |
| 14 ps | logical0 READ | −0.017324 turn | −0.017326 Φ0 | SUBTHRESHOLD |
| 14 ps | logical1 READ=0 | +0.0000089 turn | +0.0000089 Φ0 | ZERO / bounded |
| 14 ps | logical0 READ=0 | −0.0000088 turn | −0.0000088 Φ0 | ZERO / bounded |

phase 和同一 JJ、同一 segment 的 voltage-area 符号与数值一致；但这些段
远小于 1 turn，因此不能称为 BJL2 SFQ event。BJs 的多 turn activity 也只
说明前级 junction activity，不等于 downstream SFQ delivery。

### KCL 与 current partition

分析器在 QB node2/node3/node4 上直接检查了：

```text
I(BJs) = I(L1) + I(BJL1) + I(RJ1)
I(L1) + I(RB) = I(L2)
I(L2) = I(L0) + I(BJL2) + I(RJ2)
```

最大残差约为 node2 `1.4e-5 µA`、node3 `5.0e-6 µA`、node4
`1.2e-5 µA`，即远小于 `0.02 nA`，不是 KCL 失败。

13 ps read1 在约 100 ps 的代表性瞬间，current partition 约为：

```text
I(BJs)=45.818 µA
I(L1)=8.338 µA
I(BJL1)=32.264 µA
I(RJ1)=5.216 µA
I(RB)=35.000 µA
I(L2)=43.338 µA
I(L0)=0.657 µA
I(BJL2)=41.569 µA
I(RJ2)=1.112 µA
```

这说明 physical cascade 中 BJs 的活动并没有自动全部转化为 BJL1/BJL2
的正向 quantizing drive；电流在 node2/node3/node4 的分流和动态 load-line
中重新分配。

## 3. Ideal replay 对照

上一轮 ideal replay 的同一类 source 在 13/14 ps `logical1_read` 中给出：

| width | ideal BJL2 最大段 | 同段 area | physical BJL2 最大段 | physical / ideal（绝对值） |
|---|---:|---:|---:|---:|
| 13 ps | +1.016029 turn | +1.016037 Φ0 | −0.122128 turn | 0.120 |
| 14 ps | +1.060706 turn | +1.060712 Φ0 | −0.121434 turn | 0.115 |

这里不仅是幅度下降，也发生了方向变化：ideal replay 的 BJL2 段为正向，
physical cascade 的最大段为反向。因而不能把失败简化为“输入峰值略低”；
更准确的描述是 physical JSL/QB boundary 改变了 current partition、相位
方向和 downstream load-line。

## 4. Inference

最有证据支持的机制分类是：

`PHYSICAL_BACKACTION_PREVENTS_CLOSURE`

其具体边界是：

1. **不是 source-current collapse**：`I(L_SL)` read1 activity p2p 与
   source-only reference 同量级。
2. **是 loaded source waveform / JSL-QB load-line 改变**：`V(SL1)`、
   `V(N6)` 和 JS activity 的 post/active behavior 与 source-only 不同。
3. **同时存在 QB internal transfer failure**：BJs 有强 multi-turn activity，
   但 BJL1/BJL2 未沿 ideal replay 的方向闭合；KCL 表明这来自真实网络的
   分流，而不是分析器漏电流。
4. 13→14 ps 没有恢复 BJL2，且 read0/control 仍为零，因此本轮没有理由
   继续增加 width，也没有理由把 14 ps 宣称为 physical candidate。

## 5. Unknown

- 本轮没有追加 `dt=0.00625 ps`，因为没有出现 candidate；因此没有建立
  physical candidate 的 timestep convergence。
- 本轮没有做 rewrite/read repeatability；这一步只对 candidate 开放。
- 尚未分离具体贡献来自 BVM SL termination、JSL12 distributed dynamics、
  QB `Lin` 输入阻抗还是 QB 内部 BJL1/BJL2 load-line；本报告不把其中任一项
  升格为已证实的单一根因。
- 本轮没有接 standard JTL 或 T1；不存在 downstream transport evidence。

## 6. Artifact / provenance QA

- parent HEAD：`52fdd7212e44dff1d94a6f64b21a31f9927ec4c3`
- solver：`build/josim-cli v2.7.2837d13`
- solver SHA-256：`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- baseline `dt=0.0125 ps`，stop=`170 ps`
- raw、input deck、snapshot include 均保留独立 hash；首次 include 路径错误的
  失败日志也保留，未覆盖任何 raw。
- topology precheck：`PASS`；12 个 JSL、末端接 QB IN、无 JSL GND 终端、无
  ideal replay source、单一 QB load/bias。
- phase 语义：`continuous_absolute`，纵轴为原始 `P(t)/(2π)` 连续轨迹，
  不等于 SFQ count。

## 7. Final disposition

- physical one-SFQ closure candidate：**未建立**。
- 13 ps：physical BJL2 `SUBTHRESHOLD`。
- 14 ps：physical BJL2 `SUBTHRESHOLD`。
- source/JSL guards：保持 bounded，但 loaded waveform 已发生明显变化。
- T1 acceptance：**本轮不授权**。
- 下一步若继续，必须针对 `QB source matching / physical load-line` 单独提出
  新的、可区分机制的 Exploration；不得把本轮结果包装成 BVM→QB physical
  closure，也不得自动开始 T1。
