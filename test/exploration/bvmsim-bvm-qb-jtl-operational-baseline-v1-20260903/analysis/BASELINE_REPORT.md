# Historical BVMSim operational baseline V1 — execution report

> 生成时间：2026-09-03T14:48:03+08:00。本报告只解释本实验目录中的 historical BVMSim raw。

## 1. Scope and fixed source

- source class：`HISTORICAL_BVMSIM`；BVM=`BVMSim/bvm_cell.cir`，QB=`BVMSim/BQ.cir`，JTL=`BVMSim/library_josim/jtl2.cir`。
- nominal：`RJ1=12 Ω`、`RJ2=4 Ω`、QB bias=`250 µA`、JTL bias=`280 µA`、terminal=`10 Ω`、`.tran 0.1p 200p 45p`。
- historical BVM 不等于 canonical BVM：本目录没有使用 `circuits/bvm/bvm_cell.cir`；已知 `R_JM1` 为 `8 Ω` vs canonical `6 Ω`。
- 16-state 的预期为 `popcount(state)`；state 字序 `b3b2b1b0` 映射 `BVM1..BVM4`。
- single-BVM original-BQ deck 的日志保留了 `Missing model: JJMIT`/`Using default model` warning；4-BVM historical fixture 的顶层 model 可见、未出现该 warning。本轮未用 shared model 偷换 historical QB，因此结果不应描述为 shared-jjmit QB。
- 因此四个 single-BVM 记录的 intended-model closure 判为 `ARTIFACT_INVALID`，不把其 raw-derived 0/1 结果当作物理 PASS/FAIL；它们只保留作 historical 2×2 诊断。

## 2. Historical raw anchor check

`BVMSim/data_tran.csv` 的 duplicate-safe 读取保留了重复列 `V(O2)`×2；与 `F4_1111` 在 1549 个共同时间点上逐点比较，time grid exact=True，不插值。

| signal | max abs difference | RMS difference |
|---|---:|---:|
| I(BVMOUT) | 1.000e-15 | 2.541e-17 |
| V(QBIN) | 1.000e-13 | 2.541e-15 |
| V(QBOUT) | 1.000e-15 | 2.541e-17 |
| P(BJ1|XBQ1) | 0.000e+00 | 0.000e+00 |
| P(B01|XJTL1_1) | 0.000e+00 | 0.000e+00 |
| P(B01|XJTL1_2) | 0.000e+00 | 0.000e+00 |

这只是确认 print 扩展/状态 `1111` 没有改变这些共同电气轨迹，不是物理正确性或收敛证明。详见 `analysis/historical_anchor_check.json`。

## 3. Evidence inventory

- nominal runs：4 个 single-BVM + 16 个 4-BVM state = 20 个。
- individual visualizations：20 个；汇总图：2 个。
- 所有 individual 图均在 comparison 图之前生成并完成 raw-hash QA；图是描述性证据，不替代事件分析。
- raw 使用 requested `0.1 ps`；选定 raw 的存储网格 mostly 为 `0.1 ps`，但每个 run 都有一次 `62.8→63.0 ps` 的 `0.2 ps` 间隔，因此不是严格 uniform grid。分析直接使用实际时间列，不插值。

## 4. Single-BVM 2×2 baseline

| run | load | expected | QB burst | QB strict complete/clean | final burst | final strict complete/clean | artifact status |
|---|---|---:|---:|---:|---:|---:|---|
| S0-J | JTL | 0 | 0 | 0/0 | 0 | 0/0 | ARTIFACT_INVALID |
| S0-R | direct | 0 | 0 | 0/0 | 0 | 0/0 | ARTIFACT_INVALID |
| S1-J | JTL | 1 | 0 | 0/0 | 0 | 0/0 | ARTIFACT_INVALID |
| S1-R | direct | 1 | 0 | 0/0 | 0 | 0/0 | ARTIFACT_INVALID |

观察：两个 logical-1 single-BVM run 的 raw-derived QB/JTL6 burst 为 0，两个 logical-0 control 也为 0；但四个记录均出现历史 original-BQ 的 model-scope warning，故 intended-model closure 为 `ARTIFACT_INVALID`，不据此作 single-BVM 物理结论。

## 5. 4-BVM 16-state baseline

`QB burst` 与 `JTL6 burst` 是同一 READ1 窗口内、同一 JJ 的 phase/voltage-area 一致性得到的 burst-total 量化结果；它们不是仅凭 phase 位移计数。strict 列是独立的 segment/event 结构，且本轮具体阈值属于 post-hoc exploratory diagnostic，详见 `analysis/POST_HOC_DIAGNOSTIC.md`。
`popcount` 是 commanded state word 的预期，不等于 BVM1–BVM4 的内部状态已经逐颗由 raw 闭合确认；当前 print 对 BVM2–BVM4 的内部 JJ 证据不完整。因此这里判定的是 historical fixture 的端到端 commanded-state mapping，不把 mismatch 唯一归因于 QB。

