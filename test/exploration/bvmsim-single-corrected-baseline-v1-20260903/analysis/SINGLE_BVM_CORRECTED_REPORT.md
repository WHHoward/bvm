# Corrected historical BVMSim single-BVM → original QB baseline

> 本报告只覆盖 historical `BVMSim/bvm_cell.cir` 的 single-BVM 2×2；它不是 canonical BVM 兼容性结论，也不是 timestep 或参数裕度结论。

## 1. What changed

- 新建 task-local corrected decks：`S0-R-CORRECTED`、`S1-R-CORRECTED`，以及带完整 JTL 探针的新 `S0-J-CORRECTED-RERUN`、`S1-J-CORRECTED-RERUN`。
- WRITE 修正为 `WL+BL`：S0 为 `-100/-100 µA`，S1 为 `+100/+100 µA`，时间为 50–61 ps。
- READ 修正为两个逻辑态完全相同的 `WL+SE`：`WL=+100 µA`、`SE=+100 µA`、`BL=0`，时间为 70–81 ps。
- corrected deck 显式 include `circuits/models/jjmit.cir`，避免 BVM/terminal JJ 使用 default model。QB 仍是原始 `BVMSim/BQ.cir`。

## 2. What did not change

- BVM、original QB、六级 historical JTL、280 µA/JTL、10 Ω load、`.tran 0.1p 200p` 和 solver 均未改变。
- terminal sensing line 保持 11 个串联 load JJ + `BVMout`，共 12 个 JJ。
- `BVMSim/BQ.cir`、`BVMSim/bvm_cell.cir`、`BVMSim/library_josim/jtl2.cir` 和旧 single raw 均未覆盖。
- 初次 corrected JTL raw 因缺少 JTL P/V 探针而标记 `OBSERVABILITY_INCOMPLETE`；本报告使用其后的 probe-only rerun。

## 3. OBSERVED stimulus correction

四个 corrected raw 的实际 plateau 检查均为零误差：WRITE 只改变 S0/S1 的 WL/BL 极性；READ 的三条控制在 S0/S1 间完全相同。独立控制图见：

- `plots/runs/S0-R-CORRECTED/BVM_STIMULUS_AND_STATE.html`
- `plots/runs/S1-R-CORRECTED/BVM_STIMULUS_AND_STATE.html`
- `plots/runs/S0-J-CORRECTED-RERUN/BVM_STIMULUS_AND_STATE.html`
- `plots/runs/S1-J-CORRECTED-RERUN/BVM_STIMULUS_AND_STATE.html`

旧 single fixture 的 `S1-R` 在 READ 期间是 SE-only，且 log 有 `Missing model: JJMIT` / `Using default model`；它只作为 `ARTIFACT_INVALID` 历史对照。旧 raw 与 corrected raw 的因果差异不能拆分为“READ 修复贡献”和“model 修复贡献”，因为本轮两者同时修复。

## 4. OBSERVED model closure

四个实际使用的 corrected raw 均通过基本 raw QA；log 未出现 model fallback；deck 有 intended `jjmit` include；direct run 有 0 个 JTL instance，JTL rerun 有 6 个 JTL instance，terminal JJ 计数均为 12。输出 raw 的存储网格为请求的 0.1 ps 为主，但每个 JoSIM raw 保留一个 0.2 ps 间隔；所有积分均使用实际存储时间，不做插值。

## 5. OBSERVED S0

- direct 10 Ω：S0 `BJ2` RESPONSE 的 phase/area 为 `0.000359` / `0.000369` turns，未见约 1 turn 的 READ-associated QB burst。
- JTL load：S0 `QBin` READ voltage p2p 为 `0.230042` mV；`BJ2` RESPONSE 的 phase/area 为 `0.000617` / `0.000631` turns；JTL1–JTL6 的 B02 burst-total area 为 `-0.000069, 0.000004, -0.000001, -0.000000, 0.000000, 0.000000` turns，均接近零。
- bounded no-output control assessment：`FUNCTIONAL_PASS`。这不是对任意 future load 的普遍无输出证明。

## 6. OBSERVED S1

- direct 10 Ω：S1 `BJ2` RESPONSE 的 phase/area 为 `1.999600` / `1.999590` turns，显示 direct load 下约 2-turn response；这一路径没有预注册的单量子 count boundary，因此不把它直接判为 count PASS。
- JTL load：S1 `QBin` READ voltage p2p 为 `0.563671` mV；`BJ2` RESPONSE 的 phase/area 为 `0.999369` / `0.999355` turns，residual `0.000014` turns。
- JTL1–JTL6 的 B02 RESPONSE phase/area 为：`1.000070 / 1.000071 / 0.999996 / 0.999995 / 1.000001 / 1.000001 / 1.000000 / 1.000000 / 1.000000 / 1.000000 / 1.000000 / 1.000000` turns；极性为 `+/+/+/+/+/+`。
- bounded one-burst assessment：`FUNCTIONAL_PASS`。计数依据是同一 JJ 的 burst-total phase/area 与下游 B02 的一致性，不是 whole-window phase 单独计数。

## 7. OBSERVED direct vs JTL load

- S0 在 direct 与 JTL 下都没有约 1-turn BJ2 burst；JTL rerun 补足了 direct run 初次没有的六级 B01/B02 P/V 观测。
- S1 的 QB 响应明显受负载影响：direct 10 Ω 的 BJ2 RESPONSE 约 2 turns，而六级 JTL load 的 BJ2/B02 burst-total 约 1 turn。这个结果是本固定 fixture 的 load-sensitive observation，不足以单独说明某一物理机制或普适设计规则。
- JTL B02 每一级都保留约 1 的 phase/area burst-total；每一级的细碎 ringing/严格 monotonic segmentation 不被升级成额外 SFQ 数。

## 8. INFERENCE

在本轮固定的 historical BVMSim source、original QB、六级 historical JTL 和 10 Ω termination 下，修正后的 single-BVM 确实让 WL+SE READ 条件可被直接核验；S0/S1 的 QBin/QB 响应可区分；JTL load 下可得到 bounded 的 0→0 和 1→1 burst-total functional evidence。因此 corrected fixture 可以回答“这个 historical single BVM → original QB → JTL fixture 在该固定点是否工作”，而旧 single fixture 不能承担这个结论。

## 9. UNKNOWN

- 本轮没有拆分 READ protocol 与 model closure 两个修复各自的因果贡献。
- 本轮没有证明 canonical BVM 兼容性、single-BVM 的普遍行为、参数/偏置裕度、timestep convergence、T1 行为或论文机制身份。
- `P(...)` 的局部 phase turns 不是自动的 SFQ count；严格 clean-separated event count 本轮没有使用未预注册的 task-local tolerance 强行生成。
- JTL 的 0/1 bounded assessment 使用报告中明确列出的 task-local descriptive bands；这些 bands 不是全局 metric freeze，也没有被用于声称 timestep convergence。
- direct 10 Ω 的约 2-turn response 说明负载敏感，但本轮没有把它解释为错误机制或做参数优化。

## 10. Reasonable next options

1. 由用户审阅本报告和四张独立 stimulus 图，决定是否接受这组 single-BVM historical baseline。
2. 如确有必要，另行授权只拆分一个因素的 control experiment，以分别评估 READ 语义与 model closure 的影响。
3. 如需推进科学路线，再另行授权 canonical BVM 或数值鲁棒性工作；本轮没有自动执行。

## 当前状态

`AWAITING_USER_REVIEW`；`user_reviewed=false`；`next_step_authorized=false`；`automatic_next_experiment=false`。
