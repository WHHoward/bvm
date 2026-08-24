# JoSIM × BVM 项目交接文档（审计修订版）

> 用途：给下一次会话提供当前可信状态和行动顺序。完整原理与项目教学见 `docs/guide/project-guide.md`。
>
> 审计日期：2026-08-09；**被审计的前置基线 commit**：`eb51576`（不包含本轮未提交文档）；研究使用的二进制报告 `v2.7.2837d13`。
>
> 重要：2026-08-06 版“冻结口径”已因相位单位错误失效；不得从旧日志复制 SFQ 数或 `fast_events` 结论。

## 当前接收器同步（2026-08-24）

本轮科学分析的 parent HEAD：`edf9b6d6c9a26c999a9f95f8ca604993475c51d4`。R0b–R15B 的 receiver
Exploration 结论保持不变；本轮仅对既有 R11、M1、M5-PC 和 pulse-5 replay raw
完成 `JTL_TRANSPORT_GATE_V1` 回顾性 provisional 方法学分类，没有运行 JoSIM、没有修改物理电路。

当前最重要的证据边界：

1. `STRICT_LOCAL_EVENT` 与 `JTL_TRANSPORT_EVENT` 是两条不同证据链。strict
   local event 仍要求一个 continuous monotonic segment 达到至少一圈并由同一
   JJ、同一 segment 的直接电压面积支持；settled pre→post adjacent-well
   transition 不能回写成 local event。
2. R11 standard-JTL positive control 的 strict vector 为 `[1,0,0,0]`，但四颗
   JJ 的 pre/post settled wells、full-window phase/area 和 causal onset order
   满足本批 provisional transport gate。该 gate 是标准 JTL fixture 的 transport
   evidence，不是 global Authority metric freeze。
3. Q0 pulse-5 原极性 ideal replay 与 R11 在本批 provisional transport signature 下均为
   四颗 `+1` well、bounded、逐级传播；这只证明 ideal replay transport
   compatibility，不证明 physical Q0→JTL coupling。反极性 replay 不是 logical0
   control，且不形成预期的 `+1` chain。
4. M5-PC 的 full-window/pre→post 约为 `+2` wells。历史
   `abs(turns)>=0.90` predicate 没有 one-turn 上界，故旧 “approximately-one”
   label 已被更正为 `MULTI_WELL_TRANSPORT_NOT_ONE_TURN`，不能再引用为 exactly-one。
5. 当前仍没有 canonical BVM→JTL、physical QB→JTL→T1 closure；不得把 ideal
   replay transport 结果升级为最终接口成功。

详细方法与逐 JJ 数据见
`test/exploration/jtl-transport-gate-v1-methodology-20260824/analysis/REPORT.md`；
M5 判据更正见
`test/exploration/parallel-qb-jtl-interface-mechanism-20260824/analysis-v2/M5_PREDICATE_CORRECTION.md`。

## 0. 新会话第一步

```bash
cd /home/howard/JoSIM
git status --short
git log --oneline -8
build/josim-cli --version
```

然后按顺序读：

1. `docs/guide/project-guide.md`：审计后的完整教学、证据边界和计划；
2. 本文件：当前执行状态；
3. `memory/project-todo.md`：任务清单；
4. 若执行 Codex 委派任务，读 `research/CLAUDE_EXECUTOR.md` 和指定 `research/tasks/<task-id>/request.yaml`；
5. 原始网表和 CSV；旧 BASELINE/P0/P2/证据链仅作历史记录，先看其顶部审计警告。

### 0.1 Codex–Claude 分工（2026-08-09）

本仓库采用文件化任务合同：Codex 负责计划、签发 request 和独立审计；Claude Code 只在 ACK 后执行授权路径并提交 receipt；用户批准路线变化、指标冻结和论文主张。完整状态机、所有权和命令见 `research/WORKFLOW.md`。

`execution_status=COMPLETED` 只表示执行结束，不代表证据有效或物理成功。必须分别记录 artifact `VALID/INVALID`、physical `PASS/FAIL/INCONCLUSIVE` 和 audit `ACCEPTED/REWORK_REQUIRED/REJECTED`；只有接受的审计才能更新本文件或主任务表。

## 1. 项目定义

目标是验证并设计：

