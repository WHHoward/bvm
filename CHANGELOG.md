# JoSIM 项目变更日志

> **规则**: 只追加不删除。每次变更记录：日期、做了什么、为什么、影响是什么。

---

## 2026-08-17 — Workflow-maintenance C01 rework disposition

### 做了什么

- 审计 `JH-20260817-WORKFLOW-MAINT-005` 的 no-JoSIM 维护交付；保留 MAINT-004 的 scope 冲突失败证据
- 独立确认 snapshot request byte-identity 与 evidence-bundle 逐项 path/SHA-256/bytes 重算仍未满足

### 影响

- C01 为 `REWORK_REQUIRED`，未接受该协议维护实现；不改变任何 S0/S1/S2 或科学结论
- 等待用户决定满足 byte-identical snapshot 约束的非自引用 v1 表示；此期间不启动科学任务

---

## 2026-08-13 — M11 metadata errata 与 characterization preflight

### 做了什么

- 为 M11A/M11B 的历史非单调 protocol timestamps 写入 hash-bound errata，并让 handoff validator 强制新链路的时间顺序
- 以 M11A C03 澄清 six-suite regression count metadata；新增 BVM source characterization preflight

### 影响

- M11A/M11B baseline 保持 ACCEPTED，不重跑 JoSIM、不重建 baseline
- active phase 转为 Reference / Source / Receiver Characterization；尚未签发或运行新科学任务

---

## 2026-08-13 — M11 双子门与 W5B 当前知识状态接受

### 做了什么

- 接受 `JH-20260813-M11A-001` C02 和 `JH-20260813-M11B-003` C01
- 将七对象的 structured reconstruction/provenance matrix 设为 W5B 唯一 canonical registry；旧 provenance 文档降为指针

### 影响

- M4–M11 的计量与双基线阶段完成；M11B 的 PASS 仅代表当前 knowledge state 完整、诚实且可追溯
- 不建立物理/接口 Gate，不验证候选路线，不提升 published reproduction；W5A/W5C 仍开放

---

## 2026-08-13 — M9 规格冻结与 M10 历史指标重建接受

### 做了什么

- 接受 `METRIC_SPEC_V2.md` v2.0.0 的测量/报告语义冻结；全局数值容差保持 `UNFROZEN`
- 接受 `JH-20260813-M10-004`：保留旧数据和叙述，新增 BASELINE/P0/P2/BQ v4 的 V2 endpoint-arithmetic JSON、central correction table 与 superseded banners

### 影响

- M4–M10 已完成；M10 的接受限于历史 endpoint arithmetic/provenance，不构成任何物理 Gate 或路线结论
- M11 仍是候选路线重启前的下一道基线门

---

## 2026-08-12 — M8 预注册有界时间步收敛接受

### 做了什么

- 运行前注册 loaded canonical JTL 的六次匹配控制运行、0.1/0.05/0.025 ps 阶梯、比较窗口、观测量、任务局部带宽和最大深度停止规则
- 保留原 A01 六份 raw；交付物模式与 verify-log 自引用哈希缺陷使其为 `REWORK_REQUIRED`，不删除或重跑
- `JH-20260812-M8-002` 对冻结 raw 独立重算并完成 FROZEN 机械闭环；两个相邻 refinement 比较均在预注册带宽内，Codex C01 审计接受

### 影响

- M8 完成：接受范围仅为该 loaded canonical JTL 校准 fixture 的有界数值收敛
- 未冻结全局计量容差，未建立 SFQ/下游接收/系统 Gate 或路线结论；M9–M11 与 candidate tuning 继续等待用户授权

---

## 2026-08-12 — M7 计量单元、canonical JTL 与历史回归接受

### 做了什么

- 完成并接受 `M7-LITE-001`：M7A 合成数学 ground truth、M7B 直接同 JJ V/P 的 canonical JTL 校准运行、M7C DCSFQ 控制重放与 BQ v4 六周期平台常量回归
- A01 数值通过但因缺少独立 analysis 和完整范围证据被保留并要求 rework；A02 以只读 A01 raw 哈希补齐 analysis、范围证据和 Copilot 复审后由 Codex 接受
- 新增 18 项 M7 回归；M4–M7 合计 83 项测试独立复跑通过

### 影响

- M7 在任务表中完成，测量管线具备独立数学、canonical transient 与固定历史 raw 的校准/回归护栏
- JTL 残差仍未冻结容差；周期平台、活动簇和局部相位均不构成物理事件或接口 Gate。M8–M11 继续阻断候选路线判定，未签发下一任务

---

## 2026-08-11 — M5 窗口与零输入控制接受

### 做了什么

- 以 `M5-LITE-PILOT-001` 实现并接受 pre/activity/post 半开窗口、完整窗口统计、显式 ±方向、匹配零输入控制和严格阈值的连续活动聚类
- A01 经 Copilot 发现 activity 窗统计与不足样本校验缺口后保留为历史；A02 补齐 activity 0/1 样本拒绝、signal/control 双命名空间统计和 409 样本回归
- Copilot 两轮独立复审；Codex 独立复跑 M5 29 项、M4 15 项，并直接从原始 0/300 µA CSV 重算校正相位量

### 影响

- M5 在任务表中完成；`scripts/sfq_metrics_v2.py` 可用于可重复的窗口化算术与活动描述
- 活动簇、约一圈相位重放和阈值 0.3 rad 仍不构成物理事件、系统 Gate 或冻结容差；M6–M11 继续阻断候选路线判定

---

