# BVM_LOAD_QB_STRICT_EVENT_RECLASSIFICATION_V1

## 状态：`STRICT_EVENT_RECLASSIFICATION_COMPLETE`

本报告只对 `bvm-load-qb-matrix-v1-20260901` 已存在的 raw CSV 做确定性后处理；没有新的 JoSIM 运行，也没有改变 BVM、JSL、QB、读时序或拓扑。

## Provenance

- `LEGACY_NEW_SOURCE_IDENTITY = PASS`
- `LEGACY_NEW_REPLAY_FIXTURE_EQUIVALENCE = PASS`
- 旧 9 ps replay raw 与新矩阵对应 raw 的 BJL2 P/V/I 数值等价：`PASS`。
- `SERIES_JSL_CURRENT_EQUIVALENCE = PASS`（逐支路绝对电流容差 `1.0e-13 A`）。

## BJL2 strict 主结果（logical1 + READ）

| Width | JSL | Ideal replay strict BJL2 | Physical strict BJL2 |
|---|---|---|---|
| 9 ps | 12x320 | `SUBTHRESHOLD`; segment 0.892527234 turn; area 0.892537009 Phi0; n=0 | `SUBTHRESHOLD`; segment -0.104071401 turn; area -0.104078803 Phi0; n=0 |
| 9 ps | 8x500 | `SUBTHRESHOLD`; segment 0.877365815 turn; area 0.877377688 Phi0; n=0 | `SUBTHRESHOLD`; segment -0.146871253 turn; area -0.146879579 Phi0; n=0 |
| 13 ps | 12x320 | `CLEAN_ONE_SFQ_CANDIDATE`; segment 1.01602892 turn; area 1.01603683 Phi0; n=1 | `SUBTHRESHOLD`; segment -0.1221278 turn; area -0.122131039 Phi0; n=0 |
| 13 ps | 8x500 | `SUBTHRESHOLD`; segment 0.973287067 turn; area 0.973297156 Phi0; n=0 | `SUBTHRESHOLD`; segment -0.124996234 turn; area -0.125006108 Phi0; n=0 |

## 全部 32 个 replay/physical case 的分类计数

| classification | count |
|---|---:|
| `CLEAN_ONE_SFQ_CANDIDATE` | 1 |
| `SUBTHRESHOLD` | 31 |

## READ0 / no-read control gate

下表每格依次为 `largest segment / same-segment area / activity complete count`；这是控制检查，不使用 VOUT p2p。

| fixture | width | JSL | logical0 READ | logical1 READ=0 | logical0 READ=0 |
|---|---:|---|---|---|---|
| replay | 9 | 12x320 | -0.0301612304 / -0.0301655671 / n=0 | -2.5050988e-05 / -2.5054962e-05 / n=0 | 2.50350725e-05 / 2.50412226e-05 / n=0 |
| replay | 9 | 8x500 | -0.0409945414 / -0.0409990658 / n=0 | 2.00535228e-06 / 1.9954837e-06 / n=0 | -2.02126778e-06 / -2.00865099e-06 / n=0 |
| replay | 13 | 12x320 | -0.0257304046 / -0.0257324853 / n=0 | -2.5050988e-05 / -2.5054962e-05 / n=0 | 2.50350725e-05 / 2.50412226e-05 / n=0 |
| replay | 13 | 8x500 | -0.0409945414 / -0.0409990658 / n=0 | 2.00535228e-06 / 1.9954837e-06 / n=0 | -2.02126778e-06 / -2.00865099e-06 / n=0 |
| physical | 9 | 12x320 | -0.0216702506 / -0.021673069 / n=0 | 8.89676132e-06 / 8.88711337e-06 / n=0 | -8.83309934e-06 / -8.82885707e-06 / n=0 |
| physical | 9 | 8x500 | -0.026383656 / -0.0263872135 / n=0 | -2.14859173e-06 / -2.13893309e-06 / n=0 | 2.18042272e-06 / 2.16979484e-06 / n=0 |
| physical | 13 | 12x320 | -0.018375791 / -0.0183770255 / n=0 | 8.89676132e-06 / 8.88711337e-06 / n=0 | -8.83309934e-06 / -8.82885707e-06 / n=0 |
| physical | 13 | 8x500 | -0.0230093803 / -0.0230112653 / n=0 | -2.14859173e-06 / -2.13893309e-06 / n=0 | 2.18042272e-06 / 2.16979484e-06 / n=0 |

`CONTROL_EVENT_VIOLATION`：`否`；控制 complete BJL2 event 数为 0 个 case。

完整逐 case 数值在 `analysis/strict-event-summary.csv`；每段边界、POST 计数、tail boundedness、raw QA 和信号 provenance 在 `analysis/strict-event-details.json`。

