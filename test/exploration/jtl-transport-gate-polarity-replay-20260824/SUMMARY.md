# Checkpoint summary

## Verdict

`TRANSPORT_RECONCILIATION_FIRST_STAGE_ONLY`

`POLARITY_ASYMMETRY_CONFIRMED_WITHOUT_FULL_CHAIN`

这不是 `DIRECT_JTL_SELECTIVE_PASS`，也不是物理 Q0→JTL 接口通过。新 replay
是 accepted Q0 pulse 5 的理想 `V(OUT,t)` counterfactual，只有标准 JTL 的
transport/polarity 诊断意义。

## 关键结果

- R11 standard positive control：full-window 四颗 JJ 都有约一圈的 phase/area
  净变化，但 strict monotonic vector 为 `[1,0,0,0]`。这两类证据必须分开
  解释；full-window calibration 不等于四颗 JJ 均有严格完整单调事件。
- M1 ideal replay：strict vector `[1,0,0,0]`，full-window vector 全为真，故
  保持 `FIRST_STAGE_ONLY` 边界。
- M5-PC scaled-JTL control：strict vector `[1,1,0,0]`；它是独立的
  scaled-JTL positive-control topology，不能与 standard JTL 数值混称。
- Q0 pulse-5 原极性 replay：
  - `B1|XJTL1` 最大连续单调段 `1.07619 turn`，同段面积 `1.07626 Φ0`；
  - `B2|XJTL1/B1|XJTL2/B2|XJTL2` 分别约 `0.92747/0.92181/0.85943 turn`，
    均未达到严格完整事件；
  - full-window 净相位约 `0.99294/1.01275/0.98574/0.98307 turn`，但不升级
    为完整四级 transport；
  - post phase p2p 最大约 `0.02375 turn`，未见第二个完整段。
- 同一 pulse 反极性 replay：严格 vector `[0,0,0,0]`；第一颗最大反向段约
  `−0.87668 turn`，之后逐级衰减到 `−0.01123 turn`；没有完整严格事件，
  post bounded。

## Observed / Derived / Inference / Unknown

### Observed

上述 phase、同一 JJ 同一 monotonic segment 的直接 voltage area、onset、pre/post
well 和 raw/log provenance 均来自 `analysis/REPORT.md` 与 `results.json`。

### Derived

严格事件计数使用连续单调段、相位/面积同段一致和至少一圈条件；full-window
endpoint/area、pre/post well 只作为独立的 settled-state evidence。

### Inference

在当前冻结 standard-JTL fixture 下，Q0 pulse-5 原极性足以使第一颗 JTL JJ
进入严格完整段，但现有波形没有把该事件以严格完整段传到第二颗 cell。反极性
显示明显方向性，但不能替代 logical0/control。

### Unknown

未进行新的 timestep convergence、未连接 T1、未运行 read0/BVM matched case，
也未测试任何其他负载/参数。因此不能从本 checkpoint 推出普遍的 JTL 物理
不可能性。

## Stop

本批已停止。不做 M1–M5 参数延伸、R/L/Ic/bias sweep、波形整形、QB/JTL 调参
或 T1 连接。
