# BVM historical-vs-current 对照说明 — 2026-08-17

> 目的：恢复"原生/老式 JoSIM 查看体验"，直观看 2026-07-17 历史 run 与当前
> frozen S0 canonical 的区别。本文件只做**观察与单位核对**，不从视觉图单独
> 产生 scientific verdict（C02 的 INCONCLUSIVE 判定不受影响）。

## 1. 数据来源（无新 JoSIM run）

| 侧 | 来源 | 网格 | 负载 fixture | 内容 |
|---|---|---|---|---|
| **历史** (A) | `test/final/bvm/bvm_final_viz.html`（2026-07-17 自包含 HTML，内嵌 base64 f8 波形）→ 解码为 `historical/hist_test_bvm_final.csv` | 0.5 ps，0–159.5 ps（320 点） | **12×jjmit(area=3.2) 堆**（B_LD1-12，IC≈320 µA/J） | I(WL1) I(BL1) I(SE1) I(L_SL) P(JM1) P(JS1) P(JS2) |
| **当前** (B) | frozen `runs/bvm-s0-canonical-20260814-01/raw/<case>/0.025ps/run-01.csv`（12-run seal 内） | 0.025 ps，0–170 ps | **R_LD = 12 Ω 电阻** | P/V(JM1) P/V(JM2) V(SL1) I(L_SL) I(WL1) I(SE1) |

解码与校验脚本：`historical/decode_hist_viz.py`（含所有结构断言与单位修正记录）。

## 2. 拓扑 / 刺激的实际差异

**bvm_cell.cir 与 jjmit.cir 均字节级未变**（git 对比：自 2026-07-12 `916ac09` 起
与当前一致；历史 run 与 S0 用的是同一 cell、同一 JJ 模型）。真正变化的：

1. **SL 负载 fixture**：历史 = 12-JJ 堆；当前 S0 = 12 Ω 电阻（S0 网表注释
   "only R_LD SL1 0 12"）。
2. **刺激协议**：
   - 历史：6 事件序列 W1(+100µA WL+BL, 10–20p) → R1(+100µA WL+SE, 30–40p) →
     W0(−100µA, 60–70p) → R0(+100µA WL+SE, 80–90p) → HS_WL(110–120p) →
     HS_BL(+100µA BL, 140–150p)，`.tran 0.25p 160p DST`。
   - 当前：init(±100µA WL+BL, 10–21p) + 单次 read(+100µA WL+SE, **96–105p**，
     S0 注释明确 "R1-derived")，`.tran 0.025p 170p`（无 DST）。
   - **read 脉冲本身是同源的**：同为 +100 µA、10 ps、WL+SE 共激励。
3. **步长/分辨率**：0.5 ps（嵌入网格）→ 0.025 ps（20× 加密）。
4. **probe 差异**（通道缺口，见 §5）：历史有 I(BL1)/P(JS1)/P(JS2)，无
   V(JM1)/V(JM2)/V(SL1)/P(JM2)；当前相反。

## 3. 单位修正（本轮最重要的核对结果）

**历史 HTML 内嵌的 P() 数据是 turns（已 ÷2π），且无任何单位标注**（轴无
title）。判定证据：

- 同 cell + 同模型 + 同 ±100 µA/10–20 ps 写入 → JM1 状态必须相同；
- 当前 S0（及 P2 时代 12-JJ 负载 run）写入后 JM1 = **+5.913 rad = +0.9411 turns**；
- 历史嵌入值 0.9415 → 若按 turns 读 = 5.9156 rad（与 S0 差 **2.4 mrad**）；
  若按 rad 读 = 0.15 turns，与相同写入下"状态差 6.28×"物理上不可能；
- 读电流佐证：历史 R1 +75.7 µA ≈ S0 +75.3 µA（同一状态才可能）。

因此派生 CSV 中 P 列已按文档记录 ×2π 存为 **true rad**；所有后续消费方
（josim-plot2 查看器、对比图）均按 rad 处理。**历史轴无单位 + 数值恰好等于
turns 值，是旧时代"0.94"被读成 rad（0.15 圈）低估状态的根源**；P2 时代又把
raw rad（5.89）误读为 SFQ 数。当前 S0 口径（±0.94 turns）与历史 turns 值
一致——即"状态一直是 ±0.94 圈，以前是单位没标对"。

## 4. 波形对照观察（全部来自上图，数值程序化核验）

### 4.1 初始化 / settling / read timing

