---
name: current-research-state
description: 项目当前研究问题、最近重要结果、现行验收标准和可授权下一选项
metadata:
  type: project
  last_updated: 2026-09-03
---

# 当前状态

## GOAL

建立可复现、可解释、可由标准 JTL/T1 消费的 BVM→QB 数字化接口：

```text
BVM state / accumulated sensing current
→ QB quantized pulse burst
→ JTL transport / regeneration
→ T1 / downstream logic
```

对于 equal-weight array，核心功能语义是 expected active-BVM count 与 downstream
quantized pulse/count 对应；single canonical logical semantics 仍遵循
`BVM_LOGICAL_SEMANTICS_V1.md` 的 `1 → 1 event, 0 → 0 event`。

## CURRENT ACCEPTANCE STANDARD

未来新实验默认使用：

```text
docs/research/BOUNDARY_SPEC_V2.md
```

核心原则：

- **functional correctness first**；
- dense SFQ burst 合法，不冻结统一 minimum inter-pulse spacing；
- 旧 `0.25 ps` quiet-gap 只作为 strict/diagnostic，不再是 Functional PASS 硬门槛；
- expected QB count、JTL end-to-end count/polarity、T1/logic result 是硬功能检查；
- same-JJ phase/voltage-area 与 registered closed-loop fluxoid consistency 是硬 physics supporting evidence；
- 对关键功能结论，预注册的 fine timestep refinements 必须保持功能分类一致。

`BOUNDARY_SPEC_V1.md` 仍是旧 A001 retrospective contract；`METRIC_SPEC_V2.md`
仍是 frozen measurement/reporting contract，不被 V2 追溯改写。

## LAST IMPORTANT RESULTS

### Historical 4-BVM BVMSim-compatible chain

RJ1×timestep robustness 实验已完成 24 个 effective runs 并经 Sol XHigh review：

```text
RJ1=12 Ω:   0.1 ps ≈4-turn；0.05/0.025/0.0125 ps ≈5-turn
RJ1=11.5 Ω: 0.1/0.05 ps ≈4-turn；0.025/0.0125 ps ≈5-turn
RJ1=11 Ω:   0.1/0.05 ps ≈4-turn；0.025/0.0125 ps ≈5-turn
```

因此降低 RJ1 会移动 coarse→fine trajectory transition，但目前没有证明
11.5 Ω 或 11 Ω 在 fine timestep 下解决 count mismatch，也没有 winner。当前审阅
主分类为 `TIMESTEP_SENSITIVE`。

同时，JTL end-to-end net behavior 强烈显示：QB 走约4-turn时 JTL6 约4，QB 走
约5-turn时 JTL6 约5；JTL 更像是在传输/整形 QB burst，而不是主要 count-error
来源。旧 per-stage quiet-gap segmentation 尚未建立严格逐颗 event identity，因此
未来应按 `BOUNDARY_SPEC_V2` 做 burst-level transport reassessment，而不是把旧
segment count 当作唯一 Functional Gate。

实验：

```text
test/exploration/bvm-qb-rj1-timestep-robustness-v1-20260903/
```

### Canonical vs historical BVM

当前仓库的 `circuits/bvm/bvm_cell.cir` 与 `BVMSim/bvm_cell.cir` 不应视为等价 source。
除 `R_JM1=6 Ω` vs `8 Ω` 外，当前 netlist 文本中的 JM2 loop participation/节点连接
也不同。historical 结果不能自动升级为 canonical compatibility；下一阶段必须先以
canonical source 实测 unit sensing waveform / QBin scale，再决定 QB calibration。

## CURRENT QUESTION

当前最重要的问题已从“每颗 SFQ 是否被严格 quiet-gap detector 分开”改为：

1. canonical BVM 的真实 unit sensing / QBin waveform 与 historical BVMSim 有何差异；
2. 对预注册 expected count，QB 在 fine timestep 下是否给出正确 quantized burst count；
3. JTL 是否 end-to-end 保持 count/polarity 并可由 T1 消费；
4. BVM storage/readout closed-loop fluxoid 是否与逻辑状态和 non-destructive read 一致；
5. 哪个 QB operating point 在 canonical source 下同时满足功能正确与 numerical robustness。

## STATUS

`AWAITING_USER_REVIEW`。最新 RJ1 robustness 实验已完成并停在 human gate。
`BOUNDARY_SPEC_V2` 只更新未来判据，不授权新的 JoSIM run、参数 sweep 或 canonical
migration experiment。

## NEXT OPTIONS

1. 用户审阅并接受 `BOUNDARY_SPEC_V2` 作为未来实验默认 acceptance contract。
2. 获得单独授权后，设计最小 canonical-vs-historical BVM source characterization，
   重点比较 loop topology、stored-state/fluxoid、SL/QBin waveform 和 unit sensing scale。
3. 使用现有 4-BVM raw 做 analysis-only JTL burst-level transport reassessment，按
   V2 的 end-to-end count / burst area / envelope-forward criteria 判断 Functional transport。
4. 在 canonical unit-input scale 建立后，再重新决定 QB bias/RJ1 等 operating-point 参数；
   不从 historical 11/11.5/12 Ω 结果直接选 winner。
