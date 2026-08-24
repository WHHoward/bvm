# BVM→QB/JTL receiver Exploration 流程总索引
更新时间：2026-08-24；本页与 HTML 版共同服务于按流程阅读。
本索引覆盖 `test/exploration/` 下 57 个目录和 `receiver-architecture-comparison.md`；不重新判定 scientific verdict。
HTML 版：[EXPLORATION_FLOW_INDEX.html](EXPLORATION_FLOW_INDEX.html)；图形总索引：[VISUALIZATION_INDEX.html](VISUALIZATION_INDEX.html)。

## 总体结论

### Observed

- canonical BVM 的 +READ logical1/logical0 分离已稳定；read1 是强 multi-turn source，read0 主要是 edge response，READ=0 安静。
- R0b 建立 local B_TRIG discrimination；R1a 建立 isolated passive secondary transfer。
- R2-F/R2-G 只在受控持续 direct drive 下证明 local JJ complete slip、retrap 和 rearm。
- native QB、DCSFQ、paper-JSL replay 与 JTL/load matrix 都说明 activity、source preservation、local event、JTL propagation 是不同 Gate。

### Derived

- 真正缺口不是 state-dependent signal 是否存在，而是能否形成足够持续、隔离并由 bias 供能的 regenerative drive。
- phase range、voltage peak、I>Ic 都不能替代同一 JJ/同一 monotonic segment 的 direct voltage-area。

### Inference

- 当前最稳妥的解释：source/discrimination 已建立；passive routing 可改善但不量化；temporal/active regeneration 和 load boundary 是主要限制。

### Unknown

- 尚未建立 canonical BVM→exactly-one local SFQ→validated standard JTL/T1 的完整 physical chain。
- 各失败结论限定于对应 fixture、参数、输入、窗口和 model，不自动外推为整个 architecture family。

> local phase turn 不自动等于 SFQ delivery；complete event 必须回到对应报告核对 phase/area/retrap。

## 0. 源行为与语义锚点

先固定 source、storage 和 logical read 语义。
### Canonical BVM internal readout `源锚点`
- 做了什么： 固定 logical 1/0、+READ、READ=0、SL/N6 和 storage guard。
- 结果： logical1 是强 multi-turn read1 source；logical0 主要是 READ-edge response；READ=0 inactive；rewrite/read 语义保持。
- 结论边界： phase turns 不是 SFQ count；这里只是 source/state anchor。
- 可视化阅读： 看 SL/N6、JS1/JS2 与 JM1/JM2/JS guards；先比较 logical1/logical0，再看 rewrite 图中的重复性。
- 入口：[报告 / 源文档](../test/exploration/bvm-internal-readout-20260819/summary-v3.md)；[主图](../test/exploration/bvm-internal-readout-20260819/plots/logical0-canonical-read.html)；[补充图1](../test/exploration/bvm-internal-readout-20260819/plots/logical1-canonical-read.html)；[补充图2](../test/exploration/bvm-internal-readout-20260819/plots/rewrite-read-0101.html)；[补充图3](../test/exploration/bvm-internal-readout-20260819/plots/rewrite-read-1010.html)

## 1. R0–R1：前端判别与被动提取

先确认 read1/read0 可分，再确认状态能否安全带出 BVM。
### R0：原始 trigger 判别 `partial / near-threshold`
- 做了什么： 从 SL 接入最小 receiver，测试 read1/read0 threshold separation。
- 结果： 原始 read1 B_TRIG 只有约 .5845 turn；支持 R0-A discrimination，不支持完整 transition。
- 结论边界： 原 R0 PASS 已降级为 R0-A PASS / R0-B NOT YET。
- 可视化阅读： 看 B_TRIG 的 continuous phase/voltage 与 SL/N6 的 read1/read0 分离；不要把 sub-turn 视觉峰值当 event。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r0-20260819/analysis/R0_REPORT.md)
### R0b：完整 trigger closure `bounded positive`
- 做了什么： 固定 SL route、R_IN=12Ω、AREA=.50、bias=15µA，测试完整 trigger。
- 结果： read1 B_TRIG≈4.997 turns，read0≈.185 turn；controls 无完整 transition，source/storage guard 保持。
- 结论边界： multi-turn local trigger baseline；不是 exactly-one SFQ/JTL delivery。
- 可视化阅读： 看 B_TRIG 的 continuous phase/voltage 与 SL/N6 的 read1/read0 分离；不要把 sub-turn 视觉峰值当 event。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r0b-20260819/analysis/R0B_REPORT.md)；[主图](../test/exploration/bvm-sfq-receiver-r0b-20260819/plots/comparison.html)；[补充图1](../test/exploration/bvm-sfq-receiver-r0b-20260819/plots/logical0-read0-control.html)；[补充图2](../test/exploration/bvm-sfq-receiver-r0b-20260819/plots/logical1-read0-control.html)；[补充图3](../test/exploration/bvm-sfq-receiver-r0b-20260819/plots/read0.html)
### R1：parallel feedback one-shot `bounded failure / no event`
- 做了什么： 用并联 LQ–RQ branch 尝试把 trigger 变成 output event。
- 结果： 强 feedback 先压制 B_TRIG，弱 feedback 又 transfer 不足，output JJ 无合格 event。
- 结论边界： 只否定当前 parallel topology，不否定整个 one-shot family。
- 可视化阅读： 看 feedback branch current 与 B_TRIG phase 的反向关系：loading 越强，source 越被压制。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/analysis/R1_REPORT.md)
### R1a：series pickup passive extraction `bounded positive`
- 做了什么： 用 SL→RIN→LTX→BTRIG 与 LTX–LSEC mutual 提取 secondary。
- 结果： read1 BTRIG≈3.944 turns，read0≈.185；secondary read1≈66.8µV/5.56µA，ratio≈4.87。
- 结论边界： 建立 passive state-dependent transfer；没有 active gain，不是 downstream SFQ。
- 可视化阅读： 看 B_TRIG、L_TX/L_SEC、N_SEC 及 secondary V/I 的同一时间轴；这是 passive transfer 图。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/analysis/R1A_REPORT.md)；[主图](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/plots/comparison.html)；[补充图1](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/plots/logical0-read0-control.html)；[补充图2](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/plots/logical1-read0-control.html)；[补充图3](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/plots/read0.html)
### R1b：common-mode output-JJ activation `bounded failure / no event`
- 做了什么： 让 passive secondary 驱动最小 B_OUT JJ。
- 结果： V(B_OUT) 近 numerical zero，两个 node 同步移动；没有 differential activation。
- 结论边界： 否定 common-mode interface，不是继续扫 Ic/bias 可修复。
- 可视化阅读： 看 N_OUT/N_SEC common-mode 与 B_OUT differential V/P；重点是 signal 是否出现在 JJ 两端。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/analysis/R1B_REPORT.md)
### R1b：differential secondary B_OUT `bounded failure / no event`
- 做了什么： 修正 secondary return，使 transient 出现在 B_OUT 两端。
- 结果： read1 有 voltage/current response，但 phase≈.022 turn，无 complete event。
- 结论边界： signal existence 已成立，activation margin 未成立。
- 可视化阅读： 看 N_OUT/N_SEC common-mode 与 B_OUT differential V/P；重点是 signal 是否出现在 JJ 两端。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/analysis/R1B_DIFF_REPORT.md)
### R1b：AREA=.08 activation test `bounded failure / no event`
- 做了什么： 只将 B_OUT AREA=.10→.08。
- 结果： read1≈.020 turn、read0≈.005 turn；无 complete event；AREA 同时改 Ic/C/RN/R0。
- 结论边界： 简单 Ic reduction 不是主解。
- 可视化阅读： 看 N_OUT/N_SEC common-mode 与 B_OUT differential V/P；重点是 signal 是否出现在 JJ 两端。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/analysis/R1B_AREA008_REPORT.md)
### R1c：B_OUT bias margin `bounded failure / no event`
- 做了什么： 固定 AREA/拓扑/damping，只测 6–10µA bias。
- 结果： read1 约 .02 turn、read0 约 .005 turn，无 bias window。
- 结论边界： bias operating point 不是主要限制。
- 可视化阅读： 看 N_OUT/N_SEC common-mode 与 B_OUT differential V/P；重点是 signal 是否出现在 JJ 两端。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/analysis/R1C_BIAS_REPORT.md)

