# CODEX AUDIT M7-LITE-001 / A01

Audit disposition: **REWORK_REQUIRED**

Artifact status: **INVALID**
Physical verdict: **NOT_APPLICABLE**
Claim ceiling: unchanged — calibration implementation and regression only.

## Independent checks

- Re-ran M4/M5/M6/M7 test files in the delivery worktree: **83/83 passed**.
- Independently read the M7B raw CSV and integrated the actual `time` samples in `[6e-12, 50e-12)`: B1 residual `-1.4127550951559265e-4` turns; B2 residual `+1.4129306561221355e-3` turns. These agree with the production comparison and are reported only, not accepted against a tolerance.
- Independently recomputed the frozen DCSFQ control-corrected values: B1 `0.9999999829418391`, B2 `1.0000000625193106`, B3 `1.0000000147728276` turns.
- Independently recomputed BQ v4 JTL-B1 values at the declared nearest actual sample rows: all six predeclared constants match exactly at the test's precision. They remain periodic historical phase-platform regression constants, not physical-event counts or a Gate.
- The canonical JTL netlist's functional circuit/input/load/transient lines agree with `test/standard/test_jtl.cir`; its changed output probes are direct `V(B1|XDUT)`, `V(B2|XDUT)`, `P(B1|XDUT)`, and `P(B2|XDUT)`.

## Why A01 is not accepted

1. **AC3 evidence closure is incomplete.** The TASK requires the canonical run to save an analysis. A01 saves raw CSV, manifest, input copies and run log, but no attempt-local M7B analysis artifact. `RESULT.md` names values narratively but is not a separately preserved run analysis with the selected samples, signed phase/area values and residuals.
2. **AC5 scope evidence is inaccurate.** `attempts/A01/logs/scope-diff.log` lists only three untracked paths, while the delivery snapshot contains additional A01 output paths including `RESULT.md`, the manifest, raw CSV and input snapshots. Therefore it cannot serve as the required before/after allowed-scope diff or demonstrate that all actual changes were checked.

These are artifact/provenance failures, not scientific failures. Copilot's review correctly found no numerical or physical-claim Major issue, but did not detect this delivery-evidence incompleteness.

## Required A02 correction

- Preserve A01 without modification.
- Create `attempts/A02/RESULT.md` with a new Preflight. Do not alter `TASK.md`, the two implementation files, historical inputs, or A01 artifacts.
- Produce an A02-local, immutable analysis document that references the preserved A01 raw file by SHA-256 and records the declared window, first/last selected actual samples, signed phase delta, signed area turns, and residual for B1/B2. It must explicitly retain the no-tolerance/no-event/no-Gate boundary.
- Record a complete scope check against the A02 preflight baseline **after all A02 files exist**, including every changed path or an explicit deterministic command/output that proves no out-of-scope changes. Do not claim that an incomplete early snapshot is the final scope check.
- Preserve command logs and hash the A02 analysis/scope artifacts in the new RESULT. Claude then requests a new review/snapshot for A02.

No new JoSIM run, M8 convergence, metric tolerance, candidate analysis, or physical conclusion is authorized by this rework.
