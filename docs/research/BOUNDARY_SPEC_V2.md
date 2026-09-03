# BOUNDARY_SPEC_V2 — Functional-First BVM→QB→JTL→T1 Acceptance Contract

```yaml
spec_version: BOUNDARY_SPEC_V2
status: CURRENT_PROJECT_ACCEPTANCE_CONTRACT
scope: future BVM→QB→JTL→T1 experiments and new reassessments
supersedes_for_future_work: BOUNDARY_SPEC_V1
retroactive_reclassification: false
measurement_contract: docs/research/METRIC_SPEC_V2.md
logical_semantics: docs/research/BVM_LOGICAL_SEMANTICS_V1.md
```

## 0. Purpose and compatibility boundary

本规范从现在开始定义项目的**功能验收、物理一致性与数值鲁棒性**。核心原则是：

> **Functional correctness first; physics consistency is mandatory supporting evidence; strict pulse isolation is higher-level qualification, not the minimum functional gate.**

`BOUNDARY_SPEC_V1.md` 保留为 frozen A001 retrospective contract，不修改、不追溯重判其历史 artifact。`METRIC_SPEC_V2.md` 继续只定义“怎么测、怎么报”，不被本文件改写成新的 measurement semantics。

论文机制参考为 Karamuftuoglu et al., arXiv:2507.04648v1 (2025)：QB 根据 BVM accumulated current 产生可变数量 SFQ pulse；多个 pulse 可以在 short time frame 内形成 burst，后续由 T1/JTL 消费。因此本项目**不冻结统一 minimum inter-pulse spacing**。

## 1. Source identity is a hard requirement

每个实验必须明确 source class：

```text
CANONICAL_BVM      = circuits/bvm/bvm_cell.cir
HISTORICAL_BVMSIM  = BVMSim/bvm_cell.cir
```

两者不得默认 electrically equivalent。任何 BVM→QB calibration、count mapping、margin 或参数推荐都必须声明适用 source class；historical BVMSim 结果不能自动升级为 canonical compatibility。

## 2. Boundary model

### B0 — BVM state / sensing / SL transmission

职责：

```text
stored state → state-dependent analog sensing waveform → SL/QBin
```

Functional hard checks：

- logical state / active-row pattern 与预期一致；
- READ 后 QBin/SL response 在目标 load 下可用且可区分；
- 不要求 `BVMout` 或 SL-load JJ 自身发生 `2π` slip；
- 若实验声称 non-destructive read，必须检查 storage-state preservation。

Physics checks：

- canonical/historical topology 与端点 provenance；
- 注册的 superconducting closed loop 上检查 fluxoid consistency；
- 不能用单个 load-JJ 是否 slip 代替 whole-loop / sensing-function 判断。

### B1 — QB selective triggering

职责：

```text
state-dependent / accumulated QBin waveform → intended QB activation
```

Functional hard checks：

- expected active condition 必须触发目标 response；
- expected inactive condition 不得出现 comparable false trigger；
- initialization/bias transient 必须与 READ-associated response 分离。

B1 不要求 pulse 已经被 strict detector 分成 clean SFQ。

### B2 — QB quantization and count

职责：

```text
analog accumulated input → correct quantized burst count
```

对于 equal-weight N-active-BVM fixture，默认功能语义是：

```text
N active BVM → N downstream-usable quanta/pulses
```

对于 weighted / multiplier / other mapping，`N_expected` 必须在 experiment preregistration 中定义，禁止看结果后修改。

**Count correctness 是 HARD gate。** 例如 equal-weight 4-BVM fixture 若可靠 downstream observation 为 5 quanta，则为 `FUNCTIONAL_FAIL` / `FUNCTIONAL_COUNT_MISMATCH`，不能因为波形“像 SFQ”而判 PASS。

B2 允许 dense SFQ burst：

- 不要求固定 pulse-to-pulse spacing；
- 不要求每颗 pulse 之间 `|V|<0.2 µV` 持续 `0.25 ps`；
- 不要求旧 quiet-gap detector 必须切出 N 个 separated segments。