## 2. R2：输出 JJ 局部物理要求

用受控 direct drive 校准 amplitude、dwell、retrap/rearm。
### R2-A：coupling strength `bounded failure / no event`
- 做了什么： 只改变 K，测试 coupling 是否足以激活 B_OUT。
- 结果： K=.60–.95 下 read1 .0166→.0261 turn；read0 分离保留，无 complete event。
- 结论边界： 否定当前 bare secondary→B_OUT instance，不外推 entire direct family。
- 可视化阅读： 看 K 改变时 secondary/B_OUT 的 read1-read0 phase、current 和 area；所有曲线仍是 bounded sub-turn。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/analysis/R2A_COUPLING_REPORT.md)；[主图](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k080-representative/comparison.html); [all-K matrix](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k-matrix-comparison.html)；[补充图1](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k080-representative/logical0-read0-control.html)；[补充图2](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k080-representative/logical1-read0-control.html)；[补充图3](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k080-representative/read0.html)
### R2-B：secondary damping `analysis / method`
- 做了什么： 只改变 output damping/load，判断 damping 是否主瓶颈。
- 结果： damping 变化只带来小幅 sub-turn gain，secondary branch 吸收/分流仍明显。
- 结论边界： damping 不是当前最有证据的主限制。
- 可视化阅读： 看 damping branch current、B_OUT phase 和 source branch；判断 drive 是被阻尼还是被节点分流。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/analysis/R2B_DAMPING_REPORT.md)
### R2-C：direct-drive amplitude transfer `bounded failure / no event`
- 做了什么： 用受控 direct-drive 幅度点估计有效电流传递。
- 结果： fast triangle 是 bounded linear/subthreshold；只有部分输入扰动到达 B_OUT。
- 结论边界： 峰值超过 Ic 不能代替 event evidence；需同时看 duration。
- 可视化阅读： 看 direct input current 到 B_OUT current 的比例以及 phase creep；不要只看 I peak。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/analysis/R2C_DIRECTDRIVE_REPORT.md)
### R2-D：fixed-amplitude duration `bounded failure / no event`
- 做了什么： 固定 amplitude，只改变 pulse duration。
- 结果： 短 pulse transfer-limited，长 pulse balance-limited；duration alone 未闭合。
- 结论边界： activation boundary 是 amplitude×duration 二维问题。
- 可视化阅读： 看 pulse width 与 B_OUT phase evolution 的关系，分辨短时 transfer ceiling 和长时 balance ceiling。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/analysis/R2D_DURATION_REPORT.md)
### R2-E：quasi-static amplitude threshold `bounded failure / no event`
- 做了什么： 在较长 window 测 4.0/4.5/5.0µA drive。
- 结果： bounded matrix 无 complete event；drive decay 与 phase creep 竞争被量化。
- 结论边界： 真实 transformer chain 的约 1.46µA spike 更远；阈值不是 universal。
- 可视化阅读： 看 amplitude matrix 的 B_OUT phase/area 与 drive decay；“接近阈值”仍需同段证据。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/analysis/R2E_AMPTHRESHOLD_REPORT.md)
### R2-F：near-critical dwell threshold `bounded positive`
- 做了什么： 固定约 4.5µA，比较 hold 0/5/10/20ps。
- 结果： 20ps 首次得到约 1.004-turn local B_OUT event，同段 area 一致，retrap，controls 不触发。
- 结论边界： direct-drive local one-shot；不是 transformer/JTL evidence；20ps 是诊断先验。
- 可视化阅读： 把 h00/h05/h10/h20 的 B_OUT continuous phase 与 same-segment area 对齐；h20 才是 bounded local event。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/analysis/R2F_DWELL_REPORT.md)
### R2-G：two-pulse retrigger `bounded positive`
- 做了什么： 两个 4.5µA/20ps-hold pulse 检查 rearm。
- 结果： 两个 pulse 各有一次约 1.033-turn local slip，clean retrap/rearm，无 multifire。
- 结论边界： 只建立受控 drive 下的 local primitive，未解决真实 chain drive。
- 可视化阅读： 按两个 pulse 分窗看 phase/area、post well 和 quiet gap，确认 retrap/rearm 而不是一次长 excursion。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/analysis/R2G_TWOPULSE_REPORT.md)

## 3. R3–R5：capture / quantizer 机制检验

分开 fast onset、弱互感 capture 和 reduced quantizer 的失败原因。
### R3-A：capacitive onset extraction `bounded failure / no event`
- 做了什么： 用 1fF C_ON 从 B_TRIG onset 提取 fast spike。
- 结果： C_ON transduction 可见，read1 |I|≈2.24µA；B_OUT causal drive约8.06µA，无 complete event。
- 结论边界： 否定该 fast-differentiated instance，不否定所有 B_TRIG extraction。
- 可视化阅读： 把 I(C_ON)、B_OUT current/voltage 与 phase 对齐；可见 onset transduction 不等于 sustained drive。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/analysis/R3A_ONSET_REPORT.md)
### R4-A：weak-mutual passive capture `bounded failure / no event`
- 做了什么： 把 B_TRIG transient 捕获进 L_H=100pH loop。
- 结果： read1/read0 transient 有分离，但 flux/current 不足跨 capture boundary，state 回到 n=0。
- 结论边界： 只降级 single point，不外推整个 mutual family。
- 可视化阅读： 看 loop circulating current、external flux 和 fluxoid-state trajectory；read1 transient 是否持久是核心。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/analysis/R4A_AMENDED_REPORT.md)
### R5-A：reduced biased quantizer `bounded failure / no event`
- 做了什么： 测试 read1 是否越过 static saddle 并逃逸。
- 结果： read1 有 large bounded oscillation，跨 saddle 但无不可逆 complete slip；read0/control 安静。
- 结论边界： “缺少不可逆性/不对称”是 inference，不是单独 topology fact。
- 可视化阅读： 看 SET phase、loop current 与 saddle/lobe 的时间关系，再对照 BVM source guard；越 saddle 不等于逃逸。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/analysis/R5A_REPORT.md)
### R5-B：load-line correction `bounded failure / no event`
- 做了什么： 修正 minimal shunt/load-line wiring。
- 结果： branch 主要增加 damping/current diversion，仍是 bounded oscillation。
- 结论边界： 否定该 shunt hypothesis，不推出完整 paper QB 必然正确。
- 可视化阅读： 看 SET phase、loop current 与 saddle/lobe 的时间关系，再对照 BVM source guard；越 saddle 不等于逃逸。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/analysis/R5B_REPORT.md)
### R5-C：correct saddle selectivity `bounded failure / no event`
- 做了什么： 用真实 nonlinear loop equation 检验 saddle crossing 与 event 是否等价。
- 结果： read1 跨真实 saddle但仍 multi-lobe/no event；JS1/JS2 post-state 约 −4 turns。
- 结论边界： 停止 reduced-quantizer tuning；static saddle crossing 不是 event criterion。
- 可视化阅读： 看 SET phase、loop current 与 saddle/lobe 的时间关系，再对照 BVM source guard；越 saddle 不等于逃逸。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/analysis/R5C_REPORT.md)

