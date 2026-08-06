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

### 第五步：更新 project-todo.md ⚠️ 不可跳过

扫描 `memory/project-todo.md`，逐项检查状态：

- 本次会话完成的任务：🔴→🟢，写完成日期和产出
- 放弃/暂停的路线：🔴→⏸️，写原因
- 新增的待办任务：添加新行，标注 🔴
- 更新 metadata 中的 `last_updated` 日期

**同时更新 `memory/MEMORY.md` 索引**（如有新增 memory 文件）。

### 第六步：更新 MEMORY.md 索引

`memory/MEMORY.md` 是索引文件。每行一条：

```markdown
- [标题](file.md) — 一句话描述
```

新增的 memory 文件必须添加索引条目。

### 第七步：清理

删除所有可重新生成或已归档的文件。

### 第八步：报告

```
总结完成：
- CHANGELOG.md 已更新
- project-todo.md 已更新 (N 个任务状态变化)
- memory/ 已更新
- 项目状态：<一句话>
```

## 时间标注规则（2026-08-06 起强制）

**任何对 `CHANGELOG.md`、`memory/project-todo.md`、`memory/project-summary.md`、`memory/*.md` 的修改，必须在修改处标注修改时间。**

| 文件 | 标注方式 |
|------|---------|
| project-todo.md | 任务行状态/说明变化 → 行内标注 `(YYYY-MM-DD)`；更新日志表每次追加带日期行 |
| project-summary.md | 头部"最后更新"日期必改；修改的章节标题或内容处标注 `(YYYY-MM-DD)` |
| memory/*.md | frontmatter `last_updated` 必改；正文修改处行内标注 |
| CHANGELOG.md | 已有规则：每次会话追加带日期条目 |

**Why**: 项目由人类/GPT/Claude 多会话交替修改，无时间标注的修改会造成文档状态混乱（2026-07 基线矛盾教训）。
**How to apply**: 修改任何上述文件时，先确认或添加修改日期，再落笔。

## 三大追踪文件

| | CHANGELOG.md | project-todo.md | memory/*.md |
|------|-------------|-----------------|-------------|
| **内容** | 变更历史 | 任务状态 | 知识库 |
| **读者** | 人类 | AI+人类 | AI+人类 |
| **更新** | 每次会话追加 | **每次总结必更新** | 知识变化时编辑 |
| **位置** | 项目根目录 | memory/ | memory/ |
