# BVM_LOAD_QB_MATRIX_V1 独立数值与反例复核

本文件是对本 Exploration 结果的独立 review，不改变 raw CSV、网表或原始
运行日志。复核脚本直接读取 `raw/`，不把 `metrics.json` 当作唯一 oracle。

## 最强有界声明

本实验只声称：在登记的 4 个读宽/负载点、4 个 matched roles、当前 scaled QB
和当前 JoSIM 配置下，可以描述 BVM→JSL→QB physical cascade 与同一源波形
ideal replay 的输入/输出轨迹差异。它不声称硬件行为、SFQ 计数、JTL delivery
或已完成 timestep convergence。

## Numerical review

| 检查 | 结果 | 证据 |
|---|---|---|
| 单位 | PASS | CSV time 按秒读取；窗口按 ps 转换；phase turns 明确使用 ΔP/(2π)；voltage area 使用实际 CSV time 的梯形积分并除以 Φ0。 |
| 符号/方向 | PASS | 复核保留带符号的 phase delta、voltage area、current difference；没有用绝对值替代方向。physical 末级 JSL 接 `IN`，source 末级接 `0`。 |
| 非均匀采样 | PASS | 积分使用每个 CSV 的实际相邻 time 差，不假定等间隔；48/48 CSV 都发现并保留同一个 0.025 ps 打印间隔。 |
| 数值健康 | PASS | 48/48 返回码为 0，stderr 为空，raw hash 匹配，时间严格递增，选定列均为有限数。 |
| 窗口 | PASS | 复核固定使用预登记的 [94,130) ps activity 窗口，没有事后移动阈值或窗口。 |
| 收敛 | UNKNOWN | 只有 0.0125 ps 请求步长；没有 0.025/0.0125/0.00625 ps ladder，因此不做收敛结论。 |

### 独立 raw cross-check

独立读取四个 logical1/read1 raw 对的关键结果如下：

| 工作点 | source→replay 输入最大差 | physical→replay 输入最大差 | physical VOUT p2p | replay VOUT p2p | physical/replay BJL2 phase delta (turns) |
|---|---:|---:|---:|---:|---:|
| 9 ps / 12x320 | 0 | 4.054e-05 A | 2.322e-04 V | 7.898e-04 V | -1.710e-03 / 1.002 |
| 9 ps / 8x500 | 0 | 7.797e-05 A | 3.701e-04 V | 9.427e-04 V | -1.380e-03 / 9.954e-01 |
| 13 ps / 12x320 | 0 | 8.459e-05 A | 2.536e-04 V | 1.004e-03 V | -4.182e-03 / 1.002 |
| 13 ps / 8x500 | 0 | 7.797e-05 A | 3.996e-04 V | 1.217e-03 V | -7.380e-03 / 9.976e-01 |

四个点的 BJL2 phase delta 与同一 JJ、同一窗口的 voltage-area turns 复核残差
分别为 physical `5.605e-7`、`4.779e-7`、`1.011e-6`、`2.739e-6` turns；replay
分别为 `-6.377e-7`、`1.462e-6`、`-6.225e-7`、`8.071e-7` turns。这个一致性
只支持局部 P/V 诊断，不把约一 turn 直接命名为 SFQ event。

## Adversarial review

| 隐藏错误假设 | 探针 | 结果 |
|---|---|---|
| 回放没有真正使用源波形 | 逐 raw 读取 `I(B_LD1)` 与 `I(I_REPLAY)` | 16/16 matched source/replay 对在 activity 窗口最大差为 0 A；回放 deck 注明无 reshape/hold/scale/resample。 |
| physical 实际走了旁路或错误端点 | 检查 32 个 source/physical deck 的末级 `B_LD`、`XBQ`、`R_LOAD`；检查 K 行 | 0 个 `K` 行；source 末级全接 ground；physical 末级全接 QB `IN`；physical 全含 `R_LOAD OUT 0 10`。 |
| read/no-read 分支颠倒 | 独立检查 WL/SE PWL 行 | 读 case 全部含同一正 `WL+SE` READ；no-read case 的 READ 线为零；未发现 protocol mismatch。 |
| 输出是恒定值或只由初始化决定 | 比较 read1、read0 和两个 no-read control 的 `V(OUT)` activity p2p | physical 与 replay 的 read1/read0/no-read 数值均不恒定；no-read 控制保持在约 1e-8–1e-7 V 级，而 read1/read0 read case 明显不同。 |
| 旧 raw 或缓存被误用 | 检查每个 raw 旁的 SHA-256、execution log 和当前 manifest 路径 | 48/48 raw hash 匹配对应运行记录；所有 case 路径属于本目录。 |
| 局部相位被过度命名为下游事件 | 检查报告、metadata 与 phase/area 标签 | 已标为 local phase/voltage activity diagnostic；本实验无 JTL，不发布 downstream SFQ 或 Gate 结论。 |

## Residual uncertainty

- 输出时间轴的单个 0.025 ps gap 是 JoSIM 打印索引层的可重复现象；本轮没有重建
  更细的输出轴，也没有把它解释成 solver adaptive convergence。
- physical 与 replay 的输入并不相同；差异本身是加载后轨迹的观察量，不能单独
  归因于某个内部器件或机制。
- 没有独立的 hardware measurement、JTL 级接收探针或 timestep ladder。

复核结论：`REVIEW_PASS_WITH_BOUNDED_EXPLORATORY_SCOPE`。