## 4. Native QB 与隔离/路由

检验 native QB 的 source boundary、transfer 和 internal routing。
### Native paper-QB：direct SL mapping `bounded failure / no event`
- 做了什么： 将 canonical SL galvanic 接入 native paper-QB。
- 结果： read1 BJs/BJL1/BJL2 activity 明显强于 read0，但 JS1/JS2约−3 turns drift，source guard fail；BJL2 无 event。
- 结论边界： 主 verdict BACK_ACTION_FAILURE，次级 STATE_SELECTIVE_QB_ACTIVITY。
- 可视化阅读： 看 BJs/BJL1/BJL2 activity 与 SL/N6、JS1/JS2 post-window；同时读 activity separation 和 back-action。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-native-qb-20260822/analysis/NATIVE_QB_REPORT.md)
### R6-A：weak inductive isolation `bounded positive`
- 做了什么： SL-derived primary→weak mutual→native QB。
- 结果： source isolation 保持，read1/read0 QB activity 分离约3.6–3.8×；BJL2≈.001585 turn。
- 结论边界： isolation positive，不等于 quantization。
- 可视化阅读： 看 secondary/Lin/loop current 的 read1 gain，并相对 canonical baseline 看额外 source disturbance。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/analysis/R6A_REPORT.md)
### R6-B：winding-ratio transfer gain `bounded positive`
- 做了什么： 降低 secondary impedance，测 drive gain 与 reflected load。
- 结果： secondary/early QB gain；BJL2≈.001588 turn几乎不变，source guard保持。
- 结论边界： gain 到 front stage，未打开 output quantization。
- 可视化阅读： 看 secondary/Lin/loop current 的 read1 gain，并相对 canonical baseline 看额外 source disturbance。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/analysis/R6B_REPORT.md)
### R7-A：L1 proximal routing `bounded positive`
- 做了什么： L1 3.91→2.50pH，观察 front→loop routing。
- 结果： G_L2/G_BJL2 约增26%；BJL2最大segment≈.001886 turn，BJL2 DC current反而下降。
- 结论边界： 是 routing knob，不是把 DC bias 推近 Ic。
- 可视化阅读： 看 control-subtracted G_L2/G_BJL2、BJL1 redistribution 和 settled currents；routing gain 不等于 DC bias gain。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/analysis/R7A_REPORT.md)
### R8：BJL2 AREA=.70 `bounded failure / no event`
- 做了什么： 只改变 BJL2 output AREA，测 threshold-like gain。
- 结果： phase activity 变大但仍 10^-3 turn 量级，read0 co-amplify，无 nonlinear jump。
- 结论边界： AREA 同时改 Ic/C/RN/R0；停止 AREA sweep。
- 可视化阅读： 把 read1/read0 BJL2 phase、current excursion 和 AREA-scaled model side effects 放在一起看；没有 threshold-like jump。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/analysis/R8_REPORT.md)
### R9-A：L2 downstream routing `bounded positive`
- 做了什么： L2 3.91→2.50pH，观察 node3→BJL2 routing。
- 结果： G_L2/G_BJL2 约增35–37%；read0 co-amplify；BJL2≈.00226 turn。
- 结论边界： bounded routing gain；结束 passive L1/L2 tuning。
- 可视化阅读： 看 node3→L2→BJL2 的 control-subtracted RMS 以及 read0 co-amplification；这是 passive routing 结论。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/analysis/R9A_REPORT.md)
### R10-A：local BJL2 bias feed `bounded failure / no event`
- 做了什么： 在 node4 加 local bias，试图打开 BJL2 nonlinear regime。
- 结果： 约214µA feed 令 read1/read0/control 都 multi-turn running，source disturbance 很大。
- 结论边界： BACK_ACTION_OR_NONSELECTIVE_FAILURE；停止 local-bias sweep。
- 可视化阅读： 看 local bias current、BJL2 phase 和四-case post-running；read0/control 同样 running 是 nonselective evidence。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/analysis/R10A_REPORT.md)
### Ox Alpha：receiver architecture comparison `analysis / method`
- 做了什么： 只读比较 DIRECT、lightweight adapter、paper-style QB。
- 结果： 原 comparison 推荐 lightweight adapter；Sol/Luna 后续审查收缩到 B_TRIG extraction 与 active/regenerative requirements。
- 结论边界： 架构 review 不是实验 verdict，也不因 paper QB 是论文结构就自动正确。
- 可视化阅读： 该文档没有 raw plot；先读 R1/R2 comparison，再沿本页链接回各实验的原始图和报告。
- 入口：[报告 / 源文档](../test/exploration/receiver-architecture-comparison.md)

## 5. 直接 JTL、DCSFQ 与 active interstage

