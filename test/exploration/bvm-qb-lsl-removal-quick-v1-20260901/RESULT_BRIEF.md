# BVM_QB_LSL_REMOVAL_QUICK_V1

## 状态

`QUICK_NO_EFFECT` / `INCONCLUSIVE`（物理结论层）/ `USER_REVIEWED` / `STOP`

## What we changed

- BASELINE：canonical BVM，`L_SL = 0.4 pH`。
- CANDIDATE：experiment-local BVM 删除 `L_SL`，将 `R_SL` 输出直接接到 `SL`。
- canonical `circuits/bvm/bvm_cell.cir` 未修改；baseline raw 未重跑。

## What was held fixed

13 ps READ、12×320 JSL、logical1、scaled QB、QB bias `35 uA`、`10 ohm`
output load、jjmit model、其它 BVM 参数、source timing、`0.0125 ps` timestep、
170 ps stop time。没有加入 controls、sweep、JTL、T1 或 magnetic coupling。

READ waveform diagnostic window 是 W3 `[95,110)` ps；BJL2 strict-event activity
window 独立固定为 `[95,115)` ps，post window 为 `[115,130)` ps，tail 仍为
`[125,130)` ps。

## Why we tested it

这是对短 `L_SL` 是否参与 BVM output→JSL→QB READ dynamic mismatch 的最小单变量
方向性 probe；预注册目标是 source/JSL 与 QB trajectory 同时向两个既有 reference 靠近，
不是提前把 `L_SL` 认定为根因。

## What happened（关键观察）

1. **[OBSERVED] pre-READ safety**：candidate 相对 baseline 的 W2 BVM phase 最大
   差为 `1.32894e-05 turns`，source current 最大差为
   `0.000800136 uA`；预注册 safety 判定为
   `True`。
2. **[OBSERVED] source/JSL READ waveform**：W3 `I(B_LD1)` baseline 正峰
   `68.1454 uA`、candidate `67.7227 uA`；
   baseline→candidate exact-grid max diff 为
   `6.32347 uA`。
   candidate 对 grounded reference 的 W3 RMS distance reduction 为
   `-0.288176%`。
3. **[OBSERVED] BVM JS1/JS2**：candidate 与 baseline 的 W3 `JS1`/`JS2` phase
   p2p 分别为 `5.30338` /
   `5.84021 turns`；
   exact-grid 最大差分别为 `0.0344921` /
   `0.0227082 turns`。
4. **[OBSERVED] QB BJs/L1/BJL1**：candidate 相对 ideal replay 的 W3 RMS distance
   reduction 为 BJS `0.871821%`、
   L1 `-1.14401%`、
   BJL1 `-0.448068%`。
5. **[OBSERVED + PHYSICS-BASED INFERENCE] BJL2**：baseline local strict diagnostic 为
   `SUBTHRESHOLD；segment phase=-0.122128 turns，area=-0.122131 Phi0，residual=3.23871e-06 turns，segments=0`；candidate 为
   `SUBTHRESHOLD；segment phase=-0.121208 turns，area=-0.121212 Phi0，residual=4.20732e-06 turns，segments=0`。这只能说明同一 BJL2 的局部
   phase/area compatibility arithmetic；不能称为下游 SFQ delivery。

## What it means

source 和 QB 均没有满足预注册的 `≥20%` 距离下降条件（source=0，QB=0）。在预注册
方向规则下，本轮 outcome 为 `QUICK_NO_EFFECT`。允许的最强措辞是：在这个固定 Quick 条件
下，移除 `L_SL` 没有显示出使 physical BVM→JSL→QB READ trajectory 向既有 reference
明显靠近的方向性效果；不能从一轮结果确立唯一机制。

## What it does NOT prove

- 不证明 `L_SL` 是唯一根因，不证明复现论文 Fig.7。
- 不证明完整 BVM→QB 接口、JTL/T1 兼容性、硬件行为或 timestep convergence。
- 不把 `P(...)` turns、同段面积或 BJL2 local classification 写成系统 SFQ count/Gate。
- 不向其它 L_SL 值、读宽、负载、控制或拓扑外推。

## Possible next options（本轮未执行）

1. 用户先审核本 brief 和唯一 classic overview。
2. 若需机制定位，另行授权一个预注册 interface/preload Quick。
3. 若需 Candidate/结论级主张，另行冻结 controls、收敛和独立审计。
