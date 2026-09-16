# BVM -> QB TLINE Z0 rescue gate (bvm-qb-tline-z0-rescue-gate-v1-20260916)

- Status: `ANALYSIS_COMPLETE`
- Outcome: `TLINE_Z0_RESCUE_FAILED` (FAIL)
- Bounded answer: Both registered Z0=12 and Z0=24 N2 cases fail the preregistered rescue gate; no additional Z0 point or N3 case is authorized.
- HEAD: `ad15dc5abd26d12b618451f9358211ef90b3fa80`; topology remains `B_JSL8 -> TLINE_IN -> ideal lossless TLINE -> QBIN -> canonical QB`.
- Registered new physical solves: N2 `TD=0.3 ps, Z0=12/24 ohm`; at most one conditional N3 at the selected Z0.
- `Z0=12/24 ohm` are engineering diagnostic values, not matching values or measured characteristic impedances.

## N2 rescue gate

Phase is stored as raw radians. Turns are only independent continuous-unwrapped navigation values, not SFQ counts. All recovery metrics use actual stored samples in `[121,130) ps`.

| case | Z0 (ohm) | first BJ1 +0.5 (ps) | first BJ2 +0.5 (ps) | second BJ1 +1.5 (ps) | second BJ2 +1.5 (ps) | ordered chain candidates | L1 sustained -/+ (ps) | L1 positive dwell (ps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `canonical` | — | 115.2 | 116.1 | 125.9 | 126.4 | 2 | 121.7 | 3.7 |
| `previous_Z0_6_TD_0P3` | 6 | 115.5 | 116.4 | — | — | 1 | — | 0 |
| `Z0_12_0011` | 12 | 115.7 | 116.5 | — | — | 1 | — | 0 |
| `Z0_24_0011` | 24 | 116.1 | 116.9 | — | — | 1 | — | 0 |

The ordered-chain oracle is internal `BJ1 -> BJ2 -> JTL1..JTL6`; terminal signals are downstream corroboration only. A second phase-navigation candidate is not called an SFQ count.

## Re-arm, source, and BVM evidence

Detailed `I(L1)`, `I(L2)`, reset-voltage integrals, `I(B_JSL8)`, `I(LIN|XBQ1)`, COMMON_SL, QBIN, JSL1..8, active JS1/JS2, LS3/R_S/LM3/L_SL, and JM1/JM2 records are in `provenance.json.analysis` and `result.json`.
Same-JJ JS1/JS2 phase-area residuals are reported in turns after `rad/(2*pi)` conversion; voltage areas are actual-grid trapezoids and are not event counts.

## Evidence boundary and stop

This is bounded to the registered ideal-lossless-TLINE topology, canonical QB/JTL/terminal, `TD=0.3 ps`, `Z0` in the registered set, `dt=0.1 ps`, and `0–200 ps`. Timestep/solver convergence and physical characteristic impedance remain UNKNOWN.

- Standalone and paired descriptive plots: `plots/`.
- Mechanical/numerical/adversarial records: `analysis/`.
- Raw/deck/log evidence: `runs/`.
- Delivery manifest: `delivery_manifest.json`; raw ZIP is Drive-only.

Stop marker: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
