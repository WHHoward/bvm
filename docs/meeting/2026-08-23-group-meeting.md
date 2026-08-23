# 组会汇报 — 2026-08-23

> **汇报周期**：2026-08-15 → 2026-08-23
>
> **上次汇报**：[2026-08-14 组会材料](2026-08-14-group-meeting.md)
>
> **当前 HEAD**：`2622201e7e6ab72ce2a5066ccdbf3fd1c0ea65d7`
>
> **一句话主线**：本周期把问题从“BVM 是否有可观察 readout”推进到“如何把已经确认的 BVM/B_TRIG nonlinear information 转换成一个有源、受限、可被 SFQ backend 接收的事件”。BVM source/read discrimination、R0b local detector、standard JTL positive control 和 DCSFQ controlled regenerative mechanism 均已建立；但 canonical BVM 到 JTL/DCSFQ 的直接路径，以及当前 R15-B active interstage 单点，仍未形成完整 BVM→SFQ 事件。

> **证据边界**：本文严格区分 observed、derived、inference 和 unknown。所有 phase 数均来自 JoSIM raw `P()` 的 rad→turn 换算；同一 JJ、同一端点、同一方向、同一窗口的 voltage-area 才用于 phase consistency。local JJ phase transition 不自动等于 SFQ delivery、fluxoid transition 或 downstream JTL reception。

## 1. 与上次组会相比的主要变化

| 上次组会状态                                                                                | 当前状态                                                                                                                       |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| BVM-S0 fixed-fixture source observations，scientific disposition 为`VALID + INCONCLUSIVE` | 完成 stable-load bounded characterization，并冻结 BVM logical semantics；仍不声称 universal source baseline                    |
| 尚未授权 receiver route                                                                     | 完成 R0b 到 R15B 的 receiver Exploration chain                                                                                 |
| receiver 问题尚未拆分                                                                       | 已将问题拆成 detector、passive transfer、temporal dwell、backend regeneration、active interstage 五层                          |
| BQ/DCSFQ/JTL 只有历史或校准 evidence                                                        | standard JTL positive control、DCSFQ 300 µA controlled local event、B_OUT conditioned local slip 均已按新 phase/area 口径复核 |
| 尚无 downstream evidence                                                                    | direct JTL、canonical DCSFQ cascade、R15-B active interstage 均未产生可接受的 B3/JTL event                                     |

## 2. BVM source 与 logical semantics

### 2.1 Stable-load characterization

在上次 S0 之后完成了固定 `dt=0.0125 ps` 的 16-run load/polarity/read-control characterization：

- load 为 `1 / 12 / 25 / 50 Ω`；
- positive/negative source polarity 均覆盖；
- read 与 matched READ=0 control 成对运行；
- netlist、command、raw CSV、analysis 和 provenance 均保存。

该阶段提供了 fixed-load、fixed-timestep 下的 bounded source facts，但没有把 S0 提升为 resolution-independent source model。exact endpoint-V/I token diagnostic 也没有完全支持；VIZ-002 的后续图形化尝试被停止，visualization 不作为 scientific Gate。

### 2.2 Logical semantics 冻结

[BVM logical semantics v1](/home/howard/JoSIM/docs/research/BVM_LOGICAL_SEMANTICS_V1.md) 已冻结：

- logical 1：正向 write initialization；
- logical 0：负向 write initialization；
- canonical `+READ`：正向 WL+SE read stimulus；
- logical 1：strong R-loop nonlinear/multi-turn response；
- logical 0：no-running，主要保留 READ-edge response。

当前 source-side facts：

| quantity             |         logical 1 |                 logical 0 |
| -------------------- | ----------------: | ------------------------: |
| `V(SL)` scale      |    约`0.904 mV` |            约`0.317 mV` |
| `V(N6)` scale      |    约`1.814 mV` |            约`0.653 mV` |
| output-current scale |      约`75 µA` |              约`26 µA` |
| JS1/JS2              | strong multi-turn | 约 0 turn / edge response |

必须继续保留的边界是：phase turns 不是 SFQ count；单个 JJ 的 phase 也不是闭合环 fluxoid count。