区分标准 JTL 可工作、BVM 能否喂给它、以及 active gain 是否存在。
### R11-A：canonical SL→standard JTL `bounded failure / no event`
- 做了什么： 先过 positive control，再把 canonical SL 直接接 two-cell JTL。
- 结果： standard JTL positive control 有效；BVM read1 第一颗 JTL JJ最大单调excursion约 .151 turn，无第一颗完整event。
- 结论边界： 只否定 direct galvanic BVM→JTL point，不否定 JTL fixture。
- 可视化阅读： 先看 standard-JTL positive control 的四颗 JJ，再看 BVM direct case 的第一颗 JJ；两层不可混合。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/analysis/R11A_REPORT.md)；[主图](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/plots/comparison.html)；[补充图1](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/plots/logical0-read0-control.html)；[补充图2](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/plots/logical1-read0-control.html)；[补充图3](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/plots/positive-control.html)
### R12-A：historical DCSFQ_BVM re-audit `partial / near-threshold`
- 做了什么： 用 0/68.4/300µA controlled input 复核 DCSFQ，再跑 canonical cascade。
- 结果： 300µA controlled input 下 B3≈1.03-turn bounded event；68.4无event；canonical read1 B3≈.0365 turn，JTL不传播。
- 结论边界： DCSFQ mechanism 在强 controlled input 下存在；canonical source scale/temporal drive 不足。
- 可视化阅读： Phase A 看 controlled DCSFQ B3 输入窗口，Phase B 看 canonical cascade；这是 backend ability 与 source compatibility 的对照。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/analysis/R12A_REPORT.md)；[主图](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/plots/phase-a-bump-300u.html)；[补充图1](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/plots/phase-a-bump-68u4.html)；[补充图2](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/plots/phase-a-comparison.html)；[补充图3](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/plots/phase-a-zero.html)
### R13-A：ideal temporal conditioning `bounded failure / no event`
- 做了什么： raw replay 上测试 rectification、20ps hold、两者组合。
- 结果： C1/C2/C3 都只给 sub-turn B3；理想 polarity/dwell 仍不足。
- 结论边界： requirements/counterfactual 结果，不是 physical conditioner；需要 active/regenerative gain。
- 可视化阅读： 在同一时间轴比较 raw replay、C1、C2、C3 的 B3 phase/area；理想变换失败说明还缺 active gain。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/analysis/R13A_REPORT.md)；[主图](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-replay/comparison.html)；[补充图1](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-replay/logical0-read0-control.html)；[补充图2](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-replay/logical1-read0-control.html)；[补充图3](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-replay/read0.html)
### R14-A：active interstage scale precheck `bounded failure / no event`
- 做了什么： 分析 R1a passive secondary 是否足够喂 frozen DCSFQ。
- 结果： secondary≈5.564µA；optimistic estimate≈9.77µA，3ps sanity≈19.1µA；低于 68.4/110.2/300µA references。
- 结论边界： PRECHECK_NO_GO；缺少 detector→regenerator 的 bias-powered active transfer。
- 可视化阅读： 这是 analytic scale table，不是 waveform 图；并列看 R1a、68.4、110.2、300 µA reference 的 input scale。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/analysis/R14A_REPORT.md)
### R15-A：AFQ-3 initial point `bounded failure / no event`
- 做了什么： 尝试 low-Ic detector→active interstage→frozen DCSFQ。
- 结果： shared three-winding matrix invalid，determinant约−.62；未运行物理结果。
- 结论边界： PRECHECK_NO_GO 是 topology validity failure，不是 active physics failure。
- 可视化阅读： 先读 topology/matrix/KCL 与 precheck；没有可把 PRECHECK_NO_GO 当 physical event 图的 raw。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/analysis/R15A_REPORT.md)
### R15-B：split-winding correction `bounded failure / no event`
- 做了什么： 改成 split-winding/two-core mutual topology。
- 结果： B_DET read1≈3.913 turns，但 J_SET/J_Q/J_OUT四cases几乎相同；DCSFQ I(L1)≈.51µA。
- 结论边界： ACTIVE_STAGE_NO_TRIGGER；根因在 detector→J_SET causal input。
- 可视化阅读： 先读 topology/matrix/KCL 与 precheck；没有可把 PRECHECK_NO_GO 当 physical event 图的 raw。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/analysis/R15B_EXECUTION_REPORT.md)；[主图](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/plots/comparison.html)；[补充图1](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/plots/logical0-read.html)；[补充图2](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/plots/logical0-read0-control.html)；[补充图3](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/plots/logical1-read.html)
### R15-C：finite-impedance J_SET causal fixture `partial / near-threshold`
- 做了什么： 撤掉 ideal current clamp，使用 finite-impedance bias + mutual input。
- 结果： I(B_SET) read1 2.097–9.129µA，read0 4.888–6.282µA，controls≈5.6µA；phase≈.22444 turn；KCL residual≈.5pA。
- 结论边界： CAUSAL_NEAR_THRESHOLD；causal modulation成立，complete J_SET event未成立。
- 可视化阅读： 先读 topology/matrix/KCL 与 precheck；没有可把 PRECHECK_NO_GO 当 physical event 图的 raw。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/analysis/R15C_EXECUTION_REPORT.md)
### R15-D：J_Q refractory compressor `bounded failure / no event`
- 做了什么： 在 R15-C 后加入 split node、独立 J_Q bias、RL refractory branch。
- 结果： 上游 causal 保持；J_Q只有 selective sub-turn，无 complete one-shot，也无直接 depletion/recovery evidence。
- 结论边界： JQ_CAUSAL_NEAR_THRESHOLD；保留 checkpoint，不继续 R15-E。
- 可视化阅读： 先读 topology/matrix/KCL 与 precheck；没有可把 PRECHECK_NO_GO 当 physical event 图的 raw。
- 入口：[报告 / 源文档](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/analysis/R15D_EXECUTION_REPORT.md)

## 6. Standalone scaled QB

先确认 ideal input window，再回放 canonical source waveform。
### QB-Q0：standalone scaled QB window `bounded positive`
- 做了什么： 用 ideal input 0/45/68.4/90µA 重审 scaled QB。
- 结果： 0 ZERO_EVENT；45无event；68.4每pulse exactly-one BJL2≈1.096 turn；90≈2.006 turn multi-event。
- 结论边界： 68.4是 ideal standalone reference，不是 canonical threshold/downstream delivery。
- 可视化阅读： 按 input level 和六个 pulse 看 BJs→BJL1→BJL2 phase/area；68.4 的 exactly-one 与 90 的 multi-event 要并排读。
- 入口：[报告 / 源文档](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/analysis/QB_Q0_REPORT.md)；[主图](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/68p4-paper-reference.html)；[补充图1](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/90-paper-reference.html)；[补充图2](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/paper-reference-comparison.html)；[补充图3](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-0uA.html)
### QB-Q1：canonical BVM→scaled QB `bounded failure / no event`
- 做了什么： 不 reshape BVM，直接接冻结 Q0 scaled QB。
- 结果： read1 BJL2≈.098 turn、read0≈.030；read1>read0>>control，但 JS1/JS2约−3 turns drift。
- 结论边界： QB_SOURCE_BACKACTION_FAILURE，并伴随 subthreshold；不能只归因 source weak。
- 可视化阅读： 看 actual QB input 与 BVM SL/N6/JS post drift；activity separation 和 source back-action 必须同时出现。
- 入口：[报告 / 源文档](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/analysis/QB_Q1_REPORT.md)
### QB-Q2A：source-decoupled replay `bounded failure / no event`
- 做了什么： 比较 Q0 positive、Q1 loaded、canonical no-receiver logical1/0 replay。
- 结果： Q0 replay复现one-shot；canonical logical1 BJs/BJL1/BJL2≈1.228/.339/.178 turns，logical0显著更低。
- 结论边界： source isolation alone不足；QB_DYNAMIC_WINDOW_MISMATCH；replay不是 hardware interface evidence。
- 可视化阅读： 看 source-isolated replay 的 BJs→BJL1→BJL2 transfer；canonical read1 很强但仍可能落在 QB dynamic window 外。
- 入口：[报告 / 源文档](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/analysis/QB_Q2A_REPORT.md)
### QB-Q2B：central bias bracket `bounded failure / no event`
- 做了什么： 冻结 canonical replay，只测 30/35/40µA。
- 结果： read1 BJL1约 +.3206、+.3394、−.4146 turn；read0≈.059；无 BJL1/BJL2 event。
- 结论边界： BIAS_BRACKET_NO_BJL1_EVENT；central bias不是 closure。
- 可视化阅读： 看 source-isolated replay 的 BJs→BJL1→BJL2 transfer；canonical read1 很强但仍可能落在 QB dynamic window 外。
- 入口：[报告 / 源文档](../test/exploration/qb-q2b-central-bias-bracketing-20260824/analysis/QB_Q2B_REPORT.md)
### QB-Q2C：uniform junction scaling `bounded failure / no event`
- 做了什么： 统一缩放 AREA 与 IBIAS：s=.85/.70/.55。
- 结果： 三个 scale 都无 selective BJL1/BJL2 event，read0/control zero。
- 结论边界： UNIFORM_SCALE_NO_OUTPUT_EVENT；转向 paper-JSL waveform/internal routing。
- 可视化阅读： 看 source-isolated replay 的 BJs→BJL1→BJL2 transfer；canonical read1 很强但仍可能落在 QB dynamic window 外。
- 入口：[报告 / 源文档](../test/exploration/qb-q2c-uniform-junction-scale-20260824/analysis/QB_Q2C_REPORT.md)

## 7. Paper-SL/JSL 与 QB 内部路由

