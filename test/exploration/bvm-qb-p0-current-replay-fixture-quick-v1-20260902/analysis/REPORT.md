# Analysis report — BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1

生成时间：`2026-09-02T12:03:50+08:00`；artifact status：`VALID`；fixture：`CURRENT_REPLAY_FIXTURE_QUALIFIED`；Quick：`QUICK_PROMISING`。

## 1. Provenance and scope

- 新 science run：仅 `RP/run-01`，runner exit=0；P0/I0 raw 均复用，不重跑。
- solver：`build/josim-cli v2.7.2837d13`；`.tran 0.0125p 170p`。
- RP deck：`inputs/rp_p0_current_replay.cir`；literal PWL pairs=18 per continuation line is the formatting block size, not a resampling operation.
- 物理路径：P0 是 BVM→12×320 JSL→QB；RP 是 current-only ideal source→同一 QB；I0 是既有 ideal replay reference。

## 2. Input replay fidelity

| item | value |
|---|---:|
| P0 samples | 13599 |
| RP samples | 13599 |
| exact time grid | `True` |
| max abs error | 0 µA |
| RMS error | 0 µA |
| correlation | 1 |
| signed area difference | 0 A·ps |
| positive area difference | 0 A·ps |
| negative area difference | 0 A·ps |
| fidelity disposition | `PASS` |

面积是同一输入波形的 waveform diagnostic；它不是 SFQ quantity。若本节失败，则不解释下列 W3/W4。

## 3. W2 PRE state

判定：`PASS`；current max-abs limit=0.01 µA，phase max-abs limit=0.001 turns。

| signal | unit | max abs difference | pass |
|---|---|---:|---|
| `I(BJL1|XBQ)` | uA | 0 | `PASS` |
| `I(L1|XBQ)` | uA | 0 | `PASS` |
| `I(RB|XBQ)` | uA | 0 | `PASS` |
| `I(L2|XBQ)` | uA | 0 | `PASS` |
| `I(BJL2|XBQ)` | uA | 0 | `PASS` |
| `P(BJS|XBQ)` | turns | 7.590895e-10 | `PASS` |
| `P(BJL1|XBQ)` | turns | 0 | `PASS` |
| `P(BJL2|XBQ)` | turns | 0 | `PASS` |

phase 在每个 case 内先完整 continuous unwrap，再用各自 W2 median 居中；没有以 active/read response 设阈值。

## 4. W3/W4 trajectory closure

公式：`C_x = RMS(RP-P0) / RMS(I0-P0)`；reference gap floor 按单位固定。当前 summary：nondegenerate=14，pass=14，max Cx=1.7781171e-07。

| window | signal | unit | RMS(RP-P0) | RMS(I0-P0) | Cx | Cx status |
|---|---|---|---:|---:|---:|---|
| W3_read | `P(BJS|XBQ)` | turns | 1.5959873e-07 | 2.2451992 | 7.108444e-08 | `DEFINED` |
| W3_read | `I(BJL1|XBQ)` | uA | 4.5205088e-06 | 25.42301 | 1.7781171e-07 | `DEFINED` |
| W3_read | `P(BJL1|XBQ)` | turns | 1.03858e-08 | 0.5191118 | 2.0006866e-08 | `DEFINED` |
| W3_read | `I(L1|XBQ)` | uA | 1.0164994e-06 | 28.375444 | 3.5823206e-08 | `DEFINED` |
| W3_read | `I(L2|XBQ)` | uA | 1.5275252e-06 | 28.375445 | 5.3832644e-08 | `DEFINED` |
| W3_read | `I(BJL2|XBQ)` | uA | 9.1287093e-07 | 25.1613 | 3.6280754e-08 | `DEFINED` |
| W3_read | `P(BJL2|XBQ)` | turns | 2.5164606e-09 | 0.43001073 | 5.8520879e-09 | `DEFINED` |
| W4_post_read_observation | `P(BJS|XBQ)` | turns | 2.9771476e-07 | 13.936859 | 2.1361683e-08 | `DEFINED` |
| W4_post_read_observation | `I(BJL1|XBQ)` | uA | 2.1404322e-06 | 12.549513 | 1.7055899e-07 | `DEFINED` |
| W4_post_read_observation | `P(BJL1|XBQ)` | turns | 2.074601e-09 | 1.0509721 | 1.9739828e-09 | `DEFINED` |
| W4_post_read_observation | `I(L1|XBQ)` | uA | 9.0381137e-07 | 10.040924 | 9.0012773e-08 | `DEFINED` |
| W4_post_read_observation | `I(L2|XBQ)` | uA | 8.0583807e-07 | 10.040924 | 8.0255373e-08 | `DEFINED` |
| W4_post_read_observation | `I(BJL2|XBQ)` | uA | 9.3541435e-07 | 10.496099 | 8.9120192e-08 | `DEFINED` |
| W4_post_read_observation | `P(BJL2|XBQ)` | turns | 1.1936621e-09 | 1.028053 | 1.16109e-09 | `DEFINED` |

