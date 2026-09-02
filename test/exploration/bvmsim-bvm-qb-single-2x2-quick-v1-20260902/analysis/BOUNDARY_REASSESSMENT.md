# single-BVMSim matched 2x2 A001：Boundary reassessment

状态：`AWAITING_USER_REVIEW`

分析类型：analysis-only；只读取既有 A001 raw；未重新运行 JoSIM；未修改 raw CSV。
分析日期：2026-09-02

## 1. 范围与基准

本次只重新解释现有 experiment 中的四个 A001 条件：`S0-R`、`S1-R`、`S0-J`、`S1-J`。没有开始 canonical BVM、single-BVM 新实验、参数扫描、timestep ladder、T1 或任何自动 follow-up。

用户指定的基准 HEAD 是 `d91e4d333661b5ed880386800e45c35836912032`。实际执行时 HEAD 为 `87cdaca8d3befeee5aa4d62775eb4ddf3bd5f6d8`；后者只包含此前的历史 `BVMSim/data_tran.html` 可视化提交，未改变本 A001 的 input 或 raw CSV。这个基准差异已保留在 metrics provenance 中，不能被忽略。

本报告的 Boundary 判定是实验内、探索性的功能性判定，不是 Formal Gate，也不是论文或硬件结论。`FUNCTIONAL_PASS` 只表示本次冻结的局部证据满足该 Boundary 的探索性检查；所有 strict verdict 仍然是 `NOT_YET_QUALIFIED`。

## 2. 不变的测量约定

使用窗口：

| 窗口 | 时间 |
|---|---:|
| `INITIAL_BIAS` | `[0, 50)` ps |
| `PRE_READ` | `[65, 70)` ps |
| `READ_DRIVE` | `[70, 81)` ps |
| `READ_RESPONSE_TAIL` | `[81, 110)` ps |
| `POST_SETTLING` | `[110, 130)` ps |
| `POST_REST` | `[130, 200]` ps |
| `READ_LOCAL` | `[70, 110)` ps |

JoSIM 的 `P(...)` 原始单位是 rad；报告中的相位差和图中的相位显示均使用 `continuous_unwrap(raw_rad)/(2*pi)` 转为 turns。电压面积使用同一 junction 的 V 分支、实际 CSV 时间网格和梯形积分，再除以 `Phi0`。四个 raw 的时间轴逐点一致，但含有一个 0.05 ps 间隔，因此没有假设均匀采样，也没有插值。

候选的近一量子判据是探索性 `[0.8, 1.2]` turns，并要求同一 junction 的 phase/area 同向且相互一致。它不是 SFQ 计数器；没有把 Vpeak、`I > Ic`、整窗相位变化或整窗面积当作事件数。`B01` 是 JTL 输入侧内部 marker，`B02` 是输出侧 marker；运输判断只使用 B02，不把 B01+B02 算成两个事件。

## 3. 数据完整性与 provenance

四个 A001 raw 均为 `VALID`，各有 7999 个样本，时间范围为 `0` 到 `199.975 ps`，raw hash 与冻结值一致，四条时间轴逐点一致。raw SHA-256：

| 条件 | raw CSV | SHA-256 |
|---|---|---|
| `S0-R` | `runs/A001/S0-R/raw.csv` | `a8e8183d864b8170bf29074644b467d1b00613f3848b7e25f0f4b1059237d1f3` |
| `S1-R` | `runs/A001/S1-R/raw.csv` | `ac622d6c343b3edf18b656620c1df4a9263b37d117e6d48f65cc2a3399a1d904` |
| `S0-J` | `runs/A001/S0-J/raw.csv` | `8844cd26ee3f5d4058ea5f7fde34f995b8c5d09a1b5f4ab9aebed3d9ca7cbeeb` |
| `S1-J` | `runs/A001/S1-J/raw.csv` | `95042595e9c8ba9c82af1f7f9e8bd6130214405d8c8804ab4912d92bedae8b21` |

