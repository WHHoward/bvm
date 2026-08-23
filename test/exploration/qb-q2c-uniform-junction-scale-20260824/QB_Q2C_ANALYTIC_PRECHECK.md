# QB-Q2C analytic precheck — uniform junction/current scaling

## Selection

The user-authorized points are the first bounded scale bracket around the accepted Q2A/Q2B `s=1` reference. No s=1 rerun is included. The new points are `0.85`, `0.70` and `0.55`, executed from larger to smaller scale so the READ=0 guard can stop the direction before a more aggressive point.

## Actual jjmit scaling

The local `jjmit` model is:

```text
CAP=0.07 pF, r0=160 Ω, rn=16 Ω, icrit=0.1 mA
```

For `jjmit area=A`, the reconstructed first-order parameters are `Ic=100 A·µA`, `C=70 A·fF`, `RN=16/A Ω`, and `R0=160/A Ω`. Thus the uniform scale is not an Ic-only change: the external RJ1/RJ2/RB and all inductances remain fixed while intrinsic RN/R0 increase and C decreases with s.

| scale | BJs A/Ic/C/RN/R0 | BJL1 A/Ic/C/RN/R0 | BJL2 A/Ic/C/RN/R0 | IBIAS |
|---:|---|---|---|---:|
| 1.00 reference | .500 / 50 µA / 35 fF / 32.000 Ω / 320.000 Ω | .360 / 36 µA / 25.2 fF / 44.444 Ω / 444.444 Ω | .540 / 54 µA / 37.8 fF / 29.630 Ω / 296.296 Ω | 35.00 µA |
| 0.85 | .425 / 42.5 µA / 29.75 fF / 37.647 Ω / 376.471 Ω | .306 / 30.6 µA / 21.42 fF / 52.288 Ω / 522.876 Ω | .459 / 45.9 µA / 32.13 fF / 34.858 Ω / 348.584 Ω | 29.75 µA |
| 0.70 | .350 / 35.0 µA / 24.5 fF / 45.714 Ω / 457.143 Ω | .252 / 25.2 µA / 17.64 fF / 63.492 Ω / 634.921 Ω | .378 / 37.8 µA / 26.46 fF / 42.328 Ω / 423.280 Ω | 24.50 µA |
| 0.55 | .275 / 27.5 µA / 19.25 fF / 58.182 Ω / 581.818 Ω | .198 / 19.8 µA / 13.86 fF / 80.808 Ω / 808.081 Ω | .297 / 29.7 µA / 20.79 fF / 53.872 Ω / 538.721 Ω | 19.25 µA |

The products `Ic·RN`, `RN·C` and the intrinsic `R0·C` remain first-order invariant under this area scaling, while the relation to fixed external resistors and fixed L remains scale-dependent. Therefore the points test a combined current-class, capacitance and load-line scaling hypothesis, not a pure critical-current threshold.

## Existing s=1 evidence used as reference

The accepted Q2A/Q2B source-isolated reference at `IBIAS=35 µA` had read1 BJL1 activity around `0.3394 turn` and logical0 activity around `0.059 turn`, with no complete BJL1/BJL2 event. Its BJs read1 activity was already about one complete local phase/area response. This motivates testing the uniform class change while keeping the replay and external load fixed.

## Expected diagnostic value

Uniform scaling may preserve approximate bias/Ic ratios in an ideal scale-invariant network, but fixed RJ1/RJ2/RB/L values can instead redistribute the load line and damping. A lower scale is therefore informative only if the read1 output grows nonlinearly relative to read0 and controls. A control event, free-running or multifire at a smaller point is a stop condition, not evidence for continuing downward.

## Go/no-go boundary

No analytic contradiction was found: the new points are valid bounded diagnostic points under the frozen replay and actual model semantics. The experiment is authorized as a finite three-point Exploration. The event decision remains phase plus same-JJ voltage-area plus post behavior; `I/Ic` is only an operating-point diagnostic.
