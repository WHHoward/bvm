# Adversarial / numerical review

## 审阅范围

本审阅只检查本轮十个独立 run 的 deck、raw、metadata、分析脚本、独立复算和可视化索引；没有重新运行物理仿真，也没有修改任何 raw CSV。审阅对象是当前 historical BVMSim JM2-connected fixture，不是 canonical BVM，也不是硬件或论文机制的最终验证。

## Artifact 与数值有效性

- 十个 mask（`0000, 0001, 0010, 0100, 1000, 0011, 0111, 1100, 1110, 1111`）均有独立 deck/raw/log/metadata，JoSIM exit code 均为 0；没有 `Missing model:` 或 `Using default model` 警告。
- 每个 raw 为 1549 个样本，数组 run 的时间网格与 `0000` 精确相同；差分和 one-hot 叠加均未插值。
- `P(...)` 按 JoSIM 原始 rad 处理；只有 `continuous_unwrap(rad)/(2*pi)` 的派生字段标为 turns。turns 没有被用作 SFQ 计数。
- 共享 KCL 检查的 READ residual 约为 `1e-5 uA` 量级，严格串联的两组 SL residual 为 0；这支持方向约定和支路算术自洽，但不证明物理独立性。
- 独立复算没有导入主分析器或 `metrics.json`，结果为 `PASS`；测试套件为 `48 passed`。

## 三组核心证据

### 1. Active BVM vs isolated single

这组比较按 READ onset 的相对采样索引配对，不插值；但 array 与 previous single 的绝对 stimulus schedule 不相同，因此只能作为 bounded context，不能当作同协议等价性证明。主要差异为：

- `I(LIN|XBQ1)` max-abs 差异：`40.62--46.93 uA`；
- `V(QBIN)` max-abs 差异：`0.427--0.464 mV`；
- active `RSL/LSL` max-abs 差异：`25.21--49.99 uA`；
- 四个 one-hot 位置的 active response 也明显不同，说明 unit response 具有位置依赖性。

因此不能把 array 中的一个 active BVM 简化为已经被 isolated single reference 完全替代的 unit source。

### 2. Inactive BVM vs 0000

四个 one-hot run 中共 12 个 commanded-0 victim 都相对同位置 `0000` 产生非零 READ-associated 变化：

- victim `RSL/LSL` max-abs：`7.046--26.454 uA`；
- `RS`：`0.837--5.837 uA`；`LS3`：`2.126--14.324 uA`；`LM3`：`1.824--12.362 uA`；
- victim `JM1/JM2` phase 差异达到约 `0.0058--0.0610 turns` 的量级。

这说明在当前 fixture 中，active BVM 的 READ response 会让其他 commanded-0 BVM 偏离 `0000`，影响不止停留在 SL 末端观测，也可见于 R-loop 和 LM3/S-loop interface 的直接 branch probes。这里的结论是观察到 cross-coupling/back-action，不是把它归因到某一个唯一物理路径。

关键反证检查：all-one WRITE1 并没有让四个 BVM 的 stored-1111 closure 都达到描述性标准。JM1 WRITE1 约 `2.008 turns`，但 JM2 约 `0.124 turns`，低于本轮 `0.25-turn` marker。因此这些 victim 差异不能无条件称为“完整存储态隔离失败”；它们是当前协议和当前实际内部状态下的 bounded observation。

### 3. Multi-active actual vs one-hot superposition

使用 `Delta_X(mask)=X(mask)-X(0000)` 和 one-hot delta 的逐样本叠加预测，实际减预测的残差没有预设宽松阈值：

- `I(LIN|XBQ1)` residual max-abs 为 `41.25--205.38 uA`，normalized RMS 为 `0.414--1.101`；
- 四路 LSL residual 的每次 multi-active run 最大值约为 `35.9--91.3 uA`；
- `V(QBIN)` residual max-abs 为 `0.370--1.475 mV`，normalized RMS 为 `0.894--1.000`。

这些是波形尺度的非线性/非可叠加差异，不支持把本 fixture 的多 active response 解释为 one-hot unit current 的近似线性累加。正反向组合还不完全对称；这应作为观察记录，不应直接升级为根因结论。

## 次级 QB/JTL 检查的限制

`1111` 中 QB `BJ2` 的累计 phase delta 约 `4.999 turns`，但最大连续 segment 约 `4.034 turns`，clean separated event count 为 0，并被标为 continuous-running；JTL6 `B02` 的局部诊断为约 5 个 clean segments。两者不能互相替代，也不能从这些 turns 或 local segment 数推出 QB 收到了 5 个 SFQ。该结果进一步说明最终 QB 响应数量不是本轮主判据。

## 有界科学结论

在固定 historical 模型、固定 bias、固定 0.1 ps timestep、固定六级 JTL 和固定共享 RSL/SL 拓扑下，论文式“每颗 BVM 提供相对独立 unit current，经 RSL 隔离后在 SL 上近似线性累加”的假设，**在本 fixture 中未获支持**。更准确的描述是：观察到位置依赖、inactive-victim cross-coupling/back-action 和 multi-active non-additivity；all-one stored-state closure 不完整，具体耦合路径仍为 Unknown。

这不是对所有 BVM 设计、所有 bias/timestep、所有读取协议或论文机制的普适否定。也不证明 canonical BVM、工艺容差、硬件行为、QB 逻辑正确性或后续 route choice。

## Gate

`analysis_status: ANALYSIS_VALID` 只表示 artifact 和分析链有效；它不是物理 PASS。human gate 保持：

```yaml
state: AWAITING_USER_REVIEW
user_reviewed: false
next_step_authorized: false
automatic_next_experiment: false
next_action: STOP
```