把论文 12×JSL load 的真实波形带入 QB，再完成 L1/L2 factorial。
### PAPER-SL-L0：12×320µA JSL load `bounded positive`
- 做了什么： 在 SL path 放 exactly 12 个 AREA=3.2 non-switching JJs。
- 结果： 12个 JSL 全部 non-switching；logical1有 state-dependent lobes/ringing，logical0小。
- 结论边界： 限定 external-series-load realization，不是 transparent SL/QB 接入。
- 可视化阅读： 看 12 个 JSL 的 current non-switching、SL-side/far-side current、positive/negative lobes 和 ringing duration。
- 入口：[报告 / 源文档](../test/exploration/paper-sl-l0-20260824/REPORT.md)
### PAPER-SL-Q1：JSL waveform→frozen QB `bounded failure / no event`
- 做了什么： 原样 replay paper-JSL logical1/0/control current 到 scaled QB。
- 结果： read1 BJs≈14.09，BJL1=.829846，BJL2=.892527；read0 BJL2=.00656；无 complete output。
- 结论边界： PAPER-SL_QB_SUBTHRESHOLD；near-threshold，不是 amplitude absent。
- 可视化阅读： 看 paper-JSL logical1 的强 BJs 与 BJL1/BJL2 逐级衰减，并对照 logical0/control 的 separation。
- 入口：[报告 / 源文档](../test/exploration/paper-sl-q1-20260824/analysis/REPORT.md)；[主图](../test/exploration/paper-sl-q1-20260824/plots/paper-sl-l0-classic/logical0-read.html)；[补充图1](../test/exploration/paper-sl-q1-20260824/plots/paper-sl-l0-classic/logical0-read0-control.html)；[补充图2](../test/exploration/paper-sl-q1-20260824/plots/paper-sl-l0-classic/logical1-read.html)；[补充图3](../test/exploration/paper-sl-q1-20260824/plots/paper-sl-l0-classic/logical1-read0-control.html)
### PAPER-SL-Q2：local QB bias closure `bounded failure / no event`
- 做了什么： 冻结 replay，只加 IBIAS=37.5/40µA。
- 结果： 40µA BJL2≈.944323，read0/control zero-event；未闭合 bias-only event。
- 结论边界： BIAS_BRANCH_SUBTHRESHOLD；停止 bias branch，转向 routing。
- 可视化阅读： 看 37.5/40 µA 的 BJL1/BJL2 forward/backward phase 和 area；接近 1 turn 仍不是 event。
- 入口：[报告 / 源文档](../test/exploration/paper-sl-q2-20260824/analysis/REPORT.md)；[主图](../test/exploration/paper-sl-q2-20260824/plots/37p5u/comparison.html)；[补充图1](../test/exploration/paper-sl-q2-20260824/plots/37p5u/paper-j0-logical0-read.html)；[补充图2](../test/exploration/paper-sl-q2-20260824/plots/37p5u/paper-j0-logical0-read0-control.html)；[补充图3](../test/exploration/paper-sl-q2-20260824/plots/37p5u/paper-j1-logical1-read.html)
### PAPER-SL-Q3-PRE：BJs→BJL1 audit `analysis / method`
- 做了什么： 用 Q0/Q1/Q2 raw 审核 BJs→BJL1 transfer、delay 和 KCL。
- 结果： Q0 BJL1≈1.2255，paper replay≈.815–.830；更支持 waveform/routing/timing limitation。
- 结论边界： analysis-only checkpoint，不从 phase range/peak 单独宣称 event。
- 可视化阅读： 看 BJs activity window、BJL1 onset/delay/overlap、I(L1)/I(RB) split；它回答 waveform/routing/timing 而非单一 Ic。
- 入口：[报告 / 源文档](../test/exploration/paper-sl-q3-pre-20260824/analysis/REPORT.md)；[主图](../test/exploration/paper-sl-q3-pre-20260824/plots/comparison.html)；[补充图1](../test/exploration/paper-sl-q3-pre-20260824/plots/q0-68.4-ua.html)；[补充图2](../test/exploration/paper-sl-q3-pre-20260824/plots/q1-paper-sl-logical1.html)；[补充图3](../test/exploration/paper-sl-q3-pre-20260824/plots/q2-40u-paper-sl-logical1.html)
### PAPER-SL-Q3：L1 routing closure `bounded positive`
- 做了什么： 从 Q2 只改 L1=4.50pH，IBIAS=40µA。
- 结果： F_local .218660→.224945；G_local .515185→.526585；BJL1 .815414→.821070；BJL2 sub-turn。
- 结论边界： ROUTING_GAIN_WITH_BJL1_SUBTHRESHOLD；L1是 routing knob，增益弱。
- 可视化阅读： 看 F_local/G_local、BJL1 forward/backward segment 和 BJL2；Q3 只有 weak routing gain。
- 入口：[报告 / 源文档](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/analysis/REPORT.md)；[主图](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/plots/l1-4p5/comparison.html)；[补充图1](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/plots/l1-4p5/paper-j0-logical0-read.html)；[补充图2](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/plots/l1-4p5/paper-j0-logical0-read0-control.html)；[补充图3](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/plots/l1-4p5/paper-j1-logical1-read.html)
### PAPER-SL-Q4：L2 placement `bounded failure / no event`
- 做了什么： 固定 L1=3.91，只改 L2=4.50pH。
- 结果： BJL2≈.965402，但 BJL1/node2 routing 降级；largest segment=.965402 turn，零event。
- 结论边界： Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT；BJL2 strengthening 不要求先有 BJL1 slip。
- 可视化阅读： 分开看 BJL1 node2 degradation 与 BJL2 strengthening；不要用 total phase range 代替 largest monotonic segment。
- 入口：[报告 / 源文档](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/REPORT.md)；[主图](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/plots/q4-l1-3p91-l2-4p50/comparison.html)；[补充图1](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/plots/q4-l1-3p91-l2-4p50/paper-j0-logical0-read.html)；[补充图2](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/plots/q4-l1-3p91-l2-4p50/paper-j0-logical0-read0-control.html)；[补充图3](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/plots/q4-l1-3p91-l2-4p50/paper-j1-logical1-read.html)
### PAPER-SL-Q5：L1×L2 factorial `partial / near-threshold`
- 做了什么： 完成 L1=L2=4.50pH，检验 placement interaction。
- 结果： BJL1 partial recovery；BJL2=.968179、area=.968189、zero event；interaction≈−.003438。
- 结论边界： 无正 nonlinear BJL2 interaction；停止 passive L1/L2 tuning。
- 可视化阅读： 四点 factorial 要一起看 BJL1 recovery、BJL2 segment/area 和 interaction；Q5 接近 1 turn 仍为 zero event。
- 入口：[报告 / 源文档](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/REPORT.md)；[主图](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q5-l1-4p50-l2-4p50/comparison.html)；[补充图1](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q5-l1-4p50-l2-4p50/paper-j0-logical0-read.html)；[补充图2](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q5-l1-4p50-l2-4p50/paper-j0-logical0-read0-control.html)；[补充图3](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q5-l1-4p50-l2-4p50/paper-j1-logical1-read.html)
### PAPER-SL-Q6：Q5→two-cell JTL `bounded failure / no event`
- 做了什么： 把 frozen Q5 输出接 validated standard two-cell JTL。
- 结果： coupled Q5 BJL2≈.229249，四颗 JTL 无 complete event。
- 结论边界： NO_JTL_TRIGGER；不能把 coupled sub-turn activity叫 delivery。
- 可视化阅读： 同时看 coupled Q5 BJL2 与四颗 JTL JJ；load 改变 QB trajectory，不能只看 JTL voltage。
- 入口：[报告 / 源文档](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/REPORT.md)；[主图](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q6-q5-to-two-cell-jtl/comparison.html)；[补充图1](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q6-q5-to-two-cell-jtl/paper-j0-logical0-read.html)；[补充图2](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q6-q5-to-two-cell-jtl/paper-j0-logical0-read0-control.html)；[补充图3](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q6-q5-to-two-cell-jtl/paper-j1-logical1-read.html)

## 8. Load boundary 与 JTL transport reconciliation

