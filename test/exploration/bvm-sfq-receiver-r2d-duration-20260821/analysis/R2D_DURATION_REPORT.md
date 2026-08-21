# R2-D drive-duration threshold at fixed direct-drive amplitude

**Tier:** Exploration / EXPLORATORY
**Created:** 2026-08-21
**Parent exploration:** `test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821` (checkpoint `f714850a6fa5e8945ab69afc217cb708f9751163`)
**Head before experiment:** `f714850a6fa5e8945ab69afc217cb708f9751163`
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`, `.tran 0.0125p 170p`, PHASE analysis.

## Verdict

**R2-D verdict: `NO_THRESHOLD_IN_BOUNDED_DURATION_MATRIX` — but with a decisive mechanism finding.**

Increasing only the pulse FWHM from 0.27 to 20 ps at fixed amplitude 3.5 µA grows the B_OUT response strongly and nonlinearly (largest monotonic segment 0.0096 → 0.0835 turn, ~8.7×), but no duration in the matrix produces a complete 2π transition. The w20p0 point reveals why, quantitatively: the response has reached the **quasi-static subcritical ceiling** — peak junction current 9.62 µA = 96 % of Ic, peak phase 0.2069 turn ≈ arcsin(9.62/10)/2π = 0.2061 turn — and the remaining ~3.8 % shortfall to criticality is set by shunt diversion of the injected current, not by duration. Longer pulses cannot help: the trajectory already follows the drive shape reversibly.

No free-running, no ringing, no multi-turn behavior occurred; the large monotonic "decreasing" segment at w20p0 is the symmetric quasi-static relaxation back to the exact initial equilibrium (net drift over the full run = +0.1234 turn = the initial bias-point establishment from φ=0 to arcsin(0.7)/2π, identical in all four runs).

## Duration matrix (only variable; amplitude fixed 3.5 µA)

| Point | nominal FWHM (ps) | measured FWHM (ps) | measured base (ps) | measured charge (uA·ps) | measured charge (fC) |
|---|---:|---:|---:|---:|---:|
| w027 | 0.27 | 0.525* | 1.062 | 1.89 | 0.0019 |
| w1p0 | 1.0 | 0.988 | 1.988 | 3.50 | 0.0035 |
| w5p0 | 5.0 | 4.987 | 9.987 | 17.5 | 0.0175 |
| w20p0 | 20.0 | 19.987 | 39.975 | 70.0 | 0.07 |

*w027 measured FWHM reads 0.525 ps because the half-maximum crossing spans two sample intervals at dt≈0.0125–0.025 ps; the geometry is identical to the R2-C pulse (same zero points 103.97/105.05 ps). Unit note: uA·ps = 1e-3 fC; the manifest's nominal charges were corrected to uA·ps before first commit after a unit error was caught in review.

Pulse shape: same triangle geometry as R2-C stretched on the time axis only; center frozen at 104.51 ps; polarity = verified effective forward-drive direction (positive on 0→N_SEC source).

## Results

| Point | largest monotonic segment (turns) | span (ps) | same-segment V-area residual (turns) | complete? | qualifying? |
|---|---:|---|---:|:---:|:---:|
| w027 | 0.009645 | 103.2–104.9 | +2.2e-06 | no | no |
| w1p0 | 0.014940 | 103.2–105.3 | +5.6e-07 | no | no |
| w5p0 | 0.045389 | 99.4–107.0 | +5.4e-08 | no | no |
| w20p0 | 0.083504 | 109.4–170.0 | −6.3e-08 | no | no |

All artifacts valid (13,599 rows each). Storage preserved everywhere (JM1 post ≈ +5.91 rad). The w20p0 largest segment is the *relaxation* leg; its mirror-image rise leg during the pulse is comparable in magnitude. Net phase drift over the whole run is +0.1234 turn in every case (initial equilibrium establishment), i.e., every run returns exactly to its starting state.

### Peak junction state per point

| Point | peak I(B_OUT) (µA) | fraction of Ic | arcsin ceiling (turns) | observed phi_max (turns) |
|---|---:|---:|---:|---:|
| w027 | 7.783 | 77.8 % | 0.1419 | 0.1331 |
| w1p0 | 7.737 | 77.4 % | 0.1408 | 0.1383 |
| w5p0 | 8.675 | 86.8 % | 0.1671 | 0.1688 |
| w20p0 | 9.623 | 96.2 % | 0.2061 | 0.2069 |

The observed peak phase tracks the subcritical quasi-static relation phi_peak ≈ arcsin(I_peak/Ic)/2π with increasing fidelity as the drive becomes quasi-static — exact at w20p0 (0.2069 vs 0.2061).

## Observed

1. Duration growth produces strong nonlinear amplification of the response: 0.0096 → 0.0149 → 0.0454 → 0.0835 turn for 0.27 → 1 → 5 → 20 ps FWHM.
2. At w20p0 the junction current peaks at 9.62 µA (96 % of Ic) with node voltage only ~12 µV; the junction never crosses criticality.
3. The w20p0 trajectory is a reversible quasi-static excursion: rise following the drive edge, peak 0.2069 turn at ~108–110 ps, symmetric fall, exact return to 0.1234 turn by ~155 ps.
4. Phase does NOT scale with charge: charge spans 37× across the matrix while phase spans 8.7×, with clear saturation toward the arcsin ceiling.
5. No switching occurred anywhere: no complete segment, no retrap ambiguity, no ringing, no multi-turn, storage preserved, controls n/a (all four points share the quiet logical1 background).

## Derived (arithmetic only)

1. Growth ratio w20p0/w027 largest segments: 0.083504/0.009645 = 8.66.
2. Quasi-static transfer of the increment at w20p0 peak: (9.623−7)/3.5 = 75 % reaches the junction; the secondary branch (~0.97 µA) and damper (~0.12 µA) divert the rest at V≈11.8 µV.
3. Ceiling identity at w20p0: arcsin(9.623/10)/2π = 0.2061 turn vs observed 0.2069 turn (agreement to 0.4 %).
4. Short-pulse regime (w027): peak I(B_OUT) 7.78 µA ⇒ impulse transfer of the 3.5 µA injection ≈ 22 %, consistent with R2-C.
5. Extrapolation (arithmetic, not evidence): reaching Ic=10 µA at w20p0-like quasi-static transfer requires direct amplitude ≈ 7 + 3×(3.5/2.62) ≈ 11 µA total injection, i.e., roughly 4 µA added on top of bias — about 15 % above the tested 3.5 µA.

## Inference (falsifiable interpretation)

1. The activation boundary is genuinely two-dimensional (amplitude × duration): short pulses are transfer-limited by node reactivity (R2-C), long pulses are ceiling-limited by quasi-static current balance with shunt diversion (this experiment). Duration alone at 3.5 µA saturates below criticality.
2. The binding constraint at long durations is the ~25 % steady-state diversion of injected current into the L_SEC/R_SEC_LOAD branch and damper; switching requires either more amplitude (≈4+ µA added) or reduced diversion (topology change, out of scope here).
3. The real transformer chain (+1.46 µA junction spike, R2-B) sits even further from the boundary than the 3.5 µA direct pulse: closing the receiver gap requires raising sustained/peak junction drive toward ≥10 µA, not merely widening or reshaping the existing transient.

## Unknown

1. The actual switching amplitude at quasi-static durations (predicted ≈4–4.5 µA added; untested).
2. Whether an intermediate duration (e.g., 10 ps) at higher amplitude switches cleanly or shows partial-running structure.
3. Timestep convergence at the shortest widths (w027 FWHM spans ~11–22 samples).
4. Behavior once switching does occur (retrap quality, one-shot character) — entirely unobserved so far.
5. Sensitivity of the ~25 % diversion to R_SEC_LOAD value (fixed here by frozen constraints).

## Next single most informative experiment (recommendation, not started)

**R2-E: quasi-static switching-amplitude threshold at FWHM = 20 ps.** Amplitude matrix {4.0, 4.5, 5.0} µA ascending (stop at first qualifying complete transition), everything else frozen as in R2-D. Question: what minimum direct-drive amplitude produces the first complete 2π transition? This tests the ≈4–4.5 µA prediction, delivers the project's first controlled complete-switching event at the frozen output stage, and finally exposes the retrap/one-shot behavior (Situation C risk becomes live).

## Artifacts

- Manifest (preregistered before runs; nominal-charge unit annotation corrected pre-commit): `manifest.yaml`
- Inputs: `inputs/{w027,w1p0,w5p0,w20p0}.cir` + receiver variants
- Raw: `raw/<point>/run-01.csv` (4 files)
- Analysis: `analyze_r2d_lib.py`, `analysis/r2d-summary.json`
- Hashes: `analysis/sha256sums.txt`
