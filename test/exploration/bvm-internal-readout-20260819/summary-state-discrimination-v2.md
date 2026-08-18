# BVM State Discrimination under IDENTICAL +READ — Exploration summary (v2)

date: 2026-08-19 | tier: Exploration | 新增 1 run（neg-init-pos-read），
其余复用 rev3 raw

## 修正内容（v1 b8ad59c provenance error，已 supersede）
v1 的 RUN_B=neg-read-single-corr 使用 −100µA READ（accepted negative
惯例），比较实际为 (+init,+READ) vs (−init,−READ)。本版新建
**neg-init-pos-read**（−100µA init、**+100µA READ**），实现
(+init,+READ) vs (−init,+READ)。v1 中 READ-transient 相关结论全部
supersede；PRE 静态签名结论保留。

## 实验
- State A：pos-read-single（+100U WL/BL init，+100U WL+SE READ）
- State B：neg-init-pos-read（−100U WL/BL init，**+100U WL+SE READ**）
- load 12Ω、dt=0.0125ps、canonical BVM 未改；READ=0 controls 复用
  （pos-control/neg-control 已确认 NO_ACTIVITY）

## Q1：同一 +READ 下两态 transient 是否仍镜像
**否——完全不对称（决定性差异）**：
| 量 | State A (+init,+READ) | State B (−init,+READ) |
|---|---|---|
| JS1 unwrapped Δφ (READ) | **−18.81 rad（≈−3.0 圈）** | **−0.016 rad（≈0 圈）** |
| JS2 unwrapped Δφ | −18.84 rad（≈−3.0 圈） | −0.001 rad（≈0 圈） |
| V(N6) | +1.814mV / −1.088mV | +0.562mV / −0.653mV |
| V(SL1) | +0.904mV / −0.542mV | +0.273mV / −0.317mV |
| I(L_S1) | +96.6µA / −191.4µA | +1.2µA / −51.4µA |
| I(L_SL) | +75.3µA / −45.2µA | +22.7µA / −26.4µA |

JS 圈数 3 vs 0；N6 幅度比 ≈3.2×；I(L_S1) 峰值比 ≈3.7×。

## Q2：amplitude / sign / timing / switching-threshold 差异
- **amplitude**：有——N6/SL/全部 readout currents 在 State B 下显著
  衰减（0.28–0.6× 幅度，且峰值时间不同：A 主峰 @100–106ps，B 峰
  @96/106ps 边沿响应）
- **sign**：A 的主 running 瞬态为负向（−3 圈）；B 无 running
- **timing**：A 主峰 @100.99ps（running onset）；B 仅在 READ 边沿
  （96.0/106.0ps）有小响应
- **switching-threshold 差异**：推断存在（+READ 对 A 态触发 running、
  对 B 态不触发）——基于幅度/圈数证据，非直接 JJ 阈值测量

## Q3：PRE ±19.5µA R-loop static bias 如何映射到 READ transient
- PRE 静态：L_S1/L_S2/L_S3 = ±19.5µA（A/B 符号镜像），L_M3 = ±24.1µA
- READ 期间：State A 的 L_S1 达 −191.4µA（running 主导）；State B 仅
  −51.4µA（无 running）
- 映射关系：**PRE bias 符号与 READ 电流方向的乘积决定是否进入
  running**——A 态（+bias）与 +READ 同向 → 触发 running（大瞬态）；
  B 态（−bias）与 +READ 反向 → 抑制 running（小瞬态）。静态偏置
  是 discrimination 的物理来源，瞬态是放大后的表现

## Q4：receiver 更适合哪种机制
**magnitude threshold 即可**（基于当前证据）：
- 相同 +READ 下，A 态 N6/SL/电流幅度为 B 态的 3–4×，且圈数 3 vs 0
- 一个幅度阈值型 local one-shot receiver（对 N6/SL 或感应电流设置
  阈值）即可实现 1→1SFQ / 0→0SFQ 判别
- polarity discrimination 仍可作为备选（A 态 running 为负向主导），
  但非必需
- 注意：这是 bounded observation——未做 receiver 电路验证，阈值
  具体值需 screening 确定

## Q5：labels
状态仅称 **state A / state B**（operational states from +init/−init）；
不分配 logical 1/0 identity（S0 未建立，保持）。

## Observed / Derived / Inference / Unknown / Next
- Observed：A(+init,+READ) 触发 ~3 圈 running；B(−init,+READ) 无
  running；幅度 3–4× 差异
- Derived：READ 方向与存储偏置同/反向决定 running 触发
- Inference：magnitude-threshold one-shot receiver 有物理判别依据
  （比 v1 的 direction-sensitive-only 更强）
- Unknown：READ 幅度变化时触发边界（未扫）；B 态是否在更高 +READ
  下进入 running；switching-threshold 的精确值（需 JJ-biased fixture）
- Next：简化 stimulus screening——用与 accepted source 特征一致的
  受控脉冲源测 magnitude-threshold receiver 的 trigger→quench→output

## Promising?
状态判别物理依据存在且强（3 vs 0 圈、3–4× 幅度），但**仍不设计
receiver、不升级 Candidate**（本轮目标仅为确认 discrimination）。
