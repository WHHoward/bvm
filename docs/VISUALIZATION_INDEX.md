# VISUALIZATION INDEX V2

生成基线 HEAD：`576ca9d32b15c99f8c35c4271336ffa079664b64`。

本页由统一 alignment manifest 生成，按科学语义列出核心结果、对比、controls 和 source/reference。

## 阅读约定

- `continuous_absolute`：原始 JoSIM P(...) 连续轨迹的 φ/2π（turn），不等于 SFQ 计数。
- source/reference/historical 图不能作为 current result 的核心证据。
- 论文级 schematic、annotated schematic、connectivity debug graph 分开列出。

## Canonical BVM：storage/readout source baseline

**实验 ID**：`test/exploration/bvm-internal-readout-20260819`

**做了什么**：对 canonical BVM 做 write/read 与 READ=0 对照，检查 JM1/JM2、JS1/JS2、SL、N6 及 read timing。

**关键结果**：read1/read0 的 storage sign 与 SL/N6 输出保持稳定区分；read1 有强 R-loop/JS activity，read0 主要是 READ-edge response，因此该结果被用作 source baseline。

**当前状态**：`ACCEPTED_CANONICAL_SOURCE` / alignment=`ALIGNED`

**结论边界**：这是 BVM source/read baseline，不是 receiver switching 或 SFQ-delivery 结果。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-internal-readout-20260819/plots/alignment-overview.html](../test/exploration/bvm-internal-readout-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-internal-readout-20260819/topology/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-internal-readout-20260819/topology/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-internal-readout-20260819/topology/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-internal-readout-20260819/summary.md](../test/exploration/bvm-internal-readout-20260819/summary.md)

---

## R0：SL-route trigger discrimination

**实验 ID**：`test/exploration/bvm-sfq-receiver-r0-20260819`

**做了什么**：在 canonical SL 后接最小外部 JJ trigger，比较 logical1/read1、logical0/read0 和两个 READ=0 controls。

**关键结果**：R0 PARTIAL：R0-A threshold discrimination PASS；read1 与 read0/controls 分离且 source/storage guard 保持，但 read1 B_TRIG excursion 未满足完整 2π transition。

**当前状态**：`R0_PARTIAL` / alignment=`ALIGNED`

**结论边界**：不能称 complete trigger switching、exactly-one、self-quench 或 SFQ delivery。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r0-20260819/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r0-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r0-20260819/topology/publication/TOPOLOGY_75d201da61/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r0-20260819/topology/publication/TOPOLOGY_75d201da61/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r0-20260819/topology/publication/TOPOLOGY_75d201da61/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r0-20260819/analysis/R0_REPORT.md](../test/exploration/bvm-sfq-receiver-r0-20260819/analysis/R0_REPORT.md)

---

## R0b：complete trigger closure

**实验 ID**：`test/exploration/bvm-sfq-receiver-r0b-20260819`

**做了什么**：保持 SL route，使用 B_TRIG AREA=.50、bias=+15 µA，执行 read1/read0/两个 READ=0 matched cases。

**关键结果**：R0b PASS：read1 出现约 4.997-turn continuous complete segment；read0 最大约 0.185 turn，controls 无完整 transition，source/storage guard 保持。

**当前状态**：`R0B_PASS` / alignment=`ALIGNED`

**结论边界**：这是 multi-turn local trigger closure，不是 exactly-one SFQ、self-quench 或 downstream delivery。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r0b-20260819/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r0b-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r0b-20260819/topology/publication/TOPOLOGY_2600b475f4/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r0b-20260819/topology/publication/TOPOLOGY_2600b475f4/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r0b-20260819/topology/publication/TOPOLOGY_2600b475f4/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r0b-20260819/analysis/R0B_REPORT.md](../test/exploration/bvm-sfq-receiver-r0b-20260819/analysis/R0B_REPORT.md)

---

## R1：parallel feedback one-shot attempt

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1-oneshot-20260819`

**做了什么**：在 B_TRIG 后加入 parallel LQ–RQ feedback/transfer branch，尝试把 trigger running 压缩为 one-shot output。

**关键结果**：R1 FAIL：强 feedback branch 明显加载并压制 B_TRIG，弱 branch 虽保留 trigger 却不能提供足够 transfer；该拓扑没有建立 read1 output event。

**当前状态**：`R1_FAIL` / alignment=`ALIGNED`

**结论边界**：只否定当前 parallel LQ–RQ instance，不否定所有 one-shot 或 transfer family。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/topology/publication/TOPOLOGY_658acd44d8/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/topology/publication/TOPOLOGY_658acd44d8/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/topology/publication/TOPOLOGY_658acd44d8/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/analysis/R1_REPORT.md](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/analysis/R1_REPORT.md)

---

## R1a：series pickup passive transfer

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1a-transfer-20260819`

**做了什么**：用 SL→R_IN→L_TX→B_TRIG 的 series pickup，并以 L_TX–L_SEC mutual coupling 接 passive secondary/load。

**关键结果**：R1a PASS：read1 B_TRIG 约 3.944-turn complete，read0 约 0.185-turn；secondary read1 约 66.77 µV/5.56 µA，约为 read0 的 4.9 倍，controls inactive。

**当前状态**：`R1A_PASS` / alignment=`ALIGNED`

**结论边界**：建立的是 passive state-dependent extraction，不是 output-JJ switching、one-shot 或 SFQ delivery。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/topology/publication/TOPOLOGY_73d3c8d7f4/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/topology/publication/TOPOLOGY_73d3c8d7f4/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/topology/publication/TOPOLOGY_73d3c8d7f4/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/analysis/R1A_REPORT.md](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/analysis/R1A_REPORT.md)

---

## R1b：common-mode secondary → B_OUT

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819`

**做了什么**：把 R1a secondary 接到最小 output JJ，并检查 secondary 是否在 B_OUT 两端形成有效 differential drive。

**关键结果**：FAIL 的根因是 common-mode：V(N_OUT) 跟随 V(N_SEC)，V(B_OUT) 近 numerical zero，I(B_OUT) 与 phase 基本恒定；没有实际 differential activation。

**当前状态**：`R1B_FAIL` / alignment=`ALIGNED`

**结论边界**：这是接口/KCL 失配，不是通过调 AREA、bias 或 damping 可以诊断的 output-margin 结果。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/topology/publication/TOPOLOGY_5233bbad6e/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/topology/publication/TOPOLOGY_5233bbad6e/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/topology/publication/TOPOLOGY_5233bbad6e/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/analysis/R1B_REPORT.md](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/analysis/R1B_REPORT.md)

---

## R1b-area=.08：output-JJ barrier diagnostic

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1b-area008-20260821`

**做了什么**：保持 R1b differential topology，只将 B_OUT AREA 从 .10 改为 .08，比较 read1/read0/controls。

**关键结果**：AREA=.08 未提高 activation：read1 最大 B_OUT segment 约 0.020 turn，read0/controls 无完整 event；read1 signal 仍存在但远离 switching。

**当前状态**：`R1B_AREA008_FAIL` / alignment=`ALIGNED`

**结论边界**：AREA 同时改变 Ic、C、RN、R0，因此只能说明该 output-class point 不足，不能归因于纯 Ic reduction。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1b-area008-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/topology/publication/TOPOLOGY_7dca5b0bd5/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/topology/publication/TOPOLOGY_7dca5b0bd5/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/topology/publication/TOPOLOGY_7dca5b0bd5/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1b-area008-20260821/analysis/R1B_AREA008_REPORT.md](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/analysis/R1B_AREA008_REPORT.md)

---

## R1b：differential secondary-driven output

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821`

**做了什么**：修正 secondary→B_OUT 的 differential KCL，使 induced current 直接进入 B_OUT 对地支路，并保留 R1a secondary/load。

**关键结果**：因果 transfer 成立：read1 B_OUT 有 state-dependent transient，但最大连续段仅约 0.022 turn；read0/controls 无 event，B_TRIG/source guards 保持。

**当前状态**：`R1B_FAIL` / alignment=`ALIGNED`

**结论边界**：证明 signal existence，不证明 output-JJ activation；随后 AREA/bias 诊断均仍是 bounded sub-turn。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/topology/publication/TOPOLOGY_a8dab02d1d/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/topology/publication/TOPOLOGY_a8dab02d1d/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/topology/publication/TOPOLOGY_a8dab02d1d/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/analysis/R1B_DIFF_REPORT.md](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/analysis/R1B_DIFF_REPORT.md)

---

## R1c：B_OUT bias-margin diagnostic

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821`

**做了什么**：冻结 AREA=.10、transformer、secondary、damping，只测试 B_OUT bias 6/7/8/9/10 µA。

**关键结果**：所有 bias 点都有 state-dependent read1 transient，但没有完整 B_OUT transition；read0/controls 无 event，因此 bias operating point 不是该 fixture 的主要解法。

**当前状态**：`R1C_FAIL` / alignment=`ALIGNED`