已有 solver provenance：`build/josim-cli` v`2.7.2837d13`，SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`。本轮没有调用 solver。JTL 仍按 `BVMSim/library_josim/jtl2.cir` 的原始行为解释，未做 model normalization。

关键分析文件 hash：

| 文件 | SHA-256 |
|---|---|
| `docs/research/BOUNDARY_SPEC_V1.md` | `d0c47bea3bd37c7b3b9a7a9ca5b02ddae08ef9a728fe96458e2e3252fe981889` |
| `analysis/boundary_reassessment.py` | `68c42e2a71597078de2927e4bc26b5c16099766e016b982f0d903ee0faa30065` |
| `analysis/independent_boundary_check.py` | `5619cf84664fef4cb0fae47025730cb44fb601dd5641cf869a0490fcd542d8b9` |
| `analysis/qa_boundary_artifacts.py` | `c2a87f60900b171481835b6227374f67c27e3b728735b8bc0229b66f0b00094f` |
| `analysis/boundary_metrics.json` | `b4b89f2caf42c7fd831bd4d7f545cf80071fab938bf607e7d953febb8db04c48` |

## 4. OBSERVED：实际看到的内容

### B0：BVM sensing / 12-JJ sensing line / QBin

在 `READ_DRIVE` 中，`S1-J` 相对于 `S0-J` 显著增强：

| 条件 | `max V(SL1)` | `max I(L_SL)` | `max V(QBIN)` | `max V(BVMOUT)` |
|---|---:|---:|---:|---:|
| `S0-J` | `0.235802 mV` | `12.7072 uA` | `0.074905 mV` | `0.017074 mV` |
| `S1-J` | `1.225268 mV` | `100.1822 uA` | `0.718488 mV` | `0.061805 mV` |

这说明本 fixture 中存在 state-dependent 的 sensing-line / QBin waveform。直接负载控制也显示负载影响：`S1-R` 与 `S1-J` 的 `V(QBIN)`、`I(BVMOUT)` 和 `V(BVMOUT)` 在 `READ_LOCAL` 中明显不同。

目前直接探测的 line junction 只有 `B_LD4_01`、`B_LD4_11` 和 `BVMOUT` 三个 marker，不是 12 个 junction 的全覆盖。三个 marker 在 `S0-J` 的 principal phase/area 约为 `0.0010123/0.0010130` turns，在 `S1-J` 约为 `0.0049185/0.0049212` turns，均不接近一 turn。

### B1：selective QB triggering

`READ_LOCAL` 中，`S1-J` 的 `BJ1` 和 `BJ2` 出现近一-Phi0-scale 的局部响应，而 `S0-J` 没有可比响应：

| 条件 / junction | phase delta (turns) | V-area (turns) | 候选数 | 近一-Phi0 候选数 |
|---|---:|---:|---:|---:|
| `S0-J BJ2` | `0.0006824` | `0.0006834` | 1 | 0 |
| `S1-J BJ1` | `1.0020026` | `1.0020049` | 1 | 1 |
| `S1-J BJ2` | `0.9992648` | `0.9992655` | 1 | 1 |
| `S1-R BJ2`（直接负载控制） | `1.9976404` | `1.9976415` | 1 | 0 |

`BJs` 在 `S1-J` 中没有近一-Phi0 响应；它的局部 phase delta 约为 `-0.0053205` turns。`INITIAL_BIAS` 与 `READ_LOCAL` 在分析契约中分开，不能把 t≈0 的偏置启动瞬态并入 READ 响应；本轮没有把启动瞬态另行宣布为事件数。

### B2：local quantization boundary

主目标是 `S1-J BJ2`。候选 onset 为 `70.975 ps`，主活动结束为 `104.2 ps`，测量区间为 `70.95–104.225 ps`：

- `delta_phase_rad = 6.2785658 rad`，即 `0.9992647826 turns`；
- 同一 BJ2 V 分支面积为 `0.9992655404 turns`；
- signed phase-area residual 为 `-7.5782e-7 turns`；
- 只有 1 个候选、1 个近一-Phi0 候选、0 个额外可比候选；
- 依据探索性证据层级记为 `QUANTIZED_LOCAL_SFQ_CANDIDATE`。

但该段的 `complete_segment=false`、`clean_separated_event=false`：没有证明 retrap/bounded interval，也没有 timestep convergence、边界敏感性或重复稳健性。因此这里是“近一量子局部响应候选”，不是“已证明的 clean SFQ event”。`POST_SETTLING` 中 BJ2 的相位漂移率约为 `-5.9755e-5 turns/ps`，电压 RMS 约为 `1.79 uV`；这些数值被保留为 settling 诊断，不能反向制造 retrap 结论。

旧的 full-window task-local detector 仍记录为 `CONTINUOUS_MULTI_TURN_RUNNING_STATE`，但它将初始化和 READ 过程混在 `0–200 ps` 中。它只作为历史 diagnostic 保留，不作为本次 Boundary 的 B2 verdict；本次 `READ_LOCAL` 的 BJ2 结果是约一 turn 的单个局部候选，仍不足以区分干净事件和连续运行段。

### B3：QB → QBOUT → JTL1…JTL6

`S1-J` 的 `V(QBOUT)` 只作为电压活动观察量：活动约为 `71.1–104.15 ps`，峰值 `0.658038 mV`。`S0-J` 的相应峰值绝对值约为 `0.013673 mV`。由于没有 `P(QBOUT)`，这里不把 QBOUT 电压活动本身当作 SFQ 计数。

JTL 的六个 B02 是输出侧 marker。下表的 phase/area 是每一级在 `READ_LOCAL` 中的 principal near-one-Phi0 candidate，不是 clean event count：

| marker | onset (ps) | 相对前一级 latency (ps) | phase (turns) | V-area (turns) | polarity |
|---|---:|---:|---:|---:|---:|
| QB `BJ2` | `70.975` | — | `0.999265` | `0.999266` | `+` |
| JTL1 `B02` | `78.150` | `7.175` | `0.993459` | `0.993461` | `+` |
| JTL2 `B02` | `81.450` | `3.300` | `0.996853` | `0.996856` | `+` |
| JTL3 `B02` | `84.350` | `2.900` | `0.997210` | `0.997212` | `+` |
| JTL4 `B02` | `87.350` | `3.000` | `0.994693` | `0.994693` | `+` |
| JTL5 `B02` | `90.350` | `3.000` | `0.997004` | `0.997008` | `+` |
| JTL6 `B02` | `93.550` | `3.200` | `0.992447` | `0.992446` | `+` |

六级 onset 递增、极性一致；同一近一-Phi0 heuristic 下，`S0-J` 没有对应的六级响应。该结果支持“本 fixture 中有从 QB output-facing marker 到 JTL6 output-facing marker 的有序局部响应链”，但由于每一级同样缺少 retrap/convergence/repeat，不能把这张表改写成“六级 clean SFQ transport count”。

## 5. INFERENCE：在当前证据上可以说什么

1. BVM 读出不是静默的：逻辑状态改变了 SL1、SL 电感电流、BVMout 和 QBin 的波形，并且这种差异到达 QB 输入。
2. 在这个 single-BVMSim、12-JJ sensing-line、A001 fixture 中，S1-J 对 QB 内部 BJ1/BJ2 的局部响应满足近一-Phi0 phase/area heuristic，而 S0-J 没有可比响应。
3. `S1-J BJ2` 是一个量化局部响应候选；现有数据不能把它升级成严格 clean separated SFQ。
4. QBOUT 电压活动之后，JTL1–JTL6 的 B02 marker 出现有序、同极性的近一-Phi0-scale 局部响应；这支持功能性 transport boundary 的探索性通过。
5. `S1-R` 的直接 10-ohm 负载控制约为 2 turns，而 `S1-J` 约为 1 turn，表明 downstream load/backaction 会改变 QB 波形；这不是本次 Boundary 的失败条件，但必须保留为物理解释限制。

## 6. UNKNOWN：本轮没有证明什么

- 没有证明 12-JJ sensing line 的所有 junction 都无 slip；只有 3 个 line marker 被直接读出。
- 没有证明 `S1-J BJ2` 是有 retrap 的单个 clean SFQ，也没有证明有多个 separated SFQ。
- 没有 timestep convergence、repeat、参数边界敏感性或 process margin。
- 没有证明 canonical BVM 兼容性；本轮使用的是历史 `BVMSim/bvm_cell.cir`。
- 没有证明 single-BVM 贡献规则、paper mechanism identity、硬件行为、T1 或系统逻辑。
- 没有把 `B01` 和 `B02` 当成两个事件，也没有把 phase turns 直接等同于 downstream SFQ count。

## 7. Boundary verdict table

| Boundary | Functional verdict | Strict verdict | Why |
|---|---|---|---|
| B0 | `INCONCLUSIVE` | `NOT_YET_QUALIFIED` | S0/S1 的 SL1、SL 电流、BVMout、QBin 差异清楚；但 12 个 line junction 只有 3 个 marker，且没有 convergence/robustness。 |
| B1 | `FUNCTIONAL_PASS` | `NOT_YET_QUALIFIED` | S1-J 的 BJ1/BJ2 有近一-Phi0-scale local response，S0-J 没有可比目标响应；启动瞬态未被冒充成 READ event。 |
| B2 | `FUNCTIONAL_PASS` | `NOT_YET_QUALIFIED` | `S1-J BJ2` 为 `QUANTIZED_LOCAL_SFQ_CANDIDATE`：phase `0.9992648`、area `0.9992655` turns，且没有第二个可比候选；没有 retrap、convergence、repeat。 |
| B3a | `FUNCTIONAL_PASS` | `NOT_YET_QUALIFIED` | JTL1 B02 有 `0.993459/0.993461` turns 的局部响应，S0-J 没有同级响应；这里只是 output-facing local marker。 |
| B3b | `FUNCTIONAL_PASS` | `NOT_YET_QUALIFIED` | JTL1–JTL6 B02 onset 有序、极性一致、phase/area 约 `0.992–0.997` turns；仍没有严格 clean-event transport 资格。 |
| B4 | `NOT_TESTED` | `NOT_YET_QUALIFIED` | A001 没有 T1 或 downstream logic。 |

这张表不能合并成 `FOUR_SEPARATED_SFQ_TRANSPORT_SUPPORTED` 或任何 Formal PASS。当前最强的可复述结论是：本 A001 fixture 显示 state-selective、near-one-Phi0-scale 的 QB/JTL 局部响应链，但 clean separated SFQ 语义仍未建立。

## 8. 对 Boundary 问题的七个直接回答

1. **BVM 是否把状态信息传到 QBin？** 是，S0-J/S1-J 的 SL1、`I(L_SL)`、BVMout 和 QBin 的 READ 波形明显不同；这是功能性观察，不是完整 12-JJ line 无 slip 证明。
2. **line 是否已证明没有产生一量子 slip？** 仅对三个已探测 marker 看到远小于一 turn 的 phase/area；其余九个 junction 未观测，因此全线结论未知。
3. **QB 是否选择性响应 READ1？** 在 READ_LOCAL 下，S1-J BJ1/BJ2 满足近一-Phi0 heuristic，S0-J 无可比候选，支持本 fixture 的选择性响应。
4. **BJ2 是否已经是严格 clean SFQ？** 否。它是 `QUANTIZED_LOCAL_SFQ_CANDIDATE`；没有 retrap/separation、收敛和重复证据。
5. **QB local response 是否到达 QBOUT/JTL1？** `V(QBOUT)` 有明显 S1-J 活动，JTL1 B02 有有序的近一-Phi0-scale 局部响应；这是功能性边界证据，不是 clean event count。
6. **JTL1 到 JTL6 是否保持了同一 transport identity？** B02 onset 依次递增、正极性一致、每级 phase/area 约一 turn，支持探索性 transport chain；严格 identity 仍未资格化。
7. **这是否已经证明 canonical BVM、论文机制或硬件可行性？** 没有；这些都超出本次 A001 analysis-only 范围。

## 9. 对抗性与数值审查记录

| 风险 | 本轮检查 |
|---|---|
| phase 弧度被误画成 turns | HTML 轴固定为 `Phase (turns) [rad/2pi]`；B3 BJ2 图中最大值与 raw 解包除以 `2π` 的最大绝对误差为 `4.44e-16 turns`。 |
| raw 被重写或插值 | 四个 raw hash 与冻结值一致；时间轴逐点一致；所有投影均标记 `interpolation: none`。 |
| 局部 index 被当成全局 index | 首次独立复核发现该分析元数据错误：ps endpoint 正确，但 `measure_*_index` 曾是窗口局部偏移。已改为记录全局 index，同时保留 `local_*_index`；raw 未变，重新分析和独立复核均通过。 |
| B01/B02 被重复计数 | JTL transport 使用 B02 作为输出侧 marker，B01 只作内部说明。 |
| full-window 与 READ 响应混淆 | 旧 `CONTINUOUS_MULTI_TURN_RUNNING_STATE` 只作 legacy diagnostic；B2 使用 `READ_LOCAL`。 |
| 负载反馈被忽略 | 保留 `S1-R` 直接负载控制；约 2-turn 与 S1-J 约 1-turn 的差异被列为 backaction 观察。 |
| 近一-Phi0 heuristic 被冒充 strict event | 所有 Boundary strict verdict 均为 `NOT_YET_QUALIFIED`，没有使用 Formal PASS 语言。 |

## 10. 产物与复核命令

聚焦可视化（均为描述性投影，raw 仍是证据来源）：

- [BOUNDARY_B0_QBIN.html](../plots/BOUNDARY_B0_QBIN.html)
- [BOUNDARY_B2_BJ2.html](../plots/BOUNDARY_B2_BJ2.html)
- [BOUNDARY_B3_TRANSPORT.html](../plots/BOUNDARY_B3_TRANSPORT.html)
- [boundary_metrics.json](boundary_metrics.json)
- [independent_boundary_check.json](independent_boundary_check.json)
- [boundary_plot_manifest.yaml](boundary_plot_manifest.yaml)

已执行：

```text
python3 analysis/boundary_reassessment.py                                  # exit 0
python3 analysis/boundary_plot.py --timestamp 2026-09-02T18:18:17+08:00    # exit 0
python3 analysis/independent_boundary_check.py --timestamp 2026-09-02T18:20:46+08:00  # exit 0
python3 analysis/qa_boundary_artifacts.py                                  # exit 0
python3 -m py_compile analysis/boundary_reassessment.py analysis/boundary_plot.py analysis/independent_boundary_check.py analysis/qa_boundary_artifacts.py  # exit 0
```

独立复核覆盖 7 个主区间（BJ2 + 六级 JTL B02）：四个 raw hash 和 exact time grid 均通过，phase/area 与 `boundary_metrics.json` 的最大绝对误差均为 `0`。`qa_boundary_artifacts.py` 还验证了三个 HTML 页面没有 `Unknown` y-axis，且保留 P/V/I 标签前缀。

## 11. 下一步选项（本轮未执行）

1. 用户先审阅本报告、Boundary 表和三张 focused 图。
2. 如确有必要，另行授权一个明确限定的 convergence/repeat 或 line-coverage follow-up。
3. 将本轮作为 exploratory evidence 归档；不自动升级为 Gate、论文量化结论或 Stage B。

## 12. Human understanding gate

```yaml
status: AWAITING_USER_REVIEW
user_reviewed: false
next_step_authorized: false
automatic_next_experiment: false
stage_b_authorized: false
next_action: STOP
```
