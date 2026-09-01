# Reviewer notes：BVM_QB_DYNAMIC_SOURCE_LOADLINE_AUDIT_V1

## 1. 预审边界

本文件合并本轮执行前取得的 Sol XHigh 只读物理预审，以及交付前的
adversarial/numerical review。它不是新的科学 authority；raw、netlist、预注册和
本目录的派生证据共同定义本轮可说的范围。

- reviewer：Archimedes（`josim_architect`，Sol XHigh，read-only）；
- agent id：`01a05be2-2116-75b3-85c4-2ddd640e94f8`；
- 预审结论：`CONDITIONAL GO`；
- 预审期间：未改文件、未运行 JoSIM；
- 允许继续：A/B identity guard、source waveform difference、QB current
  partition/KCL、B/C port trajectory、scalar-model falsification；
- 明确停止：unique mechanism、静态阻抗、具体器件归因、parameter recommendation、
  robust margin、downstream SFQ delivery。

预审特别指出：H1 的 duration/area 与 tail timing 相互混杂；H2 可以 refute pure
duration 但不与 H1 互斥；H3 是 mediator hypothesis 而不是独立 intervention；H4
只能支持总体 source-load boundary；H5 可以被标量拟合否证但不能由良好拟合证明
充分性；H7 的数量与 Ic/area 同时变化，不能声称“primarily”。

## 2. 执行结果审查

| 检查 | 探针 | 结果 | 处置 |
|---|---|---|---|
| wrong branch / duplicate header | 独立 raw parser 保留重复 `I(B_LD1)`，明确取 occurrence 0；与主分析比较 A peak、B area | 四项关键值全部 match | 接受 occurrence 约定；不把第二个 JJ branch 偷换为 terminal current |
| stale artifact | 48 个 raw 的实际 SHA-256、sidecar 声明和 execution log 记录逐一比较 | `48/48` raw、sidecar、log hash 一致；returncode 全为 0 | raw QA=`PASS` |
| weak oracle | `independent_raw_recheck.py` 不 import `run_analysis.py`，直接重读 selected raw | source peak/area、B/C `DeltaI`、scalar residual 全部匹配主结果；独立 KCL 也通过 | 作为机械一致性检查保留，不能当第二科学权威 |
| boundary | A/B 全部注册 source/replay signal 使用 `t<=105 ps` pointwise identity；首次 divergence 用冻结 floor + 连续两点 | 12×320、8×500 均 `PASS`；首个 divergence 在 `105.0125 ps`，同 bin 多 family `TIE` | 不把 105 ps 前的共同轨迹写成差异 |
| KCL precision | 对 node1–4 按同一方程所有支路绝对电流和计算 `max(1e-12 A, 1e-6×sum(abs(terms)))` | ideal/physical 13 ps 12×320 均 `PASS`；最大 residual/ bound 比约为 0.23 | 这是 CSV 输出精度 QA，不是事件或机制证据 |
| overclaim | 搜索报告中的 event/SFQ/JTL/T1/impedance/unique wording，并核对 hypothesis 状态 | H3、H7=`UNRESOLVED`；pre-state=`CHANGED`；未写 unique device、JTL delivery 或 static impedance | 保持 bounded conclusion |

## 3. 数值复核

- JoSIM `P(...)` 保持原始弧度语义；phase trajectory 先连续 `unwrap`，图中再用
  `2π` 转为 turns。没有把 phase turn 当作 downstream SFQ count。
- 同一 JJ、同一方向、同一窗口的 phase/voltage-area strict classification 沿用
  已冻结的 `strict-event-summary.csv`，本轮没有重算或改写 A–E 分类。
- source current 的 signed/positive/negative area、centroid 和 effective duration
  只是 waveform diagnostics，不是 Φ0、SFQ 数或事件数。
- KCL 方向与 QB netlist 对齐：`I(LIN): IN→1`；`I(BJs): 1→2`；node2 的
  `BJL1/RJ1: 2→0`、`L1: 2→3`；node3 的 `RB: IB→3`、`L2: 3→4`；node4 的
  `L0: 4→OUT`、`BJL2/RJ2: 4→0`。
- raw-origin 与 baseline-corrected scalar fit 均失败：normalized residual 约
  `0.666`、correlation 约 `0.723`，且 peak-time shift 约 `−0.475 ps`；因此只支持
  bounded non-scalar waveform/load-line reshaping family，不支持纯标量衰减模型。

## 4. 对最强有界声明的审查结论

本轮最强声明是：在既有 48-run raw、A/B identity、B/C source/QB-input 差异、QB
KCL QA 和 scalar falsification 同时通过的范围内，证据支持总体 dynamic
source-load interaction，且 physical source 不能由单一 `k` 倍 grounded source
充分描述。

该声明通过了本轮探针，但边界仍然是：

- H1 被当前面积分解阈值判为 `DISFAVORED`，不是“READ duration 已被证明为唯一
  原因”；
- H2 为 `SUPPORTED` 只表示 105–110 ps 外仍有 shape/timing difference，不能定位
  某一个 waveform lobe；
- H3、H7 保持 `UNRESOLVED`；
- B/C pre-state 已经 `CHANGED`，所以不能把 physical failure 单独归因于 READ
  期间的一枚 lobe；
- `Z_sec` 只是 two-boundary diagnostic，不是 Thévenin、小信号或 constant resistor；
- 不涉及硬件、步长 robustness、JTL/T1 delivery 或 paper-level claim。

## 5. Residual uncertainty

仍未被本轮 raw 解决的风险包括：pre-state 与 READ-period reshaping 的分离、H3 的
具体 mediator、12×320 与 8×500 中数量和 Ic/area 的独立贡献、scalar attenuation
对 QB failure 的充分性，以及更细 timestep 下的 margin。按预注册停止规则，本轮
不推荐参数、不启动 sweep、不更新 HANDOVER/todo。
