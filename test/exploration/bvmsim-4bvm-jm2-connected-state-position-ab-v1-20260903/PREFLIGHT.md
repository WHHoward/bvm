# JM2-connected 4-BVM six-state A/B Quick：预注册与 preflight

本目录是一个独立的 task-local `HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT`
探索实验。A 侧使用已存在的 `bvmsim-4bvm-state-position-closure-v1-20260903`
不可变 raw；B 侧只把四个 BVM 的 include 替换为已经审阅过的
`bvm_jm2_connected.cir`，其余历史 fixture 保持不变。

## 科学问题

本轮优先回答：当只有一个 BVM 被写成 active-1 时，其他 stored-0 BVM 的
READ 响应是否仍被拉离 `0000`；这种 zero-cell response 在 JM2 omitted 与
JM2 connected 之间是变弱、变强、相近、变号还是只改变时间结构。这个问题与
`I(LIN|XBQ1)` 的位置依赖并列，不能用最终 QB 的状态序列代替。

`0000` 是每一侧自己的同 fixture baseline。对每个 one-hot state 和每个零
BVM，分析

```text
Delta I_LSL,n(t) = I(L_SL|XBVMn, one_hot) - I(L_SL|XBVMn, 0000)
Delta V_SL,n(t)  = V(SLn, one_hot) - V(SLn, 0000)
```

只在相同一侧、相同 raw 采样网格上相减。active cell 的响应另行报告，不能
和 zero-cell response 混在一起。原始差分保留为 state-conditioned difference；
为了避免把 WRITE1 后残留的状态偏移误写成 READ 因果响应，同时报告

```text
r[T,s,n](t) = X[T,s,n](t) - median_PRE_READ1(X[T,s,n])
delta[T,s,n](t) = r[T,s,n](t) - r[T,0000,n](t)
```

这里的 `READ0` 是 WRITE1 发生前的负控制窗口。没有 READ=0 对照，所以
centered difference 仍称 READ-associated/state-conditioned evidence，不升级
为唯一因果证明。每个 A/B delta 都要求 one-hot、0000 两侧共四条轨迹的时间
token 完全相同；不满足时只报告各自标量，禁止逐点 A/B delta 和插值。

## 物理边界

- BVM 来源仍是历史 `BVMSim/bvm_cell.cir` 的单一已批准 JM2-connected
  变体；这不是 canonical BVM，也不是新的固定设计。
- QB 使用原始 `BVMSim/BQ.cir`：`RJ1=12 ohm`、`RJ2=4 ohm`、bias=250 uA。
- 保持历史四段 12-JJ sensing line、六级 JTL、280-uA JTL bias、10-ohm
  终端、历史 stimulus、`.tran 0.1p 200p 45p` 和 A 侧的输出起点。
- 只运行六个状态：`0000`、四个 one-hot、`1111`。不做 sweep、优化、
  canonical BVM、single-BVM、T1 或自动 follow-up。

## 静态检查与不可变性

在第一次 JoSIM 调用前，`analysis/static_preflight.py` 检查：

1. 六个 deck 直接位于 `runs/<state>/deck.cir`，没有 `inputs/*.cir` 中间层；
2. BVM variant 的 SHA-256 和单一允许的 `L_M2 2 -> 3` 差异；
3. A/B deck 归一化后只有 BVM include 和探针包装差异；
4. QB、JTL、sensing、stimulus、load、timestep 和模型闭合；
5. 所有 required P/V/I 探针存在，且运行输出路径尚不存在；
6. 运行前工作树干净。

`stored-0` 这个词只在 `PRE_READ1` 到 `TAIL` 的 task-local 保持性观察支持时
使用；否则报告为 `commanded-0`，不强迫 connected variant 复现 omitted 侧的
状态判据。

每个 state 单独保存 `deck.cir`、`raw.csv`、`run.log`、`metadata.json`；创建
后拒绝覆盖。历史 A raw 和 deck 不修改。

## 单位与解释

JoSIM 的 `P(...)` 是弧度。图和 derived metrics 中的 turns 只来自
`continuous_unwrap(rad)/(2*pi)`。phase displacement、voltage-area、局部
phase activity 和下游 JTL 响应分开记录；任何一个都不会单独被命名为 SFQ
计数。

## 人工门

本实验结束后 gate 固定为 `AWAITING_USER_REVIEW`，`user_reviewed=false`、
`next_step_authorized=false`、`automatic_next_experiment=false`、
`next_action=STOP`。用户对上一轮 single-BVM 的审阅授权不会自动授权下一轮。