## 2026-08-11 — M4 相位计量基础接受

### 做了什么

- 以干净合同 `JH-20260811-M4-003` 重新交付 `scripts/sfq_metrics_v2.py`，明确执行 `raw phase rad / (2π)` 的圈数换算
- 将阈值结果命名为活动样本数和活动区间，禁止把导数过阈值样本写成事件数
- Codex 独立复跑 15 项回归测试，核对 request → ACK → receipt → audit 的 SHA-256 链和范围；审计 `C01` 为 `ACCEPTED`

### 影响

- M4 在任务表中完成；旧 M4-001 仍是拒绝的历史记录
- 本次只建立指标实现基础；M5 的窗口/零输入控制、M6 的同 JJ 电压面积交叉校验以及 M7–M11 未完成，任何物理 Gate 或 SFQ 事件结论仍不得据此产生

---

## 2026-08-11 — 工作流完整性加固与 M4-001 stand-in 审查

### 做了什么

- Codex 审查 `JH-20260809-M4-001/standin/S01` 并写入 `REJECTED` review：已签 request 被 `--force` 重签，且其 `PROVISIONAL` 状态下发生 ACK/执行；A01 receipt 另披露未授权删除调试日志
- 移除 `sign-request --force`；未确认或非 `CONFIRMED` stand-in 现在使 `verify-task` 非零退出；review 绑定 record、request 和签名文件，record 的最新 action target 必须匹配实际哈希
- 为 checkin 增加 `PROVISIONAL / INVALID / VERIFIED DELIVERED` 区分与单元测试；新增 stand-in review 模板
- 在 `WORKFLOW.md` 固化核心审阅、工程审阅、机械检查三层模型路由；执行 worktree 在 ACK 后冻结，禁止再从 master 同步文件

### 影响

- M4-001 的候选实现和日志保留为历史证据，但不能合并、上推 todo/HANDOVER 或作为 M4 完成；后续用新的 superseding request 在干净 worktree 重做
- stand-in 只能准备 DRAFT 和记录；不能重签既有 ISSUED request，也不能让未确认合同进入 ACK/执行

---

## 2026-08-09 — Codex 不可用时的 Claude stand-in 代理机制（⚠️ stand-in 代理，待 Codex 审查）

> **标注**：Codex 额度暂时耗尽，用户在 2026-08-09 明确授权 Claude 临时代理本条目与相关签发动作（stand-in 会话 S01）。本条目及该会话的产物为 **PROVISIONAL**，须由 Codex 在 `research/tasks/<id>/standin/<Sxx>/review.yaml` 中审查确认后才生效。协议见 `research/WORKFLOW.md` §15。

### 做了什么

- 新增 `standin-record` / `standin-review` 两类协议文档：JSON Schema（`research/schemas/standin-record.schema.json`、`standin-review.schema.json`）、模板（`josim-handoff/assets/standin-record.yaml`）
- `handoff.py` 注册两类 schema，`verify-task` 对未审查的 stand-in record 输出 `STAND-IN PROVISIONAL` 警告；`DRAFT` 任务携带 stand-in record 报错
- `research/WORKFLOW.md` 新增 §15（stand-in 不变量、可代理/不可代理、审查转正流程）；`research/CLAUDE_EXECUTOR.md` 新增 §1.1；`josim-handoff` skill 增加对应规则
- 试点合同 `JH-20260809-M4-001` 已签发为 `ISSUED`（2026-08-09 19:01-19:03，用户侧完成：重采 baseline 至 HEAD `384d753`、DRAFT→ISSUED、生成 `request.sha256`）；stand-in 机制落地后 Claude 按 §15 补写 `standin/S01/record.yaml` 标注该签发为 PROVISIONAL，并因机制文件属于 M4 read_paths 而重采 manifest 后重签（`sign-request --force`，旧签名 349ff637 留痕）

### 为什么

- Codex 暂时不可用时，研究工作不应停顿；同时“临时可用”不能变成“绕过审计”——所有代理动作必须标注、可校验，且最终由 Codex 审查后才生效

### 影响

- Codex 恢复后需审查 stand-in S01（见任务目录 `standin/`）并写入 review verdict；审查前 M4 合同为 PROVISIONAL，执行与验收照常进行，但 todo/HANDOVER 不因 stand-in 签发而更新
- 四维结果与既有 schema 语义不变；stand-in 只覆盖 Codex 的机械动作，不取代审计

## 2026-08-09 — Codex–Claude 可审计任务交接层

### 做了什么

- 新增 `josim-handoff` 项目 skill，并通过 Claude 兼容目录共享同一规范源
- 新增 `research/WORKFLOW.md` 与 `research/CLAUDE_EXECUTOR.md`，明确用户、Codex、Claude Code 和机械校验器的权限与文件所有权
- 新增 task request、execution ACK、execution receipt、audit verdict 四类 JSON Schema、YAML 模板和哈希/范围校验工具
- 将交接规则接入 `AGENTS.md`、`CLAUDE.md`、实验/证据/任务/总结 skills、HANDOVER 和项目结构记忆
- 创建 Phase −1 M4 的试点任务草案；协调层提交并重绑定基线前保持不可执行，不虚构 Claude ACK 或实验结果

### 为什么

- 将“做完代码”“产物可用”“物理假设通过”和“审计接受”分成不同状态，避免负面实验、无效数据和执行故障混为一谈
- 用 SHA-256 封存的 request、逐级哈希、路径白名单和不可覆盖证据，让 Codex 的计划/审计与 Claude 的具体执行可以复核和重放

