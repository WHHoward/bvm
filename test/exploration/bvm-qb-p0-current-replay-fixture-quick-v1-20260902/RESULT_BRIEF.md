# BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1 — Result brief

结论标签：`CURRENT_REPLAY_FIXTURE_QUALIFIED` / `QUICK_PROMISING`。

## 改变、保持与目的

- 改变：只新增一个 ideal current source RP，将 P0 完整 `I(LIN|XBQ)` 原样 replay 到 QB IN。
- 保持：QB topology、Lin/L0/L1/L2、BJs/BJL1/BJL2、RJ1/RJ2/RB、IBIAS=35 µA、R_LOAD=10 Ω、JJ model、solver、步长和 stop time。
- 目的：判断 current-only replay 是否足以复现 P0 的输入、PRE 与内部轨迹；I0 仅作为既有 reference gap。

## 关键观察

- 输入 fidelity：P0 `I(LIN|XBQ)` → RP `I(I_REPLAY)` 为 `PASS`，exact grid=True，max error=0 µA，RMS=0 µA。
- W2 PRE：PASS；五个 current 和三个 W2-median-centered phase 均按预注册阈值检查。
- W3/W4 closure：共 14 个非退化 Cx，最大 Cx=1.7781171e-07。
- RP BJL2 strict local：`SUBTHRESHOLD`，P0 为 `SUBTHRESHOLD`。
- KCL：PASS（共享 `scripts/bvmtools/kcl.py`，tolerance=0.001 µA）。

## 这意味着什么

- 当前单点、当前模型和冻结窗口下，结果属于 `QUICK_PROMISING` 所对应的 exploratory evidence。
- 任何 `C_x` 都只是 trajectory closure；strict BJL2 也只是同一 JJ 的 phase/area compatibility。

## 不能证明什么

- 不能把 phase turns 当成 SFQ count，不能证明 downstream/JTL delivery、source-impedance mechanism、硬件行为或 Formal BVM→QB Gate。
- 不能外推到其他 READ 宽度、负载、偏置、Ic、时间步长或拓扑。

## 后续可选项（本次不执行，最多三项）

1. 在用户重新授权后，选择一个固定的 receiver-side follow-up 做独立验证。
2. 在用户重新授权后，针对当前 fixture 设计最小的 source/load sensitivity 对照。
3. 暂停实验，先由用户审阅 raw、closure 表和 strict local 证据。

最终工作流状态：`AWAITING_USER_REVIEW` / `STOP`。