```text
BVM 状态相关读电流
    → BQ 或 DCSFQ_BVM 接口
    → 恰好一个可被标准 JTL 接收的 SFQ 事件
    → T1 / RSFQ 计数和计算
```

本项目没有修改 JoSIM 核心。对 `src/`、`include/`、`cmake/`、根 `CMakeLists.txt` 和 `test/CMakeLists.txt` 的 Git 核验表明，它们与上游树一致。研究层新增的是网表、实验、数据、脚本、论文和文档。

## 2. 最高优先级事故：相位指标单位错误

JoSIM 默认 phase 模式的 `P(JJ)` 是原始相位 \(\phi\)，单位 rad。证据：

- `src/Output.cpp` 直接输出相位差，没有除以 \(2\pi\)；
- `docs/tech_disc.md` 使用 \(V=(\Phi_0/2\pi)d\phi/dt\)；
- `scripts/josim-plot2.py` 默认标 `Phase (rad)`，`-j 2pi` 才归一化；
- 官方 JTL 示例在两个输入后相位约 13 rad，接近 \(4\pi\)。

但 `scripts/sfq_metrics.py` 直接把 raw rad 标为 SFQ，并把每个满足 `|ΔP|>0.3` 的采样间隔计成 `fast_events`。

正确关系：

\[
N_{\Phi_0}=\Delta\phi_{\rm rad}/(2\pi)
\]

这是某个 JJ 的净相位绕转数，不自动等于完整环 fluxoid 数。与电压面积交叉校验时，必须使用同一 JJ、同一对端点、同一方向和同一时间窗。

而 `fast_events` 是过阈值样本数，不是脉冲数。一个已知 JTL 事件会跨多个样本。

### 直接后果

- Step 0 的“基线冻结”失败；脚本在修复前暂停作为物理 Gate。
- 所有 phase 数字和事件数必须从原始 CSV 重算。
- Phase 1 计划暂停，先执行 Phase −1。
- 旧论文证据链的“八轮系统排除”不再成立。
- 哈希一致仍证明数值文件可重复，但不证明指标正确。

## 3. 经重算后的关键事实

### 3.1 BVM→BQ 基线

| 结 | 原始净相位 | 正确归一化 |
|---|---:|---:|
| BVM JM1 | −5.909806 rad | −0.940575 圈 |
| BQ BJs | +6.272743 rad | +0.998338 圈 |
| BJL1 | +0.443319 rad | +0.070556 圈 |
| BJL2 | +0.375836 rad | +0.059816 圈 |

`V(OUT_Q)` 峰值约 157 µV。该基线的 `OUT_Q` 只接 10 Ω 电阻，没有 JTL；因而它没有实际测试标准 JTL 接收。

可信结论：BJs 的净变化约一圈，但 BJL1/BJL2 未完成完整绕转，因而当前数据没有证明 BQ 完成有效量化；JTL 传播未测。不能再称 BJs 滑移 6.27 个量子，也不能用 `fast_events=0` 证明它“不是相位事件”。仅凭净值也不能排除正反过程抵消，需要完整轨迹、稳定窗和同一 JJ 两端电压面积。

### 3.2 BVM P2

- W1/W0 稳态 JM1 分别约 `+0.938/−0.937` 圈；
- WL=80 µA 不写，100/120 µA 可进入近一圈状态；
- 100 µA 读相位漂移约 0.004–0.009 圈，读电流重复性在约 1% 内；
- 120 µA 的 R0 测试会擦除负态；
- 单个 JM1 相位不能独立证明完整环 fluxoid 数，需完整环量子化计算。

用 `P(JM1)≈±5.9` 直接证明“\(\pm6\) 多涡旋”和“没有单涡旋工作点”的旧证据链已被推翻。完整环 fluxoid 数仍未由本次审计独立确定。

### 3.3 BQ v4

电流扫测试有六个周期输入：

- 70/90 µA：已测点的下游没有逐周期累积；
- 110/130/150 µA：以首脉冲前参考点为基准，BJL1/BJL2 和 JTL 各约增加六圈，其相位平台与每输入约一个下游事件相容；单脉冲电压面积、聚类和步长 Gate 尚未通过；
- 在 110–150 µA 输出点，输入 BJs 仍每周期运行约 18–22 圈；完整 70–150 µA 扫描范围为约 16–22 圈。