## 3. R0：SL → B_TRIG 已完成 local trigger closure

### R0-A 修正

初始 SL trigger 已实现 read1/read0 threshold discrimination，但 read1 activity range 只有约 `0.5845 turn`，net phase 和同 JJ voltage area 约 `0.01231 turn`，因此原先的 complete-switching 结论被降级为：

`R0-A threshold discrimination PASS`；`R0-B complete trigger NOT YET`。

### R0b closure

随后冻结：

- canonical SL route；
- `R_IN=12 Ω`；
- `B_TRIG AREA=.50`；
- bias `+15 µA`。

结果：

| case                | B_TRIG 最大 continuous monotonic segment |
| ------------------- | ---------------------------------------: |
| logical1 + READ     |                        约`4.997 turns` |
| logical0 + READ     |                        约`0.185 turns` |
| 两个 READ=0 control |                        无完整 transition |

read1 phase trajectory 与同一 JJ、同一 segment 的 voltage area 一致，完成 R0b complete-trigger criterion。

R0b 证明的是：

> canonical SL 可以驱动一个强 state-dependent local nonlinear detector。

R0b 没有证明：

- exactly-one output；
- self-quench；
- downstream SFQ delivery；
- JTL/T1 reception。

## 4. R1/R2：passive/direct receiver 的证据链

### 4.1 Parallel feedback branch

最初的 parallel `L_Q-R_Q` branch 建立了明确 tradeoff：

- `R_Q=15 Ω`：branch peak 约 `34.74 µA`，B_TRIG 约 `0.212 turn`；
- `R_Q=100 Ω`：branch peak 约 `7.80 µA`，B_TRIG 约 `0.342 turn`；
- `R_Q=1 kΩ`：branch peak 约 `1.71 µA`，B_TRIG 约 `0.920 turn`。

强 transfer branch 会压制 trigger，弱 branch 保留 trigger 但 transfer 不足。该 tested topology 被停止，不把它升级为整个 direct family 的 universal impossibility。

### 4.2 R1a passive pickup

冻结 topology：

```text
BVM SL → R_IN → series L_TX → B_TRIG
                         │
                         K
                         │
                    L_SEC → R_SEC_LOAD
```

参数：`L_TX=.20 pH`、`K=.80`、`L_SEC=2 pH`、`R_SEC_LOAD=12 Ω`。

| quantity                |            read1 |            read0 |
| ----------------------- | ---------------: | ---------------: |
| B_TRIG complete segment | `3.94377 turn` | `0.18476 turn` |
| secondary current       |    `5.564 µA` |    `1.144 µA` |
| secondary voltage       |    `66.77 µV` |    `13.72 µV` |

secondary ratio 约 `4.865`。结论为 `R1a passive extraction PASS`：被动 pickup 可以传递 state selectivity，但不能自动提供 active gain。

### 4.3 B_OUT activation 与 R2

common-mode B_OUT topology 中，`V(N_OUT)` 跟随 `V(N_SEC)`，所以 `V(B_OUT)` 维持 numerical zero；该接口被明确判为不适合作为 activation interface。

改为 differential B_OUT 后：

- read1 有 signal response，但初始 phase 只有约 `0.022 turn`；
- AREA `.10 → .08` 无明显改善；
- bias `6–10 µA` 无 complete event；
- K 增大只能单调提高 sub-turn activity，K=.95 的 read1 最大 segment 仍约 `0.0261 turn`。

R2 进一步区分了 amplitude 与 dwell：在特定 direct-drive fixture 中，约 `4.5 µA` effective drive 的 flat-top hold 从 0/5/10/20 ps 改变时，B_OUT 最大 segment 约为：

|  hold |   最大 segment |
| ----: | -------------: |
|  0 ps | `0.124 turn` |
|  5 ps | `0.170 turn` |
| 10 ps | `0.971 turn` |
| 20 ps | `1.004 turn` |

20 ps point 具备 same-JJ phase/voltage-area consistency、retrap 和 bounded post behavior；R2-G 进一步显示该 conditioned fixture 可重复 local one-slip。