但必须有足够证据证明**总量子数与 downstream functional count**。

最低物理证据：

1. same-JJ phase/voltage-area consistency：
   `Δphi/(2π)` 与 `∫Vdt/Phi0` 必须在同一 JJ、同一方向、同一局部/burst boundary 上一致；
2. burst-total quantization：对 dense burst 可以报告总 `N Phi0`，不强制人为切成 N 个 isolated event；
3. 若 pulse 可可靠分辨，再补 per-pulse local `~1 Phi0` evidence。

`phase turns ≈ integer` 单独不能定义 SFQ count。

### B3a — JTL acceptance / launch

职责：

```text
QB output burst → JTL1 accepted response
```

Functional hard checks：

- JTL1 接收到与 QB output count/polarity 一致的 burst；
- load backaction 可以存在，但不能导致功能 count 错误；
- QB→JTL interface 在 target load 下可工作。

### B3b — JTL transport / regeneration

职责：

```text
JTL1 → JTL2 → ... → JTLn
```

Functional hard checks：

- end-to-end quantum/pulse count preserved；
- polarity preserved；
- burst/energy packet 具有 forward transport evidence；
- 不发生 downstream extra-copy 或 loss；
- target receiver 可以消费输出。

`B02` 继续作为 BVMSim `jtl2.cir` 的 output-facing marker，`B01` 为 input/internal marker。

对于 dense burst，**不要求每一级都被同一 quiet-gap segmentation 切出相同 N 个 segment**。允许 JTL regeneration / reshaping 使下游 pulse identity 更清楚。Functional transport 可由以下组合建立：

- 每级/端到端 burst-total phase-area quantization；
- final-stage resolved count；
- burst-envelope forward latency / correlation；
- downstream logic consumption。

逐颗 `event_k` 的 JTL1→...→JTLn identity 属于 stronger/strict evidence；若无法建立，不自动否定已被 end-to-end evidence 支持的 Functional transport。

### B4 — T1 / logic consumption

职责：

```text
JTL output burst → correct logic result
```

Functional hard checks：

- T1/logic 对输入 pulse count 给出正确 sum/carry/logic result；
- required asynchronous carry 在 clock deadline 前完成；
- synchronous output 在目标 clock 条件下正确；
- 不因 burst 密集而出现 count corruption。

若 B4 已直接证明最终 arithmetic 正确，它是 B2/B3 functional interpretation 的强 downstream evidence，但不能替代明显的 physics inconsistency。

## 3. Physics consistency — HARD supporting layer

### 3.1 Same-JJ Josephson identity

遵循 `METRIC_SPEC_V2`：

```text
(1/Phi0) * integral(V_jj dt) ≈ Δphi_jj/(2*pi)
```

必须 same JJ / same endpoints / same sign / same window / same run。

### 3.2 Whole-loop fluxoid consistency

对声明为 superconducting closed loop 的路径，优先检查 gauge-invariant fluxoid constraint，而不是简单要求磁性部分 `LI/Phi0` 时时为整数：

```text
n_loop ≈ Phi_loop/Phi0 + Σ(s_j * phi_j)/(2*pi),   n_loop ∈ Z
```

其中 loop topology、JJ orientation、inductive-flux sign 必须在分析前注册。

适用重点：

- BVM storage loop：write 后 fluxoid state、READ 前后 state preservation；
- BVM readout loop：READ 时的 loop-state / current redistribution；
- QB/JTL：只有在真实 closed superconducting contour 被 topology audit 明确后才计算，不得凭视觉任意拼 loop。

磁通本身非整数不自动表示错误；必须与 JJ gauge-invariant phase contribution 一起判断。

## 4. Numerical robustness — HARD for decisive functional claims

单一 timestep 不能作为关键功能结论的唯一依据。

任何用于推荐设计参数、声明正确 count 或推进 system boundary 的实验，必须预注册 timestep refinement procedure。至少要求：

