---
name: project-structure
description: JoSIM 项目结构全貌 — Phase −1 目录布局、证据层级和 Workflow 入口
metadata:
  node_type: memory
  type: project
  last_updated: 2026-08-09
---

## JoSIM 项目结构（2026-08-09 更新）

### 顶层目录

```
JoSIM/
├── src/                ← C++ 源码
├── include/JoSIM/      ← 头文件
├── build/              ← CMake 构建输出 + josim-cli（v2.7.2837d13 冻结）
├── scripts/            ← 工具脚本（README.md 索引）
│   ├── run_exp.sh      ← 历史 v1 runner（不得用于当前物理 Gate）
│   └── sfq_metrics.py  ← 失效 v1 指标（等待 M4–M9 替代）
├── circuits/           ← 仿真电路（INDEX.md 索引）
│   ├── standard/       ← ColdFlux 35 元件库（冻结，含 INDEX.md）
│   ├── interface/      ← DCSFQ_BVM 候选路线
│   ├── models/         ← jjmit.cir（冻结模型）
│   ├── bvm/            ← BVM 存储单元（待 v2 基线）
│   ├── qb/             ← BQ/BQ v4 候选与历史版本
│   ├── t1/             ← T1 全加器（未验证）
│   └── sfq_gen*.cir    ← 单结 SFQ 发生器（已弃用，测试引用勿移）
├── test/
│   ├── final/          ← 项目电路测试（README.md 索引）
│   │   ├── interface/  ← DCSFQ_BVM Phase 0 历史数据
│   │   ├── single_bvm_qb/ ← 待 v2 重建的历史基线
│   │   ├── bvm/ qb/ t1/ array/ sfq_gen_*/ ref_tests/
│   ├── standard/       ← 标准元件测试
│   ├── bvm/ bq/        ← 早期测试（大部分弃用）
│   └── comp/           ← 基础元件测试
├── docs/
│   ├── HANDOVER.md     ← 会话交接（新会话第一读）★
│   ├── paper/          ← 论文证据链 + 素材
│   └── superpowers/    ← specs/（设计）+ plans/（实施计划）
├── memory/             ← 项目知识库（MEMORY.md 索引带状态标注）
├── arti/               ← 参考论文/PDF
├── .agents/skills/     ← 项目 Skills 唯一规范源
├── .claude/skills/     ← Claude Code 兼容目录链接
├── AGENTS.md           ← 仓库级证据与实验不变量
├── CLAUDE.md           ← Claude Code 架构与 skill 入口
└── CHANGELOG.md        ← 变更历史（只追加）
```

### 关键文件路径

| 用途 | 路径 |
|------|------|
| 仿真程序（唯一可用） | `build/josim-cli`（v2.7.2837d13，禁 /usr/local/bin） |
| 历史 v1 runner（禁作 Gate） | `scripts/run_exp.sh` |
| 失效 v1 指标（禁作 Gate） | `scripts/sfq_metrics.py` |
| 实验工作流 | `.agents/skills/josim-experiment/` |
| 证据审计 | `.agents/skills/josim-evidence-audit/` |
| JJ 模型 | `circuits/models/jjmit.cir` |
| 元件库索引 | `circuits/standard/INDEX.md` + `circuits/INDEX.md` |
| 历史基线入口 | `test/final/single_bvm_qb/BASELINE.md` |
| Phase 0/1 数据 | `test/final/interface/P0_LOG.md`（+ P0_LOG_P00-P03） |
| 设计/计划 | `docs/superpowers/specs/` + `docs/superpowers/plans/` |
| 任务权威 | `memory/project-todo.md` |
| 会话交接 | `docs/HANDOVER.md` |

### 构建命令

```bash
cd build && cmake .. && make -j$(nproc)
# 可选: -DSLU=ON (SuperLU), -DUSING_OPENMP=ON
```

### 当前实验入口

```bash
# 按 .agents/skills/josim-experiment/SKILL.md 创建唯一 run 目录，
# 使用已记录的 build/josim-cli 生成不可覆盖的 raw CSV。
# 物理判定按 .agents/skills/josim-evidence-audit/SKILL.md；
# 在 METRIC_SPEC_V2 冻结前只允许 calibration/exploratory 结论。
```

[[coldflux-library]] [[test-methodology]] [[sfq-physics]] [[skill-usage]] [[project-todo]]
