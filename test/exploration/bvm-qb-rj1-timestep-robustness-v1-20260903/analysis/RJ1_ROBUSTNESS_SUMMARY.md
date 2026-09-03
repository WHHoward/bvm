# RJ1_ROBUSTNESS_SUMMARY

状态：`SOL_XHIGH_REVIEWED_PENDING_USER_REVIEW`。本文件已纳入 Sol XHigh reviewer 的 analysis correction；不会因为预期的 4→5 现象而把某个 RJ1 选为 winner。

## 总体结论（当前证据层）

- 三个 RJ1 的 0.025 vs 0.0125 ps fine pair 在已登记的数值/计数比较上都一致；这是 `fine-pair agreement`，不是 timestep convergence proof。late candidate presence 仅作 post-hoc descriptive observation，不计入预注册标准。
- 三个 RJ1 都从 coarse 的约 4-turn net trajectory 转到 fine 的约 5-turn net trajectory；这是已观察到的 timestep sensitivity，但没有足够的分叉追踪、solver 诊断或初值/重启证据证明其为已识别动力学 branch switch。fine BJ2 仍是约 4-turn continuous multi-turn segment 加 late sub-unit residual，而不是四个 separated SFQ。
- Sol XHigh 复核后的 four-BVM primary classification 为 `TIMESTEP_SENSITIVE`；RJ1=12 仅作为 `BASELINE` 参考，RJ1=11.5/11 均为 `INCONCLUSIVE`，没有 winner。
- single-BVM S0 在三个 RJ1 均没有 strict complete read/post false trigger；S1 BJ2 约 1 Phi0 仅支持 source-level bounded observation，但 JTL1–JTL5 B02 只到约 0.91-turn candidate，故 full six-stage protection 仍是 `INCONCLUSIVE`，不能升级为 protected PASS。

## RJ1 × fine timestep criteria

| RJ1 | pair | count same | polarity | late complete presence | late candidate presence* | flux diff (Phi0) | phase diff (turn) | onset diff (ps) | JTL count/order observation (physical order) | fine-pair result |
|---:|---|---|---|---|---|---:|---:|---:|---|---|
| 12 | T025 vs T0125 | True | True | True | True | 0.001006 | 0.001025 | 0.0125 | count_same=True; observation_same=True; physical_order=False/False | `FINE_PAIR_ROBUST_OBSERVED` |
| 11.5 | T025 vs T0125 | True | True | True | True | 0.000677 | 0.000698 | 0.0125 | count_same=True; observation_same=True; physical_order=False/False | `FINE_PAIR_ROBUST_OBSERVED` |
| 11 | T025 vs T0125 | True | True | True | True | 0.000239 | 0.000259 | 0.0125 | count_same=True; observation_same=True; physical_order=False/False | `FINE_PAIR_ROBUST_OBSERVED` |

## 分 RJ1 回答

### RJ1 = 12 ohm

- fine-step branch: T025/T0125 BJ2 net `4.999188` / `4.999092` turn；principal same-segment phase/area `4.023470` / `4.023497` 与 `4.024495` / `4.024502`；两者均 continuous multi-turn，非 separated event count。
- timestep sensitivity: fine pair registered-comparison result `True`；但 T100/T050 → fine 的 net branch 变化为 `3.999517` / `4.998204` → `4.999188`。这是 timestep-conditioned trajectory selection 的证据，尚不足以证明已识别的 timestep-induced dynamical branch change。
- late excursion: fine BJ2 principal 后仍有 candidate phases `['0.9736']`（T025；candidate* 为 post-hoc descriptive threshold），complete late event count `0`；不是“完全消失”。
- single-BVM protection: S0 flags `[False, False]`；S1 BJ2 phase/flux `['1.0065', '1.0075']` / `['1.0066', '1.0075']`；full six-stage protection `['S1_PROTECTION_INCONCLUSIVE', 'S1_PROTECTION_INCONCLUSIVE']`，故当前为 bounded source-level preservation + full-chain inconclusive。
- reviewer disposition: `BASELINE`；four-BVM 总体为 `TIMESTEP_SENSITIVE`，没有据此推荐 11.5 或 11 为 winner。

### RJ1 = 11.5 ohm