### 影响

- 后续委派任务遵循 request → ACK → receipt → audit；只有接受的 audit 才能上推 todo、HANDOVER 或论文主张
- Claude Code 获得短入口和明确停止条件；Codex 若参与核心执行必须声明 co-executor，并安排独立复审
- 现有历史实验目录与原始 CSV 未移动、未覆盖；新控制层只引用其路径和哈希

## 2026-08-09 — 项目 skills 标准化与研究证据护栏

### 做了什么

- 将旧 `.claude/skills/*.md` 迁移为 `.agents/skills/<name>/SKILL.md` 标准包，并用 Claude 目录链接共享同一 canonical source
- 重写 `josim-viz`、任务管理、项目总结和工作流路由，移除过时优先级、失效插件依赖、自动删除和旧 v1 指标调用
- 新增 `josim-experiment` 与 `josim-evidence-audit`，提供不可覆盖实验协议、manifest/分析模板和相位—电压面积证据合同
- 新增仓库级 `AGENTS.md`，同步 `CLAUDE.md`、skill 记忆、SFQ 物理约定、脚本索引和最终实验目录入口
- 发现 `josim-plot2.py` 的 `grid/stacked/square` 在 `-j 2pi` 下只改标签未缩放；新增 M12，并在修复前由 `josim-viz` 限制布局

### 为什么

- 旧 skills 仍会调用 raw rad 误标 SFQ 的脚本，并可能把过阈值采样数、归一化图轴或内部结活动升级成物理事件
- 旧总结 skill 在普通归档任务中包含过宽删除规则；旧 todo 优先级也与当前 Phase −1 冲突
- Codex 的仓库级标准发现目录是 `.agents/skills`，单一规范源可避免 Claude/Codex 双份正文漂移

### 影响

- 实验执行、波形可视化和物理 Gate 判定被明确分离
- 新代理会自动获得 raw phase rad、同 JJ 双证据、不可覆盖原始数据和三态判定护栏
- 在 M4–M11 完成前，旧 `run_exp.sh`/`sfq_metrics.py` 被明确限制为历史追溯，不能形成新物理结论

## 2026-08-09 — 相位单位审计：撤销旧冻结口径并重开接口路线

### 做了什么

- 由 JoSIM `src/Output.cpp`、`docs/tech_disc.md`、绘图脚本和官方 JTL 示例交叉确认：`P()` 输出是 raw phase rad，不是 \(\phi/(2\pi)\)
- 复核 `scripts/sfq_metrics.py`：相位派生量缺少 `/2π`；`fast_events` 是过阈值采样间隔数，不是物理事件数
- 从已提交 CSV 独立重算 BVM→BQ 基线、BVM P2、DCSFQ Phase 0 和 BQ v4
- 重写 `docs/guide/project-guide.md` 与 `docs/HANDOVER.md`，更新 todo/summary，并给旧 BASELINE、P0/P2、论文证据链、深讲和 Phase 1 计划增加 superseded 警告
- 生成自包含离线报告及 A4 PDF 阅读版；PDF 由当前 Markdown 经 Pandoc HTML5/MathML 和 Edge 无头打印生成，保留可搜索中文与排版公式

### 主要纠正

- BVM JM1 约 `±5.9 rad = ±0.94` 个 JJ 相位圈；用它直接证明“±6 多涡旋”的旧证据链失效，完整环 fluxoid 数仍待计算
- 基线 BQ BJs `6.2727 rad = 0.9983` 圈，不是 6.27 个量子；BJL1/BJL2 未完成整圈，而基线网表未接 JTL，因而只能判定输出量化未证明、传播未测
- 标准 DCSFQ 300 µA 减零输入控制后，B1/B2/B3 约为 `−1/+1/+1` 圈，不是 7–8 次爆发
- BQ v4 的六周期测试在 110–150 µA 已测点时，下游 JTL 相位平台约每输入 +1 圈，与约 1:1 传播相容；“输出级死亡/整个 BQ 拓扑排除”被反证，但完整 SFQ Gate 尚未通过

### 影响

- Step 0 冻结基线、旧 `fast_events` Gate、45–55 µA 目标和原 Phase 1 计划失效
- 项目转入 Phase −1：先修复指标，加入控制/事件窗/同 JJ 电压积分/时间步收敛，冻结经校准的数值容差，再重建版本化基线
- BQ v4 与 DCSFQ_BVM 并列为待公平复核的候选，暂不宣称任一路线成功
- 电流峰值、FWHM、负载扫描、0.285 分流、电压峰值和字节级重复性不受相位缩放影响

---

## 2026-08-06 — Phase 0 完成：接口规格实测 + 边沿触发确认 + 设计参数修订

### 做了什么
- **P0.1 DCSFQ 行为测试**（11 组运行 + 有界 300µA 扩展）: 0-150µA 全不触发（阈值 ∈ (150,300]µA），**边沿触发确认**（sustained 148ps 零累积），300µA 为多滑移爆发；B2 是输入响应结
- **P0.0 BVM 负载扫描**（5 种负载）: 接口规格实测——I_peak 43.9-97.8µA、Zth≈39.6-41.2Ω（原 ~15Ω 假设废止）、FWHM 6.8-11.2ps、R0 SE 边沿振铃 ±40µA、存储不扰动；**68.4µA 定位为"8-JJ 链+BQ 输入"加载值**（纯链 79.55µA）
- **P0.2 DCSFQ_BVM 元件创建 + 分流标定**: 起点参数 (B1/B2=0.8, IB1=100µA)，增量耦合 **0.285** < 0.3 警示线
- **P0.3 确定性**: 5/5 md5 双算法一致 + JSON 交叉核对
- **决策门 G1-G5 判定**（test/final/interface/P0_LOG.md）; spec 修订 2: 阈值目标 25→45-55µA、输入网络待调、极性待 V4 验证

