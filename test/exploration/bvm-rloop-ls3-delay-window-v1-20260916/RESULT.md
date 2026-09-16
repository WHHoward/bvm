# LS3 timing-window closure (bvm-rloop-ls3-delay-window-v1-20260916)

- Status: `ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW`
- Artifact status: `VALID`
- Scientific interpretation: `NOT_PERFORMED`; final classification: `SCIENTIFIC_REVIEW_REQUIRED`.
- Frozen parent: `b904851be588ca88d40cf1700d5fef7ce3d889ed`; exactly four new solves; no N1/N4 or 0.3-ps rerun.
- Fixture: validated LS3-only per-instance ideal current replay; canonical BVM→JSL→QB→JTL→terminal retained.

## Timing-window table

| delay | N2 ordered chains | N3 ordered chains | N2 second response | N3 fourth chain |
|---:|---:|---:|---|---|
| `0.2 ps` | 2 | 4 | preserved | present |
| `0.3 ps` | 2 | 3 | preserved | absent |
| `0.4 ps` | 2 | 3 | preserved | absent |

- Mechanical candidate label: `LS3_TIMING_WINDOW_PARTIAL`.
- Final scientific assignment: `NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED`.
- The 0.3-ps row is read-only prior evidence; no 0.3-ps solve was executed.

## New-run evidence

| run | old strict count | phase chains | JTL6 clusters | terminal clusters | terminal area / Φ0 | first BJ1/BJ2 (ps) | timing drift max (ps) |
|---|---:|---:|---:|---:|---:|---|---:|
| `LS3_DELAY0P2_0011` | 2 | 2 | 2 | 2 | 2 | 115.3/116.2 | 0.5 |
| `LS3_DELAY0P2_0111` | 1 | 4 | 4 | 4 | 4.0000001 | 113.9/114.8 | 0.4 |
| `LS3_DELAY0P4_0011` | 2 | 2 | 2 | 2 | 2 | 115.5/116.3 | 1.7 |
| `LS3_DELAY0P4_0111` | 2 | 3 | 3 | 3 | 3 | 114/114.9 | 1.5 |

### N3 response chains

| run | response 1 | response 2 | response 3 | response 4 |
|---|---|---|---|---|
| `LS3_DELAY0P2_0111` | complete | complete | complete | complete |
| `LS3_DELAY0P4_0111` | complete | complete | complete | missing BJ1 |

N2/N3 active JS1/JS2 p2p, L1 re-arm, JSL8 signed/re-arm behavior, same-JJ phase-area arithmetic, normalized waveform deltas, source-injection error and all stage data are in `analysis/mechanical_analysis.json`. Phase is raw radians; turns are navigation only. Navigation count and voltage area are not literal SFQ counts.

Stop marker: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
