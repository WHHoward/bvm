# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Executor mode for delegated research tasks

When the user or Codex points to `research/tasks/<task-id>/request.yaml`, treat that issued, SHA-256-sealed request as the execution contract. The hash seal detects changes; it is not identity authentication:

1. Read `AGENTS.md`, [research/CLAUDE_EXECUTOR.md](research/CLAUDE_EXECUTOR.md), and the request's `contracts.read_first` files.
2. Invoke `josim-handoff`, verify the request/hash seal, and write an ACK before the first edit or run.
3. Change only `scope.write_paths`; do not edit the request, audits, `memory/project-todo.md`, `docs/HANDOVER.md`, `CHANGELOG.md`, frozen specs, or historical raw evidence.
4. Write a receipt with exact paths, commands, hashes, tests, deviations, and blockers. Propose interpretations, but leave the final evidence/Gate verdict to Codex audit.

If the task is `DRAFT`, unsealed, has issuance blockers, or needs broader authority, stop and report the blocker. Do not silently repair the contract.

If Codex is unavailable (e.g. quota exhausted), the user may explicitly authorize Claude to stand in for Codex-level actions (issue/supersede requests, state sync). Such actions must be recorded in `research/tasks/<id>/standin/<Sxx>/record.yaml` as `PROVISIONAL` and are not effective until Codex writes a review (`CONFIRMED`). See `research/WORKFLOW.md` §15. Stand-in must never audit its own execution.

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

## Repository skills

Project skills use the standard `SKILL.md` layout. The canonical source is `.agents/skills/`; `.claude/skills/` contains directory links for Claude Code compatibility. Let each skill's description trigger it, or invoke it explicitly by name. Do not force a router before every tool call.

| Skill | Use for |
|---|---|
| `josim-handoff` | Work with hash-sealed task contracts: Claude writes ACK/receipts; Codex writes audits |
| `josim-experiment` | Create/run/sweep/reproduce `.cir` experiments with immutable evidence |
| `josim-evidence-audit` | Interpret phase, voltage area, SFQ claims, JTL reception and Gate verdicts |
| `josim-viz` | Plot CSV/DAT waveforms without upgrading plots into physical proof |
| `josim-todo-manager` | Read or update evidence-backed task status and dependencies |
| `josim-project-summary` | Persist summaries, handovers, memory and material history |
| `josim-skill-router` | Route broad tasks that span several of the workflows above |

The repository-wide invariants are in `AGENTS.md`; the full delegation protocol is in `research/WORKFLOW.md`. Do not require external plugin skills unless they are actually available in the current runtime.

## Claude ↔ Codex mailbox

For informal async messages between Claude and Codex (questions, clarifications, status sync, reminders), use `research/mailbox/` — see its `README.md`. Run `python3 research/mailbox/scripts/mailbox.py list` at session start to check for Codex messages. Formal contract actions still go through `josim-handoff` protocol files under `research/tasks/<task-id>/`; mailbox messages carry no contract authority.