所以当前只能说：在这个理想周期电流测试台的已测点中，90 µA 没有逐周期输出，110 µA 已出现与约 1:1 传播相容的相位平台；实际边界尚待细扫，不称为已确定阈值。68.4 µA 是旧 BQ-v2 加载基线值，v4 改变输入阻抗后的真实 BVM 波形尚未知，真实级联仍未成功。

结论：BQ v4 重新列为候选；既不能称“已排除”，也不能称“接口完成”。

### 3.4 DCSFQ / DCSFQ_BVM

标准 DCSFQ：

- 已测至 150 µA 未见输入诱导的完整内部相位绕转；
- 300 µA 减去 0 µA 偏置启动控制后，B1/B2/B3 分别为 `−1/+1/+1` 圈；
- bump 与 sustained 的最终响应相同，保持平台不继续积累。

缩放版 DCSFQ_BVM：

- B1/B2 从 225 µA 缩至 80 µA，IB1 从 275 µA 缩至 100 µA，输出级保持标准 250 µA；
- 68.4 µA 下未触发完整输出；
- 输入增量进入 L3/结支路的比例约 0.285。

“300 µA 多滑移爆发”和由此推导的 45–55 µA 目标均失效。已测点只能说 150 µA 未见完整内部绕转、300 µA 见约一圈；这不是已定位的合格输出或 JTL 接收阈值。ColdFlux 手册原本把 DCSFQ 定义为电压脉冲→SFQ，本项目的慢/电流接口用法必须重新验证。

## 4. 不受相位单位影响的结果

- BVM 负载扫描：峰值电流约 43.9–97.8 µA；
- FWHM：约 6.8–11.2 ps；
- 特定波形的有效峰值 Thevenin 拟合：约 40 Ω、4 mV；
- 基线 BQ 输出电压峰值约 157 µV；
- DCSFQ_BVM 增量分流约 0.285；
- P2 读电流、重复性和 120 µA R0 擦除；
- 已保存运行的字节级重复哈希。

Thevenin 值是已测范围的经验拟合，不是 BVM 的普适线性源阻抗。哈希是确定性证据，不是数值收敛或物理正确性证据。

## 5. 当前不可作为事实的旧解释

- BQ 失败必然由 BJs 裸结欠阻尼唯一造成；
- 低 \(I_c\) 因 Josephson 电感增大而对所有拓扑都数学无解；
- BQ 输出电流小于 JTL 结的 \(I_c\)，所以必然推不动；
- K 互感只适合 MHz–GHz 而不适合皮秒；
- RB+LRB 的数值证明完整单元恰好临界阻尼；
- DCSFQ 平台不累积的详细机理已经确认；
- 本地论文足以证明“全球首次/文献空白已确认”。

这些可以作为假设设计对照实验，不能作为冻结物理结论。

## 6. 当前任务：Reference / Source / Receiver Characterization

### A. 已完成的 Phase −1 计量修复（历史入口）

1. `P()` 明确为 rad，派生相位统一除以 \(2\pi\)；
2. 用事件前后稳定窗或匹配的零输入控制；
3. 把连续快速样本聚类，停止把样本数叫事件数；
4. 对同一 JJ 的同一对端点，按同一方向和同一时间窗计算电压面积 `∫Vdt/Φ0`；
5. 以标准 JTL 两事件、DCSFQ 300 µA 对照和 BQ v4 六个整数下游相位增量作为回归样例；
6. 补 0.1/0.05/0.025 ps 步长收敛；
7. 先用校准数据建立并冻结 `METRIC_SPEC_V2.md` 的测量/报告语义；全局整数残差、相位—电压面积残差、BVM 漂移、幅度和抖动接受容差仍为 `UNFROZEN`，不得由单一校准 fixture 推断；
8. 在各实验目录的 `data/metrics_v2/` 中重建 BASELINE/P0/P2/v4 JSON 和结论，不覆盖旧文件。

