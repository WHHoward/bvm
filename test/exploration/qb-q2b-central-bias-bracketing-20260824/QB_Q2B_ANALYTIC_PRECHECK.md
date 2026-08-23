# QB-Q2B analytic precheck — IBIAS-only local bracket

## Frozen input and model

This precheck uses the committed QB-Q2A canonical source-isolated voltage-replay raw files and the same scaled QB model. No JoSIM run is used to choose the points.

The actual `jjmit` first-order critical currents are:

```text
BJs  AREA=.50  Ic≈50 µA
BJL1 AREA=.36  Ic≈36 µA
BJL2 AREA=.54  Ic≈54 µA
```

The target is BJs→BJL1 routing. BJL2 is not changed or used as the next tuning variable.

## Settled operating point at the existing 35 µA point

Using the Q2A `[80,90) ps` settled window:

| source replay | `I(RB)` | `I(L1)` | `I(L2)` | `I(BJL1)` | `I(BJL2)` | `I(BJs)` |
|---|---:|---:|---:|---:|---:|---:|
| canonical logical1 C | `35.000 µA` | `−17.676 µA` | `17.324 µA` | `11.406 µA` | `17.324 µA` | `−6.270 µA` |
| canonical logical0 C0 | `35.000 µA` | `−21.285 µA` | `13.715 µA` | `5.980 µA` | `13.715 µA` | `−15.305 µA` |

The node3 KCL is numerically consistent with the element directions:

```text
I(L2) − I(L1) ≈ I(RB) = IBIAS
```

At 35 µA the settled BJL1 ratios are approximately `0.317 Ic` for logical1 and `0.166 Ic` for logical0. The largest read-window BJL1 currents were about `50.27 µA` (logical1, `1.40 Ic`) and `24.19 µA` (logical0, `0.67 Ic`); these are only load-line/activity diagnostics, not switching evidence.

## Point selection

The first-order controlled variable is `I(RB)=IBIAS`. A ±5 µA change is ±14.3% around the existing 35 µA branch bias. Holding all other parameters and the canonical voltage replay fixed, the predicted direction is:

- `30 µA`: lower node3 total bias and a conservative lower-side bracket; it is not expected to improve BJL1 escape, but tests whether the 35 µA point is already over-biased or dynamically suppressing the front stage.
- `40 µA`: higher node3 total bias and the upper-side bracket; it is the first point expected to move BJL1 closer to nonlinear operation, while remaining less aggressive than an unneeded 45 µA point given the read0 activity already reaches about `0.67 Ic` at 35 µA.

The possible BJL1 settled values at 30/40 µA are not claimed as exact predictions: BJL1 is not directly equal to the RB current, and its nonlinear load-line must be measured. A rough fixed-share indication would be about `9.8/13.0 µA` for logical1 and `5.1/6.8 µA` for logical0, but this is not used as event evidence.

## Frozen choice

The only extra points are:

```text
IBIAS = 30 µA
IBIAS = 40 µA
```

The existing Q2A 35 µA C/C0 result is the baseline; no 35 µA rerun is added. No other parameter changes.

## Stop condition

At each point, run logical1 READ=0 control first, then logical0 READ=0 control. Any startup/free-running, complete control transition, or clear nonselectivity stops that bias direction. If controls are bounded, run canonical logical1/read1 and logical0/read0 using the frozen source-isolated replay waveforms. A BJL1 event still requires same-JJ continuous phase, same-segment direct voltage area, and bounded retrap.
