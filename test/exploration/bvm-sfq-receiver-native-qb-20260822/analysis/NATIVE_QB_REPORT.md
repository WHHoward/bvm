# Native paper-QB compatibility with canonical BVM SL

Exploration: `bvm-sfq-receiver-native-qb-20260822`  
Scope: one frozen native paper-QB topology and one reference parameter set; no
sweep, JTL, T1, B_TRIG mutual input, N6 tap, or secondary pickup.

## Verdict

**Overall: `BACK_ACTION_FAILURE`**

The direct `canonical SL1 -> BQ_PAPER IN` connection produces clearly
state-dependent nonlinear activity in the native QB core, but the read1
receiver load changes the BVM storage signature by approximately `-3.0 turns`
in both `JS1` and `JS2`.  Therefore this point does not satisfy the required
source/storage guards and is not a native-QB local pass.

Secondary observation: **`STATE_SELECTIVE_QB_ACTIVITY` is supported before the
back-action guard is applied.**  Read1 activity is larger than read0 activity
and much larger than both READ=0 controls, but no BJL2 monotonic segment reaches
one complete turn.

## Frozen setup

The receiver is connected directly as:

```text
canonical BVM SL1 ───────── IN  BQ_PAPER  OUT ── 10 Ω ── ground
                                   IB  ↑
                                      90 µA
```

The repository topology was preserved exactly:

```text
Lin IN 1 0.8 pH
L0  4 OUT 1.323 pH
L1  2 3 3.91 pH
L2  3 4 3.91 pH
BJs  1 2 jjmit area=1.33
BJL1 2 0 jjmit area=1.12
BJL2 4 0 jjmit area=1.89
RJ1  2 0 33 Ω
RJ2  4 0 22 Ω
RB   IB 3 8.5 Ω
```

Using the frozen `jjmit.cir` model (`Ic=0.1 mA/area`, `C=0.07 pF/area`,
`Ic*RN=1.6 mV`, `R0=10*RN`), the nominal critical currents are:

| JJ | AREA | Ic |
|---|---:|---:|
| BJs | 1.33 | 133 µA |
| BJL1 | 1.12 | 112 µA |
| BJL2 | 1.89 | 189 µA |

The 90 µA bias is the explicit repository paper-BQ cascade-fixture value. It
is recorded as an experiment parameter, not asserted to be a universal native
paper input specification.

All four cases used `dt=0.0125 ps`, `tstop=170 ps`, the same snapshots of
`jjmit.cir`, `bvm_cell.cir`, and `bq_cell_paper.cir`, and the same probes:

- BJs/BJL1/BJL2 `P`, `V`, and `I`;
- `Lin`, `L1`, `L2`, `L0`, `RB`, `RJ1`, `RJ2` currents;
- `SL1`, `N6`, `OUT_Q`, BVM SL branch currents;
- `JM1/JM2/JS1/JS2` phase and voltage;
- WL/BL/SE stimulus currents.

## Artifact QA

All four successful CSVs contain 13,599 rows, finite values, a strictly
increasing time column, and end at 169.9875 ps (the last sampled point before
170 ps). The successful solver commands returned exit code 0 and produced no
stderr.

The preserved logs also contain two non-scientific execution failures: the
first command used an incorrect relative binary path and returned 127 before
solver startup; the second simulated to completion but lacked the per-case raw
output directories. Neither produced raw evidence. The successful third
execution used the corrected path and existing frozen inputs.

No convergence ladder was run; this is an Exploration-tier single-point
result, not a convergence-qualified Candidate or Authority result.

## Event measurement

Raw `P(...)` values are radians. The analysis unwraps adjacent phase samples
continuously, forms descriptive monotonic segments in the preregistered
94--130 ps activity window, and cross-checks each segment against the direct
same-JJ `V(...)` integral divided by `Phi0`.

A complete local event requires a monotonic segment with absolute phase change
at least 1.0 turn and a same-segment voltage-area residual no larger than 0.05
turn. The current or voltage peak alone is never used as an event criterion.
The raw phase trajectories remain in the CSVs; the table below records the
derived trajectory/area evidence.

## BQ junction evidence

`range` is the total continuous phase range in the activity window. `largest`
is the largest absolute monotonic segment. `area` is the same-JJ voltage area
for that segment, and `resid = largest - area`.