### 为什么
- Phase 0 回答三个设计前置问题: 现有元件阈值在哪（>150µA）、触发性质（边沿）、BVM 真实输出规格（实测取代假设）——全部实测驱动，不靠推算

### 影响
- 方案一（最小缩放）确认，无需门控; Phase 1（V1-V4b）需含输入网络 L2/L3 调整实验与极性验证
- 全部数据/日志在 test/final/interface/（P0_LOG.md + P0_LOG_P00-P03），实现经双审查（spec+quality）

---

## 2026-08-06 — DCSFQ_BVM 新元件设计批准（H7 主路线启动）

### 做了什么
- **设计新元件 DCSFQ_BVM**（H7 主攻方向）：基于 ColdFlux DCSFQ 骨架，输入级 B1/B2 从 225µA 缩放到 80µA（触发阈值 ≈25µA），RB/LRB 按公式缩放（≈8.6Ω / 4.85-5.35pH），IB1≈100µA；**输出级 B3=250µA + L6 冻结不动**（JTL 兼容）
- 设计文档提交: `docs/superpowers/specs/2026-08-06-dcsfq-bvm-cell-design.md`（commit 8faa4f3）
- 用户决策: D1 **新元件**（非修改 BQ）、D2 **方案一最小缩放**（无门控）、D3 输出级冻结
- **保留后备**: H6（修 BQ）、方案二（+读使能门控）、方案三（双端口时钟式）

### 为什么
- BQ 8 轮失败根因三件套（裸结欠阻尼 / 通量泵 / 输出级推不动 JTL）在 DCSFQ 骨架上全部结构性解决：每结有 RB+LRB 阻尼、B3=250µA 天然匹配 JTL、输入是阈值判别器
- 决策门 P0.1：现有 DCSFQ 行为测试（边沿 vs 电平触发）先于任何参数投入，不无限迭代

### 影响
- 主攻方向从"修 BQ"（H6）转为"新元件"（H7/DCSFQ_BVM）；H6 降为后备
- Phase 0（P0.1-P0.3）→ 验证链 V1-V4b；最终 Gate: 读1 → 恰好 1 SFQ，读0 → 0
- todo/memory/CHANGELOG 已同步

---

## 2026-08-06 — 基于冻结证据链校准 H6/H7 接口建议

### 做了什么
- 在 `memory/GuidanceFromGpt.md` 追加第十节，基于 `HANDOVER.md`、冻结基线与 8 轮证据链重新评估 H6/H7 路线
- 明确 H6 不应直接复制 250µA JTL 的阻尼数值；为 BJs area=0.5 给出同标度起点 `RB≈13.7Ω`、`LRB≈8.25pH`
- 将 H6 拆分为输入级单翻转 Gate（H6-A）和输出/JTL Gate（H6-B），并明确 H7 与 BVM 多涡旋验证的后续顺序

### 为什么
- BQ v4 已独立验证失败，下一轮实验必须可归因，避免同时调整多个参数或把周期脉冲累积误判为单 SFQ 事件
- 当前 `IBias` 不直接等价于 BJs 预偏置，H6 需要显式测量 BJs 的实际工作点

### 影响
- H6 仍是最低成本验证，但成为受控阻尼/偏置实验，而非单一参数复制
- 若 H6-A 失败，应直接转向 H7 门控过阻尼比较器，停止 BQ 参数的无限迭代

---

## 2026-08-06 — Step 3 决策 D：论文证据链完成 + 交接文档

### 做了什么
- **创建论文证据链** `docs/paper/bvm-bq-interface-evidence-chain.md`：8 轮实验总表 + 逐轮详情 + 假设排除链表（H1-H5 排除，H6-H8 未测）+ 7 条冻结物理结论 + 论文章节映射 + 数据索引
- **修正 EXPERIMENT_LOG 实验 5 标签**：K 变压器原误标"待进行"，实际已完成，结果从 memory 补回
- **Step 4 重新编号为 H6-H10**（H6=输入级 RF 阻尼，最低成本验证）
- **创建交接文档** `docs/HANDOVER.md`（本文件是给新会话的完整交接说明）

### 为什么
- 用户在 v4 独立验证失败后选择 **D: 先整理论文证据链**——8 轮实验已构成完整"BQ 直接耦合路线不可行"证据链
- 论文叙事必须重构：原"双路线比较"（低IC vs 变压器）因双路线都失败而不可行 → "系统性排除 + 根因物理 + 负向设计准则"

### 影响
- 论文定位：方法学论文（问题表征 + 失效机制根因 + 设计约束），符合 ARS 评估
- 下一步按成本排序：**H6**（BQ 输入级 RF 阻尼 + BJs 预偏置，1 次验证）→ 滑移机制诊断（V(BJs) 波形）→ H7（DC-SFQ）
- 交接文档确保新会话可零上下文接手

---

## 2026-08-06 — Step 1 BQ v4 独立验证：Gate 未通过