**结论边界**：这是局部 bias bracket，未测试其他 topology，也没有 downstream SFQ/JTL 结论。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/topology/publication/TOPOLOGY_ac497f8640/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/topology/publication/TOPOLOGY_ac497f8640/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/topology/publication/TOPOLOGY_ac497f8640/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/analysis/R1C_BIAS_REPORT.md](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/analysis/R1C_BIAS_REPORT.md)

---

## R2-A：mutual-coupling transfer diagnostic

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2a-coupling-20260821`

**做了什么**：冻结 R1b differential receiver，只比较 K=.6/.7/.8/.9/.95 对 secondary 与 B_OUT activation 的影响。

**关键结果**：增大 K 会增强 secondary，但 read1 B_OUT 仍停留在约 10^-2-turn 级，未形成 complete event；read0/controls 与 source guards 保持。

**当前状态**：`R2A_FAIL_NO_COMPLETE_BOUT` / alignment=`ALIGNED`

**结论边界**：否定当前 coupling matrix 的 activation closure，不否定全部 transformer/mutual family；动态 dwell/receiver load 仍未解决。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/topology/publication/TOPOLOGY_a5649ee5af/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/topology/publication/TOPOLOGY_a5649ee5af/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/topology/publication/TOPOLOGY_a5649ee5af/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/analysis/R2A_COUPLING_REPORT.md](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/analysis/R2A_COUPLING_REPORT.md)

---

## R2-B：receiver damping diagnostic

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2b-damping-20260821`

**做了什么**：冻结其他条件，只改变 output damping，观察 underdamped/overdamped 变化是否能释放 B_OUT phase slip。

**关键结果**：减弱 damping 只使 read1 最大段约 0.0261→0.0290 turn（约 10.9%），没有 complete event；read0/controls 和 BVM guards 保持。

**当前状态**：`R2B_NO_COMPLETE_EVENT` / alignment=`ALIGNED`

**结论边界**：只说明当前 damping sweep 不是主瓶颈，不代表所有拓扑中的 damping 都无关。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2b-damping-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/topology/publication/TOPOLOGY_b01953770c/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/topology/publication/TOPOLOGY_b01953770c/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/topology/publication/TOPOLOGY_b01953770c/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2b-damping-20260821/analysis/R2B_DAMPING_REPORT.md](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/analysis/R2B_DAMPING_REPORT.md)

---

## R2-C：fast direct-drive threshold

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821`

**做了什么**：将实测 read1 narrow forward lobe 以 ideal direct current 注入 secondary，固定快脉冲形状，测试有限 amplitude matrix。

**关键结果**：没有 amplitude 点产生完整 B_OUT event；约 78% 快注入电流被 N_SEC 的 reactive/resistive shunts 分流，junction drive transfer 约 22.4%。

**当前状态**：`NO_THRESHOLD_BOUNDED_FAST_MATRIX` / alignment=`ALIGNED`

**结论边界**：这是 fast-transient fixture 的 duration/load limitation，不是静态 Ic threshold 的普适结论。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/topology/publication/TOPOLOGY_0da30ee288/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/topology/publication/TOPOLOGY_0da30ee288/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/topology/publication/TOPOLOGY_0da30ee288/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/analysis/R2C_DIRECTDRIVE_REPORT.md](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/analysis/R2C_DIRECTDRIVE_REPORT.md)

---

## R2-D：direct-drive duration bracket

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2d-duration-20260821`

**做了什么**：固定 3.5 µA direct-drive amplitude，只增加 pulse FWHM/有效持续时间。

**关键结果**：响应随 duration 非线性增大（最大段约 .0096→.0835 turn），但矩阵内仍无完整 event；20 ps 点已接近 96% Ic 的 quasi-static ceiling。

**当前状态**：`NO_THRESHOLD_BOUNDED_DURATION_MATRIX` / alignment=`ALIGNED`

**结论边界**：在该 amplitude 下 duration alone 不够；下一限制转向 amplitude，不能推出所有更长脉冲都无效。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2d-duration-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/topology/publication/TOPOLOGY_a61a44b0c0/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/topology/publication/TOPOLOGY_a61a44b0c0/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/topology/publication/TOPOLOGY_a61a44b0c0/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2d-duration-20260821/analysis/R2D_DURATION_REPORT.md](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/analysis/R2D_DURATION_REPORT.md)

---

## R2-E：quasi-static amplitude threshold

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821`

**做了什么**：固定 20 ps pulse width/shape，测试 4.0/4.5/5.0 µA direct-drive amplitude。

**关键结果**：所有点都接近 Ic 但没有完整 B_OUT segment，正式结论为 bounded matrix 内 NO_THRESHOLD；没有建立 switching threshold。

**当前状态**：`NO_THRESHOLD_BOUNDED_MATRIX` / alignment=`ALIGNED`

**结论边界**：不能把 I≈Ic 或 voltage peak 当 event，也不涉及 retrap、JTL 或 physical transformer。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/topology/publication/TOPOLOGY_879c0c5b61/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/topology/publication/TOPOLOGY_879c0c5b61/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/topology/publication/TOPOLOGY_879c0c5b61/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/analysis/R2E_AMPTHRESHOLD_REPORT.md](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/analysis/R2E_AMPTHRESHOLD_REPORT.md)

---

## R2-F：near-critical dwell closure

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2f-dwell-20260821`

**做了什么**：固定 4.5 µA direct-drive，增加 0/5/10/20 ps flat-top hold，检查 near-critical creep 是否完成 phase slip。

**关键结果**：20 ps hold 首次产生一个约 1.0039-turn、phase/area 一致且 retrap 的 local B_OUT event；0–10 ps 为 near-miss。

**当前状态**：`DWELL_THRESHOLD_FOUND` / alignment=`ALIGNED`

**结论边界**：这是理想 direct-drive output-stage requirement，不是 BVM→receiver 或 downstream SFQ delivery。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/topology/publication/TOPOLOGY_7278e859dc/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/topology/publication/TOPOLOGY_7278e859dc/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/topology/publication/TOPOLOGY_7278e859dc/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/analysis/R2F_DWELL_REPORT.md](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/analysis/R2F_DWELL_REPORT.md)

---