| Case | JJ | Range (turn) | V peak (µV) | I peak (µA) | Largest (turn) | Area (turn) | Residual (turn) | Complete segments |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| read1 | BJs | 0.366548 | 824.293 | 84.8385 | -0.364520 | -0.364571 | +0.0000505 | 0 |
| read1 | BJL1 | 0.213478 | 478.905 | 112.935 | -0.192434 | -0.192476 | +0.0000422 | 0 |
| read1 | BJL2 | 0.0692462 | 160.079 | 71.4441 | -0.065210 | -0.065224 | +0.0000139 | 0 |
| read0 | BJs | 0.0905165 | 144.194 | 31.4471 | -0.074730 | -0.074739 | +0.0000087 | 0 |
| read0 | BJL1 | 0.0881666 | 155.292 | 59.4956 | +0.063088 | +0.063100 | -0.0000117 | 0 |
| read0 | BJL2 | 0.0189728 | 37.8353 | 56.3309 | +0.016244 | +0.016247 | -0.0000027 | 0 |
| logical1 READ=0 | BJs | 0.000167603 | 0.356295 | 0.00176155 | +0.000103 | +0.000103 | -0.000000017 | 0 |
| logical1 READ=0 | BJL1 | 0.0000113159 | 0.0247785 | 40.5501 | -0.00000802 | -0.00000802 | -0.0000000055 | 0 |
| logical1 READ=0 | BJL2 | 0.00000475873 | 0.0101905 | 49.4504 | -0.00000476 | -0.00000475 | -0.000000011 | 0 |
| logical0 READ=0 | BJs | 0.000158950 | 0.337791 | 0.00172511 | -0.0000962 | -0.0000962 | +0.000000016 | 0 |
| logical0 READ=0 | BJL1 | 0.0000110454 | 0.0246654 | 40.5500 | +0.00000707 | +0.00000706 | +0.0000000038 | 0 |
| logical0 READ=0 | BJL2 | 0.00000464732 | 0.0101606 | 49.4504 | +0.00000465 | +0.00000464 | +0.0000000073 | 0 |

The direct same-JJ areas agree with the corresponding sub-turn phase segments,
but all BJL2 segments remain far below one turn. Thus the evidence supports
activity and state separation, not a complete local BJL2 event.

## Loop and bias branch currents

Currents are shown as activity-window min--max values in the declared branch
orientations. `RB` remains the 90 µA bias branch in all cases.

| Case | Lin (µA) | L1 (µA) | L2 (µA) | L0 (µA) | RB (µA) | RJ1 (µA) | RJ2 (µA) |
|---|---:|---:|---:|---:|---:|---:|---:|
| read1 | -28.28..84.84 | -63.68..-9.562 | 26.32..80.44 | -15.28..13.67 | 90 | -14.51..12.91 | -7.276..6.558 |
| read0 | -31.45..26.47 | -51.08..-30.99 | 38.92..59.01 | -3.007..3.625 | 90 | -3.167..4.706 | -1.419..1.720 |
| logical1 READ=0 | -0.001762..0.001760 | -40.55..-40.55 | 49.45..49.45 | -0.0009825..0.0008638 | 90 | -0.0007509..0.0007131 | -0.0004632..0.0004063 |
| logical0 READ=0 | -0.001725..0.001699 | -40.55..-40.55 | 49.45..49.45 | -0.0008511..0.0009791 | 90 | -0.0006953..0.0007474 | -0.0004004..0.0004618 |

The read1 `Lin` peak reaches 84.84 µA and drives substantial BJs/BJL1
activity. It is below the nominal BJs/BJL1/BJL2 critical-current class, but the
native loop is demonstrably not nearly inactive at this reference point.

## Source, output, and storage evidence

The following are activity-window peak magnitudes. Voltages are direct node
voltages; the output voltage is not interpreted as an SFQ event.

| Case | V(SL1) peak (µV) | V(N6) peak (µV) | I(L_SL) peak (µA) | V(OUT_Q) peak (µV) |
|---|---:|---:|---:|---:|
| read1 | 1174.1 | 1497.45 | 84.8385 | 152.765 |
| read0 | 284.319 | 554.514 | 31.4471 | 36.2479 |
| logical1 READ=0 | 0.381406 | 0.391274 | 0.00176155 | 0.00982472 |
| logical0 READ=0 | 0.356443 | 0.360680 | 0.00172511 | 0.00979062 |

