# R8 BJL2 output-stage current-class single-point Exploration

## Verdict

`OUTPUT_CLASS_CHANGE_WITHOUT_MEANINGFUL_BJL2_GAIN`

Changing only BJL2 `AREA=1.89 -> 0.70` increases the read1 BJL2 phase and
same-JJ voltage-area excursion by roughly `36%`, but the response remains in
the `10^-3 turn` regime. The BJL2 current excursion decreases, no complete
event occurs, and read0 activity grows proportionally more than read1. This
is not a threshold-like quantizing jump.

The source/storage guard remains preserved. `BJL2_OUTPUT_CLASS_LOCAL_PASS` is
not met. The result is bounded to this AREA point, topology, source, load,
timestep, windows, and finite simulation interval.

## Frozen point and scope

R7-A was retained except for the BJL2 output junction:

```text
BJL2 AREA = 0.70
Ic        = 70.0 uA
C         = 49.0 fF
RN        = 22.857 ohm
R0        = 228.571 ohm
```

Under the actual `jjmit.cir` model, `Ic,C` scale with AREA while `RN,R0`
scale inversely. The intrinsic `beta_c` remains approximately `5.445`, but
the damping/load-line relative to fixed `RJ2=22 ohm` and the output network
changes. The experiment therefore tests a combined output-stage AREA/current
class change, not `Ic` alone.

All other values were frozen at R7-A: `L1=2.50 pH`, `L2=3.91 pH`,
`Lin=0.8 pH`, `L0=1.323 pH`, `IB=90 uA`, BJs/BJL1 AREA, `RB/RJ1/RJ2`, the
R6-B transformer, canonical BVM, and `10 ohm` output load. No sweep, bias
change, transformer change, JTL, or T1 was used.

## Artifact QA

All four matched JoSIM runs exited with code 0 and produced no stderr output.
Each raw CSV has 13,599 rows and 39 fields, covers `0` to `169.9875 ps`, has
finite strictly increasing time, and has actual solver intervals from
`0.0125` to `0.025 ps`.

