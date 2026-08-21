# R4-A weak-mutual capture-only analytic precheck

Status: `COMPLETED` / offline analytic precheck only

Verdict: **`R4A_SINGLE_POINT_WORTH_TESTING`**

No JoSIM run was performed. No canonical BVM or existing scientific circuit was
modified.

## Scope and source mapping

Input source is the accepted R3-A raw matrix at HEAD
`4842bc7d20c755a28b2cf1a0683fbf81051173bd`.

R3-A did not directly probe `I(L_TX)`. Its source netlist is:

```text
R_IN  IN      N_PICK  12Ω
L_TX  N_PICK  N_TRIG  0.20pH
```

`N_PICK` has no other branch, so this precheck derives
`I(L_TX)=I(R_IN)` by series KCL, with the same current orientation from `IN`
through `N_PICK` to `N_TRIG`. This is explicitly a derived quantity, not a
direct raw column.

The nonlinear analysis window is `[97,130) ps`, matching R3-A. The full
`[20,170] ps` range is reported only to expose write/read-edge context.

Raw SHA-256 inputs:

```text
047fdc314a392fe3db16fac7ab19a213f900c2516462568f725dba063eded191  read1/run-01.csv
782ed4cffb3df45997964085a228b50f6d050deecf8d20fbf2d717adffa9a2c7  read0/run-01.csv
540e2f3e664c727f2eeaeb67f59a6c0f83be81416094afe167ac3e3a59ebd26c  logical1-read0-control/run-01.csv
752af8c1994ef9a2a5f6fd1e90c8bb99a23c605789cd09992589a2cb2686ee49  logical0-read0-control/run-01.csv
a894e94bd36cf9c560d1822e51581f072b4f558fc843b58b18c95c3c00f63c0b  r3a-receiver.cir
19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336  jjmit.cir
```

## Single point and model mapping

```text
L_TX       = 0.20 pH
|K|        = 0.80
L_H        = 100 pH
J_SET AREA = 0.05
J_SET bias = +3.0 µA
```

Using `Phi0=2.067833848e-15 Wb`:

```text
|M| = |K| sqrt(L_TX L_H) = 3.577708764 pH
```

The copied R3-A `jjmit` model is:

```text
.model jjmit jj(RTYPE=1, VG=2.8m, CAP=0.07p,
+              r0=160, rn=16, icrit=0.1m)
```

The repository area semantics give the proposed `J_SET`:

| quantity | value |
|---|---:|
| `Ic` | 5.000 µA |
| `C` | 3.500 fF |
| `RN` | 320 Ω |
| `R0` | 3.200 kΩ |
| bias / Ic | 0.600 |
| `beta_L = 2π L_H Ic / Phi0` | 1.519267448 |

`beta_L>1` makes a metastable fluxoid state physically plausible in an
idealized hysteretic loop. It is not, by itself, evidence that the loaded
JoSIM loop will capture or retain a state.

## Current and external-flux results

For this table the displayed flux uses the positive convention
`Phi_ext=M I(L_TX)`, with `M=+|M|`. Execution will freeze the winding polarity
explicitly; polarity sensitivity is addressed below.

### Nonlinear window `[97,130) ps`

| case | `I(L_TX)` positive peak | `I(L_TX)` negative peak | mean current | signed current area | positive / negative area | `Phi_ext/Phi0` positive / negative |
|---|---:|---:|---:|---:|---:|---:|
| read1 | +54.861 µA @100.8125 ps | −61.963 µA @104.8125 ps | +4.447 µA | +0.146628 fC | +0.293215 / −0.146587 fC | +0.094920 / −0.107207 |
| read0 | +6.394 µA @97.0000 ps | −22.107 µA @106.0000 ps | −0.617 µA | −0.020408 fC | +0.027370 / −0.047778 fC | +0.011063 / −0.038249 |
| logical1 READ=0 | +0.000273 µA | −0.000259 µA | ~0 | −1.26×10⁻⁷ fC | +9.42×10⁻⁷ / −1.07×10⁻⁶ fC | +4.73×10⁻⁷ / −4.48×10⁻⁷ |
| logical0 READ=0 | +0.001030 µA | −0.000942 µA | ~0 | +4.05×10⁻⁷ fC | +5.59×10⁻⁶ / −5.18×10⁻⁶ fC | +1.78×10⁻⁶ / −1.63×10⁻⁶ |

The corresponding `Phi_ext/Phi0` time-integrals are:

| case | `∫Phi_ext/Phi0 dt` over `[97,130)` |
|---|---:|
| read1 | +0.253692 `Phi0·ps` |
| read0 | −0.035310 `Phi0·ps` |
| logical1 READ=0 | −2.17×10⁻⁷ `Phi0·ps` |
| logical0 READ=0 | +7.01×10⁻⁷ `Phi0·ps` |

### Context over `[20,170] ps`

The full-range extrema are:

| case | positive peak | negative peak | interpretation |
|---|---:|---:|---|
| read1 | +54.861 µA | −61.963 µA | read1 nonlinear activity dominates |
| read0 | +17.166 µA | −22.107 µA | includes common READ-edge response |
| logical1 READ=0 | +6.228 µA | −7.865 µA | early write/control context, not capture onset |
| logical0 READ=0 | +7.964 µA | −6.124 µA | early write/control context, not capture onset |

## Read1/read0 separation and waveform structure

In `[97,130) ps`, pointwise `read1-read0` separation is:

| metric | value |
|---|---:|
| maximum positive separation | +55.402 µA @106.2000 ps |
| maximum negative separation | −65.361 µA @104.8125 ps |
| mean separation | +5.064 µA |
| RMS separation | 21.476 µA |
| signed separation area | +0.167036 fC |
| absolute separation area | 0.455432 fC |

Read1 is not a single-polarity pulse. It has alternating, decaying lobes:

```text
positive onset  → negative lobe → positive lobe → negative lobe
→ further alternating lobes with decreasing amplitude
```

The largest positive lobe is +54.861 µA at 100.8125 ps; the largest negative
lobe is −61.963 µA at 104.8125 ps. The current area is not zero, but it is
strongly multi-lobe: positive area is +0.293215 fC and negative area is
−0.146587 fC. This means a capture loop cannot be judged from a peak alone and
could, in principle, SET and then RESET if its state barrier is too weak.

## Bias-margin estimate

The equivalent loop-current contribution from the external flux is

```text
I_ext,eq = Phi_ext / L_H = (M/L_H) I(L_TX)
```

For the positive `M` convention:

| case | positive `I_ext,eq` | negative `I_ext,eq` |
|---|---:|---:|
| read1 | +1.963 µA | −2.217 µA |
| read0 | +0.229 µA | −0.791 µA |
| controls | <0.00004 µA | <0.00004 µA |

With `+3 µA` J_SET bias and `M>0`, the positive read1 lobe gives only
`3+1.963=4.963 µA`, just below `Ic=5 µA`. Therefore the winding polarity
cannot remain implicit.

The preregistration will freeze the same magnitude `|K|=0.80` with the mutual
polarity chosen so that the larger read1 negative lobe is additive to the
positive J_SET bias. Under that explicitly stated orientation:

```text
read1 worst-case additive lobe: 3.000 + 2.217 = 5.217 µA
read0 worst-case additive lobe: 3.000 + 0.791 = 3.791 µA
```

Thus read0 retains an estimated 1.209 µA margin below Ic, while read1 has only
about 0.217 µA margin above Ic. Controls remain essentially at the 3 µA bias
level.

This is a narrow dynamic-margin estimate, not a switching proof. It does not
assume that the loop current follows `Phi_ext/L_H` instantaneously once
`J_SET` dynamics begin.

## Required questions

### 1. Does read0 remain UNSET?

**Analytically plausible, with the preregistered favorable polarity.** Its
largest equivalent additive lobe is about 0.791 µA, giving about 3.791 µA
against 5 µA. With the opposite polarity, read1 itself loses its already small
positive margin; the sign must therefore be frozen, not tuned after a run.

### 2. Is read1 flux large enough to drive an adjacent fluxoid state?

The peak external flux is only about `0.107 Phi0`, not close to a full flux
quantum. A passive unbiased loop would therefore not have an obvious robust
fluxoid-write margin. The biased J_SET estimate makes one lobe just exceed Ic,
so a biased nonlinear write is physically plausible, but marginal.

### 3. Can read1 SET and then RESET or multi-transition?

Yes, this is the principal unresolved risk. The waveform has many alternating
lobes, and the strongest negative lobe occurs after a strong positive lobe.
`beta_L≈1.5` may preserve a metastable state, but it does not prove that the
opposite lobe cannot drive a reverse transition. R4-A must therefore count net
persistent fluxoid-state transitions, not J_SET phase slips alone.

### 4. Does `beta_L≈1.5` support metastability?

**Yes as a necessary plausibility indicator, not as a sufficient result.** It
places the loop above the simple hysteresis threshold estimate, while damping,
bias-port KCL, mutual loading, and the actual phase trajectory remain unknown.

### 5. Is there an analytic contradiction?

**No absolute contradiction was found**, provided the mutual polarity is frozen
to make the −61.963 µA read1 lobe additive. The point is nevertheless close to
threshold and exposed to multi-lobe RESET risk. Without that polarity, the
single point is analytically unfavorable rather than merely marginal.

## Verdict boundary

`R4A_SINGLE_POINT_WORTH_TESTING` means only that this one point is not ruled out
by the offline source/flux/bias calculation. It does not predict capture,
metastable retention, or one-shot output.

The future R4-A success criterion is:

> **read1 exactly one net persistent fluxoid-state transition; read0 and both
> READ=0 controls zero persistent state transitions.**

The final stable-state decision must jointly use:

- loop circulating current;
- loop fluxoid balance, including mutual-flux term;
- `J_SET` continuous phase trajectory;
- same-JJ, same-segment voltage area.

`J_SET` switching count, voltage peak, or phase excursion alone is insufficient.
