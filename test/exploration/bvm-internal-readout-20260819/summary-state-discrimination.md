# BVM Logical-State Discrimination — Exploration summary

> **SUPERSEDED (2026-08-19, user review)**：本文件 READ-transient
> discrimination 部分存在 provenance 错误——`RUN_B = neg-read-single-corr`
> 实际使用 **−100µA WL+SE READ**（accepted negative 惯例），不是 +100µA。
> 因此原比较为 (+init,+READ) vs (−init,−READ)，**不是**
> (+init,+READ) vs (−init,+READ)。以下结论全部降级/supersede：
> - "READ transient exact mirror" 及所有基于它的 discrimination 结论
>   （magnitude detector cannot discriminate / only direction-sensitive
>   discriminator）
> - 保留项：**PRE [80,90) 静态 signature 比较**（发生在 READ 前，不受
>   READ 极性影响）——JS1/JS2 phase ±0.267 rad、L_S1/L_S2/L_S3 static
>   current ±19.5µA 的 sign-mirror observation 仍有效。
> 正确实验见 `summary-state-discrimination-v2.md`。

date: 2026-08-19 | tier: Exploration | 复用 rev3 raw（无新 run）

## State 定义（来自 ACCEPTED 权威，不自行命名 logical 1/0）

| 项 | 来源 | 内容 |
|---|---|---|
| 两个 operational states | JH-20260814-BVM-S0-D0（ACCEPTED） | +init：JM1=+5.9108 rad、JM2=+0.319；−init：JM1=−5.9108、JM2=−0.319；no-init=0。**仅 operational distinctness，未建立 logical 1/0 identity** |
| canonical READ | JH-20260817-BVM-S2-STABLE-LOAD-001（ACCEPTED） | WL+SE ±100µA、96–105ps、dt=0.0125ps、R_LD=12Ω |

## 方法
完全相同 READ stimulus（+100µA）读取两态：A=pos-read-single、B=neg-read-single-corr（fixture 与 accepted L12-negative-read 逐 token 一致）。比较 10 个探针的 PRE 静态签名与 READ 窗口 signed peaks（幅度+时序）。

## 结果（state-discrimination.json，全 Decimal 精确）

1. **PRE 静态（READ 前 [80,90)）**：10/10 探针 **exact sign-mirror**（A=−B）：
   - JS1 φ ±0.2665 rad、JS2 ∓0.2669
   - L_S1 ±19.52µA、L_S2 ∓19.52µA、L_S3 ±19.52µA（R-Loop 静态电流携带状态符号）
   - L_SL ±1.10nA、V(N6) ±26nV
2. **READ transient [94,130)**：10/10 探针 signed peaks **exact mirror**（幅度逐位 + 时序逐位：A 的 +peak@t ↔ B 的 −peak@t）
   - 例：V(N6) A +1.8145mV@100.99 ↔ B −1.8145mV@100.99；V(SL1) A +0.9041mV ↔ B −0.9041mV
   - I(L_S1) A −191.4µA@104.48 ↔ B +191.4µA@104.48
3. **无任何非对称幅度/时序差异**——magnitude/energy 探测器无法区分两态

## 对 receiver 的含义（bounded inference）

- **判别信号存在且是符号编码的**：R-Loop 静态电流 L_S1/L_S2 与 JS1/JS2 相位在两态间严格反号（±19.5µA / ±0.267 rad）。一个**方向敏感**的 local one-shot receiver（例如带偏置的 JJ，只对某一符号的感应电流/相位响应）原则上可用 PRE 静态签名判别状态。
- **READ transient 完全镜像**：running 是 READ 电流主导，两态 running 形状相同（±3 圈）——若 receiver 依赖 READ 期间的幅度/能量，无法区分。
- 因此"1→1SFQ / 0→0SFQ"物理可行性取决于**方向选择性**，不取决于幅度。BVM 内部确实存在（S0 定义的）两个可判别 operational states，且判别信息以符号形式存在于 R-Loop。
- **不设计 receiver、不升级 Candidate**；此为后续 receiver screening 的输入条件。

## Observed / Derived / Inference / Unknown / Next
- Observed: 全探针 PRE+READ 精确镜像（幅度与 timing）
- Derived: 状态符号编码于 R-Loop 静态电流/相位；READ running 形状与状态无关
- Inference: 方向敏感 one-shot receiver 有判别依据；幅度型探测器不行
- Unknown: READ 幅度变化时镜像是否保持；JS1/JS2 相位在 repeated READ 后的累积（POST2 ±37.4 rad）是否影响判别窗口；1/25/50Ω 负载下的镜像性
- Next: 用与 accepted source 特征一致的简化 stimulus 构建方向敏感 discriminator 的 screening（仍不接 canonical BVM、不设计最终 receiver）
