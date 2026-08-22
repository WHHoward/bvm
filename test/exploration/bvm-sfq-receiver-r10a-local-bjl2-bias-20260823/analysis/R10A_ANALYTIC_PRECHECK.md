# R10-A analytic precheck: output-side local BJL2 bias feed
## Status and selected point
This is a physics-informed static/load-line precheck using accepted R9-A raw data. It does not run JoSIM and does not use static saddle crossing as an event criterion.
Selected single point: **source-to-node-4 feed = 214.0 µA DC**, implemented by a 21.4 mV independent voltage source through 100 Ω in series with 10 pH. The positive feed direction is source → resistor → inductor → native QB node 4 (the BJL2 top node).
## Topology and source impedances
```text
VLB(BIAS,0) -- RLB=100 ohm -- LLB=10 pH -- native node 4
                                                   |
                                                BJL2||RJ2
                                                   |
                                                  GND
```
The source return is the independent voltage-source return to ground. The branch is a finite-impedance bias injection, not a resistor directly placed across BJL2 and not a passive damping shunt. At DC, `Z=100 ohm` and the selected 21.4 mV source sets 214 µA only when the full network settles; the injected current then splits according to node-4 KCL. At 1.5 ps, `X_L=41.89 ohm` and `|Z|=108.42 ohm`; this is intentionally larger than RJ2=22 ohm and BJL2 RN=8.47 ohm, limiting AC loading.
## Calibrated nonlinear load-line
The model retains all three native JJ sine current relations, IB=90 µA, L1=L2=2.50 pH, the complete L1/L2/RB KCL, and the R9-A fluxoid branch. The input-loop constant is calibrated from the R9-A settled R6-B state; it includes the fixed source/mutual fluxoid contribution. For a feed current `iF` from the local source into node 4:
```text
iL1 = iBJs - iBJL1
iL2 = IB + iL1
iF  = iBJL2 - iL2
```
This explicitly prevents the incorrect assumption that all 214 µA enters BJL2.
## Fold and selection
The calibrated positive continuation reaches its coupled static fold at feed **216.223788 µA**, with phase `(BJs,BJL1,BJL2)=(-0.442370,0.636765,1.829844) rad`. The selected 214.0 µA point is on the stable side with coupled fold distance **2.223788 µA** and BJL2 phase **1.675409 rad**. Its bare BJL2 π/2 comparison is only a diagnostic; the coupled fold is the relevant static continuation marker.
R9 read1 BJL2 positive activity excursion was +2.590650 µA; read0 was +0.566390 µA. The first-order equivalent-feed estimate puts the read1 excursion -0.366862 µA beyond the fold and leaves read0 1.657398 µA below it. This is only a single-point selection heuristic; it is not an event or switching claim. The negative lobes move away from this positive fold.
## Full-network selected settled split (analytic prediction)
| quantity | predicted value |
|---|---:|
| `P(BJs)` | -0.41104744 |
| `P(BJL1)` | 0.59622415 |
| `P(BJL2)` | 1.67540922 |
| `I(BJs)=I(Lin) [µA]` | -53.14277550 |
| `I(BJL1) [µA]` | 62.89047616 |
| `I(BJL2) [µA]` | 187.96674834 |
| `I(L1) [µA]` | -116.03325166 |
| `I(L2) [µA]` | -26.03325166 |
| `I(RB) [µA]` | 90.00000000 |
| `I(local feed) [µA]` | 214.00000000 |
At this point, the feed current is predicted to split into approximately 187.97 µA through BJL2 and -26.03 µA through the declared 3→4 L2 branch; the remainder of the bias redistribution appears in BJs/BJL1/L1. The actual JoSIM settled values will be measured again.
## jjmit scaling used
`jjmit` gives Ic,C proportional to AREA and RN,R0 proportional to 1/AREA. The unchanged receiver values are BJs AREA=1.33 (Ic=133 µA, C=93.1 fF, RN=12.03 Ω, R0=120.30 Ω), BJL1 AREA=1.12 (112 µA, 78.4 fF, 14.29 Ω, 142.86 Ω), and BJL2 AREA=1.89 (189 µA, 132.3 fF, 8.47 Ω, 84.66 Ω).
## Precheck verdict
**R10A_SINGLE_POINT_WORTH_TESTING**. The model has a stable-side selected operating point, a finite read0 equivalent margin, and a read1-near-fold first-order rationale. The actual four-case result must be judged by continuous phase, same-JJ voltage area, retrap/free-running, selectivity, and source guards; crossing the static continuation marker alone will not count as an event.
