# RESULT_BRIEF

## 1. What changed

在完全相同的 4-BVM → BVMSim QB → 六级 JTL fixture 上，新建 T100/T050/T025/T0125/T100_FULL 独立 raw；仅改变 `.tran` 控制行，历史 raw 保持不变。

## 2. What held fixed

BVMSim historical BVM、四路 accumulated sensing line、active BVMSim QB、250 µA QB bias、原始 BVMSim JTL、10 Ω load、source waveform、stop time、共享 `jjmit` 与 solver binary 均固定。canonical BVM 未使用。

## 3. Why tested

区分历史约 4-turn 与 Stage-A 约 5-turn 的数值分支差异，且检查净相位位移是否真的由分离、re-trapped 的局部事件组成。

## 4. What happened（最多六点）

- 新 T100 raw hash 与历史 `BVMSim/data_tran.csv` 不同列布局但数值共同信号逐点一致；T100_FULL 在 45 ps 之后与 T100 一致。
- T100 BJ2 READ1 net turns=3.999517；细网格 T025=4.999188、T0125=4.999092。
- BJ2 的约 4/5-turn 位移由连续多-turn segment 主导，不应写成四个/五个 clean SFQ。
- 细网格下游 JTL6 B02 存在第五个约单位量级完整段，但上游 BJ2 与 JTL1 B01 的事件身份不满足四个 clean separated transport 条件；各级计数仅作本地 stage summary。
- KCL 使用 shared `bvmtools.kcl` 验证；详细残差和每个 junction 的 phase/area/event list 在 `analysis/metrics.json`。
- 首个既有 raw 分歧是不同阈值下的 crossing：JTL1 B01 phase-only 约 117.3 ps，BJ2 phase+voltage paired 约 120.4 ps；不能由此推断因果先后。

## 5. Physical meaning

Observed 结论是：该固定 exploratory fixture 对 timestep 很敏感，并出现约 4 与约 5 turns 的数值轨迹分支。Sol XHigh reviewer 的结论是对 timestep-conditioned numerical branch-change candidate 部分支持（中等偏强），但仍不等于 timestep convergence、离散 SFQ count，或已证明 JTL 生成/传输了第五个 SFQ。

## 6. What it does NOT prove

不证明 canonical BVM compatibility、single-BVM compatibility、一个 BVM contribution 对应一个 SFQ、timestep convergence、process margin、T1 compatibility、paper mechanism identity 或 unique QB operating mechanism。

## 7. Current status

Sol XHigh reviewer 已完成审查：4→5 归因为 timestep-conditioned numerical branch-change candidate 仅部分支持；在用户 review 前保持 `AWAITING_USER_REVIEW`，不启动后续实验。

## 8. Possible next options（不执行）

1. 由用户决定是否把 branch-change 候选升级为 Candidate 级复核。
2. 在重新授权后单独设计 event identity/transport 的受控 follow-up。
3. 在重新授权后再考虑 canonical BVM 路线；本 Quick 不执行。

## Evidence files

- `analysis/EVENT_COUNT_CONVERGENCE.md`
- `analysis/FIRST_DIVERGENCE.md`
- `analysis/metrics.json`
- `plots/RESULT_TIMESTEP_BJ2.html`
- `plots/RESULT_TIMESTEP_JTL1.html`
- `plots/RESULT_EVENT5_CANDIDATE_ORDER.html`
