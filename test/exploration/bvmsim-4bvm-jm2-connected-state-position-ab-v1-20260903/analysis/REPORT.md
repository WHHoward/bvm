# JM2-connected 4-BVM 六状态 A/B Quick 报告

## 首要问题与边界

本轮优先回答：一个 one-hot active BVM 是否会把其他 commanded-0、且在本轮
task-local retention criterion 下稳定的 BVM 的 READ-associated response 拉离
`0000`，以及该 cross-coupling 在 JM2 omitted/connected 之间如何变化；
`I(LIN|XBQ1)` 的 position dependence 是并列问题。A/B 只改变 BVM include。

原始差分是 `X(one-hot)-X(0000)`。为避免将 WRITE1 后残留误写成 READ 因果，另
报告以各自 `PRE_READ1` median 中心化后的 difference-in-differences。`READ0`
发生在 WRITE1 之前，是负控制；本实验没有 READ=0/no-read 控制，因此 centered
结果仍是 READ-associated/state-conditioned evidence，不是唯一因果证明。

## 关键观察（Observed / Derived）

- 六个 connected raw 的 artifact QA 为 `ARTIFACT_VALID`，且这不是物理 PASS。
- connected one-hot 的 READ1 `I(LIN|XBQ1)` raw 峰值 spread 为 131.8 uA（60.69–192.5 uA）；`V(QBIN)` spread 为 0.5497 mV。
- 12 个 one-hot→commanded-0 pair 中，connected state-conditioned READ1 Delta I 的 12 个超过 1 uA 描述性 floor；这 12 个 victim 的 PRE_READ1→TAIL retention 均稳定，故本轮可称为 task-local retention-stable；最大 Delta I 为 93.3 uA（1000/BVM2）。
- 同一批 pair 的 connected state-conditioned READ1 Delta V_SL max_abs 为 0.5525–2.816 mV；最大值 2.816 mV（0001/BVM1）。
- 12 个 Delta I 的 JM2 connected-vs-omitted `max_abs` 关系为 SIMILAR=4, SMALLER_CONNECTED=4, LARGER_CONNECTED=4；12 个 Delta V_SL 的关系为 SIMILAR=8, SMALLER_CONNECTED=0, LARGER_CONNECTED=4。两者都只是此 fixture 的描述，方向没有预先假定。
- BJ2 READ1 clean-separated event count 为 {'0000': 0, '1000': 0, '0100': 0, '0010': 0, '0001': 0, '1111': 0}，六状态均为 0；strict local diagnostic 的 continuous multi-turn running 出现在 1000, 0010, 0001, 1111，因此不能把 BJ2 的累计 turns 当作 SFQ 事件数。
- READ0 被作为 WRITE1 前的负控制；centered difference 与原始 state-conditioned difference 都保留，避免把 WRITE1 后状态偏移误写成唯一 READ 因果。

## Zero-cell READ1 response

下表展示 state-conditioned `Delta I_LSL` 的 `max_abs`，单位 uA；对应的
`Delta V_SL`、centered difference、signed integral、RMS、onset 和 timing 在
`analysis/metrics.json`。每一行是 4×3 矩阵中的一个 pair，不池化。

| one-hot | zero BVM | JM2 omitted | JM2 connected | connected vs omitted | abs-peak time change (ps) |
|---|---:|---:|---:|---|---:|
| 1000 | BVM2 | 100.2 | 93.3 | SIMILAR | 0.2 |
| 1000 | BVM3 | 80.07 | 78.9 | SIMILAR | 1.2 |
| 1000 | BVM4 | 53.15 | 54.88 | SIMILAR | 0 |
| 0100 | BVM1 | 97.58 | 84 | SMALLER_CONNECTED | 0.9 |
| 0100 | BVM3 | 41.49 | 49.92 | LARGER_CONNECTED | 5.3 |
| 0100 | BVM4 | 27.63 | 34.92 | LARGER_CONNECTED | 0.2 |
| 0010 | BVM1 | 51.61 | 62.01 | LARGER_CONNECTED | -7.3 |
| 0010 | BVM2 | 73.83 | 86.42 | LARGER_CONNECTED | 7.6 |
| 0010 | BVM4 | 66.27 | 45.95 | SMALLER_CONNECTED | -0.6 |
| 0001 | BVM1 | 69.65 | 76.16 | SIMILAR | -1.6 |
| 0001 | BVM2 | 84.36 | 76.16 | SMALLER_CONNECTED | -3.4 |
| 0001 | BVM3 | 81.34 | 66.94 | SMALLER_CONNECTED | 2.9 |

