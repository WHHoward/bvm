# RESULT_BRIEF — JM2 passive capture / current replay

本轮按预先限定的协议只完成 4 个新物理运行：`SINGLE_PASSIVE`、`ARRAY_PASSIVE`、`REPLAY_SINGLE`、`REPLAY_ARRAY`。solver 为记录的 `build/josim-cli` `v2.7.2837d13`；四个 raw 均为 1999 行，未覆盖历史 raw。

窗口中的差分约定为 `ARRAY − SINGLE` 或 `REPLAY_ARRAY − REPLAY_SINGLE`；电流显示为 uA，电压为 mV。`P(...)` 原始量是 rad，下面的 turns 仅指 `rad/(2*pi)` 的连续相位换算，不是 SFQ 计数。

## 六个问题

1. **SINGLE_PASSIVE 与 ARRAY_PASSIVE 的 source waveform 差异有多大？**

   **Observed / Derived:** FINAL READ（110–121 ps）中，`I(B_JSL8)` 的最大绝对差为 **32.005 uA**，RMS 差为 **14.725 uA**；`I(B_JSL1)` 数值相同。对应的 SL/COMMON_SL 边界电压最大绝对差为 **0.9231 mV**。因此 shared-SL array 的被动 source waveform 与 single 并不相同。

2. **ARRAY_PASSIVE 是否仍有 shared-SL current redistribution？**

   **Observed:** 有。FINAL READ 中 BVM1 的 `I(L_SL)` 为 **−4.627 到 89.539 uA**，BVM2–4 均为 **−10.211 到 14.847 uA**；BVM2–4 的最终读控制源均为 0，而 BVM1 是目标读。`SUM_LSL` 与 `I(B_JSL1)` 的差的最大绝对 KCL 残差为 **1.29×10⁻⁵ uA**，符合记录的 `Σ I(L_SL) − I(B_JSL1)=0` 方向。这里只报告重分配，不把它升级为耦合机制证明。

3. **REPLAY_SINGLE 的 QB/JTL response 是什么？**

   **Observed:** 全 0–200 ps 中，QBIN 电压为 **−0.3094 到 0.7014 mV**；BJ1/BJ2 的连续相位分别为 **0–8.2227 rad**、**0–7.3412 rad**；JTL1/JTL6 的 B01 相位分别为 **0–7.1506 rad**、**0–7.3537 rad**；10 Ω 端电流为 **−12.108 到 124.554 uA**。这些是 QB/JTL 波形活动和连续相位轨迹描述，不是事件或 SFQ 数量。

4. **REPLAY_ARRAY 的 QB/JTL response 是什么？**

   **Observed:** 全 0–200 ps 中，QBIN 电压为 **−0.1983 到 0.5371 mV**；BJ1/BJ2 连续相位为 **0–7.8868 rad**、**0–7.2323 rad**；JTL1/JTL6 B01 相位为 **0–7.1159 rad**、**0–7.3538 rad**；10 Ω 端电流为 **−12.113 到 124.566 uA**。FINAL READ 中 BJ1、BJ2 的端点相位位移分别为 **4.7941 rad（0.7630 turns）**、**3.4099 rad（0.5427 turns）**；不将其称为 SFQ count。

5. **切断 QB→BVM back-action 后，passive-array waveform 是否仍不足以驱动 QB？**

   **Bounded Inference:** 在本次 ideal-current PWL counterfactual 中，答案是 **没有显示为“不足”**：`REPLAY_ARRAY` 仍产生 QBIN 电压、BJ1/BJ2 相位/电压、JTL1/JTL6 轨迹和端接电流活动。因此，passive-array waveform 本身不能被判定为无法驱动 QB。

   **Unknown / boundary:** 这只证明固定输入下的 bounded waveform activity，不证明 exactly-one event、成功的 SFQ delivery、门功能或硬件行为；没有进行 timestep convergence 或参数 sensitivity。

6. **与已有 direct ARRAY failure 对照后，更支持哪一种解释？**

   **Contextual comparison / Inference:** 最符合本轮证据的表述是 **both contribute to the observed trajectory difference**：passive shared-SL coupling 已经显著改变输入 source，而把该输入改成无反馈的理想电流后，ARRAY 仍能产生 receiver/JTL activity；另一方面，`REPLAY_ARRAY` 与旧 direct ARRAY 的 QBIN、BJ1/BJ2、JTL1 轨迹仍有明显差异，说明 finite-source / QB back-action 是闭环轨迹差异的合理贡献因素。这里不能把“back-action 必然是根因”或“coupling alone 足以解释 direct failure”升级为已证实机制。

## 可视化与证据

- [READ_WRITE_CONTROLS.html](plots/READ_WRITE_CONTROLS.html)：读写控制、目标 BVM 与 BVM2–4 quiet/control 历史，含协议窗口。
- [PASSIVE_SOURCE_COMPARE.html](plots/PASSIVE_SOURCE_COMPARE.html)：JSL1/JSL8、ARRAY−SINGLE 差分、SL/COMMON_SL 电压。
- [ARRAY_CURRENT_BALANCE.html](plots/ARRAY_CURRENT_BALANCE.html)：四个 `L_SL` 分支、SUM_LSL、JSL1/JSL8。
- [QB_REPLAY_COMPARE.html](plots/QB_REPLAY_COMPARE.html)：QBIN、LIN、BJ1/BJ2 phase/voltage。
- [JTL_REPLAY_COMPARE.html](plots/JTL_REPLAY_COMPARE.html)：JTL1/JTL6、输出和 R_TERM。

机器可核验记录：[analysis/REVIEW.md](analysis/REVIEW.md)、[analysis/independent_check.json](analysis/independent_check.json)、[analysis/viz_qa.json](analysis/viz_qa.json)、[analysis/metrics.json](analysis/metrics.json)。

本结果是 Exploration evidence pack，不改变既有 scientific authority，也不重新解释历史实验。
