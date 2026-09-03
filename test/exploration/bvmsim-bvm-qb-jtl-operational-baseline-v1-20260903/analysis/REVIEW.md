# Baseline review notes

## Independent review disposition

Sol XHigh reviewer：`REWORK_REQUIRED`。本文件记录的是审阅意见的落地版本，
不是 Formal acceptance，也不授权下一项实验。

## Evidence status

- 4-BVM historical raw：`VALID` 作为 historical exploratory raw；不封装成
  canonical 或 convergence authority。
- 16-state operational mapping：`FUNCTIONAL_FAIL`，范围限定为 historical
  BVMSim、original QB、nominal `0.1 ps` stored profile。
- single-BVM 2×2：`ARTIFACT_INVALID` for intended-model comparison，因为
  original `BVMSim/BQ.cir` 在 single deck 中触发 `Missing model: JJMIT`/
  `Using default model`；不把其结果当物理 PASS/FAIL。
- `1111` QB local event structure：`INCONCLUSIVE` for four independent QB SFQ;
  只能确认一个约 4-turn continuous segment。
- `1111` JTL6 output-side structure：有限的 local-transition / loaded-forward-
  burst evidence；不升级为四个 QB SFQ 或逐事件 identity transport。
- canonical BVM、timestep convergence、RJ1/bias/input margin、T1：`UNKNOWN /
  NOT_RUN`。

## Observed

1. Historical 与 canonical 区分正确：四 BVM deck 使用
   `BVMSim/bvm_cell.cir`、`BVMSim/BQ.cir` 和 historical `jtl2.cir`；historical
   `R_JM1=8 Ω`，canonical 为 `6 Ω`。与 `BVMSim/data_tran.csv` 的 anchor 在共同
   grid 上逐点相同或仅约 `1e-13` 数值差，支持 historical fixture replay，不支持
   canonical compatibility。

2. single 与 four-BVM 的 model-resolution context 不同：four-BVM fixture 有
   visible top-level `jjmit` model；single original-BQ deck 没有得到同一 closure。
   因此 single raw 的 0/1 结果应保留为观察，不应产生 intended-model physical
   verdict，也不应和 four-BVM 作 like-for-like material-model comparison。

3. 16-state 中只有 `0000`、`0100`、`1111` 的 burst-total 与 commanded
   `popcount` 相符；其余 13 个状态明显偏高。例如 `0001: 1→3`、`0010: 1→2`、
   `0011: 2→4`。同一 JJ 的 phase 与 voltage-area 数值一致到约 `1e-5 turns`
   量级，因此 mismatch 不是单看 phase 或旧 `fast_events` 的结果。

4. `1111` 的 QB `BJ2` READ1 全窗约 `3.9995 turns`，最大连续 monotonic
   segment 约 `3.9854 turns`，strict complete segment=1、clean separated=0。
   它不是四个 QB clean SFQ。JTL6 `B02` 的输出侧可分辨四个 local transitions；
   这只说明上游 burst 在 loaded JTL 中出现了更清楚的后段结构。

5. 逐级 first upward integer phase-crossing marker 呈前向顺序：`QB BJ2` 约
   `118.31/121.68/125.48/133.73 ps`，JTL6 约 `134.54/139.23/143.53/148.62 ps`。
   这些是时序 marker，不是 SFQ count；旧 strict `clean onset` 不能直接当作
   因果 latency。

6. 已保存的四 BVM raw 在五个非 READ1 窗口 `PRE/WRITE0/READ0/WRITE1/TAIL`
   中，QB BJ2/JTL6 没有 complete segment；但 4-BVM raw 从 `45 ps` 开始，不能
   覆盖 `0–45 ps` 初始化。所有 raw requested `0.1 ps`，但每个 selected raw
   都有一次 `62.8→63.0 ps` 的 `0.2 ps` stored-grid gap，因此不是严格 uniform。

## Derived

- 可成立：`HISTORICAL_BVMSIM + original QB + six-stage JTL + nominal 0.1 ps`
  的 commanded-state mapping 失败，证据描述为 `HISTORICAL_FIXTURE_COUNT_MISMATCH`。
- 可成立：stop rule 被触发，margin sweep 保持 `NOT_RUN`；`RJ1=12 Ω` 保持 nominal。
- `SELECTIVITY_OR_OVERDRIVE_FAILURE` / `QUICK_OPPOSITE` 仅作为允许的探索性分类；
  不能把 “overdrive” 当作已证实的内部器件机理。
- strict threshold 与 `0.25-turn` burst display tolerance 是运行后诊断参数，
  见 `POST_HOC_DIAGNOSTIC.md`，不是预注册 acceptance threshold。

## Inference

- JTL 后段可能把上游连续 burst dynamics 重塑成更清楚的 local transitions。
- state/position 依赖可能来自 sensing-line loading、BVM 状态实现、QB 输入条件
  或其组合。
- `1111` 的四个 JTL6 transitions 与同一 READ-associated burst 的 forward
  propagation 相容，但尚不能建立逐个事件 identity。

## Unknown

- BVM2–BVM4 是否分别实现并保持 commanded state；当前 probes 未完整闭合其
  内部 JJ state，因此不能唯一归因于 QB。
- 每个 output transition 是否对应一个 BVM contribution；
- JTL6 transitions 是否可被下一级 receiver/T1 正确消费；
- canonical BVM compatibility、timestep convergence、RJ1/bias/input margin、
  closed-loop fluxoid consistency、硬件行为和论文机制身份。

## Review decision

`REWORK_REQUIRED` 已通过补充模型闭包、post-hoc 阈值、stored-grid、state-closure
和 crossing-latency 说明落地。当前不授权 margin、canonical migration、T1 或
设计替换；保持 `analysis/human-gate.yaml` 的 `AWAITING_USER_REVIEW`。
