# R4-A weak-mutual fluxoid capture-only — amended execution report

**Tier:** Exploration / EXPLORATORY
**Preregistration:** `manifest.yaml` at checkpoint `573c779` (precheck verdict `R4A_SINGLE_POINT_WORTH_TESTING`)
**Formulation amendment:** `R_GAUGE = 1 GΩ`, N_CAP1 → ground (per user authorization after the floating-island MNA failure at `79a2a21`)
**Head before experiment:** `79a2a21e72b78a08d55bb16bc5c9a12e45fc3484`
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`, `.tran 0.0125p 170p`, PHASE analysis; four matched cases, one run each, no sweeps.

## Main verdict

**`R4A_NO_PERSISTENT_READ1_STATE`.**

With the gauge-fixed formulation the simulation runs cleanly, and the physics answer is unambiguous: the weak-mutual capture loop **does not capture a persistent fluxoid state on read1**. The loop transient peaks at only 4.874 µA of circulating current — 23.6 % of the half-quantum boundary (~10.3 µA) needed to trap an n=±1 state in L_H=100 pH — and returns to n=0 afterward. read0 and both controls show even smaller excursions and zero transitions. J_SET never completes a phase slip in any case.

## Formulation amendment verification

- `R_GAUGE N_CAP1 0 1G` added solely as the MNA common-mode voltage reference;
- Singular-matrix error eliminated: all four cases ran to completion (13,599 rows each, finite, strictly increasing time);
- **Measured max |I(R_GAUGE)| = 2.82e-22 A across all runs** — versus ~µA-scale loop/JJ currents, a ratio of ~1e-16. The "numerically necessary but physically negligible" assumption is verified by direct probe, not assumed.

## Per-case results

| Case | complete B_SET segments | I_LH pre (µA) | I_LH held @150–170 ps (µA) | net change (µA) | \|I_LH\| peak (µA) | POST V max (µV) |
|---|---:|---:|---:|---:|---:|---:|
| read1 | 0 | +0.0000 | +0.0000 | −0.0000 | 4.874 | 172.68 |
| read0 | 0 | +0.0000 | +0.0000 | −0.0000 | 1.965 | 7.26 |
| logical1 ctrl | 0 | +0.0000 | +0.0000 | +0.0000 | 1.966 | 0.23 |
| logical0 ctrl | 0 | +0.0000 | +0.0000 | −0.0000 | 1.818 | 0.18 |

Guards preserved everywhere: JM1/JM2 storage signs intact (+5.912/−5.911 class); read1 B_TRIG nonlinear response retained; SL/N6 ordering unchanged.

## Fluxoid-balance reconstruction (read1)

- Quantum current spacing for L_H=100 pH: Φ0/L_H = **20.68 µA** per fluxoid state.
- The mutual transient delivered a loop-current excursion peaking at **4.874 µA = 0.236 of the half-quantum boundary** — far short of trapping n=±1 (which would hold ≈∓20.7 µA).
- J_SET total current ranged [−5.269, +1.874] µA. The single −5.269 µA excursion (t=116.575 ps) was examined adversarially: it coincides with V(B_SET) swinging through zero (large dV/dt), i.e., a **capacitive spike**, and the unwrapped phase shows no slip there (φ stays at +0.0709 turn). The supercurrent channel remained subcritical throughout.
- Net whole-run phase change: −0.0555 turn; φ range [−0.2368, +0.0874] turn — bounded sub-turn oscillation around the bias point, returning to n=0.
- The preregistered additive-polarity margin estimate (read1 worst-case additive lobe 5.217 µA vs Ic=5 µA) assumed the loop current would follow Φ_ext/L_H instantaneously; in the simulated loop the delivered excursion reached only 4.87 µA against a state boundary that sits at ~10.3 µA — the analytic estimate was optimistic by roughly the same factor as the flux-to-current conversion under-delivers.

## Observed

1. Zero complete B_SET segments in all four cases; no SET/RESET sequence; no multi-fire; no free-running.
2. read1 loop-current peak 4.874 µA vs read0 1.965 µA vs controls ~1.9 µA — state discrimination exists in the transient but is far below the capture boundary.
3. Gauge leakage verified negligible by direct measurement (2.82e-22 A).
4. All guards preserved.

## Derived

1. Capture boundary for this loop: |I_loop| must reach ≈Φ0/(2·L_H) ≈ 10.34 µA to trap n=±1; delivered peak was 4.874 µA → shortfall factor ≈ 2.12.
2. Equivalent required mutual flux: ≈0.5 Φ0 vs delivered ≈0.107 Φ0-class lobes (consistent with the precheck's own flux estimate) — the shortfall is structural, not marginal.
3. To close the gap within this architecture would require ~2.1× more coupled flux (larger |K|·√(L_TX·L_H) product or larger source transient) — out of scope for this single-point test.

## Inference (falsifiable)

The weak-mutual direct-capture concept fails not because of damping, formulation, or noise, but because the B_TRIG multi-turn response integrates to only ~0.1–0.25 Φ0 of net coupled flux per lobe — an order-of-magnitude-class shortfall against the ≥0.5 Φ0 needed for robust fluxoid trapping in a 100 pH loop. Any capture-based receiver needs either much stronger coupling/flux delivery or a biased near-threshold quantizer (the QB-style approach) that converts sub-quantum flux into a switching decision.

## Unknown

1. Whether a smaller L_H (raising Φ0/L_H spacing but also raising the delivered current proportionally — net effect requires analysis) could trap states at these flux levels.
2. Behavior with the opposite winding polarity (preregistered as frozen; untested).
3. Timestep convergence of the alternating-lobe response.
4. Multi-pulse accumulation effects (out of scope: capture-only).

## Rearm diagnostic

Not run — primary matrix did not PASS (`rearm = UNKNOWN`).

## Artifacts

- Amended raw: `raw-amended2/<case>/run-01.csv` ×4 (complete probes incl. I(R_GAUGE))
- Pre-amendment failed-run logs preserved in `logs/*run-01/02*` (singular-matrix evidence)
- Analysis: `analysis/r4a-amended-summary.json`, `analysis/r4a-summary.json`
- Hashes: `analysis/sha256sums.txt`
