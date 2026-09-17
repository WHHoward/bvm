# Current QB transformer isolation — bvm-qb-transformer-isolation-current-qb-v1-20260917

- Status: `ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW`
- Artifact status: `VALID`
- Scientific interpretation: `NOT_PERFORMED`; review remains required.
- Frozen interface: R_PRI=12.0 ohm, L_PRI=0.2 pH, L_SEC=2.0 pH, K=0.5, M=0.31622777 pH.

| run | mask | M (pH) | ordered phase chains | BJ1 first/second (ps) | BJ2 first/second (ps) | mechanical label |
|---|---|---:|---:|---|---|---|
| `ISO_R6A_0011` | 0011 | 0.31622777 | 0 | —/— | —/— | `ISOLATION_EFFECTIVE_FORWARD_MARGIN_INSUFFICIENT` |
| `ISO_R6A_0111` | 0111 | 0.31622777 | 0 | —/— | —/— | `ISOLATION_EFFECTIVE_FORWARD_MARGIN_INSUFFICIENT` |

Transformer primary/secondary I/V, power and timing records; active JS1/JS2 same-JJ phase/area checks; LS3/RS, COMMON_SL, JSL, QB and JTL records are in `analysis/mechanical_analysis.json`.
Replay/interface branch current is recorded according to its element orientation; no directional-isolation or physical-equivalence conclusion is assigned.
P(...) remains raw radians; rad/(2*pi) is navigation only, not an SFQ count.

Stop marker: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
