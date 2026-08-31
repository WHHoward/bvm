# BVM + 12-JJ load topology

这是当前第一版的 draw.io 可编辑拓扑图，放在用户指定的 `circuits/toplogy/`
目录中。图的结构来源于实际的 physical BVM→12×JSL→QB representative deck，
不是根据论文图片猜出的连接关系。

## 文件

- `bvm-jsl12-topology.drawio`：draw.io 原生可编辑文件，包含三个页面：
  `Overview`、`BVM internal`、`12JJ load boundary`。
- `bvm-jsl12-topology.json`：器件、端点、来源和展示边界的机器可读映射。

## 来源

- representative deck：
  `test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/inputs/13/logical1_read.cir`
- representative deck SHA-256：
  `1a07bdb7690a5deb046ab95e6246c3a88978a99f25cf66c7373ebf3566115b0b`
- BVM canonical subcircuit：`circuits/bvm/bvm_cell.cir`
- BVM subcircuit SHA-256：
  `ea7346546bef091dc2efa39ab6f0abcfa54f833aeeabb909dcf3815cdaea42a4`
- JJ model：`test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/inputs/jjmit.cir`
- JJ model SHA-256：
  `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`
- source Git HEAD：`1a56b956264520553029284f6b50c08da85b3076`
- 生成时间：`2026-08-31T17:54:00+08:00`

代表 deck 的连接边界为：

```text
XBVM1(WL1, BL1, SE1, SL1)
  → B_LD1 → B_LD2 → ... → B_LD12
  → XBQ(IN, OUT, IBIAS)
  → R_LOAD(OUT, 0)
```

`B_LD1` 到 `B_LD12` 是 12 个串联的 `jjmit area=3.2` Josephson junction，
其中 `B_LD12` 的第二端接 QB 的 `IN`，没有额外接地终端。选定网表中没有
`K` 互感元件，因此本图不添加 magnetic coupling。

## 页面说明

1. `Overview`：只保留 BVM、12-JJ 负载、QB 和输出负载等关键结构，并显示
   `WL1`、`BL1`、`SE1` 和 `IBIAS` 控制端口。
2. `BVM internal`：展开 `circuits/bvm/bvm_cell.cir` 中的 22 个实际元件，
   包括 S-loop、R-loop、WL/BL/SE 输入和 SL 输出链。
3. `12JJ load boundary`：展开 `B_LD1`…`B_LD12` 的每个端点和器件参数。

详细 `.print` 探针、完整 PWL 时间点和 QB 内部元件没有塞进第一张主拓扑图；
它们仍保留在来源 deck 中。图中“关键测量点”只表示探针位置，不把局部相位
活动直接标成下游 SFQ 成功接收。

## 使用和边界

用 [app.diagrams.net](https://app.diagrams.net/) 打开
`bvm-jsl12-topology.drawio`。这是结构展示图，不是新的模拟输入，也不是
physical Gate 或论文结论。任何端点、参数或负载变更都应先修改/确认来源
`.cir`，再更新图和 JSON 映射。
