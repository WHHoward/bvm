# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build

```bash
# From the build/ directory
cd build && cmake .. && make -j$(nproc)

# Build options:
#   -DSLU=ON            Use SuperLU instead of KLU
#   -DUSING_OPENMP=ON   Enable OpenMP parallelism
```

## Test

```bash
cd build && ctest                          # All integration tests
cd build && ctest -R integration::test_jj  # Single test
ctest --test-dir build                     # From project root
```

Tests are integration tests that run `.cir` SPICE netlists through `josim-cli` and compare output CSVs. Defined in `test/CMakeLists.txt` via `add_integration_test()`.

## Architecture

JoSIM is a SPICE syntax circuit simulator for superconducting electronics. It reads a SPICE deck (`.cir`), builds a system of equations `Ax=b`, and solves it with KLU (SuiteSparse) at each timestep.

### Pipeline

1. **Input parsing** — `Input` reads the `.cir` file and splits lines into tokens. `Netlist` expands subcircuits and parameters into a flat netlist.
2. **Matrix construction** — `Matrix` maps nodes, creates component objects, and builds the CSR sparse matrix representation.
3. **Simulation** — `Simulation` runs transient analysis using the 2nd-order Gear integration method. Each timestep sets up the `b` vector and component stamps, then calls KLU to solve.
4. **Output** — `Output` writes results as CSV or raw SPICE format.

### Key classes

| Class | Role |
|---|---|
| `Input` | Owns the parsed netlist, parameters, transient config, and CLI options |
| `Netlist` | Subcircuit expansion, parameter substitution, `.include` resolution |
| `Matrix` | Node mapping, component creation, CSR sparse matrix (`ci`, `rp`, `nz`) |
| `Simulation` | Transient analysis loop, LU solve orchestration |
| `Components` | `std::variant` container of all device types (R, L, C, JJ, VS, PS, TX, VCCS, CCCS, VCVS, CCVS) |
| `Parameters` | Expression parser/evaluator for `.param` variables |
| `Function` | Time-dependent source waveform generation |
| `Errors` | Error message catalog and exit handling |

### Component stamp model

Each component type contributes entries (stamps) to the A matrix and b vector. The stamp logic lives in each component's source file (e.g., `Resistor.cpp`, `JJ.cpp`). Components use `Row`/`Col` enums to define positions (BRANCH, POS, NEG, etc.).

### Analysis type

Phase analysis is the standard mode (voltage was deprecated as of v2.5). Only transient analysis is supported — there is no DC or AC sweep.

### Dependencies (fetched via CPM during CMake configure)

- **KLU** (SuiteSparse) — default sparse LU solver, 64-bit
- **SuperLU** — optional alternative solver (`-DSLU=ON`)
- **CBLAS** — linear algebra primitives

## Code conventions

- C++17, `JoSIM::` namespace
- Use `int64_t` throughout (codebase was migrated to 64-bit in v2.6.1)
- Headers are in `include/JoSIM/`, implementation in `src/`
- Error messages are centralized in `Errors.cpp` with `Errors::<category>_messages()` functions, keyed by error enum
- Deep copy is typical; components and vectors are passed by value/reference depending on ownership

## Skills — 强制执行（每次响应前必读）

**🚨 IRON RULE: 在任何 Bash/Write/Edit 调用之前，你必须先阅读 `.claude/skills/skill-router.md` 并输出 `[skill-router] Task: ... Skills: ...` 行。不读 skill-router = 违规。**

> 项目 skills 不是 Skill 工具——用 `Read(.claude/skills/skill-router.md)` 读取，不是 `Skill("skill-router")`。

### 触发规则

### 📋 插件 Skills — 用 `Skill("name")` 调用

| 当你在做…… | 必须调用 | 说明 |
|------------|---------|------|
| 写多步骤代码变更 | `Skill("superpowers:writing-plans")` | 先出计划再动手 |
| 实现功能或修 bug | `Skill("superpowers:test-driven-development")` | 先写测试，再写代码 |
| 测试失败或结果不对 | `Skill("superpowers:systematic-debugging")` | 系统性排查 |
| 声称完成/修好/通过 | `Skill("superpowers:verification-before-completion")` | 先验证再说话 |
| 创建图表/可视化 | `Skill("dataviz")` | 标准配色和交互 |
| 修改 C++ 源码 | `Skill("ecc:cpp-review")` | C++ 代码审查 |
| 从 PDF 提取内容 | `Skill("document-skills:pdf")` | PDF 处理 |
| 设计/架构讨论 | `Skill("superpowers:brainstorming")` | 结构化讨论 |

### 📁 项目 Skills — 用 `Read(.claude/skills/<name>.md)` 读取

> 这些是本地 `.md` 文件，不是注册的 Skill 工具。**必须用 Read 读取，不能用 Skill() 调用。**

| Skill | 文件 | 触发场景 |
|-------|------|---------|
| **skill-router** | `.claude/skills/skill-router.md` | ⚠️ **任何任务开始前必读** |
| **josim-viz** | `.claude/skills/josim-viz.md` | 仿真结果可视化 (plot/画图/波形) |
| **project-summary** | `.claude/skills/project-summary.md` | 总结整理/更新CHANGELOG/memory |
| **todo-manager** | `.claude/skills/todo-manager.md` | 会话开始/结束, 进度查询
- **`josim-viz`** — 仿真结果可视化。触发词：可视化、画图、看图、出图、plot、波形
- **`todo-manager`** — 会话开始/结束时检查/更新主任务清单。触发词：进度、接下来做什么、任务做完了
- 位于 `.claude/skills/josim-viz.md`
