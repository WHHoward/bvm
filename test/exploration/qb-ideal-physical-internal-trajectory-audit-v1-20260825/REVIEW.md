# 数值与对抗性审查

- 审查时间：`2026-08-25T01:46:05+08:00`
- 审查对象：`QB_IDEAL_PHYSICAL_INTERNAL_TRAJECTORY_AUDIT_V1`
- 分析 HEAD：`6e9cbedefeae8e8771299a8624bef081146494eb`
- 审查原则：只检查已有 raw、netlist、source chain 和本轮 derived evidence；不修改 raw，不运行新的 JoSIM。

## 数值审查

| 检查项 | 状态 | 证据与边界 |
|---|---|---|
| 单位 | `PASS` | JoSIM raw `time` 按秒读取并转换为 ps；phase 只在相对轨迹/图中显式除以 `2π`；电压面积使用同一 JJ 的 `V` 与实际 CSV 时间并除以 `Phi0`。 |
| 窗口 | `PASS` | 13 ps 使用 `[80,94)`、`[94,130)`、`[130,140)`、`[140,170)` ps；Q0 使用 preregistered 六脉冲窗口。 |
| 符号/端点 | `PASS` | 12 个 case 的 source-vs-Lin 与 node2/node3/node4 KCL 在固定符号下通过；输入相反符号没有一个 window 通过。 |
| KCL 容差 | `PASS` | 使用全部方程 terms 的绝对值构造 `1e-12 A + 1e-6 Σ|terms|`；全体 expected Gate 的最大归一化 residual 不超过约 `0.368`，且没有连续三点越界。 |
| raw 健康 | `PASS` | 注册 raw、C13 snapshots 均存在、有限、严格递增；原始 13 ps 网格为 `0.0125 ps`，Q0 为 `0.1 ps`。 |
| 独立复算 | `PASS` | `analysis/independent-raw-recheck.json` 通过直接 raw-only 计算路径复算 KCL、BJL2 phase/area、PRE 与 first-divergence 子集，未读取本目录 derived 文件。 |
| 控制可视化覆盖 | `PASS` | `plots/matched-controls.html` 集中覆盖 C13/D12/E8 的 logical0 与 READ=0 controls；保持关键图数量，不展开全量单工况页面。 |
| SHA-256 artifact inventory | `PASS` | `analysis/artifact-inventory.json` 覆盖 154 个非自身排除的 raw/provenance、dependency closure、analysis/report、plot/metadata 和 validation 路径；inventory 自身以明确 self-exemption 防止循环。 |
| 收敛/敏感性 | `UNKNOWN` | 本任务没有 timestep refinement、参数 sweep 或初始条件敏感性；不得把单一 frozen timestep 升格为 convergence Gate。 |

## 关键数值交叉核对

- C13 logical1 BJL2 largest active segment：`+1.0160289 turn`，同一段 voltage area：`+1.0160368 Phi0`。
- D12 logical1 BJL2 largest active segment：`−0.1221278 turn`，同一段 voltage area：`−0.1221310 Phi0`；该值只作 descriptive raw observation，因为 input-deck provenance mismatch。
- E8 logical1 BJL2 largest active segment：`−0.1249962 turn`，同一段 voltage area：`−0.1250061 Phi0`。
- Q0 scaled 45 µA：六个 pulse window 的 BJL2 local candidate counts 为 `[0,0,0,0,0,0]`；68.4 µA 为 `[1,1,1,1,1,1]`。这是两个冻结 standalone reference，不是 universal threshold。

## 对抗性审查

### 已执行探针

1. **Wrong-branch / sign probe**：读取 `analysis/orientation-audit.json`，expected source/KCL 组合全部通过，相反 input sign 全部失败；没有发现“错误方向也能通过”的假象。
2. **Weak-oracle probe**：独立复算不再调用 primary 的 KCL、PRE 或 divergence helper，而是重新从 raw 取列并直接重建 equations、bound、phase/area 和 first sample；仍与 primary 子集一致。
3. **Stale-artifact probe**：分析脚本只声明读取五组 raw、source snapshot、deck/include、manifest 和 metric spec，不读取 `REPORT.md`、旧 JSON 或 HTML 来生成结果；D12 的历史 deck SHA mismatch 被显式保留。
4. **Duplicate-column probe**：四个 C13 role 的 index `14/18` (`I(B_LD1)`) 和 `15/51` (`I(B_LD12)`) 均逐点相等，但历史 builder 的实际选择仍被冻结为 index 14；没有把 index 51 偷换进 replay。
5. **Boundary probe**：两组 primary pair 均没有 PRE first divergence；C13↔E8 的最早连续三点 crossing 为 `95.0125 ps`，在 ACTIVE 内且不位于窗口左边界 `94 ps`；`input_port`、`bjs_trajectory`、`node2` 在同一采样点，已按 `0.0125 ps` 预注册规则标为 `TIE`，没有强行排序。
6. **Overclaim probe**：报告把 C13 final-JSL source semantics 标为 `INCONCLUSIVE`，把 D12 标为 `DESCRIPTIVE_RAW_OBSERVATION / PROVENANCE_INCONCLUSIVE`，并将总 disposition 固定为 `MECHANISM_AUDIT_INCONCLUSIVE`。
7. **Inventory coverage probe**：`analysis/artifact-inventory.json` 的 `all_present=true`，列出 154 条实际路径，覆盖分析脚本、全部 derived JSON/CSV、报告/manifest、10 张 HTML 与 metadata、case deck/include closure 及 validation 文件；自身只在 `self_exempt` 中登记。
8. **Fresh-checkout probe**：逐条对 inventory 中 154 条路径执行 `git ls-files --error-unmatch`、`git show HEAD:<path>` 非空和 checkout 内容 SHA-256 对比，结果为 `PASS`；冻结 `build/josim-cli` 已显式进入 checkpoint。

### Residual uncertainty

- 独立复算与 primary 仍共享同一个基础 CSV loader、`mask`、MAD 和梯形积分 primitive；它已经绕过主派生文件和主要分析组合逻辑，但不是另一套 CSV parser/数值库实现。因此 `PASS` 只表示当前 raw-only 子集未发现实现分歧，不是独立 solver 复现。
- C13 exact source chain 的“可复现”与“物理语义正确”仍是两个命题；辅助 index-14 probe 的 semantic limitation 未被任何图或 phase/area 数字消除。
- first divergence 是最早可观测 feature-level 分叉，不是唯一根因；source/load-line、端口 operating point 和后续 node partition 仍可能共同耦合；本轮最早层级是并列耦合族，不是唯一 input-port 根因。
- HTML plot 只作诊断显示；没有使用图形、导数样本或 `I/Ic` 作为 SFQ event count 或 Gate。
- fresh-checkout 检查已完成且为 `PASS`；该检查不运行 JoSIM，只确认 tracked tree 与 inventory 的路径、非空性和 SHA-256 一致。

## 审查结论

当前 derived evidence 没有发现会把结果直接推翻的单位、端点、KCL 或 stale-artifact 缺陷；但 D12 run-input provenance 和 C13 final-JSL semantic boundary 足以使最终审计保持 `MECHANISM_AUDIT_INCONCLUSIVE`。不授权本轮修改参数、重新 replay index 51、磁耦合、JTL/T1 或 sweep。
