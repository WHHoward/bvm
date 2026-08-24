# Analytic precheck: M1–M5

## Inputs used

The accepted Q0 raw `V(OUT)` has 2999 samples at `0.1 ps` spacing. Across the
six registered pulse windows its measured range is:

- `V(OUT)=-212.418…+956.956 µV`, p2p `1.1693743 mV`;
- `I(R_LOAD)=-21.242…+95.696 µA`, p2p `116.9374 µA`;
- a simple `|V|` diagnostic envelope lasts about `7.3 ps` per pulse;
- the accepted direct-JTL comparator reports `I(L1|XJTL1)` p2p about
  `144.814 µA`.

The envelope and peak numbers are only sizing inputs. They are not event
criteria.

## M2: selected `R_ISO=10 Ω`

Using the accepted direct-JTL activity as a first-order loaded-boundary
estimate gives

```text
Z_eff ≈ 1.169374 mV / 144.814 µA = 8.075 Ω
I_JTL,with-RISO / I_direct ≈ Z_eff / (Z_eff + 10 Ω) = 0.4467
predicted current p2p ≈ 64.7 µA
```

This is deliberately only an impedance-scale estimate. The selected resistor
is comparable to the inferred JTL dynamic impedance, so it should reduce
reflected loading without making the branch vanish. It is one causal point,
not a resistor threshold claim.

## M4: selected `L_ISO=10 pH`

The dominant Q0 output activity has a roughly `1–7.3 ps` edge/envelope. For a
series inductor, `|X_L|≈L/τ` gives:

| diagnostic timescale | `|X_L|` for 10 pH |
|---:|---:|
| 1 ps | 10.0 Ω |
| 2.8 ps | 3.57 Ω |
| 7.3 ps | 1.37 Ω |

The point is therefore non-negligible on the first edge and becomes less
restrictive over the full pulse. It is also about `4.83×` the standard JTL
input `L1=2.07 pH` and `7.56×` QB `L0=1.323 pH`. This gives a measurable
transient boundary change while retaining a DC superconducting path. No
exact transfer fraction is assumed for the nonlinear JTL.

## M5: selected coherent scale `s=54/250=0.216`

The standard cell uses area `2.5`, hence nominal `Ic=250 µA`. The selected
cell uses area `0.54`, hence actual jjmit parameters are:

| quantity | standard area 2.5 | scaled area 0.54 |
|---|---:|---:|
| `Ic` | 250 µA | 54 µA |
| `C` | 175 fF | 37.8 fF |
| `RN` | 6.4 Ω | 29.6296 Ω |
| `R0` | 64 Ω | 296.296 Ω |
| `τQ=Φ0/(2πIcRN)` | 0.20569 ps | 0.20569 ps |
| `βc=2πIcRN²C/Φ0` | 5.44505 | 5.44505 |

The internal cell inductances are multiplied by `1/s=4.62963`, preserving
`L*Ic/Φ0`: `L1=9.5833`, `L2=9.6667`, `L3=9.6389`, `L4=9.5926 pH`;
`LB1=10.8148 pH`, `LP1=1.4523 pH`, `LP2=1.4458 pH`. The bias remains the
same normalized fraction, giving `IB1=75.6 µA`. Resistance-like damping and
termination are also scaled by `1/s`: `Rsheet=9.2593 Ω`, `RB1=RB2=12.7035 Ω`,
`R_TERM=4.6296 Ω`.

This scaling changes the current class and boundary impedance together; it is
not an Ic-only reduction. A separate positive-control run is required before
the Q0 coupling run. The historical references remain contextual only:

```text
R1a passive secondary: 5.564 µA
R12 68.4 µA controlled input: no event
R13 110.2 µA canonical replay: subthreshold
R12 300 µA controlled input: bounded one-event positive reference
```

Those references are not a universal threshold and do not replace the
same-JJ phase/area evidence in this batch.

## Precheck disposition

No analytic contradiction was found for M1–M4. M5 is conditional on its
independent positive control. The matrix is worth executing exactly at these
points and must stop after the registered fixtures.
