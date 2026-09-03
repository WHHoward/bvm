# HISTORICAL BVMSIM JM2-connected single-BVM A/B Quick

> 本报告只描述 task-local historical BVMSim 单 BVM 变体；不代表 canonical BVM、论文机制或普遍器件结论。

## 1. What changed

- 新建 `variants/bvm_jm2_connected.cir`，唯一物理改动是 `L_M2 2 4 24.5P` → `L_M2 2 3 24.5P`。
- 在同一 corrected single-BVM fixture 上运行四个新 B-side case：S0/S1 各一个 direct 10 Ω 和六级 historical JTL + 10 Ω。
- A-side 只读取既有 corrected baseline raw；没有重跑、覆盖或修改旧 raw/deck/plot。

## 2. What was held fixed

- BVM 除上述 JM2 连接外的全部拓扑与参数、original `BVMSim/BQ.cir`（RJ1=12 Ω、RJ2=4 Ω、250 µA bias）、terminal 12-JJ sensing line、historical JTL、激励、`.tran 0.1p 200p`、solver 和 10 Ω termination 均保持不变。
- WRITE 仍是 WL+BL；READ 仍是 WL+SE，且 READ 中 BL=0。

## 3. Artifact validity

- post-run preflight：`ARTIFACT_VALID`；all runs：`True`。
- variant diff：`PASS`；四个 case 的 raw、deck、probe、model closure 和 protocol 结果见 `analysis/post_run_preflight.json`。
- 所有原始 CSV 只读解析；A/B 对照要求完整时间网格一致，不做插值。A-side 没有 L_M1/L_M2/L_M3/L_PM 四条历史 probe，因此这四条不做伪造的 A/B 对照。

## 4. OBSERVED local JM2 electrical behavior

下表只报告同一 JM2 的相位端点差、电压面积和波形活动；`turns` 已明确是 rad/(2π)，不是 SFQ 数。

| run | window | Δphase (turns) | ∫Vdt/Φ0 (turns) | residual (turns) | V p2p (mV) | I p2p (µA) |
|---|---:|---:|---:|---:|---:|---:|
| S0-R-JM2C | PRE_READ | -0.101389 | -0.102513 | 0.001124 | 0.446641 | 10.317800 |
| S0-R-JM2C | READ | -0.002486 | -0.002481 | -0.000005 | 0.385750 | 30.444510 |
| S0-R-JM2C | RESPONSE | 0.033852 | 0.034232 | -0.000380 | 0.385750 | 36.397080 |
| S0-R-JM2C | TAIL | -0.000048 | -0.000049 | 0.000001 | 0.002191 | 0.022660 |
| S1-R-JM2C | PRE_READ | 0.101412 | 0.102536 | -0.001124 | 0.446760 | 10.320080 |
| S1-R-JM2C | READ | 0.151472 | 0.152613 | -0.001140 | 1.531660 | 81.001840 |
| S1-R-JM2C | RESPONSE | -0.034508 | -0.034896 | 0.000388 | 1.531660 | 83.197563 |
| S1-R-JM2C | TAIL | 0.000424 | 0.000430 | -0.000006 | 0.008942 | 0.087510 |
| S0-J-JM2C | PRE_READ | -0.101394 | -0.102518 | 0.001124 | 0.446656 | 10.314320 |
| S0-J-JM2C | READ | -0.002457 | -0.002452 | -0.000005 | 0.385683 | 30.477790 |
| S0-J-JM2C | RESPONSE | 0.033858 | 0.034238 | -0.000380 | 0.385683 | 36.426440 |
| S0-J-JM2C | TAIL | -0.000048 | -0.000049 | 0.000001 | 0.002189 | 0.022660 |
| S1-J-JM2C | PRE_READ | 0.101415 | 0.102539 | -0.001124 | 0.446764 | 10.315040 |
| S1-J-JM2C | READ | 0.134874 | 0.135983 | -0.001109 | 1.496526 | 77.649790 |
| S1-J-JM2C | RESPONSE | -0.034537 | -0.034925 | 0.000388 | 1.496526 | 77.649790 |
| S1-J-JM2C | TAIL | 0.000477 | 0.000483 | -0.000006 | 0.008564 | 0.088660 |

- `abs(V)>1 µV` 的 two-consecutive-sample onset 只作为描述性活动定位；不能单独证明完整 2π switching，也不能作为 SFQ event count。

## 5. OBSERVED S0/S1 BVM state and sensing