**M4–M7 交接状态（2026-08-12）**：M4-001 仍是被拒绝的历史候选（stand-in `S01` 重签已封存 request，且 A01 receipt 披露未授权删除日志），不得引用为完成证据。其后续合同 `JH-20260811-M4-003` 已在干净 worktree 中验收：`scripts/sfq_metrics_v2.py` 明确把 raw rad 转为圈数，且活动样本/区间绝不称为事件。其后的 `M5-LITE-PILOT-001` 经 A01 REWORK、A02 Copilot 独立复审和 Codex `ACCEPT` 后，已实现并回归验证 pre/activity/post 半开稳定窗、显式 ±方向、匹配零输入控制、严格阈值活动聚类及 activity 窗不足两样本拒绝。M6 的首个冻结候选 `JH-20260811-M6-001` A01 因合同将可修改交付物同时作为冻结输入而被 `REWORK_REQUIRED`；保留其证据但不得作为冻结完成。其 superseding 合同 `JH-20260812-M6-002` 已 `ACCEPTED`：两个唯一 0/300 µA DCSFQ 运行以同一 JJ 的直接 `V(Bn|XDCSFQ)`/`P(Bn|XDCSFQ)`、相同方向和实际 CSV 端点窗口报告相位—面积带符号残差，并经独立 raw 重算与最终 `verify-task` 复核。M7 的 `M7-LITE-001` 经 A01 证据闭环 REWORK、A02 独立复审和 Codex `ACCEPTED` 后，已完成合成 ground truth、canonical JTL 的直接同 JJ V/P 管线校准和 DCSFQ/BQ v4 历史回归；JTL 残差只报告，历史周期平台不称事件或 Gate。M8–M11 仍未完成。M7 证据：`research/tasks/M7-LITE-001/attempts/A02/CODEX-AUDIT.md`；M6 证据：`research/tasks/JH-20260812-M6-002/audits/C01/verdict.yaml`。

**M8 接受更新（2026-08-12）**：`JH-20260812-M8-001` 的 A01 在六次运行前已注册 0.1/0.05/0.025 ps、匹配零输入对照、比较窗口、观测量、任务局部稳定带宽和最大深度停止规则；其原始证据保留，但合同交付物模式和 verify-log 自引用哈希使该闭环为 `REWORK_REQUIRED`。不重跑原始 CSV 的 superseding `JH-20260812-M8-002` 已由 `audits/C01/verdict.yaml` `ACCEPTED`：两个相邻 refinement 的全部适用注册量进入预注册带宽。仅可称 loaded canonical JTL 校准 fixture 的有界数值收敛；它不提供全局数值容差或物理 Gate。

**M9 接受更新（2026-08-13）**：`JH-20260813-M9-004` 以独立 FROZEN 链闭环并被 `audits/C01/verdict.yaml` `ACCEPTED`。canonical `docs/research/METRIC_SPEC_V2.md` v2.0.0 现冻结 raw rad→turns、平台/端点差异、same-JJ P/V mapping、双符号、半开窗、匹配零输入控制、activity cluster、实际时间梯形面积、QA/三态、预注册收敛及输出契约；它明确 XLOAD P/V 为 `UNVERIFIED`、BQ/BVM mapping 为 `UNKNOWN`，且把 M8 bands 与 0.3 rad 都限制为非全局判据。它不定义 `INTERFACE_GATE_V1`、candidate 成功条件或任何物理 Gate。用户已授权 M10；M11 仍未启动。

**M10 接受更新（2026-08-13）**：`JH-20260813-M10-004` 已由 `audits/C01/verdict.yaml` `ACCEPTED`。它将保留的 BASELINE/P0/P2/BQ v4 历史 CSV 重建为 hash-bound `metrics_v2/` endpoint-arithmetic/provenance 产物，并以 central correction table 和 superseded banner 保留旧叙述。M10-003 的 scope-hash 冲突被保留为 REWORK 历史；M10-004 在不重跑 JoSIM、不修改 raw/legacy JSON、且逐项核验 11 个保存产物哈希的前提下完成重封存。该接受不构成 SFQ、fluxoid、同 JJ 面积、下游、candidate 或系统 Gate 结论；M11 仍未启动。

