# R5-C analytic saddle precheck

**Created:** `2026-08-22T21:12:14+08:00`  
**HEAD observed:** `01d2ed5fef790c3e846597446f899ebadbddd52f`  
**Mode:** Exploration / EXPLORATORY; no JoSIM run performed for R5-C at this stage.

## Question

Can one physics-informed bias point of the existing R5-A reduced quantizer place
the read1 trajectory across the *actual inductive-loop saddle*, while read0 and
both zero-read controls retain a finite margin?

The calculation uses the committed R4-A amended and R5-A raw CSVs. It does not
use the bare-JJ `±π/2` threshold.

## Actual model and orientation

The copied R5-A fixture has:

| Quantity | Value |
|---|---:|
| `L_H` | `100 pH` |
| `L_TX` | `0.20 pH` |
| `K` | `−0.80` |
| mutual `M=K√(L_TX L_H)` | `−3.577708764 pH` |
| B_SET `AREA` | `0.05` |
| `Ic` | `5.0 µA` |
| `RN` | `320 Ω` |
| `R0` | `3.2 kΩ` |
| `C` | `3.5 fF` |
| `βL=2πL_H Ic/Φ0` | `1.51926745` |
| `βc=2π Ic RN² C/Φ0` | `5.44505453` |

The area scaling is the actual JoSIM `jjmit` semantics: `Ic` and `C` scale
with area, while `RN` and `R0` scale inversely.

Using the R5-A raw orientation, the reconstructed branch quantity

\[
 n=\frac{\phi}{2\pi}+\frac{L_H I_{L_QB}+M I_{L_TX}}{\Phi_0}
\]

stays within approximately `1.1×10⁻⁷` of `n=0` through the causal read1
window. This validates the sign convention used below; it does not by itself
prove a persistent fluxoid transition.

With `φ=P(B_SET|XTRIG)` (N_B relative to N_A), the zero-voltage loop equation
on fluxoid branch `n` is written as

\[
  \phi + \beta_L\left(i_b+\sin\phi\right)
  + \phi_{ext}=2\pi n,
  \qquad
  \phi_{ext}=\frac{2\pi M I_{TX}}{\Phi_0},
\]

where `i_b=I_bias/Ic`. The R5-A polarity makes the large negative
`I(L_TX)` lobe produce positive `φ_ext`, driving the negative phase direction.

Static stability is

\[
  \frac{dF}{d\phi}=1+\beta_L\cos\phi>0,
\]

so the two saddle angles are

\[
  \phi_s=\pm\arccos(-1/\beta_L)=\pm2.28923753\ {m rad}
  =\pm0.36434347\ {m turn}.
\]

## Current R5-A point: `I_bias=4.2 µA`

For the connected `n=0` branch, the static operating point is

| Quantity | Derived value |
|---|---:|
| `φ_OP` | `−0.5205568 rad = −0.0828492 turn` |
| distance to reverse saddle | `0.2814943 turn` |
| distance to forward saddle | `0.4471927 turn` |
| reverse-saddle required `Φ_ext/Φ0` | `+0.3432665` |
| equivalent loop-current perturbation | `+7.0982 µA` |
| required primary `I_TX` for this polarity | `−198.40 µA` |
| forward-saddle required `Φ_ext/Φ0` | `−0.7494887` |
| equivalent loop-current perturbation | `−15.4982 µA` |
| required primary `I_TX` | `+433.19 µA` |

The static external-flux requirement is much larger than the instantaneous
R5-A `I_TX` peak. This does not by itself rule out a dynamic escape because the
underdamped loop has inertia; it does rule out interpreting peak external flux
as a direct static threshold crossing.

## Existing raw waveform estimates

All phase excursions below use the same-JJ `P(B_SET)` and the `80–90 ps`
pre-window median. The causal window is `[97,130) ps`.