这只建立了 fixture-specific fact：

> B_OUT 在人为 conditioning 的约 `4.5 µA / 20 ps` drive 下可以完成 local slip。

它不是 BVM raw secondary 的 threshold，也不是 downstream SFQ delivery。

## 5. R3–R5：从 onset、capture 到 reduced quantizer

| 阶段 | 主要实验                      | 结果                                                                                  | 边界                                                    |
| ---- | ----------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| R3-A | `1 fF C_ON` onset extractor | read1 `                                                                               | I(C_ON)                                                 |
| R4-A | weak-mutual passive capture   | read1/read0 transient separation 存在，但无 persistent read1 fluxoid-state transition | 降级当前 passive single point，不否定整个 mutual family |
| R5-A | reduced biased quantizer      | read1 有 large bounded nonlinear/plasma oscillation，无 SET event                     | amplitude activity 不等于 escape                        |
| R5-B | direct SET shunt              | 主要增加 damping/current diversion，仍为 bounded oscillation                          | 否定当前 shunt hypothesis                               |
| R5-C | 正确 nonlinear saddle         | saddle 可被跨越，但没有 complete local event；read1 back-action 明显                  | 停止 reduced quantizer bias/K/L tuning                  |

R5-C 的核心修正是：

> static saddle crossing 不是 complete phase transition 的充分条件。

## 6. R6–R10：native QB、隔离与 load-line routing

### 6.1 Native QB direct coupling

canonical SL 直接接 native paper-QB 时：

- read1 在 BJs/BJL1/BJL2 中有明显、强于 read0/control 的 nonlinear activity；
- 但 JS1/JS2 post-state 出现约 −3-turn 级 disturbance；
- 没有 complete BJL2 event。

主 verdict 为 `BACK_ACTION_FAILURE`，次级 observation 为 `STATE_SELECTIVE_QB_ACTIVITY`。

### 6.2 Weak transformer isolation

R6-A 用 weak inductive isolation 恢复了 canonical source behavior：

- read1/read0 QB activity separation 约 `3.6–3.8×`；
- JS1/JS2 相对 canonical baseline 的 post disturbance 明显降低；
- BJL2 最大 segment 约 `0.001585 turn`，没有 local pass。

R6-B 改 winding ratio 后：

- `I(L_SEC)` read1 excursion 约 `9.667→18.816 µA`；
- `V(L_SEC)` 约 `53.79→64.44 µV`；
- `I(Lin)` 约 `20.566→26.787 µA`；
- BJs/BJL1 activity 增加；
- BJL2 最大 segment 仍约 `0.001588 turn`。

结论：`DRIVE_GAIN_WITH_ISOLATION_PRESERVED`，但没有进入 BJL2 quantization regime。

### 6.3 L1/L2 routing 与 output class

R7-A：`L1:3.91→2.50 pH` 后：

- `G_L2` 增加约 `25.9%`；
- `G_BJL2` 增加约 `26.2%`；
- BJL2 最大 segment 约 `0.001886 turn`；
- BJL2 settled current 反而下降，因此 gain 不是简单 DC bias 靠近 `Ic`。

R8：BJL2 AREA `1.89→.70` 只产生小幅 activity gain，没有 threshold-like jump，read0 也 co-amplify。

R9-A：`L2:3.91→2.50 pH` 后：

- `G_L2` 再增加约 `35.2%`；
- `G_BJL2` 再增加约 `36.6%`；
- read0 也近似同步放大；
- BJL2 最大 read1 segment 仍只有约 `0.00226 turn`。

因此 passive L1/L2 routing tuning branch 已结束：routing gain 已建立，但没有 quantization gain。

### 6.4 Local BJL2 bias routing

R10-A 的 output-side local bias branch 使 read1/read0/control 都进入 multi-turn running：

- 最大 segment 约 `2.18 turns`；
- post-window 约 `8 turns`；
- 无 retrap；
- source guard 失败。

结论：`BACK_ACTION_OR_NONSELECTIVE_FAILURE`。该单点不能被解读为所有 bias-routing 结构均不可行，但关闭了当前 local-BJL2 bias sweep。

## 7. R11–R14：standard JTL、DCSFQ 和 temporal conditioning

### R11-A：canonical BVM direct JTL

使用仓库 `circuits/standard/JTL.cir` 的两个标准 JTL cells：

- positive-control source 可使四颗 JTL JJ 完成预期 propagation；
- phase 与 same-JJ voltage-area 一致；
- 无 free-running。

canonical BVM 直接 galvanic 接入同一条 JTL chain 时，read1 第一颗 JTL JJ 最大单调 excursion 仅约 `0.151 turn`，没有第一颗完整 event。

结论：`NO_JTL_TRIGGER`。这是 direct compatibility screening failure，不是 JTL fixture failure。

### R12-A：historical DCSFQ_BVM re-audit

Phase A controlled cases：

| controlled input | B3 result                                        |
| ---------------: | ------------------------------------------------ |
|        `0 µA` | 无完整 event                                     |
|     `68.4 µA` | 无完整 event                                     |
|      `300 µA` | 约`1.03-turn` bounded local regenerative event |

这证明 frozen DCSFQ_BVM 在强 controlled input 下具有 local regenerative mechanism。

canonical BVM cascade `SL→DCSFQ_BVM→two-cell JTL` 中：

- read1 B3 仅约 `0.0365 turn`；
- read1 > read0 >> controls；
- 无 B3 local quantization；
- 无 JTL propagation。

主结论为 `DCSFQ_BVM_NO_TRIGGER`，不是 converter mechanism 不存在。

### R13-A：ideal rectification/hold requirement test

从 R12 actual input replay，并分别测试：

- raw replay；
- favorable-polarity rectification；
- amplitude-preserving 20 ps hold；
- rectification + 20 ps hold。

四种输入均保持 sub-turn B3 activity，无 complete event、无 free-running。结论为：

`TEMPORAL_CONDITIONING_INSUFFICIENT`

即理想 polarity/dwell conditioning 在不增加 active energy 的情况下仍不足以驱动 frozen DCSFQ。

### R14-A：passive interstage analytic precheck

R1a secondary 只有约：

- `I_SEC≈5.564 µA`；
- `|V_SEC|≈66.77 µV`。

optimistic loaded DCSFQ input estimate 约 `9.77 µA`；即使按 3 ps sanity timescale 也只有约 `19.1 µA`。

与 DCSFQ evidence 对照：

| reference                            | result                         |
| ------------------------------------ | ------------------------------ |
| `68.4 µA` controlled              | 无完整 B3 event                |
| `110.2 µA` canonical read1 replay | 无完整 B3 event                |
| `300 µA` controlled               | 约`1.03-turn` B3 local event |

R14 verdict：`PRECHECK_NO_GO`。缺失功能被进一步定位为 detector→regenerator 的 active/regenerative interstage energy transfer。

## 8. R15：bias-powered active interstage

### 8.1 R15-A topology closure failure

AFQ-3 nominal point 使用三个强耦合 winding，但设定 `K_QCTL=0`。该 normalized mutual matrix determinant 为负，constitutive matrix 非 positive definite。

因此 R15-A 在 Gate 0 被判：

`PRECHECK_NO_GO`

该结果是 magnetic topology/model closure failure，不是 AFQ active-stage physics failure；没有运行 scientific cases。

### 8.2 R15-B corrected split-winding topology

采用 split-winding/two-core correction：

- `L_FQ=L_FO=20 pH`；
- `R_F=20 Ω`；
- `K_QFQ=+0.90`；
- `K_FOCTL=-0.90`；
- `K_QCTL=K_FQFO=0`。

analytic matrix 为 positive definite，随后执行四个 matched cases。首先运行 `logical1 + READ=0` control，确认没有 startup/free-running 后继续其他 cases。

#### Detector 保持

| case              | B_DET 最大 monotonic segment |
| ----------------- | ---------------------------: |
| logical1 + READ   |            `3.913019 turn` |
| logical0 + READ   |            `0.184906 turn` |
| logical1 + READ=0 |                 无完整 event |
| logical0 + READ=0 |                 无完整 event |

因此 Stage 1 `DETECTOR_PRESERVED` 成立。

#### Active stage 未形成

J_SET/J_Q/J_OUT 在四个 case 中的 phase segments 基本相同，主要是共同 startup/settling trajectory；没有 read1-selective bounded active sequence。

frozen DCSFQ input `I(L1)` 在四个 case 中几乎完全相同：

- peak 约 `0.511 µA`；
- 不高于 R1a passive secondary 的 `5.564 µA`；
- B3 最大 segment 约 `0.0000577 turn`；
- 无 complete B3 event。

R15-B execution verdict：

`ACTIVE_STAGE_NO_TRIGGER`

source disposition 为：

`BOUNDED_EXTRA_BACK_ACTION_NOT_ISOLATED`

READ=0 control 稳定、没有 free-running，logical storage sign 保持；但 read1 post-window 的 SL/N6/JS ringing 高于 canonical no-receiver baseline。因此不能称为 source-isolated success。

详细报告：[R15-B execution report](/home/howard/JoSIM/test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/analysis/R15B_EXECUTION_REPORT.md)。

## 9. 当前已建立、推断与未知

### Observed

- BVM logical 1/0 readout 在固定条件下具有稳定 state-dependent separation；
- R0b B_TRIG read1 有约 5-turn complete local detector response；
- R1a passive pickup 保留 read1/read0 separation，但只有 single-digit µA output；
- B_OUT 在人为 conditioned direct drive 下可完成 local slip + retrap；
- DCSFQ_BVM 在 300 µA controlled input 下可产生约 1.03-turn bounded B3 local event；
- standard two-cell JTL positive control 有效；
- canonical BVM direct JTL、canonical DCSFQ cascade、R15-B active stage 均没有建立 downstream event。

### Derived

- current bottleneck 不是“BVM 没有 discrimination”；
- passive transformer、简单 rectification、hold、L1/L2 routing、单点 output bias 均没有提供足够的 threshold-like nonlinear gain；
- DCSFQ backend 的 local mechanism 在 controlled strong drive 下存在；
- R15-B 的实际 current steering 没有把 B_DET state 转换成后端可见的 active drive。

### Inference

当前最有证据支持的机制假设是：

```text
BVM → B_DET
       ↓
