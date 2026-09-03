# FOUR_BVM_MATRIX

范围：historical BVMSim 4-BVM accumulated sensing line → BVMSim-compatible QB → six-stage JTL；只改变 RJ1 与 `.tran` timestep。有效 four-BVM raw 是每个 run 的 `attempt-03`，`attempt-01`/`attempt-02` 保留为探针不完整或路径失败的历史尝试。

`READ1_RESPONSE` 为 `[110,170)` ps。`BJ1/BJ2/JTL` 的 net turns 是窗口端点轨迹，不是 SFQ count；event 列只来自同一 JJ、同一连续单调 segment 的 phase/area/retrap 检查。

| RJ1 (ohm) | timestep (ps) | BJ1 net trajectory (turns) | BJ2 net trajectory (turns) | late BJ2 complete / candidate* | JTL1 B02 (net; complete/clean) | JTL6 B02 (net; complete/clean) | branch observation |
|---:|---:|---:|---:|---|---|---|---|
| 12 | 0.1 | 4.001028 | 3.999517 | 0/0 | 4.000090; 1/0 | 4.000000; 4/4 | `CONTINUOUS_MULTI_TURN_BRANCH` |
| 12 | 0.05 | 4.999671 | 4.998204 | 0/1 | 5.000094; 1/0 | 5.000000; 5/5 | `CONTINUOUS_MULTI_TURN_BRANCH` |
| 12 | 0.025 | 5.002894 | 4.999188 | 0/1 | 5.000146; 1/0 | 5.000000; 5/5 | `CONTINUOUS_MULTI_TURN_BRANCH` |
| 12 | 0.0125 | 5.003345 | 4.999092 | 0/1 | 5.000163; 1/0 | 5.000000; 5/5 | `CONTINUOUS_MULTI_TURN_BRANCH` |
| 11.5 | 0.1 | 4.001279 | 3.999495 | 0/0 | 4.000095; 1/0 | 4.000000; 4/4 | `CONTINUOUS_MULTI_TURN_BRANCH` |
| 11.5 | 0.05 | 4.003263 | 3.999545 | 0/0 | 4.000143; 1/0 | 4.000000; 4/4 | `CONTINUOUS_MULTI_TURN_BRANCH` |
| 11.5 | 0.025 | 5.002935 | 4.999000 | 0/1 | 5.000153; 1/0 | 5.000000; 5/5 | `CONTINUOUS_MULTI_TURN_BRANCH` |
| 11.5 | 0.0125 | 5.003004 | 4.999247 | 0/1 | 5.000137; 1/0 | 5.000000; 5/5 | `CONTINUOUS_MULTI_TURN_BRANCH` |
| 11 | 0.1 | 4.000865 | 3.999584 | 0/0 | 4.000085; 1/0 | 4.000000; 4/4 | `CONTINUOUS_MULTI_TURN_BRANCH` |
| 11 | 0.05 | 4.003284 | 3.999459 | 0/0 | 4.000152; 1/0 | 4.000000; 4/4 | `CONTINUOUS_MULTI_TURN_BRANCH` |
| 11 | 0.025 | 5.002851 | 4.999050 | 0/1 | 5.000142; 1/0 | 5.000000; 5/5 | `CONTINUOUS_MULTI_TURN_BRANCH` |
| 11 | 0.0125 | 5.002333 | 4.999239 | 0/1 | 5.000118; 1/0 | 5.000000; 5/5 | `CONTINUOUS_MULTI_TURN_BRANCH` |

## 关键观察（pre-review）

- 三个 RJ1 在 0.025/0.0125 ps 的 BJ2 都是约 4.023–4.024 turn 的主连续 segment；READ1 净轨迹约 4.999 turn。两者不能互换为“四个/五个 SFQ”。
- RJ1=12 在 0.1 ps 约 4-turn、0.05 ps 已约 5-turn；RJ1=11.5 和 11 在 0.1/0.05 ps 约 4-turn，但在两个 fine timestep 也约 5-turn。变化首先已出现在 BJ1/BJ2 的 QB-level trajectory，不能归因于 JTL 图形 alone；因果机制仍未知。
- fine pair 的 strict complete/clean count、极性、late-complete presence、主 event phase/area/onset 与六级 B02 count sequence 需见 `analysis/RJ1_ROBUSTNESS_SUMMARY.md`；这只是 exploratory engineering comparison，不是 convergence proof。
- fine BJ2 principal 后仍有一个 sub-unit late candidate（约 0.97 turn 量级），但没有被 strict complete 标为额外完整 event；因此不能写成“late excursion 消失”。表中的 candidate* 使用 `0.2` turn 描述阈值，仅为 post-hoc descriptive aid，不是预注册接受标准。

## Boundary

该表不证明 canonical BVM、single-BVM full six-stage Gate、paper mechanism identity 或 process margin；最终分类待 Sol XHigh reviewer。