区分 local event、接口负载效应和逐级 JTL transport。
### QB load-boundary matrix `analysis / method`
- 做了什么： 比较 Q0/Q5 在 10Ω、OPEN、JTL-only、10Ω+JTL 的边界效应。
- 结果： Q0+10Ω accepted exactly-one；OPEN/JTL/parallel 改变 event/retrap；Q5 near-event 对 load 更敏感。
- 结论边界： fixture-bounded load conclusion，不是 universal impedance rule。
- 可视化阅读： 按 Q0/Q5 两行比较 OPEN、10Ω、JTL-only、parallel 的 BJL2/OUT/L0；near-event 的 load sensitivity 更明显。
- 入口：[报告 / 源文档](../test/exploration/qb-load-boundary-matrix-20260824/analysis/REPORT.md)；[主图](../test/exploration/qb-load-boundary-matrix-20260824/plots/D-q5-open-paper-j0-logical0-read.html)；[补充图1](../test/exploration/qb-load-boundary-matrix-20260824/plots/D-q5-open-paper-j0-logical0-read0-control.html)；[补充图2](../test/exploration/qb-load-boundary-matrix-20260824/plots/D-q5-open-paper-j1-logical1-read.html)；[补充图3](../test/exploration/qb-load-boundary-matrix-20260824/plots/D-q5-open-paper-j1-logical1-read0-control.html)
### Parallel QB→JTL interface matrix `analysis / method`
- 做了什么： 用 M1–M5 分解 local event 与 JTL transport 丢失位置。
- 结果： M1 FIRST_STAGE_ONLY；M3 series-10Ω保留local event但JTL subthreshold；direct/parallel会丢event；M5 full-window为multi-well。
- 结论边界： strict local、settled well、full-window 不能混成一个 PASS。
- 可视化阅读： 分开看 QB phase matrix 与四颗 JTL phase matrix；M3 的 local event preserved/JTL subthreshold 是关键对照。
- 入口：[报告 / 源文档](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/analysis-v2/REPORT.md)；[主图](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M1-ideal-replay.html)；[补充图1](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M2-riso10.html)；[补充图2](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M3-rseries10.html)；[补充图3](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M4-liso10p.html)
### QB→JTL load back-action audit `analysis / method`
- 做了什么： 用 node-4 KCL 和分段窗口判断 load 何时改变 QB。
- 结果： KCL closes；direct/parallel 改变 pre-crossing partition，crossing 中继续分流；正式机制 MIXED_DYNAMIC_LOADING。
- 结论边界： 不是 scalar impedance universal law；限定已测 interfaces/windows。
- 可视化阅读： 看 node-4 KCL 的 I(L2)、I(L0)、I(BJL2)、I(RJ2) 在 crossing 前/中/后的 current partition。
- 入口：[报告 / 源文档](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/analysis/REPORT.md)；[主图](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/plots/backaction_compare.html)；[补充图1](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/plots/fixture-M3-series-10-JTL.html)；[补充图2](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/plots/fixture-Q0-10-JTL.html)；[补充图3](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/plots/fixture-Q0-10.html)
### JTL transport gate methodology `analysis / method`
- 做了什么： 建立 strict local、settled well、full-window、transport vector 分层读法。
- 结果： R11/M1/pulse5 可作方法参考；M5 历史 exactly-one 被 full-window multi-well supersede。
- 结论边界： 方法学图不替代正式 Gate；local turn 不自动是 downstream SFQ。
- 可视化阅读： 把 strict local、pre→post well、full-window 和 transport vector 分层读；不要把一个 settled well 当成一个 local turn。
- 入口：[报告 / 源文档](../test/exploration/jtl-transport-gate-v1-methodology-20260824/analysis/REPORT.md)；[主图](../test/exploration/jtl-transport-gate-v1-methodology-20260824/plots/M1-ideal-replay.html)；[补充图1](../test/exploration/jtl-transport-gate-v1-methodology-20260824/plots/M5-positive-control.html)；[补充图2](../test/exploration/jtl-transport-gate-v1-methodology-20260824/plots/R11-positive-control.html)；[补充图3](../test/exploration/jtl-transport-gate-v1-methodology-20260824/plots/pulse5-original.html)
### JTL numerical-freeze pilot `analysis / method`
- 做了什么： 第一次用 timestep ladder 尝试冻结 transport gate。
- 结果： pilot 因 unwrapped transform/hash/window 问题保持 INCONCLUSIVE_PENDING_STRICT_REPLAY。
- 结论边界： 缺陷历史保留，不是 Gate。
- 可视化阅读： 这是方法学缺陷记录；重点读 invalid transform/hash/window 说明，不把 provisional plot 当 Gate。
- 入口：[报告 / 源文档](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/analysis/REPORT.md)
### JTL numerical-freeze strict rerun `analysis / method`
- 做了什么： 用 dt=.025/.0125/.00625ps 重放 R11/pulse5 原/反极性。
- 结果： R11/pulse5-original 四-stage +1 随 dt 一致，reverse nontransport；window robustness 部分通过，仍 INCONCLUSIVE。
- 结论边界： 不能升级为 frozen Gate。
- 可视化阅读： 看三种 dt overlay 与注册 window robustness；数值一致性和窗口稳定性是两道不同检查。
- 入口：[报告 / 源文档](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/analysis/REPORT.md)；[主图](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-0p00625.html)；[补充图1](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-0p0125.html)；[补充图2](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-0p025.html)；[补充图3](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-timestep-comparison.html)
### JTL polarity replay reconciliation `analysis / method`
- 做了什么： 把 Q0 pulse-5 原/反极性 ideal replay 到同一 standard JTL。
- 结果： 确认 polarity asymmetry；原极性早期 local response 不能升级为 full-chain physical transport；反极性 nontransport。
- 结论边界： strict local 与 full-window/pre-post 分开，不能称 physical Q0→JTL。
- 可视化阅读： 原/反极性对齐同一 JTL cell、同一窗口；先看 local onset，再看 full-window/pre-post well。
- 入口：[报告 / 源文档](../test/exploration/jtl-transport-gate-polarity-replay-20260824/analysis/REPORT.md)；[主图](../test/exploration/jtl-transport-gate-polarity-replay-20260824/plots/original-vs-reverse.html)；[补充图1](../test/exploration/jtl-transport-gate-polarity-replay-20260824/plots/original.html)；[补充图2](../test/exploration/jtl-transport-gate-polarity-replay-20260824/plots/reverse.html)
### q3-l1-routing-closure：历史别名目录 `路径控制`
- 做了什么： 保留历史路径，防止旧目录被误当独立证据。
- 结果： 目录没有独立 report/raw；正式证据在 PAPER-SL-Q3 目录。
- 结论边界： 不是新实验，不重复计入 scientific result。
- 可视化阅读： 跳转到正式 PAPER-SL-Q3 图形；该目录不应产生第二套 evidence。
- 入口：[主图](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/plots/l1-4p5/comparison.html)

## 结构拓扑总览

结构入口区分 publication schematic 与 legacy Graphviz connectivity-debug；参考图：[BVM.png](../arti/BVM.png)、[BVMstructure.png](../arti/BVMstructure.png)、[BQstructure.png](../arti/BQstructure.png)。参数或 PWL-only 变体共用主图，结构不同的变体另列。

