# R6-B native-QB matched-ratio transfer Exploration

## Verdict

`DRIVE_GAIN_WITH_ISOLATION_PRESERVED`

This is an Exploration-tier result, not an interface Gate. The matched-ratio
point increases the measured read1 secondary and early native-QB activity over
R6-A, while the canonical source/storage guard remains close to the canonical
no-receiver and R6-A baselines. The gain does **not** produce a complete BJL2
event: read1 BJL2 remains a sub-turn, phase/area-consistent excursion.

`ISOLATED_NATIVE_QB_LOCAL_PASS` is **not met**.

The more specific interpretation is therefore:

```text
input/early-QB drive gain: observed
BJL2 output-stage gain: not meaningful at this point
source/back-action guard: preserved in the registered comparison
complete local event: absent
```

## Frozen point and provenance

```text
R_PRI  = 12 ohm
L_PRI  = 0.20 pH
L_SEC  = 1.00 pH
K      = 0.70710678
M      = 0.316227766 pH
```

The native `BQ_PAPER` topology, BJs/BJL1/BJL2 AREA, Lin/L0/L1/L2, RB/IB,
RJ1/RJ2, output load, canonical BVM, source PWLs, requested `dt=0.0125 ps`,
and stop time `170 ps` were unchanged from R6-A. The four runs were:

- `read1`
- `read0`
- `logical1-read0-control`
- `logical0-read0-control`

The complete run registration is in [`manifest.yaml`](../manifest.yaml) and
the pre-run record is in [`PREREGISTRATION.md`](../PREREGISTRATION.md).

## Artifact QA

All four JoSIM runs:

- exited with code 0;
- produced 13,599 rows and 39 fields;
- covered `0` to `169.9875 ps`;
- had strictly increasing finite actual time values;
- had no stderr output;
- had actual solver intervals from approximately `0.0125` to `0.025 ps`;
- contained all registered BVM, QB, primary, secondary, and storage probes.

The raw CSV SHA-256 values are recorded in
[`sha256sums.txt`](sha256sums.txt). The measurement semantics are those of
`METRIC_SPEC_V2` v2.0.0; its hash is recorded in the manifest.

## Measurement rule

Raw `P(...)` is retained in radians. Reported phase turns are derived from

```text
phase_delta_turns = phase_delta_rad / (2*pi)
```

For BJs, BJL1, and BJL2, the largest monotonic segment and the direct same-JJ
voltage integral use the same `[94,130) ps` activity window and actual CSV time
axis. The local-event rule requires at least one complete turn and a
phase/area-consistent same-JJ segment. A current peak or voltage peak alone is
not treated as an event.

## R6-B versus R6-A transfer

The following values use the activity window. Current excursions are
peak-to-peak values of `I(L_SEC)`; voltage values are peak absolute values of
`V(L_SEC)=V(QB_IN)`.

| case | `V(L_SEC)` peak R6-A → R6-B (µV) | `I(L_SEC)` excursion R6-A → R6-B (µA p-p) | read1/read0 state separation |
|---|---:|---:|---|
| read1 | 53.790 → 64.439 | 9.667 → 18.816 | increased |
| read0 | 15.852 → 14.834 | 2.206 → 2.011 | not increased |
| logical1 READ=0 | 0.000574 → 0.000570 | 0 → 0 | inactive |
| logical0 READ=0 | 0.000576 → 0.000567 | 0 → 0 | inactive |

Thus the first-order matched-M point did not simply scale every case upward.
The read1 transient became stronger and more state-selective, while the
controls remained at the numerical baseline.

Native QB branch peak currents show the same early-stage effect:

| case | `I(Lin)` | `I(L1)` | `I(L2)` | `I(RJ1)` | `I(RJ2)` |
|---|---:|---:|---:|---:|---:|
| read1 R6-A | 20.566 | 45.964 | 47.249 | 0.957 | 0.312 |
| read1 R6-B | 26.787 | 47.013 | 47.063 | 1.547 | 0.376 |
| read0 R6-A | 17.043 | 44.888 | 45.943 | 0.279 | 0.095 |
| read0 R6-B | 19.442 | 45.472 | 45.338 | 0.265 | 0.090 |
| READ=0 controls R6-B | 18.425 | 45.022 | 44.978 | ~0 | 0 |

