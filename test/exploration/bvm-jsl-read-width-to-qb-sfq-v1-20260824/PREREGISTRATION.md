# BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1

## 实验模式与边界

这是一个 `Exploration` / `exploratory` 任务。注册 parent HEAD 为
`955a99e9c70489f6e67ee31c7e9a21de7f4e22ff`；工作树中已有、与本实验无关的
用户修改为 `circuits/t1/t1_cell.cir`，本实验不读取其修改内容，也不修改 T1。

冻结：

- `circuits/bvm/bvm_cell.cir` 及其 JM1/JM2、JS1/JS2、S-Loop、R-Loop 参数；
- canonical BVM 的 WL/BL 初始化、READ amplitude、rise/fall、初始条件与
  `R_LD=12 Ω` external load（Phase A）；
- 12×`jjmit AREA=3.2` 的 external-series JSL load（Phase B）；
- frozen scaled QB：BJs/BJL1/BJL2 AREA `.50/.36/.54`，
  `IBIAS=35 µA`，`Lin/L0/L1/L2=.80/1.323/3.91/3.91 pH`，
  `RJ1/RJ2=33/22 Ω`，`RB=6 Ω`，`R_LOAD=10 Ω`（Phase C）；
- 不接 standard JTL、T1，不调整 QB 参数，不修改 canonical BVM。

既有 9 ps baseline 不重跑：

- Phase A 的 canonical `R_LD=12 Ω` 9 ps 使用 accepted
  `test/exploration/bvm-internal-readout-20260819` raw；
- Phase B 的 12-JSL external-load 9 ps 使用 accepted
  `test/exploration/paper-sl-l0-20260824` raw；
- READ=0 controls 在相同 topology、相同 initialization、相同 timestep/stop
  下可直接复用对应 accepted raw，并在 manifest 中保留 provenance。

## Scientific question

在 BVM core、READ amplitude/onset/rise/fall、initialization 和 external load
保持不变时，延长 canonical READ plateau 是否增加 useful read1 output
duration/area，并把已知的 paper-JSL logical1 replay 的 BJL2
`~0.893 turn` 推向 frozen scaled QB 的 exactly-one window，同时保持
logical0 与 READ=0 control 为零事件？

## Hypothesis and alternatives

主假说 H1：canonical READ 的约 9 ps plateau 限制了 BVM→JSL source waveform
的有用持续时间/面积；延长 plateau 可能增加后续 QB 的有效 drive。

替代解释：

1. `EDGE_DOMINATED`：width 只平移 falling edge，leading transient 和有用
   area 基本不增加；
2. `DEGRADING_OR_NONSELECTIVE`：read0/control、storage guard 或 post ringing
   随 width 变坏；
3. READ width 增加能改善 BVM/JSL source，但 frozen QB 的 dynamic window
   仍不匹配。

## Registered widths and cases

Phase A 只测试 `9/12/15/20 ps`。9 ps 复用 accepted raw；12/15/20 ps
只新运行：

1. logical1 + canonical READ；
2. logical0 + canonical READ；
3. READ=0 control（logical1 与 logical0 的 accepted controls 作为 matched
   zero-input reference）。

所有 READ 保持 `+100 µA`、rise `1 ps`、fall `1 ps`、onset `96 ps`；对每个
   width 只平移 falling edge：

| plateau | high interval | falling interval |
|---:|---|---|
| 9 ps | 96–105 ps | 105–106 ps |
| 12 ps | 96–108 ps | 108–109 ps |
| 15 ps | 96–111 ps | 111–112 ps |
| 20 ps | 96–116 ps | 116–117 ps |

`.tran=0.0125 ps`，stop `170 ps`。Phase A 不做 timestep sweep。

## Phase A measurements

每个 case 的 read activity 使用预注册 `[94,130) ps`，pre 使用 `[80,90) ps`，
post 使用 `[140,170) ps`；width-specific leading/plateau/falling 子窗分别由
上表定义。直接记录：

