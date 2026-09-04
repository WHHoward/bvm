# Numerical / adversarial review

## Scope

这是对本轮 common-SL topology Quick 的 artifact、数值和解释边界审查，不是
独立物理 Gate，也不把结果升级为论文结论。审查对象是十个独立 raw、生成
deck、`analysis/analyze.py`、`analysis/independent_check.py` 和经典 renderer。

## Numerical review

- 十个 raw 均 exit code `0`，无 `Missing model` / `Using default model`；每个
  1549 个样本，存储区间 `45.0--199.9 ps`。实际存储网格在所有 mask 间逐点
  相同，`dt_min≈0.1 ps`、`dt_max≈0.2 ps`；分析没有插值，也没有把名义步长
  当作实际每一相邻输出点都严格相等。
- `bvmtools.raw` 报告十个 raw 都无 duplicate column；直接 shared-load
  authority 使用 `I(B_COL_LOAD01)`，不是把四路输出求和后冒充实测 branch。
- common-column KCL 使用 `scripts/bvmtools/kcl.py`，方向为每条 branch 的
  第一个 netlist node 到第二个 node。四路 `I(L_SL)` 的和减去
  `I(B_COL_LOAD01)` 的 READ 最大残差约为 `6.0e-5 uA`；所有 BVM/KCL 方程中
  的最大 READ 残差约为 `1.0e-4 uA`。这些数值只用于连接/方向 sanity check。
- 共享栈十二个 JJ 的系列电流逐点一致到记录精度；`1111` READ 中
  `I(B_COL_LOAD01)` 最大绝对值为 `243.338 uA`，低于声明的 `500 uA`。严格
  local phase/voltage diagnostic 没有发现 complete segment；这只是
  non-switching assumption 的本 fixture 诊断，不是硬件裕量结论。
- 所有 phase 结果保持 raw `P` 为 rad；图和派生差分只在明确使用
  `continuous_unwrap(rad)/(2*pi)` 时显示 turns。没有使用 phase displacement、
  voltage area、`I>Ic` 或 peak 作为 SFQ count。

## Adversarial checks

- **Wrong-fixture check:** static preflight 检查每个 deck 的 BVM include/hash、
  `COMMON_SL` 端点和禁止 token；十个 mask 均通过。没有外部重复 RSL、没有
  `B_LD*`/per-cell load、没有 daisy segment、没有 QB/JTL/termination。
- **Weak-oracle check:** one-hot position identity 只作为观察结果；四个位置的
  common current waveform 逐点相同，并不被解释成“电路已经正确”，而是符合
  本轮位置对称拓扑的结果。独立复算没有从 `metrics.json` 读取主结论。
- **Hidden-back-action check:** inactive BVM 使用同一 stored-1111 的 `0000`
  run 作 baseline，并逐支路检查 RSL、LSL、RS、LS3、JS1/JS2 phase 和 LM3；
  未把 inactive branch 静默归零。
- **Authority check:** `I(B_COL_LOAD01)` 与 `SUM_BVM_OUTPUT` 分开保存并用
  KCL 对照；superposition 的 prediction 只来自 one-hot delta，不能替代
  direct branch。
- **Stale-artifact check:** raw、deck、log、metadata 分 mask 独立保存；run
  script 拒绝覆盖已有 raw/log/metadata，plot manifest 记录输入和输出 hash。
- **Interpretation check:** old distributed fixture 只读作 bounded context；它
  没有本轮 direct common-load authority，因此没有被写成同一测量量的等价对照。

## Disposition

`ANALYSIS_VALID`，`BOUNDED_DESCRIPTIVE_ONLY`。

当前数据支持报告 common-SL topology 下的 symmetric one-hot response、明显的
inactive back-action 和 multi-active 非加性残差；不支持把它们自动升级为独立
unit-current、RSL isolation 或论文机制证明。human gate 保持：

```yaml
state: AWAITING_USER_REVIEW
user_reviewed: false
next_step_authorized: false
automatic_next_experiment: false
next_action: STOP
```
