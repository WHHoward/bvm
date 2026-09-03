# RESULT BRIEF — JM2-connected 4-BVM 六状态 A/B Quick

## 1. 本轮内容

完成 task-local JM2-connected 四 BVM 六状态 A/B Quick。B 侧仅使用已审阅
`bvm_jm2_connected.cir` variant；A 侧使用既有 omitted endpoint raw。

## 2. 最重要的结果

- 六个 connected raw 的 artifact QA 为 `ARTIFACT_VALID`，且这不是物理 PASS。
- connected one-hot 的 READ1 `I(LIN|XBQ1)` raw 峰值 spread 为 131.8 uA（60.69–192.5 uA）；`V(QBIN)` spread 为 0.5497 mV。
- 12 个 one-hot→commanded-0 pair 中，connected state-conditioned READ1 Delta I 的 12 个超过 1 uA 描述性 floor；这 12 个 victim 的 PRE_READ1→TAIL retention 均稳定，故本轮可称为 task-local retention-stable；最大 Delta I 为 93.3 uA（1000/BVM2）。
- 同一批 pair 的 connected state-conditioned READ1 Delta V_SL max_abs 为 0.5525–2.816 mV；最大值 2.816 mV（0001/BVM1）。
- 12 个 Delta I 的 JM2 connected-vs-omitted `max_abs` 关系为 SIMILAR=4, SMALLER_CONNECTED=4, LARGER_CONNECTED=4；12 个 Delta V_SL 的关系为 SIMILAR=8, SMALLER_CONNECTED=0, LARGER_CONNECTED=4。两者都只是此 fixture 的描述，方向没有预先假定。
- BJ2 READ1 clean-separated event count 为 {'0000': 0, '1000': 0, '0100': 0, '0010': 0, '0001': 0, '1111': 0}，六状态均为 0；strict local diagnostic 的 continuous multi-turn running 出现在 1000, 0010, 0001, 1111，因此不能把 BJ2 的累计 turns 当作 SFQ 事件数。

## 3. 物理含义

每个 one-hot/zero-cell pair 的 raw delta、PRE_READ1-centered delta 和
omitted-vs-connected 比较已经单独保存。因此可以讨论 shared sensing network
中的 state-conditioned cross-coupling，但不能把非零 delta 当作唯一 READ 因果、
SFQ 接收计数或论文机制证明。

## 4. 不证明什么

不证明 canonical/single-BVM 兼容性、SFQ 一一对应、timestep 收敛、工艺裕度、
T1、paper-level claim 或任何 Gate。

## 5. 当前状态

`NO_CLEAR_STRICT_CLASSIFICATION` / `QUICK_AMBIGUOUS`；等待用户审阅，停止。

## 6. 后续选项（不执行）

1. 用户检查 six-state standalone plots、三个 focused comparison plots 与 REPORT。
2. 若需要，另行授权更细的 zero-cell coupling 时间窗诊断。
3. 若需要，另行授权 canonical BVM 对照；本轮没有创建或运行。
