# Independent review — A001 T1 CLK-only

## Scope

Mechanical and registered arithmetic review only. This is one isolated Scheme-B
T1 run with `I=0`; the input is a periodic ideal voltage source through a 5 Ω
series resistor. It is not an SFQ-clock validation. No integrated array run,
parameter sweep, or scientific mechanism interpretation was performed.

## Artifact and provenance checks

- Solver: `build/josim-cli`, `v2.7.2837d13`, exit code 0; physical solve count 1.
- Parent HEAD: `e1b7355f39ce7b9e8cb7d4c216bdbb398a99cc3c`.
- T1 source SHA-256: `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237`;
  JJMIT model SHA-256: `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`.
- Raw: `runs/A001_T1_CLK_ONLY/raw.csv`; SHA-256
  `d834fc11ff719ed15b20b55690e149e64deca4ac6fca2c4ff2758556d184834b`;
  36,999 rows, time range 0–369.99 ps, observed stored increments 0.01–0.02 ps
  (nonuniform). Raw SHA was unchanged through analysis and plotting.
- Raw, provenance, mechanical, and classic plot QA: PASS. The full-run page has
  15 traces; four registered cycle pages each have 15 traces. HTML is derived
  and excluded from the default evidence ZIP.
- Independent stdlib CSV recomputation used Decimal raw-time membership,
  full-trace phase unwrap, and trapezoids on actual stored time values. Cycle
  row counts/endpoints and all recomputed phase, JJ-area, and S/C-area values
  match the generated metrics exactly (maximum arithmetic difference 0 in the
  independent recomputation).

## Registered clock measurements

The source is configured for 1.2 mV, 1 ps rise, 2 ps width, 1 ps fall, at
170/220/270/320 ps. Arrival brackets below are first stored-sample half-peak
navigation markers; no interpolation was used. `I(R_TRIG_CLK)` is only the
current in this ideal-source series branch.

| Cycle | `V(CLK_RAW)` peak / time | Source half-peak bracket | `V(CLK)` peak / time | CLK half-peak bracket | `I(R_TRIG_CLK)` max / min |
|---|---|---|---|---|---|
| 1 | 1.200 mV / 171.00 ps | 170.49–170.50 ps | 0.898942 mV / 174.61 ps | 173.94–173.95 ps | +192.257 / −179.788 µA |
| 2 | 1.200 mV / 221.00 ps | 220.49–220.50 ps | 0.898942 mV / 224.61 ps | 223.94–223.95 ps | +192.257 / −179.788 µA |
| 3 | 1.200 mV / 271.00 ps | 270.50–270.51 ps | 0.898942 mV / 274.61 ps | 273.94–273.95 ps | +192.257 / −179.788 µA |
| 4 | 1.200 mV / 321.00 ps | 320.50–320.51 ps | 0.898942 mV / 324.61 ps | 323.94–323.95 ps | +192.257 / −179.788 µA |

## Junction and output arithmetic

Each junction cell reports `Δφ` in raw radians and the same-junction,
same-window trapezoidal `∫Vdt/Φ0`. `Δφ/(2π)` is also present in the machine
metrics as navigation arithmetic only; none of these values is an SFQ count.

| Cycle | J2 `Δφ rad / area Φ0` | J3 `Δφ rad / area Φ0` | J7 `Δφ rad / area Φ0` | J9 `Δφ rad / area Φ0` | J11 `Δφ rad / area Φ0` |
|---|---:|---:|---:|---:|---:|
| 1 | 6.2831856 / 0.999999992 | 6.2831848 / 1.000000002 | 1.00e−7 / 1.972e−8 | 0 / 1.888e−8 | −2.60e−7 / −4.154e−8 |
| 2 | 6.2831800 / 0.999999988 | 6.2831830 / 0.999999991 | −1.00e−8 / −1.937e−9 | −1.00e−7 / −3.134e−10 | 0 / −9.675e−10 |
| 3 | 6.2831900 / 0.999999988 | 6.2831900 / 0.999999991 | −1.00e−8 / −1.890e−9 | −1.00e−7 / −3.158e−10 | 0 / −9.671e−10 |
| 4 | 6.2831900 / 0.999999988 | 6.2831800 / 0.999999991 | −1.00e−8 / −1.890e−9 | −1.00e−7 / −3.155e−10 | 0 / −9.671e−10 |

Maximum absolute same-JJ phase-turn minus area/Φ0 arithmetic difference over
these windows is approximately `8.36e−7` turns. No post-hoc tolerance or
pass/fail threshold was applied.

| Cycle | `V(S)` min…max; p-p; signed area | `V(C)` min…max; p-p; signed area |
|---|---|---|
| 1 | −0.664398…+0.412719 mV; 1.077117 mV; −2.2510e−23 V·s | −24.3157…+17.3329 µV; 41.6486 µV; −9.2026e−23 V·s |
| 2 | −0.664398…+0.412719 mV; 1.077117 mV; −1.3143e−23 V·s | −24.3156…+17.3330 µV; 41.6486 µV; −1.1708e−24 V·s |
| 3 | −0.664398…+0.412719 mV; 1.077117 mV; −1.3147e−23 V·s | −24.3156…+17.3330 µV; 41.6486 µV; −1.1721e−24 V·s |
| 4 | −0.664398…+0.412719 mV; 1.077117 mV; −1.3146e−23 V·s | −24.3156…+17.3330 µV; 41.6486 µV; −1.1723e−24 V·s |

## Pre-clock and inter-pulse observations

- In `[150,170)` ps (2,000 stored rows), `V(CLK_RAW)`, `V(S)`, and `V(C)` are
  at numerical zero; the five registered JJ phase endpoint deltas are 0 rad.
- For each `[clock start + 4 ps, next clock start)` tail, the stored waveform
  ranges include `V(CLK)` about 1.01846 mV p-p, `V(S)` about 1.07712 mV p-p,
  and `V(C)` about 41.6486 µV p-p. At the last sample before the next period,
  their respective magnitudes are about 0.096 nV, 0.119 nV, and 0.0355 nV.
- Over that same tail, endpoint phase changes are approximately +2.93287 rad
  for J2 and +5.46751 rad for J3 per period; the remaining registered junction
  deltas are retained in `analysis/clock_cycle_metrics.json`.

These are stored waveform and arithmetic observations only. Timestep
sensitivity, parameter sensitivity, interpretation of internal phase motion,
clock functionality, truth table, and system throughput remain UNKNOWN and
were not tested.

## Adversarial checks

- **Wrong-boundary sample:** exact Decimal comparisons put the sample at 220 ps
  in cycle 2, not cycle 1; each cycle contains 5,000 rows. This check found and
  corrected an earlier float-endpoint selection in derived analysis. Raw was
  unchanged; metrics and plots were regenerated against the same raw with
  `physical_solve_count=0`.
- **Repair-tool failure:** the first same-raw plot rebuild rejected an internal
  Decimal value while serializing its plot manifest. The raw SHA remained
  unchanged. The manifest now serializes only public numeric windows; the
  subsequent same-raw rebuild and all linked QA passed. No second solve ran.
- **Stale/modified raw:** before/after raw hashes agree with the recorded SHA.
- **Wrong topology/quiet shunt:** deck has one T1 instance, grounded `I`, the
  registered pulse source and 5 Ω series resistor; no `R_CLK_QUIET` or
  integrated BVM/QB/CB/sJTL instance.
- **Weak numerical oracle:** independent raw-only computation reproduced the
  registered windows and arithmetic exactly.
- **Overclaim guard:** phase radians, phase/(2π), voltage areas, and ideal
  branch current are not labeled as SFQ counts or validated system behavior.