### 做了什么
- **S1.1 创建 `circuits/qb/bq_cell_v4.cir`**：IC 顺序修正 (BJs 50µA < BJL2 70µA < BJL1 90µA), RJ1→56Ω, RJ2→36Ω, L0→2.5pH
- **S1.2 偏置稳定性** ✅：BJs=0.0, 0 fast_events, Vpk=68µV（无自发翻转）
- **S1.3 SFQ 注入 (1.5mV+3Ω)** ❌：BJs +12.57 SFQ/脉冲（过驱动欠阻尼环振），JTL 收到 0
- **S1.4 电流扫参 70-150µA** ❌：BJs 全程 602-829 SFQ 电压态滑移；JTL B1 在 ≤90µA 收到 0，≥110µA 收到 38 (无控滑移)
- **S1.5 Load JTL 计数** ❌：BVM 实际水平 (70µA) 收到 0 SFQ
- **S1.6 支路诊断** ⚠️：BJL1 不再吞噬信号 ✅（修复方向正确），但 BJL2 也从不触发 ❌
- **关键对照**：同测试台 90µA，v2 Vpk=1035µV vs v4 Vpk=186µV — **v4 输出比 v2 差 5.5×**
- 全部运行 md5 确定性验证通过；原始 CSV 保存至 `test/final/qb/data/`

### 为什么
- v4 修改基于"BJL1 吞噬信号"根因，IC 顺序修正确实消除了吞噬
- 但提高 BJL1/BJL2 IC 同时消灭了输出传递路径——能量困在 BJs 滑移环路

### 影响
- **Step 1 Gate 未通过，BQ v4 独立验证失败** → 进入 Step 3 路线决策（迭代 BQ / Step 4 备用接口 / 重审 BVM 输出级）
- 冻结 3 条根因：① BJs 无分流 + βc≈5.4 欠阻尼 → 任何过驱动即持续滑移；② IC 顺序修正副作用；③ 输出级无法驱动 250µA JTL
- 计划文档: `docs/superpowers/plans/2026-08-06-bq-v4.md`（含完整执行结果）

---

## 2026-08-06 — Step 0 完成：基线矛盾解决 + 基线冻结

### 做了什么
- **S0.1 解决基线相位计数矛盾**：根因 = 旧记录混用两套模型时代 + 滑移计数误读
  - `JM1=0.94 SFQ` 来自 V0 模型时代（jj120/jj140/jj74），7/12 18:37 (commit 916ac09) 转换为 jjmit 后不可复现；当前 jjmit 配置写入**多翻转**（settle +5.93 SFQ，仅瞬态穿过 0.94）
  - `BJs=1.00 SFQ` 为计数误读；冻结口径下实际 = +6.27（电压态滑移）
  - GPT 的 `BJs=−0.00001 SFQ` 无法由任何变体重现（当前网表/旧 area=5 网表/电压模式/早期窗口全部产出 +6.2~6.3）
  - `190/96/603 SFQ`（BQ 独立）全是电压态滑移的窗口依赖计数；Vpk=1035µV 三份记录一致
- **S0.2 冻结基线**：`test/final/single_bvm_qb/BASELINE.md` — commit hash + 文件 SHA-256 + 指标定义
- **S0.3 指标脚本**：`scripts/sfq_metrics.py` — net_delta / max_excursion / total_variation / fast_events / max_dPdt，JSON 输出
- **S0.4 重复性验证**：基线×3、BVM×2、BQ×2 全部 md5 一致（确定性确认）
- **S0.5 修复硬编码路径**：`test_bvm_paper_bq.cir` 绝对路径 → 相对路径，重跑验证通过

### 为什么
- GPT 审计发现的基线矛盾（BJs ~1 vs ~0 SFQ）必须解决才能继续 BQ v4
- 旧记录不可复现的根因是 7/12 的模型转换（jj120→jjmit）与滑移计数口径不一

### 影响
- **Step 0 全部 5 项完成，Gate 通过** → Step 1 (BQ v4) 解锁
- 关键物理结论（证据增强）：BVM→BQ 级联无离散 SFQ 输出；BJs 是电压态滑移不是 SFQ 翻转
- 新发现：BVM jjmit 配置写入是多涡旋态（±~6 SFQ），非单涡旋——影响 Step 2 设计
- 所有后续实验必须以 `sfq_metrics.py` 口径产出指标并保存原始 CSV

---

## 2026-08-06 — 项目清理与状态同步

### 做了什么
- **删除 `library_josim/`**：14 个文件（12 .cir + 2 CSV, ~2.8MB），所有电路已正式提取到 `circuits/standard/`
- **删除重复 HTML**：`test/standard/{dff,xor}.html`，保留 `_viz` 版本
- **`.gitignore` 添加 `test/**/*.html`**：仿真可视化输出可随时重新生成，不再进入版本控制
- **提交积压更改**：`memory/GuidanceFromGpt.md` Section 九（GPT 7/19 接口重定义建议）、`mkdocs.yml` nav 更新
- **更新 project-summary.md**：同步至 2026-08 状态（GPT 审计、Step 0-4、BQ v4 方案）
- **扫描并确认硬编码路径**：仅 `test_bvm_paper_bq.cir` 有 1 处 `/home/howard/...`（S0.5 待修复）

### 为什么
- Session 恢复后发现多个积压项：library_josim 与 circuits/standard/ 内容重叠、GuidanceFromGpt.md 有内容未提交
- GPT 审计后项目已转向 Step 0-4 框架，但 project-summary.md 仍停留在 7/12 旧状态
- HTML 可视化已积累到 21 个文件，不应进入 git 历史

