# R7-A native-QB L1 single-point routing Exploration

## Verdict

`ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED`

The single registered change, `L1: 3.91 pH -> 2.50 pH`, increases the
control-subtracted read1 routing metrics into `L2` and `BJL2` relative to the
R6-B point, while read0 remains substantially smaller and both READ=0
controls remain inactive. The canonical BVM source/storage guard is preserved
relative to the canonical no-receiver and R6-B baselines.

This is not an `ISOLATED_NATIVE_QB_LOCAL_PASS`: read1 `BJL2` remains a
sub-turn, phase/area-consistent excursion and has no complete local event.
The result is a bounded single-point routing conclusion, not an SFQ-delivery
claim.

## Frozen point and scope

Only native-QB `L1` changed:

```text
L1       = 2.50 pH       (R6-B: 3.91 pH)
L2       = 3.91 pH
R_PRI    = 12 ohm
L_PRI    = 0.20 pH
L_SEC    = 1.00 pH
K        = 0.70710678
native QB topology, JJ AREA, RB/IB, RJ1/RJ2, BVM: unchanged
```

The four matched cases were `read1`, `read0`, `logical1-read0-control`, and
`logical0-read0-control`. The requested timestep was `0.0125 ps`, the stop
time was `170 ps`, and the routing window was the preregistered half-open
`[94,130) ps` interval. No sweep, JTL, or T1 was used.

## Artifact QA

The first launcher attempt is preserved as an artifact-only failure: the raw
case directories did not exist, so JoSIM could not open its output files and
no raw CSV was written. It is not used as scientific data.

The successful `run-02.csv` for every matched case:

- exited with code 0 and produced no stderr output;
- contains 13,599 finite rows and 39 fields;
- covers `0` to `169.9875 ps` with strictly increasing actual time;
- has actual solver intervals from `0.0125` to `0.025 ps`.

