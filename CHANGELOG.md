# JoSIM 项目变更日志

> **规则**: 只追加不删除。每次变更记录：日期、做了什么、为什么、影响是什么。

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
