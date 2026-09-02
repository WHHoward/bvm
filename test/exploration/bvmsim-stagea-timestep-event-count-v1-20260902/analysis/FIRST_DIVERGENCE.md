# FIRST_DIVERGENCE

本文件是新 JoSIM run 之前完成的 existing-raw-only 分歧审计与新矩阵结果的衔接记录。
没有对历史 raw 做重写，也没有用插值制造共同采样点。

## 既有 raw 审计（Observed）

- `BVMSim/data_tran.csv` 与 Stage-A M0 在预注册的 110–170 ps 窗口共同信号上没有检测到有意义分歧；最大相位轨迹差为 1.59155e-14 turn。
- Stage-A M0 与 Stage-A S1 的首个满足预注册持续规则的分歧为 `P(B01|XJTL1_1)`，约 117.3000 ps。
- 同一对 raw 中，JTL1 B01 的 phase-only 阈值交叉约为 117.3 ps，而 BJ2 的 phase+voltage paired 阈值交叉约为 120.4 ps；两者判据不同，不能据此推出 JTL 先导致 BJ2，也不能反向推出 BJ2 先导致 JTL。

## 新矩阵的首个可见分歧（Observed）

下表只比较 exact stored timestamp overlap，并用 T100 作为历史分辨率参照；它不是事件计数判据。

| run | 与 T100 的最早共同窗口分歧备注 |
|---|---|
| T050 | READ1 JTL1.B01 net=4.999847 turn，BJ2 net=4.998204 turn；详见 `metrics.json` 的 exact reference comparison。 |
| T025 | READ1 JTL1.B01 net=4.999830 turn，BJ2 net=4.999188 turn；详见 `metrics.json` 的 exact reference comparison。 |
| T0125 | READ1 JTL1.B01 net=4.999803 turn，BJ2 net=4.999092 turn；详见 `metrics.json` 的 exact reference comparison。 |
| T100_FULL | READ1 JTL1.B01 net=4.000387 turn，BJ2 net=3.999517 turn；详见 `metrics.json` 的 exact reference comparison。 |

## Attribution boundary

- **Observed:** 新 T100 raw 的历史共同信号与历史 raw 完全一致；T100_FULL 在 45 ps 之后也与 T100 一致；T025 raw 与 Stage-A S1 一致。
- **Derived:** 这排除了“仅仅因为 print-start 选项不同”作为 4→5 净相位分支差异的充分解释；同时支持把 `.tran` 控制行视为这组新旧 fixture 的唯一物理/数值改变。
- **Not yet a final scientific conclusion:** 是否足以称为 timestep-induced branch change，以及该 branch change 是否具有稳定的物理事件意义，必须结合 event list、同-JJ phase/area、KCL 和 reviewer 审阅；不能因为 net turns 接近 4/5 就预先下结论。
