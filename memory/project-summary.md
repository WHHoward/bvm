---
name: project-summary
description: JoSIM 项目综合总结 — 2026-08-06 状态，GPT 审计后 Step 0-4 框架，BVM→BQ 耦合待解决
metadata: 
  node_type: memory
  type: project
  last_updated: 2026-08-06
---

# JoSIM 项目综合总结

**最后更新**: 2026-08-06
**分支**: master
**构建**: 正常 (`build/josim-cli` 可用)
**当前阶段**: Step 0（基线校准）— BVM→BQ 接口阻塞中

---

## 一、项目概况

JoSIM 是一个超导电子学 SPICE 语法电路仿真器。我们使用它来仿真基于 ColdFlux RSFQ 设计方法的超导数字电路，目标是构建从存储单元（BVM）到逻辑门（ColdFlux 标准元件）再到运算单元（T1 全加器）的完整仿真流水线。

## 二、已完成工作

### 2.1 ColdFlux 标准元件库（✅ 8/8 验证通过）

从 PDF 提取了 35 个 MIT-LL SFQ5ee 标准元件，对其中 8 个核心元件进行了完整测试验证：

| 元件 | JJ | 类型 | 验证结果 |
|------|-----|------|---------|
| JTL | 2 | 异步 | ✅ SFQ 传输 |
| SPLIT | 3 | 异步 | ✅ 1→2 扇出 |
| MERGE | 7 | 异步 | ✅ 2→1 汇聚 |
| DFF | 7 | 钟控 | ✅ 写→存→读 |
| XOR | 11 | 钟控 | ✅ 真值表 4/4 |
| AND2 | 15 | 钟控 | ✅ 1∧1=1, 1∧0=0 |
| NDRO | 11 | 钟控 | ✅ 非破坏读出 |
| NOT | 8 | 钟控 | ✅ NOT(0)=1, NOT(1)=0 |

### 2.2 BVM 磁通涡旋存储器（✅ 独立工作）

- JM1 = |0.94| SFQ，写入/读取/存储/半选均正常
- 使用 jjmit 模型（area 参数调谐）

### 2.3 BQ 量化缓冲器（⚠️ 独立工作但功能有限）

- 90µA 矩形电流脉冲 → 1035µV 输出
- **局限**：需要 ≥110µA 才能通过 JTL 传播；输出饱和在 ~3 SFQ，不随输入线性增长
- **根因**：BJL1 IC(36µA) < BJs IC(50µA)，BJL1 先触发吞噬 BJs 输出能量

### 2.4 T1 全加器（🔴 未测试）

- CLK 隔离测试曾通过 (5/5)，但完整功能验证未完成
- 存在 include 顺序、电压源驱动等已知问题

## 三、BVM→BQ 耦合实验总结

**7 轮实验全部失败**。详见 [[bvm-bq-coupling-experiments]]。

| 路线 | 方法 | 结果 |
|------|------|------|
| 基线 | BVM→标准 BQ 直接级联 | ❌ BJs ~0-1 SFQ（矛盾待解） |
| 低 IC v1-v3 | BJs IC 20-50µA | ❌ L_J 内在矛盾 |
| K 元件变压器 | n=2.0/2.5/3.0 | ❌ SFQ 时间尺度耦合太弱 |
| 论文 BQ | JS=133µA 原始参数 | ❌ 阈值不匹配 |
| 电阻负载 | 12Ω | ❌ 不如 JJ 负载 |
| 单结 sfq_gen | IC 调谐 | ❌ 触发电阻分压 |

**根因分析**：BVM 输出是 ~30ps 慢振荡电流，BQ 需要 ~2ps 快边缘触发。BJL1 低 IC 进一步恶化。

## 四、当前执行框架：GPT 审计 Step 0-4

详见 [[project-todo]] 和 [[GuidanceFromGpt]]。

| Step | 内容 | 状态 |
|------|------|------|
| Step 0 | 冻结基线、解决相位计数矛盾 | 🔴 最高优先级 |
| Step 1 | BQ v4 独立验证 (BJL1 36→90µA) | 🔴 阻塞于 Step 0 |
| Step 2 | BVM→BQ v4 级联 | 🔴 阻塞于 Step 1 |
| Step 3 | 根据结果做路线决策 | 🔴 阻塞于 Step 2 |
| Step 4 | 备用接口方案 | 🔴 仅 v4 失败后启动 |

### BQ v4 修改方案

详见 [[bq-v4-modification-plan]]。核心改动：IC 顺序反转 BJs(50) < BJL2(70) < BJL1(90)，确保 BJL1 不再先触发吞噬信号。

## 五、基础设施状态

| 项目 | 状态 |
|------|------|
| 构建 | ✅ `build/josim-cli` 可用 |
| CTest | ⚠️ BVM/BQ/级联测试未接入 |
| 硬编码路径 | ⚠️ 1 处 (`test_bvm_paper_bq.cir`) |
| SFQ 计数 | ⚠️ 人工读图，无自动化脚本 |
| HTML 可视化 | ✅ 21 个，已加入 .gitignore |
| 项目记忆 | ✅ 18 个 memory 文件 |
| Skills | ✅ skill-router/josim-viz/project-summary/todo-manager |

## 六、下一步方向

1. **Step 0.1（最优先）**：解决基线相位计数矛盾（BJs ~1 vs ~0 SFQ）
2. **Step 0.2-0.5**：冻结基线 + 自动化脚本 + 修复路径
3. **Step 1**：BQ v4 独立验证（仅 Step 0 通过后）
4. **Step 2**：BVM→BQ v4 级联（仅 Step 1 通过后）
5. **备用**：如果 v4 失败，转向专用慢电流→SFQ 接口设计

论文方向暂不锁定——等 BQ v4 出结果后根据实际情况定位（问题表征 / 候选方案 / 解决方案）。