The recorded solver is JoSIM `v2.7.2837d13`, binary SHA-256
`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
Raw hashes and all commands are retained in the exploration directory.

## Measurement rule

Raw `P(...)` is in radians. Phase turns are derived as
`phase_delta_rad/(2*pi)`. For each JJ, the largest monotonic segment and the
same-JJ voltage integral use the same `[94,130) ps` window and actual CSV time
axis. A local event requires at least one complete turn with a
phase/area-consistent same-JJ segment. Current or voltage peaks alone are not
event counts.

## Settled operating point

The READ=0 controls settle to the same R7-A point. Values below are medians in
the preregistered pre-window; currents are in microamps and phases in radians.

| quantity | R6-B | R7-A | change |
|---|---:|---:|---:|
| `P(BJs)` | −0.138984 | −0.159009 | −0.020025 |
| `I(BJs)=I(Lin)` | −18.425 | −21.059 | −2.634 |
| `P(BJL1)` | +0.239760 | +0.274190 | +0.034430 |
| `I(BJL1)` | +26.597 | +30.326 | +3.729 |
| `P(BJL2)` | +0.240284 | +0.205760 | −0.034524 |
| `I(BJL2)=I(L2)` | +44.978 | +38.615 | −6.363 |
| `I(L1)` | −45.022 | −51.385 | −6.363 |
| `I(RB)` | +90.000 | +90.000 | 0 |

The static KCL split remains `90 = 51.385 + 38.615 µA`, but it is no longer
approximately the R6-B 45/45 µA L1/L2 split. Therefore the experiment shows a
combined L1 load-line and dynamic-routing effect; it does not isolate a pure
fixed-operating-point AC reactance effect.

## Control-subtracted routing

For each logical state, `delta I_x(t)` is the read waveform minus its matching
READ=0 control. RMS values use `[94,130) ps`.

| case | `RMS(delta I_Lin)` µA | `RMS(delta I_L2)` µA | `G_L2` | `RMS(delta I_BJL2)` µA | `G_BJL2` |
|---|---:|---:|---:|---:|---:|
| R7-A read1 | 3.03805 | 0.74381 | **0.244831** | 0.67046 | **0.220688** |
| R7-A read0 | 0.31810 | 0.14482 | 0.455252 | 0.12916 | 0.406046 |
| R6-B read1 | 3.18705 | 0.61978 | 0.194469 | 0.55738 | 0.174888 |
| R6-B read0 | 0.32928 | 0.11719 | 0.355905 | 0.10416 | 0.316314 |

Relative to R6-B, read1 `G_L2` increases by about `25.9%` and `G_BJL2` by
about `26.2%`. The corresponding absolute read1 L2 and BJL2 dynamic RMS
values increase by about `20%`. The read1/read0 separation remains strong:
R7-A control-subtracted p-p ratios are approximately `9.35x` for `Lin`,
`5.15x` for `L2`, and `4.90x` for `BJL2`. The two READ=0 controls are at the
numerical baseline.

## Redistribution and BJL2 event evidence

Read1 raw branch p-p excursions in R7-A are:

| branch | p-p excursion |
|---|---:|
| `I(Lin)` / BJs branch | 18.15489 µA |
| `I(L1)` | 4.89340 µA |
| `I(L2)` | 4.89340 µA |
| `I(RJ1)` | 2.89530 µA |
| `I(RJ2)` | 0.86310 µA |

The control-subtracted BJL1 RMS decreases slightly from `3.55951` to
`3.48861 µA`, and RJ1 RMS is essentially unchanged (`0.47029` to
`0.45875 µA`), while L2/BJL2 routing increases. This is consistent with
redistribution away from the front stage, but does not identify a unique
internal mechanism.

| case | JJ | activity range (turn) | largest monotonic phase (turn) | same-JJ V area (turn) | complete |
|---|---|---:|---:|---:|:---:|
| read1 | BJs | 0.015200 | +0.014741 | +0.014747 | no |
| read1 | BJL1 | 0.013953 | −0.013002 | −0.013008 | no |
| read1 | BJL2 | 0.003557 | −0.001886 | −0.001886 | no |
| read0 | BJs | 0.003690 | −0.001920 | −0.001921 | no |
| read0 | BJL1 | 0.003279 | +0.001477 | +0.001477 | no |
| read0 | BJL2 | 0.000852 | +0.000378 | +0.000378 | no |
| logical1 READ=0 | BJL2 | 0 | 0 | ~0 | no |
| logical0 READ=0 | BJL2 | 0 | 0 | ~0 | no |

The largest read1 BJL2 segment is approximately `−0.00188589 turn` with
same-JJ area `−0.00188642 turn` and residual `+5.29e−7 turn`. It is internally
consistent as a small transient, but is far below one turn. No complete BJL2
event occurs in any matched case, and no free-running BJL2 behavior is seen in
the recorded post-window.

## Canonical BVM source/storage guard

The comparison uses the canonical no-receiver raw baselines and the R6-B
matched results. Absolute canonical read1 JS1/JS2 running is expected source
behavior; it is not, by itself, receiver back-action. The relevant guard is
the additional disturbance relative to that baseline.

### Read1

| observable | canonical no receiver | R6-B | R7-A |
|---|---:|---:|---:|
| peak `I(L_SL)` (µA) | 75.341 | 75.311 | 75.302 |
| peak `V(SL)` (µV) | 904.091 | 905.200 | 905.312 |
| peak `V(N6)` (µV) | 1814.477 | 1816.524 | 1816.541 |
| JM1 drift (turn) | +7.791e−5 | +8.061e−5 | +8.077e−5 |
| JM2 drift (turn) | +5.753e−5 | +3.817e−5 | +3.924e−5 |
| JS1 post p-p (turn) | 0.008919 | 0.008909 | 0.008909 |
| JS2 post p-p (turn) | 0.000882 | 0.000888 | 0.000888 |

### Read0

| observable | canonical no receiver | R6-B | R7-A |
|---|---:|---:|---:|
| peak `I(L_SL)` (µA) | 26.411 | 26.235 | 26.236 |
| peak `V(SL)` (µV) | 316.938 | 319.274 | 319.260 |
| peak `V(N6)` (µV) | 652.993 | 653.388 | 653.391 |
| JM1 drift (turn) | −6.048e−6 | −5.968e−6 | −5.968e−6 |
| JM2 drift (turn) | +2.308e−4 | +2.309e−4 | +2.309e−4 |
| JS1 post p-p (turn) | 0.001534 | 0.001537 | 0.001537 |
| JS2 post p-p (turn) | 0.000178 | 0.000181 | 0.000180 |

R7-A READ=0 controls have approximately `0.000891 µA` maximum source-current
activity, `0.0215 µV` maximum N6 activity, and no material JM/JS drift. Thus
the source/storage guard is preserved relative to the registered baselines.

## Observed

- The four successful artifacts are valid and matched at the registered
  timestep/stop configuration.
- Reducing L1 produces a measurable read1 routing gain: both `G_L2` and
  `G_BJL2` exceed the R6-B reference.
- The gain is state-selective; read0 is much smaller and READ=0 controls are
  inactive.
- The L1 change materially shifts the settled L1/L2 bias split.
- BJL1/RJ1 activity is not amplified in proportion to L2/BJL2; the data show
  redistribution toward the L2/BJL2 side.
- No complete BJL2 phase transition occurs.

## Derived

- At this tested point, lowering L1 increases the fraction of the
  control-subtracted read1 front-stage perturbation appearing in L2/BJL2:
  `G_L2 0.1945 -> 0.2448` and `G_BJL2 0.1749 -> 0.2207`.
- The measured source/storage guard remains bounded, so this routing gain is
  not accompanied by an observed R6-B-scale loss of canonical source
  isolation.
- The result supports `ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED`, not a local
  native-QB event pass.

## Inference

- The L1 reduction likely changes both transient impedance transfer and the
  native QB static load line. Because the settled currents move by several
  microamps, this single point cannot prove that the gain is due to reactance
  alone at an otherwise fixed operating point.
- The BJL1/RJ1 versus L2/BJL2 changes are consistent with front-stage-to-loop
  redistribution, but the raw data do not uniquely identify whether the
  dominant mechanism is inductive reactance, bias relocation, or nonlinear
  load-line curvature.

## Unknown

- No second L1 point was tested; no L1 sweep is justified by this single-point
  result.
- No timestep refinement was run within this Exploration boundary.
- It is unknown whether another L1 value can produce a complete BJL2 event
  while retaining the guard.
- No JTL/T1 or downstream SFQ delivery was tested. A local BJL2 phase excursion
  is not a downstream SFQ event.

## Final classification

`ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED`

`ISOLATED_NATIVE_QB_LOCAL_PASS` is not met. The next work should not append an
L1 sweep to this Exploration solely because BJL2 did not complete a turn.