## 判据边界

- `window_phase_delta_turns` 只是 activity 窗口首末端点的连续相位位移；`WINDOW_PHASE_DISPLACEMENT != EVENT_COUNT`。
- 事件 authority 只使用同一个 `BJL2` 的 continuous unwrapped phase、实际 CSV 时间上的同段 `∫Vdt/Φ0`、signed residual、complete segment 数和 POST bounded/retrap。
- 没有使用 VOUT peak/p2p、I>Ic、whole-window phase delta、phase p2p 或 `fast_events` 作为 single-SFQ 判据。
- physical row 仍是加载后的 BVM→JSL→QB raw 观察；replay row 是理想 `I_REPLAY` fixture。严格分类不等于系统级 SFQ delivery，也不等于 JTL/T1 证据。

## 对任务问题的直接回答

1. 新矩阵 9 ps / 12x320：ideal replay 的 BJL2 最大连续单调段为约 `0.892527 turn`，同段 area 约 `0.892537 Phi0`，没有 complete BJL2 event；physical 也没有。
2. 约 `1.002 turn` 的 summary window displacement 与 `0.8925 turn` strict segment 可以同时成立，因为前者是 `[94,130)` 首末端点差，后者是窗口内最大的连续单调 excursion；中间包含 reversal/retrace，不能把端点差当作事件计数。
3. 9 ps / 8x500 ideal replay：`SUBTHRESHOLD`，最大段约 `0.877366 turn`；physical 同样 `SUBTHRESHOLD`。
4. 13 ps / 12x320 ideal replay：复现历史 `CLEAN_ONE_SFQ_CANDIDATE`，BJL2 段约 `1.016029 turn`、area 约 `1.016037 Phi0`，且没有第二个 complete segment。
5. 13 ps / 8x500 ideal replay：`SUBTHRESHOLD`，最大段约 `0.973287 turn`；尚未跨过 1-turn complete 判据。
6. 四个 physical logical1_read：全部 `SUBTHRESHOLD`，没有 complete BJL2 event。
7. 所有 logical0_read 和两个 no-read controls：complete count 全为 0，没有 `CONTROL_EVENT_VIOLATION`。
8. 从 9 ps 到 13 ps 的 strict boundary 在当前 ideal replay 的 `12x320` load 上存在（SUBTHRESHOLD → CLEAN_ONE candidate）；不是两个 load 都同时存在的普适 boundary。
9. 该 boundary 不同时存在于 `8x500`：9/13 ps 两个点都为 `SUBTHRESHOLD`。physical 两个 load 也都没有建立 one-quantum candidate。
10. window-level activity 是 `window_phase_delta_turns` 等端点/范围诊断；strict BJL2 authority 只来自连续单调 segment、同段 signed phase/area、complete count、第二段和 post boundedness。

## Source/JSL 等价性

共检查 16 个 source case；每个 load 的全部系列支路都与 `I(B_LD1)` 逐样本比较（含 max、RMS、p95 abs difference）。`SERIES_JSL_CURRENT_EQUIVALENCE = PASS`，逐支路绝对电流容差为 `1.0e-13 A`；明细在 `analysis/jsl-series-current-equivalence.csv`。

## Regression

- regression status: `PASS`。
- 9 ps / 12x320 replay 锚点应保持约 `0.892527 / 0.892537 turn` 且无 complete event；13 ps 锚点应保持约 `1.016029 / 1.016037 turn` 且为 clean-one candidate。

## Observed / Derived / Inference / Unknown

### Observed

- 以上表格和 CSV 是从当前矩阵 raw 直接计算的 segment 与面积数值；图仅标出关键 BJL2 轨迹和边界。
- 输入 raw 的 CSV 时间轴保留其实际采样点；若存在非均匀 gap，QA 中显式记录，未重采样。

### Derived

- `CLEAN_ONE_SFQ_CANDIDATE` 是本任务冻结判据下的 local BJL2 candidate，不是已经通过 JTL、T1 或 system Gate 的 SFQ delivery。
- `OVERDRIVEN_ONE_PLUS_RESIDUAL` 只描述单个完整段超过 clean upper band；不把前级 BJs/JSL 局部活动直接升级为 downstream event。

### Inference

- 本任务只解决窗口位移与连续单调事件段之间的 metric-semantics ambiguity，不据此提出新的物理机制或下一参数族。

### Unknown

- 单次 raw、当前 timestep 和有限 POST 窗口不能建立无限时间稳定性或收敛 Gate。
- BVM source loading/back-action 的机制解释、JTL/T1 接收和 magnetic coupling 均不在本任务范围内。