`RB` remains the frozen `90 µA` bias branch in every case. These are activity
diagnostics, not event counts.

## BJs/BJL1/BJL2 phase and voltage-area evidence

The table reports activity range, largest monotonic phase segment, and the
same-segment direct-voltage area for R6-B. All values are turns except raw
phase deltas explicitly marked `rad`.

| case | JJ | activity range | largest phase segment | same-JJ area | residual | complete |
|---|---|---:|---:|---:|---:|:---:|
| read1 | BJs | 0.014909 | +0.014304 | +0.014309 | −0.00000555 | no |
| read1 | BJL1 | 0.014221 | −0.013310 | −0.013317 | +0.00000670 | no |
| read1 | BJL2 | 0.002964 | −0.001588 | −0.001588 | +0.00000043 | no |
| read0 | BJs | 0.003677 | −0.001770 | −0.001770 | +0.00000034 | no |
| read0 | BJL1 | 0.003359 | +0.001515 | +0.001515 | −0.00000037 | no |
| read0 | BJL2 | 0.000720 | +0.000319 | +0.000319 | −0.00000006 | no |
| logical1 READ=0 | BJs | 2.71e−7 | +2.07e−7 | +2.02e−7 | +5.0e−9 | no |
| logical1 READ=0 | BJL1 | 0 | 0 | +6.45e−10 | −6.45e−10 | no |
| logical1 READ=0 | BJL2 | 0 | 0 | +1.46e−10 | −1.46e−10 | no |
| logical0 READ=0 | BJs | 2.71e−7 | −1.43e−7 | −1.32e−7 | −1.13e−8 | no |
| logical0 READ=0 | BJL1 | 0 | 0 | −7.07e−10 | +7.07e−10 | no |
| logical0 READ=0 | BJL2 | 0 | 0 | −1.61e−10 | +1.61e−10 | no |

The read1 BJL2 segment is `−0.0099774 rad`, or `−0.00158795 turn`, with
same-JJ area `−0.00158838 turn`. It is internally consistent as a small local
transient, but is far below the preregistered one-turn event condition.

## BJL2 R6-B/R6-A gain

| metric, read1 | R6-A | R6-B | R6-B/R6-A |
|---|---:|---:|---:|
| activity range (turn) | 0.00288519 | 0.00296404 | 1.0273 |
| largest monotonic segment (absolute turn) | 0.00158461 | 0.00158795 | 1.0021 |
| same-JJ area (absolute turn) | 0.00158499 | 0.00158838 | 1.0021 |
| voltage peak (µV) | 6.857 | 8.276 | 1.207 |
| current peak (µA) | 46.708 | 46.615 | 0.998 |
| complete segment count | 0 | 0 | — |

This is the key limitation. The secondary and BJs/BJL1 signals gain, but the
gain does not become a consequential BJL2 phase gain. The read0 BJL2 range
decreases from `0.00075525` to `0.00072002 turn`; both controls remain zero
within the recorded numerical activity.

## Primary and source guard comparison

The canonical read0 source is the current `neg-init-pos-read` B/+READ raw.
The superseded `neg-read-single` ramp-init artifact is not used.

### Read1

| observable | canonical no-receiver | R6-A | R6-B |
|---|---:|---:|---:|
| peak `I(L_SL)` (µA) | 75.341 | 75.393 | 75.311 |
| peak `V(SL)` (µV) | 904.091 | 903.312 | 905.200 |
| peak `V(N6)` (µV) | 1814.477 | 1816.279 | 1816.524 |
| JM1 post−pre drift (turn) | +7.791e−5 | +8.157e−5 | +8.061e−5 |
| JM2 post−pre drift (turn) | +5.753e−5 | +4.093e−5 | +3.817e−5 |
| JS1 post-window p2p (rad; turn) | 0.05604; 0.008919 | 0.05598; 0.008909 | 0.05598; 0.008909 |
| JS2 post-window p2p (rad; turn) | 0.00554; 0.000882 | 0.00557; 0.000886 | 0.00558; 0.000888 |