**M11 双子门接受更新（2026-08-13）**：`JH-20260813-M11A-001` A02/C02 与 `JH-20260813-M11B-003` A01/C01 均为 `ACCEPTED`，故 M11 基线冻结闭环。M11A 封存 M4--M10 的唯一 accepted/superseding 计量证据、M6 同 JJ 控制 raw、M8 fixture-local convergence 与回归；全局容差仍为 `UNFROZEN`，不构成物理或接口 Gate。M11B 的唯一 canonical facts 是 `docs/research/SCIENTIFIC_RECONSTRUCTION_OBJECT_MATRIX_V1.yaml`：它以 structured evidence/observable/provenance/reproduction/characterization/UNKNOWN/discriminator 冻结七对象的**当前 knowledge state**，并由 `docs/research/REFERENCE_PROVENANCE.md` 指向。M11B/W5B 的接受不表示 circuit physical knowledge complete、published reproduction complete、characterization complete、candidate validated，亦不完成 W5A/W5C。M11B-001/002 的历史 rework 仍保留。候选路线、`INTERFACE_GATE_V1` 与 T1 仍须单独授权和预注册。

**M11 metadata errata（2026-08-13）**：M11A/M11B 的科学 baseline 保持 `ACCEPTED`；`errata/chronology.yaml` 只为各自 hash-bound 的历史非单调时间戳建立最小例外，新的 `handoff.py` 则强制 `request ≤ ACK ≤ receipt ≤ audit`。M11A `C03` 更正 metadata：M4/M5/M6/M7 的 immutable A02 logs 分别为 15/29/21/18，M9/M10 为 59/13，总计 155；不修改冻结 receipt、baseline 或 C02，也不重跑 JoSIM。

**BVM-S0 scientific disposition（2026-08-14）**：`JH-20260814-BVM-S0-004` C02 对 sealed S0-001 raw、S0-002/003 sealing chain、S0-004 deterministic corrected report 和 Copilot review 完成只读科学审计。固定模型/12 Ω fixture/两种 operational initialization/单次 project-derived read PWL 下，source-port `V(SL1)`、`I(L_SL|XBVM1)` 与 direct JM1/JM2 P/V 的逐 timestep 命名窗口观察可用作有界 simulation facts；例如 positive-read 的 source-voltage峰值为 0.890/0.901/0.904 mV、source-current峰值为 74.18/75.06/75.30 µA（0.1/0.05/0.025 ps）。但注册的 0.1→0.05 ps matched-control latency 差为 0.85 ps，超过 0.5 ps task-local band，因此 artifact 是 `VALID` 而最终 scientific disposition 必须是 **`INCONCLUSIVE`**。这不构成收敛 source baseline、state preservation、logical read0/read1、SFQ/fluxoid、receiver、`INTERFACE_GATE_V1`、candidate 或路线结论。

**当前 active phase（2026-08-14）**：进入 **Reference / Source / Receiver Characterization**。BVM source preflight 已完成并有一组 sealed、numerically INCONCLUSIVE 的最小 source observations；若继续，必须先由用户授权新的预注册 convergence/characterization task，产生新的 immutable runs。不得从本 S0 审计直接开始 receiver、BQ、DCSFQ_BVM、`INTERFACE_GATE_V1` 或参数调优。

**2026-08-18 stable-load 接受与 VIZ-002 停止决定**：`JH-20260817-BVM-S2-STABLE-LOAD-001` A01/C01 已接受固定 closure、historical-S1 initialization、`dt=0.0125 ps` 下的 16-run（1/12/25/50 Ω × positive/negative × read/control）source characterization：全部八个 load/polarity strata 的 JM1/JM2 PRE `[80,90)` p2p 均满足 `<=0.020 rad`，故受限的 per-load terminal observations 可用；两极性的五个 exact Decimal endpoint-VI tokens 都 eligible、但均为 `NOT_SUPPORTED`，只限制该冻结诊断，不是普适 source 模型或 BQ/receiver 结论。此前 S0 的 fixed-fixture `VALID + INCONCLUSIVE` 历史不被改写。随后的 `JH-20260817-BVM-S2-STABLE-LOAD-VIZ-002` A01–A04 仅是 descriptive report 尝试；C04 保持 `REWORK_REQUIRED`，用户已明确决定在 C04 后**有意停止** VIZ-002。其余发现只涉及 descriptive visualization completeness，不影响已接受的 STABLE-LOAD-001 scientific evidence 或 conclusions。今后 custom interactive dashboard 不是 BVM scientific acceptance gate；默认波形查看使用已接受 JoSIM raw CSV、官方/仓库简单 plotting，或一次性简单 Plotly/Matplotlib 图。除非未来某一科学问题明确以特殊可视化为必要证据，否则 visualization 只作 descriptive convenience，且不再开展 visualization workflow maintenance。下一科学决策是单独预注册 BVM source envelope → BQ receiver characterization；在新合同签发前不得运行、调参或宣称 receiver/BQ/interface 结论。

