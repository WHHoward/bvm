# M11A preflight — Measurement Calibration Baseline

## Authority and scope

- Parent authority: `memory/project-todo.md` M11; both M11A and M11B must be
  independently accepted before M11 may be marked complete.
- This is a `CALIBRATION`, `CRITICAL`, `FROZEN` documentation and evidence-index
  task.  It does not run JoSIM, create a candidate criterion, or define
  `INTERFACE_GATE_V1`.
- Only the final accepted/superseding M4--M10 evidence may be accepted as the
  baseline. Historical `REWORK_REQUIRED`, rejected, and superseded attempts are
  lineage only, never acceptance evidence.

## Required accepted inputs

| Layer | Sole accepted evidence | What it contributes | Limit retained |
|---|---|---|---|
| M4 | `JH-20260811-M4-003/audits/C01/verdict.yaml` | raw-radian to turns and activity naming | activity is not an event |
| M5 | `M5-LITE-PILOT-001/attempts/A02/CODEX-AUDIT.md` | windows, direction, matched control, clustering | no physical Gate |
| M6 | `JH-20260812-M6-002/audits/C01/verdict.yaml` | DCSFQ direct same-JJ P/V and actual-time area | residual is reported, not globally accepted |
| M7 | `M7-LITE-001/attempts/A02/CODEX-AUDIT.md` | synthetic oracle, canonical JTL fixture, historical regression | fixture is not a receiver Gate |
| M8 | `JH-20260812-M8-002/audits/C01/verdict.yaml` | bounded 0.1/0.05/0.025 ps convergence | loaded canonical-JTL fixture only |
| M9 | `JH-20260813-M9-004/audits/C01/verdict.yaml` | frozen metric semantics | no universal tolerance or Gate |
| M10 | `JH-20260813-M10-004/audits/C01/verdict.yaml` | historical endpoint arithmetic/provenance | no same-JJ/physical inference |

`docs/research/METRIC_SPEC_V2.md` v2.0.0 is bound by its current file hash.
The executor must verify every recorded input hash and record the verification
result in an immutable attempt-local manifest.

## Non-negotiable boundary

M11A may freeze only the calibration evidence ledger: implementation and
reporting semantics, fixture-bounded convergence, and historical endpoint
arithmetic/provenance. Universal activity, integer, phase-area, platform,
BVM-drift, amplitude, and jitter tolerances remain `UNFROZEN`; any physical
classification depending on them remains `INCONCLUSIVE`.

