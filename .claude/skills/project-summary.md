---
name: project-summary
description: >
  Use when summarizing JoSIM project status, archiving knowledge, cleaning up redundant files,
  recording change history, or updating project memory. Trigger words: 总结项目, 整理项目,
  归档, 项目总结, 更新记忆, 记录变更. JoSIM project ONLY.
---

# 项目总结与整理

## 触发条件

当用户提到以下关键词时调用：
- 总结项目、整理项目、项目总结、归档、收尾、清理项目
- "帮我梳理一下项目"、"整理一下现在的进度"
- "记录一下变更/改动"、"更新记忆"

## 核心原则

**memory/ 目录是项目的持久知识库，位于项目根目录下，可直接查看、编辑、提交 git。**

```
JoSIM/memory/          ← 项目内（可 git 追踪）
  ├── MEMORY.md        ← 索引（Claude 会话启动时自动加载）
  ├── project-summary.md  ← 综合状态快照
  ├── coldflux-library.md ← ColdFlux 元件库知识
  ├── sfq-physics.md      ← SFQ 脉冲物理规则
  ├── test-methodology.md ← 测试方法论
  ├── jj-model-parameters.md ← JJ 模型参数演变
  ├── bvm-bq-coupling.md  ← BVM→BQ 耦合问题
  ├── t1-full-adder.md    ← T1 全加器
  ├── project-structure.md ← 项目结构
  └── skill-usage.md      ← Skill 使用规范
```

## 工作流程

### ⚠️ 第一步：更新 CHANGELOG.md（每次必做，不可跳过）

回顾当前会话做了什么，追加到项目根目录 `CHANGELOG.md`。

```markdown
## YYYY-MM-DD — 简短标题

### 做了什么
- 列出具体变更

### 为什么
- 解释原因

### 影响
- 对项目的后续影响
```

**规则**：只追加不删除、用当天日期、标题概括本轮工作。

### 第二步：扫描现状

```bash
find . -name "*.md" -type f | grep -v node_modules | grep -v build | grep -v .git
find . -name "*.html" -type f
find . -name "*.csv" -type f
find test/ -type d | sort
```

### 第三步：分类评估

| 判断 | 操作 |
|------|------|
| 内容已在 memory/ 中 | 删除 |
| 旧版本可重新生成 | 删除 |
| 唯一的知识来源 | 提取到 memory/ |
| 当前工作必需 | 保留 |

### 第四步：更新 memory/ 中的知识文件

检查并更新以下文件（所有文件在项目根目录 `memory/` 下）：

1. **`memory/project-summary.md`** — 综合状态快照：已完成工作、已知问题、下一步方向
2. **`memory/project-structure.md`** — 项目目录布局、关键文件位置
3. **`memory/coldflux-library.md`** — 元件库新增/变更
4. **`memory/sfq-physics.md`** — 新发现的物理规则
5. **`memory/test-methodology.md`** — 测试约定变更
6. **`memory/jj-model-parameters.md`** — 模型参数新发现
7. **`memory/bvm-bq-coupling.md`** — BVM/BQ 相关进展
8. **`memory/t1-full-adder.md`** — T1 全加器进展
9. **`memory/skill-usage.md`** — Skill 使用规范变更

**更新规则**：
- 如果文件已存在但内容过时 → 编辑更新
- 如果有新知识且不属于已有文件 → 创建新 .md 文件
- 每个 memory 文件保持单一主题
- 使用 frontmatter（name, description, metadata.type）
- 在 body 中记录 **Why** 和 **How to apply**
- 用 `[[other-memory]]` 链接相关知识

### 第五步：更新 MEMORY.md 索引

`memory/MEMORY.md` 是索引文件。每行一条：

```markdown
- [标题](file.md) — 一句话描述
```

新增的 memory 文件必须添加索引条目。

### 第六步：清理

删除所有可重新生成或已归档的文件：
- 旧 HTML 可视化（可用 josim-plot2 重新生成）
- 旧 CSV 仿真结果（可用 josim-cli 重新生成）
- 重复的 .md 文档（已提取到 memory/）

### 第七步：报告

```
总结完成：
- CHANGELOG.md 已更新（新增 X 条记录）
- memory/ 已更新 Y 个文件
- 删除 Z 个冗余文件
- 项目状态：<一句话>
```

## CHANGELOG vs memory 分工

| | CHANGELOG.md | memory/*.md |
|------|-------------|-------------|
| **内容** | 变更历史（时间线） | 知识库（事实） |
| **读者** | 人类 | AI + 人类 |
| **格式** | 日期→做了什么→为什么→影响 | frontmatter + 正文 |
| **更新** | 每次会话追加 | 知识变化时编辑 |
| **位置** | 项目根目录 | 项目 memory/ 目录 |
