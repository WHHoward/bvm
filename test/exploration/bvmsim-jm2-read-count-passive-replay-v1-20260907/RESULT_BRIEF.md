# RESULT_BRIEF — N1–N4 passive read-count / exact-current replay

本轮只新增 6 个 JoSIM solve：`N2_PASSIVE`、`N3_PASSIVE`、`N4_PASSIVE` 及对应 3 个 replay。`N1_PASSIVE`/`N1_REPLAY` 直接复用既有 baseline 的 hash-bound raw，没有重跑。solver 是记录的 `build/josim-cli` `v2.7.2837d13`；8 个 raw 均为 1999 点，未覆盖历史 raw。

`P(...)` 原始单位是 rad；下文的 turns 只表示 `continuous_unwrap(rad)/(2*pi)`，不是 SFQ 计数。积分均使用 raw 中实际时间列的梯形积分。

## 七个问题

### 1. 从 N=1 到 N=4，passive JSL8 waveform 怎样变化？

**Observed / Derived:** final READ mask 为 N1=`1000`、N2=`1100`、N3=`1110`、N4=`1111`。`I(B_JSL8)` 的完整指标如下；电流为 uA，面积为 uA·ps。

| N | FINAL_READ min / peak | RMS | p2p | signed / positive / negative area | endpoint |
|---:|---:|---:|---:|---:|---:|
| 1 | -2.649 / 68.414 | 39.683 | 71.063 | 401.198 / 401.331 / -0.132 | 26.535 |
| 2 | -4.563 / 141.484 | 83.676 | 146.047 | 847.992 / 848.220 / -0.228 | 75.762 |
| 3 | -4.563 / 212.326 | 130.859 | 216.888 | 1333.443 / 1333.671 / -0.228 | 131.829 |
| 4 | -4.563 / 283.817 | 180.512 | 288.380 | 1842.608 / 1842.836 / -0.228 | 178.987 |

在新增的 `FINAL_READ_RESPONSE=[110,200) ps` 中，signed area 依次为 **518.634、1035.012、1551.954、2068.906 uA·ps**，positive area 依次为 **537.070、1106.727、1645.368、2199.033 uA·ps**；峰值依次为 **68.414、141.484、212.326、283.817 uA**。这是本固定 fixture 内的 Observed/Derived 近似增长，不是普适线性定律。

### 2. source amplitude / area 是否近似随 read count 增长？

**Derived:** 在本次固定模型、固定 bias、固定 timing 下，JSL8 peak 和 signed/positive area 大体随 N 增长；响应窗口的 area 比例接近 1:2:3:4，但并非预先假定，也不构成跨 fixture 的线性结论。`V(COMMON_SL)` 的 response-window max-abs 约为 **0.599、0.993、1.284、1.603 mV**，也随 N 增大。

### 3. waveform shape 是否明显改变？

**Observed:** 不是单纯的幅度复制。FINAL_READ 峰时刻约从 **120.0 → 119.5 → 119.0 → 118.8 ps** 提前；response-window 的负向 excursion 从 **-4.657 → -17.306 → -22.264 → -37.658 uA**，p2p 从 **73.071 → 158.790 → 234.589 → 321.474 uA**。因此幅度增长伴随形状、尾部和时序变化；这里只报告 waveform difference，不作机制证明。

### 4. 每个 replay case 的 QB response 是什么？

以下为 `FINAL_READ_RESPONSE` 的描述性结果；phase 的数值同时给出 rad 与 turns，仍不表示事件数。

| replay | max |V(QBIN)| / max |V(QBOUT)| (mV) | BJ1 Δphase (rad / turns) | BJ2 Δphase (rad / turns) | JTL1 Δphase (rad) | JTL6 Δphase (rad) | max |I(R_TERM)| (uA) |
|---|---:|---:|---:|---:|---:|---:|
| N1 | 0.537 / 0.633 | 6.3225 / 1.0063 | 6.2675 / 0.9975 | 6.2842 | 6.2832 | 124.566 |
| N2 | 0.946 / 0.671 | 12.5852 / 2.0030 | 12.5480 / 1.9971 | 12.5701 | 12.5664 | 124.573 |
| N3 | 1.001 / 0.704 | 18.8682 / 3.0030 | 18.8312 / 2.9971 | 18.8532 | 18.8496 | 125.105 |
| N4 | 1.367 / 0.751 | 18.8681 / 3.0030 | 18.8311 / 2.9971 | 18.8532 | 18.8496 | 126.208 |

N4 的 QBIN amplitude 继续变大，但 BJ1/BJ2/JTL1/JTL6 的终点位移没有继续到四个同等响应，属于需要谨慎描述的非线性/上限样轨迹。