| Source case | `I_TX` min/max | signed `Φ_ext/Φ0` min/max | `Δφ` min/max from pre |
|---|---:|---:|---:|
| R5-A read1 | `−47.7816/+54.2860 µA` | `−0.093924/+0.082670` | `−0.249559/+0.184366 turn` |
| R5-A read0 | `−22.1317/+6.6483 µA` | `−0.011503/+0.038292` | `−0.030756/+0.026340 turn` |
| logical1 control | `−1.4039/+1.2391 nA` | `−2.14/+2.43×10⁻⁶` | `−0.000222/+0.000237 turn` |
| logical0 control | `−2.3456/+2.6867 nA` | `−4.65/+4.06×10⁻⁶` | `−0.000432/+0.000353 turn` |

R4-A gives the same read1 source scale within the amended fixture. R5-A
read1 `I_TX` has a multi-lobe waveform rather than a monotonic flux step:

- current-area over `[97,130) ps`: `+60.747 µA·ps` net;
- positive lobe: `+287.750 µA·ps`;
- negative lobe: `−227.003 µA·ps`.

Thus the source has a small net bias tendency but substantial alternating
lobes; a phase excursion is not equivalent to a persistent fluxoid transition.

At the original 4.2 µA point, the read1 minimum is about
`−0.332423 turn`, leaving approximately `0.031921 turn` to the true reverse
saddle at `−0.364343 turn`. The original point therefore does **not** provide
an analytic crossing margin. Read0 leaves approximately `0.250766 turn` to
that saddle, and controls leave approximately `0.281 turn`.

## Single candidate selected analytically

The raw read1 excursion is close enough to the true saddle that bias can move
the static operating point without changing topology, `AREA`, `L_H`, `L_TX`,
`K`, or damping. The relevant positive external-flux lobe is the lobe produced
by negative `I_TX` under the declared `M<0` orientation: `+0.093924 Phi0` for
read1 and `+0.038292 Phi0` for read0. Solving the same nonlinear equation gives
a conditional static selectivity interval of approximately `9.356–10.506 µA`.
The one selected point is the midpoint based on the actual signed raw lobe:

| Quantity | `I_bias=9.93 µA` |
|---|---:|
| `i_b` | `1.986` |
| connected `n=0` `φ_OP` | `−1.5016303 rad = −0.2389919 turn` |
| reverse-saddle distance | `0.1253516 turn` |
| forward-saddle distance | `0.6033354 turn` |
| reverse-saddle required `Φ_ext/Φ0` | `+0.0661649` |
| equivalent loop-current perturbation | `+1.3682 µA` |
| required primary `I_TX` | `−38.24 µA` |

If the measured R5-A source-induced relative excursion is held as the
first-order estimate, the read1 negative excursion is predicted to cross the
reverse saddle by about `0.12421 turn`. The read0 estimate remains about
`0.09460 turn` away, and the controls remain over `0.12 turn` away. The
quasistatic flux criterion independently puts the read1 lobe above, and the
read0 lobe below, the selected reverse-fold threshold.

This extrapolation is explicitly an **Inference**, not a dynamic guarantee:
changing bias can change plasma oscillation amplitude, phase, and damping
trajectory. It is nevertheless a finite selective analytic window, unlike the
original 4.2 µA point. An independent Sol review reached the same qualitative
conclusion and placed the useful interval near `9.6–10.5 µA`; the signed raw
orientation fixes the single selected point here at `9.93 µA`.

## Precheck verdict

**`R5C_SINGLE_POINT_WORTH_TESTING`**

There is no analytic contradiction. The original R5-A point itself is below
the correctly calculated reverse saddle, but one single physics-informed point,
`I_SET_BIAS=9.93 µA`, places the selected read1/read0 external-flux lobes on
opposite sides of the true reverse fold while read0/control retain finite
phase margin.

No bias sweep is authorized. The next artifact is the preregistration for this
single point and the four matched cases only.

## Evidence labels

- **Observed:** committed R4-A/R5-A CSV phase/current excursions, controls, and
  multi-lobe source waveform.
- **Derived:** nonlinear branch, saddle locations, external-flux/current
  requirements, model-scaled `Ic/RN/R0/C`, and candidate static margins.
- **Inference:** the 9.93 µA point should cross read1 while preserving read0
  separation if the source-induced relative excursion remains comparable.
- **Unknown:** dynamic bias sensitivity, true escape versus bounded turning,
  retrap, timestep stability, and post-event state.
