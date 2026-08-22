# R5-C reduced biased-quantizer correct-saddle selectivity — execution report

**Tier:** Exploration / EXPLORATORY  
**Preregistration:** [`manifest.yaml`](../manifest.yaml)  
**Analytic precheck:** [`R5C_ANALYTIC_PRECHECK.md`](R5C_ANALYTIC_PRECHECK.md)  
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256
`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`  
**Simulation:** `.tran 0.0125p 170p`; four matched cases; one run each; no sweep.

## Verdict

**`R5C_SADDLE_CROSSED_NO_COMPLETE_EVENT` / `FAIL`**

The single point `I_SET_BIAS=9.93 µA` drove read1 B_SET across the correctly
calculated reverse static saddle, but did not produce a complete `2π` monotonic
phase transition. The trajectory remained a bounded multi-lobe oscillation.

The point also caused substantial read1 back-action: B_TRIG activity fell from
the R5-A baseline of about `5.267-turn` range to `2.049-turn`, and JS1/JS2
post-state phase shifted by approximately `−4 turns`. Therefore the R5-C
selectivity criteria fail even though read0 and controls remain event-free.

Per the preregistered stop rule, no further reduced-quantizer bias tuning is
authorized by this Exploration. A native paper-QB-derived bias-routing
topology is elevated as the next candidate direction, but is not designed or
run here.

## Artifact QA

All four raw CSVs are valid for this Exploration:

| Case | Rows | End time | Required columns | Time axis | Finite |
|---|---:|---:|---|---|---|
| read1 | 13,599 | 169.9875 ps | present | strictly increasing | yes |
| read0 | 13,599 | 169.9875 ps | present | strictly increasing | yes |
| logical1 READ=0 | 13,599 | 169.9875 ps | present | strictly increasing | yes |
| logical0 READ=0 | 13,599 | 169.9875 ps | present | strictly increasing | yes |

An initial command-path attempt returned `127` before solver startup and
created no raw. The corrected repository-root commands exited `0`; the
correction is recorded in [`execution-command.txt`](execution-command.txt).

## Static model used

For the R5-C orientation:

\[
 I_{L_QB}=I_b+I_c\sin\phi,
\]

\[
 \phi+\beta_L\left(I_b/I_c+\sin\phi\right)
 +2\pi\frac{M I_{TX}}{\Phi_0}=2\pi n,
\]

with `M=−3.577708764 pH`, `Ic=5 µA`, `L_H=100 pH`, and
`βL=1.51926745`. Static stability is

\[
1+\beta_L\cos\phi>0,
\]

and the reverse saddle is `φs=−2.28923753 rad = −0.36434347 turn`.

At the selected bias, the measured pre-state is `φOP≈−0.23916 turn`, close
to the analytic connected `n=0` solution `−0.23899 turn`. The raw branch
reconstruction

\[
n=\frac{\phi}{2\pi}+\frac{L_H I_{L_QB}+M I_{TX}}{\Phi_0}
\]

stays within about `±3.3×10⁻⁷` during read1 activity, so the phase trajectory
is still on the initial branch before any putative transition.

## B_SET phase trajectory and same-JJ voltage area

The event threshold was one complete monotonic segment with absolute phase
change at least `1.0 turn`. Voltage area uses the actual CSV time column and
direct `V(B_SET|XTRIG)`.

| Case | Activity phase range | Largest monotonic segment | Same-segment area | Residual | Complete event |
|---|---:|---:|---:|---:|---:|
| read1 | `−0.829021…−0.118718 turn` (`0.710303` range) | `−0.678413 turn`, 108.05–112.1375 ps | `−0.678440` | `+2.73×10⁻⁵ turn` | 0 |
| read0 | `−0.331188…−0.174770 turn` (`0.156418` range) | `+0.156418 turn`, 107.025–108.975 ps | `+0.156433` | `−1.54×10⁻⁵ turn` | 0 |
| logical1 READ=0 | approximately `0.0020 turn` range | below event threshold | not applicable | not applicable | 0 |
| logical0 READ=0 | approximately `0.0022 turn` range | below event threshold | not applicable | not applicable | 0 |