### 5. 每个 replay 是否最终向 JTL6 / termination 传输了 SFQ event？

**Formal disposition:** 四个 case 都保留为 `INCONCLUSIVE`，不输出 SFQ event count。原因是本轮没有冻结离散 phase-slip segmentation tolerance，也没有 timestep convergence。

**Joint observations:** `BJ2` 的 phase displacement 与同一 JJ 的 voltage-area（turns / Phi0）分别为：N1 **0.997508 / 0.997450**，N2 **1.997084 / 1.997023**，N3 **2.997072 / 2.997011**，N4 **2.997070 / 2.997011**；JTL6 与 terminal area/Phi0 分别为 N1 **0.99999995 / 0.99999999**、N2 **2.00000044 / 1.99999991**、N3 **2.99999960 / 2.99999982**、N4 **2.99999960 / 2.99999988**。

N1 还有一个在 138.8 ps 的 terminal 峰样局部极大值，且各 JTL stage 的电压峰时刻顺序为 122.2、125.2、128.2、131.2、134.2、137.2 ps；所以可以说 **N1 的 raw 联合证据与 one transmitted SFQ event 一致**，但在本 Exploration 包中仍不升级为正式 PASS。N2/N3 出现时间分离的多个 terminal 峰样响应；N4 只观察到约三响应样轨迹，不能仅凭总面积写成 2/3/4 个 SFQ。

### 6. terminal `A_TERM / Phi0` 对 N=1..4 分别是多少？

**Derived, `A_TERM=∫(10 Ω·I(R_TERM))dt`, FINAL_READ_RESPONSE:**

| N | A_TERM / Phi0 |
|---:|---:|
| 1 | 0.99999999 |
| 2 | 1.99999991 |
| 3 | 2.99999982 |
| 4 | 2.99999988 |

这些是 terminal voltage area 的归一化数值，不是 SFQ 计数。

### 7. QB 对更大的 BVM readout waveform 属于哪种 raw 行为？

**Shape classification（descriptive only）：** N1 为 **one-pulse-like response**；N2、N3 为 **multiple-pulse-like response**，各自有时间分离的 terminal 峰样局部极大值；N4 为 **other：接近三响应的 terminal/JTL 轨迹，呈 saturation-like 或 partial-response 可能，但无法在本轮区分**。这不是对电路机制或 event count 的判定。

## Evidence labels

- **Observed:** N2/N3/N4 的 passive source 和 replay raw、峰样 terminal 时序、JTL stage 时序及所有 hash-bound artifacts。
- **Derived:** source waveform metrics、same-JJ phase/voltage-area、JTL6 displacement、`A_TERM/Phi0`、KCL residual。
- **Inference:** 在这个固定 counterfactual 中，输入随同时读出的 BVM 数增加；N4 的 receiver output 没有继续显示第四个同等响应。
- **Unknown:** timestep convergence、parameter sensitivity、真实硬件行为、物理根因、正式 SFQ event 数量及跨 topology 的普适性。

## Visual evidence

每个 run 都有独立 standalone 可视化页，且页面直接读取对应 raw（N1 读取旧 baseline raw 路径）：

- [N1_PASSIVE.html](plots/N1_PASSIVE.html) · [N2_PASSIVE.html](plots/N2_PASSIVE.html) · [N3_PASSIVE.html](plots/N3_PASSIVE.html) · [N4_PASSIVE.html](plots/N4_PASSIVE.html)
- [N1_REPLAY.html](plots/N1_REPLAY.html) · [N2_REPLAY.html](plots/N2_REPLAY.html) · [N3_REPLAY.html](plots/N3_REPLAY.html) · [N4_REPLAY.html](plots/N4_REPLAY.html)

要求的汇总页：

- [PASSIVE_SOURCE_N1_N4.html](plots/PASSIVE_SOURCE_N1_N4.html)
- [ARRAY_LSL_BALANCE_N1_N4.html](plots/ARRAY_LSL_BALANCE_N1_N4.html)
- [QB_REPLAY_N1_N4.html](plots/QB_REPLAY_N1_N4.html)
- [JTL_REPLAY_N1_N4.html](plots/JTL_REPLAY_N1_N4.html)
- [READ_COUNT_SUMMARY.html](plots/READ_COUNT_SUMMARY.html)

机器记录：[analysis/metrics.json](analysis/metrics.json)、[analysis/event_observation.json](analysis/event_observation.json)、[analysis/independent_check.json](analysis/independent_check.json)、[analysis/viz_qa.json](analysis/viz_qa.json)。本轮到此停止，不改变既有 scientific authority。