| Exploration | 主结构图 | 拓扑说明 | 结构变体 |
|---|---|---|---|
| `bvm-internal-readout-20260819` | [论文级电路图](../test/exploration/bvm-internal-readout-20260819/topology/schematic.svg)；[annotated schematic](../test/exploration/bvm-internal-readout-20260819/topology/schematic-annotated.svg)；[debug graph](../test/exploration/bvm-internal-readout-20260819/topology/connectivity-debug.svg) | [README](../test/exploration/bvm-internal-readout-20260819/topology/README.md) | 无 |
| `bvm-sfq-receiver-native-qb-20260822` | [主图](../test/exploration/bvm-sfq-receiver-native-qb-20260822/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-native-qb-20260822/topology/README.md) | 无 |
| `bvm-sfq-receiver-r0-20260819` | [主图](../test/exploration/bvm-sfq-receiver-r0-20260819/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r0-20260819/topology/README.md) | 无 |
| `bvm-sfq-receiver-r0b-20260819` | [主图](../test/exploration/bvm-sfq-receiver-r0b-20260819/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r0b-20260819/topology/README.md) | 无 |
| `bvm-sfq-receiver-r1-oneshot-20260819` | [主图](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/topology/README.md) | 无 |
| `bvm-sfq-receiver-r10a-local-bjl2-bias-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/topology/README.md) | 无 |
| `bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/topology/README.md) | [positive-control](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/topology/variants/positive-control/topology.svg) |
| `bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/topology/README.md) | [phase-a-zero](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/topology/variants/phase-a-zero/topology.svg) |
| `bvm-sfq-receiver-r13a-temporal-conditioning-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/topology/README.md) | 无 |
| `bvm-sfq-receiver-r14a-dcsfq-detector-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/topology/README.md) | 无 |
| `bvm-sfq-receiver-r15a-afq3-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/topology/README.md) | 无 |
| `bvm-sfq-receiver-r15b-magnetic-correction-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/topology/README.md) | 无 |
| `bvm-sfq-receiver-r15c-jset-causal-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/topology/README.md) | 无 |
| `bvm-sfq-receiver-r15d-jq-compressor-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/topology/README.md) | 无 |
| `bvm-sfq-receiver-r1a-transfer-20260819` | [主图](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/topology/README.md) | 无 |
| `bvm-sfq-receiver-r1b-area008-20260821` | [主图](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/topology/README.md) | 无 |
| `bvm-sfq-receiver-r1b-differential-output-20260821` | [主图](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/topology/README.md) | [diff-a010-b07-r100-series-return-read1](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/topology/variants/diff-a010-b07-r100-series-return-read1/topology.svg) |
| `bvm-sfq-receiver-r1b-output-jj-20260819` | [主图](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/topology/README.md) | [l010-b07-rd100-loop-read1](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/topology/variants/l010-b07-rd100-loop-read1/topology.svg) |
| `bvm-sfq-receiver-r1c-bias-margin-20260821` | [主图](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/topology/README.md) | 无 |
| `bvm-sfq-receiver-r2a-coupling-20260821` | [主图](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/topology/README.md) | 无 |
| `bvm-sfq-receiver-r2b-damping-20260821` | [主图](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/topology/README.md) | 无 |
| `bvm-sfq-receiver-r2c-directdrive-20260821` | [主图](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/topology/README.md) | [ctrl-nopulse](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/topology/variants/ctrl-nopulse/topology.svg) |
| `bvm-sfq-receiver-r2d-duration-20260821` | [主图](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/topology/README.md) | 无 |
| `bvm-sfq-receiver-r2e-ampthreshold-20260821` | [主图](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/topology/README.md) | 无 |
| `bvm-sfq-receiver-r2f-dwell-20260821` | [主图](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/topology/README.md) | 无 |
| `bvm-sfq-receiver-r2g-twopulse-20260821` | [主图](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/topology/README.md) | 无 |
| `bvm-sfq-receiver-r3a-onset-extraction-20260822` | [主图](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/topology/README.md) | 无 |
| `bvm-sfq-receiver-r4a-weak-mutual-capture-20260822` | [主图](../test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/topology/README.md) | 无 |
| `bvm-sfq-receiver-r5a-biased-quantizer-20260822` | [主图](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/topology/README.md) | 无 |
| `bvm-sfq-receiver-r5b-loadline-20260822` | [主图](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/topology/README.md) | 无 |
| `bvm-sfq-receiver-r5c-saddle-selectivity-20260822` | [主图](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/topology/README.md) | 无 |
| `bvm-sfq-receiver-r6a-native-qb-isolation-20260822` | [主图](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/topology/README.md) | 无 |
| `bvm-sfq-receiver-r6b-native-qb-ratio-20260822` | [主图](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/topology/README.md) | 无 |
| `bvm-sfq-receiver-r7a-l1-routing-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/topology/README.md) | 无 |
| `bvm-sfq-receiver-r8-bjl2-area070-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/topology/README.md) | 无 |
| `bvm-sfq-receiver-r9a-l2-routing-20260823` | [主图](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/topology/topology.svg) | [README](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/topology/README.md) | 无 |
| `jtl-transport-gate-polarity-replay-20260824` | [主图](../test/exploration/jtl-transport-gate-polarity-replay-20260824/topology/topology.svg) | [README](../test/exploration/jtl-transport-gate-polarity-replay-20260824/topology/README.md) | 无 |
| `jtl-transport-gate-v1-methodology-20260824` | [主图](../test/exploration/jtl-transport-gate-v1-methodology-20260824/topology/topology.svg) | [README](../test/exploration/jtl-transport-gate-v1-methodology-20260824/topology/README.md) | 无 |
| `jtl-transport-gate-v1-numerical-freeze-20260824` | [主图](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/topology/topology.svg) | [README](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/topology/README.md) | [main](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/topology/variants/main/topology.svg) |
| `jtl-transport-gate-v1-numerical-freeze-20260824-rerun` | [主图](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/topology/topology.svg) | [README](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/topology/README.md) | [main](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/topology/variants/main/topology.svg) |
| `paper-sl-l0-20260824` | [主图](../test/exploration/paper-sl-l0-20260824/topology/topology.svg) | [README](../test/exploration/paper-sl-l0-20260824/topology/README.md) | 无 |
| `paper-sl-q1-20260824` | [主图](../test/exploration/paper-sl-q1-20260824/topology/topology.svg) | [README](../test/exploration/paper-sl-q1-20260824/topology/README.md) | [q0-68p4u-positive-control](../test/exploration/paper-sl-q1-20260824/topology/variants/q0-68p4u-positive-control/topology.svg) |
| `paper-sl-q2-20260824` | [主图](../test/exploration/paper-sl-q2-20260824/topology/topology.svg) | [README](../test/exploration/paper-sl-q2-20260824/topology/README.md) | [paper-j1-logical1-read0-control](../test/exploration/paper-sl-q2-20260824/topology/variants/paper-j1-logical1-read0-control/topology.svg) |
| `paper-sl-q3-l1-routing-closure-20260824` | [主图](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/topology/topology.svg) | [README](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/topology/README.md) | 无 |
| `paper-sl-q3-pre-20260824` | [主图](../test/exploration/paper-sl-q3-pre-20260824/topology/topology.svg) | [README](../test/exploration/paper-sl-q3-pre-20260824/topology/README.md) | 无 |
| `paper-sl-q4-l1-l2-placement-20260824` | [主图](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/topology/topology.svg) | [README](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/topology/README.md) | 无 |
| `paper-sl-q5-l1-l2-factorial-20260824` | [主图](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/topology/topology.svg) | [README](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/topology/README.md) | 无 |
| `paper-sl-q6-qb-jtl-compatibility-20260824` | [主图](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/topology/topology.svg) | [README](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/topology/README.md) | 无 |
| `parallel-qb-jtl-interface-mechanism-20260824` | [主图](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/topology.svg) | [README](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/README.md) | [main](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main/topology.svg)、[main-2](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-2/topology.svg)、[main-3](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-3/topology.svg)、[main-4](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-4/topology.svg)、[main-5](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-5/topology.svg) |
| `q3-l1-routing-closure-20260824` | [主图](../test/exploration/q3-l1-routing-closure-20260824/topology/topology.svg) | [README](../test/exploration/q3-l1-routing-closure-20260824/topology/README.md) | 无 |
| `qb-load-boundary-matrix-20260824` | [主图](../test/exploration/qb-load-boundary-matrix-20260824/topology/topology.svg) | [README](../test/exploration/qb-load-boundary-matrix-20260824/topology/README.md) | [paper-j1-logical1-read](../test/exploration/qb-load-boundary-matrix-20260824/topology/variants/paper-j1-logical1-read/topology.svg)、[paper-j1-logical1-read-2](../test/exploration/qb-load-boundary-matrix-20260824/topology/variants/paper-j1-logical1-read-2/topology.svg)、[scaled-iin-68p4u](../test/exploration/qb-load-boundary-matrix-20260824/topology/variants/scaled-iin-68p4u/topology.svg)、[scaled-iin-68p4u-2](../test/exploration/qb-load-boundary-matrix-20260824/topology/variants/scaled-iin-68p4u-2/topology.svg) |
| `qb-q0-standalone-current-quantized-event-20260824` | [论文级电路图](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic.svg)；[annotated schematic](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic-annotated.svg)；[debug graph](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/connectivity-debug.svg) | [README](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/README.md) | [test-bvm-paper-bq](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/variants/test-bvm-paper-bq/topology.svg)、[test-qb-final](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/variants/test-qb-final/topology.svg) |
| `qb-q1-canonical-bvm-scaled-qb-compatibility-20260824` | [主图](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/topology/topology.svg) | [README](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/topology/README.md) | 无 |
| `qb-q2a-source-decoupled-waveform-replay-20260824` | [主图](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/topology.svg) | [README](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/README.md) | [b-q1-loaded-vsl](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/variants/b-q1-loaded-vsl/topology.svg) |
| `qb-q2b-central-bias-bracketing-20260824` | [主图](../test/exploration/qb-q2b-central-bias-bracketing-20260824/topology/topology.svg) | [README](../test/exploration/qb-q2b-central-bias-bracketing-20260824/topology/README.md) | 无 |
| `qb-q2c-uniform-junction-scale-20260824` | [主图](../test/exploration/qb-q2c-uniform-junction-scale-20260824/topology/topology.svg) | [README](../test/exploration/qb-q2c-uniform-junction-scale-20260824/topology/README.md) | 无 |
| `qb-to-jtl-load-backaction-causal-audit-v1-20260824` | [主图](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/topology/topology.svg) | [README](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/topology/README.md) | 无 |
## 本次补齐的 raw-case 可视化

以下目录原先有 raw CSV 但没有 HTML 结果图；overview 直接读取全部可用 case，按真实 CSV header 绘制 phase/voltage/current，不能替代 report 的 event 判定。

| Exploration | overview | 说明 |
|---|---|---|
| `bvm-sfq-receiver-native-qb-20260822` | [classic overview](../test/exploration/bvm-sfq-receiver-native-qb-20260822/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-native-qb-20260822/plots/overview-README.md) |
| `bvm-sfq-receiver-r0-20260819` | [classic overview](../test/exploration/bvm-sfq-receiver-r0-20260819/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r0-20260819/plots/overview-README.md) |
| `bvm-sfq-receiver-r1-oneshot-20260819` | [classic overview](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/plots/overview-README.md) |
| `bvm-sfq-receiver-r10a-local-bjl2-bias-20260823` | [classic overview](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/plots/overview-README.md) |
| `bvm-sfq-receiver-r15c-jset-causal-20260823` | [classic overview](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/plots/overview-README.md) |
| `bvm-sfq-receiver-r15d-jq-compressor-20260823` | [classic overview](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/plots/overview-README.md) |
| `bvm-sfq-receiver-r1b-area008-20260821` | [classic overview](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/plots/overview-README.md) |
| `bvm-sfq-receiver-r1b-differential-output-20260821` | [classic overview](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/plots/overview-README.md) |
| `bvm-sfq-receiver-r1b-output-jj-20260819` | [classic overview](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/plots/overview-README.md) |
| `bvm-sfq-receiver-r1c-bias-margin-20260821` | [classic overview](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/plots/overview-README.md) |
| `bvm-sfq-receiver-r2b-damping-20260821` | [classic overview](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/plots/overview-README.md) |
| `bvm-sfq-receiver-r2c-directdrive-20260821` | [classic overview](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/plots/overview-README.md) |
| `bvm-sfq-receiver-r2d-duration-20260821` | [classic overview](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/plots/overview-README.md) |
| `bvm-sfq-receiver-r2e-ampthreshold-20260821` | [classic overview](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/plots/overview-README.md) |
| `bvm-sfq-receiver-r2f-dwell-20260821` | [classic overview](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/plots/overview-README.md) |
| `bvm-sfq-receiver-r2g-twopulse-20260821` | [classic overview](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/plots/overview-README.md) |
| `bvm-sfq-receiver-r3a-onset-extraction-20260822` | [classic overview](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/plots/overview-README.md) |
| `bvm-sfq-receiver-r5a-biased-quantizer-20260822` | [classic overview](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/plots/overview-README.md) |
| `bvm-sfq-receiver-r5b-loadline-20260822` | [classic overview](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/plots/overview-README.md) |
| `bvm-sfq-receiver-r5c-saddle-selectivity-20260822` | [classic overview](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/plots/overview-README.md) |
| `bvm-sfq-receiver-r6a-native-qb-isolation-20260822` | [classic overview](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/plots/overview-README.md) |
| `bvm-sfq-receiver-r6b-native-qb-ratio-20260822` | [classic overview](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/plots/overview-README.md) |
| `bvm-sfq-receiver-r7a-l1-routing-20260823` | [classic overview](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/plots/overview-README.md) |
| `bvm-sfq-receiver-r8-bjl2-area070-20260823` | [classic overview](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/plots/overview-README.md) |
| `bvm-sfq-receiver-r9a-l2-routing-20260823` | [classic overview](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/plots/overview.html) | [README](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/plots/overview-README.md) |
| `jtl-transport-gate-v1-numerical-freeze-20260824` | [classic overview](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/plots/overview.html) | [README](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/plots/overview-README.md) |
| `paper-sl-l0-20260824` | [classic overview](../test/exploration/paper-sl-l0-20260824/plots/overview.html) | [README](../test/exploration/paper-sl-l0-20260824/plots/overview-README.md) |
| `qb-q1-canonical-bvm-scaled-qb-compatibility-20260824` | [classic overview](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/plots/overview.html) | [README](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/plots/overview-README.md) |
| `qb-q2a-source-decoupled-waveform-replay-20260824` | [classic overview](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/plots/overview.html) | [README](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/plots/overview-README.md) |
| `qb-q2b-central-bias-bracketing-20260824` | [classic overview](../test/exploration/qb-q2b-central-bias-bracketing-20260824/plots/overview.html) | [README](../test/exploration/qb-q2b-central-bias-bracketing-20260824/plots/overview-README.md) |
| `qb-q2c-uniform-junction-scale-20260824` | [classic overview](../test/exploration/qb-q2c-uniform-junction-scale-20260824/plots/overview.html) | [README](../test/exploration/qb-q2c-uniform-junction-scale-20260824/plots/overview-README.md) |
## 统一读图规则
1. `P(...)` 原始量是 radians；turns 是同一时间端点的 `Δphase/(2π)`。
2. complete event 必须同时满足 continuous unwrapped phase、monotonic segment、same-JJ/same-segment direct voltage-area 和 bounded post/retrap；phase range、voltage peak、I>Ic 单独都不够。
3. strict local event、pre→post settled well、full-window phase/area 是不同证据层，尤其 JTL 不可混用。
4. 图形是描述性 checkpoint；正式 verdict、artifact validity 和 source/storage guard 以各节点 report/summary 为准。
5. 失败结论限定于当前 fixture/model/window，不自动外推为整个 architecture family 不可能。
