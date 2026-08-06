---
name: project-structure
description: JoSIM 项目结构全貌 — 目录布局、关键文件位置、Workflow 约定
metadata:
  node_type: memory
  type: project
  last_updated: 2026-08-06
---

## JoSIM 项目结构（2026-08-06 更新）

### 顶层目录

```
JoSIM/
├── src/                ← C++ 源码
├── include/JoSIM/      ← 头文件
├── build/              ← CMake 构建输出 + josim-cli（v2.7.2837d13 冻结）
├── scripts/            ← 工具脚本（README.md 索引）
│   ├── run_exp.sh      ← 一键实验（仿真→指标→md5）★ Phase 1+ 标准动作
│   └── sfq_metrics.py  ← 冻结指标脚本（唯一口径）
├── circuits/           ← 仿真电路（INDEX.md 索引）
│   ├── standard/       ← ColdFlux 35 元件库（冻结，含 INDEX.md）
│   ├── interface/      ← DCSFQ_BVM（H7 主路线）★ 当前主线
│   ├── models/         ← jjmit.cir（冻结模型）
│   ├── bvm/            ← BVM 磁通涡旋存储器（冻结基线）
│   ├── qb/             ← BQ 缓冲器（路线已排除，保留）
│   ├── t1/             ← T1 全加器（未验证）
│   └── sfq_gen*.cir    ← 单结 SFQ 发生器（已弃用，测试引用勿移）
├── test/
│   ├── final/          ← 项目电路测试（README.md 索引）
│   │   ├── interface/  ← DCSFQ_BVM Phase 0/1（P0_LOG.md）★
│   │   ├── single_bvm_qb/ ← 冻结基线（BASELINE.md）
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
├── .claude/skills/     ← 项目 Skill（skill-router 强制入口）
├── CLAUDE.md           ← 项目指南（架构 + Skill 触发规则）
└── CHANGELOG.md        ← 变更历史（只追加）
```

### 关键文件路径

| 用途 | 路径 |
|------|------|
| 仿真程序（唯一可用） | `build/josim-cli`（v2.7.2837d13，禁 /usr/local/bin） |
| 一键实验 | `scripts/run_exp.sh` |
| 冻结指标 | `scripts/sfq_metrics.py` |
| JJ 模型 | `circuits/models/jjmit.cir` |
| 元件库索引 | `circuits/standard/INDEX.md` + `circuits/INDEX.md` |
| 冻结基线 | `test/final/single_bvm_qb/BASELINE.md` |
| Phase 0/1 数据 | `test/final/interface/P0_LOG.md`（+ P0_LOG_P00-P03） |
| 设计/计划 | `docs/superpowers/specs/` + `docs/superpowers/plans/` |
| 任务权威 | `memory/project-todo.md` |
| 会话交接 | `docs/HANDOVER.md` |

### 构建命令

```bash
cd build && cmake .. && make -j$(nproc)
# 可选: -DSLU=ON (SuperLU), -DUSING_OPENMP=ON
```

### 实验命令（冻结口径）

```bash
# 一键（仿真+指标+md5）：
scripts/run_exp.sh <netlist.cir> <out_name> "<phase_cols>" [--peaks "..."]
# 手动：./build/josim-cli -o data/x.csv <netlist.cir>
# 指标：python3 scripts/sfq_metrics.py data/x.csv "P(B1|XDCSFQ),..." --peaks "V(OUT1)"
```

[[coldflux-library]] [[test-methodology]] [[sfq-physics]] [[project-todo]]