| 项 | 历史 | 当前 S0 |
|---|---|---|
| 写入后 JM1 平台 | +5.9154 rad（+0.94 圈）@ 24–30 ps | +5.9130 rad（+0.94 圈）@ 21 ps 起 |
| 平台稳定耗时 | 写入结束(21p)后 ~4 ps 内 | ~4 ps 内（同） |
| 正态读峰值延迟 | +75.7 µA @ **onset+9.1 ps** | +75.30 µA @ **onset+5.03 ps** |
| 负态读电流形态 | 先小正 +17 µA（~onset+1 ps）→ 后 −23.1 µA（~onset+11 ps） | 先小正 +5 µA（~onset+4 ps）→ 后 −26.4 µA（onset+10.0 ps） |
| read 后恢复 | 读结束 ~10 ps 内回平台 | ~15 ps 内回平台（0.025 ps 网格可见细节更多） |

### 4.2 JM1/JM2 动态（旧解释 vs 当前解释）

- **JM1 状态**：±0.94 圈在两侧完全相同（见 §3）。旧时代的问题是单位标签，
  不是动力学。
- **负态读期间 JM1 下探**：历史 R0 与 S0 负读都从 −5.93 rad 下探到
  ≈ **−4.95 rad**（历史 −4.9516，S0 −4.9361，差 16 mrad），读后经
  ≈ **−5.24 rad** 摆回平台（历史 −5.2398 @ 91 ps，S0 −5.2427 @ 106 ps，
  差 3 mrad）。**两个 fixture 下 JM1 读期间动力学几乎相同。**
- **JM2**：仅当前有 probe。负态读时 P(JM2) 从 −0.32 → −0.03 → −0.35 rad
  小幅扰动；历史无 JM2 数据，无法对照（通道缺口）。

### 4.3 SL source response（正/负态读出）

- **正态读出 ≈ +75 µA 两侧一致**（75.7 vs 75.3），且峰值延迟不同
  （9.1 vs 5.0 ps——12-JJ 堆负载下峰值更晚或更钝）。
- **负态读出**："先小正、后 −23/−26 µA" 的**形状两侧一致**，量级随负载
  略有不同（早期正冲 +17 vs +5 µA；晚期 −23 vs −26 µA）。
- 即：**"现在 +75 µA / −26 µA 的 SL response 在旧波形里早已存在"成立**——
  正态 +75.7 µA（R1）、负态 −23.1 µA（R0 晚期）已在 7 月 run 中；当时没有
  V(SL1) probe、没有对齐窗口分析，且 P() 单位未标，所以没有被正确读出。

## 5. 通道缺口（无法同等对照的部分）

| 通道 | 历史 | 当前 |
|---|---|---|
| I(WL1), I(SE1), I(L_SL), P(JM1) | ✅ | ✅（直接对照） |
| I(BL1) | ✅ | ❌ S0 无 BL probe（BL 仅静态输入，读期间为 0） |
| P(JS1), P(JS2) | ✅ | ❌ 当前无 JS probe（JS1/JS2 最大仅 0.78 rad / 0 rad，读期间基本不动） |
| V(JM1), V(JM2), P(JM2), V(SL1) | ❌ 无 V probe | ✅（cmp-8） |

不重新生成科研 raw；若需补 JS/BL probe 对照，需另行授权。

## 6. 回答：哪些"真的变了"，哪些只是"测量/解释对了"

**只是测量/解释正确（电路没变）**
- JM1 状态 ±0.94 圈：历史 turns 值 == 当前值；旧误读来自无单位标签与
  P2 时代的 rad↔SFQ 混用。
- 正态读 +75 µA：历史 R1 已存在，数值几乎相同。
- 负态读"先正后负"形状与 JM1 读期间下探：历史 R0 已存在，与 S0 到 mrad
  级一致。

**电路/fixture 真的变了**
- SL 负载：12-JJ 堆 → 12 Ω（负态读量级 −23→−26 µA、早期正冲 +17→+5 µA、
  正态峰值延迟 9.1→5.0 ps 均与此相关）。
- 协议：多事件序列 → init+read 单次（S0 read 即历史 R1 的脉冲形状）。
- 网格：0.5 → 0.025 ps（历史 0.5 ps 网格无法分辨读内细节，如 V(SL1) 波形
  形状与 JM2 扰动）。

## 7. 产物清单

- `historical/decode_hist_viz.py` — 解码 + turns→rad 修正 + 断言（可复现）
- `historical/hist_test_bvm_final.csv` — 派生数据（true rad；**非 raw evidence**）
- `historical/plots/` — 6 个 josim-plot2 原生查看器（old/current × rad/turns；
  工具原生 seconds 轴）+ 8 张对比 PNG（absolute ps 轴、对齐窗口、同 y 尺度）
  + `cmp_hist_vs_s0.py` 生成器（确定性；所有标题数字经程序化断言核验）
- 本文件
