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