- 相邻两个 finest registered refinements 的**功能分类一致**；
- expected count / observed count 一致；
- polarity 一致；
- no-extra / no-loss 结论一致；
- 关键 phase-area quantities 在 experiment-local preregistered bands 内一致。

具体 timestep 和数值 tolerance 不是全局常数，必须 task-local preregister；`0.025/0.0125 ps` 只能作为当前实验实例，不自动成为全局规范。

若 finer timestep 改变功能 count（例如 4→5），则标记 `TIMESTEP_SENSITIVE`，较粗 timestep 的“正确结果”不能作为最终 Functional PASS。

## 5. HARD vs SOFT criteria

| Criterion | Class |
|---|---|
| logical/state mapping correct | HARD |
| expected QB quantum/pulse count correct | HARD |
| JTL end-to-end count preserved | HARD |
| polarity preserved | HARD |
| downstream logic result correct | HARD when B4 is in scope |
| same-JJ phase/area consistency | HARD physics |
| registered loop fluxoid consistency | HARD physics |
| fine-refinement functional classification stable | HARD for decisive claims |
| fixed minimum inter-pulse spacing | NOT A GLOBAL REQUIREMENT |
| fixed 0.25 ps quiescent gap | SOFT / strict diagnostic |
| every JTL stage segmented into identical N events | SOFT / strict evidence |
| small ringing | SOFT unless it corrupts function/state |
| exact retrap time | SOFT / robustness |
| visually ideal pulse shape | SOFT / publication-quality |

## 6. Verdict vocabulary

Primary functional verdict：

```text
NOT_TESTED
FUNCTIONAL_PASS
FUNCTIONAL_FAIL
INCONCLUSIVE
```

Additional flags：

```text
PHYSICS_WARNING
TIMESTEP_SENSITIVE
FUNCTIONAL_COUNT_MISMATCH
```

Strict qualification：

```text
STRICT_QUALIFIED
NOT_YET_QUALIFIED
```

允许组合，例如：

```text
FUNCTIONAL_PASS + PHYSICS_WARNING
FUNCTIONAL_FAIL + FUNCTIONAL_COUNT_MISMATCH
INCONCLUSIVE + TIMESTEP_SENSITIVE
```

`STRICT_QUALIFIED` 必须建立在 Functional PASS、physics consistency、数值鲁棒性和必要 margin/robustness evidence 之上。

## 7. Reporting contract

每个新实验至少明确：

```text
source_class
expected_function / expected_count
changed variables
frozen variables
functional verdict
physics status
numerical robustness status
strict qualification status
```

报告继续分：

```text
OBSERVED
INFERENCE
UNKNOWN
```

对于 pulse/burst，至少分开报告：

```text
net/burst phase turns
burst voltage area / Phi0
resolved local pulse structures if identifiable
downstream final count
logic result if tested
```

禁止把 `whole-window net turns`、`Vpeak`、`I>Ic`、旧 `fast_events` 或单一 detector segment count 自动升级成 SFQ count。

## 8. Current project interpretation examples

这些例子只说明 V2 语义，不追溯修改旧 experiment verdict：

- `1 active BVM → source ~1 Phi0 → JTL/T1 consumes one`：可支持 Functional PASS，哪怕 pulse 周围有小 ringing。
- `4 active equal-weight BVM → dense ~4 Phi0 burst → JTL final count 4 → T1 arithmetic correct`：可支持 Functional PASS，即使上游没有四段 0.25-ps quiet gaps。
- `4 active equal-weight BVM → downstream reliable count 5`：`FUNCTIONAL_FAIL + FUNCTIONAL_COUNT_MISMATCH`。
- `0.05 ps gives expected count, finer 0.025/0.0125 ps consistently give a different count`：`TIMESTEP_SENSITIVE`；不得用 coarse result 宣称设计正确。

## 9. Human gate

本规范只定义判据，不授权任何新的 JoSIM run、参数修改或 canonical migration。每个实验仍遵循：

```text
QUESTION → MINIMUM QUICK → RESULT → USER REVIEW → NEXT / ARCHIVE
```

用户 review 仍是推进下一物理实验的 gate。