### 影响
- 项目目录更简洁：根目录不再有 `library_josim/` 混淆
- 新 HTML 不会再显示为 untracked
- project-summary + project-todo 同步至当前实际状态
- 下一步明确：Step 0（基线校准）→ Step 1（BQ v4）→ Step 2（级联）

---

## 2026-07-17 — GPT 审计 + 项目重构

### 做了什么
- **接收 GPT 外部审计** (`memory/GuidanceFromGpt.md`)：GPT 阅读全部 memory/.remember/ 并重跑基线仿真
- **发现基线相位计数矛盾**：GPT 测得 BJs ~0 SFQ vs 之前记录 ~1 SFQ，需排查
- **项目主任务清单重构**：从旧 Phase 1 计划改为 GPT Step 0-4 框架 + 基建修复 + 模型矩阵
  - Step 0: 冻结基线/解决矛盾（最高优先级）
  - Step 1: BQ v4 独立验证
  - Step 2: BVM→BQ v4 级联
  - Step 3: 决策表（不是"试到成功为止"）
  - Step 4: 备用接口方案
- **确认 GPT 审计与我们的独立分析高度一致**：BQ 不是量化器、v4 是假设不是定论、论文不能以"已解决"定位
- **BQ 工作原理深度分析**：SQUID 磁通积累机制、BJL1 电流吞噬根因、约瑟夫森电感对 dφ/dt 的影响
- **BQ v4 修改方案**：IC 顺序反转 (BJs<BJL2<BJL1) + 输出级增强

### 为什么
- GPT 审计暴露了我们实验严谨性的不足：缺少冻结基线、缺少 Gate 机制、SFQ 计数方法不统一
- 基线数据矛盾说明我们的相位分析方法需要标准化（ΔP/(2π)、起止时间、符号约定）
- GPT 的 Step 0-4 执行顺序和决策表比我们原来"试到成功为止"的方法更工程化

### 影响
- project-todo.md 完全重构为 Step 0-4 框架
- 所有后续工作必须先过 Step 0（基线校准），否则后续结论不可靠
- 论文定位从"接口解决方案"调整为"问题表征与候选接口探索"（直到 v4 出结果）
- 明确：旧 Phase 1 计划中的成功概率和 Gate 描述已过时

---

## 2026-07-17 — BVM→BQ 耦合实验 + BQ 量化测试 + 元件参考手册

### 做了什么
- **BVM→BQ 耦合实验 7 轮**：基线(标准BQ)、低IC×3(阻尼/拓扑/v3仅BJs)、K元件变压器(n=2/2.5/3)、论文原始BQ(JS=133µA)、电阻负载。全部失败——根因是 BVM 慢信号(~30ps)与 SFQ 快脉冲(~2ps)的不匹配
- **发现 BQ 参数来源**：阅读 SUST 2024 论文，确认我们的 BQ(bq_cell.cir, BJs=50µA)是从论文 BQ(JS=133µA)缩小~3×的自定义版本
- **BQ 量化能力测试**：70-170µA 扫参，BQ 内部产生 48→66 SFQ，但 Load JTL 仅捕获恒定 3.1 SFQ（不满足"电流→可变SFQ数"要求）
- **K 元件变压器完整分析**：`memory/k-element-transformer-analysis.md` — 物理原理、4 配置实验、在 SFQ 时间尺度的失效原因
- **元件参考手册**：`memory/component-reference.md` — 8 ColdFlux 元件 + BVM + BQ 的 I/O 参数、测试数据、可视化索引
- **生成 18 个可视化 HTML**：标准元件(8)、BVM(3)、BQ(5)、级联(2)
- **skill-router 重写**：190→50 行，Quick Self-Check + 强制输出格式。修复"应该用 Read 而非 Skill()"的 bug
- **CLAUDE.md 重构**：Skill 调用方式明确分为"插件 Skill (Skill())"和"项目 Skill (Read)"
- **SFQ 脉冲物理规则澄清**：区分 2ps(逻辑) vs 10ps(BVM 存储)，明确"数据先于时钟"= setup time 约束
- **T1 测试文件审查**：发现 5 个问题（include 顺序、电压源驱动、时序错误、无真值表、无 CSV）

### 为什么
- BVM→BQ 耦合是项目唯一硬阻塞。7 轮实验证明不是 BQ 参数问题，是 BVM 输出特性(slow oscillatory current)与 SFQ 接收器(need sharp 2ps edge)的根本失配
- 论文 BQ 也失败说明问题不在 IC 值大小——论文通过多 cell 同时读取累加电流来达到触发阈值
- skill-router 失效的根因是"项目 skill ≠ 注册 Skill 工具"，必须用 Read 不是 Skill()

### 影响
- 确认单 BVM cell 无法直接驱动任何 IC>50µA 的接收器产生干净 SFQ
- 量化器需要重新设计：方向为 SQUID 积累型或极低 IC 检测器 + 多级脉冲压缩
- skill 调用机制修正后，后续会话不再出现 "Unknown skill" → 跳过的错误
- 元件参考手册 + 18 个可视化为所有验证过的元件建立了可查询的 I/O 数据库

---

## 2026-07-13 — 论文方向确立 + PIM 路线图 + ARS 学术技能体系

