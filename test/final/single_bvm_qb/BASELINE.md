# 冻结基线（Step 0，历史版本；计量冻结已失效）

> [!CAUTION]
> **2026-08-09 审计：本文的原始 CSV 仍有效，但相位指标和物理解释已失效。** JoSIM `P()` 为 rad；本文及 `scripts/sfq_metrics.py` 将 raw rad 误作 \(\phi/(2\pi)\)。例如 JM1 `−5.909806 rad = −0.940575` 圈，BJs `+6.272743 rad = +0.998338` 圈。`fast_events` 是过阈值采样间隔数，不是事件数。当前口径见 `docs/guide/project-guide.md` 和 `docs/HANDOVER.md`。

> **状态**: ⏸️ 2026-08-06 历史冻结；计量冻结已于 2026-08-09 失效
> **用途**: 保留原始 CSV、网表和旧判读以供审计；不是当前物理 Gate。
> **历史指标脚本**: `scripts/sfq_metrics.py`（单位与事件定义错误，修复前禁止作为物理口径）

---

## 1. 冻结配置

| 项目 | 值 |
|------|-----|
| Git commit | `6a9363cf903bc4818ff383ae5962ba9dc0e34dab` (master) |
| JoSIM 版本 | v2.7.2837d13 |
| 基线网表 | `test/final/single_bvm_qb/test_bvm_bq_baseline.cir` |
| BVM cell | `circuits/bvm/bvm_cell.cir` (jjmit 时代, 7/12 18:37 后) |
| BQ cell | `circuits/qb/bq_cell.cir` (BJs=50µA, BJL1=36µA, BJL2=54µA) |
| JJ 模型 | `circuits/models/jjmit.cir` (Ic×RN=1.6mV, R0/RN=10) |

**文件 SHA-256**:
```
9b04ac6f...  test_bvm_bq_baseline.cir
5ee4e8f0...  circuits/qb/bq_cell.cir
ea734654...  circuits/bvm/bvm_cell.cir
19862d1f...  circuits/models/jjmit.cir
```

**网表要点**: BVM → 8×jjmit(area=3.2) SL 负载 → 标准 BQ (IBias=35µA, Rload=10Ω)。
驱动序列: W1(10-20p) R1(30-40p) W0(60-70p) R0(80-90p)，全部 ±100µA/10ps。`.tran 0.1p 110p`。

---

## 2. 指标定义（冻结口径）

| 指标 | 定义 |
|------|------|
| `net_delta_sfq` | P(t_end) − P(t_start)，单位 Φ₀（JoSIM P() 输出即 φ/2π） |
| `max_excursion_sfq` | max\|P(t) − P(t_start)\| |
| `total_variation_sfq` | Σ\|P(i+1) − P(i)\|（总滑移量） |
| `fast_events` | \|ΔP\| > 0.3 SFQ / 0.1ps 样本 的次数（真 SFQ 脉冲够格，慢滑移不算） |
| `max_dPdt` | max\|ΔP\| / dt，SFQ/ps |

---

## 3. 可复现结果（确定性已验证）

**BVM→BQ 基线** — 3 次运行 md5 完全一致 (`e53acb71...`)

| 指标 | JM1 | BJs | BJL1 | BJL2 |
|------|-----|-----|------|------|
| net_delta_sfq | −5.9098 | **+6.2727** | +0.4433 | +0.3758 |
| max_excursion | 7.6677 | 6.9096 | 2.2262 | 1.2704 |
| total_variation | 33.877 | 25.941 | 16.782 | 6.353 |
| fast_events | 17 | **0** | 0 | 0 |

| 峰值 | 值 | 时刻 |
|------|-----|------|
| I(L_SL) R1 读出 | 68.41µA | 38.9ps |
| I(L_SL) R0 读出 | ~1.4µA | ~90ps |
| V(OUT_Q) | −157.4µV | 42.5ps |

**BVM 独立** (`test_bvm_final.cir`) — 2 次运行 md5 一致
- JM1@25ps = **+5.93 SFQ（写入多翻转）**，10.5ps 瞬态穿过 0.94
- JS1/JS2 大量翻转 (fast_events 101/97)
- I_SL 峰值 75.74µA @39.1ps

