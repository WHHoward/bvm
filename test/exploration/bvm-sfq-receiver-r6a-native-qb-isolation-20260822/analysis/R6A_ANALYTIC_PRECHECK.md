# R6-A weak-mutual native-QB isolation analytic precheck

## Decision

`R6A_SINGLE_POINT_WORTH_TESTING`

No JoSIM run was used for this precheck. The calculation reads the committed
direct-SL native-QB raw current `I(L_SL|XBVM1)` from
`bvm-sfq-receiver-native-qb-20260822` as a **primary-current waveform proxy**.
It does not assume that the isolated primary will carry the same current; the
new run must measure `I(R_PRI)` and `I(L_PRI)` directly.

## Frozen single point

```text
L_PRI  = 0.20 pH
L_SEC  = 2.00 pH
K      = 0.50
R_PRI  = 12 Ω
```

Therefore:

\[
M=K\sqrt{L_{PRI}L_{SEC}}
 =0.50\sqrt{0.20\times2.00}\ {m pH}
 =0.316227766\ {m pH}.
\]

The primary return is a passive `R_PRI` plus `L_PRI` branch from canonical
`SL1` to ground. The native QB input is the differential secondary arm
`QB_IN ↔ ground`; no native QB element or parameter is changed.

## Direct-SL source proxy

The values below use the preregistered `[94,130)` ps activity window and the
direct-SL raw files. Currents are in the declared `I(L_SL|XBVM1)` orientation.

| Case | I minimum (µA) | I maximum (µA) | Signed current impulse (µA·ps) | Pre median (µA) | Post median (µA) |
|---|---:|---:|---:|---:|---:|
| read1 | -28.2839 | +84.8385 | +517.217 | +0.000236 | -0.00541 |
| read0 | -31.4471 | +26.4665 | -0.0201 | -0.000264 | +0.00307 |
| logical1 READ=0 | -0.001762 | +0.001760 | -0.000673 | +0.000236 | +0.0000083 |
| logical0 READ=0 | -0.001725 | +0.001699 | +0.000593 | -0.000264 | -0.0000080 |

The read1 positive peak is about `3.21×` the read0 positive peak; the absolute
peak ratio is about `2.70×`. The read1 positive lobe occurs near 104.9 ps and
the negative lobe near 110.6 ps, so the source transient is bipolar on a
roughly few-ps scale rather than a DC bias.

The signed current impulse is not itself a fluxoid count. It is included only
to show the net bias tendency of the proxy waveform. The pre/post currents both
return close to zero, so the transformer external flux also returns close to
zero after the transient.

## Predicted secondary flux and induced voltage

Using `Phi_ext=M I_PRI` and `V_ind=M dI_PRI/dt`, with the direct-SL current as
the proxy:

| Case | Φext minimum (Φ0) | Φext maximum (Φ0) | peak |Φext| (Φ0) | Vind minimum (µV) | Vind maximum (µV) | peak |Vind| (µV) |
|---|---:|---:|---:|---:|---:|---:|
| read1 | -0.004325 | +0.012974 | 0.012974 | -50.36 | +37.17 | 50.36 |
| read0 | -0.004809 | +0.004047 | 0.004809 | -16.42 | +14.45 | 16.42 |
| logical1 READ=0 | -3.05e-7 | +2.33e-7 | 3.05e-7 | -0.001136 | +0.001193 | 0.001193 |
| logical0 READ=0 | -2.23e-7 | +3.00e-7 | 3.00e-7 | -0.001156 | +0.001125 | 0.001156 |

The positive read1/read0 predicted flux separation is approximately
`0.00893 Φ0`; the corresponding positive induced-voltage separation is about
`22.7 µV`. This is a state-dependent transient margin, not a claim that the
native QB loop will retain a persistent fluxoid state.

## Reflected-loading expectation

For a coupled-inductor interface, the reflected secondary contribution to the
primary impedance is frequency- and load-dependent. A first-order comparison
is that its coupling scale is proportional to `M²`, hence approximately

\[
\left(\frac{K=0.50}{K=0.80}\right)^2=0.390625
\]

of the corresponding `K=0.80` pickup contribution, assuming the same winding
and secondary load. This is only a relative estimate; the native QB input is
nonlinear and is not a fixed resistor.

At representative 5--10 ps edge scales:

| Quantity | 5 ps | 10 ps |
|---|---:|---:|
| ωM | 0.397 Ω | 0.199 Ω |
| ωLSEC | 2.51 Ω | 1.26 Ω |

The mutual reactance is small compared with the explicit `R_PRI=12 Ω` primary
return, which supports the expectation of reduced source loading. However,
the secondary winding itself can shunt the input transient through its native
QB load; this is the main transfer-starvation risk and cannot be decided
without the matched run.

## Physics assessment

### Observed

- Direct-SL read1 and read0 primary-current proxies are state dependent.
- READ=0 control proxies are approximately five orders of magnitude smaller
  than read1 at the selected positive/edge scales.
- The selected mutual point reduces coupling relative to the accepted R1a
  `K=0.80` pickup while retaining a finite read1/read0 transient separation.

### Derived

- The single point predicts a finite read1 secondary flux/voltage transient,
  with larger positive lobe than read0 and negligible controls.
- The proxy primary current returns near its pre-state value, so the induced
  external flux has no analytically established persistent endpoint offset.

### Inference

- `K=0.50` is weak enough to target direct-SL back-action reduction, while not
  being a no-op coupling point.
- The native QB's existing `Lin/L1/L2` loop is the only proposed capture
  mechanism; no extra accumulator, JJ, bias, or JTL is introduced.

### Unknown

- Actual isolated `I(R_PRI)`, `I(L_PRI)`, `I(L_SEC)`, and `V(L_SEC)`.
- Whether the native QB loop converts the bipolar transient into selective
  BJs/BJL1/BJL2 activity.
- Whether the secondary reflected load still produces multi-turn JS1/JS2
  drift.
- Whether BJL2 completes a phase/area-consistent event.

The point is therefore worth one four-case test, with no K/L/AREA/bias sweep.