## R2-G：two-pulse retrigger/rearm

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821`

**做了什么**：在 R2-F h20 点输入两个间隔约 60 ps 的相同 4.5 µA/20 ps-hold pulse，直接检查两次 local slip 和中间 retrap。

**关键结果**：两个 pulse 各产生 exactly one local complete slip，间隔期间 retrap/rearm 清晰，无 multifire/free-running；建立了 direct-drive 的 2-pulse single-slip primitive。

**当前状态**：`REPEATABLE_TWO_PULSE_SINGLE_SLIP` / alignment=`ALIGNED`

**结论边界**：只证明理想 direct-drive output stage 的局部可重复性，不证明真实 transformer、BVM、JTL 或 T1。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/topology/publication/TOPOLOGY_ad32926098/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/topology/publication/TOPOLOGY_ad32926098/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/topology/publication/TOPOLOGY_ad32926098/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/analysis/R2G_TWOPULSE_REPORT.md](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/analysis/R2G_TWOPULSE_REPORT.md)

---

## R3-A：B_TRIG onset extractor

**实验 ID**：`test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822`

**做了什么**：用 1 fF C_ON 将 B_TRIG onset 变成 fast differentiated spike，再驱动 B_OUT/hold branch。

**关键结果**：read1 的 C_ON current 可达约 2.24 µA，但 B_OUT causal-window peak 仅约 8.06 µA、相对 bias 只有约 1.06 µA；四 cases 均无 complete event。

**当前状态**：`NO_OUTPUT_EVENT` / alignment=`ALIGNED`

**结论边界**：只否定该 fast capacitive extractor instance；失败位于 transient→sustained drive，不否定所有 B_TRIG extraction。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/topology/publication/TOPOLOGY_a4ff2838c2/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/topology/publication/TOPOLOGY_a4ff2838c2/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/topology/publication/TOPOLOGY_a4ff2838c2/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/analysis/R3A_ONSET_REPORT.md](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/analysis/R3A_ONSET_REPORT.md)

---

## R4-A：weak-mutual passive flux capture

**实验 ID**：`test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822`

**做了什么**：用 B_TRIG→weak mutual→100 pH capture loop/J_SET，测试 read1 是否留下 persistent fluxoid state。

**关键结果**：read1 loop 最大 circulating current 约 4.874 µA，仅约 half-quantum boundary 的一小部分，最终回到 n=0；read0/controls 更小，J_SET 无 complete slip。

**当前状态**：`R4A_NO_PERSISTENT_READ1_STATE` / alignment=`NO_WAVEFORM_VISUALIZATION_REQUIRED`

**结论边界**：降级的是该 passive weak-mutual single point，不是整个 mutual-coupling family；capture 需要更强 transfer 或 bias-assisted quantization。

**推荐先看**：

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/topology/publication/TOPOLOGY_cb0a106fd7/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/topology/publication/TOPOLOGY_cb0a106fd7/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/topology/publication/TOPOLOGY_cb0a106fd7/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/analysis/R4A_AMENDED_REPORT.md](../test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/analysis/R4A_AMENDED_REPORT.md)

---

## R5-A：reduced biased quantizer

**实验 ID**：`test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822`

**做了什么**：给单 JJ quantizer 加独立 bias，在实际 B_TRIG mutual drive 下检查 read1 是否跨过 nonlinear saddle 并 escape。

**关键结果**：read1 产生 large bounded plasma oscillation并跨过 analytic reverse-critical displacement，但没有 complete phase slip；read0/controls clean。

**当前状态**：`R5A_NO_SET_EVENT` / alignment=`ALIGNED`

**结论边界**：说明 amplitude 已足以产生强 nonlinear activity，但缺少不可逆性/不对称 escape；不能称 quantization。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/topology/publication/TOPOLOGY_16ea7d821b/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/topology/publication/TOPOLOGY_16ea7d821b/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/topology/publication/TOPOLOGY_16ea7d821b/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/analysis/R5A_REPORT.md](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/analysis/R5A_REPORT.md)

---

## R5-B：minimal SET shunt/load-line test

**实验 ID**：`test/exploration/bvm-sfq-receiver-r5b-loadline-20260822`

**做了什么**：先保留并诊断 wiring correction，再把最小 shunt 放到 functionally active 的 SET boundary，测试其是否促成 escape。

**关键结果**：active shunt 实际只是额外 damping/current diversion，使 R5-A oscillation 收缩、没有 complete event；结论是 paper-QB 的 bias placement 不能用 SET 并联 shunt 替代。

**当前状态**：`R5B_STILL_BOUNDED_OSCILLATION` / alignment=`ALIGNED`

**结论边界**：否定该 minimal direct-shunt hypothesis，不等于完整 paper QB 已被实验闭合。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/topology/publication/TOPOLOGY_36fb1f63c9/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/topology/publication/TOPOLOGY_36fb1f63c9/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/topology/publication/TOPOLOGY_36fb1f63c9/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/analysis/R5B_REPORT.md](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/analysis/R5B_REPORT.md)

---

## R5-C：correct-saddle selectivity

**实验 ID**：`test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822`

**做了什么**：使用完整 nonlinear loop equation 选 bias，使 read1 预计跨真实 saddle，再用四 matched cases 检查 local phase escape。

**关键结果**：read1 确实跨过正确 static saddle，但仍为 bounded multi-lobe oscillation、没有 complete event；同时产生明显 read1 back-action 和约 −4-turn JS1/JS2 post shift。

**当前状态**：`R5C_SADDLE_CROSSED_NO_COMPLETE_EVENT` / alignment=`ALIGNED`

**结论边界**：关闭 reduced quantizer 的 bias/K/L point tuning；不能把 saddle crossing 当作 event。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/topology/publication/TOPOLOGY_4e1d8a8345/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/topology/publication/TOPOLOGY_4e1d8a8345/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/topology/publication/TOPOLOGY_4e1d8a8345/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/analysis/R5C_REPORT.md](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/analysis/R5C_REPORT.md)

---

## Native paper-QB：direct SL compatibility

**实验 ID**：`test/exploration/bvm-sfq-receiver-native-qb-20260822`

**做了什么**：用 canonical SL galvanic 直接驱动 frozen native paper-QB，记录 BJs/BJL1/BJL2 与 BVM source/storage guards。

**关键结果**：read1 在 QB core 中有明显 state-selective nonlinear activity，但 JS1/JS2 post-state 各约 −3 turns，source/storage guard 失败；BJL2 无 complete event。

**当前状态**：`BACK_ACTION_FAILURE` / alignment=`ALIGNED`

**结论边界**：direct SL native-QB point 是 back-action failure；不能因 activity 强就称 local pass。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-native-qb-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-native-qb-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-native-qb-20260822/topology/publication/TOPOLOGY_599236eda7/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-native-qb-20260822/topology/publication/TOPOLOGY_599236eda7/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-native-qb-20260822/topology/publication/TOPOLOGY_599236eda7/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-native-qb-20260822/analysis/NATIVE_QB_REPORT.md](../test/exploration/bvm-sfq-receiver-native-qb-20260822/analysis/NATIVE_QB_REPORT.md)

---

## R6-A：isolated native-QB transfer

**实验 ID**：`test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822`

**做了什么**：将 canonical SL 改接 weak mutual transformer isolation，再进入冻结 native paper-QB，保持 QB 内部 topology/参数。

**关键结果**：相对 direct SL，canonical source/storage guard 恢复，read1 QB activity 仍明显高于 read0/control，说明 isolation feasibility PASS；BJL2 仍仅约 0.0016 turn，无 local pass。

**当前状态**：`ISOLATION_PRESERVED_STATE_SELECTIVE_QB_ACTIVITY` / alignment=`ALIGNED`

**结论边界**：这是 isolation-preserved state-selective activity，不是 BJL2 quantization。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/topology/publication/TOPOLOGY_076c3ccc98/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/topology/publication/TOPOLOGY_076c3ccc98/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/topology/publication/TOPOLOGY_076c3ccc98/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/analysis/R6A_REPORT.md](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/analysis/R6A_REPORT.md)

---

## R6-B：secondary winding-ratio transfer

**实验 ID**：`test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822`

**做了什么**：冻结 native QB，只把 R6-A 的 secondary 改为 L_PRI=.20 pH、L_SEC=1.0 pH、K=.707 单点，检查 drive gain 与 reflected loading。

**关键结果**：read1 secondary/Lin current 和 BJs/BJL1 activity 增强，source isolation 保持；但 BJL2 最大段几乎不变（约 .0015846→.0015880 turn），没有 output quantization。

**当前状态**：`DRIVE_GAIN_WITH_ISOLATION_PRESERVED` / alignment=`ALIGNED`

**结论边界**：关闭 transformer 参数优化；瓶颈更像 front-stage absorption/loop load-line，而非单纯 secondary amplitude。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/topology/publication/TOPOLOGY_0bba1f61c1/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/topology/publication/TOPOLOGY_0bba1f61c1/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/topology/publication/TOPOLOGY_0bba1f61c1/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/analysis/R6B_REPORT.md](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/analysis/R6B_REPORT.md)

---

## R7-A：native-QB L1 routing

**实验 ID**：`test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823`

**做了什么**：回到 R6-B baseline，只将 native QB L1 从 3.91 pH 降到 2.50 pH，比较 front-stage→L2/BJL2 routing。

**关键结果**：G_L2 约提升 25.9%、G_BJL2 约提升 26.2%，read0 selectivity/source guard 保持；但 BJL2 最大段仍约 .001886 turn，且 settled BJL2 current 反而下降。

**当前状态**：`ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED` / alignment=`ALIGNED`

**结论边界**：建立 routing gain，不是 threshold gain、complete event 或 SFQ delivery。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/topology/publication/TOPOLOGY_b2e3690473/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/topology/publication/TOPOLOGY_b2e3690473/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/topology/publication/TOPOLOGY_b2e3690473/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/analysis/R7A_REPORT.md](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/analysis/R7A_REPORT.md)

---

## R8：BJL2 output-class adjustment

**实验 ID**：`test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823`

**做了什么**：保持 R7-A，只将 BJL2 AREA 1.89→.70，实际同时改变 Ic/C/RN/R0 与 damping/load-line。

**关键结果**：read1 phase/area activity 约增加 36%，但仍在 10^-3-turn 区间；BJL2 current excursion下降，read0 相对增幅更大，没有 threshold-like jump 或 complete event。

**当前状态**：`OUTPUT_CLASS_CHANGE_WITHOUT_MEANINGFUL_BJL2_GAIN` / alignment=`ALIGNED`

**结论边界**：停止 BJL2 AREA sweep；不能把该点解释成纯 Ic reduction failure。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/topology/publication/TOPOLOGY_e9e3fdb426/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/topology/publication/TOPOLOGY_e9e3fdb426/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/topology/publication/TOPOLOGY_e9e3fdb426/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/analysis/R8_REPORT.md](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/analysis/R8_REPORT.md)

---

## R9-A：native-QB L2 routing

**实验 ID**：`test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823`

**做了什么**：恢复 R7-A output class，将 L2 3.91→2.50 pH，测 node3→node4/BJL2 routing 与 static bias redistribution。

**关键结果**：L2/BJL2 control-subtracted routing 再次提高（read0 也近似 co-amplify），source guard 保持；BJL2 仍约 2×10^-3 turn，未进入 quantization。

**当前状态**：`ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED` / alignment=`ALIGNED`

**结论边界**：关闭 passive L1/L2 tuning 分支，不能由 routing gain 推断 nonlinear amplification。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/topology/publication/TOPOLOGY_f2413fa505/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/topology/publication/TOPOLOGY_f2413fa505/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/topology/publication/TOPOLOGY_f2413fa505/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/analysis/R9A_REPORT.md](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/analysis/R9A_REPORT.md)

---

## R10-A：local BJL2 bias routing

**实验 ID**：`test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823`

**做了什么**：在 node4 加有限阻抗、独立 bias feed，不把它直接作为 BJL2 parallel damping shunt。

**关键结果**：local bias 造成四 case 级别的 8–14-turn activity、free-running 和 source disturbance，未形成 bounded one-shot；主 verdict 为 BACK_ACTION_OR_NONSELECTIVE_FAILURE。

**当前状态**：`BACK_ACTION_OR_NONSELECTIVE_FAILURE` / alignment=`ALIGNED`

**结论边界**：只关闭当前 local-feed point，不否定所有 bias-routing，但不再继续该 sweep。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/topology/publication/TOPOLOGY_6776d3562e/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/topology/publication/TOPOLOGY_6776d3562e/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/topology/publication/TOPOLOGY_6776d3562e/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/analysis/R10A_REPORT.md](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/analysis/R10A_REPORT.md)

---

## R11-A：canonical BVM → standard JTL direct

**实验 ID**：`test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823`

**做了什么**：先用标准 SFQ positive control 验证两-cell JTL，再将 canonical BVM SL galvanic 接到同一冻结 JTL chain。

**关键结果**：positive control 通过；canonical read1 对第一颗 JTL JJ 最大单调 excursion 仅约 .151 turn，未触发第一 stage，主 verdict NO_JTL_TRIGGER；read0/controls 无 event。

**当前状态**：`NO_JTL_TRIGGER` / alignment=`ALIGNED`

**结论边界**：仅否定当前 direct-galvanic BVM→standard JTL point，不否定有 conditioner 的 JTL route。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/topology/publication/TOPOLOGY_c69c14b0ad/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/topology/publication/TOPOLOGY_c69c14b0ad/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/topology/publication/TOPOLOGY_c69c14b0ad/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/analysis/R11A_REPORT.md](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/analysis/R11A_REPORT.md)

---

## R12-A：historical DCSFQ_BVM re-audit

**实验 ID**：`test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823`

**做了什么**：先用 0/68.4/300 µA controlled bump 重审 frozen DCSFQ_BVM，再以 canonical BVM SL 接 converter 与两-cell JTL。

**关键结果**：Phase A 证明 300 µA controlled point 可使 B3 产生约 1.03-turn bounded local event，而 68.4 µA 无 event；canonical read1 B3 仅约 .0365 turn，未量化也未驱动 JTL。

**当前状态**：`DCSFQ_BVM_NO_TRIGGER` / alignment=`ALIGNED`

**结论边界**：converter mechanism 本身成立，但 canonical source 到 backend 的 amplitude/time-scale 不匹配；不恢复旧参数 sweep。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/topology/publication/TOPOLOGY_b2733b8e3c/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/topology/publication/TOPOLOGY_b2733b8e3c/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/topology/publication/TOPOLOGY_b2733b8e3c/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/analysis/R12A_REPORT.md](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/analysis/R12A_REPORT.md)

---

## R13-A：temporal conditioning requirements

**实验 ID**：`test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823`

**做了什么**：把 R12 actual input 做 raw replay，并分别测试原始、单极性整流、20 ps hold、整流+hold 四种 ideal transform。

**关键结果**：四种 replay 都未产生 selective DCSFQ B3 exactly-one；最终 verdict TEMPORAL_CONDITIONING_INSUFFICIENT，说明无 amplitude gain 的理想 conditioning 仍不够。

**当前状态**：`TEMPORAL_CONDITIONING_INSUFFICIENT` / alignment=`ALIGNED`

**结论边界**：这是 requirements/counterfactual 结果，不是 physical conditioner implementation，也不支持参数 sweep。

**推荐先看**：
- 【关键对比图】 [test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-vs-c1-vs-c2-vs-c3.html](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-vs-c1-vs-c2-vs-c3.html)
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-replay/comparison.html](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-replay/comparison.html)
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c1-rectify/comparison.html](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c1-rectify/comparison.html)
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c2-hold20/comparison.html](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c2-hold20/comparison.html)
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c3-rectify-hold20/comparison.html](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c3-rectify-hold20/comparison.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/topology/publication/DCSFQ_REPLAY_CONDITIONER/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/topology/publication/DCSFQ_REPLAY_CONDITIONER/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/topology/publication/DCSFQ_REPLAY_CONDITIONER/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/analysis/R13A_REPORT.md](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/analysis/R13A_REPORT.md)

---

## R14-A：passive interstage scale precheck

**实验 ID**：`test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823`

**做了什么**：只读比较 R1a passive secondary 的 5.56 µA 量级与 frozen DCSFQ 的 68.4/110/300 µA reference，并审计 R_SEC_LOAD termination。

**关键结果**：PRECHECK_NO_GO：optimistic loaded DCSFQ input 约 9.77 µA，3 ps sanity 也约 19.1 µA，远低于已知 68.4 µA no-event 与 300 µA positive point；缺失功能是 active/regenerative interstage energy transfer。

**当前状态**：`PRECHECK_NO_GO` / alignment=`NO_WAVEFORM_VISUALIZATION_REQUIRED`

**结论边界**：没有运行 JoSIM；不把 passive transformer/termination scale 解释成 active gain。

**推荐先看**：

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/topology/publication/TOPOLOGY_d1f5096eb9/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/topology/publication/TOPOLOGY_d1f5096eb9/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/topology/publication/TOPOLOGY_d1f5096eb9/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/SUMMARY.md](../test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/SUMMARY.md)

---

## R15-A：AFQ-3 active interstage precheck

**实验 ID**：`test/exploration/bvm-sfq-receiver-r15a-afq3-20260823`

**做了什么**：对 AFQ-3 nominal three-winding mutual topology 做 netlist closure、jjmit 参数、稳定性、discrimination 与 output-scale precheck。

**关键结果**：PRECHECK_NO_GO：L_Q/L_F/L_CTL mutual matrix determinant 为 −.62、最小 eigenvalue 为负，拓扑 constitutive matrix 无效；没有运行可解释的 physics point。

**当前状态**：`PRECHECK_NO_GO` / alignment=`NO_WAVEFORM_VISUALIZATION_REQUIRED`

**结论边界**：只否定该 invalid magnetic formulation，不是 active-stage physics failure，也没有 DCSFQ/JTL 结果。

**推荐先看**：

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/topology/publication/TOPOLOGY_9a2c21177c/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/topology/publication/TOPOLOGY_9a2c21177c/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/topology/publication/TOPOLOGY_9a2c21177c/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/SUMMARY.md](../test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/SUMMARY.md)

---

## R15-B：split-winding active interstage

**实验 ID**：`test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823`

**做了什么**：用 two-core/split-winding 修正 mutual matrix，保留 B_DET 并加入 J_SET/J_Q/J_OUT active-state-compression path。

**关键结果**：B_DET read1 仍约 3.9-turn 强 activity，但 J_SET/J_Q/J_OUT 四 cases 几乎相同，DCSFQ I(L1) 仅约 .511 µA；主 verdict ACTIVE_STAGE_NO_TRIGGER，另有 bounded extra back-action。

**当前状态**：`ACTIVE_STAGE_NO_TRIGGER` / alignment=`ALIGNED`

**结论边界**：问题定位到 detector state 未进入 J_SET 判别变量；不说明 active gain family 普遍失败。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/topology/publication/TOPOLOGY_e9d593f012/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/topology/publication/TOPOLOGY_e9d593f012/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/topology/publication/TOPOLOGY_e9d593f012/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/SUMMARY.md](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/SUMMARY.md)

---

## R15-C：finite-impedance J_SET causal fixture

**实验 ID**：`test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823`

**做了什么**：移除 ideal 5.6 µA current clamp，使用有限阻抗 bias return，让 B_DET mutual waveform 可改变 J_SET branch current。

**关键结果**：CAUSAL_NEAR_THRESHOLD：read1 I(B_SET) 约 2.10–9.13 µA、read0 约 4.89–6.28 µA，read1 最大 J_SET segment 约 .2244 turn；因果 modulation 成立但未完成 event。

**当前状态**：`CAUSAL_NEAR_THRESHOLD` / alignment=`ALIGNED`

**结论边界**：建立 detector→J_SET causal transfer，不建立 one-shot；没有接 J_Q/J_OUT/DCSFQ。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/topology/publication/TOPOLOGY_6161c7c30f/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/topology/publication/TOPOLOGY_6161c7c30f/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/topology/publication/TOPOLOGY_6161c7c30f/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/SUMMARY.md](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/SUMMARY.md)

---

## R15-D：J_SET → J_Q refractory compressor

**实验 ID**：`test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823`

**做了什么**：保留 R15-C J_SET，增加 split node、独立 J_Q bias、L_Q 和 R_Q refractory branch，检查 state compression。

**关键结果**：JQ_CAUSAL_NEAR_THRESHOLD：read1 selective J_SET/J_Q activity 与 L_Q transient depletion/recovery 可见，但 J_Q 没有完整 one-shot event；source guard 仍是 bounded extra back-action。

**当前状态**：`JQ_CAUSAL_NEAR_THRESHOLD` / alignment=`ALIGNED`

**结论边界**：不能把 depletion/recovery 单独称 refractory one-shot；暂停 R15-E 设计。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/topology/publication/TOPOLOGY_9334bd7f21/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/topology/publication/TOPOLOGY_9334bd7f21/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/topology/publication/TOPOLOGY_9334bd7f21/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/SUMMARY.md](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/SUMMARY.md)

---

## QB-Q0：scaled QB standalone 量化窗口

**实验 ID**：`test/exploration/qb-q0-standalone-current-quantized-event-20260824`

**做了什么**：用理想 current pulse 0/45/68.4/90 µA 驱动 frozen scaled QB，并以 paper-original QB 做历史参数对照。

**关键结果**：scaled：0=ZERO_EVENT，45=NO_COMPLETE_EVENT，68.4=EXACTLY_ONE（每 pulse 约 1.096 turn），90=MULTI_EVENT（约 2.006 turn）；paper 68.4/90 均无完整 BJL2 event。

**当前状态**：`ACCEPTED_STANDALONE_REFERENCE` / alignment=`ALIGNED`

**结论边界**：68.4 µA 只是 ideal standalone reference，不是 canonical BVM threshold 或 physical receiver requirement。

**推荐先看**：
- 【关键对比图】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-comparison.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-comparison.html)
- 【单工况/结果图】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-68p4uA.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-68p4uA.html)
- 【单工况/结果图】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-90uA.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-90uA.html)
- 【单工况/结果图】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-45uA.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-45uA.html)
- 【零输入对照】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-0uA.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-0uA.html)
- 【历史参考】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/paper-reference-comparison.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/paper-reference-comparison.html)
- 【历史参考】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/68p4-paper-reference.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/68p4-paper-reference.html)
- 【历史参考】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/90-paper-reference.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/90-paper-reference.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/connectivity-debug.svg)

**正式报告**：[test/exploration/qb-q0-standalone-current-quantized-event-20260824/analysis/QB_Q0_REPORT.md](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/analysis/QB_Q0_REPORT.md)

---

## QB-Q1：physical BVM → frozen scaled QB

**实验 ID**：`test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824`

**做了什么**：把 canonical BVM 直接接入 Q0 frozen scaled QB，运行 logical1/read、logical0/read 和两个 READ=0 controls。

**关键结果**：read1 QB activity 强于 read0/control，但 direct coupling 造成 JS1/JS2 约 −3-turn post drift，主 verdict QB_SOURCE_BACKACTION_FAILURE；BJL2 仍 subthreshold。

**当前状态**：`QB_SOURCE_BACKACTION_FAILURE` / alignment=`ALIGNED`

**结论边界**：直接 physical coupling 失败，不能用 source-isolated replay 替代真实 BVM back-action。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/plots/alignment-overview.html](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/topology/publication/BVM_TO_SCALED_QB/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/topology/publication/BVM_TO_SCALED_QB/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/topology/publication/BVM_TO_SCALED_QB/connectivity-debug.svg)

**正式报告**：[test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/SUMMARY.md](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/SUMMARY.md)

---

## QB-Q2A：source-decoupled waveform replay

**实验 ID**：`test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824`

**做了什么**：冻结 scaled QB，用 Q0 positive control、Q1 loaded waveform 和 canonical no-receiver read1/read0 waveform 做 ideal replay。

**关键结果**：Q0 68.4 µA replay exactly-one；canonical no-receiver read1 BJL2 约 .178 turn、read0 约 .031 turn，仍未量化，结论 QB_DYNAMIC_WINDOW_MISMATCH。

**当前状态**：`QB_DYNAMIC_WINDOW_MISMATCH` / alignment=`ALIGNED`

**结论边界**：完美 source isolation alone 也不够；不是 source impedance 唯一瓶颈。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/plots/alignment-overview.html](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/publication/SCALED_QB_REPLAY/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/publication/SCALED_QB_REPLAY/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/publication/SCALED_QB_REPLAY/connectivity-debug.svg)

**正式报告**：[test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/SUMMARY.md](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/SUMMARY.md)

---

## QB-Q2B：central-bias bracket

**实验 ID**：`test/exploration/qb-q2b-central-bias-bracketing-20260824`

**做了什么**：冻结 canonical source-isolated replay，只测试 central IBIAS=30/35/40 µA 对 BJs→BJL1/BJL2 的影响。

**关键结果**：read1 BJL1 约 +.321/.339/−.415 turn，logical0 约 .059 turn；所有点无 complete BJL1/BJL2 event，controls bounded，BIAS_BRACKET_NO_BJL1_EVENT。

**当前状态**：`BIAS_BRACKET_NO_BJL1_EVENT` / alignment=`ALIGNED`

**结论边界**：停止 central-bias branch；不把 phase range 或 I/Ic 当作 event。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/qb-q2b-central-bias-bracketing-20260824/plots/alignment-overview.html](../test/exploration/qb-q2b-central-bias-bracketing-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/publication/SCALED_QB_REPLAY/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/publication/SCALED_QB_REPLAY/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/publication/SCALED_QB_REPLAY/connectivity-debug.svg)

**正式报告**：[test/exploration/qb-q2b-central-bias-bracketing-20260824/SUMMARY.md](../test/exploration/qb-q2b-central-bias-bracketing-20260824/SUMMARY.md)

---

## QB-Q2C：uniform junction-scale bracket

**实验 ID**：`test/exploration/qb-q2c-uniform-junction-scale-20260824`

**做了什么**：在 canonical source-isolated replay 下统一缩放 BJs/BJL1/BJL2 AREA 与 IBIAS，测试 s=.85/.70/.55。

**关键结果**：三个 scale 都没有建立 selective BJL1/BJL2 event，最终 UNIFORM_SCALE_NO_OUTPUT_EVENT；停止整体缩放，转向 paper-JSL load waveform。

**当前状态**：`UNIFORM_SCALE_NO_OUTPUT_EVENT` / alignment=`ALIGNED`

**结论边界**：不能从 uniform scaling 推断某一颗 JJ ratio 是唯一原因。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/qb-q2c-uniform-junction-scale-20260824/plots/alignment-overview.html](../test/exploration/qb-q2c-uniform-junction-scale-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/publication/SCALED_QB_REPLAY/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/publication/SCALED_QB_REPLAY/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/topology/publication/SCALED_QB_REPLAY/connectivity-debug.svg)

**正式报告**：[test/exploration/qb-q2c-uniform-junction-scale-20260824/SUMMARY.md](../test/exploration/qb-q2c-uniform-junction-scale-20260824/SUMMARY.md)

---

## 历史 JSL width bracket：12 ps W* baseline

**实验 ID**：`test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824`

**做了什么**：在旧 lineage 中比较 canonical BVM/12×JSL 的 READ plateau，并把 12 ps source waveform replay 到 frozen scaled QB。

**关键结果**：旧报告支持 12 ps source-side margin improvement，但 Phase C 仍为 subthreshold；其 logical0 source provenance 不是当前 canonical WL+SE logical0，因此仅作历史/同-read1 reference。

**当前状态**：`WIDTH_IMPROVES_QB_MARGIN_BUT_SUBTHRESHOLD` / alignment=`NO_WAVEFORM_VISUALIZATION_REQUIRED`

**结论边界**：不得用该旧 logical0 lineage 支撑新的 canonical logical0 discrimination claim；本轮新的 READ semantics audit 已提供修正 12 ps logical0 与 13/14/15 ps bracket。

**推荐先看**：
- 【历史参考】 [test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824/plots/9ps-vs-Wstar-qb-replay-comparison.html](../test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824/plots/9ps-vs-Wstar-qb-replay-comparison.html)
- 【历史参考】 [test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824/plots/9ps-vs-Wstar-qb-current-comparison.html](../test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824/plots/9ps-vs-Wstar-qb-current-comparison.html)
- 【历史参考】 [test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824/plots/sl-readout-current-comparison.html](../test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824/plots/sl-readout-current-comparison.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824/REPORT.md](../test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824/REPORT.md)

---

## PAPER-SL-L0：12×320 µA JSL external load

**实验 ID**：`test/exploration/paper-sl-l0-20260824`

**做了什么**：在 canonical SL path 加入 paper Figure 4/section 2.5 语义下的 12 个 AREA=3.2 non-switching JSL series external load。

**关键结果**：12 个 JSL 全部 non-switching；logical1 current/area/duration waveform 明显改变，logical0 仍很小，判定 PAPER_JSL_LOAD_VALID（external-series-load realization）。

**当前状态**：`PAPER_JSL_LOAD_VALID` / alignment=`ALIGNED`

**结论边界**：只验证 paper-shaped SL load waveform，不接 QB，也不说明 JSL load 一定改善量化。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/paper-sl-l0-20260824/plots/alignment-overview.html](../test/exploration/paper-sl-l0-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/paper-sl-l0-20260824/topology/publication/TOPOLOGY_345d48a6be/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/paper-sl-l0-20260824/topology/publication/TOPOLOGY_345d48a6be/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-l0-20260824/topology/publication/TOPOLOGY_345d48a6be/connectivity-debug.svg)

**正式报告**：[test/exploration/paper-sl-l0-20260824/REPORT.md](../test/exploration/paper-sl-l0-20260824/REPORT.md)

---

## PAPER-SL-Q1：paper-JSL waveform → frozen scaled QB

**实验 ID**：`test/exploration/paper-sl-q1-20260824`

**做了什么**：将 PAPER-SL-L0 logical1/logical0/controls 的实际 JSL current trajectory 原样 ideal replay 到 frozen scaled QB。

**关键结果**：read1 BJL1 约 .830、BJL2 约 .893 turn，read0 约 .019/.0066，controls≈0；read1 明显 near-threshold 但无 complete event，PAPER_JSL_QB_SUBTHRESHOLD。

**当前状态**：`PAPER_JSL_QB_SUBTHRESHOLD` / alignment=`ALIGNED`

**结论边界**：不能改写为 one-shot；Q0 68.4 µA 只作 positive control。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/comparison.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j1-logical1-read.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j1-logical1-read.html)
- 【负向对照】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j0-logical0-read.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j0-logical0-read.html)
- 【零输入对照】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j1-logical1-read0-control.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j1-logical1-read0-control.html)
- 【零输入对照】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j0-logical0-read0-control.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j0-logical0-read0-control.html)
- 【正向对照】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/q0-68p4u-positive-control.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/q0-68p4u-positive-control.html)
- 【源波形参考】 [test/exploration/paper-sl-q1-20260824/plots/paper-sl-l0-classic/logical1-read.html](../test/exploration/paper-sl-q1-20260824/plots/paper-sl-l0-classic/logical1-read.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/connectivity-debug.svg)

**正式报告**：[test/exploration/paper-sl-q1-20260824/analysis/REPORT.md](../test/exploration/paper-sl-q1-20260824/analysis/REPORT.md)

---

## PAPER-SL-Q2：paper-JSL local bias bracket

**实验 ID**：`test/exploration/paper-sl-q2-20260824`

**做了什么**：保持 PAPER-SL-Q1 waveform byte-identical，只比较 37.5/40 µA central QB bias。

**关键结果**：两点均保持 read1>read0、bounded 且无 complete BJL1/BJL2 event；40 µA 将 BJL2 推到约 .944 turn，但仍未闭合。

**当前状态**：`BIAS_BRANCH_SUBTHRESHOLD` / alignment=`ALIGNED`

**结论边界**：停止 bias-only bracket；不把 .944 turn 当 event，也不连接 physical BVM。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q2-20260824/plots/bias-37p5-vs-40-comparison.html](../test/exploration/paper-sl-q2-20260824/plots/bias-37p5-vs-40-comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q2-20260824/plots/37p5u/comparison.html](../test/exploration/paper-sl-q2-20260824/plots/37p5u/comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q2-20260824/plots/40u/comparison.html](../test/exploration/paper-sl-q2-20260824/plots/40u/comparison.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/connectivity-debug.svg)

**正式报告**：[test/exploration/paper-sl-q2-20260824/analysis/REPORT.md](../test/exploration/paper-sl-q2-20260824/analysis/REPORT.md)

---

## PAPER-SL-Q3-PRE：BJs→BJL1 routing audit

**实验 ID**：`test/exploration/paper-sl-q3-pre-20260824`

**做了什么**：只读对齐 Q0 68.4 µA、PAPER-SL-Q1 35 µA、Q2 40 µA 的 BJs/BJL1/BJL2 phase、current/KCL 和 timing。

**关键结果**：BJs→BJL1 更像 waveform/routing/timing-limited：Q0 的 local branch signed transfer 比 Q1/Q2 更有利；phase/area 与 KCL 均闭合。

**当前状态**：`Q3_PRE_ROUTING_MECHANISM_INFERENCE` / alignment=`NO_WAVEFORM_VISUALIZATION_REQUIRED`

**结论边界**：这是 mechanism inference，不是 BJL1 threshold 已被排除；未运行新 circuit。

**推荐先看**：

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/paper-sl-q3-pre-20260824/topology/publication/TOPOLOGY_ba0fe9d75d/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/paper-sl-q3-pre-20260824/topology/publication/TOPOLOGY_ba0fe9d75d/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q3-pre-20260824/topology/publication/TOPOLOGY_ba0fe9d75d/connectivity-debug.svg)

**正式报告**：[test/exploration/paper-sl-q3-pre-20260824/analysis/REPORT.md](../test/exploration/paper-sl-q3-pre-20260824/analysis/REPORT.md)

---

## PAPER-SL-Q3-PRE：L1 routing point selection

**实验 ID**：`test/exploration/q3-l1-routing-closure-20260824`

**做了什么**：基于 Q3-PRE routing audit 选择唯一 L1=4.50 pH point，并登记其与 Q2/Q4/Q5 的 factorial 关系。

**关键结果**：这是 analysis-only provenance checkpoint；结论是 L1 routing knob 值得 single-point execution，独立目录不产生新 waveform。

**当前状态**：`Q3_PRE_SINGLE_POINT_SELECTED` / alignment=`NO_WAVEFORM_VISUALIZATION_REQUIRED`

**结论边界**：正式物理结果归属于下一条 paper-sl-q3-l1-routing-closure execution。

**推荐先看**：

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/connectivity-debug.svg)

---

## PAPER-SL-Q3：L1=4.50 pH routing closure

**实验 ID**：`test/exploration/paper-sl-q3-l1-routing-closure-20260824`

**做了什么**：以 Q2 accepted 40 µA replay 为 baseline，只把 native QB L1 3.91→4.50 pH，测 node2 routing 与 BJL1/BJL2。

**关键结果**：F_local .218660→.224945、G_local .515185→.526585；BJL1 .815414→.821070，BJL2 .944323→.950537，read0/control zero-event，结论为 routing gain 但仍 subthreshold。

**当前状态**：`ROUTING_GAIN_WITH_BJL1_SUBTHRESHOLD` / alignment=`ALIGNED`

**结论边界**：L1 是 causal routing knob，不是 complete-event 或 nonlinear-gain closure；不连接 physical BVM/JSL/QB。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q3-l1-routing-closure-20260824/plots/alignment-overview.html](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/connectivity-debug.svg)

**正式报告**：[test/exploration/paper-sl-q3-l1-routing-closure-20260824/analysis/REPORT.md](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/analysis/REPORT.md)

---

## PAPER-SL-Q4：L2=4.50 pH placement comparator

**实验 ID**：`test/exploration/paper-sl-q4-l1-l2-placement-20260824`

**做了什么**：从 Q2 直接改 L2 3.91→4.50 pH，与 Q3 保持相同 L1+L2 总电感，区分 proximal 与 downstream placement effect。

**关键结果**：Q4 的 BJL2 response 可增强，但 BJL1 forward phase 与 node2 local routing 明显退化；BJL2 最大连续段约 .9654 turn，仍无 event，判定方向性 placement effect。

**当前状态**：`Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT` / alignment=`ALIGNED`

**结论边界**：不能要求 BJL1 complete slip 才解释 BJL2 activity；仍无 isolated QB event。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q4-l1-l2-placement-20260824/plots/alignment-overview.html](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/connectivity-debug.svg)

**正式报告**：[test/exploration/paper-sl-q4-l1-l2-placement-20260824/REPORT.md](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/REPORT.md)

---

## PAPER-SL-Q5：L1×L2 factorial completion

**实验 ID**：`test/exploration/paper-sl-q5-l1-l2-factorial-20260824`

**做了什么**：完成 Q2/Q3/Q4/Q5=(3.91,3.91)/(4.50,3.91)/(3.91,4.50)/(4.50,4.50) 的 2×2 factorial comparison。

**关键结果**：Q5 保留 Q4 downstream BJL2 gain并部分恢复 Q3 L1 routing，但 BJL2 最大段约 .9682 turn；interaction≈−.00344，无 complete event。

**当前状态**：`Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT` / alignment=`ALIGNED`

**结论边界**：停止 passive L1/L2 tuning；未建立正向 nonlinear BJL2 interaction。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/alignment-overview.html](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/connectivity-debug.svg)

**正式报告**：[test/exploration/paper-sl-q5-l1-l2-factorial-20260824/REPORT.md](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/REPORT.md)

---

## PAPER-SL-Q6：Q5 → standard JTL

**实验 ID**：`test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824`

**做了什么**：将 frozen Q5 near-event output 接入已验证的 two-cell standard JTL，和 Q5 standalone 做 matched comparison。

**关键结果**：JTL loading 使 Q5 trajectory collapse，四颗 JTL JJ 均无完整 propagated event，主 verdict NO_JTL_TRIGGER。

**当前状态**：`NO_JTL_TRIGGER` / alignment=`ALIGNED`

**结论边界**：不能把 coupled failure 归因于 isolated QB 本身，也不能称 JTL voltage peak 为 event。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q5-standalone-vs-q6-coupled.html](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q5-standalone-vs-q6-coupled.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q6-q5-to-two-cell-jtl/comparison.html](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q6-q5-to-two-cell-jtl/comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/alignment-overview.html](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/topology/publication/Q5_TO_STANDARD_JTL/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/topology/publication/Q5_TO_STANDARD_JTL/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/topology/publication/Q5_TO_STANDARD_JTL/connectivity-debug.svg)

**正式报告**：[test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/REPORT.md](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/REPORT.md)

---

## BVM READ semantics audit + JSL width bracket

**实验 ID**：`test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824`

**做了什么**：审计 logical1/logical0/READ=0 的正式语义，修正 canonical logical0，并把 12/13/14/15 ps 的实际 12-JSL source current 原样 replay 到 frozen scaled QB。

**关键结果**：READ audit PASS；修正后的 12 ps logical0 为 zero-event；ideal replay 首个 1/0/0 candidate 在 13 ps（BJL2≈1.016 turn），14/15 ps为已执行的 post-candidate observations。

**当前状态**：`IDEAL_REPLAY_SELECTIVE_ONE_SFQ_CANDIDATE` / alignment=`ALIGNED`

**结论边界**：这只是 source waveform→frozen QB 的 ideal replay candidate，不是 physical BVM→12JSL→QB，也不是 JTL/T1 delivery；旧 PAPER-SL logical0 lineage 的 canonical read0 claims 被降级。

**推荐先看**：
- 【关键对比图】 [test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/plots/qb-replay-width-comparison.html](../test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/plots/qb-replay-width-comparison.html)
- 【源波形参考】 [test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/plots/source-width-comparison.html](../test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/plots/source-width-comparison.html)
- 【关键对比图】 [test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/plots/bjl2-margin-vs-width.html](../test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/plots/bjl2-margin-vs-width.html)
- 【关键对比图】 [test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/plots/read-semantics-audit.html](../test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/plots/read-semantics-audit.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/REPORT.md](../test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/REPORT.md)

---

## Physical BVM→12×JSL→scaled QB：SFQ closure

**实验 ID**：`test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824`

**做了什么**：把 canonical BVM SL 通过 12 个 AREA=3.2 的串联 JSL 直接接到 frozen scaled QB，运行 13/14 ps 与 logical1/logical0/两个 READ=0 controls，并与已有 ideal replay 对比。

**关键结果**：PHYSICAL_BACKACTION_PREVENTS_CLOSURE：13/14 ps physical read1 的 BJL2 最大连续段仅约 −0.122 turn，read0/control 为零 complete event；I(L_SL) 未数量级塌缩，但 physical load-line 改变了 source voltage/current partition，ideal replay 的 1/0/0 candidate 未保留。

**当前状态**：`PHYSICAL_BACKACTION_PREVENTS_CLOSURE` / alignment=`ALIGNED`

**结论边界**：不能称 physical BVM→QB selective one-SFQ closure，也没有 T1/JTL evidence；该结果把下一问题限定为 physical QB source matching/load-line，而不是继续 width sweep。

**推荐先看**：
- 【关键对比图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/physical-width-comparison.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/physical-width-comparison.html)
- 【关键对比图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/13ps-matched-cases.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/13ps-matched-cases.html)
- 【关键对比图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/14ps-matched-cases.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/14ps-matched-cases.html)
- 【关键对比图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/physical-source-and-storage-guards.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/physical-source-and-storage-guards.html)
- 【单工况/结果图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/physical-jsl12-current-consistency.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/physical-jsl12-current-consistency.html)
- 【关键对比图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/physical-qb-routing-and-kcl.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/physical-qb-routing-and-kcl.html)
- 【单工况/结果图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/13ps-logical1_read.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/13ps-logical1_read.html)
- 【负向对照】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/13ps-logical0_read.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/13ps-logical0_read.html)
- 【零输入对照】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/13ps-logical1_no_read_control.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/13ps-logical1_no_read_control.html)
- 【零输入对照】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/13ps-logical0_no_read_control.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/13ps-logical0_no_read_control.html)
- 【单工况/结果图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/14ps-logical1_read.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/14ps-logical1_read.html)
- 【负向对照】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/14ps-logical0_read.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/14ps-logical0_read.html)
- 【零输入对照】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/14ps-logical1_no_read_control.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/14ps-logical1_no_read_control.html)
- 【零输入对照】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/14ps-logical0_no_read_control.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/cases/14ps-logical0_no_read_control.html)
- 【关键对比图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/13ps-ideal-vs-physical-qb.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/13ps-ideal-vs-physical-qb.html)
- 【关键对比图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/14ps-ideal-vs-physical-qb.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/14ps-ideal-vs-physical-qb.html)
- 【关键对比图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/physical-logical1-vs-logical0.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/physical-logical1-vs-logical0.html)
- 【关键对比图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/13ps-source-before-vs-after-qb-loading.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/13ps-source-before-vs-after-qb-loading.html)
- 【关键对比图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/14ps-source-before-vs-after-qb-loading.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/14ps-source-before-vs-after-qb-loading.html)
- 【单工况/结果图】 [test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/bjl2-phase-area-evidence.html](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/bjl2-phase-area-evidence.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/topology/publication/BVM_JSL12_SCALED_QB_PHYSICAL/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/topology/publication/BVM_JSL12_SCALED_QB_PHYSICAL/schematic-annotated.svg)
- 【网表连接调试图】 `connectivity-debug.svg（未生成）`

**正式报告**：[test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/REPORT.md](../test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/REPORT.md)

---

## QB load-boundary matrix：Q0 output boundary

**实验 ID**：`test/exploration/qb-load-boundary-matrix-20260824`

**做了什么**：保持同一 Q0 true-event source，比较 OPEN、10Ω、JTL-only、10Ω||JTL 四种 output boundary。

**关键结果**：OPEN≈3 events；10Ω exactly-one；JTL-only 与 10Ω||JTL 无 event；矩阵支持 MIXED_DYNAMIC_LOADING，load 在 crossing 前/中/后都改变 current partition。

**当前状态**：`MIXED_DYNAMIC_LOADING` / alignment=`ALIGNED`

**结论边界**：不冻结普适等效阻抗；Q5 boundary 仅作 secondary comparator。

**推荐先看**：
- 【关键对比图】 [test/exploration/qb-load-boundary-matrix-20260824/plots/q0-complete-boundary-comparison.html](../test/exploration/qb-load-boundary-matrix-20260824/plots/q0-complete-boundary-comparison.html)
- 【关键对比图】 [test/exploration/qb-load-boundary-matrix-20260824/plots/q5-open-vs-jtl-read1.html](../test/exploration/qb-load-boundary-matrix-20260824/plots/q5-open-vs-jtl-read1.html)
- 【单工况/结果图】 [test/exploration/qb-load-boundary-matrix-20260824/plots/alignment-overview.html](../test/exploration/qb-load-boundary-matrix-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/connectivity-debug.svg)

**真实 topology 变体**：
- `低 Ic QB → OPEN output boundary`：
  - 【论文级电路图】 [schematic.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_OPEN/schematic.svg)
  - 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_OPEN/schematic-annotated.svg)
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_OPEN/connectivity-debug.svg)
- `低 Ic QB → standard JTL direct`：
  - 【论文级电路图】 [schematic.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_JTL_ONLY/schematic.svg)
  - 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_JTL_ONLY/schematic-annotated.svg)
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_JTL_ONLY/connectivity-debug.svg)
- `低 Ic QB + 10Ω || standard JTL`：
  - 【论文级电路图】 [schematic.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_10OHM_PARALLEL_JTL/schematic.svg)
  - 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_10OHM_PARALLEL_JTL/schematic-annotated.svg)
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_10OHM_PARALLEL_JTL/connectivity-debug.svg)

**正式报告**：[test/exploration/qb-load-boundary-matrix-20260824/analysis/REPORT.md](../test/exploration/qb-load-boundary-matrix-20260824/analysis/REPORT.md)

---

## M1–M5：QB→JTL interface mechanism matrix

**实验 ID**：`test/exploration/parallel-qb-jtl-interface-mechanism-20260824`

**做了什么**：并列比较 ideal replay、series R/L、standard/scaled JTL 和 Q0/Q5 source boundary 对 QB local event 与 JTL transport 的影响。

**关键结果**：Q0+10Ω 保留 exactly-one，M3 series-10Ω 保留 local event但 JTL subthreshold；M1/Q0 replay 与 M5 transport 需按 strict/local 与 settled-well 分层，M5 历史 exactly-one 解释废止。

**当前状态**：`BOUNDED_INTERFACE_MATRIX` / alignment=`ALIGNED`

**结论边界**：这是 interface mechanism matrix，不是一个可直接实现的 receiver，也不授权参数优化。

**推荐先看**：
- 【关键对比图】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/interface-qb-phase-comparison.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/interface-qb-phase-comparison.html)
- 【关键对比图】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/interface-jtl-phase-comparison.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/interface-jtl-phase-comparison.html)
- 【单工况/结果图】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M1-ideal-replay.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M1-ideal-replay.html)
- 【单工况/结果图】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M3-rseries10.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M3-rseries10.html)
- 【历史参考】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M5-positive-control.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M5-positive-control.html)
- 【单工况/结果图】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/alignment-overview.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M3_SERIES10_JTL/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M3_SERIES10_JTL/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M3_SERIES10_JTL/connectivity-debug.svg)

**真实 topology 变体**：
- `Q0 recorded V(OUT) ideal replay → standard JTL`：
  - 【论文级电路图】 [schematic.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M1_IDEAL_REPLAY_JTL/schematic.svg)
  - 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M1_IDEAL_REPLAY_JTL/schematic-annotated.svg)
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M1_IDEAL_REPLAY_JTL/connectivity-debug.svg)
- `低 Ic QB → RISO=10Ω → standard JTL`：
  - 【论文级电路图】 [schematic.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M2_RISO10_JTL/schematic.svg)
  - 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M2_RISO10_JTL/schematic-annotated.svg)
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M2_RISO10_JTL/connectivity-debug.svg)
- `低 Ic QB → LISO=10pH → standard JTL`：
  - 【论文级电路图】 [schematic.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M4_LISO10P_JTL/schematic.svg)
  - 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M4_LISO10P_JTL/schematic-annotated.svg)
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M4_LISO10P_JTL/connectivity-debug.svg)
- `低 Ic QB → scaled JTL`：
  - 【论文级电路图】 [schematic.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M5_SCALED_JTL/schematic.svg)
  - 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M5_SCALED_JTL/schematic-annotated.svg)
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M5_SCALED_JTL/connectivity-debug.svg)

**正式报告**：[test/exploration/parallel-qb-jtl-interface-mechanism-20260824/analysis-v2/REPORT.md](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/analysis-v2/REPORT.md)

---

## JTL polarity replay：original vs reverse

**实验 ID**：`test/exploration/jtl-transport-gate-polarity-replay-20260824`

**做了什么**：从 accepted Q0 pulse-5 提取完整 V(OUT,t)，原极性/反极性 ideal replay 到同一 standard two-cell JTL。

**关键结果**：原极性在 strict local vector 上只保证第一颗 JJ，但 full-window/pre-post 呈四级约一井响应；反极性无 strict local event、无 one-well transport。

**当前状态**：`POLARITY_REPLAY_RECONCILED` / alignment=`ALIGNED`

**结论边界**：ideal replay 不是 physical QB→JTL 证据；strict local event 与 settled-well transport 必须分开。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/jtl-transport-gate-polarity-replay-20260824/plots/alignment-overview.html](../test/exploration/jtl-transport-gate-polarity-replay-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/jtl-transport-gate-polarity-replay-20260824/topology/publication/TOPOLOGY_0fca67e829/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/jtl-transport-gate-polarity-replay-20260824/topology/publication/TOPOLOGY_0fca67e829/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-polarity-replay-20260824/topology/publication/TOPOLOGY_0fca67e829/connectivity-debug.svg)

**正式报告**：[test/exploration/jtl-transport-gate-polarity-replay-20260824/analysis/REPORT.md](../test/exploration/jtl-transport-gate-polarity-replay-20260824/analysis/REPORT.md)

---

## JTL transport methodology：strict vs settled-well

**实验 ID**：`test/exploration/jtl-transport-gate-v1-methodology-20260824`

**做了什么**：统一 R11 positive、M1 ideal replay、M5-PC、pulse5 original/reverse 的 phase/area、pre/post well、onset 和 transport vector 口径。

**关键结果**：建立 fixture-level 方法学 reconciliation：R11/M1/pulse5 original 呈 provisional +1-well transport signature，M5 是 two-well，reverse 非 transport。

**当前状态**：`JTL_TRANSPORT_GATE_V1_RECONCILED` / alignment=`ALIGNED`

**结论边界**：这是方法学整理，不是 global metric freeze，也不改变 physical BVM/JTL compatibility。

**推荐先看**：
- 【正向对照】 [test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/r11-timestep-comparison.html](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/r11-timestep-comparison.html)
- 【单工况/结果图】 [test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-timestep-comparison.html](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-timestep-comparison.html)
- 【负向对照】 [test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-reverse-timestep-comparison.html](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-reverse-timestep-comparison.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/jtl-transport-gate-v1-methodology-20260824/topology/publication/STANDARD_JTL_2CELL/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/jtl-transport-gate-v1-methodology-20260824/topology/publication/STANDARD_JTL_2CELL/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-v1-methodology-20260824/topology/publication/STANDARD_JTL_2CELL/connectivity-debug.svg)

**正式报告**：[test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/analysis/REPORT.md](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/analysis/REPORT.md)

---

## JTL transport Gate V1：timestep ladder

**实验 ID**：`test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824`

**做了什么**：对 R11、pulse5 original、pulse5 reverse 做 0.025/0.0125/0.00625 ps ladder 与预注册 window robustness。

**关键结果**：三组 timestep classification 稳定；R11/reverse window checks 通过，但 pulse5 original post-window robustness 未完全通过，最终 STRICT_REPLAY_INCONCLUSIVE。

**当前状态**：`JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE` / alignment=`ALIGNED`

**结论边界**：不是 timestep 数值不稳定，而是 registered robustness Gate 未闭合；不改变 JTL 参数。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/plots/alignment-overview.html](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/topology/publication/TOPOLOGY_3a1af7987d/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/topology/publication/TOPOLOGY_3a1af7987d/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/topology/publication/TOPOLOGY_3a1af7987d/connectivity-debug.svg)

**正式报告**：[test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/analysis/REPORT.md](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/analysis/REPORT.md)

---

## JTL transport Gate V1：rerun evidence package

**实验 ID**：`test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun`

**做了什么**：对同一 numerical-freeze raw 做 successor/rerun 复核，保留完整 timestep、phase/area、pre/post 和 window-grid evidence。

**关键结果**：R11 与 pulse5 original 的 +1-well settled behavior 跨 timestep 保持，reverse 保持 non-transport；original robustness 条件仍未全通过，结论仍 INCONCLUSIVE。

**当前状态**：`JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE` / alignment=`ALIGNED`

**结论边界**：rerun 只加强 provenance/数值稳定性，不升级 Gate 为 PASS。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/alignment-overview.html](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/topology/publication/TOPOLOGY_8403837f5b/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/topology/publication/TOPOLOGY_8403837f5b/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/topology/publication/TOPOLOGY_8403837f5b/connectivity-debug.svg)

**正式报告**：[test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/analysis/REPORT.md](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/analysis/REPORT.md)

---

## QB→JTL load back-action causal audit

**实验 ID**：`test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824`

**做了什么**：用 Q0+10Ω、OPEN、JTL-only、10Ω||JTL、M3 series-10Ω→JTL 的既有 raw，按 pre-crossing/crossing/retrap 三个时间窗审计 node4 KCL 与 current partition。

**关键结果**：判定 MIXED_DYNAMIC_LOADING：direct/parallel JTL 在 barrier crossing 前已改 settled load-line，crossing 中继续分流；M3 保留 local BJL2 event但仍不能驱动 JTL。

**当前状态**：`MIXED_DYNAMIC_LOADING` / alignment=`ALIGNED`

**结论边界**：不能把负载作用压缩成单一静态阻抗，也不能把 M3 local event 称 downstream SFQ delivery。

**推荐先看**：
- 【关键对比图】 [test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/plots/backaction_compare.html](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/plots/backaction_compare.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/connectivity-debug.svg)

**真实 topology 变体**：
- `低 Ic QB → OPEN output boundary`：
  - 【论文级电路图】 [schematic.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_OPEN/schematic.svg)
  - 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_OPEN/schematic-annotated.svg)
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_OPEN/connectivity-debug.svg)
- `低 Ic QB → standard JTL direct`：
  - 【论文级电路图】 [schematic.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_JTL_ONLY/schematic.svg)
  - 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_JTL_ONLY/schematic-annotated.svg)
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_JTL_ONLY/connectivity-debug.svg)
- `低 Ic QB + 10Ω || standard JTL`：
  - 【论文级电路图】 [schematic.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_10OHM_PARALLEL_JTL/schematic.svg)
  - 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_10OHM_PARALLEL_JTL/schematic-annotated.svg)
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/publication/QB_Q0_10OHM_PARALLEL_JTL/connectivity-debug.svg)
- `低 Ic QB → series 10Ω → standard JTL`：
  - 【论文级电路图】 [schematic.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M3_SERIES10_JTL/schematic.svg)
  - 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M3_SERIES10_JTL/schematic-annotated.svg)
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/publication/QB_M3_SERIES10_JTL/connectivity-debug.svg)

**正式报告**：[test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/analysis/REPORT.md](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/analysis/REPORT.md)

---