### 做了什么
- **确立论文 A 方向：BVM→BQ 接口设计** — 基于论文 2507.04648v1 (Karamuftuoglu et al., 2025) 的空白点，经 ARS deep-research 验证为确认的文献空白
- **编写 PIM 路线图设计文档** (`memory/pim-roadmap-design.md`)：PoC→PIM 渐进 5 阶段路线，BVM→BQ 双路线耦合方案（低 IC 检测结 + K 元件变压器），85% 综合成功率
- **编写论文方向分析** (`memory/paper-directions-analysis.md`)：四个方向创新性/可行性评估 + 竞争格局 + ARS 可行性验证 + 目标期刊推荐
- **编写 Phase 1 详细执行计划** (`memory/phase1-bvm-bq-coupling-plan.md`)：8 任务拆解 + 弹性 2 周时间线 + 实验可靠性规范
- **安装 ARS 学术技能套件** (academic-research-skills v3.16.0)：deep-research, academic-paper, academic-paper-reviewer, academic-pipeline 可用
- **创建主任务清单** (`memory/project-todo.md`)：6 大类 30+ 任务，状态追踪 + 依赖关系
- **创建 todo-manager skill** — 会话开始/结束时自动检查/更新任务进度
- **更新 skill-router** — 新增 4 种技能使用模式、ARS 注册表、调用频率统计
- **阅读 ChatGPT 项目建议** (`docs/suggestions.md`)：与我们的 PIM 路线图高度一致
- **简化 CHANGELOG** — 合并 2026-07-12 的三条记录为一条

### 为什么
- BVM→BQ 接口是 BVM PIM 架构的系统瓶颈，文献中完全空白，有明确的发表窗口
- ARS agent 确认：问题真实存在、双路线方案有足够新颖性投稿 SUST (IF~4.2)、主要风险是纯仿真无流片
- 整个 BVM 领域目前都是纯仿真阶段——我们的方法不是弱点而是领域现状
- ChatGPT 建议与我们的独立分析高度一致（BVM→BQ 优先、T1 三层验证、回归测试），增强了方向信心

### 影响
- 项目从"探索阶段"进入"目标导向阶段"：有明确论文目标、时间线和验收标准
- ARS 技能体系使论文撰写可自动化（文献调研→写作→审稿→修改）
- 主任务清单 + todo-manager 确保每次会话有明确起点和终点
- 实验可靠性规范为所有后续仿真工作建立了质量标准

---

## 2026-07-12 — NOT 元件仿真测试 + skill-router 决策技能

### 做了什么
- **NOT 元件（8 结钟控反相器）完整仿真测试**：创建 `test/standard/test_not.cir`，验证真值表 NOT(0)=1、NOT(1)=0，生成 `test/standard/not.html` 可视化
- **PDF 与电路对比验证**：逐行比对 `circuits/standard/NOT.cir` 与 PDF Listing 2.25，确认 8 个 JJ 面积、4 路偏置电流、全部电感/电阻/寄生参数完全一致
- **创建 `skill-router` 项目 Skill**：`.claude/skills/skill-router.md`，决策路由工具——分析用户请求的任务组件，输出需要的 skill 列表及调用顺序，阻止"凭直觉跳过 skill"的行为
- **更新 CLAUDE.md**：skill-router 加入触发规则表首位（任何任务开始时首先调用），josim-viz 信号表添加 NOT 条目
- **创建项目 memory**：`coldflux-library.md`、`sfq-physics.md`、`test-methodology.md`、`jj-model-parameters.md`、`bvm-bq-coupling.md`、`t1-full-adder.md`、`project-structure.md`、`skill-usage.md`、`project-summary.md`

### 为什么
- NOT 是 7 个已验证元件之后的第 8 个标准元件测试，扩展了 ColdFlux 逻辑门覆盖范围
- 上次 NOT 任务中漏掉了 3 个 skill（test-driven-development、dataviz、verification-before-completion），skill-router 的决策树可以在任务开始前捕获这些漏调
- NOT 的 Mealy FSM 有两个状态：State 0（无数据存储）→ CLK 触发输出；State 1（收到数据）→ CLK 回到 State 0 无输出

### 影响
- NOT 成为第 8 个通过验证的 ColdFlux 标准元件
- skill-router 作为元技能（meta-skill），强制任务开始前的 skill 决策检查
- 项目 memory 系统（10 个 .md 文件）覆盖所有关键技术领域，新会话通过 MEMORY.md 自动加载
- 已追踪的漏调案例作为 skill-router 的 Red Flags 表素材

---

## 2026-07-12 — 项目整理与技能体系建立

### 做了什么
- **清理 31 个冗余文件**：根目录 description.md/image_descriptions.md/PROJECT.md + test/final/ 下 3 个旧 .md + 13 个旧 HTML + 12 个旧 CSV
- **建立项目记忆系统**（`~/.claude/projects/-home-howard-JoSIM/memory/`）：10 个 .md 文件覆盖项目结构、ColdFlux 元件库、SFQ 物理、测试方法论、JJ 参数、BVM/BQ 耦合、T1 全加器、Skill 规范、综合总结
- **创建 3 个项目 Skill**：`josim-viz`（可视化）、`project-summary`（总结整理）、更新 `CLAUDE.md` Skill 触发规则表
- **配置 Effort**: settings.local.json 中将所有模型角色 effort 设为 `xhigh`（DeepSeek v4-pro 最高档）
- **测试文件全部改为 2ps 窄脉冲**：test_split.cir, test_merge.cir, test_xor.cir, test_and2.cir, test_ndro.cir 的 PWL 脉宽从 5ps 缩为 2ps

### 为什么
- 项目积累了多个版本的总结文档（PROJECT.md、SUMMARY_FINAL.md 等），内容重复且位置分散，不利于新会话快速加载
- 旧 HTML/CSV 可随时用 josim-plot2/josim-cli 重新生成，无需保留在仓库中
- 5ps 脉冲导致 multi-SFQ 事件（单脉冲触发多次结翻转），2ps 确保每次 1 SFQ
- Claude 在之前工作中未充分利用已安装的 ECC/Superpowers 技能套件