- fine-step branch: T025/T0125 BJ2 net `4.999000` / `4.999247` turn；principal same-segment phase/area `4.023387` / `4.023413` 与 `4.024084` / `4.024090`；两者均 continuous multi-turn，非 separated event count。
- timestep sensitivity: fine pair registered-comparison result `True`；但 T100/T050 → fine 的 net branch 变化为 `3.999495` / `3.999545` → `4.999000`。这是 timestep-conditioned trajectory selection 的证据，尚不足以证明已识别的 timestep-induced dynamical branch change。
- late excursion: fine BJ2 principal 后仍有 candidate phases `['0.9736']`（T025；candidate* 为 post-hoc descriptive threshold），complete late event count `0`；不是“完全消失”。
- single-BVM protection: S0 flags `[False, False]`；S1 BJ2 phase/flux `['1.0051', '1.0058']` / `['1.0051', '1.0058']`；full six-stage protection `['S1_PROTECTION_INCONCLUSIVE', 'S1_PROTECTION_INCONCLUSIVE']`，故当前为 bounded source-level preservation + full-chain inconclusive。
- reviewer disposition: `INCONCLUSIVE`；four-BVM 总体为 `TIMESTEP_SENSITIVE`，没有据此推荐 11.5 或 11 为 winner。

### RJ1 = 11 ohm

- fine-step branch: T025/T0125 BJ2 net `4.999050` / `4.999239` turn；principal same-segment phase/area `4.022799` / `4.022826` 与 `4.023058` / `4.023064`；两者均 continuous multi-turn，非 separated event count。
- timestep sensitivity: fine pair registered-comparison result `True`；但 T100/T050 → fine 的 net branch 变化为 `3.999584` / `3.999459` → `4.999050`。这是 timestep-conditioned trajectory selection 的证据，尚不足以证明已识别的 timestep-induced dynamical branch change。
- late excursion: fine BJ2 principal 后仍有 candidate phases `['0.9745']`（T025；candidate* 为 post-hoc descriptive threshold），complete late event count `0`；不是“完全消失”。
- single-BVM protection: S0 flags `[False, False]`；S1 BJ2 phase/flux `['1.0035', '1.0042']` / `['1.0036', '1.0042']`；full six-stage protection `['S1_PROTECTION_INCONCLUSIVE', 'S1_PROTECTION_INCONCLUSIVE']`，故当前为 bounded source-level preservation + full-chain inconclusive。
- reviewer disposition: `INCONCLUSIVE`；four-BVM 总体为 `TIMESTEP_SENSITIVE`，没有据此推荐 11.5 或 11 为 winner。

## Observed / Derived / Inference / Unknown

- **Observed:** 24 个有效 solver raw、实际 timestep/grid、per-run phase/area/event-list/KCL、120 张独立图和 7 张 comparison 已生成；四-BVM 细步长的 BJ2 主段为约 4-turn continuous segment，net trajectory 约 5 turns；single S1 BJ2 约 1 Phi0。
- **Derived:** fine pair 的数值/strict count comparison 如上；KCL 使用共享 `scripts/bvmtools/kcl.py`，不是本地重写。
- **Inference:** 可以把各 RJ1 的 fine pair 描述为 `FINE_PAIR_ROBUST_OBSERVED`，但 Sol XHigh 将 four-BVM 总体定为 `TIMESTEP_SENSITIVE`；JTL local B02 序列没有建立完整 cross-junction event identity。
- **Unknown:** 4→5 net branch 的真正动力学归因、是否只是 solver branch selection、11.5/11 的 margin/over-damping 机制、canonical BVM compatibility、paper mechanism identity 和更细 timestep behavior。

## Allowed next options（不在本轮执行）

1. 用户审阅 Sol XHigh 意见后，决定是否重新授权某一 RJ1 的 candidate validation。
2. 若获得单独授权，可设计 branch-attribution diagnostic；不得把本轮 net trajectory 直接当 SFQ count。
3. 只有重新授权后才考虑更细 timestep、参数点或 canonical BVM 路线。

## Gate

`AWAITING_USER_REVIEW`；`user_reviewed=false`；`next_step_authorized=false`；`automatic_next_experiment=false`。