The source remains strongly state dependent under this load. The storage
comparison is the limiting guard:

| Case | ΔJM1 (turn) | ΔJM2 (turn) | ΔJS1 (turn) | ΔJS2 (turn) | Post JS1 / JS2 phase (rad) |
|---|---:|---:|---:|---:|---:|
| read1 | +0.0000407 | +0.000851 | -2.999669 | -2.999704 | -18.58071 / -19.11467 |
| read0 | -0.0000061 | +0.000228 | -0.000234 | -0.000173 | -0.268213 / +0.265913 |
| logical1 READ=0 | +0.0000021 | -0.0000520 | +0.0000210 | +0.0000108 | +0.266901 / -0.266908 |
| logical0 READ=0 | -0.0000021 | +0.0000533 | -0.0000249 | -0.0000142 | -0.266901 / +0.266908 |

The logical1 READ=0 control preserves the expected small positive/negative JS
state, while loaded read1 does not: both JS phases move by approximately three
turns. JM1/JM2 remain comparatively bounded, so the dominant guard failure is
the JS storage state rather than a missing CSV or a solver artifact.

Post-window BJL2 phase p2p is `0.000702 turn` for read1 and below
`0.000184 turn` for read0; controls are below `4e-7 turn`. This supports a
bounded finite-window observation with no complete post-window BJL2 event. It
does not establish a general rearm theorem or downstream SFQ delivery.

## Evidence classification

### Observed

- The native paper-QB topology directly connected to SL produces read1 source
  current and voltage much larger than both READ=0 controls and larger than
  read0.
- Read1 has nonlinear, same-JJ phase/voltage-consistent sub-turn activity in
  all three QB junctions.
- Read0 has smaller BJs/BJL1 activity and no complete BJL2 segment.
- Both READ=0 controls remain near the static native loop state and have no
  complete segment.
- No BJL2 case has a qualifying one-turn monotonic segment.
- Loaded read1 changes JS1 and JS2 by approximately -3.0 turns; the matched
  logical1 READ=0 control changes them only at approximately 1e-5 turns.

### Derived

- At this fixed native parameter point, the read1/read0 BJL2 activity-range
  ratio is about 3.65, while read1/control separation is orders of magnitude.
- The direct load is not source-silent: `I(Lin)` reaches 84.84 µA and
  `V(SL1)` reaches 1.174 mV in read1.
- The event rule returns zero complete local BJL2 events for read1, read0, and
  both controls.

### Inference

- This point establishes a promising state-selective nonlinear operating
  regime, but not native QB quantization or exactly-one output behavior.
- The primary failure mechanism at this point is receiver-induced source/
  storage back-action. Insufficient current margin may also contribute to the
  absence of a BJL2 event, but this run does not isolate it from back-action.
- Direct SL loading is therefore not a valid first native-QB feasibility point
  for a preserved BVM storage state, even though it is useful evidence that the
  native core can enter a selective nonlinear regime.

### Unknown

- Whether a source-isolated or otherwise BVM-scaled native-QB connection can
  preserve JS storage while producing a complete BJL2 event.
- Whether a unified scaling of the native paper-QB current/inductive class can
  close the remaining BJL2 margin without recreating the observed back-action.
- Timestep/convergence sensitivity of the exact sub-turn amplitudes; no
  convergence ladder was preregistered for this Exploration.
- Any downstream JTL/T1 reception; neither was connected.

## Final evidence-bounded disposition

| Predeclared layer | Disposition | Reason |
|---|---|---|
| `NATIVE_QB_LOCAL_PASS` | **Not met** | No complete BJL2 event; storage guard also fails. |
| `STATE_SELECTIVE_QB_ACTIVITY` | **Supported as a sub-result** | Read1 nonlinear activity separates from read0/control. |
| `SOURCE_TOO_WEAK_OR_SCALE_MISMATCH` | **Not primary** | Input is below the paper JJ current class but the core is strongly nonlinear, not nearly inactive. |
| `BACK_ACTION_FAILURE` | **Primary verdict** | Loaded read1 JS1/JS2 storage shifts by about -3 turns. |
| `NONSELECTIVE_OR_FREE_RUNNING` | **Not observed in this finite run** | No control complete event or sustained BJL2 free-running signature. |

This is an Exploration result only. It does not modify the canonical BVM,
does not upgrade a Candidate, and does not authorize parameter sweeps or a
JTL/T1 experiment.
