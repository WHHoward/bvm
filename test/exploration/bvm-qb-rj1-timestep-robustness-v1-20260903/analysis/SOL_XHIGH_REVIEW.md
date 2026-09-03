# SOL_XHIGH_REVIEW

审阅角色：`josim_architect`（Sol XHigh，只读）  
审阅时间：`2026-09-03`  
审阅对象：`a1d80077404bf7f2651c25374d44a9cf989ad616`（`a1d8007`）  
审阅请求：`BVM_QB_RJ1_TIMESTEP_ROBUSTNESS_V1`

## Review disposition

- raw/deck 证据包：`VALID`。
- 四-BVM primary classification：`TIMESTEP_SENSITIVE`。
- RJ1=12 Ω：仅作 `BASELINE` 参考，不代表性能通过。
- RJ1=11.5 Ω、11 Ω：`INCONCLUSIVE`，没有 winner。
- single-BVM protection：`INCONCLUSIVE`。
- QUICK label：`QUICK / ARTIFACT_VALID / FOUR_BVM_TIMESTEP_SENSITIVE / PROTECTION_INCONCLUSIVE / NO_RJ1_WINNER`。
- 处置：`ANALYSIS_CORRECTION_REQUIRED`；不授予 Formal PASS，不授权后续实验。

## Independent findings

1. 24 个 effective run 的 deck、raw、command 哈希与 provenance 一致；四-BVM `attempt-03` 的选择可辩护。它只补齐 `P/V(BVMOUT)` 并修正 include 路径；12 个 four-BVM run 的初始 raw 与 attempt-03 的 53 个共同列逐样点一致。attempt-02 的路径失败没有被当作成功结果。
2. phase 使用 raw JoSIM radians，经连续 unwrap 后除以 `2π`；同一 JJ 的 phase 与 voltage-area 配对；comparison 使用共同时间戳、不插值。没有发现单位、符号或 source-boundary 混淆。
3. 三个 RJ1 都观察到 coarse 约 4-turn 与 fine 约 5-turn 的 BJ2 net trajectory。固定同一 RJ1 时只能作操作性描述：这是 timestep-conditioned trajectory selection / timestep sensitivity；现有证据不足以证明已识别的 timestep-induced dynamical branch switch，也不是 timestep convergence proof。
4. fine BJ2 是一个约 `4.023–4.025` turn 的连续主 segment，之后还有约 `0.973–0.975` turn 的 sub-unit segment；strict 结果是主 segment `1 complete / 0 clean separated`，不能解释为四个或五个 separated SFQ。`continuous_multi_turn_running` 标签本身也不等于完整机制证明。
5. fine JTL B02 的 complete/clean 序列为 `JTL1 (1,0) → JTL2 (1,0) → JTL3 (2,1) → JTL4 (2,1) → JTL5 (2,1) → JTL6 (5,5)`。这不是逐级一对一，也没有建立 BJ2 source-event identity 到 JTL6 的逐事件对应；部分 onset 顺序还不满足 forward monotonicity。
6. single-BVM 中，S0 在本 fixture/read+post 窗口内没有 complete false trigger；S1 的 BJ2 有约 `1.0035–1.0075 Φ0` 的 source-level local observation，但 JTL1–JTL5 B02 约 `0.91` turn，JTL6 约 `1.067` turn，且 onset 不构成逐级递增。因此不能宣称完整六级 protection。
7. 没有证据支持 11.5 Ω 为 winner、11.5/11 Ω 为 `ROBUST_CANDIDATE`、降低 RJ1 已消除 late activity，或差异已经被证明来自 overdamping/margin loss。

## Required analysis corrections

审阅指出以下问题属于 analysis/report 语义层，不要求修改 raw/deck 或重跑仿真：

- 将原先的 “JTL count/order flags PASS” 改为分别报告：count 是否相同、order observation 是否相同，以及物理 order 在两个 fine timestep 中均为 `False`。
- 将 `candidate >= 0.2 turn` 标为 `POST_HOC_DESCRIPTIVE_NOT_PREREGISTERED`，不纳入 fine-pair 预注册标准。
- S0 的 JTL false-trigger 检查同时覆盖 read 和 post 窗口。
- `S1_source_same_event_approximately_one_phi0` 现在真正检查 source BJ2 的 phase、voltage-area 和 residual 描述条件，并明确这些 bounds 是 post-hoc descriptive，不是冻结 Gate。
- 将“各次 solver exit code 均为 0”限定为“各 effective valid run 为 0”；attempt-02 的失败 exit code 为 `255`。

以上修正已在 `analysis/analyze.py`、`analysis/make_summaries.py` 中完成，并已从原始 raw 重新生成派生 metrics/summary；未重新运行 JoSIM。

## Gate

`analysis/human-gate.yaml` 保持：

```yaml
state: AWAITING_USER_REVIEW
user_reviewed: false
next_step_authorized: false
automatic_next_experiment: false
stage_b_authorized: false
next_action: STOP
```

本实验不证明 canonical BVM compatibility、timestep convergence、process margin、T1 或 paper mechanism identity。没有执行 0.00625 ps、更改参数、canonical BVM、后续 branch diagnostic 或任何自动 follow-up experiment。
