---
name: project-structure
description: JoSIM 项目结构全貌 — 目录布局、关键文件位置、Workflow 约定
metadata: 
  node_type: memory
  type: project
  originSessionId: c5521155-33ba-4655-a787-c46e6bb6b2b1
---

## JoSIM 项目结构

### 顶层目录

```
JoSIM/
├── src/              ← C++ 源码
├── include/JoSIM/    ← 头文件
├── build/            ← CMake 构建输出 + josim-cli
├── scripts/          ← josim-plot.py / josim-plot2.py（可视化工具）
├── circuits/         ← 仿真电路
│   ├── standard/     ← ColdFlux 35 元件库 + INDEX.md
│   ├── models/       ← jjmit.cir（JJ 模型）、mitll_models.cir
│   ├── bvm/          ← BVM 磁通涡旋存储器
│   └── qb/           ← BQ 缓冲器
├── test/
│   ├── standard/     ← 7 个元件测试 + HTML 可视化
│   ├── final/        ← BVM/BQ 综合测试 + 分析文档
│   ├── bvm/          ← BVM 早期测试（已弃用大部分）
│   ├── bq/           ← BQ 早期测试（已弃用大部分）
│   └── comp/         ← 基础元件测试（R/L/C/JJ/TX/VS...）
├── arti/             ← 参考论文/PDF 及其结构分析
├── .claude/          ← Claude Code 项目配置
│   ├── skills/       ← 项目 Skill（josim-viz.md）
│   ├── settings.json ← 项目权限
│   └── settings.local.json ← 本地配置（effort、模型）
├── CLAUDE.md         ← 项目指南（架构 + Skill 触发规则）
└── PROJECT.md        ← 项目元信息
```

### 关键文件路径

| 用途 | 路径 |
|------|------|
| 仿真程序 | `build/josim-cli` |
| 可视化脚本 | `scripts/josim-plot2.py` (有 -j 2pi 参数) |
| JJ 模型 | `circuits/models/jjmit.cir` |
| 元件库索引 | `circuits/standard/INDEX.md` |
| 已验证测试 | `test/standard/test_*.cir` (7 个) |
| BVM/BQ 分析 | `test/final/BVM_BQ_IMPEDANCE_ANALYSIS.md` |

### 构建命令

```bash
cd build && cmake .. && make -j$(nproc)
# 可选: -DSLU=ON (SuperLU), -DUSING_OPENMP=ON
```

### 仿真命令

```bash
./build/josim-cli -o output.csv test/standard/test_jtl.cir
```

[[coldflux-library]] [[test-methodology]] [[sfq-physics]] [[bvm-bq-coupling]]
