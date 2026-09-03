# SINGLE_BVM_PROTECTION

范围：既有 single historical BVMSim BVM → 12-JJ sensing line → QB → six-stage JTL-loaded fixture；读窗口按既有 `[70,82)` ps，post 检查窗口为 `[82,200)` ps。S0 false trigger 同时检查 QB/JTL 的 read 与 post complete segment；S1 行展示 BJ2 与 JTL B02 的同段 phase/area candidate。

| RJ1 (ohm) | timestep (ps) | S0 false trigger / extra | S1 BJ2 phase / flux (turns / Phi0) | JTL1 B02 candidate phase / flux; complete | JTL6 B02 phase / flux; complete/clean | protection verdict |
|---:|---:|---|---|---|---|---|
| 12 | 0.025 | False | 1.006526 / 1.006566 | 0.911512 / 0.911576; 0 | 1.067255 / 1.067312; 1/1 | `S0_NO_STRICT_TRIGGER + S1_PROTECTION_INCONCLUSIVE` |
| 12 | 0.0125 | False | 1.007525 / 1.007535 | 0.911584 / 0.911599; 0 | 1.067099 / 1.067112; 1/1 | `S0_NO_STRICT_TRIGGER + S1_PROTECTION_INCONCLUSIVE` |
| 11.5 | 0.025 | False | 1.005097 / 1.005138 | 0.911364 / 0.911427; 0 | 1.067265 / 1.067322; 1/1 | `S0_NO_STRICT_TRIGGER + S1_PROTECTION_INCONCLUSIVE` |
| 11.5 | 0.0125 | False | 1.005813 / 1.005822 | 0.911418 / 0.911432; 0 | 1.067103 / 1.067117; 1/1 | `S0_NO_STRICT_TRIGGER + S1_PROTECTION_INCONCLUSIVE` |
| 11 | 0.025 | False | 1.003547 / 1.003588 | 0.911190 / 0.911253; 0 | 1.067266 / 1.067322; 1/1 | `S0_NO_STRICT_TRIGGER + S1_PROTECTION_INCONCLUSIVE` |
| 11 | 0.0125 | False | 1.004192 / 1.004201 | 0.911261 / 0.911275; 0 | 1.067104 / 1.067117; 1/1 | `S0_NO_STRICT_TRIGGER + S1_PROTECTION_INCONCLUSIVE` |

## 关键观察

- 12/11.5/11 ohm 的 S0 均没有 strict complete BJ2/JTL B02 read 或 post trigger；这是有限 fixture 下的 bounded observation，不是普适无 false-trigger 保证。
- 三个 RJ1 的 S1 BJ2 都保持约 1.0035–1.0075 turn phase 与 1.0036–1.0075 Phi0 area；这是本矩阵内的 QB source-level approximately-one 描述性观察，不是预注册 Gate。
- JTL1–JTL5 B02 约 0.91 turn candidate，未达到本实验 complete ≥1 turn；JTL6 B02 约 1.067 turn 且 clean。因而 full six-stage one-event protection 在本 strict criteria 下是 `INCONCLUSIVE`，不能只凭 JTL6 宣称逐级保持。

## Boundary

S1 source-level candidate、local JTL activity 和 downstream identity 是不同证据层；表格不升级为 system Gate。