The recorded solver is JoSIM `v2.7.2837d13`, binary SHA-256
`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.

## Settled operating point

The new READ=0 controls, not the R7-A current, define the R8 operating point.
Values are pre-window medians; currents are in microamps and phases in
radians.

| quantity | R7-A | R8 AREA=.70 |
|---|---:|---:|
| `P(BJs)` | −0.159009 | −0.188132 |
| `I(BJs)=I(Lin)` | −21.059 | −24.874 |
| `P(BJL1)` | +0.274190 | +0.324178 |
| `I(BJL1)` | +30.326 | +35.675 |
| `P(BJL2)` | +0.205760 | +0.434241 |
| `I(BJL2)=I(L2)` | +38.615 | +29.450 |
| `I(L1)` | −51.385 | −60.550 |
| `I(RB)` | +90.000 | +90.000 |

The AREA change materially redistributes the static load line: BJL2 current
falls by about `24%`, while BJL1 and the BJs/Lin branch increase. This is why
the R7-A `38.62 uA` value is not reused for the new `I/Ic` diagnostic.

Using the new R8 controls and the new `Ic=70 uA`:

| quantity | value |
|---|---:|
| BJL2 settled `I/Ic` | `0.4207` |
| read1 BJL2 peak `I/Ic` | `0.4450` |
| read0 BJL2 peak `I/Ic` | `0.4244` |

These are operating-point diagnostics only. None is an event criterion.

## BJL2 response versus R7-A

The phase and voltage-area measurements use the same continuous unwrapped
phase rule, same `[94,130) ps` window, same JJ, and actual CSV time axis.

| case | metric | R7-A | R8 | R8/R7-A |
|---|---|---:|---:|---:|
| read1 | activity range (turn) | 0.003557 | 0.004602 | 1.294x |
| read1 | largest monotonic phase (turn) | −0.001886 | −0.002561 | 1.358x |
| read1 | same-JJ V area (turn) | −0.001886 | −0.002562 | 1.358x |
| read1 | BJL2 current p-p (uA) | 4.039 | 3.248 | 0.804x |
| read0 | activity range (turn) | 0.000852 | 0.001349 | 1.584x |
| read0 | largest monotonic phase (turn) | +0.000378 | −0.000605 | 1.601x |
| read0 | same-JJ V area (turn) | +0.000378 | −0.000605 | 1.601x |
| read0 | BJL2 current p-p (uA) | 0.824 | 0.550 | 0.668x |

R8 read1 BJL2's largest segment is `−0.00256079 turn`, with same-JJ area
`−0.00256161 turn` and residual below `1e-6 turn`. It is internally
consistent but far below the required `1.0 turn`. Read0's largest segment is
`−0.00060495 turn`, also area-consistent and incomplete.

The read1/read0 activity-range separation decreases from about `4.18x` in
R7-A to `3.41x` in R8. The largest-segment separation decreases from about
`4.99x` to `4.23x`. Thus read0 margin is degraded, although neither read0 nor
either READ=0 control produces a complete event.

The phase/area increase without a current-excursion increase is consistent
with the combined AREA-induced capacitance/resistance/load-line change; it is
not evidence for a pure critical-current threshold crossing.

## BJs/BJL1 redistribution

Read1 BJs/BJL1 activity does not show a new runaway state:

| quantity | R7-A | R8 |
|---|---:|---:|
| BJs phase range (turn) | 0.015200 | 0.014397 |
| BJL1 phase range (turn) | 0.013953 | 0.013279 |
| BJL1 current p-p (uA) | 20.712 | 19.643 |
| RJ1 current p-p (uA) | 2.895 | 2.748 |

The front-stage activity is slightly reduced while the static BJs/BJL1
currents increase. No free-running signature appears in the finite post
window.

## Source and storage guards

The following compares canonical no-receiver, R7-A, and R8. Absolute
canonical read1 JS running is expected source behavior; it is not itself
receiver back-action.

### Read1

| observable | canonical | R7-A | R8 |
|---|---:|---:|---:|
| peak `I(L_SL)` (uA) | 75.341 | 75.302 | 75.309 |
| peak `V(SL)` (uV) | 904.091 | 905.312 | 905.202 |
| peak `V(N6)` (uV) | 1814.477 | 1816.541 | 1816.531 |
| JM1 drift (turn) | +7.791e−5 | +8.077e−5 | +8.069e−5 |
| JM2 drift (turn) | +5.753e−5 | +3.924e−5 | +3.924e−5 |
| JS1 post p-p (turn) | 0.008919 | 0.008909 | 0.008909 |
| JS2 post p-p (turn) | 0.000882 | 0.000888 | 0.000886 |

### Read0

| observable | canonical | R7-A | R8 |
|---|---:|---:|---:|
| peak `I(L_SL)` (uA) | 26.411 | 26.236 | 26.235 |
| peak `V(SL)` (uV) | 316.938 | 319.260 | 319.290 |
| peak `V(N6)` (uV) | 652.993 | 653.391 | 653.397 |
| JM1 drift (turn) | −6.048e−6 | −5.968e−6 | −5.968e−6 |
| JM2 drift (turn) | +2.308e−4 | +2.309e−4 | +2.309e−4 |
| JS1 post p-p (turn) | 0.001534 | 0.001537 | 0.001537 |
| JS2 post p-p (turn) | 0.000178 | 0.000180 | 0.000181 |

R8 READ=0 controls retain numerical-baseline source activity (approximately
`0.000891 uA` peak source current and `0.0215 uV` peak N6 activity) and no
material JM/JS disturbance. The upstream BVM/source guard is preserved.

## Event and verdict evidence

- read1: zero qualifying complete BJL2 monotonic segments;
- read0: zero qualifying complete BJL2 monotonic segments;
- both READ=0 controls: zero complete segments and no free running;
- all reported read1/read0 BJL2 segments are below `0.003 turn`.

### Observed

- The AREA change shifts the settled BJL2 load line substantially.
- Read1 BJL2 phase range and same-JJ voltage area increase by about `29%` and
  `36%`, respectively.
- BJL2 current excursion decreases, and read0 phase/area activity increases
  more than read1.
- BJs/BJL1 and source/storage guards remain bounded.

### Derived

- The point does not produce threshold-like nonlinear amplification: the
  read1 response remains in the `10^-3 turn` regime and has no complete event.
- The output-class change weakens read1/read0 BJL2 separation rather than
  improving it.
- The result is not a BJL2 local pass and cannot establish downstream SFQ
  delivery.

### Inference

- The increased phase/voltage-area response is more consistent with the
  combined AREA-dependent capacitance, resistance, and load-line change than
  with a simple `Ic` margin effect.
- Because BJL2 settled current moves from `38.62` to `29.45 uA`, the output
  class change feeds back into the native loop operating point; BJL2 cannot be
  treated as an isolated threshold element at this point.
- The larger relative read0 response indicates a selectivity cost before any
  useful quantization regime is reached.

### Unknown

- Whether another output-class point could produce a complete event while
  retaining read0 margin; this point does not authorize an AREA sweep.
- Whether a different bias/load-line strategy can improve BJL2 without
  disturbing BJs/BJL1 or the source guard.
- Timestep refinement and downstream JTL/T1 reception remain untested.

## Final classification

`OUTPUT_CLASS_CHANGE_WITHOUT_MEANINGFUL_BJL2_GAIN`

No further `.60/.50/.40` AREA points are added. Any next architecture decision
must first account for the observed static load-line redistribution and the
read0 selectivity erosion.

