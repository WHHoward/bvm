---
name: josim-experiment
description: Design or run bounded JoSIM/BVM QUICK or NORMAL experiments, or explicitly authorized FORMAL experiments. Use for circuit changes or new raw data; scientific interpretation remains separate.
---

# JoSIM/BVM Experiment Executor

Use this skill for authorized circuit edits, render/static checks, physical
solves, and repair of analysis against existing raw. It does not authorize
scientific interpretation or follow-up work.

## Minimal bootstrap

For ordinary BVM execution, read:

1. `memory/EXECUTOR_NOW.md`
2. `memory/BVM_CURRENT_CONTEXT.md`
3. the active platform README and env/config

`memory/LUNA_EXECUTOR_MEMORY.md` is an optional historical execution/package
reference, not routine startup context. Binding evidence rules are in
`docs/EXPERIMENT_CONTRACT.md`; the current standard lifecycle is in
`docs/research/EXPERIMENT_WORKFLOW_V1.md`. `docs/research/COMPACT_WORKFLOW_V2.md`
is historical compatibility material.

Reuse the active platform and `USER_CASE.env`/presets. Run exactly the authorized
case set. If a valid raw already exists, fix its parser/analysis/report/plot
without another solver run. Preserve decks, failures and raw. Separate solver
execution, artifact validity, arithmetic, physical evidence, and scientific
interpretation.

Do not load scientific-audit, reviewer, or handoff skills for routine execution.
Use `josim-evidence-audit` only for requested physical/SFQ interpretation,
`josim-viz` when focused visualization is required, `josim-submit` when
submission/package is requested or required, and `josim-handoff` for an actual
Codex–Claude contract.

## Experiment risk level

Register `experiment_risk_level: QUICK | NORMAL | FORMAL` in each new work unit's
preflight. This is distinct from the research tier
`Exploration/Candidate/Authority` and collaboration risk `NORMAL/CRITICAL`; it
grants neither additional solves nor scientific interpretation.

- `QUICK`: small parameter or stimulus changes for a bounded directional check.
- `NORMAL`: new topology, 4×4 arrays, or multi-stage links; freeze a
  claim-relevant focus probe set and risk-proportionate checks before solving.
- `FORMAL`: Authority, Gate, metric freeze, route decision, or paper-level
  quantitative claim; read `references/run-protocol.md` and preserve full
  claim-relevant coverage, required controls/convergence, and independent audit.

The generic `scripts/bvm-exp.py` runner currently supports QUICK only. Do not
label its QUICK output as NORMAL or FORMAL. A custom platform may register
NORMAL in its own preflight and manifest. All risk levels still require exact
run authorization, immutable raw/provenance, required QA and package integrity.

QUICK/NORMAL may use pre-registered focus probes, one compact classic figure set
per run, consolidated canonical QA records without duplicate calculations, and
one detached PACKAGE_QA per final ZIP version. These efficiencies may not remove
raw data, required provenance, claim-relevant same-JJ evidence, registered
controls, or any contract QA category. FORMAL requirements remain unchanged.

## Validation by question

| Change or claim | Registered validation emphasis |
|---|---|
| Small parameter/stimulus change | Raw QA and target waveform/arithmetic |
| New topology or node reconnection | Static topology/connectivity and focused tests |
| Circuit migration | One equivalence comparison |
| Shared scientific tool change | Focused tests and frozen anchors |
| QB→JTL propagation evidence | Same-JJ phase/area and stage-by-stage boundary evidence |
| FORMAL/Gate/paper claim | Frozen controls, convergence, provenance, independent audit |

Do not add unrelated sweeps, timestep ladders, controls, dashboards, or repeated
QA for ceremony. Missing required evidence limits the result to UNKNOWN or
INCONCLUSIVE; never fill a gap by inference.

## Measurement boundaries

- JoSIM `P(...)` is radians. `phase_delta/(2*pi)` is navigation arithmetic,
  never an SFQ or fluxoid count.
- Do not infer JJ switching from `I > Ic`, or transmitted events from one local
  phase/voltage observation. Use evidence-audit only when scientific
  interpretation is explicitly requested.
- Artifact QA failure is `ARTIFACT_INVALID`, not physical `FAIL`. Keep `PASS`,
  `FAIL`, and `INCONCLUSIVE` distinct.
- Do not overwrite raw, sweep, upgrade risk tier, change route, or start a
  follow-up from a result. Stop at the requested delivery / user review.