Supporting currents (`I(RJ1)`, `I(RB)`, `I(RJ2)`, `I(L0)`) are retained in `metrics.json`; they are not added to the compact plot or promotion criterion。

## 5. BJL2 strict local result

| case | classification | largest segment | phase delta (turns) | same-segment area (Phi0) | residual (turns) | complete n | second complete | post bounded |
|---|---|---|---:|---:|---:|---:|---|---|
| P0 | `SUBTHRESHOLD` | [106.525, 109.6875] ps | -0.1221278 | -0.12213104 | 3.2387138e-06 | 0 | False | PASS |
| RP | `SUBTHRESHOLD` | [106.525, 109.6875] ps | -0.1221278 | -0.12213104 | 3.2382121e-06 | 0 | False | PASS |
| I0 | `CLEAN_ONE_SFQ_CANDIDATE` | [103.0375, 110.175] ps | 1.0160289 | 1.0160368 | -7.9115381e-06 | 1 | False | PASS |

P0↔RP strict local closure：`PASS`；classification match=`True`；same-segment phase/area/endpoint differences 分别为 0 turns、5.0167233e-10 Φ0、0 ps。
- 该表沿用 shared `StrictLocalEventSpec`/`strict_event_summary`：activity `[95,115) ps`，post `[115,130) ps`，tail `[125,130) ps`；local compatibility 不是 SFQ count、downstream delivery 或 system Gate。

## 6. KCL

实现：`scripts/bvmtools/kcl.py`；全 case/window/equation status=`PASS`，tolerance=0.001 µA。四条方程、每个窗口的 max/p95/RMS 在 `metrics.json` 中完整保留。

## 7. Strict-anchor regression

既有 9 ps / 13 ps replay anchors：`PASS`；该检查只消费历史 strict summary，不重跑历史 raw。13 ps I0 当前复算也列在该字段中。

## 8. Evidence labels

### Observed

- RP 是唯一新增 JoSIM raw；P0/I0 raw、QB/JJ snapshots 和现有 9/13 ps strict anchor 均保留。
- CSV 时间列、信号列、raw hash、runner command/exit、solver provenance 和唯一 plot 输入/输出均有记录。

### Derived

- 输入误差、PRE 差异、W3/W4 RMS、Cx、KCL residual 和同一 BJL2 的 phase/area 数值均由 raw 直接计算；没有插值。
- 相位报告统一为 continuous unwrap(raw radians)/(2π) turns；图只显示关键数据。

### Inference

- 在本次冻结条件下，fixture disposition 是 `CURRENT_REPLAY_FIXTURE_QUALIFIED`；这只回答 current-only replay 是否可作为隔离夹具。

### Unknown / not proven

- 没有证明物理 BVM→QB route 已解决，没有证明 source impedance 是唯一机制，没有证明 SFQ delivery、硬件行为、timestep convergence 或 Formal Gate。

## 9. Visualization and stop

- 唯一图：`test/exploration/bvm-qb-p0-current-replay-fixture-quick-v1-20260902/plots/RESULT_OVERVIEW.html`；`CLASSIC_LOCKED`，`sep_comb/dark/-j 2pi`，7 groups / 21 key traces。
- 最终 workflow：`AWAITING_USER_REVIEW`，`STOP`；user_reviewed=false，next_step_authorized=false，automatic flags=false。
