# EVENT_COUNT_CONVERGENCE

本 Quick 的关键边界：`net turns` 不是 SFQ event count。event count 使用 shared `bvmtools.sfq.strict_event_list` 的同一 JJ、同一连续单调 segment、同 segment `∫Vdt/Phi0`、相位 delta、方向和 retrap/bounded interval。

## 矩阵摘要

| timestep | BJ2 READ net turns | BJ2 complete segments | BJ2 clean separated events | JTL1 B01 net turns | JTL1 B01 clean | JTL1 local stage min | JTL6 local stage min | classification |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0.1 ps | 3.999517 | 1 | 0 | 4.000387 | 1 | 0 | 3 | CONTINUOUS_MULTI_TURN_RUNNING_STATE |
| 0.05 ps | 4.998204 | 1 | 0 | 4.999847 | 0 | 0 | 2 | CONTINUOUS_MULTI_TURN_RUNNING_STATE |
| 0.025 ps | 4.999188 | 1 | 0 | 4.999830 | 0 | 0 | 2 | CONTINUOUS_MULTI_TURN_RUNNING_STATE |
| 0.0125 ps | 4.999092 | 1 | 0 | 4.999803 | 0 | 0 | 2 | CONTINUOUS_MULTI_TURN_RUNNING_STATE |
| 0.1 ps | 3.999517 | 1 | 0 | 4.000387 | 1 | 0 | 3 | CONTINUOUS_MULTI_TURN_RUNNING_STATE |

## 重点 Observed

- T100 的 BJ2 READ1 主段约为 4 turns；T050/T025/T0125 的 BJ2 READ1 净位移约为 5 turns，但这些细网格 run 的 BJ2 仍是一个约 4-turn 的连续主段加一个不足 1 turn 的后续段，而不是五个 clean separated events。
- 细网格 run 的 JTL6 B02 可以出现五个约单位量级的完整段；这不等于 BJ2 已经产生五个 clean events。表中的 JTL1/JTL6 数值只是 B01/B02 的本地 stage summary，不是经过 event identity matching 的 transported count。
- T100_FULL 的 45 ps 之后轨迹用于检查 print-start；它与 T100 一致时，print-start 不是解释 4→5 的充分原因。

## 4→5 的当前证据边界

**Observed:** 净相位分支随 `.tran` 从 0.1 ps 变为 0.05/0.025/0.0125 ps 而改变，并在更细三个网格保持接近 5；历史/T100 保持接近 4。

**Derived but not yet accepted:** 在 fixture、source waveform、bias、load、拓扑和 solver binary 均固定且 T100/T100_FULL/T025 对照成立的前提下，这与 timestep-conditioned numerical branch-change candidate 一致。T050/T025/T0125 在约 5-turn 轨迹上具有定性稳定性，但这不是 timestep convergence proof，也不能排除数值积分路径或非线性分支选择。它更不能被改写成“4→5 个 SFQ”，因为 BJ2 的多-turn 主段没有 retrap 分隔。

**Sol XHigh review 后仍 Unknown:** 这种 branch change 是否应被解释为有物理意义的 operating branch，还是数值积分路径/吸引域切换；以及不同 junction 上的第五候选是否具有可配对的 event identity。

## 必须回答的问题

1. 历史 BVMSim JTL1 B01 是否约 4 turns：是，且 new T100 逐点复现；这只是净位移。
2. Stage-A 0.025 ps 是否约 5 turns：是，new T025 与 Stage-A S1 一致；这只是净位移。
3. T100 是否回到约 4 turns：是。
4. 第五候选段的描述性顺序在哪里：见 `metrics.json:event5_candidate_ladder`；该表按 junction 和固定展示顺序列出候选，不表示起源、前驱或因果顺序，且不能称为第五 clean BJ2 event。
5. JTL 是否生成第五个还是仅传播：当前各 junction 的本地 phase/area 候选没有完成 event identity matching，因此既不能声称已传播，也不能排除 JTL 内部本地生成或重整形。
6. event count 是否收敛：净 turns 在细网格具有定性稳定性，但没有预注册的误差阶/停止带，也没有形成“四个/五个”BJ2 收敛结论；必须以各 junction 计数表为准。
7. 应信任 4、5 还是 INCONCLUSIVE：净相位分支可报告为历史/T100≈4、细网格≈5；作为 clean SFQ event count 或机制结论，当前应保持 INCONCLUSIVE/受 reviewer 限制。
