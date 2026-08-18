# BVM Internal Readout Event Survey — Exploration summary (rev 2)

date: 2026-08-19 | tier: Exploration | solver: build/josim-cli v2.7.2837d13
（hash 48655cb3…）| dt=0.0125ps | R_LD=12Ω

Revision 2 修正（用户审阅 2026-08-19）：
1. 弃用 >π/2 sample-jump 判据 → continuous unwrapped phase +
   same-junction voltage 联合 segmentation（bounded V_ACT=50µV，
   exploration 级，非冻结 Gate）
2. 修复 JM1/JM2 storage 签名独立性（原 v1 loop 复用同 key 覆盖）
3. 修正 repeated-READ 文案（closely matched，非"逐字一致"）
4. N6/SL 只描述 observed attenuation，不归因机制

## Activity segmentation（bounded 判据）
- active: |V(B_Jx)| ≥ 50µV（PRE 静态均值 ~0.22µV vs READ 均值 ~0.72mV）
- 短 gap（<0.1ps）合并；间隔间电压实测 55–59µV（>POST 31µV）→
  尾巴为**衰减 ringing，非真正 retrap**

## JS1/JS2 phase-dynamics classification（修正后）

| run | window | JS1 | JS2 |
|---|---|---|---|
| pos-single | READ1 | DOMINANT_RUNNING_PLUS_RING (−2.98 圈, 12.6ps) | 同 (−2.96 圈, 15.6ps) |
| pos-repeated | READ1 | 同 | 同 |
| pos-repeated | READ2 | DOMINANT_RUNNING_PLUS_RING (−3.00 圈, 12.6ps) | (−2.85 圈, 14.8ps) |
| neg-single | READ1 | SUSTAINED_RUNNING (−3.97 圈, 14.1ps) | DOMINANT_RUNNING_PLUS_RING (−4.04 圈, 14.8ps) |
| neg-repeated | READ1 | 同 | 同 |
| neg-repeated | READ2 | SUSTAINED_RUNNING (−3.98 圈) | (−3.94 圈, 14.1ps) |

每个 run 的结构：**一个主导 multi-turn interval**（无真正零压 retrap 间隙，
连续 ~12–15ps，Δφ 与 ∫Vdt·2π/Φ0 一致到 1e-5 rad 级，全部 interval
va_match=True）+ **衰减 ringing 尾巴**（每段 |turns|<0.15，非 2π 事件）。

**无 LOCALIZED_SINGLE_2PI、无 MULTIPLE_SEPARABLE_2PI 实例。**

## 能否分辨 localized transitions vs sustained running
**能**。联合判据：
- localized single-2π 判据（未出现）：单 interval 且 |turns|≈1
- multiple separable 判据（未出现）：≥2 interval 各 |turns|≈1，间隔真回零
- sustained running 判据（出现）：主导 interval |turns|≥1.5，期间电压持续
  活动（50µV–2.1mV），无真零压 gap

## Storage signature（修正后，diag runs 独立保存）

| | pos | neg |
|---|---|---|
| JM1 φ PRE | 5.9111 rad | −0.00047 rad |
| JM1 φ POST2 | 5.9108 rad | +0.00042 rad |
| JM1 |Δφ| | **3e-4 rad** | **9e-4 rad** |
| L_M1 PRE | −43.6 µA | −44 nA |
| L_M1 POST2 | −44.0 µA | −260 nA |
| L_M2 PRE/POST2 | +43.6/+44.0 µA | +44/−260 nA |
| L_M3 PRE/POST2 | +24.1/+24.5 µA | +49/+289 nA |
| L_PM PRE/POST2 | +43.6/+44.0 µA | +50/+290 nA |

→ READ 后各 storage signature 恢复接近 PRE 值（bounded observation；
Exploration 级**不升级为正式 nondestructive-read Gate**）。

## Repeated-READ quantitative difference
- pos JS1: −2.983 vs −2.995 圈（Δ=0.012 圈 ≈ 0.4%）
- pos JS2: −2.959 vs −2.855 圈（Δ=0.104 圈 ≈ 3.5%）
- neg JS1: −3.974 vs −3.976 圈（Δ=0.002 圈 ≈ 0.05%）
- neg JS2: −4.036 vs −3.939 圈（Δ=0.097 圈 ≈ 2.4%）
→ **closely matched / highly reproducible**（JS2 有 2–3.5% 差异，非逐字一致）

## N6 vs SL finding（保留）
- pos: N6 1.81mV @101.0ps / SL 0.90mV @101.0ps（ratio 2.0×）
- neg: N6 2.38mV @103.3ps / SL 1.19mV @103.3ps（ratio 2.0×）
- 半峰宽相同（10.26 / 5.44ps）；峰位几乎同时
- **Observed attenuation ≈0.5×（SL/N6）；机制未独立验证，不归因分压**

## Bounded inference（修正后仍成立）
**未发现现成的 isolated single-2π internal event source。**
JS1/JS2 在 READ 中表现为 multi-turn sustained phase-running
（pos ≈3 圈、neg ≈4 圈）+ 衰减 ringing，无 separable 2π transition。
此结论是 bounded 的：限于 12Ω 负载、±100µA READ、dt=0.0125ps、
jjmit 模型、单 fixture。N6 2× amplitude finding 保留为 receiver tap
候选观察。

## Observed / Derived / Inference / Unknown / Next

- Observed: 上表全部分类与数值；storage 签名恢复
- Derived: Δφ↔∫Vdt 自洽；圈数按极性区分；running 主段参数
- Inference: JS1/JS2 为可重复 multi-turn running（非单事件源）；
  N6 为更局部 tap 候选
- Unknown: READ 幅度/宽度对圈数影响（未扫）；能否参数化收敛为单圈
  （未动 canonical）；1/25/50Ω 负载行为（未跑）
- Next: A) 简化 stimulus screening（shared-quantizing vs local
  self-quenching one-shot 的 trigger→quench→output）；B) 最小
  control run（read 幅度 0）；C) 负载灵敏度

## Promising internal event candidate?
**否**（同 v1：无 isolated single-2π 源；multi-turn running 是
receiver 设计输入而非现成 SFQ 源）。
