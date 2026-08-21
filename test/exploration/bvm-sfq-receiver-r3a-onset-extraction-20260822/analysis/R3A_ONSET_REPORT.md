# R3-A B_TRIG onset-extraction feasibility — execution report

**Tier:** Exploration / EXPLORATORY
**Preregistration:** `manifest.yaml` (DRAFT `313a1d3`, oracle clarification `8a5b25b`; Luna/Sol read-only check completed before execution)
**Head before experiment:** `8a5b25b`
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`, `.tran 0.0125p 170p`, PHASE analysis; four matched cases, one run each, no sweeps.

## Main verdict

**`NO_OUTPUT_EVENT`.**

The single preregistered extractor instance (C_ON=1 fF, B_OUT AREA=0.10/bias=7 µA, R_DAMP=100 Ω, L_Q=100 pH, R_Q=10 Ω) produced **zero complete forward events in logical1+READ**, and zero events anywhere in [20,170] ps. Per the failure boundary this falsifies only this extractor instance; rearm diagnostic was not run (gate not met); no parameters were swept.

## Runtime parameter mapping (recorded from instantiated model)

- Model line: `.model jjmit jj(RTYPE=1, VG=2.8m, CAP=0.07p, r0=160, rn=16, icrit=0.1m)`; JoSIM scales Ic,C by AREA and divides RN,R0 by AREA.
- B_OUT (AREA=0.10): **Ic=10 µA, C=7 fF, RN=160 Ω, R0=1600 Ω**
- B_TRIG (AREA=0.50): Ic=50 µA, C=35 fF, RN=32 Ω, R0=320 Ω

## Per-case results

| Case | forward complete segs | reverse complete | qualifying ([97,130) onset) | late/tail |
|---|---:|---:|---:|---:|
| read1 | 0 | 0 | 0 | 0 |
| read0 | 0 | 0 | 0 | 0 |
| logical1-read0-control | 0 | 0 | 0 | 0 |
| logical0-read0-control | 0 | 0 | 0 | 0 |

All four artifacts valid (13,599 rows each). No MULTI_FIRE, no READ0/CONTROL false trigger, no LATE_OR_TAIL_TRIGGER, no FREE_RUNNING — the failure is simply that the extractor never delivered a switching-level drive.

## Guards (all preserved)

- read1 B_TRIG retains its complete nonlinear running behavior (large alternating segments through ~150 ps; dominant excursion 103–105 ps ≈ +0.90 turn within the multi-turn pattern);
- read0 and both READ=0 controls show no complete B_TRIG transition;
- SL/N6 ordering preserved (read1 peaks 1.392/1.881 mV vs read0 0.452/0.731 mV);
- JM1/JM2 storage signs preserved in all cases (+5.911/+0.285…0.317 vs −5.911/−0.321);
- JS1/JS2 show no anomalous states.

## Causal chain reconstruction (read1)

Measured sequence inside the frozen causal window [97,130):

1. **B_TRIG nonlinear onset:** V(B_TRIG) develops large alternating excursions from ~98 ps (±0.2→1.6 mV), consistent with the R0b source behavior; the common 95–96 ps READ edge appears as a small common-mode blip (+170 µV @96 ps) and was correctly not treated as onset.
2. **I(C_ON):** coupling current flows as predicted (peaks ±0.93 µA around 100–102 ps; |I(C_ON)| max 2.24 µA across the window) — the capacitor does transduce the onset.
3. **B_OUT drive:** junction current rises to a causal-window peak of only **8.064 µA at 108.89 ps** — i.e., bias(7) + ~1.06 µA effective drive, far below Ic=10 µA.
4. **B_OUT phase event:** none possible at that drive level; largest sub-turn activity only.
5. **V_EXT:** bounded ringing ±172 µV max (105.25 ps) — far below any switching-scale voltage-time product.
6. **I_Q growth:** L_Q branch carries ≤1.85 µA transients but never a post-event quench signature (no event to quench).
7. **Refractory/retrap:** not reached; node returns to bias equilibrium after each excursion.

### Failure mode

The 1 fF coupling capacitor is a **differentiator**: it passes only the fast edges of the B_TRIG voltage, delivering µA-scale, sub-ps-class current spikes into N_EXT. This reproduces exactly the R2-C regime (fast injection → shunt diversion → deep-subcritical response) rather than the R2-F regime (sustained near-critical hold) that the calibrated requirement demands. The chain "onset → I(C_ON)" works qualitatively; the "I(C_ON) → switching-level B_OUT drive" link fails quantitatively by ~2 µA of missing sustained drive.

## Observed / Derived / Inference / Unknown

**Observed:** zero events anywhere; causal-window peak junction drive 8.064 µA; |I(C_ON)| ≤2.24 µA; |V_EXT| ≤172 µV; guards preserved; controls clean.

**Derived:** effective incremental drive at peak = 8.064−7 = 1.06 µA = 10.6 % of Ic; versus the calibrated direct-drive reference (~4.5 µA added with ~20 ps hold) the extractor underdelivers by roughly 4×.

**Inference:** with C_ON as the only coupling element, this extractor family instance cannot meet the calibrated requirement; meeting it would require an accumulation/hold mechanism (as anticipated by the architecture comparison), not a different single capacitor value.

**Unknown:** whether other C_ON values or a capture-loop replacement could work (out of scope here by the no-sweep rule); timestep sensitivity; sub-ps details of the coupling spikes.

## Rearm diagnostic

Not run — primary matrix did not PASS (`rearm = UNKNOWN`).

## Artifacts

- Preregistration commits: `313a1d3` (DRAFT), `8a5b25b` (oracle clarification)
- Raw: `raw/<case>/run-01.csv` ×4
- Analysis: `analysis/r3a-raw-summary.json`, `analysis/r3a-summary.json`
- Hashes: `analysis/sha256sums.txt`
