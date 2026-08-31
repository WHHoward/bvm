# 实验定位表

下表将用户要找的实验描述映射到本分享包和仓库原始目录。每一项都保留了 matched controls；只复制了关键图，不把所有重复 dashboard 放进分享包。

| 编号 | 对应实验 | 分享包目录 | 仓库原始目录 | 拓扑/输入 | 原实验结论边界 |
|---|---|---|---|---|---|
| 1 | 9 ps，BVM 连接 12 个 JJ | [`01_9ps_bvm_12jj_source`](experiments/01_9ps_bvm_12jj_source/) | `test/exploration/paper-sl-l0-20260824/` | BVM `SL → 12×jjmit area=3.2 → ground`；READ 为 9 ps（96–105 ps） | `PAPER_JSL_LOAD_VALID`，仅 external-series-load fixture |
| 2 | 13 ps，BVM 连接 12 个 JJ | [`02_13ps_bvm_12jj_source`](experiments/02_13ps_bvm_12jj_source/) | `test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/` | BVM `SL1 → 12×jjmit area=3.2 → ground`；READ 为 13 ps（96–109 ps） | READ 语义审计通过；source-only，联合 physical BVM→JSL→QB 在该实验中未执行 |
| 3 | 13 ps，BVM 连接 8 个 JJ | [`03_13ps_bvm_8jj_physical`](experiments/03_13ps_bvm_8jj_physical/) | `test/exploration/bvm-jsl8-500-physical-qb-recheck-v1-20260824/` | BVM `SL → 8×jjmit area=5（约500 µA）→ QB IN → 10 Ω` | 物理 recheck；报告使用 `PHYSICAL_BACKACTION_PREVENTS_CLOSURE` 边界 |
| 4 | 9 ps，12-JJ BVM 输出理想重放到 QB | [`04_9ps_12jj_ideal_replay_to_qb`](experiments/04_9ps_12jj_ideal_replay_to_qb/) | `test/exploration/paper-sl-q1-20260824/`；源数据来自 `paper-sl-l0-20260824` | 将 12-JJ 源实验的 `I(B_LD1)` 原样 replay 到 frozen scaled QB；无整形/归一化/重采样 | `PAPER-SL_QB_SUBTHRESHOLD`；是理想 waveform compatibility，不是 physical interface evidence |
| 5 | 13 ps，12-JJ BVM 输出理想重放到 QB | [`05_13ps_12jj_ideal_replay_to_qb`](experiments/05_13ps_12jj_ideal_replay_to_qb/) | `test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/` | 使用 13 ps 12-JJ source 的 `I(B_LD1)` 原时间网格、原极性、原幅值 replay 到 frozen scaled QB | 13 ps 是本 frozen fixture 的首个 selective 1/0/0 candidate；不能升级为 physical SFQ delivery |
| 6 | 9 ps，BVM 和 QB 直接相连 | [`06_9ps_bvm_to_qb_direct`](experiments/06_9ps_bvm_to_qb_direct/) | `test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/` | `BVM SL1 → QB IN`，无中间 JSL/conditioner/termination | `QB_SOURCE_BACKACTION_FAILURE`；保留了四个 matched cases |
| 7 | 13 ps，BVM 和 QB 直接物理相连 | [`07_13ps_bvm_to_qb_direct_physical`](experiments/07_13ps_bvm_to_qb_direct_physical/) | `test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/` | 仓库中的 13 ps 实现是 `BVM SL → 12×jjmit area=3.2 JSL → QB IN`；不是无 JSL 的 `SL1→QB` | `PHYSICAL_BACKACTION_PREVENTS_CLOSURE`；不是 successful closure |

## 关键图的位置

- 9 ps 12-JJ source：`01.../plots/overview.html`
- 13 ps 12-JJ source：`02.../plots/source-width-comparison.html`
- 13 ps 8-JJ physical：`03.../plots/13ps-matched-cases.html`、`13ps-bjl2-phase-area-evidence.html`
- 9 ps ideal replay：`04.../plots/qb-replay/comparison.html`
- 13 ps ideal replay：`05.../plots/qb-replay-width-comparison.html`
- 9 ps direct BVM→QB：`06.../plots/overview.html`
- 13 ps physical BVM→JSL→QB：`07.../plots/13ps-matched-cases.html`、`13ps-source-before-vs-after-qb-loading.html`

关键原始数据都在各实验目录的 `raw/`，对应网表在 `inputs/`，运行日志在 `logs/`，分析摘要在 `analysis/`。

