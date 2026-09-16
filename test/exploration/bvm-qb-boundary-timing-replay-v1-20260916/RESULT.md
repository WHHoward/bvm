# BVM -> QB boundary timing replay (bvm-qb-boundary-timing-replay-v1-20260916)

- Status: EXACT_ONLY_COMPLETE_REVIEW_GATED
- Final state: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
- Scientific interpretation: NOT_PERFORMED; this is an evidence handoff for review.
- Physical solves: EXACT_N3 = 1; DELAY_0P6 = 0; DELAY_1P2 = 0.
- Fixture: 4 BVM -> COMMON_SL -> 8 JSL -> QBIN ideal voltage replay; QB/JTL/terminal removed.
- Replay authority: canonical no-shunt N3 `0111` raw `V(QBIN)` only; exact stored samples, no interpolation.

## Registered observations and arithmetic

The following are raw observations or registered arithmetic. They do not assign a mechanism, SFQ count, or physical equivalence.

- Stored-grid equality: `True`.
- Replay source points: `1999`.
- `V(QBIN)` source/output consistency is recorded in `result.json` under `fidelity.input_boundary`.

### Phase navigation landmarks

`P(...)` raw values are radians. The displayed turns below use independent continuous unwrap and rad/(2*pi), for navigation only; they are not SFQ counts.

| signal | source -0.5 turn crossing (ps) | EXACT -0.5 turn crossing (ps) | source [110,121) p2p (turns) | EXACT [110,121) p2p (turns) |
|---|---:|---:|---:|---:|
| `P(B_JS1|XBVM2)` | 113.4 | 113.4 | 6.3864044 | 6.3864044 |
| `P(B_JS2|XBVM2)` | 112.4 | 112.4 | 6.3605665 | 6.3605665 |
| `P(B_JS1|XBVM3)` | 113.4 | 113.4 | 6.3864044 | 6.3864044 |
| `P(B_JS2|XBVM3)` | 112.4 | 112.4 | 6.3605665 | 6.3605665 |
| `P(B_JS1|XBVM4)` | 113.4 | 113.4 | 6.3864044 | 6.3864044 |
| `P(B_JS2|XBVM4)` | 112.4 | 112.4 | 6.3605665 | 6.3605665 |

### Same-JJ JS1/JS2 phase-area cross-check

The voltage area uses the actual stored timestamps and the same JJ/endpoints/direction as the phase trace. The residual is a numerical cross-check, not an event count.

| signal | source phase delta (turns) | source V-area/Phi0 (turns) | EXACT phase delta (turns) | EXACT V-area/Phi0 (turns) |
|---|---:|---:|---:|---:|
| `P(B_JS1|XBVM2)` | -6.3528459 | -6.3551239 | -6.3528459 | -6.3551239 |
| `P(B_JS2|XBVM2)` | -6.3323218 | -6.3340876 | -6.3323218 | -6.3340876 |
| `P(B_JS1|XBVM3)` | -6.3528459 | -6.3551239 | -6.3528459 | -6.3551239 |
| `P(B_JS2|XBVM3)` | -6.3323218 | -6.3340876 | -6.3323218 | -6.3340876 |
| `P(B_JS1|XBVM4)` | -6.3528459 | -6.3551239 | -6.3528459 | -6.3551239 |
| `P(B_JS2|XBVM4)` | -6.3323218 | -6.3340876 | -6.3323218 | -6.3340876 |

## Review questions retained

The requested extra-JS1/JS2 timing, read p2p contraction, JSL/source regeneration, and JM1/JM2 follower questions remain explicitly review-gated. The raw navigation and full signal deltas are in `result.json`; the delayed cases were not run.

- Canonical QB-only feedback traces (`L1`, `BJ1`, `BJ2`) are reference-only; they are not present in the replay fixture.
- `I(V_REPLAY)` is the ideal forcing-source branch current and is not a canonical source-current substitute.
- Convergence, SFQ event identity/count, mechanism, and physical equivalence are `UNKNOWN`.

## Evidence paths

- Run raw/deck/log: `runs/EXACT_N3/`.
- Standalone full-window plots: `plots/EXACT_N3/`.
- Canonical-vs-EXACT comparison plots: `plots/comparisons/`.
- Machine evidence: `provenance.json` and `result.json`.
- Raw evidence ZIP: Drive only; no ZIP is stored in this repository.

Stop marker: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
