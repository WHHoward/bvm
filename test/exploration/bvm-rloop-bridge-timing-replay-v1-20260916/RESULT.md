# BVM R-loop bridge timing replay (bvm-rloop-bridge-timing-replay-v1-20260916)

- Status: `ANALYSIS_COMPLETE`
- Artifact status: `VALID`
- Scientific interpretation: `NOT_PERFORMED`; independent scientific review: `NOT_PERFORMED`.
- Mechanical gate/outcome: `PASS` / `NOT_ASSIGNED`.
- HEAD: `3523c8c6edfaeb2b880302cf2281857134501774`; topology is canonical BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> terminal.
- Intervention: per-instance ideal bridge-current forcing from node 6 to node 10; this is a counterfactual replay, not a physical device design.

## Registered solves

| run | mask | delay (ps) | ordered QB/JTL candidates | BJ1 +0.5 (ps) | BJ2 +0.5 (ps) | BJ1 +1.5 (ps) | BJ2 +1.5 (ps) |
|---|---|---:|---:|---:|---:|---:|---:|
| `EXACT_0011` | 0011 | 0 | 2 | 115.2 | 116.1 | 125.9 | 126.4 |
| `EXACT_0111` | 0111 | 0 | 4 | 113.8 | 114.8 | 117.4 | 118.3 |
| `DELAY0P3_0011` | 0011 | 0.3 | 2 | 115.1 | 115.9 | 124 | 124.5 |
| `DELAY0P3_0111` | 0111 | 0.3 | 4 | 113.8 | 114.8 | 117.9 | 119.1 |
| `DELAY0P6_0011` | 0011 | 0.6 | 2 | 115.1 | 115.8 | 123.3 | 124.2 |
| `DELAY0P6_0111` | 0111 | 0.6 | 4 | 113.9 | 114.8 | 117.6 | 118.5 |

## Exact replay fidelity

The exact screen uses the pre-registered mechanical thresholds (timing 0.2 ps, JS1/JS2 focus p2p 0.25 turns, key-waveform normalized RMS 0.50). Actual errors, bridge differential voltage, source injection error, JM1/JM2, QB, JSL, JTL, terminal, and same-JJ phase/area data remain in `provenance.json`.

P(...) raw values are radians. Displayed turns are only independent continuous-unwrapped rad/(2*pi) navigation values, never SFQ counts. Terminal traces are corroboration only.

## Bridge sign and voltage evidence

Canonical bridge current is `I(R_S)+I(L_S3)` with positive direction node6 -> node10. Canonical `V(R_S)=V(L_S3)` and node6/node10 KCL were checked before deck generation. Replay bridge voltage is derived as `V(6)-V(10)` and is not silently treated as equal to canonical branch voltage.

## Scientific boundary

The artifact does not assign `FEEDBACK_PATH_TIMING_SELECTIVITY_SUPPORTED`, `BRIDGE_TIMING_NONSELECTIVE`, or `BRIDGE_CURRENT_TIMING_INSUFFICIENT`. Those require explicit scientific review. This replay does not prove current is the unique sufficient state variable, a physical delay implementation, or a physical R_S/L_S3 equivalent.

Previous QBIN-boundary replay, static LS3 intervention, and TLINE Z0 rescue results are referenced by hash in `provenance.json`; they are not modified or repackaged here.

- Standalone and comparison descriptive plots: `plots/`.
- Mechanical QA/reviews/transformation/source manifests: `analysis/`.
- Per-run deck/raw/metadata/log: `runs/`.
- PWL source data: `inputs/replay_sources/`.
- Raw evidence ZIP: Drive-only; delivery identity is outside the ZIP in `delivery_manifest.json`.

Stop marker: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
