# PAPER-SL-Q2 analytic settled/load-line precheck

## Result

`37.5 µA first point worth testing; 40 µA conditional bracket point`.

This is a first-order local load-line estimate from the accepted Q1 READ=0 control; it is not a switching prediction.

## Actual jjmit reconstruction

- `Ic_base=100 µA`, `CAP_base=0.07 pF`, `RN_base=16 Ω`, `R0_base=160 Ω`.

| JJ | AREA | Ic | C | RN | R0 |
|---|---:|---:|---:|---:|---:|
| BJS | 0.50 | 50.000 µA | 35.000 fF | 32 Ω | 320 Ω |
| BJL1 | 0.36 | 36.000 µA | 25.200 fF | 44.4444 Ω | 444.444 Ω |
| BJL2 | 0.54 | 54.000 µA | 37.800 fF | 29.6296 Ω | 296.296 Ω |

## Q1 settled READ=0 baseline, [140,170) ps

| quantity | median |
|---|---:|
| P(BJS) | -4.485126e-07 rad |
| P(BJL1) | 0.433496 rad |
| P(BJL2) | 0.3769835 rad |
| I(LIN) | -6.483866e-07 µA |
| I(L1) | -15.12166 µA |
| I(L2) | 19.87834 µA |
| I(RB) | 35 µA |
| I(BJL1) | 15.12166 µA |
| I(BJL2) | 19.87834 µA |
| I(RJ1) | 6.7337005e-07 µA |
| I(RJ2) | -3.874634e-07 µA |

The measured JJ branch split is 43.205% BJL1 / 56.795% BJL2; `I(BJL1)+I(BJL2)` closes the 35 µA bias to the displayed precision.

## First-order bracket projection

| IBIAS | projected BJL1 | projected BJL2 | BJL1/Ic | BJL2/Ic | approximate RB drop magnitude |
|---:|---:|---:|---:|---:|---:|
| 35.0 µA | 15.122 µA | 19.878 µA | 0.420 | 0.368 | 210.0 µV |
| 37.5 µA | 16.202 µA | 21.298 µA | 0.450 | 0.394 | 225.0 µV |
| 40.0 µA | 17.282 µA | 22.718 µA | 0.480 | 0.421 | 240.0 µV |

## Interpretation

- Observed: at Q1 35 µA control, the ideal bias branch carries 35 µA and the settled nonlinear branches carry approximately 15.122/19.878 µA; RJ1/RJ2 currents are near zero.
- Derived: the first-order high-side points raise the estimated static BJL1/BJL2 currents but leave both below their actual area-scaled Ic values.
- Inference: the bias change is a local operating-point test, not a claim that read1 will scale more than read0. The dynamic read waveform can alter the split and load-line.
- Unknown: whether the high-side bias moves the read1 transient into a complete BJL2 segment without a corresponding read0/control event.