## Position-dependent QB input

`metrics.json` 同时保存四个 one-hot 的 raw `V(QBIN)`/`I(LIN|XBQ1)`、各侧
`one-hot-0000` 校正值和 omitted/connected 对照。所有逐点比较均要求 exact time
grid，未做插值。它们是波形统计，不能作为 SFQ count。

## QB/JTL

下表是 connected B02 的 strict local diagnostic clean-separated event count，
只作局部相位/事件结构观察，绝不等同于整条链的 transport count。

| state | JTL1 | JTL2 | JTL3 | JTL4 | JTL5 | JTL6 |
|---|---:|---:|---:|---:|---:|---:|
| 0000 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1000 | 0 | 0 | 0 | 0 | 1 | 2 |
| 0100 | 0 | 0 | 0 | 0 | 0 | 1 |
| 0010 | 0 | 0 | 0 | 0 | 0 | 2 |
| 0001 | 0 | 0 | 0 | 0 | 2 | 3 |
| 1111 | 0 | 0 | 0 | 0 | 0 | 4 |

同一 junction 的 phase displacement 与 voltage area 在 `metrics.json` 的 `qb`
和 `jtl` 中对齐；JoSIM `P(...)` 是 rad，turns 只由 continuous unwrap 后除以
`2*pi` 得到。phase/area、local activity 和下游身份匹配必须分开看。

## 全时窗 selectivity diagnostic

为检查 spontaneous/extra activity，BJ2 和 JTL 的 B01/B02 都按同一个共享
strict-event-list helper 扫描 `PRE/WRITE0/READ0/WRITE1/READ1/TAIL`；下表为
BJ2 的 `clean-separated/complete-segment` 数，完整的 BJ2/JTL 逐支路记录在
`metrics.json` 的 `strict_by_window` 中。它们仍是 post-hoc local diagnostic，
不是 SFQ 或 transport Gate。

| state | PRE | WRITE0 | READ0 | WRITE1 | READ1 | TAIL |
|---|---:|---:|---:|---:|---:|---:|
| 0000 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| 1000 | 0/0 | 0/0 | 0/0 | 0/0 | 0/1 | 0/0 |
| 0100 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| 0010 | 0/0 | 0/0 | 0/0 | 0/0 | 0/1 | 0/0 |
| 0001 | 0/0 | 0/0 | 0/0 | 0/0 | 0/1 | 0/0 |
| 1111 | 0/0 | 0/0 | 0/0 | 0/0 | 0/1 | 0/0 |

## 证据分层

- **Observed**：六个 B-side raw、四组控制、每个 BVM 内部 P/V/I 和 SL telemetry、
  所有 sensing endpoint、QBin/QBout/Lin、QB branch、六级 JTL B01/B02 P/V。
- **Derived**：同侧 raw delta、PRE_READ1-centered difference-in-differences、
  position baseline correction、same-JJ phase-area、strict local diagnostic、
  QB KCL residual、A/B numeric relations。
- **Inference（有边界）**：非零 zero-cell delta 表示在此历史 shared network 中
  可以观察到 one-hot-conditioned 的 commanded-0、retention-stable victim response；A/B 大小关系只属于
  这个 fixture，不能升级为机制或普适结论。
- **Unknown**：connected-side 是否满足真正存储语义、canonical BVM、single-BVM、
  timestep convergence、process margin、paper mechanism identity 和系统 SFQ
  一一对应传输。

## 当前处置

本轮保持 `NO_CLEAR_STRICT_CLASSIFICATION` / `QUICK_AMBIGUOUS`，没有把任何
phase/area/local activity 变成 Gate，也没有执行下一项实验。