**BVM logical semantics freeze（2026-08-19）**：用户（项目负责人）正式冻结 `docs/research/BVM_LOGICAL_SEMANTICS_V1.md`，锚定 exploration checkpoint `a6ab474`（2×2 state/READ matrix）：logical 1 = +100 µA WL+BL init（state A）；logical 0 = −100 µA WL+BL init（state B）；canonical READ = positive polarity（WL+SE +100 µA，96–105 ps）；downstream semantics 冻结为 **1→exactly 1 SFQ、0→0 SFQ**（目标语义，非当前 raw 行为）。当前 raw readout：logical1+canonical READ → strong multi-turn R-loop running（JS1 ≈ −2.994 turns）；logical0 → weak edge-dominated / no-running（≈ −0.0026 turns）；A/−READ 与 B/−READ 仅为 polarity diagnostic，非 canonical READ。**~3 phase turns 不得称 3 SFQ**；receiver/transducer 的任务是把 logical-1 strong response 转成 exactly one JTL-receivable SFQ 而 logical-0 不触发。可视化（4 个 HTML，`test/exploration/bvm-internal-readout-20260819/plots/`）为 descriptive convenience，不产生新 authority。下一科学步骤（receiver/transducer 设计）仍需用户单独授权与预注册。

**研究计划同步（2026-08-12，用户采纳最终研究流程与协作方案）**：M7 保持单编号下设 `M7A`（数学 ground truth 单元测试）/ `M7B`（canonical JTL 电路验证）/ `M7C`（历史回归，expected 必须来自独立人工/raw 重算预注册 frozen constants，禁止 production analyzer 自证）；M8 为预注册 stopping rule 的有界收敛 procedure（0.1/0.05/0.025 ps 起点，稳定带宽=PASS，最大深度仍不稳=INCONCLUSIVE）；M9 只冻结 `METRIC_SPEC_V2.md`（怎么测），接口成功标准由独立的 `INTERFACE_GATE_V1` 在 Reference/Source/Receiver 事实层建立后冻结；M11 单编号双子门（M11A Measurement Calibration Baseline + M11B Scientific Reconstruction Baseline，都通过才标绿）；W5 拆 W5A 文献边界 / W5B Reference Provenance（可与 M7 并行）/ W5C 作者询问（需用户授权、time-box）。所有科研任务声明 `EXPLORATORY | CALIBRATION | CONFIRMATORY` 阶段语义；参数 provenance 标记与 R0–R3 reproduction 原则见 `memory/project-todo.md` §I 与 `docs/research/REFERENCE_PROVENANCE.md`（W5B）。

### B. 公平重测两条接口路线

**BQ v4**（等待 Phase −1 指标与容差冻结）：单次 PWL、90–110 µA 细扫、真实 BVM 波形、读 0/1、下游 JTL、参数单变量与鲁棒性。

**DCSFQ_BVM**（等待 Phase −1 指标与容差冻结）：重新定位响应边界；正确反转输入源极性；有限扫描 area/IB1/L2/L3；先理想单脉冲和 JTL，再真实 BVM 级联。

### C. 系统 Gate

- 读 1：下游 JTL 恰好一个事件；
- 读 0：零事件；
- 重复读：不丢失、不多发；
- BVM 状态不被破坏；
- 步长和关键参数扰动下仍成立。

上述“恰好”、“不被破坏”和“仍成立”的数值容差必须在独立的候选/接口 Gate 合同中由校准数据事先冻结，并引用 `METRIC_SPEC_V2.md` 的测量语义；不得在看到候选设计结果后移动。

在这些完成前，不启动最终论文结论和 T1 端到端声称。

## 7. 关键资产

