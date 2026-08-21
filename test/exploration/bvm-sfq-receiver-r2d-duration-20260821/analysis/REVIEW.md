# R2-D numerical and adversarial review

## Review scope

Strongest bounded claim: "at fixed 3.5 µA direct-drive amplitude, increasing FWHM from 0.27 to 20 ps grows the B_OUT response 8.7× but never reaches a complete transition; at w20p0 the junction peaks at 96 % of Ic and the response saturates at the quasi-static arcsin ceiling." This review tests that claim against the four runs. It does not bound amplitudes above 3.5 µA, does not claim convergence, and does not upgrade anything to Candidate.

## Numerical checks

1. Event oracle identical to R2-B/R2-C: continuous adjacent-sample unwrapped P(B_OUT|XTRIG), monotonic segment ≥1.0 turn with start ≤130 ps and same-segment direct V(B_OUT|XTRIG) trapezoid area within 0.05 turn on actual timestamps. No complete segment exists in any run.
2. The w20p0 largest segment (0.0835 turn "decreasing", 109–170 ps) was adversarially examined as a potential free-running claim: it is not. The unwrapped trajectory rises reversibly with the drive (peak 0.2069 turn ≈ arcsin(9.623/10)/2π = 0.2061), falls symmetrically, and settles exactly at the pre-pulse equilibrium 0.1234 turn by ~155 ps; net whole-run drift is +0.1234 turn in all four runs (the initial φ=0 → bias-equilibrium establishment). V(B_OUT) decays monotonically to −0.00 µV; there is no sustained rotation.
3. Ceiling identity verified numerically at all points: observed phi_max tracks arcsin(I_peak/Ic)/2π increasingly well as duration grows (w20p0 agreement 0.4 %).
4. Charge units: an initial unit error (uA·ps vs fC, factor 1000) was caught during review; measured charges in the summary JSON are correct (uA·ps = 1e-3 fC), and the manifest nominal-charge annotation was corrected to uA·ps before first commit. The report states both unit systems explicitly.
5. All four CSVs artifact-valid: 13,599 rows, finite, strictly increasing time, no missing columns; single timestep setting, no convergence claim. The w027 FWHM spans only ~11–22 samples — flagged as Unknown.

## Adversarial checks

1. **Could the w20p0 relaxation be a hidden instability?** No: it is monotonic, symmetric to the rise leg, terminates at the exact initial equilibrium, and carries matching signed voltage area (−6.3e-08 residual). Free-running would show continued unidirectional phase accumulation beyond simulation end or alternating running segments.
2. **Could the pulse have failed to be quasi-static at w20p0?** The trajectory follows the drive shape (rise over ~40 ps base, peak near center), and node RC (~76 fs) plus L_SEC/R_SEC_LOAD timescale are far shorter than the base width; the arcsin-ceiling match confirms quasi-static current balance.
3. **Is the "duration saturates" conclusion premature with only 4 points?** The saturation argument does not rest on trend-fitting: at w20p0 the response already equals the quasi-static ceiling for the achieved peak current, so further duration increase at fixed amplitude cannot raise the ceiling. This is a structural argument, stated as Inference with its assumption (quasi-static transfer fraction roughly preserved) recorded.
4. **Sequential stop rule:** runs were executed ascending with per-run qualifying checks; no run after a qualifying event exists because none qualified; no extension to 50/100 ps was run, per plan.
5. **Guards:** storage signs preserved in every run; background identical across points (no READ); controls from R2-C establish the zero-activity baseline of the same fixture family.
6. **Interpretation discipline:** Observed/Derived separated; the two-regime boundary picture and the amplitude extrapolation (≈4+ µA added) labeled Inference/extrapolation; Unknown lists five gaps including the entirely-unobserved post-switching behavior.

## Disposition

Artifacts valid; preregistered analysis executed as registered; **bounded verdict `NO_THRESHOLD_IN_BOUNDED_DURATION_MATRIX`**, upgraded in information value by the quantitative quasi-static ceiling identification (96 % of Ic, exact arcsin match). The duration axis is now bracketed: short pulses are transfer-limited, long pulses are balance-limited; the next axis is amplitude at quasi-static duration.
