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

## Skills — 每个任务开始前必须检查

**本项目安装了完整的 ECC + Superpowers 技能套件。每次响应前检查是否有适用的 skill，不要跳过。**

### 触发规则

**每次任务的第一件事：调用 `skill-router` 分析用户请求，确定需要哪些 skill。不要凭直觉跳过。**

| 当你在做…… | 必须先调用…… | 说明 |
|------------|-------------|------|
| **任何任务开始时** | `skill-router` | 决策路由，确定需要哪些 skill |
| 写多步骤代码变更 | `superpowers:writing-plans` | 先出计划再动手 |
| 实现功能或修 bug | `superpowers:test-driven-development` | 先写测试，再写代码 |
| **测试失败或结果不对** | `superpowers:systematic-debugging` | 系统性排查，不要猜 |
| **声称"完成了/修好了/通过了"** | `superpowers:verification-before-completion` | 先验证，再说话 |
| 创建任何图表/可视化 | `dataviz` | 标准配色和交互 |
| **生成仿真结果可视化** | `josim-viz` | JoSIM 可视化（本项目 skill） |
| 修改 C++ 源码 | `ecc:cpp-review` | C++ 代码审查 |
| 从 PDF 提取内容 | `document-skills:pdf` | PDF 处理 |

### 本项目自定义 Skill

- **`skill-router`** — 任务开始时决策路由，分析用户请求确定需要哪些 skill
- **`josim-viz`** — 仿真结果可视化。触发词：可视化、画图、看图、出图、plot、波形
- 位于 `.claude/skills/josim-viz.md`