Read1 clearly crosses the reverse saddle: its minimum is about
`−0.829021 turn`, well below `−0.364343 turn`. At the deep minimum near
`112.1375 ps`, the trajectory reverses rather than continuing into a complete
monotonic run. The next large segment is `+0.708287 turn` with area
`+0.708326 turn`; this is bounded reversal, not a second event or a completed
slip.

The largest B_SET voltage/current activities were:

| Case | `|V(B_SET)|` peak | `|I(B_SET)|` peak |
|---|---:|---:|
| read1 | `614.39 µV` | `7.61 µA` |
| read0 | `265.87 µV` | `6.27 µA` |
| controls | `≤4.01 µV` | `≤5.02 µA` |

These peaks are activity observations only and were not used as switching
evidence.

## Source transfer and back-action

| Case | B_TRIG activity range | `I_TX` min/max | `Φ_ext/Φ0` min/max |
|---|---:|---:|---:|
| read1 | `2.048655 turn` | `−59.443/+54.090 µA` | `−0.093586/+0.102847` |
| read0 | `0.186247 turn` | `−22.139/+6.623 µA` | `−0.011503/+0.038292` |
| logical1 READ=0 | `5.75×10⁻⁵ turn` | nA scale | `≈±3.5×10⁻⁶` |
| logical0 READ=0 | `2.61×10⁻⁴ turn` | nA scale | `≈±2.6×10⁻⁶` |

Read1/read0 source discrimination remains present, but read1 B_TRIG is no
longer R5-A-like: R5-A read1 range was about `5.267 turn`. This is bounded but
material receiver back-action, not a preserved source guard.

SL/N6 read1/read0 transient separation remains visible (`1.739/0.446 mV`
and `1.927/0.724 mV` peak magnitudes respectively), while the storage probes
show:

| Storage probe | read1 pre→post median shift | controls/read0 |
|---|---:|---|
| JM1 | `+3.40×10⁻⁵ turn` | signs preserved |
| JM2 | `+0.00134 turn` | signs preserved |
| JS1 | `−3.99962 turn` | no comparable shift |
| JS2 | `−3.99932 turn` | no comparable shift |

`I(R_GAUGE)` remained at approximately `1.13×10⁻²¹ A` peak, so the gauge
element did not cause the observed effect. The read1 JS1/JS2 shifts are a
receiver-induced BVM back-action failure, even though JM1/JM2 logical signs
remain recognizable.

## Post behavior

- B_SET read1 post-window phase p2p: `0.05518 turn`; post voltage peak:
  `109.16 µV`.
- B_SET read0 post-window phase p2p: `0.02229 turn`; post voltage peak:
  `40.97 µV`.
- No case shows a complete second B_SET segment or free-running output.

The local quantizer returns to a bounded oscillatory state, but no primary
event occurred, so the preregistered event-after-retrap criterion is not a
PASS criterion here.

## Observed / Derived / Inference / Unknown

### Observed

- All four artifacts are finite and complete.
- Read1 crosses the corrected reverse saddle but has no `≥1-turn` monotonic
  B_SET segment.
- Same-JJ phase and voltage-area values agree for the largest bounded segments.
- Read0 and both controls have zero complete B_SET segments.
- B_TRIG remains state-dependent but is strongly loaded on read1.
- JS1/JS2 read1 post-state shifts by approximately four turns.

### Derived

- The point is not limited by a static critical-current threshold: a true loop
  saddle was crossed without escape.
- The dominant observed failure is bounded inertial/plasma oscillation with
  alternating phase segments, compounded by source/storage back-action.
- The local reduced quantizer cannot be promoted to selective output behavior
  at this single point.

### Inference

The missing function is no longer plausibly supplied by bias placement alone.
The result is consistent with a need for a native bias-routing/load-line or
irreversibility mechanism, but R5-C does not prove that the full paper QB is the
only possible implementation.

### Unknown

- No timestep convergence was run; this is Exploration evidence at `0.0125 ps`.
- No JTL/T1 was attached.
- The exact causal contribution of B_TRIG loading versus quantizer internal
  damping cannot be separated by this single point.

## Final disposition

`R5C_SADDLE_CROSSED_NO_COMPLETE_EVENT` is a valid bounded physical `FAIL`, not
an artifact failure. Stop reduced biased-quantizer point tuning. The next
user-authorized candidate may be the native paper-QB-derived bias topology;
this report neither designs nor executes it.
