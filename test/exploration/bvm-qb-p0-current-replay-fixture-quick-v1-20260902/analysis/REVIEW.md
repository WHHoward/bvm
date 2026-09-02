# Independent review — BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1

审查时间：`2026-09-02T12:03:47+08:00`；方式：stdlib CSV + 独立直接算术；不运行 JoSIM。

总体验证：`PASS`。

## 检查范围

- 检查 P0/RP exact time grid、literal input replay 误差和样本数。
- 独立重算 W2 PRE 电流/phase 差异，以及 W3/W4 primary trajectory Cx。
- 检查 P0/I0/RP raw hash 和没有额外 JoSIM run 的目录事实；不修改 raw。

| check | result | key value |
|---|---|---:|
| `literal_input_replay` | `PASS` | `0.0` |
| `PRE current I(BJL1|XBQ)` | `PASS` | `0.0` |
| `PRE current I(L1|XBQ)` | `PASS` | `0.0` |
| `PRE current I(RB|XBQ)` | `PASS` | `0.0` |
| `PRE current I(L2|XBQ)` | `PASS` | `0.0` |
| `PRE current I(BJL2|XBQ)` | `PASS` | `0.0` |
| `PRE phase P(BJS|XBQ)` | `PASS` | `7.590895010752496e-10` |
| `PRE phase P(BJL1|XBQ)` | `PASS` | `0.0` |
| `PRE phase P(BJL2|XBQ)` | `PASS` | `0.0` |
| `closure W3_read P(BJS|XBQ)` | `PASS` | `7.108444018816139e-08` |
| `closure W4_post_read_observation P(BJS|XBQ)` | `PASS` | `2.1361683011918142e-08` |
| `closure W3_read I(BJL1|XBQ)` | `PASS` | `1.7781170681383778e-07` |
| `closure W4_post_read_observation I(BJL1|XBQ)` | `PASS` | `1.7055898950876475e-07` |
| `closure W3_read P(BJL1|XBQ)` | `PASS` | `2.0006865874341754e-08` |
| `closure W4_post_read_observation P(BJL1|XBQ)` | `PASS` | `1.973982847522113e-09` |
| `closure W3_read I(L1|XBQ)` | `PASS` | `3.5823206242021164e-08` |
| `closure W4_post_read_observation I(L1|XBQ)` | `PASS` | `9.001277263839752e-08` |
| `closure W3_read I(L2|XBQ)` | `PASS` | `5.3832644243697e-08` |
| `closure W4_post_read_observation I(L2|XBQ)` | `PASS` | `8.025537296408001e-08` |
| `closure W3_read I(BJL2|XBQ)` | `PASS` | `3.6280754018440715e-08` |
| `closure W4_post_read_observation I(BJL2|XBQ)` | `PASS` | `8.912019227332058e-08` |
| `closure W3_read P(BJL2|XBQ)` | `PASS` | `5.85208789347532e-09` |
| `closure W4_post_read_observation P(BJL2|XBQ)` | `PASS` | `1.1610900282369999e-09` |

## 审查边界

本复核确认的是算术、exact-grid 和 provenance 一致性；strict BJL2 标签仍是同一 JJ 的 local phase/area compatibility，不能解释为 SFQ count、downstream delivery 或 system Gate。
