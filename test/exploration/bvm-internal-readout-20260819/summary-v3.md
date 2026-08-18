# BVM Internal Readout Event Survey — Exploration summary (rev 3)

date: 2026-08-19 | tier: Exploration | solver: build/josim-cli v2.7.2837d13
（hash 48655cb3…）| dt=0.0125ps | R_LD=12Ω

Revision 3 修正（用户审阅 2026-08-19）：
**negative fixture 错误已修正**：旧 neg-*（v1/v2）的 init 是 `-100→+100 µA`
ramp（`11p -100U 20p +100U`）且 READ 用 +100U——非 accepted negative
plateau。以 ACCEPTED L12-negative-read.cir 为源重建 corrected runs：
- `neg-read-single-corr` / `neg-read-repeated-corr` / `neg-diag-corr`
  （init `-100U plateau through 20ps`，READ `-100U 96-105ps`）
- 新增 READ=0 control：`pos-control` / `neg-control`（同 topology/knots，
  READ amplitudes=0）

**supersede 声明**：旧 `neg-read-single` / `neg-read-repeated` / `neg-diag`
（v1/v2 commit 02f30b8 / 8535598 中）的 negative 结果**无效**，被
corrected runs 取代；旧 raw 保留不改（append-only）。

## Fixture 验证
- `neg-read-single-corr` vs accepted L12-negative-read：14 shared cols /
  **0 mismatches**（逐 token 一致）
- `neg-control` vs accepted L12-negative-control：14 shared cols /
  **0 mismatches**

## 1. Corrected negative JS1/JS2 dynamics
与 positive **完美镜像**（对称反转）：
| run | window | JS1 | JS2 |
|---|---|---|---|
| neg-single-corr | READ1 | DOMINANT_RUNNING_PLUS_RING (−2.983 圈, 12.6ps) | (−2.959 圈, 15.6ps) |
| neg-repeated-corr | READ1 | 同 | 同 |
| neg-repeated-corr | READ2 | (−2.995 圈, 12.6ps) | (−2.855 圈, 14.8ps) |

（对比 positive：JS1 −2.983 / JS2 −2.959 —— **与 positive 数值逐位相同**，
说明两种极性 READ 产生完全对称的 running 行为。旧错误 fixture 的
"neg≈4 圈" 是 ramp 刺激伪影，已 supersede。）

## 2. Positive vs corrected-negative 对比
- JS1/JS2 主导 interval 圈数、时长、ringing 结构**逐位相同**（±0.001 圈级）
- storage 签名镜像对称：pos JM1 5.9111→5.9108；neg JM1 −5.9111→−5.9108
- 唯一差异：极性符号（phase 累积方向同号——两者都是负向 running，
  与 READ 电流方向一致；sign 与 init 无关）

## 3. Negative storage signature（neg-diag-corr）
| | neg |
|---|---|
| JM1 φ PRE→POST2 | −5.9111→−5.9108 rad（Δ=3e-4） |
| JM2 φ | −0.3187→−0.2635 rad（Δ=0.055） |
| L_M1 | +43.6→+44.0 µA |
| L_M2 / L_M3 / L_PM | −43.6→−44.0 / −24.1→−24.5 / −43.6→−44.0 µA |
→ 恢复接近 PRE（bounded；不升级为 nondestructive-read Gate）

## 4. N6 vs SL（corrected negative）
- neg-corr: N6 1.8145mV @100.99ps / SL 0.9041mV @101.01ps（ratio 2.0×，
  同宽）—— **与 positive 严格一致**（pos: N6 1.8145mV @100.99ps /
  SL 0.9041mV @101.01ps）；负极性 READ 产生同幅值、同 timing 的瞬态
  （符号与激励反相，|V| 一致）
- observed attenuation ≈0.5×；不归因机制
- 注：summary-v2 中记录的"neg 2.38/1.19mV"来自旧错误 ramp fixture
  （已 supersede），不是 corrected negative 行为

## 5. READ=0 control（最小 control）
- `pos-control`（init +100U，READ 0）：READ1/READ2 均 **NO_ACTIVITY**
  （JS1/JS2 0 intervals，0 圈）
- `neg-control`（init −100U，READ 0）：同 **NO_ACTIVITY**
→ **JS1/JS2 multi-turn activity 确认由 READ 脉冲触发**；init/plateau
  本身不产生 running。control 与 accepted L12-control 逐 token 一致。

## 6. Bounded inference（修正后仍成立）
**仍支持：canonical BVM 没有 ready isolated single-2π source。**
- READ 触发 JS1/JS2 对称 multi-turn running（±100µA READ → ≈3 圈，
  12–15ps）+ ringing；无 LOCALIZED_SINGLE_2PI / MULTIPLE_SEPARABLE_2PI
- 极性对称（不是 0/1 区分机制）；READ=0 无活动
- bounded: 12Ω、±100µA、dt=0.0125ps、jjmit、单 fixture

## Observed / Derived / Inference / Unknown / Next
- Observed: corrected neg 与 pos 对称；control 无活动；storage 恢复
- Derived: running 由 READ 触发；极性对称
- Inference: 无现成单事件源；N6 仍为局部 tap 候选
- Unknown: READ 幅度/宽度-圈数关系（未扫）；单圈收敛可能性（未动
  canonical）；1/25/50Ω 负载（未跑）
- Next: A) 简化 stimulus screening（shared-quantizing vs local
  self-quenching one-shot）；B) 已完成的 READ=0 control；C) 负载灵敏度

## Promising internal event candidate?
**否**（与 rev2 一致；现在基于正确的 negative fixture + control）。