### Read0

| observable | canonical no-receiver | R6-A | R6-B |
|---|---:|---:|---:|
| peak `I(L_SL)` (µA) | 26.411 | 26.229 | 26.235 |
| peak `V(SL)` (µV) | 316.938 | 319.329 | 319.274 |
| peak `V(N6)` (µV) | 652.993 | 653.371 | 653.388 |
| JM1 post−pre drift (turn) | −6.048e−6 | −5.968e−6 | −5.968e−6 |
| JM2 post−pre drift (turn) | +2.308e−4 | +2.309e−4 | +2.309e−4 |
| JS1 post-window p2p (rad; turn) | 0.00964; 0.001534 | 0.00966; 0.001537 | 0.00966; 0.001537 |
| JS2 post-window p2p (rad; turn) | 0.001119; 0.000178 | 0.001134; 0.000181 | 0.001134; 0.000181 |

The absolute read1 JS1/JS2 post−pre change remains approximately `−3 turns`,
as in the canonical source. That canonical running is not classified as
receiver back-action. The relevant R6-B comparison is the extra post-window
disturbance, JM drift, and SL/N6 waveform relative to the canonical source and
R6-A. Those quantities remain close in this run.

## Observed

- All four artifacts are valid and matched at the registered timestep/stop
  configuration.
- R6-B increases read1 secondary voltage and current excursion.
- Read1 BJs and BJL1 activity increases over R6-A; read0 does not show the same
  increase, and READ=0 controls remain inactive.
- R6-B read1 BJL2 activity range increases only `2.73%`; its largest
  phase/area-consistent segment increases only `0.21%`.
- No R6-B case contains a complete BJL2 segment.
- R6-B primary current and BVM SL/N6/storage guards remain close to R6-A and
  the appropriate canonical no-receiver baseline.
- No free-running BJL2 behavior is present in the finite post window.

## Derived

- At fixed (M), the R6-B point produces a real measured early-QB drive gain,
  not transfer starvation.
- The gain is selective: read1 secondary voltage peak is about `4.34×` read0
  in R6-B, versus about `3.39×` in R6-A; the READ=0 controls remain near zero.
- The gain is not sufficient to move the output-side BJL2 into a complete local
  phase transition.
- The comparative source/storage evidence supports the bounded label
  `DRIVE_GAIN_WITH_ISOLATION_PRESERVED` for this single point.

## Inference

- Lowering `L_SEC` at matched (M) likely reduced the secondary source/leakage
  impedance enough to increase the voltage/current presented to the early QB
  loop.
- The native QB nonlinear network still limits conversion of that input gain
  into BJL2 quantization. This is an inference from the input/early-QB versus
  BJL2 split, not a proof of a unique internal mechanism.
- The result does not establish that all winding ratios or mutual couplings
  preserve source isolation.

## Unknown

- No timestep refinement was run, by the preregistered single-point
  Exploration boundary.
- The exact time-dependent nonlinear secondary impedance and reflected load are
  not independently identified.
- It is unknown whether a different isolated interface point can produce a
  complete BJL2 event without changing native QB parameters.
- No JTL/T1 or downstream SFQ delivery was tested.

## Final classification

`DRIVE_GAIN_WITH_ISOLATION_PRESERVED`

This classification is limited to the tested model, single point, four matched
cases, timestep, windows, and finite simulation interval. It is not a universal
transformer rule, not a native-QB local pass, and not downstream SFQ delivery.

No QB AREA/bias/RJ/L was changed, no sweep was added, and no canonical BVM
file was modified.