| 类别 | 路径 |
|---|---|
| 完整审计教程 | `docs/guide/project-guide.md` |
| JoSIM 相位输出 | `src/Output.cpp`, `docs/tech_disc.md`, `docs/ex_usage.md` |
| 错误指标脚本 | `scripts/sfq_metrics.py` |
| BVM | `circuits/bvm/bvm_cell.cir` |
| BQ / v4 | `circuits/qb/bq_cell.cir`, `circuits/qb/bq_cell_v4.cir` |
| DCSFQ / 改版 | `circuits/standard/DCSFQ.cir`, `circuits/interface/DCSFQ_BVM.cir` |
| JTL | `circuits/standard/JTL.cir` |
| T1 | `circuits/t1/t1_cell.cir` |
| BVM→BQ 基线 | `test/final/single_bvm_qb/` |
| BQ v4 扫描 | `test/final/qb/test_bq_v4_sweep.cir`, `test/final/qb/data/bq_v4_sweep*.csv` |
| Phase 0 | `test/final/interface/` |
| P2 | `test/final/bvm/` |
| 论文 | `arti/` |
| 项目工作流 skills | `.agents/skills/`（canonical），`.claude/skills/`（兼容链接） |
| Codex–Claude 完整工作流 | `research/WORKFLOW.md` |
| Claude Code 执行入口 | `research/CLAUDE_EXECUTOR.md` |
| 文件化任务包 | `research/tasks/<task-id>/` |

## 8. 实验纪律

1. 使用并记录 `build/josim-cli` 版本，不混用系统安装的旧二进制；
2. 原始 CSV 保存到仓库实验目录，绝不只留 `/tmp`；
3. 使用单次 `pwl(...)` 做因果实验；`pulse(... period)` 会重复；
4. 每次记录时间步、窗口、对照、单位和列方向；
5. 不用人工目测代替可执行指标，但指标必须先有单元测试；
6. 同时报告原始 rad、归一化圈数、电压积分和下游响应；
7. 机制解释标为“推断”，除非有单变量对照；
8. 固定网表重复哈希与时间步收敛分别检查；
9. 研究单元目前未接入 CTest，不能把人工波形测试称为正式回归；
10. 不覆盖旧原始数据；用审计警告和新版本结果保留可追溯性。
11. `josim-plot2.py -j 2pi` 当前仅 `combined`/`sep_comb` 真正缩放相位；`grid`/`stacked`/`square` 只改标签。修复 M12 前遵循 `josim-viz` 的布局限制。
12. 委派执行必须先验证签名 request 并 ACK；执行者不得修改 request、审计、todo、HANDOVER、CHANGELOG 或冻结 raw。合同完成与物理 Gate 分开裁决。

## 9. 当前一句话状态

> BVM 的稳定相位状态和状态相关电流已有仿真支持；直接 BVM→当前 BQ 基线的输出支路未完成完整绕转，且该网表未测 JTL；BQ v4 在理想周期电流的 110–150 µA 已测点显示与约 1:1 JTL 传播相容的相位平台，完整 Gate 尚未通过；DCSFQ_BVM 在 68.4 µA 测试输入下未见完整输出。Phase −1 的 M4–M11 已接受：M9 冻结测量/报告语义，M10 重建并封存历史 endpoint arithmetic/provenance，M11 冻结计量与当前 reconstruction knowledge state。**BVM-S0 本周已闭环（2026-08-14）**：D0 initial-state readiness bound=75 ps 接受；BVM-S0 12-run canonical source 实验在固定 12 Ω fixture 下完成，S0-001 原始证据、S0-002/003 sealing/provenance 链、S0-004 deterministic corrected report 与 Copilot skeptical review 全部完成；Codex scientific audit（C02）最终裁决 **artifact=VALID + scientific disposition=INCONCLUSIVE**——正读源响应（V(SL1) 0.890/0.901/0.904 mV，I(L_SL) 74.18/75.06/75.30 µA，latency≈5 ps）与负读响应（−0.307/−0.315/−0.317 mV，−25.57/−26.27/−26.39 µA，latency≈10 ps）是有界 fixed-fixture simulation facts，但注册的 0.1→0.05 ps matched-control peak-latency 差 0.85 ps > 0.5 ps task-local band，故**未建立 converged source baseline**，也不得把 INCONCLUSIVE 当实验失败。未接受：resolution-independent source baseline、logical 0/1、state preservation、SFQ/fluxoid count、receiver、Gate、route、published/hardware reproduction。任何后续 convergence/characterization 必须单独预注册新任务并产生新 immutable runs；候选 Gate 的数值容差仍须另行预注册并冻结。
