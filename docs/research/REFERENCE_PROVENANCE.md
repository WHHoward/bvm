# Reference Provenance（W5B）— 参数来源索引

> 状态：W5B 起点（2026-08-12）。本文件是 **documentation/provenance 记录**，不升级任何 scientific state，不构成物理结论或基线冻结。
> 标签：`[PUBLISHED]` / `[AUTHOR_PROVIDED]` / `[DERIVED]` / `[INFERRED]` / `[DESIGNED]` / `[TUNED]` / `[UNKNOWN]`
> 纪律：`[INFERRED]` / `[DESIGNED]` / `[TUNED]` 参数不得在后续总结中逐渐写成 paper parameter；任何参数缺失时使用 `R0 / partial-R1` 并显式列出 UNKNOWN。

## 1. Reproduction Levels（R0–R3）

| 级别 | 含义 |
|---|---|
| R0 | Topology reconstruction（仅拓扑结构） |
| R1 | Published nominal-parameter reconstruction（论文名义参数） |
| R2 | Behavioral reproduction（行为级复现） |
| R3 | Independent full reproduction（独立完整复现：预声明 model closure / testbench / parameter provenance / numerical settings / observation tolerance 下满足全部 reproduction criteria） |

## 2. 当前已知来源状态（2026-08-12 快照，待逐项审计补全）

> 依据：docs/HANDOVER.md 审计修订版（2026-08-09）与 M4–M6 验收证据。标记为待审计的条目不得用作论文参数。

| 对象 | 关键参数 | 来源标签 | 备注 |
|---|---|---|---|
| BVM cell | topology（JM1、WL、R0 读线等） | `[PUBLISHED]`（部分） | 网表 `circuits/bvm/bvm_cell.cir`；部分细节待与论文对照 |
| BVM JM1 | Ic / shunt / area | `[INFERRED]`–`[UNKNOWN]` | 待审计：JM1 shunt 是否为论文原值未确认 |
| BVM 读电流 | 100 µA 近似非破坏 / 120 µA R0 擦除 | `[MEASURED-重算]` → 归 `[DERIVED]` | 来自 P2 人工重算（2026-08-09 审计后）；非冻结基线 |
| published modified-QB | topology / Ic / L / R / bias / load | `[UNKNOWN]` | 论文公开参数不足（审计结论）；待 W5A 检索与 W5C 作者询问 |
| original BQ | 参数 | `[UNKNOWN]`–`[PARTIAL]` | 待与文献对照 |
| project BQ v2/v4 | L0/Ic/RJ 等 | `[DERIVED]` / `[TUNED]`（项目设计） | `circuits/qb/bq_cell_v4.cir`；v4 的修改参数是项目设计值，不是论文参数 |
| canonical DCSFQ | B1/B2/B3 area、IB1/IB2、L1–L6 | `[PUBLISHED]`（ColdFlux 库 v3.0 网表） | `circuits/standard/DCSFQ.cir` 注明来源 IARPA SuperTools/ColdFlux |
| DCSFQ_BVM | 缩放参数（225→80 µA 等） | `[DESIGNED]` / `[TUNED]`（项目设计） | `circuits/interface/DCSFQ_BVM.cir`；不是论文参数 |
| JJ model | jjmit（rtype/vg/cap/r0/rn/icrit） | `[PUBLISHED]`（MIT-LL SFQ 工艺） | `circuits/models/jjmit.cir`；JoSIM 兼容形式 |
| JoSIM 版本 | v2.7.2837d13（build/josim-cli） | `[DERIVED]`（本仓库构建） | M6-002 使用，sha256 48655cb31d6297ba… |

## 3. 待办（W5B 推进项，不升级 scientific state）

- [ ] W5A 检索记录：database / query / date / closest prior art（完成前禁止 first / no prior work / literature blank confirmed）；
- [ ] BVM 论文原参数与 `bvm_cell.cir` 逐参数对照，标记每参数来源；
- [ ] published modified-QB 参数收集（论文 + 补充材料）；不足则标 `R0 / partial-R1`；
- [ ] 作者询问（W5C，需用户授权、time-box）：modified-QB exact netlist / QB parameters / JM1 shunt / exact `.model` / source-load testbench / bias-timestep；收到信息标 `[AUTHOR_PROVIDED]`，不等同 `[PUBLISHED]`；
- [ ] original BQ 参数与 canonical BQ 对照；
- [ ] 每条网表参数行最终落到本表（或引用本表的 netlist 注释）。

## 4. 引用与更新规则

- 本文件是 W5B 的索引；新参数证据先落这里，再进网表/实验；
- 更新时保留历史行（追加 `(superseded by …)`），不覆盖旧标签；
- 任何标记变化（如 `[UNKNOWN]` → `[AUTHOR_PROVIDED]`）需注明日期与来源文件；
- 本文件不裁决物理结论；裁决只发生在 M9（METRIC_SPEC_V2）、M11（基线）与 INTERFACE_GATE_V1 的正式 Gate。
