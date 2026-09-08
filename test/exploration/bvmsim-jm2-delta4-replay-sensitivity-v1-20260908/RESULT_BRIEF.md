# RESULT_BRIEF — delta4 replay sensitivity

## Experiment identity

bvmsim-jm2-delta4-replay-sensitivity-v1-20260908, EXPLORATION / QUICK,
HEAD 2a3e3caeaefd511aa6e555dff18e596bd968f3a2. The receiver is the frozen
ideal-current replay I_REPLAY 0 QBIN -> BQ -> JTL1-JTL6 -> 10 ohm.
The source is the matched passive N3/N4 I(B_JSL8) snapshot pair.

delta_I4 = I_N4_PASSIVE(B_JSL8) - I_N3_PASSIVE(B_JSL8) is only a
marginal source contribution / mathematical counterfactual component. It is
not an independent SFQ, independent BVM source, physically separable pulse or
circuit-equivalent source reconstruction.

## Exact run matrix

| run | transformation | execution |
|---|---|---|
| DELTA4_DELAY_3PS | I_N3(t) + delta_I4(t - 3 ps) | PASS |
| DELTA4_DELAY_6PS | I_N3(t) + delta_I4(t - 6 ps) | PASS |
| DELTA4_GAIN_1P25 | I_N3(t) + 1.25 * delta_I4(t) | PASS |
| DELTA4_GAIN_1P50 | I_N3(t) + 1.50 * delta_I4(t) | PASS |

N3_REPLAY and N4_REPLAY are immutable controls and were not rerun. No other
condition was executed.

## QA status

OBSERVED: all four new raw files are valid 69-column outputs with 2059
samples through 205.9 ps; full QB internal probes and JTL1-JTL6 B01/B02 P/V/I
plus stage outputs are present. Solver is build/josim-cli,
v2.7.2837d13, SHA-256
48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2.

DERIVED: N3/N4 source snapshots share the same 1999-sample actual Decimal
grid, including the 14.7 to 14.9 ps gap. The exact source reconstruction
check has zero Decimal residual at all 1999 timestamps. Delay shifts use
exact timestamp lookup; missing or out-of-range delta values are zero. Gains
scale signed delta values without rectification, clipping or reshaping.

Raw hash before/after analysis is unchanged for all new runs and immutable
controls. The source reconstruction, independent standard-library
mechanical check and visualization QA are all PASS.

## Findings

OBSERVED: DELTA4_DELAY_3PS has internal activity that overlaps the fixed
third-response reference, but no separable BJ2 candidate. DELTA4_DELAY_6PS
has one separable BJ2 activity candidate after the fixed reference guard, but
the registered QBIN to BJ1 to BJ2 to QBOUT activity order is not established
and no subsequent complete QBOUT to JTL1 through JTL6 to termination activity
chain is established.

OBSERVED: neither DELTA4_GAIN_1P25 nor DELTA4_GAIN_1P50 has a separable
BJ2 activity candidate after the fixed reference guard. Neither has a
registered complete internal or downstream progression.

DERIVED: same-JJ phase and direct voltage-area arithmetic for BJS, BJ1, BJ2,
JTL1 B01 and JTL6 B01 is mutually consistent within the fixed
QB_INTERNAL_CRITICAL=[118,140) ps window under the registered tolerances.
This fixed-window arithmetic does not isolate a fourth event.

BOUNDED_RESULT: the delay family does not satisfy the preregistered
two-run complete-progression criterion, and the gain family does not satisfy
it either. The strongest current classification is
MIXED_OR_UNRESOLVED. A single DELAY_6PS partial BJ2 candidate is bounded
activity evidence, not recovery proof.

## Unknowns and ceiling

UNKNOWN: this batch does not uniquely separate timing/recovery,
front-end/effective-stimulus and internal-regeneration limitations.
Timestep convergence, parameter sensitivity, solver sensitivity, hardware
behavior and any universal mechanism remain unknown.

No phase turn, voltage peak, voltage/current area, threshold cluster or
terminal trace is reported as an SFQ count. No root-cause, dead-time,
saturation, physical BVM closure, formal SFQ PASS or T1 conclusion is made.
The replay remains an ideal waveform-sufficiency oracle.

## Evidence

Machine analysis: [analysis/metrics.json](analysis/metrics.json).

Source reconstruction: [analysis/source_reconstruction.json](analysis/source_reconstruction.json).

Transformation registry: [analysis/transformation_registry.json](analysis/transformation_registry.json).

Independent check: [analysis/independent_check.json](analysis/independent_check.json).

Visualization QA: [analysis/viz_qa.json](analysis/viz_qa.json).

Each run has standalone QB and JTL pages:

- [DELTA4_DELAY_3PS QB](plots/delta4_v1/DELTA4_DELAY_3PS_QB_FULL_INTERNAL.html)
- [DELTA4_DELAY_3PS JTL](plots/delta4_v1/DELTA4_DELAY_3PS_JTL_FULL_CHAIN.html)
- [DELTA4_DELAY_6PS QB](plots/delta4_v1/DELTA4_DELAY_6PS_QB_FULL_INTERNAL.html)
- [DELTA4_DELAY_6PS JTL](plots/delta4_v1/DELTA4_DELAY_6PS_JTL_FULL_CHAIN.html)
- [DELTA4_GAIN_1P25 QB](plots/delta4_v1/DELTA4_GAIN_1P25_QB_FULL_INTERNAL.html)
- [DELTA4_GAIN_1P25 JTL](plots/delta4_v1/DELTA4_GAIN_1P25_JTL_FULL_CHAIN.html)
- [DELTA4_GAIN_1P50 QB](plots/delta4_v1/DELTA4_GAIN_1P50_QB_FULL_INTERNAL.html)
- [DELTA4_GAIN_1P50 JTL](plots/delta4_v1/DELTA4_GAIN_1P50_JTL_FULL_CHAIN.html)

Comparison and critical pages:

- [DELTA4 source components](plots/delta4_v1/DELTA4_SOURCE_COMPONENTS.html)
- [controls vs interventions QB](plots/delta4_v1/CONTROLS_VS_INTERVENTIONS_QB.html)
- [controls vs interventions JTL](plots/delta4_v1/CONTROLS_VS_INTERVENTIONS_JTL.html)
- [QB internal critical zoom](plots/delta4_v1/QB_INTERNAL_CRITICAL_ZOOM_118_140.html)
- [JTL downstream zoom](plots/delta4_v1/JTL_DOWNSTREAM_ZOOM_118_180.html)

After this package is complete, status is AWAITING_USER_REVIEW. No
N5/N6, parameter tuning, sweep, convergence run, physical BVM rerun or T1
starts automatically.
