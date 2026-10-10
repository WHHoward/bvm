# A040/A041 evidence manifest

Batch: `BVM4X4_D3_CARRY_TIMING_20261010`
Status: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`
Physical solves: exactly 2 new solves; A036 is read-only reference evidence.

## Registered inputs

- Current locked PREFLIGHT: [attempt 003](attempts/003/PREFLIGHT.md), SHA-256 recorded in [WORK_UNIT.json](attempts/003/WORK_UNIT.json).
- Attempts 001 and 002 are preserved and explicitly superseded before any solve; see [REVISION_NOTE.md](REVISION_NOTE.md) and [attempt 003 REVIEW.md](attempts/003/REVIEW.md).
- Experiment definition: [experiment.yaml](experiment.yaml).
- Machine batch and probe/metric registrations: [BATCH_MANIFEST.json](attempts/003/BATCH_MANIFEST.json), [PROBE_MANIFEST.json](attempts/003/PROBE_MANIFEST.json), [METRIC_SPEC.json](attempts/003/METRIC_SPEC.json).
- Canonical/run-local source closure: [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json).
- No-transform declaration: [TRANSFORMATION_REGISTRY.json](TRANSFORMATION_REGISTRY.json).

## New immutable runs

| Run | Effective D3 Carry branch | Raw SHA-256 | Raw bytes | QA |
|---|---|---|---:|---|
| A040_D3_PRE_CB_SJTL_0_ALL_200 | `C_D2 → CB_0928 → JOIN_D3` | `3c3ec6904b900e6a3a2c8bbac82431eca05150b3aad58c52feec10b29bf7ae61` | 85,514,801 | `VALID / PASS` |
| A041_D3_PRE_CB_SJTL_2_ALL_200 | `C_D2 → sJTL_1 → interstage sensor → sJTL_2 → CB_0928 → JOIN_D3` | `e1037690671ff9457b9e032a65332cedf6d0c4f93af55ae44dfc3124521d7792` | 89,494,895 | `VALID / PASS` |

Each run directory contains the executed `deck.cir`, `stimulus.inc`, USER_CASE/STIMULUS/T1/CBU/DFF/D0-JTL snapshots, run-local source snapshots, source/topology/probe/stimulus manifests, raw, stdout/stderr, run log, metadata/provenance, metrics, raw/chain/static/plot QA, and result brief. A040/A041 use 212/222 probes respectively. Both store 29,999 rows from 0 to 299.99 ps with actual Δt 0.01–0.02 ps.

## Mechanical arithmetic and plots

- [D3_CARRY_TIMING_SUMMARY.md](D3_CARRY_TIMING_SUMMARY.md)
- [D3_CARRY_TIMING_SIGNAL_METRICS.csv](D3_CARRY_TIMING_SIGNAL_METRICS.csv)
- [D3_CARRY_TIMING_SAME_JJ_PHASE_AREA.csv](D3_CARRY_TIMING_SAME_JJ_PHASE_AREA.csv)
- [D3_CARRY_TIMING_STAGE_METRICS.csv](D3_CARRY_TIMING_STAGE_METRICS.csv)
- [D3_CARRY_TIMING_VISUALIZATION_QA.json](D3_CARRY_TIMING_VISUALIZATION_QA.json)
- [VISUALIZATION_MANIFEST.json](VISUALIZATION_MANIFEST.json)

Local Plotly pages (not included in the evidence ZIP):

- `plots/comparison/A036_A040_A041_D3_FOCUS.html`
- `plots/comparison/A040_A041_D3_EXTENDED_JJ.html`
- `plots/comparison/A036_A040_A041_D3_CARRY_PATH.html`
- `plots/comparison/A036_A040_A041_FULL_CHAIN.html`
- `plots/comparison/A036_A040_A041_OUTPUTS_DFF.html`
- Each new run has its standalone classic chain pages under `runs/<run_id>/plots/`.

`P(...)` remains raw radians; all phase/2π values are navigation arithmetic only. Same-JJ voltage-area cross-checks use identical raw rows and windows. `V(DOUT_D3)`/`V(CBU_JOIN_D3)` is a source-mixed shared boundary and is not interpreted as an array-only event count. No event/SFQ classification or physical mechanism interpretation was performed.

## Archive policy

The DELTA package includes only the A040/A041 source/config/provenance/QA/analysis additions plus their raw files; A001–A039 raw files are SHA-referenced, not copied again. Generated HTML remains local. The detached `PACKAGE_QA.json`, ZIP SHA-256 values, mirror SHA values, commit, push, and Drive verification are recorded after packaging.