| state | expected | QB burst | JTL6 burst | QB strict complete/clean | JTL6 strict complete/clean | QB max segment (turns) | QB continuous running | verdict |
|---|---:|---:|---:|---:|---:|---:|---|---|
| 0000 | 0 | 0 | 0 | 0/0 | 0/0 | 0.020 | 否 | FUNCTIONAL_PASS |
| 0001 | 1 | 3 | 3 | 1/0 | 3/3 | 3.004 | 是 | FUNCTIONAL_FAIL |
| 0010 | 1 | 2 | 2 | 1/0 | 2/2 | 2.000 | 是 | FUNCTIONAL_FAIL |
| 0011 | 2 | 4 | 4 | 1/0 | 4/4 | 3.037 | 是 | FUNCTIONAL_FAIL |
| 0100 | 1 | 1 | 1 | 0/0 | 1/1 | 0.976 | 否 | FUNCTIONAL_PASS |
| 0101 | 2 | 3 | 3 | 1/0 | 3/3 | 3.014 | 是 | FUNCTIONAL_FAIL |
| 0110 | 2 | 4 | 4 | 1/0 | 4/4 | 3.032 | 是 | FUNCTIONAL_FAIL |
| 0111 | 3 | 4 | 4 | 1/0 | 4/4 | 3.978 | 是 | FUNCTIONAL_FAIL |
| 1000 | 1 | 2 | 2 | 1/0 | 2/2 | 1.996 | 是 | FUNCTIONAL_FAIL |
| 1001 | 2 | 4 | 4 | 1/0 | 4/4 | 3.059 | 是 | FUNCTIONAL_FAIL |
| 1010 | 2 | 4 | 4 | 1/0 | 4/4 | 3.034 | 是 | FUNCTIONAL_FAIL |
| 1011 | 3 | 4 | 4 | 1/0 | 4/4 | 3.988 | 是 | FUNCTIONAL_FAIL |
| 1100 | 2 | 4 | 4 | 1/0 | 4/4 | 3.030 | 是 | FUNCTIONAL_FAIL |
| 1101 | 3 | 4 | 4 | 1/0 | 4/4 | 3.045 | 是 | FUNCTIONAL_FAIL |
| 1110 | 3 | 4 | 4 | 1/0 | 4/4 | 3.984 | 是 | FUNCTIONAL_FAIL |
| 1111 | 4 | 4 | 4 | 1/0 | 4/4 | 3.985 | 是 | FUNCTIONAL_PASS |

关键观察（Observed）：
- `0000`：QB/JTL6 均为 0，READ0/尾部控制也没有 complete event。
- `0100`：QB burst 为 1，但 QB strict 段未达到完整 1-turn 门槛；JTL6 出现 1 个 clean separated event。这说明 QB 局部结构与下游可见结构不能混为一谈。
- `1111`：QB burst=`3.9995`、area/Φ0=`3.9995`，但 QB 是一个约 4-turn continuous running segment；JTL6 最终可分辨 4 个 clean separated events。
- `0001`、`0010`、`0011`、`0101`、`0110`、`0111`、`1000`、`1001`、`1010`、`1011`、`1100`、`1101`、`1110` 的 QB/JTL6 burst 均高于预期，故 16-state mapping 未通过 hard count gate。

## 6. Strict transport detail for representative state 1111

下表使用 READ1 内相对首个存储样本的 first upward integer phase-displacement crossing 作为时序 marker；它不是 SFQ event count，也不是把 crossing 强行等同于 clean event。

| location | burst total | strict complete | clean separated | polarity | first upward crossings (ps) | first-crossing delta (ps) |
|---|---:|---:|---:|---:|---|---:|
| QB BJ2 | 4 | 1 | 0 | 1 | 118.31, 121.68, 125.48, 133.73 | — |
| JTL1 B02 | 4 | 1 | 0 | 1 | 121.30, 124.96, 129.29, 134.80 | 2.99 |
| JTL2 B02 | 4 | 1 | 0 | 1 | 124.34, 128.41, 132.78, 138.30 | 3.04 |
| JTL3 B02 | 4 | 1 | 0 | 1 | 127.37, 131.74, 136.21, 141.79 | 3.03 |
| JTL4 B02 | 4 | 1 | 0 | 1 | 130.41, 135.04, 139.53, 145.14 | 3.03 |
| JTL5 B02 | 4 | 2 | 1 | 1 | 133.43, 138.06, 142.51, 147.97 | 3.03 |
| JTL6 B02 | 4 | 4 | 4 | 1 | 134.54, 139.23, 143.53, 148.62 | 1.11 |

