# JM2-connected single-BVM R-loop / SL observability

## 1. Question

本轮只建立 isolated historical single-BVM 的 branch-level reference，回答 S0/S1 的 R-loop、SE、RSL/SL 支路如何分配；不测试 array。

## 2. Probe-only nature

两个 executed deck 均由旧 `S0-J-JM2C` / `S1-J-JM2C` 机械继承。唯一改变是新增 direct branch current/voltage `.print`，以及因 executed deck 搬到 `runs/<condition>/` 而做 include path relocation。静态归一化物理差异为 0。

## 3. What changed / what did not change

保留 JM2-connected variant、12-JJ terminal sensing line、原始 `BVMSim/BQ.cir`、六级 280-uA JTL、10-ohm load、WL+BL WRITE、WL+SE READ、0.1-ps step 和 200-ps stop。没有使用 canonical BVM，也没有做参数或 timestep sweep。

## 4. Artifact validity

总体分析状态：`ANALYSIS_VALID`。每个 run 的 raw、deck、log、metadata hash 和 post-run QA 见 `metrics.json`。JoSIM 的实际保存网格为 0 到 199.9 ps；`.tran 0.1p 200p` 的 200 ps 是 stop horizon。

| run | artifact | time grid | protocol | old probe parity |
|---|---|---|---|---|
| S0-J-RLOOP | `ARTIFACT_VALID` | `True` | `PROTOCOL_VALID` | `EXACT` |
| S1-J-RLOOP | `ARTIFACT_VALID` | `True` | `PROTOCOL_VALID` | `EXACT` |

### Tooling incidents

本轮记录了 3 个工具层 incident：首次 run.sh 的 metadata 参数分隔符、首次 analyzer 的路径变量、首次 renderer 的 comparison map 结构。它们均未修改 raw、未改变 deck、未导致 physics rerun；修复后分别对同一 raw 或同一 plot 输入重做 QA。

## 5. Topology and sign convention

元件电流方向按 netlist 的第一个节点到第二个节点；元件电压为同一方向的 V(first)-V(second)。实际 JM2-connected variant 的 endpoint 已在 static preflight 中记录。直接元件电压 probe 被 JoSIM 的 hierarchical device lookup 接受，因此本轮没有使用 node-difference fallback。

关键闭合式包括：`I(B_JM1)+I(R_JM1)-I(L_M1)`；`I(B_JS1)+I(L_PSE)-I(R_S)-I(L_S3)`；`I(R_S)+I(L_S3)+I(B_JS2)-I(L_PSL)`；以及 `I(L_PSL)-I(R_SL)`、`I(R_SL)-I(L_SL)`。完整系数和每个窗口的 residual 在 `metrics.json`。

## 6. Observed branch reference

下面只列 READ 窗口的关键量级；完整的 PRE_READ、READ、EARLY_RESPONSE、TAIL、FULL 统计均保存在 `metrics.json`。电流为 uA，电压为 mV；signed integral 的单位按字段标注。

| run | branch | I mean (uA) | I max_abs (uA) | V mean (mV) | V max_abs (mV) |
|---|---|---:|---:|---:|---:|
| S0-J-RLOOP | RJM1 | -0.32624 | 37.0791 | -0.00260992 | 0.296633 |
| S0-J-RLOOP | LM3 | 14.5109 | 37.2083 | — | — |
| S0-J-RLOOP | RS | 0.112782 | 17.7524 | 0.000338344 | 0.0532573 |
| S0-J-RLOOP | LS3 | 48.4279 | 69.9776 | 0.000338344 | 0.0532573 |
| S0-J-RLOOP | RSE | 83.3333 | 100 | 1.66667 | 2 |
| S0-J-RLOOP | LPSE | 83.3333 | 100 | -2.82599e-17 | 0.075 |
| S0-J-RLOOP | RSL | 1.80487 | 19.4776 | 0.0216584 | 0.233732 |
| S0-J-RLOOP | LSL | 1.80487 | 19.4776 | -0.000385577 | 0.0200635 |
| S1-J-RLOOP | RJM1 | -0.948616 | 53.8348 | -0.00758892 | 0.430678 |
| S1-J-RLOOP | LM3 | 86.7364 | 229.802 | — | — |
| S1-J-RLOOP | RS | -1.27542 | 55.2142 | -0.00382626 | 0.165642 |
| S1-J-RLOOP | LS3 | 57.6871 | 196.53 | -0.00382626 | 0.165642 |
| S1-J-RLOOP | RSE | 83.3333 | 100 | 1.66667 | 2 |
| S1-J-RLOOP | LPSE | 83.3333 | 100 | -9.53416e-17 | 0.075 |
| S1-J-RLOOP | RSL | 31.187 | 60.441 | 0.374244 | 0.725291 |
| S1-J-RLOOP | LSL | 31.187 | 60.441 | -0.000465164 | 0.0387524 |

