# R5-A static operating-point sanity check — report (DRAFT stage, no main matrix run)

**Tier:** Exploration / EXPLORATORY
**Fixture:** `inputs/sanity-k0.cir` — exact R5-A topology with `K_TX_LH = 0.00` (no mutual stimulus), bias-only, logical1 write init without READ.
**Run:** single JoSIM execution (`/tmp/r5a_sanity.csv`, 0–170 ps, dt=0.0125 ps); this is a formulation/operating-point check, not the preregistered four-case matrix.

## Measured bias-only operating point (settled 100–170 ps medians)

| quantity | value |
|---|---:|
| I(J_SET) | **−2.4868 µA** |
| I(L_QB) | **+1.7132 µA** |
| V(J_SET) | +0.0026 µV ≈ 0 (zero-voltage state) |
| P(J_SET) | −0.52056 rad = **−0.08285 turn** |
| I(R_GAUGE) | 0.0000 µA (V(N_A)=0; gauge carries nothing at the operating point) |

KCL closes exactly with the bias branch inside the island: I_BSET + I_BIAS = I_LQB + I_RG → −2.4868 + 4.2 = 1.7132 + 0 ✓. The floating bias source drives a persistent circulating current around the L_QB+B_SET loop — this is the intended bias-assisted mechanism working as designed.

Supercurrent consistency: Ic·sin(φ) = 5·sin(−0.52056) = −2.487 µA matches I(J_SET) exactly; normal-channel current is zero (V≈0). The junction sits in a stable zero-voltage state at φ = −4.7°.

## Answers to the four mandated questions

### Q1 — Is 4.2 µA bias-only already too close to spontaneous SET?

**No.** Zero-voltage state, phase constant to ±3e-5 turn across the whole settled window, no phase jumps >90° anywhere, no slips during or after the bias ramp (max ramp transient 163 µV, decaying). The operating point is statically stable.

### Q2 — Does read0 have a real finite margin (not nominal 10 nA)?

**Yes — and much larger than the naive additive arithmetic suggested.** The "10 nA margin" came from treating the transient as an additive junction current. In the actual loop, the transient enters as flux and moves φ. The correct margins are angular:

- Operating point: φ_OP = −0.0829 turn.
- Forward critical (+π/2): 0.3328 turn of travel away.
- Reverse critical (−π/2): 0.1672 turn of travel away.

The read0 worst-case lobe (~0.791 µA equivalent → 0.038 turn swing) leaves ~0.13 turn of reverse margin — a real, measurable margin, not 10 nA.

### Q3 — Can read1 enter the switching basin?

**Plausible but sign-sensitive — this is the decisive open item.** Two estimates bracket it:

- Flux-conversion estimate: read1's largest measured loop excursion in R4-A was 4.874 µA → 0.2355 turn of φ swing. From φ_OP=−0.083, that reaches ≈ −0.32 turn in the negative direction — **past the −π/2 reverse critical angle (−0.25)** if the excursion drives negatively; or to +0.15 turn positively — short of +π/2 (+0.25) in the positive direction.
- The biphasic waveform contains both polarities, so one of the two directions will be driven toward its nearer critical angle. With the frozen polarity, the large negative lobe drives toward reverse critical (0.167 turn away) and the measured swing (0.236 turn class) exceeds it.

So read1 has a credible path into a switching basin via the **reverse** direction — which would register as a negative-direction complete slip. The oracle must therefore count complete segments in **both** directions as SET events for read1 (direction recorded), while still requiring exactly one.

### Q4 — Multi-fire risk from alternating lobes?

**Reduced but not eliminated.** After a first slip in either direction, the loop re-equilibrates one fluxoid over; the alternating subsequent lobes decay in amplitude (R4-A/R2-A data), and the nearest wrong-direction critical angle is ≥0.33 turn away post-slip. Risk assessed LOW-to-MODERATE; the whole-run one-shot rule will adjudicate empirically.

## Consequence for the DRAFT

The 4.2 µA operating point **is physically stable and selective by angular-margin analysis** — the sanity check passes. One oracle amendment is required before execution, discovered by this check:

> The event oracle must count a qualifying complete segment in **either direction** (forward or reverse) as the SET event for read1, recording direction. The frozen polarity places the nearer critical angle in the reverse direction; restricting the oracle to forward-only would misclassify a physically successful extraction as failure.

No other semantic changes: same topology, same single point, same windows, same guards, same verdicts list.

## Artifacts

- Sanity fixture: `inputs/sanity-k0.cir`, `inputs/r5a-receiver.cir`
- Sanity raw: `/tmp/r5a_sanity.csv` (to be copied into `analysis/` as evidence before execution commit)