### 影响
- 项目根目录更简洁（仅 CLAUDE.md + README.md + CHANGELOG.md）
- 新会话通过 MEMORY.md 自动加载所有关键知识
- Skill 触发规则写入 CLAUDE.md，强制每次任务前检查适用 skill
- 可视化输出统一使用 josim-plot2.py（sep_comb 布局 + -j 2pi 单位）

---

## 2026-07-12 — ColdFlux 7 元件完整测试与验证

### 做了什么
- **全部 7 个标准元件功能验证通过**：JTL、SPLIT、MERGE、DFF、XOR、AND2、NDRO
- **发现并修复钟控逻辑时序问题**：XOR 和 AND2 的 CLK 在数据之前到达，导致 RSFQ 钟控单元无法正确采样。修正为数据 SFQ 先于时钟 SFQ
- **XOR 真值表完整验证**：0⊕0=0, 1⊕0=1, 1⊕1=0, 0⊕1=1（4/4 通过）
- **老测试文件脉冲改为 2ps**：test_jtl.cir, test_dff.cir 的 PWL 脉宽缩窄
- **使用 josim-plot2.py 生成 7 个 I/O 可视化 HTML**：仅显示输入输出电压 + Load JTL 相位，sep_comb 分组布局

### 为什么
- 之前 XOR 的 (0,0)→0 失败是因为使用了 5ps 宽脉冲 + 时钟在数据前的错误时序
- ColdFlux 钟控单元内部有存储超导环——数据先到达存储在环中，时钟才读取。时序反了就无法工作

### 影响
- 7 个元件测试全部标准化（2ps 脉冲 + 正确时序）
- 测试文件在 `test/standard/test_*.cir`，可视化在 `test/standard/*.html`
- 确认 ColdFlux 库可用于构建更复杂电路

---

## 2026-06-24 — ColdFlux 标准元件库提取

### 做了什么
- 从 `arti/ColdFlux_RSFQ_Logic_Cell_Library_for_MIT_LL_SFQ_Process_v3p0.pdf` 提取 **35 个标准元件**
- 创建 `circuits/standard/` 目录，每个元件一个 `.cir` 子电路文件
- 创建 `circuits/standard/INDEX.md` 元件库索引
- 修复 PDF 提取 artifact（拼接行号、缺参数数字、PDF 页眉混入、科学记数法拼接等）
- 为 7 个核心元件（JTL/SPLIT/MERGE/DFF/XOR/AND2/NDRO）创建测试文件和初版可视化

### 为什么
- 超导数字电路仿真需要标准元件库支持
- ColdFlux 是 MIT-LL SFQ5ee 工艺的工业级元件库

### 影响
- 建立了完整的标准化元件仿真基础
- `circuits/standard/` 成为项目核心资产
- jjmit 模型（Ic×RN=1.6mV）成为标准元件默认模型

---

## 2026-05-30 — BVM/BQ 独立验证 + T1 全加器开始

### 做了什么
- BVM 存储单元独立验证通过：写入/读取/存储/半选均正常
- BQ 量化缓冲器独立验证通过：90µA 输入 → 1.035mV SFQ 输出
- T1 全加器建模（从论文 `arti/T1_structure.md`、`arti/t1str.md` 提取拓扑结构）
- T1 CLK 隔离测试通过 (5/5)
- 发现 BVM+BQ 级联不工作：SL 输出 ~130Ω vs BQ 输入 ~350Ω 阻抗不匹配

### 为什么
- 打通「存储→缓冲→逻辑」全链路需要每级独立工作
- jjmit 模型参数（Ic×RN=1.6mV）使 BVM 无法正常工作（写操作过强，多涡旋）

### 影响
- BVM/BQ 均能独立输出 SFQ，但级联问题待解决
- 引入混合模型方案（BVM 用 V0 参数 0.25mV，BQ/ColdFlux 用 jjmit 1.6mV）

---

## 2026-05-19 — JJ 模型参数研究

### 做了什么
- 深入分析 RCSJ 模型物理原理：IC、RN、R0、CAP、VG 的作用
- 4 轮参数演变测试（V0 → JSIM → JoSIM → T2017 → grid scan 60 组合）
- 确定 V0 参数（Ic×RN=0.25mV, R0/RN=3）是 BVM 唯一工作集
- 编写 `test/final/PARAMETER_STUDY.md` 详细记录（后归档至 memory/）

### 为什么
- BVM 需要低 Ic×RN（0.25mV）才能稳定写入和存储
- 标准 ColdFlux/SFQ5ee 参数（1.6-1.7mV）导致写入过强
- 不同电路类型需要不同参数集，不能统一

### 影响
- 建立了混合模型方法：BVM=V0 + BQ=ColdFlux
- BVM 结类型分级：JM1(120µA) 开关、JM2(140µA) 非开关、JS1/JS2(74µA) 检测

---

## 2026-04-23 — 项目初始化

### 做了什么
- JoSIM 编译与基础测试
- ex_jtl_basic.cir 等示例运行通过
- 基础元件测试套件建立（R/L/C/JJ/TX/VS/VCCS/VCCS/CCCS/CCVS）

### 为什么
- 确认仿真环境可用
- 建立测试基础设施

### 影响
- 项目启动，所有后续工作的基础
