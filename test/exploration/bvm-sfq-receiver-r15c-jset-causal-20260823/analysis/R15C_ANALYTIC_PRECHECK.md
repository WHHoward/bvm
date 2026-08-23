# R15-C analytic precheck results

Input: R15-B saved `I(L_TX)` raw; no JoSIM run was used for this precheck.

Equation: `55 pH*d(delta_I)/dt + 27.5 ohm*delta_I = -M*dI_TX/dt`, with `M=-2.529822 pH` and baseline `I_JSET=5.6 uA`.

| case | delta I min (uA) | delta I max (uA) | I_JSET min (uA) | I_JSET max (uA) | forcing min (mV) | forcing max (mV) |
|---|---:|---:|---:|---:|---:|---:|
| logical1-read | -2.485953 | 2.057608 | 3.114047 | 7.657608 | -0.383599 | 0.277160 |
| logical0-read | -0.836805 | 0.608259 | 4.763195 | 6.208259 | -0.152901 | 0.141225 |
| logical1-read0-control | -0.000019 | 0.000016 | 5.599981 | 5.600016 | -0.000002 | 0.000002 |
| logical0-read0-control | -0.000027 | 0.000026 | 5.599973 | 5.600026 | -0.000003 | 0.000003 |

## Polarity and timing

The forcing column is the signed RHS `-M*dI_TX/dt`; the response is the signed `delta_I_JSET`. A positive lag means the finite `LΣ/R_BIAS` network reaches its largest absolute current excursion after the forcing peak.

| case | forcing peak signed (mV) @ ps | delta peak signed (uA) @ ps | response lag (ps) |
|---|---:|---:|---:|
| logical1-read | -0.383599 @ 104.1250 | -2.485953 @ 104.5250 | +0.4000 |
| logical0-read | -0.152901 @ 105.0000 | -0.836805 @ 106.0000 | +1.0000 |
| logical1-read0-control | -0.000002 @ 94.0000 | -0.000019 @ 94.4125 | +0.4125 |
| logical0-read0-control | -0.000003 @ 94.9625 | -0.000027 @ 95.5750 | +0.6125 |

In the analytic window, read1/read0 modulation p2p is `3.144x`; the largest READ=0 control p2p is `5.32262e-05 uA`. The sign follows the mutual polarity through the `-M*dI_TX/dt` forcing, with the expected finite-network lag.

The predicted current is a linear pre-switch estimate only; it is not event evidence and is not a substitute for JoSIM phase/area analysis.