**BQ 独立** (`test_qb_final.cir`) — 2 次运行 md5 一致
- V(OUT1) 峰值 = **1035.0µV** @13.8ps（与 7/13 记录精确一致）
- BJs 累积 = 603.25 SFQ @300ps 窗口（6×90µA 脉冲，每脉冲 ~100 SFQ = 电压态滑移）

---

## 4. 历史矛盾解决（S0.1 结论）

### 4.1 根因：旧记录 = 两套模型时代混合 + 滑移计数误读

**`JM1 = 0.94 SFQ`（旧记录）→ 不可复现，属 V0 模型时代**
- 7/12 18:37 (commit `916ac09`) 把 BVM cell 从 `jj120/jj140/jj74`（V0, Ic×RN=0.25mV）转换为 `jjmit`（1.6mV）
- 当前 jjmit 配置写入**多翻转**（settle +5.93 SFQ），仅 t=10.5ps 瞬态穿过 0.94
- 旧记录是转换前的值（`mitll_models.cir` 已随该 commit 删除，无法复现）

**`BJs = 1.00 SFQ`（7/13 记录）→ 计数错误**
- 7/13 网表与当前一致（SL 68.4µA / Vout 157µV 精确复现）
- 实际 BJs net = +6.27（R1 期间电压态滑移）；1.00 可能是相位穿越 1.0 时刻或峰值窗口的读数

**`BJs = −0.00001 SFQ`（GPT 2026-07-17）→ 不可复现**
- 尝试变体：当前网表、旧 area=5 网表（`single_bvm_qb.cir`）、电压分析模式(-a 0)、早期窗口
- 全部产出 +6.2 ~ +6.3 SFQ。该数值无法由任何合理变体重现，最可能为 GPT 测量管线（窗口/列/解析）差异

**`190 / 96 / 603 SFQ`（BQ 独立）→ 电压态滑移的窗口依赖计数**
- Vpk=1035µV 三份记录一致 ✓；相位累积量随窗口/驱动时长变化（300p→603），非物理量

### 4.2 真正稳定的物理量（所有运行一致）

1. R1 读出 SL 峰值电流 = 68.4µA（3 份记录一致）
2. BQ 输出峰值电压 ≈ 157µV ≪ 1mV（无 SFQ 脉冲）
3. BJs 在 R1 期间进入**阻尼电压态滑移**（net +6.27, 0 快速事件）——不是离散 SFQ 翻转
4. BVM jjmit 写入为多涡旋态（±~6 SFQ），非单涡旋

### 4.3 结论

> **基线结论不变且证据增强：BVM→BQ 级联无可用离散 SFQ 输出。**
> "BJs 相位计数矛盾"根因是旧记录混用两套模型时代 + 对电压态滑移计数口径不一；
> 冻结口径（`scripts/sfq_metrics.py`）下所有量确定且可复现。

---

## 5. 对后续步骤的含义

- **Step 1 (BQ v4)**：BQ 输入侧实际收到的是 ~68µA 慢衰减电流（30-40ps 时间尺度），不是 2ps SFQ 快脉冲。v4 验证必须同时检查"电流脉冲直接注入"与"真实 BVM 波形注入"两种模式
- **Step 2 (级联)**：当前 BVM 写入是多涡旋态——若需要干净单涡旋基准，需先评估 BVM 写驱动（100µA/10ps 过强）或模型选择
- 所有新实验必须以本文件的口径产出指标并保存原始 CSV（勿只存 HTML/结论）

---

## 6. 关联文件

- 指标脚本: `scripts/sfq_metrics.py`
- 实验记录: `EXPERIMENT_LOG.md`（7/13-7/17 七轮实验）
- 矛盾分析: `memory/GuidanceFromGpt.md` §二（GPT 审计）、`memory/bvm-bq-coupling-experiments.md`
- 原始 CSV（本次生成）: `/tmp/step0_run1/2/3.csv`, `/tmp/step0_bvm_1.csv`, `/tmp/step0_bq_1.csv`