- `S0-R-JM2C`：BVMout RESPONSE 的 Δphase=0.000382 turns，V-area=0.000396 turns，V p2p=0.070996 mV；完整 JM1/JM2/JS1/JS2 的 P/V/I 与 L_M path 已写入 `metrics.json`。
- `S1-R-JM2C`：BVMout RESPONSE 的 Δphase=-0.000325 turns，V-area=-0.000339 turns，V p2p=0.188758 mV；完整 JM1/JM2/JS1/JS2 的 P/V/I 与 L_M path 已写入 `metrics.json`。
- `S0-J-JM2C`：BVMout RESPONSE 的 Δphase=0.000402 turns，V-area=0.000416 turns，V p2p=0.070900 mV；完整 JM1/JM2/JS1/JS2 的 P/V/I 与 L_M path 已写入 `metrics.json`。
- `S1-J-JM2C`：BVMout RESPONSE 的 Δphase=-0.000277 turns，V-area=-0.000290 turns，V p2p=0.218177 mV；完整 JM1/JM2/JS1/JS2 的 P/V/I 与 L_M path 已写入 `metrics.json`。

## 6. OBSERVED omitted-versus-connected A/B

- 各 condition 的 `BVM_INTERNAL_STATE`、`BVM_SENSING`、`QB`，以及 JTL case 的 `JTL_TRANSPORT` 都使用相同的旧图布局、命名和 signal order 生成 A/B comparison。
- A/B 页面中的差值约定为 connected − omitted；phase comparison 显示为 turns。具体逐窗口 max/RMS/P95、时间网格和相关系数见 `metrics.json`。
- A-side 的四条 L_M 电流 probe 缺失是不可恢复的历史观测限制；本轮不重跑 A-side，因此没有把缺失列插值或补成零。

## 7. OBSERVED QB response

- `S0-R-JM2C`：QB BJ2 RESPONSE 的 Δphase=0.000525 turns，V-area=0.000539 turns，residual=-0.000014 turns；这是 local QB phase/area evidence，不自动等价于下游收到的 SFQ。
- `S1-R-JM2C`：QB BJ2 RESPONSE 的 Δphase=1.999431 turns，V-area=1.999418 turns，residual=0.000014 turns；这是 local QB phase/area evidence，不自动等价于下游收到的 SFQ。
- `S0-J-JM2C`：QB BJ2 RESPONSE 的 Δphase=0.000808 turns，V-area=0.000826 turns，residual=-0.000018 turns；这是 local QB phase/area evidence，不自动等价于下游收到的 SFQ。
- `S1-J-JM2C`：QB BJ2 RESPONSE 的 Δphase=0.999168 turns，V-area=0.999151 turns，residual=0.000018 turns；这是 local QB phase/area evidence，不自动等价于下游收到的 SFQ。

## 8. OBSERVED JTL transport

- JTL case 的六级 B01/B02 P/V 均已读取并进入 standalone 与 A/B comparison；逐级 phase-area 数值及活动定位见 `metrics.json`。
- 本轮只做固定 fixture 的描述性 transport observation；没有将局部 phase turns 直接升级成 event count 或系统 Gate。

## 9. INFERENCE

- 这个 single-BVM historical fixture 可以被用于回答“仅恢复 JM2 intended series connection 后，局部 JM2、BVM sensing、QB 和负载路径发生了什么变化”。
- 如果 connected 与 omitted 的差异集中在 JM2 及其耦合到的下游波形，这与“连接状态是影响因素”相容；但这是单变量 task-local 对照，不足以确定唯一物理机制。

## 10. UNKNOWN / NOT PROVEN

- 未证明 canonical BVM 兼容性、4-BVM/多状态行为、参数或 bias margin、timestep convergence、T1 兼容性或论文机制身份。
- 未证明 JM2 的任何局部相位变化就是完整 SFQ，也未用本轮结果证明系统逻辑成功。
- A-side 缺失 L_M path probe；JM2 connection 的内部电流差异不能在四条 path 上做完整历史 A/B 数值比较。

## 11. Reasonable next options (not executed)

1. 用户先审阅四个 JM2-connected run 的 standalone 图与八张 A/B 对照图。
2. 如仍需解释机制，另行授权一个严格单变量、预注册的局部 follow-up。
3. 如需更高等级结论，另行设计 Candidate/Authority 级验证；本轮不自动进入。

## 当前状态

`AWAITING_USER_REVIEW`；`user_reviewed=false`；`next_step_authorized=false`；`automatic_next_experiment=false`。