Observed：QB BJ2 的四个 upward crossings 约为 118.31、121.68、125.48、133.73 ps；JTL1→JTL6 的首个 crossing 依次向后，末级约为 134.54 ps。它支持该 historical loaded fixture 中存在 forward burst propagation 的有限描述。
Inference：JTL 后段可能把上游连续 burst dynamics 重塑为更清楚的局部 transitions；这不是已证实的机制。旧表中的 `clean onset` 是 local segment onset，尤其 JTL6 的早期 onset 不能当作因果传输延迟，因此不再用它作 stage latency。
1111 的 QB `BJ2` 仍是一个约 3.985-turn continuous running segment，不是四个 QB clean events；JTL6 的四个 clean labels 只描述最终输出侧的局部结构，不能反写为 QB 已产生四个独立 SFQ。

## 7. Selectivity and KCL

五个 4-BVM 非 READ1 窗口 `PRE/WRITE0/READ0/WRITE1/TAIL` 的 QB BJ2 与 JTL6 strict complete event 均为 0；因此本轮没有在这些窗口的已存储 raw 中观察到 complete spontaneous/extra event。这个结论不覆盖 4-BVM 未存储的 `0–45 ps` 启动段，也不构成每个状态都匹配的 no-READ selectivity Gate。

QB READ1 KCL residual max over all 16 states（单位 µA）：

- `QB_node2`：0.000120000 µA
- `QB_bias_node3`：0.000050000 µA
- `QB_node4`：0.000140000 µA

KCL 方程采用 branch current 从 netlist 第一节点流向第二节点：
- node2：`-I(BJs)+I(BJ1)+I(RJ1)+I(L1)=0`；
- bias node3：`-I(L1)-I(IB)+I(L2)=0`；
- node4：`-I(L2)+I(BJ2)+I(RJ2)+I(L3)=0`。

## 8. Decision and margin status

### Derived decision

`BASELINE_FUNCTIONAL_FAIL`：nominal 16-state 没有支持预注册的 `0→0, 1→1, 2→2, 3→3, 4→4` 功能映射；更精确的 evidence descriptor 是 `HISTORICAL_FIXTURE_COUNT_MISMATCH`。按允许的探索性分类保留 `SELECTIVITY_OR_OVERDRIVE_FAILURE`，quick label 为 `QUICK_OPPOSITE`，但这里的 overdrive 只描述 count mismatch/continuous running 观察，不是已经证明的器件机理。
注意：`0.25 turns` burst display tolerance、strict complete/clean/retrap thresholds 都是运行后诊断参数，不是 preflight 中已冻结的 acceptance threshold；因此具体 strict 数字不应被提升为 Formal Gate。

### Margin axes

本轮不执行 `IB`、`RJ1` 或 physical-input `alpha` 的任何裕度扫描，也不执行 pairwise map。原因是 setup 中已冻结的 stop rule：nominal 16-state baseline 未通过，不能在失败基线之上把 RJ1 结果解释为工作裕度。`RJ1=12 Ω` 继续保持 nominal baseline，不发生替换。

## 9. What this does not prove

- 不证明 canonical BVM compatibility；
- 不证明 single-BVM compatibility；四个 single 记录因 historical model-scope warning 对 intended model closure 为 artifact INVALID，不能支持普遍兼容或不兼容结论；
- 不证明 timestep convergence、process margin 或其他参数容差；
- 不证明 T1 compatibility、论文机制身份或唯一 QB operating mechanism；
- 不证明 BVM2–BVM4 的 commanded state 已逐颗闭合，也不证明一个 BVM contribution 必然对应一个 QB/JTL downstream SFQ。

## 10. Visualization index

- primary representative overview：[`plots/RESULT_OVERVIEW.html`](../plots/RESULT_OVERVIEW.html)
- single 2×2 overview：[`plots/SINGLE_2X2_OVERVIEW.html`](../plots/SINGLE_2X2_OVERVIEW.html)
- 每个 run 的独立图见 `plots/runs/<run_id>/RUN_OVERVIEW.html`；完整命令、labels、raw unchanged QA 和 HTML hashes 见 `analysis/visualization_manifest.json`。

## Current gate

`AWAITING_USER_REVIEW`; `user_reviewed=false`; `next_step_authorized=false`; `automatic_next_experiment=false`。