- `I(L_SL|XBVM1)`、`I(L_PSL|XBVM1)`；
- `V(SL1)`、`V(N6|XBVM1)`；
- `P/V(B_JM1|XBVM1)`、`P/V(B_JM2|XBVM1)`、
  `P/V(B_JS1|XBVM1)`、`P/V(B_JS2|XBVM1)`；
- current positive/negative/signed area（以 pre median 去基线，单位
  `µA·ps`），peak、diagnostic duration、leading/plateau/falling contribution；
- storage pre/post median 与 post p2p；post ringing。

原始 `P(...)` 保留 rad；相对变化只在声明窗口后以 `ΔP/(2π)` 报告 turns。
Phase A 不以 phase range、`I>Ic` 或 voltage peak 宣称 SFQ event。

## W* selection rule (registered before results)

W* 仅用于 Phase B/C 的下一阶段选择，不是结论。必须同时满足：

1. BVM source/storage guard 没有不可接受的恶化；
2. read0 与 READ=0 activity 保持低且有选择性；
3. read1 useful output area 或 duration 相对 9 ps 有明确改善；
4. 改善不能只来自单一异常 peak；
5. 多个 width 满足时选择最短 width。

若没有 width 明确优于 9 ps，记录 `NO_USEFUL_WIDTH_GAIN` 并停止，不定义 W*。

## Phase B gate

只有 Phase A 得到 W* 才运行。冻结 9 ps accepted comparator，新增：

- canonical BVM + `R_LD=12 Ω` + W*（复用 Phase A raw）；
- canonical BVM + external `B_LD1...B_LD12 AREA=3.2` JSL + W*。

后者须保持 canonical BVM 内部 `L_PSL/R_SL/L_SL` 不变。检查 12 个 JSL
non-switching、read1/read0 separation、SL/N6、storage guard 与 post ringing。

Phase-B bounded source-stage classification used in the final report is
`PAPER_JSL_WSTAR_SOURCE_VALID` when the W*=12 source remains state-selective,
all 12 JSLs remain non-switching/bounded, and the source/storage guards remain
acceptable. This label is deliberately not a QB or downstream SFQ verdict.

若 Phase A 判为 `EDGE_DOMINATED` 或 `DEGRADING_OR_NONSELECTIVE`，不强行进入
Phase B。

## Phase C gate

只有 `12-JSL + W*` 未明显破坏 source/selectivity 时，才将其真实
`I(B_LD1)(t)` 原样作为 ideal current replay 输入 frozen scaled QB。禁止
amplitude scaling、rectify、hold、smooth、resample 或重定时。至少运行
logical1/read、logical0/read、READ=0 control，并与 accepted
12-JSL + 9 ps PAPER-SL-Q1 直接比较 BJs/BJL1/BJL2。

Phase C 的 local event 仍必须满足同一 BJL2、同一 continuous monotonic
segment、`|ΔP|/(2π)≥1`、同段直接电压面积一致、exactly-one、post bounded。
这最多是 ideal replay compatibility，不是 physical BVM→JSL→QB closure。

## Stop rules

- 不修改 canonical BVM、QB、JTL、T1；
- 不追加 READ width、amplitude、timestep 或 QB parameter sweep；
- 不把 READ width 的单调性自动推广到其它 load/topology；
- Phase A 无 useful gain 时停止；
- controls/read0 非选择性、storage/source guard 明显恶化、solver/artifact 无效
  时停止相应 gate；
- Phase C 若得到 `EXACTLY_ONE`，仍停止，不自动执行 physical cascade、JTL 或 T1。

## Expected classifications

Phase A：`DURATION_SUPPORTED` / `EDGE_DOMINATED` /
`DEGRADING_OR_NONSELECTIVE` / `NO_USEFUL_WIDTH_GAIN` / `INCONCLUSIVE`。

Phase C：`IDEAL_REPLAY_SELECTIVE_ONE_SFQ` /
`WIDTH_IMPROVES_QB_MARGIN_BUT_SUBTHRESHOLD` /
`READ_WIDTH_NOT_LIMITING_QB_CLOSURE` /
`OVERDRIVEN_OR_MULTI_EVENT` / `NONSELECTIVE` / `INCONCLUSIVE`。