## 7. RJM1 split, RS||LS3 split, and RSL branch

RJM1 的 current split 由 `I(L_M1)` 与 `I(B_JM1)`/`I(R_JM1)` 的方向一致性检查给出；RS/LS3 的 fraction 仅在 `|I(RS)+I(LS3)| > 1 uA` 时计算，是描述性比值，不是 gate。RSL 的 voltage/current/dissipation 以及 RSE、RS、RJM1 的 READ energy 也只用于本 fixture 的量级比较。

| run | KCL equation | READ max_abs residual (uA) | READ RMS residual (uA) |
|---|---|---:|---:|
| S0-J-RLOOP | JM1_shunt_node7 | 0.0001 | 3.47766e-05 |
| S0-J-RLOOP | SE_RLOOP_node6 | 1e-05 | 3.692e-06 |
| S0-J-RLOOP | RLOOP_output_node10 | 1e-05 | 4.10381e-06 |
| S0-J-RLOOP | SL_series_node12 | 0 | 0 |
| S1-J-RLOOP | JM1_shunt_node7 | 1e-05 | 4.3107e-06 |
| S1-J-RLOOP | SE_RLOOP_node6 | 7e-05 | 2.3626e-05 |
| S1-J-RLOOP | RLOOP_output_node10 | 8e-05 | 2.13041e-05 |
| S1-J-RLOOP | SL_series_node12 | 0 | 0 |

## 8. OBSERVED / DERIVED / INFERENCE / UNKNOWN

**Observed:** 两个 raw 都包含完整 direct passive branch current/voltage、原有 JJ/QB/JTL probe；S0/S1 stimulus 按旧 deck 实际输出；old probe 与新 raw 的时间网格可逐点对照。

**Derived:** KCL residual、series-current difference、RS fraction、V×I / I²R energy、L×I flux linkage 和 0.5×L×I² stored-energy 是由同一 raw 的数值后处理得到的描述量。`L×I` 不被命名为 trapped Phi0。

**Inference ceiling:** 这些数据可作为下一轮 4-BVM 对照时的 isolated branch reference，尤其是同名层级下的方向和 KCL schema；不能单独推断 array isolation、cross-coupling root cause、论文机制或 SFQ transport。

**Unknown:** 本轮未运行 4-BVM selective-read/all-one/additivity/isolation，因此 single reference 是否能预测 array 行为仍未知；也未对 RJ1、bias、timestep 或任何参数做稳健性测试。

## 9. Visualization

每个 standalone 页面均使用 `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`；P 列仅做 rad/(2*pi) 数值转换并标成 turns，不是 SFQ count。

- S0 plots: `plots/runs/S0-J-RLOOP/`
- S1 plots: `plots/runs/S1-J-RLOOP/`
- comparison: `plots/comparison/`

## 10. Future 4-BVM comparison

未来 array deck 应按 `experiment.yaml` 中冻结的 `BVM_SINGLE_ARRAY_BRANCH_V1` schema，将 `XBVM1` 替换为相应 `XBVM<n>`，保留同一套串联 branch probes、端点方向和 KCL 方程。该规则只登记 schema，本轮没有建立或运行 4-BVM。

## 11. Human gate

`AWAITING_USER_REVIEW`；`user_reviewed: false`；`next_step_authorized: false`；`automatic_next_experiment: false`；`next_action: STOP`。
