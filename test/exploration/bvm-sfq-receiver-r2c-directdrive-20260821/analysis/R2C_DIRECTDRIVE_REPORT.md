# R2-C direct-drive B_OUT activation-threshold calibration

**Tier:** Exploration / EXPLORATORY
**Created:** 2026-08-21
**Parent exploration:** `test/exploration/bvm-sfq-receiver-r2b-damping-20260821` (checkpoint `163ee6836cb93a568df59c8e1c02c904d001deb8`)
**Head before experiment:** `163ee6836cb93a568df59c8e1c02c904d001deb8`
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`, `.tran 0.0125p 170p`, PHASE analysis.

## Verdict

**R2-C verdict: `NO_THRESHOLD_IN_BOUNDED_MATRIX` (amplitude axis at the measured narrow pulse shape).**

No amplitude in {2, 3, 4, 5} µA produced a complete 2π transition of B_OUT when injected directly into N_SEC with a triangle pulse matched to the measured real read1 forward-lobe shape (FWHM = 0.27 ps, peak at 104.51 ps). The phase response is strictly linear in amplitude (deep subcritical regime), the junction current never reaches Ic anywhere (peak 8.12 µA vs Ic = 10 µA), and per the preregistered plan the amplitude sweep stops here without auto-extension.

The failure mode is informative and quantitative: **at this timescale the N_SEC node shunts ~78 % of any fast injected current before it reaches the junction supercurrent channel** — the junction-drive transfer ratio is 22.4 % at every amplitude. The static margin (+3 µA to reach Ic from bias) is therefore *not* the relevant threshold for ps-scale drive; the node's reactive/resistive shunts (7 fF junction capacitance, L_SEC/R_SEC_LOAD branch, 100 Ω damper) set a much higher effective dynamic requirement.

## Direct-drive fixture topology

Identical to the R2-B k095-r100 receiver except one added element inside the subckt:

```
I_DIRECT      0           N_SEC        pwl(0p 0 103.97p 0 104.51p <A>U 105.05p 0 170p 0)
```

Positive amplitude on a 0→N_SEC source injects current into N_SEC, increasing i_BOUT in its positive element direction (N_SEC→ground) — the same physical direction as the real read1 forward-drive lobe (KCL closure verified against R2-B raw data: `i_BOUT = I_BIAS − i_LSEC − i_RDAMP`). Background case: logical1 write init, NO READ (quiet secondary), bias 7 µA retained, all output-stage parameters frozen (AREA=0.10, Ic=10 µA, RN=160 Ω, R0=1600 Ω, C=7 fF, R_OUT_DAMP=100 Ω).

## Pulse polarity / duration / timing source (measured, not assumed)

From R2-B raw `k095-r100/read1/run-01.csv`:

- Real read1 effective junction drive is biphasic: forward lobe ΔI(B_OUT) peak **+1.458 µA @ 104.51 ps**, counter lobe −2.176 µA @ 107.19 ps.
- Forward lobe FWHM: **0.27 ps** (contiguous span 104.38–104.65 ps).
- The calibration pulse is unipolar and matches only the forward lobe (triangle, base 1.08 ps zero-to-zero, FWHM 0.27 ps, centered 104.51 ps). This deliberate simplification is recorded in the manifest; it is not an equivalence claim to the biphasic real drive.

## Amplitude matrix and results

| Point | Amp (µA) | largest monotonic B_OUT segment (turns) | same-segment area residual (turns) | complete? | qualifying? |
|---|---:|---:|---:|:---:|:---:|
| ctrl-nopulse | 0 | 0.000000 | −5e-11 | no | no |
| amp20u0 | 2.0 | 0.005506 | +1.2e-06 | no | no |
| amp30u0 | 3.0 | 0.008264 | +1.9e-06 | no | no |
| amp40u0 | 4.0 | 0.011026 | +2.5e-06 | no | no |
| amp50u0 | 5.0 | 0.013792 | +3.1e-06 | no | no |

All segments are "increasing" and confined to the pulse window (≈103.8–104.9 ps). All five artifacts valid (13,599 rows each). Independent fresh-implementation spot check reproduces the amp50u0 largest segment exactly (0.013792 turn).

### Drive diagnostics

| Amp (µA) | max ΔI(B_OUT) (µA) | transfer ratio | max ΔV(N_SEC) (µV) | min ΔV(N_SEC) (µV) | peak i_BOUT (µA) |
|---:|---:|---:|---:|---:|---:|
| 2.0 | +0.447 | 22.4 % | +23.8 | −8.0 | 7.45 |
| 3.0 | +0.671 | 22.4 % | +35.7 | −11.9 | 7.67 |
| 4.0 | +0.894 | 22.4 % | +47.6 | −15.9 | 7.89 |
| 5.0 | +1.118 | 22.4 % | +59.5 | −19.8 | 8.12 |

Guards: controls exactly zero; storage preserved (JM1 post ≈ +5.911 rad everywhere); POST window (130–170 ps) has zero voltage activity and zero monotonic phase — clean retrap, no ringing, no free-running, no multi-turn behavior anywhere.

## Observed

1. Phase response scales perfectly linearly with amplitude: 0.0055/0.0083/0.0110/0.0138 turn for 2/3/4/5 µA (ratio 2.51 across 2→5 µA ≈ 5/2).
2. Junction-drive transfer ratio is constant at 22.4 % at every amplitude; peak junction current never exceeds 8.12 µA < Ic.
3. Node voltage excursions stay sub-mV (≤60 µV positive, ≤20 µV negative lobes).
4. No post-pulse activity at any point (no retrap ambiguity, no ringing, no free-running).
5. Controls are exactly zero; storage signs preserved.

## Derived (arithmetic only)

1. Transfer ratio 1.118/5.0 = 22.4 %; equivalently 78 % of injected fast current is diverted by node shunts.
2. Injected charge per pulse: Q = A × base/2 = A × 0.54 ps → 1.08/1.62/2.16/2.70 fC for 2/3/4/5 µA. If absorbed entirely by the 7 fF junction capacitance, this corresponds to ΔV = Q/C ≈ 0.15–0.39 mV — consistent with the observed sub-mV node swings.
3. Linearity check: phase(5µA)/phase(2µA) = 0.013792/0.005506 = 2.505 ≈ 5/2.
4. Comparison with the real chain: the transformer delivered a +1.458 µA junction spike (R2-B), which is *larger* than the +1.118 µA that a 5 µA narrow direct injection delivers. The real chain's phase response (0.0261 turn) is also ~1.9× the 5 µA direct response (0.0138 turn).

## Inference (falsifiable interpretation)

1. At ~0.3 ps timescales the N_SEC node is not a current-summing node for the junction: capacitance (7 fF), the L_SEC/R_SEC_LOAD branch, and the 100 Ω damper form a reactive/resistive shunt network that caps the supercurrent-channel transfer at ~22 %. The static threshold picture ("+3 µA reaches Ic") simply does not apply to this drive regime; the dynamic requirement is far higher.
2. The transformer chain is therefore *not* obviously the weak link: its effective junction delivery (+1.46 µA spike, 0.026 turn response) already exceeds what a 5 µA narrow parallel injection achieves. Both fall short of switching because both operate in the same fast, charge-starved regime.
3. The activation boundary must be a function of pulse duration (and shape), not amplitude alone: quasi-statically, any slow injection ≥3 µA must switch the junction (at DC the shunts carry no current at V≈0, so the supercurrent channel absorbs everything up to Ic). The observed fast-regime failure and the quasi-static expectation bracket the physics; the crossover duration is unknown.

## Unknown

1. The minimum pulse duration at fixed amplitude (e.g., 3–4 µA) that produces a complete transition — not bounded by this experiment.
2. Whether the required drive is better expressed as charge, as sustained supercritical current, or as voltage-time area (∫V dt ≈ Φ0 during switching) — needs a duration/threshold curve to discriminate.
3. Behavior for amplitudes >5 µA at this narrow shape (untested by design; extrapolation of the linear trend suggests it would remain sub-turn until very large amplitudes, but this is not evidence).
4. Timestep convergence of these sub-ps transients (single dt setting; the 0.27 ps FWHM spans only ~11–22 samples).
5. How the biphasic structure of the real chain drive (forward then reverse lobe) affects the comparison with unipolar pulses.

## Next single most informative experiment (recommendation, not started)

**R2-D: duration/threshold curve at fixed amplitude.** Fix injected amplitude at 3.5 µA (just above the static minimum) and sweep only the pulse width (e.g., FWHM ∈ {0.27, 1, 5, 20, 100} ps, same timing center and polarity). Question: what minimum duration produces the first complete 2π transition? This maps the activation boundary in the (amplitude, duration) plane, tests the quasi-static prediction directly, and converts "effective dynamic drive" into a concrete design target that any transformer topology must meet in *both* dimensions.

## Artifacts

- Manifest (preregistered before runs): `manifest.yaml`
- Inputs: `inputs/{ctrl-nopulse,amp20u0,amp30u0,amp40u0,amp50u0}.cir` + receiver variants
- Raw: `raw/<point>/run-01.csv` (5 files)
- Analysis: `analyze_r2c.py`, `analysis/r2c-summary.json`
- Hashes: `analysis/sha256sums.txt`
