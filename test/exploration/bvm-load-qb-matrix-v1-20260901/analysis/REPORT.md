# BVM_LOAD_QB_MATRIX_V1 分析报告

## 结论边界

这是按预注册矩阵完成的 exploratory simulation。报告只描述本目录内、
当前 JoSIM 二进制、当前步长和当前模型快照下的轨迹；不把模拟结果写成硬件测量，
也不把局部 JJ 相位变化写成 SFQ 接收计数。

## Observed

- 三类 fixture 共 48 组；artifact QA 有 48/48 组通过，CSV/数值分析有 48/48 组通过。
- 所有运行的 `.tran` 请求步长为 0.0125 ps、停止时间 170.0 ps；每个 CSV 有 13599 个数据样本。打印时间轴在 48/48 组中均为 13597 个约 0.0125 ps 间隔，并在 1.8375→1.8625 ps 处保留一个 0.025 ps 间隔；因此本轮不声称输出轴严格等间隔或已完成收敛。
- 源波形到理想 QB 重放的 `I(B_LD1)`→`I(I_REPLAY)` 在 activity 窗口的最大绝对差为 0.000e+00 A；这是回放输入一致性检查，不是物理传输结论。

### 四个工作点的关键 QB 输出

下表只保留需要看的数据。`V(OUT)` 的 p2p 是固定 activity 窗口 [94,130) ps 内的峰峰值；phase turns 是同一 QB JJ 在同一窗口的连续相位端点差除以 2π。

| 读宽/负载 | 物理 read1 VOUT p2p | 物理 read0 VOUT p2p | 重放 read1 VOUT p2p | 重放 read0 VOUT p2p | 物理-重放 read1 VOUT 最大差 | QB BJL2 read1 相位差(turns) |
|---|---:|---:|---:|---:|---:|---:|
| 9 ps / 12x320 | 2.322e-04 | 7.600e-05 | 7.898e-04 | 1.083e-04 | 7.869e-04 | -1.710e-03 |
| 9 ps / 8x500 | 3.701e-04 | 9.368e-05 | 9.427e-04 | 1.545e-04 | 6.350e-04 | -1.380e-03 |
| 13 ps / 12x320 | 2.536e-04 | 6.302e-05 | 1.004e-03 | 8.717e-05 | 1.007e-03 | -4.182e-03 |
| 13 ps / 8x500 | 3.996e-04 | 7.467e-05 | 1.217e-03 | 1.157e-04 | 9.493e-04 | -7.380e-03 |

## Derived

- 每个源端和物理级联 case 都计算了首个/末个 JSL 结的 current mismatch；每个 physical/replay case 都保留了 QB 输入、`V(OUT)` 和 `I(R_LOAD)` 的窗口统计。
- phase/voltage-area 只在同一个 junction、同一窗口、同一方向的 P/V 列上交叉检查；原始相位保留为 rad，turns 由 `phase_delta_rad/(2*pi)` 得出。具体数值见 `metrics.json`。
- physical 与 ideal replay 的差异是“加载后的 BVM→JSL→QB 轨迹”与“相同源波形直接驱动 QB”之间的描述性差异；它不能单独证明差异的唯一机制。

## Inference

- 本矩阵可以回答：在这四个读宽/负载点和四种状态控制下，物理级联及理想回放是否产生可见的 QB 输入/输出轨迹差异，以及这些差异是否与 read/no-read、read1/read0 成对比较相符。
- 即使某个 BJL2 的 phase/area diagnostic 达到一个或多个 turns，也只能称为该 JJ 的局部 phase/voltage activity；本实验没有 JTL，因此不能升级为 downstream SFQ delivery 或系统 Gate。

## Unknown / limitations

- 本轮只使用 0.0125 ps 一个步长，没有做 0.025/0.0125/0.00625 ps 收敛或时间步敏感性检查。
- 没有磁耦合、JTL 或 T1；QB 是当前 scaled cell，输出负载为 OUT 到地的 10 Ω。
- 结果是数值模拟，不是硬件测量；不对未测试的参数、拓扑或工艺条件外推。

## 文件

- `manifest.yaml`：矩阵、模型、solver、窗口和 48 个 case 的登记。
- `raw/`：48 组原始 JoSIM CSV；每个 CSV 旁有 SHA-256 文件。
- `inputs/`：BVM/JSL/QB 网表快照和每组不可变输入 deck。
- `analysis/metrics.json`：逐 case QA、窗口统计、相位/面积诊断和成对比较。
- `analysis/summary.csv`：四个工作点的关键 QB 输出摘要。
- `plots/README.md`：按项目既有 classic `josim-plot2.py` 方案生成的可视化入口；
  physical case 直接读取 raw CSV，比较页使用临时 merged CSV，统一为
  `sep_comb`/dark/`-j 2pi`。

## Next

若要把某个点提升为 Candidate，应先单独预注册步长收敛和更严格的物理证据审计；本报告不自动做该提升。

分析生成时间：2026-09-01T11:22:00+08:00。