active state compression / refractory regeneration
       ↓
frozen DCSFQ_BVM
       ↓
standard JTL
```

其中 active stage 必须由独立 bias 提供能量，同时保留 read1/read0 discrimination、避免 R0b multi-turn 直接复制，并限制 R10 式 free-running/back-action。

这是下一阶段的 architecture hypothesis，不是已验证事实。

### Unknown

- active interstage 能否在单点条件下形成 selective one-shot sequence；
- 是否能同时达到足够 DCSFQ drive 和可接受 BVM source isolation；
- J_SET/J_Q/J_OUT 的失败是 coupling、state-compression、operating-point 还是 current-steering topology 问题；
- 最终能否形成 exactly-one B3 event 并传播到 JTL；
- 是否需要重新设计 native QB/DCSFQ front stage。

## 10. 路线状态

| 路线                                  | 当前状态                      | 说明                                             |
| ------------------------------------- | ----------------------------- | ------------------------------------------------ |
| BVM source/read semantics             | bounded facts established     | 不升级为 universal source baseline               |
| SL → B_TRIG detector                 | local detector established    | read1 multi-turn，不是 one-shot                  |
| bare secondary → B_OUT               | downgraded tested instance    | raw transfer/dwell 不足                          |
| passive pickup/transformer            | useful extraction control     | state selectivity 有，active gain 无             |
| 1 fF capacitive onset                 | falsified tested instance     | fast spike 无 sustained drive                    |
| weak-mutual passive capture           | falsified tested single point | 无 persistent state                              |
| reduced biased quantizer              | stopped                       | saddle crossing 后仍无 complete event            |
| native paper-QB direct                | downgraded                    | state-selective activity，但 back-action failure |
| isolated native QB routing            | downgraded                    | isolation/routing gain，BJL2 不量化              |
| local BJL2 bias point                 | falsified tested point        | nonselective/free-running                        |
| direct canonical BVM → JTL           | compatibility fail            | positive control valid，BVM no trigger           |
| frozen DCSFQ controlled input         | local mechanism established   | 300 µA controlled positive point                |
| canonical BVM → DCSFQ → JTL         | no trigger                    | read1 separation存在但无 B3/JTL event            |
| ideal rectification/hold              | insufficient                  | 仍需 active energy transfer                      |
| R15-B AFQ split-winding point         | single-point fail             | topology valid，active stage no trigger          |
| active regenerative interstage family | not falsified                 | 当前仍是机制级候选，不应盲扫参数                 |

## 11. 当前结论与下一 Gate

目前最重要的结论不是“某个后端参数还没有调好”，而是：

> detector discrimination、passive signal extraction 和 backend local regeneration 已分别被建立；缺少的是一个能够从 B_DET 的 nonlinear information 中提取有限状态、并由独立 bias 提供实际能量的 active interstage。

R15-B 说明 corrected magnetic constitutive topology 可以运行，但本 single point 没有形成 J_SET/J_Q/J_OUT 的 active state-compression sequence。后续若继续，首要问题应限定为：

1. active stage 的 detector→relay 因果 transfer 是否真的存在；
2. first transition 后是否有 refractory/self-quench 机制；
3. 该机制是否在 read0/READ=0 下保持零事件；
4. 是否能把 DCSFQ input 从 `0.511 µA` 量级提升到具有物理意义的 active-drive 量级；
5. 是否同时满足 source/back-action guard。

不应继续无边界 sweep L1/L2/K/AREA/bias，也不应在没有 B3 local event 前接 JTL/T1。

## 12. 仍未完成的系统目标

- canonical BVM → exactly-one local output event；
- read0/READ=0 zero event；
- B3 exactly-one event；
- standard JTL propagated event；
- T1 input/计数；
- full BVM storage-preserving receiver Gate；
- Candidate 或 paper-level quantitative claim。

## 13. 关键证据索引

- [上次组会材料](2026-08-14-group-meeting.md)
- [BVM logical semantics v1](/home/howard/JoSIM/docs/research/BVM_LOGICAL_SEMANTICS_V1.md)
- [R15-B execution report](/home/howard/JoSIM/test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/analysis/R15B_EXECUTION_REPORT.md)
- R0b：`fc0f3d9466ff1533ec9f85e83a82c3503b961c16`
- R1a：`df115dd0720a068314a01605e0b97353ddbb54b1`
- R2-F/R2-G：`830f568` / `c683cf5`
- R3-A：`4842bc7d20c755a28b2cf1a0683fbf81051173bd`
- R5-C：`4d8dfaa32be4ca8955128eb05c3b043f5149b41d`
- R6-A/R6-B：`c6cdd5672e1ba457cf4c7da8e05c2757def7ccdd` / `a32c341766150e532a2e097f8c2573eb532748ce`
- R7-A/R8/R9-A/R10-A：`3d8414c` / `edf3226` / `3339459` / `6c25305`
- R11-A/R12-A/R13-A/R14-A：`ca610ce` / `ebe2498` / `abad1d4` / `3113a46`
- R15-A/R15-B：`571fa918f9623e24ea8038bfb24c32087494316e` / `2622201e7e6ab72ce2a5066ccdbf3fd1c0ea65d7`

---

## 一句总结

本周期已经证明：BVM 能稳定提供 state-dependent nonlinear source，B_TRIG 能被完整触发，DCSFQ 和 JTL 各自也有独立 positive control；但现有 passive、direct、native-QB routing、temporal-only 和 R15-B single-point active interstage 均尚未把这条 source chain 闭合为可传输的 exactly-one SFQ event。当前科学瓶颈是 **B_DET → bias-powered active state compression/regeneration**，而不是继续盲调后端 passive load-line。
